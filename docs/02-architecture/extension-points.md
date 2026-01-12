# Puntos de Extensión

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

El sistema está diseñado para ser extensible. Nuevas heurísticas y capacidades pueden añadirse sin modificar el núcleo.

---

## Añadir Nueva Heurística

### 1. Definir el tipo de alerta

Añadir en `alert_types.py`:

```python
ALERT_TYPES = {
    # Existentes
    'attribute_inconsistency': {...},
    'name_variant': {...},

    # Nueva heurística
    'my_new_check': {
        'name': 'Mi nueva verificación',
        'description': 'Detecta X problema',
        'severity_default': 'medium',
        'configurable': True,
        'family': 'H1'  # Familia de heurísticas
    }
}
```

### 2. Implementar el detector

Crear en `alerts/my_new_check.py`:

```python
from dataclasses import dataclass
from typing import List
from ..models import Alert, Entity, TextReference

@dataclass
class MyNewCheckResult:
    alerts: List[Alert]
    stats: dict

def detect_my_new_issue(
    entities: List[Entity],
    text: str,
    config: dict
) -> MyNewCheckResult:
    """
    Detecta el problema X en el texto.

    Args:
        entities: Entidades extraídas
        text: Texto completo del documento
        config: Configuración del usuario

    Returns:
        MyNewCheckResult con alertas y estadísticas
    """
    alerts = []

    # Lógica de detección...
    for entity in entities:
        if has_issue(entity, text):
            alerts.append(Alert(
                alert_type='my_new_check',
                severity='medium',
                confidence=calculate_confidence(...),
                title=f"Problema detectado en {entity.canonical_name}",
                description="...",
                source_references=[...],
                related_entity_ids=[entity.id]
            ))

    return MyNewCheckResult(
        alerts=alerts,
        stats={'issues_found': len(alerts)}
    )
```

### 3. Registrar en el motor de alertas

En `alerts/engine.py`:

```python
from .my_new_check import detect_my_new_issue

class AlertEngine:
    def __init__(self):
        self.detectors = {
            'attribute_inconsistency': detect_attribute_inconsistencies,
            'name_variant': detect_name_variants,
            'my_new_check': detect_my_new_issue,  # Nueva
        }

    def run_all(self, project) -> List[Alert]:
        all_alerts = []
        for detector_name, detector_fn in self.detectors.items():
            if self.is_enabled(detector_name):
                result = detector_fn(
                    project.entities,
                    project.text,
                    project.config
                )
                all_alerts.extend(result.alerts)
        return all_alerts
```

### 4. Añadir configuración

En `config/defaults.py`:

```python
DEFAULT_CONFIG = {
    'thresholds': {
        # Existentes...
        'my_new_check': {
            'enabled': True,
            'min_confidence': 0.5,
            'severity_override': None
        }
    }
}
```

---

## Añadir Nuevo Tipo de Entidad

### 1. Actualizar el schema

```sql
-- Añadir nuevo tipo válido
-- En la definición de entity_type CHECK:
CHECK(entity_type IN (
    'character', 'location', 'object', 'organization', 'event',
    'my_new_type'  -- Nuevo
))
```

### 2. Crear extractor

```python
# En nlp/extractors/my_new_type.py

def extract_my_new_type(doc) -> List[Entity]:
    """Extrae entidades de tipo X del documento."""
    entities = []
    # Lógica de extracción...
    return entities
```

### 3. Registrar en pipeline

```python
# En nlp/pipeline.py

class NLPPipeline:
    def __init__(self):
        self.extractors = {
            'character': extract_characters,
            'location': extract_locations,
            'my_new_type': extract_my_new_type,  # Nuevo
        }
```

---

## Añadir Nuevo Formato de Exportación

### 1. Implementar exportador

```python
# En export/my_format.py

def export_to_my_format(project, output_path: Path):
    """Exporta el proyecto a formato X."""
    data = gather_export_data(project)

    with open(output_path, 'w') as f:
        # Escribir en formato deseado
        ...

    return output_path
```

### 2. Registrar en CLI

```python
# En cli.py

@app.command()
def export(
    project_db: Path,
    output: Path,
    format: str = typer.Option("json", help="Formato: json, md, pdf, my_format")
):
    exporters = {
        'json': export_to_json,
        'md': export_to_markdown,
        'pdf': export_to_pdf,
        'my_format': export_to_my_format,  # Nuevo
    }

    exporter = exporters.get(format)
    if not exporter:
        raise ValueError(f"Formato no soportado: {format}")

    exporter(project, output)
```

---

## Añadir Nuevo Modelo NLP

### 1. Crear adapter

```python
# En nlp/models/my_model.py

from abc import ABC, abstractmethod

class NERModel(ABC):
    @abstractmethod
    def extract_entities(self, text: str) -> List[Entity]:
        pass

class MyCustomModel(NERModel):
    def __init__(self, model_path: str):
        self.model = load_model(model_path)

    def extract_entities(self, text: str) -> List[Entity]:
        # Usar modelo personalizado
        results = self.model.predict(text)
        return convert_to_entities(results)
```

### 2. Configurar como opción

```python
# En config/models.py

MODEL_CONFIGS = {
    'default': {
        'ner': 'spacy:es_core_news_lg',
        'coref': 'coreferee',
        'embeddings': 'sentence-transformers:paraphrase-multilingual-MiniLM-L12-v2'
    },
    'custom': {
        'ner': 'custom:path/to/my_model',
        'coref': 'coreferee',
        'embeddings': 'custom:path/to/embeddings'
    }
}
```

---

## Plugins (Futuro)

El sistema contempla soporte para plugins externos en fases posteriores:

```python
# Estructura de plugin propuesta

my_plugin/
├── __init__.py
├── plugin.yaml       # Metadata
├── detectors/        # Nuevos detectores de alertas
├── extractors/       # Nuevos extractores de entidades
└── exporters/        # Nuevos formatos de exportación
```

```yaml
# plugin.yaml
name: my-narrative-plugin
version: 1.0.0
author: Author Name
description: Añade detección de X

provides:
  detectors:
    - my_custom_detector
  extractors:
    - my_entity_type
  exporters:
    - my_format

requires:
  narrative-assistant: ">=1.0.0"
```

---

## Hooks de Evento

El sistema emite eventos que pueden interceptarse:

```python
# En core/events.py

class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_name: str, callback):
        self.listeners[event_name].append(callback)

    def emit(self, event_name: str, data):
        for callback in self.listeners[event_name]:
            callback(data)

# Eventos disponibles
EVENTS = [
    'project.created',
    'project.imported',
    'analysis.started',
    'analysis.completed',
    'entity.created',
    'entity.merged',
    'alert.created',
    'alert.resolved',
    'export.completed'
]

# Uso
bus = EventBus()
bus.on('alert.created', lambda alert: send_notification(alert))
```

---

## Volver

[← Arquitectura](./README.md)
