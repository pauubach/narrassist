"""Tests para el sistema de perfilado de personajes (Sprint 4)."""

import pytest

from narrative_assistant.analysis.character_profiling import (
    ActionIndicator,
    CharacterProfile,
    CharacterProfiler,
    CharacterRole,
    DefinitionIndicator,
    EnvironmentIndicator,
    PresenceIndicator,
    SentimentIndicator,
    SpeechIndicator,
)


class TestCharacterProfileDataclasses:
    """Tests para las dataclasses de perfil."""

    def test_presence_indicator_defaults(self):
        p = PresenceIndicator()
        assert p.total_mentions == 0
        assert p.continuity == 0.0
        assert p.chapter_span == 0

    def test_presence_chapter_span(self):
        p = PresenceIndicator(
            first_appearance_chapter=2,
            last_appearance_chapter=8,
        )
        assert p.chapter_span == 7

    def test_action_indicator_defaults(self):
        a = ActionIndicator()
        assert a.action_count == 0
        assert a.agency_score == 0.5

    def test_character_profile_to_dict(self):
        profile = CharacterProfile(
            entity_id=1,
            entity_name="María",
            role=CharacterRole.PROTAGONIST,
        )
        d = profile.to_dict()
        assert d["entity_name"] == "María"
        assert d["role"] == "protagonist"
        assert "presence" in d
        assert "actions" in d
        assert "speech" in d
        assert "definition" in d
        assert "sentiment" in d
        assert "environment" in d

    def test_character_role_values(self):
        assert CharacterRole.PROTAGONIST.value == "protagonist"
        assert CharacterRole.MINOR.value == "minor"
        assert CharacterRole.MENTIONED.value == "mentioned"


class TestCharacterProfiler:
    """Tests para CharacterProfiler."""

    @pytest.fixture()
    def sample_mentions(self):
        return [
            {"entity_id": 1, "entity_name": "María", "chapter": 1},
            {"entity_id": 1, "entity_name": "María", "chapter": 1},
            {"entity_id": 1, "entity_name": "María", "chapter": 2},
            {"entity_id": 1, "entity_name": "María", "chapter": 3},
            {"entity_id": 2, "entity_name": "Juan", "chapter": 1},
            {"entity_id": 2, "entity_name": "Juan", "chapter": 3},
            {"entity_id": 3, "entity_name": "Pedro", "chapter": 2},
        ]

    def test_build_presence(self, sample_mentions):
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(sample_mentions)

        assert len(profiles) == 3

        # María tiene más menciones
        maria = next(p for p in profiles if p.entity_name == "María")
        assert maria.presence.total_mentions == 4
        assert maria.presence.first_appearance_chapter == 1
        assert maria.presence.last_appearance_chapter == 3
        assert maria.presence.continuity == 1.0  # Aparece en 3/3

        # Pedro solo aparece en 1 capítulo
        pedro = next(p for p in profiles if p.entity_name == "Pedro")
        assert pedro.presence.total_mentions == 1
        assert pedro.presence.continuity == pytest.approx(1 / 3, abs=0.01)

    def test_role_assignment(self, sample_mentions):
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(sample_mentions)

        # María debería tener mayor relevancia
        maria = next(p for p in profiles if p.entity_name == "María")
        pedro = next(p for p in profiles if p.entity_name == "Pedro")
        assert maria.narrative_relevance > pedro.narrative_relevance

    def test_profiles_sorted_by_relevance(self, sample_mentions):
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(sample_mentions)

        relevances = [p.narrative_relevance for p in profiles]
        assert relevances == sorted(relevances, reverse=True)

    def test_build_speech(self, sample_mentions):
        dialogues = [
            {"speaker_id": 1, "text": "Hola, ¿cómo estás?", "chapter": 1},
            {"speaker_id": 1, "text": "¡Qué alegría verte!", "chapter": 1},
            {"speaker_id": 2, "text": "Bien, gracias.", "chapter": 1},
        ]
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(
            sample_mentions, dialogues=dialogues
        )

        maria = next(p for p in profiles if p.entity_name == "María")
        assert maria.speech.total_interventions == 2
        assert maria.speech.question_ratio == 0.5  # 1 de 2 tiene ?
        assert maria.speech.exclamation_ratio == 0.5  # 1 de 2 tiene !

    def test_build_definition(self, sample_mentions):
        attributes = [
            {"entity_name": "María", "category": "physical", "key": "hair", "value": "moreno"},
            {"entity_name": "María", "category": "social", "key": "profession", "value": "médica"},
            {"entity_name": "Juan", "category": "psychological", "key": "personality", "value": "valiente"},
        ]
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(
            sample_mentions, attributes=attributes
        )

        maria = next(p for p in profiles if p.entity_name == "María")
        assert maria.definition.attribute_count == 2
        assert maria.definition.physical_attributes["hair"] == "moreno"
        assert maria.definition.social_attributes["profession"] == "médica"

    def test_build_environment(self, sample_mentions):
        location_events = [
            {"entity_id": 1, "location_name": "Madrid", "chapter": 1, "change_type": "arrival"},
            {"entity_id": 1, "location_name": "Madrid", "chapter": 2, "change_type": "presence"},
            {"entity_id": 1, "location_name": "Barcelona", "chapter": 3, "change_type": "transition"},
        ]
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(
            sample_mentions, location_events=location_events
        )

        maria = next(p for p in profiles if p.entity_name == "María")
        assert maria.environment.primary_location == "Madrid"
        assert maria.environment.location_changes == 2  # arrival + transition

    def test_empty_mentions(self):
        profiler = CharacterProfiler()
        profiles = profiler.build_profiles([])
        assert profiles == []

    def test_build_sentiment(self, sample_mentions):
        chapter_texts = {
            1: "María sonreía feliz mientras abrazaba a su amiga. María estaba contenta.",
            2: "María lloraba con dolor. El sufrimiento de María era evidente.",
            3: "María caminaba tranquila por el parque.",
        }
        profiler = CharacterProfiler(total_chapters=3)
        profiles = profiler.build_profiles(
            sample_mentions, chapter_texts=chapter_texts
        )

        maria = next(p for p in profiles if p.entity_name == "María")
        # Cap 1: positive words (feliz, contenta), Cap 2: negative words (dolor, sufrimiento)
        assert maria.sentiment.positive_mentions > 0
        assert maria.sentiment.negative_mentions > 0


class TestCharacterNetworkAnalyzer:
    """Tests para el análisis de red de personajes."""

    def test_network_report_empty(self):
        from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer

        analyzer = CharacterNetworkAnalyzer()
        report = analyzer.analyze([], {})
        assert report.metrics.node_count == 0
        assert report.metrics.edge_count == 0

    def test_network_basic_analysis(self):
        from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer

        coocs = [
            {"entity1_id": 1, "entity2_id": 2, "chapter": 1, "distance_chars": 100},
            {"entity1_id": 1, "entity2_id": 2, "chapter": 2, "distance_chars": 50},
            {"entity1_id": 2, "entity2_id": 3, "chapter": 1, "distance_chars": 200},
        ]
        names = {1: "María", 2: "Juan", 3: "Pedro"}

        analyzer = CharacterNetworkAnalyzer()
        report = analyzer.analyze(coocs, names, total_chapters=3)

        assert report.metrics.node_count >= 2
        assert report.metrics.edge_count >= 1
        assert len(report.nodes) >= 2

    def test_chapter_evolution(self):
        from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer

        coocs = [
            {"entity1_id": 1, "entity2_id": 2, "chapter": 1, "distance_chars": 100},
            {"entity1_id": 1, "entity2_id": 3, "chapter": 2, "distance_chars": 200},
        ]
        names = {1: "María", 2: "Juan", 3: "Pedro"}

        analyzer = CharacterNetworkAnalyzer()
        report = analyzer.analyze(coocs, names, total_chapters=2)

        assert len(report.chapter_evolution) >= 1

    def test_network_report_to_dict(self):
        from narrative_assistant.analysis.character_network import (
            CharacterNetworkReport,
            NetworkMetrics,
        )

        report = CharacterNetworkReport(
            metrics=NetworkMetrics(node_count=5, edge_count=3, density=0.3)
        )
        d = report.to_dict()
        assert d["metrics"]["nodes"] == 5
        assert d["metrics"]["edges"] == 3


class TestOutOfCharacterDetector:
    """Tests para detección de comportamiento fuera de personaje."""

    def test_detector_no_profiles(self):
        from narrative_assistant.analysis.out_of_character import OutOfCharacterDetector

        detector = OutOfCharacterDetector()
        report = detector.detect([])
        assert report.total_deviations == 0
        assert report.characters_analyzed == 0

    def test_detector_insufficient_profile(self):
        from narrative_assistant.analysis.out_of_character import OutOfCharacterDetector

        # Personaje con pocas menciones no se analiza
        profile = CharacterProfile(
            entity_id=1,
            entity_name="Pedro",
            role=CharacterRole.MINOR,
        )
        profile.presence.total_mentions = 2  # Muy pocas

        detector = OutOfCharacterDetector()
        report = detector.detect([profile])
        assert report.characters_analyzed == 0

    def test_deviation_type_values(self):
        from narrative_assistant.analysis.out_of_character import DeviationType

        assert DeviationType.SPEECH_REGISTER.value == "speech_register"
        assert DeviationType.EMOTION_SHIFT.value == "emotion_shift"

    def test_ooc_event_to_dict(self):
        from narrative_assistant.analysis.out_of_character import (
            DeviationSeverity,
            DeviationType,
            OutOfCharacterEvent,
        )

        event = OutOfCharacterEvent(
            entity_id=1,
            entity_name="María",
            deviation_type=DeviationType.SPEECH_REGISTER,
            severity=DeviationSeverity.WARNING,
            description="Cambio de registro",
            expected="formal",
            actual="informal",
            chapter=3,
            confidence=0.8,
        )
        d = event.to_dict()
        assert d["entity_name"] == "María"
        assert d["type"] == "speech_register"
        assert d["severity"] == "warning"


class TestClassicalSpanishNormalizer:
    """Tests para el normalizador de español clásico."""

    def test_detect_classical_text(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()

        classical = (
            "Dixo vuestra merced que el hidalgo passó por el aposento "
            "donde el escudero le esperaba con priesa."
        )
        assert normalizer.is_classical(classical)

        modern = "María dijo que iba a la farmacia a comprar aspirinas."
        assert not normalizer.is_classical(modern)

    def test_normalize_orthographic(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        result = normalizer.normalize("El hidalgo dixo que dexaría el aposento.")

        assert "dijo" in result.normalized
        assert "dejaría" in result.normalized
        assert len(result.replacements) >= 2

    def test_normalize_vuestra_merced(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        result = normalizer.normalize(
            "Vuestra merced dixo que deste modo passaría el mesón."
        )
        assert "usted" in result.normalized
        assert "dijo" in result.normalized
        assert "pasaría" in result.normalized or "pasar" in result.normalized.lower()

    def test_detect_period_golden_age(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        text = (
            "Dixo vuestra merced que el mancebo passó por la botica "
            "y que asaz menester tenía de holgar."
        )
        period = normalizer.detect_period(text)
        assert period == "siglo_de_oro"

    def test_detect_period_modern(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        period = normalizer.detect_period(
            "María fue al supermercado y compró leche."
        )
        assert period == "moderno"

    def test_archaic_glossary(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        glossary = normalizer.get_archaic_glossary(
            "El mancebo entró en el aposento del escudero."
        )
        assert "mancebo" in glossary
        assert "aposento" in glossary
        assert glossary["mancebo"] == "joven"

    def test_normalize_medieval_fh(self):
        from narrative_assistant.nlp.classical_spanish import ClassicalSpanishNormalizer

        normalizer = ClassicalSpanishNormalizer()
        result = normalizer.normalize("El fijo del rey era fermoso.")
        assert "hijo" in result.normalized
        assert "hermoso" in result.normalized
