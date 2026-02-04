"""
Constructor de timeline narrativo.

Construye una línea temporal a partir de marcadores temporales:
- Ordena eventos cronológicamente
- Detecta flashbacks (analepsis) y flashforwards (prolepsis)
- Verifica coherencia de edades de personajes
- Exporta a diferentes formatos (Mermaid, JSON)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from .markers import MarkerType, TemporalMarker, WORD_TO_NUM, MONTHS

logger = logging.getLogger(__name__)


class TimelineResolution(Enum):
    """Resolución temporal de un evento."""

    EXACT_DATE = "exact_date"  # 15 de marzo de 1985
    MONTH = "month"  # marzo de 1985
    YEAR = "year"  # 1985
    SEASON = "season"  # verano de 1985
    PARTIAL = "partial"  # 15 de marzo (sin año), martes
    RELATIVE = "relative"  # Día +3 (offset desde referencia)
    UNKNOWN = "unknown"  # sin fecha determinable


class NarrativeOrder(Enum):
    """Orden narrativo del evento."""

    CHRONOLOGICAL = "chronological"  # Orden lineal
    ANALEPSIS = "analepsis"  # Flashback
    PROLEPSIS = "prolepsis"  # Flashforward


@dataclass
class TimelineEvent:
    """
    Evento en la línea temporal narrativa.

    Attributes:
        id: Identificador único del evento
        description: Descripción del evento
        chapter: Número de capítulo
        paragraph: Número de párrafo
        story_date: Fecha en el tiempo de la historia
        story_date_resolution: Resolución de la fecha
        discourse_position: Posición en el texto (orden del discurso)
        relative_to: ID del evento de referencia (para relativos)
        relative_offset: Offset temporal respecto al evento de referencia
        narrative_order: Clasificación narrativa (cronológico, analepsis, prolepsis)
        entity_ids: IDs de personajes involucrados
        markers: Marcadores temporales asociados
        confidence: Nivel de confianza (0-1)
    """

    id: int
    description: str
    chapter: int
    paragraph: int = 0

    # Tiempo de la historia (story time)
    story_date: Optional[date] = None
    story_date_resolution: TimelineResolution = TimelineResolution.UNKNOWN

    # Para timelines sin fechas absolutas (Día 0, Día +1, etc.)
    day_offset: Optional[int] = None  # Offset en días desde el Día 0
    weekday: Optional[str] = None  # Día de la semana si se menciona (lunes, martes, etc.)

    # Tiempo del discurso (discourse time)
    discourse_position: int = 0

    # Relaciones temporales
    relative_to: Optional[int] = None
    relative_offset: Optional[timedelta] = None

    # Clasificación narrativa
    narrative_order: NarrativeOrder = NarrativeOrder.CHRONOLOGICAL

    # Personajes involucrados
    entity_ids: list[int] = field(default_factory=list)

    # Marcadores asociados
    markers: list[TemporalMarker] = field(default_factory=list)

    # Confianza
    confidence: float = 0.5


@dataclass
class Timeline:
    """
    Línea temporal completa de la narrativa.

    Attributes:
        events: Lista de eventos temporales
        anchor_events: IDs de eventos con fecha absoluta (anclas)
    """

    events: list[TimelineEvent] = field(default_factory=list)
    anchor_events: list[int] = field(default_factory=list)

    def add_event(self, event: TimelineEvent) -> None:
        """Añade un evento a la timeline."""
        self.events.append(event)
        if event.story_date_resolution == TimelineResolution.EXACT_DATE:
            self.anchor_events.append(event.id)

    def get_event_by_id(self, event_id: int) -> Optional[TimelineEvent]:
        """Obtiene un evento por su ID."""
        for event in self.events:
            if event.id == event_id:
                return event
        return None

    def get_chronological_order(self) -> list[TimelineEvent]:
        """Devuelve eventos ordenados por tiempo de historia."""
        dated = [e for e in self.events if e.story_date]
        undated = [e for e in self.events if not e.story_date]

        sorted_dated = sorted(dated, key=lambda e: e.story_date)  # type: ignore
        return sorted_dated + undated

    def get_discourse_order(self) -> list[TimelineEvent]:
        """Devuelve eventos ordenados por aparición en el texto."""
        return sorted(self.events, key=lambda e: e.discourse_position)

    def get_events_by_chapter(self, chapter: int) -> list[TimelineEvent]:
        """Devuelve eventos de un capítulo específico."""
        return [e for e in self.events if e.chapter == chapter]

    def get_analepsis_events(self) -> list[TimelineEvent]:
        """Devuelve eventos clasificados como analepsis (flashback)."""
        return [e for e in self.events if e.narrative_order == NarrativeOrder.ANALEPSIS]

    def get_prolepsis_events(self) -> list[TimelineEvent]:
        """Devuelve eventos clasificados como prolepsis (flashforward)."""
        return [e for e in self.events if e.narrative_order == NarrativeOrder.PROLEPSIS]

    def get_time_span(self) -> Optional[tuple[date, date]]:
        """Devuelve el rango temporal de la historia (fecha mínima, fecha máxima)."""
        dated = [e for e in self.events if e.story_date]
        if not dated:
            return None
        dates = [e.story_date for e in dated]
        return min(dates), max(dates)  # type: ignore


class TimelineBuilder:
    """
    Constructor de timeline a partir de marcadores temporales.

    Ejemplo de uso:
        builder = TimelineBuilder()
        timeline = builder.build_from_markers(markers, chapters)
    """

    def __init__(self):
        """Inicializa el constructor de timeline."""
        self.timeline = Timeline()
        self.event_counter = 0

    def build_from_markers(
        self,
        markers: list[TemporalMarker],
        chapters: list[dict],
    ) -> Timeline:
        """
        Construye timeline a partir de marcadores temporales.

        Args:
            markers: Lista de marcadores temporales
            chapters: Lista de capítulos con estructura:
                      {"number": int, "title": str, "start_position": int}

        Returns:
            Timeline construido
        """
        self.timeline = Timeline()
        self.event_counter = 0

        # 1. Crear eventos base para cada capítulo
        for chapter in chapters:
            self._create_chapter_event(chapter)

        # 2. Procesar marcadores absolutos (anclas)
        absolute_markers = [
            m for m in markers if m.marker_type == MarkerType.ABSOLUTE_DATE
        ]
        for marker in sorted(absolute_markers, key=lambda m: m.confidence, reverse=True):
            self._add_absolute_anchor(marker)

        # 3. Procesar marcadores relativos
        relative_markers = [
            m for m in markers if m.marker_type == MarkerType.RELATIVE_TIME
        ]

        # Si no hay anclas absolutas pero hay marcadores relativos,
        # crear una fecha sintética de referencia (Día 0)
        if relative_markers and not self.timeline.anchor_events:
            self._create_synthetic_anchor(relative_markers, chapters)

        self._resolve_relative_markers(relative_markers)

        # 4. Procesar edades de personajes
        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        self._process_age_markers(age_markers)

        # 5. Detectar analepsis/prolepsis
        self._detect_narrative_order()

        logger.info(
            f"Built timeline with {len(self.timeline.events)} events, "
            f"{len(self.timeline.anchor_events)} anchors"
        )

        return self.timeline

    def _create_chapter_event(self, chapter: dict) -> TimelineEvent:
        """Crea un evento base para un capítulo."""
        self.event_counter += 1
        event = TimelineEvent(
            id=self.event_counter,
            description=f"Capítulo {chapter.get('number', '?')}: {chapter.get('title', 'Sin título')}",
            chapter=chapter.get("number", 0),
            paragraph=0,
            discourse_position=chapter.get("start_position", 0),
        )
        self.timeline.add_event(event)
        return event

    def _create_synthetic_anchor(
        self,
        relative_markers: list[TemporalMarker],
        chapters: list[dict],
    ) -> None:
        """
        Crea un ancla sintética cuando no hay fechas absolutas.

        Usa el primer marcador temporal o el inicio del primer capítulo
        como "Día 0" para poder construir una línea temporal relativa.

        NO crea fechas ficticias (año 1) - usa day_offset en su lugar.
        """
        if not chapters:
            return

        # Encontrar el primer evento de capítulo
        first_chapter = min(chapters, key=lambda c: c.get("number", 0))
        first_chapter_num = first_chapter.get("number", 1)

        # Extraer día de la semana si se menciona en los marcadores
        weekday = None
        for marker in relative_markers:
            if marker.weekday:
                weekday = marker.weekday
                break

        # Buscar el evento del primer capítulo
        for event in self.timeline.events:
            if event.chapter == first_chapter_num:
                # Usar day_offset=0 en vez de fecha sintética
                event.day_offset = 0
                event.weekday = weekday
                event.story_date = None  # NO crear fecha ficticia
                event.story_date_resolution = TimelineResolution.RELATIVE
                event.description = f"{event.description} (Día 0 - referencia)"
                if event.id not in self.timeline.anchor_events:
                    self.timeline.anchor_events.append(event.id)
                logger.debug(
                    f"Created synthetic anchor at chapter {first_chapter_num}: "
                    f"day_offset=0, weekday={weekday}"
                )
                break

    def _add_absolute_anchor(self, marker: TemporalMarker) -> None:
        """Añade un punto de anclaje con fecha absoluta."""
        parsed_date = self._parse_date_from_marker(marker)
        if not parsed_date:
            return

        # Determinar resolución
        resolution = TimelineResolution.UNKNOWN
        if marker.day and marker.month and marker.year:
            resolution = TimelineResolution.EXACT_DATE
        elif marker.month and marker.year:
            resolution = TimelineResolution.MONTH
        elif marker.year:
            resolution = TimelineResolution.YEAR

        # Buscar evento del capítulo para actualizar
        if marker.chapter:
            chapter_events = [
                e for e in self.timeline.events if e.chapter == marker.chapter
            ]
            if chapter_events:
                event = chapter_events[0]
                # Solo actualizar si no tiene fecha o la nueva es más precisa
                if not event.story_date or resolution.value < event.story_date_resolution.value:
                    event.story_date = parsed_date
                    event.story_date_resolution = resolution
                    event.confidence = marker.confidence
                    event.markers.append(marker)
                    if event.id not in self.timeline.anchor_events:
                        self.timeline.anchor_events.append(event.id)
                return

        # Crear nuevo evento si no hay capítulo asociado
        self.event_counter += 1
        event = TimelineEvent(
            id=self.event_counter,
            description=f"Fecha: {marker.text}",
            chapter=marker.chapter or 0,
            paragraph=marker.paragraph or 0,
            discourse_position=marker.start_char,
            story_date=parsed_date,
            story_date_resolution=resolution,
            confidence=marker.confidence,
            markers=[marker],
        )
        self.timeline.add_event(event)

    def _parse_date_from_marker(self, marker: TemporalMarker) -> Optional[date]:
        """Extrae fecha de un marcador."""
        # Si ya tiene componentes parseados
        if marker.year:
            try:
                return date(
                    marker.year,
                    marker.month or 1,
                    marker.day or 1,
                )
            except ValueError:
                return None

        # Intentar parsear del texto
        text_lower = marker.text.lower()

        # Patrón completo: "15 de marzo de 1985"
        import re

        full_match = re.search(
            r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
            text_lower,
        )
        if full_match:
            try:
                return date(
                    int(full_match.group(3)),
                    MONTHS.get(full_match.group(2), 1),
                    int(full_match.group(1)),
                )
            except ValueError:
                return None

        # Solo año
        year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text_lower)
        if year_match:
            return date(int(year_match.group(1)), 1, 1)

        return None

    def _resolve_relative_markers(self, markers: list[TemporalMarker]) -> None:
        """
        Resuelve marcadores relativos usando anclas o encadenándolos entre sí.

        Los marcadores se procesan en orden de aparición en el texto.
        Cada marcador relativo usa el evento anterior como referencia,
        permitiendo construir una cadena temporal incluso sin fechas absolutas.

        Cuando no hay fechas absolutas, usa day_offset (Día 0, Día +1, etc.)
        """
        # Ordenar marcadores por posición en el texto
        sorted_markers = sorted(markers, key=lambda m: (m.chapter or 0, m.start_char))

        # Último evento de referencia (para encadenar relativos)
        last_ref_event: Optional[TimelineEvent] = None

        # Inicializar con el ancla si existe
        if self.timeline.anchor_events:
            for event in self.timeline.events:
                if event.id in self.timeline.anchor_events:
                    last_ref_event = event
                    break

        for marker in sorted_markers:
            # Prioridad para referencia:
            # 1. Último evento de referencia (encadenamiento de relativos)
            # 2. Ancla más cercana
            # 3. Evento del capítulo
            reference_event = last_ref_event

            if not reference_event:
                # Intentar con ancla
                anchor = self._find_nearest_anchor(
                    marker.chapter or 0, marker.start_char
                )
                reference_event = anchor

            if not reference_event:
                # Usar el evento del capítulo como referencia
                chapter_events = [
                    e for e in self.timeline.events
                    if e.chapter == (marker.chapter or 0)
                ]
                if chapter_events:
                    reference_event = chapter_events[0]

            # Calcular offset
            offset = self._calculate_offset(marker)
            offset_days = offset.days if offset else 1  # Default: +1 día

            # Calcular nueva fecha o day_offset
            new_date = None
            new_day_offset = None
            direction = marker.direction or "future"

            if reference_event:
                if reference_event.story_date and offset:
                    # Hay fecha absoluta: calcular nueva fecha
                    if direction == "future":
                        new_date = reference_event.story_date + offset
                    elif direction == "past":
                        new_date = reference_event.story_date - offset
                elif reference_event.day_offset is not None:
                    # Sin fecha absoluta: usar day_offset
                    if direction == "future":
                        new_day_offset = reference_event.day_offset + offset_days
                    elif direction == "past":
                        new_day_offset = reference_event.day_offset - offset_days
                    else:
                        new_day_offset = reference_event.day_offset + offset_days

            # Crear evento
            self.event_counter += 1
            event = TimelineEvent(
                id=self.event_counter,
                description=f"{marker.text}",
                chapter=marker.chapter or 0,
                paragraph=marker.paragraph or 0,
                discourse_position=marker.start_char,
                story_date=new_date,
                day_offset=new_day_offset,
                weekday=marker.weekday if hasattr(marker, 'weekday') else None,
                story_date_resolution=(
                    TimelineResolution.EXACT_DATE if new_date
                    else TimelineResolution.RELATIVE if new_day_offset is not None
                    else TimelineResolution.UNKNOWN
                ),
                relative_to=reference_event.id if reference_event else None,
                relative_offset=offset,
                confidence=marker.confidence * 0.8,
                markers=[marker],
            )
            self.timeline.add_event(event)

            # Actualizar evento de referencia para encadenamiento
            if new_date or new_day_offset is not None:
                last_ref_event = event

            # Actualizar último evento con fecha para encadenamiento
            if new_date:
                last_dated_event = event

    def _find_nearest_anchor(
        self,
        chapter: int,
        position: int,
    ) -> Optional[TimelineEvent]:
        """Encuentra el evento ancla más cercano."""
        anchors = [
            e
            for e in self.timeline.events
            if e.id in self.timeline.anchor_events and e.story_date
        ]

        if not anchors:
            return None

        # Buscar en mismo capítulo primero
        same_chapter = [
            a for a in anchors if a.chapter == chapter and a.discourse_position <= position
        ]
        if same_chapter:
            return max(same_chapter, key=lambda a: a.discourse_position)

        # Buscar en capítulos anteriores
        previous = [a for a in anchors if a.chapter < chapter]
        if previous:
            return max(previous, key=lambda a: a.discourse_position)

        # Devolver el primer ancla disponible
        return anchors[0]

    def _calculate_offset(self, marker: TemporalMarker) -> Optional[timedelta]:
        """Calcula el offset temporal de un marcador relativo."""
        text_lower = marker.text.lower()

        # Intentar valores por defecto para expresiones comunes
        if not marker.quantity or not marker.magnitude:
            if "día siguiente" in text_lower or "mañana siguiente" in text_lower:
                return timedelta(days=1)
            if "noche anterior" in text_lower or "día anterior" in text_lower:
                return timedelta(days=1)
            if "poco después" in text_lower:
                return timedelta(hours=2)
            if "más tarde" in text_lower:
                return timedelta(hours=4)
            # Expresiones con días de semana o momentos del día
            if any(d in text_lower for d in ["aquella", "aquel", "esa", "ese"]):
                # "aquella mañana", "ese día" - asumir mismo día o cercano
                return timedelta(days=0)
            return None

        magnitude_to_days = {
            "día": 1,
            "semana": 7,
            "mes": 30,
            "año": 365,
            "hora": 0.042,  # ~1 hora
        }

        days = marker.quantity * magnitude_to_days.get(marker.magnitude, 1)
        return timedelta(days=days)

    def _process_age_markers(self, markers: list[TemporalMarker]) -> None:
        """Procesa marcadores de edad de personajes."""
        for marker in markers:
            if not marker.age:
                continue

            # Crear evento para la mención de edad
            self.event_counter += 1
            event = TimelineEvent(
                id=self.event_counter,
                description=f"Edad mencionada: {marker.text}",
                chapter=marker.chapter or 0,
                paragraph=marker.paragraph or 0,
                discourse_position=marker.start_char,
                entity_ids=[marker.entity_id] if marker.entity_id else [],
                confidence=marker.confidence,
                markers=[marker],
            )
            self.timeline.add_event(event)

    def _detect_narrative_order(self) -> None:
        """
        Detecta analepsis y prolepsis comparando orden cronológico vs discurso.

        Usa un algoritmo de "marca de agua alta" (high-water mark) para seguir
        la pista cronológica global, no solo comparar con el evento anterior.

        Una ANALEPSIS ocurre cuando:
        1. El evento actual está ANTES cronológicamente que la marca de agua
        2. Y hay evidencia adicional (marcadores retrospectivos o salto temporal significativo)

        Esto evita falsos positivos cuando la narrativa simplemente salta en el tiempo
        sin indicar explícitamente un flashback.

        Soporta tanto fechas absolutas (story_date) como offsets relativos (day_offset).
        """
        chronological = self.timeline.get_chronological_order()
        discourse = self.timeline.get_discourse_order()

        logger.info(f"[TIMELINE] Total eventos: {len(chronological)} cronológicos, {len(discourse)} en discurso")

        # Eventos con tiempo conocido (fecha O day_offset)
        def has_time(e: TimelineEvent) -> bool:
            return e.story_date is not None or e.day_offset is not None

        dated_chrono = [e for e in chronological if has_time(e)]
        dated_discourse = [e for e in discourse if has_time(e)]

        logger.info(f"[TIMELINE] Eventos con tiempo: {len(dated_chrono)} de {len(chronological)}")
        if dated_chrono:
            dates = [e.story_date for e in dated_chrono if e.story_date]
            offsets = [e.day_offset for e in dated_chrono if e.day_offset is not None]
            if dates:
                logger.info(f"[TIMELINE] Rango fechas: {min(dates)} → {max(dates)}")
            if offsets:
                logger.info(f"[TIMELINE] Rango días: Día {min(offsets)} → Día +{max(offsets)}")

        if len(dated_chrono) < 2:
            logger.info("[TIMELINE] Insuficientes eventos fechados para detectar analepsis/prolepsis")
            return

        # Crear índice cronológico: evento.id -> posición en orden cronológico
        chrono_index = {e.id: i for i, e in enumerate(dated_chrono)}

        analepsis_count = 0
        prolepsis_count = 0

        # High-water mark: máxima posición cronológica vista hasta ahora
        # Esto permite detectar analepsis correctamente en secuencias lineales
        chrono_high_water = -1

        # Comparar con orden del discurso
        for i, event in enumerate(dated_discourse):
            chrono_pos_current = chrono_index.get(event.id, -1)

            if chrono_pos_current == -1:
                continue  # Evento no encontrado en el índice

            if i == 0:
                # Primer evento: establecer marca de agua inicial
                chrono_high_water = chrono_pos_current
                continue

            # Verificar evidencia de analepsis/prolepsis
            has_retrospective_marker = self._has_retrospective_evidence(event)
            has_prospective_marker = self._has_prospective_evidence(event)

            # Calcular diferencia temporal con el high water
            time_diff_days = self._calculate_time_difference(
                dated_chrono[chrono_high_water] if chrono_high_water < len(dated_chrono) else None,
                event
            )

            # ANALEPSIS: el evento actual está ANTES cronológicamente
            if chrono_pos_current < chrono_high_water:
                # Requiere evidencia adicional para clasificar como flashback:
                # - Marcadores retrospectivos ("recordó", "años atrás", direction=past)
                # - O un salto temporal muy significativo (>90 días hacia atrás)
                if has_retrospective_marker:
                    event.narrative_order = NarrativeOrder.ANALEPSIS
                    analepsis_count += 1
                    logger.info(
                        f"[TIMELINE] ANALEPSIS detectada (con marcador): '{event.description[:50]}...' "
                        f"(pos discurso={i}, pos crono={chrono_pos_current} < high_water={chrono_high_water})"
                    )
                elif time_diff_days is not None and time_diff_days < -90:
                    # Salto muy significativo hacia el pasado (>3 meses)
                    event.narrative_order = NarrativeOrder.ANALEPSIS
                    analepsis_count += 1
                    logger.info(
                        f"[TIMELINE] ANALEPSIS detectada (por salto temporal): '{event.description[:50]}...' "
                        f"(salto de {abs(time_diff_days)} días al pasado)"
                    )
                else:
                    # Sin evidencia suficiente - podría ser solo la narrativa saltando
                    logger.debug(
                        f"[TIMELINE] Posible analepsis descartada (sin evidencia): '{event.description[:50]}...' "
                        f"(pos crono={chrono_pos_current} < high_water={chrono_high_water}, diff={time_diff_days} días)"
                    )

            # PROLEPSIS: salto significativo hacia el futuro
            elif chrono_pos_current > chrono_high_water + 3:
                if time_diff_days is not None and time_diff_days > 365:  # Más de un año
                    if has_prospective_marker:
                        event.narrative_order = NarrativeOrder.PROLEPSIS
                        prolepsis_count += 1
                        logger.info(
                            f"[TIMELINE] PROLEPSIS detectada: '{event.description[:50]}...' "
                            f"(salto de {time_diff_days} días)"
                        )
                    elif time_diff_days > 730:  # Más de 2 años sin marcador
                        event.narrative_order = NarrativeOrder.PROLEPSIS
                        prolepsis_count += 1
                        logger.info(
                            f"[TIMELINE] PROLEPSIS detectada (por salto temporal): '{event.description[:50]}...' "
                            f"(salto de {time_diff_days} días)"
                        )

            # Actualizar marca de agua alta
            chrono_high_water = max(chrono_high_water, chrono_pos_current)

        logger.info(f"[TIMELINE] Resultado: {analepsis_count} analepsis, {prolepsis_count} prolepsis")

    def _has_retrospective_evidence(self, event: TimelineEvent) -> bool:
        """
        Verifica si el evento tiene evidencia de ser un flashback/analepsis.

        Busca:
        - Marcadores temporales con direction='past'
        - Verbos de memoria en la descripción (recordó, evocó, rememoró)
        - Expresiones retrospectivas (años atrás, tiempo antes)
        """
        # Verbos y expresiones que indican flashback
        retrospective_patterns = [
            "recordó", "recordaba", "evocó", "evocaba", "rememoró", "rememoraba",
            "vino a su mente", "le vino a la memoria", "pensó en aquel",
            "años atrás", "tiempo atrás", "meses atrás", "días atrás",
            "en el pasado", "en aquella época", "en aquel entonces",
            "hacía tiempo", "hacía años", "hacía meses",
            "cuando era", "de joven", "de niño", "de pequeño",
        ]

        # Verificar descripción del evento
        desc_lower = event.description.lower()
        if any(pattern in desc_lower for pattern in retrospective_patterns):
            return True

        # Verificar marcadores asociados
        for marker in event.markers:
            if hasattr(marker, 'direction') and marker.direction == "past":
                return True
            # Verificar texto del marcador
            marker_lower = marker.text.lower()
            if any(pattern in marker_lower for pattern in ["antes", "atrás", "anterior", "pasado"]):
                return True

        return False

    def _has_prospective_evidence(self, event: TimelineEvent) -> bool:
        """
        Verifica si el evento tiene evidencia de ser una prolepsis/flashforward.

        Busca:
        - Marcadores temporales con direction='future'
        - Verbos de anticipación (presagiaba, vendría, ocurriría)
        - Expresiones prospectivas (años después, en el futuro)
        """
        prospective_patterns = [
            "años después", "tiempo después", "meses después",
            "en el futuro", "vendría", "ocurriría", "sucedería",
            "presagiaba", "anticipaba", "no sabía que",
            "llegaría el día", "algún día", "más adelante",
        ]

        desc_lower = event.description.lower()
        if any(pattern in desc_lower for pattern in prospective_patterns):
            return True

        for marker in event.markers:
            if hasattr(marker, 'direction') and marker.direction == "future":
                return True

        return False

    def _calculate_time_difference(
        self, ref_event: Optional[TimelineEvent], target_event: TimelineEvent
    ) -> Optional[int]:
        """
        Calcula diferencia en días entre dos eventos.

        Returns:
            Diferencia en días (negativo si target está antes de ref), o None si no se puede calcular.
        """
        if not ref_event:
            return None

        # Intentar con fechas absolutas
        if ref_event.story_date and target_event.story_date:
            delta = target_event.story_date - ref_event.story_date
            return delta.days

        # Intentar con day_offset
        if ref_event.day_offset is not None and target_event.day_offset is not None:
            return target_event.day_offset - ref_event.day_offset

        return None

    def export_to_mermaid(self) -> str:
        """Exporta timeline a diagrama Mermaid (Gantt)."""
        lines = ["gantt", "    title Timeline Narrativo", "    dateFormat YYYY-MM-DD"]

        chrono = self.timeline.get_chronological_order()
        dated = [e for e in chrono if e.story_date]

        if not dated:
            return "No hay eventos con fechas determinadas."

        # Agrupar por año
        by_year: dict[int, list[TimelineEvent]] = defaultdict(list)
        for event in dated:
            if event.story_date:
                by_year[event.story_date.year].append(event)

        for year in sorted(by_year.keys()):
            lines.append(f"    section {year}")
            for event in by_year[year]:
                desc = event.description[:30].replace(":", "-").replace(",", " ")
                date_str = event.story_date.strftime("%Y-%m-%d") if event.story_date else ""
                # Marcar analepsis/prolepsis
                marker = ""
                if event.narrative_order == NarrativeOrder.ANALEPSIS:
                    marker = " [FLASHBACK]"
                elif event.narrative_order == NarrativeOrder.PROLEPSIS:
                    marker = " [FLASHFORWARD]"
                lines.append(f"    {desc}{marker} :{date_str}, 1d")

        return "\n".join(lines)

    def export_to_json(self) -> dict:
        """Exporta timeline a formato JSON serializable."""
        events_data = []
        for event in self.timeline.events:
            events_data.append(
                {
                    "id": event.id,
                    "description": event.description,
                    "chapter": event.chapter,
                    "paragraph": event.paragraph,
                    "story_date": (
                        event.story_date.isoformat() if event.story_date else None
                    ),
                    "story_date_resolution": event.story_date_resolution.value,
                    "discourse_position": event.discourse_position,
                    "narrative_order": event.narrative_order.value,
                    "entity_ids": event.entity_ids,
                    "confidence": event.confidence,
                }
            )

        time_span = self.timeline.get_time_span()

        # Detectar si las fechas son sintéticas (año 1 = fecha ficticia)
        # Las fechas sintéticas se usan cuando no hay fechas absolutas en el texto
        is_synthetic = False
        has_real_dates = False
        duration_days = 0

        if time_span:
            start_date, end_date = time_span
            # Año 1 indica fechas sintéticas (no hay fechas reales en el texto)
            is_synthetic = start_date.year == 1 or end_date.year == 1
            has_real_dates = not is_synthetic
            duration_days = (end_date - start_date).days

        return {
            "total_events": len(self.timeline.events),
            "anchor_events": len(self.timeline.anchor_events),
            "analepsis_count": len(self.timeline.get_analepsis_events()),
            "prolepsis_count": len(self.timeline.get_prolepsis_events()),
            "time_span": (
                {
                    # Solo exponer fechas reales al frontend
                    "start": time_span[0].isoformat() if has_real_dates else None,
                    "end": time_span[1].isoformat() if has_real_dates else None,
                    "duration_days": duration_days,
                    "is_synthetic": is_synthetic,
                    "has_real_dates": has_real_dates,
                }
                if time_span
                else None
            ),
            "events": events_data,
        }
