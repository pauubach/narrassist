"""
Invalidación granular de enrichment cache (S8c).

Cuando una entidad se muta (merge, reject, edit attribute), este módulo:
1. Registra un invalidation_event
2. Marca como 'stale' las entradas de cache afectadas
3. Permite recompute selectivo por entity_id

Categorías de invalidación:
- Cat A (borrado): El dato ya no es válido → DELETE cache entry
- Cat B (stale): Se puede servir stale + recomputar en background
- Cat C (mark stale): Solo marcar, no recomputar automáticamente
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Mapeo de eventos a enrichment types afectados ──────────────────

# Tipos de enrichment que dependen de la identidad de entidades
ENTITY_DEPENDENT_TYPES = {
    "character_network",
    "character_profiles",
    "character_timeline",
    "character_archetypes",
    "character_knowledge",
    "emotional_arcs",
    "relationship_graph",
}

# Tipos que dependen de atributos de entidades
ATTRIBUTE_DEPENDENT_TYPES = {
    "character_profiles",
    "character_archetypes",
    "voice_profiles",
    "voice_deviations",
}

# Tipos que dependen de la lista de entidades (merge/reject cambian la lista)
ENTITY_LIST_DEPENDENT_TYPES = {
    "character_network",
    "relationship_graph",
    "character_timeline",
    "character_knowledge",
    "emotional_arcs",
    "character_archetypes",
    "character_profiles",
}

# Mapeo evento → tipos de enrichment a invalidar
EVENT_INVALIDATION_MAP: dict[str, set[str]] = {
    "merge": ENTITY_LIST_DEPENDENT_TYPES | ATTRIBUTE_DEPENDENT_TYPES,
    "undo_merge": ENTITY_LIST_DEPENDENT_TYPES | ATTRIBUTE_DEPENDENT_TYPES,
    "reject": ENTITY_LIST_DEPENDENT_TYPES,
    "attribute_create": ATTRIBUTE_DEPENDENT_TYPES,
    "attribute_edit": ATTRIBUTE_DEPENDENT_TYPES,
    "attribute_delete": ATTRIBUTE_DEPENDENT_TYPES,
}


def emit_invalidation_event(
    db_session,
    project_id: int,
    event_type: str,
    entity_ids: list[int],
    detail: dict | None = None,
) -> int:
    """
    Registra un evento de invalidación y marca cachés afectadas como stale.

    Args:
        db_session: Sesión de base de datos
        project_id: ID del proyecto
        event_type: Tipo de evento (merge, reject, attribute_edit, etc.)
        entity_ids: IDs de entidades afectadas
        detail: Detalles adicionales del evento

    Returns:
        revision: Número de revisión asignado al evento
    """
    try:
        with db_session.connection() as conn:
            # Obtener siguiente revisión para este proyecto
            row = conn.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM invalidation_events WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            revision = row[0] if row else 1

            # Registrar evento
            conn.execute(
                """
                INSERT INTO invalidation_events (project_id, event_type, entity_ids, detail, revision)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    event_type,
                    json.dumps(entity_ids),
                    json.dumps(detail) if detail else None,
                    revision,
                ),
            )

            # Marcar cachés afectadas como stale
            affected_types = EVENT_INVALIDATION_MAP.get(event_type, set())
            if affected_types:
                _mark_stale(conn, project_id, affected_types, entity_ids)

            conn.commit()

            logger.info(
                f"Invalidation event: {event_type} on project {project_id}, "
                f"entities={entity_ids}, revision={revision}, "
                f"stale_types={len(affected_types)}"
            )
            return revision

    except Exception as e:
        logger.warning(f"Failed to emit invalidation event: {e}")
        return 0


def _mark_stale(
    conn,
    project_id: int,
    enrichment_types: set[str],
    entity_ids: list[int],
) -> int:
    """
    Marca entradas de cache como 'stale' para los tipos afectados.

    Marca tanto entradas globales (entity_scope IS NULL) como per-entity.

    Returns:
        Número de filas afectadas
    """
    if not enrichment_types:
        return 0

    placeholders = ",".join("?" for _ in enrichment_types)
    types_list = list(enrichment_types)

    # Marcar entradas globales como stale
    result = conn.execute(
        f"""
        UPDATE enrichment_cache
        SET status = 'stale', updated_at = datetime('now')
        WHERE project_id = ?
          AND enrichment_type IN ({placeholders})
          AND status = 'completed'
          AND entity_scope IS NULL
        """,
        [project_id] + types_list,
    )
    affected = result.rowcount

    # Marcar entradas per-entity si hay entity_ids
    if entity_ids:
        entity_scopes = [f"entity:{eid}" for eid in entity_ids]
        scope_placeholders = ",".join("?" for _ in entity_scopes)
        result = conn.execute(
            f"""
            UPDATE enrichment_cache
            SET status = 'stale', updated_at = datetime('now')
            WHERE project_id = ?
              AND enrichment_type IN ({placeholders})
              AND status = 'completed'
              AND entity_scope IN ({scope_placeholders})
            """,
            [project_id] + types_list + entity_scopes,
        )
        affected += result.rowcount

    if affected > 0:
        logger.debug(f"Marked {affected} enrichment entries as stale")

    return affected


def get_project_revision(db_session, project_id: int) -> int:
    """Obtiene la última revisión de invalidación para un proyecto."""
    try:
        with db_session.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM invalidation_events WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def get_stale_enrichment_types(db_session, project_id: int) -> list[str]:
    """Obtiene los tipos de enrichment que están marcados como stale."""
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT enrichment_type
                FROM enrichment_cache
                WHERE project_id = ? AND status = 'stale'
                """,
                (project_id,),
            ).fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []
