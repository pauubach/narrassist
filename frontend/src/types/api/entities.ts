/**
 * API Types - Entidades
 *
 * Tipos que coinciden EXACTAMENTE con lo que devuelve el backend.
 * NO modificar sin actualizar el backend también.
 */

/** Tipos de entidad del backend (lowercase) */
export type ApiEntityType =
  | 'character'
  | 'animal'
  | 'creature'
  | 'location'
  | 'building'
  | 'region'
  | 'object'
  | 'vehicle'
  | 'organization'
  | 'faction'
  | 'family'
  | 'event'
  | 'time_period'
  | 'concept'
  | 'religion'
  | 'magic_system'
  | 'work'
  | 'title'
  | 'language'
  | 'custom'

/** Importancia de entidad del backend */
export type ApiEntityImportance =
  | 'principal'
  | 'high'
  | 'medium'
  | 'low'
  | 'minimal'

/** Entidad tal como la devuelve la API */
export interface ApiEntity {
  id: number
  project_id: number
  entity_type: ApiEntityType
  canonical_name: string
  aliases: string[]
  importance: ApiEntityImportance
  description: string | null
  first_appearance_char: number | null
  first_mention_chapter: number | null
  mention_count: number
  is_active: boolean
  /** IDs de entidades fusionadas en esta */
  merged_from_ids: number[]
  /** Score de relevancia (0-1) basado en densidad de menciones */
  relevance_score?: number
  created_at?: string
  updated_at?: string
}

/** Registro de historial de fusiones de la API */
export interface ApiMergeHistoryEntry {
  id: number
  project_id: number
  result_entity_id: number
  result_entity_name?: string
  source_entity_ids: number[]
  source_entity_names?: string[]
  canonical_name_before?: string[]
  merged_at: string
  undone_at: string | null
  note: string | null
}

/** Atributo de entidad de la API */
export interface ApiEntityAttribute {
  id: number
  entity_id: number
  category: string
  name: string
  value: string
  chapter: string | null
  confidence: number
}

/** Mención de entidad de la API */
export interface ApiEntityMention {
  id: number
  entity_id: number
  chapter_id: number
  text: string
  span_start: number
  span_end: number
  confidence: number
}

/** Relación entre entidades de la API */
export interface ApiEntityRelationship {
  id: number
  source_entity_id: number
  target_entity_id: number
  relationship_type: string
  description: string | null
  bidirectional: boolean
  strength: number
}

/** Sugerencia de fusión de la API */
export interface ApiFusionSuggestion {
  id: number
  entity_a_id: number
  entity_b_id: number
  entity_a_name: string
  entity_b_name: string
  confidence: number
  reason: string
  status: 'pending' | 'accepted' | 'rejected'
}
