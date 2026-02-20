"""
Planner incremental dependiente por impacto de capítulos y entidades.
"""

from __future__ import annotations

from typing import Any

from narrative_assistant.persistence.version_diff import (
    ChapterDiffMetrics,
    VersionDiffRepository,
)


def build_incremental_plan(
    db: Any,
    project_id: int,
    snapshot_id: int | None,
    chapters_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Construye un plan de ejecución incremental para fases de enriquecimiento.

    Regla base:
    - Siempre ejecutar Tier 2 (NER/Fusion/Attributes/Consistency/Grammar)
      por dependencia global.
    - En Tier 3, permitir saltar `relationships` y `voice` si el cambio de capítulos
      es acotado y sin cambios estructurales severos.
    """
    repo = VersionDiffRepository(db)
    chapter_metrics: ChapterDiffMetrics = repo.compute_chapter_diff(snapshot_id, chapters_data)

    severe_structure_change = (
        chapter_metrics.added > 0
        or chapter_metrics.removed > 0
        or chapter_metrics.changed_ratio >= 0.35
    )

    can_skip_entity_enrichments = (
        not severe_structure_change
        and chapter_metrics.changed_ratio <= 0.10
        and chapter_metrics.modified <= max(1, int(chapter_metrics.total_current * 0.20))
    )

    plan = {
        "mode": "full" if severe_structure_change else "incremental",
        "run_relationships": not can_skip_entity_enrichments,
        "run_voice": not can_skip_entity_enrichments,
        "run_prose": True,
        "run_health": True,
        "chapter_diff": chapter_metrics.to_dict(),
        "reason": (
            "severe_structure_change"
            if severe_structure_change
            else ("limited_chapter_delta" if can_skip_entity_enrichments else "moderate_delta")
        ),
    }
    return plan
