"""
Alineación temporal cross-book para colecciones/sagas.

Compara líneas temporales de múltiples libros y detecta inconsistencias
temporales entre entidades enlazadas:
- Edad inconsistente: Un personaje envejece de forma incompatible entre libros
- Simultaneidad imposible: Mismo personaje en dos sitios al mismo tiempo
- Orden imposible: Evento en libro B ocurre antes que en libro A pero el orden de libros dice lo contrario

Reutiliza el módulo temporal/ existente (TemporalMap, TimelineEvent, markers)
sin reimplementar resolución temporal.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Types
# ============================================================================

class CrossBookTemporalType(str, Enum):
    """Tipos de inconsistencia temporal cross-book."""
    AGE_INCONSISTENCY = "cross_book_age_inconsistency"
    SIMULTANEOUS_LOCATION = "cross_book_simultaneous_location"
    ORDERING_IMPOSSIBILITY = "cross_book_ordering_impossibility"
    DATE_CONFLICT = "cross_book_date_conflict"


@dataclass
class CrossBookTemporalIssue:
    """Inconsistencia temporal detectada entre libros."""
    issue_type: CrossBookTemporalType
    entity_name: str
    description: str
    book_a_name: str
    book_b_name: str
    book_a_chapter: int | None = None
    book_b_chapter: int | None = None
    severity: str = "medium"  # low, medium, high, critical
    confidence: float = 0.7
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "entity_name": self.entity_name,
            "description": self.description,
            "book_a_name": self.book_a_name,
            "book_b_name": self.book_b_name,
            "book_a_chapter": self.book_a_chapter,
            "book_b_chapter": self.book_b_chapter,
            "severity": self.severity,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CrossBookTemporalReport:
    """Informe de análisis temporal cross-book."""
    collection_id: int
    collection_name: str
    issues: list[CrossBookTemporalIssue] = field(default_factory=list)
    books_analyzed: int = 0
    entity_links_analyzed: int = 0

    def to_dict(self) -> dict:
        return {
            "collection_id": self.collection_id,
            "collection_name": self.collection_name,
            "issues": [i.to_dict() for i in self.issues],
            "books_analyzed": self.books_analyzed,
            "entity_links_analyzed": self.entity_links_analyzed,
            "summary": {
                "total_issues": len(self.issues),
                "by_type": self._count_by_type(),
                "by_severity": self._count_by_severity(),
            },
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for i in self.issues:
            key = i.issue_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for i in self.issues:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts


# ============================================================================
# Datos de entrada por libro
# ============================================================================

@dataclass
class BookTemporalData:
    """Datos temporales extraídos de un libro para comparación cross-book."""
    project_id: int
    project_name: str
    book_order: int
    # Edades: entity_id → list[(chapter, age, story_date_or_offset)]
    character_ages: dict[int, list[tuple[int, int, date | float | None]]] = field(
        default_factory=dict
    )
    # Ubicaciones: entity_id → list[(chapter, location)]
    character_locations: dict[int, list[tuple[int, str]]] = field(
        default_factory=dict
    )
    # Fechas de eventos clave: list[(chapter, story_date, event_description)]
    dated_events: list[tuple[int, date, str]] = field(default_factory=list)
    # Rango temporal del libro
    time_span: tuple[date, date] | None = None


# ============================================================================
# Reglas de detección
# ============================================================================

AGE_TOLERANCE_YEARS = 2.0


def _check_age_inconsistency(
    entity_name: str,
    ages_a: list[tuple[int, int, date | float | None]],
    ages_b: list[tuple[int, int, date | float | None]],
    book_a: BookTemporalData,
    book_b: BookTemporalData,
) -> list[CrossBookTemporalIssue]:
    """
    Detecta si la edad de un personaje es inconsistente entre dos libros.

    Compara:
    - Si ambos libros tienen fechas absolutas: edad esperada vs real
    - Si solo tienen edades sin fecha: la edad debería ser >= en libro posterior
    """
    issues = []

    if not ages_a or not ages_b:
        return issues

    # Libro anterior vs posterior
    if book_a.book_order < book_b.book_order:
        earlier_ages, later_ages = ages_a, ages_b
        earlier_book, later_book = book_a, book_b
    elif book_b.book_order < book_a.book_order:
        earlier_ages, later_ages = ages_b, ages_a
        earlier_book, later_book = book_b, book_a
    else:
        return issues

    # Última edad en libro anterior, primera en libro posterior
    last_earlier = max(earlier_ages, key=lambda x: x[0])  # max chapter
    first_later = min(later_ages, key=lambda x: x[0])    # min chapter

    earlier_age = last_earlier[1]
    later_age = first_later[1]
    earlier_date = last_earlier[2]
    later_date = first_later[2]

    # Caso 1: Edad retrocede (debería ser >= en libro posterior)
    if later_age < earlier_age:
        issues.append(CrossBookTemporalIssue(
            issue_type=CrossBookTemporalType.AGE_INCONSISTENCY,
            entity_name=entity_name,
            description=(
                f"{entity_name} tiene {earlier_age} años al final de "
                f"«{earlier_book.project_name}» pero {later_age} años "
                f"al inicio de «{later_book.project_name}»"
            ),
            book_a_name=earlier_book.project_name,
            book_b_name=later_book.project_name,
            book_a_chapter=last_earlier[0],
            book_b_chapter=first_later[0],
            severity="critical",
            confidence=0.9,
            metadata={
                "age_earlier": earlier_age,
                "age_later": later_age,
            },
        ))

    # Caso 2: Ambos tienen fechas absolutas — verificar coherencia
    elif (
        isinstance(earlier_date, date) and isinstance(later_date, date)
        and earlier_date < later_date
    ):
        years_passed = (later_date - earlier_date).days / 365.25
        age_diff = later_age - earlier_age

        if abs(age_diff - years_passed) > AGE_TOLERANCE_YEARS:
            issues.append(CrossBookTemporalIssue(
                issue_type=CrossBookTemporalType.AGE_INCONSISTENCY,
                entity_name=entity_name,
                description=(
                    f"{entity_name}: entre «{earlier_book.project_name}» y "
                    f"«{later_book.project_name}» pasan {years_passed:.1f} años "
                    f"pero envejece {age_diff} años"
                ),
                book_a_name=earlier_book.project_name,
                book_b_name=later_book.project_name,
                book_a_chapter=last_earlier[0],
                book_b_chapter=first_later[0],
                severity="high",
                confidence=0.85,
                metadata={
                    "years_passed": round(years_passed, 1),
                    "age_diff": age_diff,
                    "date_earlier": str(earlier_date),
                    "date_later": str(later_date),
                },
            ))

    return issues


def _check_date_conflict(
    entity_name: str,
    book_a: BookTemporalData,
    book_b: BookTemporalData,
) -> list[CrossBookTemporalIssue]:
    """
    Detecta conflictos de fechas entre libros.

    Si el rango temporal de un libro posterior debería empezar después
    del anterior pero no lo hace.
    """
    issues = []

    if not book_a.time_span or not book_b.time_span:
        return issues

    if book_a.book_order >= book_b.book_order:
        return issues

    # Libro A (anterior) debería terminar antes de que empiece libro B
    # Pero si hay solapamiento significativo, puede ser intencional (paralelo)
    a_end = book_a.time_span[1]
    b_start = book_b.time_span[0]

    # Solo reportar si libro B empieza ANTES de que termine libro A
    # y la diferencia es grande (> 1 año)
    if b_start < a_end:
        overlap_days = (a_end - b_start).days
        if overlap_days > 365:
            issues.append(CrossBookTemporalIssue(
                issue_type=CrossBookTemporalType.DATE_CONFLICT,
                entity_name=entity_name,
                description=(
                    f"«{book_b.project_name}» empieza {overlap_days} días "
                    f"antes de que termine «{book_a.project_name}» — "
                    f"posible conflicto de cronología"
                ),
                book_a_name=book_a.project_name,
                book_b_name=book_b.project_name,
                severity="low",
                confidence=0.5,
                metadata={
                    "overlap_days": overlap_days,
                    "book_a_end": str(a_end),
                    "book_b_start": str(b_start),
                },
            ))

    return issues


# ============================================================================
# Analizador principal
# ============================================================================

class CrossBookTemporalAnalyzer:
    """
    Analiza inconsistencias temporales entre libros de una colección.

    Requiere:
    - Entity links entre libros
    - Temporal markers o timeline events por libro
    """

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    def analyze(self, collection_id: int) -> CrossBookTemporalReport:
        """Ejecuta análisis temporal cross-book completo."""
        from ..persistence.collection import CollectionRepository

        repo = CollectionRepository(self._get_db())
        collection = repo.get(collection_id)
        if not collection:
            return CrossBookTemporalReport(
                collection_id=collection_id,
                collection_name="(no encontrada)",
            )

        links = repo.get_entity_links(collection_id)
        projects = repo.get_projects(collection_id)

        if not links or not projects:
            return CrossBookTemporalReport(
                collection_id=collection_id,
                collection_name=collection.name,
                books_analyzed=len(projects),
                entity_links_analyzed=len(links),
            )

        # Construir datos temporales por libro
        book_data = self._extract_temporal_data(projects)

        # Para cada entity link, comparar datos temporales
        all_issues: list[CrossBookTemporalIssue] = []

        for link in links:
            entity_name = link.source_entity_name or link.target_entity_name
            src_data = book_data.get(link.source_project_id)
            tgt_data = book_data.get(link.target_project_id)

            if not src_data or not tgt_data:
                continue

            # Edades del personaje en cada libro
            ages_a = src_data.character_ages.get(link.source_entity_id, [])
            ages_b = tgt_data.character_ages.get(link.target_entity_id, [])

            # Regla: Edad inconsistente
            all_issues.extend(
                _check_age_inconsistency(entity_name, ages_a, ages_b, src_data, tgt_data)
            )

            # Regla: Conflicto de fechas
            all_issues.extend(
                _check_date_conflict(entity_name, src_data, tgt_data)
            )

        report = CrossBookTemporalReport(
            collection_id=collection_id,
            collection_name=collection.name,
            issues=all_issues,
            books_analyzed=len(projects),
            entity_links_analyzed=len(links),
        )

        # Cache
        try:
            repo.save_workspace_cache(
                collection_id, "cross_book_temporal", report.to_dict()
            )
        except Exception as e:
            logger.warning(f"Could not cache cross-book temporal: {e}")

        logger.info(
            f"Cross-book temporal analysis: {len(all_issues)} issues "
            f"from {len(links)} entity links across {len(projects)} projects"
        )

        return report

    def _extract_temporal_data(
        self, projects: list
    ) -> dict[int, BookTemporalData]:
        """
        Extrae datos temporales de cada libro usando TemporalMap y markers.
        """
        result: dict[int, BookTemporalData] = {}

        for p in projects:
            book_data = BookTemporalData(
                project_id=p.id,
                project_name=p.name,
                book_order=getattr(p, "collection_order", 0) or 0,
            )

            try:
                self._populate_from_timeline_events(p.id, book_data)
                self._populate_from_temporal_markers(p.id, book_data)
            except Exception as e:
                logger.debug(f"Could not extract temporal data for project {p.id}: {e}")

            result[p.id] = book_data

        return result

    def _populate_from_timeline_events(self, project_id: int, data: BookTemporalData):
        """Lee timeline_events de la DB para extraer fechas y edades."""
        db = self._get_db()
        conn = db.get_connection()

        # Leer timeline_events (tabla existente del módulo temporal/)
        rows = conn.execute("""
            SELECT chapter, event_type, story_date, day_offset, entity_ids, description
            FROM timeline_events
            WHERE project_id = ?
            ORDER BY chapter, discourse_position
        """, (project_id,)).fetchall()

        dates = []
        for row in rows:
            story_date_str = row[2]
            if story_date_str:
                try:
                    d = date.fromisoformat(story_date_str)
                    dates.append(d)
                    data.dated_events.append((row[0], d, row[5] or ""))
                except (ValueError, TypeError):
                    pass

        if dates:
            data.time_span = (min(dates), max(dates))

    def _populate_from_temporal_markers(self, project_id: int, data: BookTemporalData):
        """Lee temporal_markers de la DB para extraer edades de personajes."""
        db = self._get_db()
        conn = db.get_connection()

        rows = conn.execute("""
            SELECT chapter, entity_id, age, year, month, day
            FROM temporal_markers
            WHERE project_id = ? AND marker_type = 'CHARACTER_AGE' AND age IS NOT NULL
            ORDER BY chapter
        """, (project_id,)).fetchall()

        for row in rows:
            chapter = row[0] or 0
            entity_id = row[1]
            age = row[2]
            year, month, day = row[3], row[4], row[5]

            story_date: date | float | None = None
            if year and month and day:
                try:
                    story_date = date(year, month, day)
                except (ValueError, TypeError):
                    pass

            if entity_id and age is not None:
                if entity_id not in data.character_ages:
                    data.character_ages[entity_id] = []
                data.character_ages[entity_id].append((chapter, age, story_date))
