"""
Smoke tests para coreference_resolver.py y scope_resolver.py.

Estos tests verifican que los módulos cargan correctamente y que
las integraciones recientes (hipocorísticos) están disponibles.
"""

import pytest

from narrative_assistant.nlp.coreference_resolver import (
    CorefConfig,
    CoreferenceChain,
    CoreferenceVotingResolver,
    CorefMethod,
    Gender,
    HeuristicsCorefMethod,
    Mention,
    MentionType,
    MorphoCorefMethod,
    Number,
)
from narrative_assistant.nlp.scope_resolver import ScopeResolver

# ============================================================================
# Smoke Tests — Imports y Estructura Básica
# ============================================================================


class TestImportsAndBasicStructure:
    """Verifica que las clases principales están disponibles."""

    def test_coref_config_instantiation(self):
        """CorefConfig debe poder instanciarse."""
        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS],
            min_confidence=0.3,
        )
        assert config.min_confidence == 0.3
        assert CorefMethod.HEURISTICS in config.enabled_methods

    def test_mention_instantiation(self):
        """Mention debe poder instanciarse."""
        m = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        assert m.text == "Juan"
        assert m.mention_type == MentionType.PROPER_NOUN

    def test_coreference_chain_instantiation(self):
        """CoreferenceChain debe poder instanciarse."""
        m1 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        chain = CoreferenceChain(mentions=[m1])
        assert len(chain.mentions) == 1

    def test_morpho_method_has_hypocoristic_check(self):
        """MorphoCorefMethod debe tener método _check_hypocoristic."""
        method = MorphoCorefMethod()
        assert hasattr(method, "_check_hypocoristic")

    def test_heuristics_method_has_hypocoristic_check(self):
        """HeuristicsCorefMethod debe tener método _check_hypocoristic."""
        method = HeuristicsCorefMethod()
        assert hasattr(method, "_check_hypocoristic")

    def test_scope_resolver_has_names_match_flexible(self):
        """ScopeResolver debe tener _names_match_flexible con hipocorísticos."""
        # ScopeResolver requiere doc de spaCy, solo verificamos que el método existe
        assert hasattr(ScopeResolver, "_names_match_flexible")

    def test_scope_resolver_strip_articles_static_method(self):
        """_strip_articles debe ser un método estático funcional."""
        assert ScopeResolver._strip_articles("el gato") == "gato"
        assert ScopeResolver._strip_articles("la casa") == "casa"


# ============================================================================
# Hypocoristic Integration — Verificación
# ============================================================================


class TestHypocorisiticIntegrationAvailable:
    """
    Verifica que la integración de hipocorísticos está disponible.

    Estos tests NO ejecutan la lógica completa (requeriría mocks pesados),
    pero verifican que las funciones están presentes y pueden llamarse.
    """

    def test_morpho_method_can_call_check_hypocoristic(self):
        """_check_hypocoristic debe poder llamarse."""
        method = MorphoCorefMethod()
        # Llamar con nombres que sí son hipocorísticos
        result = method._check_hypocoristic("Paco", "Francisco")
        # Debería retornar True (son hipocorísticos)
        assert result is True

    def test_heuristics_method_can_call_check_hypocoristic(self):
        """_check_hypocoristic debe poder llamarse."""
        method = HeuristicsCorefMethod()
        result = method._check_hypocoristic("Mari", "María")
        assert result is True

    def test_hypocoristic_check_returns_false_for_non_matches(self):
        """Nombres diferentes NO deben ser hipocorísticos."""
        method = MorphoCorefMethod()
        result = method._check_hypocoristic("Juan", "Pedro")
        assert result is False


# ============================================================================
# Mention Equality and Hashing
# ============================================================================


class TestMentionEquality:
    """Mention.__eq__ y __hash__ para deduplicación."""

    def test_mentions_with_same_span_are_equal(self):
        m1 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        m2 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PRONOUN,  # Diferente tipo pero mismo span
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        assert m1 == m2  # Igualdad basada en span, no en tipo
        assert hash(m1) == hash(m2)

    def test_mentions_different_span_not_equal(self):
        m1 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        m2 = Mention(
            text="Juan",
            start_char=10,
            end_char=14,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        assert m1 != m2

    def test_mentions_can_be_in_set(self):
        """Debe poder usarse en set para deduplicar."""
        m1 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        m2 = Mention(
            text="Juan",
            start_char=0,
            end_char=4,  # Mismo span → duplicado
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.MASCULINE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )
        m3 = Mention(
            text="María",
            start_char=10,
            end_char=15,
            mention_type=MentionType.PROPER_NOUN,
            gender=Gender.FEMININE,
            number=Number.SINGULAR,
            sentence_idx=0,
        )

        mentions_set = {m1, m2, m3}
        assert len(mentions_set) == 2  # m1 y m2 se deduplican
