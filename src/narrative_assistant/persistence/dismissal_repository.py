"""
Repositorio de persistencia para dismissals y reglas de supresión.

Permite que los descartes de alertas sobrevivan entre re-análisis
usando content_hash en vez de alert_id.
"""

import fnmatch
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..core.errors import DatabaseError
from ..core.result import Result
from .database import get_database

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_repository_lock = threading.Lock()
_dismissal_repository: Optional["DismissalRepository"] = None


@dataclass
class Dismissal:
    """Registro de descarte de alerta."""

    id: int
    project_id: int
    content_hash: str
    scope: str  # instance, document, project
    reason: str
    alert_type: str
    source_module: str
    created_at: datetime


@dataclass
class SuppressionRule:
    """Regla de supresión definida por el usuario."""

    id: int
    project_id: int | None  # None = global
    rule_type: str  # alert_type, category, entity, source_module
    pattern: str
    entity_name: str | None
    reason: str
    is_active: bool
    created_at: datetime


class DismissalRepository:
    """
    Repositorio para almacenar y consultar dismissals y reglas de supresión.

    Funcionalidades:
    - Persistir descartes de alertas por content_hash
    - Verificar si una alerta está descartada
    - Descartar/re-abrir alertas en batch
    - Gestionar reglas de supresión del usuario
    - Generar estadísticas de descartes por detector
    """

    def __init__(self):
        """Inicializa el repositorio."""
        self.db = get_database()

    # =========================================================================
    # Dismissals CRUD
    # =========================================================================

    def is_dismissed(self, project_id: int, content_hash: str) -> bool:
        """
        Verifica si una alerta está descartada por su content_hash.

        Args:
            project_id: ID del proyecto
            content_hash: Hash del contenido de la alerta

        Returns:
            True si está descartada
        """
        try:
            with self.db.connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM alert_dismissals WHERE project_id = ? AND content_hash = ?",
                    (project_id, content_hash),
                ).fetchone()
                return row is not None
        except Exception as e:
            logger.warning(f"Error checking dismissal: {e}")
            return False

    def get_dismissed_hashes(self, project_id: int) -> set[str]:
        """
        Obtiene todos los content_hash descartados de un proyecto.

        Útil para filtrado batch: cargar todos los hashes una vez
        y filtrar in-memory en vez de N queries.

        Args:
            project_id: ID del proyecto

        Returns:
            Set de content_hash descartados
        """
        try:
            with self.db.connection() as conn:
                rows = conn.execute(
                    "SELECT content_hash FROM alert_dismissals WHERE project_id = ?",
                    (project_id,),
                ).fetchall()
                return {row[0] for row in rows}
        except Exception as e:
            logger.warning(f"Error getting dismissed hashes: {e}")
            return set()

    def dismiss(
        self,
        project_id: int,
        content_hash: str,
        alert_type: str = "",
        source_module: str = "",
        scope: str = "instance",
        reason: str = "",
    ) -> Result[None]:
        """
        Descarta una alerta por content_hash.

        Args:
            project_id: ID del proyecto
            content_hash: Hash del contenido de la alerta
            alert_type: Tipo de alerta (para estadísticas)
            source_module: Módulo fuente (para estadísticas)
            scope: Alcance del descarte (instance, document, project)
            reason: Razón del descarte

        Returns:
            Result indicando éxito o fallo
        """
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO alert_dismissals
                        (project_id, content_hash, scope, reason, alert_type, source_module)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, content_hash, scope, reason, alert_type, source_module),
                )
            logger.debug(f"Dismissed alert hash={content_hash[:8]}... project={project_id}")
            return Result.success(None)
        except Exception as e:
            error = DatabaseError(
                message="Error dismissing alert",
                context={"error": str(e), "content_hash": content_hash},
            )
            logger.error(f"Failed to dismiss alert: {e}")
            return Result.failure(error)

    def dismiss_batch(
        self,
        project_id: int,
        items: list[dict],
        scope: str = "instance",
        reason: str = "",
    ) -> Result[int]:
        """
        Descarta múltiples alertas de una vez.

        Args:
            project_id: ID del proyecto
            items: Lista de dicts con {content_hash, alert_type, source_module}
            scope: Alcance del descarte
            reason: Razón del descarte

        Returns:
            Result con el número de alertas descartadas
        """
        try:
            with self.db.transaction() as conn:
                params = [
                    (
                        project_id,
                        item["content_hash"],
                        scope,
                        reason,
                        item.get("alert_type", ""),
                        item.get("source_module", ""),
                    )
                    for item in items
                ]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO alert_dismissals
                        (project_id, content_hash, scope, reason, alert_type, source_module)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
            count = len(items)
            logger.info(f"Batch dismissed {count} alerts for project {project_id}")
            return Result.success(count)
        except Exception as e:
            error = DatabaseError(
                message="Error in batch dismiss",
                context={"error": str(e), "count": len(items)},
            )
            logger.error(f"Failed batch dismiss: {e}")
            return Result.failure(error)

    def undismiss(self, project_id: int, content_hash: str) -> Result[None]:
        """
        Revierte el descarte de una alerta.

        Args:
            project_id: ID del proyecto
            content_hash: Hash del contenido de la alerta

        Returns:
            Result indicando éxito o fallo
        """
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    "DELETE FROM alert_dismissals WHERE project_id = ? AND content_hash = ?",
                    (project_id, content_hash),
                )
            logger.debug(f"Undismissed alert hash={content_hash[:8]}... project={project_id}")
            return Result.success(None)
        except Exception as e:
            error = DatabaseError(
                message="Error undismissing alert",
                context={"error": str(e), "content_hash": content_hash},
            )
            return Result.failure(error)

    def get_dismissal_stats(self, project_id: int) -> Result[dict]:
        """
        Obtiene estadísticas de descartes por tipo de alerta y módulo.

        Permite identificar qué detectores generan más falsos positivos.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con dict:
            {
                "by_alert_type": {"attribute_inconsistency": 5, ...},
                "by_source_module": {"attribute_consistency": 3, ...},
                "total_dismissed": 15,
                "by_reason": {"false_positive": 10, ...}
            }
        """
        try:
            stats: dict = {
                "by_alert_type": {},
                "by_source_module": {},
                "by_reason": {},
                "total_dismissed": 0,
            }

            with self.db.connection() as conn:
                # Total
                row = conn.execute(
                    "SELECT COUNT(*) FROM alert_dismissals WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                stats["total_dismissed"] = row[0] if row else 0

                # Por tipo de alerta
                rows = conn.execute(
                    """
                    SELECT alert_type, COUNT(*) as cnt
                    FROM alert_dismissals
                    WHERE project_id = ? AND alert_type != ''
                    GROUP BY alert_type
                    ORDER BY cnt DESC
                    """,
                    (project_id,),
                ).fetchall()
                stats["by_alert_type"] = {r[0]: r[1] for r in rows}

                # Por módulo fuente
                rows = conn.execute(
                    """
                    SELECT source_module, COUNT(*) as cnt
                    FROM alert_dismissals
                    WHERE project_id = ? AND source_module != ''
                    GROUP BY source_module
                    ORDER BY cnt DESC
                    """,
                    (project_id,),
                ).fetchall()
                stats["by_source_module"] = {r[0]: r[1] for r in rows}

                # Por razón
                rows = conn.execute(
                    """
                    SELECT reason, COUNT(*) as cnt
                    FROM alert_dismissals
                    WHERE project_id = ? AND reason != ''
                    GROUP BY reason
                    ORDER BY cnt DESC
                    """,
                    (project_id,),
                ).fetchall()
                stats["by_reason"] = {r[0]: r[1] for r in rows}

            return Result.success(stats)
        except Exception as e:
            error = DatabaseError(
                message="Error getting dismissal stats",
                context={"error": str(e), "project_id": project_id},
            )
            logger.error(f"Failed to get dismissal stats: {e}")
            return Result.failure(error)

    # =========================================================================
    # Suppression Rules CRUD
    # =========================================================================

    def get_suppression_rules(
        self, project_id: int | None = None, active_only: bool = True
    ) -> Result[list[SuppressionRule]]:
        """
        Obtiene reglas de supresión.

        Args:
            project_id: ID del proyecto (None = solo reglas globales)
            active_only: Si True, solo retorna reglas activas

        Returns:
            Result con lista de reglas
        """
        try:
            query = "SELECT * FROM suppression_rules WHERE 1=1"
            params: list = []

            if project_id is not None:
                # Reglas del proyecto + globales
                query += " AND (project_id = ? OR project_id IS NULL)"
                params.append(project_id)
            else:
                query += " AND project_id IS NULL"

            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY created_at DESC"

            with self.db.connection() as conn:
                rows = conn.execute(query, params).fetchall()

            rules = [
                SuppressionRule(
                    id=r["id"],
                    project_id=r["project_id"],
                    rule_type=r["rule_type"],
                    pattern=r["pattern"],
                    entity_name=r["entity_name"],
                    reason=r["reason"] or "",
                    is_active=bool(r["is_active"]),
                    created_at=datetime.fromisoformat(r["created_at"])
                    if r["created_at"]
                    else datetime.now(),
                )
                for r in rows
            ]
            return Result.success(rules)
        except Exception as e:
            error = DatabaseError(
                message="Error getting suppression rules",
                context={"error": str(e)},
            )
            return Result.failure(error)

    def create_suppression_rule(
        self,
        rule_type: str,
        pattern: str,
        project_id: int | None = None,
        entity_name: str | None = None,
        reason: str = "",
    ) -> Result[int]:
        """
        Crea una nueva regla de supresión.

        Args:
            rule_type: Tipo de regla (alert_type, category, entity, source_module)
            pattern: Patrón a suprimir (soporta wildcards: spelling_*, etc.)
            project_id: ID del proyecto (None = global)
            entity_name: Nombre de entidad (si rule_type='entity')
            reason: Explicación de la regla

        Returns:
            Result con el ID de la regla creada
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO suppression_rules
                        (project_id, rule_type, pattern, entity_name, reason)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (project_id, rule_type, pattern, entity_name, reason),
                )
                rule_id = cursor.lastrowid
            logger.info(f"Created suppression rule {rule_id}: {rule_type}={pattern}")
            return Result.success(rule_id)
        except Exception as e:
            error = DatabaseError(
                message="Error creating suppression rule",
                context={"error": str(e)},
            )
            return Result.failure(error)

    def delete_suppression_rule(self, rule_id: int) -> Result[None]:
        """Elimina una regla de supresión."""
        try:
            with self.db.transaction() as conn:
                conn.execute("DELETE FROM suppression_rules WHERE id = ?", (rule_id,))
            return Result.success(None)
        except Exception as e:
            error = DatabaseError(
                message="Error deleting suppression rule",
                context={"error": str(e), "rule_id": rule_id},
            )
            return Result.failure(error)

    def toggle_suppression_rule(self, rule_id: int, active: bool) -> Result[None]:
        """Activa o desactiva una regla de supresión."""
        try:
            with self.db.transaction() as conn:
                conn.execute(
                    "UPDATE suppression_rules SET is_active = ? WHERE id = ?",
                    (1 if active else 0, rule_id),
                )
            return Result.success(None)
        except Exception as e:
            error = DatabaseError(
                message="Error toggling suppression rule",
                context={"error": str(e), "rule_id": rule_id},
            )
            return Result.failure(error)

    def is_suppressed(
        self,
        project_id: int,
        alert_type: str,
        category: str = "",
        source_module: str = "",
        entity_name: str = "",
    ) -> bool:
        """
        Verifica si una alerta debería suprimirse según las reglas activas.

        Args:
            project_id: ID del proyecto
            alert_type: Tipo de alerta
            category: Categoría de la alerta
            source_module: Módulo fuente
            entity_name: Nombre de entidad afectada

        Returns:
            True si la alerta debería suprimirse
        """
        result = self.get_suppression_rules(project_id, active_only=True)
        if result.is_failure:
            return False

        for rule in result.value:
            if rule.rule_type == "alert_type":
                if fnmatch.fnmatch(alert_type, rule.pattern):
                    return True
            elif rule.rule_type == "category":
                if fnmatch.fnmatch(category, rule.pattern):
                    return True
            elif rule.rule_type == "source_module":
                if fnmatch.fnmatch(source_module, rule.pattern):
                    return True
            elif rule.rule_type == "entity" and rule.entity_name and entity_name:
                if rule.entity_name.lower() == entity_name.lower():
                    # Check alert_type pattern too if provided
                    if rule.pattern == "*" or fnmatch.fnmatch(alert_type, rule.pattern):
                        return True

        return False


def get_dismissal_repository() -> DismissalRepository:
    """
    Obtiene la instancia singleton del repositorio de dismissals.

    Thread-safe con double-checked locking.

    Returns:
        Instancia única de DismissalRepository
    """
    global _dismissal_repository

    if _dismissal_repository is None:
        with _repository_lock:
            if _dismissal_repository is None:
                _dismissal_repository = DismissalRepository()
                logger.debug("DismissalRepository singleton initialized")

    return _dismissal_repository
