"""
Enrichment phases 10-13: pre-compute and cache analysis results.

These phases run after the main analysis (phases 1-9) and persist results
in the enrichment_cache table for instant retrieval from GET endpoints.

Phase 10: Relationships (network, timeline, profiles, locations, emotional, archetypes)
Phase 11: Voice (profiles, deviations, register, focalization)
Phase 12: Prose (sticky, energy, echo, pacing, tension, sensory, readability, variation, dialogue, structure)
Phase 13: Health (chapter progress, narrative templates, narrative health)

S8a-07..10: Pipeline enrichment implementation.
"""

import hashlib
import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Cache helper
# ============================================================================


def _cache_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    result: Any,
    phase: int,
    entity_scope: str | None = None,
) -> bool:
    """Store an enrichment result in the cache table.

    Returns True if result was written, False if early cutoff (output unchanged).
    """
    from routers._enrichment_cache import get_schema_version

    try:
        result_json = json.dumps(result, ensure_ascii=False, default=str, sort_keys=True)
        output_hash = hashlib.sha256(result_json.encode()).hexdigest()[:16]
        current_schema = get_schema_version(enrichment_type)

        with db_session.connection() as conn:
            # Early cutoff: si el output_hash no cambió, solo marcar completed
            scope_filter = "entity_scope IS NULL" if entity_scope is None else "entity_scope = ?"
            params = [project_id, enrichment_type]
            if entity_scope is not None:
                params.append(entity_scope)

            existing = conn.execute(
                f"""SELECT output_hash, status, schema_version FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ? AND {scope_filter}
                    LIMIT 1""",
                params,
            ).fetchone()

            # Schema version changed → force update even if output_hash matches
            cached_schema = existing[2] if existing and len(existing) > 2 and existing[2] is not None else 0
            schema_outdated = cached_schema < current_schema

            if existing and existing[0] == output_hash and not schema_outdated and existing[1] in ("completed", "stale"):
                # Output no cambió — solo actualizar status y timestamp
                update_params = [project_id, enrichment_type]
                if entity_scope is not None:
                    update_params.append(entity_scope)
                conn.execute(
                    f"""UPDATE enrichment_cache
                        SET status = 'completed', updated_at = datetime('now')
                        WHERE project_id = ? AND enrichment_type = ? AND {scope_filter}""",
                    update_params,
                )
                conn.commit()
                logger.debug(f"Early cutoff: {enrichment_type} unchanged for project {project_id}")
                return False

            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status,
                    output_hash, result_json, phase, revision,
                    schema_version, computed_at, updated_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?, 0,
                           ?, datetime('now'), datetime('now'))""",
                (project_id, enrichment_type, entity_scope, output_hash, result_json, phase, current_schema),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.warning(f"Failed to cache {enrichment_type} for project {project_id}: {e}")
        return False


def _mark_failed(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    error: str,
    phase: int,
) -> None:
    """Mark an enrichment as failed in the cache table."""
    try:
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status,
                    error_message, phase, revision,
                    updated_at)
                   VALUES (?, ?, NULL, 'failed', ?, ?, 0, datetime('now'))""",
                (project_id, enrichment_type, error, phase),
            )
            conn.commit()
    except Exception as e:
        logger.warning("Failed to persist enrichment failure for %s/%s: %s",
                        project_id, enrichment_type, e)


def capture_entity_fingerprint(db_session: Any, project_id: int) -> str:
    """S8a-17: Capture entity state fingerprint for mutation detection.

    Returns a hash of entity IDs + updated_at timestamps.
    If entities are mutated during enrichment, this fingerprint changes.
    """
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """SELECT id, canonical_name, updated_at
                   FROM entities WHERE project_id = ?
                   ORDER BY id""",
                (project_id,),
            ).fetchall()
        raw = "|".join(f"{r[0]}:{r[1]}:{r[2]}" for r in rows)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except Exception:
        return ""


def _build_chapter_signature(db_session: Any, project_id: int) -> tuple[str, int]:
    """Firma estable de capítulos basada en número/título/contenido."""
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """
                SELECT chapter_number, title, content
                FROM chapters
                WHERE project_id = ?
                ORDER BY chapter_number
                """,
                (project_id,),
            ).fetchall()
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update(str(row["chapter_number"]).encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(row["title"] or "").encode("utf-8"))
            hasher.update(b"|")
            content = str(row["content"] or "")
            hasher.update(hashlib.sha256(content.encode("utf-8")).digest())
            hasher.update(b"\n")
        return hasher.hexdigest()[:16], len(rows)
    except Exception:
        return "", 0


def _build_entity_signature(db_session: Any, project_id: int) -> tuple[str, int]:
    """Firma estable de entidades activas, sin depender de IDs o timestamps."""
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """
                SELECT canonical_name, entity_type, importance, mention_count
                FROM entities
                WHERE project_id = ? AND is_active = 1
                ORDER BY canonical_name, entity_type
                """,
                (project_id,),
            ).fetchall()
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update(str(row["canonical_name"] or "").encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(row["entity_type"] or "").encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(row["importance"] or "").encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(int(row["mention_count"] or 0)).encode("utf-8"))
            hasher.update(b"\n")
        return hasher.hexdigest()[:16], len(rows)
    except Exception:
        return "", 0


def _build_mentions_signature(db_session: Any, project_id: int) -> str:
    """Firma estable de distribución de menciones por entidad/capítulo."""
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """
                SELECT e.canonical_name AS canonical_name,
                       COALESCE(ch.chapter_number, 0) AS chapter_number,
                       COUNT(*) AS mention_count
                FROM entity_mentions em
                JOIN entities e ON em.entity_id = e.id
                LEFT JOIN chapters ch ON em.chapter_id = ch.id
                WHERE e.project_id = ? AND e.is_active = 1
                GROUP BY e.canonical_name, ch.chapter_number
                ORDER BY e.canonical_name, ch.chapter_number
                """,
                (project_id,),
            ).fetchall()
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update(str(row["canonical_name"] or "").encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(int(row["chapter_number"] or 0)).encode("utf-8"))
            hasher.update(b"|")
            hasher.update(str(int(row["mention_count"] or 0)).encode("utf-8"))
            hasher.update(b"\n")
        return hasher.hexdigest()[:16]
    except Exception:
        return ""


def _build_default_input_payload(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    phase: int,
) -> dict[str, Any]:
    """Payload base para input_hash, estable entre ejecuciones equivalentes.

    Incluye schema_version para que un bump de versión invalide el hash
    y fuerce recomputación incluso si los datos de entrada no cambiaron.
    """
    from routers._enrichment_cache import get_schema_version

    chapter_signature, chapter_count = _build_chapter_signature(db_session, project_id)
    entity_signature, entity_count = _build_entity_signature(db_session, project_id)
    mentions_signature = _build_mentions_signature(db_session, project_id)
    invalidation_revision = 0
    try:
        with db_session.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(revision), 0) AS rev
                FROM invalidation_events
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
        invalidation_revision = int(row["rev"] if row else 0)
    except Exception:
        invalidation_revision = 0

    return {
        "enrichment_type": enrichment_type,
        "phase": phase,
        "schema_version": get_schema_version(enrichment_type),
        "chapter_count": chapter_count,
        "chapter_signature": chapter_signature,
        "entity_count": entity_count,
        "entity_signature": entity_signature,
        "mentions_signature": mentions_signature,
        "invalidation_revision": invalidation_revision,
    }


def invalidate_enrichment_if_mutated(
    db_session: Any, project_id: int, saved_fingerprint: str
) -> bool:
    """S8a-17 + S8c-11: Check if entities were mutated during enrichment.

    If the fingerprint changed, mark entity-dependent enrichments as stale
    (granular invalidation) instead of deleting everything.
    Returns True if cache was invalidated.
    """
    if not saved_fingerprint:
        return False

    current = capture_entity_fingerprint(db_session, project_id)
    if current != saved_fingerprint:
        logger.warning(
            f"[Enrichment] Entity mutation detected for project {project_id} "
            f"(before={saved_fingerprint}, after={current}). Marking stale."
        )
        try:
            from routers._invalidation import ATTRIBUTE_DEPENDENT_TYPES, ENTITY_DEPENDENT_TYPES

            affected_types = ENTITY_DEPENDENT_TYPES | ATTRIBUTE_DEPENDENT_TYPES
            placeholders = ",".join("?" for _ in affected_types)

            with db_session.connection() as conn:
                conn.execute(
                    f"""UPDATE enrichment_cache
                        SET status = 'stale', updated_at = datetime('now')
                        WHERE project_id = ?
                        AND enrichment_type IN ({placeholders})
                        AND status = 'completed'""",
                    [project_id] + list(affected_types),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark enrichment stale: {e}")
            # Fallback: delete all (legacy behavior)
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        "DELETE FROM enrichment_cache WHERE project_id = ?",
                        (project_id,),
                    )
                    conn.commit()
            except Exception:
                pass
        return True
    return False


# ============================================================================
# CR-05: Chapter-scoped & entity-scoped incremental helpers
# ============================================================================

# Umbral: si más del 50% de capítulos/entidades cambiaron, cómputo global.
_GRANULAR_THRESHOLD = 0.5

# Enrichments de prosa elegibles para caching per-chapter.
CHAPTER_SCOPED_ENRICHMENTS = frozenset({
    "sticky_sentences",
    "sentence_energy",
    "echo_report",
    "sentence_variation",
    "pacing_analysis",
    "dialogue_validation",
})


def _build_per_chapter_content_hashes(
    db_session: Any, project_id: int,
) -> dict[int, str]:
    """Hash de contenido por chapter_number para cache granular."""
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                "SELECT chapter_number, content FROM chapters "
                "WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        return {
            int(row["chapter_number"]): hashlib.sha256(
                (row["content"] or "").encode("utf-8")
            ).hexdigest()[:16]
            for row in rows
        }
    except Exception:
        return {}


def _get_cached_chapter_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    chapter_number: int,
    expected_input_hash: str | None = None,
) -> dict | None:
    """Lee resultado cacheado per-chapter (entity_scope = 'chapter:N')."""
    scope = f"chapter:{chapter_number}"
    try:
        from routers._enrichment_cache import get_schema_version

        with db_session.connection() as conn:
            row = conn.execute(
                """SELECT result_json, input_hash, schema_version FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = ?
                   AND entity_scope = ? AND status = 'completed'
                   LIMIT 1""",
                (project_id, enrichment_type, scope),
            ).fetchone()
        if row and row[0]:
            cached_hash = str(row[1] or "")
            cached_schema = int(row[2] or 0)
            required_schema = int(get_schema_version(enrichment_type))
            if cached_schema < required_schema:
                return None
            if expected_input_hash and (not cached_hash or cached_hash != expected_input_hash):
                return None
            return json.loads(row[0])
    except Exception:
        pass
    return None


def _cache_chapter_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    chapter_number: int,
    result: dict,
    phase: int,
    content_hash: str,
) -> None:
    """Almacena resultado per-chapter en enrichment_cache."""
    scope = f"chapter:{chapter_number}"
    result_json = json.dumps(result, ensure_ascii=False, default=str, sort_keys=True)
    try:
        from routers._enrichment_cache import get_schema_version
        schema_v = get_schema_version(enrichment_type)
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status, phase,
                    input_hash, result_json, schema_version, computed_at, updated_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (project_id, enrichment_type, scope, phase,
                 content_hash, result_json, schema_v),
            )
            conn.commit()
    except Exception as e:
        logger.debug(f"[CR-05] Failed to cache chapter result: {e}")


def _run_chapter_scoped_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    phase: int,
    chapters: list,
    changed_chapter_numbers: list[int] | None,
    compute_one_chapter,
    merge_fn,
    label: str,
    ctx: dict | None = None,
) -> bool:
    """CR-05: Ejecuta un enrichment per-chapter, reutilizando cache para capítulos sin cambios.

    Parámetros:
        compute_one_chapter: callable(chapter) → dict  (resultado para 1 capítulo)
        merge_fn: callable(dict[int, dict]) → dict  (agrega per-chapter → global)
        changed_chapter_numbers: capítulos modificados (None = todos)

    Fallback a cómputo global cuando:
    - changed_chapter_numbers es None (primer análisis / sin snapshot)
    - >50% de capítulos cambiaron
    """
    ch_numbers = [ch.chapter_number for ch in chapters]
    changed_set = set(changed_chapter_numbers) if changed_chapter_numbers is not None else None

    # Fallback: sin info o demasiados cambios
    use_granular = (
        changed_set is not None
        and len(ch_numbers) > 0
        and len(changed_set) <= len(ch_numbers) * _GRANULAR_THRESHOLD
    )

    if not use_granular:
        # Fallback a cómputo global (comportamiento original)
        def _compute_all():
            per_ch = {}
            for ch in chapters:
                per_ch[ch.chapter_number] = compute_one_chapter(ch)
            return merge_fn(per_ch)
        return _run_enrichment(
            db_session, project_id, enrichment_type, phase,
            _compute_all, label, ctx=ctx,
        )

    # Modo granular per-chapter
    t0 = time.time()
    content_hashes = _build_per_chapter_content_hashes(db_session, project_id)
    per_chapter_results: dict[int, dict] = {}
    computed = 0
    cached_count = 0

    for ch in chapters:
        ch_num = ch.chapter_number
        if ch_num not in changed_set:
            # Intentar leer cache
            cached_result = _get_cached_chapter_result(
                db_session,
                project_id,
                enrichment_type,
                ch_num,
                expected_input_hash=content_hashes.get(ch_num, ""),
            )
            if cached_result is not None:
                per_chapter_results[ch_num] = cached_result
                cached_count += 1
                continue
        # Computar (capítulo modificado o cache miss)
        try:
            result = compute_one_chapter(ch)
            per_chapter_results[ch_num] = result
            computed += 1
            # Cachear resultado per-chapter
            ch_hash = content_hashes.get(ch_num, "")
            _cache_chapter_result(
                db_session, project_id, enrichment_type, ch_num,
                result, phase, ch_hash,
            )
        except Exception as e:
            logger.warning(f"[CR-05] {label} ch{ch_num} failed: {e}")
            per_chapter_results[ch_num] = {}

    # Merge y cachear resultado global
    merged = merge_fn(per_chapter_results)
    _cache_result(db_session, project_id, enrichment_type, merged, phase)

    elapsed = time.time() - t0
    logger.info(
        f"[CR-05] {label}: {computed} computed, {cached_count} cached, "
        f"{elapsed:.1f}s"
    )
    if ctx is not None:
        timings = ctx.setdefault("phase_durations_json", {})
        if isinstance(timings, dict):
            timings[enrichment_type] = round(elapsed, 3)
    return True


def _get_affected_entity_ids(
    db_session: Any, project_id: int, changed_chapter_numbers: list[int],
) -> set[int]:
    """CR-05 Capa 3: Entidades con menciones en capítulos modificados."""
    if not changed_chapter_numbers:
        return set()
    placeholders = ",".join("?" for _ in changed_chapter_numbers)
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                f"""SELECT DISTINCT em.entity_id
                    FROM entity_mentions em
                    JOIN chapters ch ON em.chapter_id = ch.id
                    WHERE ch.project_id = ? AND ch.chapter_number IN ({placeholders})""",
                (project_id, *changed_chapter_numbers),
            ).fetchall()
        base_ids = {int(row[0]) for row in rows if row and row[0]}
        return _expand_related_entity_ids(db_session, project_id, base_ids)
    except Exception:
        return set()


def _expand_related_entity_ids(
    db_session: Any,
    project_id: int,
    seed_ids: set[int],
    max_depth: int = 2,
) -> set[int]:
    """Amplía entidades afectadas con vecinos relacionales (cierre transitivo acotado)."""
    if not seed_ids:
        return set()

    related = set(seed_ids)
    frontier = set(seed_ids)

    for _ in range(max_depth):
        if not frontier:
            break

        ids = sorted(frontier)
        placeholders = ",".join("?" for _ in ids)
        neighbors: set[int] = set()

        try:
            with db_session.connection() as conn:
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
                    e1 = int(row[0] or 0)
                    e2 = int(row[1] or 0)
                    if e1 > 0:
                        neighbors.add(e1)
                    if e2 > 0:
                        neighbors.add(e2)

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
                    e1 = int(row[0] or 0)
                    e2 = int(row[1] or 0)
                    if e1 > 0:
                        neighbors.add(e1)
                    if e2 > 0:
                        neighbors.add(e2)
        except Exception:
            # Best-effort: si falla la expansión, devolvemos al menos el seed set.
            return related

        new_nodes = neighbors - related
        related.update(new_nodes)
        frontier = new_nodes

    return related


def _get_cached_entity_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    entity_id: int,
) -> dict | None:
    """Lee resultado cacheado per-entity (entity_scope = 'entity:ID')."""
    scope = f"entity:{entity_id}"
    try:
        from routers._enrichment_cache import get_schema_version

        with db_session.connection() as conn:
            row = conn.execute(
                """SELECT result_json, schema_version FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = ?
                   AND entity_scope = ? AND status = 'completed'
                   LIMIT 1""",
                (project_id, enrichment_type, scope),
            ).fetchone()
        if row and row[0]:
            cached_schema = int(row[1] or 0)
            required_schema = int(get_schema_version(enrichment_type))
            if cached_schema < required_schema:
                return None
            return json.loads(row[0])
    except Exception:
        pass
    return None


def _cache_entity_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    entity_id: int,
    result: dict,
    phase: int,
) -> None:
    """Almacena resultado per-entity en enrichment_cache."""
    scope = f"entity:{entity_id}"
    result_json = json.dumps(result, ensure_ascii=False, default=str, sort_keys=True)
    try:
        from routers._enrichment_cache import get_schema_version
        schema_v = get_schema_version(enrichment_type)
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status, phase,
                    result_json, schema_version, computed_at, updated_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?, datetime('now'), datetime('now'))""",
                (project_id, enrichment_type, scope, phase, result_json, schema_v),
            )
            conn.commit()
    except Exception as e:
        logger.debug(f"[CR-05] Failed to cache entity result: {e}")


def _run_entity_scoped_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    phase: int,
    entities: list,
    changed_chapter_numbers: list[int] | None,
    compute_one_entity,
    merge_fn,
    label: str,
    ctx: dict | None = None,
) -> bool:
    """CR-05 Capa 3: Ejecuta enrichment per-entity, reutilizando cache para entidades sin cambios.

    Parámetros:
        compute_one_entity: callable(entity) → dict  (resultado para 1 entidad)
        merge_fn: callable(dict[int, dict]) → dict  (agrega per-entity → global)
        changed_chapter_numbers: capítulos modificados → determina entidades afectadas

    Fallback a cómputo global cuando:
    - changed_chapter_numbers es None (primer análisis)
    - >50% de entidades afectadas
    """
    affected_ids: set[int] | None = None
    if changed_chapter_numbers is not None:
        affected_ids = _get_affected_entity_ids(
            db_session, project_id, changed_chapter_numbers,
        )

    entity_ids = [e.id for e in entities]
    use_granular = (
        affected_ids is not None
        and len(entity_ids) > 0
        and len(affected_ids) <= len(entity_ids) * _GRANULAR_THRESHOLD
    )

    if not use_granular:
        # Fallback a cómputo global
        def _compute_all():
            per_ent = {}
            for entity in entities:
                per_ent[entity.id] = compute_one_entity(entity)
            return merge_fn(per_ent)
        return _run_enrichment(
            db_session, project_id, enrichment_type, phase,
            _compute_all, label, ctx=ctx,
        )

    # Modo granular per-entity
    t0 = time.time()
    per_entity_results: dict[int, dict] = {}
    computed = 0
    cached_count = 0

    for entity in entities:
        eid = entity.id
        if eid not in affected_ids:
            cached_result = _get_cached_entity_result(
                db_session, project_id, enrichment_type, eid,
            )
            if cached_result is not None:
                per_entity_results[eid] = cached_result
                cached_count += 1
                continue
        # Computar (entidad afectada o cache miss)
        try:
            result = compute_one_entity(entity)
            per_entity_results[eid] = result
            computed += 1
            _cache_entity_result(
                db_session, project_id, enrichment_type, eid,
                result, phase,
            )
        except Exception as e:
            logger.warning(f"[CR-05] {label} entity {eid} failed: {e}")
            per_entity_results[eid] = {}

    # Merge y cachear resultado global
    merged = merge_fn(per_entity_results)
    _cache_result(db_session, project_id, enrichment_type, merged, phase)

    elapsed = time.time() - t0
    logger.info(
        f"[CR-05] {label}: {computed} computed, {cached_count} cached, "
        f"{elapsed:.1f}s"
    )
    if ctx is not None:
        timings = ctx.setdefault("phase_durations_json", {})
        if isinstance(timings, dict):
            timings[enrichment_type] = round(elapsed, 3)
    return True


def _run_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    phase: int,
    compute_fn,
    label: str,
    input_payload: Any | None = None,
    ctx: dict | None = None,
) -> bool:
    """Run a single enrichment computation with error handling.

    Marks cache as 'computing' before starting. On success, stores result
    atomically. On failure, marks as 'failed' with error message.

    Returns True if successful, False otherwise.
    """
    if input_payload is None:
        try:
            input_payload = _build_default_input_payload(
                db_session=db_session,
                project_id=project_id,
                enrichment_type=enrichment_type,
                phase=phase,
            )
        except Exception:
            input_payload = {"enrichment_type": enrichment_type, "phase": phase}

    input_hash = _hash_payload(input_payload)

    # Fast skip por input_hash antes de computar (Sprint C).
    if input_hash:
        try:
            with db_session.connection() as conn:
                cached = conn.execute(
                    """
                    SELECT status, input_hash, result_json
                    FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                    LIMIT 1
                    """,
                    (project_id, enrichment_type),
                ).fetchone()
                if (
                    cached
                    and cached[1] == input_hash
                    and cached[0] == "completed"
                    and cached[2]
                ):
                    conn.execute(
                        """
                        UPDATE enrichment_cache
                        SET status = 'completed', updated_at = datetime('now')
                        WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                        """,
                        (project_id, enrichment_type),
                    )
                    conn.commit()
                    logger.info(
                        "[Enrichment] %s skipped (%s, input_hash unchanged: %s)",
                        label,
                        cached[0],
                        input_hash,
                    )
                    return True
        except Exception:
            pass

    # Marcar como 'computing' antes de empezar (S8c-10)
    try:
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status, phase, input_hash, updated_at)
                   VALUES (?, ?, NULL, 'computing', ?, ?, datetime('now'))""",
                (project_id, enrichment_type, phase, input_hash),
            )
            conn.commit()
    except Exception as e:
        logger.warning("Failed to mark enrichment %s/%s as computing: %s",
                        project_id, enrichment_type, e)

    try:
        t0 = time.time()
        result = compute_fn()
        elapsed = time.time() - t0
        changed = _cache_result(db_session, project_id, enrichment_type, result, phase)
        if input_hash:
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        """
                        UPDATE enrichment_cache
                        SET input_hash = ?, updated_at = datetime('now')
                        WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                        """,
                        (input_hash, project_id, enrichment_type),
                    )
                    conn.commit()
            except Exception:
                pass
        if ctx is not None:
            timings = ctx.setdefault("phase_durations_json", {})
            if isinstance(timings, dict):
                timings[enrichment_type] = round(elapsed, 3)
        cutoff_note = "" if changed else " (early cutoff)"
        logger.info(f"[Enrichment] {label} completed in {elapsed:.1f}s{cutoff_note}")
        return True
    except Exception as e:
        logger.warning(f"[Enrichment] {label} failed: {e}", exc_info=True)
        _mark_failed(db_session, project_id, enrichment_type, str(e)[:500], phase)
        return False


# ============================================================================
# Data loaders (shared across phases)
# ============================================================================


def _load_entities(db_session, project_id):
    """Load entities from DB."""
    from narrative_assistant.entities.repository import get_entity_repository

    repo = get_entity_repository(db_session)
    return repo.get_entities_by_project(project_id)


def _load_chapters(db_session, project_id):
    """Load chapters from DB."""
    from narrative_assistant.persistence.chapter import get_chapter_repository

    repo = get_chapter_repository(db_session)
    return repo.get_by_project(project_id)


def _build_full_text(chapters):
    """Build full text from chapters."""
    return "\n\n".join(ch.content for ch in chapters if ch.content)


def _chapters_to_dicts(chapters):
    """Convert chapter objects to dicts for analysis functions."""
    result = []
    offset = 0
    for ch in chapters:
        content = ch.content or ""
        result.append(
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": content,
                "start_char": offset,
                "end_char": offset + len(content),
            }
        )
        offset += len(content) + 2  # +2 for \n\n separator
    return result


def _entities_to_dicts(entities):
    """Convert entity objects to dicts for analysis functions."""
    result = []
    for e in entities:
        etype = e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type)
        result.append(
            {
                "id": e.id,
                "name": e.canonical_name,
                "entity_type": etype,
                "aliases": getattr(e, "aliases", []) or [],
                "importance": getattr(e, "importance", None),
            }
        )
    return result


def _detect_all_dialogues(chapters):
    """Detect dialogues in all chapters. Returns list of (speaker_hint, text, start, end, chapter_num)."""
    from narrative_assistant.nlp.dialogue import detect_dialogues

    all_dialogues = []
    for ch in chapters:
        try:
            dialogues = detect_dialogues(ch.content or "")
            for d in dialogues:
                speaker_hint = d[0] if len(d) > 0 else None
                text = d[1] if len(d) > 1 else ""
                start = d[2] if len(d) > 2 else 0
                end = d[3] if len(d) > 3 else len(text)
                all_dialogues.append(
                    {
                        "speaker_hint": speaker_hint,
                        "text": text,
                        "start_char": start,
                        "end_char": end,
                        "chapter": ch.chapter_number,
                    }
                )
        except Exception as e:
            logger.warning(f"Dialogue detection failed for chapter {ch.chapter_number}: {e}")
    return all_dialogues


# ============================================================================
# Phase 10: Relationships enrichment
# ============================================================================


def run_relationships_enrichment(ctx: dict, tracker) -> None:
    """Phase 10: Pre-compute relationship-related analysis."""
    from functools import partial

    phase_key = "relationships"
    phase_index = 9  # 0-indexed (10th phase)

    tracker.start_phase(phase_key, phase_index, "Analizando relaciones entre personajes...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]
    analysis_config = ctx.get("analysis_config")

    # CR-05: capítulos modificados para caching granular per-entity
    inc_plan = ctx.get("incremental_plan") or {}
    changed_ch = inc_plan.get("changed_chapter_numbers")

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        # entities_dicts and full_text computed on demand by individual phases

        character_entities = [
            e
            for e in entities
            if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
            in ("character", "animal", "creature")
        ]

        total_steps = 6
        step = 0

        # --- 10a: Character Network ---
        step += 1
        if not analysis_config or analysis_config.run_network_analysis:
            tracker.update_parallel_progress(phase_key, step / total_steps, "Calculando red de personajes...")
            _run_enrichment(
                db,
                project_id,
                "character_network",
                10,
                lambda: _compute_character_network(db, project_id, entities, chapters),
                "character_network",
            )
        else:
            tracker.update_parallel_progress(phase_key, step / total_steps, "Red de personajes omitida")

        # --- 10b: Character Timeline (entity-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Generando línea temporal...")
        ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}
        _shared_tl = {"db": db, "ch_number_map": ch_number_map, "chapters": chapters}
        _compute_tl = partial(_compute_timeline_for_entity, _shared=_shared_tl)
        _merge_tl = partial(_merge_timeline, chapters=chapters)
        _run_entity_scoped_enrichment(
            db, project_id, "character_timeline", 10,
            character_entities, changed_ch,
            _compute_tl, _merge_tl,
            "character_timeline", ctx=ctx,
        )

        # --- 10c: Character Profiles (6 indicators) ---
        step += 1
        if not analysis_config or analysis_config.run_character_profiling:
            tracker.update_parallel_progress(phase_key, step / total_steps, "Perfilando personajes...")
            _run_enrichment(
                db,
                project_id,
                "character_profiles",
                10,
                lambda: _compute_character_profiles(db, project_id, entities, chapters),
                "character_profiles",
            )
        else:
            tracker.update_parallel_progress(phase_key, step / total_steps, "Perfilado de personajes omitido")

        # --- 10d: Emotional Analysis ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Analizando coherencia emocional...")
        _run_enrichment(
            db,
            project_id,
            "emotional_analysis",
            10,
            lambda: _compute_emotional_analysis(chapters, character_entities),
            "emotional_analysis",
        )

        # --- 10e: Character Archetypes ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Detectando arquetipos...")
        _run_enrichment(
            db,
            project_id,
            "character_archetypes",
            10,
            lambda: _compute_character_archetypes(
                db, project_id, entities, chapters, chapters_dicts
            ),
            "character_archetypes",
        )

        # --- 10f: Character Knowledge ---
        step += 1
        if not analysis_config or analysis_config.run_knowledge:
            knowledge_mode = _resolve_character_knowledge_mode(ctx)
            tracker.update_progress(
                phase_key, step / total_steps, "Analizando conocimiento entre personajes..."
            )
            _run_enrichment(
                db,
                project_id,
                "character_knowledge",
                10,
                lambda: _compute_character_knowledge(
                    project_id,
                    entities,
                    chapters,
                    extraction_mode=knowledge_mode,
                ),
                "character_knowledge",
            )
        else:
            tracker.update_progress(
                phase_key, step / total_steps, "Conocimiento de personajes omitido"
            )

    except Exception as e:
        logger.error(f"[Phase 10] Relationships enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_character_network(db, project_id, entities, chapters):
    """Compute character network metrics (centrality, bridges, clustering)."""
    from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)
    entity_names = {}
    cooccurrences = []
    PROXIMITY_WINDOW = 500

    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        entity_names[entity.id] = entity.canonical_name

    # Build co-occurrence matrix from mentions
    for ch in chapters:
        ch_mentions = []
        for eid in entity_names:
            mentions = entity_repo.get_mentions_by_entity(eid)
            for m in mentions:
                if hasattr(m, "chapter_id") and m.chapter_id and hasattr(ch, "id"):
                    if m.chapter_id == ch.id:
                        ch_mentions.append((eid, getattr(m, "start_char", 0) or 0))
                elif hasattr(m, "start_char"):
                    ch_mentions.append((eid, getattr(m, "start_char", 0) or 0))

        ch_mentions.sort(key=lambda x: x[1])
        for i, (eid1, pos1) in enumerate(ch_mentions):
            for j in range(i + 1, len(ch_mentions)):
                eid2, pos2 = ch_mentions[j]
                if pos2 - pos1 > PROXIMITY_WINDOW:
                    break
                if eid1 != eid2:
                    cooccurrences.append(
                        {
                            "entity1_id": eid1,
                            "entity2_id": eid2,
                            "chapter": ch.chapter_number,
                            "distance_chars": pos2 - pos1,
                        }
                    )

    analyzer = CharacterNetworkAnalyzer()
    report = analyzer.analyze(cooccurrences, entity_names, len(chapters))
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_character_timeline(db, project_id, entities, chapters):
    """Build character timeline (appearances per chapter)."""
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)
    # chapter_map omitted — ch_number_map sufficient for current usage
    ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}

    characters = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue

        mentions = entity_repo.get_mentions_by_entity(entity.id)
        ch_counts: dict[int, int] = {}
        for m in mentions:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            ch_counts[ch_num] = ch_counts.get(ch_num, 0) + 1

        if not ch_counts:
            continue

        appearances = [
            {"chapter": ch_num, "mentions": count} for ch_num, count in sorted(ch_counts.items())
        ]

        characters.append(
            {
                "entity_id": entity.id,
                "name": entity.canonical_name,
                "entity_type": etype,
                "importance": getattr(entity, "importance", None),
                "total_mentions": sum(ch_counts.values()),
                "chapters_present": len(ch_counts),
                "first_chapter": min(ch_counts.keys()),
                "last_chapter": max(ch_counts.keys()),
                "appearances": appearances,
            }
        )

    characters.sort(key=lambda c: c["total_mentions"], reverse=True)

    return {
        "characters": characters,
        "chapters": [{"number": ch.chapter_number, "title": ch.title} for ch in chapters],
        "total_chapters": len(chapters),
    }


def _compute_character_profiles(db, project_id, entities, chapters):
    """Compute 6-indicator character profiles."""
    from narrative_assistant.analysis.character_profiling import CharacterProfiler
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)

    # Build mentions list and chapter_texts
    mentions_list = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}
        ems = entity_repo.get_mentions_by_entity(entity.id)
        for m in ems:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            mentions_list.append(
                {
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "chapter": ch_num,
                }
            )

    chapter_texts = {ch.chapter_number: (ch.content or "") for ch in chapters}

    profiler = CharacterProfiler()
    profiles = profiler.build_profiles(mentions_list, chapter_texts)

    return {
        "profiles": [p.to_dict() if hasattr(p, "to_dict") else p for p in profiles],
        "count": len(profiles),
    }


def _compute_emotional_analysis(chapters, character_entities):
    """Compute emotional coherence analysis."""
    from narrative_assistant.analysis.emotional_coherence import get_emotional_coherence_checker
    from narrative_assistant.nlp.dialogue import detect_dialogues

    checker = get_emotional_coherence_checker()
    character_names = [e.canonical_name for e in character_entities]

    all_incoherences = []
    chapters_analyzed = 0

    for ch in chapters:
        content = ch.content or ""
        if len(content) < 50:
            continue
        try:
            dialogues = detect_dialogues(content)
            result = checker.analyze_chapter(content, ch.chapter_number, character_names, dialogues)
            if hasattr(result, "incoherences"):
                for inc in result.incoherences:
                    d = inc.to_dict() if hasattr(inc, "to_dict") else inc
                    if isinstance(d, dict):
                        d["chapter_id"] = ch.chapter_number
                    all_incoherences.append(d)
            chapters_analyzed += 1
        except Exception as e:
            logger.warning(f"Emotional analysis failed for chapter {ch.chapter_number}: {e}")

    return {
        "incoherences": all_incoherences,
        "stats": {
            "total": len(all_incoherences),
            "chapters_analyzed": chapters_analyzed,
        },
    }


def _compute_character_archetypes(db, project_id, entities, chapters, chapters_dicts):
    """Compute character archetypes (basic mode — no LLM)."""
    from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
    from narrative_assistant.analysis.character_archetypes import CharacterArchetypeAnalyzer
    from narrative_assistant.analysis.character_profiling import CharacterProfiler
    from narrative_assistant.entities.repository import get_entity_repository
    from narrative_assistant.relationships.repository import get_relationship_repository

    # Use basic mode to avoid LLM dependency
    progress_result = analyze_chapter_progress(project_id, mode="basic")

    if hasattr(progress_result, "is_failure") and progress_result.is_failure:
        return {"characters": [], "archetype_distribution": {}}

    progress_data = progress_result.value if hasattr(progress_result, "value") else progress_result
    character_arcs = (
        progress_data.get("character_arcs", []) if isinstance(progress_data, dict) else []
    )

    # Get relationships
    rel_repo = get_relationship_repository(db)
    relationships = rel_repo.get_by_project(project_id)
    rel_dicts = [r.to_dict() if hasattr(r, "to_dict") else r for r in relationships]

    # Get profiles
    entity_repo = get_entity_repository(db)
    ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}
    mentions_list = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        ems = entity_repo.get_mentions_by_entity(entity.id)
        for m in ems:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            mentions_list.append(
                {
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "chapter": ch_num,
                }
            )

    chapter_texts = {ch.chapter_number: (ch.content or "") for ch in chapters}
    profiler = CharacterProfiler()
    profiles = profiler.build_profiles(mentions_list, chapter_texts)

    entities_data = _entities_to_dicts(entities)

    analyzer = CharacterArchetypeAnalyzer()
    report = analyzer.analyze(
        entities_data=entities_data,
        character_arcs=character_arcs,
        relationships=rel_dicts,
        profiles=[p.to_dict() if hasattr(p, "to_dict") else p for p in profiles],
        total_chapters=len(chapters),
    )

    return report.to_dict() if hasattr(report, "to_dict") else report


def _resolve_character_knowledge_mode(ctx: dict):
    """Resolve knowledge extraction mode from selected NLP methods with safe fallback."""
    from narrative_assistant.analysis.character_knowledge import KnowledgeExtractionMode

    selected_nlp_methods = ctx.get("selected_nlp_methods", {})
    analysis_config = ctx.get("analysis_config")
    methods: list[str] = []

    if isinstance(selected_nlp_methods, dict):
        raw_methods = selected_nlp_methods.get("character_knowledge")
        if isinstance(raw_methods, list):
            methods = [
                m.strip().lower()
                for m in raw_methods
                if isinstance(m, str) and m.strip()
            ]

    mode = KnowledgeExtractionMode.RULES
    if methods:
        if "hybrid" in methods:
            mode = KnowledgeExtractionMode.HYBRID
        elif "llm" in methods:
            mode = KnowledgeExtractionMode.LLM
        elif "rules" in methods:
            mode = KnowledgeExtractionMode.RULES

    llm_enabled = not analysis_config or bool(getattr(analysis_config, "use_llm", True))
    if mode in (KnowledgeExtractionMode.LLM, KnowledgeExtractionMode.HYBRID) and not llm_enabled:
        logger.info(
            "Character knowledge mode '%s' requested but use_llm=False; fallback to rules",
            mode.value,
        )
        return KnowledgeExtractionMode.RULES

    return mode


def _compute_character_knowledge(project_id, entities, chapters, extraction_mode=None):
    """Compute character knowledge using selected extraction mode."""
    from narrative_assistant.analysis.character_knowledge import (
        CharacterKnowledgeAnalyzer,
        KnowledgeExtractionMode,
    )

    analyzer = CharacterKnowledgeAnalyzer()
    mode = extraction_mode or KnowledgeExtractionMode.RULES
    character_entities = [
        e
        for e in entities
        if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
        in ("character", "animal", "creature")
    ]

    for ch in chapters:
        try:
            analyzer.analyze_narration(
                ch.content or "",
                ch.chapter_number,
                0,  # start_char
                extraction_mode=mode,
            )
        except Exception as e:
            logger.warning(f"Knowledge extraction failed for chapter {ch.chapter_number}: {e}")

    all_knowledge = analyzer.get_all_knowledge()
    knowledge_dicts = [k.to_dict() if hasattr(k, "to_dict") else k for k in all_knowledge]

    return {
        "project_id": project_id,
        "knowledge_facts": knowledge_dicts,
        "total_facts": len(knowledge_dicts),
        "characters_analyzed": len(character_entities),
        "chapters_analyzed": len(chapters),
        "extraction_mode": mode.value if hasattr(mode, "value") else str(mode),
    }


# ============================================================================
# Phase 11: Voice enrichment
# ============================================================================


def run_voice_enrichment(ctx: dict, tracker) -> None:
    """Phase 11: Pre-compute voice-related analysis."""
    phase_key = "voice"
    phase_index = 10

    tracker.start_phase(phase_key, phase_index, "Perfilando voces de personajes...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        dialogues = _detect_all_dialogues(chapters)

        character_entities = [
            e
            for e in entities
            if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
            in ("character", "animal", "creature")
        ]

        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": getattr(e, "aliases", []) or []}
            for e in character_entities
        ]

        total_steps = 4
        step = 0

        # --- 11a: Voice Profiles ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Construyendo perfiles de voz...")
        profiles_result = None

        def compute_voice_profiles():
            nonlocal profiles_result
            from narrative_assistant.voice.profiles import VoiceProfileBuilder

            builder = VoiceProfileBuilder()
            profiles = builder.build_profiles(dialogues, entity_data)
            profiles_result = profiles
            return [p.to_dict() if hasattr(p, "to_dict") else p for p in profiles]

        _run_enrichment(
            db, project_id, "voice_profiles", 11, compute_voice_profiles, "voice_profiles"
        )

        # --- 11b: Voice Deviations ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Detectando desviaciones de voz...")
        if profiles_result:
            _run_enrichment(
                db,
                project_id,
                "voice_deviations",
                11,
                lambda: _compute_voice_deviations(profiles_result, dialogues),
                "voice_deviations",
            )

        # --- 11c: Register Analysis ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Analizando registro lingüístico...")
        _run_enrichment(
            db,
            project_id,
            "register_analysis",
            11,
            lambda: _compute_register_analysis(chapters, dialogues),
            "register_analysis",
        )

        # --- 11d: Focalization Violations ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Verificando focalización...")
        _run_enrichment(
            db,
            project_id,
            "focalization_violations",
            11,
            lambda: _compute_focalization_violations(db, project_id, chapters, character_entities),
            "focalization_violations",
        )

    except Exception as e:
        logger.error(f"[Phase 11] Voice enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_voice_deviations(profiles, dialogues):
    """Compute voice deviations from baseline profiles."""
    from narrative_assistant.voice.deviations import VoiceDeviationDetector

    detector = VoiceDeviationDetector()
    deviations = detector.detect_deviations(profiles, dialogues)
    return [d.to_dict() if hasattr(d, "to_dict") else d for d in deviations]


def _compute_register_analysis(chapters, dialogues):
    """Compute register/formality analysis."""
    from narrative_assistant.voice.register import RegisterChangeDetector

    # Build segments from chapters
    segments = []
    dialogue_positions = set()
    for d in dialogues:
        dialogue_positions.add((d["chapter"], d["start_char"]))

    for ch in chapters:
        content = ch.content or ""
        # Split into paragraphs as segments
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        offset = 0
        for para in paragraphs:
            pos = content.find(para, offset)
            if pos == -1:
                pos = offset
            is_dialogue = para.startswith(("—", "–", "-", "«", '"'))
            segments.append((para, ch.chapter_number, pos, is_dialogue))
            offset = pos + len(para)

    detector = RegisterChangeDetector()
    detector.analyze_document(segments)
    changes = detector.detect_changes(min_severity="medium")
    summary = detector.get_summary()

    return {
        "changes": [c.to_dict() if hasattr(c, "to_dict") else c for c in changes],
        "summary": summary
        if isinstance(summary, dict)
        else (summary.to_dict() if hasattr(summary, "to_dict") else {}),
        "total_segments": len(segments),
    }


def _compute_focalization_violations(db, project_id, chapters, character_entities):
    """Compute focalization violations."""
    from narrative_assistant.focalization import (
        FocalizationDeclarationService,
        FocalizationViolationDetector,
        SQLiteFocalizationRepository,
    )

    repo = SQLiteFocalizationRepository(db)
    service = FocalizationDeclarationService(repo)
    characters = [e.canonical_name for e in character_entities]
    detector = FocalizationViolationDetector(service, characters)

    all_violations = []
    for ch in chapters:
        try:
            violations = detector.detect_violations(project_id, ch.content or "", ch.chapter_number)
            for v in violations:
                all_violations.append(v.to_dict() if hasattr(v, "to_dict") else v)
        except Exception as e:
            logger.warning(f"Focalization check failed for chapter {ch.chapter_number}: {e}")

    return {
        "violations": all_violations,
        "total": len(all_violations),
        "chapters_analyzed": len(chapters),
    }


# ============================================================================
# Phase 12: Prose enrichment
# ============================================================================


def run_prose_enrichment(ctx: dict, tracker) -> None:
    """Phase 12: Pre-compute prose/style analysis."""
    phase_key = "prose"
    phase_index = 11

    tracker.start_phase(phase_key, phase_index, "Evaluando estilo de escritura...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    # CR-05: capítulos modificados para caching granular
    inc_plan = ctx.get("incremental_plan") or {}
    changed_ch = inc_plan.get("changed_chapter_numbers")

    try:
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        full_text = _build_full_text(chapters)

        total_steps = 10
        step = 0

        # --- 12a: Sticky Sentences (chapter-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Detectando frases pegajosas...")
        _run_chapter_scoped_enrichment(
            db, project_id, "sticky_sentences", 12,
            chapters, changed_ch,
            _compute_sticky_for_chapter, _merge_sticky,
            "sticky_sentences", ctx=ctx,
        )

        # --- 12b: Sentence Energy (chapter-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Midiendo energía narrativa...")
        _run_chapter_scoped_enrichment(
            db, project_id, "sentence_energy", 12,
            chapters, changed_ch,
            _compute_energy_for_chapter, _merge_energy,
            "sentence_energy", ctx=ctx,
        )

        # --- 12c: Echo Report (chapter-scoped, lexical only) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Buscando repeticiones...")
        _run_chapter_scoped_enrichment(
            db, project_id, "echo_report", 12,
            chapters, changed_ch,
            _compute_echo_for_chapter, _merge_echo,
            "echo_report", ctx=ctx,
        )

        # --- 12d: Pacing Analysis (chapter-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Analizando ritmo narrativo...")
        _run_chapter_scoped_enrichment(
            db, project_id, "pacing_analysis", 12,
            chapters, changed_ch,
            _compute_pacing_for_chapter, _merge_pacing,
            "pacing_analysis", ctx=ctx,
        )

        # --- 12e: Tension Curve (cross-chapter, global) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Trazando curva de tensión...")
        _run_enrichment(
            db, project_id, "tension_curve", 12,
            lambda: _compute_tension_curve(chapters_dicts, full_text),
            "tension_curve",
        )

        # --- 12f: Sensory Report (cross-chapter, global) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Evaluando detalles sensoriales...")
        _run_enrichment(
            db, project_id, "sensory_report", 12,
            lambda: _compute_sensory_report(full_text, chapters_dicts),
            "sensory_report",
        )

        # --- 12g: Age Readability (global, full text) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Calculando legibilidad...")
        _run_enrichment(
            db, project_id, "age_readability", 12,
            lambda: _compute_readability(full_text),
            "age_readability",
        )

        # --- 12h: Sentence Variation (chapter-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Analizando variación sintáctica...")
        _run_chapter_scoped_enrichment(
            db, project_id, "sentence_variation", 12,
            chapters, changed_ch,
            _compute_variation_for_chapter, _merge_variation,
            "sentence_variation", ctx=ctx,
        )

        # --- 12i: Dialogue Validation (chapter-scoped) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Validando diálogos...")
        _run_chapter_scoped_enrichment(
            db, project_id, "dialogue_validation", 12,
            chapters, changed_ch,
            _compute_dialogue_for_chapter, _merge_dialogue,
            "dialogue_validation", ctx=ctx,
        )

        # --- 12j: Narrative Structure (cross-chapter, global) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Detectando estructura narrativa...")
        _run_enrichment(
            db, project_id, "narrative_structure", 12,
            lambda: _compute_narrative_structure(full_text, chapters_dicts),
            "narrative_structure",
        )

    except Exception as e:
        logger.error(f"[Phase 12] Prose enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_sticky_sentences(chapters):
    """Compute sticky (high glue word %) sentences."""
    from narrative_assistant.nlp.style.sticky_sentences import get_sticky_sentence_detector

    detector = get_sticky_sentence_detector()
    all_sticky = []
    stats = {"total_sentences": 0, "total_sticky": 0}
    for ch in chapters:
        report = detector.analyze(ch.content or "", threshold=0.45)
        if hasattr(report, "sticky_sentences"):
            for s in report.sticky_sentences:
                d = s.to_dict() if hasattr(s, "to_dict") else s
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_sticky.append(d)
        stats["total_sentences"] += getattr(report, "total_sentences", 0)
        stats["total_sticky"] += len(getattr(report, "sticky_sentences", []))
    return {"sticky_sentences": all_sticky, "stats": stats}


def _compute_sentence_energy(chapters):
    """Compute sentence energy (passive voice, weak verbs)."""
    from narrative_assistant.nlp.style.sentence_energy import get_sentence_energy_detector

    detector = get_sentence_energy_detector()
    all_low = []
    stats = {"avg_energy": 0, "chapters": 0}
    energy_sum = 0
    for ch in chapters:
        report = detector.analyze(ch.content or "", chapter=ch.chapter_number)
        if hasattr(report, "low_energy_sentences"):
            for s in report.low_energy_sentences:
                d = s.to_dict() if hasattr(s, "to_dict") else s
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_low.append(d)
        energy_sum += getattr(report, "avg_energy", 0.5)
        stats["chapters"] += 1
    stats["avg_energy"] = energy_sum / max(stats["chapters"], 1)
    return {"low_energy_sentences": all_low, "stats": stats}


def _compute_echo_report(chapters):
    """Compute lexical repetitions (no semantic to avoid embedding cost)."""
    from narrative_assistant.nlp.style.repetition_detector import get_repetition_detector

    detector = get_repetition_detector()
    all_repetitions = []
    for ch in chapters:
        report = detector.detect_lexical(ch.content or "", min_distance=3)
        if hasattr(report, "repetitions"):
            for r in report.repetitions:
                d = r.to_dict() if hasattr(r, "to_dict") else r
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_repetitions.append(d)
    return {"repetitions": all_repetitions, "total": len(all_repetitions)}


def _compute_pacing_analysis(chapters_dicts):
    """Compute pacing metrics per chapter."""
    from narrative_assistant.analysis.pacing import get_pacing_analyzer

    analyzer = get_pacing_analyzer()
    result = analyzer.analyze(chapters_dicts)
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "chapter_metrics"):
        return {
            "chapter_metrics": [
                m.to_dict() if hasattr(m, "to_dict") else m for m in result.chapter_metrics
            ],
        }
    return result


def _compute_tension_curve(chapters_dicts, full_text):
    """Compute tension curve across chapters."""
    from narrative_assistant.analysis.pacing import compute_tension_curve

    result = compute_tension_curve(chapters_dicts, full_text)
    return result.to_dict() if hasattr(result, "to_dict") else result


def _compute_sensory_report(full_text, chapters_dicts):
    """Compute sensory details analysis (5 senses)."""
    from narrative_assistant.nlp.style.sensory_report import get_sensory_analyzer

    analyzer = get_sensory_analyzer()
    report = analyzer.analyze(full_text, chapters=chapters_dicts)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_readability(full_text):
    """Compute age-readability analysis."""
    from narrative_assistant.nlp.style.readability import get_readability_analyzer

    analyzer = get_readability_analyzer()
    report = analyzer.analyze_for_age(full_text)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_sentence_variation(chapters):
    """Compute sentence length variation stats."""
    SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…]+")
    chapter_results = []
    all_lengths = []

    for ch in chapters:
        sentences = SENTENCE_RE.findall(ch.content or "")
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
        if not lengths:
            continue
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        std = variance**0.5
        cv = std / avg if avg > 0 else 0
        chapter_results.append(
            {
                "chapter": ch.chapter_number,
                "avg_length": round(avg, 1),
                "std_dev": round(std, 1),
                "variation_coefficient": round(cv, 3),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "sentence_count": len(lengths),
            }
        )
        all_lengths.extend(lengths)

    global_avg = sum(all_lengths) / len(all_lengths) if all_lengths else 0
    global_var = (
        sum((l - global_avg) ** 2 for l in all_lengths) / len(all_lengths) if all_lengths else 0
    )
    global_std = global_var**0.5
    global_cv = global_std / global_avg if global_avg > 0 else 0

    return {
        "global_stats": {
            "avg_length": round(global_avg, 1),
            "std_dev": round(global_std, 1),
            "variation_coefficient": round(global_cv, 3),
            "min_length": min(all_lengths) if all_lengths else 0,
            "max_length": max(all_lengths) if all_lengths else 0,
            "total_sentences": len(all_lengths),
        },
        "chapters": chapter_results,
    }


def _compute_dialogue_validation(chapters):
    """Validate dialogue attribution."""
    from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

    validator = DialogueContextValidator()
    chapters_info = [
        {"number": ch.chapter_number, "start_char": 0, "content": ch.content or ""}
        for ch in chapters
    ]
    report = validator.validate_all(chapters_info)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_narrative_structure(full_text, chapters_dicts):
    """Detect prolepsis/analepsis in narrative."""
    from narrative_assistant.analysis.narrative_structure import get_narrative_structure_detector

    detector = get_narrative_structure_detector()
    report = detector.detect_all(full_text, chapters_dicts, min_confidence=0.5)
    return report.to_dict() if hasattr(report, "to_dict") else report


# ============================================================================
# CR-05: Per-chapter compute & merge functions for chapter-scoped caching
# ============================================================================

def _compute_sticky_for_chapter(ch):
    """Compute sticky sentences para un solo capítulo."""
    from narrative_assistant.nlp.style.sticky_sentences import get_sticky_sentence_detector
    detector = get_sticky_sentence_detector()
    report = detector.analyze(ch.content or "", threshold=0.45)
    items = []
    for s in getattr(report, "sticky_sentences", []):
        d = s.to_dict() if hasattr(s, "to_dict") else s
        if isinstance(d, dict):
            d["chapter"] = ch.chapter_number
        items.append(d)
    return {
        "sticky_sentences": items,
        "total_sentences": getattr(report, "total_sentences", 0),
        "total_sticky": len(items),
    }


def _merge_sticky(per_ch: dict[int, dict]) -> dict:
    all_sticky, total_s, total_st = [], 0, 0
    for ch_num in sorted(per_ch):
        r = per_ch[ch_num]
        all_sticky.extend(r.get("sticky_sentences", []))
        total_s += r.get("total_sentences", 0)
        total_st += r.get("total_sticky", 0)
    return {"sticky_sentences": all_sticky, "stats": {"total_sentences": total_s, "total_sticky": total_st}}


def _compute_energy_for_chapter(ch):
    """Compute sentence energy para un solo capítulo."""
    from narrative_assistant.nlp.style.sentence_energy import get_sentence_energy_detector
    detector = get_sentence_energy_detector()
    report = detector.analyze(ch.content or "", chapter=ch.chapter_number)
    items = []
    for s in getattr(report, "low_energy_sentences", []):
        d = s.to_dict() if hasattr(s, "to_dict") else s
        if isinstance(d, dict):
            d["chapter"] = ch.chapter_number
        items.append(d)
    return {
        "low_energy_sentences": items,
        "avg_energy": getattr(report, "avg_energy", 0.5),
    }


def _merge_energy(per_ch: dict[int, dict]) -> dict:
    all_low, energy_sum, count = [], 0.0, 0
    for ch_num in sorted(per_ch):
        r = per_ch[ch_num]
        all_low.extend(r.get("low_energy_sentences", []))
        energy_sum += r.get("avg_energy", 0.5)
        count += 1
    avg = energy_sum / max(count, 1)
    return {"low_energy_sentences": all_low, "stats": {"avg_energy": avg, "chapters": count}}


def _compute_echo_for_chapter(ch):
    """Compute echo (lexical repetitions) para un solo capítulo."""
    from narrative_assistant.nlp.style.repetition_detector import get_repetition_detector
    detector = get_repetition_detector()
    report = detector.detect_lexical(ch.content or "", min_distance=3)
    items = []
    for r in getattr(report, "repetitions", []):
        d = r.to_dict() if hasattr(r, "to_dict") else r
        if isinstance(d, dict):
            d["chapter"] = ch.chapter_number
        items.append(d)
    return {"repetitions": items}


def _merge_echo(per_ch: dict[int, dict]) -> dict:
    all_reps = []
    for ch_num in sorted(per_ch):
        all_reps.extend(per_ch[ch_num].get("repetitions", []))
    return {"repetitions": all_reps, "total": len(all_reps)}


def _compute_variation_for_chapter(ch):
    """Compute sentence variation para un solo capítulo."""
    SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…]+")
    sentences = SENTENCE_RE.findall(ch.content or "")
    lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
    if not lengths:
        return {"lengths": [], "chapter": ch.chapter_number}
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std = variance**0.5
    cv = std / avg if avg > 0 else 0
    return {
        "chapter_result": {
            "chapter": ch.chapter_number,
            "avg_length": round(avg, 1),
            "std_dev": round(std, 1),
            "variation_coefficient": round(cv, 3),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "sentence_count": len(lengths),
        },
        "lengths": lengths,
    }


def _merge_variation(per_ch: dict[int, dict]) -> dict:
    chapter_results, all_lengths = [], []
    for ch_num in sorted(per_ch):
        r = per_ch[ch_num]
        if r.get("chapter_result"):
            chapter_results.append(r["chapter_result"])
        all_lengths.extend(r.get("lengths", []))
    g_avg = sum(all_lengths) / len(all_lengths) if all_lengths else 0
    g_var = sum((l - g_avg) ** 2 for l in all_lengths) / len(all_lengths) if all_lengths else 0
    g_std = g_var**0.5
    g_cv = g_std / g_avg if g_avg > 0 else 0
    return {
        "global_stats": {
            "avg_length": round(g_avg, 1), "std_dev": round(g_std, 1),
            "variation_coefficient": round(g_cv, 3),
            "min_length": min(all_lengths) if all_lengths else 0,
            "max_length": max(all_lengths) if all_lengths else 0,
            "total_sentences": len(all_lengths),
        },
        "chapters": chapter_results,
    }


def _compute_pacing_for_chapter(ch):
    """Compute pacing para un solo capítulo."""
    from narrative_assistant.analysis.pacing import get_pacing_analyzer
    analyzer = get_pacing_analyzer()
    ch_dict = {"chapter_number": ch.chapter_number, "content": ch.content or "", "title": ch.title or ""}
    result = analyzer.analyze([ch_dict])
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "chapter_metrics") and result.chapter_metrics:
        m = result.chapter_metrics[0]
        return m.to_dict() if hasattr(m, "to_dict") else m
    return result if isinstance(result, dict) else {}


def _merge_pacing(per_ch: dict[int, dict]) -> dict:
    metrics = [per_ch[ch_num] for ch_num in sorted(per_ch) if per_ch[ch_num]]
    return {"chapter_metrics": metrics}


def _compute_dialogue_for_chapter(ch):
    """Compute dialogue validation para un solo capítulo."""
    from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator
    validator = DialogueContextValidator()
    ch_info = [{"number": ch.chapter_number, "start_char": 0, "content": ch.content or ""}]
    report = validator.validate_all(ch_info)
    return report.to_dict() if hasattr(report, "to_dict") else (report if isinstance(report, dict) else {})


def _merge_dialogue(per_ch: dict[int, dict]) -> dict:
    # DialogueContextValidator.validate_all returns a combined report.
    # For per-chapter, merge issues/warnings.
    all_issues = []
    for ch_num in sorted(per_ch):
        r = per_ch[ch_num]
        all_issues.extend(r.get("issues", []))
        all_issues.extend(r.get("warnings", []))
    return {"issues": all_issues, "total": len(all_issues)}


# ============================================================================
# CR-05 Capa 3: Per-entity compute & merge for entity-scoped caching
# ============================================================================


def _compute_timeline_for_entity(entity, *, _shared=None):
    """Compute timeline para una sola entidad.

    _shared debe contener: db, ch_number_map, chapters.
    Se inyecta via functools.partial en run_relationships_enrichment.
    """
    from narrative_assistant.entities.repository import get_entity_repository

    db = _shared["db"]
    ch_number_map = _shared["ch_number_map"]

    etype = (
        entity.entity_type.value
        if hasattr(entity.entity_type, "value")
        else str(entity.entity_type)
    )
    if etype not in ("character", "animal", "creature"):
        return {}

    entity_repo = get_entity_repository(db)
    mentions = entity_repo.get_mentions_by_entity(entity.id)
    ch_counts: dict[int, int] = {}
    for m in mentions:
        ch_id = getattr(m, "chapter_id", None)
        ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
        ch_counts[ch_num] = ch_counts.get(ch_num, 0) + 1

    if not ch_counts:
        return {}

    appearances = [
        {"chapter": ch_num, "mentions": count}
        for ch_num, count in sorted(ch_counts.items())
    ]
    return {
        "entity_id": entity.id,
        "name": entity.canonical_name,
        "entity_type": etype,
        "importance": getattr(entity, "importance", None),
        "total_mentions": sum(ch_counts.values()),
        "chapters_present": len(ch_counts),
        "first_chapter": min(ch_counts.keys()),
        "last_chapter": max(ch_counts.keys()),
        "appearances": appearances,
    }


def _merge_timeline(per_ent: dict[int, dict], *, chapters=None) -> dict:
    """Merge per-entity timeline results en resultado global."""
    characters = [v for v in per_ent.values() if v]
    characters.sort(key=lambda c: c.get("total_mentions", 0), reverse=True)
    ch_list = []
    total_ch = 0
    if chapters is not None:
        ch_list = [{"number": ch.chapter_number, "title": ch.title} for ch in chapters]
        total_ch = len(chapters)
    return {
        "characters": characters,
        "chapters": ch_list,
        "total_chapters": total_ch,
    }


# ============================================================================
# Phase 13: Health enrichment
# ============================================================================


def run_health_enrichment(ctx: dict, tracker) -> None:
    """Phase 13: Pre-compute narrative health analysis."""
    phase_key = "health"
    phase_index = 12

    tracker.start_phase(phase_key, phase_index, "Evaluando salud narrativa...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        entities_dicts = _entities_to_dicts(entities)

        total_steps = 3
        step = 0

        # --- 13a: Chapter Progress (standard mode — LLM per chapter) ---
        step += 1
        tracker.update_progress(
            phase_key, step / total_steps, "Analizando progreso por capítulo (LLM)..."
        )
        progress_data = None

        def compute_chapter_progress():
            nonlocal progress_data
            from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
            from routers._llm_helpers import get_default_llm_model
            _model = get_default_llm_model()
            result = analyze_chapter_progress(project_id, mode="standard", llm_model=_model)
            if hasattr(result, "is_failure") and result.is_failure:
                raise RuntimeError(f"Chapter progress failed: {result.error}")
            data = result.value if hasattr(result, "value") else result
            progress_data = data
            return data.to_dict() if hasattr(data, "to_dict") else data

        _run_enrichment(
            db, project_id, "chapter_progress", 13, compute_chapter_progress, "chapter_progress"
        )

        # --- 13b: Narrative Templates ---
        step += 1
        tracker.update_progress(
            phase_key, step / total_steps, "Comparando con plantillas narrativas..."
        )
        if progress_data is not None:
            _run_enrichment(
                db,
                project_id,
                "narrative_templates",
                13,
                lambda: _compute_narrative_templates(progress_data, chapters_dicts, len(chapters)),
                "narrative_templates",
            )

        # --- 13c: Narrative Health (12 dimensions) ---
        step += 1
        tracker.update_parallel_progress(phase_key, step / total_steps, "Calculando puntuación de salud...")
        if progress_data is not None:
            _run_enrichment(
                db,
                project_id,
                "narrative_health",
                13,
                lambda: _compute_narrative_health(
                    progress_data, chapters_dicts, entities_dicts, len(chapters)
                ),
                "narrative_health",
            )

    except Exception as e:
        logger.error(f"[Phase 13] Health enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_narrative_templates(progress_data, chapters_dicts, total_chapters):
    """Match narrative against known templates (3 Acts, Hero's Journey, etc.)."""
    from narrative_assistant.analysis.narrative_templates import NarrativeTemplateAnalyzer

    analyzer = NarrativeTemplateAnalyzer()

    # Extract chapters_data from progress_data
    pd = (
        progress_data
        if isinstance(progress_data, dict)
        else (progress_data.to_dict() if hasattr(progress_data, "to_dict") else {})
    )
    ch_data = pd.get("chapters", chapters_dicts)

    report = analyzer.analyze(ch_data, total_chapters)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_narrative_health(progress_data, chapters_dicts, entities_dicts, total_chapters):
    """Compute 12-dimension narrative health check."""
    from narrative_assistant.analysis.narrative_health import NarrativeHealthChecker

    checker = NarrativeHealthChecker()

    pd = (
        progress_data
        if isinstance(progress_data, dict)
        else (progress_data.to_dict() if hasattr(progress_data, "to_dict") else {})
    )
    character_arcs = pd.get("character_arcs", [])
    chekhov_elements = pd.get("chekhov_elements", [])
    abandoned_threads = pd.get("abandoned_threads", [])
    ch_data = pd.get("chapters", chapters_dicts)

    report = checker.check(
        chapters_data=ch_data,
        total_chapters=total_chapters,
        entities_data=entities_dicts,
        character_arcs=character_arcs,
        chekhov_elements=chekhov_elements,
        abandoned_threads=abandoned_threads,
    )
    return report.to_dict() if hasattr(report, "to_dict") else report


# ============================================================================
# S15: Version metrics (post-Phase 13 hook)
# ============================================================================


def write_version_metrics(ctx: dict) -> int | None:
    """S15-03: Persist aggregated metrics for this analysis as a version.

    Called after Phase 13 completes. Reads metrics from enrichment_cache
    and analysis context to build a version_metrics row.
    """
    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        with db.connection() as conn:
            # Determine next version_num for this project
            row = conn.execute(
                "SELECT COALESCE(MAX(version_num), 0) FROM version_metrics WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            next_version = (row[0] if row else 0) + 1

            # Get latest snapshot_id (if any)
            snap_row = conn.execute(
                "SELECT id FROM analysis_snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            snapshot_id = snap_row[0] if snap_row else None

            # Alert count (open alerts)
            alert_row = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = ? AND status != 'resolved'",
                (project_id,),
            ).fetchone()
            alert_count = alert_row[0] if alert_row else 0
            severity_rows = conn.execute(
                """
                SELECT severity, COUNT(*) AS cnt
                FROM alerts
                WHERE project_id = ? AND status != 'resolved'
                GROUP BY severity
                """,
                (project_id,),
            ).fetchall()
            severity_counts = {str(r[0] or "").lower(): int(r[1]) for r in severity_rows}
            critical_count = severity_counts.get("critical", 0) + severity_counts.get("high", 0)
            warning_count = severity_counts.get("warning", 0) + severity_counts.get("medium", 0)
            info_count = severity_counts.get("info", 0) + severity_counts.get("low", 0)

            # Word count + chapter count from project
            proj_row = conn.execute(
                "SELECT word_count, chapter_count FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            word_count = proj_row[0] if proj_row else ctx.get("word_count", 0)
            chapter_count = proj_row[1] if proj_row else ctx.get("chapters_count", 0)

            # Entity count
            entity_row = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            entity_count = entity_row[0] if entity_row else 0

            # Health score from enrichment_cache (narrative_health)
            health_score = None
            health_row = conn.execute(
                """SELECT result_json FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = 'narrative_health'
                   AND status = 'completed' LIMIT 1""",
                (project_id,),
            ).fetchone()
            if health_row and health_row[0]:
                try:
                    health_data = json.loads(health_row[0])
                    health_score = health_data.get("overall_score") or health_data.get(
                        "health_score"
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

            # Formality avg from enrichment_cache (register_analysis)
            formality_avg = None
            reg_row = conn.execute(
                """SELECT result_json FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = 'register_analysis'
                   AND status = 'completed' LIMIT 1""",
                (project_id,),
            ).fetchone()
            if reg_row and reg_row[0]:
                try:
                    reg_data = json.loads(reg_row[0])
                    summary = reg_data.get("summary", {})
                    formality_avg = summary.get("avg_formality") or summary.get("formality_avg")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Dialogue ratio — average across chapters
            dialogue_ratio = None
            dr_rows = conn.execute(
                "SELECT dialogue_ratio FROM chapters WHERE project_id = ? AND dialogue_ratio IS NOT NULL",
                (project_id,),
            ).fetchall()
            if dr_rows:
                dialogue_ratio = sum(r[0] for r in dr_rows) / len(dr_rows)

            prev_snapshot_id = ctx.get("pre_analysis_snapshot_id")
            alerts_new_count = 0
            alerts_resolved_count = 0
            alerts_unchanged_count = 0
            if prev_snapshot_id:
                prev_alerts = conn.execute(
                    """
                    SELECT content_hash FROM snapshot_alerts
                    WHERE snapshot_id = ?
                    """,
                    (prev_snapshot_id,),
                ).fetchall()
                current_alerts = conn.execute(
                    """
                    SELECT content_hash FROM alerts
                    WHERE project_id = ? AND status != 'resolved'
                    """,
                    (project_id,),
                ).fetchall()
                prev_set = {str(r[0]) for r in prev_alerts if r[0]}
                current_set = {str(r[0]) for r in current_alerts if r[0]}
                if prev_set or current_set:
                    alerts_new_count = len(current_set - prev_set)
                    alerts_resolved_count = len(prev_set - current_set)
                    alerts_unchanged_count = len(current_set & prev_set)

            chapter_diff = ctx.get("version_chapter_diff", {}) or {}
            entity_diff = ctx.get("version_entity_diff", {}) or {}
            phase_durations_json = json.dumps(
                ctx.get("phase_durations_json", {}), ensure_ascii=False, sort_keys=True
            )
            run_mode = str(ctx.get("run_mode") or "full")
            duration_total_sec = float(ctx.get("duration_total_sec") or 0.0)

            conn.execute(
                """INSERT OR REPLACE INTO version_metrics
                   (project_id, version_num, snapshot_id, alert_count, word_count,
                    entity_count, chapter_count, health_score, formality_avg, dialogue_ratio,
                    alerts_new_count, alerts_resolved_count, alerts_unchanged_count,
                    critical_count, warning_count, info_count,
                    entities_new_count, entities_removed_count, entities_renamed_count,
                    chapter_added_count, chapter_removed_count, chapter_reordered_count,
                    run_mode, duration_total_sec, phase_durations_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    next_version,
                    snapshot_id,
                    alert_count,
                    word_count,
                    entity_count,
                    chapter_count,
                    health_score,
                    formality_avg,
                    dialogue_ratio,
                    alerts_new_count,
                    alerts_resolved_count,
                    alerts_unchanged_count,
                    critical_count,
                    warning_count,
                    info_count,
                    int(entity_diff.get("new_entities", 0)),
                    int(entity_diff.get("removed_entities", 0)),
                    int(entity_diff.get("renamed", entity_diff.get("renamed_entities", 0))),
                    int(chapter_diff.get("added", 0)),
                    int(chapter_diff.get("removed", 0)),
                    0,  # chapter_reordered_count (pendiente de algoritmo dedicado)
                    run_mode,
                    duration_total_sec,
                    phase_durations_json,
                ),
            )
            conn.commit()

            logger.info(
                f"[S15] Version {next_version} metrics written for project {project_id}: "
                f"alerts={alert_count}, words={word_count}, health={health_score}"
            )
            return int(next_version)

    except Exception as e:
        logger.warning(f"[S15] Failed to write version metrics for project {project_id}: {e}")
    return None


def _hash_payload(payload: Any) -> str:
    """Hash estable para detectar si los inputs de una fase cambiaron."""
    try:
        packed = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        packed = str(payload)
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()[:16]
