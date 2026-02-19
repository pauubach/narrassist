/**
 * Voice and Style Analysis Store
 *
 * Manages state for voice profiles, register analysis, dialogue attribution,
 * and character knowledge endpoints.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/services/apiClient'
import type {
  VoiceProfile,
  RegisterAnalysis,
  RegisterChange,
  RegisterSummary,
  RegisterType,
  ChangeSeverity,
  DialogueAttribution,
  DialogueAttributionStats,
  AttributionConfidence,
  AttributionMethod,
  KnowledgeFact,
  KnowledgeType,
} from '@/types'

// =============================================================================
// API Response Types (snake_case from backend)
// =============================================================================

interface ApiVoiceProfile {
  entity_id: number
  entity_name: string
  metrics: {
    avg_intervention_length: number
    std_intervention_length: number
    min_intervention_length: number
    max_intervention_length: number
    type_token_ratio: number
    hapax_legomena_ratio: number
    formality_score: number
    formal_marker_count: number
    informal_marker_count: number
    filler_ratio: number
    exclamation_ratio: number
    question_ratio: number
    ellipsis_ratio: number
    avg_sentence_length: number
    subordinate_clause_ratio: number
    total_interventions: number
    total_words: number
  }
  characteristic_words: Array<{ word: string; score: number }>
  top_fillers: Array<[string, number]>
  speech_patterns: {
    start_patterns: string[]
    end_patterns: string[]
    expressions: string[]
  }
  confidence: number
}

interface ApiRegisterAnalysis {
  segment_index: number
  chapter: number
  is_dialogue: boolean
  primary_register: RegisterType
  register_scores: Record<RegisterType, number>
  confidence: number
  formal_indicators: string[]
  colloquial_indicators: string[]
}

interface ApiRegisterChange {
  from_register: RegisterType
  to_register: RegisterType
  severity: ChangeSeverity
  explanation: string
  chapter: number | null
  position: number
  context_before: string
  context_after: string
}

interface ApiDialogueAttribution {
  dialogue_index: number
  text: string
  start_char: number
  end_char: number
  speaker_id: number | null
  speaker_name: string | null
  confidence: AttributionConfidence
  method: AttributionMethod
  speech_verb: string | null
  alternatives: Array<{ id: number; name: string; score: number }>
}

interface ApiKnowledgeFact {
  id: number | null
  knower_entity_id: number
  known_entity_id: number
  knower_name: string
  known_name: string
  knowledge_type: KnowledgeType
  fact_description: string
  fact_value: string
  source_chapter: number
  is_accurate: boolean | null
  confidence: number
}

// =============================================================================
// Transformers
// =============================================================================

function transformVoiceProfile(api: ApiVoiceProfile): VoiceProfile {
  return {
    entityId: api.entity_id,
    entityName: api.entity_name,
    metrics: {
      avgInterventionLength: api.metrics.avg_intervention_length,
      stdInterventionLength: api.metrics.std_intervention_length,
      minInterventionLength: api.metrics.min_intervention_length,
      maxInterventionLength: api.metrics.max_intervention_length,
      typeTokenRatio: api.metrics.type_token_ratio,
      hapaxLegomenaRatio: api.metrics.hapax_legomena_ratio,
      formalityScore: api.metrics.formality_score,
      formalMarkerCount: api.metrics.formal_marker_count,
      informalMarkerCount: api.metrics.informal_marker_count,
      fillerRatio: api.metrics.filler_ratio,
      exclamationRatio: api.metrics.exclamation_ratio,
      questionRatio: api.metrics.question_ratio,
      ellipsisRatio: api.metrics.ellipsis_ratio,
      avgSentenceLength: api.metrics.avg_sentence_length,
      subordinateClauseRatio: api.metrics.subordinate_clause_ratio,
      totalInterventions: api.metrics.total_interventions,
      totalWords: api.metrics.total_words,
    },
    characteristicWords: api.characteristic_words || [],
    topFillers: (api.top_fillers || []).map(([word, count]) => ({ word, count })),
    speechPatterns: {
      startPatterns: api.speech_patterns?.start_patterns || [],
      endPatterns: api.speech_patterns?.end_patterns || [],
      expressions: api.speech_patterns?.expressions || [],
    },
    confidence: api.confidence,
  }
}

function transformRegisterAnalysis(api: ApiRegisterAnalysis): RegisterAnalysis {
  return {
    segmentIndex: api.segment_index,
    chapter: api.chapter,
    isDialogue: api.is_dialogue,
    primaryRegister: api.primary_register,
    registerScores: api.register_scores,
    confidence: api.confidence,
    formalIndicators: api.formal_indicators,
    colloquialIndicators: api.colloquial_indicators,
  }
}

function transformRegisterChange(api: ApiRegisterChange): RegisterChange {
  return {
    fromRegister: api.from_register,
    toRegister: api.to_register,
    severity: api.severity,
    explanation: api.explanation,
    chapter: api.chapter,
    position: api.position,
    contextBefore: api.context_before || '',
    contextAfter: api.context_after || '',
  }
}

function transformDialogueAttribution(api: ApiDialogueAttribution): DialogueAttribution {
  return {
    dialogueIndex: api.dialogue_index,
    text: api.text,
    startChar: api.start_char,
    endChar: api.end_char,
    speakerId: api.speaker_id,
    speakerName: api.speaker_name,
    confidence: api.confidence,
    method: api.method,
    speechVerb: api.speech_verb,
    alternatives: api.alternatives,
  }
}

function transformKnowledgeFact(api: ApiKnowledgeFact): KnowledgeFact {
  return {
    id: api.id,
    knowerEntityId: api.knower_entity_id,
    knownEntityId: api.known_entity_id,
    knowerName: api.knower_name,
    knownName: api.known_name,
    knowledgeType: api.knowledge_type,
    factDescription: api.fact_description,
    factValue: api.fact_value,
    sourceChapter: api.source_chapter,
    isAccurate: api.is_accurate,
    confidence: api.confidence,
  }
}

function transformDialogueAttributionStats(apiStats: any): DialogueAttributionStats {
  const byConfidence = apiStats.by_confidence || {}
  const byMethod = apiStats.by_method || {}

  return {
    total: apiStats.total_dialogues || 0,
    attributed: apiStats.attributed_dialogues || 0,
    highConfidence: byConfidence.high || 0,
    mediumConfidence: byConfidence.medium || 0,
    lowConfidence: byConfidence.low || 0,
    unknown: byConfidence.unknown || 0,
    byMethod: byMethod,
  }
}

// =============================================================================
// Store Definition
// =============================================================================

export const useVoiceAndStyleStore = defineStore('voiceAndStyle', () => {
  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Voice profiles: projectId -> profiles[]
  const voiceProfiles = ref<Record<number, VoiceProfile[]>>({})

  // Register analysis: projectId -> { analyses, changes, summary, perChapter }
  const registerAnalyses = ref<Record<number, {
    analyses: RegisterAnalysis[]
    changes: RegisterChange[]
    summary: RegisterSummary | null
    perChapter: Array<{
      chapter_number: number
      dominant_register: string
      consistency_pct: number
      segment_count: number
      change_count: number
      distribution: Record<string, number>
    }>
  }>>({})

  // Dialogue attributions: "projectId-chapterNum" -> attributions[]
  const dialogueAttributions = ref<Record<string, {
    attributions: DialogueAttribution[]
    stats: DialogueAttributionStats | null
  }>>({})

  // Character knowledge: "projectId-entityId" -> knowledge
  const characterKnowledge = ref<Record<string, {
    knowsAboutOthers: KnowledgeFact[]
    othersKnowAbout: KnowledgeFact[]
    stats: any
  }>>({})

  // Loading and error states (per-action to avoid cross-cancellation)
  const loadingVoice = ref(false)
  const loadingRegister = ref(false)
  const loadingDialogue = ref(false)
  const loadingKnowledge = ref(false)
  const loading = computed(() => loadingVoice.value || loadingRegister.value || loadingDialogue.value || loadingKnowledge.value)
  const error = ref<string | null>(null)

  // -------------------------------------------------------------------------
  // Getters
  // -------------------------------------------------------------------------

  const getVoiceProfiles = computed(() => (projectId: number) => {
    return voiceProfiles.value[projectId] || []
  })

  const getRegisterAnalysis = computed(() => (projectId: number) => {
    return registerAnalyses.value[projectId] || null
  })

  const getDialogueAttributions = computed(() => (projectId: number, chapterNum: number) => {
    const key = `${projectId}-${chapterNum}`
    return dialogueAttributions.value[key] || null
  })

  const getCharacterKnowledge = computed(() => (projectId: number, entityId: number) => {
    const key = `${projectId}-${entityId}`
    return characterKnowledge.value[key] || null
  })

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  async function fetchVoiceProfiles(projectId: number): Promise<boolean> {
    loadingVoice.value = true
    error.value = null

    try {
      const data = await api.get<{
        project_id: number
        profiles: ApiVoiceProfile[]
        stats: any
      }>(`/api/projects/${projectId}/voice-profiles`)

      voiceProfiles.value[projectId] = (data.profiles || []).map(transformVoiceProfile)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
      console.error('Failed to fetch voice profiles:', err)
      return false
    } finally {
      loadingVoice.value = false
    }
  }

  async function fetchRegisterAnalysis(
    projectId: number,
    minSeverity: string = 'medium'
  ): Promise<boolean> {
    loadingRegister.value = true
    error.value = null

    try {
      const data = await api.get<{
        project_id: number
        analyses: ApiRegisterAnalysis[]
        changes: ApiRegisterChange[]
        summary: any
        stats: any
        per_chapter: any[]
      }>(`/api/projects/${projectId}/register-analysis?min_severity=${minSeverity}`)

      registerAnalyses.value[projectId] = {
        analyses: (data.analyses || []).map(transformRegisterAnalysis),
        changes: (data.changes || []).map(transformRegisterChange),
        summary: data.summary || null,
        perChapter: data.per_chapter || [],
      }
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
      console.error('Failed to fetch register analysis:', err)
      return false
    } finally {
      loadingRegister.value = false
    }
  }

  async function fetchDialogueAttributions(
    projectId: number,
    chapterNum: number
  ): Promise<boolean> {
    const key = `${projectId}-${chapterNum}`
    loadingDialogue.value = true
    error.value = null

    try {
      const data = await api.get<{
        project_id: number
        chapter_number: number
        attributions: ApiDialogueAttribution[]
        stats: any
      }>(`/api/projects/${projectId}/chapters/${chapterNum}/dialogue-attributions`)

      dialogueAttributions.value[key] = {
        attributions: (data.attributions || []).map(transformDialogueAttribution),
        stats: data.stats ? transformDialogueAttributionStats(data.stats) : null,
      }
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
      console.error('Failed to fetch dialogue attributions:', err)
      return false
    } finally {
      loadingDialogue.value = false
    }
  }

  async function fetchCharacterKnowledge(
    projectId: number,
    entityId: number,
    mode: string = 'auto'
  ): Promise<boolean> {
    const key = `${projectId}-${entityId}`
    loadingKnowledge.value = true
    error.value = null

    try {
      const data = await api.get<{
        project_id: number
        entity_id: number
        entity_name: string
        knows_about_others: ApiKnowledgeFact[]
        others_know_about: ApiKnowledgeFact[]
        stats: any
      }>(`/api/projects/${projectId}/characters/${entityId}/knowledge?mode=${mode}`)

      characterKnowledge.value[key] = {
        knowsAboutOthers: (data.knows_about_others || []).map(transformKnowledgeFact),
        othersKnowAbout: (data.others_know_about || []).map(transformKnowledgeFact),
        stats: data.stats || {},
      }
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
      console.error('Failed to fetch character knowledge:', err)
      return false
    } finally {
      loadingKnowledge.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearProjectData(projectId: number) {
    delete voiceProfiles.value[projectId]
    delete registerAnalyses.value[projectId]

    // Clear dialogue attributions for this project
    for (const key of Object.keys(dialogueAttributions.value)) {
      if (key.startsWith(`${projectId}-`)) {
        delete dialogueAttributions.value[key]
      }
    }

    // Clear character knowledge for this project
    for (const key of Object.keys(characterKnowledge.value)) {
      if (key.startsWith(`${projectId}-`)) {
        delete characterKnowledge.value[key]
      }
    }
  }

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    voiceProfiles,
    registerAnalyses,
    dialogueAttributions,
    characterKnowledge,
    loading,
    error,

    // Getters
    getVoiceProfiles,
    getRegisterAnalysis,
    getDialogueAttributions,
    getCharacterKnowledge,

    // Actions
    fetchVoiceProfiles,
    fetchRegisterAnalysis,
    fetchDialogueAttributions,
    fetchCharacterKnowledge,
    clearError,
    clearProjectData,
  }
})
