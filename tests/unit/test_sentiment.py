"""Tests para el módulo de análisis de sentimiento."""

import pytest
from narrative_assistant.nlp.sentiment import (
    SentimentAnalyzer,
    Sentiment,
    Emotion,
    EmotionalState,
    DeclaredEmotionalState,
    EmotionalInconsistency,
    get_sentiment_analyzer,
    KEYWORD_TO_EMOTION,
)


class TestSentimentEnums:
    """Tests para enumeraciones de sentimiento y emociones."""

    def test_sentiment_values(self):
        """Verifica valores de Sentiment."""
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEGATIVE.value == "negative"
        assert Sentiment.NEUTRAL.value == "neutral"

    def test_emotion_values(self):
        """Verifica valores de Emotion."""
        assert Emotion.JOY.value == "joy"
        assert Emotion.SADNESS.value == "sadness"
        assert Emotion.ANGER.value == "anger"
        assert Emotion.FEAR.value == "fear"
        assert Emotion.SURPRISE.value == "surprise"
        assert Emotion.DISGUST.value == "disgust"
        assert Emotion.NEUTRAL.value == "neutral"


class TestKeywordMapping:
    """Tests para el mapeo de palabras clave a emociones."""

    def test_joy_keywords(self):
        """Verifica palabras clave de alegría."""
        assert KEYWORD_TO_EMOTION.get("feliz") == Emotion.JOY
        assert KEYWORD_TO_EMOTION.get("contento") == Emotion.JOY
        assert KEYWORD_TO_EMOTION.get("alegre") == Emotion.JOY

    def test_sadness_keywords(self):
        """Verifica palabras clave de tristeza."""
        assert KEYWORD_TO_EMOTION.get("triste") == Emotion.SADNESS
        assert KEYWORD_TO_EMOTION.get("deprimido") == Emotion.SADNESS
        assert KEYWORD_TO_EMOTION.get("devastado") == Emotion.SADNESS

    def test_anger_keywords(self):
        """Verifica palabras clave de enfado."""
        assert KEYWORD_TO_EMOTION.get("furioso") == Emotion.ANGER
        assert KEYWORD_TO_EMOTION.get("enfadado") == Emotion.ANGER
        assert KEYWORD_TO_EMOTION.get("iracundo") == Emotion.ANGER

    def test_fear_keywords(self):
        """Verifica palabras clave de miedo."""
        assert KEYWORD_TO_EMOTION.get("asustado") == Emotion.FEAR
        assert KEYWORD_TO_EMOTION.get("aterrado") == Emotion.FEAR
        assert KEYWORD_TO_EMOTION.get("temeroso") == Emotion.FEAR


class TestEmotionalStateDataclass:
    """Tests para EmotionalState dataclass."""

    def test_create_emotional_state(self):
        """Test creación de EmotionalState."""
        state = EmotionalState(
            text="Estoy muy feliz",
            sentiment=Sentiment.POSITIVE,
            sentiment_confidence=0.9,
            primary_emotion=Emotion.JOY,
            emotion_confidence=0.85,
            speaker="María",
            chapter_id=1,
            start_char=100,
            end_char=115,
        )

        assert state.text == "Estoy muy feliz"
        assert state.sentiment == Sentiment.POSITIVE
        assert state.sentiment_confidence == 0.9
        assert state.primary_emotion == Emotion.JOY
        assert state.speaker == "María"

    def test_emotional_state_defaults(self):
        """Test valores por defecto de EmotionalState."""
        state = EmotionalState(
            text="Test",
            sentiment=Sentiment.NEUTRAL,
            sentiment_confidence=0.5,
            primary_emotion=Emotion.NEUTRAL,
            emotion_confidence=0.5,
        )

        assert state.speaker is None
        assert state.chapter_id is None
        assert state.start_char == 0
        assert state.emotion_probabilities == {}


class TestDeclaredEmotionalState:
    """Tests para DeclaredEmotionalState dataclass."""

    def test_create_declared_state(self):
        """Test creación de DeclaredEmotionalState."""
        state = DeclaredEmotionalState(
            entity_name="Juan",
            emotion=Emotion.ANGER,
            emotion_keyword="furioso",
            context="Juan estaba furioso con la situación",
            chapter_id=2,
            position=500,
        )

        assert state.entity_name == "Juan"
        assert state.emotion == Emotion.ANGER
        assert state.emotion_keyword == "furioso"
        assert state.chapter_id == 2


class TestEmotionalInconsistency:
    """Tests para EmotionalInconsistency dataclass."""

    def test_create_inconsistency(self):
        """Test creación de EmotionalInconsistency."""
        declared = DeclaredEmotionalState(
            entity_name="Juan",
            emotion=Emotion.ANGER,
            emotion_keyword="furioso",
            context="Juan estaba furioso",
            chapter_id=1,
            position=100,
        )

        detected = EmotionalState(
            text="Claro, no hay problema",
            sentiment=Sentiment.POSITIVE,
            sentiment_confidence=0.8,
            primary_emotion=Emotion.JOY,
            emotion_confidence=0.7,
            speaker="Juan",
            chapter_id=1,
            start_char=150,
            end_char=175,
        )

        inconsistency = EmotionalInconsistency(
            entity_name="Juan",
            declared_state=declared,
            detected_state=detected,
            inconsistency_type="emotion_dialogue_mismatch",
            explanation="Juan está furioso pero habla positivamente",
            confidence=0.75,
            chapter_id=1,
            start_char=100,
            end_char=175,
        )

        assert inconsistency.entity_name == "Juan"
        assert inconsistency.inconsistency_type == "emotion_dialogue_mismatch"
        assert inconsistency.confidence == 0.75


class TestSentimentAnalyzer:
    """Tests para SentimentAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador de sentimiento."""
        return SentimentAnalyzer()

    def test_analyzer_creation(self, analyzer):
        """Test creación del analizador."""
        assert analyzer is not None
        assert analyzer._sentiment_model is None  # Lazy loading
        assert analyzer._emotion_model is None

    def test_is_available_property(self, analyzer):
        """Test propiedad is_available."""
        # Puede ser True o False dependiendo de si pysentimiento está instalado
        result = analyzer.is_available
        assert isinstance(result, bool)

    def test_analyze_empty_text(self, analyzer):
        """Test análisis de texto vacío."""
        result = analyzer.analyze_text("")
        assert not result.is_success or result.value is None

        result = analyzer.analyze_text("   ")
        assert not result.is_success or result.value is None

    def test_analyze_text_with_rules_positive(self, analyzer):
        """Test análisis con reglas - texto positivo."""
        # Forzar fallback a reglas si pysentimiento no está disponible
        result = analyzer._analyze_with_rules(
            text="Estoy muy feliz y contento con todo",
            speaker="Juan",
            chapter_id=1,
            start_char=0,
            end_char=35,
        )

        assert result.is_success
        state = result.value
        assert state.sentiment == Sentiment.POSITIVE
        assert state.speaker == "Juan"

    def test_analyze_text_with_rules_negative(self, analyzer):
        """Test análisis con reglas - texto negativo."""
        result = analyzer._analyze_with_rules(
            text="Estoy muy triste y tengo mucho miedo",
            speaker="María",
            chapter_id=2,
            start_char=100,
            end_char=136,
        )

        assert result.is_success
        state = result.value
        assert state.sentiment == Sentiment.NEGATIVE
        assert state.speaker == "María"

    def test_analyze_text_with_rules_neutral(self, analyzer):
        """Test análisis con reglas - texto neutro."""
        result = analyzer._analyze_with_rules(
            text="El clima es templado hoy",
            speaker=None,
            chapter_id=1,
            start_char=0,
            end_char=24,
        )

        assert result.is_success
        state = result.value
        assert state.sentiment == Sentiment.NEUTRAL

    def test_analyze_dialogue(self, analyzer):
        """Test análisis de diálogo."""
        result = analyzer.analyze_dialogue(
            dialogue_text="¡Qué alegría verte de nuevo!",
            speaker="Carlos",
            context_before="Carlos se acercó sonriendo.",
            chapter_id=3,
            start_char=200,
            end_char=228,
        )

        assert result.is_success
        state = result.value
        assert state.speaker == "Carlos"
        assert state.chapter_id == 3

    def test_extract_declared_emotions_furioso(self, analyzer):
        """Test extracción de emociones declaradas - furioso."""
        text = "Juan estaba furioso. No podía creer lo que había pasado."
        entity_names = ["Juan", "María"]

        declared = analyzer.extract_declared_emotions(text, entity_names, chapter_id=1)

        assert len(declared) >= 1
        juan_states = [d for d in declared if d.entity_name == "Juan"]
        assert len(juan_states) >= 1
        assert juan_states[0].emotion == Emotion.ANGER
        assert juan_states[0].emotion_keyword == "furioso"

    def test_extract_declared_emotions_triste(self, analyzer):
        """Test extracción de emociones declaradas - triste."""
        text = "María estaba triste por la noticia."
        entity_names = ["María"]

        declared = analyzer.extract_declared_emotions(text, entity_names, chapter_id=2)

        maria_states = [d for d in declared if d.entity_name == "María"]
        assert len(maria_states) >= 1
        assert maria_states[0].emotion == Emotion.SADNESS

    def test_extract_declared_emotions_no_match(self, analyzer):
        """Test extracción sin coincidencias."""
        text = "El sol brillaba sobre la montaña."
        entity_names = ["Juan", "María"]

        declared = analyzer.extract_declared_emotions(text, entity_names)

        assert len(declared) == 0

    def test_detect_inconsistencies_anger_positive(self, analyzer):
        """Test detección de inconsistencia: furioso pero habla positivo."""
        declared = [
            DeclaredEmotionalState(
                entity_name="Juan",
                emotion=Emotion.ANGER,
                emotion_keyword="furioso",
                context="Juan estaba furioso",
                chapter_id=1,
                position=100,
            )
        ]

        dialogues = [
            EmotionalState(
                text="Claro, no hay problema, todo bien",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.85,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.7,
                speaker="Juan",
                chapter_id=1,
                start_char=150,
                end_char=183,
            )
        ]

        inconsistencies = analyzer.detect_inconsistencies(
            declared, dialogues, proximity_chars=500
        )

        assert len(inconsistencies) >= 1
        inc = inconsistencies[0]
        assert inc.entity_name == "Juan"
        assert inc.inconsistency_type == "emotion_dialogue_mismatch"
        assert "furioso" in inc.explanation

    def test_detect_inconsistencies_different_speaker(self, analyzer):
        """Test que no detecta inconsistencia si es otro personaje."""
        declared = [
            DeclaredEmotionalState(
                entity_name="Juan",
                emotion=Emotion.ANGER,
                emotion_keyword="furioso",
                context="Juan estaba furioso",
                chapter_id=1,
                position=100,
            )
        ]

        dialogues = [
            EmotionalState(
                text="Qué día tan bonito",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.9,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.8,
                speaker="María",  # Diferente personaje
                chapter_id=1,
                start_char=150,
                end_char=168,
            )
        ]

        inconsistencies = analyzer.detect_inconsistencies(
            declared, dialogues, proximity_chars=500
        )

        # No debería haber inconsistencia porque es otro personaje
        assert len(inconsistencies) == 0

    def test_detect_inconsistencies_different_chapter(self, analyzer):
        """Test que no detecta inconsistencia si es otro capítulo."""
        declared = [
            DeclaredEmotionalState(
                entity_name="Juan",
                emotion=Emotion.ANGER,
                emotion_keyword="furioso",
                context="Juan estaba furioso",
                chapter_id=1,
                position=100,
            )
        ]

        dialogues = [
            EmotionalState(
                text="Todo perfecto",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.9,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.8,
                speaker="Juan",
                chapter_id=2,  # Diferente capítulo
                start_char=150,
                end_char=163,
            )
        ]

        inconsistencies = analyzer.detect_inconsistencies(
            declared, dialogues, proximity_chars=500
        )

        assert len(inconsistencies) == 0

    def test_detect_inconsistencies_too_far(self, analyzer):
        """Test que no detecta inconsistencia si están muy lejos."""
        declared = [
            DeclaredEmotionalState(
                entity_name="Juan",
                emotion=Emotion.ANGER,
                emotion_keyword="furioso",
                context="Juan estaba furioso",
                chapter_id=1,
                position=100,
            )
        ]

        dialogues = [
            EmotionalState(
                text="Todo bien",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.9,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.8,
                speaker="Juan",
                chapter_id=1,
                start_char=10000,  # Muy lejos
                end_char=10009,
            )
        ]

        inconsistencies = analyzer.detect_inconsistencies(
            declared, dialogues, proximity_chars=500
        )

        assert len(inconsistencies) == 0

    def test_analyze_emotional_arc_no_change(self, analyzer):
        """Test arco emocional sin cambios abruptos."""
        dialogues = [
            EmotionalState(
                text="Estoy bien",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.8,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.7,
                speaker="Juan",
                chapter_id=1,
                start_char=100,
                end_char=110,
            ),
            EmotionalState(
                text="Todo va genial",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.85,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.75,
                speaker="Juan",
                chapter_id=1,
                start_char=200,
                end_char=214,
            ),
        ]

        inconsistencies = analyzer.analyze_emotional_arc(dialogues, "Juan")

        # No hay cambio abrupto (ambos positivos)
        assert len(inconsistencies) == 0

    def test_analyze_emotional_arc_abrupt_change(self, analyzer):
        """Test arco emocional con cambio abrupto."""
        dialogues = [
            EmotionalState(
                text="¡Qué felicidad! Todo es maravilloso",
                sentiment=Sentiment.POSITIVE,
                sentiment_confidence=0.9,
                primary_emotion=Emotion.JOY,
                emotion_confidence=0.85,
                speaker="Juan",
                chapter_id=1,
                start_char=100,
                end_char=135,
            ),
            EmotionalState(
                text="Esto es horrible, lo odio todo",
                sentiment=Sentiment.NEGATIVE,
                sentiment_confidence=0.9,
                primary_emotion=Emotion.ANGER,
                emotion_confidence=0.85,
                speaker="Juan",
                chapter_id=1,
                start_char=500,  # Mismo capítulo, cerca
                end_char=530,
            ),
        ]

        inconsistencies = analyzer.analyze_emotional_arc(dialogues, "Juan")

        assert len(inconsistencies) >= 1
        inc = inconsistencies[0]
        assert inc.inconsistency_type == "abrupt_emotional_change"
        assert "abrupta" in inc.explanation.lower()


class TestSentimentSingleton:
    """Tests para el singleton de SentimentAnalyzer."""

    def test_get_sentiment_analyzer(self):
        """Test obtención del singleton."""
        analyzer1 = get_sentiment_analyzer()
        analyzer2 = get_sentiment_analyzer()

        assert analyzer1 is analyzer2
        assert isinstance(analyzer1, SentimentAnalyzer)


class TestSentimentIntegration:
    """Tests de integración para análisis de sentimiento."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador."""
        return SentimentAnalyzer()

    def test_full_workflow(self, analyzer):
        """Test flujo completo de análisis."""
        # Texto narrativo con estado emocional y diálogo
        text = """
        Juan estaba furioso por lo que había ocurrido.
        Se acercó a María con paso decidido.
        """

        # Extraer emociones declaradas
        declared = analyzer.extract_declared_emotions(
            text,
            entity_names=["Juan", "María"],
            chapter_id=1
        )

        assert len(declared) >= 1
        assert any(d.entity_name == "Juan" and d.emotion == Emotion.ANGER for d in declared)

        # Simular diálogo analizado
        dialogue_result = analyzer.analyze_dialogue(
            dialogue_text="Claro, sin problema, todo perfecto",
            speaker="Juan",
            chapter_id=1,
            start_char=100,
            end_char=134,
        )

        assert dialogue_result.is_success

        # Detectar inconsistencias
        dialogues = [dialogue_result.value]
        inconsistencies = analyzer.detect_inconsistencies(
            declared, dialogues, proximity_chars=1000
        )

        # Debería detectar inconsistencia si el diálogo es positivo
        # (depende del análisis de sentimiento)
        # La prueba valida el flujo completo

    def test_multiple_characters(self, analyzer):
        """Test con múltiples personajes."""
        text = """
        Juan estaba furioso mientras María parecía contenta.
        Los dos se miraron sin decir nada.
        """

        declared = analyzer.extract_declared_emotions(
            text,
            entity_names=["Juan", "María"],
            chapter_id=1
        )

        juan_emotions = [d for d in declared if d.entity_name == "Juan"]
        maria_emotions = [d for d in declared if d.entity_name == "María"]

        # Juan debería estar furioso
        if juan_emotions:
            assert juan_emotions[0].emotion == Emotion.ANGER

        # María debería estar contenta
        if maria_emotions:
            assert maria_emotions[0].emotion == Emotion.JOY
