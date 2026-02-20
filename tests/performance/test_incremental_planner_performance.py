import sys
import time
from pathlib import Path

_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)

from routers._incremental_planner import build_phase_plan

from narrative_assistant.persistence.version_diff import ChapterDiffMetrics


def test_incremental_planner_hot_path_performance() -> None:
    """
    Guardrail de rendimiento para el planner incremental.

    Objetivo: evitar regresiones obvias en el cálculo del plan.
    """
    chapter_diff = ChapterDiffMetrics(
        total_previous=120,
        total_current=120,
        modified=12,
        added=0,
        removed=0,
        changed_ratio=0.10,
    )

    t0 = time.perf_counter()
    for _ in range(20000):
        build_phase_plan(
            chapter_diff=chapter_diff,
            entity_changes={"has_ner_delta": False, "has_attribute_delta": False},
            invalidations={},
        )
    elapsed = time.perf_counter() - t0

    # Umbral deliberadamente holgado para no introducir flaky tests en CI.
    assert elapsed < 1.5
