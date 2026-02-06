"""
Servicio de comparación antes/después de análisis (BK-05).

Compara el estado de un proyecto entre dos análisis sucesivos
usando snapshots capturados antes de cada re-análisis.
"""

import json
import logging
from dataclasses import dataclass, field

from ..analysis.entity_matcher import exact_match, fuzzy_match

logger = logging.getLogger(__name__)


@dataclass
class AlertDiff:
    """Resumen de una alerta en el diff."""

    alert_type: str
    category: str
    severity: str
    title: str
    chapter: int | None = None
    confidence: float = 0.8
    content_hash: str = ""


@dataclass
class EntityDiff:
    """Resumen de una entidad en el diff."""

    canonical_name: str
    entity_type: str
    importance: str = "secondary"
    mention_count: int = 0


@dataclass
class ComparisonReport:
    """Resultado de comparar dos estados de análisis."""

    project_id: int
    snapshot_id: int
    snapshot_created_at: str
    document_fingerprint_changed: bool

    # Alertas
    alerts_new: list[AlertDiff] = field(default_factory=list)
    alerts_resolved: list[AlertDiff] = field(default_factory=list)
    alerts_unchanged: int = 0

    # Entidades
    entities_added: list[EntityDiff] = field(default_factory=list)
    entities_removed: list[EntityDiff] = field(default_factory=list)
    entities_unchanged: int = 0

    # Resumen
    total_alerts_before: int = 0
    total_alerts_after: int = 0
    total_entities_before: int = 0
    total_entities_after: int = 0

    def to_dict(self) -> dict:
        """Serializa a diccionario para API response."""
        return {
            "project_id": self.project_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_created_at": self.snapshot_created_at,
            "document_fingerprint_changed": self.document_fingerprint_changed,
            "alerts": {
                "new": [
                    {"alert_type": a.alert_type, "category": a.category,
                     "severity": a.severity, "title": a.title,
                     "chapter": a.chapter, "confidence": a.confidence}
                    for a in self.alerts_new
                ],
                "resolved": [
                    {"alert_type": a.alert_type, "category": a.category,
                     "severity": a.severity, "title": a.title,
                     "chapter": a.chapter, "confidence": a.confidence}
                    for a in self.alerts_resolved
                ],
                "unchanged": self.alerts_unchanged,
            },
            "entities": {
                "added": [
                    {"canonical_name": e.canonical_name, "entity_type": e.entity_type,
                     "importance": e.importance, "mention_count": e.mention_count}
                    for e in self.entities_added
                ],
                "removed": [
                    {"canonical_name": e.canonical_name, "entity_type": e.entity_type,
                     "importance": e.importance, "mention_count": e.mention_count}
                    for e in self.entities_removed
                ],
                "unchanged": self.entities_unchanged,
            },
            "summary": {
                "total_alerts_before": self.total_alerts_before,
                "total_alerts_after": self.total_alerts_after,
                "total_entities_before": self.total_entities_before,
                "total_entities_after": self.total_entities_after,
            },
        }


class ComparisonService:
    """Compara el estado actual de un proyecto contra un snapshot previo."""

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    def compare(self, project_id: int) -> ComparisonReport | None:
        """
        Compara el estado actual contra el último snapshot.

        Usa two-pass matching para alertas:
        1. Match exacto por content_hash
        2. Match fuzzy por (alert_type, chapter, título/entity_names)

        Retorna None si no hay snapshot previo.
        """
        from ..persistence.snapshot import SnapshotRepository

        snapshot_repo = SnapshotRepository(self._get_db())
        snapshot = snapshot_repo.get_latest_snapshot(project_id)
        if not snapshot:
            return None

        # Verificar que el análisis actual está completado
        db = self._get_db()
        with db.connection() as conn:
            status = conn.execute(
                "SELECT analysis_status FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            if status and status[0] != "completed":
                logger.warning(
                    f"Skipping comparison: project {project_id} status={status[0]}"
                )
                return None

            # Obtener fingerprint actual
            current_fp = conn.execute(
                "SELECT document_fingerprint FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            fp_changed = (
                current_fp[0] != snapshot.document_fingerprint
                if current_fp and snapshot.document_fingerprint
                else False
            )

            # === ALERTAS ===
            old_alerts = snapshot_repo.get_snapshot_alerts(snapshot.snapshot_id)
            current_alerts = conn.execute(
                """SELECT alert_type, category, severity, title, description,
                          chapter, content_hash, confidence, entity_ids
                   FROM alerts WHERE project_id = ?""",
                (project_id,),
            ).fetchall()

            alerts_new, alerts_resolved, alerts_unchanged = self._diff_alerts(
                old_alerts, current_alerts, conn
            )

            # === ENTIDADES ===
            old_entities = snapshot_repo.get_snapshot_entities(snapshot.snapshot_id)
            current_entities = conn.execute(
                """SELECT canonical_name, entity_type, importance, mention_count
                   FROM entities WHERE project_id = ? AND is_active = 1""",
                (project_id,),
            ).fetchall()

            entities_added, entities_removed, entities_unchanged = self._diff_entities(
                old_entities, current_entities
            )

        return ComparisonReport(
            project_id=project_id,
            snapshot_id=snapshot.snapshot_id,
            snapshot_created_at=snapshot.created_at,
            document_fingerprint_changed=fp_changed,
            alerts_new=alerts_new,
            alerts_resolved=alerts_resolved,
            alerts_unchanged=alerts_unchanged,
            entities_added=entities_added,
            entities_removed=entities_removed,
            entities_unchanged=entities_unchanged,
            total_alerts_before=len(old_alerts),
            total_alerts_after=len(current_alerts),
            total_entities_before=len(old_entities),
            total_entities_after=len(current_entities),
        )

    def _diff_alerts(self, old_alerts, current_alerts_rows, conn) -> tuple:
        """
        Two-pass alert matching:
        1. Exact content_hash match
        2. Fuzzy match on (alert_type, chapter, entity_names)
        """
        # Build current alert dicts
        current = []
        for row in current_alerts_rows:
            entity_names = []
            try:
                eids = json.loads(row[8] or "[]")
                if eids:
                    placeholders = ",".join("?" * len(eids))
                    names = conn.execute(
                        f"SELECT canonical_name FROM entities WHERE id IN ({placeholders})",
                        eids,
                    ).fetchall()
                    entity_names = [n[0] for n in names]
            except (json.JSONDecodeError, TypeError):
                pass

            current.append({
                "alert_type": row[0], "category": row[1], "severity": row[2],
                "title": row[3], "description": row[4] or "",
                "chapter": row[5], "content_hash": row[6] or "",
                "confidence": row[7] or 0.8,
                "entity_names": entity_names,
            })

        # Track matched indices
        old_matched = set()
        new_matched = set()

        # Pass 1: Exact content_hash
        old_by_hash = {}
        for i, alert in enumerate(old_alerts):
            if alert.content_hash:
                old_by_hash.setdefault(alert.content_hash, []).append(i)

        for j, ca in enumerate(current):
            if ca["content_hash"] and ca["content_hash"] in old_by_hash:
                candidates = old_by_hash[ca["content_hash"]]
                for i in candidates:
                    if i not in old_matched:
                        old_matched.add(i)
                        new_matched.add(j)
                        break

        # Pass 2: Fuzzy match for remaining
        for j, ca in enumerate(current):
            if j in new_matched:
                continue
            for i, oa in enumerate(old_alerts):
                if i in old_matched:
                    continue
                if ca["alert_type"] == oa.alert_type and ca["chapter"] == oa.chapter:
                    # Check entity name overlap or title similarity
                    old_names = set()
                    try:
                        old_names = set(json.loads(oa.related_entity_names))
                    except (json.JSONDecodeError, TypeError):
                        pass
                    new_names = set(ca["entity_names"])

                    if old_names and new_names and old_names & new_names:
                        old_matched.add(i)
                        new_matched.add(j)
                        break
                    # Fallback: title similarity
                    if oa.title and ca["title"] and oa.title == ca["title"]:
                        old_matched.add(i)
                        new_matched.add(j)
                        break

        # Classify
        alerts_new = [
            AlertDiff(
                alert_type=current[j]["alert_type"],
                category=current[j]["category"],
                severity=current[j]["severity"],
                title=current[j]["title"],
                chapter=current[j]["chapter"],
                confidence=current[j]["confidence"],
                content_hash=current[j]["content_hash"],
            )
            for j in range(len(current)) if j not in new_matched
        ]

        alerts_resolved = [
            AlertDiff(
                alert_type=old_alerts[i].alert_type,
                category=old_alerts[i].category,
                severity=old_alerts[i].severity,
                title=old_alerts[i].title,
                chapter=old_alerts[i].chapter,
                confidence=old_alerts[i].confidence,
                content_hash=old_alerts[i].content_hash,
            )
            for i in range(len(old_alerts)) if i not in old_matched
        ]

        return alerts_new, alerts_resolved, len(old_matched)

    def _diff_entities(self, old_entities, current_rows) -> tuple:
        """Diff entidades usando exact + fuzzy matching."""
        current = [
            {"canonical_name": r[0], "entity_type": r[1],
             "importance": r[2] or "secondary", "mention_count": r[3] or 0}
            for r in current_rows
        ]

        old_matched = set()
        new_matched = set()

        # Pass 1: Exact name + type
        for j, ce in enumerate(current):
            for i, oe in enumerate(old_entities):
                if i in old_matched:
                    continue
                if (
                    exact_match(ce["canonical_name"], oe.canonical_name)
                    and ce["entity_type"] == oe.entity_type
                ):
                    old_matched.add(i)
                    new_matched.add(j)
                    break

        # Pass 2: Fuzzy name match (same type)
        for j, ce in enumerate(current):
            if j in new_matched:
                continue
            for i, oe in enumerate(old_entities):
                if i in old_matched:
                    continue
                if ce["entity_type"] != oe.entity_type:
                    continue
                old_aliases = []
                try:
                    old_aliases = json.loads(oe.aliases)
                except (json.JSONDecodeError, TypeError):
                    pass
                sim = fuzzy_match(
                    ce["canonical_name"], oe.canonical_name,
                    aliases2=old_aliases, threshold=0.7,
                )
                if sim >= 0.7:
                    old_matched.add(i)
                    new_matched.add(j)
                    break

        entities_added = [
            EntityDiff(**current[j])
            for j in range(len(current)) if j not in new_matched
        ]
        entities_removed = [
            EntityDiff(
                canonical_name=old_entities[i].canonical_name,
                entity_type=old_entities[i].entity_type,
                importance=old_entities[i].importance,
                mention_count=old_entities[i].mention_count,
            )
            for i in range(len(old_entities)) if i not in old_matched
        ]

        return entities_added, entities_removed, len(old_matched)
