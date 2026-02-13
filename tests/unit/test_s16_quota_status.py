"""
Tests for Sprint S16A: Quota Warnings + Tier Comparison UX.

S16-03: GET /api/license/quota-status endpoint.
S16-05/06: Warning level logic and days_remaining_in_period calculation.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure api-server is importable
_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)


# ============================================================================
# Helpers: mock objects
# ============================================================================


def _make_limits(max_pages: int = 1500, max_devices: int = 1, unlimited: bool = False):
    """Crea un mock de TierLimits."""
    limits = MagicMock()
    limits.max_pages_per_month = -1 if unlimited else max_pages
    limits.is_unlimited = unlimited
    limits.max_devices = max_devices
    return limits


def _make_subscription(days_remaining: int = 15):
    """Crea un mock de Subscription con current_period_end."""
    sub = MagicMock()
    sub.current_period_end = datetime.utcnow() + timedelta(days=days_remaining)
    return sub


def _make_license(tier="corrector", unlimited=False, max_pages=1500, sub_days=15):
    """Crea un mock de License."""
    lic = MagicMock()
    lic.tier = MagicMock()
    lic.tier.value = tier
    lic.limits = _make_limits(max_pages=max_pages, unlimited=unlimited)
    lic.subscription = _make_subscription(sub_days)
    lic.active_device_count = 1
    lic.status = MagicMock()
    lic.status.value = "active"
    lic.features = []
    lic.expires_at = None
    lic.grace_period_remaining = None
    lic.is_in_grace_period = False
    lic.extra_data = {}
    return lic


def _make_verification(license_obj, quota_remaining):
    """Crea un mock de VerificationResult."""
    v = MagicMock()
    v.is_valid = True
    v.license = license_obj
    v.quota_remaining = quota_remaining
    v.status = license_obj.status
    v.message = "OK"
    v.is_offline = False
    v.grace_remaining = None
    v.devices_remaining = 0
    return v


def _call(endpoint):
    """Ejecuta un endpoint async de forma sincrona."""
    return asyncio.run(endpoint())


# ============================================================================
# S16-03: quota-status endpoint tests
# ============================================================================


class TestQuotaStatusEndpoint:
    """Tests para GET /api/license/quota-status."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Importa el router despues de ajustar sys.path."""
        from routers.license import get_quota_status

        self.endpoint = get_quota_status

    def test_no_verifier_returns_zeros(self):
        """Sin LicenseVerifier retorna datos vacios con warning_level='none'."""
        with patch("routers.license.get_license_verifier", return_value=None):
            response = _call(self.endpoint)

        assert response.success is True
        assert response.data["pages_used"] == 0
        assert response.data["warning_level"] == "none"
        assert response.data["unlimited"] is False

    def test_0_percent_usage(self):
        """0% uso -> warning_level = 'none'."""
        lic = _make_license(max_pages=1500)
        verification = _make_verification(lic, quota_remaining=1500)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.success is True
        assert response.data["pages_used"] == 0
        assert response.data["pages_remaining"] == 1500
        assert response.data["percentage"] == 0
        assert response.data["warning_level"] == "none"

    def test_80_percent_warning(self):
        """80% uso -> warning_level = 'warning'."""
        lic = _make_license(max_pages=1500)
        verification = _make_verification(lic, quota_remaining=300)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.data["pages_used"] == 1200
        assert response.data["percentage"] == 80
        assert response.data["warning_level"] == "warning"

    def test_90_percent_danger(self):
        """90% uso -> warning_level = 'danger'."""
        lic = _make_license(max_pages=1000)
        verification = _make_verification(lic, quota_remaining=100)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.data["pages_used"] == 900
        assert response.data["percentage"] == 90
        assert response.data["warning_level"] == "danger"

    def test_100_percent_critical(self):
        """100% uso -> warning_level = 'critical'."""
        lic = _make_license(max_pages=1500)
        verification = _make_verification(lic, quota_remaining=0)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.data["pages_used"] == 1500
        assert response.data["percentage"] == 100
        assert response.data["warning_level"] == "critical"

    def test_unlimited_tier_always_none(self):
        """Tier ilimitado (editorial) siempre retorna warning_level='none'."""
        lic = _make_license(tier="editorial", unlimited=True)
        verification = _make_verification(lic, quota_remaining=None)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.data["unlimited"] is True
        assert response.data["percentage"] == 0
        assert response.data["warning_level"] == "none"

    def test_days_remaining_from_subscription(self):
        """days_remaining_in_period se calcula desde subscription.current_period_end."""
        lic = _make_license(max_pages=1500, sub_days=12)
        verification = _make_verification(lic, quota_remaining=1000)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        # Subscription has 12 days remaining
        days = response.data["days_remaining_in_period"]
        # Allow 1 day tolerance for edge-of-day timing
        assert 11 <= days <= 12

    def test_days_remaining_fallback_no_subscription(self):
        """Sin subscription, se estima fin de mes natural."""
        lic = _make_license(max_pages=1500)
        lic.subscription = None  # No subscription
        verification = _make_verification(lic, quota_remaining=1500)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        days = response.data["days_remaining_in_period"]
        assert days >= 0
        assert days <= 31  # Never more than a month

    def test_verify_failure_returns_zeros(self):
        """Si verify() falla, retorna datos vacios."""
        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=True, error="test error")

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.success is True
        assert response.data["warning_level"] == "none"


# ============================================================================
# S16-04: license status founder flag
# ============================================================================


class TestLicenseStatusEndpoint:
    """Tests para GET /api/license/status."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from routers.license import get_license_status

        self.endpoint = get_license_status

    def test_no_verifier_sets_founding_member_false(self):
        """Sin verificador, el flag founder debe ser False."""
        with patch("routers.license.get_license_verifier", return_value=None):
            response = _call(self.endpoint)

        assert response.success is True
        assert response.data["is_founding_member"] is False

    def test_status_includes_founding_member_true(self):
        """Si la licencia está marcada como founder, el endpoint lo refleja."""
        lic = _make_license()
        lic.extra_data = {"founding_member": True}
        verification = _make_verification(lic, quota_remaining=1200)

        verifier = MagicMock()
        verifier.verify.return_value = MagicMock(is_failure=False, value=verification)

        with patch("routers.license.get_license_verifier", return_value=verifier):
            response = _call(self.endpoint)

        assert response.success is True
        assert response.data["is_founding_member"] is True


# ============================================================================
# S16-02: Store computed properties (unit logic)
# ============================================================================


class TestQuotaWarningLevelLogic:
    """Tests para la logica de warning levels (misma que el store)."""

    @staticmethod
    def _compute_level(pages_used: int, pages_max: int, unlimited: bool = False) -> str:
        """Replica la logica del store quotaWarningLevel."""
        if unlimited or pages_max <= 0:
            return "none"
        pct = round(pages_used / pages_max * 100)
        if pct >= 100:
            return "critical"
        if pct >= 90:
            return "danger"
        if pct >= 80:
            return "warning"
        return "none"

    def test_0_percent(self):
        assert self._compute_level(0, 1500) == "none"

    def test_50_percent(self):
        assert self._compute_level(750, 1500) == "none"

    def test_79_percent(self):
        assert self._compute_level(1185, 1500) == "none"

    def test_80_percent(self):
        assert self._compute_level(1200, 1500) == "warning"

    def test_89_percent(self):
        assert self._compute_level(1335, 1500) == "warning"

    def test_90_percent(self):
        assert self._compute_level(1350, 1500) == "danger"

    def test_99_percent(self):
        assert self._compute_level(1485, 1500) == "danger"

    def test_100_percent(self):
        assert self._compute_level(1500, 1500) == "critical"

    def test_over_100_percent(self):
        assert self._compute_level(1600, 1500) == "critical"

    def test_unlimited(self):
        assert self._compute_level(5000, 1500, unlimited=True) == "none"

    def test_zero_max(self):
        assert self._compute_level(0, 0) == "none"
