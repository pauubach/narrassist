import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import apply_license_and_settings  # noqa: E402
from routers._enrichment_phases import _resolve_character_knowledge_mode  # noqa: E402
from routers.projects import _validate_analysis_features  # noqa: E402


class _DummyTracker:
    def __init__(self):
        self.metrics = {}

    def set_metric(self, key: str, value):
        self.metrics[key] = value


@pytest.fixture(autouse=True)
def _disable_licensing(monkeypatch):
    import narrative_assistant.licensing.gating as licensing_gating

    monkeypatch.setattr(licensing_gating, "is_licensing_enabled", lambda: False)


def test_apply_license_and_settings_applies_pipeline_flags_and_selected_methods(monkeypatch):
    project = SimpleNamespace(
        settings={
            "analysis_features": {
                "pipeline_flags": {
                    "multi_model_voting": False,
                    "name_variants": False,
                    "grammar": True,
                    "spelling": False,
                },
                "nlp_methods": {
                    "coreference": ["heuristics"],
                    "ner": ["spacy"],
                    "grammar": ["languagetool"],
                    "spelling": ["patterns"],
                    "character_knowledge": ["rules"],
                },
            }
        }
    )
    ctx = {
        "project": project,
        "analysis_mode": "standard",
        "word_count": 1200,
    }
    tracker = _DummyTracker()

    monkeypatch.setattr(
        "routers._analysis_phases._get_runtime_service_capabilities",
        lambda: {"ollama": True, "languagetool": True, "gpu": True},
    )

    apply_license_and_settings(ctx, tracker)

    analysis_config = ctx["analysis_config"]
    selected_methods = ctx["selected_nlp_methods"]

    assert analysis_config.run_multi_model_voting is False
    assert analysis_config.run_name_variants is False
    assert analysis_config.run_grammar is True
    assert analysis_config.run_spelling is False

    assert selected_methods["coreference"] == ["heuristics"]
    assert selected_methods["ner"] == ["spacy"]
    assert selected_methods["grammar"] == ["languagetool"]
    assert selected_methods["spelling"] == ["patterns"]


def test_apply_license_and_settings_disables_pipeline_when_nlp_categories_are_empty():
    project = SimpleNamespace(
        settings={
            "analysis_features": {
                "pipeline_flags": {},
                "nlp_methods": {
                    "ner": [],
                    "coreference": [],
                    "grammar": [],
                    "spelling": [],
                    "character_knowledge": [],
                },
            }
        }
    )
    ctx = {
        "project": project,
        "analysis_mode": "standard",
        "word_count": 800,
    }
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    analysis_config = ctx["analysis_config"]
    assert analysis_config.run_ner is False
    assert analysis_config.run_coreference is False
    assert analysis_config.run_grammar is False
    assert analysis_config.run_spelling is False
    assert analysis_config.run_knowledge is False


# ============================================================================
# Tests de validación contra capabilities (CR-03 post-MVP)
# ============================================================================


def test_validate_warns_ollama_unavailable():
    """Método 'llm' con Ollama no disponible genera warning."""
    features = {
        "schema_version": 1,
        "pipeline_flags": {},
        "nlp_methods": {
            "coreference": ["llm", "heuristics"],
            "ner": ["spacy", "llm"],
            "character_knowledge": ["hybrid"],
        },
    }
    capabilities = {"ollama_available": False, "languagetool_available": True, "has_gpu": True}

    _, warnings = _validate_analysis_features(features, capabilities=capabilities)

    ollama_warnings = [w for w in warnings if "Ollama" in w]
    # 3 métodos requieren Ollama: coreference/llm, ner/llm, character_knowledge/hybrid
    assert len(ollama_warnings) == 3
    assert any("coreference" in w and "'llm'" in w for w in ollama_warnings)
    assert any("ner" in w and "'llm'" in w for w in ollama_warnings)
    assert any("character_knowledge" in w and "'hybrid'" in w for w in ollama_warnings)


def test_validate_warns_languagetool_unavailable():
    """Método 'languagetool' con servicio no disponible genera warning."""
    features = {
        "schema_version": 1,
        "pipeline_flags": {},
        "nlp_methods": {
            "grammar": ["spacy_rules", "languagetool"],
            "spelling": ["languagetool", "patterns"],
        },
    }
    capabilities = {"ollama_available": True, "languagetool_available": False, "has_gpu": True}

    _, warnings = _validate_analysis_features(features, capabilities=capabilities)

    lt_warnings = [w for w in warnings if "LanguageTool" in w]
    assert len(lt_warnings) == 2
    assert any("grammar" in w for w in lt_warnings)
    assert any("spelling" in w for w in lt_warnings)


def test_validate_no_warnings_when_services_available():
    """Con todos los servicios disponibles, no genera warnings de capabilities."""
    features = {
        "schema_version": 1,
        "pipeline_flags": {},
        "nlp_methods": {
            "coreference": ["llm", "heuristics"],
            "grammar": ["languagetool", "spacy_rules"],
        },
    }
    capabilities = {"ollama_available": True, "languagetool_available": True, "has_gpu": True}

    _, warnings = _validate_analysis_features(features, capabilities=capabilities)

    assert len(warnings) == 0


def test_validate_no_capability_warnings_when_none():
    """capabilities=None (backward compat) → 0 warnings de capabilities."""
    features = {
        "schema_version": 1,
        "pipeline_flags": {},
        "nlp_methods": {
            "coreference": ["llm"],
            "grammar": ["languagetool"],
        },
    }

    _, warnings = _validate_analysis_features(features, capabilities=None)

    assert len(warnings) == 0


def test_character_knowledge_mode_respects_selection_and_llm_enabled():
    """character_knowledge=['llm'] con use_llm=True -> modo LLM."""
    mode = _resolve_character_knowledge_mode(
        {
            "selected_nlp_methods": {"character_knowledge": ["llm"]},
            "analysis_config": SimpleNamespace(use_llm=True),
        }
    )
    assert mode.value == "llm"


def test_character_knowledge_mode_falls_back_when_llm_disabled():
    """character_knowledge=['hybrid'] con use_llm=False -> fallback RULES."""
    mode = _resolve_character_knowledge_mode(
        {
            "selected_nlp_methods": {"character_knowledge": ["hybrid"]},
            "analysis_config": SimpleNamespace(use_llm=False),
        }
    )
    assert mode.value == "rules"


def test_apply_license_and_settings_filters_unavailable_runtime_methods(monkeypatch):
    """Métodos no disponibles en runtime se bloquean antes de ejecutar fases."""
    project = SimpleNamespace(
        settings={
            "analysis_features": {
                "pipeline_flags": {
                    "grammar": True,
                    "spelling": True,
                },
                "nlp_methods": {
                    "grammar": ["languagetool"],
                    "spelling": ["beto"],
                    "character_knowledge": ["llm"],
                },
            }
        }
    )
    ctx = {
        "project": project,
        "analysis_mode": "standard",
        "word_count": 2000,
    }
    tracker = _DummyTracker()

    monkeypatch.setattr(
        "routers._analysis_phases._get_runtime_service_capabilities",
        lambda: {"ollama": False, "languagetool": False, "gpu": False},
    )

    apply_license_and_settings(ctx, tracker)

    selected = ctx["selected_nlp_methods"]
    config = ctx["analysis_config"]

    assert selected["grammar"] == []
    assert selected["spelling"] == []
    assert selected["character_knowledge"] == []
    assert config.run_grammar is False
    assert config.run_spelling is False
    assert config.run_knowledge is False
    assert "analysis_settings_warnings" in tracker.metrics
