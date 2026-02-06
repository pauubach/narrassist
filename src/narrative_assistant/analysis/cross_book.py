"""
Análisis cross-book para colecciones / sagas (BK-07).

Compara atributos de entidades enlazadas entre distintos libros
para detectar inconsistencias cross-book.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CrossBookInconsistency:
    """Inconsistencia detectada entre libros de una saga."""

    entity_name: str
    attribute_type: str
    attribute_key: str
    value_book_a: str
    value_book_b: str
    book_a_name: str
    book_b_name: str
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "entity_name": self.entity_name,
            "attribute_type": self.attribute_type,
            "attribute_key": self.attribute_key,
            "value_book_a": self.value_book_a,
            "value_book_b": self.value_book_b,
            "book_a_name": self.book_a_name,
            "book_b_name": self.book_b_name,
            "confidence": self.confidence,
        }


@dataclass
class CrossBookReport:
    """Informe de análisis cross-book."""

    collection_id: int
    collection_name: str
    inconsistencies: list[CrossBookInconsistency] = field(default_factory=list)
    entity_links_analyzed: int = 0
    projects_analyzed: int = 0

    def to_dict(self) -> dict:
        return {
            "collection_id": self.collection_id,
            "collection_name": self.collection_name,
            "inconsistencies": [i.to_dict() for i in self.inconsistencies],
            "entity_links_analyzed": self.entity_links_analyzed,
            "projects_analyzed": self.projects_analyzed,
            "summary": {
                "total_inconsistencies": len(self.inconsistencies),
                "by_type": self._count_by_type(),
            },
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for inc in self.inconsistencies:
            key = inc.attribute_type
            counts[key] = counts.get(key, 0) + 1
        return counts


class CrossBookAnalyzer:
    """Analiza inconsistencias entre libros de una colección."""

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    def analyze(self, collection_id: int) -> CrossBookReport:
        """
        Analiza todos los entity links de una colección.

        Para cada par de entidades enlazadas, compara sus atributos
        buscando inconsistencias (mismo attribute_key, distinto value).
        """
        from ..persistence.collection import CollectionRepository

        repo = CollectionRepository(self._get_db())
        collection = repo.get(collection_id)
        if not collection:
            return CrossBookReport(
                collection_id=collection_id,
                collection_name="(no encontrada)",
            )

        links = repo.get_entity_links(collection_id)
        projects = repo.get_projects(collection_id)

        inconsistencies = []
        db = self._get_db()

        for link in links:
            link_inconsistencies = self._compare_entity_attributes(
                db, link
            )
            inconsistencies.extend(link_inconsistencies)

        report = CrossBookReport(
            collection_id=collection_id,
            collection_name=collection.name,
            inconsistencies=inconsistencies,
            entity_links_analyzed=len(links),
            projects_analyzed=len(projects),
        )

        # Cache en workspace auxiliar
        try:
            repo.save_workspace_cache(
                collection_id, "cross_book_analysis", report.to_dict()
            )
        except Exception as e:
            logger.warning(f"Could not cache cross-book analysis: {e}")

        return report

    def _compare_entity_attributes(self, db, link) -> list[CrossBookInconsistency]:
        """Compara atributos de dos entidades enlazadas."""
        inconsistencies = []

        with db.connection() as conn:
            # Obtener atributos de ambas entidades
            attrs_a = conn.execute(
                """SELECT attribute_type, attribute_key, attribute_value, confidence
                   FROM entity_attributes WHERE entity_id = ?""",
                (link.source_entity_id,),
            ).fetchall()

            attrs_b = conn.execute(
                """SELECT attribute_type, attribute_key, attribute_value, confidence
                   FROM entity_attributes WHERE entity_id = ?""",
                (link.target_entity_id,),
            ).fetchall()

        if not attrs_a or not attrs_b:
            return []

        # Indexar por (type, key)
        map_a: dict[tuple[str, str], list[tuple[str, float]]] = {}
        for at, ak, av, conf in attrs_a:
            map_a.setdefault((at, ak), []).append((av, conf or 0.8))

        map_b: dict[tuple[str, str], list[tuple[str, float]]] = {}
        for at, ak, av, conf in attrs_b:
            map_b.setdefault((at, ak), []).append((av, conf or 0.8))

        # Comparar atributos compartidos
        shared_keys = set(map_a.keys()) & set(map_b.keys())
        for attr_type, attr_key in shared_keys:
            values_a = {v.lower().strip() for v, _ in map_a[(attr_type, attr_key)]}
            values_b = {v.lower().strip() for v, _ in map_b[(attr_type, attr_key)]}

            # Si los valores difieren, es una posible inconsistencia
            if values_a != values_b:
                # Usar el valor de mayor confianza de cada lado
                best_a = max(map_a[(attr_type, attr_key)], key=lambda x: x[1])
                best_b = max(map_b[(attr_type, attr_key)], key=lambda x: x[1])

                inconsistencies.append(CrossBookInconsistency(
                    entity_name=link.source_entity_name,
                    attribute_type=attr_type,
                    attribute_key=attr_key,
                    value_book_a=best_a[0],
                    value_book_b=best_b[0],
                    book_a_name=link.source_project_name,
                    book_b_name=link.target_project_name,
                    confidence=min(best_a[1], best_b[1]),
                ))

        return inconsistencies
