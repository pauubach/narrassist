/**
 * API Types - Alertas
 *
 * Tipos que coinciden EXACTAMENTE con lo que devuelve el backend.
 * NO modificar sin actualizar el backend también.
 */

/** Severidad de alerta del backend */
export type ApiAlertSeverity = 'critical' | 'warning' | 'info' | 'hint'

/** Estado de alerta del backend */
export type ApiAlertStatus =
  | 'new'
  | 'open'
  | 'acknowledged'
  | 'in_progress'
  | 'resolved'
  | 'dismissed'
  | 'auto_resolved'

/** Categoría de alerta del backend */
export type ApiAlertCategory =
  | 'consistency'
  | 'style'
  | 'behavioral'
  | 'focalization'
  | 'structure'
  | 'world'
  | 'entity'
  | 'orthography'
  | 'grammar'
  | 'other'

/** Alerta tal como la devuelve la API */
export interface ApiAlert {
  id: number
  project_id: number
  category: ApiAlertCategory
  severity: ApiAlertSeverity
  alert_type: string
  title: string
  description: string
  explanation: string
  suggestion: string | null
  chapter: number | null
  start_char: number | null
  end_char: number | null
  /** Fragmento del texto donde ocurre la alerta */
  excerpt: string | null
  status: ApiAlertStatus
  entity_ids: number[]
  confidence: number
  created_at: string
  updated_at?: string
  resolved_at: string | null
}
