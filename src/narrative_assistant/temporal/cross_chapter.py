"""
Cross-Chapter Temporal Linking (Level C).

Vincula instancias temporales del mismo personaje entre capítulos,
infiere edades faltantes, y detecta contradicciones cross-chapter.

Algoritmo en 5 fases:
1. Collect — Agrupa instancias por entidad
2. Sort — Ordena cronológicamente (story-time)
3. Link + Detect — Conecta instancias consecutivas, detecta regresiones
4. Infer — Infiere birth_year y edades desde offsets
5. Discourse — Compara orden story vs discourse para detectar errores
"""

import logging
import re
import statistics
from dataclasses import dataclass, field

from narrative_assistant.core.result import Result
from narrative_assistant.temporal.inconsistencies import (
    InconsistencySeverity,
    InconsistencyType,
    TemporalInconsistency,
)
from narrative_assistant.temporal.markers import MarkerType, TemporalMarker
from narrative_assistant.temporal.timeline import NarrativeOrder, Timeline

logger = logging.getLogger(__name__)

# ============================================================================
# Constantes
# ============================================================================

# Rangos de edad por fase con solapamiento (C-4: fuzzy boundaries para español)
PHASE_AGE_RANGES: dict[str, tuple[int, int]] = {
    "child": (0, 14),
    "teen": (11, 21),
    "young": (17, 40),
    "adult": (30, 70),
    "elder": (55, 130),
}

PHASE_AGE_TOLERANCE = 3  # Tolerancia extra en límites

PHASE_RANK: dict[str, int] = {
    "child": 0,
    "teen": 1,
    "young": 2,
    "adult": 3,
    "elder": 4,
    "future_self": 5,
    "past_self": -1,
}

# Tolerancia para comparación de birth_year
BIRTH_YEAR_MAX_SPREAD = 3


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class EntityTemporalInstance:
    """Un punto de anclaje temporal para una entidad."""

    entity_id: int
    chapter: int
    instance_type: str  # "age", "phase", "year", "offset"
    value: int | str  # 40, "child", 1985, -5
    temporal_instance_id: str
    confidence: float
    is_analepsis: bool = False
    inferred: bool = False
    inference_source: str = ""


@dataclass
class TemporalLink:
    """Enlace entre dos instancias temporales de la misma entidad."""

    from_id: str
    to_id: str
    relationship: str  # age_progression, phase_age_overlap, co_occurrence, etc.
    inferred_gap_years: float | None  # None para phase-only
    confidence: float


@dataclass
class EntityTimeline:
    """Timeline biográfico de una entidad."""

    entity_id: int
    canonical_name: str
    instances: list[EntityTemporalInstance] = field(default_factory=list)
    inferred_birth_year: int | None = None
    birth_year_confidence: float = 0.0
    links: list[TemporalLink] = field(default_factory=list)


@dataclass
class CrossChapterResult:
    """Resultado del análisis cross-chapter."""

    entity_timelines: dict[int, EntityTimeline] = field(default_factory=dict)
    inferred_markers: list[TemporalMarker] = field(default_factory=list)
    new_inconsistencies: list[TemporalInconsistency] = field(default_factory=list)


# ============================================================================
# Utilidades
# ============================================================================


def _parse_instance_id(instance_id: str) -> tuple[str, int | str] | None:
    """Parsea 'entity_id@type:value' → (type, value)."""
    match = re.match(r"\d+@(\w+):(.+)$", instance_id)
    if not match:
        return None
    itype = match.group(1)
    raw_value = match.group(2)

    if itype == "age":
        try:
            return ("age", int(raw_value))
        except ValueError:
            return None
    elif itype == "phase":
        return ("phase", raw_value)
    elif itype == "year":
        try:
            return ("year", int(raw_value))
        except ValueError:
            return None
    elif itype == "offset_years":
        try:
            return ("offset", int(raw_value))
        except ValueError:
            return None
    return None


def _get_age_from_instance(inst: EntityTemporalInstance) -> int | None:
    """Extrae edad numérica de una instancia."""
    if inst.instance_type == "age" and isinstance(inst.value, int):
        return inst.value
    return None


def _get_phase_rank(inst: EntityTemporalInstance) -> int:
    """Retorna rank de fase para ordenación."""
    if inst.instance_type == "phase" and isinstance(inst.value, str):
        return PHASE_RANK.get(inst.value, 3)
    return 3  # default = adult


def _is_phase_compatible_with_age(phase: str, age: int) -> bool:
    """Verifica si una fase es compatible con una edad (con tolerancia)."""
    age_range = PHASE_AGE_RANGES.get(phase)
    if not age_range:
        return True  # Fase desconocida → no restringir
    low = age_range[0] - PHASE_AGE_TOLERANCE
    high = age_range[1] + PHASE_AGE_TOLERANCE
    return low <= age <= high


def _build_analepsis_chapters(timeline: Timeline) -> set[int]:
    """Construye set de capítulos marcados como analepsis."""
    chapters: set[int] = set()
    for event in timeline.events:
        if event.narrative_order == NarrativeOrder.ANALEPSIS:
            chapters.add(event.chapter)
    return chapters


def _sort_key(inst: EntityTemporalInstance) -> tuple:
    """Clave de ordenación: year → age → phase_rank → chapter."""
    year = inst.value if inst.instance_type == "year" else 9999
    age = inst.value if inst.instance_type == "age" and isinstance(inst.value, int) else -1
    phase_rank = _get_phase_rank(inst) if inst.instance_type == "phase" else 3
    return (year, age, phase_rank, inst.chapter)


# ============================================================================
# Fase 1: Collect
# ============================================================================


def _collect_instances(
    markers: list[TemporalMarker],
    analepsis_chapters: set[int],
) -> dict[int, list[EntityTemporalInstance]]:
    """Agrupa instancias temporales por entity_id."""
    by_entity: dict[int, list[EntityTemporalInstance]] = {}

    for marker in markers:
        if not marker.temporal_instance_id or marker.entity_id is None:
            continue

        parsed = _parse_instance_id(marker.temporal_instance_id)
        if not parsed:
            continue

        itype, value = parsed
        instance = EntityTemporalInstance(
            entity_id=marker.entity_id,
            chapter=marker.chapter or 0,
            instance_type=itype,
            value=value,
            temporal_instance_id=marker.temporal_instance_id,
            confidence=marker.confidence,
            is_analepsis=(marker.chapter or 0) in analepsis_chapters,
        )
        by_entity.setdefault(marker.entity_id, []).append(instance)

    return by_entity


# ============================================================================
# Fase 2: Sort (story-time order)
# ============================================================================


def _sort_instances(instances: list[EntityTemporalInstance]) -> list[EntityTemporalInstance]:
    """Ordena instancias en orden cronológico (story-time)."""
    return sorted(instances, key=_sort_key)


# ============================================================================
# Fase 3: Link + Detect
# ============================================================================


def _link_and_detect(
    instances: list[EntityTemporalInstance],
    entity_name: str,
) -> tuple[list[TemporalLink], list[TemporalInconsistency]]:
    """Conecta instancias consecutivas y detecta contradicciones."""
    links: list[TemporalLink] = []
    inconsistencies: list[TemporalInconsistency] = []

    # Deduplicar: no procesar el mismo instance_id más de una vez
    seen_ids: set[str] = set()
    unique: list[EntityTemporalInstance] = []
    for inst in instances:
        if inst.temporal_instance_id not in seen_ids:
            seen_ids.add(inst.temporal_instance_id)
            unique.append(inst)

    for i in range(len(unique) - 1):
        i1 = unique[i]
        i2 = unique[i + 1]

        age1 = _get_age_from_instance(i1)
        age2 = _get_age_from_instance(i2)

        # a) age → age
        if age1 is not None and age2 is not None:
            if age2 > age1:
                # Progresión normal
                links.append(TemporalLink(
                    from_id=i1.temporal_instance_id,
                    to_id=i2.temporal_instance_id,
                    relationship="age_progression",
                    inferred_gap_years=float(age2 - age1),
                    confidence=min(i1.confidence, i2.confidence),
                ))
            elif age2 == age1:
                # Co-ocurrencia (misma edad en distintos capítulos)
                links.append(TemporalLink(
                    from_id=i1.temporal_instance_id,
                    to_id=i2.temporal_instance_id,
                    relationship="co_occurrence",
                    inferred_gap_years=0.0,
                    confidence=min(i1.confidence, i2.confidence),
                ))
            else:
                # Regresión de edad
                if i2.is_analepsis:
                    # Flashback legítimo → no alertar
                    links.append(TemporalLink(
                        from_id=i1.temporal_instance_id,
                        to_id=i2.temporal_instance_id,
                        relationship="flashback_regression",
                        inferred_gap_years=float(age2 - age1),
                        confidence=min(i1.confidence, i2.confidence),
                    ))
                else:
                    inconsistencies.append(TemporalInconsistency(
                        inconsistency_type=InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION,
                        severity=InconsistencySeverity.CRITICAL,
                        description=(
                            f"{entity_name}: edad retrocede de {age1} (cap. {i1.chapter}) "
                            f"a {age2} (cap. {i2.chapter}) sin marcador de flashback"
                        ),
                        chapter=i2.chapter,
                        position=0,
                        expected=str(age1),
                        found=str(age2),
                        suggestion=(
                            f"Verificar si el capítulo {i2.chapter} es un flashback "
                            f"o si la edad {age2} es incorrecta"
                        ),
                        confidence=min(i1.confidence, i2.confidence),
                    ))
            continue

        # d/e) phase ↔ age
        phase_inst = i1 if i1.instance_type == "phase" else (i2 if i2.instance_type == "phase" else None)
        age_inst = i1 if age1 is not None else (i2 if age2 is not None else None)

        if phase_inst and age_inst:
            age_val = _get_age_from_instance(age_inst)
            phase_val = phase_inst.value
            if age_val is not None and isinstance(phase_val, str):
                if _is_phase_compatible_with_age(phase_val, age_val):
                    links.append(TemporalLink(
                        from_id=i1.temporal_instance_id,
                        to_id=i2.temporal_instance_id,
                        relationship="phase_age_overlap",
                        inferred_gap_years=None,
                        confidence=min(i1.confidence, i2.confidence) * 0.9,
                    ))
                else:
                    inconsistencies.append(TemporalInconsistency(
                        inconsistency_type=InconsistencyType.PHASE_AGE_INCOMPATIBLE,
                        severity=InconsistencySeverity.MEDIUM,
                        description=(
                            f"{entity_name}: fase '{phase_val}' (cap. {phase_inst.chapter}) "
                            f"incompatible con edad {age_val} (cap. {age_inst.chapter})"
                        ),
                        chapter=age_inst.chapter,
                        position=0,
                        expected=f"fase {phase_val}: {PHASE_AGE_RANGES.get(phase_val, '?')}",
                        found=str(age_val),
                        confidence=min(i1.confidence, i2.confidence),
                    ))
            continue

        # f) phase → phase
        if i1.instance_type == "phase" and i2.instance_type == "phase":
            rank1 = _get_phase_rank(i1)
            rank2 = _get_phase_rank(i2)
            if rank2 >= rank1:
                links.append(TemporalLink(
                    from_id=i1.temporal_instance_id,
                    to_id=i2.temporal_instance_id,
                    relationship="phase_progression",
                    inferred_gap_years=None,
                    confidence=min(i1.confidence, i2.confidence) * 0.8,
                ))
            elif not i2.is_analepsis:
                inconsistencies.append(TemporalInconsistency(
                    inconsistency_type=InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION,
                    severity=InconsistencySeverity.MEDIUM,
                    description=(
                        f"{entity_name}: fase retrocede de '{i1.value}' (cap. {i1.chapter}) "
                        f"a '{i2.value}' (cap. {i2.chapter}) sin flashback"
                    ),
                    chapter=i2.chapter,
                    position=0,
                    expected=str(i1.value),
                    found=str(i2.value),
                    confidence=min(i1.confidence, i2.confidence) * 0.7,
                ))

    return links, inconsistencies


# ============================================================================
# Fase 3b: Discourse-order regression check (C-3)
# ============================================================================


def _check_discourse_regressions(
    instances: list[EntityTemporalInstance],
    entity_name: str,
) -> list[TemporalInconsistency]:
    """
    Detecta regresiones temporales en orden de discurso (capítulo).

    Si la edad de un personaje DISMINUYE al avanzar los capítulos
    y el capítulo posterior NO es analepsis, es una inconsistencia.
    """
    inconsistencies: list[TemporalInconsistency] = []

    # Deduplicar por instance_id
    seen_ids: set[str] = set()
    unique: list[EntityTemporalInstance] = []
    for inst in instances:
        if inst.temporal_instance_id not in seen_ids:
            seen_ids.add(inst.temporal_instance_id)
            unique.append(inst)

    # Ordenar por capítulo (discourse order)
    discourse_order = sorted(unique, key=lambda inst: inst.chapter)

    # Comparar edades consecutivas en discourse order
    for i in range(len(discourse_order) - 1):
        i1 = discourse_order[i]
        i2 = discourse_order[i + 1]

        age1 = _get_age_from_instance(i1)
        age2 = _get_age_from_instance(i2)

        if age1 is not None and age2 is not None and age2 < age1:
            if i2.is_analepsis:
                # Flashback legítimo → no alertar
                continue
            inconsistencies.append(TemporalInconsistency(
                inconsistency_type=InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION,
                severity=InconsistencySeverity.CRITICAL,
                description=(
                    f"{entity_name}: edad retrocede de {age1} (cap. {i1.chapter}) "
                    f"a {age2} (cap. {i2.chapter}) sin marcador de flashback"
                ),
                chapter=i2.chapter,
                position=0,
                expected=str(age1),
                found=str(age2),
                suggestion=(
                    f"Verificar si el capítulo {i2.chapter} es un flashback "
                    f"o si la edad {age2} es incorrecta"
                ),
                confidence=min(i1.confidence, i2.confidence),
            ))

        # Phase regression in discourse order
        if (
            i1.instance_type == "phase"
            and i2.instance_type == "phase"
            and _get_phase_rank(i1) > _get_phase_rank(i2)
            and not i2.is_analepsis
        ):
            inconsistencies.append(TemporalInconsistency(
                inconsistency_type=InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION,
                severity=InconsistencySeverity.MEDIUM,
                description=(
                    f"{entity_name}: fase retrocede de '{i1.value}' (cap. {i1.chapter}) "
                    f"a '{i2.value}' (cap. {i2.chapter}) sin flashback"
                ),
                chapter=i2.chapter,
                position=0,
                expected=str(i1.value),
                found=str(i2.value),
                confidence=min(i1.confidence, i2.confidence) * 0.7,
            ))

    return inconsistencies


# ============================================================================
# Fase 4: Infer
# ============================================================================


def _infer_birth_year(
    instances: list[EntityTemporalInstance],
    entity_name: str,
) -> tuple[int | None, float, list[TemporalInconsistency]]:
    """Infiere año de nacimiento desde pares (year, age)."""
    birth_years: list[int] = []
    inconsistencies: list[TemporalInconsistency] = []

    # Recopilar pares year+age del mismo capítulo o cercanos
    year_instances = {inst.chapter: inst.value for inst in instances if inst.instance_type == "year"}
    age_instances = {inst.chapter: inst.value for inst in instances if inst.instance_type == "age"}

    for chapter, year in year_instances.items():
        if chapter in age_instances and isinstance(year, int) and isinstance(age_instances[chapter], int):
            birth_years.append(year - age_instances[chapter])

    if not birth_years:
        return None, 0.0, []

    birth_year = int(statistics.median(birth_years))
    spread = max(birth_years) - min(birth_years) if len(birth_years) > 1 else 0

    if spread > BIRTH_YEAR_MAX_SPREAD:
        inconsistencies.append(TemporalInconsistency(
            inconsistency_type=InconsistencyType.BIRTH_YEAR_CONTRADICTION,
            severity=InconsistencySeverity.HIGH,
            description=(
                f"{entity_name}: año de nacimiento inconsistente — "
                f"las combinaciones (año, edad) dan nacimientos entre "
                f"{min(birth_years)} y {max(birth_years)} (diferencia: {spread} años)"
            ),
            chapter=0,
            position=0,
            expected=f"nacimiento ~{birth_year}",
            found=f"rango {min(birth_years)}-{max(birth_years)}",
            confidence=0.85,
        ))

    confidence = 0.9 if spread <= 1 else (0.7 if spread <= 2 else 0.5)
    return birth_year, confidence, inconsistencies


def _infer_from_offsets(
    instances: list[EntityTemporalInstance],
    entity_id: int,
    entity_name: str,
) -> list[TemporalMarker]:
    """Infiere edades a partir de @offset_years + edad previa."""
    inferred: list[TemporalMarker] = []

    # Construir mapa: chapter → edad conocida
    age_by_chapter: dict[int, int] = {}
    for inst in instances:
        age = _get_age_from_instance(inst)
        if age is not None:
            age_by_chapter[inst.chapter] = age

    # Buscar instancias offset
    for inst in instances:
        if inst.instance_type != "offset" or not isinstance(inst.value, int):
            continue

        # Ya hay edad explícita en este capítulo → no inferir
        if inst.chapter in age_by_chapter:
            continue

        # Buscar edad precedente más cercana
        preceding_chapters = sorted(
            [ch for ch in age_by_chapter if ch < inst.chapter],
            reverse=True,
        )
        if not preceding_chapters:
            continue

        anchor_chapter = preceding_chapters[0]
        anchor_age = age_by_chapter[anchor_chapter]
        inferred_age = anchor_age + inst.value

        if inferred_age < 0 or inferred_age > 130:
            continue

        # Crear marcador inferido
        marker = TemporalMarker(
            text=f"[inferido: {entity_name} ~{inferred_age} años]",
            marker_type=MarkerType.CHARACTER_AGE,
            start_char=0,
            end_char=0,
            chapter=inst.chapter,
            entity_id=entity_id,
            age=inferred_age,
            confidence=inst.confidence * 0.7,
        )
        marker.temporal_instance_id = f"{entity_id}@age:{inferred_age}"
        inferred.append(marker)

        logger.debug(
            "Level C inferred %s@age:%d in ch%d (from %d in ch%d + offset %+d)",
            entity_name, inferred_age, inst.chapter,
            anchor_age, anchor_chapter, inst.value,
        )

    return inferred


# ============================================================================
# Función principal
# ============================================================================


def build_entity_timelines(
    markers: list[TemporalMarker],
    entities: list,  # list[Entity] — Any para evitar import circular
    timeline: Timeline,
) -> Result[CrossChapterResult]:
    """
    Construye timelines biográficos por entidad con linking cross-chapter.

    Args:
        markers: Todos los marcadores temporales (Level A + B)
        entities: Entidades del proyecto
        timeline: Timeline construido (para info de flashbacks)

    Returns:
        Result con CrossChapterResult conteniendo timelines, marcadores
        inferidos e inconsistencias nuevas
    """
    try:
        result = CrossChapterResult()

        if not markers:
            return Result.success(result)

        # Mapa entity_id → nombre canónico
        name_map: dict[int, str] = {}
        for entity in entities:
            if hasattr(entity, "id") and hasattr(entity, "canonical_name"):
                if entity.id is not None:
                    name_map[entity.id] = entity.canonical_name

        # Fase 1: Collect
        analepsis_chapters = _build_analepsis_chapters(timeline)
        by_entity = _collect_instances(markers, analepsis_chapters)

        if not by_entity:
            return Result.success(result)

        all_inferred: list[TemporalMarker] = []
        all_inconsistencies: list[TemporalInconsistency] = []

        for entity_id, instances in by_entity.items():
            entity_name = name_map.get(entity_id, f"Entidad {entity_id}")

            # Fase 2: Sort
            sorted_instances = _sort_instances(instances)

            # Fase 3: Link + Detect (on story-sorted data)
            links, link_inconsistencies = _link_and_detect(sorted_instances, entity_name)
            all_inconsistencies.extend(link_inconsistencies)

            # Fase 3b: Discourse-order regression check (C-3)
            discourse_inconsistencies = _check_discourse_regressions(instances, entity_name)
            all_inconsistencies.extend(discourse_inconsistencies)

            # Fase 4: Infer birth year
            birth_year, by_conf, by_inconsistencies = _infer_birth_year(
                sorted_instances, entity_name,
            )
            all_inconsistencies.extend(by_inconsistencies)

            # Fase 4: Infer from offsets
            offset_markers = _infer_from_offsets(sorted_instances, entity_id, entity_name)
            all_inferred.extend(offset_markers)

            # Construir EntityTimeline
            et = EntityTimeline(
                entity_id=entity_id,
                canonical_name=entity_name,
                instances=sorted_instances,
                inferred_birth_year=birth_year,
                birth_year_confidence=by_conf,
                links=links,
            )
            result.entity_timelines[entity_id] = et

        result.inferred_markers = all_inferred
        result.new_inconsistencies = all_inconsistencies

        logger.info(
            "Level C: %d entity timelines, %d links, %d inferred markers, %d inconsistencies",
            len(result.entity_timelines),
            sum(len(et.links) for et in result.entity_timelines.values()),
            len(result.inferred_markers),
            len(result.new_inconsistencies),
        )

        return Result.success(result)

    except Exception as e:
        logger.error(f"Level C cross-chapter linking failed: {e}")
        return Result.failure(e)
