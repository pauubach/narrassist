<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useGlobalHighlight, type HighlightSpan } from '@/composables/useHighlight'
import { useSelectionStore } from '@/stores/selection'
import { useEntityUtils } from '@/composables/useEntityUtils'
import type { Entity, EntityMention, Alert } from '@/types'

/**
 * TextHighlighter - Componente para renderizar texto con resaltados interactivos.
 *
 * Soporta:
 * - Resaltado de menciones de entidades
 * - Resaltado de alertas (incluye gramática y ortografía)
 * - Errores de gramática (wavy underline azul)
 * - Errores de ortografía (wavy underline rojo)
 * - Click para seleccionar y ver sugerencias
 * - Hover para preview con tooltip
 * - Múltiples capas de resaltado
 */

/** Tipo extendido de span para soportar errores de gramática/ortografía */
export type ErrorSpan = HighlightSpan & {
  errorType?: 'grammar' | 'spelling' | 'orthography'
  suggestion?: string
  description?: string
}

const props = defineProps<{
  /** Texto a renderizar */
  text: string
  /** Menciones de entidades a resaltar */
  mentions?: EntityMention[]
  /** Entidades (para obtener colores/tipos) */
  entities?: Entity[]
  /** Alertas a resaltar (incluye gramática y ortografía) */
  alerts?: Alert[]
  /** Si está en modo solo lectura */
  readonly?: boolean
  /** Offset base para posiciones (si es parte de un texto mayor) */
  offsetBase?: number
  /** Mostrar errores de ortografía */
  showSpellingErrors?: boolean
  /** Mostrar errores de gramática */
  showGrammarErrors?: boolean
}>()

const emit = defineEmits<{
  'entity-click': [entityId: number, mention: EntityMention]
  'alert-click': [alert: Alert]
  'error-click': [alert: Alert, event: MouseEvent]
  'text-select': [start: number, end: number, text: string]
  'add-to-dictionary': [word: string]
  'ignore-error': [alertId: number]
}>()

const highlight = useGlobalHighlight()
const selectionStore = useSelectionStore()
const { getEntityColor } = useEntityUtils()

const containerRef = ref<HTMLElement | null>(null)

// Estado para el popup de sugerencias
const activeErrorPopup = ref<{
  alert: Alert
  x: number
  y: number
} | null>(null)

// Cerrar popup al hacer click fuera
function handleClickOutside(event: MouseEvent) {
  if (activeErrorPopup.value) {
    const popup = document.querySelector('.error-suggestion-popup')
    if (popup && !popup.contains(event.target as Node)) {
      activeErrorPopup.value = null
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// Mapa de entidades por ID para lookup rápido
const entityMap = computed(() => {
  const map = new Map<number, Entity>()
  if (props.entities) {
    for (const entity of props.entities) {
      map.set(entity.id, entity)
    }
  }
  return map
})

// Convertir menciones a spans de resaltado
const mentionSpans = computed<HighlightSpan[]>(() => {
  if (!props.mentions) return []

  return props.mentions.map(mention => {
    const entity = entityMap.value.get(mention.entityId)
    const color = entity ? getEntityColor(entity.type) : 'var(--ds-color-primary)'

    return {
      id: `mention-${mention.id}`,
      type: 'mention' as const,
      elementId: mention.entityId,
      start: mention.spanStart + (props.offsetBase || 0),
      end: mention.spanEnd + (props.offsetBase || 0),
      text: mention.text,
      color,
      opacity: 0.2,
      active: selectionStore.isSelected('entity', mention.entityId),
    }
  })
})

// Determinar el tipo de error basado en la categoría de la alerta
function getErrorType(category: string): 'grammar' | 'spelling' | 'orthography' | undefined {
  if (category === 'grammar') return 'grammar'
  if (category === 'spelling' || category === 'orthography') return 'spelling'
  return undefined
}

// Verificar si una alerta debe mostrarse basado en los filtros
function shouldShowAlert(alert: Alert): boolean {
  const errorType = getErrorType(alert.category)

  // Si no es error de gramática/ortografía, siempre mostrar
  if (!errorType) return true

  // Aplicar filtros
  if (errorType === 'grammar' && props.showGrammarErrors === false) return false
  if ((errorType === 'spelling' || errorType === 'orthography') && props.showSpellingErrors === false) return false

  return true
}

// Convertir alertas a spans de resaltado
const alertSpans = computed<ErrorSpan[]>(() => {
  if (!props.alerts) return []

  return props.alerts
    .filter(alert => alert.spanStart !== undefined && alert.spanEnd !== undefined)
    .filter(shouldShowAlert)
    .map(alert => {
      const errorType = getErrorType(alert.category)

      // Color según tipo de error
      let color = `var(--ds-alert-${alert.severity})`
      if (errorType === 'spelling') {
        color = 'var(--error-spelling-color, #ef4444)'  // Rojo
      } else if (errorType === 'grammar') {
        color = 'var(--error-grammar-color, #3b82f6)'   // Azul
      }

      return {
        id: `alert-${alert.id}`,
        type: 'alert' as const,
        elementId: alert.id,
        start: alert.spanStart! + (props.offsetBase || 0),
        end: alert.spanEnd! + (props.offsetBase || 0),
        text: props.text.slice(alert.spanStart!, alert.spanEnd!),
        color,
        opacity: 0.25,
        active: selectionStore.isSelected('alert', alert.id),
        errorType,
        suggestion: alert.suggestion,
        description: alert.description,
      }
    })
})

// Tipo unión para todos los spans (incluyendo errores)
type AnySpan = HighlightSpan | ErrorSpan

// Segmentos de texto con y sin resaltado
interface TextSegment {
  text: string
  start: number
  end: number
  spans: AnySpan[]
}

// Todos los spans ordenados
const allSpans = computed<AnySpan[]>(() => {
  return [...mentionSpans.value, ...alertSpans.value].sort((a, b) => a.start - b.start)
})

const segments = computed<TextSegment[]>(() => {
  if (!props.text) return []

  const spans = allSpans.value
  if (spans.length === 0) {
    return [{ text: props.text, start: props.offsetBase || 0, end: props.text.length + (props.offsetBase || 0), spans: [] }]
  }

  const result: TextSegment[] = []
  const baseOffset = props.offsetBase || 0

  // Crear puntos de corte únicos
  const breakpoints = new Set<number>()
  breakpoints.add(0)
  breakpoints.add(props.text.length)

  for (const span of spans) {
    const relStart = span.start - baseOffset
    const relEnd = span.end - baseOffset
    if (relStart >= 0 && relStart <= props.text.length) breakpoints.add(relStart)
    if (relEnd >= 0 && relEnd <= props.text.length) breakpoints.add(relEnd)
  }

  const sortedBreakpoints = Array.from(breakpoints).sort((a, b) => a - b)

  // Build event list for sweep-line: +1 at span start, -1 at span end
  type SweepEvent = { pos: number; type: 'start' | 'end'; span: AnySpan }
  const events: SweepEvent[] = []
  for (const span of spans) {
    events.push({ pos: span.start, type: 'start', span })
    events.push({ pos: span.end, type: 'end', span })
  }
  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? -1 : 1))

  // Sweep: maintain active spans set as we walk through breakpoints
  const active = new Set<AnySpan>()
  let eventIdx = 0

  for (let i = 0; i < sortedBreakpoints.length - 1; i++) {
    const start = sortedBreakpoints[i]
    const end = sortedBreakpoints[i + 1]
    if (start >= end) continue

    const absoluteStart = start + baseOffset

    // Process events up to this segment's absolute start
    while (eventIdx < events.length && events[eventIdx].pos <= absoluteStart) {
      const ev = events[eventIdx]
      if (ev.type === 'start') active.add(ev.span)
      else active.delete(ev.span)
      eventIdx++
    }

    result.push({
      text: props.text.slice(start, end),
      start: absoluteStart,
      end: end + baseOffset,
      spans: active.size > 0 ? Array.from(active) : [],
    })
  }

  return result
})

function handleSpanClick(segment: TextSegment, event: MouseEvent) {
  if (props.readonly) return

  // Priorizar alertas sobre menciones
  const alertSpan = segment.spans.find(s => s.type === 'alert') as ErrorSpan | undefined
  if (alertSpan) {
    const alert = props.alerts?.find(a => a.id === alertSpan.elementId)
    if (alert) {
      // Si es error de gramática/ortografía, mostrar popup de sugerencias
      if (alertSpan.errorType) {
        event.stopPropagation()
        activeErrorPopup.value = {
          alert,
          x: event.clientX,
          y: event.clientY
        }
        emit('error-click', alert, event)
      } else {
        emit('alert-click', alert)
      }
      return
    }
  }

  const mentionSpan = segment.spans.find(s => s.type === 'mention')
  if (mentionSpan) {
    const mention = props.mentions?.find(m => m.entityId === mentionSpan.elementId)
    if (mention) {
      emit('entity-click', mentionSpan.elementId, mention)
    }
  }
}

// Cerrar el popup de sugerencias
function closeErrorPopup() {
  activeErrorPopup.value = null
}

// Ignorar el error
function handleIgnoreError() {
  if (activeErrorPopup.value) {
    emit('ignore-error', activeErrorPopup.value.alert.id)
    closeErrorPopup()
  }
}

// Añadir palabra al diccionario
function handleAddToDictionary() {
  if (activeErrorPopup.value) {
    const alert = activeErrorPopup.value.alert
    // El texto del error está entre spanStart y spanEnd
    if (alert.spanStart !== undefined && alert.spanEnd !== undefined) {
      const word = props.text.slice(alert.spanStart, alert.spanEnd)
      emit('add-to-dictionary', word)
    }
    closeErrorPopup()
  }
}

function handleSpanHover(segment: TextSegment, isEnter: boolean) {
  if (segment.spans.length === 0) {
    if (!isEnter) highlight.setHover(null)
    return
  }

  if (isEnter) {
    const topSpan = segment.spans[segment.spans.length - 1]
    highlight.setHover(topSpan.id)
  } else {
    highlight.setHover(null)
  }
}

function getSegmentStyle(segment: TextSegment): Record<string, string> {
  if (segment.spans.length === 0) return {}

  // Usar el span más "superior" (última en la lista = más específico)
  const topSpan = segment.spans[segment.spans.length - 1] as ErrorSpan
  const isActive = topSpan.active || highlight.hoveredSpan.value?.id === topSpan.id

  // Para errores de gramática/ortografía, no aplicar background, solo underline via CSS
  if (topSpan.errorType) {
    return {
      cursor: 'pointer',
      transition: 'opacity 0.15s',
    }
  }

  return {
    backgroundColor: topSpan.color,
    opacity: isActive ? '0.5' : String(topSpan.opacity),
    borderBottom: isActive ? `2px solid ${topSpan.color}` : 'none',
    cursor: 'pointer',
    borderRadius: '2px',
    transition: 'opacity 0.15s, background-color 0.15s',
  }
}

function getSegmentClasses(segment: TextSegment): string[] {
  const classes = ['text-segment']
  if (segment.spans.length > 0) {
    classes.push('text-segment--highlighted')
    for (const span of segment.spans) {
      const errorSpan = span as ErrorSpan
      classes.push(`text-segment--${span.type}`)
      if (span.active) classes.push('text-segment--active')

      // Añadir clases específicas para errores de gramática/ortografía
      if (errorSpan.errorType === 'spelling' || errorSpan.errorType === 'orthography') {
        classes.push('text-segment--spelling-error')
      } else if (errorSpan.errorType === 'grammar') {
        classes.push('text-segment--grammar-error')
      }
    }
  }
  return classes
}

// Obtener tooltip para un segmento
function getSegmentTooltip(segment: TextSegment): string {
  if (segment.spans.length === 0) return ''

  const errorSpan = segment.spans.find(s => (s as ErrorSpan).errorType) as ErrorSpan | undefined
  if (errorSpan) {
    let tooltip = errorSpan.description || ''
    if (errorSpan.suggestion) {
      tooltip += tooltip ? ` - Sugerencia: ${errorSpan.suggestion}` : `Sugerencia: ${errorSpan.suggestion}`
    }
    return tooltip
  }

  return ''
}

// Manejar selección de texto nativa
function handleMouseUp() {
  if (props.readonly) return

  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return

  const selectedText = selection.toString()
  if (!selectedText.trim()) return

  // Calcular posiciones en el texto original
  // Esto es una simplificación; en producción necesitaría más lógica
  const _range = selection.getRangeAt(0)
  const container = containerRef.value

  if (!container) return

  // Emitir evento de selección
  emit('text-select', 0, selectedText.length, selectedText)
}
</script>

<template>
  <div
    ref="containerRef"
    class="text-highlighter"
    @mouseup="handleMouseUp"
  >
    <template v-for="(segment, index) in segments" :key="index">
      <span
        v-if="segment.spans.length > 0"
        :class="getSegmentClasses(segment)"
        :style="getSegmentStyle(segment)"
        :title="getSegmentTooltip(segment)"
        @click="handleSpanClick(segment, $event)"
        @mouseenter="handleSpanHover(segment, true)"
        @mouseleave="handleSpanHover(segment, false)"
      >{{ segment.text }}</span>
      <span v-else>{{ segment.text }}</span>
    </template>

    <!-- Popup de sugerencias para errores -->
    <Teleport to="body">
      <div
        v-if="activeErrorPopup"
        class="error-suggestion-popup"
        :style="{
          left: activeErrorPopup.x + 'px',
          top: activeErrorPopup.y + 'px'
        }"
        @click.stop
      >
        <div class="popup-header">
          <span class="popup-type" :class="activeErrorPopup.alert.category">
            {{ activeErrorPopup.alert.category === 'grammar' ? 'Error de gramatica' : 'Error de ortografia' }}
          </span>
          <button class="popup-close" aria-label="Cerrar" @click="closeErrorPopup">
            <i class="pi pi-times"></i>
          </button>
        </div>
        <div class="popup-content">
          <p class="popup-description">{{ activeErrorPopup.alert.description }}</p>
          <div v-if="activeErrorPopup.alert.suggestion" class="popup-suggestion">
            <span class="suggestion-label">Sugerencia:</span>
            <span class="suggestion-text">{{ activeErrorPopup.alert.suggestion }}</span>
          </div>
        </div>
        <div class="popup-actions">
          <button class="popup-btn popup-btn--secondary" @click="handleIgnoreError">
            <i class="pi pi-ban"></i>
            Ignorar
          </button>
          <button
            v-if="activeErrorPopup.alert.category !== 'grammar'"
            class="popup-btn popup-btn--secondary"
            @click="handleAddToDictionary"
          >
            <i class="pi pi-plus"></i>
            Añadir al diccionario
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.text-highlighter {
  font-family: var(--ds-font-family-reading);
  font-size: var(--ds-font-size-reading);
  line-height: var(--ds-line-height-reading);
  color: var(--ds-color-text);
  white-space: pre-wrap;
  word-wrap: break-word;
  position: relative;
}

.text-segment--highlighted {
  position: relative;
}

.text-segment--active {
  font-weight: var(--ds-font-weight-medium);
}

/* Indicador visual para menciones */
.text-segment--mention::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: currentColor;
  opacity: 0;
  transition: opacity 0.15s;
}

.text-segment--mention:hover::after {
  opacity: 0.5;
}

/* Indicador visual para alertas generales */
.text-segment--alert {
  text-decoration: wavy underline;
  text-decoration-color: var(--ds-color-danger);
  text-underline-offset: 3px;
}

/* ==================== */
/* Error de ortografia  */
/* ==================== */
.text-segment--spelling-error {
  text-decoration: underline wavy;
  text-decoration-color: var(--error-spelling-color, #ef4444);
  text-underline-offset: 3px;
  text-decoration-thickness: 2px;
  background-color: transparent !important;
}

.text-segment--spelling-error:hover {
  background-color: rgba(239, 68, 68, 0.1) !important;
}

/* ==================== */
/* Error de gramatica   */
/* ==================== */
.text-segment--grammar-error {
  text-decoration: underline wavy;
  text-decoration-color: var(--error-grammar-color, #3b82f6);
  text-underline-offset: 3px;
  text-decoration-thickness: 2px;
  background-color: transparent !important;
}

.text-segment--grammar-error:hover {
  background-color: rgba(59, 130, 246, 0.1) !important;
}

/* ==================== */
/* Popup de sugerencias */
/* ==================== */
.error-suggestion-popup {
  position: fixed;
  z-index: 9999;
  background: var(--surface-0, white);
  border: 1px solid var(--surface-border, #e5e7eb);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  min-width: 280px;
  max-width: 400px;
  transform: translateX(-50%) translateY(8px);
  animation: popup-enter 0.15s ease-out;
}

@keyframes popup-enter {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(0);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(8px);
  }
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border, #e5e7eb);
}

.popup-type {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.popup-type.grammar {
  background: rgba(59, 130, 246, 0.1);
  color: var(--error-grammar-color, #3b82f6);
}

.popup-type.spelling,
.popup-type.orthography {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error-spelling-color, #ef4444);
}

.popup-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--text-color-secondary, #6b7280);
  border-radius: 4px;
  transition: background-color 0.15s;
}

.popup-close:hover {
  background-color: var(--surface-100, #f3f4f6);
}

.popup-content {
  padding: 1rem;
}

.popup-description {
  margin: 0 0 0.75rem 0;
  font-size: 0.875rem;
  color: var(--text-color, #374151);
  line-height: 1.5;
}

.popup-suggestion {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
  padding: 0.75rem;
  background: var(--surface-50, #f9fafb);
  border-radius: 6px;
}

.suggestion-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary, #6b7280);
}

.suggestion-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--primary-color, #3b82f6);
}

.popup-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--surface-border, #e5e7eb);
  background: var(--surface-50, #f9fafb);
  border-radius: 0 0 8px 8px;
}

.popup-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}

.popup-btn--secondary {
  background: var(--surface-100, #f3f4f6);
  color: var(--text-color, #374151);
}

.popup-btn--secondary:hover {
  background: var(--surface-200, #e5e7eb);
}

.popup-btn i {
  font-size: 0.75rem;
}

/* Dark mode support */
:global(.dark) .error-suggestion-popup {
  background: var(--surface-800, #1f2937);
  border-color: var(--surface-700, #374151);
}

:global(.dark) .popup-header {
  border-color: var(--surface-700, #374151);
}

:global(.dark) .popup-close:hover {
  background-color: var(--surface-700, #374151);
}

:global(.dark) .popup-description {
  color: var(--text-color, #e5e7eb);
}

:global(.dark) .popup-suggestion {
  background: var(--surface-700, #374151);
}

:global(.dark) .popup-actions {
  background: var(--surface-700, #374151);
  border-color: var(--surface-600, #4b5563);
}

:global(.dark) .popup-btn--secondary {
  background: var(--surface-600, #4b5563);
  color: var(--text-color, #e5e7eb);
}

:global(.dark) .popup-btn--secondary:hover {
  background: var(--surface-500, #6b7280);
}
</style>
