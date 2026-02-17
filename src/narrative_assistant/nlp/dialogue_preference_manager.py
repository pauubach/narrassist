"""
DialogueStylePreferenceManager - Gestión de cambios de preferencia de estilo de diálogo.

Coordina la actualización de preferencias y la regeneración de alertas sin re-análisis.
"""

import json
import logging

from ..core.result import Result
from ..persistence.database import Database, get_database
from .dialogue_style_checker import DialogueStyleChecker

logger = logging.getLogger(__name__)


class DialogueStylePreferenceManager:
    """
    Gestiona cambios en la preferencia de estilo de diálogo.

    Responsabilidades:
    - Actualizar preferencia en settings_json del proyecto
    - Invalidar alertas antiguas de estilo de diálogo
    - Generar nuevas alertas según la nueva preferencia (sin re-análisis)
    """

    def __init__(self, db: Database | None = None):
        """
        Inicializa el manager.

        Args:
            db: Base de datos (opcional, usa global si no se especifica)
        """
        self.db = db or get_database()
        self.dialogue_checker = DialogueStyleChecker(self.db)

    def update_preference(
        self, project_id: int, new_preference: str, min_severity: str = "info"
    ) -> Result[dict]:
        """
        Actualiza preferencia de estilo y regenera alertas (SIN re-análisis).

        Args:
            project_id: ID del proyecto
            new_preference: Nueva preferencia (dash, guillemets, quotes, quotes_typographic, no_check)
            min_severity: Severidad mínima de alertas a crear

        Returns:
            Result con dict conteniendo:
            - preference: Preferencia actualizada
            - alerts_invalidated: Número de alertas invalidadas
            - alerts_created: Número de alertas creadas
        """
        try:
            # 1. Actualizar preferencia en settings_json
            with self.db.connection() as conn:
                # Obtener settings actuales
                conn.row_factory = lambda c, r: dict(
                    zip([col[0] for col in c.description], r, strict=False)
                )
                row = conn.execute(
                    "SELECT settings_json FROM projects WHERE id = ?",
                    (project_id,),
                ).fetchone()

                if not row:
                    return Result.failure(
                        ValueError(f"Project {project_id} not found")
                    )

                settings = json.loads(row.get("settings_json") or "{}")
                settings["dialogue_style_preference"] = new_preference

                # Actualizar
                conn.execute(
                    "UPDATE projects SET settings_json = ? WHERE id = ?",
                    (json.dumps(settings), project_id),
                )

            logger.info(
                f"Updated dialogue_style_preference for project {project_id}: {new_preference}"
            )

            # 2. Invalidar alertas antiguas
            invalidated = self._invalidate_old_alerts(project_id)

            # 3. Generar nuevas alertas (consulta DB, NO re-analiza)
            if new_preference == "no_check":
                alerts_created = 0
                logger.info(
                    f"Project {project_id}: preference set to no_check, no alerts created"
                )
            else:
                result = self.dialogue_checker.validate_and_create_alerts(
                    project_id, min_severity
                )
                if result.is_failure:
                    return result

                alerts_created = result.value

            return Result.success(
                {
                    "preference": new_preference,
                    "alerts_invalidated": invalidated,
                    "alerts_created": alerts_created,
                }
            )

        except Exception as e:
            logger.error(
                f"Error updating dialogue preference for project {project_id}: {e}"
            )
            return Result.failure(e)

    def _invalidate_old_alerts(self, project_id: int) -> int:
        """
        Invalida (elimina) alertas antiguas de estilo de diálogo.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de alertas invalidadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM alerts
                WHERE project_id = ? AND alert_type = 'dialogue_style'
                """,
                (project_id,),
            )
            return cursor.rowcount


# Singleton thread-safe
_manager: DialogueStylePreferenceManager | None = None
_manager_lock = __import__("threading").Lock()


def get_dialogue_preference_manager(
    db: Database | None = None,
) -> DialogueStylePreferenceManager:
    """
    Obtiene la instancia singleton del manager.

    Args:
        db: Base de datos (opcional)

    Returns:
        Instancia singleton de DialogueStylePreferenceManager
    """
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = DialogueStylePreferenceManager(db)
    return _manager


def reset_dialogue_preference_manager():
    """Resetea el singleton (solo para tests)."""
    global _manager
    _manager = None
