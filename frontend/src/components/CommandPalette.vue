<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { useWorkspaceStore } from '@/stores/workspace'
import { useSelectionStore } from '@/stores/selection'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useDebouncedRef } from '@/composables/usePerformance'
import type { Entity, Alert, Chapter, AlertSeverity } from '@/types'

/**
 * CommandPalette - Paleta de comandos global (Cmd+K / Ctrl+K)
 *
 * Permite búsqueda fuzzy de:
 * - Entidades (personajes, lugares, objetos)
 * - Alertas
 * - Capítulos
 * - Acciones del sistema
 */

const props = defineProps<{
  /** ID del proyecto actual (para búsquedas contextuales) */
  projectId?: number
  /** Entidades del proyecto */
  entities?: Entity[]
  /** Alertas del proyecto */
  alerts?: Alert[]
  /** Capítulos del proyecto */
  chapters?: Chapter[]
}>()

const workspaceStore = useWorkspaceStore()
const selectionStore = useSelectionStore()
const { getSeverityConfig } = useAlertUtils()

// Estado
const visible = ref(false)
// Debounce la búsqueda para evitar cálculos excesivos en cada keystroke
const { value: query, debouncedValue: debouncedQuery } = useDebouncedRef('', 150)
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

// Tipos de resultado
interface CommandResult {
  id: string
  type: 'entity' | 'alert' | 'chapter' | 'action'
  icon: string
  label: string
  description?: string
  action: () => void
}

// Acciones del sistema
const systemActions: CommandResult[] = [
  {
    id: 'action-text',
    type: 'action',
    icon: 'pi-file',
    label: 'Ir a Texto',
    description: 'Ver documento original',
    action: () => {
      workspaceStore.setActiveTab('text')
      close()
    }
  },
  {
    id: 'action-entities',
    type: 'action',
    icon: 'pi-users',
    label: 'Ir a Entidades',
    description: 'Lista de personajes, lugares y objetos',
    action: () => {
      workspaceStore.setActiveTab('entities')
      close()
    }
  },
  {
    id: 'action-alerts',
    type: 'action',
    icon: 'pi-exclamation-triangle',
    label: 'Ir a Alertas',
    description: 'Ver todas las alertas',
    action: () => {
      workspaceStore.setActiveTab('alerts')
      close()
    }
  },
  {
    id: 'action-relations',
    type: 'action',
    icon: 'pi-share-alt',
    label: 'Ir a Relaciones',
    description: 'Grafo de relaciones',
    action: () => {
      workspaceStore.setActiveTab('relationships')
      close()
    }
  },
  {
    id: 'action-summary',
    type: 'action',
    icon: 'pi-chart-bar',
    label: 'Ir a Resumen',
    description: 'Estadísticas del proyecto',
    action: () => {
      workspaceStore.setActiveTab('summary')
      close()
    }
  },
  {
    id: 'action-toggle-left',
    type: 'action',
    icon: 'pi-window-minimize',
    label: 'Alternar panel izquierdo',
    description: 'Mostrar/ocultar sidebar',
    action: () => {
      workspaceStore.toggleLeftPanel()
      close()
    }
  },
  {
    id: 'action-toggle-right',
    type: 'action',
    icon: 'pi-window-minimize',
    label: 'Alternar panel derecho',
    description: 'Mostrar/ocultar inspector',
    action: () => {
      workspaceStore.toggleRightPanel()
      close()
    }
  }
]

// Búsqueda fuzzy simple
function fuzzyMatch(text: string, pattern: string): boolean {
  if (!pattern) return true
  const lowerText = text.toLowerCase()
  const lowerPattern = pattern.toLowerCase()

  // Match exacto primero
  if (lowerText.includes(lowerPattern)) return true

  // Fuzzy: todas las letras del patrón deben aparecer en orden
  let patternIdx = 0
  for (let i = 0; i < lowerText.length && patternIdx < lowerPattern.length; i++) {
    if (lowerText[i] === lowerPattern[patternIdx]) {
      patternIdx++
    }
  }
  return patternIdx === lowerPattern.length
}

// Resultados filtrados (usa query con debounce para optimizar rendimiento)
const results = computed<CommandResult[]>(() => {
  const q = debouncedQuery.value.trim()
  const items: CommandResult[] = []

  // Si hay proyecto, buscar en sus datos
  if (props.projectId) {
    // Entidades
    const entities = props.entities || []
    for (const entity of entities) {
      if (fuzzyMatch(entity.name, q) || entity.aliases?.some((a: string) => fuzzyMatch(a, q))) {
        items.push({
          id: `entity-${entity.id}`,
          type: 'entity',
          icon: getEntityIcon(entity.type),
          label: entity.name,
          description: `${getEntityLabel(entity.type)} · ${entity.mentionCount} apariciones`,
          action: () => {
            selectionStore.selectEntity(entity)
            workspaceStore.setActiveTab('entities')
            close()
          }
        })
      }
    }

    // Alertas
    const alerts = props.alerts || []
    for (const alert of alerts) {
      if (fuzzyMatch(alert.title, q) || fuzzyMatch(alert.description, q)) {
        items.push({
          id: `alert-${alert.id}`,
          type: 'alert',
          icon: getSeverityIcon(alert.severity),
          label: alert.title,
          description: `${getSeverityLabel(alert.severity)}${alert.chapter ? ` · Capítulo ${alert.chapter}` : ''}`,
          action: () => {
            selectionStore.selectAlert(alert)
            workspaceStore.setActiveTab('alerts')
            close()
          }
        })
      }
    }

    // Capítulos
    const chapters = props.chapters || []
    for (const chapter of chapters) {
      if (fuzzyMatch(chapter.title, q)) {
        items.push({
          id: `chapter-${chapter.id}`,
          type: 'chapter',
          icon: 'pi-book',
          label: chapter.title,
          description: `Capítulo ${chapter.chapterNumber} · ${chapter.wordCount.toLocaleString()} palabras`,
          action: () => {
            // No hay selectChapter en selection store, solo navegar
            workspaceStore.setActiveTab('text')
            close()
          }
        })
      }
    }
  }

  // Acciones del sistema
  for (const action of systemActions) {
    if (fuzzyMatch(action.label, q)) {
      items.push(action)
    }
  }

  // Limitar resultados
  return items.slice(0, 15)
})

// Helpers de entidades
function getEntityIcon(type: string): string {
  const icons: Record<string, string> = {
    character: 'pi-user',
    location: 'pi-map-marker',
    object: 'pi-box',
    organization: 'pi-building',
    event: 'pi-calendar'
  }
  return icons[type] || 'pi-circle'
}

function getEntityLabel(type: string): string {
  const labels: Record<string, string> = {
    character: 'Personaje',
    location: 'Lugar',
    object: 'Objeto',
    organization: 'Organización',
    event: 'Evento'
  }
  return labels[type] || type
}

// Helpers de alertas - usar composable centralizado
function getSeverityIcon(severity: string): string {
  // Extraer solo el nombre de clase sin 'pi ' prefix
  const fullIcon = getSeverityConfig(severity as AlertSeverity).icon
  return fullIcon.replace('pi ', '')
}

function getSeverityLabel(severity: string): string {
  return getSeverityConfig(severity as AlertSeverity).label
}

// Abrir/cerrar
function open() {
  visible.value = true
  query.value = ''
  selectedIndex.value = 0
  // Focus en siguiente tick
  setTimeout(() => {
    inputRef.value?.focus()
  }, 100)
}

function close() {
  visible.value = false
  query.value = ''
}

// Navegación por teclado
function handleKeydown(event: KeyboardEvent) {
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, results.value.length - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
    case 'Enter':
      event.preventDefault()
      if (results.value[selectedIndex.value]) {
        results.value[selectedIndex.value].action()
      }
      break
    case 'Escape':
      close()
      break
  }
}

// Reset selección cuando cambia la query
watch(query, () => {
  selectedIndex.value = 0
})

// Atajo de teclado global (Cmd+K / Ctrl+K)
function handleGlobalKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault()
    if (visible.value) {
      close()
    } else {
      open()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})

// Helper para badges de tipo
function getTypeBadge(type: string): string {
  const badges: Record<string, string> = {
    entity: 'Entidad',
    alert: 'Alerta',
    chapter: 'Capítulo',
    action: 'Acción'
  }
  return badges[type] || type
}

// Exponer open para uso externo
defineExpose({ open, close })
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :draggable="false"
    :show-header="false"
    class="command-palette-dialog"
    :pt="{
      root: { class: 'command-palette-root' },
      mask: { class: 'command-palette-mask' },
      content: { class: 'command-palette-content' }
    }"
  >
    <div class="command-palette" @keydown="handleKeydown">
      <!-- Input de búsqueda -->
      <div class="search-header">
        <i class="pi pi-search search-icon"></i>
        <InputText
          ref="inputRef"
          v-model="query"
          placeholder="Buscar entidades, alertas, capítulos, acciones..."
          class="search-input"
          :pt="{
            root: { class: 'search-input-root' }
          }"
        />
        <span class="shortcut-hint">ESC</span>
      </div>

      <!-- Lista de resultados -->
      <div v-if="results.length > 0" class="results-list">
        <button
          v-for="(result, index) in results"
          :key="result.id"
          type="button"
          class="result-item"
          :class="{
            selected: index === selectedIndex,
            [`type-${result.type}`]: true
          }"
          @click="result.action()"
          @mouseenter="selectedIndex = index"
        >
          <i :class="['result-icon', 'pi', result.icon]"></i>
          <div class="result-content">
            <span class="result-label">{{ result.label }}</span>
            <span v-if="result.description" class="result-description">{{
              result.description
            }}</span>
          </div>
          <span class="result-type-badge">{{ getTypeBadge(result.type) }}</span>
        </button>
      </div>

      <!-- Estado vacío -->
      <div v-else class="empty-state">
        <i class="pi pi-search"></i>
        <span>{{ query ? 'Sin resultados' : 'Escribe para buscar...' }}</span>
      </div>

      <!-- Footer con hints -->
      <div class="palette-footer">
        <span class="hint"><kbd>↑↓</kbd> navegar</span>
        <span class="hint"><kbd>↵</kbd> seleccionar</span>
        <span class="hint"><kbd>esc</kbd> cerrar</span>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.command-palette {
  width: 600px;
  max-width: 90vw;
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-lg);
  overflow: hidden;
  box-shadow: var(--ds-shadow-lg);
}

.search-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-surface-border);
}

.search-icon {
  color: var(--ds-color-text-secondary);
  font-size: 1.25rem;
}

.search-input {
  flex: 1;
}

:deep(.search-input-root) {
  width: 100%;
  border: none;
  background: transparent;
  font-size: var(--ds-font-size-base);
  padding: 0;
}

:deep(.search-input-root:focus) {
  box-shadow: none;
}

.shortcut-hint {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  padding: 2px 6px;
  border-radius: var(--ds-radius-sm);
}

.results-list {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--ds-space-2);
}

.result-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  width: 100%;
  padding: var(--ds-space-3);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--ds-transition-fast);
}

.result-item:hover,
.result-item.selected {
  background: var(--ds-surface-hover);
}

.result-item.selected {
  background: var(--ds-color-primary-subtle);
}

.result-icon {
  font-size: 1.25rem;
  color: var(--ds-color-text-secondary);
  width: 24px;
  text-align: center;
}

.result-item.type-entity .result-icon {
  color: var(--ds-color-primary);
}

.result-item.type-alert .result-icon {
  color: var(--ds-color-warning);
}

.result-item.type-chapter .result-icon {
  color: var(--ds-color-info);
}

.result-item.type-action .result-icon {
  color: var(--ds-color-text-secondary);
}

.result-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-label {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-description {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-type-badge {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  padding: 2px 8px;
  border-radius: var(--ds-radius-full);
  flex-shrink: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-8);
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 2rem;
  opacity: 0.5;
}

.palette-footer {
  display: flex;
  justify-content: center;
  gap: var(--ds-space-6);
  padding: var(--ds-space-3);
  border-top: 1px solid var(--ds-surface-border);
  background: var(--ds-surface-section);
}

.hint {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.hint kbd {
  font-family: inherit;
  background: var(--ds-surface-hover);
  padding: 1px 4px;
  border-radius: var(--ds-radius-sm);
  margin-right: 4px;
}

/* Scrollbar */
.results-list::-webkit-scrollbar {
  width: 6px;
}

.results-list::-webkit-scrollbar-track {
  background: transparent;
}

.results-list::-webkit-scrollbar-thumb {
  background: var(--ds-surface-border);
  border-radius: 3px;
}
</style>

<style>
/* Estilos globales para el dialog */
.command-palette-root {
  border: none !important;
  background: transparent !important;
}

.command-palette-mask {
  background: rgba(0, 0, 0, 0.5) !important;
  backdrop-filter: blur(4px);
}

.command-palette-content {
  padding: 0 !important;
  border-radius: var(--ds-radius-lg) !important;
  overflow: hidden !important;
}

.command-palette-dialog {
  max-width: none !important;
}
</style>
