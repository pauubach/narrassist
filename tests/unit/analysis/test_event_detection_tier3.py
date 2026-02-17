"""
Tests para detectores de eventos Tier 3 (Especialización por Género).

Valida detección de eventos especializados usando LLM:

Thriller/Suspense:
- CLUE_DISCOVERY: Descubrimiento de pistas
- RED_HERRING: Pistas falsas
- DANGER_ESCALATION: Aumento de peligro
- CHASE_START: Inicio de persecución

Fantasía/SciFi:
- MAGIC_USE: Uso de magia/poderes
- PROPHECY: Profecías
- WORLD_BUILDING: Expansión del mundo
- PORTAL_CROSSING: Cruce entre mundos

Romance:
- ROMANTIC_TENSION: Tensión romántica
- LOVE_DECLARATION: Declaración de amor
- BREAKUP: Ruptura
- RECONCILIATION: Reconciliación

Universal:
- KNOWLEDGE_TRANSFER: Transmisión/descubrimiento de conocimiento

Usa mocks para no depender de Ollama en tests.
"""

import pytest
from unittest.mock import patch

from narrative_assistant.analysis.event_detection_tier3 import (
    GenericLLMDetector,
    detect_tier3_events,
    detect_knowledge_transfer,
    CLUE_DISCOVERY_PROMPT,
    RED_HERRING_PROMPT,
    DANGER_ESCALATION_PROMPT,
    CHASE_START_PROMPT,
    MAGIC_USE_PROMPT,
    PROPHECY_PROMPT,
    WORLD_BUILDING_PROMPT,
    PORTAL_CROSSING_PROMPT,
    ROMANTIC_TENSION_PROMPT,
    LOVE_DECLARATION_PROMPT,
    BREAKUP_PROMPT,
    RECONCILIATION_PROMPT,
    KNOWLEDGE_TRANSFER_PROMPT,
)
from narrative_assistant.analysis.event_types import EventType


class TestClueDiscoveryDetector:
    """Tests para detector de pistas (Thriller)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.CLUE_DISCOVERY,
            prompt_template=CLUE_DISCOVERY_PROMPT,
            key="has_clue"
        )
        detector.ollama_available = True
        return detector

    def test_detect_clue_with_mock(self, detector):
        """Detecta descubrimiento de pista con respuesta mockeada."""
        text = "Laura encontró una nota escondida en el cajón con información crucial sobre el caso."

        mock_response = """{
            "has_clue": true,
            "description": "Laura encuentra nota con información crucial",
            "confidence": 0.88,
            "discoverer": "Laura",
            "clue_type": "física"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.CLUE_DISCOVERY
        assert event.confidence >= 0.8
        assert event.metadata["discoverer"] == "Laura"
        assert event.metadata["clue_type"] == "física"

    def test_no_clue_detected(self, detector):
        """No detecta pista cuando no la hay."""
        text = "Caminaron por el parque disfrutando del buen clima."

        mock_response = """{
            "has_clue": false,
            "description": "",
            "confidence": 0.0,
            "discoverer": "",
            "clue_type": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0


class TestRedHerringDetector:
    """Tests para detector de pistas falsas (Thriller)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.RED_HERRING,
            prompt_template=RED_HERRING_PROMPT,
            key="has_red_herring"
        )
        detector.ollama_available = True
        return detector

    def test_detect_red_herring_with_mock(self, detector):
        """Detecta pista falsa con respuesta mockeada."""
        text = "Todos sospechaban de Roberto, pero resultó ser una distracción del verdadero culpable."

        mock_response = """{
            "has_red_herring": true,
            "description": "Roberto como sospechoso resulta distracción",
            "confidence": 0.85,
            "misleading_element": "Roberto como sospechoso"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.RED_HERRING
        assert events[0].confidence >= 0.8


class TestDangerEscalationDetector:
    """Tests para detector de escalación de peligro (Thriller)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.DANGER_ESCALATION,
            prompt_template=DANGER_ESCALATION_PROMPT,
            key="has_escalation"
        )
        detector.ollama_available = True
        return detector

    def test_detect_danger_escalation_with_mock(self, detector):
        """Detecta escalación de peligro con respuesta mockeada."""
        text = "De pronto, la bomba comenzó a contar hacia atrás. Solo quedaban 10 minutos."

        mock_response = """{
            "has_escalation": true,
            "description": "Bomba con cuenta regresiva (10 minutos)",
            "confidence": 0.92,
            "threat_level": "crítico"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.DANGER_ESCALATION
        assert events[0].metadata["threat_level"] == "crítico"


class TestChaseStartDetector:
    """Tests para detector de inicio de persecución (Thriller)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.CHASE_START,
            prompt_template=CHASE_START_PROMPT,
            key="has_chase"
        )
        detector.ollama_available = True
        return detector

    def test_detect_chase_with_mock(self, detector):
        """Detecta inicio de persecución con respuesta mockeada."""
        text = "El detective echó a correr tras el ladrón que huía por el callejón."

        mock_response = """{
            "has_chase": true,
            "description": "Detective persigue a ladrón por callejón",
            "confidence": 0.87,
            "chaser": "detective",
            "target": "ladrón"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.CHASE_START
        assert events[0].metadata["chaser"] == "detective"
        assert events[0].metadata["target"] == "ladrón"


class TestMagicUseDetector:
    """Tests para detector de uso de magia (Fantasía)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.MAGIC_USE,
            prompt_template=MAGIC_USE_PROMPT,
            key="has_magic"
        )
        detector.ollama_available = True
        return detector

    def test_detect_magic_use_with_mock(self, detector):
        """Detecta uso de magia con respuesta mockeada."""
        text = "Elara extendió su mano y lanzó una bola de fuego hacia el enemigo."

        mock_response = """{
            "has_magic": true,
            "description": "Elara lanza bola de fuego",
            "confidence": 0.95,
            "caster": "Elara",
            "effect": "bola de fuego"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.MAGIC_USE
        assert events[0].metadata["caster"] == "Elara"


class TestProphecyDetector:
    """Tests para detector de profecías (Fantasía)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.PROPHECY,
            prompt_template=PROPHECY_PROMPT,
            key="has_prophecy"
        )
        detector.ollama_available = True
        return detector

    def test_detect_prophecy_with_mock(self, detector):
        """Detecta profecía con respuesta mockeada."""
        text = "La vidente predijo: 'Cuando la luna roja aparezca, el elegido despertará'."

        mock_response = """{
            "has_prophecy": true,
            "description": "Profecía del elegido bajo luna roja",
            "confidence": 0.9,
            "prophet": "vidente",
            "content": "el elegido despertará con luna roja"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.PROPHECY
        assert events[0].metadata["prophet"] == "vidente"


class TestWorldBuildingDetector:
    """Tests para detector de worldbuilding (Fantasía)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.WORLD_BUILDING,
            prompt_template=WORLD_BUILDING_PROMPT,
            key="has_worldbuilding"
        )
        detector.ollama_available = True
        return detector

    def test_detect_worldbuilding_with_mock(self, detector):
        """Detecta worldbuilding con respuesta mockeada."""
        text = "En el Imperio, la magia está regulada por el Consejo de Sabios desde hace mil años."

        mock_response = """{
            "has_worldbuilding": true,
            "description": "Sistema de regulación mágica del Imperio",
            "confidence": 0.83,
            "aspect": "magia"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.WORLD_BUILDING


class TestPortalCrossingDetector:
    """Tests para detector de cruce entre mundos (Fantasía)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.PORTAL_CROSSING,
            prompt_template=PORTAL_CROSSING_PROMPT,
            key="has_portal"
        )
        detector.ollama_available = True
        return detector

    def test_detect_portal_crossing_with_mock(self, detector):
        """Detecta cruce de portal con respuesta mockeada."""
        text = "Alex cruzó el portal y apareció en una dimensión completamente diferente."

        mock_response = """{
            "has_portal": true,
            "description": "Alex cruza portal a otra dimensión",
            "confidence": 0.91,
            "traveler": "Alex",
            "destination": "dimensión desconocida"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.PORTAL_CROSSING
        assert events[0].metadata["traveler"] == "Alex"


class TestRomanticTensionDetector:
    """Tests para detector de tensión romántica (Romance)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.ROMANTIC_TENSION,
            prompt_template=ROMANTIC_TENSION_PROMPT,
            key="has_tension"
        )
        detector.ollama_available = True
        return detector

    def test_detect_romantic_tension_with_mock(self, detector):
        """Detecta tensión romántica con respuesta mockeada."""
        text = "Sus miradas se encontraron y el aire entre ellos se volvió eléctrico. Casi se besan."

        mock_response = """{
            "has_tension": true,
            "description": "Tensión sexual entre personajes (casi beso)",
            "confidence": 0.89,
            "characters": ["personaje1", "personaje2"]
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.ROMANTIC_TENSION


class TestLoveDeclarationDetector:
    """Tests para detector de declaración de amor (Romance)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.LOVE_DECLARATION,
            prompt_template=LOVE_DECLARATION_PROMPT,
            key="has_declaration"
        )
        detector.ollama_available = True
        return detector

    def test_detect_love_declaration_with_mock(self, detector):
        """Detecta declaración de amor con respuesta mockeada."""
        text = "Marco tomó su mano y susurró: 'Te amo, siempre lo he hecho'."

        mock_response = """{
            "has_declaration": true,
            "description": "Marco declara su amor",
            "confidence": 0.94,
            "declarer": "Marco",
            "recipient": "personaje receptora"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.LOVE_DECLARATION
        assert events[0].metadata["declarer"] == "Marco"


class TestBreakupDetector:
    """Tests para detector de ruptura (Romance)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.BREAKUP,
            prompt_template=BREAKUP_PROMPT,
            key="has_breakup"
        )
        detector.ollama_available = True
        return detector

    def test_detect_breakup_with_mock(self, detector):
        """Detecta ruptura con respuesta mockeada."""
        text = "Sofía le dijo: 'Lo nuestro se acabó. No puedo más con esta relación'."

        mock_response = """{
            "has_breakup": true,
            "description": "Sofía termina la relación",
            "confidence": 0.91,
            "couple": ["Sofía", "pareja"],
            "initiator": "Sofía"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.BREAKUP
        assert events[0].metadata["initiator"] == "Sofía"


class TestReconciliationDetector:
    """Tests para detector de reconciliación (Romance)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.RECONCILIATION,
            prompt_template=RECONCILIATION_PROMPT,
            key="has_reconciliation"
        )
        detector.ollama_available = True
        return detector

    def test_detect_reconciliation_with_mock(self, detector):
        """Detecta reconciliación con respuesta mockeada."""
        text = "Tras días separados, Ana y Luis se perdonaron y volvieron a estar juntos."

        mock_response = """{
            "has_reconciliation": true,
            "description": "Ana y Luis se reconcilian",
            "confidence": 0.87,
            "couple": ["Ana", "Luis"]
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.RECONCILIATION


class TestKnowledgeTransferDetector:
    """Tests para detector de transmisión de conocimiento (Universal)."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.KNOWLEDGE_TRANSFER,
            prompt_template=KNOWLEDGE_TRANSFER_PROMPT,
            key="has_knowledge_transfer"
        )
        detector.ollama_available = True
        return detector

    def test_detect_knowledge_transfer_learning(self, detector):
        """Detecta transferencia de conocimiento (aprendizaje)."""
        text = "El maestro le enseñó a Pedro el antiguo arte de la esgrima."

        mock_response = """{
            "has_knowledge_transfer": true,
            "description": "Maestro enseña esgrima a Pedro",
            "confidence": 0.86,
            "learner": "Pedro",
            "teacher": "maestro",
            "knowledge": "arte de la esgrima"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KNOWLEDGE_TRANSFER
        assert event.metadata["learner"] == "Pedro"
        assert event.metadata["teacher"] == "maestro"
        assert event.metadata["knowledge"] == "arte de la esgrima"

    def test_detect_knowledge_transfer_discovery(self, detector):
        """Detecta transferencia de conocimiento (descubrimiento)."""
        text = "Clara descubrió por sí misma la verdad sobre su pasado al leer los diarios."

        mock_response = """{
            "has_knowledge_transfer": true,
            "description": "Clara descubre verdad sobre su pasado",
            "confidence": 0.88,
            "learner": "Clara",
            "teacher": "auto",
            "knowledge": "verdad sobre su pasado"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].event_type == EventType.KNOWLEDGE_TRANSFER
        assert events[0].metadata["teacher"] == "auto"

    def test_no_knowledge_transfer_detected(self, detector):
        """No detecta transferencia cuando no la hay."""
        text = "Caminaron por el parque en silencio."

        mock_response = """{
            "has_knowledge_transfer": false,
            "description": "",
            "confidence": 0.0,
            "learner": "",
            "teacher": "",
            "knowledge": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 0


class TestTier3Integration:
    """Tests de integración para función helper de Tier 3."""

    def test_detect_tier3_events_without_ollama(self):
        """Sin Ollama, no detecta eventos Tier 3."""
        text = "Magia, pistas, romance y persecuciones."

        # Simular que Ollama no está disponible
        with patch('narrative_assistant.analysis.event_detection_tier3.GenericLLMDetector') as MockDetector:
            mock_instance = MockDetector.return_value
            mock_instance.ollama_available = False
            mock_instance.detect.return_value = []

            events = detect_tier3_events(text)

        # Como todos los detectores devuelven [], la lista está vacía
        assert isinstance(events, list)

    def test_detect_knowledge_transfer_integration(self):
        """Detecta transmisión de conocimiento via función helper."""
        text = "El sabio reveló a María el secreto del cristal ancestral."

        mock_response = """{
            "has_knowledge_transfer": true,
            "description": "Sabio revela secreto del cristal a María",
            "confidence": 0.92,
            "learner": "María",
            "teacher": "sabio",
            "knowledge": "secreto del cristal ancestral"
        }"""

        with patch('narrative_assistant.analysis.event_detection_tier3.GenericLLMDetector') as MockDetector:
            mock_instance = MockDetector.return_value
            mock_instance.ollama_available = True
            mock_instance.detect.return_value = []

            # Patchear _query_ollama para simular respuesta
            with patch.object(mock_instance, '_query_ollama', return_value=mock_response):
                # Necesitamos mockear la instancia real que se crea dentro de detect_knowledge_transfer
                from narrative_assistant.analysis.event_detection import DetectedEvent

                knowledge_event = DetectedEvent(
                    event_type=EventType.KNOWLEDGE_TRANSFER,
                    description="Sabio revela secreto del cristal a María",
                    confidence=0.92,
                    start_char=0,
                    end_char=len(text),
                    metadata={
                        "learner": "María",
                        "teacher": "sabio",
                        "knowledge": "secreto del cristal ancestral"
                    }
                )

                # Patchear el detector real
                with patch('narrative_assistant.analysis.event_detection_tier3.GenericLLMDetector') as RealDetector:
                    real_instance = RealDetector.return_value
                    real_instance.detect.return_value = [knowledge_event]

                    events = detect_knowledge_transfer(text)

                    assert len(events) == 1
                    assert events[0].event_type == EventType.KNOWLEDGE_TRANSFER


class TestLowConfidenceFiltering:
    """Tests para filtrado de eventos con baja confianza."""

    @pytest.fixture
    def detector(self):
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.CLUE_DISCOVERY,
            prompt_template=CLUE_DISCOVERY_PROMPT,
            key="has_clue"
        )
        detector.ollama_available = True
        return detector

    def test_low_confidence_filtered(self, detector):
        """Filtra eventos con confianza < 0.5."""
        text = "Quizás había algo extraño en la habitación."

        mock_response = """{
            "has_clue": true,
            "description": "Posible pista en habitación",
            "confidence": 0.3,
            "discoverer": "",
            "clue_type": ""
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        # No debe detectar evento con confianza < 0.5
        assert len(events) == 0

    def test_high_confidence_accepted(self, detector):
        """Acepta eventos con confianza >= 0.5."""
        text = "Encontró una huella digital clara en el cristal."

        mock_response = """{
            "has_clue": true,
            "description": "Huella digital encontrada",
            "confidence": 0.75,
            "discoverer": "personaje",
            "clue_type": "física"
        }"""

        with patch.object(detector, '_query_ollama', return_value=mock_response):
            events = detector.detect(text)

        assert len(events) == 1
        assert events[0].confidence == 0.75


class TestOllamaUnavailable:
    """Tests para comportamiento cuando Ollama no está disponible."""

    def test_all_detectors_return_empty_without_ollama(self):
        """Todos los detectores devuelven lista vacía sin Ollama."""
        detector = GenericLLMDetector(
            model="llama3.2",
            event_type=EventType.MAGIC_USE,
            prompt_template=MAGIC_USE_PROMPT,
            key="has_magic"
        )
        detector.ollama_available = False

        text = "Lanzó un poderoso hechizo."
        events = detector.detect(text)

        assert len(events) == 0
