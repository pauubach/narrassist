"""Tests E2E: PATCH settings → apply_license_and_settings → verificar config pipeline.

Verifica que la cadena completa funciona:
1. _validate_analysis_features() sanea el payload del usuario
2. apply_license_and_settings() aplica los flags y métodos al pipeline
3. El análisis respeta la configuración del usuario

Sin spaCy, Ollama, LanguageTool ni GPU. Solo lógica de orquestación.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import apply_license_and_settings  # noqa: E402
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


def _make_ctx(pipeline_flags: dict, nlp_methods: dict | None = None, word_count: int = 1200):
    """Crea un contexto de pipeline con settings configurados."""
    settings = {
        "analysis_features": {
            "pipeline_flags": pipeline_flags,
        }
    }
    if nlp_methods is not None:
        settings["analysis_features"]["nlp_methods"] = nlp_methods

    project = SimpleNamespace(settings=settings)
    return {
        "project": project,
        "analysis_mode": "standard",
        "word_count": word_count,
    }


# ============================================================================
# Test 1: grammar=false desactiva la fase de gramática
# ============================================================================


def test_grammar_disabled_skips_phase():
    """pipeline_flags.grammar=false → config.run_grammar is False."""
    ctx = _make_ctx(pipeline_flags={"grammar": False})
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    assert ctx["analysis_config"].run_grammar is False


# ============================================================================
# Test 2: Múltiples flags desactivados simultáneamente
# ============================================================================


def test_multiple_flags_disabled():
    """Desactivar profiling + network + OOC → los 3 flags en False."""
    ctx = _make_ctx(pipeline_flags={
        "character_profiling": False,
        "network_analysis": False,
        "ooc_detection": False,
    })
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    config = ctx["analysis_config"]
    assert config.run_character_profiling is False
    assert config.run_network_analysis is False
    assert config.run_ooc_detection is False


# ============================================================================
# Test 3: nlp_methods se propagan correctamente al contexto
# ============================================================================


def test_nlp_methods_selection_propagates():
    """nlp_methods seleccionados se escriben en ctx['selected_nlp_methods']."""
    ctx = _make_ctx(
        pipeline_flags={},
        nlp_methods={
            "coreference": ["morpho", "heuristics"],
            "ner": ["spacy"],
            "grammar": ["spacy_rules"],
            "spelling": ["patterns"],
            "character_knowledge": ["rules"],
        }
    )
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    selected = ctx["selected_nlp_methods"]
    assert selected["coreference"] == ["morpho", "heuristics"]
    assert selected["ner"] == ["spacy"]
    assert selected["grammar"] == ["spacy_rules"]
    assert "llm" not in selected.get("coreference", [])


# ============================================================================
# Test 4: Categoría NLP vacía → flag del pipeline desactivado
# ============================================================================


def test_empty_nlp_category_disables_flag():
    """grammar=[] y spelling=[] → run_grammar y run_spelling en False."""
    ctx = _make_ctx(
        pipeline_flags={},
        nlp_methods={
            "grammar": [],
            "spelling": [],
        }
    )
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    config = ctx["analysis_config"]
    assert config.run_grammar is False
    assert config.run_spelling is False


# ============================================================================
# Test 5: Roundtrip completo: validate → apply → verify
# ============================================================================


def test_full_roundtrip_validate_then_apply():
    """_validate_analysis_features() → apply_license_and_settings() → config coherente."""
    # Simular payload del usuario (como llegaría del PATCH)
    user_payload = {
        "schema_version": 1,
        "pipeline_flags": {
            "grammar": False,
            "character_profiling": False,
            "network_analysis": True,
        },
        "nlp_methods": {
            "coreference": ["heuristics"],
            "ner": ["spacy", "gazetteer"],
        }
    }

    # Paso 1: Validar (como hace el PATCH endpoint)
    sanitized, warnings = _validate_analysis_features(user_payload)

    # Verificar sanitización
    assert sanitized["pipeline_flags"]["grammar"] is False
    assert sanitized["pipeline_flags"]["character_profiling"] is False
    assert sanitized["pipeline_flags"]["network_analysis"] is True
    assert sanitized["nlp_methods"]["coreference"] == ["heuristics"]
    assert sanitized["nlp_methods"]["ner"] == ["spacy", "gazetteer"]
    assert len(warnings) == 0

    # Paso 2: Aplicar al pipeline (como hace apply_license_and_settings)
    project = SimpleNamespace(
        settings={"analysis_features": sanitized}
    )
    ctx = {
        "project": project,
        "analysis_mode": "standard",
        "word_count": 1500,
    }
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    # Paso 3: Verificar que el pipeline respeta la config
    config = ctx["analysis_config"]
    assert config.run_grammar is False
    assert config.run_character_profiling is False
    assert config.run_network_analysis is True

    selected = ctx["selected_nlp_methods"]
    assert selected["coreference"] == ["heuristics"]
    assert selected["ner"] == ["spacy", "gazetteer"]


# ============================================================================
# Test 6: spelling flag controla spelling dentro de grammar
# ============================================================================


def test_spelling_flag_controls_spelling_in_grammar():
    """pipeline_flags.spelling=false → config.run_spelling is False."""
    ctx = _make_ctx(pipeline_flags={"spelling": False, "grammar": True})
    tracker = _DummyTracker()

    apply_license_and_settings(ctx, tracker)

    config = ctx["analysis_config"]
    assert config.run_spelling is False
    assert config.run_grammar is True
