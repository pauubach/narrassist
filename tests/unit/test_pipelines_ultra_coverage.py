"""
Ultra coverage boost - Tests finales para llegar a 60%+ en todos los pipelines.

Estrategia: Tests muy específicos para cada rama condicional y método interno.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def full_context():
    """Context con TODOS los atributos posibles poblados."""
    ctx = Mock()
    ctx.project_id = 1
    ctx.entities = [Mock(id=1, name="Juan"), Mock(id=2, name="María")]
    ctx.entity_map = {"juan": 1, "maría": 2}
    ctx.chapters = [
        {"number": 1, "content": "Cap 1", "start_char": 0, "end_char": 100},
        {"number": 2, "content": "Cap 2", "start_char": 100, "end_char": 200}
    ]
    ctx.dialogues = [{"start_char": 10, "end_char": 50, "speaker": "Juan"}]
    ctx.attributes = [Mock(), Mock()]
    ctx.temporal_markers = [Mock(), Mock()]
    ctx.voice_profiles = {"juan": Mock(), "maría": Mock()}
    ctx.inconsistencies = []
    ctx.alerts = []
    ctx.temporal_inconsistencies = []
    ctx.ooc_events = []
    ctx.knowledge_issues = []
    ctx.contradictions = []
    ctx.location_issues = []
    ctx.phase_times = {}
    ctx.relationships = []
    ctx.events = []
    ctx.timeline_events = []
    ctx.detected_issues = []
    ctx.corrections = []
    ctx.repetitions = []
    ctx.pacing_issues = []
    # Todas las listas posibles
    ctx.spelling_issues = []
    ctx.grammar_issues = []
    ctx.lexical_repetitions = []
    ctx.semantic_repetitions = []
    ctx.coherence_breaks = []
    ctx.voice_deviations = []
    ctx.pacing_analysis = {}
    ctx.sticky_sentences = []
    ctx.passive_sentences = []
    ctx.complex_sentences = []
    ctx.filler_words = []
    ctx.typography_issues = []
    ctx.pov_shifts = []
    ctx.reference_issues = []
    ctx.acronym_issues = []
    ctx.adverb_issues = []
    ctx.cliche_issues = []
    ctx.show_dont_tell_issues = []
    ctx.sensory_gaps = []
    ctx.dialogue_tags = []
    ctx.anglicism_issues = []
    ctx.clarity_issues = []
    ctx.register_issues = []
    ctx.register_changes = []
    ctx.emotional_incoherences = []
    ctx.focalization_violations = []
    return ctx


# ========================================================================
# UA_ALERTS - ULTRA COVERAGE (42% → 60%)
# ========================================================================

class TestUltraAlertsEdgeCases:
    """Edge cases adicionales para ua_alerts."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_lexical_repetitions_with_dict_occurrences(self, mock_engine, full_context):
        """Repeticiones léxicas con occurrences como dict."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        rep = Mock()
        rep.word = "test"
        rep.chapter = 1
        rep.confidence = 0.8
        rep.occurrences = [
            {"start_char": 10, "end_char": 14, "context": "test 1"},
            {"start_char": 50, "end_char": 54, "context": "test 2"}
        ]
        full_context.lexical_repetitions = [rep]

        alert = Mock()
        mock_engine.return_value.create_from_word_echo.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': Mock(repetition_min_distance=50),
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(full_context)
        assert len(full_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_register_change_low_severity_skipped(self, mock_engine, full_context):
        """Cambios de registro con severidad baja se saltan."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        change = {
            "severity": "low",  # No se procesa
            "from_register": "formal",
            "to_register": "coloquial"
        }
        full_context.register_changes = [change]

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': Mock(),
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(full_context)
        # No debe generar alerta
        mock_engine.return_value.create_from_register_change.assert_not_called()

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    @patch('narrative_assistant.analysis.name_variant_detector.detect_name_variants')
    @patch('narrative_assistant.entities.repository.get_entity_repository')
    def test_name_variants_exception_handling(self, mock_repo_get, mock_detect, mock_engine, full_context):
        """Name variants maneja excepciones."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        mock_detect.side_effect = ValueError("Test error")

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': Mock(),
            '_memory_monitor': Mock(),
        })()

        # No debe crashear
        pipeline._generate_all_alerts(full_context)

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_emotional_incoherence_exception_in_create(self, mock_engine, full_context):
        """Incoherencia emocional con excepción en create."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        inc = {
            "entity_name": "Test",
            "incoherence_type": "test",
            "declared_emotion": "happy",
            "actual_behavior": "crying"
        }
        full_context.emotional_incoherences = [inc]

        mock_engine.return_value.create_from_emotional_incoherence.side_effect = ValueError("Test")

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': Mock(),
            '_memory_monitor': Mock(),
        })()

        # No debe crashear
        pipeline._generate_all_alerts(full_context)

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_focalization_violation_without_value_enum(self, mock_engine, full_context):
        """Violación de focalización sin .value enum."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        violation = Mock()
        violation.violation_type = "omniscient_intrusion"  # String directo, no enum
        violation.text_excerpt = "Test excerpt"
        violation.declared_focalizer = "Juan"
        violation.explanation = "Test"
        violation.chapter = 1
        violation.position = 100
        violation.confidence = 0.8
        full_context.focalization_violations = [violation]

        alert = Mock()
        mock_engine.return_value.create_from_focalization_violation.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': Mock(),
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(full_context)
        assert len(full_context.alerts) == 1


# ========================================================================
# UA_CONSISTENCY - ULTRA COVERAGE (43% → 60%)
# ========================================================================

class TestUltraConsistencyEdgeCases:
    """Edge cases para ua_consistency."""

    def test_phase_6_with_entities_but_no_chapters(self, full_context):
        """Fase 6 con entidades pero sin capítulos."""
        from narrative_assistant.pipelines.ua_consistency import PipelineConsistencyMixin

        full_context.chapters = []

        pipeline = type('TestPipeline', (PipelineConsistencyMixin,), {
            'config': Mock(
                run_consistency=True,
                run_vital_status=True,
                run_character_location=True,
                run_ooc_detection=True,
                run_focalization=False
            ),
            '_memory_monitor': Mock(),
            '_run_vital_status_check': Mock(),
        })()

        result = pipeline._phase_6_consistency(full_context)

        # No debería llamar checks que requieren chapters
        pipeline._run_vital_status_check.assert_not_called()

    def test_phase_6_with_chapters_but_no_entities(self, full_context):
        """Fase 6 con capítulos pero sin entidades."""
        from narrative_assistant.pipelines.ua_consistency import PipelineConsistencyMixin

        full_context.entities = []

        pipeline = type('TestPipeline', (PipelineConsistencyMixin,), {
            'config': Mock(
                run_consistency=True,
                run_focalization=True,
                run_emotional=True,
                run_sentiment=True,
                run_vital_status=False
            ),
            '_memory_monitor': Mock(),
            '_run_focalization_consistency': Mock(),
            '_run_emotional_coherence': Mock(),
            '_run_sentiment_analysis': Mock(),
        })()

        result = pipeline._phase_6_consistency(full_context)

        # Debe llamar los que solo necesitan chapters
        pipeline._run_focalization_consistency.assert_called_once()
        pipeline._run_emotional_coherence.assert_called_once()
        pipeline._run_sentiment_analysis.assert_called_once()


# ========================================================================
# UA_QUALITY - ULTRA COVERAGE (21% → 60%)
# ========================================================================

class TestUltraQualityEdgeCases:
    """Edge cases para ua_quality."""

    def test_phase_5_all_disabled(self, full_context):
        """Fase 5 con todos los checks deshabilitados."""
        from narrative_assistant.pipelines.ua_quality import PipelineQualityMixin

        config = Mock(
            run_spelling=False,
            run_grammar=False,
            run_lexical_repetitions=False,
            run_semantic_repetitions=False,
            run_coherence=False,
            run_register_analysis=False,
            run_pacing=False,
            run_sticky_sentences=False,
            run_sentence_energy=False,
            run_sensory_report=False,
            run_typography=False,
            run_pov_check=False,
            run_references_check=False,
            run_acronyms_check=False,
            parallel_extraction=False
        )
        config.run_filler_detection = False

        pipeline = type('TestPipeline', (PipelineQualityMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
        })()

        result = pipeline._phase_5_quality(full_context)
        assert result.is_success

    def test_phase_5_only_one_check_enabled(self, full_context):
        """Fase 5 con solo un check habilitado."""
        from narrative_assistant.pipelines.ua_quality import PipelineQualityMixin

        config = Mock(
            run_spelling=False,
            run_grammar=True,  # Solo este
            run_lexical_repetitions=False,
            run_semantic_repetitions=False,
            run_coherence=False,
            run_register_analysis=False,
            run_pacing=False,
            run_sticky_sentences=False,
            run_sentence_energy=False,
            run_sensory_report=False,
            run_typography=False,
            run_pov_check=False,
            run_references_check=False,
            run_acronyms_check=False,
            parallel_extraction=False
        )
        config.run_filler_detection = False

        pipeline = type('TestPipeline', (PipelineQualityMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
            '_run_grammar_check': Mock(),
            '_run_spelling_check': Mock(),
        })()

        result = pipeline._phase_5_quality(full_context)

        pipeline._run_grammar_check.assert_called_once()
        pipeline._run_spelling_check.assert_not_called()


# ========================================================================
# UA_RESOLUTION - ULTRA COVERAGE (19% → 60%)
# ========================================================================

class TestUltraResolutionEdgeCases:
    """Edge cases para ua_resolution."""

    def test_phase_3_all_disabled(self, full_context):
        """Fase 3 con todo deshabilitado."""
        from narrative_assistant.pipelines.ua_resolution import PipelineResolutionMixin

        config = Mock(
            run_coreference=False,
            run_entity_fusion=False,
            run_dialogue_detection=False
        )

        pipeline = type('TestPipeline', (PipelineResolutionMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
        })()

        result = pipeline._phase_3_resolution(full_context)
        assert result.is_success

    @patch('narrative_assistant.nlp.coreference_resolver.resolve_coreferences_voting')
    def test_phase_3_with_empty_entities(self, mock_resolve, full_context):
        """Fase 3 con lista de entidades vacía."""
        from narrative_assistant.pipelines.ua_resolution import PipelineResolutionMixin

        full_context.entities = []

        config = Mock(
            run_coreference=True,
            run_entity_fusion=True,
            run_dialogue_detection=True
        )

        pipeline = type('TestPipeline', (PipelineResolutionMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
            '_persist_coref_voting_details': Mock(),
        })()

        result = pipeline._phase_3_resolution(full_context)

        # No debería llamar coreference sin entidades
        mock_resolve.assert_not_called()


# ========================================================================
# UA_DEEP_EXTRACTION - ULTRA COVERAGE (28% → 60%)
# ========================================================================

class TestUltraDeepExtractionEdgeCases:
    """Edge cases para ua_deep_extraction."""

    def test_phase_4_all_disabled(self, full_context):
        """Fase 4 con todo deshabilitado."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        config = Mock(
            run_attributes=False,
            run_relationships=False,
            run_interactions=False,
            run_knowledge=False,
            run_voice_profiles=False,
            parallel_extraction=False
        )

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
        })()

        result = pipeline._phase_4_deep_extraction(full_context)
        assert result.is_success

    def test_phase_4_without_entities(self, full_context):
        """Fase 4 sin entidades."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        full_context.entities = []

        config = Mock(
            run_attributes=True,
            run_relationships=True,
            run_interactions=True,
            run_knowledge=True,
            run_voice_profiles=True,
            parallel_extraction=False
        )

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
            '_extract_attributes': Mock(),
        })()

        result = pipeline._phase_4_deep_extraction(full_context)

        # No debería llamar métodos sin entidades
        pipeline._extract_attributes.assert_not_called()

    def test_phase_4_individual_task_exceptions(self, full_context):
        """Fase 4 con excepciones en tareas individuales."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        config = Mock(
            run_attributes=True,
            run_relationships=True,
            parallel_extraction=False
        )

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': config,
            '_memory_monitor': Mock(),
            '_extract_attributes': Mock(side_effect=ValueError("Error 1")),
            '_extract_relationships': Mock(side_effect=ValueError("Error 2")),
        })()

        result = pipeline._phase_4_deep_extraction(full_context)

        # Debe continuar a pesar de errores
        assert result.is_success
        pipeline._extract_attributes.assert_called_once()
        pipeline._extract_relationships.assert_called_once()
