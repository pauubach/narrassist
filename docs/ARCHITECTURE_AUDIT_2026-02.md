# Auditoría Arquitectónica Completa - Febrero 2026

## Resumen Ejecutivo

Auditoría comprehensiva del codebase de Narrative Assistant realizada por comité de 5 expertos paralelos:
- **Frontend TypeScript/Vue**
- **Backend Python**
- **Cobertura de Tests**
- **Seguridad**
- **Arquitectura**

---

## 1. Análisis de Patrones de Diseño

### 1.1 Result Pattern

**Estado Actual:** ✅ Bien diseñado, ⚠️ Inconsistentemente aplicado

**Implementación en `core/result.py`:**
- Factory methods: `success()`, `failure()`, `partial()`
- Severidades: `FATAL`, `RECOVERABLE`, `DEGRADED`
- Operaciones monádicas: `map()`, `unwrap()`, `unwrap_or()`, `merge()`

**Problema Principal:** Uso inconsistente:

| Módulo | Usa Result | Devuelve None |
|--------|------------|---------------|
| Parsers | ✅ | - |
| EntityRepository | ❌ | ✅ `T \| None` |
| AlertRepository | ❌ | ✅ `T \| None` |
| ChapterRepository | ❌ | ✅ `T \| None` |
| API Routers | Parcial | Mixto |

**Recomendación:** Estandarizar todos los repositorios a `Result[T]`:
```python
# ANTES
def get_entity(self, id: int) -> Entity | None:
    row = self.db.fetchone(...)
    return Entity.from_row(row) if row else None

# DESPUÉS
def get_entity(self, id: int) -> Result[Entity]:
    row = self.db.fetchone(...)
    if not row:
        return Result.failure(NotFoundError(f"Entity {id}"))
    return Result.success(Entity.from_row(row))
```

---

### 1.2 Singleton Pattern

**Estado Actual:** ⚠️ Thread-safe pero DRY violation severa

**Hallazgo:** 17+ singletons con código idéntico duplicado:

```
src/narrative_assistant/
├── nlp/dialogue_validator.py        # _validator_instance + get/reset
├── nlp/sentiment.py                 # _analyzer_instance + get/reset
├── nlp/grammar/grammar_checker.py   # _instance + get/reset
├── nlp/style/sentence_energy.py     # _instance + get/reset
├── nlp/style/sticky_sentences.py    # _instance + get/reset
├── nlp/style/repetition_detector.py # _instance + get/reset
├── nlp/style/readability.py         # _instance + get/reset
├── nlp/style/filler_detector.py     # _instance + get/reset
├── nlp/style/editorial_rules.py     # _instance + get/reset
├── nlp/style/sensory_report.py      # _instance + get/reset
├── nlp/orthography/spelling_checker.py
├── nlp/orthography/voting_checker.py
├── nlp/extraction/pipeline.py
├── analysis/duplicate_detector.py
├── analysis/narrative_structure.py
├── analysis/emotional_coherence.py
└── core/resource_manager.py
```

**Patrón actual (repetido 17 veces):**
```python
_instance: Optional["SomeClass"] = None
_lock = threading.Lock()

def get_some_class() -> SomeClass:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SomeClass()
    return _instance

def reset_some_class() -> None:
    global _instance
    _instance = None
```

**Recomendación: Decorator `@singleton`**

Crear en `core/patterns.py`:
```python
import threading
from functools import wraps
from typing import TypeVar, Type

T = TypeVar('T')

def singleton(cls: Type[T]) -> Type[T]:
    """Decorator que convierte una clase en singleton thread-safe."""
    _instance = None
    _lock = threading.Lock()
    original_new = cls.__new__

    @wraps(original_new)
    def new_singleton(cls, *args, **kwargs):
        nonlocal _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = object.__new__(cls)
        return _instance

    cls.__new__ = new_singleton
    cls._reset_singleton = staticmethod(lambda: setattr(cls, '_instance', None))
    return cls

# Uso:
@singleton
class SentenceEnergyDetector:
    def __init__(self):
        # Solo se ejecuta una vez
        pass
```

**Alternativa mejor: Dependency Injection Container**

```python
# core/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    database = providers.Singleton(Database)
    entity_repo = providers.Factory(EntityRepository, db=database)
    alert_repo = providers.Factory(AlertRepository, db=database)

    sentence_energy = providers.Singleton(SentenceEnergyDetector)
    spelling_checker = providers.Singleton(VotingSpellingChecker)
    # ... etc
```

---

### 1.3 Repository Pattern

**Estado Actual:** ✅ Bien estructurado, ⚠️ SQL inline riesgoso

**Hallazgo en `entities/repository.py:203`:**
```python
sql = f"UPDATE entities SET {', '.join(updates)} WHERE id = ?"
```

**Riesgo:** Aunque `updates` viene del código interno, es mala práctica.

**Recomendación: Query Builder o Whitelist**

```python
# Opción 1: Whitelist explícita
ALLOWED_UPDATE_FIELDS = {'canonical_name', 'description', 'importance', 'is_active'}

def update_entity(self, entity_id: int, **fields) -> Result[None]:
    invalid = set(fields.keys()) - ALLOWED_UPDATE_FIELDS
    if invalid:
        return Result.failure(ValidationError(f"Invalid fields: {invalid}"))

    updates = [f"{k}=?" for k in fields.keys()]
    values = list(fields.values()) + [entity_id]
    sql = f"UPDATE entities SET {', '.join(updates)} WHERE id = ?"
    # ...

# Opción 2: SQLAlchemy Core (más robusto)
from sqlalchemy import update
stmt = update(entities_table).where(entities_table.c.id == entity_id).values(**fields)
```

---

### 1.4 Strategy Pattern

**Estado Actual:** ✅ Bien en extractores, ❌ Mal en detectores de correcciones

**Problema en `corrections/orchestrator.py:61-72`:**
```python
# Hardcoded - viola Open/Closed Principle
self._detectors = {
    CorrectionCategory.TYPOGRAPHY: TypographyDetector(self.config.typography),
    CorrectionCategory.REPETITION: RepetitionDetector(self.config.repetition),
    # ... 10+ detectores más
}
```

**Recomendación: Detector Registry**

```python
# corrections/registry.py
from typing import Type
from .base import BaseDetector

class DetectorRegistry:
    _detectors: dict[CorrectionCategory, Type[BaseDetector]] = {}

    @classmethod
    def register(cls, category: CorrectionCategory):
        def decorator(detector_class: Type[BaseDetector]):
            cls._detectors[category] = detector_class
            return detector_class
        return decorator

    @classmethod
    def get_all(cls, config: CorrectionConfig) -> dict[CorrectionCategory, BaseDetector]:
        return {
            cat: detector_class(getattr(config, cat.value, None))
            for cat, detector_class in cls._detectors.items()
        }

# En cada detector:
@DetectorRegistry.register(CorrectionCategory.TYPOGRAPHY)
class TypographyDetector(BaseDetector):
    pass

# En orchestrator:
self._detectors = DetectorRegistry.get_all(self.config)
```

---

### 1.5 Service Layer Pattern

**Estado Actual:** ❌ NO IMPLEMENTADO - Crítico

**Problema en `api-server/routers/analysis.py`:**
- 700+ líneas de lógica de negocio en route handlers
- Operaciones SQL directas en rutas
- Progress tracking mezclado con HTTP
- Gestión de estado con dicts globales

**Ejemplo problemático (líneas 136-150):**
```python
@router.post("/api/projects/{project_id}/analyze")
async def start_analysis(project_id: int, file: UploadFile):
    # Debería ser 5 líneas delegando a servicio
    # En cambio hay 500+ líneas de:
    # - Validación de proyecto
    # - Gestión de archivos temporales
    # - Inicialización de progreso
    # - Limpieza de BD
    # - Ejecución de pipeline
    # - Manejo de errores
    # - Almacenamiento de resultados
```

**Recomendación: Capa de Servicio**

```python
# src/narrative_assistant/services/analysis_service.py
class AnalysisService:
    def __init__(
        self,
        project_manager: ProjectManager,
        pipeline: UnifiedAnalysisPipeline,
        progress_tracker: ProgressTracker,
    ):
        self._projects = project_manager
        self._pipeline = pipeline
        self._progress = progress_tracker

    async def start_analysis(
        self,
        project_id: int,
        file_path: Path | None = None
    ) -> Result[AnalysisRun]:
        # Toda la lógica de negocio aquí
        pass

# api-server/routers/analysis.py
@router.post("/api/projects/{project_id}/analyze")
async def start_analysis(
    project_id: int,
    file: UploadFile = None,
    service: AnalysisService = Depends(get_analysis_service)
):
    result = await service.start_analysis(project_id, file)
    if result.is_failure:
        raise HTTPException(400, result.error.message)
    return ApiResponse(success=True, data={"run_id": result.value.id})
```

---

### 1.6 Observer/Event Pattern

**Estado Actual:** ❌ NO IMPLEMENTADO

**Problema actual (progreso con dict global):**
```python
# deps.py
analysis_progress_storage = {}
_progress_lock = threading.Lock()

# En routers
with deps._progress_lock:
    deps.analysis_progress_storage[project_id] = {...}
```

**Recomendación: Event Emitter**

```python
# core/events.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class AnalysisProgressEvent:
    project_id: int
    phase: str
    progress: float
    message: str

class EventBus:
    _handlers: dict[type, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: type, handler: Callable):
        cls._handlers.setdefault(event_type, []).append(handler)

    @classmethod
    async def publish(cls, event):
        for handler in cls._handlers.get(type(event), []):
            await handler(event)

# En pipeline:
await EventBus.publish(AnalysisProgressEvent(
    project_id=123,
    phase="ner",
    progress=0.4,
    message="Extrayendo entidades..."
))

# En WebSocket handler:
EventBus.subscribe(AnalysisProgressEvent, send_to_client)
```

---

## 2. God Classes - Refactoring Prioritario

### 2.1 Clases >3000 líneas (Críticas)

| Archivo | Líneas | Responsabilidades | Refactoring |
|---------|--------|-------------------|-------------|
| `nlp/attributes.py` | 4333 | Extracción + Validación + Voting + Weights | Separar en 4 clases |
| `nlp/ner.py` | 4085 | NER + Gazetteer + Validation + Merging | Separar en 4 clases |
| `pipelines/unified_analysis.py` | 3526 | 8 fases + Memory + Progress + Errors | Extraer PhaseRunner |
| `nlp/orthography/voting_checker.py` | 2003 | Checker + Voting + 3 backends | Separar backends |
| `alerts/engine.py` | 1652 | Create + Classify + Prioritize + Filter + Stats | Separar concerns |

### 2.2 Plan de Refactoring para attributes.py

```
nlp/attributes.py (4333 líneas)
    ↓ Refactoring
nlp/attributes/
├── __init__.py           # Re-exports
├── extractors/
│   ├── base.py           # BaseAttributeExtractor ABC
│   ├── regex.py          # RegexAttributeExtractor
│   ├── dependency.py     # DependencyAttributeExtractor
│   └── llm.py            # LLMAttributeExtractor
├── voting/
│   ├── aggregator.py     # VotingAggregator
│   └── weights.py        # WeightManager (carga/normaliza pesos)
├── validation/
│   ├── metaphor.py       # MetaphorValidator
│   └── consistency.py    # ConsistencyValidator
└── pipeline.py           # AttributeExtractionPipeline (orquestador)
```

---

## 3. Cobertura de Tests - Estado Crítico

### 3.1 Estadísticas

| Métrica | Valor |
|---------|-------|
| Módulos totales | 164 |
| Módulos con tests | 35 (21.3%) |
| Módulos sin tests | 129 (78.7%) |
| Ratio tests/src | 0.39x |
| Tests sin assertions | 143 |

### 3.2 Módulos Críticos Sin Tests

**PARSERS (0/4):**
- `docx_parser.py`, `txt_parser.py`, `pdf_parser.py`, `epub_parser.py`

**PERSISTENCE (0/3 críticos):**
- `database.py`, `project.py`, `analysis.py`

**PIPELINES (0/2):**
- `analysis_pipeline.py`, `unified_analysis.py`

**CORE (0/8):**
- `config.py`, `device.py`, `errors.py`, `model_manager.py`, etc.

### 3.3 Tests Prioritarios a Crear

1. **Parsers** (~150 tests) - Bloquean todo lo demás
2. **Database** (~80 tests) - Persistencia crítica
3. **Pipeline E2E** (~100 tests) - Flujo principal
4. **Coreference** (~60 tests) - NLP crítico

---

## 4. Seguridad - Estado Bueno

### 4.1 Fortalezas
- ✅ Excelente protección path traversal
- ✅ Manuscritos 100% locales
- ✅ Sin telemetría
- ✅ Subprocess seguro (no shell=True)
- ✅ Dependencias actualizadas

### 4.2 Mejoras Recomendadas

**P1 - LLM Host Whitelist:**
```python
ALLOWED_LLM_HOSTS = {
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:11434",
    "http://127.0.0.1:11434",
}
```

**P2 - SQL Field Whitelist** (ya mencionado arriba)

---

## 5. Frontend TypeScript - Hallazgos Clave

### 5.1 Componentes Muy Grandes

| Componente | Líneas | Recomendación |
|------------|--------|---------------|
| SettingsView.vue | 4262 | Dividir en 7 sub-componentes |
| RelationshipGraph.vue | 2296 | Dividir en 5 sub-componentes |
| DocumentViewer.vue | 2134 | Extraer composables |
| CorrectionConfigModal.vue | 1737 | Dividir por tabs |
| EntitiesTab.vue | 1663 | Separar filtros/edición |

### 5.2 Type Safety Issues

- 8 `as any` en `voiceAndStyle.ts` (líneas 153-196)
- Type assertion insegura en `App.vue:94`
- 28 watchers sin abstracción en workspace components

### 5.3 API Consolidation

Componentes usando `fetch()` directo en vez de `api.ts`:
- `ExportDialog.vue` - 15+ fetch calls
- `CorrectionDefaultsManager.vue` - 5+ fetch calls

---

## 6. Plan de Acción Priorizado

### Fase 1: Fundamentos (2-3 semanas)

1. **Crear decorator `@singleton`** - Eliminar 17 duplicaciones
2. **Crear Service Layer básico** - Extraer lógica de analysis.py
3. **Estandarizar Result pattern** - Actualizar repositorios

### Fase 2: Tests Críticos (2-3 semanas)

4. **Tests de parsers** - 100% cobertura de formatos
5. **Tests de database** - Transacciones, migraciones
6. **Tests E2E de pipeline** - Flujo completo

### Fase 3: Refactoring God Classes (3-4 semanas)

7. **Dividir attributes.py** - 4333 → 4 módulos
8. **Dividir ner.py** - 4085 → 4 módulos
9. **Extraer PhaseRunner de unified_analysis.py**

### Fase 4: Frontend Cleanup (2 semanas)

10. **Eliminar `as any`** - Tipos correctos
11. **Dividir SettingsView.vue** - 7 sub-componentes
12. **Consolidar API calls** - Usar api.ts everywhere

---

## 7. Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Cobertura tests | 21% | 60% |
| God classes (>500 líneas) | 5 | 0 |
| Singletons duplicados | 17 | 0 |
| `as any` en TypeScript | 8+ | 0 |
| Componentes >1000 líneas | 6 | 0 |

---

*Auditoría realizada: 2026-02-04*
*Herramientas: Claude Opus 4.5, 5 agentes especializados*
