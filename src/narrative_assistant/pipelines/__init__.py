"""
Pipeline de integración para análisis completo de manuscritos.

Pipelines disponibles:

1. **unified_analysis** (RECOMENDADO): Pipeline unificado optimizado
   - Integra TODOS los analizadores
   - Sinergias: Diálogos → NER → Correferencias
   - Paralelización donde es posible
   - Ortografía, gramática, repeticiones
   - Análisis de voz, temporal, focalización

2. **analysis_pipeline** (DEPRECATED): Pipeline original paso a paso
   - NER → Atributos → Fusión → Consistencia → Alertas
   - Usar solo para compatibilidad con código existente

Uso recomendado::

    from narrative_assistant.pipelines import run_unified_analysis

    result = run_unified_analysis("novela.docx")
    if result.is_success:
        report = result.value
        print(f"Entidades: {len(report.entities)}")
        print(f"Alertas: {len(report.alerts)}")

Migración desde pipeline legacy::

    # Antes (deprecated)
    from narrative_assistant.pipelines import run_full_analysis
    result = run_full_analysis(path)

    # Ahora (recomendado)
    from narrative_assistant.pipelines import run_unified_analysis
    result = run_unified_analysis(path)
"""

# Unified pipeline (recommended) - importar primero
from .unified_analysis import (
    AnalysisContext,
    AnalysisPhase,
    UnifiedAnalysisPipeline,
    UnifiedConfig,
    UnifiedReport,
    run_unified_analysis,
)

# Export functions (compatible con ambos pipelines)
from .export import (
    export_alerts_json,
    export_report_json,
    export_report_markdown,
)

# Legacy pipeline (deprecated) - mantener para compatibilidad
from .analysis_pipeline import (
    AnalysisReport,
    PipelineConfig,
    run_full_analysis,
)


__all__ = [
    # Unified pipeline (RECOMMENDED)
    "UnifiedReport",
    "UnifiedConfig",
    "UnifiedAnalysisPipeline",
    "run_unified_analysis",
    "AnalysisPhase",
    "AnalysisContext",
    # Export (compatible con ambos)
    "export_report_json",
    "export_report_markdown",
    "export_alerts_json",
    # Legacy pipeline (DEPRECATED - mantener para compatibilidad)
    "AnalysisReport",
    "run_full_analysis",
    "PipelineConfig",
]
