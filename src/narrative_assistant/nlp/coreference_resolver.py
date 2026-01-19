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
SPANISH_PRONOUNS = {
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
    # Posesivos tónicos
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
        """Encuentra la mención más informativa."""
        priority = {
            MentionType.PROPER_NOUN: 4,
            MentionType.DEFINITE_NP: 3,
            MentionType.DEMONSTRATIVE: 2,
            MentionType.POSSESSIVE: 1,
            MentionType.PRONOUN: 0,
            MentionType.ZERO: -1,
        }

        if not self.mentions:
            return ""

        sorted_mentions = sorted(
            self.mentions,
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
class CorefResult:
    """
    Resultado de la resolución de correferencias.

    Attributes:
        chains: Cadenas de correferencia detectadas
        unresolved: Menciones que no pudieron resolverse
        method_contributions: Contribución de cada método
        processing_time_ms: Tiempo de procesamiento
    """
    chains: list[CoreferenceChain] = field(default_factory=list)
    unresolved: list[Mention] = field(default_factory=list)
    method_contributions: dict[CorefMethod, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    @property
    def total_mentions(self) -> int:
        return sum(len(c.mentions) for c in self.chains)

    @property
    def total_chains(self) -> int:
        return len(self.chains)


@dataclass
class CorefConfig:
    """Configuración del sistema de correferencias."""
    enabled_methods: list[CorefMethod] = field(default_factory=lambda: list(CorefMethod))
    method_weights: dict[CorefMethod, float] = field(default_factory=lambda: DEFAULT_COREF_WEIGHTS.copy())
    min_confidence: float = 0.5
    consensus_threshold: float = 0.6  # Mínimo % de métodos que deben acordar
    max_antecedent_distance: int = 5  # Máx oraciones hacia atrás
    use_chapter_boundaries: bool = True  # Respetar límites de capítulo
    ollama_model: str = "llama3.2"  # Modelo LLM por defecto
    ollama_timeout: int = 30  # Timeout para LLM


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
                similarity = self.embeddings.compute_similarity(
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

    def __init__(self, model: str = "llama3.2", timeout: int = 30):
        self.model = model
        self.timeout = timeout
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
                system_prompt="Eres un experto en análisis lingüístico del español. Tu tarea es resolver correferencias (determinar a quién o qué se refiere un pronombre o expresión).",
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

            # Posesivos típicamente refieren al sujeto activo
            if anaphor.mention_type == MentionType.POSSESSIVE:
                if candidate.mention_type == MentionType.PROPER_NOUN:
                    score += 0.15
                    reasons.append("posesivo → nombre")

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

        # Separar anáforas y posibles antecedentes
        anaphors = [m for m in mentions if self._is_anaphor(m)]
        potential_antecedents = [m for m in mentions if self._is_potential_antecedent(m)]

        logger.info(f"Anáforas: {len(anaphors)}, Antecedentes potenciales: {len(potential_antecedents)}")

        # Resolver cada anáfora
        resolved_pairs: list[tuple[Mention, Mention, float]] = []

        for anaphor in anaphors:
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
            best_candidate, final_score = self._weighted_vote(all_votes)

            if best_candidate and final_score >= self.config.min_confidence:
                resolved_pairs.append((anaphor, best_candidate, final_score))

                # Registrar contribución de métodos
                for score, method, _ in all_votes.get(best_candidate, []):
                    result.method_contributions[method] = \
                        result.method_contributions.get(method, 0) + 1
            else:
                result.unresolved.append(anaphor)

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

        # Extraer entidades nombradas (nombres propios)
        for ent in doc.ents:
            if ent.label_ in ("PER", "PERSON", "LOC", "ORG"):
                gender, number = self._infer_gender_number(ent.text, doc[ent.start])
                mentions.append(Mention(
                    text=ent.text,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    mention_type=MentionType.PROPER_NOUN,
                    gender=gender,
                    number=number,
                    sentence_idx=ent.sent.start if ent.sent else 0,
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
                    sentence_idx=token.sent.start if token.sent else 0,
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
                    sentence_idx=token.sent.start if token.sent else 0,
                    chapter_idx=get_chapter_idx(token.idx),
                ))

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

        mentions.sort(key=lambda m: m.start_char)
        return mentions

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

        return gender, number

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
    ) -> tuple[Optional[Mention], float]:
        """
        Realiza votación ponderada entre candidatos.

        Args:
            votes: Diccionario de candidato -> lista de (score, método, razón)

        Returns:
            (mejor_candidato, score_final)
        """
        if not votes:
            return None, 0.0

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
            return None, 0.0

        best = max(candidate_scores.items(), key=lambda x: x[1])
        return best[0], best[1]

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
