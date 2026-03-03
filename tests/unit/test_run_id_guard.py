"""Tests para verificar que run_id protege contra escrituras stale en progress storage."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import ProgressTracker, _update_storage  # noqa: E402


@pytest.fixture()
def progress_storage(monkeypatch):
    """Configura un progress storage simulado con run_id."""
    import deps

    storage = {}
    monkeypatch.setattr(deps, "analysis_progress_storage", storage)
    # Lock real para thread-safety en tests
    import threading

    monkeypatch.setattr(deps, "_progress_lock", threading.Lock())
    return storage


def _make_tracker(project_id: int, run_id: str, storage: dict) -> ProgressTracker:
    """Crea un tracker y su storage asociado."""
    storage[project_id] = {
        "project_id": project_id,
        "_run_id": run_id,
        "status": "running",
        "progress": 0,
        "current_phase": "",
        "current_action": "",
        "metrics": {},
    }
    return ProgressTracker(
        project_id=project_id,
        phases=[],
        phase_weights={},
        phase_order=[],
        db_session=MagicMock(),
        run_id=run_id,
    )


def test_tracker_update_storage_writes_with_matching_run_id(progress_storage):
    tracker = _make_tracker(1, "abc123", progress_storage)

    tracker.update_storage(current_action="Testing")

    assert progress_storage[1]["current_action"] == "Testing"


def test_tracker_update_storage_rejects_stale_run_id(progress_storage):
    """Un tracker viejo no debe poder escribir en storage de una ejecución nueva."""
    old_tracker = _make_tracker(1, "old_run", progress_storage)

    # Simular que una nueva ejecución reemplazó el storage
    progress_storage[1]["_run_id"] = "new_run"
    progress_storage[1]["current_action"] = "New action"

    # El tracker viejo intenta escribir
    old_tracker.update_storage(current_action="Stale action")

    # La escritura debe ser rechazada
    assert progress_storage[1]["current_action"] == "New action"


def test_tracker_update_storage_metrics(progress_storage):
    tracker = _make_tracker(1, "run1", progress_storage)

    tracker.update_storage(metrics_update={"entities_found": 42})

    assert progress_storage[1]["metrics"]["entities_found"] == 42


def test_raw_update_storage_without_run_id_bypasses_guard(progress_storage):
    """_update_storage sin _run_id sigue funcionando (backwards compat)."""
    _make_tracker(1, "run1", progress_storage)

    _update_storage(1, current_action="Direct write")

    assert progress_storage[1]["current_action"] == "Direct write"


def test_raw_update_storage_with_wrong_run_id_rejected(progress_storage):
    """_update_storage con _run_id incorrecto es rechazada."""
    _make_tracker(1, "correct_run", progress_storage)

    _update_storage(1, _run_id="wrong_run", current_action="Should fail")

    assert progress_storage[1]["current_action"] == ""


def test_tracker_write_rejects_stale(progress_storage):
    """tracker._write() también rechaza si run_id no coincide."""
    old_tracker = _make_tracker(1, "old_run", progress_storage)
    progress_storage[1]["_run_id"] = "new_run"

    old_tracker._write(current_action="Should be rejected")

    assert progress_storage[1]["current_action"] == ""


def test_partial_tracker_with_run_id(progress_storage):
    """El tracker parcial con run_id debe proteger escrituras."""
    tracker = _make_tracker(1, "partial_run_1", progress_storage)

    tracker.update_storage(current_action="Partial phase")
    assert progress_storage[1]["current_action"] == "Partial phase"

    # Simular nueva ejecución
    progress_storage[1]["_run_id"] = "partial_run_2"
    tracker.update_storage(current_action="Stale partial")
    assert progress_storage[1]["current_action"] == "Partial phase"
