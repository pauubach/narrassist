"""
Detección de eventos narrativos basada en taxonomía de 3 tiers.

Implementa detectores para 45+ tipos de eventos usando:
- NLP (spaCy): Verbos clave, POS tagging, NER
- Heurísticas: Regex, patrones temporales
- LLM (Ollama): Análisis semántico para eventos complejos

Referencia: docs/EVENTS_TAXONOMY_IMPLEMENTATION.md
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from spacy.tokens import Doc

from .event_types import EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Patrones y Vocabulario para Tier 1
# ============================================================================

# Grupo 1: Detección NLP Básica

PROMISE_VERBS = ["prometer", "jurar", "garantizar", "asegurar", "comprometer"]
PROMISE_PATTERNS = [
    r"\bte prometo\b",
    r"\bte juro\b",
    r"\bpalabra de honor\b",
    r"\bte doy mi palabra\b",
    r"\bpromesa\b",
]

CONFESSION_VERBS = ["confesar", "admitir", "reconocer", "revelar", "declarar"]
LIE_VERBS = ["mentir", "engañar", "ocultar", "disimular", "fingir"]

ACQUISITION_VERBS = ["conseguir", "obtener", "encontrar", "recibir", "heredar", "adquirir"]
LOSS_VERBS = ["perder", "robar", "desaparecer", "extraviar", "despojado"]

INJURY_VERBS = ["herir", "lastimar", "fracturar", "sangrar", "atravesar", "golpear"]
HEALING_VERBS = ["curar", "sanar", "recuperarse", "cicatrizar", "mejorar"]
BODY_PARTS = [
    "brazo", "pierna", "hombro", "cabeza", "pecho", "mano", "pie",
    "espalda", "rostro", "cara", "ojo", "oído", "nariz", "boca",
    "cuello", "vientre", "costilla", "muñeca", "tobillo", "rodilla"
]

# Grupo 2: Detección Heurística

FLASHBACK_START_PATTERNS = [
    r"\brecordó\b",
    r"\b\d+ años atrás\b",
    r"\ben aquel entonces\b",
    r"\bcuando era (niño|joven|pequeño|niña)\b",
    r"\b\d+ (años|meses|días) (antes|atrás)\b",
    r"\ben el pasado\b",
    r"\brecuerdos?\b",
    r"\bmemoria\b.*\bvolvió\b",
]

FLASHBACK_END_PATTERNS = [
    r"\bvolvió (en sí|al presente|a la realidad)\b",
    r"\bel presente\b",
    r"\bahora\b",
    r"\bde vuelta (en|a)\b",
    r"\bregresó a\b",
]

TIME_SKIP_PATTERNS = [
    r"\b(\d+) (años?|meses|semanas?|días?|horas?) (después|más tarde)\b",
    r"\b(\d+) (años?|meses|semanas?|días?|horas?) pasaron\b",
    r"\b(un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez) (años?|meses|semanas?|días?|horas?) (después|más tarde)\b",
    r"\bal día siguiente\b",
    r"\ba la mañana siguiente\b",
    r"\bpasó el tiempo\b",
    r"\btranscurrió\b",
]

DREAM_PATTERNS = [
    r"\bsoñó\b",
    r"\ben (el|su)? sueño\b",
    r"\bpesadilla\b",
    r"\bdespertó\b",
]

# Grupo 3: Verbos para detección LLM (para pre-filtrado)

BETRAYAL_INDICATORS = ["traicionar", "abandonar", "vender", "delatar", "engañar"]
ALLIANCE_INDICATORS = ["aliarse", "unirse", "acordar", "pactar", "colaborar"]
REVELATION_INDICATORS = ["revelar", "descubrir", "enterarse", "saber", "comprender"]
DECISION_INDICATORS = ["decidir", "elegir", "optar", "resolver", "determinar"]


# ============================================================================
# Dataclasses para eventos detectados
# ============================================================================

@dataclass
class DetectedEvent:
    """
    Evento detectado por los detectores.

    Attributes:
        event_type: Tipo de evento (EventType enum value)
        description: Descripción del evento
        confidence: Nivel de confianza (0-1)
        start_char: Posición inicial en el texto
        end_char: Posición final en el texto
        entity_ids: IDs de personajes involucrados (si se conocen)
        metadata: Información adicional específica del tipo de evento
    """

    event_type: EventType
    description: str
    confidence: float
    start_char: int
    end_char: int
    entity_ids: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Detectores Tier 1 - Grupo 1: NLP Básico
# ============================================================================

class PromiseDetector:
    """Detecta promesas usando verbos clave y patrones."""

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """
        Detecta promesas en el texto.

        Args:
            doc: Documento spaCy procesado
            text: Texto original

        Returns:
            Lista de eventos detectados
        """
        events = []

        # Buscar verbos de promesa
        for token in doc:
            if token.lemma_.lower() in PROMISE_VERBS:
                # Extraer contexto (frase completa)
                sent = token.sent
                start_char = sent.start_char
                end_char = sent.end_char

                # Extraer sujeto (quien promete)
                subject = self._extract_subject(token)

                # Extraer complemento (qué se promete)
                complement = self._extract_complement(token, sent)

                description = f"{subject or 'Alguien'} prometió {complement or 'algo'}"

                events.append(DetectedEvent(
                    event_type=EventType.PROMISE,
                    description=description,
                    confidence=0.8,
                    start_char=start_char,
                    end_char=end_char,
                    metadata={
                        "promise_text": complement,
                        "subject": subject,
                    }
                ))

        # Buscar patrones explícitos
        for pattern in PROMISE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Evitar duplicados con detección de verbos
                if not any(e.start_char <= match.start() <= e.end_char for e in events):
                    events.append(DetectedEvent(
                        event_type=EventType.PROMISE,
                        description=f"Promesa: {match.group()}",
                        confidence=0.7,
                        start_char=match.start(),
                        end_char=match.end(),
                        metadata={"pattern": pattern}
                    ))

        return events

    def _extract_subject(self, token) -> str | None:
        """Extrae el sujeto del verbo."""
        for child in token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                return child.text
        return None

    def _extract_complement(self, token, sent) -> str | None:
        """Extrae el complemento del verbo (qué se promete)."""
        # Buscar complemento directo o infinitivo
        for child in token.children:
            if child.dep_ in ("dobj", "xcomp", "ccomp"):
                # Tomar hasta el final de la frase
                return sent.text[child.idx - sent.start_char:]
        return None


class InjuryDetector:
    """Detecta heridas/lesiones de personajes."""

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """Detecta heridas en el texto."""
        events = []

        for token in doc:
            if token.lemma_.lower() in INJURY_VERBS:
                sent = token.sent
                start_char = sent.start_char
                end_char = sent.end_char

                # Buscar parte del cuerpo mencionada
                body_part = self._find_body_part(sent)

                # Buscar sujeto (quien resulta herido)
                injured = self._extract_object(token) or self._extract_subject(token)

                description = f"{injured or 'Alguien'} resultó herido"
                if body_part:
                    description += f" en {body_part}"

                # Inferir severidad del verbo
                severity = "grave" if token.lemma_ in ["atravesar", "fracturar"] else "leve"

                events.append(DetectedEvent(
                    event_type=EventType.INJURY,
                    description=description,
                    confidence=0.75,
                    start_char=start_char,
                    end_char=end_char,
                    metadata={
                        "body_part": body_part,
                        "severity": severity,
                        "injured": injured,
                    }
                ))

        return events

    def _find_body_part(self, sent) -> str | None:
        """Busca menciones de partes del cuerpo en la frase."""
        sent_text_lower = sent.text.lower()
        for part in BODY_PARTS:
            if part in sent_text_lower:
                return part
        return None

    def _extract_subject(self, token) -> str | None:
        """Extrae el sujeto del verbo."""
        for child in token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                return child.text
        return None

    def _extract_object(self, token) -> str | None:
        """Extrae el objeto directo."""
        for child in token.children:
            if child.dep_ in ("dobj", "iobj"):
                return child.text
        return None


class AcquisitionLossDetector:
    """Detecta adquisiciones y pérdidas de objetos."""

    def detect(self, doc: Doc, text: str) -> list[DetectedEvent]:
        """Detecta adquisiciones/pérdidas en el texto."""
        events = []

        for token in doc:
            lemma = token.lemma_.lower()

            # Determinar tipo de evento
            event_type = None
            if lemma in ACQUISITION_VERBS:
                event_type = EventType.ACQUISITION
            elif lemma in LOSS_VERBS:
                event_type = EventType.LOSS

            if not event_type:
                continue

            sent = token.sent
            start_char = sent.start_char
            end_char = sent.end_char

            # Buscar objeto involucrado
            obj = self._extract_object(token)

            # Buscar sujeto
            subject = self._extract_subject(token)

            action = "obtuvo" if event_type == EventType.ACQUISITION else "perdió"
            description = f"{subject or 'Alguien'} {action} {obj or 'algo'}"

            events.append(DetectedEvent(
                event_type=event_type,
                description=description,
                confidence=0.7,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    "object": obj,
                    "subject": subject,
                }
            ))

        return events

    def _extract_subject(self, token) -> str | None:
        """Extrae el sujeto del verbo."""
        for child in token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                return child.text
        return None

    def _extract_object(self, token) -> str | None:
        """Extrae el objeto (qué se adquiere/pierde)."""
        for child in token.children:
            if child.dep_ in ("dobj", "obj"):
                # Tomar toda la frase nominal si es compuesta
                obj_tokens = [child]
                obj_tokens.extend([t for t in child.subtree if t.dep_ in ("amod", "det", "compound")])
                return " ".join(sorted(obj_tokens, key=lambda t: t.i))
        return None


# ============================================================================
# Detectores Tier 1 - Grupo 2: Heurísticos
# ============================================================================

class FlashbackDetector:
    """Detecta inicio/fin de flashbacks (analepsis)."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta flashbacks mediante patrones regex."""
        events = []

        # Detectar inicio de flashback
        for pattern in FLASHBACK_START_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.FLASHBACK_START,
                    description=f"Inicio de flashback: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                    metadata={"pattern": pattern}
                ))

        # Detectar fin de flashback
        for pattern in FLASHBACK_END_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                events.append(DetectedEvent(
                    event_type=EventType.FLASHBACK_END,
                    description=f"Fin de flashback: {match.group()}",
                    confidence=0.65,
                    start_char=match.start(),
                    end_char=match.end(),
                    metadata={"pattern": pattern}
                ))

        return events


class TimeSkipDetector:
    """Detecta saltos temporales explícitos."""

    def detect(self, text: str) -> list[DetectedEvent]:
        """Detecta saltos temporales mediante patrones."""
        events = []

        for pattern in TIME_SKIP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extraer duración si está en el patrón
                duration = match.group(0) if match.groups() else None

                events.append(DetectedEvent(
                    event_type=EventType.TIME_SKIP,
                    description=f"Salto temporal: {match.group()}",
                    confidence=0.8,
                    start_char=match.start(),
                    end_char=match.end(),
                    metadata={"duration": duration}
                ))

        return events


# ============================================================================
# Detector Principal (Orquestador)
# ============================================================================

class EventDetector:
    """
    Detector principal que orquesta todos los detectores específicos.

    Implementa detección en 3 fases:
    1. Fase NLP: Detectores basados en spaCy
    2. Fase Heurística: Detectores basados en regex
    3. Fase LLM: Detectores basados en Ollama (para eventos complejos)
    """

    def __init__(self, nlp=None, enable_llm: bool = False):
        """
        Inicializa el detector.

        Args:
            nlp: Modelo spaCy (opcional, se carga si no se proporciona)
            enable_llm: Si habilitar detectores LLM (más lentos)
        """
        self.nlp = nlp
        self.enable_llm = enable_llm

        # Inicializar detectores Tier 1
        self.promise_detector = PromiseDetector()
        self.injury_detector = InjuryDetector()
        self.acquisition_loss_detector = AcquisitionLossDetector()
        self.flashback_detector = FlashbackDetector()
        self.time_skip_detector = TimeSkipDetector()

    def detect_events(self, text: str, chapter_number: int = 1) -> list[DetectedEvent]:
        """
        Detecta todos los eventos en un texto.

        Args:
            text: Texto a analizar
            chapter_number: Número de capítulo (para contexto)

        Returns:
            Lista de eventos detectados, ordenados por posición
        """
        events: list[DetectedEvent] = []

        # Fase 1: Detectores NLP (requieren spaCy)
        if self.nlp:
            doc = self.nlp(text)

            # Tier 1 - Grupo 1: NLP Básico
            events.extend(self.promise_detector.detect(doc, text))
            events.extend(self.injury_detector.detect(doc, text))
            events.extend(self.acquisition_loss_detector.detect(doc, text))

            logger.debug(f"Fase NLP: {len(events)} eventos detectados")

        # Fase 2: Detectores Heurísticos (regex)
        heuristic_events = []
        heuristic_events.extend(self.flashback_detector.detect(text))
        heuristic_events.extend(self.time_skip_detector.detect(text))
        events.extend(heuristic_events)

        logger.debug(f"Fase Heurística: {len(heuristic_events)} eventos detectados")

        # Fase 3: Detectores LLM (opcional, más lentos)
        if self.enable_llm:
            # TODO: Implementar detectores LLM para BETRAYAL, ALLIANCE, etc.
            pass

        # Ordenar por posición
        events.sort(key=lambda e: e.start_char)

        logger.info(f"Total eventos detectados en capítulo {chapter_number}: {len(events)}")
        return events


def detect_events_in_chapter(
    text: str,
    chapter_number: int,
    nlp=None,
    enable_llm: bool = False
) -> list[DetectedEvent]:
    """
    Función helper para detectar eventos en un capítulo.

    Args:
        text: Texto del capítulo
        chapter_number: Número de capítulo
        nlp: Modelo spaCy (opcional)
        enable_llm: Si habilitar detectores LLM

    Returns:
        Lista de eventos detectados
    """
    detector = EventDetector(nlp=nlp, enable_llm=enable_llm)
    return detector.detect_events(text, chapter_number)
