"""
Repositorio SQLite para escenas y etiquetas.
"""

import contextlib
import json
import logging
from datetime import datetime

from ..persistence.database import get_database
from .models import (
    CustomTagCatalog,
    Scene,
    SceneCustomTag,
    SceneTag,
    SceneTone,
    SceneType,
)

logger = logging.getLogger(__name__)


class SceneRepository:
    """
    Repositorio para operaciones CRUD de escenas y etiquetas.
    """

    def __init__(self, db=None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database (opcional, usa singleton si no se provee)
        """
        self._db = db

    @property
    def db(self):
        """Obtiene la instancia de base de datos."""
        if self._db is None:
            self._db = get_database()
        return self._db

    # =========================================================================
    # Scenes CRUD
    # =========================================================================

    def save_scene(self, scene: Scene) -> int:
        """
        Guarda o actualiza una escena.

        Returns:
            ID de la escena guardada
        """
        with self.db.transaction() as conn:
            if scene.id:
                # Update
                conn.execute(
                    """
                    UPDATE scenes SET
                        scene_number = ?,
                        start_char = ?,
                        end_char = ?,
                        separator_type = ?,
                        word_count = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (
                        scene.scene_number,
                        scene.start_char,
                        scene.end_char,
                        scene.separator_type,
                        scene.word_count,
                        scene.id,
                    ),
                )
                return scene.id
            else:
                # Insert
                cursor = conn.execute(
                    """
                    INSERT INTO scenes (
                        project_id, chapter_id, scene_number,
                        start_char, end_char, separator_type, word_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scene.project_id,
                        scene.chapter_id,
                        scene.scene_number,
                        scene.start_char,
                        scene.end_char,
                        scene.separator_type,
                        scene.word_count,
                    ),
                )
                return cursor.lastrowid

    def save_scenes_batch(self, scenes: list[Scene]) -> list[int]:
        """
        Guarda múltiples escenas en una transacción.

        Returns:
            Lista de IDs de escenas guardadas
        """
        ids = []
        with self.db.transaction() as conn:
            for scene in scenes:
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO scenes (
                        project_id, chapter_id, scene_number,
                        start_char, end_char, separator_type, word_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scene.project_id,
                        scene.chapter_id,
                        scene.scene_number,
                        scene.start_char,
                        scene.end_char,
                        scene.separator_type,
                        scene.word_count,
                    ),
                )
                ids.append(cursor.lastrowid)
        return ids

    def get_scene(self, scene_id: int) -> Scene | None:
        """Obtiene una escena por ID."""
        row = self.db.fetchone(
            "SELECT * FROM scenes WHERE id = ?",
            (scene_id,),
        )
        return self._row_to_scene(row) if row else None

    def get_scenes_by_project(self, project_id: int) -> list[Scene]:
        """Obtiene todas las escenas de un proyecto."""
        rows = self.db.fetchall(
            """
            SELECT * FROM scenes
            WHERE project_id = ?
            ORDER BY chapter_id, scene_number
            """,
            (project_id,),
        )
        return [self._row_to_scene(row) for row in rows]

    def get_scenes_by_chapter(self, chapter_id: int) -> list[Scene]:
        """Obtiene todas las escenas de un capítulo."""
        rows = self.db.fetchall(
            """
            SELECT * FROM scenes
            WHERE chapter_id = ?
            ORDER BY scene_number
            """,
            (chapter_id,),
        )
        return [self._row_to_scene(row) for row in rows]

    def count_scenes(self, project_id: int) -> int:
        """Cuenta el número total de escenas en un proyecto."""
        row = self.db.fetchone(
            "SELECT COUNT(*) as count FROM scenes WHERE project_id = ?",
            (project_id,),
        )
        return row["count"] if row else 0

    def delete_scenes_by_project(self, project_id: int) -> int:
        """
        Elimina todas las escenas de un proyecto.

        Returns:
            Número de escenas eliminadas
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM scenes WHERE project_id = ?",
                (project_id,),
            )
            return cursor.rowcount

    def delete_scenes_by_chapter(self, chapter_id: int) -> int:
        """Elimina todas las escenas de un capítulo."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM scenes WHERE chapter_id = ?",
                (chapter_id,),
            )
            return cursor.rowcount

    # =========================================================================
    # Scene Tags CRUD
    # =========================================================================

    def save_scene_tags(self, scene_id: int, tags: SceneTag) -> int:
        """
        Guarda o actualiza las etiquetas predefinidas de una escena.

        Returns:
            ID del registro de tags
        """
        participant_ids_json = json.dumps(tags.participant_ids or [])

        with self.db.transaction() as conn:
            # Upsert
            cursor = conn.execute(
                """
                INSERT INTO scene_tags (
                    scene_id, scene_type, tone, location_entity_id,
                    participant_ids, summary, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (scene_id) DO UPDATE SET
                    scene_type = excluded.scene_type,
                    tone = excluded.tone,
                    location_entity_id = excluded.location_entity_id,
                    participant_ids = excluded.participant_ids,
                    summary = excluded.summary,
                    notes = excluded.notes,
                    updated_at = datetime('now')
                """,
                (
                    scene_id,
                    tags.scene_type.value if tags.scene_type else None,
                    tags.tone.value if tags.tone else None,
                    tags.location_entity_id,
                    participant_ids_json,
                    tags.summary,
                    tags.notes,
                ),
            )
            return cursor.lastrowid

    def get_scene_tags(self, scene_id: int) -> SceneTag | None:
        """Obtiene las etiquetas predefinidas de una escena."""
        row = self.db.fetchone(
            "SELECT * FROM scene_tags WHERE scene_id = ?",
            (scene_id,),
        )
        return self._row_to_scene_tag(row) if row else None

    def delete_scene_tags(self, scene_id: int) -> bool:
        """Elimina las etiquetas predefinidas de una escena."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM scene_tags WHERE scene_id = ?",
                (scene_id,),
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Custom Tags CRUD
    # =========================================================================

    def add_custom_tag(self, scene_id: int, tag_name: str, tag_color: str | None = None) -> int:
        """
        Añade una etiqueta personalizada a una escena.

        Returns:
            ID de la etiqueta
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scene_custom_tags (scene_id, tag_name, tag_color)
                VALUES (?, ?, ?)
                """,
                (scene_id, tag_name, tag_color),
            )
            return cursor.lastrowid

    def remove_custom_tag(self, scene_id: int, tag_name: str) -> bool:
        """Elimina una etiqueta personalizada de una escena."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM scene_custom_tags WHERE scene_id = ? AND tag_name = ?",
                (scene_id, tag_name),
            )
            return cursor.rowcount > 0

    def get_custom_tags(self, scene_id: int) -> list[SceneCustomTag]:
        """Obtiene las etiquetas personalizadas de una escena."""
        rows = self.db.fetchall(
            "SELECT * FROM scene_custom_tags WHERE scene_id = ? ORDER BY tag_name",
            (scene_id,),
        )
        return [self._row_to_custom_tag(row) for row in rows]

    def get_all_custom_tags_in_project(self, project_id: int) -> list[str]:
        """Obtiene todas las etiquetas personalizadas usadas en un proyecto."""
        rows = self.db.fetchall(
            """
            SELECT DISTINCT sct.tag_name
            FROM scene_custom_tags sct
            JOIN scenes s ON s.id = sct.scene_id
            WHERE s.project_id = ?
            ORDER BY sct.tag_name
            """,
            (project_id,),
        )
        return [row["tag_name"] for row in rows]

    # =========================================================================
    # Tag Catalog
    # =========================================================================

    def add_to_catalog(self, project_id: int, tag_name: str, tag_color: str | None = None) -> int:
        """Añade una etiqueta al catálogo del proyecto."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO project_custom_tag_catalog (project_id, tag_name, tag_color)
                VALUES (?, ?, ?)
                ON CONFLICT (project_id, tag_name) DO UPDATE SET
                    usage_count = usage_count + 1
                """,
                (project_id, tag_name, tag_color),
            )
            return cursor.lastrowid

    def get_catalog(self, project_id: int) -> list[CustomTagCatalog]:
        """Obtiene el catálogo de etiquetas del proyecto."""
        rows = self.db.fetchall(
            """
            SELECT * FROM project_custom_tag_catalog
            WHERE project_id = ?
            ORDER BY usage_count DESC, tag_name
            """,
            (project_id,),
        )
        return [self._row_to_catalog(row) for row in rows]

    # =========================================================================
    # Query helpers
    # =========================================================================

    def get_scenes_by_type(self, project_id: int, scene_type: SceneType) -> list[Scene]:
        """Obtiene escenas filtradas por tipo."""
        rows = self.db.fetchall(
            """
            SELECT s.* FROM scenes s
            JOIN scene_tags st ON st.scene_id = s.id
            WHERE s.project_id = ? AND st.scene_type = ?
            ORDER BY s.chapter_id, s.scene_number
            """,
            (project_id, scene_type.value),
        )
        return [self._row_to_scene(row) for row in rows]

    def get_scenes_by_tone(self, project_id: int, tone: SceneTone) -> list[Scene]:
        """Obtiene escenas filtradas por tono."""
        rows = self.db.fetchall(
            """
            SELECT s.* FROM scenes s
            JOIN scene_tags st ON st.scene_id = s.id
            WHERE s.project_id = ? AND st.tone = ?
            ORDER BY s.chapter_id, s.scene_number
            """,
            (project_id, tone.value),
        )
        return [self._row_to_scene(row) for row in rows]

    def get_scenes_by_custom_tag(self, project_id: int, tag_name: str) -> list[Scene]:
        """Obtiene escenas que tienen una etiqueta personalizada específica."""
        rows = self.db.fetchall(
            """
            SELECT s.* FROM scenes s
            JOIN scene_custom_tags sct ON sct.scene_id = s.id
            WHERE s.project_id = ? AND sct.tag_name = ?
            ORDER BY s.chapter_id, s.scene_number
            """,
            (project_id, tag_name),
        )
        return [self._row_to_scene(row) for row in rows]

    def get_scenes_by_location(self, project_id: int, location_entity_id: int) -> list[Scene]:
        """Obtiene escenas que ocurren en una ubicación específica."""
        rows = self.db.fetchall(
            """
            SELECT s.* FROM scenes s
            JOIN scene_tags st ON st.scene_id = s.id
            WHERE s.project_id = ? AND st.location_entity_id = ?
            ORDER BY s.chapter_id, s.scene_number
            """,
            (project_id, location_entity_id),
        )
        return [self._row_to_scene(row) for row in rows]

    def get_scenes_with_participant(self, project_id: int, entity_id: int) -> list[Scene]:
        """Obtiene escenas donde participa un personaje específico."""
        try:
            rows = self.db.fetchall(
                """
                SELECT DISTINCT s.* FROM scenes s
                JOIN scene_tags st ON st.scene_id = s.id
                JOIN json_each(st.participant_ids) p
                WHERE s.project_id = ?
                  AND CAST(p.value AS INTEGER) = ?
                ORDER BY s.chapter_id, s.scene_number
                """,
                (project_id, entity_id),
            )
            return [self._row_to_scene(row) for row in rows]
        except Exception:
            # Fallback para entornos SQLite sin JSON1.
            logger.debug("json_each no disponible; usando fallback LIKE para participant_ids")
            rows = self.db.fetchall(
                """
                SELECT s.* FROM scenes s
                JOIN scene_tags st ON st.scene_id = s.id
                WHERE s.project_id = ?
                  AND st.participant_ids LIKE ?
                ORDER BY s.chapter_id, s.scene_number
                """,
                (project_id, f"%{entity_id}%"),
            )
            # Filtrado preciso en Python para evitar falsos positivos del LIKE.
            result = []
            for row in rows:
                scene = self._row_to_scene(row)
                tags = self.get_scene_tags(scene.id)
                if tags and entity_id in tags.participant_ids:
                    result.append(scene)
            return result

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _row_to_scene(self, row) -> Scene:
        """Convierte una fila de BD a objeto Scene."""
        return Scene(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            scene_number=row["scene_number"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            separator_type=row["separator_type"],
            word_count=row["word_count"] or 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    def _row_to_scene_tag(self, row) -> SceneTag:
        """Convierte una fila de BD a objeto SceneTag."""
        participant_ids = []
        if row["participant_ids"]:
            with contextlib.suppress(json.JSONDecodeError):
                participant_ids = json.loads(row["participant_ids"])

        return SceneTag(
            id=row["id"],
            scene_id=row["scene_id"],
            scene_type=SceneType(row["scene_type"]) if row["scene_type"] else None,
            tone=SceneTone(row["tone"]) if row["tone"] else None,
            location_entity_id=row["location_entity_id"],
            participant_ids=participant_ids,
            summary=row["summary"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    def _row_to_custom_tag(self, row) -> SceneCustomTag:
        """Convierte una fila de BD a objeto SceneCustomTag."""
        return SceneCustomTag(
            id=row["id"],
            scene_id=row["scene_id"],
            tag_name=row["tag_name"],
            tag_color=row["tag_color"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    def _row_to_catalog(self, row) -> CustomTagCatalog:
        """Convierte una fila de BD a objeto CustomTagCatalog."""
        return CustomTagCatalog(
            id=row["id"],
            project_id=row["project_id"],
            tag_name=row["tag_name"],
            tag_color=row["tag_color"],
            usage_count=row["usage_count"] or 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
