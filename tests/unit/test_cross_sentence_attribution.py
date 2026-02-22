"""
Tests para las 5 técnicas de mejora de cross-sentence attribution.

T1: Normalización de breaks falsos (puntos suspensivos, abreviaturas, decimales)
T2: BASE=175 + modulación por señal lingüística
T3: Concordancia de número (singular/plural)
T4: Concordancia de género del predicado
T5: Linking narrador 1a persona
"""

import pytest

from narrative_assistant.nlp.sentence_utils import (
    CROSS_SENTENCE_BASE_PENALTY,
    detect_continuity_signal as _detect_continuity_signal,
    normalize_sentence_breaks as _normalize_sentence_breaks,
)


# ============================================================================
# T1: Normalización de breaks
# ============================================================================


class TestNormalizeSentenceBreaks:
    """T1: _normalize_sentence_breaks descarta breaks falsos."""

    def test_normal_period(self):
        assert _normalize_sentence_breaks("salió. Entró") == 1

    def test_ellipsis_three_dots(self):
        """Puntos suspensivos (...) cuentan como 1, no 3."""
        assert _normalize_sentence_breaks("miraba... Tenía") == 1

    def test_ellipsis_many_dots(self):
        """Muchos puntos seguidos = 1 break."""
        assert _normalize_sentence_breaks("miraba..... Tenía") == 1

    def test_abbreviation_dr(self):
        """'Dr.' no es fin de oración."""
        assert _normalize_sentence_breaks("el Dr. García") == 0

    def test_abbreviation_sr(self):
        """'Sr.' no es fin de oración."""
        assert _normalize_sentence_breaks("el Sr. López era") == 0

    def test_abbreviation_sra(self):
        assert _normalize_sentence_breaks("la Sra. Martínez") == 0

    def test_abbreviation_etc(self):
        assert _normalize_sentence_breaks("coches, motos, etc. y más") == 0

    def test_decimal_number(self):
        """Punto decimal no es fin de oración."""
        assert _normalize_sentence_breaks("medía 1.85 metros") == 0

    def test_initials(self):
        """Iniciales J.R.R. no son fin de oración."""
        assert _normalize_sentence_breaks("como J.R.R. Tolkien") == 0

    def test_enumeration(self):
        """'1. 2. 3.' no son fines de oración."""
        assert _normalize_sentence_breaks(" 1. Ricardo 2. Tomás") == 0

    def test_mixed_real_and_fake(self):
        """Real break + abbreviation = 1."""
        assert _normalize_sentence_breaks("el Dr. García salió. Entró") == 1

    def test_exclamation(self):
        assert _normalize_sentence_breaks("¡Vete! Tenía") == 1

    def test_question(self):
        assert _normalize_sentence_breaks("¿Qué? Era") == 1

    def test_no_breaks(self):
        assert _normalize_sentence_breaks("era alto y fuerte") == 0

    def test_multiple_real_breaks(self):
        assert _normalize_sentence_breaks("salió. Caminó. Volvió") == 2


# ============================================================================
# T2: Señales de continuidad lingüística
# ============================================================================


class TestContinuitySignal:
    """T2: _detect_continuity_signal detecta patrones regex."""

    def test_no_signal(self):
        text = "María salió. El cielo era azul."
        signal = _detect_continuity_signal(text, 5, 25)
        assert signal == 0.0

    def test_gerund_signal(self):
        """Gerundio al inicio de oración = señal alta."""
        text = "Juan visitó a Isabel. Aprovechando que era médico, le pidió ayuda."
        signal = _detect_continuity_signal(text, 4, 42)
        assert signal >= 0.70

    def test_causal_porque(self):
        text = "Juan se presentó. Porque era ingeniero, fue elegido."
        signal = _detect_continuity_signal(text, 4, 32)
        assert signal >= 0.65

    def test_causal_ya_que(self):
        text = "María no asistió. Ya que estaba enferma, envió a su asistente."
        signal = _detect_continuity_signal(text, 5, 32)
        assert signal >= 0.65

    def test_copular_prodrop(self):
        """'Era alto' sin sujeto = señal media."""
        text = "Fernando sonrió. Era alto."
        signal = _detect_continuity_signal(text, 8, 21)
        assert signal >= 0.55

    def test_temporal_entonces(self):
        text = "Pedro guardó el arma. Entonces se quitó el sombrero."
        signal = _detect_continuity_signal(text, 5, 30)
        assert signal >= 0.45

    def test_possessive_sus(self):
        text = "Elena se fue. Sus ojos brillaban."
        signal = _detect_continuity_signal(text, 5, 18)
        assert signal >= 0.40

    def test_adversative(self):
        text = "María era enfermera. Sin embargo, no le gustaban los hospitales."
        signal = _detect_continuity_signal(text, 5, 50)
        assert signal >= 0.30

    def test_same_sentence_no_signal(self):
        """Sin break entre entity y attribute = 0 (no aplica)."""
        text = "Juan era alto."
        signal = _detect_continuity_signal(text, 4, 9)
        assert signal == 0.0


# ============================================================================
# T2: Constante BASE_PENALTY
# ============================================================================


class TestBasePenalty:
    def test_base_penalty_value(self):
        assert CROSS_SENTENCE_BASE_PENALTY == 175

    def test_base_penalty_not_500(self):
        """Verificar que no se ha revertido al valor antiguo."""
        assert CROSS_SENTENCE_BASE_PENALTY < 300


# ============================================================================
# T3 + T4: Concordancia número/género en scope_resolver
# (Requieren spaCy — marcados como @heavy si no hay modelo)
# ============================================================================


class TestNumberAgreementFiltering:
    """T3: _filter_by_number_agreement en ScopeResolver."""

    @pytest.fixture
    def resolver(self, shared_spacy_nlp):
        """ScopeResolver con texto de prueba."""
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Clara era la mayor. Vivía con Rosa y con Blanca. Tenía el pelo rizado."
        doc = shared_spacy_nlp(text)
        return ScopeResolver(doc, text)

    def test_singular_verb_eliminates_coordinated_plural(self, resolver):
        """'Tenía' (singular) elimina 'Rosa y Blanca' (coordinación plural)."""
        candidates = {"Clara", "Rosa", "Blanca"}
        entity_mentions = [
            ("Clara", 0, 5, "PER"),
            ("Rosa", 30, 34, "PER"),
            ("Blanca", 41, 47, "PER"),
        ]
        result = resolver._filter_by_number_agreement(
            candidates, 20, 48, entity_mentions
        )
        assert "Clara" in result
        assert "Rosa" not in result or "Blanca" not in result

    def test_no_coordination_keeps_all(self, shared_spacy_nlp):
        """Sin coordinación, mantener todos los candidatos."""
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Juan habló con Pedro. Tenía barba."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = {"Juan", "Pedro"}
        entity_mentions = [
            ("Juan", 0, 4, "PER"),
            ("Pedro", 15, 20, "PER"),
        ]
        result = resolver._filter_by_number_agreement(
            candidates, 0, 21, entity_mentions
        )
        # Sin coordinación, ambos se mantienen
        assert len(result) == 2


class TestPredicateGenderFiltering:
    """T4: _get_predicate_gender y _filter_by_predicate_gender."""

    def test_filter_by_masculine_predicate(self, shared_spacy_nlp):
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Gonzalo habló con Isabel. Era alto."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = {"Gonzalo", "Isabel"}
        result = resolver._filter_by_predicate_gender(candidates, "Masc")
        assert "Gonzalo" in result
        assert "Isabel" not in result

    def test_filter_by_feminine_predicate(self, shared_spacy_nlp):
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "El viejo habló con Clara. Estaba cansada."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = {"viejo", "Clara"}
        result = resolver._filter_by_predicate_gender(candidates, "Fem")
        assert "Clara" in result

    def test_no_gender_keeps_all(self, shared_spacy_nlp):
        from narrative_assistant.nlp.scope_resolver import ScopeResolver

        text = "Juan habló con María. Era inteligente."
        doc = shared_spacy_nlp(text)
        resolver = ScopeResolver(doc, text)

        candidates = {"Juan", "María"}
        # "inteligente" no tiene género → mantener todos
        result = resolver._filter_by_predicate_gender(candidates, None)
        assert len(result) == 2


# ============================================================================
# T5: Linking narrador primera persona
# ============================================================================


class TestFirstPersonNarrator:
    """T5: _find_narrator_entity detecta al narrador."""

    def _make_mixin(self):
        from narrative_assistant.nlp.attr_entity_resolution import (
            AttributeEntityResolutionMixin,
        )
        return AttributeEntityResolutionMixin()

    def test_me_llamo_pattern(self):
        mixin = self._make_mixin()
        text = "Me llamo Paco. Vi a María en la plaza. Tengo los ojos verdes."
        candidates = [
            ("Paco", 9, 13, 47),
            ("María", 20, 25, 35),
        ]
        result = mixin._find_narrator_entity(candidates, text)
        assert result == "Paco"

    def test_soy_pattern(self):
        mixin = self._make_mixin()
        text = "Soy Lucía. Conocí a Roberto en la universidad."
        candidates = [
            ("Lucía", 4, 9, 50),
            ("Roberto", 20, 27, 30),
        ]
        result = mixin._find_narrator_entity(candidates, text)
        assert result == "Lucía"

    def test_mi_nombre_es_pattern(self):
        mixin = self._make_mixin()
        text = "Mi nombre es Fernando. Trabajo aquí desde hace años."
        candidates = [
            ("Fernando", 13, 21, 40),
        ]
        result = mixin._find_narrator_entity(candidates, text)
        assert result == "Fernando"

    def test_no_narrator_found(self):
        mixin = self._make_mixin()
        text = "Juan caminaba por la calle. María lo miraba."
        candidates = [
            ("Juan", 0, 4, 40),
            ("María", 28, 33, 10),
        ]
        result = mixin._find_narrator_entity(candidates, text)
        assert result is None

    def test_yo_name_pattern(self):
        mixin = self._make_mixin()
        text = "Yo, Paco, vi a María en la plaza."
        candidates = [
            ("Paco", 4, 8, 30),
            ("María", 15, 20, 15),
        ]
        result = mixin._find_narrator_entity(candidates, text)
        assert result == "Paco"
