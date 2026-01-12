"""
Motor centralizado de alertas.

Recibe alertas de todos los detectores, las clasifica, prioriza
y gestiona su ciclo de vida.
"""

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional

from ..core.result import Result
from .models import Alert, AlertCategory, AlertFilter, AlertSeverity, AlertStatus
from .repository import AlertRepository, get_alert_repository

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_engine_lock = threading.Lock()
_alert_engine: Optional["AlertEngine"] = None


class AlertEngine:
    """
    Motor centralizado para gestión de alertas.

    Características:
    - Crea alertas desde diferentes detectores
    - Clasifica y prioriza automáticamente
    - Gestiona estados y transiciones
    - Filtra y busca alertas
    - Genera resúmenes y estadísticas
    """

    def __init__(self, repository: Optional[AlertRepository] = None):
        """
        Inicializa el motor de alertas.

        Args:
            repository: Repositorio de alertas (opcional, usa singleton por defecto)
        """
        self.repo = repository or get_alert_repository()
        self.alert_handlers: dict[str, Callable[[Any], Alert]] = {}

    def register_handler(
        self, alert_type: str, handler: Callable[[Any], Alert]
    ) -> None:
        """
        Registra un handler para convertir resultados de detector a alertas.

        Args:
            alert_type: Tipo de alerta (ej: "attribute_inconsistency")
            handler: Función que convierte resultado a Alert
        """
        self.alert_handlers[alert_type] = handler
        logger.debug(f"Registered handler for alert type: {alert_type}")

    def create_alert(
        self,
        project_id: int,
        category: AlertCategory,
        severity: AlertSeverity,
        alert_type: str,
        title: str,
        description: str,
        explanation: str,
        **kwargs,
    ) -> Result[Alert]:
        """
        Crea una nueva alerta.

        Args:
            project_id: ID del proyecto
            category: Categoría de la alerta
            severity: Severidad
            alert_type: Tipo específico
            title: Título breve
            description: Descripción corta
            explanation: Explicación detallada
            **kwargs: Campos opcionales (suggestion, chapter, entity_ids, etc.)

        Returns:
            Result con la alerta creada
        """
        alert = Alert(
            id=0,  # Se asignará por la DB
            project_id=project_id,
            category=category,
            severity=severity,
            alert_type=alert_type,
            title=title,
            description=description,
            explanation=explanation,
            suggestion=kwargs.get("suggestion"),
            chapter=kwargs.get("chapter"),
            scene=kwargs.get("scene"),
            start_char=kwargs.get("start_char"),
            end_char=kwargs.get("end_char"),
            excerpt=kwargs.get("excerpt", ""),
            entity_ids=kwargs.get("entity_ids", []),
            confidence=kwargs.get("confidence", 0.8),
            source_module=kwargs.get("source_module", ""),
            extra_data=kwargs.get("extra_data", {}),
        )

        return self.repo.create(alert)

    def create_alerts_batch(
        self, project_id: int, alerts_data: list[dict[str, Any]]
    ) -> Result[list[Alert]]:
        """
        Crea múltiples alertas de una vez.

        Args:
            project_id: ID del proyecto
            alerts_data: Lista de diccionarios con datos de alertas

        Returns:
            Result con lista de alertas creadas
        """
        created_alerts = []
        errors = []

        for data in alerts_data:
            data["project_id"] = project_id
            result = self.create_alert(**data)

            if result.is_success:
                created_alerts.append(result.value)
            else:
                errors.append(result.error)

        if errors:
            logger.warning(f"Created {len(created_alerts)} alerts with {len(errors)} errors")
            return Result.partial(created_alerts, errors)

        logger.info(f"Created {len(created_alerts)} alerts for project {project_id}")
        return Result.success(created_alerts)

    def get_alerts(
        self, project_id: int, alert_filter: Optional[AlertFilter] = None
    ) -> Result[list[Alert]]:
        """
        Obtiene alertas con filtros opcionales.

        Args:
            project_id: ID del proyecto
            alert_filter: Filtro opcional

        Returns:
            Result con lista de alertas filtradas
        """
        result = self.repo.get_by_project(project_id)
        if result.is_failure:
            return result

        alerts = result.value

        if alert_filter:
            alerts = [a for a in alerts if alert_filter.matches(a)]
            logger.debug(
                f"Filtered to {len(alerts)} alerts for project {project_id}"
            )

        return Result.success(alerts)

    def get_alert(self, alert_id: int) -> Result[Alert]:
        """
        Obtiene una alerta específica por ID.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result con la alerta
        """
        return self.repo.get(alert_id)

    def update_alert_status(
        self,
        alert_id: int,
        status: AlertStatus,
        note: str = "",
    ) -> Result[Alert]:
        """
        Actualiza el estado de una alerta.

        Args:
            alert_id: ID de la alerta
            status: Nuevo estado
            note: Nota sobre la resolución

        Returns:
            Result con la alerta actualizada
        """
        result = self.repo.get(alert_id)
        if result.is_failure:
            return result

        alert = result.value
        old_status = alert.status

        alert.status = status
        alert.resolution_note = note

        if status in [AlertStatus.RESOLVED, AlertStatus.DISMISSED, AlertStatus.AUTO_RESOLVED]:
            alert.resolved_at = datetime.now()

        result = self.repo.update(alert)

        if result.is_success:
            logger.info(
                f"Alert {alert_id} status changed: {old_status.value} → {status.value}"
            )

        return result

    def dismiss_alert(self, alert_id: int, reason: str = "") -> Result[Alert]:
        """Descarta una alerta (falso positivo)."""
        return self.update_alert_status(
            alert_id, AlertStatus.DISMISSED, f"Descartada: {reason}"
        )

    def resolve_alert(self, alert_id: int, resolution: str = "") -> Result[Alert]:
        """Marca una alerta como resuelta."""
        return self.update_alert_status(
            alert_id, AlertStatus.RESOLVED, f"Resuelto: {resolution}"
        )

    def acknowledge_alert(self, alert_id: int) -> Result[Alert]:
        """Marca una alerta como vista/reconocida."""
        return self.update_alert_status(
            alert_id, AlertStatus.ACKNOWLEDGED, "Usuario vio la alerta"
        )

    def get_summary(self, project_id: int) -> Result[dict[str, Any]]:
        """
        Genera resumen estadístico de alertas.

        Args:
            project_id: ID del proyecto

        Returns:
            Result con diccionario de estadísticas
        """
        result = self.repo.get_by_project(project_id)
        if result.is_failure:
            return result

        alerts = result.value

        summary = {
            "total": len(alerts),
            "open": sum(1 for a in alerts if a.is_open()),
            "closed": sum(1 for a in alerts if a.is_closed()),
            "by_category": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_status": defaultdict(int),
            "by_chapter": defaultdict(int),
            "by_source": defaultdict(int),
        }

        for alert in alerts:
            summary["by_category"][alert.category.value] += 1
            summary["by_severity"][alert.severity.value] += 1
            summary["by_status"][alert.status.value] += 1
            summary["by_source"][alert.source_module] += 1
            if alert.chapter:
                summary["by_chapter"][alert.chapter] += 1

        # Convertir defaultdict a dict normal
        summary["by_category"] = dict(summary["by_category"])
        summary["by_severity"] = dict(summary["by_severity"])
        summary["by_status"] = dict(summary["by_status"])
        summary["by_chapter"] = dict(summary["by_chapter"])
        summary["by_source"] = dict(summary["by_source"])

        return Result.success(summary)

    def prioritize_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """
        Ordena alertas por prioridad.

        Criterios:
        1. Severidad (CRITICAL > WARNING > INFO > HINT)
        2. Confianza (mayor primero)
        3. Capítulo (orden de aparición)

        Args:
            alerts: Lista de alertas sin ordenar

        Returns:
            Lista ordenada por prioridad
        """
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.INFO: 2,
            AlertSeverity.HINT: 3,
        }

        return sorted(
            alerts,
            key=lambda a: (
                severity_order.get(a.severity, 4),
                -a.confidence,
                a.chapter or 0,
            ),
        )

    def calculate_severity_from_confidence(self, confidence: float) -> AlertSeverity:
        """
        Calcula severidad automáticamente basada en confianza.

        Args:
            confidence: Nivel de confianza (0.0-1.0)

        Returns:
            Severidad calculada
        """
        if confidence >= 0.9:
            return AlertSeverity.CRITICAL
        elif confidence >= 0.7:
            return AlertSeverity.WARNING
        elif confidence >= 0.5:
            return AlertSeverity.INFO
        else:
            return AlertSeverity.HINT

    def delete_alert(self, alert_id: int) -> Result[None]:
        """
        Elimina una alerta permanentemente.

        Args:
            alert_id: ID de la alerta

        Returns:
            Result indicando éxito o fallo
        """
        return self.repo.delete(alert_id)

    # --- Métodos helper para crear alertas desde detectores específicos ---

    def create_from_attribute_inconsistency(
        self,
        project_id: int,
        entity_name: str,
        entity_id: int,
        attribute_key: str,
        value1: str,
        value2: str,
        value1_source: dict[str, Any],
        value2_source: dict[str, Any],
        explanation: str,
        confidence: float = 0.9,
    ) -> Result[Alert]:
        """
        Crea alerta desde inconsistencia de atributo.

        IMPORTANTE: Incluye referencias a ubicaciones para mostrar:
        "Capítulo X: 'valor1' vs Capítulo Y: 'valor2'"

        Args:
            value1_source, value2_source: Deben incluir:
                - chapter: int
                - page: int (calculado con calculate_page_and_line)
                - line: int (calculado con calculate_page_and_line)
                - start_char: int
                - end_char: int
                - text/excerpt: str

        Example:
            value1_source = {
                "chapter": 2,
                "page": 14,
                "line": 5,
                "start_char": 1234,
                "end_char": 1280,
                "excerpt": "ojos azules"
            }
        """
        severity = self.calculate_severity_from_confidence(confidence)

        # Construir descripción con referencias mejoradas
        ref1 = f"Cap. {value1_source.get('chapter', '?')}"
        if "page" in value1_source:
            ref1 += f", pág. {value1_source['page']}"
        if "line" in value1_source:
            ref1 += f", lín. {value1_source['line']}"

        ref2 = f"Cap. {value2_source.get('chapter', '?')}"
        if "page" in value2_source:
            ref2 += f", pág. {value2_source['page']}"
        if "line" in value2_source:
            ref2 += f", lín. {value2_source['line']}"

        # Estructura sources[] para frontend
        sources = [
            {
                "chapter": value1_source.get("chapter"),
                "page": value1_source.get("page", 1),
                "line": value1_source.get("line", 1),
                "start_char": value1_source.get("start_char", value1_source.get("position", 0)),
                "end_char": value1_source.get("end_char", value1_source.get("start_char", 0) + 100),
                "excerpt": value1_source.get("text", value1_source.get("excerpt", "")),
                "value": value1,
            },
            {
                "chapter": value2_source.get("chapter"),
                "page": value2_source.get("page", 1),
                "line": value2_source.get("line", 1),
                "start_char": value2_source.get("start_char", value2_source.get("position", 0)),
                "end_char": value2_source.get("end_char", value2_source.get("start_char", 0) + 100),
                "excerpt": value2_source.get("text", value2_source.get("excerpt", "")),
                "value": value2,
            },
        ]

        return self.create_alert(
            project_id=project_id,
            category=AlertCategory.CONSISTENCY,
            severity=severity,
            alert_type="attribute_inconsistency",
            title=f"Inconsistencia: {attribute_key} de {entity_name}",
            description=f"{ref1}: '{value1}' vs {ref2}: '{value2}'",
            explanation=explanation,
            suggestion=f"Verificar cuál es el valor correcto para {attribute_key}",
            chapter=value1_source.get("chapter"),
            entity_ids=[entity_id],
            confidence=confidence,
            source_module="attribute_consistency",
            extra_data={
                "entity_name": entity_name,
                "attribute_key": attribute_key,
                "value1": value1,
                "value2": value2,
                # ✅ Nueva estructura sources[] (consistente, fácil de usar en UI)
                "sources": sources,
                # ⚠️ Deprecated: mantener por compatibilidad temporal
                "value1_source": value1_source,
                "value2_source": value2_source,
            },
        )


def get_alert_engine() -> AlertEngine:
    """
    Obtiene la instancia singleton del motor de alertas.

    Thread-safe con double-checked locking.

    Returns:
        Instancia única de AlertEngine
    """
    global _alert_engine

    if _alert_engine is None:
        with _engine_lock:
            if _alert_engine is None:
                _alert_engine = AlertEngine()
                logger.debug("AlertEngine singleton initialized")

    return _alert_engine
