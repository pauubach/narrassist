"""
Repositorio de persistencia para eventos narrativos.

Almacena eventos detectados por event_detection.py y event_detection_llm.py
en la tabla narrative_events (schema v30).
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime

from ..core.errors import DatabaseError
from ..core.result import Result
from .database import get_database

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_repository_lock = threading.Lock()
_event_repository: "EventRepository | None" = None


@dataclass
class NarrativeEvent:
    """Evento narrativo persistido."""

    id: int
    project_id: int
    chapter: int | None
    event_type: str  # EventType enum value
    tier: int
    description: str
    start_char: int | None
    end_char: int | None
    entity_ids: list[int]  # Parsed from JSON
    confidence: float
    metadata: dict  # Parsed from JSON
    created_at: datetime


class EventRepository:
    """
    Repositorio para almacenar y consultar eventos narrativos.

    Funcionalidades:
    - Guardar eventos detectados en análisis
    - Recuperar eventos por proyecto/capítulo
    - Eliminar eventos en re-análisis
    - Filtrar por tipo de evento o entidad
    """

    def __init__(self):
        """Inicializa el repositorio."""
        self.db = get_database()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def save_events(
        self, project_id: int, events: list[dict]
    ) -> Result[int]:
        """
        Guarda múltiples eventos en batch.

        Args:
            project_id: ID del proyecto
            events: Lista de eventos como dicts con campos:
                - event_type: str (EventType.value)
                - tier: int
                - description: str
                - chapter: int | None
                - start_char: int | None
                - end_char: int | None
                - entity_ids: list[int]
                - confidence: float
                - metadata: dict

        Returns:
            Result con número de eventos guardados
        """
        if not events:
            return Result.success(0)

        try:
            with self.db.transaction() as conn:
                for event in events:
                    conn.execute(
                        """
                        INSERT INTO narrative_events (
                            project_id, chapter, event_type, tier, description,
                            start_char, end_char, entity_ids, confidence, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            event.get("chapter"),
                            event["event_type"],
                            event["tier"],
                            event["description"],
                            event.get("start_char"),
                            event.get("end_char"),
                            json.dumps(event.get("entity_ids", [])),
                            event.get("confidence", 0.8),
                            json.dumps(event.get("metadata", {})),
                        ),
                    )

            logger.info(f"Guardados {len(events)} eventos para proyecto {project_id}")
            return Result.success(len(events))

        except Exception as e:
            logger.error(f"Error guardando eventos: {e}")
            return Result.failure(
                DatabaseError(f"Error guardando eventos: {e}")
            )

    def get_by_project(self, project_id: int) -> Result[list[NarrativeEvent]]:
        """
        Obtiene todos los eventos de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con lista de eventos
        """
        try:
            with self.db.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, project_id, chapter, event_type, tier, description,
                           start_char, end_char, entity_ids, confidence, metadata,
                           created_at
                    FROM narrative_events
                    WHERE project_id = ?
                    ORDER BY chapter, start_char
                    """,
                    (project_id,),
                ).fetchall()

                events = [self._row_to_event(row) for row in rows]
                return Result.success(events)

        except Exception as e:
            logger.error(f"Error obteniendo eventos: {e}")
            return Result.failure(
                DatabaseError(f"Error obteniendo eventos: {e}")
            )

    def get_by_chapter(
        self, project_id: int, chapter: int
    ) -> Result[list[NarrativeEvent]]:
        """
        Obtiene eventos de un capítulo específico.

        Args:
            project_id: ID del proyecto
            chapter: Número de capítulo

        Returns:
            Result con lista de eventos
        """
        try:
            with self.db.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, project_id, chapter, event_type, tier, description,
                           start_char, end_char, entity_ids, confidence, metadata,
                           created_at
                    FROM narrative_events
                    WHERE project_id = ? AND chapter = ?
                    ORDER BY start_char
                    """,
                    (project_id, chapter),
                ).fetchall()

                events = [self._row_to_event(row) for row in rows]
                return Result.success(events)

        except Exception as e:
            logger.error(f"Error obteniendo eventos del capítulo: {e}")
            return Result.failure(
                DatabaseError(f"Error obteniendo eventos del capítulo: {e}")
            )

    def get_by_entity(
        self, project_id: int, entity_id: int
    ) -> Result[list[NarrativeEvent]]:
        """
        Obtiene eventos que involucran a una entidad específica.

        Args:
            project_id: ID del proyecto
            entity_id: ID de la entidad

        Returns:
            Result con lista de eventos
        """
        try:
            with self.db.connection() as conn:
                # Buscar entity_id en el JSON array usando json_each (preciso)
                rows = conn.execute(
                    """
                    SELECT DISTINCT ne.id, ne.project_id, ne.chapter, ne.event_type,
                           ne.tier, ne.description, ne.start_char, ne.end_char,
                           ne.entity_ids, ne.confidence, ne.metadata, ne.created_at
                    FROM narrative_events ne, json_each(ne.entity_ids) je
                    WHERE ne.project_id = ?
                      AND je.value = ?
                    ORDER BY ne.chapter, ne.start_char
                    """,
                    (project_id, entity_id),
                ).fetchall()

                events = [self._row_to_event(row) for row in rows]

                return Result.success(events)

        except Exception as e:
            logger.error(f"Error obteniendo eventos por entidad: {e}")
            return Result.failure(
                DatabaseError(f"Error obteniendo eventos por entidad: {e}")
            )

    def delete_by_project(self, project_id: int) -> Result[int]:
        """
        Elimina todos los eventos de un proyecto.

        Útil para re-análisis completo.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con número de eventos eliminados
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    "DELETE FROM narrative_events WHERE project_id = ?",
                    (project_id,),
                )
                deleted = cursor.rowcount

            logger.info(f"Eliminados {deleted} eventos del proyecto {project_id}")
            return Result.success(deleted)

        except Exception as e:
            logger.error(f"Error eliminando eventos: {e}")
            return Result.failure(
                DatabaseError(f"Error eliminando eventos: {e}")
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_event(self, row: tuple) -> NarrativeEvent:
        """Convierte una fila SQL a NarrativeEvent."""
        return NarrativeEvent(
            id=row[0],
            project_id=row[1],
            chapter=row[2],
            event_type=row[3],
            tier=row[4],
            description=row[5],
            start_char=row[6],
            end_char=row[7],
            entity_ids=json.loads(row[8]) if row[8] else [],
            confidence=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
        )


# =============================================================================
# Singleton
# =============================================================================

def get_event_repository() -> EventRepository:
    """
    Obtiene instancia singleton del repositorio de eventos.

    Returns:
        EventRepository singleton
    """
    global _event_repository

    if _event_repository is None:
        with _repository_lock:
            if _event_repository is None:
                _event_repository = EventRepository()

    return _event_repository
