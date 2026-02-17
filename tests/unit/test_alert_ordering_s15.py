"""
Tests para el ordenamiento de alertas (S15).

Verifica que las alertas se ordenen por:
1. Severidad (critical > warning > info > hint)
2. Confianza (mayor primero)
3. Posición en el texto (start_char o chapter)
4. Fecha de creación (más recientes primero)
"""

from datetime import datetime, timedelta

import pytest

from narrative_assistant.alerts.models import Alert, AlertCategory, AlertSeverity, AlertStatus
from narrative_assistant.alerts.repository import AlertRepository
from narrative_assistant.persistence.database import get_database


@pytest.fixture
def alert_repo():
    """Crea un repositorio de alertas limpio con proyecto de prueba."""
    db = get_database()

    # Crear proyecto de prueba (fuera de transaction para que persista)
    with db.transaction() as conn:
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM projects WHERE id = 999")
        conn.execute("""
            INSERT INTO projects (
                id, name, document_fingerprint, document_format,
                created_at, updated_at
            )
            VALUES (
                999, 'Test Project', 'test123', 'txt',
                datetime('now'), datetime('now')
            )
        """)

    return AlertRepository()


@pytest.fixture
def project_id():
    """ID de proyecto de prueba."""
    return 999


class TestAlertOrdering:
    """Tests para verificar el ordenamiento de alertas por severidad + posición."""

    def test_orden_por_severidad_primero(self, alert_repo, project_id):
        """
        Las alertas deben ordenarse por severidad PRIMERO, no por posición.

        Escenario:
        - Alert 1: INFO, chapter 1, pos 100
        - Alert 2: CRITICAL, chapter 10, pos 5000

        Resultado esperado: CRITICAL primero, luego INFO
        """
        now = datetime.now()

        # Crear alerta INFO en capítulo 1 (al principio del manuscrito)
        alert_info = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.STYLE,
            severity=AlertSeverity.INFO,
            alert_type="test_info",
            title="Info temprano",
            description="Esta alerta INFO está al principio del manuscrito",
            explanation="Pero tiene baja severidad",
            chapter=1,
            start_char=100,
            confidence=0.8,
            created_at=now,
            status=AlertStatus.NEW,
        )

        # Crear alerta CRITICAL en capítulo 10 (al final del manuscrito)
        alert_critical = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.GRAMMAR,
            severity=AlertSeverity.CRITICAL,
            alert_type="test_critical",
            title="Critical tardío",
            description="Esta alerta CRITICAL está al final del manuscrito",
            explanation="Pero tiene alta severidad",
            chapter=10,
            start_char=5000,
            confidence=0.9,
            created_at=now + timedelta(seconds=1),
            status=AlertStatus.NEW,
        )

        # Guardar alertas
        alert_repo.create(alert_info)
        alert_repo.create(alert_critical)

        # Obtener alertas priorizadas
        result = alert_repo.get_by_project_prioritized(project_id)
        assert result.is_success

        alerts = result.value
        assert len(alerts) == 2

        # CRITICAL debe venir PRIMERO, aunque esté al final del manuscrito
        assert alerts[0].severity == AlertSeverity.CRITICAL, \
            "Primera alerta debe ser CRITICAL (mayor severidad)"
        assert alerts[1].severity == AlertSeverity.INFO, \
            "Segunda alerta debe ser INFO (menor severidad)"

    def test_orden_por_confianza_dentro_misma_severidad(self, alert_repo, project_id):
        """
        Dentro de la misma severidad, ordenar por confianza (mayor primero).
        """
        now = datetime.now()

        # Crear dos alertas WARNING con diferente confianza
        alert_low_conf = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test_warning",
            title="Warning baja confianza",
            description="Confianza 0.6",
            explanation="Test",
            chapter=1,
            start_char=100,
            confidence=0.6,  # Baja confianza
            created_at=now,
            status=AlertStatus.NEW,
        )

        alert_high_conf = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test_warning",
            title="Warning alta confianza",
            description="Confianza 0.95",
            explanation="Test",
            chapter=1,
            start_char=200,
            confidence=0.95,  # Alta confianza
            created_at=now + timedelta(seconds=1),
            status=AlertStatus.NEW,
        )

        alert_repo.create(alert_low_conf)
        alert_repo.create(alert_high_conf)

        result = alert_repo.get_by_project_prioritized(project_id)
        assert result.is_success

        alerts = result.value
        assert len(alerts) == 2

        # Alta confianza debe venir primero
        assert alerts[0].confidence == 0.95, \
            "Primera alerta debe tener mayor confianza"
        assert alerts[1].confidence == 0.6, \
            "Segunda alerta debe tener menor confianza"

    def test_orden_por_posicion_dentro_misma_severidad_y_confianza(self, alert_repo, project_id):
        """
        Con misma severidad y confianza, ordenar por posición en el texto.
        """
        now = datetime.now()

        # Crear dos alertas WARNING con misma confianza pero diferente posición
        alert_final = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test_warning",
            title="Warning al final",
            description="Posición 5000",
            explanation="Test",
            chapter=10,
            start_char=5000,
            confidence=0.8,
            created_at=now,
            status=AlertStatus.NEW,
        )

        alert_inicio = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test_warning",
            title="Warning al inicio",
            description="Posición 100",
            explanation="Test",
            chapter=1,
            start_char=100,
            confidence=0.8,
            created_at=now + timedelta(seconds=1),
            status=AlertStatus.NEW,
        )

        alert_repo.create(alert_final)
        alert_repo.create(alert_inicio)

        result = alert_repo.get_by_project_prioritized(project_id)
        assert result.is_success

        alerts = result.value
        assert len(alerts) == 2

        # Posición temprana debe venir primero
        assert alerts[0].start_char == 100, \
            "Primera alerta debe estar al inicio del texto"
        assert alerts[1].start_char == 5000, \
            "Segunda alerta debe estar al final del texto"

    def test_orden_completo_severidad_confianza_posicion(self, alert_repo, project_id):
        """
        Test integrado: severidad > confianza > posición.

        Escenario:
        1. INFO, conf 0.9, pos 100
        2. WARNING, conf 0.6, pos 200
        3. WARNING, conf 0.9, pos 300
        4. CRITICAL, conf 0.7, pos 400

        Orden esperado:
        1. CRITICAL (pos 400) - severidad más alta
        2. WARNING conf 0.9 (pos 300) - segunda severidad, mayor confianza
        3. WARNING conf 0.6 (pos 200) - segunda severidad, menor confianza
        4. INFO (pos 100) - severidad más baja
        """
        now = datetime.now()

        alerts_to_create = [
            Alert(
                id=0,
                project_id=project_id,
                category=AlertCategory.STYLE,
                severity=AlertSeverity.INFO,
                alert_type="test",
                title="1. INFO conf 0.9",
                description="Test",
                explanation="Test",
                chapter=1,
                start_char=100,
                confidence=0.9,
                created_at=now,
                status=AlertStatus.NEW,
            ),
            Alert(
                id=0,
                project_id=project_id,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="test",
                title="2. WARNING conf 0.6",
                description="Test",
                explanation="Test",
                chapter=1,
                start_char=200,
                confidence=0.6,
                created_at=now + timedelta(seconds=1),
                status=AlertStatus.NEW,
            ),
            Alert(
                id=0,
                project_id=project_id,
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                alert_type="test",
                title="3. WARNING conf 0.9",
                description="Test",
                explanation="Test",
                chapter=1,
                start_char=300,
                confidence=0.9,
                created_at=now + timedelta(seconds=2),
                status=AlertStatus.NEW,
            ),
            Alert(
                id=0,
                project_id=project_id,
                category=AlertCategory.GRAMMAR,
                severity=AlertSeverity.CRITICAL,
                alert_type="test",
                title="4. CRITICAL conf 0.7",
                description="Test",
                explanation="Test",
                chapter=1,
                start_char=400,
                confidence=0.7,
                created_at=now + timedelta(seconds=3),
                status=AlertStatus.NEW,
            ),
        ]

        for alert in alerts_to_create:
            alert_repo.create(alert)

        result = alert_repo.get_by_project_prioritized(project_id)
        assert result.is_success

        alerts = result.value
        assert len(alerts) == 4

        # Verificar orden esperado
        assert alerts[0].severity == AlertSeverity.CRITICAL, \
            "1º: CRITICAL (severidad más alta)"

        assert alerts[1].severity == AlertSeverity.WARNING and alerts[1].confidence == 0.9, \
            "2º: WARNING conf 0.9 (segunda severidad, mayor confianza)"

        assert alerts[2].severity == AlertSeverity.WARNING and alerts[2].confidence == 0.6, \
            "3º: WARNING conf 0.6 (segunda severidad, menor confianza)"

        assert alerts[3].severity == AlertSeverity.INFO, \
            "4º: INFO (severidad más baja)"

    def test_alertas_sin_start_char_usan_chapter(self, alert_repo, project_id):
        """
        Alertas sin start_char deben ordenarse por chapter.
        """
        now = datetime.now()

        # Crear alertas sin start_char pero con chapter
        alert_chapter_5 = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test",
            title="Chapter 5",
            description="Test",
            explanation="Test",
            chapter=5,
            start_char=None,  # Sin start_char
            confidence=0.8,
            created_at=now,
            status=AlertStatus.NEW,
        )

        alert_chapter_2 = Alert(
            id=0,
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=AlertSeverity.WARNING,
            alert_type="test",
            title="Chapter 2",
            description="Test",
            explanation="Test",
            chapter=2,
            start_char=None,  # Sin start_char
            confidence=0.8,
            created_at=now + timedelta(seconds=1),
            status=AlertStatus.NEW,
        )

        alert_repo.create(alert_chapter_5)
        alert_repo.create(alert_chapter_2)

        result = alert_repo.get_by_project_prioritized(project_id)
        assert result.is_success

        alerts = result.value
        assert len(alerts) == 2

        # Chapter 2 debe venir antes que chapter 5
        assert alerts[0].chapter == 2, \
            "Primera alerta debe ser chapter 2 (más temprano)"
        assert alerts[1].chapter == 5, \
            "Segunda alerta debe ser chapter 5 (más tardío)"
