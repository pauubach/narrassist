"""
Sistema de atribucion de hablante en dialogos.

Determina quien dice que en los dialogos usando multiples estrategias:
1. Deteccion explicita (verbo de habla + nombre)
2. Alternancia (si A habla, luego B, luego probablemente A)
3. Perfil de voz (comparar estilo con perfiles conocidos)
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from ..persistence.chapter import _SCENE_BREAK_PATTERNS

logger = logging.getLogger(__name__)

# Decay de confianza por distancia de diálogos
CONFIDENCE_DECAY_RATE = 0.97  # base * 0.97^distance
CONFIDENCE_FLOOR = 0.30  # mínimo de confianza tras decay
EXPLICIT_AFTER_WINDOW = 220  # chars a inspeccionar tras el diálogo
IMPLICIT_SUBJECT_WINDOW = 260  # distancia para sujeto previo implícito
MULTI_SPEAKER_THRESHOLD = 3  # participantes mínimos para heurística multi-hablante


# Verbos de habla en espanol
SPEECH_VERBS: set[str] = {
    # Neutros - infinitivos y conjugaciones comunes
    "decir",
    "dijo",
    "dice",
    "dije",
    "dijeron",
    "decía",
    "dijiste",
    "hablar",
    "hablo",
    "habla",
    "hablaba",
    "hablaron",
    "responder",
    "respondio",
    "responde",
    "respondia",
    "respondieron",
    "contestar",
    "contesto",
    "contesta",
    "contestaba",
    "contestaron",
    "anadir",
    "anadio",
    "anade",
    "anadia",
    "agregar",
    "agrego",
    "agrega",
    "agregaba",
    "continuar",
    "continuo",
    "continua",
    "continuaba",
    "proseguir",
    "prosiguio",
    "prosigue",
    "replicar",
    "replico",
    "replica",
    # Emocionales
    "gritar",
    "grito",
    "grita",
    "gritaba",
    "gritaron",
    "susurrar",
    "susurro",
    "susurra",
    "susurraba",
    "murmurar",
    "murmuro",
    "murmura",
    "murmuraba",
    "exclamar",
    "exclamo",
    "exclama",
    "exclamaba",
    "gemir",
    "gimio",
    "gime",
    "gemia",
    "sollozar",
    "sollozo",
    "solloza",
    "sollozaba",
    "chillar",
    "chillo",
    "chilla",
    "chillaba",
    "bramar",
    "bramo",
    "brama",
    "rugir",
    "rugio",
    "ruge",
    # Interrogativos
    "preguntar",
    "pregunto",
    "pregunta",
    "preguntaba",
    "preguntaron",
    "inquirir",
    "inquirio",
    "inquiere",
    "interrogar",
    "interrogo",
    "interroga",
    "cuestionar",
    "cuestiono",
    "cuestiona",
    # Declarativos
    "afirmar",
    "afirmo",
    "afirma",
    "afirmaba",
    "asegurar",
    "aseguro",
    "asegura",
    "confirmar",
    "confirmo",
    "confirma",
    "negar",
    "nego",
    "niega",
    "negaba",
    # Otros
    "comentar",
    "comento",
    "comenta",
    "comentaba",
    "explicar",
    "explico",
    "explica",
    "explicaba",
    "admitir",
    "admitio",
    "admite",
    "admitia",
    "confesar",
    "confeso",
    "confiesa",
    "confesaba",
    "insistir",
    "insistio",
    "insiste",
    "insistia",
    "ordenar",
    "ordeno",
    "ordena",
    "ordenaba",
    "sugerir",
    "sugirio",
    "sugiere",
    "sugeria",
    "advertir",
    "advirtio",
    "advierte",
    "reclamar",
    "reclamo",
    "reclama",
    "protestar",
    "protesto",
    "protesta",
    "objetar",
    "objeto",
    "objeta",
    "interrumpir",
    "interrumpio",
    "interrumpe",
    "concluir",
    "concluyo",
    "concluye",
    "sentenciar",
    "sentencio",
    "sentencia",
    # Saludos y despedidas
    "saludar",
    "saludo",
    "saluda",
    "saludaba",
    "despedir",
    "despidio",
    "despide",
    "despedia",
}


class AttributionConfidence(Enum):
    """Nivel de confianza de la atribucion."""

    HIGH = "high"  # Verbo de habla explicito
    MEDIUM = "medium"  # Alternancia clara
    LOW = "low"  # Inferido por contexto/perfil
    UNKNOWN = "unknown"  # Sin atribucion clara


class AttributionMethod(Enum):
    """Metodo usado para la atribucion."""

    EXPLICIT_VERB = "explicit_verb"  # Verbo de habla + nombre
    ALTERNATION = "alternation"  # Patron de alternancia
    VOICE_PROFILE = "voice_profile"  # Match con perfil de voz
    PROXIMITY = "proximity"  # Mencion cercana
    NONE = "none"  # Sin metodo aplicable


@dataclass
class DialogueAttribution:
    """Atribucion de hablante para un dialogo."""

    dialogue_id: int
    text: str
    start_char: int
    end_char: int
    chapter: int

    # Atribucion
    speaker_id: int | None = None
    speaker_name: str | None = None
    confidence: AttributionConfidence = AttributionConfidence.UNKNOWN

    # Evidencia
    attribution_method: AttributionMethod = AttributionMethod.NONE
    speech_verb: str | None = None
    context_snippet: str = ""

    # Alternativas consideradas: (entity_id, entity_name, score)
    alternative_speakers: list[tuple[int, str, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "dialogue_id": self.dialogue_id,
            "text": self.text[:100] if self.text else "",
            "start_char": self.start_char,
            "end_char": self.end_char,
            "chapter": self.chapter,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "confidence": self.confidence.value,
            "attribution_method": self.attribution_method.value,
            "speech_verb": self.speech_verb,
            "context_snippet": (self.context_snippet[:50] if self.context_snippet else ""),
        }


@dataclass
class SceneParticipants:
    """Participantes de una escena."""

    chapter: int
    scene_start: int
    scene_end: int
    participants: list[int]  # entity_ids


class DialogueProtocol(Protocol):
    """Protocolo para objetos de dialogo."""

    text: str
    start_char: int
    end_char: int
    chapter: int


class EntityProtocol(Protocol):
    """Protocolo para objetos de entidad."""

    id: int
    canonical_name: str


class VoiceProfileProtocol(Protocol):
    """Protocolo para perfiles de voz."""

    entity_id: int
    uses_usted: bool
    uses_tu: bool
    avg_intervention_length: float
    filler_words: list[str]


class SpeakerAttributor:
    """Atribuidor de hablante para dialogos."""

    def __init__(self, entities: list[Any], voice_profiles: dict[int, Any] | None = None):
        """
        Inicializa el atribuidor.

        Args:
            entities: Lista de entidades del proyecto
            voice_profiles: Diccionario de perfiles de voz por entity_id
        """
        self.entities: dict[int, Any] = {}
        self.entity_names: dict[str, int] = {}
        self.entity_token_candidates: dict[str, set[int]] = {}
        self.entity_name_keys_by_id: dict[int, set[str]] = {}
        self._speaker_titles = {
            "don",
            "dona",
            "senor",
            "senora",
            "sr",
            "sra",
            "doctor",
            "doctora",
            "dr",
            "dra",
            "profesor",
            "profesora",
        }

        for e in entities:
            entity_id = getattr(e, "id", None)
            if entity_id is not None:
                self.entities[entity_id] = e

                # Nombre canonico
                name = getattr(e, "canonical_name", getattr(e, "name", ""))
                if name:
                    self._index_entity_name(entity_id, name)

                # Aliases
                aliases = getattr(e, "aliases", [])
                for alias in aliases:
                    if alias:
                        self._index_entity_name(entity_id, alias)

        self.voice_profiles = voice_profiles or {}

        # Compilar patrones de deteccion
        self._compile_patterns()

        logger.info(f"SpeakerAttributor initialized with {len(self.entities)} entities")

    @staticmethod
    def _strip_accents(text: str) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFD", text)
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    @classmethod
    def _normalize_name_key(cls, text: str) -> str:
        stripped = cls._strip_accents(text).lower()
        stripped = re.sub(r"[^a-z0-9\s]", " ", stripped)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        return stripped

    def _index_entity_name(self, entity_id: int, raw_name: str) -> None:
        key = self._normalize_name_key(raw_name)
        if not key:
            return
        self.entity_names[key] = entity_id
        self.entity_name_keys_by_id.setdefault(entity_id, set()).add(key)
        for token in key.split():
            if len(token) < 3:
                continue
            self.entity_token_candidates.setdefault(token, set()).add(entity_id)

    def _resolve_entity_id(self, candidate_name: str) -> int | None:
        key = self._normalize_name_key(candidate_name)
        if not key:
            return None

        direct = self.entity_names.get(key)
        if direct is not None:
            return direct

        tokens = [t for t in key.split() if t]
        if not tokens:
            return None

        # Quitar títulos al inicio (Don, Sr., Dr., etc.) y reintentar.
        while tokens and tokens[0] in self._speaker_titles:
            tokens = tokens[1:]
        if tokens:
            reduced_key = " ".join(tokens)
            direct = self.entity_names.get(reduced_key)
            if direct is not None:
                return direct

        # Fallback por token único (apellido o nombre principal) si no es ambiguo.
        candidate_ids: set[int] = set()
        if tokens:
            for token in (tokens[0], tokens[-1]):
                candidate_ids.update(self.entity_token_candidates.get(token, set()))
        if len(candidate_ids) == 1:
            return next(iter(candidate_ids))

        return None

    def _compile_patterns(self) -> None:
        """Compila patrones regex para deteccion de hablante."""
        # Patron: "—verbo Nombre" (despues del dialogo)
        verbs_pattern = "|".join(re.escape(v) for v in SPEECH_VERBS)
        name_pattern = r"([a-z][a-z'’-]*(?:\s+[a-z][a-z'’-]*){0,3})"

        # Patron 1: "—dijo Juan" o "—respondio Maria"
        self.pattern_verb_name = re.compile(
            r"[—\-]\s*(" + verbs_pattern + r")\s+" + name_pattern,
            re.IGNORECASE,
        )

        # Patron 2: "Juan dijo:" o "Maria respondio:"
        self.pattern_name_verb = re.compile(
            name_pattern + r"\s+(" + verbs_pattern + r")\s*[:\.]?\s*[—\-]?",
            re.IGNORECASE,
        )
        # Patron 2b: "Juan, con voz tensa, dijo" (cláusula intermedia)
        self.pattern_name_clause_verb = re.compile(
            name_pattern + r"(?:,\s*[^,\n.!?]{1,80},)?\s+(" + verbs_pattern + r")\b",
            re.IGNORECASE,
        )

        # Patron 3: ", dijo Juan" (con coma)
        self.pattern_comma_verb_name = re.compile(
            r",\s*(" + verbs_pattern + r")\s+" + name_pattern, re.IGNORECASE
        )
        self.pattern_any_verb = re.compile(r"\b(" + verbs_pattern + r")\b", re.IGNORECASE)

    def _trim_context_after(self, text: str) -> str:
        """Recorta contexto posterior para no mezclar con otro turno de diálogo."""
        if not text:
            return ""

        trimmed = text[:EXPLICIT_AFTER_WINDOW]
        next_dialogue = re.search(r"\n\s*[—\-]", trimmed)
        if next_dialogue:
            trimmed = trimmed[: next_dialogue.start()]
        else:
            # Corta antes de un nuevo turno inline: "... . —¿..."
            next_inline_dialogue = re.search(
                r"[.!?]\s*[—\-]\s*[¿¡A-ZÁÉÍÓÚÜÑ]",
                trimmed,
            )
            if next_inline_dialogue:
                trimmed = trimmed[: next_inline_dialogue.start() + 1]
        return trimmed

    def _resolve_entity_from_span(self, candidate_name: str) -> int | None:
        """
        Resuelve entidad desde un span potencialmente ruidoso.

        Intenta el nombre completo y, si falla, elimina tokens finales
        para quedarse con el núcleo nominal.
        """
        key = self._normalize_name_key(candidate_name)
        if not key:
            return None

        tokens = key.split()
        while tokens:
            candidate = " ".join(tokens)
            entity_id = self._resolve_entity_id(candidate)
            if entity_id is not None:
                return entity_id
            tokens = tokens[:-1]

        return None

    def _closest_entity_before(
        self,
        entity_mentions: list[tuple[int, int, int]],
        dialogue_start: int,
        max_distance: int = IMPLICIT_SUBJECT_WINDOW,
    ) -> int | None:
        """Obtiene la entidad mencionada más cercana antes del diálogo."""
        closest_id: int | None = None
        closest_distance: int | None = None

        for entity_id, start, end in entity_mentions:
            mention_pos = max(start, end)
            if mention_pos > dialogue_start:
                continue
            distance = dialogue_start - mention_pos
            if distance > max_distance:
                continue
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_id = entity_id

        return closest_id

    def _is_entity_addressed_in_dialogue(self, entity_id: int, dialogue_text: str) -> bool:
        """Detecta si una entidad parece ser destinataria vocativa del diálogo."""
        if not dialogue_text:
            return False

        text_norm = self._strip_accents(dialogue_text).lower()
        name_keys = sorted(
            self.entity_name_keys_by_id.get(entity_id, set()),
            key=len,
            reverse=True,
        )
        for key in name_keys:
            if len(key) < 3:
                continue
            if re.search(rf"(?:^|[\s¿¡]){re.escape(key)}\s*,", text_norm):
                return True
        return False

    def _has_subject_verb_hint(self, entity_id: int, context_before: str) -> bool:
        """
        Señal narrativa de sujeto: "<Nombre> ... <verbo de habla>" antes del diálogo.

        Sirve para acotaciones compuestas del tipo:
        "Don Ramiro, con voz tensa, murmuró: ..."
        """
        if not context_before:
            return False

        context_norm = self._strip_accents(context_before).lower()
        name_keys = sorted(
            self.entity_name_keys_by_id.get(entity_id, set()),
            key=len,
            reverse=True,
        )
        for key in name_keys:
            if len(key) < 4:
                continue
            pos = context_norm.rfind(key)
            if pos < 0:
                continue
            tail = context_norm[pos + len(key) : pos + len(key) + 90]
            if self.pattern_any_verb.search(tail):
                return True
        return False

    def _select_multispeaker_candidate(
        self,
        dialogue_text: str,
        context_before: str,
        dialogue_start: int,
        turns_since_explicit: int,
        nearby: list[int],
        current_participants: list[int],
        last_speaker: int | None,
        previous_speaker: int | None,
        entity_mentions: list[tuple[int, int, int]],
    ) -> list[tuple[int, float]] | None:
        """
        Heurística para escenas con 3+ participantes.

        Combina:
        - ritmo de turnos recientes,
        - proximidad/mención previa,
        - pistas narrativas con verbo compuesto,
        - penalización por vocativo (destinatario ≠ hablante).
        """
        candidate_ids: list[int] = []
        seen: set[int] = set()

        for entity_id in current_participants:
            if entity_id not in seen:
                seen.add(entity_id)
                candidate_ids.append(entity_id)

        for entity_id in nearby[:8]:
            if entity_id not in seen:
                seen.add(entity_id)
                candidate_ids.append(entity_id)

        if last_speaker is not None and last_speaker not in seen:
            seen.add(last_speaker)
            candidate_ids.append(last_speaker)
        if previous_speaker is not None and previous_speaker not in seen:
            seen.add(previous_speaker)
            candidate_ids.append(previous_speaker)

        if len(candidate_ids) < MULTI_SPEAKER_THRESHOLD:
            return None

        proximity_rank = {entity_id: idx for idx, entity_id in enumerate(nearby[:8])}
        closest_before = self._closest_entity_before(
            entity_mentions,
            dialogue_start,
            max_distance=240,
        )
        decay = max(CONFIDENCE_FLOOR, CONFIDENCE_DECAY_RATE**turns_since_explicit)
        voice_scores: dict[int, float] = {}
        if self.voice_profiles:
            voice_scores = dict(self._score_voice_match(dialogue_text, candidate_ids))

        scored: list[tuple[int, float]] = []
        for entity_id in candidate_ids:
            score = 0.0

            # Ritmo de turnos: en diálogos corales suele volver el penúltimo hablante.
            if (
                previous_speaker is not None
                and entity_id == previous_speaker
                and entity_id != last_speaker
            ):
                score += 0.46
            if last_speaker is not None and entity_id == last_speaker:
                score -= 0.18

            if closest_before is not None and entity_id == closest_before:
                score += 0.22

            if entity_id in proximity_rank:
                score += max(0.16 - (proximity_rank[entity_id] * 0.03), 0.04)

            if self._has_subject_verb_hint(entity_id, context_before):
                score += 0.22

            if self._is_entity_addressed_in_dialogue(entity_id, dialogue_text):
                score -= 0.26

            if entity_id in current_participants:
                score += 0.05

            if entity_id in voice_scores:
                score += min(0.16, voice_scores[entity_id] * 0.5)

            score *= decay
            scored.append((entity_id, round(score, 3)))

        scored.sort(key=lambda item: item[1], reverse=True)
        if not scored:
            return None

        best_score = scored[0][1]
        if best_score < 0.18:
            return None

        # Evitar decisiones débiles cuando hay empate técnico.
        if len(scored) > 1 and (best_score - scored[1][1]) < 0.03 and best_score < 0.35:
            return None

        return scored

    @staticmethod
    def _detect_scene_breaks(text: str) -> list[int]:
        """
        Detecta posiciones de scene breaks en el texto.

        Reutiliza los patrones de chapter.py (_SCENE_BREAK_PATTERNS).

        Returns:
            Lista de posiciones (char offset) donde hay scene breaks, ordenadas.
        """
        positions: set[int] = set()
        for pattern in _SCENE_BREAK_PATTERNS:
            for match in pattern.finditer(text):
                positions.add(match.start())
        return sorted(positions)

    def _is_past_scene_break(
        self,
        scene_breaks: list[int],
        last_position: int,
        current_position: int,
    ) -> bool:
        """Verifica si hay un scene break entre dos posiciones."""
        for sb in scene_breaks:
            if last_position < sb <= current_position:
                return True
        return False

    def attribute_dialogues(
        self,
        dialogues: list[Any],
        entity_mentions: list[tuple[int, int, int]] | None = None,
        full_text: str | None = None,
    ) -> list[DialogueAttribution]:
        """
        Atribuye hablante a cada dialogo.

        Args:
            dialogues: Lista de dialogos a atribuir
            entity_mentions: Lista de (entity_id, start, end) de menciones
            full_text: Texto completo para contexto

        Returns:
            Lista de atribuciones
        """
        entity_mentions = entity_mentions or []
        attributions: list[DialogueAttribution] = []

        # Ordenar dialogos por posicion
        sorted_dialogues = sorted(dialogues, key=lambda d: getattr(d, "start_char", 0))

        # Pre-calcular scene breaks del texto completo
        scene_breaks: list[int] = []
        if full_text:
            scene_breaks = self._detect_scene_breaks(full_text)

        # Contexto de escena
        current_participants: list[int] = []
        last_speaker: int | None = None
        previous_speaker: int | None = None
        last_chapter: int = -1
        last_dialogue_pos: int = 0
        # Tracking para confidence decay
        turns_since_explicit: int = 0

        for i, dialogue in enumerate(sorted_dialogues):
            text = getattr(dialogue, "text", "")
            start_char = getattr(dialogue, "start_char", 0)
            end_char = getattr(dialogue, "end_char", len(text))
            chapter = getattr(dialogue, "chapter", 1)
            attribution_text = getattr(dialogue, "attribution_text", "") or ""

            # Reset al cambiar de capitulo
            if chapter != last_chapter:
                current_participants = []
                last_speaker = None
                previous_speaker = None
                last_chapter = chapter
                turns_since_explicit = 0
                last_dialogue_pos = start_char

            # Reset en scene break (BK-10b)
            elif scene_breaks and self._is_past_scene_break(
                scene_breaks, last_dialogue_pos, start_char
            ):
                current_participants = []
                last_speaker = None
                previous_speaker = None
                turns_since_explicit = 0

            prev_dialogue_pos = last_dialogue_pos
            last_dialogue_pos = start_char

            # Obtener contexto del dialogo
            context_after = ""
            if hasattr(dialogue, "context_after"):
                context_after = dialogue.context_after
            elif full_text and end_char < len(full_text):
                context_after = full_text[end_char : end_char + 150]

            context_before = ""
            if hasattr(dialogue, "context_before"):
                context_before = dialogue.context_before
            elif full_text and start_char > 0:
                context_before = full_text[max(0, start_char - 150) : start_char]

            attr = DialogueAttribution(
                dialogue_id=i,
                text=text,
                start_char=start_char,
                end_char=end_char,
                chapter=chapter,
                context_snippet=context_after[:50] if context_after else "",
            )

            # 0. Intentar explícito en attribution_text local (más fiable que hint)
            if attribution_text:
                explicit_from_attr = self._detect_explicit_speaker(
                    "",
                    attribution_text,
                    entity_mentions,
                    start_char,
                    end_char,
                )
                if explicit_from_attr:
                    attr.speaker_id = explicit_from_attr[0]
                    attr.speaker_name = self._get_entity_name(explicit_from_attr[0])
                    attr.confidence = AttributionConfidence.HIGH
                    attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                    attr.speech_verb = explicit_from_attr[1]
                    previous_speaker = last_speaker
                    last_speaker = explicit_from_attr[0]
                    turns_since_explicit = 0
                    if explicit_from_attr[0] not in current_participants:
                        current_participants.append(explicit_from_attr[0])
                    attributions.append(attr)
                    continue

            # 1. Intentar detección explícita en contexto antes/después
            explicit = self._detect_explicit_speaker(
                context_before, context_after, entity_mentions, start_char, end_char
            )
            if explicit:
                attr.speaker_id = explicit[0]
                attr.speaker_name = self._get_entity_name(explicit[0])
                attr.confidence = AttributionConfidence.HIGH
                attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                attr.speech_verb = explicit[1]
                previous_speaker = last_speaker
                last_speaker = explicit[0]
                turns_since_explicit = 0
                if explicit[0] not in current_participants:
                    current_participants.append(explicit[0])
                attributions.append(attr)
                continue

            # 2. Usar speaker_hint solo como fallback
            speaker_hint = getattr(dialogue, "speaker_hint", "") or ""
            if speaker_hint:
                matched_id = self._resolve_entity_id(speaker_hint)
                if matched_id is not None:
                    attr.speaker_id = matched_id
                    attr.speaker_name = self._get_entity_name(matched_id)
                    attr.confidence = AttributionConfidence.HIGH
                    attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                    attr.speech_verb = "speaker_hint"
                    previous_speaker = last_speaker
                    last_speaker = matched_id
                    turns_since_explicit = 0
                    if matched_id not in current_participants:
                        current_participants.append(matched_id)
                    attributions.append(attr)
                    continue

            # A partir de aquí: métodos no explícitos → aplicar decay (BK-10c)
            turns_since_explicit += 1

            # 2. Actualizar participantes de escena por proximidad
            nearby = self._get_nearby_entities(start_char, entity_mentions, window=500)
            for e_id in nearby:
                if e_id not in current_participants:
                    current_participants.append(e_id)

            # 3. Intentar alternancia (caso clásico: exactamente 2 participantes)
            if last_speaker and len(current_participants) == 2:
                other = [p for p in current_participants if p != last_speaker]
                if other:
                    attr.speaker_id = other[0]
                    attr.speaker_name = self._get_entity_name(other[0])
                    # Aplicar decay de confianza (BK-10c)
                    decay = max(
                        CONFIDENCE_FLOOR,
                        CONFIDENCE_DECAY_RATE**turns_since_explicit,
                    )
                    if decay >= 0.74:
                        attr.confidence = AttributionConfidence.MEDIUM
                    else:
                        attr.confidence = AttributionConfidence.LOW
                    attr.attribution_method = AttributionMethod.ALTERNATION
                    previous_speaker = last_speaker
                    last_speaker = other[0]
                    attributions.append(attr)
                    continue

            # 3b. Alternancia por turnos recientes aunque la escena tenga >2 menciones.
            # Útil cuando hay acotaciones largas o múltiples nombres en la narración.
            if (
                last_speaker
                and previous_speaker
                and previous_speaker != last_speaker
                and (start_char - prev_dialogue_pos) <= 450
            ):
                candidate = previous_speaker
                if not current_participants or candidate in current_participants:
                    attr.speaker_id = candidate
                    attr.speaker_name = self._get_entity_name(candidate)
                    decay = max(
                        CONFIDENCE_FLOOR,
                        CONFIDENCE_DECAY_RATE**turns_since_explicit,
                    )
                    attr.confidence = (
                        AttributionConfidence.MEDIUM if decay >= 0.68 else AttributionConfidence.LOW
                    )
                    attr.attribution_method = AttributionMethod.ALTERNATION
                    attr.alternative_speakers = [
                        (last_speaker, self._get_entity_name(last_speaker), 0.45)
                    ]
                    previous_speaker = last_speaker
                    last_speaker = candidate
                    attributions.append(attr)
                    continue

            # 4. Escena coral (3+ participantes): scoring combinado
            multispeaker_scored = self._select_multispeaker_candidate(
                dialogue_text=text,
                context_before=context_before,
                dialogue_start=start_char,
                turns_since_explicit=turns_since_explicit,
                nearby=nearby,
                current_participants=current_participants,
                last_speaker=last_speaker,
                previous_speaker=previous_speaker,
                entity_mentions=entity_mentions,
            )
            if multispeaker_scored:
                best_id, best_score = multispeaker_scored[0]
                attr.speaker_id = best_id
                attr.speaker_name = self._get_entity_name(best_id)
                attr.confidence = (
                    AttributionConfidence.MEDIUM
                    if best_score >= 0.38
                    else AttributionConfidence.LOW
                )
                if (
                    previous_speaker is not None
                    and best_id == previous_speaker
                    and best_id != last_speaker
                ):
                    attr.attribution_method = AttributionMethod.ALTERNATION
                else:
                    attr.attribution_method = AttributionMethod.PROXIMITY
                attr.alternative_speakers = [
                    (eid, self._get_entity_name(eid), score)
                    for eid, score in multispeaker_scored[1:]
                    if score >= 0.12
                ][:3]
                previous_speaker = last_speaker
                last_speaker = best_id
                attributions.append(attr)
                continue

            # 5. Intentar perfil de voz
            voice_scored = []
            if self.voice_profiles and current_participants:
                voice_scored = self._score_voice_match(text, current_participants)

            if voice_scored and voice_scored[0][1] >= 0.25:
                best_id = voice_scored[0][0]
                attr.speaker_id = best_id
                attr.speaker_name = self._get_entity_name(best_id)
                attr.confidence = AttributionConfidence.LOW
                attr.attribution_method = AttributionMethod.VOICE_PROFILE
                # Guardar alternativas (excluyendo el ganador)
                attr.alternative_speakers = [
                    (eid, self._get_entity_name(eid), sc)
                    for eid, sc in voice_scored[1:]
                    if sc > 0.1
                ][:3]
                previous_speaker = last_speaker
                last_speaker = best_id
                attributions.append(attr)
                continue

            # 6. Intentar proximidad simple (entidad mas cercana)
            if nearby:
                closest = nearby[0]  # Ya ordenados por proximidad
                attr.speaker_id = closest
                attr.speaker_name = self._get_entity_name(closest)
                attr.confidence = AttributionConfidence.LOW
                attr.attribution_method = AttributionMethod.PROXIMITY
                # Agregar alternativas de voz si las hay
                if voice_scored:
                    attr.alternative_speakers = [
                        (eid, self._get_entity_name(eid), sc)
                        for eid, sc in voice_scored
                        if eid != closest and sc > 0.1
                    ][:3]
                previous_speaker = last_speaker
                last_speaker = closest
                attributions.append(attr)
                continue

            # 7. Sin atribucion clara
            attr.confidence = AttributionConfidence.UNKNOWN
            attr.attribution_method = AttributionMethod.NONE
            # Aun asi agregar alternativas si hay scores
            if voice_scored:
                attr.alternative_speakers = [
                    (eid, self._get_entity_name(eid), sc) for eid, sc in voice_scored if sc > 0.1
                ][:3]
            attributions.append(attr)

        logger.info(f"Attributed {len(attributions)} dialogues")
        return attributions

    def _get_entity_name(self, entity_id: int) -> str:
        """Obtiene nombre de entidad por ID."""
        entity = self.entities.get(entity_id)
        if entity:
            return getattr(entity, "canonical_name", getattr(entity, "name", str(entity_id)))
        return str(entity_id)

    def _detect_explicit_speaker(
        self,
        context_before: str,
        context_after: str,
        entity_mentions: list[tuple[int, int, int]],
        dialogue_start: int,
        dialogue_end: int,
    ) -> tuple[int, str] | None:
        """
        Detecta hablante explicito por verbo de habla.

        Args:
            context_before: Contexto antes del dialogo
            context_after: Contexto despues del dialogo
            entity_mentions: Menciones de entidades
            dialogue_start: Inicio del dialogo
            dialogue_end: Fin del dialogo

        Returns:
            Tupla (entity_id, verbo) o None
        """
        context_after_local = self._trim_context_after(context_after)
        context_after_norm = self._strip_accents(context_after_local).lower()
        context_before_norm = self._strip_accents(context_before).lower()

        # Buscar en contexto despues del dialogo
        for pattern in [self.pattern_verb_name, self.pattern_comma_verb_name]:
            match = pattern.search(context_after_norm)
            if match:
                verb = match.group(1).lower()
                name = match.group(2)
                entity_id = self._resolve_entity_from_span(name)
                if entity_id is not None:
                    return (entity_id, verb)

        # Buscar en contexto antes del dialogo
        for pattern in [self.pattern_name_clause_verb, self.pattern_name_verb]:
            match = pattern.search(context_before_norm)
            if match:
                name = match.group(1)
                verb = match.group(2).lower()
                entity_id = self._resolve_entity_from_span(name)
                if entity_id is not None:
                    return (entity_id, verb)

        # También puede aparecer tras el diálogo: "—... —Don Ramiro, ..., murmuró."
        for pattern in [self.pattern_name_clause_verb, self.pattern_name_verb]:
            match = pattern.search(context_after_norm)
            if match:
                name = match.group(1)
                verb = match.group(2).lower()
                entity_id = self._resolve_entity_from_span(name)
                if entity_id is not None:
                    return (entity_id, verb)

        # Verbo de habla sin nombre explícito: inferir sujeto por mención previa cercana.
        verb_only = self.pattern_any_verb.search(context_after_norm)
        if verb_only:
            inferred_id = self._closest_entity_before(entity_mentions, dialogue_start)
            if inferred_id is not None:
                return (inferred_id, verb_only.group(1).lower())

        # Buscar mención cercana + verbo de habla (fallback legado)
        for entity_id, start, _end in entity_mentions:
            # Si la mencion esta muy cerca del dialogo
            if (
                dialogue_start - 100 <= start <= dialogue_start
                or dialogue_end <= start <= dialogue_end + 100
            ):
                # Verificar si hay verbo de habla
                context = context_after_norm[:100]
                match = self.pattern_any_verb.search(context)
                if match:
                    return (entity_id, match.group(1).lower())

        return None

    def _get_nearby_entities(
        self,
        position: int,
        entity_mentions: list[tuple[int, int, int]],
        window: int = 500,
    ) -> list[int]:
        """
        Obtiene entidades mencionadas cerca de una posicion.

        Args:
            position: Posicion de referencia
            entity_mentions: Lista de menciones
            window: Ventana de busqueda en caracteres

        Returns:
            Lista de entity_ids ordenados por proximidad
        """
        nearby: list[tuple[int, int]] = []  # (entity_id, distance)

        for entity_id, start, end in entity_mentions:
            distance = min(abs(start - position), abs(end - position))
            if distance <= window:
                nearby.append((entity_id, distance))

        # Ordenar por distancia y eliminar duplicados
        nearby.sort(key=lambda x: x[1])
        seen: set[int] = set()
        result: list[int] = []
        for entity_id, _ in nearby:
            if entity_id not in seen:
                seen.add(entity_id)
                result.append(entity_id)

        return result

    def _score_voice_match(self, text: str, candidates: list[int]) -> list[tuple[int, float]]:
        """
        Puntua cada candidato por similitud con su perfil de voz.

        Usa multiples metricas del VoiceProfile para scoring:
        - Formalidad (usted/tu + formality_score)
        - Longitud de intervencion
        - Patrones de puntuacion (exclamaciones, preguntas, suspension)
        - Muletillas
        - Vocabulario caracteristico

        Args:
            text: Texto del dialogo
            candidates: Lista de candidatos (entity_ids)

        Returns:
            Lista de (entity_id, score) ordenada por score descendente
        """
        if not candidates or not self.voice_profiles:
            return []

        text_lower = text.lower()
        words = text.split()
        word_count = len(words)
        words_lower = {w.lower() for w in words}

        # Analizar rasgos del texto
        uses_usted = "usted" in text_lower
        uses_tu = any(w in text_lower for w in ["tú", "tu ", " tu", "tuyo", "tuya"])
        has_exclamation = "!" in text or "¡" in text
        has_question = "?" in text or "¿" in text
        has_ellipsis = "..." in text

        scored: list[tuple[int, float]] = []

        for entity_id in candidates:
            if entity_id not in self.voice_profiles:
                continue

            profile = self.voice_profiles[entity_id]
            metrics = getattr(profile, "metrics", None)
            if not metrics:
                continue

            score = 0.0
            weights_sum = 0.0

            # 1. Formalidad via usted/tu (peso 0.20)
            formality = getattr(metrics, "formality_score", 0.5)
            if uses_usted and formality > 0.6 or uses_tu and formality < 0.4:
                score += 0.20
            elif not uses_usted and not uses_tu:
                score += 0.10  # Neutral text, partial credit
            weights_sum += 0.20

            # 2. Longitud de intervencion (peso 0.20)
            avg_len = getattr(metrics, "avg_intervention_length", 0)
            std_len = getattr(metrics, "std_intervention_length", 0)
            if avg_len > 0:
                if std_len > 0:
                    z_score = abs(word_count - avg_len) / std_len
                    if z_score < 1.0:
                        score += 0.20
                    elif z_score < 2.0:
                        score += 0.10
                else:
                    if abs(word_count - avg_len) < avg_len * 0.5:
                        score += 0.15
            weights_sum += 0.20

            # 3. Patrones de puntuacion (peso 0.15)
            punct_score = 0.0
            exc_ratio = getattr(metrics, "exclamation_ratio", 0)
            qst_ratio = getattr(metrics, "question_ratio", 0)
            ell_ratio = getattr(metrics, "ellipsis_ratio", 0)

            if has_exclamation and exc_ratio > 0.15:
                punct_score += 0.33
            elif not has_exclamation and exc_ratio < 0.10:
                punct_score += 0.20

            if has_question and qst_ratio > 0.15:
                punct_score += 0.33
            elif not has_question and qst_ratio < 0.10:
                punct_score += 0.20

            if has_ellipsis and ell_ratio > 0.05:
                punct_score += 0.33
            elif not has_ellipsis and ell_ratio < 0.05:
                punct_score += 0.20

            score += punct_score * 0.15
            weights_sum += 0.15

            # 4. Muletillas (peso 0.20)
            top_fillers = getattr(metrics, "top_fillers", [])
            filler_match = False
            for filler_item in top_fillers:
                filler_word = (
                    filler_item[0] if isinstance(filler_item, (list, tuple)) else str(filler_item)
                )
                if filler_word and filler_word.lower() in text_lower:
                    filler_match = True
                    break
            if filler_match:
                score += 0.20
            weights_sum += 0.20

            # 5. Vocabulario caracteristico (peso 0.25)
            char_words = getattr(profile, "characteristic_words", [])
            if char_words and words_lower:
                char_set = set()
                for item in char_words[:15]:
                    word = item[0] if isinstance(item, (list, tuple)) else str(item)
                    char_set.add(word.lower())
                overlap = len(words_lower & char_set)
                if overlap > 0:
                    score += min(overlap * 0.08, 0.25)
            weights_sum += 0.25

            # Normalizar por confianza del perfil
            profile_confidence = getattr(profile, "confidence", 0.5)
            final_score = score * (0.5 + 0.5 * profile_confidence)

            scored.append((entity_id, round(final_score, 3)))

        # Ordenar por score descendente
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _match_voice_profile(self, text: str, candidates: list[int]) -> int | None:
        """
        Intenta matching por perfil de voz.

        Args:
            text: Texto del dialogo
            candidates: Lista de candidatos (entity_ids)

        Returns:
            entity_id del mejor match o None
        """
        scored = self._score_voice_match(text, candidates)
        if scored and scored[0][1] >= 0.25:
            return scored[0][0]
        return None

    def get_attribution_stats(self, attributions: list[DialogueAttribution]) -> dict[str, Any]:
        """
        Genera estadisticas de atribucion.

        Args:
            attributions: Lista de atribuciones

        Returns:
            Diccionario con estadisticas
        """
        total = len(attributions)
        if total == 0:
            return {
                "total_dialogues": 0,
                "by_confidence": {"high": 0, "medium": 0, "low": 0, "unknown": 0},
                "by_method": {},
                "attribution_rate": 0.0,
            }

        by_confidence = {
            "high": sum(1 for a in attributions if a.confidence == AttributionConfidence.HIGH),
            "medium": sum(1 for a in attributions if a.confidence == AttributionConfidence.MEDIUM),
            "low": sum(1 for a in attributions if a.confidence == AttributionConfidence.LOW),
            "unknown": sum(
                1 for a in attributions if a.confidence == AttributionConfidence.UNKNOWN
            ),
        }

        by_method: dict[str, int] = {}
        for a in attributions:
            method = a.attribution_method.value
            by_method[method] = by_method.get(method, 0) + 1

        by_speaker: dict[str, int] = {}
        for a in attributions:
            if a.speaker_name:
                by_speaker[a.speaker_name] = by_speaker.get(a.speaker_name, 0) + 1

        attributed = total - by_confidence["unknown"]

        return {
            "total_dialogues": total,
            "attributed_dialogues": attributed,
            "by_confidence": by_confidence,
            "by_method": by_method,
            "by_speaker": by_speaker,
            "attribution_rate": attributed / total if total > 0 else 0.0,
        }

    def get_unattributed_dialogues(
        self, attributions: list[DialogueAttribution]
    ) -> list[DialogueAttribution]:
        """
        Obtiene dialogos sin atribucion.

        Args:
            attributions: Lista de atribuciones

        Returns:
            Lista de dialogos sin atribuir
        """
        return [a for a in attributions if a.confidence == AttributionConfidence.UNKNOWN]

    def get_low_confidence_dialogues(
        self, attributions: list[DialogueAttribution]
    ) -> list[DialogueAttribution]:
        """
        Obtiene dialogos con baja confianza.

        Args:
            attributions: Lista de atribuciones

        Returns:
            Lista de dialogos con confianza LOW o UNKNOWN
        """
        return [
            a
            for a in attributions
            if a.confidence in (AttributionConfidence.LOW, AttributionConfidence.UNKNOWN)
        ]


def attribute_speakers(
    dialogues: list[Any],
    entities: list[Any],
    entity_mentions: list[tuple[int, int, int]] | None = None,
    voice_profiles: dict[int, Any] | None = None,
    full_text: str | None = None,
) -> tuple[list[DialogueAttribution], dict[str, Any]]:
    """
    Funcion de conveniencia para atribuir hablantes.

    Args:
        dialogues: Lista de dialogos
        entities: Lista de entidades
        entity_mentions: Menciones de entidades (opcional)
        voice_profiles: Perfiles de voz (opcional)
        full_text: Texto completo (opcional)

    Returns:
        Tupla de (atribuciones, estadisticas)
    """
    attributor = SpeakerAttributor(entities, voice_profiles)
    attributions = attributor.attribute_dialogues(dialogues, entity_mentions, full_text)
    stats = attributor.get_attribution_stats(attributions)
    return attributions, stats
