# API Reference - Narrative Assistant

Esta carpeta contiene la documentación de referencia de todas las APIs, modelos y tipos del proyecto.

## Estructura

### Backend Python

| Archivo | Descripción |
|---------|-------------|
| [backend-core.md](backend-core.md) | Core: Result pattern, errores, configuración |
| [backend-persistence.md](backend-persistence.md) | Clases de persistencia: Database, Project, Session, Chapter |
| [backend-entities.md](backend-entities.md) | Modelos y repositorio de entidades |
| [backend-nlp.md](backend-nlp.md) | Pipeline NLP: NER, atributos, embeddings |
| [backend-alerts.md](backend-alerts.md) | Sistema de alertas |

### Frontend TypeScript

| Archivo | Descripción |
|---------|-------------|
| [frontend-stores.md](frontend-stores.md) | Pinia stores (projects, entities, alerts, collections) |

### HTTP API

| Archivo | Descripción |
|---------|-------------|
| [http-endpoints.md](http-endpoints.md) | ~70 endpoints principales (170+ en total) |

**Endpoints por módulo**:
- Proyectos: CRUD, análisis, progreso
- Entidades: Listado, fusión, atributos
- Alertas: CRUD, resolución, filtrado
- Capítulos: Listado, estructura
- Relaciones: Grafos, asimetrías, clusters
- **Colecciones**: Cross-book, entity links, inconsistencias
- **Eventos**: Timeline, stats, export
- **Voz y Estilo**: Perfiles, desviaciones, POV, focalización
- Servicios: LLM config, Ollama status

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

## Novedades

### v0.10.9+ (2026-02-06)

- **Colecciones cross-book**: Análisis de sagas/series completas
- **Entity linking**: Vinculación de personajes entre libros
- **Eventos narrativos**: 48 tipos de eventos en 3 tiers
- **Voz y estilo**: Perfiles de habla, desviaciones, POV

### Arquitectura

El sistema sigue los patrones documentados en [docs/adr/](../adr/):
- SQLite local (ADR-001)
- LLM local con Ollama (ADR-002)
- NER multi-modelo con votación (ADR-003)
- Offline-first architecture (ADR-004)
- PrimeVue UI components (ADR-005)

## Última actualización

2026-02-18

> **Nota**: La API cuenta con 170+ endpoints. Esta referencia cubre los ~70 principales. Para detalles de endpoints específicos, ver [http-endpoints.md](http-endpoints.md).
