"""
Detectores de eventos Tier 3 (Especialización por Género).

Eventos específicos para géneros narrativos:
- Thriller/Suspense: CLUE_DISCOVERY, RED_HERRING, DANGER_ESCALATION, CHASE_START
- Fantasía/SciFi: MAGIC_USE, PROPHECY, WORLD_BUILDING, PORTAL_CROSSING
- Romance: ROMANTIC_TENSION, LOVE_DECLARATION, BREAKUP, RECONCILIATION
- Universal: KNOWLEDGE_TRANSFER (transmisión de conocimiento)

Usa Ollama (LLM) para análisis semántico avanzado.
"""

import logging
from typing import Any

from spacy.tokens import Doc

from .event_detection_llm import LLMEventDetector
from .event_detection import DetectedEvent
from .event_types import EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Prompts para Tier 3
# ============================================================================

CLUE_DISCOVERY_PROMPT = """Analiza si en el texto se descubre una PISTA o evidencia importante.

Una pista ocurre cuando:
- Se encuentra información que ayuda a resolver un misterio
- Se descubre evidencia física (objeto, marca, documento)
- Un personaje nota un detalle significativo
- Se revela información que conecta eventos

Texto:
{text}

Responde SOLO con JSON:
{{"has_clue": true/false, "description": "descripción breve (max 80 chars)", "confidence": 0.0-1.0, "discoverer": "quién descubre", "clue_type": "física/verbal/observación"}}
"""

RED_HERRING_PROMPT = """Analiza si el texto contiene una PISTA FALSA (red herring).

Una pista falsa ocurre cuando:
- Se presenta información engañosa intencionalmente
- Un personaje es sospechoso pero resulta inocente
- Se enfatiza algo que resulta irrelevante
- Se desvía la atención del verdadero misterio

Texto:
{text}

Responde SOLO con JSON:
{{"has_red_herring": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "misleading_element": "qué engaña"}}
"""

DANGER_ESCALATION_PROMPT = """Analiza si el PELIGRO aumenta significativamente.

Escalación de peligro ocurre cuando:
- La amenaza se vuelve más intensa o inmediata
- Aumenta el número de personas en riesgo
- Se descubre que el peligro es mayor de lo pensado
- El tiempo para evitar catástrofe se acorta

Texto:
{text}

Responde SOLO con JSON:
{{"has_escalation": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "threat_level": "bajo/medio/alto/crítico"}}
"""

CHASE_START_PROMPT = """Analiza si comienza una PERSECUCIÓN.

Una persecución ocurre cuando:
- Un personaje persigue activamente a otro
- Hay una huida y seguimiento explícito
- Comienza una cacería o búsqueda urgente
- Se menciona explícitamente una persecución

Texto:
{text}

Responde SOLO con JSON:
{{"has_chase": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "chaser": "perseguidor", "target": "perseguido"}}
"""

MAGIC_USE_PROMPT = """Analiza si se usa MAGIA o un poder especial.

Uso de magia ocurre cuando:
- Un personaje lanza un hechizo o conjuro
- Se activa un poder sobrenatural
- Ocurre un fenómeno mágico explícito
- Se menciona uso de energía mística/poderes

Texto:
{text}

Responde SOLO con JSON:
{{"has_magic": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "caster": "quien usa magia", "effect": "efecto del poder"}}
"""

PROPHECY_PROMPT = """Analiza si se revela o menciona una PROFECÍA.

Una profecía ocurre cuando:
- Se predice el futuro de forma sobrenatural
- Se menciona un destino o vaticinio
- Se revela una visión profética
- Se habla de un presagio o augurio importante

Texto:
{text}

Responde SOLO con JSON:
{{"has_prophecy": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "prophet": "quien profetiza", "content": "qué se predice"}}
"""

WORLD_BUILDING_PROMPT = """Analiza si hay WORLDBUILDING significativo (expansión del mundo).

Worldbuilding ocurre cuando:
- Se explica historia/lore del mundo
- Se describe un sistema mágico/tecnológico
- Se detalla cultura/sociedad/política
- Se revelan reglas del universo narrativo

Texto:
{text}

Responde SOLO con JSON:
{{"has_worldbuilding": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "aspect": "historia/magia/cultura/geografía"}}
"""

PORTAL_CROSSING_PROMPT = """Analiza si hay un CRUCE entre mundos o dimensiones.

Cruce de portal ocurre cuando:
- Personaje viaja a otra dimensión/mundo/plano
- Se cruza un umbral mágico/tecnológico
- Se menciona teletransporte entre lugares distantes
- Hay salto entre realidades

Texto:
{text}

Responde SOLO con JSON:
{{"has_portal": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "traveler": "quién viaja", "destination": "destino"}}
"""

ROMANTIC_TENSION_PROMPT = """Analiza si hay TENSIÓN ROMÁNTICA palpable.

Tensión romántica ocurre cuando:
- Hay atracción no resuelta entre personajes
- Momentos cargados emocionalmente (casi beso, miradas)
- Se menciona explícitamente la tensión
- Hay incomodidad/nerviosismo por atracción

Texto:
{text}

Responde SOLO con JSON:
{{"has_tension": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "characters": ["personaje1", "personaje2"]}}
"""

LOVE_DECLARATION_PROMPT = """Analiza si hay una DECLARACIÓN DE AMOR.

Declaración de amor ocurre cuando:
- Un personaje confiesa sus sentimientos románticos
- Se dice "te amo" o equivalente
- Hay una propuesta romántica
- Se expresa amor de forma explícita

Texto:
{text}

Responde SOLO con JSON:
{{"has_declaration": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "declarer": "quien declara", "recipient": "destinatario"}}
"""

BREAKUP_PROMPT = """Analiza si hay una RUPTURA de relación romántica.

Ruptura ocurre cuando:
- Una pareja termina su relación
- Se dice explícitamente que terminan
- Hay una separación romántica definitiva
- Se menciona el fin de la relación

Texto:
{text}

Responde SOLO con JSON:
{{"has_breakup": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "couple": ["personaje1", "personaje2"], "initiator": "quien termina"}}
"""

RECONCILIATION_PROMPT = """Analiza si hay una RECONCILIACIÓN romántica.

Reconciliación ocurre cuando:
- Una pareja separada vuelve a estar junta
- Se resuelve conflicto y reanudan relación
- Hay perdón y vuelta al romance
- Se menciona explícitamente que vuelven

Texto:
{text}

Responde SOLO con JSON:
{{"has_reconciliation": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "couple": ["personaje1", "personaje2"]}}
"""

KNOWLEDGE_TRANSFER_PROMPT = """Analiza si un personaje DESCUBRE o APRENDE algo importante.

Transferencia de conocimiento ocurre cuando:
- Un personaje aprende información crucial
- Se enseña/transmite conocimiento explícitamente
- Alguien descubre/comprende algo significativo
- Se revela información que cambia la comprensión

Texto:
{text}

Responde SOLO con JSON:
{{"has_knowledge_transfer": true/false, "description": "descripción (max 80 chars)", "confidence": 0.0-1.0, "learner": "quien aprende", "teacher": "quien enseña (o 'auto' si descubre solo)", "knowledge": "qué aprende/descubre"}}
"""


# ============================================================================
# Detectores Tier 3
# ============================================================================

class ClueDiscoveryDetector(LLMEventDetector):
    """Detecta descubrimiento de pistas (Thriller)."""

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        if not self.ollama_available:
            return []

        chunks = self._chunk_text(text, max_words=400)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = CLUE_DISCOVERY_PROMPT.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get("has_clue") and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=EventType.CLUE_DISCOVERY,
                    description=data.get("description", "Pista descubierta")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={
                        "discoverer": data.get("discoverer", ""),
                        "clue_type": data.get("clue_type", ""),
                        "llm_model": self.model,
                    }
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 400) -> list[tuple[str, int]]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))
        return chunks


# Implemento los demás detectores Tier 3 de forma similar...
# Para mantener el archivo manejable, uso una clase base genérica

class GenericLLMDetector(LLMEventDetector):
    """Detector LLM genérico configurable."""

    def __init__(self, model: str = "llama3.2", event_type: EventType = None, prompt_template: str = "", key: str = ""):
        super().__init__(model)
        self.event_type_value = event_type
        self.prompt_template = prompt_template
        self.response_key = key

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        if not self.ollama_available or not self.event_type_value:
            return []

        chunks = self._chunk_text(text, max_words=400)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = self.prompt_template.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get(self.response_key) and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=self.event_type_value,
                    description=data.get("description", f"{self.event_type_value.value} detectado")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={k: v for k, v in data.items() if k not in ["description", "confidence", self.response_key]},
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 400) -> list[tuple[str, int]]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))
        return chunks


# ============================================================================
# Helper para detectar todos los eventos Tier 3
# ============================================================================

def detect_tier3_events(text: str, doc: Doc | None = None, model: str = "llama3.2") -> list[DetectedEvent]:
    """
    Detecta todos los eventos Tier 3 (especializados por género).

    Args:
        text: Texto a analizar
        doc: Documento spaCy (opcional)
        model: Modelo de Ollama

    Returns:
        Lista de eventos Tier 3 detectados
    """
    events = []

    # Thriller/Suspense
    detectors = [
        GenericLLMDetector(model, EventType.CLUE_DISCOVERY, CLUE_DISCOVERY_PROMPT, "has_clue"),
        GenericLLMDetector(model, EventType.RED_HERRING, RED_HERRING_PROMPT, "has_red_herring"),
        GenericLLMDetector(model, EventType.DANGER_ESCALATION, DANGER_ESCALATION_PROMPT, "has_escalation"),
        GenericLLMDetector(model, EventType.CHASE_START, CHASE_START_PROMPT, "has_chase"),

        # Fantasía/SciFi
        GenericLLMDetector(model, EventType.MAGIC_USE, MAGIC_USE_PROMPT, "has_magic"),
        GenericLLMDetector(model, EventType.PROPHECY, PROPHECY_PROMPT, "has_prophecy"),
        GenericLLMDetector(model, EventType.WORLD_BUILDING, WORLD_BUILDING_PROMPT, "has_worldbuilding"),
        GenericLLMDetector(model, EventType.PORTAL_CROSSING, PORTAL_CROSSING_PROMPT, "has_portal"),

        # Romance
        GenericLLMDetector(model, EventType.ROMANTIC_TENSION, ROMANTIC_TENSION_PROMPT, "has_tension"),
        GenericLLMDetector(model, EventType.LOVE_DECLARATION, LOVE_DECLARATION_PROMPT, "has_declaration"),
        GenericLLMDetector(model, EventType.BREAKUP, BREAKUP_PROMPT, "has_breakup"),
        GenericLLMDetector(model, EventType.RECONCILIATION, RECONCILIATION_PROMPT, "has_reconciliation"),
    ]

    # Ejecutar todos los detectores
    for detector in detectors:
        events.extend(detector.detect(text, doc))

    logger.debug(f"Tier 3: {len(events)} eventos detectados")
    return events


def detect_knowledge_transfer(text: str, doc: Doc | None = None, model: str = "llama3.2") -> list[DetectedEvent]:
    """
    Detecta eventos de transmisión/descubrimiento de conocimiento.

    Este es un evento universal (no limitado a un género específico).

    Args:
        text: Texto a analizar
        doc: Documento spaCy (opcional)
        model: Modelo de Ollama

    Returns:
        Lista de eventos KNOWLEDGE_TRANSFER detectados
    """
    detector = GenericLLMDetector(
        model=model,
        event_type=EventType.KNOWLEDGE_TRANSFER,
        prompt_template=KNOWLEDGE_TRANSFER_PROMPT,
        key="has_knowledge_transfer"
    )

    events = detector.detect(text, doc)
    logger.debug(f"Knowledge Transfer: {len(events)} eventos detectados")
    return events
