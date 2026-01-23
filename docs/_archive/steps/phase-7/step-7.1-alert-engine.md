# STEP 7.1: Motor de Alertas Centralizado

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 0.3, STEP 2.4 |

---

## Descripción

Motor centralizado que recibe alertas de todos los módulos de análisis, las clasifica, prioriza y presenta al usuario de forma unificada.

---

## Inputs

- Alertas de todos los detectores:
  - Inconsistencias de atributos (STEP 2.4)
  - Repeticiones (STEPs 3.2, 3.3)
  - Inconsistencias temporales (STEP 4.3)
  - Desviaciones de voz (STEP 5.2)
  - Violaciones de focalización (STEP 6.2)

---

## Outputs

- `src/narrative_assistant/alerts/engine.py`
- Sistema unificado de alertas
- Priorización y clasificación
- Persistencia en base de datos
- API para UI

---

## Modelo de Datos

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class AlertCategory(Enum):
    CONSISTENCY = "consistency"      # Inconsistencias de atributos/tiempo
    STYLE = "style"                  # Repeticiones, voz
    FOCALIZATION = "focalization"    # Violaciones de focalización
    STRUCTURE = "structure"          # Problemas estructurales
    WORLD = "world"                  # Inconsistencias del mundo

class AlertSeverity(Enum):
    CRITICAL = "critical"  # Debe corregirse
    WARNING = "warning"    # Debería revisarse
    INFO = "info"          # Sugerencia
    HINT = "hint"          # Opcional

class AlertStatus(Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"  # Usuario vio pero no actuó
    RESOLVED = "resolved"          # Usuario corrigió
    DISMISSED = "dismissed"        # Usuario descartó (falso positivo)
    AUTO_RESOLVED = "auto_resolved"  # Se resolvió automáticamente

@dataclass
class Alert:
    id: int
    project_id: int

    # Clasificación
    category: AlertCategory
    severity: AlertSeverity
    alert_type: str  # Tipo específico del detector

    # Contenido
    title: str
    description: str
    explanation: str
    suggestion: Optional[str] = None

    # Ubicación
    chapter: Optional[int] = None
    scene: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    excerpt: str = ""

    # Entidades relacionadas
    entity_ids: List[int] = field(default_factory=list)

    # Metadata
    confidence: float = 0.8
    source_module: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # Estado
    status: AlertStatus = AlertStatus.OPEN
    resolved_at: Optional[datetime] = None
    resolution_note: str = ""

    # Datos adicionales específicos del tipo
    extra_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlertFilter:
    categories: Optional[List[AlertCategory]] = None
    severities: Optional[List[AlertSeverity]] = None
    statuses: Optional[List[AlertStatus]] = None
    chapters: Optional[List[int]] = None
    entity_ids: Optional[List[int]] = None
    min_confidence: float = 0.0
```

---

## Implementación

```python
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from collections import defaultdict

class AlertEngine:
    def __init__(self, repository: 'Repository'):
        self.repo = repository
        self.alert_handlers: Dict[str, Callable] = {}
        self._alert_counter = 0

    def register_handler(
        self,
        alert_type: str,
        handler: Callable[[Any], Alert]
    ) -> None:
        """Registra un handler para convertir resultados de detector a alertas."""
        self.alert_handlers[alert_type] = handler

    def create_alert(
        self,
        project_id: int,
        category: AlertCategory,
        severity: AlertSeverity,
        alert_type: str,
        title: str,
        description: str,
        explanation: str,
        **kwargs
    ) -> Alert:
        """Crea una nueva alerta."""
        self._alert_counter += 1

        alert = Alert(
            id=self._alert_counter,
            project_id=project_id,
            category=category,
            severity=severity,
            alert_type=alert_type,
            title=title,
            description=description,
            explanation=explanation,
            suggestion=kwargs.get('suggestion'),
            chapter=kwargs.get('chapter'),
            scene=kwargs.get('scene'),
            start_char=kwargs.get('start_char'),
            end_char=kwargs.get('end_char'),
            excerpt=kwargs.get('excerpt', ''),
            entity_ids=kwargs.get('entity_ids', []),
            confidence=kwargs.get('confidence', 0.8),
            source_module=kwargs.get('source_module', ''),
            extra_data=kwargs.get('extra_data', {})
        )

        return self.repo.save_alert(alert)

    def create_alerts_from_inconsistencies(
        self,
        project_id: int,
        inconsistencies: List['AttributeInconsistency']
    ) -> List[Alert]:
        """Convierte inconsistencias de atributos en alertas."""
        alerts = []

        for inc in inconsistencies:
            severity = self._calculate_severity_from_confidence(inc.confidence)

            alert = self.create_alert(
                project_id=project_id,
                category=AlertCategory.CONSISTENCY,
                severity=severity,
                alert_type="attribute_inconsistency",
                title=f"Inconsistencia en {inc.attribute_key}",
                description=f"{inc.entity_name}: '{inc.value1}' vs '{inc.value2}'",
                explanation=inc.explanation,
                suggestion=f"Verificar cuál es el valor correcto para {inc.attribute_key}",
                chapter=inc.value1_source.get('chapter'),
                entity_ids=[inc.entity_id],
                confidence=inc.confidence,
                source_module="attribute_consistency",
                extra_data={
                    'value1': inc.value1,
                    'value2': inc.value2,
                    'value1_source': inc.value1_source,
                    'value2_source': inc.value2_source,
                }
            )
            alerts.append(alert)

        return alerts

    def create_alerts_from_repetitions(
        self,
        project_id: int,
        repetitions: List['LexicalRepetition']
    ) -> List[Alert]:
        """Convierte repeticiones léxicas en alertas."""
        alerts = []

        severity_map = {
            'high': AlertSeverity.WARNING,
            'medium': AlertSeverity.INFO,
            'low': AlertSeverity.HINT,
        }

        for rep in repetitions:
            alert = self.create_alert(
                project_id=project_id,
                category=AlertCategory.STYLE,
                severity=severity_map.get(rep.severity, AlertSeverity.INFO),
                alert_type="lexical_repetition",
                title=f"Repetición: '{rep.word}'",
                description=f"Palabra repetida a {rep.distance_words} palabras de distancia",
                explanation=f"La palabra '{rep.word}' aparece dos veces muy cerca",
                suggestion="Considere usar un sinónimo o reformular",
                start_char=rep.positions[0] if rep.positions else None,
                end_char=rep.positions[-1] if rep.positions else None,
                excerpt=rep.context,
                source_module="lexical_repetitions",
                extra_data={
                    'word': rep.word,
                    'distance': rep.distance_words,
                    'positions': rep.positions,
                }
            )
            alerts.append(alert)

        return alerts

    def create_alerts_from_temporal(
        self,
        project_id: int,
        inconsistencies: List['TemporalInconsistency']
    ) -> List[Alert]:
        """Convierte inconsistencias temporales en alertas."""
        alerts = []

        severity_map = {
            'high': AlertSeverity.CRITICAL,
            'medium': AlertSeverity.WARNING,
            'low': AlertSeverity.INFO,
        }

        for inc in inconsistencies:
            alert = self.create_alert(
                project_id=project_id,
                category=AlertCategory.CONSISTENCY,
                severity=severity_map.get(inc.severity.value, AlertSeverity.WARNING),
                alert_type=f"temporal_{inc.inconsistency_type.value}",
                title=f"Inconsistencia temporal: {inc.inconsistency_type.value}",
                description=inc.description,
                explanation=inc.description,
                suggestion=inc.suggestion,
                entity_ids=[inc.entity_id] if inc.entity_id else [],
                confidence=inc.confidence,
                source_module="temporal_inconsistencies",
                extra_data={
                    'type': inc.inconsistency_type.value,
                    'evidence': inc.evidence,
                }
            )
            alerts.append(alert)

        return alerts

    def create_alerts_from_voice_deviations(
        self,
        project_id: int,
        deviations: List['VoiceDeviation']
    ) -> List[Alert]:
        """Convierte desviaciones de voz en alertas."""
        alerts = []

        for dev in deviations:
            severity = self._severity_from_score(dev.deviation_score)

            alert = self.create_alert(
                project_id=project_id,
                category=AlertCategory.STYLE,
                severity=severity,
                alert_type=f"voice_{dev.deviation_type.value}",
                title=f"Desviación de voz: {dev.entity_name}",
                description=dev.explanation,
                explanation=f"Esperado: {dev.expected_value}. Encontrado: {dev.found_value}",
                suggestion=dev.suggestion,
                chapter=dev.chapter,
                start_char=dev.position,
                entity_ids=[dev.entity_id],
                confidence=dev.deviation_score,
                source_module="voice_deviations",
                extra_data={
                    'deviation_type': dev.deviation_type.value,
                    'expected': dev.expected_value,
                    'found': dev.found_value,
                }
            )
            alerts.append(alert)

        return alerts

    def create_alerts_from_focalization(
        self,
        project_id: int,
        violations: List['FocalizationViolation']
    ) -> List[Alert]:
        """Convierte violaciones de focalización en alertas."""
        alerts = []

        severity_map = {
            'high': AlertSeverity.CRITICAL,
            'medium': AlertSeverity.WARNING,
            'low': AlertSeverity.INFO,
        }

        for viol in violations:
            alert = self.create_alert(
                project_id=project_id,
                category=AlertCategory.FOCALIZATION,
                severity=severity_map.get(viol.severity.value, AlertSeverity.WARNING),
                alert_type=f"focalization_{viol.violation_type.value}",
                title=f"Violación de focalización: {viol.violation_type.value}",
                description=viol.explanation,
                explanation=f"Focalizador declarado: {viol.declared_focalizer}",
                suggestion=viol.suggestion,
                chapter=viol.chapter,
                scene=viol.scene,
                start_char=viol.position,
                excerpt=viol.text_excerpt,
                entity_ids=[viol.entity_involved] if viol.entity_involved else [],
                confidence=viol.confidence,
                source_module="focalization_violations",
                extra_data={
                    'violation_type': viol.violation_type.value,
                    'declared_focalizer': viol.declared_focalizer,
                }
            )
            alerts.append(alert)

        return alerts

    def _calculate_severity_from_confidence(self, confidence: float) -> AlertSeverity:
        """Calcula severidad basada en confianza."""
        if confidence >= 0.9:
            return AlertSeverity.CRITICAL
        elif confidence >= 0.7:
            return AlertSeverity.WARNING
        elif confidence >= 0.5:
            return AlertSeverity.INFO
        else:
            return AlertSeverity.HINT

    def _severity_from_score(self, score: float) -> AlertSeverity:
        """Convierte score de desviación a severidad."""
        if score >= 0.8:
            return AlertSeverity.WARNING
        elif score >= 0.5:
            return AlertSeverity.INFO
        else:
            return AlertSeverity.HINT

    # --- Gestión de alertas ---

    def get_alerts(
        self,
        project_id: int,
        filter: Optional[AlertFilter] = None
    ) -> List[Alert]:
        """Obtiene alertas con filtros opcionales."""
        alerts = self.repo.get_alerts(project_id)

        if not filter:
            return alerts

        # Aplicar filtros
        if filter.categories:
            alerts = [a for a in alerts if a.category in filter.categories]
        if filter.severities:
            alerts = [a for a in alerts if a.severity in filter.severities]
        if filter.statuses:
            alerts = [a for a in alerts if a.status in filter.statuses]
        if filter.chapters:
            alerts = [a for a in alerts if a.chapter in filter.chapters]
        if filter.entity_ids:
            alerts = [a for a in alerts
                     if any(eid in filter.entity_ids for eid in a.entity_ids)]
        if filter.min_confidence > 0:
            alerts = [a for a in alerts if a.confidence >= filter.min_confidence]

        return alerts

    def update_alert_status(
        self,
        alert_id: int,
        status: AlertStatus,
        note: str = ""
    ) -> Alert:
        """Actualiza el estado de una alerta."""
        alert = self.repo.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.status = status
        if status in [AlertStatus.RESOLVED, AlertStatus.DISMISSED]:
            alert.resolved_at = datetime.now()
        alert.resolution_note = note

        return self.repo.save_alert(alert)

    def get_summary(self, project_id: int) -> Dict[str, Any]:
        """Genera resumen de alertas del proyecto."""
        alerts = self.repo.get_alerts(project_id)

        summary = {
            'total': len(alerts),
            'open': sum(1 for a in alerts if a.status == AlertStatus.OPEN),
            'by_category': defaultdict(int),
            'by_severity': defaultdict(int),
            'by_chapter': defaultdict(int),
        }

        for alert in alerts:
            summary['by_category'][alert.category.value] += 1
            summary['by_severity'][alert.severity.value] += 1
            if alert.chapter:
                summary['by_chapter'][alert.chapter] += 1

        return dict(summary)

    def prioritize_alerts(
        self,
        alerts: List[Alert]
    ) -> List[Alert]:
        """Ordena alertas por prioridad."""
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.INFO: 2,
            AlertSeverity.HINT: 3,
        }

        return sorted(alerts, key=lambda a: (
            severity_order.get(a.severity, 4),
            -a.confidence,
            a.chapter or 0
        ))
```

---

## Criterio de DONE

```python
from narrative_assistant.alerts import (
    AlertEngine,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertFilter
)

# Mock repository
class MockRepo:
    def __init__(self):
        self.alerts = {}

    def save_alert(self, alert):
        self.alerts[alert.id] = alert
        return alert

    def get_alerts(self, project_id):
        return [a for a in self.alerts.values() if a.project_id == project_id]

    def get_alert(self, alert_id):
        return self.alerts.get(alert_id)

engine = AlertEngine(MockRepo())

# Crear alertas de prueba
alert1 = engine.create_alert(
    project_id=1,
    category=AlertCategory.CONSISTENCY,
    severity=AlertSeverity.CRITICAL,
    alert_type="attribute_inconsistency",
    title="Color de ojos inconsistente",
    description="María: 'verdes' vs 'azules'",
    explanation="El color de ojos cambia entre capítulos",
    suggestion="Verificar cuál es el color correcto",
    chapter=2,
    entity_ids=[1],
    confidence=0.95
)

alert2 = engine.create_alert(
    project_id=1,
    category=AlertCategory.STYLE,
    severity=AlertSeverity.INFO,
    alert_type="lexical_repetition",
    title="Repetición: 'sendero'",
    description="Palabra repetida 3 veces en 50 palabras",
    explanation="Considerar sinónimos",
    chapter=3,
    confidence=0.7
)

# Verificar creación
assert alert1.id == 1
assert alert2.id == 2

# Filtrar alertas
filter = AlertFilter(severities=[AlertSeverity.CRITICAL])
critical_alerts = engine.get_alerts(1, filter)
assert len(critical_alerts) == 1

# Actualizar estado
engine.update_alert_status(1, AlertStatus.RESOLVED, "Corregido a 'verdes'")
resolved = engine.repo.get_alert(1)
assert resolved.status == AlertStatus.RESOLVED

# Obtener resumen
summary = engine.get_summary(1)
assert summary['total'] == 2
assert summary['open'] == 1  # Solo alert2 sigue abierta

print(f"✅ Motor de alertas funcionando")
print(f"   Total alertas: {summary['total']}")
print(f"   Abiertas: {summary['open']}")
```

---

## Siguiente

[STEP 7.2: Fichas de Personaje](./step-7.2-character-sheets.md)
