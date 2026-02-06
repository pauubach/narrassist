"""Tests para el módulo de coherencia emocional."""

import pytest

from narrative_assistant.analysis.emotional_coherence import (
    EMOTION_SENTIMENT_MAP,
    OPPOSITE_EMOTIONS,
    EmotionalCoherenceChecker,
    EmotionalIncoherence,
    IncoherenceType,
    get_emotional_coherence_checker,
    reset_emotional_coherence_checker,
)
from narrative_assistant.nlp.sentiment import (
    Emotion,
    Sentiment,
    SentimentAnalyzer,
)


class TestIncoherenceType:
    """Tests para IncoherenceType enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert IncoherenceType.EMOTION_DIALOGUE.value == "emotion_dialogue"
        assert IncoherenceType.EMOTION_ACTION.value == "emotion_action"
        assert IncoherenceType.TEMPORAL_JUMP.value == "temporal_jump"
        assert IncoherenceType.NARRATOR_BIAS.value == "narrator_bias"


class TestEmotionalIncoherence:
    """Tests para EmotionalIncoherence dataclass."""

    def test_create(self):
        """Test creación de incoherencia."""
        inc = EmotionalIncoherence(
            entity_name="Juan",
            incoherence_type=IncoherenceType.EMOTION_DIALOGUE,
            declared_emotion="furioso",
            actual_behavior="positive (joy)",
            declared_text="Juan estaba furioso",
            behavior_text="Claro, sin problema",
            confidence=0.8,
            explanation="Explicación",
            suggestion="Sugerencia",
            chapter_id=1,
            start_char=100,
            end_char=120,
        )

        assert inc.entity_name == "Juan"
        assert inc.incoherence_type == IncoherenceType.EMOTION_DIALOGUE
        assert inc.declared_emotion == "furioso"
        assert inc.confidence == 0.8

    def test_to_dict(self):
        """Test conversión a diccionario."""
        inc = EmotionalIncoherence(
            entity_name="María",
            incoherence_type=IncoherenceType.TEMPORAL_JUMP,
            declared_emotion="devastada",
            actual_behavior="eufórica",
            declared_text="Estaba devastada",
            behavior_text="Saltaba de alegría",
            confidence=0.7,
            explanation="Cambio abrupto",
            chapter_id=2,
        )

        d = inc.to_dict()
        assert d["entity_name"] == "María"
        assert d["incoherence_type"] == "temporal_jump"
        assert d["declared_emotion"] == "devastada"


class TestEmotionSentimentMap:
    """Tests para el mapeo de emociones a sentimientos."""

    def test_negative_emotions_map_to_negative(self):
        """Emociones negativas deben mapear a sentimiento negativo."""
        negative_emotions = ["furioso", "triste", "aterrado", "desesperado"]
        for emotion in negative_emotions:
            expected = EMOTION_SENTIMENT_MAP.get(emotion, set())
            assert "negative" in expected, f"{emotion} debería mapear a negative"

    def test_positive_emotions_map_to_positive(self):
        """Emociones positivas deben mapear a sentimiento positivo."""
        positive_emotions = ["feliz", "eufórico", "entusiasmado"]
        for emotion in positive_emotions:
            expected = EMOTION_SENTIMENT_MAP.get(emotion, set())
            assert "positive" in expected, f"{emotion} debería mapear a positive"

    def test_neutral_emotions_allow_neutral(self):
        """Emociones neutras deben permitir sentimiento neutro."""
        neutral_emotions = ["tranquilo", "sereno", "reflexivo"]
        for emotion in neutral_emotions:
            expected = EMOTION_SENTIMENT_MAP.get(emotion, set())
            assert "neutral" in expected, f"{emotion} debería permitir neutral"


class TestOppositeEmotions:
    """Tests para pares de emociones opuestas."""

    def test_opposites_are_bidirectional(self):
        """Verifica que los opuestos cubren ambas direcciones."""
        # No necesariamente tienen que ser bidireccionales en el set,
        # pero el código debe manejar ambas direcciones
        assert ("furioso", "tranquilo") in OPPOSITE_EMOTIONS
        assert ("devastado", "eufórico") in OPPOSITE_EMOTIONS

    def test_key_opposites_exist(self):
        """Verifica que los opuestos clave están definidos."""
        key_pairs = [
            ("furioso", "tranquilo"),
            ("devastado", "feliz"),
            ("triste", "alegre"),
        ]
        for pair in key_pairs:
            reverse = (pair[1], pair[0])
            assert pair in OPPOSITE_EMOTIONS or reverse in OPPOSITE_EMOTIONS


class TestEmotionalCoherenceChecker:
    """Tests para EmotionalCoherenceChecker."""

    @pytest.fixture
    def checker(self):
        """Crea verificador de coherencia."""
        reset_emotional_coherence_checker()
        return EmotionalCoherenceChecker()

    def test_creation(self, checker):
        """Test creación del verificador."""
        assert checker is not None
        assert checker.sentiment is not None
        assert checker.min_confidence == 0.4

    def test_custom_confidence(self):
        """Test con confianza personalizada."""
        checker = EmotionalCoherenceChecker(min_confidence=0.8)
        assert checker.min_confidence == 0.8

    def test_emotion_to_expected_sentiment_negative(self, checker):
        """Test mapeo de emociones negativas."""
        assert "negative" in checker._emotion_to_expected_sentiment("furioso")
        assert "negative" in checker._emotion_to_expected_sentiment("triste")
        assert "negative" in checker._emotion_to_expected_sentiment("aterrado")

    def test_emotion_to_expected_sentiment_positive(self, checker):
        """Test mapeo de emociones positivas."""
        assert "positive" in checker._emotion_to_expected_sentiment("feliz")
        assert "positive" in checker._emotion_to_expected_sentiment("eufórico")

    def test_emotion_to_expected_sentiment_unknown(self, checker):
        """Test mapeo de emoción desconocida."""
        result = checker._emotion_to_expected_sentiment("desconocida")
        assert "neutral" in result

    def test_is_extreme_change_true(self, checker):
        """Test detección de cambio extremo."""
        assert checker._is_extreme_change("furioso", "tranquilo") is True
        assert checker._is_extreme_change("tranquilo", "furioso") is True
        assert checker._is_extreme_change("devastado", "eufórico") is True
        assert checker._is_extreme_change("triste", "feliz") is True

    def test_is_extreme_change_false(self, checker):
        """Test sin cambio extremo."""
        assert checker._is_extreme_change("triste", "melancólico") is False
        assert checker._is_extreme_change("feliz", "contento") is False
        assert checker._is_extreme_change("neutro", "pensativo") is False

    def test_has_irony_marker(self, checker):
        """Test detección de marcadores de ironía."""
        assert checker._has_irony_marker("—dijo con ironía") is True
        assert checker._has_irony_marker("respondió sarcástico") is True
        assert checker._has_irony_marker("en tono burlón") is True
        assert checker._has_irony_marker("simplemente dijo") is False

    def test_has_concealment_marker(self, checker):
        """Test detección de marcadores de disimulo."""
        assert checker._has_concealment_marker("ocultando su enfado") is True
        assert checker._has_concealment_marker("fingiendo calma") is True
        assert checker._has_concealment_marker("aparentando felicidad") is True
        assert checker._has_concealment_marker("estaba triste") is False

    def test_check_dialogue_coherence_with_irony(self, checker):
        """Test que la ironía se detecta y no genera incoherencia."""
        result = checker.check_dialogue_coherence(
            entity_name="Juan",
            declared_emotion="furioso",
            dialogue_text="Oh, qué maravilloso",
            context="Juan estaba furioso. —dijo con ironía—",
            chapter_id=1,
        )
        # No debería detectar incoherencia porque hay marcador de ironía
        assert result is None

    def test_check_dialogue_coherence_with_concealment(self, checker):
        """Test que el disimulo se detecta y no genera incoherencia."""
        result = checker.check_dialogue_coherence(
            entity_name="María",
            declared_emotion="aterrada",
            dialogue_text="Todo está bien",
            context="María, ocultando su miedo, respondió:",
            chapter_id=1,
        )
        # No debería detectar incoherencia porque hay disimulo
        assert result is None

    def test_check_temporal_evolution_no_issues(self, checker):
        """Test evolución temporal sin problemas."""
        states = [
            (1, "triste", "Estaba algo triste"),
            (2, "melancólico", "Se sentía melancólico"),
            (3, "neutro", "Se sentía neutro"),
        ]

        incoherences = checker.check_temporal_evolution("Juan", states)
        assert len(incoherences) == 0

    def test_check_temporal_evolution_abrupt_change(self, checker):
        """Test evolución temporal con cambio abrupto."""
        states = [
            (1, "devastado", "Estaba devastado"),
            (2, "eufórico", "Estaba eufórico"),  # Cambio extremo cap consecutivo
        ]

        incoherences = checker.check_temporal_evolution("Juan", states)
        assert len(incoherences) >= 1
        assert incoherences[0].incoherence_type == IncoherenceType.TEMPORAL_JUMP
        assert incoherences[0].entity_name == "Juan"

    def test_check_temporal_evolution_non_consecutive(self, checker):
        """Test que capítulos no consecutivos no generan alerta."""
        states = [
            (1, "devastado", "Estaba devastado"),
            (5, "eufórico", "Estaba eufórico"),  # No consecutivo
        ]

        incoherences = checker.check_temporal_evolution("Juan", states)
        assert len(incoherences) == 0

    def test_check_action_coherence_fear_brave(self, checker):
        """Test incoherencia entre miedo y acción valiente."""
        result = checker.check_action_coherence(
            entity_name="Pedro",
            declared_emotion="aterrado",
            action_text="Avanzó decidido hacia el peligro",
            context="Pedro estaba aterrado",
            chapter_id=3,
        )

        assert result is not None
        assert result.incoherence_type == IncoherenceType.EMOTION_ACTION
        assert result.entity_name == "Pedro"

    def test_check_action_coherence_no_issue(self, checker):
        """Test acción coherente con emoción."""
        result = checker.check_action_coherence(
            entity_name="María",
            declared_emotion="feliz",
            action_text="Saltó de la cama con energía",
            context="María estaba feliz",
            chapter_id=1,
        )

        # No debería detectar incoherencia
        assert result is None


class TestEmotionalCoherenceSingleton:
    """Tests para el singleton del verificador."""

    def test_get_singleton(self):
        """Test obtención del singleton."""
        reset_emotional_coherence_checker()
        checker1 = get_emotional_coherence_checker()
        checker2 = get_emotional_coherence_checker()

        assert checker1 is checker2

    def test_reset_singleton(self):
        """Test reseteo del singleton."""
        reset_emotional_coherence_checker()
        checker1 = get_emotional_coherence_checker()

        reset_emotional_coherence_checker()
        checker2 = get_emotional_coherence_checker()

        assert checker1 is not checker2


class TestEmotionalCoherenceIntegration:
    """Tests de integración para coherencia emocional."""

    @pytest.fixture
    def checker(self):
        """Crea verificador."""
        reset_emotional_coherence_checker()
        return EmotionalCoherenceChecker()

    def test_analyze_chapter_workflow(self, checker):
        """Test flujo de análisis de capítulo."""
        chapter_text = """
        Juan estaba furioso por la traición de su socio.
        Caminaba de un lado a otro de la habitación.
        """

        entity_names = ["Juan", "María"]
        dialogues = []  # Sin diálogos en este fragmento
        chapter_id = 1

        incoherences = checker.analyze_chapter(
            chapter_text=chapter_text,
            entity_names=entity_names,
            dialogues=dialogues,
            chapter_id=chapter_id,
        )

        # Sin diálogos, no debería haber incoherencias diálogo-emoción
        assert isinstance(incoherences, list)

    def test_full_dialogue_analysis(self, checker):
        """Test análisis completo de diálogo."""
        # Este test depende del análisis de sentimiento
        result = checker.check_dialogue_coherence(
            entity_name="Carlos",
            declared_emotion="devastado",
            dialogue_text="¡Qué alegría verte! Todo es maravilloso",
            context="Carlos estaba devastado por la noticia",
            chapter_id=2,
            start_char=100,
            end_char=150,
        )

        # Puede o no detectar incoherencia dependiendo del análisis de sentimiento
        # El test verifica que no hay errores en el flujo
        if result is not None:
            assert result.entity_name == "Carlos"
            assert result.declared_emotion == "devastado"
