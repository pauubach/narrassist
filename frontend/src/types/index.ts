/**
 * Tipos del Frontend - Punto de entrada único
 *
 * ARQUITECTURA DE TIPOS:
 * - api/     : Tipos exactos del backend (snake_case, no modificar sin sync con backend)
 * - domain/  : Tipos simplificados para la UI (camelCase)
 * - transformers/ : Funciones de conversión API <-> Domain
 *
 * USO:
 * - Componentes: import type { Entity, Alert, Project } from '@/types'
 * - Stores/fetch: import type { ApiEntity } from '@/types/api'
 * - Transformar: import { transformEntity } from '@/types/transformers'
 */

// =============================================================================
// Domain Types (exports principales para componentes)
// =============================================================================

export * from './domain/entities'
export * from './domain/alerts'
export * from './domain/projects'
export * from './domain/theme'
export * from './domain/timeline'
export * from './domain/chat'
export * from './domain/corrections'

// =============================================================================
// API Types (namespace para claridad)
// =============================================================================

export * as Api from './api'

// =============================================================================
// Transformers
// =============================================================================

export * from './transformers'

// =============================================================================
// API Response (común)
// =============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// =============================================================================
// Character types (para CharacterSheet y CharacterView)
// =============================================================================

export interface CharacterAttribute {
  id?: number
  entityId: number
  category: string
  name: string
  value: string
  firstMentionChapter?: number
  confidence?: number
}

export interface CharacterRelationship {
  id?: number
  entityId: number
  relatedEntityId: number
  relatedEntityName?: string
  relationshipType: string
  description?: string
}

export interface CharacterSheet {
  entityId: number
  name: string
  aliases: string[]
  importance: string
  attributes: CharacterAttribute[]
  relationships?: CharacterRelationship[]
  firstMentionChapter?: number
  mentionCount: number
}

// =============================================================================
// Relationship types
// =============================================================================

export type RelationshipType =
  | 'family'
  | 'romantic'
  | 'friendship'
  | 'professional'
  | 'rival'
  | 'enemy'
  | 'mentor'
  | 'student'
  | 'owns'
  | 'located_in'
  | 'member_of'
  | 'other'

export interface Relationship {
  id: number
  projectId: number
  sourceEntityId: number
  targetEntityId: number
  relationshipType: RelationshipType
  description?: string
  bidirectional: boolean
  strength: number
  createdAt?: Date
}
