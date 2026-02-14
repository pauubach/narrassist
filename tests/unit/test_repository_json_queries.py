"""
Tests para consultas JSON exactas en repositorios (SQLite JSON1 + fallback).
"""

import json

from narrative_assistant.entities.models import Entity, EntityImportance, EntityType
from narrative_assistant.entities.repository import EntityRepository
from narrative_assistant.persistence.glossary import GlossaryEntry, GlossaryRepository
from narrative_assistant.scenes.repository import SceneRepository


def _create_project(db, name: str = "test-project") -> int:
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, document_path, document_fingerprint, document_format)
            VALUES (?, ?, ?, ?)
            """,
            (name, "/tmp/test.docx", f"{name}-fp", "docx"),
        )
        return cursor.lastrowid


def _create_chapter(db, project_id: int, chapter_number: int = 1) -> int:
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, chapter_number, "Capitulo", "Texto de prueba", 0, 100),
        )
        return cursor.lastrowid


def _create_scene(db, project_id: int, chapter_id: int, scene_number: int) -> int:
    with db.connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scenes (project_id, chapter_id, scene_number, start_char, end_char)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, chapter_id, scene_number, 0, 50),
        )
        return cursor.lastrowid


def test_get_scenes_with_participant_matches_exact_id(isolated_database):
    db = isolated_database
    repo = SceneRepository(db)

    project_id = _create_project(db, "scene-json")
    chapter_id = _create_chapter(db, project_id)

    scene_match = _create_scene(db, project_id, chapter_id, 1)
    scene_other = _create_scene(db, project_id, chapter_id, 2)

    with db.connection() as conn:
        conn.execute(
            "INSERT INTO scene_tags (scene_id, participant_ids) VALUES (?, ?)",
            (scene_match, json.dumps([2, 20])),
        )
        conn.execute(
            "INSERT INTO scene_tags (scene_id, participant_ids) VALUES (?, ?)",
            (scene_other, json.dumps([20])),
        )

    results = repo.get_scenes_with_participant(project_id, 2)
    result_ids = [scene.id for scene in results]

    assert result_ids == [scene_match]


def test_glossary_find_by_variant_is_case_insensitive(isolated_database):
    db = isolated_database
    repo = GlossaryRepository(db)
    project_id = _create_project(db, "glossary-json")

    created = repo.create(
        GlossaryEntry(
            project_id=project_id,
            term="Casa Stark",
            definition="Linaje noble del Norte",
            variants=["Winterfell", "Invernalia"],
        )
    )

    found = repo.find_by_term_or_variant(project_id, "winterfell")

    assert found is not None
    assert found.id == created.id


def test_glossary_find_by_variant_does_not_match_partial(isolated_database):
    db = isolated_database
    repo = GlossaryRepository(db)
    project_id = _create_project(db, "glossary-partial")

    repo.create(
        GlossaryEntry(
            project_id=project_id,
            term="Casa Stark",
            definition="Linaje noble del Norte",
            variants=["Stark"],
        )
    )

    assert repo.find_by_term_or_variant(project_id, "star") is None


def test_find_entities_by_name_fuzzy_uses_aliases_not_merged_ids(isolated_database):
    db = isolated_database
    repo = EntityRepository(db)
    project_id = _create_project(db, "entity-json")

    repo.create_entity(
        Entity(
            project_id=project_id,
            entity_type=EntityType.CHARACTER,
            canonical_name="Arya",
            aliases=["No One", "Lobita"],
            importance=EntityImportance.HIGH,
        )
    )
    repo.create_entity(
        Entity(
            project_id=project_id,
            entity_type=EntityType.CHARACTER,
            canonical_name="Bran",
            merged_from_ids=[12],
            importance=EntityImportance.MEDIUM,
        )
    )

    alias_hits = repo.find_entities_by_name(project_id, "lob", fuzzy=True)
    numeric_hits = repo.find_entities_by_name(project_id, "2", fuzzy=True)

    assert [e.canonical_name for e in alias_hits] == ["Arya"]
    assert numeric_hits == []
