"""
Mapa temporal para narrativas no lineales.

Proporciona una capa de mapping entre capítulos (discourse time) y
el tiempo de la historia (story time), permitiendo:
- Detectar si un capítulo es flashback/flashforward
- Calcular la edad de un personaje en cualquier capítulo
- Verificar si un personaje está vivo en un capítulo dado
- Calcular horas de viaje entre capítulos (para reachability)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class NarrativeType(str, Enum):
    """Tipo narrativo de un segmento temporal."""

    CHRONOLOGICAL = "chronological"
    ANALEPSIS = "analepsis"  # Flashback
    PROLEPSIS = "prolepsis"  # Flashforward
    PARALLEL = "parallel"  # Acción paralela


@dataclass
class TemporalSlice:
    """
    Slice temporal: mapea un capítulo a su posición en el tiempo de la historia.

    Attributes:
        chapter: Número de capítulo (discourse position)
        discourse_position: Posición ordinal en el texto
        story_date: Fecha absoluta en la historia (si conocida)
        day_offset: Offset en días desde Día 0 (si no hay fecha absoluta)
        narrative_type: Tipo narrativo del slice
        is_embedded: True si es flashback dentro de otro capítulo
        parent_chapter: Capítulo padre si es embedded
        confidence: Confianza en la clasificación (0-1)
    """

    chapter: int
    discourse_position: int = 0
    story_date: date | None = None
    day_offset: int | None = None
    narrative_type: NarrativeType = NarrativeType.CHRONOLOGICAL
    is_embedded: bool = False
    parent_chapter: int | None = None
    confidence: float = 0.5


@dataclass
class AgeReference:
    """
    Referencia de edad de un personaje en un punto temporal.

    Attributes:
        entity_id: ID de la entidad
        age: Edad mencionada
        chapter: Capítulo donde se menciona
        story_date: Fecha en la historia (si conocida)
        day_offset: Offset en días (si no hay fecha)
        confidence: Confianza en la referencia
    """

    entity_id: int
    age: int
    chapter: int
    story_date: date | None = None
    day_offset: int | None = None
    confidence: float = 0.8


class TemporalMap:
    """
    Mapa temporal que conecta discourse time (capítulos) con story time.

    Permite consultas como:
    - ¿En qué momento de la historia estamos en el capítulo 5?
    - ¿Está vivo el personaje X en el capítulo 7?
    - ¿Cuántas horas de viaje hay entre cap 3 y cap 4?
    """

    def __init__(self) -> None:
        self._slices: dict[int, TemporalSlice] = {}  # chapter → slice
        self._age_refs: dict[int, list[AgeReference]] = {}  # entity_id → refs
        self._death_times: dict[int, date | int | None] = (
            {}
        )  # entity_id → story_date or day_offset

    @classmethod
    def from_timeline(cls, timeline) -> "TemporalMap":
        """
        Construye un TemporalMap a partir de un Timeline existente.

        Args:
            timeline: Objeto Timeline con eventos temporales

        Returns:
            TemporalMap poblado con los datos del timeline
        """
        tmap = cls()

        for event in timeline.events:
            # Mapear narrative_order a NarrativeType
            narrative_type = NarrativeType.CHRONOLOGICAL
            order_value = getattr(event, "narrative_order", None)
            if order_value is not None:
                order_str = (
                    order_value.value
                    if hasattr(order_value, "value")
                    else str(order_value)
                )
                if order_str == "analepsis":
                    narrative_type = NarrativeType.ANALEPSIS
                elif order_str == "prolepsis":
                    narrative_type = NarrativeType.PROLEPSIS

            slice_ = TemporalSlice(
                chapter=event.chapter,
                discourse_position=getattr(event, "discourse_position", 0),
                story_date=event.story_date,
                day_offset=getattr(event, "day_offset", None),
                narrative_type=narrative_type,
                confidence=getattr(event, "confidence", 0.5),
            )

            # Solo añadir si no tenemos uno con mayor confianza
            existing = tmap._slices.get(event.chapter)
            if not existing or slice_.confidence > existing.confidence:
                tmap._slices[event.chapter] = slice_

        return tmap

    def add_slice(self, chapter: int, slice_: TemporalSlice) -> None:
        """Añade un slice temporal para un capítulo."""
        self._slices[chapter] = slice_

    def add_age_reference(self, ref: AgeReference) -> None:
        """Registra una referencia de edad."""
        if ref.entity_id not in self._age_refs:
            self._age_refs[ref.entity_id] = []
        self._age_refs[ref.entity_id].append(ref)

    def register_death(self, entity_id: int, death_chapter: int) -> None:
        """
        Registra la muerte de un personaje, usando story_time del capítulo.
        """
        slice_ = self._slices.get(death_chapter)
        if slice_:
            if slice_.story_date:
                self._death_times[entity_id] = slice_.story_date
            elif slice_.day_offset is not None:
                self._death_times[entity_id] = slice_.day_offset
            else:
                self._death_times[entity_id] = None
        else:
            self._death_times[entity_id] = None

    def get_story_time(self, chapter: int) -> date | int | None:
        """
        Obtiene el tiempo de la historia para un capítulo.

        Returns:
            date si hay fecha absoluta, int (day_offset) si es relativa, None si desconocido
        """
        slice_ = self._slices.get(chapter)
        if not slice_:
            return None
        if slice_.story_date:
            return slice_.story_date
        if slice_.day_offset is not None:
            return slice_.day_offset
        return None

    def get_narrative_type(self, chapter: int) -> NarrativeType:
        """Obtiene el tipo narrativo de un capítulo."""
        slice_ = self._slices.get(chapter)
        if not slice_:
            return NarrativeType.CHRONOLOGICAL
        return slice_.narrative_type

    def get_character_age_in_chapter(self, entity_id: int, chapter: int) -> int | None:
        """
        Calcula la edad de un personaje en un capítulo dado.

        Usa la referencia de edad más cercana y el delta temporal.
        """
        refs = self._age_refs.get(entity_id, [])
        if not refs:
            return None

        target_time = self.get_story_time(chapter)
        if target_time is None:
            return None

        # Buscar la referencia con mejor match temporal
        best_ref = None
        best_delta_days = None

        for ref in refs:
            ref_time = ref.story_date if ref.story_date else ref.day_offset
            if ref_time is None:
                # Usar el story_time del capítulo de referencia
                ref_time = self.get_story_time(ref.chapter)

            if ref_time is None:
                continue

            delta = self._compare_story_times(ref_time, target_time)
            if delta is not None:
                abs_delta = abs(delta)
                if best_delta_days is None or abs_delta < best_delta_days:
                    best_delta_days = abs_delta
                    best_ref = ref
                    # Store signed delta for age calculation
                    best_ref._delta_hours = delta  # type: ignore[attr-defined]

        if best_ref is None:
            return None

        delta_hours = getattr(best_ref, "_delta_hours", 0.0)
        delta_years = delta_hours / (24.0 * 365.25)
        age = best_ref.age + delta_years

        return max(0, int(age))

    def is_character_alive_in_chapter(self, entity_id: int, chapter: int) -> bool:
        """
        Verifica si un personaje está vivo en un capítulo dado.

        Compara story_time del capítulo con story_time de la muerte.
        Si no hay datos temporales, retorna True (fail-safe).
        """
        if entity_id not in self._death_times:
            return True  # No registrado como muerto

        death_time = self._death_times[entity_id]
        if death_time is None:
            return True  # Sin datos temporales de muerte → fail-safe

        chapter_time = self.get_story_time(chapter)
        if chapter_time is None:
            return True  # Sin datos temporales del capítulo → fail-safe

        # Comparar tiempos
        delta = self._compare_story_times(death_time, chapter_time)
        if delta is None:
            return True  # No se puede comparar → fail-safe

        # delta > 0 → chapter_time es posterior a death_time → muerto
        # delta <= 0 → chapter_time es anterior o igual a death_time → vivo
        return delta <= 0

    def get_story_time_gap_hours(self, ch1: int, ch2: int) -> float | None:
        """
        Calcula la diferencia en horas entre dos capítulos en story time.

        Returns:
            Horas entre ambos capítulos, o None si no se puede calcular.
        """
        t1 = self.get_story_time(ch1)
        t2 = self.get_story_time(ch2)

        if t1 is None or t2 is None:
            return None

        return self._compare_story_times(t1, t2)

    @staticmethod
    def _compare_story_times(
        t1: date | int | None,
        t2: date | int | None,
    ) -> float | None:
        """
        Compara dos tiempos de historia y devuelve diferencia en horas.

        Positivo si t2 > t1, negativo si t2 < t1.
        """
        if t1 is None or t2 is None:
            return None

        # Ambos son date
        if isinstance(t1, date) and isinstance(t2, date):
            delta = t2 - t1
            return delta.total_seconds() / 3600.0

        # Ambos son int (day_offset)
        if isinstance(t1, int) and isinstance(t2, int):
            return float((t2 - t1) * 24)

        # Tipos incompatibles
        return None
