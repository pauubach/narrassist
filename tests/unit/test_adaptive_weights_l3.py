"""
Tests for Adaptive Weights Level 3 (per-manuscript).

Pesos adaptativos que se acumulan del feedback del usuario y persisten
entre re-análisis. Diferente de detector_calibration (que se recomputa).
"""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
# Schema tests
# ============================================================================


class TestProjectDetectorWeightsSchema:
    """Tests para la tabla project_detector_weights."""

    def test_table_created(self, tmp_path):
        """La tabla project_detector_weights se crea al inicializar la BD."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}
            assert "project_detector_weights" in table_names

    def test_table_columns(self, tmp_path):
        """project_detector_weights tiene todas las columnas requeridas."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            cols = conn.execute("PRAGMA table_info(project_detector_weights)").fetchall()
            col_names = {c[1] for c in cols}

        expected = {
            "id", "project_id", "alert_type", "weight",
            "feedback_count", "dismiss_count", "confirm_count", "updated_at",
        }
        assert expected.issubset(col_names)

    def test_unique_constraint(self, tmp_path):
        """Unique constraint on (project_id, alert_type)."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                "INSERT INTO project_detector_weights (project_id, alert_type, weight) "
                "VALUES (1, 'attribute_inconsistency', 0.8)"
            )
            conn.commit()

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO project_detector_weights (project_id, alert_type, weight) "
                    "VALUES (1, 'attribute_inconsistency', 0.9)"
                )

    def test_cascade_delete_on_project(self, tmp_path):
        """Deleting project cascades to project_detector_weights."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(_INSERT_PROJECT, (99, "Test", 1000, 3))
            conn.execute(
                "INSERT INTO project_detector_weights (project_id, alert_type, weight) "
                "VALUES (99, 'attribute_inconsistency', 0.7)"
            )
            conn.commit()

            conn.execute("DELETE FROM projects WHERE id = 99")
            conn.commit()

            row = conn.execute(
                "SELECT COUNT(*) FROM project_detector_weights WHERE project_id = 99"
            ).fetchone()
            assert row[0] == 0

    def test_default_weight_is_one(self, tmp_path):
        """Weight por defecto es 1.0."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                "INSERT INTO project_detector_weights (project_id, alert_type) "
                "VALUES (1, 'temporal_anachronism')"
            )
            conn.commit()

            row = conn.execute(
                "SELECT weight FROM project_detector_weights WHERE project_id = 1"
            ).fetchone()
            assert row[0] == 1.0


# ============================================================================
# AlertEngine adaptive weight tests
# ============================================================================


class TestAdaptiveWeightEngine:
    """Tests para update_adaptive_weight y _get_adaptive_weight en AlertEngine."""

    def _make_db_and_engine(self, tmp_path):
        """Create a test DB and an AlertEngine using it."""
        from narrative_assistant.persistence.database import Database
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.repository import AlertRepository

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test Project", 5000, 10))
            conn.commit()

        # Patch get_database to return our test DB
        repo = MagicMock(spec=AlertRepository)
        engine = AlertEngine(repository=repo)
        return db, engine

    def test_dismiss_decreases_weight(self, tmp_path):
        """Descartar una alerta reduce el peso."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            weight = engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

        assert weight < 1.0
        assert weight == pytest.approx(1.0 - 0.03, abs=0.001)

    def test_resolve_increases_weight(self, tmp_path):
        """Resolver una alerta (confirmar útil) sube el peso un poco."""
        db, engine = self._make_db_and_engine(tmp_path)

        # First dismiss to lower weight
        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            weight = engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=False)

        # After 2 dismissals (-0.06) + 1 confirm (+0.015) = 0.955
        assert weight == pytest.approx(0.955, abs=0.001)

    def test_weight_floors_at_minimum(self, tmp_path):
        """El peso nunca baja de ADAPTIVE_WEIGHT_FLOOR (0.1)."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Dismiss 50 times to try to go below floor
            for _ in range(50):
                weight = engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

        assert weight == pytest.approx(0.1, abs=0.001)

    def test_weight_caps_at_one(self, tmp_path):
        """El peso nunca sube por encima de 1.0."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Confirm 50 times
            for _ in range(50):
                weight = engine.update_adaptive_weight(1, "temporal_anachronism", dismissed=False)

        assert weight == 1.0

    def test_get_weight_returns_default_when_no_data(self, tmp_path):
        """Sin datos en BD, _get_adaptive_weight devuelve 1.0."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            weight = engine._get_adaptive_weight(1, "nonexistent_type")

        assert weight == 1.0

    def test_weights_are_per_project(self, tmp_path):
        """Pesos son independientes por proyecto."""
        db, engine = self._make_db_and_engine(tmp_path)

        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (2, "Project 2", 3000, 5))
            conn.commit()

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            weight_p1 = engine._get_adaptive_weight(1, "attribute_inconsistency")
            weight_p2 = engine._get_adaptive_weight(2, "attribute_inconsistency")

        assert weight_p1 < 1.0  # Project 1 has dismissals
        assert weight_p2 == 1.0  # Project 2 untouched

    def test_weights_are_per_alert_type(self, tmp_path):
        """Pesos son independientes por tipo de alerta."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            weight_attr = engine._get_adaptive_weight(1, "attribute_inconsistency")
            weight_temp = engine._get_adaptive_weight(1, "temporal_anachronism")

        assert weight_attr < 1.0
        assert weight_temp == 1.0

    def test_feedback_counts_tracked(self, tmp_path):
        """dismiss_count y confirm_count se rastrean correctamente."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=False)

            weights = engine.get_adaptive_weights(1)

        info = weights["attribute_inconsistency"]
        assert info["dismiss_count"] == 2
        assert info["confirm_count"] == 1
        assert info["feedback_count"] == 3

    def test_get_all_weights(self, tmp_path):
        """get_adaptive_weights devuelve todos los pesos del proyecto."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)
            engine.update_adaptive_weight(1, "temporal_anachronism", dismissed=True)
            engine.update_adaptive_weight(1, "spelling_typo", dismissed=False)

            weights = engine.get_adaptive_weights(1)

        assert len(weights) == 3
        assert "attribute_inconsistency" in weights
        assert "temporal_anachronism" in weights
        assert "spelling_typo" in weights


# ============================================================================
# Integration: weight applied in create_alert
# ============================================================================


class TestAdaptiveWeightApplied:
    """Tests para verificar que el peso se aplica al crear alertas."""

    def test_weight_reduces_confidence(self, tmp_path):
        """Un peso < 1.0 reduce la confianza de la alerta creada."""
        from narrative_assistant.persistence.database import Database
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity
        from narrative_assistant.alerts.repository import AlertRepository

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            conn.commit()

        # Use mock repo that captures the alert
        repo = MagicMock(spec=AlertRepository)
        created_alert = None

        def capture_create(alert):
            nonlocal created_alert
            created_alert = alert
            return Result.success(alert)

        repo.create.side_effect = capture_create
        engine = AlertEngine(repository=repo)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Dismiss many times to lower weight
            for _ in range(16):
                engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            engine.clear_adaptive_weights_cache()
            weight = engine._get_adaptive_weight(1, "attribute_inconsistency")

            from narrative_assistant.core.result import Result
            engine.create_alert(
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="attribute_inconsistency",
                title="Test alert",
                description="Test description",
                explanation="Test explanation",
                confidence=0.8,
            )

        assert created_alert is not None
        # With weight < 1.0, confidence should be less than 0.8
        assert created_alert.confidence < 0.8
        assert created_alert.confidence == pytest.approx(0.8 * weight, abs=0.01)

    def test_full_weight_no_reduction(self, tmp_path):
        """Con peso 1.0 (sin feedback), la confianza no cambia."""
        from narrative_assistant.persistence.database import Database
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity
        from narrative_assistant.alerts.repository import AlertRepository

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            conn.commit()

        repo = MagicMock(spec=AlertRepository)
        created_alert = None

        def capture_create(alert):
            nonlocal created_alert
            created_alert = alert
            return Result.success(alert)

        repo.create.side_effect = capture_create
        engine = AlertEngine(repository=repo)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            from narrative_assistant.core.result import Result
            engine.create_alert(
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="attribute_inconsistency",
                title="Test alert",
                description="Test description",
                explanation="Test explanation",
                confidence=0.8,
            )

        assert created_alert is not None
        # No adaptive weight → confidence unchanged (only calibration, which is 1.0)
        assert created_alert.confidence == pytest.approx(0.8, abs=0.01)


# ============================================================================
# Persistence: weights survive re-analysis
# ============================================================================


class TestAdaptiveWeightPersistence:
    """Tests para verificar que los pesos sobreviven re-análisis."""

    def test_weights_not_deleted_by_cleanup(self, tmp_path):
        """run_cleanup NO borra project_detector_weights."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            conn.execute(
                "INSERT INTO project_detector_weights "
                "(project_id, alert_type, weight, feedback_count, dismiss_count, confirm_count) "
                "VALUES (1, 'attribute_inconsistency', 0.7, 10, 8, 2)"
            )
            conn.commit()

        # Simulate what run_cleanup does: delete alerts and related data
        with db.connection() as conn:
            conn.execute("DELETE FROM alerts WHERE project_id = 1")
            conn.commit()

        # Weights should still be there
        with db.connection() as conn:
            row = conn.execute(
                "SELECT weight, dismiss_count FROM project_detector_weights "
                "WHERE project_id = 1 AND alert_type = 'attribute_inconsistency'"
            ).fetchone()

        assert row is not None
        assert row[0] == pytest.approx(0.7)
        assert row[1] == 8

    def test_weight_accumulates_across_analyses(self, tmp_path):
        """Pesos se acumulan entre múltiples análisis."""
        from narrative_assistant.persistence.database import Database
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.repository import AlertRepository

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            conn.commit()

        repo = MagicMock(spec=AlertRepository)
        engine = AlertEngine(repository=repo)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # "First analysis": 3 dismissals
            for _ in range(3):
                engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            weight_after_first = engine._get_adaptive_weight(1, "attribute_inconsistency")

            # Simulate re-analysis cleanup (clear alerts, NOT weights)
            with db.connection() as conn:
                conn.execute("DELETE FROM alerts WHERE project_id = 1")
                conn.commit()

            # Clear engine cache to force re-read from DB
            engine.clear_adaptive_weights_cache()

            # "Second analysis": 2 more dismissals
            for _ in range(2):
                engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            weight_after_second = engine._get_adaptive_weight(1, "attribute_inconsistency")

        # Weight should be lower after second batch (accumulated)
        assert weight_after_second < weight_after_first
        # 5 total dismissals: 1.0 - 5 * 0.03 = 0.85
        assert weight_after_second == pytest.approx(0.85, abs=0.001)


# ============================================================================
# API endpoint tests
# ============================================================================


class TestAdaptiveWeightsEndpoint:
    """Tests para el endpoint GET /alerts/adaptive-weights."""

    def test_endpoint_registered(self):
        """GET /projects/{id}/alerts/adaptive-weights endpoint registrado."""
        from routers.alerts import router

        paths = [r.path for r in router.routes]
        assert "/api/projects/{project_id}/alerts/adaptive-weights" in paths
