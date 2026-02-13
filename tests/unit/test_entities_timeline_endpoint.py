"""
Tests for GET /api/projects/{project_id}/entities/{entity_id}/timeline.

Focus:
- ownership checks (entity belongs to project)
- empty timelines
- chapter-aware ordering (first appearance in earliest chapter number)
- attribute events without duplicates when chapter_id == chapter_number
- exception safety
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

API_DIR = Path(__file__).resolve().parent.parent.parent / "api-server"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import deps
from routers.entities import get_entity_timeline


def _entity(entity_id: int = 7, project_id: int = 1, name: str = "Marta"):
    return SimpleNamespace(id=entity_id, project_id=project_id, canonical_name=name)


def _mention(
    chapter_id: int,
    surface_form: str = "Marta",
    context_before: str = "",
    context_after: str = "",
):
    return SimpleNamespace(
        chapter_id=chapter_id,
        surface_form=surface_form,
        context_before=context_before,
        context_after=context_after,
    )


def _chapter(chapter_id: int, chapter_number: int, title: str):
    return SimpleNamespace(id=chapter_id, chapter_number=chapter_number, title=title)


def _attribute(
    *,
    chapter_id: int | None = None,
    first_mention_chapter: int | None = None,
    key: str = "estado",
    value: str = "agotada",
):
    return SimpleNamespace(
        chapter_id=chapter_id,
        first_mention_chapter=first_mention_chapter,
        attribute_key=key,
        attribute_value=value,
    )


@pytest.fixture
def mocked_repositories(monkeypatch):
    entity_repo = MagicMock()
    chapter_repo = MagicMock()
    monkeypatch.setattr(deps, "entity_repository", entity_repo)
    monkeypatch.setattr(deps, "chapter_repository", chapter_repo)
    return entity_repo, chapter_repo


class TestEntityTimelineEndpoint:
    def test_returns_entity_not_found_when_ownership_fails(self, mocked_repositories):
        entity_repo, _ = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=999)

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))

        assert response.success is False
        assert response.error == "Entidad no encontrada"

    def test_returns_empty_list_when_entity_has_no_mentions(self, mocked_repositories):
        entity_repo, _ = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=1)
        entity_repo.get_mentions_by_entity.return_value = []

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))

        assert response.success is True
        assert response.data == []
        entity_repo.get_attributes_by_entity.assert_not_called()

    def test_marks_first_appearance_by_earliest_chapter_number(
        self, mocked_repositories
    ):
        """
        If chapter IDs are not aligned with chapter numbers, first appearance
        must still be assigned to the earliest narrative chapter.
        """
        entity_repo, chapter_repo = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=1)
        entity_repo.get_mentions_by_entity.return_value = [
            _mention(chapter_id=200, surface_form="Marta"),  # chapter_number=1
            _mention(chapter_id=100, surface_form="Marta"),  # chapter_number=3
        ]
        entity_repo.get_attributes_by_entity.return_value = []
        chapter_repo.get_by_project.return_value = [
            _chapter(chapter_id=100, chapter_number=3, title="Capítulo Tres"),
            _chapter(chapter_id=200, chapter_number=1, title="Capítulo Uno"),
        ]

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))
        assert response.success is True

        first_event = response.data[0]
        assert first_event["type"] == "first_appearance"
        assert first_event["chapter"] == 1
        assert first_event["chapterTitle"] == "Capítulo Uno"

    def test_does_not_duplicate_attribute_event_when_ids_match_numbers(
        self, mocked_repositories
    ):
        """
        chapter_id and chapter_number can be equal in many datasets.
        The same attribute must be emitted once, not twice.
        """
        entity_repo, chapter_repo = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=1)
        entity_repo.get_mentions_by_entity.return_value = [
            _mention(chapter_id=1, surface_form="Marta")
        ]
        entity_repo.get_attributes_by_entity.return_value = [
            _attribute(chapter_id=1, key="edad", value="40")
        ]
        chapter_repo.get_by_project.return_value = [
            _chapter(chapter_id=1, chapter_number=1, title="Inicio")
        ]

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))
        assert response.success is True

        attribute_events = [e for e in response.data if e["type"] == "attribute"]
        assert len(attribute_events) == 1
        assert "edad = 40" in attribute_events[0]["description"]

    def test_truncates_context_to_200_chars(self, mocked_repositories):
        entity_repo, chapter_repo = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=1)
        entity_repo.get_mentions_by_entity.return_value = [
            _mention(
                chapter_id=10,
                surface_form="Marta",
                context_before="a" * 250,
                context_after="b" * 250,
            )
        ]
        entity_repo.get_attributes_by_entity.return_value = []
        chapter_repo.get_by_project.return_value = [
            _chapter(chapter_id=10, chapter_number=4, title="Nudo")
        ]

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))
        assert response.success is True

        first_event = response.data[0]
        assert first_event["type"] == "first_appearance"
        assert len(first_event["context"]) == 200

    def test_returns_internal_error_on_unexpected_exception(self, mocked_repositories):
        entity_repo, _ = mocked_repositories
        entity_repo.get_entity.return_value = _entity(project_id=1)
        entity_repo.get_mentions_by_entity.side_effect = RuntimeError("boom")

        response = asyncio.run(get_entity_timeline(project_id=1, entity_id=7))

        assert response.success is False
        assert response.error == "Error interno del servidor"
