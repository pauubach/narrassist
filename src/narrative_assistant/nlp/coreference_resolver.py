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
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# Enums y Constantes
# =============================================================================


class MentionType(Enum):
    """Tipo de mención en el texto."""

    PROPER_NOUN = "proper_noun"  # Nombre propio: "Juan", "María García"
    PRONOUN = "pronoun"  # Pronombre: "él", "ella", "ellos"
    DEFINITE_NP = "definite_np"  # SN definido: "el doctor", "la mujer"
    DEMONSTRATIVE = "demonstrative"  # Demostrativo: "este", "aquella"
    POSSESSIVE = "possessive"  # Posesivo: "su hermano", "sus ojos"
    ZERO = "zero"  # Sujeto omitido (pro-drop)


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

    EMBEDDINGS = "embeddings"  # Similitud semántica
    LLM = "llm"  # LLM local (Ollama)
    MORPHO = "morpho"  # Análisis morfosintáctico
    HEURISTICS = "heuristics"  # Heurísticas narrativas
    TRANSFORMER = "transformer"  # Modelo transformer fine-tuned (futuro)


# Pesos por defecto para votación
DEFAULT_COREF_WEIGHTS = {
    CorefMethod.EMBEDDINGS: 0.30,
    CorefMethod.LLM: 0.35,
    CorefMethod.MORPHO: 0.20,
    CorefMethod.HEURISTICS: 0.15,
}


# =============================================================================
# S2-04: Pesos Adaptativos
# =============================================================================

_ADAPTIVE_WEIGHTS_FILE = "adaptive_coref_weights.json"


def _get_adaptive_weights_path() -> Path:
    """Retorna la ruta del archivo de pesos adaptativos."""
    import os

    data_dir = os.environ.get("NA_DATA_DIR", "")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path.home() / ".narrative_assistant"
    base.mkdir(parents=True, exist_ok=True)
    return base / _ADAPTIVE_WEIGHTS_FILE


def load_adaptive_weights() -> dict[CorefMethod, float] | None:
    """
    Carga pesos adaptativos desde disco.

    Returns:
        Dict de pesos si existen, None si no hay pesos guardados.
    """
    import json

    path = _get_adaptive_weights_path()
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        weights = {}
        for key, value in data.get("weights", {}).items():
            try:
                method = CorefMethod(key)
                weights[method] = float(value)
            except (ValueError, KeyError):
                continue

        if weights:
            logger.info(f"Pesos adaptativos cargados: {weights}")
            return weights
    except Exception as e:
        logger.debug(f"No se pudieron cargar pesos adaptativos: {e}")

    return None


def save_adaptive_weights(
    weights: dict[CorefMethod, float],
    feedback_count: int = 0,
) -> None:
    """
    Guarda pesos adaptativos a disco.

    Args:
        weights: Pesos actuales por método
        feedback_count: Número total de feedbacks recibidos
    """
    import json
    from datetime import datetime

    path = _get_adaptive_weights_path()
    data = {
        "weights": {m.value: round(w, 4) for m, w in weights.items()},
        "feedback_count": feedback_count,
        "updated_at": datetime.now().isoformat(),
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Pesos adaptativos guardados en {path}")
    except Exception as e:
        logger.warning(f"No se pudieron guardar pesos adaptativos: {e}")


def update_adaptive_weights(
    current_weights: dict[CorefMethod, float],
    correct_method: CorefMethod | None,
    incorrect_methods: list[CorefMethod] | None = None,
    learning_rate: float = 0.05,
) -> dict[CorefMethod, float]:
    """
    Actualiza pesos basándose en feedback del usuario.

    Cuando el usuario confirma o corrige una resolución de correferencia,
    se ajustan los pesos de los métodos que acertaron/fallaron.

    Args:
        current_weights: Pesos actuales
        correct_method: Método que acertó (se incrementa su peso)
        incorrect_methods: Métodos que fallaron (se decrementan)
        learning_rate: Tasa de aprendizaje (default 0.05)

    Returns:
        Nuevos pesos normalizados
    """
    new_weights = current_weights.copy()

    if correct_method and correct_method in new_weights:
        new_weights[correct_method] += learning_rate

    for method in (incorrect_methods or []):
        if method in new_weights:
            new_weights[method] = max(0.05, new_weights[method] - learning_rate * 0.5)

    # Normalizar para que sumen 1.0
    total = sum(new_weights.values())
    if total > 0:
        new_weights = {m: w / total for m, w in new_weights.items()}

    return new_weights

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
    "vos": (Gender.NEUTRAL, Number.SINGULAR),  # Voseo rioplatense
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
    "mi": (Gender.NEUTRAL, Number.SINGULAR),  # átono
    "mis": (Gender.NEUTRAL, Number.PLURAL),  # átono plural
    "mío": (Gender.MASCULINE, Number.SINGULAR),  # tónico
    "mía": (Gender.FEMININE, Number.SINGULAR),  # tónico
    "míos": (Gender.MASCULINE, Number.PLURAL),  # tónico
    "mías": (Gender.FEMININE, Number.PLURAL),  # tónico
    "nuestro": (Gender.MASCULINE, Number.SINGULAR),
    "nuestra": (Gender.FEMININE, Number.SINGULAR),
    "nuestros": (Gender.MASCULINE, Number.PLURAL),
    "nuestras": (Gender.FEMININE, Number.PLURAL),
    # Segunda persona
    "tu": (Gender.NEUTRAL, Number.SINGULAR),  # átono
    "tus": (Gender.NEUTRAL, Number.PLURAL),  # átono plural
    "tuyo": (Gender.MASCULINE, Number.SINGULAR),  # tónico
    "tuya": (Gender.FEMININE, Number.SINGULAR),  # tónico
    "tuyos": (Gender.MASCULINE, Number.PLURAL),  # tónico
    "tuyas": (Gender.FEMININE, Number.PLURAL),  # tónico
    "vuestro": (Gender.MASCULINE, Number.SINGULAR),
    "vuestra": (Gender.FEMININE, Number.SINGULAR),
    "vuestros": (Gender.MASCULINE, Number.PLURAL),
    "vuestras": (Gender.FEMININE, Number.PLURAL),
    # Tercera persona (de él/ella/ellos/ellas/usted/ustedes)
    "su": (Gender.NEUTRAL, Number.SINGULAR),  # átono (más común)
    "sus": (Gender.NEUTRAL, Number.PLURAL),  # átono plural
    "suyo": (Gender.MASCULINE, Number.SINGULAR),  # tónico
    "suya": (Gender.FEMININE, Number.SINGULAR),  # tónico
    "suyos": (Gender.MASCULINE, Number.PLURAL),  # tónico
    "suyas": (Gender.FEMININE, Number.PLURAL),  # tónico
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
    "padre",
    "papá",
    "abuelo",
    "hijo",
    "nieto",
    "hermano",
    "tío",
    "sobrino",
    "primo",
    "cuñado",
    "suegro",
    "yerno",
    "marido",
    "esposo",
    "novio",
    # Edades/roles genéricos
    "hombre",
    "joven",
    "chico",
    "muchacho",
    "niño",
    "anciano",
    "viejo",
    "adolescente",
    "bebé",
    "adulto",
    # Profesiones/roles (masculino)
    "médico",
    "doctor",
    "abogado",
    "juez",
    "profesor",
    "maestro",
    "conductor",
    "chofer",
    "taxista",
    "piloto",
    "capitán",
    "general",
    "coronel",
    "teniente",
    "sargento",
    "soldado",
    "policía",
    "guardia",
    "jefe",
    "director",
    "gerente",
    "presidente",
    "ministro",
    "rey",
    "príncipe",
    "camarero",
    "cocinero",
    "portero",
    "conserje",
    "jardinero",
    "obrero",
    "empleado",
    "secretario",
    "asistente",
    "ayudante",
    "sacerdote",
    "cura",
    "fraile",
    "monje",
    "rabino",
    "imán",
    "escritor",
    "pintor",
    "escultor",
    "músico",
    "cantante",
    "actor",
    "detective",
    "inspector",
    "comisario",
    "fiscal",
    "testigo",
    "acusado",
    # Descriptivos
    "desconocido",
    "extraño",
    "intruso",
    "visitante",
    "huésped",
    "invitado",
    "vecino",
    "amigo",
    "enemigo",
    "rival",
    "compañero",
    "colega",
    "líder",
    "guía",
    "mentor",
    "discípulo",
    "alumno",
    "estudiante",
}

PERSON_NOUNS_FEMININE = {
    # Relaciones familiares
    "madre",
    "mamá",
    "abuela",
    "hija",
    "nieta",
    "hermana",
    "tía",
    "sobrina",
    "prima",
    "cuñada",
    "suegra",
    "nuera",
    "esposa",
    "mujer",
    "novia",
    # Edades/roles genéricos
    "joven",
    "chica",
    "muchacha",
    "niña",
    "anciana",
    "vieja",
    "adolescente",
    "adulta",
    # Profesiones/roles (femenino)
    "médica",
    "doctora",
    "abogada",
    "jueza",
    "profesora",
    "maestra",
    "conductora",
    "pilota",
    "capitana",
    "generala",
    "coronela",
    "teniente",
    "sargenta",
    "soldada",
    "policía",
    "guardia",
    "jefa",
    "directora",
    "gerenta",
    "presidenta",
    "ministra",
    "reina",
    "princesa",
    "camarera",
    "cocinera",
    "portera",
    "conserja",
    "jardinera",
    "obrera",
    "empleada",
    "secretaria",
    "asistenta",
    "ayudante",
    "monja",
    "religiosa",
    "rabina",
    "escritora",
    "pintora",
    "escultora",
    "música",
    "cantante",
    "actriz",
    "detective",
    "inspectora",
    "comisaria",
    "fiscal",
    "testigo",
    "acusada",
    # Descriptivos
    "desconocida",
    "extraña",
    "intrusa",
    "visitante",
    "huésped",
    "invitada",
    "vecina",
    "amiga",
    "enemiga",
    "rival",
    "compañera",
    "colega",
    "líder",
    "guía",
    "mentora",
    "discípula",
    "alumna",
    "estudiante",
    # Específicos femeninos
    "dama",
    "señora",
    "señorita",
    "doncella",
    "criada",
    "sirvienta",
}

# Todos los sustantivos de persona (para búsqueda rápida)
ALL_PERSON_NOUNS = PERSON_NOUNS_MASCULINE | PERSON_NOUNS_FEMININE

# Pronombres de primera persona (para detectar narrador)
FIRST_PERSON_PRONOUNS = {
    "yo",
    "me",
    "mí",
    "mi",
    "mis",
    "conmigo",
    "mío",
    "mía",
    "míos",
    "mías",
    "nosotros",
    "nosotras",
    "nos",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
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
    chapter_idx: int | None = None
    head_text: str | None = None  # Cabeza sintáctica
    context: str | None = None  # Contexto circundante

    def __hash__(self):
        return hash((self.text, self.start_char, self.end_char))

    def __eq__(self, other):
        if not isinstance(other, Mention):
            return False
        return (
            self.text == other.text
            and self.start_char == other.start_char
            and self.end_char == other.end_char
        )


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
    main_mention: str | None = None
    entity_id: int | None = None
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
            m
            for m in self.mentions
            if m.mention_type not in (MentionType.PRONOUN, MentionType.ZERO)
        ]

        # Si no hay menciones que no sean pronombres, devolver vacío
        # Una cadena con solo pronombres no tiene entidad principal identificable
        if not non_pronoun_mentions:
            return ""

        sorted_mentions = sorted(
            non_pronoun_mentions,
            key=lambda m: (priority.get(m.mention_type, 0), len(m.text)),
            reverse=True,
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


def _select_coref_model() -> str:
    """
    S2-05: Selecciona el mejor modelo LLM para correferencias en español.

    Estrategia: Qwen 2.5 es superior para tareas lingüísticas en español.
    Si está disponible en Ollama, se prefiere sobre llama3.2.
    """
    try:
        from ..llm.client import get_llm_client

        client = get_llm_client()
        if client and client.is_available:
            available = getattr(client, "_available_models", None)
            if available is None:
                # Intentar obtener modelos disponibles
                try:
                    import requests

                    resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                    if resp.status_code == 200:
                        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
                        if "qwen2.5" in models:
                            logger.info("S2-05: Usando Qwen 2.5 para correferencias (mejor español)")
                            return "qwen2.5"
                        if "mistral" in models:
                            return "mistral"
                except Exception as e:
                    logger.debug(f"Error obteniendo lista de modelos Ollama disponibles: {e}")
    except Exception as e:
        logger.debug(f"Error conectando con servidor Ollama para detectar modelo preferido: {e}")

    return "llama3.2"  # Fallback


@dataclass
class CorefConfig:
    """Configuración del sistema de correferencias."""

    enabled_methods: list[CorefMethod] = field(default_factory=_get_default_coref_methods)
    method_weights: dict[CorefMethod, float] = field(
        default_factory=lambda: DEFAULT_COREF_WEIGHTS.copy()
    )
    min_confidence: float = 0.5
    consensus_threshold: float = 0.6  # Mínimo % de métodos que deben acordar
    max_antecedent_distance: int = 5  # Máx oraciones hacia atrás
    use_chapter_boundaries: bool = True  # Respetar límites de capítulo
    ollama_model: str = "llama3.2"  # Modelo LLM por defecto
    ollama_timeout: int = 600  # 10 min - CPU sin GPU es muy lento
    use_llm_for_coref: bool = field(default=None)  # None = auto (GPU sí, CPU no)

    # S2-04: Pesos adaptativos
    use_adaptive_weights: bool = True  # Cargar pesos aprendidos si existen

    # S2-05: Preferencia de modelo para español
    prefer_spanish_model: bool = True  # Prefiere Qwen 2.5 para correferencias

    def __post_init__(self):
        """Ajusta configuración según hardware y preferencias."""
        # S2-04: Cargar pesos adaptativos si existen
        if self.use_adaptive_weights:
            adaptive = load_adaptive_weights()
            if adaptive:
                self.method_weights = adaptive
                logger.info("Usando pesos adaptativos para correferencias")

        # S2-05: Auto-seleccionar modelo preferido para español
        if self.prefer_spanish_model and self.ollama_model == "llama3.2":
            self.ollama_model = _select_coref_model()

        # Ajustar uso de LLM según hardware
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
                similarity = self.embeddings.similarity(anaphor_context, candidate_context)

                # Boost si hay concordancia de género/número
                if (
                    anaphor.gender != Gender.UNKNOWN
                    and candidate.gender != Gender.UNKNOWN
                    and anaphor.gender == candidate.gender
                ):
                    similarity *= 1.1

                if (
                    anaphor.number != Number.UNKNOWN
                    and candidate.number != Number.UNKNOWN
                    and anaphor.number == candidate.number
                ):
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
        candidates_text = "\n".join(
            [
                f'  {i + 1}. "{c.text}" (posición: {c.start_char})'
                for i, c in enumerate(candidates[:5])  # Limitar candidatos
            ]
        )

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
        self, response: str, candidates: list[Mention]
    ) -> list[tuple[Mention, float, str]]:
        """Parsea la respuesta del LLM."""
        results = []

        # Buscar número de candidato
        candidate_match = re.search(r"CANDIDATO:\s*(\d+)", response, re.IGNORECASE)
        confidence_match = re.search(r"CONFIANZA:\s*(alta|media|baja)", response, re.IGNORECASE)
        reason_match = re.search(r"RAZ[OÓ]N:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)

        if candidate_match:
            try:
                idx = int(candidate_match.group(1)) - 1
                if 0 <= idx < len(candidates):
                    # Mapear confianza
                    conf_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
                    confidence = conf_map.get(
                        confidence_match.group(1).lower() if confidence_match else "media", 0.7
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

    def __init__(self):
        # Frecuencia de menciones (se actualiza antes de resolver)
        self._mention_freq: dict[str, int] = {}

    def set_mention_frequencies(self, mentions: list["Mention"]) -> None:
        """Calcula frecuencia de nombres propios para saliencia."""
        self._mention_freq = {}
        for m in mentions:
            if m.mention_type == MentionType.PROPER_NOUN:
                key = m.text.lower()
                self._mention_freq[key] = self._mention_freq.get(key, 0) + 1

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
        most_recent_in_scope: Mention | None = None
        if anaphor.mention_type == MentionType.POSSESSIVE:
            most_recent_in_scope = self._find_most_recent_subject_candidate(anaphor, candidates)

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

            # Saliencia: preferir candidatos mencionados frecuentemente
            # (basado en frecuencia de nombre canónico en candidatos)
            if hasattr(self, '_mention_freq') and self._mention_freq:
                canonical = candidate.text.lower()
                freq = self._mention_freq.get(canonical, 0)
                if freq >= 5:
                    score += 0.15
                    reasons.append(f"alta saliencia ({freq}x)")
                elif freq >= 3:
                    score += 0.08
                    reasons.append(f"saliencia media ({freq}x)")

            # Patrones narrativos comunes
            anaphor_lower = anaphor.text.lower()

            # "él/ella" típicamente refiere al sujeto de la oración anterior
            if (
                anaphor_lower in ["él", "ella"]
                and candidate.mention_type == MentionType.PROPER_NOUN
            ):
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
            if (
                anaphor.chapter_idx is not None
                and candidate.chapter_idx is not None
                and anaphor.chapter_idx == candidate.chapter_idx
            ):
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
    ) -> Mention | None:
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

from .coref_gender import CorefGenderMixin
from .coref_mention_extraction import CorefMentionExtractionMixin
from .coref_narrator import CorefNarratorMixin
from .coref_voting import CorefVotingMixin


class CoreferenceVotingResolver(
    CorefMentionExtractionMixin,
    CorefGenderMixin,
    CorefNarratorMixin,
    CorefVotingMixin,
):
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

    def __init__(self, config: CorefConfig | None = None):
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
                model=self.config.ollama_model, timeout=self.config.ollama_timeout
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
        chapters: list[dict] | None = None,
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
            narrator_exists = any(m.text == narrator_name for m in potential_antecedents)
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

        logger.info(
            f"Anáforas: {len(anaphors)}, Antecedentes potenciales: {len(potential_antecedents)}"
        )

        # Pasar frecuencias de mención al método heurístico para saliencia
        heur_method = self._methods.get(CorefMethod.HEURISTICS)
        if heur_method and hasattr(heur_method, 'set_mention_frequencies'):
            heur_method.set_mention_frequencies(mentions)

        # Si hay narrador, resolver primero los pronombres de primera persona
        # y excluirlos de la resolución normal
        first_person_already_resolved: set[int] = set()
        if narrator_info:
            first_person_resolved = self._resolve_first_person(text, mentions, narrator_info)
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
                    result.method_contributions[method] = (
                        result.method_contributions.get(method, 0) + 1
                    )

                # Almacenar detalle de votación para esta mención
                result.voting_details[(anaphor.start_char, anaphor.end_char)] = MentionVotingDetail(
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
            first_person_resolved = self._resolve_first_person(text, mentions, narrator_info)
            for anaphor, antecedent, score in first_person_resolved:
                resolved_pairs.append((anaphor, antecedent, score))
                # Marcar como contribución del narrador (usamos HEURISTICS como indicador)
                result.method_contributions[CorefMethod.HEURISTICS] = (
                    result.method_contributions.get(CorefMethod.HEURISTICS, 0) + 1
                )

                # Detalle de votación para primera persona -> narrador
                result.voting_details[(anaphor.start_char, anaphor.end_char)] = MentionVotingDetail(
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

    # Mention extraction (full NER, simple, definite NPs, zero mentions) -> moved to coref_mention_extraction.py

    # Gender inference, validation, name dictionaries -> moved to coref_gender.py

    # Narrator detection (LLM, patterns, gender inference, dialogue detection) -> moved to coref_narrator.py

    # Resolution voting, candidate filtering, chain building -> moved to coref_voting.py


# =============================================================================
# Singleton y Funciones de Conveniencia
# =============================================================================

_resolver_lock = threading.Lock()
_resolver: CoreferenceVotingResolver | None = None


def get_coref_resolver(config: CorefConfig | None = None) -> CoreferenceVotingResolver:
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
    chapters: list[dict] | None = None,
    config: CorefConfig | None = None,
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

    logger.debug(f"Mapa de resolución construido: {len(resolution_map)} pronombres mapeados")
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
        "él",
        "ella",
        "ellos",
        "ellas",
        "este",
        "esta",
        "esto",
        "estos",
        "estas",
        "ese",
        "esa",
        "eso",
        "esos",
        "esas",
        "aquel",
        "aquella",
        "aquello",
        "aquellos",
        "aquellas",
        "su",
        "sus",
        "suyo",
        "suya",
        "suyos",
        "suyas",
        "lo",
        "la",
        "los",
        "las",
        "le",
        "les",
    }

    # Si es un pronombre conocido, intentar resolver
    if entity_name.lower() in PRONOUNS:
        resolved = pronoun_map.get(position)
        if resolved:
            logger.debug(f"Pronombre '{entity_name}' resuelto a '{resolved}'")
            return resolved

    return entity_name
