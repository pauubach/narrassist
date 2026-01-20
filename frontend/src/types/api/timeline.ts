/**
 * API Types - Timeline
 *
 * Tipos que coinciden EXACTAMENTE con lo que devuelve el backend.
 * NO modificar sin actualizar el backend tambien.
 */

/** Resolucion temporal de un evento */
export type ApiTimelineResolution =
  | 'exact_date'
  | 'month'
  | 'year'
  | 'season'
  | 'relative'
  | 'unknown'

/** Orden narrativo del evento */
export type ApiNarrativeOrder =
  | 'chronological'
  | 'analepsis'
  | 'prolepsis'

/** Evento temporal de la API */
export interface ApiTimelineEvent {
  id: number
  description: string
  chapter: number
  paragraph: number
  story_date: string | null
  story_date_resolution: ApiTimelineResolution
  discourse_position: number
  narrative_order: ApiNarrativeOrder
  entity_ids: number[]
  confidence: number
}

/** Inconsistencia temporal de la API */
export interface ApiTemporalInconsistency {
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  chapter: number
  expected: string | null
  found: string | null
  suggestion: string | null
  confidence: number
}

/** Respuesta del endpoint de timeline */
export interface ApiTimelineResponse {
  events: ApiTimelineEvent[]
  markers_count: number
  anchor_count: number
  analepsis_count: number
  prolepsis_count: number
  time_span: {
    start: string
    end: string
  } | null
  mermaid: string
  inconsistencies: ApiTemporalInconsistency[]
}
