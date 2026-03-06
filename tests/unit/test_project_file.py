"""Tests para exportación/importación de archivos .nra."""

from __future__ import annotations

import json
import sqlite3

import pytest

from narrative_assistant.persistence.database import SCHEMA_VERSION, Database
from narrative_assistant.persistence.project_file import (
    NRA_FORMAT_VERSION,
    NraExporter,
    NraImporter,
    _remap_json_ids,
)


@pytest.fixture()
def db():
    """DB en memoria con schema completo."""
    return Database(":memory:")


@pytest.fixture()
def populated_db(db):
    """DB con un proyecto y datos de ejemplo."""
    with db.connection() as conn:
        # Proyecto
        conn.execute(
            "INSERT INTO projects (id, name, document_fingerprint, document_format, "
            "document_path, word_count, analysis_status) "
            "VALUES (1, 'Mi Novela', 'fp123', 'DOCX', '/tmp/novela.docx', 5000, 'completed')"
        )

        # Capítulos
        conn.execute(
            "INSERT INTO chapters (id, project_id, chapter_number, title, content, "
            "start_char, end_char, word_count) "
            "VALUES (10, 1, 1, 'Cap 1', 'Texto del capítulo uno.', 0, 100, 50)"
        )
        conn.execute(
            "INSERT INTO chapters (id, project_id, chapter_number, title, content, "
            "start_char, end_char, word_count) "
            "VALUES (11, 1, 2, 'Cap 2', 'Texto del capítulo dos.', 101, 200, 50)"
        )

        # Entidades
        conn.execute(
            "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
            "importance, mention_count) "
            "VALUES (20, 1, 'character', 'María', 'protagonist', 15)"
        )
        conn.execute(
            "INSERT INTO entities (id, project_id, entity_type, canonical_name, "
            "importance, mention_count, merged_from_ids) "
            "VALUES (21, 1, 'character', 'Pedro', 'secondary', 8, '[20]')"
        )

        # Menciones de entidades (FK a entities, sin project_id)
        conn.execute(
            "INSERT INTO entity_mentions (id, entity_id, chapter_id, surface_form, "
            "start_char, end_char, confidence) "
            "VALUES (30, 20, 10, 'María', 5, 10, 0.95)"
        )
        conn.execute(
            "INSERT INTO entity_mentions (id, entity_id, chapter_id, surface_form, "
            "start_char, end_char, confidence) "
            "VALUES (31, 21, 11, 'Pedro', 110, 115, 0.9)"
        )

        # Atributos de entidad (FK a entities, sin project_id)
        conn.execute(
            "INSERT INTO entity_attributes (id, entity_id, attribute_type, "
            "attribute_key, attribute_value, chapter_id, confidence) "
            "VALUES (40, 20, 'physical', 'hair_color', 'negro', 10, 0.85)"
        )

        # Evidencias (FK a entity_attributes, sin project_id)
        conn.execute(
            "INSERT INTO attribute_evidences (id, attribute_id, start_char, end_char, "
            "chapter, excerpt, extraction_method, confidence) "
            "VALUES (50, 40, 15, 30, 1, 'cabello negro', 'direct_description', 0.9)"
        )

        # Alertas con entity_ids JSON
        conn.execute(
            "INSERT INTO alerts (id, project_id, category, severity, alert_type, "
            "title, description, explanation, entity_ids, confidence) "
            "VALUES (60, 1, 'consistency', 'warning', 'attribute_inconsistency', "
            "'Inconsistencia', 'Desc', 'Expl', '[20, 21]', 0.8)"
        )

        # Relaciones
        conn.execute(
            "INSERT INTO relationships (id, project_id, entity1_id, entity2_id, "
            "relation_type, confidence) "
            "VALUES (70, 1, 20, 21, 'FRIENDSHIP', 0.7)"
        )

        # Sesión
        conn.execute(
            "INSERT INTO sessions (id, project_id, started_at) "
            "VALUES (80, 1, '2026-01-01')"
        )

        # Analysis run
        conn.execute(
            "INSERT INTO analysis_runs (id, project_id, session_id, started_at, status) "
            "VALUES (90, 1, 80, '2026-01-01', 'completed')"
        )

        # Analysis phase (FK a run, sin project_id)
        conn.execute(
            "INSERT INTO analysis_phases (id, run_id, phase_name, executed) "
            "VALUES (100, 90, 'parsing', 1)"
        )

        conn.commit()

    return db


@pytest.fixture()
def nra_path(tmp_path):
    """Ruta temporal para archivo .nra."""
    return tmp_path / "test_project.nra"


class TestExportImportRoundtrip:
    """Test completo de export → import."""

    def test_roundtrip_preserves_project_data(self, populated_db, nra_path):
        """Export + import preserva nombre, status, word_count."""
        exporter = NraExporter(populated_db)
        result = exporter.export_project(1, nra_path)
        assert result.is_success, f"Export failed: {result.error}"
        assert nra_path.exists()

        # Importar en la misma DB (simula otro PC)
        importer = NraImporter(populated_db)
        import_result = importer.import_project(nra_path)
        assert import_result.is_success, f"Import failed: {import_result.error}"

        new_id = import_result.value
        assert new_id != 1  # Debe tener nuevo ID

        row = populated_db.fetchone("SELECT * FROM projects WHERE id = ?", (new_id,))
        assert row["name"] == "Mi Novela (importado)"  # Renombrado por duplicado
        assert row["analysis_status"] == "completed"
        assert row["word_count"] == 5000
        assert row["document_path"] is None  # Limpiado

    def test_roundtrip_preserves_chapters(self, populated_db, nra_path):
        """Export + import preserva capítulos con contenido."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        chapters = populated_db.fetchall(
            "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
            (new_id,),
        )
        assert len(chapters) == 2
        assert chapters[0]["title"] == "Cap 1"
        assert chapters[0]["content"] == "Texto del capítulo uno."
        assert chapters[1]["title"] == "Cap 2"

    def test_roundtrip_preserves_entities_and_mentions(self, populated_db, nra_path):
        """Export + import preserva entidades y sus menciones."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        entities = populated_db.fetchall(
            "SELECT * FROM entities WHERE project_id = ? ORDER BY canonical_name",
            (new_id,),
        )
        assert len(entities) == 2
        maria = next(e for e in entities if e["canonical_name"] == "María")
        pedro = next(e for e in entities if e["canonical_name"] == "Pedro")
        assert maria["importance"] == "protagonist"
        assert pedro["mention_count"] == 8

        # Menciones deben apuntar a los nuevos entity IDs
        mentions = populated_db.fetchall(
            "SELECT em.* FROM entity_mentions em "
            "JOIN entities e ON em.entity_id = e.id "
            "WHERE e.project_id = ?",
            (new_id,),
        )
        assert len(mentions) == 2
        assert all(m["entity_id"] in (maria["id"], pedro["id"]) for m in mentions)

    def test_roundtrip_preserves_attributes_and_evidences(self, populated_db, nra_path):
        """Export + import preserva atributos y evidencias."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        maria = populated_db.fetchone(
            "SELECT id FROM entities WHERE project_id = ? AND canonical_name = 'María'",
            (new_id,),
        )
        attrs = populated_db.fetchall(
            "SELECT * FROM entity_attributes WHERE entity_id = ?", (maria["id"],)
        )
        assert len(attrs) == 1
        assert attrs[0]["attribute_value"] == "negro"

        evidences = populated_db.fetchall(
            "SELECT * FROM attribute_evidences WHERE attribute_id = ?",
            (attrs[0]["id"],),
        )
        assert len(evidences) == 1
        assert evidences[0]["excerpt"] == "cabello negro"

    def test_roundtrip_preserves_alerts_with_remapped_entity_ids(self, populated_db, nra_path):
        """Export + import remapea entity_ids dentro de alertas."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        alerts = populated_db.fetchall(
            "SELECT * FROM alerts WHERE project_id = ?", (new_id,)
        )
        assert len(alerts) == 1

        entity_ids = json.loads(alerts[0]["entity_ids"])
        # Deben ser los nuevos IDs, no los originales (20, 21)
        entities = populated_db.fetchall(
            "SELECT id FROM entities WHERE project_id = ?", (new_id,)
        )
        new_entity_ids = {e["id"] for e in entities}
        assert set(entity_ids) == new_entity_ids

    def test_roundtrip_preserves_relationships(self, populated_db, nra_path):
        """Export + import preserva relaciones con FKs remapeadas."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        rels = populated_db.fetchall(
            "SELECT * FROM relationships WHERE project_id = ?", (new_id,)
        )
        assert len(rels) == 1
        assert rels[0]["relation_type"] == "FRIENDSHIP"

        # Los entity IDs deben ser los nuevos
        entities = populated_db.fetchall(
            "SELECT id FROM entities WHERE project_id = ?", (new_id,)
        )
        entity_ids = {e["id"] for e in entities}
        assert rels[0]["entity1_id"] in entity_ids
        assert rels[0]["entity2_id"] in entity_ids

    def test_roundtrip_preserves_analysis_runs_and_phases(self, populated_db, nra_path):
        """Export + import preserva runs y phases."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        runs = populated_db.fetchall(
            "SELECT * FROM analysis_runs WHERE project_id = ?", (new_id,)
        )
        assert len(runs) == 1
        assert runs[0]["status"] == "completed"

        phases = populated_db.fetchall(
            "SELECT * FROM analysis_phases WHERE run_id = ?", (runs[0]["id"],)
        )
        assert len(phases) == 1
        assert phases[0]["phase_name"] == "parsing"


class TestExportValidation:
    """Tests de validación de exportación."""

    def test_export_nonexistent_project_fails(self, db, nra_path):
        exporter = NraExporter(db)
        result = exporter.export_project(999, nra_path)
        assert result.is_failure

    def test_export_creates_valid_sqlite(self, populated_db, nra_path):
        NraExporter(populated_db).export_project(1, nra_path)

        conn = sqlite3.connect(str(nra_path))
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        assert integrity[0] == "ok"
        conn.close()

    def test_export_includes_nra_metadata(self, populated_db, nra_path):
        NraExporter(populated_db).export_project(1, nra_path)

        conn = sqlite3.connect(str(nra_path))
        conn.row_factory = sqlite3.Row
        meta = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT * FROM nra_metadata").fetchall()
        }
        conn.close()

        assert meta["nra_format_version"] == str(NRA_FORMAT_VERSION)
        assert int(meta["schema_version"]) == SCHEMA_VERSION
        assert meta["original_project_name"] == "Mi Novela"
        assert "export_date" in meta

    def test_export_empty_project(self, db, nra_path):
        """Proyecto sin datos de análisis se exporta correctamente."""
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO projects (id, name, document_fingerprint, document_format) "
                "VALUES (1, 'Vacío', 'fp0', 'TXT')"
            )
        result = NraExporter(db).export_project(1, nra_path)
        assert result.is_success


class TestImportValidation:
    """Tests de validación de importación."""

    def test_import_nonexistent_file_fails(self, db, tmp_path):
        result = NraImporter(db).import_project(tmp_path / "noexiste.nra")
        assert result.is_failure

    def test_import_non_sqlite_file_fails(self, db, tmp_path):
        bad_file = tmp_path / "fake.nra"
        bad_file.write_text("esto no es sqlite")
        result = NraImporter(db).import_project(bad_file)
        assert result.is_failure

    def test_import_sqlite_without_metadata_fails(self, db, tmp_path):
        bare_db = tmp_path / "bare.nra"
        conn = sqlite3.connect(str(bare_db))
        conn.execute("CREATE TABLE foo (id INTEGER)")
        conn.commit()
        conn.close()

        result = NraImporter(db).import_project(bare_db)
        assert result.is_failure

    def test_import_newer_schema_fails(self, populated_db, nra_path):
        NraExporter(populated_db).export_project(1, nra_path)

        # Hackear schema_version en el .nra
        conn = sqlite3.connect(str(nra_path))
        conn.execute(
            "UPDATE nra_metadata SET value = '999' WHERE key = 'schema_version'"
        )
        conn.commit()
        conn.close()

        result = NraImporter(populated_db).import_project(nra_path)
        assert result.is_failure


class TestJsonRemapping:
    """Tests para remapeo de IDs en JSON."""

    def test_remap_json_ids_basic(self):
        id_map = {1: 100, 2: 200, 3: 300}
        assert _remap_json_ids("[1, 2, 3]", id_map) == "[100, 200, 300]"

    def test_remap_json_ids_empty(self):
        assert _remap_json_ids("[]", {1: 100}) == "[]"
        assert _remap_json_ids(None, {1: 100}) is None
        assert _remap_json_ids("", {1: 100}) == ""

    def test_remap_json_ids_unknown_keeps_original(self):
        id_map = {1: 100}
        result = json.loads(_remap_json_ids("[1, 999]", id_map))
        assert result == [100, 999]

    def test_remap_json_ids_invalid_json(self):
        assert _remap_json_ids("not json", {1: 100}) == "not json"


class TestMergedFromIds:
    """Test que merged_from_ids se remapea correctamente."""

    def test_merged_from_ids_remapped(self, populated_db, nra_path):
        """Pedro tiene merged_from_ids=[20] (María). Tras import, debe remapear."""
        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        pedro = populated_db.fetchone(
            "SELECT * FROM entities WHERE project_id = ? AND canonical_name = 'Pedro'",
            (new_id,),
        )
        maria = populated_db.fetchone(
            "SELECT * FROM entities WHERE project_id = ? AND canonical_name = 'María'",
            (new_id,),
        )

        merged = json.loads(pedro["merged_from_ids"])
        assert merged == [maria["id"]]


class TestCoreferenceCorrections:
    """Regression: coreference_corrections remap original/corrected entity IDs."""

    def test_coreference_corrections_entity_ids_remapped(self, populated_db, nra_path):
        """original_entity_id y corrected_entity_id deben remapearse a nuevos IDs."""
        with populated_db.connection() as conn:
            conn.execute(
                "INSERT INTO coreference_corrections "
                "(project_id, mention_start_char, mention_end_char, mention_text, "
                "original_entity_id, corrected_entity_id, correction_type) "
                "VALUES (1, 5, 10, 'ella', 20, 21, 'reassign')"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        corrections = populated_db.fetchall(
            "SELECT * FROM coreference_corrections WHERE project_id = ?", (new_id,)
        )
        assert len(corrections) == 1

        entities = populated_db.fetchall(
            "SELECT id, canonical_name FROM entities WHERE project_id = ?", (new_id,)
        )
        entity_map = {e["canonical_name"]: e["id"] for e in entities}

        # original_entity_id (20 → María) y corrected_entity_id (21 → Pedro)
        assert corrections[0]["original_entity_id"] == entity_map["María"]
        assert corrections[0]["corrected_entity_id"] == entity_map["Pedro"]
        assert corrections[0]["mention_text"] == "ella"


class TestSceneTags:
    """Regression: scene_tags remap location_entity_id FK + participant_ids JSON."""

    def test_scene_tags_location_entity_remapped(self, populated_db, nra_path):
        """location_entity_id (FK) y participant_ids (JSON) deben remapearse."""
        with populated_db.connection() as conn:
            # Necesitamos una scene para crear scene_tags
            conn.execute(
                "INSERT INTO scenes (id, project_id, chapter_id, scene_number, "
                "start_char, end_char) VALUES (200, 1, 10, 1, 0, 50)"
            )
            conn.execute(
                "INSERT INTO scene_tags (scene_id, scene_type, tone, "
                "location_entity_id, participant_ids) "
                "VALUES (200, 'action', 'tense', 20, '[20, 21]')"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        entities = populated_db.fetchall(
            "SELECT id, canonical_name FROM entities WHERE project_id = ?", (new_id,)
        )
        entity_map = {e["canonical_name"]: e["id"] for e in entities}
        new_entity_ids = set(entity_map.values())

        # Buscar scene_tags vía scene → project
        scenes = populated_db.fetchall(
            "SELECT id FROM scenes WHERE project_id = ?", (new_id,)
        )
        assert len(scenes) == 1

        tags = populated_db.fetchall(
            "SELECT * FROM scene_tags WHERE scene_id = ?", (scenes[0]["id"],)
        )
        assert len(tags) == 1

        # FK directa
        assert tags[0]["location_entity_id"] == entity_map["María"]

        # JSON participant_ids
        participant_ids = json.loads(tags[0]["participant_ids"])
        assert set(participant_ids) == new_entity_ids


class TestSnapshotAlerts:
    """Regression: snapshot_alerts entity_ids JSON remapped."""

    def test_snapshot_alerts_entity_ids_remapped(self, populated_db, nra_path):
        """entity_ids en snapshot_alerts deben remapearse a nuevos IDs."""
        with populated_db.connection() as conn:
            conn.execute(
                "INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, "
                "alert_count, entity_count) VALUES (300, 1, 'fp123', 1, 2)"
            )
            conn.execute(
                "INSERT INTO snapshot_alerts (snapshot_id, project_id, alert_type, "
                "category, severity, title, entity_ids) "
                "VALUES (300, 1, 'attr_inconsistency', 'consistency', 'warning', "
                "'Test', '[20, 21]')"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        entities = populated_db.fetchall(
            "SELECT id FROM entities WHERE project_id = ?", (new_id,)
        )
        new_entity_ids = {e["id"] for e in entities}

        snap_alerts = populated_db.fetchall(
            "SELECT * FROM snapshot_alerts WHERE project_id = ?", (new_id,)
        )
        assert len(snap_alerts) == 1

        entity_ids = json.loads(snap_alerts[0]["entity_ids"])
        assert set(entity_ids) == new_entity_ids


class TestInvalidationEvents:
    """Regression: invalidation_events entity_ids JSON remapped."""

    def test_invalidation_events_entity_ids_remapped(self, populated_db, nra_path):
        """entity_ids en invalidation_events deben remapearse a nuevos IDs."""
        with populated_db.connection() as conn:
            conn.execute(
                "INSERT INTO invalidation_events (project_id, event_type, entity_ids, "
                "detail, revision) VALUES (1, 'entity_merge', '[20]', 'merged', 1)"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        maria = populated_db.fetchone(
            "SELECT id FROM entities WHERE project_id = ? AND canonical_name = 'María'",
            (new_id,),
        )

        events = populated_db.fetchall(
            "SELECT * FROM invalidation_events WHERE project_id = ?", (new_id,)
        )
        assert len(events) == 1

        entity_ids = json.loads(events[0]["entity_ids"])
        assert entity_ids == [maria["id"]]


class TestSessions:
    """Regression: sessions remap de last_chapter_id."""

    def test_sessions_last_chapter_id_remapped(self, populated_db, nra_path):
        """last_chapter_id debe apuntar al chapter nuevo tras import."""
        with populated_db.connection() as conn:
            conn.execute(
                "UPDATE sessions SET last_chapter_id = ?, last_position_char = ? WHERE id = ?",
                (10, 123, 80),
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        chapter = populated_db.fetchone(
            "SELECT id FROM chapters WHERE project_id = ? AND chapter_number = 1",
            (new_id,),
        )
        session = populated_db.fetchone(
            "SELECT last_chapter_id, last_position_char FROM sessions WHERE project_id = ?",
            (new_id,),
        )

        assert chapter is not None
        assert session is not None
        assert session["last_chapter_id"] == chapter["id"]
        assert session["last_position_char"] == 123


class TestSnapshotEntityMappings:
    """Regression: remapeo de IDs en snapshot_entities y entity_version_links."""

    def test_snapshot_entities_original_entity_id_remapped(self, populated_db, nra_path):
        """snapshot_entities.original_entity_id debe remapearse a IDs nuevos."""
        with populated_db.connection() as conn:
            conn.execute(
                "INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count) "
                "VALUES (300, 1, 'fp123', 0, 2)"
            )
            conn.execute(
                "INSERT INTO snapshot_entities (snapshot_id, project_id, original_entity_id, entity_type, canonical_name, mention_count) "
                "VALUES (300, 1, 20, 'character', 'Maria', 15)"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        maria = populated_db.fetchone(
            "SELECT id FROM entities WHERE project_id = ? AND mention_count = 15",
            (new_id,),
        )
        snap_entity = populated_db.fetchone(
            "SELECT original_entity_id FROM snapshot_entities WHERE project_id = ?",
            (new_id,),
        )

        assert maria is not None
        assert snap_entity is not None
        assert snap_entity["original_entity_id"] == maria["id"]

    def test_entity_version_links_old_new_entity_ids_remapped(self, populated_db, nra_path):
        """entity_version_links.old/new_entity_id deben remapearse."""
        with populated_db.connection() as conn:
            conn.execute(
                "INSERT INTO analysis_snapshots (id, project_id, document_fingerprint, alert_count, entity_count) "
                "VALUES (301, 1, 'fp123', 0, 2)"
            )
            conn.execute(
                "INSERT INTO entity_version_links (project_id, snapshot_id, old_entity_id, new_entity_id, old_name, new_name, link_type, confidence, reason_json) "
                "VALUES (1, 301, 20, 21, 'Maria', 'Pedro', 'renamed', 0.9, '{\"reason\":\"test\"}')"
            )
            conn.commit()

        NraExporter(populated_db).export_project(1, nra_path)
        new_id = NraImporter(populated_db).import_project(nra_path).value

        maria = populated_db.fetchone(
            "SELECT id FROM entities WHERE project_id = ? AND mention_count = 15",
            (new_id,),
        )
        pedro = populated_db.fetchone(
            "SELECT id FROM entities WHERE project_id = ? AND mention_count = 8",
            (new_id,),
        )
        link = populated_db.fetchone(
            "SELECT old_entity_id, new_entity_id FROM entity_version_links WHERE project_id = ?",
            (new_id,),
        )

        assert maria is not None
        assert pedro is not None
        assert link is not None
        assert link["old_entity_id"] == maria["id"]
        assert link["new_entity_id"] == pedro["id"]

