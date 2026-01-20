/**
 * Domain Types - Entidades
 *
 * Tipos simplificados para uso interno en la UI.
 * Agrupan tipos del backend en categorías más manejables.
 */

/** Tipos de entidad simplificados para la UI */
export type EntityType =
  | 'character'   // character, animal, creature
  | 'location'    // location, building, region
  | 'object'      // object, vehicle
  | 'organization' // organization, faction, family
  | 'event'       // event, time_period
  | 'concept'     // concept, religion, magic_system
  | 'other'       // work, title, language, custom

/** Importancia de entidad normalizada */
export type EntityImportance = 'main' | 'secondary' | 'minor'

/** Entidad para uso en componentes */
export interface Entity {
  id: number
  projectId: number
  type: EntityType
  name: string
  aliases: string[]
  importance: EntityImportance
  description?: string
  firstMentionChapter?: number
  mentionCount: number
  isActive: boolean
  /** IDs de entidades que fueron fusionadas en esta */
  mergedFromIds: number[]
  /**
   * Score de relevancia (0-1) basado en densidad de menciones.
   * Calcula: menciones por cada 1000 palabras, normalizado.
   * - 0.5 = ~2 menciones por 1000 palabras
   * - 0.7 = ~5 menciones por 1000 palabras
   * - 0.8 = ~10 menciones por 1000 palabras
   */
  relevanceScore?: number
  createdAt?: Date
  updatedAt?: Date
}

/** Registro de historial de fusiones */
export interface MergeHistoryEntry {
  id: number
  projectId: number
  resultEntityId: number
  resultEntityName: string
  sourceEntityIds: number[]
  sourceEntityNames: string[]
  mergedAt: Date
  undoneAt?: Date
  note?: string
}

/** Atributo de entidad */
export interface EntityAttribute {
  id: number
  entityId: number
  category: string
  name: string
  value: string
  chapter?: number
  chapterId?: number
  confidence: number
  /** Posición inicial en el texto (global) para navegación */
  spanStart?: number
  /** Posición final en el texto (global) */
  spanEnd?: number
  /** ID de la mención fuente */
  sourceMentionId?: number
}

/** Mención de entidad en el texto */
export interface EntityMention {
  id: number
  entityId: number
  chapterId: number
  text: string
  spanStart: number
  spanEnd: number
  confidence: number
}

/** Relación entre entidades */
export interface EntityRelationship {
  id: number
  sourceEntityId: number
  targetEntityId: number
  relationshipType: string
  description?: string
  bidirectional: boolean
  strength: number
}

/** Sugerencia de fusión de entidades */
export interface FusionSuggestion {
  id: number
  entityAId: number
  entityBId: number
  entityAName: string
  entityBName: string
  confidence: number
  reason: string
  status: 'pending' | 'accepted' | 'rejected'
}
