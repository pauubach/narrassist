import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { usePreset, updatePreset, palette, definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import Lara from '@primeuix/themes/lara'
import Material from '@primeuix/themes/material'
import Nora from '@primeuix/themes/nora'

import { customPresets, type ThemePresetConfig, type CustomPresetKey } from '@/themes/presets'

// ============================================================================
// Types
// ============================================================================

/** Presets base de PrimeVue */
export type PrimeVuePreset = 'aura' | 'lara' | 'material' | 'nora'

/** Presets personalizados para escritura */
export type CustomThemePreset = CustomPresetKey

/** Todos los presets disponibles */
export type ThemePreset = PrimeVuePreset | CustomThemePreset
export type ThemeMode = 'light' | 'dark' | 'auto'
export type FontSize = 'small' | 'medium' | 'large' | 'xlarge'
export type LineHeight = 'compact' | 'normal' | 'relaxed' | 'loose'
export type UIRadius = 'none' | 'small' | 'medium' | 'large'
export type UICompactness = 'compact' | 'normal' | 'comfortable'

/** Fuentes disponibles para la interfaz */
export type FontFamily =
  // Generales (sans-serif)
  | 'system' | 'inter' | 'source-sans' | 'nunito'
  // Lectura (serif modernas)
  | 'literata' | 'merriweather' | 'source-serif' | 'lora'
  // Clásicas (estilo Word/tradicional)
  | 'garamond' | 'baskerville' | 'crimson' | 'playfair' | 'pt-serif' | 'cormorant' | 'ibm-plex-serif' | 'spectral'
  // Accesibles y especializadas
  | 'atkinson' | 'roboto-serif' | 'noto-serif' | 'caslon'

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
  fontFamily: FontFamily
  fontFamilyReading: FontFamily
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'narrative_assistant_theme_config'

/** Info de un preset para UI */
export interface PresetInfo {
  name: string
  description: string
  category: 'general' | 'writing'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value: any // Los presets de PrimeVue tienen tipos complejos
}

/** Presets base de PrimeVue */
export const PRIMEVUE_PRESETS: Record<PrimeVuePreset, PresetInfo> = {
  aura: {
    name: 'Aura',
    description: 'Moderno y minimalista',
    category: 'general',
    value: Aura
  },
  lara: {
    name: 'Lara',
    description: 'Clásico y profesional',
    category: 'general',
    value: Lara
  },
  material: {
    name: 'Material',
    description: 'Google Material Design',
    category: 'general',
    value: Material
  },
  nora: {
    name: 'Nora',
    description: 'Sutil y elegante',
    category: 'general',
    value: Nora
  }
}

/**
 * Crea un preset PrimeVue a partir de una configuración personalizada.
 * Extiende Aura con las superficies personalizadas para light y dark.
 */
function createCustomPreset(config: ThemePresetConfig) {
  return definePreset(Aura, {
    semantic: {
      colorScheme: {
        light: {
          surface: config.lightSurface
        },
        dark: {
          surface: config.darkSurface
        }
      }
    }
  })
}

/** Presets personalizados para escritura */
export const CUSTOM_PRESETS: Record<CustomThemePreset, PresetInfo> = {
  grammarly: {
    name: customPresets.grammarly.name,
    description: customPresets.grammarly.description,
    category: customPresets.grammarly.category,
    value: createCustomPreset(customPresets.grammarly)
  },
  scrivener: {
    name: customPresets.scrivener.name,
    description: customPresets.scrivener.description,
    category: customPresets.scrivener.category,
    value: createCustomPreset(customPresets.scrivener)
  }
}

/** Todos los presets disponibles */
export const PRESETS: Record<ThemePreset, PresetInfo> = {
  ...PRIMEVUE_PRESETS,
  ...CUSTOM_PRESETS
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

/** Información de cada fuente */
export interface FontInfo {
  label: string
  description: string
  category: 'general' | 'reading'
  cssVar: string
}

export const FONT_FAMILIES: Record<FontFamily, FontInfo> = {
  // === Fuentes generales (sans-serif para interfaz) ===
  system: {
    label: 'Sistema',
    description: 'Fuente nativa del sistema operativo',
    category: 'general',
    cssVar: 'var(--font-system)'
  },
  inter: {
    label: 'Inter',
    description: 'Moderna, excelente para interfaces',
    category: 'general',
    cssVar: 'var(--font-inter)'
  },
  'source-sans': {
    label: 'Source Sans',
    description: 'Limpia y profesional',
    category: 'general',
    cssVar: 'var(--font-source-sans)'
  },
  nunito: {
    label: 'Nunito',
    description: 'Suave y amigable',
    category: 'general',
    cssVar: 'var(--font-nunito)'
  },
  // === Fuentes de lectura (serif modernas) ===
  literata: {
    label: 'Literata',
    description: 'Optimizada para lectura digital prolongada',
    category: 'reading',
    cssVar: 'var(--font-literata)'
  },
  merriweather: {
    label: 'Merriweather',
    description: 'Serif moderna, muy legible en pantalla',
    category: 'reading',
    cssVar: 'var(--font-merriweather)'
  },
  'source-serif': {
    label: 'Source Serif',
    description: 'Elegante, ideal para manuscritos',
    category: 'reading',
    cssVar: 'var(--font-source-serif)'
  },
  lora: {
    label: 'Lora',
    description: 'Contemporánea con toques caligráficos',
    category: 'reading',
    cssVar: 'var(--font-lora)'
  },
  // === Fuentes clásicas (estilo Word/tradicional) ===
  garamond: {
    label: 'Garamond',
    description: 'Clásica editorial francesa, muy elegante',
    category: 'reading',
    cssVar: 'var(--font-garamond)'
  },
  baskerville: {
    label: 'Baskerville',
    description: 'Clásica inglesa del s. XVIII, muy legible',
    category: 'reading',
    cssVar: 'var(--font-baskerville)'
  },
  crimson: {
    label: 'Crimson',
    description: 'Inspirada en tipos clásicos, elegante',
    category: 'reading',
    cssVar: 'var(--font-crimson)'
  },
  playfair: {
    label: 'Playfair Display',
    description: 'Alto contraste, ideal para títulos',
    category: 'reading',
    cssVar: 'var(--font-playfair)'
  },
  'pt-serif': {
    label: 'PT Serif',
    description: 'Profesional, muy legible en cualquier tamaño',
    category: 'reading',
    cssVar: 'var(--font-pt-serif)'
  },
  cormorant: {
    label: 'Cormorant',
    description: 'Elegante y refinada, estilo Garamond',
    category: 'reading',
    cssVar: 'var(--font-cormorant)'
  },
  'ibm-plex-serif': {
    label: 'IBM Plex Serif',
    description: 'Moderna pero con raíces clásicas',
    category: 'reading',
    cssVar: 'var(--font-ibm-plex-serif)'
  },
  spectral: {
    label: 'Spectral',
    description: 'Diseñada para pantalla, muy legible',
    category: 'reading',
    cssVar: 'var(--font-spectral)'
  },
  // === Fuentes accesibles y especializadas ===
  atkinson: {
    label: 'Atkinson Hyperlegible',
    description: 'Máxima legibilidad, ideal para baja visión',
    category: 'general',
    cssVar: 'var(--font-atkinson)'
  },
  'roboto-serif': {
    label: 'Roboto Serif',
    description: 'Versión serif de Roboto, muy versátil',
    category: 'reading',
    cssVar: 'var(--font-roboto-serif)'
  },
  'noto-serif': {
    label: 'Noto Serif',
    description: 'Universal de Google, excelente cobertura',
    category: 'reading',
    cssVar: 'var(--font-noto-serif)'
  },
  caslon: {
    label: 'Caslon',
    description: 'Clásica inglesa del s. XVIII, elegante',
    category: 'reading',
    cssVar: 'var(--font-caslon)'
  }
}

const DEFAULT_CONFIG: ThemeConfig = {
  preset: 'aura',
  primaryColor: '#3B82F6',
  mode: 'auto',
  fontSize: 'medium',
  lineHeight: 'normal',
  radius: 'medium',
  compactness: 'normal',
  reducedMotion: false,
  fontFamily: 'inter',
  fontFamilyReading: 'literata'
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
  const currentPrimaryColor = computed(
    () => PRIMARY_COLORS.find(c => c.value === config.value.primaryColor) || PRIMARY_COLORS[0]
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

  /** Verifica si es un preset personalizado */
  function isCustomPreset(preset: ThemePreset): preset is CustomThemePreset {
    return preset in CUSTOM_PRESETS
  }

  function applyPresetAndColor() {
    try {
      const presetKey = config.value.preset
      const presetInfo = PRESETS[presetKey]
      const basePreset = presetInfo.value

      // Use usePreset to change the base preset completely
      usePreset(basePreset)

      // Agregar clase de tema activo para CSS específico por tema
      // Esto permite selectores como .scrivener-theme .document-viewer
      const themeClasses = ['aura-theme', 'lara-theme', 'material-theme', 'nora-theme', 'grammarly-theme', 'scrivener-theme']
      document.documentElement.classList.remove(...themeClasses)
      document.documentElement.classList.add(`${presetKey}-theme`)

      // Aplicar el color primario a TODOS los temas (incluidos los personalizados)
      const colorPalette = palette(config.value.primaryColor)
      updatePreset(basePreset, {
        semantic: {
          primary: colorPalette
        }
      })

      console.log(
        '[Theme] Applied preset:',
        presetKey,
        'with color:',
        config.value.primaryColor
      )
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

    // Add CSS class for compactness mode
    document.documentElement.classList.remove('ui-compact', 'ui-normal', 'ui-comfortable')
    document.documentElement.classList.add(`ui-${config.value.compactness}`)

    console.log('[Theme] Compactness scale:', scale, 'class:', `ui-${config.value.compactness}`)
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

  function applyFontFamily() {
    const fontInfo = FONT_FAMILIES[config.value.fontFamily]
    const fontInfoReading = FONT_FAMILIES[config.value.fontFamilyReading]

    // Aplicar fuente de interfaz
    document.documentElement.style.setProperty('--font-family-active', fontInfo.cssVar)
    document.documentElement.style.fontFamily = fontInfo.cssVar

    // Aplicar fuente de lectura
    document.documentElement.style.setProperty('--font-family-reading', fontInfoReading.cssVar)

    console.log('[Theme] Font family:', config.value.fontFamily, '| Reading:', config.value.fontFamilyReading)
  }

  function applyAllStyles() {
    applyDarkMode()
    applyPresetAndColor()
    applyFontSize()
    applyLineHeight()
    applyRadius()
    applyCompactness()
    applyReducedMotion()
    applyFontFamily()
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
        // Migrar presets eliminados (nord, dracula) a aura
        const preset = parsed.preset as string | undefined
        if (preset === 'nord' || preset === 'dracula') {
          parsed.preset = 'aura'
        }
        // Validar que el preset existe
        if (parsed.preset && !(parsed.preset in PRESETS)) {
          parsed.preset = 'aura'
        }
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
    applyPresetAndColor() // Re-apply to ensure colors work in new mode
    saveConfig()
  }

  function toggleMode() {
    const modes: ThemeMode[] = ['light', 'dark', 'auto']
    const currentIndex = modes.indexOf(config.value.mode)
    config.value.mode = modes[(currentIndex + 1) % modes.length]
    applyDarkMode()
    applyPresetAndColor() // Re-apply to ensure colors work in new mode
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

  function setFontFamily(font: FontFamily) {
    config.value.fontFamily = font
    applyFontFamily()
    saveConfig()
  }

  function setFontFamilyReading(font: FontFamily) {
    config.value.fontFamilyReading = font
    applyFontFamily()
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
        applyPresetAndColor() // Re-apply colors for new mode
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
    PRIMEVUE_PRESETS,
    CUSTOM_PRESETS,
    PRIMARY_COLORS,
    FONT_SIZES,
    LINE_HEIGHTS,
    UI_RADIUS,
    UI_COMPACTNESS,
    FONT_FAMILIES,
    // Helpers
    isCustomPreset,
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
    setFontFamily,
    setFontFamilyReading,
    resetToDefaults,
    initialize
  }
})
