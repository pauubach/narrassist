/**
 * useAlertUtils - Utilidades para trabajar con alertas de inconsistencia.
 *
 * Proporciona funciones helper para severidades, categorías y formateo de alertas.
 */

import type { Alert, AlertSeverity, AlertCategory, AlertStatus } from '@/types'

export interface SeverityConfig {
  label: string
  icon: string
  color: string
  priority: number
}

export interface CategoryConfig {
  label: string
  description: string
  icon: string
}

export interface StatusConfig {
  label: string
  icon: string
}

const severityConfigs: Record<AlertSeverity, SeverityConfig> = {
  critical: {
    label: 'Crítico',
    icon: 'pi pi-exclamation-circle',
    color: 'var(--ds-alert-critical)',
    priority: 5,
  },
  high: {
    label: 'Alto',
    icon: 'pi pi-exclamation-triangle',
    color: 'var(--ds-alert-high)',
    priority: 4,
  },
  medium: {
    label: 'Medio',
    icon: 'pi pi-info-circle',
    color: 'var(--ds-alert-medium)',
    priority: 3,
  },
  low: {
    label: 'Bajo',
    icon: 'pi pi-circle',
    color: 'var(--ds-alert-low)',
    priority: 2,
  },
  info: {
    label: 'Información',
    icon: 'pi pi-info',
    color: 'var(--ds-alert-info)',
    priority: 1,
  },
}

const categoryConfigs: Record<AlertCategory, CategoryConfig> = {
  attribute: {
    label: 'Inconsistencia de atributo',
    description: 'Un personaje tiene atributos contradictorios',
    icon: 'pi pi-user-edit',
  },
  timeline: {
    label: 'Inconsistencia temporal',
    description: 'Problema en la línea temporal de eventos',
    icon: 'pi pi-clock',
  },
  relationship: {
    label: 'Inconsistencia de relación',
    description: 'Contradicción en relaciones entre personajes',
    icon: 'pi pi-users',
  },
  location: {
    label: 'Inconsistencia de ubicación',
    description: 'Un personaje aparece en lugares imposibles',
    icon: 'pi pi-map',
  },
  behavior: {
    label: 'Inconsistencia de comportamiento',
    description: 'Acción fuera de carácter del personaje',
    icon: 'pi pi-exclamation-triangle',
  },
  knowledge: {
    label: 'Inconsistencia de conocimiento',
    description: 'Personaje sabe algo que no debería',
    icon: 'pi pi-brain',
  },
  style: {
    label: 'Problema de estilo',
    description: 'Repeticiones, voz narrativa, etc.',
    icon: 'pi pi-pencil',
  },
  grammar: {
    label: 'Error gramatical u ortográfico',
    description: 'Errores de escritura detectados',
    icon: 'pi pi-spell-check',
  },
  structure: {
    label: 'Problema estructural',
    description: 'Problemas en la estructura narrativa',
    icon: 'pi pi-sitemap',
  },
  other: {
    label: 'Otra inconsistencia',
    description: 'Otro tipo de problema narrativo',
    icon: 'pi pi-question-circle',
  },
}

const statusConfigs: Record<AlertStatus, StatusConfig> = {
  active: {
    label: 'Activa',
    icon: 'pi pi-circle-fill',
  },
  dismissed: {
    label: 'Descartada',
    icon: 'pi pi-times-circle',
  },
  resolved: {
    label: 'Resuelta',
    icon: 'pi pi-check-circle',
  },
}

export function useAlertUtils() {
  /**
   * Obtiene la configuración de una severidad
   */
  function getSeverityConfig(severity: AlertSeverity): SeverityConfig {
    return severityConfigs[severity] || severityConfigs.medium
  }

  /**
   * Obtiene la configuración de una categoría
   */
  function getCategoryConfig(category: AlertCategory): CategoryConfig {
    return categoryConfigs[category] || categoryConfigs.other
  }

  /**
   * Obtiene la configuración de un estado
   */
  function getStatusConfig(status: AlertStatus): StatusConfig {
    return statusConfigs[status] || statusConfigs.active
  }

  /**
   * Obtiene el color CSS para una severidad
   */
  function getSeverityColor(severity: AlertSeverity): string {
    return getSeverityConfig(severity).color
  }

  /**
   * Obtiene el icono para una severidad
   */
  function getSeverityIcon(severity: AlertSeverity): string {
    return getSeverityConfig(severity).icon
  }

  /**
   * Obtiene el label traducido para una severidad
   */
  function getSeverityLabel(severity: AlertSeverity): string {
    return getSeverityConfig(severity).label
  }

  /**
   * Ordena alertas por severidad (más grave primero) y luego por fecha
   */
  function sortAlerts(alerts: Alert[]): Alert[] {
    return [...alerts].sort((a, b) => {
      const priorityA = getSeverityConfig(a.severity).priority
      const priorityB = getSeverityConfig(b.severity).priority

      if (priorityA !== priorityB) {
        return priorityB - priorityA // Mayor prioridad primero
      }

      // Si misma severidad, ordenar por fecha (más reciente primero)
      const dateA = a.createdAt?.getTime() ?? 0
      const dateB = b.createdAt?.getTime() ?? 0
      return dateB - dateA
    })
  }

  /**
   * Agrupa alertas por categoría
   */
  function groupAlertsByCategory(alerts: Alert[]): Map<AlertCategory, Alert[]> {
    const groups = new Map<AlertCategory, Alert[]>()

    for (const alert of alerts) {
      const existing = groups.get(alert.category) || []
      existing.push(alert)
      groups.set(alert.category, existing)
    }

    // Ordenar dentro de cada grupo
    for (const [category, list] of groups) {
      groups.set(category, sortAlerts(list))
    }

    return groups
  }

  /**
   * Agrupa alertas por severidad
   */
  function groupAlertsBySeverity(alerts: Alert[]): Map<AlertSeverity, Alert[]> {
    const groups = new Map<AlertSeverity, Alert[]>()

    for (const alert of alerts) {
      const existing = groups.get(alert.severity) || []
      existing.push(alert)
      groups.set(alert.severity, existing)
    }

    return groups
  }

  /**
   * Filtra alertas por búsqueda de texto
   */
  function filterAlerts(alerts: Alert[], query: string): Alert[] {
    if (!query.trim()) return alerts

    const normalizedQuery = query.toLowerCase().trim()

    return alerts.filter((alert) => {
      // Buscar en título
      if (alert.title.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      // Buscar en descripción
      if (alert.description.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      // Buscar en sugerencia
      if (alert.suggestion?.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      return false
    })
  }

  /**
   * Cuenta alertas por severidad
   */
  function countBySeverity(alerts: Alert[]): Record<AlertSeverity, number> {
    const counts: Record<AlertSeverity, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    }

    for (const alert of alerts) {
      counts[alert.severity]++
    }

    return counts
  }

  /**
   * Cuenta alertas por estado
   */
  function countByStatus(alerts: Alert[]): Record<AlertStatus, number> {
    const counts: Record<AlertStatus, number> = {
      active: 0,
      dismissed: 0,
      resolved: 0,
    }

    for (const alert of alerts) {
      counts[alert.status]++
    }

    return counts
  }

  /**
   * Obtiene solo alertas activas
   */
  function getActiveAlerts(alerts: Alert[]): Alert[] {
    return alerts.filter((alert) => alert.status === 'active')
  }

  /**
   * Formatea la ubicación de una alerta (capítulo + posición)
   */
  function formatAlertLocation(alert: Alert): string {
    const parts: string[] = []

    if (alert.chapter !== undefined) {
      parts.push(`Cap. ${alert.chapter}`)
    }

    if (alert.spanStart !== undefined && alert.spanEnd !== undefined) {
      parts.push(`pos. ${alert.spanStart}-${alert.spanEnd}`)
    }

    return parts.join(' · ') || 'Sin ubicación'
  }

  /**
   * Obtiene todas las configuraciones de severidad (para selectores)
   */
  function getAllSeverityConfigs(): Array<{ value: AlertSeverity } & SeverityConfig> {
    return (Object.entries(severityConfigs) as [AlertSeverity, SeverityConfig][]).map(
      ([value, config]) => ({ value, ...config }),
    )
  }

  /**
   * Obtiene todas las configuraciones de categoría (para selectores)
   */
  function getAllCategoryConfigs(): Array<{ value: AlertCategory } & CategoryConfig> {
    return (Object.entries(categoryConfigs) as [AlertCategory, CategoryConfig][]).map(
      ([value, config]) => ({ value, ...config }),
    )
  }

  return {
    getSeverityConfig,
    getCategoryConfig,
    getStatusConfig,
    getSeverityColor,
    getSeverityIcon,
    getSeverityLabel,
    sortAlerts,
    groupAlertsByCategory,
    groupAlertsBySeverity,
    filterAlerts,
    countBySeverity,
    countByStatus,
    getActiveAlerts,
    formatAlertLocation,
    getAllSeverityConfigs,
    getAllCategoryConfigs,
  }
}
