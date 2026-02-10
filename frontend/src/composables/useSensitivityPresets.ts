/**
 * Composable: sensitivity preset system.
 *
 * Manages the unified sensitivity slider with 3 presets (conservador/balanceado/exhaustivo),
 * interpolation logic for custom values, and the advanced panel state.
 */

import { ref, computed, type Ref } from 'vue'
import type { Settings } from './useSettingsPersistence'

// ── Types ──────────────────────────────────────────────────

export interface SensitivityPreset {
  value: 'conservador' | 'balanceado' | 'exhaustivo'
  label: string
  description: string
  icon: string
  recommended?: boolean
  sensitivity: number
  minConfidence: number
  inferenceMinConfidence: number
  inferenceMinConsensus: number
}

// ── Constants ──────────────────────────────────────────────

export const sensitivityPresets: SensitivityPreset[] = [
  {
    value: 'conservador',
    label: 'Solo lo importante',
    description: 'Menos avisos, solo inconsistencias claras',
    icon: 'pi pi-shield',
    sensitivity: 20,
    minConfidence: 80,
    inferenceMinConfidence: 70,
    inferenceMinConsensus: 75,
  },
  {
    value: 'balanceado',
    label: 'Equilibrado',
    description: 'Balance entre detecci\u00F3n y ruido',
    icon: 'pi pi-sliders-h',
    recommended: true,
    sensitivity: 50,
    minConfidence: 65,
    inferenceMinConfidence: 55,
    inferenceMinConsensus: 60,
  },
  {
    value: 'exhaustivo',
    label: 'Revisar todo',
    description: 'M\u00E1s sugerencias para que t\u00FA decidas',
    icon: 'pi pi-search',
    sensitivity: 80,
    minConfidence: 45,
    inferenceMinConfidence: 40,
    inferenceMinConsensus: 40,
  },
]

// ── Composable ─────────────────────────────────────────────

export function useSensitivityPresets(
  settings: Ref<Settings>,
  saveSettings: () => void,
  onSliderChange: () => void,
) {
  const showAdvancedSensitivity = ref(false)

  const sensitivityLabel = computed(() => {
    const s = settings.value.sensitivity
    if (s <= 25) return 'Conservador'
    if (s <= 45) return 'Algo conservador'
    if (s <= 55) return 'Equilibrado'
    if (s <= 75) return 'Algo exhaustivo'
    return 'Exhaustivo'
  })

  function selectSensitivityPreset(presetValue: 'conservador' | 'balanceado' | 'exhaustivo') {
    const preset = sensitivityPresets.find(p => p.value === presetValue)
    if (!preset) return

    settings.value.sensitivityPreset = presetValue
    settings.value.sensitivity = preset.sensitivity
    settings.value.minConfidence = preset.minConfidence
    settings.value.inferenceMinConfidence = preset.inferenceMinConfidence
    settings.value.inferenceMinConsensus = preset.inferenceMinConsensus

    saveSettings()
  }

  function onSensitivityChange() {
    const s = settings.value.sensitivity
    const matchingPreset = sensitivityPresets.find(p => Math.abs(p.sensitivity - s) < 5)

    if (matchingPreset) {
      settings.value.sensitivityPreset = matchingPreset.value
      settings.value.minConfidence = matchingPreset.minConfidence
      settings.value.inferenceMinConfidence = matchingPreset.inferenceMinConfidence
      settings.value.inferenceMinConsensus = matchingPreset.inferenceMinConsensus
    } else {
      settings.value.sensitivityPreset = 'custom'
      settings.value.minConfidence = Math.round(90 - (s * 0.55))
      settings.value.inferenceMinConfidence = Math.round(80 - (s * 0.5))
      settings.value.inferenceMinConsensus = Math.round(80 - (s * 0.45))
    }

    onSliderChange()
  }

  function onAdvancedSliderChange() {
    settings.value.sensitivityPreset = 'custom'
    onSliderChange()
  }

  function recalculateFromSensitivity() {
    const s = settings.value.sensitivity
    const matchingPreset = sensitivityPresets.find(p => Math.abs(p.sensitivity - s) < 10)

    if (matchingPreset) {
      selectSensitivityPreset(matchingPreset.value)
    } else {
      settings.value.minConfidence = Math.round(90 - (s * 0.55))
      settings.value.inferenceMinConfidence = Math.round(80 - (s * 0.5))
      settings.value.inferenceMinConsensus = Math.round(80 - (s * 0.45))
      saveSettings()
    }
  }

  return {
    sensitivityPresets,
    showAdvancedSensitivity,
    sensitivityLabel,
    selectSensitivityPreset,
    onSensitivityChange,
    onAdvancedSliderChange,
    recalculateFromSensitivity,
  }
}
