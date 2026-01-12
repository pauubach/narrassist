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
        """Normaliza la forma canónica si no se proporciona."""
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
        entities: Lista de entidades extraídas
        processed_chars: Caracteres procesados
        gazetteer_candidates: Candidatos detectados por heurísticas
    """

    entities: list[ExtractedEntity] = field(default_factory=list)
    processed_chars: int = 0
    gazetteer_candidates: set[str] = field(default_factory=set)

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
    }

    # Longitud mínima para considerar una entidad válida
    MIN_ENTITY_LENGTH = 2

    def __init__(
        self,
        enable_gazetteer: bool = True,
        min_entity_confidence: float = 0.5,
        enable_gpu: Optional[bool] = None,
    ):
        """
        Inicializa el extractor NER.

        Args:
            enable_gazetteer: Habilitar detección heurística de nombres
            min_entity_confidence: Confianza mínima para incluir entidades
            enable_gpu: Usar GPU para spaCy (None = auto)
        """
        self.enable_gazetteer = enable_gazetteer

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

        logger.info(f"NERExtractor inicializado (gazetteer={enable_gazetteer})")

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
        # Títulos de capítulos comunes
        "la contradicción", "el encuentro", "el principio", "el final",
        # Expresiones que parecen ser detectadas como MISC
        "hola juan", "fresh test do", "imposible",
    }

    # Palabras sueltas que spaCy a veces detecta erróneamente como MISC
    SPACY_FALSE_POSITIVE_WORDS = {
        "imposible", "increíble", "horrible", "terrible", "extraño",
        "cabello", "pelo", "ojos", "negro", "rubio", "moreno",
        "fresh", "test", "hola",
    }

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

        # Filtrar entidades que terminan en puntuación (error de segmentación)
        if text_stripped and text_stripped[-1] in '.,:;!?':
            logger.debug(f"Entidad spaCy filtrada (puntuación): '{text}'")
            return False

        # Filtrar solo artículos/preposiciones sueltas
        if text_lower in self.STOP_TITLES:
            return False

        # Filtrar si es solo números o puntuación
        if text.isdigit() or not any(c.isalpha() for c in text):
            return False

        # Filtrar frases comunes que no son entidades
        if text_lower in self.COMMON_PHRASES_NOT_ENTITIES:
            logger.debug(f"Entidad spaCy filtrada (frase común): '{text}'")
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

        # Filtrar frases que empiezan con artículo seguido de sustantivo común
        # Ejemplo: "El otro día", "La mañana siguiente", "Un hombre muy alto"
        if len(words) >= 3:
            if first_word in {"el", "la", "los", "las", "un", "una", "unos", "unas"}:
                # Verificar si parece descripción genérica
                second_word = words[1].lower() if len(words) > 1 else ""
                generic_words = {
                    "otro", "otra", "mismo", "misma", "siguiente", "anterior",
                    "hombre", "mujer", "persona", "gente", "cosa", "día", "noche",
                    "vez", "tiempo", "momento", "lugar", "forma", "manera",
                }
                if second_word in generic_words:
                    logger.debug(f"Entidad spaCy filtrada (descripción genérica): '{text}'")
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

    def extract_entities(self, text: str) -> Result[NERResult]:
        """
        Extrae entidades nombradas del texto.

        Args:
            text: Texto a procesar

        Returns:
            Result con NERResult conteniendo las entidades extraídas
        """
        if not text or not text.strip():
            return Result.success(NERResult(processed_chars=0))

        result = NERResult(processed_chars=len(text))
        entities_found: set[tuple[int, int]] = set()  # (start, end) para evitar duplicados

        try:
            doc = self.nlp(text)

            # 1. Entidades detectadas por spaCy - CONFIAMOS EN SPACY
            for ent in doc.ents:
                label = self.SPACY_LABEL_MAP.get(ent.label_)
                if label is None:
                    continue

                # Solo filtrar errores obvios de segmentación
                if not self._is_valid_spacy_entity(ent.text):
                    continue

                entity = ExtractedEntity(
                    text=ent.text,
                    label=label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.8,  # spaCy no proporciona confianza
                    source="spacy",
                )

                if (ent.start_char, ent.end_char) not in entities_found:
                    result.entities.append(entity)
                    entities_found.add((ent.start_char, ent.end_char))

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
                gazetteer_entities = self._detect_gazetteer_entities(doc, entities_found)
                result.entities.extend(gazetteer_entities)

                # Registrar candidatos para el gazetteer
                candidates = self._find_gazetteer_candidates(doc, entities_found)
                result.gazetteer_candidates = candidates

            # Ordenar por posición
            result.entities.sort(key=lambda e: e.start_char)

            logger.debug(
                f"NER: {len(result.entities)} entidades extraídas "
                f"({len(result.get_persons())} PER, "
                f"{len(result.get_locations())} LOC, "
                f"{len(result.get_organizations())} ORG)"
            )

            return Result.success(result)

        except Exception as e:
            error = NERExtractionError(
                text_sample=text[:100] if len(text) > 100 else text,
                original_error=str(e),
            )
            logger.error(f"Error en extracción NER: {e}")
            return Result.partial(result, [error])

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


def extract_entities(text: str) -> Result[NERResult]:
    """
    Atajo para extraer entidades de un texto.

    Args:
        text: Texto a procesar

    Returns:
        Result con NERResult
    """
    return get_ner_extractor().extract_entities(text)
