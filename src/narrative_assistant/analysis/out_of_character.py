"""
Detección de comportamiento fuera de personaje (out-of-character).

Compara las acciones, habla y sentimiento de un personaje en un fragmento
concreto contra su perfil establecido. Genera alertas cuando un personaje
se comporta de forma inconsistente sin justificación narrativa.

Tipos de desviaciones detectadas:
- Registro de habla incoherente (formal/informal)
- Acciones atípicas respecto al patrón habitual
- Cambio emocional brusco sin transición
- Aparición en ubicaciones inesperadas
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from .character_profiling import (
    CharacterProfile,
    CharacterRole,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
)

logger = logging.getLogger(__name__)


class DeviationType(Enum):
    """Tipo de desviación del perfil del personaje."""

    SPEECH_REGISTER = "speech_register"  # Cambio de formalidad
    ACTION_ATYPICAL = "action_atypical"  # Acción fuera de patrón
    EMOTION_SHIFT = "emotion_shift"  # Cambio emocional brusco
    LOCATION_UNEXPECTED = "location_unexpected"  # Lugar inesperado
    AGENCY_SHIFT = "agency_shift"  # Cambio en agentividad


class DeviationSeverity(Enum):
    """Severidad de la desviación."""

    INFO = "info"  # Desviación menor, posiblemente intencional
    WARNING = "warning"  # Desviación notable
    ALERT = "alert"  # Desviación significativa que requiere revisión


@dataclass
class OutOfCharacterEvent:
    """Evento de comportamiento fuera de personaje."""

    entity_id: int
    entity_name: str
    deviation_type: DeviationType
    severity: DeviationSeverity
    description: str
    expected: str  # Lo que se esperaría según el perfil
    actual: str  # Lo que se encontró
    chapter: int | None = None
    excerpt: str = ""
    confidence: float = 0.7
    is_intentional: bool = False  # Si parece una decisión narrativa deliberada

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "type": self.deviation_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
            "chapter": self.chapter,
            "excerpt": self.excerpt[:200] if self.excerpt else "",
            "confidence": round(self.confidence, 3),
            "possibly_intentional": self.is_intentional,
        }


@dataclass
class OutOfCharacterReport:
    """Reporte de desviaciones de personaje."""

    events: list[OutOfCharacterEvent] = field(default_factory=list)
    characters_analyzed: int = 0
    total_deviations: int = 0

    @property
    def alerts(self) -> list[OutOfCharacterEvent]:
        """Desviaciones de alta severidad."""
        return [e for e in self.events if e.severity == DeviationSeverity.ALERT]

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "characters_analyzed": self.characters_analyzed,
            "total_deviations": self.total_deviations,
            "alerts_count": len(self.alerts),
        }


# Umbrales para detección
FORMALITY_DEVIATION_THRESHOLD = 0.35  # Diferencia mínima en formalidad
SENTIMENT_DEVIATION_THRESHOLD = 0.5  # Diferencia mínima en sentimiento
AGENCY_DEVIATION_THRESHOLD = 0.4  # Diferencia mínima en agentividad
MIN_PROFILE_MENTIONS = 5  # Menciones mínimas para confiar en el perfil

# Marcadores de transición narrativa que justifican un cambio
TRANSITION_MARKERS = {
    "de repente", "inesperadamente", "sin previo aviso", "de pronto",
    "para su sorpresa", "contra todo pronóstico", "sin esperarlo",
    "algo cambió", "todo cambió", "ya no era", "dejó de ser",
    "se transformó", "se convirtió", "nunca antes",
}


class OutOfCharacterDetector:
    """
    Detecta comportamiento fuera de personaje comparando
    fragmentos contra el perfil establecido.
    """

    def __init__(
        self,
        formality_threshold: float = FORMALITY_DEVIATION_THRESHOLD,
        sentiment_threshold: float = SENTIMENT_DEVIATION_THRESHOLD,
    ):
        self.formality_threshold = formality_threshold
        self.sentiment_threshold = sentiment_threshold

    def detect(
        self,
        profiles: list[CharacterProfile],
        chapter_dialogues: dict[int, list[dict]] | None = None,
        chapter_texts: dict[int, str] | None = None,
    ) -> OutOfCharacterReport:
        """
        Detecta desviaciones en todos los personajes.

        Args:
            profiles: Perfiles construidos por CharacterProfiler
            chapter_dialogues: Diálogos organizados por capítulo
                              {chapter: [{speaker_id, text}]}
            chapter_texts: Textos de capítulos para análisis contextual

        Returns:
            OutOfCharacterReport con las desviaciones detectadas.
        """
        report = OutOfCharacterReport()

        # Solo analizar personajes con perfil suficiente
        analyzable = [
            p for p in profiles
            if p.presence.total_mentions >= MIN_PROFILE_MENTIONS
            and p.role in (
                CharacterRole.PROTAGONIST,
                CharacterRole.DEUTERAGONIST,
                CharacterRole.SUPPORTING,
            )
        ]

        report.characters_analyzed = len(analyzable)

        for profile in analyzable:
            events = []

            # 1. Desviación de registro de habla
            if chapter_dialogues:
                events.extend(
                    self._check_speech_register(profile, chapter_dialogues)
                )

            # 2. Desviación emocional
            if chapter_texts:
                events.extend(
                    self._check_emotion_shift(profile, chapter_texts)
                )

            # 3. Desviación de agentividad
            if chapter_texts:
                events.extend(
                    self._check_agency_shift(profile, chapter_texts)
                )

            report.events.extend(events)

        report.total_deviations = len(report.events)

        # Marcar como posiblemente intencional si hay marcadores de transición
        if chapter_texts:
            self._mark_intentional_transitions(report.events, chapter_texts)

        logger.info(
            f"OOC: {report.total_deviations} desviaciones en "
            f"{report.characters_analyzed} personajes "
            f"({len(report.alerts)} alertas)"
        )

        return report

    def _check_speech_register(
        self,
        profile: CharacterProfile,
        chapter_dialogues: dict[int, list[dict]],
    ) -> list[OutOfCharacterEvent]:
        """Verifica coherencia del registro de habla por capítulo."""
        events = []
        baseline_formality = profile.speech.formality_score

        # Si no hay datos de habla suficientes, no analizar
        if profile.speech.total_interventions < 3:
            return events

        from ..voice.profiles import FORMAL_MARKERS, INFORMAL_MARKERS

        for chapter, dialogues in chapter_dialogues.items():
            # Filtrar diálogos de este personaje
            char_dialogues = [
                d["text"] for d in dialogues
                if d.get("speaker_id") == profile.entity_id and d.get("text")
            ]

            if len(char_dialogues) < 2:
                continue

            # Calcular formalidad local
            all_text = " ".join(char_dialogues).lower()
            words = all_text.split()
            formal = sum(1 for w in words if w in FORMAL_MARKERS)
            informal = sum(1 for w in words if w in INFORMAL_MARKERS)
            total = formal + informal

            if total < 3:
                continue

            local_formality = formal / total

            deviation = abs(local_formality - baseline_formality)
            if deviation >= self.formality_threshold:
                direction = "más formal" if local_formality > baseline_formality else "más informal"
                severity = (
                    DeviationSeverity.ALERT if deviation > 0.5
                    else DeviationSeverity.WARNING
                )

                events.append(
                    OutOfCharacterEvent(
                        entity_id=profile.entity_id,
                        entity_name=profile.entity_name,
                        deviation_type=DeviationType.SPEECH_REGISTER,
                        severity=severity,
                        description=(
                            f"{profile.entity_name} habla {direction} de lo habitual "
                            f"en capítulo {chapter}"
                        ),
                        expected=f"formalidad={baseline_formality:.2f}",
                        actual=f"formalidad={local_formality:.2f}",
                        chapter=chapter,
                        excerpt=char_dialogues[0][:150] if char_dialogues else "",
                        confidence=min(0.9, 0.5 + deviation),
                    )
                )

        return events

    def _check_emotion_shift(
        self,
        profile: CharacterProfile,
        chapter_texts: dict[int, str],
    ) -> list[OutOfCharacterEvent]:
        """Verifica cambios emocionales bruscos entre capítulos."""
        events = []
        baseline = profile.sentiment.avg_sentiment

        # Calcular sentimiento por capítulo
        name_lower = profile.entity_name.lower()
        chapter_sentiments: dict[int, float] = {}

        for chapter, text in chapter_texts.items():
            sentences = re.split(r"[.!?]+", text)
            pos = 0
            neg = 0
            mentions = 0

            for sentence in sentences:
                sl = sentence.lower()
                if name_lower not in sl:
                    continue
                mentions += 1
                words = set(sl.split())
                pos += len(words & POSITIVE_WORDS)
                neg += len(words & NEGATIVE_WORDS)

            if mentions >= 2:
                total = pos + neg
                if total > 0:
                    chapter_sentiments[chapter] = (pos - neg) / total

        # Detectar cambios bruscos entre capítulos consecutivos
        sorted_chapters = sorted(chapter_sentiments.keys())
        for i in range(1, len(sorted_chapters)):
            prev_ch = sorted_chapters[i - 1]
            curr_ch = sorted_chapters[i]
            prev_sent = chapter_sentiments[prev_ch]
            curr_sent = chapter_sentiments[curr_ch]

            shift = abs(curr_sent - prev_sent)
            if shift >= self.sentiment_threshold:
                direction = "positivo" if curr_sent > prev_sent else "negativo"
                events.append(
                    OutOfCharacterEvent(
                        entity_id=profile.entity_id,
                        entity_name=profile.entity_name,
                        deviation_type=DeviationType.EMOTION_SHIFT,
                        severity=DeviationSeverity.WARNING,
                        description=(
                            f"{profile.entity_name}: cambio emocional brusco "
                            f"hacia {direction} entre capítulos {prev_ch} y {curr_ch}"
                        ),
                        expected=f"sentimiento≈{prev_sent:+.2f}",
                        actual=f"sentimiento={curr_sent:+.2f}",
                        chapter=curr_ch,
                        confidence=min(0.85, 0.5 + shift * 0.5),
                    )
                )

        return events

    def _check_agency_shift(
        self,
        profile: CharacterProfile,
        chapter_texts: dict[int, str],
    ) -> list[OutOfCharacterEvent]:
        """Verifica cambios en agentividad (activo/pasivo)."""
        events = []
        baseline_agency = profile.actions.agency_score

        if profile.actions.action_count < 5:
            return events

        # Agentividad global significativamente diferente requiere
        # análisis por capítulo, pero el patrón simple ya es útil
        # para alertar sobre personajes que cambian drásticamente
        if baseline_agency > 0.8 and profile.sentiment.avg_sentiment < -0.3:
            events.append(
                OutOfCharacterEvent(
                    entity_id=profile.entity_id,
                    entity_name=profile.entity_name,
                    deviation_type=DeviationType.AGENCY_SHIFT,
                    severity=DeviationSeverity.INFO,
                    description=(
                        f"{profile.entity_name}: personaje muy activo "
                        f"(agentividad={baseline_agency:.2f}) con sentimiento "
                        f"predominantemente negativo ({profile.sentiment.avg_sentiment:+.2f})"
                    ),
                    expected="coherencia agentividad-sentimiento",
                    actual="posible conflicto interno no resuelto narrativamente",
                    confidence=0.5,
                )
            )

        return events

    def _mark_intentional_transitions(
        self,
        events: list[OutOfCharacterEvent],
        chapter_texts: dict[int, str],
    ) -> None:
        """Marca desviaciones como posiblemente intencionales si hay marcadores."""
        for event in events:
            if event.chapter is None:
                continue

            text = chapter_texts.get(event.chapter, "").lower()
            name_lower = event.entity_name.lower()

            # Buscar marcadores de transición cerca del nombre del personaje
            for marker in TRANSITION_MARKERS:
                if marker in text:
                    # Verificar proximidad al personaje
                    marker_pos = text.find(marker)
                    name_pos = text.find(name_lower)
                    if name_pos >= 0 and abs(marker_pos - name_pos) < 500:
                        event.is_intentional = True
                        event.severity = DeviationSeverity.INFO
                        break
