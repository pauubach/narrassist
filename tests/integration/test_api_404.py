"""
Tests de integración: proyecto inexistente devuelve 404.

Verifica que los 4 endpoints de análisis avanzado devuelven HTTP 404
cuando se consulta un project_id que no existe en la BD.

Endpoints cubiertos:
- GET /api/projects/{id}/narrative-templates
- GET /api/projects/{id}/narrative-health
- GET /api/projects/{id}/character-archetypes
- GET /api/projects/{id}/sentence-energy
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Añadir api-server al path para poder importar main
_api_dir = str(Path(__file__).resolve().parent.parent.parent / "api-server")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def _make_failure_result():
    """Crear un Result con is_failure=True."""
    from narrative_assistant.core.errors import ErrorSeverity, NarrativeError
    from narrative_assistant.core.result import Result

    return Result(
        errors=[
            NarrativeError(
                message="Not found",
                severity=ErrorSeverity.FATAL,
            )
        ]
    )


@pytest.fixture
def api_client():
    """TestClient con project_manager mockeado para devolver failure."""
    import main as api_main
    import deps

    mock_pm = MagicMock()
    mock_pm.get.return_value = _make_failure_result()

    original_pm = deps.project_manager
    deps.project_manager = mock_pm

    client = TestClient(api_main.app, raise_server_exceptions=False)

    yield client

    deps.project_manager = original_pm


NONEXISTENT_ID = 999999


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI no disponible")
class TestProjectNotFound404:
    """Los 4 endpoints de análisis devuelven 404 con proyecto inexistente."""

    def test_narrative_templates_404(self, api_client):
        """GET /api/projects/{id}/narrative-templates → 404."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/narrative-templates")
        assert resp.status_code == 404, f"Esperado 404, recibido {resp.status_code}: {resp.text}"
        assert "no encontrado" in resp.json()["detail"].lower()

    def test_narrative_health_404(self, api_client):
        """GET /api/projects/{id}/narrative-health → 404."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/narrative-health")
        assert resp.status_code == 404, f"Esperado 404, recibido {resp.status_code}: {resp.text}"
        assert "no encontrado" in resp.json()["detail"].lower()

    def test_character_archetypes_404(self, api_client):
        """GET /api/projects/{id}/character-archetypes → 404."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/character-archetypes")
        assert resp.status_code == 404, f"Esperado 404, recibido {resp.status_code}: {resp.text}"
        assert "no encontrado" in resp.json()["detail"].lower()

    def test_sentence_energy_404(self, api_client):
        """GET /api/projects/{id}/sentence-energy → 404."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/sentence-energy")
        assert resp.status_code == 404, f"Esperado 404, recibido {resp.status_code}: {resp.text}"
        assert "no encontrado" in resp.json()["detail"].lower()


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI no disponible")
class TestProjectNotFoundDetail:
    """Verifica el formato del error 404."""

    def test_404_response_is_json(self, api_client):
        """La respuesta 404 tiene content-type JSON."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/narrative-health")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    def test_404_detail_message(self, api_client):
        """El detail contiene 'Proyecto no encontrado'."""
        resp = api_client.get(f"/api/projects/{NONEXISTENT_ID}/narrative-templates")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Proyecto no encontrado"
