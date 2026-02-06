"""
Configuración compartida para pytest.

Define fixtures comunes y configuración de tests.

Gestión de memoria para modelos NLP:
- spaCy se carga UNA VEZ por sesión (session-scoped) y se comparte entre tests
- Los tests que necesitan spaCy/NLP deben marcarse con @pytest.mark.heavy
- Por defecto pytest excluye @heavy (ver pytest.ini: -m "not heavy")
- Para correr todos: pytest -m ""
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# ============================================================================
# Markers automáticos para tests pesados
# ============================================================================

# Archivos/directorios que sabemos que cargan modelos NLP pesados
_HEAVY_PATTERNS = {
    "test_attributes.py",
    "test_ner.py",
    "test_cesp_linguistic.py",
    "test_spanish_rules.py",
    "test_ojos_verdes_bug.py",
    "test_llamacpp_manager.py",  # start_server tests cuelgan sin timeout
}

_HEAVY_DIRS = {
    "adversarial",
    "evaluation",
    "integration",
    "regression",
    "performance",
}


def pytest_collection_modifyitems(config, items):
    """
    Auto-marca tests como @heavy basándose en su ubicación.

    Tests en adversarial/, evaluation/, integration/, regression/ y ciertos
    archivos unit que cargan spaCy se marcan automáticamente como heavy.
    Esto permite excluirlos por defecto en equipos con poca RAM.
    """
    heavy_marker = pytest.mark.heavy

    for item in items:
        # Ya marcado manualmente → respetar
        if "heavy" in item.keywords:
            continue

        fspath = str(item.fspath)

        # Por nombre de archivo
        filename = os.path.basename(fspath)
        if filename in _HEAVY_PATTERNS:
            item.add_marker(heavy_marker)
            continue

        # Por directorio
        parts = Path(fspath).parts
        for part in parts:
            if part in _HEAVY_DIRS:
                item.add_marker(heavy_marker)
                break


# ============================================================================
# Fixture session-scoped para spaCy (carga UNA vez, ~500MB)
# ============================================================================

@pytest.fixture(scope="session")
def shared_spacy_nlp():
    """
    Modelo spaCy compartido entre TODOS los tests de la sesión.

    Carga el modelo una sola vez (~500MB) y lo reutiliza.
    Usar esta fixture en tests que necesiten spaCy directamente.
    """
    try:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        nlp = load_spacy_model()
        return nlp
    except Exception:
        pytest.skip("Modelo spaCy no disponible")


@pytest.fixture(scope="session")
def shared_attribute_extractor():
    """
    AttributeExtractor compartido entre tests de la sesión.

    Evita crear múltiples instancias que re-cargan spaCy.
    """
    try:
        from narrative_assistant.nlp.attributes import AttributeExtractor
        return AttributeExtractor(filter_metaphors=False)
    except Exception:
        pytest.skip("AttributeExtractor no disponible")


# ============================================================================
# Fixtures básicas (ligeras, sin modelos NLP)
# ============================================================================

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
