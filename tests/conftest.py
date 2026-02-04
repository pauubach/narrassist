"""
Configuración compartida para pytest.

Define fixtures comunes y configuración de tests.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir():
    """Directorio con archivos de prueba."""
    return Path(__file__).parent.parent / "test_books"


@pytest.fixture
def temp_db():
    """Base de datos temporal para tests."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    yield db_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    """
    Fixture que aísla la BD para cada test.

    Se ejecuta automáticamente antes de cada test para asegurar
    que cada test tiene su propia BD limpia con el schema actual.
    """
    from narrative_assistant.persistence.database import get_database, reset_database

    # Crear directorio temporal para la BD de este test
    test_db_dir = tmp_path / "narrative_assistant"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    test_db_path = test_db_dir / "test.db"

    # Setear variable de entorno para que el sistema use esta BD
    old_data_dir = os.environ.get("NA_DATA_DIR")
    os.environ["NA_DATA_DIR"] = str(tmp_path)

    # Resetear singleton para que use la nueva ubicación
    reset_database()

    # Inicializar BD con schema actual (esto crea las tablas)
    db = get_database(test_db_path)

    yield db

    # Cleanup: restaurar variable de entorno
    reset_database()
    if old_data_dir:
        os.environ["NA_DATA_DIR"] = old_data_dir
    elif "NA_DATA_DIR" in os.environ:
        del os.environ["NA_DATA_DIR"]


@pytest.fixture
def sample_text():
    """Texto de prueba simple."""
    return """
    Capítulo 1: El Inicio

    María era una mujer de ojos azules y cabello negro. Tenía treinta años.
    Juan, su hermano, era alto y delgado. Vivía en Madrid.

    Capítulo 2: El Cambio

    María apareció con ojos verdes y cabello rubio. Ahora parecía tener cuarenta años.
    Juan era bajo y fornido, y vivía en Barcelona.
    """


@pytest.fixture
def sample_entities():
    """Entidades de prueba."""
    from narrative_assistant.entities.models import Entity, EntityImportance, EntityType

    return [
        Entity(
            id=1,
            project_id=1,
            entity_type=EntityType.CHARACTER,
            canonical_name="María",
            aliases=["Maria", "la mujer"],
            importance=EntityImportance.MAIN,
        ),
        Entity(
            id=2,
            project_id=1,
            entity_type=EntityType.CHARACTER,
            canonical_name="Juan",
            aliases=["el hermano"],
            importance=EntityImportance.SECONDARY,
        ),
        Entity(
            id=3,
            project_id=1,
            entity_type=EntityType.LOCATION,
            canonical_name="Madrid",
            aliases=[],
            importance=EntityImportance.MINOR,
        ),
    ]
