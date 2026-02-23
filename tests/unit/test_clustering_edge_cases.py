"""
Tests de edge cases para clustering de entidades.

Verifica:
- Word-level containment (fix P3a: "a" in "maria garcia" ≠ 0.77)
- Threshold sensitivity
- Nombres extremos (1 char, muy largos, Unicode)
- N-gram similarity edge cases
"""

import pytest

from narrative_assistant.entities.clustering import (
    _fast_name_similarity,
    _ngram_similarity,
    _name_fingerprint,
)


# ============================================================================
# Word-level containment (P3a fix verification)
# ============================================================================


class TestWordLevelContainment:
    """Verifica que la similitud usa palabras completas, no subcadenas."""

    def test_single_char_not_high_similarity(self):
        """'a' vs 'maria garcia' NO debe dar similitud alta."""
        sim = _fast_name_similarity("a", "maria garcia")
        assert sim < 0.5, f"'a' vs 'maria garcia' = {sim}, esperado < 0.5"

    def test_word_containment_high_similarity(self):
        """'garcia' in 'maria garcia' → palabra completa → alta similitud."""
        sim = _fast_name_similarity("garcia", "maria garcia")
        assert sim >= 0.75, f"'garcia' vs 'maria garcia' = {sim}, esperado >= 0.75"

    def test_full_name_containment(self):
        """'María Sánchez' vs 'María Sánchez García' → contención completa."""
        sim = _fast_name_similarity("María Sánchez", "María Sánchez García")
        assert sim >= 0.75

    def test_two_char_substring_rejected(self):
        """'an' vs 'Juan Antonio' → subcadena, no palabra."""
        sim = _fast_name_similarity("an", "Juan Antonio")
        # Should not get word-level containment bonus
        assert sim < 0.5

    def test_short_name_minimum_length(self):
        """Nombres < 3 chars no reciben bonus de contención."""
        sim = _fast_name_similarity("Jo", "José María")
        assert sim < 0.75  # No word containment bonus

    def test_word_match_not_substring(self):
        """'Mar' no es palabra de 'María García' (subcadena, no palabra)."""
        sim = _fast_name_similarity("Mar", "María García")
        # Mar no es una palabra de "maria garcia" normalizado
        assert sim < 0.75


# ============================================================================
# Exact matches
# ============================================================================


class TestExactMatches:
    """Nombres idénticos → 1.0."""

    def test_identical_names(self):
        assert _fast_name_similarity("Juan", "Juan") == 1.0

    def test_identical_with_accents(self):
        assert _fast_name_similarity("María", "María") == 1.0

    def test_case_insensitive_exact(self):
        """normalize_for_comparison debería normalizar case."""
        sim = _fast_name_similarity("JUAN", "juan")
        assert sim == 1.0

    def test_accent_normalization_exact(self):
        """'María' vs 'Maria' → normalizados iguales."""
        sim = _fast_name_similarity("María", "Maria")
        assert sim == 1.0


# ============================================================================
# Edge cases extremos
# ============================================================================


class TestEdgeCases:
    """Casos extremos que podrían fallar."""

    def test_empty_string(self):
        assert _fast_name_similarity("", "Juan") == 0.0

    def test_both_empty(self):
        assert _fast_name_similarity("", "") == 0.0

    def test_very_long_name(self):
        """Nombres muy largos no deben crashear."""
        long_name = "Juan Carlos María Fernando de la Cruz Hernández López"
        sim = _fast_name_similarity(long_name, "Juan Carlos")
        assert 0.0 <= sim <= 1.0

    def test_special_characters(self):
        """Nombres con caracteres especiales."""
        sim = _fast_name_similarity("O'Brien", "O'Brien")
        assert sim >= 0.8

    def test_hyphenated_names(self):
        """Nombres con guión."""
        sim = _fast_name_similarity("María-José", "María José")
        assert 0.0 <= sim <= 1.0  # Shouldn't crash


# ============================================================================
# N-gram similarity
# ============================================================================


class TestNgramSimilarity:
    """Verifica similaridad por n-gramas."""

    def test_identical_names(self):
        sim = _ngram_similarity("Juan", "Juan")
        assert sim == 1.0

    def test_completely_different(self):
        sim = _ngram_similarity("abc", "xyz")
        assert sim == 0.0

    def test_similar_names(self):
        """Nombres similares deben tener alta similitud de n-gramas."""
        sim = _ngram_similarity("García", "Garcia")
        assert sim >= 0.5

    def test_empty_string(self):
        sim = _ngram_similarity("", "Juan")
        # Depends on implementation, but shouldn't crash
        assert 0.0 <= sim <= 1.0

    def test_single_char(self):
        """Nombres de 1 char → n-grama degenerado."""
        sim = _ngram_similarity("a", "a")
        assert sim == 1.0


# ============================================================================
# Name fingerprint
# ============================================================================


class TestNameFingerprint:
    """Verifica generación de fingerprints de nombre."""

    def test_order_independent(self):
        """Fingerprint es independiente del orden."""
        fp1 = _name_fingerprint("María García")
        fp2 = _name_fingerprint("García María")
        assert fp1 == fp2

    def test_case_independent(self):
        fp1 = _name_fingerprint("JUAN CARLOS")
        fp2 = _name_fingerprint("juan carlos")
        assert fp1 == fp2

    def test_empty_string(self):
        fp = _name_fingerprint("")
        assert fp == ""

    def test_accent_normalization(self):
        fp1 = _name_fingerprint("García")
        fp2 = _name_fingerprint("Garcia")
        assert fp1 == fp2
