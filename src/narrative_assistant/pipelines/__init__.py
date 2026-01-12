"""
Pipeline de integración para análisis completo de manuscritos.

Este módulo orquesta el flujo completo:
1. Parsing del documento (DOCX, TXT, etc.)
2. Extracción NLP (NER, atributos)
3. Análisis de consistencia
4. Generación de alertas
5. Persistencia en base de datos
6. Exportación de informes
"""

from .analysis_pipeline import (
    AnalysisReport,
    run_full_analysis,
    PipelineConfig,
)
from .export import (
    export_report_json,
    export_report_markdown,
    export_alerts_json,
)

__all__ = [
    "AnalysisReport",
    "run_full_analysis",
    "PipelineConfig",
    "export_report_json",
    "export_report_markdown",
    "export_alerts_json",
]
