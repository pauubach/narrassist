"""
Repositorio de entidades - Acceso a datos en SQLite.

Proporciona CRUD para entidades, menciones y atributos,
con soporte para transacciones y búsquedas.
"""

import json
import logging
import threading
from datetime import datetime
from typing import Optional

from ..persistence.database import get_database, Database
from .models import (
    Entity,
    EntityType,
    EntityImportance,
    EntityMention,
    MergeHistory,
)

logger = logging.getLogger(__name__)


class EntityRepository:
    """
    Repositorio para gestión de entidades en SQLite.

    Proporciona operaciones CRUD y búsquedas especializadas
    para entidades narrativas y sus menciones.
    """

    def __init__(self, database: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            database: Instancia de Database. Si None, usa singleton.
        """
        self.db = database or get_database()

    # =========================================================================
    # Entidades - CRUD
    # =========================================================================

    def create_entity(self, entity: Entity) -> int:
        """
        Crea una nueva entidad.

        Args:
            entity: Entidad a crear

        Returns:
            ID de la entidad creada
        """
        # Serializar aliases y merged_from en JSON
        merged_data = json.dumps({
            "aliases": entity.aliases,
            "merged_ids": entity.merged_from_ids,
        })

        sql = """
            INSERT INTO entities (
                project_id, entity_type, canonical_name, importance,
                description, first_appearance_char, mention_count,
                merged_from_ids, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self.db.connection() as conn:
            cursor = conn.execute(
                sql,
                (
                    entity.project_id,
                    entity.entity_type.value,
                    entity.canonical_name,
                    entity.importance.value,
                    entity.description,
                    entity.first_appearance_char,
                    entity.mention_count,
                    merged_data,
                    1 if entity.is_active else 0,
                ),
            )
            entity_id = cursor.lastrowid
            logger.debug(f"Entidad creada: {entity.canonical_name} (ID={entity_id})")
            return entity_id

    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """
        Obtiene una entidad por ID.

        Args:
            entity_id: ID de la entidad

        Returns:
            Entity o None si no existe
        """
        row = self.db.fetchone(
            "SELECT * FROM entities WHERE id = ?",
            (entity_id,),
        )
        return Entity.from_row(row) if row else None

    def get_entities_by_project(
        self,
        project_id: int,
        entity_type: Optional[EntityType] = None,
        active_only: bool = True,
    ) -> list[Entity]:
        """
        Obtiene entidades de un proyecto.

        Args:
            project_id: ID del proyecto
            entity_type: Filtrar por tipo (opcional)
            active_only: Solo entidades activas

        Returns:
            Lista de entidades
        """
        sql = "SELECT * FROM entities WHERE project_id = ?"
        params: list = [project_id]

        if active_only:
            sql += " AND is_active = 1"

        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type.value)

        sql += " ORDER BY mention_count DESC, canonical_name"

        rows = self.db.fetchall(sql, tuple(params))
        return [Entity.from_row(row) for row in rows]

    def update_entity(
        self,
        entity_id: int,
        canonical_name: Optional[str] = None,
        aliases: Optional[list[str]] = None,
        importance: Optional[EntityImportance] = None,
        description: Optional[str] = None,
        merged_from_ids: Optional[list[int]] = None,
    ) -> bool:
        """
        Actualiza campos de una entidad.

        Args:
            entity_id: ID de la entidad
            canonical_name: Nuevo nombre canónico
            aliases: Nueva lista de aliases
            importance: Nueva importancia
            description: Nueva descripción
            merged_from_ids: Nuevos IDs fusionados

        Returns:
            True si se actualizó
        """
        updates = []
        params = []

        if canonical_name is not None:
            updates.append("canonical_name = ?")
            params.append(canonical_name)

        if aliases is not None or merged_from_ids is not None:
            # Obtener valores actuales si solo uno se actualiza
            current = self.get_entity(entity_id)
            if current:
                new_aliases = aliases if aliases is not None else current.aliases
                new_merged = (
                    merged_from_ids
                    if merged_from_ids is not None
                    else current.merged_from_ids
                )
                merged_data = json.dumps({
                    "aliases": new_aliases,
                    "merged_ids": new_merged,
                })
                updates.append("merged_from_ids = ?")
                params.append(merged_data)

        if importance is not None:
            updates.append("importance = ?")
            params.append(importance.value)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return False

        updates.append("updated_at = datetime('now')")
        params.append(entity_id)

        sql = f"UPDATE entities SET {', '.join(updates)} WHERE id = ?"

        with self.db.connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            return cursor.rowcount > 0

    def delete_entity(self, entity_id: int, hard_delete: bool = False) -> bool:
        """
        Elimina o desactiva una entidad.

        Args:
            entity_id: ID de la entidad
            hard_delete: Si True, elimina de la BD. Si False, marca como inactiva.

        Returns:
            True si se eliminó/desactivó
        """
        if hard_delete:
            sql = "DELETE FROM entities WHERE id = ?"
        else:
            sql = "UPDATE entities SET is_active = 0, updated_at = datetime('now') WHERE id = ?"

        with self.db.connection() as conn:
            cursor = conn.execute(sql, (entity_id,))
            return cursor.rowcount > 0

    def increment_mention_count(self, entity_id: int, delta: int = 1) -> None:
        """Incrementa el contador de menciones."""
        self.db.execute(
            "UPDATE entities SET mention_count = mention_count + ? WHERE id = ?",
            (delta, entity_id),
        )

    # =========================================================================
    # Menciones - CRUD
    # =========================================================================

    def create_mention(self, mention: EntityMention) -> int:
        """
        Crea una nueva mención.

        Args:
            mention: Mención a crear

        Returns:
            ID de la mención creada
        """
        sql = """
            INSERT INTO entity_mentions (
                entity_id, chapter_id, surface_form, start_char, end_char,
                context_before, context_after, confidence, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self.db.connection() as conn:
            cursor = conn.execute(
                sql,
                (
                    mention.entity_id,
                    mention.chapter_id,
                    mention.surface_form,
                    mention.start_char,
                    mention.end_char,
                    mention.context_before,
                    mention.context_after,
                    mention.confidence,
                    mention.source,
                ),
            )
            return cursor.lastrowid

    def create_mentions_batch(self, mentions: list[EntityMention]) -> int:
        """
        Crea múltiples menciones en batch.

        Args:
            mentions: Lista de menciones

        Returns:
            Número de menciones creadas
        """
        if not mentions:
            return 0

        sql = """
            INSERT INTO entity_mentions (
                entity_id, chapter_id, surface_form, start_char, end_char,
                context_before, context_after, confidence, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = [
            (
                m.entity_id,
                m.chapter_id,
                m.surface_form,
                m.start_char,
                m.end_char,
                m.context_before,
                m.context_after,
                m.confidence,
                m.source,
            )
            for m in mentions
        ]

        with self.db.connection() as conn:
            conn.executemany(sql, params)
            return len(params)

    def get_mentions_by_entity(self, entity_id: int) -> list[EntityMention]:
        """Obtiene todas las menciones de una entidad."""
        rows = self.db.fetchall(
            "SELECT * FROM entity_mentions WHERE entity_id = ? ORDER BY start_char",
            (entity_id,),
        )
        return [EntityMention.from_row(row) for row in rows]

    def get_mentions_by_chapter(self, chapter_id: int) -> list[EntityMention]:
        """Obtiene todas las menciones de un capítulo."""
        rows = self.db.fetchall(
            "SELECT * FROM entity_mentions WHERE chapter_id = ? ORDER BY start_char",
            (chapter_id,),
        )
        return [EntityMention.from_row(row) for row in rows]

    def find_mention_by_position(
        self,
        entity_id: int,
        start_char: int,
        end_char: int,
        chapter_id: Optional[int] = None,
    ) -> Optional[EntityMention]:
        """
        Busca una mención por entity_id y posición de caracteres.

        Útil para vincular atributos extraídos con sus menciones de origen.

        Args:
            entity_id: ID de la entidad
            start_char: Posición inicial del carácter
            end_char: Posición final del carácter
            chapter_id: ID del capítulo (opcional, para búsqueda más precisa)

        Returns:
            EntityMention si se encuentra, None si no
        """
        if chapter_id is not None:
            # Búsqueda exacta con chapter_id
            row = self.db.fetchone(
                """
                SELECT * FROM entity_mentions
                WHERE entity_id = ? AND chapter_id = ?
                AND start_char <= ? AND end_char >= ?
                ORDER BY ABS(start_char - ?) + ABS(end_char - ?)
                LIMIT 1
                """,
                (entity_id, chapter_id, start_char, end_char, start_char, end_char),
            )
        else:
            # Búsqueda sin chapter_id - buscar la mención más cercana
            row = self.db.fetchone(
                """
                SELECT * FROM entity_mentions
                WHERE entity_id = ?
                AND start_char <= ? AND end_char >= ?
                ORDER BY ABS(start_char - ?) + ABS(end_char - ?)
                LIMIT 1
                """,
                (entity_id, start_char, end_char, start_char, end_char),
            )

        return EntityMention.from_row(row) if row else None

    def move_mentions(self, from_entity_id: int, to_entity_id: int) -> int:
        """
        Mueve todas las menciones de una entidad a otra.

        Args:
            from_entity_id: ID de la entidad origen
            to_entity_id: ID de la entidad destino

        Returns:
            Número de menciones movidas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            return cursor.rowcount

    def delete_mentions_by_entity(self, entity_id: int) -> int:
        """Elimina todas las menciones de una entidad."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM entity_mentions WHERE entity_id = ?",
                (entity_id,),
            )
            return cursor.rowcount

    # =========================================================================
    # Atributos
    # =========================================================================

    def create_attribute(
        self,
        entity_id: int,
        attribute_type: str,
        attribute_key: str,
        attribute_value: str,
        confidence: float = 1.0,
        source_mention_id: Optional[int] = None,
    ) -> int:
        """
        Crea un nuevo atributo para una entidad.

        Args:
            entity_id: ID de la entidad
            attribute_type: Tipo de atributo (physical, psychological, social, role)
            attribute_key: Clave del atributo (eye_color, hair_color, etc.)
            attribute_value: Valor del atributo
            confidence: Confianza de la extracción (0.0-1.0)
            source_mention_id: ID de la mención de origen (opcional)

        Returns:
            ID del atributo creado
        """
        sql = """
            INSERT INTO entity_attributes (
                entity_id, attribute_type, attribute_key, attribute_value,
                confidence, source_mention_id, is_verified
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
        """

        with self.db.connection() as conn:
            cursor = conn.execute(
                sql,
                (
                    entity_id,
                    attribute_type,
                    attribute_key,
                    attribute_value,
                    confidence,
                    source_mention_id,
                ),
            )
            attribute_id = cursor.lastrowid
            logger.debug(
                f"Attribute created: {attribute_key}={attribute_value} for entity {entity_id} (ID={attribute_id})"
            )
            return attribute_id

    def move_attributes(self, from_entity_id: int, to_entity_id: int) -> int:
        """
        Mueve todos los atributos de una entidad a otra.

        Args:
            from_entity_id: ID de la entidad origen
            to_entity_id: ID de la entidad destino

        Returns:
            Número de atributos movidos
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "UPDATE entity_attributes SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            return cursor.rowcount

    def get_attributes_by_entity(self, entity_id: int) -> list[dict]:
        """
        Obtiene todos los atributos de una entidad específica.

        Args:
            entity_id: ID de la entidad

        Returns:
            Lista de atributos con sus datos, incluyendo información de la mención fuente
        """
        rows = self.db.fetchall(
            """
            SELECT
                ea.id,
                ea.entity_id,
                ea.attribute_type,
                ea.attribute_key,
                ea.attribute_value,
                ea.confidence,
                ea.source_mention_id,
                ea.is_verified,
                ea.created_at,
                em.start_char,
                em.end_char,
                em.chapter_id,
                c.chapter_number
            FROM entity_attributes ea
            LEFT JOIN entity_mentions em ON ea.source_mention_id = em.id
            LEFT JOIN chapters c ON em.chapter_id = c.id
            WHERE ea.entity_id = ?
            ORDER BY ea.attribute_type, ea.attribute_key
            """,
            (entity_id,),
        )

        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "entity_id": row["entity_id"],
                "category": row["attribute_type"],
                "name": row["attribute_key"],
                "value": row["attribute_value"],
                "confidence": row["confidence"],
                "source_mention_id": row["source_mention_id"],
                "is_verified": bool(row["is_verified"]),
                "created_at": row["created_at"],
                "span_start": row["start_char"],
                "span_end": row["end_char"],
                "chapter_id": row["chapter_id"],
                "chapter": row["chapter_number"],
            })

        return result

    def update_attribute(
        self,
        attribute_id: int,
        attribute_key: Optional[str] = None,
        attribute_value: Optional[str] = None,
        is_verified: Optional[bool] = None,
    ) -> bool:
        """
        Actualiza un atributo existente.

        Args:
            attribute_id: ID del atributo
            attribute_key: Nueva clave/nombre (opcional)
            attribute_value: Nuevo valor (opcional)
            is_verified: Marcar como verificado (opcional)

        Returns:
            True si se actualizó
        """
        updates = []
        params = []

        if attribute_key is not None:
            updates.append("attribute_key = ?")
            params.append(attribute_key)

        if attribute_value is not None:
            updates.append("attribute_value = ?")
            params.append(attribute_value)

        if is_verified is not None:
            updates.append("is_verified = ?")
            params.append(1 if is_verified else 0)

        if not updates:
            return False

        params.append(attribute_id)
        sql = f"UPDATE entity_attributes SET {', '.join(updates)} WHERE id = ?"

        with self.db.connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            return cursor.rowcount > 0

    def delete_attribute(self, attribute_id: int) -> bool:
        """
        Elimina un atributo.

        Args:
            attribute_id: ID del atributo

        Returns:
            True si se eliminó
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM entity_attributes WHERE id = ?",
                (attribute_id,),
            )
            return cursor.rowcount > 0

    def get_attribute_evidences(self, attribute_id: int) -> list[dict]:
        """
        Obtiene todas las evidencias de un atributo.

        Args:
            attribute_id: ID del atributo

        Returns:
            Lista de evidencias con ubicaciones completas

        Example:
            >>> evidences = repo.get_attribute_evidences(42)
            >>> for ev in evidences:
            ...     print(f"Cap {ev['chapter']}, pág {ev['page']}, lín {ev['line']}")
            ...     print(f"  Método: {ev['extraction_method']}")
            ...     print(f"  Keywords: {ev['keywords']}")
        """
        import json

        rows = self.db.fetchall(
            """
            SELECT
                id,
                start_char,
                end_char,
                chapter,
                page,
                line,
                excerpt,
                extraction_method,
                keywords,
                confidence,
                created_at
            FROM attribute_evidences
            WHERE attribute_id = ?
            ORDER BY chapter, start_char
            """,
            (attribute_id,),
        )

        evidences = []
        for row in rows:
            evidence = {
                "id": row["id"],
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "chapter": row["chapter"],
                "page": row["page"],
                "line": row["line"],
                "excerpt": row["excerpt"],
                "extraction_method": row["extraction_method"],
                "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                "confidence": row["confidence"],
                "created_at": row["created_at"],
            }
            evidences.append(evidence)

        return evidences

    def get_attributes_by_project(self, project_id: int) -> list[dict]:
        """
        Obtiene todos los atributos de un proyecto con el nombre canónico de la entidad.

        Hace JOIN con entities para obtener el canonical_name actualizado
        (importante después de fusiones).

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de dicts con: entity_id, entity_name, attribute_type,
            attribute_key, attribute_value, confidence, source_mention_id
        """
        sql = """
            SELECT
                ea.id as attribute_id,
                ea.entity_id,
                e.canonical_name as entity_name,
                ea.attribute_type,
                ea.attribute_key,
                ea.attribute_value,
                ea.confidence,
                ea.source_mention_id,
                ea.created_at
            FROM entity_attributes ea
            JOIN entities e ON ea.entity_id = e.id
            WHERE e.project_id = ?
            AND e.is_active = 1
            ORDER BY e.canonical_name, ea.attribute_key
        """

        rows = self.db.fetchall(sql, (project_id,))

        result = []
        for row in rows:
            result.append({
                "attribute_id": row["attribute_id"],
                "entity_id": row["entity_id"],
                "entity_name": row["entity_name"],
                "attribute_type": row["attribute_type"],
                "attribute_key": row["attribute_key"],
                "attribute_value": row["attribute_value"],
                "confidence": row["confidence"],
                "source_mention_id": row["source_mention_id"],
                "created_at": row["created_at"],
            })

        logger.debug(f"Retrieved {len(result)} attributes for project {project_id}")
        return result

    # =========================================================================
    # Historial de fusiones
    # =========================================================================

    def add_merge_history(
        self,
        project_id: int,
        result_entity_id: int,
        source_entity_ids: list[int],
        source_snapshots: list[dict],
        canonical_names_before: list[str],
        merged_by: str = "user",
        note: Optional[str] = None,
    ) -> int:
        """
        Registra una fusión en el historial.

        Args:
            project_id: ID del proyecto
            result_entity_id: ID de la entidad resultante
            source_entity_ids: IDs de entidades fusionadas
            source_snapshots: Snapshots de entidades antes de fusionar
            canonical_names_before: Nombres canónicos originales
            merged_by: Quién realizó la fusión
            note: Nota opcional

        Returns:
            ID del registro
        """
        # Guardar en review_history con formato JSON
        old_value = json.dumps({
            "source_entity_ids": source_entity_ids,
            "source_snapshots": source_snapshots,
            "canonical_names_before": canonical_names_before,
        })
        new_value = json.dumps({
            "result_entity_id": result_entity_id,
            "merged_by": merged_by,
        })

        sql = """
            INSERT INTO review_history (
                project_id, action_type, target_type, target_id,
                old_value_json, new_value_json, note
            ) VALUES (?, 'entity_merged', 'entity', ?, ?, ?, ?)
        """

        with self.db.connection() as conn:
            cursor = conn.execute(
                sql,
                (project_id, result_entity_id, old_value, new_value, note),
            )
            return cursor.lastrowid

    def get_merge_history(self, project_id: int) -> list[MergeHistory]:
        """
        Obtiene historial de fusiones de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de registros de fusión
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM review_history
            WHERE project_id = ? AND action_type = 'entity_merged'
            ORDER BY created_at DESC
            """,
            (project_id,),
        )

        history = []
        for row in rows:
            old_data = json.loads(row["old_value_json"]) if row["old_value_json"] else {}
            new_data = json.loads(row["new_value_json"]) if row["new_value_json"] else {}

            history.append(
                MergeHistory(
                    id=row["id"],
                    project_id=row["project_id"],
                    result_entity_id=new_data.get("result_entity_id", row["target_id"]),
                    source_entity_ids=old_data.get("source_entity_ids", []),
                    source_snapshots=old_data.get("source_snapshots", []),
                    canonical_name_before=old_data.get("canonical_names_before", []),
                    merged_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                    merged_by=new_data.get("merged_by", "user"),
                    note=row["note"],
                )
            )

        return history

    def mark_merge_undone(self, merge_id: int) -> bool:
        """
        Marca una fusión como deshecha.

        Args:
            merge_id: ID del registro de fusión

        Returns:
            True si se actualizó
        """
        # Añadir nota indicando que fue deshecha
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE review_history
                SET note = COALESCE(note || ' ', '') || '[UNDONE at ' || datetime('now') || ']'
                WHERE id = ?
                """,
                (merge_id,),
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Búsquedas especializadas
    # =========================================================================

    def find_entities_by_name(
        self,
        project_id: int,
        name: str,
        fuzzy: bool = False,
    ) -> list[Entity]:
        """
        Busca entidades por nombre.

        Args:
            project_id: ID del proyecto
            name: Nombre a buscar
            fuzzy: Si True, usa LIKE para búsqueda parcial

        Returns:
            Lista de entidades que coinciden
        """
        if fuzzy:
            sql = """
                SELECT * FROM entities
                WHERE project_id = ? AND is_active = 1
                AND (canonical_name LIKE ? OR merged_from_ids LIKE ?)
            """
            pattern = f"%{name}%"
            rows = self.db.fetchall(sql, (project_id, pattern, pattern))
        else:
            sql = """
                SELECT * FROM entities
                WHERE project_id = ? AND is_active = 1
                AND LOWER(canonical_name) = LOWER(?)
            """
            rows = self.db.fetchall(sql, (project_id, name))

        return [Entity.from_row(row) for row in rows]

    def get_entity_stats(self, project_id: int) -> dict:
        """
        Obtiene estadísticas de entidades de un proyecto.

        Returns:
            Dict con conteos por tipo e importancia
        """
        stats = {
            "total": 0,
            "by_type": {},
            "by_importance": {},
        }

        # Total
        row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM entities WHERE project_id = ? AND is_active = 1",
            (project_id,),
        )
        stats["total"] = row["cnt"] if row else 0

        # Por tipo
        rows = self.db.fetchall(
            """
            SELECT entity_type, COUNT(*) as cnt
            FROM entities WHERE project_id = ? AND is_active = 1
            GROUP BY entity_type
            """,
            (project_id,),
        )
        stats["by_type"] = {row["entity_type"]: row["cnt"] for row in rows}

        # Por importancia
        rows = self.db.fetchall(
            """
            SELECT importance, COUNT(*) as cnt
            FROM entities WHERE project_id = ? AND is_active = 1
            GROUP BY importance
            """,
            (project_id,),
        )
        stats["by_importance"] = {row["importance"]: row["cnt"] for row in rows}

        return stats


# =============================================================================
# Singleton thread-safe
# =============================================================================

_repo_lock = threading.Lock()
_entity_repository: Optional[EntityRepository] = None


def get_entity_repository(database: Optional[Database] = None) -> EntityRepository:
    """
    Obtiene el singleton del repositorio de entidades.

    Args:
        database: Instancia de Database (opcional)

    Returns:
        Instancia única del EntityRepository
    """
    global _entity_repository

    if _entity_repository is None:
        with _repo_lock:
            if _entity_repository is None:
                _entity_repository = EntityRepository(database)

    return _entity_repository


def reset_entity_repository() -> None:
    """Resetea el singleton (útil para tests)."""
    global _entity_repository
    with _repo_lock:
        _entity_repository = None
