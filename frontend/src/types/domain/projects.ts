/**
 * Domain Types - Proyectos
 *
 * Tipos para proyectos y capítulos en la UI.
 */

import type { AlertSeverity } from './alerts'

/** Estado del análisis */
export type AnalysisStatus = 'pending' | 'in_progress' | 'analyzing' | 'queued' | 'completed' | 'error' | 'failed'

/** Tipos de documento detectados */
export type DocumentType =
  | 'fiction'      // Novela, cuento, relato
  | 'essay'        // Ensayo, artículo de opinión
  | 'self_help'    // Autoayuda, desarrollo personal
  | 'technical'    // Manual técnico, documentación
  | 'memoir'       // Memorias, autobiografía
  | 'biography'    // Biografías de terceros
  | 'celebrity'    // Libros de famosos/influencers
  | 'divulgation'  // Divulgación científica/histórica
  | 'practical'    // Cocina, jardinería, DIY, guías
  | 'children'     // Infantil/juvenil
  | 'drama'        // Teatro, guiones cine/TV
  | 'graphic'      // Novela gráfica, cómic, manga
  | 'cookbook'     // (legacy) -> practical
  | 'academic'     // (legacy) -> essay
  | 'unknown'      // No clasificado

/** Clasificación del documento */
export interface DocumentClassification {
  type: DocumentType
  confidence: number
  indicators: string[]
}

/** Configuración de análisis recomendada según tipo de documento */
export interface RecommendedAnalysis {
  entity_detection: {
    focus: string
    detect_implicit: boolean
    min_mentions_for_entity: number
  }
  semantic_fusion: {
    threshold: number
    allow_cross_type: boolean
  }
  analysis: {
    temporal_analysis: boolean
    relationship_detection: boolean
    behavior_consistency?: boolean
    dialog_analysis?: boolean
    concept_tracking?: boolean
    argument_tracking?: boolean
    terminology_consistency?: boolean
    ingredient_tracking?: boolean
  }
  alerts: Record<string, boolean>
}

/** Proyecto para uso en componentes */
export interface Project {
  id: number
  name: string
  description?: string
  documentPath?: string
  /** @deprecated Use documentPath instead */
  source_path?: string
  documentFormat: string
  createdAt: Date
  lastModified: Date
  lastOpened?: Date
  analysisStatus: AnalysisStatus
  analysisProgress: number
  wordCount: number
  chapterCount: number
  entityCount: number
  openAlertsCount: number
  highestAlertSeverity?: AlertSeverity
  /** Tipo de documento detectado (fiction, essay, self_help, etc.) */
  documentType?: DocumentType
  /** Clasificación detallada del documento */
  documentClassification?: DocumentClassification
  /** Configuración de análisis recomendada según el tipo de documento */
  recommendedAnalysis?: RecommendedAnalysis
}

/** Sección dentro de un capítulo (H2, H3, H4) */
export interface Section {
  id: number
  projectId: number
  chapterId: number
  parentSectionId: number | null
  sectionNumber: number
  title: string | null
  headingLevel: number  // 2=H2, 3=H3, 4=H4
  startChar: number
  endChar: number
  subsections: Section[]
}

/** Capítulo para uso en componentes */
export interface Chapter {
  id: number
  projectId: number
  title: string
  content: string
  chapterNumber: number
  wordCount: number
  positionStart: number
  positionEnd: number
  structureType?: string
  createdAt?: Date
  updatedAt?: Date
  sections?: Section[]
}
