/**
 * useNavigation - Composable para navegación multi-capa
 *
 * Gestiona la navegación entre elementos del documento:
 * - hover → tooltip informativo
 * - click → scroll + highlight temporal
 * - doble-click → modal de detalle
 */

import { ref, computed, type Ref } from 'vue'
import type { Entity, Alert, Chapter } from '@/types'

export interface NavigationTarget {
  type: 'entity' | 'alert' | 'chapter' | 'mention'
  id: number
  element?: HTMLElement
  position?: { start: number; end: number }
}

export interface TooltipData {
  visible: boolean
  x: number
  y: number
  target: NavigationTarget | null
  content: {
    title: string
    subtitle?: string
    badges?: { label: string; color: string }[]
  } | null
}

export interface HighlightState {
  targetId: number | null
  targetType: string | null
  isActive: boolean
  duration: number
}

export function useNavigation(options?: {
  /** Duración del highlight temporal en ms (default: 3000) */
  highlightDuration?: number
  /** Callback cuando se hace click en un elemento */
  onClick?: (target: NavigationTarget) => void
  /** Callback cuando se hace doble-click */
  onDoubleClick?: (target: NavigationTarget) => void
  /** Callback cuando se hace hover */
  onHover?: (target: NavigationTarget | null) => void
}) {
  const highlightDuration = options?.highlightDuration ?? 3000

  // Estado del tooltip
  const tooltip = ref<TooltipData>({
    visible: false,
    x: 0,
    y: 0,
    target: null,
    content: null
  })

  // Estado del highlight temporal
  const highlight = ref<HighlightState>({
    targetId: null,
    targetType: null,
    isActive: false,
    duration: highlightDuration
  })

  // Timer para el highlight
  let highlightTimer: ReturnType<typeof setTimeout> | null = null

  // Timer para el delay del tooltip
  let tooltipTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * Muestra el tooltip para un elemento
   */
  function showTooltip(
    target: NavigationTarget,
    event: MouseEvent,
    content: TooltipData['content']
  ) {
    // Cancelar timer anterior si existe
    if (tooltipTimer) {
      clearTimeout(tooltipTimer)
    }

    // Delay corto antes de mostrar (evita flicker)
    tooltipTimer = setTimeout(() => {
      tooltip.value = {
        visible: true,
        x: event.clientX + 10,
        y: event.clientY + 10,
        target,
        content
      }
      options?.onHover?.(target)
    }, 200)
  }

  /**
   * Oculta el tooltip
   */
  function hideTooltip() {
    if (tooltipTimer) {
      clearTimeout(tooltipTimer)
      tooltipTimer = null
    }
    tooltip.value = {
      visible: false,
      x: 0,
      y: 0,
      target: null,
      content: null
    }
    options?.onHover?.(null)
  }

  /**
   * Activa el highlight temporal en un elemento
   */
  function activateHighlight(target: NavigationTarget) {
    // Cancelar highlight anterior
    if (highlightTimer) {
      clearTimeout(highlightTimer)
    }

    // Activar nuevo highlight
    highlight.value = {
      targetId: target.id,
      targetType: target.type,
      isActive: true,
      duration: highlightDuration
    }

    // Programar desactivación
    highlightTimer = setTimeout(() => {
      deactivateHighlight()
    }, highlightDuration)
  }

  /**
   * Desactiva el highlight temporal
   */
  function deactivateHighlight() {
    highlight.value = {
      targetId: null,
      targetType: null,
      isActive: false,
      duration: highlightDuration
    }

    if (highlightTimer) {
      clearTimeout(highlightTimer)
      highlightTimer = null
    }
  }

  /**
   * Navega a un elemento (scroll + highlight)
   */
  function navigateTo(target: NavigationTarget) {
    // Scroll al elemento si tiene posición
    if (target.element) {
      target.element.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }

    // Activar highlight temporal
    activateHighlight(target)

    // Callback
    options?.onClick?.(target)
  }

  /**
   * Handler para hover en un elemento del documento
   */
  function handleHover(
    target: NavigationTarget,
    event: MouseEvent,
    data: { entity?: Entity; alert?: Alert; chapter?: Chapter }
  ) {
    let content: TooltipData['content'] = null

    if (target.type === 'entity' && data.entity) {
      content = {
        title: data.entity.name,
        subtitle: getEntityLabel(data.entity.type),
        badges: [
          { label: `${data.entity.mentionCount} apariciones`, color: 'var(--ds-color-primary)' }
        ]
      }
    } else if (target.type === 'alert' && data.alert) {
      content = {
        title: data.alert.title,
        subtitle: data.alert.description?.slice(0, 100),
        badges: [{ label: getSeverityLabel(data.alert.severity), color: getSeverityColor(data.alert.severity) }]
      }
    } else if (target.type === 'chapter' && data.chapter) {
      content = {
        title: data.chapter.title,
        subtitle: `${data.chapter.wordCount.toLocaleString()} palabras`
      }
    }

    if (content) {
      showTooltip(target, event, content)
    }
  }

  /**
   * Handler para leave de un elemento
   */
  function handleLeave() {
    hideTooltip()
  }

  /**
   * Handler para click en un elemento
   */
  function handleClick(target: NavigationTarget) {
    navigateTo(target)
  }

  /**
   * Handler para doble-click en un elemento
   */
  function handleDoubleClick(target: NavigationTarget) {
    options?.onDoubleClick?.(target)
  }

  /**
   * Verifica si un elemento está resaltado
   */
  function isHighlighted(type: string, id: number): boolean {
    return highlight.value.isActive && highlight.value.targetType === type && highlight.value.targetId === id
  }

  // Helpers
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

  function getSeverityLabel(severity: string): string {
    const labels: Record<string, string> = {
      critical: 'Crítico',
      high: 'Alto',
      medium: 'Medio',
      low: 'Bajo',
      info: 'Info'
    }
    return labels[severity] || severity
  }

  function getSeverityColor(severity: string): string {
    const colors: Record<string, string> = {
      critical: 'var(--ds-color-danger)',
      high: 'var(--ds-color-warning)',
      medium: 'var(--ds-color-warning-subtle)',
      low: 'var(--ds-color-info)',
      info: 'var(--ds-color-info-subtle)'
    }
    return colors[severity] || 'var(--ds-color-text-secondary)'
  }

  // Cleanup
  function cleanup() {
    if (highlightTimer) {
      clearTimeout(highlightTimer)
      highlightTimer = null
    }
    if (tooltipTimer) {
      clearTimeout(tooltipTimer)
      tooltipTimer = null
    }
  }

  return {
    // Estado
    tooltip,
    highlight,

    // Acciones
    showTooltip,
    hideTooltip,
    activateHighlight,
    deactivateHighlight,
    navigateTo,

    // Handlers
    handleHover,
    handleLeave,
    handleClick,
    handleDoubleClick,

    // Utilities
    isHighlighted,
    cleanup
  }
}
