"""
Parser para documentos EPUB.

Utiliza ebooklib para extracción de texto y estructura de capítulos.
EPUB es un formato ZIP con contenido HTML/XHTML estructurado.
"""

import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from ..core.errors import CorruptedDocumentError, EmptyDocumentError
from ..core.result import Result
from .base import DocumentFormat, DocumentParser, RawDocument, RawParagraph

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """
    Extractor de texto desde HTML que preserva estructura de párrafos.
    """

    def __init__(self):
        super().__init__()
        self.paragraphs: list[dict] = []
        self.current_text: list[str] = []
        self.current_heading_level: Optional[int] = None
        self.in_paragraph = False
        self.in_heading = False
        self.skip_content = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()

        # Tags a ignorar
        if tag in ("script", "style", "head", "meta", "link"):
            self.skip_content = True
            return

        # Headings
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_current()
            self.in_heading = True
            self.current_heading_level = int(tag[1])

        # Párrafos y divs
        elif tag in ("p", "div"):
            self._flush_current()
            self.in_paragraph = True

        # Line breaks
        elif tag == "br":
            self.current_text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in ("script", "style", "head"):
            self.skip_content = False
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_current()
            self.in_heading = False
            self.current_heading_level = None

        elif tag in ("p", "div"):
            self._flush_current()
            self.in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self.skip_content:
            return
        # Normalizar espacios
        text = " ".join(data.split())
        if text:
            self.current_text.append(text)

    def _flush_current(self) -> None:
        """Guarda el texto acumulado como párrafo."""
        text = " ".join(self.current_text).strip()
        if text:
            self.paragraphs.append({
                "text": text,
                "is_heading": self.in_heading,
                "heading_level": self.current_heading_level,
            })
        self.current_text = []

    def get_paragraphs(self) -> list[dict]:
        """Retorna los párrafos extraídos."""
        self._flush_current()
        return self.paragraphs


class EpubParser(DocumentParser):
    """
    Parser para documentos EPUB.

    Extrae:
    - Texto de todos los documentos HTML/XHTML del ebook
    - Estructura de capítulos desde TOC y headings HTML
    - Metadatos del libro (título, autor, etc.)
    """

    format = DocumentFormat.EPUB

    def __init__(self):
        self._ebooklib_available = self._check_dependency()

    def _check_dependency(self) -> bool:
        """Verifica que ebooklib está disponible."""
        try:
            import ebooklib
            from ebooklib import epub
            return True
        except ImportError:
            logger.warning(
                "ebooklib no instalado. Instalar con: pip install ebooklib"
            )
            return False

    def parse(self, path: Path) -> Result[RawDocument]:
        """
        Parsea un documento EPUB.

        Args:
            path: Ruta al archivo EPUB

        Returns:
            Result con RawDocument o error
        """
        # Validar archivo antes de abrir
        validation_result = self.validate_file(path)
        if validation_result.is_failure:
            return validation_result

        path = validation_result.value

        if not self._ebooklib_available:
            from ..core.errors import NarrativeError, ErrorSeverity

            return Result.failure(
                NarrativeError(
                    message="ebooklib not installed",
                    severity=ErrorSeverity.FATAL,
                    user_message="Instala ebooklib: pip install ebooklib",
                )
            )

        from ebooklib import epub, ITEM_DOCUMENT

        try:
            book = epub.read_epub(str(path), options={"ignore_ncx": True})
        except Exception as e:
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error=f"No se pudo abrir el EPUB: {str(e)}",
                )
            )

        try:
            # Extraer metadatos
            metadata = self._extract_metadata(book)

            # Extraer texto de todos los documentos
            paragraphs = []
            current_char_pos = 0
            paragraph_index = 0
            chapter_num = 0

            # Obtener items de documento en orden
            items = list(book.get_items_of_type(ITEM_DOCUMENT))

            for item in items:
                try:
                    content = item.get_content()
                    if not content:
                        continue

                    # Decodificar contenido
                    try:
                        html_content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        html_content = content.decode("latin-1", errors="ignore")

                    # Extraer párrafos del HTML
                    item_paragraphs = self._extract_paragraphs_from_html(
                        html_content, paragraph_index, current_char_pos
                    )

                    # Detectar si este item es un nuevo capítulo
                    if item_paragraphs and self._is_chapter_start(item_paragraphs[0]):
                        chapter_num += 1
                        item_paragraphs[0].metadata["chapter_number"] = chapter_num

                    for para in item_paragraphs:
                        para.metadata["chapter"] = chapter_num
                        paragraphs.append(para)
                        current_char_pos = para.end_char + 2
                        paragraph_index += 1

                except Exception as e:
                    logger.warning(f"Error procesando item EPUB: {e}")
                    continue

        except Exception as e:
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

        # Post-proceso: detectar capítulos por patrón
        self._detect_chapters_by_pattern(paragraphs)

        # Crear documento
        raw_doc = RawDocument(
            paragraphs=paragraphs,
            metadata=metadata,
            source_path=path,
            source_format=DocumentFormat.EPUB,
        )

        # Advertencias
        if metadata.get("has_images"):
            raw_doc.add_warning("El documento contiene imágenes que serán ignoradas.")

        logger.info(
            f"EPUB parseado: {raw_doc.paragraph_count} párrafos, "
            f"{raw_doc.word_count} palabras, {chapter_num} capítulos detectados"
        )

        return Result.success(raw_doc)

    def _extract_metadata(self, book) -> dict:
        """Extrae metadatos del EPUB."""
        metadata = {
            "has_images": False,
        }

        try:
            # Título
            title = book.get_metadata("DC", "title")
            if title:
                metadata["title"] = title[0][0] if isinstance(title[0], tuple) else str(title[0])

            # Autor
            creator = book.get_metadata("DC", "creator")
            if creator:
                metadata["author"] = creator[0][0] if isinstance(creator[0], tuple) else str(creator[0])

            # Idioma
            language = book.get_metadata("DC", "language")
            if language:
                metadata["language"] = language[0][0] if isinstance(language[0], tuple) else str(language[0])

            # Descripción
            description = book.get_metadata("DC", "description")
            if description:
                metadata["subject"] = description[0][0] if isinstance(description[0], tuple) else str(description[0])

            # Publisher
            publisher = book.get_metadata("DC", "publisher")
            if publisher:
                metadata["publisher"] = publisher[0][0] if isinstance(publisher[0], tuple) else str(publisher[0])

            # Fecha
            date = book.get_metadata("DC", "date")
            if date:
                metadata["created"] = date[0][0] if isinstance(date[0], tuple) else str(date[0])

            # Verificar si hay imágenes
            from ebooklib import ITEM_IMAGE
            images = list(book.get_items_of_type(ITEM_IMAGE))
            metadata["has_images"] = len(images) > 0

        except Exception as e:
            logger.debug(f"Error extrayendo metadatos EPUB: {e}")

        return metadata

    def _extract_paragraphs_from_html(
        self,
        html_content: str,
        start_index: int,
        start_char_pos: int,
    ) -> list[RawParagraph]:
        """
        Extrae párrafos de contenido HTML.

        Args:
            html_content: Contenido HTML del documento
            start_index: Índice inicial para párrafos
            start_char_pos: Posición de carácter inicial

        Returns:
            Lista de párrafos extraídos
        """
        # Parsear HTML
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(html_content)
        except Exception as e:
            logger.debug(f"Error parseando HTML: {e}")
            return []

        raw_paragraphs = extractor.get_paragraphs()

        paragraphs = []
        current_char_pos = start_char_pos
        paragraph_index = start_index

        for para_data in raw_paragraphs:
            text = para_data["text"].strip()
            if not text:
                continue

            para = RawParagraph(
                text=text,
                index=paragraph_index,
                style_name="Heading" if para_data["is_heading"] else "Normal",
                is_heading=para_data["is_heading"],
                heading_level=para_data["heading_level"],
                start_char=current_char_pos,
                end_char=current_char_pos + len(text),
                metadata={
                    "source_format": "epub",
                },
            )

            paragraphs.append(para)
            current_char_pos += len(text) + 2
            paragraph_index += 1

        return paragraphs

    def _is_chapter_start(self, para: RawParagraph) -> bool:
        """
        Determina si un párrafo marca el inicio de un capítulo.
        """
        if para.is_heading and para.heading_level == 1:
            return True

        text = para.text.strip().lower()

        # Patrones de capítulo
        chapter_patterns = [
            r"^cap[íi]tulo\s+\d+",
            r"^chapter\s+\d+",
            r"^parte\s+\d+",
            r"^[ivxlcdm]+\.\s*",
        ]

        for pattern in chapter_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def _detect_chapters_by_pattern(self, paragraphs: list[RawParagraph]) -> None:
        """
        Post-proceso para detectar capítulos por patrón de texto.
        """
        chapter_number_pattern = re.compile(r"^(\d{1,3})\s*$")
        chapter_word_pattern = re.compile(
            r"^cap[íi]tulo\s+(\d+)", re.IGNORECASE
        )

        current_chapter = 0

        for i, para in enumerate(paragraphs):
            text = para.text.strip()

            # Número solo
            match = chapter_number_pattern.match(text)
            if match:
                para.is_heading = True
                para.heading_level = 1
                current_chapter = int(match.group(1))
                para.metadata["chapter_number"] = current_chapter

                # Buscar título en siguiente párrafo
                if i + 1 < len(paragraphs):
                    next_para = paragraphs[i + 1]
                    next_text = next_para.text.strip()
                    if len(next_text) < 60 and not self._is_narrative_start(next_text):
                        # Solo añadimos metadata, NO marcamos como heading
                        # para evitar duplicados en la detección de estructura
                        next_para.metadata["is_chapter_title"] = True
                        next_para.metadata["chapter_number"] = current_chapter
                        para.metadata["chapter_title"] = next_text
                continue

            # "Capítulo N"
            match = chapter_word_pattern.match(text)
            if match:
                para.is_heading = True
                para.heading_level = 1
                current_chapter = int(match.group(1))
                para.metadata["chapter_number"] = current_chapter

    def _is_narrative_start(self, text: str) -> bool:
        """Verifica si el texto comienza con conectores narrativos."""
        narrative_starters = [
            'cuando', 'mientras', 'entonces', 'sin embargo',
            'de pronto', 'aquella', 'aquel', 'había', 'era', 'fue',
        ]
        text_lower = text.lower()
        return any(text_lower.startswith(starter) for starter in narrative_starters)
