"""
Sistema de atribucion de hablante en dialogos.

Determina quien dice que en los dialogos usando multiples estrategias:
1. Deteccion explicita (verbo de habla + nombre)
2. Alternancia (si A habla, luego B, luego probablemente A)
3. Perfil de voz (comparar estilo con perfiles conocidos)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any, Protocol
from enum import Enum

logger = logging.getLogger(__name__)


# Verbos de habla en espanol
SPEECH_VERBS: Set[str] = {
    # Neutros - infinitivos y conjugaciones comunes
    'decir', 'dijo', 'dice', 'dije', 'dijeron', 'decía', 'dijiste',
    'hablar', 'hablo', 'habla', 'hablaba', 'hablaron',
    'responder', 'respondio', 'responde', 'respondia', 'respondieron',
    'contestar', 'contesto', 'contesta', 'contestaba', 'contestaron',
    'anadir', 'anadio', 'anade', 'anadia',
    'agregar', 'agrego', 'agrega', 'agregaba',
    'continuar', 'continuo', 'continua', 'continuaba',
    'proseguir', 'prosiguio', 'prosigue',
    'replicar', 'replico', 'replica',

    # Emocionales
    'gritar', 'grito', 'grita', 'gritaba', 'gritaron',
    'susurrar', 'susurro', 'susurra', 'susurraba',
    'murmurar', 'murmuro', 'murmura', 'murmuraba',
    'exclamar', 'exclamo', 'exclama', 'exclamaba',
    'gemir', 'gimio', 'gime', 'gemia',
    'sollozar', 'sollozo', 'solloza', 'sollozaba',
    'chillar', 'chillo', 'chilla', 'chillaba',
    'bramar', 'bramo', 'brama',
    'rugir', 'rugio', 'ruge',

    # Interrogativos
    'preguntar', 'pregunto', 'pregunta', 'preguntaba', 'preguntaron',
    'inquirir', 'inquirio', 'inquiere',
    'interrogar', 'interrogo', 'interroga',
    'cuestionar', 'cuestiono', 'cuestiona',

    # Declarativos
    'afirmar', 'afirmo', 'afirma', 'afirmaba',
    'asegurar', 'aseguro', 'asegura',
    'confirmar', 'confirmo', 'confirma',
    'negar', 'nego', 'niega', 'negaba',

    # Otros
    'comentar', 'comento', 'comenta', 'comentaba',
    'explicar', 'explico', 'explica', 'explicaba',
    'admitir', 'admitio', 'admite', 'admitia',
    'confesar', 'confeso', 'confiesa', 'confesaba',
    'insistir', 'insistio', 'insiste', 'insistia',
    'ordenar', 'ordeno', 'ordena', 'ordenaba',
    'sugerir', 'sugirio', 'sugiere', 'sugeria',
    'advertir', 'advirtio', 'advierte',
    'reclamar', 'reclamo', 'reclama',
    'protestar', 'protesto', 'protesta',
    'objetar', 'objeto', 'objeta',
    'interrumpir', 'interrumpio', 'interrumpe',
    'concluir', 'concluyo', 'concluye',
    'sentenciar', 'sentencio', 'sentencia',
    # Saludos y despedidas
    'saludar', 'saludo', 'saluda', 'saludaba',
    'despedir', 'despidio', 'despide', 'despedia',
}


class AttributionConfidence(Enum):
    """Nivel de confianza de la atribucion."""
    HIGH = "high"       # Verbo de habla explicito
    MEDIUM = "medium"   # Alternancia clara
    LOW = "low"         # Inferido por contexto/perfil
    UNKNOWN = "unknown" # Sin atribucion clara


class AttributionMethod(Enum):
    """Metodo usado para la atribucion."""
    EXPLICIT_VERB = "explicit_verb"     # Verbo de habla + nombre
    ALTERNATION = "alternation"         # Patron de alternancia
    VOICE_PROFILE = "voice_profile"     # Match con perfil de voz
    PROXIMITY = "proximity"             # Mencion cercana
    NONE = "none"                       # Sin metodo aplicable


@dataclass
class DialogueAttribution:
    """Atribucion de hablante para un dialogo."""

    dialogue_id: int
    text: str
    start_char: int
    end_char: int
    chapter: int

    # Atribucion
    speaker_id: Optional[int] = None
    speaker_name: Optional[str] = None
    confidence: AttributionConfidence = AttributionConfidence.UNKNOWN

    # Evidencia
    attribution_method: AttributionMethod = AttributionMethod.NONE
    speech_verb: Optional[str] = None
    context_snippet: str = ""

    # Alternativas consideradas
    alternative_speakers: List[Tuple[int, float]] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
            "context_snippet": self.context_snippet[:50] if self.context_snippet else "",
        }


@dataclass
class SceneParticipants:
    """Participantes de una escena."""
    chapter: int
    scene_start: int
    scene_end: int
    participants: List[int]  # entity_ids


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
    filler_words: List[str]


class SpeakerAttributor:
    """Atribuidor de hablante para dialogos."""

    def __init__(
        self,
        entities: List[Any],
        voice_profiles: Optional[Dict[int, Any]] = None
    ):
        """
        Inicializa el atribuidor.

        Args:
            entities: Lista de entidades del proyecto
            voice_profiles: Diccionario de perfiles de voz por entity_id
        """
        self.entities: Dict[int, Any] = {}
        self.entity_names: Dict[str, int] = {}

        for e in entities:
            entity_id = getattr(e, 'id', None)
            if entity_id is not None:
                self.entities[entity_id] = e

                # Nombre canonico
                name = getattr(e, 'canonical_name', getattr(e, 'name', ''))
                if name:
                    self.entity_names[name.lower()] = entity_id

                # Aliases
                aliases = getattr(e, 'aliases', [])
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
        verbs_pattern = '|'.join(re.escape(v) for v in SPEECH_VERBS)

        # Patron 1: "—dijo Juan" o "—respondio Maria"
        self.pattern_verb_name = re.compile(
            r'[—\-]\s*(' + verbs_pattern + r')\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',
            re.IGNORECASE
        )

        # Patron 2: "Juan dijo:" o "Maria respondio:"
        self.pattern_name_verb = re.compile(
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(' + verbs_pattern + r')\s*[:\.]?\s*[—\-]?',
            re.IGNORECASE
        )

        # Patron 3: ", dijo Juan" (con coma)
        self.pattern_comma_verb_name = re.compile(
            r',\s*(' + verbs_pattern + r')\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',
            re.IGNORECASE
        )

    def attribute_dialogues(
        self,
        dialogues: List[Any],
        entity_mentions: Optional[List[Tuple[int, int, int]]] = None,
        full_text: Optional[str] = None
    ) -> List[DialogueAttribution]:
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
        attributions: List[DialogueAttribution] = []

        # Ordenar dialogos por posicion
        sorted_dialogues = sorted(
            dialogues,
            key=lambda d: getattr(d, 'start_char', 0)
        )

        # Contexto de escena
        current_participants: List[int] = []
        last_speaker: Optional[int] = None
        last_chapter: int = -1

        for i, dialogue in enumerate(sorted_dialogues):
            text = getattr(dialogue, 'text', '')
            start_char = getattr(dialogue, 'start_char', 0)
            end_char = getattr(dialogue, 'end_char', len(text))
            chapter = getattr(dialogue, 'chapter', 1)

            # Reset al cambiar de capitulo
            if chapter != last_chapter:
                current_participants = []
                last_speaker = None
                last_chapter = chapter

            # Obtener contexto del dialogo
            context_after = ""
            if hasattr(dialogue, 'context_after'):
                context_after = dialogue.context_after
            elif full_text and end_char < len(full_text):
                context_after = full_text[end_char:end_char + 150]

            context_before = ""
            if hasattr(dialogue, 'context_before'):
                context_before = dialogue.context_before
            elif full_text and start_char > 0:
                context_before = full_text[max(0, start_char - 150):start_char]

            attr = DialogueAttribution(
                dialogue_id=i,
                text=text,
                start_char=start_char,
                end_char=end_char,
                chapter=chapter,
                context_snippet=context_after[:50] if context_after else ""
            )

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
                if explicit[0] not in current_participants:
                    current_participants.append(explicit[0])
                attributions.append(attr)
                continue

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
                    attr.confidence = AttributionConfidence.MEDIUM
                    attr.attribution_method = AttributionMethod.ALTERNATION
                    last_speaker = other[0]
                    attributions.append(attr)
                    continue

            # 4. Intentar perfil de voz
            if self.voice_profiles and current_participants:
                best_match = self._match_voice_profile(text, current_participants)
                if best_match:
                    attr.speaker_id = best_match
                    attr.speaker_name = self._get_entity_name(best_match)
                    attr.confidence = AttributionConfidence.LOW
                    attr.attribution_method = AttributionMethod.VOICE_PROFILE
                    last_speaker = best_match
                    attributions.append(attr)
                    continue

            # 5. Intentar proximidad simple (entidad mas cercana)
            if nearby:
                closest = nearby[0]  # Ya ordenados por proximidad
                attr.speaker_id = closest
                attr.speaker_name = self._get_entity_name(closest)
                attr.confidence = AttributionConfidence.LOW
                attr.attribution_method = AttributionMethod.PROXIMITY
                last_speaker = closest
                attributions.append(attr)
                continue

            # 6. Sin atribucion clara
            attr.confidence = AttributionConfidence.UNKNOWN
            attr.attribution_method = AttributionMethod.NONE
            attributions.append(attr)

        logger.info(f"Attributed {len(attributions)} dialogues")
        return attributions

    def _get_entity_name(self, entity_id: int) -> str:
        """Obtiene nombre de entidad por ID."""
        entity = self.entities.get(entity_id)
        if entity:
            return getattr(entity, 'canonical_name', getattr(entity, 'name', str(entity_id)))
        return str(entity_id)

    def _detect_explicit_speaker(
        self,
        context_before: str,
        context_after: str,
        entity_mentions: List[Tuple[int, int, int]],
        dialogue_start: int,
        dialogue_end: int
    ) -> Optional[Tuple[int, str]]:
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
        for entity_id, start, end in entity_mentions:
            # Si la mencion esta muy cerca del dialogo
            if (dialogue_start - 100 <= start <= dialogue_start or
                dialogue_end <= start <= dialogue_end + 100):
                # Verificar si hay verbo de habla
                context = context_after[:100].lower()
                for verb in SPEECH_VERBS:
                    if verb in context:
                        return (entity_id, verb)

        return None

    def _get_nearby_entities(
        self,
        position: int,
        entity_mentions: List[Tuple[int, int, int]],
        window: int = 500
    ) -> List[int]:
        """
        Obtiene entidades mencionadas cerca de una posicion.

        Args:
            position: Posicion de referencia
            entity_mentions: Lista de menciones
            window: Ventana de busqueda en caracteres

        Returns:
            Lista de entity_ids ordenados por proximidad
        """
        nearby: List[Tuple[int, int]] = []  # (entity_id, distance)

        for entity_id, start, end in entity_mentions:
            distance = min(abs(start - position), abs(end - position))
            if distance <= window:
                nearby.append((entity_id, distance))

        # Ordenar por distancia y eliminar duplicados
        nearby.sort(key=lambda x: x[1])
        seen: Set[int] = set()
        result: List[int] = []
        for entity_id, _ in nearby:
            if entity_id not in seen:
                seen.add(entity_id)
                result.append(entity_id)

        return result

    def _match_voice_profile(
        self,
        text: str,
        candidates: List[int]
    ) -> Optional[int]:
        """
        Intenta matching por perfil de voz.

        Args:
            text: Texto del dialogo
            candidates: Lista de candidatos (entity_ids)

        Returns:
            entity_id del mejor match o None
        """
        if not candidates or not self.voice_profiles:
            return None

        best_match: Optional[int] = None
        best_score = 0.0

        text_lower = text.lower()
        uses_usted = 'usted' in text_lower
        uses_tu = any(w in text_lower for w in ['tú', 'tu ', ' tu', 'tuyo', 'tuya'])
        word_count = len(text.split())

        for entity_id in candidates:
            if entity_id not in self.voice_profiles:
                continue

            profile = self.voice_profiles[entity_id]
            score = 0.0

            # Matching de formalidad
            profile_uses_usted = getattr(profile, 'uses_usted', False)
            profile_uses_tu = getattr(profile, 'uses_tu', False)

            if uses_usted and profile_uses_usted:
                score += 0.3
            if uses_tu and profile_uses_tu:
                score += 0.3

            # Matching de longitud
            avg_length = getattr(profile, 'avg_intervention_length', 0)
            if avg_length > 0:
                length_diff = abs(word_count - avg_length)
                if length_diff < avg_length * 0.5:
                    score += 0.2

            # Matching de muletillas
            filler_words = getattr(profile, 'filler_words', [])
            for filler in filler_words:
                if filler and filler.lower() in text_lower:
                    score += 0.2
                    break

            if score > best_score:
                best_score = score
                best_match = entity_id

        return best_match if best_score >= 0.3 else None

    def get_attribution_stats(
        self,
        attributions: List[DialogueAttribution]
    ) -> Dict[str, Any]:
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
                'total_dialogues': 0,
                'by_confidence': {'high': 0, 'medium': 0, 'low': 0, 'unknown': 0},
                'by_method': {},
                'attribution_rate': 0.0,
            }

        by_confidence = {
            'high': sum(1 for a in attributions if a.confidence == AttributionConfidence.HIGH),
            'medium': sum(1 for a in attributions if a.confidence == AttributionConfidence.MEDIUM),
            'low': sum(1 for a in attributions if a.confidence == AttributionConfidence.LOW),
            'unknown': sum(1 for a in attributions if a.confidence == AttributionConfidence.UNKNOWN),
        }

        by_method: Dict[str, int] = {}
        for a in attributions:
            method = a.attribution_method.value
            by_method[method] = by_method.get(method, 0) + 1

        by_speaker: Dict[str, int] = {}
        for a in attributions:
            if a.speaker_name:
                by_speaker[a.speaker_name] = by_speaker.get(a.speaker_name, 0) + 1

        attributed = total - by_confidence['unknown']

        return {
            'total_dialogues': total,
            'attributed_dialogues': attributed,
            'by_confidence': by_confidence,
            'by_method': by_method,
            'by_speaker': by_speaker,
            'attribution_rate': attributed / total if total > 0 else 0.0,
        }

    def get_unattributed_dialogues(
        self,
        attributions: List[DialogueAttribution]
    ) -> List[DialogueAttribution]:
        """
        Obtiene dialogos sin atribucion.

        Args:
            attributions: Lista de atribuciones

        Returns:
            Lista de dialogos sin atribuir
        """
        return [a for a in attributions if a.confidence == AttributionConfidence.UNKNOWN]

    def get_low_confidence_dialogues(
        self,
        attributions: List[DialogueAttribution]
    ) -> List[DialogueAttribution]:
        """
        Obtiene dialogos con baja confianza.

        Args:
            attributions: Lista de atribuciones

        Returns:
            Lista de dialogos con confianza LOW o UNKNOWN
        """
        return [
            a for a in attributions
            if a.confidence in (AttributionConfidence.LOW, AttributionConfidence.UNKNOWN)
        ]


def attribute_speakers(
    dialogues: List[Any],
    entities: List[Any],
    entity_mentions: Optional[List[Tuple[int, int, int]]] = None,
    voice_profiles: Optional[Dict[int, Any]] = None,
    full_text: Optional[str] = None
) -> Tuple[List[DialogueAttribution], Dict[str, Any]]:
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
    attributions = attributor.attribute_dialogues(
        dialogues, entity_mentions, full_text
    )
    stats = attributor.get_attribution_stats(attributions)
    return attributions, stats
