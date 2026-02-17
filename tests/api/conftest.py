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
from narrative_assistant.persistence.project import Project, ProjectManager


@pytest.fixture
def test_client(temp_db, monkeypatch):
    """
    Fixture que proporciona un TestClient de FastAPI.

    Configura la DB del test para que el app use la misma base de datos.
    """
    # Parchear get_database para que devuelva la DB del test
    test_db = Database(temp_db)
    monkeypatch.setattr("narrative_assistant.persistence.database.get_database", lambda: test_db)

    # Inicializar deps globals con test_db
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api-server"))
    import deps
    deps.project_manager = ProjectManager(test_db)
    deps.get_database = lambda: test_db

    return TestClient(app)


@pytest.fixture
def sample_project(temp_db):
    """
    Fixture que crea un proyecto de ejemplo con capítulos.

    Retorna un objeto Project con:
    - ID asignado automáticamente
    - Nombre = "Sample Project"
    - 5 capítulos con texto de ejemplo
    """
    db = Database(temp_db)
    manager = ProjectManager(db)

    # Crear texto de ejemplo con 5 capítulos
    text = ""
    for i in range(1, 6):
        text += f"\n# Capítulo {i}\n\n"
        text += f"Este es el texto del capítulo {i}. " * 50  # ~250 palabras por capítulo
        text += "\n\n"

    # Crear proyecto usando ProjectManager
    result = manager.create_from_document(
        text=text,
        name="Sample Project",
        document_format="txt",
        check_existing=False
    )

    if result.is_failure:
        pytest.fail(f"Failed to create project: {result.error}")

    return result.value


@pytest.fixture
def empty_project(temp_db):
    """
    Fixture que crea un proyecto vacío sin capítulos.

    Retorna un objeto Project vacío para tests de edge cases.
    """
    db = Database(temp_db)
    manager = ProjectManager(db)

    # Crear proyecto vacío (sin texto)
    result = manager.create_from_document(
        text="",
        name="Empty Project",
        document_format="txt",
        check_existing=False
    )

    if result.is_failure:
        pytest.fail(f"Failed to create project: {result.error}")

    return result.value
