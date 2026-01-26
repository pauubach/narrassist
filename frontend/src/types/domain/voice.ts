/**
 * Domain types for Voice and Style Analysis.
 *
 * These types are used by Vue components and represent the UI-friendly
 * version of the data (camelCase naming convention).
 */

// =============================================================================
// Voice Profile Types
// =============================================================================

export interface VoiceMetrics {
  avgInterventionLength: number
  stdInterventionLength: number
  typeTokenRatio: number
  formalityScore: number
  fillerRatio: number
  exclamationRatio: number
  questionRatio: number
  totalInterventions: number
  totalWords: number
}

export interface VoiceProfile {
  entityId: number
  entityName: string
  metrics: VoiceMetrics
  characteristicWords: Array<{ word: string; score: number }>
  topFillers: Array<{ word: string; count: number }>
  speechPatterns: {
    startPatterns: string[]
    endPatterns: string[]
    expressions: string[]
  }
  confidence: number
}

export interface VoiceProfilesResponse {
  projectId: number
  profiles: VoiceProfile[]
  stats: {
    charactersAnalyzed: number
    totalDialogues: number
    chaptersAnalyzed: number
  }
}

// =============================================================================
// Register Analysis Types
// =============================================================================

export type RegisterType =
  | 'formal_literary'
  | 'neutral'
  | 'colloquial'
  | 'technical'
  | 'poetic'

export type ChangeSeverity = 'low' | 'medium' | 'high' | 'none'

export interface RegisterAnalysis {
  segmentIndex: number
  chapter: number
  isDialogue: boolean
  primaryRegister: RegisterType
  registerScores: Record<RegisterType, number>
  confidence: number
  formalIndicators: string[]
  colloquialIndicators: string[]
}

export interface RegisterChange {
  fromSegment: number
  toSegment: number
  fromRegister: RegisterType
  toRegister: RegisterType
  severity: ChangeSeverity
  explanation: string
  chapter: number | null
}

export interface RegisterSummary {
  totalSegments: number
  narrativeSegments: number
  dialogueSegments: number
  distribution: Record<string, number>
  dominantRegister: string
  consistency?: number
}

export interface RegisterAnalysisResponse {
  projectId: number
  analyses: RegisterAnalysis[]
  changes: RegisterChange[]
  summary: RegisterSummary
  stats: {
    segmentsAnalyzed: number
    changesDetected: number
    chaptersAnalyzed: number
  }
}

// =============================================================================
// Dialogue Attribution Types
// =============================================================================

export type AttributionConfidence = 'high' | 'medium' | 'low' | 'unknown'

export type AttributionMethod =
  | 'explicit_verb'
  | 'alternation'
  | 'voice_profile'
  | 'proximity'
  | 'none'

export interface DialogueAttribution {
  dialogueIndex: number
  text: string
  startChar: number
  endChar: number
  speakerId: number | null
  speakerName: string | null
  confidence: AttributionConfidence
  method: AttributionMethod
  speechVerb: string | null
  alternatives: Array<{
    id: number
    name: string
    score: number
  }>
}

export interface DialogueAttributionStats {
  total: number
  attributed: number
  highConfidence: number
  mediumConfidence: number
  lowConfidence: number
  unknown: number
  byMethod: Record<AttributionMethod, number>
}

export interface DialogueAttributionResponse {
  projectId: number
  chapterNum: number
  attributions: DialogueAttribution[]
  stats: DialogueAttributionStats
}

// =============================================================================
// Character Knowledge Types
// =============================================================================

export type KnowledgeType =
  | 'existence'
  | 'identity'
  | 'attribute'
  | 'location'
  | 'relationship'
  | 'secret'
  | 'history'
  | 'intention'

export interface KnowledgeFact {
  id: number | null
  knowerEntityId: number
  knownEntityId: number
  knowerName: string
  knownName: string
  knowledgeType: KnowledgeType
  factDescription: string
  factValue: string
  sourceChapter: number
  isAccurate: boolean | null
  confidence: number
}

export interface CharacterKnowledgeResponse {
  projectId: number
  entityId: number
  entityName: string
  knowsAboutOthers: KnowledgeFact[]
  othersKnowAbout: KnowledgeFact[]
  stats: {
    factsKnown: number
    factsAbout: number
    chaptersAnalyzed: number
    extractionMode: string
  }
}
