"""
Configuración compartida para pytest.

Define fixtures comunes y configuración de tests.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


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
    from narrative_assistant.entities.models import Entity, EntityType, EntityImportance

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
