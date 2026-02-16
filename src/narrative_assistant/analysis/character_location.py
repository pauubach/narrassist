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

from ..core.errors import NLPError
from ..core.result import Result
from .location_ontology import HistoricalPeriod, LocationOntology, get_default_ontology

logger = logging.getLogger(__name__)


class LocationChangeType(Enum):
    """Tipo de cambio de ubicación."""

    ARRIVAL = "arrival"  # Llegada a un lugar
    DEPARTURE = "departure"  # Salida de un lugar
    TRANSITION = "transition"  # Transición entre lugares
    PRESENCE = "presence"  # Presencia en un lugar (sin movimiento explícito)


@dataclass
class LocationEvent:
    """
    Evento de ubicación de un personaje.

    Representa un cambio de ubicación o presencia en un lugar.
    """

    entity_id: int
    entity_name: str
    location_id: int | None  # ID de entidad LOC si existe
    location_name: str  # Nombre del lugar
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
            "characters_tracked": len({e.entity_id for e in self.location_events}),
            "locations_found": len({e.location_name for e in self.location_events}),
        }


class CharacterLocationAnalyzer:
    """
    Analizador de ubicaciones de personajes.

    Detecta movimientos entre ubicaciones y posibles inconsistencias.
    """

    # Patrones de llegada
    ARRIVAL_PATTERNS = [
        r"(?P<name>\w+)\s+(?:llegó|arribó|entró|accedió|irrumpió)\s+(?:a|en)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        r"(?P<name>\w+)\s+(?:apareció|se\s+presentó|se\s+instaló)\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        r"cuando\s+(?P<name>\w+)\s+(?:llegó|entró)\s+(?:a|en)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
    ]

    # Patrones de salida
    DEPARTURE_PATTERNS = [
        r"(?P<name>\w+)\s+(?:salió|partió|se\s+fue|abandonó|se\s+marchó|huyó)\s+(?:de\s+)?(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        r"(?P<name>\w+)\s+(?:dejó)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
    ]

    # Patrones de presencia
    PRESENCE_PATTERNS = [
        r"(?P<name>\w+)\s+(?:estaba|se\s+encontraba|permanecía|seguía|continuaba|aguardaba|residía|vivía)\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        r"en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})[,\s]+(?P<name>\w+)\s+(?:esperaba|miraba|observaba|trabajaba|descansaba|dormía|leía)",
        r"en\s+(?P<loc>[A-ZÁÉÍÓÚÑ]\w+)[,]\s*(?P<name>[A-ZÁÉÍÓÚÑ]\w+)\s+(?:estaba|se\s+encontraba|permanecía)",
        # "Name se quedó/se reunió en LOC"
        r"(?P<name>\w+)\s+(?:se\s+quedó|se\s+reunió|se\s+hospedó|se\s+alojó)\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
    ]

    # Patrones de transición
    TRANSITION_PATTERNS = [
        r"(?P<name>\w+)\s+(?:viajó|caminó|fue|se\s+dirigió|corrió|condujo|voló|navegó|regresó|volvió)\s+(?:de\s+(?:la\s+|el\s+)?(?P<from>\w+(?:\s+\w+){0,3})\s+)?(?:a|hacia)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        r"(?P<name>\w+)\s+(?:cruzó|atravesó|recorrió)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        # "Name tomó un vuelo/tren/barco a LOC"
        r"(?P<name>\w+)\s+(?:tomó|cogió)\s+(?:un\s+)?(?:vuelo|tren|barco|autobús|taxi|avión|coche)\s+(?:a|hacia|con\s+destino\s+a?)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
    ]

    # Patrones de co-presencia: otro personaje acompaña/sigue/lleva a alguien
    # Estos extraen <name> como personaje y <loc> como destino (puede ser evento)
    COPRESENCE_PATTERNS = [
        # "Name, que había acompañado al [evento/lugar]"
        r"(?P<name>\w+)[,]\s+que\s+(?:lo|la|le|les|los|las)?\s*(?:había\s+)?(?:acompañado|acompañó|seguido|llevado)\s+(?:a|al|a\s+la)\s+(?P<loc>\w+(?:\s+\w+){0,3})",
        # "Name acompañó a [persona] a/al [lugar]"
        r"(?P<name>\w+)\s+(?:acompañó|acompañaba|siguió|seguía|llevó|llevaba|condujo)\s+a\s+\w+\s+(?:a|al|a\s+la|hasta)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        # "Name fue con [persona] a/al [lugar]"
        r"(?P<name>\w+)\s+(?:fue|iba|vino|venía)\s+con\s+\w+\s+(?:a|al|a\s+la|hasta)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        # "[persona] y Name estaban/fueron a [lugar]"
        r"\w+\s+y\s+(?P<name>\w+)\s+(?:estaban|fueron|llegaron|viajaron)\s+(?:a|en)\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
        # "Name recogió a [persona] en [lugar]"
        r"(?P<name>\w+)\s+(?:recogió|dejó|esperó\s+a)\s+(?:a\s+)?\w+\s+en\s+(?:la\s+|el\s+)?(?P<loc>\w+(?:\s+\w+){0,3})",
    ]

    # Palabras clave que son eventos, no ubicaciones geográficas directas
    _EVENT_KEYWORDS = {
        "congreso", "conferencia", "seminario", "simposio", "coloquio",
        "reunión", "cena", "almuerzo", "fiesta", "boda", "funeral",
        "entierro", "juicio", "ceremonia", "gala", "exposición",
        "presentación", "concierto", "espectáculo", "partido",
    }

    def __init__(self, ontology: LocationOntology | None = None):
        self._ontology = ontology if ontology is not None else get_default_ontology()
        self._compile_patterns()

    def _compile_patterns(self):
        """Compila los patrones regex."""
        self.compiled_arrival = [
            re.compile(p, re.IGNORECASE) for p in self.ARRIVAL_PATTERNS
        ]
        self.compiled_departure = [
            re.compile(p, re.IGNORECASE) for p in self.DEPARTURE_PATTERNS
        ]
        self.compiled_presence = [
            re.compile(p, re.IGNORECASE) for p in self.PRESENCE_PATTERNS
        ]
        self.compiled_transition = [
            re.compile(p, re.IGNORECASE) for p in self.TRANSITION_PATTERNS
        ]
        self.compiled_copresence = [
            re.compile(p, re.IGNORECASE) for p in self.COPRESENCE_PATTERNS
        ]

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

            # Filtrar personajes (PER/character) y ubicaciones (LOC/location)
            char_types = {"PER", "character", "PERSON", "person"}
            loc_types = {"LOC", "location", "LOCATION", "building"}
            characters = {
                (e.get("name") or e.get("canonical_name", "")).lower(): e
                for e in entities if e.get("entity_type") in char_types
            }
            locations = {
                (e.get("name") or e.get("canonical_name", "")).lower(): e
                for e in entities if e.get("entity_type") in loc_types
            }

            # Tracking de última ubicación conocida por personaje
            last_known_location: dict[int, tuple[str, int]] = (
                {}
            )  # entity_id -> (location, chapter)

            for chapter in sorted(chapters, key=lambda c: c.get("number", 0)):
                chapter_num = chapter.get("number", 0)
                content = chapter.get("content", "")

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
                        if (
                            prev_chapter == chapter_num
                            and prev_loc.lower() != event.location_name.lower()
                            and event.change_type != LocationChangeType.TRANSITION
                        ):
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
                    last_known_location[event.entity_id] = (
                        event.location_name,
                        chapter_num,
                    )

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
                    match,
                    characters,
                    locations,
                    chapter,
                    text,
                    LocationChangeType.ARRIVAL,
                )
                if event:
                    events.append(event)

        # Buscar salidas
        for pattern in self.compiled_departure:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match,
                    characters,
                    locations,
                    chapter,
                    text,
                    LocationChangeType.DEPARTURE,
                )
                if event:
                    events.append(event)

        # Buscar presencias
        for pattern in self.compiled_presence:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match,
                    characters,
                    locations,
                    chapter,
                    text,
                    LocationChangeType.PRESENCE,
                )
                if event:
                    events.append(event)

        # Buscar transiciones
        for pattern in self.compiled_transition:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match,
                    characters,
                    locations,
                    chapter,
                    text,
                    LocationChangeType.TRANSITION,
                )
                if event:
                    events.append(event)

        # Buscar co-presencias (acompañó, fue con, siguió a)
        for pattern in self.compiled_copresence:
            for match in pattern.finditer(text):
                event = self._create_event(
                    match,
                    characters,
                    locations,
                    chapter,
                    text,
                    LocationChangeType.PRESENCE,
                    confidence=0.70,
                )
                if event:
                    # Si el "lugar" es un evento (congreso, cena...), resolver ubicación real
                    resolved = self._resolve_event_location(
                        event.location_name, text
                    )
                    if resolved:
                        event = LocationEvent(
                            entity_id=event.entity_id,
                            entity_name=event.entity_name,
                            location_id=event.location_id,
                            location_name=resolved,
                            chapter=event.chapter,
                            start_char=event.start_char,
                            end_char=event.end_char,
                            excerpt=event.excerpt,
                            change_type=event.change_type,
                            confidence=0.70,
                        )
                    events.append(event)

        return events

    def _resolve_event_location(
        self, loc_name: str, text: str
    ) -> str | None:
        """
        Resuelve un nombre de evento a una ubicación geográfica real.

        Si loc_name es un evento (congreso, cena, etc.), busca en el texto
        cercano una ubicación geográfica explícita asociada al evento.

        Ejemplo: "congreso" + "Centro de Convenciones de Madrid" → "Madrid"
        """
        # Solo resolver si parece un evento, no una ubicación directa
        loc_lower = loc_name.lower().split()[0]  # primera palabra
        if loc_lower not in self._EVENT_KEYWORDS:
            # Verificar si la ontología ya lo conoce como ubicación real
            if self._ontology.resolve(loc_name):
                return None  # Ya es una ubicación conocida, no resolver
            # Si no es evento ni ubicación conocida, intentar resolver igual
            # (podría ser un nombre de edificio, etc.)
            return None

        # Buscar ubicaciones geográficas cerca del nombre del evento en el texto
        # Estrategia: buscar ciudades/regiones conocidas mencionadas en el mismo
        # párrafo o dentro de 500 caracteres del evento
        event_positions = [
            m.start()
            for m in re.finditer(re.escape(loc_lower), text, re.IGNORECASE)
        ]

        if not event_positions:
            return None

        # Buscar nombres de ciudades/regiones conocidas en el texto
        known_locations = self._ontology.get_all_names()
        best_match = None
        best_distance = float("inf")

        for known_loc in known_locations:
            if len(known_loc) < 3:
                continue
            loc_type = self._ontology.get_type(known_loc)
            if not loc_type:
                continue
            # Solo resolver a CITY, REGION, COUNTRY (no a ROOM/BUILDING)
            from .location_ontology import LocationType
            if loc_type.value < LocationType.CITY.value:
                continue

            for loc_match in re.finditer(
                rf"\b{re.escape(known_loc)}\b", text, re.IGNORECASE
            ):
                for ev_pos in event_positions:
                    dist = abs(loc_match.start() - ev_pos)
                    if dist < best_distance and dist < 500:
                        best_distance = dist
                        best_match = known_loc

        return best_match

    def _create_event(
        self,
        match: re.Match,
        characters: dict,
        locations: dict,
        chapter: int,
        text: str,
        change_type: LocationChangeType,
        confidence: float = 0.75,
    ) -> LocationEvent | None:
        """Crea un evento de ubicación a partir de un match."""
        try:
            groups = match.groupdict()
            name = groups.get("name", "").strip()
            loc = groups.get("loc", "").strip()

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
            loc_id = loc_data["id"] if loc_data else None

            # Extraer contexto
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 50)
            excerpt = text[start:end].strip()

            return LocationEvent(
                entity_id=char_data.get("id", 0),
                entity_name=char_data.get("name") or char_data.get("canonical_name", ""),
                location_id=loc_id,
                location_name=loc,
                chapter=chapter,
                start_char=match.start(),
                end_char=match.end(),
                excerpt=excerpt,
                change_type=change_type,
                confidence=confidence,
            )
        except Exception as e:
            logger.warning(f"Error creando evento de ubicación: {e}")
            return None

    def check_impossible_travel(
        self,
        report: CharacterLocationReport,
        hours_between: float | None = None,
        period: HistoricalPeriod = HistoricalPeriod.MODERN,
    ) -> list[LocationInconsistency]:
        """
        Detecta viajes imposibles: un personaje en dos ubicaciones distantes
        sin tiempo narrativo suficiente entre ambas.

        Se basa en:
        - Ontología jerárquica de ubicaciones (are_compatible)
        - Reachability con distancias geográficas y periodo histórico
        - Cambios de ubicación dentro del mismo capítulo sin transición

        Args:
            report: Reporte de ubicaciones a verificar
            hours_between: Horas entre capítulos para check cross-chapter.
                          Si es None, solo verifica mismo capítulo.
            period: Periodo histórico para velocidad de viaje.

        Returns:
            Lista de inconsistencias de viaje imposible.
        """
        inconsistencies = []

        # Agrupar eventos por personaje
        events_by_char: dict[int, list[LocationEvent]] = {}
        for event in report.location_events:
            if event.entity_id not in events_by_char:
                events_by_char[event.entity_id] = []
            events_by_char[event.entity_id].append(event)

        for entity_id, events in events_by_char.items():
            # Ordenar por capítulo y posición
            events.sort(key=lambda e: (e.chapter, e.start_char))

            for i in range(1, len(events)):
                prev = events[i - 1]
                curr = events[i]

                # Transición explícita = ok
                if curr.change_type == LocationChangeType.TRANSITION:
                    continue

                loc1 = prev.location_name
                loc2 = curr.location_name

                if loc1.lower() == loc2.lower():
                    continue

                if prev.chapter == curr.chapter:
                    # Mismo capítulo: verificar compatibilidad jerárquica
                    if not self._ontology.are_compatible(loc1, loc2):
                        inconsistencies.append(
                            LocationInconsistency(
                                entity_id=entity_id,
                                entity_name=curr.entity_name,
                                location1_name=prev.location_name,
                                location1_chapter=prev.chapter,
                                location1_excerpt=prev.excerpt,
                                location2_name=curr.location_name,
                                location2_chapter=curr.chapter,
                                location2_excerpt=curr.excerpt,
                                explanation=(
                                    f"{curr.entity_name} aparece en {curr.location_name} "
                                    f"pero estaba en {prev.location_name} en el mismo capítulo "
                                    f"sin transición explícita"
                                ),
                                confidence=0.75,
                            )
                        )
                elif hours_between is not None:
                    # Cross-chapter: verificar alcanzabilidad
                    if not self._ontology.are_compatible(loc1, loc2):
                        if not self._ontology.is_reachable(
                            loc1, loc2, hours_between, period
                        ):
                            inconsistencies.append(
                                LocationInconsistency(
                                    entity_id=entity_id,
                                    entity_name=curr.entity_name,
                                    location1_name=prev.location_name,
                                    location1_chapter=prev.chapter,
                                    location1_excerpt=prev.excerpt,
                                    location2_name=curr.location_name,
                                    location2_chapter=curr.chapter,
                                    location2_excerpt=curr.excerpt,
                                    explanation=(
                                        f"{curr.entity_name} viaja de {prev.location_name} "
                                        f"a {curr.location_name} entre capítulos "
                                        f"{prev.chapter} y {curr.chapter}, "
                                        f"pero la distancia es inalcanzable en "
                                        f"{hours_between:.0f}h ({period.value})"
                                    ),
                                    confidence=0.70,
                                )
                            )

        return inconsistencies

    def _are_locations_incompatible(self, loc1: str, loc2: str) -> bool:
        """
        Determina si dos ubicaciones son incompatibles (no se puede estar
        en ambas simultáneamente). Delega a la ontología.
        """
        return not self._ontology.are_compatible(loc1, loc2)


def analyze_character_locations(
    project_id: int,
    chapters: list[dict],
    entities: list[dict],
    ontology: LocationOntology | None = None,
) -> Result[CharacterLocationReport]:
    """
    Función de conveniencia para analizar ubicaciones de personajes.

    Args:
        project_id: ID del proyecto
        chapters: Lista de capítulos
        entities: Lista de entidades
        ontology: Ontología de ubicaciones (opcional, usa la default)

    Returns:
        Result con CharacterLocationReport
    """
    analyzer = CharacterLocationAnalyzer(ontology=ontology)
    result = analyzer.analyze(project_id, chapters, entities)

    # Añadir detección de viajes imposibles
    if result.is_success and result.value:
        impossible = analyzer.check_impossible_travel(result.value)
        result.value.inconsistencies.extend(impossible)

    return result
