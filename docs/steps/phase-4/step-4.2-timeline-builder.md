# STEP 4.2: Constructor de Timeline

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | XL (8-12 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 4.1 |

---

## Descripción

Construir una línea temporal de la narrativa a partir de los marcadores extraídos. Esto permite:
- Ordenar eventos cronológicamente
- Detectar flashbacks/flashforwards
- Verificar coherencia de edades de personajes
- Identificar analepsis y prolepsis

---

## Inputs

- Marcadores temporales extraídos (STEP 4.1)
- Eventos narrativos con posiciones
- Declaraciones del usuario (fechas explícitas)

---

## Outputs

- `src/narrative_assistant/temporal/timeline.py`
- Timeline con eventos ordenados
- Detección de saltos temporales
- Visualización de la línea temporal

---

## Modelo de Datos

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import date, timedelta
from enum import Enum

class TimelineResolution(Enum):
    EXACT_DATE = "exact_date"      # 15 de marzo de 1985
    MONTH = "month"                # marzo de 1985
    YEAR = "year"                  # 1985
    SEASON = "season"              # verano de 1985
    RELATIVE = "relative"          # 3 días después
    UNKNOWN = "unknown"            # sin fecha determinable

class NarrativeOrder(Enum):
    CHRONOLOGICAL = "chronological"
    ANALEPSIS = "analepsis"        # Flashback
    PROLEPSIS = "prolepsis"        # Flashforward

@dataclass
class TimelineEvent:
    id: int
    description: str
    chapter: int
    paragraph: int

    # Tiempo de la historia (story time)
    story_date: Optional[date] = None
    story_date_resolution: TimelineResolution = TimelineResolution.UNKNOWN

    # Tiempo del discurso (discourse time)
    discourse_position: int = 0  # Orden en el texto

    # Relaciones temporales
    relative_to: Optional[int] = None  # ID del evento de referencia
    relative_offset: Optional[timedelta] = None

    # Clasificación narrativa
    narrative_order: NarrativeOrder = NarrativeOrder.CHRONOLOGICAL

    # Personajes involucrados
    entity_ids: List[int] = field(default_factory=list)

    # Confianza
    confidence: float = 0.5

@dataclass
class Timeline:
    events: List[TimelineEvent] = field(default_factory=list)
    anchor_events: List[int] = field(default_factory=list)  # IDs de eventos con fecha absoluta

    def add_event(self, event: TimelineEvent) -> None:
        self.events.append(event)
        if event.story_date_resolution == TimelineResolution.EXACT_DATE:
            self.anchor_events.append(event.id)

    def get_chronological_order(self) -> List[TimelineEvent]:
        """Devuelve eventos ordenados por tiempo de historia."""
        dated = [e for e in self.events if e.story_date]
        undated = [e for e in self.events if not e.story_date]

        sorted_dated = sorted(dated, key=lambda e: e.story_date)
        return sorted_dated + undated

    def get_discourse_order(self) -> List[TimelineEvent]:
        """Devuelve eventos ordenados por aparición en el texto."""
        return sorted(self.events, key=lambda e: e.discourse_position)
```

---

## Implementación

```python
from typing import Optional, List, Tuple
from datetime import date, timedelta
from collections import defaultdict

class TimelineBuilder:
    def __init__(self):
        self.timeline = Timeline()
        self.event_counter = 0

    def build_from_markers(
        self,
        markers: List['TemporalMarker'],
        chapters: List['Chapter']
    ) -> Timeline:
        """Construye timeline a partir de marcadores temporales."""
        # 1. Crear eventos para cada capítulo como mínimo
        for chapter in chapters:
            self._create_chapter_event(chapter)

        # 2. Procesar marcadores absolutos (anclas)
        absolute_markers = [
            m for m in markers
            if m.marker_type.value == 'absolute_date'
        ]
        for marker in absolute_markers:
            self._add_absolute_anchor(marker)

        # 3. Procesar marcadores relativos
        relative_markers = [
            m for m in markers
            if m.marker_type.value == 'relative_time'
        ]
        self._resolve_relative_markers(relative_markers)

        # 4. Detectar analepsis/prolepsis
        self._detect_narrative_order()

        return self.timeline

    def _create_chapter_event(self, chapter: 'Chapter') -> TimelineEvent:
        """Crea un evento base para un capítulo."""
        self.event_counter += 1
        event = TimelineEvent(
            id=self.event_counter,
            description=f"Inicio capítulo {chapter.number}: {chapter.title}",
            chapter=chapter.number,
            paragraph=0,
            discourse_position=chapter.start_position
        )
        self.timeline.add_event(event)
        return event

    def _add_absolute_anchor(self, marker: 'TemporalMarker') -> None:
        """Añade un punto de anclaje con fecha absoluta."""
        parsed_date = self._parse_date_from_marker(marker)
        if not parsed_date:
            return

        # Buscar evento del capítulo
        chapter_events = [
            e for e in self.timeline.events
            if e.chapter == marker.chapter
        ]

        if chapter_events:
            event = chapter_events[0]
            event.story_date = parsed_date
            event.story_date_resolution = TimelineResolution.EXACT_DATE
            event.confidence = marker.confidence

    def _parse_date_from_marker(
        self,
        marker: 'TemporalMarker'
    ) -> Optional[date]:
        """Extrae fecha de un marcador."""
        import re

        text = marker.text.lower()

        # Patrón completo: "15 de marzo de 1985"
        full_match = re.search(
            r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|'
            r'julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})',
            text
        )
        if full_match:
            day = int(full_match.group(1))
            month = self._month_to_num(full_match.group(2))
            year = int(full_match.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                return None

        # Solo año
        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text)
        if year_match:
            return date(int(year_match.group(1)), 1, 1)

        return None

    def _month_to_num(self, month_name: str) -> int:
        """Convierte nombre de mes a número."""
        months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        return months.get(month_name.lower(), 1)

    def _resolve_relative_markers(
        self,
        markers: List['TemporalMarker']
    ) -> None:
        """Resuelve marcadores relativos usando anclas."""
        for marker in markers:
            # Encontrar el ancla más cercana anterior
            anchor = self._find_nearest_anchor(marker.chapter, marker.start_char)
            if not anchor:
                continue

            # Calcular offset
            offset = self._calculate_offset(marker)
            if offset is None:
                continue

            # Crear o actualizar evento
            self.event_counter += 1
            new_date = None

            if anchor.story_date and offset:
                if marker.direction == 'future':
                    new_date = anchor.story_date + offset
                elif marker.direction == 'past':
                    new_date = anchor.story_date - offset

            event = TimelineEvent(
                id=self.event_counter,
                description=f"Evento relativo: {marker.text}",
                chapter=marker.chapter,
                paragraph=marker.paragraph or 0,
                discourse_position=marker.start_char,
                story_date=new_date,
                story_date_resolution=TimelineResolution.RELATIVE if new_date else TimelineResolution.UNKNOWN,
                relative_to=anchor.id,
                relative_offset=offset,
                confidence=marker.confidence * 0.8
            )
            self.timeline.add_event(event)

    def _find_nearest_anchor(
        self,
        chapter: int,
        position: int
    ) -> Optional[TimelineEvent]:
        """Encuentra el evento ancla más cercano."""
        anchors = [
            e for e in self.timeline.events
            if e.id in self.timeline.anchor_events
        ]

        # Buscar en mismo capítulo primero
        same_chapter = [
            a for a in anchors
            if a.chapter == chapter and a.discourse_position <= position
        ]
        if same_chapter:
            return max(same_chapter, key=lambda a: a.discourse_position)

        # Buscar en capítulos anteriores
        previous = [a for a in anchors if a.chapter < chapter]
        if previous:
            return max(previous, key=lambda a: a.discourse_position)

        return anchors[0] if anchors else None

    def _calculate_offset(
        self,
        marker: 'TemporalMarker'
    ) -> Optional[timedelta]:
        """Calcula el offset temporal de un marcador relativo."""
        if not marker.quantity or not marker.magnitude:
            return None

        magnitude_to_days = {
            'día': 1,
            'semana': 7,
            'mes': 30,
            'año': 365,
        }

        days = marker.quantity * magnitude_to_days.get(marker.magnitude, 1)
        return timedelta(days=days)

    def _detect_narrative_order(self) -> None:
        """Detecta analepsis y prolepsis comparando orden cronológico vs discurso."""
        chronological = self.timeline.get_chronological_order()
        discourse = self.timeline.get_discourse_order()

        # Solo eventos con fecha conocida
        dated_chrono = [e for e in chronological if e.story_date]
        dated_discourse = [e for e in discourse if e.story_date]

        if len(dated_chrono) < 2:
            return

        # Crear índice cronológico
        chrono_index = {e.id: i for i, e in enumerate(dated_chrono)}

        # Comparar con orden del discurso
        for i, event in enumerate(dated_discourse):
            if i == 0:
                continue

            prev_event = dated_discourse[i - 1]

            chrono_pos_current = chrono_index.get(event.id, 0)
            chrono_pos_prev = chrono_index.get(prev_event.id, 0)

            if chrono_pos_current < chrono_pos_prev:
                # El evento actual ocurrió antes cronológicamente
                # pero aparece después en el discurso = analepsis
                event.narrative_order = NarrativeOrder.ANALEPSIS
            elif chrono_pos_current > chrono_pos_prev + 1:
                # Salto grande hacia adelante podría ser prolepsis
                # (Esto es heurístico, requiere contexto)
                pass

    def export_to_mermaid(self) -> str:
        """Exporta timeline a diagrama Mermaid."""
        lines = ["gantt", "    title Timeline Narrativo", "    dateFormat YYYY-MM-DD"]

        chrono = self.timeline.get_chronological_order()
        dated = [e for e in chrono if e.story_date]

        if not dated:
            return "No hay eventos con fechas determinadas."

        # Agrupar por año
        by_year = defaultdict(list)
        for event in dated:
            by_year[event.story_date.year].append(event)

        for year in sorted(by_year.keys()):
            lines.append(f"    section {year}")
            for event in by_year[year]:
                desc = event.description[:30].replace(":", "-")
                date_str = event.story_date.strftime("%Y-%m-%d")
                lines.append(f"    {desc} :{date_str}, 1d")

        return "\n".join(lines)
```

---

## Criterio de DONE

```python
from narrative_assistant.temporal import TimelineBuilder, TemporalMarkerExtractor

# Extraer marcadores
extractor = TemporalMarkerExtractor()
text = """
Capítulo 1: La partida
El 15 de marzo de 1985, Juan dejó su pueblo.

Capítulo 2: El viaje
Tres días después llegó a Madrid.

Capítulo 3: Recuerdos
Recordó aquel verano de 1980, cuando tenía quince años.
"""

markers = extractor.extract(text)

# Construir timeline
builder = TimelineBuilder()

class MockChapter:
    def __init__(self, num, title, pos):
        self.number = num
        self.title = title
        self.start_position = pos

chapters = [
    MockChapter(1, "La partida", 0),
    MockChapter(2, "El viaje", 100),
    MockChapter(3, "Recuerdos", 200),
]

timeline = builder.build_from_markers(markers, chapters)

# Verificaciones
assert len(timeline.events) >= 3
assert len(timeline.anchor_events) >= 1

# Verificar detección de analepsis (el recuerdo de 1980)
analepsis = [e for e in timeline.events
             if e.narrative_order.value == 'analepsis']
# Nota: puede no detectarse sin información adicional

print(f"✅ Timeline construido con {len(timeline.events)} eventos")
print(builder.export_to_mermaid())
```

---

## Siguiente

[STEP 4.3: Inconsistencias Temporales](./step-4.3-temporal-inconsistencies.md)
