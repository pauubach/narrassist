"""
Modelos de datos para el sistema de alertas.

Representa alertas generadas por diferentes detectores de inconsistencias.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AlertCategory(Enum):
    """Categorías de alertas."""

    CONSISTENCY = "consistency"  # Inconsistencias de atributos/tiempo
    STYLE = "style"  # Repeticiones, voz, estilo narrativo
    FOCALIZATION = "focalization"  # Violaciones de focalización/PDV
    STRUCTURE = "structure"  # Problemas estructurales
    WORLD = "world"  # Inconsistencias del mundo narrativo
    ENTITY = "entity"  # Problemas con entidades (fusión, detección)
    OTHER = "other"  # Otras alertas no categorizadas


class AlertSeverity(Enum):
    """Niveles de severidad de alertas."""

    CRITICAL = "critical"  # Debe corregirse (error evidente)
    WARNING = "warning"  # Debería revisarse (posible error)
    INFO = "info"  # Sugerencia (mejora recomendada)
    HINT = "hint"  # Opcional (sugerencia menor)


class AlertStatus(Enum):
    """Estados posibles de una alerta."""

    NEW = "new"  # Recién creada
    OPEN = "open"  # Vista por el usuario pero sin acción
    ACKNOWLEDGED = "acknowledged"  # Usuario vio y registró
    IN_PROGRESS = "in_progress"  # Usuario está trabajando en ella
    RESOLVED = "resolved"  # Usuario corrigió el problema
    DISMISSED = "dismissed"  # Usuario descartó (falso positivo)
    AUTO_RESOLVED = "auto_resolved"  # Se resolvió automáticamente


@dataclass
class Alert:
    """
    Alerta generada por un detector de inconsistencias.

    Representa un problema, inconsistencia o sugerencia detectada
    en el manuscrito.
    """

    # Identity
    id: int
    project_id: int

    # Clasificación
    category: AlertCategory
    severity: AlertSeverity
    alert_type: str  # Tipo específico del detector (ej: "attribute_inconsistency")

    # Contenido
    title: str  # Título breve (ej: "Color de ojos inconsistente")
    description: str  # Descripción corta (ej: "María: 'verdes' vs 'azules'")
    explanation: str  # Explicación detallada
    suggestion: Optional[str] = None  # Sugerencia de corrección

    # Ubicación en el manuscrito
    chapter: Optional[int] = None  # Número de capítulo (1-indexed)
    scene: Optional[int] = None  # Número de escena (1-indexed)
    start_char: Optional[int] = None  # Posición de inicio (0-indexed)
    end_char: Optional[int] = None  # Posición de fin (0-indexed)
    excerpt: str = ""  # Extracto del texto relevante

    # Entidades relacionadas
    entity_ids: list[int] = field(default_factory=list)

    # Metadata
    confidence: float = 0.8  # Confianza del detector (0.0-1.0)
    source_module: str = ""  # Módulo que generó la alerta
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    # Estado del ciclo de vida
    status: AlertStatus = AlertStatus.NEW
    resolved_at: Optional[datetime] = None
    resolution_note: str = ""  # Nota del usuario sobre la resolución

    # Datos adicionales específicos del tipo de alerta
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convierte la alerta a diccionario para persistencia."""
        data = asdict(self)
        # Convertir enums a strings
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        # Convertir datetimes a ISO format
        data["created_at"] = (
            self.created_at.isoformat() if self.created_at else None
        )
        data["updated_at"] = (
            self.updated_at.isoformat() if self.updated_at else None
        )
        data["resolved_at"] = (
            self.resolved_at.isoformat() if self.resolved_at else None
        )
        # Serializar extra_data como JSON
        data["extra_data"] = json.dumps(self.extra_data)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alert":
        """Crea una alerta desde un diccionario."""
        # Convertir strings a enums
        data["category"] = AlertCategory(data["category"])
        data["severity"] = AlertSeverity(data["severity"])
        data["status"] = AlertStatus(data["status"])
        # Convertir ISO strings a datetimes
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("resolved_at"):
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])
        # Deserializar extra_data desde JSON
        if isinstance(data.get("extra_data"), str):
            data["extra_data"] = json.loads(data["extra_data"])
        return cls(**data)

    def is_open(self) -> bool:
        """Retorna True si la alerta está abierta (no resuelta ni descartada)."""
        return self.status in [
            AlertStatus.NEW,
            AlertStatus.OPEN,
            AlertStatus.ACKNOWLEDGED,
            AlertStatus.IN_PROGRESS,
        ]

    def is_closed(self) -> bool:
        """Retorna True si la alerta está cerrada."""
        return self.status in [
            AlertStatus.RESOLVED,
            AlertStatus.DISMISSED,
            AlertStatus.AUTO_RESOLVED,
        ]


@dataclass
class AlertFilter:
    """
    Filtro para consultas de alertas.

    Permite filtrar por categoría, severidad, estado, ubicación, etc.
    """

    categories: Optional[list[AlertCategory]] = None
    severities: Optional[list[AlertSeverity]] = None
    statuses: Optional[list[AlertStatus]] = None
    chapters: Optional[list[int]] = None
    scenes: Optional[list[int]] = None
    entity_ids: Optional[list[int]] = None
    alert_types: Optional[list[str]] = None
    source_modules: Optional[list[str]] = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0

    def matches(self, alert: Alert) -> bool:
        """Verifica si una alerta cumple con los criterios del filtro."""
        if self.categories and alert.category not in self.categories:
            return False
        if self.severities and alert.severity not in self.severities:
            return False
        if self.statuses and alert.status not in self.statuses:
            return False
        if self.chapters and alert.chapter not in self.chapters:
            return False
        if self.scenes and alert.scene not in self.scenes:
            return False
        if self.entity_ids and not any(
            eid in self.entity_ids for eid in alert.entity_ids
        ):
            return False
        if self.alert_types and alert.alert_type not in self.alert_types:
            return False
        if self.source_modules and alert.source_module not in self.source_modules:
            return False
        if alert.confidence < self.min_confidence:
            return False
        if alert.confidence > self.max_confidence:
            return False
        return True
