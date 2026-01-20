"""
Modelos de datos para interacciones entre entidades.

Define tipos de interacción, tonos, y estructuras para
rastrear cómo las entidades interactúan a lo largo de la narrativa.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class InteractionType(Enum):
    """Tipos de interacción entre entidades."""
    DIALOGUE = "dialogue"           # Conversación directa
    ACTION_TOWARDS = "action"       # Acción de uno hacia otro
    THOUGHT_ABOUT = "thought"       # Pensamiento sobre otro
    OBSERVATION = "observation"     # Observación de uno sobre otro
    PHYSICAL_CONTACT = "physical"   # Contacto físico
    GIFT_EXCHANGE = "gift"          # Intercambio de objetos
    MENTION = "mention"             # Mención de uno por otro
    REACTION = "reaction"           # Reacción a acciones del otro


class InteractionTone(Enum):
    """Tono emocional de la interacción."""
    HOSTILE = "hostile"             # Hostil, agresivo
    COLD = "cold"                   # Frío, distante
    NEUTRAL = "neutral"             # Neutral, sin carga emocional
    WARM = "warm"                   # Cálido, amigable
    AFFECTIONATE = "affectionate"   # Afectuoso, cariñoso

    @classmethod
    def from_score(cls, score: float) -> "InteractionTone":
        """
        Convierte un score de sentimiento (-1 a 1) a tono.

        Args:
            score: Valor de -1 (muy negativo) a 1 (muy positivo)

        Returns:
            Tono correspondiente
        """
        if score < -0.5:
            return cls.HOSTILE
        elif score < -0.2:
            return cls.COLD
        elif score < 0.2:
            return cls.NEUTRAL
        elif score < 0.5:
            return cls.WARM
        else:
            return cls.AFFECTIONATE

    def to_score(self) -> float:
        """Convierte tono a score aproximado."""
        mapping = {
            InteractionTone.HOSTILE: -0.75,
            InteractionTone.COLD: -0.35,
            InteractionTone.NEUTRAL: 0.0,
            InteractionTone.WARM: 0.35,
            InteractionTone.AFFECTIONATE: 0.75,
        }
        return mapping.get(self, 0.0)


@dataclass
class EntityInteraction:
    """Una interacción específica entre entidades."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: int = 0

    # Participantes
    initiator_id: str = ""
    receiver_id: str = ""
    initiator_name: str = ""
    receiver_name: str = ""

    # Clasificación
    interaction_type: InteractionType = InteractionType.OBSERVATION
    tone: InteractionTone = InteractionTone.NEUTRAL

    # Ubicación
    chapter: int = 0
    scene_index: Optional[int] = None
    text_excerpt: str = ""
    start_char: int = 0
    end_char: int = 0

    # Análisis
    sentiment_score: float = 0.0   # -1 a 1
    intensity: float = 0.5         # 0 a 1 (qué tan intensa es la interacción)

    # Coherencia con relación
    relationship_id: Optional[str] = None
    expected_tone: Optional[InteractionTone] = None
    is_coherent: bool = True
    coherence_note: str = ""

    # Metadatos
    confidence: float = 0.5
    detection_method: str = "pattern"  # pattern, sentiment, llm
    created_at: datetime = field(default_factory=datetime.now)

    # Flags
    user_marked_intentional: bool = False  # Usuario marcó como incoherencia intencional

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "initiator_id": self.initiator_id,
            "receiver_id": self.receiver_id,
            "initiator_name": self.initiator_name,
            "receiver_name": self.receiver_name,
            "interaction_type": self.interaction_type.value,
            "tone": self.tone.value,
            "chapter": self.chapter,
            "scene_index": self.scene_index,
            "text_excerpt": self.text_excerpt,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "sentiment_score": self.sentiment_score,
            "intensity": self.intensity,
            "relationship_id": self.relationship_id,
            "expected_tone": self.expected_tone.value if self.expected_tone else None,
            "is_coherent": self.is_coherent,
            "coherence_note": self.coherence_note,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "created_at": self.created_at.isoformat(),
            "user_marked_intentional": self.user_marked_intentional,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EntityInteraction":
        """Crea desde diccionario."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", 0),
            initiator_id=data.get("initiator_id", ""),
            receiver_id=data.get("receiver_id", ""),
            initiator_name=data.get("initiator_name", ""),
            receiver_name=data.get("receiver_name", ""),
            interaction_type=InteractionType(data.get("interaction_type", "observation")),
            tone=InteractionTone(data.get("tone", "neutral")),
            chapter=data.get("chapter", 0),
            scene_index=data.get("scene_index"),
            text_excerpt=data.get("text_excerpt", ""),
            start_char=data.get("start_char", 0),
            end_char=data.get("end_char", 0),
            sentiment_score=data.get("sentiment_score", 0.0),
            intensity=data.get("intensity", 0.5),
            relationship_id=data.get("relationship_id"),
            expected_tone=(
                InteractionTone(data["expected_tone"])
                if data.get("expected_tone") else None
            ),
            is_coherent=data.get("is_coherent", True),
            coherence_note=data.get("coherence_note", ""),
            confidence=data.get("confidence", 0.5),
            detection_method=data.get("detection_method", "pattern"),
            user_marked_intentional=data.get("user_marked_intentional", False),
        )


@dataclass
class InteractionPattern:
    """Patrón de interacción entre dos entidades a lo largo del texto."""
    entity1_id: str = ""
    entity2_id: str = ""
    entity1_name: str = ""
    entity2_name: str = ""

    # Estadísticas generales
    total_interactions: int = 0
    interactions_by_type: dict = field(default_factory=dict)
    interactions_by_tone: dict = field(default_factory=dict)

    # Tono promedio
    average_tone: InteractionTone = InteractionTone.NEUTRAL
    average_sentiment_score: float = 0.0
    tone_variance: float = 0.0  # Qué tan variable es el tono

    # Evolución temporal
    tone_trend: str = "stable"  # improving, deteriorating, stable, volatile
    first_interaction_chapter: int = 0
    last_interaction_chapter: int = 0

    # Asimetría
    initiations_by_entity1: int = 0
    initiations_by_entity2: int = 0
    asymmetry_ratio: float = 0.5  # 0.5 = equilibrado, <0.5 = e1 inicia más, >0.5 = e2

    # Alertas potenciales
    has_sudden_changes: bool = False
    has_tone_mismatch: bool = False

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "entity1_id": self.entity1_id,
            "entity2_id": self.entity2_id,
            "entity1_name": self.entity1_name,
            "entity2_name": self.entity2_name,
            "total_interactions": self.total_interactions,
            "interactions_by_type": self.interactions_by_type,
            "interactions_by_tone": self.interactions_by_tone,
            "average_tone": self.average_tone.value,
            "average_sentiment_score": self.average_sentiment_score,
            "tone_variance": self.tone_variance,
            "tone_trend": self.tone_trend,
            "first_interaction_chapter": self.first_interaction_chapter,
            "last_interaction_chapter": self.last_interaction_chapter,
            "initiations_by_entity1": self.initiations_by_entity1,
            "initiations_by_entity2": self.initiations_by_entity2,
            "asymmetry_ratio": self.asymmetry_ratio,
            "has_sudden_changes": self.has_sudden_changes,
            "has_tone_mismatch": self.has_tone_mismatch,
        }


@dataclass
class InteractionAlert:
    """Alerta generada por análisis de interacciones."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    code: str = ""
    alert_type: str = ""  # Tipo legible
    severity: str = "info"  # error, warning, info

    # Entidades
    entity1_name: str = ""
    entity2_name: str = ""
    relationship_type: str = ""

    # Interacción problemática
    interaction_id: Optional[str] = None
    chapter: int = 0
    text_excerpt: str = ""

    # Contexto
    detected_tone: str = ""
    expected_tones: list = field(default_factory=list)

    # Explicación
    explanation: str = ""
    suggestion: str = ""

    # Metadatos
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "code": self.code,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "entity1_name": self.entity1_name,
            "entity2_name": self.entity2_name,
            "relationship_type": self.relationship_type,
            "interaction_id": self.interaction_id,
            "chapter": self.chapter,
            "text_excerpt": self.text_excerpt,
            "detected_tone": self.detected_tone,
            "expected_tones": self.expected_tones,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


# Mapeo de tipos de interacción a intensidad base
INTERACTION_TYPE_INTENSITY = {
    InteractionType.DIALOGUE: 0.5,
    InteractionType.ACTION_TOWARDS: 0.7,
    InteractionType.THOUGHT_ABOUT: 0.3,
    InteractionType.OBSERVATION: 0.2,
    InteractionType.PHYSICAL_CONTACT: 0.8,
    InteractionType.GIFT_EXCHANGE: 0.6,
    InteractionType.MENTION: 0.2,
    InteractionType.REACTION: 0.6,
}

# Verbos que indican tipos de interacción
DIALOGUE_VERBS = [
    "dijo", "respondió", "preguntó", "exclamó", "susurró", "gritó",
    "murmuró", "contestó", "añadió", "interrumpió", "declaró",
]

ACTION_VERBS_POSITIVE = [
    "abrazó", "besó", "acarició", "ayudó", "protegió", "salvó",
    "defendió", "cuidó", "consoló", "animó", "apoyó",
]

ACTION_VERBS_NEGATIVE = [
    "golpeó", "atacó", "empujó", "insultó", "amenazó", "hirió",
    "traicionó", "abandonó", "ignoró", "rechazó", "humilló",
]

ACTION_VERBS_NEUTRAL = [
    "miró", "observó", "siguió", "esperó", "encontró", "buscó",
    "llamó", "tocó", "cogió", "dejó",
]

THOUGHT_VERBS = [
    "pensó", "recordó", "imaginó", "soñó", "creyó", "dudó",
    "temió", "esperó", "deseó", "planeó",
]

PHYSICAL_CONTACT_VERBS = [
    "abrazó", "besó", "golpeó", "empujó", "acarició", "tocó",
    "cogió", "sujetó", "soltó", "arrastró",
]
