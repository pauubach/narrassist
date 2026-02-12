"""
Tests para BK-09: migración de FK al fusionar entidades.

Verifica que move_related_data() migra correctamente las 14 columnas FK
en 10 tablas cuando se fusionan entidades.
"""

import json

import pytest

from narrative_assistant.entities.repository import EntityRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_project_and_entities(db):
    """Crea un proyecto y dos entidades de prueba. Devuelve (project_id, eid_from, eid_to)."""
    with db.connection() as conn:
        c = conn.execute(
            "INSERT INTO projects (name, document_path, document_fingerprint, document_format) "
            "VALUES ('test', '/tmp/t.docx', 'abc123', 'docx')"
        )
        pid = c.lastrowid
        c = conn.execute(
            "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
            "VALUES (?, 'CHARACTER', 'Source', 'MAIN', 0, 1)",
            (pid,),
        )
        eid_from = c.lastrowid
        c = conn.execute(
            "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
            "VALUES (?, 'CHARACTER', 'Target', 'MAIN', 0, 1)",
            (pid,),
        )
        eid_to = c.lastrowid
    return pid, eid_from, eid_to


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMoveRelatedData:
    """Suite de tests para EntityRepository.move_related_data()."""

    def test_merge_moves_temporal_markers(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO temporal_markers (project_id, chapter, marker_type, text, start_char, end_char, entity_id) "
                "VALUES (?, 1, 'ABSOLUTE_DATE', '1920', 0, 4, ?)",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["temporal_markers"] == 1
        row = db.fetchone(
            "SELECT entity_id FROM temporal_markers WHERE project_id = ?", (pid,)
        )
        assert row["entity_id"] == eid_to

    def test_merge_moves_voice_profiles(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO voice_profiles (project_id, entity_id, avg_sentence_length, formality_score) "
                "VALUES (?, ?, 12.5, 0.7)",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["voice_profiles"] == 1
        row = db.fetchone(
            "SELECT entity_id FROM voice_profiles WHERE project_id = ?", (pid,)
        )
        assert row["entity_id"] == eid_to

    def test_merge_voice_profile_dedup(self, isolated_database):
        """Si ambas entidades tienen perfil, se elimina el del origen."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO voice_profiles (project_id, entity_id, avg_sentence_length) VALUES (?, ?, 10.0)",
                (pid, eid_from),
            )
            conn.execute(
                "INSERT INTO voice_profiles (project_id, entity_id, avg_sentence_length) VALUES (?, ?, 15.0)",
                (pid, eid_to),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["voice_profiles"] == 1  # deleted 1
        rows = db.fetchall(
            "SELECT entity_id, avg_sentence_length FROM voice_profiles WHERE project_id = ?",
            (pid,),
        )
        assert len(rows) == 1
        assert rows[0]["entity_id"] == eid_to
        assert rows[0]["avg_sentence_length"] == 15.0  # se quedó el del target

    def test_merge_moves_vital_status_events(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO vital_status_events (project_id, entity_id, entity_name, event_type, chapter, confidence) "
                "VALUES (?, ?, 'Source', 'death', 3, 0.9)",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["vital_status_events"] == 1
        row = db.fetchone(
            "SELECT entity_id FROM vital_status_events WHERE project_id = ?", (pid,)
        )
        assert row["entity_id"] == eid_to

    def test_merge_moves_character_location_events(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO character_location_events (project_id, entity_id, entity_name, location_name, chapter, change_type) "
                "VALUES (?, ?, 'Source', 'Casa', 1, 'arrival')",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["character_location_events"] == 1
        row = db.fetchone(
            "SELECT entity_id FROM character_location_events WHERE project_id = ?",
            (pid,),
        )
        assert row["entity_id"] == eid_to

    def test_merge_moves_ooc_events(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO ooc_events (project_id, entity_id, entity_name, deviation_type, severity) "
                "VALUES (?, ?, 'Source', 'register', 'high')",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["ooc_events"] == 1
        row = db.fetchone(
            "SELECT entity_id FROM ooc_events WHERE project_id = ?", (pid,)
        )
        assert row["entity_id"] == eid_to

    def test_merge_moves_relationships_entity1(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        # Tercera entidad para el otro lado de la relación
        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
                "VALUES (?, 'CHARACTER', 'Third', 'SECONDARY', 0, 1)",
                (pid,),
            )
            eid_third = c.lastrowid
            conn.execute(
                "INSERT INTO relationships (project_id, entity1_id, entity2_id, relation_type) "
                "VALUES (?, ?, ?, 'FRIENDSHIP')",
                (pid, eid_from, eid_third),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["relationships"] >= 1
        row = db.fetchone(
            "SELECT entity1_id FROM relationships WHERE project_id = ?", (pid,)
        )
        assert row["entity1_id"] == eid_to

    def test_merge_moves_relationships_entity2(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
                "VALUES (?, 'CHARACTER', 'Third', 'SECONDARY', 0, 1)",
                (pid,),
            )
            eid_third = c.lastrowid
            conn.execute(
                "INSERT INTO relationships (project_id, entity1_id, entity2_id, relation_type) "
                "VALUES (?, ?, ?, 'RIVALRY')",
                (pid, eid_third, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["relationships"] >= 1
        row = db.fetchone(
            "SELECT entity2_id FROM relationships WHERE project_id = ?", (pid,)
        )
        assert row["entity2_id"] == eid_to

    def test_merge_removes_self_relationships(self, isolated_database):
        """Relación from↔to se convierte en to↔to y se elimina."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO relationships (project_id, entity1_id, entity2_id, relation_type) "
                "VALUES (?, ?, ?, 'FAMILY')",
                (pid, eid_from, eid_to),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["relationships_self_deleted"] >= 1
        rows = db.fetchall("SELECT * FROM relationships WHERE project_id = ?", (pid,))
        assert len(rows) == 0

    def test_merge_moves_interactions(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
                "VALUES (?, 'CHARACTER', 'Third', 'SECONDARY', 0, 1)",
                (pid,),
            )
            eid_third = c.lastrowid
            # entity1 = from, entity2 = third
            conn.execute(
                "INSERT INTO interactions (project_id, entity1_id, entity2_id, interaction_type) "
                "VALUES (?, ?, ?, 'DIALOGUE')",
                (pid, eid_from, eid_third),
            )
            # entity1 = third, entity2 = from
            conn.execute(
                "INSERT INTO interactions (project_id, entity1_id, entity2_id, interaction_type) "
                "VALUES (?, ?, ?, 'OBSERVATION')",
                (pid, eid_third, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["interactions"] == 2
        rows = db.fetchall(
            "SELECT entity1_id, entity2_id FROM interactions WHERE project_id = ?",
            (pid,),
        )
        ids = {r["entity1_id"] for r in rows} | {
            r["entity2_id"] for r in rows if r["entity2_id"]
        }
        assert eid_from not in ids
        assert eid_to in ids

    def test_merge_moves_coreference_corrections(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO coreference_corrections "
                "(project_id, mention_start_char, mention_end_char, mention_text, original_entity_id, corrected_entity_id) "
                "VALUES (?, 0, 5, 'él', ?, NULL)",
                (pid, eid_from),
            )
            conn.execute(
                "INSERT INTO coreference_corrections "
                "(project_id, mention_start_char, mention_end_char, mention_text, original_entity_id, corrected_entity_id) "
                "VALUES (?, 10, 15, 'ella', NULL, ?)",
                (pid, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["coreference_corrections"] == 2
        rows = db.fetchall(
            "SELECT original_entity_id, corrected_entity_id FROM coreference_corrections WHERE project_id = ?",
            (pid,),
        )
        for row in rows:
            if row["original_entity_id"] is not None:
                assert row["original_entity_id"] == eid_to
            if row["corrected_entity_id"] is not None:
                assert row["corrected_entity_id"] == eid_to

    def test_merge_moves_speaker_corrections(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO speaker_corrections "
                "(project_id, chapter_number, dialogue_start_char, dialogue_end_char, dialogue_text, "
                "original_speaker_id, corrected_speaker_id) "
                "VALUES (?, 1, 0, 20, 'Hola', ?, ?)",
                (pid, eid_from, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["speaker_corrections"] == 2  # both columns updated
        row = db.fetchone(
            "SELECT original_speaker_id, corrected_speaker_id FROM speaker_corrections WHERE project_id = ?",
            (pid,),
        )
        assert row["original_speaker_id"] == eid_to
        assert row["corrected_speaker_id"] == eid_to

    def test_merge_moves_collection_entity_links(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute("INSERT INTO collections (name) VALUES ('saga')")
            coll_id = c.lastrowid
            # Tercera entidad en otro proyecto para target
            c = conn.execute(
                "INSERT INTO projects (name, document_path, document_fingerprint, document_format) "
                "VALUES ('test2', '/tmp/t2.docx', 'def456', 'docx')"
            )
            pid2 = c.lastrowid
            c = conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
                "VALUES (?, 'CHARACTER', 'Other', 'MAIN', 0, 1)",
                (pid2,),
            )
            eid_other = c.lastrowid
            conn.execute(
                "INSERT INTO collection_entity_links (collection_id, source_entity_id, target_entity_id, source_project_id, target_project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (coll_id, eid_from, eid_other, pid, pid2),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        row = db.fetchone(
            "SELECT source_entity_id FROM collection_entity_links WHERE collection_id = ?",
            (coll_id,),
        )
        assert row["source_entity_id"] == eid_to

    def test_merge_collection_links_dedup(self, isolated_database):
        """Si ya existe un link con el target, el duplicado se elimina."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute("INSERT INTO collections (name) VALUES ('saga')")
            coll_id = c.lastrowid
            c = conn.execute(
                "INSERT INTO projects (name, document_path, document_fingerprint, document_format) "
                "VALUES ('p2', '/tmp/p2.docx', 'ghi789', 'docx')"
            )
            pid2 = c.lastrowid
            c = conn.execute(
                "INSERT INTO entities (project_id, entity_type, canonical_name, importance, mention_count, is_active) "
                "VALUES (?, 'CHARACTER', 'Other', 'MAIN', 0, 1)",
                (pid2,),
            )
            eid_other = c.lastrowid
            # Link desde from → other
            conn.execute(
                "INSERT INTO collection_entity_links (collection_id, source_entity_id, target_entity_id, source_project_id, target_project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (coll_id, eid_from, eid_other, pid, pid2),
            )
            # Link desde to → other (ya existe)
            conn.execute(
                "INSERT INTO collection_entity_links (collection_id, source_entity_id, target_entity_id, source_project_id, target_project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (coll_id, eid_to, eid_other, pid, pid2),
            )

        repo.move_related_data(eid_from, eid_to)

        rows = db.fetchall(
            "SELECT * FROM collection_entity_links WHERE collection_id = ?", (coll_id,)
        )
        assert len(rows) == 1
        assert rows[0]["source_entity_id"] == eid_to

    def test_merge_updates_scene_participant_ids(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            # Necesitamos un scene_id válido → crear escena
            c = conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char) "
                "VALUES (?, 1, 'Cap 1', 'texto', 0, 100)",
                (pid,),
            )
            chap_id = c.lastrowid
            c = conn.execute(
                "INSERT INTO scenes (project_id, chapter_id, scene_number, start_char, end_char) "
                "VALUES (?, ?, 1, 0, 50)",
                (pid, chap_id),
            )
            scene_id = c.lastrowid
            conn.execute(
                "INSERT INTO scene_tags (scene_id, participant_ids) VALUES (?, ?)",
                (scene_id, json.dumps([eid_from, 999])),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["scene_tags_participants"] == 1
        row = db.fetchone(
            "SELECT participant_ids FROM scene_tags WHERE scene_id = ?", (scene_id,)
        )
        ids = json.loads(row["participant_ids"])
        assert eid_to in ids
        assert eid_from not in ids

    def test_merge_updates_scene_location_entity_id(self, isolated_database):
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char) "
                "VALUES (?, 1, 'Cap 1', 'texto', 0, 100)",
                (pid,),
            )
            chap_id = c.lastrowid
            c = conn.execute(
                "INSERT INTO scenes (project_id, chapter_id, scene_number, start_char, end_char) "
                "VALUES (?, ?, 1, 0, 50)",
                (pid, chap_id),
            )
            scene_id = c.lastrowid
            conn.execute(
                "INSERT INTO scene_tags (scene_id, location_entity_id) VALUES (?, ?)",
                (scene_id, eid_from),
            )

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["scene_tags_location"] == 1
        row = db.fetchone(
            "SELECT location_entity_id FROM scene_tags WHERE scene_id = ?", (scene_id,)
        )
        assert row["location_entity_id"] == eid_to

    def test_scene_participants_no_partial_match(self, isolated_database):
        """ID=2 no debe matchear dentro de ID=20 o ID=12."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char) "
                "VALUES (?, 1, 'Cap 1', 'texto', 0, 100)",
                (pid,),
            )
            chap_id = c.lastrowid
            c = conn.execute(
                "INSERT INTO scenes (project_id, chapter_id, scene_number, start_char, end_char) "
                "VALUES (?, ?, 1, 0, 50)",
                (pid, chap_id),
            )
            scene_id = c.lastrowid
            # eid_from aparece solo como elemento, junto a IDs que lo contienen como substring
            other_id = eid_from * 10  # e.g. 20 si from=2
            conn.execute(
                "INSERT INTO scene_tags (scene_id, participant_ids) VALUES (?, ?)",
                (scene_id, json.dumps([eid_from, other_id])),
            )

        repo.move_related_data(eid_from, eid_to)

        row = db.fetchone(
            "SELECT participant_ids FROM scene_tags WHERE scene_id = ?", (scene_id,)
        )
        ids = json.loads(row["participant_ids"])
        assert eid_to in ids
        assert eid_from not in ids
        # other_id no debe haberse modificado
        assert other_id in ids

    def test_move_related_data_noop_when_empty(self, isolated_database):
        """Si no hay datos relacionados, todos los conteos son 0."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        counts = repo.move_related_data(eid_from, eid_to)

        assert counts["temporal_markers"] == 0
        assert counts["voice_profiles"] == 0
        assert counts["vital_status_events"] == 0
        assert counts["character_location_events"] == 0
        assert counts["ooc_events"] == 0
        assert counts["relationships"] == 0
        assert counts["interactions"] == 0
        assert counts["coreference_corrections"] == 0
        assert counts["speaker_corrections"] == 0

    def test_scene_participants_dedup_after_merge(self, isolated_database):
        """Si ambas entidades están en la misma escena, el resultado no tiene duplicados."""
        db = isolated_database
        pid, eid_from, eid_to = _setup_project_and_entities(db)
        repo = EntityRepository(db)

        with db.connection() as conn:
            c = conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, start_char, end_char) "
                "VALUES (?, 1, 'Cap 1', 'texto', 0, 100)",
                (pid,),
            )
            chap_id = c.lastrowid
            c = conn.execute(
                "INSERT INTO scenes (project_id, chapter_id, scene_number, start_char, end_char) "
                "VALUES (?, ?, 1, 0, 50)",
                (pid, chap_id),
            )
            scene_id = c.lastrowid
            # Ambas entidades presentes en la misma escena
            conn.execute(
                "INSERT INTO scene_tags (scene_id, participant_ids) VALUES (?, ?)",
                (scene_id, json.dumps([eid_from, eid_to, 999])),
            )

        repo.move_related_data(eid_from, eid_to)

        row = db.fetchone(
            "SELECT participant_ids FROM scene_tags WHERE scene_id = ?", (scene_id,)
        )
        ids = json.loads(row["participant_ids"])
        assert ids.count(eid_to) == 1  # sin duplicados
        assert eid_from not in ids
        assert 999 in ids
