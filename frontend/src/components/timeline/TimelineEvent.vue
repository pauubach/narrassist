<template>
  <div
    class="timeline-event"
    :class="[
      `event-${event.narrativeOrder}`,
      { 'event-selected': isSelected, 'event-hovered': isHovered }
    ]"
    @click="handleClick"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <!-- Indicador de orden narrativo -->
    <div class="event-indicator" :class="`indicator-${event.narrativeOrder}`">
      <i :class="getIndicatorIcon(event.narrativeOrder)"></i>
    </div>

    <!-- Contenido del evento -->
    <div class="event-content">
      <!-- Header: Fecha y capitulo -->
      <div class="event-header">
        <div class="event-date">
          <i class="pi pi-calendar"></i>
          <span v-if="event.storyDate">{{ formatDate(event.storyDate, event.storyDateResolution) }}</span>
          <span v-else class="date-unknown">Fecha desconocida</span>
        </div>
        <Tag
          :severity="getNarrativeOrderSeverity(event.narrativeOrder)"
          :value="getNarrativeOrderLabel(event.narrativeOrder)"
          class="event-type-tag"
        />
      </div>

      <!-- Descripcion del evento -->
      <div class="event-description">
        <h4>{{ event.description }}</h4>
      </div>

      <!-- Metadata -->
      <div class="event-meta">
        <div class="meta-item">
          <i class="pi pi-book"></i>
          <span>Capitulo {{ event.chapter }}</span>
        </div>
        <div v-if="event.entityIds.length > 0" class="meta-item">
          <i class="pi pi-users"></i>
          <span>{{ event.entityIds.length }} personaje{{ event.entityIds.length > 1 ? 's' : '' }}</span>
        </div>
        <div class="meta-item confidence" :class="getConfidenceClass(event.confidence)">
          <i class="pi pi-check-circle"></i>
          <span>{{ Math.round(event.confidence * 100) }}%</span>
        </div>
      </div>

      <!-- Personajes involucrados (si se proporcionan nombres) -->
      <div v-if="entityNames.length > 0" class="event-entities">
        <Chip
          v-for="name in entityNames.slice(0, 3)"
          :key="name"
          :label="name"
          class="entity-chip"
        />
        <span v-if="entityNames.length > 3" class="more-entities">
          +{{ entityNames.length - 3 }} mas
        </span>
      </div>
    </div>

    <!-- Linea conectora -->
    <div v-if="showConnector" class="event-connector">
      <div class="connector-line"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import type { TimelineEvent, NarrativeOrder, TimelineResolution } from '@/types'

const props = withDefaults(defineProps<{
  event: TimelineEvent
  entityNames?: string[]
  isSelected?: boolean
  isHovered?: boolean
  showConnector?: boolean
}>(), {
  entityNames: () => [],
  isSelected: false,
  isHovered: false,
  showConnector: true
})

const emit = defineEmits<{
  click: [event: TimelineEvent]
  hover: [event: TimelineEvent | null]
}>()

// Formateador de fechas
const formatDate = (date: Date, resolution: TimelineResolution): string => {
  // Para fechas sintéticas (año < 100), mostrar como "Día X" relativo
  // Esto ocurre cuando no hay fechas absolutas en el texto y se usa
  // una fecha de referencia sintética (año 1) para calcular offsets relativos
  if (date.getFullYear() < 100) {
    // Calcular día relativo desde el 1 de enero del año 1
    const baseDate = new Date(1, 0, 1) // 1 de enero del año 1
    const diffTime = date.getTime() - baseDate.getTime()
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24))

    // Siempre mostrar días positivos (Día 0, Día 1, etc.)
    if (diffDays < 0) {
      return 'Inicio'
    }
    return `Día ${diffDays}`
  }

  const options: Intl.DateTimeFormatOptions = {}

  switch (resolution) {
    case 'exact_date':
      options.day = 'numeric'
      options.month = 'long'
      options.year = 'numeric'
      break
    case 'month':
      options.month = 'long'
      options.year = 'numeric'
      break
    case 'year':
      options.year = 'numeric'
      break
    case 'season':
      // Para estaciones, mostramos el mes y año
      options.month = 'long'
      options.year = 'numeric'
      break
    case 'relative':
      options.month = 'short'
      options.year = 'numeric'
      break
    default:
      options.year = 'numeric'
  }

  return new Intl.DateTimeFormat('es-ES', options).format(date)
}

// Obtener icono del indicador segun orden narrativo
const getIndicatorIcon = (order: NarrativeOrder): string => {
  switch (order) {
    case 'chronological':
      return 'pi pi-arrow-right'
    case 'analepsis':
      return 'pi pi-arrow-left'
    case 'prolepsis':
      return 'pi pi-arrow-up-right'
    default:
      return 'pi pi-circle'
  }
}

// Obtener severidad del tag segun orden narrativo
const getNarrativeOrderSeverity = (order: NarrativeOrder): string => {
  switch (order) {
    case 'chronological':
      return 'success'
    case 'analepsis':
      return 'info'
    case 'prolepsis':
      return 'warn'
    default:
      return 'secondary'
  }
}

// Obtener etiqueta del orden narrativo
const getNarrativeOrderLabel = (order: NarrativeOrder): string => {
  switch (order) {
    case 'chronological':
      return 'Cronologico'
    case 'analepsis':
      return 'Analepsis'
    case 'prolepsis':
      return 'Prolepsis'
    default:
      return order
  }
}

// Obtener clase de confianza
const getConfidenceClass = (confidence: number): string => {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.5) return 'confidence-medium'
  return 'confidence-low'
}

// Handlers de eventos
const handleClick = () => {
  emit('click', props.event)
}

const handleMouseEnter = () => {
  emit('hover', props.event)
}

const handleMouseLeave = () => {
  emit('hover', null)
}
</script>

<style scoped>
.timeline-event {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-card);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.timeline-event:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.timeline-event.event-selected {
  border-color: var(--primary-color);
  background: var(--primary-50);
}

.timeline-event.event-hovered {
  border-color: var(--primary-300);
}

/* Indicador por orden narrativo */
.event-indicator {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.event-indicator i {
  font-size: 1.125rem;
  color: white;
}

.indicator-chronological {
  background: linear-gradient(135deg, #10b981, #059669);
}

.indicator-analepsis {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.indicator-prolepsis {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

/* Contenido del evento */
.event-content {
  flex: 1;
  min-width: 0;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.event-date {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.event-date i {
  color: var(--primary-color);
}

.date-unknown {
  font-style: italic;
  color: var(--text-color-secondary);
}

.event-type-tag {
  font-size: 0.75rem;
}

.event-description h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
  line-height: 1.4;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.75rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.meta-item i {
  font-size: 0.875rem;
}

.confidence.confidence-high {
  color: #10b981;
}

.confidence.confidence-medium {
  color: #f59e0b;
}

.confidence.confidence-low {
  color: #ef4444;
}

.event-entities {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-200);
}

.entity-chip {
  font-size: 0.75rem;
}

.more-entities {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
}

/* Conector de linea (para visualizacion vertical) */
.event-connector {
  position: absolute;
  left: 28px;
  bottom: -1rem;
  width: 2px;
  height: 1rem;
  display: flex;
  justify-content: center;
}

.connector-line {
  width: 2px;
  height: 100%;
  background: var(--surface-300);
}

/* Variantes por orden narrativo */
.event-chronological {
  border-left: 4px solid #10b981;
}

.event-analepsis {
  border-left: 4px solid #3b82f6;
}

.event-prolepsis {
  border-left: 4px solid #f59e0b;
}

/* Responsive */
@media (max-width: 600px) {
  .timeline-event {
    flex-direction: column;
    gap: 0.75rem;
  }

  .event-indicator {
    width: 32px;
    height: 32px;
  }

  .event-indicator i {
    font-size: 0.875rem;
  }

  .event-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .event-meta {
    gap: 0.75rem;
  }
}
</style>
