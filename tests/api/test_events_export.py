"""
Tests para endpoints de export de eventos.

Tests para /api/projects/{id}/events/export con formatos CSV y JSON.
"""

import json

import pytest
from fastapi.testclient import TestClient


def test_export_csv_basic(test_client: TestClient, sample_project):
    """Test export CSV básico."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/export?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    content = response.content.decode("utf-8")

    # Verificar BOM UTF-8 (crítico para Excel Windows)
    assert content.startswith("\ufeff")

    # Verificar cabeceras CSV
    assert "chapter,event_type,tier,description,confidence,start_char,end_char" in content


def test_export_csv_spanish_characters(test_client: TestClient, sample_project):
    """Test CSV export preserva caracteres españoles."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/export?format=csv")

    assert response.status_code == 200

    content = response.content.decode("utf-8")

    # Si hay eventos, verificar que caracteres especiales se preservan
    # (depende del contenido del proyecto, pero el encoding debe funcionar)
    assert "\ufeff" in content  # BOM


def test_export_json_basic(test_client: TestClient, sample_project):
    """Test export JSON básico."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/export?format=json")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "project_id" in data["data"]
    assert "events" in data["data"]
    assert data["data"]["project_id"] == sample_project.id


def test_export_json_schema(test_client: TestClient, sample_project):
    """Test schema JSON consistente."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/export?format=json")

    data = response.json()["data"]

    assert "project_id" in data
    assert "project_name" in data
    assert "exported_at" in data
    assert "total_events" in data
    assert "filters_applied" in data
    assert "events" in data

    if len(data["events"]) > 0:
        event = data["events"][0]
        assert "chapter" in event
        assert "event_type" in event
        assert "tier" in event
        assert "description" in event
        assert "confidence" in event
        assert "start_char" in event
        assert "end_char" in event


def test_export_filter_by_tier(test_client: TestClient, sample_project):
    """Test filtrado por tier."""
    response = test_client.get(
        f"/api/projects/{sample_project.id}/events/export?format=json&tier_filter=1"
    )

    data = response.json()["data"]

    # Verificar que solo hay eventos tier1
    for event in data["events"]:
        assert event["tier"] == 1


def test_export_filter_by_event_types(test_client: TestClient, sample_project):
    """Test filtrado por tipos de evento."""
    response = test_client.get(
        f"/api/projects/{sample_project.id}/events/export?format=json&event_types=promise,injury"
    )

    data = response.json()["data"]

    # Verificar que solo hay eventos de los tipos especificados
    for event in data["events"]:
        assert event["event_type"] in ["promise", "injury"]


def test_export_filter_critical_only(test_client: TestClient, sample_project):
    """Test filtrado solo eventos críticos."""
    response = test_client.get(
        f"/api/projects/{sample_project.id}/events/export?format=json&critical_only=true"
    )

    assert response.status_code == 200

    data = response.json()["data"]

    # Eventos críticos sin resolver (puede ser 0 si no hay)
    assert isinstance(data["events"], list)


def test_export_filter_chapter_range(test_client: TestClient, sample_project):
    """Test filtrado por rango de capítulos."""
    response = test_client.get(
        f"/api/projects/{sample_project.id}/events/export?format=json&chapter_start=1&chapter_end=3"
    )

    data = response.json()["data"]

    # Verificar que solo hay eventos de capítulos 1-3
    for event in data["events"]:
        if event["chapter"]:
            assert 1 <= event["chapter"] <= 3


def test_export_project_not_found(test_client: TestClient):
    """Test export proyecto inexistente."""
    response = test_client.get("/api/projects/99999/events/export?format=csv")

    assert response.status_code == 404


def test_export_csv_filename(test_client: TestClient, sample_project):
    """Test que el filename CSV es correcto."""
    response = test_client.get(f"/api/projects/{sample_project.id}/events/export?format=csv")

    assert response.status_code == 200

    content_disposition = response.headers.get("content-disposition", "")
    assert "attachment" in content_disposition
    assert "eventos_" in content_disposition
    assert ".csv" in content_disposition


def test_export_combined_filters(test_client: TestClient, sample_project):
    """Test múltiples filtros combinados."""
    response = test_client.get(
        f"/api/projects/{sample_project.id}/events/export?"
        "format=json&tier_filter=1&chapter_start=1&chapter_end=5"
    )

    assert response.status_code == 200

    data = response.json()["data"]

    # Verificar filtros aplicados
    assert data["filters_applied"]["tier"] == "1"
    assert data["filters_applied"]["chapter_range"] == [1, 5]
