/**
 * Domain Types - Alertas
 *
 * Tipos simplificados para uso interno en la UI.
 */

/**
 * Fuente de una inconsistencia (ubicación donde se menciona un valor).
 * Usado para navegación a múltiples ubicaciones en alertas de inconsistencia.
 */
export interface AlertSource {
  /** Número de capítulo (1-indexed) */
  chapter: number | null
  /** Página estimada */
  page?: number
  /** Línea estimada */
  line?: number
  /** Posición de inicio en caracteres */
  startChar: number
  /** Posición de fin en caracteres */
  endChar: number
  /** Texto donde aparece el valor */
  excerpt: string
  /** Valor del atributo en esta ubicación */
  value: string
}

/**
 * Datos adicionales de la alerta según su tipo.
 * Permite acceder a información específica como sources para inconsistencias.
 */
export interface AlertExtraData {
  /** Nombre de la entidad (para inconsistencias de atributo) */
  entityName?: string
  /** Clave del atributo (para inconsistencias de atributo) */
  attributeKey?: string
  /** Primer valor conflictivo */
  value1?: string
  /** Segundo valor conflictivo */
  value2?: string
  /** Fuentes de cada valor para navegación múltiple */
  sources?: AlertSource[]
  /** Otros datos específicos del tipo de alerta */
  [key: string]: unknown
}

/** Severidad de alerta normalizada para la UI */
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** Estado de alerta simplificado */
export type AlertStatus = 'active' | 'dismissed' | 'resolved'

/** Categoría de alerta para la UI */
export type AlertCategory =
  | 'attribute'     // consistency
  | 'timeline'      // time-related from consistency
  | 'relationship'  // relaciones entre personajes
  | 'location'      // world
  | 'behavior'      // behavioral
  | 'knowledge'     // focalization
  | 'style'         // style
  | 'grammar'       // grammar, orthography
  | 'structure'     // structure
  | 'typography'    // tipografía (guiones, comillas, espaciado)
  | 'punctuation'   // puntuación (raya de diálogo, puntos suspensivos)
  | 'repetition'    // repeticiones léxicas
  | 'agreement'     // concordancia género/número
  | 'other'         // entity, other

/** Tipo específico de alerta (issue_type del backend) */
export type AlertIssueType =
  | 'linguistic_filler'      // FillerDetector: muletillas catálogo prescriptivo
  | 'overused_word'          // CrutchWordsDetector: muletillas análisis estadístico
  | 'lexical_close'          // RepetitionDetector: repetición léxica cercana
  | 'sentence_start'         // RepetitionDetector: inicio de oraciones repetido
  | 'paragraph_start'        // RepetitionDetector: inicio de párrafos repetido
  | 'gender_disagreement'    // AgreementDetector: discordancia género
  | 'number_disagreement'    // AgreementDetector: discordancia número
  | 'register_change'        // RegisterChangeDetector: cambio de registro
  | 'pov_shift'              // POVDetector: cambio de POV
  | 'sticky_sentence'        // StickySentenceDetector: oración pegajosa
  | 'low_energy_sentence'    // SentenceEnergyDetector: oración baja energía
  | 'speech_change'          // SpeechTracker: cambio de habla por personaje (v0.10.13)
  | 'typo'                   // SpellingChecker: error tipográfico
  | 'misspelling'            // SpellingChecker: palabra mal escrita
  | 'accent'                 // SpellingChecker: falta/sobra tilde
  | string                   // Otros tipos no listados

/** Alerta para uso en componentes */
export interface Alert {
  id: number
  projectId: number
  category: AlertCategory
  severity: AlertSeverity
  status: AlertStatus
  /** Tipo específico de alerta (ej: linguistic_filler, overused_word) */
  alertType: AlertIssueType
  title: string
  description: string
  explanation?: string
  suggestion?: string
  chapter?: number
  spanStart?: number
  spanEnd?: number
  /** Fragmento del texto donde ocurre la alerta */
  excerpt?: string
  entityIds: number[]
  confidence: number
  createdAt: Date
  resolvedAt?: Date
  /**
   * Datos adicionales específicos del tipo de alerta.
   * Para inconsistencias de atributo, contiene sources[] con ubicaciones
   * de cada valor conflictivo para navegación múltiple.
   */
  extraData?: AlertExtraData
  /** S14: Resumen de la alerta previa (si fue vinculada) */
  previousAlertSummary?: string
  /** S14: Confianza del matching con alerta anterior (0-1) */
  matchConfidence?: number
  /** S14: Razón de resolución (text_changed, detector_improved, manual) */
  resolutionReason?: string
}

/** Filtros para alertas */
export interface AlertFilters {
  severity?: AlertSeverity[]
  category?: AlertCategory[]
  status?: AlertStatus[]
  entityId?: number
  chapter?: number
  search?: string
}

/** Estadísticas de alertas */
export interface AlertStats {
  total: number
  bySeverity: Record<AlertSeverity, number>
  byCategory: Record<AlertCategory, number>
  byStatus: Record<AlertStatus, number>
}

// ============================================================================
// S14: Revision Intelligence domain types
// ============================================================================

/** Alerta en un diff de comparación */
export interface ComparisonAlertDiff {
  alertType: string
  category: string
  severity: string
  title: string
  chapter?: number
  confidence: number
  resolutionReason?: string
  matchConfidence?: number
  spanStart?: number
  spanEnd?: number
}

/** Detalle completo de comparación entre versiones */
export interface ComparisonDetail {
  hasComparison: boolean
  projectId?: number
  snapshotId?: number
  snapshotCreatedAt?: string
  documentChanged?: boolean
  alertsNew: ComparisonAlertDiff[]
  alertsResolved: ComparisonAlertDiff[]
  alertsUnchanged: number
  entitiesAdded: { name: string; type: string }[]
  entitiesRemoved: { name: string; type: string }[]
  entitiesUnchanged: number
  totalAlertsBefore: number
  totalAlertsAfter: number
}
