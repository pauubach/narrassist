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
