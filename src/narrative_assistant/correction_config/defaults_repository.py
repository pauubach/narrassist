"""
Repositorio para gestionar overrides de configuración de corrección.

Permite a los usuarios personalizar los defaults de tipos/subtipos
sin modificar el código fuente.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from ..persistence.database import Database, get_database

logger = logging.getLogger(__name__)


class CorrectionConfigDefaultsRepository:
    """
    Gestiona overrides de configuración de corrección por tipo/subtipo.

    Los overrides se almacenan como deltas (solo los campos modificados),
    no como configuraciones completas.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Base de datos. Si None, usa la instancia global.
        """
        self.db = db or get_database()

    def get_override(
        self,
        type_code: str,
        subtype_code: Optional[str] = None
    ) -> Optional[dict]:
        """
        Obtiene el override de un tipo o subtipo.

        Args:
            type_code: Código del tipo (FIC, MEM, etc.)
            subtype_code: Código del subtipo (opcional). None = override de tipo.

        Returns:
            Dict con los overrides o None si no existe.
        """
        with self.db.connection() as conn:
            if subtype_code is None:
                cursor = conn.execute(
                    """
                    SELECT overrides_json, updated_at
                    FROM correction_config_overrides
                    WHERE type_code = ? AND subtype_code IS NULL
                    """,
                    (type_code,)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT overrides_json, updated_at
                    FROM correction_config_overrides
                    WHERE type_code = ? AND subtype_code = ?
                    """,
                    (type_code, subtype_code)
                )

            row = cursor.fetchone()
            if row:
                return {
                    "overrides": json.loads(row["overrides_json"]),
                    "updated_at": row["updated_at"]
                }
            return None

    def get_all_overrides(self) -> list[dict]:
        """
        Obtiene todos los overrides definidos por el usuario.

        Returns:
            Lista de overrides con type_code, subtype_code y overrides.
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT type_code, subtype_code, overrides_json, updated_at
                FROM correction_config_overrides
                ORDER BY type_code, subtype_code
                """
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "type_code": row["type_code"],
                    "subtype_code": row["subtype_code"],
                    "overrides": json.loads(row["overrides_json"]),
                    "updated_at": row["updated_at"]
                })
            return results

    def get_overrides_for_type(self, type_code: str) -> list[dict]:
        """
        Obtiene todos los overrides para un tipo y sus subtipos.

        Args:
            type_code: Código del tipo.

        Returns:
            Lista de overrides (tipo + subtipos).
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT type_code, subtype_code, overrides_json, updated_at
                FROM correction_config_overrides
                WHERE type_code = ?
                ORDER BY subtype_code NULLS FIRST
                """,
                (type_code,)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "type_code": row["type_code"],
                    "subtype_code": row["subtype_code"],
                    "overrides": json.loads(row["overrides_json"]),
                    "updated_at": row["updated_at"]
                })
            return results

    def set_override(
        self,
        type_code: str,
        subtype_code: Optional[str],
        overrides: dict
    ) -> bool:
        """
        Crea o actualiza un override.

        Args:
            type_code: Código del tipo.
            subtype_code: Código del subtipo (None para override de tipo).
            overrides: Dict con los parámetros a sobrescribir.

        Returns:
            True si se guardó correctamente.
        """
        if not overrides:
            # Si no hay overrides, eliminar el registro
            return self.delete_override(type_code, subtype_code)

        overrides_json = json.dumps(overrides, ensure_ascii=False)
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO correction_config_overrides
                    (type_code, subtype_code, overrides_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (type_code, subtype_code)
                DO UPDATE SET
                    overrides_json = excluded.overrides_json,
                    updated_at = excluded.updated_at
                """,
                (type_code, subtype_code, overrides_json, now)
            )

        logger.info(
            f"Override guardado: {type_code}"
            f"{f'/{subtype_code}' if subtype_code else ''}"
        )
        return True

    def delete_override(
        self,
        type_code: str,
        subtype_code: Optional[str] = None
    ) -> bool:
        """
        Elimina un override (reset a hardcoded defaults).

        Args:
            type_code: Código del tipo.
            subtype_code: Código del subtipo (None para override de tipo).

        Returns:
            True si se eliminó, False si no existía.
        """
        with self.db.connection() as conn:
            if subtype_code is None:
                cursor = conn.execute(
                    """
                    DELETE FROM correction_config_overrides
                    WHERE type_code = ? AND subtype_code IS NULL
                    """,
                    (type_code,)
                )
            else:
                cursor = conn.execute(
                    """
                    DELETE FROM correction_config_overrides
                    WHERE type_code = ? AND subtype_code = ?
                    """,
                    (type_code, subtype_code)
                )

            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(
                f"Override eliminado: {type_code}"
                f"{f'/{subtype_code}' if subtype_code else ''}"
            )
        return deleted

    def delete_all_overrides(self) -> int:
        """
        Elimina todos los overrides (full reset).

        Returns:
            Número de overrides eliminados.
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM correction_config_overrides"
            )
            count = cursor.rowcount

        logger.info(f"Todos los overrides eliminados: {count} registros")
        return count

    def has_overrides(self, type_code: str) -> bool:
        """
        Verifica si un tipo tiene overrides (él o sus subtipos).

        Args:
            type_code: Código del tipo.

        Returns:
            True si tiene algún override.
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                SELECT 1 FROM correction_config_overrides
                WHERE type_code = ?
                LIMIT 1
                """,
                (type_code,)
            )
            return cursor.fetchone() is not None


# Singleton para acceso global
_repository: Optional[CorrectionConfigDefaultsRepository] = None
_repository_lock = __import__('threading').Lock()


def get_defaults_repository() -> CorrectionConfigDefaultsRepository:
    """Obtiene la instancia singleton del repositorio."""
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = CorrectionConfigDefaultsRepository()
    return _repository
