"""
Analizador de patrones de interacción.

Detecta:
- Patrones de comportamiento entre pares de entidades
- Evolución temporal de interacciones
- Anomalías y cambios bruscos
- Asimetrías en las interacciones
"""

import logging
import statistics
from collections import defaultdict

from ..relationships import EntityRelationship, RelationType
from .models import (
    EntityInteraction,
    InteractionAlert,
    InteractionPattern,
    InteractionTone,
)

logger = logging.getLogger(__name__)


# Mapeo de tipos de relación a tonos esperados
EXPECTED_TONES_BY_RELATION = {
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
    RelationType.SIBLING: [InteractionTone.WARM, InteractionTone.NEUTRAL, InteractionTone.COLD],
    RelationType.MENTOR: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    RelationType.FEARS: [InteractionTone.COLD, InteractionTone.HOSTILE],
    RelationType.HATES: [InteractionTone.HOSTILE, InteractionTone.COLD],
    RelationType.ADMIRES: [InteractionTone.WARM, InteractionTone.AFFECTIONATE],
    RelationType.TRUSTS: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    RelationType.DISTRUSTS: [InteractionTone.COLD, InteractionTone.NEUTRAL],
}


class InteractionPatternAnalyzer:
    """
    Analiza patrones de interacción entre entidades.

    Funcionalidades:
    - Calcular estadísticas de interacción por par de entidades
    - Detectar tendencias (mejora, deterioro, estabilidad)
    - Identificar anomalías respecto al patrón establecido
    - Generar alertas por incoherencias con relaciones
    """

    def __init__(self, relationships: list[EntityRelationship] | None = None):
        """
        Inicializa el analizador.

        Args:
            relationships: Lista de relaciones conocidas para verificar coherencia
        """
        self.relationships = relationships or []
        self._relationship_map = self._build_relationship_map()

    def _build_relationship_map(self) -> dict[tuple[str, str], EntityRelationship]:
        """Construye mapa de relaciones por par de entidades."""
        rel_map = {}
        for rel in self.relationships:
            key = self._normalize_pair(rel.source_entity_name, rel.target_entity_name)
            rel_map[key] = rel
        return rel_map

    def _normalize_pair(self, name1: str, name2: str) -> tuple[str, str]:
        """Normaliza un par de nombres (orden alfabético)."""
        if name1.lower() <= name2.lower():
            return (name1.lower(), name2.lower())
        return (name2.lower(), name1.lower())

    def analyze_pair(
        self,
        entity1_name: str,
        entity2_name: str,
        interactions: list[EntityInteraction],
    ) -> InteractionPattern:
        """
        Genera análisis de patrón para un par de entidades.

        Args:
            entity1_name: Nombre de primera entidad
            entity2_name: Nombre de segunda entidad
            interactions: Lista de interacciones entre ellas

        Returns:
            Patrón de interacción calculado
        """
        if not interactions:
            return InteractionPattern(
                entity1_name=entity1_name,
                entity2_name=entity2_name,
            )

        # Contar por tipo
        by_type = defaultdict(int)
        for inter in interactions:
            by_type[inter.interaction_type.value] += 1

        # Contar por tono
        by_tone = defaultdict(int)
        for inter in interactions:
            by_tone[inter.tone.value] += 1

        # Calcular tono promedio
        tone_scores = [inter.tone.to_score() for inter in interactions]
        avg_score = statistics.mean(tone_scores) if tone_scores else 0.0
        avg_tone = InteractionTone.from_score(avg_score)

        # Calcular varianza de tono
        tone_variance = statistics.variance(tone_scores) if len(tone_scores) > 1 else 0.0

        # Analizar tendencia temporal
        tone_trend = self._calculate_trend(interactions)

        # Calcular asimetría
        e1_lower = entity1_name.lower()
        e2_lower = entity2_name.lower()
        e1_initiations = sum(1 for i in interactions if i.initiator_name.lower() == e1_lower)
        e2_initiations = sum(1 for i in interactions if i.initiator_name.lower() == e2_lower)
        total = e1_initiations + e2_initiations
        asymmetry = e2_initiations / total if total > 0 else 0.5

        # Capítulos
        chapters = [i.chapter for i in interactions]
        first_chapter = min(chapters) if chapters else 0
        last_chapter = max(chapters) if chapters else 0

        # Detectar cambios bruscos
        has_sudden_changes = self._detect_sudden_changes(interactions)

        # Verificar coherencia con relación
        has_tone_mismatch = self._check_tone_mismatch(entity1_name, entity2_name, avg_tone)

        return InteractionPattern(
            entity1_name=entity1_name,
            entity2_name=entity2_name,
            entity1_id="",  # Se puede rellenar si hay IDs
            entity2_id="",
            total_interactions=len(interactions),
            interactions_by_type=dict(by_type),
            interactions_by_tone=dict(by_tone),
            average_tone=avg_tone,
            average_sentiment_score=avg_score,
            tone_variance=tone_variance,
            tone_trend=tone_trend,
            first_interaction_chapter=first_chapter,
            last_interaction_chapter=last_chapter,
            initiations_by_entity1=e1_initiations,
            initiations_by_entity2=e2_initiations,
            asymmetry_ratio=asymmetry,
            has_sudden_changes=has_sudden_changes,
            has_tone_mismatch=has_tone_mismatch,
        )

    def _calculate_trend(self, interactions: list[EntityInteraction]) -> str:
        """
        Calcula la tendencia del tono a lo largo del tiempo.

        Returns:
            "improving", "deteriorating", "stable", o "volatile"
        """
        if len(interactions) < 3:
            return "stable"

        # Ordenar por capítulo
        sorted_interactions = sorted(interactions, key=lambda i: (i.chapter, i.start_char))

        # Dividir en primera y segunda mitad
        mid = len(sorted_interactions) // 2
        first_half = sorted_interactions[:mid]
        second_half = sorted_interactions[mid:]

        first_avg = statistics.mean([i.tone.to_score() for i in first_half])
        second_avg = statistics.mean([i.tone.to_score() for i in second_half])

        # Calcular varianza total
        all_scores = [i.tone.to_score() for i in sorted_interactions]
        variance = statistics.variance(all_scores) if len(all_scores) > 1 else 0

        # Si hay mucha varianza, es volátil
        if variance > 0.3:
            return "volatile"

        # Comparar medias
        diff = second_avg - first_avg
        if diff > 0.2:
            return "improving"
        elif diff < -0.2:
            return "deteriorating"
        else:
            return "stable"

    def _detect_sudden_changes(self, interactions: list[EntityInteraction]) -> bool:
        """
        Detecta cambios bruscos de tono entre interacciones consecutivas.

        Returns:
            True si hay cambios bruscos
        """
        if len(interactions) < 2:
            return False

        sorted_interactions = sorted(interactions, key=lambda i: (i.chapter, i.start_char))

        for i in range(1, len(sorted_interactions)):
            prev_score = sorted_interactions[i - 1].tone.to_score()
            curr_score = sorted_interactions[i].tone.to_score()

            # Cambio brusco = diferencia > 1.0 (de afectuoso a hostil o viceversa)
            if abs(curr_score - prev_score) > 1.0:
                return True

        return False

    def _check_tone_mismatch(
        self,
        entity1_name: str,
        entity2_name: str,
        avg_tone: InteractionTone,
    ) -> bool:
        """
        Verifica si el tono promedio contradice la relación conocida.

        Returns:
            True si hay discrepancia
        """
        pair_key = self._normalize_pair(entity1_name, entity2_name)
        relationship = self._relationship_map.get(pair_key)

        if not relationship:
            return False

        expected_tones = EXPECTED_TONES_BY_RELATION.get(relationship.relation_type, [])

        if not expected_tones:
            return False

        return avg_tone not in expected_tones

    def detect_anomaly(
        self,
        pattern: InteractionPattern,
        new_interaction: EntityInteraction,
    ) -> InteractionAlert | None:
        """
        Detecta si una nueva interacción rompe el patrón establecido.

        Args:
            pattern: Patrón establecido para el par
            new_interaction: Nueva interacción a evaluar

        Returns:
            Alerta si hay anomalía, None si es normal
        """
        if pattern.total_interactions < 3:
            # No hay suficiente historial para detectar anomalías
            return None

        # Calcular diferencia con el tono promedio
        new_score = new_interaction.tone.to_score()
        diff = abs(new_score - pattern.average_sentiment_score)

        # Si la diferencia es mayor que 2 desviaciones estándar (o > 0.6 si no hay varianza)
        threshold = max(0.6, pattern.tone_variance * 2) if pattern.tone_variance > 0 else 0.6

        if diff > threshold:
            # Es una anomalía
            return InteractionAlert(
                code="INT_SUDDEN_CHANGE",
                alert_type="Cambio brusco de tono",
                severity="warning",
                entity1_name=new_interaction.initiator_name,
                entity2_name=new_interaction.receiver_name,
                interaction_id=new_interaction.id,
                chapter=new_interaction.chapter,
                text_excerpt=new_interaction.text_excerpt,
                detected_tone=new_interaction.tone.value,
                expected_tones=[pattern.average_tone.value],
                explanation=(
                    f"La interacción tiene tono '{new_interaction.tone.value}' "
                    f"pero el patrón establecido entre {pattern.entity1_name} y "
                    f"{pattern.entity2_name} es '{pattern.average_tone.value}' "
                    f"(score promedio: {pattern.average_sentiment_score:.2f})."
                ),
                suggestion=(
                    "Verificar si hay un evento narrativo que justifique este cambio de tono."
                ),
                confidence=0.7,
            )

        return None

    def check_relationship_coherence(
        self,
        interaction: EntityInteraction,
        relationship: EntityRelationship | None = None,
    ) -> InteractionAlert | None:
        """
        Verifica si una interacción es coherente con la relación.

        Args:
            interaction: Interacción a verificar
            relationship: Relación conocida (se busca automáticamente si no se proporciona)

        Returns:
            Alerta si hay incoherencia
        """
        if relationship is None:
            pair_key = self._normalize_pair(interaction.initiator_name, interaction.receiver_name)
            relationship = self._relationship_map.get(pair_key)

        if relationship is None:
            return None

        expected_tones = EXPECTED_TONES_BY_RELATION.get(relationship.relation_type, [])

        if not expected_tones:
            return None

        if interaction.tone in expected_tones:
            return None

        # Determinar código y severidad según el tipo de incoherencia
        if relationship.relation_type == RelationType.ENEMY:
            if interaction.tone in [InteractionTone.WARM, InteractionTone.AFFECTIONATE]:
                code = "INT_ENEMY_FRIENDLY"
                alert_type = "Enemigos interactúan amistosamente"
                severity = "warning"
            else:
                code = "INT_TONE_MISMATCH"
                alert_type = "Tono no corresponde con relación"
                severity = "info"

        elif relationship.relation_type == RelationType.FRIEND:
            if interaction.tone in [InteractionTone.HOSTILE, InteractionTone.COLD]:
                code = "INT_FRIEND_HOSTILE"
                alert_type = "Amigos interactúan hostilmente"
                severity = "warning"
            else:
                code = "INT_TONE_MISMATCH"
                alert_type = "Tono no corresponde con relación"
                severity = "info"

        elif relationship.relation_type == RelationType.LOVER:
            if interaction.tone in [InteractionTone.HOSTILE, InteractionTone.COLD]:
                code = "INT_LOVER_HOSTILE"
                alert_type = "Pareja interactúa hostilmente"
                severity = "warning"
            else:
                code = "INT_TONE_MISMATCH"
                alert_type = "Tono no corresponde con relación"
                severity = "info"

        else:
            code = "INT_TONE_MISMATCH"
            alert_type = "Tono no corresponde con relación"
            severity = "info"

        expected_str = ", ".join(t.value for t in expected_tones)

        return InteractionAlert(
            code=code,
            alert_type=alert_type,
            severity=severity,
            entity1_name=interaction.initiator_name,
            entity2_name=interaction.receiver_name,
            relationship_type=relationship.relation_type.value,
            interaction_id=interaction.id,
            chapter=interaction.chapter,
            text_excerpt=interaction.text_excerpt,
            detected_tone=interaction.tone.value,
            expected_tones=[t.value for t in expected_tones],
            explanation=(
                f"La relación entre {interaction.initiator_name} y "
                f"{interaction.receiver_name} es de tipo '{relationship.relation_type.value}', "
                f"pero la interacción tiene tono '{interaction.tone.value}'. "
                f"Se esperaban tonos: {expected_str}."
            ),
            suggestion=(
                "Verificar si existe un cambio de relación que justifique "
                "esta interacción, o marcarla como incoherencia intencional."
            ),
            confidence=0.7,
        )

    def generate_all_patterns(
        self,
        interactions: list[EntityInteraction],
    ) -> dict[tuple[str, str], InteractionPattern]:
        """
        Genera patrones para todos los pares de entidades con interacciones.

        Args:
            interactions: Todas las interacciones detectadas

        Returns:
            Dict de (entity1, entity2) -> InteractionPattern
        """
        # Agrupar por par de entidades
        by_pair: dict[tuple[str, str], list[EntityInteraction]] = defaultdict(list)

        for interaction in interactions:
            pair = self._normalize_pair(interaction.initiator_name, interaction.receiver_name)
            by_pair[pair].append(interaction)

        # Generar patrón para cada par
        patterns = {}
        for (e1, e2), pair_interactions in by_pair.items():
            patterns[(e1, e2)] = self.analyze_pair(e1, e2, pair_interactions)

        return patterns

    def generate_coherence_alerts(
        self,
        interactions: list[EntityInteraction],
    ) -> list[InteractionAlert]:
        """
        Genera todas las alertas de coherencia para una lista de interacciones.

        Args:
            interactions: Lista de interacciones a analizar

        Returns:
            Lista de alertas generadas
        """
        alerts = []

        # Generar patrones
        patterns = self.generate_all_patterns(interactions)

        for interaction in interactions:
            # Verificar coherencia con relación
            rel_alert = self.check_relationship_coherence(interaction)
            if rel_alert:
                alerts.append(rel_alert)

            # Verificar anomalía respecto al patrón
            pair = self._normalize_pair(interaction.initiator_name, interaction.receiver_name)
            pattern = patterns.get(pair)

            if pattern:
                anomaly_alert = self.detect_anomaly(pattern, interaction)
                if anomaly_alert:
                    alerts.append(anomaly_alert)

        return alerts

    def detect_asymmetric_relationships(
        self,
        patterns: dict[tuple[str, str], InteractionPattern],
        threshold: float = 0.3,
    ) -> list[InteractionAlert]:
        """
        Detecta relaciones donde las interacciones son muy asimétricas.

        Args:
            patterns: Patrones de interacción por par
            threshold: Umbral de asimetría (default 0.3 = 70/30)

        Returns:
            Lista de alertas por asimetría
        """
        alerts = []

        for (e1, e2), pattern in patterns.items():
            if pattern.total_interactions < 5:
                continue

            # Asimetría muy alta
            if pattern.asymmetry_ratio < threshold or pattern.asymmetry_ratio > (1 - threshold):
                dominant = (
                    pattern.entity1_name if pattern.asymmetry_ratio < 0.5 else pattern.entity2_name
                )
                passive = (
                    pattern.entity2_name if pattern.asymmetry_ratio < 0.5 else pattern.entity1_name
                )

                alerts.append(
                    InteractionAlert(
                        code="INT_ONE_SIDED",
                        alert_type="Interacciones unidireccionales",
                        severity="info",
                        entity1_name=dominant,
                        entity2_name=passive,
                        explanation=(
                            f"Las interacciones entre {e1} y {e2} son muy asimétricas. "
                            f"{dominant} inicia la mayoría de las interacciones "
                            f"({int((1 - pattern.asymmetry_ratio if pattern.asymmetry_ratio < 0.5 else pattern.asymmetry_ratio) * 100)}%)."
                        ),
                        suggestion=(
                            "Verificar si esta asimetría es intencional o si "
                            f"{passive} debería tener más iniciativa."
                        ),
                        confidence=0.6,
                    )
                )

        return alerts
