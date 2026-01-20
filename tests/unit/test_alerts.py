"""
Tests unitarios para el sistema de alertas.

Estos tests verifican los modelos, filtros y repositorio de alertas.
"""

import pytest
from datetime import datetime

from narrative_assistant.alerts.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertFilter,
)
from narrative_assistant.alerts.repository import AlertRepository, get_alert_repository


class TestAlertModels:
    """Tests para los modelos de alertas."""

    def test_alert_severity_enum(self):
        """Verifica el enum de severidad."""
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.HINT.value == "hint"

    def test_alert_category_enum(self):
        """Verifica el enum de categorías."""
        assert AlertCategory.CONSISTENCY.value == "consistency"
        assert AlertCategory.STYLE.value == "style"
        assert AlertCategory.FOCALIZATION.value == "focalization"
        assert AlertCategory.STRUCTURE.value == "structure"

    def test_alert_status_enum(self):
        """Verifica el enum de estados."""
        assert AlertStatus.NEW.value == "new"
        assert AlertStatus.OPEN.value == "open"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.DISMISSED.value == "dismissed"

    def test_create_alert(self):
        """Crea una alerta básica."""
        alert = Alert(
            id=1,
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.CRITICAL,
            alert_type="attribute_inconsistency",
            title="Color de ojos inconsistente",
            description="María: 'verdes' vs 'azules'",
            explanation="El color de ojos de María cambia entre capítulos.",
            suggestion="Verificar cuál es el color correcto",
            chapter=1,
            entity_ids=[1],
            confidence=0.95,
            source_module="attribute_consistency",
        )

        assert alert.id == 1
        assert alert.project_id == 1
        assert alert.category == AlertCategory.CONSISTENCY
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.alert_type == "attribute_inconsistency"
        assert alert.confidence == 0.95
        assert alert.is_open()
        assert not alert.is_closed()

    def test_alert_to_dict(self):
        """Convierte alerta a diccionario."""
        alert = Alert(
            id=1,
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="timeline_error",
            title="Error temporal",
            description="Inconsistencia en la línea temporal",
            explanation="Explicación detallada",
        )

        data = alert.to_dict()

        assert data["id"] == 1
        assert data["category"] == "consistency"
        assert data["severity"] == "warning"
        assert data["alert_type"] == "timeline_error"
        assert data["status"] == "new"

    def test_alert_from_dict(self):
        """Crea alerta desde diccionario."""
        data = {
            "id": 2,
            "project_id": 1,
            "category": "consistency",
            "severity": "critical",
            "alert_type": "attribute_inconsistency",
            "title": "Test Alert",
            "description": "Test description",
            "explanation": "Test explanation",
            "suggestion": None,
            "chapter": 1,
            "scene": None,
            "start_char": 100,
            "end_char": 200,
            "excerpt": "texto de ejemplo",
            "entity_ids": [1, 2],
            "confidence": 0.9,
            "source_module": "test",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
            "status": "new",
            "resolved_at": None,
            "resolution_note": "",
            "extra_data": {},
        }

        alert = Alert.from_dict(data)

        assert alert.id == 2
        assert alert.category == AlertCategory.CONSISTENCY
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.entity_ids == [1, 2]
        assert alert.confidence == 0.9

    def test_alert_is_open(self):
        """Verifica estado abierto."""
        alert = Alert(
            id=1,
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test",
            title="Test",
            description="Test",
            explanation="Test",
            status=AlertStatus.NEW,
        )
        assert alert.is_open()

        alert.status = AlertStatus.IN_PROGRESS
        assert alert.is_open()

        alert.status = AlertStatus.RESOLVED
        assert not alert.is_open()
        assert alert.is_closed()

    def test_alert_is_closed(self):
        """Verifica estado cerrado."""
        alert = Alert(
            id=1,
            project_id=1,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test",
            title="Test",
            description="Test",
            explanation="Test",
            status=AlertStatus.DISMISSED,
        )
        assert alert.is_closed()
        assert not alert.is_open()


class TestAlertFilter:
    """Tests para filtros de alertas."""

    @pytest.fixture
    def sample_alerts(self):
        """Crea un conjunto de alertas de prueba."""
        return [
            Alert(
                id=1,
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.CRITICAL,
                alert_type="attribute_inconsistency",
                title="Alert 1",
                description="Desc 1",
                explanation="Exp 1",
                chapter=1,
                entity_ids=[1],
                confidence=0.95,
            ),
            Alert(
                id=2,
                project_id=1,
                category=AlertCategory.STYLE,
                severity=AlertSeverity.WARNING,
                alert_type="repetition",
                title="Alert 2",
                description="Desc 2",
                explanation="Exp 2",
                chapter=2,
                entity_ids=[2],
                confidence=0.7,
            ),
            Alert(
                id=3,
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.INFO,
                alert_type="timeline_warning",
                title="Alert 3",
                description="Desc 3",
                explanation="Exp 3",
                chapter=1,
                entity_ids=[1, 3],
                confidence=0.5,
            ),
        ]

    def test_filter_by_category(self, sample_alerts):
        """Filtra por categoría."""
        filter_ = AlertFilter(categories=[AlertCategory.CONSISTENCY])

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 2
        assert all(a.category == AlertCategory.CONSISTENCY for a in matching)

    def test_filter_by_severity(self, sample_alerts):
        """Filtra por severidad."""
        filter_ = AlertFilter(severities=[AlertSeverity.CRITICAL])

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 1
        assert matching[0].severity == AlertSeverity.CRITICAL

    def test_filter_by_chapter(self, sample_alerts):
        """Filtra por capítulo."""
        filter_ = AlertFilter(chapters=[1])

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 2
        assert all(a.chapter == 1 for a in matching)

    def test_filter_by_entity_ids(self, sample_alerts):
        """Filtra por IDs de entidad."""
        filter_ = AlertFilter(entity_ids=[1])

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 2
        assert all(1 in a.entity_ids for a in matching)

    def test_filter_by_confidence(self, sample_alerts):
        """Filtra por confianza mínima."""
        filter_ = AlertFilter(min_confidence=0.8)

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 1
        assert matching[0].confidence >= 0.8

    def test_filter_combined(self, sample_alerts):
        """Filtra con múltiples criterios."""
        filter_ = AlertFilter(
            categories=[AlertCategory.CONSISTENCY],
            severities=[AlertSeverity.CRITICAL, AlertSeverity.WARNING],
            min_confidence=0.9,
        )

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == 1
        assert matching[0].id == 1

    def test_empty_filter_matches_all(self, sample_alerts):
        """Filtro vacío coincide con todas."""
        filter_ = AlertFilter()

        matching = [a for a in sample_alerts if filter_.matches(a)]

        assert len(matching) == len(sample_alerts)


class TestAlertRepository:
    """Tests para el repositorio de alertas."""

    def test_repository_singleton(self):
        """Verifica que el repositorio es singleton."""
        repo1 = get_alert_repository()
        repo2 = get_alert_repository()

        assert repo1 is repo2

    def test_repository_instance(self):
        """Verifica que el repositorio se puede instanciar."""
        repo = get_alert_repository()
        assert repo is not None
        assert hasattr(repo, "create")
        assert hasattr(repo, "get")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "get_by_project")


class TestAlertEngine:
    """Tests para el motor de alertas."""

    @pytest.fixture
    def engine(self):
        """Crea un motor de alertas para tests."""
        from narrative_assistant.alerts.engine import AlertEngine
        from unittest.mock import MagicMock

        # Mock del repositorio para evitar DB real
        mock_repo = MagicMock()
        mock_repo.create.return_value = MagicMock(
            is_success=True,
            value=Alert(
                id=1,
                project_id=1,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="test",
                title="Test",
                description="Test",
                explanation="Test",
            )
        )
        return AlertEngine(repository=mock_repo)

    def test_calculate_severity_from_confidence(self, engine):
        """Test calculo automatico de severidad."""
        assert engine.calculate_severity_from_confidence(0.95) == AlertSeverity.CRITICAL
        assert engine.calculate_severity_from_confidence(0.75) == AlertSeverity.WARNING
        assert engine.calculate_severity_from_confidence(0.55) == AlertSeverity.INFO
        assert engine.calculate_severity_from_confidence(0.3) == AlertSeverity.HINT

    def test_create_from_temporal_inconsistency(self, engine):
        """Test creacion de alerta temporal."""
        result = engine.create_from_temporal_inconsistency(
            project_id=1,
            inconsistency_type="timeline_gap",
            description="Salto temporal inexplicado",
            explanation="Hay una semana sin explicar entre eventos",
            chapter=3,
            start_char=1000,
            end_char=1100,
            excerpt="texto de ejemplo",
            confidence=0.85,
        )

        # Verificamos que se llamo al repositorio
        engine.repo.create.assert_called_once()
        call_args = engine.repo.create.call_args[0][0]
        assert call_args.category == AlertCategory.TIMELINE_ISSUE
        assert call_args.alert_type == "temporal_timeline_gap"

    def test_create_from_voice_deviation(self, engine):
        """Test creacion de alerta de desviacion de voz."""
        result = engine.create_from_voice_deviation(
            project_id=1,
            entity_id=5,
            entity_name="Juan",
            deviation_type="formality_shift",
            expected_value="formal",
            actual_value="colloquial",
            description="Juan usa lenguaje coloquial inesperado",
            explanation="El perfil indica que Juan habla formalmente",
            chapter=2,
            start_char=500,
            end_char=600,
            excerpt="Bro, eso mola",
            confidence=0.75,
        )

        engine.repo.create.assert_called_once()
        call_args = engine.repo.create.call_args[0][0]
        assert call_args.category == AlertCategory.VOICE_DEVIATION
        assert call_args.entity_ids == [5]

    def test_create_from_register_change(self, engine):
        """Test creacion de alerta de cambio de registro."""
        result = engine.create_from_register_change(
            project_id=1,
            from_register="formal_literary",
            to_register="colloquial",
            severity_level="high",
            chapter=4,
            position=2000,
            context_before="Contempló la vastedad del horizonte",
            context_after="Bro, eso flipaba mogollón",
            explanation="Cambio abrupto de registro narrativo",
            confidence=0.8,
        )

        engine.repo.create.assert_called_once()
        call_args = engine.repo.create.call_args[0][0]
        assert call_args.category == AlertCategory.STYLE
        assert call_args.alert_type == "register_change"
        assert call_args.severity == AlertSeverity.WARNING  # high -> WARNING

    def test_create_from_focalization_violation(self, engine):
        """Test creacion de alerta de violacion de focalizacion."""
        result = engine.create_from_focalization_violation(
            project_id=1,
            violation_type="unauthorized_pov",
            declared_focalizer="María",
            violated_rule="No se puede acceder a pensamientos de otros personajes",
            description="Acceso a pensamientos de Juan desde perspectiva de María",
            explanation="María no debería saber qué piensa Juan",
            chapter=5,
            start_char=3000,
            end_char=3100,
            excerpt="Juan pensó que María era tonta",
            confidence=0.9,
            entity_ids=[1, 2],
        )

        engine.repo.create.assert_called_once()
        call_args = engine.repo.create.call_args[0][0]
        assert call_args.category == AlertCategory.FOCALIZATION
        assert "unauthorized_pov" in call_args.alert_type

    def test_create_from_speaker_attribution_unknown(self, engine):
        """Test creacion de alerta de hablante ambiguo."""
        result = engine.create_from_speaker_attribution(
            project_id=1,
            dialogue_text="No sé qué hacer con esto",
            chapter=1,
            start_char=100,
            end_char=130,
            attribution_confidence="unknown",
            possible_speakers=["María", "Juan"],
            context="Estaban solos en la habitación",
        )

        engine.repo.create.assert_called_once()
        call_args = engine.repo.create.call_args[0][0]
        assert call_args.category == AlertCategory.STYLE
        assert call_args.alert_type == "speaker_attribution_ambiguous"
        assert call_args.severity == AlertSeverity.WARNING  # unknown -> WARNING

    def test_create_from_speaker_attribution_high_confidence_skipped(self, engine):
        """Test que atribucion con alta confianza no genera alerta."""
        result = engine.create_from_speaker_attribution(
            project_id=1,
            dialogue_text="Hola María",
            chapter=1,
            start_char=100,
            end_char=110,
            attribution_confidence="high",  # Alta confianza
            possible_speakers=["Juan"],
            context="Juan dijo:",
        )

        # No debería llamar al repositorio
        engine.repo.create.assert_not_called()

    def test_prioritize_alerts(self, engine):
        """Test priorizacion de alertas."""
        alerts = [
            Alert(
                id=1, project_id=1, category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.INFO, alert_type="test", title="A",
                description="A", explanation="A", confidence=0.5, chapter=1
            ),
            Alert(
                id=2, project_id=1, category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.CRITICAL, alert_type="test", title="B",
                description="B", explanation="B", confidence=0.9, chapter=2
            ),
            Alert(
                id=3, project_id=1, category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING, alert_type="test", title="C",
                description="C", explanation="C", confidence=0.95, chapter=1
            ),
        ]

        sorted_alerts = engine.prioritize_alerts(alerts)

        # CRITICAL primero, luego WARNING, luego INFO
        assert sorted_alerts[0].severity == AlertSeverity.CRITICAL
        assert sorted_alerts[1].severity == AlertSeverity.WARNING
        assert sorted_alerts[2].severity == AlertSeverity.INFO
