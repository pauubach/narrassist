"""Tests para CR-04: fast-path reutiliza artefactos tras cancelación."""

import sys
from pathlib import Path

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers.analysis import _should_use_fast_path  # noqa: E402


FP = "abc123def456"  # fingerprint de ejemplo


class TestShouldUseFastPath:
    """Verifica la lógica de elegibilidad del fast-path."""

    def test_completed_with_matching_fp(self):
        """Regresión: completed + fingerprint match → True."""
        assert _should_use_fast_path(FP, FP, "completed") is True

    def test_cancelled_with_matching_fp(self):
        """CR-04: cancelled + fingerprint match → True."""
        assert _should_use_fast_path(FP, FP, "cancelled") is True

    def test_pending_with_matching_fp(self):
        """CR-04: pending (cancelado desde cola) + fingerprint match → True."""
        assert _should_use_fast_path(FP, FP, "pending") is True

    def test_error_blocked(self):
        """Error siempre fuerza reanálisis completo."""
        assert _should_use_fast_path(FP, FP, "error") is False

    def test_failed_blocked(self):
        """Failed siempre fuerza reanálisis completo."""
        assert _should_use_fast_path(FP, FP, "failed") is False

    def test_no_previous_fingerprint(self):
        """Sin fingerprint previo → False (proyecto nuevo)."""
        assert _should_use_fast_path("", FP, "pending") is False

    def test_no_current_fingerprint(self):
        """Sin fingerprint actual → False."""
        assert _should_use_fast_path(FP, "", "completed") is False

    def test_fingerprint_mismatch(self):
        """Documento modificado → False."""
        assert _should_use_fast_path(FP, "different_fp", "completed") is False

    def test_none_fingerprints(self):
        """Fingerprints vacíos → False."""
        assert _should_use_fast_path("", "", "completed") is False
