"""
Content diffing a nivel de capítulo/párrafo (BK-25, S14-01).

Compara textos de capítulos entre dos versiones del documento
para identificar rangos añadidos, eliminados y movidos.
Usa difflib.SequenceMatcher a nivel párrafo para granularidad editorial.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Párrafo = separación por doble newline o newline simple con indentación
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n|\n(?=\s{2,})")


@dataclass
class TextRange:
    """Rango de texto con posición en caracteres."""

    start_char: int
    end_char: int
    text: str = ""

    @property
    def length(self) -> int:
        return self.end_char - self.start_char


@dataclass
class ChapterDiff:
    """Resultado de comparar un capítulo entre dos versiones."""

    chapter_number: int
    status: str  # "unchanged", "modified", "added", "removed"
    similarity: float = 1.0  # 0.0 = totalmente distinto, 1.0 = idéntico

    added_ranges: list[TextRange] = field(default_factory=list)
    removed_ranges: list[TextRange] = field(default_factory=list)

    # Estadísticas
    paragraphs_added: int = 0
    paragraphs_removed: int = 0
    paragraphs_modified: int = 0
    paragraphs_unchanged: int = 0


@dataclass
class DocumentDiff:
    """Resultado completo de comparar dos versiones del documento."""

    chapter_diffs: list[ChapterDiff] = field(default_factory=list)
    chapters_added: list[int] = field(default_factory=list)
    chapters_removed: list[int] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.chapters_added
            or self.chapters_removed
            or any(d.status != "unchanged" for d in self.chapter_diffs)
        )


def _split_paragraphs(text: str) -> list[str]:
    """Divide texto en párrafos, eliminando vacíos."""
    paragraphs = _PARAGRAPH_SPLIT.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _compute_paragraph_positions(text: str, paragraphs: list[str]) -> list[tuple[int, int]]:
    """Calcula posiciones (start_char, end_char) de cada párrafo en el texto original."""
    positions = []
    search_start = 0
    for para in paragraphs:
        idx = text.find(para, search_start)
        if idx == -1:
            # Fallback: buscar desde el inicio (puede pasar con whitespace normalizado)
            idx = text.find(para)
        if idx >= 0:
            positions.append((idx, idx + len(para)))
            search_start = idx + len(para)
        else:
            # No encontrado — usar posición estimada
            positions.append((search_start, search_start + len(para)))
            search_start += len(para)
    return positions


def _content_hash(text: str) -> str:
    """Hash rápido para comparación de igualdad."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def diff_chapter_texts(
    old_text: str,
    new_text: str,
    chapter_number: int = 0,
) -> ChapterDiff:
    """
    Compara dos versiones del texto de un capítulo a nivel párrafo.

    Retorna ChapterDiff con rangos añadidos/eliminados y estadísticas.
    """
    # Fast path: textos idénticos
    if _content_hash(old_text) == _content_hash(new_text):
        old_paras = _split_paragraphs(old_text)
        return ChapterDiff(
            chapter_number=chapter_number,
            status="unchanged",
            similarity=1.0,
            paragraphs_unchanged=len(old_paras),
        )

    old_paras = _split_paragraphs(old_text)
    new_paras = _split_paragraphs(new_text)

    old_positions = _compute_paragraph_positions(old_text, old_paras)
    new_positions = _compute_paragraph_positions(new_text, new_paras)

    matcher = SequenceMatcher(None, old_paras, new_paras, autojunk=False)
    similarity = matcher.ratio()

    added_ranges: list[TextRange] = []
    removed_ranges: list[TextRange] = []
    paragraphs_added = 0
    paragraphs_removed = 0
    paragraphs_modified = 0
    paragraphs_unchanged = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            paragraphs_unchanged += i2 - i1

        elif tag == "delete":
            # Párrafos eliminados del viejo
            paragraphs_removed += i2 - i1
            for k in range(i1, i2):
                if k < len(old_positions):
                    start, end = old_positions[k]
                    removed_ranges.append(TextRange(
                        start_char=start, end_char=end, text=old_paras[k][:200],
                    ))

        elif tag == "insert":
            # Párrafos añadidos en el nuevo
            paragraphs_added += j2 - j1
            for k in range(j1, j2):
                if k < len(new_positions):
                    start, end = new_positions[k]
                    added_ranges.append(TextRange(
                        start_char=start, end_char=end, text=new_paras[k][:200],
                    ))

        elif tag == "replace":
            # Párrafos modificados (old[i1:i2] → new[j1:j2])
            paragraphs_modified += max(i2 - i1, j2 - j1)
            for k in range(i1, i2):
                if k < len(old_positions):
                    start, end = old_positions[k]
                    removed_ranges.append(TextRange(
                        start_char=start, end_char=end, text=old_paras[k][:200],
                    ))
            for k in range(j1, j2):
                if k < len(new_positions):
                    start, end = new_positions[k]
                    added_ranges.append(TextRange(
                        start_char=start, end_char=end, text=new_paras[k][:200],
                    ))

    return ChapterDiff(
        chapter_number=chapter_number,
        status="modified",
        similarity=similarity,
        added_ranges=added_ranges,
        removed_ranges=removed_ranges,
        paragraphs_added=paragraphs_added,
        paragraphs_removed=paragraphs_removed,
        paragraphs_modified=paragraphs_modified,
        paragraphs_unchanged=paragraphs_unchanged,
    )


def compute_chapter_diffs(
    old_chapters: dict[int, str],
    new_chapters: dict[int, str],
) -> DocumentDiff:
    """
    Compara capítulos entre dos versiones del documento.

    Args:
        old_chapters: {chapter_number: content_text} del snapshot anterior.
        new_chapters: {chapter_number: content_text} de la versión actual.

    Returns:
        DocumentDiff con diffs por capítulo y listas de capítulos añadidos/eliminados.
    """
    old_nums = set(old_chapters.keys())
    new_nums = set(new_chapters.keys())

    chapters_added = sorted(new_nums - old_nums)
    chapters_removed = sorted(old_nums - new_nums)
    common = sorted(old_nums & new_nums)

    chapter_diffs: list[ChapterDiff] = []

    # Capítulos añadidos
    for ch_num in chapters_added:
        text = new_chapters[ch_num]
        paras = _split_paragraphs(text)
        chapter_diffs.append(ChapterDiff(
            chapter_number=ch_num,
            status="added",
            similarity=0.0,
            paragraphs_added=len(paras),
        ))

    # Capítulos eliminados
    for ch_num in chapters_removed:
        text = old_chapters[ch_num]
        paras = _split_paragraphs(text)
        chapter_diffs.append(ChapterDiff(
            chapter_number=ch_num,
            status="removed",
            similarity=0.0,
            paragraphs_removed=len(paras),
        ))

    # Capítulos comunes: diff paragraph-level
    for ch_num in common:
        diff = diff_chapter_texts(old_chapters[ch_num], new_chapters[ch_num], ch_num)
        chapter_diffs.append(diff)

    # Ordenar por chapter_number
    chapter_diffs.sort(key=lambda d: d.chapter_number)

    return DocumentDiff(
        chapter_diffs=chapter_diffs,
        chapters_added=chapters_added,
        chapters_removed=chapters_removed,
    )


def is_position_in_removed_range(
    chapter: int,
    start_char: int,
    end_char: int,
    doc_diff: DocumentDiff,
) -> bool:
    """
    Verifica si una posición de alerta cae dentro de un rango eliminado.

    Usado por ComparisonService pass 3 para determinar si una alerta
    desapareció porque el texto fue editado en esa zona.
    """
    for ch_diff in doc_diff.chapter_diffs:
        if ch_diff.chapter_number != chapter:
            continue
        for removed in ch_diff.removed_ranges:
            # Overlap: alert range intersecta con removed range
            if start_char < removed.end_char and end_char > removed.start_char:
                return True
    return False


def is_position_in_modified_area(
    chapter: int,
    start_char: int,
    end_char: int,
    doc_diff: DocumentDiff,
    margin: int = 200,
) -> bool:
    """
    Verifica si una posición está cerca de un área modificada (con margen).

    Más permisivo que is_position_in_removed_range: detecta alertas
    que estaban cerca de cambios aunque no exactamente en el rango eliminado.
    """
    for ch_diff in doc_diff.chapter_diffs:
        if ch_diff.chapter_number != chapter:
            continue
        for removed in ch_diff.removed_ranges:
            if (start_char - margin) < removed.end_char and (end_char + margin) > removed.start_char:
                return True
        for added in ch_diff.added_ranges:
            if (start_char - margin) < added.end_char and (end_char + margin) > added.start_char:
                return True
    return False
