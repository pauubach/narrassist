"""Tests del endpoint /api/models/download (orquestacion robusta HI-01)."""

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

import deps  # noqa: E402
from routers import system as system_router  # noqa: E402


class _DummyThread:
    def __init__(self, target, args=(), daemon=False):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True


def test_download_models_rejects_parallel_session(monkeypatch):
    monkeypatch.setattr(deps, "MODULES_LOADED", True)
    monkeypatch.setattr(system_router, "_has_active_nlp_downloads", lambda: True)

    # Evitar efectos secundarios reales.
    monkeypatch.setattr(system_router.threading, "Thread", _DummyThread)

    request = deps.DownloadModelsRequest(models=["spacy"], force=False)
    with pytest.raises(HTTPException) as exc:
        system_router.download_models(request)

    assert exc.value.status_code == 409


def test_download_models_validates_dedups_and_queues(monkeypatch):
    monkeypatch.setattr(deps, "MODULES_LOADED", True)
    monkeypatch.setattr(system_router, "_has_active_nlp_downloads", lambda: False)

    import narrative_assistant.core.model_manager as mm

    queued_updates = []
    started_tokens = {}
    thread_holder = {}

    def _fake_begin(model_type):
        token = len(started_tokens) + 1
        started_tokens[model_type.value] = token
        return token

    def _fake_update(model_type, phase, **kwargs):
        queued_updates.append((model_type.value, phase, kwargs))

    class _CapturingThread(_DummyThread):
        def __init__(self, target, args=(), daemon=False):
            super().__init__(target=target, args=args, daemon=daemon)
            thread_holder["thread"] = self

    monkeypatch.setattr(mm, "get_model_manager", lambda: object())
    monkeypatch.setattr(mm, "begin_download_progress_session", _fake_begin)
    monkeypatch.setattr(mm, "_update_download_progress", _fake_update)
    monkeypatch.setattr(system_router.threading, "Thread", _CapturingThread)

    request = deps.DownloadModelsRequest(
        models=["spacy", "invalid_model", "spacy", "embeddings"],
        force=True,
    )
    response = system_router.download_models(request)

    assert response.success is True
    assert response.data["models"] == ["spacy", "embeddings"]
    assert response.data["ignored_models"] == ["invalid_model"]

    assert "thread" in thread_holder
    assert thread_holder["thread"].started is True
    assert thread_holder["thread"].target is system_router._run_nlp_download_jobs

    # Debe dejar ambos modelos en cola con token de sesion.
    queued_models = [row[0] for row in queued_updates if row[1] == "queued"]
    assert queued_models == ["spacy", "embeddings"]
    for _, _, kwargs in queued_updates:
        assert kwargs.get("progress_token") is not None
