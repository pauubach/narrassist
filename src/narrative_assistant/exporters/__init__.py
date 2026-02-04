"""
Exporters module - Exportación de datos a formatos legibles.

Módulos:
- character_sheets: Fichas de personaje (Markdown/JSON)
- style_guide: Guía de estilo automática
- document_exporter: Exportación completa a DOCX/PDF
"""

from .character_sheets import (
    AlertSummary,
    AttributeInfo,
    CharacterSheet,
    MentionInfo,
    VoiceProfileSummary,
    export_all_character_sheets,
    export_character_sheet,
)
from .corrected_document_exporter import (
    CorrectedDocumentExporter,
    TrackChangeOptions,
    export_with_track_changes,
)
from .document_exporter import (
    DocumentExporter,
    ExportOptions,
    ExportSection,
    ProjectExportData,
    collect_export_data,
)
from .review_report_exporter import (
    CategoryStats,
    ReviewReportData,
    ReviewReportExporter,
    ReviewReportOptions,
    export_review_report,
)
from .scrivener_exporter import (
    ScrivenerChapter,
    ScrivenerCharacter,
    ScrivenerExportData,
    ScrivenerExporter,
    ScrivenerExportOptions,
    export_to_scrivener,
)
from .style_guide import (
    StyleGuide,
    export_style_guide,
    generate_style_guide,
)

__all__ = [
    # Character sheets
    "CharacterSheet",
    "AttributeInfo",
    "MentionInfo",
    "VoiceProfileSummary",
    "AlertSummary",
    "export_character_sheet",
    "export_all_character_sheets",
    # Style guide
    "StyleGuide",
    "generate_style_guide",
    "export_style_guide",
    # Document exporter
    "DocumentExporter",
    "ExportOptions",
    "ExportSection",
    "ProjectExportData",
    "collect_export_data",
    # Corrected document exporter
    "CorrectedDocumentExporter",
    "TrackChangeOptions",
    "export_with_track_changes",
    # Review report exporter
    "ReviewReportExporter",
    "ReviewReportOptions",
    "ReviewReportData",
    "CategoryStats",
    "export_review_report",
    # Scrivener exporter
    "ScrivenerExporter",
    "ScrivenerExportOptions",
    "ScrivenerExportData",
    "ScrivenerChapter",
    "ScrivenerCharacter",
    "export_to_scrivener",
]
