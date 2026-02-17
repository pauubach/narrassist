"""
Detectores de eventos usando LLM (Ollama).

Implementa detección de eventos complejos que requieren análisis semántico:
- Tier 1: BETRAYAL, ALLIANCE, REVELATION, DECISION (4 eventos críticos)
- Tier 3: Eventos especializados (12+)

Usa Ollama para análisis local con modelos como llama3.2, qwen2.5, mistral.
"""

import json
import logging
import re
from typing import Any

from spacy.tokens import Doc

from .event_detection import DetectedEvent
from .event_types import EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Prompts para detectores LLM
# ============================================================================

BETRAYAL_PROMPT = """Analiza el siguiente texto narrativo y detecta si hay alguna TRAICIÓN (betrayal).

Una traición ocurre cuando:
- Un personaje rompe la confianza o lealtad de otro
- Alguien actúa en contra de un aliado o amigo
- Se revela que un personaje trabajaba secretamente contra otro
- Hay un cambio de bando o lealtad inesperado

Texto:
{text}

Responde SOLO con un JSON en este formato exacto:
{{
  "has_betrayal": true/false,
  "description": "descripción breve del evento de traición (max 80 caracteres)",
  "confidence": 0.0-1.0,
  "betrayer": "nombre del traidor",
  "victim": "nombre de la víctima"
}}

Si NO hay traición, usa: {{"has_betrayal": false, "description": "", "confidence": 0.0, "betrayer": "", "victim": ""}}
"""

ALLIANCE_PROMPT = """Analiza el siguiente texto narrativo y detecta si se forma una ALIANZA.

Una alianza ocurre cuando:
- Dos o más personajes acuerdan trabajar juntos
- Se forma un pacto, acuerdo o colaboración
- Personajes enemigos deciden unir fuerzas
- Se menciona explícitamente una unión estratégica

Texto:
{text}

Responde SOLO con un JSON en este formato exacto:
{{
  "has_alliance": true/false,
  "description": "descripción breve de la alianza (max 80 caracteres)",
  "confidence": 0.0-1.0,
  "members": ["personaje1", "personaje2"]
}}

Si NO hay alianza, usa: {{"has_alliance": false, "description": "", "confidence": 0.0, "members": []}}
"""

REVELATION_PROMPT = """Analiza el siguiente texto narrativo y detecta si hay una REVELACIÓN importante.

Una revelación ocurre cuando:
- Se descubre un secreto importante
- Un personaje confiesa algo crucial
- Se revela información que cambia la comprensión de la trama
- Hay una verdad oculta que sale a la luz

Texto:
{text}

Responde SOLO con un JSON en este formato exacto:
{{
  "has_revelation": true/false,
  "description": "descripción breve de la revelación (max 80 caracteres)",
  "confidence": 0.0-1.0,
  "revealer": "quién revela (si aplica)",
  "content": "qué se revela"
}}

Si NO hay revelación, usa: {{"has_revelation": false, "description": "", "confidence": 0.0, "revealer": "", "content": ""}}
"""

DECISION_PROMPT = """Analiza el siguiente texto narrativo y detecta si hay una DECISIÓN crucial.

Una decisión crucial ocurre cuando:
- Un personaje toma una decisión importante que afecta la trama
- Hay un momento de elección difícil o dilema
- Se menciona explícitamente que alguien decide algo importante
- Un personaje elige entre opciones con consecuencias significativas

Texto:
{text}

Responde SOLO con un JSON en este formato exacto:
{{
  "has_decision": true/false,
  "description": "descripción breve de la decisión (max 80 caracteres)",
  "confidence": 0.0-1.0,
  "decision_maker": "quién decide",
  "choice": "qué decide"
}}

Si NO hay decisión crucial, usa: {{"has_decision": false, "description": "", "confidence": 0.0, "decision_maker": "", "choice": ""}}
"""


# ============================================================================
# Sistema LLM Base
# ============================================================================

class LLMEventDetector:
    """Detector base usando Ollama para eventos complejos."""

    def __init__(self, model: str = "llama3.2"):
        """
        Inicializa el detector LLM.

        Args:
            model: Modelo de Ollama a usar (llama3.2, qwen2.5, mistral)
        """
        self.model = model
        self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            from narrative_assistant.llm.ollama_manager import get_ollama_manager
            manager = get_ollama_manager()
            return manager.is_available()
        except Exception as e:
            logger.warning(f"Ollama no disponible: {e}")
            return False

    def _query_ollama(self, prompt: str) -> str:
        """
        Consulta Ollama con un prompt.

        Args:
            prompt: Prompt para el LLM

        Returns:
            Respuesta del LLM
        """
        if not self.ollama_available:
            return "{}"

        try:
            from narrative_assistant.llm.ollama_manager import get_ollama_manager
            manager = get_ollama_manager()

            response = manager.generate(
                prompt=prompt,
                model=self.model,
                temperature=0.3,  # Baja temperatura para respuestas consistentes
                max_tokens=200,
            )

            return response.strip()
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return "{}"

    def _extract_json(self, response: str) -> dict[str, Any]:
        """
        Extrae JSON de la respuesta del LLM.

        Args:
            response: Respuesta del LLM

        Returns:
            Diccionario parseado o vacío si falla
        """
        # Intentar parsear directamente
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Buscar JSON en la respuesta (puede haber texto antes/después)
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"No se pudo extraer JSON de respuesta: {response[:100]}")
        return {}


# ============================================================================
# Detectores Tier 1 (LLM)
# ============================================================================

class BetrayalDetector(LLMEventDetector):
    """Detecta traiciones usando LLM."""

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        """
        Detecta eventos de traición.

        Args:
            text: Texto a analizar
            doc: Documento spaCy (opcional)

        Returns:
            Lista de eventos BETRAYAL detectados
        """
        if not self.ollama_available:
            return []

        # Dividir en fragmentos manejables (max 500 palabras)
        chunks = self._chunk_text(text, max_words=500)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = BETRAYAL_PROMPT.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get("has_betrayal") and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=EventType.BETRAYAL,
                    description=data.get("description", "Traición detectada")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={
                        "betrayer": data.get("betrayer", ""),
                        "victim": data.get("victim", ""),
                        "llm_model": self.model,
                    }
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 500) -> list[tuple[str, int]]:
        """
        Divide texto en fragmentos manejables.

        Args:
            text: Texto a dividir
            max_words: Máximo de palabras por fragmento

        Returns:
            Lista de (texto_fragmento, offset_inicial)
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            # Calcular offset aproximado
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))

        return chunks


class AllianceDetector(LLMEventDetector):
    """Detecta formación de alianzas usando LLM."""

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        """Detecta eventos de alianza."""
        if not self.ollama_available:
            return []

        chunks = self._chunk_text(text, max_words=500)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = ALLIANCE_PROMPT.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get("has_alliance") and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=EventType.ALLIANCE,
                    description=data.get("description", "Alianza formada")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={
                        "members": data.get("members", []),
                        "llm_model": self.model,
                    }
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 500) -> list[tuple[str, int]]:
        """Divide texto en fragmentos."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))
        return chunks


class RevelationDetector(LLMEventDetector):
    """Detecta revelaciones usando LLM."""

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        """Detecta eventos de revelación."""
        if not self.ollama_available:
            return []

        chunks = self._chunk_text(text, max_words=500)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = REVELATION_PROMPT.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get("has_revelation") and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=EventType.REVELATION,
                    description=data.get("description", "Revelación importante")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={
                        "revealer": data.get("revealer", ""),
                        "content": data.get("content", ""),
                        "llm_model": self.model,
                    }
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 500) -> list[tuple[str, int]]:
        """Divide texto en fragmentos."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))
        return chunks


class DecisionDetector(LLMEventDetector):
    """Detecta decisiones cruciales usando LLM."""

    def detect(self, text: str, doc: Doc | None = None) -> list[DetectedEvent]:
        """Detecta eventos de decisión crucial."""
        if not self.ollama_available:
            return []

        chunks = self._chunk_text(text, max_words=500)
        events = []

        for chunk_text, start_offset in chunks:
            prompt = DECISION_PROMPT.format(text=chunk_text)
            response = self._query_ollama(prompt)
            data = self._extract_json(response)

            if data.get("has_decision") and data.get("confidence", 0) > 0.5:
                events.append(DetectedEvent(
                    event_type=EventType.DECISION,
                    description=data.get("description", "Decisión crucial")[:80],
                    confidence=min(data.get("confidence", 0.6), 1.0),
                    start_char=start_offset,
                    end_char=start_offset + len(chunk_text),
                    metadata={
                        "decision_maker": data.get("decision_maker", ""),
                        "choice": data.get("choice", ""),
                        "llm_model": self.model,
                    }
                ))

        return events

    def _chunk_text(self, text: str, max_words: int = 500) -> list[tuple[str, int]]:
        """Divide texto en fragmentos."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = " ".join(chunk_words)
            offset = len(" ".join(words[:i]))
            chunks.append((chunk_text, offset))
        return chunks


# ============================================================================
# Función helper para detectar todos los eventos LLM Tier 1
# ============================================================================

def detect_llm_tier1_events(text: str, doc: Doc | None = None, model: str = "llama3.2") -> list[DetectedEvent]:
    """
    Detecta todos los eventos Tier 1 que requieren LLM.

    Args:
        text: Texto a analizar
        doc: Documento spaCy (opcional)
        model: Modelo de Ollama a usar

    Returns:
        Lista de eventos LLM detectados
    """
    events = []

    # Detectores Tier 1 (LLM)
    betrayal_detector = BetrayalDetector(model=model)
    alliance_detector = AllianceDetector(model=model)
    revelation_detector = RevelationDetector(model=model)
    decision_detector = DecisionDetector(model=model)

    events.extend(betrayal_detector.detect(text, doc))
    events.extend(alliance_detector.detect(text, doc))
    events.extend(revelation_detector.detect(text, doc))
    events.extend(decision_detector.detect(text, doc))

    logger.debug(f"LLM Tier 1: {len(events)} eventos detectados")
    return events
