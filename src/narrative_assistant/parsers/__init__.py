"""
Parsers module - Lectura de documentos en múltiples formatos.

Formatos soportados:
- DOCX (Microsoft Word) - Prioritario
- TXT/MD (Texto plano/Markdown)
- PDF (con limitaciones)
- EPUB (eBooks)
- ODT (LibreOffice)

Estructura:
- Detección de capítulos y escenas
"""

from .base import (
    MAX_FILE_SIZE_BYTES,
    DocumentFormat,
    DocumentParser,
    RawDocument,
    RawParagraph,
    detect_format,
    get_parser,
)
from .docx_parser import DocxParser
from .sanitization import (
    InputSanitizer,
    get_allowed_document_extensions,
    sanitize_filename,
    validate_file_path,
)
from .structure_detector import (
    Chapter,
    DocumentStructure,
    Scene,
    Section,
    StructureDetector,
    StructureType,
    detect_chapters,
    detect_structure,
)
from .txt_parser import TxtParser

__all__ = [
    # Base
    "DocumentFormat",
    "RawDocument",
    "RawParagraph",
    "DocumentParser",
    "detect_format",
    "get_parser",
    "MAX_FILE_SIZE_BYTES",
    # Parsers
    "DocxParser",
    "TxtParser",
    # Sanitization
    "InputSanitizer",
    "sanitize_filename",
    "validate_file_path",
    "get_allowed_document_extensions",
    # Structure
    "StructureType",
    "Section",
    "Scene",
    "Chapter",
    "DocumentStructure",
    "StructureDetector",
    "detect_structure",
    "detect_chapters",
]
