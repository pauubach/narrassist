"""
Parser para documentos Microsoft Word (DOCX).

DOCX es el formato prioritario para el MVP:
- Más común en flujos editoriales
- Preserva estructura (headings, estilos)
- Mejor soporte para detección de capítulos
"""

import logging
import re
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile

from ..core.errors import CorruptedDocumentError, EmptyDocumentError
from ..core.result import Result
from .base import DocumentFormat, DocumentParser, RawDocument, RawParagraph

logger = logging.getLogger(__name__)

# Patrones para detectar capítulos
CHAPTER_PATTERNS = [
    re.compile(r"^cap[íi]tulo\s+\d+", re.IGNORECASE),
    re.compile(r"^chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^parte\s+\d+", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]+\.\s*", re.IGNORECASE),  # Numeración romana
    re.compile(r"^\d+\.\s+[A-ZÁÉÍÓÚÑ]"),  # "1. Título"
]


class DocxParser(DocumentParser):
    """
    Parser para documentos DOCX.

    Extrae:
    - Párrafos con posiciones de caracteres
    - Headings y niveles
    - Metadatos del documento
    - Detección de posibles capítulos
    """

    format = DocumentFormat.DOCX

    def __init__(self):
        self._docx_available = self._check_dependency()

    def _check_dependency(self) -> bool:
        """Verifica que python-docx está disponible."""
        try:
            import docx

            return True
        except ImportError:
            logger.warning("python-docx no instalado. Instalar con: pip install python-docx")
            return False

    def parse(self, path: Path) -> Result[RawDocument]:
        """
        Parsea un documento DOCX.

        Args:
            path: Ruta al archivo DOCX

        Returns:
            Result con RawDocument o error
        """
        # Validar archivo antes de abrir
        validation_result = self.validate_file(path)
        if validation_result.is_failure:
            return validation_result

        path = validation_result.value

        if not self._docx_available:
            from ..core.errors import NarrativeError, ErrorSeverity

            return Result.failure(
                NarrativeError(
                    message="python-docx not installed",
                    severity=ErrorSeverity.FATAL,
                    user_message="Instala python-docx: pip install python-docx",
                )
            )

        import docx

        try:
            doc = docx.Document(str(path))
        except BadZipFile:
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error="Archivo ZIP inválido (no es un DOCX válido)",
                )
            )
        except Exception as e:
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error=str(e),
                )
            )

        # Extraer metadatos
        metadata = self._extract_metadata(doc)

        # Extraer párrafos
        paragraphs = []
        current_pos = 0

        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()

            # Detectar si es heading
            is_heading, heading_level = self._detect_heading(para)

            raw_para = RawParagraph(
                text=para.text,  # Mantener whitespace original
                index=idx,
                style_name=para.style.name if para.style else "Normal",
                is_heading=is_heading,
                heading_level=heading_level,
                start_char=current_pos,
                end_char=current_pos + len(para.text),
                metadata={
                    "has_bold": self._has_bold(para),
                    "has_italic": self._has_italic(para),
                    "alignment": str(para.alignment) if para.alignment else None,
                },
            )

            paragraphs.append(raw_para)
            current_pos += len(para.text) + 2  # +2 for paragraph separator

        # Verificar que hay contenido
        total_text = sum(len(p.text.strip()) for p in paragraphs)
        if total_text == 0:
            return Result.failure(EmptyDocumentError(file_path=str(path)))

        # Crear documento
        raw_doc = RawDocument(
            paragraphs=paragraphs,
            metadata=metadata,
            source_path=path,
            source_format=DocumentFormat.DOCX,
        )

        # Advertencias
        if self._has_tables(doc):
            raw_doc.add_warning(
                "El documento contiene tablas. El contenido de las tablas puede no extraerse correctamente."
            )

        if self._has_images(doc):
            raw_doc.add_warning("El documento contiene imágenes que serán ignoradas.")

        logger.info(
            f"DOCX parseado: {raw_doc.paragraph_count} párrafos, "
            f"{raw_doc.word_count} palabras, {len(raw_doc.headings)} headings"
        )

        return Result.success(raw_doc)

    def _extract_metadata(self, doc) -> dict:
        """Extrae metadatos del documento."""
        props = doc.core_properties
        return {
            "title": props.title or "",
            "author": props.author or "",
            "subject": props.subject or "",
            "keywords": props.keywords or "",
            "created": props.created.isoformat() if props.created else None,
            "modified": props.modified.isoformat() if props.modified else None,
            "last_modified_by": props.last_modified_by or "",
        }

    def _detect_heading(self, para) -> tuple[bool, Optional[int]]:
        """
        Detecta si un párrafo es un heading.

        Returns:
            Tupla (is_heading, level)
        """
        style_name = para.style.name if para.style else ""

        # Por estilo
        if style_name.startswith("Heading"):
            try:
                level = int(style_name.replace("Heading ", "").strip())
                return True, level
            except ValueError:
                return True, 1

        # Por patrón de texto (capítulos)
        text = para.text.strip()
        for pattern in CHAPTER_PATTERNS:
            if pattern.match(text):
                return True, 1

        return False, None

    def _has_bold(self, para) -> bool:
        """Verifica si el párrafo tiene texto en negrita."""
        for run in para.runs:
            if run.bold:
                return True
        return False

    def _has_italic(self, para) -> bool:
        """Verifica si el párrafo tiene texto en cursiva."""
        for run in para.runs:
            if run.italic:
                return True
        return False

    def _has_tables(self, doc) -> bool:
        """Verifica si el documento tiene tablas."""
        return len(doc.tables) > 0

    def _has_images(self, doc) -> bool:
        """Verifica si el documento tiene imágenes."""
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                return True
        return False
