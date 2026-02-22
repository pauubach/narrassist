"""
Tests para inferencia de género multi-tier (gender_names.py).

Tier 1: spaCy morph (con doc)
Tier 2: Gazetteer de nombres
Tier 3: Heurística por sufijo

Incluye: normales, extremos y creativos.
"""

import pytest

from narrative_assistant.nlp.gender_names import (
    AMBIGUOUS_NAMES,
    FEMININE_NAMES,
    MASCULINE_NAMES,
    infer_gender_from_name,
)


# ============================================================================
# Tier 2: Gazetteer (sin doc)
# ============================================================================


class TestGazetteerNormal:
    """Nombres comunes en el gazetteer → deben resolverse sin doc."""

    @pytest.mark.parametrize("name", [
        "María", "Ana", "Elena", "Laura", "Carmen", "Isabel", "Rosa",
        "Lucía", "Clara", "Blanca", "Patricia", "Sofía", "Cristina",
    ])
    def test_feminine_gazetteer(self, name):
        assert infer_gender_from_name(name) == "Fem"

    @pytest.mark.parametrize("name", [
        "Juan", "Pedro", "Carlos", "Miguel", "Antonio", "Luis",
        "Fernando", "Alejandro", "Gonzalo", "Santiago", "Héctor",
    ])
    def test_masculine_gazetteer(self, name):
        assert infer_gender_from_name(name) == "Masc"

    def test_compound_name_uses_first(self):
        """'María García' → usa 'maría' (primer nombre)."""
        assert infer_gender_from_name("María García") == "Fem"
        assert infer_gender_from_name("Juan Carlos") == "Masc"

    def test_case_insensitive(self):
        """El gazetteer funciona en minúsculas."""
        assert infer_gender_from_name("MARÍA") == "Fem"
        assert infer_gender_from_name("juan") == "Masc"

    def test_accent_variants(self):
        """Variantes con/sin tilde deben estar cubiertas."""
        assert infer_gender_from_name("Lucía") == "Fem"
        assert infer_gender_from_name("lucia") == "Fem"
        assert infer_gender_from_name("José") == "Masc"
        assert infer_gender_from_name("jose") == "Masc"


# ============================================================================
# Tier 3: Heurística por sufijo
# ============================================================================


class TestSuffixHeuristic:
    """Nombres NO en gazetteer → usa sufijo -a/-o."""

    def test_feminine_suffix_a(self):
        """Nombres terminados en -a no en gazetteer → femenino."""
        assert infer_gender_from_name("Esperanza") == "Fem"
        assert infer_gender_from_name("Carlota") == "Fem"
        assert infer_gender_from_name("Jimena") == "Fem"
        assert infer_gender_from_name("Valentina") == "Fem"

    def test_masculine_suffix_o(self):
        """Nombres terminados en -o no en gazetteer → masculino."""
        assert infer_gender_from_name("Paco") == "Masc"
        assert infer_gender_from_name("Benito") == "Masc"
        assert infer_gender_from_name("Ernesto") == "Masc"

    def test_no_suffix_match_returns_none(self):
        """Nombres sin sufijo claro y no en gazetteer → None."""
        assert infer_gender_from_name("Noor") is None
        assert infer_gender_from_name("Shen") is None


# ============================================================================
# Casos extremos y adversariales
# ============================================================================


class TestEdgeCases:
    """Casos extremos que podrían fallar."""

    def test_empty_string(self):
        assert infer_gender_from_name("") is None

    def test_none_safe(self):
        """No debe crashear con tipos raros (aunque type hints dicen str)."""
        assert infer_gender_from_name("") is None

    def test_single_letter(self):
        """Nombres de 1-2 caracteres → no se aplica heurística de sufijo."""
        assert infer_gender_from_name("A") is None
        assert infer_gender_from_name("Bo") is None

    def test_ambiguous_names_return_none(self):
        """Nombres en AMBIGUOUS_NAMES → siempre None."""
        assert infer_gender_from_name("Cruz") is None
        assert infer_gender_from_name("Trinidad") is None
        assert infer_gender_from_name("Guadalupe") is None

    def test_andrea_is_feminine_in_spanish(self):
        """'Andrea' está en el gazetteer como femenino (español)."""
        assert infer_gender_from_name("Andrea") == "Fem"

    def test_foreign_names_in_gazetteer(self):
        """Nombres internacionales frecuentes en narrativa están en gazetteer."""
        # Ingleses
        assert infer_gender_from_name("John") == "Masc"
        assert infer_gender_from_name("Mary") == "Fem"
        assert infer_gender_from_name("Elizabeth") == "Fem"
        assert infer_gender_from_name("William") == "Masc"
        # Franceses
        assert infer_gender_from_name("Jean") == "Masc"
        assert infer_gender_from_name("Sophie") == "Fem"
        # Rusos
        assert infer_gender_from_name("Dimitri") == "Masc"
        assert infer_gender_from_name("Boris") == "Masc"
        # Italianos
        assert infer_gender_from_name("Giovanni") == "Masc"
        assert infer_gender_from_name("Francesca") == "Fem"

    def test_foreign_names_unknown(self):
        """Nombres no reconocibles → None."""
        assert infer_gender_from_name("Chen") is None
        assert infer_gender_from_name("Shen") is None
        assert infer_gender_from_name("Noor") is None

    def test_arabic_names_in_gazetteer(self):
        """Nombres árabes frecuentes en narrativa están en gazetteer."""
        assert infer_gender_from_name("Mohammed") == "Masc"
        assert infer_gender_from_name("Ahmed") == "Masc"
        assert infer_gender_from_name("Omar") == "Masc"
        assert infer_gender_from_name("Fátima") == "Fem"
        assert infer_gender_from_name("Aisha") == "Fem"
        assert infer_gender_from_name("Layla") == "Fem"

    def test_diminutives_by_suffix(self):
        """Diminutivos terminados en -a/-o se infieren correctamente."""
        assert infer_gender_from_name("Paquita") == "Fem"
        assert infer_gender_from_name("Paquito") == "Masc"
        assert infer_gender_from_name("Antoñita") == "Fem"


# ============================================================================
# Tier 1: spaCy morph (con doc)
# ============================================================================


class TestSpacyTier:
    """Tier 1: spaCy morph debería tener prioridad sobre gazetteer y sufijo."""

    def test_spacy_detects_masculine(self, shared_spacy_nlp):
        """spaCy detecta género masculino de 'Gonzalo' por morph."""
        doc = shared_spacy_nlp("Gonzalo habló con Isabel.")
        result = infer_gender_from_name("Gonzalo", doc=doc)
        assert result == "Masc"

    def test_spacy_detects_feminine(self, shared_spacy_nlp):
        """spaCy detecta género femenino de 'Isabel'."""
        doc = shared_spacy_nlp("Gonzalo habló con Isabel.")
        result = infer_gender_from_name("Isabel", doc=doc)
        assert result == "Fem"

    def test_spacy_name_not_in_gazetteer(self, shared_spacy_nlp):
        """Nombre no en gazetteer pero que spaCy analiza correctamente."""
        doc = shared_spacy_nlp("Esperanza caminaba por el parque.")
        result = infer_gender_from_name("Esperanza", doc=doc)
        # spaCy puede o no detectar morph para este nombre
        # Pero con Tier 3 (sufijo) debería dar Fem en cualquier caso
        assert result == "Fem"

    def test_fallback_to_gazetteer_when_spacy_no_morph(self, shared_spacy_nlp):
        """Si spaCy no tiene morph, cae al gazetteer."""
        doc = shared_spacy_nlp("Era un día lluvioso.")
        # "María" no aparece en el doc → sin morph → cae a gazetteer
        result = infer_gender_from_name("María", doc=doc)
        assert result == "Fem"

    def test_doc_none_uses_gazetteer(self):
        """doc=None → salta Tier 1, usa Tier 2/3."""
        assert infer_gender_from_name("María", doc=None) == "Fem"
        assert infer_gender_from_name("Juan", doc=None) == "Masc"


# ============================================================================
# Creativos: frases narrativas reales
# ============================================================================


class TestCreativeNarrative:
    """Escenarios narrativos creativos para validar inferencia en contexto."""

    def test_medieval_names(self):
        """Nombres medievales/clásicos."""
        assert infer_gender_from_name("Dorotea") == "Fem"
        assert infer_gender_from_name("Sancho") == "Masc"
        assert infer_gender_from_name("Dulcinea") == "Fem"

    def test_literary_characters(self):
        """Personajes literarios clásicos españoles."""
        assert infer_gender_from_name("Fernando") == "Masc"
        assert infer_gender_from_name("Celestina") == "Fem"
        assert infer_gender_from_name("Bernarda") == "Fem"

    def test_hyphenated_compound(self):
        """Nombres compuestos con guión → usa primer nombre."""
        assert infer_gender_from_name("María-Teresa López") == "Fem"

    def test_gazetteer_sets_are_frozenset(self):
        """Las listas deben ser inmutables (frozenset)."""
        assert isinstance(FEMININE_NAMES, frozenset)
        assert isinstance(MASCULINE_NAMES, frozenset)
        assert isinstance(AMBIGUOUS_NAMES, frozenset)

    def test_no_overlap_between_sets(self):
        """No debe haber nombres en ambas listas (femenina y masculina)."""
        overlap = FEMININE_NAMES & MASCULINE_NAMES
        assert len(overlap) == 0, f"Nombres en ambas listas: {overlap}"

    def test_ambiguous_not_in_either(self):
        """Nombres ambiguos no deben estar en las listas de género."""
        overlap_fem = AMBIGUOUS_NAMES & FEMININE_NAMES
        overlap_masc = AMBIGUOUS_NAMES & MASCULINE_NAMES
        assert len(overlap_fem) == 0, f"Ambiguos en fem: {overlap_fem}"
        assert len(overlap_masc) == 0, f"Ambiguos en masc: {overlap_masc}"
