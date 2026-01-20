"""
Persistencia de relaciones entre entidades.

Almacena:
- Tipos de relación (templates con expectativas)
- Instancias de relaciones entre entidades
- Evidencias textuales
- Cambios en relaciones
"""

import json
import logging
from datetime import datetime
from typing import Optional

from ..persistence.database import Database
from .models import (
    EntityRelationship,
    InferredExpectations,
    RelationshipChange,
    RelationshipEvidence,
    RelationshipType,
    RelationType,
    RelationCategory,
    RelationValence,
    TextReference,
)

logger = logging.getLogger(__name__)

# SQL para crear tablas de relaciones
RELATIONSHIPS_SCHEMA = """
-- Tipos de relación (templates)
CREATE TABLE IF NOT EXISTS relationship_types (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    relation_type TEXT NOT NULL,
    category TEXT NOT NULL,
    source_entity_types TEXT NOT NULL DEFAULT '["PERSON"]',
    target_entity_types TEXT NOT NULL DEFAULT '["PERSON"]',
    default_valence INTEGER DEFAULT 0,
    is_bidirectional INTEGER DEFAULT 0,
    inverse_type_id TEXT,
    expected_behaviors TEXT DEFAULT '[]',
    forbidden_behaviors TEXT DEFAULT '[]',
    expected_consequences TEXT DEFAULT '[]',
    inference_reasoning TEXT DEFAULT '',
    inference_source TEXT DEFAULT 'rule_based',
    expectations_confidence REAL DEFAULT 0.0,
    extraction_source TEXT DEFAULT 'pattern',
    confidence REAL DEFAULT 0.5,
    user_confirmed INTEGER DEFAULT 0,
    user_rejected INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (inverse_type_id) REFERENCES relationship_types(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_types_project ON relationship_types(project_id);
CREATE INDEX IF NOT EXISTS idx_rel_types_name ON relationship_types(name);

-- Instancias de relaciones entre entidades
CREATE TABLE IF NOT EXISTS entity_relationships (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    relationship_type_id TEXT,
    relation_type TEXT NOT NULL,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    source_entity_name TEXT NOT NULL,
    target_entity_name TEXT NOT NULL,
    bidirectional INTEGER DEFAULT 0,
    intensity REAL DEFAULT 0.5,
    sentiment REAL DEFAULT 0.0,
    first_mention_chapter INTEGER,
    last_mention_chapter INTEGER,
    is_active INTEGER DEFAULT 1,
    evidence_texts TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    expectations_json TEXT,
    user_confirmed INTEGER DEFAULT 0,
    user_rejected INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (relationship_type_id) REFERENCES relationship_types(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_rels_project ON entity_relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_rels_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_rels_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_rels_type ON entity_relationships(relation_type);
CREATE INDEX IF NOT EXISTS idx_rels_active ON entity_relationships(is_active);

-- Evidencias textuales de relaciones
CREATE TABLE IF NOT EXISTS relationship_evidence (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    text TEXT NOT NULL,
    behavior_type TEXT DEFAULT 'other',
    chapter INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (relationship_id) REFERENCES entity_relationships(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rel_evidence_rel ON relationship_evidence(relationship_id);
CREATE INDEX IF NOT EXISTS idx_rel_evidence_chapter ON relationship_evidence(chapter);

-- Cambios/evolución de relaciones
CREATE TABLE IF NOT EXISTS relationship_changes (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    change_type TEXT NOT NULL,
    old_relation_type TEXT,
    new_relation_type TEXT,
    old_intensity REAL,
    new_intensity REAL,
    trigger_text TEXT,
    ref_chapter INTEGER,
    ref_char_start INTEGER,
    ref_char_end INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (relationship_id) REFERENCES entity_relationships(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rel_changes_rel ON relationship_changes(relationship_id);
CREATE INDEX IF NOT EXISTS idx_rel_changes_chapter ON relationship_changes(chapter);
"""


class RelationshipRepository:
    """
    Repositorio para persistencia de relaciones.

    Gestiona tipos de relación, instancias, evidencias y cambios.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si None, crea una nueva.
        """
        self.db = db or Database()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Crea las tablas si no existen."""
        with self.db.connection() as conn:
            conn.executescript(RELATIONSHIPS_SCHEMA)
            logger.debug("Schema de relaciones inicializado")

    # ==================== Relationship Types ====================

    def create_relationship_type(self, rel_type: RelationshipType) -> str:
        """
        Crea un tipo de relación.

        Args:
            rel_type: Tipo de relación a crear

        Returns:
            ID del tipo creado
        """
        expectations = rel_type.expectations
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO relationship_types (
                    id, project_id, name, description,
                    relation_type, category,
                    source_entity_types, target_entity_types,
                    default_valence, is_bidirectional, inverse_type_id,
                    expected_behaviors, forbidden_behaviors, expected_consequences,
                    inference_reasoning, inference_source, expectations_confidence,
                    extraction_source, confidence, user_confirmed, user_rejected,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel_type.id,
                    rel_type.project_id,
                    rel_type.name,
                    rel_type.description,
                    rel_type.relation_type.value,
                    rel_type.category.value,
                    json.dumps(rel_type.source_entity_types),
                    json.dumps(rel_type.target_entity_types),
                    rel_type.default_valence.value,
                    1 if rel_type.is_bidirectional else 0,
                    rel_type.inverse_type_id,
                    json.dumps(expectations.expected_behaviors if expectations else []),
                    json.dumps(expectations.forbidden_behaviors if expectations else []),
                    json.dumps(expectations.expected_consequences if expectations else []),
                    expectations.reasoning if expectations else "",
                    expectations.inference_source if expectations else "rule_based",
                    expectations.confidence if expectations else 0.0,
                    rel_type.extraction_source,
                    rel_type.confidence,
                    1 if rel_type.user_confirmed else 0,
                    1 if rel_type.user_rejected else 0,
                    rel_type.created_at.isoformat(),
                ),
            )
        logger.debug(f"Tipo de relación creado: {rel_type.id}")
        return rel_type.id

    def get_relationship_type(self, type_id: str) -> Optional[RelationshipType]:
        """Obtiene un tipo de relación por ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM relationship_types WHERE id = ?",
                (type_id,),
            ).fetchone()

        if not row:
            return None

        return self._row_to_relationship_type(row)

    def get_relationship_types_for_project(
        self,
        project_id: int,
    ) -> list[RelationshipType]:
        """Obtiene todos los tipos de relación de un proyecto."""
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM relationship_types WHERE project_id = ?",
                (project_id,),
            ).fetchall()

        return [self._row_to_relationship_type(row) for row in rows]

    def _row_to_relationship_type(self, row) -> RelationshipType:
        """Convierte una fila de BD a RelationshipType."""
        expectations = None
        expected_behaviors = json.loads(row["expected_behaviors"] or "[]")
        if expected_behaviors or row["forbidden_behaviors"]:
            expectations = InferredExpectations(
                expected_behaviors=expected_behaviors,
                forbidden_behaviors=json.loads(row["forbidden_behaviors"] or "[]"),
                expected_consequences=json.loads(row["expected_consequences"] or "[]"),
                confidence=row["expectations_confidence"] or 0.0,
                reasoning=row["inference_reasoning"] or "",
                inference_source=row["inference_source"] or "rule_based",
            )

        return RelationshipType(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"] or "",
            relation_type=RelationType(row["relation_type"]),
            category=RelationCategory(row["category"]),
            source_entity_types=json.loads(row["source_entity_types"]),
            target_entity_types=json.loads(row["target_entity_types"]),
            default_valence=RelationValence(row["default_valence"]),
            is_bidirectional=bool(row["is_bidirectional"]),
            inverse_type_id=row["inverse_type_id"],
            expectations=expectations,
            created_at=datetime.fromisoformat(row["created_at"]),
            extraction_source=row["extraction_source"] or "pattern",
            confidence=row["confidence"] or 0.5,
            user_confirmed=bool(row["user_confirmed"]),
            user_rejected=bool(row["user_rejected"]),
        )

    # ==================== Entity Relationships ====================

    def create_relationship(self, rel: EntityRelationship) -> str:
        """
        Crea una relación entre entidades.

        Args:
            rel: Relación a crear

        Returns:
            ID de la relación creada
        """
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO entity_relationships (
                    id, project_id, relationship_type_id, relation_type,
                    source_entity_id, target_entity_id,
                    source_entity_name, target_entity_name,
                    bidirectional, intensity, sentiment,
                    first_mention_chapter, last_mention_chapter, is_active,
                    evidence_texts, confidence, expectations_json,
                    user_confirmed, user_rejected, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.id,
                    rel.project_id,
                    rel.relationship_type_id,
                    rel.relation_type.value,
                    rel.source_entity_id,
                    rel.target_entity_id,
                    rel.source_entity_name,
                    rel.target_entity_name,
                    1 if rel.bidirectional else 0,
                    rel.intensity,
                    rel.sentiment,
                    rel.first_mention_chapter,
                    rel.last_mention_chapter,
                    1 if rel.is_active else 0,
                    json.dumps(rel.evidence_texts),
                    rel.confidence,
                    json.dumps(rel.expectations.to_dict()) if rel.expectations else None,
                    1 if rel.user_confirmed else 0,
                    1 if rel.user_rejected else 0,
                    rel.created_at.isoformat(),
                ),
            )

            # Guardar evidencias
            for evidence in rel.evidence:
                evidence.relationship_id = rel.id
                self._save_evidence(conn, evidence)

        logger.debug(f"Relación creada: {rel.id}")
        return rel.id

    def _save_evidence(self, conn, evidence: RelationshipEvidence) -> None:
        """Guarda una evidencia de relación."""
        conn.execute(
            """
            INSERT INTO relationship_evidence (
                id, relationship_id, text, behavior_type,
                chapter, char_start, char_end, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.id,
                evidence.relationship_id,
                evidence.text,
                evidence.behavior_type,
                evidence.reference.chapter if evidence.reference else None,
                evidence.reference.char_start if evidence.reference else None,
                evidence.reference.char_end if evidence.reference else None,
                evidence.confidence,
                evidence.created_at.isoformat(),
            ),
        )

    def get_relationship(self, rel_id: str) -> Optional[EntityRelationship]:
        """Obtiene una relación por ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM entity_relationships WHERE id = ?",
                (rel_id,),
            ).fetchone()

            if not row:
                return None

            rel = self._row_to_relationship(row)

            # Cargar evidencias
            evidence_rows = conn.execute(
                "SELECT * FROM relationship_evidence WHERE relationship_id = ?",
                (rel_id,),
            ).fetchall()

            rel.evidence = [
                self._row_to_evidence(ev_row)
                for ev_row in evidence_rows
            ]

        return rel

    def get_relationships_for_entity(
        self,
        entity_id: str,
        include_as_target: bool = True,
    ) -> list[EntityRelationship]:
        """
        Obtiene relaciones donde la entidad participa.

        Args:
            entity_id: ID de la entidad
            include_as_target: Si incluir relaciones donde es target

        Returns:
            Lista de relaciones
        """
        with self.db.connection() as conn:
            if include_as_target:
                rows = conn.execute(
                    """
                    SELECT * FROM entity_relationships
                    WHERE source_entity_id = ? OR target_entity_id = ?
                    """,
                    (entity_id, entity_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM entity_relationships WHERE source_entity_id = ?",
                    (entity_id,),
                ).fetchall()

        return [self._row_to_relationship(row) for row in rows]

    def get_relationship_between(
        self,
        entity1_id: str,
        entity2_id: str,
    ) -> Optional[EntityRelationship]:
        """
        Obtiene la relación entre dos entidades específicas.

        Args:
            entity1_id: ID de primera entidad
            entity2_id: ID de segunda entidad

        Returns:
            Relación si existe, None si no
        """
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM entity_relationships
                WHERE (source_entity_id = ? AND target_entity_id = ?)
                   OR (source_entity_id = ? AND target_entity_id = ? AND bidirectional = 1)
                """,
                (entity1_id, entity2_id, entity2_id, entity1_id),
            ).fetchone()

        if not row:
            return None

        return self._row_to_relationship(row)

    def get_relationships_for_project(
        self,
        project_id: int,
        active_only: bool = True,
        confirmed_only: bool = False,
    ) -> list[EntityRelationship]:
        """
        Obtiene todas las relaciones de un proyecto.

        Args:
            project_id: ID del proyecto
            active_only: Solo relaciones activas
            confirmed_only: Solo confirmadas por usuario

        Returns:
            Lista de relaciones
        """
        query = "SELECT * FROM entity_relationships WHERE project_id = ?"
        params = [project_id]

        if active_only:
            query += " AND is_active = 1"
        if confirmed_only:
            query += " AND user_confirmed = 1"

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_relationship(row) for row in rows]

    def get_relationship_graph(
        self,
        project_id: int,
    ) -> dict[str, list[EntityRelationship]]:
        """
        Obtiene grafo de relaciones por entidad.

        Args:
            project_id: ID del proyecto

        Returns:
            Dict de entity_id -> lista de relaciones
        """
        relationships = self.get_relationships_for_project(project_id)
        graph: dict[str, list[EntityRelationship]] = {}

        for rel in relationships:
            if rel.source_entity_id not in graph:
                graph[rel.source_entity_id] = []
            graph[rel.source_entity_id].append(rel)

            # Si es bidireccional, añadir también en dirección inversa
            if rel.bidirectional:
                if rel.target_entity_id not in graph:
                    graph[rel.target_entity_id] = []
                graph[rel.target_entity_id].append(rel)

        return graph

    def update_relationship(self, rel: EntityRelationship) -> bool:
        """
        Actualiza una relación existente.

        Args:
            rel: Relación con datos actualizados

        Returns:
            True si se actualizó
        """
        with self.db.connection() as conn:
            result = conn.execute(
                """
                UPDATE entity_relationships SET
                    relation_type = ?,
                    bidirectional = ?,
                    intensity = ?,
                    sentiment = ?,
                    last_mention_chapter = ?,
                    is_active = ?,
                    evidence_texts = ?,
                    confidence = ?,
                    expectations_json = ?,
                    user_confirmed = ?,
                    user_rejected = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    rel.relation_type.value,
                    1 if rel.bidirectional else 0,
                    rel.intensity,
                    rel.sentiment,
                    rel.last_mention_chapter,
                    1 if rel.is_active else 0,
                    json.dumps(rel.evidence_texts),
                    rel.confidence,
                    json.dumps(rel.expectations.to_dict()) if rel.expectations else None,
                    1 if rel.user_confirmed else 0,
                    1 if rel.user_rejected else 0,
                    datetime.now().isoformat(),
                    rel.id,
                ),
            )

        return result.rowcount > 0

    def confirm_relationship(self, rel_id: str) -> bool:
        """Marca una relación como confirmada por el usuario."""
        with self.db.connection() as conn:
            result = conn.execute(
                """
                UPDATE entity_relationships
                SET user_confirmed = 1, user_rejected = 0, updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), rel_id),
            )
        return result.rowcount > 0

    def reject_relationship(self, rel_id: str) -> bool:
        """Marca una relación como rechazada por el usuario."""
        with self.db.connection() as conn:
            result = conn.execute(
                """
                UPDATE entity_relationships
                SET user_rejected = 1, user_confirmed = 0, updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), rel_id),
            )
        return result.rowcount > 0

    def delete_relationship(self, rel_id: str) -> bool:
        """Elimina una relación."""
        with self.db.connection() as conn:
            result = conn.execute(
                "DELETE FROM entity_relationships WHERE id = ?",
                (rel_id,),
            )
        return result.rowcount > 0

    def _row_to_relationship(self, row) -> EntityRelationship:
        """Convierte una fila de BD a EntityRelationship."""
        expectations = None
        if row["expectations_json"]:
            expectations = InferredExpectations.from_dict(
                json.loads(row["expectations_json"])
            )

        return EntityRelationship(
            id=row["id"],
            project_id=row["project_id"],
            source_entity_id=row["source_entity_id"],
            target_entity_id=row["target_entity_id"],
            source_entity_name=row["source_entity_name"],
            target_entity_name=row["target_entity_name"],
            relation_type=RelationType(row["relation_type"]),
            relationship_type_id=row["relationship_type_id"],
            bidirectional=bool(row["bidirectional"]),
            intensity=row["intensity"] or 0.5,
            sentiment=row["sentiment"] or 0.0,
            first_mention_chapter=row["first_mention_chapter"],
            last_mention_chapter=row["last_mention_chapter"],
            is_active=bool(row["is_active"]),
            evidence_texts=json.loads(row["evidence_texts"] or "[]"),
            confidence=row["confidence"] or 0.5,
            expectations=expectations,
            created_at=datetime.fromisoformat(row["created_at"]),
            user_confirmed=bool(row["user_confirmed"]),
            user_rejected=bool(row["user_rejected"]),
        )

    def _row_to_evidence(self, row) -> RelationshipEvidence:
        """Convierte una fila de BD a RelationshipEvidence."""
        reference = None
        if row["chapter"] is not None:
            reference = TextReference(
                chapter=row["chapter"],
                char_start=row["char_start"] or 0,
                char_end=row["char_end"] or 0,
            )

        return RelationshipEvidence(
            id=row["id"],
            relationship_id=row["relationship_id"],
            text=row["text"],
            reference=reference,
            behavior_type=row["behavior_type"] or "other",
            confidence=row["confidence"] or 0.5,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ==================== Relationship Changes ====================

    def add_relationship_change(self, change: RelationshipChange) -> str:
        """Registra un cambio en una relación."""
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO relationship_changes (
                    id, relationship_id, chapter, change_type,
                    old_relation_type, new_relation_type,
                    old_intensity, new_intensity,
                    trigger_text, ref_chapter, ref_char_start, ref_char_end,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change.id,
                    change.relationship_id,
                    change.chapter,
                    change.change_type,
                    change.old_relation_type.value if change.old_relation_type else None,
                    change.new_relation_type.value if change.new_relation_type else None,
                    change.old_intensity,
                    change.new_intensity,
                    change.trigger_text,
                    change.reference.chapter if change.reference else None,
                    change.reference.char_start if change.reference else None,
                    change.reference.char_end if change.reference else None,
                    change.notes,
                    change.created_at.isoformat(),
                ),
            )

        return change.id

    def get_changes_for_relationship(
        self,
        relationship_id: str,
    ) -> list[RelationshipChange]:
        """Obtiene el historial de cambios de una relación."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM relationship_changes
                WHERE relationship_id = ?
                ORDER BY chapter ASC
                """,
                (relationship_id,),
            ).fetchall()

        return [self._row_to_change(row) for row in rows]

    def _row_to_change(self, row) -> RelationshipChange:
        """Convierte una fila de BD a RelationshipChange."""
        reference = None
        if row["ref_chapter"] is not None:
            reference = TextReference(
                chapter=row["ref_chapter"],
                char_start=row["ref_char_start"] or 0,
                char_end=row["ref_char_end"] or 0,
            )

        return RelationshipChange(
            id=row["id"],
            relationship_id=row["relationship_id"],
            chapter=row["chapter"],
            change_type=row["change_type"],
            old_relation_type=(
                RelationType(row["old_relation_type"])
                if row["old_relation_type"] else None
            ),
            new_relation_type=(
                RelationType(row["new_relation_type"])
                if row["new_relation_type"] else None
            ),
            old_intensity=row["old_intensity"],
            new_intensity=row["new_intensity"],
            trigger_text=row["trigger_text"] or "",
            reference=reference,
            notes=row["notes"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ==================== Evidence ====================

    def add_evidence(self, evidence: RelationshipEvidence) -> str:
        """Añade evidencia a una relación existente."""
        with self.db.connection() as conn:
            self._save_evidence(conn, evidence)

            # Actualizar lista de textos en la relación
            rel = self.get_relationship(evidence.relationship_id)
            if rel:
                rel.evidence_texts.append(evidence.text)
                self.update_relationship(rel)

        return evidence.id

    def get_evidence_for_relationship(
        self,
        relationship_id: str,
    ) -> list[RelationshipEvidence]:
        """Obtiene todas las evidencias de una relación."""
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM relationship_evidence WHERE relationship_id = ?",
                (relationship_id,),
            ).fetchall()

        return [self._row_to_evidence(row) for row in rows]

    # ==================== Bulk Operations ====================

    def save_relationships_batch(
        self,
        relationships: list[EntityRelationship],
    ) -> int:
        """
        Guarda múltiples relaciones de forma eficiente.

        Args:
            relationships: Lista de relaciones a guardar

        Returns:
            Número de relaciones guardadas
        """
        count = 0
        with self.db.connection() as conn:
            for rel in relationships:
                try:
                    # Verificar si ya existe
                    existing = conn.execute(
                        """
                        SELECT id FROM entity_relationships
                        WHERE project_id = ?
                          AND source_entity_id = ?
                          AND target_entity_id = ?
                          AND relation_type = ?
                        """,
                        (
                            rel.project_id,
                            rel.source_entity_id,
                            rel.target_entity_id,
                            rel.relation_type.value,
                        ),
                    ).fetchone()

                    if existing:
                        # Actualizar existente
                        rel.id = existing["id"]
                        conn.execute(
                            """
                            UPDATE entity_relationships SET
                                confidence = MAX(confidence, ?),
                                last_mention_chapter = ?,
                                evidence_texts = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                rel.confidence,
                                rel.last_mention_chapter,
                                json.dumps(rel.evidence_texts),
                                datetime.now().isoformat(),
                                rel.id,
                            ),
                        )
                    else:
                        # Insertar nueva
                        conn.execute(
                            """
                            INSERT INTO entity_relationships (
                                id, project_id, relationship_type_id, relation_type,
                                source_entity_id, target_entity_id,
                                source_entity_name, target_entity_name,
                                bidirectional, intensity, sentiment,
                                first_mention_chapter, last_mention_chapter, is_active,
                                evidence_texts, confidence, user_confirmed, user_rejected,
                                created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                rel.id,
                                rel.project_id,
                                rel.relationship_type_id,
                                rel.relation_type.value,
                                rel.source_entity_id,
                                rel.target_entity_id,
                                rel.source_entity_name,
                                rel.target_entity_name,
                                1 if rel.bidirectional else 0,
                                rel.intensity,
                                rel.sentiment,
                                rel.first_mention_chapter,
                                rel.last_mention_chapter,
                                1 if rel.is_active else 0,
                                json.dumps(rel.evidence_texts),
                                rel.confidence,
                                0,
                                0,
                                rel.created_at.isoformat(),
                            ),
                        )
                    count += 1

                except Exception as e:
                    logger.warning(f"Error guardando relación {rel.id}: {e}")

        logger.info(f"Guardadas {count} relaciones en batch")
        return count

    # ==================== Statistics ====================

    def get_relationship_stats(self, project_id: int) -> dict:
        """Obtiene estadísticas de relaciones para un proyecto."""
        with self.db.connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as count FROM entity_relationships WHERE project_id = ?",
                (project_id,),
            ).fetchone()["count"]

            by_type = conn.execute(
                """
                SELECT relation_type, COUNT(*) as count
                FROM entity_relationships
                WHERE project_id = ?
                GROUP BY relation_type
                """,
                (project_id,),
            ).fetchall()

            confirmed = conn.execute(
                """
                SELECT COUNT(*) as count FROM entity_relationships
                WHERE project_id = ? AND user_confirmed = 1
                """,
                (project_id,),
            ).fetchone()["count"]

            rejected = conn.execute(
                """
                SELECT COUNT(*) as count FROM entity_relationships
                WHERE project_id = ? AND user_rejected = 1
                """,
                (project_id,),
            ).fetchone()["count"]

        return {
            "total": total,
            "by_type": {row["relation_type"]: row["count"] for row in by_type},
            "confirmed": confirmed,
            "rejected": rejected,
            "pending_review": total - confirmed - rejected,
        }
