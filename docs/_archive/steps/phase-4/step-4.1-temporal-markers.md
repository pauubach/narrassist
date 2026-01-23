# STEP 4.1: Extracción de Marcadores Temporales

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 1.3 |

---

## Descripción

Extraer referencias temporales del texto narrativo:
- Fechas explícitas ("15 de marzo de 1985")
- Referencias relativas ("tres días después", "la semana anterior")
- Estaciones/épocas ("aquel verano", "durante la guerra")
- Edades de personajes ("cuando tenía 20 años")

---

## Inputs

- Texto procesado
- Entidades detectadas (para edades)
- Metadatos de capítulo/escena

---

## Outputs

- `src/narrative_assistant/temporal/markers.py`
- Lista de marcadores temporales con posiciones
- Clasificación por tipo de marcador
- Referencias a entidades (para edades)

---

## Tipos de Marcadores

| Tipo | Ejemplos | Dificultad |
|------|----------|------------|
| `absolute_date` | "15 de marzo de 1985" | Fácil |
| `relative_time` | "tres días después", "la semana anterior" | Media |
| `season_epoch` | "aquel verano", "durante la guerra" | Media |
| `character_age` | "cuando tenía 20 años" | Difícil |
| `duration` | "durante tres meses" | Media |
| `frequency` | "cada martes", "todas las noches" | Fácil |

---

## Implementación

```python
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

class MarkerType(Enum):
    ABSOLUTE_DATE = "absolute_date"
    RELATIVE_TIME = "relative_time"
    SEASON_EPOCH = "season_epoch"
    CHARACTER_AGE = "character_age"
    DURATION = "duration"
    FREQUENCY = "frequency"

@dataclass
class TemporalMarker:
    text: str
    marker_type: MarkerType
    start_char: int
    end_char: int
    chapter: Optional[int] = None
    paragraph: Optional[int] = None
    # Para marcadores relativos
    direction: Optional[str] = None  # 'past', 'future'
    magnitude: Optional[str] = None  # 'días', 'meses', 'años'
    quantity: Optional[int] = None
    # Para edades
    entity_id: Optional[int] = None
    age: Optional[int] = None
    # Confianza
    confidence: float = 1.0

# Patrones de extracción
TEMPORAL_PATTERNS = {
    MarkerType.ABSOLUTE_DATE: [
        # "15 de marzo de 1985"
        (r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b', 0.95),
        # "marzo de 1985"
        (r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b', 0.9),
        # "1985"
        (r'\b(19\d{2}|20[0-2]\d)\b', 0.7),
        # "el año 1985"
        (r'\bel\s+año\s+(\d{4})\b', 0.95),
    ],

    MarkerType.RELATIVE_TIME: [
        # "X días/semanas/meses/años después/antes"
        (r'\b(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+(días?|semanas?|meses?|años?)\s+(después|antes|más\s+tarde|atrás)\b', 0.9),
        # "al día siguiente", "la noche anterior"
        (r'\b(al\s+día\s+siguiente|la\s+noche\s+anterior|la\s+mañana\s+siguiente|el\s+día\s+anterior)\b', 0.95),
        # "aquella noche", "esa mañana"
        (r'\b(aquel|aquella|ese|esa)\s+(noche|mañana|tarde|día)\b', 0.8),
        # "más tarde", "poco después"
        (r'\b(más\s+tarde|poco\s+después|mucho\s+después|tiempo\s+después)\b', 0.85),
    ],

    MarkerType.SEASON_EPOCH: [
        # "aquel verano", "ese invierno"
        (r'\b(aquel|aquella|ese|esa|el|la)\s+(verano|invierno|otoño|primavera)\b', 0.9),
        # "durante la guerra"
        (r'\bdurante\s+(la\s+guerra|la\s+posguerra|la\s+República|el\s+franquismo)\b', 0.85),
        # "en los años 80"
        (r'\ben\s+los\s+años\s+(\d{2})\b', 0.9),
    ],

    MarkerType.CHARACTER_AGE: [
        # "cuando tenía X años"
        (r'\bcuando\s+ten[íi]a\s+(\d{1,3})\s+años\b', 0.9),
        # "a los X años"
        (r'\ba\s+los\s+(\d{1,3})\s+años\b', 0.85),
        # "con X años"
        (r'\bcon\s+(\d{1,3})\s+años\b', 0.85),
        # "X años cumplidos"
        (r'\b(\d{1,3})\s+años\s+cumplidos\b', 0.9),
    ],

    MarkerType.DURATION: [
        # "durante X días/meses/años"
        (r'\bdurante\s+(\d+|un|una|dos|tres|algunos?|varios?)\s+(días?|semanas?|meses?|años?)\b', 0.9),
        # "por X tiempo"
        (r'\bpor\s+(\d+|un|una|largo)\s+(tiempo|rato|momento)\b', 0.8),
    ],

    MarkerType.FREQUENCY: [
        # "cada día", "todas las noches"
        (r'\b(cada|todos?\s+los?|todas?\s+las?)\s+(día|noche|mañana|semana|mes|año|lunes|martes|miércoles|jueves|viernes|sábado|domingo)s?\b', 0.9),
        # "siempre", "nunca"
        (r'\b(siempre|nunca|jamás|a\s+veces|a\s+menudo|frecuentemente)\b', 0.85),
    ],
}

# Conversión de palabras a números
WORD_TO_NUM = {
    'un': 1, 'una': 1, 'uno': 1,
    'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
    'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
    'once': 11, 'doce': 12, 'quince': 15, 'veinte': 20,
    'algunos': 3, 'varios': 3,  # Aproximación
}

class TemporalMarkerExtractor:
    def __init__(self):
        self.patterns = TEMPORAL_PATTERNS

    def extract(
        self,
        text: str,
        chapter: Optional[int] = None
    ) -> List[TemporalMarker]:
        """Extrae todos los marcadores temporales del texto."""
        markers = []

        for marker_type, patterns in self.patterns.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    marker = self._create_marker(
                        match, marker_type, confidence, chapter
                    )
                    markers.append(marker)

        # Ordenar por posición
        return sorted(markers, key=lambda m: m.start_char)

    def _create_marker(
        self,
        match: re.Match,
        marker_type: MarkerType,
        confidence: float,
        chapter: Optional[int]
    ) -> TemporalMarker:
        """Crea un marcador con información extraída."""
        marker = TemporalMarker(
            text=match.group(0),
            marker_type=marker_type,
            start_char=match.start(),
            end_char=match.end(),
            chapter=chapter,
            confidence=confidence
        )

        # Extraer información adicional según tipo
        if marker_type == MarkerType.RELATIVE_TIME:
            marker = self._parse_relative(marker, match)
        elif marker_type == MarkerType.CHARACTER_AGE:
            marker = self._parse_age(marker, match)

        return marker

    def _parse_relative(
        self,
        marker: TemporalMarker,
        match: re.Match
    ) -> TemporalMarker:
        """Parsea información de marcador relativo."""
        text_lower = marker.text.lower()

        # Dirección
        if any(w in text_lower for w in ['después', 'siguiente', 'más tarde']):
            marker.direction = 'future'
        elif any(w in text_lower for w in ['antes', 'anterior', 'atrás']):
            marker.direction = 'past'

        # Magnitud y cantidad
        groups = match.groups()
        if len(groups) >= 2:
            qty_str = groups[0].lower()
            marker.quantity = WORD_TO_NUM.get(qty_str) or (
                int(qty_str) if qty_str.isdigit() else None
            )
            marker.magnitude = groups[1].rstrip('s')  # Singular

        return marker

    def _parse_age(
        self,
        marker: TemporalMarker,
        match: re.Match
    ) -> TemporalMarker:
        """Parsea información de edad."""
        groups = match.groups()
        if groups:
            age_str = groups[0]
            if age_str.isdigit():
                marker.age = int(age_str)

        return marker

    def extract_with_entities(
        self,
        text: str,
        entity_mentions: List[Tuple[int, int, int]],  # (entity_id, start, end)
        chapter: Optional[int] = None
    ) -> List[TemporalMarker]:
        """Extrae marcadores y los asocia con entidades cercanas."""
        markers = self.extract(text, chapter)

        # Asociar edades con entidades
        for marker in markers:
            if marker.marker_type == MarkerType.CHARACTER_AGE:
                # Buscar entidad más cercana antes del marcador
                closest_entity = None
                min_distance = float('inf')

                for entity_id, start, end in entity_mentions:
                    if end <= marker.start_char:
                        distance = marker.start_char - end
                        if distance < min_distance and distance < 200:  # Max 200 chars
                            min_distance = distance
                            closest_entity = entity_id

                marker.entity_id = closest_entity

        return markers
```

---

## Criterio de DONE

```python
from narrative_assistant.temporal import TemporalMarkerExtractor, MarkerType

extractor = TemporalMarkerExtractor()

text = """
El 15 de marzo de 1985, cuando tenía 20 años, Juan dejó su pueblo.
Tres días después llegó a Madrid. Durante aquel verano trabajó
en una fábrica. Cada mañana se levantaba temprano.
"""

markers = extractor.extract(text)

# Verificar tipos detectados
types_found = {m.marker_type for m in markers}
assert MarkerType.ABSOLUTE_DATE in types_found
assert MarkerType.CHARACTER_AGE in types_found
assert MarkerType.RELATIVE_TIME in types_found
assert MarkerType.SEASON_EPOCH in types_found
assert MarkerType.FREQUENCY in types_found

# Verificar datos extraídos
age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
assert age_markers[0].age == 20

relative_markers = [m for m in markers if m.marker_type == MarkerType.RELATIVE_TIME]
assert relative_markers[0].quantity == 3
assert relative_markers[0].magnitude == 'día'

print(f"✅ Extraídos {len(markers)} marcadores temporales")
for m in markers:
    print(f"  - [{m.marker_type.value}] '{m.text}'")
```

---

## Siguiente

[STEP 4.2: Constructor de Timeline](./step-4.2-timeline-builder.md)
