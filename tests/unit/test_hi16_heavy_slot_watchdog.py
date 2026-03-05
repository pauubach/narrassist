"""Behavior tests for HI-16 heavy-slot watchdog stale-run protection."""

import copy
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

import deps
from routers._analysis_phases import claim_heavy_slot_or_queue


@pytest.fixture(autouse=True)
def _isolate_heavy_slot_state():
    prev_project_id = deps._heavy_analysis_project_id
    prev_claimed_at = deps._heavy_analysis_claimed_at
    prev_run_id = deps._heavy_analysis_run_id
    prev_timeout = deps.HEAVY_SLOT_TIMEOUT_SECONDS
    prev_project_manager = deps.project_manager
    prev_queue = copy.deepcopy(deps._heavy_analysis_queue)
    prev_storage = copy.deepcopy(deps.analysis_progress_storage)
    try:
        deps._heavy_analysis_project_id = None
        deps._heavy_analysis_claimed_at = None
        deps._heavy_analysis_run_id = None
        deps.HEAVY_SLOT_TIMEOUT_SECONDS = 1
        deps.project_manager = None
        deps._heavy_analysis_queue.clear()
        deps.analysis_progress_storage.clear()
        yield
    finally:
        deps._heavy_analysis_project_id = prev_project_id
        deps._heavy_analysis_claimed_at = prev_claimed_at
        deps._heavy_analysis_run_id = prev_run_id
        deps.HEAVY_SLOT_TIMEOUT_SECONDS = prev_timeout
        deps.project_manager = prev_project_manager
        deps._heavy_analysis_queue.clear()
        deps._heavy_analysis_queue.extend(prev_queue)
        deps.analysis_progress_storage.clear()
        deps.analysis_progress_storage.update(prev_storage)


def test_watchdog_does_not_mark_error_for_replaced_run():
    stale_pid = 101
    deps._heavy_analysis_project_id = stale_pid
    deps._heavy_analysis_claimed_at = time.time() - 5
    deps._heavy_analysis_run_id = "run-old"

    deps.analysis_progress_storage[stale_pid] = {
        "_run_id": "run-new",
        "status": "running",
        "_heavy_slot_claim_ts": time.time(),
    }
    deps.analysis_progress_storage[202] = {"status": "running"}

    ctx = {"project_id": 202, "_run_id": "run-202"}
    claimed = claim_heavy_slot_or_queue(ctx, SimpleNamespace())

    assert claimed is True
    assert deps.analysis_progress_storage[stale_pid]["status"] == "running"
    assert deps._heavy_analysis_project_id == 202
    assert deps._heavy_analysis_run_id == "run-202"


def test_watchdog_marks_error_for_same_stale_run():
    stale_pid = 303
    stale_claim_ts = time.time() - 5
    deps._heavy_analysis_project_id = stale_pid
    deps._heavy_analysis_claimed_at = stale_claim_ts
    deps._heavy_analysis_run_id = "run-stale"

    deps.analysis_progress_storage[stale_pid] = {
        "_run_id": "run-stale",
        "status": "running",
        "_heavy_slot_claim_ts": stale_claim_ts,
    }
    deps.analysis_progress_storage[404] = {"status": "running"}

    ctx = {"project_id": 404, "_run_id": "run-404"}
    claimed = claim_heavy_slot_or_queue(ctx, SimpleNamespace())

    assert claimed is True
    assert deps.analysis_progress_storage[stale_pid]["status"] == "error"
    err_msg = deps.analysis_progress_storage[stale_pid]["error"].lower()
    assert "tiempo maximo" in err_msg or "tiempo m\u00e1ximo" in err_msg


def test_watchdog_syncs_db_when_marking_stale_error():
    stale_pid = 505
    stale_claim_ts = time.time() - 5
    deps._heavy_analysis_project_id = stale_pid
    deps._heavy_analysis_claimed_at = stale_claim_ts
    deps._heavy_analysis_run_id = "run-stale"

    deps.analysis_progress_storage[stale_pid] = {
        "_run_id": "run-stale",
        "status": "running",
        "_heavy_slot_claim_ts": stale_claim_ts,
    }
    deps.analysis_progress_storage[606] = {"status": "running"}

    project = SimpleNamespace(id=stale_pid, analysis_status="analyzing", analysis_progress=0.42)
    updates: list[tuple[str, str, float]] = []

    class _FakeProjectManager:
        def get(self, pid: int):
            assert pid == stale_pid
            return SimpleNamespace(is_failure=False, value=project)

        def update(self, proj):
            updates.append((proj.analysis_status, str(proj.id), float(proj.analysis_progress)))

    deps.project_manager = _FakeProjectManager()

    ctx = {"project_id": 606, "_run_id": "run-606"}
    claimed = claim_heavy_slot_or_queue(ctx, SimpleNamespace())

    assert claimed is True
    assert deps.analysis_progress_storage[stale_pid]["status"] == "error"
    assert updates == [("error", str(stale_pid), 0.0)]


def test_watchdog_skips_db_sync_for_terminal_cancelled():
    stale_pid = 707
    stale_claim_ts = time.time() - 5
    deps._heavy_analysis_project_id = stale_pid
    deps._heavy_analysis_claimed_at = stale_claim_ts
    deps._heavy_analysis_run_id = "run-stale"

    deps.analysis_progress_storage[stale_pid] = {
        "_run_id": "run-stale",
        "status": "cancelled",
        "_heavy_slot_claim_ts": stale_claim_ts,
    }
    deps.analysis_progress_storage[808] = {"status": "running"}

    calls: list[tuple[str, int]] = []

    class _FakeProjectManager:
        def get(self, pid: int):
            calls.append(("get", pid))
            return SimpleNamespace(
                is_failure=False,
                value=SimpleNamespace(id=pid, analysis_status="cancelled", analysis_progress=0.0),
            )

        def update(self, proj):
            calls.append(("update", proj.id))

    deps.project_manager = _FakeProjectManager()

    ctx = {"project_id": 808, "_run_id": "run-808"}
    claimed = claim_heavy_slot_or_queue(ctx, SimpleNamespace())

    assert claimed is True
    assert deps.analysis_progress_storage[stale_pid]["status"] == "cancelled"
    assert calls == []


def test_watchdog_syncs_db_when_stale_storage_missing():
    stale_pid = 909
    stale_claim_ts = time.time() - 5
    deps._heavy_analysis_project_id = stale_pid
    deps._heavy_analysis_claimed_at = stale_claim_ts
    deps._heavy_analysis_run_id = "run-stale"

    # No stale storage for stale_pid: previous run died and storage was already cleaned.
    deps.analysis_progress_storage[1001] = {"status": "running"}

    updates: list[tuple[str, str, float]] = []
    project = SimpleNamespace(id=stale_pid, analysis_status="analyzing", analysis_progress=0.7)

    class _FakeProjectManager:
        def get(self, pid: int):
            assert pid == stale_pid
            return SimpleNamespace(is_failure=False, value=project)

        def update(self, proj):
            updates.append((proj.analysis_status, str(proj.id), float(proj.analysis_progress)))

    deps.project_manager = _FakeProjectManager()

    ctx = {"project_id": 1001, "_run_id": "run-1001"}
    claimed = claim_heavy_slot_or_queue(ctx, SimpleNamespace())

    assert claimed is True
    assert updates == [("error", str(stale_pid), 0.0)]
