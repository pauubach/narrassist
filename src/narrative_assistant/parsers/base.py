"""
Base classes y utilidades para parsers de documentos.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from ..core.errors import UnsupportedFormatError, NarrativeError, ErrorSeverity
from ..core.result import Result

logger = logging.getLogger(__name__)

# Límite de tamaño de archivo por defecto (50 MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class DocumentFormat(Enum):
    """Formatos de documento soportados."""

    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    PDF = "pdf"
    EPUB = "epub"
    ODT = "odt"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> "DocumentFormat":
        """Obtiene formato desde extensión de archivo."""
        ext = ext.lower().lstrip(".")
        mapping = {
            "docx": cls.DOCX,
            "doc": cls.DOCX,  # Intentar como DOCX, puede fallar
            "txt": cls.TXT,
            "md": cls.MD,
            "markdown": cls.MD,
            "pdf": cls.PDF,
            "epub": cls.EPUB,
            "odt": cls.ODT,
        }
        return mapping.get(ext, cls.UNKNOWN)


@dataclass
class RawParagraph:
    """
    Párrafo extraído de un documento.

    Attributes:
        text: Texto del párrafo
        index: Índice del párrafo en el documento
        style_name: Nombre del estilo (Heading 1, Normal, etc.)
        is_heading: True si es un encabezado
        heading_level: Nivel de heading (1-6) o None
        start_char: Posición de inicio en el texto completo
        end_char: Posición de fin en el texto completo
        metadata: Metadatos adicionales del párrafo
    """

    text: str
    index: int = 0
    style_name: str = "Normal"
    is_heading: bool = False
    heading_level: Optional[int] = None
    start_char: int = 0
    end_char: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """True si el párrafo está vacío o solo tiene whitespace."""
        return not self.text.strip()

    @property
    def word_count(self) -> int:
        """Número de palabras en el párrafo."""
        return len(self.text.split())


@dataclass
class RawDocument:
    """
    Documento parseado sin procesar.

    Attributes:
        paragraphs: Lista de párrafos extraídos
        metadata: Metadatos del documento (autor, título, etc.)
        source_path: Ruta al archivo original
        source_format: Formato detectado
        full_text: Texto completo concatenado
        warnings: Advertencias durante el parseo
    """

    paragraphs: list[RawParagraph] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source_path: Optional[Path] = None
    source_format: DocumentFormat = DocumentFormat.UNKNOWN
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Texto completo del documento."""
        return "\n\n".join(p.text for p in self.paragraphs if not p.is_empty)

    @property
    def word_count(self) -> int:
        """Número total de palabras."""
        return sum(p.word_count for p in self.paragraphs)

    @property
    def paragraph_count(self) -> int:
        """Número de párrafos no vacíos."""
        return sum(1 for p in self.paragraphs if not p.is_empty)

    @property
    def headings(self) -> list[RawParagraph]:
        """Lista de párrafos que son headings."""
        return [p for p in self.paragraphs if p.is_heading]

    def add_warning(self, message: str) -> None:
        """Añade una advertencia."""
        self.warnings.append(message)
        logger.warning(f"Parser: {message}")


class DocumentParser(ABC):
    """
    Clase base abstracta para parsers de documentos.

    Subclases deben implementar:
    - parse(path) -> Result[RawDocument]
    - parse_text(text) -> Result[RawDocument] (opcional)
    """

    format: DocumentFormat = DocumentFormat.UNKNOWN
    max_file_size: int = MAX_FILE_SIZE_BYTES

    def validate_file(self, path: Path) -> Result[Path]:
        """
        Valida que el archivo existe, tiene extensión válida y no excede límite de tamaño.

        Args:
            path: Ruta al archivo

        Returns:
            Result con path validado o error
        """
        from .sanitization import validate_file_path, get_allowed_document_extensions

        # Validar path (incluye check de existencia y path traversal)
        try:
            validated_path = validate_file_path(
                path,
                must_exist=True,
                allowed_extensions=get_allowed_document_extensions(),
            )
        except FileNotFoundError as e:
            return Result.failure(
                NarrativeError(
                    message=str(e),
                    severity=ErrorSeverity.FATAL,
                    user_message=f"Archivo no encontrado: {path}",
                )
            )
        except ValueError as e:
            return Result.failure(
                NarrativeError(
                    message=str(e),
                    severity=ErrorSeverity.FATAL,
                    user_message=str(e),
                )
            )
        except PermissionError as e:
            return Result.failure(
                NarrativeError(
                    message=str(e),
                    severity=ErrorSeverity.FATAL,
                    user_message="Acceso denegado al archivo",
                )
            )

        # Verificar tamaño
        file_size = validated_path.stat().st_size
        if file_size > self.max_file_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.max_file_size / (1024 * 1024)
            return Result.failure(
                NarrativeError(
                    message=f"File too large: {size_mb:.1f}MB > {max_mb:.1f}MB",
                    severity=ErrorSeverity.FATAL,
                    user_message=f"Archivo demasiado grande ({size_mb:.1f} MB). Máximo permitido: {max_mb:.0f} MB",
                )
            )

        return Result.success(validated_path)

    @abstractmethod
    def parse(self, path: Path) -> Result[RawDocument]:
        """
        Parsea un documento desde archivo.

        Args:
            path: Ruta al archivo

        Returns:
            Result con RawDocument o error
        """
        pass

    def parse_text(self, text: str) -> Result[RawDocument]:
        """
        Parsea texto plano.

        Implementación por defecto: crear documento con un solo párrafo.
        Subclases pueden sobrescribir para lógica específica.
        """
        paragraphs = []
        current_pos = 0

        for idx, para_text in enumerate(text.split("\n\n")):
            para_text = para_text.strip()
            if para_text:
                paragraphs.append(
                    RawParagraph(
                        text=para_text,
                        index=idx,
                        start_char=current_pos,
                        end_char=current_pos + len(para_text),
                    )
                )
            current_pos += len(para_text) + 2  # +2 for \n\n

        doc = RawDocument(
            paragraphs=paragraphs,
            source_format=self.format,
        )

        return Result.success(doc)

    def can_parse(self, path: Path) -> bool:
        """Verifica si este parser puede procesar el archivo."""
        detected = DocumentFormat.from_extension(path.suffix)
        return detected == self.format


def detect_format(path: Path) -> DocumentFormat:
    """
    Detecta el formato de un documento.

    Usa extensión y opcionalmente magic bytes.
    """
    # Por extensión
    fmt = DocumentFormat.from_extension(path.suffix)

    if fmt != DocumentFormat.UNKNOWN:
        return fmt

    # Fallback: intentar detectar por contenido
    try:
        with open(path, "rb") as f:
            header = f.read(8)

        # DOCX/XLSX/PPTX son ZIPs
        if header[:4] == b"PK\x03\x04":
            return DocumentFormat.DOCX

        # PDF
        if header[:4] == b"%PDF":
            return DocumentFormat.PDF

        # Texto plano (heurística)
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.read(1000)
            return DocumentFormat.TXT
        except UnicodeDecodeError:
            pass

    except Exception as e:
        logger.warning(f"Error detectando formato de {path}: {e}")

    return DocumentFormat.UNKNOWN


def get_parser(format_or_path: Union[DocumentFormat, Path, str]) -> DocumentParser:
    """
    Obtiene el parser apropiado para un formato o archivo.

    Args:
        format_or_path: DocumentFormat, Path, o string con extensión

    Returns:
        DocumentParser apropiado

    Raises:
        UnsupportedFormatError: Si el formato no está soportado
    """
    # Resolver formato
    if isinstance(format_or_path, DocumentFormat):
        fmt = format_or_path
    elif isinstance(format_or_path, (Path, str)):
        path = Path(format_or_path)
        fmt = detect_format(path)
    else:
        raise ValueError(f"Tipo no soportado: {type(format_or_path)}")

    # Importar parsers aquí para evitar imports circulares
    from .docx_parser import DocxParser
    from .txt_parser import TxtParser

    parsers = {
        DocumentFormat.DOCX: DocxParser,
        DocumentFormat.TXT: TxtParser,
        DocumentFormat.MD: TxtParser,  # MD usa el mismo parser que TXT
    }

    # PDF, EPUB, ODT requieren dependencias opcionales
    if fmt == DocumentFormat.PDF:
        try:
            from .pdf_parser import PdfParser
            parsers[DocumentFormat.PDF] = PdfParser
        except ImportError:
            raise UnsupportedFormatError(
                file_path=str(format_or_path) if not isinstance(format_or_path, DocumentFormat) else "",
                detected_format="PDF (requiere: pip install pdfplumber)",
            )

    if fmt == DocumentFormat.EPUB:
        try:
            from .epub_parser import EpubParser
            parsers[DocumentFormat.EPUB] = EpubParser
        except ImportError:
            raise UnsupportedFormatError(
                file_path=str(format_or_path) if not isinstance(format_or_path, DocumentFormat) else "",
                detected_format="EPUB (requiere: pip install ebooklib)",
            )

    if fmt == DocumentFormat.ODT:
        try:
            from .odt_parser import OdtParser
            parsers[DocumentFormat.ODT] = OdtParser
        except ImportError:
            raise UnsupportedFormatError(
                file_path=str(format_or_path) if not isinstance(format_or_path, DocumentFormat) else "",
                detected_format="ODT (requiere: pip install odfpy)",
            )

    if fmt not in parsers or fmt == DocumentFormat.UNKNOWN:
        raise UnsupportedFormatError(
            file_path=str(format_or_path) if not isinstance(format_or_path, DocumentFormat) else "",
            detected_format=fmt.value,
        )

    return parsers[fmt]()


def calculate_page_and_line(
    start_char: int,
    raw_document: RawDocument,
    words_per_page: int = 300
) -> tuple[int, int]:
    """
    Calcula número de página y línea desde posición de carácter.

    Args:
        start_char: Posición del carácter en el documento completo
        raw_document: Documento parseado con full_text
        words_per_page: Palabras por página para cálculo heurístico (default: 300)

    Returns:
        (page_number, line_number)

    Notes:
        - Page: Basado en heurística de palabras/página (~300 palabras)
        - Line: Conteo de saltos de línea desde inicio del documento

    Example:
        >>> doc = RawDocument(...)
        >>> page, line = calculate_page_and_line(1234, doc)
        >>> print(f"Página {page}, línea {line}")
        Página 5, línea 42
    """
    # Obtener texto completo del documento
    full_text = raw_document.full_text

    # Validar que start_char está dentro del documento
    if start_char < 0 or start_char > len(full_text):
        logger.warning(
            f"start_char {start_char} fuera de rango [0, {len(full_text)}]"
        )
        return 1, 1  # Default: página 1, línea 1

    # Calcular línea: contar saltos de línea hasta start_char
    text_until_position = full_text[:start_char]
    line_number = text_until_position.count('\n') + 1

    # Calcular página: heurística basada en palabras
    # Contar palabras hasta la posición
    words_until_position = len(text_until_position.split())

    # Calcular número de página (redondeando hacia arriba)
    if words_until_position == 0:
        page_number = 1
    else:
        page_number = (words_until_position // words_per_page) + 1

    return page_number, line_number
