"""
Tests unitarios para PipelineAlertsMixin (ua_alerts.py).

Objetivo: Subir coverage de 3% a >40%.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity
from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin
from narrative_assistant.pipelines.unified_analysis import AnalysisContext


class MockPipeline(PipelineAlertsMixin):
    """Pipeline mock para testear el mixin."""

    def __init__(self):
        self.config = Mock()
        self._memory_monitor = Mock()


@pytest.fixture
def pipeline():
    """Fixture: pipeline con mixin."""
    return MockPipeline()


@pytest.fixture
def context():
    """Fixture: contexto de análisis básico."""
    ctx = Mock(spec=AnalysisContext)
    ctx.project_id = 1
    ctx.entity_map = {"juan": 1, "maría": 2}
    ctx.inconsistencies = []
    ctx.alerts = []
    ctx.temporal_issues = []
    ctx.temporal_inconsistencies = []
    ctx.ooc_events = []
    ctx.knowledge_issues = []
    ctx.contradictions = []
    ctx.location_issues = []
    # Todas las listas que _generate_all_alerts recorre
    ctx.spelling_issues = []
    ctx.grammar_issues = []
    ctx.lexical_repetitions = []
    ctx.semantic_repetitions = []
    ctx.coherence_breaks = []
    ctx.voice_deviations = []
    ctx.pacing_analysis = {}
    ctx.sticky_sentences = []
    ctx.passive_sentences = []
    ctx.complex_sentences = []
    ctx.filler_words = []
    ctx.typography_issues = []
    ctx.pov_shifts = []
    ctx.reference_issues = []
    ctx.acronym_issues = []
    ctx.adverb_issues = []
    ctx.cliche_issues = []
    ctx.show_dont_tell_issues = []
    ctx.sensory_gaps = []
    ctx.dialogue_tags = []
    ctx.anglicism_issues = []
    ctx.clarity_issues = []
    ctx.register_issues = []
    ctx.register_changes = []
    ctx.emotional_incoherences = []
    ctx.entities = []
    return ctx


class TestGenerateAlertsFromAttributeInconsistencies:
    """Tests para generación de alertas desde inconsistencias de atributos."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_from_single_inconsistency(self, mock_engine, pipeline, context):
        """Genera alerta desde una inconsistencia de atributo."""
        # Setup
        inc = Mock()
        inc.entity_name = "Juan"
        inc.attribute_key = Mock(value="eye_color")
        inc.value1 = "azul"
        inc.value2 = "verde"
        inc.value1_chapter = 1
        inc.value2_chapter = 3
        inc.value1_excerpt = "ojos azules"
        inc.value2_excerpt = "ojos verdes"
        inc.value1_position = 100
        inc.value2_position = 500
        inc.explanation = "Color de ojos inconsistente"
        inc.confidence = 0.9
        context.inconsistencies = [inc]

        alert = Mock(spec=Alert)
        mock_engine.return_value.create_from_attribute_inconsistency.return_value = Mock(
            is_success=True, value=alert
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify
        assert len(context.alerts) == 1
        assert context.alerts[0] == alert
        mock_engine.return_value.create_from_attribute_inconsistency.assert_called_once()

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_skips_failed_creation(self, mock_engine, pipeline, context):
        """No añade alerta si create_from_* falla."""
        inc = Mock()
        inc.entity_name = "Juan"
        inc.attribute_key = Mock(value="age")
        inc.value1 = "25"
        inc.value2 = "30"
        inc.value1_chapter = 1
        inc.value2_chapter = 2
        inc.value1_excerpt = "25 años"
        inc.value2_excerpt = "30 años"
        inc.value1_position = 10
        inc.value2_position = 50
        inc.explanation = "Edad inconsistente"
        inc.confidence = 0.8
        context.inconsistencies = [inc]

        mock_engine.return_value.create_from_attribute_inconsistency.return_value = Mock(
            is_success=False, error=Mock()
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify
        assert len(context.alerts) == 0


class TestGenerateAlertsFromTemporalIssues:
    """Tests para generación de alertas desde issues temporales."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_temporal_alerts(self, mock_engine, pipeline, context):
        """Genera alertas desde temporal_inconsistencies."""
        issue = Mock()
        issue.inconsistency_type = Mock(value="age_contradiction")
        issue.description = "Edad inconsistente con fecha de nacimiento"
        issue.chapter = 2
        issue.position = 200
        issue.confidence = 0.85
        issue.suggestion = "Verificar fechas"
        issue.expected = "25 años"
        issue.found = "30 años"
        issue.severity = Mock(value="high")
        issue.methods_agreed = ["temporal_map", "heuristic"]
        context.temporal_inconsistencies = [issue]

        alert = Mock(spec=Alert)
        mock_engine.return_value.create_from_temporal_inconsistency.return_value = Mock(
            is_success=True, value=alert
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify
        assert len(context.alerts) == 1


class TestGenerateAlertsFromOOC:
    """Tests para generación de alertas desde eventos OOC."""

    @pytest.mark.skip(reason="WIP - need to fix OOC event structure")
    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_ooc_alerts(self, mock_engine, pipeline, context):
        """Genera alertas desde ooc_events."""
        ooc = {
            "entity_name": "Pedro",
            "entity_id": 1,
            "ooc_type": "behavioral",
            "severity": "warning",
            "chapter": 5,
            "excerpt": "Pedro actuó de forma extraña",
            "position": 1000,
            "explanation": "Comportamiento fuera de carácter",
            "confidence": 0.7,
            "expected_behavior": "Pedro es siempre calmado",
            "observed_behavior": "Pedro gritó furiosamente"
        }
        context.ooc_events = [ooc]

        alert = Mock(spec=Alert)
        mock_engine.return_value.create_alert.return_value = Mock(
            is_success=True, value=alert
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify
        assert len(context.alerts) == 1


class TestGenerateAlertsErrorHandling:
    """Tests de manejo de errores en generación de alertas."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_continues_after_single_alert_failure(self, mock_engine, pipeline, context):
        """Continúa generando alertas aunque falle una."""
        inc1 = Mock()
        inc1.entity_name = "A"
        inc1.attribute_key = Mock(value="x")
        inc1.value1 = "1"
        inc1.value2 = "2"
        inc1.value1_chapter = 1
        inc1.value2_chapter = 2
        inc1.value1_excerpt = "x"
        inc1.value2_excerpt = "y"
        inc1.value1_position = 0
        inc1.value2_position = 10
        inc1.explanation = "test"
        inc1.confidence = 0.9

        inc2 = Mock()
        inc2.entity_name = "B"
        inc2.attribute_key = Mock(value="y")
        inc2.value1 = "3"
        inc2.value2 = "4"
        inc2.value1_chapter = 1
        inc2.value2_chapter = 2
        inc2.value1_excerpt = "z"
        inc2.value2_excerpt = "w"
        inc2.value1_position = 20
        inc2.value2_position = 30
        inc2.explanation = "test2"
        inc2.confidence = 0.8

        context.inconsistencies = [inc1, inc2]

        alert2 = Mock(spec=Alert)
        mock_engine.return_value.create_from_attribute_inconsistency.side_effect = [
            Mock(is_success=False, error=Mock()),  # Primera falla
            Mock(is_success=True, value=alert2)     # Segunda funciona
        ]

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify - debe haber 1 alerta (la segunda)
        assert len(context.alerts) == 1
        assert context.alerts[0] == alert2


class TestEntityMapping:
    """Tests para mapeo de entity_name → entity_id."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_maps_entity_name_to_id_correctly(self, mock_engine, pipeline, context):
        """Mapea entity_name correctamente usando entity_map."""
        inc = Mock()
        inc.entity_name = "María"
        inc.attribute_key = Mock(value="test")
        inc.value1 = "a"
        inc.value2 = "b"
        inc.value1_chapter = 1
        inc.value2_chapter = 2
        inc.value1_excerpt = "x"
        inc.value2_excerpt = "y"
        inc.value1_position = 0
        inc.value2_position = 10
        inc.explanation = "test"
        inc.confidence = 0.9
        context.inconsistencies = [inc]
        context.entity_map = {"maría": 42}  # lowercase en el map

        mock_engine.return_value.create_from_attribute_inconsistency.return_value = Mock(
            is_success=True, value=Mock()
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify - debe pasar entity_id=42
        call_kwargs = mock_engine.return_value.create_from_attribute_inconsistency.call_args[1]
        assert call_kwargs['entity_id'] == 42

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_defaults_to_zero_if_entity_not_in_map(self, mock_engine, pipeline, context):
        """Usa entity_id=0 si la entidad no está en el map."""
        inc = Mock()
        inc.entity_name = "Desconocido"
        inc.attribute_key = Mock(value="test")
        inc.value1 = "a"
        inc.value2 = "b"
        inc.value1_chapter = 1
        inc.value2_chapter = 2
        inc.value1_excerpt = "x"
        inc.value2_excerpt = "y"
        inc.value1_position = 0
        inc.value2_position = 10
        inc.explanation = "test"
        inc.confidence = 0.9
        context.inconsistencies = [inc]
        context.entity_map = {}

        mock_engine.return_value.create_from_attribute_inconsistency.return_value = Mock(
            is_success=True, value=Mock()
        )

        # Execute
        pipeline._generate_all_alerts(context)

        # Verify
        call_kwargs = mock_engine.return_value.create_from_attribute_inconsistency.call_args[1]
        assert call_kwargs['entity_id'] == 0
