/**
 * Transformers - Timeline
 *
 * Funciones de conversion API <-> Domain para tipos de timeline.
 */

import type {
  ApiTimelineEvent,
  ApiTimelineResponse,
  ApiTemporalInconsistency
} from '../api/timeline'
import type {
  TimelineEvent,
  Timeline,
  TemporalInconsistency,
  TimeSpan
} from '../domain/timeline'

/**
 * Transforma un evento de timeline de la API al formato del dominio.
 */
export function transformTimelineEvent(apiEvent: ApiTimelineEvent): TimelineEvent {
  return {
    id: apiEvent.id,
    description: apiEvent.description,
    chapter: apiEvent.chapter,
    paragraph: apiEvent.paragraph,
    storyDate: apiEvent.story_date ? new Date(apiEvent.story_date) : null,
    storyDateResolution: apiEvent.story_date_resolution,
    dayOffset: apiEvent.day_offset ?? null,
    weekday: apiEvent.weekday ?? null,
    discoursePosition: apiEvent.discourse_position,
    narrativeOrder: apiEvent.narrative_order,
    entityIds: apiEvent.entity_ids || [],
    confidence: apiEvent.confidence
  }
}

/**
 * Transforma una inconsistencia temporal de la API al formato del dominio.
 */
export function transformInconsistency(apiInc: ApiTemporalInconsistency): TemporalInconsistency {
  return {
    type: apiInc.type,
    severity: apiInc.severity,
    description: apiInc.description,
    chapter: apiInc.chapter,
    expected: apiInc.expected || undefined,
    found: apiInc.found || undefined,
    suggestion: apiInc.suggestion || undefined,
    confidence: apiInc.confidence
  }
}

/**
 * Transforma la respuesta completa del timeline de la API al formato del dominio.
 */
export function transformTimeline(apiResponse: ApiTimelineResponse): Timeline {
  let timeSpan: TimeSpan | null = null
  if (apiResponse.time_span) {
    const ts = apiResponse.time_span
    timeSpan = {
      start: ts.start ? new Date(ts.start) : null,
      end: ts.end ? new Date(ts.end) : null,
      durationDays: ts.duration_days ?? 0,
      isSynthetic: ts.is_synthetic ?? false,
      hasRealDates: ts.has_real_dates ?? true
    }
  }

  return {
    events: (apiResponse.events || []).map(transformTimelineEvent),
    markersCount: apiResponse.markers_count || 0,
    anchorCount: apiResponse.anchor_count || 0,
    analepsiCount: apiResponse.analepsis_count || 0,
    prolepsiCount: apiResponse.prolepsis_count || 0,
    timeSpan,
    mermaid: apiResponse.mermaid || '',
    inconsistencies: (apiResponse.inconsistencies || []).map(transformInconsistency)
  }
}
