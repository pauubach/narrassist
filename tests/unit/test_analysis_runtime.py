import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

import routers._analysis_runtime as runtime  # noqa: E402


def test_runtime_caps_attempts_to_start_ollama(monkeypatch):
    calls: list[tuple[bool, bool]] = []

    def fake_ensure_ollama_ready(*, install_if_missing: bool, start_if_stopped: bool):
        calls.append((install_if_missing, start_if_stopped))
        return True, ""

    monkeypatch.setattr(runtime, "ensure_ollama_ready", fake_ensure_ollama_ready)
    monkeypatch.setattr(runtime.deps, "_check_languagetool_available", lambda auto_start=False: False)
    monkeypatch.setitem(sys.modules, "torch", type("TorchModule", (), {"cuda": type("Cuda", (), {"is_available": staticmethod(lambda: False)})()})())

    caps = runtime._get_runtime_service_capabilities()

    assert caps["ollama"] is True
    assert calls == [(False, True)]


def test_runtime_caps_attempts_to_autostart_languagetool(monkeypatch):
    lt_calls: list[bool] = []

    monkeypatch.setattr(runtime, "ensure_ollama_ready", lambda **kwargs: (False, ""))

    def fake_check_languagetool_available(*, auto_start: bool = False):
        lt_calls.append(auto_start)
        return True

    monkeypatch.setattr(runtime.deps, "_check_languagetool_available", fake_check_languagetool_available)
    monkeypatch.setitem(sys.modules, "torch", type("TorchModule", (), {"cuda": type("Cuda", (), {"is_available": staticmethod(lambda: False)})()})())

    caps = runtime._get_runtime_service_capabilities()

    assert caps["languagetool"] is True
    assert lt_calls == [True]
