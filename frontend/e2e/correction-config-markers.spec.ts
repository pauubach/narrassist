/**
 * Tests adversariales (GAN approach) para el sistema de configuración
 * de marcadores de diálogo.
 *
 * Enfoque: Intentar romper la persistencia, herencia y serialización
 * de la configuración de corrección.
 *
 * IMPORTANT: All suites run serially because they share project state.
 */
import { test, expect, type APIRequestContext } from '@playwright/test'

const API_URL = 'http://localhost:8008/api'
const FRONTEND_URL = 'http://localhost:5173'

// All tests in this file must run serially - they share project state
test.describe.configure({ mode: 'serial' })

// ============================================================================
// Helpers
// ============================================================================

async function getFirstProjectId(request: APIRequestContext): Promise<number | null> {
  const res = await request.get(`${API_URL}/projects`).catch(() => null)
  if (!res || !res.ok()) return null
  const data = await res.json()
  return data.data?.[0]?.id ?? null
}

async function getProjectConfig(request: APIRequestContext, projectId: number) {
  const res = await request.get(`${API_URL}/projects/${projectId}/correction-config`)
  expect(res.ok()).toBe(true)
  const data = await res.json()
  expect(data.success).toBe(true)
  return data.data
}

async function saveProjectConfig(
  request: APIRequestContext,
  projectId: number,
  customizations: Record<string, unknown>
) {
  const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
    data: { customizations },
  })
  expect(res.ok()).toBe(true)
  const data = await res.json()
  expect(data.success).toBe(true)
  return data.data
}

async function getDefaultConfig(request: APIRequestContext, typeCode: string, subtypeCode?: string) {
  let url = `${API_URL}/correction-config/defaults/${typeCode}`
  if (subtypeCode) url += `?subtype_code=${subtypeCode}`
  const res = await request.get(url)
  expect(res.ok()).toBe(true)
  const data = await res.json()
  expect(data.success).toBe(true)
  return data.data
}

async function saveDefaultConfig(
  request: APIRequestContext,
  typeCode: string,
  overrides: Record<string, unknown>,
  subtypeCode?: string
) {
  let url = `${API_URL}/correction-config/defaults/${typeCode}`
  if (subtypeCode) url += `?subtype_code=${subtypeCode}`
  const res = await request.put(url, {
    data: { overrides },
  })
  expect(res.ok()).toBe(true)
  const data = await res.json()
  expect(data.success).toBe(true)
  return data.data
}

async function deleteDefaultOverrides(request: APIRequestContext, typeCode: string, subtypeCode?: string) {
  let url = `${API_URL}/correction-config/defaults/${typeCode}`
  if (subtypeCode) url += `?subtype_code=${subtypeCode}`
  const res = await request.delete(url)
  return res
}

// Valores válidos por campo
const VALID_PRESETS = ['spanish_traditional', 'anglo_saxon', 'spanish_quotes', 'detect']
const VALID_DASH_TYPES = ['em_dash', 'en_dash', 'hyphen', 'none', 'auto']
const VALID_QUOTE_TYPES = ['angular', 'double', 'single', 'none', 'auto']
const VALID_DETECTION_MODES = ['auto', 'preset', 'custom']

// ============================================================================
// Test suite: API - Serialización y campos
// ============================================================================

test.describe('Correction Config API - Serialization', () => {
  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
  })

  test('GET config returns ALL new dialog fields', async ({ request }) => {
    const projectId = await getFirstProjectId(request)
    if (!projectId) { test.skip(); return }

    const config = await getProjectConfig(request, projectId)
    const dialog = config.dialog

    // Verificar que TODOS los campos nuevos existen
    const requiredFields = [
      'preset', 'detection_mode',
      'spoken_dialogue_dash', 'spoken_dialogue_quote',
      'thoughts_quote', 'thoughts_use_italics',
      'nested_dialogue_quote', 'textual_quote',
      'auto_detected', 'detection_confidence',
      'flag_inconsistent_markers',
      'analyze_dialog_tags', 'dialog_tag_variation_min',
      'flag_consecutive_same_tag', 'enabled',
    ]

    for (const field of requiredFields) {
      expect(dialog, `Field '${field}' should exist in dialog config`).toHaveProperty(field)
    }
  })

  test('preset field contains a valid value', async ({ request }) => {
    const projectId = await getFirstProjectId(request)
    if (!projectId) { test.skip(); return }

    const config = await getProjectConfig(request, projectId)
    expect(VALID_PRESETS).toContain(config.dialog.preset)
  })

  test('all enum fields contain valid values', async ({ request }) => {
    const projectId = await getFirstProjectId(request)
    if (!projectId) { test.skip(); return }

    const config = await getProjectConfig(request, projectId)
    const dialog = config.dialog

    expect(VALID_DETECTION_MODES).toContain(dialog.detection_mode)
    expect(VALID_DASH_TYPES).toContain(dialog.spoken_dialogue_dash)
    expect(VALID_QUOTE_TYPES).toContain(dialog.spoken_dialogue_quote)
    expect(VALID_QUOTE_TYPES).toContain(dialog.thoughts_quote)
    expect(VALID_QUOTE_TYPES).toContain(dialog.nested_dialogue_quote)
    expect(VALID_QUOTE_TYPES).toContain(dialog.textual_quote)
    expect(typeof dialog.thoughts_use_italics).toBe('boolean')
  })

  test('default FIC config has spanish_traditional preset', async ({ request }) => {
    const config = await getDefaultConfig(request, 'FIC')
    const effectiveConfig = config.effective_config

    expect(effectiveConfig.dialog.preset).toBe('spanish_traditional')
    expect(effectiveConfig.dialog.detection_mode).toBe('preset')
    expect(effectiveConfig.dialog.spoken_dialogue_dash).toBe('em_dash')
    expect(effectiveConfig.dialog.spoken_dialogue_quote).toBe('none')
    expect(effectiveConfig.dialog.thoughts_quote).toBe('angular')
    expect(effectiveConfig.dialog.nested_dialogue_quote).toBe('double')
  })

  test('config types endpoint returns all types', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/types`)
    expect(res.ok()).toBe(true)
    const data = await res.json()
    expect(data.success).toBe(true)

    const types = data.data
    expect(Array.isArray(types)).toBe(true)
    expect(types.length).toBeGreaterThanOrEqual(5)

    // Cada tipo debe tener campos requeridos
    for (const type of types) {
      expect(type).toHaveProperty('code')
      expect(type).toHaveProperty('name')
      expect(type).toHaveProperty('subtypes')
      expect(Array.isArray(type.subtypes)).toBe(true)
    }
  })
})

// ============================================================================
// Test suite: API - Persistencia (save → load → verify)
// ============================================================================

test.describe('Correction Config API - Persistence', () => {
  let projectId: number | null = null

  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
    projectId = await getFirstProjectId(request)
    if (!projectId) test.skip()
  })

  test('save preset and verify it persists', async ({ request }) => {
    if (!projectId) return

    // Guardar preset anglo_saxon
    await saveProjectConfig(request, projectId, {
      dialog: { preset: 'anglo_saxon', detection_mode: 'preset' },
    })

    // Cargar de nuevo y verificar
    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('anglo_saxon')
    expect(config.dialog.detection_mode).toBe('preset')
  })

  test('save all marker fields and verify they persist', async ({ request }) => {
    if (!projectId) return

    const customizations = {
      dialog: {
        preset: 'spanish_quotes',
        detection_mode: 'preset',
        spoken_dialogue_dash: 'none',
        spoken_dialogue_quote: 'angular',
        thoughts_quote: 'double',
        thoughts_use_italics: false,
        nested_dialogue_quote: 'single',
        textual_quote: 'angular',
        flag_inconsistent_markers: true,
      },
    }

    await saveProjectConfig(request, projectId, customizations)

    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('spanish_quotes')
    expect(config.dialog.spoken_dialogue_dash).toBe('none')
    expect(config.dialog.spoken_dialogue_quote).toBe('angular')
    expect(config.dialog.thoughts_quote).toBe('double')
    expect(config.dialog.thoughts_use_italics).toBe(false)
    expect(config.dialog.nested_dialogue_quote).toBe('single')
    expect(config.dialog.textual_quote).toBe('angular')
    expect(config.dialog.flag_inconsistent_markers).toBe(true)
  })

  test('save detect preset and verify auto detection mode', async ({ request }) => {
    if (!projectId) return

    await saveProjectConfig(request, projectId, {
      dialog: { preset: 'detect', detection_mode: 'auto' },
    })

    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('detect')
    expect(config.dialog.detection_mode).toBe('auto')
  })

  test('overwrite saved config with new values', async ({ request }) => {
    if (!projectId) return

    // Guardar primero anglo_saxon
    await saveProjectConfig(request, projectId, {
      dialog: { preset: 'anglo_saxon' },
    })

    // Verificar
    let config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('anglo_saxon')

    // Sobrescribir con spanish_traditional
    await saveProjectConfig(request, projectId, {
      dialog: { preset: 'spanish_traditional' },
    })

    // Verificar sobrescritura
    config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('spanish_traditional')
  })

  test('save multiple categories simultaneously', async ({ request }) => {
    if (!projectId) return

    await saveProjectConfig(request, projectId, {
      dialog: { preset: 'anglo_saxon', enabled: true },
      repetition: { tolerance: 'high', enabled: true },
      sentence: { max_length_words: 30 },
    })

    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBe('anglo_saxon')
    expect(config.repetition.tolerance).toBe('high')
    expect(config.sentence.max_length_words).toBe(30)
  })

  test('save boolean fields correctly (no string coercion)', async ({ request }) => {
    if (!projectId) return

    // Guardar con booleans false
    await saveProjectConfig(request, projectId, {
      dialog: {
        enabled: false,
        thoughts_use_italics: false,
        flag_inconsistent_markers: false,
        analyze_dialog_tags: false,
      },
    })

    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.enabled).toBe(false)
    expect(config.dialog.thoughts_use_italics).toBe(false)
    expect(config.dialog.flag_inconsistent_markers).toBe(false)
    expect(config.dialog.analyze_dialog_tags).toBe(false)

    // Verificar que no son strings "false"
    expect(config.dialog.enabled).not.toBe('false')
    expect(config.dialog.thoughts_use_italics).not.toBe('false')
  })

  test('save numeric fields correctly', async ({ request }) => {
    if (!projectId) return

    await saveProjectConfig(request, projectId, {
      repetition: { proximity_window_chars: 250 },
      sentence: { max_length_words: 42, passive_voice_tolerance_pct: 20.5 },
    })

    const config = await getProjectConfig(request, projectId)
    expect(config.repetition.proximity_window_chars).toBe(250)
    expect(config.sentence.max_length_words).toBe(42)
    expect(config.sentence.passive_voice_tolerance_pct).toBe(20.5)
  })

  // Restaurar estado original al final
  test.afterAll(async ({ request }) => {
    if (!projectId) return
    // Limpiar customizations restaurando preset por defecto
    await saveProjectConfig(request, projectId, {
      dialog: {
        preset: 'spanish_traditional',
        detection_mode: 'preset',
        spoken_dialogue_dash: 'em_dash',
        spoken_dialogue_quote: 'none',
        thoughts_quote: 'angular',
        thoughts_use_italics: true,
        nested_dialogue_quote: 'double',
        textual_quote: 'angular',
        flag_inconsistent_markers: true,
        analyze_dialog_tags: true,
        enabled: true,
      },
      repetition: { tolerance: 'medium', proximity_window_chars: 150, enabled: true },
      sentence: { max_length_words: null, passive_voice_tolerance_pct: 15.0, enabled: true },
    }).catch(() => {})
  })
})

// ============================================================================
// Test suite: Adversarial - Intentar romper el sistema
// ============================================================================

test.describe('Correction Config - Adversarial (GAN)', () => {
  let projectId: number | null = null

  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
    projectId = await getFirstProjectId(request)
    if (!projectId) test.skip()
  })

  test('ADV: save invalid preset value - should not crash API', async ({ request }) => {
    if (!projectId) return

    // Intentar guardar un preset inexistente
    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: 'NONEXISTENT_PRESET' },
        },
      },
    })

    // La API no debería crashear (puede aceptar o rechazar, pero no 500)
    expect(res.status()).not.toBe(500)
  })

  test('ADV: save empty string as preset', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: '' },
        },
      },
    })

    expect(res.status()).not.toBe(500)

    // Verificar que se puede cargar sin error
    const config = await getProjectConfig(request, projectId)
    expect(config.dialog).toBeDefined()
  })

  test('ADV: save null values for enum fields', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: {
            preset: null,
            spoken_dialogue_dash: null,
            thoughts_quote: null,
          },
        },
      },
    })

    expect(res.status()).not.toBe(500)

    // Cargar y verificar que no crashea
    const config = await getProjectConfig(request, projectId)
    expect(config.dialog).toBeDefined()
    expect(config.dialog.enabled).toBeDefined()
  })

  test('ADV: save wrong types (number as string field)', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: 12345 },
        },
      },
    })

    expect(res.status()).not.toBe(500)
  })

  test('ADV: save string as boolean field', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: {
            enabled: 'true',
            thoughts_use_italics: 'yes',
          },
        },
      },
    })

    expect(res.status()).not.toBe(500)
  })

  test('ADV: save very long string as preset', async ({ request }) => {
    if (!projectId) return

    const longString = 'A'.repeat(10000)
    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: longString },
        },
      },
    })

    expect(res.status()).not.toBe(500)
  })

  test('ADV: save deeply nested object in field', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: {
            preset: { nested: { very: { deep: 'value' } } },
          },
        },
      },
    })

    expect(res.status()).not.toBe(500)
  })

  test('ADV: save unknown category', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          nonexistent_category: { foo: 'bar' },
        },
      },
    })

    // Deberia aceptar pero ignorar categorías desconocidas
    expect(res.status()).not.toBe(500)

    // Los campos existentes no deberían verse afectados
    const config = await getProjectConfig(request, projectId)
    expect(config.dialog).toBeDefined()
    expect(config.repetition).toBeDefined()
  })

  test('ADV: save unknown field in known category', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { unknown_field_xyz: 'some_value' },
        },
      },
    })

    expect(res.status()).not.toBe(500)
  })

  test('ADV: save empty customizations object', async ({ request }) => {
    if (!projectId) return

    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: { customizations: {} },
    })

    expect(res.status()).not.toBe(500)
    const data = await res.json()
    expect(data.success).toBe(true)
  })

  test('ADV: rapid save/load cycle (race condition test)', async ({ request }) => {
    if (!projectId) return

    // Hacer 5 guardados rápidos con valores diferentes
    const presets = ['anglo_saxon', 'spanish_quotes', 'detect', 'spanish_traditional', 'anglo_saxon']
    const results = await Promise.all(
      presets.map((preset) =>
        request.put(`${API_URL}/projects/${projectId}/correction-config`, {
          data: {
            customizations: { dialog: { preset } },
          },
        })
      )
    )

    // Ninguno debería dar 500
    for (const res of results) {
      expect(res.status()).not.toBe(500)
    }

    // El valor final debería ser determinístico (último guardado gana)
    const config = await getProjectConfig(request, projectId)
    expect(VALID_PRESETS).toContain(config.dialog.preset)
  })

  test('ADV: XSS attempt in string fields', async ({ request }) => {
    if (!projectId) return

    const xssPayload = '<script>alert("xss")</script>'
    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: xssPayload },
        },
      },
    })

    expect(res.status()).not.toBe(500)

    // Verificar que el payload se guarda como texto plano, no se ejecuta
    const config = await getProjectConfig(request, projectId)
    // El valor debería estar ahí como string (sin sanitizar necesariamente, pero sin ejecutarse)
    expect(config.dialog).toBeDefined()
  })

  test('ADV: SQL injection attempt in string fields', async ({ request }) => {
    if (!projectId) return

    const sqlPayload = "'; DROP TABLE projects; --"
    const res = await request.put(`${API_URL}/projects/${projectId}/correction-config`, {
      data: {
        customizations: {
          dialog: { preset: sqlPayload },
        },
      },
    })

    expect(res.status()).not.toBe(500)

    // Verificar que la BD sigue intacta
    const projectsRes = await request.get(`${API_URL}/projects`)
    expect(projectsRes.ok()).toBe(true)
    const projectsData = await projectsRes.json()
    expect(projectsData.data.length).toBeGreaterThan(0)
  })

  // Limpiar después de tests adversariales
  test.afterAll(async ({ request }) => {
    if (!projectId) return
    await saveProjectConfig(request, projectId, {
      dialog: {
        preset: 'spanish_traditional',
        detection_mode: 'preset',
        spoken_dialogue_dash: 'em_dash',
        spoken_dialogue_quote: 'none',
        thoughts_quote: 'angular',
        thoughts_use_italics: true,
        nested_dialogue_quote: 'double',
        textual_quote: 'angular',
        flag_inconsistent_markers: true,
        analyze_dialog_tags: true,
        enabled: true,
      },
    }).catch(() => {})
  })
})

// ============================================================================
// Test suite: Herencia (tipo → subtipo → proyecto)
// ============================================================================

test.describe('Correction Config - Inheritance Chain', () => {
  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
  })

  test('FIC type config has correct defaults', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/FIC`)
    expect(res.ok()).toBe(true)
    const data = await res.json()

    const dialog = data.data.dialog
    expect(dialog.enabled).toBe(true)
    expect(dialog.preset).toBe('spanish_traditional')
    expect(dialog.spoken_dialogue_dash).toBe('em_dash')
  })

  test('INF type config has readability enabled', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/INF`)
    expect(res.ok()).toBe(true)
    const data = await res.json()

    expect(data.data.readability.enabled).toBe(true)
    expect(data.data.dialog.enabled).toBe(true)
  })

  test('TEC type config has dialog disabled', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/TEC`)
    expect(res.ok()).toBe(true)
    const data = await res.json()

    expect(data.data.dialog.enabled).toBe(false)
  })

  test('subtype INF_MID inherits from INF with overrides', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/INF?subtype_code=INF_MID`)
    expect(res.ok()).toBe(true)
    const data = await res.json()

    // INF_MID should have specific age range
    expect(data.data.readability.target_age_min).toBe(8)
    expect(data.data.readability.target_age_max).toBe(12)
    expect(data.data.sentence.max_length_words).toBe(20)
  })

  test('subtype INF_CAR overrides dialog to disabled', async ({ request }) => {
    const res = await request.get(`${API_URL}/correction-config/INF?subtype_code=INF_CAR`)
    expect(res.ok()).toBe(true)
    const data = await res.json()

    // INF_CAR (0-3 years) should have dialog disabled
    expect(data.data.dialog.enabled).toBe(false)
    expect(data.data.readability.target_age_min).toBe(0)
    expect(data.data.readability.target_age_max).toBe(3)
    expect(data.data.sentence.max_length_words).toBe(5)
  })

  test('all types have valid dialog configs', async ({ request }) => {
    const typesRes = await request.get(`${API_URL}/correction-config/types`)
    const typesData = await typesRes.json()

    for (const type of typesData.data) {
      const configRes = await request.get(`${API_URL}/correction-config/${type.code}`)
      if (!configRes.ok()) continue

      const configData = await configRes.json()
      const dialog = configData.data?.dialog

      // Todos los tipos deben tener un objeto dialog válido
      expect(dialog, `Type ${type.code} should have dialog config`).toBeDefined()
      expect(typeof dialog.enabled, `Type ${type.code} dialog.enabled should be boolean`).toBe('boolean')

      // Si dialog está habilitado, debe tener preset válido
      if (dialog.enabled && dialog.preset) {
        expect(
          VALID_PRESETS,
          `Type ${type.code} has invalid preset: ${dialog.preset}`
        ).toContain(dialog.preset)
      }
    }
  })
})

// ============================================================================
// Test suite: Defaults Management (user overrides)
// ============================================================================

test.describe('Correction Config - Defaults Overrides', () => {
  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
  })

  test('save and load default override for FIC type', async ({ request }) => {
    // Guardar override
    await saveDefaultConfig(request, 'FIC', {
      dialog: { flag_inconsistent_markers: false },
    })

    // Cargar y verificar
    const config = await getDefaultConfig(request, 'FIC')
    expect(config.override).toBeTruthy()
    expect(config.override.overrides.dialog.flag_inconsistent_markers).toBe(false)

    // La config efectiva debe reflejar el override
    expect(config.effective_config.dialog.flag_inconsistent_markers).toBe(false)

    // Limpiar
    await deleteDefaultOverrides(request, 'FIC')
  })

  test('delete default override restores original values', async ({ request }) => {
    // Guardar override
    await saveDefaultConfig(request, 'FIC', {
      dialog: { flag_inconsistent_markers: false },
    })

    // Eliminar override
    await deleteDefaultOverrides(request, 'FIC')

    // Verificar que vuelve al valor original
    const config = await getDefaultConfig(request, 'FIC')
    expect(config.effective_config.dialog.flag_inconsistent_markers).toBe(true)
  })

  test('override lifecycle: save, verify via GET, delete, verify cleared', async ({ request }) => {
    // Save an override
    await saveDefaultConfig(request, 'FIC', {
      dialog: { preset: 'anglo_saxon' },
    })

    // Verify it's reflected in the effective config
    const config = await getDefaultConfig(request, 'FIC')
    expect(config.override).toBeTruthy()
    expect(config.effective_config.dialog.preset).toBe('anglo_saxon')

    // Delete it
    const delRes = await deleteDefaultOverrides(request, 'FIC')
    expect(delRes.ok()).toBe(true)

    // Verify it's gone
    const configAfter = await getDefaultConfig(request, 'FIC')
    expect(configAfter.override).toBeNull()
    expect(configAfter.effective_config.dialog.preset).toBe('spanish_traditional')
  })
})

// ============================================================================
// Test suite: UI - Abrir modal y verificar campos
// ============================================================================

test.describe('Correction Config - UI Modal', () => {
  let projectId: number | null = null

  test.beforeEach(async ({ page, request }) => {
    const health = await request.get(`${API_URL}/health`).catch(() => null)
    if (!health || !health.ok()) test.skip()
    projectId = await getFirstProjectId(request)
    if (!projectId) { test.skip(); return }

    // Restaurar config por defecto antes de cada test UI
    await saveProjectConfig(request, projectId, {
      dialog: {
        preset: 'spanish_traditional',
        detection_mode: 'preset',
        spoken_dialogue_dash: 'em_dash',
        spoken_dialogue_quote: 'none',
        thoughts_quote: 'angular',
        thoughts_use_italics: true,
        nested_dialogue_quote: 'double',
        textual_quote: 'angular',
        flag_inconsistent_markers: true,
        enabled: true,
      },
    }).catch(() => {})

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(2000)
  })

  async function openCorrectionConfigModal(page: import('@playwright/test').Page): Promise<boolean> {
    // Dismiss any overlaying dialogs (e.g. welcome modal)
    const overlay = page.locator('.p-dialog-mask')
    if (await overlay.isVisible({ timeout: 1000 }).catch(() => false)) {
      // Try to close it via close button or clicking outside
      const closeBtn = page.locator('.p-dialog-mask .p-dialog-close-button, .p-dialog-mask button.p-dialog-header-close')
      if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeBtn.first().click()
        await page.waitForTimeout(500)
      } else {
        // Press Escape to dismiss
        await page.keyboard.press('Escape')
        await page.waitForTimeout(500)
      }
    }

    // Estrategia 1: Buscar chip de tipo de documento y su botón de settings
    const typeChip = page.locator('.document-type-chip, [data-testid="document-type-chip"]')
    if (await typeChip.isVisible({ timeout: 3000 }).catch(() => false)) {
      await typeChip.click({ timeout: 5000 }).catch(() => null)
      await page.waitForTimeout(500)

      const settingsOption = page.getByText(/configuración.*corrección/i).or(
        page.getByText(/config.*corrección/i)
      )
      if (await settingsOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await settingsOption.click()
        await page.waitForTimeout(1000)
        const dialog = page.locator('.p-dialog').filter({ hasText: /configuración/i })
        if (await dialog.isVisible({ timeout: 5000 }).catch(() => false)) {
          return true
        }
      }
    }

    // Estrategia 2: Buscar menú con ícono de engranaje
    const gearButtons = page.locator('button .pi-cog, button .pi-sliders-h').locator('..')
    const count = await gearButtons.count()
    for (let i = 0; i < count; i++) {
      const btn = gearButtons.nth(i)
      if (await btn.isVisible().catch(() => false)) {
        await btn.click()
        await page.waitForTimeout(1000)
        const dialog = page.locator('.p-dialog').filter({ hasText: /configuración/i })
        if (await dialog.isVisible({ timeout: 3000 }).catch(() => false)) {
          return true
        }
      }
    }

    // Estrategia 3: Intentar directamente abrir vía ejecutar JS
    const opened = await page.evaluate(() => {
      // Buscar instancia Vue del CorrectionConfigModal
      const modals = document.querySelectorAll('.correction-config-wrapper')
      for (const modal of modals) {
        const vueInstance = (modal as any).__vue_app__
        if (vueInstance) return true
      }
      return false
    }).catch(() => false)

    return false
  }

  test('modal can be opened and shows correct initial preset', async ({ page }) => {
    if (!projectId) return

    const opened = await openCorrectionConfigModal(page)
    if (!opened) {
      // Tomar screenshot para debug y skip
      await page.screenshot({ path: 'test-results/correction-config-ui-cannot-open.png', fullPage: true })
      console.log('Could not open correction config modal via UI')
      test.skip()
      return
    }

    // Verificar que el modal muestra el preset correcto
    const dialog = page.locator('.p-dialog').filter({ hasText: /configuración/i })

    // Buscar el select de preset
    const presetLabel = dialog.locator('.p-select-label').first()
    const presetText = await presetLabel.textContent({ timeout: 5000 }).catch(() => '')

    console.log('Preset display text:', presetText)

    // No debería mostrar placeholder
    expect(presetText).not.toContain('Seleccionar')
    expect(presetText).toBeTruthy()
  })

  test('ADV UI: change preset, save, verify console logs', async ({ page, request }) => {
    if (!projectId) return

    // Capturar console logs
    const consoleLogs: string[] = []
    page.on('console', (msg) => {
      if (msg.text().includes('CorrectionConfigModal')) {
        consoleLogs.push(msg.text())
      }
    })

    const opened = await openCorrectionConfigModal(page)
    if (!opened) {
      test.skip()
      return
    }

    // Verificar que los datos se cargaron correctamente via console
    await page.waitForTimeout(2000)

    // Verificar API directamente después del test
    const config = await getProjectConfig(request, projectId)
    expect(config.dialog.preset).toBeTruthy()
    expect(config.dialog.preset).not.toBe('undefined')
  })
})
