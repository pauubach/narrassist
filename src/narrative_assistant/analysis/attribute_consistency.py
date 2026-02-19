"""
Verificador de Consistencia de Atributos.

Detecta cuando una entidad tiene valores contradictorios para
el mismo atributo en diferentes partes del texto.

Ejemplo: "ojos verdes" en cap. 2 vs "ojos azules" en cap. 5

Estrategias de detección:
1. Antónimos conocidos (verde/azul, alto/bajo)
2. Similitud semántica con embeddings
3. Reglas específicas por tipo de atributo
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..nlp.attributes import (
    AttributeKey,
    ExtractedAttribute,
)

logger = logging.getLogger(__name__)


# Traducciones de claves de atributos a español
# (nombre, género: 'm'=masculino, 'f'=femenino)
ATTRIBUTE_KEY_INFO: dict[str, tuple[str, str]] = {
    "eye_color": ("color de ojos", "m"),
    "hair_color": ("color de cabello", "m"),
    "hair_type": ("tipo de cabello", "m"),
    "hair_modification": ("modificación de cabello", "f"),  # teñido, natural, decolorado
    "age": ("edad", "f"),
    "apparent_age": ("edad aparente", "f"),
    "height": ("altura", "f"),
    "build": ("complexión", "f"),
    "skin": ("piel", "f"),
    "distinctive_feature": ("rasgo distintivo", "m"),
    "facial_hair": ("vello facial", "m"),
    "personality": ("personalidad", "f"),
    "temperament": ("temperamento", "m"),
    "fear": ("miedo", "m"),
    "desire": ("deseo", "m"),
    "profession": ("profesión", "f"),
    "title": ("título", "m"),
    "relationship": ("relación", "f"),
    "nationality": ("nacionalidad", "f"),
    "climate": ("clima", "m"),
    "terrain": ("terreno", "m"),
    "size": ("tamaño", "m"),
    "location": ("ubicación", "f"),
    "material": ("material", "m"),
    "color": ("color", "m"),
    "condition": ("estado", "m"),
    "other": ("atributo", "m"),
}

# Compatibilidad hacia atrás
ATTRIBUTE_KEY_TRANSLATIONS = {k: v[0] for k, v in ATTRIBUTE_KEY_INFO.items()}


def get_attribute_display_name(attr_key: "AttributeKey") -> str:
    """Obtiene el nombre traducido de un atributo."""
    key_value = attr_key.value if hasattr(attr_key, "value") else str(attr_key)
    info = ATTRIBUTE_KEY_INFO.get(key_value)
    if info:
        return info[0]
    return key_value.replace("_", " ")


def get_attribute_gender(attr_key: "AttributeKey") -> str:
    """Obtiene el género gramatical de un atributo ('m' o 'f')."""
    key_value = attr_key.value if hasattr(attr_key, "value") else str(attr_key)
    info = ATTRIBUTE_KEY_INFO.get(key_value)
    return info[1] if info else "m"  # masculino por defecto


class InconsistencyType(Enum):
    """Tipos de inconsistencia detectada."""

    ANTONYM = "antonym"  # Valores opuestos conocidos
    SEMANTIC_DIFF = "semantic_diff"  # Diferencia semántica alta
    VALUE_CHANGE = "value_change"  # Cambio de valor numérico
    CONTRADICTORY = "contradictory"  # Contradicción explícita


@dataclass
class ConflictingValue:
    """
    Representa un valor en un conflicto multi-valor.

    Attributes:
        value: Valor del atributo
        chapter: Capítulo donde aparece
        excerpt: Extracto del texto
        position: Posición en caracteres
    """

    value: str
    chapter: int | None
    excerpt: str
    position: int = 0


@dataclass
class AttributeInconsistency:
    """
    Representa una inconsistencia detectada entre atributos.

    Soporta tanto inconsistencias de 2 valores (legacy) como N valores (multi-valor).

    Attributes:
        entity_name: Nombre de la entidad
        entity_id: ID de la entidad en la base de datos
        attribute_key: Clave del atributo inconsistente
        conflicting_values: Lista de valores conflictivos (para N valores)
        value1: Primer valor encontrado (legacy, solo para 2 valores)
        value1_chapter: Capítulo del primer valor (legacy)
        value1_excerpt: Extracto del texto (legacy)
        value1_position: Posición en caracteres del primer valor (legacy)
        value2: Segundo valor encontrado (legacy, solo para 2 valores)
        value2_chapter: Capítulo del segundo valor (legacy)
        value2_excerpt: Extracto del texto (legacy)
        value2_position: Posición en caracteres del segundo valor (legacy)
        inconsistency_type: Tipo de inconsistencia
        confidence: Confianza de que sea inconsistencia real (0.0-1.0)
        explanation: Explicación legible
    """

    entity_name: str
    entity_id: int
    attribute_key: AttributeKey
    # Multi-valor (preferido)
    conflicting_values: list[ConflictingValue] = field(default_factory=list)
    # Legacy (compatibilidad hacia atrás para tests existentes)
    value1: str = ""
    value1_chapter: int | None = None
    value1_excerpt: str = ""
    value1_position: int = 0
    value2: str = ""
    value2_chapter: int | None = None
    value2_excerpt: str = ""
    value2_position: int = 0
    inconsistency_type: InconsistencyType = InconsistencyType.VALUE_CHANGE
    confidence: float = 0.5
    explanation: str = ""

    def __post_init__(self):
        """Inicializa campos legacy si conflicting_values está vacío."""
        # Si no hay conflicting_values pero sí value1/value2, construir desde legacy
        if not self.conflicting_values and self.value1 and self.value2:
            self.conflicting_values = [
                ConflictingValue(
                    value=self.value1,
                    chapter=self.value1_chapter,
                    excerpt=self.value1_excerpt,
                    position=self.value1_position,
                ),
                ConflictingValue(
                    value=self.value2,
                    chapter=self.value2_chapter,
                    excerpt=self.value2_excerpt,
                    position=self.value2_position,
                ),
            ]
        # Si hay conflicting_values pero no value1/value2, sincronizar legacy
        elif self.conflicting_values and not self.value1:
            if len(self.conflicting_values) >= 1:
                first = self.conflicting_values[0]
                self.value1 = first.value
                self.value1_chapter = first.chapter
                self.value1_excerpt = first.excerpt
                self.value1_position = first.position
            if len(self.conflicting_values) >= 2:
                second = self.conflicting_values[1]
                self.value2 = second.value
                self.value2_chapter = second.chapter
                self.value2_excerpt = second.excerpt
                self.value2_position = second.position

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "attribute_key": self.attribute_key.value,
            "conflicting_values": [
                {
                    "value": cv.value,
                    "chapter": cv.chapter,
                    "excerpt": cv.excerpt,
                    "position": cv.position,
                }
                for cv in self.conflicting_values
            ],
            "value1": self.value1,
            "value1_chapter": self.value1_chapter,
            "value1_excerpt": self.value1_excerpt,
            "value1_position": self.value1_position,
            "value2": self.value2,
            "value2_chapter": self.value2_chapter,
            "value2_excerpt": self.value2_excerpt,
            "value2_position": self.value2_position,
            "inconsistency_type": self.inconsistency_type.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass
class ConsistencyCheckError(NarrativeError):
    """Error durante la verificación de consistencia."""

    original_error: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    user_message: str | None = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Consistency check error: {self.original_error}"
        if not self.user_message:
            self.user_message = (
                "Error al verificar consistencia. Se continuará con los resultados parciales."
            )
        super().__post_init__()


# =============================================================================
# Diccionarios de antónimos y relaciones
# =============================================================================

# =============================================================================
# Lematización (normalización morfológica)
# =============================================================================

# Fallback manual para cuando spaCy no está disponible
# Solo los casos más comunes - spaCy es preferible
_FALLBACK_LEMMAS: dict[str, str] = {
    # Build - femeninos y plurales comunes
    "alta": "alto",
    "altas": "alto",
    "altos": "alto",
    "baja": "bajo",
    "bajas": "bajo",
    "bajos": "bajo",
    "bajita": "bajito",
    "bajitas": "bajito",
    "bajitos": "bajito",
    # Colores - plurales
    "verdes": "verde",
    "azules": "azul",
    "marrones": "marrón",
    "negros": "negro",
    "negras": "negro",
    # Personalidad
    "valientes": "valiente",
    "cobardes": "cobarde",
}

# Cache de lemas para evitar recalcular
_lemma_cache: dict[str, str] = {}
_spacy_nlp = None
_spacy_checked = False


def _get_spacy_for_lemmas():
    """Obtiene modelo spaCy para lematización (lazy loading)."""
    global _spacy_nlp, _spacy_checked
    if not _spacy_checked:
        _spacy_checked = True
        try:
            from ..nlp.spacy_gpu import load_spacy_model

            _spacy_nlp = load_spacy_model()
            logger.debug("spaCy cargado para lematización")
        except Exception as e:
            logger.debug(f"spaCy no disponible para lematización: {e}")
    return _spacy_nlp


# Regiones corporales para sub-matching de DISTINCTIVE_FEATURE.
# Solo se comparan rasgos de la misma región (nariz vs nariz, no nariz vs cicatriz).
_BODY_REGION_PREFIXES: dict[str, str] = {}
for _region, _keywords in {
    "nariz": ("nariz", "narigudo", "nariguda"),
    "labios": ("labio", "labios"),
    "frente": ("frente",),
    "menton": ("mentón", "menton", "barbilla"),
    "mejillas": ("mejilla", "mejillas"),
    "orejas": ("oreja", "orejas", "orejudo", "orejuda"),
    "manos": ("mano", "manos"),
    "cicatriz": ("cicatriz", "cicatrices"),
    "lunar": ("lunar", "lunares"),
    "tatuaje": ("tatuaje", "tatuajes"),
    "pecas": ("peca", "pecas", "pecoso", "pecosa"),
    "marca": ("marca", "mancha"),
    "rostro": ("rostro", "cara"),
    "cojera": ("cojera", "cojo", "coja", "patizambo", "patizamba"),
    "ojos": ("bizco", "bizca"),
    "dientes": ("desdentado", "desdentada"),
}.items():
    for _kw in _keywords:
        _BODY_REGION_PREFIXES[_kw] = _region


# Dimensiones de vello facial — solo valores de la misma dimensión son comparables
_FACIAL_HAIR_DIMENSIONS: dict[str, str] = {
    # Densidad / grosor
    "espeso": "density",
    "espesa": "density",
    "poblado": "density",
    "poblada": "density",
    "tupido": "density",
    "tupida": "density",
    "cerrado": "density",
    "cerrada": "density",
    "fino": "density",
    "fina": "density",
    "ralo": "density",
    "rala": "density",
    "escaso": "density",
    "escasa": "density",
    "incipiente": "density",
    # Color
    "canoso": "color",
    "canosa": "color",
    "cana": "color",
    "canas": "color",
    "gris": "color",
    "entrecano": "color",
    "entrecana": "color",
    "negro": "color",
    "negra": "color",
    "oscuro": "color",
    "oscura": "color",
    "rojizo": "color",
    "rojiza": "color",
    "rubio": "color",
    "rubia": "color",
    "blanco": "color",
    "blanca": "color",
    # Longitud
    "largo": "length",
    "larga": "length",
    "corto": "length",
    "corta": "length",
    "recortado": "length",
    "recortada": "length",
    # Estilo / cuidado
    "cuidado": "style",
    "cuidada": "style",
    "descuidado": "style",
    "descuidada": "style",
}


def _same_facial_hair_dimension(value1: str, value2: str) -> bool:
    """
    Determina si dos valores de vello facial pertenecen a la misma dimensión.

    Solo valores de la misma dimensión son comparables:
    - "espesa" vs "rala" → True (ambas densidad)
    - "espesa" vs "canas" → False (densidad vs color)
    """
    v1 = _normalize_value(value1)
    v2 = _normalize_value(value2)

    dim1 = _FACIAL_HAIR_DIMENSIONS.get(v1)
    dim2 = _FACIAL_HAIR_DIMENSIONS.get(v2)

    # Si alguno no tiene dimensión conocida, asumir comparable (fallback conservador)
    if dim1 is None or dim2 is None:
        return True

    return dim1 == dim2


def _same_body_region(value1: str, value2: str) -> bool:
    """
    Determina si dos rasgos distintivos pertenecen a la misma región corporal.

    Solo rasgos del mismo tipo deben compararse como posibles inconsistencias.
    Ej: "nariz aguileña" vs "nariz chata" → True (misma región)
        "nariz aguileña" vs "cicatriz en mejilla" → False (regiones diferentes)
    """
    v1 = value1.lower().strip()
    v2 = value2.lower().strip()

    region1 = None
    region2 = None

    for keyword, region in _BODY_REGION_PREFIXES.items():
        if keyword in v1:
            region1 = region
            break
    for keyword, region in _BODY_REGION_PREFIXES.items():
        if keyword in v2:
            region2 = region
            break

    # Si alguno no tiene región reconocida, no comparar (no sabemos si es el mismo tipo)
    if region1 is None or region2 is None:
        return False

    return region1 == region2


def _extract_descriptor(value: str) -> str | None:
    """
    Extrae el descriptor (adjetivo) de un rasgo distintivo.

    "nariz aguileña" → "aguileña"
    "labios gruesos" → "gruesos"
    "cicatriz" → None (sin descriptor)
    """
    v = value.lower().strip()
    for keyword in _BODY_REGION_PREFIXES:
        if v.startswith(keyword):
            rest = v[len(keyword) :].strip()
            return rest if rest else None
        # Handle "labios gruesos" where keyword is "labio" (singular)
        # and value starts with "labios" (plural)
        if keyword.endswith("o") and v.startswith(keyword + "s"):
            rest = v[len(keyword) + 1 :].strip()
            return rest if rest else None
    return None


def _normalize_value(value: str) -> str:
    """
    Normaliza un valor a su lema (forma canónica).

    Usa spaCy para lematización morfológica si está disponible.
    Fallback a diccionario manual si no.

    Args:
        value: Valor a normalizar (ej: "verdes", "alta")

    Returns:
        Lema normalizado (ej: "verde", "alto")
    """
    v = value.lower().strip()

    # Check cache first
    if v in _lemma_cache:
        return _lemma_cache[v]

    # Try spaCy lemmatization
    nlp = _get_spacy_for_lemmas()
    if nlp:
        try:
            doc = nlp(v)
            if doc and len(doc) > 0:
                if len(doc) == 1:
                    lemma = str(doc[0].lemma_).lower()
                else:
                    # Multi-word: lematizar todos los tokens
                    lemma = " ".join(str(token.lemma_).lower() for token in doc)
                _lemma_cache[v] = lemma
                return lemma
        except Exception as e:
            logger.debug(f"Error en lematización spaCy: {e}")

    # Fallback to manual dictionary
    lemma = _FALLBACK_LEMMAS.get(v, v)
    _lemma_cache[v] = lemma
    return lemma


def reset_lemma_cache() -> None:
    """Resetea el cache de lemas y estado de spaCy (útil para tests)."""
    global _lemma_cache, _spacy_nlp, _spacy_checked
    _lemma_cache = {}
    _spacy_nlp = None
    _spacy_checked = False


# =============================================================================
# Atributos temporales (pueden cambiar sin ser inconsistencia)
# =============================================================================


def is_temporal_attribute(attr_key: AttributeKey, value: str) -> bool:
    """
    Determina si un atributo representa algo que puede cambiar
    legítimamente en una narrativa (peinados, ropa, etc.).

    Usa análisis semántico en lugar de listas fijas para escalar mejor.

    Args:
        attr_key: Tipo de atributo
        value: Valor del atributo

    Returns:
        True si es un atributo temporal que puede cambiar
    """
    value_lower = value.lower().strip()

    # HAIR_TYPE: distinguir textura natural vs estilo temporal
    if attr_key == AttributeKey.HAIR_TYPE:
        # Texturas naturales (inconsistencias válidas)
        natural_textures = {"liso", "rizado", "ondulado", "encrespado", "lacio"}
        # Si menciona longitud (largo/corto) también es más permanente
        if value_lower in natural_textures:
            return False
        if "largo" in value_lower or "corto" in value_lower:
            return False

        # Todo lo demás son peinados temporales
        # (trenza, coleta, recogido, suelto, moño, etc.)
        return True

    # HAIR_MODIFICATION: teñido puede cambiar libremente EXCEPTO a "natural"
    # Consenso: teñido/decolorado/mechas son cambios válidos dentro de historia
    # Solo es inconsistencia si dice que volvió a ser "natural" sin explicación
    if attr_key == AttributeKey.HAIR_MODIFICATION:
        # Si es "natural", es permanente (no debería cambiar a natural sin explicación)
        if "natural" in value_lower:
            return False
        # teñido, decolorado, mechas, etc. son temporales (pueden cambiar)
        return True

    # Atributos que son inherentemente permanentes
    permanent_keys = {
        AttributeKey.EYE_COLOR,  # Color de ojos no cambia (excepto lentillas)
        AttributeKey.HAIR_COLOR,  # El color natural es relevante
        AttributeKey.HEIGHT,  # La altura no cambia
        AttributeKey.BUILD,  # La constitución puede cambiar pero lentamente
        AttributeKey.AGE,  # La edad es permanente en un momento dado
        AttributeKey.APPARENT_AGE,  # La apariencia de edad no cambia en una narración
        AttributeKey.SKIN,  # Color de piel
        AttributeKey.DISTINCTIVE_FEATURE,  # Cicatrices, tatuajes, lunares
        AttributeKey.FACIAL_HAIR,  # Tipo/estilo de barba es bastante estable
    }

    if attr_key in permanent_keys:
        return False

    # Por defecto, asumir que puede ser temporal para evitar falsos positivos
    return False


# =============================================================================
# Diccionarios de sinónimos (para evitar falsos positivos)
# =============================================================================

# Sinónimos de colores (pueden coexistir o referirse a lo mismo)
COLOR_SYNONYMS: dict[str, set[str]] = {
    "castaño": {"marrón", "pardo", "chocolate"},
    "marrón": {"castaño", "pardo", "chocolate"},
    "negro": {"azabache", "oscuro", "moreno"},
    "blanco": {"cano", "cana", "canas", "canoso", "plateado", "gris"},
    "canoso": {"cano", "cana", "canas", "blanco", "plateado", "gris"},
    "cana": {"canoso", "cano", "canas", "blanco", "plateado", "gris", "entrecano"},
    "canas": {"canoso", "cano", "cana", "blanco", "plateado", "gris", "entrecano"},
    "rubio": {"dorado", "pajizo", "claro"},
    "rojo": {"pelirrojo", "cobrizo", "bermejo"},
    "pelirrojo": {"rojo", "cobrizo", "bermejo"},
    "gris": {"plateado", "ceniza", "canoso"},
    "miel": {"ámbar", "dorado", "avellana"},
    "ámbar": {"miel", "dorado", "avellana"},
    "avellana": {"miel", "ámbar", "castaño"},
}

# Sinónimos de constitución física
BUILD_SYNONYMS: dict[str, set[str]] = {
    "alto": {"grande", "esbelto", "larguirucho"},
    "bajo": {"pequeño", "bajito", "menudo", "chico"},
    "bajito": {"bajo", "pequeño", "menudo"},
    "delgado": {"flaco", "esbelto", "fino", "delgadísimo"},
    "flaco": {"delgado", "esbelto", "escuálido", "enjuto"},
    "gordo": {"obeso", "rollizo", "corpulento", "rechoncho", "gordito"},
    "corpulento": {"fornido", "robusto", "grande", "fuerte"},
    "robusto": {"corpulento", "fornido", "fuerte", "atlético"},
    "fornido": {"corpulento", "robusto", "fuerte", "musculoso"},
    "musculoso": {"atlético", "fornido", "fuerte"},
    "esbelto": {"delgado", "alto", "estilizado"},
}

# Sinónimos de personalidad
PERSONALITY_SYNONYMS: dict[str, set[str]] = {
    "valiente": {"audaz", "intrépido", "osado", "bravo"},
    "cobarde": {"miedoso", "temeroso", "pusilánime"},
    "amable": {"bondadoso", "afable", "simpático", "cordial"},
    "cruel": {"despiadado", "malvado", "sádico"},
    "honesto": {"sincero", "veraz", "íntegro", "recto"},
    "mentiroso": {"embustero", "falso", "tramposo"},
    "generoso": {"dadivoso", "espléndido", "altruista"},
    "tacaño": {"avaro", "mezquino", "cicatero"},
    "paciente": {"calmado", "sereno", "tranquilo"},
    "impaciente": {"nervioso", "inquieto", "ansioso"},
    "tímido": {"introvertido", "reservado", "retraído"},
    "extrovertido": {"sociable", "abierto", "comunicativo"},
    "sabio": {"inteligente", "prudente", "sensato"},
    "ingenuo": {"inocente", "cándido", "crédulo"},
    "astuto": {"sagaz", "perspicaz", "listo", "avispado"},
    "orgulloso": {"altivo", "soberbio", "arrogante"},
    "humilde": {"modesto", "sencillo", "llano"},
}

# Sinónimos de vello facial
# Incluye lemas masculinos (normalización spaCy: espesa→espeso) y femeninos
FACIAL_HAIR_SYNONYMS: dict[str, set[str]] = {
    "espeso": {"poblado", "tupido", "cerrado", "espesa", "poblada", "tupida"},
    "espesa": {"poblada", "tupida", "cerrada", "espeso", "poblado", "tupido"},
    "poblado": {"espeso", "tupido", "cerrado", "poblada", "espesa"},
    "poblada": {"espesa", "tupida", "cerrada", "poblado", "espeso"},
    "tupido": {"espeso", "poblado", "cerrado", "tupida", "espesa"},
    "tupida": {"espesa", "poblada", "cerrada", "tupido", "espeso"},
    "cerrado": {"espeso", "poblado", "tupido", "cerrada"},
    "cerrada": {"espesa", "poblada", "tupida", "cerrado"},
    "fino": {"ralo", "escaso", "fina", "rala"},
    "fina": {"rala", "escasa", "fino", "ralo"},
    "ralo": {"fino", "escaso", "rala", "fina"},
    "rala": {"fina", "escasa", "ralo", "fino"},
    "canoso": {"gris", "blanco", "entrecano", "canosa", "cana", "canas"},
    "canosa": {"gris", "blanca", "entrecana", "canoso", "cana", "canas"},
    "cana": {"canoso", "canosa", "gris", "entrecano", "entrecana", "canas"},
    "canas": {"canoso", "canosa", "gris", "entrecano", "entrecana", "cana"},
    "gris": {"canoso", "canosa", "entrecano", "entrecana", "cana", "canas"},
    "entrecano": {"canoso", "gris", "entrecana", "cana", "canas"},
    "entrecana": {"canosa", "gris", "entrecano", "cana", "canas"},
    "recortado": {"cuidado", "corto", "recortada"},
    "recortada": {"cuidada", "corta", "recortado"},
    "cuidado": {"recortado", "cuidada"},
    "cuidada": {"recortada", "cuidado"},
    "negro": {"oscuro", "negra"},
    "negra": {"oscura", "negro"},
    "oscuro": {"negro", "oscura"},
    "oscura": {"negra", "oscuro"},
    "rojizo": {"rojiza"},
    "rojiza": {"rojizo"},
}

# Combinación de sinónimos por tipo de atributo
SYNONYMS_BY_KEY: dict[AttributeKey, dict[str, set[str]]] = {
    AttributeKey.EYE_COLOR: COLOR_SYNONYMS,
    AttributeKey.HAIR_COLOR: COLOR_SYNONYMS,
    AttributeKey.BUILD: BUILD_SYNONYMS,
    AttributeKey.HEIGHT: BUILD_SYNONYMS,
    AttributeKey.PERSONALITY: PERSONALITY_SYNONYMS,
    AttributeKey.TEMPERAMENT: PERSONALITY_SYNONYMS,
    AttributeKey.FACIAL_HAIR: FACIAL_HAIR_SYNONYMS,
}


def _are_synonyms(v1: str, v2: str, attr_key: AttributeKey) -> bool:
    """Verifica si dos valores son sinónimos."""
    if attr_key not in SYNONYMS_BY_KEY:
        return False
    synonyms = SYNONYMS_BY_KEY[attr_key]
    # Check both directions
    if v1 in synonyms and v2 in synonyms.get(v1, set()):
        return True
    return bool(v2 in synonyms and v1 in synonyms.get(v2, set()))


# =============================================================================
# Diccionarios de antónimos (para detectar contradicciones)
# =============================================================================

# Antónimos para colores (no se pueden tener dos a la vez)
COLOR_ANTONYMS: dict[str, set[str]] = {
    "verde": {"azul", "marrón", "negro", "gris", "castaño", "miel", "ámbar"},
    "azul": {"verde", "marrón", "negro", "castaño", "miel", "ámbar"},
    "marrón": {"verde", "azul", "gris", "negro"},
    "castaño": {"verde", "azul", "rubio", "negro", "pelirrojo"},
    "negro": {
        "verde",
        "azul",
        "rubio",
        "castaño",
        "pelirrojo",
        "canoso",
        "cana",
        "canas",
        "blanco",
    },
    "rubio": {"negro", "castaño", "moreno", "pelirrojo"},
    "pelirrojo": {"negro", "rubio", "castaño", "moreno", "canoso", "cana", "canas"},
    "canoso": {"negro", "rubio", "castaño", "pelirrojo"},
    "cana": {"negro", "rubio", "castaño", "pelirrojo"},
    "canas": {"negro", "rubio", "castaño", "pelirrojo"},
    "blanco": {"negro", "castaño", "rubio"},
    "gris": {"verde", "azul", "marrón"},
    "miel": {"verde", "azul", "negro"},
    "ámbar": {"verde", "azul", "negro"},
}

# Antónimos para constitución física
BUILD_ANTONYMS: dict[str, set[str]] = {
    "alto": {"bajo", "bajito", "pequeño"},
    "bajo": {"alto", "altísimo"},
    "bajito": {"alto", "altísimo"},
    "delgado": {"gordo", "corpulento", "obeso", "robusto", "fornido"},
    "gordo": {"delgado", "flaco", "esbelto", "delgadísimo"},
    "flaco": {"gordo", "corpulento", "robusto", "fornido"},
    "corpulento": {"delgado", "flaco", "esbelto", "enclenque"},
    "esbelto": {"gordo", "corpulento", "rechoncho"},
    "musculoso": {"enclenque", "débil", "escuálido"},
    "enclenque": {"musculoso", "fornido", "robusto"},
    "robusto": {"enclenque", "débil", "flaco", "delgado"},
    "fornido": {"enclenque", "débil", "flaco", "delgado"},
}

# Antónimos para tipo de pelo (largo/corto, liso/rizado)
HAIR_TYPE_ANTONYMS: dict[str, set[str]] = {
    "largo": {"corto", "rapado"},
    "corto": {"largo"},
    "liso": {"rizado", "ondulado", "encrespado"},
    "rizado": {"liso", "lacio"},
    "ondulado": {"liso", "lacio"},
    "encrespado": {"liso", "lacio"},
    "lacio": {"rizado", "ondulado", "encrespado"},
    "rapado": {"largo"},
    "recogido": {"suelto"},
    "suelto": {"recogido", "trenzado"},
    "trenzado": {"suelto"},
}

# Antónimos para personalidad
PERSONALITY_ANTONYMS: dict[str, set[str]] = {
    "amable": {"cruel", "desagradable", "hostil", "grosero"},
    "cruel": {"amable", "bondadoso", "compasivo"},
    "valiente": {"cobarde", "miedoso", "temeroso"},
    "cobarde": {"valiente", "audaz", "intrépido"},
    "honesto": {"mentiroso", "deshonesto", "tramposo"},
    "mentiroso": {"honesto", "sincero", "veraz"},
    "generoso": {"tacaño", "avaro", "mezquino"},
    "tacaño": {"generoso", "espléndido", "dadivoso"},
    "paciente": {"impaciente", "nervioso", "inquieto"},
    "impaciente": {"paciente", "calmado", "sereno"},
    "tímido": {"extrovertido", "desinhibido", "sociable"},
    "extrovertido": {"tímido", "introvertido", "reservado"},
    "sabio": {"ignorante", "necio", "tonto"},
    "ingenuo": {"astuto", "sagaz", "perspicaz"},
    "astuto": {"ingenuo", "inocente", "cándido"},
    "orgulloso": {"humilde", "modesto"},
    "humilde": {"orgulloso", "arrogante", "soberbio"},
    "arrogante": {"humilde", "modesto", "sencillo"},
}

# Antónimos para ubicación/posición (un personaje no puede estar en dos lugares a la vez)
# Estos son lugares que son mutuamente excluyentes dentro de un mismo capítulo/escena
LOCATION_ANTONYMS: dict[str, set[str]] = {
    # Interior vs exterior
    "dentro": {"fuera", "afuera", "exterior"},
    "fuera": {"dentro", "interior", "adentro"},
    "interior": {"exterior", "afuera", "fuera"},
    "exterior": {"interior", "dentro", "adentro"},
    # Direcciones cardinales
    "norte": {"sur"},
    "sur": {"norte"},
    "este": {"oeste"},
    "oeste": {"este"},
    # Arriba vs abajo
    "arriba": {"abajo"},
    "abajo": {"arriba"},
    "sótano": {"ático", "azotea", "tejado"},
    "ático": {"sótano", "planta baja"},
    "azotea": {"sótano", "planta baja"},
    # Ciudades/países conocidos que son mutuamente excluyentes
    "madrid": {"barcelona", "sevilla", "valencia", "bilbao", "londres", "parís", "roma"},
    "barcelona": {"madrid", "sevilla", "valencia", "bilbao", "londres", "parís", "roma"},
    "londres": {"madrid", "barcelona", "parís", "roma", "nueva york", "berlín"},
    "parís": {"madrid", "barcelona", "londres", "roma", "nueva york", "berlín"},
    "roma": {"madrid", "barcelona", "londres", "parís", "nueva york", "berlín"},
}

# Antónimos de vello facial
# Incluye lemas masculinos (normalización spaCy) y femeninos
FACIAL_HAIR_ANTONYMS: dict[str, set[str]] = {
    "espeso": {"fino", "ralo", "escaso", "incipiente", "fina", "rala"},
    "espesa": {"fina", "rala", "escasa", "incipiente", "fino", "ralo"},
    "poblado": {"fino", "ralo", "escaso", "fina", "rala"},
    "poblada": {"fina", "rala", "escasa", "fino", "ralo"},
    "tupido": {"fino", "ralo", "escaso", "fina", "rala"},
    "tupida": {"fina", "rala", "escasa", "fino", "ralo"},
    "fino": {"espeso", "poblado", "tupido", "cerrado", "espesa", "poblada"},
    "fina": {"espesa", "poblada", "tupida", "cerrada", "espeso", "poblado"},
    "ralo": {"espeso", "poblado", "tupido", "cerrado", "espesa", "poblada"},
    "rala": {"espesa", "poblada", "tupida", "cerrada", "espeso", "poblado"},
    "largo": {"corto", "recortado", "corta", "recortada"},
    "larga": {"corta", "recortada", "corto", "recortado"},
    "corto": {"largo", "larga"},
    "corta": {"larga", "largo"},
    "recortado": {"largo", "descuidado", "larga", "descuidada"},
    "recortada": {"larga", "descuidada", "largo", "descuidado"},
    "cuidado": {"descuidado", "descuidada"},
    "cuidada": {"descuidada", "descuidado"},
    "descuidado": {"cuidado", "recortado", "cuidada", "recortada"},
    "descuidada": {"cuidada", "recortada", "cuidado", "recortado"},
    "canoso": {"negro", "oscuro", "rojizo", "rubio", "negra", "oscura"},
    "canosa": {"negra", "oscura", "rojiza", "rubia", "negro", "oscuro"},
    "cana": {"negro", "oscuro", "rojizo", "rubio", "negra", "oscura"},
    "canas": {"negro", "oscuro", "rojizo", "rubio", "negra", "oscura"},
    "negro": {"canoso", "rubio", "rojizo", "blanco", "canosa", "rubia", "cana", "canas"},
    "negra": {"canosa", "rubia", "rojiza", "blanca", "canoso", "rubio", "cana", "canas"},
    "rubio": {"negro", "oscuro", "canoso", "negra", "cana", "canas"},
    "rubia": {"negra", "oscura", "canosa", "negro", "cana", "canas"},
    "rojizo": {"negro", "canoso", "rubio", "negra", "cana", "canas"},
    "rojiza": {"negra", "canosa", "rubia", "negro", "cana", "canas"},
}

# Combinación de todos los antónimos por tipo de atributo
ANTONYMS_BY_KEY: dict[AttributeKey, dict[str, set[str]]] = {
    AttributeKey.EYE_COLOR: COLOR_ANTONYMS,
    AttributeKey.HAIR_COLOR: COLOR_ANTONYMS,
    AttributeKey.HAIR_TYPE: HAIR_TYPE_ANTONYMS,
    AttributeKey.BUILD: BUILD_ANTONYMS,
    AttributeKey.HEIGHT: BUILD_ANTONYMS,
    AttributeKey.PERSONALITY: PERSONALITY_ANTONYMS,
    AttributeKey.TEMPERAMENT: PERSONALITY_ANTONYMS,
    AttributeKey.LOCATION: LOCATION_ANTONYMS,
    AttributeKey.FACIAL_HAIR: FACIAL_HAIR_ANTONYMS,
}


class AttributeConsistencyChecker:
    """
    Verificador de consistencia de atributos.

    Detecta contradicciones en los atributos de entidades
    comparando valores extraídos de diferentes partes del texto.

    Attributes:
        use_embeddings: Usar embeddings para comparación semántica
        min_confidence: Confianza mínima para reportar inconsistencia
    """

    def __init__(
        self,
        use_embeddings: bool = True,
        min_confidence: float = 0.5,
    ):
        """
        Inicializa el verificador.

        Args:
            use_embeddings: Usar embeddings para similitud semántica
            min_confidence: Confianza mínima (0.0-1.0)
        """
        self.use_embeddings = use_embeddings
        self.min_confidence = min_confidence
        self._embeddings_model = None

    def _get_embeddings_model(self):
        """Obtiene el modelo de embeddings (lazy loading)."""
        if self._embeddings_model is None and self.use_embeddings:
            try:
                from ..nlp.embeddings import get_embeddings_model

                self._embeddings_model = get_embeddings_model()
            except Exception as e:
                logger.warning(f"No se pudo cargar modelo de embeddings: {e}")
                self._embeddings_model = False
        return self._embeddings_model if self._embeddings_model else None

    def _group_conflicting_values(
        self,
        attrs: list[ExtractedAttribute],
        attr_key: AttributeKey,
    ) -> list[list[ExtractedAttribute]]:
        """
        Agrupa atributos por valores equivalentes (después de normalización y sinónimos).

        Atributos con valores idénticos o sinónimos se agrupan juntos.
        Retorna lista de grupos, donde cada grupo representa un valor único.

        Args:
            attrs: Lista de atributos a agrupar
            attr_key: Clave del atributo

        Returns:
            Lista de grupos de atributos equivalentes
        """
        groups: list[list[ExtractedAttribute]] = []

        for attr in attrs:
            # Saltar atributos negados
            if attr.is_negated:
                continue

            # Saltar atributos temporales
            if is_temporal_attribute(attr_key, attr.value):
                continue

            # Normalizar valor
            normalized = _normalize_value(attr.value)

            # Buscar grupo compatible (sinónimos o misma región corporal)
            found_group = False
            for group in groups:
                representative = group[0]
                rep_normalized = _normalize_value(representative.value)

                # Mismo valor normalizado
                if normalized == rep_normalized:
                    group.append(attr)
                    found_group = True
                    break

                # Sinónimos
                if _are_synonyms(normalized, rep_normalized, attr_key):
                    group.append(attr)
                    found_group = True
                    break

                # DISTINCTIVE_FEATURE: diferentes regiones corporales → grupos separados
                if attr_key == AttributeKey.DISTINCTIVE_FEATURE:
                    if not _same_body_region(attr.value, representative.value):
                        continue  # No agrupar, son regiones diferentes

                # FACIAL_HAIR: diferentes dimensiones → grupos separados
                if attr_key == AttributeKey.FACIAL_HAIR:
                    if not _same_facial_hair_dimension(normalized, rep_normalized):
                        continue

            # Si no encontró grupo compatible, crear uno nuevo
            if not found_group:
                groups.append([attr])

        return groups

    def _generate_multi_value_explanation(
        self,
        attr_key: AttributeKey,
        conflicting_values: list[ConflictingValue],
        inc_type: InconsistencyType,
        confidence: float,
    ) -> str:
        """
        Genera explicación para inconsistencias multi-valor.

        Args:
            attr_key: Clave del atributo
            conflicting_values: Lista de valores conflictivos
            inc_type: Tipo de inconsistencia
            confidence: Confianza de la inconsistencia

        Returns:
            Explicación legible
        """
        if len(conflicting_values) < 2:
            return "Inconsistencia detectada"

        key_name = get_attribute_display_name(attr_key)
        gender = get_attribute_gender(attr_key)
        # entity = conflicting_values[0].value  # Usamos el primer valor para referencia

        # Construir lista de valores con ubicaciones
        values_list = []
        for cv in conflicting_values:
            loc = f"cap. {cv.chapter}" if cv.chapter else "texto"
            values_list.append(f"'{cv.value}' ({loc})")

        values_str = ", ".join(values_list[:-1]) + f" y {values_list[-1]}"

        # Adjetivos con concordancia de género
        adj_contradictorio = "contradictorias" if gender == "f" else "contradictorios"
        adj_diferente = "diferentes"

        if inc_type == InconsistencyType.ANTONYM:
            return (
                f"Se encontraron {len(conflicting_values)} descripciones de {key_name} {adj_contradictorio}: "
                f"{values_str}. Son valores opuestos."
            )

        if inc_type == InconsistencyType.CONTRADICTORY:
            return (
                f"Se encontraron {len(conflicting_values)} descripciones de {key_name} muy {adj_diferente}: "
                f"{values_str}. Posible error de continuidad."
            )

        return (
            f"Se encontraron {len(conflicting_values)} descripciones de {key_name} {adj_diferente}: "
            f"{values_str}. Verificar si es intencional."
        )

    def _build_entity_name_mapping(
        self,
        attributes: list[ExtractedAttribute],
    ) -> dict[str, str]:
        """
        Construye un mapeo de nombres de entidades para normalizar variantes.

        "María Sánchez" y "María" se mapean a "maría sánchez" (nombre completo)
        "Juan Pérez" y "Juan" se mapean a "juan pérez" (nombre completo)

        IMPORTANTE: Solo agrupa nombres cuando hay evidencia clara de que son la misma
        entidad (uno es prefijo del otro Y ambos aparecen en el mismo contexto).
        """
        # Extraer todos los nombres únicos
        all_names = {attr.entity_name.lower() for attr in attributes}

        # Crear mapeo - cada nombre se mapea a sí mismo por defecto
        mapping: dict[str, str] = {name: name for name in all_names}

        # Lista de nombres ordenados por longitud (más largos primero)
        # Preferimos el nombre más completo como base
        sorted_names = sorted(all_names, key=len, reverse=True)

        # Agrupar solo nombres que claramente son la misma entidad
        processed = set()
        for full_name in sorted_names:
            if full_name in processed:
                continue

            # Buscar nombres más cortos que sean prefijo de este
            first_word = full_name.split()[0]
            for other_name in sorted_names:
                if other_name == full_name or other_name in processed:
                    continue

                # Solo agrupar si other_name es exactamente el primer nombre
                # y full_name es nombre + apellido
                if other_name == first_word and len(full_name.split()) > 1:
                    # Verificar que no haya OTRO nombre completo que empiece con este primer nombre
                    # Ej: Si hay "Juan Pérez" y "Juan García", no agrupar "Juan" con ninguno
                    conflicting_names = [
                        n for n in all_names if n != full_name and n.startswith(first_word + " ")
                    ]

                    if not conflicting_names:
                        # Seguro de agrupar: solo hay una entidad con este primer nombre
                        mapping[other_name] = full_name
                        mapping[full_name] = full_name
                        processed.add(other_name)
                        logger.debug(f"Normalización: '{other_name}' -> '{full_name}'")
                    else:
                        # Hay conflicto: mantener separados para evitar confusión
                        logger.debug(
                            f"NO agrupando '{other_name}' - conflicto con: {conflicting_names}"
                        )

            processed.add(full_name)

        return mapping

    def _get_canonical_name(
        self,
        normalized_key: str,
        name1: str,
        name2: str,
    ) -> str:
        """
        Obtiene el nombre canónico para usar en la inconsistencia.

        Prefiere el nombre más largo (más específico) para que coincida
        con entity_map que usa nombres canónicos completos.

        Args:
            normalized_key: Clave normalizada usada para agrupar
            name1: Nombre de la primera entidad
            name2: Nombre de la segunda entidad

        Returns:
            Nombre canónico (el más largo/específico)
        """
        # Preferir el nombre más largo (más específico)
        if len(name1) > len(name2):
            return name1
        elif len(name2) > len(name1):
            return name2
        else:
            # Misma longitud, usar el primer nombre original (preserva casing)
            return name1

    def check_consistency(
        self,
        attributes: list[ExtractedAttribute],
    ) -> Result[list[AttributeInconsistency]]:
        """
        Verifica consistencia en una lista de atributos.

        Agrupa atributos por (entidad, clave) y busca valores
        contradictorios.

        Args:
            attributes: Lista de atributos extraídos

        Returns:
            Result con lista de inconsistencias detectadas
        """
        if not attributes:
            return Result.success([])

        inconsistencies: list[AttributeInconsistency] = []

        try:
            # Normalizar nombres de entidades para agrupar variantes
            # "María Sánchez" y "María" -> ambas agrupadas bajo "maría"
            # "Juan Pérez" y "Juan" -> ambas agrupadas bajo "juan"
            normalized_names = self._build_entity_name_mapping(attributes)

            # Agrupar por (entity_name_normalizado, attribute_key)
            grouped: dict[tuple[str, AttributeKey], list[ExtractedAttribute]] = {}

            for attr in attributes:
                # Usar nombre normalizado para agrupar
                entity_key = normalized_names.get(
                    attr.entity_name.lower(), attr.entity_name.lower()
                )
                key = (entity_key, attr.key)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(attr)

            logger.debug(
                f"Grouped {len(attributes)} attributes into {len(grouped)} entity-attribute pairs"
            )

            # Buscar inconsistencias en cada grupo
            for (entity_name, attr_key), attrs in grouped.items():
                if len(attrs) < 2:
                    continue

                logger.debug(
                    f"Checking {entity_name}.{attr_key.value}: {len(attrs)} values - {[a.value for a in attrs]}"
                )

                # Agrupar valores únicos (normalizados) para detectar conflictos multi-valor
                value_groups = self._group_conflicting_values(attrs, attr_key)

                # Si hay múltiples grupos de valores conflictivos, crear 1 alerta
                if len(value_groups) > 1:
                    # Calcular confianza y tipo basándose en el par más conflictivo
                    max_confidence = 0.0
                    dominant_type = InconsistencyType.VALUE_CHANGE

                    # Comparar todos los pares para encontrar la máxima confianza
                    for i, group1 in enumerate(value_groups):
                        for group2 in value_groups[i + 1 :]:
                            # Usar el primer atributo de cada grupo para comparación
                            attr1 = group1[0]
                            attr2 = group2[0]
                            confidence, inc_type = self._calculate_inconsistency(
                                attr1, attr2, attr_key
                            )
                            if confidence > max_confidence:
                                max_confidence = confidence
                                dominant_type = inc_type

                    if max_confidence >= self.min_confidence:
                        # Construir lista de valores conflictivos
                        conflicting_values = []
                        all_values_str = []
                        for group in value_groups:
                            # Usar el primer atributo de cada grupo (representante)
                            attr = group[0]
                            conflicting_values.append(
                                ConflictingValue(
                                    value=attr.value,
                                    chapter=attr.chapter_id,
                                    excerpt=attr.source_text,
                                    position=attr.start_char,
                                )
                            )
                            all_values_str.append(f"'{attr.value}'")

                        # Generar explicación multi-valor
                        explanation = self._generate_multi_value_explanation(
                            attr_key,
                            conflicting_values,
                            dominant_type,
                            max_confidence,
                        )

                        logger.info(
                            f"MULTI-VALUE INCONSISTENCY DETECTED: {entity_name}.{attr_key.value} "
                            f"{', '.join(all_values_str)} (confidence: {max_confidence:.2f})"
                        )

                        # Usar el nombre canónico
                        canonical_name = self._get_canonical_name(
                            entity_name, attrs[0].entity_name, attrs[0].entity_name
                        )

                        inconsistencies.append(
                            AttributeInconsistency(
                                entity_name=canonical_name,
                                entity_id=0,
                                attribute_key=attr_key,
                                conflicting_values=conflicting_values,
                                inconsistency_type=dominant_type,
                                confidence=max_confidence,
                                explanation=explanation,
                            )
                        )

            # Ordenar por confianza descendente
            inconsistencies.sort(key=lambda x: -x.confidence)

            logger.info(f"Inconsistencias detectadas: {len(inconsistencies)}")
            return Result.success(inconsistencies)

        except Exception as e:
            error = ConsistencyCheckError(original_error=str(e))
            logger.error(f"Error verificando consistencia: {e}")
            return Result.partial(inconsistencies, [error])

    def _calculate_inconsistency(
        self,
        attr1: ExtractedAttribute,
        attr2: ExtractedAttribute,
        attr_key: AttributeKey,
    ) -> tuple[float, InconsistencyType]:
        """
        Calcula la confianza de que haya una inconsistencia real.

        Returns:
            Tupla de (confianza, tipo_inconsistencia)
        """
        # Normalizar valores (lematización morfológica)
        v1 = _normalize_value(attr1.value)
        v2 = _normalize_value(attr2.value)

        # Valores idénticos después de normalización = no hay inconsistencia
        if v1 == v2:
            return 0.0, InconsistencyType.VALUE_CHANGE

        # 0. Verificar sinónimos conocidos (evitar falsos positivos)
        if _are_synonyms(v1, v2, attr_key):
            logger.debug(f"Sinónimos detectados: {v1} ~ {v2}")
            return 0.0, InconsistencyType.VALUE_CHANGE  # No es inconsistencia

        # 1. Verificar antónimos conocidos
        if attr_key in ANTONYMS_BY_KEY:
            antonyms = ANTONYMS_BY_KEY[attr_key]
            if v1 in antonyms and v2 in antonyms.get(v1, set()):
                return 0.95, InconsistencyType.ANTONYM
            if v2 in antonyms and v1 in antonyms.get(v2, set()):
                return 0.95, InconsistencyType.ANTONYM

        # 1b. Caso especial: DISTINCTIVE_FEATURE de la misma región corporal
        # "nariz aguileña" vs "nariz chata" → comparar solo descriptores
        if attr_key == AttributeKey.DISTINCTIVE_FEATURE and _same_body_region(v1, v2):
            # Extraer descriptores (parte después de la región corporal)
            desc1 = _extract_descriptor(v1)
            desc2 = _extract_descriptor(v2)
            if desc1 and desc2 and desc1 != desc2:
                # Descriptores diferentes para la misma parte del cuerpo = inconsistencia
                return 0.75, InconsistencyType.SEMANTIC_DIFF

        # 1c. Caso especial: FACIAL_HAIR — solo comparar misma dimensión
        # "espesa" (densidad) vs "canas" (color) NO son inconsistentes
        if attr_key == AttributeKey.FACIAL_HAIR:
            if not _same_facial_hair_dimension(v1, v2):
                logger.debug(f"Dimensiones distintas de vello facial: {v1} vs {v2} — no comparar")
                return 0.0, InconsistencyType.VALUE_CHANGE

        # 2. Caso especial: edad (real o aparente, valores numéricos o descriptivos)
        if attr_key in (AttributeKey.AGE, AttributeKey.APPARENT_AGE):
            return self._check_age_consistency(v1, v2)

        # 3. Similitud semántica con embeddings
        if self.use_embeddings:
            similarity = self._calculate_semantic_similarity(v1, v2)
            if similarity is not None:
                # Alta similitud = probablemente sinónimos (no inconsistencia)
                if similarity >= 0.7:
                    logger.debug(f"Alta similitud semántica: {v1} ~ {v2} ({similarity:.2f})")
                    return 0.1, InconsistencyType.VALUE_CHANGE
                # Media similitud = cambio menor
                elif similarity >= 0.5:
                    return 0.4, InconsistencyType.VALUE_CHANGE
                # Baja similitud = posible inconsistencia
                elif similarity >= 0.3:
                    return 0.6, InconsistencyType.SEMANTIC_DIFF
                # Muy baja similitud = probable inconsistencia
                else:
                    return 0.8, InconsistencyType.SEMANTIC_DIFF

        # 4. Fallback: valores diferentes = posible inconsistencia
        # Considerar longitud de valores y overlap de caracteres
        overlap = len(set(v1) & set(v2)) / max(len(set(v1)), len(set(v2)), 1)
        if overlap < 0.3:
            return 0.6, InconsistencyType.VALUE_CHANGE

        return 0.4, InconsistencyType.VALUE_CHANGE

    # Rangos aproximados para descriptores de edad
    _AGE_RANGES: dict[str, tuple[int, int]] = {
        "niño": (0, 12),
        "niña": (0, 12),
        "adolescente": (13, 17),
        "joven": (15, 30),
        "veinteañero": (20, 29),
        "veinteañera": (20, 29),
        "treintañero": (30, 39),
        "treintañera": (30, 39),
        "cuarentón": (40, 49),
        "cuarentona": (40, 49),
        "cincuentón": (50, 59),
        "cincuentona": (50, 59),
        "de mediana edad": (40, 55),
        "maduro": (40, 60),
        "madura": (40, 60),
        "mayor": (55, 80),
        "sexagenario": (60, 69),
        "sexagenaria": (60, 69),
        "septuagenario": (70, 79),
        "septuagenaria": (70, 79),
        "octogenario": (80, 89),
        "octogenaria": (80, 89),
        "nonagenario": (90, 99),
        "nonagenaria": (90, 99),
        "viejo": (60, 99),
        "vieja": (60, 99),
        "anciano": (65, 99),
        "anciana": (65, 99),
    }

    def _age_to_range(self, value: str) -> tuple[int, int] | None:
        """Convierte un valor de edad a rango numérico."""
        try:
            n = int(value)
            return (n, n)
        except ValueError:
            return self._AGE_RANGES.get(value.lower())

    def _check_age_consistency(
        self,
        v1: str,
        v2: str,
    ) -> tuple[float, InconsistencyType]:
        """Verifica consistencia de edades numéricas o descriptivas."""
        r1 = self._age_to_range(v1)
        r2 = self._age_to_range(v2)

        if r1 is None or r2 is None:
            # At least one value isn't recognized — soft comparison
            return 0.5, InconsistencyType.VALUE_CHANGE

        # Check if ranges overlap
        overlap_start = max(r1[0], r2[0])
        overlap_end = min(r1[1], r2[1])

        if overlap_start <= overlap_end:
            # Ranges overlap — compatible
            # Calculate how much they overlap vs total span
            overlap_size = overlap_end - overlap_start
            total_span = max(r1[1], r2[1]) - min(r1[0], r2[0])
            overlap_ratio = overlap_size / max(total_span, 1)
            if overlap_ratio > 0.5:
                return 0.1, InconsistencyType.VALUE_CHANGE  # Very compatible
            return 0.3, InconsistencyType.VALUE_CHANGE  # Some overlap

        # No overlap — gap between ranges
        gap = overlap_start - overlap_end
        if gap <= 5:
            return 0.6, InconsistencyType.VALUE_CHANGE  # Close but non-overlapping
        return 0.9, InconsistencyType.CONTRADICTORY  # Clearly contradictory

    def _calculate_semantic_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float | None:
        """
        Calcula similitud semántica usando embeddings.

        Returns:
            Similitud coseno (0.0-1.0) o None si no disponible
        """
        model = self._get_embeddings_model()
        if not model:
            return None

        try:
            embeddings = model.encode([text1, text2])

            # Similitud coseno
            import numpy as np

            dot_product = np.dot(embeddings[0], embeddings[1])
            norm1 = np.linalg.norm(embeddings[0])
            norm2 = np.linalg.norm(embeddings[1])

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        except Exception as e:
            logger.warning(f"Error calculando similitud semántica: {e}")
            return None

    def _generate_explanation(
        self,
        attr_key: AttributeKey,
        attr1: ExtractedAttribute,
        attr2: ExtractedAttribute,
        inc_type: InconsistencyType,
        confidence: float,
    ) -> str:
        """Genera una explicación legible de la inconsistencia."""
        key_name = get_attribute_display_name(attr_key)
        gender = get_attribute_gender(attr_key)
        entity = attr1.entity_name

        # Adjetivos con concordancia de género
        # Usamos plural porque hablamos de "valores" o "descripciones"
        adj_contradictorio = "contradictorias" if gender == "f" else "contradictorios"
        adj_diferente = "diferentes"
        adj_opuesto = "opuestas" if gender == "f" else "opuestos"

        # Ubicación
        loc1 = f"cap. {attr1.chapter_id}" if attr1.chapter_id else "texto"
        loc2 = f"cap. {attr2.chapter_id}" if attr2.chapter_id else "texto"

        if inc_type == InconsistencyType.ANTONYM:
            return (
                f"'{entity}' tiene descripciones de {key_name} {adj_contradictorio}: "
                f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
                f"Son valores {adj_opuesto}."
            )

        if inc_type == InconsistencyType.CONTRADICTORY:
            return (
                f"'{entity}' tiene descripciones de {key_name} muy {adj_diferente}: "
                f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
                f"Posible error de continuidad."
            )

        return (
            f"'{entity}' tiene descripciones de {key_name} {adj_diferente}: "
            f"'{attr1.value}' ({loc1}) vs '{attr2.value}' ({loc2}). "
            f"Verificar si es intencional."
        )

    def check_entity_attributes(
        self,
        entity_name: str,
        attributes: list[ExtractedAttribute],
    ) -> list[AttributeInconsistency]:
        """
        Verifica consistencia de atributos de una entidad específica.

        Args:
            entity_name: Nombre de la entidad
            attributes: Atributos de esa entidad

        Returns:
            Lista de inconsistencias encontradas
        """
        # Filtrar atributos de la entidad
        entity_attrs = [a for a in attributes if a.entity_name.lower() == entity_name.lower()]

        result = self.check_consistency(entity_attrs)
        if result.is_success and result.value is not None:
            return result.value
        return []


# =============================================================================
# Funciones de conveniencia
# =============================================================================


def check_attribute_consistency(
    attributes: list[ExtractedAttribute],
) -> Result[list[AttributeInconsistency]]:
    """
    Función de conveniencia para verificar consistencia.

    Args:
        attributes: Lista de atributos extraídos

    Returns:
        Result con lista de inconsistencias
    """
    checker = get_consistency_checker()
    return checker.check_consistency(attributes)


# =============================================================================
# Singleton thread-safe
# =============================================================================

_checker_lock = threading.Lock()
_consistency_checker: AttributeConsistencyChecker | None = None


def get_consistency_checker(
    use_embeddings: bool = True,
    min_confidence: float = 0.5,
) -> AttributeConsistencyChecker:
    """
    Obtiene el singleton del verificador de consistencia.

    Args:
        use_embeddings: Usar embeddings para comparación
        min_confidence: Confianza mínima

    Returns:
        Instancia única del AttributeConsistencyChecker
    """
    global _consistency_checker

    if _consistency_checker is None:
        with _checker_lock:
            if _consistency_checker is None:
                _consistency_checker = AttributeConsistencyChecker(
                    use_embeddings=use_embeddings,
                    min_confidence=min_confidence,
                )

    return _consistency_checker


def reset_consistency_checker() -> None:
    """Resetea el singleton (útil para tests)."""
    global _consistency_checker
    with _checker_lock:
        _consistency_checker = None
