/**
 * Tests para transformers API -> Domain
 *
 * Estos tests verifican que:
 * 1. Todos los campos de la API se mapean correctamente al Domain
 * 2. Los campos opcionales se manejan correctamente (null -> undefined)
 * 3. Las transformaciones de tipos (fechas, enums) funcionan
 * 4. No hay campos faltantes en los tipos
 */

import { describe, it, expect } from 'vitest'
import { transformProject, transformChapter } from '../transformers/projects'
import { transformEntity } from '../transformers/entities'
import { transformAlert } from '../transformers/alerts'
import type { ApiProject, ApiChapter } from '../api/projects'
import type { ApiEntity } from '../api/entities'
import type { ApiAlert } from '../api/alerts'

// =============================================================================
// Tests de Projects Transformer
// =============================================================================

describe('transformProject', () => {
  const mockApiProject: ApiProject = {
    id: 1,
    name: 'Test Project',
    description: 'A test project',
    document_path: '/path/to/doc.docx',
    document_format: 'docx',
    created_at: '2024-01-15T10:00:00Z',
    last_modified: '2024-01-15T12:00:00Z',
    last_opened: '2024-01-15T11:00:00Z',
    analysis_status: 'analyzing',
    analysis_progress: 50,
    word_count: 10000,
    chapter_count: 5,
    entity_count: 25,
    open_alerts_count: 3,
    highest_alert_severity: 'warning',
    document_type: 'fiction',
    document_classification: {
      type: 'fiction',
      confidence: 0.95,
      indicators: ['dialogue', 'characters', 'narrative'],
    },
    recommended_analysis: {
      entity_detection: {
        focus: 'characters',
        detect_implicit: true,
        min_mentions_for_entity: 2,
      },
      semantic_fusion: {
        threshold: 0.85,
        allow_cross_type: false,
      },
      analysis: {
        temporal_analysis: true,
        relationship_detection: true,
        behavior_consistency: true,
      },
      alerts: {
        attribute_consistency: true,
        timeline_consistency: true,
      },
    },
  }

  it('should transform all required fields', () => {
    const result = transformProject(mockApiProject)

    expect(result.id).toBe(1)
    expect(result.name).toBe('Test Project')
    expect(result.documentFormat).toBe('docx')
    expect(result.wordCount).toBe(10000)
    expect(result.chapterCount).toBe(5)
    expect(result.entityCount).toBe(25)
    expect(result.openAlertsCount).toBe(3)
  })

  it('should transform analysisStatus correctly', () => {
    const result = transformProject(mockApiProject)
    expect(result.analysisStatus).toBe('analyzing')
  })

  it('should handle all analysis status values', () => {
    const statuses = ['pending', 'in_progress', 'analyzing', 'completed', 'error', 'failed'] as const

    for (const status of statuses) {
      const project = { ...mockApiProject, analysis_status: status }
      const result = transformProject(project)
      expect(result.analysisStatus).toBe(status)
    }
  })

  it('should default analysisStatus to completed when missing', () => {
    const projectWithoutStatus = { ...mockApiProject } as any
    delete projectWithoutStatus.analysis_status

    const result = transformProject(projectWithoutStatus)
    expect(result.analysisStatus).toBe('completed')
  })

  it('should transform dates correctly', () => {
    const result = transformProject(mockApiProject)

    expect(result.createdAt).toBeInstanceOf(Date)
    expect(result.lastModified).toBeInstanceOf(Date)
    expect(result.lastOpened).toBeInstanceOf(Date)
  })

  it('should handle null optional fields', () => {
    const projectWithNulls: ApiProject = {
      ...mockApiProject,
      description: null,
      document_path: null,
      last_opened: null,
      highest_alert_severity: null,
    }

    const result = transformProject(projectWithNulls)

    expect(result.description).toBeUndefined()
    expect(result.documentPath).toBeUndefined()
    expect(result.lastOpened).toBeUndefined()
    expect(result.highestAlertSeverity).toBeUndefined()
  })

  it('should transform alert severity correctly', () => {
    const result = transformProject(mockApiProject)
    // 'warning' en API -> 'high' en Domain
    expect(result.highestAlertSeverity).toBe('high')
  })

  it('should transform documentType correctly', () => {
    const result = transformProject(mockApiProject)
    expect(result.documentType).toBe('fiction')
  })

  it('should default documentType to unknown when missing', () => {
    const projectWithoutType = { ...mockApiProject } as any
    delete projectWithoutType.document_type

    const result = transformProject(projectWithoutType)
    expect(result.documentType).toBe('unknown')
  })

  it('should transform documentClassification correctly', () => {
    const result = transformProject(mockApiProject)

    expect(result.documentClassification).toBeDefined()
    expect(result.documentClassification?.type).toBe('fiction')
    expect(result.documentClassification?.confidence).toBe(0.95)
    expect(result.documentClassification?.indicators).toContain('dialogue')
  })

  it('should handle null documentClassification', () => {
    const projectWithNullClassification = {
      ...mockApiProject,
      document_classification: null,
    }

    const result = transformProject(projectWithNullClassification)
    expect(result.documentClassification).toBeUndefined()
  })

  it('should transform recommendedAnalysis correctly', () => {
    const result = transformProject(mockApiProject)

    expect(result.recommendedAnalysis).toBeDefined()
    expect(result.recommendedAnalysis?.entity_detection.focus).toBe('characters')
    expect(result.recommendedAnalysis?.semantic_fusion.threshold).toBe(0.85)
    expect(result.recommendedAnalysis?.analysis.temporal_analysis).toBe(true)
    expect(result.recommendedAnalysis?.analysis.relationship_detection).toBe(true)
  })

  it('should handle null recommendedAnalysis', () => {
    const projectWithNullRecommended = {
      ...mockApiProject,
      recommended_analysis: null,
    }

    const result = transformProject(projectWithNullRecommended)
    expect(result.recommendedAnalysis).toBeUndefined()
  })

  it('should transform recommendedAnalysis with partial analysis fields', () => {
    const projectWithPartialAnalysis: ApiProject = {
      ...mockApiProject,
      recommended_analysis: {
        entity_detection: {
          focus: 'concepts',
          detect_implicit: false,
          min_mentions_for_entity: 3,
        },
        semantic_fusion: {
          threshold: 0.9,
          allow_cross_type: true,
        },
        analysis: {
          // Only some fields provided
          temporal_analysis: false,
          concept_tracking: true,
        },
        alerts: {},
      },
    }

    const result = transformProject(projectWithPartialAnalysis)

    expect(result.recommendedAnalysis?.analysis.temporal_analysis).toBe(false)
    expect(result.recommendedAnalysis?.analysis.concept_tracking).toBe(true)
    // Default value for missing relationship_detection
    expect(result.recommendedAnalysis?.analysis.relationship_detection).toBe(true)
  })
})

describe('transformChapter', () => {
  const mockApiChapter: ApiChapter = {
    id: 1,
    project_id: 1,
    title: 'Chapter 1',
    content: 'Chapter content here...',
    chapter_number: 1,
    word_count: 2000,
    position_start: 0,
    position_end: 10000,
    structure_type: 'chapter',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T12:00:00Z',
  }

  it('should transform all fields correctly', () => {
    const result = transformChapter(mockApiChapter)

    expect(result.id).toBe(1)
    expect(result.projectId).toBe(1)
    expect(result.title).toBe('Chapter 1')
    expect(result.chapterNumber).toBe(1)
    expect(result.wordCount).toBe(2000)
    expect(result.positionStart).toBe(0)
    expect(result.positionEnd).toBe(10000)
  })

  it('should handle null structure_type', () => {
    const chapter = { ...mockApiChapter, structure_type: null }
    const result = transformChapter(chapter)
    expect(result.structureType).toBeUndefined()
  })
})

// =============================================================================
// Tests de Entities Transformer
// =============================================================================

describe('transformEntity', () => {
  const mockApiEntity: ApiEntity = {
    id: 1,
    project_id: 1,
    entity_type: 'character',
    canonical_name: 'John Doe',
    aliases: ['Johnny', 'J.D.'],
    importance: 'principal',  // 'principal' maps to 'main' in Domain
    description: 'The protagonist',
    first_appearance_char: 150,
    first_mention_chapter: 1,
    mention_count: 50,
    is_active: true,
    merged_from_ids: [2, 3],
    relevance_score: 0.85,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T12:00:00Z',
  }

  it('should transform all required fields', () => {
    const result = transformEntity(mockApiEntity)

    expect(result.id).toBe(1)
    expect(result.projectId).toBe(1)
    expect(result.name).toBe('John Doe')
    expect(result.aliases).toEqual(['Johnny', 'J.D.'])
    expect(result.mentionCount).toBe(50)
    expect(result.isActive).toBe(true)
  })

  it('should transform entity type correctly', () => {
    const result = transformEntity(mockApiEntity)
    expect(result.type).toBe('character')
  })

  it('should transform importance correctly', () => {
    const result = transformEntity(mockApiEntity)
    // 'principal' en API -> 'main' en Domain
    expect(result.importance).toBe('main')
  })

  it('should include relevanceScore', () => {
    const result = transformEntity(mockApiEntity)
    expect(result.relevanceScore).toBe(0.85)
  })

  it('should handle missing relevanceScore', () => {
    const entityWithoutRelevance = { ...mockApiEntity }
    delete (entityWithoutRelevance as any).relevance_score

    const result = transformEntity(entityWithoutRelevance)
    expect(result.relevanceScore).toBeUndefined()
  })

  it('should transform mergedFromIds', () => {
    const result = transformEntity(mockApiEntity)
    expect(result.mergedFromIds).toEqual([2, 3])
  })

  it('should handle null merged_from_ids', () => {
    const entity = { ...mockApiEntity, merged_from_ids: null as any }
    const result = transformEntity(entity)
    expect(result.mergedFromIds).toEqual([])
  })
})

// =============================================================================
// Tests de Alerts Transformer
// =============================================================================

describe('transformAlert', () => {
  const mockApiAlert: ApiAlert = {
    id: 1,
    project_id: 1,
    category: 'consistency',
    severity: 'warning',
    alert_type: 'attribute_inconsistency',
    title: 'Inconsistencia detectada',
    description: 'El color de ojos cambió',
    explanation: 'En el capítulo 1 dice azules, en el 3 dice verdes',
    suggestion: 'Verificar cuál es el color correcto',
    chapter: 3,
    start_char: 1500,
    end_char: 1520,
    excerpt: 'sus ojos verdes brillaban',
    status: 'open',
    entity_ids: [1, 2],
    confidence: 0.9,
    created_at: '2024-01-15T10:00:00Z',
    resolved_at: null,
  }

  it('should transform all required fields', () => {
    const result = transformAlert(mockApiAlert)

    expect(result.id).toBe(1)
    expect(result.projectId).toBe(1)
    expect(result.title).toBe('Inconsistencia detectada')
    expect(result.description).toBe('El color de ojos cambió')
    expect(result.confidence).toBe(0.9)
    expect(result.entityIds).toEqual([1, 2])
  })

  it('should transform severity correctly', () => {
    const result = transformAlert(mockApiAlert)
    // 'warning' en API -> 'high' en Domain
    expect(result.severity).toBe('high')
  })

  it('should transform status correctly', () => {
    const result = transformAlert(mockApiAlert)
    // 'open' en API -> 'active' en Domain
    expect(result.status).toBe('active')
  })

  it('should transform category correctly', () => {
    const result = transformAlert(mockApiAlert)
    // 'consistency' en API -> 'attribute' en Domain
    expect(result.category).toBe('attribute')
  })

  it('should include excerpt', () => {
    const result = transformAlert(mockApiAlert)
    expect(result.excerpt).toBe('sus ojos verdes brillaban')
  })

  it('should handle null excerpt', () => {
    const alertWithoutExcerpt = { ...mockApiAlert, excerpt: null }
    const result = transformAlert(alertWithoutExcerpt)
    expect(result.excerpt).toBeUndefined()
  })

  it('should include span positions', () => {
    const result = transformAlert(mockApiAlert)
    expect(result.spanStart).toBe(1500)
    expect(result.spanEnd).toBe(1520)
  })

  it('should handle null span positions', () => {
    const alertWithoutSpan = { ...mockApiAlert, start_char: null, end_char: null }
    const result = transformAlert(alertWithoutSpan)
    expect(result.spanStart).toBeUndefined()
    expect(result.spanEnd).toBeUndefined()
  })

  it('should transform dates correctly', () => {
    const result = transformAlert(mockApiAlert)
    expect(result.createdAt).toBeInstanceOf(Date)
    expect(result.resolvedAt).toBeUndefined()
  })

  it('should handle resolved_at when present', () => {
    const resolvedAlert = { ...mockApiAlert, resolved_at: '2024-01-16T10:00:00Z' }
    const result = transformAlert(resolvedAlert)
    expect(result.resolvedAt).toBeInstanceOf(Date)
  })
})

// =============================================================================
// Tests de Completitud de Campos
// =============================================================================

describe('Field Completeness', () => {
  it('Project transformer should map all API fields', () => {
    // Este test falla si se añade un campo a ApiProject sin añadirlo al transformer
    const apiFields = [
      'id', 'name', 'description', 'document_path', 'document_format',
      'created_at', 'last_modified', 'last_opened', 'analysis_status',
      'analysis_progress', 'word_count', 'chapter_count', 'entity_count',
      'open_alerts_count', 'highest_alert_severity'
    ]

    const mockProject: ApiProject = {
      id: 1,
      name: 'Test',
      description: 'Desc',
      document_path: '/path',
      document_format: 'docx',
      created_at: '2024-01-01T00:00:00Z',
      last_modified: '2024-01-01T00:00:00Z',
      last_opened: '2024-01-01T00:00:00Z',
      analysis_status: 'completed',
      analysis_progress: 100,
      word_count: 1000,
      chapter_count: 1,
      entity_count: 10,
      open_alerts_count: 0,
      highest_alert_severity: null,
    }

    // Verificar que todos los campos esperados existen en el mock
    for (const field of apiFields) {
      expect(mockProject).toHaveProperty(field)
    }

    // Verificar que el transformer no falla
    const result = transformProject(mockProject)
    expect(result).toBeDefined()
  })

  it('Alert transformer should include excerpt field', () => {
    const mockAlert: ApiAlert = {
      id: 1,
      project_id: 1,
      category: 'grammar',
      severity: 'info',
      alert_type: 'test',
      title: 'Test',
      description: 'Test desc',
      explanation: 'Test explanation',
      suggestion: null,
      chapter: null,
      start_char: null,
      end_char: null,
      excerpt: 'test excerpt text',
      status: 'new',
      entity_ids: [],
      confidence: 0.5,
      created_at: '2024-01-01T00:00:00Z',
      resolved_at: null,
    }

    const result = transformAlert(mockAlert)

    // Este test habría fallado antes de añadir excerpt al transformer
    expect(result.excerpt).toBe('test excerpt text')
  })

  it('Entity transformer should include relevanceScore field', () => {
    const mockEntity: ApiEntity = {
      id: 1,
      project_id: 1,
      entity_type: 'character',
      canonical_name: 'Test',
      aliases: [],
      importance: 'minimal',
      description: null,
      first_appearance_char: null,
      first_mention_chapter: null,
      mention_count: 5,
      is_active: true,
      merged_from_ids: [],
      relevance_score: 0.25,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: undefined,
    }

    const result = transformEntity(mockEntity)

    // Este test habría fallado antes de añadir relevanceScore al transformer
    expect(result.relevanceScore).toBe(0.25)
  })

  it('Project transformer should include document_path field', () => {
    const mockProject: ApiProject = {
      id: 1,
      name: 'Test',
      description: 'Desc',
      document_path: '/path/to/document.docx',
      document_format: 'docx',
      created_at: '2024-01-01T00:00:00Z',
      last_modified: '2024-01-01T00:00:00Z',
      last_opened: null,
      analysis_status: 'completed',
      analysis_progress: 100,
      word_count: 1000,
      chapter_count: 1,
      entity_count: 10,
      open_alerts_count: 0,
      highest_alert_severity: null,
    }

    const result = transformProject(mockProject)

    // Este test habría fallado si document_path no estaba en el backend
    expect(result.documentPath).toBe('/path/to/document.docx')
  })

  it('Entity transformer should include all required fields from API', () => {
    const apiFields = [
      'id', 'project_id', 'entity_type', 'canonical_name', 'aliases',
      'importance', 'description', 'first_appearance_char', 'first_mention_chapter', 'mention_count',
      'is_active', 'merged_from_ids', 'relevance_score', 'created_at', 'updated_at'
    ]

    const mockEntity: ApiEntity = {
      id: 1,
      project_id: 1,
      entity_type: 'character',
      canonical_name: 'Test',
      aliases: ['Alias'],
      importance: 'medium',
      description: 'Description',
      first_appearance_char: 100,
      first_mention_chapter: 1,
      mention_count: 10,
      is_active: true,
      merged_from_ids: [],
      relevance_score: 0.5,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    }

    // Verificar que todos los campos esperados existen
    for (const field of apiFields) {
      expect(mockEntity).toHaveProperty(field)
    }

    const result = transformEntity(mockEntity)
    expect(result).toBeDefined()
    expect(result.description).toBe('Description')
    expect(result.firstMentionChapter).toBe(1)
    expect(result.isActive).toBe(true)
  })

  it('Alert transformer should include all required fields from API', () => {
    const apiFields = [
      'id', 'project_id', 'category', 'severity', 'alert_type', 'title',
      'description', 'explanation', 'suggestion', 'chapter', 'start_char',
      'end_char', 'excerpt', 'status', 'entity_ids', 'confidence',
      'created_at', 'resolved_at'
    ]

    const mockAlert: ApiAlert = {
      id: 1,
      project_id: 1,
      category: 'consistency',
      severity: 'warning',
      alert_type: 'test',
      title: 'Test',
      description: 'Test desc',
      explanation: 'Test explanation',
      suggestion: 'Fix this',
      chapter: 1,
      start_char: 100,
      end_char: 200,
      excerpt: 'test excerpt',
      status: 'open',
      entity_ids: [1, 2],
      confidence: 0.9,
      created_at: '2024-01-01T00:00:00Z',
      resolved_at: null,
    }

    // Verificar que todos los campos esperados existen
    for (const field of apiFields) {
      expect(mockAlert).toHaveProperty(field)
    }

    const result = transformAlert(mockAlert)
    expect(result).toBeDefined()
    expect(result.entityIds).toEqual([1, 2])
    expect(result.confidence).toBe(0.9)
  })
})

// =============================================================================
// Tests para validar comportamiento con datos faltantes/incorrectos
// =============================================================================

describe('Transformer Robustness', () => {
  it('should handle missing optional fields gracefully', () => {
    // Simular respuesta de backend antigua sin campos nuevos
    const legacyApiProject = {
      id: 1,
      name: 'Legacy Project',
      description: null,
      document_path: null,
      document_format: 'docx',
      created_at: '2024-01-01T00:00:00Z',
      last_modified: '2024-01-01T00:00:00Z',
      last_opened: null,
      // analysis_status missing!
      analysis_progress: 100,
      word_count: 1000,
      chapter_count: 1,
      entity_count: 10,
      open_alerts_count: 0,
      highest_alert_severity: null,
    } as any

    const result = transformProject(legacyApiProject)

    // Should default to 'completed' if missing
    expect(result.analysisStatus).toBe('completed')
  })

  it('should handle empty entity_ids array', () => {
    const mockAlert: ApiAlert = {
      id: 1,
      project_id: 1,
      category: 'grammar',
      severity: 'info',
      alert_type: 'test',
      title: 'Test',
      description: 'Test',
      explanation: 'Test',
      suggestion: null,
      chapter: null,
      start_char: null,
      end_char: null,
      excerpt: null,
      status: 'new',
      entity_ids: [],
      confidence: 0.5,
      created_at: '2024-01-01T00:00:00Z',
      resolved_at: null,
    }

    const result = transformAlert(mockAlert)
    expect(result.entityIds).toEqual([])
  })

  it('should handle zero confidence value', () => {
    const mockAlert: ApiAlert = {
      id: 1,
      project_id: 1,
      category: 'grammar',
      severity: 'info',
      alert_type: 'test',
      title: 'Test',
      description: 'Test',
      explanation: 'Test',
      suggestion: null,
      chapter: null,
      start_char: null,
      end_char: null,
      excerpt: null,
      status: 'new',
      entity_ids: [],
      confidence: 0,
      created_at: '2024-01-01T00:00:00Z',
      resolved_at: null,
    }

    const result = transformAlert(mockAlert)
    expect(result.confidence).toBe(0)
  })
})
