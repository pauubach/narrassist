"""
DialogueStyleChecker - Validación de estilo de diálogo sin re-análisis.

Consulta los diálogos almacenados en BD y genera alertas dinámicamente
según la preferencia del usuario, sin necesidad de re-analizar el documento.
"""

import logging
from datetime import datetime

from ..core.result import Result
from ..persistence.database import Database, get_database
from ..persistence.dialogue import DialogueRepository, get_dialogue_repository

logger = logging.getLogger(__name__)


class DialogueStyleChecker:
    """
    Valida el estilo de diálogo consultando BD sin re-análisis.

    Flujo:
    1. Obtiene preferencia del proyecto desde settings_json
    2. Consulta diálogos que NO cumplen la preferencia (get_by_type_not)
    3. Genera alertas con severidad dinámica según proporción de errores
    """

    def __init__(self, db: Database | None = None):
        """
        Inicializa el checker.

        Args:
            db: Base de datos (opcional, usa global si no se especifica)
        """
        self.db = db or get_database()
        # Crear repositorio con la misma DB (NO usar singleton para tests)
        self.dialogue_repo = DialogueRepository(self.db)

    def get_style_preference(self, project_id: int) -> str | None:
        """
        Obtiene la preferencia de estilo de diálogo desde settings.

        Args:
            project_id: ID del proyecto

        Returns:
            Preferencia (dash, guillemets, quotes, quotes_typographic, no_check) o None
        """
        with self.db.connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r, strict=False))
            row = conn.execute(
                "SELECT settings_json FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

            if not row or not row.get("settings_json"):
                return None

            import json
            settings = json.loads(row["settings_json"])
            return settings.get("dialogue_style_preference")

    def validate_and_create_alerts(
        self, project_id: int, min_severity: str = "info"
    ) -> Result[int]:
        """
        Valida estilo de diálogo y crea alertas para inconsistencias.

        NO re-analiza el documento. Consulta diálogos existentes en BD.

        Args:
            project_id: ID del proyecto
            min_severity: Severidad mínima de alertas a crear (info, low, medium, high)

        Returns:
            Result con número de alertas creadas
        """
        try:
            # 1. Obtener preferencia
            preference = self.get_style_preference(project_id)

            if not preference or preference == "no_check":
                logger.debug(
                    f"Project {project_id}: no dialogue style preference or no_check, skipping validation"
                )
                return Result.success(0)

            # 2. Obtener estadísticas de diálogos
            all_dialogues = self.dialogue_repo.get_by_project(project_id)
            total = len(all_dialogues)

            if total == 0:
                logger.debug(f"Project {project_id}: no dialogues found, skipping validation")
                return Result.success(0)

            by_type = {}
            for dlg in all_dialogues:
                by_type[dlg.dialogue_type] = by_type.get(dlg.dialogue_type, 0) + 1

            # 3. Obtener diálogos que NO cumplen la preferencia
            non_compliant = self.dialogue_repo.get_by_type_not(project_id, preference)

            if not non_compliant:
                logger.debug(
                    f"Project {project_id}: all dialogues match preference '{preference}'"
                )
                return Result.success(0)

            # 4. Crear alertas con severidad dinámica
            alerts_created = 0
            for dialogue in non_compliant:
                severity = self._determine_severity(
                    dialogue, by_type, total, min_severity
                )

                if severity:
                    self._create_style_alert(project_id, dialogue, preference, severity)
                    alerts_created += 1

            logger.info(
                f"Project {project_id}: created {alerts_created} dialogue style alerts "
                f"({len(non_compliant)}/{total} dialogues don't match preference '{preference}')"
            )

            return Result.success(alerts_created)

        except Exception as e:
            logger.error(f"Error validating dialogue style for project {project_id}: {e}")
            return Result.failure(e)

    def _determine_severity(
        self,
        dialogue,
        by_type: dict[str, int],
        total: int,
        min_severity: str,
    ) -> str | None:
        """
        Determina severidad según proporción de inconsistencias.

        Lógica:
        - <20% inconsistente → HIGH (minoría de errores, probablemente error del usuario)
        - 20-80% inconsistente → MEDIUM (uso mixto)
        - >80% inconsistente → LOW (mayoría inconsistente, probablemente config incorrecta)

        Args:
            dialogue: Diálogo a evaluar
            by_type: Dict con conteo por tipo
            total: Total de diálogos
            min_severity: Severidad mínima a retornar

        Returns:
            Severidad (high, medium, low, info) o None si está por debajo del mínimo
        """
        # Calcular proporción del tipo del diálogo actual
        count_this_type = by_type.get(dialogue.dialogue_type, 0)
        proportion = count_this_type / total if total > 0 else 0

        # Determinar severidad
        if proportion < 0.20:
            severity = "high"  # Minoría de errores
        elif proportion < 0.80:
            severity = "medium"  # Uso mixto
        else:
            severity = "low"  # Mayoría inconsistente (config probablemente incorrecta)

        # Filtrar por min_severity
        severity_levels = {"info": 0, "low": 1, "medium": 2, "high": 3}
        if severity_levels.get(severity, 0) < severity_levels.get(min_severity, 0):
            return None

        return severity

    def _create_style_alert(
        self,
        project_id: int,
        dialogue,
        expected_style: str,
        severity: str,
    ):
        """
        Crea una alerta de estilo de diálogo.

        Args:
            project_id: ID del proyecto
            dialogue: DialogueData con información del diálogo
            expected_style: Estilo esperado
            severity: Severidad de la alerta
        """
        # Mapeo de tipos a descripciones amigables
        style_labels = {
            "dash": "raya (—)",
            "guillemets": "comillas latinas (« »)",
            "quotes": 'comillas rectas (" ")',
            "quotes_typographic": 'comillas inglesas (" ")',
        }

        found_label = style_labels.get(dialogue.dialogue_type, dialogue.dialogue_type)
        expected_label = style_labels.get(expected_style, expected_style)

        message = (
            f"Estilo de diálogo inconsistente: se encontró {found_label} "
            f"pero se esperaba {expected_label}"
        )

        suggestion = f"Cambiar a {expected_label} o actualizar la preferencia del proyecto"

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO alerts (
                    project_id, chapter, alert_type, category,
                    severity, title, description, explanation, suggestion,
                    start_char, end_char, excerpt, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    dialogue.chapter_id,  # chapter es INTEGER (no chapter_id)
                    "dialogue_style",
                    "typography",
                    severity,
                    "Estilo de diálogo inconsistente",
                    message,
                    f"Formato detectado: {found_label}. Formato esperado: {expected_label}.",
                    suggestion,
                    dialogue.start_char,
                    dialogue.end_char,
                    dialogue.text[:200],  # Limitar excerpt
                    datetime.now().isoformat(),
                ),
            )


# Singleton thread-safe
_checker: DialogueStyleChecker | None = None
_checker_lock = __import__("threading").Lock()


def get_dialogue_style_checker(db: Database | None = None) -> DialogueStyleChecker:
    """
    Obtiene la instancia singleton del checker.

    Args:
        db: Base de datos (opcional)

    Returns:
        Instancia singleton de DialogueStyleChecker
    """
    global _checker
    if _checker is None:
        with _checker_lock:
            if _checker is None:
                _checker = DialogueStyleChecker(db)
    return _checker


def reset_dialogue_style_checker():
    """Resetea el singleton (solo para tests)."""
    global _checker
    _checker = None
