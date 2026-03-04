"""
Planner incremental dependiente por impacto de capítulos y entidades.
"""

from __future__ import annotations

from typing import Any

from narrative_assistant.persistence.version_diff import ChapterDiffMetrics, VersionDiffRepository

# Fases de enrichment (Tier 3) controladas por planner.
ENRICHMENT_PHASES = ("relationships", "voice", "prose", "health")


def _derive_invalidation_signals(db: Any, project_id: int) -> dict[str, bool]:
    """Infiere señales de invalidación desde enrichment_cache."""
    try:
        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT enrichment_type
                FROM enrichment_cache
                WHERE project_id = ? AND status = 'stale'
                """,
                (project_id,),
            ).fetchall()
        stale_types = {str(row[0]) for row in rows if row and row[0]}
    except Exception:
        stale_types = set()

    if not stale_types:
        return {
            "entity_dependent_stale": False,
            "attribute_dependent_stale": False,
            "force_full": False,
        }

    try:
        from routers._invalidation import ATTRIBUTE_DEPENDENT_TYPES, ENTITY_DEPENDENT_TYPES

        entity_dependent_stale = bool(stale_types & ENTITY_DEPENDENT_TYPES)
        attribute_dependent_stale = bool(stale_types & ATTRIBUTE_DEPENDENT_TYPES)
    except Exception:
        # Fallback conservador: si no podemos resolver categorías, asumimos impacto.
        entity_dependent_stale = True
        attribute_dependent_stale = True

    return {
        "entity_dependent_stale": entity_dependent_stale,
        "attribute_dependent_stale": attribute_dependent_stale,
        "force_full": False,
    }


def build_impact_graph() -> dict[str, set[str]]:
    """
    Grafo de dependencias (simple) para cierre transitivo del impacto.

    Nota:
    - Tier 2 (NER/Fusion/Attributes/Consistency/Grammar/Alerts) se ejecuta siempre.
    - Este planner decide únicamente qué parte de Tier 3 conviene re-ejecutar.
    """
    return {
        "relationships": {"health"},
        "voice": {"health"},
        "prose": {"health"},
        "health": set(),
    }


def _close_over_dependencies(nodes: set[str], graph: dict[str, set[str]]) -> set[str]:
    closed = set(nodes)
    changed = True
    while changed:
        changed = False
        for node in list(closed):
            for dep in graph.get(node, set()):
                if dep not in closed:
                    closed.add(dep)
                    changed = True
    return closed


def compute_impacted_nodes(
    chapter_diff: ChapterDiffMetrics,
    entity_changes: dict[str, Any] | None = None,
    invalidations: dict[str, Any] | None = None,
) -> set[str]:
    """
    Calcula nodos impactados de Tier 3.
    """
    entity_changes = entity_changes or {}
    invalidations = invalidations or {}

    impacted: set[str] = set()
    has_text_delta = chapter_diff.modified > 0 or chapter_diff.added > 0 or chapter_diff.removed > 0

    # Cambios textuales afectan prosa/salud.
    if has_text_delta:
        impacted.update({"prose", "health"})

    # Cambios moderados suelen introducir drift de entidades/atributos.
    if chapter_diff.changed_ratio >= 0.12:
        impacted.update({"relationships", "voice"})

    # Señales explícitas de cambios de entidades/atributos.
    if entity_changes.get("has_ner_delta"):
        impacted.update({"relationships", "voice", "health"})
    if entity_changes.get("has_attribute_delta"):
        impacted.update({"voice", "health"})

    # Invalidaciones explícitas del sistema.
    if invalidations.get("entity_dependent_stale"):
        impacted.update({"relationships", "voice"})
    if invalidations.get("attribute_dependent_stale"):
        impacted.update({"voice", "health"})

    graph = build_impact_graph()
    return _close_over_dependencies(impacted, graph)


def build_phase_plan(
    chapter_diff: ChapterDiffMetrics,
    entity_changes: dict[str, Any] | None = None,
    invalidations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye el plan de ejecución incremental para Tier 3.
    """
    invalidations = invalidations or {}
    severe_structure_change = (
        chapter_diff.added > 0 or chapter_diff.removed > 0 or chapter_diff.changed_ratio >= 0.35
    )
    force_full = bool(invalidations.get("force_full", False))

    # CR-05: capítulos específicos afectados (para granularidad en enrichment)
    changed_chapters = sorted(
        chapter_diff.modified_chapters | chapter_diff.added_chapters
    )

    if severe_structure_change or force_full:
        reason = "severe_structure_change" if severe_structure_change else "forced_full"
        return {
            "mode": "full",
            "impacted_nodes": list(ENRICHMENT_PHASES),
            "run_relationships": True,
            "run_voice": True,
            "run_prose": True,
            "run_health": True,
            "chapter_diff": chapter_diff.to_dict(),
            "changed_chapter_numbers": changed_chapters,
            "reason": reason,
        }

    impacted_nodes = compute_impacted_nodes(
        chapter_diff=chapter_diff,
        entity_changes=entity_changes,
        invalidations=invalidations,
    )
    if not impacted_nodes:
        # Documento tocado pero sin impacto suficiente: solo prosa + health como baseline seguro.
        impacted_nodes = {"prose", "health"}

    return {
        "mode": "incremental",
        "impacted_nodes": sorted(impacted_nodes),
        "run_relationships": "relationships" in impacted_nodes,
        "run_voice": "voice" in impacted_nodes,
        "run_prose": "prose" in impacted_nodes,
        "run_health": "health" in impacted_nodes,
        "chapter_diff": chapter_diff.to_dict(),
        "changed_chapter_numbers": changed_chapters,
        "reason": "impact_planner",
    }


def build_incremental_plan(
    db: Any,
    project_id: int,
    snapshot_id: int | None,
    chapters_data: list[dict[str, Any]],
    *,
    chapter_metrics: ChapterDiffMetrics | None = None,
    entity_changes: dict[str, Any] | None = None,
    invalidations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    API legacy usada por `analysis.py`.
    """
    if chapter_metrics is None:
        repo = VersionDiffRepository(db)
        chapter_metrics = repo.compute_chapter_diff(snapshot_id, chapters_data)

    if entity_changes is None:
        # Heurística de fallback cuando no hay señales reales de Tier 2.
        entity_changes = {
            "has_ner_delta": chapter_metrics.changed_ratio >= 0.12,
            "has_attribute_delta": chapter_metrics.changed_ratio >= 0.20,
        }

    if invalidations is None:
        invalidations = _derive_invalidation_signals(db, project_id)

    return build_phase_plan(
        chapter_diff=chapter_metrics,
        entity_changes=entity_changes,
        invalidations=invalidations,
    )
