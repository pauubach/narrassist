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
            "payoff_context": (self.payoff_context[:200] if self.payoff_context else None),
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
    llm_events: list[NarrativeEvent] = field(default_factory=list)  # Eventos detectados por LLM

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
    global_summary: str | None = None  # Sinopsis global del manuscrito

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
            "global_summary": self.global_summary,
        }


# ============================================================================
# Instrucciones específicas por género/subgénero
# ============================================================================

GENRE_INSTRUCTIONS: dict[str, str] = {
    # Subgéneros de ficción (prioridad alta)
    "FIC_POL": "Prioriza: pistas descubiertas, coartadas, interrogatorios, sospechas, deducciones del investigador.",
    "FIC_ROM": "Prioriza: desarrollo de la relación, obstáculos emocionales, malentendidos, momentos de conexión.",
    "FIC_THR": "Prioriza: escalada de tensión, amenazas, persecuciones, giros inesperados, revelaciones peligrosas.",
    "FIC_FAN": "Prioriza: sistema de magia, alianzas, profecías, conflictos de poder, worldbuilding relevante.",
    "FIC_SCI": "Prioriza: tecnología clave, conflictos éticos, exploración, descubrimientos, worldbuilding.",
    "FIC_TER": "Prioriza: escalada del horror, amenazas sobrenaturales o psicológicas, muertes, revelaciones aterradoras.",
    "FIC_HIS": "Prioriza: eventos históricos, anacronismos potenciales, tensión entre ficción y contexto real.",
    "FIC_LIT": "Prioriza: giros de trama, revelaciones, conflictos internos, decisiones con consecuencias.",
    # Tipos principales (fallback)
    "FIC": "Prioriza: giros de trama, revelaciones, conflictos, decisiones con consecuencias.",
    "MEM": "Prioriza: momentos formativos, relaciones clave, puntos de inflexión vitales.",
    "BIO": "Prioriza: hitos vitales, relaciones determinantes, logros y fracasos.",
    "ENS": "Prioriza: tesis principal, argumentos, contraargumentos, conclusiones.",
    "AUT": "Prioriza: problema planteado, técnica propuesta, ejemplos prácticos.",
    "DIV": "Prioriza: descubrimientos explicados, datos sorprendentes, conexiones entre conceptos.",
    "CEL": "Prioriza: anécdotas reveladoras, lecciones personales, momentos de autenticidad.",
    "TEC": "Prioriza: conceptos clave, procedimientos, decisiones técnicas.",
    "PRA": "Prioriza: técnicas explicadas, pasos importantes, consejos prácticos.",
    "INF": "Prioriza: momentos emocionales, lecciones, aventuras, resolución de conflictos.",
    "DRA": "Prioriza: conflictos entre personajes, revelaciones, clímax de actos.",
    "GRA": "Prioriza: giros visuales, acción, diálogos impactantes.",
}

# Labels legibles para tipos de documento
GENRE_LABELS: dict[str, str] = {
    "FIC": "Ficción",
    "FIC_POL": "Novela policial/misterio",
    "FIC_ROM": "Novela romántica",
    "FIC_THR": "Thriller/Suspense",
    "FIC_FAN": "Fantasía",
    "FIC_SCI": "Ciencia ficción",
    "FIC_TER": "Terror/Horror",
    "FIC_HIS": "Novela histórica",
    "FIC_LIT": "Novela literaria",
    "FIC_GEN": "Novela de género",
    "FIC_COR": "Relato/Cuento",
    "FIC_MIC": "Microrrelatos",
    "MEM": "Memorias/Autobiografía",
    "BIO": "Biografía",
    "ENS": "Ensayo",
    "AUT": "Autoayuda",
    "DIV": "Divulgación",
    "CEL": "Famosos/Influencers",
    "TEC": "Manual técnico",
    "PRA": "Libro práctico",
    "INF": "Infantil/Juvenil",
    "DRA": "Teatro/Guion",
    "GRA": "Novela gráfica",
}


def _get_genre_label(document_type: str, document_subtype: str | None = None) -> str:
    """Obtiene label legible para un tipo/subtipo de documento."""
    if document_subtype and document_subtype in GENRE_LABELS:
        return GENRE_LABELS[document_subtype]
    return GENRE_LABELS.get(document_type, "Texto")


def _get_genre_instruction(document_type: str, document_subtype: str | None = None) -> str:
    """Obtiene instrucción específica de género para el prompt.

    Lookup: primero subtipo, luego tipo, luego fallback genérico.
    """
    if document_subtype and document_subtype in GENRE_INSTRUCTIONS:
        return GENRE_INSTRUCTIONS[document_subtype]
    if document_type in GENRE_INSTRUCTIONS:
        return GENRE_INSTRUCTIONS[document_type]
    return "Prioriza: eventos que cambian el estado narrativo, revelaciones y decisiones con consecuencias."


# Prompt para extracción de eventos con LLM (genre-aware)
EVENTS_EXTRACTION_PROMPT = """Eres un analista literario profesional. Responde SIEMPRE en español correcto (nunca uses posesivos ingleses como "'s", ni mezcles idiomas).

CONTEXTO:
- Tipo de obra: {genre_label}
- Capítulo {chapter_num} de {total_chapters}{title_part}
{character_roster_block}{prev_summary_block}
TEXTO DEL CAPÍTULO:
---
{text}
---

Primero, clasifica este capítulo:
- "chapter_type": "narrative" si es contenido de la obra, "front_matter" si es dedicatoria/agradecimientos/prólogo ajeno, "back_matter" si es epílogo/bibliografía/notas del autor.
- "genre_hint": en una palabra, qué género o subgénero percibes (ej: "policial", "romance", "fantasía", "ensayo", "memorias"). Solo para capítulos narrativos.

Extrae 3-5 eventos que un EDITOR profesional necesitaría para verificar consistencia. Ignora acciones rutinarias (despertar, comer, caminar) salvo que desencadenen algo significativo.

{genre_instruction}

Cada evento debe responder: QUIÉN hace QUÉ a QUIÉN, y qué CAMBIA.

El campo "summary" DEBE (CRÍTICO):
- Priorizar eventos de ALTO IMPACTO narrativo: desapariciones, muertes, revelaciones, descubrimientos, decisiones clave, conflictos importantes
- Omitir detalles triviales (llegadas rutinarias, saludos, descripciones ambientales)
- Nombrar personajes por su nombre propio
- Explicar QUÉ sucede y POR QUÉ importa para la trama
- Indicar qué CAMBIA respecto al estado anterior (qué está en riesgo, qué se descubre, qué se pierde)
- Señalar qué queda ABIERTO o sin resolver
- 4-6 frases narrativas enfocadas en CONSECUENCIAS (causa → efecto → implicación)

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
  "summary": "Resumen narrativo de 3-5 frases",
  "character_inferences": [
    {{"character": "nombre", "inferred_role": "detective/protagonista/antagonista/...", "evidence": "breve evidencia"}}
  ],
  "chapter_type": "narrative",
  "genre_hint": "policial"
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


# Prompt para resumen global del manuscrito
GLOBAL_SUMMARY_PROMPT = """Eres un editor literario profesional. Escribe una sinopsis narrativa del manuscrito en UN PÁRRAFO de 3-5 frases.

TIPO: {genre_label}
PERSONAJES: {characters}

CAPÍTULOS:
{all_chapter_summaries}

REQUISITOS ESTILÍSTICOS:
- Usa lenguaje narrativo y fluido (evita sustantivos abstractos sin artículo: "la misteriosa desaparición" en vez de "Desaparecimiento")
- Escribe en presente narrativo para mayor inmediatez
- Sé CONCISO: enfócate en premisa y conflicto central, omite detalles secundarios
- Captura el tono del género ({genre_label})
- Sé específico con nombres propios, NO uses "el protagonista" o "la detective"

EJEMPLO DE BUENA SINOPSIS enfocada en eventos de ALTO IMPACTO (4-6 frases):
"Isabel, la heredera de la mansión Aldebarán, ha desaparecido sin dejar rastro. Elena Montero llega para investigar el caso y descubre comportamientos extraños en el servicio, que parece ocultar información. Al explorar la casa, encuentra cartas antiguas que revelan secretos familiares enterrados durante décadas. La tensión aumenta cuando nota que alguien está saboteando activamente su investigación. Elena debe descubrir qué pasó con Isabel antes de que sea demasiado tarde."

CONTRAEJEMPLO DE MAL RESUMEN (demasiado anodino):
"Elena Montero llegó a la mansión Aldebarán un lunes de noviembre. Don Ramiro la esperaba en el porche. Se instaló en su habitación y conoció al servicio."

Responde SOLO con este JSON (el valor DEBE ser un string de texto narrativo, NO un objeto estructurado):
{{"global_summary": "[tu sinopsis narrativa aquí]"}}"""


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
        document_type: str = "FIC",
        document_subtype: str | None = None,
    ):
        from ..persistence.database import get_database

        self.db = get_database(db_path)
        self.mode = mode
        self.llm_model = llm_model
        self.document_type = document_type
        self.document_subtype = document_subtype
        self._ollama_client = None
        self._embeddings_model = None

    @property
    def ollama_client(self):
        """Lazy loading del cliente LLM local."""
        if self._ollama_client is None and self.mode != AnalysisMode.BASIC:
            try:
                from ..llm.client import get_llm_client

                self._ollama_client = get_llm_client()
            except Exception as e:
                logger.warning(f"No se pudo inicializar LLM client: {e}")
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

        # Cargar tipo/subtipo de documento desde BD si no se pasó al constructor
        if self.document_type == "FIC":
            db_type, db_subtype = self._get_document_type(project_id)
            if db_type:
                self.document_type = db_type
            if db_subtype:
                self.document_subtype = db_subtype

        all_characters = self._get_characters(project_id)
        report.total_characters = len(all_characters)

        first_appearances = self._get_first_appearances(project_id)
        last_appearances: dict[int, int] = {}

        # Context threading: acumular personajes conocidos y resumen previo
        known_character_names: list[str] = []
        prev_llm_summary: str | None = None
        genre_hints: list[str] = []  # Para consenso LLM

        # Procesar cada capítulo
        for idx, chapter in enumerate(chapters, 1):
            logger.info(
                f"Analizando capítulo {idx}/{len(chapters)} (LLM: {self.mode.value}, modelo: {self.llm_model})..."
            )
            chapter_summary = self._analyze_chapter(
                project_id=project_id,
                chapter=chapter,
                all_characters=all_characters,
                first_appearances=first_appearances,
                last_appearances=last_appearances,
                total_chapters=report.total_chapters,
                known_character_names=known_character_names,
                prev_llm_summary=prev_llm_summary,
            )
            report.chapters.append(chapter_summary)

            for char in chapter_summary.characters_present:
                last_appearances[char.entity_id] = chapter["chapter_number"]
                if char.name not in known_character_names:
                    known_character_names.append(char.name)

            # Actualizar resumen previo para el siguiente capítulo
            prev_llm_summary = chapter_summary.llm_summary or chapter_summary.auto_summary

            # Acumular genre_hints de capítulos narrativos
            ch_type = getattr(chapter_summary, "_chapter_type", "narrative")
            ch_hint = getattr(chapter_summary, "_genre_hint", None)
            if ch_type == "narrative" and ch_hint:
                genre_hints.append(ch_hint)

        # Consenso de genre_hints del LLM
        if genre_hints:
            self._apply_genre_consensus(genre_hints, project_id)

        # Detectar personajes dormidos
        if report.total_chapters >= 3:
            recent_chapters = set(
                range(max(1, report.total_chapters - 2), report.total_chapters + 1)
            )
            for char_id, char_name in all_characters.items():
                last_ch = last_appearances.get(char_id, 0)
                if last_ch not in recent_chapters and last_ch > 0:
                    report.dormant_characters.append(char_name)
            report.active_characters = report.total_characters - len(report.dormant_characters)
        else:
            report.active_characters = report.total_characters

        # Calcular arcos de personajes (básico)
        report.character_arcs = self._calculate_character_arcs(report.chapters, all_characters)

        # Análisis avanzado con LLM
        if self.mode != AnalysisMode.BASIC:
            self._enhance_with_llm(report, all_characters)

        # Resumen global del manuscrito (1 sola llamada LLM, incluso en modo basic)
        self._generate_global_summary(report, all_characters)

        # Detectar Chekhov's Guns
        report.chekhov_elements = self._detect_chekhov_elements(project_id)

        return report

    def _get_document_type(self, project_id: int) -> tuple[str | None, str | None]:
        """Obtiene el tipo y subtipo de documento desde la BD."""
        try:
            with self.db.connection() as conn:
                row = conn.execute(
                    "SELECT document_type, document_subtype FROM projects WHERE id = ?",
                    (project_id,),
                ).fetchone()
                if row:
                    return row["document_type"], row["document_subtype"]
        except Exception:
            pass
        return None, None

    def _apply_genre_consensus(self, genre_hints: list[str], project_id: int) -> None:
        """Aplica consenso de genre_hints del LLM para refinar subgénero.

        Vota el hint más frecuente entre capítulos narrativos.
        Si difiere del heurístico, usa el del LLM (tiene más contexto).
        """
        from collections import Counter

        # Normalizar hints
        normalized = [h.lower().strip() for h in genre_hints if h]
        if not normalized:
            return

        hint_counts = Counter(normalized)
        best_hint, best_count = hint_counts.most_common(1)[0]

        # Mapeo de hints libres a códigos de subtipo
        hint_to_subtype: dict[str, str] = {
            "policial": "FIC_POL",
            "misterio": "FIC_POL",
            "detective": "FIC_POL",
            "noir": "FIC_POL",
            "crimen": "FIC_POL",
            "romance": "FIC_ROM",
            "romántica": "FIC_ROM",
            "romántico": "FIC_ROM",
            "amor": "FIC_ROM",
            "thriller": "FIC_THR",
            "suspense": "FIC_THR",
            "intriga": "FIC_THR",
            "fantasía": "FIC_FAN",
            "fantasy": "FIC_FAN",
            "épica": "FIC_FAN",
            "ciencia ficción": "FIC_SCI",
            "sci-fi": "FIC_SCI",
            "espacial": "FIC_SCI",
            "terror": "FIC_TER",
            "horror": "FIC_TER",
            "gótico": "FIC_TER",
            "histórica": "FIC_HIS",
            "histórico": "FIC_HIS",
            "época": "FIC_HIS",
            "literaria": "FIC_LIT",
            "literario": "FIC_LIT",
        }

        llm_subtype = hint_to_subtype.get(best_hint)
        if not llm_subtype:
            logger.debug(f"Genre hint '{best_hint}' not mapped to known subtype")
            return

        # Solo actualizar si el LLM tiene señal fuerte (>50% consenso)
        consensus_ratio = best_count / len(normalized)
        if consensus_ratio < 0.5:
            logger.debug(f"Genre consensus too weak: {best_hint} ({best_count}/{len(normalized)})")
            return

        # Comparar con heurística actual
        if self.document_subtype and self.document_subtype == llm_subtype:
            logger.debug(f"LLM genre consensus matches heuristic: {llm_subtype}")
            return

        # El LLM difiere o no había subgénero heurístico → actualizar
        logger.info(
            f"LLM genre consensus: {best_hint} → {llm_subtype} "
            f"({best_count}/{len(normalized)} chapters, "
            f"heuristic was: {self.document_subtype or 'none'})"
        )
        self.document_subtype = llm_subtype

        # Persistir en BD
        try:
            with self.db.connection() as conn:
                conn.execute(
                    "UPDATE projects SET document_subtype = ? WHERE id = ?",
                    (llm_subtype, project_id),
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Could not persist LLM genre consensus: {e}")

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

    def _get_mentions_by_chapter(self, project_id: int, chapter_id: int) -> dict[int, list[dict]]:
        """Obtiene menciones agrupadas por entidad para un capítulo."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT em.entity_id, em.surface_form, em.start_char, em.end_char,
                       e.canonical_name, e.entity_type
                FROM entity_mentions em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.chapter_id = ? AND e.project_id = ?
                  AND e.is_active = 1
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

    def _get_interactions_by_chapter(self, project_id: int, chapter_id: int) -> list[dict]:
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
                  AND e.is_active = 1
                ORDER BY LOWER(e.canonical_name)
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
        total_chapters: int = 0,
        known_character_names: list[str] | None = None,
        prev_llm_summary: str | None = None,
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

        summary.locations_mentioned = self._get_locations_by_chapter(project_id, chapter_id)

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

        summary.auto_summary = self._generate_text_summary(summary, chapter_text)

        # Análisis LLM del capítulo
        if self.mode != AnalysisMode.BASIC and chapter_text:
            self._analyze_chapter_with_llm(
                summary,
                chapter_text,
                total_chapters=total_chapters,
                known_character_names=known_character_names or [],
                prev_llm_summary=prev_llm_summary,
            )

        return summary

    def _detect_pattern_events(self, summary: ChapterSummary, text: str, chapter_num: int) -> None:
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
        self,
        summary: ChapterSummary,
        chapter_text: str,
        total_chapters: int = 0,
        known_character_names: list[str] | None = None,
        prev_llm_summary: str | None = None,
    ) -> None:
        """Analiza el capítulo con LLM para extraer eventos significativos."""
        if not self.ollama_client:
            return

        try:
            from narrative_assistant.llm.sanitization import sanitize_for_prompt

            # Sanitizar texto del manuscrito antes de enviarlo al LLM (A-10)
            max_chars = 6000
            text_to_analyze = sanitize_for_prompt(chapter_text[:max_chars], max_length=max_chars)

            # Validar que el texto sanitizado no quedó vacío
            if not text_to_analyze or not text_to_analyze.strip():
                logger.warning(
                    f"Capítulo {summary.chapter_number}: texto vacío tras sanitización, "
                    "saltando análisis LLM"
                )
                return

            if len(chapter_text) > max_chars:
                text_to_analyze += "\n[... texto truncado ...]"

            title_part = f" - {summary.chapter_title}" if summary.chapter_title else ""

            # Construir bloques de contexto
            genre_label = _get_genre_label(self.document_type, self.document_subtype)
            genre_instruction = _get_genre_instruction(self.document_type, self.document_subtype)

            # Roster de personajes conocidos
            character_roster_block = ""
            if known_character_names:
                roster = ", ".join(known_character_names[:20])
                character_roster_block = f"- Personajes conocidos: {roster}\n"

            # Resumen del capítulo anterior
            prev_summary_block = ""
            if prev_llm_summary:
                sanitized_prev = sanitize_for_prompt(prev_llm_summary, max_length=300)
                prev_summary_block = f"- Capítulo anterior: {sanitized_prev}\n"

            prompt = EVENTS_EXTRACTION_PROMPT.format(
                genre_label=genre_label,
                chapter_num=summary.chapter_number,
                total_chapters=total_chapters or "?",
                title_part=title_part,
                character_roster_block=character_roster_block,
                prev_summary_block=prev_summary_block,
                text=text_to_analyze,
                genre_instruction=genre_instruction,
            )

            response = self.ollama_client.complete(
                prompt=prompt,
                model_name=self.llm_model,
                temperature=0.3,
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

                # Parsear chapter_type y genre_hint (Frente 1D)
                chapter_type = data.get("chapter_type", "narrative")
                genre_hint = data.get("genre_hint")

                # Almacenar como atributos privados para el loop de analyze_project
                summary._chapter_type = chapter_type  # type: ignore[attr-defined]
                summary._genre_hint = genre_hint  # type: ignore[attr-defined]

                # Log character_inferences si existen
                char_inferences = data.get("character_inferences", [])
                if char_inferences:
                    logger.info(
                        f"Cap. {summary.chapter_number} character inferences: "
                        f"{[ci.get('character', '?') + '=' + ci.get('inferred_role', '?') for ci in char_inferences]}"
                    )

        except Exception as e:
            logger.warning(f"Error en análisis LLM del capítulo {summary.chapter_number}: {e}")

    def _generate_text_summary(self, summary: ChapterSummary, chapter_text: str = "") -> str:
        """Genera un resumen narrativo extractivo del capítulo.

        Selecciona las oraciones más representativas del texto original
        usando scoring por: posición, mención de personajes, eventos
        narrativos y relevancia estructural.
        """
        if not chapter_text or not chapter_text.strip():
            return "Sin contenido disponible para generar resumen."

        sentences = self._split_into_sentences(chapter_text)
        if not sentences:
            return "Sin contenido disponible para generar resumen."

        # Nombres de personajes presentes (para scoring)
        char_names = {c.name.lower() for c in summary.characters_present}
        # También incluir formas parciales (primer nombre)
        char_first_names: set[str] = set()
        for name in char_names:
            parts = name.split()
            if parts:
                char_first_names.add(parts[0])
                if len(parts) > 1:
                    char_first_names.add(parts[-1])
        all_names = char_names | char_first_names

        scored: list[tuple[float, int, str]] = []
        n_sents = len(sentences)

        for idx, sent in enumerate(sentences):
            score = self._score_sentence(sent, idx, n_sents, all_names)
            scored.append((score, idx, sent))

        # Seleccionar top oraciones manteniendo orden original
        scored.sort(key=lambda x: x[0], reverse=True)

        # Cuántas oraciones elegir (INCREMENTADO: 3-6 según longitud del texto)
        max_sents = 3 if len(chapter_text) < 3000 else (5 if len(chapter_text) < 8000 else 6)
        selected = sorted(scored[:max_sents], key=lambda x: x[1])  # Orden original

        result = " ".join(s[2] for s in selected)

        # Limitar a ~600 caracteres (INCREMENTADO de 400)
        if len(result) > 600:
            result = result[:597].rsplit(" ", 1)[0] + "..."

        return result if result.strip() else "Sin contenido disponible para generar resumen."

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Divide texto en oraciones para resumen extractivo."""
        # Eliminar diálogo (rayas) — el resumen debe ser narrativo
        lines = text.split("\n")
        narrative_lines = []
        for line in lines:
            stripped = line.strip()
            # Ignorar líneas de diálogo y separadores
            if stripped.startswith(("—", "–", '-"', "«")) or stripped in ("", "* * *", "***"):
                continue
            narrative_lines.append(stripped)

        narrative_text = " ".join(narrative_lines)
        # Limpiar espacios múltiples
        narrative_text = re.sub(r"\s+", " ", narrative_text).strip()

        if not narrative_text:
            return []

        # Split por puntuación de fin de oración
        raw_sents = re.split(r"(?<=[.!?])\s+", narrative_text)

        result = []
        for s in raw_sents:
            s = s.strip()
            # Filtrar oraciones demasiado cortas o sin contenido real
            if len(s) < 20:
                continue
            # Filtrar fragmentos que son solo nombres propios
            words = s.split()
            if len(words) < 4:
                continue
            result.append(s)

        return result

    @staticmethod
    def _score_sentence(sent: str, idx: int, total: int, char_names: set[str]) -> float:
        """Puntúa una oración para resumen extractivo.

        Criterios:
        - Posición: leve bonus a inicio/final (no dominante)
        - Personajes: menciona personajes presentes en el capítulo
        - Eventos narrativos significativos: muerte, desaparición, revelación, etc.
        - Conectores causales: indican progresión narrativa
        - Longitud: ni demasiado corta ni demasiado larga
        """
        score = 0.0
        sent_lower = sent.lower()

        # --- Posición (bonus MUY leve, NO debe dominar) ---
        # REDUCIDO: primera oración suele ser setup trivial, no el evento principal
        if idx == 0:
            score += 0.3
        elif idx == 1:
            score += 0.2
        # Últimas oraciones suelen cerrar/concluir — bonus moderado
        if total > 3 and idx >= total - 2:
            score += 0.8

        # --- Mención de personajes (alta prioridad) ---
        name_hits = sum(1 for name in char_names if name in sent_lower)
        score += min(name_hits * 1.2, 3.6)  # Max 3.6 puntos por personajes

        # --- Eventos narrativos de alto impacto (PRIORIDAD MÁXIMA) ---
        high_impact_patterns = [
            r"\b(?:desapareci|desaparic|muri|muert|asesina|matar|mat[óo])\w*\b",
            r"\b(?:revel|confes|descubr|secret|traicion|enga[ñn])\w*\b",
            r"\b(?:secuestr|rapt|encarcel|prision|encerr|captur)\w*\b",
            r"\b(?:cadáver|cuerpo sin vida|sangre|herida|arma)\b",
        ]
        for pattern in high_impact_patterns:
            if re.search(pattern, sent_lower):
                score += 4.0  # INCREMENTADO de 2.0 a 4.0

        # --- Verbos de acción narrativa significativa ---
        action_patterns = [
            r"\b(?:decid|resolv|comprend|interrog|investig|examin|inspeccion)\w+\b",
            r"\b(?:huy|escap|regres|abandon|march|desaparec)\w+\b",
            r"\b(?:enfrent|luch|atac|defend|acus|culp)\w+\b",
            r"\b(?:prometi|jur|advirti|amenaz|exigi|orden)\w+\b",
            r"\b(?:naci|transform|cambi|convirti|volvi)\w+\b",
            r"\b(?:testific|declar|afirm|neg|reconoc|admit)\w+\b",  # NUEVO: testimonios
            r"\b(?:sospech|dud|desconfí|tem|tem[ií])\w+\b",  # NUEVO: sospechas
        ]
        for pattern in action_patterns:
            if re.search(pattern, sent_lower):
                score += 1.5  # INCREMENTADO de 1.2

        # --- Conectores causales/temporales (indican progresión narrativa) ---
        if re.search(
            r"\b(?:por eso|por lo tanto|entonces|así que|de modo que|sin embargo|"
            r"no obstante|mientras tanto|después de|antes de|cuando)\b",
            sent_lower,
        ):
            score += 0.5

        # --- Contraste/negación (suelen indicar giros) ---
        if re.search(
            r"\b(?:pero|aunque|a pesar de|en cambio|nadie|nunca|jamás|"
            r"tampoco|ni siquiera|no lograba|no podía)\b",
            sent_lower,
        ):
            score += 0.5

        # --- Penalización por oraciones genéricas/descriptivas (INCREMENTADA) ---
        # Oraciones de setup ambiental/temporal genérico
        if re.search(r"^(?:el sol|la noche|el día|hacía|era un|llegó a|se encontraba)\b", sent_lower):
            score -= 2.5  # INCREMENTADO de -1.0
        # Penalizar acciones cotidianas rutinarias
        if re.search(
            r"\b(?:se levant|despert|desayun|camin|se sent[óo]|cerr[óo] la puerta|esperaba en|"
            r"le explicó|habló con|conversó|charlaron)\b",
            sent_lower,
        ):
            score -= 1.5  # INCREMENTADO de -0.5
        # Penalizar descripciones triviales sin eventos
        if re.search(
            r"\b(?:estaba podando|regando|limpiando|cocinando|preparando|ordenando)\b",
            sent_lower,
        ):
            score -= 2.0  # NUEVO: penalizar acciones descriptivas sin impacto narrativo

        # --- Longitud óptima (40-180 chars) ---
        length = len(sent)
        if 40 <= length <= 180:
            score += 0.3
        elif length > 300:
            score -= 0.3

        return score

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
                presence_map[char.entity_id].append((chapter.chapter_number, char.mention_count))

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
            from narrative_assistant.llm.sanitization import sanitize_for_prompt

            # Sanitizar resúmenes antes de enviarlo al LLM (A-10)
            chapter_summaries = []
            for ch in report.chapters:
                summary_text = ch.llm_summary or ch.auto_summary
                chapter_summaries.append(
                    f"Cap. {ch.chapter_number}: {sanitize_for_prompt(summary_text, max_length=500)}"
                )

            main_chars = list(all_characters.values())[:10]

            prompt = NARRATIVE_ARCS_PROMPT.format(
                chapter_summaries="\n".join(chapter_summaries),
                main_characters=", ".join(
                    sanitize_for_prompt(c, max_length=100) for c in main_chars
                ),
            )

            response = self.ollama_client.complete(
                prompt=prompt,
                model_name=self.llm_model,
                temperature=0.3,
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

        # Resumen global se genera en _generate_global_summary() — llamado aparte

    def _generate_global_summary(
        self, report: ChapterProgressReport, all_characters: dict[int, str]
    ) -> None:
        """Genera resumen global del manuscrito con 1 llamada LLM.

        Se invoca para TODOS los modos (incluyendo basic) porque solo requiere
        una única llamada LLM y el valor para el usuario es alto.
        Inicializa su propio cliente Ollama si es necesario (en modo basic,
        self.ollama_client es None por diseño).
        """
        # Obtener cliente LLM — en modo basic, self.ollama_client es None por el
        # guard en la property. Lo inicializamos aquí directamente.
        client = self._ollama_client
        if client is None:
            try:
                from ..llm.client import get_llm_client

                client = get_llm_client()
            except Exception as e:
                logger.debug(f"LLM client not available for global summary: {e}")
                return
        if not client:
            return

        try:
            import json

            from narrative_assistant.llm.sanitization import sanitize_for_prompt

            genre_label = _get_genre_label(self.document_type, self.document_subtype)
            main_chars = list(all_characters.values())[:10]

            # Filtrar solo capítulos narrativos para el resumen global
            narrative_summaries = []
            for ch in report.chapters:
                ch_type = getattr(ch, "_chapter_type", "narrative")
                if ch_type in ("front_matter", "back_matter"):
                    continue
                summary_text = ch.llm_summary or ch.auto_summary
                narrative_summaries.append(
                    f"Cap. {ch.chapter_number}: {sanitize_for_prompt(summary_text, max_length=400)}"
                )

            if not narrative_summaries:
                return

            global_prompt = GLOBAL_SUMMARY_PROMPT.format(
                genre_label=genre_label,
                characters=", ".join(sanitize_for_prompt(c, max_length=100) for c in main_chars),
                all_chapter_summaries="\n".join(narrative_summaries),
            )

            global_response = client.complete(
                prompt=global_prompt,
                model_name=self.llm_model,
                temperature=0.3,
            )

            if global_response:
                clean_global = global_response.strip()
                if clean_global.startswith("```"):
                    clean_global = re.sub(r"^```(?:json)?\n?", "", clean_global)
                    clean_global = re.sub(r"\n?```$", "", clean_global)

                global_data = json.loads(clean_global)
                summary_val = global_data.get("global_summary")

                # LLM a veces devuelve un dict en vez de string — extraer texto
                if isinstance(summary_val, dict):
                    # Extraer recursivamente todos los strings del dict
                    def _extract_strings(obj: object) -> list[str]:
                        if isinstance(obj, str):
                            return [obj]
                        if isinstance(obj, dict):
                            parts: list[str] = []
                            for v in obj.values():
                                parts.extend(_extract_strings(v))
                            return parts
                        if isinstance(obj, list):
                            parts = []
                            for item in obj:
                                parts.extend(_extract_strings(item))
                            return parts
                        return []

                    all_parts = _extract_strings(summary_val)
                    summary_val = " ".join(all_parts) if all_parts else None
                elif isinstance(summary_val, list):
                    summary_val = " ".join(str(s) for s in summary_val)

                if isinstance(summary_val, str) and len(summary_val) > 20:
                    report.global_summary = summary_val
                    logger.info(f"Global summary generated: {len(summary_val)} chars")
                else:
                    logger.warning(
                        f"Global summary rejected: type={type(summary_val).__name__}, "
                        f"len={len(summary_val) if isinstance(summary_val, str) else 'N/A'}, "
                        f"raw={repr(summary_val)[:200]}"
                    )

        except Exception as e:
            logger.warning(f"Error generating global summary: {e}", exc_info=True)

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
                    setup_context = (
                        f"{ctx_row['context_before'] or ''} {name} {ctx_row['context_after'] or ''}"
                    )
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
    document_type: str = "FIC",
    document_subtype: str | None = None,
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
        document_type: Tipo de documento (FIC, MEM, etc.)
        document_subtype: Subtipo (FIC_POL, etc.)

    Returns:
        ChapterProgressReport con el análisis completo
    """
    analysis_mode = AnalysisMode(mode)
    analyzer = ChapterSummaryAnalyzer(
        db_path,
        mode=analysis_mode,
        llm_model=llm_model,
        document_type=document_type,
        document_subtype=document_subtype,
    )
    revision = _get_project_revision(analyzer.db, project_id)
    cache_key = f"{project_id}:{mode}:{llm_model}:{document_type}:rev{revision}"
    now = time.monotonic()

    with _cache_lock:
        if cache_key in _cache:
            ts, cached_report = _cache[cache_key]
            if now - ts < _CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for chapter progress: project={project_id}, mode={mode}")
                return cached_report
            else:
                del _cache[cache_key]

    report = analyzer.analyze_project(project_id)

    with _cache_lock:
        _cache[cache_key] = (time.monotonic(), report)
        # Limpiar entradas expiradas
        expired = [k for k, (ts, _) in _cache.items() if now - ts >= _CACHE_TTL_SECONDS]
        for k in expired:
            del _cache[k]

    return report


def _get_project_revision(db_session, project_id: int) -> int:
    """Obtiene la revisión de invalidación para invalidar cachés en memoria."""
    try:
        with db_session.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(revision), 0) AS revision
                FROM invalidation_events
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            if row is None:
                return 0
            try:
                return int(row["revision"])
            except Exception:
                return int(row[0])
    except Exception:
        # Compatibilidad con DBs antiguas sin tabla invalidation_events.
        return 0


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
