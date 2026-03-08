import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_structure_helpers import (  # noqa: E402
    compute_and_persist_chapter_metrics,
    detect_and_persist_dialogues,
    find_chapter_id_for_position,
    initialize_dialogue_style_preference,
)


def test_find_chapter_id_for_position_uses_closest_fallback():
    chapters = [
        SimpleNamespace(id=10, start_char=0, end_char=100),
        SimpleNamespace(id=20, start_char=150, end_char=300),
    ]

    assert find_chapter_id_for_position(chapters, 40) == 10
    assert find_chapter_id_for_position(chapters, 130) == 20
    assert find_chapter_id_for_position([], 50) is None


def test_compute_and_persist_chapter_metrics_updates_matching_chapters(monkeypatch):
    updated = []

    class _Repo:
        def update_metrics(self, chapter_id, metrics):
            updated.append((chapter_id, metrics))

    monkeypatch.setattr(
        "narrative_assistant.persistence.chapter.compute_chapter_metrics",
        lambda content: {"dialogue_ratio": 0.2, "word_count": len(content.split())},
    )

    compute_and_persist_chapter_metrics(
        chapters_data=[
            {"chapter_number": 1, "content": "uno dos tres"},
            {"chapter_number": 2, "content": ""},
        ],
        chapters_with_ids=[
            SimpleNamespace(id=101, chapter_number=1),
            SimpleNamespace(id=202, chapter_number=2),
        ],
        chapter_repo=_Repo(),
        chapters_count=2,
        logger=logging.getLogger("test"),
    )

    assert updated == [(101, {"dialogue_ratio": 0.2, "word_count": 3})]


def test_detect_and_persist_dialogues_cleans_and_saves(monkeypatch):
    saved_batches = []
    deleted_projects = []

    class _DialogueRepo:
        def delete_by_project(self, project_id):
            deleted_projects.append(project_id)

        def create_batch(self, items):
            saved_batches.append(items)

    class _DialogueData:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    fake_result = SimpleNamespace(
        is_success=True,
        value=SimpleNamespace(
            dialogues=[
                SimpleNamespace(
                    start_char=5,
                    end_char=17,
                    text="Hola Maria",
                    dialogue_type=SimpleNamespace(value="dash"),
                    original_format="—",
                    attribution_text="dijo Juan",
                    speaker_hint="Juan",
                    confidence=0.92,
                )
            ]
        ),
    )

    monkeypatch.setattr(
        "narrative_assistant.persistence.dialogue.get_dialogue_repository",
        lambda db_session: _DialogueRepo(),
    )
    monkeypatch.setattr(
        "narrative_assistant.persistence.dialogue.DialogueData",
        _DialogueData,
    )
    monkeypatch.setattr(
        "narrative_assistant.nlp.dialogue.detect_dialogues",
        lambda content: fake_result,
    )

    total = detect_and_persist_dialogues(
        project_id=7,
        chapters_data=[{"chapter_number": 1, "content": "—Hola Maria—"}],
        chapters_with_ids=[SimpleNamespace(id=11, chapter_number=1)],
        db_session=object(),
        chapters_count=1,
        logger=logging.getLogger("test"),
    )

    assert total == 1
    assert deleted_projects == [7]
    assert len(saved_batches) == 1
    assert saved_batches[0][0].project_id == 7
    assert saved_batches[0][0].chapter_id == 11
    assert saved_batches[0][0].speaker_hint == "Juan"


def test_initialize_dialogue_style_preference_only_when_missing(monkeypatch):
    project = SimpleNamespace(
        settings_json={
            "correction_config": {
                "dialogue_dash": "em_dash",
                "quote_style": "guillemets",
            }
        }
    )
    updated = []

    class _ProjectManager:
        def __init__(self, db_session):
            self.db_session = db_session

        def get_by_id(self, project_id):
            assert project_id == 12
            return project

        def update(self, project_obj):
            updated.append(project_obj.settings_json.copy())

    monkeypatch.setattr(
        "narrative_assistant.persistence.project.ProjectManager",
        _ProjectManager,
    )
    monkeypatch.setattr(
        "narrative_assistant.nlp.dialogue_config_mapper.map_correction_config_to_dialogue_preference",
        lambda dialogue_dash, quote_style: f"{dialogue_dash}:{quote_style}",
    )

    initialize_dialogue_style_preference(12, object(), logging.getLogger("test"))

    assert updated == [
        {
            "correction_config": {
                "dialogue_dash": "em_dash",
                "quote_style": "guillemets",
            },
            "dialogue_style_preference": "em_dash:guillemets",
        }
    ]

    initialize_dialogue_style_preference(12, object(), logging.getLogger("test"))
    assert len(updated) == 1
