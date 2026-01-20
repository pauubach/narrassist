/**
 * useHighlight - Sistema de resaltado bidireccional texto ↔ paneles.
 *
 * Gestiona el resaltado de entidades, alertas y menciones en el texto
 * y su conexión con los paneles laterales.
 *
 * Incluye soporte para:
 * - Resaltado persistente (selección)
 * - Resaltado temporal con animación (flash)
 * - Scroll suave hacia elementos
 */

import { ref, computed, nextTick } from 'vue'

/** Duración por defecto del flash en ms */
const DEFAULT_FLASH_DURATION = 2000

/** Clase CSS para el efecto de flash */
export const HIGHLIGHT_FLASH_CLASS = 'highlight-flash'

export interface HighlightSpan {
  /** ID único del span */
  id: string
  /** Tipo de elemento resaltado */
  type: 'entity' | 'alert' | 'mention'
  /** ID del elemento (entity_id o alert_id) */
  elementId: number
  /** Posición inicial en el texto (caracteres) */
  start: number
  /** Posición final en el texto (caracteres) */
  end: number
  /** Texto resaltado */
  text: string
  /** Color del resaltado (CSS variable o hex) */
  color: string
  /** Nivel de opacidad (0-1) */
  opacity?: number
  /** Si está activo (hover/selección) */
  active?: boolean
}

export interface HighlightOptions {
  /** Color por defecto para entidades */
  defaultEntityColor?: string
  /** Color por defecto para alertas */
  defaultAlertColor?: string
  /** Opacidad base del resaltado */
  baseOpacity?: number
  /** Opacidad cuando está activo */
  activeOpacity?: number
  /** Si permite múltiples selecciones */
  multiSelect?: boolean
  /** Duración del flash en ms */
  flashDuration?: number
  /** Contenedor para scroll (por defecto busca .document-viewer) */
  scrollContainer?: string
}

/** Estado de un flash temporal activo */
export interface FlashState {
  spanId: string
  timeout: ReturnType<typeof setTimeout>
}

const defaultOptions: HighlightOptions = {
  defaultEntityColor: 'var(--ds-color-primary)',
  defaultAlertColor: 'var(--ds-alert-medium)',
  baseOpacity: 0.2,
  activeOpacity: 0.5,
  multiSelect: false,
  flashDuration: DEFAULT_FLASH_DURATION,
  scrollContainer: '.document-viewer'
}

export function useHighlight(options: HighlightOptions = {}) {
  const config = { ...defaultOptions, ...options }

  // Estado
  const spans = ref<HighlightSpan[]>([])
  const activeSpanIds = ref<Set<string>>(new Set())
  const hoveredSpanId = ref<string | null>(null)
  const flashingSpans = ref<Map<string, FlashState>>(new Map())

  /**
   * Spans ordenados por posición
   */
  const sortedSpans = computed(() => {
    return [...spans.value].sort((a, b) => a.start - b.start)
  })

  /**
   * Spans activos actualmente
   */
  const activeSpans = computed(() => {
    return spans.value.filter(span => activeSpanIds.value.has(span.id))
  })

  /**
   * Span bajo el cursor
   */
  const hoveredSpan = computed(() => {
    return spans.value.find(span => span.id === hoveredSpanId.value) || null
  })

  /**
   * Registra un nuevo span de resaltado
   */
  function registerSpan(span: Omit<HighlightSpan, 'id' | 'opacity' | 'active'>): string {
    const id = `${span.type}-${span.elementId}-${span.start}-${span.end}`

    // Evitar duplicados
    if (spans.value.some(s => s.id === id)) {
      return id
    }

    spans.value.push({
      ...span,
      id,
      opacity: config.baseOpacity,
      active: false
    })

    return id
  }

  /**
   * Elimina un span de resaltado
   */
  function unregisterSpan(spanId: string): void {
    const index = spans.value.findIndex(s => s.id === spanId)
    if (index !== -1) {
      spans.value.splice(index, 1)
      activeSpanIds.value.delete(spanId)
    }
  }

  /**
   * Elimina todos los spans de un elemento
   */
  function unregisterElement(type: HighlightSpan['type'], elementId: number): void {
    spans.value = spans.value.filter(span => !(span.type === type && span.elementId === elementId))

    // Limpiar IDs activos
    for (const spanId of activeSpanIds.value) {
      const span = spans.value.find(s => s.id === spanId)
      if (!span) {
        activeSpanIds.value.delete(spanId)
      }
    }
  }

  /**
   * Limpia todos los spans
   */
  function clearSpans(): void {
    spans.value = []
    activeSpanIds.value.clear()
    hoveredSpanId.value = null
  }

  /**
   * Activa un span (selección)
   */
  function activateSpan(spanId: string): void {
    if (!config.multiSelect) {
      activeSpanIds.value.clear()
    }
    activeSpanIds.value.add(spanId)

    // Actualizar estado del span
    const span = spans.value.find(s => s.id === spanId)
    if (span) {
      span.active = true
      span.opacity = config.activeOpacity
    }
  }

  /**
   * Desactiva un span
   */
  function deactivateSpan(spanId: string): void {
    activeSpanIds.value.delete(spanId)

    const span = spans.value.find(s => s.id === spanId)
    if (span) {
      span.active = false
      span.opacity = config.baseOpacity
    }
  }

  /**
   * Alterna la activación de un span
   */
  function toggleSpan(spanId: string): void {
    if (activeSpanIds.value.has(spanId)) {
      deactivateSpan(spanId)
    } else {
      activateSpan(spanId)
    }
  }

  /**
   * Desactiva todos los spans
   */
  function deactivateAll(): void {
    for (const spanId of activeSpanIds.value) {
      deactivateSpan(spanId)
    }
  }

  /**
   * Activa todos los spans de un elemento
   */
  function activateElement(type: HighlightSpan['type'], elementId: number): void {
    const elementSpans = spans.value.filter(
      span => span.type === type && span.elementId === elementId
    )

    if (!config.multiSelect) {
      deactivateAll()
    }

    for (const span of elementSpans) {
      activateSpan(span.id)
    }
  }

  /**
   * Desactiva todos los spans de un elemento
   */
  function deactivateElement(type: HighlightSpan['type'], elementId: number): void {
    const elementSpans = spans.value.filter(
      span => span.type === type && span.elementId === elementId
    )

    for (const span of elementSpans) {
      deactivateSpan(span.id)
    }
  }

  /**
   * Establece hover sobre un span
   */
  function setHover(spanId: string | null): void {
    // Restaurar opacidad del span anterior
    if (hoveredSpanId.value && hoveredSpanId.value !== spanId) {
      const prevSpan = spans.value.find(s => s.id === hoveredSpanId.value)
      if (prevSpan && !prevSpan.active) {
        prevSpan.opacity = config.baseOpacity
      }
    }

    hoveredSpanId.value = spanId

    // Aumentar opacidad del nuevo span
    if (spanId) {
      const span = spans.value.find(s => s.id === spanId)
      if (span && !span.active) {
        span.opacity = (config.baseOpacity! + config.activeOpacity!) / 2
      }
    }
  }

  /**
   * Encuentra spans en una posición del texto
   */
  function getSpansAtPosition(position: number): HighlightSpan[] {
    return spans.value.filter(span => position >= span.start && position <= span.end)
  }

  /**
   * Encuentra spans que se solapan con un rango
   */
  function getSpansInRange(start: number, end: number): HighlightSpan[] {
    return spans.value.filter(
      span => (span.start >= start && span.start <= end) || (span.end >= start && span.end <= end)
    )
  }

  /**
   * Obtiene el primer span de un elemento
   */
  function getFirstSpan(type: HighlightSpan['type'], elementId: number): HighlightSpan | null {
    return (
      sortedSpans.value.find(span => span.type === type && span.elementId === elementId) || null
    )
  }

  /**
   * Genera el CSS inline para un span
   */
  function getSpanStyle(span: HighlightSpan): Record<string, string> {
    return {
      backgroundColor: span.color,
      opacity: String(span.opacity),
      borderBottom: span.active ? `2px solid ${span.color}` : 'none',
      cursor: 'pointer'
    }
  }

  /**
   * Realiza un flash temporal en un span (resaltado con animación que desaparece)
   * @param spanId - ID del span a flashear
   * @param duration - Duración del flash en ms (por defecto usa config.flashDuration)
   */
  function flashSpan(spanId: string, duration?: number): void {
    const flashDuration = duration ?? config.flashDuration ?? DEFAULT_FLASH_DURATION

    // Cancelar flash anterior si existe
    const existingFlash = flashingSpans.value.get(spanId)
    if (existingFlash) {
      clearTimeout(existingFlash.timeout)
    }

    // Activar el span visualmente
    const span = spans.value.find(s => s.id === spanId)
    if (span) {
      span.active = true
      span.opacity = config.activeOpacity
    }

    // Programar la desactivación
    const timeout = setTimeout(() => {
      const span = spans.value.find(s => s.id === spanId)
      if (span && !activeSpanIds.value.has(spanId)) {
        span.active = false
        span.opacity = config.baseOpacity
      }
      flashingSpans.value.delete(spanId)
    }, flashDuration)

    flashingSpans.value.set(spanId, { spanId, timeout })
  }

  /**
   * Realiza un flash en todos los spans de un elemento
   * @param type - Tipo de elemento
   * @param elementId - ID del elemento
   * @param duration - Duración del flash en ms
   */
  function flashElement(type: HighlightSpan['type'], elementId: number, duration?: number): void {
    const elementSpans = spans.value.filter(
      span => span.type === type && span.elementId === elementId
    )

    for (const span of elementSpans) {
      flashSpan(span.id, duration)
    }
  }

  /**
   * Cancela un flash en progreso
   */
  function cancelFlash(spanId: string): void {
    const flash = flashingSpans.value.get(spanId)
    if (flash) {
      clearTimeout(flash.timeout)
      flashingSpans.value.delete(spanId)

      // Restaurar estado si no está activo
      const span = spans.value.find(s => s.id === spanId)
      if (span && !activeSpanIds.value.has(spanId)) {
        span.active = false
        span.opacity = config.baseOpacity
      }
    }
  }

  /**
   * Cancela todos los flashes en progreso
   */
  function cancelAllFlashes(): void {
    for (const flash of flashingSpans.value.values()) {
      clearTimeout(flash.timeout)
    }
    flashingSpans.value.clear()
  }

  /**
   * Encuentra el elemento DOM correspondiente a un span y hace scroll hacia él
   * @param spanId - ID del span
   * @param options - Opciones de scroll
   */
  function scrollToSpan(spanId: string, scrollOptions?: ScrollIntoViewOptions): void {
    const element = document.querySelector(`[data-span-id="${spanId}"]`)
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest',
        ...scrollOptions
      })
    }
  }

  /**
   * Hace scroll al primer span de un elemento
   * @param type - Tipo de elemento
   * @param elementId - ID del elemento
   * @param scrollOptions - Opciones de scroll
   */
  function scrollToElement(
    type: HighlightSpan['type'],
    elementId: number,
    scrollOptions?: ScrollIntoViewOptions
  ): void {
    const firstSpan = getFirstSpan(type, elementId)
    if (firstSpan) {
      scrollToSpan(firstSpan.id, scrollOptions)
    }
  }

  /**
   * Hace scroll y flash a un span (navegación completa)
   * @param spanId - ID del span
   * @param flashDuration - Duración del flash en ms
   */
  async function navigateToSpan(spanId: string, flashDuration?: number): Promise<void> {
    scrollToSpan(spanId)

    // Esperar a que termine el scroll antes de flashear
    await nextTick()
    setTimeout(() => {
      flashSpan(spanId, flashDuration)
    }, 300) // Pequeño delay para que el scroll termine
  }

  /**
   * Hace scroll y flash al primer span de un elemento (navegación completa)
   * @param type - Tipo de elemento
   * @param elementId - ID del elemento
   * @param flashDuration - Duración del flash en ms
   */
  async function navigateToElement(
    type: HighlightSpan['type'],
    elementId: number,
    flashDuration?: number
  ): Promise<void> {
    const firstSpan = getFirstSpan(type, elementId)
    if (firstSpan) {
      await navigateToSpan(firstSpan.id, flashDuration)
    }
  }

  /**
   * Verifica si un span está en flash
   */
  function isFlashing(spanId: string): boolean {
    return flashingSpans.value.has(spanId)
  }

  return {
    // Estado
    spans: sortedSpans,
    activeSpans,
    hoveredSpan,
    activeSpanIds,
    flashingSpans,

    // Registro
    registerSpan,
    unregisterSpan,
    unregisterElement,
    clearSpans,

    // Activación
    activateSpan,
    deactivateSpan,
    toggleSpan,
    deactivateAll,
    activateElement,
    deactivateElement,

    // Hover
    setHover,

    // Flash (resaltado temporal)
    flashSpan,
    flashElement,
    cancelFlash,
    cancelAllFlashes,
    isFlashing,

    // Scroll
    scrollToSpan,
    scrollToElement,

    // Navegación (scroll + flash)
    navigateToSpan,
    navigateToElement,

    // Consultas
    getSpansAtPosition,
    getSpansInRange,
    getFirstSpan,

    // Estilos
    getSpanStyle
  }
}

// Singleton para estado global de highlight
let globalHighlight: ReturnType<typeof useHighlight> | null = null

export function useGlobalHighlight(options?: HighlightOptions): ReturnType<typeof useHighlight> {
  if (!globalHighlight) {
    globalHighlight = useHighlight(options)
  }
  return globalHighlight
}

export function resetGlobalHighlight(): void {
  globalHighlight = null
}
