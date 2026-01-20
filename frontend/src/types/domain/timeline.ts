/**
 * Domain Types - Timeline
 *
 * Tipos simplificados para uso interno en la UI.
 */

/** Resolucion temporal de un evento */
export type TimelineResolution =
  | 'exact_date'
  | 'month'
  | 'year'
  | 'season'
  | 'relative'
  | 'unknown'

/** Orden narrativo del evento */
export type NarrativeOrder =
  | 'chronological'
  | 'analepsis'
  | 'prolepsis'

/** Severidad de inconsistencia */
export type InconsistencySeverity = 'low' | 'medium' | 'high' | 'critical'

/** Evento en la linea temporal */
export interface TimelineEvent {
  id: number
  description: string
  chapter: number
  paragraph: number
  storyDate: Date | null
  storyDateResolution: TimelineResolution
  discoursePosition: number
  narrativeOrder: NarrativeOrder
  entityIds: number[]
  confidence: number
}

/** Inconsistencia temporal detectada */
export interface TemporalInconsistency {
  type: string
  severity: InconsistencySeverity
  description: string
  chapter: number
  expected?: string
  found?: string
  suggestion?: string
  confidence: number
}

/** Rango temporal de la historia */
export interface TimeSpan {
  start: Date
  end: Date
}

/** Timeline completo del proyecto */
export interface Timeline {
  events: TimelineEvent[]
  markersCount: number
  anchorCount: number
  analepsiCount: number
  prolepsiCount: number
  timeSpan: TimeSpan | null
  mermaid: string
  inconsistencies: TemporalInconsistency[]
}
