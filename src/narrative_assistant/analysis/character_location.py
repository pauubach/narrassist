"""
Tracking de ubicación de personajes.

Detecta movimientos de personajes entre ubicaciones y verifica
que no aparezcan en dos lugares simultáneamente.

Genera alertas de tipo CONSISTENCY cuando:
- Un personaje está en ubicación A en capítulo N
- Y aparece en ubicación B (incompatible) en el mismo momento narrativo
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ..core.result import Result
from ..core.errors import NLPError

logger = logging.getLogger(__name__)


class LocationChangeType(Enum):
    """Tipo de cambio de ubicación."""
    ARRIVAL = "arrival"          # Llegada a un lugar
    DEPARTURE = "departure"      # Salida de un lugar
    TRANSITION = "transition"    # Transición entre lugares
    PRESENCE = "presence"        # Presencia en un lugar (sin movimiento explícito)


@dataclass
class LocationEvent:
    """
    Evento de ubicación de un personaje.

    Representa un cambio de ubicación o presencia en un lugar.
    """
    entity_id: int
    entity_name: str
    location_id: Optional[int]   # ID de entidad LOC si existe
    location_name: str           # Nombre del lugar
    chapter: int
    start_char: int
    end_char: int
    excerpt: str
    change_type: LocationChangeType
    confidence: float = 0.8

    # Metadatos
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "chapter": self.chapter,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "excerpt": self.excerpt,
            "change_type": self.change_type.value,
            "confidence": self.confidence,
        }


@dataclass
class LocationInconsistency:
    """
    Inconsistencia de ubicación detectada.

    Un personaje aparece en dos lugares incompatibles en el mismo
    momento narrativo.
    """
    entity_id: int
    entity_name: str
    location1_name: str
    location1_chapter: int
    location1_excerpt: str
    location2_name: str
    location2_chapter: int
    location2_excerpt: str
    explanation: str
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "location1_name": self.location1_name,
            "location1_chapter": self.location1_chapter,
            "location1_excerpt": self.location1_excerpt,
            "location2_name": self.location2_name,
            "location2_chapter": self.location2_chapter,
            "location2_excerpt": self.location2_excerpt,
            "explanation": self.explanation,
            "confidence": self.confidence,
        }


@dataclass
class CharacterLocationReport:
    """
    Reporte de ubicaciones de personajes.
    """
    project_id: int
    location_events: list[LocationEvent] = field(default_factory=list)
    inconsistencies: list[LocationInconsistency] = field(default_factory=list)
    # Mapa: entity_id -> última ubicación conocida
    current_locations: dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "location_events": [e.to_dict() for e in self.location_events],
            "inconsistencies": [i.to_dict() for i in self.inconsistencies],
            "inconsistencies_count": len(self.inconsistencies),
            "current_locations": self.current_locations,
            "characters_tracked": len(set(e.entity_id for e in self.location_events)),
            "locations_found": len(set(e.location_name for e in self.location_events)),
        }


class CharacterLocationAnalyzer:
    """
    Analizador de ubicaciones de personajes.

    Detecta movimientos entre ubicaciones y posibles inconsistencias.
    """

    # Patrones de llegada
    ARRIVAL_PATTERNS = [
        r"(?P<name>\w+)\s+(?:llegó|arribó|entró)\s+(?:a|en)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
        r"(?P<name>\w+)\s+(?:apareció|se\s+presentó)\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
        r"cuando\s+(?P<name>\w+)\s+(?:llegó|entró)\s+(?:a|en)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
    ]

    # Patrones de salida
    DEPARTURE_PATTERNS = [
        r"(?P<name>\w+)\s+(?:salió|partió|se\s+fue|abandonó)\s+(?:de\s+)?(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
        r"(?P<name>\w+)\s+(?:dejó)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
    ]

    # Patrones de presencia
    PRESENCE_PATTERNS = [
        r"(?P<name>\w+)\s+(?:estaba|se\s+encontraba|permanecía)\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
        r"en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)[,\s]+(?P<name>\w+)\s+(?:esperaba|miraba|observaba)",
    ]

    # Patrones de transición
    TRANSITION_PATTERNS = [
        r"(?P<name>\w+)\s+(?:viajó|caminó|fue|se\s+dirigió)\s+(?:de\s+(?:la\s+|el\s+)?(?P<from>\w+)\s+)?(?:a|hacia)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
        r"(?P<name>\w+)\s+(?:cruzó|atravesó)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+)?)",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compila los patrones regex."""
        self.compiled_arrival = [re.compile(p, re.IGNORECASE) for p in self.ARRIVAL_PATTERNS]
        self.compiled_departure = [re.compile(p, re.IGNORECASE) for p in self.DEPARTURE_PATTERNS]
        self.compiled_presence = [re.compile(p, re.IGNORECASE) for p in self.PRESENCE_PATTERNS]
        self.compiled_transition = [re.compile(p, re.IGNORECASE) for p in self.TRANSITION_PATTERNS]

    def analyze(
        self,
        project_id: int,
        chapters: list[dict],
        entities: list[dict],
    ) -> Result[CharacterLocationReport]:
        """
        Analiza ubicaciones de personajes en los capítulos.

        Args:
            project_id: ID del proyecto
            chapters: Lista de capítulos con 'number', 'title', 'content'
            entities: Lista de entidades con 'id', 'name', 'entity_type'

        Returns:
            Result con CharacterLocationReport
        """
        try:
            report = CharacterLocationReport(project_id=project_id)

            # Filtrar personajes (PER) y ubicaciones (LOC)
            characters = {e['name'].lower(): e for e in entities if e.get('entity_type') == 'PER'}
            locations = {e['name'].lower(): e for e in entities if e.get('entity_type') == 'LOC'}

            # Tracking de última ubicación conocida por personaje
            last_known_location: dict[int, tuple[str, int]] = {}  # entity_id -> (location, chapter)

            for chapter in sorted(chapters, key=lambda c: c.get('number', 0)):
                chapter_num = chapter.get('number', 0)
                content = chapter.get('content', '')

                if not content:
                    continue

                # Detectar eventos de ubicación
                events = self._detect_location_events(
                    content, chapter_num, characters, locations
                )

                for event in events:
                    report.location_events.append(event)

                    # Verificar inconsistencias
                    if event.entity_id in last_known_location:
                        prev_loc, prev_chapter = last_known_location[event.entity_id]

                        # Si está en el mismo capítulo pero diferente ubicación sin transición
                        if (prev_chapter == chapter_num and
                            prev_loc.lower() != event.location_name.lower() and
                            event.change_type != LocationChangeType.TRANSITION):

                            inconsistency = LocationInconsistency(
                                entity_id=event.entity_id,
                                entity_name=event.entity_name,
                                location1_name=prev_loc,
                                location1_chapter=prev_chapter,
                                location1_excerpt="(ver ubicación anterior)",
                                location2_name=event.location_name,
                                location2_chapter=chapter_num,
                                location2_excerpt=event.excerpt,
                                explanation=f"{event.entity_name} aparece en {event.location_name} "
                                           f"pero estaba en {prev_loc} en el mismo capítulo",
                                confidence=0.7,
                            )
                            report.inconsistencies.append(inconsistency)

                    # Actualizar última ubicación conocida
                    last_known_location[event.entity_id] = (event.location_name, chapter_num)

            # Guardar ubicaciones actuales
            for entity_id, (loc, _) in last_known_location.items():
                report.current_locations[entity_id] = loc

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error analizando ubicaciones: {e}")
            return Result.failure(NLPError(str(e)))

    def _detect_location_events(
        self,
        text: str,
        chapter: int,
        characters: dict,
        locations: dict,
    ) -> list[LocationEvent]:
        """Detecta eventos de ubicación en el texto."""
        events = []

        # Buscar llegadas
        for pattern in self.compiled_arrival:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match, characters, locations, chapter, text,
                    LocationChangeType.ARRIVAL
                )
                if event:
                    events.append(event)

        # Buscar salidas
        for pattern in self.compiled_departure:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match, characters, locations, chapter, text,
                    LocationChangeType.DEPARTURE
                )
                if event:
                    events.append(event)

        # Buscar presencias
        for pattern in self.compiled_presence:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match, characters, locations, chapter, text,
                    LocationChangeType.PRESENCE
                )
                if event:
                    events.append(event)

        # Buscar transiciones
        for pattern in self.compiled_transition:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match, characters, locations, chapter, text,
                    LocationChangeType.TRANSITION
                )
                if event:
                    events.append(event)

        return events

    def _create_event(
        self,
        match: re.Match,
        characters: dict,
        locations: dict,
        chapter: int,
        text: str,
        change_type: LocationChangeType,
    ) -> Optional[LocationEvent]:
        """Crea un evento de ubicación a partir de un match."""
        try:
            groups = match.groupdict()
            name = groups.get('name', '').strip()
            loc = groups.get('loc', '').strip()

            if not name or not loc:
                return None

            # Buscar el personaje
            char_data = characters.get(name.lower())
            if not char_data:
                # Intento de búsqueda parcial
                for char_name, data in characters.items():
                    if name.lower() in char_name or char_name in name.lower():
                        char_data = data
                        break

            if not char_data:
                return None

            # Buscar la ubicación
            loc_data = locations.get(loc.lower())
            loc_id = loc_data['id'] if loc_data else None

            # Extraer contexto
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 50)
            excerpt = text[start:end].strip()

            return LocationEvent(
                entity_id=char_data['id'],
                entity_name=char_data['name'],
                location_id=loc_id,
                location_name=loc,
                chapter=chapter,
                start_char=match.start(),
                end_char=match.end(),
                excerpt=excerpt,
                change_type=change_type,
                confidence=0.75,
            )
        except Exception as e:
            logger.warning(f"Error creando evento de ubicación: {e}")
            return None


def analyze_character_locations(
    project_id: int,
    chapters: list[dict],
    entities: list[dict],
) -> Result[CharacterLocationReport]:
    """
    Función de conveniencia para analizar ubicaciones de personajes.

    Args:
        project_id: ID del proyecto
        chapters: Lista de capítulos
        entities: Lista de entidades

    Returns:
        Result con CharacterLocationReport
    """
    analyzer = CharacterLocationAnalyzer()
    return analyzer.analyze(project_id, chapters, entities)
