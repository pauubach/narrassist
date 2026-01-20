/**
 * Domain Types - Tema y UI
 *
 * Configuración de apariencia de la aplicación.
 */

/** Modo de tema */
export type ThemeMode = 'light' | 'dark' | 'auto'

/** Preset de tema PrimeVue */
export type ThemePreset = 'aura' | 'lara' | 'material' | 'nora'

/** Tamaño de fuente */
export type FontSize = 'small' | 'medium' | 'large' | 'xlarge'

/** Altura de línea */
export type LineHeight = 'compact' | 'normal' | 'relaxed' | 'loose'

/** Radio de bordes */
export type UIRadius = 'none' | 'small' | 'medium' | 'large'

/** Compactación de UI */
export type UICompactness = 'compact' | 'normal' | 'comfortable'

/** Configuración completa del tema */
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
