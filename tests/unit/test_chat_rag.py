"""
Tests para el módulo de RAG exhaustivo del chat.

Verifica:
- Extracción de términos de búsqueda
- Búsqueda exhaustiva en capítulos
- Ranking y selección de excerpts
- Construcción de contexto numerado
- Parsing de referencias [REF:N]
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._chat_rag import (  # noqa: E402
    build_numbered_context,
    build_reference_index,
    build_selection_context,
    exhaustive_search,
    extract_search_terms,
    rank_and_select,
)

# ============================================================================
# Helpers
# ============================================================================

def _make_chapters():
    """Capítulos de ejemplo para tests."""
    return [
        {
            "number": 1,
            "title": "La llegada",
            "content": "María llegó al pueblo con sus ojos azules brillando bajo el sol. "
                       "Su hermano Pedro la esperaba en la estación.",
            "start_char": 0,
        },
        {
            "number": 2,
            "title": "El encuentro",
            "content": "Pedro abrazó a María con fuerza. Ella sonrió mostrando sus dientes "
                       "blancos. El pueblo no había cambiado nada.",
            "start_char": 300,
        },
        {
            "number": 3,
            "title": "El reencuentro",
            "content": "María se miró al espejo y vio sus ojos verdes reflejados. "
                       "No entendía por qué se sentía tan diferente.",
            "start_char": 600,
        },
    ]


class _FakeEntity:
    def __init__(self, canonical_name, aliases=None):
        self.canonical_name = canonical_name
        self.aliases = aliases or []


# ============================================================================
# extract_search_terms
# ============================================================================

class TestExtractSearchTerms:
    def test_basic_keywords(self):
        terms = extract_search_terms("¿De qué color tiene los ojos María?")
        # "color" is in stopwords, "ojos" and "maría" should be extracted
        assert "maría" in [t.lower() for t in terms]

    def test_quoted_phrases(self):
        terms = extract_search_terms('Busca "ojos azules" en el texto')
        assert "ojos azules" in terms

    def test_entity_expansion(self):
        entities = [_FakeEntity("María", aliases=["Marita", "la chica"])]
        terms = extract_search_terms("¿Qué dice María?", entities)
        terms_lower = [t.lower() for t in terms]
        assert "marita" in terms_lower
        assert "la chica" in terms_lower

    def test_no_duplicates(self):
        terms = extract_search_terms("María María María")
        assert len([t for t in terms if t.lower() == "maría"]) == 1

    def test_stopwords_fallback_longest(self):
        """Cuando todo son stopwords, usa la más larga como fallback."""
        terms = extract_search_terms("pero como para este tiene")
        assert len(terms) == 1
        assert terms[0] == "tiene"

    def test_short_words_filtered(self):
        terms = extract_search_terms("el de la un")
        assert len(terms) == 0


# ============================================================================
# exhaustive_search
# ============================================================================

class TestExhaustiveSearch:
    def test_finds_all_occurrences(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María"], chapters)
        # María appears in chapters 1, 2, and 3
        chapter_nums = {m["chapter_number"] for m in matches}
        assert chapter_nums == {1, 2, 3}

    def test_finds_term_in_context(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["ojos"], chapters, context_window=50)
        assert len(matches) >= 2  # "ojos azules" in ch1 and "ojos verdes" in ch3
        for m in matches:
            assert "ojos" in m["excerpt"].lower()

    def test_records_positions(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["Pedro"], chapters)
        assert all("global_start" in m for m in matches)
        assert all("position_in_chapter" in m for m in matches)

    def test_no_matches_returns_empty(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["Inexistente"], chapters)
        assert matches == []

    def test_multiple_terms(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María", "Pedro"], chapters)
        terms_found = {m["term"] for m in matches}
        assert "María" in terms_found
        assert "Pedro" in terms_found


# ============================================================================
# rank_and_select
# ============================================================================

class TestRankAndSelect:
    def test_respects_max_excerpts(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María", "Pedro", "ojos", "pueblo"], chapters)
        selected = rank_and_select(matches, max_chars=10000, max_excerpts=3)
        assert len(selected) <= 3

    def test_respects_max_chars(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María"], chapters)
        selected = rank_and_select(matches, max_chars=100, max_excerpts=10)
        total_chars = sum(len(s["excerpt"]) for s in selected)
        assert total_chars <= 200  # Some slack for merging

    def test_diversifies_chapters(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María"], chapters)
        selected = rank_and_select(matches, max_chars=5000, max_excerpts=5)
        chapter_nums = {s["chapter_number"] for s in selected}
        # Should include excerpts from multiple chapters
        assert len(chapter_nums) >= 2

    def test_empty_input(self):
        assert rank_and_select([]) == []

    def test_ordered_by_position(self):
        chapters = _make_chapters()
        matches = exhaustive_search(["María"], chapters)
        selected = rank_and_select(matches, max_chars=5000)
        positions = [s["global_start"] for s in selected]
        assert positions == sorted(positions)


# ============================================================================
# build_numbered_context
# ============================================================================

class TestBuildNumberedContext:
    def test_returns_numbered_text(self):
        excerpts = [
            {"chapter_number": 1, "chapter_title": "Cap 1", "excerpt": "texto uno",
             "global_start": 0, "global_end": 9},
            {"chapter_number": 2, "chapter_title": "Cap 2", "excerpt": "texto dos",
             "global_start": 100, "global_end": 109},
        ]
        text, ref_map = build_numbered_context(excerpts)
        assert "[REF:1]" in text
        assert "[REF:2]" in text
        assert "Cap 1" in text
        assert "texto uno" in text
        assert 1 in ref_map
        assert 2 in ref_map

    def test_ref_map_has_positions(self):
        excerpts = [
            {"chapter_number": 3, "chapter_title": "Cap 3", "excerpt": "test",
             "global_start": 500, "global_end": 504},
        ]
        _, ref_map = build_numbered_context(excerpts)
        assert ref_map[1]["global_start"] == 500
        assert ref_map[1]["chapter_number"] == 3

    def test_empty_excerpts(self):
        text, ref_map = build_numbered_context([])
        assert text == ""
        assert ref_map == {}


# ============================================================================
# build_reference_index
# ============================================================================

class TestBuildReferenceIndex:
    def test_parses_refs(self):
        ref_map = {
            1: {"chapter_number": 1, "chapter_title": "Cap 1",
                "global_start": 10, "global_end": 40, "excerpt": "ojos azules"},
            2: {"chapter_number": 3, "chapter_title": "Cap 3",
                "global_start": 600, "global_end": 630, "excerpt": "ojos verdes"},
        }
        response = 'María tiene "ojos azules" [REF:1] pero luego dice "ojos verdes" [REF:2].'
        refs = build_reference_index(response, ref_map)
        assert len(refs) == 2
        assert refs[0]["id"] == 1
        assert refs[0]["chapter"] == 1
        assert refs[0]["startChar"] == 10
        assert refs[1]["id"] == 2
        assert refs[1]["chapter"] == 3

    def test_ignores_unknown_refs(self):
        ref_map = {1: {"chapter_number": 1, "chapter_title": "Cap 1",
                        "global_start": 0, "global_end": 10, "excerpt": "test"}}
        response = "Texto [REF:1] y [REF:99] inexistente."
        refs = build_reference_index(response, ref_map)
        assert len(refs) == 1
        assert refs[0]["id"] == 1

    def test_no_refs_returns_empty(self):
        ref_map = {1: {"chapter_number": 1, "chapter_title": "Cap 1",
                        "global_start": 0, "global_end": 10, "excerpt": "test"}}
        response = "Respuesta sin referencias."
        refs = build_reference_index(response, ref_map)
        assert refs == []

    def test_deduplicates_refs(self):
        ref_map = {1: {"chapter_number": 1, "chapter_title": "Cap 1",
                        "global_start": 0, "global_end": 10, "excerpt": "test"}}
        response = "Primera [REF:1] y otra vez [REF:1]."
        refs = build_reference_index(response, ref_map)
        assert len(refs) == 1


# ============================================================================
# build_selection_context
# ============================================================================

class TestBuildSelectionContext:
    def test_includes_text(self):
        result = build_selection_context("texto seleccionado", "Cap 1")
        assert "texto seleccionado" in result
        assert "Cap 1" in result

    def test_truncates_long_text(self):
        long_text = "a" * 600
        result = build_selection_context(long_text)
        # Should truncate to 500 chars
        assert len(long_text) > 500
        assert "a" * 500 in result

    def test_without_chapter(self):
        result = build_selection_context("texto")
        assert "Capítulo" not in result
        assert "texto" in result
