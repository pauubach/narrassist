"""
Tests unitarios para el sistema de verificacion de licencias.

Cubre:
- LicenseVerifier: verify, check_quota, check_feature, record_usage
- Cuota de paginas con rollover
- Feature gating por tier
- Gestion de dispositivos: registro, cooldown, limites
- Modo offline con periodo de gracia
- Errores: TierFeatureError, QuotaExceededError, DeviceLimitError, etc.
- Edge cases: re-analisis gratuito, boundary values, rollover enero
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.core.result import Result
from narrative_assistant.licensing.models import (
    TIER_FEATURES,
    Device,
    DeviceStatus,
    License,
    LicenseFeature,
    LicenseStatus,
    LicenseTier,
    Subscription,
    TierLimits,
    UsageRecord,
    initialize_licensing_schema,
    words_to_pages,
)
from narrative_assistant.licensing.verification import (
    DeviceCooldownError,
    DeviceLimitError,
    LicenseExpiredError,
    LicenseNotFoundError,
    LicenseOfflineError,
    LicenseVerifier,
    QuotaExceededError,
    TierFeatureError,
    VerificationResult,
    get_cached_license,
)

# =============================================================================
# Fixtures: in-memory SQLite DB
# =============================================================================


class FakeDatabase:
    """Mock ligero de la clase Database para tests."""

    def __init__(self):
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

    def connection(self):
        """Context manager for connection."""
        return _FakeConnectionCtx(self._conn)

    def transaction(self):
        """Context manager for transaction (auto-commit)."""
        return _FakeTransactionCtx(self._conn)

    def fetchone(self, query, params=()):
        cursor = self._conn.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        cursor = self._conn.execute(query, params)
        return cursor.fetchall()

    def execute(self, query, params=()):
        self._conn.execute(query, params)
        self._conn.commit()

    def close(self):
        self._conn.close()


class _FakeConnectionCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *args):
        pass


class _FakeTransactionCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, *args):
        if exc_type is None:
            self._conn.commit()


@pytest.fixture
def db():
    """Base de datos in-memory con schema de licencias."""
    database = FakeDatabase()
    # Initialize schema
    database._conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL UNIQUE,
            user_email TEXT NOT NULL,
            user_name TEXT,
            tier TEXT NOT NULL DEFAULT 'corrector',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            activated_at TEXT,
            expires_at TEXT,
            last_verified_at TEXT,
            grace_period_ends_at TEXT,
            extra_data TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL UNIQUE,
            stripe_subscription_id TEXT NOT NULL,
            stripe_customer_id TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'corrector',
            status TEXT NOT NULL DEFAULT 'active',
            current_period_start TEXT,
            current_period_end TEXT,
            cancel_at_period_end INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT,
            FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL,
            hardware_fingerprint TEXT NOT NULL,
            device_name TEXT,
            os_info TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            activated_at TEXT,
            deactivated_at TEXT,
            cooldown_ends_at TEXT,
            last_seen_at TEXT,
            is_current_device INTEGER DEFAULT 0,
            FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
            UNIQUE (license_id, hardware_fingerprint)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            is_demo INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL,
            project_id INTEGER,
            document_fingerprint TEXT NOT NULL,
            document_name TEXT,
            word_count INTEGER DEFAULT 0,
            page_count INTEGER DEFAULT 0,
            analysis_started_at TEXT NOT NULL DEFAULT (datetime('now')),
            analysis_completed_at TEXT,
            billing_period TEXT NOT NULL,
            counted_for_quota INTEGER DEFAULT 1,
            FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS license_verification_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL UNIQUE,
            cached_response TEXT NOT NULL,
            cached_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS device_swaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL,
            device_id INTEGER NOT NULL,
            swapped_at TEXT NOT NULL DEFAULT (datetime('now')),
            billing_period TEXT NOT NULL,
            FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_device_swaps_license_period
            ON device_swaps(license_id, billing_period);
        """
    )
    yield database
    database.close()


@pytest.fixture
def verifier(db):
    """LicenseVerifier con DB in-memory."""
    v = LicenseVerifier(db=db)
    return v


def _insert_license(db, tier="corrector", status="active", license_key="TEST-KEY-001"):
    """Helper: inserta una licencia y retorna su ID."""
    now = datetime.utcnow().isoformat()
    cursor = db._conn.execute(
        """
        INSERT INTO licenses (license_key, user_email, user_name, tier, status, created_at, activated_at, last_verified_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (license_key, "test@example.com", "Test User", tier, status, now, now, now),
    )
    db._conn.commit()
    return cursor.lastrowid


def _insert_device(db, license_id, fingerprint="test-fp-001", status="active"):
    """Helper: inserta un dispositivo."""
    now = datetime.utcnow().isoformat()
    cursor = db._conn.execute(
        """
        INSERT INTO devices (license_id, hardware_fingerprint, device_name, os_info, status, activated_at, last_seen_at, is_current_device)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (license_id, fingerprint, "Test PC", "Windows 11", status, now, now, 1),
    )
    db._conn.commit()
    return cursor.lastrowid


def _insert_usage(db, license_id, fingerprint="doc-fp-001", word_count=1000, billing_period=None, counted=1):
    """Helper: inserta un registro de uso."""
    if billing_period is None:
        billing_period = UsageRecord.current_billing_period()
    page_count = words_to_pages(word_count)
    db._conn.execute(
        """
        INSERT INTO usage_records (license_id, project_id, document_fingerprint, document_name, word_count, page_count, billing_period, counted_for_quota)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (license_id, 1, fingerprint, "test.docx", word_count, page_count, billing_period, counted),
    )
    db._conn.commit()


# =============================================================================
# VerificationResult
# =============================================================================


class TestVerificationResult:
    """Tests para VerificationResult."""

    def test_can_analyze_valid_with_quota(self):
        vr = VerificationResult(
            is_valid=True,
            license=None,
            status=LicenseStatus.ACTIVE,
            message="OK",
            quota_remaining=100,
        )
        assert vr.can_analyze

    def test_can_analyze_unlimited(self):
        vr = VerificationResult(
            is_valid=True,
            license=None,
            status=LicenseStatus.ACTIVE,
            message="OK",
            quota_remaining=None,
        )
        assert vr.can_analyze

    def test_cannot_analyze_no_quota(self):
        vr = VerificationResult(
            is_valid=True,
            license=None,
            status=LicenseStatus.ACTIVE,
            message="OK",
            quota_remaining=0,
        )
        assert not vr.can_analyze

    def test_cannot_analyze_invalid(self):
        vr = VerificationResult(
            is_valid=False,
            license=None,
            status=LicenseStatus.EXPIRED,
            message="Expired",
            quota_remaining=100,
        )
        assert not vr.can_analyze

    def test_cannot_analyze_negative_quota(self):
        vr = VerificationResult(
            is_valid=True,
            license=None,
            status=LicenseStatus.ACTIVE,
            message="OK",
            quota_remaining=-5,
        )
        assert not vr.can_analyze


# =============================================================================
# Feature Gating
# =============================================================================


class TestCheckFeature:
    """Tests para verificacion de features por tier."""

    def test_corrector_basic_feature_allowed(self, verifier, db):
        lid = _insert_license(db, tier="corrector")
        _insert_device(db, lid)

        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        result = verifier.check_feature(LicenseFeature.GRAMMAR_SPELLING, lic)
        assert result.is_success
        assert result.value is True

    def test_corrector_advanced_feature_denied(self, verifier, db):
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        result = verifier.check_feature(LicenseFeature.CHARACTER_PROFILING, lic)
        assert result.is_failure
        assert isinstance(result.error, TierFeatureError)
        assert result.error.feature == LicenseFeature.CHARACTER_PROFILING

    def test_profesional_features_allowed(self, verifier, db):
        lid = _insert_license(db, tier="profesional")
        lic = License(id=lid, tier=LicenseTier.PROFESIONAL, status=LicenseStatus.ACTIVE)
        for feature in LicenseFeature:
            result = verifier.check_feature(feature, lic)
            if feature == LicenseFeature.EXPORT_IMPORT:
                assert result.is_failure, "EXPORT_IMPORT should be Editorial-only"
            else:
                assert result.is_success, f"Feature {feature} should be allowed for Profesional"

    def test_editorial_all_features_allowed(self, verifier, db):
        lid = _insert_license(db, tier="editorial")
        lic = License(id=lid, tier=LicenseTier.EDITORIAL, status=LicenseStatus.ACTIVE)
        for feature in LicenseFeature:
            result = verifier.check_feature(feature, lic)
            assert result.is_success

    def test_check_feature_no_license_fails(self, verifier):
        """check_feature sin licencia cacheada falla."""
        # Reset global cache
        import narrative_assistant.licensing.verification as v
        with v._license_lock:
            v._cached_license = None

        result = verifier.check_feature(LicenseFeature.GRAMMAR_SPELLING)
        assert result.is_failure
        assert isinstance(result.error, LicenseNotFoundError)

    def test_tier_feature_error_message(self):
        err = TierFeatureError(
            feature=LicenseFeature.CHARACTER_PROFILING,
            required_tier="Profesional",
        )
        assert "Profesional" in err.user_message
        assert "Character profiling" in err.user_message


# =============================================================================
# Quota (Pages + Rollover)
# =============================================================================


class TestQuota:
    """Tests para cuota de paginas con rollover."""

    def test_fresh_corrector_full_quota_with_rollover(self, verifier, db):
        """Sin uso previo en ambos meses, cuota = base + rollover (1500 + 1500 = 3000)."""
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 3000  # 1500 base + 1500 rollover

    def test_corrector_no_rollover_when_prev_full(self, verifier, db):
        """Si el mes anterior se uso toda la cuota, no hay rollover."""
        lid = _insert_license(db, tier="corrector")
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_doc", word_count=375000, billing_period=prev_period)  # 1500 pages
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 1500  # Solo base, 0 rollover

    def test_editorial_unlimited(self, verifier, db):
        """Editorial = ilimitado → None."""
        lid = _insert_license(db, tier="editorial")
        lic = License(id=lid, tier=LicenseTier.EDITORIAL, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining is None

    def test_usage_deducts_pages(self, verifier, db):
        """500 palabras = 2 paginas usadas, con rollover del mes anterior."""
        lid = _insert_license(db, tier="corrector")
        # Fill previous month so no rollover
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)
        # Current month: 2 pages used
        _insert_usage(db, lid, word_count=500)  # 2 pages
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 1498  # 1500 base - 2 used, 0 rollover

    def test_quota_exhausted(self, verifier, db):
        """Cuota agotada (incluyendo rollover) → 0."""
        lid = _insert_license(db, tier="corrector")
        # Fill previous month too (no rollover)
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)  # 1500 pages
        # Current month: use all 1500
        _insert_usage(db, lid, fingerprint="doc1", word_count=375000)  # 1500 pages
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 0

    def test_quota_over_limit_returns_zero(self, verifier, db):
        """Mas paginas usadas que el limite total (base + rollover) → 0 (no negativo)."""
        lid = _insert_license(db, tier="corrector")
        # Fill previous month (no rollover)
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)
        # Current month: exceed limit
        _insert_usage(db, lid, fingerprint="doc1", word_count=400000)  # 1600 pages > 1500
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 0

    def test_rollover_from_previous_month(self, verifier, db):
        """Rollover: mes anterior no se uso nada → +1500 este mes."""
        lid = _insert_license(db, tier="corrector")
        # No usage in previous month → 1500 rollover
        # Current: 0 used, limit 1500 + 1500 rollover = 3000 total
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        # 1500 (base) + 1500 (rollover from empty prev month) = 3000
        assert remaining == 3000

    def test_rollover_partial_previous_usage(self, verifier, db):
        """Rollover parcial: mes anterior uso 500 paginas → +1000."""
        lid = _insert_license(db, tier="corrector")
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_doc", word_count=125000, billing_period=prev_period)  # 500 pages
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        # 1500 (base) + 1000 (rollover from 500 used of 1500) = 2500
        assert remaining == 2500

    def test_rollover_fully_used_previous(self, verifier, db):
        """Si el mes anterior se uso todo → 0 rollover."""
        lid = _insert_license(db, tier="corrector")
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_doc", word_count=375000, billing_period=prev_period)  # 1500 pages
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 1500  # No rollover

    def test_editorial_no_rollover(self, verifier, db):
        """Editorial no tiene rollover (ilimitado)."""
        lid = _insert_license(db, tier="editorial")
        lic = License(id=lid, tier=LicenseTier.EDITORIAL, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining is None

    def test_check_quota_success(self, verifier, db):
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        result = verifier.check_quota(lic)
        assert result.is_success
        assert result.value > 0

    def test_check_quota_unlimited(self, verifier, db):
        lid = _insert_license(db, tier="editorial")
        lic = License(id=lid, tier=LicenseTier.EDITORIAL, status=LicenseStatus.ACTIVE)
        result = verifier.check_quota(lic)
        assert result.is_success
        assert result.value == -1

    def test_check_quota_exceeded(self, verifier, db):
        lid = _insert_license(db, tier="corrector")
        # Usar toda la cuota + rollover
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)  # 1500 = no rollover
        _insert_usage(db, lid, fingerprint="cur_full", word_count=375000)  # 1500 = full
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        result = verifier.check_quota(lic)
        assert result.is_failure
        assert isinstance(result.error, QuotaExceededError)


# =============================================================================
# Record Usage
# =============================================================================


class TestRecordUsage:
    """Tests para registro de uso de manuscritos."""

    def test_record_new_usage(self, verifier, db):
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)

        # Cache the license
        import narrative_assistant.licensing.verification as v
        with v._license_lock:
            v._cached_license = lic

        result = verifier.record_usage(
            project_id=1,
            document_fingerprint="doc-abc123",
            document_name="novela.docx",
            word_count=25000,
        )
        assert result.is_success
        record = result.value
        assert record.word_count == 25000
        assert record.page_count == 100  # 25000/250 = 100
        assert record.counted_for_quota is True

    def test_reanalysis_free(self, verifier, db):
        """Re-analisis del mismo documento en el mismo periodo = gratis."""
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)

        import narrative_assistant.licensing.verification as v
        with v._license_lock:
            v._cached_license = lic

        # First analysis
        result1 = verifier.record_usage(
            project_id=1,
            document_fingerprint="doc-same",
            document_name="test.docx",
            word_count=5000,
        )
        assert result1.is_success
        assert result1.value.counted_for_quota is True

        # Re-analysis of same doc
        result2 = verifier.record_usage(
            project_id=1,
            document_fingerprint="doc-same",
            document_name="test.docx",
            word_count=5000,
        )
        assert result2.is_success
        assert result2.value.counted_for_quota is False

    def test_record_usage_no_license(self, verifier):
        """Sin licencia cacheada → fallo."""
        import narrative_assistant.licensing.verification as v
        with v._license_lock:
            v._cached_license = None

        result = verifier.record_usage(
            project_id=1,
            document_fingerprint="doc-xyz",
            document_name="test.docx",
            word_count=1000,
        )
        assert result.is_failure
        assert isinstance(result.error, LicenseNotFoundError)

    def test_different_docs_both_counted(self, verifier, db):
        """Documentos diferentes ambos cuentan contra cuota."""
        lid = _insert_license(db, tier="corrector")
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)

        import narrative_assistant.licensing.verification as v
        with v._license_lock:
            v._cached_license = lic

        r1 = verifier.record_usage(1, "doc-a", "a.docx", 1000)
        r2 = verifier.record_usage(2, "doc-b", "b.docx", 2000)
        assert r1.is_success and r1.value.counted_for_quota is True
        assert r2.is_success and r2.value.counted_for_quota is True


# =============================================================================
# Error Classes
# =============================================================================


class TestLicenseErrors:
    """Tests para las clases de error de licencias."""

    def test_license_not_found_error(self):
        err = LicenseNotFoundError()
        assert "No se encontro" in err.user_message

    def test_license_expired_error(self):
        err = LicenseExpiredError(expired_at=datetime(2025, 1, 1))
        assert "expirado" in err.user_message

    def test_license_offline_error_with_grace(self):
        err = LicenseOfflineError(grace_remaining=timedelta(days=10))
        assert "10 dias" in err.user_message

    def test_license_offline_error_no_grace(self):
        err = LicenseOfflineError()
        assert "sin conexion" in err.user_message.lower() or "No se puede" in err.user_message

    def test_device_limit_error(self):
        err = DeviceLimitError(current_devices=2, max_devices=2)
        assert "2 dispositivo" in err.user_message

    def test_device_cooldown_error(self):
        ends = datetime.utcnow() + timedelta(hours=24)
        err = DeviceCooldownError(cooldown_ends=ends)
        assert "horas" in err.user_message

    def test_quota_exceeded_error(self):
        err = QuotaExceededError(current_usage=1500, max_usage=1500, billing_period="2025-06")
        assert "1500 paginas" in err.user_message

    def test_tier_feature_error(self):
        err = TierFeatureError(
            feature=LicenseFeature.MULTI_MODEL,
            required_tier="Profesional",
        )
        assert "Profesional" in err.user_message
        assert "multi-modelo" in err.user_message.lower() or "Multi" in err.user_message


# =============================================================================
# Offline / Grace Period
# =============================================================================


class TestOfflineMode:
    """Tests para modo offline y periodo de gracia."""

    def test_handle_offline_starts_grace(self, verifier):
        lic = License(status=LicenseStatus.ACTIVE)
        result = verifier._handle_offline_mode(lic)
        assert result.status == LicenseStatus.GRACE_PERIOD
        assert result.grace_period_ends_at is not None

    def test_handle_offline_grace_not_expired(self, verifier):
        lic = License(
            status=LicenseStatus.GRACE_PERIOD,
            grace_period_ends_at=datetime.utcnow() + timedelta(days=5),
        )
        result = verifier._handle_offline_mode(lic)
        assert result.status == LicenseStatus.GRACE_PERIOD

    def test_handle_offline_grace_expired(self, verifier):
        lic = License(
            status=LicenseStatus.GRACE_PERIOD,
            grace_period_ends_at=datetime.utcnow() - timedelta(hours=1),
        )
        result = verifier._handle_offline_mode(lic)
        assert result.status == LicenseStatus.EXPIRED

    def test_status_message_active(self, verifier):
        lic = License(status=LicenseStatus.ACTIVE)
        msg = verifier._get_status_message(lic)
        assert msg == "Licencia activa"

    def test_status_message_grace(self, verifier):
        lic = License(
            status=LicenseStatus.GRACE_PERIOD,
            grace_period_ends_at=datetime.utcnow() + timedelta(days=7),
        )
        msg = verifier._get_status_message(lic)
        assert "offline" in msg.lower() or "Modo" in msg


# =============================================================================
# Verify Flow (integration with in-memory DB)
# =============================================================================


class TestVerifyFlow:
    """Tests de integracion para el flujo de verificacion completo."""

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_active_license(self, mock_hw_info, mock_fp, verifier, db):
        """Verificar licencia activa con dispositivo registrado."""
        mock_fp.return_value = Result.success("test-fp-001")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="Test PC", os_info="Windows 11"))

        lid = _insert_license(db, tier="profesional")
        _insert_device(db, lid, fingerprint="test-fp-001")

        result = verifier.verify()
        assert result.is_success
        vr = result.value
        assert vr.is_valid
        assert vr.status == LicenseStatus.ACTIVE

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_no_license_fails(self, mock_hw_info, mock_fp, verifier, db):
        """Sin licencia en BD → fallo."""
        mock_fp.return_value = Result.success("test-fp-001")
        result = verifier.verify()
        assert result.is_failure
        assert isinstance(result.error, LicenseNotFoundError)

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_expired_license(self, mock_hw_info, mock_fp, verifier, db):
        """Licencia expirada → fallo."""
        mock_fp.return_value = Result.success("test-fp-001")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="Test", os_info="Test"))

        lid = _insert_license(db, tier="corrector", status="expired")
        _insert_device(db, lid, fingerprint="test-fp-001")

        result = verifier.verify()
        assert result.is_failure
        assert isinstance(result.error, LicenseExpiredError)

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_new_device_auto_register(self, mock_hw_info, mock_fp, verifier, db):
        """Dispositivo nuevo se registra automaticamente si hay hueco."""
        mock_fp.return_value = Result.success("new-device-fp")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="New PC", os_info="Win"))

        lid = _insert_license(db, tier="profesional")  # 2 max devices

        result = verifier.verify()
        assert result.is_success
        # Verify device was registered
        row = db.fetchone("SELECT * FROM devices WHERE hardware_fingerprint = ?", ("new-device-fp",))
        assert row is not None
        assert row["status"] == "active"

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_device_limit_reached(self, mock_hw_info, mock_fp, verifier, db):
        """Corrector (1 dispositivo max) con otro ya registrado → fallo."""
        mock_fp.return_value = Result.success("new-device-fp")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="New", os_info="Win"))

        lid = _insert_license(db, tier="corrector")  # 1 max device
        _insert_device(db, lid, fingerprint="existing-device-fp")

        result = verifier.verify()
        assert result.is_failure
        assert isinstance(result.error, DeviceLimitError)

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_device_in_cooldown(self, mock_hw_info, mock_fp, verifier, db):
        """Dispositivo en cooldown → fallo."""
        mock_fp.return_value = Result.success("cooldown-fp")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="Test", os_info="Win"))

        lid = _insert_license(db, tier="corrector")
        now = datetime.utcnow()
        cooldown_end = (now + timedelta(hours=24)).isoformat()
        db._conn.execute(
            """
            INSERT INTO devices (license_id, hardware_fingerprint, device_name, os_info, status, deactivated_at, cooldown_ends_at, is_current_device)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lid, "cooldown-fp", "Test", "Win", "inactive", now.isoformat(), cooldown_end, 0),
        )
        db._conn.commit()

        result = verifier.verify()
        assert result.is_failure
        assert isinstance(result.error, DeviceCooldownError)

    @patch("narrative_assistant.licensing.verification.get_hardware_fingerprint")
    @patch("narrative_assistant.licensing.verification.get_hardware_info")
    def test_verify_calculates_quota(self, mock_hw_info, mock_fp, verifier, db):
        """Verificar que quota_remaining se calcula correctamente."""
        mock_fp.return_value = Result.success("test-fp-001")
        mock_hw_info.return_value = Result.success(MagicMock(device_name="Test", os_info="Win"))

        lid = _insert_license(db, tier="corrector")
        _insert_device(db, lid, fingerprint="test-fp-001")
        _insert_usage(db, lid, word_count=25000)  # 100 pages

        # Also fill previous month to avoid rollover noise
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)

        result = verifier.verify()
        assert result.is_success
        # 1500 base + 0 rollover (prev month full) - 100 used = 1400
        assert result.value.quota_remaining == 1400


# =============================================================================
# Deactivate Device
# =============================================================================


class TestDeactivateDevice:
    """Tests para desactivar dispositivos."""

    def test_deactivate_device_success(self, verifier, db):
        lid = _insert_license(db, tier="profesional")
        did = _insert_device(db, lid, fingerprint="fp-to-deactivate")

        result = verifier.deactivate_device(did)
        assert result.is_success
        device = result.value
        assert device.status == DeviceStatus.INACTIVE
        # Primer swap del mes: sin cooldown (reactivacion inmediata)
        assert device.cooldown_ends_at is None

    def test_deactivate_device_not_found(self, verifier, db):
        result = verifier.deactivate_device(99999)
        assert result.is_failure

    def test_deactivate_sets_cooldown_7d_on_third_swap(self, verifier, db):
        """Cooldown 7d solo se aplica a partir del 3er swap del mes."""
        lid = _insert_license(db, tier="editorial")
        did1 = _insert_device(db, lid, fingerprint="fp-d1")
        did2 = _insert_device(db, lid, fingerprint="fp-d2")
        did3 = _insert_device(db, lid, fingerprint="fp-d3")

        # Primeros 2 swaps: sin cooldown
        verifier.deactivate_device(did1)
        verifier.deactivate_device(did2)

        # Tercer swap: cooldown 7 dias
        result = verifier.deactivate_device(did3)
        device = result.value
        assert device.cooldown_ends_at is not None
        expected = datetime.utcnow() + timedelta(hours=168)
        diff = abs((device.cooldown_ends_at - expected).total_seconds())
        assert diff < 5


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests de edge cases y boundary values."""

    def test_words_to_pages_exactly_250(self):
        assert words_to_pages(250) == 1

    def test_words_to_pages_exactly_500(self):
        assert words_to_pages(500) == 2

    def test_words_to_pages_one_word(self):
        assert words_to_pages(1) == 1

    def test_license_from_dict_old_tier_fails(self):
        """Intentar crear licencia con tier antiguo falla."""
        with pytest.raises(ValueError):
            License.from_dict({"tier": "freelance"})

    def test_usage_record_zero_word_count(self):
        record = UsageRecord(word_count=0)
        assert record.page_count == 0

    def test_usage_record_very_large_document(self):
        """Documento enorme: 1 millon de palabras."""
        record = UsageRecord(word_count=1_000_000)
        assert record.page_count == 4000

    def test_license_features_immutable(self):
        """Features set es frozenset, no se puede modificar."""
        lic = License(tier=LicenseTier.CORRECTOR)
        with pytest.raises(AttributeError):
            lic.features.add(LicenseFeature.MULTI_MODEL)

    def test_grace_period_remaining_zero_when_expired(self):
        """Grace period restante = 0 cuando ya expiro."""
        lic = License(
            status=LicenseStatus.GRACE_PERIOD,
            grace_period_ends_at=datetime.utcnow() - timedelta(days=1),
        )
        remaining = lic.grace_period_remaining
        assert remaining == timedelta(0)

    def test_grace_period_remaining_none_when_no_date(self):
        lic = License(status=LicenseStatus.ACTIVE)
        assert lic.grace_period_remaining is None

    def test_device_cooldown_remaining_none_when_not_in_cooldown(self):
        device = Device(status=DeviceStatus.ACTIVE)
        assert device.cooldown_remaining is None

    def test_subscription_from_dict_with_old_tier(self):
        """Intentar crear sub con tier antiguo falla."""
        with pytest.raises(ValueError):
            Subscription.from_dict({"tier": "agencia"})

    def test_multiple_usage_records_same_period(self, verifier, db):
        """Multiples documentos en el mismo periodo se suman correctamente."""
        lid = _insert_license(db, tier="corrector")
        # Fill prev month (no rollover)
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)
        # Current month: 200 + 300 + 500 = 1000 pages
        _insert_usage(db, lid, fingerprint="doc1", word_count=50000)   # 200 pages
        _insert_usage(db, lid, fingerprint="doc2", word_count=75000)   # 300 pages
        _insert_usage(db, lid, fingerprint="doc3", word_count=125000)  # 500 pages

        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        # 1500 base + 0 rollover - 1000 used = 500
        assert remaining == 500

    def test_profesional_quota_3000_with_rollover(self, verifier, db):
        """Profesional: 3000 base + 3000 rollover (no prev usage) = 6000."""
        lid = _insert_license(db, tier="profesional")
        lic = License(id=lid, tier=LicenseTier.PROFESIONAL, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 6000

    def test_profesional_quota_3000_no_rollover(self, verifier, db):
        """Profesional sin rollover: 3000 base."""
        lid = _insert_license(db, tier="profesional")
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=750000, billing_period=prev_period)  # 3000 pages
        lic = License(id=lid, tier=LicenseTier.PROFESIONAL, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        assert remaining == 3000

    def test_not_counted_for_quota_ignored(self, verifier, db):
        """Records con counted_for_quota=0 no se cuentan."""
        lid = _insert_license(db, tier="corrector")
        # Fill prev month
        prev_period = UsageRecord.previous_billing_period()
        _insert_usage(db, lid, fingerprint="prev_full", word_count=375000, billing_period=prev_period)
        # Current: 1500 pages but NOT counted (re-analysis)
        _insert_usage(db, lid, fingerprint="doc1", word_count=375000, counted=0)
        lic = License(id=lid, tier=LicenseTier.CORRECTOR, status=LicenseStatus.ACTIVE)
        remaining = verifier._calculate_quota_remaining(lic)
        # Should be full: 1500 base + 0 rollover = 1500 (uncounted records ignored)
        assert remaining == 1500


# =============================================================================
# Device Swap Counting (SP2-03)
# =============================================================================


class TestDeviceSwapCounting:
    """Tests para el conteo de swaps mensuales: 2 gratis, 3o+ con cooldown 7d."""

    def test_first_swap_no_cooldown(self, verifier, db):
        """Primer swap del mes: sin cooldown."""
        lid = _insert_license(db, tier="profesional")
        did = _insert_device(db, lid, fingerprint="fp-swap-1")

        result = verifier.deactivate_device(did)
        assert result.is_success
        assert result.value.status == DeviceStatus.INACTIVE
        assert result.value.cooldown_ends_at is None  # Sin cooldown

    def test_second_swap_no_cooldown(self, verifier, db):
        """Segundo swap del mes: sin cooldown."""
        lid = _insert_license(db, tier="editorial")
        did1 = _insert_device(db, lid, fingerprint="fp-swap-a")
        did2 = _insert_device(db, lid, fingerprint="fp-swap-b")

        r1 = verifier.deactivate_device(did1)
        assert r1.is_success
        assert r1.value.cooldown_ends_at is None

        r2 = verifier.deactivate_device(did2)
        assert r2.is_success
        assert r2.value.cooldown_ends_at is None

    def test_third_swap_has_cooldown(self, verifier, db):
        """Tercer swap del mes: cooldown 7 dias."""
        lid = _insert_license(db, tier="editorial")
        did1 = _insert_device(db, lid, fingerprint="fp-c1")
        did2 = _insert_device(db, lid, fingerprint="fp-c2")
        did3 = _insert_device(db, lid, fingerprint="fp-c3")

        verifier.deactivate_device(did1)
        verifier.deactivate_device(did2)
        r3 = verifier.deactivate_device(did3)

        assert r3.is_success
        assert r3.value.cooldown_ends_at is not None
        expected = datetime.utcnow() + timedelta(hours=168)
        diff = abs((r3.value.cooldown_ends_at - expected).total_seconds())
        assert diff < 5

    def test_swap_count_resets_monthly(self, verifier, db):
        """Swaps del mes anterior no cuentan."""
        lid = _insert_license(db, tier="editorial")

        # Insertar 3 swaps del mes anterior
        prev_period = UsageRecord.previous_billing_period()
        for i in range(3):
            db._conn.execute(
                "INSERT INTO device_swaps (license_id, device_id, billing_period) VALUES (?, ?, ?)",
                (lid, i + 1, prev_period),
            )
        db._conn.commit()

        # Primer swap del mes actual: deberia ser sin cooldown
        did = _insert_device(db, lid, fingerprint="fp-new-month")
        result = verifier.deactivate_device(did)
        assert result.is_success
        assert result.value.cooldown_ends_at is None

    def test_get_swap_count_this_month(self, verifier, db):
        """Helper _get_swap_count_this_month funciona correctamente."""
        lid = _insert_license(db, tier="corrector")
        assert verifier._get_swap_count_this_month(lid) == 0

        # Insertar 2 swaps del mes actual
        billing_period = UsageRecord.current_billing_period()
        for i in range(2):
            db._conn.execute(
                "INSERT INTO device_swaps (license_id, device_id, billing_period) VALUES (?, ?, ?)",
                (lid, i + 1, billing_period),
            )
        db._conn.commit()
        assert verifier._get_swap_count_this_month(lid) == 2
