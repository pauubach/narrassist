"""
Tests masivos adicionales para alcanzar 60%+ coverage en pipelines.

Este archivo complementa test_pipelines_coverage_boost.py con tests más
profundos que cubren:
- Manejo de diferentes tipos de datos (dict vs objeto)
- Edge cases (listas vacías, valores None, tipos incorrectos)
- Rutas de error y excepciones
- Configuraciones parciales
- Integración entre fases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime


# Fixtures comunes (duplicados de test_pipelines_coverage_boost.py)
@pytest.fixture
def mock_config():
    """Config mock con todas las features habilitadas."""
    config = Mock()
    # ua_consistency flags
    config.run_consistency = True
    config.run_temporal_consistency = True
    config.run_focalization = True
    config.run_voice_deviations = True
    config.run_emotional = True
    config.run_vital_status = True
    config.run_character_location = True
    config.run_ooc_detection = True
    config.run_chekhov = True
    config.run_sentiment = True
    config.run_character_profiling = True
    config.run_knowledge = True
    # ua_resolution flags
    config.run_coreference = True
    config.run_entity_fusion = True
    config.run_dialogue_detection = True
    config.coreference_threshold = 0.7
    # ua_quality flags
    config.run_spelling = True
    config.run_grammar = True
    config.run_lexical_repetitions = True
    config.run_semantic_repetitions = True
    config.run_coherence = True
    config.run_register_analysis = True
    config.run_pacing = True
    config.run_sticky_sentences = True
    config.run_sentence_energy = True
    config.run_sensory_report = True
    config.run_typography = True
    config.run_pov_check = True
    config.run_references_check = True
    config.run_acronyms_check = True
    config.run_filler_detection = True
    # ua_deep_extraction flags
    config.run_attributes = True
    config.run_relationships = True
    config.run_interactions = True
    config.run_knowledge = True
    config.run_voice_profiles = True
    config.parallel_extraction = False
    config.repetition_min_distance = 50
    return config


@pytest.fixture
def mock_context():
    """Context mock con datos mínimos."""
    ctx = Mock()
    ctx.project_id = 1
    ctx.entities = [Mock(id=1, name="Juan"), Mock(id=2, name="María")]
    ctx.entity_map = {"juan": 1, "maría": 2}
    ctx.chapters = [{"number": 1, "content": "Texto del capítulo 1", "start_char": 0, "end_char": 100}]
    ctx.dialogues = []
    ctx.attributes = [Mock()]
    ctx.temporal_markers = [Mock()]
    ctx.voice_profiles = {"juan": Mock()}
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
    # Todas las listas que _generate_all_alerts recorre
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
# UA_ALERTS - TESTS ADICIONALES (16% → 60%)
# ========================================================================

class TestPipelineAlertsDeepCoverage:
    """Tests adicionales para ua_alerts.py."""

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_multiple_types(self, mock_engine, mock_config, mock_context):
        """Genera alertas de múltiples tipos simultáneamente."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        # Setup múltiples tipos de issues
        inc = Mock()
        inc.entity_name = "Juan"
        inc.attribute_key = Mock(value="age")
        inc.value1 = "25"
        inc.value2 = "30"
        inc.value1_chapter = 1
        inc.value2_chapter = 2
        inc.value1_excerpt = "25 años"
        inc.value2_excerpt = "30 años"
        inc.value1_position = 0
        inc.value2_position = 100
        inc.explanation = "test"
        inc.confidence = 0.9
        mock_context.inconsistencies = [inc]

        tinc = Mock()
        tinc.inconsistency_type = Mock(value="age_contradiction")
        tinc.description = "Edad incorrecta"
        tinc.chapter = 1
        tinc.position = 50
        tinc.confidence = 0.8
        tinc.suggestion = "Revisar"
        tinc.expected = "25"
        tinc.found = "30"
        tinc.severity = Mock(value="high")
        tinc.methods_agreed = ["method1"]
        mock_context.temporal_inconsistencies = [tinc]

        alert = Mock()
        mock_engine.return_value.create_from_attribute_inconsistency.return_value = Mock(
            is_success=True, value=alert
        )
        mock_engine.return_value.create_from_temporal_inconsistency.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        # Debe haber 2 alertas
        assert len(mock_context.alerts) == 2

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_handles_spelling_issues(self, mock_engine, mock_config, mock_context):
        """Genera alertas de ortografía."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        issue = Mock()
        issue.word = "hola"
        issue.start_char = 10
        issue.end_char = 14
        issue.sentence = "Hola mundo"
        issue.error_type = Mock(value="capitalization")
        issue.suggestions = ["Hola"]
        issue.confidence = 0.95
        issue.explanation = "Debe capitalizarse"
        issue.chapter = 1
        mock_context.spelling_issues = [issue]

        alert = Mock()
        mock_engine.return_value.create_from_spelling_issue.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1
        mock_engine.return_value.create_from_spelling_issue.assert_called_once()

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_handles_grammar_issues(self, mock_engine, mock_config, mock_context):
        """Genera alertas de gramática."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        issue = Mock()
        issue.text = "los casa"
        issue.start_char = 20
        issue.end_char = 28
        issue.sentence = "Vi los casa azules"
        issue.error_type = Mock(value="agreement")
        issue.suggestion = "las casas"
        issue.confidence = 0.9
        issue.explanation = "Concordancia género/número"
        issue.rule_id = "AGREEMENT_001"
        issue.chapter = 1
        mock_context.grammar_issues = [issue]

        alert = Mock()
        mock_engine.return_value.create_from_grammar_issue.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_lexical_repetitions_with_occurrences(self, mock_engine, mock_config, mock_context):
        """Genera alertas de repeticiones léxicas con occurrences."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        rep = Mock()
        rep.word = "muy"
        rep.chapter = 1
        rep.confidence = 0.85

        occ1 = Mock()
        occ1.start_char = 10
        occ1.end_char = 13
        occ1.context = "Es muy bonito"

        occ2 = Mock()
        occ2.start_char = 50
        occ2.end_char = 53
        occ2.context = "Muy interesante"

        rep.occurrences = [occ1, occ2]
        mock_context.lexical_repetitions = [rep]

        alert = Mock()
        mock_engine.return_value.create_from_word_echo.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()
        pipeline.config.repetition_min_distance = 50

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_semantic_repetitions(self, mock_engine, mock_config, mock_context):
        """Genera alertas de repeticiones semánticas."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        rep = Mock()
        rep.word = "grande"
        rep.count = 5
        rep.similar_words = ["enorme", "gigante", "inmenso"]
        rep.confidence = 0.75
        mock_context.semantic_repetitions = [rep]

        alert = Mock()
        mock_engine.return_value.create_alert.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_coherence_breaks(self, mock_engine, mock_config, mock_context):
        """Genera alertas de saltos de coherencia."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin
        from narrative_assistant.alerts.models import AlertSeverity

        brk = Mock()
        brk.severity = Mock(value="high")
        brk.break_type = Mock(value="topic_shift")
        brk.explanation = "Cambio abrupto de tema"
        brk.similarity_score = 0.2
        brk.expected_similarity = 0.7
        brk.text_before = "Hablando de Juan..."
        brk.text_after = "El planeta Marte..."
        brk.position_char = 500
        brk.chapter_id = 1
        brk.confidence = 0.8
        mock_context.coherence_breaks = [brk]

        alert = Mock()
        mock_engine.return_value.create_alert.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_voice_deviations(self, mock_engine, mock_config, mock_context):
        """Genera alertas de desviaciones de voz."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        deviation = {
            "entity_name": "Pedro",
            "entity_id": 1,
            "severity": "high",
            "explanation": "Comportamiento inconsistente",
            "chapter": 2,
            "violation_text": "Pedro gritó furiosamente",
            "expectation": "Pedro es calmado",
            "consensus_score": 0.85,
            "detection_methods": ["llm", "profile"]
        }
        mock_context.voice_deviations = [deviation]

        alert = Mock()
        mock_engine.return_value.create_alert.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_pacing_issues(self, mock_engine, mock_config, mock_context):
        """Genera alertas de ritmo narrativo."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        mock_context.pacing_analysis = {
            "issues": [
                {
                    "issue_type": "too_slow",
                    "severity": "warning",
                    "segment_id": 1,
                    "segment_type": "chapter",
                    "description": "Ritmo muy lento",
                    "explanation": "Demasiados detalles",
                    "suggestion": "Reducir descripciones",
                    "actual_value": 100.0,
                    "expected_range": (50.0, 80.0),
                    "comparison_value": 65.0
                }
            ]
        }

        alert = Mock()
        mock_engine.return_value.create_from_pacing_issue.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_sticky_sentences(self, mock_engine, mock_config, mock_context):
        """Genera alertas de oraciones pesadas."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        sent = Mock()
        sent.text = "La casa que está en la calle que tiene el árbol"
        sent.glue_percentage = 45.0
        sent.severity = Mock(value="medium")
        sent.chapter = 1
        sent.start_char = 100
        sent.end_char = 148
        mock_context.sticky_sentences = [sent]

        alert = Mock()
        mock_engine.return_value.create_from_sticky_sentence.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_register_changes(self, mock_engine, mock_config, mock_context):
        """Genera alertas de cambios de registro."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        change = {
            "severity": "high",
            "from_register": "formal",
            "to_register": "coloquial",
            "chapter": 1,
            "position": 100,
            "context_before": "En virtud de lo expuesto...",
            "context_after": "Pues mira tío...",
            "explanation": "Cambio abrupto de registro",
            "confidence": 0.85
        }
        mock_context.register_changes = [change]

        alert = Mock()
        mock_engine.return_value.create_from_register_change.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1
        mock_engine.return_value.create_from_register_change.assert_called_once()

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    @patch('narrative_assistant.analysis.name_variant_detector.detect_name_variants')
    @patch('narrative_assistant.entities.repository.get_entity_repository')
    def test_generate_alerts_name_variants(self, mock_repo_get, mock_detect, mock_engine, mock_config, mock_context):
        """Genera alertas de variantes de nombres."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        # Setup entities
        entity = Mock()
        entity.id = 1
        entity.name = "Juan"
        mock_context.entities = [entity]

        mock_repo = Mock()
        mock_repo.get_mentions_by_entity.return_value = []
        mock_repo_get.return_value = mock_repo

        variant = Mock()
        variant.entity_id = 1
        variant.entity_name = "Juan"
        variant.canonical_form = "Juan"
        variant.variant_form = "Juanito"
        variant.canonical_count = 10
        variant.variant_count = 2
        variant.variant_mentions = ["Juanito apareció", "Juanito salió"]
        variant.all_in_dialogue = True
        variant.confidence = 0.8
        mock_detect.return_value = [variant]

        alert = Mock()
        mock_engine.return_value.create_from_name_variant.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_emotional_incoherences(self, mock_engine, mock_config, mock_context):
        """Genera alertas de incoherencias emocionales."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        inc = {
            "entity_name": "María",
            "incoherence_type": "emotion_dialogue",
            "declared_emotion": "triste",
            "actual_behavior": "sonrisa radiante",
            "declared_text": "María estaba triste",
            "behavior_text": "María sonrió radiantemente",
            "explanation": "Emoción declarada no coincide con comportamiento",
            "confidence": 0.75,
            "suggestion": "Revisar coherencia emocional",
            "chapter_id": 1,
            "start_char": 100,
            "end_char": 150
        }
        mock_context.emotional_incoherences = [inc]

        alert = Mock()
        mock_engine.return_value.create_from_emotional_incoherence.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1

    @patch('narrative_assistant.alerts.engine.get_alert_engine')
    def test_generate_alerts_focalization_violations(self, mock_engine, mock_config, mock_context):
        """Genera alertas de violaciones de focalización."""
        from narrative_assistant.pipelines.ua_alerts import PipelineAlertsMixin

        violation = Mock()
        violation.violation_type = Mock(value="omniscient_intrusion")
        violation.text_excerpt = "Pedro pensó que María era hermosa"
        violation.declared_focalizer = "María"
        violation.explanation = "Conocimiento imposible desde focalización de María"
        violation.chapter = 1
        violation.position = 200
        violation.confidence = 0.9
        mock_context.focalization_violations = [violation]

        alert = Mock()
        mock_engine.return_value.create_from_focalization_violation.return_value = Mock(
            is_success=True, value=alert
        )

        pipeline = type('TestPipeline', (PipelineAlertsMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
        })()

        pipeline._generate_all_alerts(mock_context)

        assert len(mock_context.alerts) == 1


# ========================================================================
# UA_CONSISTENCY - TESTS ADICIONALES (39% → 60%)
# ========================================================================

class TestPipelineConsistencyDeepCoverage:
    """Tests adicionales para ua_consistency.py."""

    def test_phase_6_with_empty_data(self, mock_config, mock_context):
        """Fase 6 con datos vacíos no ejecuta checks."""
        from narrative_assistant.pipelines.ua_consistency import PipelineConsistencyMixin

        mock_context.attributes = []
        mock_context.temporal_markers = []
        mock_context.voice_profiles = {}
        mock_context.entities = []

        pipeline = type('TestPipeline', (PipelineConsistencyMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_attribute_consistency': Mock(),
            '_run_temporal_consistency': Mock(),
            '_run_vital_status_check': Mock(),
        })()

        result = pipeline._phase_6_consistency(mock_context)

        # Con listas vacías, no debería llamar a los métodos
        pipeline._run_attribute_consistency.assert_not_called()
        pipeline._run_temporal_consistency.assert_not_called()
        pipeline._run_vital_status_check.assert_not_called()

    def test_phase_6_partial_data(self, mock_config, mock_context):
        """Fase 6 con datos parciales solo ejecuta checks relevantes."""
        from narrative_assistant.pipelines.ua_consistency import PipelineConsistencyMixin

        # Solo attributes, no temporal markers
        mock_context.attributes = [Mock()]
        mock_context.temporal_markers = []

        pipeline = type('TestPipeline', (PipelineConsistencyMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_attribute_consistency': Mock(),
            '_run_temporal_consistency': Mock(),
        })()

        result = pipeline._phase_6_consistency(mock_context)

        # Debe llamar attribute pero no temporal
        pipeline._run_attribute_consistency.assert_called_once()
        pipeline._run_temporal_consistency.assert_not_called()

    def test_phase_6_all_flags_disabled(self, mock_config, mock_context):
        """Fase 6 con todos los flags deshabilitados."""
        from narrative_assistant.pipelines.ua_consistency import PipelineConsistencyMixin

        # Deshabilitar todos
        mock_config.run_consistency = False
        mock_config.run_temporal_consistency = False
        mock_config.run_focalization = False
        mock_config.run_voice_deviations = False
        mock_config.run_emotional = False
        mock_config.run_vital_status = False
        mock_config.run_character_location = False
        mock_config.run_ooc_detection = False
        mock_config.run_chekhov = False
        mock_config.run_sentiment = False
        mock_config.run_character_profiling = False
        mock_config.run_knowledge = False

        pipeline = type('TestPipeline', (PipelineConsistencyMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_attribute_consistency': Mock(),
            '_run_sentiment_analysis': Mock(),
        })()

        result = pipeline._phase_6_consistency(mock_context)

        # No debería llamar ningún método
        pipeline._run_attribute_consistency.assert_not_called()
        pipeline._run_sentiment_analysis.assert_not_called()
        assert result.is_success


# ========================================================================
# UA_RESOLUTION - TESTS ADICIONALES (18% → 60%)
# ========================================================================

class TestPipelineResolutionDeepCoverage:
    """Tests adicionales para ua_resolution.py."""

    @patch('narrative_assistant.nlp.coreference_resolver.resolve_coreferences_voting')
    def test_phase_3_resolution_with_dialogue(self, mock_resolve, mock_config, mock_context):
        """Fase 3 con diálogos activa attribution."""
        from narrative_assistant.pipelines.ua_resolution import PipelineResolutionMixin

        mock_context.dialogues = [Mock()]
        mock_resolve.return_value = Mock(chains=[], unresolved=[])

        pipeline = type('TestPipeline', (PipelineResolutionMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_persist_coref_voting_details': Mock(),
            '_run_entity_fusion': Mock(),
            '_attribute_dialogues': Mock(),
        })()

        result = pipeline._phase_3_resolution(mock_context)

        assert result.is_success
        pipeline._attribute_dialogues.assert_called_once()

    def test_phase_3_resolution_only_fusion(self, mock_config, mock_context):
        """Fase 3 solo con entity fusion habilitado."""
        from narrative_assistant.pipelines.ua_resolution import PipelineResolutionMixin

        mock_config.run_coreference = False
        mock_config.run_dialogue_detection = False
        mock_config.run_entity_fusion = True

        pipeline = type('TestPipeline', (PipelineResolutionMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_entity_fusion': Mock(),
        })()

        result = pipeline._phase_3_resolution(mock_context)

        pipeline._run_entity_fusion.assert_called_once()


# ========================================================================
# UA_QUALITY - TESTS ADICIONALES (18% → 60%)
# ========================================================================

class TestPipelineQualityDeepCoverage:
    """Tests adicionales para ua_quality.py."""

    def test_phase_5_only_spelling_enabled(self, mock_config, mock_context):
        """Fase 5 solo con spelling habilitado."""
        from narrative_assistant.pipelines.ua_quality import PipelineQualityMixin

        # Deshabilitar todo excepto spelling
        mock_config.run_spelling = True
        mock_config.run_grammar = False
        mock_config.run_lexical_repetitions = False
        mock_config.run_semantic_repetitions = False
        mock_config.run_coherence = False
        mock_config.run_register_analysis = False
        mock_config.run_pacing = False
        mock_config.run_sticky_sentences = False
        mock_config.run_sentence_energy = False
        mock_config.run_sensory_report = False
        mock_config.run_typography = False
        mock_config.run_pov_check = False
        mock_config.run_references_check = False
        mock_config.run_acronyms_check = False
        mock_config.run_filler_detection = False

        pipeline = type('TestPipeline', (PipelineQualityMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_spelling_check': Mock(),
            '_run_grammar_check': Mock(),
        })()

        result = pipeline._phase_5_quality(mock_context)

        pipeline._run_spelling_check.assert_called_once()
        pipeline._run_grammar_check.assert_not_called()

    def test_phase_5_parallel_execution(self, mock_config, mock_context):
        """Fase 5 con ejecución paralela."""
        from narrative_assistant.pipelines.ua_quality import PipelineQualityMixin

        mock_config.parallel_extraction = True

        pipeline = type('TestPipeline', (PipelineQualityMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_parallel_tasks': Mock(),
            '_run_spelling_check': Mock(),
            '_run_grammar_check': Mock(),
        })()

        result = pipeline._phase_5_quality(mock_context)

        # Debe llamar _run_parallel_tasks
        pipeline._run_parallel_tasks.assert_called_once()


# ========================================================================
# UA_DEEP_EXTRACTION - TESTS ADICIONALES (12% → 60%)
# ========================================================================

class TestPipelineDeepExtractionDeepCoverage:
    """Tests adicionales para ua_deep_extraction.py."""

    def test_phase_4_only_attributes(self, mock_config, mock_context):
        """Fase 4 solo con attributes habilitado."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        mock_config.run_attributes = True
        mock_config.run_relationships = False
        mock_config.run_interactions = False
        mock_config.run_knowledge = False
        mock_config.run_voice_profiles = False

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_extract_attributes': Mock(),
            '_extract_relationships': Mock(),
        })()

        result = pipeline._phase_4_deep_extraction(mock_context)

        pipeline._extract_attributes.assert_called_once()
        pipeline._extract_relationships.assert_not_called()

    def test_phase_4_parallel_execution(self, mock_config, mock_context):
        """Fase 4 con ejecución paralela."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        mock_config.parallel_extraction = True

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_run_parallel_tasks': Mock(),
            '_extract_attributes': Mock(),
            '_extract_relationships': Mock(),
        })()

        result = pipeline._phase_4_deep_extraction(mock_context)

        pipeline._run_parallel_tasks.assert_called_once()

    def test_phase_4_exception_handling(self, mock_config, mock_context):
        """Fase 4 maneja excepciones sin crashear."""
        from narrative_assistant.pipelines.ua_deep_extraction import PipelineDeepExtractionMixin

        pipeline = type('TestPipeline', (PipelineDeepExtractionMixin,), {
            'config': mock_config,
            '_memory_monitor': Mock(),
            '_extract_attributes': Mock(side_effect=ValueError("Test error")),
            '_extract_relationships': Mock(),
        })()

        result = pipeline._phase_4_deep_extraction(mock_context)

        # Debería continuar con relationships a pesar del error
        assert result.is_success
        pipeline._extract_relationships.assert_called_once()
