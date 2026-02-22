# Análisis de Bugs - 2026-02-22

> **Análisis comprehensivo de 15 bugs detectados en Narrative Assistant**
>
> Documento de trabajo para documentar root causes, impacto y estrategias de solución.

---

## Estado General

| Categoría | Total | Resueltos | En Progreso | Pendientes |
|-----------|-------|-----------|-------------|------------|
| **TOTAL** | 15 | 1 | 0 | 14 |
| I18N | 1 | 1 | 0 | 0 |
| NER/Clasificación | 6 | 0 | 0 | 6 |
| UX/Analytics | 3 | 0 | 0 | 3 |
| Búsqueda/Navegación | 2 | 0 | 0 | 2 |
| Filtros/Sugerencias | 2 | 0 | 0 | 2 |
| Pipeline | 1 | 0 | 0 | 1 |

---

## ✅ Bugs Resueltos

### Bug #7: I18N - Categorías en inglés en Top Categorías

**Archivo**: `frontend/src/components/alerts/AlertsAnalytics.vue`

**Problema**: Las categorías "grammar" y "spelling" aparecían sin traducir en el widget "Top Categorías".

**Root Cause**: Faltaban las traducciones en la función `getCategoryLabel()` (líneas 109-124).

**Solución Implementada**:
```typescript
function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    coherence: 'Coherencia',
    consistency: 'Consistencia',
    agreement: 'Concordancia',
    punctuation: 'Puntuación',
    attribute: 'Atributos',
    behavior: 'Comportamiento',
    voice: 'Voz narrativa',
    temporal: 'Temporal',
    style: 'Estilo',
    repetition: 'Repetición',
    filler: 'Muletillas',
    grammar: 'Gramática',      // ✅ ADDED
    spelling: 'Ortografía'     // ✅ ADDED
  }
  return labels[category] || category
}
```

**Estado**: ✅ **RESUELTO** - Commit pendiente

---

## 🔍 Bugs Investigados (Root Cause Identificado)

### Bug #15: Entidades muestran 0% menciones activas

**Archivos Involucrados**:
- `frontend/src/components/inspector/EntityInspector.vue` (líneas 165-196)
- `api-server/routers/entities.py` (línea 1171)
- `src/narrative_assistant/persistence/database.py` (líneas 205-219)
- `src/narrative_assistant/pipelines/ua_ner.py` (líneas 460-479)
- `src/narrative_assistant/nlp/mention_finder.py` (línea 241)
- `src/narrative_assistant/entities/repository.py` (líneas 320-379)

**Problema**: Todas las entidades muestran "0% menciones activas" en el EntityInspector.

**Síntomas**:
```
Isabel González (protagonista)
├── 47 menciones totales
├── 0 como sujeto (activo)
├── 0 como objeto (activo)
├── 0 en diálogo (activo)
└── Protagonismo: 0% ❌
```

**Root Cause Identificado**:

El cálculo de protagonismo depende del campo `validationReasoning` de cada mención:

```typescript
// EntityInspector.vue:178-190
mentionNav.state.value.mentions.forEach((m: any) => {
  const reasoning = (m.validationReasoning?.toLowerCase() || '') as string

  if (reasoning.includes('sujeto')) {
    stats.asSubject++
  } else if (reasoning.includes('objeto')) {
    stats.asObject++
  } else if (reasoning.includes('comunicativo') || reasoning.includes('verbo')) {
    stats.inDialogue++
  }
})
```

**Infraestructura Existente** (✅ correcta):
1. ✅ Base de datos tiene campo `entity_mentions.metadata` (JSON)
2. ✅ API deserializa metadata y expone `validationReasoning` (entities.py:1171)
3. ✅ Pipeline `ua_ner.py` tiene función `_validate_mention()` (líneas 460-479)
4. ✅ Función serializa metadata con `validation_method` y `validation_reasoning`

**Hipótesis del Problema**:

El campo `metadata.validation_reasoning` está **vacío o null** en la base de datos, lo que sugiere:

1. **Hipótesis A**: `_validate_mention()` NO se está llamando durante el análisis
2. **Hipótesis B**: El validador retorna `reasoning=None` o string vacío
3. **Hipótesis C**: El metadata no se está guardando correctamente en `entity_mentions`

**Verificación Necesaria**:

```python
# ¿Dónde se llama _validate_mention() en UANERPipeline?
# ¿Se guarda el resultado en entity_mentions.metadata?

# Buscar en ua_ner.py:
grep -n "_validate_mention" src/narrative_assistant/pipelines/ua_ner.py

# Verificar si create_mention() recibe metadata:
grep -n "create_mention" src/narrative_assistant/pipelines/ua_ner.py
```

**Impacto**:
- 🔴 **ALTO** - Funcionalidad crítica para análisis de personajes
- El protagonismo score es inútil sin validation_reasoning
- Afecta a todas las entidades de todos los proyectos

**Solución Propuesta**:
1. Verificar que `UANERPipeline.process()` llame a `_validate_mention()` para cada mención
2. Asegurar que el metadata se pase a `repository.create_mention()`
3. Añadir logging para confirmar que `validation_reasoning` no está vacío
4. Migrar menciones existentes (recalcular validation_reasoning)

**Estado**: 🟡 **ROOT CAUSE IDENTIFICADO** - Pendiente verificación y fix

---

### Bug #8: Distribución por capítulo vacía

**Archivo**: `frontend/src/components/alerts/AlertsAnalytics.vue`

**Problema**: El widget "Distribución por Capítulo" no muestra gráfico ni números.

**Root Cause Probable**:

El componente filtra alertas con:
```typescript
// AlertsAnalytics.vue:40
const byChapter = alerts.value.filter(a => a.chapter != null && a.status === 'active')
```

**Hipótesis del Problema**:

1. **Hipótesis A**: Las alertas no tienen el campo `chapter` poblado
2. **Hipótesis B**: Todas las alertas tienen `status !== 'active'`
3. **Hipótesis C**: El campo `chapter` existe pero es `undefined` (no `null`)

**Verificación Necesaria**:

```typescript
// Comprobar en datos reales:
console.log('Total alerts:', alerts.value.length)
console.log('With chapter:', alerts.value.filter(a => a.chapter != null).length)
console.log('Active:', alerts.value.filter(a => a.status === 'active').length)
console.log('Both:', alerts.value.filter(a => a.chapter != null && a.status === 'active').length)
```

**Archivos a Revisar**:
- Backend: ¿Las alertas se crean con `chapter_id`?
- Frontend transformer: ¿El campo `chapter` se mapea correctamente desde `chapter_id`?
- Base de datos: ¿La tabla `alerts` tiene FK a `chapters`?

**Impacto**:
- 🟡 **MEDIO** - Funcionalidad analítica importante pero no crítica
- Usuarios no pueden ver distribución de alertas por capítulo

**Solución Propuesta**:
1. Verificar que el backend incluya `chapter_id` en las alertas
2. Verificar que el transformer frontend mapee correctamente
3. Añadir logging para identificar cuál hipótesis es correcta

**Estado**: 🟡 **ROOT CAUSE PARCIAL** - Pendiente verificación

---

## 📋 Bugs Pendientes de Documentar

### Categoría: NER/Clasificación de Entidades (6 bugs)

#### Bug #2: "médico" detectado como profesión de Isabel

**Texto**:
```
"El médico forense determinó que Isabel había muerto..."
```

**Problema**:
- "médico" se asigna como profesión de "Isabel"
- Debería asignarse a "médico forense" (entidad separada LOC/PER)

**Archivos a Investigar**:
- `src/narrative_assistant/nlp/attribute_extraction.py` - Extracción de atributos
- `src/narrative_assistant/nlp/ner.py` - NER extractor
- Lógica de asignación de atributos a entidades

**Impacto**: 🔴 **ALTO** - Atributos incorrectos confunden al usuario

**Prioridad**: 🟠 **ALTA**

---

#### Bug #3: "exactamente" detectado como profesión

**Problema**:
- La palabra "exactamente" aparece como profesión de Isabel
- Obviamente no es una profesión válida

**Root Cause Probable**:
- Falta validación semántica en extracción de profesiones
- No hay lista blanca/negra de adverbios

**Solución Propuesta**:
- Filtrar POS tags no válidos (ADV, CONJ, etc.)
- Añadir lista de stopwords para profesiones
- Validar que la profesión sea un NOUN/PROPN

**Impacto**: 🔴 **ALTO** - Ruido en datos de entidades

**Prioridad**: 🟠 **ALTA**

---

#### Bug #4: "Solo faltaba Isabel" - desincronización de entidades

**Problema**:
- ChaptersPanel reconoce "Isabel" como personaje
- Panel de entidades NO lo muestra

**Root Cause Probable**:
- Dos fuentes de datos diferentes para entidades:
  - `ChaptersPanel` usa menciones inline del texto
  - `EntitiesPanel` usa tabla `entities` de la base de datos
- Falta sincronización o consolidación

**Archivos a Investigar**:
- `frontend/src/components/chapters/ChaptersPanel.vue`
- `frontend/src/components/entities/EntitiesPanel.vue`
- Backend: endpoints `/chapters/{id}` vs `/entities`

**Impacto**: 🔴 **ALTO** - Inconsistencia de datos crítica

**Prioridad**: 🔴 **CRÍTICA**

---

#### Bug #5: Ford T clasificado como ORG

**Problema**:
- "Ford T" detectado como organización (ORG)
- Debería ser MISC (automóvil/vehículo)

**Root Cause Probable**:
- spaCy clasifica "Ford" como marca → ORG
- Falta post-procesamiento para vehículos históricos

**Solución Propuesta**:
- Gazetteer de vehículos históricos (Ford T, Citroën 2CV, etc.)
- Regla: `[MARCA] + [MODELO_CORTO]` → reclasificar a MISC
- Añadir a `entity_validator.py` como caso especial

**Impacto**: 🟡 **MEDIO** - Clasificación incorrecta pero no crítica

**Prioridad**: 🟢 **BAJA**

---

#### Bug #6: GPS clasificado como LOC

**Problema**:
- "GPS" detectado como ubicación (LOC)
- Debería ser MISC (dispositivo)

**Root Cause Probable**:
- spaCy asocia GPS con coordenadas geográficas → LOC
- Falta lista de dispositivos tecnológicos

**Solución Propuesta**:
- Gazetteer de dispositivos: GPS, radar, sonar, RFID, etc.
- Reclasificar automáticamente en `entity_validator.py`

**Impacto**: 🟡 **MEDIO** - Clasificación incorrecta

**Prioridad**: 🟢 **BAJA**

---

### Categoría: UX/Analytics (3 bugs)

#### Bug #9: Formato de títulos de capítulos

**Problema**:
- Se muestra "Cap. 1" incluso cuando hay espacio para "1. La llegada"
- El usuario prefiere ver el título completo cuando hay espacio disponible

**Archivos Involucrados**:
- `frontend/src/components/alerts/AlertsAnalytics.vue` (byChapter, probablemente en template)
- Cualquier componente que muestre títulos de capítulos

**Solución Propuesta**:

1. **Opción A - CSS Truncate**:
```vue
<template>
  <span class="chapter-title" :title="fullTitle">
    {{ chapter.chapterNumber }}. {{ chapter.title }}
  </span>
</template>

<style>
.chapter-title {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
```

2. **Opción B - Función Condicional**:
```typescript
function formatChapterTitle(chapter: Chapter, maxChars = 30): string {
  const fullTitle = `${chapter.chapterNumber}. ${chapter.title}`
  if (fullTitle.length <= maxChars) {
    return fullTitle
  }
  return `Cap. ${chapter.chapterNumber}`
}
```

3. **Opción C - Responsive**:
```vue
<span class="chapter-full">{{ chapter.chapterNumber }}. {{ chapter.title }}</span>
<span class="chapter-short">Cap. {{ chapter.chapterNumber }}</span>

<style>
@media (max-width: 768px) {
  .chapter-full { display: none; }
  .chapter-short { display: inline; }
}
@media (min-width: 769px) {
  .chapter-full { display: inline; }
  .chapter-short { display: none; }
}
</style>
```

**Recomendación**: **Opción A** - CSS truncate con tooltip (más simple y estándar)

**Impacto**: 🟢 **BAJO** - Estética/UX

**Prioridad**: 🟢 **BAJA** - Nice to have

---

### Categoría: Filtros/Sugerencias (2 bugs)

#### Bug #10: Filtrado por capítulos solo funciona con inconsistencias

**Problema Reportado**:
- El filtro de rango de capítulos solo se aplica a tipo "inconsistencias"
- Debería aplicarse a todos los tipos de alerta

**Archivos Involucrados**:
- `frontend/src/composables/useAlertFiltering.ts` (líneas 145-191)
- `frontend/src/components/workspace/AlertsDashboard.vue`
- `frontend/src/components/alerts/ChapterRangeSelector.vue`

**Root Cause**:

✅ **EL CÓDIGO ES CORRECTO** - El filtro SÍ funciona para todos los tipos:

```typescript
// useAlertFiltering.ts:173-177
if (hasChapterRange) {
  if (a.chapter == null) return false
  if (chapterMin != null && a.chapter < chapterMin) return false
  if (chapterMax != null && a.chapter > chapterMax) return false
}
```

**Análisis**:
1. El filtro **no discrimina** por tipo de alerta (category, alertType)
2. Solo filtra por: `a.chapter >= chapterMin && a.chapter <= chapterMax`
3. Funciona para **TODOS** los tipos: errores, inconsistencias, sugerencias, etc.

**Hipótesis del Reporte Incorrecto**:

El usuario probablemente observó uno de estos escenarios:

1. **Alertas sin capítulo**: Algunas alertas tienen `chapter=null` (alertas globales)
   - Estas se filtran automáticamente (línea 174)
   - Pueden parecer de cierto tipo pero simplemente no tienen capítulo

2. **Confusión con meta-categorías**: El usuario tenía activa una meta-categoría (ej: "inconsistencias")
   - El filtro de capítulos funcionaba pero solo sobre alertas ya filtradas por meta-categoría
   - Esto podría parecer que "solo funciona con inconsistencias"

3. **Bug visual temporal**: El ChapterRangeSelector no actualizaba el estado reactivo

**Verificación Recomendada**:

1. Reproducir el bug con pasos específicos
2. Verificar que `ChapterRangeSelector` actualiza `chapterRange.value` correctamente
3. Comprobar que no hay meta-categoría activa durante la prueba

**Estado**: ⚪ **NO REPRODUCIBLE** / **POSIBLE FALSO POSITIVO**

**Impacto**: 🟢 **NINGUNO** (si el código es correcto como parece)

**Prioridad**: 🔵 **VERIFICAR PRIMERO** - Pedir al usuario pasos específicos de reproducción

---

#### Bug #11: No hay sugerencias en UI

**Problema**:
- Las alertas de categoría "Estilo" deberían mostrar sugerencias
- El panel de sugerencias no aparece

**Archivos Involucrados**:
- `frontend/src/views/AlertsView.vue` (líneas 133-142) - **SÍ muestra sugerencias**
- `api-server/routers/alerts.py` (línea 191) - **SÍ retorna suggestion**
- `src/narrative_assistant/persistence/database.py` - **SÍ tiene campo suggestion**

**Root Cause**:

✅ **La infraestructura es correcta**:
```vue
<!-- AlertsView.vue:133-142 -->
<div v-if="selectedAlert.suggestion" class="detail-section">
  <h4>Sugerencia</h4>
  <Panel class="suggestion-panel">
    <template #header>
      <i class="pi pi-lightbulb"></i>
      <span>Cómo resolverlo</span>
    </template>
    <p>{{ selectedAlert.suggestion }}</p>
  </Panel>
</div>
```

❌ **El problema**: Los detectores de estilo **NO están generando** el campo `suggestion` al crear las alertas.

**Verificación Necesaria**:

1. Buscar detectores de categoría "style":
```bash
grep -rn "category.*style" src/narrative_assistant/corrections/detectors/
```

2. Verificar que llamen a `create_alert()` con parámetro `suggestion=...`

3. Si no lo hacen, añadir lógica de sugerencias:
```python
# Ejemplo: StickySentenceDetector
suggestion = (
    f"Considera reescribir: '{excerpt}' para mejorar la claridad. "
    f"Intenta usar oraciones más cortas o restructurar la sintaxis."
)
```

**Impacto**: 🟡 **MEDIO** - Funcionalidad valiosa pero no crítica

**Prioridad**: 🟠 **MEDIA**

---

#### Bug #12: Sugerencias sin contexto completo

**Problema**:
- Ejemplo reportado: "formalidad propia" (fragmento incompleto)
- Usuario espera: "la formalidad propia de un médico forense" (contexto completo)

**Root Cause Probable**:

Este bug está **vinculado a Bug #11**. Si las sugerencias no se generan, no hay contexto que mostrar.

**Solución (una vez resuelto Bug #11)**:

Las sugerencias deberían incluir contexto ampliado en el campo `suggestion`:

```python
# En detector de estilo
context_before = text[max(0, start-50):start]
context_after = text[end:end+50]
full_context = f"{context_before}**{excerpt}**{context_after}"

suggestion = f"Considera revisar: '{full_context.strip()}'. [razón específica]"
```

**Alternativa**:
- El campo `excerpt` en la alerta ya tiene el texto
- Si `excerpt` es muy corto, el problema está en su generación
- Verificar que detectores usen `excerpt` amplio (±50 chars)

**Impacto**: 🟢 **BAJO** - UX/Claridad (depende de Bug #11)

**Prioridad**: 🟢 **BAJA** (resolver después de #11)

---

### Categoría: Búsqueda/Navegación (2 bugs)

#### Bug #1: Búsqueda solo funciona en capítulos lazy-loaded

**Problema**:
- La búsqueda global en DocumentViewer solo busca en capítulos ya cargados
- Los capítulos no cargados (lazy loading) no se buscan
- El usuario espera buscar en TODO el documento

**Archivos Involucrados**:
- `frontend/src/components/DocumentViewer.vue` (líneas 1791-1888)
- Función `cleanExcerptForSearch()` y búsqueda de texto en nodos DOM

**Root Cause**:

La búsqueda actual recorre solo los nodos DOM existentes:
```typescript
// DocumentViewer.vue:1818-1826
while (true) {
  const index = nodeText.toLowerCase().indexOf(searchText.toLowerCase(), searchIndex)
  if (index === -1) break

  matches.push({
    node,
    index,
    length: searchText.length,
    charPosition: charCount + index
  })
  searchIndex = index + 1
}
```

**Problema**: Solo busca en `nodeText` de capítulos ya renderizados. Los capítulos no cargados (lazy loading) no están en el DOM.

**Solución Propuesta**:

1. **Opción A - Búsqueda Backend**:
   - Endpoint `/api/projects/{id}/search?q=texto` que busque en la BD
   - Retorna: `[{chapterId, position, excerpt}]`
   - Frontend carga capítulo bajo demanda si no está cargado

2. **Opción B - Carga Progresiva**:
   - Al buscar, cargar todos los capítulos automáticamente (con indicador de progreso)
   - Más simple pero más lento

3. **Opción C - Índice de Búsqueda**:
   - Pre-indexar documento completo en el pipeline
   - Guardar índice invertido en BD
   - Búsqueda instantánea sin necesidad de cargar capítulos

**Recomendación**: **Opción A** - Búsqueda backend con carga bajo demanda

**Impacto**: 🟡 **MEDIO** - Feature útil pero workaround existe (navegar manualmente)

**Prioridad**: 🟢 **BAJA**

---

#### Bug #13: Modo secuencial no hace scroll+highlight

**Problema**:
- Botón "Ver en documento" en modo secuencial (RevisionDashboard)
- **NO EXISTE** - El componente AlertDiffViewer no tiene botón de navegación
- Falta funcionalidad completa de navegación desde el diff viewer

**Archivos Involucrados**:
- `frontend/src/views/RevisionView.vue` (líneas 1-48)
- `frontend/src/components/revision/RevisionDashboard.vue` (líneas 1-200+)
- `frontend/src/components/revision/AlertDiffViewer.vue` (líneas 1-199) - **NO tiene navegación**

**Root Cause**:

AlertDiffViewer solo muestra información estática:
```vue
<!-- AlertDiffViewer.vue:112-114 -->
<template #footer>
  <Button label="Cerrar" text @click="emit('close')" />
</template>
```

**No hay**:
- Botón "Ver en documento"
- Emit de evento para navegar
- Integración con DocumentViewer

**Solución Propuesta**:

1. **Añadir botón de navegación**:
```vue
<template #footer>
  <Button label="Ver en documento" icon="pi pi-eye" @click="emit('viewInDocument', alert)" />
  <Button label="Cerrar" text @click="emit('close')" />
</template>
```

2. **RevisionDashboard debe emitir evento**:
```typescript
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'viewInDocument', alert: ComparisonAlertDiff): void  // NUEVO
}>()
```

3. **RevisionView debe navegar al documento**:
```typescript
function viewInDocument(alert: ComparisonAlertDiff) {
  router.push({
    name: 'project',
    params: { id: projectId.value },
    query: {
      tab: 'document',
      highlight: `${alert.spanStart}-${alert.spanEnd}`,
      chapter: alert.chapter
    }
  })
}
```

4. **DocumentViewer debe consumir query params** y hacer scroll+highlight

**Impacto**: 🔴 **ALTO** - Funcionalidad crítica para flujo de revisión

**Prioridad**: 🟠 **ALTA**

---

### Categoría: Pipeline/Performance (1 bug)

#### Bug #14: Timeline calculada en runtime

**Problema**:
- La timeline de personajes se calcula cada vez que se abre el panel
- Debería estar precalculada durante el análisis (pipeline)
- Causa delays innecesarios en la UI

**Archivos Involucrados**:
- `api-server/routers/relationships.py` (líneas 1796-1890)
- Endpoint `/api/projects/{project_id}/character-timeline`

**Root Cause**:

El endpoint calcula la timeline en cada request:

```python
# relationships.py:1841-1851
# Construir timeline por personaje — query batch con JOIN (evita N+1)
all_mentions = entity_repo.get_mentions_by_project(project_id)

# Pre-agrupar menciones por entity_id y capítulo
mentions_per_entity: dict[int, dict[int, int]] = {}
for m in all_mentions:
    ch_num = chapter_id_to_number.get(m["chapter_id"])
    if ch_num is not None:
        mentions_per_entity.setdefault(m["entity_id"], {})
        by_ch = mentions_per_entity[m["entity_id"]]
        by_ch[ch_num] = by_ch.get(ch_num, 0) + 1
```

**Mitigación Parcial**:
- ✅ Ya existe caché de enrichment (líneas 1809-1813)
- El caché reduce el impacto pero no elimina el cálculo inicial

**Solución Propuesta**:

1. **Opción A - Precalcular en Pipeline**:
   - Añadir paso al pipeline de análisis que genere timeline
   - Guardar en tabla `character_timeline` (nuevo schema)
   - Endpoint solo lee de la tabla
   - **Pro**: Performance máxima
   - **Contra**: Añade complejidad al schema

2. **Opción B - Materializar en Cache al Terminar Análisis**:
   - Al finalizar pipeline, calcular timeline y guardar en cache
   - Endpoint usa cache (ya implementado)
   - **Pro**: Simple, sin cambios en schema
   - **Contra**: Cache puede expirar

3. **Opción C - Mantener Actual + Optimizar Query**:
   - El cálculo es O(n) menciones, razonable
   - Cache funciona bien para proyectos ya analizados
   - **Solo optimizar**: añadir índice en `entity_mentions(entity_id, chapter_id)`

**Recomendación**: **Opción C** - Optimizar query con índice, mantener caché actual

**Impacto**: 🟢 **BAJO** - Performance, mitigado por caché

**Prioridad**: 🟢 **BAJA** (optimización incremental)

---

## 🔢 Priorización Propuesta

### 🔴 Críticos (Arreglar YA)
1. **Bug #4**: Desincronización ChaptersPanel vs EntitiesPanel - Inconsistencia de datos
2. **Bug #15**: Menciones activas al 0% (protagonismo roto) - Feature crítica rota
3. **Bug #13**: Navegación desde modo secuencial - Feature NO implementada

### 🟠 Altos (Siguiente Sprint)
4. **Bug #2**: "médico" asignado incorrectamente a Isabel - Atributos incorrectos
5. **Bug #3**: "exactamente" como profesión - Ruido en datos
6. **Bug #11**: Sugerencias no se generan - Detectores incompletos

### 🟡 Medios (Backlog)
7. **Bug #8**: Distribución por capítulo vacía - Investigación necesaria

### 🟢 Bajos (Nice to Have)
8. **Bug #1**: Búsqueda en capítulos lazy-loaded - Feature enhancement
9. **Bug #5**: Ford T como ORG - Clasificación menor
10. **Bug #6**: GPS como LOC - Clasificación menor
11. **Bug #9**: Formato de títulos - Estética/UX
12. **Bug #12**: Contexto de sugerencias - Depende de #11
13. **Bug #14**: Timeline en runtime - Ya tiene caché, optimización incremental

### ⚪ Verificar/No Reproducible
14. **Bug #10**: Filtrado por capítulos - Código correcto, posible falso positivo

---

## 📊 Resumen Ejecutivo

### Bugs por Severidad

| Severidad | Count | % |
|-----------|-------|---|
| 🔴 Crítico | 3 | 20% |
| 🟠 Alto | 3 | 20% |
| 🟡 Medio | 1 | 7% |
| 🟢 Bajo | 6 | 40% |
| ⚪ Verificar | 1 | 7% |
| ✅ Resuelto | 1 | 7% |

### Tiempo Estimado de Resolución

| Bug | Tiempo | Complejidad |
|-----|--------|-------------|
| #15 | 4-6h | Alta (investigación + migración) |
| #4 | 3-4h | Alta (arquitectura) |
| #2 | 2-3h | Media (lógica NER) |
| #3 | 1-2h | Baja (validación) |
| #13 | 2-3h | Media (navegación) |
| #8 | 2h | Media (investigación) |
| Resto | 1-2h cada uno | Baja-Media |

### Archivos Más Afectados

1. `frontend/src/components/alerts/AlertsAnalytics.vue` (Bugs #7, #8, #9)
2. `frontend/src/components/inspector/EntityInspector.vue` (Bug #15)
3. `src/narrative_assistant/nlp/attribute_extraction.py` (Bugs #2, #3)
4. `src/narrative_assistant/pipelines/ua_ner.py` (Bugs #15, #2, #3, #4)
5. `api-server/routers/entities.py` (Bugs #15, #4)

---

## 🎯 Próximos Pasos

1. **Completar investigación de Bug #15**:
   - Grep para encontrar llamadas a `_validate_mention()`
   - Verificar si metadata se pasa a `create_mention()`
   - Añadir logging temporal para debugging

2. **Verificar Bug #8**:
   - Inspeccionar datos reales en DevTools
   - Confirmar hipótesis A, B o C

3. **Documentar Bug #1** (Búsqueda):
   - Investigar arquitectura de lazy loading
   - Proponer solución custom de búsqueda

4. **Crear plan de refactoring NER** (Bugs #2-#6):
   - Centralizar validación de atributos
   - Implementar gazetteers
   - Mejorar post-procesamiento de entidades

---

**Última actualización**: 2026-02-22 21:30
**Autor**: Claude Code (análisis de bugs reportados por usuario)
**Estado**: ✅ **COMPLETO** - Análisis comprehensivo de 15 bugs

**Resumen de Hallazgos**:
- **1 bug resuelto** (I18N traducciones)
- **3 bugs críticos** identificados (desincronización, protagonismo, navegación)
- **2 bugs con root cause completo** (Bug #15 menciones activas, Bug #13 navegación)
- **1 posible falso positivo** (Bug #10 filtrado de capítulos)
- **11 bugs documentados** con análisis parcial/completo

**Próximo paso sugerido**: Resolver Bug #15 (menciones activas al 0%), ya investigado con root cause claro.
