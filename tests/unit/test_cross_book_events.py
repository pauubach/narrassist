"""
Tests para análisis de contradicciones de eventos cross-book.

Cubre:
- 4 reglas de contradicción (death_then_alive, injury, acquisition, location)
- Dataclasses (EventContradiction, CrossBookEventReport)
- CrossBookEventAnalyzer con dependencias mockeadas
- Edge cases: sin eventos, sin links, mismo orden de libros
"""

import pytest

from narrative_assistant.analysis.cross_book_events import (
    ALIVE_EVENTS,
    CONTRADICTION_RULES,
    CrossBookEventAnalyzer,
    CrossBookEventReport,
    EventContradiction,
    _check_acquisition_vs_loss,
    _check_death_then_alive,
    _check_injury_healed_differently,
    _check_location_impossibility,
)
from narrative_assistant.analysis.event_types import EventType


# ============================================================================
# Helpers
# ============================================================================

def _event(event_type: str, chapter: int = 1, description: str = "",
           metadata: dict | None = None, entity_ids: list | None = None) -> dict:
    """Crea un evento dict para tests."""
    return {
        "event_type": event_type,
        "chapter": chapter,
        "description": description,
        "confidence": 0.8,
        "metadata": metadata or {},
        "entity_ids": entity_ids or [],
    }


# ============================================================================
# EventContradiction dataclass
# ============================================================================

class TestEventContradiction:
    def test_to_dict_all_fields(self):
        c = EventContradiction(
            rule="death_then_alive",
            entity_name="Juan",
            description="Juan muere en libro A",
            event_a_type=EventType.DEATH.value,
            event_b_type=EventType.FIRST_APPEARANCE.value,
            book_a_name="Libro 1",
            book_b_name="Libro 2",
            book_a_chapter=5,
            book_b_chapter=1,
            confidence=0.9,
            metadata={"extra": "data"},
        )
        d = c.to_dict()
        assert d["rule"] == "death_then_alive"
        assert d["entity_name"] == "Juan"
        assert d["book_a_name"] == "Libro 1"
        assert d["book_b_name"] == "Libro 2"
        assert d["book_a_chapter"] == 5
        assert d["book_b_chapter"] == 1
        assert d["confidence"] == 0.9
        assert d["metadata"]["extra"] == "data"

    def test_to_dict_defaults(self):
        c = EventContradiction(
            rule="test", entity_name="X", description="desc",
            event_a_type="a", event_b_type="b",
            book_a_name="A", book_b_name="B",
        )
        d = c.to_dict()
        assert d["book_a_chapter"] is None
        assert d["book_b_chapter"] is None
        assert d["confidence"] == 0.7
        assert d["metadata"] == {}


# ============================================================================
# CrossBookEventReport dataclass
# ============================================================================

class TestCrossBookEventReport:
    def test_empty_report(self):
        r = CrossBookEventReport(collection_id=1, collection_name="Saga")
        d = r.to_dict()
        assert d["collection_id"] == 1
        assert d["contradictions"] == []
        assert d["summary"]["total_contradictions"] == 0
        assert d["summary"]["by_rule"] == {}

    def test_report_with_contradictions(self):
        c1 = EventContradiction(
            rule="death_then_alive", entity_name="A", description="d1",
            event_a_type="x", event_b_type="y",
            book_a_name="L1", book_b_name="L2",
        )
        c2 = EventContradiction(
            rule="death_then_alive", entity_name="B", description="d2",
            event_a_type="x", event_b_type="y",
            book_a_name="L1", book_b_name="L3",
        )
        c3 = EventContradiction(
            rule="location_impossibility", entity_name="A", description="d3",
            event_a_type="x", event_b_type="y",
            book_a_name="L1", book_b_name="L2",
        )
        r = CrossBookEventReport(
            collection_id=1, collection_name="Saga",
            contradictions=[c1, c2, c3],
            entity_links_analyzed=5,
            projects_analyzed=3,
        )
        d = r.to_dict()
        assert d["summary"]["total_contradictions"] == 3
        assert d["summary"]["by_rule"]["death_then_alive"] == 2
        assert d["summary"]["by_rule"]["location_impossibility"] == 1
        assert d["entity_links_analyzed"] == 5
        assert d["projects_analyzed"] == 3


# ============================================================================
# Rule: death_then_alive
# ============================================================================

class TestDeathThenAlive:
    def test_death_in_earlier_alive_in_later(self):
        events_a = [_event(EventType.DEATH.value, chapter=10, description="muere")]
        events_b = [_event(EventType.DECISION.value, chapter=1, description="decide algo")]
        result = _check_death_then_alive(
            "Juan", events_a, events_b, "Libro 1", "Libro 2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1
        assert result[0].rule == "death_then_alive"
        assert result[0].entity_name == "Juan"
        assert result[0].confidence == 0.9
        assert "Libro 1" in result[0].description
        assert "Libro 2" in result[0].description

    def test_death_in_later_no_contradiction(self):
        """Si la muerte es en el libro posterior, no hay contradicción."""
        events_a = [_event(EventType.DECISION.value)]
        events_b = [_event(EventType.DEATH.value)]
        result = _check_death_then_alive(
            "Juan", events_a, events_b, "Libro 1", "Libro 2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_no_death_events(self):
        events_a = [_event(EventType.INJURY.value)]
        events_b = [_event(EventType.HEALING.value)]
        result = _check_death_then_alive(
            "Juan", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_same_order_returns_empty(self):
        events_a = [_event(EventType.DEATH.value)]
        events_b = [_event(EventType.DECISION.value)]
        result = _check_death_then_alive(
            "Juan", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=1,
        )
        assert len(result) == 0

    def test_reversed_order_detects_correctly(self):
        """book_b tiene orden menor (muerte en B), book_a tiene alive events."""
        events_a = [_event(EventType.ALLIANCE.value, chapter=3)]
        events_b = [_event(EventType.DEATH.value, chapter=8)]
        result = _check_death_then_alive(
            "María", events_a, events_b, "Libro 2", "Libro 1",
            book_a_order=2, book_b_order=1,
        )
        assert len(result) == 1
        assert result[0].book_a_name == "Libro 1"  # El anterior cronológicamente
        assert result[0].book_b_name == "Libro 2"

    def test_death_no_alive_events_after(self):
        events_a = [_event(EventType.DEATH.value)]
        events_b = [_event(EventType.DEATH.value)]  # Morir de nuevo no es ALIVE_EVENT
        result = _check_death_then_alive(
            "Juan", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_all_alive_event_types_trigger(self):
        """Verifica que todos los ALIVE_EVENTS provocan contradicción con DEATH."""
        events_a = [_event(EventType.DEATH.value)]
        for alive_type in ALIVE_EVENTS:
            events_b = [_event(alive_type)]
            result = _check_death_then_alive(
                "Test", events_a, events_b, "L1", "L2",
                book_a_order=1, book_b_order=2,
            )
            assert len(result) == 1, f"ALIVE_EVENT {alive_type} should trigger contradiction"


# ============================================================================
# Rule: injury_healed_differently
# ============================================================================

class TestInjuryHealedDifferently:
    def test_different_body_parts(self):
        events_a = [_event(
            EventType.INJURY.value,
            metadata={"body_part": "brazo"},
            description="se lesiona el brazo",
        )]
        events_b = [_event(
            EventType.HEALING.value,
            metadata={"body_part": "pierna"},
            description="curación de pierna",
        )]
        result = _check_injury_healed_differently(
            "Ana", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1
        assert result[0].rule == "injury_healed_differently"
        assert "brazo" in result[0].description
        assert "pierna" in result[0].description

    def test_same_body_part_no_contradiction(self):
        events_a = [_event(EventType.INJURY.value, metadata={"body_part": "brazo"})]
        events_b = [_event(EventType.HEALING.value, metadata={"body_part": "brazo"})]
        result = _check_injury_healed_differently(
            "Ana", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_no_body_part_metadata(self):
        """Sin metadata de body_part no se puede detectar contradicción."""
        events_a = [_event(EventType.INJURY.value)]
        events_b = [_event(EventType.HEALING.value)]
        result = _check_injury_healed_differently(
            "Ana", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_one_body_part_empty(self):
        events_a = [_event(EventType.INJURY.value, metadata={"body_part": "brazo"})]
        events_b = [_event(EventType.HEALING.value, metadata={"body_part": ""})]
        result = _check_injury_healed_differently(
            "Ana", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_multiple_injuries_and_healings(self):
        events_a = [
            _event(EventType.INJURY.value, metadata={"body_part": "brazo"}),
            _event(EventType.INJURY.value, metadata={"body_part": "cabeza"}),
        ]
        events_b = [
            _event(EventType.HEALING.value, metadata={"body_part": "pierna"}),
            _event(EventType.HEALING.value, metadata={"body_part": "brazo"}),
        ]
        result = _check_injury_healed_differently(
            "Ana", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        # brazo→pierna (diff), brazo→brazo (same, skip), cabeza→pierna (diff), cabeza→brazo (diff)
        assert len(result) == 3


# ============================================================================
# Rule: acquisition_vs_loss
# ============================================================================

class TestAcquisitionVsLoss:
    def test_acquired_then_lost_without_explanation(self):
        events_a = [_event(EventType.ACQUISITION.value, metadata={"object": "espada"})]
        events_b = [_event(EventType.LOSS.value, metadata={"object": "espada"})]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1
        assert result[0].rule == "acquisition_vs_loss"
        assert "espada" in result[0].description

    def test_acquired_and_lost_in_same_book(self):
        """Si pierde el objeto en el mismo libro, no hay contradicción."""
        events_a = [
            _event(EventType.ACQUISITION.value, metadata={"object": "espada"}),
            _event(EventType.LOSS.value, metadata={"object": "espada"}),
        ]
        events_b = [_event(EventType.LOSS.value, metadata={"object": "espada"})]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_loss_with_later_acquisition(self):
        """Si en libro posterior re-adquiere antes de perder, no es contradicción."""
        events_a = [_event(EventType.ACQUISITION.value, metadata={"object": "espada"})]
        events_b = [
            _event(EventType.ACQUISITION.value, metadata={"object": "espada"}),
            _event(EventType.LOSS.value, metadata={"object": "espada"}),
        ]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_same_order_returns_empty(self):
        events_a = [_event(EventType.ACQUISITION.value, metadata={"object": "espada"})]
        events_b = [_event(EventType.LOSS.value, metadata={"object": "espada"})]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=1,
        )
        assert len(result) == 0

    def test_no_object_metadata(self):
        events_a = [_event(EventType.ACQUISITION.value)]
        events_b = [_event(EventType.LOSS.value)]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_case_insensitive_matching(self):
        events_a = [_event(EventType.ACQUISITION.value, metadata={"object": "Espada Mágica"})]
        events_b = [_event(EventType.LOSS.value, metadata={"object": "espada mágica"})]
        result = _check_acquisition_vs_loss(
            "Pedro", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1


# ============================================================================
# Rule: location_impossibility
# ============================================================================

class TestLocationImpossibility:
    def test_different_locations(self):
        events_a = [_event(
            EventType.LOCATION_CHANGE.value,
            chapter=10, metadata={"location": "Madrid"},
        )]
        events_b = [_event(
            EventType.LOCATION_CHANGE.value,
            chapter=1, metadata={"location": "Tokio"},
        )]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1
        assert result[0].rule == "location_impossibility"
        assert "Madrid" in result[0].description
        assert "Tokio" in result[0].description

    def test_same_location_no_contradiction(self):
        events_a = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": "Madrid"})]
        events_b = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": "madrid"})]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_book_a_not_earlier(self):
        events_a = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": "Madrid"})]
        events_b = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": "Tokio"})]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=2, book_b_order=1,
        )
        assert len(result) == 0

    def test_no_location_changes(self):
        events_a = [_event(EventType.DEATH.value)]
        events_b = [_event(EventType.DEATH.value)]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_empty_location_metadata(self):
        events_a = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": ""})]
        events_b = [_event(EventType.LOCATION_CHANGE.value, metadata={"location": "Tokio"})]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 0

    def test_uses_last_loc_a_and_first_loc_b(self):
        """Usa la última ubicación del libro A y la primera del libro B."""
        events_a = [
            _event(EventType.LOCATION_CHANGE.value, chapter=1, metadata={"location": "Madrid"}),
            _event(EventType.LOCATION_CHANGE.value, chapter=5, metadata={"location": "Barcelona"}),
            _event(EventType.LOCATION_CHANGE.value, chapter=10, metadata={"location": "Sevilla"}),
        ]
        events_b = [
            _event(EventType.LOCATION_CHANGE.value, chapter=1, metadata={"location": "Tokio"}),
            _event(EventType.LOCATION_CHANGE.value, chapter=5, metadata={"location": "Sevilla"}),
        ]
        result = _check_location_impossibility(
            "Elena", events_a, events_b, "L1", "L2",
            book_a_order=1, book_b_order=2,
        )
        assert len(result) == 1
        assert "Sevilla" in result[0].metadata["location_a"]
        assert "Tokio" in result[0].metadata["location_b"]


# ============================================================================
# CONTRADICTION_RULES registry
# ============================================================================

class TestContradictionRules:
    def test_all_four_rules_registered(self):
        assert len(CONTRADICTION_RULES) == 4
        assert _check_death_then_alive in CONTRADICTION_RULES
        assert _check_injury_healed_differently in CONTRADICTION_RULES
        assert _check_acquisition_vs_loss in CONTRADICTION_RULES
        assert _check_location_impossibility in CONTRADICTION_RULES


# ============================================================================
# ALIVE_EVENTS completeness
# ============================================================================

class TestAliveEvents:
    def test_death_not_in_alive_events(self):
        assert EventType.DEATH.value not in ALIVE_EVENTS

    def test_loss_not_in_alive_events(self):
        assert EventType.LOSS.value not in ALIVE_EVENTS

    def test_key_alive_types_present(self):
        expected = {
            EventType.DECISION.value,
            EventType.BETRAYAL.value,
            EventType.ALLIANCE.value,
            EventType.REVELATION.value,
            EventType.FIRST_APPEARANCE.value,
        }
        assert expected.issubset(ALIVE_EVENTS)


# ============================================================================
# CrossBookEventAnalyzer (con mocks)
# ============================================================================

class TestCrossBookEventAnalyzer:
    def test_filter_events_for_entity(self):
        analyzer = CrossBookEventAnalyzer()
        events = [
            {"entity_ids": [1, 2], "event_type": "death"},
            {"entity_ids": [3], "event_type": "injury"},
            {"entity_ids": [1], "event_type": "decision"},
            {"entity_ids": [], "event_type": "loss"},
        ]
        filtered = analyzer._filter_events_for_entity(events, 1)
        assert len(filtered) == 2
        assert filtered[0]["event_type"] == "death"
        assert filtered[1]["event_type"] == "decision"

    def test_filter_events_no_match(self):
        analyzer = CrossBookEventAnalyzer()
        events = [{"entity_ids": [1, 2], "event_type": "death"}]
        filtered = analyzer._filter_events_for_entity(events, 99)
        assert len(filtered) == 0

    def test_filter_events_empty_list(self):
        analyzer = CrossBookEventAnalyzer()
        filtered = analyzer._filter_events_for_entity([], 1)
        assert filtered == []


# ============================================================================
# Integration-style: rules con empty inputs
# ============================================================================

class TestEdgeCases:
    def test_all_rules_empty_events_a(self):
        for rule_fn in CONTRADICTION_RULES:
            result = rule_fn(
                entity_name="Test",
                events_a=[],
                events_b=[_event(EventType.DEATH.value)],
                book_a_name="L1", book_b_name="L2",
                book_a_order=1, book_b_order=2,
            )
            assert isinstance(result, list)

    def test_all_rules_empty_events_b(self):
        for rule_fn in CONTRADICTION_RULES:
            result = rule_fn(
                entity_name="Test",
                events_a=[_event(EventType.DEATH.value)],
                events_b=[],
                book_a_name="L1", book_b_name="L2",
                book_a_order=1, book_b_order=2,
            )
            assert isinstance(result, list)

    def test_all_rules_both_empty(self):
        for rule_fn in CONTRADICTION_RULES:
            result = rule_fn(
                entity_name="Test",
                events_a=[], events_b=[],
                book_a_name="L1", book_b_name="L2",
                book_a_order=1, book_b_order=2,
            )
            assert result == []
