"""Tests de integración ligera para propagación temporal con menciones de entidad."""

from types import SimpleNamespace

from narrative_assistant.core.result import Result
from narrative_assistant.entities.models import Entity, EntityType
from narrative_assistant.exporters.document_exporter import ExportOptions, collect_export_data
from narrative_assistant.pipelines.analysis_pipeline import ChapterInfo, _run_temporal_analysis


def test_run_temporal_analysis_builds_temporal_instance_from_mentions(monkeypatch):
    """El pipeline batch debe asociar edad->entidad al existir menciones persistidas."""

    class FakeChapterRepository:
        def get_by_project(self, _project_id: int):
            return [SimpleNamespace(id=10, chapter_number=1, start_char=100)]

    class FakeEntityRepository:
        def get_mentions_by_entity(self, _entity_id: int):
            return [SimpleNamespace(chapter_id=10, start_char=100, end_char=103)]

    monkeypatch.setattr(
        "narrative_assistant.persistence.chapter.ChapterRepository",
        FakeChapterRepository,
    )
    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline.get_entity_repository",
        lambda: FakeEntityRepository(),
    )

    chapters = [
        ChapterInfo(
            number=1,
            title="Capítulo 1",
            content="Ana, a los 40 años, volvió al pueblo.",
            start_char=100,
            end_char=140,
            word_count=8,
        )
    ]
    entities = [
        Entity(
            id=1,
            project_id=1,
            entity_type=EntityType.CHARACTER,
            canonical_name="Ana",
        )
    ]

    result = _run_temporal_analysis(
        text=chapters[0].content,
        chapters=chapters,
        project_id=1,
        entities=entities,
    )

    assert result.is_success
    markers = result.value["markers"]
    assert any(m.temporal_instance_id == "1@age:40" for m in markers)


def test_collect_export_data_timeline_uses_entity_mentions_for_instances():
    """La exportación debe conservar temporal_instance_id cuando hay menciones."""

    class FakeProjectManager:
        def get(self, _project_id: int):
            return Result.success(
                SimpleNamespace(
                    name="Proyecto Test",
                    description="",
                    word_count=1200,
                    chapter_count=1,
                )
            )

    class FakeEntityRepository:
        def get_entities_by_project(self, _project_id: int, active_only: bool = True):
            return [
                Entity(
                    id=1,
                    project_id=1,
                    entity_type=EntityType.CHARACTER,
                    canonical_name="Ana",
                )
            ]

        def get_mentions_by_entity(self, _entity_id: int):
            return [SimpleNamespace(chapter_id=10, start_char=100, end_char=103)]

    class FakeChapterRepository:
        def get_by_project(self, _project_id: int):
            return [
                SimpleNamespace(
                    id=10,
                    chapter_number=1,
                    title="Capítulo 1",
                    start_char=100,
                    content="Ana, a los 40 años, volvió al pueblo.",
                )
            ]

    options = ExportOptions(
        include_cover=False,
        include_toc=False,
        include_statistics=False,
        include_character_sheets=False,
        include_alerts=False,
        include_timeline=True,
        include_relationships=False,
        include_style_guide=False,
    )

    result = collect_export_data(
        project_id=1,
        project_manager=FakeProjectManager(),
        entity_repository=FakeEntityRepository(),
        alert_repository=None,
        chapter_repository=FakeChapterRepository(),
        options=options,
    )

    assert result.is_success
    events = result.value.timeline_events
    assert len(events) > 0
    assert any(event.get("temporal_instance_id") == "1@age:40" for event in events)


def test_load_entity_mentions_by_chapter_shared_utility():
    """La utilidad compartida agrupa menciones correctamente por capítulo."""
    from narrative_assistant.temporal.entity_mentions import load_entity_mentions_by_chapter

    chapters = [
        SimpleNamespace(id=10, chapter_number=1, start_char=0),
        SimpleNamespace(id=20, chapter_number=2, start_char=500),
    ]
    entities = [
        Entity(id=1, project_id=1, entity_type=EntityType.CHARACTER, canonical_name="Ana"),
        Entity(id=2, project_id=1, entity_type=EntityType.CHARACTER, canonical_name="Pedro"),
    ]

    class MockEntityRepo:
        def get_mentions_by_entity(self, entity_id):
            if entity_id == 1:
                return [
                    SimpleNamespace(chapter_id=10, start_char=5, end_char=8),
                    SimpleNamespace(chapter_id=20, start_char=510, end_char=513),
                ]
            return [SimpleNamespace(chapter_id=10, start_char=20, end_char=25)]

    result = load_entity_mentions_by_chapter(entities, chapters, MockEntityRepo())

    assert 1 in result
    assert 2 in result
    # Cap 1: Ana (5-8 → rel 5-8) + Pedro (20-25 → rel 20-25) = 2 menciones
    assert len(result[1]) == 2
    # Cap 2: solo Ana (510-513 → rel 10-13)
    assert len(result[2]) == 1
    assert result[2][0] == (1, 10, 13)


def test_load_entity_mentions_skips_non_character():
    """Entidades no-personaje se excluyen de la carga."""
    from narrative_assistant.temporal.entity_mentions import load_entity_mentions_by_chapter

    chapters = [SimpleNamespace(id=10, chapter_number=1, start_char=0)]
    entities = [
        Entity(id=1, project_id=1, entity_type=EntityType.LOCATION, canonical_name="Madrid"),
    ]

    class MockEntityRepo:
        def get_mentions_by_entity(self, entity_id):
            return [SimpleNamespace(chapter_id=10, start_char=5, end_char=11)]

    result = load_entity_mentions_by_chapter(entities, chapters, MockEntityRepo())
    assert len(result) == 0
