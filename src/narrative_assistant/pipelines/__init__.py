"""
Pipeline de integración para análisis completo de manuscritos.

Pipelines disponibles:

1. **analysis_pipeline** (legacy): Pipeline original paso a paso
   - NER → Atributos → Fusión → Consistencia → Alertas

2. **unified_analysis** (nuevo): Pipeline unificado optimizado
   - Integra TODOS los analizadores
   - Sinergias: Diálogos → NER → Correferencias
   - Paralelización donde es posible
   - Ortografía, gramática, repeticiones
   - Análisis de voz, temporal, focalización (experimental)

Uso recomendado:
    from narrative_assistant.pipelines import run_unified_analysis

    result = run_unified_analysis("novela.docx")
    if result.is_success:
        report = result.value
        print(f"Entidades: {len(report.entities)}")
        print(f"Alertas: {len(report.alerts)}")
"""

from .analysis_pipeline import (
    AnalysisReport,
    run_full_analysis,
    PipelineConfig,
)
from .unified_analysis import (
    UnifiedReport,
    UnifiedConfig,
    UnifiedAnalysisPipeline,
    run_unified_analysis,
    AnalysisPhase,
    AnalysisContext,
)
from .export import (
    export_report_json,
    export_report_markdown,
    export_alerts_json,
)

__all__ = [
    # Legacy pipeline
    "AnalysisReport",
    "run_full_analysis",
    "PipelineConfig",
    # Unified pipeline (recommended)
    "UnifiedReport",
    "UnifiedConfig",
    "UnifiedAnalysisPipeline",
    "run_unified_analysis",
    "AnalysisPhase",
    "AnalysisContext",
    # Export
    "export_report_json",
    "export_report_markdown",
    "export_alerts_json",
]
