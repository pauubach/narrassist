import { buildPatchFromLocalStorage, migrateLocalStorageSettingsToBackend } from '../useSettingsMigration'

vi.mock('@/utils/safeStorage', () => ({
  safeGetItem: vi.fn(),
}))

vi.mock('@/services/projects', () => ({
  getProject: vi.fn(),
  updateProjectSettings: vi.fn(),
}))

import { safeGetItem } from '@/utils/safeStorage'
import { getProject, updateProjectSettings } from '@/services/projects'

const mockSafeGetItem = safeGetItem as unknown as ReturnType<typeof vi.fn>
const mockGetProject = getProject as unknown as ReturnType<typeof vi.fn>
const mockUpdateProjectSettings = updateProjectSettings as unknown as ReturnType<typeof vi.fn>

describe('useSettingsMigration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('buildPatchFromLocalStorage usa defaults seguros para categorías ausentes', () => {
    const raw = JSON.stringify({
      enabledNLPMethods: {
        grammar: ['spacy_rules'],
      },
      multiModelSynthesis: true,
    })

    const patch = buildPatchFromLocalStorage(raw)
    expect(patch).not.toBeNull()

    const features = patch!.analysis_features
    expect(features.pipeline_flags.grammar).toBe(true)
    expect(features.pipeline_flags.spelling).toBe(true)
    expect(features.pipeline_flags.multi_model_voting).toBe(true)
    expect(features.nlp_methods.spelling).toContain('patterns')
    expect(features.nlp_methods.coreference).toContain('embeddings')
  })

  it('buildPatchFromLocalStorage respeta categorías vacías explícitas', () => {
    const raw = JSON.stringify({
      enabledNLPMethods: {
        grammar: [],
        spelling: [],
      },
    })

    const patch = buildPatchFromLocalStorage(raw)
    expect(patch).not.toBeNull()
    expect(patch!.analysis_features.nlp_methods.grammar).toEqual([])
    expect(patch!.analysis_features.nlp_methods.spelling).toEqual([])
    expect(patch!.analysis_features.pipeline_flags.grammar).toBe(false)
    expect(patch!.analysis_features.pipeline_flags.spelling).toBe(false)
  })

  it('forceSync omite check de backend y sincroniza settings', async () => {
    mockSafeGetItem.mockReturnValue(
      JSON.stringify({
        enabledNLPMethods: {
          grammar: ['spacy_rules'],
        },
      }),
    )
    mockUpdateProjectSettings.mockResolvedValue({})

    const migrated = await migrateLocalStorageSettingsToBackend(42, true)

    expect(migrated).toBe(true)
    expect(mockGetProject).not.toHaveBeenCalled()
    expect(mockUpdateProjectSettings).toHaveBeenCalledTimes(1)
    expect(mockUpdateProjectSettings).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        analysis_features: expect.any(Object),
      }),
    )
  })

  it('modo normal no sobreescribe backend ya configurado', async () => {
    mockGetProject.mockResolvedValue({
      settings: {
        analysis_features: {
          updated_by: 'api',
        },
      },
    })
    mockSafeGetItem.mockReturnValue(
      JSON.stringify({
        enabledNLPMethods: {
          grammar: ['spacy_rules'],
        },
      }),
    )

    const migrated = await migrateLocalStorageSettingsToBackend(99)

    expect(migrated).toBe(false)
    expect(mockGetProject).toHaveBeenCalledWith(99)
    expect(mockUpdateProjectSettings).not.toHaveBeenCalled()
  })
})
