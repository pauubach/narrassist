"""
Extracción de Atributos de entidades narrativas.

Detecta atributos físicos, psicológicos y relacionales de personajes
y otras entidades a partir del texto circundante a sus menciones.

Incluye filtro de metáforas para evitar falsos positivos como
"sus ojos eran dos luceros" o "era alto como un roble".

Tipos de atributos soportados:
- Personajes: físicos (ojos, pelo, edad, altura), psicológicos, roles
- Lugares: características, clima, tamaño
- Objetos: material, color, tamaño, estado
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.result import Result
from ..core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)


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
        0.6,  # Menor confianza, necesita resolver "sus"
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
    (
        r"[EeÉé]l?\s+era\s+(?:un\s+)?(?:hombre|mujer)\s+(muy\s+)?(alto|alta|bajo|baja|"
        r"delgado|delgada|corpulento|corpulenta|fornido|fornida)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.75,
        False,
    ),
    # "era un hombre bajo y fornido" - captura ambos
    (
        r"era\s+(?:un\s+)?(?:hombre|mujer)\s+(?:muy\s+)?(alto|alta|bajo|baja)\s+y\s+"
        r"(delgado|delgada|corpulento|corpulenta|fornido|fornida|esbelto|esbelta)",
        AttributeKey.BUILD,
        AttributeCategory.PHYSICAL,
        0.8,
        False,
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
    # "mujer alta" / "hombre bajo" (en contexto)
    (
        r"(?:una?\s+)?(mujer|hombre)\s+(muy\s+)?(alto|alta|bajo|baja|delgado|delgada)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.7,
        False,
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
    # "Era una mujer alta, de aproximadamente treinta años"
    (
        r"[Ee]ra\s+(?:una?\s+)?(mujer|hombre)\s+(alto|alta|bajo|baja)",
        AttributeKey.HEIGHT,
        AttributeCategory.PHYSICAL,
        0.75,
        False,
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

# Indicadores de negación
NEGATION_INDICATORS = [
    r"\bno\b",
    r"\bnunca\b",
    r"\bjamás\b",
    r"\bsin\b",
    r"\bcarec[íi]a\b",
    r"\bfaltaba\b",
]


class AttributeExtractor:
    """
    Extractor de atributos de entidades narrativas.

    Combina dos estrategias:
    1. Patrones regex predefinidos (alta precisión)
    2. Dependency parsing con spaCy (alta cobertura)

    La extracción por dependencias analiza el árbol sintáctico para
    encontrar relaciones sujeto-verbo-atributo genéricas que no
    requieren patrones específicos.

    Attributes:
        filter_metaphors: Si filtrar expresiones metafóricas
        min_confidence: Confianza mínima para incluir atributos
        use_dependency_extraction: Usar extracción por dependencias
    """

    def __init__(
        self,
        filter_metaphors: bool = True,
        min_confidence: float = 0.5,
        use_dependency_extraction: bool = True,
    ):
        """
        Inicializa el extractor.

        Args:
            filter_metaphors: Filtrar metáforas y comparaciones
            min_confidence: Confianza mínima (0.0-1.0)
            use_dependency_extraction: Habilitar extracción por dependencias
        """
        self.filter_metaphors = filter_metaphors
        self.min_confidence = min_confidence
        self.use_dependency_extraction = use_dependency_extraction

        # spaCy para dependency parsing
        self._nlp = None

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

    def extract_attributes(
        self,
        text: str,
        entity_mentions: Optional[list[tuple[str, int, int]]] = None,
        chapter_id: Optional[int] = None,
    ) -> Result[AttributeExtractionResult]:
        """
        Extrae atributos del texto.

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

        try:
            for pattern, key, category, base_conf, swap_groups in self._compiled_patterns:
                for match in pattern.finditer(text):
                    # Obtener contexto para análisis
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context = text[context_start:context_end]

                    # Verificar si es metáfora
                    is_metaphor = self._is_metaphor(context)
                    if is_metaphor and self.filter_metaphors:
                        result.metaphors_filtered += 1
                        continue

                    # Verificar negación
                    is_negated = self._is_negated(context, match.start() - context_start)

                    # Extraer grupos
                    groups = match.groups()
                    if len(groups) < 2:
                        # Patrón con un solo grupo (ej: "sus ojos verdes")
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

                    # Validar valor según tipo de atributo
                    if not self._validate_value(key, value):
                        continue

                    # Ajustar confianza
                    confidence = base_conf
                    if is_metaphor:
                        confidence *= 0.5  # Reducir si es metáfora pero no filtrada
                    if is_negated:
                        confidence *= 0.9  # Ligeramente menor para negaciones

                    if confidence < self.min_confidence:
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
                    result.attributes.append(attr)

            # Extracción por dependencias (más genérica)
            if self.use_dependency_extraction:
                dep_attrs = self._extract_by_dependency(
                    text, entity_mentions, chapter_id
                )
                result.attributes.extend(dep_attrs)

            # Eliminar duplicados (mismo atributo extraído por múltiples patrones)
            result.attributes = self._deduplicate(result.attributes)

            logger.debug(
                f"Atributos extraídos: {len(result.attributes)}, "
                f"metáforas filtradas: {result.metaphors_filtered}"
            )

            return Result.success(result)

        except Exception as e:
            error = AttributeExtractionError(
                text_sample=text[:100] if len(text) > 100 else text,
                original_error=str(e),
            )
            logger.error(f"Error extrayendo atributos: {e}")
            return Result.partial(result, [error])

    def _is_metaphor(self, context: str) -> bool:
        """Detecta si el contexto sugiere una metáfora."""
        for pattern in self._metaphor_patterns:
            if pattern.search(context):
                return True
        return False

    def _is_negated(self, context: str, match_pos: int) -> bool:
        """Detecta si el atributo está negado."""
        # Solo buscar en el contexto antes del match
        before_context = context[:match_pos]
        for pattern in self._negation_patterns:
            # Buscar negación cercana (últimas 20 caracteres)
            if pattern.search(before_context[-20:]):
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
            return value_lower in COLORS or value_lower in HAIR_TYPES

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

        # Para otros tipos, aceptar cualquier valor no vacío
        return len(value) > 1

    def _find_nearest_entity(
        self,
        text: str,
        position: int,
        entity_mentions: Optional[list[tuple[str, int, int]]],
    ) -> Optional[str]:
        """
        Encuentra la entidad más cercana a una posición.

        Útil para resolver "sus ojos" o pronombres como "ella".
        Resuelve correferencias usando contexto y prioriza entidades tipo PERSON.
        Maneja sujetos elípticos en español.
        """
        if not entity_mentions:
            return None

        import re as regex_module

        # Extraer contexto alrededor de la posición (400 chars antes para capturar oraciones previas)
        context_start = max(0, position - 400)
        context = text[context_start:position]

        # También extraer un poco adelante (20 chars) para detectar patrones que inician en position
        context_forward = text[position:position + 20]

        # Buscar todas las entidades antes de la posición con sus distancias
        candidates = []
        for name, start, end in entity_mentions:
            if end <= position:
                distance = position - end
                if distance < 400:  # Ventana amplia
                    candidates.append((name, start, end, distance))

        if not candidates:
            return None

        # Clasificar entidades por tipo
        person_candidates = []
        location_candidates = []

        for name, start, end, distance in candidates:
            name_words = name.split()
            is_likely_person = (
                len(name_words) <= 2 and
                not any(word.lower() in ['parque', 'del', 'de', 'la', 'el', 'retiro', 'madrid'] for word in name_words) and
                name[0].isupper()
            )

            if is_likely_person:
                person_candidates.append((name, start, end, distance))
            else:
                location_candidates.append((name, start, end, distance))

        # Buscar límites de oración (. ! ?) para entender contexto
        last_sentence_break = max(
            context.rfind('.'),
            context.rfind('!'),
            context.rfind('?')
        )

        # Buscar pronombres o verbos en 3ª persona que indican sujeto elíptico
        immediate_context = context[-50:] if len(context) > 50 else context
        has_pronoun = bool(regex_module.search(r'\b(ella|él|su|sus|la|lo|le)\b', immediate_context, regex_module.IGNORECASE))
        has_3rd_person_verb = bool(regex_module.search(r'\b(tenía|era|estaba|llevaba|parecía|mostraba)\b', immediate_context, regex_module.IGNORECASE))

        # Detectar pronombres posesivos que podrían referirse al objeto (no al sujeto)
        # Ej: "Juan la saludó, sorprendido por su cabello" -> "su" se refiere a "la" (María), no a Juan
        # Buscar tanto en contexto anterior como en el inicio del match (context_forward)
        has_possessive = bool(regex_module.search(r'\b(su|sus)\b', immediate_context + " " + context_forward, regex_module.IGNORECASE))
        has_object_pronoun = bool(regex_module.search(r'\b(la|lo|le)\b', immediate_context, regex_module.IGNORECASE))

        # Estrategia de selección mejorada:
        # 0. Si hay "su/sus" después de un pronombre objeto "la/lo/le" → buscar referente del objeto
        # 1. Si hay verbo en 3ª persona SIN sujeto explícito cerca → sujeto elíptico, buscar persona en oración anterior
        # 2. Si hay pronombre → buscar persona más cercana
        # 3. Si no hay indicadores → usar persona más cercana pero penalizar lugares

        # Caso 0: Pronombre posesivo refiriéndose al objeto
        # Patrón: "Juan la saludó... su cabello" -> "su" se refiere a "la" (María), no a Juan
        if has_possessive and has_object_pronoun and person_candidates:
            # Buscar "la" o "lo" seguido eventualmente de "su/sus"
            # El objeto suele estar antes que el posesivo en español
            # IMPORTANTE: Buscar en immediate_context + forward para capturar "su" que está en la posición actual
            search_text = immediate_context + " " + context_forward
            obj_pronoun_match = regex_module.search(r'\b(la|lo)\b.*?\b(su|sus)\b', search_text, regex_module.IGNORECASE | regex_module.DOTALL)

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
        if has_3rd_person_verb and not has_pronoun and last_sentence_break > 0:
            # Buscar persona ANTES del último punto (oración anterior)
            before_sentence_break = context[:last_sentence_break]

            # Buscar candidatos antes del punto
            before_break_candidates = []
            for name, start, end, distance in person_candidates:
                if start < (context_start + last_sentence_break):
                    # Calcular distancia desde el punto
                    dist_from_break = (context_start + last_sentence_break) - end
                    before_break_candidates.append((name, start, end, dist_from_break))

            if before_break_candidates:
                # Tomar la persona más cercana ANTES del punto
                before_break_candidates.sort(key=lambda x: x[3])
                return before_break_candidates[0][0]

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

            # Crear índice de menciones para búsqueda rápida
            mention_spans = {}
            if entity_mentions:
                for name, start, end in entity_mentions:
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
) -> AttributeExtractor:
    """
    Obtiene el singleton del extractor de atributos.

    Args:
        filter_metaphors: Filtrar expresiones metafóricas
        min_confidence: Confianza mínima

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
                )

    return _attribute_extractor


def reset_attribute_extractor() -> None:
    """Resetea el singleton (útil para tests)."""
    global _attribute_extractor
    with _extractor_lock:
        _attribute_extractor = None
