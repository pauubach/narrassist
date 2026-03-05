"""Tests para CR-04: elegibilidad y completitud de fast-path tras cancelación."""

import sys
from pathlib import Path

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers.analysis import (  # noqa: E402
    _FAST_PATH_REQUIRED_PHASES,
    _has_complete_fast_path_artifacts,
    _missing_fast_path_phases,
    _should_use_fast_path,
)

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

    def test_status_normalization_accepts_case_and_spaces(self):
        """Regresión: el status se normaliza (strip/lower)."""
        assert _should_use_fast_path(FP, FP, "  CANCELLED  ") is True


class TestMissingFastPathPhases:
    """Verifica cobertura de fases requeridas para reutilización segura."""

    def test_returns_empty_when_all_required_present(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        assert _missing_fast_path_phases(executed) == []

    def test_detects_single_missing_phase(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        executed["timeline"] = False
        assert _missing_fast_path_phases(executed) == ["timeline"]

    def test_detects_multiple_missing_phases_in_pipeline_order(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        executed["ner"] = False
        executed["grammar"] = False
        missing = _missing_fast_path_phases(executed)
        assert missing == ["ner", "grammar"]

    def test_missing_when_phase_not_present_in_dict(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES if phase != "alerts"}
        assert _missing_fast_path_phases(executed) == ["alerts"]

    def test_ignores_non_required_phases(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        executed["relationships"] = False
        executed["voice"] = False
        assert _missing_fast_path_phases(executed) == []


class TestFastPathArtifactsCompleteness:
    """Valida reglas de seguridad para activar fast-path."""

    def test_rejects_when_no_chapters(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=0,
            entities_count=10,
            executed_phases={phase: True for phase in _FAST_PATH_REQUIRED_PHASES},
            previous_status="cancelled",
        )
        assert ok is False
        assert "incomplete persisted data" in reason

    def test_rejects_when_no_entities(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=8,
            entities_count=0,
            executed_phases={phase: True for phase in _FAST_PATH_REQUIRED_PHASES},
            previous_status="pending",
        )
        assert ok is False
        assert "incomplete persisted data" in reason

    def test_allows_legacy_completed_without_ledger(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases={},
            previous_status="completed",
        )
        assert ok is True
        assert reason == "legacy completed run without ledger"

    def test_rejects_cancelled_without_ledger(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases={},
            previous_status="cancelled",
        )
        assert ok is False
        assert reason == "missing run ledger for non-completed previous status"

    def test_rejects_pending_without_ledger(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases={},
            previous_status="pending",
        )
        assert ok is False
        assert reason == "missing run ledger for non-completed previous status"

    def test_rejects_when_required_phase_missing(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        executed["timeline"] = False
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases=executed,
            previous_status="cancelled",
        )
        assert ok is False
        assert "timeline" in reason

    def test_allows_cancelled_when_required_phases_present(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases={phase: True for phase in _FAST_PATH_REQUIRED_PHASES},
            previous_status="cancelled",
        )
        assert ok is True
        assert reason == "ok"

    def test_allows_pending_when_required_phases_present(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=7,
            entities_count=18,
            executed_phases={phase: True for phase in _FAST_PATH_REQUIRED_PHASES},
            previous_status="pending",
        )
        assert ok is True
        assert reason == "ok"

    def test_rejects_completed_when_ledger_exists_but_is_incomplete(self):
        executed = {phase: True for phase in _FAST_PATH_REQUIRED_PHASES}
        executed["alerts"] = False
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=5,
            entities_count=12,
            executed_phases=executed,
            previous_status="completed",
        )
        assert ok is False
        assert "alerts" in reason

    def test_allows_completed_with_full_ledger(self):
        ok, reason = _has_complete_fast_path_artifacts(
            chapters_count=9,
            entities_count=20,
            executed_phases={phase: True for phase in _FAST_PATH_REQUIRED_PHASES},
            previous_status="completed",
        )
        assert ok is True
        assert reason == "ok"
