import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { mockSafeGetItem, mockSafeSetItem } = vi.hoisted(() => ({
  mockSafeGetItem: vi.fn<(key: string) => string | null>(),
  mockSafeSetItem: vi.fn<(key: string, value: string) => boolean>(),
}))

vi.mock('@/utils/safeStorage', () => ({
  safeGetItem: mockSafeGetItem,
  safeSetItem: mockSafeSetItem,
}))

vi.mock('@primeuix/themes', () => ({
  usePreset: vi.fn(),
  updatePreset: vi.fn(),
  palette: vi.fn(() => ({ 500: '#3B82F6' })),
  definePreset: vi.fn((_base: unknown, config: unknown) => config),
}))

vi.mock('@primeuix/themes/aura', () => ({ default: {} }))
vi.mock('@primeuix/themes/lara', () => ({ default: {} }))
vi.mock('@primeuix/themes/material', () => ({ default: {} }))
vi.mock('@primeuix/themes/nora', () => ({ default: {} }))

import { useThemeStore } from '../theme'

describe('themeStore legacy migration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: '',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('migrates legacy theme mode when modern config is absent', () => {
    mockSafeGetItem.mockImplementation((key: string) => {
      if (key === 'narrative_assistant_theme_config') return null
      if (key === 'narrative_assistant_theme') return 'dark'
      return null
    })
    mockSafeSetItem.mockReturnValue(true)

    const store = useThemeStore()
    store.initialize()

    expect(store.config.mode).toBe('dark')
    expect(mockSafeSetItem).toHaveBeenCalledWith(
      'narrative_assistant_theme_config',
      expect.stringContaining('"mode":"dark"')
    )
  })

  it('prefers the modern config over the legacy theme key', () => {
    mockSafeGetItem.mockImplementation((key: string) => {
      if (key === 'narrative_assistant_theme_config') {
        return JSON.stringify({ mode: 'light', preset: 'scrivener' })
      }
      if (key === 'narrative_assistant_theme') return 'dark'
      return null
    })

    const store = useThemeStore()
    store.initialize()

    expect(store.config.mode).toBe('light')
    expect(store.config.preset).toBe('scrivener')
    expect(mockSafeSetItem).not.toHaveBeenCalled()
  })
})
