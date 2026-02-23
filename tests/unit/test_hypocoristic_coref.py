"""
Tests para integración de hipocorísticos en el pipeline de correferencias.

Verifica que las variantes de nombres (Mari↔María, Paco↔Francisco, Dani↔Daniel)
se reconocen correctamente durante la resolución de correferencias, no solo
durante la fusión de entidades post-NER.
"""

import pytest

from narrative_assistant.nlp.coreference_resolver import (
    Gender,
    HeuristicsCorefMethod,
    Mention,
    MentionType,
    MorphoCorefMethod,
    Number,
)


# ============================================================================
# Utilidades para crear menciones de prueba
# ============================================================================


def _make_mention(
    text: str,
    start: int,
    end: int,
    mention_type: MentionType = MentionType.PROPER_NOUN,
    gender: Gender = Gender.UNKNOWN,
    number: Number = Number.SINGULAR,
    sentence_idx: int = 0,
    chapter_idx: int = 0,
) -> Mention:
    return Mention(
        text=text,
        start_char=start,
        end_char=end,
        mention_type=mention_type,
        gender=gender,
        number=number,
        sentence_idx=sentence_idx,
        chapter_idx=chapter_idx,
    )


# ============================================================================
# Tests: HeuristicsCorefMethod con hipocorísticos
# ============================================================================


class TestHeuristicsHypocoristic:
    """Verifica que HeuristicsCorefMethod da bonus a hipocorísticos."""

    @pytest.fixture
    def method(self):
        return HeuristicsCorefMethod()

    def test_paco_francisco_bonus(self, method):
        """Paco y Francisco deben recibir bonus de hipocorístico."""
        anaphor = _make_mention("Paco", 50, 54, sentence_idx=1)
        candidates = [
            _make_mention("Francisco", 0, 9, sentence_idx=0),
            _make_mention("Pedro", 15, 20, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Francisco caminaba. Pedro estaba sentado. Paco se rió.")
        # Francisco debe tener score más alto por hipocorístico
        assert results[0][0].text == "Francisco"
        assert results[0][1] > results[1][1]
        assert "hipocorístico" in results[0][2]

    def test_mari_maria_bonus(self, method):
        """Mari y María deben reconocerse como variantes."""
        anaphor = _make_mention("Mari", 40, 44, sentence_idx=1)
        candidates = [
            _make_mention("María", 0, 5, sentence_idx=0),
            _make_mention("Elena", 12, 17, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "María estaba en casa. Elena preparaba café. Mari llamó.")
        assert results[0][0].text == "María"
        assert "hipocorístico" in results[0][2]

    def test_dani_daniel_bonus(self, method):
        """Dani y Daniel deben reconocerse como variantes."""
        anaphor = _make_mention("Dani", 35, 39, sentence_idx=1)
        candidates = [
            _make_mention("Daniel", 0, 6, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Daniel estudió. Dani aprobó.")
        assert results[0][0].text == "Daniel"
        assert "hipocorístico" in results[0][2]

    def test_transitive_paco_curro(self, method):
        """Paco y Curro, ambos de Francisco, deben reconocerse."""
        anaphor = _make_mention("Curro", 30, 35, sentence_idx=1)
        candidates = [
            _make_mention("Paco", 0, 4, sentence_idx=0),
            _make_mention("Luis", 10, 14, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Paco y Luis estaban. Curro llegó.")
        assert results[0][0].text == "Paco"
        assert "hipocorístico" in results[0][2]

    def test_no_false_positive_different_names(self, method):
        """Juan y Pedro NO son hipocorísticos."""
        anaphor = _make_mention("Juan", 30, 34, sentence_idx=1)
        candidates = [
            _make_mention("Pedro", 0, 5, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Pedro caminaba. Juan llegó.")
        # No debe tener razón "hipocorístico"
        for _mention, _score, reasoning in results:
            assert "hipocorístico" not in reasoning

    def test_same_name_no_hypocoristic_label(self, method):
        """María y María no se marcan como hipocorístico (son el mismo nombre)."""
        anaphor = _make_mention("María", 30, 35, sentence_idx=1)
        candidates = [
            _make_mention("María", 0, 5, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "María salió. María volvió.")
        # No aplica hipocorístico si es el mismo nombre
        for _mention, _score, reasoning in results:
            assert "hipocorístico" not in reasoning

    def test_possessive_inherits_from_hypocoristic(self, method):
        """Posesivo después de hipocorístico: 'Paco entró. Sus ojos...'"""
        # Aquí el posesivo no activa hipocorístico (es un posesivo, no nombre propio)
        anaphor = _make_mention(
            "Sus", 20, 23, mention_type=MentionType.POSSESSIVE, sentence_idx=1
        )
        candidates = [
            _make_mention("Paco", 0, 4, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Paco entró. Sus ojos brillaban.")
        # Posesivo no activa hipocorístico (no es PROPER_NOUN)
        for _mention, _score, reasoning in results:
            assert "hipocorístico" not in reasoning

    def test_lola_dolores_bonus(self, method):
        """Lola y Dolores deben reconocerse como variantes."""
        anaphor = _make_mention("Lola", 35, 39, sentence_idx=1)
        candidates = [
            _make_mention("Dolores", 0, 7, sentence_idx=0),
            _make_mention("Carmen", 12, 18, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "Dolores y Carmen estaban. Lola saludó.")
        assert results[0][0].text == "Dolores"

    def test_pepe_jose_bonus(self, method):
        """Pepe y José deben reconocerse como variantes."""
        anaphor = _make_mention("Pepe", 30, 34, sentence_idx=1)
        candidates = [
            _make_mention("José", 0, 4, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "José trabajaba. Pepe descansó.")
        assert results[0][0].text == "José"
        assert "hipocorístico" in results[0][2]


# ============================================================================
# Tests: MorphoCorefMethod con hipocorísticos
# ============================================================================


class TestMorphoHypocoristic:
    """Verifica que MorphoCorefMethod da bonus a hipocorísticos."""

    @pytest.fixture
    def method(self):
        return MorphoCorefMethod()

    def test_paco_francisco_bonus(self, method):
        """Paco y Francisco deben recibir bonus en método morpho."""
        anaphor = _make_mention("Paco", 50, 54, sentence_idx=1)
        candidates = [
            _make_mention("Francisco", 0, 9, sentence_idx=0),
            _make_mention("Pedro", 15, 20, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "")
        # Francisco debe tener score más alto
        francisco_score = next(s for m, s, _ in results if m.text == "Francisco")
        pedro_score = next(s for m, s, _ in results if m.text == "Pedro")
        assert francisco_score > pedro_score

    def test_mari_maria_morpho(self, method):
        """Mari y María en método morpho."""
        anaphor = _make_mention("Mari", 30, 34, sentence_idx=1)
        candidates = [
            _make_mention("María", 0, 5, sentence_idx=0),
            _make_mention("Juan", 10, 14, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "")
        maria_score = next(s for m, s, _ in results if m.text == "María")
        juan_score = next(s for m, s, _ in results if m.text == "Juan")
        assert maria_score > juan_score

    def test_no_hypocoristic_for_pronoun_candidates(self, method):
        """Pronombres no deben activar hipocorístico."""
        anaphor = _make_mention("él", 20, 22, mention_type=MentionType.PRONOUN, sentence_idx=1)
        candidates = [
            _make_mention("Francisco", 0, 9, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "")
        for _mention, _score, reasoning in results:
            assert "hipocorístico" not in reasoning


# ============================================================================
# Tests: ScopeResolver con hipocorísticos
# ============================================================================


class TestScopeResolverHypocoristic:
    """Verifica que ScopeResolver._names_match_flexible detecta hipocorísticos."""

    @pytest.fixture
    def resolver(self, shared_spacy_nlp):
        from narrative_assistant.nlp.scope_resolver import ScopeResolver
        text = "Francisco y Pedro estaban en la plaza."
        doc = shared_spacy_nlp(text)
        return ScopeResolver(doc, text)

    def test_paco_francisco_match(self, resolver):
        """_names_match_flexible reconoce Paco↔Francisco."""
        assert resolver._names_match_flexible("Paco", "Francisco")
        assert resolver._names_match_flexible("Francisco", "Paco")

    def test_mari_maria_match(self, resolver):
        """_names_match_flexible reconoce Mari↔María."""
        assert resolver._names_match_flexible("Mari", "María")

    def test_lola_dolores_match(self, resolver):
        """_names_match_flexible reconoce Lola↔Dolores."""
        assert resolver._names_match_flexible("Lola", "Dolores")

    def test_normal_match_still_works(self, resolver):
        """Matching normal sigue funcionando."""
        assert resolver._names_match_flexible("María", "Maria")
        assert resolver._names_match_flexible("El hombre", "hombre")

    def test_different_names_no_match(self, resolver):
        """Nombres distintos no deben matchear."""
        assert not resolver._names_match_flexible("Juan", "Pedro")
        assert not resolver._names_match_flexible("María", "Carmen")


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestHypocorsiticEdgeCases:
    """Casos extremos para la integración de hipocorísticos."""

    def test_empty_name_no_crash(self):
        """Nombres vacíos no deben causar crash."""
        method = HeuristicsCorefMethod()
        anaphor = _make_mention("", 0, 0, sentence_idx=0)
        candidates = [_make_mention("Francisco", 10, 19, sentence_idx=0)]
        # No debe crashear
        results = method.resolve(anaphor, candidates, "")
        assert isinstance(results, list)

    def test_accent_variants(self):
        """Variantes con/sin tilde deben funcionar."""
        method = HeuristicsCorefMethod()
        anaphor = _make_mention("Paco", 30, 34, sentence_idx=1)
        candidates = [
            _make_mention("José", 0, 4, sentence_idx=0),
        ]
        results = method.resolve(anaphor, candidates, "")
        # Paco → Francisco, José no es hipocorístico de Paco
        for _m, _s, reason in results:
            assert "hipocorístico" not in reason

    def test_compound_name_hypocoristic(self):
        """José María → Pepe debería funcionar."""
        from narrative_assistant.entities.semantic_fusion import are_hypocoristic_match
        assert are_hypocoristic_match("Pepe", "José")

    def test_multiple_candidates_ranking(self):
        """Con múltiples candidatos, el hipocorístico debe rankear arriba."""
        method = HeuristicsCorefMethod()
        anaphor = _make_mention("Paco", 80, 84, sentence_idx=2)
        candidates = [
            _make_mention("Luis", 0, 4, sentence_idx=0),
            _make_mention("Francisco", 10, 19, sentence_idx=0),
            _make_mention("Carmen", 25, 31, sentence_idx=1),
            _make_mention("Alberto", 40, 47, sentence_idx=1),
        ]
        results = method.resolve(anaphor, candidates, "Luis y Francisco charlaban. Carmen y Alberto llegaron. Paco se unió.")
        # Francisco debe ser el primero por hipocorístico
        assert results[0][0].text == "Francisco"
