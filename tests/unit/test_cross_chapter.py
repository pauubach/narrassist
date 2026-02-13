"""Tests para Level C: Cross-Chapter Temporal Linking."""

from types import SimpleNamespace

import pytest

from narrative_assistant.core.result import Result
from narrative_assistant.entities.models import Entity, EntityType
from narrative_assistant.temporal.cross_chapter import (
    PHASE_AGE_RANGES,
    PHASE_AGE_TOLERANCE,
    CrossChapterResult,
    EntityTemporalInstance,
    EntityTimeline,
    TemporalLink,
    _build_analepsis_chapters,
    _check_discourse_regressions,
    _collect_instances,
    _get_age_from_instance,
    _infer_birth_year,
    _infer_from_offsets,
    _is_phase_compatible_with_age,
    _link_and_detect,
    _parse_instance_id,
    _sort_instances,
    build_entity_timelines,
)
from narrative_assistant.temporal.inconsistencies import (
    InconsistencySeverity,
    InconsistencyType,
)
from narrative_assistant.temporal.markers import MarkerType, TemporalMarker
from narrative_assistant.temporal.timeline import (
    NarrativeOrder,
    Timeline,
    TimelineEvent,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_marker(
    *,
    text: str = "test",
    chapter: int = 1,
    entity_id: int | None = None,
    age: int | None = None,
    age_phase: str | None = None,
    year: int | None = None,
    offset: int | None = None,
    temporal_instance_id: str | None = None,
    confidence: float = 0.9,
) -> TemporalMarker:
    """Helper para crear TemporalMarker con temporal_instance_id."""
    m = TemporalMarker(
        text=text,
        marker_type=MarkerType.CHARACTER_AGE,
        start_char=0,
        end_char=len(text),
        chapter=chapter,
        entity_id=entity_id,
        age=age,
        age_phase=age_phase,
        year=year,
        confidence=confidence,
    )
    if offset is not None:
        m.relative_year_offset = offset
    if temporal_instance_id:
        m.temporal_instance_id = temporal_instance_id
    return m


def _make_entity(id: int, name: str) -> Entity:
    """Helper para crear Entity."""
    return Entity(
        id=id,
        project_id=1,
        entity_type=EntityType.CHARACTER,
        canonical_name=name,
        aliases=[],
    )


def _make_timeline(*events: TimelineEvent) -> Timeline:
    """Helper para crear Timeline con eventos."""
    tl = Timeline()
    for e in events:
        tl.events.append(e)
    return tl


def _make_event(
    id: int,
    chapter: int,
    narrative_order: NarrativeOrder = NarrativeOrder.CHRONOLOGICAL,
) -> TimelineEvent:
    """Helper para crear TimelineEvent."""
    return TimelineEvent(
        id=id,
        description=f"Event {id}",
        chapter=chapter,
        narrative_order=narrative_order,
    )


# ============================================================================
# Test 1: Simple age progression
# ============================================================================


class TestSimpleAgeProgression:
    """Ana@10 Ch1 → Ana@30 Ch5 → link gap=20."""

    def test_age_progression_link(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=5, entity_id=1, age=30, temporal_instance_id="1@age:30"),
        ]
        entities = [_make_entity(1, "Ana")]
        timeline = _make_timeline()

        result = build_entity_timelines(markers, entities, timeline)
        assert result.is_success
        cross = result.value

        et = cross.entity_timelines[1]
        assert len(et.links) == 1
        link = et.links[0]
        assert link.relationship == "age_progression"
        assert link.inferred_gap_years == 20.0

    def test_no_inconsistencies_on_normal_progression(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=5, entity_id=1, age=30, temporal_instance_id="1@age:30"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        assert len(result.value.new_inconsistencies) == 0


# ============================================================================
# Test 2: Phase + age overlap
# ============================================================================


class TestPhaseAgeOverlap:
    """phase:child Ch1 + age:8 Ch3 → linked."""

    def test_phase_age_compatible(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
            _make_marker(chapter=3, entity_id=1, age=8, temporal_instance_id="1@age:8"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        et = result.value.entity_timelines[1]
        # Should have a phase_age_overlap link, no inconsistency
        links_types = [l.relationship for l in et.links]
        assert "phase_age_overlap" in links_types
        assert len(result.value.new_inconsistencies) == 0


# ============================================================================
# Test 3: Birth year inference
# ============================================================================


class TestBirthYearInference:
    """age:10 + year:1985 → birth=1975."""

    def test_birth_year_from_single_pair(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=1, entity_id=1, year=1985, temporal_instance_id="1@year:1985"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        et = result.value.entity_timelines[1]
        assert et.inferred_birth_year == 1975
        assert et.birth_year_confidence == 0.9


# ============================================================================
# Test 4: Birth year contradiction
# ============================================================================


class TestBirthYearContradiction:
    """(1985,10)→1975 vs (2005,25)→1980 → flag."""

    def test_birth_year_spread_flags_inconsistency(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=1, entity_id=1, year=1985, temporal_instance_id="1@year:1985"),
            _make_marker(chapter=3, entity_id=1, age=25, temporal_instance_id="1@age:25"),
            _make_marker(chapter=3, entity_id=1, year=2005, temporal_instance_id="1@year:2005"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        inc_types = [i.inconsistency_type for i in result.value.new_inconsistencies]
        assert InconsistencyType.BIRTH_YEAR_CONTRADICTION in inc_types


# ============================================================================
# Test 5: Birth year within tolerance
# ============================================================================


class TestBirthYearTolerance:
    """(1985,10)→1975 vs (1986,10)→1976 → ok (spread=1)."""

    def test_birth_year_small_spread_ok(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=1, entity_id=1, year=1985, temporal_instance_id="1@year:1985"),
            _make_marker(chapter=3, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=3, entity_id=1, year=1986, temporal_instance_id="1@year:1986"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        # Spread = 1 → no contradiction
        birth_contradictions = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.BIRTH_YEAR_CONTRADICTION
        ]
        assert len(birth_contradictions) == 0


# ============================================================================
# Test 6: Offset inference
# ============================================================================


class TestOffsetInference:
    """age:40 Ch1 + offset:+5 Ch3 → infer age:45."""

    def test_offset_infers_age(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=40, temporal_instance_id="1@age:40"),
            _make_marker(chapter=3, entity_id=1, offset=5, temporal_instance_id="1@offset_years:+5"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        inferred = result.value.inferred_markers
        assert len(inferred) == 1
        assert inferred[0].age == 45
        assert inferred[0].chapter == 3
        assert inferred[0].confidence < 0.9  # Penalized for being inferred


# ============================================================================
# Test 7: Age regression with flashback → suppressed
# ============================================================================


class TestAgeRegressionWithFlashback:
    """Age regression in analepsis chapter → no alert."""

    def test_flashback_suppresses_regression(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=40, temporal_instance_id="1@age:40"),
            _make_marker(chapter=3, entity_id=1, age=10, temporal_instance_id="1@age:10"),
        ]
        # Mark chapter 3 as analepsis
        timeline = _make_timeline(
            _make_event(1, chapter=1),
            _make_event(2, chapter=3, narrative_order=NarrativeOrder.ANALEPSIS),
        )
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], timeline)
        assert result.is_success
        # No regression alert — discourse regression suppressed by analepsis
        regressions = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION
        ]
        assert len(regressions) == 0
        # Story-sorted: age:10 comes before age:40 → progression link
        et = result.value.entity_timelines[1]
        assert any(l.relationship == "age_progression" for l in et.links)


# ============================================================================
# Test 8: Age regression without flashback → CRITICAL alert
# ============================================================================


class TestAgeRegressionNoFlashback:
    """Age regression without analepsis → CRITICAL alert."""

    def test_regression_without_flashback_is_critical(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=40, temporal_instance_id="1@age:40"),
            _make_marker(chapter=3, entity_id=1, age=10, temporal_instance_id="1@age:10"),
        ]
        timeline = _make_timeline()  # No flashback markers
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], timeline)
        assert result.is_success
        regressions = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION
        ]
        assert len(regressions) == 1
        assert regressions[0].severity == InconsistencySeverity.CRITICAL


# ============================================================================
# Test 9: Same age in 2 chapters → co-occurrence
# ============================================================================


class TestSameAgeTwoChapters:
    """Same age in different chapters → co-occurrence, no alert."""

    def test_co_occurrence_no_alert(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=40, temporal_instance_id="1@age:40"),
            _make_marker(chapter=5, entity_id=1, age=40, temporal_instance_id="1@age:40"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        assert len(result.value.new_inconsistencies) == 0


# ============================================================================
# Test 10: Phase-age incompatible
# ============================================================================


class TestPhaseAgeIncompatible:
    """phase:child + age:40 → MEDIUM alert."""

    def test_incompatible_phase_age(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
            _make_marker(chapter=3, entity_id=1, age=40, temporal_instance_id="1@age:40"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        inc = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.PHASE_AGE_INCOMPATIBLE
        ]
        assert len(inc) == 1
        assert inc[0].severity == InconsistencySeverity.MEDIUM


# ============================================================================
# Test 11: Phase-age compatible with tolerance
# ============================================================================


class TestPhaseAgeWithTolerance:
    """phase:young + age:38 → ok (within range 17-40, or up to 43 with tolerance)."""

    def test_compatible_with_tolerance(self):
        # "young" range = (17, 40) + tolerance 3 → (14, 43)
        assert _is_phase_compatible_with_age("young", 38)
        assert _is_phase_compatible_with_age("young", 43)  # At tolerance boundary
        assert not _is_phase_compatible_with_age("young", 44)  # Beyond tolerance

    def test_child_boundary_with_tolerance(self):
        # "child" range = (0, 14) + tolerance 3 → (-3, 17)
        assert _is_phase_compatible_with_age("child", 16)  # Within tolerance
        assert _is_phase_compatible_with_age("child", 17)  # At tolerance edge
        assert not _is_phase_compatible_with_age("child", 18)  # Beyond


# ============================================================================
# Test 12: No entity_id markers → skip gracefully
# ============================================================================


class TestNoEntityIdMarkers:
    """Markers without entity_id are skipped."""

    def test_no_entity_id_skipped(self):
        markers = [
            _make_marker(chapter=1, entity_id=None, age=40, temporal_instance_id="1@age:40"),
            _make_marker(chapter=3, entity_id=None, age=30, temporal_instance_id=None),
        ]
        result = build_entity_timelines(markers, [], _make_timeline())
        assert result.is_success
        assert len(result.value.entity_timelines) == 0
        assert len(result.value.new_inconsistencies) == 0


# ============================================================================
# Test 13: Empty markers list → empty result
# ============================================================================


class TestEmptyMarkers:
    """Empty markers → empty result, no errors."""

    def test_empty_markers(self):
        result = build_entity_timelines([], [], _make_timeline())
        assert result.is_success
        assert len(result.value.entity_timelines) == 0
        assert len(result.value.inferred_markers) == 0
        assert len(result.value.new_inconsistencies) == 0


# ============================================================================
# Test 14: Phase-only timeline → sorted by rank, low confidence
# ============================================================================


class TestPhaseOnlyTimeline:
    """Only phases, no ages → sorted by phase rank."""

    def test_phase_only_sorted(self):
        markers = [
            _make_marker(chapter=3, entity_id=1, age_phase="adult", temporal_instance_id="1@phase:adult"),
            _make_marker(chapter=1, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
            _make_marker(chapter=5, entity_id=1, age_phase="elder", temporal_instance_id="1@phase:elder"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        et = result.value.entity_timelines[1]
        # Instances should be sorted: child, adult, elder
        phases = [inst.value for inst in et.instances]
        assert phases == ["child", "adult", "elder"]

    def test_phase_progression_link(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
            _make_marker(chapter=5, entity_id=1, age_phase="elder", temporal_instance_id="1@phase:elder"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        et = result.value.entity_timelines[1]
        assert any(l.relationship == "phase_progression" for l in et.links)


# ============================================================================
# Test 15: Explicit age overrides inferred age from offset
# ============================================================================


class TestExplicitOverridesInferred:
    """Explicit age in a chapter means offset inference is skipped for that chapter."""

    def test_no_inferred_when_explicit_exists(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=40, temporal_instance_id="1@age:40"),
            # Chapter 3 has BOTH an explicit age and an offset
            _make_marker(chapter=3, entity_id=1, age=50, temporal_instance_id="1@age:50"),
            _make_marker(chapter=3, entity_id=1, offset=5, temporal_instance_id="1@offset_years:+5"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        # No inferred markers — ch3 already has explicit age 50
        assert len(result.value.inferred_markers) == 0


# ============================================================================
# Utility function tests
# ============================================================================


class TestParseInstanceId:
    """Tests para _parse_instance_id."""

    def test_age(self):
        assert _parse_instance_id("1@age:40") == ("age", 40)

    def test_phase(self):
        assert _parse_instance_id("1@phase:child") == ("phase", "child")

    def test_year(self):
        assert _parse_instance_id("1@year:1985") == ("year", 1985)

    def test_offset_positive(self):
        assert _parse_instance_id("1@offset_years:+5") == ("offset", 5)

    def test_offset_negative(self):
        assert _parse_instance_id("1@offset_years:-3") == ("offset", -3)

    def test_invalid(self):
        assert _parse_instance_id("invalid") is None

    def test_no_value(self):
        assert _parse_instance_id("1@age:") is None


class TestBuildAnalepsisChapters:
    """Tests para _build_analepsis_chapters."""

    def test_empty_timeline(self):
        assert _build_analepsis_chapters(_make_timeline()) == set()

    def test_detects_analepsis(self):
        tl = _make_timeline(
            _make_event(1, chapter=1),
            _make_event(2, chapter=3, narrative_order=NarrativeOrder.ANALEPSIS),
            _make_event(3, chapter=5, narrative_order=NarrativeOrder.ANALEPSIS),
        )
        assert _build_analepsis_chapters(tl) == {3, 5}


class TestMultipleEntities:
    """Multiple entities are tracked independently."""

    def test_two_entities_independent(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age=10, temporal_instance_id="1@age:10"),
            _make_marker(chapter=5, entity_id=1, age=30, temporal_instance_id="1@age:30"),
            _make_marker(chapter=1, entity_id=2, age=50, temporal_instance_id="2@age:50"),
            _make_marker(chapter=5, entity_id=2, age=40, temporal_instance_id="2@age:40"),
        ]
        entities = [_make_entity(1, "Ana"), _make_entity(2, "Pedro")]
        result = build_entity_timelines(markers, entities, _make_timeline())
        assert result.is_success

        # Ana: normal progression
        assert 1 in result.value.entity_timelines
        ana_inc = [
            i for i in result.value.new_inconsistencies
            if "Ana" in i.description
        ]
        assert len(ana_inc) == 0

        # Pedro: regression → alert
        assert 2 in result.value.entity_timelines
        pedro_inc = [
            i for i in result.value.new_inconsistencies
            if "Pedro" in i.description
        ]
        assert len(pedro_inc) == 1
        assert pedro_inc[0].inconsistency_type == InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION


class TestPhaseRegression:
    """Phase goes backward without flashback → alert."""

    def test_phase_regression_alert(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age_phase="elder", temporal_instance_id="1@phase:elder"),
            _make_marker(chapter=5, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        regressions = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION
        ]
        assert len(regressions) == 1

    def test_phase_regression_suppressed_by_flashback(self):
        markers = [
            _make_marker(chapter=1, entity_id=1, age_phase="elder", temporal_instance_id="1@phase:elder"),
            _make_marker(chapter=5, entity_id=1, age_phase="child", temporal_instance_id="1@phase:child"),
        ]
        timeline = _make_timeline(
            _make_event(1, chapter=1),
            _make_event(2, chapter=5, narrative_order=NarrativeOrder.ANALEPSIS),
        )
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], timeline)
        assert result.is_success
        regressions = [
            i for i in result.value.new_inconsistencies
            if i.inconsistency_type == InconsistencyType.CROSS_CHAPTER_AGE_REGRESSION
        ]
        assert len(regressions) == 0


class TestResultPattern:
    """Verifica que build_entity_timelines retorna Result correctamente."""

    def test_returns_result_success(self):
        result = build_entity_timelines([], [], _make_timeline())
        assert isinstance(result, Result)
        assert result.is_success
        assert isinstance(result.value, CrossChapterResult)


class TestOffsetNegative:
    """Offset negativo: age:40 Ch5 + offset:-10 Ch1 → infer age:30 en Ch1."""

    def test_negative_offset_not_inferred_without_prior(self):
        """Offset en Ch1 sin edad previa → no puede inferir."""
        markers = [
            _make_marker(chapter=1, entity_id=1, offset=-10, temporal_instance_id="1@offset_years:-10"),
            _make_marker(chapter=5, entity_id=1, age=40, temporal_instance_id="1@age:40"),
        ]
        result = build_entity_timelines(markers, [_make_entity(1, "Ana")], _make_timeline())
        assert result.is_success
        # Ch1 offset is BEFORE Ch5 age, so no "preceding" age → no inference
        # (offset inference only looks at PRECEDING chapters)
        assert len(result.value.inferred_markers) == 0
