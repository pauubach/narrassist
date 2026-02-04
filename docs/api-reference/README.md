# API Reference - Narrative Assistant

Esta carpeta contiene la documentación de referencia de todas las APIs, modelos y tipos del proyecto.

## Estructura

| Archivo | Descripción |
|---------|-------------|
| [backend-persistence.md](backend-persistence.md) | Clases de persistencia: Database, Project, Session, Chapter |
| [backend-entities.md](backend-entities.md) | Modelos y repositorio de entidades |
| [backend-nlp.md](backend-nlp.md) | Pipeline NLP: NER, atributos, embeddings |
| [backend-alerts.md](backend-alerts.md) | Sistema de alertas |
| [backend-core.md](backend-core.md) | Core: Result pattern, errores, configuración |
| [frontend-types.md](frontend-types.md) | Tipos TypeScript del frontend |
| [frontend-stores.md](frontend-stores.md) | Pinia stores |
| [http-endpoints.md](http-endpoints.md) | Endpoints HTTP del API server |

## Uso

**IMPORTANTE**: Antes de usar cualquier clase o método del backend/frontend:

1. Consultar el archivo correspondiente para verificar:
   - Nombre exacto de la clase/función
   - Firma completa del método (parámetros y tipos)
   - Nombre de la función factory (`get_*()`)

2. Al crear nuevo código, actualizar esta documentación si se añaden/modifican APIs.

## Convenciones

### Backend (Python)

- **Singleton pattern**: Usar `get_*()` para obtener instancias
  ```python
  # Correcto
  from narrative_assistant.persistence.database import get_database
  db = get_database()

  # Incorrecto - no existe
  from narrative_assistant.persistence.database import get_db
  ```

- **Result pattern**: Las operaciones fallibles retornan `Result[T]`
  ```python
  result = repo.create(entity)
  if result.is_success:
      entity = result.value
  ```

### Frontend (TypeScript)

- **Stores**: Usar composables de Pinia
  ```typescript
  import { useProjectsStore } from '@/stores/projects'
  const store = useProjectsStore()
  ```

- **Types**: Importar desde `@/types`
  ```typescript
  import type { Project, Entity, Alert } from '@/types'
  ```

## Última actualización

2026-02-04

> **Nota**: La API cuenta con 170+ endpoints. Para el listado completo, ver [http-endpoints.md](http-endpoints.md).
