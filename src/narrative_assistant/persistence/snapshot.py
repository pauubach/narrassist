"""
Repositorio de snapshots de análisis (BK-05).

Captura el estado de alertas y entidades antes de re-analizar,
permitiendo comparar el estado antes/después.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_SNAPSHOTS_PER_PROJECT = 10


@dataclass
class SnapshotAlert:
    """Alerta capturada en un snapshot."""

    alert_type: str
    category: str
    severity: str
    title: str
    description: str = ""
    chapter: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    excerpt: str = ""
    content_hash: str = ""
    confidence: float = 0.8
    entity_ids: str = "[]"
    related_entity_names: str = "[]"
    extra_data: str = "{}"


@dataclass
class SnapshotEntity:
    """Entidad capturada en un snapshot."""

    original_entity_id: int
    entity_type: str
    canonical_name: str
    aliases: str = "[]"
    importance: str = "secondary"
    mention_count: int = 0


@dataclass
class SnapshotSummary:
    """Resumen de un snapshot."""

    snapshot_id: int
    project_id: int
    document_fingerprint: str | None
    alert_count: int
    entity_count: int
    status: str
    created_at: str


class SnapshotRepository:
    """Gestiona snapshots de análisis para comparación antes/después."""

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    def create_snapshot(self, project_id: int) -> int | None:
        """
        Captura snapshot del estado actual (alertas + entidades).

        Retorna snapshot_id o None si no hay datos que capturar.
        """
        db = self._get_db()
        try:
            with db.connection() as conn:
                # Obtener fingerprint actual
                row = conn.execute(
                    "SELECT document_fingerprint FROM projects WHERE id = ?",
                    (project_id,),
                ).fetchone()
                fingerprint = row[0] if row else None

                # Contar datos existentes
                alert_count = conn.execute(
                    "SELECT COUNT(*) FROM alerts WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0]

                entity_count = conn.execute(
                    "SELECT COUNT(*) FROM entities WHERE project_id = ? AND is_active = 1",
                    (project_id,),
                ).fetchone()[0]

                if alert_count == 0 and entity_count == 0:
                    logger.info(f"No data to snapshot for project {project_id}")
                    return None

                # Crear snapshot
                cursor = conn.execute(
                    """INSERT INTO analysis_snapshots
                       (project_id, document_fingerprint, alert_count, entity_count, status)
                       VALUES (?, ?, ?, ?, 'complete')""",
                    (project_id, fingerprint, alert_count, entity_count),
                )
                snapshot_id = cursor.lastrowid

                # Copiar alertas con entity names denormalizados
                alerts = conn.execute(
                    """SELECT alert_type, category, severity, title, description,
                              chapter, start_char, end_char, excerpt, content_hash,
                              confidence, entity_ids, extra_data
                       FROM alerts WHERE project_id = ?""",
                    (project_id,),
                ).fetchall()

                for alert in alerts:
                    entity_ids_json = alert[11] or "[]"
                    # Resolver nombres de entidades para matching estable
                    entity_names = []
                    try:
                        eids = json.loads(entity_ids_json)
                        if eids:
                            placeholders = ",".join("?" * len(eids))
                            names = conn.execute(
                                f"SELECT canonical_name FROM entities WHERE id IN ({placeholders})",
                                eids,
                            ).fetchall()
                            entity_names = [n[0] for n in names]
                    except (json.JSONDecodeError, TypeError):
                        pass

                    conn.execute(
                        """INSERT INTO snapshot_alerts
                           (snapshot_id, project_id, alert_type, category, severity,
                            title, description, chapter, start_char, end_char,
                            excerpt, content_hash, confidence, entity_ids,
                            related_entity_names, extra_data)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot_id, project_id,
                            alert[0], alert[1], alert[2], alert[3], alert[4],
                            alert[5], alert[6], alert[7], alert[8], alert[9],
                            alert[10], entity_ids_json,
                            json.dumps(entity_names, ensure_ascii=False),
                            alert[12] or "{}",
                        ),
                    )

                # Copiar entidades
                entities = conn.execute(
                    """SELECT id, entity_type, canonical_name, importance, mention_count
                       FROM entities WHERE project_id = ? AND is_active = 1""",
                    (project_id,),
                ).fetchall()

                for entity in entities:
                    # Obtener aliases
                    aliases_json = "[]"
                    try:
                        mentions = conn.execute(
                            """SELECT DISTINCT surface_form FROM entity_mentions
                               WHERE entity_id = ? AND surface_form != ?""",
                            (entity[0], entity[2]),
                        ).fetchall()
                        if mentions:
                            aliases_json = json.dumps(
                                [m[0] for m in mentions[:10]],
                                ensure_ascii=False,
                            )
                    except Exception:
                        pass

                    conn.execute(
                        """INSERT INTO snapshot_entities
                           (snapshot_id, project_id, original_entity_id, entity_type,
                            canonical_name, aliases, importance, mention_count)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot_id, project_id,
                            entity[0], entity[1], entity[2],
                            aliases_json, entity[3] or "secondary", entity[4] or 0,
                        ),
                    )

                conn.commit()
                logger.info(
                    f"Snapshot {snapshot_id} created for project {project_id}: "
                    f"{alert_count} alerts, {entity_count} entities"
                )
                return snapshot_id

        except Exception as e:
            logger.error(f"Error creating snapshot for project {project_id}: {e}")
            return None

    def get_latest_snapshot(self, project_id: int) -> SnapshotSummary | None:
        """Obtiene el snapshot más reciente de un proyecto."""
        db = self._get_db()
        with db.connection() as conn:
            row = conn.execute(
                """SELECT id, project_id, document_fingerprint, alert_count,
                          entity_count, status, created_at
                   FROM analysis_snapshots
                   WHERE project_id = ? AND status = 'complete'
                   ORDER BY created_at DESC LIMIT 1""",
                (project_id,),
            ).fetchone()
            if not row:
                return None
            return SnapshotSummary(
                snapshot_id=row[0],
                project_id=row[1],
                document_fingerprint=row[2],
                alert_count=row[3],
                entity_count=row[4],
                status=row[5],
                created_at=row[6],
            )

    def get_snapshot_alerts(self, snapshot_id: int) -> list[SnapshotAlert]:
        """Obtiene las alertas de un snapshot."""
        db = self._get_db()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT alert_type, category, severity, title, description,
                          chapter, start_char, end_char, excerpt, content_hash,
                          confidence, entity_ids, related_entity_names, extra_data
                   FROM snapshot_alerts WHERE snapshot_id = ?""",
                (snapshot_id,),
            ).fetchall()
            return [
                SnapshotAlert(
                    alert_type=r[0], category=r[1], severity=r[2],
                    title=r[3], description=r[4] or "", chapter=r[5],
                    start_char=r[6], end_char=r[7], excerpt=r[8] or "",
                    content_hash=r[9] or "", confidence=r[10] or 0.8,
                    entity_ids=r[11] or "[]",
                    related_entity_names=r[12] or "[]",
                    extra_data=r[13] or "{}",
                )
                for r in rows
            ]

    def get_snapshot_entities(self, snapshot_id: int) -> list[SnapshotEntity]:
        """Obtiene las entidades de un snapshot."""
        db = self._get_db()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT original_entity_id, entity_type, canonical_name,
                          aliases, importance, mention_count
                   FROM snapshot_entities WHERE snapshot_id = ?""",
                (snapshot_id,),
            ).fetchall()
            return [
                SnapshotEntity(
                    original_entity_id=r[0], entity_type=r[1],
                    canonical_name=r[2], aliases=r[3] or "[]",
                    importance=r[4] or "secondary", mention_count=r[5] or 0,
                )
                for r in rows
            ]

    def cleanup_old_snapshots(self, project_id: int, keep: int = MAX_SNAPSHOTS_PER_PROJECT) -> int:
        """
        Elimina snapshots antiguos, manteniendo los últimos `keep`.

        Retorna número de snapshots eliminados.
        """
        db = self._get_db()
        with db.connection() as conn:
            # Obtener IDs a mantener
            keep_ids = conn.execute(
                """SELECT id FROM analysis_snapshots
                   WHERE project_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (project_id, keep),
            ).fetchall()
            keep_set = {r[0] for r in keep_ids}

            if not keep_set:
                return 0

            # Obtener todos los IDs
            all_ids = conn.execute(
                "SELECT id FROM analysis_snapshots WHERE project_id = ?",
                (project_id,),
            ).fetchall()
            delete_ids = [r[0] for r in all_ids if r[0] not in keep_set]

            if not delete_ids:
                return 0

            # CASCADE borrará snapshot_alerts y snapshot_entities
            placeholders = ",".join("?" * len(delete_ids))
            conn.execute(
                f"DELETE FROM analysis_snapshots WHERE id IN ({placeholders})",
                delete_ids,
            )
            conn.commit()
            logger.info(
                f"Cleaned up {len(delete_ids)} old snapshots for project {project_id}"
            )
            return len(delete_ids)
