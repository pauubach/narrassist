"""
Sistema de atribucion de hablante en dialogos.

Determina quien dice que en los dialogos usando multiples estrategias:
1. Deteccion explicita (verbo de habla + nombre)
2. Alternancia (si A habla, luego B, luego probablemente A)
3. Perfil de voz (comparar estilo con perfiles conocidos)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from ..persistence.chapter import _SCENE_BREAK_PATTERNS

logger = logging.getLogger(__name__)

# Decay de confianza por distancia de diálogos
CONFIDENCE_DECAY_RATE = 0.97  # base * 0.97^distance
CONFIDENCE_FLOOR = 0.30  # mínimo de confianza tras decay


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
            "context_snippet": (
                self.context_snippet[:50] if self.context_snippet else ""
            ),
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

    def __init__(
        self, entities: list[Any], voice_profiles: dict[int, Any] | None = None
    ):
        """
        Inicializa el atribuidor.

        Args:
            entities: Lista de entidades del proyecto
            voice_profiles: Diccionario de perfiles de voz por entity_id
        """
        self.entities: dict[int, Any] = {}
        self.entity_names: dict[str, int] = {}

        for e in entities:
            entity_id = getattr(e, "id", None)
            if entity_id is not None:
                self.entities[entity_id] = e

                # Nombre canonico
                name = getattr(e, "canonical_name", getattr(e, "name", ""))
                if name:
                    self.entity_names[name.lower()] = entity_id

                # Aliases
                aliases = getattr(e, "aliases", [])
                for alias in aliases:
                    if alias:
                        self.entity_names[alias.lower()] = entity_id

        self.voice_profiles = voice_profiles or {}

        # Compilar patrones de deteccion
        self._compile_patterns()

        logger.info(f"SpeakerAttributor initialized with {len(self.entities)} entities")

    def _compile_patterns(self) -> None:
        """Compila patrones regex para deteccion de hablante."""
        # Patron: "—verbo Nombre" (despues del dialogo)
        verbs_pattern = "|".join(re.escape(v) for v in SPEECH_VERBS)

        # Patron 1: "—dijo Juan" o "—respondio Maria"
        self.pattern_verb_name = re.compile(
            r"[—\-]\s*(" + verbs_pattern + r")\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            re.IGNORECASE,
        )

        # Patron 2: "Juan dijo:" o "Maria respondio:"
        self.pattern_name_verb = re.compile(
            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(" + verbs_pattern + r")\s*[:\.]?\s*[—\-]?",
            re.IGNORECASE,
        )

        # Patron 3: ", dijo Juan" (con coma)
        self.pattern_comma_verb_name = re.compile(
            r",\s*(" + verbs_pattern + r")\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)", re.IGNORECASE
        )

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
        last_chapter: int = -1
        last_dialogue_pos: int = 0
        # Tracking para confidence decay
        turns_since_explicit: int = 0

        for i, dialogue in enumerate(sorted_dialogues):
            text = getattr(dialogue, "text", "")
            start_char = getattr(dialogue, "start_char", 0)
            end_char = getattr(dialogue, "end_char", len(text))
            chapter = getattr(dialogue, "chapter", 1)

            # Reset al cambiar de capitulo
            if chapter != last_chapter:
                current_participants = []
                last_speaker = None
                last_chapter = chapter
                turns_since_explicit = 0
                last_dialogue_pos = start_char

            # Reset en scene break (BK-10b)
            elif scene_breaks and self._is_past_scene_break(
                scene_breaks, last_dialogue_pos, start_char
            ):
                current_participants = []
                last_speaker = None
                turns_since_explicit = 0

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

            # 0. Usar speaker_hint del detector de diálogos
            speaker_hint = getattr(dialogue, "speaker_hint", "") or ""
            if speaker_hint:
                hint_lower = speaker_hint.strip().lower()
                if hint_lower in self.entity_names:
                    matched_id = self.entity_names[hint_lower]
                    attr.speaker_id = matched_id
                    attr.speaker_name = self._get_entity_name(matched_id)
                    attr.confidence = AttributionConfidence.HIGH
                    attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                    attr.speech_verb = "speaker_hint"
                    last_speaker = matched_id
                    turns_since_explicit = 0
                    if matched_id not in current_participants:
                        current_participants.append(matched_id)
                    attributions.append(attr)
                    continue
                else:
                    # Intentar coincidencia parcial (nombre sin apellido)
                    for name, eid in self.entity_names.items():
                        if hint_lower in name or name in hint_lower:
                            attr.speaker_id = eid
                            attr.speaker_name = self._get_entity_name(eid)
                            attr.confidence = AttributionConfidence.HIGH
                            attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                            attr.speech_verb = "speaker_hint"
                            last_speaker = eid
                            turns_since_explicit = 0
                            if eid not in current_participants:
                                current_participants.append(eid)
                            attributions.append(attr)
                            break
                    else:
                        # No match found, fall through to next steps
                        pass
                    if attr.speaker_id is not None:
                        continue

            # 1. Intentar deteccion explicita
            explicit = self._detect_explicit_speaker(
                context_before, context_after, entity_mentions, start_char, end_char
            )
            if explicit:
                attr.speaker_id = explicit[0]
                attr.speaker_name = self._get_entity_name(explicit[0])
                attr.confidence = AttributionConfidence.HIGH
                attr.attribution_method = AttributionMethod.EXPLICIT_VERB
                attr.speech_verb = explicit[1]
                last_speaker = explicit[0]
                turns_since_explicit = 0
                if explicit[0] not in current_participants:
                    current_participants.append(explicit[0])
                attributions.append(attr)
                continue

            # A partir de aquí: métodos no explícitos → aplicar decay (BK-10c)
            turns_since_explicit += 1

            # 2. Actualizar participantes de escena por proximidad
            nearby = self._get_nearby_entities(start_char, entity_mentions, window=500)
            for e_id in nearby:
                if e_id not in current_participants:
                    current_participants.append(e_id)

            # 3. Intentar alternancia (solo si hay exactamente 2 participantes)
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
                    last_speaker = other[0]
                    attributions.append(attr)
                    continue

            # 4. Intentar perfil de voz
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
                last_speaker = best_id
                attributions.append(attr)
                continue

            # 5. Intentar proximidad simple (entidad mas cercana)
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
                last_speaker = closest
                attributions.append(attr)
                continue

            # 6. Sin atribucion clara
            attr.confidence = AttributionConfidence.UNKNOWN
            attr.attribution_method = AttributionMethod.NONE
            # Aun asi agregar alternativas si hay scores
            if voice_scored:
                attr.alternative_speakers = [
                    (eid, self._get_entity_name(eid), sc)
                    for eid, sc in voice_scored
                    if sc > 0.1
                ][:3]
            attributions.append(attr)

        logger.info(f"Attributed {len(attributions)} dialogues")
        return attributions

    def _get_entity_name(self, entity_id: int) -> str:
        """Obtiene nombre de entidad por ID."""
        entity = self.entities.get(entity_id)
        if entity:
            return getattr(
                entity, "canonical_name", getattr(entity, "name", str(entity_id))
            )
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
        # Buscar en contexto despues del dialogo
        for pattern in [self.pattern_verb_name, self.pattern_comma_verb_name]:
            match = pattern.search(context_after)
            if match:
                verb = match.group(1).lower()
                name = match.group(2).lower()
                if name in self.entity_names:
                    return (self.entity_names[name], verb)

        # Buscar en contexto antes del dialogo
        match = self.pattern_name_verb.search(context_before)
        if match:
            name = match.group(1).lower()
            verb = match.group(2).lower()
            if name in self.entity_names:
                return (self.entity_names[name], verb)

        # Buscar mencion cercana + verbo de habla
        for entity_id, start, _end in entity_mentions:
            # Si la mencion esta muy cerca del dialogo
            if (
                dialogue_start - 100 <= start <= dialogue_start
                or dialogue_end <= start <= dialogue_end + 100
            ):
                # Verificar si hay verbo de habla
                context = context_after[:100].lower()
                for verb in SPEECH_VERBS:
                    if verb in context:
                        return (entity_id, verb)

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

    def _score_voice_match(
        self, text: str, candidates: list[int]
    ) -> list[tuple[int, float]]:
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
                    filler_item[0]
                    if isinstance(filler_item, (list, tuple))
                    else str(filler_item)
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

    def get_attribution_stats(
        self, attributions: list[DialogueAttribution]
    ) -> dict[str, Any]:
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
            "high": sum(
                1 for a in attributions if a.confidence == AttributionConfidence.HIGH
            ),
            "medium": sum(
                1 for a in attributions if a.confidence == AttributionConfidence.MEDIUM
            ),
            "low": sum(
                1 for a in attributions if a.confidence == AttributionConfidence.LOW
            ),
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
        return [
            a for a in attributions if a.confidence == AttributionConfidence.UNKNOWN
        ]

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
            if a.confidence
            in (AttributionConfidence.LOW, AttributionConfidence.UNKNOWN)
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
