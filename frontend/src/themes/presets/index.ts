/**
 * Theme Presets - Narrative Assistant
 *
 * Presets de temas personalizados orientados a escritura y corrección literaria.
 * Cada tema funciona tanto en modo claro como oscuro.
 * Los colores primarios son personalizables independientemente del tema.
 */

import type { PaletteDesignToken } from '@primeuix/themes/types'

// ============================================================================
// Types
// ============================================================================

/**
 * Tokens semánticos para texto y componentes en un color scheme
 */
export interface SemanticColorTokens {
  /** Color de texto principal */
  text?: string
  /** Color de texto secundario/muted */
  textMuted?: string
  /** Color de texto para botones text (secondary) */
  textButtonColor?: string
  /** Color de texto para botones text en hover */
  textButtonHoverColor?: string
  /** Fondo para hover en botones text */
  textButtonHoverBg?: string
  /** Color de error (para mensajes, botones danger) */
  errorColor?: string
  /** Color de borde por defecto */
  borderColor?: string
}

export interface ThemePresetConfig {
  name: string
  description: string
  /** Categoría del tema */
  category: 'general' | 'writing'
  /** Paleta de superficies para modo claro */
  lightSurface: PaletteDesignToken
  /** Paleta de superficies para modo oscuro */
  darkSurface: PaletteDesignToken
  /** Tokens semánticos para modo claro (opcional, usa defaults si no se especifica) */
  lightSemantics?: SemanticColorTokens
  /** Tokens semánticos para modo oscuro (opcional, usa defaults si no se especifica) */
  darkSemantics?: SemanticColorTokens
}

// ============================================================================
// Grammarly Theme - Clean, professional writing environment
// ============================================================================

/**
 * Tema Grammarly: Limpio, profesional, neutral.
 * Ideal para corrección de textos con buena legibilidad.
 * Basado en grises neutros que no cansan la vista.
 */
export const grammarlyPreset: ThemePresetConfig = {
  name: 'Grammarly',
  description: 'Limpio y profesional, ideal para corrección',
  category: 'writing',
  lightSurface: {
    0: '#FFFFFF',
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#EEEEEE',
    300: '#E0E0E0',
    400: '#BDBDBD',
    500: '#9E9E9E',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
    950: '#121212'
  },
  darkSurface: {
    0: '#121212',
    50: '#1E1E1E',
    100: '#232323',
    200: '#2C2C2C',
    300: '#3D3D3D',
    400: '#4F4F4F',
    500: '#6B6B6B',
    600: '#8A8A8A',
    700: '#A8A8A8',
    800: '#C7C7C7',
    900: '#E5E5E5',
    950: '#FAFAFA'
  }
}

// ============================================================================
// Scrivener Theme - Warm, paper-like writing environment
// ============================================================================

/**
 * Tema Scrivener: Cálido, acogedor, similar al papel.
 * Ideal para largas sesiones de lectura de manuscritos.
 * Tonos sepia que reducen la fatiga visual.
 *
 * Colores de contraste WCAG AA (mínimo 4.5:1):
 * - Dark mode (fondo #1A170F):
 *   - Texto principal: #E8DCC8 (sepia-200) = 9.5:1
 *   - Texto secundario: #C4B494 (sepia-400) = 5.2:1
 *   - Botones text: #D8CAB0 (sepia-300) = 6.5:1
 *   - Error: #fca5a5 (red-300) = 9.1:1
 */
export const scrivenerPreset: ThemePresetConfig = {
  name: 'Scrivener',
  description: 'Cálido como papel, perfecto para lectura prolongada',
  category: 'writing',
  lightSurface: {
    0: '#FBF7F0',
    50: '#F7F2E8',
    100: '#F0E8D8',
    200: '#E8DCC8',
    300: '#D8CAB0',
    400: '#C4B494',
    500: '#A89878',
    600: '#8C7C5C',
    700: '#6E6248',
    800: '#504834',
    900: '#322E20',
    950: '#1A170F'
  },
  darkSurface: {
    0: '#1A170F',
    50: '#252114',
    100: '#302A1C',
    200: '#3E3626',
    300: '#504834',
    400: '#6E6248',
    500: '#8C7C5C',
    600: '#A89878',
    700: '#C4B494',
    800: '#D8CAB0',
    900: '#E8DCC8',
    950: '#F7F2E8'
  },
  // Tokens semánticos para Scrivener Light (fondo claro sepia)
  lightSemantics: {
    text: '#322E20',           // sepia-900: texto principal
    textMuted: '#6E6248',      // sepia-700: texto secundario
    textButtonColor: '#504834', // sepia-800: botones text
    textButtonHoverColor: '#322E20',
    textButtonHoverBg: 'rgba(80, 72, 52, 0.08)',
    errorColor: '#b91c1c',     // red-700: buen contraste en light
    borderColor: '#D8CAB0'     // sepia-300
  },
  // Tokens semánticos para Scrivener Dark (fondo #1A170F)
  darkSemantics: {
    text: '#E8DCC8',           // sepia-200: 9.5:1 contraste
    textMuted: '#C4B494',      // sepia-400: 5.2:1 contraste (WCAG AA)
    textButtonColor: '#D8CAB0', // sepia-300: 6.5:1 contraste - botones "Cancelar"
    textButtonHoverColor: '#E8DCC8',
    textButtonHoverBg: 'rgba(216, 202, 176, 0.15)',
    errorColor: '#fca5a5',     // red-300: 9.1:1 contraste en dark
    borderColor: '#504834'     // sepia-300 dark
  }
}

// ============================================================================
// Export all presets
// ============================================================================

export const customPresets = {
  grammarly: grammarlyPreset,
  scrivener: scrivenerPreset
} as const

export type CustomPresetKey = keyof typeof customPresets
