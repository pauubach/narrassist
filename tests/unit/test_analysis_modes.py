"""
Tests para modos de análisis y auto-degradación por word count.

Verifica:
1. UnifiedConfig.light() tiene los flags correctos
2. Todos los modos se crean correctamente
3. Auto-degradación: 80k palabras → LIGHT, 120k → EXPRESS, 30k → STANDARD
4. Dependencias se resuelven correctamente en modo LIGHT
"""

import pytest

from narrative_assistant.pipelines.unified_analysis import UnifiedConfig


class TestUnifiedConfigLight:
    """Verifica que el modo LIGHT tiene los flags esperados."""

    def test_light_enables_ner(self):
        config = UnifiedConfig.light()
        assert config.run_ner is True

    def test_light_disables_fusion(self):
        config = UnifiedConfig.light()
        assert config.run_entity_fusion is False

    def test_light_disables_coreference(self):
        config = UnifiedConfig.light()
        assert config.run_coreference is False

    def test_light_disables_llm(self):
        config = UnifiedConfig.light()
        assert config.use_llm is False

    def test_light_enables_grammar(self):
        config = UnifiedConfig.light()
        assert config.run_grammar is True
        assert config.run_spelling is True

    def test_light_enables_consistency(self):
        config = UnifiedConfig.light()
        assert config.run_consistency is True

    def test_light_enables_attributes(self):
        config = UnifiedConfig.light()
        assert config.run_attributes is True

    def test_light_disables_relationships(self):
        config = UnifiedConfig.light()
        assert config.run_relationships is False

    def test_light_disables_heavy_features(self):
        config = UnifiedConfig.light()
        assert config.run_knowledge is False
        assert config.run_voice_profiles is False
        assert config.run_semantic_repetitions is False
        assert config.run_focalization is False
        assert config.run_emotional is False
        assert config.run_sentiment is False
        assert config.run_pacing is False

    def test_light_max_workers_reduced(self):
        config = UnifiedConfig.light()
        assert config.max_workers == 2

    def test_light_enables_lexical_repetitions(self):
        config = UnifiedConfig.light()
        assert config.run_lexical_repetitions is True

    def test_light_enables_sticky_sentences(self):
        config = UnifiedConfig.light()
        assert config.run_sticky_sentences is True


class TestAllModes:
    """Verifica que todos los modos se crean correctamente."""

    @pytest.mark.parametrize("mode_name", ["express", "light", "standard", "deep", "complete"])
    def test_mode_creation(self, mode_name):
        factory = getattr(UnifiedConfig, mode_name)
        config = factory()
        assert isinstance(config, UnifiedConfig)

    def test_express_disables_everything_heavy(self):
        config = UnifiedConfig.express()
        assert config.run_ner is False
        assert config.run_entity_fusion is False
        assert config.run_coreference is False
        assert config.use_llm is False

    def test_standard_enables_ner_and_fusion(self):
        config = UnifiedConfig.standard()
        assert config.run_ner is True
        assert config.run_entity_fusion is True
        assert config.run_coreference is True
        assert config.use_llm is True

    def test_deep_enables_relationships(self):
        config = UnifiedConfig.deep()
        assert config.run_relationships is True
        assert config.run_knowledge is True

    def test_mode_ordering_by_resource_cost(self):
        """Verificar que cada modo sucesivo habilita más features."""
        express = UnifiedConfig.express()
        light = UnifiedConfig.light()
        standard = UnifiedConfig.standard()

        # Express < Light: light tiene NER
        assert not express.run_ner
        assert light.run_ner

        # Light < Standard: standard tiene fusion + LLM
        assert not light.run_entity_fusion
        assert standard.run_entity_fusion
        assert not light.use_llm
        assert standard.use_llm


class TestAutoDegradation:
    """Verifica la lógica de auto-degradación por word count."""

    def test_auto_selects_standard_for_small_docs(self):
        """Documentos <50k palabras → STANDARD."""
        mode = _resolve_mode("auto", 30_000)
        assert mode == "standard"

    def test_auto_selects_light_for_medium_docs(self):
        """Documentos 50k-100k palabras → LIGHT."""
        mode = _resolve_mode("auto", 80_000)
        assert mode == "light"

    def test_auto_selects_express_for_huge_docs(self):
        """Documentos >100k palabras → EXPRESS."""
        mode = _resolve_mode("auto", 120_000)
        assert mode == "express"

    def test_auto_boundary_50k(self):
        """Exactamente 50k → STANDARD (umbral exclusivo)."""
        mode = _resolve_mode("auto", 50_000)
        assert mode == "standard"

    def test_auto_boundary_50001(self):
        """50001 → LIGHT."""
        mode = _resolve_mode("auto", 50_001)
        assert mode == "light"

    def test_auto_boundary_100k(self):
        """Exactamente 100k → LIGHT (umbral exclusivo)."""
        mode = _resolve_mode("auto", 100_000)
        assert mode == "light"

    def test_auto_boundary_100001(self):
        """100001 → EXPRESS."""
        mode = _resolve_mode("auto", 100_001)
        assert mode == "express"

    def test_manual_mode_ignores_word_count(self):
        """Modo manual siempre respeta la selección del usuario."""
        assert _resolve_mode("light", 10_000) == "light"
        assert _resolve_mode("express", 10_000) == "express"
        assert _resolve_mode("standard", 200_000) == "standard"
        assert _resolve_mode("deep", 200_000) == "deep"

    def test_auto_with_zero_word_count(self):
        """Si word_count=0 (antes del parsing), usar STANDARD."""
        mode = _resolve_mode("auto", 0)
        assert mode == "standard"


def _resolve_mode(requested_mode: str, word_count: int) -> str:
    """Replica la lógica de auto-degradación del backend."""
    valid_modes = {"express", "light", "standard", "deep", "complete"}

    if requested_mode in valid_modes:
        return requested_mode

    # Auto mode
    if word_count > 100_000:
        return "express"
    elif word_count > 50_000:
        return "light"
    else:
        return "standard"


class TestDependencyValidation:
    """Verifica que las dependencias se resuelven correctamente."""

    def test_light_consistency_works_with_attributes(self):
        """LIGHT tiene attributes=True, así que consistency puede funcionar."""
        config = UnifiedConfig.light()
        assert config.run_attributes is True
        assert config.run_consistency is True

    def test_express_disables_consistency(self):
        """EXPRESS sin attributes desactiva consistency (dependencia)."""
        config = UnifiedConfig.express()
        # _validate_dependencies() debería haberlo corregido
        assert config.run_consistency is False

    def test_light_no_fusion_without_coreference(self):
        """LIGHT sin coreference no debería tener entity_fusion."""
        config = UnifiedConfig.light()
        assert config.run_coreference is False
        assert config.run_entity_fusion is False
