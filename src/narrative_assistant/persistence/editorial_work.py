"""
Servicio de export/import de trabajo editorial (.narrassist).

Permite a equipos editoriales compartir decisiones (fusiones de entidades,
descartes de alertas, atributos verificados, reglas de supresión) entre
correctores sin transferir texto del manuscrito.

Formato: JSON versionado (.narrassist), format_version=1.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)

# Versión actual del formato
FORMAT_VERSION = 1


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ImportConflict:
    """Un conflicto entre datos importados y locales."""

    section: str  # entity_merges, alert_decisions, verified_attributes
    item_key: str  # Clave única (content_hash, entity_name, etc.)
    description: str  # Descripción legible
    local_value: str
    imported_value: str
    local_timestamp: str
    imported_timestamp: str
    resolution: str  # imported_wins o local_wins (pre-calculado)

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "item_key": self.item_key,
            "description": self.description,
            "local_value": self.local_value,
            "imported_value": self.imported_value,
            "local_timestamp": self.local_timestamp,
            "imported_timestamp": self.imported_timestamp,
            "resolution": self.resolution,
        }


@dataclass
class ImportPreview:
    """Resultado del preview de importación."""

    project_fingerprint_match: bool = True
    warnings: list[str] = field(default_factory=list)

    entity_merges_to_apply: int = 0
    entity_merges_already_done: int = 0
    entity_merges_conflicts: int = 0

    alert_decisions_to_apply: int = 0
    alert_decisions_already_done: int = 0
    alert_decisions_conflicts: int = 0

    verified_attributes_to_apply: int = 0
    verified_attributes_already_done: int = 0
    verified_attributes_conflicts: int = 0

    suppression_rules_to_add: int = 0
    suppression_rules_already_exist: int = 0

    conflicts: list[ImportConflict] = field(default_factory=list)

    # Detalle para el paso confirm (no expuesto al usuario)
    _merge_actions: list[dict] = field(default_factory=list)
    _alert_actions: list[dict] = field(default_factory=list)
    _attribute_actions: list[dict] = field(default_factory=list)
    _rule_actions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_fingerprint_match": self.project_fingerprint_match,
            "warnings": self.warnings,
            "entity_merges": {
                "to_apply": self.entity_merges_to_apply,
                "already_done": self.entity_merges_already_done,
                "conflicts": self.entity_merges_conflicts,
            },
            "alert_decisions": {
                "to_apply": self.alert_decisions_to_apply,
                "already_done": self.alert_decisions_already_done,
                "conflicts": self.alert_decisions_conflicts,
            },
            "verified_attributes": {
                "to_apply": self.verified_attributes_to_apply,
                "already_done": self.verified_attributes_already_done,
                "conflicts": self.verified_attributes_conflicts,
            },
            "suppression_rules": {
                "to_add": self.suppression_rules_to_add,
                "already_exist": self.suppression_rules_already_exist,
            },
            "conflicts": [c.to_dict() for c in self.conflicts],
            "total_to_apply": (
                self.entity_merges_to_apply
                + self.alert_decisions_to_apply
                + self.verified_attributes_to_apply
                + self.suppression_rules_to_add
            ),
            "total_conflicts": len(self.conflicts),
        }


# =============================================================================
# Export
# =============================================================================


def export_editorial_work(
    project_id: int,
    project_name: str = "",
    project_fingerprint: str = "",
    exported_by: str = "",
) -> Result[dict]:
    """
    Exporta todo el trabajo editorial de un proyecto como dict .narrassist.

    Recoge: merge history, alert decisions, verified attributes, suppression rules.
    NO incluye texto del manuscrito.

    Args:
        project_id: ID del proyecto
        project_name: Nombre del proyecto
        project_fingerprint: Fingerprint del documento
        exported_by: Nombre del exportador

    Returns:
        Result con dict serializable a JSON
    """
    try:
        from ..alerts.repository import get_alert_repository
        from ..entities.repository import get_entity_repository
        from .database import get_database
        from .dismissal_repository import get_dismissal_repository

        entity_repo = get_entity_repository()
        alert_repo = get_alert_repository()
        dismissal_repo = get_dismissal_repository()
        db = get_database()

        # 1. Entity merges (de review_history, skip UNDONE)
        entity_merges = _collect_entity_merges(db, project_id)

        # 2. Alert decisions (status != 'new')
        alert_decisions = _collect_alert_decisions(alert_repo, project_id)

        # 3. Verified attributes (is_verified=1)
        verified_attributes = _collect_verified_attributes(entity_repo, project_id)

        # 4. Suppression rules
        suppression_rules = _collect_suppression_rules(dismissal_repo, project_id)

        # App version
        try:
            from .. import __version__

            app_version = __version__
        except Exception:
            app_version = "unknown"

        export = {
            "format_version": FORMAT_VERSION,
            "app_version": app_version,
            "exported_at": datetime.now().isoformat(),
            "exported_by": exported_by,
            "project_fingerprint": project_fingerprint,
            "project_name": project_name,
            "entity_merges": entity_merges,
            "alert_decisions": alert_decisions,
            "verified_attributes": verified_attributes,
            "suppression_rules": suppression_rules,
            "statistics": {
                "total_entity_merges": len(entity_merges),
                "total_alert_decisions": len(alert_decisions),
                "total_verified_attributes": len(verified_attributes),
                "total_suppression_rules": len(suppression_rules),
            },
        }

        logger.info(
            f"Exported editorial work for project {project_id}: "
            f"{len(entity_merges)} merges, {len(alert_decisions)} decisions, "
            f"{len(verified_attributes)} attrs, {len(suppression_rules)} rules"
        )
        return Result.success(export)

    except Exception as e:
        error = NarrativeError(
            message="Error exporting editorial work",
            context={"error": str(e), "project_id": project_id},
        )
        logger.error(f"Export failed: {e}")
        return Result.failure(error)


def _collect_entity_merges(db, project_id: int) -> list[dict]:
    """Recoge merges de review_history (skip UNDONE)."""
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT old_value_json, new_value_json, note, created_at "
            "FROM review_history "
            "WHERE project_id = ? AND action_type = 'entity_merged' "
            "ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()

    merges = []
    for row in rows:
        note = row["note"] or ""
        if "[UNDONE" in note:
            continue

        old_data = json.loads(row["old_value_json"]) if row["old_value_json"] else {}
        new_data = json.loads(row["new_value_json"]) if row["new_value_json"] else {}

        source_names = old_data.get("canonical_names_before", [])
        if len(source_names) < 2:
            continue

        merges.append(
            {
                "result_canonical_name": source_names[0],
                "result_aliases": source_names[1:],
                "source_canonical_names": source_names,
                "merged_at": row["created_at"] or "",
                "merged_by": new_data.get("merged_by", "user"),
                "note": note.split("[UNDONE")[0].strip() if "[UNDONE" in note else note,
            }
        )

    return merges


def _collect_alert_decisions(alert_repo, project_id: int) -> list[dict]:
    """Recoge alertas con decisiones del usuario (status != 'new')."""
    result = alert_repo.get_by_project(project_id)
    if result.is_failure:
        return []

    decisions = []
    for alert in result.value:
        if alert.status.value == "new":
            continue

        entity_names = []
        if alert.entity_ids:
            # entity_ids ya viene como lista de ints
            pass  # No resolvemos nombres aquí para evitar dependencia circular

        decisions.append(
            {
                "content_hash": alert.content_hash or "",
                "status": alert.status.value,
                "resolution_note": alert.resolution_note or "",
                "decided_at": (
                    alert.resolved_at.isoformat()
                    if alert.resolved_at
                    else alert.updated_at.isoformat()
                    if alert.updated_at
                    else ""
                ),
                "alert_type": alert.alert_type or "",
                "category": alert.category.value if alert.category else "",
                "chapter": alert.chapter or 0,
                "entity_names": entity_names,
                "description_hint": (alert.title or "")[:100],
            }
        )

    return decisions


def _collect_verified_attributes(entity_repo, project_id: int) -> list[dict]:
    """Recoge atributos verificados (is_verified=1)."""
    from .database import get_database

    db = get_database()

    with db.connection() as conn:
        rows = conn.execute(
            "SELECT e.canonical_name, e.entity_type, "
            "ea.attribute_type, ea.attribute_key, ea.attribute_value, "
            "ea.confidence, ea.is_verified, ea.created_at "
            "FROM entity_attributes ea "
            "JOIN entities e ON ea.entity_id = e.id "
            "WHERE e.project_id = ? AND ea.is_verified = 1 AND e.is_active = 1",
            (project_id,),
        ).fetchall()

    return [
        {
            "entity_name": row["canonical_name"],
            "entity_type": row["entity_type"],
            "attribute_type": row["attribute_type"],
            "attribute_key": row["attribute_key"],
            "attribute_value": row["attribute_value"],
            "confidence": row["confidence"],
        }
        for row in rows
    ]


def _collect_suppression_rules(dismissal_repo, project_id: int) -> list[dict]:
    """Recoge reglas de supresión (activas e inactivas)."""
    result = dismissal_repo.get_suppression_rules(project_id, active_only=False)
    if result.is_failure:
        return []

    return [
        {
            "rule_type": rule.rule_type,
            "pattern": rule.pattern,
            "entity_name": rule.entity_name,
            "reason": rule.reason,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat() if rule.created_at else "",
        }
        for rule in result.value
    ]


# =============================================================================
# Import Preview
# =============================================================================


def preview_import(project_id: int, import_data: dict) -> Result[ImportPreview]:
    """
    Step 1 de import: analiza el archivo y genera preview con conflictos.

    Args:
        project_id: ID del proyecto destino
        import_data: Dict parseado del .narrassist

    Returns:
        Result con ImportPreview
    """
    try:
        # Validar formato
        validation = _validate_import_data(import_data)
        if validation.is_failure:
            return validation

        from ..alerts.repository import get_alert_repository
        from ..entities.repository import get_entity_repository
        from .database import get_database
        from .dismissal_repository import get_dismissal_repository

        entity_repo = get_entity_repository()
        alert_repo = get_alert_repository()
        dismissal_repo = get_dismissal_repository()
        db = get_database()

        preview = ImportPreview()

        # Verificar fingerprint
        project_fp = _get_project_fingerprint(db, project_id)
        imported_fp = import_data.get("project_fingerprint", "")
        if imported_fp and project_fp and imported_fp != project_fp:
            preview.project_fingerprint_match = False
            preview.warnings.append(
                "El archivo fue exportado de un manuscrito diferente. "
                "Algunos datos podrían no coincidir."
            )

        # Analizar cada sección
        _preview_entity_merges(
            preview, import_data.get("entity_merges", []), entity_repo, project_id
        )
        _preview_alert_decisions(
            preview, import_data.get("alert_decisions", []), alert_repo, db, project_id
        )
        _preview_verified_attributes(
            preview,
            import_data.get("verified_attributes", []),
            entity_repo,
            db,
            project_id,
        )
        _preview_suppression_rules(
            preview,
            import_data.get("suppression_rules", []),
            dismissal_repo,
            project_id,
        )

        logger.info(
            f"Import preview for project {project_id}: "
            f"{preview.to_dict()['total_to_apply']} to apply, "
            f"{len(preview.conflicts)} conflicts"
        )
        return Result.success(preview)

    except Exception as e:
        error = NarrativeError(
            message="Error previewing import",
            context={"error": str(e), "project_id": project_id},
        )
        logger.error(f"Preview failed: {e}")
        return Result.failure(error)


def _validate_import_data(data: dict) -> Result[None]:
    """Valida estructura básica del archivo .narrassist."""
    if not isinstance(data, dict):
        return Result.failure(
            NarrativeError(
                message="El archivo no contiene JSON válido",
                severity=ErrorSeverity.FATAL,
            )
        )

    version = data.get("format_version")
    if version != FORMAT_VERSION:
        return Result.failure(
            NarrativeError(
                message=f"Versión de formato no soportada: {version} (esperado: {FORMAT_VERSION})",
                severity=ErrorSeverity.FATAL,
            )
        )

    return Result.success(None)


def _get_project_fingerprint(db, project_id: int) -> str:
    """Obtiene el fingerprint del documento del proyecto."""
    with db.connection() as conn:
        row = conn.execute(
            "SELECT document_fingerprint FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    return row["document_fingerprint"] if row and row["document_fingerprint"] else ""


def _preview_entity_merges(
    preview: ImportPreview, merges: list[dict], entity_repo, project_id: int
):
    """Analiza merges importados vs estado local."""
    for merge in merges:
        result_name = merge.get("result_canonical_name", "")
        source_names = merge.get("source_canonical_names", [])
        if not result_name or len(source_names) < 2:
            continue

        # Buscar si la entidad resultado ya existe con los aliases
        result_entities = entity_repo.find_entities_by_name(
            project_id, result_name, fuzzy=False
        )

        if result_entities:
            # La entidad principal existe; verificar si ya tiene los aliases
            primary = result_entities[0]
            aliases = primary.aliases or []
            all_merged = all(
                sn.lower() == result_name.lower() or sn in aliases
                for sn in source_names
            )
            if all_merged:
                preview.entity_merges_already_done += 1
                continue

        # Verificar si las entidades fuente existen separadas
        sources_found = []
        for sn in source_names:
            found = entity_repo.find_entities_by_name(project_id, sn, fuzzy=False)
            if found:
                sources_found.append(found[0])

        if len(sources_found) >= 2:
            preview.entity_merges_to_apply += 1
            preview._merge_actions.append(
                {
                    "action": "apply",
                    "result_name": result_name,
                    "source_names": source_names,
                    "source_ids": [e.id for e in sources_found],
                }
            )
        else:
            # Entidades no encontradas, no se puede aplicar
            preview.entity_merges_already_done += 1


def _preview_alert_decisions(
    preview: ImportPreview,
    decisions: list[dict],
    alert_repo,
    db,
    project_id: int,
):
    """Analiza decisiones de alertas importadas vs estado local."""
    # Cargar alertas locales indexadas por content_hash
    result = alert_repo.get_by_project(project_id)
    local_alerts = {}
    if result.is_success:
        for alert in result.value:
            if alert.content_hash:
                local_alerts[alert.content_hash] = alert

    # Cargar hashes de dismissals existentes
    from .dismissal_repository import get_dismissal_repository

    dismissal_repo = get_dismissal_repository()
    dismissed_hashes = dismissal_repo.get_dismissed_hashes(project_id)

    for decision in decisions:
        content_hash = decision.get("content_hash", "")
        if not content_hash:
            continue

        imported_status = decision.get("status", "")
        imported_timestamp = decision.get("decided_at", "")

        # ¿Ya está dismisseado en alert_dismissals?
        if content_hash in dismissed_hashes and imported_status == "dismissed":
            preview.alert_decisions_already_done += 1
            continue

        # ¿Existe la alerta localmente?
        local_alert = local_alerts.get(content_hash)
        if local_alert:
            local_status = local_alert.status.value
            if local_status == imported_status:
                preview.alert_decisions_already_done += 1
                continue
            elif local_status == "new":
                # Alerta nueva localmente, importar decisión
                preview.alert_decisions_to_apply += 1
                preview._alert_actions.append(
                    {
                        "action": "apply",
                        "content_hash": content_hash,
                        "alert_id": local_alert.id,
                        "status": imported_status,
                        "resolution_note": decision.get("resolution_note", ""),
                    }
                )
            else:
                # Conflicto: local tiene un status diferente
                resolution = _resolve_latest_wins(
                    local_alert.updated_at.isoformat()
                    if local_alert.updated_at
                    else "",
                    imported_timestamp,
                )
                preview.alert_decisions_conflicts += 1
                preview.conflicts.append(
                    ImportConflict(
                        section="alert_decisions",
                        item_key=content_hash,
                        description=decision.get("description_hint", "Alerta"),
                        local_value=local_status,
                        imported_value=imported_status,
                        local_timestamp=local_alert.updated_at.isoformat()
                        if local_alert.updated_at
                        else "",
                        imported_timestamp=imported_timestamp,
                        resolution=resolution,
                    )
                )
                preview._alert_actions.append(
                    {
                        "action": "conflict",
                        "content_hash": content_hash,
                        "alert_id": local_alert.id,
                        "status": imported_status,
                        "resolution_note": decision.get("resolution_note", ""),
                        "resolution": resolution,
                    }
                )
        else:
            # Alerta no existe localmente, guardar en dismissals para futuro
            if imported_status == "dismissed":
                preview.alert_decisions_to_apply += 1
                preview._alert_actions.append(
                    {
                        "action": "dismiss_future",
                        "content_hash": content_hash,
                        "alert_type": decision.get("alert_type", ""),
                        "source_module": "",
                    }
                )
            else:
                preview.alert_decisions_already_done += 1


def _preview_verified_attributes(
    preview: ImportPreview,
    attributes: list[dict],
    entity_repo,
    db,
    project_id: int,
):
    """Analiza atributos verificados importados vs locales."""
    # Cargar atributos locales
    local_attrs = {}
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT ea.id, e.canonical_name, ea.attribute_type, ea.attribute_key, "
            "ea.attribute_value, ea.is_verified, ea.created_at "
            "FROM entity_attributes ea "
            "JOIN entities e ON ea.entity_id = e.id "
            "WHERE e.project_id = ? AND e.is_active = 1",
            (project_id,),
        ).fetchall()

    for row in rows:
        key = (
            row["canonical_name"].lower(),
            row["attribute_key"].lower(),
            row["attribute_type"].lower(),
        )
        local_attrs[key] = {
            "id": row["id"],
            "value": row["attribute_value"],
            "is_verified": row["is_verified"],
            "created_at": row["created_at"] or "",
        }

    for attr in attributes:
        entity_name = attr.get("entity_name", "")
        attr_key = attr.get("attribute_key", "")
        attr_type = attr.get("attribute_type", "")
        if not entity_name or not attr_key:
            continue

        key = (entity_name.lower(), attr_key.lower(), attr_type.lower())
        local = local_attrs.get(key)

        if local:
            if local["is_verified"]:
                if local["value"] == attr.get("attribute_value", ""):
                    preview.verified_attributes_already_done += 1
                else:
                    # Conflicto: mismo attr verificado con valor diferente
                    preview.verified_attributes_conflicts += 1
                    preview.conflicts.append(
                        ImportConflict(
                            section="verified_attributes",
                            item_key=f"{entity_name}:{attr_key}",
                            description=f"{entity_name} - {attr_key}",
                            local_value=local["value"],
                            imported_value=attr.get("attribute_value", ""),
                            local_timestamp=local["created_at"],
                            imported_timestamp="",
                            resolution="local_wins",
                        )
                    )
                    preview._attribute_actions.append(
                        {
                            "action": "conflict",
                            "attribute_id": local["id"],
                            "value": attr.get("attribute_value", ""),
                            "resolution": "local_wins",
                        }
                    )
            else:
                # No verificado localmente → verificar
                preview.verified_attributes_to_apply += 1
                preview._attribute_actions.append(
                    {
                        "action": "verify",
                        "attribute_id": local["id"],
                        "value": attr.get("attribute_value", ""),
                    }
                )
        else:
            # Atributo no existe localmente, skip (no podemos crear sin entidad)
            preview.verified_attributes_already_done += 1


def _preview_suppression_rules(
    preview: ImportPreview,
    rules: list[dict],
    dismissal_repo,
    project_id: int,
):
    """Analiza reglas de supresión importadas vs locales."""
    result = dismissal_repo.get_suppression_rules(project_id, active_only=False)
    local_rules = set()
    if result.is_success:
        for rule in result.value:
            local_rules.add(
                (rule.rule_type.lower(), rule.pattern.lower(), (rule.entity_name or "").lower())
            )

    for rule in rules:
        key = (
            rule.get("rule_type", "").lower(),
            rule.get("pattern", "").lower(),
            (rule.get("entity_name") or "").lower(),
        )
        if key in local_rules:
            preview.suppression_rules_already_exist += 1
        else:
            preview.suppression_rules_to_add += 1
            preview._rule_actions.append(
                {
                    "action": "add",
                    "rule_type": rule.get("rule_type", ""),
                    "pattern": rule.get("pattern", ""),
                    "entity_name": rule.get("entity_name"),
                    "reason": rule.get("reason", ""),
                }
            )


def _resolve_latest_wins(local_timestamp: str, imported_timestamp: str) -> str:
    """Determina ganador por LATEST_WINS."""
    if not local_timestamp:
        return "imported_wins"
    if not imported_timestamp:
        return "local_wins"
    try:
        local_dt = datetime.fromisoformat(local_timestamp)
        imported_dt = datetime.fromisoformat(imported_timestamp)
        return "imported_wins" if imported_dt >= local_dt else "local_wins"
    except (ValueError, TypeError):
        return "imported_wins"


# =============================================================================
# Import Confirm
# =============================================================================


def confirm_import(
    project_id: int,
    import_data: dict,
    import_entity_merges: bool = True,
    import_alert_decisions: bool = True,
    import_verified_attributes: bool = True,
    import_suppression_rules: bool = True,
    conflict_overrides: dict[str, str] | None = None,
) -> Result[dict]:
    """
    Step 2 de import: aplica los cambios basándose en el preview.

    Args:
        project_id: ID del proyecto destino
        import_data: Dict parseado del .narrassist (mismo que preview)
        import_entity_merges: Si True, aplica merges
        import_alert_decisions: Si True, aplica decisiones de alertas
        import_verified_attributes: Si True, aplica atributos verificados
        import_suppression_rules: Si True, aplica reglas de supresión
        conflict_overrides: Dict de item_key → 'imported_wins'|'local_wins'

    Returns:
        Result con estadísticas de lo aplicado
    """
    try:
        if conflict_overrides is None:
            conflict_overrides = {}

        # Re-generar preview para obtener acciones actualizadas
        preview_result = preview_import(project_id, import_data)
        if preview_result.is_failure:
            return Result.failure(preview_result.error)

        preview = preview_result.value
        stats = {
            "entity_merges_applied": 0,
            "alert_decisions_applied": 0,
            "verified_attributes_applied": 0,
            "suppression_rules_added": 0,
            "conflicts_resolved": 0,
        }

        # Aplicar merges
        if import_entity_merges:
            stats["entity_merges_applied"] = _apply_entity_merges(
                project_id, preview._merge_actions
            )

        # Aplicar decisiones de alertas
        if import_alert_decisions:
            stats["alert_decisions_applied"] = _apply_alert_decisions(
                project_id, preview._alert_actions, conflict_overrides
            )

        # Aplicar atributos verificados
        if import_verified_attributes:
            stats["verified_attributes_applied"] = _apply_verified_attributes(
                preview._attribute_actions, conflict_overrides
            )

        # Aplicar reglas de supresión
        if import_suppression_rules:
            stats["suppression_rules_added"] = _apply_suppression_rules(
                project_id, preview._rule_actions
            )

        stats["conflicts_resolved"] = sum(
            1 for c in preview.conflicts if c.item_key in conflict_overrides
        )

        logger.info(f"Import applied for project {project_id}: {stats}")
        return Result.success(stats)

    except Exception as e:
        error = NarrativeError(
            message="Error confirming import",
            context={"error": str(e), "project_id": project_id},
        )
        logger.error(f"Import confirm failed: {e}")
        return Result.failure(error)


def _apply_entity_merges(project_id: int, actions: list[dict]) -> int:
    """Aplica fusiones de entidades."""
    from ..entities.repository import get_entity_repository

    entity_repo = get_entity_repository()
    applied = 0

    for action in actions:
        if action["action"] != "apply":
            continue

        source_ids = action.get("source_ids", [])
        if len(source_ids) < 2:
            continue

        primary_id = source_ids[0]
        primary = entity_repo.get_entity(primary_id)
        if not primary:
            continue

        for secondary_id in source_ids[1:]:
            secondary = entity_repo.get_entity(secondary_id)
            if not secondary or not secondary.is_active:
                continue

            aliases = primary.aliases or []
            if secondary.canonical_name not in aliases:
                aliases.append(secondary.canonical_name)

            merged_ids = primary.merged_from_ids or []
            if secondary.id and secondary.id not in merged_ids:
                merged_ids.append(secondary.id)

            entity_repo.update_entity(
                entity_id=primary.id,
                aliases=aliases,
                merged_from_ids=merged_ids,
            )
            entity_repo.move_mentions(secondary.id, primary.id)
            entity_repo.delete_entity(secondary.id, hard_delete=False)

            logger.info(
                f"Import: merged '{secondary.canonical_name}' → '{primary.canonical_name}'"
            )

        applied += 1

    return applied


def _update_alert_status(
    alert_repo, dismissal_repo, project_id: int, alert_id: int,
    content_hash: str, status: str, resolution_note: str,
):
    """Actualiza el status de una alerta y registra dismissal si aplica."""
    from ..alerts.models import AlertStatus

    alert_result = alert_repo.get(alert_id)
    if alert_result.is_failure:
        return
    alert = alert_result.value
    alert.status = AlertStatus(status)
    alert.resolution_note = resolution_note
    if status in ("dismissed", "resolved"):
        alert.resolved_at = datetime.now()
    alert_repo.update(alert)

    if status == "dismissed" and content_hash:
        dismissal_repo.dismiss(
            project_id=project_id,
            content_hash=content_hash,
            scope="instance",
            reason="imported",
        )


def _apply_alert_decisions(
    project_id: int,
    actions: list[dict],
    conflict_overrides: dict[str, str],
) -> int:
    """Aplica decisiones de alertas."""
    from ..alerts.repository import get_alert_repository
    from .dismissal_repository import get_dismissal_repository

    alert_repo = get_alert_repository()
    dismissal_repo = get_dismissal_repository()
    applied = 0

    for action in actions:
        act_type = action["action"]

        if act_type == "dismiss_future":
            # Guardar en dismissals para futuros re-análisis
            dismissal_repo.dismiss(
                project_id=project_id,
                content_hash=action["content_hash"],
                alert_type=action.get("alert_type", ""),
                source_module=action.get("source_module", ""),
                scope="instance",
                reason="imported",
            )
            applied += 1

        elif act_type == "apply":
            # Actualizar alerta existente
            alert_id = action.get("alert_id")
            if alert_id:
                _update_alert_status(
                    alert_repo, dismissal_repo, project_id, alert_id,
                    action["content_hash"], action["status"],
                    action.get("resolution_note", ""),
                )
                applied += 1

        elif act_type == "conflict":
            content_hash = action.get("content_hash", "")
            override = conflict_overrides.get(content_hash, action.get("resolution", ""))
            if override == "imported_wins":
                alert_id = action.get("alert_id")
                if alert_id:
                    _update_alert_status(
                        alert_repo, dismissal_repo, project_id, alert_id,
                        content_hash, action["status"],
                        action.get("resolution_note", ""),
                    )
                    applied += 1

    return applied


def _apply_verified_attributes(
    actions: list[dict], conflict_overrides: dict[str, str]
) -> int:
    """Aplica verificación de atributos."""
    from .database import get_database

    db = get_database()
    applied = 0

    for action in actions:
        act_type = action["action"]

        if act_type == "verify":
            attr_id = action.get("attribute_id")
            if attr_id:
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE entity_attributes SET is_verified = 1 WHERE id = ?",
                        (attr_id,),
                    )
                applied += 1

        elif act_type == "conflict":
            # Solo aplicar si override dice imported_wins
            attr_id = action.get("attribute_id")
            item_key = f"attr_{attr_id}"
            override = conflict_overrides.get(item_key, action.get("resolution", ""))
            if override == "imported_wins" and attr_id:
                with db.transaction() as conn:
                    conn.execute(
                        "UPDATE entity_attributes SET attribute_value = ?, is_verified = 1 "
                        "WHERE id = ?",
                        (action["value"], attr_id),
                    )
                applied += 1

    return applied


def _apply_suppression_rules(project_id: int, actions: list[dict]) -> int:
    """Añade reglas de supresión nuevas."""
    from .dismissal_repository import get_dismissal_repository

    dismissal_repo = get_dismissal_repository()
    added = 0

    for action in actions:
        if action["action"] != "add":
            continue

        result = dismissal_repo.create_suppression_rule(
            rule_type=action["rule_type"],
            pattern=action["pattern"],
            project_id=project_id,
            entity_name=action.get("entity_name"),
            reason=action.get("reason", "imported"),
        )
        if result.is_success:
            added += 1

    return added
