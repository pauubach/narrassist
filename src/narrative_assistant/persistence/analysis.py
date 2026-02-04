"""
Persistencia de resultados de análisis.

Gestiona:
- Ejecuciones de análisis (analysis_runs)
- Fases ejecutadas (analysis_phases)
- Relaciones entre entidades (relationships)
- Interacciones (interactions)
- Cambios de registro (register_changes)
- Métricas de pacing (pacing_metrics)
- Arcos emocionales (emotional_arcs)
- Perfiles de voz (voice_profiles)
"""

import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .database import Database, get_database

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class AnalysisStatus(Enum):
    """Estados de una ejecución de análisis."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RelationType(Enum):
    """Tipos de relación entre entidades."""

    FAMILY = "FAMILY"
    ROMANTIC = "ROMANTIC"
    PROFESSIONAL = "PROFESSIONAL"
    FRIENDSHIP = "FRIENDSHIP"
    RIVALRY = "RIVALRY"
    HIERARCHICAL = "HIERARCHICAL"
    OTHER = "OTHER"


class InteractionType(Enum):
    """Tipos de interacción entre entidades."""

    DIALOGUE = "DIALOGUE"
    PHYSICAL = "PHYSICAL"
    THOUGHT = "THOUGHT"
    OBSERVATION = "OBSERVATION"
    REFERENCE = "REFERENCE"


class Tone(Enum):
    """Tono de una interacción."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class AnalysisRun:
    """Una ejecución de análisis."""

    id: int | None = None
    project_id: int = 0
    session_id: int | None = None
    config_json: str = ""
    quality_profile: str = "standard"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "running"
    error_message: str | None = None

    @classmethod
    def from_row(cls, row) -> "AnalysisRun":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            session_id=row["session_id"],
            config_json=row["config_json"] or "",
            quality_profile=row["quality_profile"] or "standard",
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            status=row["status"] or "running",
            error_message=row["error_message"],
        )


@dataclass
class AnalysisPhase:
    """Una fase dentro de una ejecución de análisis."""

    id: int | None = None
    run_id: int = 0
    phase_name: str = ""
    executed: bool = False
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_count: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row) -> "AnalysisPhase":
        """Crea desde fila de SQLite."""
        metadata = {}
        if row["metadata_json"]:
            with contextlib.suppress(json.JSONDecodeError):
                metadata = json.loads(row["metadata_json"])
        return cls(
            id=row["id"],
            run_id=row["run_id"],
            phase_name=row["phase_name"],
            executed=bool(row["executed"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            result_count=row["result_count"] or 0,
            error_message=row["error_message"],
            metadata=metadata,
        )


@dataclass
class Relationship:
    """Una relación entre dos entidades."""

    id: int | None = None
    project_id: int = 0
    entity1_id: int = 0
    entity2_id: int = 0
    relation_type: str = "OTHER"
    subtype: str | None = None
    direction: str = "bidirectional"
    confidence: float = 0.8
    chapter_id: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    source_text: str | None = None
    detection_method: str | None = None
    is_inferred: bool = False
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "Relationship":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            entity1_id=row["entity1_id"],
            entity2_id=row["entity2_id"],
            relation_type=row["relation_type"],
            subtype=row["subtype"],
            direction=row["direction"] or "bidirectional",
            confidence=row["confidence"] or 0.8,
            chapter_id=row["chapter_id"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            source_text=row["source_text"],
            detection_method=row["detection_method"],
            is_inferred=bool(row["is_inferred"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entity1_id": self.entity1_id,
            "entity2_id": self.entity2_id,
            "relation_type": self.relation_type,
            "subtype": self.subtype,
            "direction": self.direction,
            "confidence": self.confidence,
            "chapter_id": self.chapter_id,
            "source_text": self.source_text,
            "detection_method": self.detection_method,
            "is_inferred": self.is_inferred,
        }


@dataclass
class Interaction:
    """Una interacción entre entidades."""

    id: int | None = None
    project_id: int = 0
    entity1_id: int = 0
    entity2_id: int | None = None
    interaction_type: str = "DIALOGUE"
    tone: str = "NEUTRAL"
    intensity: float = 0.5
    chapter_id: int | None = None
    position: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    text_excerpt: str | None = None
    is_in_dialogue: bool = False
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "Interaction":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            entity1_id=row["entity1_id"],
            entity2_id=row["entity2_id"],
            interaction_type=row["interaction_type"],
            tone=row["tone"] or "NEUTRAL",
            intensity=row["intensity"] or 0.5,
            chapter_id=row["chapter_id"],
            position=row["position"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            text_excerpt=row["text_excerpt"],
            is_in_dialogue=bool(row["is_in_dialogue"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entity1_id": self.entity1_id,
            "entity2_id": self.entity2_id,
            "interaction_type": self.interaction_type,
            "tone": self.tone,
            "intensity": self.intensity,
            "chapter_id": self.chapter_id,
            "text_excerpt": self.text_excerpt,
            "is_in_dialogue": self.is_in_dialogue,
        }


@dataclass
class RegisterChange:
    """Un cambio de registro detectado."""

    id: int | None = None
    project_id: int = 0
    from_register: str = ""
    to_register: str = ""
    chapter_id: int | None = None
    start_char: int = 0
    end_char: int = 0
    position: int | None = None
    text_excerpt: str | None = None
    severity: str = "medium"
    explanation: str | None = None
    confidence: float = 0.8
    is_justified: bool = False
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "RegisterChange":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            from_register=row["from_register"],
            to_register=row["to_register"],
            chapter_id=row["chapter_id"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            position=row["position"],
            text_excerpt=row["text_excerpt"],
            severity=row["severity"] or "medium",
            explanation=row["explanation"],
            confidence=row["confidence"] or 0.8,
            is_justified=bool(row["is_justified"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )


@dataclass
class PacingMetrics:
    """Métricas de pacing de un capítulo."""

    id: int | None = None
    project_id: int = 0
    chapter_id: int = 0
    word_count: int = 0
    sentence_count: int | None = None
    paragraph_count: int | None = None
    dialogue_count: int | None = None
    dialogue_ratio: float | None = None
    avg_sentence_length: float | None = None
    avg_paragraph_length: float | None = None
    lexical_density: float | None = None
    unique_words: int | None = None
    longest_sentence_words: int | None = None
    action_verb_ratio: float | None = None
    pacing_score: float | None = None
    balance_deviation: float | None = None
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> "PacingMetrics":
        """Crea desde fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            word_count=row["word_count"],
            sentence_count=row["sentence_count"],
            paragraph_count=row["paragraph_count"],
            dialogue_count=row["dialogue_count"],
            dialogue_ratio=row["dialogue_ratio"],
            avg_sentence_length=row["avg_sentence_length"],
            avg_paragraph_length=row["avg_paragraph_length"],
            lexical_density=row["lexical_density"],
            unique_words=row["unique_words"],
            longest_sentence_words=row["longest_sentence_words"],
            action_verb_ratio=row["action_verb_ratio"],
            pacing_score=row["pacing_score"],
            balance_deviation=row["balance_deviation"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )


# =============================================================================
# Repository
# =============================================================================


class AnalysisRepository:
    """
    Repositorio para resultados de análisis.

    Uso:
        repo = AnalysisRepository()
        run_id = repo.create_run(project_id, config_json)
        repo.save_relationships(project_id, relationships)
        repo.save_pacing_metrics(project_id, chapter_id, metrics)
    """

    def __init__(self, db: Database | None = None):
        """Inicializa el repositorio."""
        self.db = db or get_database()

    # -------------------------------------------------------------------------
    # Analysis Runs
    # -------------------------------------------------------------------------

    def create_run(
        self,
        project_id: int,
        config_json: str = "",
        quality_profile: str = "standard",
        session_id: int | None = None,
    ) -> int:
        """
        Crea una nueva ejecución de análisis.

        Returns:
            ID del run creado
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_runs (project_id, session_id, config_json, quality_profile)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, session_id, config_json, quality_profile),
            )
            return cursor.lastrowid

    def complete_run(
        self, run_id: int, status: str = "completed", error_message: str | None = None
    ) -> None:
        """Marca un run como completado o fallido."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE analysis_runs
                SET completed_at = datetime('now'), status = ?, error_message = ?
                WHERE id = ?
                """,
                (status, error_message, run_id),
            )

    def get_run(self, run_id: int) -> AnalysisRun | None:
        """Obtiene un run por ID."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            return AnalysisRun.from_row(row) if row else None

    def get_latest_run(self, project_id: int) -> AnalysisRun | None:
        """Obtiene el último run de un proyecto."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            row = conn.execute(
                """
                SELECT * FROM analysis_runs
                WHERE project_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            return AnalysisRun.from_row(row) if row else None

    # -------------------------------------------------------------------------
    # Analysis Phases
    # -------------------------------------------------------------------------

    def save_phase(
        self,
        run_id: int,
        phase_name: str,
        executed: bool = True,
        result_count: int = 0,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Guarda el estado de una fase de análisis."""
        metadata_json = json.dumps(metadata) if metadata else None
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_phases
                (run_id, phase_name, executed, started_at, completed_at, result_count, error_message, metadata_json)
                VALUES (?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?)
                """,
                (run_id, phase_name, int(executed), result_count, error_message, metadata_json),
            )
            return cursor.lastrowid

    def get_executed_phases(self, project_id: int) -> dict[str, bool]:
        """
        Obtiene qué fases se han ejecutado para un proyecto.

        Returns:
            Dict con nombre de fase -> bool ejecutado
        """
        run = self.get_latest_run(project_id)
        if not run:
            return {}

        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            rows = conn.execute(
                "SELECT phase_name, executed FROM analysis_phases WHERE run_id = ?", (run.id,)
            ).fetchall()

        return {row["phase_name"]: bool(row["executed"]) for row in rows}

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    def save_relationship(self, rel: Relationship) -> int:
        """Guarda una relación."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO relationships
                (project_id, entity1_id, entity2_id, relation_type, subtype, direction,
                 confidence, chapter_id, start_char, end_char, source_text, detection_method, is_inferred)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.project_id,
                    rel.entity1_id,
                    rel.entity2_id,
                    rel.relation_type,
                    rel.subtype,
                    rel.direction,
                    rel.confidence,
                    rel.chapter_id,
                    rel.start_char,
                    rel.end_char,
                    rel.source_text,
                    rel.detection_method,
                    int(rel.is_inferred),
                ),
            )
            return cursor.lastrowid

    def save_relationships_batch(self, relationships: list[Relationship]) -> int:
        """Guarda múltiples relaciones en batch."""
        if not relationships:
            return 0
        with self.db.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO relationships
                (project_id, entity1_id, entity2_id, relation_type, subtype, direction,
                 confidence, chapter_id, start_char, end_char, source_text, detection_method, is_inferred)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.project_id,
                        r.entity1_id,
                        r.entity2_id,
                        r.relation_type,
                        r.subtype,
                        r.direction,
                        r.confidence,
                        r.chapter_id,
                        r.start_char,
                        r.end_char,
                        r.source_text,
                        r.detection_method,
                        int(r.is_inferred),
                    )
                    for r in relationships
                ],
            )
        return len(relationships)

    def get_relationships(self, project_id: int) -> list[Relationship]:
        """Obtiene todas las relaciones de un proyecto."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            rows = conn.execute(
                "SELECT * FROM relationships WHERE project_id = ?", (project_id,)
            ).fetchall()
        return [Relationship.from_row(row) for row in rows]

    def delete_relationships(self, project_id: int) -> int:
        """Elimina todas las relaciones de un proyecto."""
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM relationships WHERE project_id = ?", (project_id,))
            return cursor.rowcount

    # -------------------------------------------------------------------------
    # Interactions
    # -------------------------------------------------------------------------

    def save_interaction(self, interaction: Interaction) -> int:
        """Guarda una interacción."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO interactions
                (project_id, entity1_id, entity2_id, interaction_type, tone, intensity,
                 chapter_id, position, start_char, end_char, text_excerpt, is_in_dialogue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.project_id,
                    interaction.entity1_id,
                    interaction.entity2_id,
                    interaction.interaction_type,
                    interaction.tone,
                    interaction.intensity,
                    interaction.chapter_id,
                    interaction.position,
                    interaction.start_char,
                    interaction.end_char,
                    interaction.text_excerpt,
                    int(interaction.is_in_dialogue),
                ),
            )
            return cursor.lastrowid

    def save_interactions_batch(self, interactions: list[Interaction]) -> int:
        """Guarda múltiples interacciones en batch."""
        if not interactions:
            return 0
        with self.db.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO interactions
                (project_id, entity1_id, entity2_id, interaction_type, tone, intensity,
                 chapter_id, position, start_char, end_char, text_excerpt, is_in_dialogue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        i.project_id,
                        i.entity1_id,
                        i.entity2_id,
                        i.interaction_type,
                        i.tone,
                        i.intensity,
                        i.chapter_id,
                        i.position,
                        i.start_char,
                        i.end_char,
                        i.text_excerpt,
                        int(i.is_in_dialogue),
                    )
                    for i in interactions
                ],
            )
        return len(interactions)

    def get_interactions(self, project_id: int, chapter_id: int | None = None) -> list[Interaction]:
        """Obtiene interacciones de un proyecto."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            if chapter_id:
                rows = conn.execute(
                    "SELECT * FROM interactions WHERE project_id = ? AND chapter_id = ?",
                    (project_id, chapter_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM interactions WHERE project_id = ?", (project_id,)
                ).fetchall()
        return [Interaction.from_row(row) for row in rows]

    def delete_interactions(self, project_id: int) -> int:
        """Elimina todas las interacciones de un proyecto."""
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM interactions WHERE project_id = ?", (project_id,))
            return cursor.rowcount

    # -------------------------------------------------------------------------
    # Register Changes
    # -------------------------------------------------------------------------

    def save_register_change(self, change: RegisterChange) -> int:
        """Guarda un cambio de registro."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO register_changes
                (project_id, from_register, to_register, chapter_id, start_char, end_char,
                 position, text_excerpt, severity, explanation, confidence, is_justified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change.project_id,
                    change.from_register,
                    change.to_register,
                    change.chapter_id,
                    change.start_char,
                    change.end_char,
                    change.position,
                    change.text_excerpt,
                    change.severity,
                    change.explanation,
                    change.confidence,
                    int(change.is_justified),
                ),
            )
            return cursor.lastrowid

    def save_register_changes_batch(self, changes: list[RegisterChange]) -> int:
        """Guarda múltiples cambios de registro en batch."""
        if not changes:
            return 0
        with self.db.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO register_changes
                (project_id, from_register, to_register, chapter_id, start_char, end_char,
                 position, text_excerpt, severity, explanation, confidence, is_justified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.project_id,
                        c.from_register,
                        c.to_register,
                        c.chapter_id,
                        c.start_char,
                        c.end_char,
                        c.position,
                        c.text_excerpt,
                        c.severity,
                        c.explanation,
                        c.confidence,
                        int(c.is_justified),
                    )
                    for c in changes
                ],
            )
        return len(changes)

    def get_register_changes(self, project_id: int) -> list[RegisterChange]:
        """Obtiene cambios de registro de un proyecto."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            rows = conn.execute(
                "SELECT * FROM register_changes WHERE project_id = ?", (project_id,)
            ).fetchall()
        return [RegisterChange.from_row(row) for row in rows]

    def delete_register_changes(self, project_id: int) -> int:
        """Elimina todos los cambios de registro de un proyecto."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM register_changes WHERE project_id = ?", (project_id,)
            )
            return cursor.rowcount

    # -------------------------------------------------------------------------
    # Pacing Metrics
    # -------------------------------------------------------------------------

    def save_pacing_metrics(self, metrics: PacingMetrics) -> int:
        """Guarda métricas de pacing (upsert por chapter)."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO pacing_metrics
                (project_id, chapter_id, word_count, sentence_count, paragraph_count,
                 dialogue_count, dialogue_ratio, avg_sentence_length, avg_paragraph_length,
                 lexical_density, unique_words, longest_sentence_words, action_verb_ratio,
                 pacing_score, balance_deviation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metrics.project_id,
                    metrics.chapter_id,
                    metrics.word_count,
                    metrics.sentence_count,
                    metrics.paragraph_count,
                    metrics.dialogue_count,
                    metrics.dialogue_ratio,
                    metrics.avg_sentence_length,
                    metrics.avg_paragraph_length,
                    metrics.lexical_density,
                    metrics.unique_words,
                    metrics.longest_sentence_words,
                    metrics.action_verb_ratio,
                    metrics.pacing_score,
                    metrics.balance_deviation,
                ),
            )
            return cursor.lastrowid

    def get_pacing_metrics(self, project_id: int) -> list[PacingMetrics]:
        """Obtiene métricas de pacing de un proyecto."""
        with self.db.transaction() as conn:
            conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r, strict=False)
            )
            rows = conn.execute(
                "SELECT * FROM pacing_metrics WHERE project_id = ? ORDER BY chapter_id",
                (project_id,),
            ).fetchall()
        return [PacingMetrics.from_row(row) for row in rows]

    def delete_pacing_metrics(self, project_id: int) -> int:
        """Elimina métricas de pacing de un proyecto."""
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM pacing_metrics WHERE project_id = ?", (project_id,))
            return cursor.rowcount


# =============================================================================
# Singleton
# =============================================================================

_analysis_repository: AnalysisRepository | None = None


def get_analysis_repository(db: Database | None = None) -> AnalysisRepository:
    """Obtiene singleton del repositorio de análisis."""
    global _analysis_repository
    if _analysis_repository is None:
        _analysis_repository = AnalysisRepository(db)
    return _analysis_repository


def reset_analysis_repository() -> None:
    """Resetea el singleton (útil para tests)."""
    global _analysis_repository
    _analysis_repository = None
