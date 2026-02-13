"""
Tests for Adaptive Weights Level 3 (per-manuscript).

Pesos adaptativos que se acumulan del feedback del usuario y persisten
entre re-análisis. Diferente de detector_calibration (que se recomputa).
"""

import asyncio
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
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
            "id", "project_id", "alert_type", "entity_canonical_name",
            "weight", "feedback_count", "dismiss_count", "confirm_count", "updated_at",
        }
        assert expected.issubset(col_names)

    def test_unique_constraint(self, tmp_path):
        """Unique constraint on (project_id, alert_type, entity_canonical_name)."""
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
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.persistence.database import Database

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
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.persistence.database import Database

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
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.persistence.database import Database

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
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.persistence.database import Database

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


# ============================================================================
# Router hooks: resolve-all / dismiss-batch
# ============================================================================


class TestAdaptiveWeightRouterHooks:
    """Tests para hooks de pesos adaptativos en endpoints de alertas."""

    def test_resolve_all_updates_adaptive_weights(self, monkeypatch):
        """resolve-all debe confirmar pesos adaptativos para alertas abiertas."""
        import deps
        from routers.alerts import resolve_all_alerts

        from narrative_assistant.alerts.models import AlertStatus

        open_alert = SimpleNamespace(
            project_id=1,
            alert_type="attribute_inconsistency",
            status=AlertStatus.NEW,
            extra_data={"entity_name": "Pedro"},
        )
        already_closed = SimpleNamespace(
            project_id=1,
            alert_type="attribute_inconsistency",
            status=AlertStatus.RESOLVED,
            extra_data={"entity_name": "María"},
        )

        alert_repo = MagicMock()
        alert_repo.get_by_project.return_value = SimpleNamespace(
            is_failure=False, value=[open_alert, already_closed]
        )

        engine = MagicMock()
        monkeypatch.setattr(deps, "alert_repository", alert_repo)

        with patch("narrative_assistant.alerts.engine.get_alert_engine", return_value=engine):
            response = asyncio.run(resolve_all_alerts(1))

        assert response.success is True
        alert_repo.update.assert_called_once_with(open_alert)
        engine.update_adaptive_weight.assert_called_once_with(
            1,
            "attribute_inconsistency",
            dismissed=False,
            entity_names=["Pedro"],
        )

    def test_dismiss_batch_uses_get_and_updates_adaptive_weights(self, monkeypatch):
        """dismiss-batch usa get() (no get_by_id) y actualiza pesos por entidad."""
        import deps
        from routers.alerts import dismiss_batch

        from narrative_assistant.alerts.models import AlertStatus

        # Repo sin get_by_id: si el endpoint lo usara, fallaría.
        class AlertRepoNoGetById:
            def __init__(self, alerts_by_id):
                self._alerts = alerts_by_id
                self.updated = []

            def get(self, alert_id: int):
                alert = self._alerts.get(alert_id)
                if alert is None:
                    return SimpleNamespace(is_success=False, value=None)
                return SimpleNamespace(is_success=True, value=alert)

            def update(self, alert):
                self.updated.append(alert)
                return SimpleNamespace(is_success=True, value=alert)

        alerts_by_id = {
            1: SimpleNamespace(
                project_id=1,
                alert_type="attribute_inconsistency",
                source_module="attribute_consistency",
                content_hash="h1",
                status=AlertStatus.NEW,
                extra_data={"entity_name": "Pedro"},
            ),
            2: SimpleNamespace(
                project_id=1,
                alert_type="attribute_inconsistency",
                source_module="attribute_consistency",
                content_hash="h2",
                status=AlertStatus.NEW,
                extra_data={"entity_name": "María"},
            ),
        }

        alert_repo = AlertRepoNoGetById(alerts_by_id)
        dismissal_repo = MagicMock()
        engine = MagicMock()

        monkeypatch.setattr(deps, "alert_repository", alert_repo)
        monkeypatch.setattr(deps, "dismissal_repository", dismissal_repo)

        body = deps.BatchDismissRequest(
            alert_ids=[1, 2],
            reason="false_positive",
            scope="instance",
        )

        with patch("narrative_assistant.alerts.engine.get_alert_engine", return_value=engine):
            response = asyncio.run(dismiss_batch(1, body))

        assert response.success is True
        assert len(alert_repo.updated) == 2
        assert all(a.status == AlertStatus.DISMISSED for a in alert_repo.updated)
        dismissal_repo.dismiss_batch.assert_called_once()
        engine.recalibrate_detector.assert_called_once_with(
            1, "attribute_inconsistency", "attribute_consistency"
        )
        engine.update_adaptive_weight.assert_called_once()
        args, kwargs = engine.update_adaptive_weight.call_args
        assert args[0] == 1
        assert args[1] == "attribute_inconsistency"
        assert kwargs["dismissed"] is True
        assert set(kwargs["entity_names"]) == {"Pedro", "María"}


# ============================================================================
# Per-entity adaptive weight tests
# ============================================================================


class TestPerEntityAdaptiveWeights:
    """Tests para pesos adaptativos per-entity (cascading lookup)."""

    def _make_db_and_engine(self, tmp_path):
        """Create a test DB and an AlertEngine using it."""
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test Project", 5000, 10))
            conn.commit()

        repo = MagicMock(spec=AlertRepository)
        engine = AlertEngine(repository=repo)
        return db, engine

    def test_per_entity_dismiss_only_affects_that_entity(self, tmp_path):
        """Descartar alerta de 'Pedro' no afecta peso per-entity de 'María'.

        Nota: project-level también baja (siempre se actualiza), así que
        María hereda el project-level. Pero Pedro tiene su propio peso
        per-entity separado del de María.
        """
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(
                1, "attribute_inconsistency", dismissed=True, entity_names=["Pedro"]
            )

            engine.clear_adaptive_weights_cache()
            weight_pedro = engine._get_adaptive_weight(1, "attribute_inconsistency", "Pedro")
            weight_maria = engine._get_adaptive_weight(1, "attribute_inconsistency", "María")

        assert weight_pedro < 1.0
        # María no tiene per-entity → fallback a project-level (0.97)
        # Ambos bajan, pero Pedro tiene su propia entrada per-entity
        assert weight_maria == pytest.approx(0.97, abs=0.001)
        # La clave: María no tiene fila per-entity propia, solo hereda project-level
        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            with db.connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM project_detector_weights "
                    "WHERE entity_canonical_name = 'maría'"
                ).fetchone()
                assert row[0] == 0  # María no tiene entrada propia

    def test_cascading_lookup_entity_over_project(self, tmp_path):
        """Per-entity weight toma precedencia sobre project-level."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Project-level: dismiss 5 veces → 0.85
            for _ in range(5):
                engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            engine.clear_adaptive_weights_cache()
            project_weight = engine._get_adaptive_weight(1, "attribute_inconsistency", "")
            assert project_weight == pytest.approx(0.85, abs=0.001)

            # Per-entity para "Pedro": dismiss 1 vez → entity_lr = 0.03/1 = 0.03 → 0.97
            engine.update_adaptive_weight(
                1, "attribute_inconsistency", dismissed=True, entity_names=["Pedro"]
            )

            engine.clear_adaptive_weights_cache()
            # Pedro tiene su propio peso per-entity → debería usarlo, no project-level
            weight_pedro = engine._get_adaptive_weight(1, "attribute_inconsistency", "Pedro")

        # Per-entity peso (0.97) toma precedencia sobre project-level (0.82)
        assert weight_pedro == pytest.approx(0.97, abs=0.001)

    def test_cascading_fallback_to_project_when_no_entity_data(self, tmp_path):
        """Sin datos per-entity, se usa el peso project-level."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Solo project-level
            for _ in range(3):
                engine.update_adaptive_weight(1, "attribute_inconsistency", dismissed=True)

            engine.clear_adaptive_weights_cache()
            # "María" no tiene datos per-entity → fallback a project-level
            weight = engine._get_adaptive_weight(1, "attribute_inconsistency", "María")

        # Project-level: 1.0 - 3*0.03 = 0.91
        assert weight == pytest.approx(0.91, abs=0.001)

    def test_multi_entity_fractional_learning_rate(self, tmp_path):
        """Alerta con 2 entidades divide learning rate entre ellas."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(
                1, "attribute_inconsistency", dismissed=True,
                entity_names=["Pedro", "María"],
            )

            engine.clear_adaptive_weights_cache()
            w_pedro = engine._get_adaptive_weight(1, "attribute_inconsistency", "pedro")
            w_maria = engine._get_adaptive_weight(1, "attribute_inconsistency", "maría")

        # Fractional LR: 0.03 / 2 = 0.015 per entity
        assert w_pedro == pytest.approx(1.0 - 0.015, abs=0.001)
        assert w_maria == pytest.approx(1.0 - 0.015, abs=0.001)

    def test_entity_name_case_insensitive(self, tmp_path):
        """Entity names se normalizan a lowercase."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(
                1, "voice_deviation", dismissed=True, entity_names=["PEDRO"]
            )

            engine.clear_adaptive_weights_cache()
            # Lookup con distinta capitalización
            weight = engine._get_adaptive_weight(1, "voice_deviation", "Pedro")

        assert weight < 1.0

    def test_per_entity_weight_applied_in_create_alert(self, tmp_path):
        """Per-entity weight se aplica al crear alerta via extra_data[entity_name]."""
        from narrative_assistant.alerts.engine import AlertEngine
        from narrative_assistant.alerts.models import AlertCategory, AlertSeverity
        from narrative_assistant.alerts.repository import AlertRepository
        from narrative_assistant.core.result import Result
        from narrative_assistant.persistence.database import Database

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
            # Dismiss Pedro 10 times → entity weight muy bajo
            for _ in range(10):
                engine.update_adaptive_weight(
                    1, "attribute_inconsistency", dismissed=True, entity_names=["Pedro"]
                )

            engine.clear_adaptive_weights_cache()

            engine.create_alert(
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="attribute_inconsistency",
                title="Pedro tiene pelo rubio",
                description="Antes dijiste que es moreno",
                explanation="Inconsistencia en el atributo pelo",
                confidence=0.8,
                extra_data={"entity_name": "Pedro"},
            )

        assert created_alert is not None
        # Per-entity weight for Pedro should reduce the confidence
        expected_entity_weight = 1.0 - 10 * (0.03 / 1)  # = 0.70
        assert created_alert.confidence == pytest.approx(0.8 * expected_entity_weight, abs=0.01)

    def test_different_entities_same_type_independent(self, tmp_path):
        """Pesos per-entity son independientes entre entidades para mismo alert_type."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            # Pedro: 5 dismissals
            for _ in range(5):
                engine.update_adaptive_weight(
                    1, "attribute_inconsistency", dismissed=True, entity_names=["Pedro"]
                )
            # María: 2 dismissals
            for _ in range(2):
                engine.update_adaptive_weight(
                    1, "attribute_inconsistency", dismissed=True, entity_names=["María"]
                )

            engine.clear_adaptive_weights_cache()
            w_pedro = engine._get_adaptive_weight(1, "attribute_inconsistency", "Pedro")
            w_maria = engine._get_adaptive_weight(1, "attribute_inconsistency", "María")

        # Pedro: 1.0 - 5*0.03 = 0.85, María: 1.0 - 2*0.03 = 0.94
        assert w_pedro == pytest.approx(0.85, abs=0.001)
        assert w_maria == pytest.approx(0.94, abs=0.001)

    def test_get_all_weights_includes_entity_info(self, tmp_path):
        """get_adaptive_weights devuelve info de entidad en el resultado."""
        db, engine = self._make_db_and_engine(tmp_path)

        with patch("narrative_assistant.persistence.database.get_database", return_value=db):
            engine.update_adaptive_weight(
                1, "attribute_inconsistency", dismissed=True, entity_names=["Pedro"]
            )
            engine.update_adaptive_weight(
                1, "voice_deviation", dismissed=True, entity_names=["María"]
            )

            weights = engine.get_adaptive_weights(1)

        # Should have project-level entries AND per-entity entries
        assert any(v.get("entity") == "pedro" for v in weights.values())
        assert any(v.get("entity") == "maría" for v in weights.values())

    def test_extract_entity_names_helper(self):
        """_extract_entity_names extrae nombres de extra_data."""
        from routers.alerts import _extract_entity_names

        # Con entity_name
        alert = MagicMock()
        alert.extra_data = {"entity_name": "Pedro"}
        assert _extract_entity_names(alert) == ["Pedro"]

        # Con entity1_name y entity2_name (relaciones)
        alert.extra_data = {"entity1_name": "Pedro", "entity2_name": "María"}
        names = _extract_entity_names(alert)
        assert "Pedro" in names
        assert "María" in names

        # Sin datos de entidad
        alert.extra_data = {}
        assert _extract_entity_names(alert) == []

        # extra_data None
        alert.extra_data = None
        assert _extract_entity_names(alert) == []


# ============================================================================
# Entity merge weight transfer tests
# ============================================================================


class TestEntityMergeWeightTransfer:
    """Tests para la transferencia de pesos al fusionar entidades."""

    def test_merge_transfers_weights(self, tmp_path):
        """Al fusionar entidades, los pesos se transfieren al target."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            # Create source and target entities
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type, mention_count) "
                "VALUES (10, 1, 'Pedro García', 'CHARACTER', 5)"
            )
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type, mention_count) "
                "VALUES (20, 1, 'Pedro', 'CHARACTER', 3)"
            )
            # Source entity has adaptive weight
            conn.execute(
                "INSERT INTO project_detector_weights "
                "(project_id, alert_type, entity_canonical_name, weight, "
                "feedback_count, dismiss_count, confirm_count) "
                "VALUES (1, 'attribute_inconsistency', 'pedro garcía', 0.7, 10, 8, 2)"
            )
            conn.commit()

        from narrative_assistant.entities.repository import EntityRepository
        repo = EntityRepository(db)
        repo.move_related_data(from_entity_id=10, to_entity_id=20)

        # Check that weight was transferred to target entity name
        with db.connection() as conn:
            row = conn.execute(
                "SELECT weight, feedback_count FROM project_detector_weights "
                "WHERE project_id = 1 AND entity_canonical_name = 'pedro'"
            ).fetchone()
            # Source didn't conflict → just rename
            assert row is not None
            assert row[0] == pytest.approx(0.7)
            assert row[1] == 10

            # Source should be gone
            src = conn.execute(
                "SELECT COUNT(*) FROM project_detector_weights "
                "WHERE entity_canonical_name = 'pedro garcía'"
            ).fetchone()
            assert src[0] == 0

    def test_merge_weighted_average_on_conflict(self, tmp_path):
        """Si ambas entidades tienen pesos, se hace media ponderada."""
        from narrative_assistant.persistence.database import Database

        db = Database(db_path=tmp_path / "test.db")
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type, mention_count) "
                "VALUES (10, 1, 'Pedro García', 'CHARACTER', 5)"
            )
            conn.execute(
                "INSERT INTO entities (id, project_id, canonical_name, entity_type, mention_count) "
                "VALUES (20, 1, 'Pedro', 'CHARACTER', 3)"
            )
            # Both entities have weights for same alert type
            conn.execute(
                "INSERT INTO project_detector_weights "
                "(project_id, alert_type, entity_canonical_name, weight, "
                "feedback_count, dismiss_count, confirm_count) "
                "VALUES (1, 'attribute_inconsistency', 'pedro garcía', 0.7, 10, 8, 2)"
            )
            conn.execute(
                "INSERT INTO project_detector_weights "
                "(project_id, alert_type, entity_canonical_name, weight, "
                "feedback_count, dismiss_count, confirm_count) "
                "VALUES (1, 'attribute_inconsistency', 'pedro', 0.9, 5, 3, 2)"
            )
            conn.commit()

        from narrative_assistant.entities.repository import EntityRepository
        repo = EntityRepository(db)
        repo.move_related_data(from_entity_id=10, to_entity_id=20)

        with db.connection() as conn:
            row = conn.execute(
                "SELECT weight, feedback_count, dismiss_count, confirm_count "
                "FROM project_detector_weights "
                "WHERE project_id = 1 AND entity_canonical_name = 'pedro'"
            ).fetchone()
            assert row is not None
            # Weighted average: (0.7*10 + 0.9*5) / 15 = 11.5/15 ≈ 0.7667
            assert row[0] == pytest.approx(0.7667, abs=0.01)
            assert row[1] == 15  # feedback_count sumados
            assert row[2] == 11  # dismiss_count sumados
            assert row[3] == 4   # confirm_count sumados


# ============================================================================
# v23 → v24 migration test
# ============================================================================


class TestV23ToV24Migration:
    """Test que la migración de v23 (sin entity_canonical_name) a v24 funciona."""

    def test_migration_adds_entity_column(self, tmp_path):
        """Simular BD v23 y verificar que la migración reconstruye la tabla."""
        # Primero crear una BD completa v24 para tener todas las tablas
        from narrative_assistant.persistence.database import Database
        db_path = tmp_path / "test_v23.db"
        db = Database(db_path=db_path)

        # Ahora simular "v23" rebajando la tabla project_detector_weights
        with db.connection() as conn:
            conn.execute(_INSERT_PROJECT, (1, "Test", 5000, 10))
            # Drop v24 table and recreate as v23 (without entity_canonical_name)
            conn.execute("DROP TABLE IF EXISTS project_detector_weights")
            conn.execute("""CREATE TABLE project_detector_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                feedback_count INTEGER NOT NULL DEFAULT 0,
                dismiss_count INTEGER NOT NULL DEFAULT 0,
                confirm_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE (project_id, alert_type)
            )""")
            conn.execute(
                "INSERT INTO project_detector_weights (project_id, alert_type, weight, "
                "feedback_count, dismiss_count, confirm_count) "
                "VALUES (1, 'attribute_inconsistency', 0.7, 10, 8, 2)"
            )
            conn.commit()

        # Reopen with Database (triggers migrations)
        db2 = Database(db_path=db_path)

        with db2.connection() as conn:
            cols = conn.execute("PRAGMA table_info(project_detector_weights)").fetchall()
            col_names = {c[1] for c in cols}
            assert "entity_canonical_name" in col_names

            # Datos preservados
            row = conn.execute(
                "SELECT weight, feedback_count, entity_canonical_name "
                "FROM project_detector_weights "
                "WHERE project_id = 1 AND alert_type = 'attribute_inconsistency'"
            ).fetchone()
            assert row is not None
            assert row[0] == pytest.approx(0.7)
            assert row[1] == 10
            assert row[2] == ""  # Migrated rows get empty string
