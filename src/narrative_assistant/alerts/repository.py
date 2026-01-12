"""
Repositorio de persistencia para alertas.

Maneja CRUD de alertas en la base de datos SQLite.
"""

import json
import logging
import threading
from datetime import datetime
from typing import Optional

from ..core.errors import DatabaseError, NarrativeError
from ..core.result import Result
from ..persistence.database import get_database
from .models import Alert, AlertCategory, AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_repository_lock = threading.Lock()
_alert_repository: Optional["AlertRepository"] = None


class AlertRepository:
    """
    Repositorio para almacenar y recuperar alertas.

    Usa SQLite como backend de persistencia.
    """

    def __init__(self):
        """Inicializa el repositorio."""
        self.db = get_database()

    def create(self, alert: Alert) -> Result[Alert]:
        """
        Crea una nueva alerta en la base de datos.

        Args:
            alert: Alerta a crear

        Returns:
            Result con la alerta creada (incluyendo ID asignado)
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO alerts (
                        project_id, category, severity, alert_type,
                        title, description, explanation, suggestion,
                        chapter, scene, start_char, end_char, excerpt,
                        entity_ids, confidence, source_module,
                        created_at, updated_at, status, resolved_at,
                        resolution_note, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert.project_id,
                        alert.category.value,
                        alert.severity.value,
                        alert.alert_type,
                        alert.title,
                        alert.description,
                        alert.explanation,
                        alert.suggestion,
                        alert.chapter,
                        alert.scene,
                        alert.start_char,
                        alert.end_char,
                        alert.excerpt,
                        json.dumps(alert.entity_ids),
                        alert.confidence,
                        alert.source_module,
                        alert.created_at.isoformat() if alert.created_at else None,
                        alert.updated_at.isoformat() if alert.updated_at else None,
                        alert.status.value,
                        alert.resolved_at.isoformat() if alert.resolved_at else None,
                        alert.resolution_note,
                        json.dumps(alert.extra_data),
                    ),
                )
                alert.id = cursor.lastrowid

            logger.info(f"Created alert {alert.id} for project {alert.project_id}")
            return Result.success(alert)

        except Exception as e:
            error = DatabaseError(
                message="Error creating alert",
                context={"error": str(e), "project_id": alert.project_id},
            )
            logger.error(f"Failed to create alert: {e}")
            return Result.failure(error)

    def get(self, alert_id: int) -> Result[Alert]:
        """
        Obtiene una alerta por ID.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result con la alerta encontrada
        """
        try:
            with self.db.connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM alerts WHERE id = ?",
                    (alert_id,),
                )
                row = cursor.fetchone()

            if not row:
                error = NarrativeError(
                    message=f"Alert {alert_id} not found"
                )
                return Result.failure(error)

            alert = self._row_to_alert(row)
            return Result.success(alert)

        except Exception as e:
            error = DatabaseError(
                message="Error retrieving alert",
                context={"error": str(e), "alert_id": alert_id},
            )
            logger.error(f"Failed to get alert {alert_id}: {e}")
            return Result.failure(error)

    def get_by_project(self, project_id: int) -> Result[list[Alert]]:
        """
        Obtiene todas las alertas de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con lista de alertas
        """
        try:
            with self.db.connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM alerts WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                )
                rows = cursor.fetchall()

            alerts = [self._row_to_alert(row) for row in rows]
            logger.debug(f"Retrieved {len(alerts)} alerts for project {project_id}")
            return Result.success(alerts)

        except Exception as e:
            error = DatabaseError(
                message="Error retrieving alerts",
                details={"error": str(e), "project_id": project_id},
            )
            logger.error(f"Failed to get alerts for project {project_id}: {e}")
            return Result.failure(error)

    def update(self, alert: Alert) -> Result[Alert]:
        """
        Actualiza una alerta existente.

        Args:
            alert: Alerta con cambios

        Returns:
            Result con la alerta actualizada
        """
        try:
            alert.updated_at = datetime.now()

            with self.db.transaction() as conn:
                conn.execute(
                    """
                    UPDATE alerts SET
                        category = ?, severity = ?, alert_type = ?,
                        title = ?, description = ?, explanation = ?, suggestion = ?,
                        chapter = ?, scene = ?, start_char = ?, end_char = ?, excerpt = ?,
                        entity_ids = ?, confidence = ?, source_module = ?,
                        updated_at = ?, status = ?, resolved_at = ?,
                        resolution_note = ?, extra_data = ?
                    WHERE id = ?
                    """,
                    (
                        alert.category.value,
                        alert.severity.value,
                        alert.alert_type,
                        alert.title,
                        alert.description,
                        alert.explanation,
                        alert.suggestion,
                        alert.chapter,
                        alert.scene,
                        alert.start_char,
                        alert.end_char,
                        alert.excerpt,
                        json.dumps(alert.entity_ids),
                        alert.confidence,
                        alert.source_module,
                        alert.updated_at.isoformat(),
                        alert.status.value,
                        alert.resolved_at.isoformat() if alert.resolved_at else None,
                        alert.resolution_note,
                        json.dumps(alert.extra_data),
                        alert.id,
                    ),
                )

            logger.info(f"Updated alert {alert.id}")
            return Result.success(alert)

        except Exception as e:
            error = DatabaseError(
                message="Error updating alert",
                details={"error": str(e), "alert_id": alert.id},
            )
            logger.error(f"Failed to update alert {alert.id}: {e}")
            return Result.failure(error)

    def delete(self, alert_id: int) -> Result[None]:
        """
        Elimina una alerta.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result indicando éxito o fallo
        """
        try:
            with self.db.transaction() as conn:
                conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

            logger.info(f"Deleted alert {alert_id}")
            return Result.success(None)

        except Exception as e:
            error = DatabaseError(
                message="Error deleting alert",
                context={"error": str(e), "alert_id": alert_id},
            )
            logger.error(f"Failed to delete alert {alert_id}: {e}")
            return Result.failure(error)

    def count_by_status(self, project_id: int) -> Result[dict[str, int]]:
        """
        Cuenta alertas por estado.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con diccionario {status: count}
        """
        try:
            with self.db.connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM alerts
                    WHERE project_id = ?
                    GROUP BY status
                    """,
                    (project_id,),
                )
                rows = cursor.fetchall()

            counts = {row[0]: row[1] for row in rows}
            return Result.success(counts)

        except Exception as e:
            error = DatabaseError(
                message="Error counting alerts",
                details={"error": str(e), "project_id": project_id},
            )
            logger.error(f"Failed to count alerts for project {project_id}: {e}")
            return Result.failure(error)

    def _row_to_alert(self, row) -> Alert:
        """Convierte una fila de DB a objeto Alert."""
        # sqlite3.Row permite acceso por nombre de columna
        return Alert(
            id=row["id"],
            project_id=row["project_id"],
            category=AlertCategory(row["category"]),
            severity=AlertSeverity(row["severity"]),
            alert_type=row["alert_type"],
            title=row["title"],
            description=row["description"],
            explanation=row["explanation"],
            suggestion=row["suggestion"],
            chapter=row["chapter"],
            scene=row["scene"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            excerpt=row["excerpt"] or "",
            entity_ids=json.loads(row["entity_ids"]) if row["entity_ids"] else [],
            confidence=row["confidence"] or 0.8,
            source_module=row["source_module"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            status=AlertStatus(row["status"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            resolution_note=row["resolution_note"] or "",
            extra_data=json.loads(row["extra_data"]) if row["extra_data"] else {},
        )


def get_alert_repository() -> AlertRepository:
    """
    Obtiene la instancia singleton del repositorio de alertas.

    Thread-safe con double-checked locking.

    Returns:
        Instancia única de AlertRepository
    """
    global _alert_repository

    if _alert_repository is None:
        with _repository_lock:
            if _alert_repository is None:
                _alert_repository = AlertRepository()
                logger.debug("AlertRepository singleton initialized")

    return _alert_repository
