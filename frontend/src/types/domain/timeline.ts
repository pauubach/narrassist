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
  | 'partial'    // Fecha sin año (15 de marzo, martes)
  | 'relative'   // Día +N (offset desde referencia)
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
  // Para timelines sin fechas absolutas (Día 0, Día +1, etc.)
  dayOffset: number | null  // Offset en días desde el Día 0
  weekday: string | null    // Día de la semana si se menciona (lunes, martes, etc.)
  discoursePosition: number
  narrativeOrder: NarrativeOrder
  /** Instancia temporal para viajes en el tiempo (A@40 vs A@45) */
  temporalInstanceId: string | null
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
  start: Date | null          // null si fechas sintéticas
  end: Date | null            // null si fechas sintéticas
  durationDays: number        // duración en días
  isSynthetic: boolean        // true si no hay fechas absolutas en el texto
  hasRealDates: boolean       // true si hay fechas absolutas en el texto
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
  /** True si la respuesta fue truncada por límite de eventos */
  truncated: boolean
  /** Total de eventos sin truncar (solo informativo cuando truncated=true) */
  totalEvents: number
}
