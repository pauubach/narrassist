"""
Tipos de datos para Speech Tracking.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricChangeResult:
    """Resultado de comparación de una métrica entre dos ventanas."""

    metric_name: str
    value1: float
    value2: float
    relative_change: float  # Cambio relativo (0.0 = sin cambio, 1.0 = 100% cambio)
    p_value: float  # Significancia estadística (< 0.05 = significativo)
    is_significant: bool  # True si p_value < 0.05 y relative_change > threshold


@dataclass
class NarrativeContext:
    """Contexto narrativo detectado entre ventanas."""

    has_dramatic_event: bool = False
    event_type: Optional[str] = None  # "muerte", "boda", "pelea", "trauma"
    event_chapter: Optional[int] = None
    keywords_found: list[str] = field(default_factory=list)


@dataclass
class SpeechChangeAlert:
    """
    Alerta de cambio en el habla de un personaje.

    Representa un cambio estadísticamente significativo en las características
    de habla de un personaje entre dos ventanas temporales.
    """

    character_id: int
    character_name: str
    window1_chapters: str  # Ej: "1-3"
    window2_chapters: str  # Ej: "7-9"
    changed_metrics: dict[str, MetricChangeResult]
    confidence: float  # Confianza agregada (0.0-1.0)
    severity: str  # "low", "medium", "high"
    narrative_context: Optional[NarrativeContext] = None

    # Datos para UI
    description: str = ""
    suggestion: str = ""
    evidence: dict = field(default_factory=dict)

    def __post_init__(self):
        """Genera descripción y sugerencia automáticamente."""
        if not self.description:
            self.description = self._generate_description()
        if not self.suggestion:
            self.suggestion = self._generate_suggestion()
        if not self.evidence:
            self.evidence = self._generate_evidence()

    def _generate_description(self) -> str:
        """Genera descripción legible del cambio."""
        metric_descriptions = []

        for metric_name, result in self.changed_metrics.items():
            metric_label = self._metric_label(metric_name)
            change_direction = "↑" if result.value2 > result.value1 else "↓"
            change_pct = abs(result.relative_change * 100)

            metric_descriptions.append(
                f"{metric_label}: {result.value1:.1f} → {result.value2:.1f} "
                f"({change_direction}{change_pct:.0f}%)"
            )

        metrics_text = ", ".join(metric_descriptions)

        return (
            f"**{self.character_name}** cambió su forma de hablar entre "
            f"capítulos {self.window1_chapters} y {self.window2_chapters}. "
            f"Cambios detectados: {metrics_text}."
        )

    def _generate_suggestion(self) -> str:
        """Genera sugerencia de revisión."""
        if self.narrative_context and self.narrative_context.has_dramatic_event:
            event = self.narrative_context.event_type
            return (
                f"Se detectó un evento dramático ({event}) entre las ventanas. "
                f"Revisar si el cambio de habla es intencional y coherente con "
                f"el desarrollo del personaje."
            )

        return (
            f"Revisar diálogos de {self.character_name} en capítulos "
            f"{self.window2_chapters} para verificar si el cambio de habla "
            f"es intencional o una inconsistencia. Si es intencional, considerar "
            f"añadir contexto narrativo que lo justifique."
        )

    def _generate_evidence(self) -> dict:
        """Genera evidencia estructurada para la UI."""
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "window1": self.window1_chapters,
            "window2": self.window2_chapters,
            "metrics_changed": list(self.changed_metrics.keys()),
            "confidence": self.confidence,
            "severity": self.severity,
            "has_context": self.narrative_context is not None,
        }

    @staticmethod
    def _metric_label(metric_name: str) -> str:
        """Etiqueta legible de la métrica."""
        labels = {
            "filler_rate": "Muletillas",
            "formality_score": "Formalidad",
            "avg_sentence_length": "Long. oraciones",
            "lexical_diversity": "Riqueza léxica",
            "exclamation_rate": "Exclamaciones",
            "question_rate": "Preguntas",
        }
        return labels.get(metric_name, metric_name)
