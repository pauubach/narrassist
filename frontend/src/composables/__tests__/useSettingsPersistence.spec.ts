import { nextTick } from 'vue'
import {
  useSettingsPersistence,
  waitForPendingAnalysisSettingsSync,
} from '../useSettingsPersistence'

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({
    add: vi.fn(),
  }),
}))

vi.mock('@/stores/theme', () => ({
  useThemeStore: () => ({
    resetToDefaults: vi.fn(),
  }),
}))

vi.mock('@/utils/safeStorage', () => ({
  safeSetItem: vi.fn(() => true),
  safeGetItem: vi.fn(() => null),
}))

vi.mock('@/services/projects', () => ({
  getProject: vi.fn(),
  updateProjectSettings: vi.fn(async () => ({ settings: {}, runtime_warnings: [] })),
}))

import { safeSetItem } from '@/utils/safeStorage'
import { getProject, updateProjectSettings } from '@/services/projects'
import { safeGetItem } from '@/utils/safeStorage'

const mockSafeSetItem = safeSetItem as unknown as ReturnType<typeof vi.fn>
const mockGetProject = getProject as unknown as ReturnType<typeof vi.fn>
const mockSafeGetItem = safeGetItem as unknown as ReturnType<typeof vi.fn>
const mockUpdateProjectSettings = updateProjectSettings as unknown as ReturnType<typeof vi.fn>

describe('useSettingsPersistence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('saveSettings no persiste settings de análisis en localStorage', async () => {
    const { settings, saveSettings } = useSettingsPersistence()

    settings.value.multiModelSynthesis = false
    settings.value.characterKnowledgeMode = 'hybrid'
    settings.value.enabledNLPMethods.coreference = ['heuristics']
    saveSettings()
    await nextTick()

    expect(mockSafeSetItem).toHaveBeenCalledTimes(1)
    const payloadRaw = mockSafeSetItem.mock.calls[0][1] as string
    const payload = JSON.parse(payloadRaw)
    expect(payload.multiModelSynthesis).toBeUndefined()
    expect(payload.characterKnowledgeMode).toBeUndefined()
    expect(payload.enabledNLPMethods).toBeUndefined()
  })

  it('loadAnalysisSettingsFromBackend aplica analysis_features al estado local', async () => {
    mockGetProject.mockResolvedValue({
      settings: {
        analysis_features: {
          schema_version: 1,
          pipeline_flags: {
            multi_model_voting: false,
          },
          nlp_methods: {
            coreference: ['heuristics'],
            ner: ['spacy'],
            grammar: ['spacy_rules'],
            spelling: ['patterns', 'symspell'],
            character_knowledge: ['llm'],
          },
          updated_at: null,
          updated_by: 'api',
        },
      },
    })

    const { settings, loadAnalysisSettingsFromBackend } = useSettingsPersistence()
    const ok = await loadAnalysisSettingsFromBackend(7)

    expect(ok).toBe(true)
    expect(settings.value.enabledNLPMethods.coreference).toEqual(['heuristics'])
    expect(settings.value.enabledNLPMethods.spelling).toEqual(['patterns', 'symspell'])
    expect(settings.value.multiModelSynthesis).toBe(false)
    expect(settings.value.characterKnowledgeMode).toBe('llm')
  })

  it('loadSettings ignora analysis settings legacy guardados en localStorage', () => {
    mockSafeGetItem.mockReturnValue(
      JSON.stringify({
        theme: 'dark',
        enabledNLPMethods: {
          coreference: ['llm'],
          ner: ['llm'],
          grammar: ['llm'],
          spelling: ['beto'],
          character_knowledge: ['hybrid'],
        },
        multiModelSynthesis: false,
        characterKnowledgeMode: 'hybrid',
      }),
    )

    const { settings, loadSettings } = useSettingsPersistence()
    loadSettings()

    expect(settings.value.theme).toBe('dark')
    expect(settings.value.enabledNLPMethods.coreference).toEqual([
      'embeddings',
      'morpho',
      'heuristics',
    ])
    expect(settings.value.multiModelSynthesis).toBe(true)
    expect(settings.value.characterKnowledgeMode).toBe('rules')
  })

  it('waitForPendingAnalysisSettingsSync espera a sync en curso', async () => {
    let resolvePatch: (value: { settings: object; runtime_warnings: string[] }) => void = () => undefined
    mockUpdateProjectSettings.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePatch = resolve
        }),
    )

    const { syncAnalysisSettingsToBackend } = useSettingsPersistence()
    const syncPromise = syncAnalysisSettingsToBackend(42)
    const waitPromise = waitForPendingAnalysisSettingsSync(42)

    expect(mockUpdateProjectSettings).toHaveBeenCalledTimes(1)

    resolvePatch({ settings: {}, runtime_warnings: [] })

    await expect(waitPromise).resolves.toBe(true)
    await expect(syncPromise).resolves.toBe(true)
    await expect(waitForPendingAnalysisSettingsSync(42)).resolves.toBe(true)
  })
})
