# Frontend - Stores y Types

Ubicación: `frontend/src/stores/` y `frontend/src/types/`

## Types (`types/index.ts`)

### Interface `ApiResponse<T>`

```typescript
interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}
```

### Interface `Project`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID del proyecto |
| `name` | `string` | Nombre |
| `description` | `string?` | Descripción |
| `document_path` | `string?` | Ruta del documento |
| `document_format` | `string` | Formato (docx, txt, etc.) |
| `created_at` | `string` | Fecha creación (ISO) |
| `last_modified` | `string` | Última modificación (ISO) |
| `last_opened` | `string?` | Última apertura (ISO) |
| `analysis_progress` | `number` | Progreso 0-100 |
| `word_count` | `number` | Palabras totales |
| `chapter_count` | `number` | Capítulos detectados |
| `entity_count` | `number?` | Entidades detectadas |
| `open_alerts_count` | `number?` | Alertas abiertas |
| `highest_alert_severity` | `AlertSeverity?` | Severidad máxima |

### Interface `Entity`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID de la entidad |
| `project_id` | `number` | ID del proyecto |
| `entity_type` | `EntityType` | Tipo de entidad |
| `canonical_name` | `string` | Nombre canónico |
| `aliases` | `string[]` | Lista de alias |
| `importance` | `EntityImportance` | Importancia |
| `description` | `string?` | Descripción |
| `first_mention_chapter` | `number?` | Capítulo primera mención |
| `first_mention_position` | `number?` | Posición primera mención |
| `mention_count` | `number` | Número de menciones |
| `created_at` | `string?` | Fecha creación |
| `updated_at` | `string?` | Última modificación |

### Type `EntityType`

```typescript
type EntityType =
  | 'CHARACTER'
  | 'LOCATION'
  | 'ORGANIZATION'
  | 'OBJECT'
  | 'EVENT'
  | 'ANIMAL'
  | 'CREATURE'
  | 'BUILDING'
  | 'REGION'
  | 'VEHICLE'
  | 'FACTION'
  | 'FAMILY'
  | 'TIME_PERIOD'
  | 'CONCEPT'
  | 'RELIGION'
  | 'MAGIC_SYSTEM'
  | 'WORK'
  | 'TITLE'
  | 'LANGUAGE'
```

### Type `EntityImportance`

```typescript
type EntityImportance = 'critical' | 'high' | 'medium' | 'low' | 'minimal'
```

### Interface `Alert`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID de la alerta |
| `project_id` | `number` | ID del proyecto |
| `category` | `AlertCategory` | Categoría |
| `severity` | `AlertSeverity` | Severidad |
| `alert_type` | `string` | Tipo específico |
| `title` | `string` | Título |
| `description` | `string` | Descripción |
| `explanation` | `string` | Explicación detallada |
| `suggestion` | `string?` | Sugerencia |
| `chapter` | `number?` | Capítulo |
| `position_start` | `number?` | Posición inicio |
| `position_end` | `number?` | Posición fin |
| `status` | `AlertStatus` | Estado |
| `entity_ids` | `number[]?` | IDs entidades relacionadas |
| `entities` | `Entity[]?` | Entidades relacionadas |
| `created_at` | `string` | Fecha creación |
| `updated_at` | `string?` | Última modificación |
| `resolved_at` | `string?` | Fecha resolución |

### Types de Alert

```typescript
type AlertSeverity = 'critical' | 'warning' | 'info' | 'hint'
type AlertStatus = 'open' | 'dismissed' | 'resolved' | 'false_positive'
type AlertCategory = 'consistency' | 'continuity' | 'character' | 'timeline' | 'other'
```

### Interface `Chapter`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID del capítulo |
| `project_id` | `number` | ID del proyecto |
| `title` | `string` | Título |
| `content` | `string` | Contenido |
| `chapter_number` | `number` | Número (1-indexed) |
| `word_count` | `number` | Palabras |
| `position_start` | `number` | Posición inicio |
| `position_end` | `number` | Posición fin |
| `structure_type` | `string?` | Tipo de estructura |

### Interface `CharacterSheet`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `entity_id` | `number` | ID de la entidad |
| `canonical_name` | `string` | Nombre canónico |
| `aliases` | `string[]` | Alias |
| `importance` | `EntityImportance` | Importancia |
| `attributes` | `CharacterAttribute[]` | Atributos |
| `relationships` | `CharacterRelationship[]?` | Relaciones |
| `first_mention_chapter` | `number?` | Primer capítulo |
| `mention_count` | `number` | Menciones |

---

## Store: `useProjectsStore` (`stores/projects.ts`)

```typescript
import { useProjectsStore } from '@/stores/projects'

const projectsStore = useProjectsStore()
```

### State

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `projects` | `Ref<Project[]>` | Lista de proyectos |
| `currentProject` | `Ref<Project \| null>` | Proyecto actual |
| `loading` | `Ref<boolean>` | Cargando |
| `error` | `Ref<string \| null>` | Error actual |

### Getters

| Getter | Tipo | Descripción |
|--------|------|-------------|
| `projectCount` | `ComputedRef<number>` | Total proyectos |
| `hasProjects` | `ComputedRef<boolean>` | Tiene proyectos |
| `recentProjects` | `ComputedRef<Project[]>` | 5 más recientes |

### Actions

| Método | Firma | Descripción |
|--------|-------|-------------|
| `fetchProjects` | `() => Promise<void>` | Carga todos los proyectos |
| `fetchProject` | `(id: number) => Promise<void>` | Carga un proyecto específico |
| `createProject` | `(name: string, description?: string, file?: File) => Promise<Project>` | Crea proyecto |
| `clearError` | `() => void` | Limpia el error |
| `clearCurrentProject` | `() => void` | Limpia proyecto actual |

---

## Store: `useAnalysisStore` (`stores/analysis.ts`)

```typescript
import { useAnalysisStore } from '@/stores/analysis'

const analysisStore = useAnalysisStore()
```

### Interface `AnalysisProgress`

```typescript
interface AnalysisProgress {
  project_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number  // 0-100
  current_phase: string
  current_action?: string
  phases: Array<{
    id: string
    name: string
    completed: boolean
    current: boolean
    duration?: number
  }>
  metrics?: {
    chapters_found?: number
    entities_found?: number
    word_count?: number
    alerts_generated?: number
  }
  estimated_seconds_remaining?: number
  error?: string
}
```

### State

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `currentAnalysis` | `Ref<AnalysisProgress \| null>` | Análisis actual |
| `isAnalyzing` | `Ref<boolean>` | En progreso |
| `error` | `Ref<string \| null>` | Error actual |

### Getters

| Getter | Tipo | Descripción |
|--------|------|-------------|
| `hasActiveAnalysis` | `ComputedRef<boolean>` | Hay análisis activo |
| `progressPercentage` | `ComputedRef<number>` | Porcentaje 0-100 |

### Actions

| Método | Firma | Descripción |
|--------|-------|-------------|
| `startAnalysis` | `(projectId: number, file?: File) => Promise<boolean>` | Inicia análisis |
| `getProgress` | `(projectId: number) => Promise<AnalysisProgress \| null>` | Obtiene progreso |
| `clearAnalysis` | `() => void` | Limpia estado |
| `clearError` | `() => void` | Limpia error |

---

## Store: `useAppStore` (`stores/app.ts`)

```typescript
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
```

### State

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `backendConnected` | `Ref<boolean>` | Backend conectado |
| `backendVersion` | `Ref<string \| null>` | Versión del backend |
| `loading` | `Ref<boolean>` | Cargando |
| `error` | `Ref<string \| null>` | Error actual |
| `theme` | `Ref<'light' \| 'dark' \| 'auto'>` | Tema |
| `isDark` | `Ref<boolean>` | Modo oscuro activo |
| `themePreset` | `Ref<ThemePreset>` | Preset de tema |

### Types de Tema (exportados en `@/types`)

```typescript
import type { ThemeMode, ThemePreset } from '@/types'

type ThemeMode = 'light' | 'dark' | 'auto'
type ThemePreset = 'vscode' | 'obsidian' | 'notion' | 'material' | 'slack' | 'github' | 'spotify' | 'linear'
```

### Getters

| Getter | Tipo | Descripción |
|--------|------|-------------|
| `isReady` | `ComputedRef<boolean>` | Backend listo |

### Actions

| Método | Firma | Descripción |
|--------|-------|-------------|
| `checkBackendHealth` | `() => Promise<void>` | Verifica backend |
| `clearError` | `() => void` | Limpia error |
| `setTheme` | `(theme: 'light' \| 'dark' \| 'auto') => void` | Establece tema |
| `toggleTheme` | `() => void` | Alterna tema |
| `setThemePreset` | `(preset: ThemePreset) => void` | Establece preset |

---

## Store: `useSystemStore` (`stores/system.ts`)

**NOTA**: Este store tiene funcionalidad duplicada con `useAppStore`. Se recomienda usar `useAppStore` para verificar el backend ya que usa rutas relativas (`/api/health`) en lugar de URLs hardcodeadas.

```typescript
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
```

### State

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `backendConnected` | `Ref<boolean>` | Backend conectado |
| `backendVersion` | `Ref<string>` | Versión del backend (default: "unknown") |

### Actions

| Método | Firma | Descripción |
|--------|-------|-------------|
| `checkBackendStatus` | `() => Promise<void>` | Verifica estado (URL hardcodeada: localhost:8008) |

**Diferencias con `useAppStore`:**
- `useSystemStore.checkBackendStatus()` usa URL hardcodeada `http://localhost:8008/api/health`
- `useAppStore.checkBackendHealth()` usa ruta relativa `/api/health` (recomendado)

---

## Errores Comunes

### Error: Acceder a store fuera de setup

**Incorrecto:**
```typescript
// En módulo sin contexto Vue
const store = useProjectsStore()  // Error!
```

**Correcto:**
```typescript
// En componente Vue (setup)
export default defineComponent({
  setup() {
    const store = useProjectsStore()
    return { store }
  }
})

// O con <script setup>
<script setup lang="ts">
import { useProjectsStore } from '@/stores/projects'
const store = useProjectsStore()
</script>
```

### Error: No esperar async actions

**Incorrecto:**
```typescript
store.fetchProjects()
console.log(store.projects)  // Puede estar vacío
```

**Correcto:**
```typescript
await store.fetchProjects()
console.log(store.projects)  // Datos cargados
```

### Error: Modificar state directamente

**Incorrecto:**
```typescript
store.projects.push(newProject)  // Evitar
```

**Correcto:**
```typescript
await store.createProject(name, description, file)
// El store actualiza internamente
```

### Error: No verificar loading/error

**Incorrecto:**
```typescript
await store.fetchProject(id)
doSomething(store.currentProject)  // Puede ser null si falló
```

**Correcto:**
```typescript
await store.fetchProject(id)
if (store.error) {
  showError(store.error)
} else if (store.currentProject) {
  doSomething(store.currentProject)
}
```
