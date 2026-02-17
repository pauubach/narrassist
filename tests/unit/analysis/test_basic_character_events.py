"""
Tests para detectores de eventos básicos de personajes.

Valida detección de:
- FIRST_APPEARANCE: Primera aparición de personaje
- RETURN: Retorno de personaje ausente
- DEATH: Muerte de personaje
- POWER_SHIFT: Cambio en balance de poder
- CHAPTER_START: Inicio de capítulo
- CHAPTER_END: Fin de capítulo
"""

import pytest

from narrative_assistant.analysis.event_detection_tier2 import (
    BasicCharacterEventsDetector,
    ChapterBoundaryDetector,
    PowerShiftDetector,
)
from narrative_assistant.analysis.event_types import EventType


class TestBasicCharacterEventsDetector:
    """Tests para detector de eventos básicos de personajes."""

    @pytest.fixture
    def detector(self):
        return BasicCharacterEventsDetector()

    @pytest.fixture
    def nlp(self, shared_spacy_nlp):
        """Usa el modelo spaCy compartido."""
        return shared_spacy_nlp

    def test_detect_death_by_verb(self, detector, nlp):
        """Detecta muerte usando verbos clave."""
        text = "Pedro murió en el hospital tras días de agonía."
        doc = nlp(text)

        events = detector.detect(doc, text)
        deaths = [e for e in events if e.event_type == EventType.DEATH]

        assert len(deaths) > 0
        assert deaths[0].confidence >= 0.7
        assert "Pedro" in deaths[0].description or "murió" in deaths[0].description.lower()

    def test_detect_death_by_pattern(self, detector, nlp):
        """Detecta muerte usando patrones regex."""
        text = "Lamentablemente, su muerte fue inevitable."
        doc = nlp(text)

        events = detector.detect(doc, text)
        deaths = [e for e in events if e.event_type == EventType.DEATH]

        assert len(deaths) > 0

    def test_detect_return(self, detector, nlp):
        """Detecta retorno de personaje."""
        text = "Tras años de ausencia, María volvió al pueblo."
        doc = nlp(text)

        events = detector.detect(doc, text)
        returns = [e for e in events if e.event_type == EventType.RETURN]

        assert len(returns) > 0
        assert returns[0].confidence >= 0.6
        assert "volvió" in returns[0].description.lower()

    def test_detect_first_appearance(self, detector, nlp):
        """Detecta primera aparición de personaje."""
        text = "Conoce a Roberto, un nuevo personaje en la historia."
        doc = nlp(text)

        events = detector.detect(doc, text)
        appearances = [e for e in events if e.event_type == EventType.FIRST_APPEARANCE]

        assert len(appearances) > 0
        assert appearances[0].confidence >= 0.5

    def test_multiple_deaths_different_patterns(self, detector, nlp):
        """Detecta múltiples muertes con diferentes patrones."""
        text = """
        Juan murió en la batalla. Poco después, María falleció de tristeza.
        La muerte de ambos marcó el final de la era.
        """
        doc = nlp(text)

        events = detector.detect(doc, text)
        deaths = [e for e in events if e.event_type == EventType.DEATH]

        # Debe detectar al menos 2 muertes (Juan y María)
        assert len(deaths) >= 2

    def test_no_false_positives_for_death(self, detector, nlp):
        """No detecta muerte en contextos no relacionados."""
        text = "La muerte del verano dio paso al otoño."
        doc = nlp(text)

        events = detector.detect(doc, text)
        deaths = [e for e in events if e.event_type == EventType.DEATH]

        # Puede detectar por el patrón "muerte", pero con baja confianza
        # O no detectar si el contexto es claro
        # Este test verifica que no haya muchos falsos positivos
        assert len(deaths) <= 1


class TestPowerShiftDetector:
    """Tests para detector de cambios de poder."""

    @pytest.fixture
    def detector(self):
        return PowerShiftDetector()

    def test_detect_power_takeover(self, detector):
        """Detecta toma de poder."""
        text = "El general tomó el control del ejército tras el golpe."

        events = detector.detect(text)
        power_shifts = [e for e in events if e.event_type == EventType.POWER_SHIFT]

        assert len(power_shifts) > 0
        assert power_shifts[0].confidence >= 0.7
        assert "control" in power_shifts[0].description.lower()

    def test_detect_dethronement(self, detector):
        """Detecta derrocamiento."""
        text = "Los rebeldes derrocaron al tirano y lo expulsaron del palacio."

        events = detector.detect(text)
        power_shifts = [e for e in events if e.event_type == EventType.POWER_SHIFT]

        assert len(power_shifts) > 0
        assert "derrocaron" in power_shifts[0].description.lower()

    def test_detect_new_leader(self, detector):
        """Detecta nuevo líder."""
        text = "Ana se convirtió en la nueva reina tras la coronación."

        events = detector.detect(text)
        power_shifts = [e for e in events if e.event_type == EventType.POWER_SHIFT]

        assert len(power_shifts) > 0

    def test_detect_power_loss(self, detector):
        """Detecta pérdida de poder."""
        text = "El emperador perdió el poder tras la revolución."

        events = detector.detect(text)
        power_shifts = [e for e in events if e.event_type == EventType.POWER_SHIFT]

        assert len(power_shifts) > 0

    def test_no_power_shift_in_normal_text(self, detector):
        """No detecta cambio de poder en texto normal."""
        text = "Caminaron por el parque disfrutando del día."

        events = detector.detect(text)
        power_shifts = [e for e in events if e.event_type == EventType.POWER_SHIFT]

        assert len(power_shifts) == 0


class TestChapterBoundaryDetector:
    """Tests para detector de inicio y fin de capítulo."""

    @pytest.fixture
    def detector(self):
        return ChapterBoundaryDetector()

    def test_detect_chapter_start_numbered(self, detector):
        """Detecta inicio de capítulo numerado."""
        text = "Capítulo 5\n\nLa mañana amaneció fría y gris."

        events = detector.detect(text)
        starts = [e for e in events if e.event_type == EventType.CHAPTER_START]

        assert len(starts) == 1
        assert starts[0].confidence >= 0.9

    def test_detect_chapter_start_roman(self, detector):
        """Detecta inicio de capítulo con numeración romana."""
        text = "CAPÍTULO III\n\nEn aquel entonces..."

        events = detector.detect(text)
        starts = [e for e in events if e.event_type == EventType.CHAPTER_START]

        assert len(starts) == 1

    def test_detect_chapter_end_explicit(self, detector):
        """Detecta fin de capítulo explícito."""
        text = "Y así terminó todo.\n\nFin del capítulo"

        events = detector.detect(text)
        ends = [e for e in events if e.event_type == EventType.CHAPTER_END]

        assert len(ends) == 1
        assert ends[0].confidence >= 0.85

    def test_detect_chapter_end_continuara(self, detector):
        """Detecta fin con 'Continuará'."""
        text = "El misterio quedó sin resolver.\n\nContinuará..."

        events = detector.detect(text)
        ends = [e for e in events if e.event_type == EventType.CHAPTER_END]

        assert len(ends) == 1

    def test_no_chapter_boundaries_in_middle(self, detector):
        """No detecta boundaries en medio del texto."""
        text = "Era un día normal. El sol brillaba. Capítulo importante de la vida."

        events = detector.detect(text)

        # No debe detectar "Capítulo importante" como inicio
        # porque no está al principio del texto
        starts = [e for e in events if e.event_type == EventType.CHAPTER_START]
        assert len(starts) == 0


class TestIntegrationWithTier2:
    """Tests de integración con detect_tier2_events."""

    @pytest.fixture
    def nlp(self, shared_spacy_nlp):
        return shared_spacy_nlp

    def test_all_new_events_integrated(self, nlp):
        """Verifica que los 6 nuevos eventos se detectan en tier2."""
        from narrative_assistant.analysis.event_detection_tier2 import detect_tier2_events

        text = """
        Capítulo 1

        Conoce a Pedro, un nuevo personaje. El rey murió ayer.
        Juan tomó el control del reino. María volvió tras años de ausencia.

        Fin del capítulo
        """

        doc = nlp(text)
        events = detect_tier2_events(doc, text)

        event_types = {e.event_type for e in events}

        # Verificar que detecta al menos algunos de los 6 nuevos tipos
        new_types = {
            EventType.CHAPTER_START,
            EventType.CHAPTER_END,
            EventType.FIRST_APPEARANCE,
            EventType.DEATH,
            EventType.POWER_SHIFT,
            EventType.RETURN,
        }

        detected_new = event_types & new_types
        assert len(detected_new) >= 3, f"Solo detectó {detected_new}"

    def test_no_duplicates_from_multiple_detectors(self, nlp):
        """Verifica que no hay duplicados innecesarios."""
        from narrative_assistant.analysis.event_detection_tier2 import detect_tier2_events

        text = "Pedro murió en la batalla."
        doc = nlp(text)
        events = detect_tier2_events(doc, text)

        # Puede haber múltiples detecciones del mismo evento
        # (verbo + patrón), pero deben tener posiciones similares
        deaths = [e for e in events if e.event_type == EventType.DEATH]

        if len(deaths) > 1:
            # Verificar que las posiciones son similares (mismo contexto)
            positions = [e.start_char for e in deaths]
            # Todos deben estar en un rango de 50 caracteres
            assert max(positions) - min(positions) < 50
