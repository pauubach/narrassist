"""
Parser de revisiones (track changes) en documentos DOCX (S14-14, BK-25).

Extrae marcas de revisión (w:ins, w:del) del XML interno de un .docx
para correlacionar cambios editoriales con alertas resueltas.

Solo ~60% de flujos editoriales usan track changes, por lo que este
módulo es complementario al content diffing de S14-01.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

logger = logging.getLogger(__name__)

# Namespaces del formato Office Open XML
NAMESPACES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


@dataclass
class Revision:
    """Una marca de revisión en el documento."""

    revision_type: str  # "insert", "delete", "format_change"
    text: str
    author: str = ""
    date: str = ""
    paragraph_index: int = 0
    char_offset: int = 0  # Posición estimada en caracteres dentro del párrafo


@dataclass
class DocxRevisions:
    """Resultado del parsing de revisiones de un .docx."""

    revisions: list[Revision] = field(default_factory=list)
    has_revisions: bool = False
    total_insertions: int = 0
    total_deletions: int = 0
    authors: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return self.total_insertions + self.total_deletions


def _get_text_from_element(element: ET.Element) -> str:
    """Extrae todo el texto de un elemento XML y sus hijos."""
    texts = []
    for t_elem in element.iter(f"{{{NAMESPACES['w']}}}t"):
        if t_elem.text:
            texts.append(t_elem.text)
    return "".join(texts)


def _get_attr(element: ET.Element, attr: str) -> str:
    """Obtiene atributo con namespace w:."""
    return element.get(f"{{{NAMESPACES['w']}}}{attr}", "")


def parse_docx_revisions(path: Path) -> DocxRevisions:
    """
    Parsea las revisiones (track changes) de un archivo .docx.

    Lee word/document.xml y extrae elementos w:ins (inserciones) y
    w:del (eliminaciones) con autor, fecha y texto.

    Args:
        path: Ruta al archivo .docx

    Returns:
        DocxRevisions con lista de revisiones encontradas.
    """
    result = DocxRevisions()

    if not path.exists():
        logger.warning(f"File not found: {path}")
        return result

    try:
        with ZipFile(str(path), "r") as zf:
            if "word/document.xml" not in zf.namelist():
                logger.warning(f"No word/document.xml in {path}")
                return result

            xml_content = zf.read("word/document.xml")

    except (BadZipFile, Exception) as e:
        logger.warning(f"Error reading .docx: {e}")
        return result

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning(f"Error parsing XML: {e}")
        return result

    authors_set: set[str] = set()
    paragraph_index = 0
    w_ns = NAMESPACES["w"]

    # Iterar sobre los body elements
    body = root.find(f"{{{w_ns}}}body")
    if body is None:
        return result

    for paragraph in body.iter(f"{{{w_ns}}}p"):
        char_offset = 0

        for child in paragraph:
            tag = child.tag

            # w:ins — texto insertado
            if tag == f"{{{w_ns}}}ins":
                text = _get_text_from_element(child)
                author = _get_attr(child, "author")
                date = _get_attr(child, "date")

                if text.strip():
                    result.revisions.append(Revision(
                        revision_type="insert",
                        text=text,
                        author=author,
                        date=date,
                        paragraph_index=paragraph_index,
                        char_offset=char_offset,
                    ))
                    result.total_insertions += 1
                    if author:
                        authors_set.add(author)

                char_offset += len(text)

            # w:del — texto eliminado
            elif tag == f"{{{w_ns}}}del":
                # Dentro de w:del, el texto está en w:delText
                texts = []
                for dt in child.iter(f"{{{w_ns}}}delText"):
                    if dt.text:
                        texts.append(dt.text)
                text = "".join(texts)

                author = _get_attr(child, "author")
                date = _get_attr(child, "date")

                if text.strip():
                    result.revisions.append(Revision(
                        revision_type="delete",
                        text=text,
                        author=author,
                        date=date,
                        paragraph_index=paragraph_index,
                        char_offset=char_offset,
                    ))
                    result.total_deletions += 1
                    if author:
                        authors_set.add(author)
                # Deleted text doesn't advance char_offset (it's removed)

            # w:r — run normal (para tracking de offset)
            elif tag == f"{{{w_ns}}}r":
                # Check for rPr with rStyle revision marks (format changes)
                rpr = child.find(f"{{{w_ns}}}rPr")
                if rpr is not None:
                    rpr_change = rpr.find(f"{{{w_ns}}}rPrChange")
                    if rpr_change is not None:
                        text = _get_text_from_element(child)
                        author = _get_attr(rpr_change, "author")
                        date = _get_attr(rpr_change, "date")
                        if text.strip():
                            result.revisions.append(Revision(
                                revision_type="format_change",
                                text=text,
                                author=author,
                                date=date,
                                paragraph_index=paragraph_index,
                                char_offset=char_offset,
                            ))

                text = _get_text_from_element(child)
                char_offset += len(text)

        paragraph_index += 1

    result.has_revisions = len(result.revisions) > 0
    result.authors = sorted(authors_set)

    if result.has_revisions:
        logger.info(
            f"Parsed {len(result.revisions)} revisions from {path.name}: "
            f"{result.total_insertions} ins, {result.total_deletions} del, "
            f"authors={result.authors}"
        )

    return result


def get_deletion_char_ranges(
    revisions: DocxRevisions,
    paragraph_offsets: dict[int, int] | None = None,
) -> list[tuple[int, int]]:
    """
    Convierte revisiones de tipo 'delete' a rangos de caracteres absolutos.

    Args:
        revisions: Resultado de parse_docx_revisions.
        paragraph_offsets: Mapa {paragraph_index: start_char_offset_in_document}.
            Si None, usa paragraph_index * estimated_paragraph_length.

    Returns:
        Lista de (start_char, end_char) para cada eliminación.
    """
    ranges = []
    for rev in revisions.revisions:
        if rev.revision_type != "delete":
            continue

        if paragraph_offsets and rev.paragraph_index in paragraph_offsets:
            doc_offset = paragraph_offsets[rev.paragraph_index]
        else:
            # Estimación: ~500 chars por párrafo promedio
            doc_offset = rev.paragraph_index * 500

        start = doc_offset + rev.char_offset
        end = start + len(rev.text)
        ranges.append((start, end))

    return ranges
