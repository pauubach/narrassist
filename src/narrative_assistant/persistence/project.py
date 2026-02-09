"""
Gestión de proyectos (un proyecto = un manuscrito analizado).
"""

import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.errors import DocumentAlreadyExistsError, ProjectNotFoundError
from ..core.result import Result
from .database import Database, get_database
from .document_fingerprint import FingerprintMatcher, generate_fingerprint

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """
    Representa un proyecto de análisis de manuscrito.

    Attributes:
        id: ID en base de datos
        name: Nombre del proyecto
        document_path: Ruta al documento original
        document_fingerprint: Hash único del documento
        document_format: Formato (docx, pdf, etc.)
        word_count: Conteo de palabras
        chapter_count: Capítulos detectados
        analysis_status: Estado del análisis
        analysis_progress: Progreso 0.0 - 1.0
        settings: Configuración específica del proyecto
    """

    id: int | None = None
    name: str = ""
    description: str = ""
    document_path: str | None = None
    document_fingerprint: str = ""
    document_format: str = ""
    word_count: int = 0
    chapter_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_opened_at: datetime | None = None
    analysis_status: str = "pending"  # pending, queued, analyzing, completed, error
    analysis_progress: float = 0.0
    settings: dict[str, Any] = field(default_factory=dict)
    document_type: str = "FIC"  # Tipo de documento (FIC, MEM, etc.)
    document_subtype: str | None = None  # Subtipo específico
    document_type_confirmed: bool = False  # Si el usuario confirmó el tipo
    detected_document_type: str | None = None  # Tipo detectado automáticamente

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "document_path": self.document_path,
            "document_fingerprint": self.document_fingerprint,
            "document_format": self.document_format,
            "word_count": self.word_count,
            "chapter_count": self.chapter_count,
            "analysis_status": self.analysis_status,
            "analysis_progress": self.analysis_progress,
            "settings": self.settings,
            "document_type": self.document_type,
            "document_subtype": self.document_subtype,
            "document_type_confirmed": self.document_type_confirmed,
            "detected_document_type": self.detected_document_type,
        }

    @classmethod
    def from_row(cls, row) -> "Project":
        """Crea desde fila de SQLite."""
        settings = {}
        if row["settings_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                settings = json.loads(row["settings_json"])

        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            document_path=row["document_path"],
            document_fingerprint=row["document_fingerprint"],
            document_format=row["document_format"],
            word_count=row["word_count"] or 0,
            chapter_count=row["chapter_count"] or 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            last_opened_at=datetime.fromisoformat(row["last_opened_at"])
            if row["last_opened_at"]
            else None,
            analysis_status=row["analysis_status"] or "pending",
            analysis_progress=row["analysis_progress"] or 0.0,
            settings=settings,
            document_type=row["document_type"] or "FIC",
            document_subtype=row["document_subtype"],
            document_type_confirmed=bool(row["document_type_confirmed"])
            if row["document_type_confirmed"]
            else False,
            detected_document_type=row["detected_document_type"],
        )


class ProjectManager:
    """
    Gestiona proyectos en la base de datos.

    Uso:
        manager = ProjectManager()
        project = manager.create_from_document(text, "Mi Novela", "docx")
    """

    def __init__(self, db: Database | None = None):
        self.db = db or get_database()
        self.matcher = FingerprintMatcher()

    def create_from_document(
        self,
        text: str,
        name: str,
        document_format: str,
        document_path: Path | None = None,
        description: str = "",
        check_existing: bool = True,
    ) -> Result[Project]:
        """
        Crea un proyecto desde el contenido de un documento.

        Args:
            text: Contenido del documento
            name: Nombre del proyecto
            document_format: Formato (docx, pdf, etc.)
            document_path: Ruta al archivo original
            description: Descripción opcional
            check_existing: Si True, verifica si el documento ya existe

        Returns:
            Result con el proyecto creado o error si ya existe
        """
        # Generar fingerprint
        fingerprint = generate_fingerprint(text)

        # Inicializar match para evitar referencia no definida
        match = None

        # Verificar si ya existe
        if check_existing:
            match = self.matcher.find_match(fingerprint, self.db)

            if match.is_exact_match:
                return Result.failure(
                    DocumentAlreadyExistsError(
                        document_fingerprint=fingerprint.full_hash,
                        existing_project_name=match.existing_project_name or "Desconocido",
                    )
                )

            # Si hay documento similar, continuamos con la creación y añadimos warning al final

        # Crear proyecto
        project = Project(
            name=name,
            description=description,
            document_path=str(document_path) if document_path else None,
            document_fingerprint=fingerprint.full_hash,
            document_format=document_format,
            word_count=fingerprint.word_count,
        )

        # Insertar en BD
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, description, document_path, document_fingerprint,
                    document_format, word_count, settings_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.name,
                    project.description,
                    project.document_path,
                    project.document_fingerprint,
                    project.document_format,
                    project.word_count,
                    json.dumps(project.settings) if project.settings else None,
                ),
            )
            project.id = cursor.lastrowid
            project.created_at = datetime.now()
            project.updated_at = datetime.now()

        logger.info(f"Proyecto creado: {project.name} (ID: {project.id})")

        # Si había warnings de documento similar, devolverlos
        if match is not None and match.is_similar:
            result = Result.success(project)
            result.add_warning(
                f"Documento similar encontrado: '{match.existing_project_name}' "
                f"(similitud: {match.similarity_score:.0%})"
            )
            return result

        return Result.success(project)

    def get(self, project_id: int) -> Result[Project]:
        """
        Obtiene un proyecto por ID.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con el proyecto o error si no existe
        """
        row = self.db.fetchone(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        )

        if not row:
            return Result.failure(ProjectNotFoundError(project_id=project_id))

        project = Project.from_row(row)

        # Actualizar last_opened_at
        self.db.execute(
            "UPDATE projects SET last_opened_at = datetime('now') WHERE id = ?",
            (project_id,),
        )

        return Result.success(project)

    def get_by_fingerprint(self, fingerprint: str) -> Project | None:
        """Busca proyecto por fingerprint exacto."""
        row = self.db.fetchone(
            "SELECT * FROM projects WHERE document_fingerprint = ?",
            (fingerprint,),
        )
        return Project.from_row(row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """Lista todos los proyectos ordenados por fecha de apertura."""
        rows = self.db.fetchall(
            """
            SELECT * FROM projects
            ORDER BY last_opened_at DESC NULLS LAST, created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [Project.from_row(row) for row in rows]

    def update(self, project: Project) -> Result[Project]:
        """Actualiza un proyecto existente."""
        if not project.id:
            return Result.failure(ProjectNotFoundError(project_id=0))

        self.db.execute(
            """
            UPDATE projects SET
                name = ?,
                description = ?,
                document_path = ?,
                analysis_status = ?,
                analysis_progress = ?,
                chapter_count = ?,
                word_count = ?,
                settings_json = ?,
                document_type = ?,
                document_subtype = ?,
                document_type_confirmed = ?,
                detected_document_type = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                project.name,
                project.description,
                project.document_path,
                project.analysis_status,
                project.analysis_progress,
                project.chapter_count,
                project.word_count,
                json.dumps(project.settings) if project.settings else None,
                project.document_type,
                project.document_subtype,
                1 if project.document_type_confirmed else 0,
                project.detected_document_type,
                project.id,
            ),
        )

        project.updated_at = datetime.now()
        return Result.success(project)

    def delete(self, project_id: int) -> Result[bool]:
        """
        Elimina un proyecto y todos sus datos relacionados.

        Las foreign keys con ON DELETE CASCADE eliminan:
        - chapters
        - entities
        - entity_mentions
        - entity_attributes
        - alerts
        - review_history
        - sessions
        """
        # Verificar que existe
        existing = self.get(project_id)
        if existing.is_failure:
            return Result.failure(existing.fatal_errors[0])

        self.db.execute("DELETE FROM projects WHERE id = ?", (project_id,))

        logger.info(f"Proyecto eliminado: ID {project_id}")
        return Result.success(True)

    def find_similar(self, text: str) -> Project | None:
        """
        Busca un proyecto con documento similar.

        Útil para preguntar "¿continuar donde lo dejaste?"
        """
        fingerprint = generate_fingerprint(text)
        match = self.matcher.find_match(fingerprint, self.db)

        if match.is_exact_match or match.is_similar:
            result = self.get(match.existing_project_id)
            return result.value if result.is_success else None

        return None
