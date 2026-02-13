"""
Tests unitarios para AlertEngine.

Estos tests verifican que AlertEngine crea alertas correctamente
desde diferentes tipos de datos de entrada (inconsistencias, errores gramaticales, etc.)
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from narrative_assistant.alerts.engine import AlertEngine, get_alert_engine
from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity, AlertStatus
from narrative_assistant.analysis.attribute_consistency import (
    AttributeInconsistency,
    AttributeKey,
    InconsistencyType,
)
from narrative_assistant.core.result import Result


class TestAlertEngineCreateFromAttributeInconsistency:
    """Tests para create_from_attribute_inconsistency."""

    @pytest.fixture
    def mock_repo(self):
        """Mock del repositorio de alertas."""
        repo = Mock()
        repo.create.return_value = Result.success(
            Alert(
                id=1,
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="attribute_inconsistency",
                title="Test Alert",
                description="Test description",
                explanation="Test explanation",
                entity_ids=[1],
                confidence=0.9,
                source_module="test",
            )
        )
        return repo

    @pytest.fixture
    def engine(self, mock_repo):
        """AlertEngine con repo mockeado."""
        engine = AlertEngine.__new__(AlertEngine)
        engine.repo = mock_repo
        return engine

    def test_create_from_attribute_inconsistency_with_correct_params(self, engine):
        """
        Verifica que create_from_attribute_inconsistency funciona con parámetros correctos.

        Este test habría detectado el bug donde se pasaba inconsistency=inc
        en lugar de los parámetros individuales.
        """
        result = engine.create_from_attribute_inconsistency(
            project_id=1,
            entity_name="María",
            entity_id=1,
            attribute_key="eye_color",
            value1="azules",
            value2="verdes",
            value1_source={
                "chapter": 1,
                "excerpt": "sus ojos azules",
                "start_char": 100,
            },
            value2_source={
                "chapter": 3,
                "excerpt": "sus ojos verdes",
                "start_char": 5000,
            },
            explanation="El color de ojos de María cambia",
            confidence=0.9,
        )

        assert result.is_success
        # Verificar que se llamó al repo.create
        engine.repo.create.assert_called_once()

    def test_create_from_attribute_inconsistency_without_positional_inconsistency(
        self, engine
    ):
        """
        Verifica que NO se puede pasar un objeto AttributeInconsistency directamente.

        Este es el patrón de error que encontramos - debe fallar si se intenta.
        """
        inconsistency = AttributeInconsistency(
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR,
            value1="azules",
            value1_chapter=1,
            value1_excerpt="ojos azules",
            value2="verdes",
            value2_chapter=3,
            value2_excerpt="ojos verdes",
            confidence=0.9,
            explanation="Color cambia",
        )

        # El método NO debe aceptar un parámetro 'inconsistency'
        # Este test verifica que la firma del método es correcta
        import inspect

        sig = inspect.signature(engine.create_from_attribute_inconsistency)
        param_names = list(sig.parameters.keys())

        assert (
            "inconsistency" not in param_names
        ), "create_from_attribute_inconsistency no debe tener parámetro 'inconsistency'"

    def test_create_from_attribute_inconsistency_all_params_required(self, engine):
        """Verifica que todos los parámetros requeridos están presentes."""
        import inspect

        sig = inspect.signature(engine.create_from_attribute_inconsistency)

        required_params = [
            "project_id",
            "entity_name",
            "entity_id",
            "attribute_key",
            "value1",
            "value2",
            "value1_source",
            "value2_source",
            "explanation",
        ]

        param_names = list(sig.parameters.keys())
        for param in required_params:
            assert param in param_names, f"Falta parámetro requerido: {param}"

    def test_create_from_attribute_inconsistency_with_attribute_key_enum(self, engine):
        """
        Verifica que funciona con AttributeKey como string (después de .value).

        Esto es importante porque AttributeInconsistency tiene attribute_key como enum.
        """
        result = engine.create_from_attribute_inconsistency(
            project_id=1,
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR.value,  # "eye_color" como string
            value1="azules",
            value2="verdes",
            value1_source={"chapter": 1, "excerpt": "test"},
            value2_source={"chapter": 2, "excerpt": "test"},
            explanation="Test",
            confidence=0.8,
        )

        assert result.is_success


class TestAlertEngineIntegrationWithInconsistency:
    """
    Tests de integración que simulan el flujo real del análisis.

    Estos tests verifican que los datos de AttributeInconsistency
    se pueden convertir correctamente a los parámetros de AlertEngine.
    """

    def test_inconsistency_to_alert_params_mapping(self):
        """
        Verifica que AttributeInconsistency tiene todos los campos
        necesarios para crear una alerta.
        """
        inconsistency = AttributeInconsistency(
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR,
            value1="azules",
            value1_chapter=1,
            value1_excerpt="ojos azules brillantes",
            value1_position=100,
            value2="verdes",
            value2_chapter=3,
            value2_excerpt="ojos verdes profundos",
            value2_position=5000,
            confidence=0.9,
            explanation="El color de ojos cambia entre capítulos",
        )

        # Verificar que podemos extraer todos los datos necesarios
        assert inconsistency.entity_name == "María"
        assert inconsistency.entity_id == 1
        assert inconsistency.attribute_key.value == "eye_color"
        assert inconsistency.value1 == "azules"
        assert inconsistency.value2 == "verdes"
        assert inconsistency.value1_chapter == 1
        assert inconsistency.value2_chapter == 3
        assert inconsistency.value1_excerpt == "ojos azules brillantes"
        assert inconsistency.value2_excerpt == "ojos verdes profundos"
        assert inconsistency.value1_position == 100
        assert inconsistency.value2_position == 5000
        assert inconsistency.confidence == 0.9
        assert inconsistency.explanation == "El color de ojos cambia entre capítulos"

    def test_correct_conversion_pattern(self):
        """
        Demuestra el patrón correcto para convertir AttributeInconsistency
        a parámetros de AlertEngine.

        Este es el código que debería usarse en main.py y pipelines.
        """
        inc = AttributeInconsistency(
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR,
            value1="azules",
            value1_chapter=1,
            value1_excerpt="ojos azules",
            value1_position=100,
            value2="verdes",
            value2_chapter=3,
            value2_excerpt="ojos verdes",
            value2_position=5000,
            confidence=0.9,
            explanation="Color cambia",
        )

        # CORRECTO: Extraer campos individuales
        params = {
            "project_id": 1,  # Viene del contexto
            "entity_name": inc.entity_name,
            "entity_id": inc.entity_id,
            "attribute_key": (
                inc.attribute_key.value
                if hasattr(inc.attribute_key, "value")
                else str(inc.attribute_key)
            ),
            "value1": inc.value1,
            "value2": inc.value2,
            "value1_source": {
                "chapter": inc.value1_chapter,
                "excerpt": inc.value1_excerpt,
                "start_char": inc.value1_position,
            },
            "value2_source": {
                "chapter": inc.value2_chapter,
                "excerpt": inc.value2_excerpt,
                "start_char": inc.value2_position,
            },
            "explanation": inc.explanation,
            "confidence": inc.confidence,
        }

        # Verificar que todos los campos requeridos están presentes
        required = [
            "project_id",
            "entity_name",
            "entity_id",
            "attribute_key",
            "value1",
            "value2",
            "value1_source",
            "value2_source",
            "explanation",
            "confidence",
        ]

        for field in required:
            assert field in params, f"Falta campo: {field}"
            assert params[field] is not None, f"Campo {field} es None"


class TestAlertEngineGrammarIssues:
    """Tests para create_from_grammar_issue."""

    @pytest.fixture
    def mock_repo(self):
        """Mock del repositorio."""
        repo = Mock()
        repo.create.return_value = Result.success(
            Alert(
                id=1,
                project_id=1,
                category=AlertCategory.GRAMMAR,
                severity=AlertSeverity.INFO,
                alert_type="grammar_error",
                title="Error gramatical",
                description="Test",
                explanation="Test",
                entity_ids=[],
                confidence=0.8,
                source_module="grammar",
            )
        )
        return repo

    @pytest.fixture
    def engine(self, mock_repo):
        """AlertEngine con repo mockeado."""
        engine = AlertEngine.__new__(AlertEngine)
        engine.repo = mock_repo
        return engine

    def test_create_from_grammar_issue(self, engine):
        """Verifica creación de alerta desde error gramatical."""
        result = engine.create_from_grammar_issue(
            project_id=1,
            text="habia",
            start_char=100,
            end_char=105,
            sentence="El habia ido al parque.",
            error_type="accent",
            suggestion="había",
            confidence=0.95,
            explanation="Falta tilde en 'había'",
        )

        assert result.is_success
        engine.repo.create.assert_called_once()


class TestConfidenceDecay:
    """Tests para BK-18: Decay temporal de confianza."""

    @pytest.fixture
    def engine(self):
        """AlertEngine con repo mockeado y total_chapters inyectado."""
        repo = Mock()
        repo.create.side_effect = lambda alert: Result.success(alert)
        engine = AlertEngine.__new__(AlertEngine)
        engine.repo = repo
        engine.alert_handlers = {}
        engine._calibration_cache = {}
        engine._total_chapters_cache = {}
        return engine

    def test_decay_nearby_chapter(self, engine):
        """Alerta en capítulo cercano al último → poca pérdida de confianza."""
        result = engine.create_alert(
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="attribute_inconsistency",
            title="Test",
            description="desc",
            explanation="expl",
            confidence=0.9,
            chapter=9,
            _total_chapters=10,  # distance = 1
        )
        assert result.is_success
        alert = result.value
        # 0.9 * 0.97^1 = 0.873
        assert alert.confidence >= 0.85
        assert alert.confidence < 0.9

    def test_decay_distant_chapter(self, engine):
        """Alerta en capítulo 1 de un libro de 50 capítulos → mucha pérdida."""
        result = engine.create_alert(
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="attribute_inconsistency",
            title="Test",
            description="desc",
            explanation="expl",
            confidence=0.9,
            chapter=1,
            _total_chapters=50,  # distance = 49
        )
        assert result.is_success
        alert = result.value
        # 0.9 * 0.97^49 ≈ 0.9 * 0.218 ≈ 0.196
        assert alert.confidence < 0.3
        assert alert.confidence >= AlertEngine.DECAY_FLOOR

    def test_no_decay_for_grammar(self, engine):
        """Alertas de gramática NO aplican decay temporal."""
        result = engine.create_alert(
            project_id=1,
            category=AlertCategory.GRAMMAR,
            severity=AlertSeverity.INFO,
            alert_type="grammar_error",
            title="Test",
            description="desc",
            explanation="expl",
            confidence=0.9,
            chapter=1,
            _total_chapters=50,
        )
        assert result.is_success
        alert = result.value
        # Sin decay → confianza original (solo calibración, factor=1.0)
        assert alert.confidence == 0.9
