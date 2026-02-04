# Backend - Entities Module

Ubicación: `src/narrative_assistant/entities/`

## Models (`models.py`)

### Enum `EntityType`

| Valor | Descripción |
|-------|-------------|
| `CHARACTER` | Personaje |
| `ANIMAL` | Animal |
| `CREATURE` | Criatura fantástica |
| `LOCATION` | Lugar genérico |
| `BUILDING` | Edificio |
| `REGION` | Región geográfica |
| `OBJECT` | Objeto |
| `VEHICLE` | Vehículo |
| `ORGANIZATION` | Organización |
| `FACTION` | Facción/grupo |
| `FAMILY` | Familia |
| `EVENT` | Evento |
| `TIME_PERIOD` | Período temporal |
| `CONCEPT` | Concepto abstracto |
| `RELIGION` | Religión |
| `MAGIC_SYSTEM` | Sistema mágico |
| `WORK` | Obra (libro, canción) |
| `TITLE` | Título nobiliario |
| `LANGUAGE` | Idioma |
| `CUSTOM` | Personalizado |

**Nota**: Los valores son lowercase en la base de datos (ej: `"character"`, `"location"`)

### Enum `EntityImportance`

| Valor | Descripción |
|-------|-------------|
| `CRITICAL` | Protagonista/crucial |
| `HIGH` | Muy importante |
| `MEDIUM` | Importancia media |
| `LOW` | Secundario |
| `MINIMAL` | Mención menor |

### Dataclass `Entity`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `Optional[int]` | ID de la entidad |
| `project_id` | `int` | ID del proyecto |
| `entity_type` | `EntityType` | Tipo de entidad |
| `canonical_name` | `str` | Nombre canónico |
| `aliases` | `list[str]` | Lista de alias |
| `importance` | `EntityImportance` | Importancia |
| `description` | `Optional[str]` | Descripción |
| `first_appearance_char` | `Optional[int]` | Posición primera aparición |
| `mention_count` | `int` | Número de menciones |
| `merged_from_ids` | `list[int]` | IDs de entidades fusionadas |
| `is_active` | `bool` | Si está activa |
| `created_at` | `Optional[datetime]` | Fecha creación |
| `updated_at` | `Optional[datetime]` | Última modificación |

| Método | Firma |
|--------|-------|
| `to_dict` | `() -> dict` |
| `from_row` | `@classmethod (row) -> Entity` |
| `add_alias` | `(name: str) -> bool` |
| `has_alias` | `(name: str) -> bool` |
| `all_names` | `@property -> list[str]` |

### Dataclass `EntityMention`

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `id` | `Optional[int]` | `None` | ID de la mención |
| `entity_id` | `int` | `0` | ID de la entidad |
| `surface_form` | `str` | `""` | Texto como aparece |
| `start_char` | `int` | `0` | Posición inicial |
| `end_char` | `int` | `0` | Posición final |
| `chapter_id` | `Optional[int]` | `None` | ID del capítulo |
| `context_before` | `Optional[str]` | `None` | Contexto previo (para visualización) |
| `context_after` | `Optional[str]` | `None` | Contexto posterior |
| `confidence` | `float` | `1.0` | Confianza 0.0-1.0 |
| `source` | `str` | `"ner"` | Fuente (ner, coref, manual, gazetteer) |

| Método/Propiedad | Firma |
|------------------|-------|
| `to_dict` | `() -> dict` |
| `from_row` | `@classmethod (row) -> EntityMention` |
| `char_span` | `@property -> tuple[int, int]` |

---

## Repository (`repository.py`)

### Clase `EntityRepository`

#### Constructor

```python
from narrative_assistant.entities.repository import get_entity_repository

repo = get_entity_repository()  # Singleton
```

#### Métodos CRUD de Entidades

| Método | Firma | Retorno |
|--------|-------|---------|
| `create_entity` | `(entity: Entity) -> int` | ID de la entidad creada |
| `get_entity` | `(entity_id: int) -> Optional[Entity]` | Entidad o None |
| `get_entities_by_project` | `(project_id: int, entity_type: Optional[EntityType] = None, active_only: bool = True) -> list[Entity]` | Lista de entidades |
| `update_entity` | `(entity_id: int, canonical_name: Optional[str] = None, aliases: Optional[list[str]] = None, importance: Optional[EntityImportance] = None, description: Optional[str] = None, merged_from_ids: Optional[list[int]] = None) -> bool` | Éxito |
| `delete_entity` | `(entity_id: int, hard_delete: bool = False) -> bool` | Éxito |
| `increment_mention_count` | `(entity_id: int, delta: int = 1) -> None` | - |

**Nota**: `update_entity` toma parámetros individuales, NO un objeto `Entity`. Solo actualiza los campos que se pasan (no-None).

#### Métodos de Menciones

| Método | Firma | Retorno |
|--------|-------|---------|
| `create_mention` | `(mention: EntityMention) -> int` | ID de la mención |
| `create_mentions_batch` | `(mentions: list[EntityMention]) -> int` | Número creadas |
| `get_mentions_by_entity` | `(entity_id: int) -> list[EntityMention]` | Lista de menciones |
| `get_mentions_by_chapter` | `(chapter_id: int) -> list[EntityMention]` | Menciones del capítulo |
| `move_mentions` | `(from_entity_id: int, to_entity_id: int) -> int` | Número movidas |
| `delete_mentions_by_entity` | `(entity_id: int) -> int` | Número eliminadas |

#### Métodos de Atributos

| Método | Firma | Retorno |
|--------|-------|---------|
| `create_attribute` | `(entity_id: int, attribute_type: str, attribute_key: str, attribute_value: str, confidence: float = 1.0, source_mention_id: Optional[int] = None) -> int` | ID del atributo |
| `get_attributes_by_project` | `(project_id: int) -> list[dict]` | Lista de atributos con entity_name |
| `get_attribute_evidences` | `(attribute_id: int) -> list[dict]` | Lista de evidencias del atributo |
| `move_attributes` | `(from_entity_id: int, to_entity_id: int) -> int` | Número movidos |

#### Métodos de Búsqueda

| Método | Firma | Retorno |
|--------|-------|---------|
| `find_entities_by_name` | `(project_id: int, name: str, fuzzy: bool = False) -> list[Entity]` | Entidades coincidentes |
| `get_entity_stats` | `(project_id: int) -> dict` | Estadísticas |

#### Métodos de Historial de Fusión

| Método | Firma | Retorno |
|--------|-------|---------|
| `add_merge_history` | `(project_id: int, result_entity_id: int, source_entity_ids: list[int], source_snapshots: list[dict], canonical_names_before: list[str], merged_by: str = "user", note: Optional[str] = None) -> int` | ID del registro |
| `get_merge_history` | `(project_id: int) -> list[MergeHistory]` | Historial de fusiones |
| `mark_merge_undone` | `(merge_id: int) -> bool` | Éxito |

### Factory Function

```python
from narrative_assistant.entities.repository import get_entity_repository, reset_entity_repository

repo = get_entity_repository()  # Obtener singleton
reset_entity_repository()  # Reset para tests
```

| Función | Firma |
|---------|-------|
| `get_entity_repository` | `(database: Optional[Database] = None) -> EntityRepository` |
| `reset_entity_repository` | `() -> None` |

---

## Fusion (`fusion.py`)

### Clase `EntityFusionService`

| Método | Firma | Retorno |
|--------|-------|---------|
| `__init__` | `(repo: Optional[EntityRepository] = None)` | - |
| `merge_entities` | `(project_id: int, source_ids: list[int], target_id: int, note: str = "") -> Result[Entity]` | Entidad fusionada |
| `suggest_merges` | `(project_id: int, similarity_threshold: float = 0.8) -> Result[list[MergeSuggestion]]` | Sugerencias |
| `auto_merge_by_name` | `(project_id: int, similarity_threshold: float = 0.9) -> Result[int]` | Número fusionadas |
| `undo_merge` | `(merge_history: MergeHistory) -> Result[Entity]` | Entidad restaurada |

---

## Errores Comunes

### Error: `'EntityRepository' object has no attribute 'get_by_project'`

**Incorrecto:**
```python
entities = repo.get_by_project(project_id)
```

**Correcto:**
```python
entities = repo.get_entities_by_project(project_id, active_only=True)
```

### Error: `'EntityRepository' object has no attribute 'get_by_id'`

**Incorrecto:**
```python
entity = repo.get_by_id(entity_id)
```

**Correcto:**
```python
entity = repo.get_entity(entity_id)
```

### Error: `'EntityRepository' object has no attribute 'get_mentions'`

**Incorrecto:**
```python
mentions = repo.get_mentions(entity_id)
```

**Correcto:**
```python
mentions = repo.get_mentions_by_entity(entity_id)
```

### Error: `'EntityRepository' object has no attribute 'create'`

**Incorrecto:**
```python
repo.create(project_id=1, name="Juan", entity_type="CHARACTER")
```

**Correcto:**
```python
entity = Entity(
    project_id=1,
    entity_type=EntityType.CHARACTER,
    canonical_name="Juan",
    aliases=[],
    importance=EntityImportance.MEDIUM,
    mention_count=1,
    is_active=True,
)
entity_id = repo.create_entity(entity)
```
