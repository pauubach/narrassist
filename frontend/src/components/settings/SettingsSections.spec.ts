import { computed, defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisSection from './AnalysisSection.vue'
import SemanticAnalyzerSection from './SemanticAnalyzerSection.vue'
import DetectionMethodsSection from './DetectionMethodsSection.vue'
import CorrectionsSection from './CorrectionsSection.vue'
import DataMaintenanceSection from './DataMaintenanceSection.vue'
import LicenseSection from './LicenseSection.vue'
import { nlpMethodsKey, ollamaKey, settingsKey, sensitivityKey } from './settingsInjection'

const {
  toastAddMock,
  apiMock,
  safeGetItemMock,
  safeSetItemMock,
  systemStoreMock,
  licenseStoreMock,
} = vi.hoisted(() => ({
  toastAddMock: vi.fn(),
  apiMock: {
    getRaw: vi.fn(),
    postRaw: vi.fn(),
    del: vi.fn(),
  },
  safeGetItemMock: vi.fn(),
  safeSetItemMock: vi.fn(),
  systemStoreMock: {
    systemCapabilities: {
      hardware: {
        has_gpu: false,
        gpu: null,
        gpu_blocked: null,
        cpu: { name: 'CPU de prueba' },
      },
    },
    downloadModels: vi.fn(),
    modelsError: null as string | null,
  },
  licenseStoreMock: {
    isLicensed: false,
    tierDisplayName: 'Profesional',
    quotaStatus: null as null | { unlimited: boolean; pages_used: number; pages_max: number },
    quotaWarningLevel: 'none',
  },
}))

vi.mock('@/services/apiClient', () => ({ api: apiMock }))
vi.mock('@/utils/safeStorage', () => ({
  safeGetItem: safeGetItemMock,
  safeSetItem: safeSetItemMock,
}))
vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAddMock }),
}))
vi.mock('@/stores/system', () => ({
  useSystemStore: () => systemStoreMock,
}))
vi.mock('@/stores/license', () => ({
  useLicenseStore: () => licenseStoreMock,
}))

const ButtonStub = defineComponent({
  name: 'PButton',
  props: ['label', 'ariaLabel', 'disabled'],
  emits: ['click'],
  template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label || ariaLabel || "button" }}</button>',
})

const ToggleSwitchStub = defineComponent({
  name: 'ToggleSwitch',
  props: ['modelValue', 'inputId', 'ariaLabel', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: '<button class="toggle-switch" :data-input-id="inputId" :disabled="disabled" @click="$emit(\'update:modelValue\', !modelValue); $emit(\'change\')">{{ inputId || ariaLabel || "toggle" }}</button>',
})

const SliderStub = defineComponent({
  name: 'Slider',
  props: ['modelValue'],
  emits: ['update:modelValue', 'change'],
  template: '<div class="slider-stub" @click="$emit(\'update:modelValue\', modelValue); $emit(\'change\')"></div>',
})

const TagStub = defineComponent({
  name: 'Tag',
  props: ['value'],
  template: '<span class="tag-stub">{{ value }}</span>',
})

const MessageStub = defineComponent({
  name: 'Message',
  template: '<div class="message-stub"><slot /></div>',
})

const DividerStub = defineComponent({
  name: 'Divider',
  template: '<hr class="divider-stub">',
})

const SelectStub = defineComponent({
  name: 'PSelect',
  props: ['modelValue', 'options', 'optionLabel', 'optionValue'],
  emits: ['update:modelValue', 'change'],
  methods: {
    nextValue() {
      const options = (this as any).options || []
      const candidate = options[1] ?? options[0]
      if (!candidate) return undefined
      const key = (this as any).optionValue || 'value'
      return candidate[key] ?? candidate.id ?? candidate.value
    },
  },
  template: '<select class="select-stub" @change="$emit(\'update:modelValue\', nextValue()); $emit(\'change\')"><option v-for="(opt, index) in options || []" :key="index">{{ opt[optionLabel || "label"] || opt.label || opt.name }}</option></select>',
})

const DsDownloadProgressStub = defineComponent({
  name: 'DsDownloadProgress',
  props: ['label'],
  template: '<div class="download-progress">{{ label }}</div>',
})

const CorrectionDefaultsManagerStub = defineComponent({
  name: 'CorrectionDefaultsManager',
  template: '<div class="defaults-manager-stub"></div>',
})

const MethodCardStub = defineComponent({
  name: 'MethodCard',
  props: ['category', 'methodKey', 'method', 'enabled'],
  emits: ['toggle'],
  template: '<button class="method-card-stub" @click="$emit(\'toggle\', !enabled)">{{ category }}:{{ methodKey }}:{{ method.name }}</button>',
})

const baseSettings = () => ref({
  sensitivityPreset: 'balanceado',
  sensitivity: 50,
  minConfidence: 70,
  inferenceMinConfidence: 60,
  inferenceMinConsensus: 70,
  autoAnalysis: true,
  showPartialResults: true,
  notifyAnalysisComplete: true,
  soundEnabled: true,
  qualityLevel: 'rapida',
  llmSensitivity: 5,
  enabledNLPMethods: {
    coreference: ['rules'],
    ner: ['spacy'],
    grammar: ['rules'],
    spelling: ['patterns'],
    character_knowledge: ['rules'],
  },
  characterKnowledgeMode: 'rules',
})

const baseGlobal = (provide: Record<PropertyKey, unknown> = {}) => ({
  global: {
    provide,
    stubs: {
      Button: ButtonStub,
      ToggleSwitch: ToggleSwitchStub,
      Slider: SliderStub,
      Tag: TagStub,
      Message: MessageStub,
      Divider: DividerStub,
      Select: SelectStub,
      DsDownloadProgress: DsDownloadProgressStub,
      CorrectionDefaultsManager: CorrectionDefaultsManagerStub,
      MethodCard: MethodCardStub,
    },
    directives: {
      tooltip: {
        mounted: () => {},
        updated: () => {},
        unmounted: () => {},
      },
    },
  },
})

describe('settings sections refactor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    safeGetItemMock.mockReturnValue(null)
    safeSetItemMock.mockReturnValue(true)
    apiMock.getRaw.mockReset()
    apiMock.postRaw.mockReset()
    apiMock.del.mockReset()
    systemStoreMock.downloadModels.mockReset()
    systemStoreMock.modelsError = null
    systemStoreMock.systemCapabilities = {
      hardware: {
        has_gpu: false,
        gpu: null,
        gpu_blocked: null,
        cpu: { name: 'CPU de prueba' },
      },
    }
    licenseStoreMock.isLicensed = false
    licenseStoreMock.quotaStatus = null
    licenseStoreMock.quotaWarningLevel = 'none'
  })

  it('AnalysisSection wires presets and toggle handlers through injected contexts', async () => {
    const settings = baseSettings()
    const onSettingChange = vi.fn()
    const selectSensitivityPreset = vi.fn()

    const wrapper = mount(AnalysisSection, baseGlobal({
      [settingsKey as symbol]: { settings, onSettingChange, saveSettings: vi.fn() },
      [sensitivityKey as symbol]: {
        sensitivityPresets: [
          { value: 'conservador', label: 'Conservador', description: 'Menos avisos', icon: 'pi pi-shield', recommended: false },
          { value: 'balanceado', label: 'Balanceado', description: 'Equilibrado', icon: 'pi pi-balance-scale', recommended: true },
        ],
        showAdvancedSensitivity: ref(false),
        sensitivityLabel: computed(() => 'Equilibrado'),
        selectSensitivityPreset,
        onSensitivityChange: vi.fn(),
        onAdvancedSliderChange: vi.fn(),
        recalculateFromSensitivity: vi.fn(),
      },
    }))

    await wrapper.get('.preset-button').trigger('click')
    expect(selectSensitivityPreset).toHaveBeenCalledWith('conservador')

    const firstToggle = wrapper.findComponent({ name: 'ToggleSwitch' })
    firstToggle.vm.$emit('change')
    expect(onSettingChange).toHaveBeenCalled()
  })

  it('SemanticAnalyzerSection emits quality changes and executes ollama action', async () => {
    const settings = baseSettings()
    const actionSpy = vi.fn()
    const ollamaState = ref('ready')

    const wrapper = mount(SemanticAnalyzerSection, {
      ...baseGlobal({
        [settingsKey as symbol]: { settings, onSettingChange: vi.fn(), saveSettings: vi.fn() },
        [ollamaKey as symbol]: {
          ollamaState,
          ollamaActionConfig: computed(() => ({ label: 'Iniciar', icon: 'pi pi-play', severity: 'secondary', action: actionSpy })),
          ollamaStatusMessage: computed(() => 'Listo'),
          ollamaStarting: ref(false),
          modelDownloading: ref(false),
          ollamaDownloadProgress: ref({ percentage: 50 }),
          installModel: vi.fn(),
        },
      }),
      props: {
        qualityLevels: [
          { value: 'rapida', label: 'Rapida', description: 'Rapida', icon: 'pi pi-bolt', available: true, recommended: true, reason: null, estimate: '1 min' },
        ],
        qualityLevelDownloading: false,
        loadingCapabilities: false,
      },
    })

    await wrapper.get('.quality-level-card').trigger('click')
    expect(wrapper.emitted('selectQualityLevel')).toEqual([['rapida']])

    ollamaState.value = 'not_running'
    await wrapper.vm.$nextTick()
    await wrapper.get('button').trigger('click')
    expect(actionSpy).toHaveBeenCalledTimes(1)
  })

  it('DetectionMethodsSection wires method toggles and recommended config', async () => {
    const settings = baseSettings()
    const toggleMethod = vi.fn()
    const setCharacterKnowledgeMode = vi.fn()
    const applyRecommendedConfig = vi.fn()

    const methodsByCategory = {
      coreference: { rules: { name: 'Rules', available: true } },
      ner: { spacy: { name: 'spaCy', available: true } },
      grammar: { rules: { name: 'Rules', available: true } },
      spelling: { patterns: { name: 'Patterns', available: true, weight: 0.5 } },
      character_knowledge: {
        rules: { name: 'Rules', description: 'Reglas', available: true },
        llm: { name: 'LLM', description: 'LLM', available: true },
      },
    } as Record<string, Record<string, any>>

    const wrapper = mount(DetectionMethodsSection, {
      ...baseGlobal({
        [settingsKey as symbol]: { settings, onSettingChange: vi.fn(), saveSettings: vi.fn() },
        [nlpMethodsKey as symbol]: {
          gpuRequirementTooltip: computed(() => 'GPU'),
          getNLPMethodsForCategory: (category: string) => methodsByCategory[category] || {},
          isMethodEnabled: (_category: string, key: string) => key !== 'llm',
          toggleMethod,
          setCharacterKnowledgeMode,
          applyRecommendedConfig,
        },
      }),
      props: {
        ltActionConfig: { label: 'Instalar', icon: 'pi pi-download', severity: 'secondary', action: vi.fn() },
        ltStatusMessage: 'No disponible',
        ltInstalling: false,
        ltStarting: false,
        ltInstallProgress: null,
        ltState: 'not_installed',
      },
    })

    expect(wrapper.findAll('.method-card-stub')).toHaveLength(4)

    await wrapper.findAll('.method-card-stub')[0].trigger('click')
    expect(toggleMethod).toHaveBeenCalledWith('coreference', 'rules', false)

    await wrapper.find('.knowledge-mode-card:not(.selected)').trigger('click')
    expect(setCharacterKnowledgeMode).toHaveBeenCalledWith('llm')

    const applyButton = wrapper.findAll('button').find(button => button.text().includes('Aplicar recomendada'))
    expect(applyButton).toBeDefined()
    await applyButton!.trigger('click')
    expect(applyRecommendedConfig).toHaveBeenCalledTimes(1)
  })

  it('CorrectionsSection loads presets and persists the selected default preset', async () => {
    apiMock.getRaw.mockResolvedValue({
      success: true,
      data: {
        presets: [
          {
            id: 'default',
            name: 'General',
            description: 'Preset general',
            config: {
              profile: { document_field: 'general', register: 'standard', audience: 'adult' },
              typography: { enabled: true, dialogue_dash: 'em_dash', quote_style: 'spanish' },
              repetition: { enabled: true, min_distance: 40, sensitivity: 'medium' },
              regional: { enabled: true, target_region: 'es_ES' },
            },
          },
          {
            id: 'literary',
            name: 'Literario',
            description: 'Preset literario',
            config: {
              profile: { document_field: 'fiction', register: 'formal', audience: 'adult' },
              typography: { enabled: true, dialogue_dash: 'em_dash', quote_style: 'spanish' },
              repetition: { enabled: true, min_distance: 60, sensitivity: 'high' },
              regional: { enabled: true, target_region: 'es_AR' },
            },
          },
        ],
        options: {
          regions: [
            { value: 'es_ES', label: 'Espana' },
            { value: 'es_AR', label: 'Argentina' },
          ],
        },
      },
    })
    safeGetItemMock.mockImplementation((key: string) => {
      if (key === 'defaultCorrectionPreset') return 'default'
      if (key === 'defaultCorrectionRegion') return 'es_ES'
      if (key === 'useLLMReview') return 'false'
      return null
    })

    const wrapper = mount(CorrectionsSection, baseGlobal())
    await (wrapper.vm as unknown as { loadCorrectionPresets: () => Promise<void> }).loadCorrectionPresets()

    expect(wrapper.text()).toContain('Resumen de configuración')
    expect(wrapper.text()).toContain('Perfil de documento')

    await wrapper.get('.select-stub').trigger('change')
    expect(safeSetItemMock).toHaveBeenCalledWith('defaultCorrectionPreset', 'literary')
  })

  it('DataMaintenanceSection emits actions and restores rejected entities', async () => {
    systemStoreMock.downloadModels.mockResolvedValue(true)
    apiMock.getRaw.mockResolvedValue({
      success: true,
      data: [
        {
          id: 1,
          entityName: 'Alicia',
          entityType: 'character',
          reason: 'No es una entidad',
          rejectedAt: '2026-03-08T00:00:00Z',
        },
      ],
    })
    apiMock.del.mockResolvedValue({ success: true })

    const wrapper = mount(DataMaintenanceSection, {
      ...baseGlobal(),
      props: { dataLocation: 'D:/NarrAssist' },
    })

    const changeButton = wrapper.findAll('button').find(button => button.text().includes('Cambiar ubicación'))
    const resetButton = wrapper.findAll('button').find(button => button.text().includes('Restablecer'))
    expect(changeButton).toBeDefined()
    expect(resetButton).toBeDefined()
    await changeButton!.trigger('click')
    expect(wrapper.emitted('changeDataLocation')).toBeTruthy()

    await (wrapper.vm as unknown as { loadUserRejections: () => Promise<void> }).loadUserRejections()
    expect(wrapper.text()).toContain('Alicia')

    const restoreButton = wrapper.findAll('button').find(button => button.text().includes('Restaurar entidad rechazada Alicia'))
    expect(restoreButton).toBeDefined()
    await restoreButton!.trigger('click')
    expect(apiMock.del).toHaveBeenCalledWith('/api/entity-filters/user-rejections/1')
    expect(wrapper.text()).not.toContain('Alicia')

    await resetButton!.trigger('click')
    expect(wrapper.emitted('confirmReset')).toBeTruthy()
  })

  it('LicenseSection reflects licensed and unlicensed states', () => {
    licenseStoreMock.isLicensed = false
    let wrapper = mount(LicenseSection, baseGlobal())
    expect(wrapper.text()).toContain('Sin licencia activa')
    expect(wrapper.text()).toContain('Activar licencia')

    licenseStoreMock.isLicensed = true
    licenseStoreMock.tierDisplayName = 'Profesional'
    licenseStoreMock.quotaStatus = { unlimited: false, pages_used: 15, pages_max: 100 }
    licenseStoreMock.quotaWarningLevel = 'warning'
    wrapper = mount(LicenseSection, baseGlobal())
    expect(wrapper.text()).toContain('Plan Profesional activo')
    expect(wrapper.text()).toContain('Gestionar licencia')
    expect(wrapper.text()).toContain('15 / 100 páginas')
  })
})
