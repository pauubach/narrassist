"""
Repositorio de capítulos.

Gestiona el almacenamiento y recuperación de capítulos detectados en documentos.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .database import Database, get_database

logger = logging.getLogger(__name__)


@dataclass
class ChapterData:
    """Datos de un capítulo almacenado."""

    id: Optional[int]
    project_id: int
    chapter_number: int
    title: Optional[str]
    content: str
    start_char: int
    end_char: int
    word_count: int
    structure_type: str = "chapter"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_number": self.chapter_number,
            "title": self.title or f"Capítulo {self.chapter_number}",
            "content": self.content,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "word_count": self.word_count,
            "structure_type": self.structure_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> "ChapterData":
        """Crea desde una fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_number=row["chapter_number"],
            title=row["title"],
            content=row["content"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            word_count=row["word_count"],
            structure_type=row["structure_type"] or "chapter",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ChapterRepository:
    """
    Repositorio para gestionar capítulos en la base de datos.

    Permite crear, leer, actualizar y eliminar capítulos de un proyecto.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si es None, usa singleton.
        """
        self.db = db or get_database()

    def create(self, chapter: ChapterData) -> ChapterData:
        """
        Crea un nuevo capítulo.

        Args:
            chapter: Datos del capítulo a crear

        Returns:
            Capítulo creado con ID asignado
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char, word_count, structure_type,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter.project_id,
                    chapter.chapter_number,
                    chapter.title,
                    chapter.content,
                    chapter.start_char,
                    chapter.end_char,
                    chapter.word_count,
                    chapter.structure_type,
                    now,
                    now,
                ),
            )
            chapter.id = cursor.lastrowid
            chapter.created_at = now
            chapter.updated_at = now

        logger.debug(f"Creado capítulo {chapter.chapter_number} para proyecto {chapter.project_id}")
        return chapter

    def create_many(self, chapters: list[ChapterData]) -> list[ChapterData]:
        """
        Crea múltiples capítulos en una transacción.

        Args:
            chapters: Lista de capítulos a crear

        Returns:
            Lista de capítulos creados con IDs asignados
        """
        if not chapters:
            return []

        now = datetime.now().isoformat()
        created = []

        with self.db.transaction() as conn:
            for chapter in chapters:
                cursor = conn.execute(
                    """
                    INSERT INTO chapters (
                        project_id, chapter_number, title, content,
                        start_char, end_char, word_count, structure_type,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chapter.project_id,
                        chapter.chapter_number,
                        chapter.title,
                        chapter.content,
                        chapter.start_char,
                        chapter.end_char,
                        chapter.word_count,
                        chapter.structure_type,
                        now,
                        now,
                    ),
                )
                chapter.id = cursor.lastrowid
                chapter.created_at = now
                chapter.updated_at = now
                created.append(chapter)

        logger.info(f"Creados {len(created)} capítulos para proyecto {chapters[0].project_id if chapters else 'N/A'}")
        return created

    def get_by_id(self, chapter_id: int) -> Optional[ChapterData]:
        """
        Obtiene un capítulo por su ID.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Capítulo encontrado o None
        """
        row = self.db.fetchone(
            "SELECT * FROM chapters WHERE id = ?",
            (chapter_id,)
        )
        return ChapterData.from_row(row) if row else None

    def get_by_project(self, project_id: int) -> list[ChapterData]:
        """
        Obtiene todos los capítulos de un proyecto ordenados por número.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de capítulos ordenados
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM chapters
            WHERE project_id = ?
            ORDER BY chapter_number ASC
            """,
            (project_id,)
        )
        return [ChapterData.from_row(row) for row in rows]

    def delete_by_project(self, project_id: int) -> int:
        """
        Elimina todos los capítulos de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de capítulos eliminados
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chapters WHERE project_id = ?",
                (project_id,)
            )
            count = cursor.rowcount

        logger.info(f"Eliminados {count} capítulos del proyecto {project_id}")
        return count

    def update_content(self, chapter_id: int, content: str, word_count: int) -> bool:
        """
        Actualiza el contenido de un capítulo.

        Args:
            chapter_id: ID del capítulo
            content: Nuevo contenido
            word_count: Nuevo conteo de palabras

        Returns:
            True si se actualizó, False si no existe
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE chapters
                SET content = ?, word_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (content, word_count, now, chapter_id)
            )
            return cursor.rowcount > 0


# Función de conveniencia para obtener instancia
def get_chapter_repository(db: Optional[Database] = None) -> ChapterRepository:
    """Obtiene una instancia del repositorio de capítulos."""
    return ChapterRepository(db)
