"""
Historial de cambios y acciones del revisor.

Permite:
- Auditoría de decisiones
- Undo/redo universal
- Análisis de patrones de corrección
- Undo selectivo con detección de dependencias
"""

import contextlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .database import SCHEMA_VERSION, Database, get_database

logger = logging.getLogger(__name__)


# --- Tipos de cambio undoable ---

# Acciones que el usuario puede deshacer
UNDOABLE_ACTIONS = frozenset({
    "entity_merged",
    "entity_deleted",
    "entity_updated",
    "entity_created",
    "alert_resolved",
    "alert_dismissed",
    "attribute_verified",
    "attribute_updated",
    "attribute_added",
    "attribute_deleted",
    "relationship_created",
    "relationship_updated",
    "relationship_deleted",
})


class ChangeType(Enum):
    """Tipos de cambios registrados en el historial."""

    # Alertas
    ALERT_CREATED = "alert_created"
    ALERT_REVIEWED = "alert_reviewed"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_DISMISSED = "alert_dismissed"
    ALERT_REOPENED = "alert_reopened"

    # Entidades
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_MERGED = "entity_merged"
    ENTITY_SPLIT = "entity_split"
    ENTITY_DELETED = "entity_deleted"

    # Atributos
    ATTRIBUTE_ADDED = "attribute_added"
    ATTRIBUTE_UPDATED = "attribute_updated"
    ATTRIBUTE_VERIFIED = "attribute_verified"
    ATTRIBUTE_DELETED = "attribute_deleted"

    # Relaciones
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_UPDATED = "relationship_updated"
    RELATIONSHIP_DELETED = "relationship_deleted"

    # Proyecto
    PROJECT_CREATED = "project_created"
    PROJECT_SETTINGS_CHANGED = "project_settings_changed"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"

    # Undo/redo
    UNDO = "undo"
    REDO = "redo"
    OTHER = "other"


@dataclass
class HistoryEntry:
    """Entrada en el historial de cambios."""

    id: int | None = None
    project_id: int = 0
    action_type: ChangeType = ChangeType.ALERT_CREATED
    target_type: str = ""
    target_id: int | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    note: str = ""
    created_at: datetime | None = None
    batch_id: str | None = None
    depends_on_ids: list[int] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    undone_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "HistoryEntry":
        """Crea desde fila de SQLite."""
        old_value = None
        new_value = None
        depends_on: list[int] = []

        if row["old_value_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                old_value = json.loads(row["old_value_json"])

        if row["new_value_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                new_value = json.loads(row["new_value_json"])

        # Columnas v25 — pueden no existir en BD vieja
        batch_id = None
        schema_ver = SCHEMA_VERSION
        undone_at = None
        try:
            batch_id = row["batch_id"]
        except (IndexError, KeyError):
            pass
        try:
            raw = row["depends_on_ids"]
            if raw:
                depends_on = json.loads(raw)
        except (IndexError, KeyError, json.JSONDecodeError):
            pass
        try:
            schema_ver = row["schema_version"] or SCHEMA_VERSION
        except (IndexError, KeyError):
            pass
        try:
            raw_undone = row["undone_at"]
            if raw_undone:
                undone_at = datetime.fromisoformat(raw_undone)
        except (IndexError, KeyError, ValueError):
            pass

        return cls(
            id=row["id"],
            project_id=row["project_id"],
            action_type=ChangeType(row["action_type"]),
            target_type=row["target_type"] or "",
            target_id=row["target_id"],
            old_value=old_value,
            new_value=new_value,
            note=row["note"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            batch_id=batch_id,
            depends_on_ids=depends_on,
            schema_version=schema_ver,
            undone_at=undone_at,
        )

    @property
    def is_undoable(self) -> bool:
        """Indica si esta acción se puede deshacer."""
        return (
            self.action_type.value in UNDOABLE_ACTIONS
            and self.old_value is not None
            and self.undone_at is None
        )

    @property
    def is_undone(self) -> bool:
        return self.undone_at is not None

    def to_dict(self) -> dict:
        """Serializa a diccionario para la API."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "action_type": self.action_type.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "batch_id": self.batch_id,
            "depends_on_ids": self.depends_on_ids,
            "is_undoable": self.is_undoable,
            "is_undone": self.is_undone,
            "undone_at": self.undone_at.isoformat() if self.undone_at else None,
        }


@dataclass
class UndoResult:
    """Resultado de una operación de undo."""

    success: bool
    message: str = ""
    entry_id: int | None = None
    conflicts: list[dict] | None = None


class HistoryManager:
    """
    Gestiona el historial de cambios de un proyecto.

    Soporta undo/redo universal con:
    - Registro de todas las acciones con old_value/new_value
    - Operaciones compuestas (batch_id)
    - Detección de dependencias (depends_on_ids)
    - Undo selectivo (deshacer B sin deshacer C si son independientes)
    """

    def __init__(self, project_id: int, db: Database | None = None):
        self.project_id = project_id
        self.db = db or get_database()

    # ── Registro ──

    def record(
        self,
        action_type: ChangeType,
        target_type: str = "",
        target_id: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        note: str = "",
        batch_id: str | None = None,
        depends_on_ids: list[int] | None = None,
    ) -> HistoryEntry:
        """Registra un cambio en el historial."""
        deps_json = json.dumps(depends_on_ids) if depends_on_ids else "[]"

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO review_history (
                    project_id, action_type, target_type, target_id,
                    old_value_json, new_value_json, note,
                    batch_id, depends_on_ids, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.project_id,
                    action_type.value,
                    target_type,
                    target_id,
                    json.dumps(old_value) if old_value else None,
                    json.dumps(new_value) if new_value else None,
                    note,
                    batch_id,
                    deps_json,
                    SCHEMA_VERSION,
                ),
            )
            entry_id = cursor.lastrowid

        entry = HistoryEntry(
            id=entry_id,
            project_id=self.project_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            note=note,
            created_at=datetime.now(),
            batch_id=batch_id,
            depends_on_ids=depends_on_ids or [],
            schema_version=SCHEMA_VERSION,
        )

        logger.debug(f"Historial: {action_type.value} on {target_type}:{target_id}")
        return entry

    def new_batch_id(self) -> str:
        """Genera un batch_id único para agrupar operaciones compuestas."""
        return str(uuid.uuid4())[:8]

    # ── Consulta ──

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        action_types: list[ChangeType] | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        undoable_only: bool = False,
    ) -> list[HistoryEntry]:
        """Obtiene entradas del historial con filtros opcionales."""
        conditions = ["project_id = ?"]
        params: list[Any] = [self.project_id]

        if action_types:
            placeholders = ",".join("?" * len(action_types))
            conditions.append(f"action_type IN ({placeholders})")
            params.extend(at.value for at in action_types)

        if target_type:
            conditions.append("target_type = ?")
            params.append(target_type)

        if target_id is not None:
            conditions.append("target_id = ?")
            params.append(target_id)

        if undoable_only:
            # Solo acciones undoable que no hayan sido deshhechas
            undoable_list = ",".join(f"'{a}'" for a in UNDOABLE_ACTIONS)
            conditions.append(f"action_type IN ({undoable_list})")
            conditions.append("old_value_json IS NOT NULL")
            conditions.append("undone_at IS NULL")

        where_clause = " AND ".join(conditions)
        params.extend([limit, offset])

        rows = self.db.fetchall(
            f"""
            SELECT * FROM review_history
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

        return [HistoryEntry.from_row(row) for row in rows]

    def get_entry(self, entry_id: int) -> HistoryEntry | None:
        """Obtiene una entrada específica por ID."""
        row = self.db.fetchone(
            "SELECT * FROM review_history WHERE id = ? AND project_id = ?",
            (entry_id, self.project_id),
        )
        return HistoryEntry.from_row(row) if row else None

    def get_last_undoable(self) -> HistoryEntry | None:
        """Obtiene la última acción undoable (para Ctrl+Z)."""
        entries = self.get_history(limit=1, undoable_only=True)
        return entries[0] if entries else None

    def get_target_history(
        self,
        target_type: str,
        target_id: int,
    ) -> list[HistoryEntry]:
        """Obtiene todo el historial de un objeto específico."""
        return self.get_history(
            limit=1000,
            target_type=target_type,
            target_id=target_id,
        )

    def get_stats(self) -> dict:
        """Obtiene estadísticas del historial."""
        rows = self.db.fetchall(
            """
            SELECT action_type, COUNT(*) as count
            FROM review_history
            WHERE project_id = ?
            GROUP BY action_type
            ORDER BY count DESC
            """,
            (self.project_id,),
        )

        stats = {row["action_type"]: row["count"] for row in rows}
        stats["total"] = sum(stats.values())
        return stats

    def get_undoable_count(self) -> int:
        """Cuenta acciones pendientes de deshacer (para badge del sidebar)."""
        row = self.db.fetchone(
            """
            SELECT COUNT(*) as cnt FROM review_history
            WHERE project_id = ?
              AND action_type IN ({})
              AND old_value_json IS NOT NULL
              AND undone_at IS NULL
            """.format(",".join(f"'{a}'" for a in UNDOABLE_ACTIONS)),
            (self.project_id,),
        )
        return row["cnt"] if row else 0

    # ── Dependencias ──

    def check_dependencies(self, entry_id: int) -> list[HistoryEntry]:
        """
        Busca entradas que dependen de esta acción.

        Devuelve lista de entradas que bloquean el undo (dependientes no-deshhechas).
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM review_history
            WHERE project_id = ?
              AND undone_at IS NULL
              AND depends_on_ids LIKE ?
            ORDER BY created_at DESC
            """,
            (self.project_id, f"%{entry_id}%"),
        )

        dependents = []
        for row in rows:
            entry = HistoryEntry.from_row(row)
            if entry_id in entry.depends_on_ids:
                dependents.append(entry)
        return dependents

    def check_batch_dependencies(self, batch_id: str) -> list[HistoryEntry]:
        """Busca entradas que dependen de cualquier entry de un batch."""
        batch_entries = self.db.fetchall(
            "SELECT id FROM review_history WHERE project_id = ? AND batch_id = ?",
            (self.project_id, batch_id),
        )
        batch_entry_ids = {row["id"] for row in batch_entries}

        all_dependents = []
        for eid in batch_entry_ids:
            for dep in self.check_dependencies(eid):
                if dep.id not in batch_entry_ids:
                    all_dependents.append(dep)
        return all_dependents

    # ── Undo ──

    def can_undo(self, entry_id: int) -> tuple[bool, str]:
        """
        Verifica si una entrada puede ser deshecha.

        Returns:
            (puede_deshacer, motivo)
        """
        entry = self.get_entry(entry_id)
        if not entry:
            return False, "Entrada no encontrada"

        if not entry.is_undoable:
            if entry.is_undone:
                return False, "Ya fue deshecha"
            return False, "Esta acción no es reversible"

        # Verificar dependencias
        dependents = self.check_dependencies(entry_id)
        if dependents:
            dep_descriptions = [
                f"#{d.id}: {d.action_type.value} ({d.target_type}:{d.target_id})"
                for d in dependents[:5]
            ]
            return False, (
                f"No se puede deshacer: {len(dependents)} acciones dependen de esta. "
                f"Deshaz primero: {', '.join(dep_descriptions)}"
            )

        return True, "OK"

    def undo(self, entry_id: int) -> UndoResult:
        """
        Deshace una acción restaurando el estado previo.

        Soporta undo selectivo: se puede deshacer cualquier acción siempre
        que no haya dependencias activas.
        """
        ok, reason = self.can_undo(entry_id)
        if not ok:
            return UndoResult(success=False, message=reason, entry_id=entry_id)

        entry = self.get_entry(entry_id)
        if not entry:
            return UndoResult(success=False, message="Entrada no encontrada")

        action = entry.action_type.value
        target_id = entry.target_id
        old_value = entry.old_value

        logger.info(f"Deshaciendo acción {entry_id}: {action}")

        try:
            # Dispatch por tipo de acción
            if action == "entity_merged":
                self._undo_entity_merge(target_id, old_value)  # type: ignore[arg-type]
            elif action == "entity_deleted":
                self._undo_entity_delete(target_id, old_value)  # type: ignore[arg-type]
            elif action == "entity_updated":
                self._undo_entity_update(target_id, old_value)  # type: ignore[arg-type]
            elif action in ("alert_resolved", "alert_dismissed"):
                self._undo_alert_status_change(target_id, old_value)  # type: ignore[arg-type]
            elif action == "attribute_verified":
                self._undo_attribute_verification(target_id, old_value)  # type: ignore[arg-type]
            elif action in ("attribute_updated", "attribute_added"):
                self._undo_attribute_change(target_id, old_value)  # type: ignore[arg-type]
            elif action == "attribute_deleted":
                self._undo_attribute_delete(target_id, old_value)  # type: ignore[arg-type]
            elif action in ("relationship_created", "relationship_updated", "relationship_deleted"):
                self._undo_relationship_change(action, target_id, old_value)  # type: ignore[arg-type]
            else:
                return UndoResult(
                    success=False,
                    message=f"Tipo de acción '{action}' no soportado para undo",
                    entry_id=entry_id,
                )

            # Marcar como deshecha
            with self.db.connection() as conn:
                conn.execute(
                    "UPDATE review_history SET undone_at = datetime('now') WHERE id = ?",
                    (entry_id,),
                )

            # Registrar la reversión
            self.record(
                action_type=ChangeType.UNDO,
                target_type=entry.target_type,
                target_id=target_id,
                old_value={"undone_entry_id": entry_id},
                new_value=entry.old_value,
                note=_undo_description(entry),
            )

            logger.info(f"Acción {entry_id} deshecha exitosamente")
            return UndoResult(
                success=True,
                message=_undo_description(entry),
                entry_id=entry_id,
            )

        except Exception as e:
            logger.error(f"Error deshaciendo acción {entry_id}: {e}", exc_info=True)
            return UndoResult(
                success=False,
                message=f"Error al deshacer: {e}",
                entry_id=entry_id,
            )

    def undo_last(self) -> UndoResult:
        """Deshace la última acción undoable (Ctrl+Z)."""
        entry = self.get_last_undoable()
        if not entry or not entry.id:
            return UndoResult(success=False, message="No hay acciones para deshacer")
        return self.undo(entry.id)

    def undo_batch(self, batch_id: str) -> UndoResult:
        """Deshace todas las acciones de un batch (operación compuesta)."""
        entries = self.db.fetchall(
            """
            SELECT * FROM review_history
            WHERE project_id = ? AND batch_id = ? AND undone_at IS NULL
            ORDER BY created_at DESC
            """,
            (self.project_id, batch_id),
        )

        if not entries:
            return UndoResult(success=False, message="No hay acciones en este batch")

        # Verificar dependencias externas
        ext_deps = self.check_batch_dependencies(batch_id)
        if ext_deps:
            dep_descs = [f"#{d.id}: {d.action_type.value}" for d in ext_deps[:5]]
            return UndoResult(
                success=False,
                message=f"No se puede deshacer el batch: {len(ext_deps)} acciones externas dependen de él. "
                        f"Deshaz primero: {', '.join(dep_descs)}",
                conflicts=[d.to_dict() for d in ext_deps],
            )

        # Deshacer en orden inverso (más reciente primero)
        for row in entries:
            entry = HistoryEntry.from_row(row)
            if entry.id and entry.is_undoable:
                result = self.undo(entry.id)
                if not result.success:
                    return UndoResult(
                        success=False,
                        message=f"Error deshaciendo batch en entrada #{entry.id}: {result.message}",
                    )

        return UndoResult(
            success=True,
            message=f"Batch {batch_id} deshecho ({len(entries)} acciones)",
        )

    # ── Handlers de undo específicos ──

    def _undo_entity_merge(self, result_entity_id: int, old_value: dict) -> None:
        """Revierte fusión de entidades restaurando las originales."""
        if not old_value:
            raise ValueError("No hay información de fusión para deshacer")

        source_entity_ids = old_value.get("source_entity_ids", [])
        source_snapshots = old_value.get("source_snapshots", [])

        if not source_entity_ids:
            raise ValueError("No hay entidades fuente para restaurar")

        snapshots_by_id = {s["id"]: s for s in source_snapshots}

        with self.db.connection() as conn:
            # 1. Reactivar entidades fusionadas
            for entity_id in source_entity_ids:
                conn.execute(
                    "UPDATE entities SET is_active = 1, updated_at = datetime('now') WHERE id = ?",
                    (entity_id,),
                )

            # 2. Mover menciones de vuelta
            for entity_id in source_entity_ids:
                snapshot = snapshots_by_id.get(entity_id, {})
                original_mention_count = snapshot.get("mention_count", 0)
                if original_mention_count > 0:
                    conn.execute(
                        """
                        UPDATE entity_mentions SET entity_id = ?
                        WHERE id IN (
                            SELECT id FROM entity_mentions
                            WHERE entity_id = ? ORDER BY id DESC LIMIT ?
                        )
                        """,
                        (entity_id, result_entity_id, original_mention_count),
                    )

            # 3. Mover atributos de vuelta
            for entity_id in source_entity_ids:
                conn.execute(
                    """
                    UPDATE entity_attributes SET entity_id = ?
                    WHERE entity_id = ?
                    AND id IN (
                        SELECT ea.id FROM entity_attributes ea
                        LEFT JOIN attribute_evidences ae ON ea.id = ae.attribute_id
                        WHERE ea.entity_id = ?
                        ORDER BY ea.id DESC
                    )
                    """,
                    (entity_id, result_entity_id, result_entity_id),
                )

            # 4. Restaurar aliases de la entidad principal
            result = conn.execute(
                "SELECT merged_from_ids FROM entities WHERE id = ?",
                (result_entity_id,),
            ).fetchone()

            if result and result[0]:
                with contextlib.suppress(json.JSONDecodeError):
                    merged_data = json.loads(result[0])
                    current_aliases = merged_data.get("aliases", [])
                    current_merged_ids = merged_data.get("merged_ids", [])

                    names_to_remove = set()
                    for snapshot in source_snapshots:
                        names_to_remove.add(snapshot.get("canonical_name", ""))
                        names_to_remove.update(snapshot.get("aliases", []))

                    new_aliases = [a for a in current_aliases if a not in names_to_remove]
                    new_merged_ids = [
                        mid for mid in current_merged_ids if mid not in source_entity_ids
                    ]

                    conn.execute(
                        "UPDATE entities SET merged_from_ids = ?, updated_at = datetime('now') WHERE id = ?",
                        (json.dumps({"aliases": new_aliases, "merged_ids": new_merged_ids}), result_entity_id),
                    )

            # 5. Actualizar contador de menciones
            total_restored = sum(
                snapshots_by_id.get(eid, {}).get("mention_count", 0) for eid in source_entity_ids
            )
            if total_restored > 0:
                conn.execute(
                    "UPDATE entities SET mention_count = mention_count - ? WHERE id = ?",
                    (total_restored, result_entity_id),
                )

        logger.info(
            f"Fusión deshecha: restauradas {len(source_entity_ids)} entidades "
            f"desde entidad {result_entity_id}"
        )

    def _undo_entity_delete(self, entity_id: int, old_value: dict) -> None:
        """Revierte eliminación de entidad (reactivar soft-delete)."""
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE entities SET is_active = 1, updated_at = datetime('now') WHERE id = ?",
                (entity_id,),
            )
        logger.debug(f"Entidad {entity_id} restaurada (reactivada)")

    def _undo_entity_update(self, entity_id: int, old_value: dict) -> None:
        """Revierte actualización de entidad restaurando valores anteriores."""
        if not old_value:
            raise ValueError("No hay old_value para restaurar")

        sets = []
        params: list[Any] = []
        for key in ("canonical_name", "entity_type", "importance"):
            if key in old_value:
                sets.append(f"{key} = ?")
                params.append(old_value[key])

        if not sets:
            return

        sets.append("updated_at = datetime('now')")
        params.append(entity_id)

        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE entities SET {', '.join(sets)} WHERE id = ?",
                tuple(params),
            )
        logger.debug(f"Entidad {entity_id} restaurada a estado anterior")

    def _undo_alert_status_change(self, alert_id: int, old_value: dict) -> None:
        """Revierte cambio de status de alerta."""
        old_status = "open"
        if old_value and "status" in old_value:
            old_status = old_value["status"]

        with self.db.connection() as conn:
            conn.execute(
                "UPDATE alerts SET status = ? WHERE id = ?",
                (old_status, alert_id),
            )

            # Si se reabre, quitar dismissal persistido
            if old_status == "open":
                conn.execute(
                    """
                    DELETE FROM alert_dismissals
                    WHERE project_id = ? AND content_hash IN (
                        SELECT content_hash FROM alerts WHERE id = ?
                    )
                    """,
                    (self.project_id, alert_id),
                )

        logger.debug(f"Alerta {alert_id} restaurada a status '{old_status}'")

    def _undo_attribute_verification(self, attribute_id: int, old_value: dict) -> None:
        """Revierte verificación de atributo."""
        old_verified = 0
        old_attr_value = None
        if old_value:
            old_verified = 1 if old_value.get("is_verified") else 0
            old_attr_value = old_value.get("attribute_value")

        with self.db.connection() as conn:
            if old_attr_value is not None:
                conn.execute(
                    "UPDATE entity_attributes SET is_verified = ?, attribute_value = ? WHERE id = ?",
                    (old_verified, old_attr_value, attribute_id),
                )
            else:
                conn.execute(
                    "UPDATE entity_attributes SET is_verified = ? WHERE id = ?",
                    (old_verified, attribute_id),
                )
        logger.debug(f"Atributo {attribute_id} des-verificado")

    def _undo_attribute_change(self, attribute_id: int, old_value: dict) -> None:
        """Revierte cambio de valor de atributo."""
        if not old_value:
            raise ValueError("No hay old_value para restaurar atributo")

        with self.db.connection() as conn:
            if old_value.get("_was_new"):
                # El atributo fue creado — deshacerlo = eliminarlo
                conn.execute("DELETE FROM entity_attributes WHERE id = ?", (attribute_id,))
                logger.debug(f"Atributo {attribute_id} eliminado (undo de creación)")
            else:
                sets = []
                params: list[Any] = []
                for key in ("attribute_value", "attribute_key", "is_verified", "confidence"):
                    if key in old_value:
                        sets.append(f"{key} = ?")
                        params.append(old_value[key])
                if sets:
                    params.append(attribute_id)
                    conn.execute(
                        f"UPDATE entity_attributes SET {', '.join(sets)} WHERE id = ?",
                        tuple(params),
                    )
                logger.debug(f"Atributo {attribute_id} restaurado")

    def _undo_attribute_delete(self, attribute_id: int, old_value: dict) -> None:
        """Revierte eliminación de atributo (re-crearlo)."""
        if not old_value:
            raise ValueError("No hay old_value para restaurar atributo eliminado")

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO entity_attributes
                    (id, entity_id, attribute_key, attribute_value, is_verified, confidence, chapter_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attribute_id,
                    old_value.get("entity_id"),
                    old_value.get("attribute_key"),
                    old_value.get("attribute_value"),
                    old_value.get("is_verified", 0),
                    old_value.get("confidence", 0.0),
                    old_value.get("chapter_id"),
                ),
            )
        logger.debug(f"Atributo {attribute_id} restaurado (re-creado)")

    def _undo_relationship_change(self, action: str, target_id: int, old_value: dict) -> None:
        """Revierte cambio en relación."""
        if not old_value:
            raise ValueError("No hay old_value para restaurar relación")

        with self.db.connection() as conn:
            if action == "relationship_created":
                # Fue creada → deshacerlo = eliminarla
                conn.execute("DELETE FROM interactions WHERE id = ?", (target_id,))
                logger.debug(f"Relación {target_id} eliminada (undo de creación)")

            elif action == "relationship_deleted":
                # Fue eliminada → deshacerlo = re-crearla
                conn.execute(
                    """
                    INSERT OR IGNORE INTO interactions
                        (id, project_id, entity1_id, entity2_id, relationship_type, detail, chapter_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_id,
                        old_value.get("project_id", self.project_id),
                        old_value.get("entity1_id"),
                        old_value.get("entity2_id"),
                        old_value.get("relationship_type"),
                        old_value.get("detail"),
                        old_value.get("chapter_id"),
                    ),
                )
                logger.debug(f"Relación {target_id} restaurada (re-creada)")

            elif action == "relationship_updated":
                # Fue actualizada → restaurar valores anteriores
                conn.execute(
                    """
                    UPDATE interactions
                    SET relationship_type = ?, detail = ?
                    WHERE id = ?
                    """,
                    (
                        old_value.get("relationship_type"),
                        old_value.get("detail"),
                        target_id,
                    ),
                )
                logger.debug(f"Relación {target_id} restaurada a estado anterior")

    # ── Utilidades ──

    def get_undo_info(self, entry_id: int) -> dict | None:
        """Obtiene información para deshacer una acción (compatibilidad)."""
        entry = self.get_entry(entry_id)
        if not entry or not entry.old_value:
            return None

        return {
            "action_type": entry.action_type.value if entry.action_type else None,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "restore_value": entry.old_value,
            "description": _undo_description(entry),
        }

    def clear_old_entries(self, keep_days: int = 90) -> int:
        """
        DEPRECATED: El historial debe ser permanente según requisitos UX.

        Raises:
            NotImplementedError: Esta función está deprecada
        """
        raise NotImplementedError(
            "Función deprecada: el historial debe ser permanente sin caducidad."
        )


def _undo_description(entry: HistoryEntry) -> str:
    """Genera descripción legible de un undo."""
    descriptions = {
        "entity_merged": "Fusión de entidades deshecha",
        "entity_deleted": "Entidad restaurada",
        "entity_updated": "Cambio de entidad deshecho",
        "entity_created": "Creación de entidad deshecha",
        "alert_resolved": "Alerta reabierta",
        "alert_dismissed": "Alerta restaurada",
        "attribute_verified": "Verificación de atributo deshecha",
        "attribute_updated": "Cambio de atributo deshecho",
        "attribute_added": "Atributo eliminado (undo)",
        "attribute_deleted": "Atributo restaurado",
        "relationship_created": "Relación eliminada (undo)",
        "relationship_updated": "Cambio de relación deshecho",
        "relationship_deleted": "Relación restaurada",
    }
    base = descriptions.get(entry.action_type.value, f"Deshecho: {entry.action_type.value}")
    if entry.note:
        return f"{base} — {entry.note}"
    return base
