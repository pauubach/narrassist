# Backend - Alerts Module

Ubicación: `src/narrative_assistant/alerts/`

## Models (`models.py`)

### Enum `AlertCategory`

| Valor | Descripción |
|-------|-------------|
| `CONSISTENCY` | Inconsistencias de atributos/tiempo |
| `STYLE` | Repeticiones, voz, estilo narrativo |
| `FOCALIZATION` | Violaciones de focalización/PDV |
| `STRUCTURE` | Problemas estructurales |
| `WORLD` | Inconsistencias del mundo narrativo |
| `ENTITY` | Problemas con entidades |
| `OTHER` | Otras alertas |

### Enum `AlertSeverity`

| Valor | Descripción |
|-------|-------------|
| `CRITICAL` | Debe corregirse (error evidente) |
| `WARNING` | Debería revisarse (posible error) |
| `INFO` | Sugerencia (mejora recomendada) |
| `HINT` | Opcional (sugerencia menor) |

### Enum `AlertStatus`

| Valor | Descripción |
|-------|-------------|
| `NEW` | Recién creada |
| `OPEN` | Vista pero sin acción |
| `ACKNOWLEDGED` | Usuario registró |
| `IN_PROGRESS` | Usuario trabajando |
| `RESOLVED` | Usuario corrigió |
| `DISMISSED` | Usuario descartó (falso positivo) |
| `AUTO_RESOLVED` | Se resolvió automáticamente |

### Dataclass `Alert`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int` | ID de la alerta |
| `project_id` | `int` | ID del proyecto |
| `category` | `AlertCategory` | Categoría |
| `severity` | `AlertSeverity` | Severidad |
| `alert_type` | `str` | Tipo específico (ej: "attribute_inconsistency") |
| `title` | `str` | Título breve |
| `description` | `str` | Descripción corta |
| `explanation` | `str` | Explicación detallada |
| `suggestion` | `Optional[str]` | Sugerencia de corrección |
| `chapter` | `Optional[int]` | Número de capítulo (1-indexed) |
| `scene` | `Optional[int]` | Número de escena (1-indexed) |
| `start_char` | `Optional[int]` | Posición de inicio (0-indexed) |
| `end_char` | `Optional[int]` | Posición de fin (0-indexed) |
| `excerpt` | `str` | Extracto del texto |
| `entity_ids` | `list[int]` | IDs de entidades relacionadas |
| `confidence` | `float` | Confianza del detector (0.0-1.0) |
| `source_module` | `str` | Módulo que generó la alerta |
| `created_at` | `datetime` | Fecha creación |
| `updated_at` | `Optional[datetime]` | Última modificación |
| `status` | `AlertStatus` | Estado actual |
| `resolved_at` | `Optional[datetime]` | Fecha de resolución |
| `resolution_note` | `str` | Nota sobre la resolución |
| `extra_data` | `dict[str, Any]` | Datos adicionales |

| Método | Firma | Retorno |
|--------|-------|---------|
| `to_dict` | `() -> dict[str, Any]` | Diccionario para persistencia |
| `from_dict` | `@classmethod (data: dict) -> Alert` | Alerta desde dict |
| `is_open` | `() -> bool` | True si no resuelta/descartada |
| `is_closed` | `() -> bool` | True si resuelta/descartada |

### Dataclass `AlertFilter`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `categories` | `Optional[list[AlertCategory]]` | Filtrar por categorías |
| `severities` | `Optional[list[AlertSeverity]]` | Filtrar por severidades |
| `statuses` | `Optional[list[AlertStatus]]` | Filtrar por estados |
| `chapters` | `Optional[list[int]]` | Filtrar por capítulos |
| `scenes` | `Optional[list[int]]` | Filtrar por escenas |
| `entity_ids` | `Optional[list[int]]` | Filtrar por entidades |
| `alert_types` | `Optional[list[str]]` | Filtrar por tipos |
| `source_modules` | `Optional[list[str]]` | Filtrar por módulos |
| `min_confidence` | `float` | Confianza mínima (default: 0.0) |
| `max_confidence` | `float` | Confianza máxima (default: 1.0) |

| Método | Firma | Retorno |
|--------|-------|---------|
| `matches` | `(alert: Alert) -> bool` | True si la alerta cumple |

---

## Repository (`repository.py`)

### Clase `AlertRepository`

```python
from narrative_assistant.alerts.repository import get_alert_repository

repo = get_alert_repository()  # Singleton
```

#### Métodos CRUD

| Método | Firma | Retorno |
|--------|-------|---------|
| `create` | `(alert: Alert) -> Result[Alert]` | Alerta creada con ID |
| `get` | `(alert_id: int) -> Result[Alert]` | Alerta encontrada |
| `get_by_project` | `(project_id: int) -> Result[list[Alert]]` | Alertas del proyecto |
| `update` | `(alert: Alert) -> Result[Alert]` | Alerta actualizada |
| `delete` | `(alert_id: int) -> Result[None]` | Éxito/fallo |

#### Métodos de Estadísticas

| Método | Firma | Retorno |
|--------|-------|---------|
| `count_by_status` | `(project_id: int) -> Result[dict[str, int]]` | Conteo por estado |

### Factory Function

```python
from narrative_assistant.alerts.repository import get_alert_repository

repo = get_alert_repository()  # Singleton
```

| Función | Firma |
|---------|-------|
| `get_alert_repository` | `() -> AlertRepository` |

---

## Errores Comunes

### Error: `'AlertRepository' object has no attribute 'get_alerts'`

**Incorrecto:**
```python
alerts = repo.get_alerts(project_id)
```

**Correcto:**
```python
result = repo.get_by_project(project_id)
if result.is_success:
    alerts = result.value
```

### Error: `'AlertRepository' object has no attribute 'find'`

**Incorrecto:**
```python
alert = repo.find(alert_id)
```

**Correcto:**
```python
result = repo.get(alert_id)
if result.is_success:
    alert = result.value
```

### Error: `'AlertRepository' object has no attribute 'create_alert'`

**Incorrecto:**
```python
repo.create_alert(project_id=1, title="...", ...)
```

**Correcto:**
```python
alert = Alert(
    id=0,  # Se asignará al crear
    project_id=1,
    category=AlertCategory.CONSISTENCY,
    severity=AlertSeverity.WARNING,
    alert_type="attribute_inconsistency",
    title="Color de ojos inconsistente",
    description="María: 'verdes' vs 'azules'",
    explanation="Se detectaron valores diferentes...",
)
result = repo.create(alert)
```

### Error: Resultado no manejado

**Incorrecto:**
```python
alerts = repo.get_by_project(project_id)  # Esto es un Result, no una lista
for alert in alerts:  # Error!
    print(alert.title)
```

**Correcto:**
```python
result = repo.get_by_project(project_id)
if result.is_success:
    for alert in result.value:
        print(alert.title)
else:
    print(f"Error: {result.error}")
```
