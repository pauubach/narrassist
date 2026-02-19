"""
Análisis de conocimiento entre personajes.

Detecta y analiza:
1. Menciones dirigidas: A menciona/habla de B
2. Conocimiento: qué sabe A sobre B (atributos, hechos)
3. Opiniones: qué piensa A de B (positivo/negativo/neutro)
4. Intenciones: qué quiere A respecto a B/objeto
5. Asimetrías: A sabe más de B que B de A

Fuentes de información:
- Diálogos: lo que dice el personaje
- Pensamientos: narración en primera persona o estilo indirecto libre
- Acciones: comportamiento que revela conocimiento/intención
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MentionType(Enum):
    """Tipo de mención de una entidad sobre otra."""

    DIALOGUE = "dialogue"  # En diálogo directo
    THOUGHT = "thought"  # Pensamiento/monólogo interno
    NARRATION = "narration"  # Narración describe que A piensa en B
    ACTION = "action"  # Acción que implica conocimiento


class KnowledgeType(Enum):
    """Tipo de conocimiento que A tiene sobre B."""

    EXISTENCE = "existence"  # Sabe que existe
    IDENTITY = "identity"  # Sabe quién es (nombre, rol)
    ATTRIBUTE = "attribute"  # Conoce atributo (físico, psicológico)
    LOCATION = "location"  # Sabe dónde está
    RELATIONSHIP = "relationship"  # Sabe relación con tercero
    SECRET = "secret"  # Conoce un secreto
    HISTORY = "history"  # Conoce su pasado
    INTENTION = "intention"  # Conoce intenciones de B


class OpinionValence(Enum):
    """Valencia de la opinión."""

    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2
    AMBIVALENT = 3  # Sentimientos mezclados
    UNKNOWN = 4


class IntentionType(Enum):
    """Tipo de intención de A respecto a B."""

    # Positivas
    HELP = "help"  # Quiere ayudar
    PROTECT = "protect"  # Quiere proteger
    BEFRIEND = "befriend"  # Quiere ser amigo
    LOVE = "love"  # Quiere relación romántica
    COLLABORATE = "collaborate"  # Quiere colaborar

    # Negativas
    HARM = "harm"  # Quiere dañar
    DECEIVE = "deceive"  # Quiere engañar
    AVOID = "avoid"  # Quiere evitar
    COMPETE = "compete"  # Quiere competir/vencer
    REVENGE = "revenge"  # Quiere vengarse

    # Neutras/Transaccionales
    OBTAIN = "obtain"  # Quiere obtener algo (objeto)
    LEARN = "learn"  # Quiere aprender/saber
    USE = "use"  # Quiere usar (objeto/persona)
    FIND = "find"  # Quiere encontrar
    UNKNOWN = "unknown"


class KnowledgeExtractionMode(Enum):
    """Modo de extracción de conocimiento."""

    RULES = "rules"  # Patrones regex + spaCy dependency (rápido, ~70% precisión)
    LLM = "llm"  # Ollama local (lento, ~90% precisión)
    HYBRID = "hybrid"  # Rules primero, LLM para casos ambiguos


@dataclass
class DirectedMention:
    """
    Mención dirigida: A menciona/habla de B.

    Captura el contexto donde un personaje habla, piensa o
    actúa en relación a otra entidad.
    """

    id: int | None = None
    project_id: int = 0

    # Quién menciona a quién
    source_entity_id: int = 0  # A (quien menciona)
    target_entity_id: int = 0  # B (mencionado)
    source_name: str = ""
    target_name: str = ""

    # Tipo y contexto
    mention_type: MentionType = MentionType.NARRATION
    chapter: int = 0
    scene: int | None = None

    # Ubicación en texto
    start_char: int = 0
    end_char: int = 0

    # Contenido
    text_excerpt: str = ""  # Extracto del texto
    speaker_text: str = ""  # Lo que dice/piensa A (si aplica)

    # Análisis
    sentiment_score: float = 0.0  # -1.0 a 1.0
    confidence: float = 0.5

    # Metadatos
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "source_name": self.source_name,
            "target_name": self.target_name,
            "mention_type": self.mention_type.value,
            "chapter": self.chapter,
            "text_excerpt": self.text_excerpt,
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence,
        }


@dataclass
class KnowledgeFact:
    """
    Hecho que A conoce sobre B.

    Representa un pedazo de información que un personaje
    tiene sobre otra entidad.
    """

    id: int | None = None
    project_id: int = 0

    # Quién sabe qué de quién
    knower_entity_id: int = 0  # A (quien sabe)
    known_entity_id: int = 0  # B (sobre quien se sabe)
    knower_name: str = ""
    known_name: str = ""

    # El conocimiento
    knowledge_type: KnowledgeType = KnowledgeType.EXISTENCE
    fact_description: str = ""  # Descripción del hecho
    fact_value: str = ""  # Valor específico (ej: "ojos azules")

    # Cómo lo supo
    source_chapter: int = 0  # Capítulo donde lo aprendió
    source_position: int = 0  # Posición en caracteres dentro del capítulo
    source_mention_id: int | None = None  # Mención donde se evidencia
    learned_how: str = ""  # "told", "observed", "deduced", "overheard"

    # Veracidad
    is_accurate: bool | None = None  # True si el conocimiento es correcto
    actual_value: str | None = None  # Valor real (si difiere)

    # Metadatos
    confidence: float = 0.5
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knower_entity_id": self.knower_entity_id,
            "known_entity_id": self.known_entity_id,
            "knower_name": self.knower_name,
            "known_name": self.known_name,
            "knowledge_type": self.knowledge_type.value,
            "fact_description": self.fact_description,
            "fact_value": self.fact_value,
            "source_chapter": self.source_chapter,
            "is_accurate": self.is_accurate,
            "confidence": self.confidence,
        }


@dataclass
class Opinion:
    """
    Opinión que A tiene de B.

    Representa la valoración emocional/evaluativa de un personaje
    sobre otra entidad.
    """

    id: int | None = None
    project_id: int = 0

    # Quién opina de quién
    holder_entity_id: int = 0  # A (quien opina)
    target_entity_id: int = 0  # B (sobre quien se opina)
    holder_name: str = ""
    target_name: str = ""

    # La opinión
    valence: OpinionValence = OpinionValence.UNKNOWN
    opinion_summary: str = ""  # Resumen de la opinión
    opinion_aspects: list[str] = field(default_factory=list)  # Aspectos específicos

    # Evidencia
    evidence_chapters: list[int] = field(default_factory=list)
    evidence_excerpts: list[str] = field(default_factory=list)

    # Evolución
    initial_valence: OpinionValence | None = None  # Opinión inicial
    changed_at_chapter: int | None = None  # Cuándo cambió

    # Metadatos
    confidence: float = 0.5
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "holder_entity_id": self.holder_entity_id,
            "target_entity_id": self.target_entity_id,
            "holder_name": self.holder_name,
            "target_name": self.target_name,
            "valence": self.valence.value
            if isinstance(self.valence, OpinionValence)
            else self.valence,
            "opinion_summary": self.opinion_summary,
            "opinion_aspects": self.opinion_aspects,
            "evidence_chapters": self.evidence_chapters,
            "confidence": self.confidence,
        }


@dataclass
class Intention:
    """
    Intención de A respecto a B (persona u objeto).

    Representa lo que un personaje quiere hacer/conseguir
    respecto a otra entidad.
    """

    id: int | None = None
    project_id: int = 0

    # Quién quiere qué respecto a quién
    agent_entity_id: int = 0  # A (quien tiene la intención)
    target_entity_id: int = 0  # B (objetivo de la intención)
    agent_name: str = ""
    target_name: str = ""

    # La intención
    intention_type: IntentionType = IntentionType.UNKNOWN
    intention_description: str = ""  # Descripción detallada
    motivation: str = ""  # Por qué quiere esto

    # Estado
    is_active: bool = True  # Si la intención sigue vigente
    is_fulfilled: bool = False  # Si se cumplió
    is_abandoned: bool = False  # Si se abandonó

    # Temporalidad
    first_evidence_chapter: int = 0
    last_evidence_chapter: int | None = None
    fulfilled_chapter: int | None = None

    # Evidencia
    evidence_excerpts: list[str] = field(default_factory=list)

    # Metadatos
    confidence: float = 0.5
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_entity_id": self.agent_entity_id,
            "target_entity_id": self.target_entity_id,
            "agent_name": self.agent_name,
            "target_name": self.target_name,
            "intention_type": self.intention_type.value,
            "intention_description": self.intention_description,
            "motivation": self.motivation,
            "is_active": self.is_active,
            "is_fulfilled": self.is_fulfilled,
            "confidence": self.confidence,
        }


@dataclass
class KnowledgeAsymmetryReport:
    """
    Reporte de asimetría de conocimiento entre dos personajes.

    Compara qué sabe A de B vs qué sabe B de A.
    """

    entity_a_id: int
    entity_b_id: int
    entity_a_name: str
    entity_b_name: str

    # Conocimiento de A sobre B
    a_knows_about_b: list[KnowledgeFact] = field(default_factory=list)
    a_opinion_of_b: Opinion | None = None
    a_intentions_toward_b: list[Intention] = field(default_factory=list)
    a_mentions_b_count: int = 0

    # Conocimiento de B sobre A
    b_knows_about_a: list[KnowledgeFact] = field(default_factory=list)
    b_opinion_of_a: Opinion | None = None
    b_intentions_toward_a: list[Intention] = field(default_factory=list)
    b_mentions_a_count: int = 0

    # Score de asimetría (-1 a 1)
    # >0: A sabe más de B
    # <0: B sabe más de A
    # =0: equilibrado
    knowledge_asymmetry_score: float = 0.0
    opinion_asymmetry_score: float = 0.0

    # Alertas potenciales
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entity_a_id": self.entity_a_id,
            "entity_b_id": self.entity_b_id,
            "entity_a_name": self.entity_a_name,
            "entity_b_name": self.entity_b_name,
            "a_knows_about_b": [k.to_dict() for k in self.a_knows_about_b],
            "a_opinion_of_b": self.a_opinion_of_b.to_dict() if self.a_opinion_of_b else None,
            "a_mentions_b_count": self.a_mentions_b_count,
            "b_knows_about_a": [k.to_dict() for k in self.b_knows_about_a],
            "b_opinion_of_a": self.b_opinion_of_a.to_dict() if self.b_opinion_of_a else None,
            "b_mentions_a_count": self.b_mentions_a_count,
            "knowledge_asymmetry_score": self.knowledge_asymmetry_score,
            "opinion_asymmetry_score": self.opinion_asymmetry_score,
            "alerts": self.alerts,
        }


class CharacterKnowledgeAnalyzer:
    """
    Analizador de conocimiento entre personajes.

    Detecta menciones dirigidas, conocimiento, opiniones e intenciones
    a partir de diálogos, pensamientos y narración.
    """

    # Patrones para detectar pensamiento/conocimiento
    THOUGHT_PATTERNS = [
        r"(?P<name>\w+)\s+(pensó|pensaba|sabía|recordó|recordaba)\s+que",
        r"(?P<name>\w+)\s+(se preguntó|se preguntaba)\s+si",
        r"(?P<name>\w+)\s+(creía|sospechaba|intuía)\s+que",
        r"para\s+(?P<name>\w+),?\s+(?P<target>\w+)\s+(era|parecía)",
    ]

    # Patrones de pensamiento implícito: "A pensó en la X de B" (sin cláusula 'que')
    # Capturan relaciones de conocimiento cuando un personaje reflexiona sobre
    # algo que pertenece a o está asociado con otro personaje.
    IMPLICIT_THOUGHT_PATTERNS = [
        # "Name pensó/reflexionó en la oferta/propuesta/invitación de Target"
        (
            r"(?P<knower>\w+)\s+(?:pensó|pensaba|reflexionó|reflexionaba|meditó|meditaba|caviló|cavilaba)\s+(?:en|sobre)\s+(?:la|el|los|las)\s+(?P<fact>\w+(?:\s+\w+)?)\s+de\s+(?P<known>\w+)",
            KnowledgeType.ATTRIBUTE,
            "thought",
        ),
        # "Name consideraba/sopesaba la X de Target"
        (
            r"(?P<knower>\w+)\s+(?:consideraba|consideró|sopesaba|sopesó|evaluaba|evaluó|valoraba|valoró)\s+(?:la|el|los|las)\s+(?P<fact>\w+(?:\s+\w+)?)\s+de\s+(?P<known>\w+)",
            KnowledgeType.ATTRIBUTE,
            "thought",
        ),
        # "Name tenía en mente la X de Target"
        (
            r"(?P<knower>\w+)\s+(?:tenía\s+en\s+mente|no\s+podía\s+(?:dejar\s+de\s+pensar|olvidar))\s+(?:la|el|los|las)?\s*(?P<fact>\w+(?:\s+\w+)?)\s+de\s+(?P<known>\w+)",
            KnowledgeType.ATTRIBUTE,
            "thought",
        ),
        # "Name recordó/evocó la X de Target" (sin 'que')
        (
            r"(?P<knower>\w+)\s+(?:recordó|evocó|rememoró|recordaba|evocaba)\s+(?:la|el|los|las)\s+(?P<fact>\w+(?:\s+\w+)?)\s+de\s+(?P<known>\w+)",
            KnowledgeType.HISTORY,
            "remembered",
        ),
        # "Name sabía de la existencia/oferta de Target"
        (
            r"(?P<knower>\w+)\s+(?:sabía|conocía)\s+(?:de\s+)?(?:la|el|los|las)\s+(?P<fact>\w+(?:\s+\w+)?)\s+de\s+(?P<known>\w+)",
            KnowledgeType.ATTRIBUTE,
            "knew",
        ),
    ]

    # Patrones para detectar opinión
    OPINION_POSITIVE_PATTERNS = [
        r"(?P<name>\w+)\s+(admiraba|respetaba|quería|amaba|adoraba)\s+a\s+(?P<target>\w+)",
        r"(?P<name>\w+)\s+(confiaba|confíaba)\s+en\s+(?P<target>\w+)",
        r"(?P<target>\w+)\s+le\s+(agradaba|caía\s+bien|gustaba)\s+a\s+(?P<name>\w+)",
    ]

    OPINION_NEGATIVE_PATTERNS = [
        r"(?P<name>\w+)\s+(odiaba|detestaba|despreciaba)\s+a\s+(?P<target>\w+)",
        r"(?P<name>\w+)\s+(desconfiaba|temía)\s+(?:a|de)\s+(?P<target>\w+)",
        r"(?P<target>\w+)\s+le\s+(disgustaba|caía\s+mal)\s+a\s+(?P<name>\w+)",
    ]

    # Patrones para detectar intención
    INTENTION_PATTERNS = [
        r"(?P<name>\w+)\s+(quería|deseaba|necesitaba|buscaba)\s+(?P<action>\w+)\s+(?:a\s+)?(?P<target>\w+)",
        r"(?P<name>\w+)\s+(planeaba|pretendía|intentaba)\s+(?P<action>\w+)",
        r"el\s+objetivo\s+de\s+(?P<name>\w+)\s+era\s+(?P<action>.+)",
    ]

    # Verbos que indican intención positiva/negativa
    POSITIVE_INTENTION_VERBS = {
        "ayudar",
        "proteger",
        "salvar",
        "cuidar",
        "apoyar",
        "acompañar",
        "defender",
        "rescatar",
    }

    NEGATIVE_INTENTION_VERBS = {
        "matar",
        "destruir",
        "dañar",
        "herir",
        "engañar",
        "traicionar",
        "robar",
        "vengarse",
        "eliminar",
    }

    OBTAIN_VERBS = {
        "conseguir",
        "obtener",
        "comprar",
        "adquirir",
        "encontrar",
        "recuperar",
        "robar",
        "tomar",
    }

    def __init__(self, project_id: int = 0, entities: Optional[list[dict]] = None):
        self.project_id = project_id

        # Datos extraídos
        self._mentions: list[DirectedMention] = []
        self._knowledge: list[KnowledgeFact] = []
        self._opinions: list[Opinion] = []
        self._intentions: list[Intention] = []

        # Mapeo de nombres a IDs
        self._entity_names: dict[int, str] = {}
        self._name_to_id: dict[str, int] = {}
        self._person_ids: set[int] = set()

        # Registrar entidades si se proporcionan
        if entities:
            for entity in entities:
                self.register_entity(
                    entity["id"],
                    entity["name"],
                    entity.get("aliases", []),
                )

    def register_entity(
        self,
        entity_id: int,
        name: str,
        aliases: Optional[list[str]] = None,
        entity_type: str = "",
    ):
        """Registra una entidad para el análisis."""
        self._entity_names[entity_id] = name
        self._name_to_id[name.lower()] = entity_id

        if entity_type.lower() in ("per", "person", "character"):
            self._person_ids.add(entity_id)

        # Registrar partes del nombre que parezcan nombres propios
        original_parts = name.split()
        if len(original_parts) > 1:
            for part in original_parts:
                # Solo registrar partes que empiezan con mayúscula (nombres propios)
                if len(part) > 2 and part[0].isupper():
                    self._name_to_id.setdefault(part.lower(), entity_id)

        if aliases:
            for alias in aliases:
                self._name_to_id[alias.lower()] = entity_id

    def _resolve_name(self, name: str) -> int | None:
        """Resuelve un nombre a su entity_id, con fallback por substring."""
        if not name:
            return None
        # Búsqueda exacta
        eid = self._name_to_id.get(name)
        if eid:
            return eid
        # Fallback: buscar si name es parte de un nombre registrado
        for registered, rid in self._name_to_id.items():
            if name in registered or registered in name:
                return rid
        return None

    def analyze_dialogue(
        self,
        speaker_id: int,
        dialogue_text: str,
        chapter: int,
        start_char: int,
        context_before: str = "",
    ) -> list[DirectedMention]:
        """
        Analiza un diálogo para detectar menciones de otras entidades.

        Args:
            speaker_id: ID del personaje que habla
            dialogue_text: Texto del diálogo
            chapter: Número de capítulo
            start_char: Posición en el documento
            context_before: Contexto narrativo antes del diálogo

        Returns:
            Lista de menciones detectadas
        """
        mentions = []
        speaker_name = self._entity_names.get(speaker_id, str(speaker_id))

        # Buscar nombres de otras entidades en el diálogo
        for name, entity_id in self._name_to_id.items():
            if entity_id == speaker_id:
                continue  # No contar auto-referencias

            # Buscar mención (case insensitive)
            pattern = rf"\b{re.escape(name)}\b"
            matches = list(re.finditer(pattern, dialogue_text, re.IGNORECASE))

            for match in matches:
                # Analizar sentimiento del contexto
                sentiment = self._analyze_sentiment_around_mention(
                    dialogue_text, match.start(), match.end()
                )

                mention = DirectedMention(
                    project_id=self.project_id,
                    source_entity_id=speaker_id,
                    target_entity_id=entity_id,
                    source_name=speaker_name,
                    target_name=self._entity_names.get(entity_id, name),
                    mention_type=MentionType.DIALOGUE,
                    chapter=chapter,
                    start_char=start_char + match.start(),
                    end_char=start_char + match.end(),
                    text_excerpt=dialogue_text,
                    speaker_text=dialogue_text,
                    sentiment_score=sentiment,
                    confidence=0.8,
                    created_at=datetime.now(),
                )

                mentions.append(mention)
                self._mentions.append(mention)

        return mentions

    def analyze_narration(
        self,
        text: str,
        chapter: int,
        start_char: int,
        extraction_mode: KnowledgeExtractionMode | None = None,
    ) -> tuple[list[DirectedMention], list[KnowledgeFact], list[Opinion]]:
        """
        Analiza narración para detectar pensamientos, conocimiento y opiniones.

        Args:
            text: Texto de narración a analizar
            chapter: Número de capítulo
            start_char: Posición inicial en el documento
            extraction_mode: Modo de extracción de conocimiento (None = auto)

        Returns:
            Tupla de (menciones, hechos de conocimiento, opiniones)
        """
        mentions = []
        opinions = []

        # Extraer hechos de conocimiento
        knowledge = self.extract_knowledge_facts(text, chapter, start_char, extraction_mode)

        # Buscar patrones de pensamiento
        for pattern in self.THOUGHT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                source_name = groups.get("name", "").lower()
                target_name = groups.get("target", "").lower()

                source_id = self._name_to_id.get(source_name)
                target_id = self._name_to_id.get(target_name) if target_name else None

                if source_id:
                    mention = DirectedMention(
                        project_id=self.project_id,
                        source_entity_id=source_id,
                        target_entity_id=target_id or 0,
                        source_name=self._entity_names.get(source_id, source_name),
                        target_name=self._entity_names.get(target_id, target_name)
                        if target_id
                        else "",
                        mention_type=MentionType.THOUGHT,
                        chapter=chapter,
                        start_char=start_char + match.start(),
                        end_char=start_char + match.end(),
                        text_excerpt=text[max(0, match.start() - 50) : match.end() + 50],
                        confidence=0.7,
                        created_at=datetime.now(),
                    )
                    mentions.append(mention)
                    self._mentions.append(mention)

        # Buscar patrones de opinión positiva
        for pattern in self.OPINION_POSITIVE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                holder_name = groups.get("name", "").lower()
                target_name = groups.get("target", "").lower()

                holder_id = self._name_to_id.get(holder_name)
                target_id = self._name_to_id.get(target_name)

                if holder_id and target_id:
                    opinion = Opinion(
                        project_id=self.project_id,
                        holder_entity_id=holder_id,
                        target_entity_id=target_id,
                        holder_name=self._entity_names.get(holder_id, holder_name),
                        target_name=self._entity_names.get(target_id, target_name),
                        valence=OpinionValence.POSITIVE,
                        opinion_summary=match.group(0),
                        evidence_chapters=[chapter],
                        evidence_excerpts=[text[max(0, match.start() - 30) : match.end() + 30]],
                        confidence=0.7,
                        created_at=datetime.now(),
                    )
                    opinions.append(opinion)
                    self._opinions.append(opinion)

        # Buscar patrones de opinión negativa
        for pattern in self.OPINION_NEGATIVE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                holder_name = groups.get("name", "").lower()
                target_name = groups.get("target", "").lower()

                holder_id = self._name_to_id.get(holder_name)
                target_id = self._name_to_id.get(target_name)

                if holder_id and target_id:
                    opinion = Opinion(
                        project_id=self.project_id,
                        holder_entity_id=holder_id,
                        target_entity_id=target_id,
                        holder_name=self._entity_names.get(holder_id, holder_name),
                        target_name=self._entity_names.get(target_id, target_name),
                        valence=OpinionValence.NEGATIVE,
                        opinion_summary=match.group(0),
                        evidence_chapters=[chapter],
                        evidence_excerpts=[text[max(0, match.start() - 30) : match.end() + 30]],
                        confidence=0.7,
                        created_at=datetime.now(),
                    )
                    opinions.append(opinion)
                    self._opinions.append(opinion)

        return mentions, knowledge, opinions

    def analyze_intentions(
        self,
        text: str,
        chapter: int,
        start_char: int,
    ) -> list[Intention]:
        """
        Analiza texto para detectar intenciones de personajes.
        """
        intentions = []

        for pattern in self.INTENTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                agent_name = groups.get("name", "").lower()
                action = groups.get("action", "").lower()
                target_name = groups.get("target", "").lower()

                agent_id = self._name_to_id.get(agent_name)
                target_id = self._name_to_id.get(target_name)

                if not agent_id:
                    continue

                # Determinar tipo de intención
                intention_type = IntentionType.UNKNOWN
                if action in self.POSITIVE_INTENTION_VERBS:
                    intention_type = IntentionType.HELP
                elif action in self.NEGATIVE_INTENTION_VERBS:
                    intention_type = IntentionType.HARM
                elif action in self.OBTAIN_VERBS:
                    intention_type = IntentionType.OBTAIN

                intention = Intention(
                    project_id=self.project_id,
                    agent_entity_id=agent_id,
                    target_entity_id=target_id or 0,
                    agent_name=self._entity_names.get(agent_id, agent_name),
                    target_name=self._entity_names.get(target_id, target_name)
                    if target_id
                    else target_name,
                    intention_type=intention_type,
                    intention_description=match.group(0),
                    first_evidence_chapter=chapter,
                    evidence_excerpts=[text[max(0, match.start() - 30) : match.end() + 30]],
                    confidence=0.6,
                    created_at=datetime.now(),
                )

                intentions.append(intention)
                self._intentions.append(intention)

        return intentions

    def _analyze_sentiment_around_mention(
        self,
        text: str,
        start: int,
        end: int,
        window: int = 50,
    ) -> float:
        """
        Analiza el sentimiento del texto alrededor de una mención.

        Returns:
            Score de -1.0 (muy negativo) a 1.0 (muy positivo)
        """
        # Palabras positivas y negativas en español
        positive_words = {
            "bien",
            "bueno",
            "buena",
            "genial",
            "maravilloso",
            "excelente",
            "fantástico",
            "increíble",
            "amor",
            "cariño",
            "querido",
            "querida",
            "gracias",
            "feliz",
            "alegre",
            "hermoso",
            "hermosa",
            "bello",
            "bella",
            "amigo",
            "amiga",
            "confío",
            "confiar",
            "admirar",
            "admiro",
        }

        negative_words = {
            "mal",
            "malo",
            "mala",
            "terrible",
            "horrible",
            "odio",
            "odiar",
            "detesto",
            "detestar",
            "maldito",
            "maldita",
            "inútil",
            "estúpido",
            "idiota",
            "traidor",
            "traidora",
            "mentiroso",
            "mentirosa",
            "desconfío",
            "desconfiar",
            "temo",
            "temer",
            "miedo",
        }

        # Extraer ventana de texto
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        context = text[context_start:context_end].lower()

        # Contar palabras
        words = re.findall(r"\b\w+\b", context)

        positive_count = sum(1 for w in words if w in positive_words)
        negative_count = sum(1 for w in words if w in negative_words)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        return (positive_count - negative_count) / total

    def get_asymmetry_report(
        self,
        entity_a_id: int,
        entity_b_id: int,
    ) -> KnowledgeAsymmetryReport:
        """
        Genera reporte de asimetría de conocimiento entre dos personajes.
        """
        entity_a_name = self._entity_names.get(entity_a_id, str(entity_a_id))
        entity_b_name = self._entity_names.get(entity_b_id, str(entity_b_id))

        # Filtrar datos relevantes
        a_mentions_b = [
            m
            for m in self._mentions
            if m.source_entity_id == entity_a_id and m.target_entity_id == entity_b_id
        ]
        b_mentions_a = [
            m
            for m in self._mentions
            if m.source_entity_id == entity_b_id and m.target_entity_id == entity_a_id
        ]

        a_knows_b = [
            k
            for k in self._knowledge
            if k.knower_entity_id == entity_a_id and k.known_entity_id == entity_b_id
        ]
        b_knows_a = [
            k
            for k in self._knowledge
            if k.knower_entity_id == entity_b_id and k.known_entity_id == entity_a_id
        ]

        a_opinion_b = next(
            (
                o
                for o in self._opinions
                if o.holder_entity_id == entity_a_id and o.target_entity_id == entity_b_id
            ),
            None,
        )
        b_opinion_a = next(
            (
                o
                for o in self._opinions
                if o.holder_entity_id == entity_b_id and o.target_entity_id == entity_a_id
            ),
            None,
        )

        a_intentions_b = [
            i
            for i in self._intentions
            if i.agent_entity_id == entity_a_id and i.target_entity_id == entity_b_id
        ]
        b_intentions_a = [
            i
            for i in self._intentions
            if i.agent_entity_id == entity_b_id and i.target_entity_id == entity_a_id
        ]

        # Calcular scores de asimetría
        knowledge_score = self._calculate_knowledge_asymmetry(
            len(a_knows_b), len(b_knows_a), len(a_mentions_b), len(b_mentions_a)
        )

        opinion_score = self._calculate_opinion_asymmetry(a_opinion_b, b_opinion_a)

        # Detectar alertas
        alerts = []

        if abs(knowledge_score) > 0.5:
            more_knowledgeable = entity_a_name if knowledge_score > 0 else entity_b_name
            less_knowledgeable = entity_b_name if knowledge_score > 0 else entity_a_name
            alerts.append(
                f"Asimetría de conocimiento: {more_knowledgeable} sabe significativamente "
                f"más sobre {less_knowledgeable} que viceversa"
            )

        if a_opinion_b and b_opinion_a:
            if (a_opinion_b.valence.value > 0 and b_opinion_a.valence.value < 0) or (
                a_opinion_b.valence.value < 0 and b_opinion_a.valence.value > 0
            ):
                alerts.append(
                    f"Opiniones opuestas: {entity_a_name} y {entity_b_name} "
                    f"tienen opiniones contrarias el uno del otro"
                )

        return KnowledgeAsymmetryReport(
            entity_a_id=entity_a_id,
            entity_b_id=entity_b_id,
            entity_a_name=entity_a_name,
            entity_b_name=entity_b_name,
            a_knows_about_b=a_knows_b,
            a_opinion_of_b=a_opinion_b,
            a_intentions_toward_b=a_intentions_b,
            a_mentions_b_count=len(a_mentions_b),
            b_knows_about_a=b_knows_a,
            b_opinion_of_a=b_opinion_a,
            b_intentions_toward_a=b_intentions_a,
            b_mentions_a_count=len(b_mentions_a),
            knowledge_asymmetry_score=knowledge_score,
            opinion_asymmetry_score=opinion_score,
            alerts=alerts,
        )

    def _calculate_knowledge_asymmetry(
        self,
        a_facts: int,
        b_facts: int,
        a_mentions: int,
        b_mentions: int,
    ) -> float:
        """Calcula score de asimetría de conocimiento (-1 a 1)."""
        total_facts = a_facts + b_facts
        total_mentions = a_mentions + b_mentions

        if total_facts == 0 and total_mentions == 0:
            return 0.0

        fact_score = (a_facts - b_facts) / max(total_facts, 1)
        mention_score = (a_mentions - b_mentions) / max(total_mentions, 1)

        # Ponderar más los hechos que las menciones
        return 0.7 * fact_score + 0.3 * mention_score

    def _calculate_opinion_asymmetry(
        self,
        a_opinion: Opinion | None,
        b_opinion: Opinion | None,
    ) -> float:
        """Calcula score de asimetría de opinión (-1 a 1)."""
        if not a_opinion and not b_opinion:
            return 0.0

        a_val = (
            a_opinion.valence.value
            if a_opinion and a_opinion.valence != OpinionValence.UNKNOWN
            else 0
        )
        b_val = (
            b_opinion.valence.value
            if b_opinion and b_opinion.valence != OpinionValence.UNKNOWN
            else 0
        )

        # Normalizar a -1 a 1
        return float(a_val - b_val) / 4  # Max diferencia es 4 (-2 a 2)

    def get_all_mentions(self) -> list[DirectedMention]:
        """Retorna todas las menciones detectadas."""
        return self._mentions

    def get_all_opinions(self) -> list[Opinion]:
        """Retorna todas las opiniones detectadas."""
        return self._opinions

    def get_all_intentions(self) -> list[Intention]:
        """Retorna todas las intenciones detectadas."""
        return self._intentions

    def get_entity_profile(self, entity_id: int) -> dict:
        """
        Genera perfil completo de lo que otros saben/opinan de una entidad.
        """
        entity_name = self._entity_names.get(entity_id, str(entity_id))

        # Quién menciona a esta entidad
        mentioned_by = [m for m in self._mentions if m.target_entity_id == entity_id]

        # Opiniones sobre esta entidad
        opinions_about = [o for o in self._opinions if o.target_entity_id == entity_id]

        # Intenciones hacia esta entidad
        intentions_toward = [i for i in self._intentions if i.target_entity_id == entity_id]

        # Qué menciona/sabe/opina esta entidad
        mentions_others = [m for m in self._mentions if m.source_entity_id == entity_id]
        opinions_of_others = [o for o in self._opinions if o.holder_entity_id == entity_id]
        intentions_of = [i for i in self._intentions if i.agent_entity_id == entity_id]

        return {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "mentioned_by_count": len(mentioned_by),
            "mentioned_by": [
                {"name": m.source_name, "count": 1, "sentiment_avg": m.sentiment_score}
                for m in mentioned_by
            ],
            "opinions_about": [o.to_dict() for o in opinions_about],
            "intentions_toward": [i.to_dict() for i in intentions_toward],
            "mentions_others_count": len(mentions_others),
            "opinions_of_others": [o.to_dict() for o in opinions_of_others],
            "intentions_of": [i.to_dict() for i in intentions_of],
        }

    # =========================================================================
    # Knowledge Fact Extraction
    # =========================================================================

    # Patrones para detectar conocimiento de hechos
    KNOWLEDGE_PATTERNS = [
        # REFERENCIA: "A sabía/conocía que B era/tenía X" (ya lo sabía)
        (
            r"(?P<knower>\w+)\s+(?:sabía|conocía)\s+(?:de\s+)?que\s+(?P<known>\w+)\s+(?:era|tenía|estaba|había)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "knew",
        ),
        # ADQUISICIÓN: "A descubrió/averiguó/se enteró que B era/tenía X"
        (
            r"(?P<knower>\w+)\s+(?:descubrió|averiguó|se\s+enteró)\s+(?:de\s+)?que\s+(?P<known>\w+)\s+(?:era|tenía|estaba|había)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "discovered",
        ),
        # REFERENCIA: "A recordaba que B X"
        (
            r"(?P<knower>\w+)\s+(?:recordaba|recordó)\s+(?:de\s+)?que\s+(?P<known>\w+)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.HISTORY,
            "remembered",
        ),
        # ADQUISICIÓN: "A se dio cuenta de que B X"
        (
            r"(?P<knower>\w+)\s+se\s+dio\s+cuenta\s+de\s+que\s+(?P<known>\w+)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "observed",
        ),
        # ADQUISICIÓN: "A notó/observó que B X"
        (
            r"(?P<knower>\w+)\s+(?:notó|observó|advirtió)\s+que\s+(?P<known>\w+)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "observed",
        ),
        # REFERENCIA: "para A, B era X" (conocimiento implícito/asumido)
        (
            r"para\s+(?P<knower>\w+),?\s+(?P<known>\w+)\s+era\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "assumed",
        ),
        # IGNORANCIA: "A ignoraba/desconocía que B X"
        (
            r"(?P<knower>\w+)\s+(?:ignoraba|desconocía|no\s+sabía)\s+que\s+(?P<known>\w+)\s+(?P<fact>.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "unknown",
        ),
    ]

    # Patrones para detectar que A sabe dónde está B
    LOCATION_PATTERNS = [
        # REFERENCIA: "A sabía dónde vivía B"
        (
            r"(?P<knower>\w+)\s+(?:sabía|conocía)\s+(?P<fact>(?:dónde|donde)\s+(?:estaba|vivía|se encontraba))\s+(?P<known>\w+)",
            KnowledgeType.LOCATION,
            "knew",
        ),
        # ADQUISICIÓN: "A encontró a B en LUGAR"
        (
            r"(?P<knower>\w+)\s+(?:encontró|localizó|halló)\s+a\s+(?P<known>\w+)\s+en\s+(?P<location>.+?)(?:\.|,|;|$)",
            KnowledgeType.LOCATION,
            "observed",
        ),
    ]

    # Patrones para detectar secretos
    SECRET_PATTERNS = [
        # REFERENCIA: "A guardaba/sabía el secreto de B"
        (
            r"(?P<knower>\w+)\s+(?:sabía|conocía|guardaba)\s+el\s+(?P<fact>secreto)\s+de\s+(?P<known>\w+)",
            KnowledgeType.SECRET,
            "knew",
        ),
        # ADQUISICIÓN: "B le confesó/reveló su secreto a A"
        (
            r"(?P<known>\w+)\s+le\s+(?:confesó|reveló|contó)\s+(?:su\s+)?(?P<fact>secreto)\s+a\s+(?P<knower>\w+)",
            KnowledgeType.SECRET,
            "told",
        ),
    ]

    # Patrones para detectar revelaciones (alguien le dice/muestra algo a otro)
    REVELATION_PATTERNS = [
        # "... le contó/dijo/confesó/reveló a KNOWER que KNOWN era/tenía FACT" (3 entidades)
        # e.g. "Ana le contó a Luis que Pedro era ladrón"
        # e.g. "El médico le contó a Ana que Luis estaba enfermo"
        (
            r"le\s+(?:contó|dijo|confesó|reveló)\s+a\s+(?P<knower>\w+)\s+que\s+(?P<known>\w+)\s+(?P<fact>(?:era|tenía|estaba|había)\s+.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "told",
        ),
        # "KNOWN le contó/dijo/confesó/reveló a KNOWER que era/tenía FACT" (2 entidades)
        # e.g. "Pedro le confesó a María que era espía"
        (
            r"(?P<known>\w+)\s+le\s+(?:contó|dijo|confesó|reveló)\s+a\s+(?P<knower>\w+)\s+que\s+(?P<fact>(?:era|tenía|estaba|había)\s+.+?)(?:\.|,|;|$)",
            KnowledgeType.ATTRIBUTE,
            "told",
        ),
        # "KNOWN le mostró FACT a KNOWER"
        # e.g. "Pedro le mostró la cicatriz de su mano a María por primera vez"
        (
            r"(?P<known>\w+)\s+le\s+mostró\s+(?P<fact>.+?)\s+a\s+(?P<knower>\w+)",
            KnowledgeType.ATTRIBUTE,
            "shown",
        ),
        # "KNOWN le dio su dirección/ubicación a KNOWER"
        # e.g. "Elena le dio su dirección a Carlos por teléfono"
        (
            r"(?P<known>\w+)\s+le\s+dio\s+su\s+(?P<fact>dirección|ubicación)\s+a\s+(?P<knower>\w+)",
            KnowledgeType.LOCATION,
            "told",
        ),
        # "—FACT— dijo KNOWN a KNOWER" (revelación en diálogo directo)
        # e.g. "—Soy médico —dijo Juan a María."
        (
            r"—(?P<fact>.+?)\s*—\s*dijo\s+(?P<known>\w+)\s+a\s+(?P<knower>\w+)",
            KnowledgeType.IDENTITY,
            "told",
        ),
    ]

    def _auto_select_mode(self) -> KnowledgeExtractionMode:
        """
        Selecciona automáticamente el modo de extracción según hardware.

        Returns:
            HYBRID si hay GPU/LLM disponible, RULES si solo CPU.
        """
        try:
            from ..core.device import get_device_detector
            from ..llm.client import get_client

            # Verificar si hay LLM disponible
            client = get_client()
            if client and client.is_available():
                detector = get_device_detector()
                device_info = detector.get_info()
                # Si hay GPU, usar HYBRID para mejor calidad
                if device_info.get("cuda_available") or device_info.get("mps_available"):
                    return KnowledgeExtractionMode.HYBRID
                # Si hay LLM pero no GPU, RULES es más rápido
                return KnowledgeExtractionMode.RULES
        except Exception as e:
            logger.debug(f"Error checking device/LLM availability: {e}")

        return KnowledgeExtractionMode.RULES

    def extract_knowledge_facts(
        self,
        text: str,
        chapter: int,
        start_char: int = 0,
        mode: KnowledgeExtractionMode | None = None,
    ) -> list[KnowledgeFact]:
        """
        Extrae hechos de conocimiento del texto.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            start_char: Posición inicial en el documento
            mode: Modo de extracción (None = auto-detectar)

        Returns:
            Lista de hechos de conocimiento extraídos
        """
        if mode is None:
            mode = self._auto_select_mode()

        logger.debug(f"Extracting knowledge facts with mode: {mode.value}")

        if mode == KnowledgeExtractionMode.RULES:
            facts = self._extract_knowledge_facts_rules(text, chapter, start_char)
        elif mode == KnowledgeExtractionMode.LLM:
            facts = self._extract_knowledge_facts_llm(text, chapter, start_char)
        else:  # HYBRID
            # Primero reglas, después LLM para enriquecer
            facts = self._extract_knowledge_facts_rules(text, chapter, start_char)
            if len(facts) < 2:  # Si encontramos poco, usar LLM
                llm_facts = self._extract_knowledge_facts_llm(text, chapter, start_char)
                # Fusionar evitando duplicados
                existing_keys = {
                    (f.knower_entity_id, f.known_entity_id, f.fact_value) for f in facts
                }
                for f in llm_facts:
                    key = (f.knower_entity_id, f.known_entity_id, f.fact_value)
                    if key not in existing_keys:
                        facts.append(f)
                        existing_keys.add(key)

        # Almacenar internamente
        self._knowledge.extend(facts)

        return facts

    def _extract_knowledge_facts_rules(
        self,
        text: str,
        chapter: int,
        start_char: int,
    ) -> list[KnowledgeFact]:
        """
        Extrae hechos usando patrones regex.

        Rápido pero con precisión limitada (~70%).
        """
        facts = []

        all_patterns = (
            self.KNOWLEDGE_PATTERNS
            + self.IMPLICIT_THOUGHT_PATTERNS
            + self.LOCATION_PATTERNS
            + self.SECRET_PATTERNS
            + self.REVELATION_PATTERNS
        )

        for pattern, knowledge_type, learned_how in all_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()

                knower_name = groups.get("knower", "").lower()
                known_name = groups.get("known", "").lower()
                fact_text = groups.get("fact", "") or groups.get("location", "")

                knower_id = self._resolve_name(knower_name)
                known_id = self._resolve_name(known_name)

                if not knower_id or not known_id:
                    continue

                # Limpiar el hecho
                fact_value = fact_text.strip()
                if len(fact_value) > 100:
                    fact_value = fact_value[:100] + "..."

                # Determinar si es conocimiento negado
                is_negated = learned_how == "unknown"

                fact = KnowledgeFact(
                    project_id=self.project_id,
                    knower_entity_id=knower_id,
                    known_entity_id=known_id,
                    knower_name=self._entity_names.get(knower_id, knower_name),
                    known_name=self._entity_names.get(known_id, known_name),
                    knowledge_type=knowledge_type,
                    fact_description=match.group(0)[:200],
                    fact_value=fact_value if not is_negated else f"[NO SABE] {fact_value}",
                    source_chapter=chapter,
                    source_position=start_char + match.start(),
                    learned_how=learned_how,
                    is_accurate=None,  # No podemos verificar sin más contexto
                    confidence=0.65 if not is_negated else 0.7,
                    created_at=datetime.now(),
                )

                facts.append(fact)

        # Detectar presentaciones formales: "Este es [Name]" → adquisición
        # Busca quién es presentado y a quién se le presenta
        introduction_facts = self._extract_introductions(text, chapter, start_char)
        facts.extend(introduction_facts)

        return facts

    def _extract_introductions(
        self,
        text: str,
        chapter: int,
        start_char: int,
    ) -> list[KnowledgeFact]:
        """
        Detecta presentaciones formales donde un personaje conoce a otro.

        Patrones: "Este/Esta es [título] Name", "quiero que conozcas a Name",
        "te presento a Name", etc.

        El 'knower' es quien RECIBE la presentación (la persona a quien se
        le presenta alguien nuevo), no quien la hace.
        """
        facts = []
        # Patrones de presentación
        intro_patterns = [
            re.compile(
                r"[Ee]ste\s+es\s+(?:el\s+)?(?:profesor|doctor|señor|Dr\.)\s+"
                r"(?P<known>[A-ZÁÉÍÓÚÑ]\w+(?:\s+[A-ZÁÉÍÓÚÑ]\w+)?)",
            ),
            re.compile(
                r"(?:quiero|quisiera)\s+que\s+(?:conozcas|conozca)\s+"
                r"(?:a\s+)?(?:el\s+|la\s+)?(?:\w+\s+)?(?P<known>[A-ZÁÉÍÓÚÑ]\w+)",
            ),
            re.compile(
                r"(?:te|le|les)\s+presento\s+a\s+(?:el\s+|la\s+)?"
                r"(?:\w+\s+)?(?P<known>[A-ZÁÉÍÓÚÑ]\w+)",
            ),
        ]

        for pattern in intro_patterns:
            for match in pattern.finditer(text):
                known_name = match.group("known").lower()
                known_id = self._name_to_id.get(known_name)
                if not known_id:
                    for name, eid in self._name_to_id.items():
                        if known_name in name or name in known_name:
                            known_id = eid
                            known_name = name
                            break
                if not known_id:
                    continue

                # Buscar el presenter (quien habla la introducción):
                # "—dijo Name" justo antes del match
                presenter_id = None
                dijo_pattern = re.compile(
                    r"—\s*dijo\s+(?P<speaker>\w+)", re.IGNORECASE
                )
                # Buscar "dijo X" en las 200 chars antes del match
                context_before = text[max(0, match.start() - 200): match.start()]
                for dm in dijo_pattern.finditer(context_before):
                    speaker_name = dm.group("speaker").lower()
                    pid = self._name_to_id.get(speaker_name)
                    if pid and pid != known_id:
                        presenter_id = pid

                # El knower es el personaje más cercano que NO sea
                # el presentado NI el presentador
                best_knower_id = None
                best_dist = float("inf")
                pos = match.start()

                # Buscar en ventana de 500 chars antes de la presentación
                search_window = text[max(0, pos - 500): pos]

                # Usar nombre canónico (case-sensitive) para distinguir
                # nombres propios de adjetivos homónimos
                seen_eids = set()
                for eid, canon_name in self._entity_names.items():
                    if eid in seen_eids or eid in (known_id, presenter_id):
                        continue
                    seen_eids.add(eid)
                    if self._person_ids and eid not in self._person_ids:
                        continue
                    # Case-sensitive: "Elena" sí, "brillante" no
                    for m in re.finditer(rf"\b{re.escape(canon_name)}\b", search_window):
                        dist = len(search_window) - m.end()
                        if 0 < dist < best_dist:
                            best_dist = dist
                            best_knower_id = eid

                if not best_knower_id:
                    continue

                fact = KnowledgeFact(
                    project_id=self.project_id,
                    knower_entity_id=best_knower_id,
                    known_entity_id=known_id,
                    knower_name=self._entity_names.get(best_knower_id, ""),
                    known_name=self._entity_names.get(known_id, known_name),
                    knowledge_type=KnowledgeType.IDENTITY,
                    fact_description=text[max(0, match.start() - 30): match.end() + 30][:200],
                    fact_value="identidad",
                    source_chapter=chapter,
                    source_position=start_char + match.start(),
                    learned_how="told",
                    confidence=0.75,
                    created_at=datetime.now(),
                )
                facts.append(fact)

        return facts

    def _extract_knowledge_facts_llm(
        self,
        text: str,
        chapter: int,
        start_char: int,
    ) -> list[KnowledgeFact]:
        """
        Extrae hechos usando LLM local (Ollama).

        Más lento pero mayor precisión (~90%).
        """
        facts: list = []

        try:
            from ..llm.client import get_client

            client = get_client()
            if not client or not client.is_available():
                logger.debug("LLM not available, skipping LLM extraction")
                return facts

            # Construir lista de personajes para el prompt
            character_names = list(self._entity_names.values())
            if not character_names:
                return facts

            prompt = f"""Analiza el siguiente texto narrativo y extrae qué personajes saben sobre otros personajes.

Personajes conocidos: {", ".join(character_names)}

Texto:
{text[:2000]}

Para cada hecho de conocimiento detectado, responde en formato JSON:
[
  {{"knower": "nombre", "known": "nombre", "fact": "descripción del hecho", "type": "attribute|location|secret|identity|history", "how": "told|observed|deduced"}}
]

Solo incluye hechos explícitos donde un personaje claramente sabe algo sobre otro.
Responde solo con el JSON, sin explicaciones."""

            response = client.generate(prompt, max_tokens=1024, temperature=0.1)

            if not response:
                return facts

            # Parsear respuesta JSON
            import json

            try:
                # Buscar JSON en la respuesta
                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                    for item in extracted:
                        knower_name = item.get("knower", "").lower()
                        known_name = item.get("known", "").lower()

                        knower_id = self._name_to_id.get(knower_name)
                        known_id = self._name_to_id.get(known_name)

                        if not knower_id or not known_id:
                            continue

                        # Mapear tipo
                        type_map = {
                            "attribute": KnowledgeType.ATTRIBUTE,
                            "location": KnowledgeType.LOCATION,
                            "secret": KnowledgeType.SECRET,
                            "identity": KnowledgeType.IDENTITY,
                            "history": KnowledgeType.HISTORY,
                        }
                        knowledge_type = type_map.get(
                            item.get("type", "").lower(), KnowledgeType.ATTRIBUTE
                        )

                        fact = KnowledgeFact(
                            project_id=self.project_id,
                            knower_entity_id=knower_id,
                            known_entity_id=known_id,
                            knower_name=self._entity_names.get(knower_id, knower_name),
                            known_name=self._entity_names.get(known_id, known_name),
                            knowledge_type=knowledge_type,
                            fact_description=item.get("fact", "")[:200],
                            fact_value=item.get("fact", "")[:100],
                            source_chapter=chapter,
                            learned_how=item.get("how", "deduced"),
                            confidence=0.85,  # Mayor confianza con LLM
                            created_at=datetime.now(),
                        )

                        facts.append(fact)

            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse LLM response as JSON: {e}")

        except Exception as e:
            logger.warning(f"Error in LLM knowledge extraction: {e}")

        return facts

    def get_all_knowledge(self) -> list[KnowledgeFact]:
        """Retorna todos los hechos de conocimiento extraídos."""
        return self._knowledge


# =============================================================================
# Detección de anachronismos temporales de conocimiento
# =============================================================================

# Clasificación semántica de learned_how
_REFERENCE_MODES = {"knew", "remembered", "assumed", "learned", "thought"}
_ACQUISITION_MODES = {"discovered", "told", "shown", "overheard", "observed"}
_IGNORANCE_MODES = {"unknown"}

# Conocimiento público: atributos que una persona puede conocer sin contacto directo
# (por leer su obra, ver sus películas, conocer su reputación, etc.)
_PUBLIC_KNOWLEDGE_TERMS = {
    "obra", "libro", "novela", "teoría", "teorema", "trabajo", "investigación",
    "canción", "disco", "álbum", "película", "serie", "cuadro", "pintura",
    "artículo", "ensayo", "poema", "sinfonía", "ley", "descubrimiento",
    "reputación", "fama", "carrera", "trayectoria", "legado", "filosofía",
}


def _is_public_knowledge(fact_value: str) -> bool:
    """
    Determina si un hecho puede ser conocimiento público.

    Conocimiento público es lo que alguien puede saber sin contacto directo:
    la obra, el libro, la teoría, la fama de alguien. No necesita
    presentación formal para saber esto.
    """
    words = set(fact_value.lower().split())
    return bool(words & _PUBLIC_KNOWLEDGE_TERMS)


def _extract_significant_words(text: str) -> set[str]:
    """Extrae palabras significativas de un texto (≥3 caracteres, sin stopwords)."""
    stopwords = {
        "que",
        "una",
        "uno",
        "con",
        "por",
        "para",
        "del",
        "los",
        "las",
        "les",
        "era",
        "tenía",
        "estaba",
        "había",
        "muy",
        "más",
        "como",
        "pero",
        "sobre",
        "este",
        "esta",
        "ese",
        "esa",
        "sus",
        "sabe",
        "desde",
        "aquella",
        "cada",
        "día",
        "noche",
    }
    words = set(re.findall(r"\b\w{3,}\b", text.lower()))
    return words - stopwords


def _facts_related(fact_a: KnowledgeFact, fact_b: KnowledgeFact) -> bool:
    """
    Determina si dos hechos tratan sobre el mismo tema.

    Compara tipo de conocimiento y palabras clave del fact_value.
    Para SECRET y LOCATION siempre se consideran relacionados si
    comparten el mismo tipo.
    """
    same_type = fact_a.knowledge_type == fact_b.knowledge_type

    # IDENTITY adquisición hace prematuros TODOS los hechos previos
    # sobre la misma entidad (si no conoces a Weber, no puedes pensar en su oferta)
    if KnowledgeType.IDENTITY in (fact_a.knowledge_type, fact_b.knowledge_type):
        return True

    # Secretos y ubicación: un hecho por par de entidades
    if same_type and fact_a.knowledge_type in (KnowledgeType.SECRET, KnowledgeType.LOCATION):
        return True

    words_a = _extract_significant_words(fact_a.fact_value)
    words_b = _extract_significant_words(fact_b.fact_value)

    # Sin palabras significativas: considerar relacionados si mismo tipo
    if not words_a or not words_b:
        return same_type

    overlap = words_a & words_b
    if not overlap:
        return False

    # Verificar contradicciones: ambos lados tienen palabras únicas
    # (e.g., "ojos azules" vs "ojos verdes" → contradicción, no anachronismo)
    diff_a = words_a - words_b
    diff_b = words_b - words_a
    return not (diff_a and diff_b)


def detect_knowledge_anachronisms(
    facts: list[KnowledgeFact],
) -> list[dict]:
    """
    Detecta anachronismos temporales de conocimiento.

    Un anachronismo ocurre cuando un personaje referencia o demuestra
    conocimiento en un capítulo anterior al capítulo donde lo adquiere.

    Args:
        facts: Lista de hechos de conocimiento extraídos de todo el manuscrito.

    Returns:
        Lista de dicts con información de cada anachronismo detectado:
        - knower_name: nombre del personaje
        - known_name: nombre de la entidad sobre la que sabe
        - fact_value: descripción del hecho
        - used_chapter: capítulo donde referencia el conocimiento
        - learned_chapter: capítulo donde lo adquiere
        - severity: "high" (>3 capítulos) o "medium"
        - description: descripción legible del problema
    """
    # Agrupar hechos por (knower, known)
    groups: dict[tuple[int, int], list[KnowledgeFact]] = defaultdict(list)
    for fact in facts:
        key = (fact.knower_entity_id, fact.known_entity_id)
        groups[key].append(fact)

    anachronisms = []

    for (_knower_id, _known_id), group_facts in groups.items():
        # Separar por rol semántico
        references = [f for f in group_facts if f.learned_how in _REFERENCE_MODES]
        acquisitions = [f for f in group_facts if f.learned_how in _ACQUISITION_MODES]
        ignorances = [f for f in group_facts if f.learned_how in _IGNORANCE_MODES]

        # Caso 1: Referencia antes de adquisición explícita
        # Compara primero por capítulo; si mismo capítulo, compara por posición
        for ref in references:
            for acq in acquisitions:
                is_before = (
                    acq.source_chapter > ref.source_chapter
                    or (
                        acq.source_chapter == ref.source_chapter
                        and acq.source_position > ref.source_position > 0
                    )
                )
                if not (is_before and _facts_related(ref, acq)):
                    continue

                # Excluir conocimiento público: si alguien conoce la "obra"
                # o "libro" de otro, no necesita presentación formal
                if (
                    acq.knowledge_type == KnowledgeType.IDENTITY
                    and ref.knowledge_type == KnowledgeType.ATTRIBUTE
                    and _is_public_knowledge(ref.fact_value)
                ):
                    continue

                gap = acq.source_chapter - ref.source_chapter
                if gap > 0:
                    desc = (
                        f"{ref.knower_name} referencia "
                        f"'{ref.fact_value}' en capítulo {ref.source_chapter}, "
                        f"pero lo aprende en capítulo {acq.source_chapter}"
                    )
                else:
                    desc = (
                        f"{ref.knower_name} referencia "
                        f"'{ref.fact_value}' antes de aprenderlo "
                        f"en el mismo capítulo {ref.source_chapter}"
                    )
                anachronisms.append(
                    {
                        "knower_name": ref.knower_name,
                        "known_name": ref.known_name,
                        "fact_value": ref.fact_value,
                        "fact_description": ref.fact_description,
                        "used_chapter": ref.source_chapter,
                        "learned_chapter": acq.source_chapter,
                        "severity": "high" if gap > 3 else "medium",
                        "description": desc,
                    }
                )

        # Caso 2: Ignorancia → referencia sin adquisición intermedia
        for ign in ignorances:
            for ref in references:
                if ref.source_chapter > ign.source_chapter and _facts_related(ign, ref):
                    # Verificar si hay adquisición entre la ignorancia y la referencia
                    has_acq_between = any(
                        ign.source_chapter < acq.source_chapter <= ref.source_chapter
                        and _facts_related(ign, acq)
                        for acq in acquisitions
                    )
                    if not has_acq_between:
                        anachronisms.append(
                            {
                                "knower_name": ref.knower_name,
                                "known_name": ref.known_name,
                                "fact_value": ref.fact_value,
                                "fact_description": ref.fact_description,
                                "used_chapter": ref.source_chapter,
                                "learned_chapter": None,
                                "severity": "high",
                                "description": (
                                    f"{ref.knower_name} no sabía "
                                    f"'{ign.fact_value}' en capítulo {ign.source_chapter}, "
                                    f"pero lo referencia en capítulo {ref.source_chapter} "
                                    f"sin evento de aprendizaje intermedio"
                                ),
                            }
                        )

        # Caso 3: Adquisición temprana antes de revelación explícita
        # (descubrió/observó en cap X, pero se lo cuentan en cap Y > X)
        early_discoveries = [f for f in group_facts if f.learned_how in ("discovered", "observed")]
        explicit_tells = [f for f in group_facts if f.learned_how in ("told", "shown")]
        for disc in early_discoveries:
            for tell in explicit_tells:
                if tell.source_chapter > disc.source_chapter and _facts_related(disc, tell):
                    gap = tell.source_chapter - disc.source_chapter
                    anachronisms.append(
                        {
                            "knower_name": disc.knower_name,
                            "known_name": disc.known_name,
                            "fact_value": disc.fact_value,
                            "fact_description": disc.fact_description,
                            "used_chapter": disc.source_chapter,
                            "learned_chapter": tell.source_chapter,
                            "severity": "medium" if gap <= 3 else "high",
                            "description": (
                                f"{disc.knower_name} descubre "
                                f"'{disc.fact_value}' en capítulo {disc.source_chapter}, "
                                f"pero se lo comunican en capítulo {tell.source_chapter}"
                            ),
                        }
                    )

    # Deduplicar por (knower, fact_value, used_chapter, learned_chapter)
    seen = set()
    unique = []
    for a in anachronisms:
        key = (a["knower_name"], a["used_chapter"], a.get("learned_chapter"))
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique
