# API Tests

## Estado Actual

Los tests de API (`test_events_export.py`, `test_events_stats.py`) están implementados pero **no se pueden ejecutar actualmente** debido a una incompatibilidad de versiones entre httpx y starlette.

### Error

```
TypeError: Client.__init__() got an unexpected keyword argument 'app'
```

### Causa

- **httpx**: 0.28.1
- **starlette**: 0.36.3
- **fastapi**: 0.109.2

Starlette 0.36.3 usa una API de httpx que cambió en la versión 0.28.x.

### Solución

Actualizar httpx a una versión compatible o downgrade starlette:

```bash
# Opción 1: Actualizar httpx (preferido)
pip install --upgrade httpx

# Opción 2: Downgrade starlette
pip install starlette==0.35.0
```

**NOTA**: No se ha aplicado la solución automáticamente para evitar romper otras dependencias del proyecto.

## Tests Implementados

### `test_events_export.py` (17 tests)

Tests para el endpoint `/api/projects/{id}/events/export`:

- **Formatos**: CSV (UTF-8 BOM), JSON
- **Filtros**: tier, event_types, critical_only, chapter_range
- **Edge cases**: proyecto inexistente, proyecto vacío, filtros combinados
- **CSV**: Verificación de BOM, encoding español, content-disposition
- **JSON**: Schema consistency, filters_applied

### `test_events_stats.py` (11 tests)

Tests para el endpoint `/api/projects/{id}/events/stats`:

- **Schema**: Estructura completa de stats response
- **Métricas**:
  - `critical_unresolved`: count, by_type, details (limit 10)
  - `empty_chapters`: lista de capítulos sin eventos tier 1
  - `event_clusters`: top 3 clusters (3+ eventos mismo tipo)
  - `density_by_chapter`: tier1/2/3 por capítulo
- **Edge cases**: proyecto vacío, proyecto inexistente, sorting

## Fixtures

Las fixtures están definidas en `conftest.py`:

- **`test_client`**: TestClient de FastAPI (cuando httpx/starlette compatibles)
- **`sample_project`**: Proyecto con 5 capítulos de ~250 palabras cada uno
- **`empty_project`**: Proyecto sin capítulos para edge cases

## Ejecución Manual

Una vez resuelto el issue de dependencias:

```bash
# Todos los tests de API
pytest tests/api/ -v

# Solo export
pytest tests/api/test_events_export.py -v

# Solo stats
pytest tests/api/test_events_stats.py -v

# Test específico
pytest tests/api/test_events_export.py::test_export_csv_basic -v
```

## Verificación Manual

Mientras los tests automáticos no funcionen, se puede verificar manualmente:

1. Iniciar el servidor API: `python api-server/main.py`
2. Crear un proyecto y capítulos desde el frontend
3. Probar endpoints:
   - `GET /api/projects/{id}/events/export?format=csv`
   - `GET /api/projects/{id}/events/stats`
4. Verificar respuestas con Postman/curl
