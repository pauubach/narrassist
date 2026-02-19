"""
Detector de inconsistencias temporales con votación multi-método.

Sistema de Votación Ponderada:
1. **Análisis directo** (35%): Comparación directa de fechas y edades
2. **Análisis contextual** (25%): Patrones narrativos y transiciones
3. **LLM semántico** (25%): Comprensión profunda de contexto temporal
4. **Heurísticas narrativas** (15%): Reglas de género y estructura

Detecta problemas en la coherencia temporal:
- Contradicciones de edad de personajes
- Eventos imposibles cronológicamente
- Saltos temporales sospechosos
- Inconsistencias entre marcadores
- Anacronismos
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from .markers import MarkerType, TemporalMarker
from .timeline import NarrativeOrder, Timeline

logger = logging.getLogger(__name__)


# =============================================================================
# Enums y Configuración del Sistema de Votación
# =============================================================================


class TemporalDetectionMethod(Enum):
    """Métodos de detección de inconsistencias temporales."""

    DIRECT = "direct"  # Análisis directo de fechas/edades
    CONTEXTUAL = "contextual"  # Patrones de transición y contexto
    LLM = "llm"  # LLM local para análisis semántico
    HEURISTICS = "heuristics"  # Heurísticas narrativas


# Pesos por defecto para votación
DEFAULT_TEMPORAL_WEIGHTS = {
    TemporalDetectionMethod.DIRECT: 0.35,
    TemporalDetectionMethod.CONTEXTUAL: 0.25,
    TemporalDetectionMethod.LLM: 0.25,
    TemporalDetectionMethod.HEURISTICS: 0.15,
}

# Bonus por acuerdo entre métodos
TEMPORAL_AGREEMENT_BONUS = 1.15


def _get_default_temporal_methods() -> list[TemporalDetectionMethod]:
    """Retorna los métodos habilitados por defecto según el hardware."""
    try:
        from ..core.device import get_device_config

        device_config = get_device_config()
        has_gpu = device_config.device_type in ("cuda", "mps")
    except Exception:
        has_gpu = False

    if has_gpu:
        return list(TemporalDetectionMethod)
    else:
        return [
            TemporalDetectionMethod.DIRECT,
            TemporalDetectionMethod.CONTEXTUAL,
            TemporalDetectionMethod.HEURISTICS,
        ]


@dataclass
class TemporalDetectionConfig:
    """Configuración del sistema de detección temporal."""

    enabled_methods: list[TemporalDetectionMethod] = field(
        default_factory=_get_default_temporal_methods
    )
    method_weights: dict[TemporalDetectionMethod, float] = field(
        default_factory=lambda: DEFAULT_TEMPORAL_WEIGHTS.copy()
    )
    min_confidence: float = 0.5
    consensus_threshold: float = 0.5
    ollama_model: str = "llama3.2"
    use_llm: bool = field(default=None)

    # Umbrales para detección
    impossible_sequence_days: int = 7  # Días para considerar secuencia imposible
    suspicious_jump_years: int = 5  # Años para considerar salto sospechoso
    age_tolerance_years: float = 1.5  # Tolerancia en años para edades

    def __post_init__(self):
        """Ajusta configuración según hardware si use_llm es None."""
        if self.use_llm is None:
            self.use_llm = TemporalDetectionMethod.LLM in self.enabled_methods
        elif self.use_llm and TemporalDetectionMethod.LLM not in self.enabled_methods:
            self.enabled_methods.append(TemporalDetectionMethod.LLM)
        elif not self.use_llm and TemporalDetectionMethod.LLM in self.enabled_methods:
            self.enabled_methods.remove(TemporalDetectionMethod.LLM)


class InconsistencyType(Enum):
    """Tipos de inconsistencias temporales."""

    AGE_CONTRADICTION = "age_contradiction"  # Edades que no cuadran
    IMPOSSIBLE_SEQUENCE = "impossible_sequence"  # Eventos en orden imposible
    TIME_JUMP_SUSPICIOUS = "time_jump_suspicious"  # Salto temporal sospechoso
    MARKER_CONFLICT = "marker_conflict"  # Marcadores contradictorios
    CHARACTER_AGE_MISMATCH = "character_age_mismatch"  # Edad no coincide con fechas
    ANACHRONISM = "anachronism"  # Referencia anacrónica
    # Level C: Cross-chapter linking
    CROSS_CHAPTER_AGE_REGRESSION = "cross_chapter_age_regression"  # Edad retrocede sin flashback
    PHASE_AGE_INCOMPATIBLE = "phase_age_incompatible"  # Fase vital incompatible con edad
    BIRTH_YEAR_CONTRADICTION = "birth_year_contradiction"  # Año de nacimiento contradictorio


class InconsistencySeverity(Enum):
    """Severidad de la inconsistencia."""

    LOW = "low"  # Posible problema menor
    MEDIUM = "medium"  # Problema probable
    HIGH = "high"  # Inconsistencia clara
    CRITICAL = "critical"  # Error evidente


@dataclass
class TemporalInconsistency:
    """
    Inconsistencia temporal detectada.

    Attributes:
        inconsistency_type: Tipo de inconsistencia
        severity: Severidad del problema
        description: Descripción del problema
        chapter: Capítulo donde se detecta
        position: Posición en el texto
        events_involved: IDs de eventos involucrados
        markers_involved: Marcadores temporales involucrados
        expected: Valor esperado
        found: Valor encontrado
        suggestion: Sugerencia de corrección
        confidence: Nivel de confianza en la detección
        methods_agreed: Métodos que detectaron esta inconsistencia
        reasoning: Razonamiento de cada método
    """

    inconsistency_type: InconsistencyType
    severity: InconsistencySeverity
    description: str
    chapter: int
    position: int
    events_involved: list[int] = field(default_factory=list)
    markers_involved: list[TemporalMarker] = field(default_factory=list)
    expected: str | None = None
    found: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8
    methods_agreed: list[str] = field(default_factory=list)
    reasoning: dict[str, str] = field(default_factory=dict)


class TemporalConsistencyChecker:
    """
    Verificador de consistencia temporal en narrativas.

    Ejemplo de uso:
        checker = TemporalConsistencyChecker()
        inconsistencies = checker.check(timeline, markers, character_ages)
    """

    def __init__(self, config: TemporalDetectionConfig | None = None):
        """
        Inicializa el verificador.

        Args:
            config: Configuración del sistema de votación (opcional)
        """
        self.config = config or TemporalDetectionConfig()
        self.inconsistencies: list[TemporalInconsistency] = []
        self._llm_validator: LLMTemporalValidator | None = None
        self._init_validators()

    def _init_validators(self) -> None:
        """Inicializa los validadores según la configuración."""
        if TemporalDetectionMethod.LLM in self.config.enabled_methods:
            try:
                self._llm_validator = LLMTemporalValidator(model=self.config.ollama_model)
            except Exception as e:
                logger.warning(f"No se pudo inicializar validador LLM: {e}")

    def check(
        self,
        timeline: Timeline,
        markers: list[TemporalMarker],
        character_ages: dict[int, list[tuple[int, int]]] | None = None,
    ) -> list[TemporalInconsistency]:
        """
        Verifica consistencia temporal completa.

        Args:
            timeline: Timeline construido
            markers: Lista de marcadores temporales
            character_ages: Dict de entity_id -> [(chapter, age), ...]

        Returns:
            Lista de inconsistencias detectadas
        """
        self.inconsistencies = []

        # 1. Verificar secuencias imposibles
        self._check_impossible_sequences(timeline)

        # 2. Verificar conflictos entre marcadores
        self._check_marker_conflicts(markers)

        # 3. Verificar edades de personajes
        if character_ages:
            self._check_character_ages(timeline, character_ages)

        # 4. Verificar saltos temporales sospechosos
        self._check_suspicious_jumps(timeline)

        # 5. Verificar anacronismos
        self._check_anachronisms(timeline, markers)

        logger.info(f"Found {len(self.inconsistencies)} temporal inconsistencies")

        return sorted(
            self.inconsistencies,
            key=lambda i: (i.severity.value, i.chapter, i.position),
            reverse=True,
        )

    def _check_impossible_sequences(self, timeline: Timeline) -> None:
        """Detecta secuencias de eventos cronológicamente imposibles."""
        discourse_order = timeline.get_discourse_order()
        dated_events = [e for e in discourse_order if e.story_date]

        if len(dated_events) < 2:
            return

        for i in range(1, len(dated_events)):
            current = dated_events[i]
            prev = dated_events[i - 1]

            # Saltar si uno de los dos es analepsis/prolepsis declarado
            if (
                current.narrative_order != NarrativeOrder.CHRONOLOGICAL
                or prev.narrative_order != NarrativeOrder.CHRONOLOGICAL
            ):
                continue

            # Verificar si hay una regresión temporal no declarada
            if current.story_date and prev.story_date:
                if current.story_date < prev.story_date:
                    delta = prev.story_date - current.story_date

                    # Si el retroceso es significativo, es probable inconsistencia
                    if delta.days > 7:  # Más de una semana
                        self.inconsistencies.append(
                            TemporalInconsistency(
                                inconsistency_type=InconsistencyType.IMPOSSIBLE_SEQUENCE,
                                severity=InconsistencySeverity.HIGH,
                                description=(
                                    f"El evento '{current.description[:50]}' ocurre "
                                    f"cronológicamente antes que '{prev.description[:50]}', "
                                    f"pero aparece después en el texto sin indicar flashback."
                                ),
                                chapter=current.chapter,
                                position=current.discourse_position,
                                events_involved=[prev.id, current.id],
                                expected=f"Fecha posterior a {prev.story_date}",
                                found=str(current.story_date),
                                suggestion=(
                                    "Considerar añadir un marcador de flashback o "
                                    "revisar las fechas."
                                ),
                                confidence=0.85,
                            )
                        )

    def _check_marker_conflicts(self, markers: list[TemporalMarker]) -> None:
        """Detecta conflictos entre marcadores temporales cercanos."""
        # Agrupar marcadores por capítulo
        by_chapter: dict[int, list[TemporalMarker]] = {}
        for marker in markers:
            chapter = marker.chapter or 0
            if chapter not in by_chapter:
                by_chapter[chapter] = []
            by_chapter[chapter].append(marker)

        for chapter, chapter_markers in by_chapter.items():
            # Ordenar por posición
            sorted_markers = sorted(chapter_markers, key=lambda m: m.start_char)

            # Buscar marcadores relativos contradictorios
            for i, marker in enumerate(sorted_markers):
                if marker.marker_type != MarkerType.RELATIVE_TIME:
                    continue

                # Buscar marcadores cercanos
                for j, other in enumerate(sorted_markers):
                    if i == j or other.marker_type != MarkerType.RELATIVE_TIME:
                        continue

                    # Si están cerca (menos de 500 caracteres)
                    distance = abs(marker.start_char - other.start_char)
                    if distance < 500:
                        # Verificar contradicción de dirección
                        if (
                            marker.direction
                            and other.direction
                            and marker.direction != other.direction
                        ):
                            self.inconsistencies.append(
                                TemporalInconsistency(
                                    inconsistency_type=InconsistencyType.MARKER_CONFLICT,
                                    severity=InconsistencySeverity.MEDIUM,
                                    description=(
                                        f"Marcadores temporales contradictorios: "
                                        f"'{marker.text}' ({marker.direction}) y "
                                        f"'{other.text}' ({other.direction})"
                                    ),
                                    chapter=chapter,
                                    position=min(marker.start_char, other.start_char),
                                    markers_involved=[marker, other],
                                    suggestion=(
                                        "Revisar la coherencia de las referencias "
                                        "temporales en este pasaje."
                                    ),
                                    confidence=0.7,
                                )
                            )

        # Detectar fechas absolutas conflictivas entre capítulos
        self._check_cross_chapter_date_conflicts(markers)

    def _check_cross_chapter_date_conflicts(self, markers: list[TemporalMarker]) -> None:
        """
        Detecta fechas absolutas que difieren entre capítulos para el mismo evento.

        Estrategia: compara marcadores ABSOLUTE_DATE de diferentes capítulos.
        Si comparten contexto textual (palabras clave cercanas) pero tienen
        años distintos, es una inconsistencia.
        """
        import re

        absolute = [
            m for m in markers if m.marker_type == MarkerType.ABSOLUTE_DATE and m.year and m.chapter
        ]
        if len(absolute) < 2:
            return

        # Extraer palabras clave del texto del marcador y contexto cercano
        def _context_words(marker: TemporalMarker) -> set[str]:
            """Extrae palabras significativas del texto del marcador."""
            text = marker.text or ""
            # Extraer palabras de más de 3 chars, excluyendo números y stopwords
            words = re.findall(r"[A-ZÁÉÍÓÚÜÑa-záéíóúüñ]{4,}", text)
            return {w.lower() for w in words}

        # Comparar pares de marcadores en distintos capítulos
        checked: set[tuple[int, int]] = set()
        for i, m1 in enumerate(absolute):
            for j, m2 in enumerate(absolute):
                if i >= j:
                    continue
                if m1.chapter == m2.chapter:
                    continue
                if m1.year == m2.year:
                    continue

                pair_key = (min(i, j), max(i, j))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                # Las fechas difieren entre capítulos - posible conflicto
                # Calcular similitud: ¿comparten contexto?
                words1 = _context_words(m1)
                words2 = _context_words(m2)
                shared = words1 & words2

                # Si comparten palabras de contexto o los años están muy cerca,
                # es probable que se refieran al mismo evento
                years_close = abs(m1.year - m2.year) <= 10

                if shared or years_close:
                    confidence = 0.6
                    if shared and years_close:
                        confidence = 0.85
                    elif shared:
                        confidence = 0.75

                    self.inconsistencies.append(
                        TemporalInconsistency(
                            inconsistency_type=InconsistencyType.MARKER_CONFLICT,
                            severity=InconsistencySeverity.HIGH,
                            description=(
                                f"Posible conflicto de fechas: "
                                f"'{m1.text}' (cap. {m1.chapter}) vs "
                                f"'{m2.text}' (cap. {m2.chapter}). "
                                f"Años {m1.year} y {m2.year} difieren."
                            ),
                            chapter=m2.chapter or 0,
                            position=m2.start_char,
                            markers_involved=[m1, m2],
                            expected=f"Año {m1.year} (cap. {m1.chapter})",
                            found=f"Año {m2.year} (cap. {m2.chapter})",
                            suggestion=(
                                f"Verificar si ambas fechas ({m1.year} y {m2.year}) "
                                f"se refieren al mismo evento."
                            ),
                            confidence=confidence,
                        )
                    )

    def _check_character_ages(
        self,
        timeline: Timeline,
        character_ages: dict[int, list[tuple[int, int]]],
    ) -> None:
        """
        Verifica coherencia de edades de personajes.

        Args:
            timeline: Timeline con eventos
            character_ages: Dict de entity_id -> [(chapter, age), ...]
        """
        for entity_id, age_mentions in character_ages.items():
            if len(age_mentions) < 2:
                continue

            # Ordenar por capítulo
            sorted_mentions = sorted(age_mentions, key=lambda x: x[0])

            # Buscar fechas en los capítulos correspondientes
            chapter_dates: dict[int, date | None] = {}
            for event in timeline.events:
                if event.story_date:
                    chapter_dates[event.chapter] = event.story_date

            # Verificar coherencia
            for i in range(1, len(sorted_mentions)):
                prev_chapter, prev_age = sorted_mentions[i - 1]
                curr_chapter, curr_age = sorted_mentions[i]

                prev_date = chapter_dates.get(prev_chapter)
                curr_date = chapter_dates.get(curr_chapter)

                if prev_date and curr_date:
                    # Calcular diferencia de tiempo
                    time_diff = curr_date - prev_date
                    years_passed = time_diff.days / 365.25

                    # Diferencia de edad declarada
                    age_diff = curr_age - prev_age

                    # Verificar si es coherente (tolerancia de 1 año)
                    if abs(age_diff - years_passed) > 1.5:
                        self.inconsistencies.append(
                            TemporalInconsistency(
                                inconsistency_type=InconsistencyType.CHARACTER_AGE_MISMATCH,
                                severity=InconsistencySeverity.HIGH,
                                description=(
                                    f"Inconsistencia de edad del personaje {entity_id}: "
                                    f"Pasa de {prev_age} años (cap. {prev_chapter}) a "
                                    f"{curr_age} años (cap. {curr_chapter}), pero según "
                                    f"las fechas solo han pasado {years_passed:.1f} años."
                                ),
                                chapter=curr_chapter,
                                position=0,
                                expected=f"{prev_age + int(years_passed)} años",
                                found=f"{curr_age} años",
                                suggestion=(
                                    f"Revisar la edad del personaje. Si han pasado "
                                    f"{years_passed:.0f} años, debería tener "
                                    f"aproximadamente {prev_age + int(years_passed)} años."
                                ),
                                confidence=0.9,
                            )
                        )
                elif curr_age < prev_age and curr_chapter > prev_chapter:
                    # Edad disminuye sin fechas conocidas
                    self.inconsistencies.append(
                        TemporalInconsistency(
                            inconsistency_type=InconsistencyType.AGE_CONTRADICTION,
                            severity=InconsistencySeverity.CRITICAL,
                            description=(
                                f"El personaje {entity_id} tiene {prev_age} años en "
                                f"el capítulo {prev_chapter}, pero {curr_age} años en "
                                f"el capítulo {curr_chapter} (posterior)."
                            ),
                            chapter=curr_chapter,
                            position=0,
                            expected=f">= {prev_age} años",
                            found=f"{curr_age} años",
                            suggestion=(
                                "Un personaje no puede rejuvenecer a menos que sea "
                                "un flashback. Revisar las edades mencionadas."
                            ),
                            confidence=0.95,
                        )
                    )

    def _check_suspicious_jumps(self, timeline: Timeline) -> None:
        """Detecta saltos temporales sospechosos no declarados."""
        discourse_order = timeline.get_discourse_order()
        dated_events = [
            e
            for e in discourse_order
            if e.story_date and e.narrative_order == NarrativeOrder.CHRONOLOGICAL
        ]

        if len(dated_events) < 2:
            return

        for i in range(1, len(dated_events)):
            current = dated_events[i]
            prev = dated_events[i - 1]

            if current.story_date and prev.story_date:
                delta = current.story_date - prev.story_date

                # Salto hacia adelante muy grande (más de 5 años)
                if delta.days > 365 * 5:
                    self.inconsistencies.append(
                        TemporalInconsistency(
                            inconsistency_type=InconsistencyType.TIME_JUMP_SUSPICIOUS,
                            severity=InconsistencySeverity.LOW,
                            description=(
                                f"Salto temporal de {delta.days // 365} años entre "
                                f"capítulo {prev.chapter} y capítulo {current.chapter} "
                                f"sin transición explícita."
                            ),
                            chapter=current.chapter,
                            position=current.discourse_position,
                            events_involved=[prev.id, current.id],
                            suggestion=(
                                "Considerar añadir un marcador temporal explícito "
                                "para el salto en el tiempo."
                            ),
                            confidence=0.6,
                        )
                    )

    def _check_anachronisms(
        self,
        timeline: Timeline,
        markers: list[TemporalMarker],
    ) -> None:
        """Detecta posibles anacronismos (referencias a eventos fuera de época)."""
        # Obtener rango temporal de la historia
        time_span = timeline.get_time_span()
        if not time_span:
            return

        story_start, story_end = time_span

        # Verificar referencias a épocas
        epoch_markers = [m for m in markers if m.marker_type == MarkerType.SEASON_EPOCH]

        for marker in epoch_markers:
            text_lower = marker.text.lower()

            # Detectar referencias a períodos históricos específicos
            anachronism_checks = [
                ("la guerra civil", 1936, 1939),
                ("la posguerra", 1939, 1959),
                ("el franquismo", 1939, 1975),
                ("la transición", 1975, 1982),
                ("la república", 1931, 1939),
            ]

            for period_name, period_start, period_end in anachronism_checks:
                if period_name in text_lower:
                    # Verificar si la historia ocurre en ese período
                    if story_end.year < period_start or story_start.year > period_end:
                        self.inconsistencies.append(
                            TemporalInconsistency(
                                inconsistency_type=InconsistencyType.ANACHRONISM,
                                severity=InconsistencySeverity.MEDIUM,
                                description=(
                                    f"Referencia a '{period_name}' ({period_start}-{period_end}) "
                                    f"cuando la historia ocurre entre {story_start.year} "
                                    f"y {story_end.year}."
                                ),
                                chapter=marker.chapter or 0,
                                position=marker.start_char,
                                markers_involved=[marker],
                                suggestion=(
                                    "Verificar si la referencia temporal es correcta "
                                    "para el período de la historia."
                                ),
                                confidence=0.75,
                            )
                        )

    def get_inconsistencies_by_severity(
        self,
        severity: InconsistencySeverity,
    ) -> list[TemporalInconsistency]:
        """Filtra inconsistencias por severidad."""
        return [i for i in self.inconsistencies if i.severity == severity]

    def get_inconsistencies_by_chapter(
        self,
        chapter: int,
    ) -> list[TemporalInconsistency]:
        """Filtra inconsistencias por capítulo."""
        return [i for i in self.inconsistencies if i.chapter == chapter]

    def export_report(self) -> str:
        """Genera un informe de inconsistencias en formato Markdown."""
        if not self.inconsistencies:
            return "# Informe de Consistencia Temporal\n\nNo se detectaron inconsistencias."

        lines = [
            "# Informe de Consistencia Temporal",
            "",
            f"**Total de inconsistencias:** {len(self.inconsistencies)}",
            "",
        ]

        # Agrupar por severidad
        by_severity: dict[InconsistencySeverity, list[TemporalInconsistency]] = {}
        for inc in self.inconsistencies:
            if inc.severity not in by_severity:
                by_severity[inc.severity] = []
            by_severity[inc.severity].append(inc)

        severity_order = [
            InconsistencySeverity.CRITICAL,
            InconsistencySeverity.HIGH,
            InconsistencySeverity.MEDIUM,
            InconsistencySeverity.LOW,
        ]

        severity_labels = {
            InconsistencySeverity.CRITICAL: "🔴 Crítico",
            InconsistencySeverity.HIGH: "🟠 Alto",
            InconsistencySeverity.MEDIUM: "🟡 Medio",
            InconsistencySeverity.LOW: "🟢 Bajo",
        }

        for severity in severity_order:
            if severity not in by_severity:
                continue

            lines.append(f"## {severity_labels[severity]}")
            lines.append("")

            for inc in by_severity[severity]:
                lines.append(f"### Capítulo {inc.chapter}")
                lines.append(f"**Tipo:** {inc.inconsistency_type.value}")
                lines.append(f"**Descripción:** {inc.description}")
                if inc.expected and inc.found:
                    lines.append(f"- Esperado: {inc.expected}")
                    lines.append(f"- Encontrado: {inc.found}")
                if inc.suggestion:
                    lines.append(f"**Sugerencia:** {inc.suggestion}")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# Validador LLM para Inconsistencias Temporales
# =============================================================================


class LLMTemporalValidator:
    """
    Validador de inconsistencias temporales usando LLM.

    Analiza candidatos detectados por otros métodos para confirmar
    o descartar mediante comprensión semántica profunda.
    """

    def __init__(self, model: str = "llama3.2", timeout: int = 300):
        self.model = model
        self.timeout = timeout
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        """Lazy loading del cliente LLM."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        from ..llm.client import get_llm_client

                        self._client = get_llm_client()
                    except Exception as e:
                        logger.warning(f"No se pudo conectar LLM: {e}")
        return self._client

    @property
    def is_available(self) -> bool:
        """Verifica si el LLM está disponible."""
        return self.client is not None and self.client.is_available

    def validate_inconsistency(
        self,
        inconsistency: TemporalInconsistency,
        context: str,
        timeline_summary: str,
    ) -> tuple[float, str]:
        """
        Valida una inconsistencia detectada usando LLM.

        Args:
            inconsistency: Inconsistencia candidata
            context: Contexto textual alrededor de la inconsistencia
            timeline_summary: Resumen del timeline para contexto

        Returns:
            (score_ajustado, razonamiento)
        """
        if not self.is_available:
            return inconsistency.confidence, "LLM no disponible"

        from ..llm.sanitization import sanitize_for_prompt

        # Sanitizar texto del manuscrito antes de enviarlo al LLM (A-10)
        safe_context = sanitize_for_prompt(context[:1500], max_length=1500)
        safe_timeline = sanitize_for_prompt(timeline_summary[:500], max_length=500)

        prompt = f"""Analiza esta posible inconsistencia temporal en una narrativa en español.

INCONSISTENCIA DETECTADA:
- Tipo: {inconsistency.inconsistency_type.value}
- Descripción: {inconsistency.description}
- Esperado: {inconsistency.expected or "N/A"}
- Encontrado: {inconsistency.found or "N/A"}

CONTEXTO NARRATIVO:
{safe_context}

RESUMEN DEL TIMELINE:
{safe_timeline}

¿Es esto realmente una inconsistencia temporal o podría haber una explicación narrativa válida?

Responde en formato:
VEREDICTO: [CONFIRMADO/PROBABLE/DUDOSO/DESCARTADO]
RAZONAMIENTO: [tu análisis]
CONFIANZA_AJUSTADA: [0.0-1.0]"""

        try:
            response = self.client.complete(
                prompt=prompt,
                system="Eres un experto editor de narrativa. Analiza inconsistencias temporales con precisión, considerando técnicas narrativas como flashbacks, prolepsis, narradores no fiables, etc.",
                max_tokens=500,
                temperature=0.1,
            )

            if not response:
                return inconsistency.confidence, "sin respuesta LLM"

            return self._parse_validation_response(response, inconsistency.confidence)

        except Exception as e:
            logger.debug(f"Error en validación LLM: {e}")
            return inconsistency.confidence, "error LLM"

    def _parse_validation_response(
        self,
        response: str,
        original_confidence: float,
    ) -> tuple[float, str]:
        """Parsea la respuesta del LLM."""
        import re

        # Buscar veredicto
        verdict_match = re.search(
            r"VEREDICTO:\s*(CONFIRMADO|PROBABLE|DUDOSO|DESCARTADO)", response, re.IGNORECASE
        )
        verdict = verdict_match.group(1).upper() if verdict_match else "PROBABLE"

        # Buscar razonamiento
        reasoning_match = re.search(
            r"RAZONAMIENTO:\s*(.+?)(?=CONFIANZA|$)", response, re.IGNORECASE | re.DOTALL
        )
        reasoning = (
            reasoning_match.group(1).strip()[:200] if reasoning_match else "sin razonamiento"
        )

        # Buscar confianza ajustada
        confidence_match = re.search(r"CONFIANZA_AJUSTADA:\s*([\d.]+)", response, re.IGNORECASE)

        # Ajustar según veredicto
        verdict_multipliers = {
            "CONFIRMADO": 1.2,
            "PROBABLE": 1.0,
            "DUDOSO": 0.7,
            "DESCARTADO": 0.3,
        }

        if confidence_match:
            new_confidence = float(confidence_match.group(1))
        else:
            multiplier = verdict_multipliers.get(verdict, 1.0)
            new_confidence = original_confidence * multiplier

        new_confidence = max(0.0, min(1.0, new_confidence))

        return new_confidence, f"{verdict}: {reasoning}"

    # =========================================================================
    # S3-01: Narrative-of-Thought Analysis
    # =========================================================================

    def analyze_with_not(
        self,
        text: str,
        entities: list[str],
        markers: list[str],
    ) -> list[TemporalInconsistency]:
        """
        Analiza texto usando Narrative-of-Thought (NoT) prompting.

        El método NoT convierte eventos narrativos a una estructura temporal
        ordenada, genera una narrativa cronológica y detecta contradicciones.

        Args:
            text: Texto narrativo a analizar (max ~2000 chars)
            entities: Lista de nombres de entidades
            markers: Lista de marcadores temporales

        Returns:
            Lista de inconsistencias detectadas por NoT
        """
        if not self.is_available:
            return []

        try:
            from ..llm.prompts import (
                NARRATIVE_OF_THOUGHT_EXAMPLES,
                NARRATIVE_OF_THOUGHT_SYSTEM,
                NARRATIVE_OF_THOUGHT_TEMPLATE,
                build_prompt,
            )

            prompt = build_prompt(
                NARRATIVE_OF_THOUGHT_TEMPLATE,
                examples=NARRATIVE_OF_THOUGHT_EXAMPLES,
                text=text[:2000],
                entities=", ".join(entities[:10]),
                markers=", ".join(markers[:15]),
            )

            response = self.client.complete(
                prompt=prompt,
                system=NARRATIVE_OF_THOUGHT_SYSTEM,
                max_tokens=1000,
                temperature=0.2,
            )

            if not response:
                return []

            return self._parse_not_response(response)

        except Exception as e:
            logger.debug(f"Error en análisis NoT: {e}")
            return []

    def _parse_not_response(self, response: str) -> list[TemporalInconsistency]:
        """Parsea la respuesta del análisis NoT."""
        import json
        import re

        inconsistencies = []

        # Intentar parsear JSON de la respuesta
        try:
            # Buscar JSON en la respuesta
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            raw_issues = data.get("inconsistencies", [])

            type_mapping = {
                "impossible_sequence": InconsistencyType.IMPOSSIBLE_SEQUENCE,
                "age_contradiction": InconsistencyType.AGE_CONTRADICTION,
                "anachronism": InconsistencyType.ANACHRONISM,
                "marker_conflict": InconsistencyType.MARKER_CONFLICT,
                "time_jump_suspicious": InconsistencyType.TIME_JUMP_SUSPICIOUS,
            }

            for issue in raw_issues:
                inc_type_str = issue.get("type", "marker_conflict")
                inc_type = type_mapping.get(inc_type_str, InconsistencyType.MARKER_CONFLICT)
                confidence = min(1.0, max(0.0, float(issue.get("confidence", 0.7))))

                inconsistencies.append(TemporalInconsistency(
                    inconsistency_type=inc_type,
                    severity=InconsistencySeverity.MEDIUM if confidence < 0.8 else InconsistencySeverity.HIGH,
                    description=issue.get("description", "Inconsistencia detectada por NoT"),
                    chapter=0,
                    position=0,
                    confidence=confidence,
                    methods_agreed=["not_llm"],
                    reasoning={"not": data.get("reasoning", "")},
                ))

        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"No se pudo parsear respuesta NoT: {e}")

        return inconsistencies

    # =========================================================================
    # S3-02: Timeline Self-Reflection
    # =========================================================================

    def self_reflect_timeline(
        self,
        timeline_summary: str,
        markers_summary: str,
        character_ages: str,
    ) -> list[TemporalInconsistency]:
        """
        Auto-reflexión sobre un timeline construido.

        Revisa un timeline ya construido para detectar problemas que
        los métodos automáticos pudieron haber pasado por alto.

        Args:
            timeline_summary: Resumen del timeline construido
            markers_summary: Resumen de marcadores temporales
            character_ages: Información de edades de personajes

        Returns:
            Lista de inconsistencias adicionales detectadas
        """
        if not self.is_available:
            return []

        try:
            from ..llm.prompts import (
                TIMELINE_SELF_REFLECTION_SYSTEM,
                TIMELINE_SELF_REFLECTION_TEMPLATE,
                build_prompt,
            )

            prompt = build_prompt(
                TIMELINE_SELF_REFLECTION_TEMPLATE,
                timeline_summary=timeline_summary[:1500],
                markers_summary=markers_summary[:500],
                character_ages=character_ages[:500],
            )

            response = self.client.complete(
                prompt=prompt,
                system=TIMELINE_SELF_REFLECTION_SYSTEM,
                max_tokens=800,
                temperature=0.1,
            )

            if not response:
                return []

            return self._parse_self_reflection_response(response)

        except Exception as e:
            logger.debug(f"Error en self-reflection: {e}")
            return []

    def _parse_self_reflection_response(self, response: str) -> list[TemporalInconsistency]:
        """Parsea la respuesta de self-reflection."""
        import json
        import re

        inconsistencies = []

        try:
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            issues = data.get("issues", [])

            type_mapping = {
                "age_inconsistency": InconsistencyType.CHARACTER_AGE_MISMATCH,
                "impossible_travel": InconsistencyType.IMPOSSIBLE_SEQUENCE,
                "anachronism": InconsistencyType.ANACHRONISM,
                "wrong_order": InconsistencyType.IMPOSSIBLE_SEQUENCE,
                "missing_flashback": InconsistencyType.TIME_JUMP_SUSPICIOUS,
            }

            for issue in issues:
                issue_type = issue.get("type", "wrong_order")
                inc_type = type_mapping.get(issue_type, InconsistencyType.MARKER_CONFLICT)
                confidence = min(1.0, max(0.0, float(issue.get("confidence", 0.6))))

                inconsistencies.append(TemporalInconsistency(
                    inconsistency_type=inc_type,
                    severity=InconsistencySeverity.MEDIUM,
                    description=issue.get("description", "Problema detectado en self-reflection"),
                    chapter=0,
                    position=0,
                    suggestion=issue.get("suggestion"),
                    confidence=confidence,
                    methods_agreed=["self_reflection"],
                    reasoning={"self_reflection": data.get("reasoning", "")},
                ))

        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"No se pudo parsear self-reflection: {e}")

        return inconsistencies


# =============================================================================
# Sistema de Votación y Funciones de Conveniencia
# =============================================================================


@dataclass
class TemporalCheckResult:
    """
    Resultado de la verificación temporal con votación.

    Attributes:
        inconsistencies: Inconsistencias detectadas y validadas
        method_contributions: Cuántas inconsistencias detectó cada método
        processing_time_ms: Tiempo de procesamiento
        consensus_stats: Estadísticas de consenso entre métodos
    """

    inconsistencies: list[TemporalInconsistency] = field(default_factory=list)
    method_contributions: dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    consensus_stats: dict[str, float] = field(default_factory=dict)

    @property
    def total_inconsistencies(self) -> int:
        return len(self.inconsistencies)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.inconsistencies if i.severity == InconsistencySeverity.CRITICAL)

    @property
    def high_confidence_count(self) -> int:
        return sum(1 for i in self.inconsistencies if i.confidence >= 0.8)


class VotingTemporalChecker:
    """
    Verificador de consistencia temporal con votación multi-método.

    Combina múltiples técnicas de detección y usa votación ponderada
    para determinar las inconsistencias finales con mayor precisión.

    Arquitectura optimizada:
    1. DIRECT + CONTEXTUAL + HEURISTICS se ejecutan rápidamente
    2. LLM solo valida candidatos (reduce llamadas costosas)
    3. Votación pondera y consolida resultados

    Example:
        >>> checker = VotingTemporalChecker()
        >>> result = checker.check(timeline, markers, character_ages)
        >>> for inc in result.inconsistencies:
        ...     print(f"{inc.inconsistency_type.value}: {inc.description}")
    """

    def __init__(
        self,
        config: TemporalDetectionConfig | None = None,
    ):
        """
        Inicializa el verificador con votación.

        Args:
            config: Configuración del sistema de votación
        """
        self.config = config or TemporalDetectionConfig()

        # Inicializar el checker base (métodos directos)
        self._base_checker = TemporalConsistencyChecker(self.config)

        logger.info(
            f"VotingTemporalChecker inicializado con métodos: "
            f"{[m.value for m in self.config.enabled_methods]}"
        )

    def check(
        self,
        timeline: Timeline,
        markers: list[TemporalMarker],
        character_ages: dict[int, list[tuple[int, int]]] | None = None,
        text: str | None = None,
    ) -> TemporalCheckResult:
        """
        Verifica consistencia temporal con votación multi-método.

        Args:
            timeline: Timeline construido
            markers: Lista de marcadores temporales
            character_ages: Dict de entity_id -> [(chapter, age), ...]
            text: Texto original (para validación LLM)

        Returns:
            TemporalCheckResult con inconsistencias y estadísticas
        """
        import time

        start_time = time.time()

        result = TemporalCheckResult()

        # Fase 1: Detección directa (rápida)
        # Estos métodos se ejecutan secuencialmente pero son muy rápidos
        direct_inconsistencies = self._base_checker.check(timeline, markers, character_ages)

        # Marcar método de detección
        for inc in direct_inconsistencies:
            inc.methods_agreed = [TemporalDetectionMethod.DIRECT.value]
            inc.reasoning[TemporalDetectionMethod.DIRECT.value] = "Detección directa"

        result.method_contributions["direct"] = len(direct_inconsistencies)

        # Fase 2: Validación contextual (añade evidencia)
        if TemporalDetectionMethod.CONTEXTUAL in self.config.enabled_methods:
            for inc in direct_inconsistencies:
                contextual_score, contextual_reason = self._validate_contextually(
                    inc, timeline, markers
                )
                if contextual_score > 0.5:
                    inc.methods_agreed.append(TemporalDetectionMethod.CONTEXTUAL.value)
                    inc.reasoning[TemporalDetectionMethod.CONTEXTUAL.value] = contextual_reason
                    # Ajustar confianza
                    inc.confidence = min(1.0, inc.confidence * 1.1)

        # Fase 3: Heurísticas narrativas (añade evidencia)
        if TemporalDetectionMethod.HEURISTICS in self.config.enabled_methods:
            for inc in direct_inconsistencies:
                heur_score, heur_reason = self._apply_heuristics(inc, timeline)
                if heur_score > 0.5:
                    inc.methods_agreed.append(TemporalDetectionMethod.HEURISTICS.value)
                    inc.reasoning[TemporalDetectionMethod.HEURISTICS.value] = heur_reason
                    inc.confidence = min(1.0, inc.confidence * 1.05)

        # Fase 4: Validación LLM (solo para candidatos de alta prioridad)
        if (
            TemporalDetectionMethod.LLM in self.config.enabled_methods
            and self._base_checker._llm_validator
            and self._base_checker._llm_validator.is_available
            and text
        ):
            # Solo validar inconsistencias de severidad MEDIUM o superior
            high_priority = [
                inc
                for inc in direct_inconsistencies
                if inc.severity
                in (
                    InconsistencySeverity.CRITICAL,
                    InconsistencySeverity.HIGH,
                    InconsistencySeverity.MEDIUM,
                )
            ]

            timeline_summary = self._get_timeline_summary(timeline)

            for inc in high_priority:
                # Ceder turno al chat interactivo si hay uno esperando
                try:
                    from narrative_assistant.llm.client import get_llm_scheduler
                    get_llm_scheduler().yield_to_chat()
                except Exception:
                    pass

                context = self._get_context_for_inconsistency(inc, text)
                llm_score, llm_reason = self._base_checker._llm_validator.validate_inconsistency(
                    inc, context, timeline_summary
                )

                # Solo añadir si el LLM confirma
                if llm_score >= 0.5:
                    inc.methods_agreed.append(TemporalDetectionMethod.LLM.value)
                    inc.reasoning[TemporalDetectionMethod.LLM.value] = llm_reason
                    # Ajustar confianza según validación LLM
                    inc.confidence = llm_score

            result.method_contributions["llm"] = len(high_priority)

            # S3-01: Narrative-of-Thought - análisis complementario
            if text and len(text) >= 200:
                entity_names = []
                for event in timeline.events[:20]:
                    entity_names.extend(
                        str(eid) for eid in getattr(event, "entity_ids", [])
                    )
                marker_texts = [m.text for m in markers[:15]]

                not_issues = self._base_checker._llm_validator.analyze_with_not(
                    text[:2000],
                    entities=list(set(entity_names))[:10],
                    markers=marker_texts,
                )

                # Añadir inconsistencias NoT que no dupliquen las existentes
                existing_descs = {inc.description.lower()[:50] for inc in direct_inconsistencies}
                for not_inc in not_issues:
                    if not_inc.description.lower()[:50] not in existing_descs:
                        direct_inconsistencies.append(not_inc)
                        existing_descs.add(not_inc.description.lower()[:50])

                result.method_contributions["not"] = len(not_issues)

            # S3-02: Timeline Self-Reflection
            if timeline.events:
                timeline_summary = self._get_timeline_summary(timeline)
                markers_summary = ", ".join(m.text for m in markers[:10])
                ages_summary = ""
                if character_ages:
                    ages_parts = []
                    for eid, age_list in list(character_ages.items())[:5]:
                        for ch, age in age_list[:3]:
                            ages_parts.append(f"entity_{eid}: {age} años (cap. {ch})")
                    ages_summary = "; ".join(ages_parts)

                reflection_issues = self._base_checker._llm_validator.self_reflect_timeline(
                    timeline_summary=timeline_summary,
                    markers_summary=markers_summary,
                    character_ages=ages_summary or "No disponible",
                )

                for ref_inc in reflection_issues:
                    if ref_inc.description.lower()[:50] not in existing_descs:
                        direct_inconsistencies.append(ref_inc)
                        existing_descs.add(ref_inc.description.lower()[:50])

                result.method_contributions["self_reflection"] = len(reflection_issues)

        # Fase 5: Aplicar bonus por consenso
        for inc in direct_inconsistencies:
            num_methods = len(inc.methods_agreed)
            if num_methods >= 2:
                inc.confidence = min(1.0, inc.confidence * TEMPORAL_AGREEMENT_BONUS)
            if num_methods >= 3:
                inc.confidence = min(1.0, inc.confidence * 1.05)

        # Fase 6: Filtrar por confianza mínima
        result.inconsistencies = [
            inc for inc in direct_inconsistencies if inc.confidence >= self.config.min_confidence
        ]

        # Ordenar por severidad y confianza
        result.inconsistencies.sort(
            key=lambda i: (list(InconsistencySeverity).index(i.severity), -i.confidence)
        )

        # Calcular estadísticas
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.consensus_stats = self._calculate_consensus_stats(result.inconsistencies)

        logger.info(
            f"Verificación completada: {result.total_inconsistencies} inconsistencias, "
            f"{result.critical_count} críticas, {result.processing_time_ms:.1f}ms"
        )

        return result

    def _validate_contextually(
        self,
        inc: TemporalInconsistency,
        timeline: Timeline,
        markers: list[TemporalMarker],
    ) -> tuple[float, str]:
        """
        Valida contextualmente una inconsistencia.

        Busca patrones de transición y contexto que puedan
        confirmar o descartar la inconsistencia.
        """
        score = 0.5
        reasons = []

        # Verificar si hay marcadores de flashback/prolepsis cercanos
        nearby_markers = [m for m in markers if abs(m.start_char - inc.position) < 500]

        # Buscar indicadores de salto temporal intencional
        transition_words = [
            "más tarde",
            "años después",
            "tiempo atrás",
            "en aquel entonces",
            "cuando era",
            "de joven",
        ]

        for marker in nearby_markers:
            marker_lower = marker.text.lower()
            for word in transition_words:
                if word in marker_lower:
                    score -= 0.2  # Puede ser intencional
                    reasons.append(f"Transición detectada: '{word}'")

        # Verificar consistencia con eventos adyacentes
        if inc.events_involved:
            for event_id in inc.events_involved:
                event = next((e for e in timeline.events if e.id == event_id), None)
                if event and event.narrative_order != NarrativeOrder.CHRONOLOGICAL:
                    score -= 0.3  # Es un flashback/prolepsis declarado
                    reasons.append("Evento marcado como no-cronológico")

        if not reasons:
            reasons.append("Sin transiciones que justifiquen")
            score += 0.1

        return max(0.0, min(1.0, score)), "; ".join(reasons)

    def _apply_heuristics(
        self,
        inc: TemporalInconsistency,
        timeline: Timeline,
    ) -> tuple[float, str]:
        """
        Aplica heurísticas narrativas para validar inconsistencia.

        Considera patrones comunes en narrativa que pueden
        explicar aparentes inconsistencias.
        """
        score = 0.5
        reasons = []

        # Heurística 1: Inconsistencias de edad son más creíbles
        if inc.inconsistency_type == InconsistencyType.AGE_CONTRADICTION:
            score += 0.2
            reasons.append("Edad es dato objetivo")

        # Heurística 2: Saltos temporales en cambios de capítulo son normales
        elif inc.inconsistency_type == InconsistencyType.TIME_JUMP_SUSPICIOUS:
            # Verificar si es en límite de capítulo
            chapter_events = [e for e in timeline.events if e.chapter == inc.chapter]
            if chapter_events and chapter_events[0].discourse_position <= inc.position:
                score -= 0.2  # Inicio de capítulo, normal
                reasons.append("Salto en inicio de capítulo")
            else:
                reasons.append("Salto dentro de capítulo")

        # Heurística 3: Anacronismos pueden ser intencionales
        elif inc.inconsistency_type == InconsistencyType.ANACHRONISM:
            # Algunos géneros usan anacronismos a propósito
            score = 0.4  # Menos confianza
            reasons.append("Anacronismos pueden ser estilísticos")

        # Heurística 4: Secuencias imposibles con fechas son graves
        elif inc.inconsistency_type == InconsistencyType.IMPOSSIBLE_SEQUENCE:
            score += 0.15
            reasons.append("Fechas explícitas contradictorias")

        if not reasons:
            reasons.append("Sin heurísticas aplicables")

        return max(0.0, min(1.0, score)), "; ".join(reasons)

    def _get_timeline_summary(self, timeline: Timeline) -> str:
        """Genera un resumen del timeline para contexto LLM."""
        events = timeline.get_chronological_order()[:10]  # Primeros 10 eventos
        lines = []
        for e in events:
            date_str = str(e.story_date) if e.story_date else "fecha desconocida"
            lines.append(f"- Cap {e.chapter}: {e.description[:50]}... ({date_str})")
        return "\n".join(lines)

    def _get_context_for_inconsistency(
        self,
        inc: TemporalInconsistency,
        text: str,
    ) -> str:
        """Extrae contexto textual alrededor de una inconsistencia."""
        pos = inc.position
        start = max(0, pos - 300)
        end = min(len(text), pos + 300)
        return text[start:end]

    def _calculate_consensus_stats(
        self,
        inconsistencies: list[TemporalInconsistency],
    ) -> dict[str, float]:
        """Calcula estadísticas de consenso."""
        if not inconsistencies:
            return {}

        total = len(inconsistencies)
        single_method = sum(1 for i in inconsistencies if len(i.methods_agreed) == 1)
        multi_method = sum(1 for i in inconsistencies if len(i.methods_agreed) >= 2)
        high_consensus = sum(1 for i in inconsistencies if len(i.methods_agreed) >= 3)

        return {
            "single_method_pct": single_method / total * 100,
            "multi_method_pct": multi_method / total * 100,
            "high_consensus_pct": high_consensus / total * 100 if total > 0 else 0,
            "avg_confidence": sum(i.confidence for i in inconsistencies) / total,
        }


# =============================================================================
# Singleton y Funciones de Conveniencia
# =============================================================================

_voting_checker_lock = threading.Lock()
_voting_checker: VotingTemporalChecker | None = None


def get_voting_temporal_checker(
    config: TemporalDetectionConfig | None = None,
) -> VotingTemporalChecker:
    """
    Obtiene el singleton del verificador temporal con votación.

    Args:
        config: Configuración opcional

    Returns:
        Instancia del VotingTemporalChecker
    """
    global _voting_checker

    if _voting_checker is None:
        with _voting_checker_lock:
            if _voting_checker is None:
                _voting_checker = VotingTemporalChecker(config)

    return _voting_checker


def reset_voting_temporal_checker() -> None:
    """Resetea el singleton (útil para tests)."""
    global _voting_checker
    with _voting_checker_lock:
        _voting_checker = None


def check_temporal_consistency_voting(
    timeline: Timeline,
    markers: list[TemporalMarker],
    character_ages: dict[int, list[tuple[int, int]]] | None = None,
    text: str | None = None,
    config: TemporalDetectionConfig | None = None,
) -> TemporalCheckResult:
    """
    Función de conveniencia para verificar consistencia temporal con votación.

    Esta es la función recomendada para obtener resultados de alta calidad.

    Args:
        timeline: Timeline construido
        markers: Lista de marcadores temporales
        character_ages: Dict de entity_id -> [(chapter, age), ...]
        text: Texto original (para validación LLM)
        config: Configuración opcional

    Returns:
        TemporalCheckResult con inconsistencias y estadísticas

    Example:
        >>> result = check_temporal_consistency_voting(timeline, markers, text=full_text)
        >>> for inc in result.inconsistencies:
        ...     print(f"{inc.inconsistency_type.value}: {inc.description}")
        ...     print(f"  Confianza: {inc.confidence:.2f}")
        ...     print(f"  Métodos: {', '.join(inc.methods_agreed)}")
    """
    checker = VotingTemporalChecker(config)
    return checker.check(timeline, markers, character_ages, text)
