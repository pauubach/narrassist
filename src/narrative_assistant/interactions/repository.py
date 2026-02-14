"""
Persistencia de interacciones entre entidades.

Almacena:
- Interacciones detectadas
- Patrones calculados
- Alertas generadas
"""

import json
import logging
from datetime import datetime

from ..persistence.database import Database
from .models import (
    EntityInteraction,
    InteractionAlert,
    InteractionPattern,
    InteractionTone,
    InteractionType,
)

logger = logging.getLogger(__name__)

# SQL para crear tablas de interacciones
INTERACTIONS_SCHEMA = """
-- Interacciones entre entidades
CREATE TABLE IF NOT EXISTS entity_interactions (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,

    -- Participantes
    initiator_id TEXT NOT NULL DEFAULT '',
    receiver_id TEXT NOT NULL DEFAULT '',
    initiator_name TEXT NOT NULL,
    receiver_name TEXT NOT NULL,

    -- Clasificación
    interaction_type TEXT NOT NULL,
    tone TEXT NOT NULL,

    -- Ubicación
    chapter INTEGER NOT NULL DEFAULT 0,
    scene_index INTEGER,
    text_excerpt TEXT NOT NULL,
    start_char INTEGER NOT NULL DEFAULT 0,
    end_char INTEGER NOT NULL DEFAULT 0,

    -- Análisis
    sentiment_score REAL DEFAULT 0.0,
    intensity REAL DEFAULT 0.5,

    -- Coherencia
    relationship_id TEXT,
    expected_tone TEXT,
    is_coherent INTEGER DEFAULT 1,
    coherence_note TEXT DEFAULT '',

    -- Metadatos
    confidence REAL DEFAULT 0.5,
    detection_method TEXT DEFAULT 'pattern',
    user_marked_intentional INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interactions_project ON entity_interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_interactions_initiator ON entity_interactions(initiator_name);
CREATE INDEX IF NOT EXISTS idx_interactions_receiver ON entity_interactions(receiver_name);
CREATE INDEX IF NOT EXISTS idx_interactions_chapter ON entity_interactions(chapter);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON entity_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_coherent ON entity_interactions(is_coherent);

-- Patrones de interacción (cache para evitar recalcular)
CREATE TABLE IF NOT EXISTS interaction_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity1_name TEXT NOT NULL,
    entity2_name TEXT NOT NULL,

    -- Estadísticas
    total_interactions INTEGER DEFAULT 0,
    interactions_by_type TEXT DEFAULT '{}',
    interactions_by_tone TEXT DEFAULT '{}',

    -- Tono
    average_tone TEXT DEFAULT 'neutral',
    average_sentiment_score REAL DEFAULT 0.0,
    tone_variance REAL DEFAULT 0.0,
    tone_trend TEXT DEFAULT 'stable',

    -- Temporal
    first_interaction_chapter INTEGER,
    last_interaction_chapter INTEGER,

    -- Asimetría
    initiations_by_entity1 INTEGER DEFAULT 0,
    initiations_by_entity2 INTEGER DEFAULT 0,
    asymmetry_ratio REAL DEFAULT 0.5,

    -- Flags
    has_sudden_changes INTEGER DEFAULT 0,
    has_tone_mismatch INTEGER DEFAULT 0,

    -- Metadatos
    calculated_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, entity1_name, entity2_name)
);

CREATE INDEX IF NOT EXISTS idx_patterns_project ON interaction_patterns(project_id);

-- Alertas de interacción
CREATE TABLE IF NOT EXISTS interaction_alerts (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,

    -- Clasificación
    code TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',

    -- Entidades
    entity1_name TEXT NOT NULL,
    entity2_name TEXT NOT NULL,
    relationship_type TEXT DEFAULT '',

    -- Interacción
    interaction_id TEXT,
    chapter INTEGER DEFAULT 0,
    text_excerpt TEXT DEFAULT '',

    -- Tono
    detected_tone TEXT DEFAULT '',
    expected_tones TEXT DEFAULT '[]',

    -- Explicación
    explanation TEXT NOT NULL,
    suggestion TEXT DEFAULT '',

    -- Estado
    status TEXT DEFAULT 'new',
    resolved_at TEXT,
    resolution_note TEXT DEFAULT '',

    -- Metadatos
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (interaction_id) REFERENCES entity_interactions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_int_alerts_project ON interaction_alerts(project_id);
CREATE INDEX IF NOT EXISTS idx_int_alerts_status ON interaction_alerts(status);
CREATE INDEX IF NOT EXISTS idx_int_alerts_code ON interaction_alerts(code);
"""


class InteractionRepository:
    """
    Repositorio para persistencia de interacciones.

    Gestiona interacciones, patrones y alertas.
    """

    def __init__(self, db: Database | None = None):
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
            conn.executescript(INTERACTIONS_SCHEMA)
            conn.commit()  # Explicit commit to ensure visibility across connections
            logger.debug("Schema de interacciones inicializado")

    # ==================== Interactions ====================

    def save_interaction(self, interaction: EntityInteraction) -> str:
        """
        Guarda una interacción.

        Args:
            interaction: Interacción a guardar

        Returns:
            ID de la interacción guardada
        """
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_interactions (
                    id, project_id,
                    initiator_id, receiver_id,
                    initiator_name, receiver_name,
                    interaction_type, tone,
                    chapter, scene_index,
                    text_excerpt, start_char, end_char,
                    sentiment_score, intensity,
                    relationship_id, expected_tone,
                    is_coherent, coherence_note,
                    confidence, detection_method,
                    user_marked_intentional, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.id,
                    interaction.project_id,
                    interaction.initiator_id,
                    interaction.receiver_id,
                    interaction.initiator_name,
                    interaction.receiver_name,
                    interaction.interaction_type.value,
                    interaction.tone.value,
                    interaction.chapter,
                    interaction.scene_index,
                    interaction.text_excerpt,
                    interaction.start_char,
                    interaction.end_char,
                    interaction.sentiment_score,
                    interaction.intensity,
                    interaction.relationship_id,
                    interaction.expected_tone.value if interaction.expected_tone else None,
                    1 if interaction.is_coherent else 0,
                    interaction.coherence_note,
                    interaction.confidence,
                    interaction.detection_method,
                    1 if interaction.user_marked_intentional else 0,
                    interaction.created_at.isoformat(),
                ),
            )

        return interaction.id

    def get_interaction(self, interaction_id: str) -> EntityInteraction | None:
        """Obtiene una interacción por ID."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM entity_interactions WHERE id = ?",
                (interaction_id,),
            ).fetchone()

        if not row:
            return None

        return self._row_to_interaction(row)

    def get_interactions_for_project(
        self,
        project_id: int,
        chapter: int | None = None,
        incoherent_only: bool = False,
    ) -> list[EntityInteraction]:
        """
        Obtiene interacciones de un proyecto.

        Args:
            project_id: ID del proyecto
            chapter: Filtrar por capítulo (opcional)
            incoherent_only: Solo interacciones incoherentes

        Returns:
            Lista de interacciones
        """
        query = "SELECT * FROM entity_interactions WHERE project_id = ?"
        params = [project_id]

        if chapter is not None:
            query += " AND chapter = ?"
            params.append(chapter)

        if incoherent_only:
            query += " AND is_coherent = 0"

        query += " ORDER BY chapter, start_char"

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_interaction(row) for row in rows]

    def get_interactions_between(
        self,
        project_id: int,
        entity1_name: str,
        entity2_name: str,
    ) -> list[EntityInteraction]:
        """
        Obtiene interacciones entre dos entidades específicas.

        Args:
            project_id: ID del proyecto
            entity1_name: Nombre de primera entidad
            entity2_name: Nombre de segunda entidad

        Returns:
            Lista de interacciones entre ellas
        """
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM entity_interactions
                WHERE project_id = ?
                  AND ((initiator_name = ? AND receiver_name = ?)
                       OR (initiator_name = ? AND receiver_name = ?))
                ORDER BY chapter, start_char
                """,
                (project_id, entity1_name, entity2_name, entity2_name, entity1_name),
            ).fetchall()

        return [self._row_to_interaction(row) for row in rows]

    def mark_as_intentional(self, interaction_id: str) -> bool:
        """Marca una interacción incoherente como intencional."""
        with self.db.connection() as conn:
            result = conn.execute(
                """
                UPDATE entity_interactions
                SET user_marked_intentional = 1
                WHERE id = ?
                """,
                (interaction_id,),
            )
        return result.rowcount > 0

    def save_interactions_batch(
        self,
        interactions: list[EntityInteraction],
    ) -> int:
        """
        Guarda múltiples interacciones de forma eficiente.

        Returns:
            Número de interacciones guardadas
        """
        count = 0
        with self.db.connection() as conn:
            for interaction in interactions:
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO entity_interactions (
                            id, project_id,
                            initiator_id, receiver_id,
                            initiator_name, receiver_name,
                            interaction_type, tone,
                            chapter, scene_index,
                            text_excerpt, start_char, end_char,
                            sentiment_score, intensity,
                            relationship_id, expected_tone,
                            is_coherent, coherence_note,
                            confidence, detection_method,
                            user_marked_intentional, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            interaction.id,
                            interaction.project_id,
                            interaction.initiator_id,
                            interaction.receiver_id,
                            interaction.initiator_name,
                            interaction.receiver_name,
                            interaction.interaction_type.value,
                            interaction.tone.value,
                            interaction.chapter,
                            interaction.scene_index,
                            interaction.text_excerpt,
                            interaction.start_char,
                            interaction.end_char,
                            interaction.sentiment_score,
                            interaction.intensity,
                            interaction.relationship_id,
                            interaction.expected_tone.value if interaction.expected_tone else None,
                            1 if interaction.is_coherent else 0,
                            interaction.coherence_note,
                            interaction.confidence,
                            interaction.detection_method,
                            1 if interaction.user_marked_intentional else 0,
                            interaction.created_at.isoformat(),
                        ),
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Error guardando interacción {interaction.id}: {e}")

        logger.info(f"Guardadas {count} interacciones en batch")
        return count

    def _row_to_interaction(self, row) -> EntityInteraction:
        """Convierte una fila de BD a EntityInteraction."""
        return EntityInteraction(
            id=row["id"],
            project_id=row["project_id"],
            initiator_id=row["initiator_id"] or "",
            receiver_id=row["receiver_id"] or "",
            initiator_name=row["initiator_name"],
            receiver_name=row["receiver_name"],
            interaction_type=InteractionType(row["interaction_type"]),
            tone=InteractionTone(row["tone"]),
            chapter=row["chapter"],
            scene_index=row["scene_index"],
            text_excerpt=row["text_excerpt"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            sentiment_score=row["sentiment_score"] or 0.0,
            intensity=row["intensity"] or 0.5,
            relationship_id=row["relationship_id"],
            expected_tone=(InteractionTone(row["expected_tone"]) if row["expected_tone"] else None),
            is_coherent=bool(row["is_coherent"]),
            coherence_note=row["coherence_note"] or "",
            confidence=row["confidence"] or 0.5,
            detection_method=row["detection_method"] or "pattern",
            created_at=datetime.fromisoformat(row["created_at"]),
            user_marked_intentional=bool(row["user_marked_intentional"]),
        )

    # ==================== Patterns ====================

    def save_pattern(self, project_id: int, pattern: InteractionPattern) -> None:
        """
        Guarda o actualiza un patrón de interacción.

        Args:
            project_id: ID del proyecto
            pattern: Patrón a guardar
        """
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO interaction_patterns (
                    project_id, entity1_name, entity2_name,
                    total_interactions, interactions_by_type, interactions_by_tone,
                    average_tone, average_sentiment_score, tone_variance, tone_trend,
                    first_interaction_chapter, last_interaction_chapter,
                    initiations_by_entity1, initiations_by_entity2, asymmetry_ratio,
                    has_sudden_changes, has_tone_mismatch, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    pattern.entity1_name,
                    pattern.entity2_name,
                    pattern.total_interactions,
                    json.dumps(pattern.interactions_by_type),
                    json.dumps(pattern.interactions_by_tone),
                    pattern.average_tone.value,
                    pattern.average_sentiment_score,
                    pattern.tone_variance,
                    pattern.tone_trend,
                    pattern.first_interaction_chapter,
                    pattern.last_interaction_chapter,
                    pattern.initiations_by_entity1,
                    pattern.initiations_by_entity2,
                    pattern.asymmetry_ratio,
                    1 if pattern.has_sudden_changes else 0,
                    1 if pattern.has_tone_mismatch else 0,
                    datetime.now().isoformat(),
                ),
            )

    def get_patterns_for_project(
        self,
        project_id: int,
    ) -> list[InteractionPattern]:
        """Obtiene todos los patrones de un proyecto."""
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM interaction_patterns WHERE project_id = ?",
                (project_id,),
            ).fetchall()

        return [self._row_to_pattern(row) for row in rows]

    def _row_to_pattern(self, row) -> InteractionPattern:
        """Convierte una fila de BD a InteractionPattern."""
        return InteractionPattern(
            entity1_name=row["entity1_name"],
            entity2_name=row["entity2_name"],
            total_interactions=row["total_interactions"],
            interactions_by_type=json.loads(row["interactions_by_type"] or "{}"),
            interactions_by_tone=json.loads(row["interactions_by_tone"] or "{}"),
            average_tone=InteractionTone(row["average_tone"]),
            average_sentiment_score=row["average_sentiment_score"] or 0.0,
            tone_variance=row["tone_variance"] or 0.0,
            tone_trend=row["tone_trend"] or "stable",
            first_interaction_chapter=row["first_interaction_chapter"] or 0,
            last_interaction_chapter=row["last_interaction_chapter"] or 0,
            initiations_by_entity1=row["initiations_by_entity1"] or 0,
            initiations_by_entity2=row["initiations_by_entity2"] or 0,
            asymmetry_ratio=row["asymmetry_ratio"] or 0.5,
            has_sudden_changes=bool(row["has_sudden_changes"]),
            has_tone_mismatch=bool(row["has_tone_mismatch"]),
        )

    # ==================== Alerts ====================

    def save_alert(self, project_id: int, alert: InteractionAlert) -> str:
        """
        Guarda una alerta de interacción.

        Returns:
            ID de la alerta guardada
        """
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO interaction_alerts (
                    id, project_id, code, alert_type, severity,
                    entity1_name, entity2_name, relationship_type,
                    interaction_id, chapter, text_excerpt,
                    detected_tone, expected_tones,
                    explanation, suggestion,
                    confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.id,
                    project_id,
                    alert.code,
                    alert.alert_type,
                    alert.severity,
                    alert.entity1_name,
                    alert.entity2_name,
                    alert.relationship_type,
                    alert.interaction_id,
                    alert.chapter,
                    alert.text_excerpt,
                    alert.detected_tone,
                    json.dumps(alert.expected_tones),
                    alert.explanation,
                    alert.suggestion,
                    alert.confidence,
                    alert.created_at.isoformat(),
                ),
            )

        return alert.id

    def get_alerts_for_project(
        self,
        project_id: int,
        status: str | None = None,
    ) -> list[InteractionAlert]:
        """
        Obtiene alertas de un proyecto.

        Args:
            project_id: ID del proyecto
            status: Filtrar por estado (optional)

        Returns:
            Lista de alertas
        """
        query = "SELECT * FROM interaction_alerts WHERE project_id = ?"
        params = [project_id]

        if status:
            query += " AND status = ?"
            params.append(status)  # type: ignore[arg-type]

        query += " ORDER BY created_at DESC"

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_alert(row) for row in rows]

    def _row_to_alert(self, row) -> InteractionAlert:
        """Convierte una fila de BD a InteractionAlert."""
        return InteractionAlert(
            id=row["id"],
            code=row["code"],
            alert_type=row["alert_type"],
            severity=row["severity"],
            entity1_name=row["entity1_name"],
            entity2_name=row["entity2_name"],
            relationship_type=row["relationship_type"] or "",
            interaction_id=row["interaction_id"],
            chapter=row["chapter"] or 0,
            text_excerpt=row["text_excerpt"] or "",
            detected_tone=row["detected_tone"] or "",
            expected_tones=json.loads(row["expected_tones"] or "[]"),
            explanation=row["explanation"],
            suggestion=row["suggestion"] or "",
            confidence=row["confidence"] or 0.5,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ==================== Statistics ====================

    def get_interaction_stats(self, project_id: int) -> dict:
        """Obtiene estadísticas de interacciones para un proyecto."""
        with self.db.connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as count FROM entity_interactions WHERE project_id = ?",
                (project_id,),
            ).fetchone()["count"]

            by_type = conn.execute(
                """
                SELECT interaction_type, COUNT(*) as count
                FROM entity_interactions
                WHERE project_id = ?
                GROUP BY interaction_type
                """,
                (project_id,),
            ).fetchall()

            by_tone = conn.execute(
                """
                SELECT tone, COUNT(*) as count
                FROM entity_interactions
                WHERE project_id = ?
                GROUP BY tone
                """,
                (project_id,),
            ).fetchall()

            incoherent = conn.execute(
                """
                SELECT COUNT(*) as count FROM entity_interactions
                WHERE project_id = ? AND is_coherent = 0
                """,
                (project_id,),
            ).fetchone()["count"]

        return {
            "total": total,
            "by_type": {row["interaction_type"]: row["count"] for row in by_type},
            "by_tone": {row["tone"]: row["count"] for row in by_tone},
            "incoherent": incoherent,
            "coherent": total - incoherent,
        }
