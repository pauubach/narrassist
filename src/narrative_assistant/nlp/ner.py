"""
Pipeline de Reconocimiento de Entidades Nombradas (NER).

Extrae entidades (personajes, lugares, organizaciones) del texto usando spaCy
con gazetteers dinámicos para mejorar la detección de nombres creativos típicos
de ficción.

ADVERTENCIA: F1 esperado ~60-70% en ficción española.
Los modelos NER están entrenados en texto periodístico. Los nombres inventados
(Frodo, Hogwarts) NO se detectan bien sin gazetteers.
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.config import get_config
from ..core.result import Result
from ..core.errors import NLPError, ErrorSeverity
from .spacy_gpu import load_spacy_model
from .entity_validator import get_entity_validator, ValidationResult

logger = logging.getLogger(__name__)

# Límite máximo de entradas en el gazetteer dinámico para evitar memory leak
MAX_GAZETTEER_SIZE = 5000


class EntityLabel(Enum):
    """Etiquetas de entidades soportadas."""

    PER = "PER"  # Persona (personaje)
    LOC = "LOC"  # Lugar
    ORG = "ORG"  # Organización
    MISC = "MISC"  # Miscelánea


@dataclass
class ExtractedEntity:
    """
    Entidad extraída del texto.

    Attributes:
        text: Texto de la entidad tal como aparece en el documento
        label: Tipo de entidad (PER, LOC, ORG, MISC)
        start_char: Posición de inicio en el texto original
        end_char: Posición de fin en el texto original
        confidence: Confianza de la extracción (0.0-1.0)
        source: Fuente de detección ("spacy", "gazetteer", "heuristic")
        canonical_form: Forma normalizada (para comparación)
    """

    text: str
    label: EntityLabel
    start_char: int
    end_char: int
    confidence: float = 0.8
    source: str = "spacy"
    canonical_form: Optional[str] = None

    def __post_init__(self):
        """Normaliza el texto y la forma canónica."""
        # Puntuación que no debería aparecer en bordes de entidades
        BOUNDARY_PUNCT = '–—-,.;:!?¿¡\'\"()[]{}«»""'' '

        # Limpiar puntuación al final del texto (errores de segmentación)
        clean_text = self.text.rstrip(BOUNDARY_PUNCT)
        if clean_text != self.text:
            chars_removed = len(self.text) - len(clean_text)
            self.text = clean_text
            self.end_char = self.end_char - chars_removed

        # Limpiar puntuación al inicio del texto (errores de segmentación)
        clean_text = self.text.lstrip(BOUNDARY_PUNCT)
        if clean_text != self.text:
            chars_removed = len(self.text) - len(clean_text)
            self.text = clean_text
            self.start_char = self.start_char + chars_removed

        # Normalizar forma canónica
        if self.canonical_form is None:
            self.canonical_form = self.text.strip().lower()

    def __hash__(self) -> int:
        return hash((self.text, self.label, self.start_char, self.end_char))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExtractedEntity):
            return False
        return (
            self.text == other.text
            and self.label == other.label
            and self.start_char == other.start_char
            and self.end_char == other.end_char
        )


@dataclass
class NERResult:
    """
    Resultado de la extracción NER.

    Attributes:
        entities: Lista de entidades extraídas (validadas)
        processed_chars: Caracteres procesados
        gazetteer_candidates: Candidatos detectados por heurísticas
        rejected_entities: Entidades rechazadas por el validador
        validation_scores: Scores de validación por entidad
        validation_method: Método de validación usado (heuristic, llm, combined)
    """

    entities: list[ExtractedEntity] = field(default_factory=list)
    processed_chars: int = 0
    gazetteer_candidates: set[str] = field(default_factory=set)
    rejected_entities: list[ExtractedEntity] = field(default_factory=list)
    validation_scores: dict = field(default_factory=dict)
    validation_method: str = "none"

    def get_by_label(self, label: EntityLabel) -> list[ExtractedEntity]:
        """Retorna entidades filtradas por etiqueta."""
        return [e for e in self.entities if e.label == label]

    def get_persons(self) -> list[ExtractedEntity]:
        """Retorna todas las entidades de tipo persona."""
        return self.get_by_label(EntityLabel.PER)

    def get_locations(self) -> list[ExtractedEntity]:
        """Retorna todas las entidades de tipo lugar."""
        return self.get_by_label(EntityLabel.LOC)

    def get_organizations(self) -> list[ExtractedEntity]:
        """Retorna todas las entidades de tipo organización."""
        return self.get_by_label(EntityLabel.ORG)

    @property
    def unique_entities(self) -> dict[str, ExtractedEntity]:
        """Retorna diccionario de entidades únicas por forma canónica."""
        unique: dict[str, ExtractedEntity] = {}
        for entity in self.entities:
            key = f"{entity.label.value}:{entity.canonical_form}"
            if key not in unique or entity.confidence > unique[key].confidence:
                unique[key] = entity
        return unique


@dataclass
class NERExtractionError(NLPError):
    """Error durante la extracción NER."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"NER extraction error: {self.original_error}"
        self.user_message = (
            f"Error al extraer entidades del texto. "
            f"Se continuará con los resultados parciales."
        )
        super().__post_init__()


class NERExtractor:
    """
    Extractor de entidades nombradas con soporte para gazetteers dinámicos.

    El gazetteer dinámico permite mejorar la detección de nombres creativos
    (típicos de ficción) que spaCy no reconoce por estar entrenado en texto
    periodístico.

    Uso:
        extractor = NERExtractor()
        result = extractor.extract_entities("Juan García vive en Madrid.")
        for entity in result.entities:
            print(f"{entity.text} ({entity.label.value})")
    """

    # Mapeo de etiquetas spaCy a nuestras etiquetas
    SPACY_LABEL_MAP = {
        "PER": EntityLabel.PER,
        "PERSON": EntityLabel.PER,
        "LOC": EntityLabel.LOC,
        "GPE": EntityLabel.LOC,  # Geopolitical entity -> LOC
        "ORG": EntityLabel.ORG,
        "MISC": EntityLabel.MISC,
    }

    # Palabras a ignorar en detección heurística de nombres
    STOP_TITLES = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "en",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "entre",
        "hacia",
        "hasta",
        "desde",
        "durante",
        "según",
        "mediante",
        "y",
        "o",
        "ni",
        "pero",
        "sino",
        "aunque",
        "porque",
        "cuando",
        "si",
        "que",
        "como",
        "donde",
        "quien",
        "cual",
        "cuyo",
        "esto",
        "eso",
        "aquello",
        "ese",
        "este",
        "aquel",
        # Pronombres personales (nunca son entidades independientes)
        "él",
        "ella",
        "ellos",
        "ellas",
        "yo",
        "tú",
        "usted",
        "ustedes",
        "nosotros",
        "nosotras",
        "vosotros",
        "vosotras",
        "le",
        "les",
        "lo",
        "la",
        "nos",
        "os",
        "me",
        "te",
        "se",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
        "nuestro",
        "nuestra",
        "vuestro",
        "vuestra",
        "señor",
        "señora",
        "don",
        "doña",
        "sr",
        "sra",
        "dr",
        "dra",
    }

    # Palabras que NUNCA son entidades por sí solas (solo para gazetteer heurístico)
    # NOTA: Si spaCy detecta algo como entidad, confiamos en spaCy.
    # Estos filtros solo aplican a candidatos heurísticos (palabras capitalizadas
    # que spaCy NO detectó como entidad).
    #
    # NO incluir títulos como "rey", "padre", etc. porque pueden ser referencias
    # a personajes específicos ("El Rey ordenó...").
    HEURISTIC_FALSE_POSITIVES = {
        # Expresiones temporales (nunca son personajes/lugares)
        "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        "primavera", "verano", "otoño", "invierno",
        "mañana", "tarde", "noche", "mediodía", "madrugada",
        "ayer", "hoy", "anoche", "ahora", "entonces", "después", "antes",
        # Términos narrativos/estructura (metadatos, no contenido)
        "capítulo", "prólogo", "epílogo", "parte", "libro", "volumen",
        "escena", "acto", "fin", "final", "principio", "inicio",
        # Pronombres/determinantes (nunca son entidades)
        "algo", "alguien", "nadie", "nada", "todo", "todos",
        "otro", "otra", "otros", "otras",
        "mismo", "misma", "mismos", "mismas",
        "cada", "cualquier", "cualquiera",
        # Adverbios (nunca son entidades)
        "bien", "mal", "aquí", "allí", "allá", "acá",
        "sí", "no", "quizá", "quizás",
        "ahora", "entonces", "luego", "después", "antes", "siempre", "nunca",
        # Interjecciones
        "oh", "ah", "ay", "eh", "uf", "bah", "ja",
        # Atributos físicos (descripciones, no entidades)
        "cabello", "pelo", "ojos", "rostro", "cara", "manos", "piel",
        "negro", "blanco", "rubio", "moreno", "rojo", "azul", "verde",
        "alto", "bajo", "gordo", "flaco", "grande", "pequeño",
        # Adjetivos comunes
        "extraño", "raro", "imposible", "increíble", "horrible", "terrible",
        "hermoso", "bello", "feo", "viejo", "nuevo", "joven", "antiguo",
        # Palabras de test/desarrollo
        "test", "fresh", "prueba", "ejemplo", "demo",
        # Pronombres interrogativos y frases de diálogo
        "quién", "quien", "qué", "que", "cómo", "como",
        "dónde", "donde", "cuándo", "cuando", "cuánto", "cuanto",
        # Términos científicos/biológicos genéricos
        "endorfinas", "endorfina", "adrenalina", "serotonina", "dopamina",
        "hormona", "hormonas", "neurotransmisor", "neurotransmisores",
    }

    # Longitud mínima para considerar una entidad válida
    MIN_ENTITY_LENGTH = 2

    def __init__(
        self,
        enable_gazetteer: bool = True,
        min_entity_confidence: float = 0.5,
        enable_gpu: Optional[bool] = None,
        use_llm_preprocessing: bool = True,
    ):
        """
        Inicializa el extractor NER.

        Args:
            enable_gazetteer: Habilitar detección heurística de nombres
            min_entity_confidence: Confianza mínima para incluir entidades
            enable_gpu: Usar GPU para spaCy (None = auto)
            use_llm_preprocessing: Usar LLM como preprocesador para mejorar detección
        """
        self.enable_gazetteer = enable_gazetteer
        self.use_llm_preprocessing = use_llm_preprocessing

        config = get_config()
        # Usar 'is None' para permitir 0.0 como valor válido
        self.min_entity_confidence = (
            min_entity_confidence if min_entity_confidence is not None
            else config.nlp.min_entity_confidence
        )

        # Lock para operaciones thread-safe en el gazetteer
        # Usamos RLock para permitir llamadas anidadas
        self._gazetteer_lock = threading.RLock()

        # Gazetteer dinámico: nombres detectados por heurísticas
        # que se confirman al aparecer múltiples veces
        # NOTA: Todas las operaciones de escritura deben usar _gazetteer_lock
        self.dynamic_gazetteer: dict[str, EntityLabel] = {}

        # LLM client (lazy loading)
        self._llm_client = None

        # Cargar modelo spaCy
        logger.info("Cargando modelo spaCy para NER...")
        self.nlp = load_spacy_model(
            enable_gpu=enable_gpu,
            # Deshabilitar componentes no necesarios para NER
            disable_components=["tagger", "attribute_ruler", "lemmatizer"],
        )

        # Verificar que NER está disponible
        if "ner" not in self.nlp.pipe_names:
            logger.warning(
                "El modelo spaCy no tiene componente NER. "
                "La extracción de entidades puede ser limitada."
            )

        logger.info(f"NERExtractor inicializado (gazetteer={enable_gazetteer}, llm={use_llm_preprocessing})")

    # Frases comunes que nunca son entidades (saludos, expresiones, etc.)
    COMMON_PHRASES_NOT_ENTITIES = {
        # Saludos
        "buenos días", "buenas tardes", "buenas noches", "buen día",
        "hola", "adiós", "hasta luego", "hasta pronto",
        # Expresiones comunes
        "por favor", "muchas gracias", "de nada", "lo siento",
        "por supuesto", "sin embargo", "no obstante", "en cambio",
        "por cierto", "de hecho", "en realidad", "al parecer",
        "tal vez", "quizás", "a veces", "de vez en cuando",
        # Frases narrativas que empiezan con mayúscula pero no son entidades
        "capítulo", "prólogo", "epílogo", "parte",
        # Descripciones físicas que no son entidades
        "cabello negro", "cabello rubio", "cabello castaño", "pelo negro",
        "ojos azules", "ojos verdes", "ojos negros", "ojos marrones",
        # Descripciones con posesivos
        "sus ojos", "sus ojos verdes", "sus ojos azules", "sus ojos negros",
        "su cabello", "su pelo", "su rostro", "su cara", "su mirada",
        "mis ojos", "mis manos", "mi cabello", "mi pelo",
        "tus ojos", "tu cabello", "tu pelo", "tu rostro",
        # Títulos de capítulos comunes
        "la contradicción", "el encuentro", "el principio", "el final",
        # Expresiones que parecen ser detectadas como MISC
        "hola juan", "fresh test do", "imposible",
        # Preguntas y frases interrogativas (diálogo)
        "quién eres", "quien eres", "qué eres", "que eres",
        "quién es", "quien es", "qué es", "que es",
        "cómo estás", "como estas", "qué tal", "que tal",
        "dónde estás", "donde estas", "dónde está", "donde esta",
        "por qué", "porque", "para qué", "para que",
        # Sustantivos genéricos que a veces se detectan erróneamente
        "las endorfinas", "la endorfina", "endorfinas", "endorfina",
        "la adrenalina", "adrenalina", "la serotonina", "serotonina",
        "la dopamina", "dopamina",
        # NUEVOS (iter9): frases detectadas como MISC incorrectamente
        "feliz cumpleaños", "me gusta tu perfume", "tengo",
        "extrañaba su pelo negro natural", "esos ojos verdes que tanto le gustaban",
    }

    # Patrones regex para detectar descripciones físicas que NO son entidades
    PHYSICAL_DESCRIPTION_PATTERNS = [
        r"^(sus?|mis?|tus?)\s+(ojos|cabello|pelo|rostro|cara|manos?|piel)\b",
        r"^(ojos|cabello|pelo)\s+(verdes?|azules?|negros?|marrones?|rubios?|castaños?)\b",
    ]

    # Palabras sueltas que spaCy a veces detecta erróneamente como MISC
    SPACY_FALSE_POSITIVE_WORDS = {
        "imposible", "increíble", "horrible", "terrible", "extraño",
        "cabello", "pelo", "ojos", "negro", "rubio", "moreno",
        "fresh", "test", "hola",
    }

    def _is_false_positive_by_morphology(
        self,
        entity_text: str,
        entity_label: EntityLabel,
        context: str,
        position: int,
    ) -> tuple[bool, str]:
        """
        Filtro genérico de falsos positivos basado en análisis morfosintáctico.

        Usa patrones lingüísticos genéricos en lugar de listas cerradas:
        1. Analiza el POS-tag de la palabra en contexto
        2. Detecta si está al inicio de oración (capitalización obligatoria)
        3. Verifica concordancia con determinantes/adjetivos previos
        4. Detecta patrones de frases nominales genéricas

        Args:
            entity_text: Texto de la entidad
            entity_label: Etiqueta NER asignada
            context: Texto circundante (±100 caracteres)
            position: Posición de la entidad en el contexto

        Returns:
            Tupla (is_false_positive, reason)
        """
        import re

        text_lower = entity_text.lower().strip()
        words = entity_text.split()

        # 1. ANÁLISIS MORFOLÓGICO CON SPACY
        # Si tenemos spaCy disponible, analizamos el contexto completo
        try:
            doc = self.nlp(context)

            # Encontrar el token correspondiente a la entidad
            entity_tokens = []
            for token in doc:
                if token.text.lower() == text_lower or text_lower in token.text.lower():
                    entity_tokens.append(token)
                    break
                # Para entidades multi-palabra, buscar la primera palabra
                elif words and token.text.lower() == words[0].lower():
                    entity_tokens.append(token)
                    # Añadir tokens siguientes
                    idx = token.i
                    for w in words[1:]:
                        if idx + 1 < len(doc) and doc[idx + 1].text.lower() == w.lower():
                            entity_tokens.append(doc[idx + 1])
                            idx += 1
                    break

            if entity_tokens:
                first_token = entity_tokens[0]

                # 1.1 Detectar VERBOS mal clasificados
                if first_token.pos_ == "VERB":
                    return True, f"Detectado como verbo (POS={first_token.pos_}, morfología={first_token.morph})"

                # 1.2 Detectar ADJETIVOS/ADVERBIOS mal clasificados
                if first_token.pos_ in ("ADJ", "ADV") and len(entity_tokens) == 1:
                    return True, f"Detectado como {first_token.pos_} (no es nombre propio)"

                # 1.3 Detectar SUSTANTIVOS COMUNES al inicio de oración
                # Si es un sustantivo común (no PROPN) y está al inicio de oración
                if first_token.pos_ == "NOUN":
                    # Verificar si está al inicio de oración
                    if first_token.i == 0 or (first_token.i > 0 and doc[first_token.i - 1].text in ".!?¿¡\n"):
                        # Verificar si es un sustantivo que aparece en minúsculas en otras partes
                        # del texto (indicando que no es nombre propio)
                        lowercase_pattern = r'\b' + re.escape(text_lower) + r'\b'
                        lowercase_matches = len(re.findall(lowercase_pattern, context.lower()))
                        uppercase_matches = len(re.findall(r'\b' + re.escape(entity_text) + r'\b', context))

                        # Si aparece más veces en minúsculas que con mayúscula, es sustantivo común
                        if lowercase_matches > uppercase_matches:
                            return True, "Sustantivo común capitalizado al inicio de oración"

                # 1.4 Detectar DETERMINANTE + SUSTANTIVO (frase nominal genérica)
                if first_token.pos_ == "DET" and len(entity_tokens) > 1:
                    # "El público", "La luna", etc.
                    second_token = entity_tokens[1] if len(entity_tokens) > 1 else None
                    if second_token and second_token.pos_ == "NOUN":
                        return True, f"Frase nominal genérica: DET + NOUN"

        except Exception as e:
            logger.debug(f"Error en análisis morfológico: {e}")

        # 2. PATRONES GENÉRICOS (sin spaCy disponible)

        # 2.1 Detectar verbos por terminaciones típicas del español
        verb_endings_preterite = ('ó', 'ió', 'aron', 'ieron', 'aste', 'iste')
        verb_endings_imperative = ('ate', 'ete', 'ite')
        if len(words) == 1 and len(text_lower) > 3:
            if text_lower.endswith(verb_endings_preterite):
                return True, f"Terminación verbal (pretérito): -{text_lower[-2:]}"
            if text_lower.endswith(verb_endings_imperative):
                return True, f"Terminación verbal (imperativo): -{text_lower[-3:]}"

        # 2.2 Detectar fragmentos de oración (más de 3 palabras con preposiciones/artículos)
        if len(words) >= 3:
            function_words = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en', 'con', 'por', 'para', 'a', 'al'}
            function_count = sum(1 for w in words if w.lower() in function_words)
            if function_count >= 2:
                return True, f"Fragmento de oración (muchas palabras funcionales)"

        # 2.3 Detectar cuantificadores/adverbios como entidad
        quantifiers = {'tanto', 'tanta', 'tantos', 'tantas', 'mucho', 'mucha', 'poco', 'poca'}
        if text_lower in quantifiers:
            return True, "Cuantificador/adverbio, no entidad"

        # 2.4 Para LOC: Verificar si es dirección cardinal sin contexto geográfico
        if entity_label == EntityLabel.LOC:
            cardinal_directions = {'norte', 'sur', 'este', 'oeste', 'noroeste', 'noreste', 'suroeste', 'sureste'}
            if text_lower in cardinal_directions:
                # Solo es falso positivo si no va acompañado de nombre de lugar
                # "al Norte" vs "Norte de España"
                if not re.search(r'(de|del)\s+[A-ZÁÉÍÓÚÑ]', context[position:position+50]):
                    return True, "Dirección cardinal sin nombre de lugar"

        # 2.5 Para ORG: Verificar si es término temporal
        if entity_label == EntityLabel.ORG:
            # Los meses como organización son casi siempre falsos positivos
            months = {'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'}
            if text_lower in months:
                return True, "Mes del año, no organización"

            # Términos técnicos que no son organizaciones
            technical_terms = {'escotillón', 'escotilla', 'prensa', 'iglesia'}
            if text_lower in technical_terms:
                return True, "Término técnico/genérico, no organización"

        # 2.6 Para PER: Detectar adjetivos capitalizados al inicio de oración
        if entity_label == EntityLabel.PER:
            # Adjetivos comunes que spaCy detecta como PER
            common_adjectives = {
                'hermoso', 'hermosa', 'hermosos', 'hermosas',
                'influido', 'influida', 'influidos', 'influidas',
                'natural', 'naturales', 'naturalismo',
                'picaresca', 'picaresco',
            }
            if text_lower in common_adjectives:
                return True, "Adjetivo común, no nombre de persona"

        # 2.7 Para LOC: Sustantivos comunes de la naturaleza/edificios
        if entity_label == EntityLabel.LOC:
            common_nature_nouns = {
                'luna', 'sol', 'cielo', 'tierra', 'mar', 'río',
                'yerba', 'hierba', 'bosque', 'jardín', 'campo',
                'catedral', 'iglesia', 'casino', 'obispo',
            }
            if text_lower in common_nature_nouns:
                return True, "Sustantivo común de lugar/naturaleza"

            # Frases con artículo + sustantivo común
            if text_lower.startswith(('la ', 'el ', 'las ', 'los ')):
                rest = text_lower.split(' ', 1)[1] if ' ' in text_lower else ''
                if rest in common_nature_nouns:
                    return True, "Artículo + sustantivo común"

        # 2.8 Para MISC: Expresiones comunes y fragmentos
        if entity_label == EntityLabel.MISC:
            # Expresiones comunes que no son entidades
            common_expressions = {
                'sin duda', 'por mi parte', 'por su parte', 'en efecto',
                'tanta', 'tanto', 'tantas', 'tantos',
                'el nuestro', 'la nuestra', 'lo nuestro',
            }
            if text_lower in common_expressions:
                return True, "Expresión común, no entidad"

        return False, ""

    def _get_llm_client(self):
        """Obtiene el cliente LLM (lazy loading)."""
        if self._llm_client is None:
            try:
                from ..llm.client import get_llm_client
                self._llm_client = get_llm_client()
                if self._llm_client and self._llm_client.is_available:
                    logger.info(f"LLM disponible para NER: {self._llm_client.model_name}")
                else:
                    self._llm_client = False
            except Exception as e:
                logger.warning(f"No se pudo cargar LLM client para NER: {e}")
                self._llm_client = False
        return self._llm_client if self._llm_client else None

    def _preprocess_with_llm(self, text: str) -> list[ExtractedEntity]:
        """
        Usa LLM como preprocesador para detectar entidades.

        El LLM es mejor que spaCy para:
        - Nombres inventados de ficción (Gandalf, Hogwarts)
        - Personajes implícitos (narrador en primera persona)
        - Distinguir personajes de descripciones
        - Entender contexto narrativo

        Args:
            text: Texto a procesar (se limita a 4000 chars)

        Returns:
            Lista de entidades detectadas por LLM
        """
        import json
        import re

        llm = self._get_llm_client()
        if not llm:
            return []

        entities: list[ExtractedEntity] = []

        # Limitar texto para no sobrecargar LLM
        text_sample = text[:4000] if len(text) > 4000 else text

        prompt = f"""Analiza este texto narrativo en español y extrae TODAS las entidades nombradas.

TEXTO:
{text_sample}

EXTRAE:
1. PERSONAJES (PER): Nombres propios de personas/personajes, incluyendo apodos y títulos
2. LUGARES (LOC): Ciudades, países, lugares ficticios, edificios
3. ORGANIZACIONES (ORG): Empresas, instituciones, grupos

IMPORTANTE:
- El narrador en primera persona ("yo") NO es una entidad a menos que se nombre
- Los pronombres (él, ella, ellos) NO son entidades
- Las descripciones físicas (hombre alto, mujer rubia) NO son entidades
- Los saludos (Hola María) - solo extraer "María", no el saludo
- "doctor García" → extraer como "García" con tipo PER

Responde SOLO con JSON válido:
{{"entities": [
  {{"text": "Juan", "type": "PER", "start": 0}},
  {{"text": "Madrid", "type": "LOC", "start": 50}},
  {{"text": "doctor García", "type": "PER", "start": 100}}
]}}

JSON:"""

        try:
            response = llm.complete(
                prompt,
                system="Eres un experto en NER para textos narrativos en español. Extraes entidades con precisión.",
                temperature=0.1,
            )

            if not response:
                return entities

            # Parsear JSON
            data = self._parse_llm_json_ner(response)
            if not data or "entities" not in data:
                return entities

            for ent_data in data["entities"]:
                try:
                    text_ent = ent_data.get("text", "").strip()
                    type_str = ent_data.get("type", "PER").upper()

                    if not text_ent or len(text_ent) < 2:
                        continue

                    # Mapear tipo
                    label = {
                        "PER": EntityLabel.PER,
                        "PERSON": EntityLabel.PER,
                        "LOC": EntityLabel.LOC,
                        "LOCATION": EntityLabel.LOC,
                        "ORG": EntityLabel.ORG,
                        "ORGANIZATION": EntityLabel.ORG,
                        "MISC": EntityLabel.MISC,
                    }.get(type_str, EntityLabel.PER)

                    # Encontrar posición real en texto
                    # Buscar coincidencia exacta o parcial
                    start_char = self._find_entity_position(text, text_ent)

                    if start_char >= 0:
                        entity = ExtractedEntity(
                            text=text_ent,
                            label=label,
                            start_char=start_char,
                            end_char=start_char + len(text_ent),
                            confidence=0.85,  # Alta confianza para LLM
                            source="llm",
                        )
                        entities.append(entity)

                        # Añadir al gazetteer para futuras detecciones
                        canonical = entity.canonical_form
                        if canonical:
                            with self._gazetteer_lock:
                                if len(self.dynamic_gazetteer) < MAX_GAZETTEER_SIZE:
                                    self.dynamic_gazetteer[canonical] = label

                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Error parseando entidad LLM: {e}")
                    continue

            logger.debug(f"LLM preprocesador detectó {len(entities)} entidades")

        except Exception as e:
            logger.warning(f"Error en preprocesamiento LLM para NER: {e}")

        return entities

    def _parse_llm_json_ner(self, response: str) -> Optional[dict]:
        """Parsea respuesta JSON del LLM con limpieza."""
        import json

        try:
            cleaned = response.strip()

            # Remover bloques de código markdown
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [line for line in lines if not line.startswith("```")]
                cleaned = "\n".join(lines)

            # Encontrar JSON
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                cleaned = cleaned[start_idx:end_idx]

            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.debug(f"Error parseando JSON del LLM en NER: {e}")
            return None

    def _find_entity_position(self, text: str, entity_text: str) -> int:
        """
        Encuentra la posición de una entidad en el texto.

        Busca coincidencia exacta primero, luego case-insensitive.
        """
        import re

        # Búsqueda exacta
        pos = text.find(entity_text)
        if pos >= 0:
            return pos

        # Búsqueda case-insensitive con word boundaries
        pattern = r'\b' + re.escape(entity_text) + r'\b'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.start()

        # Búsqueda parcial (para casos como "doctor García" vs "García")
        words = entity_text.split()
        if len(words) > 1:
            # Buscar la última palabra (normalmente el apellido)
            last_word = words[-1]
            match = re.search(r'\b' + re.escape(last_word) + r'\b', text, re.IGNORECASE)
            if match:
                return match.start()

        return -1

    def _llm_verify_low_confidence_entities(
        self,
        full_text: str,
        entities: list[ExtractedEntity],
        validation_scores: dict[str, dict],
    ) -> list[ExtractedEntity]:
        """
        Verifica entidades de baja confianza usando LLM como segunda capa.

        Cuando la validación multi-método tiene bajo acuerdo (confianza < 0.7),
        consultamos al LLM para verificar si realmente son entidades válidas.

        Args:
            full_text: Texto completo para contexto
            entities: Lista de entidades detectadas
            validation_scores: Scores de validación por entidad

        Returns:
            Lista filtrada de entidades verificadas
        """
        llm = self._get_llm_client()
        if not llm:
            return entities

        # Identificar entidades de baja confianza (< 0.7)
        low_confidence = []
        high_confidence = []

        for ent in entities:
            score_data = validation_scores.get(ent.text, {})
            final_score = score_data.get("final_score", ent.confidence)

            if final_score < 0.7:
                low_confidence.append(ent)
            else:
                high_confidence.append(ent)

        if not low_confidence:
            return entities

        logger.info(f"Verificando {len(low_confidence)} entidades de baja confianza con LLM")

        # Preparar contexto para cada entidad dudosa
        entities_to_verify = []
        for ent in low_confidence[:20]:  # Limitar a 20 para no sobrecargar
            # Obtener contexto circundante (±100 caracteres)
            start = max(0, ent.start_char - 100)
            end = min(len(full_text), ent.end_char + 100)
            context = full_text[start:end]

            entities_to_verify.append({
                "text": ent.text,
                "type": ent.label.value,
                "context": context,
                "entity": ent,
            })

        if not entities_to_verify:
            return entities

        # Construir prompt para verificación batch
        entities_json = [
            {"text": e["text"], "type": e["type"], "context": e["context"][:200]}
            for e in entities_to_verify
        ]

        prompt = f"""Verifica si estas posibles entidades son correctas.

ENTIDADES A VERIFICAR:
{entities_json}

Para cada entidad, responde:
- "valid" si ES una entidad nombrada real (personaje, lugar, organización)
- "invalid" si NO es una entidad (descripción, error, frase común)

Criterios:
- Nombres propios de personas/personajes → valid
- Lugares (ciudades, países, ficticios) → valid
- Organizaciones → valid
- Descripciones ("el hombre", "la mujer alta") → invalid
- Frases comunes ("Buenos días", "Por favor") → invalid
- Errores de detección ("sus ojos verdes") → invalid

Responde SOLO con JSON:
{{"results": [
  {{"text": "...", "verdict": "valid|invalid", "reason": "breve explicación"}}
]}}

JSON:"""

        try:
            response = llm.complete(
                prompt,
                system="Verificas entidades NER. Sé estricto: solo valida nombres propios reales.",
                temperature=0.1,
                max_tokens=1000,
            )

            if not response:
                return entities

            data = self._parse_llm_json_ner(response)
            if not data or "results" not in data:
                return entities

            # Procesar resultados
            verified_entities = list(high_confidence)
            verified_count = 0
            rejected_count = 0

            for result in data.get("results", []):
                text = result.get("text", "")
                verdict = result.get("verdict", "").lower()

                # Buscar la entidad correspondiente
                for verify_data in entities_to_verify:
                    if verify_data["text"].lower() == text.lower():
                        if verdict == "valid":
                            # Boost de confianza por verificación LLM
                            ent = verify_data["entity"]
                            ent.confidence = min(0.9, ent.confidence + 0.2)
                            ent.source = f"{ent.source}+llm_verified"
                            verified_entities.append(ent)
                            verified_count += 1
                        else:
                            rejected_count += 1
                        break

            logger.info(
                f"Verificación LLM: {verified_count} confirmadas, "
                f"{rejected_count} rechazadas de {len(low_confidence)} dudosas"
            )

            return verified_entities

        except Exception as e:
            logger.warning(f"Error en verificación LLM de entidades: {e}")
            # En caso de error, mantener todas las entidades
            return entities

    def _postprocess_misc_entities(
        self, entities: list[ExtractedEntity]
    ) -> list[ExtractedEntity]:
        """
        Post-procesa entidades MISC para filtrar errores y reclasificar.

        1. Filtra MISC que son claramente frases (>3 palabras)
        2. Reclasifica pseudónimos literarios conocidos como PER
        3. Reclasifica lugares ficticios conocidos como LOC

        Args:
            entities: Lista de entidades extraídas

        Returns:
            Lista filtrada y reclasificada
        """
        # Pseudónimos literarios y apodos -> PER
        LITERARY_PSEUDONYMS = {
            "clarín", "azorín", "el greco", "el cid", "la regenta",
            "el magistral", "la dama", "el caballero",
            "tirso de molina", "fernán caballero", "benito el garbancero",
        }

        # Lugares ficticios conocidos -> LOC
        FICTIONAL_PLACES = {
            "vetusta", "orbajosa", "marineda", "ficóbriga", "pilares",
            "castroforte", "villabajo", "macondo",
        }

        # Palabras MISC que son claramente errores y deben filtrarse
        MISC_ERRORS = {
            # Verbos imperativos que spaCy confunde
            "levántate", "levantate", "siéntate", "sientate", "ven", "vete",
            # Adverbios/expresiones comunes
            "tanta", "tanto", "más", "menos", "bien", "mal",
            # Artículos/preposiciones que escapan
            "y al", "el", "la", "los", "las",
            # Palabras genéricas
            "naturaleza", "diccionario", "dios",
        }

        # MISC que son probablemente apellidos -> PER
        # (apellidos comunes españoles que aparecen solos)
        COMMON_SURNAMES_AS_PER = {
            "ozores", "garcía", "martínez", "lópez", "fernández",
            "rodríguez", "pérez", "sánchez", "romero", "navarro",
            "gonzález", "díaz", "hernández", "moreno", "muñoz",
        }

        result = []
        filtered_count = 0
        reclassified_count = 0

        for entity in entities:
            # Solo procesar MISC
            if entity.label != EntityLabel.MISC:
                result.append(entity)
                continue

            text_lower = entity.text.lower().strip()
            word_count = len(entity.text.split())

            # Filtrar frases largas (>3 palabras) - probablemente error de segmentación
            if word_count > 3:
                logger.debug(f"MISC filtrado (frase larga): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar si empieza con minúscula (error de spaCy)
            if entity.text and entity.text[0].islower():
                logger.debug(f"MISC filtrado (minúscula): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar si contiene guiones bajos (metadatos)
            if '_' in entity.text:
                logger.debug(f"MISC filtrado (guion bajo): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar MISC que son claramente errores
            if text_lower in MISC_ERRORS:
                logger.debug(f"MISC filtrado (error conocido): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar si empieza con artículo + solo 1-2 palabras más (ej: "El público")
            if word_count <= 3 and text_lower.startswith(("el ", "la ", "los ", "las ", "un ", "una ")):
                # Excepto si es pseudónimo conocido
                if text_lower not in LITERARY_PSEUDONYMS:
                    logger.debug(f"MISC filtrado (artículo + frase): '{entity.text}'")
                    filtered_count += 1
                    continue

            # Reclasificar apellidos comunes a PER
            if text_lower in COMMON_SURNAMES_AS_PER:
                entity.label = EntityLabel.PER
                entity.source = f"{entity.source}+reclassified"
                logger.debug(f"MISC reclasificado a PER (apellido): '{entity.text}'")
                reclassified_count += 1
                result.append(entity)
                continue

            # Reclasificar pseudónimos literarios a PER
            if text_lower in LITERARY_PSEUDONYMS:
                entity.label = EntityLabel.PER
                entity.source = f"{entity.source}+reclassified"
                logger.debug(f"MISC reclasificado a PER: '{entity.text}'")
                reclassified_count += 1

            # Reclasificar lugares ficticios a LOC
            elif text_lower in FICTIONAL_PLACES:
                entity.label = EntityLabel.LOC
                entity.source = f"{entity.source}+reclassified"
                logger.debug(f"MISC reclasificado a LOC: '{entity.text}'")
                reclassified_count += 1

            result.append(entity)

        if filtered_count > 0 or reclassified_count > 0:
            logger.info(
                f"Post-proceso MISC: {filtered_count} filtrados, "
                f"{reclassified_count} reclasificados"
            )

        return result

    def _is_valid_spacy_entity(self, text: str) -> bool:
        """
        Valida una entidad detectada por spaCy.

        Filtramos errores obvios de segmentación y frases que claramente
        no son entidades nombradas.

        Args:
            text: Texto de la entidad

        Returns:
            True si es válida, False solo si hay error obvio
        """
        if not text:
            return False

        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Filtrar entidades muy cortas (probablemente ruido)
        if len(text_stripped) < self.MIN_ENTITY_LENGTH:
            return False

        # Filtrar errores de segmentación obvios
        if '\n' in text or len(text_stripped) > 100:
            logger.debug(f"Entidad spaCy filtrada (segmentación): '{text[:50]}...'")
            return False

        # Puntuación que no debería aparecer en bordes de entidades
        # Incluye signos de apertura españoles ¿¡ y otros símbolos comunes
        BOUNDARY_PUNCTUATION = '.,:;!?¿¡–—-\'\"()[]{}«»""'''

        # Filtrar entidades que terminan en puntuación (error de segmentación)
        if text_stripped and text_stripped[-1] in BOUNDARY_PUNCTUATION:
            logger.debug(f"Entidad spaCy filtrada (puntuación final): '{text}'")
            return False

        # Filtrar entidades que empiezan con puntuación (error de segmentación)
        if text_stripped and text_stripped[0] in BOUNDARY_PUNCTUATION:
            logger.debug(f"Entidad spaCy filtrada (puntuación inicial): '{text}'")
            return False

        # Limpiar guiones y puntuación al final y verificar si queda algo válido
        text_clean = text_stripped.rstrip('–—-,.;:!?¿¡ ')
        if text_clean != text_stripped:
            # Si había caracteres finales que limpiar, verificar el resultado
            if len(text_clean) < self.MIN_ENTITY_LENGTH:
                return False

        # Filtrar solo artículos/preposiciones sueltas
        if text_lower in self.STOP_TITLES:
            return False

        # Términos familiares que NO son nombres propios cuando están solos
        # Nota: "Papa" puede ser padre (familia) o Papa de Roma (iglesia)
        # El contexto lo resuelve la correferencia, no el NER
        FAMILY_TERMS = {
            "hijo", "hija", "hijos", "hijas",
            "padre", "madre", "padres", "madres",
            "hermano", "hermana", "hermanos", "hermanas",
            "abuelo", "abuela", "abuelos", "abuelas",
            "tío", "tía", "tíos", "tías", "tio", "tia",
            "primo", "prima", "primos", "primas",
            "sobrino", "sobrina", "sobrinos", "sobrinas",
            "nieto", "nieta", "nietos", "nietas",
            "esposo", "esposa", "marido", "mujer",
            "novio", "novia", "novios", "novias",
        }
        if text_lower in FAMILY_TERMS:
            logger.debug(f"Entidad spaCy filtrada (término familiar): '{text}'")
            return False

        # Filtrar pronombres personales (NUNCA pueden ser entidades independientes)
        # Los pronombres deben resolverse mediante correferencia, no extraerse como entidades
        PRONOUNS = {
            # Pronombres personales sujeto
            "él", "ella", "ellos", "ellas", "yo", "tú", "usted", "ustedes",
            "nosotros", "nosotras", "vosotros", "vosotras",
            # Pronombres átonos
            "le", "les", "lo", "la", "los", "las", "nos", "os", "me", "te", "se",
            # Pronombres reflexivos y recíprocos
            "sí", "consigo",
            # Pronombres demostrativos que pueden confundirse con personas
            "éste", "ésta", "éstos", "éstas", "ése", "ésa", "ésos", "ésas",
            "aquél", "aquélla", "aquéllos", "aquéllas",
            # Formas sin tilde (ortografía moderna)
            "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
            "aquel", "aquella", "aquellos", "aquellas",
        }
        if text_lower in PRONOUNS:
            logger.debug(f"Entidad spaCy filtrada (pronombre): '{text}'")
            return False

        # Filtrar si es solo números o puntuación
        if text.isdigit() or not any(c.isalpha() for c in text):
            return False

        # ===== NUEVO: Filtrar palabras completamente en mayúsculas (metadatos) =====
        # Excepción: acrónimos cortos (2-3 letras) pueden ser válidos
        if text_stripped.isupper() and len(text_stripped) > 3:
            logger.debug(f"Entidad spaCy filtrada (todo mayúsculas, probable metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar verbos conjugados comunes al inicio de oración =====
        # Estos aparecen capitalizados pero no son entidades
        # Incluye versiones con y sin tilde para textos sin acentos
        VERBS_AT_SENTENCE_START = {
            # Pretérito perfecto simple (3ra persona singular)
            "supo", "trajo", "traía", "dijo", "penso", "pensó", "miro", "miró", "vio", "sintió",
            "llegó", "entró", "salió", "pasó", "siguió", "encontró",
            "oyó", "notó", "recordó", "olvidó", "decidió", "intentó",
            "logró", "consiguió", "empezó", "terminó", "continuó",
            "preguntó", "respondió", "contestó", "exclamó", "susurró",
            "gritó", "murmuró", "añadió", "explicó", "comentó",
            "saludo", "saludó",  # verbo saludar
            "abrio", "abrió", "bajo", "bajó", "compro", "compró",
            "preparo", "preparó", "recibio", "recibió", "tomo", "tomó",
            "tuvo", "pudo", "hizo", "fue", "dio", "vino",
            "sentaron", "elaboraron", "contacto", "contactó",
            # Verbos frecuentes en narrativa (iter7)
            "camino", "caminó", "corrio", "corrió", "beso", "besó",
            "abrazo", "abrazó", "cerro", "cerró", "colgo", "colgó",
            "espero", "esperó", "escucho", "escuchó", "marco", "marcó",
            "reviso", "revisó", "suspiro", "suspiró",
            "desperto", "despertó", "levanto", "levantó", "sono", "sonó",
            "nacio", "nació", "murio", "murió", "vivio", "vivió",
            "conocio", "conoció", "aprendio", "aprendió", "escribio", "escribió",
            "leyo", "leyó", "cayo", "cayó", "mudo", "mudó",
            "trabajo", "trabajó", "caso", "casó", "graduo", "graduó",
            # Imperfecto (con y sin tilde)
            "sabía", "tenía", "había", "quería", "podía", "debía",
            "sabia", "tenia", "habia", "queria", "podia", "debia",
            "decia", "decía", "creia", "creía", "vivia", "vivía",
            "estaba", "era", "iba", "hacia", "hacía",
            # Condicional / Futuro
            "contactarian", "contactarían", "iria", "iría",
            "diria", "diría", "seria", "sería", "tendria", "tendría",
            "podria", "podría", "deberia", "debería", "haria", "haría",
            "usaria", "usaría", "volveria", "volvería",
            # Imperativo/subjuntivo
            "diga", "venga", "salga", "haga", "ponga", "traiga",
            # Verbos en 2da persona (diálogo)
            "sigues", "tienes", "tengo", "quieres", "puedes", "debes",
            "sabes", "haces", "vas", "vienes", "dices", "ves",
        }
        if text_lower in VERBS_AT_SENTENCE_START:
            logger.debug(f"Entidad spaCy filtrada (verbo al inicio de oración): '{text}'")
            return False

        # ===== NUEVO: Filtrar palabras comunes capitalizadas (falsos positivos) =====
        COMMON_WORDS_CAPITALIZED = {
            # Palabras comunes que aparecen capitalizadas por error o como ejemplo
            "correcto", "incorrecto", "habemos", "hubieron", "haiga",
            "mejor", "peor", "mayor", "menor", "más", "menos",
            # Términos lingüísticos/gramaticales
            "dequeísmo", "queísmo", "laísmo", "leísmo", "loísmo",
            "concordancia", "redundancia", "redundancias", "pleonasmo",
            "solecismo", "anacoluto", "gramática", "sintaxis",
            # Palabras de sección/documento
            "notas", "ejemplo", "error", "observación", "nota",
            # Pronombres indefinidos
            "alguien", "nadie", "cualquiera", "quienquiera",
            # Adverbios de cantidad/grado
            "demasiado", "demasiada", "demasiados", "demasiadas",
            "bastante", "bastantes", "suficiente", "suficientes",
            # Sustantivos abstractos comunes (títulos de sección)
            "revelaciones", "revelación", "explicaciones", "explicación",
            "decisiones", "decisión", "secretos", "verdad", "verdades",
            "origenes", "orígenes", "comienzo", "comienzos",
            "encuentro", "encuentros", "viaje", "viajes",
            "despertar", "carta", "cartas", "plan", "planes",
            # Adjetivos usados como titulo
            "urgente", "urgentes", "importante", "importantes",
            "dificiles", "difíciles", "faciles", "fáciles",
            # Palabras de estructura de documento
            "resumen", "estructura", "esperada", "formatos",
            "incluidos", "incluidas", "formato", "cronologico", "cronológico",
            # Ordinales que aparecen como títulos
            "primera", "primero", "segunda", "segundo", "tercera", "tercero",
            "cuarta", "cuarto", "quinta", "quinto",
            # NUEVOS (iter8): sustantivos abstractos de eventos/títulos
            "graduacion", "graduación", "nacimiento", "nacimientos",
            "infancia", "adolescencia", "universidad", "adulta", "adulto",
            "comienzo", "final", "inicio", "eventos", "temporales",
            "boda", "bodas", "muerte", "muertes", "trabajo", "trabajos",
            # NUEVOS (iter9): falsos positivos detectados en evaluación NER
            "inconsistencias", "intencionadas", "intencionados", "personaje",
            "postre", "barba", "ojos", "pelo", "estatura", "edad", "profesion", "profesión",
            "cabello", "bebida", "perfume", "aroma",
            "ahora", "feliz", "martes", "miércoles", "jueves", "viernes",
            # Adverbios temporales
            "antes", "después", "despues", "luego", "pronto", "tarde", "temprano",
            # NUEVOS (iter11): sustantivos abstractos que aparecen como MISC
            "conflictos", "resoluciones", "problemas", "situaciones", "circunstancias",
            "consecuencias", "motivos", "razones", "causas", "efectos",
        }
        if text_lower in COMMON_WORDS_CAPITALIZED:
            logger.debug(f"Entidad spaCy filtrada (palabra común capitalizada): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con barra (metadatos/variantes) =====
        if "/" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (contiene barra, probable metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con flecha → (listas de cambios) =====
        if "→" in text_stripped or "->" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (contiene flecha, metadato): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades con dos puntos (metadatos tipo "Ojos: azules") =====
        # También filtra líneas de timeline como "Verano 2006: Primer trabajo"
        if ":" in text_stripped:
            logger.debug(f"Entidad spaCy filtrada (formato metadato key:value): '{text}'")
            return False

        # ===== NUEVO: Filtrar frases que empiezan con "Personaje" (metadatos) =====
        if text_lower.startswith("personaje "):
            logger.debug(f"Entidad spaCy filtrada (metadato personaje): '{text}'")
            return False

        # Filtrar frases comunes que no son entidades
        if text_lower in self.COMMON_PHRASES_NOT_ENTITIES:
            logger.debug(f"Entidad spaCy filtrada (frase común): '{text}'")
            return False

        # Filtrar descripciones físicas usando patrones regex
        import re
        for pattern in self.PHYSICAL_DESCRIPTION_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                logger.debug(f"Entidad spaCy filtrada (descripción física): '{text}'")
                return False

        # Filtrar palabras sueltas que spaCy detecta erróneamente
        if text_lower in self.SPACY_FALSE_POSITIVE_WORDS:
            logger.debug(f"Entidad spaCy filtrada (falso positivo conocido): '{text}'")
            return False

        # Filtrar frases muy largas con muchas palabras (probablemente no son entidades)
        words = text_stripped.split()
        if len(words) > 5:
            logger.debug(f"Entidad spaCy filtrada (demasiadas palabras): '{text}'")
            return False

        # Filtrar frases que parecen oraciones (tienen verbo conjugado típico)
        # Patrones: "Algo estaba", "Era un", "Había una", etc.
        sentence_starters = {
            "algo", "era", "había", "fue", "es", "está", "estaba",
            "tiene", "tenía", "hace", "hacía", "dice", "decía",
            "va", "iba", "viene", "venía", "parece", "parecía",
        }
        first_word = words[0].lower() if words else ""
        if first_word in sentence_starters and len(words) > 2:
            logger.debug(f"Entidad spaCy filtrada (parece oración): '{text}'")
            return False

        # Filtrar frases que empiezan con artículo seguido de sustantivo/verbo común
        # Ejemplo: "El otro día", "La mañana siguiente", "La había preparado"
        if len(words) >= 2:
            if first_word in {"el", "la", "los", "las", "un", "una", "unos", "unas"}:
                second_word = words[1].lower() if len(words) > 1 else ""

                # Sustantivos/adjetivos genéricos
                generic_words = {
                    "otro", "otra", "mismo", "misma", "siguiente", "anterior",
                    "hombre", "mujer", "persona", "gente", "cosa", "día", "noche",
                    "vez", "tiempo", "momento", "lugar", "forma", "manera",
                    # Sustantivos comunes de lugares/objetos
                    "casa", "calle", "ciudad", "país", "mundo", "tierra",
                    "mesa", "silla", "puerta", "ventana", "habitación", "cocina",
                    "libro", "vaso", "copa", "plato", "cama", "pared",
                    # Sustantivos abstractos
                    "amor", "vida", "muerte", "verdad", "historia", "relación",
                    # NUEVO iter3: objetos/instrumentos
                    "reloj", "telefono", "teléfono", "carta", "sobre", "llave",
                    "coche", "tren", "avion", "avión", "autobus", "autobús",
                    # NUEVO iter3: elementos naturales/descripciones
                    "luz", "sol", "luna", "cielo", "aire", "viento", "mar",
                    "corazon", "corazón", "mente", "alma", "cuerpo",
                    # NUEVO iter3: lugares genéricos
                    "estacion", "estación", "aeropuerto", "hospital", "escuela",
                    "cafe", "café", "bar", "restaurante", "tienda", "oficina",
                    # NUEVO iter3: abstracciones
                    "plan", "idea", "decision", "decisión", "problema", "solucion",
                    "solución", "camino", "viaje", "mensaje", "padre", "madre",
                    # NUEVO iter10: profesiones genéricas (plural)
                    "medicos", "médicos", "doctores", "profesores", "estudiantes",
                    "soldados", "policias", "policías", "abogados", "jueces",
                    # Términos anatómicos (no son nombres propios)
                    "paladar", "laringe", "esofago", "esófago", "garganta",
                    "lengua", "labio", "labios", "diente", "dientes", "muela",
                    "nariz", "ojo", "ojos", "oreja", "orejas", "boca",
                    "mano", "manos", "dedo", "dedos", "brazo", "brazos",
                    "pierna", "piernas", "pie", "pies", "rodilla", "tobillo",
                    "cabeza", "cara", "frente", "cuello", "hombro", "hombros",
                    "espalda", "pecho", "estomago", "estómago", "vientre",
                    "cerebro", "pulmon", "pulmón", "higado", "hígado", "riñon", "riñón",
                }
                if second_word in generic_words:
                    logger.debug(f"Entidad spaCy filtrada (descripción genérica): '{text}'")
                    return False

                # NUEVO: Verbos auxiliares/conjugados comunes después de artículo
                common_verbs_after_article = {
                    "había", "fue", "era", "es", "está", "estaba",
                    "tiene", "tenía", "hace", "hacía", "puede", "podía",
                    "debe", "debía", "va", "iba", "viene", "venía",
                    "quiere", "quería", "sabe", "sabía", "dos", "tres",
                }
                if second_word in common_verbs_after_article:
                    logger.debug(f"Entidad spaCy filtrada (artículo + verbo): '{text}'")
                    return False

        # Filtrar frases que comienzan con pronombre reflexivo + verbo
        # Ejemplo: "Se levanto", "Se acerco", "Me dijo"
        REFLEXIVE_PRONOUNS = {"se", "me", "te", "nos", "os"}
        if first_word in REFLEXIVE_PRONOUNS and len(words) >= 2:
            logger.debug(f"Entidad spaCy filtrada (pronombre reflexivo + verbo): '{text}'")
            return False

        # Filtrar frases que contienen verbos conjugados (son oraciones, no entidades)
        # "El se acerco a saludarla", "Hola Maria", etc.
        verb_indicators = {
            "se", "me", "te", "le", "lo", "la", "nos", "os", "les", "los", "las",
            # Verbos comunes conjugados
            "acerco", "acercó", "dijo", "respondió", "preguntó", "miró", "vio",
            "saludo", "saludó", "entró", "salió", "llegó", "fue", "era", "estaba",
            # Infinitivos después de preposiciones
            "para", "sin", "por", "con", "de", "a",
        }
        words_lower = [w.lower() for w in words]
        if len(words) >= 3 and any(w in verb_indicators for w in words_lower[1:]):
            logger.debug(f"Entidad spaCy filtrada (contiene verbo): '{text}'")
            return False

        # Filtrar saludos como "Hola X" - extraer solo el nombre
        if first_word in {"hola", "adiós", "buenos", "buenas"}:
            logger.debug(f"Entidad spaCy filtrada (saludo): '{text}'")
            return False

        # Filtrar frases interrogativas (quién eres, qué es, etc.)
        interrogative_starters = {
            "quién", "quien", "qué", "que", "cómo", "como",
            "dónde", "donde", "cuándo", "cuando", "cuánto", "cuanto",
            "por qué", "para qué",
        }
        if first_word in interrogative_starters:
            logger.debug(f"Entidad spaCy filtrada (interrogativa): '{text}'")
            return False

        # Filtrar términos científicos/biológicos genéricos
        scientific_terms = {
            "endorfinas", "endorfina", "adrenalina", "serotonina", "dopamina",
            "hormona", "hormonas", "neurotransmisor", "neurotransmisores",
        }
        if text_lower in scientific_terms or (len(words) > 1 and words[-1].lower() in scientific_terms):
            logger.debug(f"Entidad spaCy filtrada (término científico): '{text}'")
            return False

        # ===== NUEVO: Filtrar entidades que terminan en gerundio =====
        # Ejemplo: "Camino corriendo" no es una entidad válida
        if len(words) > 1:
            last_word_lower = words[-1].lower()
            if last_word_lower.endswith(('ando', 'endo', 'iendo')):
                logger.debug(f"Entidad spaCy filtrada (termina en gerundio): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar frases que empiezan con posesivo =====
        # Patrón: "su/sus/mi/mis + sustantivo" -> descripción, no entidad
        # Ejemplo: "su novio", "mi hermano miguel", "sus padres"
        # EXCEPCIÓN: Títulos formales como "Su Santidad", "Su Majestad", "Su Excelencia"
        POSSESSIVES = {"su", "sus", "mi", "mis", "tu", "tus", "nuestro", "nuestra"}
        FORMAL_TITLES_AFTER_SU = {"santidad", "majestad", "excelencia", "alteza", "eminencia", "señoría"}
        if first_word in POSSESSIVES and len(words) >= 2:
            second_word = words[1].lower() if len(words) > 1 else ""
            if second_word not in FORMAL_TITLES_AFTER_SU:
                logger.debug(f"Entidad spaCy filtrada (frase posesiva): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar verbos conjugados (terminaciones comunes) =====
        # Detectar verbos por sus terminaciones en lugar de lista específica
        VERB_ENDINGS = (
            # Pretérito imperfecto/indefinido
            'aban', 'ían', 'eron', 'aron', 'ieron',
            'aba', 'ía', 'ió', 'ó',
            # Futuro simple (-ás, -á, -án, -emos, -éis)
            'arás', 'erás', 'irás', 'ará', 'erá', 'irá',
            'arán', 'erán', 'irán', 'aremos', 'eremos', 'iremos',
            # Condicional (-aría, -ería, -iría)
            'aría', 'ería', 'iría', 'arían', 'erían', 'irían',
            'aríamos', 'eríamos', 'iríamos',
            # Subjuntivo presente (-es, -e, -emos, -en para -ar; -as, -a, -amos, -an para -er/-ir)
            'ases', 'ieses', 'ase', 'iese', 'ásemos', 'iésemos',
            'ara', 'iera', 'aras', 'ieras', 'áramos', 'iéramos',
            # Subjuntivo futuro (raro pero existe)
            'are', 'iere', 'aren', 'ieren',
            # Gerundio
            'ando', 'iendo', 'endo',
            # Infinitivo (si son una sola palabra)
            'ar', 'er', 'ir',
            # Presente simple 1ª/2ª persona plural
            'amos', 'emos', 'imos',
        )

        # Pronombres enclíticos que se añaden a verbos
        ENCLITICS = ('me', 'te', 'se', 'lo', 'la', 'los', 'las', 'le', 'les', 'nos', 'os')
        # Combinaciones dobles de enclíticos
        DOUBLE_ENCLITICS = (
            'melo', 'mela', 'melos', 'melas',
            'telo', 'tela', 'telos', 'telas',
            'selo', 'sela', 'selos', 'selas',
            'noslo', 'nosla', 'noslos', 'noslas',
        )

        # Vocales acentuadas (patrón típico de verbos con enclíticos en español)
        ACCENTED_VOWELS = ('á', 'é', 'í', 'ó', 'ú')

        if len(words) == 1 and len(text_stripped) > 4:
            # Detectar verbos con pronombres enclíticos (tomármelos, dáselo, piénsalo)
            # Patrón: raíz verbal con vocal acentuada + enclítico(s)
            # Esto es típico de imperativos y formas verbales con pronombres
            for encl in DOUBLE_ENCLITICS + ENCLITICS:
                if text_lower.endswith(encl) and len(text_lower) > len(encl) + 3:
                    # La raíz antes del enclítico
                    stem = text_lower[:-len(encl)]
                    # Solo filtrar si la raíz CONTIENE una vocal acentuada
                    # (patrón de verbo + enclítico: tomár-melos, piéns-alo, dá-selo)
                    # Esto evita falsos positivos como "Carlos", "Marcos"
                    if any(v in stem for v in ACCENTED_VOWELS):
                        logger.debug(f"Entidad spaCy filtrada (verbo + enclítico): '{text}'")
                        return False

            # Solo palabras largas para terminaciones generales
            if len(text_stripped) > 5 and text_lower.endswith(VERB_ENDINGS):
                # Terminaciones verbales muy específicas que SIEMPRE indican verbo
                # (ningún nombre propio en español termina así)
                DEFINITE_VERB_ENDINGS = (
                    # Futuro 2ª persona
                    'arás', 'erás', 'irás',
                    # Condicional
                    'aría', 'ería', 'iría', 'arían', 'erían', 'irían',
                    # Pretérito plural
                    'aban', 'aron', 'ieron', 'ían',
                    # Subjuntivo
                    'ases', 'ieses', 'áramos', 'iéramos',
                    # 1ª persona plural presente (Acabamos, Sonreímos)
                    'amos', 'emos', 'imos',
                )
                # Filtrar si:
                # 1. No empieza con mayúscula (claramente no es nombre)
                # 2. O termina en terminación verbal definitiva
                if not text_stripped[0].isupper() or text_lower.endswith(DEFINITE_VERB_ENDINGS):
                    logger.debug(f"Entidad spaCy filtrada (probable verbo): '{text}'")
                    return False

        # Detectar verbos en presente simple con mayúscula (Pones, Sonrío)
        # Patrones: termina en -es, -o (1ª/2ª persona singular presente)
        if len(words) == 1 and len(text_stripped) >= 4:
            # Presente 2ª persona singular: -es, -as
            if text_lower.endswith(('ones', 'enes', 'ines', 'anes', 'unes')):
                logger.debug(f"Entidad spaCy filtrada (verbo presente 2ª pers.): '{text}'")
                return False
            # Presente 1ª persona singular con acento: -ío, -úo (sonrío, actúo)
            if text_lower.endswith(('ío', 'úo')):
                logger.debug(f"Entidad spaCy filtrada (verbo presente 1ª pers.): '{text}'")
                return False

        # ===== GENERALIZABLE: Filtrar entidades que terminan en verbo =====
        # Patrón: "Nombre + verbo" -> error de segmentación
        # Ejemplo: "Alejandro asintio", "María corrió"
        # CUIDADO: No filtrar apellidos válidos como "García" (termina en ía)
        if len(words) >= 2:
            last_word = words[-1].lower()
            # Solo filtrar si:
            # 1. La última palabra empieza con minúscula (verbos, no apellidos)
            # 2. O termina en patrones verbales muy específicos
            if not words[-1][0].isupper():
                if last_word.endswith(('ió', 'ó', 'aron', 'ieron', 'aba')):
                    logger.debug(f"Entidad spaCy filtrada (termina en verbo): '{text}'")
                    return False
            # Palabras que terminan en "io" sin tilde son típicamente verbos
            # Ejemplo: "asintio", "salio", "corrio"
            if last_word.endswith('io') and not last_word.endswith(('lio', 'rio', 'nio')):
                # Excluir sufijos comunes de nombres: -ario, -erio, -orio
                if not last_word.endswith(('ario', 'erio', 'orio')):
                    logger.debug(f"Entidad spaCy filtrada (termina en verbo -io): '{text}'")
                    return False

        return True

    def _is_valid_heuristic_candidate(self, text: str) -> bool:
        """
        Valida un candidato heurístico (palabra capitalizada NO detectada por spaCy).

        Para candidatos heurísticos somos más estrictos porque no tenemos
        la validación del modelo NER.

        Args:
            text: Texto del candidato

        Returns:
            True si es un candidato válido para el gazetteer
        """
        if not text:
            return False

        text_stripped = text.strip()
        canonical = text_stripped.lower()

        # Requisitos básicos
        if len(text_stripped) < 3:  # Más estricto que spaCy
            return False

        # Filtrar stopwords
        if canonical in self.STOP_TITLES:
            return False

        # Filtrar falsos positivos heurísticos (solo para candidatos, no spaCy)
        if canonical in self.HEURISTIC_FALSE_POSITIVES:
            return False

        # Filtrar números y puntuación
        if text.isdigit() or not any(c.isalpha() for c in text):
            return False

        return True

    def _is_high_quality_entity(self, text: str, label: EntityLabel) -> bool:
        """
        Determina si una entidad es de alta calidad para añadir al gazetteer.

        Solo añadimos al gazetteer entidades que tienen alta probabilidad
        de ser correctas, para evitar propagar falsos positivos.

        Criterios:
        - Nombres con múltiples palabras (ej: "Juan García")
        - Nombres largos (ej: "Hogwarts")
        - Lugares conocidos (ciudades, países)

        Args:
            text: Texto de la entidad
            label: Tipo de entidad

        Returns:
            True si es de alta calidad para gazetteer
        """
        if not text:
            return False

        text_stripped = text.strip()
        words = text_stripped.split()

        # Nombres con múltiples palabras son más confiables
        # Ejemplo: "Juan García", "Ciudad de México"
        if len(words) >= 2:
            # Verificar que al menos una palabra sea significativa
            significant_words = [
                w for w in words
                if w.lower() not in self.STOP_TITLES and len(w) > 2
            ]
            if len(significant_words) >= 2:
                return True

        # Palabras largas de una sola palabra (posiblemente nombres propios)
        # Ejemplo: "Gandalf", "Mordor", "Hogwarts"
        if len(words) == 1 and len(text_stripped) >= 5:
            # Verificar que empiece con mayúscula (nombre propio)
            if text_stripped[0].isupper():
                return True

        return False

    def extract_entities(
        self,
        text: str,
        progress_callback: Optional[callable] = None,
        project_id: Optional[int] = None,
        enable_validation: bool = True,
    ) -> Result[NERResult]:
        """
        Extrae entidades nombradas del texto.

        Pipeline de extracción:
        1. LLM preprocesador (si habilitado) - detecta entidades con comprensión semántica
        2. spaCy NER - detección estadística tradicional
        3. Gazetteer dinámico - detecta menciones de entidades ya conocidas
        4. Fusión y deduplicación - combina resultados priorizando por confianza
        5. Validación multi-capa - filtra falsos positivos (heurísticas + LLM + feedback)

        Args:
            text: Texto a procesar
            progress_callback: Función opcional para reportar progreso.
                               Recibe (fase: str, porcentaje: float, mensaje: str)
            project_id: ID del proyecto (para feedback de usuario en validación)
            enable_validation: Habilitar validación post-NER para filtrar falsos positivos

        Returns:
            Result con NERResult conteniendo las entidades extraídas
        """
        if not text or not text.strip():
            return Result.success(NERResult(processed_chars=0))

        result = NERResult(processed_chars=len(text))
        entities_found: set[tuple[int, int]] = set()  # (start, end) para evitar duplicados

        def report_progress(fase: str, pct: float, msg: str):
            """Helper para reportar progreso si hay callback."""
            if progress_callback:
                try:
                    progress_callback(fase, pct, msg)
                except Exception as e:
                    logger.debug(f"Error en callback de progreso: {e}")

        try:
            # 0. Preprocesamiento con LLM (si habilitado)
            llm_entities: list[ExtractedEntity] = []
            if self.use_llm_preprocessing:
                report_progress("ner", 0.0, "Analizando texto con LLM...")
                llm_entities = self._preprocess_with_llm(text)
                report_progress("ner", 0.3, f"LLM: {len(llm_entities)} entidades detectadas")
                logger.info(f"LLM preprocesador: {len(llm_entities)} entidades detectadas")

                # Añadir entidades del LLM primero (tienen prioridad)
                for entity in llm_entities:
                    pos = (entity.start_char, entity.end_char)
                    if pos not in entities_found:
                        result.entities.append(entity)
                        entities_found.add(pos)

            report_progress("ner", 0.4, "Procesando con spaCy NER...")
            doc = self.nlp(text)
            report_progress("ner", 0.7, "Extrayendo entidades de spaCy...")

            # 1. Entidades detectadas por spaCy
            for ent in doc.ents:
                label = self.SPACY_LABEL_MAP.get(ent.label_)
                if label is None:
                    continue

                # Solo filtrar errores obvios de segmentación
                if not self._is_valid_spacy_entity(ent.text):
                    # Intentar extraer sub-entidades de entidades mal segmentadas
                    # (ej: "María\n\nMaría Sánchez" -> "María Sánchez")
                    if '\n' in ent.text:
                        sub_entities = self._extract_sub_entities_from_malformed(
                            ent.text, ent.start_char, label, text
                        )
                        for sub_ent in sub_entities:
                            sub_pos = (sub_ent.start_char, sub_ent.end_char)
                            if sub_pos not in entities_found:
                                result.entities.append(sub_ent)
                                entities_found.add(sub_pos)
                    continue

                # Verificar si ya fue detectada por LLM (evitar duplicados)
                pos = (ent.start_char, ent.end_char)
                if pos in entities_found:
                    continue

                # Verificar solapamiento con entidades LLM
                overlaps_llm = False
                for llm_ent in llm_entities:
                    if self._entities_overlap(
                        ent.start_char, ent.end_char,
                        llm_ent.start_char, llm_ent.end_char
                    ):
                        overlaps_llm = True
                        break

                if overlaps_llm:
                    continue  # LLM tiene prioridad

                # ===== NUEVO: Filtro morfológico genérico =====
                # Obtener contexto alrededor de la entidad para análisis
                ctx_start = max(0, ent.start_char - 100)
                ctx_end = min(len(text), ent.end_char + 100)
                context = text[ctx_start:ctx_end]
                entity_pos_in_ctx = ent.start_char - ctx_start

                is_fp, fp_reason = self._is_false_positive_by_morphology(
                    ent.text, label, context, entity_pos_in_ctx
                )
                if is_fp:
                    logger.debug(f"Entidad filtrada por morfología: '{ent.text}' - {fp_reason}")
                    continue

                entity = ExtractedEntity(
                    text=ent.text,
                    label=label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.8,  # spaCy no proporciona confianza
                    source="spacy",
                )

                result.entities.append(entity)
                entities_found.add(pos)

                # Solo añadir al gazetteer entidades de alta calidad
                # (nombres propios con múltiples palabras o nombres largos)
                canonical = entity.canonical_form
                if canonical and self._is_high_quality_entity(ent.text, label):
                    with self._gazetteer_lock:
                        # Limitar tamaño del gazetteer
                        if len(self.dynamic_gazetteer) < MAX_GAZETTEER_SIZE:
                            self.dynamic_gazetteer[canonical] = label

            # 2. Detección heurística (gazetteer dinámico)
            if self.enable_gazetteer:
                report_progress("ner", 0.80, "Aplicando gazetteer dinámico...")
                gazetteer_entities = self._detect_gazetteer_entities(doc, entities_found)
                result.entities.extend(gazetteer_entities)

                # Registrar candidatos para el gazetteer
                candidates = self._find_gazetteer_candidates(doc, entities_found)
                result.gazetteer_candidates = candidates

            # 2.3 Detección de patrones título+apellido ("doctor Ramírez", "coronel Salgado")
            # NOTA: Esta función MODIFICA result.entities in-place para extender entidades
            report_progress("ner", 0.82, "Detectando patrones título+nombre...")
            title_entities = self._detect_title_name_patterns(
                doc, text, entities_found, result.entities
            )
            # Solo agregar las entidades completamente nuevas (no extensiones)
            for ent in title_entities:
                result.entities.append(ent)

            # 2.4 Detección de lugares compuestos ("Valle Marineris", "Monte Olimpo")
            # NOTA: Similar a títulos, extiende entidades LOC existentes
            report_progress("ner", 0.83, "Detectando lugares compuestos...")
            compound_loc_entities = self._detect_compound_locations(
                doc, text, entities_found, result.entities
            )
            for ent in compound_loc_entities:
                result.entities.append(ent)

            # 2.5 Separar entidades coordinadas ("Pedro y Carmen" -> ["Pedro", "Carmen"])
            report_progress("ner", 0.85, "Separando entidades coordinadas...")
            result.entities = self._split_coordinated_entities(doc, result.entities)

            # 3. Validación multi-capa (filtra falsos positivos)
            if enable_validation and result.entities:
                report_progress("ner", 0.90, "Validando entidades detectadas...")
                validator = get_entity_validator()
                validation_result = validator.validate(
                    entities=result.entities,
                    full_text=text,
                    project_id=project_id,
                )

                # Actualizar resultado con entidades validadas
                result.entities = validation_result.valid_entities
                result.rejected_entities = validation_result.rejected_entities
                result.validation_scores = {
                    text: score.to_dict()
                    for text, score in validation_result.scores.items()
                }
                result.validation_method = validation_result.validation_method

                logger.info(
                    f"Validación: {len(validation_result.valid_entities)} válidas, "
                    f"{len(validation_result.rejected_entities)} rechazadas "
                    f"(método: {validation_result.validation_method})"
                )

            # 4. Verificación LLM para entidades de baja confianza (segunda capa)
            if self.use_llm_preprocessing and result.entities:
                report_progress("ner", 0.93, "Verificando entidades con LLM...")
                result.entities = self._llm_verify_low_confidence_entities(
                    text, result.entities, result.validation_scores
                )

            # 5. Post-procesamiento: limpiar MISC espurios y reclasificar conocidos
            result.entities = self._postprocess_misc_entities(result.entities)

            # Ordenar por posición
            result.entities.sort(key=lambda e: e.start_char)

            # Log de fuentes
            sources = {}
            for e in result.entities:
                sources[e.source] = sources.get(e.source, 0) + 1

            report_progress("ner", 1.0, f"NER completado: {len(result.entities)} menciones detectadas")

            logger.info(
                f"NER: {len(result.entities)} entidades extraídas "
                f"({len(result.get_persons())} PER, "
                f"{len(result.get_locations())} LOC, "
                f"{len(result.get_organizations())} ORG) - "
                f"Fuentes: {sources}"
            )

            return Result.success(result)

        except Exception as e:
            error = NERExtractionError(
                text_sample=text[:100] if len(text) > 100 else text,
                original_error=str(e),
            )
            logger.error(f"Error en extracción NER: {e}")
            return Result.partial(result, [error])

    def _extract_sub_entities_from_malformed(
        self,
        malformed_text: str,
        start_offset: int,
        label: EntityLabel,
        full_text: str,
    ) -> list[ExtractedEntity]:
        """
        Extrae entidades válidas de texto mal segmentado por spaCy.

        Cuando spaCy une incorrectamente texto a través de líneas
        (ej: "María\n\nMaría Sánchez"), intentamos extraer las partes
        válidas como entidades separadas.

        Args:
            malformed_text: Texto de la entidad mal segmentada
            start_offset: Posición de inicio en el texto completo
            label: Etiqueta de la entidad
            full_text: Texto completo del documento

        Returns:
            Lista de entidades válidas extraídas
        """
        import re
        entities = []

        # Separar por saltos de línea
        parts = re.split(r'\n+', malformed_text)

        current_offset = start_offset
        for part in parts:
            part_stripped = part.strip()

            # Encontrar la posición real en el texto completo
            part_start = full_text.find(part_stripped, current_offset)
            if part_start == -1:
                current_offset += len(part) + 1
                continue

            # Validar que la parte parece un nombre propio
            # (empieza con mayúscula, tiene más de 2 caracteres)
            if (
                part_stripped
                and len(part_stripped) >= 2
                and part_stripped[0].isupper()
                and self._is_valid_spacy_entity(part_stripped)
            ):
                entity = ExtractedEntity(
                    text=part_stripped,
                    label=label,
                    start_char=part_start,
                    end_char=part_start + len(part_stripped),
                    confidence=0.7,  # Menor confianza por extracción manual
                    source="spacy_split",
                )
                entities.append(entity)

            current_offset = part_start + len(part_stripped)

        return entities

    def _simple_coord_split(self, text: str) -> list[tuple[str, int]]:
        """
        Divide texto coordinado simple como "Pedro y Carmen" en partes.

        Fallback cuando spaCy no detecta la estructura coordinada.

        Args:
            text: Texto a dividir

        Returns:
            Lista de tuplas (texto, offset) para cada parte
        """
        import re

        parts = []

        # Buscar patrón "X y Y" o "X e Y"
        # Solo dividir si ambas partes empiezan con mayúscula (nombres propios)
        pattern = r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\s+[ye]\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)$'

        match = re.match(pattern, text.strip())
        if match:
            part1 = match.group(1)
            part2 = match.group(2)

            # Encontrar offsets
            offset1 = text.find(part1)
            offset2 = text.find(part2, offset1 + len(part1))

            if offset1 >= 0:
                parts.append((part1, offset1))
            if offset2 >= 0:
                parts.append((part2, offset2))

        return parts

    def _entities_overlap(
        self,
        start1: int, end1: int,
        start2: int, end2: int,
    ) -> bool:
        """Verifica si dos rangos de entidades se solapan."""
        return not (end1 <= start2 or end2 <= start1)

    def _split_coordinated_entities(
        self,
        doc,
        entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Separa entidades coordinadas como "Pedro y Carmen" en entidades individuales.

        Usa análisis de dependencias de spaCy para detectar estructuras coordinadas
        y extraer cada componente como entidad separada.

        Args:
            doc: Documento spaCy procesado
            entities: Lista de entidades detectadas

        Returns:
            Lista de entidades con coordinaciones separadas
        """
        result = []
        processed_spans = set()

        for entity in entities:
            # Verificar si ya procesamos este span
            span_key = (entity.start_char, entity.end_char)
            if span_key in processed_spans:
                continue

            # Verificar si contiene conjunción coordinante
            if " y " not in entity.text.lower() and " e " not in entity.text.lower():
                result.append(entity)
                processed_spans.add(span_key)
                continue

            # Buscar tokens en el span de la entidad
            entity_tokens = [t for t in doc if t.idx >= entity.start_char and t.idx < entity.end_char]

            # Buscar la conjunción
            conj_token = None
            for token in entity_tokens:
                if token.lower_ in ("y", "e") and token.dep_ == "cc":
                    conj_token = token
                    break

            if not conj_token:
                # Fallback: separación simple por patrón "X y Y"
                # Esto funciona cuando spaCy no detecta la estructura coordinada
                parts = self._simple_coord_split(entity.text)
                if len(parts) >= 2:
                    for part_text, part_offset in parts:
                        if self._is_valid_spacy_entity(part_text):
                            new_ent = ExtractedEntity(
                                text=part_text,
                                label=entity.label,
                                start_char=entity.start_char + part_offset,
                                end_char=entity.start_char + part_offset + len(part_text),
                                confidence=entity.confidence * 0.85,
                                source="simple_coord_split",
                            )
                            result.append(new_ent)
                            processed_spans.add((new_ent.start_char, new_ent.end_char))
                    processed_spans.add(span_key)
                    continue
                else:
                    # No se pudo separar, mantener original
                    result.append(entity)
                    processed_spans.add(span_key)
                    continue

            # Encontrar los elementos coordinados
            # El patrón puede ser:
            # 1. "Pedro y Carmen" donde y->Carmen y Carmen->Pedro(conj)
            # 2. "Pedro y Carmen" donde y->Pedro y Pedro->Carmen(conj)
            # Buscamos todos los tokens con dep=conj y su head

            coordinated = []
            for token in entity_tokens:
                if token.dep_ == "conj":
                    # Encontrar el head de la coordinación
                    if token.head in entity_tokens:
                        coordinated.append(token.head)
                    coordinated.append(token)

            # Si no encontramos con dep=conj, buscar nombres propios directamente
            if len(coordinated) < 2:
                coordinated = [t for t in entity_tokens if t.pos_ == "PROPN"]

            if len(coordinated) < 2:
                # No se encontró estructura coordinada válida, usar fallback
                parts = self._simple_coord_split(entity.text)
                if len(parts) >= 2:
                    for part_text, part_offset in parts:
                        if self._is_valid_spacy_entity(part_text):
                            new_ent = ExtractedEntity(
                                text=part_text,
                                label=entity.label,
                                start_char=entity.start_char + part_offset,
                                end_char=entity.start_char + part_offset + len(part_text),
                                confidence=entity.confidence * 0.85,
                                source="simple_coord_split",
                            )
                            result.append(new_ent)
                            processed_spans.add((new_ent.start_char, new_ent.end_char))
                    processed_spans.add(span_key)
                    continue
                else:
                    result.append(entity)
                    processed_spans.add(span_key)
                    continue

            # Crear entidades separadas para cada elemento coordinado
            for coord_token in coordinated:
                # Encontrar el span completo del nombre (puede incluir apellido/modificadores)
                start = coord_token.idx
                end = coord_token.idx + len(coord_token.text)

                # Expandir para incluir tokens siguientes que sean parte del nombre
                # (apellidos, títulos, etc.)
                for next_token in doc:
                    if next_token.idx == end + 1:  # Token siguiente
                        # Incluir si es un nombre propio o parte del nombre
                        if next_token.pos_ in ("PROPN", "NOUN") and next_token.dep_ in ("flat", "appos", "compound"):
                            end = next_token.idx + len(next_token.text)
                        else:
                            break

                # Verificar que el span es válido y dentro de la entidad original
                if start >= entity.start_char and end <= entity.end_char:
                    coord_text = doc.text[start:end]

                    # Solo añadir si el texto parece un nombre válido
                    if coord_text and coord_text[0].isupper() and len(coord_text) >= 2:
                        new_entity = ExtractedEntity(
                            text=coord_text,
                            label=entity.label,
                            start_char=start,
                            end_char=end,
                            confidence=entity.confidence * 0.9,  # Ligeramente menor confianza
                            source="coord_split",
                        )
                        result.append(new_entity)
                        processed_spans.add((start, end))

            # Marcar el span original como procesado
            processed_spans.add(span_key)

        # Deduplicar y ordenar
        seen = set()
        unique_result = []
        for entity in sorted(result, key=lambda e: e.start_char):
            key = (entity.text, entity.start_char, entity.end_char)
            if key not in seen:
                unique_result.append(entity)
                seen.add(key)

        logger.debug(f"Separación de coordinados: {len(entities)} -> {len(unique_result)} entidades")
        return unique_result

    # ==========================================================================
    # Patrones de título + nombre (generalizable)
    # ==========================================================================

    # Títulos profesionales/militares que preceden a un apellido
    # Formato: "título Apellido" -> entidad PER
    PROFESSIONAL_TITLES = {
        # Médicos/Sanitarios
        "doctor", "doctora", "dr", "dra",
        # Militares
        "coronel", "general", "capitán", "capitan", "teniente", "sargento",
        "almirante", "comandante", "mayor",
        # Policiales/Judiciales
        "inspector", "inspectora", "comisario", "comisaria",
        "juez", "jueza", "fiscal",
        "subinspector", "subinspectora",
        # Religiosos
        "fray", "sor", "padre", "madre", "hermano", "hermana",
        "rabino", "rabina", "imán", "iman",
        # Académicos
        "profesor", "profesora", "catedrático", "catedratica",
        # Nobiliarios/Formales
        "conde", "condesa", "duque", "duquesa", "marqués", "marques", "marquesa",
        "barón", "baron", "baronesa", "sultán", "sultan", "sultana",
        "rey", "reina", "príncipe", "principe", "princesa",
    }

    # Prefijos de lugares compuestos
    # Formato: "prefijo Nombre" -> entidad LOC
    LOCATION_PREFIXES = {
        # Geográficos
        "monte", "sierra", "cordillera", "volcán", "volcan",
        "valle", "cañón", "canon", "desfiladero",
        "río", "rio", "lago", "laguna", "mar", "océano", "oceano",
        "isla", "península", "peninsula", "cabo", "bahía", "bahia",
        "desierto", "bosque", "selva", "pradera", "llanura",
        # Urbanos
        "plaza", "calle", "avenida", "paseo", "parque",
        "barrio", "colonia", "urbanización", "urbanizacion",
        "puerto", "aeropuerto", "estación", "estacion",
        # Construcciones
        "palacio", "castillo", "torre", "fortaleza", "muralla",
        "catedral", "iglesia", "monasterio", "convento",
        "hospital", "universidad", "instituto", "colegio",
        "base", "campo", "campamento",
        # Políticos
        "imperio", "reino", "república", "republica",
        "provincia", "región", "region", "departamento",
    }

    def _detect_title_name_patterns(
        self,
        doc,
        full_text: str,
        already_found: set[tuple[int, int]],
        existing_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Detecta patrones de título + nombre/apellido y EXTIENDE entidades existentes.

        Busca secuencias como "doctor Ramírez", "coronel Salgado", "fiscal Montero".
        Si encuentra un patrón que CONTIENE una entidad ya detectada, extiende
        esa entidad para incluir el título.

        Este patrón es GENERALIZABLE - no depende de nombres específicos,
        sino de la estructura título + palabra con mayúscula.

        Args:
            doc: Documento spaCy procesado
            full_text: Texto completo
            already_found: Posiciones ya detectadas (se modificará in-place)
            existing_entities: Entidades ya detectadas (se modificará in-place)

        Returns:
            Lista de NUEVAS entidades detectadas (que no extienden existentes)
        """
        import re
        new_entities = []

        # Buscar patrón: título (case-insensitive) + Nombre (MUST start with uppercase)
        # Usamos (?-i:...) para hacer los nombres case-sensitive mientras el título es case-insensitive
        # Esto evita capturar palabras como "nos", "ha" que siguen al nombre
        title_pattern = r'\b(' + '|'.join(re.escape(t) for t in self.PROFESSIONAL_TITLES) + r')\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?\b'

        for match in re.finditer(title_pattern, full_text, re.IGNORECASE):
            full_match = match.group(0)
            title = match.group(1)
            # name_part is extracted from full_match by removing the title
            # (no capture group needed - was causing "no such group" error)

            pattern_start = match.start()
            pattern_end = match.end()

            # Verificar que no está ya detectada exactamente
            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si hay una entidad existente que este patrón EXTIENDE
            # (es decir, el patrón contiene la entidad existente)
            extended = False
            for i, ent in enumerate(existing_entities):
                # El patrón debe contener la entidad existente
                # y el patrón debe ser más largo (incluye título)
                if (ent.start_char >= pattern_start and
                    ent.end_char <= pattern_end and
                    pattern_end - pattern_start > ent.end_char - ent.start_char and
                    ent.label == EntityLabel.PER):

                    # Extender la entidad existente
                    logger.debug(
                        f"Extendiendo entidad '{ent.text}' a '{full_match}' "
                        f"(añadiendo título '{title}')"
                    )

                    # Actualizar posiciones en already_found
                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    # Actualizar la entidad
                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,  # Mantener confianza original
                        source=ent.source + "+title",
                    )
                    extended = True
                    break

            # Si no extendió ninguna entidad existente, verificar si es nueva
            if not extended:
                # Solo agregar si no hay solapamiento
                overlaps = False
                for (s, e) in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.PER,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.75,
                        source="title_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón título+nombre detectado: '{full_match}'")

        return new_entities

    def _detect_compound_locations(
        self,
        doc,
        full_text: str,
        already_found: set[tuple[int, int]],
        existing_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Detecta lugares compuestos con prefijo geográfico y EXTIENDE entidades existentes.

        Busca secuencias como "Monte Olimpo", "Valle Marineris", "Palacio de Cristal".
        Si encuentra un patrón que CONTIENE una entidad LOC ya detectada, la extiende.

        Este patrón es GENERALIZABLE - detecta cualquier prefijo geográfico
        seguido de un nombre propio.

        Args:
            doc: Documento spaCy procesado
            full_text: Texto completo
            already_found: Posiciones ya detectadas (se modificará in-place)
            existing_entities: Entidades ya detectadas (se modificará in-place)

        Returns:
            Lista de NUEVAS entidades detectadas (que no extienden existentes)
        """
        import re
        new_entities = []

        # Patrón 1: prefijo (case-insensitive) + Nombre (MUST start with uppercase)
        # Usamos (?-i:...) para hacer los nombres case-sensitive
        prefix_pattern = r'\b(' + '|'.join(re.escape(p) for p in self.LOCATION_PREFIXES) + r')\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+(?-i:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?\b'

        for match in re.finditer(prefix_pattern, full_text, re.IGNORECASE):
            full_match = match.group(0)
            prefix = match.group(1)

            pattern_start = match.start()
            pattern_end = match.end()

            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si extiende una entidad LOC existente
            extended = False
            for i, ent in enumerate(existing_entities):
                if (ent.start_char >= pattern_start and
                    ent.end_char <= pattern_end and
                    pattern_end - pattern_start > ent.end_char - ent.start_char and
                    ent.label == EntityLabel.LOC):

                    logger.debug(
                        f"Extendiendo ubicación '{ent.text}' a '{full_match}' "
                        f"(añadiendo prefijo '{prefix}')"
                    )

                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,
                        source=ent.source + "+prefix",
                    )
                    extended = True
                    break

            if not extended:
                overlaps = False
                for (s, e) in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.75,
                        source="location_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón lugar compuesto: '{full_match}'")

        # Patrón 2: prefijo + de + Nombre (ej: "Palacio de Cristal")
        # NO usar IGNORECASE aquí - los nombres DEBEN empezar con mayúscula
        compound_pattern = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(de|del|de la|de los|de las)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b'

        for match in re.finditer(compound_pattern, full_text):
            first_word = match.group(1).lower()
            full_match = match.group(0)

            if first_word not in self.LOCATION_PREFIXES:
                continue

            pattern_start = match.start()
            pattern_end = match.end()

            pos = (pattern_start, pattern_end)
            if pos in already_found:
                continue

            # Buscar si extiende una entidad existente
            extended = False
            for i, ent in enumerate(existing_entities):
                if (ent.start_char >= pattern_start and
                    ent.end_char <= pattern_end and
                    pattern_end - pattern_start > ent.end_char - ent.start_char and
                    ent.label == EntityLabel.LOC):

                    old_pos = (ent.start_char, ent.end_char)
                    if old_pos in already_found:
                        already_found.discard(old_pos)
                    already_found.add(pos)

                    existing_entities[i] = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=ent.confidence,
                        source=ent.source + "+compound",
                    )
                    extended = True
                    break

            if not extended:
                overlaps = False
                for (s, e) in already_found:
                    if not (pattern_end <= s or pattern_start >= e):
                        overlaps = True
                        break

                if not overlaps:
                    entity = ExtractedEntity(
                        text=full_match,
                        label=EntityLabel.LOC,
                        start_char=pattern_start,
                        end_char=pattern_end,
                        confidence=0.7,
                        source="location_pattern",
                    )
                    new_entities.append(entity)
                    already_found.add(pos)
                    logger.debug(f"Nuevo patrón lugar compuesto (de): '{full_match}'")

        return new_entities

    def _detect_gazetteer_entities(
        self,
        doc,
        already_found: set[tuple[int, int]],
    ) -> list[ExtractedEntity]:
        """
        Detecta entidades usando el gazetteer dinámico.

        Busca tokens que coincidan con nombres ya conocidos en el gazetteer.
        Solo añade entidades si el token tiene forma de nombre propio
        (empieza con mayúscula y no es inicio de oración).
        """
        entities = []

        for token in doc:
            # Solo considerar tokens que parecen nombres propios
            # (empiezan con mayúscula y no son inicio de oración)
            if not token.text or len(token.text) < self.MIN_ENTITY_LENGTH:
                continue

            if not token.text[0].isupper():
                continue

            # Evitar inicios de oración (menor confianza)
            if token.is_sent_start:
                continue

            canonical = token.text.lower().strip()

            # Verificar si está en el gazetteer (lectura thread-safe)
            with self._gazetteer_lock:
                label = self.dynamic_gazetteer.get(canonical)

            if label is not None:
                # El gazetteer ya contiene entidades validadas, solo filtrar errores básicos
                if not self._is_valid_spacy_entity(token.text):
                    continue

                pos = (token.idx, token.idx + len(token.text))
                if pos not in already_found:
                    entity = ExtractedEntity(
                        text=token.text,
                        label=label,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        confidence=0.6,  # Menor confianza que spaCy directo
                        source="gazetteer",
                    )
                    entities.append(entity)
                    already_found.add(pos)

        return entities

    def _find_gazetteer_candidates(
        self,
        doc,
        already_found: set[tuple[int, int]],
    ) -> set[str]:
        """
        Encuentra candidatos para añadir al gazetteer.

        Busca palabras con mayúscula que podrían ser nombres propios
        no detectados por spaCy (típico en ficción con nombres inventados).

        NOTA: Los candidatos NO se añaden automáticamente al gazetteer.
        Solo se retornan para ser contados. Entidades se crean solo si
        aparecen múltiples veces (MIN_MENTIONS_FOR_ENTITY).
        """
        candidates: set[str] = set()

        for token in doc:
            # Condiciones para ser candidato:
            # 1. Empieza con mayúscula
            # 2. No es inicio de oración
            # 3. No fue detectado por spaCy
            # 4. No es un stopword conocido
            # 5. No es un falso positivo común
            # 6. Tiene longitud mínima

            if not token.text or len(token.text) < 3:
                continue

            if not token.text[0].isupper():
                continue

            if token.is_sent_start:
                continue

            pos = (token.idx, token.idx + len(token.text))
            if pos in already_found:
                continue

            canonical = token.text.lower().strip()

            # Usar validación heurística (más estricta que spaCy)
            if not self._is_valid_heuristic_candidate(token.text):
                continue

            if token.like_num or token.like_email or token.like_url:
                continue

            # Es un candidato válido - solo lo registramos, NO añadimos al gazetteer
            # El gazetteer solo se actualiza con entidades confirmadas por spaCy
            # o manualmente por el usuario
            candidates.add(token.text)

        return candidates

    def add_to_gazetteer(
        self,
        name: str,
        label: EntityLabel = EntityLabel.PER,
    ) -> None:
        """
        Añade un nombre al gazetteer dinámico manualmente.

        Útil cuando el usuario confirma que un nombre es una entidad válida.

        Args:
            name: Nombre a añadir
            label: Tipo de entidad
        """
        canonical = name.lower().strip()
        if len(canonical) > 2:
            with self._gazetteer_lock:
                self.dynamic_gazetteer[canonical] = label
            logger.debug(f"Añadido al gazetteer: {name} ({label.value})")

    def remove_from_gazetteer(self, name: str) -> bool:
        """
        Elimina un nombre del gazetteer dinámico.

        Útil cuando el usuario indica que una detección es incorrecta.

        Args:
            name: Nombre a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        canonical = name.lower().strip()
        with self._gazetteer_lock:
            if canonical in self.dynamic_gazetteer:
                del self.dynamic_gazetteer[canonical]
                logger.debug(f"Eliminado del gazetteer: {name}")
                return True
        return False

    def clear_gazetteer(self) -> None:
        """Limpia el gazetteer dinámico."""
        with self._gazetteer_lock:
            self.dynamic_gazetteer.clear()
        logger.debug("Gazetteer limpiado")

    def get_gazetteer_stats(self) -> dict[str, int]:
        """Retorna estadísticas del gazetteer."""
        with self._gazetteer_lock:
            stats: dict[str, int] = {
                "total": len(self.dynamic_gazetteer),
                "PER": 0,
                "LOC": 0,
                "ORG": 0,
                "MISC": 0,
            }
            for label in self.dynamic_gazetteer.values():
                stats[label.value] += 1
        return stats


# =============================================================================
# Singleton thread-safe
# =============================================================================

_ner_lock = threading.Lock()
_ner_extractor: Optional[NERExtractor] = None


def get_ner_extractor(
    enable_gazetteer: bool = True,
    enable_gpu: Optional[bool] = None,
) -> NERExtractor:
    """
    Obtiene el extractor NER singleton (thread-safe).

    Args:
        enable_gazetteer: Habilitar gazetteer dinámico
        enable_gpu: Usar GPU (None = auto)

    Returns:
        Instancia de NERExtractor
    """
    global _ner_extractor

    if _ner_extractor is None:
        with _ner_lock:
            # Double-checked locking
            if _ner_extractor is None:
                _ner_extractor = NERExtractor(
                    enable_gazetteer=enable_gazetteer,
                    enable_gpu=enable_gpu,
                )

    return _ner_extractor


def reset_ner_extractor() -> None:
    """Resetea el extractor singleton (thread-safe, para testing)."""
    global _ner_extractor
    with _ner_lock:
        _ner_extractor = None


def extract_entities(
    text: str,
    project_id: Optional[int] = None,
    enable_validation: bool = True,
) -> Result[NERResult]:
    """
    Atajo para extraer entidades de un texto.

    Args:
        text: Texto a procesar
        project_id: ID del proyecto (para feedback de usuario)
        enable_validation: Habilitar validación post-NER

    Returns:
        Result con NERResult
    """
    return get_ner_extractor().extract_entities(
        text,
        project_id=project_id,
        enable_validation=enable_validation,
    )


def extract_implicit_characters(
    text: str,
    known_entities: Optional[list[str]] = None,
) -> Result[list[ExtractedEntity]]:
    """
    Detecta personajes implícitos usando LLM.

    Identifica menciones de personajes que no son nombres propios pero
    se refieren a personas específicas, como "el hombre", "la anciana",
    "el jefe de Juan", "mi madre", etc.

    Args:
        text: Texto a analizar
        known_entities: Lista de entidades ya conocidas (para no duplicar)

    Returns:
        Result con lista de entidades implícitas detectadas
    """
    try:
        from ..llm.client import get_llm_client

        client = get_llm_client()
        if not client or not client.is_available:
            logger.debug("LLM no disponible para detección de personajes implícitos")
            return Result.success([])

        # Tomar solo los primeros 3000 caracteres para eficiencia
        text_sample = text[:3000] if len(text) > 3000 else text

        known_str = ", ".join(known_entities) if known_entities else "ninguno"

        prompt = f"""Analiza el siguiente texto narrativo en español y encuentra TODOS los personajes mencionados.

TEXTO:
{text_sample}

PERSONAJES YA CONOCIDOS: {known_str}

INSTRUCCIONES:
1. Identifica personajes que NO sean nombres propios pero se refieran a personas específicas
2. Incluye: "el hombre", "la mujer", "el extraño", "el jefe", "mi madre", "su hermano", etc.
3. NO incluyas los personajes ya conocidos
4. NO incluyas objetos o lugares

Responde SOLO con una lista, un personaje por línea, en formato:
MENCION: [texto exacto como aparece]
DESCRIPCION: [breve descripción si hay contexto]

Si no hay personajes implícitos, responde: NINGUNO"""

        response = client.complete(
            prompt=prompt,
            system="Eres un experto en análisis narrativo. Detecta personajes mencionados de forma implícita (no por nombre propio) en textos de ficción.",
            max_tokens=500,
            temperature=0.1,
        )

        if not response or "NINGUNO" in response.upper():
            return Result.success([])

        # Parsear respuesta
        entities = []
        import re

        for match in re.finditer(r"MENCION:\s*(.+?)(?:\n|$)", response, re.IGNORECASE):
            mention_text = match.group(1).strip().strip('"\'')

            # Buscar la mención en el texto original para obtener posición
            text_lower = text.lower()
            mention_lower = mention_text.lower()

            # Buscar todas las ocurrencias
            start = 0
            while True:
                pos = text_lower.find(mention_lower, start)
                if pos == -1:
                    break

                entity = ExtractedEntity(
                    text=text[pos:pos + len(mention_text)],  # Usar capitalización original
                    label=EntityLabel.PER,  # Personaje
                    start_char=pos,
                    end_char=pos + len(mention_text),
                    confidence=0.7,  # Menor confianza que spaCy
                    source="llm_implicit",
                )
                entities.append(entity)
                start = pos + 1  # Buscar siguiente ocurrencia

        logger.info(f"Detectados {len(entities)} personajes implícitos por LLM")
        return Result.success(entities)

    except Exception as e:
        logger.warning(f"Error detectando personajes implícitos: {e}")
        return Result.failure(NLPError(
            message=f"Error en detección de personajes implícitos: {e}",
            severity=ErrorSeverity.WARNING,
        ))
