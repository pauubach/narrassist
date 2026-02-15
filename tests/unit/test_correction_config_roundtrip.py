"""
Tests de round-trip para CorrectionConfig.to_dict() / from_dict().

Verifica que TODAS las configs se serializan y deserializan correctamente,
incluyendo las que estaban ausentes antes de S18-00a.
"""

from narrative_assistant.corrections.config import (
    AnacolutoConfig,
    AnglicismsConfig,
    AgreementConfig,
    ClarityConfig,
    CorrectionConfig,
    CrutchWordsConfig,
    DocumentProfile,
    FieldDictionaryConfig,
    GlossaryConfig,
    GrammarConfig,
    OrthographicVariantsConfig,
    POVConfig,
    RegionalConfig,
    RepetitionConfig,
    StyleRegisterConfig,
    TerminologyConfig,
    TypographyConfig,
)


class TestCorrectionConfigRoundTrip:
    """Round-trip: config → to_dict() → from_dict() → comparar."""

    def test_default_config_roundtrip(self):
        """Config por defecto sobrevive round-trip."""
        original = CorrectionConfig.default()
        restored = CorrectionConfig.from_dict(original.to_dict())

        assert restored.typography.enabled == original.typography.enabled
        assert restored.typography.dialogue_dash == original.typography.dialogue_dash
        assert restored.repetition.sensitivity == original.repetition.sensitivity
        assert restored.agreement.min_confidence == original.agreement.min_confidence

    def test_clarity_config_roundtrip(self):
        """ClarityConfig se serializa y restaura (bug S18-00a)."""
        original = CorrectionConfig.default()
        original.clarity = ClarityConfig(
            enabled=True,
            max_sentence_words=40,
            max_sentence_chars=250,
            warning_sentence_words=30,
            max_subordinates=2,
            min_pauses_per_100_words=5,
            base_confidence=0.90,
        )
        d = original.to_dict()
        assert "clarity" in d
        assert d["clarity"]["max_sentence_words"] == 40

        restored = CorrectionConfig.from_dict(d)
        assert restored.clarity.enabled is True
        assert restored.clarity.max_sentence_words == 40
        assert restored.clarity.max_sentence_chars == 250
        assert restored.clarity.warning_sentence_words == 30
        assert restored.clarity.max_subordinates == 2
        assert restored.clarity.min_pauses_per_100_words == 5
        assert restored.clarity.base_confidence == 0.90

    def test_grammar_config_roundtrip(self):
        """GrammarConfig se serializa y restaura (bug S18-00a)."""
        original = CorrectionConfig.default()
        original.grammar = GrammarConfig(
            enabled=False,
            check_dequeismo=False,
            check_queismo=True,
            min_confidence=0.75,
        )
        d = original.to_dict()
        assert "grammar" in d
        assert d["grammar"]["enabled"] is False

        restored = CorrectionConfig.from_dict(d)
        assert restored.grammar.enabled is False
        assert restored.grammar.check_dequeismo is False
        assert restored.grammar.check_queismo is True
        assert restored.grammar.min_confidence == 0.75

    def test_crutch_words_config_roundtrip(self):
        """CrutchWordsConfig se serializa y restaura (bug S18-00a)."""
        original = CorrectionConfig.default()
        original.crutch_words = CrutchWordsConfig(
            enabled=True,
            z_score_threshold=3.0,
            min_occurrences=10,
            check_adverbs=False,
            base_confidence=0.80,
        )
        d = original.to_dict()
        assert "crutch_words" in d

        restored = CorrectionConfig.from_dict(d)
        assert restored.crutch_words.z_score_threshold == 3.0
        assert restored.crutch_words.min_occurrences == 10
        assert restored.crutch_words.check_adverbs is False
        assert restored.crutch_words.base_confidence == 0.80

    def test_glossary_config_roundtrip(self):
        """GlossaryConfig se serializa y restaura (bug S18-00a)."""
        original = CorrectionConfig.default()
        original.glossary = GlossaryConfig(
            enabled=False,
            alert_on_variants=False,
            fuzzy_threshold=0.70,
        )
        d = original.to_dict()
        assert "glossary" in d

        restored = CorrectionConfig.from_dict(d)
        assert restored.glossary.enabled is False
        assert restored.glossary.alert_on_variants is False
        assert restored.glossary.fuzzy_threshold == 0.70

    def test_orthographic_variants_config_roundtrip(self):
        """OrthographicVariantsConfig se serializa y restaura (bug S18-00a)."""
        original = CorrectionConfig.default()
        original.orthographic_variants = OrthographicVariantsConfig(
            enabled=True,
            check_consonant_groups=False,
            check_bv_confusion=True,
            base_confidence=0.90,
        )
        d = original.to_dict()
        assert "orthographic_variants" in d

        restored = CorrectionConfig.from_dict(d)
        assert restored.orthographic_variants.enabled is True
        assert restored.orthographic_variants.check_consonant_groups is False
        assert restored.orthographic_variants.check_bv_confusion is True
        assert restored.orthographic_variants.base_confidence == 0.90

    def test_full_roundtrip_all_configs(self):
        """TODAS las configs sobreviven round-trip completo."""
        original = CorrectionConfig.default()
        d = original.to_dict()
        restored = CorrectionConfig.from_dict(d)

        # Verificar que todas las claves de primer nivel están presentes
        expected_keys = {
            "profile", "typography", "repetition", "agreement",
            "terminology", "regional", "field_dictionary",
            "clarity", "grammar", "crutch_words", "glossary",
            "orthographic_variants", "anacoluto", "pov", "style_register",
            "max_issues_per_category", "use_llm_review", "llm_review_model",
        }
        assert set(d.keys()) == expected_keys

        # Verificar round-trip de segundo nivel
        d2 = restored.to_dict()
        assert d == d2, f"Round-trip mismatch: {set(d.keys()) ^ set(d2.keys())}"

    def test_from_dict_empty_uses_defaults(self):
        """from_dict({}) usa valores por defecto sin crashear."""
        restored = CorrectionConfig.from_dict({})
        assert restored.clarity.enabled is True
        assert restored.grammar.enabled is True
        assert restored.crutch_words.enabled is True
        assert restored.glossary.enabled is True
        assert restored.orthographic_variants.enabled is True

    def test_factory_methods_roundtrip(self):
        """Configs de factory methods sobreviven round-trip."""
        for factory_name in ["for_novel", "for_technical", "for_legal",
                             "for_medical", "for_journalism", "for_selfhelp"]:
            factory = getattr(CorrectionConfig, factory_name)
            original = factory()
            d = original.to_dict()
            restored = CorrectionConfig.from_dict(d)
            d2 = restored.to_dict()
            assert d == d2, f"{factory_name} round-trip failed"
