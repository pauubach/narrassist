"""Tests para T-014: concurrencia adaptativa de Tier-3."""

import sys
from pathlib import Path

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers.analysis import _select_tier3_worker_count  # noqa: E402


def test_select_workers_single_enabled_phase_returns_one() -> None:
    workers = _select_tier3_worker_count(
        run_relationships=True,
        run_voice=False,
        run_prose=False,
        run_health=False,
        cpu_count_override=16,
        available_memory_gb_override=32.0,
        queue_depth_override=0,
        active_tier3_override=0,
    )
    assert workers == 1


def test_select_workers_respects_low_cpu_and_memory() -> None:
    workers = _select_tier3_worker_count(
        run_relationships=True,
        run_voice=True,
        run_prose=True,
        run_health=True,
        cpu_count_override=2,
        available_memory_gb_override=1.5,
        queue_depth_override=0,
        active_tier3_override=0,
    )
    assert workers == 1


def test_select_workers_uses_four_on_powerful_machine_without_pressure() -> None:
    workers = _select_tier3_worker_count(
        run_relationships=True,
        run_voice=True,
        run_prose=True,
        run_health=True,
        cpu_count_override=16,
        available_memory_gb_override=24.0,
        queue_depth_override=0,
        active_tier3_override=0,
    )
    assert workers == 4


def test_select_workers_reduces_when_queue_and_parallel_runs_exist() -> None:
    workers = _select_tier3_worker_count(
        run_relationships=True,
        run_voice=True,
        run_prose=True,
        run_health=True,
        cpu_count_override=12,
        available_memory_gb_override=16.0,
        queue_depth_override=2,
        active_tier3_override=2,
    )
    assert workers == 2


def test_select_workers_never_drops_below_one() -> None:
    workers = _select_tier3_worker_count(
        run_relationships=True,
        run_voice=True,
        run_prose=True,
        run_health=True,
        cpu_count_override=4,
        available_memory_gb_override=2.5,
        queue_depth_override=9,
        active_tier3_override=5,
    )
    assert workers == 1
