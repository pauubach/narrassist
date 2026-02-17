/**
 * Servicio para detección de eventos narrativos.
 *
 * Wrapper del endpoint /api/projects/{project_id}/chapters/{chapter_number}/events
 */

import { api } from './apiClient'

export interface DetectedEvent {
  event_type: string
  description: string
  confidence: number
  start_char: number
  end_char: number
  entity_ids: number[]
  metadata: Record<string, any>
}

export interface ChapterEventsResponse {
  project_id: number
  chapter_number: number
  chapter_title: string | null
  total_events: number
  tier1_events: DetectedEvent[]
  tier2_events: DetectedEvent[]
  tier3_events: DetectedEvent[]
  events_by_type: Record<string, number>
}

/**
 * Obtiene eventos detectados en un capítulo.
 *
 * @param projectId - ID del proyecto
 * @param chapterNumber - Número de capítulo
 * @returns Eventos agrupados por tier
 */
export async function getChapterEvents(
  projectId: number,
  chapterNumber: number
): Promise<ChapterEventsResponse> {
  const response = await api.getRaw<ChapterEventsResponse>(
    `/api/projects/${projectId}/chapters/${chapterNumber}/events`
  )

  if (!response.success) {
    throw new Error(response.error || 'Error obteniendo eventos del capítulo')
  }

  return response.data as ChapterEventsResponse
}
