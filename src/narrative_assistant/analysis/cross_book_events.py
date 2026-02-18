"""
Detección de contradicciones de eventos entre libros de una colección.

Complementa cross_book.py (que compara atributos) añadiendo comparación
de eventos narrativos entre entidades enlazadas.

Reglas de contradicción:
- death_then_alive: Personaje muere en libro A pero aparece vivo en libro B posterior
- injury_healed_differently: Herida inconsistente entre libros
- acquisition_vs_loss: Objeto poseído en un libro, perdido en otro sin evento intermedio
- location_impossibility: Personaje en dos lugares incompatibles
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .event_types import EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class EventContradiction:
    """Contradicción detectada entre eventos de dos libros."""

    rule: str  # Nombre de la regla que la detectó
    entity_name: str
    description: str
    event_a_type: str  # EventType.value del libro A
    event_b_type: str  # EventType.value del libro B
    book_a_name: str
    book_b_name: str
    book_a_chapter: int | None = None
    book_b_chapter: int | None = None
    confidence: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "entity_name": self.entity_name,
            "description": self.description,
            "event_a_type": self.event_a_type,
            "event_b_type": self.event_b_type,
            "book_a_name": self.book_a_name,
            "book_b_name": self.book_b_name,
            "book_a_chapter": self.book_a_chapter,
            "book_b_chapter": self.book_b_chapter,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CrossBookEventReport:
    """Informe de contradicciones de eventos cross-book."""

    collection_id: int
    collection_name: str
    contradictions: list[EventContradiction] = field(default_factory=list)
    entity_links_analyzed: int = 0
    projects_analyzed: int = 0

    def to_dict(self) -> dict:
        return {
            "collection_id": self.collection_id,
            "collection_name": self.collection_name,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "entity_links_analyzed": self.entity_links_analyzed,
            "projects_analyzed": self.projects_analyzed,
            "summary": {
                "total_contradictions": len(self.contradictions),
                "by_rule": self._count_by_rule(),
            },
        }

    def _count_by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.contradictions:
            counts[c.rule] = counts.get(c.rule, 0) + 1
        return counts


# ============================================================================
# Contradiction Rules
# ============================================================================

# Eventos que implican que el personaje está vivo
ALIVE_EVENTS = {
    EventType.PROMISE.value, EventType.CONFESSION.value, EventType.LIE.value,
    EventType.ACQUISITION.value, EventType.INJURY.value, EventType.HEALING.value,
    EventType.DECISION.value, EventType.BETRAYAL.value, EventType.ALLIANCE.value,
    EventType.REVELATION.value, EventType.CONFLICT_START.value,
    EventType.FIRST_MEETING.value, EventType.REUNION.value,
    EventType.SEPARATION.value, EventType.LOCATION_CHANGE.value,
    EventType.LOVE_DECLARATION.value, EventType.SOCIAL_CHANGE.value,
    EventType.RETURN.value, EventType.FIRST_APPEARANCE.value,
}


def _check_death_then_alive(
    entity_name: str,
    events_a: list[dict],
    events_b: list[dict],
    book_a_name: str,
    book_b_name: str,
    book_a_order: int,
    book_b_order: int,
) -> list[EventContradiction]:
    """
    Detecta si un personaje muere en un libro y aparece vivo en un libro posterior.
    """
    contradictions = []

    # Buscar muerte en el libro de orden menor
    if book_a_order < book_b_order:
        earlier_events, later_events = events_a, events_b
        earlier_name, later_name = book_a_name, book_b_name
    elif book_b_order < book_a_order:
        earlier_events, later_events = events_b, events_a
        earlier_name, later_name = book_b_name, book_a_name
    else:
        return []  # Mismo orden, no se puede determinar secuencia

    # ¿Muere en el libro anterior?
    death_events = [e for e in earlier_events if e["event_type"] == EventType.DEATH.value]
    if not death_events:
        return []

    # ¿Aparece vivo en el libro posterior?
    alive_events = [e for e in later_events if e["event_type"] in ALIVE_EVENTS]
    if not alive_events:
        return []

    death = death_events[-1]  # Última muerte
    alive = alive_events[0]  # Primera aparición viva

    contradictions.append(EventContradiction(
        rule="death_then_alive",
        entity_name=entity_name,
        description=(
            f"{entity_name} muere en «{earlier_name}» "
            f"pero aparece vivo/a en «{later_name}»"
        ),
        event_a_type=death["event_type"],
        event_b_type=alive["event_type"],
        book_a_name=earlier_name,
        book_b_name=later_name,
        book_a_chapter=death.get("chapter"),
        book_b_chapter=alive.get("chapter"),
        confidence=0.9,
        metadata={
            "death_description": death.get("description", ""),
            "alive_description": alive.get("description", ""),
        },
    ))

    return contradictions


def _check_injury_healed_differently(
    entity_name: str,
    events_a: list[dict],
    events_b: list[dict],
    book_a_name: str,
    book_b_name: str,
    book_a_order: int,
    book_b_order: int,
) -> list[EventContradiction]:
    """
    Detecta si una herida se describe de forma contradictoria entre libros.

    Ej: En libro A el personaje se lesiona el brazo, en libro B se menciona
    curación de la pierna.
    """
    contradictions = []

    injuries_a = [e for e in events_a if e["event_type"] == EventType.INJURY.value]
    injuries_b = [e for e in events_b if e["event_type"] == EventType.INJURY.value]
    healings_a = [e for e in events_a if e["event_type"] == EventType.HEALING.value]
    healings_b = [e for e in events_b if e["event_type"] == EventType.HEALING.value]

    # Herida en A, curación incompatible en B (o viceversa)
    for injury in injuries_a:
        injury_desc = injury.get("description", "").lower()
        for healing in healings_b:
            healing_desc = healing.get("description", "").lower()
            # Si ambos mencionan partes del cuerpo diferentes, es sospechoso
            injury_meta = injury.get("metadata", {})
            healing_meta = healing.get("metadata", {})
            body_part_a = injury_meta.get("body_part", "")
            body_part_b = healing_meta.get("body_part", "")

            if body_part_a and body_part_b and body_part_a != body_part_b:
                contradictions.append(EventContradiction(
                    rule="injury_healed_differently",
                    entity_name=entity_name,
                    description=(
                        f"{entity_name}: herida en {body_part_a} (en «{book_a_name}») "
                        f"pero curación de {body_part_b} (en «{book_b_name}»)"
                    ),
                    event_a_type=EventType.INJURY.value,
                    event_b_type=EventType.HEALING.value,
                    book_a_name=book_a_name,
                    book_b_name=book_b_name,
                    book_a_chapter=injury.get("chapter"),
                    book_b_chapter=healing.get("chapter"),
                    confidence=0.6,
                    metadata={
                        "body_part_a": body_part_a,
                        "body_part_b": body_part_b,
                    },
                ))

    return contradictions


def _check_acquisition_vs_loss(
    entity_name: str,
    events_a: list[dict],
    events_b: list[dict],
    book_a_name: str,
    book_b_name: str,
    book_a_order: int,
    book_b_order: int,
) -> list[EventContradiction]:
    """
    Detecta si un objeto adquirido en un libro aparece como perdido en otro
    sin evento de pérdida intermedio.
    """
    contradictions = []

    if book_a_order < book_b_order:
        earlier_events, later_events = events_a, events_b
        earlier_name, later_name = book_a_name, book_b_name
    elif book_b_order < book_a_order:
        earlier_events, later_events = events_b, events_a
        earlier_name, later_name = book_b_name, book_a_name
    else:
        return []

    acquisitions = [e for e in earlier_events if e["event_type"] == EventType.ACQUISITION.value]
    losses = [e for e in earlier_events if e["event_type"] == EventType.LOSS.value]
    later_losses = [e for e in later_events if e["event_type"] == EventType.LOSS.value]

    # Objetos adquiridos sin pérdida en el mismo libro
    acquired_items = set()
    for acq in acquisitions:
        item = acq.get("metadata", {}).get("object", "").lower()
        if item:
            acquired_items.add(item)
    for loss in losses:
        item = loss.get("metadata", {}).get("object", "").lower()
        acquired_items.discard(item)

    # ¿Algún objeto adquirido se pierde en el libro posterior sin explicación?
    for loss in later_losses:
        item = loss.get("metadata", {}).get("object", "").lower()
        if item and item in acquired_items:
            # Buscar si hay otra adquisición en libro posterior que lo explique
            later_acq = [
                e for e in later_events
                if e["event_type"] == EventType.ACQUISITION.value
                and e.get("metadata", {}).get("object", "").lower() == item
            ]
            if not later_acq:
                contradictions.append(EventContradiction(
                    rule="acquisition_vs_loss",
                    entity_name=entity_name,
                    description=(
                        f"{entity_name} adquiere '{item}' en «{earlier_name}» "
                        f"pero lo pierde en «{later_name}» sin evento intermedio"
                    ),
                    event_a_type=EventType.ACQUISITION.value,
                    event_b_type=EventType.LOSS.value,
                    book_a_name=earlier_name,
                    book_b_name=later_name,
                    confidence=0.5,
                    metadata={"object": item},
                ))

    return contradictions


def _check_location_impossibility(
    entity_name: str,
    events_a: list[dict],
    events_b: list[dict],
    book_a_name: str,
    book_b_name: str,
    book_a_order: int,
    book_b_order: int,
) -> list[EventContradiction]:
    """
    Detecta si el personaje está en ubicaciones imposiblemente diferentes
    al final de un libro vs el inicio del siguiente.
    """
    contradictions = []

    if book_a_order >= book_b_order:
        return []

    # Última ubicación en libro A
    loc_changes_a = [
        e for e in events_a if e["event_type"] == EventType.LOCATION_CHANGE.value
    ]
    # Primera ubicación en libro B
    loc_changes_b = [
        e for e in events_b if e["event_type"] == EventType.LOCATION_CHANGE.value
    ]

    if not loc_changes_a or not loc_changes_b:
        return []

    last_loc_a = loc_changes_a[-1].get("metadata", {}).get("location", "")
    first_loc_b = loc_changes_b[0].get("metadata", {}).get("location", "")

    if (
        last_loc_a
        and first_loc_b
        and last_loc_a.lower() != first_loc_b.lower()
    ):
        contradictions.append(EventContradiction(
            rule="location_impossibility",
            entity_name=entity_name,
            description=(
                f"{entity_name} está en '{last_loc_a}' al final de «{book_a_name}» "
                f"pero aparece en '{first_loc_b}' al inicio de «{book_b_name}»"
            ),
            event_a_type=EventType.LOCATION_CHANGE.value,
            event_b_type=EventType.LOCATION_CHANGE.value,
            book_a_name=book_a_name,
            book_b_name=book_b_name,
            confidence=0.5,
            metadata={
                "location_a": last_loc_a,
                "location_b": first_loc_b,
            },
        ))

    return contradictions


# Registro de reglas
CONTRADICTION_RULES = [
    _check_death_then_alive,
    _check_injury_healed_differently,
    _check_acquisition_vs_loss,
    _check_location_impossibility,
]


# ============================================================================
# Main Analyzer
# ============================================================================


class CrossBookEventAnalyzer:
    """
    Analiza contradicciones de eventos entre libros de una colección.

    Requiere:
    - narrative_events poblada (run_events en pipeline)
    - entity links creados en la colección
    """

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    def analyze(self, collection_id: int, validate_with_llm: bool = False) -> CrossBookEventReport:
        """
        Analiza contradicciones de eventos entre todos los libros
        de una colección.
        """
        from ..persistence.collection import CollectionRepository
        from ..persistence.event_repository import get_event_repository

        repo = CollectionRepository(self._get_db())
        collection = repo.get(collection_id)
        if not collection:
            return CrossBookEventReport(
                collection_id=collection_id,
                collection_name="(no encontrada)",
            )

        links = repo.get_entity_links(collection_id)
        projects = repo.get_projects(collection_id)

        if not links or not projects:
            return CrossBookEventReport(
                collection_id=collection_id,
                collection_name=collection.name,
                entity_links_analyzed=len(links),
                projects_analyzed=len(projects),
            )

        # Construir mapa project_id → order + name
        project_info = {}
        for p in projects:
            project_info[p.id] = {
                "name": p.name,
                "order": getattr(p, "collection_order", 0) or 0,
            }

        # Obtener eventos por proyecto (de narrative_events)
        event_repo = get_event_repository()
        events_by_project: dict[int, list[dict]] = {}

        for p in projects:
            result = event_repo.get_by_project(p.id)
            if result.is_success and result.value:
                events_by_project[p.id] = [
                    {
                        "event_type": e.event_type,
                        "description": e.description,
                        "chapter": e.chapter,
                        "confidence": e.confidence,
                        "metadata": e.metadata,
                        "entity_ids": e.entity_ids,
                    }
                    for e in result.value
                ]
            else:
                events_by_project[p.id] = []

        # Para cada entity link, filtrar eventos por entidad y comparar
        all_contradictions = []

        for link in links:
            src_project_id = link.source_project_id
            tgt_project_id = link.target_project_id
            entity_name = link.source_entity_name or link.target_entity_name

            src_info = project_info.get(src_project_id, {"name": "?", "order": 0})
            tgt_info = project_info.get(tgt_project_id, {"name": "?", "order": 0})

            # Filtrar eventos de esta entidad en cada proyecto
            events_a = self._filter_events_for_entity(
                events_by_project.get(src_project_id, []),
                link.source_entity_id,
            )
            events_b = self._filter_events_for_entity(
                events_by_project.get(tgt_project_id, []),
                link.target_entity_id,
            )

            if not events_a and not events_b:
                continue

            # Aplicar todas las reglas de contradicción
            for rule_fn in CONTRADICTION_RULES:
                contradictions = rule_fn(
                    entity_name=entity_name,
                    events_a=events_a,
                    events_b=events_b,
                    book_a_name=src_info["name"],
                    book_b_name=tgt_info["name"],
                    book_a_order=src_info["order"],
                    book_b_order=tgt_info["order"],
                )
                all_contradictions.extend(contradictions)

        # Validación LLM opcional (reduce falsos positivos)
        if validate_with_llm and all_contradictions:
            all_contradictions = self._validate_contradictions(all_contradictions)

        report = CrossBookEventReport(
            collection_id=collection_id,
            collection_name=collection.name,
            contradictions=all_contradictions,
            entity_links_analyzed=len(links),
            projects_analyzed=len(projects),
        )

        # Cache en workspace
        try:
            repo.save_workspace_cache(
                collection_id, "cross_book_events", report.to_dict()
            )
        except Exception as e:
            logger.warning(f"Could not cache cross-book events: {e}")

        logger.info(
            f"Cross-book event analysis: {len(all_contradictions)} contradictions "
            f"from {len(links)} entity links across {len(projects)} projects"
        )

        return report

    def _filter_events_for_entity(
        self, events: list[dict], entity_id: int
    ) -> list[dict]:
        """Filtra eventos que involucran a una entidad específica."""
        return [
            e for e in events
            if entity_id in e.get("entity_ids", [])
        ]

    def _validate_contradictions(
        self, contradictions: list[EventContradiction]
    ) -> list[EventContradiction]:
        """
        Valida contradicciones con LLM para reducir falsos positivos.

        Las contradicciones con veredicto DISMISSED se eliminan.
        Las demás se actualizan con la confianza ajustada.
        """
        from .contradiction_validator import get_contradiction_validator

        validator = get_contradiction_validator()
        if not validator.is_available:
            logger.info("LLM not available, skipping contradiction validation")
            return contradictions

        results = validator.validate_batch(contradictions)

        validated = []
        for result in results:
            if result.verdict == "DISMISSED":
                logger.debug(
                    f"Dismissed contradiction: {result.contradiction.rule} "
                    f"— {result.reasoning}"
                )
                continue

            # Actualizar confianza del candidato
            c = result.contradiction
            c.confidence = result.adjusted_confidence
            if result.reasoning:
                c.metadata["llm_reasoning"] = result.reasoning
            if result.narrative_explanation:
                c.metadata["narrative_explanation"] = result.narrative_explanation
            if result.models_used:
                c.metadata["llm_models"] = result.models_used
            validated.append(c)

        logger.info(
            f"LLM validation: {len(contradictions)} candidates → "
            f"{len(validated)} validated ({len(contradictions) - len(validated)} dismissed)"
        )
        return validated
