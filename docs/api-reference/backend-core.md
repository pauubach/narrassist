# Backend - Core Module

Ubicación: `src/narrative_assistant/core/`

## Result Pattern (`result.py`)

### Clase `Result[T]`

Patrón para operaciones que pueden tener éxitos parciales.

```python
from narrative_assistant.core.result import Result

# Uso básico
result = some_operation()
if result.is_success:
    print(result.value)
elif result.is_partial:
    print(f"Parcial: {result.value}, errores: {result.errors}")
else:
    print(f"Error: {result.error}")
```

#### Atributos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `value` | `Optional[T]` | Resultado de la operación |
| `errors` | `list[NarrativeError]` | Lista de errores |
| `warnings` | `list[str]` | Advertencias |

#### Propiedades

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `is_success` | `bool` | True si no hay errores fatales |
| `is_partial` | `bool` | True si hay errores recuperables |
| `is_degraded` | `bool` | True si funciona con capacidad reducida |
| `is_failure` | `bool` | True si hay errores fatales |
| `fatal_errors` | `list[NarrativeError]` | Solo errores fatales |
| `recoverable_errors` | `list[NarrativeError]` | Solo errores recuperables |
| `error` | `Optional[NarrativeError]` | Primer error (fatal o cualquiera) |

#### Métodos de Instancia

| Método | Firma | Descripción |
|--------|-------|-------------|
| `add_error` | `(error: NarrativeError) -> None` | Añade un error |
| `add_warning` | `(message: str) -> None` | Añade una advertencia |
| `merge` | `(other: Result) -> Result[T]` | Combina con otro resultado |
| `unwrap` | `() -> T` | Retorna valor o lanza error |
| `unwrap_or` | `(default: T) -> T` | Retorna valor o default |
| `map` | `(func: Callable[[T], U]) -> Result[U]` | Transforma el valor |

#### Métodos de Clase (Constructores)

| Método | Firma | Descripción |
|--------|-------|-------------|
| `success` | `(value: T) -> Result[T]` | Crea resultado exitoso |
| `failure` | `(error: NarrativeError) -> Result[T]` | Crea resultado fallido |
| `partial` | `(value: T, errors: list[NarrativeError]) -> Result[T]` | Crea resultado parcial |

#### Ejemplos

```python
from narrative_assistant.core.result import Result
from narrative_assistant.core.errors import NarrativeError

# Crear resultado exitoso
result = Result.success({"entities": 10})

# Crear resultado fallido
error = NarrativeError(message="Documento corrupto")
result = Result.failure(error)

# Crear resultado parcial
result = Result.partial(
    value={"entities": 8},
    errors=[ChapterProcessingError(chapter_num=3)]
)

# Verificar y usar
if result.is_success:
    data = result.value
elif result.is_partial:
    data = result.value  # Datos parciales disponibles
    for err in result.errors:
        print(f"Advertencia: {err.user_message}")
else:
    print(f"Error fatal: {result.error.user_message}")

# Usar unwrap_or para valor por defecto
count = result.unwrap_or(default=0)

# Transformar con map
doubled = result.map(lambda x: x * 2)
```

---

## Errors (`errors.py`)

### Enum `ErrorSeverity`

| Valor | Descripción |
|-------|-------------|
| `RECOVERABLE` | Continuar con advertencia |
| `DEGRADED` | Continuar con funcionalidad reducida |
| `FATAL` | Abortar operación |

### Clase Base `NarrativeError`

```python
from narrative_assistant.core.errors import NarrativeError, ErrorSeverity

error = NarrativeError(
    message="Technical message for logs",
    severity=ErrorSeverity.RECOVERABLE,
    user_message="Mensaje amigable para el usuario",
    context={"key": "value"}
)
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `message` | `str` | Mensaje técnico (logs) |
| `severity` | `ErrorSeverity` | Nivel de severidad |
| `user_message` | `Optional[str]` | Mensaje para el usuario |
| `context` | `dict[str, Any]` | Datos adicionales |

### Errores de Parsing

| Clase | Severidad | Descripción |
|-------|-----------|-------------|
| `ParsingError` | - | Base para errores de parsing |
| `CorruptedDocumentError` | FATAL | Documento corrupto |
| `EmptyDocumentError` | FATAL | Documento sin contenido |
| `UnsupportedFormatError` | FATAL | Formato no soportado |
| `ScannedPDFError` | FATAL | PDF escaneado sin OCR |

#### `CorruptedDocumentError`

```python
from narrative_assistant.core.errors import CorruptedDocumentError

error = CorruptedDocumentError(
    file_path="/path/to/file.docx",
    original_error="ZIP file is corrupted"
)
```

| Campo | Tipo |
|-------|------|
| `file_path` | `str` |
| `original_error` | `str` |

#### `UnsupportedFormatError`

```python
from narrative_assistant.core.errors import UnsupportedFormatError

error = UnsupportedFormatError(
    file_path="/path/to/file.xyz",
    detected_format="xyz"
)
```

| Campo | Tipo |
|-------|------|
| `file_path` | `str` |
| `detected_format` | `str` |

### Errores de NLP

| Clase | Severidad | Descripción |
|-------|-----------|-------------|
| `NLPError` | - | Base para errores NLP |
| `ModelNotLoadedError` | FATAL | Modelo no disponible |
| `ChapterProcessingError` | RECOVERABLE | Error en un capítulo |

#### `ModelNotLoadedError`

```python
from narrative_assistant.core.errors import ModelNotLoadedError

error = ModelNotLoadedError(
    model_name="es_core_news_lg",
    hint="Ejecuta: python scripts/download_models.py"
)
```

| Campo | Tipo |
|-------|------|
| `model_name` | `str` |
| `hint` | `Optional[str]` |

#### `ChapterProcessingError`

```python
from narrative_assistant.core.errors import ChapterProcessingError

error = ChapterProcessingError(
    chapter_num=5,
    original_error="Memory error"
)
```

| Campo | Tipo |
|-------|------|
| `chapter_num` | `int` |
| `original_error` | `str` |

### Errores de Base de Datos

| Clase | Severidad | Descripción |
|-------|-----------|-------------|
| `DatabaseError` | - | Base para errores BD |
| `ProjectNotFoundError` | FATAL | Proyecto no existe |
| `DocumentAlreadyExistsError` | RECOVERABLE | Documento duplicado |

#### `ProjectNotFoundError`

```python
from narrative_assistant.core.errors import ProjectNotFoundError

error = ProjectNotFoundError(project_id=123)
```

| Campo | Tipo |
|-------|------|
| `project_id` | `int` |

### Errores de Recursos

| Clase | Severidad | Descripción |
|-------|-----------|-------------|
| `ResourceError` | - | Base para errores de recursos |
| `OutOfMemoryError` | DEGRADED | Memoria insuficiente |

#### `OutOfMemoryError`

```python
from narrative_assistant.core.errors import OutOfMemoryError

error = OutOfMemoryError(
    operation="embedding_generation",
    estimated_mb=2048
)
```

| Campo | Tipo |
|-------|------|
| `operation` | `str` |
| `estimated_mb` | `int` |

---

## Errores Comunes

### Error: Crear Result incorrectamente

**Incorrecto:**
```python
result = Result(value=data)  # Funciona pero no es idiomático
```

**Correcto:**
```python
result = Result.success(data)
# o
result = Result.failure(error)
# o
result = Result.partial(data, errors)
```

### Error: No verificar el resultado

**Incorrecto:**
```python
result = some_operation()
process(result.value)  # Puede ser None si falló
```

**Correcto:**
```python
result = some_operation()
if result.is_success:
    process(result.value)
else:
    handle_error(result.error)
```

### Error: Usar raise con NarrativeError

**Incorrecto (para operaciones que retornan Result):**
```python
def process(data):
    if invalid:
        raise NarrativeError(message="Invalid")
    return data
```

**Correcto:**
```python
def process(data) -> Result[Data]:
    if invalid:
        return Result.failure(NarrativeError(message="Invalid"))
    return Result.success(data)
```

### Error: Confundir is_success con is_failure

```python
# is_success = no hay errores FATALES (puede haber errores RECOVERABLE)
# is_failure = hay al menos un error FATAL

result = Result.partial(value=data, errors=[recoverable_error])

result.is_success  # True (no hay errores fatales)
result.is_failure  # False
result.is_partial  # True (hay errores recuperables)
result.value       # data (disponible)
```
