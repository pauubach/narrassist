"""Tests for remaining P1 tickets: HI-07/08, HI-10, HI-11, HI-16, HI-17."""
import re
import time
from pathlib import Path

import pytest

# Source file paths (api-server is not a pip package)
_API_ROOT = Path(__file__).resolve().parents[2] / "api-server" / "routers"
_ANALYSIS_PHASES = _API_ROOT / "_analysis_phases.py"
_ENRICHMENT_PHASES = _API_ROOT / "_enrichment_phases.py"
_SERVICES = _API_ROOT / "services.py"
_SYSTEM = _API_ROOT / "system.py"


# ─── HI-10: Silent failures → structured errors ─────────────────


class TestHI10SilentFailures:
    """Verify silent catches have been replaced with structured logging."""

    def test_mark_failed_logs_warning(self):
        """_mark_failed should log, not silently pass."""
        source = _ENRICHMENT_PHASES.read_text(encoding="utf-8")
        # Find the _mark_failed function's except block
        match = re.search(
            r"def _mark_failed\b.*?(?=\ndef\s|\Z)", source, re.DOTALL
        )
        assert match, "_mark_failed function not found"
        body = match.group(0)
        assert "logger.warning" in body, "_mark_failed should log warnings on failure"
        assert "except Exception:" not in body or "pass" not in body.split("except Exception:")[-1][:30], \
            "_mark_failed should not have bare 'pass' after except"

    def test_computing_status_logs_warning(self):
        """The 'computing' status setter should also log on failure."""
        source = _ENRICHMENT_PHASES.read_text(encoding="utf-8")
        # Check that there are no more bare "pass  # Best effort" patterns
        assert source.count("pass  # Best effort") == 0, \
            "No silent 'pass  # Best effort' catches should remain in _enrichment_phases.py"

    def test_lt_status_returns_error_on_exception(self):
        """LanguageTool status endpoint should return success=False on exception."""
        source = _SERVICES.read_text(encoding="utf-8")
        # Find the error handler in the LT status endpoint
        # It should return success=False, not success=True
        assert 'success=False' in source, \
            "LanguageTool status should return success=False on error"
        # Verify there's no success=True in an except block near "Error checking LanguageTool"
        idx = source.find("Error checking LanguageTool")
        assert idx > 0
        nearby = source[idx:idx + 200]
        assert "success=True" not in nearby, \
            "LanguageTool error handler should NOT return success=True"


# ─── HI-11: Idempotent guard on install ─────────────────────────


class TestHI11IdempotentGuard:
    """install_dependencies should reject concurrent calls."""

    def test_install_has_guard(self):
        source = _SYSTEM.read_text(encoding="utf-8")
        # Find install_dependencies function
        match = re.search(
            r"def install_dependencies\b.*?(?=\n@|\Z)", source, re.DOTALL
        )
        assert match, "install_dependencies function not found"
        body = match.group(0)
        # Should check INSTALLING_DEPENDENCIES before starting thread
        assert "INSTALLING_DEPENDENCIES" in body, "Should reference INSTALLING_DEPENDENCIES flag"
        # Should have early return/rejection when already installing
        guard_pattern = re.search(
            r"if\s+deps\.INSTALLING_DEPENDENCIES.*?return", body, re.DOTALL
        )
        assert guard_pattern, "Should have early return when INSTALLING_DEPENDENCIES is True"


# ─── HI-16: Watchdog marks stale running as error ───────────────


class TestHI16WatchdogStaleRunning:
    """Watchdog should mark stale 'running' status as error."""

    def test_running_not_excluded_from_error_marking(self):
        source = _ANALYSIS_PHASES.read_text(encoding="utf-8")
        match = re.search(
            r"def claim_heavy_slot_or_queue\b.*?(?=\ndef\s|\Z)",
            source,
            re.DOTALL,
        )
        assert match, "claim_heavy_slot_or_queue function not found"
        body = match.group(0)

        # "running" should NOT be in the exclusion list
        # The exclusion list should only have terminal/waiting states.
        status_check = re.search(r'status.*not in\s*\((.*?)\)', body, re.DOTALL)
        assert status_check, "Status exclusion check not found in watchdog function"
        excluded = status_check.group(1)
        assert '"running"' not in excluded, \
            "Watchdog should NOT exclude 'running' from error marking (HI-16)"
        assert '"completed"' in excluded, \
            "Watchdog should exclude 'completed' from error marking"


# ─── HI-17: Timeline degraded state ─────────────────────────────


class TestHI17TimelineDegraded:
    """Timeline failure should signal degraded state."""

    def test_timeline_failure_marks_degraded_phases(self):
        source = _ANALYSIS_PHASES.read_text(encoding="utf-8")
        # Find the timeline exception handler
        idx = source.find("Timeline construction failed (non-critical)")
        assert idx > 0, "Timeline failure handler not found"
        nearby = source[idx:idx + 600]
        assert "degraded_phases" in nearby, \
            "Timeline failure should add to degraded_phases in storage"


# ─── HI-08: Voting thresholds from settings ─────────────────────


class TestHI08VotingThresholds:
    """Voting thresholds should be read from user settings, not hardcoded."""

    def test_coref_uses_context_thresholds(self):
        source = _ANALYSIS_PHASES.read_text(encoding="utf-8")
        # Find CorefConfig instantiation
        match = re.search(r"CorefConfig\((.*?)\)", source, re.DOTALL)
        assert match, "CorefConfig instantiation not found"
        config_body = match.group(1)
        # Should NOT have hardcoded 0.5 for min_confidence
        assert "min_confidence=0.5" not in config_body, \
            "min_confidence should not be hardcoded to 0.5 (HI-08)"
        # Should reference ctx or a variable, not a literal
        assert "inference_min_confidence" in config_body or "user_min_conf" in config_body, \
            "min_confidence should come from user settings via context"

    def test_voting_thresholds_extracted_from_settings(self):
        source = _ANALYSIS_PHASES.read_text(encoding="utf-8")
        assert "voting_thresholds" in source, \
            "Should extract voting_thresholds from analysis_features"
        assert "inferenceMinConfidence" in source, \
            "Should read inferenceMinConfidence from settings"
        assert "inferenceMinConsensus" in source, \
            "Should read inferenceMinConsensus from settings"
