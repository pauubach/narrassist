"""Behavior tests for HI-07 timeline voting integration in main pipeline."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import run_timeline


class _DummyTracker:
    def __init__(self):
        self.metrics = {}
        self.started = []
        self.ended = []

    def start_phase(self, phase_key, *_args):
        self.started.append(phase_key)

    def update_storage(self, **_kwargs):
        return None

    def update_time_remaining(self):
        return None

    def end_phase(self, phase_key, *_args):
        self.ended.append(phase_key)

    def check_cancelled(self):
        return None

    def set_metric(self, key, value):
        self.metrics[key] = value


class _FakeTimelineRepo:
    def clear_timeline(self, _project_id):
        return None

    def save_markers(self, _project_id, _markers):
        return None

    def save_event(self, _event):
        return None


class _FakeMarkerExtractor:
    def extract(self, text, chapter):
        return [{"text": text[:5], "chapter": chapter}]

    def extract_with_entities(self, text, entity_mentions, chapter):
        if entity_mentions:
            return [{"text": text[:5], "chapter": chapter}]
        return self.extract(text, chapter)


class _FakeTimelineBuilder:
    def build_from_markers(self, markers, chapter_data):
        return SimpleNamespace(events=[{"id": 1, "chapter": 1}], markers=markers, chapters=chapter_data)


def _ctx(run_multi_model_voting: bool) -> dict:
    chapter = SimpleNamespace(
        chapter_number=1,
        content="En 1990 sucedió algo.",
        title="Capítulo 1",
        start_char=0,
    )
    return {
        "project_id": 1,
        "chapters_with_ids": [chapter],
        "entities": [],
        "entity_repo": None,
        "full_text": "En 1990 sucedió algo.",
        "analysis_config": SimpleNamespace(
            run_multi_model_voting=run_multi_model_voting,
            use_llm=False,
        ),
    }


def test_run_timeline_uses_voting_checker_when_enabled(monkeypatch):
    class _FakeVotingChecker:
        def __init__(self, _config):
            pass

        def check(self, timeline, markers, text=None):
            assert timeline is not None
            assert markers
            assert text
            return SimpleNamespace(
                inconsistencies=[{"source": "voting"}],
                consensus_stats={"multi_method_pct": 100.0},
            )

    class _NeverCalledBasic:
        def check(self, _timeline, _markers):
            raise AssertionError("Basic checker should not run when voting works")

    monkeypatch.setattr("narrative_assistant.persistence.timeline.TimelineRepository", _FakeTimelineRepo)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalMarkerExtractor", _FakeMarkerExtractor)
    monkeypatch.setattr("narrative_assistant.temporal.TimelineBuilder", _FakeTimelineBuilder)
    monkeypatch.setattr("narrative_assistant.temporal.VotingTemporalChecker", _FakeVotingChecker)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalConsistencyChecker", _NeverCalledBasic)

    tracker = _DummyTracker()
    ctx = _ctx(run_multi_model_voting=True)
    run_timeline(ctx, tracker)

    assert tracker.metrics["timeline_voting_enabled"] is True
    assert "timeline_voting_stats" in tracker.metrics
    assert ctx["temporal_inconsistencies"] == [{"source": "voting"}]
    assert tracker.started == ["timeline"]
    assert tracker.ended == ["timeline"]


def test_run_timeline_falls_back_to_basic_checker_if_voting_fails(monkeypatch):
    class _FailingVotingChecker:
        def __init__(self, _config):
            pass

        def check(self, _timeline, _markers, text=None):
            raise RuntimeError("voting unavailable")

    class _BasicChecker:
        def check(self, _timeline, _markers):
            return [{"source": "basic"}]

    monkeypatch.setattr("narrative_assistant.persistence.timeline.TimelineRepository", _FakeTimelineRepo)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalMarkerExtractor", _FakeMarkerExtractor)
    monkeypatch.setattr("narrative_assistant.temporal.TimelineBuilder", _FakeTimelineBuilder)
    monkeypatch.setattr("narrative_assistant.temporal.VotingTemporalChecker", _FailingVotingChecker)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalConsistencyChecker", _BasicChecker)

    tracker = _DummyTracker()
    ctx = _ctx(run_multi_model_voting=True)
    run_timeline(ctx, tracker)

    assert tracker.metrics["timeline_voting_fallback"] is True
    assert ctx["temporal_inconsistencies"] == [{"source": "basic"}]


def test_run_timeline_uses_basic_checker_when_multi_model_voting_disabled(monkeypatch):
    class _VotingShouldNotRun:
        def __init__(self, _config):
            raise AssertionError("Voting checker should not be instantiated")

    class _BasicChecker:
        def check(self, _timeline, _markers):
            return [{"source": "basic"}]

    monkeypatch.setattr("narrative_assistant.persistence.timeline.TimelineRepository", _FakeTimelineRepo)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalMarkerExtractor", _FakeMarkerExtractor)
    monkeypatch.setattr("narrative_assistant.temporal.TimelineBuilder", _FakeTimelineBuilder)
    monkeypatch.setattr("narrative_assistant.temporal.VotingTemporalChecker", _VotingShouldNotRun)
    monkeypatch.setattr("narrative_assistant.temporal.TemporalConsistencyChecker", _BasicChecker)

    tracker = _DummyTracker()
    ctx = _ctx(run_multi_model_voting=False)
    run_timeline(ctx, tracker)

    assert tracker.metrics["timeline_voting_enabled"] is False
    assert ctx["temporal_inconsistencies"] == [{"source": "basic"}]
