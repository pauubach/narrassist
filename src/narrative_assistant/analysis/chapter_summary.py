"""
Resumen automático de avance por capítulo.

Genera resúmenes estructurados de cada capítulo incluyendo:
- Personajes presentes y sus interacciones
- Eventos clave detectados (primera aparición, muerte, etc.)
- Arco emocional del capítulo
- Relaciones que progresan o cambian

Modos de análisis:
- BASIC: Solo conteos y patrones (sin LLM)
- STANDARD: Análisis LLM con llama3.2 (rápido)
- DEEP: Multi-modelo con votación (más preciso)
"""

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Cache con TTL para analyze_chapter_progress
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, "ChapterProgressReport"]] = {}
_CACHE_TTL_SECONDS = 60  # 1 minuto


class AnalysisMode(str, Enum):
    """Modos de análisis disponibles."""

    BASIC = "basic"  # Sin LLM, solo patrones
    STANDARD = "standard"  # LLM con modelo rápido
    DEEP = "deep"  # Multi-modelo con votación


class EventType(str, Enum):
    """Tipos de eventos narrativos detectables."""

    # Eventos básicos (detección por patrones)
    FIRST_APPEARANCE = "first_appearance"
    RETURN = "return"
    DEATH = "death"
    DEPARTURE = "departure"
    CONFLICT = "conflict"
    ALLIANCE = "alliance"
    EMOTIONAL_SHIFT = "emotional_shift"
    LOCATION_CHANGE = "location_change"
    NEW_RELATIONSHIP = "new_relationship"

    # Eventos avanzados (requieren LLM)
    DECISION = "decision"  # Personaje toma decisión clave
    DISCOVERY = "discovery"  # Información/secreto descubierto
    REVELATION = "revelation"  # Revelación importante
    BETRAYAL = "betrayal"  # Traición
    SACRIFICE = "sacrifice"  # Personaje sacrifica algo
    TRANSFORMATION = "transformation"  # Hito en arco del personaje
    PLOT_TWIST = "plot_twist"  # Giro inesperado
    CLIMAX_MOMENT = "climax_moment"  # Punto de alta tensión
    RESOLUTION = "resolution"  # Conflicto resuelto


# Patrones para detectar eventos sin LLM
REVELATION_PATTERNS = [
    re.compile(r"nunca.*había.*(?:contado|dicho|revelado)", re.IGNORECASE),
    re.compile(r"(?:descubr|revel|confes)[óií](?:ó|a)", re.IGNORECASE),
    re.compile(r"la verdad es que", re.IGNORECASE),
    re.compile(r"todo este tiempo", re.IGNORECASE),
    re.compile(r"(?:por fin|finalmente).*(?:supo|entendió|comprendió)", re.IGNORECASE),
]

DEATH_PATTERNS = [
    re.compile(r"(?:murió|falleció|expiró|pereció)", re.IGNORECASE),
    re.compile(r"dejó de existir", re.IGNORECASE),
    re.compile(r"último aliento", re.IGNORECASE),
    re.compile(r"ya no (?:estaba|respiraba)", re.IGNORECASE),
]

DECISION_PATTERNS = [
    re.compile(r"(?:decidió|resolvió|determinó)\s+(?:que|no)", re.IGNORECASE),
    re.compile(r"tomó la decisión", re.IGNORECASE),
    re.compile(r"no había vuelta atrás", re.IGNORECASE),
]


@dataclass
class NarrativeEvent:
    """Un evento narrativo detectado en el capítulo."""

    event_type: EventType
    description: str
    characters_involved: list[str] = field(default_factory=list)
    chapter_number: int = 0
    position: int = 0
    confidence: float = 1.0
    source_text: str = ""
    detected_by: str = "pattern"  # pattern, llm, hybrid

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "description": self.description,
            "characters_involved": self.characters_involved,
            "chapter_number": self.chapter_number,
            "position": self.position,
            "confidence": self.confidence,
            "source_text": self.source_text[:200] if self.source_text else "",
            "detected_by": self.detected_by,
        }


@dataclass
class CharacterPresence:
    """Presencia de un personaje en un capítulo."""

    entity_id: int
    name: str
    mention_count: int = 0
    first_mention_position: int = 0
    last_mention_position: int = 0
    is_first_appearance: bool = False
    is_return: bool = False
    chapters_absent: int = 0

    dialogues_count: int = 0
    actions_count: int = 0
    interactions_with: list[str] = field(default_factory=list)

    dominant_emotion: str | None = None
    emotional_trajectory: str = "stable"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "mention_count": self.mention_count,
            "first_mention_position": self.first_mention_position,
            "last_mention_position": self.last_mention_position,
            "is_first_appearance": self.is_first_appearance,
            "is_return": self.is_return,
            "chapters_absent": self.chapters_absent,
            "dialogues_count": self.dialogues_count,
            "actions_count": self.actions_count,
            "interactions_with": self.interactions_with,
            "dominant_emotion": self.dominant_emotion,
            "emotional_trajectory": self.emotional_trajectory,
        }


@dataclass
class ChekhovElement:
    """Elemento narrativo tipo Chekhov's Gun (setup sin payoff)."""

    entity_id: int | None
    name: str
    element_type: str  # object, detail, foreshadowing
    setup_chapter: int
    setup_position: int
    setup_context: str
    payoff_chapter: int | None = None
    payoff_position: int | None = None
    payoff_context: str | None = None
    is_fired: bool = False  # True si tiene payoff
    confidence: float = 0.5
    llm_analysis: str | None = None

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "element_type": self.element_type,
            "setup_chapter": self.setup_chapter,
            "setup_position": self.setup_position,
            "setup_context": self.setup_context[:200] if self.setup_context else "",
            "payoff_chapter": self.payoff_chapter,
            "payoff_position": self.payoff_position,
            "payoff_context": (
                self.payoff_context[:200] if self.payoff_context else None
            ),
            "is_fired": self.is_fired,
            "confidence": self.confidence,
            "llm_analysis": self.llm_analysis,
        }


@dataclass
class CharacterArc:
    """Arco narrativo de un personaje."""

    character_id: int
    character_name: str
    arc_type: str  # growth, fall, redemption, static, circular
    start_state: str = ""
    end_state: str = ""
    key_turning_points: list[dict] = field(default_factory=list)
    completeness: float = 0.0  # 0-1
    chapters_present: int = 0
    total_mentions: int = 0
    max_absence_gap: int = 0
    trajectory: str = "stable"  # rising, declining, stable
    llm_notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "arc_type": self.arc_type,
            "start_state": self.start_state,
            "end_state": self.end_state,
            "key_turning_points": self.key_turning_points,
            "completeness": self.completeness,
            "chapters_present": self.chapters_present,
            "total_mentions": self.total_mentions,
            "max_absence_gap": self.max_absence_gap,
            "trajectory": self.trajectory,
            "llm_notes": self.llm_notes,
        }


@dataclass
class AbandonedThread:
    """Trama o hilo narrativo abandonado."""

    description: str
    introduced_chapter: int
    last_mention_chapter: int
    characters_involved: list[str] = field(default_factory=list)
    entities_involved: list[str] = field(default_factory=list)
    suggestion: str | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "introduced_chapter": self.introduced_chapter,
            "last_mention_chapter": self.last_mention_chapter,
            "characters_involved": self.characters_involved,
            "entities_involved": self.entities_involved,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


@dataclass
class ChapterSummary:
    """Resumen completo de un capítulo."""

    chapter_number: int
    chapter_title: str | None = None
    word_count: int = 0

    characters_present: list[CharacterPresence] = field(default_factory=list)
    new_characters: list[str] = field(default_factory=list)
    returning_characters: list[str] = field(default_factory=list)
    absent_characters: list[str] = field(default_factory=list)

    key_events: list[NarrativeEvent] = field(default_factory=list)
    llm_events: list[NarrativeEvent] = field(
        default_factory=list
    )  # Eventos detectados por LLM

    total_interactions: int = 0
    conflict_interactions: int = 0
    positive_interactions: int = 0

    dominant_tone: str = "neutral"
    tone_intensity: float = 0.5

    locations_mentioned: list[str] = field(default_factory=list)
    location_changes: int = 0

    auto_summary: str = ""
    llm_summary: str | None = None  # Resumen generado por LLM

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "word_count": self.word_count,
            "characters_present": [c.to_dict() for c in self.characters_present],
            "new_characters": self.new_characters,
            "returning_characters": self.returning_characters,
            "absent_characters": self.absent_characters,
            "key_events": [e.to_dict() for e in self.key_events],
            "llm_events": [e.to_dict() for e in self.llm_events],
            "total_interactions": self.total_interactions,
            "conflict_interactions": self.conflict_interactions,
            "positive_interactions": self.positive_interactions,
            "dominant_tone": self.dominant_tone,
            "tone_intensity": self.tone_intensity,
            "locations_mentioned": self.locations_mentioned,
            "location_changes": self.location_changes,
            "auto_summary": self.auto_summary,
            "llm_summary": self.llm_summary,
        }


@dataclass
class ChapterProgressReport:
    """Informe completo de avance narrativo."""

    project_id: int
    analysis_mode: str = "basic"
    total_chapters: int = 0
    chapters: list[ChapterSummary] = field(default_factory=list)

    total_characters: int = 0
    active_characters: int = 0
    dormant_characters: list[str] = field(default_factory=list)

    character_arcs: list[CharacterArc] = field(default_factory=list)
    chekhov_elements: list[ChekhovElement] = field(default_factory=list)
    abandoned_threads: list[AbandonedThread] = field(default_factory=list)

    structural_notes: str | None = None  # Análisis LLM de estructura

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "analysis_mode": self.analysis_mode,
            "total_chapters": self.total_chapters,
            "chapters": [c.to_dict() for c in self.chapters],
            "total_characters": self.total_characters,
            "active_characters": self.active_characters,
            "dormant_characters": self.dormant_characters,
            "character_arcs": [a.to_dict() for a in self.character_arcs],
            "chekhov_elements": [c.to_dict() for c in self.chekhov_elements],
            "abandoned_threads": [t.to_dict() for t in self.abandoned_threads],
            "structural_notes": self.structural_notes,
        }


# Prompt para extracción de eventos con LLM
EVENTS_EXTRACTION_PROMPT = """Analiza el siguiente fragmento de capítulo y extrae los eventos SIGNIFICATIVOS para la trama.

CAPÍTULO {chapter_num}{title_part}
---
{text}
---

Extrae los 3-5 eventos MÁS IMPORTANTES que:
1. Cambian el estado de un personaje o relación
2. Revelan información crucial
3. Impulsan la trama hacia adelante
4. Representan un punto de no retorno

Responde SOLO con JSON válido (sin markdown):
{{
  "events": [
    {{
      "type": "decision|discovery|revelation|betrayal|sacrifice|transformation|plot_twist|climax_moment|resolution",
      "description": "Descripción breve del evento en español",
      "characters": ["nombre1", "nombre2"],
      "importance": 1-5
    }}
  ],
  "summary": "Resumen de 2-3 oraciones del capítulo"
}}"""

# Prompt para análisis de arcos narrativos
NARRATIVE_ARCS_PROMPT = """Analiza los siguientes resúmenes de capítulos para identificar arcos narrativos.

RESÚMENES POR CAPÍTULO:
{chapter_summaries}

PERSONAJES PRINCIPALES: {main_characters}

Identifica:
1. Arcos de personajes: ¿Qué personajes tienen una transformación clara?
2. Tramas abandonadas: ¿Hay hilos narrativos que se introducen pero no se resuelven?

Responde SOLO con JSON válido:
{{
  "character_arcs": [
    {{
      "character": "nombre",
      "arc_type": "growth|fall|redemption|static|circular",
      "start_state": "estado inicial del personaje",
      "end_state": "estado final del personaje",
      "turning_points": [
        {{"chapter": 1, "event": "descripción"}}
      ],
      "completeness": 0-100
    }}
  ],
  "abandoned_threads": [
    {{
      "description": "descripción de la trama abandonada",
      "introduced_chapter": 1,
      "last_chapter": 5,
      "characters": ["nombre"],
      "suggestion": "cómo podría resolverse"
    }}
  ],
  "structural_notes": "observaciones sobre la estructura narrativa"
}}"""

# Prompt para detección de Chekhov's Gun
CHEKHOV_ANALYSIS_PROMPT = """Analiza si el siguiente objeto/detalle mencionado en el capítulo {setup_chapter} tiene un "payoff" narrativo posteriormente.

OBJETO/DETALLE: {element_name}
CONTEXTO DE INTRODUCCIÓN (Cap. {setup_chapter}):
"{setup_context}"

MENCIONES POSTERIORES:
{later_mentions}

¿Es este un "Chekhov's Gun" (elemento narrativo introducido que debe tener consecuencias)?
¿Tiene un payoff satisfactorio?

Responde SOLO con JSON:
{{
  "is_chekhov_element": true/false,
  "has_payoff": true/false,
  "payoff_description": "descripción del payoff si existe",
  "recommendation": "sugerencia si no tiene payoff"
}}"""


class ChapterSummaryAnalyzer:
    """
    Analizador de resúmenes por capítulo.

    Soporta tres modos:
    - BASIC: Solo patrones, sin LLM
    - STANDARD: LLM con modelo rápido (llama3.2)
    - DEEP: Multi-modelo con votación
    """

    def __init__(
        self,
        db_path: str | None = None,
        mode: AnalysisMode = AnalysisMode.BASIC,
        llm_model: str = "llama3.2",
    ):
        from ..persistence.database import get_database

        self.db = get_database(db_path)
        self.mode = mode
        self.llm_model = llm_model
        self._ollama_client = None
        self._embeddings_model = None

    @property
    def ollama_client(self):
        """Lazy loading del cliente Ollama."""
        if self._ollama_client is None and self.mode != AnalysisMode.BASIC:
            try:
                from ..llm.ollama_client import OllamaClient

                self._ollama_client = OllamaClient()
            except Exception as e:
                logger.warning(f"No se pudo inicializar Ollama: {e}")
        return self._ollama_client

    @property
    def embeddings_model(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings_model is None:
            try:
                from ..nlp.embeddings import EmbeddingsModel

                self._embeddings_model = EmbeddingsModel()
            except Exception as e:
                logger.warning(f"No se pudo inicializar embeddings: {e}")
        return self._embeddings_model

    def analyze_project(self, project_id: int) -> ChapterProgressReport:
        """Genera el informe de avance para un proyecto completo."""
        report = ChapterProgressReport(
            project_id=project_id,
            analysis_mode=self.mode.value,
        )

        chapters = self._get_chapters(project_id)
        report.total_chapters = len(chapters)

        if not chapters:
            return report

        all_characters = self._get_characters(project_id)
        report.total_characters = len(all_characters)

        first_appearances = self._get_first_appearances(project_id)
        last_appearances: dict[int, int] = {}

        # Procesar cada capítulo
        for chapter in chapters:
            chapter_summary = self._analyze_chapter(
                project_id=project_id,
                chapter=chapter,
                all_characters=all_characters,
                first_appearances=first_appearances,
                last_appearances=last_appearances,
            )
            report.chapters.append(chapter_summary)

            for char in chapter_summary.characters_present:
                last_appearances[char.entity_id] = chapter["chapter_number"]

        # Detectar personajes dormidos
        if report.total_chapters >= 3:
            recent_chapters = set(
                range(max(1, report.total_chapters - 2), report.total_chapters + 1)
            )
            for char_id, char_name in all_characters.items():
                last_ch = last_appearances.get(char_id, 0)
                if last_ch not in recent_chapters and last_ch > 0:
                    report.dormant_characters.append(char_name)
            report.active_characters = report.total_characters - len(
                report.dormant_characters
            )
        else:
            report.active_characters = report.total_characters

        # Calcular arcos de personajes (básico)
        report.character_arcs = self._calculate_character_arcs(
            report.chapters, all_characters
        )

        # Análisis avanzado con LLM
        if self.mode != AnalysisMode.BASIC:
            self._enhance_with_llm(report, all_characters)

        # Detectar Chekhov's Guns
        report.chekhov_elements = self._detect_chekhov_elements(project_id)

        return report

    def _get_chapters(self, project_id: int) -> list[dict]:
        """Obtiene los capítulos del proyecto."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, chapter_number, title, word_count, start_char, end_char, content
                FROM chapters
                WHERE project_id = ?
                ORDER BY chapter_number
                """,
                (project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _get_characters(self, project_id: int) -> dict[int, str]:
        """Obtiene todos los personajes del proyecto."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, canonical_name
                FROM entities
                WHERE project_id = ? AND entity_type = 'character' AND is_active = 1
                """,
                (project_id,),
            )
            return {row["id"]: row["canonical_name"] for row in cursor.fetchall()}

    def _get_first_appearances(self, project_id: int) -> dict[int, int]:
        """Obtiene el capítulo de primera aparición de cada personaje."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT e.id, MIN(c.chapter_number) as first_chapter
                FROM entities e
                JOIN entity_mentions em ON e.id = em.entity_id
                JOIN chapters c ON em.chapter_id = c.id
                WHERE e.project_id = ? AND e.entity_type = 'character'
                GROUP BY e.id
                """,
                (project_id,),
            )
            return {row["id"]: row["first_chapter"] for row in cursor.fetchall()}

    def _get_mentions_by_chapter(
        self, project_id: int, chapter_id: int
    ) -> dict[int, list[dict]]:
        """Obtiene menciones agrupadas por entidad para un capítulo."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT em.entity_id, em.surface_form, em.start_char, em.end_char,
                       e.canonical_name, e.entity_type
                FROM entity_mentions em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.chapter_id = ? AND e.project_id = ?
                ORDER BY em.start_char
                """,
                (chapter_id, project_id),
            )

            mentions_by_entity: dict[int, list[dict]] = {}
            for row in cursor.fetchall():
                entity_id = row["entity_id"]
                if entity_id not in mentions_by_entity:
                    mentions_by_entity[entity_id] = []
                mentions_by_entity[entity_id].append(dict(row))

            return mentions_by_entity

    def _get_interactions_by_chapter(
        self, project_id: int, chapter_id: int
    ) -> list[dict]:
        """Obtiene interacciones para un capítulo."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT i.*,
                       e1.canonical_name as from_name,
                       e2.canonical_name as to_name
                FROM interactions i
                JOIN entities e1 ON i.entity1_id = e1.id
                LEFT JOIN entities e2 ON i.entity2_id = e2.id
                WHERE i.project_id = ? AND i.chapter_id = ?
                ORDER BY i.position
                """,
                (project_id, chapter_id),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _get_locations_by_chapter(self, project_id: int, chapter_id: int) -> list[str]:
        """Obtiene ubicaciones mencionadas en un capítulo."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT e.canonical_name
                FROM entity_mentions em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.chapter_id = ? AND e.project_id = ?
                  AND e.entity_type IN ('location', 'building', 'region')
                """,
                (chapter_id, project_id),
            )
            return [row["canonical_name"] for row in cursor.fetchall()]

    def _analyze_chapter(
        self,
        project_id: int,
        chapter: dict,
        all_characters: dict[int, str],
        first_appearances: dict[int, int],
        last_appearances: dict[int, int],
    ) -> ChapterSummary:
        """Analiza un capítulo individual."""
        summary = ChapterSummary(
            chapter_number=chapter["chapter_number"],
            chapter_title=chapter.get("title"),
            word_count=chapter.get("word_count", 0),
        )

        chapter_id = chapter["id"]
        chapter_num = chapter["chapter_number"]

        mentions = self._get_mentions_by_chapter(project_id, chapter_id)
        interactions = self._get_interactions_by_chapter(project_id, chapter_id)
        summary.total_interactions = len(interactions)

        for interaction in interactions:
            tone = interaction.get("tone", "neutral")
            if tone in ("hostile", "cold"):
                summary.conflict_interactions += 1
            elif tone in ("warm", "affectionate"):
                summary.positive_interactions += 1

        summary.locations_mentioned = self._get_locations_by_chapter(
            project_id, chapter_id
        )

        characters_in_chapter: set[int] = set()

        for entity_id, entity_mentions in mentions.items():
            if not entity_mentions:
                continue

            first_mention = entity_mentions[0]
            if first_mention.get("entity_type") != "character":
                continue

            characters_in_chapter.add(entity_id)
            char_name = first_mention["canonical_name"]

            presence = CharacterPresence(
                entity_id=entity_id,
                name=char_name,
                mention_count=len(entity_mentions),
                first_mention_position=entity_mentions[0]["start_char"],
                last_mention_position=entity_mentions[-1]["end_char"],
            )

            if first_appearances.get(entity_id) == chapter_num:
                presence.is_first_appearance = True
                summary.new_characters.append(char_name)
                summary.key_events.append(
                    NarrativeEvent(
                        event_type=EventType.FIRST_APPEARANCE,
                        description=f"Primera aparición de {char_name}",
                        characters_involved=[char_name],
                        chapter_number=chapter_num,
                        position=presence.first_mention_position,
                    )
                )

            last_seen = last_appearances.get(entity_id, 0)
            if last_seen > 0 and chapter_num - last_seen > 1:
                presence.is_return = True
                presence.chapters_absent = chapter_num - last_seen - 1
                summary.returning_characters.append(char_name)
                if presence.chapters_absent >= 2:
                    summary.key_events.append(
                        NarrativeEvent(
                            event_type=EventType.RETURN,
                            description=f"{char_name} regresa después de {presence.chapters_absent} capítulos",
                            characters_involved=[char_name],
                            chapter_number=chapter_num,
                            position=presence.first_mention_position,
                        )
                    )

            summary.characters_present.append(presence)

        # Procesar interacciones
        for interaction in interactions:
            from_id = interaction["entity1_id"]
            to_id = interaction["entity2_id"]
            from_name = interaction["from_name"]
            to_name = interaction.get("to_name")  # Puede ser NULL
            int_type = interaction.get("interaction_type", "")

            for presence in summary.characters_present:
                if presence.entity_id == from_id:
                    if int_type == "dialogue":
                        presence.dialogues_count += 1
                    else:
                        presence.actions_count += 1
                    if to_name and to_name not in presence.interactions_with:
                        presence.interactions_with.append(to_name)
                elif to_id and presence.entity_id == to_id:
                    if from_name not in presence.interactions_with:
                        presence.interactions_with.append(from_name)

            tone = interaction.get("tone", "neutral")
            if tone == "hostile" and to_name:
                summary.key_events.append(
                    NarrativeEvent(
                        event_type=EventType.CONFLICT,
                        description=f"Conflicto entre {from_name} y {to_name}",
                        characters_involved=[from_name, to_name],
                        chapter_number=chapter_num,
                        position=interaction.get("position", 0),
                        source_text=interaction.get("text_excerpt", "")[:100],
                    )
                )

        # Detectar eventos por patrones en el texto
        chapter_text = chapter.get("content", "")
        if chapter_text:
            self._detect_pattern_events(summary, chapter_text, chapter_num)

        # Detectar personajes ausentes
        for char_id, char_name in all_characters.items():
            first_ch = first_appearances.get(char_id, 999)
            if first_ch < chapter_num and char_id not in characters_in_chapter:
                with self.db.connection() as conn:
                    cursor = conn.execute(
                        "SELECT mention_count FROM entities WHERE id = ?", (char_id,)
                    )
                    row = cursor.fetchone()
                    if row and row["mention_count"] >= 5:
                        summary.absent_characters.append(char_name)

        summary.characters_present.sort(key=lambda x: x.mention_count, reverse=True)

        # Calcular tono
        if summary.conflict_interactions > summary.positive_interactions:
            summary.dominant_tone = "tense"
            summary.tone_intensity = min(
                1.0, summary.conflict_interactions / max(1, summary.total_interactions)
            )
        elif summary.positive_interactions > summary.conflict_interactions:
            summary.dominant_tone = "positive"
            summary.tone_intensity = min(
                1.0, summary.positive_interactions / max(1, summary.total_interactions)
            )
        else:
            summary.dominant_tone = "neutral"
            summary.tone_intensity = 0.5

        summary.auto_summary = self._generate_text_summary(summary)

        # Análisis LLM del capítulo
        if self.mode != AnalysisMode.BASIC and chapter_text:
            self._analyze_chapter_with_llm(summary, chapter_text)

        return summary

    def _detect_pattern_events(
        self, summary: ChapterSummary, text: str, chapter_num: int
    ) -> None:
        """Detecta eventos usando patrones regex."""
        # Revelaciones
        for pattern in REVELATION_PATTERNS:
            for match in pattern.finditer(text):
                summary.key_events.append(
                    NarrativeEvent(
                        event_type=EventType.REVELATION,
                        description="Posible revelación detectada",
                        chapter_number=chapter_num,
                        position=match.start(),
                        source_text=text[max(0, match.start() - 50) : match.end() + 50],
                        confidence=0.6,
                        detected_by="pattern",
                    )
                )
                break  # Solo una revelación por patrón

        # Muertes
        for pattern in DEATH_PATTERNS:
            for match in pattern.finditer(text):
                summary.key_events.append(
                    NarrativeEvent(
                        event_type=EventType.DEATH,
                        description="Posible muerte detectada",
                        chapter_number=chapter_num,
                        position=match.start(),
                        source_text=text[max(0, match.start() - 50) : match.end() + 50],
                        confidence=0.7,
                        detected_by="pattern",
                    )
                )
                break

        # Decisiones
        for pattern in DECISION_PATTERNS:
            for match in pattern.finditer(text):
                summary.key_events.append(
                    NarrativeEvent(
                        event_type=EventType.DECISION,
                        description="Posible decisión importante detectada",
                        chapter_number=chapter_num,
                        position=match.start(),
                        source_text=text[max(0, match.start() - 50) : match.end() + 50],
                        confidence=0.5,
                        detected_by="pattern",
                    )
                )
                break

    def _analyze_chapter_with_llm(
        self, summary: ChapterSummary, chapter_text: str
    ) -> None:
        """Analiza el capítulo con LLM para extraer eventos significativos."""
        if not self.ollama_client:
            return

        try:
            # Truncar texto si es muy largo
            max_chars = 6000
            text_to_analyze = chapter_text[:max_chars]
            if len(chapter_text) > max_chars:
                text_to_analyze += "\n[... texto truncado ...]"

            title_part = f" - {summary.chapter_title}" if summary.chapter_title else ""

            prompt = EVENTS_EXTRACTION_PROMPT.format(
                chapter_num=summary.chapter_number,
                title_part=title_part,
                text=text_to_analyze,
            )

            response = self.ollama_client.generate(
                prompt=prompt,
                model=self.llm_model,
                temperature=0.3,
                timeout=60,
            )

            if response:
                import json

                # Limpiar respuesta de markdown
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = re.sub(r"^```(?:json)?\n?", "", clean_response)
                    clean_response = re.sub(r"\n?```$", "", clean_response)

                data = json.loads(clean_response)

                # Procesar eventos
                for event_data in data.get("events", []):
                    event_type_str = event_data.get("type", "revelation")
                    try:
                        event_type = EventType(event_type_str)
                    except ValueError:
                        event_type = EventType.REVELATION

                    summary.llm_events.append(
                        NarrativeEvent(
                            event_type=event_type,
                            description=event_data.get("description", ""),
                            characters_involved=event_data.get("characters", []),
                            chapter_number=summary.chapter_number,
                            confidence=event_data.get("importance", 3) / 5.0,
                            detected_by="llm",
                        )
                    )

                # Guardar resumen LLM
                summary.llm_summary = data.get("summary")

        except Exception as e:
            logger.warning(
                f"Error en análisis LLM del capítulo {summary.chapter_number}: {e}"
            )

    def _generate_text_summary(self, summary: ChapterSummary) -> str:
        """Genera un resumen textual del capítulo."""
        parts = []

        if summary.characters_present:
            top_chars = summary.characters_present[:5]
            char_names = [c.name for c in top_chars]
            if len(char_names) == 1:
                parts.append(f"Protagonizado por {char_names[0]}")
            else:
                parts.append(
                    f"Personajes principales: {', '.join(char_names[:-1])} y {char_names[-1]}"
                )

        if summary.new_characters:
            if len(summary.new_characters) == 1:
                parts.append(f"Aparece por primera vez {summary.new_characters[0]}")
            else:
                parts.append(f"Nuevos personajes: {', '.join(summary.new_characters)}")

        if summary.returning_characters:
            parts.append(f"Regresan: {', '.join(summary.returning_characters)}")

        if summary.total_interactions > 0:
            int_desc = []
            if summary.conflict_interactions > 0:
                int_desc.append(f"{summary.conflict_interactions} conflictivas")
            if summary.positive_interactions > 0:
                int_desc.append(f"{summary.positive_interactions} positivas")
            if int_desc:
                parts.append(
                    f"{summary.total_interactions} interacciones ({', '.join(int_desc)})"
                )

        if summary.locations_mentioned:
            locs = summary.locations_mentioned[:3]
            parts.append(f"Escenarios: {', '.join(locs)}")

        tone_names = {
            "tense": "Tono tenso",
            "positive": "Tono positivo",
            "negative": "Tono negativo",
            "neutral": "Tono neutro",
        }
        if summary.dominant_tone != "neutral":
            parts.append(tone_names.get(summary.dominant_tone, ""))

        return (
            ". ".join(filter(None, parts)) + "."
            if parts
            else "Sin información destacada."
        )

    def _calculate_character_arcs(
        self, chapters: list[ChapterSummary], all_characters: dict[int, str]
    ) -> list[CharacterArc]:
        """Calcula el arco de cada personaje a lo largo de los capítulos."""
        arcs: list[CharacterArc] = []

        presence_map: dict[int, list[tuple[int, int]]] = {}

        for chapter in chapters:
            for char in chapter.characters_present:
                if char.entity_id not in presence_map:
                    presence_map[char.entity_id] = []
                presence_map[char.entity_id].append(
                    (chapter.chapter_number, char.mention_count)
                )

        for char_id, presences in presence_map.items():
            if len(presences) < 2:
                continue

            presences.sort(key=lambda x: x[0])
            mentions = [p[1] for p in presences]
            first_half = sum(mentions[: len(mentions) // 2]) if mentions else 0
            second_half = sum(mentions[len(mentions) // 2 :]) if mentions else 0

            if second_half > first_half * 1.5:
                trajectory = "rising"
            elif first_half > second_half * 1.5:
                trajectory = "declining"
            else:
                trajectory = "stable"

            chapters_present = [p[0] for p in presences]
            max_gap = 0
            for i in range(1, len(chapters_present)):
                gap = chapters_present[i] - chapters_present[i - 1] - 1
                max_gap = max(max_gap, gap)

            arc = CharacterArc(
                character_id=char_id,
                character_name=all_characters.get(char_id, "Desconocido"),
                arc_type="static",  # Se actualiza con LLM
                trajectory=trajectory,
                chapters_present=len(presences),
                total_mentions=sum(mentions),
                max_absence_gap=max_gap,
            )
            arcs.append(arc)

        return arcs

    def _enhance_with_llm(
        self, report: ChapterProgressReport, all_characters: dict[int, str]
    ) -> None:
        """Mejora el informe con análisis LLM de arcos y estructura."""
        if not self.ollama_client:
            return

        try:
            # Preparar resúmenes de capítulos
            chapter_summaries = []
            for ch in report.chapters:
                summary_text = ch.llm_summary or ch.auto_summary
                chapter_summaries.append(f"Cap. {ch.chapter_number}: {summary_text}")

            main_chars = list(all_characters.values())[:10]

            prompt = NARRATIVE_ARCS_PROMPT.format(
                chapter_summaries="\n".join(chapter_summaries),
                main_characters=", ".join(main_chars),
            )

            response = self.ollama_client.generate(
                prompt=prompt,
                model=self.llm_model,
                temperature=0.3,
                timeout=120,
            )

            if response:
                import json

                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = re.sub(r"^```(?:json)?\n?", "", clean_response)
                    clean_response = re.sub(r"\n?```$", "", clean_response)

                data = json.loads(clean_response)

                # Actualizar arcos con info LLM
                for arc_data in data.get("character_arcs", []):
                    char_name = arc_data.get("character", "")
                    for arc in report.character_arcs:
                        if arc.character_name.lower() == char_name.lower():
                            arc.arc_type = arc_data.get("arc_type", "static")
                            arc.start_state = arc_data.get("start_state", "")
                            arc.end_state = arc_data.get("end_state", "")
                            arc.completeness = arc_data.get("completeness", 0) / 100.0
                            arc.key_turning_points = arc_data.get("turning_points", [])
                            break

                # Procesar tramas abandonadas
                for thread_data in data.get("abandoned_threads", []):
                    report.abandoned_threads.append(
                        AbandonedThread(
                            description=thread_data.get("description", ""),
                            introduced_chapter=thread_data.get("introduced_chapter", 0),
                            last_mention_chapter=thread_data.get("last_chapter", 0),
                            characters_involved=thread_data.get("characters", []),
                            suggestion=thread_data.get("suggestion"),
                            confidence=0.7,
                        )
                    )

                report.structural_notes = data.get("structural_notes")

        except Exception as e:
            logger.warning(f"Error en análisis LLM de arcos: {e}")

    def _detect_chekhov_elements(self, project_id: int) -> list[ChekhovElement]:
        """
        Detecta elementos tipo Chekhov's Gun (objetos introducidos sin payoff).

        Algoritmo:
        1. Busca objetos mencionados en primeros capítulos
        2. Verifica si reaparecen posteriormente
        3. Usa embeddings para detectar si el contexto cambia (setup -> payoff)
        """
        elements: list[ChekhovElement] = []

        with self.db.connection() as conn:
            # Obtener objetos del proyecto
            cursor = conn.execute(
                """
                SELECT e.id, e.canonical_name, e.mention_count,
                       MIN(c.chapter_number) as first_chapter,
                       MAX(c.chapter_number) as last_chapter
                FROM entities e
                JOIN entity_mentions em ON e.id = em.entity_id
                JOIN chapters c ON em.chapter_id = c.id
                WHERE e.project_id = ?
                  AND e.entity_type IN ('object', 'vehicle')
                  AND e.is_active = 1
                GROUP BY e.id
                HAVING MIN(c.chapter_number) <= 3
                """,
                (project_id,),
            )

            for row in cursor.fetchall():
                entity_id = row["id"]
                name = row["canonical_name"]
                first_ch = row["first_chapter"]
                last_ch = row["last_chapter"]
                mention_count = row["mention_count"]

                # Si solo aparece en un capítulo o muy pocas veces, potencial Chekhov
                gap = last_ch - first_ch

                # Obtener contexto de primera mención
                ctx_cursor = conn.execute(
                    """
                    SELECT em.context_before, em.context_after, em.start_char
                    FROM entity_mentions em
                    JOIN chapters c ON em.chapter_id = c.id
                    WHERE em.entity_id = ? AND c.chapter_number = ?
                    ORDER BY em.start_char
                    LIMIT 1
                    """,
                    (entity_id, first_ch),
                )
                ctx_row = ctx_cursor.fetchone()

                setup_context = ""
                setup_position = 0
                if ctx_row:
                    setup_context = f"{ctx_row['context_before'] or ''} {name} {ctx_row['context_after'] or ''}"
                    setup_position = ctx_row["start_char"]

                # Determinar si es "unfired" (sin payoff claro)
                is_fired = gap > 0 and mention_count > 2

                element = ChekhovElement(
                    entity_id=entity_id,
                    name=name,
                    element_type="object",
                    setup_chapter=first_ch,
                    setup_position=setup_position,
                    setup_context=setup_context.strip(),
                    payoff_chapter=last_ch if is_fired else None,
                    is_fired=is_fired,
                    confidence=0.6 if not is_fired else 0.3,
                )

                # Si no está "fired" y estamos en modo avanzado, es candidato
                if not is_fired or mention_count <= 2:
                    elements.append(element)

        # BK-16: Extender Chekhov a personajes secundarios
        try:
            from .chekhov_tracker import ChekhovTracker

            tracker = ChekhovTracker(self.db)
            total_chapters = self._get_total_chapters(project_id)
            character_elements = tracker.track_characters(project_id, total_chapters)
            elements.extend(character_elements)
        except Exception as e:
            logger.warning(f"Error tracking Chekhov characters: {e}")

        return elements

    def _get_total_chapters(self, project_id: int) -> int:
        """Obtiene el número total de capítulos de un proyecto."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM chapters WHERE project_id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0


def analyze_chapter_progress(
    project_id: int,
    db_path: str | None = None,
    mode: str = "basic",
    llm_model: str = "llama3.2",
) -> ChapterProgressReport:
    """
    Función de conveniencia para analizar el avance de un proyecto.

    Incluye caché con TTL para evitar recálculos costosos cuando múltiples
    endpoints solicitan los mismos datos en un intervalo corto.

    Args:
        project_id: ID del proyecto a analizar
        db_path: Ruta opcional a la base de datos
        mode: Modo de análisis (basic, standard, deep)
        llm_model: Modelo LLM a usar (llama3.2, qwen2.5, mistral)

    Returns:
        ChapterProgressReport con el análisis completo
    """
    cache_key = f"{project_id}:{mode}:{llm_model}"
    now = time.monotonic()

    with _cache_lock:
        if cache_key in _cache:
            ts, cached_report = _cache[cache_key]
            if now - ts < _CACHE_TTL_SECONDS:
                logger.debug(
                    f"Cache hit for chapter progress: project={project_id}, mode={mode}"
                )
                return cached_report
            else:
                del _cache[cache_key]

    analysis_mode = AnalysisMode(mode)
    analyzer = ChapterSummaryAnalyzer(db_path, mode=analysis_mode, llm_model=llm_model)
    report = analyzer.analyze_project(project_id)

    with _cache_lock:
        _cache[cache_key] = (time.monotonic(), report)
        # Limpiar entradas expiradas
        expired = [k for k, (ts, _) in _cache.items() if now - ts >= _CACHE_TTL_SECONDS]
        for k in expired:
            del _cache[k]

    return report


def invalidate_chapter_progress_cache(project_id: int | None = None) -> None:
    """
    Invalidar caché de analyze_chapter_progress.

    Args:
        project_id: Si se proporciona, invalida solo ese proyecto.
                    Si es None, limpia toda la caché.
    """
    with _cache_lock:
        if project_id is None:
            _cache.clear()
        else:
            prefix = f"{project_id}:"
            keys_to_del = [k for k in _cache if k.startswith(prefix)]
            for k in keys_to_del:
                del _cache[k]
