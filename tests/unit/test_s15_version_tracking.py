"""
Tests for Sprint S15: Version Tracking (BK-28).

S15-01: Schema migration — version_metrics table.
S15-02: API endpoints — versions list + trend.
S15-03: Hook — write_version_metrics post-Phase 13.
"""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure api-server is importable
_api_server = str(Path(__file__).resolve().parents[2] / "api-server")
if _api_server not in sys.path:
    sys.path.insert(0, _api_server)


# Helper: minimal project INSERT with all NOT NULL columns
_INSERT_PROJECT = (
    "INSERT INTO projects (id, name, document_path, document_format, document_fingerprint, "
    "word_count, chapter_count) VALUES (?, ?, '/tmp/test.docx', 'DOCX', 'fp_test', ?, ?)"
)


# ============================================================================
# S15-01: Schema migration tests
# ============================================================================


class TestVersionMetricsSchema:
    """Tests para la tabla version_metrics."""

    def test_table_created(self, tmp_path):
        """La tabla version_metrics se crea al inicializar la BD."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = {t[0] for t in tables}
            assert "version_metrics" in table_names

    def test_table_columns(self, tmp_path):
        """version_metrics tiene todas las columnas requeridas."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            cols = conn.execute("PRAGMA table_info(version_metrics)").fetchall()
            col_names = {c[1] for c in cols}

        expected = {
            "id",
            "project_id",
            "version_num",
            "snapshot_id",
            "alert_count",
            "word_count",
            "entity_count",
            "chapter_count",
            "health_score",
            "formality_avg",
            "dialogue_ratio",
            "created_at",
        }
        assert expected.issubset(col_names)

    def test_unique_index_on_project_version(self, tmp_path):
        """Unique index on (project_id, version_num) previene duplicados."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            # Disable FK checks for this test
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                "INSERT INTO version_metrics (project_id, version_num, alert_count, word_count, entity_count, chapter_count) "
                "VALUES (1, 1, 5, 1000, 10, 3)"
            )
            conn.commit()

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO version_metrics (project_id, version_num, alert_count, word_count, entity_count, chapter_count) "
                    "VALUES (1, 1, 8, 2000, 12, 4)"
                )

    def test_cascade_delete_on_project(self, tmp_path):
        """Deleting project cascades to version_metrics."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(_INSERT_PROJECT, (99, "Test", 1000, 3))
            conn.execute(
                "INSERT INTO version_metrics (project_id, version_num, alert_count, word_count, entity_count, chapter_count) "
                "VALUES (99, 1, 5, 1000, 10, 3)"
            )
            conn.commit()

            conn.execute("DELETE FROM projects WHERE id = 99")
            conn.commit()

            row = conn.execute(
                "SELECT COUNT(*) FROM version_metrics WHERE project_id = 99"
            ).fetchone()
            assert row[0] == 0


# ============================================================================
# S15-03: write_version_metrics hook tests
# ============================================================================


class TestWriteVersionMetrics:
    """Tests para write_version_metrics hook."""

    def _make_db(self, tmp_path):
        """Create a test database with required tables."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test Project", 5000, 10))
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type) "
                "VALUES (1, 1, 'Juan', 'character')"
            )
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type) "
                "VALUES (2, 1, 'Madrid', 'location')"
            )
            conn.execute(
                "INSERT INTO alerts (project_id, alert_type, category, severity, title, description, explanation, status) "
                "VALUES (1, 'inconsistency', 'character', 'medium', 'Alert 1', 'desc', 'expl', 'open')"
            )
            conn.execute(
                "INSERT INTO alerts (project_id, alert_type, category, severity, title, description, explanation, status) "
                "VALUES (1, 'temporal', 'timeline', 'low', 'Alert 2', 'desc', 'expl', 'open')"
            )
            conn.execute(
                "INSERT INTO alerts (project_id, alert_type, category, severity, title, description, explanation, status) "
                "VALUES (1, 'grammar', 'grammar', 'info', 'Resolved', 'desc', 'expl', 'resolved')"
            )
            conn.commit()
        return db

    def test_writes_first_version(self, tmp_path):
        """Primera ejecución crea version_num=1."""
        from routers._enrichment_phases import write_version_metrics

        db = self._make_db(tmp_path)
        ctx = {"project_id": 1, "db_session": db}
        write_version_metrics(ctx)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT version_num, alert_count, word_count, entity_count, chapter_count "
                "FROM version_metrics WHERE project_id = 1"
            ).fetchone()

        assert row is not None
        assert row[0] == 1  # version_num
        assert row[1] == 2  # alert_count (2 open, 1 resolved excluded)
        assert row[2] == 5000  # word_count
        assert row[3] == 2  # entity_count
        assert row[4] == 10  # chapter_count

    def test_increments_version_num(self, tmp_path):
        """Segunda ejecución → version_num=2."""
        from routers._enrichment_phases import write_version_metrics

        db = self._make_db(tmp_path)
        ctx = {"project_id": 1, "db_session": db}

        write_version_metrics(ctx)
        write_version_metrics(ctx)

        with db.connection() as conn:
            rows = conn.execute(
                "SELECT version_num FROM version_metrics WHERE project_id = 1 ORDER BY version_num"
            ).fetchall()

        assert len(rows) == 2
        assert rows[0][0] == 1
        assert rows[1][0] == 2

    def test_reads_health_score_from_cache(self, tmp_path):
        """health_score se lee del enrichment_cache (narrative_health)."""
        from routers._enrichment_phases import write_version_metrics

        db = self._make_db(tmp_path)

        health_result = {"overall_score": 0.78, "dimensions": []}
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO enrichment_cache
                   (project_id, enrichment_type, status, result_json, phase)
                   VALUES (1, 'narrative_health', 'completed', ?, 13)""",
                (json.dumps(health_result),),
            )
            conn.commit()

        ctx = {"project_id": 1, "db_session": db}
        write_version_metrics(ctx)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT health_score FROM version_metrics WHERE project_id = 1"
            ).fetchone()

        assert row[0] == pytest.approx(0.78, abs=0.01)

    def test_reads_dialogue_ratio_from_chapters(self, tmp_path):
        """dialogue_ratio se calcula como promedio de chapters.dialogue_ratio."""
        from routers._enrichment_phases import write_version_metrics

        db = self._make_db(tmp_path)

        with db.connection() as conn:
            conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, word_count, start_char, end_char, dialogue_ratio) "
                "VALUES (1, 1, 'Ch1', 'Text', 100, 0, 100, 0.3)"
            )
            conn.execute(
                "INSERT INTO chapters (project_id, chapter_number, title, content, word_count, start_char, end_char, dialogue_ratio) "
                "VALUES (1, 2, 'Ch2', 'Text', 100, 100, 200, 0.5)"
            )
            conn.commit()

        ctx = {"project_id": 1, "db_session": db}
        write_version_metrics(ctx)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT dialogue_ratio FROM version_metrics WHERE project_id = 1"
            ).fetchone()

        assert row[0] == pytest.approx(0.4, abs=0.01)

    def test_graceful_on_missing_table(self):
        """Si la tabla no existe, no crashea (graceful degradation)."""
        from routers._enrichment_phases import write_version_metrics

        db = MagicMock()
        conn_mock = MagicMock()
        conn_mock.execute.side_effect = Exception("no such table: version_metrics")
        db.connection.return_value.__enter__ = MagicMock(return_value=conn_mock)
        db.connection.return_value.__exit__ = MagicMock(return_value=False)

        ctx = {"project_id": 1, "db_session": db}
        # Should not raise
        write_version_metrics(ctx)


# ============================================================================
# S15-02: API endpoint tests
# ============================================================================


class TestVersionEndpoints:
    """Tests para los endpoints de versiones."""

    def test_versions_endpoint_exists(self):
        """GET /projects/{id}/versions endpoint registrado."""
        from routers.projects import router

        paths = [r.path for r in router.routes]
        assert "/api/projects/{project_id}/versions" in paths

    def test_trend_endpoint_exists(self):
        """GET /projects/{id}/versions/trend endpoint registrado."""
        from routers.projects import router

        paths = [r.path for r in router.routes]
        assert "/api/projects/{project_id}/versions/trend" in paths

    def test_versions_response_format(self, tmp_path):
        """La tabla almacena y devuelve datos en formato correcto."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                "INSERT INTO version_metrics "
                "(project_id, version_num, alert_count, word_count, entity_count, chapter_count, health_score) "
                "VALUES (1, 1, 10, 5000, 15, 5, 0.72)"
            )
            conn.commit()

            row = conn.execute(
                "SELECT id, project_id, version_num, snapshot_id, "
                "alert_count, word_count, entity_count, chapter_count, "
                "health_score, formality_avg, dialogue_ratio, created_at "
                "FROM version_metrics WHERE project_id = 1"
            ).fetchone()

        assert row is not None
        assert row[2] == 1  # version_num
        assert row[4] == 10  # alert_count
        assert row[8] == pytest.approx(0.72)  # health_score


# ============================================================================
# S15-04/05/06: Frontend type/component tests
# ============================================================================


class TestVersionTypes:
    """Tests para tipos de frontend (importabilidad)."""

    def test_api_types_defined(self):
        """ApiVersionMetrics y ApiVersionTrend definidos en types."""
        api_file = Path("frontend/src/types/api/projects.ts")
        assert api_file.exists()

        content = api_file.read_text(encoding="utf-8")
        assert "ApiVersionMetrics" in content
        assert "ApiVersionTrend" in content
        assert "ApiVersionDelta" in content
        assert "top_entity_renames" in content

    def test_domain_types_defined(self):
        """VersionMetrics y VersionTrend domain types definidos."""
        domain_file = Path("frontend/src/types/domain/projects.ts")
        assert domain_file.exists()

        content = domain_file.read_text(encoding="utf-8")
        assert "VersionMetrics" in content
        assert "VersionTrend" in content
        assert "VersionDelta" in content
        assert "topEntityRenames" in content

    def test_transformer_functions_defined(self):
        """transformVersionMetrics y transformVersionTrend definidos."""
        transformer_file = Path("frontend/src/types/transformers/projects.ts")
        assert transformer_file.exists()

        content = transformer_file.read_text(encoding="utf-8")
        assert "transformVersionMetrics" in content
        assert "transformVersionTrend" in content

    def test_sparkline_component_exists(self):
        """VersionSparkline.vue existe con SVG sparkline."""
        vue_file = Path("frontend/src/components/project/VersionSparkline.vue")
        assert vue_file.exists()

        content = vue_file.read_text(encoding="utf-8")
        assert "<script setup" in content
        assert "<svg" in content
        assert "polyline" in content

    def test_history_component_exists(self):
        """VersionHistory.vue existe con DataTable."""
        vue_file = Path("frontend/src/components/project/VersionHistory.vue")
        assert vue_file.exists()

        content = vue_file.read_text(encoding="utf-8")
        assert "DataTable" in content
        assert "VersionComparison" in content

    def test_comparison_component_exists(self):
        """VersionComparison.vue existe con Dialog + ProgressBar."""
        vue_file = Path("frontend/src/components/project/VersionComparison.vue")
        assert vue_file.exists()

        content = vue_file.read_text(encoding="utf-8")
        assert "Dialog" in content
        assert "ProgressBar" in content
