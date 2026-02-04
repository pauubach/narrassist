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
