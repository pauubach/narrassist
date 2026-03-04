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
    prev_queue = copy.deepcopy(deps._heavy_analysis_queue)
    prev_storage = copy.deepcopy(deps.analysis_progress_storage)
    try:
        deps._heavy_analysis_project_id = None
        deps._heavy_analysis_claimed_at = None
        deps._heavy_analysis_run_id = None
        deps.HEAVY_SLOT_TIMEOUT_SECONDS = 1
        deps._heavy_analysis_queue.clear()
        deps.analysis_progress_storage.clear()
        yield
    finally:
        deps._heavy_analysis_project_id = prev_project_id
        deps._heavy_analysis_claimed_at = prev_claimed_at
        deps._heavy_analysis_run_id = prev_run_id
        deps.HEAVY_SLOT_TIMEOUT_SECONDS = prev_timeout
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
    assert "tiempo máximo" in deps.analysis_progress_storage[stale_pid]["error"]
