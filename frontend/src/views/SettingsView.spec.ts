import { computed, defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  routerGoMock,
  toastAddMock,
  apiMock,
  settingsState,
  loadSettingsMock,
  saveSettingsMock,
  onSettingChangeMock,
  onSliderChangeMock,
  applyDefaultsFromCapabilitiesMock,
  resetSettingsMock,
  loadAnalysisSettingsFromBackendMock,
  syncAnalysisSettingsToBackendMock,
  cleanupPersistenceMock,
  selectSensitivityPresetMock,
  onSensitivityChangeMock,
  onAdvancedSliderChangeMock,
  recalculateFromSensitivityMock,
  installModelMock,
  ollamaCleanupMock,
  toggleMethodMock,
  setCharacterKnowledgeModeMock,
  applyRecommendedConfigMock,
  systemStoreMock,
  licenseStoreMock,
  projectsStoreMock,
  safeGetItemMock,
  loadCorrectionPresetsMock,
  loadUserRejectionsMock,
} = vi.hoisted(() => ({
  routerGoMock: vi.fn(),
  toastAddMock: vi.fn(),
  apiMock: {
    get: vi.fn(),
    getRaw: vi.fn(),
    postRaw: vi.fn(),
    put: vi.fn(),
  },
  settingsState: {
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
    multiModelSynthesis: false,
  },
  loadSettingsMock: vi.fn(),
  saveSettingsMock: vi.fn(),
  onSettingChangeMock: vi.fn(),
  onSliderChangeMock: vi.fn(),
  applyDefaultsFromCapabilitiesMock: vi.fn(),
  resetSettingsMock: vi.fn(),
  loadAnalysisSettingsFromBackendMock: vi.fn(),
  syncAnalysisSettingsToBackendMock: vi.fn(),
  cleanupPersistenceMock: vi.fn(),
  selectSensitivityPresetMock: vi.fn(),
  onSensitivityChangeMock: vi.fn(),
  onAdvancedSliderChangeMock: vi.fn(),
  recalculateFromSensitivityMock: vi.fn(),
  installModelMock: vi.fn(),
  ollamaCleanupMock: vi.fn(),
  toggleMethodMock: vi.fn(),
  setCharacterKnowledgeModeMock: vi.fn(),
  applyRecommendedConfigMock: vi.fn(),
  systemStoreMock: {
    systemCapabilities: {
      detection_status: 'ready',
      detection_warnings: [],
      languagetool: { running: false, installed: false },
    },
    capabilitiesLoading: false,
    ltInstalling: false,
    ltStarting: false,
    ltInstallProgress: null,
    ltState: 'not_installed',
    modelsError: null,
    loadCapabilities: vi.fn(),
    installLanguageTool: vi.fn(),
    startLanguageTool: vi.fn(),
    stopLTPolling: vi.fn(),
  },
  licenseStoreMock: {
    isLicensed: false,
    tierDisplayName: 'Profesional',
    quotaStatus: null,
    quotaWarningLevel: 'none',
  },
  projectsStoreMock: {
    currentProject: { id: 42 },
  },
  safeGetItemMock: vi.fn(),
  loadCorrectionPresetsMock: vi.fn(),
  loadUserRejectionsMock: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ go: routerGoMock }),
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAddMock }),
}))

vi.mock('@/services/apiClient', () => ({
  api: apiMock,
}))

vi.mock('@/stores/system', () => ({
  useSystemStore: () => systemStoreMock,
}))

vi.mock('@/stores/license', () => ({
  useLicenseStore: () => licenseStoreMock,
}))

vi.mock('@/stores/projects', () => ({
  useProjectsStore: () => projectsStoreMock,
}))

vi.mock('@/utils/safeStorage', () => ({
  safeGetItem: safeGetItemMock,
}))

vi.mock('@/composables/useSettingsPersistence', () => ({
  useSettingsPersistence: () => ({
    settings: ref(settingsState),
    loadSettings: loadSettingsMock,
    saveSettings: saveSettingsMock,
    onSettingChange: onSettingChangeMock,
    onSliderChange: onSliderChangeMock,
    applyDefaultsFromCapabilities: applyDefaultsFromCapabilitiesMock,
    resetSettings: resetSettingsMock,
    loadAnalysisSettingsFromBackend: loadAnalysisSettingsFromBackendMock,
    syncAnalysisSettingsToBackend: syncAnalysisSettingsToBackendMock,
    cleanup: cleanupPersistenceMock,
  }),
}))

vi.mock('@/composables/useSensitivityPresets', () => ({
  useSensitivityPresets: () => ({
    sensitivityPresets: [],
    showAdvancedSensitivity: ref(false),
    sensitivityLabel: computed(() => 'Equilibrado'),
    selectSensitivityPreset: selectSensitivityPresetMock,
    onSensitivityChange: onSensitivityChangeMock,
    onAdvancedSliderChange: onAdvancedSliderChangeMock,
    recalculateFromSensitivity: recalculateFromSensitivityMock,
  }),
}))

vi.mock('@/composables/useOllamaManagement', () => ({
  useOllamaManagement: () => ({
    ollamaState: ref('ready'),
    ollamaActionConfig: computed(() => ({
      label: 'Iniciar',
      icon: 'pi pi-play',
      severity: 'secondary',
      action: vi.fn(),
    })),
    ollamaStatusMessage: computed(() => 'Listo'),
    ollamaStarting: ref(false),
    modelDownloading: ref(false),
    ollamaDownloadProgress: ref(null),
    installModel: installModelMock,
    cleanup: ollamaCleanupMock,
  }),
}))

vi.mock('@/composables/useNLPMethods', () => ({
  useNLPMethods: () => ({
    gpuRequirementTooltip: computed(() => 'GPU'),
    getNLPMethodsForCategory: () => ({}),
    isMethodEnabled: () => true,
    toggleMethod: toggleMethodMock,
    setCharacterKnowledgeMode: setCharacterKnowledgeModeMock,
    applyRecommendedConfig: applyRecommendedConfigMock,
  }),
}))

vi.mock('@/components/settings/AppearanceSection.vue', () => ({
  default: { name: 'AppearanceSection', template: '<div data-test="appearance-section">appearance</div>' },
}))

vi.mock('@/components/settings/AnalysisSection.vue', () => ({
  default: { name: 'AnalysisSection', template: '<div data-test="analysis-section">analysis</div>' },
}))

vi.mock('@/components/settings/SemanticAnalyzerSection.vue', () => ({
  default: { name: 'SemanticAnalyzerSection', template: '<div data-test="semantic-section">semantic</div>' },
}))

vi.mock('@/components/settings/DetectionMethodsSection.vue', () => ({
  default: { name: 'DetectionMethodsSection', template: '<div data-test="detection-section">detection</div>' },
}))

vi.mock('@/components/settings/CorrectionsSection.vue', () => ({
  default: defineComponent({
    name: 'CorrectionsSection',
    setup(_props, { expose }) {
      expose({ loadCorrectionPresets: loadCorrectionPresetsMock })
      return () => h('div', { 'data-test': 'corrections-section' }, 'corrections')
    },
  }),
}))

vi.mock('@/components/settings/DataMaintenanceSection.vue', () => ({
  default: defineComponent({
    name: 'DataMaintenanceSection',
    props: {
      dataLocation: {
        type: String,
        default: '',
      },
    },
    emits: ['changeDataLocation', 'confirmReset'],
    setup(props, { emit, expose }) {
      expose({ loadUserRejections: loadUserRejectionsMock })
      return () => h('div', { 'data-test': 'maintenance-section' }, [
        h('span', { 'data-test': 'data-location-prop' }, props.dataLocation),
        h('button', {
          'data-test': 'maintenance-change-location',
          onClick: () => emit('changeDataLocation'),
        }, 'Cambiar ubicación'),
        h('button', {
          'data-test': 'maintenance-confirm-reset',
          onClick: () => emit('confirmReset'),
        }, 'Restablecer'),
      ])
    },
  }),
}))

vi.mock('@/components/settings/LicenseSection.vue', () => ({
  default: defineComponent({
    name: 'LicenseSection',
    emits: ['showLicenseDialog'],
    setup(_props, { emit }) {
      return () => h('button', {
        'data-test': 'show-license-dialog',
        onClick: () => emit('showLicenseDialog'),
      }, 'Licencia')
    },
  }),
}))

vi.mock('@/components/LicenseDialog.vue', () => ({
  default: defineComponent({
    name: 'LicenseDialog',
    props: {
      visible: {
        type: Boolean,
        default: false,
      },
    },
    emits: ['update:visible', 'activated'],
    setup(props) {
      return () => props.visible
        ? h('div', { 'data-test': 'license-dialog' }, 'license dialog')
        : null
    },
  }),
}))

import SettingsView from './SettingsView.vue'

const ButtonStub = defineComponent({
  name: 'Button',
  props: ['label', 'icon', 'disabled', 'loading'],
  emits: ['click'],
  template: '<button :disabled="disabled || loading" @click="$emit(\'click\')">{{ label || icon || "button" }}</button>',
})

const CardStub = defineComponent({
  name: 'Card',
  template: '<section class="card-stub"><div class="card-title"><slot name="title" /></div><div class="card-content"><slot name="content" /></div></section>',
})

const DialogStub = defineComponent({
  name: 'Dialog',
  props: ['visible', 'header'],
  emits: ['update:visible'],
  template: '<div v-if="visible" class="dialog-stub"><h2>{{ header }}</h2><slot /><footer><slot name="footer" /></footer></div>',
})

const TagStub = defineComponent({
  name: 'Tag',
  props: ['value'],
  template: '<span class="tag-stub">{{ value }}</span>',
})

const InputTextStub = defineComponent({
  name: 'InputText',
  props: ['modelValue', 'placeholder'],
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" :placeholder="placeholder">',
})

const ToggleSwitchStub = defineComponent({
  name: 'ToggleSwitch',
  props: ['modelValue', 'inputId', 'ariaLabel'],
  emits: ['update:modelValue', 'change'],
  template: '<button :data-testid="inputId || ariaLabel" @click="$emit(\'update:modelValue\', !modelValue); $emit(\'change\')">{{ inputId || ariaLabel || "toggle" }}</button>',
})

const MessageStub = defineComponent({
  name: 'Message',
  template: '<div class="message-stub"><slot /></div>',
})

function mountView() {
  return mount(SettingsView, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: CardStub,
        Dialog: DialogStub,
        Tag: TagStub,
        InputText: InputTextStub,
        ToggleSwitch: ToggleSwitchStub,
        Message: MessageStub,
      },
    },
  })
}

describe('SettingsView refactor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(settingsState, {
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
      multiModelSynthesis: false,
    })
    systemStoreMock.capabilitiesLoading = false
    systemStoreMock.ltInstalling = false
    systemStoreMock.ltStarting = false
    systemStoreMock.ltInstallProgress = null
    systemStoreMock.ltState = 'not_installed'
    systemStoreMock.systemCapabilities = {
      detection_status: 'ready',
      detection_warnings: [],
      languagetool: { running: false, installed: false },
    }
    systemStoreMock.loadCapabilities.mockResolvedValue(systemStoreMock.systemCapabilities)
    systemStoreMock.installLanguageTool.mockResolvedValue(true)
    systemStoreMock.startLanguageTool.mockResolvedValue(true)
    safeGetItemMock.mockReturnValue(null)
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/services/llm/hardware') return { levels: [] }
      if (path.startsWith('/api/services/llm/estimates')) return { estimates: {} }
      if (path === '/api/services/llm/config') return { qualityLevel: 'rapida', sensitivity: 5 }
      throw new Error(`Unexpected GET ${path}`)
    })
    apiMock.getRaw.mockImplementation(async (path: string) => {
      if (path === '/api/maintenance/data-location') {
        return { success: true, data: { path: 'D:/NarrAssist' } }
      }
      throw new Error(`Unexpected GET RAW ${path}`)
    })
    apiMock.postRaw.mockResolvedValue({ success: true, data: { restart_required: false, migrated_items: [] } })
    apiMock.put.mockResolvedValue({})
    projectsStoreMock.currentProject = { id: 42 }
    licenseStoreMock.isLicensed = false
    licenseStoreMock.tierDisplayName = 'Profesional'
  })

  it('loads persisted settings, project analysis settings and child section data on mount', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(loadSettingsMock).toHaveBeenCalledTimes(1)
    expect(loadAnalysisSettingsFromBackendMock).toHaveBeenCalledWith(42)
    expect(systemStoreMock.loadCapabilities).toHaveBeenCalledWith(true)
    expect(loadCorrectionPresetsMock).toHaveBeenCalledTimes(1)
    expect(loadUserRejectionsMock).toHaveBeenCalledTimes(1)
    expect(apiMock.get).toHaveBeenCalledWith('/api/services/llm/hardware')
    expect(apiMock.getRaw).toHaveBeenCalledWith('/api/maintenance/data-location')
    expect(wrapper.get('[data-test=\"appearance-section\"]')).toBeTruthy()
    expect(wrapper.get('[data-test=\"corrections-section\"]')).toBeTruthy()
    expect(wrapper.get('[data-test=\"data-location-prop\"]').text()).toBe('D:/NarrAssist')
  })

  it('routes navigation and child section events to the correct dialogs', async () => {
    const wrapper = mountView()
    await flushPromises()

    const backButton = wrapper.findAll('button').find(button => button.text().includes('Volver'))
    expect(backButton).toBeDefined()
    await backButton!.trigger('click')
    expect(routerGoMock).toHaveBeenCalledWith(-1)

    await wrapper.get('[data-test=\"maintenance-change-location\"]').trigger('click')
    expect(wrapper.text()).toContain('Cambiar ubicación de datos')

    await wrapper.get('[data-test=\"maintenance-confirm-reset\"]').trigger('click')
    expect(wrapper.text()).toContain('Confirmar restablecimiento')

    await wrapper.get('[data-test=\"show-license-dialog\"]').trigger('click')
    expect(wrapper.get('[data-test=\"license-dialog\"]')).toBeTruthy()
  })
})
