import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { usePreset, updatePreset, palette } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import Lara from '@primeuix/themes/lara'
import Material from '@primeuix/themes/material'
import Nora from '@primeuix/themes/nora'

// ============================================================================
// Types
// ============================================================================

export type ThemePreset = 'aura' | 'lara' | 'material' | 'nora'
export type ThemeMode = 'light' | 'dark' | 'auto'
export type FontSize = 'small' | 'medium' | 'large' | 'xlarge'
export type LineHeight = 'compact' | 'normal' | 'relaxed' | 'loose'
export type UIRadius = 'none' | 'small' | 'medium' | 'large'
export type UICompactness = 'compact' | 'normal' | 'comfortable'

export interface PrimaryColor {
  name: string
  value: string
  label: string
}

export interface ThemeConfig {
  preset: ThemePreset
  primaryColor: string
  mode: ThemeMode
  fontSize: FontSize
  lineHeight: LineHeight
  radius: UIRadius
  compactness: UICompactness
  reducedMotion: boolean
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'narrative_assistant_theme_config'

export const PRESETS: Record<ThemePreset, { name: string; value: typeof Aura }> = {
  aura: { name: 'Aura', value: Aura },
  lara: { name: 'Lara', value: Lara },
  material: { name: 'Material', value: Material },
  nora: { name: 'Nora', value: Nora }
}

export const PRIMARY_COLORS: PrimaryColor[] = [
  { name: 'blue', value: '#3B82F6', label: 'Azul' },
  { name: 'indigo', value: '#6366F1', label: 'Índigo' },
  { name: 'purple', value: '#A855F7', label: 'Púrpura' },
  { name: 'pink', value: '#EC4899', label: 'Rosa' },
  { name: 'red', value: '#EF4444', label: 'Rojo' },
  { name: 'orange', value: '#F97316', label: 'Naranja' },
  { name: 'amber', value: '#F59E0B', label: 'Ámbar' },
  { name: 'yellow', value: '#EAB308', label: 'Amarillo' },
  { name: 'lime', value: '#84CC16', label: 'Lima' },
  { name: 'green', value: '#22C55E', label: 'Verde' },
  { name: 'teal', value: '#14B8A6', label: 'Teal' },
  { name: 'cyan', value: '#06B6D4', label: 'Cian' }
]

export const FONT_SIZES: Record<FontSize, { label: string; value: string }> = {
  small: { label: 'Pequeño', value: '14px' },
  medium: { label: 'Mediano', value: '16px' },
  large: { label: 'Grande', value: '18px' },
  xlarge: { label: 'Extra grande', value: '20px' }
}

export const LINE_HEIGHTS: Record<LineHeight, { label: string; value: string }> = {
  compact: { label: 'Compacto', value: '1.4' },
  normal: { label: 'Normal', value: '1.6' },
  relaxed: { label: 'Amplio', value: '1.8' },
  loose: { label: 'Muy amplio', value: '2.0' }
}

export const UI_RADIUS: Record<UIRadius, { label: string; value: string }> = {
  none: { label: 'Sin bordes', value: '0px' },
  small: { label: 'Sutil', value: '4px' },
  medium: { label: 'Medio', value: '8px' },
  large: { label: 'Redondeado', value: '12px' }
}

export const UI_COMPACTNESS: Record<UICompactness, { label: string; scale: number }> = {
  compact: { label: 'Compacto', scale: 0.875 },
  normal: { label: 'Normal', scale: 1 },
  comfortable: { label: 'Espacioso', scale: 1.125 }
}

const DEFAULT_CONFIG: ThemeConfig = {
  preset: 'aura',
  primaryColor: '#3B82F6',
  mode: 'auto',
  fontSize: 'medium',
  lineHeight: 'normal',
  radius: 'medium',
  compactness: 'normal',
  reducedMotion: false
}

// ============================================================================
// Store
// ============================================================================

export const useThemeStore = defineStore('theme', () => {
  // State
  const config = ref<ThemeConfig>({ ...DEFAULT_CONFIG })
  const isDark = ref(false)

  // System preference detection
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)')
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

  // Computed
  const currentPreset = computed(() => PRESETS[config.value.preset])
  const currentPrimaryColor = computed(() =>
    PRIMARY_COLORS.find(c => c.value === config.value.primaryColor) || PRIMARY_COLORS[0]
  )

  // ============================================================================
  // Theme Application
  // ============================================================================

  function applyDarkMode() {
    if (config.value.mode === 'auto') {
      isDark.value = prefersDark.matches
    } else {
      isDark.value = config.value.mode === 'dark'
    }

    // Toggle dark class on html element
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }

    console.log('[Theme] Dark mode:', isDark.value)
  }

  function applyPresetAndColor() {
    try {
      const basePreset = PRESETS[config.value.preset].value
      const colorPalette = palette(config.value.primaryColor)

      // Use usePreset to change the base preset completely
      usePreset(basePreset)

      // Then update the primary color
      updatePreset(basePreset, {
        semantic: {
          primary: colorPalette
        }
      })

      console.log('[Theme] Applied preset:', config.value.preset, 'with color:', config.value.primaryColor)
    } catch (e) {
      console.error('[Theme] Error applying preset:', e)
    }
  }

  function applyFontSize() {
    const size = FONT_SIZES[config.value.fontSize].value
    document.documentElement.style.fontSize = size
    console.log('[Theme] Font size:', size)
  }

  function applyLineHeight() {
    const height = LINE_HEIGHTS[config.value.lineHeight].value
    document.documentElement.style.lineHeight = height
    // Also set as CSS variable for components that need it
    document.documentElement.style.setProperty('--app-line-height', height)
    console.log('[Theme] Line height:', height)
  }

  function applyRadius() {
    const radius = UI_RADIUS[config.value.radius].value
    // Set custom property that overrides PrimeVue's border radius
    document.documentElement.style.setProperty('--p-content-border-radius', radius)
    document.documentElement.style.setProperty('--p-form-field-border-radius', radius)
    console.log('[Theme] Border radius:', radius)
  }

  function applyCompactness() {
    const scale = UI_COMPACTNESS[config.value.compactness].scale
    document.documentElement.style.setProperty('--app-spacing-scale', scale.toString())
    // Apply scaling to common spacing variables
    const baseGap = 1 * scale
    document.documentElement.style.setProperty('--app-gap', `${baseGap}rem`)
    console.log('[Theme] Compactness scale:', scale)
  }

  function applyReducedMotion() {
    const shouldReduce = config.value.reducedMotion || prefersReducedMotion.matches
    if (shouldReduce) {
      document.documentElement.classList.add('reduced-motion')
    } else {
      document.documentElement.classList.remove('reduced-motion')
    }
    console.log('[Theme] Reduced motion:', shouldReduce)
  }

  function applyAllStyles() {
    applyDarkMode()
    applyPresetAndColor()
    applyFontSize()
    applyLineHeight()
    applyRadius()
    applyCompactness()
    applyReducedMotion()
  }

  // ============================================================================
  // Persistence
  // ============================================================================

  function saveConfig() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config.value))
  }

  function loadConfig() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Partial<ThemeConfig>
        config.value = { ...DEFAULT_CONFIG, ...parsed }
      } catch (e) {
        console.warn('[Theme] Failed to parse theme config:', e)
        config.value = { ...DEFAULT_CONFIG }
      }
    }
  }

  // ============================================================================
  // Actions
  // ============================================================================

  function setPreset(preset: ThemePreset) {
    config.value.preset = preset
    applyPresetAndColor()
    saveConfig()
  }

  function setPrimaryColor(color: string) {
    config.value.primaryColor = color
    applyPresetAndColor()
    saveConfig()
  }

  function setMode(mode: ThemeMode) {
    config.value.mode = mode
    applyDarkMode()
    saveConfig()
  }

  function toggleMode() {
    const modes: ThemeMode[] = ['light', 'dark', 'auto']
    const currentIndex = modes.indexOf(config.value.mode)
    config.value.mode = modes[(currentIndex + 1) % modes.length]
    applyDarkMode()
    saveConfig()
  }

  function setFontSize(size: FontSize) {
    config.value.fontSize = size
    applyFontSize()
    saveConfig()
  }

  function setLineHeight(height: LineHeight) {
    config.value.lineHeight = height
    applyLineHeight()
    saveConfig()
  }

  function setRadius(radius: UIRadius) {
    config.value.radius = radius
    applyRadius()
    saveConfig()
  }

  function setCompactness(compactness: UICompactness) {
    config.value.compactness = compactness
    applyCompactness()
    saveConfig()
  }

  function setReducedMotion(reduced: boolean) {
    config.value.reducedMotion = reduced
    applyReducedMotion()
    saveConfig()
  }

  function resetToDefaults() {
    config.value = { ...DEFAULT_CONFIG }
    applyAllStyles()
    saveConfig()
  }

  // ============================================================================
  // Initialize
  // ============================================================================

  function initialize() {
    console.log('[Theme] Initializing...')
    loadConfig()
    applyAllStyles()

    // Listen for system preference changes
    prefersDark.addEventListener('change', () => {
      if (config.value.mode === 'auto') {
        applyDarkMode()
      }
    })

    prefersReducedMotion.addEventListener('change', () => {
      applyReducedMotion()
    })

    console.log('[Theme] Initialized with config:', config.value)
  }

  return {
    // State
    config,
    isDark,
    // Computed
    currentPreset,
    currentPrimaryColor,
    // Constants (exported for UI)
    PRESETS,
    PRIMARY_COLORS,
    FONT_SIZES,
    LINE_HEIGHTS,
    UI_RADIUS,
    UI_COMPACTNESS,
    // Actions
    setPreset,
    setPrimaryColor,
    setMode,
    toggleMode,
    setFontSize,
    setLineHeight,
    setRadius,
    setCompactness,
    setReducedMotion,
    resetToDefaults,
    initialize
  }
})
