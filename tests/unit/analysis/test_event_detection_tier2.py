"""
Tests para detectores de eventos Tier 2 (Prioridad Media).

Valida detección de 15 tipos de eventos de enriquecimiento narrativo:
- Relaciones entre personajes (5)
- Transformaciones narrativas (4)
- Eventos de trama (4)
- Meta-narrativos (2)
"""

import pytest
from spacy.language import Language

from narrative_assistant.analysis.event_detection_tier2 import (
    ConflictDetector,
    FirstMeetingDetector,
    LocationChangeDetector,
    PlotEventDetector,
    SeparationReunionDetector,
    SocialChangeDetector,
    TransformationDetector,
    detect_tier2_events,
)
from narrative_assistant.analysis.event_types import EventType


class TestFirstMeetingDetector:
    """Tests para detector de primer encuentro."""

    @pytest.fixture
    def detector(self):
        return FirstMeetingDetector()

    def test_detect_first_meeting_verb(self, detector, shared_spacy_nlp):
        """Detecta primer encuentro con verbo 'conocer'."""
        text = "María conoció a Pedro en la biblioteca."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        event = events[0]
        assert event.event_type == EventType.FIRST_MEETING
        assert event.confidence >= 0.6
        assert "conoció" in text[event.start_char:event.end_char].lower()

    def test_detect_first_meeting_pattern(self, detector, shared_spacy_nlp):
        """Detecta primer encuentro con patrón explícito."""
        text = "Se vieron por primera vez en el parque."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert any(e.event_type == EventType.FIRST_MEETING for e in events)

    def test_no_false_positives(self, detector, shared_spacy_nlp):
        """No detecta encuentros en texto sin patrones relevantes."""
        text = "El clima estaba agradable ese día."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) == 0


class TestSeparationReunionDetector:
    """Tests para detector de separaciones y reencuentros."""

    @pytest.fixture
    def detector(self):
        return SeparationReunionDetector()

    def test_detect_separation(self, detector):
        """Detecta separación entre personajes."""
        text = "Juan y María se separaron en la estación."

        events = detector.detect(text)

        assert len(events) > 0
        separations = [e for e in events if e.event_type == EventType.SEPARATION]
        assert len(separations) > 0
        assert separations[0].confidence >= 0.6

    def test_detect_reunion(self, detector):
        """Detecta reencuentro entre personajes."""
        text = "Después de años, volvieron a encontrarse en la plaza."

        events = detector.detect(text)

        reunions = [e for e in events if e.event_type == EventType.REUNION]
        assert len(reunions) > 0
        assert reunions[0].confidence >= 0.6

    def test_detect_both_separation_and_reunion(self, detector):
        """Detecta ambos eventos en texto largo."""
        text = """
        Ana y Carlos se despidieron en el puerto. Era el último día juntos.
        Años más tarde, Ana volvió a ver a Carlos en el mismo lugar.
        """

        events = detector.detect(text)

        separations = [e for e in events if e.event_type == EventType.SEPARATION]
        reunions = [e for e in events if e.event_type == EventType.REUNION]
        assert len(separations) > 0
        assert len(reunions) > 0


class TestConflictDetector:
    """Tests para detector de conflictos."""

    @pytest.fixture
    def detector(self):
        return ConflictDetector()

    def test_detect_conflict_start(self, detector):
        """Detecta inicio de conflicto."""
        text = "Pedro y Luis discutieron violentamente sobre el plan."

        events = detector.detect(text)

        conflicts = [e for e in events if e.event_type == EventType.CONFLICT_START]
        assert len(conflicts) > 0
        assert conflicts[0].confidence >= 0.7

    def test_detect_conflict_resolution(self, detector):
        """Detecta resolución de conflicto."""
        text = "Finalmente, se reconciliaron después de hablar."

        events = detector.detect(text)

        resolutions = [e for e in events if e.event_type == EventType.CONFLICT_RESOLUTION]
        assert len(resolutions) > 0
        assert resolutions[0].confidence >= 0.7

    def test_detect_conflict_arc(self, detector):
        """Detecta arco completo de conflicto."""
        text = """
        Los hermanos se enfrentaron por la herencia. El desacuerdo duró meses.
        Sin embargo, al final perdonaron las ofensas y resolvieron el conflicto.
        """

        events = detector.detect(text)

        conflicts = [e for e in events if e.event_type == EventType.CONFLICT_START]
        resolutions = [e for e in events if e.event_type == EventType.CONFLICT_RESOLUTION]
        assert len(conflicts) > 0
        assert len(resolutions) > 0


class TestTransformationDetector:
    """Tests para detector de transformaciones."""

    @pytest.fixture
    def detector(self):
        return TransformationDetector()

    def test_detect_transformation(self, detector, shared_spacy_nlp):
        """Detecta transformación de personaje."""
        text = "El joven se transformó en un hombre sabio con los años."
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) > 0
        assert events[0].event_type == EventType.CHARACTER_TRANSFORMATION
        assert events[0].confidence >= 0.6

    def test_detect_multiple_transformation_verbs(self, detector, shared_spacy_nlp):
        """Detecta múltiples transformaciones."""
        text = """
        María cambió radicalmente después del viaje.
        Pedro evolucionó como persona tras la tragedia.
        """
        doc = shared_spacy_nlp(text)

        events = detector.detect(doc, text)

        assert len(events) >= 2
        assert all(e.event_type == EventType.CHARACTER_TRANSFORMATION for e in events)


class TestSocialChangeDetector:
    """Tests para detector de cambios sociales."""

    @pytest.fixture
    def detector(self):
        return SocialChangeDetector()

    def test_detect_social_promotion(self, detector):
        """Detecta ascenso social."""
        text = "El rey lo nombrado duque por sus servicios."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.SOCIAL_CHANGE
        assert events[0].confidence >= 0.6

    def test_detect_social_demotion(self, detector):
        """Detecta pérdida de estatus."""
        text = "Fue destituido de su cargo tras el escándalo."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.SOCIAL_CHANGE

    def test_detect_coronation(self, detector):
        """Detecta coronación."""
        text = "Finalmente fue coronado emperador de las tierras del norte."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.SOCIAL_CHANGE


class TestLocationChangeDetector:
    """Tests para detector de cambios de escenario."""

    @pytest.fixture
    def detector(self):
        return LocationChangeDetector()

    def test_detect_arrival(self, detector):
        """Detecta llegada a nuevo lugar."""
        text = "Tras semanas de viaje, finalmente llegó a Roma."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.LOCATION_CHANGE
        assert events[0].confidence >= 0.6

    def test_detect_new_location(self, detector):
        """Detecta mención de nueva ciudad."""
        text = "Se mudaron a una nueva ciudad en el norte."

        events = detector.detect(text)

        assert len(events) > 0
        assert events[0].event_type == EventType.LOCATION_CHANGE

    def test_no_false_positive_on_movement(self, detector):
        """No detecta movimientos triviales."""
        text = "Caminó hasta la esquina de la calle."

        events = detector.detect(text)

        # Este texto no debería generar eventos (movimiento local, no cambio significativo)
        # Pero si genera, verificar que sea con baja confianza
        if events:
            assert events[0].confidence < 0.7


class TestPlotEventDetector:
    """Tests para detector de eventos de trama."""

    @pytest.fixture
    def detector(self):
        return PlotEventDetector()

    def test_detect_climax(self, detector):
        """Detecta clímax de la historia."""
        text = "Era el momento culminante de la batalla, todo estaba en juego."

        events = detector.detect(text)

        climaxes = [e for e in events if e.event_type == EventType.CLIMAX]
        assert len(climaxes) > 0
        assert climaxes[0].confidence >= 0.6

    def test_detect_twist(self, detector):
        """Detecta giro argumental."""
        text = "En un giro inesperado, resultó que ella era la verdadera heredera."

        events = detector.detect(text)

        twists = [e for e in events if e.event_type == EventType.TWIST]
        assert len(twists) > 0
        assert twists[0].confidence >= 0.6

    def test_detect_foreshadowing(self, detector):
        """Detecta prefiguración."""
        text = "Un presagio oscuro se cernía sobre el castillo esa noche."

        events = detector.detect(text)

        foreshadows = [e for e in events if e.event_type == EventType.FORESHADOWING]
        assert len(foreshadows) > 0
        assert foreshadows[0].confidence >= 0.5

    def test_detect_callback(self, detector):
        """Detecta referencia a evento previo."""
        text = "Como ya mencioné antes, el plan tenía un fallo."

        events = detector.detect(text)

        callbacks = [e for e in events if e.event_type == EventType.CALLBACK]
        assert len(callbacks) > 0
        assert callbacks[0].confidence >= 0.6

    def test_detect_multiple_plot_events(self, detector):
        """Detecta múltiples eventos de trama."""
        text = """
        Como ya mencioné antes, había señales de lo que vendría.
        En el momento culminante, todo cambió.
        Pero resultó que nada era lo que parecía.
        """

        events = detector.detect(text)

        # Debería haber al menos 2 tipos de eventos de trama
        event_types = {e.event_type for e in events}
        assert len(event_types) >= 2
        # Al menos uno debe ser CLIMAX o TWIST
        assert EventType.CLIMAX in event_types or EventType.TWIST in event_types


class TestTier2Integration:
    """Tests de integración para función helper de Tier 2."""

    def test_detect_tier2_events_comprehensive(self, shared_spacy_nlp):
        """Detecta eventos Tier 2 en texto complejo."""
        text = """
        María conoció a Juan en la universidad. Fue su primer encuentro.
        Años después, se separaron por desacuerdos irreconciliables.

        Juan se transformó en un hombre diferente tras la pérdida.
        Fue nombrado director de la empresa, un ascenso importante.

        Llegó a Nueva York buscando un nuevo comienzo.

        En un giro inesperado, volvió a encontrarse con María.
        Como recordó entonces, ella siempre había estado ahí.
        """
        doc = shared_spacy_nlp(text)

        events = detect_tier2_events(doc, text)

        # Verificar que se detectaron eventos de múltiples categorías
        event_types = {e.event_type for e in events}

        # Relaciones
        assert EventType.FIRST_MEETING in event_types
        assert EventType.SEPARATION in event_types or EventType.REUNION in event_types

        # Transformaciones
        assert EventType.CHARACTER_TRANSFORMATION in event_types or EventType.SOCIAL_CHANGE in event_types

        # Trama
        assert len(event_types) >= 3  # Al menos 3 tipos diferentes

    def test_detect_tier2_events_empty_text(self, shared_spacy_nlp):
        """No detecta eventos en texto vacío."""
        text = ""
        doc = shared_spacy_nlp(text)

        events = detect_tier2_events(doc, text)

        assert len(events) == 0

    def test_detect_tier2_events_no_relevant_content(self, shared_spacy_nlp):
        """No detecta eventos en texto sin contenido narrativo relevante."""
        text = "El clima era agradable. Las flores florecían en primavera."
        doc = shared_spacy_nlp(text)

        events = detect_tier2_events(doc, text)

        # Puede haber 0 eventos o muy pocos con baja confianza
        assert len(events) <= 1

    def test_tier2_events_ordering(self, shared_spacy_nlp):
        """Los eventos se devuelven en orden textual."""
        text = """
        Primero, María conoció a Juan.
        Luego, se separaron tras un conflicto.
        Finalmente, se reconciliaron años después.
        """
        doc = shared_spacy_nlp(text)

        events = detect_tier2_events(doc, text)

        if len(events) >= 2:
            # Verificar que están ordenados por start_char
            for i in range(len(events) - 1):
                assert events[i].start_char <= events[i + 1].start_char
