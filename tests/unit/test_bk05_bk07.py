"""
Tests para BK-05 (Comparación antes/después) y BK-07 (Multi-documento / Sagas).

Cubre:
- EntityMatcher: exact + fuzzy name matching
- SnapshotRepository: create, get, cleanup
- ComparisonService: two-pass alert matching, entity diff
- CollectionRepository: CRUD, entity links, suggestions
- CrossBookAnalyzer: attribute comparison cross-book
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# EntityMatcher Tests
# ============================================================================


class TestEntityMatcher:
    """Tests para el matching de entidades."""

    def test_exact_match_identical(self):
        from narrative_assistant.analysis.entity_matcher import exact_match
        assert exact_match("María García", "María García") is True

    def test_exact_match_case_insensitive(self):
        from narrative_assistant.analysis.entity_matcher import exact_match
        assert exact_match("Juan Carlos", "juan carlos") is True

    def test_exact_match_accent_normalized(self):
        from narrative_assistant.analysis.entity_matcher import exact_match
        assert exact_match("José", "Jose") is True

    def test_exact_match_different(self):
        from narrative_assistant.analysis.entity_matcher import exact_match
        assert exact_match("Juan", "Pedro") is False

    def test_fuzzy_match_similar_names(self):
        from narrative_assistant.analysis.entity_matcher import fuzzy_match
        sim = fuzzy_match("Juan García", "Juan Garcia Lopez")
        assert sim > 0.5  # Should be similar

    def test_fuzzy_match_different_names(self):
        from narrative_assistant.analysis.entity_matcher import fuzzy_match
        sim = fuzzy_match("Juan", "Pedro")
        assert sim < 0.5

    def test_fuzzy_match_with_aliases(self):
        from narrative_assistant.analysis.entity_matcher import fuzzy_match
        sim = fuzzy_match(
            "Don Quijote", "El Caballero",
            aliases1=["El Caballero de la Triste Figura"],
            aliases2=["Don Quijote de la Mancha"],
        )
        # Aliases should boost match
        assert sim > 0.3

    def test_jaccard_similarity(self):
        from narrative_assistant.analysis.entity_matcher import jaccard_similarity
        assert jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(0.5)

    def test_jaccard_similarity_empty(self):
        from narrative_assistant.analysis.entity_matcher import jaccard_similarity
        assert jaccard_similarity(set(), set()) == 1.0
        assert jaccard_similarity({"a"}, set()) == 0.0

    def test_find_matches(self):
        from narrative_assistant.analysis.entity_matcher import find_matches
        source = [
            {"canonical_name": "María", "entity_type": "character"},
            {"canonical_name": "Madrid", "entity_type": "location"},
        ]
        target = [
            {"canonical_name": "María García", "entity_type": "character"},
            {"canonical_name": "Barcelona", "entity_type": "location"},
        ]
        matches = find_matches(source, target, threshold=0.5)
        # María should fuzzy-match María García
        assert len(matches) >= 1
        assert matches[0].source_name == "María"

    def test_find_matches_respects_type(self):
        from narrative_assistant.analysis.entity_matcher import find_matches
        source = [{"canonical_name": "Madrid", "entity_type": "character"}]
        target = [{"canonical_name": "Madrid", "entity_type": "location"}]
        matches = find_matches(source, target, threshold=0.5)
        # Different types should not match
        assert len(matches) == 0

    def test_char_ngrams(self):
        from narrative_assistant.analysis.entity_matcher import _char_ngrams
        ngrams = _char_ngrams("hola", n=3)
        assert "hol" in ngrams
        assert "ola" in ngrams


# ============================================================================
# SnapshotRepository Tests
# ============================================================================


class TestSnapshotRepository:
    """Tests para el repositorio de snapshots."""

    def test_create_snapshot_empty_project(self, isolated_database):
        """No crea snapshot si no hay datos."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Test', 'abc123', 'txt')"""
            )
            conn.commit()

        repo = SnapshotRepository(db)
        result = repo.create_snapshot(1)
        assert result is None

    def test_create_snapshot_with_data(self, isolated_database):
        """Crea snapshot con alertas y entidades."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Test', 'abc123', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type, title, description, explanation)
                   VALUES (1, 'consistency', 'warning', 'attr_change', 'Test alert', 'Desc', 'Expl')"""
            )
            conn.commit()

        repo = SnapshotRepository(db)
        snapshot_id = repo.create_snapshot(1)
        assert snapshot_id is not None

        summary = repo.get_latest_snapshot(1)
        assert summary is not None
        assert summary.alert_count == 1
        assert summary.entity_count == 1

        alerts = repo.get_snapshot_alerts(snapshot_id)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "attr_change"

        entities = repo.get_snapshot_entities(snapshot_id)
        assert len(entities) == 1
        assert entities[0].canonical_name == "María"

    def test_cleanup_old_snapshots(self, isolated_database):
        """Limpia snapshots antiguos manteniendo los últimos N."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Test', 'abc123', 'txt')"""
            )
            # Crear entidad para que snapshot tenga datos
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'Test')"""
            )
            conn.commit()

        repo = SnapshotRepository(db)

        # Crear 3 snapshots
        for _ in range(3):
            repo.create_snapshot(1)

        # Verificar que hay 3
        with db.connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM analysis_snapshots WHERE project_id = 1"
            ).fetchone()[0]
            assert count == 3

        # Cleanup manteniendo 2
        deleted = repo.cleanup_old_snapshots(1, keep=2)
        assert deleted == 1

        with db.connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM analysis_snapshots WHERE project_id = 1"
            ).fetchone()[0]
            assert count == 2

    def test_snapshot_related_entity_names(self, isolated_database):
        """Snapshot guarda nombres de entidades denormalizados."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Test', 'abc123', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type,
                   title, description, explanation, entity_ids)
                   VALUES (1, 'consistency', 'warning', 'test', 'T', 'D', 'E', '[1]')"""
            )
            conn.commit()

        repo = SnapshotRepository(db)
        snapshot_id = repo.create_snapshot(1)
        alerts = repo.get_snapshot_alerts(snapshot_id)
        assert len(alerts) == 1
        names = json.loads(alerts[0].related_entity_names)
        assert "María" in names


# ============================================================================
# ComparisonService Tests
# ============================================================================


class TestComparisonService:
    """Tests para el servicio de comparación."""

    def _setup_project_with_snapshot(self, db):
        """Helper: crea proyecto con datos, snapshot, y nuevos datos."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format, analysis_status)
                   VALUES (1, 'Test', 'fp1', 'txt', 'completed')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count)
                   VALUES (1, 1, 'character', 'María', 10)"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count)
                   VALUES (2, 1, 'character', 'Juan', 5)"""
            )
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type,
                   title, description, explanation, content_hash)
                   VALUES (1, 'consistency', 'warning', 'attr', 'Old alert', 'D', 'E', 'hash_old')"""
            )
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type,
                   title, description, explanation, content_hash)
                   VALUES (1, 'style', 'info', 'rep', 'Shared alert', 'D', 'E', 'hash_shared')"""
            )
            conn.commit()

        # Create snapshot
        repo = SnapshotRepository(db)
        repo.create_snapshot(1)

        # Simulate re-analysis: clear and recreate with different data
        with db.connection() as conn:
            conn.execute("DELETE FROM alerts WHERE project_id = 1")
            conn.execute("DELETE FROM entities WHERE project_id = 1")

            # New entities (María stays, Juan gone, Pedro added)
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count)
                   VALUES (10, 1, 'character', 'María', 12)"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name, mention_count)
                   VALUES (11, 1, 'character', 'Pedro', 3)"""
            )

            # New alerts (old resolved, shared stays, new added)
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type,
                   title, description, explanation, content_hash)
                   VALUES (1, 'style', 'info', 'rep', 'Shared alert', 'D', 'E', 'hash_shared')"""
            )
            conn.execute(
                """INSERT INTO alerts (project_id, category, severity, alert_type,
                   title, description, explanation, content_hash)
                   VALUES (1, 'consistency', 'critical', 'timeline', 'New alert', 'D', 'E', 'hash_new')"""
            )
            conn.commit()

    def test_comparison_report(self, isolated_database):
        """Genera reporte de comparación correcto."""
        from narrative_assistant.analysis.comparison import ComparisonService

        self._setup_project_with_snapshot(isolated_database)
        service = ComparisonService(isolated_database)
        report = service.compare(1)

        assert report is not None
        assert report.project_id == 1

        # Alerts: 'hash_old' resolved, 'hash_shared' unchanged, 'hash_new' is new
        assert len(report.alerts_resolved) == 1
        assert report.alerts_resolved[0].content_hash == "hash_old"
        assert len(report.alerts_new) == 1
        assert report.alerts_new[0].content_hash == "hash_new"
        assert report.alerts_unchanged == 1

        # Entities: María unchanged, Juan removed, Pedro added
        assert len(report.entities_removed) == 1
        assert report.entities_removed[0].canonical_name == "Juan"
        assert len(report.entities_added) == 1
        assert report.entities_added[0].canonical_name == "Pedro"
        assert report.entities_unchanged == 1

    def test_comparison_no_snapshot(self, isolated_database):
        """Retorna None si no hay snapshot."""
        from narrative_assistant.analysis.comparison import ComparisonService

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format, analysis_status)
                   VALUES (1, 'Test', 'fp1', 'txt', 'completed')"""
            )
            conn.commit()

        service = ComparisonService(db)
        assert service.compare(1) is None

    def test_comparison_to_dict(self, isolated_database):
        """to_dict() produce formato serializable."""
        from narrative_assistant.analysis.comparison import ComparisonService

        self._setup_project_with_snapshot(isolated_database)
        service = ComparisonService(isolated_database)
        report = service.compare(1)
        d = report.to_dict()

        assert "alerts" in d
        assert "entities" in d
        assert "summary" in d
        assert isinstance(d["alerts"]["new"], list)
        assert isinstance(d["summary"]["total_alerts_before"], int)

    def test_comparison_fingerprint_change(self, isolated_database):
        """Detecta cambio de fingerprint."""
        from narrative_assistant.analysis.comparison import ComparisonService
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format, analysis_status)
                   VALUES (1, 'Test', 'fp_old', 'txt', 'completed')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'Test')"""
            )
            conn.commit()

        SnapshotRepository(db).create_snapshot(1)

        # Change fingerprint
        with db.connection() as conn:
            conn.execute("UPDATE projects SET document_fingerprint = 'fp_new' WHERE id = 1")
            conn.commit()

        report = ComparisonService(db).compare(1)
        assert report.document_fingerprint_changed is True


# ============================================================================
# CollectionRepository Tests
# ============================================================================


class TestCollectionRepository:
    """Tests para el repositorio de colecciones."""

    def test_create_and_get(self, isolated_database):
        """CRUD básico de colecciones."""
        from narrative_assistant.persistence.collection import CollectionRepository

        repo = CollectionRepository(isolated_database)
        cid = repo.create("Saga del Quijote", "Dos libros")
        assert cid > 0

        coll = repo.get(cid)
        assert coll.name == "Saga del Quijote"
        assert coll.description == "Dos libros"

    def test_list_all(self, isolated_database):
        from narrative_assistant.persistence.collection import CollectionRepository

        repo = CollectionRepository(isolated_database)
        repo.create("Col 1")
        repo.create("Col 2")
        all_cols = repo.list_all()
        assert len(all_cols) == 2

    def test_update(self, isolated_database):
        from narrative_assistant.persistence.collection import CollectionRepository

        repo = CollectionRepository(isolated_database)
        cid = repo.create("Old Name")
        repo.update(cid, name="New Name")
        assert repo.get(cid).name == "New Name"

    def test_delete(self, isolated_database):
        from narrative_assistant.persistence.collection import CollectionRepository

        repo = CollectionRepository(isolated_database)
        cid = repo.create("To Delete")
        repo.delete(cid)
        assert repo.get(cid) is None

    def test_add_remove_project(self, isolated_database):
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        result = repo.add_project(cid, 1)
        assert result["success"]

        projects = repo.get_projects(cid)
        assert len(projects) == 1
        assert projects[0]["id"] == 1

        repo.remove_project(cid, 1)
        assert len(repo.get_projects(cid)) == 0

    def test_add_project_warning_threshold(self, isolated_database):
        """Warning cuando hay muchos proyectos."""
        from narrative_assistant.persistence.collection import (
            WARN_PROJECTS_THRESHOLD,
            CollectionRepository,
        )

        db = isolated_database
        repo = CollectionRepository(db)
        cid = repo.create("Big Saga")

        # Create enough projects
        with db.connection() as conn:
            for i in range(WARN_PROJECTS_THRESHOLD + 1):
                conn.execute(
                    """INSERT INTO projects (id, name, document_fingerprint, document_format, collection_id)
                       VALUES (?, ?, ?, 'txt', ?)""",
                    (i + 1, f"Book {i}", f"fp{i}", cid),
                )
            conn.commit()

        # Adding one more should produce warning
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (999, 'Extra', 'fpx', 'txt')"""
            )
            conn.commit()

        result = repo.add_project(cid, 999)
        assert result["success"]
        assert "warning" in result

    def test_entity_link_crud(self, isolated_database):
        """CRUD de entity links."""
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María García')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)

        result = repo.create_entity_link(cid, 1, 2, 1, 2)
        assert result["success"]

        links = repo.get_entity_links(cid)
        assert len(links) == 1
        assert links[0].source_entity_name == "María"
        assert links[0].target_entity_name == "María García"

        repo.delete_entity_link(links[0].id)
        assert len(repo.get_entity_links(cid)) == 0

    def test_entity_link_validates_collection_membership(self, isolated_database):
        """Entity links validan que proyectos pertenezcan a la colección."""
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        # Project 2 NOT in collection

        result = repo.create_entity_link(cid, 1, 2, 1, 2)
        assert not result["success"]
        assert "does not belong" in result["error"]

    def test_remove_project_cleans_entity_links(self, isolated_database):
        """Quitar proyecto de colección limpia sus entity links."""
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)
        repo.create_entity_link(cid, 1, 2, 1, 2)

        assert len(repo.get_entity_links(cid)) == 1

        repo.remove_project(cid, 1)
        assert len(repo.get_entity_links(cid)) == 0

    def test_link_suggestions(self, isolated_database):
        """Sugiere links para entidades con nombres similares."""
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María García')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María García')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (3, 1, 'location', 'Madrid')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (4, 2, 'location', 'Barcelona')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)

        suggestions = repo.get_link_suggestions(cid, threshold=0.7)
        # María García should be suggested (exact match)
        maria_suggestions = [s for s in suggestions if "María" in s.source_entity_name]
        assert len(maria_suggestions) >= 1

    def test_workspace_cache(self, isolated_database, tmp_path):
        """Workspace auxiliar guarda y carga datos."""
        import os

        from narrative_assistant.persistence.collection import CollectionRepository

        os.environ["NA_DATA_DIR"] = str(tmp_path)
        try:
            repo = CollectionRepository(isolated_database)
            repo.save_workspace_cache(1, "cross_book_analysis", {"key": "value"})
            loaded = repo.load_workspace_cache(1, "cross_book_analysis")
            assert loaded == {"key": "value"}
        finally:
            if "NA_DATA_DIR" in os.environ:
                del os.environ["NA_DATA_DIR"]


# ============================================================================
# CrossBookAnalyzer Tests
# ============================================================================


class TestCrossBookAnalyzer:
    """Tests para el analizador cross-book."""

    def test_cross_book_attribute_inconsistency(self, isolated_database):
        """Detecta inconsistencia de atributos entre libros."""
        from narrative_assistant.analysis.cross_book import CrossBookAnalyzer
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            # Dos libros
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            # María en ambos libros
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María')"""
            )
            # Atributos inconsistentes: ojos azules vs verdes
            conn.execute(
                """INSERT INTO entity_attributes (entity_id, attribute_type, attribute_key, attribute_value, confidence)
                   VALUES (1, 'physical', 'color_ojos', 'azules', 0.9)"""
            )
            conn.execute(
                """INSERT INTO entity_attributes (entity_id, attribute_type, attribute_key, attribute_value, confidence)
                   VALUES (2, 'physical', 'color_ojos', 'verdes', 0.85)"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)
        repo.create_entity_link(cid, 1, 2, 1, 2)

        analyzer = CrossBookAnalyzer(db)
        report = analyzer.analyze(cid)

        assert report.entity_links_analyzed == 1
        assert len(report.inconsistencies) == 1
        inc = report.inconsistencies[0]
        assert inc.attribute_key == "color_ojos"
        assert inc.value_book_a == "azules"
        assert inc.value_book_b == "verdes"

    def test_cross_book_no_inconsistency(self, isolated_database):
        """No hay inconsistencia cuando atributos coinciden."""
        from narrative_assistant.analysis.cross_book import CrossBookAnalyzer
        from narrative_assistant.persistence.collection import CollectionRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María')"""
            )
            # Same attribute value
            conn.execute(
                """INSERT INTO entity_attributes (entity_id, attribute_type, attribute_key, attribute_value)
                   VALUES (1, 'physical', 'color_ojos', 'azules')"""
            )
            conn.execute(
                """INSERT INTO entity_attributes (entity_id, attribute_type, attribute_key, attribute_value)
                   VALUES (2, 'physical', 'color_ojos', 'azules')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)
        repo.create_entity_link(cid, 1, 2, 1, 2)

        analyzer = CrossBookAnalyzer(db)
        report = analyzer.analyze(cid)
        assert len(report.inconsistencies) == 0

    def test_cross_book_report_to_dict(self, isolated_database):
        """to_dict() produce formato serializable."""
        from narrative_assistant.analysis.cross_book import CrossBookReport

        report = CrossBookReport(collection_id=1, collection_name="Test")
        d = report.to_dict()
        assert d["collection_id"] == 1
        assert d["summary"]["total_inconsistencies"] == 0


# ============================================================================
# Schema Migration Tests
# ============================================================================


class TestSchemaV14:
    """Verifica que las nuevas tablas existen en el schema."""

    def test_analysis_snapshots_table(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute("SELECT id, project_id, status FROM analysis_snapshots LIMIT 0")

    def test_snapshot_alerts_table(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                "SELECT id, snapshot_id, content_hash, related_entity_names FROM snapshot_alerts LIMIT 0"
            )

    def test_snapshot_entities_table(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                "SELECT id, snapshot_id, canonical_name, aliases FROM snapshot_entities LIMIT 0"
            )

    def test_collections_table(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute("SELECT id, name, description FROM collections LIMIT 0")

    def test_collection_entity_links_table(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                "SELECT id, collection_id, source_entity_id, match_type FROM collection_entity_links LIMIT 0"
            )

    def test_projects_collection_columns(self, isolated_database):
        db = isolated_database
        with db.connection() as conn:
            conn.execute("SELECT collection_id, collection_order FROM projects LIMIT 0")


# ============================================================================
# Security / Adversarial Tests
# ============================================================================


class TestSecurityPathTraversal:
    """Tests de seguridad: path traversal en workspace cache."""

    def test_cache_type_path_traversal_rejected(self, isolated_database, tmp_path):
        """cache_type con path traversal es rechazado."""
        import os

        from narrative_assistant.persistence.collection import CollectionRepository

        os.environ["NA_DATA_DIR"] = str(tmp_path)
        try:
            repo = CollectionRepository(isolated_database)
            # Intento de path traversal
            repo.save_workspace_cache(1, "../../../etc/passwd", {"malicious": True})
            # Verificar que NO se creó el archivo
            malicious_path = tmp_path / ".." / ".." / ".." / "etc" / "passwd.json"
            assert not malicious_path.exists()
            # Verificar que load también rechaza
            result = repo.load_workspace_cache(1, "../../../etc/passwd")
            assert result is None
        finally:
            if "NA_DATA_DIR" in os.environ:
                del os.environ["NA_DATA_DIR"]

    def test_cache_type_invalid_name_rejected(self, isolated_database, tmp_path):
        """cache_type con nombre no autorizado es rechazado."""
        import os

        from narrative_assistant.persistence.collection import CollectionRepository

        os.environ["NA_DATA_DIR"] = str(tmp_path)
        try:
            repo = CollectionRepository(isolated_database)
            repo.save_workspace_cache(1, "arbitrary_type", {"data": 1})
            result = repo.load_workspace_cache(1, "arbitrary_type")
            assert result is None
        finally:
            if "NA_DATA_DIR" in os.environ:
                del os.environ["NA_DATA_DIR"]

    def test_cache_type_valid_name_accepted(self, isolated_database, tmp_path):
        """cache_type válido funciona correctamente."""
        import os

        from narrative_assistant.persistence.collection import CollectionRepository

        os.environ["NA_DATA_DIR"] = str(tmp_path)
        try:
            repo = CollectionRepository(isolated_database)
            for valid_type in ["cross_book_analysis", "entity_suggestions", "collection_summary"]:
                repo.save_workspace_cache(1, valid_type, {"type": valid_type})
                loaded = repo.load_workspace_cache(1, valid_type)
                assert loaded is not None
                assert loaded["type"] == valid_type
        finally:
            if "NA_DATA_DIR" in os.environ:
                del os.environ["NA_DATA_DIR"]


class TestSecurityInputValidation:
    """Tests de validación de entrada."""

    def test_entity_matcher_empty_name(self):
        """EntityMatcher maneja nombres vacíos sin crash."""
        from narrative_assistant.analysis.entity_matcher import exact_match, fuzzy_match
        assert exact_match("", "") is True
        assert exact_match("", "María") is False
        sim = fuzzy_match("", "María")
        assert sim >= 0.0  # No crash, retorna valor válido

    def test_entity_matcher_special_characters(self):
        """EntityMatcher maneja caracteres especiales."""
        from narrative_assistant.analysis.entity_matcher import exact_match, fuzzy_match
        # SQL injection attempt in name
        assert exact_match("'; DROP TABLE--", "'; DROP TABLE--") is True
        assert exact_match("'; DROP TABLE--", "María") is False
        # Unicode edge cases
        sim = fuzzy_match("María\u200b", "María")  # zero-width space
        assert sim >= 0.0

    def test_entity_matcher_very_long_name(self):
        """EntityMatcher no crash con nombres muy largos."""
        from narrative_assistant.analysis.entity_matcher import fuzzy_match
        long_name = "A" * 10000
        sim = fuzzy_match(long_name, "María")
        assert 0.0 <= sim <= 1.0

    def test_snapshot_nonexistent_project(self, isolated_database):
        """Snapshot de proyecto inexistente retorna None."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository
        repo = SnapshotRepository(isolated_database)
        result = repo.create_snapshot(999999)
        assert result is None

    def test_comparison_nonexistent_project(self, isolated_database):
        """Comparison de proyecto inexistente retorna None."""
        from narrative_assistant.analysis.comparison import ComparisonService
        service = ComparisonService(isolated_database)
        result = service.compare(999999)
        assert result is None

    def test_collection_double_delete(self, isolated_database):
        """Eliminar colección dos veces no crashea."""
        from narrative_assistant.persistence.collection import CollectionRepository
        repo = CollectionRepository(isolated_database)
        cid = repo.create("Test")
        repo.delete(cid)
        repo.delete(cid)  # No crash

    def test_entity_link_duplicate(self, isolated_database):
        """Crear enlace duplicado retorna error, no crash."""
        from narrative_assistant.persistence.collection import CollectionRepository
        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Book 1', 'fp1', 'txt')"""
            )
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (2, 'Book 2', 'fp2', 'txt')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (1, 1, 'character', 'María')"""
            )
            conn.execute(
                """INSERT INTO entities (id, project_id, entity_type, canonical_name)
                   VALUES (2, 2, 'character', 'María')"""
            )
            conn.commit()

        repo = CollectionRepository(db)
        cid = repo.create("Saga")
        repo.add_project(cid, 1)
        repo.add_project(cid, 2)

        result1 = repo.create_entity_link(cid, 1, 2, 1, 2)
        assert result1["success"] is True

        result2 = repo.create_entity_link(cid, 1, 2, 1, 2)
        assert result2["success"] is False
        assert "already exists" in result2["error"]

    def test_cross_book_empty_collection(self, isolated_database):
        """Cross-book analysis de colección vacía no crashea."""
        from narrative_assistant.analysis.cross_book import CrossBookAnalyzer
        from narrative_assistant.persistence.collection import CollectionRepository

        repo = CollectionRepository(isolated_database)
        cid = repo.create("Empty Saga")

        analyzer = CrossBookAnalyzer(isolated_database)
        report = analyzer.analyze(cid)
        assert report.entity_links_analyzed == 0
        assert len(report.inconsistencies) == 0

    def test_cross_book_nonexistent_collection(self, isolated_database):
        """Cross-book de colección inexistente no crashea."""
        from narrative_assistant.analysis.cross_book import CrossBookAnalyzer
        analyzer = CrossBookAnalyzer(isolated_database)
        report = analyzer.analyze(999999)
        assert report.collection_name == "(no encontrada)"

    def test_snapshot_with_malformed_entity_ids(self, isolated_database):
        """Snapshot maneja entity_ids malformados sin crash."""
        from narrative_assistant.persistence.snapshot import SnapshotRepository

        db = isolated_database
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_fingerprint, document_format)
                   VALUES (1, 'Test', 'fp1', 'txt')"""
            )
            # Alerta con entity_ids JSON inválido
            conn.execute(
                """INSERT INTO alerts (project_id, alert_type, category, severity,
                          title, description, explanation, entity_ids)
                   VALUES (1, 'test', 'consistency', 'medium', 'Test alert',
                           'Test desc', 'Test expl', '}{invalid json}')"""
            )
            conn.commit()

        repo = SnapshotRepository(db)
        sid = repo.create_snapshot(1)
        # No crash, snapshot creado (entity_names será [])
        assert sid is not None
        alerts = repo.get_snapshot_alerts(sid)
        assert len(alerts) == 1
