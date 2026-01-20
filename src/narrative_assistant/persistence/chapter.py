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


@dataclass
class SectionData:
    """Datos de una sección (H2, H3, H4) dentro de un capítulo."""

    id: Optional[int]
    project_id: int
    chapter_id: int
    parent_section_id: Optional[int]  # None si es sección de nivel superior
    section_number: int
    title: Optional[str]
    heading_level: int  # 2=H2, 3=H3, 4=H4
    start_char: int
    end_char: int
    created_at: Optional[str] = None
    # Campo calculado para hijos (no persistido)
    subsections: list["SectionData"] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "parent_section_id": self.parent_section_id,
            "section_number": self.section_number,
            "title": self.title or f"Sección {self.section_number}",
            "heading_level": self.heading_level,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "created_at": self.created_at,
            "subsections": [s.to_dict() for s in self.subsections],
        }

    @classmethod
    def from_row(cls, row) -> "SectionData":
        """Crea desde una fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            parent_section_id=row["parent_section_id"],
            section_number=row["section_number"],
            title=row["title"],
            heading_level=row["heading_level"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            created_at=row["created_at"],
        )


class SectionRepository:
    """
    Repositorio para gestionar secciones en la base de datos.

    Las secciones son subdivisiones dentro de capítulos (H2, H3, H4).
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si es None, usa singleton.
        """
        self.db = db or get_database()

    def create(self, section: SectionData) -> SectionData:
        """
        Crea una nueva sección.

        Args:
            section: Datos de la sección a crear

        Returns:
            Sección creada con ID asignado
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sections (
                    project_id, chapter_id, parent_section_id, section_number,
                    title, heading_level, start_char, end_char, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    section.project_id,
                    section.chapter_id,
                    section.parent_section_id,
                    section.section_number,
                    section.title,
                    section.heading_level,
                    section.start_char,
                    section.end_char,
                    now,
                ),
            )
            section.id = cursor.lastrowid
            section.created_at = now

        logger.debug(f"Creada sección {section.section_number} para capítulo {section.chapter_id}")
        return section

    def create_many(self, sections: list[SectionData]) -> list[SectionData]:
        """
        Crea múltiples secciones en una transacción.

        Args:
            sections: Lista de secciones a crear

        Returns:
            Lista de secciones creadas con IDs asignados
        """
        if not sections:
            return []

        now = datetime.now().isoformat()
        created = []

        with self.db.transaction() as conn:
            for section in sections:
                cursor = conn.execute(
                    """
                    INSERT INTO sections (
                        project_id, chapter_id, parent_section_id, section_number,
                        title, heading_level, start_char, end_char, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        section.project_id,
                        section.chapter_id,
                        section.parent_section_id,
                        section.section_number,
                        section.title,
                        section.heading_level,
                        section.start_char,
                        section.end_char,
                        now,
                    ),
                )
                section.id = cursor.lastrowid
                section.created_at = now
                created.append(section)

        logger.info(f"Creadas {len(created)} secciones")
        return created

    def get_by_chapter(self, chapter_id: int) -> list[SectionData]:
        """
        Obtiene todas las secciones de un capítulo ordenadas por posición.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Lista de secciones ordenadas (flat, sin jerarquía)
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM sections
            WHERE chapter_id = ?
            ORDER BY start_char ASC
            """,
            (chapter_id,)
        )
        return [SectionData.from_row(row) for row in rows]

    def get_by_chapter_hierarchical(self, chapter_id: int) -> list[SectionData]:
        """
        Obtiene secciones de un capítulo organizadas jerárquicamente.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Lista de secciones de nivel superior con subsections pobladas
        """
        all_sections = self.get_by_chapter(chapter_id)

        # Crear mapa id -> sección
        section_map = {s.id: s for s in all_sections}

        # Organizar en árbol
        top_level = []
        for section in all_sections:
            if section.parent_section_id is None:
                top_level.append(section)
            else:
                parent = section_map.get(section.parent_section_id)
                if parent:
                    parent.subsections.append(section)

        return top_level

    def get_by_project(self, project_id: int) -> list[SectionData]:
        """
        Obtiene todas las secciones de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de todas las secciones ordenadas por capítulo y posición
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM sections
            WHERE project_id = ?
            ORDER BY chapter_id ASC, start_char ASC
            """,
            (project_id,)
        )
        return [SectionData.from_row(row) for row in rows]

    def delete_by_project(self, project_id: int) -> int:
        """
        Elimina todas las secciones de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de secciones eliminadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sections WHERE project_id = ?",
                (project_id,)
            )
            count = cursor.rowcount

        logger.info(f"Eliminadas {count} secciones del proyecto {project_id}")
        return count

    def delete_by_chapter(self, chapter_id: int) -> int:
        """
        Elimina todas las secciones de un capítulo.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Número de secciones eliminadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sections WHERE chapter_id = ?",
                (chapter_id,)
            )
            count = cursor.rowcount

        logger.debug(f"Eliminadas {count} secciones del capítulo {chapter_id}")
        return count


def get_section_repository(db: Optional[Database] = None) -> SectionRepository:
    """Obtiene una instancia del repositorio de secciones."""
    return SectionRepository(db)
