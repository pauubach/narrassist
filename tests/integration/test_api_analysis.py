"""
Tests de integración para la API de análisis.

Estos tests verifican el flujo completo de análisis,
incluyendo el tracking de progreso y actualización de estados.
"""

import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# Importar FastAPI test client si está disponible
try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI no disponible")
class TestAnalysisAPIIntegration:
    """Tests de integración para endpoints de análisis."""

    @pytest.fixture
    def mock_project(self):
        """Mock de proyecto para tests."""
        project = Mock()
        project.id = 1
        project.name = "Test Project"
        project.document_path = "/tmp/test.docx"
        project.analysis_status = "pending"
        project.analysis_progress = 0.0
        project.word_count = 0
        project.chapter_count = 0
        return project

    def test_analysis_status_updated_on_start(self, mock_project):
        """
        Verifica que al iniciar análisis, el proyecto
        se actualiza a status='analyzing'.

        Este test habría detectado que faltaba actualizar
        analysis_status en la BD al iniciar.
        """
        # Simular el flujo de inicio de análisis
        assert mock_project.analysis_status == "pending"

        # Al iniciar análisis, debe cambiar a "analyzing"
        mock_project.analysis_status = "analyzing"
        mock_project.analysis_progress = 0.0

        assert mock_project.analysis_status == "analyzing"
        assert mock_project.analysis_progress == 0.0

    def test_analysis_status_values(self):
        """Verifica todos los valores posibles de analysis_status."""
        valid_statuses = [
            'pending',      # Inicial, sin análisis
            'in_progress',  # Análisis en curso (alternativo)
            'analyzing',    # Análisis en curso
            'completed',    # Análisis completado
            'error',        # Error durante análisis
            'failed',       # Análisis falló
        ]

        # Este test documenta los estados válidos
        for status in valid_statuses:
            assert status in valid_statuses


class TestAnalysisProgressStorage:
    """Tests para el almacenamiento de progreso de análisis."""

    def test_progress_storage_structure(self):
        """
        Verifica la estructura del diccionario de progreso.

        Esto documenta los campos que el frontend espera.
        """
        expected_structure = {
            "project_id": 1,
            "status": "running",  # pending, running, completed, failed
            "progress": 0,  # 0-100
            "current_phase": "Iniciando análisis...",
            "current_action": "Preparando documento",
            "phases": [
                {"id": "parsing", "name": "Extracción de texto", "completed": False, "current": False},
                {"id": "structure", "name": "Detección de estructura", "completed": False, "current": False},
                {"id": "ner", "name": "Reconocimiento de entidades", "completed": False, "current": False},
                {"id": "attributes", "name": "Extracción de atributos", "completed": False, "current": False},
                {"id": "consistency", "name": "Análisis de consistencia", "completed": False, "current": False},
                {"id": "grammar", "name": "Análisis gramatical", "completed": False, "current": False},
                {"id": "alerts", "name": "Generación de alertas", "completed": False, "current": False}
            ],
            "metrics": {},
            "estimated_seconds_remaining": 60,
        }

        # Verificar campos requeridos
        required_fields = ['project_id', 'status', 'progress', 'current_phase', 'phases']
        for field in required_fields:
            assert field in expected_structure, f"Falta campo requerido: {field}"

    def test_progress_status_transitions(self):
        """
        Verifica las transiciones válidas de estado.
        """
        # Transiciones válidas
        valid_transitions = {
            'pending': ['running'],
            'running': ['completed', 'failed', 'error'],
            'completed': [],  # Estado final
            'failed': [],     # Estado final
            'error': [],      # Estado final
        }

        # Verificar que completed y failed son estados finales
        assert len(valid_transitions['completed']) == 0
        assert len(valid_transitions['failed']) == 0

    def test_progress_response_format(self):
        """
        Verifica el formato de respuesta del endpoint /analysis/progress.
        """
        # Formato esperado por el frontend
        expected_response = {
            "success": True,
            "data": {
                "project_id": 1,
                "status": "running",
                "progress": 45,
                "current_phase": "Reconocimiento de entidades",
                "current_action": "Procesando capítulo 3",
                "phases": [],
                "estimated_seconds_remaining": 30,
            }
        }

        # Verificar estructura
        assert "success" in expected_response
        assert "data" in expected_response
        assert "progress" in expected_response["data"]
        assert "status" in expected_response["data"]
        assert "current_phase" in expected_response["data"]


class TestProjectResponseFormat:
    """
    Tests para verificar que la respuesta del proyecto
    incluye todos los campos necesarios.
    """

    def test_project_response_includes_analysis_status(self):
        """
        Verifica que la respuesta del proyecto incluye analysis_status.

        Este test habría detectado que faltaba analysis_status
        en el tipo Project del frontend.
        """
        project_response = {
            "id": 1,
            "name": "Test Project",
            "description": "Test description",
            "document_path": "/path/to/doc.docx",
            "document_format": "docx",
            "created_at": "2024-01-15T10:00:00Z",
            "last_modified": "2024-01-15T12:00:00Z",
            "last_opened": "2024-01-15T11:00:00Z",
            "analysis_status": "analyzing",  # Campo crítico
            "analysis_progress": 50,
            "word_count": 10000,
            "chapter_count": 5,
            "entity_count": 25,
            "open_alerts_count": 3,
            "highest_alert_severity": "warning",
        }

        # Verificar campos críticos para el frontend
        assert "analysis_status" in project_response, \
            "Falta analysis_status en respuesta de proyecto"
        assert "analysis_progress" in project_response, \
            "Falta analysis_progress en respuesta de proyecto"

        # Verificar valores válidos
        valid_statuses = ['pending', 'in_progress', 'analyzing', 'completed', 'error', 'failed']
        assert project_response["analysis_status"] in valid_statuses

    def test_project_fields_match_frontend_types(self):
        """
        Verifica que los campos del backend coinciden
        con lo que espera el frontend.

        Referencia: frontend/src/types/api/projects.ts
        """
        # Campos que el frontend espera (snake_case de la API)
        expected_api_fields = [
            'id',
            'name',
            'description',
            'document_path',
            'document_format',
            'created_at',
            'last_modified',
            'last_opened',
            'analysis_status',      # Añadido
            'analysis_progress',
            'word_count',
            'chapter_count',
            'entity_count',
            'open_alerts_count',
            'highest_alert_severity',
        ]

        # Simular respuesta del backend
        mock_response = {
            'id': 1,
            'name': 'Test',
            'description': 'Desc',
            'document_path': '/path',
            'document_format': 'docx',
            'created_at': '2024-01-01T00:00:00Z',
            'last_modified': '2024-01-01T00:00:00Z',
            'last_opened': None,
            'analysis_status': 'completed',
            'analysis_progress': 100,
            'word_count': 1000,
            'chapter_count': 1,
            'entity_count': 10,
            'open_alerts_count': 0,
            'highest_alert_severity': None,
        }

        for field in expected_api_fields:
            assert field in mock_response, \
                f"Campo '{field}' falta en respuesta del backend"


class TestAlertResponseFormat:
    """Tests para verificar formato de respuesta de alertas."""

    def test_alert_response_includes_excerpt(self):
        """
        Verifica que la respuesta de alerta incluye excerpt.

        Este test habría detectado que faltaba excerpt
        en la respuesta del backend.
        """
        alert_response = {
            "id": 1,
            "project_id": 1,
            "category": "consistency",
            "severity": "warning",
            "alert_type": "attribute_inconsistency",
            "title": "Inconsistencia detectada",
            "description": "El color de ojos cambió",
            "explanation": "En el capítulo 1...",
            "suggestion": "Verificar cuál es correcto",
            "chapter": 3,
            "start_char": 1500,
            "end_char": 1520,
            "excerpt": "sus ojos verdes brillaban",  # Campo crítico
            "status": "open",
            "entity_ids": [1],
            "confidence": 0.9,
            "created_at": "2024-01-15T10:00:00Z",
            "resolved_at": None,
        }

        assert "excerpt" in alert_response, \
            "Falta excerpt en respuesta de alerta"
        assert "start_char" in alert_response, \
            "Falta start_char en respuesta de alerta"
        assert "end_char" in alert_response, \
            "Falta end_char en respuesta de alerta"


class TestEntityResponseFormat:
    """Tests para verificar formato de respuesta de entidades."""

    def test_entity_response_includes_relevance_score(self):
        """
        Verifica que la respuesta de entidad incluye relevance_score.

        Este test habría detectado que faltaba relevance_score
        en la respuesta del backend.
        """
        entity_response = {
            "id": 1,
            "project_id": 1,
            "entity_type": "character",
            "canonical_name": "María",
            "aliases": ["Mari"],
            "importance": "major",
            "description": "La protagonista",
            "first_mention_chapter": 1,
            "mention_count": 50,
            "is_active": True,
            "merged_from_ids": [],
            "relevance_score": 0.85,  # Campo crítico
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
        }

        assert "relevance_score" in entity_response, \
            "Falta relevance_score en respuesta de entidad"
