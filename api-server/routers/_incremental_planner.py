"""
Planner incremental dependiente por impacto de capítulos y entidades.
"""

from __future__ import annotations

import json
from typing import Any

from narrative_assistant.persistence.version_diff import ChapterDiffMetrics, VersionDiffRepository

# Fases de enrichment (Tier 3) controladas por planner.
ENRICHMENT_PHASES = ("relationships", "voice", "prose", "health")


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.lstrip("-").isdigit():
            return int(normalized)
    return None


def _load_seed_entities_from_changed_chapters(
    db: Any, project_id: int, changed_chapters: list[int]
) -> set[int]:
    """Obtiene entidades semilla con actividad textual/eventual en capítulos modificados."""
    if not changed_chapters:
        return set()

    placeholders = ",".join("?" for _ in changed_chapters)
    params = (project_id, *changed_chapters)
    seeds: set[int] = set()

    try:
        with db.connection() as conn:
            mention_rows = conn.execute(
                f"""
                SELECT DISTINCT em.entity_id
                FROM entity_mentions em
                JOIN chapters ch ON em.chapter_id = ch.id
                WHERE ch.project_id = ?
                  AND ch.chapter_number IN ({placeholders})
                """,
                params,
            ).fetchall()
            for row in mention_rows:
                entity_id = _safe_int(row[0] if row else None)
                if entity_id and entity_id > 0:
                    seeds.add(entity_id)
    except Exception:
        pass

    # Acciones/eventos en capítulos cambiados (coherente con "acciones relacionadas").
    try:
        with db.connection() as conn:
            event_rows = conn.execute(
                f"""
                SELECT ne.entity_ids
                FROM narrative_events ne
                WHERE ne.project_id = ?
                  AND ne.chapter IN ({placeholders})
                  AND ne.entity_ids IS NOT NULL
                """,
                params,
            ).fetchall()
        for row in event_rows:
            if not row:
                continue
            raw = row[0]
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            if isinstance(parsed, list):
                for candidate in parsed:
                    entity_id = _safe_int(candidate)
                    if entity_id and entity_id > 0:
                        seeds.add(entity_id)
    except Exception:
        pass

    return seeds


def _load_seed_entities_from_version_links(
    db: Any,
    project_id: int,
    snapshot_id: int | None,
) -> set[int]:
    """Obtiene entidades potencialmente afectadas por renombres/fusiones entre versiones."""
    if not snapshot_id:
        return set()

    seeds: set[int] = set()
    try:
        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT old_entity_id, new_entity_id, link_type
                FROM entity_version_links
                WHERE project_id = ? AND snapshot_id = ?
                """,
                (project_id, snapshot_id),
            ).fetchall()
        for row in rows:
            if not row:
                continue
            link_type = str(row[2] or "").strip().lower()
            # matched = continuidad limpia; renamed/new/removed pueden propagar impacto.
            if link_type == "matched":
                continue
            old_id = _safe_int(row[0])
            new_id = _safe_int(row[1])
            if old_id and old_id > 0:
                seeds.add(old_id)
            if new_id and new_id > 0:
                seeds.add(new_id)
    except Exception:
        pass

    return seeds


def _expand_entity_subgraph(
    db: Any,
    project_id: int,
    seed_entity_ids: set[int],
    *,
    max_depth: int = 2,
) -> set[int]:
    """Cierre transitivo acotado sobre relaciones/interacciones y co-eventos narrativos."""
    if not seed_entity_ids:
        return set()

    related = set(seed_entity_ids)
    frontier = set(seed_entity_ids)

    for _ in range(max_depth):
        if not frontier:
            break

        ids = sorted(frontier)
        placeholders = ",".join("?" for _ in ids)
        next_ids: set[int] = set()

        try:
            with db.connection() as conn:
                rel_rows = conn.execute(
                    f"""
                    SELECT entity1_id, entity2_id
                    FROM relationships
                    WHERE project_id = ?
                      AND (entity1_id IN ({placeholders}) OR entity2_id IN ({placeholders}))
                    """,
                    (project_id, *ids, *ids),
                ).fetchall()
                for row in rel_rows:
                    e1 = _safe_int(row[0] if row else None)
                    e2 = _safe_int(row[1] if row else None)
                    if e1 and e1 > 0:
                        next_ids.add(e1)
                    if e2 and e2 > 0:
                        next_ids.add(e2)

                inter_rows = conn.execute(
                    f"""
                    SELECT entity1_id, entity2_id
                    FROM interactions
                    WHERE project_id = ?
                      AND (entity1_id IN ({placeholders}) OR entity2_id IN ({placeholders}))
                    """,
                    (project_id, *ids, *ids),
                ).fetchall()
                for row in inter_rows:
                    e1 = _safe_int(row[0] if row else None)
                    e2 = _safe_int(row[1] if row else None)
                    if e1 and e1 > 0:
                        next_ids.add(e1)
                    if e2 and e2 > 0:
                        next_ids.add(e2)

                # Vecinos por co-participación en eventos narrativos.
                event_rows = conn.execute(
                    f"""
                    SELECT ne.entity_ids
                    FROM narrative_events ne
                    WHERE ne.project_id = ?
                      AND ne.entity_ids IS NOT NULL
                      AND EXISTS (
                        SELECT 1
                        FROM json_each(ne.entity_ids) seed
                        WHERE CAST(seed.value AS INTEGER) IN ({placeholders})
                      )
                    """,
                    (project_id, *ids),
                ).fetchall()
                for row in event_rows:
                    raw = row[0] if row else None
                    if not raw:
                        continue
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        continue
                    if isinstance(parsed, list):
                        for candidate in parsed:
                            entity_id = _safe_int(candidate)
                            if entity_id and entity_id > 0:
                                next_ids.add(entity_id)
        except Exception:
            # Fallback seguro: conservar lo ya conocido.
            break

        new_nodes = next_ids - related
        related.update(new_nodes)
        frontier = new_nodes

    return related


def _load_chapters_for_entities(db: Any, project_id: int, entity_ids: set[int]) -> set[int]:
    """Capítulos en los que aparecen entidades impactadas."""
    if not entity_ids:
        return set()

    ids = sorted(entity_ids)
    placeholders = ",".join("?" for _ in ids)
    try:
        with db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT DISTINCT ch.chapter_number
                FROM entity_mentions em
                JOIN chapters ch ON em.chapter_id = ch.id
                WHERE ch.project_id = ?
                  AND em.entity_id IN ({placeholders})
                """,
                (project_id, *ids),
            ).fetchall()
        return {
            chapter_num
            for row in rows
            if row and (chapter_num := _safe_int(row[0])) is not None and chapter_num >= 0
        }
    except Exception:
        return set()


def _derive_entity_subgraph_context(
    db: Any,
    project_id: int,
    snapshot_id: int | None,
    chapter_diff: ChapterDiffMetrics,
    entity_changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye contexto granular de impacto por entidad+relaciones+acciones."""
    entity_changes = entity_changes or {}
    changed_chapters = sorted(chapter_diff.modified_chapters | chapter_diff.added_chapters)

    seeds = _load_seed_entities_from_changed_chapters(db, project_id, changed_chapters)
    seeds |= _load_seed_entities_from_version_links(db, project_id, snapshot_id)

    # Si hay delta de NER pero no semillas detectables, usar top entidades activas.
    if entity_changes.get("has_ner_delta") and not seeds:
        try:
            with db.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id
                    FROM entities
                    WHERE project_id = ? AND is_active = 1
                    ORDER BY mention_count DESC, id ASC
                    LIMIT 20
                    """,
                    (project_id,),
                ).fetchall()
            for row in rows:
                entity_id = _safe_int(row[0] if row else None)
                if entity_id and entity_id > 0:
                    seeds.add(entity_id)
        except Exception:
            pass

    impacted_entities = _expand_entity_subgraph(db, project_id, seeds, max_depth=2)
    impacted_chapters = _load_chapters_for_entities(db, project_id, impacted_entities)
    impacted_chapters |= set(changed_chapters)

    return {
        "seed_entity_ids": sorted(seeds),
        "impacted_entity_ids": sorted(impacted_entities),
        "impacted_chapter_numbers": sorted(impacted_chapters),
    }


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
    subgraph_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye el plan de ejecución incremental para Tier 3.
    """
    invalidations = invalidations or {}
    subgraph_context = subgraph_context or {}
    severe_structure_change = (
        chapter_diff.added > 0 or chapter_diff.removed > 0 or chapter_diff.changed_ratio >= 0.35
    )
    force_full = bool(invalidations.get("force_full", False))

    # CR-05: capítulos específicos afectados (para granularidad en enrichment)
    changed_chapters = sorted(
        chapter_diff.modified_chapters | chapter_diff.added_chapters
    )
    impacted_entity_ids = sorted(
        {
            entity_id
            for raw in subgraph_context.get("impacted_entity_ids", [])
            if (entity_id := _safe_int(raw)) is not None and entity_id > 0
        }
    )
    seed_entity_ids = sorted(
        {
            entity_id
            for raw in subgraph_context.get("seed_entity_ids", [])
            if (entity_id := _safe_int(raw)) is not None and entity_id > 0
        }
    )
    impacted_chapter_numbers = sorted(
        {
            chapter_num
            for raw in subgraph_context.get("impacted_chapter_numbers", [])
            if (chapter_num := _safe_int(raw)) is not None and chapter_num >= 0
        }
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
            "impacted_chapter_numbers": impacted_chapter_numbers,
            "impacted_entity_ids": impacted_entity_ids,
            "seed_entity_ids": seed_entity_ids,
            "reason": reason,
        }

    impacted_nodes = compute_impacted_nodes(
        chapter_diff=chapter_diff,
        entity_changes=entity_changes,
        invalidations=invalidations,
    )
    if impacted_entity_ids:
        # Subgrafo de entidades/acciones impacta principalmente relaciones/voz/salud.
        impacted_nodes.update({"relationships", "voice", "health"})
    if not impacted_nodes:
        # Documento tocado pero sin impacto suficiente: solo prosa + health como baseline seguro.
        impacted_nodes = {"prose", "health"}

    reason = "impact_planner"
    if impacted_entity_ids and chapter_diff.changed_ratio < 0.12:
        reason = "entity_subgraph_impact"

    return {
        "mode": "incremental",
        "impacted_nodes": sorted(impacted_nodes),
        "run_relationships": "relationships" in impacted_nodes,
        "run_voice": "voice" in impacted_nodes,
        "run_prose": "prose" in impacted_nodes,
        "run_health": "health" in impacted_nodes,
        "chapter_diff": chapter_diff.to_dict(),
        "changed_chapter_numbers": changed_chapters,
        "impacted_chapter_numbers": impacted_chapter_numbers,
        "impacted_entity_ids": impacted_entity_ids,
        "seed_entity_ids": seed_entity_ids,
        "reason": reason,
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

    subgraph_context = _derive_entity_subgraph_context(
        db=db,
        project_id=project_id,
        snapshot_id=snapshot_id,
        chapter_diff=chapter_metrics,
        entity_changes=entity_changes,
    )

    return build_phase_plan(
        chapter_diff=chapter_metrics,
        entity_changes=entity_changes,
        invalidations=invalidations,
        subgraph_context=subgraph_context,
    )
