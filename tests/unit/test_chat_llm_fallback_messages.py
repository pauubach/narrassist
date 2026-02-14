"""Regression tests for chat LLM fallback behavior in services router."""

from __future__ import annotations

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
from deps import ChatRequest
from routers.services import chat_with_assistant


@pytest.fixture
def patched_project_manager(monkeypatch):
    """Provide a project_manager that always returns an existing project."""
    project = SimpleNamespace(id=1, name="Proyecto Test")
    result = SimpleNamespace(is_failure=False, value=project)

    pm = MagicMock()
    pm.get.return_value = result
    monkeypatch.setattr(deps, "project_manager", pm)
    monkeypatch.setattr(deps, "chapter_repository", None)
    return pm


def _run_chat(project_id: int = 1, message: str = "hola"):
    return asyncio.run(chat_with_assistant(project_id, ChatRequest(message=message)))


def test_chat_unavailable_message_windows(monkeypatch, patched_project_manager):
    import routers.services as services_mod

    import narrative_assistant.llm as llm_mod

    monkeypatch.setattr(services_mod.sys, "platform", "win32")
    monkeypatch.setattr(llm_mod, "is_llm_available", lambda: False)

    response = _run_chat()

    assert response.success is False
    assert response.error is not None
    assert "start_ollama_cpu.bat" in response.error
    assert "OLLAMA_NUM_GPU=0 ollama serve" not in response.error


def test_chat_unavailable_message_macos(monkeypatch, patched_project_manager):
    import routers.services as services_mod

    import narrative_assistant.llm as llm_mod

    monkeypatch.setattr(services_mod.sys, "platform", "darwin")
    monkeypatch.setattr(llm_mod, "is_llm_available", lambda: False)

    response = _run_chat()

    assert response.success is False
    assert response.error is not None
    assert "OLLAMA_NUM_GPU=0 ollama serve" in response.error
    assert "start_ollama_cpu.bat" not in response.error


def test_chat_success_sets_using_cpu_flag(monkeypatch, patched_project_manager):
    import routers.services as services_mod

    import narrative_assistant.llm as llm_mod

    llm_client = SimpleNamespace(
        is_available=True,
        model_name="llama3.2",
        _ollama_num_gpu=0,
        complete=lambda **_: "respuesta",
    )

    monkeypatch.setattr(services_mod.sys, "platform", "darwin")
    monkeypatch.setattr(llm_mod, "is_llm_available", lambda: True)
    monkeypatch.setattr(llm_mod, "get_llm_client", lambda: llm_client)

    response = _run_chat()

    assert response.success is True
    assert response.data is not None
    assert response.data["response"] == "respuesta"
    assert response.data["usingCpu"] is True
    assert response.data["model"] == "llama3.2"


def test_chat_vram_error_message_uses_platform_hint(monkeypatch, patched_project_manager):
    import routers.services as services_mod

    import narrative_assistant.llm as llm_mod

    def _raise_vram_error(**_):
        raise RuntimeError("llama runner process has terminated: exit status 2")

    llm_client = SimpleNamespace(
        is_available=True,
        model_name="llama3.2",
        _ollama_num_gpu=None,
        complete=_raise_vram_error,
    )

    monkeypatch.setattr(services_mod.sys, "platform", "darwin")
    monkeypatch.setattr(llm_mod, "is_llm_available", lambda: True)
    monkeypatch.setattr(llm_mod, "get_llm_client", lambda: llm_client)

    response = _run_chat()

    assert response.success is False
    assert response.error is not None
    assert "Ollama se quedó sin memoria GPU" in response.error
    assert "OLLAMA_NUM_GPU=0 ollama serve" in response.error

