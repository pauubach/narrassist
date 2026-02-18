/**
 * Transformers - Collections / Cross-Book
 *
 * Funciones para convertir entre tipos API (snake_case) y Domain (camelCase).
 */

import type {
  ApiCollection, ApiCollectionDetail, ApiCollectionProject,
  ApiEntityLink, ApiLinkSuggestion,
  ApiCrossBookReport, ApiCrossBookInconsistency,
  ApiEventContradiction, ApiCrossBookEventReport,
} from '../api/collections'
import type {
  Collection, CollectionDetail, CollectionProject,
  EntityLink, LinkSuggestion,
  CrossBookReport, CrossBookInconsistency,
  EventContradiction, CrossBookEventReport,
} from '../domain/collections'
import { safeDate } from './projects'

export function transformCollection(api: ApiCollection): Collection {
  return {
    id: api.id,
    name: api.name,
    description: api.description,
    projectCount: api.project_count,
    createdAt: safeDate(api.created_at, new Date())!,
  }
}

export function transformCollections(apiList: ApiCollection[]): Collection[] {
  return apiList.map(transformCollection)
}

function transformCollectionProject(api: ApiCollectionProject): CollectionProject {
  return {
    id: api.id,
    name: api.name,
    orderIndex: api.order_index,
    wordCount: api.word_count,
    entityCount: api.entity_count,
    documentFormat: api.document_format,
  }
}

export function transformCollectionDetail(api: ApiCollectionDetail): CollectionDetail {
  return {
    id: api.id,
    name: api.name,
    description: api.description,
    projectCount: api.project_count,
    createdAt: safeDate(api.created_at, new Date())!,
    projects: (api.projects || []).map(transformCollectionProject),
    entityLinkCount: api.entity_link_count,
  }
}

export function transformEntityLink(api: ApiEntityLink): EntityLink {
  return {
    id: api.id,
    collectionId: api.collection_id,
    sourceEntityId: api.source_entity_id,
    targetEntityId: api.target_entity_id,
    sourceProjectId: api.source_project_id,
    targetProjectId: api.target_project_id,
    sourceEntityName: api.source_entity_name,
    targetEntityName: api.target_entity_name,
    sourceProjectName: api.source_project_name,
    targetProjectName: api.target_project_name,
    similarity: api.similarity,
    matchType: api.match_type,
  }
}

export function transformEntityLinks(apiList: ApiEntityLink[]): EntityLink[] {
  return apiList.map(transformEntityLink)
}

export function transformLinkSuggestion(api: ApiLinkSuggestion): LinkSuggestion {
  return {
    sourceEntityId: api.source_entity_id,
    sourceEntityName: api.source_entity_name,
    sourceEntityType: api.source_entity_type,
    sourceProjectId: api.source_project_id,
    sourceProjectName: api.source_project_name,
    targetEntityId: api.target_entity_id,
    targetEntityName: api.target_entity_name,
    targetEntityType: api.target_entity_type,
    targetProjectId: api.target_project_id,
    targetProjectName: api.target_project_name,
    similarity: api.similarity,
    matchType: api.match_type,
  }
}

export function transformLinkSuggestions(apiList: ApiLinkSuggestion[]): LinkSuggestion[] {
  return apiList.map(transformLinkSuggestion)
}

function transformInconsistency(api: ApiCrossBookInconsistency): CrossBookInconsistency {
  return {
    entityName: api.entity_name,
    attributeType: api.attribute_type,
    attributeKey: api.attribute_key,
    valueBookA: api.value_book_a,
    valueBookB: api.value_book_b,
    bookAName: api.book_a_name,
    bookBName: api.book_b_name,
    confidence: api.confidence,
  }
}

export function transformCrossBookReport(api: ApiCrossBookReport): CrossBookReport {
  return {
    collectionId: api.collection_id,
    collectionName: api.collection_name,
    inconsistencies: (api.inconsistencies || []).map(transformInconsistency),
    entityLinksAnalyzed: api.entity_links_analyzed,
    projectsAnalyzed: api.projects_analyzed,
    summary: {
      totalInconsistencies: api.summary.total_inconsistencies,
      byType: api.summary.by_type,
    },
  }
}

function transformEventContradiction(api: ApiEventContradiction): EventContradiction {
  return {
    rule: api.rule,
    entityName: api.entity_name,
    description: api.description,
    eventAType: api.event_a_type,
    eventBType: api.event_b_type,
    bookAName: api.book_a_name,
    bookBName: api.book_b_name,
    bookAChapter: api.book_a_chapter,
    bookBChapter: api.book_b_chapter,
    confidence: api.confidence,
    metadata: api.metadata || {},
  }
}

export function transformCrossBookEventReport(api: ApiCrossBookEventReport): CrossBookEventReport {
  return {
    collectionId: api.collection_id,
    collectionName: api.collection_name,
    contradictions: (api.contradictions || []).map(transformEventContradiction),
    entityLinksAnalyzed: api.entity_links_analyzed,
    projectsAnalyzed: api.projects_analyzed,
    summary: {
      totalContradictions: api.summary.total_contradictions,
      byRule: api.summary.by_rule,
    },
  }
}
