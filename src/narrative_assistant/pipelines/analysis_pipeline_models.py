"""Modelos y configuracion del pipeline legacy de analisis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..alerts.models import Alert, AlertSeverity
from ..analysis.emotional_coherence import EmotionalIncoherence
from ..core.errors import NarrativeError
from ..entities.models import Entity
from ..focalization import FocalizationDeclaration, FocalizationViolation
from ..parsers.document_classifier import DocumentClassification, DocumentType
from ..temporal import TemporalInconsistency, Timeline
from ..voice import VoiceDeviation, VoiceProfile


@dataclass
class PipelineConfig:
    """
    Configuracion del pipeline de analisis.

    Attributes:
        run_ner: Ejecutar NER (extraccion de entidades)
        run_attributes: Ejecutar extraccion de atributos
        run_consistency: Ejecutar analisis de consistencia
        run_temporal: Ejecutar analisis temporal (timeline)
        create_alerts: Crear alertas en la base de datos
        min_confidence: Confianza minima para alertas
        batch_size: Tamaño de batch para procesamiento NLP
        force_reanalysis: Si True, limpia datos previos y re-analiza
        use_hybrid_extraction: Usar pipeline hibrido (regex+dependency+embeddings)
        use_llm_extraction: Usar LLM local (Ollama) para extraccion
        llm_ensemble_mode: Usar multiples modelos LLM con votacion
        llm_models: Lista de modelos Ollama a usar
    """

    run_ner: bool = True
    run_attributes: bool = True
    run_consistency: bool = True
    run_temporal: bool = True
    run_voice: bool = True
    run_focalization: bool = False
    run_emotional: bool = True
    create_alerts: bool = True
    min_confidence: float = 0.5
    batch_size: int | None = None
    force_reanalysis: bool = False
    use_hybrid_extraction: bool = True
    use_llm_extraction: bool = False
    llm_ensemble_mode: bool = False
    llm_models: list[str] | None = None


@dataclass
class SectionInfo:
    """Informacion de una seccion dentro de un capitulo."""

    number: int
    title: str | None
    heading_level: int
    start_char: int
    end_char: int
    subsections: list["SectionInfo"] = field(default_factory=list)


@dataclass
class ChapterInfo:
    """Informacion de un capitulo detectado."""

    number: int
    title: str | None
    content: str
    start_char: int
    end_char: int
    word_count: int
    structure_type: str = "chapter"
    sections: list[SectionInfo] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """
    Informe de analisis completo del pipeline legacy.

    Mantiene el contrato historico para compatibilidad.
    """

    project_id: int
    session_id: int
    document_path: str
    document_fingerprint: str
    entities: list[Entity] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    chapters: list[ChapterInfo] = field(default_factory=list)
    document_type: DocumentType = DocumentType.UNKNOWN
    document_classification: DocumentClassification | None = None
    timeline: Timeline | None = None
    temporal_inconsistencies: list[TemporalInconsistency] = field(default_factory=list)
    voice_profiles: list[VoiceProfile] = field(default_factory=list)
    voice_deviations: list[VoiceDeviation] = field(default_factory=list)
    focalization_declarations: list[FocalizationDeclaration] = field(default_factory=list)
    focalization_violations: list[FocalizationViolation] = field(default_factory=list)
    emotional_incoherences: list[EmotionalIncoherence] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    errors: list[NarrativeError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def critical_alerts(self) -> list[Alert]:
        return [alert for alert in self.alerts if alert.severity == AlertSeverity.CRITICAL]

    @property
    def warning_alerts(self) -> list[Alert]:
        return [alert for alert in self.alerts if alert.severity == AlertSeverity.WARNING]
