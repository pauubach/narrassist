# Backend - Persistence Module

Ubicación: `src/narrative_assistant/persistence/`

## Database (`database.py`)

### Clase `Database`

| Método | Firma | Descripción |
|--------|-------|-------------|
| `__init__` | `(db_path: Optional[Path] = None)` | Constructor |
| `connection` | `() -> Iterator[sqlite3.Connection]` | Context manager para conexión |
| `transaction` | `() -> Iterator[sqlite3.Connection]` | Context manager con transacción |
| `execute` | `(sql: str, params: tuple = ()) -> sqlite3.Cursor` | Ejecuta SQL |
| `executemany` | `(sql: str, params_list: list[tuple]) -> sqlite3.Cursor` | Ejecuta SQL múltiples veces |
| `fetchone` | `(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]` | Obtiene una fila |
| `fetchall` | `(sql: str, params: tuple = ()) -> list[sqlite3.Row]` | Obtiene todas las filas |
| `get_schema_version` | `() -> int` | Versión del esquema |

### Factory Function

```python
from narrative_assistant.persistence.database import get_database

db = get_database()  # Singleton
db = get_database(custom_path)  # Con path específico
```

| Función | Firma |
|---------|-------|
| `get_database` | `(db_path: Optional[Path] = None) -> Database` |
| `reset_database` | `() -> None` |

---

## Project (`project.py`)

### Dataclass `Project`

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `id` | `Optional[int]` | `None` | ID del proyecto |
| `name` | `str` | `""` | Nombre |
| `description` | `str` | `""` | Descripción |
| `document_path` | `Optional[str]` | `None` | Ruta al documento |
| `document_fingerprint` | `str` | `""` | Fingerprint (hash + n-gram) |
| `document_format` | `str` | `""` | Formato (DOCX, TXT, etc.) |
| `word_count` | `int` | `0` | Conteo de palabras |
| `chapter_count` | `int` | `0` | Número de capítulos |
| `created_at` | `Optional[datetime]` | `None` | Fecha creación |
| `updated_at` | `Optional[datetime]` | `None` | Última modificación |
| `last_opened_at` | `Optional[datetime]` | `None` | Última apertura |
| `analysis_status` | `str` | `"pending"` | Estado: pending, analyzing, completed, error |
| `analysis_progress` | `float` | `0.0` | Progreso 0.0-1.0 |
| `settings` | `dict[str, Any]` | `{}` | Configuración específica del proyecto |

### Clase `ProjectManager`

| Método | Firma | Retorno |
|--------|-------|---------|
| `__init__` | `(db: Optional[Database] = None)` | - |
| `create_from_document` | `(text: str, name: str, document_format: str, document_path: Optional[Path] = None, description: str = "", check_existing: bool = True) -> Result[Project]` | Proyecto con fingerprint |
| `get` | `(project_id: int) -> Result[Project]` | Proyecto o error |
| `get_by_fingerprint` | `(fingerprint: str) -> Optional[Project]` | Proyecto existente |
| `list_all` | `(limit: int = 100, offset: int = 0) -> list[Project]` | Lista de proyectos |
| `update` | `(project: Project) -> Result[Project]` | Proyecto actualizado |
| `delete` | `(project_id: int) -> Result[bool]` | Éxito/error |
| `find_similar` | `(text: str) -> Optional[Project]` | Proyecto similar |

**Nota**: NO existe un método `create(project: Project)`. Para crear proyectos, usar `create_from_document()`.

---

## Chapter (`chapter.py`)

### Dataclass `ChapterData`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `Optional[int]` | ID del capítulo |
| `project_id` | `int` | ID del proyecto |
| `chapter_number` | `int` | Número de capítulo |
| `title` | `Optional[str]` | Título |
| `content` | `str` | Contenido del texto |
| `start_char` | `int` | Posición inicial |
| `end_char` | `int` | Posición final |
| `word_count` | `int` | Conteo de palabras |
| `structure_type` | `str` | Tipo: chapter, prologue, epilogue (default: "chapter") |
| `created_at` | `Optional[str]` | Fecha creación (ISO format string) |
| `updated_at` | `Optional[str]` | Última modificación (ISO format string) |

### Clase `ChapterRepository`

| Método | Firma | Retorno |
|--------|-------|---------|
| `__init__` | `(db: Optional[Database] = None)` | - |
| `create` | `(chapter: ChapterData) -> ChapterData` | Capítulo creado con ID |
| `create_many` | `(chapters: list[ChapterData]) -> list[ChapterData]` | Capítulos creados |
| `get_by_id` | `(chapter_id: int) -> Optional[ChapterData]` | Capítulo o None |
| `get_by_project` | `(project_id: int) -> list[ChapterData]` | Lista de capítulos |
| `update_content` | `(chapter_id: int, content: str, word_count: int) -> bool` | True si actualizó |
| `delete_by_project` | `(project_id: int) -> int` | Número eliminados |

**Nota**: `create()` retorna `ChapterData` directamente (no `Result`). Para eliminar un capítulo individual, usar `delete_by_project()` con el project_id.

### Factory Function

```python
from narrative_assistant.persistence.chapter import get_chapter_repository

repo = get_chapter_repository()
```

| Función | Firma |
|---------|-------|
| `get_chapter_repository` | `(db: Optional[Database] = None) -> ChapterRepository` |

---

## Session (`session.py`)

### Enum `AlertAction`

| Valor | Descripción |
|-------|-------------|
| `REVIEWED` | Revisada |
| `RESOLVED` | Resuelta |
| `DISMISSED` | Descartada |
| `DEFERRED` | Pospuesta |

### Dataclass `Session`

| Campo | Tipo | Default |
|-------|------|---------|
| `id` | `Optional[int]` | `None` |
| `project_id` | `int` | `0` |
| `started_at` | `Optional[datetime]` | `None` |
| `ended_at` | `Optional[datetime]` | `None` |
| `duration_seconds` | `int` | `0` |
| `alerts_reviewed` | `int` | `0` |
| `alerts_resolved` | `int` | `0` |
| `entities_merged` | `int` | `0` |
| `last_position_char` | `Optional[int]` | `None` |
| `last_chapter_id` | `Optional[int]` | `None` |
| `notes` | `str` | `""` |

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `is_active` | `bool` | True si `ended_at` es None |
| `duration_minutes` | `float` | `duration_seconds / 60` |

### Clase `SessionManager`

| Método | Firma | Retorno |
|--------|-------|---------|
| `__init__` | `(project_id: int, db: Optional[Database] = None)` | - |
| `start` | `() -> Session` | Nueva sesión |
| `end` | `(notes: str = "") -> Session` | Sesión finalizada |
| `record_alert_action` | `(alert_id: int, action: AlertAction) -> None` | - |
| `record_entity_merge` | `() -> None` | - |
| `update_position` | `(chapter_id: Optional[int] = None, char_position: Optional[int] = None) -> None` | - |
| `get_last_position` | `() -> tuple[Optional[int], Optional[int]]` | (chapter_id, position) |
| `get_project_stats` | `() -> dict` | Estadísticas |
| `list_sessions` | `(limit: int = 20) -> list[Session]` | Sesiones recientes |

---

## Document Fingerprint (`document_fingerprint.py`)

### Dataclass `DocumentFingerprint`

| Campo | Tipo |
|-------|------|
| `full_hash` | `str` |
| `sample_hash` | `str` |
| `word_count` | `int` |
| `char_count` | `int` |
| `ngram_signature` | `list[str]` |

### Convenience Function

```python
from narrative_assistant.persistence.document_fingerprint import generate_fingerprint

fp = generate_fingerprint(text)
```

| Función | Firma |
|---------|-------|
| `generate_fingerprint` | `(text: str) -> DocumentFingerprint` |

---

## Errores Comunes

### Error: `'ProjectManager' object has no attribute 'create'`

**Incorrecto:**
```python
manager = ProjectManager()
project = Project(name="Mi Novela", ...)
manager.create(project)  # Este método NO existe
```

**Correcto:**
```python
manager = ProjectManager()
result = manager.create_from_document(
    text="Contenido del documento...",
    name="Mi Novela",
    document_format="docx",
    document_path=Path("ruta/al/documento.docx"),
    description="Novela de fantasía",
)
if result.is_success:
    project = result.value
```

### Error: Usando `last_char_position` en Session

**Incorrecto:**
```python
session.last_char_position  # Campo inexistente
```

**Correcto:**
```python
session.last_position_char  # Campo correcto
```

### Error: Esperando datetime en ChapterData

**Incorrecto:**
```python
chapter.created_at.strftime("%Y-%m-%d")  # Es string, no datetime
```

**Correcto:**
```python
# created_at ya es un ISO format string
created_date = chapter.created_at  # "2024-01-15T10:30:00"
# O convertir si necesitas datetime:
from datetime import datetime
dt = datetime.fromisoformat(chapter.created_at)
```
