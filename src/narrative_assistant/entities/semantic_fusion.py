"""
Fusión semántica de entidades usando embeddings y LLMs locales (Ollama).

Este módulo complementa fusion.py con capacidades de IA para:
1. Calcular similaridad semántica usando embeddings (sentence-transformers)
2. Resolver correferencia nominal compleja ("El parque" → "Parque del Retiro")
3. Normalización ortográfica para comparación flexible

NOTA: Todo el procesamiento es LOCAL - no se usan servicios externos de pago.
Los LLMs se ejecutan via Ollama (llama3.2, mistral, qwen2.5).
"""

import logging
import unicodedata
from dataclasses import dataclass

from ..core.config import get_config
from ..nlp.embeddings import get_embeddings_model
from .models import Entity, EntityType

logger = logging.getLogger(__name__)

# Umbral de similaridad semántica para sugerir fusión (valor por defecto)
# NOTA: Este valor se puede configurar desde Settings -> NLP -> semantic_fusion_threshold
# IMPORTANTE: 0.65 es demasiado bajo para embeddings multilingual - genera falsos positivos
# Usar 0.82+ para evitar fusiones absurdas como "La alta sensibilidad" + "Créeme"
SEMANTIC_SIMILARITY_THRESHOLD = 0.82


def _get_fusion_threshold() -> float:
    """Obtiene el umbral de fusión desde la configuración global."""
    try:
        config = get_config()
        return config.nlp.semantic_fusion_threshold
    except Exception:
        return SEMANTIC_SIMILARITY_THRESHOLD


# Contextos que indican referencia anafórica
ANAPHORIC_MARKERS = [
    "el ",
    "la ",
    "los ",
    "las ",  # Artículos definidos
    "ese ",
    "esa ",
    "esos ",
    "esas ",  # Demostrativos
    "aquel ",
    "aquella ",
    "dicho ",
    "dicha ",  # Referencias
    "mismo ",
    "misma ",  # Identidad
]

# =============================================================================
# Normalización de nombres de entidades
# =============================================================================

# Prefijos a quitar para normalización (ordenados de más largo a más corto para
# evitar que "la" coincida antes que "la señora")
PREFIXES_TO_STRIP = [
    # Artículos
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    # Demostrativos
    "este",
    "esta",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquellos",
    "aquellas",
    # Posesivos
    "mi",
    "mis",
    "tu",
    "tus",
    "su",
    "sus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
    "vuestro",
    "vuestra",
    "vuestros",
    "vuestras",
    # Honoríficos
    "don",
    "doña",
    "señor",
    "señora",
    "señorita",
    "sr",
    "sra",
    "srta",
    # Profesionales
    "doctor",
    "doctora",
    "dr",
    "dra",
    "ingeniero",
    "ingeniera",
    "ing",
    "licenciado",
    "licenciada",
    "lic",
    "profesor",
    "profesora",
    "prof",
    "maestro",
    "maestra",
    # Nobiliarios
    "conde",
    "condesa",
    "duque",
    "duquesa",
    "marqués",
    "marquesa",
    "barón",
    "baronesa",
    "príncipe",
    "princesa",
    "rey",
    "reina",
    "infante",
    "infanta",
    "lord",
    "lady",
    "sir",
    # Religiosos
    "padre",
    "madre",
    "hermano",
    "hermana",
    "fray",
    "sor",
    "san",
    "santa",
    "obispo",
    "arzobispo",
    "cardenal",
    "papa",
    "reverendo",
    "reverenda",
    # Militares
    "capitán",
    "capitana",
    "coronel",
    "coronela",
    "general",
    "generala",
    "teniente",
    "sargento",
    "cabo",
    "soldado",
    "almirante",
    "comandante",
]

# Ordenar de mayor a menor longitud para matching correcto
PREFIXES_TO_STRIP_SORTED = sorted(PREFIXES_TO_STRIP, key=len, reverse=True)


# =============================================================================
# Tabla de hipocorísticos españoles (diminutivos de nombres propios)
# =============================================================================

# Mapeo bidireccional: nombre formal → hipocorísticos conocidos
# Fuente: RAE, uso común en España y Latinoamérica
SPANISH_HYPOCORISTICS: dict[str, list[str]] = {
    # -------------------------------------------------------------------------
    # Masculinos
    # -------------------------------------------------------------------------
    "adolfo": ["fito"],
    "agustin": ["agus"],
    "alberto": ["berto", "alber", "beti", "bertin", "tito"],
    "alejandro": ["alex", "álex", "alejo", "jandro", "sandro"],
    "alfredo": ["fredo", "fred", "alfre"],
    "alfonso": ["poncho", "fonso", "fonsi", "foncho"],
    "alvaro": ["alvarito"],
    "anastasio": ["tasio"],
    "andres": ["andy"],
    "angel": ["gelo"],
    "antonio": ["toño", "toni", "toñin", "toñín"],
    "bartolome": ["tolo"],
    "carlos": ["charly", "carlitos"],
    "constantino": ["tino"],
    "daniel": ["dani"],
    "david": ["davi"],
    "domingo": ["mingo"],
    "eduardo": ["edu", "lalo"],
    "emilio": ["milo"],
    "enrique": ["quique", "kike", "tico"],
    "ernesto": ["neto"],
    "esteban": ["estebi"],
    "federico": ["fede", "quico"],
    "felipe": ["pipe", "feli"],
    "fernando": ["fer", "nando"],
    "florentino": ["flo"],
    "francisco": ["paco", "pancho", "pacho", "curro", "fran", "quico", "kiko", "cisco"],
    "gabriel": ["gabi"],
    "gonzalo": ["gonzo", "gonza", "chalo"],
    "gregorio": ["goyo"],
    "guillermo": ["guille", "memo", "willy"],
    "ignacio": ["nacho", "iñaki"],
    "inocencio": ["chencho"],
    "jaime": ["jaimito"],
    "javier": ["javi"],
    "jesus": ["chucho", "chuy", "chu", "chus", "chechu", "chule", "xule"],
    "joaquin": ["quino", "kin", "ximo", "chimo"],
    "jorge": ["coque"],
    "jose": ["pepe", "chepe", "pepito", "pepin", "pepín"],
    "josemaria": ["chema", "chemari"],
    "joseramon": ["joserra"],
    "juan": ["juanito", "juancho"],
    "juanmanuel": ["juanma"],
    "leonardo": ["leo", "nardo"],
    "leoncio": ["leo"],
    "leopoldo": ["leo", "polo"],
    "lorenzo": ["lencho"],
    "luis": ["lucho"],
    "manuel": ["manolo", "manu", "manolito", "lolo", "nolo"],
    "marcelo": ["chelo"],
    "marcos": ["marquitos"],
    "mateo": ["teo"],
    "miguel": ["migue"],
    "nicolas": ["nico"],
    "pablo": ["pablito"],
    "patricio": ["pato"],
    "pedro": ["perico"],
    "rafael": ["rafa", "rafi"],
    "ramon": ["moncho"],
    "ricardo": ["richi", "ricky"],
    "roberto": ["beto", "robi"],
    "rodolfo": ["rudi", "fito"],
    "rodrigo": ["rodri"],
    "salvador": ["salva", "chava"],
    "santiago": ["santi", "diego", "yago"],
    "sebastian": ["sebas"],
    "sergio": ["sergi", "checo"],
    "teodoro": ["teo"],
    "valentin": ["vale"],
    "vicente": ["chente", "vicen"],
    # -------------------------------------------------------------------------
    # Femeninos
    # -------------------------------------------------------------------------
    "adolfa": ["dolfi", "fita"],
    "antonia": ["toña", "toni"],
    "asuncion": ["asun", "chon"],
    "beatriz": ["bea"],
    "carmen": ["carmela", "menchu", "carmina"],
    "carolina": ["carol", "caro"],
    "catalina": ["cata", "lina"],
    "claudia": ["clau"],
    "concepcion": ["concha", "conchita", "conchi"],
    "consuelo": ["chelo"],
    "cristina": ["cris"],
    "dolores": ["lola", "loles", "lolita", "loli"],
    "elena": ["nena"],
    "enriqueta": ["queta"],
    "esperanza": ["espe"],
    "eulalia": ["lali"],
    "francisca": ["paca", "paquita", "curra", "fran", "chesca", "cisca"],
    "gregoria": ["goyi"],
    "guadalupe": ["lupe", "lupita"],
    "inmaculada": ["inma"],
    "irene": ["ire"],
    "isabel": ["isa", "chabela", "chavela", "beli", "chabeli"],
    "josefa": ["pepa", "pepita", "pepi"],
    "leocadia": ["leo", "cadia"],
    "leoncia": ["leo"],
    "leonor": ["leo", "nora"],
    "lucia": ["luci", "lu"],
    "luisa": ["lucha"],
    "macarena": ["maca"],
    "magdalena": ["magda", "malena", "malen"],
    "manuela": ["manoli"],
    "margarita": ["marga", "cuqui"],
    "maria": ["mari", "marita"],
    "mariaangeles": ["nines", "mariangeles"],
    "mariacarmen": ["mamen", "maricarmen"],
    "mariadolores": ["marilo"],
    "mariaeugenia": ["maru"],
    "mariaisabel": ["marisa"],
    "mariajose": ["majo"],
    "marialuisa": ["malu", "magüi"],
    "mariateresa": ["maite", "maritere"],
    "mariavictoria": ["marivi"],
    "mercedes": ["meche", "merche", "menchu"],
    "milagros": ["mila"],
    "montserrat": ["montse"],
    "natalia": ["nati", "nata"],
    "patricia": ["patri", "pati"],
    "pilar": ["pili", "piluca"],
    "purificacion": ["puri"],
    "remedios": ["reme"],
    "rosa": ["rosi", "rosita"],
    "rosario": ["charo", "chayo", "rosi"],
    "silvia": ["silvi"],
    "socorro": ["coco"],
    "soledad": ["sole", "chole", "marisol"],
    "susana": ["susi"],
    "teresa": ["tere"],
    "veronica": ["vero"],
    "victoria": ["vicky", "vicki"],
    "virginia": ["virgi"],
}

# Construir índice inverso: hipocorístico → nombres formales posibles
# Un hipocorístico puede corresponder a varios nombres (ej: "leo" → leonardo, leoncio)
_HYPOCORISTIC_TO_FORMALS: dict[str, list[str]] = {}
for _formal, _hyps in SPANISH_HYPOCORISTICS.items():
    for _h in _hyps:
        _key = _h.lower()
        if _key not in _HYPOCORISTIC_TO_FORMALS:
            _HYPOCORISTIC_TO_FORMALS[_key] = []
        _HYPOCORISTIC_TO_FORMALS[_key].append(_formal)

# Compatibilidad: primer formal encontrado (para get_formal_name)
_HYPOCORISTIC_TO_FORMAL: dict[str, str] = {k: v[0] for k, v in _HYPOCORISTIC_TO_FORMALS.items()}

# Sufijos diminutivos productivos en español
DIMINUTIVE_SUFFIXES = [
    ("ito", ""),  # Juanito → Juan
    ("ita", ""),  # Anita → Ana (pero no "bonita")
    ("illo", ""),  # Juanillo → Juan
    ("illa", ""),  # Rosilla → Rosa (raro en nombres)
    ("ín", ""),  # Pepín → Pepe / Agustín (nombre propio, no diminutivo)
    ("ina", ""),  # Josefina → Josefa (cuidado: algunos son nombres propios)
    ("ico", ""),  # Perico → Pedro (regional)
    ("ica", ""),  # Federica → (nombre propio)
    ("ete", ""),  # Juanete → (no aplica bien a nombres)
    ("uela", ""),  # Solo en raros casos
    ("uelo", ""),  # Solo en raros casos
]


def get_formal_name(name: str) -> str | None:
    """
    Obtiene el nombre formal a partir de un hipocorístico.

    Args:
        name: Nombre que puede ser un hipocorístico (ej: "Paco")

    Returns:
        Nombre formal si existe (ej: "Francisco"), o None

    Examples:
        >>> get_formal_name("Paco")
        'francisco'
        >>> get_formal_name("Lola")
        'dolores'
        >>> get_formal_name("Juan")  # No es hipocorístico
    """
    name_lower = strip_accents(name.lower().strip())
    return _HYPOCORISTIC_TO_FORMAL.get(name_lower)


def get_hypocoristics(name: str) -> list[str]:
    """
    Obtiene los hipocorísticos de un nombre formal.

    Args:
        name: Nombre formal (ej: "Francisco")

    Returns:
        Lista de hipocorísticos conocidos (ej: ["paco", "pancho", "curro"])

    Examples:
        >>> get_hypocoristics("Francisco")
        ['paco', 'pancho', 'curro', 'fran', 'quico', 'cisco']
    """
    name_lower = strip_accents(name.lower().strip())
    return SPANISH_HYPOCORISTICS.get(name_lower, [])


def are_hypocoristic_match(name1: str, name2: str) -> bool:
    """
    Comprueba si dos nombres son el mismo a través de hipocorísticos.

    Detecta tanto el mapeo directo (Paco↔Francisco) como
    hipocorísticos del mismo nombre (Paco↔Curro, ambos de Francisco).

    Args:
        name1: Primer nombre
        name2: Segundo nombre

    Returns:
        True si son variantes del mismo nombre

    Examples:
        >>> are_hypocoristic_match("Paco", "Francisco")
        True
        >>> are_hypocoristic_match("Paco", "Curro")  # ambos de Francisco
        True
        >>> are_hypocoristic_match("Juan", "Pedro")
        False
    """
    n1 = strip_accents(name1.lower().strip())
    n2 = strip_accents(name2.lower().strip())

    if n1 == n2:
        return True

    # Generar variantes: forma simple + forma compuesta sin espacios
    # "jose maria" → ["jose maria", "josemaria"]
    def _variants(name: str) -> list[str]:
        vs = [name]
        if " " in name:
            vs.append(name.replace(" ", ""))
        return vs

    variants1 = _variants(n1)
    variants2 = _variants(n2)

    for v1 in variants1:
        for v2 in variants2:
            # Caso 1: ambos son hipocorísticos del mismo nombre formal
            # Usar lista de posibles formales (leo → [leonardo, leoncio, leopoldo])
            formals1 = _HYPOCORISTIC_TO_FORMALS.get(v1, [v1])
            formals2 = _HYPOCORISTIC_TO_FORMALS.get(v2, [v2])

            # Si comparten algún nombre formal → match
            if set(formals1) & set(formals2):
                return True

            # Caso 2: uno es formal y el otro está en sus hipocorísticos
            if v2 in SPANISH_HYPOCORISTICS.get(v1, []):
                return True
            if v1 in SPANISH_HYPOCORISTICS.get(v2, []):
                return True

    return False


def strip_accents(text: str) -> str:
    """
    Quita acentos diacríticos del texto para comparación.

    Mantiene la ñ (es letra, no acento) y otros caracteres base.

    Args:
        text: Texto con posibles acentos

    Returns:
        Texto sin acentos diacríticos

    Examples:
        >>> strip_accents("María")
        'Maria'
        >>> strip_accents("José García")
        'Jose Garcia'
        >>> strip_accents("niño")  # ñ se mantiene
        'niño'
    """
    if not text:
        return text

    # NFD descompone los caracteres acentuados en base + acento
    normalized = unicodedata.normalize("NFD", text)
    # Filtrar solo los "Nonspacing Mark" (acentos), manteniendo todo lo demás
    result = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    # Recomponer cualquier carácter que pudiera haberse descompuesto
    return unicodedata.normalize("NFC", result)


def normalize_for_comparison(name: str) -> str:
    """
    Normaliza un nombre para comparación flexible.

    Aplica múltiples normalizaciones:
    1. Quita acentos (María → Maria)
    2. Convierte a minúsculas
    3. Normaliza espacios
    4. Quita prefijos (artículos, títulos)

    Esta función se usa para comparar si dos nombres son "iguales"
    aunque tengan diferencias ortográficas menores.

    Args:
        name: Nombre original

    Returns:
        Nombre normalizado para comparación

    Examples:
        >>> normalize_for_comparison("María Sánchez")
        'maria sanchez'
        >>> normalize_for_comparison("Don José García")
        'jose garcia'
        >>> normalize_for_comparison("  El   Niño  ")
        'niño'
    """
    if not name:
        return name

    # 1. Quitar prefijos primero (artículos, títulos)
    name = normalize_entity_name(name)

    # 2. Quitar acentos
    name = strip_accents(name)

    # 3. Minúsculas y espacios normalizados
    return " ".join(name.lower().split())


def normalize_entity_name(name: str) -> str:
    """
    Normaliza un nombre de entidad para comparación de fusión.

    Quita prefijos como artículos, demostrativos, posesivos, títulos
    honoríficos, profesionales, nobiliarios, religiosos y militares.

    Puede quitar múltiples prefijos encadenados:
    "el señor don García" → "García"
    "la doctora María Sánchez" → "María Sánchez"

    Args:
        name: Nombre original de la entidad

    Returns:
        Nombre normalizado (sin prefijos)

    Examples:
        >>> normalize_entity_name("la Mona Lisa")
        'Mona Lisa'
        >>> normalize_entity_name("el señor García")
        'García'
        >>> normalize_entity_name("Don Quijote")
        'Quijote'
    """
    if not name:
        return name

    words = name.split()
    if not words:
        return name

    # Quitar prefijos (puede haber varios encadenados)
    changed = True
    while changed and words:
        changed = False
        first_word_lower = words[0].lower()

        for prefix in PREFIXES_TO_STRIP_SORTED:
            if first_word_lower == prefix:
                words = words[1:]
                changed = True
                break

    result = " ".join(words) if words else name
    return result


def generate_name_variants(name: str) -> set[str]:
    """
    Genera todas las variantes de un nombre para matching de fusión.

    Incluye:
    - Nombre original
    - Nombre normalizado (sin prefijos)
    - Versiones con/sin tilde

    Args:
        name: Nombre de la entidad

    Returns:
        Set de variantes del nombre

    Examples:
        >>> variants = generate_name_variants("la Mona Lisa")
        >>> "Mona Lisa" in variants
        True
        >>> "la Mona Lisa" in variants
        True
    """
    variants = {name}

    # Añadir versión normalizada
    normalized = normalize_entity_name(name)
    if normalized and normalized != name:
        variants.add(normalized)

    # Añadir versiones sin tildes (para matching más flexible)
    import unicodedata

    def remove_accents(text: str) -> str:
        """Quita tildes/acentos de un texto."""
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    for variant in list(variants):
        no_accent = remove_accents(variant)
        if no_accent != variant:
            variants.add(no_accent)

    return variants


def names_match_after_normalization(name1: str, name2: str) -> bool:
    """
    Verifica si dos nombres coinciden después de normalización.

    Útil para determinar si dos entidades deberían fusionarse
    basándose solo en el nombre (antes de usar embeddings).

    Args:
        name1: Primer nombre
        name2: Segundo nombre

    Returns:
        True si los nombres coinciden después de normalizar

    Examples:
        >>> names_match_after_normalization("la Mona Lisa", "Mona Lisa")
        True
        >>> names_match_after_normalization("señor García", "García")
        True
        >>> names_match_after_normalization("María", "Juan")
        False
    """
    variants1 = generate_name_variants(name1)
    variants2 = generate_name_variants(name2)

    # Verificar si hay intersección
    # Comparar en lowercase para mayor flexibilidad
    variants1_lower = {v.lower() for v in variants1}
    variants2_lower = {v.lower() for v in variants2}

    if variants1_lower & variants2_lower:
        return True

    # Verificar con normalización: contención a nivel de palabras
    # "garcia" ⊂ "maria garcia" → True (palabras completas)
    # "carlos" ⊄ "carolina" → False (no es palabra completa)
    n1_normalized = normalize_for_comparison(name1)
    n2_normalized = normalize_for_comparison(name2)

    words1 = set(n1_normalized.split()) if n1_normalized else set()
    words2 = set(n2_normalized.split()) if n2_normalized else set()

    if words1 and words2:
        # Si todas las palabras de uno están en el otro → match
        if words1 <= words2 or words2 <= words1:
            return True

    # Verificar hipocorísticos (Paco ↔ Francisco, Lola ↔ Dolores)
    # Extraer primer nombre (sin apellidos) para comparar hipocorísticos
    first1 = n1_normalized.split()[0] if n1_normalized else ""
    first2 = n2_normalized.split()[0] if n2_normalized else ""

    return bool(first1 and first2 and are_hypocoristic_match(first1, first2))


@dataclass
class SemanticFusionResult:
    """Resultado de análisis de fusión semántica."""

    should_merge: bool
    similarity: float
    reason: str
    confidence: float
    method: str  # "embeddings", "dictionary", "llm"


class SemanticFusionService:
    """
    Servicio de fusión basado en similaridad semántica.

    Usa embeddings de sentence-transformers para calcular
    similaridad entre entidades más allá de coincidencia textual.

    Ejemplo:
        >>> service = SemanticFusionService()
        >>> result = service.should_merge(entity1, entity2, context="narrativa aquí...")
        >>> if result.should_merge:
        ...     print(f"Fusionar con confianza {result.confidence}")
    """

    def __init__(
        self,
        similarity_threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
        use_llm: bool = False,  # Preparado para futuro
    ):
        """
        Inicializa el servicio.

        Args:
            similarity_threshold: Umbral mínimo de similaridad semántica
            use_llm: Si True, usa LLM para casos complejos (no implementado)
        """
        self.similarity_threshold = similarity_threshold
        self.use_llm = use_llm
        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings is None:
            self._embeddings = get_embeddings_model()
        return self._embeddings

    def compute_semantic_similarity(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> float:
        """
        Calcula similaridad semántica entre dos entidades usando embeddings.

        Usa nombres normalizados (sin prefijos) para mejor comparación.

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad

        Returns:
            Similaridad entre 0.0 y 1.0
        """
        try:
            # Usar nombres normalizados para la comparación
            # normalize_for_comparison quita prefijos, acentos y pasa a minúsculas
            text1 = normalize_for_comparison(entity1.canonical_name)
            text2 = normalize_for_comparison(entity2.canonical_name)

            # Si los nombres normalizados son idénticos, es una fusión segura
            if text1 == text2 and text1:
                logger.debug(
                    f"Perfect match after normalization: '{entity1.canonical_name}' = "
                    f"'{entity2.canonical_name}' (both normalize to '{text1}')"
                )
                return 1.0

            # Añadir contexto de tipo para embeddings
            type_prefix1 = self._get_type_context(entity1.entity_type)
            type_prefix2 = self._get_type_context(entity2.entity_type)

            # Usar texto original (sin quitar acentos) para embeddings
            # Los embeddings multilingual manejan bien los acentos
            orig_text1 = normalize_entity_name(entity1.canonical_name)
            orig_text2 = normalize_entity_name(entity2.canonical_name)

            full_text1 = f"{type_prefix1} {orig_text1}"
            full_text2 = f"{type_prefix2} {orig_text2}"

            similarity = self.embeddings.similarity(full_text1, full_text2)

            logger.debug(
                f"Semantic similarity: '{entity1.canonical_name}' (norm: '{text1}') vs "
                f"'{entity2.canonical_name}' (norm: '{text2}') = {similarity:.3f}"
            )

            return float(similarity)

        except Exception as e:
            logger.warning(f"Error computing semantic similarity: {e}")
            return 0.0

    def _get_type_context(self, entity_type: EntityType) -> str:
        """Genera contexto textual para el tipo de entidad."""
        type_contexts = {
            EntityType.CHARACTER: "persona llamada",
            EntityType.LOCATION: "lugar llamado",
            EntityType.ORGANIZATION: "organización llamada",
            EntityType.OBJECT: "objeto llamado",
            EntityType.EVENT: "evento llamado",
            EntityType.CREATURE: "criatura llamada",
            EntityType.BUILDING: "edificio llamado",
            EntityType.REGION: "región llamada",
            EntityType.FACTION: "facción llamada",
            EntityType.FAMILY: "familia llamada",
            EntityType.CONCEPT: "concepto de",
        }
        return type_contexts.get(entity_type, "")

    def should_merge(
        self,
        entity1: Entity,
        entity2: Entity,
        narrative_context: str | None = None,
    ) -> SemanticFusionResult:
        """
        Determina si dos entidades deberían fusionarse.

        Combina múltiples señales:
        1. Similaridad semántica (embeddings)
        2. Marcadores anafóricos ("El parque" sugiere referencia)
        3. Contexto narrativo (si se proporciona)

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad
            narrative_context: Contexto narrativo opcional

        Returns:
            SemanticFusionResult con decisión y confianza
        """
        # 0a. FILTRO: No fusionar entidades de tipos incompatibles
        if not self._are_compatible_types(entity1, entity2):
            logger.debug(
                f"No fusionar: '{entity1.canonical_name}' ({entity1.entity_type}) y "
                f"'{entity2.canonical_name}' ({entity2.entity_type}) son tipos incompatibles"
            )
            return SemanticFusionResult(
                should_merge=False,
                similarity=0.0,
                reason="Tipos de entidad incompatibles",
                confidence=1.0,
                method="type_filter",
            )

        # 0b. FILTRO: No fusionar si una es frase larga y otra corta (estructura muy diferente)
        if self._have_incompatible_structure(entity1, entity2):
            logger.debug(
                f"No fusionar: '{entity1.canonical_name}' y '{entity2.canonical_name}' "
                "tienen estructuras incompatibles"
            )
            return SemanticFusionResult(
                should_merge=False,
                similarity=0.0,
                reason="Estructuras textuales incompatibles",
                confidence=1.0,
                method="structure_filter",
            )

        # 0c. FILTRO: No fusionar nombres propios diferentes
        # "María Sánchez" y "Juan Pérez" no deben fusionarse nunca
        if self._are_different_proper_names(entity1, entity2):
            logger.debug(
                f"No fusionar: '{entity1.canonical_name}' y '{entity2.canonical_name}' "
                "son nombres propios diferentes"
            )
            return SemanticFusionResult(
                should_merge=False,
                similarity=0.0,
                reason="Nombres propios diferentes",
                confidence=1.0,
                method="name_filter",
            )

        # 0d. FAST PATH: Si los nombres coinciden después de normalizar, fusionar directamente
        # Esto evita calcular embeddings para casos obvios como "la Mona Lisa" vs "Mona Lisa"
        if names_match_after_normalization(entity1.canonical_name, entity2.canonical_name):
            logger.debug(
                f"Fusionar por normalización: '{entity1.canonical_name}' = '{entity2.canonical_name}'"
            )
            return SemanticFusionResult(
                should_merge=True,
                similarity=1.0,
                reason="Nombres coinciden después de normalizar prefijos",
                confidence=0.95,
                method="normalization",
            )

        # 0e. ALIAS CHECK: Verificar si una entidad es alias/título de la otra
        # Ejemplo: "el Magistral" puede ser alias de "Fermín", "don Fermín" = "Fermín"
        is_alias, alias_confidence = self._check_alias_relationship(entity1, entity2)
        if is_alias and alias_confidence >= 0.7:
            logger.debug(
                f"Fusionar por alias: '{entity1.canonical_name}' ↔ '{entity2.canonical_name}' "
                f"(confianza={alias_confidence:.2f})"
            )
            return SemanticFusionResult(
                should_merge=True,
                similarity=alias_confidence,
                reason="Relación de alias/título detectada",
                confidence=alias_confidence,
                method="alias",
            )

        # 1. Calcular similaridad semántica base (usando nombres normalizados)
        similarity = self.compute_semantic_similarity(entity1, entity2)

        # 2. Detectar marcadores anafóricos
        has_anaphoric = self._has_anaphoric_marker(entity1, entity2)

        # Boost si hay marcador anafórico y el tipo coincide
        if has_anaphoric and entity1.entity_type == entity2.entity_type:
            similarity = min(1.0, similarity * 1.2)

        # 3. Determinar umbral dinámico según patrones
        # Para entidades tipo "el X" o "la X" (posibles alias/apodos),
        # usamos un umbral más bajo porque los embeddings no capturan
        # bien la relación entre apodos y nombres
        effective_threshold = self.similarity_threshold
        has_article_pattern = self._has_article_pattern(entity1, entity2)

        if has_article_pattern and entity1.entity_type == EntityType.CHARACTER:
            # Umbral reducido para posibles alias de personajes
            # "el Magistral" ↔ "Fermín" (0.64) debería poder fusionarse
            effective_threshold = max(0.60, self.similarity_threshold - 0.15)
            logger.debug(
                f"Umbral reducido a {effective_threshold:.2f} para patrón art+nombre: "
                f"'{entity1.canonical_name}' ↔ '{entity2.canonical_name}'"
            )

        # 4. Determinar si fusionar
        should_merge = similarity >= effective_threshold

        # 4. Calcular confianza
        confidence = similarity
        if has_anaphoric:
            confidence = min(1.0, confidence + 0.1)

        # 5. Generar razón
        if should_merge:
            reason = f"Similaridad semántica alta ({similarity:.2f})"
            if has_anaphoric:
                reason += " con marcador anafórico"
        else:
            reason = f"Similaridad semántica baja ({similarity:.2f})"

        return SemanticFusionResult(
            should_merge=should_merge,
            similarity=similarity,
            reason=reason,
            confidence=confidence,
            method="embeddings",
        )

    def _check_alias_relationship(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> tuple[bool, float]:
        """
        Verifica si una entidad es alias/título de la otra.

        Detecta patrones como:
        - "don Fermín" ↔ "Fermín" (título + nombre)
        - "el doctor" ↔ "García" (rol genérico + nombre, requiere contexto)
        - "el Magistral" ↔ "Fermín" (apodo, requiere contexto/LLM)

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad

        Returns:
            Tupla (is_alias, confidence)
        """
        name1 = entity1.canonical_name
        name2 = entity2.canonical_name
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()

        # Títulos que preceden directamente al nombre
        direct_titles = {"don", "doña", "fray", "sor", "san", "santa"}

        # Títulos profesionales/eclesiásticos/etc.
        role_titles = {
            "doctor",
            "doctora",
            "dr",
            "dra",
            "padre",
            "madre",
            "hermano",
            "hermana",  # religiosos
            "general",
            "coronel",
            "capitán",
            "comandante",
            "conde",
            "condesa",
            "duque",
            "duquesa",
            "marqués",
            "marquesa",
            "profesor",
            "profesora",
            "maestro",
            "maestra",
            "licenciado",
            "licenciada",
        }

        words1 = name1_lower.split()
        words2 = name2_lower.split()

        # Caso 1: "don Fermín" ↔ "Fermín"
        # Una tiene título directo + nombre, la otra solo el nombre
        if len(words1) >= 2 and words1[0] in direct_titles:
            # words1 = ["don", "fermín", ...]
            name_without_title1 = " ".join(words1[1:])
            if name_without_title1 == name2_lower:
                return True, 0.95
            # También verificar si el apellido coincide
            if len(words1) >= 2 and words1[-1] == name2_lower:
                return True, 0.85

        if len(words2) >= 2 and words2[0] in direct_titles:
            name_without_title2 = " ".join(words2[1:])
            if name_without_title2 == name1_lower:
                return True, 0.95
            if len(words2) >= 2 and words2[-1] == name1_lower:
                return True, 0.85

        # Caso 2: "el doctor García" ↔ "García"
        # Artículo + título + apellido ↔ apellido solo
        if len(words1) >= 3 and words1[0] in {"el", "la"} and words1[1] in role_titles:
            name_part1 = " ".join(words1[2:])
            if name_part1 == name2_lower:
                return True, 0.90
            # Verificar si el apellido coincide con alguna palabra
            if words1[-1] == name2_lower or words1[-1] in words2:
                return True, 0.80

        if len(words2) >= 3 and words2[0] in {"el", "la"} and words2[1] in role_titles:
            name_part2 = " ".join(words2[2:])
            if name_part2 == name1_lower:
                return True, 0.90
            if words2[-1] == name1_lower or words2[-1] in words1:
                return True, 0.80

        # Caso 3: "el Magistral" ↔ "Fermín" (apodo, más difícil)
        # Este caso requiere LLM si use_llm está habilitado
        # Detectamos si hay patrón de posible apodo
        is_possible_nickname1 = (
            len(words1) == 2
            and words1[0] in {"el", "la"}
            and len(name1.split()) > 1
            and name1.split()[1][0].isupper()
            and len(name1.split()[1]) > 2
            and words1[1] not in role_titles  # No es un título conocido
        )

        is_possible_nickname2 = (
            len(words2) == 2
            and words2[0] in {"el", "la"}
            and len(name2.split()) > 1
            and name2.split()[1][0].isupper()
            and len(name2.split()[1]) > 2
            and words2[1] not in role_titles
        )

        # Si uno es posible apodo y el otro es nombre propio corto (1-2 palabras),
        # consultar al LLM si use_llm está habilitado
        if self.use_llm and (is_possible_nickname1 or is_possible_nickname2):
            llm_result = self._check_alias_with_llm(entity1, entity2)
            if llm_result[0]:
                return llm_result

        # Caso 4: Nombre dentro de nombre compuesto
        # "María" ↔ "María García" (el nombre corto está contenido en el largo)
        if len(words1) == 1 and len(words2) > 1 and words1[0] in words2:
            return True, 0.85

        if len(words2) == 1 and len(words1) > 1 and words2[0] in words1:
            return True, 0.85

        return False, 0.0

    def _check_alias_with_llm(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> tuple[bool, float]:
        """
        Usa LLM para verificar si dos entidades son alias/referencia a la misma persona.

        Casos que maneja:
        - Apodos: "el Magistral" ↔ "Fermín de Pas"
        - Seudónimos: "Clarín" ↔ "Leopoldo Alas"
        - Referencias descriptivas: "el canónigo" ↔ "don Fermín"

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad

        Returns:
            Tupla (is_alias, confidence)
        """
        try:
            from ..llm.client import get_llm_client

            client = get_llm_client()

            if not client or not client.is_available:
                logger.debug("LLM no disponible para verificación de alias")
                return False, 0.0

            name1 = entity1.canonical_name
            name2 = entity2.canonical_name

            prompt = f"""En un texto narrativo en español, ¿estas dos referencias podrían ser la MISMA persona/entidad?

Referencia 1: "{name1}"
Referencia 2: "{name2}"

Considera:
- Apodos y motes (ej: "el Gordo" = "Pedro", "la Regenta" = "Ana Ozores")
- Títulos y cargos (ej: "el Magistral" = "Fermín de Pas", "don Quijote" = "Alonso Quijano")
- Seudónimos literarios (ej: "Clarín" = "Leopoldo Alas")
- Referencias por rol (ej: "el canónigo" = "don Fermín")

Responde SOLO con JSON:
{{"same_entity": true/false, "confidence": 0.0-1.0, "reason": "breve explicación"}}

JSON:"""

            response = client.complete(
                prompt,
                system="Eres un experto en análisis literario español. Identificas alias y referencias a personajes.",
                temperature=0.1,
                max_tokens=200,
            )

            if not response:
                return False, 0.0

            # Parsear respuesta
            import json

            cleaned = response.strip()

            # Limpiar markdown si está presente
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)

            # Encontrar JSON
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(cleaned[start:end])

                is_same = data.get("same_entity", False)
                confidence = float(data.get("confidence", 0.0))
                reason = data.get("reason", "")

                if is_same:
                    logger.debug(
                        f"LLM detectó alias: '{name1}' ↔ '{name2}' "
                        f"(confianza={confidence:.2f}, razón={reason})"
                    )
                    return True, confidence

        except json.JSONDecodeError as e:
            logger.debug(f"Error parseando JSON de LLM en alias check: {e}")
        except Exception as e:
            logger.warning(f"Error en verificación de alias con LLM: {e}")

        return False, 0.0

    def _has_article_pattern(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Detecta si alguna entidad tiene patrón artículo + palabra capitalizada.

        Este patrón indica un posible alias/apodo:
        - "el Magistral" (artículo + título/apodo)
        - "la Regenta" (artículo + apodo)
        - "el canónigo" (artículo + rol)

        Se excluyen frases descriptivas como "el hombre alto".
        """
        articles = {"el", "la", "los", "las"}

        for entity in [entity1, entity2]:
            name = entity.canonical_name
            words = name.split()

            if len(words) == 2:
                first_lower = words[0].lower()
                second = words[1]

                # Artículo + palabra capitalizada (no minúscula común)
                if first_lower in articles and second[0].isupper():
                    # Excluir sustantivos comunes que suelen ir después de artículo
                    common_nouns = {
                        "hombre",
                        "mujer",
                        "niño",
                        "niña",
                        "joven",
                        "anciano",
                        "persona",
                        "gente",
                        "mundo",
                        "vida",
                        "tiempo",
                        "día",
                        "casa",
                        "calle",
                        "ciudad",
                        "país",
                        "tierra",
                        "mar",
                    }
                    if second.lower() not in common_nouns:
                        return True

        return False

    def _has_anaphoric_marker(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Detecta si alguna entidad tiene un marcador anafórico.

        Marcadores anafóricos (ej: "El parque", "Ese hombre") sugieren
        que la entidad es una referencia a otra mencionada previamente.
        """
        name1 = entity1.canonical_name.lower()
        name2 = entity2.canonical_name.lower()

        for marker in ANAPHORIC_MARKERS:
            if name1.startswith(marker) or name2.startswith(marker):
                return True

        return False

    def _are_compatible_types(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Verifica si dos entidades tienen tipos compatibles para fusión.

        Reglas:
        - Mismo tipo: siempre compatible
        - CHARACTER con CREATURE: compatible (personajes fantásticos)
        - LOCATION con BUILDING/REGION: compatible
        - Todo lo demás: incompatible
        """
        if entity1.entity_type == entity2.entity_type:
            return True

        compatible_pairs = {
            (EntityType.CHARACTER, EntityType.CREATURE),
            (EntityType.CREATURE, EntityType.CHARACTER),
            (EntityType.LOCATION, EntityType.BUILDING),
            (EntityType.BUILDING, EntityType.LOCATION),
            (EntityType.LOCATION, EntityType.REGION),
            (EntityType.REGION, EntityType.LOCATION),
            (EntityType.BUILDING, EntityType.REGION),
            (EntityType.REGION, EntityType.BUILDING),
            (EntityType.ORGANIZATION, EntityType.FACTION),
            (EntityType.FACTION, EntityType.ORGANIZATION),
        }

        return (entity1.entity_type, entity2.entity_type) in compatible_pairs

    def _have_incompatible_structure(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Detecta si dos entidades tienen estructuras textuales incompatibles.

        Evita fusiones absurdas como:
        - "La alta sensibilidad" + "Créeme" (frase descriptiva vs verbo)
        - "El problema" + "McGyver" (concepto vs nombre propio)
        - "Quiero saber más" + "El voluntario" (oración vs sustantivo)

        Reglas:
        - Si una tiene >3 palabras y otra <2: incompatible
        - Si una parece oración (tiene verbo conjugado) y otra no: incompatible
        - Si una empieza con artículo/preposición y otra es nombre propio simple: incompatible
        """
        name1 = entity1.canonical_name.strip()
        name2 = entity2.canonical_name.strip()

        words1 = name1.split()
        words2 = name2.split()
        len1 = len(words1)
        len2 = len(words2)

        # Diferencia extrema de longitud
        if (len1 >= 4 and len2 == 1) or (len2 >= 4 and len1 == 1):
            return True

        # Detectar si parece verbo conjugado (terminaciones típicas)
        verb_endings = (
            "ar",
            "er",
            "ir",
            "ando",
            "endo",
            "iendo",
            "ado",
            "ido",
            "é",
            "ó",
            "emos",
            "aron",
            "ieron",
            "aba",
            "ía",
        )

        # Artículos que pueden preceder títulos/apodos en español
        # "el Magistral", "la Regenta", "don Fermín" - estos son válidos para fusión
        title_articles = {"el", "la", "don", "doña", "san", "santa"}

        # Preposiciones que indican frases descriptivas (no nombres)
        prepositions = {"sobre", "para", "por", "sin", "con", "de", "en", "hacia", "desde"}

        def is_article_plus_title(words: list[str]) -> bool:
            """Detecta patrones como 'el Magistral', 'la Regenta', 'don Fermín'."""
            if len(words) == 2:
                first = words[0].lower()
                second = words[1] if len(words) > 1 else ""
                # Artículo + palabra con mayúscula = título/apodo
                if first in title_articles and second and second[0].isupper():
                    return True
            return False

        def looks_like_descriptive_phrase(words: list[str]) -> bool:
            """Detecta frases descriptivas que NO deben fusionarse con nombres propios."""
            if not words:
                return False
            first = words[0].lower()
            # Empieza con preposición = frase descriptiva
            if first in prepositions:
                return True
            # 3+ palabras y no es artículo + título = probablemente frase
            return bool(len(words) >= 3 and not is_article_plus_title(words))

        def has_verb(words: list[str]) -> bool:
            for w in words:
                w_lower = w.lower()
                if any(w_lower.endswith(end) for end in verb_endings):
                    return True
            return False

        # Si una es frase descriptiva (no título) y otra es nombre propio simple
        if looks_like_descriptive_phrase(words1) and len2 <= 2:
            if name2 and name2[0].isupper():
                return True

        if looks_like_descriptive_phrase(words2) and len1 <= 2:
            if name1 and name1[0].isupper():
                return True

        # Si una tiene verbo y otra no, probablemente no deben fusionarse
        if has_verb(words1) != has_verb(words2):
            # Solo si son estructuralmente muy diferentes
            if abs(len1 - len2) >= 2:
                return True

        return False

    def _are_different_proper_names(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Detecta si dos entidades son nombres propios claramente diferentes.

        "María Sánchez" y "Juan Pérez" -> True (diferentes)
        "María Sánchez" y "María" -> False (posible alias)
        "Él" y "Juan" -> False (pronombre, podría referirse a Juan)
        """
        name1 = entity1.canonical_name.strip()
        name2 = entity2.canonical_name.strip()

        # Si alguno es pronombre, no son "nombres propios diferentes"
        pronouns = {
            "él",
            "ella",
            "ellos",
            "ellas",
            "este",
            "esta",
            "ese",
            "esa",
            "aquel",
            "aquella",
            "lo",
            "la",
            "le",
            "les",
            "se",
            "quien",
        }
        if name1.lower() in pronouns or name2.lower() in pronouns:
            return False

        # Si alguno empieza con artículo, podría ser referencia anafórica
        for marker in ANAPHORIC_MARKERS:
            if name1.lower().startswith(marker) or name2.lower().startswith(marker):
                return False

        # Extraer primer nombre (antes del espacio o todo si no hay espacio)
        first_name1 = name1.split()[0] if name1 else ""
        first_name2 = name2.split()[0] if name2 else ""

        # Si ambos empiezan con mayúscula (nombres propios)
        if first_name1 and first_name2:
            if first_name1[0].isupper() and first_name2[0].isupper():
                # Verificar si uno contiene al otro (posible alias)
                # "María" es parte de "María Sánchez" -> permitir fusión
                name1_lower = name1.lower()
                name2_lower = name2.lower()

                if name1_lower.startswith(name2_lower) or name2_lower.startswith(name1_lower):
                    return False  # Posible alias, permitir fusión

                # Son nombres propios diferentes
                return True

        return False

    def resolve_nominal_coreference(
        self,
        anaphoric_entity: Entity,
        candidates: list[Entity],
        narrative_context: str | None = None,
    ) -> Entity | None:
        """
        Resuelve a qué entidad se refiere una mención anafórica.

        Por ejemplo: "El parque" → busca el parque más probable

        Args:
            anaphoric_entity: Entidad con mención anafórica
            candidates: Candidatos posibles
            narrative_context: Contexto para desambiguación

        Returns:
            Entity más probable o None si no hay coincidencia clara
        """
        if not candidates:
            return None

        best_match = None
        best_similarity = 0.0

        for candidate in candidates:
            if candidate.id == anaphoric_entity.id:
                continue

            result = self.should_merge(anaphoric_entity, candidate, narrative_context)

            if result.similarity > best_similarity:
                best_similarity = result.similarity
                best_match = candidate

        # Solo retornar si la confianza es suficiente
        if best_similarity >= self.similarity_threshold:
            logger.info(
                f"Resolved '{anaphoric_entity.canonical_name}' -> "
                f"'{best_match.canonical_name}' (similarity: {best_similarity:.2f})"
            )
            return best_match

        return None


# =============================================================================
# LLM Integration Placeholder (Post-MVP)
# =============================================================================


async def resolve_coreference_with_local_llm(
    text: str,
    mention: str,
    candidates: list[str],
    model_path: str | None = None,
) -> str | None:
    """
    Resuelve correferencia usando un LLM LOCAL.

    IMPORTANTE: Para mantener la privacidad de los manuscritos,
    SOLO se usan modelos ejecutados localmente. Opciones:
    - Ollama (Llama 3, Mistral, Phi-2, etc.)
    - llama.cpp con modelos GGUF
    - Modelos pequeños de HuggingFace en local

    NOTA: No implementado en MVP. Preparado para integración futura.

    Args:
        text: Contexto narrativo
        mention: Mención a resolver ("el parque")
        candidates: Nombres de candidatos posibles
        model_path: Ruta al modelo local (opcional)

    Returns:
        Nombre del candidato más probable o None

    TODO Post-MVP:
        - Integrar con Ollama (más fácil de instalar)
        - O usar llama-cpp-python para modelos GGUF
        - Añadir caching para reducir latencia
        - Probar con Phi-2 o Mistral-7B-Instruct

    Ejemplo de prompt para el LLM:
        "En el siguiente texto narrativo, la mención '{mention}'
        probablemente se refiere a: {candidates}. ¿Cuál es más probable?
        Texto: {text[:500]}..."
    """
    logger.warning(
        "Local LLM coreference resolution not implemented. "
        "This feature is planned for post-MVP. "
        "Consider using Ollama with Phi-2 or Mistral for local inference."
    )
    return None


# =============================================================================
# Singleton
# =============================================================================

_semantic_fusion_service: SemanticFusionService | None = None


def get_semantic_fusion_service(
    similarity_threshold: float | None = None,
) -> SemanticFusionService:
    """
    Obtiene singleton del servicio de fusión semántica.

    Args:
        similarity_threshold: Umbral de similaridad (None = usa config global)

    Returns:
        Instancia única de SemanticFusionService
    """
    global _semantic_fusion_service

    if _semantic_fusion_service is None:
        threshold = (
            similarity_threshold if similarity_threshold is not None else _get_fusion_threshold()
        )
        _semantic_fusion_service = SemanticFusionService(
            similarity_threshold=threshold,
        )

    return _semantic_fusion_service


def update_fusion_threshold(new_threshold: float) -> None:
    """
    Actualiza el umbral de fusión en tiempo de ejecución.

    Útil cuando el usuario cambia la configuración desde SettingsView.

    Args:
        new_threshold: Nuevo umbral de similitud (0.0 a 1.0)
    """
    global _semantic_fusion_service

    if not 0.0 <= new_threshold <= 1.0:
        raise ValueError(f"El umbral debe estar entre 0.0 y 1.0, recibido: {new_threshold}")

    if _semantic_fusion_service is not None:
        _semantic_fusion_service.similarity_threshold = new_threshold
        logger.info(f"Umbral de fusión semántica actualizado a {new_threshold:.2f}")


def reset_semantic_fusion_service() -> None:
    """Resetea el singleton (útil para tests)."""
    global _semantic_fusion_service
    _semantic_fusion_service = None
