"""
Interactions module - Detección y análisis de interacciones entre entidades.

Componentes:
- models: Tipos de interacción, patrones
- detector: Detección de interacciones en texto
- pattern_analyzer: Análisis de patrones de interacción
- repository: Persistencia de interacciones
"""

from .detector import (
    InteractionDetector,
    detect_interactions_in_text,
)
from .models import (
    ACTION_VERBS_NEGATIVE,
    ACTION_VERBS_NEUTRAL,
    ACTION_VERBS_POSITIVE,
    DIALOGUE_VERBS,
    # Constants
    INTERACTION_TYPE_INTENSITY,
    PHYSICAL_CONTACT_VERBS,
    THOUGHT_VERBS,
    # Dataclasses
    EntityInteraction,
    InteractionAlert,
    InteractionPattern,
    InteractionTone,
    # Enums
    InteractionType,
)
from .pattern_analyzer import (
    InteractionPatternAnalyzer,
)
from .repository import (
    InteractionRepository,
)

__all__ = [
    # Enums
    "InteractionType",
    "InteractionTone",
    # Dataclasses
    "EntityInteraction",
    "InteractionPattern",
    "InteractionAlert",
    # Constants
    "INTERACTION_TYPE_INTENSITY",
    "DIALOGUE_VERBS",
    "ACTION_VERBS_POSITIVE",
    "ACTION_VERBS_NEGATIVE",
    "ACTION_VERBS_NEUTRAL",
    "THOUGHT_VERBS",
    "PHYSICAL_CONTACT_VERBS",
    # Detector
    "InteractionDetector",
    "detect_interactions_in_text",
    # Pattern Analyzer
    "InteractionPatternAnalyzer",
    # Repository
    "InteractionRepository",
]
