"""
Repositorio de entidades - Acceso a datos en SQLite.

Proporciona CRUD para entidades, menciones y atributos,
con soporte para transacciones y búsquedas.
"""

import json
import logging
import threading
from datetime import datetime

from ..persistence.database import Database, get_database
from .models import (
    Entity,
    EntityImportance,
    EntityMention,
    EntityType,
    MergeHistory,
)

logger = logging.getLogger(__name__)


class EntityRepository:
    """
    Repositorio para gestión de entidades en SQLite.

    Proporciona operaciones CRUD y búsquedas especializadas
    para entidades narrativas y sus menciones.
    """

    def __init__(self, database: Database | None = None):
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
        merged_data = json.dumps(
            {
                "aliases": entity.aliases,
                "merged_ids": entity.merged_from_ids,
            }
        )

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

    def get_entity(self, entity_id: int) -> Entity | None:
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
        entity_type: EntityType | None = None,
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

    # Alias para compatibilidad
    get_by_project = get_entities_by_project

    def update_entity(
        self,
        entity_id: int,
        canonical_name: str | None = None,
        aliases: list[str] | None = None,
        importance: EntityImportance | None = None,
        description: str | None = None,
        merged_from_ids: list[int] | None = None,
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
                merged_data = json.dumps(
                    {
                        "aliases": new_aliases,
                        "merged_ids": new_merged,
                    }
                )
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

    def delete_entities_by_project(self, project_id: int) -> int:
        """
        Elimina todas las entidades de un proyecto (hard delete).

        También elimina las menciones asociadas gracias a ON DELETE CASCADE.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de entidades eliminadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM entities WHERE project_id = ?",
                (project_id,),
            )
            count = cursor.rowcount
            logger.info(f"Deleted {count} entities for project {project_id}")
            return count

    def increment_mention_count(self, entity_id: int, delta: int = 1) -> None:
        """Incrementa el contador de menciones."""
        self.db.execute(
            "UPDATE entities SET mention_count = mention_count + ? WHERE id = ?",
            (delta, entity_id),
        )

    def reconcile_mention_count(self, entity_id: int) -> int:
        """
        Reconcilia el contador de menciones con las menciones reales en la BD.

        Esto asegura consistencia después de fusiones u otras operaciones.

        Args:
            entity_id: ID de la entidad

        Returns:
            El nuevo valor de mention_count
        """
        # Contar menciones reales
        row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM entity_mentions WHERE entity_id = ?",
            (entity_id,),
        )
        actual_count = row["cnt"] if row else 0

        # Actualizar el campo mention_count
        self.db.execute(
            "UPDATE entities SET mention_count = ? WHERE id = ?",
            (actual_count, entity_id),
        )
        return actual_count

    def reconcile_all_mention_counts(self, project_id: int) -> int:
        """
        Reconcilia los contadores de menciones para todas las entidades de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de entidades actualizadas
        """
        # Actualizar todas las entidades del proyecto en una sola query
        self.db.execute(
            """
            UPDATE entities
            SET mention_count = (
                SELECT COUNT(*)
                FROM entity_mentions
                WHERE entity_mentions.entity_id = entities.id
            )
            WHERE project_id = ? AND is_active = 1
            """,
            (project_id,),
        )
        row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM entities WHERE project_id = ? AND is_active = 1",
            (project_id,),
        )
        return row["cnt"] if row and "cnt" in row else 0

    # =========================================================================
    # Menciones - CRUD
    # =========================================================================

    def create_mention(self, mention: EntityMention) -> int:
        """
        Crea una nueva mención.

        Args:
            mention: Mención a crear

        Returns:
            ID de la mención creada (0 si ya existía)
        """
        # INSERT OR IGNORE evita duplicados cuando hay constraint único
        sql = """
            INSERT OR IGNORE INTO entity_mentions (
                entity_id, chapter_id, surface_form, start_char, end_char,
                context_before, context_after, confidence, source, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    mention.metadata,
                ),
            )
            return cursor.lastrowid

    def create_mentions_batch(self, mentions: list[EntityMention]) -> int:
        """
        Crea múltiples menciones en batch.

        Usa INSERT OR IGNORE para evitar duplicados cuando hay un constraint
        único en (entity_id, start_char, end_char).

        Args:
            mentions: Lista de menciones

        Returns:
            Número de menciones intentadas (puede haber menos insertadas si hay duplicados)
        """
        if not mentions:
            return 0

        # INSERT OR IGNORE evita duplicados cuando hay constraint único
        sql = """
            INSERT OR IGNORE INTO entity_mentions (
                entity_id, chapter_id, surface_form, start_char, end_char,
                context_before, context_after, confidence, source, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                m.metadata,
            )
            for m in mentions
        ]

        with self.db.connection() as conn:
            cursor = conn.executemany(sql, params)
            # Retorna el número real de filas insertadas (no las ignoradas)
            return cursor.rowcount

    def get_mentions_by_entity(self, entity_id: int) -> list[EntityMention]:
        """Obtiene todas las menciones de una entidad."""
        rows = self.db.fetchall(
            "SELECT * FROM entity_mentions WHERE entity_id = ? ORDER BY start_char",
            (entity_id,),
        )
        return [EntityMention.from_row(row) for row in rows]

    def get_mentions_by_project(
        self, project_id: int
    ) -> list[dict]:
        """
        Obtiene todas las menciones de un proyecto con JOIN a entidades.

        Evita el patrón N+1: una sola query en vez de una por entidad.
        Retorna dicts con entity_id, entity_name, start_char, end_char, chapter_id.
        """
        rows = self.db.fetchall(
            """SELECT m.entity_id, e.canonical_name AS entity_name,
                      m.start_char, m.end_char, m.chapter_id
               FROM entity_mentions m
               JOIN entities e ON e.id = m.entity_id
               WHERE e.project_id = ? AND e.is_active = 1
               ORDER BY m.start_char""",
            (project_id,),
        )
        return [
            {
                "entity_id": r["entity_id"],
                "entity_name": r["entity_name"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "chapter_id": r["chapter_id"],
            }
            for r in rows
        ]

    def get_entity_ids_for_chapter(
        self, chapter_id: int, chapter_start: int, chapter_end: int
    ) -> set[int]:
        """Obtiene IDs de entidades con menciones en un capítulo (query única)."""
        rows = self.db.fetchall(
            """SELECT DISTINCT entity_id FROM entity_mentions
               WHERE chapter_id = ?
                  OR (start_char >= ? AND start_char < ?)""",
            (chapter_id, chapter_start, chapter_end),
        )
        return {row["entity_id"] for row in rows}

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
        chapter_id: int | None = None,
    ) -> EntityMention | None:
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
        source_mention_id: int | None = None,
        chapter_id: int | None = None,
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
            chapter_id: Capítulo donde se detectó el atributo (opcional, S8a-06)

        Returns:
            ID del atributo creado
        """
        sql = """
            INSERT INTO entity_attributes (
                entity_id, attribute_type, attribute_key, attribute_value,
                confidence, source_mention_id, chapter_id, is_verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
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
                    chapter_id,
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

    def move_related_data(
        self, from_entity_id: int, to_entity_id: int
    ) -> dict[str, int]:
        """
        Migra todas las referencias FK de una entidad a otra.

        Cubre las 14 columnas FK en 10 tablas que no se migran
        con move_mentions() / move_attributes(). Se ejecuta dentro
        de una sola transacción.

        Args:
            from_entity_id: ID de la entidad origen (será desactivada)
            to_entity_id: ID de la entidad destino

        Returns:
            Dict con conteos de filas afectadas por tabla
        """
        counts: dict[str, int] = {}

        with self.db.connection() as conn:
            # 1. temporal_markers (entity_id → SET NULL)
            c = conn.execute(
                "UPDATE temporal_markers SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["temporal_markers"] = c.rowcount

            # 2. voice_profiles (UNIQUE on project_id, entity_id)
            #    Si el destino ya tiene perfil, eliminar el origen; sino, mover.
            existing = conn.execute(
                "SELECT id FROM voice_profiles WHERE entity_id = ?",
                (to_entity_id,),
            ).fetchone()
            if existing:
                c = conn.execute(
                    "DELETE FROM voice_profiles WHERE entity_id = ?",
                    (from_entity_id,),
                )
            else:
                c = conn.execute(
                    "UPDATE voice_profiles SET entity_id = ? WHERE entity_id = ?",
                    (to_entity_id, from_entity_id),
                )
            counts["voice_profiles"] = c.rowcount

            # 3. vital_status_events
            c = conn.execute(
                "UPDATE vital_status_events SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["vital_status_events"] = c.rowcount

            # 4. character_location_events
            c = conn.execute(
                "UPDATE character_location_events SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["character_location_events"] = c.rowcount

            # 5. ooc_events
            c = conn.execute(
                "UPDATE ooc_events SET entity_id = ? WHERE entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["ooc_events"] = c.rowcount

            # 6-8. relationships (entity1_id + entity2_id + self-ref cleanup)
            c1 = conn.execute(
                "UPDATE relationships SET entity1_id = ? WHERE entity1_id = ?",
                (to_entity_id, from_entity_id),
            )
            c2 = conn.execute(
                "UPDATE relationships SET entity2_id = ? WHERE entity2_id = ?",
                (to_entity_id, from_entity_id),
            )
            c3 = conn.execute(
                "DELETE FROM relationships WHERE entity1_id = entity2_id",
            )
            counts["relationships"] = c1.rowcount + c2.rowcount
            counts["relationships_self_deleted"] = c3.rowcount

            # 9-10. interactions (entity1_id + entity2_id)
            c1 = conn.execute(
                "UPDATE interactions SET entity1_id = ? WHERE entity1_id = ?",
                (to_entity_id, from_entity_id),
            )
            c2 = conn.execute(
                "UPDATE interactions SET entity2_id = ? WHERE entity2_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["interactions"] = c1.rowcount + c2.rowcount

            # 11. coreference_corrections (original_entity_id + corrected_entity_id)
            c1 = conn.execute(
                "UPDATE coreference_corrections SET original_entity_id = ? WHERE original_entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            c2 = conn.execute(
                "UPDATE coreference_corrections SET corrected_entity_id = ? WHERE corrected_entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["coreference_corrections"] = c1.rowcount + c2.rowcount

            # 12. speaker_corrections (original_speaker_id + corrected_speaker_id)
            c1 = conn.execute(
                "UPDATE speaker_corrections SET original_speaker_id = ? WHERE original_speaker_id = ?",
                (to_entity_id, from_entity_id),
            )
            c2 = conn.execute(
                "UPDATE speaker_corrections SET corrected_speaker_id = ? WHERE corrected_speaker_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["speaker_corrections"] = c1.rowcount + c2.rowcount

            # 13-14. collection_entity_links (source + target, skip duplicates)
            conn.execute(
                """UPDATE collection_entity_links
                   SET source_entity_id = ?
                   WHERE source_entity_id = ?
                     AND NOT EXISTS (
                         SELECT 1 FROM collection_entity_links dup
                         WHERE dup.collection_id = collection_entity_links.collection_id
                           AND dup.source_entity_id = ?
                           AND dup.target_entity_id = collection_entity_links.target_entity_id
                     )""",
                (to_entity_id, from_entity_id, to_entity_id),
            )
            conn.execute(
                """UPDATE collection_entity_links
                   SET target_entity_id = ?
                   WHERE target_entity_id = ?
                     AND NOT EXISTS (
                         SELECT 1 FROM collection_entity_links dup
                         WHERE dup.collection_id = collection_entity_links.collection_id
                           AND dup.source_entity_id = collection_entity_links.source_entity_id
                           AND dup.target_entity_id = ?
                     )""",
                (to_entity_id, from_entity_id, to_entity_id),
            )
            # Limpiar filas huérfanas que no se pudieron mover (duplicados)
            conn.execute(
                "DELETE FROM collection_entity_links WHERE source_entity_id = ? OR target_entity_id = ?",
                (from_entity_id, from_entity_id),
            )
            # Limpiar self-links creados por la fusión
            c = conn.execute(
                "DELETE FROM collection_entity_links WHERE source_entity_id = target_entity_id",
            )
            counts["collection_entity_links"] = (
                c.rowcount
            )  # solo self-links eliminados contados

            # 15. scene_tags: location_entity_id
            c = conn.execute(
                "UPDATE scene_tags SET location_entity_id = ? WHERE location_entity_id = ?",
                (to_entity_id, from_entity_id),
            )
            counts["scene_tags_location"] = c.rowcount

            # 16. scene_tags: participant_ids (JSON array)
            #     Usa json_each para matching exacto, con fallback LIKE + filtro Python
            try:
                rows = conn.execute(
                    """SELECT id, participant_ids FROM scene_tags
                       WHERE EXISTS (
                           SELECT 1 FROM json_each(participant_ids)
                           WHERE CAST(value AS INTEGER) = ?
                       )""",
                    (from_entity_id,),
                ).fetchall()
            except Exception:
                rows = conn.execute(
                    "SELECT id, participant_ids FROM scene_tags WHERE participant_ids LIKE ?",
                    (f"%{from_entity_id}%",),
                ).fetchall()
            scene_part_count = 0
            for row in rows:
                ids = json.loads(row["participant_ids"] or "[]")
                if from_entity_id in ids:
                    new_ids = [to_entity_id if x == from_entity_id else x for x in ids]
                    # Dedup preservando orden
                    seen: set[int] = set()
                    deduped: list[int] = []
                    for x in new_ids:
                        if x not in seen:
                            seen.add(x)
                            deduped.append(x)
                    conn.execute(
                        "UPDATE scene_tags SET participant_ids = ? WHERE id = ?",
                        (json.dumps(deduped), row["id"]),
                    )
                    scene_part_count += 1
            counts["scene_tags_participants"] = scene_part_count

            # 17. project_detector_weights: merge per-entity adaptive weights
            #     Keyed on canonical_name, so we need both entity names
            from_name_row = conn.execute(
                "SELECT canonical_name, project_id FROM entities WHERE id = ?",
                (from_entity_id,),
            ).fetchone()
            to_name_row = conn.execute(
                "SELECT canonical_name FROM entities WHERE id = ?",
                (to_entity_id,),
            ).fetchone()
            weight_merge_count = 0
            if from_name_row and to_name_row:
                from_norm = from_name_row["canonical_name"].strip().lower()
                to_norm = to_name_row["canonical_name"].strip().lower()
                pid = from_name_row["project_id"]
                if from_norm and to_norm and from_norm != to_norm:
                    # Get source weights
                    src_rows = conn.execute(
                        "SELECT alert_type, weight, feedback_count, dismiss_count, confirm_count "
                        "FROM project_detector_weights "
                        "WHERE project_id = ? AND entity_canonical_name = ?",
                        (pid, from_norm),
                    ).fetchall()
                    for sr in src_rows:
                        at = sr["alert_type"]
                        # Check if target already has weight for this alert_type
                        tgt = conn.execute(
                            "SELECT weight, feedback_count, dismiss_count, confirm_count "
                            "FROM project_detector_weights "
                            "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ?",
                            (pid, at, to_norm),
                        ).fetchone()
                        if tgt:
                            # Weighted average
                            sc, tc = sr["feedback_count"], tgt["feedback_count"]
                            total = max(sc + tc, 1)
                            merged_w = round((sr["weight"] * sc + tgt["weight"] * tc) / total, 4)
                            conn.execute(
                                "UPDATE project_detector_weights "
                                "SET weight = ?, feedback_count = ?, dismiss_count = ?, "
                                "confirm_count = ?, updated_at = datetime('now') "
                                "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ?",
                                (merged_w, sc + tc, sr["dismiss_count"] + tgt["dismiss_count"],
                                 sr["confirm_count"] + tgt["confirm_count"], pid, at, to_norm),
                            )
                        else:
                            # Transfer source weight to target name
                            conn.execute(
                                "UPDATE project_detector_weights "
                                "SET entity_canonical_name = ? "
                                "WHERE project_id = ? AND alert_type = ? AND entity_canonical_name = ?",
                                (to_norm, pid, at, from_norm),
                            )
                        weight_merge_count += 1
                    # Clean up any remaining source weights (from merged rows)
                    conn.execute(
                        "DELETE FROM project_detector_weights "
                        "WHERE project_id = ? AND entity_canonical_name = ?",
                        (pid, from_norm),
                    )
            counts["detector_weights"] = weight_merge_count

        logger.debug(f"move_related_data({from_entity_id} → {to_entity_id}): {counts}")
        return counts

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
            result.append(
                {
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
                }
            )

        # Enriquecer cada atributo con la lista de capítulos donde aparece
        # (desde attribute_evidences, no solo desde source_mention)
        if result:
            attr_ids = [a["id"] for a in result]
            placeholders = ",".join("?" * len(attr_ids))
            evidence_rows = self.db.fetchall(
                f"""
                SELECT attribute_id, chapter
                FROM attribute_evidences
                WHERE attribute_id IN ({placeholders})
                  AND chapter IS NOT NULL
                ORDER BY attribute_id, chapter
                """,
                tuple(attr_ids),
            )

            # Agrupar capítulos por attribute_id
            chapters_by_attr: dict[int, list[int]] = {}
            for ev_row in evidence_rows:
                attr_id = ev_row["attribute_id"]
                ch = ev_row["chapter"]
                if attr_id not in chapters_by_attr:
                    chapters_by_attr[attr_id] = []
                if ch not in chapters_by_attr[attr_id]:
                    chapters_by_attr[attr_id].append(ch)

            for attr in result:
                evidence_chapters = chapters_by_attr.get(attr["id"], [])
                # Usar evidencias si existen, sino el capítulo de source_mention
                if evidence_chapters:
                    attr["chapters"] = sorted(evidence_chapters)
                elif attr["chapter"] is not None:
                    attr["chapters"] = [attr["chapter"]]
                else:
                    attr["chapters"] = []
                attr["firstMentionChapter"] = (
                    attr["chapters"][0] if attr["chapters"] else attr["chapter"]
                )

        return result

    def update_attribute(
        self,
        attribute_id: int,
        attribute_key: str | None = None,
        attribute_value: str | None = None,
        is_verified: bool | None = None,
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
            result.append(
                {
                    "attribute_id": row["attribute_id"],
                    "entity_id": row["entity_id"],
                    "entity_name": row["entity_name"],
                    "attribute_type": row["attribute_type"],
                    "attribute_key": row["attribute_key"],
                    "attribute_value": row["attribute_value"],
                    "confidence": row["confidence"],
                    "source_mention_id": row["source_mention_id"],
                    "created_at": row["created_at"],
                }
            )

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
        note: str | None = None,
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
        old_value = json.dumps(
            {
                "source_entity_ids": source_entity_ids,
                "source_snapshots": source_snapshots,
                "canonical_names_before": canonical_names_before,
            }
        )
        new_value = json.dumps(
            {
                "result_entity_id": result_entity_id,
                "merged_by": merged_by,
            }
        )

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

    def merge_entities_atomic(
        self,
        project_id: int,
        primary_entity_id: int,
        source_entities: list[dict],
        combined_aliases: list[str],
        new_merged_ids: list[int],
        total_mention_delta: int,
        merged_by: str = "user",
    ) -> int:
        """
        Fusiona varias entidades en una sola de forma atómica.

        Todas las operaciones de escritura (mover menciones, mover atributos,
        desactivar fuentes, actualizar primaria, historial) se ejecutan en una
        única transacción. Si alguna falla, se hace rollback completo.

        Args:
            project_id: ID del proyecto
            primary_entity_id: ID de la entidad destino
            source_entities: Lista de dicts con datos de las entidades a fusionar:
                [{"id": int, "canonical_name": str, "entity_type": str,
                  "aliases": list, "mention_count": int}, ...]
            combined_aliases: Lista final de aliases para la entidad primaria
            new_merged_ids: Lista acumulada de IDs fusionados
            total_mention_delta: Incremento total de menciones
            merged_by: Quién realizó la fusión

        Returns:
            Número de entidades fusionadas
        """
        if not source_entities:
            return 0

        merged_count = 0
        source_entity_ids = [e["id"] for e in source_entities]
        canonical_names_before = [e["canonical_name"] for e in source_entities]

        with self.db.transaction() as conn:
            for src in source_entities:
                eid = src["id"]

                # 1. Mover menciones
                conn.execute(
                    "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?",
                    (primary_entity_id, eid),
                )

                # 2. Mover atributos
                conn.execute(
                    "UPDATE entity_attributes SET entity_id = ? WHERE entity_id = ?",
                    (primary_entity_id, eid),
                )

                # 3. Mover datos relacionados (FK en otras tablas)
                conn.execute(
                    "UPDATE temporal_markers SET entity_id = ? WHERE entity_id = ?",
                    (primary_entity_id, eid),
                )
                # voice_profiles: mover si no existe destino, si no eliminar
                existing = conn.execute(
                    "SELECT 1 FROM voice_profiles WHERE entity_id = ?",
                    (primary_entity_id,),
                ).fetchone()
                if existing:
                    conn.execute(
                        "DELETE FROM voice_profiles WHERE entity_id = ?", (eid,)
                    )
                else:
                    conn.execute(
                        "UPDATE voice_profiles SET entity_id = ? WHERE entity_id = ?",
                        (primary_entity_id, eid),
                    )

                # 4. Soft-delete la entidad fuente
                conn.execute(
                    "UPDATE entities SET is_active = 0, updated_at = datetime('now') WHERE id = ?",
                    (eid,),
                )

                merged_count += 1

            # 5. Actualizar aliases y merged_from_ids en la entidad primaria
            merged_data = json.dumps(
                {"aliases": combined_aliases, "merged_ids": new_merged_ids}
            )
            conn.execute(
                "UPDATE entities SET merged_from_ids = ?, updated_at = datetime('now') WHERE id = ?",
                (merged_data, primary_entity_id),
            )

            # 6. Incrementar mention_count
            if total_mention_delta > 0:
                conn.execute(
                    "UPDATE entities SET mention_count = mention_count + ? WHERE id = ?",
                    (total_mention_delta, primary_entity_id),
                )

            # 7. Registrar en historial
            old_value = json.dumps(
                {
                    "source_entity_ids": source_entity_ids,
                    "source_snapshots": source_entities,
                    "canonical_names_before": canonical_names_before,
                }
            )
            new_value = json.dumps(
                {"result_entity_id": primary_entity_id, "merged_by": merged_by}
            )
            note = f"Fusión de {merged_count} entidades en entidad {primary_entity_id}"
            conn.execute(
                """INSERT INTO review_history (
                    project_id, action_type, target_type, target_id,
                    old_value_json, new_value_json, note
                ) VALUES (?, 'entity_merged', 'entity', ?, ?, ?, ?)""",
                (project_id, primary_entity_id, old_value, new_value, note),
            )

        logger.info(
            f"Atomic merge: {merged_count} entities into {primary_entity_id} "
            f"for project {project_id}"
        )
        return merged_count

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
            old_data = (
                json.loads(row["old_value_json"]) if row["old_value_json"] else {}
            )
            new_data = (
                json.loads(row["new_value_json"]) if row["new_value_json"] else {}
            )

            history.append(
                MergeHistory(
                    id=row["id"],
                    project_id=row["project_id"],
                    result_entity_id=new_data.get("result_entity_id", row["target_id"]),
                    source_entity_ids=old_data.get("source_entity_ids", []),
                    source_snapshots=old_data.get("source_snapshots", []),
                    canonical_name_before=old_data.get("canonical_names_before", []),
                    merged_at=(
                        datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None
                    ),
                    merged_by=new_data.get("merged_by", "user"),
                    undone_at=(
                        datetime.fromisoformat(row["undone_at"])
                        if dict(row).get("undone_at")
                        else None
                    ),
                    note=row["note"],
                )
            )

        return history

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
            pattern = f"%{name}%"
            try:
                sql = """
                    SELECT DISTINCT e.* FROM entities e
                    LEFT JOIN json_each(json_extract(e.merged_from_ids, '$.aliases')) a
                    WHERE e.project_id = ? AND e.is_active = 1
                    AND (
                        e.canonical_name LIKE ?
                        OR LOWER(CAST(a.value AS TEXT)) LIKE LOWER(?)
                    )
                """
                rows = self.db.fetchall(sql, (project_id, pattern, pattern))
            except Exception:
                logger.debug("json_each no disponible; usando fallback LIKE en merged_from_ids")
                sql = """
                    SELECT * FROM entities
                    WHERE project_id = ? AND is_active = 1
                    AND (canonical_name LIKE ? OR merged_from_ids LIKE ?)
                """
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
_entity_repository: EntityRepository | None = None


def get_entity_repository(database: Database | None = None) -> EntityRepository:
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
