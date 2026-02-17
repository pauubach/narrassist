"""
Tests para detección de eventos narrativos.

Valida detectores de Tier 1 (alta prioridad).
"""

import pytest

from narrative_assistant.analysis.event_detection import (
    ConfessionLieDetector,
    DreamSequenceDetector,
    EventDetector,
    FlashbackDetector,
    HealingDetector,
    InjuryDetector,
    NarrativeIntrusionDetector,
    POVChangeDetector,
    PromiseDetector,
    TimeSkipDetector,
)
from narrative_assistant.analysis.event_types import EventType


class TestPromiseDetector:
    """Tests para detector de promesas."""

    @pytest.fixture
    def detector(self):
        return PromiseDetector()

    def test_detect_explicit_promise(self, detector, shared_spacy_nlp):
        """Detecta promesa explícita con verbo."""
        text = "Juan prometió volver antes del anochecer."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert events[0].event_type == EventType.PROMISE
        assert "prometió" in events[0].description.lower()
        assert events[0].confidence > 0.5

    def test_detect_promise_pattern(self, detector, shared_spacy_nlp):
        """Detecta promesa con patrón 'te prometo'."""
        text = "Te prometo que volveré sano y salvo."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert any(e.event_type == EventType.PROMISE for e in events)

    def test_extract_promise_complement(self, detector, shared_spacy_nlp):
        """Extrae correctamente qué se promete."""
        text = "María juró proteger a su hermano."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        event = events[0]
        assert event.metadata.get("promise_text") is not None


class TestInjuryDetector:
    """Tests para detector de heridas."""

    @pytest.fixture
    def detector(self):
        return InjuryDetector()

    def test_detect_injury_with_body_part(self, detector, shared_spacy_nlp):
        """Detecta herida con parte del cuerpo."""
        text = "Le atravesaron el hombro con una flecha."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        event = events[0]
        assert event.event_type == EventType.INJURY
        assert event.metadata.get("body_part") == "hombro"

    def test_injury_severity_grave(self, detector, shared_spacy_nlp):
        """Heridas graves se marcan como tal."""
        text = "Le fracturaron la pierna en dos partes."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        event = events[0]
        assert event.metadata.get("severity") == "grave"

    def test_injury_severity_leve(self, detector, shared_spacy_nlp):
        """Heridas leves se marcan como tal."""
        text = "Se lastimó la mano al caer."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        event = events[0]
        assert event.metadata.get("severity") == "leve"


class TestFlashbackDetector:
    """Tests para detector de flashbacks."""

    @pytest.fixture
    def detector(self):
        return FlashbackDetector()

    def test_detect_flashback_start(self, detector):
        """Detecta inicio de flashback."""
        text = "Recordó aquel día de verano, años atrás, cuando era niño."

        events = detector.detect(text)

        starts = [e for e in events if e.event_type == EventType.FLASHBACK_START]
        assert len(starts) > 0

    def test_detect_flashback_end(self, detector):
        """Detecta fin de flashback."""
        text = "Volvió al presente, sacudiendo la cabeza."

        events = detector.detect(text)

        ends = [e for e in events if e.event_type == EventType.FLASHBACK_END]
        assert len(ends) > 0


class TestTimeSkipDetector:
    """Tests para detector de saltos temporales."""

    @pytest.fixture
    def detector(self):
        return TimeSkipDetector()

    def test_detect_time_skip_with_duration(self, detector):
        """Detecta salto temporal con duración."""
        text = "Tres años después, todo había cambiado."

        events = detector.detect(text)

        assert len(events) > 0
        event = events[0]
        assert event.event_type == EventType.TIME_SKIP
        assert event.metadata.get("duration") is not None

    def test_detect_next_day_skip(self, detector):
        """Detecta salto 'al día siguiente'."""
        text = "Al día siguiente, despertó con un plan."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.TIME_SKIP


class TestConfessionLieDetector:
    """Tests para detector de confesiones y mentiras."""

    @pytest.fixture
    def detector(self):
        return ConfessionLieDetector()

    def test_detect_confession(self, detector, shared_spacy_nlp):
        """Detecta confesión."""
        text = "Juan confesó que había robado el dinero."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert events[0].event_type == EventType.CONFESSION

    def test_detect_lie(self, detector, shared_spacy_nlp):
        """Detecta mentira."""
        text = "María mintió sobre su paradero."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert events[0].event_type == EventType.LIE


class TestHealingDetector:
    """Tests para detector de curaciones."""

    @pytest.fixture
    def detector(self):
        return HealingDetector()

    def test_detect_healing(self, detector, shared_spacy_nlp):
        """Detecta curación."""
        text = "Pedro se curó de la herida en el brazo."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert events[0].event_type == EventType.HEALING
        assert events[0].metadata.get("body_part") == "brazo"


class TestDreamSequenceDetector:
    """Tests para detector de sueños."""

    @pytest.fixture
    def detector(self):
        return DreamSequenceDetector()

    def test_detect_dream(self, detector):
        """Detecta secuencia onírica."""
        text = "Esa noche soñó con campos de flores."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.DREAM_SEQUENCE


class TestPOVChangeDetector:
    """Tests para detector de cambios de POV."""

    @pytest.fixture
    def detector(self):
        return POVChangeDetector()

    def test_detect_pov_change_first_to_third(self, detector):
        """Detecta cambio de primera a tercera persona."""
        prev_text = "Yo caminaba por la calle. Me sentía cansado."
        current_text = "Él llegó a casa. Ella lo esperaba."

        events = detector.detect(current_text, prev_text)

        assert len(events) > 0
        assert events[0].event_type == EventType.POV_CHANGE
        assert events[0].metadata.get("previous_pov") == "first_person"
        assert events[0].metadata.get("current_pov") == "third_person"

    def test_no_pov_change(self, detector):
        """No detecta cambio si POV es el mismo."""
        prev_text = "Él caminaba. Ella hablaba."
        current_text = "Él llegó. Ella esperaba."

        events = detector.detect(current_text, prev_text)

        assert len(events) == 0


class TestNarrativeIntrusionDetector:
    """Tests para detector de intrusiones narrativas."""

    @pytest.fixture
    def detector(self):
        return NarrativeIntrusionDetector()

    def test_detect_narrative_intrusion(self, detector):
        """Detecta intrusión del narrador."""
        text = "Querido lector, debo advertirte que lo que sigue es terrible."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.NARRATIVE_INTRUSION


class TestEventDetector:
    """Tests para detector principal (orquestador)."""

    @pytest.fixture
    def detector(self, shared_spacy_nlp):
        return EventDetector(nlp=shared_spacy_nlp, enable_llm=False)

    def test_detect_multiple_event_types(self, detector):
        """Detecta múltiples tipos de eventos en un texto."""
        text = """
        Juan prometió volver. Tres días después, llegó herido.
        Le atravesaron el brazo durante la batalla.
        """

        events = detector.detect_events(text, chapter_number=1)

        # Debe detectar: PROMISE, TIME_SKIP, INJURY
        event_types = {e.event_type for e in events}
        assert EventType.PROMISE in event_types
        assert EventType.TIME_SKIP in event_types
        assert EventType.INJURY in event_types

    def test_events_ordered_by_position(self, detector):
        """Los eventos se devuelven ordenados por posición."""
        text = "Primero prometió algo. Luego se lastimó el brazo."

        events = detector.detect_events(text, chapter_number=1)

        # Verificar que están ordenados
        positions = [e.start_char for e in events]
        assert positions == sorted(positions)

    def test_no_duplicate_events(self, detector):
        """No genera eventos duplicados en la misma posición."""
        text = "Te prometo que volveré."

        events = detector.detect_events(text, chapter_number=1)

        # Puede haber múltiples detecciones del mismo tipo, pero no en posición idéntica
        positions = [(e.event_type, e.start_char, e.end_char) for e in events]
        assert len(positions) == len(set(positions))
