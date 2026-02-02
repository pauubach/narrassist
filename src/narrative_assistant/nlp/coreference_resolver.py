"""
Sistema de Resolución de Correferencias Multi-Método con Votación.

Este módulo implementa un sistema robusto de resolución de correferencias
para textos narrativos en español, combinando múltiples métodos modernos:

1. **Embeddings semánticos** (sentence-transformers)
   - Similitud entre menciones y candidatos
   - Contexto semántico de oraciones

2. **LLM local** (Ollama)
   - Análisis profundo de relaciones anafóricas
   - Comprensión del contexto narrativo

3. **Análisis morfosintáctico** (spaCy)
   - Concordancia de género/número
   - Análisis de dependencias

4. **Heurísticas narrativas**
   - Proximidad textual
   - Saliencia del personaje
   - Patrones narrativos típicos

Arquitectura:
- Cada método genera candidatos con scores de confianza
- Sistema de votación ponderada para consenso
- Procesamiento por capítulos para mejor contexto
- Fallbacks graceful si algún método no está disponible

Referencias:
- Lee et al. (2017): End-to-end Neural Coreference Resolution
- XLM-RoBERTa para representaciones multilingües
- AnCora-CO corpus para evaluación en español
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# Enums y Constantes
# =============================================================================

class MentionType(Enum):
    """Tipo de mención en el texto."""
    PROPER_NOUN = "proper_noun"      # Nombre propio: "Juan", "María García"
    PRONOUN = "pronoun"              # Pronombre: "él", "ella", "ellos"
    DEFINITE_NP = "definite_np"      # SN definido: "el doctor", "la mujer"
    DEMONSTRATIVE = "demonstrative"  # Demostrativo: "este", "aquella"
    POSSESSIVE = "possessive"        # Posesivo: "su hermano", "sus ojos"
    ZERO = "zero"                    # Sujeto omitido (pro-drop)


class Gender(Enum):
    """Género gramatical."""
    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class Number(Enum):
    """Número gramatical."""
    SINGULAR = "singular"
    PLURAL = "plural"
    UNKNOWN = "unknown"


class CorefMethod(Enum):
    """Métodos de resolución de correferencias."""
    EMBEDDINGS = "embeddings"        # Similitud semántica
    LLM = "llm"                      # LLM local (Ollama)
    MORPHO = "morpho"                # Análisis morfosintáctico
    HEURISTICS = "heuristics"        # Heurísticas narrativas
    TRANSFORMER = "transformer"      # Modelo transformer fine-tuned (futuro)


# Pesos por defecto para votación
DEFAULT_COREF_WEIGHTS = {
    CorefMethod.EMBEDDINGS: 0.30,
    CorefMethod.LLM: 0.35,
    CorefMethod.MORPHO: 0.20,
    CorefMethod.HEURISTICS: 0.15,
}

# Mapeo de pronombres españoles a género/número
# IMPORTANTE: Los posesivos están en SPANISH_POSSESSIVES, no aquí
SPANISH_PRONOUNS = {
    # =========================================================================
    # PRIMERA PERSONA (narrador)
    # =========================================================================
    # Sujeto
    "yo": (Gender.NEUTRAL, Number.SINGULAR),  # Género se infiere del contexto
    # Objeto directo/indirecto
    "me": (Gender.NEUTRAL, Number.SINGULAR),
    "mí": (Gender.NEUTRAL, Number.SINGULAR),
    "conmigo": (Gender.NEUTRAL, Number.SINGULAR),
    # Plural
    "nosotros": (Gender.MASCULINE, Number.PLURAL),
    "nosotras": (Gender.FEMININE, Number.PLURAL),
    "nos": (Gender.NEUTRAL, Number.PLURAL),
    # =========================================================================
    # SEGUNDA PERSONA (interlocutor)
    # =========================================================================
    "tú": (Gender.NEUTRAL, Number.SINGULAR),
    "te": (Gender.NEUTRAL, Number.SINGULAR),
    "ti": (Gender.NEUTRAL, Number.SINGULAR),
    "contigo": (Gender.NEUTRAL, Number.SINGULAR),
    "usted": (Gender.NEUTRAL, Number.SINGULAR),
    "ustedes": (Gender.NEUTRAL, Number.PLURAL),
    "vosotros": (Gender.MASCULINE, Number.PLURAL),
    "vosotras": (Gender.FEMININE, Number.PLURAL),
    "os": (Gender.NEUTRAL, Number.PLURAL),
    # =========================================================================
    # TERCERA PERSONA
    # =========================================================================
    # Pronombres personales sujeto
    "él": (Gender.MASCULINE, Number.SINGULAR),
    "ella": (Gender.FEMININE, Number.SINGULAR),
    "ellos": (Gender.MASCULINE, Number.PLURAL),
    "ellas": (Gender.FEMININE, Number.PLURAL),
    # Pronombres objeto directo
    "lo": (Gender.MASCULINE, Number.SINGULAR),
    "la": (Gender.FEMININE, Number.SINGULAR),
    "los": (Gender.MASCULINE, Number.PLURAL),
    "las": (Gender.FEMININE, Number.PLURAL),
    # Pronombres objeto indirecto (sin género específico)
    "le": (Gender.NEUTRAL, Number.SINGULAR),
    "les": (Gender.NEUTRAL, Number.PLURAL),
    # Reflexivos
    "se": (Gender.NEUTRAL, Number.UNKNOWN),
    "sí": (Gender.NEUTRAL, Number.UNKNOWN),
    "consigo": (Gender.NEUTRAL, Number.UNKNOWN),
    # Posesivos tónicos tercera persona
    "suyo": (Gender.MASCULINE, Number.SINGULAR),
    "suya": (Gender.FEMININE, Number.SINGULAR),
    "suyos": (Gender.MASCULINE, Number.PLURAL),
    "suyas": (Gender.FEMININE, Number.PLURAL),
}

# Demostrativos
SPANISH_DEMONSTRATIVES = {
    "este": (Gender.MASCULINE, Number.SINGULAR),
    "esta": (Gender.FEMININE, Number.SINGULAR),
    "estos": (Gender.MASCULINE, Number.PLURAL),
    "estas": (Gender.FEMININE, Number.PLURAL),
    "ese": (Gender.MASCULINE, Number.SINGULAR),
    "esa": (Gender.FEMININE, Number.SINGULAR),
    "esos": (Gender.MASCULINE, Number.PLURAL),
    "esas": (Gender.FEMININE, Number.PLURAL),
    "aquel": (Gender.MASCULINE, Number.SINGULAR),
    "aquella": (Gender.FEMININE, Number.SINGULAR),
    "aquellos": (Gender.MASCULINE, Number.PLURAL),
    "aquellas": (Gender.FEMININE, Number.PLURAL),
}

# Posesivos (separados de pronombres para clasificación correcta)
# Los posesivos de tercera persona (su, sus) son NEUTRALES porque no indican
# el género del poseedor, sino del objeto poseído.
# IMPORTANTE: El género del poseedor se determina por el ANTECEDENTE, no por el posesivo.
SPANISH_POSSESSIVES = {
    # Primera persona
    "mi": (Gender.NEUTRAL, Number.SINGULAR),     # átono
    "mis": (Gender.NEUTRAL, Number.PLURAL),      # átono plural
    "mío": (Gender.MASCULINE, Number.SINGULAR),  # tónico
    "mía": (Gender.FEMININE, Number.SINGULAR),   # tónico
    "míos": (Gender.MASCULINE, Number.PLURAL),   # tónico
    "mías": (Gender.FEMININE, Number.PLURAL),    # tónico
    "nuestro": (Gender.MASCULINE, Number.SINGULAR),
    "nuestra": (Gender.FEMININE, Number.SINGULAR),
    "nuestros": (Gender.MASCULINE, Number.PLURAL),
    "nuestras": (Gender.FEMININE, Number.PLURAL),
    # Segunda persona
    "tu": (Gender.NEUTRAL, Number.SINGULAR),     # átono
    "tus": (Gender.NEUTRAL, Number.PLURAL),      # átono plural
    "tuyo": (Gender.MASCULINE, Number.SINGULAR), # tónico
    "tuya": (Gender.FEMININE, Number.SINGULAR),  # tónico
    "tuyos": (Gender.MASCULINE, Number.PLURAL),  # tónico
    "tuyas": (Gender.FEMININE, Number.PLURAL),   # tónico
    "vuestro": (Gender.MASCULINE, Number.SINGULAR),
    "vuestra": (Gender.FEMININE, Number.SINGULAR),
    "vuestros": (Gender.MASCULINE, Number.PLURAL),
    "vuestras": (Gender.FEMININE, Number.PLURAL),
    # Tercera persona (de él/ella/ellos/ellas/usted/ustedes)
    "su": (Gender.NEUTRAL, Number.SINGULAR),     # átono (más común)
    "sus": (Gender.NEUTRAL, Number.PLURAL),      # átono plural
    "suyo": (Gender.MASCULINE, Number.SINGULAR), # tónico
    "suya": (Gender.FEMININE, Number.SINGULAR),  # tónico
    "suyos": (Gender.MASCULINE, Number.PLURAL),  # tónico
    "suyas": (Gender.FEMININE, Number.PLURAL),   # tónico
}

# =============================================================================
# Sustantivos que refieren a personas (para DEFINITE_NP)
# =============================================================================

# Artículos definidos y su género/número
DEFINITE_ARTICLES = {
    "el": (Gender.MASCULINE, Number.SINGULAR),
    "la": (Gender.FEMININE, Number.SINGULAR),
    "los": (Gender.MASCULINE, Number.PLURAL),
    "las": (Gender.FEMININE, Number.PLURAL),
}

# Sustantivos que típicamente refieren a personas en narrativa
# Organizados por género para validación
PERSON_NOUNS_MASCULINE = {
    # Relaciones familiares
    "padre", "papá", "abuelo", "hijo", "nieto", "hermano", "tío", "sobrino",
    "primo", "cuñado", "suegro", "yerno", "marido", "esposo", "novio",
    # Edades/roles genéricos
    "hombre", "joven", "chico", "muchacho", "niño", "anciano", "viejo",
    "adolescente", "bebé", "adulto",
    # Profesiones/roles (masculino)
    "médico", "doctor", "abogado", "juez", "profesor", "maestro",
    "conductor", "chofer", "taxista", "piloto", "capitán", "general",
    "coronel", "teniente", "sargento", "soldado", "policía", "guardia",
    "jefe", "director", "gerente", "presidente", "ministro", "rey", "príncipe",
    "camarero", "cocinero", "portero", "conserje", "jardinero", "obrero",
    "empleado", "secretario", "asistente", "ayudante",
    "sacerdote", "cura", "fraile", "monje", "rabino", "imán",
    "escritor", "pintor", "escultor", "músico", "cantante", "actor",
    "detective", "inspector", "comisario", "fiscal", "testigo", "acusado",
    # Descriptivos
    "desconocido", "extraño", "intruso", "visitante", "huésped", "invitado",
    "vecino", "amigo", "enemigo", "rival", "compañero", "colega",
    "líder", "guía", "mentor", "discípulo", "alumno", "estudiante",
}

PERSON_NOUNS_FEMININE = {
    # Relaciones familiares
    "madre", "mamá", "abuela", "hija", "nieta", "hermana", "tía", "sobrina",
    "prima", "cuñada", "suegra", "nuera", "esposa", "mujer", "novia",
    # Edades/roles genéricos
    "joven", "chica", "muchacha", "niña", "anciana", "vieja",
    "adolescente", "adulta",
    # Profesiones/roles (femenino)
    "médica", "doctora", "abogada", "jueza", "profesora", "maestra",
    "conductora", "pilota", "capitana", "generala", "coronela",
    "teniente", "sargenta", "soldada", "policía", "guardia",
    "jefa", "directora", "gerenta", "presidenta", "ministra", "reina", "princesa",
    "camarera", "cocinera", "portera", "conserja", "jardinera", "obrera",
    "empleada", "secretaria", "asistenta", "ayudante",
    "monja", "religiosa", "rabina",
    "escritora", "pintora", "escultora", "música", "cantante", "actriz",
    "detective", "inspectora", "comisaria", "fiscal", "testigo", "acusada",
    # Descriptivos
    "desconocida", "extraña", "intrusa", "visitante", "huésped", "invitada",
    "vecina", "amiga", "enemiga", "rival", "compañera", "colega",
    "líder", "guía", "mentora", "discípula", "alumna", "estudiante",
    # Específicos femeninos
    "dama", "señora", "señorita", "doncella", "criada", "sirvienta",
}

# Todos los sustantivos de persona (para búsqueda rápida)
ALL_PERSON_NOUNS = PERSON_NOUNS_MASCULINE | PERSON_NOUNS_FEMININE

# Pronombres de primera persona (para detectar narrador)
FIRST_PERSON_PRONOUNS = {
    "yo", "me", "mí", "mi", "mis", "conmigo",
    "mío", "mía", "míos", "mías",
    "nosotros", "nosotras", "nos", "nuestro", "nuestra", "nuestros", "nuestras",
}

# Patrones para detectar auto-identificación del narrador
# El nombre debe terminar en punto, coma, o fin de línea para evitar falsos positivos
# como "me llamó con malos modales" vs "me llamo Marta."
NARRATOR_PATTERNS = [
    r"me\s+llamo\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n]|$)",
    r"mi\s+nombre\s+es\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n]|$)",
    r"soy\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n])",
    r"me\s+llaman\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n]|$)",
    r"pueden\s+llamarme\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n]|$)",
    r"me\s+dicen\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[,.\n]|$)",
]


# =============================================================================
# Estructuras de Datos
# =============================================================================

@dataclass
class Mention:
    """
    Representa una mención en el texto.

    Attributes:
        text: Texto de la mención
        start_char: Posición inicial en el documento
        end_char: Posición final en el documento
        mention_type: Tipo de mención
        gender: Género gramatical detectado
        number: Número gramatical detectado
        sentence_idx: Índice de la oración
        chapter_idx: Índice del capítulo (opcional)
    """
    text: str
    start_char: int
    end_char: int
    mention_type: MentionType
    gender: Gender = Gender.UNKNOWN
    number: Number = Number.UNKNOWN
    sentence_idx: int = 0
    chapter_idx: Optional[int] = None
    head_text: Optional[str] = None  # Cabeza sintáctica
    context: Optional[str] = None    # Contexto circundante

    def __hash__(self):
        return hash((self.text, self.start_char, self.end_char))

    def __eq__(self, other):
        if not isinstance(other, Mention):
            return False
        return (self.text == other.text and
                self.start_char == other.start_char and
                self.end_char == other.end_char)


@dataclass
class CorefCandidate:
    """
    Un candidato de correferencia con scores por método.

    Attributes:
        antecedent: Mención antecedente (a la que refiere)
        anaphor: Mención anafórica (la que refiere)
        scores: Scores por cada método de resolución
        final_score: Score final ponderado
        is_coreferent: Si se considera correferenciales
    """
    antecedent: Mention
    anaphor: Mention
    scores: dict[CorefMethod, float] = field(default_factory=dict)
    final_score: float = 0.0
    is_coreferent: bool = False
    reasoning: dict[CorefMethod, str] = field(default_factory=dict)


@dataclass
class CoreferenceChain:
    """
    Cadena de menciones correferenciales.

    Attributes:
        mentions: Lista de menciones en la cadena
        main_mention: Mención principal (nombre propio preferido)
        entity_id: ID de entidad asociada (si existe)
        confidence: Confianza promedio de la cadena
        methods_agreed: Métodos que contribuyeron
    """
    mentions: list[Mention] = field(default_factory=list)
    main_mention: Optional[str] = None
    entity_id: Optional[int] = None
    confidence: float = 0.0
    methods_agreed: list[CorefMethod] = field(default_factory=list)

    def __post_init__(self):
        if self.mentions and not self.main_mention:
            self.main_mention = self._find_main_mention()

    def _find_main_mention(self) -> str:
        """
        Encuentra la mención más informativa.

        REGLA CRÍTICA: Un pronombre NUNCA puede ser la mención principal.
        Si la cadena solo tiene pronombres, devuelve vacío.
        """
        priority = {
            MentionType.PROPER_NOUN: 4,
            MentionType.DEFINITE_NP: 3,
            MentionType.DEMONSTRATIVE: 2,
            MentionType.POSSESSIVE: 1,
            MentionType.PRONOUN: 0,  # Pronombres: prioridad mínima
            MentionType.ZERO: -1,
        }

        if not self.mentions:
            return ""

        # Filtrar pronombres y menciones cero - nunca pueden ser la mención principal
        non_pronoun_mentions = [
            m for m in self.mentions
            if m.mention_type not in (MentionType.PRONOUN, MentionType.ZERO)
        ]

        # Si no hay menciones que no sean pronombres, devolver vacío
        # Una cadena con solo pronombres no tiene entidad principal identificable
        if not non_pronoun_mentions:
            return ""

        sorted_mentions = sorted(
            non_pronoun_mentions,
            key=lambda m: (priority.get(m.mention_type, 0), len(m.text)),
            reverse=True
        )
        return sorted_mentions[0].text

    def add_mention(self, mention: Mention) -> None:
        """Añade una mención a la cadena."""
        if mention not in self.mentions:
            self.mentions.append(mention)
            self.mentions.sort(key=lambda m: m.start_char)
            self.main_mention = self._find_main_mention()


@dataclass
class MentionVotingDetail:
    """
    Detalle de la votación para una mención resuelta.

    Attributes:
        anaphor_text: Texto de la mención anafórica
        anaphor_start: Posición inicial de la anáfora
        anaphor_end: Posición final de la anáfora
        resolved_to: Texto del antecedente ganador
        final_score: Score ponderado final
        method_votes: Votos de cada método {method: {score, reasoning}}
    """
    anaphor_text: str = ""
    anaphor_start: int = 0
    anaphor_end: int = 0
    resolved_to: str = ""
    final_score: float = 0.0
    method_votes: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serializa a diccionario para almacenamiento JSON."""
        return {
            "anaphor_text": self.anaphor_text,
            "anaphor_start": self.anaphor_start,
            "anaphor_end": self.anaphor_end,
            "resolved_to": self.resolved_to,
            "final_score": self.final_score,
            "method_votes": self.method_votes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MentionVotingDetail":
        """Deserializa desde diccionario."""
        return cls(
            anaphor_text=data.get("anaphor_text", ""),
            anaphor_start=data.get("anaphor_start", 0),
            anaphor_end=data.get("anaphor_end", 0),
            resolved_to=data.get("resolved_to", ""),
            final_score=data.get("final_score", 0.0),
            method_votes=data.get("method_votes", {}),
        )


@dataclass
class CorefResult:
    """
    Resultado de la resolución de correferencias.

    Attributes:
        chains: Cadenas de correferencia detectadas
        unresolved: Menciones que no pudieron resolverse
        method_contributions: Contribución de cada método
        voting_details: Detalle de votación por mención {(start, end): MentionVotingDetail}
        processing_time_ms: Tiempo de procesamiento
    """
    chains: list[CoreferenceChain] = field(default_factory=list)
    unresolved: list[Mention] = field(default_factory=list)
    method_contributions: dict[CorefMethod, int] = field(default_factory=dict)
    voting_details: dict[tuple[int, int], MentionVotingDetail] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    @property
    def total_mentions(self) -> int:
        return sum(len(c.mentions) for c in self.chains)

    @property
    def total_chains(self) -> int:
        return len(self.chains)


def _get_default_coref_methods() -> list[CorefMethod]:
    """
    Retorna los métodos de correferencia habilitados por defecto.

    - Con GPU: Todos los métodos (incluyendo LLM)
    - Sin GPU: Solo métodos rápidos (sin LLM)
    """
    try:
        from ..core.device import get_device_config
        device_config = get_device_config()
        has_gpu = device_config.device_type in ("cuda", "mps")
    except Exception:
        has_gpu = False

    if has_gpu:
        # GPU disponible: usar todos los métodos
        return list(CorefMethod)
    else:
        # Solo CPU: excluir LLM (muy lento)
        return [
            CorefMethod.EMBEDDINGS,
            CorefMethod.MORPHO,
            CorefMethod.HEURISTICS,
        ]


@dataclass
class CorefConfig:
    """Configuración del sistema de correferencias."""
    enabled_methods: list[CorefMethod] = field(default_factory=_get_default_coref_methods)
    method_weights: dict[CorefMethod, float] = field(default_factory=lambda: DEFAULT_COREF_WEIGHTS.copy())
    min_confidence: float = 0.5
    consensus_threshold: float = 0.6  # Mínimo % de métodos que deben acordar
    max_antecedent_distance: int = 5  # Máx oraciones hacia atrás
    use_chapter_boundaries: bool = True  # Respetar límites de capítulo
    ollama_model: str = "llama3.2"  # Modelo LLM por defecto
    ollama_timeout: int = 600  # 10 min - CPU sin GPU es muy lento
    use_llm_for_coref: bool = field(default=None)  # None = auto (GPU sí, CPU no)

    def __post_init__(self):
        """Ajusta configuración según hardware si use_llm_for_coref es None."""
        if self.use_llm_for_coref is None:
            # Auto-detectar
            has_llm = CorefMethod.LLM in self.enabled_methods
            self.use_llm_for_coref = has_llm
        elif self.use_llm_for_coref and CorefMethod.LLM not in self.enabled_methods:
            # Usuario quiere LLM pero no está habilitado
            self.enabled_methods.append(CorefMethod.LLM)
        elif not self.use_llm_for_coref and CorefMethod.LLM in self.enabled_methods:
            # Usuario no quiere LLM pero está habilitado
            self.enabled_methods.remove(CorefMethod.LLM)


# =============================================================================
# Interfaces de Métodos
# =============================================================================

class CorefMethodInterface(Protocol):
    """Interfaz para métodos de resolución."""

    def resolve(
        self,
        anaphor: Mention,
        candidates: list[Mention],
        context: str,
    ) -> list[tuple[Mention, float, str]]:
        """
        Resuelve una mención anafórica.

        Args:
            anaphor: Mención a resolver
            candidates: Candidatos antecedentes
            context: Contexto textual

        Returns:
            Lista de (candidato, score, razonamiento)
        """
        ...


# =============================================================================
# Implementación de Métodos
# =============================================================================

class EmbeddingsCorefMethod:
    """
    Resolución basada en embeddings semánticos.

    Usa sentence-transformers para calcular similitud
    entre el contexto de la mención y los candidatos.
    """

    def __init__(self):
        self._embeddings_model = None
        self._lock = threading.Lock()

    @property
    def embeddings(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings_model is None:
            with self._lock:
                if self._embeddings_model is None:
                    try:
                        from ..nlp.embeddings import get_embeddings_model
                        self._embeddings_model = get_embeddings_model()
                        logger.info("Modelo de embeddings cargado para correferencias")
                    except Exception as e:
                        logger.warning(f"No se pudo cargar embeddings: {e}")
        return self._embeddings_model

    def resolve(
        self,
        anaphor: Mention,
        candidates: list[Mention],
        context: str,
    ) -> list[tuple[Mention, float, str]]:
        """Resuelve usando similitud de embeddings."""
        if not self.embeddings or not candidates:
            return []

        results = []

        # Construir texto contextual para la mención anafórica
        anaphor_context = anaphor.context or anaphor.text

        for candidate in candidates:
            # Construir texto del candidato con contexto
            candidate_context = candidate.context or candidate.text

            # Calcular similitud
            try:
                similarity = self.embeddings.similarity(
                    anaphor_context,
                    candidate_context
                )

                # Boost si hay concordancia de género/número
                if (anaphor.gender != Gender.UNKNOWN and
                    candidate.gender != Gender.UNKNOWN and
                    anaphor.gender == candidate.gender):
                    similarity *= 1.1

                if (anaphor.number != Number.UNKNOWN and
                    candidate.number != Number.UNKNOWN and
                    anaphor.number == candidate.number):
                    similarity *= 1.1

                # Normalizar a [0, 1]
                similarity = min(1.0, max(0.0, similarity))

                reasoning = f"Similitud semántica: {similarity:.2f}"
                results.append((candidate, similarity, reasoning))

            except Exception as e:
                logger.debug(f"Error calculando similitud: {e}")
                continue

        return sorted(results, key=lambda x: x[1], reverse=True)


class LLMCorefMethod:
    """
    Resolución usando LLM local (Ollama).

    Aprovecha la comprensión semántica profunda del LLM
    para resolver correferencias complejas.
    """

    def __init__(self, model: str = "llama3.2", timeout: int = 600):
        self.model = model
        self.timeout = timeout  # 10 min default - CPU sin GPU es lento
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        """Lazy loading del cliente LLM."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        from ..llm.client import get_llm_client
                        self._client = get_llm_client()
                        if self._client:
                            logger.info(f"Cliente LLM conectado para correferencias: {self.model}")
                    except Exception as e:
                        logger.warning(f"No se pudo conectar LLM: {e}")
        return self._client

    def resolve(
        self,
        anaphor: Mention,
        candidates: list[Mention],
        context: str,
    ) -> list[tuple[Mention, float, str]]:
        """Resuelve usando el LLM local."""
        if not self.client or not candidates:
            return []

        # Construir prompt para el LLM
        candidates_text = "\n".join([
            f"  {i+1}. \"{c.text}\" (posición: {c.start_char})"
            for i, c in enumerate(candidates[:5])  # Limitar candidatos
        ])

        prompt = f"""Analiza la siguiente correferencia en español.

CONTEXTO:
"{context}"

MENCIÓN A RESOLVER: "{anaphor.text}" (tipo: {anaphor.mention_type.value})

CANDIDATOS POSIBLES:
{candidates_text}

¿A cuál candidato se refiere "{anaphor.text}"? Responde SOLO con el número del candidato más probable y una breve explicación.

Formato de respuesta:
CANDIDATO: [número]
CONFIANZA: [alta/media/baja]
RAZÓN: [explicación breve]"""

        try:
            response = self.client.complete(
                prompt=prompt,
                system="Eres un experto en análisis lingüístico del español. Tu tarea es resolver correferencias (determinar a quién o qué se refiere un pronombre o expresión).",
                max_tokens=200,
                temperature=0.1,
            )

            if not response:
                return []

            # Parsear respuesta
            results = self._parse_llm_response(response, candidates)
            return results

        except Exception as e:
            logger.debug(f"Error en LLM coref: {e}")
            return []

    def _parse_llm_response(
        self,
        response: str,
        candidates: list[Mention]
    ) -> list[tuple[Mention, float, str]]:
        """Parsea la respuesta del LLM."""
        results = []

        # Buscar número de candidato
        candidate_match = re.search(r'CANDIDATO:\s*(\d+)', response, re.IGNORECASE)
        confidence_match = re.search(r'CONFIANZA:\s*(alta|media|baja)', response, re.IGNORECASE)
        reason_match = re.search(r'RAZ[OÓ]N:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)

        if candidate_match:
            try:
                idx = int(candidate_match.group(1)) - 1
                if 0 <= idx < len(candidates):
                    # Mapear confianza
                    conf_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
                    confidence = conf_map.get(
                        confidence_match.group(1).lower() if confidence_match else "media",
                        0.7
                    )

                    reason = reason_match.group(1).strip() if reason_match else "LLM selection"
                    results.append((candidates[idx], confidence, reason))
            except (ValueError, IndexError):
                pass

        return results


class MorphoCorefMethod:
    """
    Resolución basada en análisis morfosintáctico.

    Usa spaCy para analizar concordancia gramatical
    y relaciones de dependencia.
    """

    def __init__(self):
        self._nlp = None
        self._lock = threading.Lock()

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            with self._lock:
                if self._nlp is None:
                    try:
                        from ..nlp.spacy_gpu import load_spacy_model
                        self._nlp = load_spacy_model()
                        logger.info("Modelo spaCy cargado para correferencias")
                    except Exception as e:
                        logger.warning(f"No se pudo cargar spaCy: {e}")
        return self._nlp

    def resolve(
        self,
        anaphor: Mention,
        candidates: list[Mention],
        context: str,
    ) -> list[tuple[Mention, float, str]]:
        """Resuelve usando análisis morfosintáctico."""
        if not self.nlp or not candidates:
            return []

        results = []

        for candidate in candidates:
            score = 0.0
            reasons = []

            # Concordancia de género
            if anaphor.gender != Gender.UNKNOWN and candidate.gender != Gender.UNKNOWN:
                if anaphor.gender == candidate.gender:
                    score += 0.4
                    reasons.append("género coincide")
                elif anaphor.gender == Gender.NEUTRAL or candidate.gender == Gender.NEUTRAL:
                    score += 0.2
                    reasons.append("género compatible")
                else:
                    score -= 0.3
                    reasons.append("género no coincide")

            # Concordancia de número
            if anaphor.number != Number.UNKNOWN and candidate.number != Number.UNKNOWN:
                if anaphor.number == candidate.number:
                    score += 0.3
                    reasons.append("número coincide")
                else:
                    score -= 0.3
                    reasons.append("número no coincide")

            # Bonificación por tipo de mención
            if candidate.mention_type == MentionType.PROPER_NOUN:
                score += 0.2
                reasons.append("nombre propio")

            # Penalización por distancia
            sentence_distance = abs(anaphor.sentence_idx - candidate.sentence_idx)
            if sentence_distance == 0:
                score += 0.1
            elif sentence_distance <= 2:
                score += 0.05
            elif sentence_distance > 5:
                score -= 0.1

            # Normalizar
            score = min(1.0, max(0.0, (score + 0.5) / 1.5))

            reasoning = "; ".join(reasons) if reasons else "análisis morfológico"
            results.append((candidate, score, reasoning))

        return sorted(results, key=lambda x: x[1], reverse=True)


class HeuristicsCorefMethod:
    """
    Resolución basada en heurísticas narrativas.

    Implementa reglas basadas en patrones típicos
    de la narrativa en español.

    REGLA PRINCIPAL para posesivos (su, sus):
    El posesivo típicamente refiere al SUJETO de la oración actual o anterior,
    NO simplemente a la entidad más cercana. En "María apareció. Sus ojos verdes...",
    "Sus" refiere a María porque María es el sujeto de la oración anterior.
    """

    def resolve(
        self,
        anaphor: Mention,
        candidates: list[Mention],
        context: str,
    ) -> list[tuple[Mention, float, str]]:
        """Resuelve usando heurísticas narrativas."""
        if not candidates:
            return []

        results = []

        # Para posesivos, calcular quién es el candidato más reciente en misma/anterior oración
        # Este candidato recibe un bonus muy alto
        most_recent_in_scope: Optional[Mention] = None
        if anaphor.mention_type == MentionType.POSSESSIVE:
            most_recent_in_scope = self._find_most_recent_subject_candidate(
                anaphor, candidates
            )

        for candidate in candidates:
            score = 0.0
            reasons = []

            # Recencia: preferir candidatos más cercanos
            char_distance = anaphor.start_char - candidate.end_char
            if char_distance > 0:  # El candidato está antes
                if char_distance < 100:
                    score += 0.4
                    reasons.append("muy cercano")
                elif char_distance < 300:
                    score += 0.3
                    reasons.append("cercano")
                elif char_distance < 1000:
                    score += 0.1
                    reasons.append("moderadamente cerca")
                else:
                    score -= 0.1
                    reasons.append("lejano")

            # Saliencia: personajes mencionados frecuentemente
            # (esto requeriría información adicional sobre frecuencia)

            # Patrones narrativos comunes
            anaphor_lower = anaphor.text.lower()

            # "él/ella" típicamente refiere al sujeto de la oración anterior
            if anaphor_lower in ["él", "ella"] and candidate.mention_type == MentionType.PROPER_NOUN:
                score += 0.2
                reasons.append("pronombre personal → nombre propio")

            # Posesivos típicamente refieren al sujeto de la oración actual o anterior
            # REGLA CRÍTICA: En español, "Sus ojos verdes" después de "María apareció"
            # típicamente refiere a María (el sujeto de la oración anterior)
            if anaphor.mention_type == MentionType.POSSESSIVE:
                if candidate.mention_type == MentionType.PROPER_NOUN:
                    # Bonus base por ser nombre propio
                    score += 0.15
                    reasons.append("posesivo → nombre")

                    # BONUS CRÍTICO: Si es el candidato más reciente en scope
                    if candidate == most_recent_in_scope:
                        score += 0.45
                        reasons.append("sujeto más reciente")

                    # BONUS por distancia de oración
                    sentence_distance = abs(anaphor.sentence_idx - candidate.sentence_idx)
                    if sentence_distance == 0:
                        # Mismo oración: muy alta probabilidad
                        score += 0.25
                        reasons.append("misma oración")
                    elif sentence_distance == 1:
                        # Oración anterior: alta probabilidad (caso típico)
                        score += 0.20
                        reasons.append("oración anterior")
                    elif sentence_distance == 2:
                        # Dos oraciones atrás: probabilidad moderada
                        score += 0.10
                        reasons.append("2 oraciones atrás")

            # Mismo capítulo bonus
            if (anaphor.chapter_idx is not None and
                candidate.chapter_idx is not None and
                anaphor.chapter_idx == candidate.chapter_idx):
                score += 0.1
                reasons.append("mismo capítulo")

            # Normalizar
            score = min(1.0, max(0.0, score))

            reasoning = "; ".join(reasons) if reasons else "heurísticas narrativas"
            results.append((candidate, score, reasoning))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def _find_most_recent_subject_candidate(
        self,
        anaphor: Mention,
        candidates: list[Mention],
    ) -> Optional[Mention]:
        """
        Encuentra el candidato más reciente que pueda ser el sujeto referido por el posesivo.

        Para posesivos en español, el referente típico es:
        1. El sujeto de la misma oración (si hay uno)
        2. El sujeto de la oración inmediatamente anterior
        3. La entidad más reciente mencionada (si no hay sujeto explícito)

        El "sujeto" típicamente es un nombre propio que aparece ANTES del verbo
        en la oración anterior.
        """
        # Filtrar candidatos que están en misma oración o la anterior
        in_scope = []
        for c in candidates:
            if c.mention_type != MentionType.PROPER_NOUN:
                continue
            if c.start_char >= anaphor.start_char:
                continue  # Solo candidatos anteriores
            sentence_distance = anaphor.sentence_idx - c.sentence_idx
            if 0 <= sentence_distance <= 1:  # Misma oración o la anterior
                in_scope.append(c)

        if not in_scope:
            return None

        # El candidato más reciente (por posición de carácter) es el más probable
        # En "María apareció. Sus ojos...", María es el más reciente antes de "Sus"
        return max(in_scope, key=lambda c: c.end_char)


# =============================================================================
# Sistema Principal de Votación
# =============================================================================

class CoreferenceVotingResolver:
    """
    Sistema de resolución de correferencias con votación multi-método.

    Combina múltiples métodos de resolución y usa votación ponderada
    para determinar las correferencias finales.

    Example:
        >>> resolver = CoreferenceVotingResolver()
        >>> result = resolver.resolve_document(text, chapters)
        >>> for chain in result.chains:
        ...     print(f"{chain.main_mention}: {len(chain.mentions)} menciones")
    """

    def __init__(self, config: Optional[CorefConfig] = None):
        """
        Inicializa el resolutor.

        Args:
            config: Configuración del sistema
        """
        self.config = config or CorefConfig()

        # Inicializar métodos
        self._methods: dict[CorefMethod, CorefMethodInterface] = {}
        self._init_methods()

        logger.info(
            f"CoreferenceVotingResolver inicializado con métodos: "
            f"{[m.value for m in self.config.enabled_methods]}"
        )

    def _init_methods(self) -> None:
        """Inicializa los métodos de resolución habilitados."""
        method_classes = {
            CorefMethod.EMBEDDINGS: EmbeddingsCorefMethod,
            CorefMethod.LLM: lambda: LLMCorefMethod(
                model=self.config.ollama_model,
                timeout=self.config.ollama_timeout
            ),
            CorefMethod.MORPHO: MorphoCorefMethod,
            CorefMethod.HEURISTICS: HeuristicsCorefMethod,
        }

        for method in self.config.enabled_methods:
            if method in method_classes:
                try:
                    self._methods[method] = method_classes[method]()
                    logger.debug(f"Método {method.value} inicializado")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar {method.value}: {e}")

    def resolve_document(
        self,
        text: str,
        chapters: Optional[list[dict]] = None,
    ) -> CorefResult:
        """
        Resuelve correferencias en un documento completo.

        Args:
            text: Texto completo del documento
            chapters: Lista de capítulos con start_char/end_char

        Returns:
            CorefResult con cadenas y estadísticas
        """
        import time
        start_time = time.time()

        result = CorefResult()

        # Extraer menciones
        mentions = self._extract_mentions(text, chapters)
        logger.info(f"Extraídas {len(mentions)} menciones del documento")

        if not mentions:
            return result

        # Detectar narrador en primera persona
        narrator_info = self._detect_narrator(text, mentions)

        # Separar anáforas y posibles antecedentes
        anaphors = [m for m in mentions if self._is_anaphor(m)]
        potential_antecedents = [m for m in mentions if self._is_potential_antecedent(m)]

        # Si hay narrador, añadirlo como antecedente potencial
        if narrator_info:
            narrator_name, narrator_gender = narrator_info
            # Buscar si ya existe en antecedentes
            narrator_exists = any(
                m.text == narrator_name for m in potential_antecedents
            )
            if not narrator_exists:
                for pattern in NARRATOR_PATTERNS:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        narrator_mention = Mention(
                            text=narrator_name,
                            start_char=match.start(1),
                            end_char=match.end(1),
                            mention_type=MentionType.PROPER_NOUN,
                            gender=narrator_gender,
                            number=Number.SINGULAR,
                            sentence_idx=0,
                        )
                        potential_antecedents.append(narrator_mention)
                        break

        logger.info(f"Anáforas: {len(anaphors)}, Antecedentes potenciales: {len(potential_antecedents)}")

        # Si hay narrador, resolver primero los pronombres de primera persona
        # y excluirlos de la resolución normal
        first_person_already_resolved: set[int] = set()
        if narrator_info:
            first_person_resolved = self._resolve_first_person(
                text, mentions, narrator_info
            )
            for anaphor, antecedent, score in first_person_resolved:
                first_person_already_resolved.add(anaphor.start_char)

        # Resolver cada anáfora (excluyendo las de primera persona ya resueltas)
        resolved_pairs: list[tuple[Mention, Mention, float]] = []

        for anaphor in anaphors:
            # Si es pronombre de primera persona y hay narrador, saltar
            if anaphor.start_char in first_person_already_resolved:
                continue

            # Filtrar candidatos válidos (anteriores y cercanos)
            candidates = self._filter_candidates(anaphor, potential_antecedents)

            if not candidates:
                result.unresolved.append(anaphor)
                continue

            # Obtener contexto
            context = self._get_context(text, anaphor, window=200)

            # Aplicar cada método y recolectar votos
            all_votes: dict[Mention, list[tuple[float, CorefMethod, str]]] = {}

            for method, resolver in self._methods.items():
                try:
                    method_results = resolver.resolve(anaphor, candidates, context)

                    for candidate, score, reasoning in method_results:
                        if candidate not in all_votes:
                            all_votes[candidate] = []
                        all_votes[candidate].append((score, method, reasoning))

                except Exception as e:
                    logger.debug(f"Error en método {method.value}: {e}")

            # Votación ponderada
            best_candidate, final_score, method_detail = self._weighted_vote(all_votes)

            if best_candidate and final_score >= self.config.min_confidence:
                resolved_pairs.append((anaphor, best_candidate, final_score))

                # Registrar contribución de métodos
                for score, method, _ in all_votes.get(best_candidate, []):
                    result.method_contributions[method] = \
                        result.method_contributions.get(method, 0) + 1

                # Almacenar detalle de votación para esta mención
                result.voting_details[(anaphor.start_char, anaphor.end_char)] = \
                    MentionVotingDetail(
                        anaphor_text=anaphor.text,
                        anaphor_start=anaphor.start_char,
                        anaphor_end=anaphor.end_char,
                        resolved_to=best_candidate.text,
                        final_score=round(final_score, 3),
                        method_votes=method_detail,
                    )
            else:
                result.unresolved.append(anaphor)

        # Añadir resoluciones de primera persona al narrador
        if narrator_info and first_person_already_resolved:
            first_person_resolved = self._resolve_first_person(
                text, mentions, narrator_info
            )
            for anaphor, antecedent, score in first_person_resolved:
                resolved_pairs.append((anaphor, antecedent, score))
                # Marcar como contribución del narrador (usamos HEURISTICS como indicador)
                result.method_contributions[CorefMethod.HEURISTICS] = \
                    result.method_contributions.get(CorefMethod.HEURISTICS, 0) + 1

                # Detalle de votación para primera persona -> narrador
                result.voting_details[(anaphor.start_char, anaphor.end_char)] = \
                    MentionVotingDetail(
                        anaphor_text=anaphor.text,
                        anaphor_start=anaphor.start_char,
                        anaphor_end=anaphor.end_char,
                        resolved_to=antecedent.text,
                        final_score=round(score, 3),
                        method_votes={
                            "heuristics": {
                                "score": round(score, 3),
                                "reasoning": f"Pronombre 1ª persona → narrador '{antecedent.text}'",
                                "weight": 1.0,
                                "weighted_score": round(score, 3),
                            }
                        },
                    )

        # Construir cadenas de correferencia
        result.chains = self._build_chains(resolved_pairs, potential_antecedents)

        result.processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Resolución completada: {result.total_chains} cadenas, "
            f"{len(result.unresolved)} sin resolver, "
            f"{result.processing_time_ms:.1f}ms"
        )

        return result

    def _extract_mentions(
        self,
        text: str,
        chapters: Optional[list[dict]] = None,
    ) -> list[Mention]:
        """Extrae menciones del texto usando spaCy."""
        mentions = []

        try:
            from ..nlp.spacy_gpu import load_spacy_model
            nlp = load_spacy_model()
        except Exception as e:
            logger.warning(f"No se pudo cargar spaCy para extracción: {e}")
            # Fallback a extracción simple
            return self._extract_mentions_simple(text, chapters)

        doc = nlp(text)

        # Mapear posición a capítulo
        def get_chapter_idx(char_pos: int) -> Optional[int]:
            if not chapters:
                return None
            for i, ch in enumerate(chapters):
                if ch.get("start_char", 0) <= char_pos < ch.get("end_char", len(text)):
                    return i
            return None

        # Mapear oración a índice real (no índice de token)
        sentence_to_idx = {}
        for i, sent in enumerate(doc.sents):
            sentence_to_idx[sent.start] = i

        def get_sentence_idx(token_or_span) -> int:
            """Obtiene el índice real de la oración (0, 1, 2, ...)."""
            sent = token_or_span.sent if hasattr(token_or_span, 'sent') else None
            if sent is None:
                return 0
            return sentence_to_idx.get(sent.start, 0)

        # Extraer entidades nombradas (nombres propios)
        for ent in doc.ents:
            if ent.label_ in ("PER", "PERSON", "LOC", "ORG"):
                # Filtrar menciones inválidas
                if not self._is_valid_mention(ent.text):
                    logger.debug(f"Mención filtrada: '{ent.text}'")
                    continue

                gender, number = self._infer_gender_number(ent.text, doc[ent.start])
                mentions.append(Mention(
                    text=ent.text,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    mention_type=MentionType.PROPER_NOUN,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(doc[ent.start]),
                    chapter_idx=get_chapter_idx(ent.start_char),
                    context=self._get_context(text, None, window=50,
                                             start=ent.start_char, end=ent.end_char),
                ))

        # Extraer pronombres
        for token in doc:
            text_lower = token.text.lower()

            # Pronombres personales
            if text_lower in SPANISH_PRONOUNS:
                gender, number = SPANISH_PRONOUNS[text_lower]
                mentions.append(Mention(
                    text=token.text,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    mention_type=MentionType.PRONOUN,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(token),
                    chapter_idx=get_chapter_idx(token.idx),
                    context=self._get_context(text, None, window=50,
                                             start=token.idx, end=token.idx + len(token.text)),
                ))

            # Demostrativos
            elif text_lower in SPANISH_DEMONSTRATIVES:
                gender, number = SPANISH_DEMONSTRATIVES[text_lower]
                mentions.append(Mention(
                    text=token.text,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    mention_type=MentionType.DEMONSTRATIVE,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(token),
                    chapter_idx=get_chapter_idx(token.idx),
                ))

            # Posesivos (su, sus, mi, mis, tu, tus, etc.)
            # IMPORTANTE: Clasificados como POSSESSIVE, no PRONOUN
            elif text_lower in SPANISH_POSSESSIVES:
                gender, number = SPANISH_POSSESSIVES[text_lower]
                mentions.append(Mention(
                    text=token.text,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    mention_type=MentionType.POSSESSIVE,
                    gender=gender,
                    number=number,
                    sentence_idx=get_sentence_idx(token),
                    chapter_idx=get_chapter_idx(token.idx),
                    context=self._get_context(text, None, window=50,
                                             start=token.idx, end=token.idx + len(token.text)),
                ))

        # Extraer sintagmas nominales definidos (DEFINITE_NP)
        # Patrones como "el padre", "la niña", "el conductor del autobús"
        definite_nps = self._extract_definite_nps(doc, text, get_sentence_idx, get_chapter_idx)
        mentions.extend(definite_nps)

        # Extraer sujetos omitidos (pro-drop / ZERO)
        # Solo 3ª persona singular/plural — 1ª/2ª persona no son útiles para correferencia
        zero_mentions = self._extract_zero_mentions(doc, text, get_sentence_idx, get_chapter_idx)
        mentions.extend(zero_mentions)

        n_total = len(mentions)
        n_zero = len(zero_mentions)
        logger.info(
            "Menciones extraídas: %d total, %d ZERO/pro-drop (%.0f%%)",
            n_total, n_zero, (n_zero / n_total * 100) if n_total else 0,
        )

        # Ordenar por posición
        mentions.sort(key=lambda m: m.start_char)

        return mentions

    def _extract_mentions_simple(
        self,
        text: str,
        chapters: Optional[list[dict]] = None,
    ) -> list[Mention]:
        """Extracción simple de menciones sin spaCy."""
        mentions = []

        # Buscar pronombres con regex
        for pronoun, (gender, number) in SPANISH_PRONOUNS.items():
            pattern = rf'\b{re.escape(pronoun)}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append(Mention(
                    text=match.group(),
                    start_char=match.start(),
                    end_char=match.end(),
                    mention_type=MentionType.PRONOUN,
                    gender=gender,
                    number=number,
                ))

        # Buscar posesivos con regex
        for possessive, (gender, number) in SPANISH_POSSESSIVES.items():
            pattern = rf'\b{re.escape(possessive)}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append(Mention(
                    text=match.group(),
                    start_char=match.start(),
                    end_char=match.end(),
                    mention_type=MentionType.POSSESSIVE,
                    gender=gender,
                    number=number,
                ))

        mentions.sort(key=lambda m: m.start_char)
        return mentions

    def _extract_definite_nps(
        self,
        doc,
        text: str,
        get_sentence_idx,
        get_chapter_idx,
    ) -> list[Mention]:
        """
        Extrae sintagmas nominales definidos que refieren a personas.

        Detecta patrones como:
        - "el padre", "la niña", "el joven"
        - "el conductor del autobús", "la mujer de la tienda"
        - "el viejo profesor", "la joven estudiante"

        Returns:
            Lista de menciones de tipo DEFINITE_NP
        """
        mentions = []
        seen_spans = set()  # Evitar duplicados

        # Estrategia 1: Usar chunks de spaCy para sintagmas nominales
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip()
            chunk_lower = chunk_text.lower()

            # Debe empezar con artículo definido
            first_word = chunk_lower.split()[0] if chunk_lower else ""
            if first_word not in DEFINITE_ARTICLES:
                continue

            # La cabeza del chunk debe ser un sustantivo de persona
            head = chunk.root
            head_lemma = head.lemma_.lower()

            if head_lemma not in ALL_PERSON_NOUNS:
                continue

            # Evitar duplicados y solapamientos con entidades ya detectadas
            span_key = (chunk.start_char, chunk.end_char)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

            # Determinar género y número
            # El artículo tiene prioridad para sustantivos ambiguos (estudiante, colega, etc.)
            art_gender, _ = DEFINITE_ARTICLES.get(first_word, (Gender.UNKNOWN, Number.UNKNOWN))

            # Si el sustantivo está SOLO en masculino o SOLO en femenino, usar eso
            in_masc = head_lemma in PERSON_NOUNS_MASCULINE
            in_fem = head_lemma in PERSON_NOUNS_FEMININE

            if in_masc and not in_fem:
                gender = Gender.MASCULINE
            elif in_fem and not in_masc:
                gender = Gender.FEMININE
            else:
                # Sustantivo ambiguo o desconocido: usar el artículo
                gender = art_gender

            # Número del artículo
            _, number = DEFINITE_ARTICLES.get(first_word, (Gender.UNKNOWN, Number.UNKNOWN))

            mentions.append(Mention(
                text=chunk_text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                mention_type=MentionType.DEFINITE_NP,
                gender=gender,
                number=number,
                sentence_idx=get_sentence_idx(head),
                chapter_idx=get_chapter_idx(chunk.start_char),
                head_text=head.text,
                context=self._get_context(text, None, window=50,
                                         start=chunk.start_char, end=chunk.end_char),
            ))

        # Estrategia 2: Regex para patrones no capturados por chunks
        # Patrones como "el conductor del autobús"
        for article, (art_gender, art_number) in DEFINITE_ARTICLES.items():
            # Patrón: artículo + (adjetivo?) + sustantivo_persona + (complemento?)
            for noun in ALL_PERSON_NOUNS:
                # Patrón simple: "el padre", "la niña"
                pattern = rf'\b{article}\s+{noun}\b'
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    span_key = (match.start(), match.end())
                    if span_key in seen_spans:
                        continue

                    # Verificar que no está dentro de un span ya detectado
                    is_subspan = any(
                        s <= match.start() and e >= match.end()
                        for (s, e) in seen_spans
                    )
                    if is_subspan:
                        continue

                    seen_spans.add(span_key)

                    # Determinar género del sustantivo
                    if noun in PERSON_NOUNS_MASCULINE:
                        gender = Gender.MASCULINE
                    elif noun in PERSON_NOUNS_FEMININE:
                        gender = Gender.FEMININE
                    else:
                        gender = art_gender

                    mentions.append(Mention(
                        text=match.group(),
                        start_char=match.start(),
                        end_char=match.end(),
                        mention_type=MentionType.DEFINITE_NP,
                        gender=gender,
                        number=art_number,
                        head_text=noun,
                    ))

        return mentions

    def _extract_zero_mentions(
        self,
        doc,
        text: str,
        get_sentence_idx,
        get_chapter_idx,
    ) -> list[Mention]:
        """
        Extrae menciones de sujeto omitido (pro-drop) en verbos finitos.

        En español, el sujeto puede omitirse cuando la conjugación verbal
        es inequívoca. Solo se extraen menciones de 3ª persona (singular
        y plural) porque 1ª/2ª persona raramente son útiles para
        correferencia narrativa.

        Se genera con confianza baja (0.4) para evitar contaminar cadenas
        existentes en la resolución posterior.

        Returns:
            Lista de menciones de tipo ZERO
        """
        mentions = []

        # Posiciones de sujetos explícitos ya detectados (para evitar duplicar)
        explicit_subj_verbs: set[int] = set()
        for token in doc:
            if token.dep_ in ("nsubj", "nsubj:pass") and token.head.pos_ == "VERB":
                explicit_subj_verbs.add(token.head.i)

        for token in doc:
            # Solo verbos finitos
            if token.pos_ != "VERB":
                continue
            morph = str(token.morph)
            if "VerbForm=Fin" not in morph:
                continue

            # Saltar si ya tiene sujeto explícito
            if token.i in explicit_subj_verbs:
                continue

            # Solo 3ª persona — 1ª/2ª no son útiles para correferencia narrativa
            if "Person=3" not in morph:
                continue

            # Inferir número
            if "Number=Sing" in morph:
                number = Number.SINGULAR
            elif "Number=Plur" in morph:
                number = Number.PLURAL
            else:
                continue  # No se puede determinar

            # Inferir género del contexto verbal (limitado — UNKNOWN por defecto)
            gender = Gender.UNKNOWN

            # Representación textual: verbo entre corchetes (ASCII-safe)
            zero_text = f"[PRO {token.text}]"

            mentions.append(Mention(
                text=zero_text,
                start_char=token.idx,
                end_char=token.idx + len(token.text),
                mention_type=MentionType.ZERO,
                gender=gender,
                number=number,
                sentence_idx=get_sentence_idx(token),
                chapter_idx=get_chapter_idx(token.idx),
                context=self._get_context(text, None, window=50,
                                         start=token.idx, end=token.idx + len(token.text)),
            ))

        logger.debug(f"Extraídas {len(mentions)} menciones pro-drop (ZERO)")
        return mentions

    # Nombres españoles comunes por género (para inferencia cuando spaCy no detecta)
    FEMININE_NAMES = {
        "maría", "maria", "ana", "carmen", "laura", "marta", "elena", "sara",
        "paula", "lucía", "lucia", "sofía", "sofia", "isabel", "rosa", "pilar",
        "teresa", "julia", "clara", "alicia", "beatriz", "andrea", "cristina",
        "diana", "eva", "irene", "lorena", "nuria", "olga", "patricia", "raquel",
        "silvia", "susana", "verónica", "veronica", "virginia", "inés", "ines",
    }

    MASCULINE_NAMES = {
        "juan", "pedro", "carlos", "miguel", "josé", "jose", "antonio", "manuel",
        "francisco", "david", "jorge", "pablo", "andrés", "andres", "luis",
        "javier", "sergio", "fernando", "alejandro", "alberto", "daniel", "diego",
        "enrique", "felipe", "gabriel", "héctor", "hector", "ignacio", "jaime",
        "mario", "rafael", "ramón", "ramon", "roberto", "víctor", "victor",
    }

    def _infer_gender_number(self, text: str, token) -> tuple[Gender, Number]:
        """Infiere género y número de un token."""
        gender = Gender.UNKNOWN
        number = Number.UNKNOWN

        morph = str(token.morph)

        if "Gender=Masc" in morph:
            gender = Gender.MASCULINE
        elif "Gender=Fem" in morph:
            gender = Gender.FEMININE

        if "Number=Sing" in morph:
            number = Number.SINGULAR
        elif "Number=Plur" in morph:
            number = Number.PLURAL

        # Si spaCy no detectó género, intentar por nombre propio
        if gender == Gender.UNKNOWN:
            text_lower = text.lower().strip()
            # Extraer primera palabra (nombre) si hay varias
            first_word = text_lower.split()[0] if text_lower else ""

            if first_word in self.FEMININE_NAMES or text_lower in self.FEMININE_NAMES:
                gender = Gender.FEMININE
                logger.debug(f"Género inferido por nombre: {text} -> femenino")
            elif first_word in self.MASCULINE_NAMES or text_lower in self.MASCULINE_NAMES:
                gender = Gender.MASCULINE
                logger.debug(f"Género inferido por nombre: {text} -> masculino")
            # Heurística: nombres terminados en -a suelen ser femeninos en español
            elif first_word.endswith("a") and len(first_word) > 2:
                gender = Gender.FEMININE
                logger.debug(f"Género inferido por terminación -a: {text} -> femenino")
            # Heurística: nombres terminados en -o suelen ser masculinos
            elif first_word.endswith("o") and len(first_word) > 2:
                gender = Gender.MASCULINE
                logger.debug(f"Género inferido por terminación -o: {text} -> masculino")

        return gender, number

    def _is_valid_mention(self, text: str) -> bool:
        """
        Valida si un texto es una mención válida para correferencias.

        Filtra:
        - Saludos como "Hola Juan", "Buenos días María"
        - Frases con verbos (oraciones, no entidades)
        - Textos muy largos o con errores de segmentación
        """
        if not text or len(text) < 2:
            return False

        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        words = text_stripped.split()

        # Filtrar entidades muy largas (probablemente error de segmentación)
        if len(words) > 5 or len(text_stripped) > 50:
            return False

        # Filtrar saludos: "Hola X", "Buenos días X", etc.
        saludo_starters = {"hola", "adiós", "buenos", "buenas", "hey", "oye"}
        if words and words[0].lower() in saludo_starters:
            return False

        # Filtrar frases que contienen verbos o pronombres clíticos
        verb_indicators = {
            "se", "me", "te", "le", "lo", "la", "nos", "os", "les",
            "acerco", "acercó", "dijo", "respondió", "preguntó", "miró", "vio",
            "saludo", "saludó", "entró", "salió", "llegó", "fue", "era", "estaba",
            "tenía", "había", "hizo", "quería", "podía", "sabía",
        }
        if len(words) >= 3:
            words_lower = [w.lower() for w in words]
            if any(w in verb_indicators for w in words_lower[1:]):
                return False

        # Filtrar errores de segmentación (saltos de línea, puntuación final)
        if '\n' in text or (text_stripped and text_stripped[-1] in '.,:;!?'):
            return False

        return True

    def _is_anaphor(self, mention: Mention) -> bool:
        """Determina si una mención es anafórica."""
        return mention.mention_type in (
            MentionType.PRONOUN,
            MentionType.DEMONSTRATIVE,
            MentionType.POSSESSIVE,
        )

    def _is_potential_antecedent(self, mention: Mention) -> bool:
        """Determina si una mención puede ser antecedente."""
        return mention.mention_type in (
            MentionType.PROPER_NOUN,
            MentionType.DEFINITE_NP,
        )

    def _detect_narrator(
        self,
        text: str,
        mentions: list[Mention],
    ) -> Optional[tuple[str, Gender]]:
        """
        Detecta el nombre del narrador en primera persona usando LLM.

        El LLM analiza semánticamente el texto para identificar si hay un
        narrador en primera persona y cuál es su nombre/género.

        Returns:
            Tupla (nombre_narrador, género) o None si no se detecta
        """
        # Verificar si hay pronombres de primera persona (indicador de narrador)
        has_first_person = any(
            word in text.lower()
            for word in ["yo", " me ", " mi ", " mis ", "mí"]
        )

        if not has_first_person:
            return None

        # Usar LLM para detectar narrador semánticamente
        if CorefMethod.LLM in self._methods:
            llm_method = self._methods[CorefMethod.LLM]
            if llm_method.client and llm_method.client.is_available:
                return self._detect_narrator_with_llm(text, llm_method.client)

        # Fallback a patrones si LLM no está disponible
        return self._detect_narrator_with_patterns(text, mentions)

    def _detect_narrator_with_llm(
        self,
        text: str,
        llm_client,
    ) -> Optional[tuple[str, Gender]]:
        """Detecta el narrador usando LLM para análisis semántico."""
        # Tomar solo los primeros 2000 caracteres para eficiencia
        text_sample = text[:2000] if len(text) > 2000 else text

        prompt = f"""Analiza el siguiente texto narrativo en español.

TEXTO:
{text_sample}

PREGUNTA: ¿El texto está narrado en primera persona? Si es así, ¿el narrador se presenta o identifica con un nombre propio en algún momento?

Responde en formato:
NARRADOR_PRIMERA_PERSONA: [sí/no]
NOMBRE_NARRADOR: [nombre si se identifica, o "desconocido"]
GENERO_NARRADOR: [masculino/femenino/desconocido]
EVIDENCIA: [frase donde se identifica, si existe]"""

        try:
            response = llm_client.complete(
                prompt=prompt,
                system="Eres un experto en análisis narrativo. Detecta narradores en primera persona con precisión. Busca patrones como 'me llamo X', 'soy X', 'mi nombre es X', o cualquier forma en que el narrador revele su identidad.",
                max_tokens=200,
                temperature=0.1,
            )

            if not response:
                return None

            # Parsear respuesta
            is_first_person = "sí" in response.lower() and "NARRADOR_PRIMERA_PERSONA:" in response.upper()

            if not is_first_person:
                return None

            # Extraer nombre
            name_match = re.search(
                r"NOMBRE_NARRADOR:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ]+)",
                response,
                re.IGNORECASE
            )
            if name_match:
                name = name_match.group(1).strip()
                if name.lower() in ("desconocido", "no", "ninguno", "sin"):
                    return None

                # Extraer género
                gender = Gender.NEUTRAL
                if "GENERO_NARRADOR:" in response.upper():
                    if "femenino" in response.lower():
                        gender = Gender.FEMININE
                    elif "masculino" in response.lower():
                        gender = Gender.MASCULINE

                logger.info(f"Narrador detectado por LLM: {name} ({gender.value})")
                return (name, gender)

        except Exception as e:
            logger.debug(f"Error detectando narrador con LLM: {e}")

        return None

    def _detect_narrator_with_patterns(
        self,
        text: str,
        mentions: list[Mention],
    ) -> Optional[tuple[str, Gender]]:
        """Fallback: detecta narrador con patrones regex."""
        for pattern in NARRATOR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1)
                gender = self._infer_narrator_gender(text, name, mentions)
                logger.info(f"Narrador detectado por patrones: {name} ({gender.value})")
                return (name, gender)
        return None

    def _infer_narrator_gender(
        self,
        text: str,
        name: str,
        mentions: list[Mention],
    ) -> Gender:
        """
        Infiere el género del narrador basándose en contexto.

        Busca adjetivos y participios que concuerden con el narrador.
        """
        # Buscar patrones de género en el contexto del narrador
        # "soy una persona curiosa", "he sido tímido/tímida"
        fem_patterns = [
            r"\bsoy\s+(?:una|la)\b",
            r"\bhe\s+sido\s+\w+a\b",  # participios femeninos
            r"\bestoy\s+\w+a\b",  # adjetivos femeninos
            r"\bfui\s+\w+a\b",
            r"\bera\s+\w+a\b",
            r"\bme\s+siento\s+\w+a\b",
        ]
        masc_patterns = [
            r"\bsoy\s+(?:un|el)\b",
            r"\bhe\s+sido\s+\w+o\b",  # participios masculinos
            r"\bestoy\s+\w+o\b",  # adjetivos masculinos
            r"\bfui\s+\w+o\b",
            r"\bera\s+\w+o\b",
            r"\bme\s+siento\s+\w+o\b",
        ]

        fem_count = sum(1 for p in fem_patterns if re.search(p, text, re.IGNORECASE))
        masc_count = sum(1 for p in masc_patterns if re.search(p, text, re.IGNORECASE))

        if fem_count > masc_count:
            return Gender.FEMININE
        elif masc_count > fem_count:
            return Gender.MASCULINE

        # Intentar inferir del nombre
        if name.endswith("a"):
            return Gender.FEMININE
        elif name.endswith("o"):
            return Gender.MASCULINE

        return Gender.NEUTRAL

    def _is_in_dialogue(self, text: str, start_char: int, end_char: int) -> bool:
        """
        Determina si una posición está dentro de un diálogo.

        Detecta diálogos entre:
        - Guiones largos (—) o medios (–) o simples (-)
        - Comillas españolas («»)
        - Comillas inglesas ("")
        """
        # Buscar el inicio del contexto relevante (última línea/párrafo)
        line_start = text.rfind("\n", 0, start_char)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        line_text = text[line_start:end_char + 50] if end_char + 50 < len(text) else text[line_start:]

        # Posición relativa dentro de la línea
        rel_pos = start_char - line_start

        # Detectar si hay guion de diálogo al inicio
        line_stripped = line_text.lstrip()
        if line_stripped.startswith(("-", "—", "–")):
            # Está en línea de diálogo
            # Verificar si está después del cierre del diálogo (narrador)
            # Patrón: "- Texto del diálogo - dijo el narrador."
            # El segundo guion marca el fin del diálogo
            guion_positions = [i for i, c in enumerate(line_text) if c in "-—–"]
            if len(guion_positions) >= 2:
                # Hay apertura y cierre
                second_guion = guion_positions[1]
                if rel_pos > second_guion:
                    # Está después del cierre, es narración
                    return False
            return True

        # Detectar comillas
        # Contar comillas antes de la posición
        quotes_before = line_text[:rel_pos]
        open_spanish = quotes_before.count("«") - quotes_before.count("»")
        open_english = quotes_before.count('"') % 2  # Alternancia abrir/cerrar

        if open_spanish > 0 or open_english > 0:
            return True

        return False

    def _resolve_first_person(
        self,
        text: str,
        mentions: list[Mention],
        narrator_info: Optional[tuple[str, Gender]],
    ) -> list[tuple[Mention, Mention, float]]:
        """
        Resuelve menciones de primera persona al narrador.

        Solo asigna al narrador los pronombres que NO están en diálogo.
        """
        if not narrator_info:
            return []

        narrator_name, narrator_gender = narrator_info
        resolved = []

        # Crear mención sintética para el narrador
        narrator_mention = None
        for m in mentions:
            if m.mention_type == MentionType.PROPER_NOUN and m.text == narrator_name:
                narrator_mention = m
                break

        if not narrator_mention:
            # Buscar dónde se presenta el narrador
            for pattern in NARRATOR_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    narrator_mention = Mention(
                        text=narrator_name,
                        start_char=match.start(1),
                        end_char=match.end(1),
                        mention_type=MentionType.PROPER_NOUN,
                        gender=narrator_gender,
                        number=Number.SINGULAR,
                        sentence_idx=0,  # Se actualizará si es necesario
                    )
                    break

        if not narrator_mention:
            return []

        # Vincular pronombres de primera persona fuera de diálogo
        for m in mentions:
            if m.mention_type != MentionType.PRONOUN:
                continue

            if m.text.lower() not in FIRST_PERSON_PRONOUNS:
                continue

            # Verificar si está en diálogo
            if self._is_in_dialogue(text, m.start_char, m.end_char):
                continue  # No asignar al narrador, puede ser otro personaje

            # Asignar al narrador
            resolved.append((m, narrator_mention, 0.9))
            logger.debug(f"'{m.text}' (pos {m.start_char}) -> narrador '{narrator_name}'")

        return resolved

    def _filter_candidates(
        self,
        anaphor: Mention,
        candidates: list[Mention],
    ) -> list[Mention]:
        """Filtra candidatos válidos para una anáfora."""
        valid = []

        for candidate in candidates:
            # Debe estar antes de la anáfora
            if candidate.start_char >= anaphor.start_char:
                continue

            # Respetar límites de capítulo si está configurado
            if self.config.use_chapter_boundaries:
                if (anaphor.chapter_idx is not None and
                    candidate.chapter_idx is not None and
                    anaphor.chapter_idx != candidate.chapter_idx):
                    continue

            # Distancia máxima en oraciones
            sentence_distance = abs(anaphor.sentence_idx - candidate.sentence_idx)
            if sentence_distance > self.config.max_antecedent_distance:
                continue

            valid.append(candidate)

        return valid

    def _get_context(
        self,
        text: str,
        mention: Optional[Mention],
        window: int = 100,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> str:
        """Obtiene el contexto alrededor de una mención."""
        if mention:
            start = mention.start_char
            end = mention.end_char

        if start is None or end is None:
            return ""

        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        return text[ctx_start:ctx_end]

    def _weighted_vote(
        self,
        votes: dict[Mention, list[tuple[float, CorefMethod, str]]],
    ) -> tuple[Optional[Mention], float, dict[str, dict]]:
        """
        Realiza votación ponderada entre candidatos.

        Args:
            votes: Diccionario de candidato -> lista de (score, método, razón)

        Returns:
            (mejor_candidato, score_final, method_votes_detail)
            method_votes_detail: {method_name: {score, reasoning, weight}} para el candidato ganador
        """
        if not votes:
            return None, 0.0, {}

        candidate_scores: dict[Mention, float] = {}

        for candidate, method_votes in votes.items():
            total_weight = 0.0
            weighted_sum = 0.0

            for score, method, _ in method_votes:
                weight = self.config.method_weights.get(method, 0.1)
                weighted_sum += score * weight
                total_weight += weight

            if total_weight > 0:
                candidate_scores[candidate] = weighted_sum / total_weight

        if not candidate_scores:
            return None, 0.0, {}

        best = max(candidate_scores.items(), key=lambda x: x[1])
        best_candidate = best[0]
        best_score = best[1]

        # Construir detalle de votos del candidato ganador
        method_votes_detail: dict[str, dict] = {}
        for score, method, reasoning in votes.get(best_candidate, []):
            weight = self.config.method_weights.get(method, 0.1)
            method_votes_detail[method.value] = {
                "score": round(score, 3),
                "reasoning": reasoning,
                "weight": round(weight, 2),
                "weighted_score": round(score * weight, 3),
            }

        return best_candidate, best_score, method_votes_detail

    def _build_chains(
        self,
        resolved_pairs: list[tuple[Mention, Mention, float]],
        antecedents: list[Mention],
    ) -> list[CoreferenceChain]:
        """Construye cadenas de correferencia a partir de pares resueltos."""
        # Usar union-find para agrupar
        parent: dict[Mention, Mention] = {}

        def find(m: Mention) -> Mention:
            if m not in parent:
                parent[m] = m
            if parent[m] != m:
                parent[m] = find(parent[m])
            return parent[m]

        def union(m1: Mention, m2: Mention) -> None:
            r1, r2 = find(m1), find(m2)
            if r1 != r2:
                # Preferir el antecedente como raíz
                if m2.mention_type == MentionType.PROPER_NOUN:
                    parent[r1] = r2
                else:
                    parent[r2] = r1

        # Unir pares resueltos
        for anaphor, antecedent, _ in resolved_pairs:
            union(anaphor, antecedent)

        # Agrupar por raíz
        groups: dict[Mention, list[Mention]] = {}
        all_mentions = set()
        for anaphor, antecedent, _ in resolved_pairs:
            all_mentions.add(anaphor)
            all_mentions.add(antecedent)

        for mention in all_mentions:
            root = find(mention)
            if root not in groups:
                groups[root] = []
            if mention not in groups[root]:
                groups[root].append(mention)

        # Crear cadenas
        chains = []
        for root, members in groups.items():
            chain = CoreferenceChain(mentions=sorted(members, key=lambda m: m.start_char))

            # Calcular confianza promedio
            relevant_scores = [
                score for a, ant, score in resolved_pairs
                if a in members or ant in members
            ]
            if relevant_scores:
                chain.confidence = sum(relevant_scores) / len(relevant_scores)

            chains.append(chain)

        return chains


# =============================================================================
# Singleton y Funciones de Conveniencia
# =============================================================================

_resolver_lock = threading.Lock()
_resolver: Optional[CoreferenceVotingResolver] = None


def get_coref_resolver(config: Optional[CorefConfig] = None) -> CoreferenceVotingResolver:
    """
    Obtiene el singleton del resolutor de correferencias.

    Args:
        config: Configuración opcional

    Returns:
        Instancia del CoreferenceVotingResolver
    """
    global _resolver

    if _resolver is None:
        with _resolver_lock:
            if _resolver is None:
                _resolver = CoreferenceVotingResolver(config)

    return _resolver


def reset_coref_resolver() -> None:
    """Resetea el singleton (útil para tests)."""
    global _resolver
    with _resolver_lock:
        _resolver = None


def resolve_coreferences_voting(
    text: str,
    chapters: Optional[list[dict]] = None,
    config: Optional[CorefConfig] = None,
) -> CorefResult:
    """
    Función de conveniencia para resolver correferencias.

    Args:
        text: Texto a procesar
        chapters: Capítulos opcionales
        config: Configuración opcional

    Returns:
        CorefResult con las cadenas de correferencia
    """
    resolver = get_coref_resolver(config)
    return resolver.resolve_document(text, chapters)


def build_pronoun_resolution_map(coref_result: CorefResult) -> dict[tuple[int, int], str]:
    """
    Construye un mapa de posiciones de pronombres a sus antecedentes resueltos.

    Este mapa es útil para la extracción de atributos: cuando se encuentra
    un atributo asociado a un pronombre (ej: "Él era carpintero"), se puede
    usar este mapa para resolver "Él" a su antecedente (ej: "Juan García").

    Args:
        coref_result: Resultado de la resolución de correferencias

    Returns:
        Diccionario {(start_char, end_char): entity_name}
        Solo incluye menciones que son pronombres/demostrativos y tienen
        un antecedente resuelto (nombre propio o SN definido).

    Example:
        >>> result = resolve_coreferences_voting(text)
        >>> pronoun_map = build_pronoun_resolution_map(result)
        >>> # Si "Él" en posición (100, 102) refiere a "Juan García":
        >>> pronoun_map.get((100, 102))  # → "Juan García"
    """
    resolution_map: dict[tuple[int, int], str] = {}

    for chain in coref_result.chains:
        # Solo procesar cadenas con un main_mention válido
        if not chain.main_mention:
            continue

        main_name = chain.main_mention.strip()
        if not main_name:
            continue

        # Para cada mención en la cadena que NO sea el nombre principal
        for mention in chain.mentions:
            # Solo mapear pronombres, demostrativos y posesivos
            if mention.mention_type in (
                MentionType.PRONOUN,
                MentionType.DEMONSTRATIVE,
                MentionType.POSSESSIVE,
                MentionType.ZERO,
            ):
                key = (mention.start_char, mention.end_char)
                resolution_map[key] = main_name

    logger.debug(
        f"Mapa de resolución construido: {len(resolution_map)} pronombres mapeados"
    )
    return resolution_map


def resolve_entity_name(
    entity_name: str,
    position: tuple[int, int],
    pronoun_map: dict[tuple[int, int], str],
) -> str:
    """
    Resuelve un nombre de entidad usando el mapa de correferencias.

    Si el nombre es un pronombre y tenemos su posición en el mapa,
    devuelve el nombre del antecedente. En caso contrario, devuelve
    el nombre original.

    Args:
        entity_name: Nombre de la entidad (puede ser pronombre)
        position: Posición (start_char, end_char) en el texto
        pronoun_map: Mapa de resolución de pronombres

    Returns:
        Nombre resuelto o el original si no se puede resolver
    """
    # Pronombres comunes en español
    PRONOUNS = {
        "él", "ella", "ellos", "ellas",
        "este", "esta", "esto", "estos", "estas",
        "ese", "esa", "eso", "esos", "esas",
        "aquel", "aquella", "aquello", "aquellos", "aquellas",
        "su", "sus", "suyo", "suya", "suyos", "suyas",
        "lo", "la", "los", "las", "le", "les",
    }

    # Si es un pronombre conocido, intentar resolver
    if entity_name.lower() in PRONOUNS:
        resolved = pronoun_map.get(position)
        if resolved:
            logger.debug(f"Pronombre '{entity_name}' resuelto a '{resolved}'")
            return resolved

    return entity_name
