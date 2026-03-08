"""
SP-1: Restauración de datos de usuario tras re-análisis.

Extraído de _analysis_phases.py — preserva ediciones del usuario
(atributos verificados, fusiones manuales, descartes guardados)
a través de re-análisis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("narrative_assistant.api")


def restore_verified_attributes(ctx: dict) -> None:
    """
    SP-1: Restaura is_verified=1 en atributos que el usuario había verificado.

    Busca en los atributos recién creados aquellos que coinciden con los
    que el usuario verificó en el análisis anterior (guardados en ctx por run_cleanup).
    """
    verified_attrs = ctx.get("_sp1_verified_attrs")
    if not verified_attrs:
        return

    project_id = ctx["project_id"]
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        restored = 0

        for va in verified_attrs:
            entity_name = va["entity_name"]
            attr_key = va["attribute_key"]
            attr_value = va["attribute_value"]

            with db.connection() as conn:
                row = conn.execute(
                    "SELECT ea.id FROM entity_attributes ea "
                    "JOIN entities e ON ea.entity_id = e.id "
                    "WHERE e.project_id = ? AND e.canonical_name = ? "
                    "AND ea.attribute_key = ? AND ea.attribute_value = ? "
                    "AND ea.is_verified = 0 "
                    "LIMIT 1",
                    (project_id, entity_name, attr_key, attr_value),
                ).fetchone()

            if row:
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE entity_attributes SET is_verified = 1 WHERE id = ?",
                        (row["id"],),
                    )
                restored += 1

        if restored > 0:
            logger.info(
                f"SP-1: Restored is_verified on {restored}/{len(verified_attrs)} attributes"
            )

    except Exception as e:
        logger.warning(f"SP-1: Error restoring verified attributes: {e}")


def reapply_user_merges(project_id: int, entity_repo: Any, entities: list) -> None:
    """
    SP-1: Re-aplica fusiones de usuario preservadas en review_history.

    Después de NER + fusión automática, verifica si hay merges de usuario
    previos (action_type='entity_merged') que la fusión automática no descubrió.
    Si ambas entidades existen con sus canonical_names originales, las fusiona.
    """
    try:
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        with db.connection() as conn:
            rows = conn.execute(
                "SELECT old_value_json, new_value_json, note FROM review_history "
                "WHERE project_id = ? AND action_type = 'entity_merged' "
                "ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()

        if not rows:
            return

        # Construir índice de entidades actuales por nombre
        entities_by_name: dict[str, Any] = {}
        for ent in entities:
            if ent.canonical_name:
                entities_by_name[ent.canonical_name.lower()] = ent

        reapplied = 0
        for row in rows:
            try:
                # SP-1: Saltar fusiones deshechas por el usuario
                note = row["note"] or ""
                if "[UNDONE" in note:
                    logger.debug(f"SP-1: Skipping undone merge: {note}")
                    continue

                old_data = json.loads(row["old_value_json"])
                names_before = old_data.get("canonical_names_before", [])

                if len(names_before) < 2:
                    continue

                primary_name = names_before[0].lower()
                primary = entities_by_name.get(primary_name)

                for secondary_name_raw in names_before[1:]:
                    secondary_name = secondary_name_raw.lower()
                    secondary = entities_by_name.get(secondary_name)

                    if not primary or not secondary or primary.id == secondary.id:
                        continue

                    if secondary.canonical_name in (primary.aliases or []):
                        continue

                    # Re-aplicar el merge
                    if primary.aliases is None:
                        primary.aliases = []
                    if secondary.canonical_name not in primary.aliases:
                        primary.aliases.append(secondary.canonical_name)

                    if primary.merged_from_ids is None:
                        primary.merged_from_ids = []
                    if secondary.id and secondary.id not in primary.merged_from_ids:
                        primary.merged_from_ids.append(secondary.id)

                    entity_repo.update_entity(
                        entity_id=primary.id,
                        aliases=primary.aliases,
                        merged_from_ids=primary.merged_from_ids,
                    )
                    entity_repo.move_mentions(secondary.id, primary.id)
                    entity_repo.delete_entity(secondary.id, hard_delete=False)

                    entities_by_name.pop(secondary_name, None)

                    logger.info(
                        f"SP-1: Re-applied user merge: '{secondary.canonical_name}' → "
                        f"'{primary.canonical_name}'"
                    )
                    reapplied += 1

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"SP-1: Skip malformed merge history entry: {e}")

        if reapplied > 0:
            logger.info(f"SP-1: Re-applied {reapplied} user merges from previous analysis")

    except Exception as e:
        logger.warning(f"SP-1: Error reapplying user merges: {e}")


def apply_saved_dismissals(project_id: int) -> None:
    """Aplica dismissals y suppression rules guardados a alertas recién generadas."""
    try:
        from narrative_assistant.alerts.repository import get_alert_repository
        from narrative_assistant.persistence.dismissal_repository import get_dismissal_repository

        alert_repo = get_alert_repository()
        dismissal_repo = get_dismissal_repository()

        # 1. Aplicar dismissals por content_hash
        result = alert_repo.apply_dismissals(project_id)
        if result.is_success and result.value > 0:  # type: ignore[operator]
            logger.info(f"SP-1: Auto-dismissed {result.value} alerts from saved dismissals")

        # 2. Aplicar suppression rules
        from narrative_assistant.persistence.database import get_database

        db = get_database()
        rules_result = dismissal_repo.get_suppression_rules(project_id, active_only=True)
        if rules_result.is_failure:
            return

        rules = rules_result.value
        if not rules:
            return

        suppressed_count = 0
        with db.connection() as conn:
            rows = conn.execute(
                "SELECT id, alert_type, source_module, content_hash FROM alerts "
                "WHERE project_id = ? AND status NOT IN ('dismissed', 'resolved', 'auto_resolved')",
                (project_id,),
            ).fetchall()

        for row in rows:
            if dismissal_repo.is_suppressed(
                project_id,
                alert_type=row["alert_type"] or "",
                source_module=row["source_module"] or "",
            ):
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE alerts SET status = 'dismissed', "
                        "resolution_note = 'Auto-suprimida por regla de supresión' "
                        "WHERE id = ?",
                        (row["id"],),
                    )
                suppressed_count += 1

        if suppressed_count > 0:
            logger.info(f"SP-1: Suppressed {suppressed_count} alerts from active rules")

    except Exception as e:
        logger.warning(f"SP-1: Error applying saved dismissals: {e}")
