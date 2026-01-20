"""
Tests unitarios para el pipeline unificado.

Verifica que todos los componentes se importen correctamente
y que las configuraciones funcionen.
"""

import pytest


class TestUnifiedPipelineImports:
    """Tests de importación del pipeline unificado."""

    def test_import_unified_analysis_module(self):
        """Verifica importación del módulo unified_analysis."""
        from narrative_assistant.pipelines import unified_analysis
        assert unified_analysis is not None

    def test_import_run_unified_analysis(self):
        """Verifica importación de run_unified_analysis."""
        from narrative_assistant.pipelines import run_unified_analysis
        assert callable(run_unified_analysis)

    def test_import_unified_config(self):
        """Verifica importación de UnifiedConfig."""
        from narrative_assistant.pipelines import UnifiedConfig
        assert UnifiedConfig is not None

    def test_import_unified_report(self):
        """Verifica importación de UnifiedReport."""
        from narrative_assistant.pipelines import UnifiedReport
        assert UnifiedReport is not None

    def test_import_unified_pipeline_class(self):
        """Verifica importación de UnifiedAnalysisPipeline."""
        from narrative_assistant.pipelines import UnifiedAnalysisPipeline
        assert UnifiedAnalysisPipeline is not None

    def test_import_analysis_phase(self):
        """Verifica importación de AnalysisPhase."""
        from narrative_assistant.pipelines import AnalysisPhase
        assert AnalysisPhase is not None

    def test_import_analysis_context(self):
        """Verifica importación de AnalysisContext."""
        from narrative_assistant.pipelines import AnalysisContext
        assert AnalysisContext is not None


class TestUnifiedConfig:
    """Tests para UnifiedConfig."""

    def test_default_config(self):
        """Configuración por defecto tiene valores esperados."""
        from narrative_assistant.pipelines import UnifiedConfig

        config = UnifiedConfig()

        # Fases principales
        assert config.run_structure is True
        assert config.run_dialogue_detection is True
        assert config.run_ner is True
        assert config.run_coreference is True
        assert config.run_entity_fusion is True
        assert config.run_attributes is True

        # Análisis de calidad
        assert config.run_spelling is True
        assert config.run_grammar is True
        assert config.run_lexical_repetitions is True

        # Opcionales (costosos)
        assert config.run_relationships is False
        assert config.run_knowledge is False
        assert config.run_semantic_repetitions is False
        assert config.use_llm is False

    def test_custom_config(self):
        """Configuración personalizada funciona."""
        from narrative_assistant.pipelines import UnifiedConfig

        config = UnifiedConfig(
            run_spelling=False,
            run_grammar=False,
            run_relationships=True,
            use_llm=True,
            min_confidence=0.7,
        )

        assert config.run_spelling is False
        assert config.run_grammar is False
        assert config.run_relationships is True
        assert config.use_llm is True
        assert config.min_confidence == 0.7

    def test_config_thresholds(self):
        """Umbrales de configuración tienen valores por defecto."""
        from narrative_assistant.pipelines import UnifiedConfig

        config = UnifiedConfig()

        assert config.min_confidence == 0.5
        assert config.spelling_min_confidence == 0.6
        assert config.grammar_min_confidence == 0.5
        assert config.repetition_min_distance == 50


class TestAnalysisPhase:
    """Tests para AnalysisPhase enum."""

    def test_all_phases_exist(self):
        """Todas las fases esperadas existen."""
        from narrative_assistant.pipelines import AnalysisPhase

        expected_phases = [
            "PARSING",
            "STRUCTURE",
            "BASE_EXTRACTION",
            "RESOLUTION",
            "DEEP_EXTRACTION",
            "QUALITY",
            "CONSISTENCY",
            "ALERTS",
        ]

        for phase_name in expected_phases:
            assert hasattr(AnalysisPhase, phase_name), f"Missing phase: {phase_name}"

    def test_phase_values(self):
        """Fases tienen valores string correctos."""
        from narrative_assistant.pipelines import AnalysisPhase

        assert AnalysisPhase.PARSING.value == "parsing"
        assert AnalysisPhase.QUALITY.value == "quality"
        assert AnalysisPhase.ALERTS.value == "alerts"


class TestAnalysisContext:
    """Tests para AnalysisContext."""

    def test_context_defaults(self):
        """Contexto tiene valores por defecto vacíos."""
        from narrative_assistant.pipelines import AnalysisContext

        ctx = AnalysisContext()

        assert ctx.project_id == 0
        assert ctx.session_id == 0
        assert ctx.document_path == ""
        assert ctx.full_text == ""
        assert ctx.chapters == []
        assert ctx.entities == []
        assert ctx.dialogues == []
        assert ctx.alerts == []
        assert ctx.errors == []

    def test_context_with_data(self):
        """Contexto acepta datos."""
        from narrative_assistant.pipelines import AnalysisContext

        ctx = AnalysisContext(
            project_id=1,
            document_path="/test/path.txt",
            full_text="Test content",
        )

        assert ctx.project_id == 1
        assert ctx.document_path == "/test/path.txt"
        assert ctx.full_text == "Test content"


class TestUnifiedPipelineClass:
    """Tests para la clase UnifiedAnalysisPipeline."""

    def test_pipeline_instantiation(self):
        """Pipeline se puede instanciar."""
        from narrative_assistant.pipelines import UnifiedAnalysisPipeline, UnifiedConfig

        pipeline = UnifiedAnalysisPipeline()
        assert pipeline is not None
        assert pipeline.config is not None

    def test_pipeline_with_custom_config(self):
        """Pipeline acepta configuración personalizada."""
        from narrative_assistant.pipelines import UnifiedAnalysisPipeline, UnifiedConfig

        config = UnifiedConfig(run_spelling=False)
        pipeline = UnifiedAnalysisPipeline(config)

        assert pipeline.config.run_spelling is False

    def test_pipeline_has_analyze_method(self):
        """Pipeline tiene método analyze."""
        from narrative_assistant.pipelines import UnifiedAnalysisPipeline

        pipeline = UnifiedAnalysisPipeline()
        assert hasattr(pipeline, "analyze")
        assert callable(pipeline.analyze)


class TestUnifiedReport:
    """Tests para UnifiedReport."""

    def test_report_creation(self):
        """Report se puede crear."""
        from narrative_assistant.pipelines import UnifiedReport

        report = UnifiedReport(
            project_id=1,
            session_id=1,
            document_path="/test.txt",
            fingerprint="abc123",
        )

        assert report.project_id == 1
        assert report.session_id == 1
        assert report.document_path == "/test.txt"
        assert report.fingerprint == "abc123"

    def test_report_defaults(self):
        """Report tiene valores por defecto."""
        from narrative_assistant.pipelines import UnifiedReport

        report = UnifiedReport(
            project_id=1,
            session_id=1,
            document_path="/test.txt",
            fingerprint="abc123",
        )

        assert report.entities == []
        assert report.attributes == []
        assert report.relationships == []
        assert report.alerts == []
        assert report.chapters == []
        assert report.dialogues == []
        assert report.spelling_issues == []
        assert report.grammar_issues == []
        assert report.repetitions == []

    def test_report_duration(self):
        """Report calcula duración correctamente."""
        from narrative_assistant.pipelines import UnifiedReport
        from datetime import datetime, timedelta

        start = datetime.now()
        end = start + timedelta(seconds=10)

        report = UnifiedReport(
            project_id=1,
            session_id=1,
            document_path="/test.txt",
            fingerprint="abc123",
            start_time=start,
            end_time=end,
        )

        assert report.duration_seconds == pytest.approx(10.0, abs=0.1)
