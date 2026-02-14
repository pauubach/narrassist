"""
Análisis de coherencia relacional y detección de inconsistencias.

Verifica que las interacciones entre entidades sean coherentes
con las relaciones establecidas y genera alertas cuando no lo son.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

from .models import (
    CoherenceAlert,
    EntityRelationship,
    InferredExpectations,
    RelationType,
    TextReference,
)

logger = logging.getLogger(__name__)


class InteractionTone(Enum):
    """Tono de una interacción."""

    HOSTILE = "hostile"
    COLD = "cold"
    NEUTRAL = "neutral"
    WARM = "warm"
    AFFECTIONATE = "affectionate"


@dataclass
class EntityInteraction:
    """Una interacción específica entre entidades."""

    initiator_name: str
    receiver_name: str
    interaction_type: str  # dialogue, action, thought, observation
    tone: InteractionTone
    chapter: int = 0
    text_excerpt: str = ""
    start_char: int = 0
    end_char: int = 0
    sentiment_score: float = 0.0


# Mapeo de tipos de relación a tonos esperados
EXPECTED_TONES = {
    RelationType.FRIEND: [
        InteractionTone.WARM,
        InteractionTone.AFFECTIONATE,
        InteractionTone.NEUTRAL,
    ],
    RelationType.ENEMY: [InteractionTone.HOSTILE, InteractionTone.COLD],
    RelationType.LOVER: [InteractionTone.AFFECTIONATE, InteractionTone.WARM],
    RelationType.RIVAL: [InteractionTone.COLD, InteractionTone.HOSTILE, InteractionTone.NEUTRAL],
    RelationType.PARENT: [
        InteractionTone.WARM,
        InteractionTone.NEUTRAL,
        InteractionTone.AFFECTIONATE,
    ],
    RelationType.CHILD: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    RelationType.MENTOR: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    RelationType.FEARS: [InteractionTone.COLD, InteractionTone.HOSTILE],  # Receptor inspira miedo
    RelationType.HATES: [InteractionTone.HOSTILE, InteractionTone.COLD],
    RelationType.ADMIRES: [InteractionTone.WARM, InteractionTone.AFFECTIONATE],
    RelationType.TRUSTS: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    RelationType.DISTRUSTS: [InteractionTone.COLD, InteractionTone.NEUTRAL],
}

# Palabras clave para detectar tono
TONE_KEYWORDS = {
    InteractionTone.HOSTILE: [
        "golpeó",
        "atacó",
        "gritó",
        "insultó",
        "amenazó",
        "odio",
        "maldijo",
        "escupió",
        "empujó",
        "hirió",
        "furioso",
        "rabia",
        "desprecio",
    ],
    InteractionTone.COLD: [
        "ignoró",
        "evitó",
        "frialdad",
        "distante",
        "indiferente",
        "seco",
        "cortante",
        "despectivo",
        "desdeñoso",
    ],
    InteractionTone.WARM: [
        "sonrió",
        "ayudó",
        "apoyó",
        "compartió",
        "alegró",
        "amable",
        "cariño",
        "preocupó",
        "animó",
    ],
    InteractionTone.AFFECTIONATE: [
        "abrazó",
        "besó",
        "acarició",
        "amor",
        "adoraba",
        "quería",
        "ternura",
        "dulzura",
        "cariñosamente",
    ],
}

# Comportamientos que contradicen relaciones específicas
CONTRADICTING_BEHAVIORS = {
    RelationType.FRIEND: ["traicionó", "abandonó", "ignoró completamente", "atacó sin razón"],
    RelationType.ENEMY: ["abrazó con cariño", "ayudó desinteresadamente", "declaró su amor"],
    RelationType.FEARS: ["se acercó tranquilamente", "abrazó", "disfrutó", "buscó"],
    RelationType.HATES: ["abrazó cariñosamente", "besó", "ayudó sin motivo"],
    RelationType.AVOIDS: ["visitó voluntariamente", "buscó", "disfrutó del lugar"],
    RelationType.CURSED_BY: [],  # Consecuencias, no comportamientos
}


class InteractionCoherenceChecker:
    """
    Verifica coherencia entre interacciones y relaciones establecidas.

    Detecta cuando el tono o comportamiento de una interacción
    contradice la relación conocida entre las entidades.
    """

    def __init__(self, sentiment_analyzer=None):
        """
        Inicializa el checker.

        Args:
            sentiment_analyzer: Analizador de sentimiento opcional para
                               clasificación más precisa del tono.
        """
        self.sentiment_analyzer = sentiment_analyzer

    def classify_tone(self, text: str) -> InteractionTone:
        """
        Clasifica el tono de un texto de interacción.

        Args:
            text: Texto de la interacción

        Returns:
            Tono detectado
        """
        text_lower = text.lower()

        # Contar keywords por tono
        scores = dict.fromkeys(InteractionTone, 0)

        for tone, keywords in TONE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[tone] += 1

        # Si hay keywords, usar el tono con más coincidencias
        max_score = max(scores.values())
        if max_score > 0:
            for tone, score in scores.items():
                if score == max_score:
                    return tone

        # Si hay analizador de sentimiento, usarlo
        if self.sentiment_analyzer:
            try:
                result = self.sentiment_analyzer.analyze_text(
                    text, speaker="", chapter_id=0, start_char=0, end_char=len(text)
                )
                if result.is_success and result.value:
                    score = result.value.sentiment_score
                    if score < -0.5:
                        return InteractionTone.HOSTILE
                    elif score < -0.2:
                        return InteractionTone.COLD
                    elif score < 0.2:
                        return InteractionTone.NEUTRAL
                    elif score < 0.5:
                        return InteractionTone.WARM
                    else:
                        return InteractionTone.AFFECTIONATE
            except Exception as e:
                logger.debug(f"Error usando analizador de sentimiento para clasificar tono: {e}")

        return InteractionTone.NEUTRAL

    def check_coherence(
        self,
        interaction: EntityInteraction,
        relationship: EntityRelationship,
    ) -> CoherenceAlert | None:
        """
        Verifica si una interacción es coherente con la relación.

        Args:
            interaction: La interacción a verificar
            relationship: La relación establecida

        Returns:
            Alerta si hay incoherencia, None si es coherente
        """
        expected_tones = EXPECTED_TONES.get(relationship.relation_type, [])

        # Si no hay expectativas definidas, no podemos verificar
        if not expected_tones:
            return None

        # Verificar si el tono es esperado
        if interaction.tone in expected_tones:
            return None

        # Verificar si hay comportamiento explícitamente contradictorio
        contradicting = CONTRADICTING_BEHAVIORS.get(relationship.relation_type, [])
        has_explicit_contradiction = any(
            c in interaction.text_excerpt.lower() for c in contradicting
        )

        # Determinar severidad
        severity = "warning" if has_explicit_contradiction else "info"

        # Determinar código de alerta
        if relationship.relation_type == RelationType.ENEMY:
            if interaction.tone in [InteractionTone.WARM, InteractionTone.AFFECTIONATE]:
                code = "INT_ENEMY_FRIENDLY"
                alert_type = "Enemigos interactúan amistosamente"
            else:
                code = "INT_TONE_MISMATCH"
                alert_type = "Tono no corresponde con relación"
        elif relationship.relation_type == RelationType.FRIEND:
            if interaction.tone in [InteractionTone.HOSTILE, InteractionTone.COLD]:
                code = "INT_FRIEND_HOSTILE"
                alert_type = "Amigos interactúan hostilmente"
            else:
                code = "INT_TONE_MISMATCH"
                alert_type = "Tono no corresponde con relación"
        else:
            code = "INT_TONE_MISMATCH"
            alert_type = "Tono no corresponde con relación"

        expected_tones_str = ", ".join(t.value for t in expected_tones)

        return CoherenceAlert(
            code=code,
            alert_type=alert_type,
            severity=severity,
            source_entity=interaction.initiator_name,
            target_entity=interaction.receiver_name,
            relationship_type=relationship.relation_type.value,
            establishing_reference=TextReference(
                chapter=relationship.first_mention_chapter or 0,
            ),
            establishing_quote=(
                relationship.evidence_texts[0] if relationship.evidence_texts else ""
            ),
            contradicting_reference=TextReference(
                chapter=interaction.chapter,
                char_start=interaction.start_char,
                char_end=interaction.end_char,
            ),
            contradicting_quote=interaction.text_excerpt,
            explanation=(
                f"La relación entre {interaction.initiator_name} y {interaction.receiver_name} "
                f"es de tipo '{relationship.relation_type.value}', pero la interacción detectada "
                f"tiene tono '{interaction.tone.value}'. Se esperaban tonos: {expected_tones_str}."
            ),
            suggestion=(
                "Verificar si existe un cambio de relación entre los personajes "
                "que justifique esta interacción, o si el tono detectado es incorrecto."
            ),
            confidence=0.7,
        )

    def check_forbidden_behavior(
        self,
        text: str,
        relationship: EntityRelationship,
        chapter: int = 0,
        start_char: int = 0,
        end_char: int = 0,
    ) -> CoherenceAlert | None:
        """
        Verifica si el texto contiene comportamiento prohibido para la relación.

        Args:
            text: Texto a analizar
            relationship: Relación establecida
            chapter: Número de capítulo
            start_char: Posición inicial
            end_char: Posición final

        Returns:
            Alerta si hay comportamiento prohibido
        """
        # Obtener expectativas
        expectations = relationship.expectations
        if not expectations:
            # Usar expectativas basadas en reglas
            if hasattr(relationship, "relation_type"):
                rel_type = relationship.relation_type
                # Crear expectations desde reglas internas
                forbidden = CONTRADICTING_BEHAVIORS.get(rel_type, [])
                if forbidden:
                    expectations = InferredExpectations(
                        expected_behaviors=[],
                        forbidden_behaviors=forbidden,
                        expected_consequences=[],
                        confidence=0.6,
                        reasoning="Reglas internas",
                        inference_source="rule_based",
                    )

        if not expectations or not expectations.forbidden_behaviors:
            return None

        text_lower = text.lower()

        # Buscar comportamientos prohibidos
        for forbidden in expectations.forbidden_behaviors:  # type: ignore[assignment]
            if forbidden.lower() in text_lower:  # type: ignore[attr-defined]
                return CoherenceAlert(
                    code="COHERENCE_FORBIDDEN_BEHAVIOR",
                    alert_type="Comportamiento contradictorio",
                    severity="warning",
                    source_entity=relationship.source_entity_name,
                    target_entity=relationship.target_entity_name,
                    relationship_type=relationship.relation_type.value,
                    establishing_reference=TextReference(
                        chapter=relationship.first_mention_chapter or 0,
                    ),
                    establishing_quote=(
                        relationship.evidence_texts[0] if relationship.evidence_texts else ""
                    ),
                    contradicting_reference=TextReference(
                        chapter=chapter,
                        char_start=start_char,
                        char_end=end_char,
                    ),
                    contradicting_quote=text[:200] + ("..." if len(text) > 200 else ""),
                    explanation=(
                        f"{relationship.source_entity_name} realiza comportamiento "
                        f"prohibido ('{forbidden}') respecto a {relationship.target_entity_name}, "
                        f"lo cual contradice la relación de tipo '{relationship.relation_type.value}'."
                    ),
                    suggestion=(
                        "Verificar si hay una escena de cambio de relación que justifique "
                        "este comportamiento."
                    ),
                    confidence=0.8,
                )

        return None

    def check_missing_expected_behavior(
        self,
        scene_text: str,
        relationship: EntityRelationship,
        chapter: int = 0,
    ) -> CoherenceAlert | None:
        """
        Verifica si falta un comportamiento esperado en un encuentro.

        Args:
            scene_text: Texto de la escena donde coinciden las entidades
            relationship: Relación establecida
            chapter: Número de capítulo

        Returns:
            Alerta si falta comportamiento esperado
        """
        expectations = relationship.expectations
        if not expectations or not expectations.expected_behaviors:
            return None

        scene_lower = scene_text.lower()

        # Verificar si algún comportamiento esperado está presente
        found_expected = False
        for expected in expectations.expected_behaviors:
            if expected.lower() in scene_lower:
                found_expected = True
                break

        if found_expected:
            return None

        # Solo alertar si la relación tiene alta intensidad/importancia
        if relationship.intensity < 0.6:
            return None

        expected_str = ", ".join(expectations.expected_behaviors[:3])

        return CoherenceAlert(
            code="COHERENCE_MISSING_EXPECTED",
            alert_type="Reacción esperada ausente",
            severity="info",
            source_entity=relationship.source_entity_name,
            target_entity=relationship.target_entity_name,
            relationship_type=relationship.relation_type.value,
            establishing_reference=TextReference(
                chapter=relationship.first_mention_chapter or 0,
            ),
            establishing_quote=(
                relationship.evidence_texts[0] if relationship.evidence_texts else ""
            ),
            contradicting_reference=TextReference(chapter=chapter),
            contradicting_quote="",
            explanation=(
                f"En el capítulo {chapter}, {relationship.source_entity_name} y "
                f"{relationship.target_entity_name} coinciden, pero no se observan "
                f"los comportamientos esperados para una relación de tipo "
                f"'{relationship.relation_type.value}': {expected_str}."
            ),
            suggestion=(
                "Considerar añadir una reacción o comportamiento que refleje "
                "la naturaleza de la relación entre los personajes."
            ),
            confidence=0.5,
        )


class RelationshipAnalyzer:
    """
    Analiza coherencia y evolución de relaciones.

    Detecta:
    - Comportamientos que contradicen relaciones establecidas
    - Cambios de relación sin justificación narrativa
    - Interacciones con tonos inadecuados
    """

    def __init__(
        self,
        inference_engine=None,
        coherence_checker: InteractionCoherenceChecker | None = None,
    ):
        """
        Inicializa el analizador.

        Args:
            inference_engine: Motor de inferencia de expectativas (IA)
            coherence_checker: Verificador de coherencia de interacciones
        """
        self.inference_engine = inference_engine
        self.coherence_checker = coherence_checker or InteractionCoherenceChecker()

    def check_scene_consistency(
        self,
        scene_text: str,
        relationships: list[EntityRelationship],
        chapter: int = 0,
        start_char: int = 0,
        end_char: int = 0,
    ) -> list[CoherenceAlert]:
        """
        Verifica coherencia de una escena respecto a relaciones conocidas.

        Args:
            scene_text: Texto de la escena
            relationships: Relaciones entre entidades presentes
            chapter: Número de capítulo
            start_char: Posición inicial de la escena
            end_char: Posición final de la escena

        Returns:
            Lista de alertas de inconsistencia
        """
        alerts = []

        for rel in relationships:
            # Verificar comportamientos prohibidos
            forbidden_alert = self.coherence_checker.check_forbidden_behavior(
                scene_text,
                rel,
                chapter,
                start_char,
                end_char,
            )
            if forbidden_alert:
                alerts.append(forbidden_alert)

            # Verificar comportamientos esperados ausentes
            missing_alert = self.coherence_checker.check_missing_expected_behavior(
                scene_text,
                rel,
                chapter,
            )
            if missing_alert:
                alerts.append(missing_alert)

        return alerts

    def detect_interaction(
        self,
        text: str,
        entity1_name: str,
        entity2_name: str,
        chapter: int = 0,
        start_char: int = 0,
        end_char: int = 0,
    ) -> EntityInteraction | None:
        """
        Detecta una interacción entre dos entidades en un texto.

        Args:
            text: Texto a analizar
            entity1_name: Nombre de primera entidad
            entity2_name: Nombre de segunda entidad
            chapter: Número de capítulo
            start_char: Posición inicial
            end_char: Posición final

        Returns:
            Interacción detectada o None
        """
        text_lower = text.lower()
        e1_lower = entity1_name.lower()
        e2_lower = entity2_name.lower()

        # Verificar que ambas entidades están mencionadas
        if e1_lower not in text_lower or e2_lower not in text_lower:
            return None

        # Determinar tipo de interacción
        interaction_type = "observation"  # Default

        # Patrones para tipos de interacción
        dialogue_patterns = [r"—.*—", r'".*"', r"«.*»", r"dijo", r"respondió", r"preguntó"]
        action_patterns = [r"golpeó", r"abrazó", r"besó", r"empujó", r"ayudó", r"atacó"]
        thought_patterns = [r"pensó", r"recordó", r"imaginó", r"creyó"]

        for pattern in dialogue_patterns:
            if re.search(pattern, text):
                interaction_type = "dialogue"
                break

        if interaction_type == "observation":
            for pattern in action_patterns:
                if pattern in text_lower:
                    interaction_type = "action"
                    break

        if interaction_type == "observation":
            for pattern in thought_patterns:
                if pattern in text_lower:
                    interaction_type = "thought"
                    break

        # Clasificar tono
        tone = self.coherence_checker.classify_tone(text)

        # Determinar quién inicia
        # Si entity1 aparece primero y es sujeto de verbos, es el iniciador
        pos1 = text_lower.find(e1_lower)
        pos2 = text_lower.find(e2_lower)

        if pos1 < pos2:
            initiator = entity1_name
            receiver = entity2_name
        else:
            initiator = entity2_name
            receiver = entity1_name

        return EntityInteraction(
            initiator_name=initiator,
            receiver_name=receiver,
            interaction_type=interaction_type,
            tone=tone,
            chapter=chapter,
            text_excerpt=text[:300] + ("..." if len(text) > 300 else ""),
            start_char=start_char,
            end_char=end_char,
        )

    def analyze_interaction_coherence(
        self,
        interaction: EntityInteraction,
        relationship: EntityRelationship,
    ) -> CoherenceAlert | None:
        """
        Analiza si una interacción es coherente con una relación.

        Args:
            interaction: Interacción detectada
            relationship: Relación establecida

        Returns:
            Alerta si hay incoherencia
        """
        return self.coherence_checker.check_coherence(interaction, relationship)

    def track_relationship_evolution(
        self,
        relationship: EntityRelationship,
        interactions: list[EntityInteraction],
    ) -> list[dict]:
        """
        Rastrea cómo evoluciona una relación a lo largo de las interacciones.

        Args:
            relationship: Relación a analizar
            interactions: Lista de interacciones ordenadas por capítulo

        Returns:
            Lista de cambios detectados
        """
        changes = []  # type: ignore[var-annotated]
        prev_tone = None

        for interaction in sorted(interactions, key=lambda i: i.chapter):
            if prev_tone is not None and prev_tone != interaction.tone:
                # Detectar cambio significativo
                change = {
                    "chapter": interaction.chapter,
                    "old_tone": prev_tone.value,
                    "new_tone": interaction.tone.value,
                    "text": interaction.text_excerpt,
                    "significant": self._is_significant_change(prev_tone, interaction.tone),
                }
                changes.append(change)

            prev_tone = interaction.tone

        return changes

    def _is_significant_change(
        self,
        old_tone: InteractionTone,
        new_tone: InteractionTone,
    ) -> bool:
        """Determina si un cambio de tono es significativo."""
        # Cambios entre extremos son significativos
        significant_pairs = [
            (InteractionTone.HOSTILE, InteractionTone.AFFECTIONATE),
            (InteractionTone.AFFECTIONATE, InteractionTone.HOSTILE),
            (InteractionTone.HOSTILE, InteractionTone.WARM),
            (InteractionTone.WARM, InteractionTone.HOSTILE),
            (InteractionTone.COLD, InteractionTone.AFFECTIONATE),
            (InteractionTone.AFFECTIONATE, InteractionTone.COLD),
        ]

        return (old_tone, new_tone) in significant_pairs

    def generate_relationship_report(
        self,
        relationships: list[EntityRelationship],
    ) -> dict:
        """
        Genera un reporte de relaciones.

        Args:
            relationships: Lista de relaciones a incluir

        Returns:
            Diccionario con el reporte
        """
        by_type: dict[str, list] = {}
        high_intensity = []
        unconfirmed = []

        for rel in relationships:
            # Agrupar por tipo
            type_key = rel.relation_type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(
                {
                    "source": rel.source_entity_name,
                    "target": rel.target_entity_name,
                    "intensity": rel.intensity,
                    "confidence": rel.confidence,
                }
            )

            # Relaciones intensas
            if rel.intensity >= 0.8:
                high_intensity.append(
                    {
                        "source": rel.source_entity_name,
                        "target": rel.target_entity_name,
                        "type": rel.relation_type.value,
                        "intensity": rel.intensity,
                    }
                )

            # Relaciones sin confirmar
            if not rel.user_confirmed and not rel.user_rejected:
                unconfirmed.append(
                    {
                        "id": rel.id,
                        "source": rel.source_entity_name,
                        "target": rel.target_entity_name,
                        "type": rel.relation_type.value,
                        "confidence": rel.confidence,
                    }
                )

        return {
            "total_relationships": len(relationships),
            "by_type": by_type,
            "high_intensity_relationships": high_intensity,
            "pending_review": unconfirmed,
            "type_counts": {k: len(v) for k, v in by_type.items()},
        }
