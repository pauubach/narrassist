"""Tests de contrato para endpoints Guardar/Abrir proyecto (.nra)."""

from __future__ import annotations

from pathlib import Path

from narrative_assistant.core.errors import ErrorSeverity, NarrativeError
from narrative_assistant.core.result import Result


class _FakeExporterOK:
    def __init__(self, _db):
        pass

    def export_project(self, _project_id: int, output_path: Path) -> Result[Path]:
        out = Path(output_path)
        if out.suffix.lower() != ".nra":
            out = out.with_suffix(".nra")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"nra!")
        return Result.success(out)


class _FakeExporterFail:
    def __init__(self, _db):
        pass

    def export_project(self, _project_id: int, _output_path: Path) -> Result[Path]:
        return Result.failure(NarrativeError("fallo exportando", severity=ErrorSeverity.FATAL))


class _FakeImporterFail:
    def __init__(self, _db):
        pass

    def import_project(self, _nra_path: Path) -> Result[int]:
        return Result.failure(NarrativeError("fallo importando", severity=ErrorSeverity.FATAL))


def test_save_project_file_success(test_client, sample_project, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "narrative_assistant.persistence.project_file.NraExporter",
        _FakeExporterOK,
    )

    response = test_client.post(
        f"/api/projects/{sample_project.id}/save-file",
        json={"file_path": str(tmp_path / "mi_proyecto")},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Proyecto guardado correctamente."
    assert payload["data"]["path"].endswith(".nra")
    assert payload["data"]["size_bytes"] == 4


def test_save_project_file_failure(test_client, sample_project, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "narrative_assistant.persistence.project_file.NraExporter",
        _FakeExporterFail,
    )

    response = test_client.post(
        f"/api/projects/{sample_project.id}/save-file",
        json={"file_path": str(tmp_path / "mi_proyecto.nra")},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is False
    assert "fallo exportando" in payload["error"]


def test_open_project_file_success_with_warnings(test_client, sample_project, tmp_path, monkeypatch):
    class _FakeImporterOK:
        def __init__(self, _db):
            pass

        def import_project(self, _nra_path: Path) -> Result[int]:
            result = Result.success(sample_project.id)
            result.add_warning("Archivo exportado con versión anterior (schema 31).")
            return result

    monkeypatch.setattr(
        "narrative_assistant.persistence.project_file.NraImporter",
        _FakeImporterOK,
    )

    response = test_client.post(
        "/api/projects/open-file",
        json={"file_path": str(tmp_path / "entrada.nra")},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Proyecto abierto correctamente."
    assert payload["data"]["project_id"] == sample_project.id
    assert payload["data"]["project_name"] == sample_project.name
    assert payload["data"]["warnings"] == ["Archivo exportado con versión anterior (schema 31)."]


def test_open_project_file_failure(test_client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "narrative_assistant.persistence.project_file.NraImporter",
        _FakeImporterFail,
    )

    response = test_client.post(
        "/api/projects/open-file",
        json={"file_path": str(tmp_path / "entrada.nra")},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is False
    assert "fallo importando" in payload["error"]
