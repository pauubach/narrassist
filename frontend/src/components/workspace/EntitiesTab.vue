<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { apiUrl } from '@/config/api'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DsInput from '@/components/ds/DsInput.vue'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import Chips from 'primevue/chips'
import Tag from 'primevue/tag'
import Drawer from 'primevue/drawer'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import MergeEntitiesDialog from '@/components/MergeEntitiesDialog.vue'
import UndoMergeDialog from '@/components/UndoMergeDialog.vue'
import MergeHistoryPanel from '@/components/MergeHistoryPanel.vue'
import RejectEntityDialog from '@/components/RejectEntityDialog.vue'
import type { Entity, MergeHistoryEntry, EntityAttribute } from '@/types'
import { transformEntityAttribute } from '@/types/transformers'
import type { ApiEntityAttribute } from '@/types/api'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useWorkspaceStore } from '@/stores/workspace'
import { useSelectionStore } from '@/stores/selection'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'

/**
 * EntitiesTab - Pestaña completa de gestión de entidades
 *
 * Muestra todas las entidades del proyecto con:
 * - Filtros por tipo, importancia, búsqueda
 * - Edición, fusión, eliminación
 * - Historial de fusiones
 * - Exportación
 */

interface Props {
  /** Entidades del proyecto */
  entities: Entity[]
  /** Si está cargando */
  loading?: boolean
  /** ID del proyecto */
  projectId: number
  /** ID de entidad a seleccionar inicialmente (para navegación desde /characters/:id) */
  initialEntityId?: number | null
  /** Total de capítulos en el documento (para formateo inteligente) */
  chapterCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  initialEntityId: null,
  chapterCount: 0
})

const emit = defineEmits<{
  'entity-select': [entity: Entity]
  'refresh': []
}>()

const toast = useToast()
const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()
const _selectionStore = useSelectionStore()
const { getEntityIcon, getEntityLabel, getEntityColor } = useEntityUtils()
const { formatChapterLabel } = useAlertUtils()

// Estado de filtros
const searchQuery = ref('')
const selectedType = ref<string | null>(null)
const selectedImportance = ref<string | null>(null)
const showOnlyRelevant = ref(false) // Filtrar entidades con baja relevancia

// Estado de selección y diálogos
// NOTA: selectedEntity se mantiene para operaciones locales (editar, eliminar, etc.)
// El panel de detalles se maneja en el panel derecho global (EntityInspector)
const selectedEntity = ref<Entity | null>(null)
const selectedEntityAttributes = ref<EntityAttribute[]>([])
const loadingAttributes = ref(false)
const showEditDialog = ref(false)
const showMergeDialog = ref(false)
const showUndoMergeDialog = ref(false)
const showMergeHistory = ref(false)
const showRejectDialog = ref(false)
const entityToReject = ref<Entity | null>(null)
const editingEntity = ref<Entity | null>(null)
const entityToUndoMerge = ref<Entity | null>(null)
const selectedEntitiesForMerge = ref<Entity[]>([])
const mergeHistoryRef = ref<InstanceType<typeof MergeHistoryPanel> | null>(null)

// ID de la última entidad seleccionada automáticamente
const lastAutoSelectedId = ref<number | null>(null)

// Watch para seleccionar entidad inicial (navegación desde /characters/:id o onEntityEdit)
watch(() => props.initialEntityId, async (entityId) => {
  if (entityId && entityId !== lastAutoSelectedId.value && props.entities.length > 0) {
    const entity = props.entities.find(e => e.id === entityId)
    if (entity) {
      lastAutoSelectedId.value = entityId
      await handleEntityClick(entity)
      // Limpiar el query param de la URL si existe
      if (route.query.entity) {
        router.replace({ query: { ...route.query, entity: undefined } })
      }
    }
  }
}, { immediate: true })

// También cuando se cargan las entidades
watch(() => props.entities, async (newEntities, oldEntities) => {
  // Si hay una entidad seleccionada y las entidades cambiaron, refrescar atributos
  // Esto es necesario después de un re-análisis
  if (selectedEntity.value && newEntities.length > 0 && oldEntities && oldEntities.length > 0) {
    const updatedEntity = newEntities.find(e => e.id === selectedEntity.value!.id)
    if (updatedEntity) {
      // Actualizar la referencia a la entidad con los nuevos datos
      selectedEntity.value = updatedEntity
      // Recargar atributos desde el backend
      await loadEntityAttributes(updatedEntity.id)
    } else {
      // La entidad ya no existe, limpiar selección
      selectedEntity.value = null
      selectedEntityAttributes.value = []
    }
  }

  // Selección inicial si viene de navegación
  if (props.initialEntityId && props.initialEntityId !== lastAutoSelectedId.value && newEntities.length > 0 && !selectedEntity.value) {
    const entity = newEntities.find(e => e.id === props.initialEntityId)
    if (entity) {
      lastAutoSelectedId.value = props.initialEntityId
      await handleEntityClick(entity)
      // Limpiar el query param de la URL si existe
      if (route.query.entity) {
        router.replace({ query: { ...route.query, entity: undefined } })
      }
    }
  }
})

// Opciones de filtros
const typeOptions = computed(() => {
  const types = new Set(props.entities.map(e => e.type))
  return [
    { label: 'Todos los tipos', value: null },
    ...Array.from(types).map(type => ({
      label: getEntityLabel(type),
      value: type
    }))
  ]
})

const _importanceOptions = [
  { label: 'Todas', value: null },
  { label: 'Principal', value: 'main' },
  { label: 'Secundario', value: 'secondary' },
  { label: 'Menor', value: 'minor' }
]

const entityTypeOptions = [
  { label: 'Personaje', value: 'character' },
  { label: 'Lugar', value: 'location' },
  { label: 'Organización', value: 'organization' },
  { label: 'Objeto', value: 'object' },
  { label: 'Evento', value: 'event' },
  { label: 'Concepto', value: 'concept' },
  { label: 'Otro', value: 'other' }
]

const importanceEditOptions = [
  { label: 'Menor', value: 'minor' },
  { label: 'Secundario', value: 'secondary' },
  { label: 'Principal', value: 'main' }
]

// Umbral de relevancia mínima (entidades con score < 0.1 se consideran poco relevantes)
const RELEVANCE_THRESHOLD = 0.1

// Entidades filtradas
const filteredEntities = computed(() => {
  let result = props.entities

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(e =>
      e.name.toLowerCase().includes(query) ||
      e.aliases?.some(a => a.toLowerCase().includes(query))
    )
  }

  if (selectedType.value) {
    result = result.filter(e => e.type === selectedType.value)
  }

  if (selectedImportance.value) {
    result = result.filter(e => e.importance === selectedImportance.value)
  }

  // Filtrar entidades poco relevantes si está activado
  if (showOnlyRelevant.value) {
    result = result.filter(e => (e.relevanceScore ?? 0) >= RELEVANCE_THRESHOLD)
  }

  return [...result].sort((a, b) => (b.mentionCount || 0) - (a.mentionCount || 0))
})

// Contar entidades de baja relevancia
const lowRelevanceCount = computed(() => {
  return props.entities.filter(e => (e.relevanceScore ?? 0) < RELEVANCE_THRESHOLD).length
})

// Estadísticas
const stats = computed(() => ({
  total: props.entities.length,
  filtered: filteredEntities.value.length,
  characters: props.entities.filter(e => e.type === 'character').length,
  locations: props.entities.filter(e => e.type === 'location').length,
  organizations: props.entities.filter(e => e.type === 'organization').length
}))

// Handlers
async function handleEntityClick(entity: Entity) {
  selectedEntity.value = entity
  // Cargar atributos de la entidad
  await loadEntityAttributes(entity.id)
  // NO emitir entity-select - los detalles se muestran en el panel central
  // El panel derecho (EntityInspector) no debe abrirse aquí
}

/**
 * Carga los atributos de una entidad desde el backend
 */
async function loadEntityAttributes(entityId: number) {
  loadingAttributes.value = true
  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/${entityId}/attributes`))
    const data = await response.json()
    if (data.success) {
      const rawAttributes: ApiEntityAttribute[] = data.data || []
      selectedEntityAttributes.value = rawAttributes.map(transformEntityAttribute)
    } else {
      selectedEntityAttributes.value = []
    }
  } catch (err) {
    console.error('Error loading entity attributes:', err)
    selectedEntityAttributes.value = []
  } finally {
    loadingAttributes.value = false
  }
}

function clearFilters() {
  searchQuery.value = ''
  selectedType.value = null
  selectedImportance.value = null
}

function onEntityEdit(entity: Entity) {
  editingEntity.value = { ...entity }
  showEditDialog.value = true
}

function onEntityMerge(entity: Entity) {
  selectedEntitiesForMerge.value = [entity]
  showMergeDialog.value = true
}

function onUndoMerge(entity: Entity) {
  entityToUndoMerge.value = entity
  showUndoMergeDialog.value = true
}

async function onEntityDelete(entity: Entity) {
  if (!confirm(`¿Seguro que deseas eliminar la entidad "${entity.name}"?\n\nEsta acción desactivará la entidad.`)) {
    return
  }

  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/${entity.id}`), {
      method: 'DELETE',
    })

    const data = await response.json()

    if (data.success) {
      if (selectedEntity.value?.id === entity.id) {
        selectedEntity.value = null
      }
      emit('refresh')
      toast.add({ severity: 'success', summary: 'Eliminada', detail: 'Entidad eliminada correctamente', life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al eliminar: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error deleting entity:', err)
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo eliminar la entidad', life: 5000 })
  }
}

/**
 * Abre el diálogo de rechazo de entidad
 */
function onRejectEntity(entity: Entity) {
  entityToReject.value = entity
  showRejectDialog.value = true
}

/**
 * Procesa el rechazo de una entidad con el alcance seleccionado
 */
async function handleRejectEntity(scope: 'project' | 'global', reason: string) {
  if (!entityToReject.value) return

  const entity = entityToReject.value

  try {
    // 1. Primero eliminar la entidad actual del proyecto
    const deleteResponse = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/${entity.id}/reject`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    })

    const deleteData = await deleteResponse.json()
    if (!deleteData.success) {
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al rechazar: ${deleteData.error}`, life: 5000 })
      return
    }

    // 2. Según el alcance, añadir al filtro correspondiente
    if (scope === 'global') {
      // Añadir a rechazos globales del usuario
      const globalResponse = await fetch(apiUrl('/api/entity-filters/user-rejections'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_name: entity.name,
          entity_type: entity.type,
          reason
        })
      })

      const globalData = await globalResponse.json()
      if (!globalData.success) {
        console.warn('No se pudo añadir a filtros globales:', globalData.error)
      }
    } else {
      // Añadir a overrides del proyecto
      const projectResponse = await fetch(apiUrl(`/api/projects/${props.projectId}/entity-filters/overrides`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_name: entity.name,
          entity_type: entity.type,
          action: 'reject',
          reason
        })
      })

      const projectData = await projectResponse.json()
      if (!projectData.success) {
        console.warn('No se pudo añadir a filtros del proyecto:', projectData.error)
      }
    }

    // 3. Limpiar selección y refrescar
    if (selectedEntity.value?.id === entity.id) {
      selectedEntity.value = null
    }
    emit('refresh')

    const scopeText = scope === 'global' ? 'en todos tus proyectos' : 'en este proyecto'
    toast.add({
      severity: 'success',
      summary: 'Rechazada',
      detail: `"${entity.name}" no aparecerá ${scopeText}`,
      life: 4000
    })
  } catch (err) {
    console.error('Error rejecting entity:', err)
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo rechazar la entidad', life: 5000 })
  } finally {
    entityToReject.value = null
  }
}

async function saveEntity() {
  if (!editingEntity.value) {
    showEditDialog.value = false
    return
  }

  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/${editingEntity.value.id}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: editingEntity.value.name,
        type: editingEntity.value.type,
        importance: editingEntity.value.importance,
        aliases: editingEntity.value.aliases,
      }),
    })

    const data = await response.json()

    if (data.success) {
      showEditDialog.value = false
      if (selectedEntity.value?.id === editingEntity.value.id) {
        selectedEntity.value = { ...editingEntity.value }
      }
      emit('refresh')
      toast.add({ severity: 'success', summary: 'Guardado', detail: 'Entidad actualizada correctamente', life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al guardar: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error updating entity:', err)
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo guardar la entidad', life: 5000 })
  }
}

async function onMergeEntities(primaryEntityId: number, entityIdsToMerge: number[]) {
  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/merge`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        primary_entity_id: primaryEntityId,
        entity_ids: entityIdsToMerge
      })
    })

    const data = await response.json()

    if (data.success) {
      showMergeDialog.value = false
      emit('refresh')
      mergeHistoryRef.value?.refresh()
      toast.add({ severity: 'success', summary: 'Fusionadas', detail: 'Entidades fusionadas correctamente', life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al fusionar: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error merging entities:', err)
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo fusionar las entidades', life: 5000 })
  }
}

async function onUndoMergeComplete(_restoredIds: number[]) {
  if (selectedEntity.value?.id === entityToUndoMerge.value?.id) {
    selectedEntity.value = null
  }
  emit('refresh')
  mergeHistoryRef.value?.refresh()
  entityToUndoMerge.value = null
  toast.add({ severity: 'success', summary: 'Fusión deshecha', detail: 'Entidades restauradas correctamente', life: 3000 })
}

async function onUndoMergeFromHistory(entry: MergeHistoryEntry) {
  const entity = props.entities.find(e => e.id === entry.resultEntityId)
  if (entity) {
    entityToUndoMerge.value = entity
    showUndoMergeDialog.value = true
  } else {
    try {
      const response = await fetch(
        `/api/projects/${props.projectId}/entities/undo-merge/${entry.id}`,
        { method: 'POST' }
      )
      const data = await response.json()

      if (data.success) {
        emit('refresh')
        mergeHistoryRef.value?.refresh()
        toast.add({ severity: 'success', summary: 'Fusión deshecha', detail: 'Las entidades originales han sido restauradas', life: 3000 })
      } else {
        toast.add({ severity: 'error', summary: 'Error', detail: `Error al deshacer fusión: ${data.error}`, life: 5000 })
      }
    } catch (err) {
      console.error('Error undoing merge:', err)
      toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo deshacer la fusión', life: 5000 })
    }
  }
}

function viewMentions(entity: Entity) {
  // Seleccionar la entidad correcta para mostrar en el inspector
  emit('entity-select', entity)
  // Navegar a la pestaña de texto mostrando las menciones de esta entidad
  workspaceStore.navigateToEntityMentions(entity.id)
}

function exportEntities() {
  if (!props.entities || props.entities.length === 0) {
    toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'No hay entidades para exportar', life: 4000 })
    return
  }

  try {
    const content = {
      projectId: props.projectId,
      exportedAt: new Date().toISOString(),
      totalEntities: props.entities.length,
      entities: props.entities.map(e => ({
        id: e.id,
        name: e.name,
        type: e.type,
        importance: e.importance,
        aliases: e.aliases,
        mentionCount: e.mentionCount,
      })),
    }

    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `entidades_proyecto_${props.projectId}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.add({ severity: 'success', summary: 'Exportado', detail: 'Entidades exportadas correctamente', life: 3000 })
  } catch (err) {
    console.error('Error exporting entities:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar entidades', life: 5000 })
  }
}

// Helpers para el sidebar (reservado para uso futuro)
function _getTypeSeverity(type: string): string {
  const severities: Record<string, string> = {
    'character': 'success',
    'location': 'danger',
    'organization': 'info',
    'object': 'warning',
    'event': 'secondary',
    'concept': 'contrast',
    'other': 'secondary'
  }
  return severities[type] || 'secondary'
}

function _getImportanceSeverity(importance: string): string {
  const severities: Record<string, string> = {
    'main': 'success',
    'secondary': 'info',
    'minor': 'secondary'
  }
  return severities[importance] || 'secondary'
}

// Mapeo para DsBadge severity (usa los valores del design system)
function getImportanceSeverityForBadge(importance: string): 'critical' | 'high' | 'medium' | 'low' | 'info' {
  const severities: Record<string, 'critical' | 'high' | 'medium' | 'low' | 'info'> = {
    'main': 'high',       // Naranja - Principal
    'principal': 'high',
    'high': 'medium',     // Amarillo - Alto
    'secondary': 'low',   // Azul - Secundario
    'medium': 'low',
    'minor': 'info',      // Gris - Menor
    'low': 'info',
    'minimal': 'info'
  }
  return severities[importance] || 'info'
}

function getImportanceLabel(importance: string): string {
  const labels: Record<string, string> = {
    'main': 'Principal',
    'secondary': 'Secundario',
    'minor': 'Menor'
  }
  return labels[importance] || importance
}

// Helpers para relevancia
function formatRelevance(score: number): string {
  return `${Math.round(score * 100)}%`
}

function getRelevanceClass(score: number): string {
  if (score >= 0.5) return 'relevance-high'
  if (score >= 0.2) return 'relevance-medium'
  if (score >= 0.1) return 'relevance-low'
  return 'relevance-very-low'
}

function _getRelevanceTooltip(score: number): string {
  if (score >= 0.5) return 'Alta relevancia: entidad muy mencionada'
  if (score >= 0.2) return 'Relevancia media: entidad mencionada regularmente'
  if (score >= 0.1) return 'Baja relevancia: pocas menciones en el documento'
  return 'Muy baja relevancia: mencionada raramente (posible falso positivo)'
}

/** Obtiene el color de fondo para un tipo de entidad */
function getTypeBackgroundColor(type: string): string {
  const colors: Record<string, string> = {
    'character': 'var(--ds-entity-character-bg)',
    'location': 'var(--ds-entity-location-bg)',
    'organization': 'var(--ds-entity-organization-bg)',
    'object': 'var(--ds-entity-object-bg)',
    'event': 'var(--ds-entity-event-bg)',
    'concept': 'var(--ds-entity-concept-bg)',
    'animal': 'var(--ds-entity-animal-bg)',
    'creature': 'var(--ds-entity-creature-bg)',
    'building': 'var(--ds-entity-building-bg)',
    'region': 'var(--ds-entity-region-bg)',
    'vehicle': 'var(--ds-entity-vehicle-bg)',
    'faction': 'var(--ds-entity-faction-bg)',
    'family': 'var(--ds-entity-family-bg)',
    'time_period': 'var(--ds-entity-time-period-bg)',
    'other': 'var(--ds-entity-other-bg)'
  }
  return colors[type] || colors.other
}

/** Obtiene el color del texto para un tipo de entidad */
function getTypeTextColor(type: string): string {
  const colors: Record<string, string> = {
    'character': 'var(--ds-entity-character)',
    'location': 'var(--ds-entity-location)',
    'organization': 'var(--ds-entity-organization)',
    'object': 'var(--ds-entity-object)',
    'event': 'var(--ds-entity-event)',
    'concept': 'var(--ds-entity-concept)',
    'animal': 'var(--ds-entity-animal)',
    'creature': 'var(--ds-entity-creature)',
    'building': 'var(--ds-entity-building)',
    'region': 'var(--ds-entity-region)',
    'vehicle': 'var(--ds-entity-vehicle)',
    'faction': 'var(--ds-entity-faction)',
    'family': 'var(--ds-entity-family)',
    'time_period': 'var(--ds-entity-time-period)',
    'other': 'var(--ds-entity-other)'
  }
  return colors[type] || colors.other
}

/** Traduce nombres de atributos del inglés al español */
// Usa la función centralizada de useAlertUtils
const { translateAttributeName } = useAlertUtils()

/**
 * Navega al texto donde se encontró el atributo
 */
function navigateToAttributeSource(attr: EntityAttribute) {
  if (attr.spanStart !== undefined && attr.spanStart !== null) {
    // Navegar a la posición exacta en el texto
    workspaceStore.navigateToTextPosition(attr.spanStart, attr.value)
  }
}
</script>

<template>
  <div class="entities-tab">
    <!-- Header con explicación -->
    <div class="entities-header">
      <div class="header-content">
        <h3>
          <i class="pi pi-users"></i>
          Gestión de Entidades
        </h3>
        <p class="header-subtitle">
          Lista técnica de personajes, lugares y conceptos detectados.
          Fusiona duplicados, edita atributos y navega a menciones.
          <span v-tooltip.right="'Esta pestaña es para gestionar las entidades: fusionar duplicados, corregir tipos, editar atributos. Para una vista wiki consolidada, usa la pestaña Story Bible.'" class="info-tip">
            <i class="pi pi-info-circle"></i>
          </span>
        </p>
      </div>
    </div>

    <!-- Layout de 2 columnas: Lista izquierda + Contenido centro -->
    <div class="entities-layout">
      <!-- Panel izquierdo: Lista de entidades -->
      <div class="entities-sidebar">
        <!-- Toolbar compacto - filtros en dos filas -->
        <div class="sidebar-toolbar">
          <div class="toolbar-row">
            <DsInput
              v-model="searchQuery"
              placeholder="Buscar..."
              icon="pi pi-search"
              clearable
              class="search-input"
            />
            <Button
              v-if="searchQuery || selectedType || selectedImportance"
              v-tooltip="'Limpiar'"
              icon="pi pi-times"
              text
              rounded
              size="small"
              @click="clearFilters"
            />
          </div>
          <div class="toolbar-row">
            <Select
              v-model="selectedType"
              :options="typeOptions"
              option-label="label"
              option-value="value"
              placeholder="Filtrar por tipo"
              class="type-filter-full"
            />
          </div>
        </div>

        <!-- Stats compactas -->
        <div class="sidebar-stats">
          <span class="stat-pill">{{ stats.filtered }}/{{ stats.total }}</span>
          <span v-if="lowRelevanceCount > 0" class="relevance-toggle-compact" @click="showOnlyRelevant = !showOnlyRelevant">
            <i :class="showOnlyRelevant ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
            <span class="relevance-count">{{ lowRelevanceCount }}</span>
          </span>
        </div>

        <!-- Lista de entidades compacta -->
        <div class="entities-list-compact">
          <DsEmptyState
            v-if="filteredEntities.length === 0 && !loading"
            icon="pi pi-users"
            title="Sin resultados"
            description="No se encontraron entidades"
          />

          <div
            v-for="entity in filteredEntities"
            :key="entity.id"
            class="entity-item-compact"
            :class="{ 'selected': selectedEntity?.id === entity.id }"
            @click="handleEntityClick(entity)"
          >
            <div class="entity-icon-small" :style="{ backgroundColor: getTypeBackgroundColor(entity.type) }">
              <i :class="getEntityIcon(entity.type)" :style="{ color: getTypeTextColor(entity.type) }"></i>
            </div>
            <div class="entity-info-compact">
              <span class="entity-name-compact">{{ entity.name }}</span>
              <span class="entity-meta-compact">
                <span
                  class="entity-type-badge"
                  :style="{
                    backgroundColor: getTypeBackgroundColor(entity.type),
                    color: getTypeTextColor(entity.type)
                  }"
                >{{ getEntityLabel(entity.type) }}</span>
                <span v-if="entity.mentionCount" class="mention-count-compact">{{ entity.mentionCount }}</span>
              </span>
            </div>
            <Tag v-if="entity.mergedFromIds && entity.mergedFromIds.length > 0" v-tooltip="'Fusionada'" severity="info" class="merged-dot">
              <i class="pi pi-link"></i>
            </Tag>
          </div>
        </div>
      </div>

      <!-- Panel central: Contenido completo de la entidad -->
      <div class="entity-content">
        <!-- Estado vacío -->
        <div v-if="!selectedEntity" class="entity-empty-state">
          <div class="empty-icon">
            <i class="pi pi-user"></i>
          </div>
          <h3>Selecciona una entidad</h3>
          <p>Elige una entidad de la lista para ver sus detalles completos</p>
        </div>

        <!-- Contenido de la entidad seleccionada -->
        <div v-else class="entity-detail">
          <!-- Header con acciones -->
          <div class="detail-header">
            <div class="detail-header-main">
              <div class="entity-icon-large" :style="{ backgroundColor: getEntityColor(selectedEntity.type) + '20' }">
                <i :class="getEntityIcon(selectedEntity.type)" :style="{ color: getEntityColor(selectedEntity.type) }"></i>
              </div>
              <div class="entity-header-info">
                <h2 class="entity-title">{{ selectedEntity.name }}</h2>
                <div class="entity-badges">
                  <DsBadge :entity-type="selectedEntity.type">{{ getEntityLabel(selectedEntity.type) }}</DsBadge>
                  <DsBadge :severity="getImportanceSeverityForBadge(selectedEntity.importance)">{{ getImportanceLabel(selectedEntity.importance) }}</DsBadge>
                  <DsBadge v-if="selectedEntity.mergedFromIds && selectedEntity.mergedFromIds.length > 0" color="info" icon="pi pi-link">
                    Fusionada
                  </DsBadge>
                </div>
              </div>
            </div>
            <div class="detail-actions">
              <Button
                icon="pi pi-pencil"
                label="Editar"
                size="small"
                outlined
                @click="onEntityEdit(selectedEntity)"
              />
              <Button
                icon="pi pi-link"
                label="Fusionar"
                size="small"
                outlined
                @click="onEntityMerge(selectedEntity)"
              />
              <Button
                v-if="selectedEntity.mergedFromIds && selectedEntity.mergedFromIds.length > 0"
                icon="pi pi-replay"
                label="Deshacer fusión"
                size="small"
                outlined
                severity="warning"
                @click="onUndoMerge(selectedEntity)"
              />
            </div>
          </div>

          <!-- Contenido principal -->
          <div class="detail-body">
            <!-- Estadísticas -->
            <div class="detail-section">
              <h4 class="section-title">Estadísticas</h4>
              <div class="stats-cards">
                <div class="stat-card">
                  <div class="stat-card-icon">
                    <i class="pi pi-comment"></i>
                  </div>
                  <div class="stat-card-content">
                    <span class="stat-card-value">{{ selectedEntity.mentionCount || 0 }}</span>
                    <span class="stat-card-label">apariciones</span>
                  </div>
                </div>
                <div v-if="formatChapterLabel(selectedEntity.firstMentionChapter, props.chapterCount)" class="stat-card">
                  <div class="stat-card-icon">
                    <i class="pi pi-bookmark"></i>
                  </div>
                  <div class="stat-card-content">
                    <span class="stat-card-value">{{ formatChapterLabel(selectedEntity.firstMentionChapter, props.chapterCount) }}</span>
                    <span class="stat-card-label">primera aparición</span>
                  </div>
                </div>
                <div v-if="selectedEntity.relevanceScore !== undefined" class="stat-card">
                  <div class="stat-card-icon">
                    <i class="pi pi-chart-line"></i>
                  </div>
                  <div class="stat-card-content">
                    <span class="stat-card-value" :class="getRelevanceClass(selectedEntity.relevanceScore)">
                      {{ formatRelevance(selectedEntity.relevanceScore) }}
                    </span>
                    <span class="stat-card-label">relevancia</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Aliases -->
            <div v-if="selectedEntity.aliases && selectedEntity.aliases.length > 0" class="detail-section">
              <h4 class="section-title">También conocido como</h4>
              <div class="aliases-grid">
                <span v-for="(alias, idx) in selectedEntity.aliases" :key="idx" class="alias-chip">
                  {{ alias }}
                </span>
              </div>
            </div>

            <!-- Descripción -->
            <div v-if="selectedEntity.description" class="detail-section">
              <h4 class="section-title">Descripción</h4>
              <p class="entity-description">{{ selectedEntity.description }}</p>
            </div>

            <!-- Atributos -->
            <div v-if="selectedEntityAttributes.length > 0" class="detail-section">
              <h4 class="section-title">Atributos</h4>
              <div class="attributes-list">
                <div
                  v-for="attr in selectedEntityAttributes"
                  :key="attr.id"
                  class="attribute-item"
                >
                  <span class="attribute-name">{{ translateAttributeName(attr.name) }}</span>
                  <span class="attribute-value">{{ attr.value }}</span>
                  <span v-if="attr.chapter" class="attribute-chapter">Cap. {{ attr.chapter }}</span>
                  <Button
                    v-if="attr.spanStart !== undefined && attr.spanStart !== null"
                    v-tooltip="'Ver en el texto'"
                    icon="pi pi-search"
                    text
                    rounded
                    size="small"
                    class="attribute-nav-btn"
                    @click.stop="navigateToAttributeSource(attr)"
                  />
                </div>
              </div>
            </div>
            <div v-else-if="loadingAttributes" class="detail-section">
              <h4 class="section-title">Atributos</h4>
              <p class="loading-text">Cargando atributos...</p>
            </div>

            <!-- Acción ver en texto -->
            <div v-if="selectedEntity.mentionCount && selectedEntity.mentionCount > 0" class="detail-section">
              <h4 class="section-title">Apariciones</h4>
              <Button
                label="Ver en el texto"
                icon="pi pi-search"
                outlined
                @click="viewMentions(selectedEntity)"
              />
            </div>

            <!-- Información de fusión -->
            <div v-if="selectedEntity.mergedFromIds && selectedEntity.mergedFromIds.length > 0" class="detail-section merged-info-section">
              <h4 class="section-title">Información de fusión</h4>
              <div class="merged-info-content">
                <i class="pi pi-info-circle"></i>
                <p>Esta entidad fue creada fusionando {{ selectedEntity.mergedFromIds.length }} entidades originales. Puedes deshacer esta fusión para restaurarlas.</p>
              </div>
            </div>
          </div>

          <!-- Footer con acciones secundarias -->
          <div class="detail-footer">
            <Button
              icon="pi pi-ban"
              label="Rechazar como falso positivo"
              size="small"
              text
              severity="warning"
              @click="onRejectEntity(selectedEntity)"
            />
            <Button
              icon="pi pi-trash"
              label="Eliminar entidad"
              size="small"
              text
              severity="danger"
              @click="onEntityDelete(selectedEntity)"
            />
          </div>
        </div>
      </div>

      <!-- Acciones globales flotantes -->
      <div class="floating-actions">
        <Button
          v-tooltip.left="'Historial de fusiones'"
          icon="pi pi-history"
          text
          rounded
          @click="showMergeHistory = true"
        />
        <Button
          v-tooltip.left="'Exportar entidades'"
          icon="pi pi-download"
          text
          rounded
          @click="exportEntities"
        />
        <Button
          v-tooltip.left="'Actualizar'"
          icon="pi pi-refresh"
          text
          rounded
          @click="emit('refresh')"
        />
      </div>
    </div>

    <!-- Diálogo de edición -->
    <Dialog
      v-model:visible="showEditDialog"
      modal
      header="Editar Entidad"
      :style="{ width: '500px' }"
    >
      <div v-if="editingEntity" class="edit-dialog">
        <div class="field">
          <label>Nombre canónico *</label>
          <InputText v-model="editingEntity.name" class="w-full" />
        </div>

        <div class="field">
          <label>Tipo de entidad</label>
          <Select
            v-model="editingEntity.type"
            :options="entityTypeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Importancia</label>
          <SelectButton
            v-model="editingEntity.importance"
            :options="importanceEditOptions"
            option-label="label"
            option-value="value"
          />
        </div>

        <div class="field">
          <label>Nombres alternativos</label>
          <Chips
            v-model="editingEntity.aliases"
            placeholder="Añadir alias y presionar Enter"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" icon="pi pi-times" text @click="showEditDialog = false" />
        <Button label="Guardar" icon="pi pi-check" @click="saveEntity" />
      </template>
    </Dialog>

    <!-- Diálogo de fusión -->
    <MergeEntitiesDialog
      :visible="showMergeDialog"
      :project-id="projectId"
      :available-entities="entities"
      :preselected-entities="selectedEntitiesForMerge"
      @update:visible="showMergeDialog = $event"
      @merge="onMergeEntities"
      @cancel="showMergeDialog = false"
    />

    <!-- Diálogo de deshacer fusión -->
    <UndoMergeDialog
      :visible="showUndoMergeDialog"
      :project-id="projectId"
      :entity="entityToUndoMerge"
      @update:visible="showUndoMergeDialog = $event"
      @undo-complete="onUndoMergeComplete"
    />

    <!-- Diálogo de rechazo de entidad -->
    <RejectEntityDialog
      v-model:visible="showRejectDialog"
      :entity-name="entityToReject?.name || ''"
      :entity-type="entityToReject?.type"
      :project-id="projectId"
      :mention-count="entityToReject?.mentionCount || 0"
      @reject="handleRejectEntity"
    />

    <!-- Panel de historial de fusiones -->
    <Drawer
      v-model:visible="showMergeHistory"
      position="right"
      :style="{ width: '400px' }"
      header="Historial de Fusiones"
    >
      <MergeHistoryPanel
        ref="mergeHistoryRef"
        :project-id="projectId"
        @undo="onUndoMergeFromHistory"
      />
    </Drawer>
  </div>
</template>

<style scoped>
.entities-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header */
.entities-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.entities-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
}

.header-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-tip {
  color: var(--primary-color);
  cursor: help;
}

/* Layout de 2 columnas */
.entities-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Panel izquierdo - Lista */
.entities-sidebar {
  width: 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.sidebar-toolbar {
  padding: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.toolbar-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.type-filter-full {
  width: 100%;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.search-wrapper .pi-search {
  position: absolute;
  right: 0.5rem;
  color: var(--text-color-secondary);
  pointer-events: none;
  font-size: 0.75rem;
}

.search-input {
  width: 100%;
  padding-right: 2rem;
  font-size: 0.8125rem;
}

:deep(.search-input.p-inputtext) {
  padding: 0.375rem 0.5rem;
  padding-right: 1.75rem;
}

.type-filter {
  width: 90px;
  flex-shrink: 0;
}

:deep(.type-filter .p-dropdown-label) {
  padding: 0.375rem 0.5rem;
  font-size: 0.8125rem;
}

:deep(.type-filter .p-dropdown-trigger) {
  width: 1.5rem;
}

.sidebar-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.stat-pill {
  font-weight: 600;
}

.relevance-toggle-compact {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.relevance-toggle-compact:hover {
  background: var(--surface-100);
}

/* Lista compacta */
.entities-list-compact {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.entity-item-compact {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.entity-item-compact:hover {
  background: var(--surface-hover);
}

.entity-item-compact.selected {
  background: var(--primary-50);
}

.entity-icon-small {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-100);
  border-radius: 8px;
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 2px;
}

.entity-icon-small i {
  font-size: 1rem;
  color: var(--text-color-secondary);
}

.entity-info-compact {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.entity-name-compact {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entity-meta-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entity-type-badge {
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: capitalize;
}

.mention-count-compact {
  color: var(--primary-color);
  font-weight: 500;
}

.merged-dot {
  font-size: 0.5rem;
  padding: 0.125rem 0.25rem;
}

/* Panel central - Contenido */
.entity-content {
  flex: 1;
  overflow-y: auto;
  background: var(--surface-ground);
}

.entity-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-100);
  border-radius: 50%;
  margin-bottom: 1rem;
}

.empty-icon i {
  font-size: 1.5rem;
  color: var(--text-color-secondary);
}

.entity-empty-state h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  color: var(--text-color);
}

.entity-empty-state p {
  margin: 0;
  font-size: 0.875rem;
}

/* Detalle de entidad */
.entity-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
  gap: 1rem;
  flex-wrap: wrap;
}

.detail-header-main {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.entity-icon-large {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  flex-shrink: 0;
}

.entity-icon-large i {
  font-size: 1.5rem;
}

.entity-header-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.entity-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.detail-body {
  flex: 1;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.section-title {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stats-cards {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
}

.stat-card-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 8px;
}

.stat-card-icon i {
  color: var(--primary-color);
}

.stat-card-content {
  display: flex;
  flex-direction: column;
}

.stat-card-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.stat-card-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.aliases-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.alias-chip {
  padding: 0.375rem 0.75rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  font-size: 0.875rem;
}

.entity-description {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-color);
}

/* Atributos */
.attributes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.attribute-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.attribute-name {
  font-weight: 500;
  color: var(--text-color);
  min-width: 100px;
}

.attribute-value {
  flex: 1;
  color: var(--text-color);
}

.attribute-chapter {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-100);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.attribute-nav-btn {
  flex-shrink: 0;
  width: 1.75rem !important;
  height: 1.75rem !important;
  padding: 0 !important;
}

.attribute-nav-btn :deep(.p-button-icon) {
  font-size: 0.75rem;
}

.loading-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.merged-info-section {
  background: var(--blue-50);
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--blue-200);
}

.merged-info-content {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.merged-info-content i {
  color: var(--blue-600);
  font-size: 1rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.merged-info-content p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--blue-700);
  line-height: 1.5;
}

.detail-footer {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--surface-border);
  background: var(--surface-card);
}

/* Acciones flotantes - WCAG compliant */
.floating-actions {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: #ffffff !important; /* Fondo blanco fijo en light mode */
  padding: 0.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

/* Dark mode: fondo oscuro fijo */
.dark .floating-actions {
  background: #1e293b !important; /* slate-800 fijo */
  border-color: rgba(255, 255, 255, 0.1);
}

/* Botones dentro de floating-actions con color fijo para contraste */
.floating-actions :deep(.p-button) {
  color: #1e40af !important; /* blue-800: 8.5:1 on white */
}

.floating-actions :deep(.p-button:hover) {
  color: #1d4ed8 !important;
  background: rgba(59, 130, 246, 0.12) !important;
}

/* Dark mode icon color */
.dark .floating-actions :deep(.p-button) {
  color: #93c5fd !important; /* blue-300: high contrast on dark */
}

.dark .floating-actions :deep(.p-button:hover) {
  color: #bfdbfe !important;
  background: rgba(147, 197, 253, 0.15) !important;
}

/* Relevancia */
.relevance-high { color: var(--green-600); }
.relevance-medium { color: var(--blue-600); }
.relevance-low { color: var(--orange-600); }
.relevance-very-low { color: var(--red-500); }

/* Diálogos */
.edit-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  color: var(--text-color);
}

.w-full {
  width: 100%;
}

/* Dark mode */
.dark .entity-icon {
  background: var(--surface-700);
}

.dark .entity-item.selected {
  background: var(--primary-900);
  border-color: var(--primary-700);
}
</style>
