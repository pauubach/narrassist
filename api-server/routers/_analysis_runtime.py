"""Helpers de capabilities runtime para el pipeline de analisis."""

from __future__ import annotations

import deps

from narrative_assistant.llm.ollama_manager import ensure_ollama_ready

# Mapa de requisitos de servicio por metodo NLP (consistente con projects.py).
_METHOD_SERVICE_REQUIREMENTS: dict[tuple[str, str], str] = {
    ("coreference", "llm"): "ollama",
    ("ner", "llm"): "ollama",
    ("grammar", "llm"): "ollama",
    ("spelling", "llm_arbitrator"): "ollama",
    ("character_knowledge", "llm"): "ollama",
    ("character_knowledge", "hybrid"): "ollama",
    ("grammar", "languagetool"): "languagetool",
    ("spelling", "languagetool"): "languagetool",
    ("spelling", "beto"): "gpu",
}


def _get_runtime_service_capabilities() -> dict[str, bool]:
    """Obtiene disponibilidad runtime de servicios para validacion estricta."""
    caps = {
        "ollama": False,
        "languagetool": False,
        "gpu": False,
    }

    try:
        ollama_ready, _ = ensure_ollama_ready(
            install_if_missing=False,
            start_if_stopped=True,
        )
        caps["ollama"] = bool(ollama_ready)
    except Exception:
        pass

    try:
        caps["languagetool"] = bool(deps._check_languagetool_available(auto_start=True))
    except Exception:
        pass

    try:
        import torch

        caps["gpu"] = bool(torch.cuda.is_available())
    except Exception:
        pass

    return caps


def _filter_nlp_methods_by_runtime_capabilities(
    selected_methods: dict[str, list[str]],
    runtime_caps: dict[str, bool] | None = None,
) -> tuple[dict[str, list[str]], list[str]]:
    """
    Filtra metodos NLP no viables en runtime antes de ejecutar fases.

    Devuelve:
    - metodos filtrados (bloqueo estricto de combinaciones inviables)
    - warnings legibles para logs/UI
    """
    runtime_caps = runtime_caps or _get_runtime_service_capabilities()
    filtered: dict[str, list[str]] = {}
    warnings: list[str] = []

    for category, methods in selected_methods.items():
        if not isinstance(category, str) or not isinstance(methods, list):
            continue

        allowed: list[str] = []
        for method in methods:
            if not isinstance(method, str):
                continue
            normalized_method = method.strip()
            if not normalized_method:
                continue

            service = _METHOD_SERVICE_REQUIREMENTS.get((category, normalized_method))
            if service and not runtime_caps.get(service, False):
                warnings.append(
                    f"Metodo '{normalized_method}' en '{category}' no esta disponible ahora y se omitira."
                )
                continue
            allowed.append(normalized_method)

        filtered[category] = allowed

    return filtered, warnings
