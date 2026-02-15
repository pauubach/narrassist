"""Tests para StyleRegisterDetector."""

from __future__ import annotations

import pytest

from narrative_assistant.corrections.config import StyleRegisterConfig
from narrative_assistant.corrections.detectors.style_register import (
    StyleRegisterDetector,
)


def _make_detector(profile: str = "strict", **kwargs) -> StyleRegisterDetector:
    return StyleRegisterDetector(StyleRegisterConfig(enabled=True, profile=profile, **kwargs))


def _types(issues) -> list[str]:
    """Extrae issue_type de cada issue."""
    return [i.issue_type for i in issues]


# ============================================================================
# Tests por perfil
# ============================================================================


class TestStrictProfile:
    """Perfil strict: todo activo (científico/técnico)."""

    def setup_method(self):
        self.detector = _make_detector("strict")

    def test_first_person_pronoun(self):
        issues = self.detector.detect("Nosotros consideramos que el resultado es válido.")
        types = _types(issues)
        assert "first_person_pronoun" in types

    def test_first_person_verb(self):
        issues = self.detector.detect("Encontramos diferencias significativas en los datos.")
        types = _types(issues)
        assert "first_person_verb" in types

    def test_opinion_verb(self):
        issues = self.detector.detect("Creemos que los datos confirman la hipótesis.")
        types = _types(issues)
        assert "opinion_verb" in types

    def test_vague_quantifier(self):
        issues = self.detector.detect("Varios estudios sugieren que muchos participantes mejoraron.")
        types = _types(issues)
        assert types.count("vague_quantifier") >= 2

    def test_assertion_no_hedging(self):
        issues = self.detector.detect("Los resultados confirman que la hipótesis es correcta. Claramente, los datos lo avalan.")
        types = _types(issues)
        assert "assertion_no_hedging" in types

    def test_assertion_with_hedging_not_flagged(self):
        text = "Los resultados posiblemente demuestran que la hipótesis es correcta."
        issues = self.detector.detect(text)
        types = _types(issues)
        assert "assertion_no_hedging" not in types

    def test_assertion_adverb(self):
        issues = self.detector.detect("Evidentemente, los datos reflejan una tendencia.")
        types = _types(issues)
        assert "assertion_no_hedging" in types

    def test_emotional_language(self):
        issues = self.detector.detect("Sorprendentemente, el grupo A superó al grupo B.")
        types = _types(issues)
        assert "emotional_language" in types

    def test_multiple_issues_in_one_text(self):
        text = "Nosotros creemos que varios estudios demuestran sorprendentemente los resultados."
        issues = self.detector.detect(text)
        types = set(_types(issues))
        assert "first_person_pronoun" in types
        assert "opinion_verb" in types
        assert "vague_quantifier" in types
        assert "emotional_language" in types


class TestFormalProfile:
    """Perfil formal: 1ª persona es warning, hedging activo."""

    def setup_method(self):
        self.detector = _make_detector("formal")

    def test_first_person_lower_confidence(self):
        issues = self.detector.detect("Nosotros observamos cambios.")
        fp_issues = [i for i in issues if i.issue_type == "first_person_pronoun"]
        assert len(fp_issues) >= 1
        assert fp_issues[0].confidence < 0.80  # formal = 0.70

    def test_vague_quantifier_active(self):
        issues = self.detector.detect("Varios autores coinciden en que muchos casos son graves.")
        types = _types(issues)
        assert "vague_quantifier" in types


class TestModerateProfile:
    """Perfil moderate: 1ª persona y opinión desactivados."""

    def setup_method(self):
        self.detector = _make_detector("moderate")

    def test_first_person_not_flagged(self):
        issues = self.detector.detect("Yo recuerdo que nosotros vinimos aquí.")
        types = _types(issues)
        assert "first_person_pronoun" not in types
        assert "first_person_verb" not in types

    def test_opinion_verb_not_flagged(self):
        issues = self.detector.detect("Creo que fue importante para mí.")
        types = _types(issues)
        assert "opinion_verb" not in types

    def test_vague_quantifier_still_active(self):
        issues = self.detector.detect("Varios amigos vinieron a visitarme.")
        types = _types(issues)
        assert "vague_quantifier" in types

    def test_emotional_not_flagged(self):
        issues = self.detector.detect("Afortunadamente, todo salió bien.")
        types = _types(issues)
        assert "emotional_language" not in types


class TestFreeProfile:
    """Perfil free: todo desactivado (ficción)."""

    def test_nothing_flagged(self):
        detector = _make_detector("free")
        text = "Yo creo que varios amigos demuestran sorprendentemente su lealtad."
        issues = detector.detect(text)
        assert issues == []


# ============================================================================
# Exención de diálogo
# ============================================================================


class TestDialogueExemption:

    def test_dialogue_raya_not_flagged(self):
        detector = _make_detector("strict")
        text = "—Nosotros creemos que es importante —dijo María."
        issues = detector.detect(text)
        types = _types(issues)
        assert "first_person_pronoun" not in types
        assert "opinion_verb" not in types

    def test_dialogue_angular_quotes_not_flagged(self):
        detector = _make_detector("strict")
        text = "Pedro respondió: «Yo creo que varios estudios lo demuestran»."
        issues = detector.detect(text)
        types = _types(issues)
        assert "first_person_pronoun" not in types
        assert "opinion_verb" not in types

    def test_narration_around_dialogue_still_flagged(self):
        detector = _make_detector("strict")
        text = "Nosotros observamos que —es cierto —confirmó ella— el dato es bueno."
        issues = detector.detect(text)
        types = _types(issues)
        # "Nosotros" is outside dialogue
        assert "first_person_pronoun" in types

    def test_skip_dialogue_disabled(self):
        detector = _make_detector("strict", skip_dialogue=False)
        text = "—Nosotros creemos que es importante —dijo María."
        issues = detector.detect(text)
        types = _types(issues)
        # With skip_dialogue=False, should find issues inside dialogue
        assert len(issues) > 0

    def test_skip_quotes_disabled_flags_quoted_text(self):
        detector = _make_detector("strict", skip_quotes=False)
        text = "Pedro respondió: «Yo creo que varios estudios lo demuestran»."
        issues = detector.detect(text)
        types = _types(issues)
        # With skip_quotes=False, should find issues inside quotes
        assert "first_person_pronoun" in types

    def test_skip_quotes_enabled_skips_quoted_text(self):
        detector = _make_detector("strict", skip_quotes=True)
        text = "Pedro respondió: «Yo creo que varios estudios lo demuestran»."
        issues = detector.detect(text)
        types = _types(issues)
        assert "first_person_pronoun" not in types

    def test_skip_dialogue_only_not_quotes(self):
        """skip_dialogue=True, skip_quotes=False: masks dashes but not quotes."""
        detector = _make_detector("strict", skip_dialogue=True, skip_quotes=False)
        text = "—Hola —dijo Ana.\nPedro escribió: «Yo creo que es importante»."
        issues = detector.detect(text)
        types = _types(issues)
        # Quotes not masked → "Yo" flagged
        assert "first_person_pronoun" in types


# ============================================================================
# Disabled detector
# ============================================================================


class TestDisabledDetector:

    def test_returns_empty_when_disabled(self):
        detector = StyleRegisterDetector(StyleRegisterConfig(enabled=False))
        issues = detector.detect("Nosotros creemos que varios demuestran sorprendentemente.")
        assert issues == []

    def test_returns_empty_with_default_config(self):
        """Default config has enabled=False."""
        detector = StyleRegisterDetector()
        issues = detector.detect("Nosotros creemos que varios estudios demuestran.")
        assert issues == []


# ============================================================================
# Sugerencias (rewrites deterministas)
# ============================================================================


class TestSuggestions:

    def setup_method(self):
        self.detector = _make_detector("strict")

    def test_pronoun_has_suggestion(self):
        issues = self.detector.detect("Nosotros medimos los resultados.")
        pronoun_issues = [i for i in issues if i.issue_type == "first_person_pronoun"]
        assert len(pronoun_issues) >= 1
        assert pronoun_issues[0].suggestion is not None
        assert "impersonal" in pronoun_issues[0].suggestion.lower()

    def test_opinion_verb_has_suggestion(self):
        issues = self.detector.detect("Creemos que los datos son consistentes.")
        opinion_issues = [i for i in issues if i.issue_type == "opinion_verb"]
        assert len(opinion_issues) >= 1
        assert opinion_issues[0].suggestion is not None

    def test_first_person_verb_has_impersonal(self):
        issues = self.detector.detect("Encontramos diferencias significativas.")
        verb_issues = [i for i in issues if i.issue_type == "first_person_verb"]
        assert len(verb_issues) >= 1
        assert "encontró" in verb_issues[0].suggestion

    def test_vague_quantifier_has_suggestion(self):
        issues = self.detector.detect("Varios estudios lo confirman.")
        vague_issues = [i for i in issues if i.issue_type == "vague_quantifier"]
        assert len(vague_issues) >= 1
        assert vague_issues[0].suggestion is not None

    def test_emotional_has_suggestion(self):
        issues = self.detector.detect("Sorprendentemente, se halló una correlación.")
        emotional_issues = [i for i in issues if i.issue_type == "emotional_language"]
        assert len(emotional_issues) >= 1
        assert emotional_issues[0].suggestion is not None


# ============================================================================
# Posiciones
# ============================================================================


class TestPositions:

    def test_positions_match_original_text(self):
        detector = _make_detector("strict")
        text = "En este artículo, nosotros analizamos los datos."
        issues = detector.detect(text)
        fp = [i for i in issues if i.issue_type == "first_person_pronoun"]
        assert len(fp) >= 1
        issue = fp[0]
        assert text[issue.start_char : issue.end_char].lower() == "nosotros"

    def test_positions_after_dialogue_mask(self):
        detector = _make_detector("strict")
        text = "—Hola —dijo Juan— ¿qué tal?\nNosotros observamos los resultados."
        issues = detector.detect(text)
        fp = [i for i in issues if i.issue_type == "first_person_pronoun"]
        assert len(fp) >= 1
        issue = fp[0]
        assert text[issue.start_char : issue.end_char].lower() == "nosotros"


# ============================================================================
# CorrectionIssue fields
# ============================================================================


class TestIssueFields:

    def test_category_is_style_register(self):
        detector = _make_detector("strict")
        issues = detector.detect("Nosotros analizamos los datos.")
        assert all(i.category == "style_register" for i in issues)

    def test_rule_id_present(self):
        detector = _make_detector("strict")
        issues = detector.detect("Nosotros creemos que sorprendentemente varios demuestran que funciona.")
        assert all(i.rule_id is not None for i in issues)
        rule_ids = {i.rule_id for i in issues}
        assert "STYLE_FIRST_PERSON_PRONOUN" in rule_ids

    def test_chapter_index_propagated(self):
        detector = _make_detector("strict")
        issues = detector.detect("Nosotros lo observamos.", chapter_index=5)
        assert all(i.chapter_index == 5 for i in issues)


# ============================================================================
# Parametrizado cruzado perfil × sub-detector
# ============================================================================


@pytest.mark.parametrize(
    "text,profile,expected_types",
    [
        # Strict: todo
        (
            "Nosotros creemos que es evidente que varios datos sorprendentemente lo confirman.",
            "strict",
            {"first_person_pronoun", "opinion_verb", "vague_quantifier", "assertion_no_hedging", "emotional_language"},
        ),
        # Formal: todo pero con menor confianza
        (
            "Nosotros creemos que es evidente que varios datos sorprendentemente lo confirman.",
            "formal",
            {"first_person_pronoun", "opinion_verb", "vague_quantifier", "assertion_no_hedging", "emotional_language"},
        ),
        # Moderate: solo vague + hedging
        (
            "Nosotros creemos que es evidente que varios datos sorprendentemente lo confirman.",
            "moderate",
            {"vague_quantifier", "assertion_no_hedging"},
        ),
        # Free: nada
        (
            "Nosotros creemos que es evidente que varios datos sorprendentemente lo confirman.",
            "free",
            set(),
        ),
    ],
    ids=["strict", "formal", "moderate", "free"],
)
def test_profile_cross_detection(text, profile, expected_types):
    detector = _make_detector(profile)
    issues = detector.detect(text)
    actual_types = {i.issue_type for i in issues}
    assert actual_types == expected_types


# ============================================================================
# Hedging nearby suppresses assertion
# ============================================================================


class TestHedgingNearby:

    def test_hedging_before_assertion_suppresses(self):
        detector = _make_detector("strict")
        text = "Los datos posiblemente demuestran que la tendencia existe."
        issues = detector.detect(text)
        types = _types(issues)
        assert "assertion_no_hedging" not in types

    def test_hedging_after_assertion_suppresses(self):
        detector = _make_detector("strict")
        text = "Es evidente que podría haber una correlación."
        issues = detector.detect(text)
        types = _types(issues)
        assert "assertion_no_hedging" not in types

    def test_no_hedging_nearby_flags(self):
        detector = _make_detector("strict")
        text = "Los resultados claramente confirman que el efecto es real."
        issues = detector.detect(text)
        types = _types(issues)
        assert "assertion_no_hedging" in types
