"""
Tests unitarios para el sistema de licencias - modelos de datos.

Cubre:
- words_to_pages: conversion palabras a paginas
- LicenseTier: enums, display_name
- LicenseFeature: enums, display_name
- TIER_FEATURES: mapping tier -> features
- TierLimits: for_tier, is_unlimited
- UsageRecord: post_init page calc, billing periods
- License: features, has_feature, grace period, serialization
- Device: cooldown, serialization
- Subscription: is_active, days_until_renewal
- Edge cases: boundary values, empty data, serialization round-trips
"""

import json
import math
from datetime import datetime, timedelta

import pytest

from narrative_assistant.licensing.models import (
    DEVICE_DEACTIVATION_COOLDOWN_HOURS,
    LICENSING_SCHEMA_SQL,
    OFFLINE_GRACE_PERIOD_DAYS,
    TIER_FEATURES,
    WORDS_PER_PAGE,
    Device,
    DeviceStatus,
    License,
    LicenseFeature,
    LicenseStatus,
    LicenseTier,
    Subscription,
    TierLimits,
    UsageRecord,
    words_to_pages,
)

# =============================================================================
# words_to_pages
# =============================================================================


class TestWordsToPages:
    """Tests para la conversion de palabras a paginas."""

    def test_zero_words(self):
        assert words_to_pages(0) == 0

    def test_negative_words(self):
        assert words_to_pages(-100) == 0

    def test_exactly_one_page(self):
        assert words_to_pages(250) == 1

    def test_one_word_rounds_up(self):
        assert words_to_pages(1) == 1

    def test_251_words_rounds_up(self):
        assert words_to_pages(251) == 2

    def test_500_words_exact(self):
        assert words_to_pages(500) == 2

    def test_large_document(self):
        """80000 palabras ~= novela completa."""
        assert words_to_pages(80000) == 320

    def test_boundary_249(self):
        assert words_to_pages(249) == 1

    def test_boundary_250(self):
        assert words_to_pages(250) == 1

    def test_words_per_page_constant(self):
        assert WORDS_PER_PAGE == 250


# =============================================================================
# LicenseTier
# =============================================================================


class TestLicenseTier:
    """Tests para los niveles de suscripcion."""

    def test_corrector_value(self):
        assert LicenseTier.CORRECTOR.value == "corrector"

    def test_profesional_value(self):
        assert LicenseTier.PROFESIONAL.value == "profesional"

    def test_editorial_value(self):
        assert LicenseTier.EDITORIAL.value == "editorial"

    def test_display_names(self):
        assert LicenseTier.CORRECTOR.display_name == "Corrector"
        assert LicenseTier.PROFESIONAL.display_name == "Profesional"
        assert LicenseTier.EDITORIAL.display_name == "Editorial"

    def test_from_string(self):
        assert LicenseTier("corrector") == LicenseTier.CORRECTOR
        assert LicenseTier("profesional") == LicenseTier.PROFESIONAL
        assert LicenseTier("editorial") == LicenseTier.EDITORIAL

    def test_invalid_tier_raises(self):
        with pytest.raises(ValueError):
            LicenseTier("freelance")

    def test_old_tiers_do_not_exist(self):
        """Los tiers antiguos no existen."""
        with pytest.raises(ValueError):
            LicenseTier("agencia")

    def test_three_tiers_total(self):
        assert len(LicenseTier) == 3


# =============================================================================
# LicenseFeature
# =============================================================================


class TestLicenseFeature:
    """Tests para las features de funcionalidad."""

    def test_twelve_features_total(self):
        assert len(LicenseFeature) == 12

    def test_basic_features_exist(self):
        assert LicenseFeature.ATTRIBUTE_CONSISTENCY.value == "attribute_consistency"
        assert LicenseFeature.GRAMMAR_SPELLING.value == "grammar_spelling"
        assert LicenseFeature.NER_COREFERENCE.value == "ner_coreference"
        assert LicenseFeature.NAME_VARIANTS.value == "name_variants"

    def test_advanced_features_exist(self):
        assert LicenseFeature.CHARACTER_PROFILING.value == "character_profiling"
        assert LicenseFeature.NETWORK_ANALYSIS.value == "network_analysis"
        assert LicenseFeature.ANACHRONISM_DETECTION.value == "anachronism_detection"
        assert LicenseFeature.OOC_DETECTION.value == "ooc_detection"
        assert LicenseFeature.CLASSICAL_SPANISH.value == "classical_spanish"
        assert LicenseFeature.MULTI_MODEL.value == "multi_model"
        assert LicenseFeature.FULL_REPORTS.value == "full_reports"

    def test_display_names_not_empty(self):
        for feature in LicenseFeature:
            assert feature.display_name, f"Feature {feature} has empty display_name"

    def test_from_string(self):
        assert (
            LicenseFeature("attribute_consistency")
            == LicenseFeature.ATTRIBUTE_CONSISTENCY
        )

    def test_invalid_feature_raises(self):
        with pytest.raises(ValueError):
            LicenseFeature("nonexistent_feature")

    def test_old_modules_do_not_exist(self):
        """Los modulos antiguos no existen como features."""
        with pytest.raises(ValueError):
            LicenseFeature("CORE")
        with pytest.raises(ValueError):
            LicenseFeature("NARRATIVA")


# =============================================================================
# TIER_FEATURES mapping
# =============================================================================


class TestTierFeatures:
    """Tests para el mapping tier -> features."""

    def test_corrector_has_4_basic_features(self):
        features = TIER_FEATURES[LicenseTier.CORRECTOR]
        assert len(features) == 4
        assert LicenseFeature.ATTRIBUTE_CONSISTENCY in features
        assert LicenseFeature.GRAMMAR_SPELLING in features
        assert LicenseFeature.NER_COREFERENCE in features
        assert LicenseFeature.NAME_VARIANTS in features

    def test_corrector_no_advanced_features(self):
        features = TIER_FEATURES[LicenseTier.CORRECTOR]
        assert LicenseFeature.CHARACTER_PROFILING not in features
        assert LicenseFeature.NETWORK_ANALYSIS not in features
        assert LicenseFeature.ANACHRONISM_DETECTION not in features
        assert LicenseFeature.MULTI_MODEL not in features
        assert LicenseFeature.FULL_REPORTS not in features

    def test_profesional_has_11_features(self):
        features = TIER_FEATURES[LicenseTier.PROFESIONAL]
        assert len(features) == 11
        assert LicenseFeature.EXPORT_IMPORT not in features

    def test_editorial_has_all_12_features(self):
        features = TIER_FEATURES[LicenseTier.EDITORIAL]
        assert len(features) == 12
        assert LicenseFeature.EXPORT_IMPORT in features

    def test_editorial_superset_of_profesional(self):
        pro = TIER_FEATURES[LicenseTier.PROFESIONAL]
        edit = TIER_FEATURES[LicenseTier.EDITORIAL]
        assert pro.issubset(edit)
        assert LicenseFeature.EXPORT_IMPORT in edit - pro

    def test_all_tiers_covered(self):
        for tier in LicenseTier:
            assert tier in TIER_FEATURES

    def test_features_are_frozenset(self):
        """No se pueden mutar."""
        for tier in LicenseTier:
            assert isinstance(TIER_FEATURES[tier], frozenset)


# =============================================================================
# TierLimits
# =============================================================================


class TestTierLimits:
    """Tests para los limites por tier."""

    def test_corrector_limits(self):
        limits = TierLimits.for_tier(LicenseTier.CORRECTOR)
        assert limits.max_pages_per_month == 1500
        assert limits.max_devices == 1
        assert limits.pages_rollover_months == 1
        assert not limits.is_unlimited

    def test_profesional_limits(self):
        limits = TierLimits.for_tier(LicenseTier.PROFESIONAL)
        assert limits.max_pages_per_month == 3000
        assert limits.max_devices == 1
        assert limits.max_words_per_manuscript == -1
        assert limits.pages_rollover_months == 1
        assert not limits.is_unlimited

    def test_editorial_limits(self):
        limits = TierLimits.for_tier(LicenseTier.EDITORIAL)
        assert limits.max_pages_per_month == -1
        assert limits.max_devices == 3
        assert limits.max_words_per_manuscript == -1
        assert limits.pages_rollover_months == 0
        assert limits.is_unlimited

    def test_corrector_manuscript_word_limit(self):
        limits = TierLimits.for_tier(LicenseTier.CORRECTOR)
        assert limits.max_words_per_manuscript == 60_000

    def test_frozen_immutable(self):
        limits = TierLimits.for_tier(LicenseTier.CORRECTOR)
        with pytest.raises(AttributeError):
            limits.max_pages_per_month = 9999


# =============================================================================
# UsageRecord
# =============================================================================


class TestUsageRecord:
    """Tests para registros de uso."""

    def test_post_init_calculates_page_count(self):
        record = UsageRecord(word_count=500)
        assert record.page_count == 2

    def test_post_init_zero_words(self):
        record = UsageRecord(word_count=0)
        assert record.page_count == 0

    def test_post_init_does_not_override_explicit(self):
        record = UsageRecord(word_count=500, page_count=10)
        assert record.page_count == 10

    def test_current_billing_period_format(self):
        period = UsageRecord.current_billing_period()
        assert len(period) == 7  # YYYY-MM
        assert period[4] == "-"
        year, month = period.split("-")
        assert 2020 <= int(year) <= 2030
        assert 1 <= int(month) <= 12

    def test_previous_billing_period_january(self):
        """En enero, el mes anterior es diciembre del ano anterior."""
        import unittest.mock

        with unittest.mock.patch(
            "narrative_assistant.licensing.models.datetime"
        ) as mock_dt:
            mock_dt.utcnow.return_value = datetime(2025, 1, 15)
            period = UsageRecord.previous_billing_period()
            assert period == "2024-12"

    def test_previous_billing_period_regular(self):
        import unittest.mock

        with unittest.mock.patch(
            "narrative_assistant.licensing.models.datetime"
        ) as mock_dt:
            mock_dt.utcnow.return_value = datetime(2025, 6, 15)
            period = UsageRecord.previous_billing_period()
            assert period == "2025-05"

    def test_serialization_roundtrip(self):
        now = datetime.utcnow()
        record = UsageRecord(
            id=1,
            license_id=42,
            project_id=7,
            document_fingerprint="abc123",
            document_name="test.docx",
            word_count=1000,
            page_count=4,
            analysis_started_at=now,
            billing_period="2025-06",
            counted_for_quota=True,
        )
        data = record.to_dict()
        restored = UsageRecord.from_dict(data)
        assert restored.word_count == 1000
        assert restored.page_count == 4
        assert restored.document_fingerprint == "abc123"
        assert restored.counted_for_quota is True


# =============================================================================
# License
# =============================================================================


class TestLicense:
    """Tests para la licencia."""

    def test_default_tier_is_corrector(self):
        lic = License()
        assert lic.tier == LicenseTier.CORRECTOR

    def test_features_by_tier(self):
        lic = License(tier=LicenseTier.CORRECTOR)
        assert len(lic.features) == 4
        lic.tier = LicenseTier.PROFESIONAL
        assert len(lic.features) == 11

    def test_has_feature_corrector(self):
        lic = License(tier=LicenseTier.CORRECTOR)
        assert lic.has_feature(LicenseFeature.GRAMMAR_SPELLING)
        assert not lic.has_feature(LicenseFeature.CHARACTER_PROFILING)

    def test_has_feature_profesional(self):
        lic = License(tier=LicenseTier.PROFESIONAL)
        assert lic.has_feature(LicenseFeature.GRAMMAR_SPELLING)
        assert lic.has_feature(LicenseFeature.CHARACTER_PROFILING)

    def test_limits_property(self):
        lic = License(tier=LicenseTier.EDITORIAL)
        assert lic.limits.is_unlimited

    def test_is_valid_active(self):
        lic = License(status=LicenseStatus.ACTIVE)
        assert lic.is_valid

    def test_is_valid_grace_period(self):
        lic = License(status=LicenseStatus.GRACE_PERIOD)
        assert lic.is_valid

    def test_not_valid_expired(self):
        lic = License(status=LicenseStatus.EXPIRED)
        assert not lic.is_valid

    def test_not_valid_suspended(self):
        lic = License(status=LicenseStatus.SUSPENDED)
        assert not lic.is_valid

    def test_grace_period_lifecycle(self):
        lic = License(status=LicenseStatus.ACTIVE)
        lic.start_grace_period()
        assert lic.status == LicenseStatus.GRACE_PERIOD
        assert lic.grace_period_ends_at is not None
        assert lic.grace_period_remaining.days >= 13  # ~14 days minus microseconds

        lic.end_grace_period()
        assert lic.status == LicenseStatus.ACTIVE
        assert lic.grace_period_ends_at is None

    def test_expire_grace_period(self):
        lic = License(status=LicenseStatus.ACTIVE)
        lic.start_grace_period()
        lic.expire_grace_period()
        assert lic.status == LicenseStatus.EXPIRED

    def test_start_grace_only_from_active(self):
        """Grace period solo se inicia desde estado ACTIVE."""
        lic = License(status=LicenseStatus.EXPIRED)
        lic.start_grace_period()
        assert lic.status == LicenseStatus.EXPIRED  # Sin cambio

    def test_active_devices_count(self):
        lic = License()
        lic.devices = [
            Device(status=DeviceStatus.ACTIVE),
            Device(status=DeviceStatus.INACTIVE),
            Device(status=DeviceStatus.ACTIVE),
        ]
        assert lic.active_device_count == 2
        assert len(lic.active_devices) == 2

    def test_can_add_device_corrector(self):
        lic = License(tier=LicenseTier.CORRECTOR)
        assert lic.can_add_device()  # 0 active < 1 max
        lic.devices = [Device(status=DeviceStatus.ACTIVE)]
        assert not lic.can_add_device()  # 1 active == 1 max

    def test_can_add_device_profesional(self):
        lic = License(tier=LicenseTier.PROFESIONAL)
        assert lic.can_add_device()  # 0 active < 1 max
        lic.devices = [Device(status=DeviceStatus.ACTIVE)]
        assert not lic.can_add_device()  # 1 active == 1 max

    def test_serialization_roundtrip(self):
        lic = License(
            id=1,
            license_key="TEST-KEY",
            user_email="test@example.com",
            tier=LicenseTier.PROFESIONAL,
            status=LicenseStatus.ACTIVE,
            created_at=datetime(2025, 1, 1),
            extra_data={"foo": "bar"},
        )
        lic.subscription = Subscription(
            tier=LicenseTier.PROFESIONAL,
            status="active",
        )
        lic.devices = [
            Device(
                hardware_fingerprint="abc123",
                device_name="Test PC",
                status=DeviceStatus.ACTIVE,
            )
        ]

        data = lic.to_dict()
        restored = License.from_dict(data)

        assert restored.license_key == "TEST-KEY"
        assert restored.tier == LicenseTier.PROFESIONAL
        assert restored.extra_data == {"foo": "bar"}
        assert restored.subscription is not None
        assert restored.subscription.tier == LicenseTier.PROFESIONAL
        assert len(restored.devices) == 1
        assert restored.devices[0].device_name == "Test PC"

    def test_serialization_with_none_subscription(self):
        lic = License()
        data = lic.to_dict()
        restored = License.from_dict(data)
        assert restored.subscription is None

    def test_from_dict_defaults(self):
        """Minimal dict should use defaults."""
        lic = License.from_dict({})
        assert lic.tier == LicenseTier.CORRECTOR
        assert lic.status == LicenseStatus.ACTIVE
        assert lic.license_key == ""


# =============================================================================
# Device
# =============================================================================


class TestDevice:
    """Tests para dispositivos."""

    def test_cooldown_not_active(self):
        device = Device()
        assert not device.is_in_cooldown
        assert device.cooldown_remaining is None

    def test_cooldown_active(self):
        device = Device(cooldown_ends_at=datetime.utcnow() + timedelta(hours=24))
        assert device.is_in_cooldown
        remaining = device.cooldown_remaining
        assert remaining is not None
        assert remaining.total_seconds() > 0

    def test_cooldown_expired(self):
        device = Device(cooldown_ends_at=datetime.utcnow() - timedelta(hours=1))
        assert not device.is_in_cooldown
        assert device.cooldown_remaining is None

    def test_serialization_roundtrip(self):
        now = datetime.utcnow()
        device = Device(
            id=1,
            license_id=42,
            hardware_fingerprint="abc123def456",
            device_name="Test Laptop",
            os_info="Windows 11",
            status=DeviceStatus.ACTIVE,
            activated_at=now,
            last_seen_at=now,
            is_current_device=True,
        )
        data = device.to_dict()
        restored = Device.from_dict(data)
        assert restored.hardware_fingerprint == "abc123def456"
        assert restored.device_name == "Test Laptop"
        assert restored.status == DeviceStatus.ACTIVE
        assert restored.is_current_device is True

    def test_from_dict_defaults(self):
        device = Device.from_dict({})
        assert device.hardware_fingerprint == ""
        assert device.status == DeviceStatus.PENDING


# =============================================================================
# Subscription
# =============================================================================


class TestSubscription:
    """Tests para suscripciones."""

    def test_is_active_true(self):
        sub = Subscription(status="active")
        assert sub.is_active

    def test_is_active_trialing(self):
        sub = Subscription(status="trialing")
        assert sub.is_active

    def test_is_active_false(self):
        sub = Subscription(status="past_due")
        assert not sub.is_active
        sub2 = Subscription(status="canceled")
        assert not sub2.is_active

    def test_days_until_renewal(self):
        sub = Subscription(current_period_end=datetime.utcnow() + timedelta(days=10))
        days = sub.days_until_renewal
        assert days is not None
        assert 9 <= days <= 10

    def test_days_until_renewal_expired(self):
        sub = Subscription(current_period_end=datetime.utcnow() - timedelta(days=5))
        assert sub.days_until_renewal == 0

    def test_days_until_renewal_none(self):
        sub = Subscription()
        assert sub.days_until_renewal is None

    def test_default_tier_corrector(self):
        sub = Subscription()
        assert sub.tier == LicenseTier.CORRECTOR

    def test_serialization_roundtrip(self):
        now = datetime.utcnow()
        sub = Subscription(
            id=1,
            license_id=42,
            stripe_subscription_id="sub_123",
            stripe_customer_id="cus_456",
            tier=LicenseTier.PROFESIONAL,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        data = sub.to_dict()
        restored = Subscription.from_dict(data)
        assert restored.tier == LicenseTier.PROFESIONAL
        assert restored.stripe_subscription_id == "sub_123"
        assert restored.is_active


# =============================================================================
# Constants
# =============================================================================


class TestConstants:
    """Tests para constantes del sistema de licencias."""

    def test_offline_grace_period(self):
        assert OFFLINE_GRACE_PERIOD_DAYS == 14

    def test_device_cooldown_hours(self):
        assert DEVICE_DEACTIVATION_COOLDOWN_HOURS == 168  # 7 dias

    def test_words_per_page(self):
        assert WORDS_PER_PAGE == 250


# =============================================================================
# SQL Schema
# =============================================================================


class TestLicensingSchema:
    """Tests para el schema SQL."""

    def test_schema_contains_all_tables(self):
        assert "CREATE TABLE IF NOT EXISTS licenses" in LICENSING_SCHEMA_SQL
        assert "CREATE TABLE IF NOT EXISTS subscriptions" in LICENSING_SCHEMA_SQL
        assert "CREATE TABLE IF NOT EXISTS devices" in LICENSING_SCHEMA_SQL
        assert "CREATE TABLE IF NOT EXISTS usage_records" in LICENSING_SCHEMA_SQL
        assert (
            "CREATE TABLE IF NOT EXISTS license_verification_cache"
            in LICENSING_SCHEMA_SQL
        )

    def test_schema_has_page_count_column(self):
        assert "page_count" in LICENSING_SCHEMA_SQL

    def test_schema_defaults_corrector(self):
        """Default tier should be 'corrector', not 'freelance'."""
        assert "'corrector'" in LICENSING_SCHEMA_SQL
        assert "'freelance'" not in LICENSING_SCHEMA_SQL

    def test_schema_no_bundle_column(self):
        """El campo bundle fue eliminado."""
        # bundle no debe aparecer como nombre de columna (puede aparecer en texto)
        lines = LICENSING_SCHEMA_SQL.split("\n")
        for line in lines:
            # Solo buscar en definiciones de columnas (sin comments)
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("--")
                and not stripped.startswith("CREATE")
            ):
                assert "bundle " not in stripped.lower() or "FOREIGN" in stripped
