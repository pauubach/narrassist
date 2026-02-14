"""
Parser para archivos de texto plano (TXT) y Markdown (MD).

Incluye:
- Detección automática de encoding
- Detección de headings en Markdown
- Normalización de saltos de línea
"""

import logging
import re
from pathlib import Path

from ..core.errors import CorruptedDocumentError, EmptyDocumentError
from ..core.result import Result
from .base import DocumentFormat, DocumentParser, RawDocument, RawParagraph

logger = logging.getLogger(__name__)

# Patrones para headings en Markdown
MD_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

# Patrones para detectar capítulos en texto plano
CHAPTER_PATTERNS = [
    re.compile(r"^cap[íi]tulo\s+\d+", re.IGNORECASE),
    re.compile(r"^chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^parte\s+\d+", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]+\.\s*$"),  # Solo numeración romana
    # Prólogo y epílogo
    re.compile(r"^pr[óo]logo\s*$", re.IGNORECASE),
    re.compile(r"^prologue\s*$", re.IGNORECASE),
    re.compile(r"^ep[íi]logo\s*$", re.IGNORECASE),
    re.compile(r"^epilogue\s*$", re.IGNORECASE),
]

# Palabras que NO deben tratarse como headings aunque estén en mayúsculas
NOT_HEADING_WORDS = {
    "fin",
    "the end",
    "end",
    "finis",
    "continuará",
    "continuara",
    "to be continued",
    "nota",
    "notas",
    "notes",
    "note",
    "agradecimientos",
    "acknowledgments",
    "acknowledgements",
    "dedicatoria",
    "dedication",
    "índice",
    "indice",
    "index",
    "contents",
    "bibliografía",
    "bibliografia",
    "bibliography",
    "references",
}


class TxtParser(DocumentParser):
    """
    Parser para archivos de texto plano y Markdown.

    Características:
    - Detección automática de encoding (UTF-8, Latin-1, etc.)
    - Soporte para headings Markdown (# ## ###)
    - Detección de patrones de capítulo
    - Normalización de saltos de línea
    """

    format = DocumentFormat.TXT

    def __init__(self, is_markdown: bool = False):
        """
        Args:
            is_markdown: True para parsear como Markdown
        """
        self.is_markdown = is_markdown

    def parse(self, path: Path) -> Result[RawDocument]:
        """
        Parsea un archivo de texto.

        Args:
            path: Ruta al archivo

        Returns:
            Result con RawDocument o error
        """
        # Validar archivo antes de abrir
        validation_result = self.validate_file(path)
        if validation_result.is_failure:
            return validation_result  # type: ignore[return-value]

        path = validation_result.value  # type: ignore[assignment]

        # Detectar si es Markdown por extensión
        if path.suffix.lower() in (".md", ".markdown"):
            self.is_markdown = True
            self.format = DocumentFormat.MD

        # Detectar encoding y leer
        text, encoding = self._read_with_encoding_detection(path)

        if text is None:
            return Result.failure(
                CorruptedDocumentError(
                    file_path=str(path),
                    original_error="No se pudo detectar encoding válido",
                )
            )

        # Verificar que hay contenido
        if not text.strip():
            return Result.failure(EmptyDocumentError(file_path=str(path)))

        # Normalizar saltos de línea
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Parsear párrafos
        paragraphs = self._parse_paragraphs(text)

        # Crear documento
        raw_doc = RawDocument(
            paragraphs=paragraphs,
            metadata={
                "encoding": encoding,
                "is_markdown": self.is_markdown,
            },
            source_path=path,
            source_format=self.format,
        )

        logger.info(
            f"TXT parseado ({encoding}): {raw_doc.paragraph_count} párrafos, "
            f"{raw_doc.word_count} palabras"
        )

        return Result.success(raw_doc)

    def _read_with_encoding_detection(self, path: Path) -> tuple[str | None, str]:
        """
        Lee archivo con detección automática de encoding.

        Intenta en orden:
        1. Detección con chardet
        2. UTF-8
        3. Latin-1 (nunca falla)

        Returns:
            Tupla (contenido, encoding_usado)
        """
        # Intentar con chardet primero
        try:
            import chardet

            with open(path, "rb") as f:
                raw = f.read()

            detected = chardet.detect(raw)
            if detected["encoding"] and detected["confidence"] > 0.7:
                try:
                    return raw.decode(detected["encoding"]), detected["encoding"]
                except (UnicodeDecodeError, LookupError):
                    pass
        except ImportError:
            logger.debug("chardet no disponible, usando fallbacks")

        # Fallback: UTF-8
        try:
            with open(path, encoding="utf-8") as f:
                return f.read(), "utf-8"
        except UnicodeDecodeError:
            pass

        # Fallback final: Latin-1 (nunca falla)
        try:
            with open(path, encoding="latin-1") as f:
                return f.read(), "latin-1"
        except Exception as e:
            logger.error(f"Error leyendo {path}: {e}")
            return None, ""

    def _parse_paragraphs(self, text: str) -> list[RawParagraph]:
        """
        Parsea el texto en párrafos.

        Separa por líneas en blanco dobles.
        """
        paragraphs = []
        current_pos = 0

        # Dividir por párrafos (líneas en blanco)
        raw_paragraphs = re.split(r"\n\s*\n", text)

        for idx, para_text in enumerate(raw_paragraphs):
            para_text_stripped = para_text.strip()

            if not para_text_stripped:
                current_pos += len(para_text) + 2
                continue

            # Detectar heading
            is_heading, heading_level = self._detect_heading(para_text_stripped)

            raw_para = RawParagraph(
                text=para_text_stripped,
                index=idx,
                style_name="Heading" if is_heading else "Normal",
                is_heading=is_heading,
                heading_level=heading_level,
                start_char=current_pos,
                end_char=current_pos + len(para_text_stripped),
            )

            paragraphs.append(raw_para)
            current_pos += len(para_text) + 2  # +2 for \n\n separator

        return paragraphs

    def _detect_heading(self, text: str) -> tuple[bool, int | None]:
        """
        Detecta si un párrafo es un heading.

        En Markdown: # ## ### etc.
        En texto plano: patrones de capítulo
        """
        # Markdown headings - detectar SIEMPRE, no solo si is_markdown
        # Esto permite detectar archivos .txt que usan sintaxis Markdown
        match = MD_HEADING_PATTERN.match(text)
        if match:
            level = len(match.group(1))
            # Auto-detectar que es Markdown si encontramos headings con #
            self.is_markdown = True
            return True, level

        # Patrones de capítulo (texto plano)
        for pattern in CHAPTER_PATTERNS:
            if pattern.match(text):
                return True, 1

        # Heurística: línea corta en mayúsculas podría ser título
        # Pero excluir palabras comunes que no son headings (FIN, NOTAS, etc.)
        if (
            len(text) < 80
            and text.isupper()
            and not text.endswith(".")
            and len(text.split()) <= 10
            and text.lower() not in NOT_HEADING_WORDS
        ):
            return True, 1

        return False, None

    def parse_text(self, text: str) -> Result[RawDocument]:
        """Parsea texto directamente (para testing)."""
        # Normalizar
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        paragraphs = self._parse_paragraphs(text)

        doc = RawDocument(
            paragraphs=paragraphs,
            source_format=self.format,
        )

        return Result.success(doc)
