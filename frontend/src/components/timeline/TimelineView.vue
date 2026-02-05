<template>
  <div class="timeline-view">
    <!-- Toolbar -->
    <div class="timeline-toolbar">
      <div class="toolbar-left">
        <h3>
          <i class="pi pi-clock"></i>
          Timeline Temporal
        </h3>
        <div class="toolbar-stats">
          <Tag v-if="timeline" severity="info">
            {{ timeline.events.length }} eventos
          </Tag>
          <Tag v-if="timeline && timeline.anchorCount > 0" severity="success">
            {{ timeline.anchorCount }} anclas
          </Tag>
          <Tag v-if="timeline && timeline.analepsiCount > 0" severity="secondary" class="stat-analepsis">
            {{ timeline.analepsiCount }} analepsis
          </Tag>
          <Tag v-if="timeline && timeline.prolepsiCount > 0" severity="warn" class="stat-prolepsis">
            {{ timeline.prolepsiCount }} prolepsis
          </Tag>
        </div>
      </div>
      <div class="toolbar-right">
        <!-- View Mode Toggle -->
        <SelectButton
          v-model="viewMode"
          :options="viewModeOptions"
          option-label="label"
          option-value="value"
          class="view-mode-toggle"
          :allow-empty="false"
        >
          <template #option="{ option }">
            <i v-tooltip.bottom="option.tooltip" :class="option.icon"></i>
          </template>
        </SelectButton>

        <Select
          v-if="viewMode === 'list'"
          v-model="sortOrder"
          :options="sortOptions"
          option-label="label"
          option-value="value"
          placeholder="Ordenar por"
          class="sort-dropdown"
        />
        <Select
          v-if="viewMode === 'list'"
          v-model="filterNarrativeOrder"
          :options="narrativeOrderOptions"
          option-label="label"
          option-value="value"
          placeholder="Filtrar tipo"
          class="filter-dropdown"
          show-clear
        />
        <Button
          v-tooltip.bottom="'Recargar timeline'"
          icon="pi pi-refresh"
          text
          rounded
          :loading="loading"
          @click="loadTimeline"
        />
        <Button
          v-tooltip.bottom="'Exportar timeline'"
          icon="pi pi-download"
          text
          rounded
          @click="exportTimeline"
        />
      </div>
    </div>

    <!-- Time Span Info -->
    <div v-if="timeline && timeline.timeSpan" class="time-span-info">
      <div class="time-span-content">
        <i class="pi pi-calendar-plus"></i>
        <!-- Si hay fechas reales, mostrar rango completo -->
        <span v-if="timeline.timeSpan.hasRealDates && timeline.timeSpan.start && timeline.timeSpan.end">
          La historia abarca desde
          <strong>{{ formatDateShort(timeline.timeSpan.start) }}</strong>
          hasta
          <strong>{{ formatDateShort(timeline.timeSpan.end) }}</strong>
          ({{ formatDuration(timeline.timeSpan.durationDays) }})
        </span>
        <!-- Si son fechas sintéticas, mostrar solo la duración -->
        <span v-else>
          La historia abarca <strong>{{ formatDuration(timeline.timeSpan.durationDays) }}</strong>
          <span class="synthetic-note">(sin fechas absolutas definidas)</span>
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" />
      <p>Analizando marcadores temporales...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle error-icon"></i>
      <h4>Error al cargar el timeline</h4>
      <p class="error-message">{{ error }}</p>
      <Button
        label="Reintentar"
        icon="pi pi-refresh"
        outlined
        @click="loadTimeline"
      />
    </div>

    <!-- Empty State -->
    <div v-else-if="!timeline || timeline.events.length === 0" class="empty-state">
      <i class="pi pi-clock empty-icon"></i>
      <h4>No hay eventos temporales</h4>
      <p class="empty-description">
        No se han detectado marcadores temporales en el texto.
      </p>
      <div class="empty-reasons">
        <p><strong>Esto puede ocurrir porque:</strong></p>
        <ul>
          <li>El texto es demasiado corto para contener referencias temporales</li>
          <li>La narrativa no incluye fechas, horas o marcadores como "ayer", "la semana pasada", etc.</li>
          <li>Los eventos temporales no siguen patrones reconocibles</li>
        </ul>
      </div>
      <p class="empty-tip">
        <i class="pi pi-info-circle"></i>
        Para generar una linea temporal, el texto debe contener referencias temporales explicitas
        como fechas, estaciones, o expresiones como "tres dias despues".
      </p>
      <Button
        label="Recargar"
        icon="pi pi-refresh"
        outlined
        @click="loadTimeline"
      />
    </div>

    <!-- Main Content -->
    <div v-else class="timeline-content">
      <!-- Vista Horizontal (vis-timeline) -->
      <template v-if="viewMode === 'horizontal'">
        <VisTimeline
          :events="filteredEvents"
          :entities="entities"
          @event-select="handleEventClick"
          @navigate-to-text="(pos) => emit('navigateToText', pos)"
        />
      </template>

      <!-- Vista Lista -->
      <template v-else>
        <!-- Leyenda -->
        <div class="timeline-legend">
          <div class="legend-item">
            <span class="legend-dot chronological"></span>
            <span>Cronologico</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot analepsis"></span>
            <span>Analepsis (Flashback)</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot prolepsis"></span>
            <span>Prolepsis (Flashforward)</span>
          </div>
        </div>

        <!-- Toggle de agrupación -->
        <div class="group-toggle">
          <label class="toggle-label">
            <input v-model="groupByChapter" type="checkbox" />
            <span>Agrupar por capítulo</span>
          </label>
        </div>

        <!-- Lista de eventos agrupados por capítulo -->
        <div v-if="groupByChapter" class="events-list grouped">
          <div
            v-for="group in groupedEvents"
            :key="group.chapter"
            class="chapter-group"
          >
            <div
              class="chapter-header"
              @click="toggleGroupExpansion(group.chapter)"
            >
              <i :class="group.isExpanded ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
              <span class="chapter-title">{{ group.title }}</span>
              <Tag severity="secondary" class="event-count">
                {{ group.events.length }} evento{{ group.events.length !== 1 ? 's' : '' }}
              </Tag>
            </div>
            <div v-if="group.isExpanded" class="chapter-events">
              <TimelineEventVue
                v-for="(event, index) in group.events"
                :key="event.id"
                :event="event"
                :entity-names="getEntityNames(event.entityIds)"
                :is-selected="selectedEvent?.id === event.id"
                :is-hovered="hoveredEvent?.id === event.id"
                :show-connector="index < group.events.length - 1"
                @click="handleEventClick"
                @hover="handleEventHover"
              />
            </div>
          </div>
        </div>

        <!-- Lista de eventos sin agrupar -->
        <div v-else class="events-list">
          <TimelineEventVue
            v-for="(event, index) in filteredEvents"
            :key="event.id"
            :event="event"
            :entity-names="getEntityNames(event.entityIds)"
            :is-selected="selectedEvent?.id === event.id"
            :is-hovered="hoveredEvent?.id === event.id"
            :show-connector="index < filteredEvents.length - 1"
            @click="handleEventClick"
            @hover="handleEventHover"
          />
        </div>
      </template>

      <!-- Panel de Inconsistencias -->
      <div v-if="timeline.inconsistencies.length > 0" class="inconsistencies-panel">
        <div class="panel-header">
          <i class="pi pi-exclamation-triangle"></i>
          <h4>Inconsistencias Detectadas ({{ timeline.inconsistencies.length }})</h4>
        </div>
        <div class="inconsistencies-list">
          <div
            v-for="(inc, index) in timeline.inconsistencies"
            :key="index"
            class="inconsistency-item"
            :class="`severity-${inc.severity}`"
          >
            <div class="inconsistency-header">
              <Tag :severity="getSeverityColor(inc.severity)">
                {{ getSeverityLabel(inc.severity) }}
              </Tag>
              <span class="inconsistency-chapter">Capitulo {{ inc.chapter }}</span>
            </div>
            <p class="inconsistency-description">{{ inc.description }}</p>
            <div v-if="inc.expected || inc.found" class="inconsistency-details">
              <div v-if="inc.expected" class="detail-item">
                <span class="detail-label">Esperado:</span>
                <span>{{ inc.expected }}</span>
              </div>
              <div v-if="inc.found" class="detail-item">
                <span class="detail-label">Encontrado:</span>
                <span>{{ inc.found }}</span>
              </div>
            </div>
            <p v-if="inc.suggestion" class="inconsistency-suggestion">
              <i class="pi pi-lightbulb"></i>
              {{ inc.suggestion }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Selected Event Detail Panel -->
    <Dialog
      v-model:visible="showEventDetail"
      :header="selectedEvent?.description || 'Detalle del Evento'"
      :style="{ width: '500px' }"
      modal
    >
      <div v-if="selectedEvent" class="event-detail">
        <div class="detail-section">
          <h5>Informacion Temporal</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Fecha en la historia:</span>
              <!-- Fecha absoluta -->
              <span v-if="selectedEvent.storyDate && selectedEvent.storyDate.getFullYear() > 1">
                {{ formatDateFull(selectedEvent.storyDate) }}
              </span>
              <!-- Day offset (Día 0, Día +1, etc.) -->
              <span v-else-if="selectedEvent.dayOffset !== null">
                {{ formatDayOffset(selectedEvent.dayOffset, selectedEvent.weekday) }}
              </span>
              <!-- No determinada -->
              <span v-else class="unknown">No determinada</span>
            </div>
            <div class="detail-item">
              <span class="label">Resolucion:</span>
              <span>{{ getResolutionLabel(selectedEvent.storyDateResolution) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Tipo narrativo:</span>
              <Tag :severity="getNarrativeOrderSeverity(selectedEvent.narrativeOrder)">
                {{ getNarrativeOrderLabel(selectedEvent.narrativeOrder) }}
              </Tag>
            </div>
          </div>
        </div>

        <Divider />

        <div class="detail-section">
          <h5>Ubicacion en el Texto</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Capitulo:</span>
              <span>{{ selectedEvent.chapter }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Parrafo:</span>
              <span>{{ selectedEvent.paragraph || 'No especificado' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Confianza:</span>
              <span :class="getConfidenceClass(selectedEvent.confidence)">
                {{ Math.round(selectedEvent.confidence * 100) }}%
              </span>
            </div>
          </div>
        </div>

        <div v-if="selectedEvent.entityIds.length > 0">
          <Divider />
          <div class="detail-section">
            <h5>Personajes Involucrados</h5>
            <div class="entity-chips">
              <Chip
                v-for="entityId in selectedEvent.entityIds"
                :key="entityId"
                :label="getEntityName(entityId)"
                class="entity-chip"
              />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Ir al texto"
          icon="pi pi-arrow-right"
          @click="navigateToText"
        />
        <Button
          label="Cerrar"
          icon="pi pi-times"
          text
          @click="showEventDetail = false"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import Chip from 'primevue/chip'
import TimelineEventVue from './TimelineEvent.vue'
import VisTimeline from './VisTimeline.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { transformTimeline } from '@/types/transformers'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { apiUrl } from '@/config/api'
import type {
  Timeline,
  TimelineEvent,
  NarrativeOrder,
  TimelineResolution,
  InconsistencySeverity,
  AlertSeverity
} from '@/types'

const props = defineProps<{
  projectId: number
  entities?: Array<{ id: number; name: string }>
}>()

const emit = defineEmits<{
  eventSelect: [event: TimelineEvent]
  navigateToText: [position: number]
}>()

const workspaceStore = useWorkspaceStore()
const { getSeverityConfig } = useAlertUtils()

// Estado
const loading = ref(false)
const error = ref<string | null>(null)
const timeline = ref<Timeline | null>(null)
const selectedEvent = ref<TimelineEvent | null>(null)
const hoveredEvent = ref<TimelineEvent | null>(null)
const showEventDetail = ref(false)

// View mode: list (vertical) or horizontal (vis-timeline)
type ViewMode = 'list' | 'horizontal'
const viewMode = ref<ViewMode>('list')
const viewModeOptions = [
  { label: 'Lista', value: 'list', icon: 'pi pi-list', tooltip: 'Vista de lista vertical' },
  { label: 'Horizontal', value: 'horizontal', icon: 'pi pi-arrows-h', tooltip: 'Vista horizontal interactiva' },
]

// Filtros y ordenamiento
const sortOrder = ref<'chronological' | 'discourse'>('chronological')
const filterNarrativeOrder = ref<NarrativeOrder | null>(null)

const sortOptions = [
  { label: 'Orden cronologico', value: 'chronological' },
  { label: 'Orden del texto', value: 'discourse' }
]

const narrativeOrderOptions = [
  { label: 'Cronologico', value: 'chronological' },
  { label: 'Analepsis', value: 'analepsis' },
  { label: 'Prolepsis', value: 'prolepsis' }
]

// Agrupación por capítulo
const groupByChapter = ref(true)  // Agrupar eventos por capítulo por defecto

interface ChapterGroup {
  chapter: number
  title: string
  events: TimelineEvent[]
  isExpanded: boolean
}

// Eventos agrupados por capítulo
const groupedEvents = computed<ChapterGroup[]>(() => {
  if (!timeline.value || !groupByChapter.value) return []

  const groups = new Map<number, ChapterGroup>()

  for (const event of filteredEvents.value) {
    const chapter = event.chapter || 0
    if (!groups.has(chapter)) {
      groups.set(chapter, {
        chapter,
        title: `Capítulo ${chapter}`,
        events: [],
        isExpanded: true,
      })
    }
    groups.get(chapter)!.events.push(event)
  }

  // Ordenar grupos por número de capítulo
  return Array.from(groups.values()).sort((a, b) => a.chapter - b.chapter)
})

// Toggle expansión de grupo
const toggleGroupExpansion = (chapter: number) => {
  const group = groupedEvents.value.find(g => g.chapter === chapter)
  if (group) {
    group.isExpanded = !group.isExpanded
  }
}

// Eventos filtrados y ordenados
const filteredEvents = computed(() => {
  if (!timeline.value) return []

  let events = [...timeline.value.events]

  // Filtrar por tipo narrativo
  if (filterNarrativeOrder.value) {
    events = events.filter(e => e.narrativeOrder === filterNarrativeOrder.value)
  }

  // Ordenar
  if (sortOrder.value === 'chronological') {
    events.sort((a, b) => {
      // Prioridad: storyDate > dayOffset > sin tiempo
      const aHasDate = a.storyDate && a.storyDate.getFullYear() > 1
      const bHasDate = b.storyDate && b.storyDate.getFullYear() > 1
      const aHasOffset = a.dayOffset !== null
      const bHasOffset = b.dayOffset !== null

      // Si ambos tienen fecha real
      if (aHasDate && bHasDate) {
        return a.storyDate!.getTime() - b.storyDate!.getTime()
      }
      // Si ambos tienen day_offset
      if (aHasOffset && bHasOffset) {
        return a.dayOffset! - b.dayOffset!
      }
      // Priorizar los que tienen tiempo conocido
      if (aHasDate || aHasOffset) return -1
      if (bHasDate || bHasOffset) return 1
      return 0
    })
  } else {
    events.sort((a, b) => a.discoursePosition - b.discoursePosition)
  }

  return events
})

// Cargar timeline
const loadTimeline = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/timeline`))
    const data = await response.json()

    if (data.success && data.data) {
      timeline.value = transformTimeline(data.data)
    } else {
      console.error('Error loading timeline:', data.error)
      error.value = data.error || 'Error al cargar el timeline'
      timeline.value = null
    }
  } catch (err) {
    console.error('Error fetching timeline:', err)
    error.value = err instanceof Error ? err.message : 'Error de conexión'
    timeline.value = null
  } finally {
    loading.value = false
  }
}

// Formatear fechas
const formatDateShort = (date: Date): string => {
  // Para fechas sinteticas (ano 1), mostrar como "Dia X"
  if (date.getFullYear() === 1) {
    const baseDate = new Date(1, 0, 1)
    const diffTime = date.getTime() - baseDate.getTime()
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24))
    return `Dia ${diffDays}`
  }
  return new Intl.DateTimeFormat('es-ES', {
    year: 'numeric',
    month: 'long'
  }).format(date)
}

const formatDateFull = (date: Date): string => {
  // Para fechas sinteticas (ano 1), no deberían llegar aquí
  // pero por compatibilidad con datos antiguos
  if (date.getFullYear() === 1) {
    return 'Fecha relativa'
  }
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  }).format(date)
}

// Formato para eventos con day_offset (Día 0, Día +1, etc.)
const formatDayOffset = (offset: number, weekday: string | null): string => {
  let result = ''
  if (offset === 0) {
    result = 'Día 0'
  } else if (offset > 0) {
    result = `Día +${offset}`
  } else {
    result = `Día ${offset}`
  }

  // Añadir día de la semana si está disponible
  if (weekday) {
    result += ` (${weekday})`
  }

  return result
}

// Formatear duración en días a texto legible
const formatDuration = (days: number): string => {
  if (days < 1) {
    return 'menos de 1 día'
  } else if (days === 1) {
    return '1 día'
  } else if (days < 30) {
    return `${days} días`
  } else if (days < 365) {
    const months = Math.floor(days / 30)
    const remainingDays = days % 30
    if (remainingDays > 0 && months < 3) {
      return `${months} mes${months > 1 ? 'es' : ''} y ${remainingDays} día${remainingDays > 1 ? 's' : ''}`
    }
    return `${months} mes${months > 1 ? 'es' : ''}`
  } else {
    const years = Math.floor(days / 365)
    const remainingMonths = Math.floor((days % 365) / 30)
    if (remainingMonths > 0) {
      return `${years} año${years > 1 ? 's' : ''} y ${remainingMonths} mes${remainingMonths > 1 ? 'es' : ''}`
    }
    return `${years} año${years > 1 ? 's' : ''}`
  }
}

// Obtener nombre de entidad
const getEntityName = (entityId: number): string => {
  if (props.entities) {
    const entity = props.entities.find(e => e.id === entityId)
    if (entity) return entity.name
  }
  return `Entidad ${entityId}`
}

const getEntityNames = (entityIds: number[]): string[] => {
  return entityIds.map(id => getEntityName(id))
}

// Helpers para labels y colores
const getNarrativeOrderSeverity = (order: NarrativeOrder): string => {
  switch (order) {
    case 'chronological': return 'success'
    case 'analepsis': return 'info'
    case 'prolepsis': return 'warn'
    default: return 'secondary'
  }
}

const getNarrativeOrderLabel = (order: NarrativeOrder): string => {
  switch (order) {
    case 'chronological': return 'Cronologico'
    case 'analepsis': return 'Analepsis'
    case 'prolepsis': return 'Prolepsis'
    default: return order
  }
}

const getResolutionLabel = (resolution: TimelineResolution): string => {
  switch (resolution) {
    case 'exact_date': return 'Fecha exacta'
    case 'month': return 'Mes'
    case 'year': return 'Ano'
    case 'season': return 'Estacion'
    case 'partial': return 'Parcial (sin año)'
    case 'relative': return 'Relativa'
    case 'unknown': return 'Desconocida'
    default: return resolution
  }
}

const getSeverityColor = (severity: InconsistencySeverity): string => {
  switch (severity) {
    case 'critical': return 'danger'
    case 'high': return 'danger'
    case 'medium': return 'warn'
    case 'low': return 'info'
    default: return 'secondary'
  }
}

// Usar composable centralizado
const getSeverityLabel = (severity: InconsistencySeverity): string => {
  return getSeverityConfig(severity as AlertSeverity).label
}

const getConfidenceClass = (confidence: number): string => {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.5) return 'confidence-medium'
  return 'confidence-low'
}

// Handlers
const handleEventClick = (event: TimelineEvent) => {
  selectedEvent.value = event
  showEventDetail.value = true
  emit('eventSelect', event)
}

const handleEventHover = (event: TimelineEvent | null) => {
  hoveredEvent.value = event
}

const navigateToText = () => {
  if (selectedEvent.value) {
    workspaceStore.navigateToTextPosition(selectedEvent.value.discoursePosition)
    emit('navigateToText', selectedEvent.value.discoursePosition)
    showEventDetail.value = false
  }
}

const exportTimeline = () => {
  if (!timeline.value) return

  const ts = timeline.value.timeSpan
  const exportData = {
    projectId: props.projectId,
    exportedAt: new Date().toISOString(),
    summary: {
      totalEvents: timeline.value.events.length,
      anchors: timeline.value.anchorCount,
      analepsis: timeline.value.analepsiCount,
      prolepsis: timeline.value.prolepsiCount,
      timeSpan: ts
        ? {
            start: ts.start?.toISOString() || null,
            end: ts.end?.toISOString() || null,
            durationDays: ts.durationDays,
            isSynthetic: ts.isSynthetic,
            hasRealDates: ts.hasRealDates
          }
        : null
    },
    events: timeline.value.events.map(e => ({
      ...e,
      storyDate: e.storyDate?.toISOString() || null
    })),
    inconsistencies: timeline.value.inconsistencies,
    mermaid: timeline.value.mermaid
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `timeline_proyecto_${props.projectId}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Lifecycle
onMounted(() => {
  loadTimeline()
})

// Watch para recargar cuando cambie el proyecto
watch(() => props.projectId, () => {
  loadTimeline()
})
</script>

<style scoped>
.timeline-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-ground);
  overflow: hidden;
}

/* Toolbar */
.timeline-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-200);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.toolbar-left h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-left h3 i {
  color: var(--primary-color);
}

.toolbar-stats {
  display: flex;
  gap: 0.5rem;
}

.stat-analepsis :deep(.p-tag) {
  background: #3b82f6 !important;
}

.stat-prolepsis :deep(.p-tag) {
  background: #f59e0b !important;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-dropdown,
.filter-dropdown {
  width: 160px;
}

/* View Mode Toggle */
.view-mode-toggle {
  margin-right: 0.5rem;
}

.view-mode-toggle :deep(.p-button) {
  padding: 0.5rem 0.75rem;
}

.view-mode-toggle :deep(.p-button i) {
  font-size: 1rem;
}

/* Time Span Info */
.time-span-info {
  padding: 0.75rem 1.5rem;
  background: var(--primary-50);
  border-bottom: 1px solid var(--primary-100);
}

.time-span-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--primary-700);
  font-size: 0.9375rem;
}

.time-span-content i {
  font-size: 1.25rem;
}

.synthetic-note {
  font-size: 0.8125rem;
  color: var(--primary-500);
  font-style: italic;
  margin-left: 0.25rem;
}

/* Loading, Error & Empty States */
.loading-state,
.error-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.4;
}

.error-icon {
  font-size: 3rem;
  color: var(--red-500);
  opacity: 0.7;
}

.error-state h4 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-color);
}

.error-message {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--red-500);
  max-width: 400px;
  text-align: center;
}

.empty-state h4 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-color);
}

.empty-state p {
  margin: 0;
  font-size: 0.9375rem;
}

.empty-description {
  margin-bottom: 0.5rem;
}

.empty-reasons {
  text-align: left;
  background: var(--surface-50);
  padding: 1rem 1.5rem;
  border-radius: 8px;
  margin: 0.5rem 0;
  max-width: 500px;
}

.empty-reasons p {
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.empty-reasons ul {
  margin: 0;
  padding-left: 1.25rem;
  color: var(--text-color-secondary);
}

.empty-reasons li {
  margin-bottom: 0.25rem;
  line-height: 1.5;
}

.empty-tip {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  max-width: 450px;
  text-align: left;
  padding: 0.75rem 1rem;
  background: var(--blue-50);
  border-radius: 6px;
  color: var(--blue-700);
  font-size: 0.875rem;
  margin: 0.5rem 0 1rem 0;
}

.empty-tip i {
  margin-top: 0.125rem;
  flex-shrink: 0;
}

/* Main Content */
.timeline-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

/* Legend */
.timeline-legend {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.chronological {
  background: #10b981;
}

.legend-dot.analepsis {
  background: #3b82f6;
}

.legend-dot.prolepsis {
  background: #f59e0b;
}

/* Group Toggle */
.group-toggle {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  user-select: none;
}

.toggle-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--primary-color);
}

.toggle-label:hover {
  color: var(--text-color);
}

/* Events List */
.events-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.events-list.grouped {
  gap: 0.5rem;
}

/* Chapter Groups */
.chapter-group {
  background: var(--surface-card);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
  overflow: hidden;
}

.chapter-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: var(--surface-50);
  cursor: pointer;
  transition: background-color 0.15s ease;
  border-bottom: 1px solid transparent;
}

.chapter-header:hover {
  background: var(--surface-100);
}

.chapter-header i {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  transition: transform 0.2s ease;
}

.chapter-title {
  flex: 1;
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
}

.event-count {
  font-size: 0.75rem;
}

.chapter-events {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-top: 1px solid var(--surface-200);
  background: var(--surface-ground);
}

/* Inconsistencies Panel */
.inconsistencies-panel {
  margin-top: 2rem;
  background: var(--surface-card);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
  overflow: hidden;
}

.inconsistencies-panel .panel-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: #fef3c7;
  border-bottom: 1px solid #fcd34d;
}

.inconsistencies-panel .panel-header i {
  color: #d97706;
  font-size: 1.25rem;
}

.inconsistencies-panel .panel-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #92400e;
}

.inconsistencies-list {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.inconsistency-item {
  padding: 1rem;
  border-radius: 6px;
  background: var(--surface-50);
  border-left: 4px solid;
}

.inconsistency-item.severity-critical {
  border-color: #dc2626;
  background: #fef2f2;
}

.inconsistency-item.severity-high {
  border-color: #ef4444;
  background: #fef2f2;
}

.inconsistency-item.severity-medium {
  border-color: var(--ds-alert-medium-border, #f59e0b);
  background: var(--ds-alert-medium-bg, #fffbeb);
}

.inconsistency-item.severity-low {
  border-color: var(--ds-alert-low-border, #3b82f6);
  background: var(--ds-alert-low-bg, #eff6ff);
}

.inconsistency-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.inconsistency-chapter {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.inconsistency-description {
  margin: 0 0 0.75rem 0;
  font-size: 0.9375rem;
  color: var(--text-color);
  line-height: 1.5;
}

.inconsistency-details {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  background: var(--p-surface-0, white);
  border-radius: 4px;
}

.inconsistency-details .detail-item {
  font-size: 0.8125rem;
}

.inconsistency-details .detail-label {
  font-weight: 600;
  margin-right: 0.5rem;
  color: var(--text-color-secondary);
}

.inconsistency-suggestion {
  margin: 0;
  font-size: 0.8125rem;
  color: #059669;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.inconsistency-suggestion i {
  margin-top: 0.125rem;
}

/* Event Detail Dialog */
.event-detail {
  padding: 0.5rem 0;
}

.detail-section {
  margin-bottom: 1rem;
}

.detail-section h5 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item .label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.detail-item .unknown {
  font-style: italic;
  color: var(--text-color-secondary);
}

.entity-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.entity-chip {
  font-size: 0.875rem;
}

.confidence-high {
  color: #10b981;
  font-weight: 600;
}

.confidence-medium {
  color: #f59e0b;
  font-weight: 600;
}

.confidence-low {
  color: #ef4444;
  font-weight: 600;
}

/* Responsive */
@media (max-width: 768px) {
  .timeline-toolbar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }

  .toolbar-stats {
    flex-wrap: wrap;
    justify-content: center;
  }

  .timeline-legend {
    flex-wrap: wrap;
    justify-content: center;
  }

  .sort-dropdown,
  .filter-dropdown {
    width: 140px;
  }
}
</style>
