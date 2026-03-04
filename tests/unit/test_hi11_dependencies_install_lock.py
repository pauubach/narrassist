"""Behavior tests for HI-11 atomic/idempotent dependencies install guard."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

import deps
from routers.system import install_dependencies


class _FakeThread:
    """Thread double that captures start() without executing target."""

    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True


class _FailingThread:
    """Thread double that fails on start() to test rollback."""

    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        raise RuntimeError("boom thread start")


@pytest.fixture(autouse=True)
def _reset_install_flag():
    prev = deps.INSTALLING_DEPENDENCIES
    deps.INSTALLING_DEPENDENCIES = False
    yield
    deps.INSTALLING_DEPENDENCIES = prev


def test_install_dependencies_rejects_second_call_while_in_progress(monkeypatch):
    monkeypatch.setattr(
        "routers.system.get_python_status",
        lambda: {
            "python_available": True,
            "python_path": "python",
            "python_version": "3.12.0",
            "error": None,
        },
    )
    monkeypatch.setattr("threading.Thread", _FakeThread)

    first = install_dependencies()
    second = install_dependencies()

    assert first.success is True
    assert first.data == {"installing": True}
    assert second.success is True
    assert second.data == {"installing": True}
    assert "already in progress" in (second.message or "").lower()


def test_install_dependencies_rolls_back_flag_if_thread_start_fails(monkeypatch):
    monkeypatch.setattr(
        "routers.system.get_python_status",
        lambda: {
            "python_available": True,
            "python_path": "python",
            "python_version": "3.12.0",
            "error": None,
        },
    )
    monkeypatch.setattr("threading.Thread", _FailingThread)

    with pytest.raises(RuntimeError):
        install_dependencies()

    assert deps.INSTALLING_DEPENDENCIES is False
