/**
 * Composable: NLP method toggling and capability-based defaults.
 *
 * Manages per-category method enable/disable, character knowledge mode,
 * available LLM options, and recommended config application.
 */

import { computed, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useSystemStore, type NLPMethod } from '@/stores/system'
import type { Settings } from './useSettingsPersistence'

// ── Constants ──────────────────────────────────────────────

export const inferenceMethodOptions = [
  { value: 'llama3.2', label: 'Llama 3.2 (3B)', description: 'R\u00E1pido, buena calidad general', speed: 'fast', quality: 'good' },
  { value: 'mistral', label: 'Mistral (7B)', description: 'Mayor calidad, m\u00E1s lento', speed: 'medium', quality: 'high' },
  { value: 'gemma2', label: 'Gemma 2 (9B)', description: 'Alta calidad, requiere m\u00E1s recursos', speed: 'slow', quality: 'very_high' },
  { value: 'qwen2.5', label: 'Qwen 2.5 (7B)', description: 'Excelente para espa\u00F1ol', speed: 'medium', quality: 'high' },
]

export type NLPCategory = 'coreference' | 'ner' | 'grammar' | 'spelling' | 'character_knowledge'

// Default methods shown while system capabilities are loading
const DEFAULT_METHODS: Record<string, Record<string, NLPMethod>> = {
  coreference: {
    embeddings: { name: 'An\u00E1lisis de significado similar', description: 'Cargando...', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: true },
    llm: { name: 'Analizador inteligente', description: 'Requiere iniciar el analizador inteligente', available: false, default_enabled: false, requires_gpu: false, recommended_gpu: true },
    morpho: { name: 'An\u00E1lisis de estructura gramatical', description: 'Cargando...', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
    heuristics: { name: 'Reglas narrativas', description: 'Cargando...', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
  },
  ner: {
    spacy: { name: 'Detector de nombres', description: 'Cargando...', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: true },
  },
  grammar: {
    spacy_rules: { name: 'Corrector b\u00E1sico', description: 'Cargando...', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
  },
  spelling: {
    patterns: { name: 'Patrones', description: 'Reglas y patrones comunes', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
    symspell: { name: 'SymSpell', description: 'Corrector r\u00E1pido por distancia', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
    hunspell: { name: 'Hunspell', description: 'Diccionario de LibreOffice', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
    languagetool: { name: 'LanguageTool', description: 'Gram\u00E1tica y ortograf\u00EDa avanzada', available: true, default_enabled: false, requires_gpu: false, recommended_gpu: false },
    pyspellchecker: { name: 'PySpellChecker', description: 'Corrector por frecuencia', available: true, default_enabled: false, requires_gpu: false, recommended_gpu: false },
    beto: { name: 'BETO ML', description: 'Modelo neuronal espa\u00F1ol', available: false, default_enabled: false, requires_gpu: true, recommended_gpu: true },
  },
  character_knowledge: {
    rules: { name: 'Reglas', description: 'Inferencia basada en reglas narrativas', available: true, default_enabled: true, requires_gpu: false, recommended_gpu: false },
    llm: { name: 'Análisis semántico', description: 'Análisis profundo con modelo de lenguaje', available: false, default_enabled: false, requires_gpu: false, recommended_gpu: true },
    hybrid: { name: 'Híbrido', description: 'Combina reglas con verificación semántica', available: false, default_enabled: false, requires_gpu: false, recommended_gpu: true },
  },
}

// ── Composable ─────────────────────────────────────────────

export function useNLPMethods(
  settings: Ref<Settings>,
  saveSettings: () => void,
  applyDefaultsFromCapabilities: (caps: any) => void,
) {
  const toast = useToast()
  const systemStore = useSystemStore()

  const systemCapabilities = computed(() => systemStore.systemCapabilities)

  const availableLLMOptions = computed(() => {
    const installedModels = systemCapabilities.value?.ollama.models.map((m: any) => m.name.split(':')[0]) || []
    return inferenceMethodOptions.map(opt => ({
      ...opt,
      installed: installedModels.includes(opt.value),
    }))
  })

  const gpuRequirementTooltip = computed(() => {
    const blocked = systemCapabilities.value?.hardware.gpu_blocked
    if (blocked) {
      return `${blocked.name} no es compatible con el análisis avanzado. Se requiere hardware más reciente.`
    }
    return 'Necesita aceleración por hardware para este método'
  })

  function getNLPMethodsForCategory(category: NLPCategory): Record<string, NLPMethod> {
    if (!systemCapabilities.value) {
      return DEFAULT_METHODS[category] || {}
    }
    return systemCapabilities.value.nlp_methods[category] || {}
  }

  function isMethodEnabled(category: NLPCategory, methodKey: string): boolean {
    const methods = settings.value.enabledNLPMethods[category]
    return methods ? methods.includes(methodKey) : false
  }

  function toggleMethod(category: NLPCategory, methodKey: string, enabled: boolean) {
    let methods = settings.value.enabledNLPMethods[category]
    if (!methods) {
      settings.value.enabledNLPMethods[category] = []
      methods = settings.value.enabledNLPMethods[category]
    }
    if (enabled && !methods.includes(methodKey)) {
      methods.push(methodKey)
    } else if (!enabled) {
      const index = methods.indexOf(methodKey)
      if (index > -1) {
        methods.splice(index, 1)
      }
    }
    saveSettings()
  }

  function setCharacterKnowledgeMode(mode: string) {
    settings.value.characterKnowledgeMode = mode
    saveSettings()
  }

  function applyRecommendedConfig() {
    if (!systemCapabilities.value) return
    applyDefaultsFromCapabilities(systemCapabilities.value)
    toast.add({
      severity: 'success',
      summary: 'Configuraci\u00F3n aplicada',
      detail: 'Se ha aplicado la configuraci\u00F3n recomendada para tu hardware',
      life: 3000,
    })
  }

  return {
    availableLLMOptions,
    gpuRequirementTooltip,
    getNLPMethodsForCategory,
    isMethodEnabled,
    toggleMethod,
    setCharacterKnowledgeMode,
    applyRecommendedConfig,
  }
}
