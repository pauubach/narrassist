/**
 * API Types - Alertas
 *
 * Tipos que coinciden EXACTAMENTE con lo que devuelve el backend.
 * NO modificar sin actualizar el backend también.
 */

/** Fuente de una inconsistencia (ubicación donde se menciona un valor) */
export interface ApiAlertSource {
  chapter: number | null
  page?: number
  line?: number
  start_char: number
  end_char: number
  excerpt: string
  value: string
}

/** Datos adicionales de la alerta según su tipo */
export interface ApiAlertExtraData {
  // Para attribute_inconsistency
  entity_name?: string
  attribute_key?: string
  value1?: string
  value2?: string
  sources?: ApiAlertSource[]
  // Para otros tipos de alertas
  [key: string]: unknown
}

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
  | 'typography'
  | 'punctuation'
  | 'repetition'
  | 'agreement'
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
  /** Datos adicionales específicos del tipo de alerta (sources para inconsistencias, etc.) */
  extra_data?: ApiAlertExtraData | null
  /** S14: Revision Intelligence fields */
  previous_alert_summary?: string | null
  match_confidence?: number | null
  resolution_reason?: string | null
}

// ============================================================================
// S14: Comparison / Revision Intelligence API types
// ============================================================================

export interface ApiComparisonAlertDiff {
  alert_type: string
  category: string
  severity: string
  title: string
  chapter: number | null
  confidence: number
  resolution_reason?: string
  match_confidence?: number
  start_char?: number | null
  end_char?: number | null
}

export interface ApiComparisonDetail {
  has_comparison: boolean
  project_id?: number
  snapshot_id?: number
  snapshot_created_at?: string
  document_fingerprint_changed?: boolean
  alerts?: {
    new: ApiComparisonAlertDiff[]
    resolved: ApiComparisonAlertDiff[]
    unchanged: number
  }
  entities?: {
    added: { canonical_name: string; entity_type: string }[]
    removed: { canonical_name: string; entity_type: string }[]
    unchanged: number
  }
  summary?: {
    total_alerts_before: number
    total_alerts_after: number
    total_entities_before: number
    total_entities_after: number
  }
}
