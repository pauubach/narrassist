<template>
  <div class="vis-timeline-container">
    <!-- Toolbar -->
    <div class="vis-toolbar">
      <div class="toolbar-left">
        <Select
          v-model="groupBy"
          :options="groupByOptions"
          option-label="label"
          option-value="value"
          placeholder="Agrupar por"
          class="group-dropdown"
        />
        <Button
          v-tooltip.bottom="'Acercar'"
          icon="pi pi-search-plus"
          text
          rounded
          size="small"
          @click="zoomIn"
        />
        <Button
          v-tooltip.bottom="'Alejar'"
          icon="pi pi-search-minus"
          text
          rounded
          size="small"
          @click="zoomOut"
        />
        <Button
          v-tooltip.bottom="'Ver todo'"
          icon="pi pi-arrows-h"
          text
          rounded
          size="small"
          @click="fitAll"
        />
      </div>
      <div class="toolbar-right">
        <div class="legend">
          <span class="legend-item">
            <span class="dot chronological"></span> Cronológico
          </span>
          <span class="legend-item">
            <span class="dot analepsis"></span> Analepsis
          </span>
          <span class="legend-item">
            <span class="dot prolepsis"></span> Prolepsis
          </span>
        </div>
      </div>
    </div>

    <!-- Timeline Container -->
    <div ref="timelineContainer" class="timeline-element"></div>

    <!-- Event Detail Tooltip -->
    <div
      v-if="hoveredEvent"
      class="event-tooltip"
      :style="tooltipStyle"
    >
      <div class="tooltip-header">
        <Tag :severity="getNarrativeOrderSeverity(hoveredEvent.narrativeOrder)" size="small">
          {{ getNarrativeOrderLabel(hoveredEvent.narrativeOrder) }}
        </Tag>
        <span class="tooltip-chapter">Cap. {{ hoveredEvent.chapter }}</span>
      </div>
      <p class="tooltip-description">{{ hoveredEvent.description }}</p>
      <div v-if="hoveredEvent.storyDate && hoveredEvent.storyDate.getFullYear() > 1" class="tooltip-date">
        <i class="pi pi-calendar"></i>
        {{ formatDate(hoveredEvent.storyDate) }}
      </div>
      <div v-else-if="hoveredEvent.dayOffset !== null && hoveredEvent.dayOffset !== undefined" class="tooltip-date">
        <i class="pi pi-calendar"></i>
        {{ formatDayOffset(hoveredEvent.dayOffset) }}
      </div>
      <div v-else-if="hoveredEvent.storyDate" class="tooltip-date">
        <i class="pi pi-calendar"></i>
        {{ formatDate(hoveredEvent.storyDate) }}
      </div>
      <div v-if="getEventEntities(hoveredEvent).length > 0" class="tooltip-entities">
        <i class="pi pi-users"></i>
        {{ getEventEntities(hoveredEvent).join(', ') }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Timeline } from 'vis-timeline/standalone'
import { DataSet } from 'vis-data/standalone'
import type { TimelineOptions, DataItem, DataGroup } from 'vis-timeline'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import type { TimelineEvent as DomainTimelineEvent, NarrativeOrder } from '@/types'

// Re-alias to avoid confusion with vis-timeline Timeline
type TimelineEvent = DomainTimelineEvent

const props = defineProps<{
  events: TimelineEvent[]
  entities?: Array<{ id: number; name: string }>
}>()

const emit = defineEmits<{
  eventSelect: [event: TimelineEvent]
  navigateToText: [position: number]
}>()

// Refs
const timelineContainer = ref<HTMLElement | null>(null)
const timeline = ref<Timeline | null>(null)
const hoveredEvent = ref<TimelineEvent | null>(null)
const tooltipPosition = ref({ x: 0, y: 0 })

// Grouping
const groupBy = ref<'none' | 'chapter' | 'entity'>('chapter')
const groupByOptions = [
  { label: 'Sin agrupar', value: 'none' },
  { label: 'Por capítulo', value: 'chapter' },
  { label: 'Por personaje', value: 'entity' },
]

// Tooltip style
const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`,
}))

// Color mapping for narrative order
const narrativeOrderColors: Record<NarrativeOrder, string> = {
  chronological: '#10b981',
  analepsis: '#3b82f6',
  prolepsis: '#f59e0b',
}

// Get entity name by ID
const getEntityName = (entityId: number): string => {
  if (props.entities) {
    const entity = props.entities.find(e => e.id === entityId)
    if (entity) return entity.name
  }
  return `Entidad ${entityId}`
}

// Get entities for an event
const getEventEntities = (event: TimelineEvent): string[] => {
  return event.entityIds.map(id => getEntityName(id))
}

// Get chapter number (using 'chapter' field from TimelineEvent type)
const getChapterNumber = (event: TimelineEvent): number => {
  return event.chapter
}

// Format date
const formatDate = (date: Date): string => {
  if (date.getFullYear() === 1) {
    // Evitar el quirk de JS para años 0..99 (new Date(1,...) => 1901).
    const baseDate = new Date(0)
    baseDate.setFullYear(1, 0, 1)
    baseDate.setHours(0, 0, 0, 0)
    const diffTime = date.getTime() - baseDate.getTime()
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24))
    return `Día ${diffDays}`
  }
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date)
}

// Formatea offsets relativos sin ambigüedad de signo ("Día +3", "Día -2", "Día 0").
const formatDayOffset = (offset: number): string => {
  if (offset === 0) return 'Día 0'
  return offset > 0 ? `Día +${offset}` : `Día ${offset}`
}

// Narrative order helpers
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
    case 'chronological': return 'Cronológico'
    case 'analepsis': return 'Analepsis'
    case 'prolepsis': return 'Prolepsis'
    default: return order
  }
}

// Resolve an event to a usable Date for the horizontal timeline
const resolveEventDate = (event: TimelineEvent): Date | null => {
  // Real date (year > 1)
  if (event.storyDate && event.storyDate.getFullYear() > 1) {
    return event.storyDate
  }
  // dayOffset -> synthetic date starting at year 1.
  // Usamos setFullYear() porque new Date(1, ...) en JS significa 1901
  // (quirk para años 0..99) y desplaza indebidamente la línea temporal.
  if (event.dayOffset !== null && event.dayOffset !== undefined) {
    const syntheticDate = new Date(0)
    syntheticDate.setFullYear(1, 0, 1 + event.dayOffset)
    syntheticDate.setHours(0, 0, 0, 0)
    return syntheticDate
  }
  // Synthetic storyDate (year === 1) — use as-is
  if (event.storyDate) {
    return event.storyDate
  }
  return null
}

// Build timeline items
const buildItems = computed(() => {
  const items: DataItem[] = []

  for (const event of props.events) {
    const date = resolveEventDate(event)
    if (!date) continue

    const color = narrativeOrderColors[event.narrativeOrder] || '#6b7280'
    const entityNames = getEventEntities(event)

    items.push({
      id: event.id,
      content: `<div class="timeline-item-content">
        <span class="item-text">${truncate(event.description, 40)}</span>
        ${entityNames.length > 0 ? `<span class="item-entities">${entityNames.slice(0, 2).join(', ')}${entityNames.length > 2 ? '...' : ''}</span>` : ''}
      </div>`,
      start: date,
      group: getGroupId(event),
      className: `event-${event.narrativeOrder}`,
      style: `background-color: ${color}; border-color: ${color};`,
    })
  }

  return items
})

// Build groups based on groupBy selection
const buildGroups = computed((): DataGroup[] => {
  if (groupBy.value === 'none') {
    return []
  }

  if (groupBy.value === 'chapter') {
    const chapters = new Set<number>()
    for (const event of props.events) {
      if (getChapterNumber(event)) {
        chapters.add(getChapterNumber(event))
      }
    }
    return Array.from(chapters)
      .sort((a, b) => a - b)
      .map(chapter => ({
        id: `chapter-${chapter}`,
        content: `Capítulo ${chapter}`,
        className: 'chapter-group',
      }))
  }

  if (groupBy.value === 'entity') {
    const entityIds = new Set<number>()
    for (const event of props.events) {
      for (const entityId of event.entityIds) {
        entityIds.add(entityId)
      }
    }
    return Array.from(entityIds).map(entityId => ({
      id: `entity-${entityId}`,
      content: getEntityName(entityId),
      className: 'entity-group',
    }))
  }

  return []
})

// Get group ID for an event
const getGroupId = (event: TimelineEvent): string | undefined => {
  if (groupBy.value === 'none') {
    return undefined
  }
  if (groupBy.value === 'chapter') {
    return getChapterNumber(event) ? `chapter-${getChapterNumber(event)}` : undefined
  }
  if (groupBy.value === 'entity' && event.entityIds.length > 0) {
    // Use first entity for grouping
    return `entity-${event.entityIds[0]}`
  }
  return undefined
}

// Truncate text
const truncate = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Initialize timeline
const initTimeline = () => {
  if (!timelineContainer.value) return

  // Clean up previous instance
  if (timeline.value) {
    timeline.value.destroy()
    timeline.value = null
  }

  const items = new DataSet(buildItems.value)
  const groups = groupBy.value !== 'none' ? new DataSet(buildGroups.value) : undefined

  const options: TimelineOptions = {
    height: '100%',
    min: getMinDate(),
    max: getMaxDate(),
    zoomMin: 1000 * 60 * 60 * 24,  // 1 day
    zoomMax: 1000 * 60 * 60 * 24 * 365 * 10,  // 10 years
    orientation: 'top',
    stack: true,
    showCurrentTime: false,
    tooltip: {
      followMouse: true,
      overflowMethod: 'cap',
    },
    groupOrder: 'content',
    margin: {
      item: {
        horizontal: 5,
        vertical: 5,
      },
    },
  }

  timeline.value = new Timeline(timelineContainer.value, items, options)

  if (groups) {
    timeline.value.setGroups(groups)
  }

  // Event handlers
  timeline.value.on('select', (properties: { items: (string | number)[] }) => {
    if (properties.items.length > 0) {
      const eventId = properties.items[0]
      const event = props.events.find(e => e.id === eventId)
      if (event) {
        emit('eventSelect', event)
      }
    }
  })

  timeline.value.on('itemover', (properties: { item: string | number; event: MouseEvent }) => {
    const event = props.events.find(e => e.id === properties.item)
    if (event) {
      hoveredEvent.value = event
      tooltipPosition.value = {
        x: properties.event.clientX + 10,
        y: properties.event.clientY + 10,
      }
    }
  })

  timeline.value.on('itemout', () => {
    hoveredEvent.value = null
  })

  // Fit all items
  nextTick(() => {
    fitAll()
  })
}

// Get min date from events (considers resolved dates including synthetic)
const getMinDate = (): Date => {
  let min = new Date()
  for (const event of props.events) {
    const date = resolveEventDate(event)
    if (date && date < min) {
      min = date
    }
  }
  // Add some padding
  return new Date(min.getTime() - 1000 * 60 * 60 * 24 * 30)  // 30 days before
}

// Get max date from events (considers resolved dates including synthetic)
const getMaxDate = (): Date => {
  let max = new Date(0)
  for (const event of props.events) {
    const date = resolveEventDate(event)
    if (date && date > max) {
      max = date
    }
  }
  // Add some padding
  return new Date(max.getTime() + 1000 * 60 * 60 * 24 * 30)  // 30 days after
}

// Zoom controls
const zoomIn = () => {
  timeline.value?.zoomIn(0.5)
}

const zoomOut = () => {
  timeline.value?.zoomOut(0.5)
}

const fitAll = () => {
  timeline.value?.fit()
}

// Lifecycle
onMounted(() => {
  initTimeline()
})

onUnmounted(() => {
  if (timeline.value) {
    timeline.value.destroy()
    timeline.value = null
  }
})

// Watch for changes
watch(() => props.events, () => {
  initTimeline()
}, { deep: true })

watch(groupBy, () => {
  initTimeline()
})
</script>

<style scoped>
.vis-timeline-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-ground);
}

.vis-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-200);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.group-dropdown {
  width: 150px;
}

.legend {
  display: flex;
  gap: 1rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.legend .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend .dot.chronological {
  background: #10b981;
}

.legend .dot.analepsis {
  background: #3b82f6;
}

.legend .dot.prolepsis {
  background: #f59e0b;
}

.timeline-element {
  flex: 1;
  overflow: hidden;
}

/* Event tooltip */
.event-tooltip {
  position: fixed;
  z-index: var(--ds-z-dropdown);
  max-width: 300px;
  padding: 0.75rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-200);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: none;
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.tooltip-chapter {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.tooltip-description {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: var(--text-color);
  line-height: 1.4;
}

.tooltip-date,
.tooltip-entities {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.tooltip-date i,
.tooltip-entities i {
  font-size: 0.75rem;
}
</style>

<style>
/* vis-timeline global styles */
.vis-timeline {
  border: none !important;
  font-family: inherit !important;
}

.vis-panel.vis-center,
.vis-panel.vis-left,
.vis-panel.vis-right,
.vis-panel.vis-top,
.vis-panel.vis-bottom {
  border: none !important;
}

.vis-time-axis .vis-text {
  color: var(--text-color-secondary) !important;
  font-size: 0.75rem !important;
}

.vis-time-axis .vis-grid.vis-minor {
  border-color: var(--surface-200) !important;
}

.vis-time-axis .vis-grid.vis-major {
  border-color: var(--surface-300) !important;
}

.vis-item {
  border-radius: 4px !important;
  font-size: 0.8125rem !important;
  color: white !important;
  border-width: 0 !important;
}

.vis-item.vis-selected {
  box-shadow: 0 0 0 2px var(--primary-color) !important;
}

.vis-item .vis-item-content {
  padding: 4px 8px !important;
}

.timeline-item-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.timeline-item-content .item-text {
  font-weight: 500;
}

.timeline-item-content .item-entities {
  font-size: 0.6875rem;
  opacity: 0.85;
}

/* Groups */
.vis-labelset .vis-label {
  background: var(--surface-50) !important;
  border-bottom: 1px solid var(--surface-200) !important;
  color: var(--text-color) !important;
  font-weight: 600 !important;
  font-size: 0.8125rem !important;
}

.vis-foreground .vis-group {
  border-bottom: 1px solid var(--surface-200) !important;
}

/* Event type specific styling */
.vis-item.event-chronological {
  background-color: #10b981 !important;
}

.vis-item.event-analepsis {
  background-color: #3b82f6 !important;
}

.vis-item.event-prolepsis {
  background-color: #f59e0b !important;
}
</style>
