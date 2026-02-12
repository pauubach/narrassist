"""Tests para el sistema de feature gating."""

import os
from unittest.mock import patch

import pytest

from narrative_assistant.licensing.gating import (
    apply_license_gating,
    check_manuscript_word_limit,
    get_allowed_features,
    is_feature_allowed,
    is_licensing_enabled,
)
from narrative_assistant.licensing.models import LicenseFeature, LicenseTier
from narrative_assistant.licensing.verification import ManuscriptTooLargeError
from narrative_assistant.pipelines.unified_analysis import UnifiedConfig


class TestIsLicensingEnabled:
    """Tests para is_licensing_enabled()."""

    def test_default_disabled(self):
        """Por defecto, licensing esta desactivado."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove NA_LICENSING_ENABLED if present
            os.environ.pop("NA_LICENSING_ENABLED", None)
            assert is_licensing_enabled() is False

    def test_explicitly_disabled(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "false"}):
            assert is_licensing_enabled() is False

    def test_enabled(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            assert is_licensing_enabled() is True

    def test_enabled_case_insensitive(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "TRUE"}):
            assert is_licensing_enabled() is True


class TestIsFeatureAllowed:
    """Tests para is_feature_allowed()."""

    def test_all_features_allowed_when_disabled(self):
        """Sin licensing, todas las features estan disponibles."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "false"}):
            for feature in LicenseFeature:
                assert is_feature_allowed(feature) is True

    def test_basic_features_allowed_for_corrector(self):
        """Tier CORRECTOR solo tiene features basicas."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            assert is_feature_allowed(LicenseFeature.GRAMMAR_SPELLING, LicenseTier.CORRECTOR) is True
            assert is_feature_allowed(LicenseFeature.NER_COREFERENCE, LicenseTier.CORRECTOR) is True
            assert is_feature_allowed(LicenseFeature.ATTRIBUTE_CONSISTENCY, LicenseTier.CORRECTOR) is True
            assert is_feature_allowed(LicenseFeature.NAME_VARIANTS, LicenseTier.CORRECTOR) is True

    def test_advanced_features_blocked_for_corrector(self):
        """Tier CORRECTOR no tiene features avanzadas."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            assert is_feature_allowed(LicenseFeature.CHARACTER_PROFILING, LicenseTier.CORRECTOR) is False
            assert is_feature_allowed(LicenseFeature.NETWORK_ANALYSIS, LicenseTier.CORRECTOR) is False
            assert is_feature_allowed(LicenseFeature.OOC_DETECTION, LicenseTier.CORRECTOR) is False
            assert is_feature_allowed(LicenseFeature.ANACHRONISM_DETECTION, LicenseTier.CORRECTOR) is False
            assert is_feature_allowed(LicenseFeature.CLASSICAL_SPANISH, LicenseTier.CORRECTOR) is False

    def test_profesional_features(self):
        """Tier PROFESIONAL tiene todas las features excepto EXPORT_IMPORT."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            for feature in LicenseFeature:
                if feature == LicenseFeature.EXPORT_IMPORT:
                    assert is_feature_allowed(feature, LicenseTier.PROFESIONAL) is False
                else:
                    assert is_feature_allowed(feature, LicenseTier.PROFESIONAL) is True

    def test_all_features_allowed_for_editorial(self):
        """Tier EDITORIAL tiene todas las features."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            for feature in LicenseFeature:
                assert is_feature_allowed(feature, LicenseTier.EDITORIAL) is True

    def test_no_tier_defaults_to_corrector(self):
        """Sin tier, se usa CORRECTOR (mas restrictivo)."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            assert is_feature_allowed(LicenseFeature.GRAMMAR_SPELLING) is True
            assert is_feature_allowed(LicenseFeature.OOC_DETECTION) is False


class TestGetAllowedFeatures:
    """Tests para get_allowed_features()."""

    def test_all_features_when_disabled(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "false"}):
            features = get_allowed_features()
            assert features == frozenset(LicenseFeature)

    def test_basic_features_for_corrector(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            features = get_allowed_features(LicenseTier.CORRECTOR)
            assert len(features) == 4
            assert LicenseFeature.GRAMMAR_SPELLING in features
            assert LicenseFeature.CHARACTER_PROFILING not in features

    def test_profesional_features_exclude_export(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            features = get_allowed_features(LicenseTier.PROFESIONAL)
            assert len(features) == 11
            assert LicenseFeature.EXPORT_IMPORT not in features


class TestApplyLicenseGating:
    """Tests para apply_license_gating()."""

    def test_no_changes_when_disabled(self):
        """Sin licensing, config no cambia."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "false"}):
            config = UnifiedConfig.standard()
            config.run_ooc_detection = True
            original_ooc = config.run_ooc_detection
            result = apply_license_gating(config)
            assert result.run_ooc_detection == original_ooc

    def test_corrector_disables_advanced_features(self):
        """CORRECTOR desactiva features avanzadas."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            config = UnifiedConfig.standard()
            config.run_ooc_detection = True
            config.run_character_profiling = True
            config.run_anachronism_detection = True
            config.run_classical_spanish = True

            result = apply_license_gating(config, LicenseTier.CORRECTOR)
            assert result.run_ooc_detection is False
            assert result.run_character_profiling is False
            assert result.run_anachronism_detection is False
            assert result.run_classical_spanish is False

    def test_corrector_keeps_basic_features(self):
        """CORRECTOR mantiene features basicas."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            config = UnifiedConfig.standard()
            result = apply_license_gating(config, LicenseTier.CORRECTOR)
            assert result.run_ner is True
            assert result.run_spelling is True
            assert result.run_grammar is True
            assert result.run_consistency is True

    def test_profesional_keeps_all_features(self):
        """PROFESIONAL mantiene todas las features."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            config = UnifiedConfig.standard()
            config.run_ooc_detection = True
            config.run_character_profiling = True

            result = apply_license_gating(config, LicenseTier.PROFESIONAL)
            assert result.run_ooc_detection is True
            assert result.run_character_profiling is True
            assert result.run_ner is True

    def test_gating_does_not_enable_disabled_features(self):
        """Gating solo desactiva, nunca activa features."""
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            config = UnifiedConfig.standard()
            config.run_ooc_detection = False  # Ya desactivado por config

            result = apply_license_gating(config, LicenseTier.PROFESIONAL)
            assert result.run_ooc_detection is False  # Sigue desactivado


class TestUnifiedConfigNewFlags:
    """Tests para los nuevos flags en UnifiedConfig."""

    def test_new_flags_default_true(self):
        config = UnifiedConfig()
        assert config.run_character_profiling is True
        assert config.run_network_analysis is True
        assert config.run_anachronism_detection is True
        assert config.run_ooc_detection is True
        assert config.run_classical_spanish is True
        assert config.run_name_variants is True
        assert config.run_multi_model_voting is True
        assert config.run_full_reports is True

    def test_express_profile_inherits_defaults(self):
        """Express profile tiene los nuevos flags por defecto (True)."""
        config = UnifiedConfig.express()
        assert config.run_character_profiling is True
        assert config.run_ooc_detection is True


class TestCheckManuscriptWordLimit:
    """Tests para check_manuscript_word_limit()."""

    def test_disabled_licensing_always_passes(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "false"}):
            result = check_manuscript_word_limit(999_999)
            assert result.is_success

    def test_corrector_under_limit(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(50_000, LicenseTier.CORRECTOR)
            assert result.is_success

    def test_corrector_at_limit(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(60_000, LicenseTier.CORRECTOR)
            assert result.is_success

    def test_corrector_over_limit(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(60_001, LicenseTier.CORRECTOR)
            assert result.is_failure
            assert isinstance(result.error, ManuscriptTooLargeError)
            assert result.error.word_count == 60_001
            assert result.error.max_words == 60_000

    def test_profesional_unlimited(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(500_000, LicenseTier.PROFESIONAL)
            assert result.is_success

    def test_editorial_unlimited(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(1_000_000, LicenseTier.EDITORIAL)
            assert result.is_success

    def test_no_tier_defaults_to_corrector(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(60_001)
            assert result.is_failure
            assert isinstance(result.error, ManuscriptTooLargeError)

    def test_error_message_format(self):
        with patch.dict(os.environ, {"NA_LICENSING_ENABLED": "true"}):
            result = check_manuscript_word_limit(75_000, LicenseTier.CORRECTOR)
            assert result.is_failure
            assert "75,000" in result.error.user_message
            assert "60,000" in result.error.user_message
            assert "Profesional" in result.error.user_message
