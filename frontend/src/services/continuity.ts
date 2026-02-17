/**
 * Servicio para análisis de continuidad de eventos.
 *
 * Wrapper del endpoint /api/projects/{project_id}/continuity
 */

import { api } from './apiClient'

export interface SourceEvent {
  event_type: string
  description: string
  confidence: number
  start_char: number
  end_char: number
  metadata: Record<string, any>
}

export interface ContinuityIssue {
  event_type: string
  paired_type: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  source_events: SourceEvent[]
  metadata: Record<string, any>
}

export interface ContinuityResponse {
  project_id: number
  total_chapters: number
  total_issues: number
  issues_by_severity: {
    critical: ContinuityIssue[]
    high: ContinuityIssue[]
    medium: ContinuityIssue[]
    low: ContinuityIssue[]
  }
  issues_by_type: Record<string, number>
}

/**
 * Obtiene análisis de continuidad de eventos de todo el proyecto.
 *
 * @param projectId - ID del proyecto
 * @returns Issues de continuidad agrupados por severidad
 */
export async function getProjectContinuity(
  projectId: number
): Promise<ContinuityResponse> {
  const response = await api.get(`/api/projects/${projectId}/continuity`)

  if (!response.data.success) {
    throw new Error(response.data.error || 'Error obteniendo análisis de continuidad')
  }

  return response.data.data as ContinuityResponse
}
