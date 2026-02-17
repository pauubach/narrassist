"""
Speech Tracking Module - Detección de Inconsistencias de Habla por Personaje.

Este módulo detecta cambios abruptos en la forma de hablar de los personajes
a lo largo del manuscrito, identificando posibles inconsistencias en:
- Uso de muletillas (filler words)
- Registro lingüístico (formal/coloquial)
- Longitud promedio de oraciones
- Riqueza léxica
- Patrones de puntuación (exclamaciones, preguntas)

El sistema usa ventanas deslizantes temporales para comparar el habla
del personaje en diferentes secciones del manuscrito, aplicando pruebas
estadísticas (chi-cuadrado, z-test) para determinar si los cambios
son estadísticamente significativos.
"""

from .speech_tracker import SpeechTracker
from .speech_window import SpeechWindow, create_sliding_windows
from .metrics import SpeechMetrics, TRACKED_METRICS
from .change_detector import ChangeDetector, MetricChangeResult
from .contextual_analyzer import ContextualAnalyzer
from .cache import MetricsCache, get_metrics_cache, clear_metrics_cache
from .types import SpeechChangeAlert, NarrativeContext

__all__ = [
    "SpeechTracker",
    "SpeechWindow",
    "create_sliding_windows",
    "SpeechMetrics",
    "TRACKED_METRICS",
    "ChangeDetector",
    "MetricChangeResult",
    "ContextualAnalyzer",
    "MetricsCache",
    "get_metrics_cache",
    "clear_metrics_cache",
    "SpeechChangeAlert",
    "NarrativeContext",
]
