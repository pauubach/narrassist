"""
Tests para rastreo de continuidad entre eventos.

Valida detección de inconsistencias cuando faltan eventos paired.
"""

import pytest

from narrative_assistant.analysis.event_continuity import (
    EventContinuityTracker,
    track_continuity_in_chapters,
)
from narrative_assistant.analysis.event_detection import DetectedEvent
from narrative_assistant.analysis.event_types import EventType


class TestEventContinuityTracker:
    """Tests para el tracker de continuidad."""

    @pytest.fixture
    def tracker(self):
        return EventContinuityTracker()

    def test_promise_without_resolution_creates_issue(self, tracker):
        """Promesa sin cumplir/romper genera issue."""
        promise = DetectedEvent(
            event_type=EventType.PROMISE,
            description="Juan prometió volver",
            confidence=0.8,
            start_char=0,
            end_char=20,
            metadata={"subject": "Juan"}
        )

        tracker.track_event(promise)
        issues = tracker.check_continuity()

        assert len(issues) > 0
        assert issues[0].event_type == EventType.PROMISE
        assert issues[0].paired_type == EventType.BROKEN_PROMISE

    def test_promise_with_broken_promise_no_issue(self, tracker):
        """Promesa + incumplimiento no genera issue."""
        promise = DetectedEvent(
            event_type=EventType.PROMISE,
            description="Juan prometió volver",
            confidence=0.8,
            start_char=0,
            end_char=20,
            metadata={"subject": "Juan"}
        )

        broken = DetectedEvent(
            event_type=EventType.BROKEN_PROMISE,
            description="Juan no volvió",
            confidence=0.7,
            start_char=100,
            end_char=120,
            metadata={"subject": "Juan"}
        )

        tracker.track_event(promise)
        tracker.track_event(broken)
        issues = tracker.check_continuity()

        # No debe haber issues para este par
        promise_issues = [i for i in issues if i.event_type == EventType.PROMISE]
        assert len(promise_issues) == 0

    def test_injury_without_healing_creates_issue(self, tracker):
        """Herida sin curación genera issue."""
        injury = DetectedEvent(
            event_type=EventType.INJURY,
            description="Herida en el hombro",
            confidence=0.8,
            start_char=0,
            end_char=30,
            metadata={"subject": "María", "body_part": "hombro"}
        )

        tracker.track_event(injury)
        issues = tracker.check_continuity()

        assert len(issues) > 0
        assert issues[0].event_type == EventType.INJURY
        assert issues[0].paired_type == EventType.HEALING

    def test_injury_with_healing_no_issue(self, tracker):
        """Herida + curación no genera issue."""
        injury = DetectedEvent(
            event_type=EventType.INJURY,
            description="Herida en el hombro",
            confidence=0.8,
            start_char=0,
            end_char=30,
            metadata={"subject": "María", "body_part": "hombro"}
        )

        healing = DetectedEvent(
            event_type=EventType.HEALING,
            description="Curación del hombro",
            confidence=0.7,
            start_char=100,
            end_char=130,
            metadata={"subject": "María", "body_part": "hombro"}
        )

        tracker.track_event(injury)
        tracker.track_event(healing)
        issues = tracker.check_continuity()

        injury_issues = [i for i in issues if i.event_type == EventType.INJURY]
        assert len(injury_issues) == 0

    def test_flashback_without_end_critical_severity(self, tracker):
        """Flashback sin cerrar es severidad critical."""
        flashback_start = DetectedEvent(
            event_type=EventType.FLASHBACK_START,
            description="Recordó...",
            confidence=0.7,
            start_char=0,
            end_char=20,
        )

        tracker.track_event(flashback_start)
        issues = tracker.check_continuity()

        assert len(issues) > 0
        issue = issues[0]
        assert issue.severity == "critical"

    def test_multiple_promises_different_subjects(self, tracker):
        """Múltiples promesas de diferentes sujetos se rastrean independientemente."""
        promise1 = DetectedEvent(
            event_type=EventType.PROMISE,
            description="Juan prometió",
            confidence=0.8,
            start_char=0,
            end_char=20,
            metadata={"subject": "Juan"}
        )

        promise2 = DetectedEvent(
            event_type=EventType.PROMISE,
            description="María prometió",
            confidence=0.8,
            start_char=50,
            end_char=70,
            metadata={"subject": "María"}
        )

        # Solo Juan rompe su promesa
        broken1 = DetectedEvent(
            event_type=EventType.BROKEN_PROMISE,
            description="Juan no cumplió",
            confidence=0.7,
            start_char=100,
            end_char=120,
            metadata={"subject": "Juan"}
        )

        tracker.track_event(promise1)
        tracker.track_event(promise2)
        tracker.track_event(broken1)
        issues = tracker.check_continuity()

        # Solo debe quedar issue de María
        assert len(issues) == 1
        assert issues[0].metadata.get("subject") == "María"

    def test_acquisition_loss_matching(self, tracker):
        """Adquisición + pérdida del mismo objeto se emparejan."""
        acquisition = DetectedEvent(
            event_type=EventType.ACQUISITION,
            description="Encontró la espada",
            confidence=0.8,
            start_char=0,
            end_char=30,
            metadata={"subject": "Pedro", "object": "espada"}
        )

        loss = DetectedEvent(
            event_type=EventType.LOSS,
            description="Perdió la espada",
            confidence=0.7,
            start_char=100,
            end_char=130,
            metadata={"subject": "Pedro", "object": "espada"}
        )

        tracker.track_event(acquisition)
        tracker.track_event(loss)
        issues = tracker.check_continuity()

        acquisition_issues = [i for i in issues if i.event_type == EventType.ACQUISITION]
        assert len(acquisition_issues) == 0


class TestCrossChapterContinuity:
    """Tests para continuidad entre múltiples capítulos."""

    def test_track_continuity_across_chapters(self):
        """Rastrea continuidad a través de capítulos."""
        events_by_chapter = {
            1: [
                DetectedEvent(
                    event_type=EventType.PROMISE,
                    description="Promesa en cap 1",
                    confidence=0.8,
                    start_char=0,
                    end_char=20,
                    metadata={"subject": "Ana"}
                )
            ],
            2: [],  # Sin eventos
            3: [
                DetectedEvent(
                    event_type=EventType.BROKEN_PROMISE,
                    description="Incumplimiento en cap 3",
                    confidence=0.7,
                    start_char=0,
                    end_char=25,
                    metadata={"subject": "Ana"}
                )
            ]
        }

        issues = track_continuity_in_chapters(events_by_chapter)

        # No debe haber issues: promesa en cap 1, incumplimiento en cap 3
        promise_issues = [i for i in issues if i.event_type == EventType.PROMISE]
        assert len(promise_issues) == 0

    def test_multiple_chapters_with_open_events(self):
        """Detecta eventos abiertos en múltiples capítulos."""
        events_by_chapter = {
            1: [
                DetectedEvent(
                    event_type=EventType.PROMISE,
                    description="Promesa 1",
                    confidence=0.8,
                    start_char=0,
                    end_char=20,
                    metadata={"subject": "Luis"}
                )
            ],
            2: [
                DetectedEvent(
                    event_type=EventType.INJURY,
                    description="Herida",
                    confidence=0.8,
                    start_char=0,
                    end_char=30,
                    metadata={"subject": "Carmen"}
                )
            ],
            3: []  # Sin resoluciones
        }

        issues = track_continuity_in_chapters(events_by_chapter)

        # Deben haber 2 issues: promesa + herida sin resolver
        assert len(issues) == 2
        event_types = {i.event_type for i in issues}
        assert EventType.PROMISE in event_types
        assert EventType.INJURY in event_types
