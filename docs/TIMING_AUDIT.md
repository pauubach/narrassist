# Auditoría de Timing de Ticks en Pipeline de Análisis

## Problemas Detectados

El usuario reportó **dos ticks que aparecen antes de tiempo**:

1. ❌ **Entidades**: Tick aparece antes de que MentionFinder complete la búsqueda de menciones adicionales
2. ❌ **Línea temporal**: Tick aparece inmediatamente, pero la timeline se construye on-demand al acceder al tab

## Análisis del Flujo

### Pipeline de Entidades (Fase NER + Fusion)

```
1. run_ner() → NER extrae entidades del texto
   └─ Persiste entidades y menciones NER en BD
   └─ tracker.end_phase("ner", 3) ✅

2. run_fusion() → Fusión semántica de entidades
   ├─ Fusiona entidades duplicadas
   ├─ Ejecuta correferencias
   ├─ **MARCA: entities_found** ❌ AQUÍ ESTÁ EL PROBLEMA
   │  └─ Línea 1577: metrics_update={"entities_found": len(entities)}
   │
   ├─ ⏳ MentionFinder busca menciones adicionales (líneas 1588-1652)
   │  ├─ Encuentra ocurrencias adicionales de nombres ya conocidos
   │  ├─ Valida menciones con sistema adaptativo (regex + spaCy)
   │  └─ Persiste menciones adicionales en BD
   │
   └─ Recalcula importancia de entidades (líneas 1654-1698)
      └─ tracker.end_phase("fusion", 4) ✅
```

### Frontend (useAnalysisPolling.ts)

```typescript
// Líneas 79-83
const entitiesFound = progressData.metrics?.entities_found
if (entitiesFound && entitiesFound > 0 && !entitiesLoadedDuringAnalysis && entities.value.length === 0) {
  entitiesLoadedDuringAnalysis = true
  loadEntities(project.value!.id)  // ✅ TICK aparece aquí
}
```

**Problema**: El tick se muestra cuando `entities_found > 0`, pero esto sucede **ANTES** de que MentionFinder complete.

## Impacto

1. **UX inconsistente**: El usuario ve el tick antes de que todas las menciones estén listas
2. **Datos incompletos**: Si el usuario accede a las entidades inmediatamente, verá `mention_count` incompleto
3. **Importancia incorrecta**: La importancia se recalcula DESPUÉS del tick (líneas 1654-1698)

## Solución

Mover la marca de `entities_found` al **final** del proceso de fusión, después de:
1. ✅ MentionFinder completar
2. ✅ Importancia recalculada
3. ✅ Menciones persistidas

### Cambio Requerido

**Archivo**: `api-server/routers/_analysis_phases.py`

**Línea actual (1577)**:
```python
_update_storage(
    project_id,
    progress=fusion_pct_end,
    current_action=f"Encontrados {len(entities)} personajes y elementos únicos",
    metrics_update={"entities_found": len(entities)},  # ❌ AQUÍ
)
tracker.end_phase("fusion", 4)
```

**Mover a después de línea 1698** (después de recalcular importancia):
```python
# Recalcular importancia final
logger.info("Recalculando importancia de entidades...")
# ... código de recalculo ...

# AQUÍ: Ahora sí, marcar entities_found
_update_storage(
    project_id,
    metrics_update={"entities_found": len(entities)},
)

tracker.end_phase("fusion", 4)
```

---

## Problema 2: Línea Temporal - Tab Status Prematuro

### Análisis del Flujo

```
1. Fase de análisis termina:
   └─ coreference phase completes ✅

2. Frontend verifica tab status (analysis.ts:527-557):
   ├─ TAB_PHASE_GATES['timeline'] = { partial: 'coreference', complete: 'coreference' }
   └─ isPhaseExecuted('coreference') = true
   └─ ✅ TICK aparece inmediatamente ❌ PROBLEMA

3. Usuario hace click en tab Timeline:
   └─ TimelineView.vue carga (línea 658)
   └─ loadTimeline() → api.getRaw('/api/projects/{id}/timeline')
   └─ ⏳ Backend construye timeline ON-DEMAND (chapters.py:395)
      ├─ Extrae marcadores temporales de cada capítulo
      ├─ Construye timeline con TimelineBuilder
      ├─ Identifica referencias cruzadas
      └─ Persiste eventos en BD
```

### Frontend (analysis.ts)

**Archivo**: `frontend/src/stores/analysis.ts`

```typescript
// Líneas 123-134
export const TAB_PHASE_GATES: Partial<Record<WorkspaceTab, {
  partial: keyof ExecutedPhases
  complete: keyof ExecutedPhases
}>> = {
  entities: { partial: 'entities', complete: 'attributes' },
  alerts: { partial: 'alerts_grammar', complete: 'alerts' },
  relationships: { partial: 'coreference', complete: 'coreference' },
  timeline: { partial: 'coreference', complete: 'coreference' },  // ❌ PROBLEMA
  // ...
}
```

**Problema**: El tab se marca como "completado" cuando la fase `coreference` termina, pero la timeline **NO se construye durante el análisis**, sino cuando el usuario accede al tab.

### Backend (Construcción On-Demand)

**Archivo**: `api-server/routers/chapters.py:395`

```python
@router.get("/api/projects/{project_id}/timeline", response_model=ApiResponse)
def get_project_timeline(project_id: int, force_refresh: bool = False):
    """
    Obtiene el timeline temporal del proyecto.

    Lee el timeline desde la base de datos si ya fue analizado.
    Solo recalcula si no hay datos o se fuerza el refresh.
    """
    # Línea 433: Verificar si hay datos en BD
    if not force_refresh and timeline_repo.has_timeline(project_id):
        # Lectura rápida desde BD

    # Línea 495-543: Si no hay datos, CONSTRUIR AHORA
    marker_extractor = TemporalMarkerExtractor()
    for chapter in chapters:
        chapter_markers = marker_extractor.extract(...)  # ⏳ Proceso largo

    builder = TimelineBuilder()
    timeline = builder.build_from_markers(all_markers, chapter_data)  # ⏳ Proceso largo
```

### Impacto

1. **UX confusa**: El usuario ve el tick verde pero al acceder al tab ve "Analizando marcadores temporales..."
2. **Expectativa incorrecta**: El tick sugiere que los datos están listos, pero la timeline se construye on-demand
3. **Primera carga lenta**: La primera vez que se accede al tab, hay un tiempo de espera significativo

### Solución Propuesta

**Opción A**: Construir timeline durante el análisis (agregar fase `timeline`)
- ✅ Tick refleja estado real
- ❌ Aumenta tiempo total de análisis
- ❌ Procesa datos que el usuario podría no ver

**Opción B**: Cambiar gate del tab a una fase específica de timeline
- Agregar fase `timeline` al pipeline
- Actualizar `TAB_PHASE_GATES['timeline'] = { partial: 'timeline', complete: 'timeline' }`
- ✅ Solución limpia
- ❌ Requiere agregar fase al pipeline

**Opción C** (RECOMENDADA): Mostrar estado "lazy loading" en el tab
- Cambiar el gate a `null` (sin fase requerida)
- El tab siempre está disponible pero muestra estado de carga interno
- ✅ No aumenta tiempo de análisis
- ✅ Refleja comportamiento real on-demand
- ✅ Cambio mínimo

```typescript
// analysis.ts
export const TAB_PHASE_GATES: Partial<Record<WorkspaceTab, {
  partial: keyof ExecutedPhases
  complete: keyof ExecutedPhases
}>> = {
  // ...
  // timeline: { partial: 'coreference', complete: 'coreference' },  // ❌ BEFORE
  // No gate para timeline → siempre disponible, muestra spinner interno
  // ...
}
```

---

## Otros Ticks Auditados

### ✅ chapters_found
- **Dónde**: `_analysis_phases.py:787` (final de `run_structure`)
- **Timing**: Después de persistir todos los capítulos y calcular métricas
- **Estado**: ✅ **CORRECTO** - No hay procesamiento posterior

### ✅ alerts_grammar / alerts (dos fases)
- **alerts_grammar**: Fase 8a (línea 2452+) - Alertas de gramática
- **alerts**: Fase 9 (línea 2821+) - Alertas de consistencia
- **Estado**: ✅ **CORRECTO** - Dos ticks secuenciales diseñados para carga incremental

## Plan de Implementación

### Fix 1: Entities Timing

1. **Backend**: Mover `entities_found` metric al final de `run_fusion()`
   - Archivo: `api-server/routers/_analysis_phases.py:1577` → ~1698
2. **Testing**: Verificar tests de integración
3. **Validación**: Confirmar tick después de MentionFinder

### Fix 2: Timeline Tab Status

**Implementar Opción C** (lazy loading):

1. **Frontend**: Remover gate de timeline en `analysis.ts`
   ```typescript
   // Línea 130: Comentar o eliminar
   // timeline: { partial: 'coreference', complete: 'coreference' },
   ```

2. **Tab siempre disponible**: Sin gate, el tab se muestra como "completed" siempre
3. **Spinner interno**: `TimelineView.vue:107-110` ya muestra loading state correctamente

**Alternativa** (si se prefiere agregar fase):
1. Agregar fase `timeline` al pipeline después de `coreference`
2. Extraer y persistir marcadores temporales durante análisis
3. Actualizar gate: `timeline: { partial: 'timeline', complete: 'timeline' }`

## Archivos Afectados

**Fix 1 (Entities)**:
- `api-server/routers/_analysis_phases.py:1577` → Mover a ~1698
- `tests/integration/test_pipeline.py` (verificar timing)

**Fix 2 (Timeline)**:
- `frontend/src/stores/analysis.ts:130` → Remover gate o actualizar
- `api-server/routers/chapters.py:395` → (sin cambios si opción C)
- `src/narrative_assistant/pipelines/ua_ner.py:370` → (agregar fase si alternativa)
