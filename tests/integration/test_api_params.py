"""
Tests de integración: validación de query parameters en endpoints API.

Verifica que los endpoints validan correctamente los parámetros de consulta:
- sentence-energy: low_threshold (0-100), chapter_number (int optional)
- FastAPI devuelve 422 para valores fuera de rango o tipos incorrectos
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_api_dir = str(Path(__file__).resolve().parent.parent.parent / "api-server")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def _make_failure_result():
    """Result con is_failure=True (proyecto inexistente)."""
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
    """TestClient con project_manager que siempre devuelve failure."""
    import main as api_main
    import deps

    mock_pm = MagicMock()
    mock_pm.get.return_value = _make_failure_result()

    original_pm = deps.project_manager
    deps.project_manager = mock_pm

    client = TestClient(api_main.app, raise_server_exceptions=False)

    yield client

    deps.project_manager = original_pm


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI no disponible")
class TestSentenceEnergyParams:
    """Validación de parámetros del endpoint sentence-energy."""

    def test_low_threshold_negative_rejected(self, api_client):
        """low_threshold=-1 devuelve 422 (ge=0.0)."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=-1")
        assert resp.status_code == 422

    def test_low_threshold_over_100_rejected(self, api_client):
        """low_threshold=101 devuelve 422 (le=100.0)."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=101")
        assert resp.status_code == 422

    def test_low_threshold_not_a_number_rejected(self, api_client):
        """low_threshold=abc devuelve 422."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=abc")
        assert resp.status_code == 422

    def test_low_threshold_valid_accepted(self, api_client):
        """low_threshold=50 no devuelve 422 (devuelve 404 por proyecto inexistente)."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=50")
        # 404 porque el proyecto no existe, pero NO 422 (param válido)
        assert resp.status_code == 404

    def test_low_threshold_boundary_zero(self, api_client):
        """low_threshold=0 es válido (ge=0.0)."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=0")
        assert resp.status_code == 404  # Param OK → llega a project lookup → 404

    def test_low_threshold_boundary_100(self, api_client):
        """low_threshold=100 es válido (le=100.0)."""
        resp = api_client.get("/api/projects/1/sentence-energy?low_threshold=100")
        assert resp.status_code == 404

    def test_chapter_number_non_integer_rejected(self, api_client):
        """chapter_number=abc devuelve 422."""
        resp = api_client.get("/api/projects/1/sentence-energy?chapter_number=abc")
        assert resp.status_code == 422

    def test_chapter_number_valid(self, api_client):
        """chapter_number=3 es válido."""
        resp = api_client.get("/api/projects/1/sentence-energy?chapter_number=3")
        assert resp.status_code == 404  # Param OK → project lookup → 404

    def test_default_threshold_applied(self, api_client):
        """Sin low_threshold, usa el default (no 422)."""
        resp = api_client.get("/api/projects/1/sentence-energy")
        assert resp.status_code == 404  # No 422, params OK


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI no disponible")
class TestInvalidProjectIdParam:
    """Validación del path param project_id."""

    def test_non_integer_project_id_rejected(self, api_client):
        """project_id=abc devuelve 422."""
        resp = api_client.get("/api/projects/abc/sentence-energy")
        assert resp.status_code == 422

    def test_negative_project_id_accepted(self, api_client):
        """project_id=-1 es int válido, llega al endpoint (→ 404)."""
        resp = api_client.get("/api/projects/-1/sentence-energy")
        # FastAPI acepta -1 como int, el endpoint devuelve 404
        assert resp.status_code == 404
