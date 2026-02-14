"""
Sistema híbrido de filtros de entidades.

Arquitectura de 3 niveles con prioridad:
1. Project Override (máxima prioridad) - 'force_include' o 'reject' por proyecto
2. User Global - Rechazos globales del usuario
3. System Patterns - Patrones predefinidos del sistema (toggleables)

Orden de evaluación:
1. Si hay project_override con 'force_include' → INCLUIR
2. Si hay project_override con 'reject' → RECHAZAR
3. Si coincide con user_rejected_entities → RECHAZAR
4. Si coincide con system_entity_patterns activo → RECHAZAR
5. De lo contrario → INCLUIR
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from enum import Enum

from ..persistence.database import get_database

logger = logging.getLogger(__name__)


class FilterAction(Enum):
    """Acciones posibles para un override de proyecto."""

    REJECT = "reject"
    FORCE_INCLUDE = "force_include"


class PatternType(Enum):
    """Tipos de patrones soportados."""

    EXACT = "exact"
    REGEX = "regex"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    CONTAINS = "contains"


@dataclass
class SystemPattern:
    """Patrón de falso positivo del sistema."""

    id: int
    pattern: str
    pattern_type: PatternType
    entity_type: str | None
    language: str
    category: str | None
    description: str | None
    is_active: bool


@dataclass
class UserRejection:
    """Rechazo global del usuario."""

    id: int
    entity_name: str
    entity_type: str | None
    reason: str | None
    rejected_at: str


@dataclass
class ProjectOverride:
    """Override de entidad a nivel de proyecto."""

    id: int
    project_id: int
    entity_name: str
    entity_type: str | None
    action: FilterAction
    reason: str | None
    created_at: str


@dataclass
class FilterDecision:
    """Resultado de evaluar si una entidad debe filtrarse."""

    should_filter: bool
    reason: str
    level: str  # 'project', 'user', 'system', 'none'
    rule_id: int | None = None


# =============================================================================
# Patrones predefinidos del sistema para español
# =============================================================================

SYSTEM_PATTERNS_ES = [
    # Marcadores temporales
    ("Al día siguiente", "exact", None, "temporal", "Expresión temporal común"),
    ("Al cabo de", "startswith", None, "temporal", "Expresión temporal de duración"),
    ("Hace tiempo", "exact", None, "temporal", "Expresión temporal vaga"),
    ("Aquella noche", "exact", None, "temporal", "Expresión temporal demostrativa"),
    ("Aquella mañana", "exact", None, "temporal", "Expresión temporal demostrativa"),
    ("Aquel día", "exact", None, "temporal", "Expresión temporal demostrativa"),
    ("En ese momento", "exact", None, "temporal", "Expresión temporal"),
    ("En aquel momento", "exact", None, "temporal", "Expresión temporal"),
    ("Mientras tanto", "exact", None, "temporal", "Expresión temporal"),
    ("Por aquel entonces", "exact", None, "temporal", "Expresión temporal"),
    ("Un rato después", "exact", None, "temporal", "Expresión temporal"),
    ("Poco después", "exact", None, "temporal", "Expresión temporal"),
    ("Mucho después", "exact", None, "temporal", "Expresión temporal"),
    ("Horas después", "exact", None, "temporal", "Expresión temporal"),
    ("Días después", "exact", None, "temporal", "Expresión temporal"),
    ("Semanas después", "exact", None, "temporal", "Expresión temporal"),
    ("Meses después", "exact", None, "temporal", "Expresión temporal"),
    ("Años después", "exact", None, "temporal", "Expresión temporal"),
    # Artículos y determinantes como entidades
    ("El", "exact", None, "article", "Artículo determinado"),
    ("La", "exact", None, "article", "Artículo determinado"),
    ("Los", "exact", None, "article", "Artículo determinado"),
    ("Las", "exact", None, "article", "Artículo determinado"),
    ("Un", "exact", None, "article", "Artículo indeterminado"),
    ("Una", "exact", None, "article", "Artículo indeterminado"),
    ("Unos", "exact", None, "article", "Artículo indeterminado"),
    ("Unas", "exact", None, "article", "Artículo indeterminado"),
    # Pronombres que a veces se detectan como entidades
    ("Él", "exact", None, "pronoun", "Pronombre personal"),
    ("Ella", "exact", None, "pronoun", "Pronombre personal"),
    ("Ellos", "exact", None, "pronoun", "Pronombre personal"),
    ("Ellas", "exact", None, "pronoun", "Pronombre personal"),
    ("Alguien", "exact", None, "pronoun", "Pronombre indefinido"),
    ("Nadie", "exact", None, "pronoun", "Pronombre indefinido"),
    ("Algo", "exact", None, "pronoun", "Pronombre indefinido"),
    ("Nada", "exact", None, "pronoun", "Pronombre indefinido"),
    ("Todo", "exact", None, "pronoun", "Pronombre indefinido"),
    ("Todos", "exact", None, "pronoun", "Pronombre indefinido"),
    # Expresiones comunes que no son entidades
    ("Sin embargo", "exact", None, "connector", "Conector adversativo"),
    ("No obstante", "exact", None, "connector", "Conector adversativo"),
    ("Por lo tanto", "exact", None, "connector", "Conector consecutivo"),
    ("Además", "exact", None, "connector", "Conector aditivo"),
    ("Por otra parte", "exact", None, "connector", "Conector"),
    ("En cambio", "exact", None, "connector", "Conector"),
    # Números y cantidades
    (r"^\d+$", "regex", None, "numeric", "Solo números"),
    (r"^\d+[\.,]\d+$", "regex", None, "numeric", "Número decimal"),
    (
        r"^\d+\s*(años|meses|días|horas|minutos|segundos)$",
        "regex",
        None,
        "numeric",
        "Cantidad temporal",
    ),
    # Patrones de lugares genéricos
    ("La casa", "exact", "location", "generic_location", "Lugar genérico"),
    ("El edificio", "exact", "location", "generic_location", "Lugar genérico"),
    ("La habitación", "exact", "location", "generic_location", "Lugar genérico"),
    ("El cuarto", "exact", "location", "generic_location", "Lugar genérico"),
    ("La cocina", "exact", "location", "generic_location", "Lugar genérico"),
    ("El salón", "exact", "location", "generic_location", "Lugar genérico"),
    ("La calle", "exact", "location", "generic_location", "Lugar genérico"),
    # Conceptos genéricos que no deberían ser entidades
    ("El tiempo", "exact", "concept", "generic_concept", "Concepto abstracto genérico"),
    ("La vida", "exact", "concept", "generic_concept", "Concepto abstracto genérico"),
    ("El amor", "exact", "concept", "generic_concept", "Concepto abstracto genérico"),
    ("La muerte", "exact", "concept", "generic_concept", "Concepto abstracto genérico"),
    ("El mundo", "exact", "concept", "generic_concept", "Concepto abstracto genérico"),
]


class EntityFilterRepository:
    """
    Repositorio para gestionar filtros de entidades.

    Implementa el sistema híbrido de 3 niveles:
    - System patterns (predefinidos)
    - User rejections (globales)
    - Project overrides (por proyecto)
    """

    def __init__(self):
        self.db = get_database()
        self._ensure_system_patterns()

    def _ensure_system_patterns(self) -> None:
        """Asegura que los patrones del sistema estén cargados."""
        with self.db.connection() as conn:
            # Verificar si ya hay patrones
            count = conn.execute(
                "SELECT COUNT(*) FROM system_entity_patterns WHERE language = 'es'"
            ).fetchone()[0]

            if count == 0:
                logger.info("Inicializando patrones de sistema para español...")
                self._load_system_patterns(conn, "es", SYSTEM_PATTERNS_ES)

    def _load_system_patterns(
        self, conn: sqlite3.Connection, language: str, patterns: list[tuple]
    ) -> None:
        """Carga patrones del sistema en la base de datos."""
        for pattern_data in patterns:
            pattern, pattern_type, entity_type, category, description = pattern_data
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO system_entity_patterns
                    (pattern, pattern_type, entity_type, language, category, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (pattern, pattern_type, entity_type, language, category, description),
                )
            except sqlite3.Error as e:
                logger.warning(f"Error insertando patrón '{pattern}': {e}")

        conn.commit()
        logger.info(f"Cargados {len(patterns)} patrones para idioma '{language}'")

    # =========================================================================
    # Evaluación de filtros
    # =========================================================================

    def should_filter_entity(
        self, entity_name: str, entity_type: str | None = None, project_id: int | None = None
    ) -> FilterDecision:
        """
        Evalúa si una entidad debe filtrarse.

        Args:
            entity_name: Nombre de la entidad
            entity_type: Tipo de entidad (character, location, etc.)
            project_id: ID del proyecto (para overrides)

        Returns:
            FilterDecision con el resultado y la razón
        """
        normalized_name = entity_name.strip().lower()

        # 1. Verificar project override (máxima prioridad)
        if project_id is not None:
            override = self._get_project_override(project_id, normalized_name, entity_type)
            if override:
                if override.action == FilterAction.FORCE_INCLUDE:
                    return FilterDecision(
                        should_filter=False,
                        reason=f"Forzado a incluir en proyecto: {override.reason or 'Sin razón'}",
                        level="project",
                        rule_id=override.id,
                    )
                else:  # REJECT
                    return FilterDecision(
                        should_filter=True,
                        reason=f"Rechazado en proyecto: {override.reason or 'Sin razón'}",
                        level="project",
                        rule_id=override.id,
                    )

        # 2. Verificar user rejection
        user_rejection = self._get_user_rejection(normalized_name, entity_type)
        if user_rejection:
            return FilterDecision(
                should_filter=True,
                reason=f"Rechazado globalmente: {user_rejection.reason or 'Sin razón'}",
                level="user",
                rule_id=user_rejection.id,
            )

        # 3. Verificar system patterns
        system_match = self._matches_system_pattern(entity_name, entity_type)
        if system_match:
            return FilterDecision(
                should_filter=True,
                reason=f"Patrón del sistema: {system_match.description or system_match.pattern}",
                level="system",
                rule_id=system_match.id,
            )

        # 4. No hay filtro
        return FilterDecision(
            should_filter=False, reason="No coincide con ningún filtro", level="none"
        )

    def _get_project_override(
        self, project_id: int, entity_name: str, entity_type: str | None
    ) -> ProjectOverride | None:
        """Busca un override a nivel de proyecto."""
        # Buscar coincidencia exacta con tipo
        row = self.db.fetchone(
            """
            SELECT * FROM project_entity_overrides
            WHERE project_id = ? AND entity_name = ? AND (entity_type = ? OR entity_type IS NULL)
            ORDER BY CASE WHEN entity_type IS NOT NULL THEN 0 ELSE 1 END
            LIMIT 1
        """,
            (project_id, entity_name, entity_type),
        )

        if row:
            return ProjectOverride(
                id=row["id"],
                project_id=row["project_id"],
                entity_name=row["entity_name"],
                entity_type=row["entity_type"],
                action=FilterAction(row["action"]),
                reason=row["reason"],
                created_at=row["created_at"],
            )
        return None

    def _get_user_rejection(
        self, entity_name: str, entity_type: str | None
    ) -> UserRejection | None:
        """Busca un rechazo global del usuario."""
        row = self.db.fetchone(
            """
            SELECT * FROM user_rejected_entities
            WHERE entity_name = ? AND (entity_type = ? OR entity_type IS NULL)
            ORDER BY CASE WHEN entity_type IS NOT NULL THEN 0 ELSE 1 END
            LIMIT 1
        """,
            (entity_name, entity_type),
        )

        if row:
            return UserRejection(
                id=row["id"],
                entity_name=row["entity_name"],
                entity_type=row["entity_type"],
                reason=row["reason"],
                rejected_at=row["rejected_at"],
            )
        return None

    def _matches_system_pattern(
        self, entity_name: str, entity_type: str | None
    ) -> SystemPattern | None:
        """Verifica si una entidad coincide con algún patrón del sistema activo."""
        patterns = self.db.fetchall(
            """
            SELECT * FROM system_entity_patterns
            WHERE is_active = 1
            AND (entity_type IS NULL OR entity_type = ?)
            ORDER BY
                CASE WHEN entity_type IS NOT NULL THEN 0 ELSE 1 END,
                pattern_type
        """,
            (entity_type,),
        )

        for row in patterns:
            pattern = SystemPattern(
                id=row["id"],
                pattern=row["pattern"],
                pattern_type=PatternType(row["pattern_type"]),
                entity_type=row["entity_type"],
                language=row["language"],
                category=row["category"],
                description=row["description"],
                is_active=bool(row["is_active"]),
            )

            if self._pattern_matches(pattern, entity_name):
                return pattern

        return None

    def _pattern_matches(self, pattern: SystemPattern, entity_name: str) -> bool:
        """Verifica si un patrón coincide con un nombre de entidad."""
        text = entity_name.strip()
        pat = pattern.pattern

        if pattern.pattern_type == PatternType.EXACT:
            return text.lower() == pat.lower()
        elif pattern.pattern_type == PatternType.STARTSWITH:
            return text.lower().startswith(pat.lower())
        elif pattern.pattern_type == PatternType.ENDSWITH:
            return text.lower().endswith(pat.lower())
        elif pattern.pattern_type == PatternType.CONTAINS:
            return pat.lower() in text.lower()
        elif pattern.pattern_type == PatternType.REGEX:
            try:
                return bool(re.match(pat, text, re.IGNORECASE))
            except re.error:
                logger.warning(f"Patrón regex inválido: {pat}")
                return False

        return False

    # =========================================================================
    # Gestión de filtros
    # =========================================================================

    def add_project_override(
        self,
        project_id: int,
        entity_name: str,
        action: FilterAction,
        entity_type: str | None = None,
        reason: str | None = None,
    ) -> int:
        """
        Añade o actualiza un override a nivel de proyecto.

        Returns:
            ID del override creado/actualizado
        """
        normalized_name = entity_name.strip().lower()

        with self.db.transaction() as conn:
            # Upsert
            conn.execute(
                """
                INSERT INTO project_entity_overrides
                (project_id, entity_name, entity_type, action, reason)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (project_id, entity_name, entity_type)
                DO UPDATE SET action = excluded.action, reason = excluded.reason
            """,
                (project_id, normalized_name, entity_type, action.value, reason),
            )

            row = conn.execute(
                """
                SELECT id FROM project_entity_overrides
                WHERE project_id = ? AND entity_name = ?
                AND (entity_type = ? OR (entity_type IS NULL AND ? IS NULL))
            """,
                (project_id, normalized_name, entity_type, entity_type),
            ).fetchone()

            return row[0] if row else 0  # type: ignore[no-any-return]

    def remove_project_override(
        self, project_id: int, entity_name: str, entity_type: str | None = None
    ) -> bool:
        """Elimina un override de proyecto."""
        normalized_name = entity_name.strip().lower()

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                DELETE FROM project_entity_overrides
                WHERE project_id = ? AND entity_name = ?
                AND (entity_type = ? OR (entity_type IS NULL AND ? IS NULL))
            """,
                (project_id, normalized_name, entity_type, entity_type),
            )

            return cursor.rowcount > 0  # type: ignore[no-any-return]

    def add_user_rejection(
        self, entity_name: str, entity_type: str | None = None, reason: str | None = None
    ) -> int:
        """
        Añade un rechazo global del usuario.

        Returns:
            ID del rechazo creado
        """
        normalized_name = entity_name.strip().lower()

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_rejected_entities
                (entity_name, entity_type, reason)
                VALUES (?, ?, ?)
            """,
                (normalized_name, entity_type, reason),
            )

            row = conn.execute(
                """
                SELECT id FROM user_rejected_entities
                WHERE entity_name = ?
                AND (entity_type = ? OR (entity_type IS NULL AND ? IS NULL))
            """,
                (normalized_name, entity_type, entity_type),
            ).fetchone()

            return row[0] if row else 0  # type: ignore[no-any-return]

    def remove_user_rejection(self, entity_name: str, entity_type: str | None = None) -> bool:
        """Elimina un rechazo global del usuario."""
        normalized_name = entity_name.strip().lower()

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                DELETE FROM user_rejected_entities
                WHERE entity_name = ?
                AND (entity_type = ? OR (entity_type IS NULL AND ? IS NULL))
            """,
                (normalized_name, entity_type, entity_type),
            )

            return cursor.rowcount > 0  # type: ignore[no-any-return]

    def toggle_system_pattern(self, pattern_id: int, is_active: bool) -> bool:
        """Activa o desactiva un patrón del sistema."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE system_entity_patterns
                SET is_active = ?
                WHERE id = ?
            """,
                (1 if is_active else 0, pattern_id),
            )

            return cursor.rowcount > 0  # type: ignore[no-any-return]

    # =========================================================================
    # Listados para UI
    # =========================================================================

    def get_system_patterns(
        self, language: str = "es", only_active: bool = False
    ) -> list[SystemPattern]:
        """Lista todos los patrones del sistema."""
        query = """
            SELECT * FROM system_entity_patterns
            WHERE language = ?
        """
        params: list = [language]

        if only_active:
            query += " AND is_active = 1"

        query += " ORDER BY category, pattern"

        rows = self.db.fetchall(query, tuple(params))
        return [
            SystemPattern(
                id=row["id"],
                pattern=row["pattern"],
                pattern_type=PatternType(row["pattern_type"]),
                entity_type=row["entity_type"],
                language=row["language"],
                category=row["category"],
                description=row["description"],
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def get_user_rejections(self) -> list[UserRejection]:
        """Lista todos los rechazos globales del usuario."""
        rows = self.db.fetchall("""
            SELECT * FROM user_rejected_entities
            ORDER BY rejected_at DESC
        """)
        return [
            UserRejection(
                id=row["id"],
                entity_name=row["entity_name"],
                entity_type=row["entity_type"],
                reason=row["reason"],
                rejected_at=row["rejected_at"],
            )
            for row in rows
        ]

    def get_project_overrides(self, project_id: int) -> list[ProjectOverride]:
        """Lista todos los overrides de un proyecto."""
        rows = self.db.fetchall(
            """
            SELECT * FROM project_entity_overrides
            WHERE project_id = ?
            ORDER BY created_at DESC
        """,
            (project_id,),
        )
        return [
            ProjectOverride(
                id=row["id"],
                project_id=row["project_id"],
                entity_name=row["entity_name"],
                entity_type=row["entity_type"],
                action=FilterAction(row["action"]),
                reason=row["reason"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_filter_stats(self, project_id: int | None = None) -> dict:
        """Obtiene estadísticas de filtros."""
        stats = {
            "system_patterns_total": 0,
            "system_patterns_active": 0,
            "user_rejections": 0,
            "project_overrides_reject": 0,
            "project_overrides_include": 0,
        }

        # System patterns
        row = self.db.fetchone("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
            FROM system_entity_patterns
        """)
        if row:
            stats["system_patterns_total"] = row["total"]
            stats["system_patterns_active"] = row["active"]

        # User rejections
        row = self.db.fetchone("SELECT COUNT(*) as count FROM user_rejected_entities")
        if row:
            stats["user_rejections"] = row["count"]

        # Project overrides
        if project_id is not None:
            row = self.db.fetchone(
                """
                SELECT
                    SUM(CASE WHEN action = 'reject' THEN 1 ELSE 0 END) as rejects,
                    SUM(CASE WHEN action = 'force_include' THEN 1 ELSE 0 END) as includes
                FROM project_entity_overrides
                WHERE project_id = ?
            """,
                (project_id,),
            )
            if row:
                stats["project_overrides_reject"] = row["rejects"] or 0
                stats["project_overrides_include"] = row["includes"] or 0

        return stats


# Singleton
_filter_repository: EntityFilterRepository | None = None
_filter_lock = __import__("threading").Lock()


def get_filter_repository() -> EntityFilterRepository:
    """Obtiene instancia singleton del repositorio de filtros."""
    global _filter_repository
    if _filter_repository is None:
        with _filter_lock:
            if _filter_repository is None:
                _filter_repository = EntityFilterRepository()
    return _filter_repository
