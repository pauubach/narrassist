/**
 * Domain Types - Corrections
 *
 * Tipos para configuración de correcciones editoriales.
 */

/** Configuración completa de correcciones */
export interface CorrectionConfig {
  profile: {
    document_field: string
    secondary_fields: string[]
    register: string
    audience: string
    region: string
    allow_mixed_register: boolean
  }
  typography: {
    enabled: boolean
    dialogue_dash: string
    quote_style: string
    check_spacing: boolean
    check_ellipsis: boolean
  }
  repetition: {
    enabled: boolean
    min_distance: number
    sensitivity: string
    ignore_dialogue: boolean
  }
  agreement: {
    enabled: boolean
    check_gender: boolean
    check_number: boolean
  }
  regional: {
    enabled: boolean
    target_region: string
    detect_mixed_variants: boolean
  }
  terminology: {
    enabled: boolean
  }
  use_llm_review: boolean
}

/** Preset de corrección */
export interface CorrectionPreset {
  id: string
  name: string
  description: string
  config: CorrectionConfig
}

/**
 * Regla editorial para el modal de configuración
 * (usado en DetailedCorrectionConfig)
 */
export interface EditorialRule {
  id: string
  text: string
  enabled: boolean
  source: 'type' | 'subtype' | 'custom'
  source_name: string | null
  overridden: boolean
}

/**
 * Configuración de correcciones con esquema detallado + herencia
 * (usado en CorrectionConfigModal y DocumentTypeChip)
 *
 * Este schema es más profundo que CorrectionConfig:
 * - Incluye metadata de tipo/subtipo
 * - Soporta herencia de configuración
 * - Esquema dialog más completo con presets + legacy markers
 * - Más configuraciones granulares (proximity_window_chars, sticky_threshold_pct, etc.)
 */
export interface DetailedCorrectionConfig {
  type_code: string
  type_name: string
  subtype_code: string | null
  subtype_name: string | null
  dialog: {
    enabled: boolean
    // New marker system
    preset: string
    detection_mode: string
    spoken_dialogue_dash: string
    spoken_dialogue_quote: string
    thoughts_quote: string
    thoughts_use_italics: boolean
    nested_dialogue_quote: string
    textual_quote: string
    // Legacy fields (for backwards compatibility)
    dialog_markers: string[]
    preferred_marker: string | null
    flag_inconsistent_markers: boolean
    analyze_dialog_tags: boolean
    dialog_tag_variation_min: number
    flag_consecutive_same_tag: boolean
  }
  repetition: {
    enabled: boolean
    tolerance: string
    proximity_window_chars: number
    min_word_length: number
    ignore_words: string[]
    flag_lack_of_repetition: boolean
  }
  sentence: {
    enabled: boolean
    max_length_words: number | null
    recommended_length_words: number | null
    analyze_complexity: boolean
    passive_voice_tolerance_pct: number
    adverb_ly_tolerance_pct: number
  }
  style: {
    enabled: boolean
    analyze_sentence_starts: boolean
    analyze_sticky_sentences: boolean
    sticky_threshold_pct: number
    analyze_register: boolean
    analyze_emotions: boolean
  }
  structure: {
    timeline_enabled: boolean
    relationships_enabled: boolean
    behavior_consistency_enabled: boolean
    scenes_enabled: boolean
    location_tracking_enabled: boolean
    vital_status_enabled: boolean
  }
  readability: {
    enabled: boolean
    target_age_min: number | null
    target_age_max: number | null
    analyze_vocabulary_age: boolean
    max_vocabulary_size: number | null
  }
  regional: {
    enabled: boolean
    target_region: string
    detect_mixed_variants: boolean
    suggest_regional_alternatives: boolean
    min_confidence: number
  }
  editorial_rules: {
    rules: EditorialRule[]
  }
  inheritance: Record<string, { source: string; source_name: string | null }>
}
