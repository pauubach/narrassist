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
                context={"error": str(e), "project_id": project_id},
            )
            logger.error(f"Failed to get alerts for project {project_id}: {e}")
            return Result.failure(error)

    def get_by_project_prioritized(
        self,
        project_id: int,
        current_chapter: Optional[int] = None,
        status_filter: Optional[list[AlertStatus]] = None,
    ) -> Result[list[Alert]]:
        """
        Obtiene alertas priorizadas por relevancia al capítulo actual.

        Orden de priorización:
        1. Alertas del capítulo actual (si se especifica)
        2. Alertas de capítulos cercanos (±2 capítulos)
        3. Por severidad (critical > high > medium > low > info)
        4. Por confianza (mayor primero)
        5. Por fecha de creación (más recientes primero)

        Args:
            project_id: ID del proyecto
            current_chapter: Capítulo que el usuario está viendo (None = sin priorización)
            status_filter: Lista de estados a incluir (None = todos)

        Returns:
            Result con lista de alertas priorizadas
        """
        try:
            # Construir query base
            query = """
                SELECT *,
                    CASE
                        WHEN chapter = ? THEN 0
                        WHEN chapter BETWEEN ? AND ? THEN 1
                        ELSE 2
                    END as chapter_priority,
                    CASE severity
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        WHEN 'info' THEN 4
                        ELSE 5
                    END as severity_priority
                FROM alerts
                WHERE project_id = ?
            """

            # Parámetros base para chapter_priority
            chapter_for_priority = current_chapter if current_chapter is not None else -999
            nearby_start = chapter_for_priority - 2
            nearby_end = chapter_for_priority + 2

            params: list = [chapter_for_priority, nearby_start, nearby_end, project_id]

            # Añadir filtro de status si se especifica
            if status_filter:
                placeholders = ",".join("?" * len(status_filter))
                query += f" AND status IN ({placeholders})"
                params.extend([s.value for s in status_filter])

            # Ordenar por prioridad
            query += """
                ORDER BY
                    chapter_priority ASC,
                    severity_priority ASC,
                    confidence DESC,
                    created_at DESC
            """

            with self.db.connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            alerts = [self._row_to_alert(row) for row in rows]
            logger.debug(
                f"Retrieved {len(alerts)} prioritized alerts for project {project_id}, "
                f"current_chapter={current_chapter}"
            )
            return Result.success(alerts)

        except Exception as e:
            error = DatabaseError(
                message="Error retrieving prioritized alerts",
                context={"error": str(e), "project_id": project_id, "current_chapter": current_chapter},
            )
            logger.error(f"Failed to get prioritized alerts for project {project_id}: {e}")
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
                context={"error": str(e), "alert_id": alert.id},
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
                context={"error": str(e), "project_id": project_id},
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
