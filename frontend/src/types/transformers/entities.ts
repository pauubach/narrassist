/**
 * Transformers - Entidades
 *
 * Funciones para convertir entre tipos API y Domain.
 */

import type {
  ApiEntity,
  ApiEntityType,
  ApiEntityImportance,
  ApiEntityAttribute,
  ApiEntityMention,
  ApiEntityRelationship,
  ApiFusionSuggestion,
  ApiMergeHistoryEntry,
} from '../api/entities'

import type {
  Entity,
  EntityType,
  EntityImportance,
  EntityAttribute,
  EntityMention,
  EntityRelationship,
  FusionSuggestion,
  MergeHistoryEntry,
} from '../domain/entities'

// =============================================================================
// Mapeos de tipos
// =============================================================================

const ENTITY_TYPE_MAP: Record<ApiEntityType, EntityType> = {
  character: 'character',
  animal: 'character',
  creature: 'character',
  location: 'location',
  building: 'location',
  region: 'location',
  object: 'object',
  vehicle: 'object',
  organization: 'organization',
  faction: 'organization',
  family: 'organization',
  event: 'event',
  time_period: 'event',
  concept: 'concept',
  religion: 'concept',
  magic_system: 'concept',
  work: 'other',
  title: 'other',
  language: 'other',
  custom: 'other',
}

const IMPORTANCE_MAP: Record<ApiEntityImportance, EntityImportance> = {
  principal: 'main',
  high: 'main',
  medium: 'secondary',
  low: 'minor',
  minimal: 'minor',
}

// Mapeo inverso para enviar al backend
const ENTITY_TYPE_TO_API: Record<EntityType, ApiEntityType> = {
  character: 'character',
  location: 'location',
  object: 'object',
  organization: 'organization',
  event: 'event',
  concept: 'concept',
  other: 'custom',
}

const IMPORTANCE_TO_API: Record<EntityImportance, ApiEntityImportance> = {
  main: 'principal',
  secondary: 'medium',
  minor: 'low',
}

// =============================================================================
// Transformadores API -> Domain
// =============================================================================

/** Transforma EntityType de API a Domain */
export function transformEntityType(apiType: ApiEntityType): EntityType {
  return ENTITY_TYPE_MAP[apiType] ?? 'other'
}

/** Transforma EntityImportance de API a Domain */
export function transformEntityImportance(apiImportance: ApiEntityImportance): EntityImportance {
  return IMPORTANCE_MAP[apiImportance] ?? 'secondary'
}

/** Transforma una entidad de API a Domain */
export function transformEntity(api: ApiEntity): Entity {
  return {
    id: api.id,
    projectId: api.project_id,
    type: transformEntityType(api.entity_type),
    name: api.canonical_name,
    aliases: api.aliases,
    importance: transformEntityImportance(api.importance),
    description: api.description ?? undefined,
    firstMentionChapter: api.first_mention_chapter ?? undefined,
    mentionCount: api.mention_count,
    isActive: api.is_active,
    mergedFromIds: api.merged_from_ids ?? [],
    relevanceScore: api.relevance_score ?? undefined,
    createdAt: api.created_at ? new Date(api.created_at) : undefined,
    updatedAt: api.updated_at ? new Date(api.updated_at) : undefined,
  }
}

/** Transforma un array de entidades */
export function transformEntities(apiEntities: ApiEntity[]): Entity[] {
  return apiEntities.map(transformEntity)
}

/** Transforma un atributo de entidad */
export function transformEntityAttribute(api: ApiEntityAttribute): EntityAttribute {
  return {
    id: api.id,
    entityId: api.entity_id,
    category: api.category,
    name: api.name,
    value: api.value,
    chapter: api.chapter ? parseInt(api.chapter, 10) : undefined,
    confidence: api.confidence,
  }
}

/** Transforma una mención de entidad */
export function transformEntityMention(api: ApiEntityMention): EntityMention {
  return {
    id: api.id,
    entityId: api.entity_id,
    chapterId: api.chapter_id,
    text: api.text,
    spanStart: api.span_start,
    spanEnd: api.span_end,
    confidence: api.confidence,
  }
}

/** Transforma una relación entre entidades */
export function transformEntityRelationship(api: ApiEntityRelationship): EntityRelationship {
  return {
    id: api.id,
    sourceEntityId: api.source_entity_id,
    targetEntityId: api.target_entity_id,
    relationshipType: api.relationship_type,
    description: api.description ?? undefined,
    bidirectional: api.bidirectional,
    strength: api.strength,
  }
}

/** Transforma una sugerencia de fusión */
export function transformFusionSuggestion(api: ApiFusionSuggestion): FusionSuggestion {
  return {
    id: api.id,
    entityAId: api.entity_a_id,
    entityBId: api.entity_b_id,
    entityAName: api.entity_a_name,
    entityBName: api.entity_b_name,
    confidence: api.confidence,
    reason: api.reason,
    status: api.status,
  }
}

// =============================================================================
// Transformadores Domain -> API
// =============================================================================

/** Transforma EntityType de Domain a API */
export function entityTypeToApi(type: EntityType): ApiEntityType {
  return ENTITY_TYPE_TO_API[type]
}

/** Transforma EntityImportance de Domain a API */
export function entityImportanceToApi(importance: EntityImportance): ApiEntityImportance {
  return IMPORTANCE_TO_API[importance]
}

/** Prepara una entidad para enviar a la API */
export function entityToApiPayload(entity: Partial<Entity>): Partial<ApiEntity> {
  const payload: Partial<ApiEntity> = {}

  if (entity.name !== undefined) payload.canonical_name = entity.name
  if (entity.type !== undefined) payload.entity_type = entityTypeToApi(entity.type)
  if (entity.importance !== undefined) payload.importance = entityImportanceToApi(entity.importance)
  if (entity.description !== undefined) payload.description = entity.description ?? null
  if (entity.aliases !== undefined) payload.aliases = entity.aliases

  return payload
}

// =============================================================================
// Helpers para compatibilidad con código legacy
// =============================================================================

/** Normaliza un tipo de entidad desde cualquier formato */
export function normalizeEntityType(type: string): EntityType {
  const lower = type.toLowerCase() as ApiEntityType
  return ENTITY_TYPE_MAP[lower] ?? 'other'
}

/** Normaliza una importancia desde cualquier formato */
export function normalizeEntityImportance(importance: string): EntityImportance {
  const lower = importance.toLowerCase()
  // Mapeo directo si ya es un valor domain
  if (lower === 'main' || lower === 'secondary' || lower === 'minor') {
    return lower as EntityImportance
  }
  // Mapeo desde valores API
  return IMPORTANCE_MAP[lower as ApiEntityImportance] ?? 'secondary'
}

// =============================================================================
// Transformadores para Historial de Fusiones
// =============================================================================

/** Transforma una entrada de historial de fusiones de API a Domain */
export function transformMergeHistoryEntry(api: ApiMergeHistoryEntry): MergeHistoryEntry {
  return {
    id: api.id,
    projectId: api.project_id,
    resultEntityId: api.result_entity_id,
    resultEntityName: api.result_entity_name ?? api.canonical_name_before?.[0] ?? 'Entidad fusionada',
    sourceEntityIds: api.source_entity_ids,
    sourceEntityNames: api.source_entity_names ?? api.canonical_name_before ?? [],
    mergedAt: new Date(api.merged_at),
    undoneAt: api.undone_at ? new Date(api.undone_at) : undefined,
    note: api.note ?? undefined,
  }
}

/** Transforma un array de entradas de historial de fusiones */
export function transformMergeHistory(apiEntries: ApiMergeHistoryEntry[]): MergeHistoryEntry[] {
  return apiEntries.map(transformMergeHistoryEntry)
}
