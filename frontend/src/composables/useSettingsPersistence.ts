/**
 * Composable: settings persistence (load/save/reset from localStorage + backend).
 *
 * Extracted from SettingsView.vue — manages the central settings ref,
 * localStorage serialization, migration of old formats, and debounced saves.
 *
 * CR-03 post-MVP: Los settings de análisis (enabledNLPMethods,
 * multiModelSynthesis, characterKnowledgeMode) se persisten también en
 * el backend por proyecto vía PATCH /api/projects/{id}/settings.
 */

import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useThemeStore } from '@/stores/theme'
import type { SystemCapabilities } from '@/stores/system'
import { safeSetItem, safeGetItem } from '@/utils/safeStorage'
import { getProject, updateProjectSettings } from '@/services/projects'
import type {
  ApiAnalysisFeatures,
  ApiNLPMethods,
  ApiPipelineFlags,
} from '@/types/api/projects'

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
  multiModelSynthesis: boolean
  enabledNLPMethods: EnabledMethods
  characterKnowledgeMode: string
  qualityLevel: string
  llmSensitivity: number
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
  prioritizeSpeed: false,
  multiModelSynthesis: true,
  qualityLevel: 'rapida',
  llmSensitivity: 5,
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
const VALID_INFERENCE_METHODS = ['llama3.2', 'mistral', 'gemma2', 'qwen2.5', 'qwen3', 'hermes3', 'deepseek-r1']

function createDefaultSettings(): Settings {
  return {
    ...DEFAULT_SETTINGS,
    enabledInferenceMethods: [...DEFAULT_SETTINGS.enabledInferenceMethods],
    enabledNLPMethods: {
      coreference: [...DEFAULT_SETTINGS.enabledNLPMethods.coreference],
      ner: [...DEFAULT_SETTINGS.enabledNLPMethods.ner],
      grammar: [...DEFAULT_SETTINGS.enabledNLPMethods.grammar],
      spelling: [...DEFAULT_SETTINGS.enabledNLPMethods.spelling],
      character_knowledge: [...DEFAULT_SETTINGS.enabledNLPMethods.character_knowledge],
    },
  }
}

function toLocalStoragePayload(settings: Settings): Omit<Settings, 'enabledNLPMethods' | 'multiModelSynthesis' | 'characterKnowledgeMode'> {
  const {
    enabledNLPMethods: _enabledNLPMethods,
    multiModelSynthesis: _multiModelSynthesis,
    characterKnowledgeMode: _characterKnowledgeMode,
    ...rest
  } = settings
  return rest
}

function extractCharacterKnowledgeMode(features: ApiAnalysisFeatures): string {
  const methods = features.nlp_methods?.character_knowledge ?? []
  if (methods.includes('hybrid')) return 'hybrid'
  if (methods.includes('llm')) return 'llm'
  return 'rules'
}

// Syncs pendientes de settings por proyecto (permite coordinar entre vistas).
const pendingAnalysisSettingsSync = new Map<number, Promise<boolean>>()

function registerPendingAnalysisSettingsSync(
  projectId: number,
  pending: Promise<boolean>,
): Promise<boolean> {
  pendingAnalysisSettingsSync.set(projectId, pending)
  pending.finally(() => {
    if (pendingAnalysisSettingsSync.get(projectId) === pending) {
      pendingAnalysisSettingsSync.delete(projectId)
    }
  })
  return pending
}

/**
 * Espera una sincronización de settings en curso para un proyecto.
 * Devuelve true si no había sync pendiente o si terminó correctamente.
 */
export async function waitForPendingAnalysisSettingsSync(projectId: number): Promise<boolean> {
  const pending = pendingAnalysisSettingsSync.get(projectId)
  if (!pending) return true
  try {
    return await pending
  } catch {
    return false
  }
}

// ── Composable ─────────────────────────────────────────────

export function useSettingsPersistence() {
  const toast = useToast()
  const themeStore = useThemeStore()

  const settings = ref<Settings>(createDefaultSettings())

  let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null

  // ── Load ────────────────────────────────────────────────

  function loadSettings() {
    const savedSettings = safeGetItem(STORAGE_KEY)
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings)
        // CR-03: analysis settings come from backend (project scope), never from localStorage.
        const {
          enabledNLPMethods: _legacyEnabledNLPMethods,
          multiModelSynthesis: _legacyMultiModelSynthesis,
          characterKnowledgeMode: _legacyCharacterKnowledgeMode,
          ...parsedWithoutAnalysis
        } = parsed || {}

        // Filter inference methods to remove basic ones that are always active
        const filteredMethods = (parsedWithoutAnalysis.enabledInferenceMethods || ['llama3.2'])
          .filter((m: string) => VALID_INFERENCE_METHODS.includes(m))

        // Migrate old settings without unified sensitivity
        const hasSensitivity = 'sensitivityPreset' in parsedWithoutAnalysis && 'sensitivity' in parsedWithoutAnalysis
        const sensitivityPreset = hasSensitivity ? parsedWithoutAnalysis.sensitivityPreset : 'balanceado'
        const sensitivity = hasSensitivity ? parsedWithoutAnalysis.sensitivity : 50

        settings.value = {
          ...settings.value,
          ...parsedWithoutAnalysis,
          sensitivityPreset,
          sensitivity,
          minConfidence: parsedWithoutAnalysis.minConfidence ?? 65,
          inferenceMinConfidence: parsedWithoutAnalysis.inferenceMinConfidence ?? 55,
          inferenceMinConsensus: parsedWithoutAnalysis.inferenceMinConsensus ?? 60,
          enabledInferenceMethods: filteredMethods.length > 0 ? filteredMethods : ['llama3.2'],
          prioritizeSpeed: parsedWithoutAnalysis.prioritizeSpeed ?? false,
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    }
  }

  // ── Save ────────────────────────────────────────────────

  function saveSettings() {
    const ok = safeSetItem(STORAGE_KEY, JSON.stringify(toLocalStoragePayload(settings.value)))
    window.dispatchEvent(new CustomEvent('settings-changed', { detail: settings.value }))
    toast.add({
      severity: ok ? 'success' : 'warn',
      summary: ok ? 'Configuraci\u00F3n guardada' : 'Error al guardar',
      detail: ok ? 'Los cambios se han guardado correctamente' : 'No se pudieron guardar los cambios (almacenamiento lleno)',
      life: 3000,
    })
  }

  function onSettingChange() {
    saveSettings()
  }

  /** Debounced save for sliders — shows toast only after user stops sliding. */
  function onSliderChange() {
    safeSetItem(STORAGE_KEY, JSON.stringify(toLocalStoragePayload(settings.value)))
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
    settings.value = createDefaultSettings()

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

  async function loadAnalysisSettingsFromBackend(projectId: number): Promise<boolean> {
    try {
      const project = await getProject(projectId)
      const features = project.settings?.analysis_features
      if (!features) {
        return false
      }

      const methods = features.nlp_methods || {}
      settings.value.enabledNLPMethods = {
        coreference: [...(methods.coreference || [])],
        ner: [...(methods.ner || [])],
        grammar: [...(methods.grammar || [])],
        spelling: [...(methods.spelling || [])],
        character_knowledge: [...(methods.character_knowledge || [])],
      }

      settings.value.multiModelSynthesis = features.pipeline_flags?.multi_model_voting ?? true
      settings.value.characterKnowledgeMode = extractCharacterKnowledgeMode(features)
      return true
    } catch (err) {
      console.warn('Could not load analysis settings from backend:', err)
      return false
    }
  }

  // ── Backend sync (CR-03 post-MVP) ─────────────────────

  /**
   * Sincroniza los settings de análisis al backend para un proyecto.
   *
   * Construye un patch con pipeline_flags y nlp_methods desde el estado
   * actual de settings y lo envía al backend. Muestra warnings de
   * capabilities si el backend los reporta.
   *
   * @param projectId - ID del proyecto activo
   * @returns true si se sincronizó correctamente
   */
  async function syncAnalysisSettingsToBackend(projectId: number): Promise<boolean> {
    const pending = (async () => {
      try {
        const s = settings.value
        const nlpMethods: ApiNLPMethods = {
          coreference: [...s.enabledNLPMethods.coreference],
          ner: [...s.enabledNLPMethods.ner],
          grammar: [...s.enabledNLPMethods.grammar],
          spelling: [...s.enabledNLPMethods.spelling],
          character_knowledge: [...s.enabledNLPMethods.character_knowledge],
        }

        const pipelineFlags: ApiPipelineFlags = {
          grammar: (nlpMethods.grammar?.length ?? 0) > 0,
          spelling: (nlpMethods.spelling?.length ?? 0) > 0,
        }

        if (typeof s.multiModelSynthesis === 'boolean') {
          pipelineFlags.multi_model_voting = s.multiModelSynthesis
        }

        const result = await updateProjectSettings(projectId, {
          analysis_features: {
            schema_version: 1,
            pipeline_flags: pipelineFlags,
            nlp_methods: nlpMethods,
          },
        })

        // Mostrar warnings de capabilities si los hay
        if (result.runtime_warnings && result.runtime_warnings.length > 0) {
          for (const warning of result.runtime_warnings) {
            toast.add({
              severity: 'warn',
              summary: 'Advertencia de capacidad',
              detail: warning,
              life: 5000,
            })
          }
        }

        return true
      } catch (err) {
        console.warn('Could not sync analysis settings to backend:', err)
        return false
      }
    })()

    return registerPendingAnalysisSettingsSync(projectId, pending)
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
    loadAnalysisSettingsFromBackend,
    syncAnalysisSettingsToBackend,
    cleanup,
  }
}
