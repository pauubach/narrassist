"""
Tracker de Chekhov para personajes secundarios.

Extiende la detección de Chekhov's Gun a personajes SUPPORTING/MINOR que
desaparecen del manuscrito sin resolución de su arco narrativo.

BK-16: Chekhov Tracker for SUPPORTING Characters
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .chapter_summary import AbandonedThread, ChekhovElement

logger = logging.getLogger(__name__)


@dataclass
class SupportingCharacterData:
    """Datos de un personaje secundario para análisis de Chekhov."""

    entity_id: int
    name: str
    role: str
    mention_count: int
    first_chapter: int
    last_chapter: int
    chapters_present: int
    has_dialogue: bool
    has_actions: bool
    interaction_partners: list[str] = field(default_factory=list)


class ChekhovTracker:
    """Extiende detección de Chekhov a personajes SUPPORTING."""

    DISAPPEARANCE_THRESHOLD = 0.70
    MIN_MENTIONS = 3
    MAX_MENTIONS = 50
    MIN_CHAPTERS = 2

    def __init__(self, db) -> None:
        self.db = db

    def identify_supporting_characters(
        self, project_id: int
    ) -> list[SupportingCharacterData]:
        """
        Identifica personajes secundarios relevantes.

        Filtra entidades tipo 'person' con 3-50 menciones en 2+ capítulos,
        que tengan diálogo o acciones.
        """
        characters: list[SupportingCharacterData] = []

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT e.id, e.canonical_name, e.mention_count,
                       MIN(c.chapter_number) as first_chapter,
                       MAX(c.chapter_number) as last_chapter,
                       COUNT(DISTINCT c.chapter_number) as chapters_present
                FROM entities e
                JOIN entity_mentions em ON e.id = em.entity_id
                JOIN chapters c ON em.chapter_id = c.id
                WHERE e.project_id = ?
                  AND e.entity_type = 'person'
                  AND e.is_active = 1
                GROUP BY e.id
                HAVING e.mention_count >= ? AND e.mention_count <= ?
                   AND COUNT(DISTINCT c.chapter_number) >= ?
                """,
                (project_id, self.MIN_MENTIONS, self.MAX_MENTIONS, self.MIN_CHAPTERS),
            )

            for row in cursor.fetchall():
                entity_id = row["id"]

                # Verificar diálogo
                dial_cursor = conn.execute(
                    """
                    SELECT COUNT(*) as cnt FROM interactions
                    WHERE project_id = ?
                      AND (entity1_id = ? OR entity2_id = ?)
                      AND interaction_type = 'DIALOGUE'
                    """,
                    (project_id, entity_id, entity_id),
                )
                has_dialogue = dial_cursor.fetchone()["cnt"] > 0

                # Verificar acciones
                act_cursor = conn.execute(
                    """
                    SELECT COUNT(*) as cnt FROM interactions
                    WHERE project_id = ?
                      AND (entity1_id = ? OR entity2_id = ?)
                      AND interaction_type = 'PHYSICAL'
                    """,
                    (project_id, entity_id, entity_id),
                )
                has_actions = act_cursor.fetchone()["cnt"] > 0

                # Solo incluir si tiene diálogo o acciones
                if not has_dialogue and not has_actions:
                    continue

                # Obtener partners de interacción
                partners_cursor = conn.execute(
                    """
                    SELECT DISTINCT e2.canonical_name
                    FROM interactions i
                    JOIN entities e2 ON (
                        CASE WHEN i.entity1_id = ? THEN i.entity2_id
                             ELSE i.entity1_id END
                    ) = e2.id
                    WHERE i.project_id = ?
                      AND (i.entity1_id = ? OR i.entity2_id = ?)
                      AND i.entity2_id IS NOT NULL
                    LIMIT 10
                    """,
                    (entity_id, project_id, entity_id, entity_id),
                )
                partners = [r["canonical_name"] for r in partners_cursor.fetchall()]

                # Determinar rol por menciones
                mc = row["mention_count"]
                role = "supporting" if mc >= 10 else "minor"

                characters.append(
                    SupportingCharacterData(
                        entity_id=entity_id,
                        name=row["canonical_name"],
                        role=role,
                        mention_count=mc,
                        first_chapter=row["first_chapter"],
                        last_chapter=row["last_chapter"],
                        chapters_present=row["chapters_present"],
                        has_dialogue=has_dialogue,
                        has_actions=has_actions,
                        interaction_partners=partners,
                    )
                )

        logger.debug(
            f"Identificados {len(characters)} personajes secundarios para Chekhov"
        )
        return characters

    def track_characters(
        self, project_id: int, total_chapters: int
    ) -> list[ChekhovElement]:
        """
        Detecta personajes tipo Chekhov's Gun (introducidos sin resolución).

        Un personaje "unfired" desaparece antes del último 30% del libro.
        """
        if total_chapters <= 0:
            return []

        characters = self.identify_supporting_characters(project_id)
        elements: list[ChekhovElement] = []

        threshold_chapter = int(total_chapters * self.DISAPPEARANCE_THRESHOLD)

        for char in characters:
            is_fired = char.last_chapter >= threshold_chapter

            # Confianza basada en indicadores
            confidence = 0.4
            if char.has_dialogue:
                confidence += 0.15
            if char.has_actions:
                confidence += 0.10
            if char.chapters_present >= 3:
                confidence += 0.10
            if char.interaction_partners:
                confidence += 0.10
            confidence = min(0.9, confidence)

            # Solo reportar personajes "unfired" (desaparecen temprano)
            if is_fired:
                continue

            element = ChekhovElement(
                entity_id=char.entity_id,
                name=char.name,
                element_type="character",
                setup_chapter=char.first_chapter,
                setup_position=0,
                setup_context=f"Personaje secundario '{char.name}' introducido en capítulo {char.first_chapter}",
                payoff_chapter=None,
                is_fired=False,
                confidence=confidence,
            )
            elements.append(element)

        logger.debug(f"Detectados {len(elements)} personajes Chekhov unfired")
        return elements

    def detect_abandoned_character_threads(
        self, characters: list[SupportingCharacterData], total_chapters: int
    ) -> list[AbandonedThread]:
        """
        Detecta hilos narrativos abandonados por personajes que desaparecen.

        Solo genera AbandonedThread para personajes con interacciones.
        """
        if total_chapters <= 0:
            return []

        threads: list[AbandonedThread] = []
        threshold = int(total_chapters * self.DISAPPEARANCE_THRESHOLD)

        for char in characters:
            # Solo si desaparece antes del umbral y tiene interacciones
            if char.last_chapter >= threshold:
                continue
            if not char.interaction_partners:
                continue

            thread = AbandonedThread(
                description=(
                    f"Personaje secundario '{char.name}' desaparece tras capítulo {char.last_chapter}"
                ),
                introduced_chapter=char.first_chapter,
                last_mention_chapter=char.last_chapter,
                characters_involved=[char.name] + char.interaction_partners[:3],
                entities_involved=[char.name],
                suggestion=(
                    f"Considere resolver el arco de {char.name} o eliminar su introducción"
                ),
                confidence=0.6,
            )
            threads.append(thread)

        return threads
