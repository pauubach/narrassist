"""
Servicio de gestión de escenas y etiquetado.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from ..persistence.database import get_database
from ..parsers.structure_detector import Scene as ParsedScene, Chapter
from .models import (
    Scene,
    SceneTag,
    SceneCustomTag,
    SceneType,
    SceneTone,
    SceneWithTags,
)
from .repository import SceneRepository

logger = logging.getLogger(__name__)


@dataclass
class SceneStats:
    """Estadísticas de escenas de un proyecto."""
    total_scenes: int
    chapters_with_scenes: int
    tagged_scenes: int
    untagged_scenes: int
    scenes_by_type: dict[str, int]
    scenes_by_tone: dict[str, int]
    custom_tags_used: list[str]
    has_scenes: bool  # Si el proyecto tiene estructura de escenas


class SceneService:
    """
    Servicio para gestionar escenas y sus etiquetas.

    Proporciona:
    - Persistencia de escenas detectadas durante el parsing
    - Asignación de etiquetas predefinidas (tipo, tono)
    - Asignación de etiquetas personalizadas
    - Consultas y filtrado
    - Estadísticas para determinar si mostrar UI de escenas
    """

    def __init__(self, db=None):
        """
        Inicializa el servicio.

        Args:
            db: Instancia de Database (opcional)
        """
        self._db = db
        self._repo = SceneRepository(db)

    @property
    def db(self):
        """Obtiene la instancia de base de datos."""
        if self._db is None:
            self._db = get_database()
        return self._db

    # =========================================================================
    # Persistencia de escenas detectadas
    # =========================================================================

    def persist_scenes_from_chapters(
        self,
        project_id: int,
        chapters: list[Chapter],
    ) -> int:
        """
        Persiste las escenas detectadas durante el parsing.

        Reemplaza escenas existentes del proyecto.

        Args:
            project_id: ID del proyecto
            chapters: Lista de Chapter con escenas detectadas

        Returns:
            Número de escenas guardadas
        """
        # Primero eliminar escenas existentes
        self._repo.delete_scenes_by_project(project_id)

        # Obtener chapter_ids de la BD
        chapter_ids = self._get_chapter_ids(project_id)

        scenes_to_save = []
        for chapter in chapters:
            chapter_id = chapter_ids.get(chapter.number)
            if not chapter_id:
                logger.warning(f"No chapter_id found for chapter {chapter.number}")
                continue

            for parsed_scene in chapter.scenes:
                scene = Scene(
                    id=0,  # Will be assigned by DB
                    project_id=project_id,
                    chapter_id=chapter_id,
                    scene_number=parsed_scene.number,
                    start_char=parsed_scene.start_char,
                    end_char=parsed_scene.end_char,
                    separator_type=parsed_scene.separator_type,
                    word_count=self._count_words(parsed_scene, chapter.content),
                )
                scenes_to_save.append(scene)

        if scenes_to_save:
            self._repo.save_scenes_batch(scenes_to_save)
            logger.info(f"Persisted {len(scenes_to_save)} scenes for project {project_id}")

        return len(scenes_to_save)

    def _get_chapter_ids(self, project_id: int) -> dict[int, int]:
        """Obtiene mapping de chapter_number -> chapter_id."""
        rows = self.db.fetchall(
            "SELECT id, chapter_number FROM chapters WHERE project_id = ?",
            (project_id,),
        )
        return {row["chapter_number"]: row["id"] for row in rows}

    def _count_words(self, scene: ParsedScene, chapter_content: str) -> int:
        """Cuenta palabras en una escena."""
        # Ajustar offsets relativos al capítulo
        text = chapter_content[scene.start_char:scene.end_char]
        return len(text.split())

    # =========================================================================
    # Consultas de escenas
    # =========================================================================

    def get_scenes(self, project_id: int) -> list[SceneWithTags]:
        """
        Obtiene todas las escenas de un proyecto con sus etiquetas.

        Returns:
            Lista de SceneWithTags ordenada por capítulo y número de escena
        """
        scenes = self._repo.get_scenes_by_project(project_id)

        # Obtener datos de capítulos para enriquecer respuesta
        chapter_info = self._get_chapter_info(project_id)

        # Obtener entidades para nombres
        entities = self._get_entities_map(project_id)

        result = []
        for scene in scenes:
            tags = self._repo.get_scene_tags(scene.id)
            custom_tags = self._repo.get_custom_tags(scene.id)

            # Enriquecer con datos de UI
            chapter_data = chapter_info.get(scene.chapter_id, {})

            # Resolver nombres de ubicación y participantes
            location_name = None
            participant_names = []

            if tags:
                if tags.location_entity_id:
                    location_name = entities.get(tags.location_entity_id, {}).get("name")
                for pid in tags.participant_ids:
                    name = entities.get(pid, {}).get("name")
                    if name:
                        participant_names.append(name)

            result.append(SceneWithTags(
                scene=scene,
                tags=tags,
                custom_tags=custom_tags,
                chapter_number=chapter_data.get("number"),
                chapter_title=chapter_data.get("title"),
                location_name=location_name,
                participant_names=participant_names,
                excerpt=self._get_excerpt(scene, chapter_data.get("content", "")),
            ))

        return result

    def get_scenes_by_chapter(self, project_id: int, chapter_number: int) -> list[SceneWithTags]:
        """Obtiene escenas de un capítulo específico."""
        # Obtener chapter_id
        row = self.db.fetchone(
            "SELECT id, title, content FROM chapters WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter_number),
        )
        if not row:
            return []

        chapter_id = row["id"]
        chapter_title = row["title"]
        chapter_content = row["content"] or ""

        scenes = self._repo.get_scenes_by_chapter(chapter_id)
        entities = self._get_entities_map(project_id)

        result = []
        for scene in scenes:
            tags = self._repo.get_scene_tags(scene.id)
            custom_tags = self._repo.get_custom_tags(scene.id)

            location_name = None
            participant_names = []

            if tags:
                if tags.location_entity_id:
                    location_name = entities.get(tags.location_entity_id, {}).get("name")
                for pid in tags.participant_ids:
                    name = entities.get(pid, {}).get("name")
                    if name:
                        participant_names.append(name)

            result.append(SceneWithTags(
                scene=scene,
                tags=tags,
                custom_tags=custom_tags,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                location_name=location_name,
                participant_names=participant_names,
                excerpt=self._get_excerpt(scene, chapter_content),
            ))

        return result

    def _get_chapter_info(self, project_id: int) -> dict[int, dict]:
        """Obtiene información de capítulos."""
        rows = self.db.fetchall(
            "SELECT id, chapter_number, title, content FROM chapters WHERE project_id = ?",
            (project_id,),
        )
        return {
            row["id"]: {
                "number": row["chapter_number"],
                "title": row["title"],
                "content": row["content"] or "",
            }
            for row in rows
        }

    def _get_entities_map(self, project_id: int) -> dict[int, dict]:
        """Obtiene mapping de entity_id -> {name, type}."""
        rows = self.db.fetchall(
            "SELECT id, canonical_name, entity_type FROM entities WHERE project_id = ? AND is_active = 1",
            (project_id,),
        )
        return {
            row["id"]: {"name": row["canonical_name"], "type": row["entity_type"]}
            for row in rows
        }

    def _get_excerpt(self, scene: Scene, chapter_content: str, max_chars: int = 150) -> str:
        """Extrae un excerpt del inicio de la escena."""
        if not chapter_content:
            return ""

        # Las posiciones de escena son relativas al capítulo
        text = chapter_content[scene.start_char:scene.end_char]
        text = text.strip()

        if len(text) <= max_chars:
            return text

        # Truncar en el último espacio antes del límite
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + "..."

    # =========================================================================
    # Etiquetado
    # =========================================================================

    def tag_scene(
        self,
        scene_id: int,
        scene_type: Optional[SceneType] = None,
        tone: Optional[SceneTone] = None,
        location_entity_id: Optional[int] = None,
        participant_ids: Optional[list[int]] = None,
        summary: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Asigna etiquetas predefinidas a una escena.

        Returns:
            True si se guardó correctamente
        """
        scene = self._repo.get_scene(scene_id)
        if not scene:
            return False

        tags = SceneTag(
            id=0,
            scene_id=scene_id,
            scene_type=scene_type,
            tone=tone,
            location_entity_id=location_entity_id,
            participant_ids=participant_ids or [],
            summary=summary,
            notes=notes,
        )

        self._repo.save_scene_tags(scene_id, tags)
        logger.info(f"Tagged scene {scene_id}: type={scene_type}, tone={tone}")
        return True

    def add_custom_tag(
        self,
        scene_id: int,
        tag_name: str,
        tag_color: Optional[str] = None,
    ) -> bool:
        """
        Añade una etiqueta personalizada a una escena.

        Returns:
            True si se añadió correctamente
        """
        scene = self._repo.get_scene(scene_id)
        if not scene:
            return False

        self._repo.add_custom_tag(scene_id, tag_name, tag_color)

        # Añadir al catálogo del proyecto
        self._repo.add_to_catalog(scene.project_id, tag_name, tag_color)

        logger.info(f"Added custom tag '{tag_name}' to scene {scene_id}")
        return True

    def remove_custom_tag(self, scene_id: int, tag_name: str) -> bool:
        """Elimina una etiqueta personalizada de una escena."""
        return self._repo.remove_custom_tag(scene_id, tag_name)

    # =========================================================================
    # Estadísticas y metadata
    # =========================================================================

    def get_stats(self, project_id: int) -> SceneStats:
        """
        Obtiene estadísticas de escenas del proyecto.

        Útil para determinar si mostrar UI de escenas y qué filtros están disponibles.
        """
        scenes = self._repo.get_scenes_by_project(project_id)

        if not scenes:
            return SceneStats(
                total_scenes=0,
                chapters_with_scenes=0,
                tagged_scenes=0,
                untagged_scenes=0,
                scenes_by_type={},
                scenes_by_tone={},
                custom_tags_used=[],
                has_scenes=False,
            )

        # Contar capítulos con escenas (más de 1 escena por capítulo = tiene estructura)
        chapters_with_multiple = set()
        chapter_scene_counts: dict[int, int] = {}
        for scene in scenes:
            chapter_scene_counts[scene.chapter_id] = chapter_scene_counts.get(scene.chapter_id, 0) + 1

        for chapter_id, count in chapter_scene_counts.items():
            if count > 1:
                chapters_with_multiple.add(chapter_id)

        # Determinar si realmente tiene estructura de escenas
        # (al menos un capítulo con más de 1 escena)
        has_scenes = len(chapters_with_multiple) > 0

        # Contar tags
        tagged = 0
        untagged = 0
        by_type: dict[str, int] = {}
        by_tone: dict[str, int] = {}

        for scene in scenes:
            tags = self._repo.get_scene_tags(scene.id)
            if tags and (tags.scene_type or tags.tone):
                tagged += 1
                if tags.scene_type:
                    t = tags.scene_type.value
                    by_type[t] = by_type.get(t, 0) + 1
                if tags.tone:
                    t = tags.tone.value
                    by_tone[t] = by_tone.get(t, 0) + 1
            else:
                untagged += 1

        custom_tags = self._repo.get_all_custom_tags_in_project(project_id)

        return SceneStats(
            total_scenes=len(scenes),
            chapters_with_scenes=len(chapters_with_multiple),
            tagged_scenes=tagged,
            untagged_scenes=untagged,
            scenes_by_type=by_type,
            scenes_by_tone=by_tone,
            custom_tags_used=custom_tags,
            has_scenes=has_scenes,
        )

    def has_scene_structure(self, project_id: int) -> bool:
        """
        Determina si el proyecto tiene estructura de escenas.

        Útil para decidir si mostrar el tab de escenas en la UI.

        Un proyecto tiene estructura de escenas si al menos un capítulo
        tiene más de una escena detectada.
        """
        stats = self.get_stats(project_id)
        return stats.has_scenes

    # =========================================================================
    # Filtrado
    # =========================================================================

    def filter_scenes(
        self,
        project_id: int,
        scene_type: Optional[SceneType] = None,
        tone: Optional[SceneTone] = None,
        custom_tag: Optional[str] = None,
        location_id: Optional[int] = None,
        participant_id: Optional[int] = None,
    ) -> list[SceneWithTags]:
        """
        Filtra escenas por criterios.

        Args:
            project_id: ID del proyecto
            scene_type: Filtrar por tipo de escena
            tone: Filtrar por tono
            custom_tag: Filtrar por etiqueta personalizada
            location_id: Filtrar por ubicación
            participant_id: Filtrar por participante

        Returns:
            Lista de escenas que cumplen todos los criterios
        """
        # Obtener todas las escenas y filtrar
        all_scenes = self.get_scenes(project_id)

        result = []
        for swt in all_scenes:
            # Aplicar filtros
            if scene_type and (not swt.tags or swt.tags.scene_type != scene_type):
                continue

            if tone and (not swt.tags or swt.tags.tone != tone):
                continue

            if location_id and (not swt.tags or swt.tags.location_entity_id != location_id):
                continue

            if participant_id and (not swt.tags or participant_id not in swt.tags.participant_ids):
                continue

            if custom_tag:
                has_tag = any(ct.tag_name == custom_tag for ct in swt.custom_tags)
                if not has_tag:
                    continue

            result.append(swt)

        return result

    def get_tag_catalog(self, project_id: int) -> list[dict]:
        """
        Obtiene el catálogo de etiquetas personalizadas disponibles.

        Returns:
            Lista de diccionarios con name, color, usage_count
        """
        catalog = self._repo.get_catalog(project_id)
        return [
            {
                "name": item.tag_name,
                "color": item.tag_color,
                "usage_count": item.usage_count,
            }
            for item in catalog
        ]
