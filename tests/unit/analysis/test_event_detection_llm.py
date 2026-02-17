"""
Tests para detectores de eventos LLM (Tier 1).

Valida detección de eventos complejos usando Ollama:
- BETRAYAL: Traiciones
- ALLIANCE: Formación de alianzas
- REVELATION: Revelaciones importantes
- DECISION: Decisiones cruciales

Usa mocks para no depender de Ollama en tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.analysis.event_detection_llm import (
    AllianceDetector,
    BetrayalDetector,
    DecisionDetector,
    RevelationDetector,
    detect_llm_tier1_events,
)
from narrative_assistant.analysis.event_types import EventType


class TestBetrayalDetector:
    """Tests para detector de traiciones."""

    @pytest.fixture
    def detector(self):
        """Crea detector con Ollama mockeado."""
        detector = BetrayalDetector()
        detector.ollama_available = True
        return detector

    def test_detect_betrayal_with_mock(self, detector):
        """Detecta traición con respuesta mockeada."""
        text = "Marcus reveló el secreto de Ana a sus enemigos, traicionando su confianza."

        # Mock de respuesta de Ollama
        mock_response = """{
            "has_betrayal": true,
            "description": "Marcus traiciona a Ana revelando su secreto",
            "confidence": 0.85,
            "betrayer": "Marcus",
            "victim": "Ana"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.BETRAYAL
        assert event.confidence >= 0.8
        assert event.metadata["betrayer"] == "Marcus"
        assert event.metadata["victim"] == "Ana"

    def test_no_betrayal_detected(self, detector):
        """No detecta traición cuando no la hay."""
        text = "Juan y María trabajaron juntos en el proyecto con éxito."

        mock_response = """{
            "has_betrayal": false,
            "description": "",
            "confidence": 0.0,
            "betrayer": "",
            "victim": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0

    def test_low_confidence_filtered(self, detector):
        """Filtra eventos con confianza < 0.5."""
        text = "Algo pasó entre ellos."

        mock_response = """{
            "has_betrayal": true,
            "description": "Posible traición",
            "confidence": 0.3,
            "betrayer": "",
            "victim": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0

    def test_ollama_unavailable(self):
        """No detecta nada si Ollama no está disponible."""
        detector = BetrayalDetector()
        detector.ollama_available = False

        text = "Marcus traicionó a Ana completamente."
        events = detector.detect(text)

        assert len(events) == 0


class TestAllianceDetector:
    """Tests para detector de alianzas."""

    @pytest.fixture
    def detector(self):
        detector = AllianceDetector()
        detector.ollama_available = True
        return detector

    def test_detect_alliance_with_mock(self, detector):
        """Detecta formación de alianza."""
        text = "Los reinos del norte y del sur acordaron unir fuerzas contra el enemigo común."

        mock_response = """{
            "has_alliance": true,
            "description": "Alianza entre reinos del norte y sur",
            "confidence": 0.9,
            "members": ["reino norte", "reino sur"]
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.ALLIANCE
        assert event.confidence >= 0.8
        assert len(event.metadata["members"]) == 2

    def test_no_alliance_detected(self, detector):
        """No detecta alianza cuando no la hay."""
        text = "Cada reino siguió su propio camino sin cooperar."

        mock_response = """{
            "has_alliance": false,
            "description": "",
            "confidence": 0.0,
            "members": []
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0


class TestRevelationDetector:
    """Tests para detector de revelaciones."""

    @pytest.fixture
    def detector(self):
        detector = RevelationDetector()
        detector.ollama_available = True
        return detector

    def test_detect_revelation_with_mock(self, detector):
        """Detecta revelación importante."""
        text = "Elena confesó que ella era la verdadera heredera del trono, no su hermano."

        mock_response = """{
            "has_revelation": true,
            "description": "Elena revela que es la heredera legítima",
            "confidence": 0.88,
            "revealer": "Elena",
            "content": "verdadera heredera del trono"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.REVELATION
        assert event.confidence >= 0.8
        assert event.metadata["revealer"] == "Elena"

    def test_no_revelation_detected(self, detector):
        """No detecta revelación cuando no la hay."""
        text = "Hablaron sobre el clima durante el almuerzo."

        mock_response = """{
            "has_revelation": false,
            "description": "",
            "confidence": 0.0,
            "revealer": "",
            "content": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0


class TestDecisionDetector:
    """Tests para detector de decisiones cruciales."""

    @pytest.fixture
    def detector(self):
        detector = DecisionDetector()
        detector.ollama_available = True
        return detector

    def test_detect_decision_with_mock(self, detector):
        """Detecta decisión crucial."""
        text = "Tras días de deliberación, Carlos decidió aceptar la oferta y cambiar de bando."

        mock_response = """{
            "has_decision": true,
            "description": "Carlos decide cambiar de bando",
            "confidence": 0.82,
            "decision_maker": "Carlos",
            "choice": "aceptar oferta y cambiar de bando"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.DECISION
        assert event.confidence >= 0.8
        assert event.metadata["decision_maker"] == "Carlos"

    def test_no_decision_detected(self, detector):
        """No detecta decisión cuando no la hay."""
        text = "Pasaron el día sin hacer nada en particular."

        mock_response = """{
            "has_decision": false,
            "description": "",
            "confidence": 0.0,
            "decision_maker": "",
            "choice": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0


class TestLLMIntegration:
    """Tests de integración para función helper."""

    def test_detect_llm_tier1_events_without_ollama(self):
        """Sin Ollama, no detecta eventos LLM."""
        text = "Hubo traiciones, alianzas y revelaciones importantes."

        # Mock para que todos los detectores digan que Ollama no está disponible
        with patch('narrative_assistant.analysis.event_detection_llm.BetrayalDetector') as MockBetrayal, \
             patch('narrative_assistant.analysis.event_detection_llm.AllianceDetector') as MockAlliance, \
             patch('narrative_assistant.analysis.event_detection_llm.RevelationDetector') as MockRevelation, \
             patch('narrative_assistant.analysis.event_detection_llm.DecisionDetector') as MockDecision:

            # Configurar mocks para devolver listas vacías
            for mock_class in [MockBetrayal, MockAlliance, MockRevelation, MockDecision]:
                mock_instance = MagicMock()
                mock_instance.detect.return_value = []
                mock_class.return_value = mock_instance

            events = detect_llm_tier1_events(text)

            assert len(events) == 0

    def test_detect_multiple_llm_events(self):
        """Detecta múltiples tipos de eventos LLM."""
        text = """
        Marcus traicionó a Elena revelando sus secretos.
        Luego, los tres reinos formaron una alianza.
        Elena decidió perdonar a Marcus tras la revelación de que trabajaba como espía.
        """

        # Mock de todos los detectores
        with patch('narrative_assistant.analysis.event_detection_llm.BetrayalDetector') as MockBetrayal, \
             patch('narrative_assistant.analysis.event_detection_llm.AllianceDetector') as MockAlliance, \
             patch('narrative_assistant.analysis.event_detection_llm.RevelationDetector') as MockRevelation, \
             patch('narrative_assistant.analysis.event_detection_llm.DecisionDetector') as MockDecision:

            from narrative_assistant.analysis.event_detection import DetectedEvent

            # Configurar respuestas mock
            betrayal_event = DetectedEvent(
                event_type=EventType.BETRAYAL,
                description="Marcus traiciona a Elena",
                confidence=0.85,
                start_char=0,
                end_char=50,
                metadata={}
            )

            alliance_event = DetectedEvent(
                event_type=EventType.ALLIANCE,
                description="Alianza de tres reinos",
                confidence=0.9,
                start_char=60,
                end_char=100,
                metadata={}
            )

            revelation_event = DetectedEvent(
                event_type=EventType.REVELATION,
                description="Revelación de Marcus como espía",
                confidence=0.8,
                start_char=120,
                end_char=180,
                metadata={}
            )

            decision_event = DetectedEvent(
                event_type=EventType.DECISION,
                description="Elena decide perdonar",
                confidence=0.75,
                start_char=120,
                end_char=160,
                metadata={}
            )

            MockBetrayal.return_value.detect.return_value = [betrayal_event]
            MockAlliance.return_value.detect.return_value = [alliance_event]
            MockRevelation.return_value.detect.return_value = [revelation_event]
            MockDecision.return_value.detect.return_value = [decision_event]

            events = detect_llm_tier1_events(text)

            # Debería detectar los 4 tipos
            assert len(events) == 4
            event_types = {e.event_type for e in events}
            assert EventType.BETRAYAL in event_types
            assert EventType.ALLIANCE in event_types
            assert EventType.REVELATION in event_types
            assert EventType.DECISION in event_types


class TestJSONExtraction:
    """Tests para extracción de JSON de respuestas LLM."""

    def test_extract_valid_json(self):
        """Extrae JSON válido de respuesta."""
        detector = BetrayalDetector()

        response = '{"has_betrayal": true, "confidence": 0.8}'
        data = detector._extract_json(response)

        assert data["has_betrayal"] is True
        assert data["confidence"] == 0.8

    def test_extract_json_with_surrounding_text(self):
        """Extrae JSON de respuesta con texto adicional."""
        detector = BetrayalDetector()

        response = 'Aquí está el análisis: {"has_betrayal": true, "confidence": 0.75} Fin del análisis.'
        data = detector._extract_json(response)

        assert data["has_betrayal"] is True
        assert data["confidence"] == 0.75

    def test_extract_invalid_json_returns_empty(self):
        """Devuelve diccionario vacío si no puede parsear JSON."""
        detector = BetrayalDetector()

        response = 'No hay JSON válido aquí'
        data = detector._extract_json(response)

        assert data == {}
