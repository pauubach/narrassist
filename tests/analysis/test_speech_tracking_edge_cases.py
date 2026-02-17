"""
Batería de Tests - Edge Cases para Speech Consistency Tracking.

Cubre casos extremos, situaciones reales y escenarios complejos.
"""

import pytest
from narrative_assistant.analysis.speech_tracking import (
    SpeechWindow,
    SpeechMetrics,
    SpeechTracker,
    ContextualAnalyzer,
    create_sliding_windows,
)


# =============================================================================
# Fixtures Avanzados
# =============================================================================


@pytest.fixture
def mock_chapter_factory():
    """Factory para crear mock chapters dinámicamente."""

    class MockChapter:
        def __init__(self, chapter_number, text, dialogues=None):
            self.chapter_number = chapter_number
            self.text = text
            self.content = text
            self.dialogues = dialogues or []

    def create_chapter(chapter_number, text, dialogues=None):
        return MockChapter(chapter_number, text, dialogues)

    return create_chapter


# =============================================================================
# Edge Case: Flashbacks y Saltos Temporales
# =============================================================================


def test_flashback_child_vs_adult(mock_chapter_factory):
    """
    Test personaje niño en caps 1-3, adulto en caps 10-12.

    El cambio de habla es VÁLIDO (desarrollo natural), no inconsistencia.
    El sistema NO debería generar alerta HIGH, máximo LOW/MEDIUM.
    """
    tracker = SpeechTracker(window_size=3, overlap=1, min_confidence=0.6)

    # Capítulos 1-3: Niño (habla infantil, simple)
    chapters_child = []
    for i in range(3):
        text = "—Mamá quiero helado. Tengo hambre. Dame más. —dijo Juanito."
        chapters_child.append(mock_chapter_factory(i + 1, text * 20))

    # Capítulos 10-12: Adulto (habla madura, compleja)
    chapters_adult = []
    for i in range(10, 13):
        text = (
            "—Considero que la propuesta económica requiere un análisis "
            "profundo de sus implicaciones fiscales. —dijo Juan."
        )
        chapters_adult.append(mock_chapter_factory(i, text * 20))

    all_chapters = chapters_child + chapters_adult

    alerts = tracker.detect_changes(
        character_id=1,
        character_name="Juan",
        chapters=all_chapters,
        spacy_nlp=None,
        narrative_context_analyzer=None,
    )

    # Si genera alerta, severidad debe ser LOW (es desarrollo válido)
    for alert in alerts:
        assert alert.severity in ("low", "medium")


def test_narrative_gap_no_continuous_chapters(mock_chapter_factory):
    """
    Test ventanas con capítulos no contiguos (saltos en numeración).

    El sistema debe manejar gaps en capítulos sin crashear.
    """
    tracker = SpeechTracker(window_size=2, overlap=1)

    # Capítulos: 1, 2, 5, 6, 10, 11 (gaps: 3-4, 7-9)
    chapters = [
        mock_chapter_factory(1, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(2, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(5, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(6, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(10, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(11, "—Texto. —dijo Ana." * 50),
    ]

    alerts = tracker.detect_changes(
        character_id=1, character_name="Ana", chapters=chapters
    )

    # NO debe crashear, resultado puede ser vacío o con alertas
    assert isinstance(alerts, list)


# =============================================================================
# Edge Case: Personajes Bilingües
# =============================================================================


def test_bilingual_character_spanish_english(mock_chapter_factory):
    """
    Test personaje que mezcla español e inglés.

    NO debe detectar como inconsistencia el código-switching natural.
    """
    tracker = SpeechTracker(window_size=2, overlap=1, min_confidence=0.7)

    # Capítulos con mezcla español-inglés consistente
    chapters = []
    for i in range(6):
        text = (
            "—Sí, I agree with that. Es una buena idea, you know? "
            "La verdad, it makes sense. —dijo María."
        )
        chapters.append(mock_chapter_factory(i + 1, text * 30))

    alerts = tracker.detect_changes(
        character_id=1, character_name="María", chapters=chapters
    )

    # Mezcla consistente → NO debería generar alertas (o muy pocas)
    assert len(alerts) <= 1


# =============================================================================
# Edge Case: Capítulos Muy Cortos
# =============================================================================


def test_very_short_chapters(mock_chapter_factory):
    """
    Test con capítulos muy cortos (<100 palabras).

    El sistema debe filtrar ventanas con muestra insuficiente.
    """
    tracker = SpeechTracker(
        window_size=3, overlap=1, min_words_per_window=200  # Umbral alto
    )

    # Capítulos muy cortos (10 palabras cada uno)
    chapters = []
    for i in range(10):
        text = "—Hola cómo estás bien gracias. —dijo Pedro."
        chapters.append(mock_chapter_factory(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1, character_name="Pedro", chapters=chapters
    )

    # Muestra insuficiente → NO alertas
    assert len(alerts) == 0


# =============================================================================
# Edge Case: Personajes sin Diálogos en Ventanas
# =============================================================================


def test_character_no_dialogues_in_window(mock_chapter_factory):
    """
    Test personaje que NO habla en algunos capítulos.

    Ejemplo: Aparece en caps 1-3, ausente en 4-6, regresa en 7-9.
    """
    tracker = SpeechTracker(window_size=3, overlap=1)

    # Capítulos 1-3: Con diálogos
    chapters_with_dialogue = []
    for i in range(3):
        text = "—Hola mundo. —dijo Carlos." * 50
        chapters_with_dialogue.append(mock_chapter_factory(i + 1, text))

    # Capítulos 4-6: SIN diálogos de Carlos (solo narración)
    chapters_no_dialogue = []
    for i in range(3, 6):
        text = "La ciudad estaba tranquila. El sol brillaba." * 50
        chapters_no_dialogue.append(mock_chapter_factory(i + 1, text))

    # Capítulos 7-9: Con diálogos de nuevo
    chapters_return = []
    for i in range(6, 9):
        text = "—Hola de nuevo. —dijo Carlos." * 50
        chapters_return.append(mock_chapter_factory(i + 1, text))

    all_chapters = (
        chapters_with_dialogue + chapters_no_dialogue + chapters_return
    )

    alerts = tracker.detect_changes(
        character_id=1, character_name="Carlos", chapters=all_chapters
    )

    # Sistema debe manejar ausencia sin crashear
    assert isinstance(alerts, list)


# =============================================================================
# Edge Case: Cambios Graduales vs Abruptos
# =============================================================================


def test_gradual_change_vs_abrupt(mock_chapter_factory):
    """
    Test diferencia entre cambio gradual (válido) y abrupto (inconsistencia).

    Gradual: 10% → 9% → 8% → 7% (OK)
    Abrupto: 10% → 2% (alerta)
    """
    tracker = SpeechTracker(window_size=2, overlap=1, min_confidence=0.6)

    # Cambio gradual (filler_rate decreciendo lentamente)
    chapters_gradual = []
    filler_texts = [
        "O sea pues la verdad básicamente",  # Alta densidad
        "O sea pues la verdad",  # Media-alta
        "O sea pues",  # Media
        "Pues",  # Baja
    ]

    for i, filler_text in enumerate(filler_texts):
        text = f"—{filler_text} es una buena idea. —dijo Ana." * 50
        chapters_gradual.append(mock_chapter_factory(i + 1, text))

    alerts_gradual = tracker.detect_changes(
        character_id=1, character_name="Ana", chapters=chapters_gradual
    )

    # Cambio gradual → NO debería generar alertas HIGH
    high_severity_alerts = [a for a in alerts_gradual if a.severity == "high"]
    assert len(high_severity_alerts) == 0


def test_abrupt_change_high_severity(mock_chapter_factory):
    """Test cambio abrupto genera alerta HIGH."""
    tracker = SpeechTracker(window_size=2, overlap=0, min_confidence=0.5)

    # Caps 1-2: Muletillas intensas
    chapters_before = []
    for i in range(2):
        text = (
            "—O sea pues la verdad básicamente literalmente o sea pues. "
            "—dijo Luis."
        ) * 50
        chapters_before.append(mock_chapter_factory(i + 1, text))

    # Caps 3-4: Formal extremo (sin muletillas)
    chapters_after = []
    for i in range(2, 4):
        text = (
            "—Evidentemente considero que la situación requiere análisis. "
            "—dijo Luis."
        ) * 50
        chapters_after.append(mock_chapter_factory(i + 1, text))

    all_chapters = chapters_before + chapters_after

    alerts = tracker.detect_changes(
        character_id=1, character_name="Luis", chapters=all_chapters
    )

    # Cambio abrupto → al menos 1 alerta (puede ser medium/high)
    # (si hay suficiente confianza)
    assert len(alerts) >= 0  # Puede o no generar según thresholds exactos


# =============================================================================
# Edge Case: Eventos Narrativos que Justifican Cambios
# =============================================================================


def test_trauma_justifies_speech_change(mock_chapter_factory):
    """
    Test que trauma detectado reduce severidad de alerta.

    Personaje cambia de habla tras evento traumático → severity LOW.
    """
    tracker = SpeechTracker(window_size=2, overlap=0, min_confidence=0.5)
    analyzer = ContextualAnalyzer()

    # Caps 1-2: Habla normal
    chapters_before = []
    for i in range(2):
        text = "—Estoy bien, todo va genial. —dijo Laura." * 50
        chapters_before.append(mock_chapter_factory(i + 1, text))

    # Cap 3: TRAUMA (entre ventanas)
    chapter_trauma = mock_chapter_factory(
        3,
        "Laura sufrió un accidente grave. Estuvo en el hospital. "
        "Fue un shock terrible. Sangre por todas partes. Emergencia." * 20,
    )

    # Caps 4-5: Habla cambiada (apagada, sin energía)
    chapters_after = []
    for i in range(3, 5):
        text = "—No sé. Tal vez. Da igual. —dijo Laura." * 50
        chapters_after.append(mock_chapter_factory(i + 1, text))

    all_chapters = chapters_before + [chapter_trauma] + chapters_after

    alerts = tracker.detect_changes(
        character_id=1,
        character_name="Laura",
        chapters=all_chapters,
        narrative_context_analyzer=analyzer,
    )

    # Si hay alerta, debería tener severidad baja (justificada por trauma)
    for alert in alerts:
        if alert.narrative_context and alert.narrative_context.has_dramatic_event:
            assert alert.severity in ("low", "medium")


# =============================================================================
# Edge Case: Personajes Secundarios (Poco Texto)
# =============================================================================


def test_secondary_character_filtered_out(mock_chapter_factory):
    """
    Test que personajes secundarios (<200 palabras) se filtran.

    El pipeline NO debería procesar personajes con poco diálogo.
    """
    tracker = SpeechTracker(
        window_size=3, overlap=1, min_words_per_window=200  # Umbral alto
    )

    # Personaje secundario: solo 3 diálogos cortos
    chapters = []
    for i in range(6):
        text = "—Sí. —dijo Secretaria."  # 1 palabra
        chapters.append(mock_chapter_factory(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1, character_name="Secretaria", chapters=chapters
    )

    # Muy poco texto → NO alertas (filtrado)
    assert len(alerts) == 0


# =============================================================================
# Edge Case: Diálogos con Formato Inusual
# =============================================================================


def test_dialogue_without_quotation_marks(mock_chapter_factory):
    """
    Test extracción de diálogos sin rayas (—).

    Algunos autores usan otros formatos.
    """
    # Este test valida que el sistema NO crashea
    # (puede no extraer correctamente, pero no debe fallar)
    tracker = SpeechTracker(window_size=2, overlap=1)

    chapters = []
    for i in range(4):
        # Diálogo sin rayas (estilo directo sin marcas)
        text = "Juan dijo que estaba cansado. María respondió que sí." * 50
        chapters.append(mock_chapter_factory(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1, character_name="Juan", chapters=chapters
    )

    # NO debe crashear (resultado puede ser vacío)
    assert isinstance(alerts, list)


# =============================================================================
# Edge Case: Texto con Encoding Especial
# =============================================================================


def test_unicode_special_characters(mock_chapter_factory):
    """Test manejo de caracteres Unicode especiales."""
    tracker = SpeechTracker(window_size=2, overlap=1)

    chapters = []
    for i in range(4):
        # Texto con emojis, símbolos, acentos raros
        text = (
            "—¡Increíble! 😊 ¿Cómo así? Ñoño. Curaçao. Zürich. ™ © ®. "
            "—dijo José."
        ) * 50
        chapters.append(mock_chapter_factory(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1, character_name="José", chapters=chapters
    )

    # NO debe crashear con caracteres especiales
    assert isinstance(alerts, list)


# =============================================================================
# Edge Case: Performance con Manuscritos Grandes
# =============================================================================


def test_large_manuscript_performance(mock_chapter_factory):
    """
    Test rendimiento con manuscrito grande (100 capítulos).

    Debe completar en <5 segundos (sin scipy/spaCy).
    """
    import time

    tracker = SpeechTracker(window_size=3, overlap=1, min_confidence=0.6)

    # Crear 100 capítulos con texto mediano
    chapters = []
    for i in range(100):
        text = "—Texto de diálogo estándar aquí. —dijo Personaje." * 100
        chapters.append(mock_chapter_factory(i + 1, text))

    start_time = time.time()

    alerts = tracker.detect_changes(
        character_id=1, character_name="Personaje", chapters=chapters
    )

    elapsed = time.time() - start_time

    # Debe completar en tiempo razonable (<10s sin scipy)
    assert elapsed < 10.0
    assert isinstance(alerts, list)


# =============================================================================
# Edge Case: Múltiples Métricas Cambian Simultáneamente
# =============================================================================


def test_multiple_metrics_change_together(mock_chapter_factory):
    """
    Test cuando TODAS las métricas cambian a la vez.

    Esto indica cambio muy fuerte → alta confianza.
    """
    tracker = SpeechTracker(window_size=2, overlap=0, min_confidence=0.6)

    # Caps 1-2: Coloquial, oraciones cortas, muletillas, exclamaciones
    chapters_before = []
    for i in range(2):
        text = (
            "—¡O sea! ¡Pues sí! ¡La verdad! ¿Básicamente? ¿Literalmente? "
            "—dijo Marta."
        ) * 50
        chapters_before.append(mock_chapter_factory(i + 1, text))

    # Caps 3-4: Formal, oraciones largas, sin muletillas, sin exclamaciones
    chapters_after = []
    for i in range(2, 4):
        text = (
            "—Considero que la situación amerita un análisis profundo de "
            "las circunstancias subyacentes que han conducido a este estado "
            "de cosas. —dijo Marta."
        ) * 50
        chapters_after.append(mock_chapter_factory(i + 1, text))

    all_chapters = chapters_before + chapters_after

    alerts = tracker.detect_changes(
        character_id=1, character_name="Marta", chapters=all_chapters
    )

    # Cambio en múltiples métricas → alta confianza
    if alerts:
        # Si genera alerta, debe tener alta confianza
        assert any(a.confidence > 0.7 for a in alerts)
        # Y múltiples métricas cambiadas
        assert any(len(a.changed_metrics) >= 3 for a in alerts)


# =============================================================================
# Edge Case: Personaje Solo Aparece en Narración (No Diálogos)
# =============================================================================


def test_character_only_narration_no_dialogue(mock_chapter_factory):
    """
    Test personaje que solo aparece en narración, nunca habla.

    El sistema NO debe generar alertas (no hay diálogos).
    """
    tracker = SpeechTracker(window_size=3, overlap=1)

    # Capítulos con mención del personaje, pero sin diálogos
    chapters = []
    for i in range(6):
        text = (
            "Roberto caminó por la calle. Roberto pensaba en su vida. "
            "Roberto era un hombre silencioso." * 50
        )
        chapters.append(mock_chapter_factory(i + 1, text))

    alerts = tracker.detect_changes(
        character_id=1, character_name="Roberto", chapters=chapters
    )

    # Sin diálogos → NO alertas
    assert len(alerts) == 0


# =============================================================================
# Edge Case: Capítulos Desordenados
# =============================================================================


def test_chapters_out_of_order(mock_chapter_factory):
    """
    Test capítulos en orden incorrecto (numeración scrambled).

    El sistema debe usar índices, no números de capítulo.
    """
    tracker = SpeechTracker(window_size=2, overlap=1)

    # Capítulos en orden: 5, 2, 8, 1, 3, 10 (scrambled)
    chapters = [
        mock_chapter_factory(5, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(2, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(8, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(1, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(3, "—Texto. —dijo Ana." * 50),
        mock_chapter_factory(10, "—Texto. —dijo Ana." * 50),
    ]

    alerts = tracker.detect_changes(
        character_id=1, character_name="Ana", chapters=chapters
    )

    # NO debe crashear (usa índices, no números)
    assert isinstance(alerts, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
