import json
import sys
from pathlib import Path

from narrative_assistant.entities.models import EntityImportance, EntityType
from narrative_assistant.persistence.analysis_cache import AnalysisCache
from narrative_assistant.persistence.database import get_database
from narrative_assistant.persistence.project import ProjectManager

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import (  # noqa: E402
    _restore_chapter_mentions_from_cache,
    _restore_entities_from_cache,
    _serialize_chapter_mentions_for_cache,
    _serialize_entities_for_cache,
)


class _DummyMention:
    def __init__(
        self,
        surface_form: str,
        start_char: int,
        end_char: int,
        chapter_id: int | None = None,
        confidence: float = 0.9,
        source: str = "ner",
    ):
        self.surface_form = surface_form
        self.start_char = start_char
        self.end_char = end_char
        self.chapter_id = chapter_id
        self.confidence = confidence
        self.source = source


class _DummyEntity:
    def __init__(self, entity_id: int, canonical_name: str):
        self.id = entity_id
        self.canonical_name = canonical_name
        self.entity_type = EntityType.CHARACTER
        self.aliases = []
        self.importance = EntityImportance.MEDIUM
        self.first_appearance_char = 0
        self.mention_count = 1


def test_serialize_entities_for_cache_reads_mentions_with_repository_api():
    class _Repo:
        def get_mentions_by_entity(self, entity_id: int):
            assert entity_id == 1
            return [_DummyMention("Maria", 10, 15, chapter_id=2)]

    payload = _serialize_entities_for_cache([_DummyEntity(1, "Maria")], _Repo())
    data = json.loads(payload)

    assert len(data) == 1
    assert data[0]["canonical_name"] == "Maria"
    assert len(data[0]["mentions"]) == 1
    assert data[0]["mentions"][0]["chapter_id"] == 2


def test_restore_entities_from_cache_remaps_chapter_id(monkeypatch):
    from narrative_assistant.entities import repository as entity_repo_module

    class _FakeRepo:
        def __init__(self):
            self.created_mentions = []

        def create_entity(self, entity):
            return 101

        def create_mentions_batch(self, mentions):
            self.created_mentions.extend(mentions)
            return len(mentions)

    fake_repo = _FakeRepo()
    monkeypatch.setattr(
        entity_repo_module,
        "get_entity_repository",
        lambda: fake_repo,
    )

    entities_json = json.dumps(
        [
            {
                "id": 1,
                "canonical_name": "Maria",
                "entity_type": EntityType.CHARACTER.value,
                "aliases": [],
                "importance": EntityImportance.MEDIUM.value,
                "first_appearance_char": 0,
                "mention_count": 1,
                "mentions": [
                    {
                        "surface_form": "Maria",
                        "start_char": 120,
                        "end_char": 125,
                        "chapter_id": 999,  # stale chapter_id from previous run
                        "confidence": 0.95,
                        "source": "ner",
                    }
                ],
            }
        ]
    )

    restored = _restore_entities_from_cache(
        entities_json=entities_json,
        project_id=1,
        find_chapter_id_for_position=lambda start_char: 7 if start_char == 120 else None,
    )

    assert len(restored) == 1
    assert len(fake_repo.created_mentions) == 1
    assert fake_repo.created_mentions[0].chapter_id == 7


def test_project_update_persists_document_fingerprint():
    manager = ProjectManager()
    create_result = manager.create_from_document(
        text="Texto inicial de prueba",
        name="Proyecto Cache Fingerprint",
        document_format="txt",
        check_existing=False,
    )
    assert create_result.is_success
    project = create_result.value
    assert project is not None

    new_fingerprint = "f" * 64
    project.document_fingerprint = new_fingerprint

    update_result = manager.update(project)
    assert update_result.is_success

    fetched_result = manager.get(project.id)
    assert fetched_result.is_success
    fetched = fetched_result.value
    assert fetched is not None
    assert fetched.document_fingerprint == new_fingerprint


def test_ner_chapter_cache_roundtrip():
    cache = AnalysisCache(get_database())
    manager = ProjectManager()
    create_result = manager.create_from_document(
        text="Texto de prueba para cache por capítulo",
        name="Proyecto NER Chapter Cache",
        document_format="txt",
        check_existing=False,
    )
    assert create_result.is_success
    project_id = create_result.value.id
    chapter_hash = "a" * 64
    config_hash = "default"
    mentions_json = '[{"text":"Maria","label":"PER","start_char":0,"end_char":5}]'

    cache.set_ner_chapter_results(
        project_id=project_id,
        chapter_hash=chapter_hash,
        config_hash=config_hash,
        mentions_json=mentions_json,
        mention_count=1,
        processed_chars=120,
    )

    cached = cache.get_ner_chapter_results(project_id, chapter_hash, config_hash)

    assert cached is not None
    assert cached["mentions_json"] == mentions_json
    assert cached["mention_count"] == 1
    assert cached["processed_chars"] == 120


def test_chapter_mentions_cache_serialization_rebases_offsets():
    from narrative_assistant.nlp.ner import EntityLabel, ExtractedEntity

    mentions = [
        ExtractedEntity(
            text="María",
            label=EntityLabel.PER,
            start_char=110,
            end_char=115,
            confidence=0.92,
            source="ner",
        )
    ]

    serialized = _serialize_chapter_mentions_for_cache(mentions, chapter_start=100)
    restored = _restore_chapter_mentions_from_cache(serialized, chapter_start=400)

    assert len(restored) == 1
    assert restored[0].text == "María"
    assert restored[0].label == EntityLabel.PER
    assert restored[0].start_char == 410
    assert restored[0].end_char == 415
