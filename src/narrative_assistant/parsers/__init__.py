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
    DocumentFormat,
    RawDocument,
    RawParagraph,
    DocumentParser,
    detect_format,
    get_parser,
)
from .docx_parser import DocxParser
from .txt_parser import TxtParser
from .sanitization import (
    InputSanitizer,
    sanitize_filename,
    validate_file_path,
    get_allowed_document_extensions,
)
from .structure_detector import (
    StructureType,
    Scene,
    Chapter,
    DocumentStructure,
    StructureDetector,
    detect_structure,
    detect_chapters,
)
from .base import MAX_FILE_SIZE_BYTES

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
    "Scene",
    "Chapter",
    "DocumentStructure",
    "StructureDetector",
    "detect_structure",
    "detect_chapters",
]
