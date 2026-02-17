"""
Tests para endpoint de estadísticas de eventos.

Tests para /api/projects/{id}/events/stats.
"""

import pytest
from fastapi.testclient import TestClient


def test_get_event_stats_basic(test_client: TestClient, sample_project):
    """Test obtener estadísticas básicas."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "data" in data


def test_event_stats_schema(test_client: TestClient, sample_project):
    """Test schema de estadísticas."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]

    # Verificar estructura
    assert "project_id" in stats
    assert "total_events" in stats
    assert "critical_unresolved" in stats
    assert "empty_chapters" in stats
    assert "event_clusters" in stats
    assert "density_by_chapter" in stats

    assert stats["project_id"] == sample_project.id


def test_critical_unresolved_structure(test_client: TestClient, sample_project):
    """Test estructura de eventos críticos sin resolver."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    critical = stats["critical_unresolved"]

    assert "count" in critical
    assert "by_type" in critical
    assert "details" in critical

    assert isinstance(critical["count"], int)
    assert isinstance(critical["by_type"], dict)
    assert isinstance(critical["details"], list)


def test_empty_chapters_list(test_client: TestClient, sample_project):
    """Test lista de capítulos vacíos."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    empty_chapters = stats["empty_chapters"]

    assert isinstance(empty_chapters, list)

    # Si hay capítulos vacíos, deben ser números
    for ch in empty_chapters:
        assert isinstance(ch, int)
        assert ch > 0


def test_event_clusters_structure(test_client: TestClient, sample_project):
    """Test estructura de clusters de eventos."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    clusters = stats["event_clusters"]

    assert isinstance(clusters, list)

    # Máximo 3 clusters (top 3)
    assert len(clusters) <= 3

    # Verificar estructura de cada cluster
    for cluster in clusters:
        assert "event_type" in cluster
        assert "chapter" in cluster
        assert "count" in cluster
        assert "description" in cluster

        # Count debe ser >= 3 (definición de cluster)
        assert cluster["count"] >= 3


def test_density_by_chapter_structure(test_client: TestClient, sample_project):
    """Test estructura de densidad por capítulo."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    density = stats["density_by_chapter"]

    assert isinstance(density, list)

    # Debe haber una entrada por capítulo
    for entry in density:
        assert "chapter" in entry
        assert "tier1" in entry
        assert "tier2" in entry
        assert "tier3" in entry
        assert "total" in entry

        # Verificar sumas
        assert entry["total"] == entry["tier1"] + entry["tier2"] + entry["tier3"]


def test_stats_project_not_found(test_client: TestClient):
    """Test stats proyecto inexistente."""
    response = test_client.get("/api/projects/99999/events/stats")

    assert response.status_code == 404


def test_stats_empty_project(test_client: TestClient, empty_project):
    """Test stats proyecto sin capítulos."""
    response = test_client.get(f"/api/projects/{empty_project.id}/events/stats")

    assert response.status_code == 200

    stats = response.json()["data"]

    assert stats["total_events"] == 0
    assert stats["critical_unresolved"]["count"] == 0
    assert stats["empty_chapters"] == []
    assert stats["event_clusters"] == []
    assert stats["density_by_chapter"] == []


def test_critical_unresolved_details_limit(test_client: TestClient, sample_project):
    """Test que details de critical_unresolved está limitado a 10."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    details = stats["critical_unresolved"]["details"]

    # Máximo 10 detalles
    assert len(details) <= 10


def test_event_clusters_sorted_by_count(test_client: TestClient, sample_project):
    """Test que clusters están ordenados por count descendente."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/stats")

    stats = response.json()["data"]
    clusters = stats["event_clusters"]

    if len(clusters) > 1:
        # Verificar orden descendente
        for i in range(len(clusters) - 1):
            assert clusters[i]["count"] >= clusters[i + 1]["count"]
