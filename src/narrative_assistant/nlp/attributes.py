"""
Extracción de Atributos de entidades narrativas.

.. note:: MÓDULO EN PROCESO DE UNIFICACIÓN

    Este módulo coexiste con `narrative_assistant.nlp.extraction` que proporciona
    una arquitectura más limpia con Strategy Pattern. Ambos sistemas funcionan
    y están integrados en el pipeline.

    Para nuevos desarrollos, se recomienda usar directamente:
    - `from narrative_assistant.nlp.extraction import AttributeExtractionPipeline`

    Este módulo (`attributes.py`) seguirá funcionando y manteniéndose.

Sistema multi-método con votación:
1. LLM (Ollama): Extracción semántica profunda - Peso 40%
2. Embeddings: Similitud semántica con patrones - Peso 25%
3. Dependency Parsing (spaCy): Análisis sintáctico - Peso 20%
4. Patrones (regex): Alta precisión para casos conocidos - Peso 15%

Incluye filtro de metáforas para evitar falsos positivos como
"sus ojos eran dos luceros" o "era alto como un roble".

Tipos de atributos soportados:
- Personajes: físicos (ojos, pelo, edad, altura), psicológicos, roles
- Lugares: características, clima, tamaño
- Objetos: material, color, tamaño, estado
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..core.result import Result
from ..core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)

# Pesos de votación por método (defaults heurísticos)
# Se reemplazan automáticamente por pesos aprendidos si existe default_weights.json
DEFAULT_METHOD_WEIGHTS = {
    "llm": 0.40,        # Mayor peso - comprensión semántica
    "embeddings": 0.25,  # Similitud semántica
    "dependency": 0.20,  # Análisis sintáctico
    "patterns": 0.15,    # Patrones regex (fallback)
}

# Pesos activos (pueden cambiar si se cargan pesos entrenados)
METHOD_WEIGHTS = dict(DEFAULT_METHOD_WEIGHTS)


def _load_default_trained_weights() -> None:
    """
    Carga pesos entrenados por defecto si existe el archivo.

    Se ejecuta automáticamente al importar el módulo.
    Busca en: training_data/default_weights.json
    """
    global METHOD_WEIGHTS

    try:
        weights_file = Path(__file__).parent / "training_data" / "default_weights.json"
        if weights_file.exists():
            with open(weights_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            weights = data.get("weights", {})
            if weights:
                METHOD_WEIGHTS.update(weights)
                # Normalizar
                total = sum(METHOD_WEIGHTS.values())
                if total > 0:
                    for method in METHOD_WEIGHTS:
                        METHOD_WEIGHTS[method] /= total
                logger.debug(f"Pesos entrenados cargados: {METHOD_WEIGHTS}")
    except Exception as e:
        logger.debug(f"No se pudieron cargar pesos entrenados: {e}")


# Cargar pesos entrenados automáticamente al importar
_load_default_trained_weights()


class AttributeCategory(Enum):
    """Categorías de atributos."""

    # Personajes/seres vivos
    PHYSICAL = "physical"  # Ojos, pelo, altura, edad
    PSYCHOLOGICAL = "psychological"  # Personalidad, temperamento
    SOCIAL = "social"  # Profesión, rol, relaciones
    ABILITY = "ability"  # Habilidades, poderes

    # Lugares
    GEOGRAPHIC = "geographic"  # Ubicación, clima, terreno
    ARCHITECTURAL = "architectural"  # Estilo, tamaño, estado

    # Objetos
    MATERIAL = "material"  # De qué está hecho
    APPEARANCE = "appearance"  # Color, forma, tamaño
    FUNCTION = "function"  # Para qué sirve
    STATE = "state"  # Condición actual


class AttributeKey(Enum):
    """Claves de atributos conocidas."""

    # Físicos - personajes
    EYE_COLOR = "eye_color"
    HAIR_COLOR = "hair_color"
    HAIR_TYPE = "hair_type"
    HAIR_MODIFICATION = "hair_modification"  # teñido, natural, decolorado, mechas
    AGE = "age"
    HEIGHT = "height"
    BUILD = "build"
    SKIN = "skin"
    DISTINCTIVE_FEATURE = "distinctive_feature"

    # Psicológicos
    PERSONALITY = "personality"
    TEMPERAMENT = "temperament"
    FEAR = "fear"
    DESIRE = "desire"

    # Sociales
    PROFESSION = "profession"
    TITLE = "title"
    RELATIONSHIP = "relationship"
    NATIONALITY = "nationality"

    # Lugares
    CLIMATE = "climate"
    TERRAIN = "terrain"
    SIZE = "size"
    LOCATION = "location"

    # Objetos
    MATERIAL = "material"
    COLOR = "color"
    CONDITION = "condition"

    # Genérico
    OTHER = "other"


@dataclass
class ExtractedAttribute:
    """
    Un atributo extraído del texto.

    Attributes:
        entity_name: Nombre de la entidad asociada
        category: Categoría del atributo
        key: Clave del atributo
        value: Valor extraído
        source_text: Texto original de donde se extrajo
        start_char: Posición de inicio en el texto
        end_char: Posición de fin
        confidence: Confianza de la extracción (0.0-1.0)
        is_negated: Si el atributo está negado ("no tenía ojos verdes")
        is_metaphor: Si se detectó como posible metáfora
        chapter_id: ID del capítulo donde se encontró
    """

    entity_name: str
    category: AttributeCategory
    key: AttributeKey
    value: str
    source_text: str
    start_char: int
    end_char: int
    confidence: float = 0.8
    is_negated: bool = False
    is_metaphor: bool = False
    chapter_id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "entity_name": self.entity_name,
            "category": self.category.value,
            "key": self.key.value,
            "value": self.value,
            "source_text": self.source_text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
            "is_negated": self.is_negated,
            "is_metaphor": self.is_metaphor,
            "chapter_id": self.chapter_id,
        }


@dataclass
class AttributeExtractionResult:
    """
    Resultado de la extracción de atributos.

    Attributes:
        attributes: Lista de atributos extraídos
        processed_chars: Caracteres procesados
        metaphors_filtered: Número de metáforas filtradas
    """

    attributes: list[ExtractedAttribute] = field(default_factory=list)
    processed_chars: int = 0
    metaphors_filtered: int = 0

    @property
    def by_entity(self) -> dict[str, list[ExtractedAttribute]]:
        """Agrupa atributos por entidad."""
        grouped: dict[str, list[ExtractedAttribute]] = {}
        for attr in self.attributes:
            if attr.entity_name not in grouped:
                grouped[attr.entity_name] = []
            grouped[attr.entity_name].append(attr)
        return grouped

    @property
    def by_key(self) -> dict[str, list[ExtractedAttribute]]:
        """Agrupa atributos por clave."""
        grouped: dict[str, list[ExtractedAttribute]] = {}
        for attr in self.attributes:
            key = attr.key.value
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(attr)
        return grouped


@dataclass
class AttributeExtractionError(NLPError):
    """Error durante la extracción de atributos."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Attribute extraction error: {self.original_error}"
        self.user_message = (
            "Error al extraer atributos. "
            "Se continuará con los resultados parciales."
        )
        super().__post_init__()


# =============================================================================
# Patrones de extracción
# =============================================================================

# Colores válidos para ojos y pelo (español)
COLORS = {
    "azul", "azules", "verde", "verdes", "marrón", "marrones", "castaño",
    "castaños", "negro", "negros", "gris", "grises", "miel", "avellana",
    "ámbar", "violeta", "dorado", "dorados", "plateado", "plateados",
    "rubio", "rubios", "pelirrojo", "pelirrojos", "canoso", "canosos",
    "blanco", "blancos", "oscuro", "oscuros", "claro", "claros",
    "rojo", "rojos", "cobrizo", "cobrizos", "azabache",
}

# Tipos de pelo
HAIR_TYPES = {
    "liso", "rizado", "ondulado", "encrespado", "lacio", "fino", "grueso",
    "abundante", "escaso", "largo", "corto", "rapado", "calvo",
}

# Modificaciones de cabello (teñido, natural, etc.)
# Consenso: teñido puede cambiar libremente, solo alerta si pasa a "natural"
HAIR_MODIFICATIONS = {
    "natural", "teñido", "teñida", "decolorado", "decolorada",
    "mechas", "reflejos", "tinte", "de bote",  # coloquial: "rubia de bote"
    "oxigenado", "oxigenada", "pintado", "pintada",
}

# Constitución física
BUILD_TYPES = {
    "alto", "alta", "altos", "altas",
    "bajo", "baja", "bajos", "bajas",
    "delgado", "delgada", "delgados", "delgadas",
    "corpulento", "corpulenta", "corpulentos", "corpulentas",
    "esbelto", "esbelta", "esbeltos", "esbeltas",
    "robusto", "robusta", "robustos", "robustas",
    "musculoso", "musculosa", "musculosos", "musculosas",
    "gordo", "gorda", "gordos", "gordas",
    "flaco", "flaca", "flacos", "flacas",
    "atlético", "atlética", "atléticos", "atléticas",
    "enclenque", "enclenques",
    "fornido", "fornida", "fornidos", "fornidas",
}

# Rasgos de personalidad
PERSONALITY_TRAITS = {
    "amable", "cruel", "tímido", "tímida", "extrovertido", "extrovertida",
    "introvertido", "introvertida", "valiente", "cobarde", "leal", "traidor",
    "traidora", "honesto", "honesta", "mentiroso", "mentirosa", "generoso",
    "generosa", "tacaño", "tacaña", "paciente", "impaciente", "orgulloso",
    "orgullosa", "humilde", "arrogante", "sabio", "sabia", "ingenuo",
    "ingenua", "astuto", "astuta", "torpe",
}


# =============================================================================
# Helpers para entity_mentions
# =============================================================================

# Tipo para menciones de entidad: (name, start, end, entity_type)
# entity_type puede ser: "PER", "LOC", "ORG", "MISC", None
EntityMention = tuple[str, int, int, Optional[str]]


def _normalize_entity_mentions(
    entity_mentions: Optional[list[tuple]] | None,
) -> list[EntityMention]:
    """
    Normaliza entity_mentions al formato de 4 elementos.

    Soporta tanto el formato antiguo (3 elementos: name, start, end)
    como el nuevo (4 elementos: name, start, end, entity_type).

    Args:
        entity_mentions: Lista de menciones en cualquier formato

    Returns:
        Lista de menciones normalizadas como (name, start, end, entity_type)
    """
    if not entity_mentions:
        return []

    normalized = []
    for mention in entity_mentions:
        if len(mention) == 3:
            # Formato antiguo: (name, start, end) -> agregar None como entity_type
            name, start, end = mention
            normalized.append((name, start, end, None))
        elif len(mention) >= 4:
            # Formato nuevo: (name, start, end, entity_type)
            name, start, end, entity_type = mention[:4]
            normalized.append((name, start, end, entity_type))
        else:
            logger.warning(f"entity_mention con formato inválido: {mention}")
            continue

    return normalized


def _is_person_entity(entity_type: Optional[str]) -> bool:
    """Verifica si el tipo de entidad es una persona."""
    if entity_type is None:
        return True  # Si no hay tipo, asumir que puede ser persona
    return entity_type.upper() in ("PER", "PERSON", "PERS")


def _is_location_entity(entity_type: Optional[str]) -> bool:
    """Verifica si el tipo de entidad es una ubicación."""
    if entity_type is None:
        return False  # Si no hay tipo, no asumir ubicación
    return entity_type.upper() in ("LOC", "LOCATION", "GPE")


# Patrones de extracción: (regex, key, categoría, confianza_base)
# Los grupos de captura deben ser: (entidad, valor) o (valor, entidad)
ATTRIBUTE_PATTERNS: list[tuple[str, AttributeKey, AttributeCategory, float, bool]] = [
    # === OJOS ===
    # "Juan tenía ojos verdes" / "María tenía unos ojos azules"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+ten[íi]a\s+(?:unos\s+)?ojos\s+(\w+)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.9,
        False,  # (entidad, valor)
    ),
    # "los ojos verdes de Juan"
    (
        r"los\s+ojos\s+(\w+)\s+de\s+(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        True,  # (valor, entidad)
    ),
    # "Juan, de ojos verdes,"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)(?:,\s+de\s+ojos\s+(\w+))",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "sus ojos verdes" (requiere contexto de entidad cercana)
    (
        r"sus\s+ojos\s+(\w+)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.75,  # Confianza media-alta, resuelve "sus" con _find_nearest_entity
        False,
    ),
    # "de ojos azules" (requiere contexto de entidad cercana)
    (
        r"de\s+ojos\s+(\w+)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.65,
        False,
    ),
    # "con ... y ojos marrones" / "y ojos azules" (en listas de características)
    # Ejemplo: "con barba espesa y ojos marrones"
    (
        r"(?:con\s+\w+(?:\s+\w+)?(?:\s+y\s+\w+(?:\s+\w+)?)?\s+y\s+)?ojos\s+"
        r"(azules|verdes|marrones|negros|grises|castaños|miel|avellana|ámbar|claros|oscuros)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.7,  # Mayor confianza para colores conocidos
        False,
    ),
    # "ojos azules" (en diálogos o descripciones genéricas)
    (
        r"ojos\s+(\w+)",
        AttributeKey.EYE_COLOR,
        AttributeCategory.PHYSICAL,
        0.5,  # Baja confianza, muy genérico
        False,
    ),

    # === PELO/CABELLO ===
    # "Tenía el cabello largo y negro" - TIPO (largo/corto)
    (
        r"[Tt]en[íi]a\s+(?:el\s+)?(?:pelo|cabello)\s+(largo|corto|liso|rizado|ondulado)",
        AttributeKey.HAIR_TYPE,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "Tenía el cabello largo y negro" - COLOR (después de tipo)
    (
        r"[Tt]en[íi]a\s+(?:el\s+)?(?:pelo|cabello)\s+(?:largo|corto|liso|rizado|ondulado)\s+y\s+"
        r"(negro|rubio|castaño|pelirrojo|canoso|moreno|blanco|gris)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "Llevaba el cabello corto y rubio" - TIPO
    (
        r"[Ll]levaba\s+(?:el\s+)?(?:pelo|cabello)\s+(largo|corto|liso|rizado|ondulado|recogido|suelto)",
        AttributeKey.HAIR_TYPE,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "Llevaba el cabello corto y rubio" - COLOR
    (
        r"[Ll]levaba\s+(?:el\s+)?(?:pelo|cabello)\s+(?:largo|corto|liso|rizado|ondulado)\s+y\s+"
        r"(negro|rubio|castaño|pelirrojo|canoso|moreno|blanco|gris)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "Cabello negro y largo" - ambos en cualquier orden
    (
        r"(?:pelo|cabello)\s+(negro|rubio|castaño|pelirrojo|canoso|moreno|blanco|gris)"
        r"\s+y\s+(largo|corto|liso|rizado|ondulado)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.8,
        False,
    ),
    # "Juan tenía el pelo negro" / "María tenía cabello rubio"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+ten[íi]a\s+(?:el\s+)?(?:pelo|cabello)\s+(\w+)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.9,
        False,
    ),
    # "el pelo negro de Juan"
    (
        r"(?:el\s+)?(?:pelo|cabello)\s+(\w+)\s+de\s+(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        True,
    ),
    # "Juan, de pelo canoso," / "María, de cabello rubio"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)(?:,\s+de\s+(?:pelo|cabello)\s+(\w+))",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "de cabello rubio" (después de mención cercana)
    (
        r"de\s+(?:pelo|cabello)\s+(\w+)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.65,
        False,
    ),
    # "su cabello rubio" o "su pelo negro" (requiere contexto)
    (
        r"su\s+(?:pelo|cabello)\s+(\w+)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.6,
        False,
    ),
    # "el cabello negro" o "el pelo rubio" (genérico, requiere contexto)
    (
        r"el\s+(?:pelo|cabello)\s+(\w+)",
        AttributeKey.HAIR_COLOR,
        AttributeCategory.PHYSICAL,
        0.55,
        False,
    ),

    # === MODIFICACIÓN DE CABELLO (teñido/natural) ===
    # "era rubia de bote" / "rubia teñida"
    (
        r"(?:rubia?|morena?|pelirroja?)\s+(de\s+bote|teñid[oa])",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.9,
        False,
    ),
    # "el cabello teñido" / "pelo teñido" / "cabello decolorado"
    (
        r"(?:el\s+)?(?:pelo|cabello)\s+(teñido|teñida|decolorado|decolorada|natural|oxigenado|oxigenada)",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "tenía el pelo teñido" / "llevaba mechas"
    (
        r"(?:ten[íi]a|llevaba)\s+(?:el\s+)?(?:pelo|cabello)\s+(teñido|teñida|con\s+mechas|con\s+reflejos)",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),
    # "se había teñido" / "se tiñó el pelo"
    (
        r"se\s+(?:había\s+)?(?:teñido|decolorado|pintado|oxigenado)",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.9,
        False,
    ),
    # "con mechas" / "con reflejos" / "con tinte"
    (
        r"(?:pelo|cabello)\s+(?:con\s+)?(mechas|reflejos|tinte)",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.8,
        False,
    ),
    # "su color natural" / "pelo natural"
    (
        r"(?:su\s+)?(?:color\s+)?(?:de\s+pelo\s+)?natural",
        AttributeKey.HAIR_MODIFICATION,
        AttributeCategory.PHYSICAL,
        0.75,
        False,
    ),

    # === EDAD ===
    # "Juan, de 25 años,"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)(?:,\s+de\s+(\d+)\s+años)",
        AttributeKey.AGE,
        AttributeCategory.PHYSICAL,
        0.95,
        False,
    ),
    # "Juan tenía 25 años"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+ten[íi]a\s+(\d+)\s+años",
        AttributeKey.AGE,
        AttributeCategory.PHYSICAL,
        0.9,
        False,
    ),
    # "a sus 25 años" (contexto necesario)
    (
        r"a\s+sus\s+(\d+)\s+años",
        AttributeKey.AGE,
        AttributeCategory.PHYSICAL,
        0.6,
        False,
    ),
    # "rondaba los 30"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+rondaba\s+los\s+(\d+)",
        AttributeKey.AGE,
        AttributeCategory.PHYSICAL,
        0.7,
        False,
    ),

    # === ALTURA/CONSTITUCIÓN ===
    # "Juan era alto" / "María era delgada"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+era\s+(alto|alta|bajo|baja|delgado|delgada|"
        r"corpulento|corpulenta|esbelto|esbelta|robusto|robusta|gordo|gorda|"
        r"flaco|flaca|musculoso|musculosa|atlético|atlética|fornido|fornida)",
        AttributeKey.BUILD,
        AttributeCategory.PHYSICAL,
        0.8,
        False,
    ),
    # "Era un hombre/mujer alto/bajo y fornido/delgada" (para pronombres)
    # Usa grupo no-capturador (?:muy\s+)? para ignorar "muy"
    (
        r"[EeÉé]l?\s+era\s+(?:un\s+)?(?:hombre|mujer)\s+(?:muy\s+)?(alto|alta|bajo|baja|"
        r"delgado|delgada|corpulento|corpulenta|fornido|fornida)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.75,
        False,
    ),
    # "era un hombre bajo y fornido" - 1 grupo para BUILD, resolver entidad
    (
        r"era\s+(?:un\s+)?(?:hombre|mujer)\s+(?:muy\s+)?(?:alto|alta|bajo|baja)\s+y\s+"
        r"(delgado|delgada|corpulento|corpulenta|fornido|fornida|esbelto|esbelta)",
        AttributeKey.BUILD,
        AttributeCategory.PHYSICAL,
        0.8,
        False,  # 1 grupo = resolver entidad con _find_nearest_entity
    ),
    # "Era alto y corpulento" (requiere contexto - un solo grupo)
    (
        r"[Ee]ra\s+((?:muy\s+)?(?:alto|alta|bajo|baja|delgado|delgada|"
        r"corpulento|corpulenta|esbelto|esbelta|robusto|robusta|gordo|gorda|"
        r"flaco|flaca|musculoso|musculosa|atlético|atlética|fornido|fornida)"
        r"(?:\s+y\s+(?:alto|alta|bajo|baja|delgado|delgada|"
        r"corpulento|corpulenta|esbelto|esbelta|robusto|robusta))?)",
        AttributeKey.BUILD,
        AttributeCategory.PHYSICAL,
        0.65,
        False,
    ),
    # "mujer alta" / "hombre bajo" (en contexto) - 1 grupo, resolver entidad desde contexto
    (
        r"(?:una?\s+)?(?:mujer|hombre)\s+(?:muy\s+)?(alto|alta|bajo|baja|delgado|delgada)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.7,
        False,  # 1 grupo = resolver entidad con _find_nearest_entity
    ),
    # "el alto Juan" / "la delgada María"
    (
        r"(?:el|la)\s+(alto|alta|bajo|baja|delgado|delgada|corpulento|corpulenta|"
        r"esbelto|esbelta)\s+(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.BUILD,
        AttributeCategory.PHYSICAL,
        0.75,
        True,
    ),
    # "Era una mujer alta, de aproximadamente treinta años" - 1 grupo, resolver entidad
    (
        r"[Ee]ra\s+(?:una?\s+)?(?:mujer|hombre)\s+(alto|alta|bajo|baja)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.75,
        False,  # 1 grupo = resolver entidad con _find_nearest_entity
    ),

    # === PERSONALIDAD ===
    # "Juan era amable" / "María era valiente"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+era\s+(amable|cruel|tímido|tímida|"
        r"valiente|cobarde|leal|honesto|honesta|generoso|generosa|"
        r"paciente|impaciente|orgulloso|orgullosa|humilde|arrogante|"
        r"sabio|sabia|ingenuo|ingenua|astuto|astuta)",
        AttributeKey.PERSONALITY,
        AttributeCategory.PSYCHOLOGICAL,
        0.75,
        False,
    ),

    # === PROFESIÓN/ROL ===
    # "Juan, el médico," / "María, la abogada,"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+),\s+(?:el|la)\s+(\w+),",
        AttributeKey.PROFESSION,
        AttributeCategory.SOCIAL,
        0.7,
        False,
    ),
    # "el doctor Juan" / "la profesora María"
    (
        r"(?:el|la)\s+(doctor|doctora|médico|médica|abogado|abogada|profesor|profesora|"
        r"capitán|capitana|rey|reina|príncipe|princesa|conde|condesa|duque|duquesa|"
        r"soldado|guerrero|guerrera|mago|maga|brujo|bruja|sacerdote|sacerdotisa)\s+"
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.PROFESSION,
        AttributeCategory.SOCIAL,
        0.85,
        True,
    ),
    # "era carpintero", "es médico" - profesiones con sufijos comunes (un grupo, requiere contexto)
    (
        r"[Ee]ra\s+(?:un\s+)?(\w+(?:ero|era|ista|or|ora|ico|ica|nte|dor|dora|tor|tora|ogo|oga|ino|ina|ario|aria|ador|adora))\b",
        AttributeKey.PROFESSION,
        AttributeCategory.SOCIAL,
        0.65,
        False,  # False = un grupo, necesita resolver entidad desde contexto
    ),
    # "trabaja como X", "trabajaba de X"
    (
        r"trabaj(?:a|aba)\s+(?:como|de)\s+(\w+)",
        AttributeKey.PROFESSION,
        AttributeCategory.SOCIAL,
        0.7,
        False,
    ),

    # === RASGOS DISTINTIVOS ===
    # "Juan tenía una cicatriz en..."
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+ten[íi]a\s+(?:una?\s+)?"
        r"(cicatriz|tatuaje|lunar|marca|mancha|cojera|parche)",
        AttributeKey.DISTINCTIVE_FEATURE,
        AttributeCategory.PHYSICAL,
        0.85,
        False,
    ),

    # ==========================================================================
    # LUGARES
    # ==========================================================================

    # === UBICACIÓN/CLIMA ===
    # "la ciudad de Valencia" / "el pueblo de Miraflores"
    (
        r"(?:la\s+)?(ciudad|pueblo|aldea|villa|capital)\s+de\s+"
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.LOCATION,
        AttributeCategory.GEOGRAPHIC,
        0.9,
        True,
    ),
    # "Mordor, un lugar oscuro y desolado"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+),\s+(?:un\s+)?lugar\s+"
        r"(oscuro|luminoso|frío|cálido|húmedo|seco|desolado|fértil|"
        r"peligroso|tranquilo|misterioso|antiguo|sagrado|maldito)",
        AttributeKey.TERRAIN,
        AttributeCategory.GEOGRAPHIC,
        0.75,
        False,
    ),
    # "el frío norte" / "las cálidas tierras del sur"
    (
        r"(?:el|la|las|los)\s+(frío|fría|cálido|cálida|helado|helada|"
        r"árido|árida|húmedo|húmeda)\s+(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.CLIMATE,
        AttributeCategory.GEOGRAPHIC,
        0.7,
        True,
    ),

    # === ARQUITECTURA ===
    # "el viejo castillo" / "la antigua fortaleza"
    (
        r"(?:el|la)\s+(viejo|vieja|antiguo|antigua|nuevo|nueva|"
        r"abandonado|abandonada|ruinoso|ruinosa|imponente|majestuoso|majestuosa)\s+"
        r"(castillo|fortaleza|torre|palacio|templo|iglesia|catedral|mansión|"
        r"cabaña|choza|taberna|posada)",
        AttributeKey.CONDITION,
        AttributeCategory.ARCHITECTURAL,
        0.75,
        True,
    ),

    # ==========================================================================
    # OBJETOS
    # ==========================================================================

    # === MATERIAL ===
    # "espada de acero" / "anillo de oro"
    (
        r"(espada|daga|cuchillo|hacha|lanza|escudo|armadura|casco|"
        r"anillo|collar|corona|cetro|copa|cáliz|cofre|baúl|"
        r"bastón|vara|libro|pergamino|llave|moneda)\s+de\s+"
        r"(oro|plata|bronce|hierro|acero|cobre|madera|cristal|"
        r"diamante|rubí|esmeralda|zafiro|obsidiana|hueso|cuero|"
        r"mithril|adamantio|valyrio)",
        AttributeKey.MATERIAL,
        AttributeCategory.MATERIAL,
        0.9,
        False,
    ),

    # === COLOR DE OBJETO ===
    # "capa roja" / "túnica negra"
    (
        r"(capa|túnica|manto|vestido|armadura|escudo|estandarte|bandera)\s+"
        r"(roja|rojo|negra|negro|blanca|blanco|azul|verde|dorada|dorado|"
        r"plateada|plateado|púrpura|carmesí|escarlata|gris)",
        AttributeKey.COLOR,
        AttributeCategory.APPEARANCE,
        0.85,
        False,
    ),
    # "la espada negra" / "el anillo dorado"
    (
        r"(?:el|la)\s+(espada|daga|anillo|corona|capa|libro|piedra|gema)\s+"
        r"(roja|rojo|negra|negro|blanca|blanco|azul|verde|dorada|dorado|"
        r"plateada|plateado|brillante|oscura|oscuro)",
        AttributeKey.COLOR,
        AttributeCategory.APPEARANCE,
        0.8,
        False,
    ),

    # ==========================================================================
    # PATRONES GENÉRICOS (menor confianza)
    # ==========================================================================

    # "X era conocido por su Y" - captura genérica
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\s+era\s+conocid[oa]\s+por\s+su\s+(\w+)",
        AttributeKey.OTHER,
        AttributeCategory.SOCIAL,
        0.6,
        False,
    ),
    # "X, famoso por su Y"
    (
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+),\s+famos[oa]\s+por\s+su\s+(\w+)",
        AttributeKey.OTHER,
        AttributeCategory.SOCIAL,
        0.6,
        False,
    ),
    # "la característica X de Y" (captura atributos mencionados explícitamente)
    (
        r"(?:la|el)\s+(\w+)\s+(?:característica|rasgo|cualidad)\s+de\s+"
        r"(\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)",
        AttributeKey.OTHER,
        AttributeCategory.PHYSICAL,
        0.65,
        True,
    ),
]

# Indicadores de metáfora/comparación a filtrar
METAPHOR_INDICATORS = [
    r"\bcomo\b",
    r"\bparec[íi]a\b",
    r"\bcual\b",
    r"\bsemejante\s+a\b",
    r"\btan\s+\w+\s+como\b",
    r"\bcomo\s+si\b",
    r"\bsi\s+fuera\b",
    r"\brecordaba\s+a\b",
    r"\bevocaba\b",
    r"\bsimulaba\b",
    r"\baparentemente\b",
]

# Indicadores de negación simple
NEGATION_INDICATORS = [
    r"\bno\b",
    r"\bnunca\b",
    r"\bjamás\b",
    r"\bsin\b",
    r"\bcarec[íi]a\b",
    r"\bfaltaba\b",
    r"\bningún\b",
    r"\bninguna\b",
    r"\bnada\s+de\b",
    r"\bni\s+siquiera\b",
]

# Patrones contrastivos: "No es X, sino Y" - el primer valor está negado
# Estos patrones indican que se debe extraer Y, no X
CONTRASTIVE_PATTERNS = [
    r"\bno\s+es\s+que\b.*?\bsino\b",  # "No es que X, sino Y"
    r"\bno\s+(?:era|tenía|fue)\b.*?\bsino\b",  # "no era X, sino Y"
    r"\b(?:era|tenía)\s+\w+,?\s+no\s+\w+\b",  # "era X, no Y" (X es verdadero)
]

# Indicadores de atributo temporal/pasado (no actual)
TEMPORAL_PAST_INDICATORS = [
    r"\bde\s+joven\b",
    r"\bde\s+niñ[oa]\b",
    r"\bde\s+pequeñ[oa]\b",
    r"\bantes\s+de\b",
    r"\bsolía\s+(?:ser|tener)\b",
    r"\ben\s+(?:su\s+)?juventud\b",
    r"\bcuando\s+era\s+(?:joven|niño|pequeño)\b",
    r"\ben\s+(?:la|aquella)\s+época\b",
    r"\bhace\s+(?:muchos\s+)?años\b",
    r"\ben\s+el\s+pasado\b",
]

# Indicadores de atributo condicional/hipotético (no real)
CONDITIONAL_INDICATORS = [
    r"\bsi\s+(?:fuera|tuviera|hubiera)\b",
    r"\bsería\b",
    r"\bpodría\s+(?:ser|tener)\b",
    r"\bimagina(?:ba)?\s+(?:que|a)\b",
    r"\bsoñaba\s+con\s+(?:ser|tener)\b",
    r"\bdesearía\b",
    r"\bquisiera\b",
]


class AttributeExtractor:
    """
    Extractor de atributos de entidades narrativas.

    Sistema multi-método con votación ponderada:
    1. LLM (Ollama): Extracción semántica profunda - comprende contexto
    2. Embeddings: Similitud semántica con descripciones conocidas
    3. Dependency parsing (spaCy): Análisis sintáctico - relaciones gramaticales
    4. Patrones regex: Alta precisión para casos conocidos (fallback)

    La combinación de métodos permite:
    - Generalizar a textos con errores ortográficos
    - Capturar atributos implícitos ("estudiaba lingüística" → profesión)
    - Mantener alta precisión con patrones conocidos

    Attributes:
        filter_metaphors: Si filtrar expresiones metafóricas
        min_confidence: Confianza mínima para incluir atributos
        use_llm: Usar LLM para extracción semántica
        use_embeddings: Usar embeddings para similitud
        use_dependency_extraction: Usar extracción por dependencias
        use_patterns: Usar patrones regex
    """

    def __init__(
        self,
        filter_metaphors: bool = True,
        min_confidence: float = 0.5,
        use_llm: bool = True,
        use_embeddings: bool = True,
        use_dependency_extraction: bool = True,
        use_patterns: bool = True,
    ):
        """
        Inicializa el extractor.

        Args:
            filter_metaphors: Filtrar metáforas y comparaciones
            min_confidence: Confianza mínima (0.0-1.0)
            use_llm: Habilitar extracción por LLM
            use_embeddings: Habilitar extracción por embeddings
            use_dependency_extraction: Habilitar extracción por dependencias
            use_patterns: Habilitar extracción por patrones regex
        """
        self.filter_metaphors = filter_metaphors
        self.min_confidence = min_confidence
        self.use_llm = use_llm
        self.use_embeddings = use_embeddings
        self.use_dependency_extraction = use_dependency_extraction
        self.use_patterns = use_patterns

        # Lazy-loaded components
        self._nlp = None  # spaCy
        self._llm_client = None  # Ollama client
        self._embeddings_model = None  # Sentence transformers

        # Compilar patrones
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.UNICODE), key, cat, conf, swap)
            for pattern, key, cat, conf, swap in ATTRIBUTE_PATTERNS
        ]

        self._metaphor_patterns = [
            re.compile(p, re.IGNORECASE) for p in METAPHOR_INDICATORS
        ]

        self._negation_patterns = [
            re.compile(p, re.IGNORECASE) for p in NEGATION_INDICATORS
        ]

        # Patrones contrastivos (No es X, sino Y)
        self._contrastive_patterns = [
            re.compile(p, re.IGNORECASE | re.DOTALL) for p in CONTRASTIVE_PATTERNS
        ]

        # Indicadores temporales (atributo pasado, no actual)
        self._temporal_past_patterns = [
            re.compile(p, re.IGNORECASE) for p in TEMPORAL_PAST_INDICATORS
        ]

        # Indicadores condicionales (atributo hipotético)
        self._conditional_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONDITIONAL_INDICATORS
        ]

        # Verbos copulativos para atributos (español)
        self._copulative_verbs = {
            "ser", "estar", "parecer", "resultar", "quedarse",
            "volverse", "ponerse", "hacerse", "convertirse",
        }

        # Verbos de posesión/descripción
        self._descriptive_verbs = {
            "tener", "poseer", "lucir", "mostrar", "presentar",
            "llevar", "vestir", "portar",
        }

    def _get_nlp(self):
        """Obtiene el modelo spaCy (lazy loading)."""
        if self._nlp is None:
            try:
                from .spacy_gpu import load_spacy_model
                self._nlp = load_spacy_model()
            except Exception as e:
                logger.warning(f"No se pudo cargar spaCy: {e}")
                self._nlp = False  # Marca que falló
        return self._nlp if self._nlp else None

    def _get_llm_client(self):
        """Obtiene el cliente LLM (lazy loading)."""
        if self._llm_client is None:
            try:
                from ..llm.client import get_llm_client
                self._llm_client = get_llm_client()
                if self._llm_client and self._llm_client.is_available:
                    logger.info(f"LLM disponible para atributos: {self._llm_client.model_name}")
                else:
                    self._llm_client = False
            except Exception as e:
                logger.warning(f"No se pudo cargar LLM client: {e}")
                self._llm_client = False
        return self._llm_client if self._llm_client else None

    def _get_embeddings_model(self):
        """Obtiene el modelo de embeddings (lazy loading)."""
        if self._embeddings_model is None:
            try:
                from .embeddings import get_embeddings_model
                self._embeddings_model = get_embeddings_model()
                if self._embeddings_model:
                    logger.info("Embeddings disponible para atributos")
                else:
                    self._embeddings_model = False
            except Exception as e:
                logger.warning(f"No se pudo cargar embeddings: {e}")
                self._embeddings_model = False
        return self._embeddings_model if self._embeddings_model else None

    def extract_attributes(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]] = None,
        chapter_id: Optional[int] = None,
    ) -> Result[AttributeExtractionResult]:
        """
        Extrae atributos del texto usando votación multi-método.

        Combina resultados de:
        1. LLM (Ollama) - comprensión semántica profunda
        2. Embeddings - similitud con descripciones conocidas
        3. Dependency parsing (spaCy) - análisis sintáctico
        4. Patrones regex - alta precisión para casos conocidos

        Args:
            text: Texto a procesar
            entity_mentions: Lista de menciones conocidas [(nombre, start, end)]
            chapter_id: ID del capítulo (opcional)

        Returns:
            Result con AttributeExtractionResult
        """
        if not text or not text.strip():
            return Result.success(AttributeExtractionResult(processed_chars=0))

        result = AttributeExtractionResult(processed_chars=len(text))
        all_extractions: dict[str, list[ExtractedAttribute]] = {}  # método -> atributos

        try:
            # 1. Extracción por LLM (mayor peso)
            if self.use_llm:
                llm_client = self._get_llm_client()
                if llm_client:
                    llm_attrs = self._extract_by_llm(
                        text, entity_mentions, chapter_id, llm_client
                    )
                    all_extractions["llm"] = llm_attrs
                    logger.debug(f"LLM extrajo {len(llm_attrs)} atributos")

            # 2. Extracción por embeddings
            if self.use_embeddings:
                embeddings_model = self._get_embeddings_model()
                if embeddings_model:
                    emb_attrs = self._extract_by_embeddings(
                        text, entity_mentions, chapter_id, embeddings_model
                    )
                    all_extractions["embeddings"] = emb_attrs
                    logger.debug(f"Embeddings extrajo {len(emb_attrs)} atributos")

            # 3. Extracción por dependencias (spaCy)
            if self.use_dependency_extraction:
                dep_attrs = self._extract_by_dependency(
                    text, entity_mentions, chapter_id
                )
                all_extractions["dependency"] = dep_attrs
                logger.debug(f"Dependency extrajo {len(dep_attrs)} atributos")

            # 4. Extracción por patrones regex (fallback)
            if self.use_patterns:
                pattern_attrs = self._extract_by_patterns(
                    text, entity_mentions, chapter_id
                )
                all_extractions["patterns"] = pattern_attrs
                result.metaphors_filtered = sum(
                    1 for a in pattern_attrs if a.is_metaphor
                )
                logger.debug(f"Patterns extrajo {len(pattern_attrs)} atributos")

            # Votación ponderada para combinar resultados
            result.attributes = self._vote_attributes(all_extractions)

            # Eliminar duplicados finales
            result.attributes = self._deduplicate(result.attributes)

            logger.info(
                f"Atributos finales (votación): {len(result.attributes)}, "
                f"métodos activos: {list(all_extractions.keys())}"
            )

            return Result.success(result)

        except Exception as e:
            error = AttributeExtractionError(
                text_sample=text[:100] if len(text) > 100 else text,
                original_error=str(e),
            )
            logger.error(f"Error extrayendo atributos: {e}")
            return Result.partial(result, [error])

    def _extract_by_llm(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]],
        chapter_id: Optional[int],
        llm_client: Any,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos usando LLM (Ollama).

        El LLM puede entender contexto semántico, detectar atributos implícitos
        y manejar errores ortográficos.
        """
        attributes: list[ExtractedAttribute] = []

        # Construir lista de entidades conocidas (solo personas para atributos físicos)
        known_entities = []
        if entity_mentions:
            normalized = _normalize_entity_mentions(entity_mentions)
            # Filtrar solo personas para extracción de atributos físicos
            known_entities = list(set(
                name for name, _, _, entity_type in normalized
                if entity_type is None or _is_person_entity(entity_type)
            ))

        # Limitar texto para no sobrecargar el LLM
        text_sample = text[:3000] if len(text) > 3000 else text

        prompt = f"""Extrae atributos físicos de personajes. Responde SOLO con JSON válido.

TEXTO:
{text_sample}

PERSONAJES: {', '.join(known_entities) if known_entities else 'Detectar'}

REGLAS:
- Una entrada por CADA mención (si un atributo aparece dos veces, dos entradas)
- Ignora metáforas
- Keys válidas: eye_color, hair_color, hair_type, hair_modification, age, height, build, profession
- hair_modification valores: natural, teñido, decolorado, mechas, reflejos (detectar "rubia de bote" = teñido)
- IMPORTANTE: Si el atributo se refiere a un pronombre (Él, Ella, él, ella), resuelve el pronombre al nombre del personaje más cercano mencionado antes. Ejemplo: "Juan entró. Él era carpintero" -> entity="Juan", key="profession", value="carpintero"

RESPONDE SOLO JSON (sin markdown, sin explicaciones):
{{"attributes":[{{"entity":"María","key":"eye_color","value":"azules","evidence":"ojos azules brillaban"}}]}}"""

        try:
            response = llm_client.complete(
                prompt,
                system="Responde ÚNICAMENTE con JSON válido. Sin explicaciones ni markdown.",
                temperature=0.0,  # Determinístico para consistencia
            )

            if not response:
                return attributes

            # Parsear JSON de la respuesta
            data = self._parse_llm_json(response)
            if not data or "attributes" not in data:
                return attributes

            for attr_data in data["attributes"]:
                try:
                    # Mapear categoría
                    cat_str = attr_data.get("category", "physical").lower()
                    category = {
                        "physical": AttributeCategory.PHYSICAL,
                        "psychological": AttributeCategory.PSYCHOLOGICAL,
                        "social": AttributeCategory.SOCIAL,
                        "ability": AttributeCategory.ABILITY,
                    }.get(cat_str, AttributeCategory.PHYSICAL)

                    # Mapear key
                    key_str = attr_data.get("key", "other").lower()
                    key = self._map_attribute_key(key_str)

                    # Encontrar posición en texto
                    evidence = attr_data.get("evidence", "")
                    start_char = text.find(evidence) if evidence else 0
                    end_char = start_char + len(evidence) if start_char >= 0 else 0

                    attr = ExtractedAttribute(
                        entity_name=attr_data.get("entity", ""),
                        category=category,
                        key=key,
                        value=attr_data.get("value", "").lower(),
                        source_text=evidence,
                        start_char=max(0, start_char),
                        end_char=max(0, end_char),
                        confidence=float(attr_data.get("confidence", 0.8)),
                        is_negated=attr_data.get("is_negated", False),
                        chapter_id=chapter_id,
                    )
                    attributes.append(attr)

                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Error parseando atributo LLM: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error en extracción LLM: {e}")

        return attributes

    def _extract_by_embeddings(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]],
        chapter_id: Optional[int],
        embeddings_model: Any,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos usando similitud de embeddings.

        Compara frases del texto con descripciones canónicas de atributos.
        """
        attributes: list[ExtractedAttribute] = []

        # Descripciones canónicas para detectar por similitud
        canonical_descriptions = {
            # Físicos
            ("physical", "eye_color"): [
                "tiene ojos azules", "tiene ojos verdes", "tiene ojos marrones",
                "ojos de color", "sus ojos son", "la mirada",
            ],
            ("physical", "hair_color"): [
                "pelo rubio", "cabello negro", "pelo castaño", "pelirrojo",
                "es rubia", "es rubio", "tiene el pelo", "su cabello",
            ],
            ("physical", "age"): [
                "tiene años", "de edad", "joven", "viejo", "anciano", "niño",
            ],
            ("physical", "build"): [
                "alto", "baja", "delgado", "corpulento", "musculoso", "esbelto",
            ],
            # Psicológicos
            ("psychological", "personality"): [
                "es amable", "persona curiosa", "carácter", "temperamento",
                "personalidad", "siempre fue", "era conocido por",
            ],
            # Sociales
            ("social", "profession"): [
                "trabaja como", "es médico", "profesión", "estudios como",
                "se dedica a", "lingüista", "profesor", "abogado",
            ],
        }

        try:
            # Dividir texto en oraciones
            sentences = self._split_sentences(text)

            for sentence in sentences:
                if len(sentence) < 10:
                    continue

                # Obtener embedding de la oración
                try:
                    sent_embedding = embeddings_model.encode(sentence)
                except Exception:
                    continue

                # Comparar con cada descripción canónica
                for (category_str, key_str), descriptions in canonical_descriptions.items():
                    for desc in descriptions:
                        try:
                            desc_embedding = embeddings_model.encode(desc)

                            # Calcular similitud coseno
                            similarity = self._cosine_similarity(
                                sent_embedding, desc_embedding
                            )

                            if similarity > 0.5:  # Umbral de similitud
                                # Encontrar entidad en la oración
                                entity = self._find_entity_in_sentence(
                                    sentence, entity_mentions, text
                                )

                                if entity:
                                    # Extraer valor del atributo
                                    value = self._extract_value_from_sentence(
                                        sentence, key_str
                                    )

                                    if value:
                                        category = {
                                            "physical": AttributeCategory.PHYSICAL,
                                            "psychological": AttributeCategory.PSYCHOLOGICAL,
                                            "social": AttributeCategory.SOCIAL,
                                        }.get(category_str, AttributeCategory.PHYSICAL)

                                        key = self._map_attribute_key(key_str)

                                        start_char = text.find(sentence)
                                        attr = ExtractedAttribute(
                                            entity_name=entity,
                                            category=category,
                                            key=key,
                                            value=value.lower(),
                                            source_text=sentence,
                                            start_char=max(0, start_char),
                                            end_char=max(0, start_char + len(sentence)),
                                            confidence=min(0.9, similarity),
                                            chapter_id=chapter_id,
                                        )
                                        attributes.append(attr)
                                        break  # Solo un match por descripción

                        except Exception as e:
                            logger.debug(f"Error comparando embeddings: {e}")

        except Exception as e:
            logger.warning(f"Error en extracción por embeddings: {e}")

        return attributes

    def _is_inside_dialogue(self, text: str, position: int) -> bool:
        """
        Detecta si una posición está dentro de un diálogo (entre comillas o guiones).

        Los atributos mencionados en diálogos no deben asignarse al hablante,
        ya que podrían referirse a otra persona.

        Ejemplos:
        - "Tenías los ojos verdes" -> dentro de diálogo
        - —Eras muy alta —dijo Juan. -> dentro de diálogo
        - - Pero tenías el pelo rubio... -> dentro de diálogo
        """
        # Buscar hacia atrás para encontrar inicio de diálogo
        before = text[:position]

        # Contar comillas y guiones de diálogo
        # Español usa: «», "", '', —, -

        # Comillas españolas «»
        open_spanish = before.count('«')
        close_spanish = before.count('»')
        if open_spanish > close_spanish:
            return True

        # Comillas dobles ""
        open_double = before.count('"')
        # Si número impar de comillas dobles, estamos dentro
        if open_double % 2 == 1:
            return True

        # Comillas inglesas ""
        open_curly = before.count('"')
        close_curly = before.count('"')
        if open_curly > close_curly:
            return True

        # Guiones de diálogo (— largo o - corto al inicio de línea)
        # Buscar el último inicio de línea con guión
        import re
        # Patrón: inicio de línea o después de punto/salto seguido de guión
        dialogue_start_pattern = re.compile(r'(?:^|\n)\s*[-—]')
        matches = list(dialogue_start_pattern.finditer(before))

        if matches:
            last_dialogue_start = matches[-1].end()
            between = before[last_dialogue_start:]

            # Verificar si hay un cierre de diálogo
            # El diálogo termina con: otro guión, salto de línea, o verbo de habla
            speech_verbs = ['dijo', 'preguntó', 'contestó', 'respondió', 'exclamó',
                          'murmuró', 'gritó', 'susurró', 'añadió', 'comentó']
            has_speech_verb = any(verb in between.lower() for verb in speech_verbs)
            has_closing_dash = bool(re.search(r'\s[-—]\s', between))
            has_newline = '\n' in between

            # Si no hay indicador de fin de diálogo, estamos dentro
            if not has_speech_verb and not has_closing_dash and not has_newline:
                return True

            # Caso especial: "- texto - dijo X - más texto"
            # Si hay verbo de habla pero después sigue el diálogo
            if has_speech_verb:
                # Buscar si hay otro guión después del verbo de habla
                verb_match = None
                for verb in speech_verbs:
                    verb_pos = between.lower().find(verb)
                    if verb_pos != -1:
                        verb_match = verb_pos
                        break
                if verb_match is not None:
                    after_verb = between[verb_match:]
                    # Si hay otro guión después del verbo, el texto posterior está en diálogo
                    if re.search(r'\s[-—]\s', after_verb):
                        # La posición está después de ese segundo guión?
                        second_dash = re.search(r'\s[-—]\s', after_verb)
                        if second_dash:
                            return True

        return False

    def _extract_by_patterns(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]],
        chapter_id: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos usando patrones regex (método original).

        Mantiene alta precisión para casos conocidos.
        """
        attributes: list[ExtractedAttribute] = []

        for pattern, key, category, base_conf, swap_groups in self._compiled_patterns:
            for match in pattern.finditer(text):
                # Verificar si está dentro de diálogo
                # Los atributos en diálogos no deben asignarse automáticamente
                if self._is_inside_dialogue(text, match.start()):
                    logger.debug(f"Ignorando atributo en diálogo: {match.group(0)[:40]}...")
                    continue

                # Obtener contexto para análisis
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                match_pos_in_context = match.start() - context_start

                # Verificar si es metáfora (pasando info del match para detección precisa)
                is_metaphor = self._is_metaphor(
                    context,
                    match_text=match.group(0),
                    match_pos_in_context=match_pos_in_context
                )
                if is_metaphor and self.filter_metaphors:
                    continue

                # Verificar negación
                is_negated = self._is_negated(context, match.start() - context_start)

                # Verificar si es atributo temporal (pasado, no actual)
                is_temporal_past = self._is_temporal_past(context, match.start() - context_start)

                # Verificar si es atributo condicional/hipotético
                is_conditional = self._is_conditional(context, match.start() - context_start)

                # Skip atributos claramente negados, temporales o condicionales
                # Estos no representan el estado actual del personaje
                if is_negated or is_conditional:
                    logger.debug(
                        f"Atributo ignorado ({'negado' if is_negated else 'condicional'}): "
                        f"{match.group(0)[:40]}..."
                    )
                    continue

                # Extraer grupos
                groups = match.groups()
                if len(groups) < 2:
                    value = groups[0] if groups else None
                    entity_name = self._find_nearest_entity(
                        text, match.start(), entity_mentions
                    )
                    if not entity_name:
                        continue
                elif swap_groups:
                    value, entity_name = groups[0], groups[1]
                else:
                    entity_name, value = groups[0], groups[1]

                # Verificar patrón contrastivo "No es X, sino Y"
                match_end_in_context = match.end() - context_start
                is_contrastive, corrected_value = self._check_contrastive_correction(
                    context, match_pos_in_context, match_end_in_context, value
                )
                if is_contrastive:
                    if corrected_value:
                        # Usar el valor corregido
                        value = corrected_value
                        logger.debug(f"Valor contrastivo corregido: {match.group(0)[:30]} → {value}")
                    else:
                        # Es contrastivo pero no pudimos extraer el valor correcto, ignorar
                        logger.debug(f"Atributo contrastivo ignorado: {match.group(0)[:40]}")
                        continue

                # Validar valor
                if not self._validate_value(key, value):
                    continue

                # Ajustar confianza
                confidence = base_conf
                if is_metaphor:
                    confidence *= 0.5
                if is_temporal_past:
                    # Reducir confianza para atributos del pasado (pero no descartar)
                    confidence *= 0.6
                    logger.debug(f"Atributo temporal (pasado), reduciendo confianza: {match.group(0)[:30]}")

                if confidence < self.min_confidence:
                    continue

                # Validar que entity_name no sea un color, adjetivo, verbo o palabra inválida
                # Esto evita falsos positivos cuando IGNORECASE hace que el patrón
                # capture palabras comunes en minúscula como si fueran nombres propios
                invalid_entity_names = {
                    # Colores y adjetivos físicos
                    'negro', 'rubio', 'castaño', 'moreno', 'blanco', 'gris', 'canoso',
                    'alto', 'bajo', 'largo', 'corto', 'azules', 'verdes', 'marrones',
                    'delgado', 'fornido', 'sorprendido', 'confundido', 'extraño',
                    # Verbos comunes (infinitivos y gerundios)
                    'llorar', 'reír', 'sonreír', 'caminar', 'correr', 'hablar', 'mirar',
                    'llorando', 'riendo', 'sonriendo', 'caminando', 'corriendo', 'mirando',
                    # Sustantivos comunes
                    'emoción', 'emocion', 'felicidad', 'tristeza', 'dolor', 'alegría', 'alegria',
                    'miedo', 'rabia', 'enojo', 'cansancio', 'sueño', 'hambre',
                    # Preposiciones y conjunciones
                    'tanto', 'mucho', 'poco', 'algo', 'nada', 'todo', 'siempre', 'nunca',
                }
                if entity_name and entity_name.lower() in invalid_entity_names:
                    continue

                # Validación adicional: nombres propios deben comenzar con mayúscula en el texto original
                # Esto ayuda a filtrar palabras comunes capturadas por IGNORECASE
                if entity_name and match.group(0):
                    # Buscar el entity_name en el texto original del match
                    original_text = match.group(0)
                    # Si la entidad aparece en minúscula en el texto original, probablemente no es nombre propio
                    if entity_name.lower() in original_text.lower() and entity_name not in original_text:
                        # La entidad está en minúscula en el original - probable falso positivo
                        continue

                # Filtrar valores que son estados emocionales (no atributos físicos)
                emotional_states = {
                    'sorprendido', 'confundido', 'extrañado', 'asustado', 'feliz',
                    'triste', 'enfadado', 'nervioso', 'preocupado', 'emocionado',
                }
                if value and value.lower() in emotional_states:
                    continue

                attr = ExtractedAttribute(
                    entity_name=entity_name,
                    category=category,
                    key=key,
                    value=value.lower() if value else "",
                    source_text=match.group(0),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=confidence,
                    is_negated=is_negated,
                    is_metaphor=is_metaphor,
                    chapter_id=chapter_id,
                )
                attributes.append(attr)

        return attributes

    def _vote_attributes(
        self,
        extractions: dict[str, list[ExtractedAttribute]],
    ) -> list[ExtractedAttribute]:
        """
        Combina atributos de múltiples métodos usando votación ponderada (weighted voting).

        Fórmula de confianza final:
        - Un método: conf_final = conf_original * (0.8 + method_weight * 0.5)
          - LLM (0.40): factor = 1.0 -> mantiene confianza
          - Patterns (0.15): factor = 0.875 -> reduce ligeramente
        - Múltiples métodos: conf_final = conf_promedio_ponderado + bonus_consenso
          - Promedio ponderado por peso de cada método
          - Bonus por consenso (más métodos = más confianza)

        Esto permite:
        - Aceptar atributos de un solo método si tienen confianza alta
        - Dar prioridad a atributos detectados por múltiples métodos
        - No filtrar arbitrariamente atributos válidos
        """
        # Agrupar atributos por (entidad, key, value_normalizado)
        grouped: dict[tuple, list[tuple[str, ExtractedAttribute]]] = {}

        for method, attrs in extractions.items():
            for attr in attrs:
                # Filtrar atributos sin entidad o valor
                if not attr.entity_name or not attr.value:
                    logger.debug(f"Atributo ignorado (sin entidad/valor): {attr}")
                    continue

                # Filtrar valores que son estados emocionales (no atributos físicos)
                emotional_states = {
                    'sorprendido', 'confundido', 'extrañado', 'asustado', 'feliz',
                    'triste', 'enfadado', 'nervioso', 'preocupado', 'emocionado',
                }
                if attr.value.lower() in emotional_states:
                    logger.debug(f"Atributo ignorado (estado emocional): {attr.value}")
                    continue

                # Filtrar entidades inválidas (pronombres, adverbios, colores, etc.)
                # Incluir versiones con y sin tilde para ser robusto
                invalid_entities = {
                    "también", "tambien", "este", "esta", "esto", "ese", "esa", "eso",
                    "aquel", "aquella", "aquello", "él", "el", "ella", "ellos", "ellas",
                    "uno", "una", "algo", "alguien", "nadie", "nada", "todo",
                    "todos", "todas", "otro", "otra", "otros", "otras", "mismo",
                    "misma", "mismos", "mismas", "ambos", "ambas", "varios", "varias",
                    "quien", "quién", "cual", "cuál", "cuales", "cuáles",
                    # Colores y adjetivos que no son entidades
                    "negro", "rubio", "castaño", "moreno", "blanco", "gris", "canoso",
                    "alto", "bajo", "largo", "corto", "azules", "verdes", "marrones",
                }
                if attr.entity_name.lower() in invalid_entities:
                    logger.debug(f"Atributo ignorado (entidad inválida): {attr.entity_name}")
                    continue

                # Normalizar para comparación
                # Usar solo entity + key para agrupar valores similares
                key = (
                    attr.entity_name.lower(),
                    attr.key,
                    attr.value.lower().strip(),
                )
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append((method, attr))

        # Votar y generar atributos finales
        final_attributes: list[ExtractedAttribute] = []
        num_active_methods = len(extractions)

        # Normalizar pesos basándose en métodos ACTIVOS (que están en extractions)
        # Esto evita que los pesos entrenados para LLM penalicen otros métodos
        # cuando LLM no está habilitado
        active_methods = set(extractions.keys())
        active_weights = {m: METHOD_WEIGHTS.get(m, 0.15) for m in active_methods}
        total_active_weight = sum(active_weights.values())

        if total_active_weight > 0:
            normalized_weights = {m: w / total_active_weight for m, w in active_weights.items()}
        else:
            normalized_weights = {m: 1.0 / len(active_methods) for m in active_methods}

        logger.debug(f"Pesos normalizados para métodos activos {active_methods}: {normalized_weights}")

        for group_key, method_attrs in grouped.items():
            methods_with_attrs = list(method_attrs)
            unique_methods = set(m for m, _ in methods_with_attrs)
            num_votes = len(unique_methods)

            if num_votes == 1:
                # Solo un método detectó este atributo
                method, attr = methods_with_attrs[0]
                # Usar peso normalizado para métodos activos
                method_weight = normalized_weights.get(method, 0.25)

                # Factor de escala: con pesos normalizados, un método único tiene peso ~0.5
                # si hay 2 métodos activos, o ~0.25 si hay 4 métodos activos.
                # Queremos ser más permisivos cuando solo hay pocos métodos activos.
                # Si hay N métodos activos, peso normalizado es ~1/N.
                # Factor de escala: 0.85 + weight * 0.15 para ser más permisivo
                scale_factor = 0.85 + (method_weight * 0.15)
                new_confidence = attr.confidence * scale_factor
                best_attr = attr

            else:
                # Múltiples métodos coinciden - weighted average + consensus bonus
                total_weight = 0.0
                weighted_conf_sum = 0.0
                best_attr = None
                best_conf = 0.0

                for method, attr in methods_with_attrs:
                    # Usar peso normalizado para métodos activos
                    weight = normalized_weights.get(method, 0.25)
                    total_weight += weight
                    weighted_conf_sum += attr.confidence * weight

                    if attr.confidence > best_conf:
                        best_conf = attr.confidence
                        best_attr = attr

                # Promedio ponderado
                avg_weighted_conf = weighted_conf_sum / total_weight if total_weight > 0 else 0.5

                # Bonus por consenso: más métodos = más confianza
                # 2 métodos: +0.05, 3 métodos: +0.10, 4 métodos: +0.15
                consensus_bonus = min(0.15, (num_votes - 1) * 0.05)

                new_confidence = min(1.0, avg_weighted_conf + consensus_bonus)

            new_confidence = min(1.0, max(0.0, new_confidence))

            # Solo incluir si supera umbral mínimo
            if new_confidence >= self.min_confidence and best_attr is not None:
                final_attr = ExtractedAttribute(
                    entity_name=best_attr.entity_name,
                    category=best_attr.category,
                    key=best_attr.key,
                    value=best_attr.value,
                    source_text=best_attr.source_text,
                    start_char=best_attr.start_char,
                    end_char=best_attr.end_char,
                    confidence=new_confidence,
                    is_negated=best_attr.is_negated,
                    is_metaphor=best_attr.is_metaphor,
                    chapter_id=best_attr.chapter_id,
                )
                final_attributes.append(final_attr)

                logger.debug(
                    f"Atributo votado: {best_attr.entity_name}.{best_attr.key.value}="
                    f"{best_attr.value} (métodos: {unique_methods}, votos: {num_votes}/{num_active_methods}, "
                    f"conf: {best_attr.confidence:.2f} -> {new_confidence:.2f})"
                )

        return final_attributes

    def _map_attribute_key(self, key_str: str) -> AttributeKey:
        """Mapea string a AttributeKey."""
        mapping = {
            "eye_color": AttributeKey.EYE_COLOR,
            "hair_color": AttributeKey.HAIR_COLOR,
            "hair_type": AttributeKey.HAIR_TYPE,
            "hair_modification": AttributeKey.HAIR_MODIFICATION,
            "age": AttributeKey.AGE,
            "height": AttributeKey.HEIGHT,
            "build": AttributeKey.BUILD,
            "skin": AttributeKey.SKIN,
            "distinctive_feature": AttributeKey.DISTINCTIVE_FEATURE,
            "personality": AttributeKey.PERSONALITY,
            "temperament": AttributeKey.TEMPERAMENT,
            "fear": AttributeKey.FEAR,
            "desire": AttributeKey.DESIRE,
            "profession": AttributeKey.PROFESSION,
            "title": AttributeKey.TITLE,
            "relationship": AttributeKey.RELATIONSHIP,
            "nationality": AttributeKey.NATIONALITY,
            "color": AttributeKey.COLOR,
            "material": AttributeKey.MATERIAL,
            "condition": AttributeKey.CONDITION,
        }
        return mapping.get(key_str.lower(), AttributeKey.OTHER)

    def _parse_llm_json(self, response: str) -> Optional[dict]:
        """Parsea respuesta JSON del LLM con limpieza y fallback."""
        try:
            # Limpiar respuesta
            cleaned = response.strip()

            # Remover bloques de código markdown
            if "```" in cleaned:
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)

            # Encontrar JSON
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx]
                return json.loads(json_str)

            # Fallback: parsear texto formateado con markdown
            # El LLM a veces responde con formato tipo "**key**: value"
            return self._parse_markdown_response(response)

        except json.JSONDecodeError as e:
            logger.debug(f"Error parseando JSON del LLM: {e}")
            # Intentar parsear como markdown
            return self._parse_markdown_response(response)

    def _parse_markdown_response(self, response: str) -> Optional[dict]:
        """
        Parsea respuesta formateada del LLM cuando no devuelve JSON.

        Maneja formatos como:
        **María Sánchez**
        * **Eye color**: azules ("Sus ojos azules brillaban")
        """
        attributes = []
        current_entity = None

        # Patrones para extraer información
        entity_pattern = re.compile(r'\*\*([^*]+)\*\*')
        attr_pattern = re.compile(
            r'\*\s*\*\*([^*]+)\*\*:\s*([^(]+)(?:\("([^"]+)"\))?'
        )

        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Detectar nombre de entidad
            entity_match = entity_pattern.match(line)
            if entity_match and not ':' in line:
                current_entity = entity_match.group(1).strip()
                # Limpiar "(en la cafetería)" y similares
                if '(' in current_entity:
                    current_entity = current_entity.split('(')[0].strip()
                continue

            # Detectar atributo
            attr_match = attr_pattern.match(line)
            if attr_match and current_entity:
                key_raw = attr_match.group(1).strip().lower()
                value = attr_match.group(2).strip()
                evidence = attr_match.group(3) if attr_match.lastindex >= 3 else ""

                # Mapear key
                key_mapping = {
                    'eye color': 'eye_color',
                    'hair color': 'hair_color',
                    'hair type': 'hair_type',
                    'hair modification': 'hair_modification',
                    'height': 'height',
                    'build': 'build',
                    'age': 'age',
                    'profession': 'profession',
                }
                key = key_mapping.get(key_raw, key_raw.replace(' ', '_'))

                if key in ['eye_color', 'hair_color', 'hair_type', 'hair_modification', 'height', 'build', 'age', 'profession']:
                    attributes.append({
                        'entity': current_entity,
                        'key': key,
                        'value': value,
                        'evidence': evidence or '',
                    })

        if attributes:
            logger.debug(f"Parseados {len(attributes)} atributos desde markdown")
            return {'attributes': attributes}
        return None

    def _split_sentences(self, text: str) -> list[str]:
        """Divide texto en oraciones."""
        # Simple split por puntuación
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calcula similitud coseno entre dos vectores."""
        import numpy as np
        # Aplanar a 1D si vienen como 2D (batch de 1)
        v1 = np.array(vec1).flatten()
        v2 = np.array(vec2).flatten()
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def _find_entity_in_sentence(
        self,
        sentence: str,
        entity_mentions: Optional[list[tuple]],
        full_text: str,
    ) -> Optional[str]:
        """
        Encuentra entidad SUJETO en una oración, incluyendo resolución de pronombres.

        IMPORTANTE: Distingue entre sujeto y objeto/complemento.
        - "Sus ojos azules miraban a María" → sujeto implícito (no María)
        - "María tenía ojos azules" → sujeto = María
        - "Los ojos de María brillaban" → María (genitivo posesivo)
        - "María, que tenía ojos verdes, saludó" → María (cláusula relativa)
        - "Juan fue admirado por María" → Juan (voz pasiva, sujeto paciente)

        Args:
            sentence: Oración a analizar
            entity_mentions: Lista de (name, start, end, entity_type) o (name, start, end)
            full_text: Texto completo para contexto

        Returns:
            Nombre de la entidad sujeto o None
        """
        if not entity_mentions:
            return None

        import re as regex_module

        # Normalizar menciones al formato de 4 elementos
        normalized_mentions = _normalize_entity_mentions(entity_mentions)

        # Filtrar solo personas (excluir LOC, ORG) para atributos físicos
        person_mentions = [
            (name, start, end, entity_type)
            for name, start, end, entity_type in normalized_mentions
            if entity_type is None or _is_person_entity(entity_type)
        ]

        if not person_mentions:
            return None

        sentence_lower = sentence.lower()
        sentence_start = full_text.find(sentence)

        # =================================================================
        # CASO 1: Genitivo posesivo - "los ojos DE María brillaban"
        # El poseedor es quien tiene el atributo físico
        # =================================================================
        body_parts = (
            'ojos', 'ojo', 'pelo', 'cabello', 'cara', 'rostro', 'manos', 'mano',
            'piel', 'nariz', 'boca', 'labios', 'cejas', 'ceja', 'frente',
            'mejillas', 'mejilla', 'barbilla', 'mentón', 'cuello', 'espalda',
            'hombros', 'brazos', 'piernas', 'pies', 'dedos', 'uñas', 'dientes',
            'sonrisa', 'mirada', 'expresión', 'gesto', 'voz', 'tono', 'altura',
            'estatura', 'complexión', 'figura', 'silueta', 'cuerpo', 'aspecto'
        )

        for name, start, end, entity_type in person_mentions:
            name_lower = name.lower()
            # Patrón: [artículo] [parte_cuerpo] de [Nombre]
            for part in body_parts:
                pattern = rf'\b(?:el|la|los|las|su|sus)?\s*{part}\s+de\s+{regex_module.escape(name_lower)}\b'
                if regex_module.search(pattern, sentence_lower):
                    logger.debug(f"Genitivo posesivo detectado: '{part} de {name}'")
                    return name

        # =================================================================
        # CASO 2: Cláusula relativa - "María, QUE TENÍA ojos verdes, saludó"
        # El antecedente de la cláusula es el poseedor
        # =================================================================
        relative_verbs = r'(?:tenía|tiene|era|es|parecía|parece|llevaba|lleva|lucía|luce|mostraba|muestra)'

        for name, start, end, entity_type in person_mentions:
            name_lower = name.lower()
            # Patrón: [Nombre], que [verbo_descriptivo] [atributo]
            pattern = rf'{regex_module.escape(name_lower)}\s*,\s*(?:que|quien|la cual|el cual)\s+{relative_verbs}\s+'
            if regex_module.search(pattern, sentence_lower):
                logger.debug(f"Cláusula relativa detectada para '{name}'")
                return name

        # =================================================================
        # CASO 3: Voz pasiva - "Juan FUE admirado POR María por sus ojos"
        # En voz pasiva, el sujeto gramatical (paciente) es el poseedor
        # "por [Nombre]" es el agente, NO el poseedor
        # =================================================================
        passive_pattern = r'(?:fue|era|había sido|ha sido|será|siendo)\s+\w+[oa]?(?:do|da|dos|das)?\s+por\s+'
        if regex_module.search(passive_pattern, sentence_lower):
            # En voz pasiva, buscar el sujeto al inicio de la oración
            for name, start, end, entity_type in person_mentions:
                name_lower = name.lower()
                # Si el nombre está al inicio (antes del verbo pasivo), es el sujeto paciente
                name_pos = sentence_lower.find(name_lower)
                passive_match = regex_module.search(passive_pattern, sentence_lower)
                if passive_match and name_pos >= 0 and name_pos < passive_match.start():
                    logger.debug(f"Voz pasiva detectada: sujeto paciente = '{name}'")
                    return name

        # =================================================================
        # CASO GENERAL: Buscar sujeto vs objeto
        # =================================================================

        # Patrones que indican que la entidad es OBJETO (no sujeto):
        object_patterns = [
            r'\ba\s+{}\b',      # "a María", "a Juan"
            r'\bcon\s+{}\b',    # "con María"
            r'\bpara\s+{}\b',   # "para Juan"
            r'\bhacia\s+{}\b',  # "hacia María"
            r'\bsobre\s+{}\b',  # "sobre Juan"
        ]

        subject_candidates = []
        object_entities = set()

        for name, start, end, entity_type in person_mentions:
            name_lower = name.lower()
            if name_lower not in sentence_lower:
                continue

            # Verificar si aparece como objeto
            is_object = False
            for pattern_template in object_patterns:
                pattern = pattern_template.format(regex_module.escape(name_lower))
                if regex_module.search(pattern, sentence_lower):
                    is_object = True
                    object_entities.add(name)
                    break

            if not is_object:
                # Calcular posición en la oración (priorizar inicio = más probable sujeto)
                pos_in_sentence = sentence_lower.find(name_lower)
                subject_candidates.append((name, pos_in_sentence))

        if subject_candidates:
            # Priorizar el que aparece primero (más probable sujeto)
            subject_candidates.sort(key=lambda x: x[1])
            return subject_candidates[0][0]

        # =================================================================
        # FALLBACK: Resolución de pronombres
        # =================================================================
        pronouns_pattern = r'\b(él|ella|sus?|este|esta|aquel|aquella)\b'
        has_pronoun = regex_module.search(pronouns_pattern, sentence_lower)

        if has_pronoun and sentence_start > 0:
            # Buscar la entidad mencionada más recientemente antes de esta oración
            # PERO excluir entidades que aparecen como objeto en esta oración
            mentions_before = [
                (name, start, end)
                for name, start, end, entity_type in person_mentions
                if end <= sentence_start and name not in object_entities
            ]

            if mentions_before:
                # Tomar la más cercana (última mencionada antes de la oración)
                mentions_before.sort(key=lambda x: x[1], reverse=True)

                # Aplicar concordancia de género si es posible
                pronoun_match = regex_module.search(pronouns_pattern, sentence_lower)
                if pronoun_match:
                    pronoun = pronoun_match.group(1).lower()
                    is_feminine = pronoun in ('ella', 'esta', 'aquella')
                    is_masculine = pronoun in ('él', 'este', 'aquel')

                    if is_feminine or is_masculine:
                        # Filtrar por género
                        gendered = []
                        for name, start, end in mentions_before:
                            name_lower = name.lower().split()[0]
                            # Heurística simple: nombres terminados en 'a' suelen ser femeninos
                            name_is_feminine = name_lower.endswith('a') and name_lower not in ('jesús', 'elías', 'josué')

                            if is_feminine and name_is_feminine:
                                gendered.append((name, start, end))
                            elif is_masculine and not name_is_feminine:
                                gendered.append((name, start, end))

                        if gendered:
                            return gendered[0][0]

                # Fallback: retornar el más cercano
                return mentions_before[0][0]

        return None

    def _extract_value_from_sentence(
        self,
        sentence: str,
        key_str: str,
    ) -> Optional[str]:
        """Extrae valor de atributo de una oración."""
        sentence_lower = sentence.lower()

        # Indicadores de partes del cuerpo para validación
        eye_indicators = {"ojo", "ojos", "mirada", "pupila", "iris"}
        hair_indicators = {"pelo", "cabello", "cabellera", "melena", "trenza", "rizos", "mechón"}

        has_eye = any(ind in sentence_lower for ind in eye_indicators)
        has_hair = any(ind in sentence_lower for ind in hair_indicators)

        if key_str == "hair_color":
            # IMPORTANTE: Solo extraer hair_color si hay indicador de pelo
            # y NO hay indicador de ojos (para evitar "ojos azules" -> hair_color)
            if has_eye and not has_hair:
                return None  # Rechazar: es sobre ojos, no pelo
            for color in COLORS:
                if color in sentence_lower:
                    # Si hay indicador de pelo, aceptar
                    # Si no hay ningún indicador, también aceptar (contexto implícito)
                    if has_hair or not has_eye:
                        return color

        elif key_str == "eye_color":
            # eye_color requiere indicador de ojos
            if not has_eye:
                return None
            for color in COLORS:
                if color in sentence_lower:
                    return color

        elif key_str == "build":
            for build in BUILD_TYPES:
                if build in sentence_lower:
                    return build

        elif key_str == "personality":
            for trait in PERSONALITY_TRAITS:
                if trait in sentence_lower:
                    return trait

        elif key_str == "profession":
            # Enfoque dinámico: buscar patrones "era/es [sustantivo]"
            # En lugar de una lista fija, extraemos el sustantivo del patrón
            import re as regex_module

            # Patrones para detectar profesiones/ocupaciones
            profession_patterns = [
                # "era carpintero", "es médico", "fue ingeniero"
                r'\b(?:era|es|fue|será)\s+(?:un|una)?\s*(\w+(?:ero|era|ista|or|ora|ico|ica|nte|dor|dora|tor|tora|ogo|oga|ino|ina|ario|aria|ador|adora))\b',
                # "trabaja como X", "trabajaba de X"
                r'\btrabaj(?:a|aba|ó)\s+(?:como|de)\s+(\w+)\b',
                # "se dedica a ser X", "se dedicaba a X"
                r'\bse\s+dedica(?:ba)?\s+a\s+(?:ser\s+)?(\w+)\b',
                # "de profesión X"
                r'\bde\s+profesión\s+(\w+)\b',
            ]

            for pattern in profession_patterns:
                match = regex_module.search(pattern, sentence_lower, regex_module.IGNORECASE)
                if match:
                    profession = match.group(1).lower()
                    # Excluir palabras muy genéricas que no son profesiones
                    excluded = {
                        "hombre", "mujer", "persona", "tipo", "chico", "chica",
                        "joven", "viejo", "niño", "niña", "señor", "señora",
                        "alto", "bajo", "grande", "pequeño", "bueno", "malo",
                    }
                    if profession not in excluded and len(profession) > 3:
                        return profession

            # Fallback: lista mínima de profesiones comunes (solo las más frecuentes)
            common_professions = [
                "médico", "médica", "abogado", "abogada", "profesor", "profesora",
                "ingeniero", "ingeniera", "arquitecto", "arquitecta", "policía",
                "bombero", "militar", "enfermero", "enfermera", "periodista",
            ]
            for prof in common_professions:
                if prof in sentence_lower:
                    return prof

        return None

    def _is_metaphor(self, context: str, match_text: str = "", match_pos_in_context: int = 0) -> bool:
        """
        Detecta si el contexto sugiere una metáfora.

        Args:
            context: Texto de contexto alrededor del match
            match_text: Texto que hizo match (para verificar si la metáfora lo afecta)
            match_pos_in_context: Posición del match dentro del contexto

        Returns:
            True si es probable que sea una metáfora
        """
        for pattern in self._metaphor_patterns:
            # Buscar TODAS las ocurrencias del patrón de metáfora en el contexto
            for metaphor_match in pattern.finditer(context):
                metaphor_pos = metaphor_match.start()
                metaphor_end = metaphor_match.end()

                # Si no tenemos info del match, cualquier metáfora cuenta
                if not match_text or match_pos_in_context < 0:
                    return True

                match_end_in_context = match_pos_in_context + len(match_text)

                # Caso 1: Metáfora está ANTES del match
                if metaphor_end <= match_pos_in_context:
                    between = context[metaphor_end:match_pos_in_context]
                    # Si hay puntuación entre la metáfora y el match, no afecta
                    if ',' in between or '.' in between or ';' in between or '\n' in between:
                        continue
                    # Si hay más de 20 caracteres, probablemente no afecta
                    if len(between.strip()) > 20:
                        continue
                    return True

                # Caso 2: Metáfora está DENTRO del match
                elif metaphor_pos >= match_pos_in_context and metaphor_end <= match_end_in_context:
                    return True

                # Caso 3: Metáfora está DESPUÉS del match
                elif metaphor_pos >= match_end_in_context:
                    between = context[match_end_in_context:metaphor_pos]
                    # Si hay puntuación entre el match y la metáfora, no afecta
                    if ',' in between or '.' in between or ';' in between or '\n' in between:
                        continue
                    # Si hay más de 20 caracteres, probablemente no afecta
                    if len(between.strip()) > 20:
                        continue
                    return True

        return False

    def _is_negated(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo está negado.

        Maneja:
        - Negación simple: "no era alto", "nunca tuvo pelo negro"
        - Negación parcial: "no es que X, sino Y" (X está negado)

        Args:
            context: Contexto alrededor del match
            match_pos: Posición del match en el contexto

        Returns:
            True si el atributo está negado
        """
        # Solo buscar en el contexto antes del match
        before_context = context[:match_pos]

        # Buscar negación simple cercana (últimos 30 caracteres)
        for pattern in self._negation_patterns:
            if pattern.search(before_context[-30:]):
                return True

        return False

    def _is_temporal_past(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo se refiere al pasado (no al estado actual).

        Ejemplo: "De joven, Eva tenía pelo negro" → atributo pasado
        """
        before_context = context[:match_pos]

        for pattern in self._temporal_past_patterns:
            if pattern.search(before_context[-60:]):
                return True

        return False

    def _is_conditional(self, context: str, match_pos: int) -> bool:
        """
        Detecta si el atributo es hipotético/condicional (no real).

        Ejemplo: "Si Oscar se tiñera, sería pelirrojo" → no es pelirrojo realmente
        """
        before_context = context[:match_pos]

        for pattern in self._conditional_patterns:
            if pattern.search(before_context[-50:]):
                return True

        return False

    def _check_contrastive_correction(
        self, context: str, match_start: int, match_end: int, value: str
    ) -> tuple[bool, Optional[str]]:
        """
        Detecta patrón contrastivo "No es X, sino Y" y extrae el valor correcto.

        Ejemplo: "No es que Pedro tuviera ojos azules, sino grises"
        → El valor "azules" está negado, "grises" es el correcto.

        Args:
            context: Contexto alrededor del match
            match_start: Inicio del match en el contexto
            match_end: Fin del match en el contexto
            value: Valor extraído actual

        Returns:
            (is_contrastive, corrected_value) - Si es contrastivo y el valor corregido
        """
        # Buscar patrón "no es que... sino" o "no era/tenía... sino"
        for pattern in self._contrastive_patterns:
            match = pattern.search(context)
            if match:
                # Verificar si nuestro valor está ANTES del "sino"
                sino_pos = context.lower().find("sino", match.start())
                if sino_pos > 0 and match_start < sino_pos:
                    # El valor actual está en la parte negada
                    # Buscar el valor después del "sino"
                    after_sino = context[sino_pos + 4:].strip()
                    # Extraer la primera palabra después de "sino" como posible corrección
                    import re
                    color_match = re.search(r'\b([a-záéíóú]+)\b', after_sino)
                    if color_match:
                        corrected = color_match.group(1).lower()
                        # Verificar que sea un color válido
                        if corrected in COLORS:
                            return True, corrected
                    return True, None  # Es contrastivo pero no pudimos extraer corrección

        return False, None

    def _is_inside_relative_clause(
        self, text: str, entity_start: int, entity_end: int, attribute_pos: int
    ) -> bool:
        """
        Detecta si una entidad está dentro de una cláusula relativa.

        En español, las cláusulas relativas comienzan con:
        - "que" (pronombre relativo): "el hombre que vi"
        - "quien/quienes": "la mujer a quien conocí"
        - "cual/cuales": "el cual era..."
        - "cuyo/cuya/cuyos/cuyas": "cuyo hermano..."
        - "donde": "la casa donde vivía"

        Ejemplo: "El hombre que María había visto tenía ojos azules."
        → "María" está dentro de "que María había visto" (cláusula relativa)
        → El atributo "ojos azules" pertenece a "El hombre", NO a María

        Args:
            text: Texto completo
            entity_start: Posición inicial de la entidad
            entity_end: Posición final de la entidad
            attribute_pos: Posición del atributo

        Returns:
            True si la entidad está dentro de una cláusula relativa
        """
        import re as regex_module

        # La entidad está ANTES del atributo (ya filtrado en el caller)
        if entity_end > attribute_pos:
            return False

        # Buscar si hay un pronombre relativo ANTES de la entidad
        # que indica que la entidad está dentro de una cláusula relativa
        # Patrón: Antecedente + "que/quien/etc" + [Entidad] + verbo + ... + atributo

        # Buscar el contexto antes de la entidad (buscando el pronombre relativo)
        search_start = max(0, entity_start - 30)
        before_entity = text[search_start:entity_start]

        # Patrones de inicio de cláusula relativa en español
        relative_patterns = [
            r'\bque\s*$',           # "...que María"
            r'\bquien(?:es)?\s*$',  # "...quien María"
            r'\bel\s+cual\s*$',     # "el cual María"
            r'\bla\s+cual\s*$',
            r'\bcuy[oa]s?\s*$',     # "cuyo hermano"
            r'\bdonde\s*$',         # "donde María"
            r'\bcuando\s*$',        # "cuando María"
        ]

        for pattern in relative_patterns:
            if regex_module.search(pattern, before_entity, regex_module.IGNORECASE):
                # Hay un pronombre relativo justo antes de la entidad
                # Verificar que el atributo NO está dentro de la misma cláusula
                # (buscar verbos entre la entidad y el atributo que podrían cerrar la cláusula)

                between = text[entity_end:attribute_pos]

                # Si encontramos un verbo seguido de otro verbo principal, la cláusula terminó
                # Patrones de cierre de cláusula: verbo en pasado + verbo en imperfecto
                # Ej: "había visto" (cláusula) + "tenía" (principal)
                clause_closure = regex_module.search(
                    r'\b(?:había|hubo|hizo|fue|vio|conoció|dijo)\s+\w+\s+(?:tenía|era|estaba|llevaba|mostraba)\b',
                    between, regex_module.IGNORECASE
                )

                if clause_closure:
                    logger.debug(
                        f"Entidad en cláusula relativa: '{text[entity_start:entity_end]}' "
                        f"(patrón relativo antes, cierre de cláusula detectado)"
                    )
                    return True

        return False

    def _validate_value(self, key: AttributeKey, value: str) -> bool:
        """Valida que el valor sea apropiado para el tipo de atributo."""
        if not value:
            return False

        value_lower = value.lower()

        if key == AttributeKey.EYE_COLOR:
            return value_lower in COLORS

        if key == AttributeKey.HAIR_COLOR:
            # Solo colores válidos, NO tipos de cabello (largo/corto son hair_type)
            return value_lower in COLORS

        if key == AttributeKey.HAIR_MODIFICATION:
            # Modificaciones: teñido, natural, decolorado, mechas, etc.
            return value_lower in HAIR_MODIFICATIONS or "teñid" in value_lower or "de bote" in value_lower

        if key == AttributeKey.BUILD:
            return value_lower in BUILD_TYPES

        if key == AttributeKey.PERSONALITY:
            return value_lower in PERSONALITY_TRAITS

        if key == AttributeKey.AGE:
            try:
                age = int(value)
                return 0 < age < 200  # Rango razonable
            except ValueError:
                return False

        if key == AttributeKey.PROFESSION:
            # Excluir palabras genéricas que no son profesiones
            excluded = {
                "hombre", "mujer", "persona", "tipo", "chico", "chica",
                "joven", "viejo", "niño", "niña", "señor", "señora",
                "alto", "bajo", "grande", "pequeño", "bueno", "malo",
                "mejor", "peor", "primero", "primera", "último", "última",
            }
            return value_lower not in excluded and len(value) > 3

        # Para otros tipos, aceptar cualquier valor no vacío
        return len(value) > 1

    def _find_nearest_entity(
        self,
        text: str,
        position: int,
        entity_mentions: Optional[list[tuple]],
    ) -> Optional[str]:
        """
        Encuentra la entidad más cercana a una posición.

        Útil para resolver "sus ojos" o pronombres como "ella".
        Resuelve correferencias usando contexto y prioriza entidades tipo PERSON.
        Maneja sujetos elípticos en español.

        Args:
            text: Texto completo
            position: Posición del atributo a resolver
            entity_mentions: Lista de (name, start, end, entity_type) o (name, start, end)

        Returns:
            Nombre de la entidad más probable o None
        """
        if not entity_mentions:
            return None

        import re as regex_module

        # Normalizar menciones al formato de 4 elementos
        normalized_mentions = _normalize_entity_mentions(entity_mentions)

        # Extraer contexto alrededor de la posición (400 chars antes para capturar oraciones previas)
        context_start = max(0, position - 400)
        context = text[context_start:position]

        # También extraer un poco adelante (20 chars) para detectar patrones que inician en position
        context_forward = text[position:position + 20]

        # Buscar todas las entidades antes de la posición con sus distancias
        candidates = []
        for name, start, end, entity_type in normalized_mentions:
            if end <= position:
                distance = position - end
                if distance < 400:  # Ventana amplia
                    candidates.append((name, start, end, distance, entity_type))

        if not candidates:
            return None

        # Clasificar entidades por tipo usando entity_type real del NER
        # También detectar si están dentro de cláusulas relativas
        person_candidates = []
        location_candidates = []

        for name, start, end, distance, entity_type in candidates:
            # NUEVO: Detectar si la entidad está dentro de una cláusula relativa
            # Esto es importante para casos como:
            # "La mujer de ojos verdes que Juan conoció era María"
            # → "Juan" está en la cláusula relativa, no es el dueño de "ojos verdes"
            in_relative_clause = self._is_inside_relative_clause(text, start, end, position)

            # Aplicar penalización por cláusula relativa
            relative_clause_penalty = 300 if in_relative_clause else 0
            adjusted_distance = distance + relative_clause_penalty

            # Si tenemos entity_type del NER, usarlo directamente
            if entity_type is not None:
                if _is_person_entity(entity_type):
                    person_candidates.append((name, start, end, adjusted_distance))
                elif _is_location_entity(entity_type):
                    location_candidates.append((name, start, end, adjusted_distance))
                # ORG y otros tipos se ignoran para atributos físicos
            else:
                # Fallback: heurística por nombre si no hay entity_type
                name_words = name.split()
                is_likely_person = (
                    len(name_words) <= 2 and
                    not any(word.lower() in ['parque', 'del', 'de', 'la', 'el', 'retiro', 'madrid'] for word in name_words) and
                    name[0].isupper()
                )

                if is_likely_person:
                    person_candidates.append((name, start, end, adjusted_distance))
                else:
                    location_candidates.append((name, start, end, adjusted_distance))

        # Buscar límites de oración (. ! ?) para entender contexto
        last_sentence_break = max(
            context.rfind('.'),
            context.rfind('!'),
            context.rfind('?')
        )

        # Buscar pronombres o verbos en 3ª persona que indican sujeto elíptico
        immediate_context = context[-50:] if len(context) > 50 else context

        # IMPORTANTE: Separar pronombres de sujeto de artículos/determinantes
        # - Pronombres de sujeto: él, ella (indican sujeto explícito)
        # - Posesivos: su, sus (pueden indicar el referente)
        # - "la", "lo", "le" son MUY comunes como artículos, NO usar para has_pronoun
        #   Ej: "llamaron la atención" - "la" es artículo, no pronombre
        has_subject_pronoun = bool(regex_module.search(r'\b(ella|él)\b', immediate_context, regex_module.IGNORECASE))
        has_pronoun = has_subject_pronoun  # Solo pronombres de sujeto reales

        # IMPORTANTE: Buscar verbos en 3ª persona tanto en contexto anterior como en el inicio del match
        # El patrón puede empezar con el verbo (ej: "Llevaba el cabello corto")
        combined_context = immediate_context + " " + context_forward
        has_3rd_person_verb = bool(regex_module.search(r'\b(tenía|era|estaba|llevaba|parecía|mostraba)\b', combined_context, regex_module.IGNORECASE))

        # Detectar pronombres posesivos que podrían referirse al objeto (no al sujeto)
        # Ej: "Juan la saludó, sorprendido por su cabello" -> "su" se refiere a "la" (María), no a Juan
        # Buscar tanto en contexto anterior como en el inicio del match (context_forward)
        has_possessive = bool(regex_module.search(r'\b(su|sus)\b', immediate_context + " " + context_forward, regex_module.IGNORECASE))

        # IMPORTANTE: Detectar "la/lo/le" como pronombre OBJETO, no como artículo
        # "la" como artículo: "la cafetería", "la mesa", "la atención"
        # "la" como pronombre objeto: "la saludó", "la vio", "la llevó"
        # El pronombre objeto va ANTES de un verbo, el artículo va ANTES de un sustantivo
        # Patrón: "la/lo/le" seguido de verbo en 3ª persona indica pronombre objeto
        has_object_pronoun = bool(regex_module.search(
            r'\b(la|lo|le)\s+(?:saludó|vio|miró|abrazó|besó|llamó|llevó|trajo|cogió|tomó|dejó|encontró|conoció|reconoció|observó|siguió|esperó|ayudó)',
            immediate_context, regex_module.IGNORECASE
        ))

        # Detectar pronombres de sujeto explícitos (Él/Ella) o indicadores de género (hombre/mujer)
        # Esto tiene MÁXIMA prioridad porque indica claramente el género del referente
        subject_pronoun_match = regex_module.search(
            r'\b(él|ella)\b', immediate_context + " " + context_forward, regex_module.IGNORECASE
        )
        gender_noun_match = regex_module.search(
            r'\b(hombre|mujer|chico|chica|señor|señora|niño|niña)\b',
            immediate_context + " " + context_forward, regex_module.IGNORECASE
        )

        # Estrategia de selección mejorada:
        # -1. Si hay pronombre de sujeto (Él/Ella) o indicador (hombre/mujer) → buscar por género
        # 0. Si hay "su/sus" después de un pronombre objeto "la/lo/le" → buscar referente del objeto
        # 1. Si hay verbo en 3ª persona SIN sujeto explícito cerca → sujeto elíptico, buscar persona en oración anterior
        # 2. Si hay pronombre → buscar persona más cercana
        # 3. Si no hay indicadores → usar persona más cercana pero penalizar lugares

        # Caso -1: Pronombre de sujeto explícito o indicador de género
        # "Él era un hombre bajo" → buscar entidad masculina (Juan, no María)
        # "Ella era alta" → buscar entidad femenina
        if (subject_pronoun_match or gender_noun_match) and person_candidates:
            # Determinar género
            is_feminine = False
            if subject_pronoun_match:
                pronoun = subject_pronoun_match.group(1).lower()
                is_feminine = (pronoun == "ella")
            elif gender_noun_match:
                noun = gender_noun_match.group(1).lower()
                is_feminine = noun in ("mujer", "chica", "señora", "niña")

            # Buscar candidatos con género coincidente
            gendered_candidates = []
            for name, start, end, distance in person_candidates:
                name_lower = name.lower()
                first_name = name_lower.split()[0] if name_lower else ""

                # Nombres femeninos comunes en español
                feminine_names = {
                    'maría', 'ana', 'elena', 'laura', 'carmen', 'isabel', 'rosa',
                    'lucía', 'marta', 'paula', 'sara', 'andrea', 'claudia', 'sofía',
                    'julia', 'clara', 'alba', 'irene', 'nuria', 'eva', 'raquel',
                    'silvia', 'cristina', 'patricia', 'mónica', 'beatriz', 'alicia'
                }
                # Nombres masculinos comunes en español
                masculine_names = {
                    'juan', 'pedro', 'carlos', 'antonio', 'josé', 'luis', 'miguel',
                    'francisco', 'javier', 'david', 'daniel', 'pablo', 'alejandro',
                    'sergio', 'fernando', 'alberto', 'manuel', 'rafael', 'jorge',
                    'mario', 'andrés', 'roberto', 'enrique', 'ricardo', 'diego'
                }

                # Determinar si el nombre coincide con el género buscado
                name_is_feminine = (
                    first_name in feminine_names or
                    (first_name.endswith('a') and first_name not in masculine_names)
                )
                name_is_masculine = (
                    first_name in masculine_names or
                    (first_name.endswith('o') and first_name not in feminine_names)
                )

                # Calcular ajuste de distancia por género
                gender_adjustment = 0
                if is_feminine and name_is_feminine:
                    gender_adjustment = -100  # Gran boost para coincidencia de género
                elif not is_feminine and name_is_masculine:
                    gender_adjustment = -100  # Gran boost para coincidencia de género
                elif is_feminine and name_is_masculine:
                    gender_adjustment = 200  # Penalización fuerte por género incorrecto
                elif not is_feminine and name_is_feminine:
                    gender_adjustment = 200  # Penalización fuerte por género incorrecto

                adjusted_distance = distance + gender_adjustment
                gendered_candidates.append((name, adjusted_distance, distance))

            if gendered_candidates:
                # Ordenar por distancia ajustada
                gendered_candidates.sort(key=lambda x: x[1])
                best_candidate = gendered_candidates[0]
                # Aceptar si la distancia ajustada es razonable
                if best_candidate[1] < 400:
                    logger.debug(
                        f"Género detectado ({'femenino' if is_feminine else 'masculino'}): "
                        f"seleccionando '{best_candidate[0]}' (dist={best_candidate[2]}, "
                        f"ajustada={best_candidate[1]})"
                    )
                    return best_candidate[0]

        # Caso 0: Pronombre posesivo refiriéndose al objeto
        # Patrón: "Juan la saludó... su cabello" -> "su" se refiere a "la" (María), no a Juan
        # IMPORTANTE: Solo aplica cuando "la/lo" es PRONOMBRE OBJETO (antes de verbo), NO artículo
        if has_possessive and has_object_pronoun and person_candidates:
            # Buscar "la/lo" + verbo seguido eventualmente de "su/sus"
            # El patrón debe ser más específico para evitar falsos positivos con artículos
            search_text = immediate_context + " " + context_forward
            # Patrón mejorado: pronombre objeto + verbo ... posesivo
            obj_pronoun_match = regex_module.search(
                r'\b(la|lo)\s+(?:saludó|vio|miró|abrazó|besó|llamó|llevó).*?\b(su|sus)\b',
                search_text, regex_module.IGNORECASE | regex_module.DOTALL
            )

            if obj_pronoun_match:
                obj_pronoun = obj_pronoun_match.group(1).lower()

                # Determinar género del pronombre objeto
                # "la" = femenino, "lo" = masculino
                is_feminine = (obj_pronoun == "la")

                # Buscar en candidates la entidad que mejor coincida con el género
                # Heurística simple: nombres que terminan en 'a' son probablemente femeninos
                # nombres que terminan en 'o' son probablemente masculinos
                gendered_candidates = []

                for name, start, end, distance in person_candidates:
                    name_lower = name.lower()
                    # Calcular score de género (preferencia)
                    gender_score = 0

                    if is_feminine:
                        if name_lower.endswith('a') or name_lower in ['maría', 'ana', 'elena', 'laura', 'carmen', 'isabel']:
                            gender_score = -50  # Boost femenino (distancia menor = mejor)
                    else:
                        if name_lower.endswith('o') or name_lower in ['juan', 'pedro', 'carlos', 'antonio', 'josé', 'luis']:
                            gender_score = -50  # Boost masculino

                    # Si no coincide el género, penalizar
                    if is_feminine and not name_lower.endswith('a'):
                        gender_score = 100
                    if not is_feminine and not name_lower.endswith('o'):
                        gender_score = 100

                    adjusted_distance = distance + gender_score
                    gendered_candidates.append((name, adjusted_distance))

                if gendered_candidates:
                    # Ordenar por distancia ajustada y tomar el mejor
                    gendered_candidates.sort(key=lambda x: x[1])
                    # Solo tomar si la distancia ajustada es razonable (< 300)
                    if gendered_candidates[0][1] < 300:
                        return gendered_candidates[0][0]

                # Fallback: buscar segunda persona más cercana
                person_candidates_sorted = sorted(person_candidates, key=lambda x: x[3])
                if len(person_candidates_sorted) >= 2 and person_candidates_sorted[1][3] < 200:
                    return person_candidates_sorted[1][0]

                # Si todo falla, devolver la más cercana
                if person_candidates_sorted:
                    return person_candidates_sorted[0][0]

        # Caso 1: Sujeto elíptico (verbo en 3ª persona sin sujeto)
        # En español, el sujeto elíptico típicamente refiere al sujeto de la oración anterior
        if has_3rd_person_verb and not has_pronoun and last_sentence_break > 0:
            # Buscar persona ANTES del último punto (oración anterior)
            before_sentence_break = context[:last_sentence_break]

            # Buscar candidatos antes del punto
            before_break_candidates = []
            for name, start, end, distance in person_candidates:
                if start < (context_start + last_sentence_break):
                    # Calcular distancia desde el punto
                    dist_from_break = (context_start + last_sentence_break) - end

                    # MEJORA: Identificar si es SUJETO u OBJETO en la oración anterior
                    # Heurística: "a [Name]" indica objeto (acusativo en español)
                    name_pos_in_context = start - context_start
                    is_object = False

                    if name_pos_in_context > 0:
                        # Buscar "a " justo antes del nombre
                        prefix = context[max(0, name_pos_in_context - 3):name_pos_in_context]
                        if prefix.strip().endswith('a') or ' a ' in prefix:
                            is_object = True

                    # También verificar patrones de complemento indirecto
                    # "le dijo a Juan" → Juan es objeto
                    indirect_pattern = regex_module.search(
                        rf'\b(le|les)\s+\w+\s+a\s+{regex_module.escape(name)}\b',
                        before_sentence_break,
                        regex_module.IGNORECASE
                    )
                    if indirect_pattern:
                        is_object = True

                    # Penalizar objetos (el sujeto elíptico suele referir al sujeto)
                    object_penalty = 150 if is_object else 0
                    adjusted_dist = dist_from_break + object_penalty

                    before_break_candidates.append((name, start, end, dist_from_break, adjusted_dist, is_object))

            if before_break_candidates:
                # Ordenar por distancia ajustada (penalizando objetos)
                before_break_candidates.sort(key=lambda x: x[4])
                best = before_break_candidates[0]
                logger.debug(
                    f"Sujeto elíptico: seleccionando '{best[0]}' "
                    f"(dist={best[3]}, ajustada={best[4]}, es_objeto={best[5]})"
                )
                return best[0]

        # Caso 2 y 3: Pronombre o búsqueda general
        if person_candidates:
            # Ordenar por distancia y tomar el más cercano
            person_candidates.sort(key=lambda x: x[3])
            return person_candidates[0][0]

        # Si no hay personas, penalizar lugares severamente
        all_candidates = location_candidates
        if all_candidates:
            scored_candidates = []
            for name, start, end, distance in all_candidates:
                # Penalizar lugares muy fuertemente (x5)
                score = distance * 5
                scored_candidates.append((name, score))

            scored_candidates.sort(key=lambda x: x[1])
            # Solo retornar lugar si está MUY cerca (distancia * 5 < 100)
            if scored_candidates[0][1] < 100:
                return scored_candidates[0][0]

        return None

    def _deduplicate(
        self, attributes: list[ExtractedAttribute]
    ) -> list[ExtractedAttribute]:
        """Elimina atributos duplicados, manteniendo el de mayor confianza."""
        seen: dict[tuple, ExtractedAttribute] = {}

        for attr in attributes:
            key = (attr.entity_name.lower(), attr.key, attr.value)
            if key not in seen or attr.confidence > seen[key].confidence:
                seen[key] = attr

        return list(seen.values())

    def _resolve_conflicts(
        self, attributes: list[ExtractedAttribute]
    ) -> list[ExtractedAttribute]:
        """
        Resuelve conflictos donde una entidad tiene múltiples valores para el mismo atributo.

        Por ejemplo, si Juan tiene eye_color=verdes, eye_color=azules, eye_color=marrones,
        solo mantiene el de mayor confianza.

        Args:
            attributes: Lista de atributos (posiblemente con conflictos)

        Returns:
            Lista de atributos sin conflictos (un valor por entidad+key)
        """
        # Atributos que pueden tener múltiples valores legítimos
        MULTI_VALUE_KEYS = {
            AttributeKey.PERSONALITY,      # Puede tener múltiples rasgos
            AttributeKey.FEAR,             # Puede tener múltiples miedos
            AttributeKey.DESIRE,           # Puede tener múltiples deseos
            AttributeKey.DISTINCTIVE_FEATURE,  # Puede tener múltiples rasgos distintivos
            AttributeKey.RELATIONSHIP,     # Múltiples relaciones
            AttributeKey.OTHER,            # Categoría genérica
        }

        # Agrupar por (entidad, key) - sin el valor
        grouped: dict[tuple, list[ExtractedAttribute]] = {}
        for attr in attributes:
            group_key = (attr.entity_name.lower(), attr.key)
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(attr)

        resolved: list[ExtractedAttribute] = []

        for (entity, key), attrs in grouped.items():
            if len(attrs) == 1:
                # Sin conflicto
                resolved.append(attrs[0])
            elif key in MULTI_VALUE_KEYS:
                # Atributo que puede tener múltiples valores
                resolved.extend(attrs)
            else:
                # Conflicto: múltiples valores para atributo que debería ser único
                # Mantener solo el de mayor confianza
                best = max(attrs, key=lambda a: a.confidence)
                conflict_values = [a.value for a in attrs if a.value != best.value]
                if conflict_values:
                    logger.warning(
                        f"Conflicto de atributos para {entity}.{key.value}: "
                        f"manteniendo '{best.value}' (conf={best.confidence:.2f}), "
                        f"descartando: {conflict_values}"
                    )
                resolved.append(best)

        logger.debug(
            f"Resolución de conflictos: {len(attributes)} -> {len(resolved)} atributos"
        )
        return resolved

    def _extract_by_dependency(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]],
        chapter_id: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos usando dependency parsing de spaCy.

        Busca patrones sintácticos como:
        - Sujeto + verbo copulativo + atributo (Juan era alto)
        - Sujeto + verbo descriptivo + objeto (Juan tenía barba)
        - Modificadores adjetivales de entidades

        Basado en el estado del arte de Open Information Extraction.
        Ver: https://spacy.io/usage/linguistic-features

        Args:
            text: Texto a procesar
            entity_mentions: Menciones conocidas
            chapter_id: ID del capítulo

        Returns:
            Lista de atributos extraídos
        """
        nlp = self._get_nlp()
        if not nlp:
            return []

        attributes: list[ExtractedAttribute] = []

        try:
            doc = nlp(text)

            # Crear índice de menciones para búsqueda rápida (solo personas)
            mention_spans = {}
            if entity_mentions:
                normalized = _normalize_entity_mentions(entity_mentions)
                for name, start, end, entity_type in normalized:
                    # Solo incluir personas para atributos físicos
                    if entity_type is None or _is_person_entity(entity_type):
                        mention_spans[(start, end)] = name

            for sent in doc.sents:
                # Buscar verbos copulativos y descriptivos
                for token in sent:
                    # === Patrón 1: Sujeto + verbo copulativo + atributo ===
                    # "Juan era alto", "María estaba cansada"
                    if token.lemma_ in self._copulative_verbs and token.pos_ == "AUX":
                        subject = None
                        attribute_value = None
                        attr_token = None

                        for child in token.children:
                            # Buscar sujeto nominal
                            if child.dep_ in ("nsubj", "nsubj:pass"):
                                subject = child
                            # Buscar atributo (adjetivo o sustantivo predicativo)
                            elif child.dep_ in ("acomp", "attr", "xcomp", "ROOT") or \
                                 (child.pos_ == "ADJ" and child.dep_ == "ROOT"):
                                attribute_value = child.text
                                attr_token = child

                        # También buscar atributos como hijos del ROOT
                        if not attribute_value:
                            for child in token.head.children:
                                if child.pos_ == "ADJ" and child != token:
                                    attribute_value = child.text
                                    attr_token = child
                                    break

                        if subject and attribute_value:
                            entity_name = self._resolve_entity_from_token(
                                subject, mention_spans, doc
                            )
                            if entity_name and len(attribute_value) > 1:
                                # Determinar categoría
                                category = self._infer_category(attribute_value, attr_token)

                                confidence = 0.55  # Menor que patrones explícitos
                                if confidence >= self.min_confidence:
                                    attr = ExtractedAttribute(
                                        entity_name=entity_name,
                                        category=category,
                                        key=AttributeKey.OTHER,
                                        value=attribute_value.lower(),
                                        source_text=sent.text,
                                        start_char=sent.start_char,
                                        end_char=sent.end_char,
                                        confidence=confidence,
                                        chapter_id=chapter_id,
                                    )
                                    attributes.append(attr)

                    # === Patrón 2: Sujeto + verbo descriptivo + objeto ===
                    # "Juan tenía barba", "María llevaba gafas"
                    if token.lemma_ in self._descriptive_verbs and token.pos_ == "VERB":
                        subject = None
                        obj = None

                        for child in token.children:
                            if child.dep_ in ("nsubj", "nsubj:pass"):
                                subject = child
                            elif child.dep_ in ("dobj", "obj", "obl"):
                                obj = child

                        if subject and obj:
                            entity_name = self._resolve_entity_from_token(
                                subject, mention_spans, doc
                            )
                            if entity_name and len(obj.text) > 1:
                                # Obtener modificadores del objeto
                                obj_text = obj.text
                                for mod in obj.children:
                                    if mod.pos_ == "ADJ" and mod.i < obj.i:
                                        obj_text = f"{mod.text} {obj_text}"

                                confidence = 0.5
                                if confidence >= self.min_confidence:
                                    attr = ExtractedAttribute(
                                        entity_name=entity_name,
                                        category=AttributeCategory.PHYSICAL,
                                        key=AttributeKey.DISTINCTIVE_FEATURE,
                                        value=obj_text.lower(),
                                        source_text=sent.text,
                                        start_char=sent.start_char,
                                        end_char=sent.end_char,
                                        confidence=confidence,
                                        chapter_id=chapter_id,
                                    )
                                    attributes.append(attr)

                    # === Patrón 3: Entidad con modificador adjetival ===
                    # "el valiente Juan", "la hermosa María"
                    if token.pos_ == "PROPN" and token.ent_type_ in ("PER", "PERSON", ""):
                        for child in token.children:
                            if child.pos_ == "ADJ" and child.dep_ == "amod":
                                confidence = 0.6
                                if confidence >= self.min_confidence:
                                    attr = ExtractedAttribute(
                                        entity_name=token.text,
                                        category=self._infer_category(child.text, child),
                                        key=AttributeKey.OTHER,
                                        value=child.text.lower(),
                                        source_text=sent.text,
                                        start_char=sent.start_char,
                                        end_char=sent.end_char,
                                        confidence=confidence,
                                        chapter_id=chapter_id,
                                    )
                                    attributes.append(attr)

        except Exception as e:
            logger.warning(f"Error en extracción por dependencias: {e}")

        return attributes

    def _resolve_entity_from_token(
        self,
        token,
        mention_spans: dict,
        doc,
    ) -> Optional[str]:
        """
        Resuelve un token a un nombre de entidad.

        Intenta:
        1. Buscar en menciones conocidas
        2. Usar el texto del token si es nombre propio
        3. Resolver pronombres a entidad cercana usando menciones conocidas

        Optimizado para precisión sobre velocidad.
        """
        # Si es nombre propio, usar directamente
        if token.pos_ == "PROPN":
            return token.text

        # Buscar en menciones conocidas por posición
        for (start, end), name in mention_spans.items():
            if start <= token.idx < end:
                return name

        # Si es pronombre, buscar entidad cercana con análisis exhaustivo
        if token.pos_ == "PRON":
            # 1. Buscar nombre propio más cercano ANTES del pronombre
            # Recorrer tokens anteriores buscando nombres propios
            best_candidate = None
            best_distance = float('inf')

            for i, prev_token in enumerate(doc):
                if prev_token.i >= token.i:
                    break  # Solo buscar antes del pronombre

                # Si es nombre propio y es persona (heurística)
                if prev_token.pos_ == "PROPN":
                    distance = token.i - prev_token.i

                    # Filtrar lugares comunes
                    if prev_token.text not in ['Retiro', 'Madrid'] and distance < best_distance:
                        # Verificar que no sea parte de un nombre de lugar
                        # Buscar si tiene preposiciones como "del", "de", "el" cerca
                        is_location = False
                        if prev_token.i > 0:
                            prev_prev = doc[prev_token.i - 1]
                            if prev_prev.text.lower() in ['del', 'de', 'el', 'la']:
                                is_location = True

                        if not is_location:
                            best_candidate = prev_token.text
                            best_distance = distance

            if best_candidate and best_distance < 50:  # Ventana de 50 tokens
                return best_candidate

            # 2. Si no encontramos nombre propio, buscar en mention_spans
            sorted_mentions = sorted(mention_spans.items(), key=lambda x: x[0][0], reverse=True)

            person_mentions = []
            for (start, end), name in sorted_mentions:
                if end < token.idx:  # Está antes del pronombre
                    # Heurística para distinguir personas
                    name_words = name.split()
                    is_likely_person = (
                        len(name_words) <= 2 and
                        not any(word.lower() in ['parque', 'del', 'de', 'la', 'el', 'retiro'] for word in name_words)
                    )

                    if is_likely_person:
                        person_mentions.append((start, end, name, token.idx - end))

            # Ordenar por distancia y tomar el más cercano
            if person_mentions:
                person_mentions.sort(key=lambda x: x[3])
                return person_mentions[0][2]

        return None

    def _infer_category(self, value: str, token) -> AttributeCategory:
        """Infiere la categoría del atributo basándose en el valor y POS."""
        value_lower = value.lower()

        # Físicos
        if value_lower in BUILD_TYPES or value_lower in COLORS:
            return AttributeCategory.PHYSICAL

        # Psicológicos
        if value_lower in PERSONALITY_TRAITS:
            return AttributeCategory.PSYCHOLOGICAL

        # Por defecto, usar PHYSICAL para adjetivos descriptivos
        if token and token.pos_ == "ADJ":
            return AttributeCategory.PHYSICAL

        return AttributeCategory.SOCIAL

    def extract_from_context(
        self,
        entity_name: str,
        context: str,
        context_start: int = 0,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos del contexto de una mención específica.

        Args:
            entity_name: Nombre de la entidad
            context: Texto del contexto
            context_start: Posición de inicio del contexto en el documento

        Returns:
            Lista de atributos extraídos
        """
        result = self.extract_attributes(
            context,
            entity_mentions=[(entity_name, 0, len(entity_name))],
        )

        if result.is_success:
            # Ajustar posiciones al contexto global
            for attr in result.value.attributes:
                attr.start_char += context_start
                attr.end_char += context_start
            return result.value.attributes

        return []


def extract_attributes(
    text: str,
    entity_mentions: Optional[list[tuple[str, int, int]]] = None,
) -> Result[AttributeExtractionResult]:
    """
    Función de conveniencia para extraer atributos.

    Args:
        text: Texto a procesar
        entity_mentions: Menciones conocidas

    Returns:
        Result con AttributeExtractionResult
    """
    extractor = get_attribute_extractor()
    return extractor.extract_attributes(text, entity_mentions)


# =============================================================================
# Singleton thread-safe
# =============================================================================

import threading

_extractor_lock = threading.Lock()
_attribute_extractor: Optional[AttributeExtractor] = None


def get_attribute_extractor(
    filter_metaphors: bool = True,
    min_confidence: float = 0.5,
    use_llm: bool = True,
    use_embeddings: bool = True,
    use_dependency_extraction: bool = True,
    use_patterns: bool = True,
) -> AttributeExtractor:
    """
    Obtiene el singleton del extractor de atributos.

    Args:
        filter_metaphors: Filtrar expresiones metafóricas
        min_confidence: Confianza mínima
        use_llm: Habilitar extracción por LLM
        use_embeddings: Habilitar extracción por embeddings
        use_dependency_extraction: Habilitar extracción por dependencias
        use_patterns: Habilitar extracción por patrones

    Returns:
        Instancia única del AttributeExtractor
    """
    global _attribute_extractor

    if _attribute_extractor is None:
        with _extractor_lock:
            if _attribute_extractor is None:
                _attribute_extractor = AttributeExtractor(
                    filter_metaphors=filter_metaphors,
                    min_confidence=min_confidence,
                    use_llm=use_llm,
                    use_embeddings=use_embeddings,
                    use_dependency_extraction=use_dependency_extraction,
                    use_patterns=use_patterns,
                )

    return _attribute_extractor


def reset_attribute_extractor() -> None:
    """Resetea el singleton (útil para tests)."""
    global _attribute_extractor
    with _extractor_lock:
        _attribute_extractor = None


# =============================================================================
# Resolución de atributos con correferencias
# =============================================================================

def resolve_attributes_with_coreferences(
    attributes: list[ExtractedAttribute],
    coref_chains: list,  # list[CoreferenceChain] - evitar import circular
    text: str,
) -> list[ExtractedAttribute]:
    """
    Resuelve nombres de entidades en atributos usando cadenas de correferencia.

    Cuando un atributo tiene entity_name="Ella" o "él", busca en las cadenas
    de correferencia para encontrar el nombre propio correspondiente.

    Args:
        attributes: Lista de atributos extraídos
        coref_chains: Cadenas de correferencia (del CorefResult)
        text: Texto original para buscar posiciones

    Returns:
        Lista de atributos con entity_name resueltos

    Example:
        >>> # Antes: Ella.hair_color = "rubio"
        >>> # Después: María.hair_color = "rubio" (si Ella -> María en coref)
    """
    if not coref_chains or not attributes:
        return attributes

    # Construir mapa de menciones -> nombre principal
    mention_to_entity: dict[str, str] = {}
    position_to_entity: dict[tuple[int, int], str] = {}

    for chain in coref_chains:
        # Obtener el nombre principal de la cadena
        main_name = chain.main_mention
        if not main_name:
            # Buscar la primera mención que sea nombre propio
            for mention in chain.mentions:
                if hasattr(mention, 'mention_type'):
                    # MentionType.PROPER_NOUN
                    if mention.mention_type.value == "proper_noun":
                        main_name = mention.text
                        break
                elif mention.text and mention.text[0].isupper():
                    # Heurística: empieza con mayúscula
                    text_lower = mention.text.lower()
                    # No es pronombre
                    if text_lower not in {
                        "él", "ella", "ellos", "ellas", "este", "esta",
                        "ese", "esa", "aquel", "aquella", "lo", "la", "le",
                    }:
                        main_name = mention.text
                        break

        if not main_name:
            continue

        # Mapear todas las menciones de la cadena al nombre principal
        for mention in chain.mentions:
            mention_text_lower = mention.text.lower().strip()
            mention_to_entity[mention_text_lower] = main_name

            # También mapear por posición
            if hasattr(mention, 'start_char') and hasattr(mention, 'end_char'):
                position_to_entity[(mention.start_char, mention.end_char)] = main_name

    # Resolver atributos
    resolved_attributes = []
    pronouns = {
        "él", "ella", "ellos", "ellas", "este", "esta", "ese", "esa",
        "aquel", "aquella", "lo", "la", "le", "les", "su", "sus",
    }

    for attr in attributes:
        entity_lower = attr.entity_name.lower().strip()

        # Verificar si es pronombre o mención que necesita resolución
        needs_resolution = (
            entity_lower in pronouns or
            entity_lower in mention_to_entity or
            not attr.entity_name[0].isupper()  # No empieza con mayúscula
        )

        if needs_resolution:
            resolved_name = None

            # 1. Buscar por posición exacta
            attr_pos = (attr.start_char, attr.end_char)
            if attr_pos in position_to_entity:
                resolved_name = position_to_entity[attr_pos]

            # 2. Buscar por texto de mención
            if not resolved_name and entity_lower in mention_to_entity:
                resolved_name = mention_to_entity[entity_lower]

            # 3. Buscar por proximidad en el texto
            if not resolved_name:
                resolved_name = _find_nearest_antecedent(
                    attr.start_char,
                    position_to_entity,
                    text,
                )

            if resolved_name:
                # Crear nuevo atributo con nombre resuelto
                resolved_attr = ExtractedAttribute(
                    entity_name=resolved_name,
                    category=attr.category,
                    key=attr.key,
                    value=attr.value,
                    source_text=attr.source_text,
                    start_char=attr.start_char,
                    end_char=attr.end_char,
                    confidence=attr.confidence * 0.95,  # Ligera penalización por resolución
                    is_negated=attr.is_negated,
                    is_metaphor=attr.is_metaphor,
                    chapter_id=attr.chapter_id,
                )
                resolved_attributes.append(resolved_attr)
                logger.debug(
                    f"Atributo resuelto: {attr.entity_name} -> {resolved_name} "
                    f"({attr.key.value}={attr.value})"
                )
                continue

        # No necesita resolución o no se pudo resolver
        resolved_attributes.append(attr)

    return resolved_attributes


def _find_nearest_antecedent(
    position: int,
    position_to_entity: dict[tuple[int, int], str],
    text: str,
    max_distance: int = 500,
) -> Optional[str]:
    """
    Encuentra el antecedente más cercano por posición en el texto.

    Busca hacia atrás desde la posición del atributo.
    """
    nearest_name = None
    nearest_distance = max_distance

    for (start, end), name in position_to_entity.items():
        # Solo considerar menciones anteriores
        if end <= position:
            distance = position - end
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_name = name

    return nearest_name


# =============================================================================
# Funciones para pesos entrenables
# =============================================================================

def set_method_weights(weights: dict[str, float]) -> None:
    """
    Establece pesos personalizados para los métodos de votación.

    Args:
        weights: Diccionario {método: peso}
                 Métodos válidos: llm, embeddings, dependency, patterns

    Example:
        >>> set_method_weights({"llm": 0.88, "embeddings": 0.04, "dependency": 0.04, "patterns": 0.04})
    """
    global METHOD_WEIGHTS

    # Validar métodos
    valid_methods = {"llm", "embeddings", "dependency", "patterns"}
    for method in weights:
        if method not in valid_methods:
            raise ValueError(f"Método desconocido: {method}. Válidos: {valid_methods}")

    # Actualizar pesos
    METHOD_WEIGHTS.update(weights)

    # Normalizar para que sumen 1.0
    total = sum(METHOD_WEIGHTS.values())
    if total > 0:
        for method in METHOD_WEIGHTS:
            METHOD_WEIGHTS[method] /= total

    logger.info(f"Pesos de votación actualizados: {METHOD_WEIGHTS}")


def load_trained_weights(path: "Path") -> dict[str, float]:
    """
    Carga pesos entrenados desde archivo y los aplica.

    Args:
        path: Ruta al archivo JSON con pesos entrenados
              (generado por TrainableWeightedVoting.save())

    Returns:
        Diccionario con los pesos cargados

    Example:
        >>> from pathlib import Path
        >>> weights = load_trained_weights(Path("weights.json"))
        >>> print(weights)
        {'llm': 0.88, 'embeddings': 0.04, 'dependency': 0.04, 'patterns': 0.04}
    """
    from pathlib import Path as PathClass
    import json

    path = PathClass(path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo de pesos no encontrado: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    weights = data.get("weights", {})
    if not weights:
        raise ValueError(f"No se encontraron pesos en {path}")

    set_method_weights(weights)

    logger.info(f"Pesos cargados desde {path}: {weights}")
    return weights


def reset_method_weights() -> None:
    """Restablece los pesos a los valores por defecto."""
    global METHOD_WEIGHTS
    METHOD_WEIGHTS = dict(DEFAULT_METHOD_WEIGHTS)
    logger.info(f"Pesos restablecidos a defaults: {METHOD_WEIGHTS}")


def get_current_weights() -> dict[str, float]:
    """Obtiene los pesos de votación actuales."""
    return dict(METHOD_WEIGHTS)


def train_weights_from_examples(
    num_synthetic_examples: int = 10,
    output_path: Optional["Path"] = None,
    method: str = "nnls",
    apply_weights: bool = True,
) -> dict[str, float]:
    """
    Entrena pesos usando ejemplos sintéticos y opcionalmente los aplica.

    Esta función es una conveniencia para entrenar pesos sin necesidad
    de importar el módulo training_data.

    Args:
        num_synthetic_examples: Ejemplos por escenario (5-20 recomendado)
        output_path: Ruta para guardar los pesos (opcional)
        method: Método de optimización ('nnls' o 'grid_search')
        apply_weights: Si aplicar los pesos entrenados inmediatamente

    Returns:
        Diccionario con los pesos aprendidos

    Example:
        >>> weights = train_weights_from_examples(num_synthetic_examples=10)
        >>> print(weights)
        {'llm': 0.88, 'embeddings': 0.04, 'dependency': 0.04, 'patterns': 0.04}
    """
    from pathlib import Path as PathClass
    from .training_data import generate_synthetic_dataset, TrainableWeightedVoting

    # Generar dataset sintético
    examples = generate_synthetic_dataset(
        num_examples_per_scenario=num_synthetic_examples,
        add_noise=True,
    )

    # Entrenar
    learner = TrainableWeightedVoting()
    result = learner.train(examples, method=method)

    # Guardar si se especifica ruta
    if output_path:
        output_path = PathClass(output_path)
        learner.save(output_path)

    # Aplicar si se solicita
    if apply_weights:
        set_method_weights(result.weights)

    logger.info(
        f"Pesos entrenados con {len(examples)} ejemplos: {result.weights}\n"
        f"MSE: {result.mse:.4f}, Accuracy: {result.accuracy:.2%}"
    )

    return result.weights
