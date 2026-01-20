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
  created_at: string
  last_modified: string
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
