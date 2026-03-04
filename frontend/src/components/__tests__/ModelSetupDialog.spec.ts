import { nextTick, reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import ModelSetupDialog from '../ModelSetupDialog.vue'

const h = vi.hoisted(() => ({
  store: null as any,
  showNotification: vi.fn(),
  downloadModel: vi.fn(),
  apiGetRaw: vi.fn(),
}))

vi.mock('@/stores/system', () => ({
  useSystemStore: () => h.store,
}))

vi.mock('@/composables/useNotifications', () => ({
  useNotifications: () => ({
    showNotification: h.showNotification,
  }),
}))

vi.mock('@/composables/useOllamaManagement', () => ({
  useOllamaManagement: () => ({
    downloadModel: h.downloadModel,
    ollamaDownloadProgress: { value: null },
  }),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: h.apiGetRaw,
  },
}))

function createSystemStore(overrides: Record<string, unknown> = {}) {
  return reactive({
    downloadProgress: {},
    modelsStatus: { nlp_models: {} },
    modelSizes: { total: 0 },
    modelsReady: false,
    modelsError: null,
    pythonAvailable: true,
    dependenciesNeeded: false,
    backendLoaded: true,
    dependenciesInstalling: false,
    waitForBackend: vi.fn().mockResolvedValue(true),
    loadCapabilities: vi.fn().mockResolvedValue(null),
    checkModelsStatus: vi.fn().mockResolvedValue(null),
    autoConfigOnStartup: vi.fn().mockResolvedValue(undefined),
    downloadModels: vi.fn().mockResolvedValue(true),
    installDependencies: vi.fn().mockResolvedValue(true),
    stopPolling: vi.fn(),
    ...overrides,
  })
}

function mountDialog() {
  return shallowMount(ModelSetupDialog, {
    global: {
      stubs: {
        Dialog: { template: '<div><slot /></div>' },
        DsDownloadProgress: true,
      },
    },
  })
}

describe('ModelSetupDialog (CR-06 orchestration)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    h.store = createSystemStore()
    h.downloadModel.mockResolvedValue(true)
    h.apiGetRaw.mockResolvedValue({
      data: {
        ready: true,
        ollama_running: false,
        missing_models: [],
      },
    })
  })

  it('ejecuta autoConfig al volverse modelsReady tras instalación inicial', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(0)

    h.store.modelsReady = true
    await nextTick()
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })

  it('ejecuta autoConfig una vez cuando modelsReady ya era true al montar', async () => {
    h.store = createSystemStore({ modelsReady: true })

    const wrapper = mountDialog()
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })

  it('retryStartup ejecuta autoConfig cuando el backend se recupera y modelsReady=true', async () => {
    h.store = createSystemStore({
      waitForBackend: vi
        .fn()
        .mockResolvedValueOnce(false)
        .mockResolvedValueOnce(true),
      checkModelsStatus: vi.fn().mockImplementation(async () => {
        h.store.modelsReady = true
      }),
    })

    const wrapper = mountDialog()
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(0)

    await wrapper.find('button.retry-button').trigger('click')
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })

  it('recheckPython ejecuta autoConfig cuando Python aparece y modelsReady=true', async () => {
    h.store = createSystemStore({
      pythonAvailable: false,
      checkModelsStatus: vi
        .fn()
        .mockImplementationOnce(async () => {})
        .mockImplementationOnce(async () => {
          h.store.pythonAvailable = true
          h.store.modelsReady = true
        }),
    })

    const wrapper = mountDialog()
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(0)

    await wrapper.find('button.retry-button.secondary').trigger('click')
    await flushPromises()

    expect(h.store.autoConfigOnStartup).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })
})
