/**
 * Transformers - Proyectos
 *
 * Funciones para convertir entre tipos API y Domain.
 */

import type {
  ApiProject, ApiChapter, ApiSection, ApiRecommendedAnalysis,
  ApiVersionMetrics, ApiVersionTrend,
} from '../api/projects'
import type {
  Project, Chapter, Section, RecommendedAnalysis,
  VersionMetrics, VersionTrend,
} from '../domain/projects'
import { transformAlertSeverity } from './alerts'

// =============================================================================
// Helpers
// =============================================================================

/** Parsea una fecha de string, retorna fallback si es inválida */
export function safeDate(value: string | null | undefined, fallback?: Date): Date | undefined {
  if (!value) return fallback
  const d = new Date(value)
  if (isNaN(d.getTime())) return fallback
  return d
}

// =============================================================================
// Transformadores API -> Domain
// =============================================================================

/** Transforma la configuración de análisis recomendada */
function transformRecommendedAnalysis(api: ApiRecommendedAnalysis): RecommendedAnalysis {
  const analysis = api.analysis || {}
  return {
    entity_detection: api.entity_detection,
    semantic_fusion: api.semantic_fusion,
    analysis: {
      temporal_analysis: analysis.temporal_analysis ?? true,
      relationship_detection: analysis.relationship_detection ?? true,
      behavior_consistency: analysis.behavior_consistency,
      dialog_analysis: analysis.dialog_analysis,
      concept_tracking: analysis.concept_tracking,
      argument_tracking: analysis.argument_tracking,
      terminology_consistency: analysis.terminology_consistency,
      ingredient_tracking: analysis.ingredient_tracking,
    },
    alerts: api.alerts,
  }
}

/** Transforma un proyecto de API a Domain */
export function transformProject(api: ApiProject): Project {
  return {
    id: api.id,
    name: api.name,
    description: api.description ?? undefined,
    documentPath: api.document_path ?? undefined,
    documentFormat: api.document_format,
    createdAt: safeDate(api.created_at, new Date())!,
    lastModified: safeDate(api.last_modified, new Date())!,
    lastOpened: safeDate(api.last_opened),
    analysisStatus: api.analysis_status || 'completed',
    analysisProgress: api.analysis_progress,
    wordCount: api.word_count,
    chapterCount: api.chapter_count,
    entityCount: api.entity_count,
    openAlertsCount: api.open_alerts_count,
    highestAlertSeverity: api.highest_alert_severity
      ? transformAlertSeverity(api.highest_alert_severity)
      : undefined,
    // Tipo de documento detectado
    documentType: api.document_type ?? 'unknown',
    documentClassification: api.document_classification ?? undefined,
    recommendedAnalysis: api.recommended_analysis
      ? transformRecommendedAnalysis(api.recommended_analysis)
      : undefined,
  }
}

/** Transforma un array de proyectos */
export function transformProjects(apiProjects: ApiProject[]): Project[] {
  return apiProjects.map(transformProject)
}

/** Transforma una sección de API a Domain */
export function transformSection(api: ApiSection): Section {
  return {
    id: api.id,
    projectId: api.project_id,
    chapterId: api.chapter_id,
    parentSectionId: api.parent_section_id,
    sectionNumber: api.section_number,
    title: api.title,
    headingLevel: api.heading_level,
    startChar: api.start_char,
    endChar: api.end_char,
    subsections: api.subsections?.map(transformSection) || [],
  }
}

/** Transforma un capítulo de API a Domain */
export function transformChapter(api: ApiChapter): Chapter {
  return {
    id: api.id,
    projectId: api.project_id,
    title: api.title,
    content: api.content,
    chapterNumber: api.chapter_number,
    wordCount: api.word_count,
    positionStart: api.position_start,
    positionEnd: api.position_end,
    structureType: api.structure_type ?? undefined,
    createdAt: safeDate(api.created_at),
    updatedAt: safeDate(api.updated_at),
    sections: api.sections?.map(transformSection) || [],
  }
}

/** Transforma un array de capítulos */
export function transformChapters(apiChapters: ApiChapter[]): Chapter[] {
  return apiChapters.map(transformChapter)
}

// =============================================================================
// S15: Version tracking transformers
// =============================================================================

/** Transforma version metrics de API a Domain */
export function transformVersionMetrics(api: ApiVersionMetrics): VersionMetrics {
  return {
    id: api.id,
    projectId: api.project_id,
    versionNum: api.version_num,
    snapshotId: api.snapshot_id,
    alertCount: api.alert_count,
    wordCount: api.word_count,
    entityCount: api.entity_count,
    chapterCount: api.chapter_count,
    healthScore: api.health_score,
    formalityAvg: api.formality_avg,
    dialogueRatio: api.dialogue_ratio,
    alertsNewCount: api.alerts_new_count ?? 0,
    alertsResolvedCount: api.alerts_resolved_count ?? 0,
    alertsUnchangedCount: api.alerts_unchanged_count ?? 0,
    criticalCount: api.critical_count ?? 0,
    warningCount: api.warning_count ?? 0,
    infoCount: api.info_count ?? 0,
    entitiesNewCount: api.entities_new_count ?? 0,
    entitiesRemovedCount: api.entities_removed_count ?? 0,
    entitiesRenamedCount: api.entities_renamed_count ?? 0,
    chapterAddedCount: api.chapter_added_count ?? 0,
    chapterRemovedCount: api.chapter_removed_count ?? 0,
    chapterReorderedCount: api.chapter_reordered_count ?? 0,
    runMode: api.run_mode ?? 'full',
    durationTotalSec: api.duration_total_sec ?? 0,
    phaseDurationsJson: api.phase_durations_json ?? '{}',
    modifiedChapters: api.modified_chapters ?? 0,
    addedChapters: api.added_chapters ?? 0,
    removedChapters: api.removed_chapters ?? 0,
    chapterChangeRatio: api.chapter_change_ratio ?? 0,
    renamedEntities: api.renamed_entities ?? 0,
    newEntities: api.new_entities ?? 0,
    removedEntities: api.removed_entities ?? 0,
    topEntityRenames: (api.top_entity_renames ?? []).map(rename => ({
      oldName: rename.old_name,
      newName: rename.new_name,
      confidence: rename.confidence,
    })),
    createdAt: safeDate(api.created_at, new Date())!,
  }
}

/** Transforma version trend de API a Domain */
export function transformVersionTrend(api: ApiVersionTrend): VersionTrend {
  return {
    trend: api.trend.map(p => ({
      versionNum: p.version_num,
      alertCount: p.alert_count,
      healthScore: p.health_score,
      wordCount: p.word_count,
      alertsNewCount: p.alerts_new_count ?? 0,
      alertsResolvedCount: p.alerts_resolved_count ?? 0,
      runMode: p.run_mode ?? 'full',
      durationTotalSec: p.duration_total_sec ?? 0,
      createdAt: safeDate(p.created_at, new Date())!,
    })),
    delta: api.delta ? {
      alertCount: api.delta.alert_count,
      healthScore: api.delta.health_score,
      wordCount: api.delta.word_count,
    } : null,
  }
}
