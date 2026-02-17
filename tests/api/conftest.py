"""
Fixtures para tests de API.

Proporciona TestClient de FastAPI y fixtures de datos de prueba.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock

# Import the FastAPI app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api-server"))

from main import app
from narrative_assistant.persistence.database import Database
from narrative_assistant.persistence.project import Project


@pytest.fixture
def test_client():
    """Fixture que proporciona un TestClient de FastAPI."""
    return TestClient(app)


@pytest.fixture
def sample_project(temp_db):
    """
    Fixture que crea un proyecto de ejemplo con capítulos.

    Retorna un objeto Project con:
    - ID = 1
    - Nombre = "Sample Project"
    - 5 capítulos con texto de ejemplo
    """
    db = Database(temp_db)

    # Crear proyecto
    result = db.create_project(
        name="Sample Project",
        document_path="/tmp/sample.docx"
    )

    if result.is_failure:
        pytest.fail(f"Failed to create project: {result.error}")

    project_id = result.value

    # Obtener el proyecto
    project_result = db.get_project(project_id)
    if project_result.is_failure:
        pytest.fail(f"Failed to get project: {project_result.error}")

    project = project_result.value

    # Crear algunos capítulos de ejemplo
    for i in range(1, 6):
        chapter_result = db.create_chapter(
            project_id=project_id,
            chapter_number=i,
            title=f"Capítulo {i}",
            text=f"Este es el texto del capítulo {i}. " * 50,  # ~250 palabras
            word_count=250
        )

        if chapter_result.is_failure:
            pytest.fail(f"Failed to create chapter {i}: {chapter_result.error}")

    return project


@pytest.fixture
def empty_project(temp_db):
    """
    Fixture que crea un proyecto vacío sin capítulos.

    Retorna un objeto Project vacío para tests de edge cases.
    """
    db = Database(temp_db)

    # Crear proyecto
    result = db.create_project(
        name="Empty Project",
        document_path="/tmp/empty.docx"
    )

    if result.is_failure:
        pytest.fail(f"Failed to create project: {result.error}")

    project_id = result.value

    # Obtener el proyecto
    project_result = db.get_project(project_id)
    if project_result.is_failure:
        pytest.fail(f"Failed to get project: {project_result.error}")

    return project_result.value
