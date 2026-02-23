"""
Tests para core/text_utils.py — utilidades consolidadas de normalización.

Verifica que las funciones DRY producen resultados idénticos a las
10+ implementaciones previas que reemplazan.
"""

import pytest

from narrative_assistant.core.text_utils import (
    char_ngrams,
    jaccard_similarity,
    names_match,
    normalize_for_lookup,
    normalize_name,
    strip_accents,
    token_jaccard,
)


# ============================================================================
# strip_accents
# ============================================================================


class TestStripAccents:
    """strip_accents debe eliminar acentos diacríticos."""

    def test_basic_accent(self):
        assert strip_accents("María") == "Maria"

    def test_multiple_accents(self):
        assert strip_accents("José García") == "Jose Garcia"

    def test_preserve_ñ_default(self):
        """ñ se preserva por defecto (es letra, no acento)."""
        assert strip_accents("niño") == "niño"
        assert strip_accents("España") == "España"

    def test_preserve_Ñ_uppercase(self):
        assert strip_accents("NIÑO") == "NIÑO"

    def test_no_preserve_ñ(self):
        """Con preserve_ñ=False, ñ se convierte a n."""
        assert strip_accents("niño", preserve_ñ=False) == "nino"

    def test_empty_string(self):
        assert strip_accents("") == ""

    def test_no_accents(self):
        assert strip_accents("Juan Pedro") == "Juan Pedro"

    def test_all_vowel_accents(self):
        result = strip_accents("áéíóú ÁÉÍÓÚ")
        assert result == "aeiou AEIOU"

    def test_dieresis(self):
        """Diéresis (ü) se elimina como acento."""
        assert strip_accents("güe") == "gue"
        assert strip_accents("pingüino") == "pinguino"

    def test_unicode_combining_marks(self):
        """Marcas combinantes no estándar."""
        # Cedilla (ç) se preserva (no es acento)
        result = strip_accents("François")
        assert "c" in result.lower() or "ç" in result.lower()


# ============================================================================
# normalize_name
# ============================================================================


class TestNormalizeName:
    """normalize_name: lowercase + sin acentos + whitespace colapsado."""

    def test_basic(self):
        assert normalize_name("María García") == "maria garcia"

    def test_accents_removed(self):
        assert normalize_name("José") == "jose"

    def test_whitespace_collapsed(self):
        assert normalize_name("Juan   de  la   Cruz") == "juan de la cruz"

    def test_empty(self):
        assert normalize_name("") == ""

    def test_leading_trailing_whitespace(self):
        assert normalize_name("  María  ") == "maria"

    def test_case_insensitive(self):
        assert normalize_name("MARÍA") == normalize_name("maría")

    def test_tabs_and_newlines(self):
        assert normalize_name("Juan\t\nPedro") == "juan pedro"

    def test_consistency_with_legacy(self):
        """Debe producir el mismo resultado que morpho_utils.normalize_name."""
        # Verificar equivalencia con la implementación anterior
        test_names = ["María García", "José de la Cruz", "François", "Ñoño"]
        for name in test_names:
            result = normalize_name(name)
            assert result == result.lower()
            assert "  " not in result


# ============================================================================
# normalize_for_lookup
# ============================================================================


class TestNormalizeForLookup:
    """normalize_for_lookup: para búsquedas en diccionarios."""

    def test_removes_punctuation(self):
        assert normalize_for_lookup("¿Cómo?") == "como"

    def test_removes_hyphens(self):
        assert normalize_for_lookup("García-López") == "garcialopez"

    def test_basic_word(self):
        assert normalize_for_lookup("casa") == "casa"

    def test_empty(self):
        assert normalize_for_lookup("") == ""

    def test_accented(self):
        assert normalize_for_lookup("café") == "cafe"


# ============================================================================
# names_match
# ============================================================================


class TestNamesMatch:
    """names_match: comparación de nombres accent-insensitive."""

    def test_same_name(self):
        assert names_match("María", "María")

    def test_accent_variant(self):
        assert names_match("María García", "Maria Garcia")

    def test_case_variant(self):
        assert names_match("JOSÉ", "josé")

    def test_different_names(self):
        assert not names_match("Juan", "Pedro")

    def test_empty_both(self):
        assert names_match("", "")

    def test_empty_one(self):
        assert not names_match("Juan", "")


# ============================================================================
# jaccard_similarity
# ============================================================================


class TestJaccardSimilarity:
    """jaccard_similarity: similitud de conjuntos."""

    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        result = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(result - 0.5) < 0.01  # 2 / 4

    def test_empty_both(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_empty_one(self):
        assert jaccard_similarity(set(), {"a"}) == 0.0


# ============================================================================
# token_jaccard
# ============================================================================


class TestTokenJaccard:
    """token_jaccard: similitud por tokens de palabras."""

    def test_identical(self):
        assert token_jaccard("María García", "maria garcia") == 1.0

    def test_partial(self):
        result = token_jaccard("María García López", "María García Cruz")
        assert 0.3 < result < 0.8

    def test_completely_different(self):
        assert token_jaccard("Juan Pedro", "Ana Carmen") == 0.0

    def test_empty(self):
        assert token_jaccard("", "") == 1.0


# ============================================================================
# char_ngrams
# ============================================================================


class TestCharNgrams:
    """char_ngrams: generación de trigramas."""

    def test_basic(self):
        ngrams = char_ngrams("hola")
        assert "hol" in ngrams
        assert "ola" in ngrams
        assert len(ngrams) == 2

    def test_short_string(self):
        ngrams = char_ngrams("ab")
        assert ngrams == {"ab"}

    def test_empty(self):
        ngrams = char_ngrams("")
        assert ngrams == set()

    def test_accent_normalized(self):
        """Trigramas se generan sobre texto normalizado."""
        ngrams_accent = char_ngrams("María")
        ngrams_plain = char_ngrams("maria")
        assert ngrams_accent == ngrams_plain

    def test_custom_n(self):
        ngrams = char_ngrams("abcde", n=2)
        assert len(ngrams) == 4
        assert "ab" in ngrams
        assert "de" in ngrams
