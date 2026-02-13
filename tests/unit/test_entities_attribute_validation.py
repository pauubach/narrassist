"""
Tests para validación de categoría en POST /entities/{id}/attributes.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

API_DIR = Path(__file__).resolve().parent.parent.parent / "api-server"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import deps
from routers.entities import create_entity_attribute


def _entity(entity_id: int = 7, project_id: int = 1, entity_type: str = "location"):
    return SimpleNamespace(
        id=entity_id,
        project_id=project_id,
        entity_type=SimpleNamespace(value=entity_type),
    )


@pytest.fixture
def mocked_entity_repo(monkeypatch):
    entity_repo = MagicMock()
    monkeypatch.setattr(deps, "entity_repository", entity_repo)
    return entity_repo


class TestEntityAttributeCategoryValidation:
    def test_rejects_invalid_category_for_entity_type(self, mocked_entity_repo):
        mocked_entity_repo.get_entity.return_value = _entity(entity_type="location")

        body = deps.CreateAttributeRequest(
            category="physical",  # inválida para location
            name="Color del cielo",
            value="gris",
            confidence=1.0,
        )

        response = asyncio.run(
            create_entity_attribute(project_id=1, entity_id=7, body=body)
        )

        assert response.success is False
        assert "no permitida" in (response.error or "")
        mocked_entity_repo.create_attribute.assert_not_called()

    def test_accepts_valid_category_for_entity_type(self, mocked_entity_repo):
        mocked_entity_repo.get_entity.return_value = _entity(entity_type="location")
        mocked_entity_repo.create_attribute.return_value = 123

        body = deps.CreateAttributeRequest(
            category="geographic",
            name="clima",
            value="húmedo",
            confidence=0.9,
        )

        response = asyncio.run(
            create_entity_attribute(project_id=1, entity_id=7, body=body)
        )

        assert response.success is True
        assert response.data["id"] == 123
        mocked_entity_repo.create_attribute.assert_called_once()
