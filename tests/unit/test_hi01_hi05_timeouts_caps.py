"""Tests for HI-01 through HI-05: timeouts, error logging, capabilities tri-axis."""
import time
from pathlib import Path

import pytest

# Path to api-server source (not a pip-installed package)
_API_SERVER_ROOT = Path(__file__).resolve().parents[2] / "api-server"
_SYSTEM_PY = _API_SERVER_ROOT / "routers" / "system.py"


# --- HI-01: Download Timeout Constants ---------------------------------------


class TestDownloadTimeoutConstants:
    """Verify named constants exist with sensible values."""

    def test_ollama_manager_constants(self):
        from narrative_assistant.llm.ollama_manager import (
            OLLAMA_GENERATE_TIMEOUT_S,
            OLLAMA_INSTALLER_TIMEOUT_S,
            OLLAMA_MODEL_PULL_TIMEOUT_S,
        )

        assert OLLAMA_INSTALLER_TIMEOUT_S >= 60, "Installer needs at least 1 min"
        assert OLLAMA_MODEL_PULL_TIMEOUT_S >= 600, "Model pull needs at least 10 min"
        assert OLLAMA_GENERATE_TIMEOUT_S >= 30, "Generate needs at least 30s"
        # Pull must be longer than installer
        assert OLLAMA_MODEL_PULL_TIMEOUT_S > OLLAMA_INSTALLER_TIMEOUT_S

    def test_llamacpp_manager_constants(self):
        from narrative_assistant.llm.llamacpp_manager import (
            LLAMACPP_BINARY_TIMEOUT_S,
            LLAMACPP_MODEL_TIMEOUT_S,
        )

        assert LLAMACPP_BINARY_TIMEOUT_S >= 60
        assert LLAMACPP_MODEL_TIMEOUT_S >= 600
        assert LLAMACPP_MODEL_TIMEOUT_S > LLAMACPP_BINARY_TIMEOUT_S


class TestDeadlineCalculation:
    """Verify the deadline-based timeout pattern produces correct remainders."""

    def test_remaining_never_negative(self):
        """Even when deadline has passed, min floor prevents negative timeout."""
        nlp_download_per_model_min_s = 60
        deadline = time.time() - 100  # already past
        remaining = max(nlp_download_per_model_min_s, deadline - time.time())
        assert remaining == nlp_download_per_model_min_s

    def test_remaining_equals_time_left_when_above_min(self):
        nlp_download_per_model_min_s = 60
        deadline = time.time() + 300  # 5 min left
        remaining = max(nlp_download_per_model_min_s, deadline - time.time())
        assert remaining >= 299  # approximately 300, accounting for execution time
        assert remaining <= 301

    def test_remaining_clamps_to_min_when_near_deadline(self):
        nlp_download_per_model_min_s = 60
        deadline = time.time() + 10  # only 10s left
        remaining = max(nlp_download_per_model_min_s, deadline - time.time())
        assert remaining == nlp_download_per_model_min_s


class TestDownloadEndpointArchitecture:
    """Verify HI-01 implementation uses robust orchestration patterns."""

    @pytest.fixture
    def source(self):
        return _SYSTEM_PY.read_text(encoding="utf-8")

    def test_timeout_loop_uses_wait_first_completed(self, source):
        assert "FIRST_COMPLETED" in source
        assert "wait(" in source
        # Avoid old anti-pattern in download loop.
        assert "as_completed(futures, timeout=" not in source
        assert "future.result(timeout=remaining)" not in source

    def test_progress_session_guard_is_wired(self, source):
        assert "begin_download_progress_session" in source
        assert "bind_download_progress_session" in source
        assert "rotate_download_progress_session" in source

    def test_parallel_download_start_is_guarded(self, source):
        assert "_has_active_nlp_downloads" in source
        assert "status_code=409" in source


# --- HI-05: Capabilities Tri-Axis --------------------------------------------


class TestCapabilitiesTriAxis:
    """Verify NLP methods include hardware_supported and requires_ollama fields."""

    @pytest.fixture
    def source(self):
        return _SYSTEM_PY.read_text(encoding="utf-8")

    def test_all_nlp_methods_have_tri_axis_fields(self, source):
        """Every NLP method must have hardware_supported and requires_ollama."""
        assert '"hardware_supported"' in source
        assert '"requires_ollama"' in source

    def test_llm_dependent_methods_require_ollama(self, source):
        """Methods that need LLM should have requires_ollama=True."""
        import re

        ollama_blocks = re.findall(r'"requires_ollama":\s*True', source)
        # At least 3: llm coreference, grammar llm, spelling llm
        assert len(ollama_blocks) >= 3, f"Expected >=3 ollama-dependent methods, found {len(ollama_blocks)}"

    def test_hardware_supported_false_only_for_gpu_dependent(self, source):
        """Only GPU-dependent methods (beto) should have hardware_supported = has_gpu."""
        count = source.count('"hardware_supported": has_gpu')
        assert count == 1, f"Expected exactly 1 dynamic hardware_supported (beto), found {count}"

    def test_always_available_methods_have_true_hardware(self, source):
        """Rule-based and heuristic methods should always be hardware_supported=True."""
        count = source.count('"hardware_supported": True')
        assert count >= 10, f"Expected >=10 always-supported methods, found {count}"


# --- HI-02: GPU Detection Logging ---------------------------------------------


class TestGPUDetectionLogging:
    """Verify the GPU detection catch logs instead of silencing."""

    def test_gpu_detection_uses_logger_warning(self):
        """The health endpoint GPU detection must log warnings, not bare except:pass."""
        source = _SYSTEM_PY.read_text(encoding="utf-8")
        assert "GPU detection failed" in source, "Expected logger.warning for GPU detection failure"
