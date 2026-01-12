/**
 * Tipos compartidos para el frontend de Narrative Assistant
 */

// ============================================================================
// API Response
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// ============================================================================
// Alert Types (declarados primero porque Project los usa)
// ============================================================================

export type AlertSeverity = 'critical' | 'warning' | 'info' | 'hint'
export type AlertStatus = 'open' | 'dismissed' | 'resolved' | 'false_positive'
export type AlertCategory = 'consistency' | 'continuity' | 'character' | 'timeline' | 'other'

// ============================================================================
// Theme Types
// ============================================================================

export type ThemeMode = 'light' | 'dark' | 'auto'
export type ThemePreset = 'aura' | 'lara' | 'material' | 'nora'
export type FontSize = 'small' | 'medium' | 'large' | 'xlarge'
export type LineHeight = 'compact' | 'normal' | 'relaxed' | 'loose'
export type UIRadius = 'none' | 'small' | 'medium' | 'large'
export type UICompactness = 'compact' | 'normal' | 'comfortable'

export interface ThemeConfig {
  preset: ThemePreset
  primaryColor: string
  mode: ThemeMode
  fontSize: FontSize
  lineHeight: LineHeight
  radius: UIRadius
  compactness: UICompactness
  reducedMotion: boolean
}

// ============================================================================
// Project
// ============================================================================

export interface Project {
  id: number
  name: string
  description?: string
  document_path?: string
  document_format: string
  created_at: string
  last_modified: string
  last_opened?: string
  analysis_progress: number
  word_count: number
  chapter_count: number
  entity_count?: number
  open_alerts_count?: number
  highest_alert_severity?: AlertSeverity
}

// ============================================================================
// Entity
// ============================================================================

export type EntityType =
  | 'CHARACTER'
  | 'LOCATION'
  | 'ORGANIZATION'
  | 'OBJECT'
  | 'EVENT'
  | 'ANIMAL'
  | 'CREATURE'
  | 'BUILDING'
  | 'REGION'
  | 'VEHICLE'
  | 'FACTION'
  | 'FAMILY'
  | 'TIME_PERIOD'
  | 'CONCEPT'
  | 'RELIGION'
  | 'MAGIC_SYSTEM'
  | 'WORK'
  | 'TITLE'
  | 'LANGUAGE'

export type EntityImportance = 'critical' | 'high' | 'medium' | 'low' | 'minimal'

export interface Entity {
  id: number
  project_id: number
  entity_type: EntityType
  canonical_name: string
  aliases: string[]
  importance: EntityImportance
  description?: string
  first_mention_chapter?: number
  first_mention_position?: number
  mention_count: number
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Alert (interface completa, los tipos están arriba)
// ============================================================================

export interface Alert {
  id: number
  project_id: number
  category: AlertCategory
  severity: AlertSeverity
  alert_type: string
  title: string
  description: string
  explanation: string
  suggestion?: string
  chapter?: number
  position_start?: number
  position_end?: number
  status: AlertStatus
  entity_ids?: number[]
  entities?: Entity[]
  created_at: string
  updated_at?: string
  resolved_at?: string
}

// ============================================================================
// Chapter
// ============================================================================

export interface Chapter {
  id: number
  project_id: number
  title: string
  content: string
  chapter_number: number
  word_count: number
  position_start: number
  position_end: number
  structure_type?: string
  created_at?: string
  updated_at?: string
}

// ============================================================================
// Character (ficha de personaje)
// ============================================================================

export interface CharacterAttribute {
  id?: number
  entity_id: number
  attribute_category: string
  attribute_name: string
  attribute_value: string
  first_mention_chapter?: number
  confidence_score?: number
}

export interface CharacterRelationship {
  id?: number
  entity_id: number
  related_entity_id: number
  related_entity_name?: string
  relationship_type: string
  description?: string
}

export interface CharacterSheet {
  entity_id: number
  canonical_name: string
  aliases: string[]
  importance: EntityImportance
  attributes: CharacterAttribute[]
  relationships?: CharacterRelationship[]
  first_mention_chapter?: number
  mention_count: number
}

// ============================================================================
// Relationship
// ============================================================================

export type RelationshipType =
  | 'FAMILY'
  | 'ROMANTIC'
  | 'FRIENDSHIP'
  | 'PROFESSIONAL'
  | 'RIVAL'
  | 'ENEMY'
  | 'MENTOR'
  | 'STUDENT'
  | 'OWNS'
  | 'LOCATED_IN'
  | 'MEMBER_OF'
  | 'OTHER'

export interface Relationship {
  id: number
  project_id: number
  source_entity_id: number
  target_entity_id: number
  relationship_type: RelationshipType
  description?: string
  bidirectional: boolean
  strength: number
  created_at?: string
}
