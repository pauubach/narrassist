"""
Modelos de datos para relaciones entre entidades narrativas.

Soporta relaciones entre cualquier tipo de entidad:
- PERSON ↔ PERSON: familia, amistad, enemistad, amor
- PERSON ↔ PLACE: vive_en, teme, frecuenta
- PERSON ↔ OBJECT: posee, desea, teme
- PERSON ↔ ORGANIZATION: miembro_de, trabaja_para
- Etc.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RelationCategory(Enum):
    """Categorías de relaciones."""
    FAMILY = "family"              # Relaciones familiares
    SOCIAL = "social"              # Amistad, enemistad, conocidos
    ROMANTIC = "romantic"          # Amor, pareja, ex
    PROFESSIONAL = "professional"  # Trabajo, jefe, empleado
    OWNERSHIP = "ownership"        # Posesión, pertenencia
    EMOTIONAL = "emotional"        # Miedo, odio, admiración
    SPATIAL = "spatial"            # Vive en, está en, trabaja en
    MEMBERSHIP = "membership"      # Miembro de, fundador de
    SUPERNATURAL = "supernatural"  # Maldito por, bendecido por
    OTHER = "other"


class RelationType(Enum):
    """Tipos específicos de relación."""
    # Familia
    PARENT = "parent"              # X es padre/madre de Y
    CHILD = "child"                # X es hijo/a de Y
    SIBLING = "sibling"            # X es hermano/a de Y
    SPOUSE = "spouse"              # X es esposo/a de Y
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    UNCLE_AUNT = "uncle_aunt"
    NEPHEW_NIECE = "nephew_niece"
    COUSIN = "cousin"

    # Social
    FRIEND = "friend"
    ENEMY = "enemy"
    RIVAL = "rival"
    ACQUAINTANCE = "acquaintance"
    ALLY = "ally"
    MENTOR = "mentor"
    STUDENT = "student"

    # Romántico
    LOVER = "lover"
    EX_LOVER = "ex_lover"
    ADMIRER = "admirer"
    UNREQUITED_LOVE = "unrequited_love"

    # Profesional
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    COLLEAGUE = "colleague"
    SUBORDINATE = "subordinate"
    SUPERIOR = "superior"

    # Posesión
    OWNS = "owns"
    OWNED_BY = "owned_by"
    CREATED = "created"
    CREATED_BY = "created_by"
    DESIRES = "desires"

    # Emocional
    FEARS = "fears"
    FEARED_BY = "feared_by"
    HATES = "hates"
    HATED_BY = "hated_by"
    ADMIRES = "admires"
    ADMIRED_BY = "admired_by"
    TRUSTS = "trusts"
    DISTRUSTS = "distrusts"

    # Espacial
    LIVES_IN = "lives_in"
    WORKS_IN = "works_in"
    BORN_IN = "born_in"
    DIED_IN = "died_in"
    FREQUENTS = "frequents"
    AVOIDS = "avoids"
    LOCATED_IN = "located_in"
    NEAR = "near"
    PART_OF = "part_of"

    # Membresía
    MEMBER_OF = "member_of"
    FOUNDER_OF = "founder_of"
    LEADER_OF = "leader_of"
    PERSECUTED_BY = "persecuted_by"
    PROTECTED_BY = "protected_by"

    # Sobrenatural
    CURSED_BY = "cursed_by"
    BLESSED_BY = "blessed_by"
    BOUND_TO = "bound_to"
    HAUNTED_BY = "haunted_by"

    # Genérico
    ASSOCIATED_WITH = "associated_with"
    UNKNOWN = "unknown"


class RelationValence(Enum):
    """Valencia emocional de la relación."""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2
    FEAR = 3
    DESIRE = 4
    UNKNOWN = 5


# Mapeo de tipos a valencia por defecto
RELATION_TYPE_VALENCE = {
    RelationType.FRIEND: RelationValence.POSITIVE,
    RelationType.ENEMY: RelationValence.VERY_NEGATIVE,
    RelationType.RIVAL: RelationValence.NEGATIVE,
    RelationType.LOVER: RelationValence.VERY_POSITIVE,
    RelationType.EX_LOVER: RelationValence.NEGATIVE,
    RelationType.FEARS: RelationValence.FEAR,
    RelationType.HATES: RelationValence.VERY_NEGATIVE,
    RelationType.ADMIRES: RelationValence.POSITIVE,
    RelationType.TRUSTS: RelationValence.POSITIVE,
    RelationType.DISTRUSTS: RelationValence.NEGATIVE,
    RelationType.DESIRES: RelationValence.DESIRE,
    RelationType.AVOIDS: RelationValence.NEGATIVE,
    RelationType.CURSED_BY: RelationValence.VERY_NEGATIVE,
    RelationType.BLESSED_BY: RelationValence.VERY_POSITIVE,
    RelationType.ALLY: RelationValence.POSITIVE,
    RelationType.MENTOR: RelationValence.POSITIVE,
    RelationType.PARENT: RelationValence.POSITIVE,
    RelationType.CHILD: RelationValence.POSITIVE,
    RelationType.SIBLING: RelationValence.NEUTRAL,
    RelationType.SPOUSE: RelationValence.POSITIVE,
}

# Relaciones inversas
INVERSE_RELATIONS = {
    RelationType.PARENT: RelationType.CHILD,
    RelationType.CHILD: RelationType.PARENT,
    RelationType.OWNS: RelationType.OWNED_BY,
    RelationType.OWNED_BY: RelationType.OWNS,
    RelationType.CREATED: RelationType.CREATED_BY,
    RelationType.CREATED_BY: RelationType.CREATED,
    RelationType.FEARS: RelationType.FEARED_BY,
    RelationType.FEARED_BY: RelationType.FEARS,
    RelationType.HATES: RelationType.HATED_BY,
    RelationType.HATED_BY: RelationType.HATES,
    RelationType.ADMIRES: RelationType.ADMIRED_BY,
    RelationType.ADMIRED_BY: RelationType.ADMIRES,
    RelationType.EMPLOYER: RelationType.EMPLOYEE,
    RelationType.EMPLOYEE: RelationType.EMPLOYER,
    RelationType.SUPERIOR: RelationType.SUBORDINATE,
    RelationType.SUBORDINATE: RelationType.SUPERIOR,
    RelationType.MENTOR: RelationType.STUDENT,
    RelationType.STUDENT: RelationType.MENTOR,
    RelationType.GRANDPARENT: RelationType.GRANDCHILD,
    RelationType.GRANDCHILD: RelationType.GRANDPARENT,
    RelationType.UNCLE_AUNT: RelationType.NEPHEW_NIECE,
    RelationType.NEPHEW_NIECE: RelationType.UNCLE_AUNT,
    RelationType.PERSECUTED_BY: RelationType.UNKNOWN,
    RelationType.PROTECTED_BY: RelationType.UNKNOWN,
}

# Relaciones simétricas (bidireccionales)
SYMMETRIC_RELATIONS = {
    RelationType.FRIEND,
    RelationType.ENEMY,
    RelationType.RIVAL,
    RelationType.SIBLING,
    RelationType.SPOUSE,
    RelationType.COLLEAGUE,
    RelationType.ACQUAINTANCE,
    RelationType.ALLY,
    RelationType.COUSIN,
    RelationType.NEAR,
    RelationType.ASSOCIATED_WITH,
}


@dataclass
class TextReference:
    """Referencia precisa a ubicación en el texto."""
    chapter: int
    chapter_title: Optional[str] = None
    page: Optional[int] = None
    paragraph: Optional[int] = None
    sentence: Optional[int] = None
    char_start: int = 0
    char_end: int = 0

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "chapter": self.chapter,
            "chapter_title": self.chapter_title,
            "page": self.page,
            "paragraph": self.paragraph,
            "sentence": self.sentence,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TextReference":
        """Crea desde diccionario."""
        return cls(
            chapter=data.get("chapter", 0),
            chapter_title=data.get("chapter_title"),
            page=data.get("page"),
            paragraph=data.get("paragraph"),
            sentence=data.get("sentence"),
            char_start=data.get("char_start", 0),
            char_end=data.get("char_end", 0),
        )


@dataclass
class RelationshipEvidence:
    """Evidencia textual de una relación."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    relationship_id: str = ""
    text: str = ""
    reference: Optional[TextReference] = None
    behavior_type: str = "other"  # expected, forbidden, consequence, other
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "relationship_id": self.relationship_id,
            "text": self.text,
            "reference": self.reference.to_dict() if self.reference else None,
            "behavior_type": self.behavior_type,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class InferredExpectations:
    """Expectativas inferidas por IA para una relación."""
    expected_behaviors: list[str] = field(default_factory=list)
    forbidden_behaviors: list[str] = field(default_factory=list)
    expected_consequences: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    inference_source: str = "rule_based"  # local_llm, api, rule_based

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "expected_behaviors": self.expected_behaviors,
            "forbidden_behaviors": self.forbidden_behaviors,
            "expected_consequences": self.expected_consequences,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "inference_source": self.inference_source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InferredExpectations":
        """Crea desde diccionario."""
        return cls(
            expected_behaviors=data.get("expected_behaviors", []),
            forbidden_behaviors=data.get("forbidden_behaviors", []),
            expected_consequences=data.get("expected_consequences", []),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", ""),
            inference_source=data.get("inference_source", "rule_based"),
        )


@dataclass
class RelationshipType:
    """
    Tipo de relación extraído automáticamente del texto.
    Define categoría, valencia y expectativas de comportamiento.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: int = 0
    name: str = ""
    description: str = ""

    # Clasificación
    relation_type: RelationType = RelationType.UNKNOWN
    category: RelationCategory = RelationCategory.OTHER
    source_entity_types: list[str] = field(default_factory=lambda: ["PERSON"])
    target_entity_types: list[str] = field(default_factory=lambda: ["PERSON"])

    # Valencia
    default_valence: RelationValence = RelationValence.NEUTRAL
    is_bidirectional: bool = False
    inverse_type_id: Optional[str] = None

    # Expectativas (inferidas o definidas)
    expectations: Optional[InferredExpectations] = None

    # Metadatos
    created_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "pattern"  # pattern, dependency, cooccurrence, llm_inference
    confidence: float = 0.5
    user_confirmed: bool = False
    user_rejected: bool = False

    def __post_init__(self):
        """Inicializa valencia por defecto si no se especificó."""
        if self.default_valence == RelationValence.NEUTRAL:
            self.default_valence = RELATION_TYPE_VALENCE.get(
                self.relation_type, RelationValence.NEUTRAL
            )
        if self.relation_type in SYMMETRIC_RELATIONS:
            self.is_bidirectional = True

    def get_expectations(self) -> Optional[InferredExpectations]:
        """Obtiene expectativas, creándolas desde reglas si no existen."""
        if self.expectations:
            return self.expectations

        # Generar expectativas básicas desde reglas
        return self._generate_rule_based_expectations()

    def _generate_rule_based_expectations(self) -> InferredExpectations:
        """Genera expectativas basadas en reglas para el tipo de relación."""
        expected = []
        forbidden = []
        consequences = []

        rt = self.relation_type

        # Expectativas por tipo de relación
        if rt == RelationType.FRIEND:
            expected = ["ayuda", "apoya", "defiende", "comparte", "confía"]
            forbidden = ["traiciona", "ataca", "ignora", "desprecia"]

        elif rt == RelationType.ENEMY:
            expected = ["evita", "confronta", "desconfía", "critica"]
            forbidden = ["ayuda desinteresadamente", "confía ciegamente", "defiende"]

        elif rt == RelationType.LOVER:
            expected = ["protege", "apoya", "busca", "extraña"]
            forbidden = ["traiciona", "ignora", "abandona sin explicación"]

        elif rt == RelationType.FEARS:
            expected = ["evita", "huye", "tiembla", "palidece", "nervioso"]
            forbidden = ["se acerca tranquilamente", "abraza", "disfruta"]
            consequences = ["ansiedad", "pesadillas", "parálisis"]

        elif rt == RelationType.PARENT:
            expected = ["protege", "cuida", "aconseja", "preocupa"]
            forbidden = ["abandona sin razón", "ignora peligro"]

        elif rt == RelationType.MENTOR:
            expected = ["enseña", "guía", "corrige", "apoya"]
            forbidden = ["abandona", "sabotea", "engaña"]

        elif rt == RelationType.CURSED_BY:
            expected = ["sufre", "busca liberarse", "teme al objeto"]
            consequences = ["desgracia", "mala suerte", "dolor"]

        elif rt == RelationType.OWNS:
            expected = ["protege", "usa", "cuida"]
            forbidden = ["destruye sin razón", "olvida completamente"]

        elif rt == RelationType.AVOIDS:
            expected = ["rodea", "no menciona", "cambia de tema"]
            forbidden = ["visita voluntariamente", "disfruta del lugar"]

        return InferredExpectations(
            expected_behaviors=expected,
            forbidden_behaviors=forbidden,
            expected_consequences=consequences,
            confidence=0.6,
            reasoning=f"Expectativas basadas en reglas para relación tipo {rt.value}",
            inference_source="rule_based",
        )

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "relation_type": self.relation_type.value,
            "category": self.category.value,
            "source_entity_types": self.source_entity_types,
            "target_entity_types": self.target_entity_types,
            "default_valence": self.default_valence.value,
            "is_bidirectional": self.is_bidirectional,
            "inverse_type_id": self.inverse_type_id,
            "expectations": self.expectations.to_dict() if self.expectations else None,
            "created_at": self.created_at.isoformat(),
            "extraction_source": self.extraction_source,
            "confidence": self.confidence,
            "user_confirmed": self.user_confirmed,
            "user_rejected": self.user_rejected,
        }


@dataclass
class EntityRelationship:
    """Relación entre dos entidades específicas."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: int = 0
    source_entity_id: str = ""
    target_entity_id: str = ""
    source_entity_name: str = ""
    target_entity_name: str = ""

    # Tipo de relación
    relation_type: RelationType = RelationType.UNKNOWN
    relationship_type_id: Optional[str] = None  # FK a RelationshipType si existe

    # Metadatos
    bidirectional: bool = False
    intensity: float = 0.5  # 0.0 (débil) a 1.0 (fuerte)
    sentiment: float = 0.0  # -1.0 (negativo) a 1.0 (positivo)

    # Temporalidad
    first_mention_chapter: Optional[int] = None
    last_mention_chapter: Optional[int] = None
    is_active: bool = True

    # Evidencia
    evidence: list[RelationshipEvidence] = field(default_factory=list)
    evidence_texts: list[str] = field(default_factory=list)
    confidence: float = 0.5

    # Expectativas inferidas
    expectations: Optional[InferredExpectations] = None

    # Auditoría
    created_at: datetime = field(default_factory=datetime.now)
    user_confirmed: bool = False
    user_rejected: bool = False

    def __post_init__(self):
        """Ajusta bidireccionalidad según tipo."""
        if self.relation_type in SYMMETRIC_RELATIONS:
            self.bidirectional = True

    def get_valence(self) -> RelationValence:
        """Obtiene la valencia de la relación."""
        return RELATION_TYPE_VALENCE.get(self.relation_type, RelationValence.NEUTRAL)

    def get_inverse_type(self) -> Optional[RelationType]:
        """Obtiene el tipo inverso de la relación."""
        return INVERSE_RELATIONS.get(self.relation_type)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "source_entity_name": self.source_entity_name,
            "target_entity_name": self.target_entity_name,
            "relation_type": self.relation_type.value,
            "relationship_type_id": self.relationship_type_id,
            "bidirectional": self.bidirectional,
            "intensity": self.intensity,
            "sentiment": self.sentiment,
            "first_mention_chapter": self.first_mention_chapter,
            "last_mention_chapter": self.last_mention_chapter,
            "is_active": self.is_active,
            "evidence_texts": self.evidence_texts,
            "confidence": self.confidence,
            "expectations": self.expectations.to_dict() if self.expectations else None,
            "created_at": self.created_at.isoformat(),
            "user_confirmed": self.user_confirmed,
            "user_rejected": self.user_rejected,
        }


@dataclass
class RelationshipChange:
    """Cambio en una relación a lo largo de la narrativa."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    relationship_id: str = ""
    chapter: int = 0
    change_type: str = "created"  # created, intensified, weakened, ended, transformed
    old_relation_type: Optional[RelationType] = None
    new_relation_type: Optional[RelationType] = None
    old_intensity: Optional[float] = None
    new_intensity: Optional[float] = None
    trigger_text: str = ""
    reference: Optional[TextReference] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "relationship_id": self.relationship_id,
            "chapter": self.chapter,
            "change_type": self.change_type,
            "old_relation_type": self.old_relation_type.value if self.old_relation_type else None,
            "new_relation_type": self.new_relation_type.value if self.new_relation_type else None,
            "old_intensity": self.old_intensity,
            "new_intensity": self.new_intensity,
            "trigger_text": self.trigger_text,
            "reference": self.reference.to_dict() if self.reference else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EntityContext:
    """Contexto conocido de una entidad para inferencia de expectativas."""
    entity_id: str = ""
    entity_name: str = ""
    entity_type: str = "PERSON"
    attributes: list[dict] = field(default_factory=list)
    relationships: list["EntityRelationship"] = field(default_factory=list)
    mentions_summary: str = ""
    personality_traits: list[str] = field(default_factory=list)
    backstory_facts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "mentions_summary": self.mentions_summary,
            "personality_traits": self.personality_traits,
            "backstory_facts": self.backstory_facts,
        }


@dataclass
class CoherenceAlert:
    """Alerta de inconsistencia relacional con referencias precisas."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    code: str = ""
    alert_type: str = ""  # Tipo legible para el editor
    severity: str = "warning"  # error, warning, info

    # Entidades involucradas
    source_entity: str = ""
    target_entity: str = ""
    relationship_type: str = ""

    # Referencia donde se establece la relación/expectativa
    establishing_reference: Optional[TextReference] = None
    establishing_quote: str = ""

    # Referencia donde se contradice
    contradicting_reference: Optional[TextReference] = None
    contradicting_quote: str = ""

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
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "establishing_reference": (
                self.establishing_reference.to_dict()
                if self.establishing_reference else None
            ),
            "establishing_quote": self.establishing_quote,
            "contradicting_reference": (
                self.contradicting_reference.to_dict()
                if self.contradicting_reference else None
            ),
            "contradicting_quote": self.contradicting_quote,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
