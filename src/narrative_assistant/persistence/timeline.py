"""
Repositorio de Timeline.

Gestiona el almacenamiento y recuperación de eventos temporales y marcadores.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from .database import Database, get_database

logger = logging.getLogger(__name__)


@dataclass
class TimelineEventData:
    """Datos de un evento del timeline almacenado."""

    id: int | None
    project_id: int
    event_id: str
    chapter: int | None
    paragraph: int | None
    description: str
    story_date: str | None
    story_date_resolution: str = "UNKNOWN"
    narrative_order: str = "CHRONOLOGICAL"
    discourse_position: int | None = None
    confidence: float = 0.5
    # Para timelines sin fechas absolutas (Día 0, Día +1, etc.)
    day_offset: float | None = None
    weekday: str | None = None
    # Instancia temporal (viajes en el tiempo: A@40 vs A@45)
    temporal_instance_id: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.event_id,  # Usar event_id como id para compatibilidad con frontend
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "description": self.description,
            "story_date": self.story_date,
            "story_date_resolution": self.story_date_resolution,
            "narrative_order": self.narrative_order,
            "discourse_position": self.discourse_position,
            "confidence": self.confidence,
            "day_offset": self.day_offset,
            "weekday": self.weekday,
            "temporal_instance_id": self.temporal_instance_id,
            "entity_ids": [],  # Placeholder - entities tracked separately
        }

    @classmethod
    def from_row(cls, row) -> "TimelineEventData":
        """Crea desde una fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            event_id=row["event_id"],
            chapter=row["chapter"],
            paragraph=row["paragraph"],
            description=row["description"],
            story_date=row["story_date"],
            story_date_resolution=row["story_date_resolution"] or "UNKNOWN",
            narrative_order=row["narrative_order"] or "CHRONOLOGICAL",
            discourse_position=row["discourse_position"],
            confidence=row["confidence"] or 0.5,
            day_offset=row.get("day_offset"),
            weekday=row.get("weekday"),
            temporal_instance_id=row.get("temporal_instance_id"),
            created_at=row["created_at"],
        )


@dataclass
class TemporalMarkerData:
    """Datos de un marcador temporal almacenado."""

    id: int | None
    project_id: int
    chapter: int
    marker_type: str
    text: str
    start_char: int
    end_char: int
    confidence: float = 0.5
    # Componentes para fechas absolutas
    year: int | None = None
    month: int | None = None
    day: int | None = None
    # Para marcadores relativos
    direction: str | None = None
    quantity: int | None = None
    magnitude: str | None = None
    # Para edades
    age: int | None = None
    entity_id: int | None = None
    created_at: str | None = None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        result = {
            "id": self.id,
            "chapter": self.chapter,
            "type": self.marker_type,
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
        }
        if self.year is not None:
            result["year"] = self.year
        if self.month is not None:
            result["month"] = self.month
        if self.day is not None:
            result["day"] = self.day
        if self.direction:
            result["direction"] = self.direction
        if self.quantity is not None:
            result["quantity"] = self.quantity
        if self.magnitude:
            result["magnitude"] = self.magnitude
        if self.age is not None:
            result["age"] = self.age
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        return result

    @classmethod
    def from_row(cls, row) -> "TemporalMarkerData":
        """Crea desde una fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter=row["chapter"],
            marker_type=row["marker_type"],
            text=row["text"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            confidence=row["confidence"] or 0.5,
            year=row["year"],
            month=row["month"],
            day=row["day"],
            direction=row["direction"],
            quantity=row["quantity"],
            magnitude=row["magnitude"],
            age=row["age"],
            entity_id=row["entity_id"],
            created_at=row["created_at"],
        )


class TimelineRepository:
    """
    Repositorio para gestionar timeline y marcadores temporales.

    Permite crear, leer y eliminar eventos del timeline y marcadores.
    """

    def __init__(self, db: Database | None = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si es None, usa singleton.
        """
        self.db = db or get_database()

    # =========================================================================
    # Timeline Events
    # =========================================================================

    def save_events(self, project_id: int, events: list[TimelineEventData]) -> int:
        """
        Guarda eventos del timeline, reemplazando los existentes.

        Args:
            project_id: ID del proyecto
            events: Lista de eventos a guardar

        Returns:
            Número de eventos guardados
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            # Eliminar eventos anteriores
            conn.execute("DELETE FROM timeline_events WHERE project_id = ?", (project_id,))

            # Insertar nuevos eventos
            for event in events:
                conn.execute(
                    """
                    INSERT INTO timeline_events (
                        project_id, event_id, chapter, paragraph, description,
                        story_date, story_date_resolution, narrative_order,
                        discourse_position, confidence, day_offset, weekday,
                        temporal_instance_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        event.event_id,
                        event.chapter,
                        event.paragraph,
                        event.description,
                        event.story_date,
                        event.story_date_resolution,
                        event.narrative_order,
                        event.discourse_position,
                        event.confidence,
                        event.day_offset,
                        event.weekday,
                        event.temporal_instance_id,
                        now,
                    ),
                )
            conn.commit()

        logger.info(f"Guardados {len(events)} eventos de timeline para proyecto {project_id}")
        return len(events)

    def get_events(
        self, project_id: int, *, max_events: int = 0
    ) -> list[TimelineEventData]:
        """
        Obtiene los eventos del timeline de un proyecto.

        Args:
            project_id: ID del proyecto
            max_events: Límite máximo de eventos (0 = sin límite)

        Returns:
            Lista de eventos ordenados por discourse_position
        """
        query = """
            SELECT * FROM timeline_events
            WHERE project_id = ?
            ORDER BY discourse_position, chapter, id
        """
        params: list = [project_id]
        if max_events > 0:
            query += " LIMIT ?"
            params.append(max_events)

        with self.db.connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [TimelineEventData.from_row(row) for row in rows]

    def count_events(self, project_id: int) -> int:
        """Cuenta el total de eventos del timeline de un proyecto."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM timeline_events WHERE project_id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    def has_timeline(self, project_id: int) -> bool:
        """
        Verifica si un proyecto tiene timeline guardado.

        Args:
            project_id: ID del proyecto

        Returns:
            True si hay eventos guardados
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM timeline_events WHERE project_id = ?", (project_id,)
            )
            row = cursor.fetchone()

        return int(row[0]) > 0 if row else False

    def delete_events(self, project_id: int) -> int:
        """
        Elimina todos los eventos de timeline de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de eventos eliminados
        """
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM timeline_events WHERE project_id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount

    # =========================================================================
    # Temporal Markers
    # =========================================================================

    def save_markers(self, project_id: int, markers: list[TemporalMarkerData]) -> int:
        """
        Guarda marcadores temporales, reemplazando los existentes.

        Args:
            project_id: ID del proyecto
            markers: Lista de marcadores a guardar

        Returns:
            Número de marcadores guardados
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            # Eliminar marcadores anteriores
            conn.execute("DELETE FROM temporal_markers WHERE project_id = ?", (project_id,))

            # Insertar nuevos marcadores
            for marker in markers:
                conn.execute(
                    """
                    INSERT INTO temporal_markers (
                        project_id, chapter, marker_type, text, start_char, end_char,
                        confidence, year, month, day, direction, quantity, magnitude,
                        age, entity_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        marker.chapter,
                        marker.marker_type,
                        marker.text,
                        marker.start_char,
                        marker.end_char,
                        marker.confidence,
                        marker.year,
                        marker.month,
                        marker.day,
                        marker.direction,
                        marker.quantity,
                        marker.magnitude,
                        marker.age,
                        marker.entity_id,
                        now,
                    ),
                )
            conn.commit()

        logger.info(f"Guardados {len(markers)} marcadores temporales para proyecto {project_id}")
        return len(markers)

    def get_markers(self, project_id: int, chapter: int | None = None) -> list[TemporalMarkerData]:
        """
        Obtiene marcadores temporales de un proyecto.

        Args:
            project_id: ID del proyecto
            chapter: Filtrar por capítulo (opcional)

        Returns:
            Lista de marcadores ordenados por posición
        """
        with self.db.connection() as conn:
            if chapter is not None:
                cursor = conn.execute(
                    """
                    SELECT * FROM temporal_markers
                    WHERE project_id = ? AND chapter = ?
                    ORDER BY start_char
                    """,
                    (project_id, chapter),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM temporal_markers
                    WHERE project_id = ?
                    ORDER BY chapter, start_char
                    """,
                    (project_id,),
                )
            rows = cursor.fetchall()

        return [TemporalMarkerData.from_row(row) for row in rows]

    def get_markers_count(self, project_id: int) -> int:
        """
        Cuenta los marcadores temporales de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de marcadores
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM temporal_markers WHERE project_id = ?", (project_id,)
            )
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    def delete_markers(self, project_id: int) -> int:
        """
        Elimina todos los marcadores de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de marcadores eliminados
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM temporal_markers WHERE project_id = ?", (project_id,)
            )
            conn.commit()
            return cursor.rowcount

    # =========================================================================
    # Utility
    # =========================================================================

    def delete_all(self, project_id: int) -> dict:
        """
        Elimina todo el timeline de un proyecto (eventos y marcadores).

        Args:
            project_id: ID del proyecto

        Returns:
            Diccionario con conteos de elementos eliminados
        """
        events_deleted = self.delete_events(project_id)
        markers_deleted = self.delete_markers(project_id)

        return {
            "events": events_deleted,
            "markers": markers_deleted,
        }
