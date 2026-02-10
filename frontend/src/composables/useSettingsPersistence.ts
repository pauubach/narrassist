/**
 * Composable: settings persistence (load/save/reset from localStorage).
 *
 * Extracted from SettingsView.vue — manages the central settings ref,
 * localStorage serialization, migration of old formats, and debounced saves.
 */

import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useThemeStore } from '@/stores/theme'
import type { SystemCapabilities } from '@/stores/system'

// ── Types ──────────────────────────────────────────────────

export interface EnabledMethods {
  coreference: string[]
  ner: string[]
  grammar: string[]
  spelling: string[]
  character_knowledge: string[]
}

export interface Settings {
  theme: 'light' | 'dark' | 'auto'
  fontSize: 'small' | 'medium' | 'large'
  lineHeight: string
  sensitivityPreset: 'conservador' | 'balanceado' | 'exhaustivo' | 'custom'
  sensitivity: number
  minConfidence: number
  inferenceMinConfidence: number
  inferenceMinConsensus: number
  autoAnalysis: boolean
  showPartialResults: boolean
  notifyAnalysisComplete: boolean
  soundEnabled: boolean
  enabledInferenceMethods: string[]
  prioritizeSpeed: boolean
  enabledNLPMethods: EnabledMethods
  characterKnowledgeMode: string
}

// ── Constants ──────────────────────────────────────────────

const STORAGE_KEY = 'narrative_assistant_settings'

const DEFAULT_SETTINGS: Settings = {
  theme: 'auto',
  fontSize: 'medium',
  lineHeight: '1.6',
  sensitivityPreset: 'balanceado',
  sensitivity: 50,
  minConfidence: 65,
  inferenceMinConfidence: 55,
  inferenceMinConsensus: 60,
  autoAnalysis: true,
  showPartialResults: true,
  notifyAnalysisComplete: true,
  soundEnabled: true,
  enabledInferenceMethods: ['llama3.2'],
  prioritizeSpeed: true,
  enabledNLPMethods: {
    coreference: ['embeddings', 'morpho', 'heuristics'],
    ner: ['spacy', 'gazetteer'],
    grammar: ['spacy_rules'],
    spelling: ['patterns', 'symspell', 'hunspell', 'languagetool', 'pyspellchecker'],
    character_knowledge: ['rules'],
  },
  characterKnowledgeMode: 'rules',
}

// Valid LLM method values (basic methods like rule_based/embeddings are always active)
const VALID_INFERENCE_METHODS = ['llama3.2', 'mistral', 'gemma2', 'qwen2.5']

// ── Composable ─────────────────────────────────────────────

export function useSettingsPersistence() {
  const toast = useToast()
  const themeStore = useThemeStore()

  const settings = ref<Settings>({ ...DEFAULT_SETTINGS })

  let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null

  // ── Load ────────────────────────────────────────────────

  function loadSettings() {
    const savedSettings = localStorage.getItem(STORAGE_KEY)
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings)

        // Filter inference methods to remove basic ones that are always active
        const filteredMethods = (parsed.enabledInferenceMethods || ['llama3.2'])
          .filter((m: string) => VALID_INFERENCE_METHODS.includes(m))

        // Migrate old settings without unified sensitivity
        const hasSensitivity = 'sensitivityPreset' in parsed && 'sensitivity' in parsed
        const sensitivityPreset = hasSensitivity ? parsed.sensitivityPreset : 'balanceado'
        const sensitivity = hasSensitivity ? parsed.sensitivity : 50

        settings.value = {
          ...settings.value,
          ...parsed,
          sensitivityPreset,
          sensitivity,
          minConfidence: parsed.minConfidence ?? 65,
          inferenceMinConfidence: parsed.inferenceMinConfidence ?? 55,
          inferenceMinConsensus: parsed.inferenceMinConsensus ?? 60,
          enabledInferenceMethods: filteredMethods.length > 0 ? filteredMethods : ['llama3.2'],
          prioritizeSpeed: parsed.prioritizeSpeed ?? true,
          enabledNLPMethods: parsed.enabledNLPMethods ?? {
            coreference: ['embeddings', 'morpho', 'heuristics'],
            ner: ['spacy', 'gazetteer'],
            grammar: ['spacy_rules'],
          },
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    }
  }

  // ── Save ────────────────────────────────────────────────

  function saveSettings() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings.value))
    window.dispatchEvent(new CustomEvent('settings-changed', { detail: settings.value }))
    toast.add({
      severity: 'success',
      summary: 'Configuraci\u00F3n guardada',
      detail: 'Los cambios se han guardado correctamente',
      life: 3000,
    })
  }

  function onSettingChange() {
    saveSettings()
  }

  /** Debounced save for sliders — shows toast only after user stops sliding. */
  function onSliderChange() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings.value))
    window.dispatchEvent(new CustomEvent('settings-changed', { detail: settings.value }))

    if (saveDebounceTimer) {
      clearTimeout(saveDebounceTimer)
    }
    saveDebounceTimer = setTimeout(() => {
      toast.add({
        severity: 'success',
        summary: 'Configuraci\u00F3n guardada',
        detail: 'Los cambios se han guardado correctamente',
        life: 3000,
      })
    }, 500)
  }

  // ── Defaults from capabilities ──────────────────────────

  function applyDefaultsFromCapabilities(capabilities: SystemCapabilities) {
    const methods = capabilities.nlp_methods
    const enabledMethods: EnabledMethods = {
      coreference: [],
      ner: [],
      grammar: [],
      spelling: [],
      character_knowledge: [],
    }

    for (const category of ['coreference', 'ner', 'grammar', 'spelling', 'character_knowledge'] as const) {
      const catMethods = methods[category]
      if (catMethods) {
        for (const [key, method] of Object.entries(catMethods)) {
          if (method.available && method.default_enabled) {
            enabledMethods[category].push(key)
          }
        }
      }
    }

    settings.value.enabledNLPMethods = enabledMethods
    saveSettings()
  }

  // ── Reset ───────────────────────────────────────────────

  function resetSettings(systemCapabilities: SystemCapabilities | null) {
    settings.value = { ...DEFAULT_SETTINGS }

    if (systemCapabilities) {
      applyDefaultsFromCapabilities(systemCapabilities)
    } else {
      saveSettings()
    }

    themeStore.resetToDefaults()

    toast.add({
      severity: 'success',
      summary: 'Configuraci\u00F3n restablecida',
      detail: 'Se ha restaurado la configuraci\u00F3n por defecto',
      life: 3000,
    })
  }

  // ── Cleanup ─────────────────────────────────────────────

  function cleanup() {
    if (saveDebounceTimer) {
      clearTimeout(saveDebounceTimer)
    }
  }

  return {
    settings,
    loadSettings,
    saveSettings,
    onSettingChange,
    onSliderChange,
    applyDefaultsFromCapabilities,
    resetSettings,
    cleanup,
  }
}
