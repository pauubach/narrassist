"""
Análisis de estado vital de personajes.

Detecta eventos de muerte y verifica que personajes fallecidos
no reaparezcan como vivos posteriormente.

Genera alertas de tipo CONSISTENCY cuando:
- Un personaje muere en capítulo N
- Y aparece actuando/hablando en capítulo M > N
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.errors import NLPError
from ..core.result import Result

logger = logging.getLogger(__name__)


class VitalStatus(Enum):
    """Estado vital de un personaje."""

    ALIVE = "alive"  # Vivo (estado por defecto)
    DEAD = "dead"  # Muerto confirmado
    PRESUMED_DEAD = "presumed_dead"  # Presumiblemente muerto (no confirmado)
    UNKNOWN = "unknown"  # Estado desconocido


@dataclass
class DeathEvent:
    """
    Evento de muerte detectado en el texto.

    Representa el momento en que un personaje muere o es declarado muerto.
    """

    entity_id: int
    entity_name: str
    chapter: int
    start_char: int
    end_char: int
    excerpt: str  # Texto donde se menciona la muerte
    death_type: str  # "direct", "narrated", "reported", "implied"
    confidence: float = 0.8

    # Metadatos
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "chapter": self.chapter,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "excerpt": self.excerpt,
            "death_type": self.death_type,
            "confidence": self.confidence,
        }


@dataclass
class PostMortemAppearance:
    """
    Aparición de un personaje después de su muerte.

    Puede ser:
    - Un error de continuidad (bug narrativo)
    - Referencia válida (recuerdo, fantasma, flashback)
    """

    entity_id: int
    entity_name: str
    death_chapter: int
    appearance_chapter: int
    appearance_start_char: int
    appearance_end_char: int
    appearance_excerpt: str
    appearance_type: str  # "dialogue", "action", "narration"
    is_valid: bool = False  # True si es referencia válida (flashback, recuerdo)
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "death_chapter": self.death_chapter,
            "appearance_chapter": self.appearance_chapter,
            "appearance_start_char": self.appearance_start_char,
            "appearance_end_char": self.appearance_end_char,
            "appearance_excerpt": self.appearance_excerpt,
            "appearance_type": self.appearance_type,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
        }


@dataclass
class VitalStatusReport:
    """
    Reporte de estado vital para un proyecto.

    Contiene eventos de muerte detectados y apariciones post-mortem.
    """

    project_id: int
    death_events: list[DeathEvent] = field(default_factory=list)
    post_mortem_appearances: list[PostMortemAppearance] = field(default_factory=list)
    entities_status: dict[int, VitalStatus] = field(default_factory=dict)

    @property
    def inconsistencies(self) -> list[PostMortemAppearance]:
        """Apariciones post-mortem que son inconsistencias (no válidas)."""
        return [a for a in self.post_mortem_appearances if not a.is_valid]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "death_events": [e.to_dict() for e in self.death_events],
            "post_mortem_appearances": [
                a.to_dict() for a in self.post_mortem_appearances
            ],
            "inconsistencies_count": len(self.inconsistencies),
            "entities_status": {k: v.value for k, v in self.entities_status.items()},
        }


class VitalStatusAnalyzer:
    """
    Analizador de estado vital de personajes.

    Detecta muertes de personajes y verifica que no reaparezcan
    como vivos después de morir.
    """

    # Patrones para detectar muerte directa (el personaje muere)
    DEATH_DIRECT_PATTERNS = [
        # Verbos de muerte en pasado
        r"(?P<name>\w+)\s+(?:murió|falleció|pereció|expiró)",
        r"(?P<name>\w+)\s+(?:cayó\s+muert[oa]|cayó\s+sin\s+vida)",
        r"(?P<name>\w+)\s+(?:dejó\s+de\s+respirar|exhaló\s+su\s+último\s+aliento)",
        r"el\s+(?:cadáver|cuerpo\s+sin\s+vida)\s+de\s+(?P<name>\w+)",
        r"(?P<name>\w+)\s+(?:ya\s+no\s+respiraba|estaba\s+muert[oa])",
    ]

    # Patrones para muerte causada (alguien mata al personaje)
    DEATH_CAUSED_PATTERNS = [
        r"(?:mató|mataron|asesinó|asesinaron|ejecutó|ejecutaron)\s+a\s+(?P<name>\w+)",
        r"(?:lo|la|le)\s+(?:mató|mataron|asesinó|asesinaron)\s+a\s+(?P<name>\w+)",
        r"(?P<name>\w+)\s+(?:fue\s+asesinado|fue\s+ejecutado|fue\s+matado)",
        r"(?:la\s+muerte|el\s+asesinato)\s+de\s+(?P<name>\w+)",
        r"(?:disparó|dispararon|apuñaló|apuñalaron|envenenó|envenenaron|ahorcó|ahorcaron|degolló|degollaron)\s+a\s+(?P<name>\w+)",
    ]

    # Patrones para muerte reportada (se informa de la muerte)
    DEATH_REPORTED_PATTERNS = [
        r"(?P<name>\w+)\s+(?:ha\s+muerto|está\s+muerto)",
        r"(?:supieron|descubrieron|se\s+enteraron)\s+(?:de\s+)?que\s+(?P<name>\w+)\s+(?:murió|falleció)",
        r"(?:anunciaron|comunicaron|informaron)\s+(?:de\s+)?(?:la\s+muerte|el\s+fallecimiento)\s+de\s+(?P<name>\w+)",
        r"(?P<name>\w+)\s+(?:no\s+sobrevivió|no\s+lo\s+logró)",
    ]

    # Patrones para muerte en pluscuamperfecto (pasado relativo, ambigua)
    DEATH_PLUPERFECT_PATTERNS = [
        r"(?P<name>\w+)\s+(?:había\s+muerto|había\s+fallecido|ya\s+había\s+muerto)",
        r"(?P<name>\w+)\s+(?:había\s+sido\s+asesinado|había\s+sido\s+ejecutado)",
        r"(?:hacía|hace)\s+\w+\s+que\s+(?P<name>\w+)\s+(?:murió|falleció|había\s+muerto)",
        r"(?:supieron|descubrieron|se\s+enteraron)\s+(?:de\s+)?que\s+(?P<name>\w+)\s+había\s+(?:muerto|fallecido)",
    ]

    # Patrones para muerte implícita (presumido muerto)
    DEATH_IMPLIED_PATTERNS = [
        r"(?:el\s+cuerpo|los\s+restos)\s+de\s+(?P<name>\w+)",
        r"(?P<name>\w+)\s+(?:nunca\s+regresó|desapareció\s+para\s+siempre)",
        r"(?:la\s+tumba|la\s+lápida)\s+de\s+(?P<name>\w+)",
        r"(?:en\s+memoria|en\s+honor)\s+(?:a|de)\s+(?P<name>\w+)",
    ]

    # Patrones que indican que la mención es válida (no inconsistencia)
    VALID_REFERENCE_PATTERNS = [
        r"(?:recordaba|recordó)\s+(?:a\s+)?(?P<name>\w+)",
        r"(?:el\s+recuerdo|la\s+memoria)\s+de\s+(?P<name>\w+)",
        r"(?:el\s+fantasma|el\s+espíritu|el\s+espectro)\s+de\s+(?P<name>\w+)",
        r"(?:como|igual\s+que)\s+(?P<name>\w+)\s+(?:solía|hacía)",
        r"(?:pensaba|pensó)\s+en\s+(?P<name>\w+)",
        r"(?:soñaba|soñó)\s+con\s+(?P<name>\w+)",
        r"(?P<name>\w+)\s+(?:le\s+)?(?:había\s+)?dicho\s+(?:una\s+vez|antes)",
        # Flashback markers
        r"años?\s+(?:antes|atrás)",
        r"(?:en\s+el\s+pasado|tiempo\s+atrás)",
        r"(?:cuando|mientras)\s+(?P<name>\w+)\s+(?:vivía|estaba\s+vivo)",
    ]

    # Patrones que indican acción activa (inconsistente si está muerto)
    ACTIVE_ACTION_PATTERNS = [
        r"(?P<name>\w+)\s+(?:dijo|respondió|preguntó|exclamó|gritó|susurró)",
        r"(?P<name>\w+)\s+(?:se\s+levantó|caminó|corrió|saltó|entró|salió)",
        r"(?P<name>\w+)\s+(?:miró|observó|vio|escuchó|oyó)",
        r"(?P<name>\w+)\s+(?:tomó|agarró|cogió|soltó|dejó|puso)",
        r"(?P<name>\w+)\s+(?:sonrió|rió|lloró|suspiró|frunció)",
    ]

    def __init__(self, project_id: int, temporal_map=None):
        self.project_id = project_id
        self._temporal_map = temporal_map

        # Estado interno
        self._death_events: dict[int, DeathEvent] = {}  # entity_id -> DeathEvent
        self._entity_names: dict[int, str] = {}
        self._name_to_id: dict[str, int] = {}

    def register_entity(self, entity_id: int, name: str, aliases: list[str] = None):
        """Registra una entidad para el análisis."""
        self._entity_names[entity_id] = name
        self._name_to_id[name.lower()] = entity_id

        if aliases:
            for alias in aliases:
                self._name_to_id[alias.lower()] = entity_id

    def get_entity_id(self, name: str) -> int | None:
        """Obtiene el ID de entidad para un nombre."""
        return self._name_to_id.get(name.lower())

    def detect_death_events(
        self,
        text: str,
        chapter: int,
        start_offset: int = 0,
    ) -> list[DeathEvent]:
        """
        Detecta eventos de muerte en el texto.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            start_offset: Offset para posiciones absolutas

        Returns:
            Lista de eventos de muerte detectados
        """
        events = []
        # Track entities already found in this chapter to avoid duplicates
        found_in_chapter: set[int] = set()

        # Patrones y sus tipos
        pattern_groups = [
            (self.DEATH_DIRECT_PATTERNS, "direct"),
            (self.DEATH_CAUSED_PATTERNS, "caused"),
            (self.DEATH_REPORTED_PATTERNS, "reported"),
            (self.DEATH_PLUPERFECT_PATTERNS, "pluperfect"),
            (self.DEATH_IMPLIED_PATTERNS, "implied"),
        ]

        for patterns, death_type in pattern_groups:
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    name = match.group("name").lower()
                    entity_id = self.get_entity_id(name)

                    if not entity_id:
                        continue

                    # No duplicar si ya encontramos muerte para esta entidad en este capítulo
                    if entity_id in found_in_chapter:
                        continue

                    # No duplicar si ya tenemos muerte para esta entidad en cap anterior
                    if entity_id in self._death_events:
                        existing = self._death_events[entity_id]
                        if existing.chapter < chapter:
                            continue  # Ya murió antes

                    # Extraer contexto (expandido para capturar marcadores)
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(text), match.end() + 100)
                    excerpt = text[context_start:context_end]

                    # BK-08: Descartar muertes especulativas (irrealis)
                    if self._is_speculative_death(excerpt):
                        logger.debug(
                            f"Skipping speculative death for {name} in chapter {chapter}"
                        )
                        continue

                    # Calcular confianza según tipo
                    confidence_map = {
                        "direct": 0.95,
                        "caused": 0.90,
                        "reported": 0.85,
                        "pluperfect": 0.65,
                        "implied": 0.60,
                    }

                    event = DeathEvent(
                        entity_id=entity_id,
                        entity_name=self._entity_names.get(entity_id, name),
                        chapter=chapter,
                        start_char=start_offset + match.start(),
                        end_char=start_offset + match.end(),
                        excerpt=excerpt,
                        death_type=death_type,
                        confidence=confidence_map.get(death_type, 0.7),
                    )

                    events.append(event)
                    self._death_events[entity_id] = event
                    found_in_chapter.add(entity_id)

                    # Registrar muerte en temporal_map si disponible
                    if self._temporal_map is not None:
                        self._temporal_map.register_death(entity_id, chapter)

                    logger.info(
                        f"Death event detected: {event.entity_name} in chapter {chapter} "
                        f"(type: {death_type}, confidence: {event.confidence:.2f})"
                    )

        return events

    def check_post_mortem_appearances(
        self,
        text: str,
        chapter: int,
        start_offset: int = 0,
    ) -> list[PostMortemAppearance]:
        """
        Verifica apariciones de personajes muertos.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo
            start_offset: Offset para posiciones absolutas

        Returns:
            Lista de apariciones post-mortem detectadas
        """
        appearances = []

        for entity_id, death_event in self._death_events.items():
            # Verificar si el personaje está vivo en este capítulo
            if self._temporal_map is not None:
                if self._temporal_map.is_character_alive_in_chapter(entity_id, chapter):
                    continue
            else:
                # Fallback: comparación lineal por capítulo
                if death_event.chapter >= chapter:
                    continue

            entity_name = death_event.entity_name
            entity_name.lower()

            # Buscar menciones activas del personaje
            for pattern in self.ACTIVE_ACTION_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matched_name = match.group("name").lower()

                    # Verificar si es este personaje
                    matched_id = self.get_entity_id(matched_name)
                    if matched_id != entity_id:
                        continue

                    # Extraer contexto amplio para verificar validez
                    # BK-08: Expandido a 250 chars para capturar marcadores de flashback
                    context_start = max(0, match.start() - 250)
                    context_end = min(len(text), match.end() + 250)
                    context = text[context_start:context_end]

                    # Verificar si es referencia válida (recuerdo, flashback, etc.)
                    is_valid = self._is_valid_reference(context, entity_name)

                    # Determinar tipo de aparición
                    if (
                        "dijo" in match.group(0).lower()
                        or "preguntó" in match.group(0).lower()
                    ):
                        appearance_type = "dialogue"
                    else:
                        appearance_type = "action"

                    appearance = PostMortemAppearance(
                        entity_id=entity_id,
                        entity_name=entity_name,
                        death_chapter=death_event.chapter,
                        appearance_chapter=chapter,
                        appearance_start_char=start_offset + match.start(),
                        appearance_end_char=start_offset + match.end(),
                        appearance_excerpt=context,
                        appearance_type=appearance_type,
                        is_valid=is_valid,
                        confidence=0.85 if not is_valid else 0.5,
                    )

                    appearances.append(appearance)

                    if not is_valid:
                        logger.warning(
                            f"Post-mortem appearance: {entity_name} appears in chapter {chapter} "
                            f"but died in chapter {death_event.chapter}"
                        )

        return appearances

    def _is_valid_reference(self, context: str, entity_name: str) -> bool:
        """
        Verifica si una mención de un personaje muerto es válida.

        Una referencia es válida si es:
        - Un recuerdo
        - Un flashback
        - Una mención del fantasma/espíritu
        - Una referencia al pasado
        """
        for pattern in self.VALID_REFERENCE_PATTERNS:
            # Reemplazar placeholder de nombre
            pattern_with_name = pattern.replace(
                r"(?P<name>\w+)", re.escape(entity_name)
            )
            if re.search(pattern_with_name, context, re.IGNORECASE):
                return True
            # También probar el patrón original
            if re.search(pattern, context, re.IGNORECASE):
                return True

        # Verificar marcadores de flashback en el contexto general
        flashback_markers = [
            "años antes",
            "años atrás",
            "tiempo atrás",
            "en el pasado",
            "recordaba",
            "recordó",
            "aquella vez",
            "cuando vivía",
            "antes de morir",
        ]
        context_lower = context.lower()
        return any(marker in context_lower for marker in flashback_markers)

    def _is_speculative_death(self, context: str) -> bool:
        """Verifica si una mención de muerte es especulativa (irrealis), no factual."""
        irrealis_markers = [
            r"\bsi\s+(?:hubiera|hubiese|habría|hubiere)\b",
            r"\bcomo\s+si\b",
            r"\b(?:imagina|imaginaba)(?:ba|mos|n)?\s+que\b",
            r"\bhabría\s+(?:podido|sabido|sido|fallecido|muerto|perecido)\b",
            r"\bpodría\s+haber\s+(?:muerto|fallecido|perecido)\b",
            r"\bqué\s+pasaría\s+si\b",
        ]
        context_lower = context.lower()
        return any(re.search(m, context_lower) for m in irrealis_markers)

    def analyze_chapter(
        self,
        text: str,
        chapter: int,
        start_offset: int = 0,
    ) -> tuple[list[DeathEvent], list[PostMortemAppearance]]:
        """
        Analiza un capítulo completo.

        Args:
            text: Texto del capítulo
            chapter: Número de capítulo
            start_offset: Offset para posiciones absolutas

        Returns:
            Tupla de (eventos de muerte, apariciones post-mortem)
        """
        death_events = self.detect_death_events(text, chapter, start_offset)
        appearances = self.check_post_mortem_appearances(text, chapter, start_offset)

        return death_events, appearances

    def get_entity_status(self, entity_id: int) -> VitalStatus:
        """Obtiene el estado vital actual de una entidad."""
        if entity_id in self._death_events:
            event = self._death_events[entity_id]
            if event.death_type == "implied":
                return VitalStatus.PRESUMED_DEAD
            return VitalStatus.DEAD
        return VitalStatus.ALIVE

    def generate_report(self) -> VitalStatusReport:
        """Genera reporte de estado vital."""
        report = VitalStatusReport(project_id=self.project_id)
        report.death_events = list(self._death_events.values())

        # Generar estado por entidad
        for entity_id in self._entity_names:
            report.entities_status[entity_id] = self.get_entity_status(entity_id)

        return report

    def clear(self):
        """Limpia el estado interno."""
        self._death_events.clear()


def analyze_vital_status(
    project_id: int,
    chapters: list[dict],
    entities: list[dict],
    temporal_map=None,
) -> Result[VitalStatusReport]:
    """
    Analiza el estado vital de personajes en todo el proyecto.

    Args:
        project_id: ID del proyecto
        chapters: Lista de capítulos con texto
        entities: Lista de entidades con nombres y aliases
        temporal_map: TemporalMap opcional para narrativas no lineales

    Returns:
        Result con VitalStatusReport
    """
    try:
        analyzer = VitalStatusAnalyzer(project_id, temporal_map=temporal_map)

        # Registrar entidades
        for entity in entities:
            if entity.get("entity_type") in ["character", "animal", "creature"]:
                analyzer.register_entity(
                    entity_id=entity["id"],
                    name=entity["canonical_name"],
                    aliases=entity.get("aliases", []),
                )

        # Analizar cada capítulo en orden
        all_death_events = []
        all_appearances = []

        for chapter in sorted(chapters, key=lambda c: c.get("number", 0)):
            chapter_num = chapter.get("number", 0)
            text = chapter.get("content", "") or chapter.get("text", "")
            start_offset = chapter.get("start_char", 0)

            if not text:
                continue

            death_events, appearances = analyzer.analyze_chapter(
                text, chapter_num, start_offset
            )

            all_death_events.extend(death_events)
            all_appearances.extend(appearances)

        # Generar reporte
        report = analyzer.generate_report()
        report.death_events = all_death_events
        report.post_mortem_appearances = all_appearances

        return Result.success(report)

    except Exception as e:
        logger.error(f"Error analyzing vital status: {e}")
        return Result.failure(NLPError(f"Error analyzing vital status: {e}"))
