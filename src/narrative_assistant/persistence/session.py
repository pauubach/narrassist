"""
Gestión de sesiones de trabajo.

Una sesión representa un período de trabajo del revisor en un proyecto.
Permite:
- Reanudar donde se dejó
- Tracking de progreso
- Métricas de productividad
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .database import Database, get_database

logger = logging.getLogger(__name__)


class AlertAction(Enum):
    """Acciones que el revisor puede tomar sobre alertas."""

    REVIEWED = "reviewed"  # Visto, pendiente de decisión
    RESOLVED = "resolved"  # Problema corregido
    DISMISSED = "dismissed"  # Ignorado (falso positivo)
    DEFERRED = "deferred"  # Pospuesto para después


@dataclass
class Session:
    """
    Sesión de trabajo en un proyecto.

    Attributes:
        id: ID en base de datos
        project_id: Proyecto asociado
        started_at: Inicio de sesión
        ended_at: Fin de sesión (None si activa)
        duration_seconds: Duración total
        alerts_reviewed: Alertas revisadas
        alerts_resolved: Alertas resueltas
        entities_merged: Entidades fusionadas
        last_position_char: Última posición en el texto
        last_chapter_id: Último capítulo visitado
        notes: Notas del revisor
    """

    id: Optional[int] = None
    project_id: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    alerts_reviewed: int = 0
    alerts_resolved: int = 0
    entities_merged: int = 0
    last_position_char: Optional[int] = None
    last_chapter_id: Optional[int] = None
    notes: str = ""

    @property
    def is_active(self) -> bool:
        """True si la sesión está activa (no cerrada)."""
        return self.ended_at is None

    @property
    def duration_minutes(self) -> float:
        """Duración en minutos."""
        return self.duration_seconds / 60

    @classmethod
    def from_row(cls, row) -> "Session":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            duration_seconds=row["duration_seconds"] or 0,
            alerts_reviewed=row["alerts_reviewed"] or 0,
            alerts_resolved=row["alerts_resolved"] or 0,
            entities_merged=row["entities_merged"] or 0,
            last_position_char=row["last_position_char"],
            last_chapter_id=row["last_chapter_id"],
            notes=row["notes"] or "",
        )


class SessionManager:
    """
    Gestiona sesiones de trabajo.

    Uso:
        manager = SessionManager(project_id=1)
        session = manager.start()
        # ... trabajo ...
        manager.record_alert_action(alert_id, AlertAction.RESOLVED)
        manager.update_position(chapter_id=5, char_position=12345)
        manager.end()
    """

    def __init__(self, project_id: int, db: Optional[Database] = None):
        self.project_id = project_id
        self.db = db or get_database()
        self._current_session: Optional[Session] = None

    @property
    def current_session(self) -> Optional[Session]:
        """Sesión actual activa."""
        return self._current_session

    def start(self) -> Session:
        """
        Inicia una nueva sesión.

        Si hay una sesión activa sin cerrar, la cierra primero.
        """
        # Cerrar sesión anterior si existe
        self._close_stale_sessions()

        # Crear nueva sesión
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (project_id, started_at)
                VALUES (?, datetime('now'))
                """,
                (self.project_id,),
            )
            session_id = cursor.lastrowid

        # Obtener sesión creada
        row = self.db.fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
        self._current_session = Session.from_row(row)

        logger.info(f"Sesión iniciada: {self._current_session.id}")
        return self._current_session

    def end(self, notes: str = "") -> Session:
        """
        Finaliza la sesión actual.

        Args:
            notes: Notas opcionales del revisor
        """
        if not self._current_session:
            raise ValueError("No hay sesión activa")

        # Calcular duración
        started = self._current_session.started_at
        duration = int((datetime.now() - started).total_seconds()) if started else 0

        self.db.execute(
            """
            UPDATE sessions SET
                ended_at = datetime('now'),
                duration_seconds = ?,
                notes = COALESCE(notes || ?, notes, ?)
            WHERE id = ?
            """,
            (duration, notes, notes, self._current_session.id),
        )

        # Actualizar objeto
        self._current_session.ended_at = datetime.now()
        self._current_session.duration_seconds = duration
        if notes:
            self._current_session.notes = (
                self._current_session.notes + notes
                if self._current_session.notes
                else notes
            )

        logger.info(f"Sesión finalizada: {self._current_session.id} ({duration}s)")

        ended_session = self._current_session
        self._current_session = None
        return ended_session

    def _close_stale_sessions(self) -> None:
        """Cierra sesiones que quedaron abiertas (crash, etc.)."""
        self.db.execute(
            """
            UPDATE sessions SET
                ended_at = datetime('now'),
                duration_seconds = CAST(
                    (julianday('now') - julianday(started_at)) * 86400 AS INTEGER
                )
            WHERE project_id = ? AND ended_at IS NULL
            """,
            (self.project_id,),
        )

    def record_alert_action(self, alert_id: int, action: AlertAction) -> None:
        """
        Registra una acción sobre una alerta.

        Args:
            alert_id: ID de la alerta
            action: Acción tomada
        """
        if not self._current_session:
            return

        # Actualizar contadores
        if action == AlertAction.RESOLVED:
            self._current_session.alerts_resolved += 1
            self.db.execute(
                "UPDATE sessions SET alerts_resolved = alerts_resolved + 1 WHERE id = ?",
                (self._current_session.id,),
            )

        if action in (AlertAction.REVIEWED, AlertAction.RESOLVED, AlertAction.DISMISSED):
            self._current_session.alerts_reviewed += 1
            self.db.execute(
                "UPDATE sessions SET alerts_reviewed = alerts_reviewed + 1 WHERE id = ?",
                (self._current_session.id,),
            )

    def record_entity_merge(self) -> None:
        """Registra una fusión de entidades."""
        if not self._current_session:
            return

        self._current_session.entities_merged += 1
        self.db.execute(
            "UPDATE sessions SET entities_merged = entities_merged + 1 WHERE id = ?",
            (self._current_session.id,),
        )

    def update_position(
        self,
        chapter_id: Optional[int] = None,
        char_position: Optional[int] = None,
    ) -> None:
        """
        Actualiza la última posición visitada.

        Permite reanudar donde se dejó.
        """
        if not self._current_session:
            return

        updates = []
        params = []

        if chapter_id is not None:
            updates.append("last_chapter_id = ?")
            params.append(chapter_id)
            self._current_session.last_chapter_id = chapter_id

        if char_position is not None:
            updates.append("last_position_char = ?")
            params.append(char_position)
            self._current_session.last_position_char = char_position

        if updates:
            params.append(self._current_session.id)
            self.db.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )

    def get_last_position(self) -> tuple[Optional[int], Optional[int]]:
        """
        Obtiene la última posición de la sesión más reciente.

        Returns:
            Tupla (chapter_id, char_position)
        """
        row = self.db.fetchone(
            """
            SELECT last_chapter_id, last_position_char
            FROM sessions
            WHERE project_id = ? AND ended_at IS NOT NULL
            ORDER BY ended_at DESC
            LIMIT 1
            """,
            (self.project_id,),
        )

        if row:
            return row["last_chapter_id"], row["last_position_char"]
        return None, None

    def get_project_stats(self) -> dict:
        """
        Obtiene estadísticas agregadas de todas las sesiones del proyecto.

        Returns:
            Dict con métricas totales
        """
        row = self.db.fetchone(
            """
            SELECT
                COUNT(*) as session_count,
                SUM(duration_seconds) as total_duration,
                SUM(alerts_reviewed) as total_alerts_reviewed,
                SUM(alerts_resolved) as total_alerts_resolved,
                SUM(entities_merged) as total_entities_merged,
                MIN(started_at) as first_session,
                MAX(ended_at) as last_session
            FROM sessions
            WHERE project_id = ?
            """,
            (self.project_id,),
        )

        return {
            "session_count": row["session_count"] or 0,
            "total_duration_seconds": row["total_duration"] or 0,
            "total_duration_hours": (row["total_duration"] or 0) / 3600,
            "total_alerts_reviewed": row["total_alerts_reviewed"] or 0,
            "total_alerts_resolved": row["total_alerts_resolved"] or 0,
            "total_entities_merged": row["total_entities_merged"] or 0,
            "first_session": row["first_session"],
            "last_session": row["last_session"],
        }

    def list_sessions(self, limit: int = 20) -> list[Session]:
        """Lista las sesiones más recientes del proyecto."""
        rows = self.db.fetchall(
            """
            SELECT * FROM sessions
            WHERE project_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (self.project_id, limit),
        )
        return [Session.from_row(row) for row in rows]
