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
    # S14: Revision Intelligence fields
    resolution_reason: str = ""  # "text_changed", "detector_improved", ""
    match_confidence: float = 0.0  # Confianza del matching (0-1)
    start_char: int | None = None
    end_char: int | None = None


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
                     "chapter": a.chapter, "confidence": a.confidence,
                     "start_char": a.start_char, "end_char": a.end_char}
                    for a in self.alerts_new
                ],
                "resolved": [
                    {"alert_type": a.alert_type, "category": a.category,
                     "severity": a.severity, "title": a.title,
                     "chapter": a.chapter, "confidence": a.confidence,
                     "resolution_reason": a.resolution_reason,
                     "match_confidence": a.match_confidence,
                     "start_char": a.start_char, "end_char": a.end_char}
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

            # === CONTENT DIFFING (S14) ===
            doc_diff = None
            if fp_changed:
                try:
                    old_chapter_texts = snapshot_repo.get_snapshot_chapter_texts(
                        snapshot.snapshot_id
                    )
                    if old_chapter_texts:
                        current_chapter_texts = {}
                        ch_rows = conn.execute(
                            """SELECT chapter_number, content
                               FROM chapters WHERE project_id = ?""",
                            (project_id,),
                        ).fetchall()
                        for ch_row in ch_rows:
                            current_chapter_texts[ch_row[0]] = ch_row[1] or ""

                        from .content_diff import compute_chapter_diffs
                        doc_diff = compute_chapter_diffs(
                            old_chapter_texts, current_chapter_texts
                        )
                        logger.info(
                            f"Content diff computed: {len(doc_diff.chapter_diffs)} chapters, "
                            f"added={doc_diff.chapters_added}, removed={doc_diff.chapters_removed}"
                        )
                except Exception as e:
                    logger.warning(f"Content diff failed (non-fatal): {e}")

            # === TRACK CHANGES (S14 Phase 4) ===
            docx_del_ranges: list[tuple[int, int]] = []
            try:
                doc_path_row = conn.execute(
                    "SELECT document_path FROM projects WHERE id = ?",
                    (project_id,),
                ).fetchone()
                if doc_path_row and doc_path_row[0]:
                    from pathlib import Path as _Path
                    doc_path = _Path(doc_path_row[0])
                    if doc_path.suffix.lower() == ".docx" and doc_path.exists():
                        from ..parsers.docx_revisions import (
                            get_deletion_char_ranges,
                            parse_docx_revisions,
                        )
                        revisions = parse_docx_revisions(doc_path)
                        if revisions.has_revisions:
                            docx_del_ranges = get_deletion_char_ranges(revisions)
                            logger.info(
                                f"Track changes: {revisions.total_changes} revisions, "
                                f"{len(docx_del_ranges)} deletion ranges"
                            )
            except Exception as e:
                logger.debug(f"Track changes parsing skipped: {e}")

            # === ALERTAS ===
            old_alerts = snapshot_repo.get_snapshot_alerts(snapshot.snapshot_id)
            current_alerts = conn.execute(
                """SELECT alert_type, category, severity, title, description,
                          chapter, content_hash, confidence, entity_ids,
                          start_char, end_char, id
                   FROM alerts WHERE project_id = ?""",
                (project_id,),
            ).fetchall()

            alerts_new, alerts_resolved, alerts_unchanged = self._diff_alerts(
                old_alerts, current_alerts, conn,
                doc_diff=doc_diff,
                docx_del_ranges=docx_del_ranges,
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

    def compare_and_link(self, project_id: int) -> ComparisonReport | None:
        """
        Compare + write alert links to DB (S14, BK-25).

        Calls compare() and then writes previous_snapshot_alert_id,
        match_confidence, and resolution_reason to matching current alerts.
        """
        from ..persistence.snapshot import SnapshotRepository

        snapshot_repo = SnapshotRepository(self._get_db())
        snapshot = snapshot_repo.get_latest_snapshot(project_id)
        if not snapshot:
            return None

        report = self.compare(project_id)
        if report is None:
            return None

        # Write links: match current alerts to their snapshot predecessors
        try:
            self._write_alert_links(project_id, snapshot.snapshot_id)
        except Exception as e:
            logger.warning(f"Alert linking failed (non-fatal): {e}")

        return report

    def _write_alert_links(self, project_id: int, snapshot_id: int) -> int:
        """
        Write alert links after comparison (S14-06).

        For each current alert that matches a snapshot alert (by content_hash
        or fuzzy match), writes previous_snapshot_alert_id + match_confidence.
        For resolved alerts, writes resolution_reason.

        Returns number of links written.
        """
        from ..persistence.snapshot import SnapshotRepository

        db = self._get_db()
        snapshot_repo = SnapshotRepository(db)
        old_alerts = snapshot_repo.get_snapshot_alerts(snapshot_id)
        if not old_alerts:
            return 0

        links_written = 0

        with db.connection() as conn:
            current_rows = conn.execute(
                """SELECT id, content_hash, alert_type, chapter, title, entity_ids
                   FROM alerts WHERE project_id = ?""",
                (project_id,),
            ).fetchall()

            # Build lookup from old alerts
            old_by_hash: dict[str, int] = {}
            for oa in old_alerts:
                if oa.content_hash and oa.snapshot_alert_id:
                    old_by_hash[oa.content_hash] = oa.snapshot_alert_id

            old_by_key: dict[tuple, int] = {}
            for oa in old_alerts:
                if oa.snapshot_alert_id:
                    key = (oa.alert_type, oa.chapter, oa.title)
                    old_by_key[key] = oa.snapshot_alert_id

            for row in current_rows:
                alert_id = row[0]
                content_hash = row[1] or ""
                alert_type = row[2]
                chapter = row[3]
                title = row[4]

                # Pass 1: exact hash match
                snap_alert_id = old_by_hash.get(content_hash)
                confidence = 1.0

                # Pass 2: fuzzy key match
                if snap_alert_id is None:
                    key = (alert_type, chapter, title)
                    snap_alert_id = old_by_key.get(key)
                    confidence = 0.7

                if snap_alert_id is not None:
                    conn.execute(
                        """UPDATE alerts
                           SET previous_snapshot_alert_id = ?,
                               match_confidence = ?
                           WHERE id = ?""",
                        (snap_alert_id, confidence, alert_id),
                    )
                    links_written += 1

            conn.commit()

        logger.info(f"Alert linking: {links_written} links written for project {project_id}")
        return links_written

    def _diff_alerts(
        self, old_alerts, current_alerts_rows, conn,
        doc_diff=None, docx_del_ranges: list[tuple[int, int]] | None = None,
    ) -> tuple:
        """
        Four-pass alert matching:
        1. Exact content_hash match
        2. Fuzzy match on (alert_type, chapter, entity_names)
        3. Proximity matching with content diff (S14)
        4. Track changes: w:del ranges from .docx (S14 Phase 4)
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
                "start_char": row[9] if len(row) > 9 else None,
                "end_char": row[10] if len(row) > 10 else None,
                "alert_id": row[11] if len(row) > 11 else None,
            })

        # Track matched indices + match pairs for linking
        old_matched = set()
        new_matched = set()
        # S14: Map new_index → (old_index, confidence) for alert linking
        match_pairs: dict[int, tuple[int, float]] = {}

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
                        match_pairs[j] = (i, 1.0)
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
                        match_pairs[j] = (i, 0.8)
                        break
                    # Fallback: title similarity
                    if oa.title and ca["title"] and oa.title == ca["title"]:
                        old_matched.add(i)
                        new_matched.add(j)
                        match_pairs[j] = (i, 0.7)
                        break

        # Pass 3: Proximity matching with content diff (S14)
        # For unmatched old alerts, check if their position falls in a removed/modified area
        resolution_reasons: dict[int, str] = {}  # old_alert_index → reason
        match_confidences: dict[int, float] = {}  # old_alert_index → confidence

        if doc_diff is not None:
            from .content_diff import is_position_in_modified_area, is_position_in_removed_range

            for i, oa in enumerate(old_alerts):
                if i in old_matched:
                    # Already matched — set confidence from pass (1=exact, 2=fuzzy)
                    match_confidences[i] = 1.0  # Known match
                    continue
                if oa.chapter is None or oa.start_char is None or oa.end_char is None:
                    continue

                if is_position_in_removed_range(
                    oa.chapter, oa.start_char, oa.end_char, doc_diff
                ):
                    resolution_reasons[i] = "text_changed"
                    match_confidences[i] = 0.9
                elif is_position_in_modified_area(
                    oa.chapter, oa.start_char, oa.end_char, doc_diff
                ):
                    resolution_reasons[i] = "text_changed"
                    match_confidences[i] = 0.7

        # Pass 4: Track changes from .docx (S14 Phase 4)
        # If the document has w:del revisions, check if old alert position
        # falls within a deleted range → high confidence "text_changed"
        if docx_del_ranges:
            for i, oa in enumerate(old_alerts):
                if i in old_matched or i in resolution_reasons:
                    continue
                if oa.start_char is None or oa.end_char is None:
                    continue
                for del_start, del_end in docx_del_ranges:
                    if oa.start_char < del_end and oa.end_char > del_start:
                        resolution_reasons[i] = "text_changed"
                        match_confidences[i] = 0.95  # High: explicit track change
                        break

        # For unmatched old alerts without position info or not near changes
        for i in range(len(old_alerts)):
            if i not in old_matched and i not in resolution_reasons:
                resolution_reasons[i] = "detector_improved"
                match_confidences[i] = 0.5

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
                start_char=current[j].get("start_char"),
                end_char=current[j].get("end_char"),
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
                resolution_reason=resolution_reasons.get(i, ""),
                match_confidence=match_confidences.get(i, 0.0),
                start_char=old_alerts[i].start_char,
                end_char=old_alerts[i].end_char,
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
