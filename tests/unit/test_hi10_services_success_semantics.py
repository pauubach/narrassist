"""Behavior tests for HI-10: no success=true on internal exceptions."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers.services import get_llm_config, get_llm_readiness


def test_get_llm_config_returns_success_false_on_exception(monkeypatch):
    import narrative_assistant.persistence.database as db_module

    def _boom():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(db_module, "get_database", _boom)

    response = asyncio.run(get_llm_config())

    assert response.success is False
    assert response.error
    assert response.data["qualityLevel"] == "rapida"
    assert response.data["sensitivity"] == 5.0


def test_get_llm_readiness_returns_success_false_on_exception(monkeypatch):
    import routers._llm_helpers as llm_helpers

    def _boom():
        raise RuntimeError("readiness failed")

    monkeypatch.setattr(llm_helpers, "check_llm_readiness", _boom)

    response = asyncio.run(get_llm_readiness())

    assert response.success is False
    assert response.error
    assert response.data["ready"] is False
    assert response.data["ollama_running"] is False
