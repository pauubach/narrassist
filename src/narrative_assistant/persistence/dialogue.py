"""
Repositorio para gestionar diálogos detectados en el manuscrito.

Los diálogos se almacenan con su formato original (antes de normalización)
para permitir validación de estilo sin re-análisis completo.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from .database import Database, get_database

logger = logging.getLogger(__name__)


@dataclass
class DialogueData:
    """
    Representa un diálogo detectado en el manuscrito.

    Attributes:
        id: ID en base de datos (None si no se ha guardado)
        project_id: ID del proyecto
        chapter_id: ID del capítulo (nullable)
        start_char: Posición de inicio (global o del capítulo)
        end_char: Posición de fin
        text: Texto del diálogo
        dialogue_type: Tipo normalizado (dash, guillemets, quotes, quotes_typographic)
        original_format: Formato ANTES de normalización (em_dash, minus, guillemets, etc.)
        attribution_text: Texto de atribución ("dijo María")
        speaker_hint: Pista del hablante
        speaker_entity_id: ID de la entidad hablante (nullable)
        confidence: Confianza de la detección (0.0 - 1.0)
        created_at: Timestamp de creación
    """

    id: int | None
    project_id: int
    chapter_id: int | None
    start_char: int
    end_char: int
    text: str
    dialogue_type: str
    original_format: str | None = None
    attribution_text: str | None = None
    speaker_hint: str | None = None
    speaker_entity_id: int | None = None
    confidence: float = 0.9
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: dict) -> "DialogueData":
        """Crea instancia desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row.get("chapter_id"),
            start_char=row["start_char"],
            end_char=row["end_char"],
            text=row["text"],
            dialogue_type=row["dialogue_type"],
            original_format=row.get("original_format"),
            attribution_text=row.get("attribution_text"),
            speaker_hint=row.get("speaker_hint"),
            speaker_entity_id=row.get("speaker_entity_id"),
            confidence=row.get("confidence", 0.9),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
        )


class DialogueRepository:
    """
    Repositorio para gestionar diálogos en la base de datos.

    Operaciones:
    - create(), create_batch(): Crear diálogos
    - get_by_project(): Obtener todos los diálogos de un proyecto
    - get_by_type(): Filtrar por tipo de diálogo
    - get_by_type_not(): Obtener diálogos que NO son de un tipo (útil para validación)
    - count_by_type(): Contar diálogos por tipo
    - delete_by_project(): Eliminar todos los diálogos de un proyecto
    """

    def __init__(self, db: Database | None = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de base de datos. Si None, usa la global.
        """
        self.db = db or get_database()

    def create(self, dialogue: DialogueData) -> DialogueData:
        """
        Crea un diálogo en la base de datos.

        Args:
            dialogue: Datos del diálogo

        Returns:
            DialogueData con id asignado
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO dialogues (
                    project_id, chapter_id, start_char, end_char, text,
                    dialogue_type, original_format, attribution_text, speaker_hint,
                    speaker_entity_id, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dialogue.project_id,
                    dialogue.chapter_id,
                    dialogue.start_char,
                    dialogue.end_char,
                    dialogue.text,
                    dialogue.dialogue_type,
                    dialogue.original_format,
                    dialogue.attribution_text,
                    dialogue.speaker_hint,
                    dialogue.speaker_entity_id,
                    dialogue.confidence,
                ),
            )

            dialogue.id = cursor.lastrowid
            return dialogue

    def create_batch(self, dialogues: list[DialogueData]) -> list[DialogueData]:
        """
        Crea múltiples diálogos en batch.

        Args:
            dialogues: Lista de diálogos a crear

        Returns:
            Lista de diálogos con IDs asignados
        """
        if not dialogues:
            return []

        with self.db.connection() as conn:
            for dialogue in dialogues:
                cursor = conn.execute(
                    """
                    INSERT INTO dialogues (
                        project_id, chapter_id, start_char, end_char, text,
                        dialogue_type, original_format, attribution_text, speaker_hint,
                        speaker_entity_id, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dialogue.project_id,
                        dialogue.chapter_id,
                        dialogue.start_char,
                        dialogue.end_char,
                        dialogue.text,
                        dialogue.dialogue_type,
                        dialogue.original_format,
                        dialogue.attribution_text,
                        dialogue.speaker_hint,
                        dialogue.speaker_entity_id,
                        dialogue.confidence,
                    ),
                )
                dialogue.id = cursor.lastrowid

        return dialogues

    def get_by_project(self, project_id: int) -> list[DialogueData]:
        """
        Obtiene todos los diálogos de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de diálogos ordenados por chapter_id, start_char
        """
        with self.db.connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r, strict=False))
            rows = conn.execute(
                """
                SELECT * FROM dialogues
                WHERE project_id = ?
                ORDER BY chapter_id, start_char
                """,
                (project_id,),
            ).fetchall()

            return [DialogueData.from_row(row) for row in rows]

    def get_by_type(self, project_id: int, dialogue_type: str) -> list[DialogueData]:
        """
        Obtiene diálogos de un tipo específico.

        Args:
            project_id: ID del proyecto
            dialogue_type: Tipo de diálogo (dash, guillemets, quotes, quotes_typographic)

        Returns:
            Lista de diálogos del tipo especificado
        """
        with self.db.connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r, strict=False))
            rows = conn.execute(
                """
                SELECT * FROM dialogues
                WHERE project_id = ? AND dialogue_type = ?
                ORDER BY chapter_id, start_char
                """,
                (project_id, dialogue_type),
            ).fetchall()

            return [DialogueData.from_row(row) for row in rows]

    def get_by_type_not(self, project_id: int, dialogue_type: str) -> list[DialogueData]:
        """
        Obtiene diálogos que NO son de un tipo específico.

        Útil para validación de estilo: obtener todos los diálogos que NO cumplen
        la preferencia del usuario sin re-analizar.

        Args:
            project_id: ID del proyecto
            dialogue_type: Tipo a excluir

        Returns:
            Lista de diálogos que no son del tipo especificado
        """
        with self.db.connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r, strict=False))
            rows = conn.execute(
                """
                SELECT * FROM dialogues
                WHERE project_id = ? AND dialogue_type != ?
                ORDER BY chapter_id, start_char
                """,
                (project_id, dialogue_type),
            ).fetchall()

            return [DialogueData.from_row(row) for row in rows]

    def count_by_type(self, project_id: int, dialogue_type: str) -> int:
        """
        Cuenta diálogos de un tipo específico.

        Args:
            project_id: ID del proyecto
            dialogue_type: Tipo de diálogo

        Returns:
            Número de diálogos del tipo especificado
        """
        with self.db.connection() as conn:
            result = conn.execute(
                """
                SELECT COUNT(*) as count FROM dialogues
                WHERE project_id = ? AND dialogue_type = ?
                """,
                (project_id, dialogue_type),
            ).fetchone()

            return int(result["count"]) if result else 0

    def delete_by_project(self, project_id: int) -> int:
        """
        Elimina todos los diálogos de un proyecto.

        Útil para re-análisis: limpiar datos anteriores antes de guardar nuevos.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de diálogos eliminados
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM dialogues WHERE project_id = ?",
                (project_id,),
            )
            return cursor.rowcount


# Singleton thread-safe
_repository: DialogueRepository | None = None
_repository_lock = __import__("threading").Lock()


def get_dialogue_repository(db: Database | None = None) -> DialogueRepository:
    """
    Obtiene la instancia singleton del repositorio.

    Args:
        db: Base de datos (opcional, usa la global si no se especifica)

    Returns:
        Instancia singleton de DialogueRepository
    """
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = DialogueRepository(db)
    return _repository


def reset_dialogue_repository():
    """Resetea el singleton (solo para tests)."""
    global _repository
    _repository = None
