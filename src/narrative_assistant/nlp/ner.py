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
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import get_config
from ..core.errors import ErrorSeverity, NLPError
from ..core.result import Result
from . import morpho_utils
from .entity_validator import get_entity_validator
from .ner_coord_splitter import NERCoordSplitterMixin
from .ner_patterns import NERPatternDetectorMixin
from .ner_validators import NERValidatorMixin
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
    canonical_form: str | None = None

    def __post_init__(self):
        """Normaliza el texto y la forma canónica."""
        # Puntuación que no debería aparecer en bordes de entidades
        # Include typographic quotes to avoid leaving entities like “María as lowercase words.
        BOUNDARY_PUNCT = '–—-,.;:!?¿¡\'"()[]{}«»"" “”‘’'

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

        # Normalizar forma canónica (sin acentos para fusión)
        if self.canonical_form is None:
            self.canonical_form = morpho_utils.normalize_name(self.text)

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
    user_message: str | None = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"NER extraction error: {self.original_error}"
        self.user_message = (
            "Error al extraer entidades del texto. Se continuará con los resultados parciales."
        )
        super().__post_init__()


class NERExtractor(NERValidatorMixin, NERPatternDetectorMixin, NERCoordSplitterMixin):
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

    # Longitud mínima para considerar una entidad válida
    MIN_ENTITY_LENGTH = 2

    def __init__(
        self,
        enable_gazetteer: bool = True,
        min_entity_confidence: float = 0.5,
        enable_gpu: bool | None = None,
        use_llm_preprocessing: bool = True,
        use_transformer_ner: bool = True,
        transformer_ner_model: str | None = None,
    ):
        """
        Inicializa el extractor NER.

        Args:
            enable_gazetteer: Habilitar detección heurística de nombres
            min_entity_confidence: Confianza mínima para incluir entidades
            enable_gpu: Usar GPU para spaCy (None = auto)
            use_llm_preprocessing: Usar LLM como preprocesador para mejorar detección
            use_transformer_ner: Usar modelo transformer (PlanTL RoBERTa) como
                método adicional de detección NER
            transformer_ner_model: Modelo transformer a usar (None = auto/default)
        """
        self.enable_gazetteer = enable_gazetteer
        self.use_llm_preprocessing = use_llm_preprocessing
        self.use_transformer_ner = use_transformer_ner
        self._transformer_ner_model_key = transformer_ner_model

        config = get_config()
        # Usar 'is None' para permitir 0.0 como valor válido
        self.min_entity_confidence = (
            min_entity_confidence
            if min_entity_confidence is not None
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

        # Transformer NER (lazy loading)
        self._transformer_ner = None

        logger.info(
            f"NERExtractor inicializado (gazetteer={enable_gazetteer}, "
            f"llm={use_llm_preprocessing}, transformer={use_transformer_ner})"
        )

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

    # Pesos para votación multi-método NER
    NER_METHOD_WEIGHTS = {
        "roberta": 0.50,  # Transformer (PlanTL) - mejor F1
        "llm": 0.30,  # LLM (Ollama) - comprensión semántica
        "spacy": 0.20,  # spaCy - baseline estadístico
        "gazetteer": 0.10,  # Gazetteer - lookup
        "heuristic": 0.10,  # Heurísticas
    }

    def _apply_multi_method_voting(
        self,
        entities: list[ExtractedEntity],
        transformer_entities: list[ExtractedEntity],
        llm_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """
        Aplica votación multi-método: boost de confianza para entidades
        confirmadas por múltiples fuentes.

        Si el mismo texto+label aparece en >1 método, aumentamos confianza.
        """
        # Construir índice de textos canónicos detectados por cada método
        method_detections: dict[str, set[str]] = {}
        for ent in transformer_entities:
            key = f"{ent.label.value}:{(ent.canonical_form or ent.text).lower()}"
            method_detections.setdefault(key, set()).add("roberta")
        for ent in llm_entities:
            key = f"{ent.label.value}:{(ent.canonical_form or ent.text).lower()}"
            method_detections.setdefault(key, set()).add("llm")
        for ent in entities:
            if ent.source in ("spacy", "gazetteer", "heuristic"):
                key = f"{ent.label.value}:{(ent.canonical_form or ent.text).lower()}"
                method_detections.setdefault(key, set()).add(ent.source)

        # Aplicar boost de confianza
        for ent in entities:
            key = f"{ent.label.value}:{(ent.canonical_form or ent.text).lower()}"
            methods = method_detections.get(key, set())
            if len(methods) >= 3:
                # 3+ métodos coinciden: alta confianza
                ent.confidence = min(ent.confidence + 0.15, 0.98)
            elif len(methods) >= 2:
                # 2 métodos coinciden: boost moderado
                ent.confidence = min(ent.confidence + 0.08, 0.95)

        return entities

    def _extract_with_transformer(self, text: str) -> list[ExtractedEntity]:
        """
        Extrae entidades usando modelo transformer (PlanTL RoBERTa).

        El modelo transformer está fine-tuned en NER español y tiene mejor
        precisión que spaCy para entidades estándar (F1 ~82-85% vs ~65%).
        """
        try:
            from .transformer_ner import get_transformer_ner
        except ImportError:
            logger.debug("Módulo transformer_ner no disponible")
            return []

        try:
            if self._transformer_ner is None:
                self._transformer_ner = get_transformer_ner(
                    model_key=self._transformer_ner_model_key
                )

            raw_entities = self._transformer_ner.extract(text)
            result: list[ExtractedEntity] = []
            for ent in raw_entities:
                label = self.SPACY_LABEL_MAP.get(ent.label)
                if label is None:
                    # Intentar mapeo directo desde EntityLabel
                    try:
                        label = EntityLabel(ent.label)
                    except ValueError:
                        continue

                # Verificar que el texto coincide con la posición original
                original_text = text[ent.start : ent.end]
                entity_text = original_text if original_text.strip() else ent.text

                entity = ExtractedEntity(
                    text=entity_text,
                    label=label,
                    start_char=ent.start,
                    end_char=ent.end,
                    confidence=min(ent.score, 0.95),  # Cap: transformer tiende a dar >0.99
                    source="roberta",
                )
                result.append(entity)

            return result

        except Exception as e:
            logger.warning(f"Error en transformer NER: {e}")
            return []

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

    def _parse_llm_json_ner(self, response: str) -> dict | None:
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
        pattern = r"\b" + re.escape(entity_text) + r"\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.start()

        # Búsqueda parcial (para casos como "doctor García" vs "García")
        words = entity_text.split()
        if len(words) > 1:
            # Buscar la última palabra (normalmente el apellido)
            last_word = words[-1]
            match = re.search(r"\b" + re.escape(last_word) + r"\b", text, re.IGNORECASE)
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

            entities_to_verify.append(
                {
                    "text": ent.text,
                    "type": ent.label.value,
                    "context": context,
                    "entity": ent,
                }
            )

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

    def _postprocess_misc_entities(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
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
            "clarín",
            "azorín",
            "el greco",
            "el cid",
            "la regenta",
            "el magistral",
            "la dama",
            "el caballero",
            "tirso de molina",
            "fernán caballero",
            "benito el garbancero",
        }

        # Lugares ficticios conocidos -> LOC
        FICTIONAL_PLACES = {
            "vetusta",
            "orbajosa",
            "marineda",
            "ficóbriga",
            "pilares",
            "castroforte",
            "villabajo",
            "macondo",
        }

        # Palabras MISC que son claramente errores y deben filtrarse
        MISC_ERRORS = {
            # Verbos imperativos que spaCy confunde
            "levántate",
            "levantate",
            "siéntate",
            "sientate",
            "ven",
            "vete",
            # Adverbios/expresiones comunes
            "tanta",
            "tanto",
            "más",
            "menos",
            "bien",
            "mal",
            # Artículos/preposiciones que escapan
            "y al",
            "el",
            "la",
            "los",
            "las",
            # Palabras genéricas
            "naturaleza",
            "diccionario",
            "dios",
        }

        # MISC que son probablemente apellidos -> PER
        # (apellidos comunes españoles que aparecen solos)
        COMMON_SURNAMES_AS_PER = {
            "ozores",
            "garcía",
            "martínez",
            "lópez",
            "fernández",
            "rodríguez",
            "pérez",
            "sánchez",
            "romero",
            "navarro",
            "gonzález",
            "díaz",
            "hernández",
            "moreno",
            "muñoz",
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
            if "_" in entity.text:
                logger.debug(f"MISC filtrado (guion bajo): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar MISC que son claramente errores
            if text_lower in MISC_ERRORS:
                logger.debug(f"MISC filtrado (error conocido): '{entity.text}'")
                filtered_count += 1
                continue

            # Filtrar si empieza con artículo + solo 1-2 palabras más (ej: "El público")
            if word_count <= 3 and text_lower.startswith(
                ("el ", "la ", "los ", "las ", "un ", "una ")
            ):
                # Excepto si es pseudónimo conocido
                if text_lower not in LITERARY_PSEUDONYMS:
                    logger.debug(f"MISC filtrado (artículo + frase): '{entity.text}'")
                    filtered_count += 1
                    continue

            # Reclasificar apellidos comunes a PER — solo si el contexto sugiere persona
            # Evita reclasificar "la García" (taberna), "calle Fernández" (lugar)
            if text_lower in COMMON_SURNAMES_AS_PER:
                # Verificar contexto si tenemos acceso al doc de spaCy
                is_person = True
                try:
                    if hasattr(self, "nlp") and self.nlp:
                        # Pequeño contexto alrededor de la entidad para analizar
                        ctx_text = entity.text
                        ctx_doc = self.nlp(ctx_text)
                        # Heurística simple: si el propio texto empieza con mayúscula
                        # y no tiene indicadores de lugar, asumir persona
                        is_person = morpho_utils.is_person_context(ctx_doc, 0, len(ctx_text))
                except Exception:
                    is_person = True  # Default: asumir persona

                if is_person:
                    entity.label = EntityLabel.PER
                    entity.source = f"{entity.source}+reclassified"
                    logger.debug(f"MISC reclasificado a PER (apellido): '{entity.text}'")
                    reclassified_count += 1
                else:
                    logger.debug(f"MISC no reclasificado (contexto no es persona): '{entity.text}'")
                result.append(entity)
                continue

            # Reclasificar nombres compuestos (ej: "María Sánchez") a PER
            # Si alguna palabra del nombre es un apellido conocido y todas empiezan con mayúscula
            words = entity.text.split()
            if 2 <= len(words) <= 3 and all(w[0].isupper() for w in words):
                words_lower = [w.lower() for w in words]
                has_surname = any(w in COMMON_SURNAMES_AS_PER for w in words_lower)
                if has_surname:
                    entity.label = EntityLabel.PER
                    entity.source = f"{entity.source}+reclassified_fullname"
                    logger.debug(f"MISC reclasificado a PER (nombre completo): '{entity.text}'")
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

    # _is_valid_spacy_entity, _is_valid_heuristic_candidate, _is_high_quality_entity
    # and constants (STOP_TITLES, HEURISTIC_FALSE_POSITIVES, COMMON_PHRASES_NOT_ENTITIES,
    # PHYSICAL_DESCRIPTION_PATTERNS, SPACY_FALSE_POSITIVE_WORDS) are inherited from
    # NERValidatorMixin (see ner_validators.py)
    _VALIDATORS_FROM_MIXIN = True  # marker for grep/search

    def extract_entities(
        self,
        text: str,
        progress_callback: Callable | None = None,
        project_id: int | None = None,
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
                report_progress("ner", 0.0, "Analizando el texto...")
                llm_entities = self._preprocess_with_llm(text)
                report_progress("ner", 0.3, f"Encontrados {len(llm_entities)} posibles nombres...")
                logger.info(f"LLM preprocesador: {len(llm_entities)} entidades detectadas")

                # Añadir entidades del LLM primero (tienen prioridad)
                for entity in llm_entities:
                    pos = (entity.start_char, entity.end_char)
                    if pos not in entities_found:
                        result.entities.append(entity)
                        entities_found.add(pos)

            # 0.5 Transformer NER (PlanTL RoBERTa)
            transformer_entities: list[ExtractedEntity] = []
            if self.use_transformer_ner:
                report_progress("ner", 0.35, "Analizando con modelo transformer...")
                transformer_entities = self._extract_with_transformer(text)
                for entity in transformer_entities:
                    pos = (entity.start_char, entity.end_char)
                    if pos not in entities_found:
                        # No solapar con LLM
                        overlaps = False
                        for llm_ent in llm_entities:
                            if self._entities_overlap(
                                entity.start_char, entity.end_char,
                                llm_ent.start_char, llm_ent.end_char,
                            ):
                                overlaps = True
                                break
                        if not overlaps:
                            result.entities.append(entity)
                            entities_found.add(pos)
                if transformer_entities:
                    logger.info(
                        f"Transformer NER: {len(transformer_entities)} entidades detectadas"
                    )
                    # S1-03: Auto-alimentar gazetteer con entidades transformer
                    # (mayor confianza que spaCy, no requieren _is_high_quality)
                    if self.enable_gazetteer:
                        with self._gazetteer_lock:
                            for ent in transformer_entities:
                                if (
                                    ent.confidence >= 0.7
                                    and ent.canonical_form
                                    and len(self.dynamic_gazetteer) < MAX_GAZETTEER_SIZE
                                ):
                                    self.dynamic_gazetteer[ent.canonical_form] = ent.label

            report_progress("ner", 0.4, "Buscando personajes y lugares...")
            doc = self.nlp(text)
            report_progress("ner", 0.7, "Identificando menciones en el texto...")

            # 1. Entidades detectadas por spaCy
            for ent in doc.ents:
                label = self.SPACY_LABEL_MAP.get(ent.label_)
                if label is None:
                    continue

                # Solo filtrar errores obvios de segmentación
                # Pasamos el span de spaCy para usar POS tags (filtro principal)
                if not self._is_valid_spacy_entity(ent.text, spacy_span=ent):
                    # Intentar extraer sub-entidades de entidades mal segmentadas
                    # (ej: "María\n\nMaría Sánchez" -> "María Sánchez")
                    if "\n" in ent.text:
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

                # Verificar solapamiento con entidades LLM o transformer
                overlaps_prior = False
                for prior_ent in llm_entities + transformer_entities:
                    if self._entities_overlap(
                        ent.start_char, ent.end_char,
                        prior_ent.start_char, prior_ent.end_char,
                    ):
                        overlaps_prior = True
                        break

                if overlaps_prior:
                    continue  # LLM/transformer tienen prioridad

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
                report_progress("ner", 0.80, "Buscando más apariciones de nombres conocidos...")
                gazetteer_entities = self._detect_gazetteer_entities(doc, entities_found)
                result.entities.extend(gazetteer_entities)

                # Registrar candidatos para el gazetteer
                candidates = self._find_gazetteer_candidates(doc, entities_found)
                result.gazetteer_candidates = candidates

            # 2.3 Detección de patrones título+apellido ("doctor Ramírez", "coronel Salgado")
            # NOTA: Esta función MODIFICA result.entities in-place para extender entidades
            report_progress("ner", 0.82, "Detectando títulos (doctor, señor...)...")
            title_entities = self._detect_title_name_patterns(
                doc, text, entities_found, result.entities
            )
            # Solo agregar las entidades completamente nuevas (no extensiones)
            for ent in title_entities:
                result.entities.append(ent)

            # 2.4 Detección de lugares compuestos ("Valle Marineris", "Monte Olimpo")
            # NOTA: Similar a títulos, extiende entidades LOC existentes
            report_progress("ner", 0.83, "Identificando nombres de lugares...")
            compound_loc_entities = self._detect_compound_locations(
                doc, text, entities_found, result.entities
            )
            for ent in compound_loc_entities:
                result.entities.append(ent)

            # 2.4b Detección de personas compuestas con partículas
            # ("García de la Vega", "De la Fuente")
            report_progress("ner", 0.84, "Detectando apellidos con partículas...")
            compound_per_entities = self._detect_compound_persons(
                doc, text, entities_found, result.entities
            )
            for ent in compound_per_entities:
                result.entities.append(ent)

            # 2.5 Separar entidades coordinadas ("Pedro y Carmen" -> ["Pedro", "Carmen"])
            report_progress("ner", 0.85, "Analizando nombres compuestos...")
            result.entities = self._split_coordinated_entities(doc, result.entities)

            # 2.6 Votación multi-método: boost de confianza para entidades
            # detectadas por múltiples fuentes (spaCy, transformer, LLM)
            if transformer_entities or llm_entities:
                result.entities = self._apply_multi_method_voting(
                    result.entities, transformer_entities, llm_entities
                )

            # 3. Validación multi-capa (filtra falsos positivos)
            if enable_validation and result.entities:
                report_progress("ner", 0.90, "Verificando detecciones...")
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
                    text: score.to_dict() for text, score in validation_result.scores.items()
                }
                result.validation_method = validation_result.validation_method

                logger.info(
                    f"Validación: {len(validation_result.valid_entities)} válidas, "
                    f"{len(validation_result.rejected_entities)} rechazadas "
                    f"(método: {validation_result.validation_method})"
                )

            # 4. Verificación LLM para entidades de baja confianza (segunda capa)
            if self.use_llm_preprocessing and result.entities:
                report_progress("ner", 0.93, "Confirmando resultados...")
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

            report_progress("ner", 1.0, f"Encontradas {len(result.entities)} menciones")

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
        parts = re.split(r"\n+", malformed_text)

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

            token.text.lower().strip()

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
_ner_extractor: NERExtractor | None = None


def get_ner_extractor(
    enable_gazetteer: bool = True,
    enable_gpu: bool | None = None,
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
    project_id: int | None = None,
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
    known_entities: list[str] | None = None,
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
            mention_text = match.group(1).strip().strip("\"'")

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
                    text=text[pos : pos + len(mention_text)],  # Usar capitalización original
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
        return Result.failure(
            NLPError(
                message=f"Error en detección de personajes implícitos: {e}",
                severity=ErrorSeverity.WARNING,
            )
        )
