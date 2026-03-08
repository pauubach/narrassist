/**
 * Clave de inyección para compartir estado de composables entre
 * SettingsView y sus secciones extraídas.
 *
 * Permite evitar pasar docenas de props repetitivos:
 * el parent hace provide() y cada sección hace inject().
 */
import type { InjectionKey, Ref, ComputedRef } from 'vue'
import type { SensitivityPreset } from '@/composables/useSensitivityPresets'
import type { NLPCategory } from '@/composables/useNLPMethods'

/** Tipo que devuelve useSettingsPersistence() — solo lo que las secciones necesitan */
export interface SettingsContext {
  settings: Ref<Record<string, any>>
  onSettingChange: () => void
  saveSettings: () => void
}

export interface SensitivityContext {
  sensitivityPresets: SensitivityPreset[]
  showAdvancedSensitivity: Ref<boolean>
  sensitivityLabel: ComputedRef<string>
  selectSensitivityPreset: (value: 'conservador' | 'balanceado' | 'exhaustivo') => void
  onSensitivityChange: () => void
  onAdvancedSliderChange: () => void
  recalculateFromSensitivity: () => void
}

export interface OllamaContext {
  ollamaState: ComputedRef<string>
  ollamaActionConfig: ComputedRef<{ label: string; icon: string; severity: string; action: () => void }>
  ollamaStatusMessage: ComputedRef<string>
  ollamaStarting: Ref<boolean>
  modelDownloading: Ref<boolean>
  ollamaDownloadProgress: Ref<{ percentage: number | null } | null>
  installModel: (name: string) => Promise<boolean>
}

export interface NLPMethodsContext {
  gpuRequirementTooltip: ComputedRef<string>
  getNLPMethodsForCategory: (category: NLPCategory) => Record<string, any>
  isMethodEnabled: (category: NLPCategory, key: string) => boolean
  toggleMethod: (category: NLPCategory, key: string, value: boolean) => void
  setCharacterKnowledgeMode: (mode: string) => void
  applyRecommendedConfig: () => void
}

export const settingsKey: InjectionKey<SettingsContext> = Symbol('settings')
export const sensitivityKey: InjectionKey<SensitivityContext> = Symbol('sensitivity')
export const ollamaKey: InjectionKey<OllamaContext> = Symbol('ollama')
export const nlpMethodsKey: InjectionKey<NLPMethodsContext> = Symbol('nlpMethods')
