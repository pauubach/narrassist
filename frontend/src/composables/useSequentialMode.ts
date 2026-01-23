/**
 * useSequentialMode - Composable para el modo de corrección secuencial
 *
 * Gestiona el estado y la navegación del modo "túnel" para revisar
 * alertas una por una de forma enfocada.
 *
 * Basado en recomendaciones de expertos:
 * - UX Designer: Layout adaptativo, mínimos clics
 * - Editor profesional: Flujo con teclado, contexto visible
 * - Accesibilidad: Sin auto-avance, undo multinivel
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import type { Alert, AlertStatus, AlertSeverity } from '@/types'
import { apiUrl } from '@/config/api'

export interface SequentialFilters {
  statuses: AlertStatus[]
  minSeverity?: AlertSeverity
  categories?: string[]
  chapters?: number[]
}

export interface CorrectionAction {
  alertId: number
  action: 'resolve' | 'dismiss' | 'flag' | 'skip'
  previousStatus: AlertStatus
  timestamp: Date
}

export interface SequentialSettings {
  autoAdvance: boolean
  autoAdvanceDelay: number // ms
  showResolved: boolean
  contextLevel: 'minimal' | 'paragraph' | 'section'
}

const severityOrder: Record<AlertSeverity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
}

const MAX_UNDO_HISTORY = 50

export function useSequentialMode(
  allAlerts: () => Alert[],
  projectId: () => number,
  onAlertStatusChanged?: (alertId: number, newStatus: AlertStatus) => void
) {
  // State
  const active = ref(false)
  const currentIndex = ref(0)
  const filters = ref<SequentialFilters>({
    statuses: ['active'],
    minSeverity: undefined,
    categories: undefined,
    chapters: undefined,
  })
  const settings = ref<SequentialSettings>({
    autoAdvance: false,
    autoAdvanceDelay: 1000,
    showResolved: false,
    contextLevel: 'paragraph',
  })
  const updating = ref(false)
  const actionHistory = ref<CorrectionAction[]>([])
  const sessionStartedAt = ref<Date | null>(null)

  // Computed
  const filteredAlerts = computed(() => {
    let alerts = allAlerts()

    // Filter by status
    if (filters.value.statuses.length > 0) {
      if (settings.value.showResolved) {
        // Show all but still track which filter was selected
        // Resolved alerts will be visually distinct
      } else {
        alerts = alerts.filter(a => filters.value.statuses.includes(a.status))
      }
    }

    // Filter by minimum severity
    if (filters.value.minSeverity) {
      const minOrder = severityOrder[filters.value.minSeverity]
      alerts = alerts.filter(a => severityOrder[a.severity] >= minOrder)
    }

    // Filter by categories
    if (filters.value.categories && filters.value.categories.length > 0) {
      alerts = alerts.filter(a => filters.value.categories!.includes(a.category))
    }

    // Filter by chapters
    if (filters.value.chapters && filters.value.chapters.length > 0) {
      alerts = alerts.filter(a => a.chapter !== undefined && filters.value.chapters!.includes(a.chapter))
    }

    // Sort by chapter, then by position within chapter
    return alerts.sort((a, b) => {
      // First by chapter
      const chapterA = a.chapter ?? 0
      const chapterB = b.chapter ?? 0
      if (chapterA !== chapterB) return chapterA - chapterB

      // Then by position
      const posA = a.spanStart ?? 0
      const posB = b.spanStart ?? 0
      return posA - posB
    })
  })

  const totalCount = computed(() => filteredAlerts.value.length)

  const pendingCount = computed(() =>
    filteredAlerts.value.filter(a => a.status === 'active').length
  )

  const currentAlert = computed(() => {
    if (currentIndex.value < 0 || currentIndex.value >= filteredAlerts.value.length) {
      return null
    }
    return filteredAlerts.value[currentIndex.value]
  })

  const hasNext = computed(() => currentIndex.value < totalCount.value - 1)
  const hasPrevious = computed(() => currentIndex.value > 0)

  const progress = computed(() => ({
    current: totalCount.value > 0 ? currentIndex.value + 1 : 0,
    total: totalCount.value,
    pending: pendingCount.value,
    percentage: totalCount.value > 0
      ? Math.round(((currentIndex.value + 1) / totalCount.value) * 100)
      : 0,
  }))

  const recentActions = computed(() =>
    actionHistory.value.slice(-10).reverse()
  )

  const canUndo = computed(() => actionHistory.value.length > 0)

  // Keyboard handling
  let keyboardHandler: ((e: KeyboardEvent) => void) | null = null

  function setupKeyboardShortcuts() {
    keyboardHandler = (e: KeyboardEvent) => {
      // Don't handle if focus is in an input field
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      // Don't handle if modifiers are pressed (except for Ctrl+Z)
      if (e.altKey || e.metaKey) return
      if (e.ctrlKey && e.key !== 'z' && e.key !== 'Z') return

      switch (e.key) {
        // Navigation
        case 'ArrowRight':
        case 'n':
        case 'N':
          e.preventDefault()
          next()
          break
        case 'ArrowLeft':
        case 'p':
        case 'P':
          e.preventDefault()
          previous()
          break
        case 'Home':
          e.preventDefault()
          goTo(0)
          break
        case 'End':
          e.preventDefault()
          goTo(totalCount.value - 1)
          break

        // Actions
        case 'a':
        case 'A':
        case 'Enter':
          e.preventDefault()
          resolveCurrentAndAdvance()
          break
        case 'd':
        case 'D':
          e.preventDefault()
          dismissCurrentAndAdvance()
          break
        case 's':
        case 'S':
          e.preventDefault()
          skipToNext()
          break
        case 'f':
        case 'F':
          e.preventDefault()
          flagCurrentAndAdvance()
          break

        // Undo
        case 'z':
        case 'Z':
          if (e.ctrlKey) {
            e.preventDefault()
            undoLastAction()
          }
          break

        // Exit
        case 'Escape':
          e.preventDefault()
          exit()
          break
      }
    }

    window.addEventListener('keydown', keyboardHandler)
  }

  function teardownKeyboardShortcuts() {
    if (keyboardHandler) {
      window.removeEventListener('keydown', keyboardHandler)
      keyboardHandler = null
    }
  }

  // Actions
  function enter(initialFilters?: Partial<SequentialFilters>) {
    if (initialFilters) {
      filters.value = {
        ...filters.value,
        ...initialFilters,
      }
    }
    currentIndex.value = 0
    actionHistory.value = []
    sessionStartedAt.value = new Date()
    active.value = true
    setupKeyboardShortcuts()
  }

  function exit() {
    teardownKeyboardShortcuts()
    active.value = false
    currentIndex.value = 0
  }

  function next() {
    if (hasNext.value) {
      currentIndex.value++
    }
  }

  function previous() {
    if (hasPrevious.value) {
      currentIndex.value--
    }
  }

  function goTo(index: number) {
    if (index >= 0 && index < totalCount.value) {
      currentIndex.value = index
    }
  }

  function goToAlert(alertId: number) {
    const index = filteredAlerts.value.findIndex(a => a.id === alertId)
    if (index >= 0) {
      currentIndex.value = index
    }
  }

  async function updateAlertStatus(
    alert: Alert,
    newStatus: AlertStatus
  ): Promise<boolean> {
    updating.value = true
    try {
      const response = await fetch(
        apiUrl(`/api/projects/${projectId()}/alerts/${alert.id}/status`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        }
      )

      if (response.ok) {
        // Record action for undo
        actionHistory.value.push({
          alertId: alert.id,
          action: newStatus === 'resolved' ? 'resolve' : newStatus === 'dismissed' ? 'dismiss' : 'flag',
          previousStatus: alert.status,
          timestamp: new Date(),
        })

        // Trim history if needed
        if (actionHistory.value.length > MAX_UNDO_HISTORY) {
          actionHistory.value = actionHistory.value.slice(-MAX_UNDO_HISTORY)
        }

        // Notify parent
        onAlertStatusChanged?.(alert.id, newStatus)

        return true
      }
    } catch (error) {
      console.error('Error updating alert status:', error)
    } finally {
      updating.value = false
    }
    return false
  }

  function advanceAfterAction() {
    // If we're not showing resolved alerts and the current alert was resolved,
    // it will be filtered out, so we stay at the same index (shows next alert)
    // Otherwise, we need to explicitly move to next
    if (settings.value.showResolved && hasNext.value) {
      if (settings.value.autoAdvance) {
        setTimeout(() => next(), settings.value.autoAdvanceDelay)
      }
    }
    // If not showing resolved, the list will update and we'll see the next alert
    // at the current index (because the resolved one is filtered out)
  }

  async function resolveCurrentAndAdvance() {
    const alert = currentAlert.value
    if (!alert || alert.status === 'resolved') return false

    const success = await updateAlertStatus(alert, 'resolved')
    if (success) {
      advanceAfterAction()
    }
    return success
  }

  async function dismissCurrentAndAdvance() {
    const alert = currentAlert.value
    if (!alert || alert.status === 'dismissed') return false

    const success = await updateAlertStatus(alert, 'dismissed')
    if (success) {
      advanceAfterAction()
    }
    return success
  }

  async function flagCurrentAndAdvance() {
    // "Flag" is treated as a special dismiss with metadata
    // In the future, we could add a separate "flagged" status
    // For now, we'll use a note or just skip
    const alert = currentAlert.value
    if (!alert) return false

    // Record as a "flag" action but don't change status
    actionHistory.value.push({
      alertId: alert.id,
      action: 'flag',
      previousStatus: alert.status,
      timestamp: new Date(),
    })

    // Move to next
    if (hasNext.value) {
      next()
    }
    return true
  }

  function skipToNext() {
    const alert = currentAlert.value
    if (!alert) return

    // Record skip action
    actionHistory.value.push({
      alertId: alert.id,
      action: 'skip',
      previousStatus: alert.status,
      timestamp: new Date(),
    })

    if (hasNext.value) {
      next()
    }
  }

  async function undoLastAction(): Promise<boolean> {
    if (actionHistory.value.length === 0) return false

    const lastAction = actionHistory.value.pop()!

    // Skip and flag don't need API undo
    if (lastAction.action === 'skip' || lastAction.action === 'flag') {
      // Navigate back to that alert
      goToAlert(lastAction.alertId)
      return true
    }

    // Restore previous status
    updating.value = true
    try {
      const response = await fetch(
        apiUrl(`/api/projects/${projectId()}/alerts/${lastAction.alertId}/status`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: lastAction.previousStatus }),
        }
      )

      if (response.ok) {
        onAlertStatusChanged?.(lastAction.alertId, lastAction.previousStatus)
        goToAlert(lastAction.alertId)
        return true
      }
    } catch (error) {
      console.error('Error undoing action:', error)
      // Put the action back
      actionHistory.value.push(lastAction)
    } finally {
      updating.value = false
    }
    return false
  }

  function setFilters(newFilters: Partial<SequentialFilters>) {
    filters.value = {
      ...filters.value,
      ...newFilters,
    }
    // Reset to first alert when filters change
    currentIndex.value = 0
  }

  function setSettings(newSettings: Partial<SequentialSettings>) {
    settings.value = {
      ...settings.value,
      ...newSettings,
    }
  }

  // Watch for alerts changes (e.g., after resolve/dismiss from external source)
  watch(filteredAlerts, (newAlerts) => {
    // Ensure currentIndex is within bounds
    if (currentIndex.value >= newAlerts.length) {
      currentIndex.value = Math.max(0, newAlerts.length - 1)
    }
  })

  // Cleanup on unmount
  onUnmounted(() => {
    teardownKeyboardShortcuts()
  })

  return {
    // State
    active,
    currentIndex,
    filters,
    settings,
    updating,
    actionHistory,
    sessionStartedAt,

    // Computed
    filteredAlerts,
    totalCount,
    pendingCount,
    currentAlert,
    hasNext,
    hasPrevious,
    progress,
    recentActions,
    canUndo,

    // Actions
    enter,
    exit,
    next,
    previous,
    goTo,
    goToAlert,
    resolveCurrentAndAdvance,
    dismissCurrentAndAdvance,
    flagCurrentAndAdvance,
    skipToNext,
    undoLastAction,
    setFilters,
    setSettings,
  }
}
