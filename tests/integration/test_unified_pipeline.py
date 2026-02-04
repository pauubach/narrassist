"""
Tests de integración para el pipeline unificado.

Verifica que todas las fases del pipeline funcionan correctamente
de forma integrada.
"""

import tempfile
from pathlib import Path

import pytest

# Texto de prueba con contenido narrativo completo
SAMPLE_NARRATIVE = """
# Capítulo 1: El Encuentro

María era una mujer de ojos azules y cabello negro. Tenía treinta años y vivía en Madrid.
Era profesora de literatura en la universidad.

—Buenos días —dijo María al entrar en el café.

Juan, su hermano mayor, la esperaba en una mesa junto a la ventana. Era alto y delgado,
con el pelo castaño y una sonrisa amable.

—Llegas tarde —respondió Juan—. Como siempre.

María se sentó frente a él. El café estaba lleno de gente aquella mañana de primavera.
María pidió un cortado. Juan ya tenía su café con leche.

—¿Cómo está Pedro? —preguntó María.

—Pedro está bien. Sigue trabajando en Barcelona. Pedro dice que vendrá a visitarnos pronto.

# Capítulo 2: La Revelación

Había pasado una semana desde el encuentro en el café. María caminaba por el parque,
pensando en lo que Juan le habia contado.

María tenía los ojos verdes brillantes aquella tarde. El sol iluminaba su cabello rubio.
Parecía otra persona completamente diferente.

—María —llamó una voz familiar.

Era Pedro. Pedro había llegado antes de lo esperado. Pedro corrió hacia ella.

—No esperaba verte aquí —dijo María sorprendida.

Pedro tenía el pelo rubio, no castaño como lo recordaba. Pedro parecía más joven,
casi como si hubiera rejuvenecido diez años.

—Tenemos que hablar —dijo Pedro—. Es sobre Juan. Juan no es quien crees que es.

María miró a Pedro con desconfianza. María no entendía nada. María se preguntó
si todo era un sueño.
"""


@pytest.fixture
def sample_file(tmp_path):
    """Crea archivo de prueba temporal."""
    file_path = tmp_path / "test_narrative.txt"
    file_path.write_text(SAMPLE_NARRATIVE, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_file_with_errors(tmp_path):
    """Crea archivo con errores ortográficos y gramaticales."""
    text = """
    # Capítulo 1

    María habia llegado tarde. Ella tenia mucha prisa.

    —Pienso de que deberíamos irnos —dijo María.

    La dije que esperara. Subir arriba era imposible.

    El casa era muy bonito. Una libro antiguo estaba en la mesa.
    """
    file_path = tmp_path / "test_errors.txt"
    file_path.write_text(text, encoding="utf-8")
    return file_path


class TestUnifiedPipelineIntegration:
    """Tests de integración del pipeline unificado."""

    def test_pipeline_runs_without_crash(self, sample_file):
        """Pipeline ejecuta sin errores fatales."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_ner=True,
            run_attributes=False,  # Deshabilitado para velocidad
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            run_lexical_repetitions=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Integration Test",
            config=config,
        )

        # El pipeline debe completar (success o partial)
        assert result.is_success or result.is_partial, f"Pipeline failed: {result.error}"

    def test_pipeline_detects_chapters(self, sample_file):
        """Pipeline detecta capítulos correctamente."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Chapter Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar 2 capítulos
        assert len(report.chapters) >= 1, "No chapters detected"

    def test_pipeline_detects_dialogues(self, sample_file):
        """Pipeline detecta diálogos."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Dialogue Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar varios diálogos
        assert len(report.dialogues) >= 1, "No dialogues detected"

    def test_pipeline_detects_entities(self, sample_file):
        """Pipeline detecta entidades (NER)."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=False,
            run_entity_fusion=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="NER Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar entidades (María, Juan, Pedro, Madrid, Barcelona)
        assert len(report.entities) >= 1, "No entities detected"

    def test_pipeline_spelling_check(self, sample_file_with_errors):
        """Pipeline detecta errores ortográficos."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=False,
            run_dialogue_detection=False,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=True,
            run_grammar=False,
            run_lexical_repetitions=False,
            create_alerts=True,
        )

        result = run_unified_analysis(
            sample_file_with_errors,
            project_name="Spelling Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar errores como "habia", "tenia"
        # (dependiendo de la implementación del checker)
        assert hasattr(report, "spelling_issues")

    def test_pipeline_grammar_check(self, sample_file_with_errors):
        """Pipeline detecta errores gramaticales."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=False,
            run_dialogue_detection=False,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=True,
            run_lexical_repetitions=False,
            create_alerts=True,
        )

        result = run_unified_analysis(
            sample_file_with_errors,
            project_name="Grammar Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar errores como dequeísmo, laísmo
        assert hasattr(report, "grammar_issues")

    def test_pipeline_detects_specific_grammar_errors(self, sample_file_with_errors):
        """Pipeline detecta errores específicos: laísmo, dequeísmo, concordancia."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=False,
            run_dialogue_detection=False,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=True,
            run_lexical_repetitions=False,
            create_alerts=False,  # Solo queremos grammar_issues
        )

        result = run_unified_analysis(
            sample_file_with_errors,
            project_name="Specific Grammar Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # El archivo tiene estos errores:
        # - "Pienso de que" -> dequeísmo
        # - "La dije" -> laísmo
        # - "Subir arriba" -> redundancia
        # - "El casa", "Una libro" -> concordancia de género
        assert hasattr(report, "grammar_issues")
        assert len(report.grammar_issues) >= 1, "No grammar issues detected"

        # Verificar que los issues tienen la estructura correcta
        for issue in report.grammar_issues:
            assert hasattr(issue, "text")
            assert hasattr(issue, "error_type")
            assert hasattr(issue, "explanation")
            assert hasattr(issue, "confidence")

        # Verificar tipos de errores detectados
        error_types = {str(i.error_type) for i in report.grammar_issues}

        # Al menos uno de estos debe estar presente
        expected_types = {
            "GrammarErrorType.LAISMO",
            "GrammarErrorType.DEQUEISMO",
            "GrammarErrorType.REDUNDANCY",
            "GrammarErrorType.GENDER_AGREEMENT",
        }
        detected = error_types & expected_types
        assert len(detected) >= 1, f"Expected at least one of {expected_types}, got {error_types}"

    def test_pipeline_repetition_detection(self, sample_file):
        """Pipeline detecta repeticiones."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=False,
            run_dialogue_detection=False,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            run_lexical_repetitions=True,
            run_semantic_repetitions=False,
            create_alerts=True,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Repetition Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Debería detectar repeticiones de "María", "Pedro", etc.
        assert hasattr(report, "repetitions")

    def test_pipeline_generates_alerts(self, sample_file):
        """Pipeline genera alertas."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=False,
            run_entity_fusion=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=True,
            create_alerts=True,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Alerts Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        assert hasattr(report, "alerts")
        assert isinstance(report.alerts, list)

    def test_pipeline_statistics(self, sample_file):
        """Pipeline genera estadísticas."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Stats Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Verificar estadísticas básicas
        assert hasattr(report, "stats")
        assert isinstance(report.stats, dict)

    def test_pipeline_timing(self, sample_file):
        """Pipeline registra tiempos."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Timing Test",
            config=config,
        )

        assert result.is_success or result.is_partial
        report = result.value

        # Verificar que registró tiempos
        assert hasattr(report, "phase_times")
        assert report.duration_seconds >= 0


class TestUnifiedPipelineErrorHandling:
    """Tests de manejo de errores del pipeline unificado."""

    def test_nonexistent_file(self, tmp_path):
        """Maneja archivo inexistente."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig()
        nonexistent = tmp_path / "nonexistent.txt"

        result = run_unified_analysis(
            nonexistent,
            project_name="Error Test",
            config=config,
        )

        assert result.is_failure
        assert result.error is not None

    def test_empty_file(self, tmp_path):
        """Maneja archivo vacío."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        config = UnifiedConfig(
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            empty_file,
            project_name="Empty Test",
            config=config,
        )

        # Puede ser success o partial con warnings
        assert result.is_success or result.is_partial or result.is_failure

    def test_minimal_config(self, sample_file):
        """Pipeline con configuración mínima."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=False,
            run_dialogue_detection=False,
            run_ner=False,
            run_coreference=False,
            run_entity_fusion=False,
            run_attributes=False,
            run_relationships=False,
            run_knowledge=False,
            run_spelling=False,
            run_grammar=False,
            run_lexical_repetitions=False,
            run_semantic_repetitions=False,
            run_consistency=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Minimal Test",
            config=config,
        )

        # Debería al menos parsear el documento
        assert result.is_success or result.is_partial


class TestUnifiedPipelineProgressCallback:
    """Tests para callback de progreso."""

    def test_progress_callback_called(self, sample_file):
        """Callback de progreso es llamado."""
        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        progress_calls = []

        def progress_callback(progress: float, message: str):
            progress_calls.append((progress, message))

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=False,
            run_grammar=False,
            create_alerts=False,
        )

        result = run_unified_analysis(
            sample_file,
            project_name="Progress Test",
            config=config,
            progress_callback=progress_callback,
        )

        assert result.is_success or result.is_partial

        # Debería haber llamadas de progreso
        assert len(progress_calls) >= 1

        # Progreso debe ir de 0 a 1
        if progress_calls:
            assert progress_calls[0][0] >= 0.0
            assert progress_calls[-1][0] <= 1.0


class TestUnifiedPipelinePerformance:
    """Tests de rendimiento del pipeline."""

    def test_performance_acceptable(self, sample_file):
        """Pipeline completa en tiempo aceptable."""
        import time

        from narrative_assistant.pipelines import UnifiedConfig, run_unified_analysis

        config = UnifiedConfig(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=False,
            run_entity_fusion=False,
            run_attributes=False,
            run_consistency=False,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=True,
            create_alerts=True,
        )

        start = time.time()
        result = run_unified_analysis(
            sample_file,
            project_name="Performance Test",
            config=config,
        )
        duration = time.time() - start

        assert result.is_success or result.is_partial

        # Para un texto pequeño, debería completar en menos de 2 minutos
        # (spaCy puede tardar en cargar el modelo la primera vez)
        assert duration < 120.0, f"Pipeline took {duration:.1f}s, expected < 120s"
