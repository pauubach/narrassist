/**
 * Transformers - Alertas
 *
 * Funciones para convertir entre tipos API y Domain.
 */

import type {
  ApiAlert,
  ApiAlertSeverity,
  ApiAlertStatus,
  ApiAlertCategory,
} from '../api/alerts'

import type {
  Alert,
  AlertSeverity,
  AlertStatus,
  AlertCategory,
} from '../domain/alerts'

// =============================================================================
// Mapeos de tipos
// =============================================================================

const SEVERITY_MAP: Record<ApiAlertSeverity, AlertSeverity> = {
  critical: 'critical',
  warning: 'high',
  info: 'medium',
  hint: 'low',
}

const STATUS_MAP: Record<ApiAlertStatus, AlertStatus> = {
  new: 'active',
  open: 'active',
  acknowledged: 'active',
  in_progress: 'active',
  resolved: 'resolved',
  dismissed: 'dismissed',
  auto_resolved: 'resolved',
}

const CATEGORY_MAP: Record<ApiAlertCategory, AlertCategory> = {
  consistency: 'attribute',
  style: 'style',
  behavioral: 'behavior',
  focalization: 'knowledge',
  structure: 'structure',
  world: 'location',
  entity: 'other',
  orthography: 'grammar',
  grammar: 'grammar',
  other: 'other',
}

// Mapeo inverso para enviar al backend
const SEVERITY_TO_API: Record<AlertSeverity, ApiAlertSeverity> = {
  critical: 'critical',
  high: 'warning',
  medium: 'info',
  low: 'hint',
  info: 'info',
}

const STATUS_TO_API: Record<AlertStatus, ApiAlertStatus> = {
  active: 'open',
  dismissed: 'dismissed',
  resolved: 'resolved',
}

const CATEGORY_TO_API: Record<AlertCategory, ApiAlertCategory> = {
  attribute: 'consistency',
  timeline: 'consistency',
  relationship: 'consistency',
  location: 'world',
  behavior: 'behavioral',
  knowledge: 'focalization',
  style: 'style',
  grammar: 'grammar',
  structure: 'structure',
  other: 'other',
}

// =============================================================================
// Transformadores API -> Domain
// =============================================================================

/** Transforma AlertSeverity de API a Domain */
export function transformAlertSeverity(apiSeverity: ApiAlertSeverity): AlertSeverity {
  return SEVERITY_MAP[apiSeverity] ?? 'medium'
}

/** Transforma AlertStatus de API a Domain */
export function transformAlertStatus(apiStatus: ApiAlertStatus): AlertStatus {
  return STATUS_MAP[apiStatus] ?? 'active'
}

/** Transforma AlertCategory de API a Domain */
export function transformAlertCategory(apiCategory: ApiAlertCategory): AlertCategory {
  return CATEGORY_MAP[apiCategory] ?? 'other'
}

/** Transforma una alerta de API a Domain */
export function transformAlert(api: ApiAlert): Alert {
  return {
    id: api.id,
    projectId: api.project_id,
    category: transformAlertCategory(api.category),
    severity: transformAlertSeverity(api.severity),
    status: transformAlertStatus(api.status),
    title: api.title,
    description: api.description,
    explanation: api.explanation || undefined,
    suggestion: api.suggestion ?? undefined,
    chapter: api.chapter ?? undefined,
    spanStart: api.start_char ?? undefined,
    spanEnd: api.end_char ?? undefined,
    excerpt: api.excerpt ?? undefined,
    entityIds: api.entity_ids,
    confidence: api.confidence,
    createdAt: new Date(api.created_at),
    resolvedAt: api.resolved_at ? new Date(api.resolved_at) : undefined,
  }
}

/** Transforma un array de alertas */
export function transformAlerts(apiAlerts: ApiAlert[]): Alert[] {
  return apiAlerts.map(transformAlert)
}

// =============================================================================
// Transformadores Domain -> API
// =============================================================================

/** Transforma AlertSeverity de Domain a API */
export function alertSeverityToApi(severity: AlertSeverity): ApiAlertSeverity {
  return SEVERITY_TO_API[severity]
}

/** Transforma AlertStatus de Domain a API */
export function alertStatusToApi(status: AlertStatus): ApiAlertStatus {
  return STATUS_TO_API[status]
}

/** Transforma AlertCategory de Domain a API */
export function alertCategoryToApi(category: AlertCategory): ApiAlertCategory {
  return CATEGORY_TO_API[category]
}

// =============================================================================
// Helpers para compatibilidad con código legacy
// =============================================================================

/** Normaliza una severidad desde cualquier formato */
export function normalizeAlertSeverity(severity: string): AlertSeverity {
  const lower = severity.toLowerCase()

  // Si ya es un valor domain válido
  const validDomain: AlertSeverity[] = ['critical', 'high', 'medium', 'low', 'info']
  if (validDomain.includes(lower as AlertSeverity)) {
    return lower as AlertSeverity
  }

  // Mapear desde valores API
  return SEVERITY_MAP[lower as ApiAlertSeverity] ?? 'medium'
}

/** Normaliza un estado desde cualquier formato */
export function normalizeAlertStatus(status: string): AlertStatus {
  const lower = status.toLowerCase()

  // Si ya es un valor domain válido
  const validDomain: AlertStatus[] = ['active', 'dismissed', 'resolved']
  if (validDomain.includes(lower as AlertStatus)) {
    return lower as AlertStatus
  }

  // Mapear desde valores API
  return STATUS_MAP[lower as ApiAlertStatus] ?? 'active'
}

/** Normaliza una categoría desde cualquier formato */
export function normalizeAlertCategory(category: string): AlertCategory {
  const lower = category.toLowerCase()

  // Si ya es un valor domain válido
  const validDomain: AlertCategory[] = [
    'attribute', 'timeline', 'relationship', 'location',
    'behavior', 'knowledge', 'style', 'grammar', 'structure', 'other'
  ]
  if (validDomain.includes(lower as AlertCategory)) {
    return lower as AlertCategory
  }

  // Mapear desde valores API
  return CATEGORY_MAP[lower as ApiAlertCategory] ?? 'other'
}

/** Obtiene el mensaje principal de una alerta (para compatibilidad) */
export function getAlertMessage(alert: Alert | ApiAlert): string {
  if ('description' in alert) {
    return alert.description || alert.title || ''
  }
  return ''
}

/** Obtiene la ubicación de una alerta */
export function getAlertLocation(alert: Alert | ApiAlert): {
  chapter?: number
  start?: number
  end?: number
} {
  // Check if it's a Domain Alert (has spanStart)
  if ('spanStart' in alert) {
    return {
      chapter: alert.chapter,
      start: alert.spanStart,
      end: alert.spanEnd,
    }
  }
  // It's an ApiAlert (has start_char)
  const apiAlert = alert as ApiAlert
  return {
    chapter: apiAlert.chapter ?? undefined,
    start: apiAlert.start_char ?? undefined,
    end: apiAlert.end_char ?? undefined,
  }
}
