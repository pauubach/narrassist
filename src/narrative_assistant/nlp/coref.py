"""
Resolución de Correferencias para textos narrativos en español.

Utiliza Coreferee con spaCy para resolver correferencias (pronombres,
descripciones definidas) y agrupar menciones de la misma entidad.

Limitaciones conocidas:
- F1 esperado: ~45-55% (textos literarios)
- Pro-drop hace ~40-50% de sujetos invisibles
- Fusión manual (STEP 2.2) es OBLIGATORIA para resultados confiables

Heurísticas adicionales:
- Concordancia de género (él/ella)
- Concordancia de número (ellos/ellas)
- Proximidad textual para desambiguación
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum

from ..core.errors import ErrorSeverity, NLPError
from ..core.result import Result
from .spacy_gpu import load_spacy_model

logger = logging.getLogger(__name__)


class MentionType(Enum):
    """Tipo de mención en una cadena de correferencia."""

    PROPER_NOUN = "proper_noun"  # Nombre propio: "Juan", "María García"
    PRONOUN = "pronoun"  # Pronombre: "él", "ella", "ellos"
    DEFINITE_NP = "definite_np"  # Sintagma nominal definido: "el doctor", "la mujer"
    DEMONSTRATIVE = "demonstrative"  # Demostrativo: "este", "aquella"
    ZERO = "zero"  # Sujeto omitido (pro-drop) - detectado por contexto


class GrammaticalGender(Enum):
    """Género gramatical para concordancia."""

    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTRAL = "neutral"  # Indeterminado o neutro
    UNKNOWN = "unknown"


class GrammaticalNumber(Enum):
    """Número gramatical para concordancia."""

    SINGULAR = "singular"
    PLURAL = "plural"
    UNKNOWN = "unknown"


@dataclass
class Mention:
    """
    Una mención individual dentro de una cadena de correferencia.

    Attributes:
        text: Texto de la mención
        start_char: Posición de inicio en el texto original
        end_char: Posición de fin en el texto original
        mention_type: Tipo de mención (pronombre, nombre propio, etc.)
        gender: Género gramatical detectado
        number: Número gramatical detectado
        head_index: Índice del token cabeza en el documento spaCy
        confidence: Confianza de la detección (0.0-1.0)
    """

    text: str
    start_char: int
    end_char: int
    mention_type: MentionType
    gender: GrammaticalGender = GrammaticalGender.UNKNOWN
    number: GrammaticalNumber = GrammaticalNumber.UNKNOWN
    head_index: int = -1
    confidence: float = 0.8

    @property
    def char_span(self) -> tuple[int, int]:
        """Retorna el span de caracteres como tupla."""
        return (self.start_char, self.end_char)

    def __hash__(self) -> int:
        return hash((self.text, self.start_char, self.end_char))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mention):
            return False
        return (
            self.text == other.text
            and self.start_char == other.start_char
            and self.end_char == other.end_char
        )


@dataclass
class CoreferenceChain:
    """
    Una cadena de menciones que refieren a la misma entidad.

    Attributes:
        mentions: Lista de menciones ordenadas por posición
        main_mention: La mención más informativa (nombre completo)
        entity_id: ID opcional de entidad NER asociada
        confidence: Confianza promedio de la cadena
    """

    mentions: list[Mention] = field(default_factory=list)
    main_mention: str | None = None
    entity_id: str | None = None
    confidence: float = 0.5

    def __post_init__(self):
        """Calcula la mención principal si no está especificada."""
        if self.mentions and self.main_mention is None:
            self.main_mention = self._find_main_mention()
        if self.mentions:
            self.confidence = sum(m.confidence for m in self.mentions) / len(self.mentions)

    def _find_main_mention(self) -> str:
        """
        Encuentra la mención más informativa de la cadena.

        Prioriza: nombres propios > sintagmas nominales > pronombres
        Dentro de cada tipo, prefiere el texto más largo.
        """
        priority = {
            MentionType.PROPER_NOUN: 4,
            MentionType.DEFINITE_NP: 3,
            MentionType.DEMONSTRATIVE: 2,
            MentionType.PRONOUN: 1,
            MentionType.ZERO: 0,
        }

        if not self.mentions:
            return ""

        # Ordenar por prioridad de tipo y longitud
        sorted_mentions = sorted(
            self.mentions,
            key=lambda m: (priority.get(m.mention_type, 0), len(m.text)),
            reverse=True,
        )

        return sorted_mentions[0].text

    @property
    def all_texts(self) -> list[str]:
        """Retorna todos los textos de las menciones."""
        return [m.text for m in self.mentions]

    @property
    def span_range(self) -> tuple[int, int]:
        """Retorna el rango completo cubierto por la cadena."""
        if not self.mentions:
            return (0, 0)
        starts = [m.start_char for m in self.mentions]
        ends = [m.end_char for m in self.mentions]
        return (min(starts), max(ends))

    def add_mention(self, mention: Mention) -> None:
        """Añade una mención a la cadena manteniendo orden por posición."""
        self.mentions.append(mention)
        self.mentions.sort(key=lambda m: m.start_char)
        # Recalcular mención principal
        self.main_mention = self._find_main_mention()
        self.confidence = sum(m.confidence for m in self.mentions) / len(self.mentions)


@dataclass
class CoreferenceResult:
    """
    Resultado de la resolución de correferencias.

    Attributes:
        chains: Lista de cadenas de correferencia detectadas
        processed_chars: Caracteres procesados
        unresolved_pronouns: Pronombres que no pudieron resolverse
    """

    chains: list[CoreferenceChain] = field(default_factory=list)
    processed_chars: int = 0
    unresolved_pronouns: list[Mention] = field(default_factory=list)

    @property
    def total_mentions(self) -> int:
        """Total de menciones en todas las cadenas."""
        return sum(len(chain.mentions) for chain in self.chains)

    @property
    def average_chain_length(self) -> float:
        """Longitud promedio de las cadenas."""
        if not self.chains:
            return 0.0
        return self.total_mentions / len(self.chains)

    def get_chain_for_position(self, char_pos: int) -> CoreferenceChain | None:
        """Encuentra la cadena que contiene una posición de caracter."""
        for chain in self.chains:
            for mention in chain.mentions:
                if mention.start_char <= char_pos < mention.end_char:
                    return chain
        return None


@dataclass
class CoreferenceError(NLPError):
    """Error durante la resolución de correferencias."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: str | None = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Coreference resolution error: {self.original_error}"
        self.user_message = (
            "Error al resolver correferencias. Se continuará con resultados parciales."
        )
        super().__post_init__()


# =============================================================================
# Mapas de género y número para heurísticas
# =============================================================================

# Pronombres personales con su género y número
PRONOUN_FEATURES: dict[str, tuple[GrammaticalGender, GrammaticalNumber]] = {
    # Sujeto
    "él": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "ella": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "ellos": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "ellas": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
    # Objeto
    "lo": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "la": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "los": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "las": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
    "le": (GrammaticalGender.NEUTRAL, GrammaticalNumber.SINGULAR),
    "les": (GrammaticalGender.NEUTRAL, GrammaticalNumber.PLURAL),
    # Reflexivos
    "se": (GrammaticalGender.NEUTRAL, GrammaticalNumber.UNKNOWN),
    # Posesivos tónicos
    "suyo": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "suya": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "suyos": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "suyas": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
}

# Artículos definidos para detectar género en sintagmas nominales
DEFINITE_ARTICLES: dict[str, tuple[GrammaticalGender, GrammaticalNumber]] = {
    "el": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "la": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "los": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "las": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
}

# Demostrativos
DEMONSTRATIVES: dict[str, tuple[GrammaticalGender, GrammaticalNumber]] = {
    "este": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "esta": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "estos": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "estas": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
    "ese": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "esa": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "esos": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "esas": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
    "aquel": (GrammaticalGender.MASCULINE, GrammaticalNumber.SINGULAR),
    "aquella": (GrammaticalGender.FEMININE, GrammaticalNumber.SINGULAR),
    "aquellos": (GrammaticalGender.MASCULINE, GrammaticalNumber.PLURAL),
    "aquellas": (GrammaticalGender.FEMININE, GrammaticalNumber.PLURAL),
}


class CoreferenceResolver:
    """
    Resolutor de correferencias para español usando Coreferee.

    Combina el modelo de Coreferee con heurísticas adicionales de
    concordancia de género y número para mejorar la precisión.

    Attributes:
        nlp: Pipeline de spaCy con Coreferee
        use_heuristics: Usar heurísticas adicionales de género/número
    """

    def __init__(
        self,
        use_heuristics: bool = True,
        enable_gpu: bool | None = None,
    ):
        """
        Inicializa el resolutor de correferencias.

        Args:
            use_heuristics: Habilitar heurísticas de género/número
            enable_gpu: Usar GPU para spaCy (None = auto)
        """
        self.use_heuristics = use_heuristics
        self._coreferee_available = False

        # Cargar modelo spaCy
        logger.info("Cargando modelo spaCy para correferencia...")
        self.nlp = load_spacy_model(enable_gpu=enable_gpu)

        # Intentar añadir Coreferee
        self._setup_coreferee()

    def _setup_coreferee(self) -> None:
        """Configura Coreferee si está disponible."""
        try:
            # Verificar si coreferee ya está en el pipeline
            if "coreferee" not in self.nlp.pipe_names:
                self.nlp.add_pipe("coreferee")
            self._coreferee_available = True
            logger.info("Coreferee configurado correctamente")
        except Exception as e:
            logger.warning(f"Coreferee no disponible, usando solo heurísticas: {e}")
            self._coreferee_available = False

    def resolve(self, text: str) -> Result[CoreferenceResult]:
        """
        Resuelve correferencias en el texto.

        Args:
            text: Texto a procesar

        Returns:
            Result con CoreferenceResult conteniendo las cadenas detectadas
        """
        if not text or not text.strip():
            return Result.success(CoreferenceResult(processed_chars=0))

        result = CoreferenceResult(processed_chars=len(text))
        errors: list[NLPError] = []

        try:
            doc = self.nlp(text)

            # 1. Obtener cadenas de Coreferee (si disponible)
            if self._coreferee_available:
                coreferee_chains = self._extract_coreferee_chains(doc)
                result.chains.extend(coreferee_chains)

            # 2. Aplicar heurísticas adicionales
            if self.use_heuristics:
                # Detectar pronombres no resueltos
                unresolved = self._find_unresolved_pronouns(doc, result.chains)
                result.unresolved_pronouns.extend(unresolved)

                # Intentar resolver con heurísticas de género/número
                self._apply_gender_number_heuristics(doc, result)

            logger.debug(
                f"Correferencias resueltas: {len(result.chains)} cadenas, "
                f"{result.total_mentions} menciones, "
                f"{len(result.unresolved_pronouns)} pronombres sin resolver"
            )

            if errors:
                return Result.partial(result, errors)
            return Result.success(result)

        except Exception as e:
            error = CoreferenceError(
                text_sample=text[:100] if len(text) > 100 else text,
                original_error=str(e),
            )
            logger.error(f"Error en resolución de correferencias: {e}")
            return Result.partial(result, [error])

    def _extract_coreferee_chains(self, doc) -> list[CoreferenceChain]:
        """Extrae cadenas de correferencia de Coreferee."""
        chains: list[CoreferenceChain] = []

        if not hasattr(doc._, "coref_chains") or doc._.coref_chains is None:
            return chains

        for coref_chain in doc._.coref_chains:
            chain = CoreferenceChain()

            for mention_idx in coref_chain:
                # Coreferee puede dar índices individuales o listas
                if hasattr(mention_idx, "__iter__") and not isinstance(mention_idx, int):
                    # Es una lista de índices (mención multi-token)
                    indices = list(mention_idx)
                    if not indices:
                        continue
                    start_token = doc[indices[0]]
                    end_token = doc[indices[-1]]
                    text = doc[indices[0] : indices[-1] + 1].text
                    head_idx = indices[0]
                else:
                    # Es un índice individual
                    token = doc[mention_idx]
                    start_token = token
                    end_token = token
                    text = token.text
                    head_idx = mention_idx

                # Determinar tipo de mención
                mention_type = self._classify_mention_type(start_token)

                # Obtener género y número
                gender, number = self._get_grammatical_features(start_token, text)

                mention = Mention(
                    text=text,
                    start_char=start_token.idx,
                    end_char=end_token.idx + len(end_token.text),
                    mention_type=mention_type,
                    gender=gender,
                    number=number,
                    head_index=head_idx,
                    confidence=0.7,  # Confianza base de Coreferee
                )

                chain.add_mention(mention)

            if chain.mentions:
                chains.append(chain)

        return chains

    def _classify_mention_type(self, token) -> MentionType:
        """Clasifica el tipo de mención basándose en el token."""
        text_lower = token.text.lower()

        # Pronombre
        if text_lower in PRONOUN_FEATURES or token.pos_ == "PRON":
            return MentionType.PRONOUN

        # Demostrativo
        if text_lower in DEMONSTRATIVES:
            return MentionType.DEMONSTRATIVE

        # Nombre propio
        if token.pos_ == "PROPN" or token.ent_type_ in ("PER", "PERSON"):
            return MentionType.PROPER_NOUN

        # Sintagma nominal definido (empieza con artículo definido)
        if token.pos_ == "DET" and text_lower in DEFINITE_ARTICLES:
            return MentionType.DEFINITE_NP

        # Por defecto, sintagma nominal
        return MentionType.DEFINITE_NP

    def _get_grammatical_features(
        self, token, text: str
    ) -> tuple[GrammaticalGender, GrammaticalNumber]:
        """Obtiene género y número de una mención."""
        text_lower = text.lower().strip()

        # Buscar en mapas conocidos
        if text_lower in PRONOUN_FEATURES:
            return PRONOUN_FEATURES[text_lower]

        if text_lower in DEMONSTRATIVES:
            return DEMONSTRATIVES[text_lower]

        # Inferir de morfología de spaCy
        gender = GrammaticalGender.UNKNOWN
        number = GrammaticalNumber.UNKNOWN

        morph = token.morph

        # Género
        if "Gender=Masc" in str(morph):
            gender = GrammaticalGender.MASCULINE
        elif "Gender=Fem" in str(morph):
            gender = GrammaticalGender.FEMININE

        # Número
        if "Number=Sing" in str(morph):
            number = GrammaticalNumber.SINGULAR
        elif "Number=Plur" in str(morph):
            number = GrammaticalNumber.PLURAL

        return gender, number

    def _find_unresolved_pronouns(self, doc, chains: list[CoreferenceChain]) -> list[Mention]:
        """Encuentra pronombres que no están en ninguna cadena."""
        # Construir set de posiciones ya resueltas
        resolved_positions: set[tuple[int, int]] = set()
        for chain in chains:
            for mention in chain.mentions:
                resolved_positions.add((mention.start_char, mention.end_char))

        unresolved: list[Mention] = []

        for token in doc:
            text_lower = token.text.lower()

            # Solo pronombres de 3ra persona (los que refieren a otros)
            if text_lower in PRONOUN_FEATURES:
                pos = (token.idx, token.idx + len(token.text))

                if pos not in resolved_positions:
                    gender, number = PRONOUN_FEATURES[text_lower]
                    mention = Mention(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        mention_type=MentionType.PRONOUN,
                        gender=gender,
                        number=number,
                        head_index=token.i,
                        confidence=0.5,
                    )
                    unresolved.append(mention)

        return unresolved

    def _apply_gender_number_heuristics(self, doc, result: CoreferenceResult) -> None:
        """
        Aplica heurísticas de concordancia de género/número.

        Intenta asignar pronombres no resueltos a cadenas existentes
        basándose en concordancia gramatical y proximidad.
        """
        if not result.unresolved_pronouns or not result.chains:
            return

        # Para cada pronombre no resuelto
        still_unresolved: list[Mention] = []

        for pronoun in result.unresolved_pronouns:
            best_chain: CoreferenceChain | None = None
            best_score = 0.0

            for chain in result.chains:
                score = self._compute_compatibility_score(pronoun, chain)

                if score > best_score and score > 0.5:  # Umbral mínimo
                    best_score = score
                    best_chain = chain

            if best_chain is not None:
                pronoun.confidence = best_score
                best_chain.add_mention(pronoun)
                logger.debug(
                    f"Heurística: '{pronoun.text}' -> cadena '{best_chain.main_mention}' "
                    f"(score={best_score:.2f})"
                )
            else:
                still_unresolved.append(pronoun)

        result.unresolved_pronouns = still_unresolved

    def _compute_compatibility_score(self, pronoun: Mention, chain: CoreferenceChain) -> float:
        """
        Calcula score de compatibilidad entre pronombre y cadena.

        Factores:
        - Concordancia de género (0.4)
        - Concordancia de número (0.3)
        - Proximidad textual (0.3)
        """
        score = 0.0

        # Obtener features dominantes de la cadena
        chain_gender = self._get_chain_gender(chain)
        chain_number = self._get_chain_number(chain)

        # Concordancia de género (0.4 puntos)
        if pronoun.gender != GrammaticalGender.UNKNOWN:
            if pronoun.gender == chain_gender:
                score += 0.4
            elif chain_gender == GrammaticalGender.UNKNOWN:
                score += 0.2  # Parcial si la cadena no tiene género claro
            elif pronoun.gender == GrammaticalGender.NEUTRAL:
                score += 0.2  # Neutral es compatible con todo
            # else: no concuerda, 0 puntos

        # Concordancia de número (0.3 puntos)
        if pronoun.number != GrammaticalNumber.UNKNOWN:
            if pronoun.number == chain_number:
                score += 0.3
            elif chain_number == GrammaticalNumber.UNKNOWN:
                score += 0.15  # Parcial
            # else: no concuerda, 0 puntos

        # Proximidad (0.3 puntos)
        # Buscar la mención más cercana anterior al pronombre
        closest_distance = float("inf")
        for mention in chain.mentions:
            if mention.end_char < pronoun.start_char:
                distance = pronoun.start_char - mention.end_char
                closest_distance = min(closest_distance, distance)

        if closest_distance < float("inf"):
            # Escala: 0-100 chars = full score, >1000 chars = 0
            proximity_score = max(0, 1 - (closest_distance / 1000))
            score += 0.3 * proximity_score

        return score

    def _get_chain_gender(self, chain: CoreferenceChain) -> GrammaticalGender:
        """Obtiene el género dominante de una cadena."""
        gender_counts: dict[GrammaticalGender, int] = {}

        for mention in chain.mentions:
            if mention.gender != GrammaticalGender.UNKNOWN:
                gender_counts[mention.gender] = gender_counts.get(mention.gender, 0) + 1

        if not gender_counts:
            return GrammaticalGender.UNKNOWN

        return max(gender_counts, key=lambda g: gender_counts[g])

    def _get_chain_number(self, chain: CoreferenceChain) -> GrammaticalNumber:
        """Obtiene el número dominante de una cadena."""
        number_counts: dict[GrammaticalNumber, int] = {}

        for mention in chain.mentions:
            if mention.number != GrammaticalNumber.UNKNOWN:
                number_counts[mention.number] = number_counts.get(mention.number, 0) + 1

        if not number_counts:
            return GrammaticalNumber.UNKNOWN

        return max(number_counts, key=lambda n: number_counts[n])

    def merge_with_entities(
        self,
        entities: list,
        chains: list[CoreferenceChain],
    ) -> dict[str, list]:
        """
        Agrupa entidades NER por cadena de correferencia.

        Args:
            entities: Lista de ExtractedEntity del NER
            chains: Cadenas de correferencia

        Returns:
            Dict con 'grouped' (entidades agrupadas por chain_id) y
            'ungrouped' (entidades sin cadena)
        """
        # Mapear cada mención a su cadena
        mention_to_chain: dict[tuple[int, int], int] = {}
        for i, chain in enumerate(chains):
            for mention in chain.mentions:
                mention_to_chain[(mention.start_char, mention.end_char)] = i

        # Agrupar entidades
        grouped: dict[int, list] = {}
        ungrouped: list = []

        for entity in entities:
            # Buscar por posición exacta o por solapamiento
            chain_id = mention_to_chain.get((entity.start_char, entity.end_char))

            # Si no hay match exacto, buscar solapamiento
            if chain_id is None:
                for (start, end), cid in mention_to_chain.items():
                    # Solapamiento parcial
                    if (
                        start <= entity.start_char < end
                        or start < entity.end_char <= end
                        or (entity.start_char <= start and entity.end_char >= end)
                    ):
                        chain_id = cid
                        break

            if chain_id is not None:
                if chain_id not in grouped:
                    grouped[chain_id] = []
                grouped[chain_id].append(entity)
            else:
                ungrouped.append(entity)

        return {"grouped": grouped, "ungrouped": ungrouped, "chains": chains}


# =============================================================================
# Singleton thread-safe
# =============================================================================

_coref_lock = threading.Lock()
_coref_resolver: CoreferenceResolver | None = None


def get_coref_resolver(
    use_heuristics: bool = True,
    enable_gpu: bool | None = None,
) -> CoreferenceResolver:
    """
    Obtiene el singleton del resolutor de correferencias.

    Args:
        use_heuristics: Habilitar heurísticas adicionales
        enable_gpu: Usar GPU (None = auto)

    Returns:
        Instancia única del CoreferenceResolver
    """
    global _coref_resolver

    if _coref_resolver is None:
        with _coref_lock:
            if _coref_resolver is None:
                _coref_resolver = CoreferenceResolver(
                    use_heuristics=use_heuristics,
                    enable_gpu=enable_gpu,
                )

    return _coref_resolver


def reset_coref_resolver() -> None:
    """Resetea el singleton (útil para tests)."""
    global _coref_resolver
    with _coref_lock:
        _coref_resolver = None


def resolve_coreferences(text: str) -> Result[CoreferenceResult]:
    """
    Atajo para resolver correferencias de un texto.

    Args:
        text: Texto a procesar

    Returns:
        Result con CoreferenceResult
    """
    return get_coref_resolver().resolve(text)
