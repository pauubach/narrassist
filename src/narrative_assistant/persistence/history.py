"""
Historial de cambios y acciones del revisor.

Permite:
- Auditoría de decisiones
- Undo/redo
- Análisis de patrones de corrección
"""

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .database import Database, get_database

logger = logging.getLogger(__name__)


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

    # Proyecto
    PROJECT_CREATED = "project_created"
    PROJECT_SETTINGS_CHANGED = "project_settings_changed"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"

    # Otros
    UNDO = "undo"
    OTHER = "other"


@dataclass
class HistoryEntry:
    """
    Entrada en el historial de cambios.

    Attributes:
        id: ID en base de datos
        project_id: Proyecto asociado
        action_type: Tipo de acción
        target_type: Tipo de objeto afectado (alert, entity, etc.)
        target_id: ID del objeto afectado
        old_value: Valor anterior (para undo)
        new_value: Valor nuevo
        note: Nota del revisor
        created_at: Timestamp
    """

    id: int | None = None
    project_id: int = 0
    action_type: ChangeType = ChangeType.ALERT_CREATED
    target_type: str = ""
    target_id: int | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    note: str = ""
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "HistoryEntry":
        """Crea desde fila de SQLite."""
        old_value = None
        new_value = None

        if row["old_value_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                old_value = json.loads(row["old_value_json"])

        if row["new_value_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                new_value = json.loads(row["new_value_json"])

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
        )

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
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
        }


class HistoryManager:
    """
    Gestiona el historial de cambios de un proyecto.

    Uso:
        history = HistoryManager(project_id=1)
        history.record(
            ChangeType.ENTITY_MERGED,
            target_type="entity",
            target_id=5,
            old_value={"names": ["Juan", "Juanito"]},
            new_value={"canonical_name": "Juan"},
            note="Fusionados por contexto"
        )
    """

    def __init__(self, project_id: int, db: Database | None = None):
        self.project_id = project_id
        self.db = db or get_database()

    def record(
        self,
        action_type: ChangeType,
        target_type: str = "",
        target_id: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        note: str = "",
    ) -> HistoryEntry:
        """
        Registra un cambio en el historial.

        Args:
            action_type: Tipo de acción
            target_type: Tipo de objeto (alert, entity, attribute)
            target_id: ID del objeto afectado
            old_value: Estado anterior (para undo)
            new_value: Estado nuevo
            note: Nota explicativa

        Returns:
            HistoryEntry creada
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO review_history (
                    project_id, action_type, target_type, target_id,
                    old_value_json, new_value_json, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.project_id,
                    action_type.value,
                    target_type,
                    target_id,
                    json.dumps(old_value) if old_value else None,
                    json.dumps(new_value) if new_value else None,
                    note,
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
        )

        logger.debug(f"Historial: {action_type.value} on {target_type}:{target_id}")
        return entry

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        action_types: list[ChangeType] | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
    ) -> list[HistoryEntry]:
        """
        Obtiene entradas del historial con filtros opcionales.

        Args:
            limit: Máximo de entradas
            offset: Offset para paginación
            action_types: Filtrar por tipos de acción
            target_type: Filtrar por tipo de objeto
            target_id: Filtrar por ID de objeto
        """
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
        """
        Obtiene estadísticas del historial.

        Returns:
            Dict con conteos por tipo de acción
        """
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

    def can_undo(self, entry_id: int) -> bool:
        """
        Verifica si una entrada puede ser deshecha.

        Solo se pueden deshacer acciones que tienen old_value.
        """
        entry = self.get_entry(entry_id)
        if not entry:
            return False
        return entry.old_value is not None

    def get_undo_info(self, entry_id: int) -> dict | None:
        """
        Obtiene información para deshacer una acción.

        Returns:
            Dict con target_type, target_id, old_value o None
        """
        entry = self.get_entry(entry_id)
        if not entry or not entry.old_value:
            return None

        return {
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "restore_value": entry.old_value,
            "description": f"Deshacer: {entry.action_type.value}",
        }

    def clear_old_entries(self, keep_days: int = 90) -> int:
        """
        DEPRECATED: El historial debe ser permanente según requisitos UX.

        Esta función solo debe usarse manualmente para limpieza de proyectos
        abandonados o por solicitud explícita del usuario.

        IMPORTANTE: Nunca llamar automáticamente desde el pipeline.

        Args:
            keep_days: Días a mantener

        Returns:
            Número de entradas eliminadas

        Raises:
            NotImplementedError: Esta función está deprecada
        """
        logger.warning(
            "clear_old_entries() está DEPRECADO. El historial debe ser permanente. "
            "Solo usar para limpieza manual de proyectos abandonados con confirmación explícita del usuario."
        )

        raise NotImplementedError(
            "Función deprecada según requisitos UX: el historial debe ser permanente sin caducidad. "
            "Para limpiar manualmente un proyecto abandonado, usar un método alternativo con confirmación explícita."
        )

    def undo(self, entry_id: int) -> bool:
        """
        Deshace una acción restaurando el estado previo.

        NOTA: Implementación inicial con soporte básico.
        Para implementación completa con verificación de dependencias,
        ver docs/05-ui-design/BACKEND_GAPS_ANALYSIS.md

        Args:
            entry_id: ID de la entrada de historial a deshacer

        Returns:
            True si se deshizo exitosamente, False si no fue posible

        Example:
            >>> manager = HistoryManager(project_id=1)
            >>> entry_id = manager.record("ENTITY_MERGED", target_id=42, old_value={...})
            >>> success = manager.undo(entry_id)
            >>> print(success)
            True
        """
        # 1. Verificar que la acción es reversible
        if not self.can_undo(entry_id):
            logger.warning(f"La acción {entry_id} no es reversible")
            return False

        # 2. Obtener información de undo
        undo_info = self.get_undo_info(entry_id)
        if not undo_info:
            logger.error(f"No se encontró información de undo para {entry_id}")
            return False

        # 3. TODO: Verificar conflictos/dependencias
        # conflicts = self.check_undo_conflicts(entry_id)
        # if conflicts:
        #     logger.warning(f"Undo tiene {len(conflicts)} conflictos")
        #     return False

        # 4. Ejecutar undo según tipo de acción
        action_type = undo_info["action_type"]
        target_id = undo_info.get("target_id")
        old_value = undo_info.get("restore_value")

        logger.info(f"Deshaciendo acción {entry_id}: {action_type}")

        try:
            # Dispatch por tipo de acción
            # NOTA: Implementación básica - extender según necesidades
            if action_type == "ENTITY_MERGED":
                self._undo_entity_merge(target_id, old_value)

            elif action_type == "ALERT_RESOLVED":
                # Re-abrir alerta
                self._undo_alert_resolution(target_id)

            elif action_type == "ATTRIBUTE_VERIFIED":
                # Des-verificar atributo
                self._undo_attribute_verification(target_id)

            else:
                logger.warning(f"Tipo de acción {action_type} no soportado para undo")
                return False

            # 5. Registrar la reversión en el historial
            self.record(
                action_type=ChangeType.UNDO,
                target_type=undo_info.get("target_type"),
                target_id=target_id,
                note=f"Deshecha acción #{entry_id}: {action_type}",
            )

            logger.info(f"Acción {entry_id} deshecha exitosamente")
            return True

        except Exception as e:
            logger.error(f"Error deshaciendo acción {entry_id}: {e}", exc_info=True)
            return False

    def _undo_alert_resolution(self, alert_id: int) -> None:
        """
        Revierte resolución de alerta (cambia status de resolved a open).

        Args:
            alert_id: ID de la alerta

        Example:
            >>> manager._undo_alert_resolution(42)
        """
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE alerts SET status = 'open' WHERE id = ?",
                (alert_id,),
            )
        logger.debug(f"Alerta {alert_id} re-abierta")

    def _undo_attribute_verification(self, attribute_id: int) -> None:
        """
        Revierte verificación de atributo (cambia is_verified de True a False).

        Args:
            attribute_id: ID del atributo

        Example:
            >>> manager._undo_attribute_verification(42)
        """
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE entity_attributes SET is_verified = 0 WHERE id = ?",
                (attribute_id,),
            )
        logger.debug(f"Atributo {attribute_id} des-verificado")

    def _undo_entity_merge(self, result_entity_id: int, old_value: dict) -> None:
        """
        Revierte fusión de entidades restaurando las entidades originales.

        Args:
            result_entity_id: ID de la entidad resultado de la fusión
            old_value: Datos de la fusión original con source_entity_ids y source_snapshots

        El proceso:
        1. Obtener IDs de entidades fusionadas desde old_value
        2. Reactivar las entidades fusionadas (is_active = 1)
        3. Mover menciones de vuelta a sus entidades originales
        4. Mover atributos de vuelta a sus entidades originales
        5. Restaurar aliases originales en entidad principal
        6. Actualizar merged_from_ids en entidad principal

        Example:
            >>> manager._undo_entity_merge(42, {
            ...     "source_entity_ids": [10, 11],
            ...     "source_snapshots": [
            ...         {"id": 10, "canonical_name": "Juan", "mention_count": 5},
            ...         {"id": 11, "canonical_name": "Juanito", "mention_count": 3}
            ...     ]
            ... })
        """
        if not old_value:
            logger.error("No hay información de fusión para deshacer")
            return

        source_entity_ids = old_value.get("source_entity_ids", [])
        source_snapshots = old_value.get("source_snapshots", [])

        if not source_entity_ids:
            logger.error("No hay entidades fuente para restaurar")
            return

        # Crear mapeo de snapshot por ID
        snapshots_by_id = {s["id"]: s for s in source_snapshots}

        with self.db.connection() as conn:
            # 1. Reactivar las entidades fusionadas
            for entity_id in source_entity_ids:
                conn.execute(
                    "UPDATE entities SET is_active = 1, updated_at = datetime('now') WHERE id = ?",
                    (entity_id,),
                )
                logger.debug(f"Entidad {entity_id} reactivada")

            # 2. Mover menciones de vuelta a sus entidades originales
            # Usamos la información del snapshot para identificar las menciones
            # que pertenecían a cada entidad (basado en mention_count)
            for entity_id in source_entity_ids:
                snapshot = snapshots_by_id.get(entity_id, {})
                original_mention_count = snapshot.get("mention_count", 0)

                if original_mention_count > 0:
                    # Mover las menciones más recientes de vuelta
                    # (asumimos que las menciones se agregaron al final)
                    conn.execute(
                        """
                        UPDATE entity_mentions
                        SET entity_id = ?
                        WHERE id IN (
                            SELECT id FROM entity_mentions
                            WHERE entity_id = ?
                            ORDER BY id DESC
                            LIMIT ?
                        )
                        """,
                        (entity_id, result_entity_id, original_mention_count),
                    )
                    logger.debug(
                        f"Movidas ~{original_mention_count} menciones a entidad {entity_id}"
                    )

            # 3. Mover atributos de vuelta
            # Los atributos se identifican por su entity_id original antes de la fusión
            for entity_id in source_entity_ids:
                # Buscar atributos que originalmente pertenecían a esta entidad
                # usando la tabla de evidencias o metadata si existe
                conn.execute(
                    """
                    UPDATE entity_attributes
                    SET entity_id = ?
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

            # 4. Restaurar aliases originales en la entidad principal
            # Obtener la entidad principal actual
            result = conn.execute(
                "SELECT merged_from_ids FROM entities WHERE id = ?",
                (result_entity_id,),
            ).fetchone()

            if result and result[0]:
                try:
                    merged_data = json.loads(result[0])
                    current_aliases = merged_data.get("aliases", [])
                    current_merged_ids = merged_data.get("merged_ids", [])

                    # Remover los aliases que vinieron de las entidades fusionadas
                    names_to_remove = set()
                    for snapshot in source_snapshots:
                        names_to_remove.add(snapshot.get("canonical_name", ""))
                        names_to_remove.update(snapshot.get("aliases", []))

                    new_aliases = [a for a in current_aliases if a not in names_to_remove]
                    new_merged_ids = [
                        mid for mid in current_merged_ids if mid not in source_entity_ids
                    ]

                    # Actualizar la entidad principal
                    new_merged_data = json.dumps(
                        {
                            "aliases": new_aliases,
                            "merged_ids": new_merged_ids,
                        }
                    )

                    conn.execute(
                        "UPDATE entities SET merged_from_ids = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_merged_data, result_entity_id),
                    )
                except json.JSONDecodeError:
                    logger.warning("Error parseando merged_from_ids")

            # 5. Actualizar contador de menciones en la entidad principal
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
