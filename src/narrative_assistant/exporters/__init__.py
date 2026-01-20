"""
Exporters module - Exportación de datos a formatos legibles.

Módulos:
- character_sheets: Fichas de personaje (Markdown/JSON)
- style_guide: Guía de estilo automática
- document_exporter: Exportación completa a DOCX/PDF
"""

from .character_sheets import (
    CharacterSheet,
    AttributeInfo,
    MentionInfo,
    VoiceProfileSummary,
    AlertSummary,
    export_character_sheet,
    export_all_character_sheets,
)
from .style_guide import (
    StyleGuide,
    generate_style_guide,
    export_style_guide,
)
from .document_exporter import (
    DocumentExporter,
    ExportOptions,
    ExportSection,
    ProjectExportData,
    collect_export_data,
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
]
