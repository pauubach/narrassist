"""
Parser para documentos PDF.

Utiliza pdfplumber para extracción de texto con información de layout.
Detecta estructura de capítulos basada en formato de texto (fuente, tamaño).
"""

import logging
import re
from pathlib import Path
from typing import Optional

from ..core.errors import CorruptedDocumentError, EmptyDocumentError
from ..core.result import Result
from .base import DocumentFormat, DocumentParser, RawDocument, RawParagraph

logger = logging.getLogger(__name__)

# Patrones para detectar capítulos (igual que en docx_parser)
CHAPTER_PATTERNS = [
    re.compile(r"^cap[íi]tulo\s+\d+", re.IGNORECASE),
    re.compile(r"^chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^parte\s+\d+", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]+\.\s*", re.IGNORECASE),
    re.compile(r"^\d+\.\s+[A-ZÁÉÍÓÚÑ]"),
]

# Tamaño mínimo de fuente para considerar como heading (relativo al texto normal)
HEADING_FONT_SIZE_RATIO = 1.2


class PdfParser(DocumentParser):
    """
    Parser para documentos PDF.

    Extrae:
    - Texto por páginas con posiciones de caracteres
    - Detección de headings por tamaño de fuente
    - Metadatos del documento (si disponibles)
    - Información de páginas en metadata de párrafos
    """

    format = DocumentFormat.PDF

    def __init__(self):
        self._pdfplumber_available = self._check_dependency()

    def _check_dependency(self) -> bool:
        """Verifica que pdfplumber está disponible."""
        try:
            import pdfplumber
            return True
        except ImportError:
            logger.warning(
                "pdfplumber no instalado. Instalar con: pip install pdfplumber"
            )
            return False

    def parse(self, path: Path) -> Result[RawDocument]:
        """
        Parsea un documento PDF.

        Args:
            path: Ruta al archivo PDF

        Returns:
            Result con RawDocument o error
        """
        # Validar archivo antes de abrir
        validation_result = self.validate_file(path)
        if validation_result.is_failure:
            return validation_result

        path = validation_result.value

        if not self._pdfplumber_available:
            from ..core.errors import NarrativeError, ErrorSeverity

            return Result.failure(
                NarrativeError(
                    message="pdfplumber not installed",
                    severity=ErrorSeverity.FATAL,
                    user_message="Instala pdfplumber: pip install pdfplumber",
                )
            )

        import pdfplumber

        try:
            pdf = pdfplumber.open(str(path))
        except Exception as e:
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error=f"No se pudo abrir el PDF: {str(e)}",
                )
            )

        try:
            # Extraer metadatos
            metadata = self._extract_metadata(pdf)

            # Extraer texto por páginas
            paragraphs = []
            current_char_pos = 0
            paragraph_index = 0
            base_font_size = None

            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_paragraphs, base_font_size = self._extract_page_paragraphs(
                        page, page_num, paragraph_index, current_char_pos, base_font_size
                    )

                    for para in page_paragraphs:
                        paragraphs.append(para)
                        current_char_pos = para.end_char + 2  # +2 para separador \n\n
                        paragraph_index += 1

                except Exception as e:
                    logger.warning(f"Error procesando página {page_num}: {e}")
                    # Continuar con las siguientes páginas

            pdf.close()

        except Exception as e:
            pdf.close()
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error=str(e),
                )
            )

        # Verificar que hay contenido
        total_text = sum(len(p.text.strip()) for p in paragraphs)
        if total_text == 0:
            return Result.failure(EmptyDocumentError(file_path=str(path)))

        # Post-proceso: detectar capítulos por patrón de texto
        self._detect_chapters_by_pattern(paragraphs)

        # Crear documento
        raw_doc = RawDocument(
            paragraphs=paragraphs,
            metadata=metadata,
            source_path=path,
            source_format=DocumentFormat.PDF,
        )

        # Advertencias
        if metadata.get("is_encrypted"):
            raw_doc.add_warning("El PDF está encriptado. Algunos contenidos pueden no extraerse.")

        if metadata.get("has_images"):
            raw_doc.add_warning("El documento contiene imágenes que serán ignoradas.")

        logger.info(
            f"PDF parseado: {raw_doc.paragraph_count} párrafos, "
            f"{raw_doc.word_count} palabras, {metadata.get('page_count', 0)} páginas"
        )

        return Result.success(raw_doc)

    def _extract_metadata(self, pdf) -> dict:
        """Extrae metadatos del PDF."""
        metadata = {
            "page_count": len(pdf.pages),
            "is_encrypted": False,
            "has_images": False,
        }

        try:
            if pdf.metadata:
                metadata.update({
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                    "producer": pdf.metadata.get("Producer", ""),
                    "created": pdf.metadata.get("CreationDate", ""),
                    "modified": pdf.metadata.get("ModDate", ""),
                })
        except Exception as e:
            logger.debug(f"Error extrayendo metadatos PDF: {e}")

        # Verificar si hay imágenes en alguna página (muestra)
        try:
            if pdf.pages and len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                if first_page.images:
                    metadata["has_images"] = True
        except Exception:
            pass

        return metadata

    def _extract_page_paragraphs(
        self,
        page,
        page_num: int,
        start_index: int,
        start_char_pos: int,
        base_font_size: Optional[float],
    ) -> tuple[list[RawParagraph], Optional[float]]:
        """
        Extrae párrafos de una página.

        Args:
            page: Página de pdfplumber
            page_num: Número de página (1-based)
            start_index: Índice inicial para párrafos
            start_char_pos: Posición de carácter inicial
            base_font_size: Tamaño de fuente base detectado

        Returns:
            Tupla (lista de párrafos, tamaño de fuente base actualizado)
        """
        paragraphs = []

        # Extraer texto con información de caracteres
        text = page.extract_text() or ""
        if not text.strip():
            return paragraphs, base_font_size

        # Intentar obtener información de fuente para detectar headings
        chars = page.chars or []
        font_sizes = [c.get("size", 12) for c in chars if c.get("size")]

        if font_sizes and base_font_size is None:
            # Calcular tamaño de fuente base (mediana)
            sorted_sizes = sorted(font_sizes)
            base_font_size = sorted_sizes[len(sorted_sizes) // 2]

        # Dividir en párrafos por líneas en blanco
        raw_paragraphs = self._split_into_paragraphs(text)

        current_char_pos = start_char_pos
        paragraph_index = start_index

        for para_text in raw_paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue

            # Detectar si es heading
            is_heading, heading_level = self._detect_heading(
                para_text, chars, base_font_size
            )

            para = RawParagraph(
                text=para_text,
                index=paragraph_index,
                style_name="Heading" if is_heading else "Normal",
                is_heading=is_heading,
                heading_level=heading_level,
                start_char=current_char_pos,
                end_char=current_char_pos + len(para_text),
                metadata={
                    "page_number": page_num,
                    "source_format": "pdf",
                },
            )

            paragraphs.append(para)
            current_char_pos += len(para_text) + 2  # +2 para \n\n
            paragraph_index += 1

        return paragraphs, base_font_size

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """
        Divide el texto en párrafos.

        Usa doble salto de línea como separador principal,
        pero también considera líneas cortas seguidas de línea vacía.
        """
        # Normalizar saltos de línea
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Dividir por doble salto de línea
        paragraphs = re.split(r"\n\s*\n", text)

        # Filtrar vacíos y limpiar
        return [p.strip() for p in paragraphs if p.strip()]

    def _detect_heading(
        self,
        text: str,
        chars: list,
        base_font_size: Optional[float],
    ) -> tuple[bool, Optional[int]]:
        """
        Detecta si un texto es un heading.

        Criterios:
        1. Coincide con patrones de capítulo
        2. Tamaño de fuente mayor que el base
        3. Línea corta con formato especial

        Returns:
            Tupla (is_heading, level)
        """
        text_stripped = text.strip()

        # Por patrón de texto (capítulos)
        for pattern in CHAPTER_PATTERNS:
            if pattern.match(text_stripped):
                return True, 1

        # Por tamaño de fuente (si disponible)
        if base_font_size and chars:
            # Buscar caracteres que correspondan a este texto
            text_start = text_stripped[:20]  # Primeros caracteres
            matching_chars = [
                c for c in chars
                if c.get("text", "").strip() and text_start.startswith(c.get("text", "").strip()[:5])
            ]

            if matching_chars:
                avg_size = sum(c.get("size", 12) for c in matching_chars) / len(matching_chars)
                if avg_size > base_font_size * HEADING_FONT_SIZE_RATIO:
                    # Determinar nivel por tamaño relativo
                    ratio = avg_size / base_font_size
                    if ratio > 1.5:
                        return True, 1
                    elif ratio > 1.3:
                        return True, 2
                    else:
                        return True, 3

        # Línea corta en mayúsculas (posible título)
        if len(text_stripped) < 60 and text_stripped.isupper():
            return True, 2

        return False, None

    def _detect_chapters_by_pattern(self, paragraphs: list[RawParagraph]) -> None:
        """
        Post-proceso para detectar capítulos por patrón de texto.

        Similar al de docx_parser.
        """
        chapter_number_pattern = re.compile(r"^(\d{1,3})\s*$")

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            text = para.text.strip()

            # Verificar si es un número de capítulo solo
            match = chapter_number_pattern.match(text)
            if match:
                para.is_heading = True
                para.heading_level = 1
                para.metadata["chapter_number"] = int(match.group(1))

                # Buscar el siguiente párrafo no vacío
                next_idx = i + 1
                while next_idx < len(paragraphs) and paragraphs[next_idx].is_empty:
                    next_idx += 1

                if next_idx < len(paragraphs):
                    next_para = paragraphs[next_idx]
                    next_text = next_para.text.strip()

                    # Verificar si parece un título (corto, no narrativo)
                    if len(next_text) < 60 and not self._is_narrative_start(next_text):
                        # Solo añadimos metadata, NO marcamos como heading
                        # para evitar duplicados en la detección de estructura
                        next_para.metadata["is_chapter_title"] = True
                        next_para.metadata["chapter_number"] = int(match.group(1))
                        para.metadata["chapter_title"] = next_text

            i += 1

    def _is_narrative_start(self, text: str) -> bool:
        """Verifica si el texto comienza con conectores narrativos."""
        narrative_starters = [
            'cuando', 'mientras', 'entonces', 'sin embargo', 'no obstante',
            'de pronto', 'aquella', 'aquel', 'aquellos', 'aquellas',
            'había', 'era', 'fue', 'estaba', 'tenía', 'hacía',
            'el día', 'la noche', 'esa mañana', 'aquella tarde',
        ]
        text_lower = text.lower()
        return any(text_lower.startswith(starter) for starter in narrative_starters)
