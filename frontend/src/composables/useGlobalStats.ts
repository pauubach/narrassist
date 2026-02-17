/**
 * useGlobalStats - Estadísticas globales agregadas de todos los proyectos.
 *
 * Cachea stats por proyecto en localStorage cuando se abren y cargaron alertas.
 * Agrega las stats para la vista global (HomeView).
 */

import { computed } from 'vue'
import type { Alert } from '@/types'
import { META_CATEGORIES } from '@/composables/useAlertUtils'
import { safeGetItem, safeSetItem } from '@/utils/safeStorage'

const STATS_PREFIX = 'na_project_stats_'

interface ProjectStats {
  projectId: number
  projectName: string
  total: number
  resolved: number
  dismissed: number
  active: number
  byMetaCategory: {
    errors: number
    inconsistencies: number
    suggestions: number
  }
  lastUpdated: string
}

/**
 * Actualiza las stats cacheadas de un proyecto.
 * Se llama desde ProjectDetailView cuando se cargan alertas.
 */
export function updateProjectStats(projectId: number, projectName: string, alerts: Alert[]) {
  const stats: ProjectStats = {
    projectId,
    projectName,
    total: alerts.length,
    resolved: alerts.filter(a => a.status === 'resolved').length,
    dismissed: alerts.filter(a => a.status === 'dismissed').length,
    active: alerts.filter(a => a.status === 'active').length,
    byMetaCategory: {
      errors: alerts.filter(a => META_CATEGORIES.errors.categories.includes(a.category)).length,
      inconsistencies: alerts.filter(a => META_CATEGORIES.inconsistencies.categories.includes(a.category)).length,
      suggestions: alerts.filter(a => META_CATEGORIES.suggestions.categories.includes(a.category)).length,
    },
    lastUpdated: new Date().toISOString(),
  }

  safeSetItem(`${STATS_PREFIX}${projectId}`, JSON.stringify(stats))
}

/**
 * Obtiene las stats cacheadas de un proyecto específico.
 */
export function getProjectStats(projectId: number): ProjectStats | null {
  const raw = safeGetItem(`${STATS_PREFIX}${projectId}`)
  if (!raw) return null
  try {
    return JSON.parse(raw) as ProjectStats
  } catch {
    return null
  }
}

/**
 * Obtiene todas las stats cacheadas de todos los proyectos.
 */
function getAllProjectStats(): ProjectStats[] {
  const stats: ProjectStats[] = []
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key?.startsWith(STATS_PREFIX)) {
        const raw = localStorage.getItem(key)
        if (raw) {
          stats.push(JSON.parse(raw))
        }
      }
    }
  } catch {
    // Silenciar errores de localStorage
  }
  return stats
}

/** Minutos de ahorro estimados por tipo de alerta */
const TIME_SAVINGS: Record<string, number> = {
  errors: 2,         // 2 min por errata
  inconsistencies: 5, // 5 min por inconsistencia
  suggestions: 3,    // 3 min por sugerencia
}

export function useGlobalStats() {
  const allStats = computed(() => getAllProjectStats())

  const globalMetrics = computed(() => {
    const stats = allStats.value
    const manuscripts = stats.length
    const totalAlerts = stats.reduce((sum, s) => sum + s.total, 0)
    const reviewed = stats.reduce((sum, s) => sum + s.resolved + s.dismissed, 0)
    const active = stats.reduce((sum, s) => sum + s.active, 0)

    // Calcular tiempo ahorrado por tipo
    let timeSavedMinutes = 0
    for (const s of stats) {
      timeSavedMinutes += s.byMetaCategory.errors * TIME_SAVINGS.errors
      timeSavedMinutes += s.byMetaCategory.inconsistencies * TIME_SAVINGS.inconsistencies
      timeSavedMinutes += s.byMetaCategory.suggestions * TIME_SAVINGS.suggestions
    }

    const reviewRate = totalAlerts > 0 ? Math.round((reviewed / totalAlerts) * 100) : 0

    return {
      manuscripts,
      totalAlerts,
      reviewed,
      active,
      timeSavedMinutes,
      timeSavedFormatted: formatTime(timeSavedMinutes),
      reviewRate,
    }
  })

  return { globalMetrics, allStats }
}

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) return `${hours}h`
  return `${hours}h ${mins}m`
}
