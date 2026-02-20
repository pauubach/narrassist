/**
 * API Types - Proyectos
 *
 * Tipos que coinciden EXACTAMENTE con lo que devuelve el backend.
 */

import type { ApiAlertSeverity } from './alerts'

/** Estado del análisis en la API */
export type ApiAnalysisStatus = 'pending' | 'in_progress' | 'analyzing' | 'completed' | 'error' | 'failed'

/** Tipo de documento en la API */
export type ApiDocumentType =
  | 'fiction'
  | 'essay'
  | 'self_help'
  | 'technical'
  | 'memoir'
  | 'cookbook'
  | 'academic'
  | 'unknown'

/** Clasificación de documento de la API */
export interface ApiDocumentClassification {
  type: ApiDocumentType
  confidence: number
  indicators: string[]
}

/** Configuración de análisis recomendada */
export interface ApiRecommendedAnalysis {
  entity_detection: {
    focus: string
    detect_implicit: boolean
    min_mentions_for_entity: number
  }
  semantic_fusion: {
    threshold: number
    allow_cross_type: boolean
  }
  analysis: Record<string, boolean>
  alerts: Record<string, boolean>
}

/** Proyecto tal como lo devuelve la API */
export interface ApiProject {
  id: number
  name: string
  description: string | null
  document_path: string | null
  document_format: string
  created_at: string | null
  last_modified: string | null
  last_opened: string | null
  analysis_status: ApiAnalysisStatus
  analysis_progress: number
  word_count: number
  chapter_count: number
  entity_count: number
  open_alerts_count: number
  highest_alert_severity: ApiAlertSeverity | null
  /** Tipo de documento detectado */
  document_type?: ApiDocumentType
  /** Clasificación detallada del documento */
  document_classification?: ApiDocumentClassification | null
  /** Configuración de análisis recomendada */
  recommended_analysis?: ApiRecommendedAnalysis | null
}

/** Versión con métricas tal como la devuelve la API (S15, BK-28) */
export interface ApiVersionMetrics {
  id: number
  project_id: number
  version_num: number
  snapshot_id: number | null
  alert_count: number
  word_count: number
  entity_count: number
  chapter_count: number
  health_score: number | null
  formality_avg: number | null
  dialogue_ratio: number | null
  alerts_new_count?: number
  alerts_resolved_count?: number
  alerts_unchanged_count?: number
  critical_count?: number
  warning_count?: number
  info_count?: number
  entities_new_count?: number
  entities_removed_count?: number
  entities_renamed_count?: number
  chapter_added_count?: number
  chapter_removed_count?: number
  chapter_reordered_count?: number
  run_mode?: 'fast_path' | 'incremental' | 'full' | string
  duration_total_sec?: number
  phase_durations_json?: string
  modified_chapters?: number
  added_chapters?: number
  removed_chapters?: number
  chapter_change_ratio?: number
  renamed_entities?: number
  new_entities?: number
  removed_entities?: number
  top_entity_renames?: Array<{
    old_name: string
    new_name: string
    confidence: number
  }>
  created_at: string
}

/** Punto de trend para sparkline (S15) */
export interface ApiVersionTrendPoint {
  version_num: number
  alert_count: number
  health_score: number | null
  word_count: number
  alerts_new_count?: number
  alerts_resolved_count?: number
  run_mode?: 'fast_path' | 'incremental' | 'full' | string
  duration_total_sec?: number
  created_at: string
}

/** Delta entre últimas 2 versiones (S15) */
export interface ApiVersionDelta {
  alert_count: number
  health_score: number | null
  word_count: number
}

/** Respuesta del endpoint /versions/trend (S15) */
export interface ApiVersionTrend {
  trend: ApiVersionTrendPoint[]
  delta: ApiVersionDelta | null
}

/** Sección tal como la devuelve la API */
export interface ApiSection {
  id: number
  project_id: number
  chapter_id: number
  parent_section_id: number | null
  section_number: number
  title: string | null
  heading_level: number
  start_char: number
  end_char: number
  subsections: ApiSection[]
}

/** Capítulo tal como lo devuelve la API */
export interface ApiChapter {
  id: number
  project_id: number
  title: string
  content: string
  chapter_number: number
  word_count: number
  position_start: number
  position_end: number
  structure_type: string | null
  created_at?: string
  updated_at?: string
  sections?: ApiSection[]
}
