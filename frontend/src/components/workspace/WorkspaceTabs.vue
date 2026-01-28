<script setup lang="ts">
import { computed } from 'vue'
import { useWorkspaceStore, type WorkspaceTab } from '@/stores/workspace'
import { useDocumentTypeConfig } from '@/composables/useDocumentTypeConfig'
import type { DocumentType, RecommendedAnalysis } from '@/types/domain/projects'
import { storeToRefs } from 'pinia'

/**
 * WorkspaceTabs - Barra de pestanas del workspace.
 *
 * Las pestañas visibles se adaptan al tipo de documento detectado.
 * Por ejemplo, para autoayuda no se muestran Timeline ni Relaciones.
 */

const workspaceStore = useWorkspaceStore()
// Usar storeToRefs para asegurar reactividad correcta
const { activeTab } = storeToRefs(workspaceStore)

interface TabConfig {
  id: WorkspaceTab
  label: string
  icon: string
  badge?: number
  /** Key para lookup en documentTypeConfig */
  configKey?: string
}

const props = defineProps<{
  /** Contador de entidades para badge */
  entityCount?: number
  /** Contador de alertas para badge */
  alertCount?: number
  /** Tipo de documento detectado */
  documentType?: DocumentType
  /** Configuración de análisis recomendada */
  recommendedAnalysis?: RecommendedAnalysis
}>()

// Usar el composable para obtener configuración según tipo de documento
const { config, isTabVisible, getTabLabel } = useDocumentTypeConfig(
  computed(() => props.documentType),
  computed(() => props.recommendedAnalysis)
)

// Mapeo de tabs a sus keys de config
const tabConfigMapping: Record<WorkspaceTab, string> = {
  text: 'text',
  entities: 'entities',
  relationships: 'relations',
  alerts: 'alerts',
  timeline: 'timeline',
  style: 'style',
  glossary: 'text', // Siempre visible
  summary: 'text', // Siempre visible
}

// Configuración base de todas las tabs
const allTabs: TabConfig[] = [
  { id: 'text', label: 'Texto', icon: 'pi pi-file-edit', configKey: 'text' },
  { id: 'entities', label: 'Entidades', icon: 'pi pi-users', configKey: 'entities' },
  { id: 'relationships', label: 'Relaciones', icon: 'pi pi-share-alt', configKey: 'relations' },
  { id: 'alerts', label: 'Revisión', icon: 'pi pi-search', configKey: 'alerts' },
  { id: 'timeline', label: 'Cronología', icon: 'pi pi-clock', configKey: 'timeline' },
  { id: 'style', label: 'Escritura', icon: 'pi pi-pencil', configKey: 'style' },
  { id: 'glossary', label: 'Glosario', icon: 'pi pi-book', configKey: 'text' },
  { id: 'summary', label: 'Resumen', icon: 'pi pi-chart-bar', configKey: 'text' },
]

// Tabs filtradas según el tipo de documento
const tabs = computed<TabConfig[]>(() => {
  return allTabs
    .filter(tab => {
      // Summary y Glossary siempre visibles
      if (tab.id === 'summary' || tab.id === 'glossary') return true
      // Usar configKey para verificar visibilidad
      const configKey = tab.configKey || tab.id
      return isTabVisible(configKey)
    })
    .map(tab => ({
      ...tab,
      // Aplicar label dinámico según tipo de documento (excepto summary/glossary que mantienen su label fijo)
      label: (tab.id === 'summary' || tab.id === 'glossary') ? tab.label :
             (tab.configKey ? getTabLabel(tab.configKey) : tab.label),
      // Añadir badges
      badge: tab.id === 'entities' ? props.entityCount :
             tab.id === 'alerts' ? props.alertCount : undefined,
    }))
})

function selectTab(tab: WorkspaceTab) {
  workspaceStore.setActiveTab(tab)
}

function handleKeydown(event: KeyboardEvent, index: number) {
  const tabCount = tabs.value.length
  let newIndex = index

  switch (event.key) {
    case 'ArrowLeft':
      newIndex = (index - 1 + tabCount) % tabCount
      break
    case 'ArrowRight':
      newIndex = (index + 1) % tabCount
      break
    case 'Home':
      newIndex = 0
      break
    case 'End':
      newIndex = tabCount - 1
      break
    default:
      return
  }

  event.preventDefault()
  selectTab(tabs.value[newIndex].id)

  // Focus the new tab
  const tabElements = document.querySelectorAll('.workspace-tabs__tab')
  ;(tabElements[newIndex] as HTMLElement)?.focus()
}
</script>

<template>
  <div class="workspace-tabs" role="tablist" aria-label="Secciones del workspace">
    <button
      v-for="(tab, index) in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      class="workspace-tabs__tab"
      :class="{ 'workspace-tabs__tab--active': activeTab === tab.id }"
      :aria-selected="activeTab === tab.id"
      :tabindex="activeTab === tab.id ? 0 : -1"
      @click="selectTab(tab.id)"
      @keydown="handleKeydown($event, index)"
    >
      <i :class="tab.icon" class="workspace-tabs__icon" />
      <span class="workspace-tabs__label">{{ tab.label }}</span>
      <span
        v-if="tab.badge !== undefined && tab.badge > 0"
        class="workspace-tabs__badge"
      >
        {{ tab.badge > 99 ? '99+' : tab.badge }}
      </span>
    </button>

    <!-- Spacer -->
    <div class="workspace-tabs__spacer" />

    <!-- Actions slot -->
    <div class="workspace-tabs__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.workspace-tabs {
  display: flex;
  align-items: stretch;
  gap: var(--ds-space-1);
  padding: 0 var(--ds-space-4);
  background-color: var(--ds-surface-card);
  height: 48px;
}

.workspace-tabs__tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: 0 var(--ds-space-4);
  min-width: 120px;
  border: none;
  background: transparent;
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  cursor: pointer;
  position: relative;
  transition: color var(--ds-transition-fast), background-color var(--ds-transition-fast);
}

.workspace-tabs__tab:hover {
  color: var(--ds-color-text);
  background-color: var(--ds-surface-hover);
}

.workspace-tabs__tab:focus-visible {
  outline: 2px solid var(--ds-color-primary);
  outline-offset: -2px;
  border-radius: var(--ds-radius-sm);
}

.workspace-tabs__tab--active {
  color: var(--ds-color-primary);
}

.workspace-tabs__tab--active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--ds-space-2);
  right: var(--ds-space-2);
  height: 2px;
  background-color: var(--ds-color-primary);
  border-radius: var(--ds-radius-full) var(--ds-radius-full) 0 0;
}

.workspace-tabs__icon {
  font-size: 1rem;
}

.workspace-tabs__label {
  white-space: nowrap;
}

.workspace-tabs__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 var(--ds-space-1-5);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: white;
  background-color: var(--ds-color-primary);
  border-radius: var(--ds-radius-full);
}

.workspace-tabs__tab--active .workspace-tabs__badge {
  background-color: var(--ds-color-primary-dark);
}

.workspace-tabs__spacer {
  flex: 1;
}

.workspace-tabs__actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

/* Responsive: ocultar labels en móvil */
@media (max-width: 768px) {
  .workspace-tabs {
    padding: 0 var(--ds-space-2);
  }

  .workspace-tabs__tab {
    padding: 0 var(--ds-space-3);
  }

  .workspace-tabs__label {
    display: none;
  }

  .workspace-tabs__icon {
    font-size: 1.25rem;
  }
}
</style>
