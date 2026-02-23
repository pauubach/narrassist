"""
Tests para entities/semantic_fusion.py — hipocorísticos, normalización y fusión.

Cobertura: are_hypocoristic_match, get_formal_name, get_hypocoristics,
strip_accents, normalize_for_comparison, generate_name_variants.
"""

import pytest

from narrative_assistant.entities.semantic_fusion import (
    SPANISH_HYPOCORISTICS,
    are_hypocoristic_match,
    generate_name_variants,
    get_formal_name,
    get_hypocoristics,
    normalize_for_comparison,
    strip_accents,
    strip_interior_particles,
)


# ============================================================================
# are_hypocoristic_match — directos
# ============================================================================


class TestHypocorsiticMatchDirect:
    """Matches directos: formal ↔ hipocorístico."""

    @pytest.mark.parametrize("formal,hyp", [
        ("Francisco", "Paco"),
        ("Francisco", "Curro"),
        ("Francisco", "Pancho"),
        ("Francisco", "Fran"),
        ("José", "Pepe"),
        ("María", "Mari"),
        ("Daniel", "Dani"),
        ("Manuel", "Manolo"),
        ("Dolores", "Lola"),
        ("Isabel", "Isa"),
        ("Concepción", "Concha"),
        ("Jesús", "Chucho"),
        ("Enrique", "Quique"),
        ("Guillermo", "Guille"),
        ("Ignacio", "Nacho"),
        ("Javier", "Javi"),
        ("Carmen", "Carmela"),
        ("Pilar", "Pili"),
        ("Teresa", "Tere"),
        ("Gonzalo", "Gonzo"),
    ])
    def test_direct_match(self, formal, hyp):
        assert are_hypocoristic_match(formal, hyp)
        assert are_hypocoristic_match(hyp, formal)  # Simétrico

    def test_same_name(self):
        assert are_hypocoristic_match("Juan", "Juan")
        assert are_hypocoristic_match("María", "María")

    def test_case_insensitive(self):
        assert are_hypocoristic_match("PACO", "francisco")
        assert are_hypocoristic_match("paco", "FRANCISCO")


# ============================================================================
# are_hypocoristic_match — transitivos
# ============================================================================


class TestHypocorsiticMatchTransitive:
    """Matches transitivos: hipocorístico ↔ hipocorístico del mismo formal."""

    def test_paco_curro(self):
        """Ambos son de Francisco."""
        assert are_hypocoristic_match("Paco", "Curro")

    def test_paco_pancho(self):
        assert are_hypocoristic_match("Paco", "Pancho")

    def test_lola_loles(self):
        """Ambos de Dolores."""
        assert are_hypocoristic_match("Lola", "Loles")

    def test_pepe_pepito(self):
        """Ambos de José."""
        assert are_hypocoristic_match("Pepe", "Pepito")

    def test_concha_conchita(self):
        """Ambos de Concepción."""
        assert are_hypocoristic_match("Concha", "Conchita")


# ============================================================================
# are_hypocoristic_match — negativos
# ============================================================================


class TestHypocorsiticMatchNegative:
    """Nombres que NO deben matchear."""

    def test_different_names(self):
        assert not are_hypocoristic_match("Juan", "Pedro")
        assert not are_hypocoristic_match("María", "Carmen")
        assert not are_hypocoristic_match("Paco", "Luis")

    def test_similar_sounding_not_related(self):
        assert not are_hypocoristic_match("María", "Marina")
        assert not are_hypocoristic_match("Carlos", "Carolina")

    def test_feminine_masculine_same_root(self):
        """Francisco y Francisca tienen hipocorísticos distintos."""
        # Paco es de Francisco, Paca es de Francisca
        assert not are_hypocoristic_match("Paco", "Paca")


# ============================================================================
# are_hypocoristic_match — edge cases
# ============================================================================


class TestHypocorsiticEdgeCases:
    """Casos extremos."""

    def test_empty_strings(self):
        assert are_hypocoristic_match("", "")
        assert not are_hypocoristic_match("", "Juan")
        assert not are_hypocoristic_match("Juan", "")

    def test_whitespace_handling(self):
        assert are_hypocoristic_match(" Paco ", " Francisco ")

    def test_accent_handling(self):
        assert are_hypocoristic_match("José", "Pepe")
        assert are_hypocoristic_match("Jesús", "Chucho")

    def test_compound_names(self):
        """José María → Chema."""
        assert are_hypocoristic_match("Chema", "JoseMaría")
        assert are_hypocoristic_match("Chema", "josemaria")


# ============================================================================
# get_formal_name / get_hypocoristics
# ============================================================================


class TestGetFormalName:
    def test_paco(self):
        assert get_formal_name("Paco") == "francisco"

    def test_lola(self):
        assert get_formal_name("Lola") == "dolores"

    def test_formal_name_returns_none(self):
        """Un nombre formal no es hipocorístico de otro."""
        assert get_formal_name("Juan") is None

    def test_unknown_name(self):
        assert get_formal_name("Zxqwerty") is None


class TestGetHypocoristics:
    def test_francisco(self):
        hyps = get_hypocoristics("Francisco")
        assert "paco" in hyps
        assert "curro" in hyps
        assert "fran" in hyps

    def test_unknown(self):
        assert get_hypocoristics("Zxqwerty") == []

    def test_case_insensitive(self):
        assert get_hypocoristics("FRANCISCO") == get_hypocoristics("francisco")


# ============================================================================
# strip_accents
# ============================================================================


class TestStripAccentsFusion:
    """strip_accents en semantic_fusion.py."""

    def test_basic(self):
        assert strip_accents("María") == "Maria"

    def test_preserves_ñ(self):
        assert strip_accents("niño") == "niño"

    def test_preserves_Ñ(self):
        assert strip_accents("Ñoño") == "Ñoño"

    def test_empty(self):
        assert strip_accents("") == ""

    def test_no_accents(self):
        assert strip_accents("abc") == "abc"

    def test_multiple_accents(self):
        assert strip_accents("áéíóú") == "aeiou"


# ============================================================================
# normalize_for_comparison
# ============================================================================


class TestNormalizeForComparison:
    def test_basic(self):
        assert normalize_for_comparison("María García") == "maria garcia"

    def test_accents(self):
        assert normalize_for_comparison("José") == "jose"

    def test_empty(self):
        assert normalize_for_comparison("") == ""

    def test_whitespace(self):
        assert normalize_for_comparison("  Juan   Pedro  ") == "juan pedro"

    def test_preserves_ñ(self):
        result = normalize_for_comparison("Ñoño")
        assert "ñ" in result


# ============================================================================
# generate_name_variants
# ============================================================================


class TestGenerateNameVariants:
    def test_basic_variants(self):
        variants = generate_name_variants("María García")
        assert len(variants) > 0
        assert "maría garcía" in {v.lower() for v in variants}

    def test_empty(self):
        variants = generate_name_variants("")
        # generate_name_variants returns {''} for empty input
        meaningful = {v for v in variants if v.strip()}
        assert len(meaningful) == 0

    def test_single_name(self):
        variants = generate_name_variants("Juan")
        assert len(variants) >= 1


# ============================================================================
# strip_interior_particles
# ============================================================================


class TestStripInteriorParticles:
    def test_de_la(self):
        assert strip_interior_particles("García de la Cruz") == "García Cruz"

    def test_del(self):
        result = strip_interior_particles("López del Valle")
        assert "Valle" in result
        assert "del" not in result

    def test_no_particles(self):
        assert strip_interior_particles("García López") == "García López"

    def test_empty(self):
        assert strip_interior_particles("") == ""


# ============================================================================
# Dictionary integrity
# ============================================================================


class TestDictionaryIntegrity:
    """Verifica integridad del diccionario de hipocorísticos."""

    def test_all_keys_lowercase(self):
        for key in SPANISH_HYPOCORISTICS:
            assert key == key.lower(), f"Key no es lowercase: {key}"

    def test_all_values_lowercase(self):
        for key, values in SPANISH_HYPOCORISTICS.items():
            for v in values:
                assert v == v.lower(), f"Valor no es lowercase: {v} (de {key})"

    def test_no_empty_lists(self):
        for key, values in SPANISH_HYPOCORISTICS.items():
            assert len(values) > 0, f"Lista vacía para: {key}"

    def test_no_duplicate_values_within_key(self):
        for key, values in SPANISH_HYPOCORISTICS.items():
            assert len(values) == len(set(values)), f"Duplicados en {key}: {values}"

    def test_minimum_entries(self):
        """Debe haber al menos 50 nombres formales."""
        assert len(SPANISH_HYPOCORISTICS) >= 50

    def test_has_common_names(self):
        """Debe incluir los nombres más comunes."""
        must_have = ["francisco", "jose", "maria", "manuel", "dolores", "carmen"]
        for name in must_have:
            assert name in SPANISH_HYPOCORISTICS, f"Falta nombre común: {name}"
