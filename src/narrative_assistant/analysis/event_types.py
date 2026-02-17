"""
Taxonomía de tipos de eventos narrativos.

Organización en 3 tiers:
- Tier 1 (18 eventos): Alta prioridad, detección crítica
- Tier 2 (15 eventos): Prioridad media, enriquecimiento narrativo
- Tier 3 (12+ eventos): Especialización por género

Referencia: docs/EVENTS_TAXONOMY_IMPLEMENTATION.md
"""

from enum import Enum


class EventTier(Enum):
    """Nivel de prioridad del tipo de evento."""

    TIER_1 = 1  # Alta prioridad - Críticos para continuidad
    TIER_2 = 2  # Prioridad media - Enriquecimiento narrativo
    TIER_3 = 3  # Especialización - Específicos de género


class EventType(Enum):
    """Tipos de eventos narrativos detectables."""

    # ========================================================================
    # TIER 1: Alta Prioridad (18 eventos)
    # ========================================================================

    # Grupo 1: Detección NLP Básica
    PROMISE = "promise"  # Promesa hecha por personaje
    BROKEN_PROMISE = "broken_promise"  # Incumplimiento de promesa previa
    CONFESSION = "confession"  # Confesión de secreto
    LIE = "lie"  # Mentira dicha
    ACQUISITION = "acquisition"  # Obtención de objeto/habilidad
    LOSS = "loss"  # Pérdida de objeto/persona
    INJURY = "injury"  # Herida/lesión de personaje
    HEALING = "healing"  # Curación de herida

    # Grupo 2: Detección Heurística
    FLASHBACK_START = "flashback_start"  # Inicio de analepsis
    FLASHBACK_END = "flashback_end"  # Fin de analepsis
    POV_CHANGE = "pov_change"  # Cambio de punto de vista
    TIME_SKIP = "time_skip"  # Salto temporal explícito
    DREAM_SEQUENCE = "dream_sequence"  # Secuencia onírica
    NARRATIVE_INTRUSION = "narrative_intrusion"  # Interrupción del narrador

    # Grupo 3: Detección LLM
    BETRAYAL = "betrayal"  # Traición entre personajes
    ALLIANCE = "alliance"  # Alianza formada
    REVELATION = "revelation"  # Revelación de información crítica
    DECISION = "decision"  # Decisión importante con consecuencias

    # ========================================================================
    # TIER 2: Prioridad Media (15 eventos)
    # ========================================================================

    # Subgrupo 1: Relaciones entre personajes
    FIRST_MEETING = "first_meeting"  # Primer encuentro entre personajes
    REUNION = "reunion"  # Reencuentro tras separación
    SEPARATION = "separation"  # Separación de personajes
    CONFLICT_START = "conflict_start"  # Inicio de conflicto interpersonal
    CONFLICT_RESOLUTION = "conflict_resolution"  # Resolución de conflicto

    # Subgrupo 2: Transformaciones narrativas
    CHARACTER_TRANSFORMATION = "character_transformation"  # Cambio psicológico profundo
    SOCIAL_CHANGE = "social_change"  # Cambio de estatus social
    LOCATION_CHANGE = "location_change"  # Cambio de escenario principal
    POWER_SHIFT = "power_shift"  # Cambio en balance de poder

    # Subgrupo 3: Eventos de trama
    CLIMAX = "climax"  # Punto culminante de tensión
    TWIST = "twist"  # Giro argumental inesperado
    FORESHADOWING = "foreshadowing"  # Prefiguración de eventos futuros
    CALLBACK = "callback"  # Referencia a evento anterior

    # Subgrupo 4: Meta-narrativos
    CHAPTER_START = "chapter_start"  # Inicio de capítulo
    CHAPTER_END = "chapter_end"  # Fin de capítulo

    # ========================================================================
    # TIER 3: Especialización por Género (12+ eventos)
    # ========================================================================

    # Thriller / Suspense
    CLUE_DISCOVERY = "clue_discovery"  # Descubrimiento de pista
    RED_HERRING = "red_herring"  # Pista falsa
    DANGER_ESCALATION = "danger_escalation"  # Aumento de peligro
    CHASE_START = "chase_start"  # Inicio de persecución

    # Fantasía / Ciencia Ficción
    MAGIC_USE = "magic_use"  # Uso de magia/poder especial
    PROPHECY = "prophecy"  # Profecía revelada
    WORLD_BUILDING = "world_building"  # Expansión de worldbuilding
    PORTAL_CROSSING = "portal_crossing"  # Cruce entre mundos/dimensiones

    # Romance
    ROMANTIC_TENSION = "romantic_tension"  # Tensión romántica
    LOVE_DECLARATION = "love_declaration"  # Declaración de amor
    BREAKUP = "breakup"  # Ruptura de relación
    RECONCILIATION = "reconciliation"  # Reconciliación romántica

    # Universal (aplicable a todos los géneros)
    KNOWLEDGE_TRANSFER = "knowledge_transfer"  # Transmisión o descubrimiento de conocimiento

    # ========================================================================
    # Eventos Básicos Preexistentes (mantener compatibilidad)
    # ========================================================================
    FIRST_APPEARANCE = "first_appearance"  # Primera aparición de personaje
    RETURN = "return"  # Retorno de personaje ausente
    DEATH = "death"  # Muerte de personaje


# Mapeo de tipos de eventos a sus tiers
EVENT_TIER_MAP: dict[EventType, EventTier] = {
    # Tier 1
    EventType.PROMISE: EventTier.TIER_1,
    EventType.BROKEN_PROMISE: EventTier.TIER_1,
    EventType.CONFESSION: EventTier.TIER_1,
    EventType.LIE: EventTier.TIER_1,
    EventType.ACQUISITION: EventTier.TIER_1,
    EventType.LOSS: EventTier.TIER_1,
    EventType.INJURY: EventTier.TIER_1,
    EventType.HEALING: EventTier.TIER_1,
    EventType.FLASHBACK_START: EventTier.TIER_1,
    EventType.FLASHBACK_END: EventTier.TIER_1,
    EventType.POV_CHANGE: EventTier.TIER_1,
    EventType.TIME_SKIP: EventTier.TIER_1,
    EventType.DREAM_SEQUENCE: EventTier.TIER_1,
    EventType.NARRATIVE_INTRUSION: EventTier.TIER_1,
    EventType.BETRAYAL: EventTier.TIER_1,
    EventType.ALLIANCE: EventTier.TIER_1,
    EventType.REVELATION: EventTier.TIER_1,
    EventType.DECISION: EventTier.TIER_1,
    # Tier 2
    EventType.FIRST_MEETING: EventTier.TIER_2,
    EventType.REUNION: EventTier.TIER_2,
    EventType.SEPARATION: EventTier.TIER_2,
    EventType.CONFLICT_START: EventTier.TIER_2,
    EventType.CONFLICT_RESOLUTION: EventTier.TIER_2,
    EventType.CHARACTER_TRANSFORMATION: EventTier.TIER_2,
    EventType.SOCIAL_CHANGE: EventTier.TIER_2,
    EventType.LOCATION_CHANGE: EventTier.TIER_2,
    EventType.POWER_SHIFT: EventTier.TIER_2,
    EventType.CLIMAX: EventTier.TIER_2,
    EventType.TWIST: EventTier.TIER_2,
    EventType.FORESHADOWING: EventTier.TIER_2,
    EventType.CALLBACK: EventTier.TIER_2,
    EventType.CHAPTER_START: EventTier.TIER_2,
    EventType.CHAPTER_END: EventTier.TIER_2,
    # Tier 3
    EventType.CLUE_DISCOVERY: EventTier.TIER_3,
    EventType.RED_HERRING: EventTier.TIER_3,
    EventType.DANGER_ESCALATION: EventTier.TIER_3,
    EventType.CHASE_START: EventTier.TIER_3,
    EventType.MAGIC_USE: EventTier.TIER_3,
    EventType.PROPHECY: EventTier.TIER_3,
    EventType.WORLD_BUILDING: EventTier.TIER_3,
    EventType.PORTAL_CROSSING: EventTier.TIER_3,
    EventType.ROMANTIC_TENSION: EventTier.TIER_3,
    EventType.LOVE_DECLARATION: EventTier.TIER_3,
    EventType.BREAKUP: EventTier.TIER_3,
    EventType.RECONCILIATION: EventTier.TIER_3,
    EventType.KNOWLEDGE_TRANSFER: EventTier.TIER_3,
    # Preexistentes (asignar a Tier 1 por importancia)
    EventType.FIRST_APPEARANCE: EventTier.TIER_1,
    EventType.RETURN: EventTier.TIER_1,
    EventType.DEATH: EventTier.TIER_1,
}


# Pares de eventos que requieren rastreo de continuidad
EVENT_PAIRS: list[tuple[EventType, EventType]] = [
    (EventType.PROMISE, EventType.BROKEN_PROMISE),
    (EventType.INJURY, EventType.HEALING),
    (EventType.ACQUISITION, EventType.LOSS),
    (EventType.LIE, EventType.CONFESSION),
    (EventType.FLASHBACK_START, EventType.FLASHBACK_END),
    (EventType.CONFLICT_START, EventType.CONFLICT_RESOLUTION),
    (EventType.SEPARATION, EventType.REUNION),
    (EventType.ALLIANCE, EventType.BETRAYAL),
]


def get_event_tier(event_type: EventType) -> EventTier:
    """Obtiene el tier de un tipo de evento."""
    return EVENT_TIER_MAP.get(event_type, EventTier.TIER_3)


def get_paired_event(event_type: EventType) -> EventType | None:
    """
    Obtiene el evento par de un tipo (si existe).

    Ej: PROMISE → BROKEN_PROMISE, INJURY → HEALING
    """
    for pair in EVENT_PAIRS:
        if pair[0] == event_type:
            return pair[1]
        if pair[1] == event_type:
            return pair[0]
    return None


def get_events_by_tier(tier: EventTier) -> list[EventType]:
    """Obtiene todos los eventos de un tier específico."""
    return [
        event_type
        for event_type, event_tier in EVENT_TIER_MAP.items()
        if event_tier == tier
    ]
