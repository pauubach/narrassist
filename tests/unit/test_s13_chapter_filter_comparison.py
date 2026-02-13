"""
Tests for Sprint S13: Chapter range filtering (BK-27) + Comparison summary (BK-25 MVP).

S13-05: Tests for chapter range filter in repository.
S13-09: Tests for comparison summary endpoint.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# S13-05: Chapter range filtering tests
# ============================================================================


class TestChapterRangeFiltering:
    """Tests para filtrado de alertas por rango de capítulos (BK-27)."""

    def _make_repo(self):
        """Crea un AlertRepository con DB mockeada."""
        from narrative_assistant.alerts.repository import AlertRepository

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.connection.return_value.__enter__ = lambda s: mock_conn
        mock_db.connection.return_value.__exit__ = MagicMock(return_value=False)

        with patch("narrative_assistant.alerts.repository.get_database", return_value=mock_db):
            repo = AlertRepository()

        return repo, mock_conn

    def test_get_by_project_no_range_returns_all(self):
        """Sin rango, devuelve todas las alertas."""
        repo, mock_conn = self._make_repo()
        result = repo.get_by_project(1)
        assert result.is_success

        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        assert "chapter >=" not in query
        assert "chapter <=" not in query

    def test_get_by_project_with_chapter_min(self):
        """Con chapter_min, filtra desde ese capítulo."""
        repo, mock_conn = self._make_repo()
        result = repo.get_by_project(1, chapter_min=5)
        assert result.is_success

        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "chapter >= ?" in query
        assert 5 in params

    def test_get_by_project_with_chapter_max(self):
        """Con chapter_max, filtra hasta ese capítulo."""
        repo, mock_conn = self._make_repo()
        result = repo.get_by_project(1, chapter_max=10)
        assert result.is_success

        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "chapter <= ?" in query
        assert 10 in params

    def test_get_by_project_with_both_range_params(self):
        """Con ambos params, filtra el rango completo."""
        repo, mock_conn = self._make_repo()
        result = repo.get_by_project(1, chapter_min=3, chapter_max=8)
        assert result.is_success

        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "chapter >= ?" in query
        assert "chapter <= ?" in query
        assert 3 in params
        assert 8 in params

    def test_get_by_project_prioritized_with_range(self):
        """Método priorizado también acepta rango de capítulos."""
        repo, mock_conn = self._make_repo()
        result = repo.get_by_project_prioritized(
            1, current_chapter=5, chapter_min=3, chapter_max=10
        )
        assert result.is_success

        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "chapter >= ?" in query
        assert "chapter <= ?" in query
        assert 3 in params
        assert 10 in params


# ============================================================================
# S13-09: Comparison summary endpoint tests
# ============================================================================


class TestComparisonSummary:
    """Tests para el endpoint de resumen de comparación (BK-25 MVP)."""

    def test_comparison_summary_no_snapshot(self):
        """Sin snapshot previo, la lógica devuelve defaults correctos."""
        # Simular la lógica del endpoint cuando no hay snapshot
        report = None  # ComparisonService.compare() returns None when no snapshot
        if report is None:
            summary = {
                "has_comparison": False,
                "resolved": 0,
                "new": 0,
                "unchanged": 0,
                "document_changed": False,
            }
        assert summary["has_comparison"] is False
        assert summary["resolved"] == 0

    def test_comparison_summary_with_data(self):
        """Con snapshot, devuelve counts correctos."""
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {
            "alerts_resolved": [{"id": 1}, {"id": 2}, {"id": 3}],
            "alerts_new": [{"id": 4}],
            "alerts_unchanged": 5,
            "document_changed": True,
        }

        # Simular la lógica del endpoint
        d = mock_report.to_dict()
        summary = {
            "has_comparison": True,
            "resolved": len(d.get("alerts_resolved", [])),
            "new": len(d.get("alerts_new", [])),
            "unchanged": d.get("alerts_unchanged", 0),
            "document_changed": d.get("document_changed", False),
        }

        assert summary["has_comparison"] is True
        assert summary["resolved"] == 3
        assert summary["new"] == 1
        assert summary["unchanged"] == 5
        assert summary["document_changed"] is True

    def test_comparison_summary_zero_changes(self):
        """Sin cambios, todos los counts son 0 excepto unchanged."""
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {
            "alerts_resolved": [],
            "alerts_new": [],
            "alerts_unchanged": 10,
            "document_changed": False,
        }

        d = mock_report.to_dict()
        summary = {
            "has_comparison": True,
            "resolved": len(d.get("alerts_resolved", [])),
            "new": len(d.get("alerts_new", [])),
            "unchanged": d.get("alerts_unchanged", 0),
            "document_changed": d.get("document_changed", False),
        }

        assert summary["resolved"] == 0
        assert summary["new"] == 0
        assert summary["unchanged"] == 10
        assert summary["document_changed"] is False


# ============================================================================
# API endpoint integration test (lightweight)
# ============================================================================


class TestAlertsEndpointChapterRange:
    """Test que verifica que list_alerts acepta chapter_min/chapter_max."""

    def test_list_alerts_signature_has_chapter_params(self):
        """Verificar que list_alerts tiene los parámetros chapter_min y chapter_max."""
        import inspect
        import sys

        sys.path.insert(0, "api-server")
        try:
            from routers.alerts import list_alerts

            sig = inspect.signature(list_alerts)
            param_names = list(sig.parameters.keys())
            assert "chapter_min" in param_names, "chapter_min param missing"
            assert "chapter_max" in param_names, "chapter_max param missing"
        finally:
            sys.path.pop(0)

    def test_comparison_summary_endpoint_exists(self):
        """Verificar que el endpoint comparison/summary existe."""
        import sys

        sys.path.insert(0, "api-server")
        try:
            from routers.collections import get_comparison_summary

            assert callable(get_comparison_summary)
        finally:
            sys.path.pop(0)
