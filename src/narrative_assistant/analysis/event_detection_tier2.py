"""
Detectores de eventos Tier 2 (Prioridad Media).

Eventos de enriquecimiento narrativo:
- Relaciones entre personajes (5 eventos)
- Transformaciones narrativas (4 eventos)
- Eventos de trama (4 eventos)
- Meta-narrativos (2 eventos)
"""

import logging
import re
from dataclasses import dataclass

from spacy.tokens import Doc

from .event_detection import DetectedEvent
from .event_types import EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Patrones Tier 2
# ============================================================================

# Subgrupo 1: Relaciones entre personajes
MEETING_PATTERNS = [
    r"\b(conoció|conocer)\b",
    r"\b(primer|primera) (vez|encuentro)\b",
    r"\b(se encontraron|se vieron) por primera vez\b",
]

REUNION_PATTERNS = [
    r"\b(volvió a ver|volvieron a encontrarse)\b",
    r"\b(reencuentro|reencontró)\b",
    r"\b(de vuelta|de regreso)\b",
]

SEPARATION_PATTERNS = [
    r"\b(se separaron|se despidieron)\b",
    r"\b(partió|marchó|se fue)\b",
    r"\b(adiós|despedida)\b",
]

CONFLICT_START_PATTERNS = [
    r"\b(discutieron|pelearon|se enfrentaron)\b",
    r"\b(conflicto|disputa|riña)\b",
    r"\bdesacuerdo\b",
]

CONFLICT_RESOLUTION_PATTERNS = [
    r"\b(se reconciliaron|hicieron las paces)\b",
    r"\b(resolvieron|solucionaron) (el|la) (conflicto|disputa)\b",
    r"\b(perdonó|perdonar)\b",
]

# Subgrupo 2: Transformaciones narrativas
TRANSFORMATION_VERBS = ["transformar", "convertir", "cambiar", "evolucionar"]
SOCIAL_CHANGE_MARKERS = [
    r"\b(ascendió|promovieron|nombrado|coronado)\b",
    r"\b(perdió (su|el) título|destituido|exiliado)\b",
]

LOCATION_CHANGE_MARKERS = [
    r"\b(llegó a|arribó|alcanzó)\b",
    r"\b(nueva ciudad|nuevo lugar|destino)\b",
]

POWER_SHIFT_MARKERS = [
    r"\b(tomó el poder|asumió el mando|derrocó)\b",
    r"\b(balance de poder|equilibrio)\b",
]

# Subgrupo 3: Eventos de trama
CLIMAX_MARKERS = [
    r"\b(momento culminante|punto álgido)\b",
    r"\b(batalla final|enfrentamiento definitivo)\b",
]

TWIST_MARKERS = [
    r"\b(giro inesperado|sorpresa|resulta que)\b",
    r"\b(no era quien|en realidad)\b",
]

FORESHADOWING_MARKERS = [
    r"\b(presagio|señal|augurio)\b",
    r"\b(algo malo (iba a|podría) pasar)\b",
]

CALLBACK_MARKERS = [
    r"\b(como (antes|ya) (mencioné|dije|vimos))\b",
    r"\b(recordó (cuando|que))\b",
]


# ============================================================================
# Detectores Tier 2
# ============================================================================

class FirstMeetingDetector:
    """Detecta primer encuentro entre personajes."""

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """Detecta primeros encuentros."""
        events = []

        # Buscar verbos de conocer
        for token in doc:
            if token.lemma_.lower() == "conocer":
                sent = token.sent
                events.append(DetectedEvent(
                    event_type=EventType.FIRST_MEETING,
                    description=f"Primer encuentro: {sent.text[:50]}...",
                    confidence=0.6,
                    start_char=sent.start_char,
                    end_char=sent.end_char,
                ))

        # Buscar patrones explícitos
        for pattern in MEETING_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if not any(e.start_char <= match.start() <= e.end_char for e in events):
                    events.append(DetectedEvent(
                        event_type=EventType.FIRST_MEETING,
                        description=f"Primer encuentro: {match.group()}",
                        confidence=0.7,
                        start_char=match.start(),
                        end_char=match.end(),
                    ))

        return events


class SeparationReunionDetector:
    """Detecta separaciones y reencuentros."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta separaciones/reencuentros."""
        events = []

        # Separaciones
        for pattern in SEPARATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.SEPARATION,
                    description=f"Separación: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # Reencuentros
        for pattern in REUNION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.REUNION,
                    description=f"Reencuentro: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        return events


class ConflictDetector:
    """Detecta inicio y resolución de conflictos."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta conflictos y resoluciones."""
        events = []

        # Inicio de conflicto
        for pattern in CONFLICT_START_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.CONFLICT_START,
                    description=f"Inicio de conflicto: {match.group()}",
                    confidence=0.7,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # Resolución de conflicto
        for pattern in CONFLICT_RESOLUTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.CONFLICT_RESOLUTION,
                    description=f"Resolución de conflicto: {match.group()}",
                    confidence=0.7,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        return events


class TransformationDetector:
    """Detecta transformaciones de personajes."""

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """Detecta transformaciones."""
        events = []

        for token in doc:
            if token.lemma_.lower() in TRANSFORMATION_VERBS:
                sent = token.sent
                events.append(DetectedEvent(
                    event_type=EventType.CHARACTER_TRANSFORMATION,
                    description=f"Transformación: {sent.text[:60]}...",
                    confidence=0.6,
                    start_char=sent.start_char,
                    end_char=sent.end_char,
                ))

        return events


class SocialChangeDetector:
    """Detecta cambios de estatus social."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta cambios sociales."""
        events = []

        for pattern in SOCIAL_CHANGE_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.SOCIAL_CHANGE,
                    description=f"Cambio social: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        return events


class LocationChangeDetector:
    """Detecta cambios de escenario principal."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta cambios de localización."""
        events = []

        for pattern in LOCATION_CHANGE_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.LOCATION_CHANGE,
                    description=f"Cambio de escenario: {match.group()}",
                    confidence=0.6,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        return events


class PlotEventDetector:
    """Detecta eventos clave de trama (climax, twist, etc.)."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta eventos de trama."""
        events = []

        # Climax
        for pattern in CLIMAX_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.CLIMAX,
                    description=f"Clímax: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # Twist
        for pattern in TWIST_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.TWIST,
                    description=f"Giro argumental: {match.group()}",
                    confidence=0.6,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # Foreshadowing
        for pattern in FORESHADOWING_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.FORESHADOWING,
                    description=f"Prefiguración: {match.group()}",
                    confidence=0.55,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # Callback
        for pattern in CALLBACK_MARKERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.CALLBACK,
                    description=f"Referencia: {match.group()}",
                    confidence=0.6,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        return events


# ============================================================================
# Función helper para detectar todos los eventos Tier 2
# ============================================================================

def detect_tier2_events(doc: Doc, text: str) -> list[DetectedEvent]:
    """
    Detecta todos los eventos Tier 2 en un texto.

    Args:
        doc: Documento spaCy procesado
        text: Texto original

    Returns:
        Lista de eventos Tier 2 detectados
    """
    events = []

    # Subgrupo 1: Relaciones
    first_meeting_detector = FirstMeetingDetector()
    events.extend(first_meeting_detector.detect(doc, text))

    separation_reunion_detector = SeparationReunionDetector()
    events.extend(separation_reunion_detector.detect(text))

    conflict_detector = ConflictDetector()
    events.extend(conflict_detector.detect(text))

    # Subgrupo 2: Transformaciones
    transformation_detector = TransformationDetector()
    events.extend(transformation_detector.detect(doc, text))

    social_change_detector = SocialChangeDetector()
    events.extend(social_change_detector.detect(text))

    location_change_detector = LocationChangeDetector()
    events.extend(location_change_detector.detect(text))

    # Subgrupo 3: Trama
    plot_detector = PlotEventDetector()
    events.extend(plot_detector.detect(text))

    logger.debug(f"Tier 2: {len(events)} eventos detectados")
    return events
