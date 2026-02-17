"""
Sistema de rastreo de continuidad entre eventos.

Detecta inconsistencias cuando eventos esperados no ocurren:
- Promesas sin cumplir/romper
- Heridas sin curación
- Objetos perdidos sin recuperación
- Flashbacks sin cerrar
- Etc.

Genera alertas de continuidad narrativa.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .event_detection import DetectedEvent
from .event_types import EVENT_PAIRS, EventType, get_paired_event

logger = logging.getLogger(__name__)


@dataclass
class EventContinuityIssue:
    """
    Problema de continuidad entre eventos.

    Representa una inconsistencia detectada cuando falta el evento par esperado.
    """

    event_type: EventType
    paired_type: EventType
    description: str
    severity: str  # "critical", "high", "medium", "low"
    source_events: list[DetectedEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EventContinuityTracker:
    """
    Rastreador de continuidad entre eventos paired.

    Mantiene estado de eventos abiertos (sin par) y detecta inconsistencias.
    """

    def __init__(self):
        """Inicializa el tracker."""
        # Estado de eventos abiertos por tipo
        # {EventType: [list of DetectedEvent]}
        self.open_events: dict[EventType, list[DetectedEvent]] = {}

        # Issues detectados
        self.issues: list[EventContinuityIssue] = []

        # Inicializar contadores para pares
        for pair_start, pair_end in EVENT_PAIRS:
            self.open_events[pair_start] = []
            self.open_events[pair_end] = []

    def track_event(self, event: DetectedEvent) -> None:
        """
        Registra un evento y verifica continuidad.

        Args:
            event: Evento detectado
        """
        event_type = event.event_type

        # Verificar si este evento cierra un evento previo
        paired_type = get_paired_event(event_type)
        if paired_type and paired_type in self.open_events:
            open_paired = self.open_events[paired_type]

            if open_paired:
                # Intentar emparejar con evento abierto
                matched = self._try_match_event(event, open_paired)
                if matched:
                    logger.debug(
                        f"Evento {event_type.value} emparejado con {paired_type.value}"
                    )
                    return

        # Si no cerró ningún evento previo, añadir como abierto
        if event_type in self.open_events:
            self.open_events[event_type].append(event)
            logger.debug(f"Evento {event_type.value} registrado como abierto")

    def _try_match_event(
        self, event: DetectedEvent, open_events: list[DetectedEvent]
    ) -> bool:
        """
        Intenta emparejar un evento con uno abierto.

        Args:
            event: Evento actual
            open_events: Lista de eventos abiertos del tipo paired

        Returns:
            True si se emparejó exitosamente
        """
        # Buscar evento compatible
        for i, open_event in enumerate(open_events):
            if self._events_match(event, open_event):
                # Emparejar: remover de abiertos
                open_events.pop(i)
                return True

        return False

    def _events_match(self, event1: DetectedEvent, event2: DetectedEvent) -> bool:
        """
        Verifica si dos eventos son compatibles para emparejarse.

        Criterios:
        - Mismo sujeto/entidad (si está en metadata)
        - Mismo objeto (si aplica)
        - Proximidad temporal razonable
        """
        # Verificar entidades involucradas
        if event1.entity_ids and event2.entity_ids:
            # Al menos una entidad en común
            if not set(event1.entity_ids).intersection(set(event2.entity_ids)):
                return False

        # Verificar sujeto en metadata (para eventos sin entity_ids)
        subject1 = event1.metadata.get("subject")
        subject2 = event2.metadata.get("subject")
        if subject1 and subject2:
            if subject1.lower() != subject2.lower():
                return False

        # Verificar objeto (para ACQUISITION/LOSS)
        obj1 = event1.metadata.get("object")
        obj2 = event2.metadata.get("object")
        if obj1 and obj2:
            # Coincidencia parcial (para "espada ancestral" vs "espada")
            if obj1.lower() not in obj2.lower() and obj2.lower() not in obj1.lower():
                return False

        return True

    def check_continuity(self) -> list[EventContinuityIssue]:
        """
        Verifica la continuidad al final del análisis.

        Detecta eventos abiertos sin cerrar como inconsistencias.

        Returns:
            Lista de issues de continuidad
        """
        self.issues = []

        for event_type, open_events in self.open_events.items():
            if not open_events:
                continue

            paired_type = get_paired_event(event_type)
            if not paired_type:
                continue

            # Determinar severidad según el tipo de evento
            severity = self._get_issue_severity(event_type)

            # Crear issue por cada evento sin cerrar
            for event in open_events:
                description = self._build_issue_description(event, paired_type)

                issue = EventContinuityIssue(
                    event_type=event_type,
                    paired_type=paired_type,
                    description=description,
                    severity=severity,
                    source_events=[event],
                    metadata={
                        "subject": event.metadata.get("subject"),
                        "object": event.metadata.get("object"),
                        "start_char": event.start_char,
                    }
                )
                self.issues.append(issue)

        logger.info(f"Continuity check: {len(self.issues)} issues detectados")
        return self.issues

    def _get_issue_severity(self, event_type: EventType) -> str:
        """
        Determina la severidad de un issue según el tipo de evento.

        Args:
            event_type: Tipo de evento sin cerrar

        Returns:
            Severidad: "critical", "high", "medium", "low"
        """
        critical_events = [
            EventType.FLASHBACK_START,  # Flashback sin cerrar es crítico
            EventType.INJURY,  # Herida sin mencionar curación (puede ser grave)
        ]

        high_events = [
            EventType.PROMISE,  # Promesa sin cumplir/romper
            EventType.ACQUISITION,  # Objeto adquirido sin usar/perder
        ]

        if event_type in critical_events:
            return "critical"
        elif event_type in high_events:
            return "high"
        else:
            return "medium"

    def _build_issue_description(
        self, event: DetectedEvent, expected_type: EventType
    ) -> str:
        """
        Construye descripción del issue de continuidad.

        Args:
            event: Evento abierto
            expected_type: Tipo de evento esperado (pair)

        Returns:
            Descripción del issue
        """
        event_type = event.event_type

        # Mensajes específicos por tipo
        messages = {
            EventType.PROMISE: "Promesa sin cumplir ni romper explícitamente",
            EventType.INJURY: "Herida sin mención de curación posterior",
            EventType.ACQUISITION: "Objeto obtenido sin uso o pérdida posterior",
            EventType.FLASHBACK_START: "Flashback iniciado sin cierre explícito",
            EventType.CONFLICT_START: "Conflicto iniciado sin resolución",
            EventType.SEPARATION: "Separación de personajes sin reencuentro",
            EventType.LIE: "Mentira sin confesión posterior",
            EventType.ALLIANCE: "Alianza formada sin mención de traición o finalización",
        }

        base_msg = messages.get(
            event_type,
            f"{event_type.value} sin {expected_type.value} correspondiente"
        )

        # Añadir contexto del evento
        subject = event.metadata.get("subject")
        obj = event.metadata.get("object")

        if subject:
            base_msg += f" (personaje: {subject})"
        if obj:
            base_msg += f" (objeto: {obj})"

        return base_msg

    def reset(self) -> None:
        """Resetea el estado del tracker."""
        for key in self.open_events:
            self.open_events[key] = []
        self.issues = []


def track_continuity_in_chapters(
    events_by_chapter: dict[int, list[DetectedEvent]]
) -> list[EventContinuityIssue]:
    """
    Rastrea continuidad a través de múltiples capítulos.

    Args:
        events_by_chapter: Diccionario {chapter_number: [events]}

    Returns:
        Lista de issues de continuidad detectados
    """
    tracker = EventContinuityTracker()

    # Procesar eventos en orden de capítulos
    for chapter_num in sorted(events_by_chapter.keys()):
        events = events_by_chapter[chapter_num]
        for event in events:
            tracker.track_event(event)

    # Verificar continuidad al final
    issues = tracker.check_continuity()

    logger.info(
        f"Rastreo de continuidad: {len(issues)} inconsistencias en "
        f"{len(events_by_chapter)} capítulos"
    )

    return issues
