"""Utilidad compartida para cargar menciones de entidades por capítulo.

Usado por:
- api-server/routers/chapters.py (endpoint timeline)
- analysis_pipeline.py (pipeline batch)
- document_exporter.py (exportación DOC/PDF)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tipos de entidad que se consideran "personaje" para instancias temporales.
_CHARACTER_TYPES = frozenset({
    "character", "animal", "creature", "per", "person", "pers",
})


def _get_entity_type_str(entity: Any) -> str:
    """Extrae entity_type como string normalizado."""
    entity_type = getattr(entity, "entity_type", None)
    if entity_type is None:
        return ""
    if hasattr(entity_type, "value"):
        return str(entity_type.value).lower()
    return str(entity_type).lower()


def is_character_entity(entity: Any) -> bool:
    """Verifica si una entidad es de tipo personaje/criatura."""
    return _get_entity_type_str(entity) in _CHARACTER_TYPES


def load_entity_mentions_by_chapter(
    entities: list[Any],
    chapters: list[Any],
    entity_repository: Any,
) -> dict[int, list[tuple[int, int, int]]]:
    """Carga menciones de entidades-personaje agrupadas por número de capítulo.

    Convierte coordenadas globales del documento a posiciones relativas al
    capítulo, que es lo que espera ``TemporalMarkerExtractor.extract_with_entities``.

    Args:
        entities: Lista de entidades (necesitan ``.id`` y ``.entity_type``).
        chapters: Lista de capítulos (necesitan ``.id``, ``.chapter_number``, ``.start_char``).
        entity_repository: Repositorio con ``.get_mentions_by_entity(entity_id)``.

    Returns:
        Dict ``{chapter_number: [(entity_id, rel_start, rel_end), ...]}``
    """
    result: dict[int, list[tuple[int, int, int]]] = {}

    chapter_number_by_id = {ch.id: ch.chapter_number for ch in chapters}
    chapter_start_by_id = {ch.id: ch.start_char for ch in chapters}

    for entity in entities:
        if not entity.id or not is_character_entity(entity):
            continue

        mentions = entity_repository.get_mentions_by_entity(entity.id)
        for mention in mentions:
            chapter_number = chapter_number_by_id.get(mention.chapter_id)
            if chapter_number is None:
                continue

            chapter_start = chapter_start_by_id.get(mention.chapter_id, 0)
            rel_start = mention.start_char - chapter_start
            rel_end = mention.end_char - chapter_start
            if rel_end <= 0:
                continue

            result.setdefault(chapter_number, []).append(
                (entity.id, max(0, rel_start), max(0, rel_end))
            )

    return result
