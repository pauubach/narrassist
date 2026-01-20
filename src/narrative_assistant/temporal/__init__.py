"""
Módulo de análisis temporal para narrativas.

Proporciona herramientas para:
- Extraer marcadores temporales del texto
- Construir timelines narrativos
- Detectar inconsistencias temporales
- Identificar analepsis y prolepsis
"""

from .markers import (
    TemporalMarker,
    MarkerType,
    TemporalMarkerExtractor,
    WORD_TO_NUM,
)
from .timeline import (
    Timeline,
    TimelineEvent,
    TimelineResolution,
    NarrativeOrder,
    TimelineBuilder,
)
from .inconsistencies import (
    # Basic checker
    TemporalInconsistency,
    InconsistencyType,
    InconsistencySeverity,
    TemporalConsistencyChecker,
    # Voting system
    TemporalDetectionMethod,
    TemporalDetectionConfig,
    TemporalCheckResult,
    VotingTemporalChecker,
    get_voting_temporal_checker,
    reset_voting_temporal_checker,
    check_temporal_consistency_voting,
)

__all__ = [
    # Markers
    "TemporalMarker",
    "MarkerType",
    "TemporalMarkerExtractor",
    "WORD_TO_NUM",
    # Timeline
    "Timeline",
    "TimelineEvent",
    "TimelineResolution",
    "NarrativeOrder",
    "TimelineBuilder",
    # Basic Inconsistencies
    "TemporalInconsistency",
    "InconsistencyType",
    "InconsistencySeverity",
    "TemporalConsistencyChecker",
    # Voting System (recommended)
    "TemporalDetectionMethod",
    "TemporalDetectionConfig",
    "TemporalCheckResult",
    "VotingTemporalChecker",
    "get_voting_temporal_checker",
    "reset_voting_temporal_checker",
    "check_temporal_consistency_voting",
]
