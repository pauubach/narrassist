"""
Módulo de análisis de voz y registro para narrativas.

Proporciona herramientas para:
- Construir perfiles de voz por personaje
- Detectar desviaciones del patrón de voz
- Analizar cambios de registro
- Identificar inconsistencias estilísticas en diálogos
"""

from .profiles import (
    VoiceProfile,
    VoiceMetrics,
    VoiceProfileBuilder,
)
from .deviations import (
    VoiceDeviation,
    DeviationType,
    VoiceDeviationDetector,
)
from .register import (
    RegisterType,
    RegisterAnalysis,
    RegisterChange,
    RegisterAnalyzer,
    RegisterChangeDetector,
    FORMAL_INDICATORS,
    COLLOQUIAL_INDICATORS,
    analyze_register_changes,
)
from .speaker_attribution import (
    AttributionConfidence,
    AttributionMethod,
    DialogueAttribution,
    SceneParticipants,
    SpeakerAttributor,
    SPEECH_VERBS,
    attribute_speakers,
)

__all__ = [
    # Profiles
    "VoiceProfile",
    "VoiceMetrics",
    "VoiceProfileBuilder",
    # Deviations
    "VoiceDeviation",
    "DeviationType",
    "VoiceDeviationDetector",
    # Register
    "RegisterType",
    "RegisterAnalysis",
    "RegisterChange",
    "RegisterAnalyzer",
    "RegisterChangeDetector",
    "FORMAL_INDICATORS",
    "COLLOQUIAL_INDICATORS",
    "analyze_register_changes",
    # Speaker Attribution
    "AttributionConfidence",
    "AttributionMethod",
    "DialogueAttribution",
    "SceneParticipants",
    "SpeakerAttributor",
    "SPEECH_VERBS",
    "attribute_speakers",
]
