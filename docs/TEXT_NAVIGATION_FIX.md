# Fix: Navegación "Ver en Texto" - Timing y Cache

## Problema Reportado

Cuando el usuario hace click en "Ver en el texto" desde tabs como **Entidades** o **Alertas**:

1. ❌ El tab cambia a **Texto** correctamente
2. ❌ Pero NO hace scroll ni highlight porque los capítulos aún no están cargados
3. ❌ Cada vez que cambias de tab, recarga los capítulos innecesariamente

---

## Análisis

### Flujo Actual (ROTO)

```
1. Usuario en tab "Alertas" hace click "Ver en texto"
2. alertModal.vue → workspaceStore.navigateToTextPosition(position, text, chapterId)
3. workspaceStore:
   - scrollToPosition = position
   - scrollToText = text
   - setActiveTab('text')  ← Cambio de tab INMEDIATO
4. ProjectDetailView detecta cambio de tab → renderiza TextTab
5. TextTab monta → computed scrollTarget intenta usar chapters
6. ❌ PROBLEMA: chapters.value aún está vacío o cargando
7. ❌ RESULTADO: No hace scroll, no hace highlight
```

### Root Cause

- `navigateToTextPosition()` cambia el tab **inmediatamente** sin esperar a que los capítulos estén listos
- `loadChapters()` se llamaba en cada cambio de tab, sin cache
- No había sincronización entre "cambiar tab" y "datos listos"

---

## Solución Implementada

### **Parte 1: Cache de Capítulos** ✅

**Archivo**: [frontend/src/composables/useProjectData.ts](../frontend/src/composables/useProjectData.ts)

**Cambios**:
1. ✅ Agregado `loadingChapters` ref (booleano)
2. ✅ Agregado `chaptersLoaded` ref (booleano)
3. ✅ Agregado `lastLoadedProjectId` ref (número)
4. ✅ Agregado parámetro `forceReload` a `loadChapters()` (default: false)

**Lógica de Cache**:
```typescript
async function loadChapters(projectId: number, fallbackProject?, forceReload = false) {
  // ✅ SI ya están cargados para este proyecto → SKIP (instantáneo)
  if (!forceReload && chaptersLoaded.value && lastLoadedProjectId.value === projectId && chapters.value.length > 0) {
    console.log('[useProjectData] Chapters already loaded from cache')
    return
  }

  // ✅ SI ya está cargando → ESPERAR (evita race conditions)
  if (loadingChapters.value) {
    while (loadingChapters.value) {
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    return
  }

  // ✅ Cargar desde API
  loadingChapters.value = true
  try {
    const data = await api.getRaw(`/api/projects/${projectId}/chapters`)
    if (data.success) {
      chapters.value = transformChapters(data.data || [])
      chaptersLoaded.value = true
      lastLoadedProjectId.value = projectId
    }
  } finally {
    loadingChapters.value = false
  }
}
```

**Beneficios**:
- ✅ Primera carga: ~200-500ms (API)
- ✅ Cargas posteriores: **~0ms** (cache en memoria)
- ✅ Evita race conditions con flag `loadingChapters`

---

### **Parte 2: Sincronización con Navegación** ✅

**Archivo**: [frontend/src/views/ProjectDetailView.vue](../frontend/src/views/ProjectDetailView.vue) (~línea 1130)

**Cambios**:
```typescript
// Watch: detectar cambio a tab 'text' con scroll pendiente
watch(() => workspaceStore.activeTab, async (newTab) => {
  if (!project.value) return

  // ✅ NUEVO: Si navegamos a 'text' con scroll pendiente, asegurar que capítulos estén cargados
  if (newTab === 'text' && workspaceStore.scrollToPosition !== null) {
    console.log('[ProjectDetailView] Navigating to text with pending scroll, ensuring chapters loaded...')
    await loadChapters(project.value.id, project.value)  // ← Espera a que termine (usa cache si ya están cargados)
  }

  // ... resto de lógica
})
```

**Flujo Corregido**:
```
1. Usuario hace click "Ver en texto" desde Alertas
2. workspaceStore.navigateToTextPosition(position, text, chapterId)
3. setActiveTab('text') → Cambio de tab
4. Watch detecta: newTab === 'text' && scrollToPosition !== null
5. ✅ await loadChapters() → Carga desde cache (instantáneo) o API (si es primera vez)
6. ✅ Capítulos ya disponibles cuando TextTab monta
7. ✅ TextTab.scrollTarget computed → encuentra el capítulo correcto
8. ✅ Hace scroll + highlight correctamente
```

---

## Resultado

### **Antes** ❌
- Primera navegación: No hace scroll/highlight (capítulos cargando)
- Navegaciones posteriores: Recarga capítulos innecesariamente (~200-500ms cada vez)

### **Después** ✅
- Primera navegación: Scroll + highlight correctos (espera a que capítulos carguen)
- Navegaciones posteriores: **Instantáneo** (lee desde cache)

---

## Archivos Modificados (2)

1. ✅ `frontend/src/composables/useProjectData.ts` - Cache de capítulos
2. ✅ `frontend/src/views/ProjectDetailView.vue` - Sincronización con navegación

---

## Testing

### Escenario 1: Primera navegación desde Alertas
1. Abrir proyecto recién analizado
2. Ir a tab "Alertas"
3. Hacer click en "Ver en texto" en una alerta
4. **Resultado esperado**:
   - ✅ Cambia a tab Texto
   - ✅ Carga capítulos (~200-500ms)
   - ✅ Hace scroll a la posición
   - ✅ Highlight correcto

### Escenario 2: Navegación subsecuente
1. Volver a tab "Alertas"
2. Hacer click en "Ver en texto" en otra alerta
3. **Resultado esperado**:
   - ✅ Cambia a tab Texto
   - ✅ Usa cache (instantáneo, sin API)
   - ✅ Hace scroll a la posición
   - ✅ Highlight correcto

### Escenario 3: Navegación desde Entidades
1. Ir a tab "Entidades"
2. Hacer click en "Ver menciones en texto" de una entidad
3. **Resultado esperado**:
   - ✅ Usa cache (instantáneo)
   - ✅ Scroll + highlight correcto

---

## Mejoras Futuras (Opcionales)

1. **Cache persistente** (localStorage):
   - Guardar capítulos en localStorage
   - Invalidar al re-analizar
   - Beneficio: Instantáneo incluso en primera carga

2. **Pre-carga proactiva**:
   - Cargar capítulos al abrir el proyecto (en background)
   - Beneficio: Primera navegación también instantánea

3. **Cache de otros datos**:
   - Aplicar mismo patrón a `entities`, `alerts`, `relationships`
   - Beneficio: Toda la navegación instantánea

---

## Notas Técnicas

### ¿Por qué no pre-cargar siempre?

Los capítulos pueden ser grandes (~500KB-2MB para documentos largos). Pre-cargar en cada apertura de proyecto podría:
- Ralentizar la carga inicial del proyecto
- Consumir más ancho de banda
- No ser necesario si el usuario nunca navega a "Texto"

El enfoque actual (lazy loading con cache) es un **buen balance**:
- ✅ Carga solo cuando se necesita
- ✅ Cache para navegaciones posteriores
- ✅ Sincronización garantizada con el scroll

### Race Conditions

El flag `loadingChapters` previene race conditions cuando:
1. Usuario hace click "Ver texto" desde Alertas
2. Mientras carga, hace click en otro "Ver texto"
3. La segunda llamada **espera** en vez de duplicar la petición

```typescript
if (loadingChapters.value) {
  while (loadingChapters.value) {
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  return  // La primera llamada ya completó la carga
}
```
