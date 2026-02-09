"""
Modelos de datos para el sistema de alertas.

Representa alertas generadas por diferentes detectores de inconsistencias.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlertCategory(Enum):
    """Categorías de alertas."""

    CONSISTENCY = "consistency"  # Inconsistencias de atributos/tiempo
    STYLE = "style"  # Repeticiones, voz, estilo narrativo
    BEHAVIORAL = "behavioral"  # Inconsistencias de comportamiento de personajes
    FOCALIZATION = "focalization"  # Violaciones de focalización/PDV
    STRUCTURE = "structure"  # Problemas estructurales
    WORLD = "world"  # Inconsistencias del mundo narrativo
    ENTITY = "entity"  # Problemas con entidades (fusión, detección)
    ORTHOGRAPHY = "orthography"  # Errores ortográficos
    GRAMMAR = "grammar"  # Errores gramaticales
    TIMELINE_ISSUE = "timeline"  # Inconsistencias temporales (timeline)
    CHARACTER_CONSISTENCY = "character_consistency"  # Inconsistencias de personajes (edades, etc.)
    VOICE_DEVIATION = "voice_deviation"  # Desviaciones de voz/registro de personajes
    EMOTIONAL = "emotional"  # Incoherencias emocionales (emoción vs diálogo/acción)
    # Nuevas categorías de corrección editorial
    TYPOGRAPHY = "typography"  # Errores tipográficos (comillas, espacios)
    PUNCTUATION = "punctuation"  # Puntuación (raya de diálogo, puntos suspensivos)
    REPETITION = "repetition"  # Repeticiones léxicas cercanas
    AGREEMENT = "agreement"  # Concordancia gramatical (género, número)
    DIALOGUE = "dialogue"  # Problemas de diálogos (huérfanos, atribución, contexto)
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
    suggestion: str | None = None  # Sugerencia de corrección

    # Ubicación en el manuscrito
    chapter: int | None = None  # Número de capítulo (1-indexed)
    scene: int | None = None  # Número de escena (1-indexed)
    start_char: int | None = None  # Posición de inicio (0-indexed)
    end_char: int | None = None  # Posición de fin (0-indexed)
    excerpt: str = ""  # Extracto del texto relevante

    # Entidades relacionadas
    entity_ids: list[int] = field(default_factory=list)

    # Metadata
    confidence: float = 0.8  # Confianza del detector (0.0-1.0)
    source_module: str = ""  # Módulo que generó la alerta
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime | None = None

    # Estado del ciclo de vida
    status: AlertStatus = AlertStatus.NEW
    resolved_at: datetime | None = None
    resolution_note: str = ""  # Nota del usuario sobre la resolución

    # Datos adicionales específicos del tipo de alerta
    extra_data: dict[str, Any] = field(default_factory=dict)

    # Hash de contenido para identificar "misma alerta" entre re-análisis
    content_hash: str = ""

    def __post_init__(self):
        """Calcula content_hash si no se proporcionó."""
        if not self.content_hash:
            self.content_hash = self.compute_content_hash()

    def compute_content_hash(self) -> str:
        """
        Calcula hash determinista basado en el contenido semántico de la alerta.

        Permite identificar la "misma" alerta entre re-análisis sucesivos,
        incluso cuando el ID de la alerta cambia.

        El hash se basa en:
        - project_id: Agrupar por proyecto
        - alert_type: Tipo de detector (attribute_inconsistency, spelling_typo, etc.)
        - entity_ids: Entidades afectadas (ordenadas para determinismo)
        - chapter: Capítulo donde ocurre
        - key content: Campos clave según el tipo de alerta

        Returns:
            SHA-256 hex digest truncado a 16 chars
        """
        # Componentes principales (siempre presentes)
        parts = [
            str(self.project_id),
            self.alert_type,
            str(sorted(self.entity_ids)),
            str(self.chapter or 0),
        ]

        # Componentes de contenido específicos del tipo de alerta
        if self.alert_type == "attribute_inconsistency":
            # Para inconsistencias de atributos: entidad + atributo + valores
            ed = self.extra_data
            parts.extend(
                [
                    ed.get("entity_name", ""),
                    ed.get("attribute_key", ""),
                    str(sorted([ed.get("value1", ""), ed.get("value2", "")])),
                ]
            )
        elif self.alert_type.startswith("spelling_"):
            # Para ortografía: palabra + posición aproximada
            ed = self.extra_data
            parts.append(ed.get("word", ""))
            parts.append(str(self.start_char or 0))
        elif self.alert_type.startswith("grammar_"):
            # Para gramática: texto + tipo de error
            ed = self.extra_data
            parts.append(ed.get("text", ""))
            parts.append(ed.get("error_type", ""))
        elif self.alert_type == "entity_name_variant":
            ed = self.extra_data
            parts.extend(
                [
                    ed.get("canonical_form", ""),
                    ed.get("variant_form", ""),
                ]
            )
        elif self.alert_type == "deceased_reappearance":
            ed = self.extra_data
            parts.extend(
                [
                    ed.get("entity_name", ""),
                    str(ed.get("death_chapter", 0)),
                    str(ed.get("appearance_chapter", 0)),
                ]
            )
        else:
            # Para otros tipos: título + descripción (primeros 100 chars)
            parts.append(self.title[:100])
            parts.append(self.description[:100])

        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convierte la alerta a diccionario para persistencia."""
        data = asdict(self)
        # Convertir enums a strings
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        # Convertir datetimes a ISO format
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        data["resolved_at"] = self.resolved_at.isoformat() if self.resolved_at else None
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

    categories: list[AlertCategory] | None = None
    severities: list[AlertSeverity] | None = None
    statuses: list[AlertStatus] | None = None
    chapters: list[int] | None = None
    scenes: list[int] | None = None
    entity_ids: list[int] | None = None
    alert_types: list[str] | None = None
    source_modules: list[str] | None = None
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
        if self.entity_ids and not any(eid in self.entity_ids for eid in alert.entity_ids):
            return False
        if self.alert_types and alert.alert_type not in self.alert_types:
            return False
        if self.source_modules and alert.source_module not in self.source_modules:
            return False
        if alert.confidence < self.min_confidence:
            return False
        return not alert.confidence > self.max_confidence
