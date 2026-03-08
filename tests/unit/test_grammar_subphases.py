import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._grammar_subphases import run_grammar_phase  # noqa: E402


class _FakeTracker:
    def __init__(self):
        self.started = []
        self.ended = []
        self.storage_updates = []

    def start_phase(self, phase_name, message):
        self.started.append((phase_name, message))

    def end_phase(self, phase_name):
        self.ended.append(phase_name)

    def update_storage(self, **kwargs):
        self.storage_updates.append(kwargs)

    def update_time_remaining(self):
        return None


class _FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.warning_calls = []
        self.debug_calls = []

    def info(self, message, *args):
        self.info_calls.append((message, args))

    def warning(self, message, *args):
        self.warning_calls.append((message, args))

    def debug(self, message, *args):
        self.debug_calls.append((message, args))


def test_run_grammar_phase_skips_when_project_flags_disable_checks():
    tracker = _FakeTracker()
    logger = _FakeLogger()
    ctx = {
        "project": SimpleNamespace(settings={}),
        "project_id": 1,
        "full_text": "Texto de prueba.",
        "chapters_data": [],
        "entities": [],
        "analysis_config": SimpleNamespace(run_grammar=False, run_spelling=False),
        "selected_nlp_methods": {},
    }

    run_grammar_phase(
        ctx,
        tracker,
        logger=logger,
        to_optional_int=lambda value: value if isinstance(value, int) else None,
        find_chapter_number_for_position=lambda _chapters, _start: None,
    )

    assert tracker.started == [("grammar", "Revisando la redacción...")]
    assert tracker.ended == ["grammar"]
    assert ctx["grammar_issues"] == []
    assert ctx["spelling_issues"] == []
    assert ctx["correction_issues"] == []
    assert tracker.storage_updates[-1]["metrics_update"] == {
        "grammar_issues_found": 0,
        "correction_suggestions": 0,
    }


def test_run_grammar_phase_empty_method_lists_disable_checks_even_if_flags_are_enabled():
    tracker = _FakeTracker()
    logger = _FakeLogger()
    ctx = {
        "project": SimpleNamespace(settings={}),
        "project_id": 1,
        "full_text": "Texto de prueba.",
        "chapters_data": [],
        "entities": [],
        "analysis_config": SimpleNamespace(run_grammar=True, run_spelling=True),
        "selected_nlp_methods": {
            "grammar": [],
            "spelling": [],
        },
    }

    run_grammar_phase(
        ctx,
        tracker,
        logger=logger,
        to_optional_int=lambda value: value if isinstance(value, int) else None,
        find_chapter_number_for_position=lambda _chapters, _start: None,
    )

    assert ctx["grammar_issues"] == []
    assert ctx["spelling_issues"] == []
    assert ctx["correction_issues"] == []
    assert any("Grammar checks omitted" in call[0] for call in logger.info_calls)
    assert any("Spelling/editorial checks omitted" in call[0] for call in logger.info_calls)
