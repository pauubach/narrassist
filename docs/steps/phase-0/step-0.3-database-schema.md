# STEP 0.3: Schema de Base de Datos

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 0.2 |

---

## Descripción

Implementar el schema SQLite completo para persistencia del modelo de datos narrativo.

---

## Inputs

- Modelo de datos de la [documentación de arquitectura](../../02-architecture/data-model.md)

---

## Outputs

- `src/narrative_assistant/db/schema.sql`
- `src/narrative_assistant/db/models.py` (dataclasses)
- Tests de migración

---

## Implementación

### schema.sql

Ver el schema completo en [Database Schema](../../02-architecture/database-schema.md).

Tablas principales:
- `project` - Proyecto y configuración
- `document_version` - Versiones del documento
- `chapter` - Capítulos
- `scene` - Escenas
- `entity` - Entidades (personajes, lugares, etc.)
- `text_reference` - Referencias al texto
- `attribute` - Atributos de entidades
- `relationship` - Relaciones entre entidades
- `dialogue` - Diálogos detectados
- `voice_profile` - Perfiles de voz
- `event` - Eventos temporales
- `alert` - Alertas generadas
- `note` - Notas del corrector
- `user_decision` - Decisiones del usuario
- `merge_history` - Historial de fusiones

### models.py

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import json

@dataclass
class Project:
    id: int
    name: str
    language: str = "es"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    settings: dict = field(default_factory=dict)

@dataclass
class Entity:
    id: int
    project_id: int
    entity_type: str  # 'character', 'location', 'object', 'organization', 'event'
    canonical_name: str
    aliases: List[str] = field(default_factory=list)
    importance: str = "secondary"
    first_chapter: Optional[int] = None
    last_chapter: Optional[int] = None
    validated_by_user: bool = False

@dataclass
class TextReference:
    id: int
    entity_id: int
    chapter_id: Optional[int]
    start_char: int
    end_char: int
    surface_form: str
    detection_method: str = "ner"
    confidence: float = 1.0

@dataclass
class Attribute:
    id: int
    entity_id: int
    attribute_type: str  # 'physical', 'psychological', 'social', 'background'
    attribute_key: str
    value: str
    normalized_value: Optional[str] = None
    source_chapter: Optional[int] = None
    source_excerpt: Optional[str] = None
    confidence: float = 1.0
    validated_by_user: bool = False

@dataclass
class Alert:
    id: int
    project_id: int
    alert_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    confidence: float
    title: str
    description: str
    source_references: List[dict] = field(default_factory=list)
    related_entity_ids: List[int] = field(default_factory=list)
    status: str = "pending"
    resolution_note: Optional[str] = None
```

### repository.py

```python
import sqlite3
from pathlib import Path
from typing import List, Optional
from .models import Project, Entity, Alert

class Repository:
    def __init__(self, db_path: str = "data/project.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Inicializa la base de datos si no existe."""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open("src/narrative_assistant/db/schema.sql") as f:
                schema = f.read()
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema)

    def create_project(self, name: str, language: str = "es") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO project (name, language) VALUES (?, ?)",
                (name, language)
            )
            return cursor.lastrowid

    def get_entities(self, project_id: int) -> List[Entity]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM entity WHERE project_id = ?",
                (project_id,)
            )
            return [Entity(**dict(row)) for row in cursor.fetchall()]

    def create_alert(self, alert: Alert) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO alert (
                    project_id, alert_type, severity, confidence,
                    title, description, source_references, related_entity_ids, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.project_id, alert.alert_type, alert.severity,
                alert.confidence, alert.title, alert.description,
                json.dumps(alert.source_references),
                json.dumps(alert.related_entity_ids),
                alert.status
            ))
            return cursor.lastrowid
```

---

## Criterio de DONE

```python
from narrative_assistant.db import Repository

repo = Repository("test.db")
project_id = repo.create_project("Test Novel", "es")
entities = repo.get_entities(project_id)
assert entities == []  # Vacío inicialmente
print("✅ Base de datos funcional")
```

---

## Siguiente

[STEP 1.1: Parser DOCX](../phase-1/step-1.1-docx-parser.md)
