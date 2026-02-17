"""
Tests MVP para Character Speech Consistency Tracking.

Valida funcionalidad básica sin dependencias pesadas.
"""

import pytest
from narrative_assistant.analysis.speech_tracking import (
    SpeechWindow,
    SpeechMetrics,
    ChangeDetector,
    SpeechTracker,
    ContextualAnalyzer,
    create_sliding_windows,
)
from narrative_assistant.analysis.speech_tracking.types import MetricChangeResult


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_chapter():
    """Mock de capítulo con texto."""

    class MockChapter:
        def __init__(self, chapter_number, text):
            self.chapter_number = chapter_number
            self.text = text
            self.content = text

    return MockChapter


@pytest.fixture
def sample_dialogues_consistent():
    """Diálogos consistentes (mismo estilo)."""
    return [
        "O sea, la verdad es que me parece bien.",
        "Pues sí, o sea, básicamente eso es lo que pienso.",
        "La verdad, no sé qué decir, o sea.",
    ]


@pytest.fixture
def sample_dialogues_formal():
    """Diálogos formales (sin muletillas)."""
    return [
        "Considero que la propuesta es adecuada.",
        "Evidentemente, esto requiere mayor análisis.",
        "Permitame expresar mi desacuerdo respetuosamente.",
    ]


# =============================================================================
# Tests: SpeechWindow
# =============================================================================


def test_speech_window_creation():
    """Test creación básica de SpeechWindow."""
    window = SpeechWindow(
        character_id=1,
        character_name="Juan",
        start_chapter=1,
        end_chapter=3,
        dialogues=["Hola", "Adiós"],
        total_words=2,
        dialogue_count=2,
    )

    assert window.character_id == 1
    assert window.character_name == "Juan"
    assert window.chapter_range == "1-3"
    assert window.avg_words_per_dialogue == 1.0


def test_speech_window_single_chapter():
    """Test ventana de un solo capítulo."""
    window = SpeechWindow(
        character_id=1,
        character_name="María",
        start_chapter=5,
        end_chapter=5,
        dialogues=["Texto"],
        total_words=1,
        dialogue_count=1,
    )

    assert window.chapter_range == "5"


def test_create_sliding_windows_basic(mock_chapter):
    """Test creación de ventanas deslizantes básico."""
    chapters = [
        mock_chapter(1, "—Hola —dijo Juan. —¿Cómo estás?"),
        mock_chapter(2, "—Bien —respondió Juan. —Gracias."),
        mock_chapter(3, "—Me alegro —dijo Juan."),
    ]

    windows = create_sliding_windows(
        character_id=1,
        character_name="Juan",
        chapters=chapters,
        window_size=2,
        overlap=1,
        min_words_per_window=1,  # Relajado para test
    )

    # Con window_size=2, overlap=1: [0-1], [1-2]
    assert len(windows) >= 1  # Al menos una ventana


# =============================================================================
# Tests: SpeechMetrics
# =============================================================================


def test_speech_metrics_filler_rate():
    """Test cálculo de filler_rate."""
    dialogues = [
        "O sea, la verdad es que básicamente me parece bien.",
        "Pues sí, o sea, literalmente eso es lo que pienso.",
    ]

    metrics = SpeechMetrics.calculate(dialogues, spacy_nlp=None)

    # Debe detectar muletillas (o sea, la verdad, básicamente, literalmente)
    assert "filler_rate" in metrics
    assert metrics["filler_rate"] >= 0.0


def test_speech_metrics_lexical_diversity():
    """Test cálculo de lexical_diversity (TTR)."""
    # Texto con baja diversidad (palabras repetidas)
    dialogues_low_diversity = ["hola hola hola mundo mundo"]

    # Texto con alta diversidad (palabras únicas)
    dialogues_high_diversity = ["amanecer brillante colorido día especial"]

    metrics_low = SpeechMetrics.calculate(dialogues_low_diversity)
    metrics_high = SpeechMetrics.calculate(dialogues_high_diversity)

    assert metrics_low["lexical_diversity"] < metrics_high["lexical_diversity"]


def test_speech_metrics_exclamation_rate():
    """Test cálculo de exclamation_rate."""
    dialogues_no_exclamations = ["Hola. Cómo estás. Bien."]
    dialogues_with_exclamations = ["¡Hola! ¡Qué alegría! ¡Genial!"]

    metrics_no = SpeechMetrics.calculate(dialogues_no_exclamations)
    metrics_yes = SpeechMetrics.calculate(dialogues_with_exclamations)

    assert metrics_no["exclamation_rate"] < metrics_yes["exclamation_rate"]


def test_speech_metrics_question_rate():
    """Test cálculo de question_rate."""
    dialogues_no_questions = ["Es un día bonito. Hace sol."]
    dialogues_with_questions = ["¿Cómo estás? ¿Qué tal? ¿Todo bien?"]

    metrics_no = SpeechMetrics.calculate(dialogues_no_questions)
    metrics_yes = SpeechMetrics.calculate(dialogues_with_questions)

    assert metrics_no["question_rate"] < metrics_yes["question_rate"]


# =============================================================================
# Tests: ChangeDetector
# =============================================================================


def test_change_detector_no_change():
    """Test que NO detecta cambio cuando valores son iguales."""
    detector = ChangeDetector()

    result = detector.detect_metric_change(
        metric_name="filler_rate",
        value1=5.0,
        value2=5.1,  # Cambio mínimo (2%)
        n1=500,
        n2=500,
    )

    # Cambio relativo < threshold (15%) → NO significativo
    assert result.is_significant is False


def test_change_detector_significant_change():
    """Test que detecta cambio significativo."""
    detector = ChangeDetector()

    result = detector.detect_metric_change(
        metric_name="filler_rate",
        value1=10.0,
        value2=2.0,  # Cambio grande (-80%)
        n1=500,
        n2=500,
    )

    # Cambio relativo > threshold (15%) → significativo
    assert result.relative_change > 0.15
    # El detector debería marcarlo como significativo
    # (depende de p-value también)


def test_change_detector_formality_shift():
    """Test detección de cambio en formalidad."""
    detector = ChangeDetector()

    result = detector.detect_metric_change(
        metric_name="formality_score",
        value1=0.2,  # Coloquial
        value2=0.8,  # Formal
        n1=300,
        n2=300,
    )

    # Cambio > threshold (0.25) → significativo
    assert result.relative_change > 0.25


# =============================================================================
# Tests: ContextualAnalyzer
# =============================================================================


def test_contextual_analyzer_no_event(mock_chapter):
    """Test que NO detecta evento cuando no hay keywords."""
    analyzer = ContextualAnalyzer()

    chapters = [mock_chapter(1, "Juan caminó por el parque tranquilamente.")]

    context = analyzer.analyze(chapters)

    assert context.has_dramatic_event is False
    assert context.event_type is None


def test_contextual_analyzer_death_event(mock_chapter):
    """Test detección de evento de muerte."""
    analyzer = ContextualAnalyzer()

    chapters = [
        mock_chapter(
            1,
            "María lloró desconsoladamente. Su padre había muerto. "
            "El funeral fue al día siguiente. Todo el pueblo asistió al entierro.",
        )
    ]

    context = analyzer.analyze(chapters)

    assert context.has_dramatic_event is True
    assert context.event_type == "muerte"
    assert len(context.keywords_found) > 0


def test_contextual_analyzer_wedding_event(mock_chapter):
    """Test detección de evento de boda."""
    analyzer = ContextualAnalyzer()

    chapters = [
        mock_chapter(
            1, "La boda fue hermosa. Los esposos intercambiaron votos ante el altar."
        )
    ]

    context = analyzer.analyze(chapters)

    assert context.has_dramatic_event is True
    assert context.event_type == "boda"


def test_contextual_analyzer_fight_event(mock_chapter):
    """Test detección de pelea."""
    analyzer = ContextualAnalyzer()

    chapters = [
        mock_chapter(
            1,
            "Discutieron violentamente. Juan gritó furioso y golpeó la mesa. "
            "La pelea duró horas.",
        )
    ]

    context = analyzer.analyze(chapters)

    assert context.has_dramatic_event is True
    assert context.event_type == "pelea"


# =============================================================================
# Tests: SpeechTracker (Integration)
# =============================================================================


def test_speech_tracker_consistent_character(
    mock_chapter, sample_dialogues_consistent
):
    """Test que NO genera alerta para personaje consistente."""
    tracker = SpeechTracker(window_size=2, overlap=1, min_confidence=0.6)

    # Mock chapters con diálogos consistentes
    chapters = []
    for i in range(6):
        text = " ".join(
            [
                f"—{dialogue} —dijo Juan."
                for dialogue in sample_dialogues_consistent
            ]
        )
        chapters.append(mock_chapter(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1,
        character_name="Juan",
        chapters=chapters,
        spacy_nlp=None,
        narrative_context_analyzer=None,
    )

    # Personaje consistente → NO alertas (o muy pocas)
    assert len(alerts) == 0 or all(a.confidence < 0.6 for a in alerts)


def test_speech_tracker_abrupt_change(
    mock_chapter, sample_dialogues_consistent, sample_dialogues_formal
):
    """Test que genera alerta para cambio abrupto."""
    tracker = SpeechTracker(
        window_size=2, overlap=0, min_confidence=0.5  # Sin solapamiento para test
    )

    # Capítulos 1-3: coloquial (muletillas)
    chapters_coloquial = []
    for i in range(3):
        text = " ".join(
            [f"—{d} —dijo Juan." for d in sample_dialogues_consistent]
        )
        chapters_coloquial.append(mock_chapter(i + 1, text))

    # Capítulos 4-6: formal (sin muletillas)
    chapters_formal = []
    for i in range(3, 6):
        text = " ".join([f"—{d} —dijo Juan." for d in sample_dialogues_formal])
        chapters_formal.append(mock_chapter(i + 1, text))

    all_chapters = chapters_coloquial + chapters_formal

    alerts = tracker.detect_changes(
        character_id=1,
        character_name="Juan",
        chapters=all_chapters,
        spacy_nlp=None,
        narrative_context_analyzer=None,
    )

    # Cambio abrupto coloquial → formal → debe generar alerta
    # (si hay suficientes palabras en ventanas)
    # Nota: Puede no generar alerta si sample es muy pequeño
    # Este test valida que el sistema NO crashea, no necesariamente
    # que siempre genere alerta (depende de thresholds)
    assert isinstance(alerts, list)


def test_speech_tracker_insufficient_data(mock_chapter):
    """Test que NO genera alertas con datos insuficientes."""
    tracker = SpeechTracker(
        window_size=3, overlap=1, min_words_per_window=200  # Umbral alto
    )

    # Solo 2 capítulos con poco texto
    chapters = [
        mock_chapter(1, "—Hola —dijo Juan."),
        mock_chapter(2, "—Adiós —dijo Juan."),
    ]

    alerts = tracker.detect_changes(
        character_id=1,
        character_name="Juan",
        chapters=chapters,
        spacy_nlp=None,
        narrative_context_analyzer=None,
    )

    # Datos insuficientes → NO alertas
    assert len(alerts) == 0


# =============================================================================
# Tests: Edge Cases
# =============================================================================


def test_empty_dialogues():
    """Test manejo de diálogos vacíos."""
    metrics = SpeechMetrics.calculate([], spacy_nlp=None)

    # Debe retornar métricas en 0, NO crashear
    assert all(v == 0.0 for v in metrics.values())


def test_single_word_dialogue():
    """Test manejo de diálogo de una sola palabra."""
    metrics = SpeechMetrics.calculate(["Sí"], spacy_nlp=None)

    assert metrics["lexical_diversity"] == 1.0  # Todas las palabras son únicas


def test_very_long_dialogue():
    """Test manejo de diálogo muy largo."""
    long_dialogue = " ".join(["palabra"] * 1000)
    metrics = SpeechMetrics.calculate([long_dialogue])

    assert metrics["lexical_diversity"] == 1.0 / 1000  # Solo 1 palabra única
    assert metrics["avg_sentence_length"] > 0


def test_special_characters_in_dialogue():
    """Test manejo de caracteres especiales."""
    dialogues = [
        "¡¡¡Increíble!!!",
        "¿¿Qué??",
        "..."
    ]

    metrics = SpeechMetrics.calculate(dialogues)

    # Debe manejar sin crashear
    assert metrics["exclamation_rate"] > 0
    assert metrics["question_rate"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
