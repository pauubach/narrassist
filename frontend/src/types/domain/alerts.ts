/**
 * Domain Types - Alertas
 *
 * Tipos simplificados para uso interno en la UI.
 */

/** Severidad de alerta normalizada para la UI */
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** Estado de alerta simplificado */
export type AlertStatus = 'active' | 'dismissed' | 'resolved'

/** Categoría de alerta para la UI */
export type AlertCategory =
  | 'attribute'     // consistency
  | 'timeline'      // time-related from consistency
  | 'relationship'  // relaciones entre personajes
  | 'location'      // world
  | 'behavior'      // behavioral
  | 'knowledge'     // focalization
  | 'style'         // style
  | 'grammar'       // grammar, orthography
  | 'structure'     // structure
  | 'other'         // entity, other

/** Alerta para uso en componentes */
export interface Alert {
  id: number
  projectId: number
  category: AlertCategory
  severity: AlertSeverity
  status: AlertStatus
  title: string
  description: string
  explanation?: string
  suggestion?: string
  chapter?: number
  spanStart?: number
  spanEnd?: number
  /** Fragmento del texto donde ocurre la alerta */
  excerpt?: string
  entityIds: number[]
  confidence: number
  createdAt: Date
  resolvedAt?: Date
}

/** Filtros para alertas */
export interface AlertFilters {
  severity?: AlertSeverity[]
  category?: AlertCategory[]
  status?: AlertStatus[]
  entityId?: number
  chapter?: number
  search?: string
}

/** Estadísticas de alertas */
export interface AlertStats {
  total: number
  bySeverity: Record<AlertSeverity, number>
  byCategory: Record<AlertCategory, number>
  byStatus: Record<AlertStatus, number>
}
