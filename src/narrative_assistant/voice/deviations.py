"""
Detector de desviaciones de voz.

Identifica cuando un personaje habla de manera inconsistente con su perfil
establecido, lo cual puede indicar un error del autor o un cambio intencional.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from statistics import mean

from .profiles import VoiceProfile, VoiceMetrics, VoiceProfileBuilder

logger = logging.getLogger(__name__)


class DeviationType(Enum):
    """Tipos de desviación de voz."""
    FORMALITY_SHIFT = "formality_shift"  # Cambio de registro formal/informal
    LENGTH_ANOMALY = "length_anomaly"  # Intervención inusualmente larga/corta
    VOCABULARY_SHIFT = "vocabulary_shift"  # Uso de vocabulario atípico
    FILLER_ANOMALY = "filler_anomaly"  # Cambio en uso de muletillas
    PUNCTUATION_SHIFT = "punctuation_shift"  # Cambio en patrones de puntuación
    TTR_ANOMALY = "ttr_anomaly"  # Cambio en riqueza léxica
    SYNTAX_SHIFT = "syntax_shift"  # Cambio en complejidad sintáctica


class DeviationSeverity(Enum):
    """Severidad de la desviación."""
    LOW = "low"  # Desviación menor, probablemente aceptable
    MEDIUM = "medium"  # Desviación notable, revisar
    HIGH = "high"  # Desviación significativa, posible error


@dataclass
class VoiceDeviation:
    """Una desviación detectada en la voz de un personaje."""

    entity_id: int
    entity_name: str
    deviation_type: DeviationType
    severity: DeviationSeverity

    # Ubicación
    chapter: int
    position: int
    text: str  # El diálogo problemático

    # Detalles de la desviación
    expected_value: float
    actual_value: float
    description: str

    # Confianza en la detección
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        """Convierte la desviación a diccionario."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "deviation_type": self.deviation_type.value,
            "severity": self.severity.value,
            "chapter": self.chapter,
            "position": self.position,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "description": self.description,
            "confidence": self.confidence,
        }


class VoiceDeviationDetector:
    """Detector de desviaciones de voz."""

    def __init__(
        self,
        length_threshold: float = 2.0,  # Desviaciones estándar
        formality_threshold: float = 0.3,  # Diferencia en score
        filler_threshold: float = 0.5,  # Diferencia relativa
        punctuation_threshold: float = 0.5,  # Diferencia relativa
    ):
        """
        Inicializa el detector.

        Args:
            length_threshold: Umbral en desviaciones estándar para longitud
            formality_threshold: Umbral de diferencia para formalidad
            filler_threshold: Umbral de diferencia relativa para muletillas
            punctuation_threshold: Umbral de diferencia para puntuación
        """
        self.length_threshold = length_threshold
        self.formality_threshold = formality_threshold
        self.filler_threshold = filler_threshold
        self.punctuation_threshold = punctuation_threshold

    def detect_deviations(
        self,
        profiles: List[VoiceProfile],
        dialogues: List[Dict],
    ) -> List[VoiceDeviation]:
        """
        Detecta desviaciones de voz en diálogos.

        Args:
            profiles: Perfiles de voz de los personajes
            dialogues: Diálogos a analizar con formato:
                {
                    "text": str,
                    "speaker_id": int,
                    "chapter": int,
                    "position": int
                }

        Returns:
            Lista de desviaciones detectadas
        """
        deviations = []
        profile_map = {p.entity_id: p for p in profiles}

        for dialogue in dialogues:
            speaker_id = dialogue.get("speaker_id")
            if not speaker_id or speaker_id not in profile_map:
                continue

            profile = profile_map[speaker_id]

            # Solo analizar si el perfil tiene suficiente confianza
            if profile.confidence < 0.3:
                continue

            text = dialogue.get("text", "")
            chapter = dialogue.get("chapter", 0)
            position = dialogue.get("position", 0)

            # Detectar cada tipo de desviación
            deviation = self._check_length_deviation(
                profile, text, chapter, position
            )
            if deviation:
                deviations.append(deviation)

            deviation = self._check_formality_deviation(
                profile, text, chapter, position
            )
            if deviation:
                deviations.append(deviation)

            deviation = self._check_filler_deviation(
                profile, text, chapter, position
            )
            if deviation:
                deviations.append(deviation)

            deviation = self._check_punctuation_deviation(
                profile, text, chapter, position
            )
            if deviation:
                deviations.append(deviation)

        logger.info(f"Detectadas {len(deviations)} desviaciones de voz")
        return deviations

    def _check_length_deviation(
        self,
        profile: VoiceProfile,
        text: str,
        chapter: int,
        position: int,
    ) -> Optional[VoiceDeviation]:
        """Verifica si la longitud de la intervención es anómala."""
        words = self._tokenize(text)
        length = len(words)

        expected = profile.metrics.avg_intervention_length
        std = profile.metrics.std_intervention_length

        if std < 1:  # Evitar división por cero o std muy pequeña
            return None

        z_score = abs(length - expected) / std

        if z_score > self.length_threshold:
            severity = self._severity_from_z_score(z_score)
            direction = "más larga" if length > expected else "más corta"

            return VoiceDeviation(
                entity_id=profile.entity_id,
                entity_name=profile.entity_name,
                deviation_type=DeviationType.LENGTH_ANOMALY,
                severity=severity,
                chapter=chapter,
                position=position,
                text=text,
                expected_value=round(expected, 1),
                actual_value=float(length),
                description=(
                    f"Intervención {direction} de lo habitual para {profile.entity_name}. "
                    f"Esperado: ~{expected:.0f} palabras, encontrado: {length} palabras "
                    f"({z_score:.1f} desviaciones estándar)"
                ),
                confidence=min(0.9, profile.confidence),
            )

        return None

    def _check_formality_deviation(
        self,
        profile: VoiceProfile,
        text: str,
        chapter: int,
        position: int,
    ) -> Optional[VoiceDeviation]:
        """Verifica si hay un cambio de registro formal/informal."""
        from .profiles import FORMAL_MARKERS, INFORMAL_MARKERS

        text_lower = text.lower()

        formal_count = sum(1 for m in FORMAL_MARKERS if m in text_lower)
        informal_count = sum(1 for m in INFORMAL_MARKERS if m in text_lower)

        total = formal_count + informal_count
        if total < 2:  # No hay suficientes marcadores
            return None

        actual_formality = formal_count / total
        expected_formality = profile.metrics.formality_score

        diff = abs(actual_formality - expected_formality)

        if diff > self.formality_threshold:
            severity = self._severity_from_diff(diff, 0.3, 0.5)
            direction = "más formal" if actual_formality > expected_formality else "más informal"

            return VoiceDeviation(
                entity_id=profile.entity_id,
                entity_name=profile.entity_name,
                deviation_type=DeviationType.FORMALITY_SHIFT,
                severity=severity,
                chapter=chapter,
                position=position,
                text=text,
                expected_value=round(expected_formality, 2),
                actual_value=round(actual_formality, 2),
                description=(
                    f"Cambio de registro: {profile.entity_name} habla {direction} de lo habitual. "
                    f"Score de formalidad esperado: {expected_formality:.0%}, "
                    f"encontrado: {actual_formality:.0%}"
                ),
                confidence=min(0.85, profile.confidence),
            )

        return None

    def _check_filler_deviation(
        self,
        profile: VoiceProfile,
        text: str,
        chapter: int,
        position: int,
    ) -> Optional[VoiceDeviation]:
        """Verifica si hay un cambio en el uso de muletillas."""
        from .profiles import FILLERS

        text_lower = text.lower()
        words = self._tokenize(text)

        if len(words) < 5:  # Intervención muy corta
            return None

        filler_count = sum(1 for f in FILLERS if f in text_lower)
        actual_ratio = filler_count / len(words)
        expected_ratio = profile.metrics.filler_ratio

        # Calcular diferencia relativa
        if expected_ratio > 0.01:
            relative_diff = abs(actual_ratio - expected_ratio) / expected_ratio
        else:
            relative_diff = actual_ratio * 10  # Si no usa muletillas, cualquier uso es notable

        if relative_diff > self.filler_threshold:
            severity = self._severity_from_diff(relative_diff, 0.5, 1.0)
            direction = "más muletillas" if actual_ratio > expected_ratio else "menos muletillas"

            return VoiceDeviation(
                entity_id=profile.entity_id,
                entity_name=profile.entity_name,
                deviation_type=DeviationType.FILLER_ANOMALY,
                severity=severity,
                chapter=chapter,
                position=position,
                text=text,
                expected_value=round(expected_ratio, 3),
                actual_value=round(actual_ratio, 3),
                description=(
                    f"{profile.entity_name} usa {direction} de lo habitual. "
                    f"Ratio esperado: {expected_ratio:.1%}, encontrado: {actual_ratio:.1%}"
                ),
                confidence=min(0.75, profile.confidence),
            )

        return None

    def _check_punctuation_deviation(
        self,
        profile: VoiceProfile,
        text: str,
        chapter: int,
        position: int,
    ) -> Optional[VoiceDeviation]:
        """Verifica si hay un cambio en patrones de puntuación."""
        exclamations = text.count("!")
        questions = text.count("?")
        ellipsis = text.count("...")

        # Comparar con el perfil (ajustado por intervención)
        expected_exc = profile.metrics.exclamation_ratio
        expected_q = profile.metrics.question_ratio
        expected_ell = profile.metrics.ellipsis_ratio

        deviations = []

        # Verificar exclamaciones
        if expected_exc < 0.5 and exclamations >= 3:
            deviations.append((
                "exclamaciones",
                expected_exc,
                exclamations,
                f"Uso inusual de exclamaciones ({exclamations}!) para un personaje que normalmente usa ~{expected_exc:.1f} por intervención"
            ))

        # Verificar preguntas
        if expected_q < 0.5 and questions >= 3:
            deviations.append((
                "preguntas",
                expected_q,
                questions,
                f"Uso inusual de preguntas ({questions}?) para un personaje que normalmente usa ~{expected_q:.1f} por intervención"
            ))

        # Verificar puntos suspensivos
        if expected_ell < 0.3 and ellipsis >= 3:
            deviations.append((
                "puntos suspensivos",
                expected_ell,
                ellipsis,
                f"Uso inusual de puntos suspensivos ({ellipsis}) para un personaje que normalmente usa ~{expected_ell:.1f} por intervención"
            ))

        if not deviations:
            return None

        # Usar la desviación más significativa
        _, expected, actual, description = max(deviations, key=lambda x: x[2])

        return VoiceDeviation(
            entity_id=profile.entity_id,
            entity_name=profile.entity_name,
            deviation_type=DeviationType.PUNCTUATION_SHIFT,
            severity=DeviationSeverity.LOW,
            chapter=chapter,
            position=position,
            text=text,
            expected_value=expected,
            actual_value=float(actual),
            description=f"{profile.entity_name}: {description}",
            confidence=min(0.7, profile.confidence),
        )

    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto en palabras."""
        import re
        text = re.sub(r'[^\w\sáéíóúüñ]', ' ', text.lower())
        words = text.split()
        return [w for w in words if len(w) > 1]

    def _severity_from_z_score(self, z_score: float) -> DeviationSeverity:
        """Determina severidad basada en z-score."""
        if z_score > 4:
            return DeviationSeverity.HIGH
        elif z_score > 3:
            return DeviationSeverity.MEDIUM
        else:
            return DeviationSeverity.LOW

    def _severity_from_diff(
        self,
        diff: float,
        medium_threshold: float,
        high_threshold: float
    ) -> DeviationSeverity:
        """Determina severidad basada en diferencia."""
        if diff > high_threshold:
            return DeviationSeverity.HIGH
        elif diff > medium_threshold:
            return DeviationSeverity.MEDIUM
        else:
            return DeviationSeverity.LOW


def detect_voice_deviations(
    chapters: List[Dict],
    entities: List[Dict],
    profiles: Optional[List[VoiceProfile]] = None,
) -> Tuple[List[VoiceProfile], List[VoiceDeviation]]:
    """
    Función de conveniencia para detectar desviaciones de voz.

    Args:
        chapters: Lista de capítulos con diálogos
        entities: Lista de entidades del proyecto
        profiles: Perfiles pre-calculados (opcional)

    Returns:
        Tupla de (perfiles, desviaciones)
    """
    # Extraer diálogos
    dialogues = []
    for chapter in chapters:
        chapter_dialogues = chapter.get("dialogues", [])
        for d in chapter_dialogues:
            dialogues.append({
                "text": d.get("text", ""),
                "speaker_id": d.get("speaker_id"),
                "chapter": chapter.get("number", 0),
                "position": d.get("position", 0),
            })

    # Construir perfiles si no se proporcionan
    if profiles is None:
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entities)

    # Detectar desviaciones
    detector = VoiceDeviationDetector()
    deviations = detector.detect_deviations(profiles, dialogues)

    return profiles, deviations
