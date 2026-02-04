# STEP 4.3: Detector de Inconsistencias Temporales

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 4.2 |

---

## Descripción

Detectar inconsistencias temporales en la narrativa:
- **Edades incoherentes**: personaje con 20 años en 1985, pero 30 años en 1990
- **Eventos imposibles**: "nació en 1980" pero "en 1975 ya era adulto"
- **Duraciones contradictorias**: "tras tres meses" pero contexto sugiere días
- **Anacronismos**: tecnología/eventos que no existían en la época

---

## Inputs

- Timeline construido (STEP 4.2)
- Edades de personajes extraídas
- Marcadores temporales con contexto

---

## Outputs

- `src/narrative_assistant/temporal/inconsistencies.py`
- Alertas de inconsistencias temporales
- Explicaciones detalladas
- Sugerencias de corrección

---

## Tipos de Inconsistencias

| Tipo | Descripción | Severidad |
|------|-------------|-----------|
| `age_mismatch` | Edad no coincide con fechas | Alta |
| `impossible_sequence` | Evento B antes de A, pero A es prerequisito | Alta |
| `duration_conflict` | Duraciones contradictorias | Media |
| `anachronism` | Elemento fuera de época | Media |
| `timeline_gap` | Salto temporal inexplicado | Baja |

---

## Implementación

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from datetime import date
from enum import Enum

class InconsistencyType(Enum):
    AGE_MISMATCH = "age_mismatch"
    IMPOSSIBLE_SEQUENCE = "impossible_sequence"
    DURATION_CONFLICT = "duration_conflict"
    ANACHRONISM = "anachronism"
    TIMELINE_GAP = "timeline_gap"

class InconsistencySeverity(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class TemporalInconsistency:
    inconsistency_type: InconsistencyType
    severity: InconsistencySeverity
    description: str
    evidence: List[str]  # Fragmentos de texto que evidencian el problema
    locations: List[Tuple[int, int]]  # (capítulo, párrafo)
    suggestion: Optional[str] = None
    confidence: float = 0.8

    # Para age_mismatch
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    expected_age: Optional[int] = None
    found_age: Optional[int] = None

@dataclass
class CharacterAgeRecord:
    entity_id: int
    entity_name: str
    age: int
    reference_date: Optional[date]
    chapter: int
    source_text: str

class TemporalInconsistencyDetector:
    def __init__(self, timeline: 'Timeline'):
        self.timeline = timeline
        self.age_records: Dict[int, List[CharacterAgeRecord]] = {}

    def detect_all(
        self,
        age_markers: List['TemporalMarker'] = None
    ) -> List[TemporalInconsistency]:
        """Detecta todas las inconsistencias temporales."""
        inconsistencies = []

        # 1. Detectar inconsistencias de edad
        if age_markers:
            self._build_age_records(age_markers)
            inconsistencies.extend(self._check_age_consistency())

        # 2. Detectar secuencias imposibles
        inconsistencies.extend(self._check_impossible_sequences())

        # 3. Detectar conflictos de duración
        inconsistencies.extend(self._check_duration_conflicts())

        # 4. Detectar gaps inexplicados
        inconsistencies.extend(self._check_timeline_gaps())

        return sorted(
            inconsistencies,
            key=lambda i: (
                0 if i.severity == InconsistencySeverity.HIGH else
                1 if i.severity == InconsistencySeverity.MEDIUM else 2
            )
        )

    def _build_age_records(
        self,
        age_markers: List['TemporalMarker']
    ) -> None:
        """Construye registros de edad por personaje."""
        for marker in age_markers:
            if marker.marker_type.value != 'character_age':
                continue
            if not marker.entity_id or not marker.age:
                continue

            # Buscar fecha de referencia del evento
            ref_date = self._find_reference_date(marker.chapter, marker.start_char)

            record = CharacterAgeRecord(
                entity_id=marker.entity_id,
                entity_name=marker.entity_name if hasattr(marker, 'entity_name') else f"Entity {marker.entity_id}",
                age=marker.age,
                reference_date=ref_date,
                chapter=marker.chapter,
                source_text=marker.text
            )

            if marker.entity_id not in self.age_records:
                self.age_records[marker.entity_id] = []
            self.age_records[marker.entity_id].append(record)

    def _find_reference_date(
        self,
        chapter: int,
        position: int
    ) -> Optional[date]:
        """Encuentra la fecha de referencia para una posición."""
        # Buscar el evento más cercano con fecha
        candidates = [
            e for e in self.timeline.events
            if e.story_date and e.chapter <= chapter
        ]
        if not candidates:
            return None

        # El más cercano por capítulo y posición
        same_chapter = [c for c in candidates if c.chapter == chapter]
        if same_chapter:
            return max(same_chapter, key=lambda e: e.discourse_position).story_date

        return max(candidates, key=lambda e: e.discourse_position).story_date

    def _check_age_consistency(self) -> List[TemporalInconsistency]:
        """Verifica consistencia de edades entre menciones."""
        inconsistencies = []

        for entity_id, records in self.age_records.items():
            if len(records) < 2:
                continue

            # Ordenar por fecha de referencia
            dated_records = [r for r in records if r.reference_date]
            if len(dated_records) < 2:
                continue

            dated_records.sort(key=lambda r: r.reference_date)

            # Comparar pares consecutivos
            for i in range(len(dated_records) - 1):
                r1 = dated_records[i]
                r2 = dated_records[i + 1]

                # Calcular años transcurridos
                years_passed = (r2.reference_date - r1.reference_date).days / 365.25
                expected_age = r1.age + int(years_passed)

                # Tolerancia de 1 año
                if abs(r2.age - expected_age) > 1:
                    inconsistencies.append(TemporalInconsistency(
                        inconsistency_type=InconsistencyType.AGE_MISMATCH,
                        severity=InconsistencySeverity.HIGH,
                        description=(
                            f"{r1.entity_name}: tenía {r1.age} años en {r1.reference_date.year}, "
                            f"pero {r2.age} años en {r2.reference_date.year} "
                            f"(esperado: ~{expected_age})"
                        ),
                        evidence=[r1.source_text, r2.source_text],
                        locations=[(r1.chapter, 0), (r2.chapter, 0)],
                        suggestion=f"Revisar: ¿debería tener {expected_age} años en el capítulo {r2.chapter}?",
                        entity_id=entity_id,
                        entity_name=r1.entity_name,
                        expected_age=expected_age,
                        found_age=r2.age
                    ))

        return inconsistencies

    def _check_impossible_sequences(self) -> List[TemporalInconsistency]:
        """Detecta secuencias de eventos imposibles."""
        inconsistencies = []

        # Ordenar eventos por tiempo de discurso
        discourse_order = self.timeline.get_discourse_order()
        dated_events = [e for e in discourse_order if e.story_date]

        for i in range(1, len(dated_events)):
            prev = dated_events[i - 1]
            curr = dated_events[i]

            # Si el evento actual tiene fecha anterior al previo
            # Y no está marcado como analepsis
            if (curr.story_date < prev.story_date and
                curr.narrative_order.value == 'chronological'):

                # Podría ser error o analepsis no detectada
                gap_days = (prev.story_date - curr.story_date).days

                if gap_days > 365:  # Salto de más de un año
                    inconsistencies.append(TemporalInconsistency(
                        inconsistency_type=InconsistencyType.IMPOSSIBLE_SEQUENCE,
                        severity=InconsistencySeverity.MEDIUM,
                        description=(
                            f"Posible salto temporal no marcado: "
                            f"'{curr.description}' ({curr.story_date}) aparece después de "
                            f"'{prev.description}' ({prev.story_date})"
                        ),
                        evidence=[prev.description, curr.description],
                        locations=[(prev.chapter, 0), (curr.chapter, 0)],
                        suggestion="Verificar si es un flashback intencional"
                    ))

        return inconsistencies

    def _check_duration_conflicts(self) -> List[TemporalInconsistency]:
        """Detecta conflictos en duraciones mencionadas."""
        # Esta función requiere marcadores de duración y eventos relacionados
        # Implementación simplificada
        return []

    def _check_timeline_gaps(self) -> List[TemporalInconsistency]:
        """Detecta gaps inexplicados en el timeline."""
        inconsistencies = []

        chrono = self.timeline.get_chronological_order()
        dated = [e for e in chrono if e.story_date]

        for i in range(1, len(dated)):
            prev = dated[i - 1]
            curr = dated[i]

            gap_days = (curr.story_date - prev.story_date).days

            # Gap de más de 5 años sin explicación
            if gap_days > 5 * 365:
                inconsistencies.append(TemporalInconsistency(
                    inconsistency_type=InconsistencyType.TIMELINE_GAP,
                    severity=InconsistencySeverity.LOW,
                    description=(
                        f"Gap de {gap_days // 365} años entre "
                        f"'{prev.description}' y '{curr.description}'"
                    ),
                    evidence=[],
                    locations=[(prev.chapter, 0), (curr.chapter, 0)],
                    suggestion="Considerar añadir contexto temporal para este salto"
                ))

        return inconsistencies

    def check_anachronism(
        self,
        term: str,
        mentioned_date: date,
        known_dates: Dict[str, int]  # término -> año de aparición
    ) -> Optional[TemporalInconsistency]:
        """Verifica si un término es anacrónico para una fecha."""
        term_lower = term.lower()

        if term_lower in known_dates:
            appearance_year = known_dates[term_lower]
            if mentioned_date.year < appearance_year:
                return TemporalInconsistency(
                    inconsistency_type=InconsistencyType.ANACHRONISM,
                    severity=InconsistencySeverity.MEDIUM,
                    description=(
                        f"'{term}' mencionado en {mentioned_date.year}, "
                        f"pero no existía hasta {appearance_year}"
                    ),
                    evidence=[term],
                    locations=[],
                    suggestion=f"El término '{term}' es anacrónico para esta época"
                )

        return None

# Base de datos simple de anacronismos conocidos
KNOWN_ANACHRONISMS = {
    'internet': 1991,
    'email': 1971,
    'smartphone': 2007,
    'iphone': 2007,
    'whatsapp': 2009,
    'facebook': 2004,
    'google': 1998,
    'spotify': 2008,
    'netflix': 1997,  # Como streaming: 2007
    'uber': 2009,
    'covid': 2019,
    'coronavirus': 2019,  # En contexto pandémico
    'selfie': 2002,
    'emoji': 2010,
    'tuit': 2006,
    'tweet': 2006,
    'hashtag': 2007,
}
```

---

## Criterio de DONE

```python
from narrative_assistant.temporal import (
    TemporalInconsistencyDetector,
    TimelineBuilder,
    TemporalMarkerExtractor,
    InconsistencyType
)
from datetime import date

# Setup
extractor = TemporalMarkerExtractor()
text = """
Capítulo 1 - 1985
María tenía 20 años cuando llegó a Madrid el 15 de marzo de 1985.

Capítulo 5 - 1990
En enero de 1990, María celebró sus 30 años.
"""
# Nota: Si tenía 20 en 1985, debería tener 25 en 1990, no 30

markers = extractor.extract(text)
# Simular entity_id para los markers de edad
for m in markers:
    if m.marker_type.value == 'character_age':
        m.entity_id = 1
        m.entity_name = "María"

# Construir timeline
builder = TimelineBuilder()

class MockChapter:
    def __init__(self, num, title, pos):
        self.number = num
        self.title = title
        self.start_position = pos

chapters = [MockChapter(1, "1985", 0), MockChapter(5, "1990", 100)]
timeline = builder.build_from_markers(markers, chapters)

# Detectar inconsistencias
detector = TemporalInconsistencyDetector(timeline)
inconsistencies = detector.detect_all(markers)

# Debe detectar inconsistencia de edad
age_issues = [i for i in inconsistencies
              if i.inconsistency_type == InconsistencyType.AGE_MISMATCH]

# Verificar detección de anacronismos
anachronism = detector.check_anachronism(
    "WhatsApp",
    date(1995, 1, 1),
    KNOWN_ANACHRONISMS
)
assert anachronism is not None
assert anachronism.inconsistency_type == InconsistencyType.ANACHRONISM

print(f"✅ Detectadas {len(inconsistencies)} inconsistencias")
for inc in inconsistencies:
    print(f"  [{inc.severity.value}] {inc.description}")
```

---

## Siguiente

[STEP 5.1: Perfiles de Voz](../phase-5/step-5.1-voice-profiles.md)
