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
# Subgrupo 4: Meta-narrativos + Eventos básicos Tier 1
# ============================================================================

class ChapterBoundaryDetector:
    """Detecta inicio y fin de capítulo."""

    CHAPTER_START_PATTERNS = [
        r"^Capítulo \d+",
        r"^CAPÍTULO [IVX]+",
        r"^\d+\.",
        r"^Parte \d+",
    ]

    CHAPTER_END_PATTERNS = [
        r"\bFin del capítulo\b",
        r"\bContinuará\b",
        r"^\* \* \*$",
    ]

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta inicio y fin de capítulo."""
        events = []

        # Detectar inicio (primeras líneas)
        first_lines = "\n".join(text.split("\n")[:5])
        for pattern in self.CHAPTER_START_PATTERNS:
            if re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE):
                events.append(DetectedEvent(
                    event_type=EventType.CHAPTER_START,
                    description="Inicio de capítulo",
                    confidence=0.95,
                    start_char=0,
                    end_char=min(100, len(text)),
                ))
                break

        # Detectar fin (últimas líneas)
        last_lines = "\n".join(text.split("\n")[-5:])
        for pattern in self.CHAPTER_END_PATTERNS:
            if re.search(pattern, last_lines, re.IGNORECASE | re.MULTILINE):
                events.append(DetectedEvent(
                    event_type=EventType.CHAPTER_END,
                    description="Fin de capítulo",
                    confidence=0.9,
                    start_char=max(0, len(text) - 100),
                    end_char=len(text),
                ))
                break

        return events


class BasicCharacterEventsDetector:
    """Detecta eventos básicos de personajes (primera aparición, retorno, muerte)."""

    DEATH_VERBS = ["morir", "fallecer", "expirar", "perecer", "sucumbir", "asesinar", "matar"]
    DEATH_PATTERNS = [
        r"\bmurió\b",
        r"\bfalleció\b",
        r"\bmataron\b",
        r"\bperdió la vida\b",
        r"\bsu muerte\b",
        r"\bya no viv",
        r"\bdejó de existir\b",
        r"\bexhaló su último suspiro\b",
    ]

    RETURN_PATTERNS = [
        r"\bvolvió\b",
        r"\bregresó\b",
        r"\bha vuelto\b",
        r"\bde vuelta\b",
        r"\bretornó\b",
        r"\breapareció\b",
        r"\bsurge de nuevo\b",
    ]

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """Detecta primera aparición, retorno y muerte de personajes."""
        events = []

        # DEATH: Detectar muerte
        for token in doc:
            if token.lemma_.lower() in self.DEATH_VERBS:
                sent = token.sent
                # Buscar sujeto (el que muere)
                subject = None
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = child.text
                        break

                description = f"Muerte: {sent.text[:60]}..."
                if subject:
                    description = f"Muerte de {subject}"

                events.append(DetectedEvent(
                    event_type=EventType.DEATH,
                    description=description,
                    confidence=0.75,
                    start_char=sent.start_char,
                    end_char=sent.end_char,
                    metadata={"subject": subject or ""},
                ))

        # DEATH: Detectar por patrones adicionales
        for pattern in self.DEATH_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                events.append(DetectedEvent(
                    event_type=EventType.DEATH,
                    description=f"Muerte detectada: {context[:60]}...",
                    confidence=0.7,
                    start_char=match.start(),
                    end_char=match.end(),
                ))

        # RETURN: Detectar retorno de personaje
        for pattern in self.RETURN_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                events.append(DetectedEvent(
                    event_type=EventType.RETURN,
                    description=f"Retorno: {context[:60]}...",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=min(match.end() + 100, len(text)),
                ))

        # FIRST_APPEARANCE: Detectar por contexto de presentación
        # Patrones comunes: "Este es X", "Conoce a X", "Se presentó X"
        first_appearance_patterns = [
            r"\b(conoce a|conocer a|se presentó|este es|esta es|apareció por primera vez)\b",
            r"\b(un nuevo|una nueva|llegó)\b.*\b(personaje|hombre|mujer|chico|chica|niño|niña)\b",
        ]

        for pattern in first_appearance_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context_start = max(0, match.start() - 30)
                context_end = min(len(text), match.end() + 70)
                context = text[context_start:context_end]

                events.append(DetectedEvent(
                    event_type=EventType.FIRST_APPEARANCE,
                    description=f"Primera aparición: {context[:60]}...",
                    confidence=0.6,
                    start_char=match.start(),
                    end_char=min(match.end() + 100, len(text)),
                ))

        return events


class PowerShiftDetector:
    """Detecta cambios en el balance de poder entre personajes o grupos."""

    POWER_SHIFT_PATTERNS = [
        r"\b(tom[oóaóe]\w* el (control|mando|poder)|asumi[oóe]\w* el (control|mando|liderazgo))\b",
        r"\b(derroc[oóaóe]\w*|destron[oóaóe]\w*|usurp[oóaóe]\w*)\b",
        r"\b(se convirti[oóe]\w* en (rey|reina|líder|jefe|comandante))\b",
        r"\b(perdi[oóe]\w* (el poder|su autoridad|el control))\b",
        r"\b(nuevo|nueva) (rey|reina|líder|emperador|gobernante)\b",
        r"\b(cambio de (poder|liderazgo|mando))\b",
        r"\b(ascendi[oóe]\w* al (trono|poder))\b",
    ]

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta cambios de poder."""
        events = []

        for pattern in self.POWER_SHIFT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                events.append(DetectedEvent(
                    event_type=EventType.POWER_SHIFT,
                    description=f"Cambio de poder: {context[:60]}...",
                    confidence=0.75,
                    start_char=match.start(),
                    end_char=min(match.end() + 100, len(text)),
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

    # Subgrupo 4: Meta-narrativos
    chapter_boundary_detector = ChapterBoundaryDetector()
    events.extend(chapter_boundary_detector.detect(text))

    power_shift_detector = PowerShiftDetector()
    events.extend(power_shift_detector.detect(text))

    # Eventos básicos de personajes (Tier 1, pero se detectan aquí)
    basic_character_detector = BasicCharacterEventsDetector()
    events.extend(basic_character_detector.detect(doc, text))

    logger.debug(f"Tier 2: {len(events)} eventos detectados")
    return events
