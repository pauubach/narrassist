"""
Módulo de análisis temporal para narrativas.

Proporciona herramientas para:
- Extraer marcadores temporales del texto
- Construir timelines narrativos
- Detectar inconsistencias temporales
- Identificar analepsis y prolepsis
"""

from .inconsistencies import (  # Voting system; Basic checker
    InconsistencySeverity, InconsistencyType, TemporalCheckResult,
    TemporalConsistencyChecker, TemporalDetectionConfig,
    TemporalDetectionMethod, TemporalInconsistency, VotingTemporalChecker,
    check_temporal_consistency_voting, get_voting_temporal_checker,
    reset_voting_temporal_checker)
from .markers import (WORD_TO_NUM, MarkerType, TemporalMarker,
                      TemporalMarkerExtractor)
from .non_linear_detector import NonLinearNarrativeDetector, NonLinearSignal
from .temporal_map import (AgeReference, NarrativeType, TemporalMap,
                           TemporalSlice)
from .timeline import (NarrativeOrder, Timeline, TimelineBuilder,
                       TimelineEvent, TimelineResolution)

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
    # Temporal Map (non-linear narratives)
    "TemporalMap",
    "TemporalSlice",
    "NarrativeType",
    "AgeReference",
    # Non-linear detector
    "NonLinearNarrativeDetector",
    "NonLinearSignal",
]
