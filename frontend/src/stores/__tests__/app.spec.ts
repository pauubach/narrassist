import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const listenMock = vi.fn()
const invokeMock = vi.fn()

vi.mock('@tauri-apps/api/event', () => ({
  listen: listenMock,
}))

vi.mock('@tauri-apps/api/core', () => ({
  invoke: invokeMock,
}))

type BackendStatusPayload = {
  status: string
  message: string
}

describe('appStore', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    setActivePinia(createPinia())

    Object.defineProperty(window, '__TAURI__', {
      value: {},
      configurable: true,
    })
  })

  afterEach(() => {
    delete (window as Window & { __TAURI__?: unknown }).__TAURI__
  })

  async function loadStores() {
    const { useAppStore } = await import('../app')
    const { useSystemStore } = await import('../system')
    const appStore = useAppStore()
    const systemStore = useSystemStore()
    await vi.dynamicImportSettled()
    await Promise.resolve()
    return { appStore, systemStore }
  }

  it('marks backend as running when the sidecar reports running', async () => {
    let handler: ((event: { payload: unknown }) => void) | undefined
    listenMock.mockImplementation(async (_event: string, cb: (event: { payload: unknown }) => void) => {
      handler = cb
      return () => {}
    })

    const { systemStore } = await loadStores()

    expect(handler).toBeTypeOf('function')
    handler!({
      payload: {
        status: 'running',
        message: 'Servidor listo',
      } satisfies BackendStatusPayload,
    })

    expect(systemStore.backendConnected).toBe(true)
    expect(systemStore.backendStartupError).toBeNull()
  })

  it('marks backend as disconnected while starting or restarting', async () => {
    let handler: ((event: { payload: unknown }) => void) | undefined
    listenMock.mockImplementation(async (_event: string, cb: (event: { payload: unknown }) => void) => {
      handler = cb
      return () => {}
    })

    const { systemStore } = await loadStores()
    systemStore.backendConnected = true
    systemStore.backendStartupError = 'old error'

    handler!({
      payload: {
        status: 'starting',
        message: 'Iniciando...',
      } satisfies BackendStatusPayload,
    })

    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBeNull()

    systemStore.backendConnected = true
    systemStore.backendStartupError = 'old error'

    handler!({
      payload: {
        status: 'restarting',
        message: 'Reiniciando...',
      } satisfies BackendStatusPayload,
    })

    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBeNull()
  })

  it('stores startup error and enables retry flow when the sidecar reports error', async () => {
    let handler: ((event: { payload: unknown }) => void) | undefined
    listenMock.mockImplementation(async (_event: string, cb: (event: { payload: unknown }) => void) => {
      handler = cb
      return () => {}
    })

    const { systemStore } = await loadStores()
    const retrySpy = vi.spyOn(systemStore, 'startRetrying').mockImplementation(() => {})

    handler!({
      payload: {
        status: 'error',
        message: 'No se pudo iniciar el backend',
      } satisfies BackendStatusPayload,
    })

    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBe('No se pudo iniciar el backend')
    expect(retrySpy).toHaveBeenCalledTimes(1)
  })

  it('covers the desktop shell lifecycle from startup to restart and terminal failure', async () => {
    let handler: ((event: { payload: unknown }) => void) | undefined
    listenMock.mockImplementation(async (_event: string, cb: (event: { payload: unknown }) => void) => {
      handler = cb
      return () => {}
    })
    invokeMock.mockResolvedValue('Backend server started successfully')

    const { appStore, systemStore } = await loadStores()
    const retrySpy = vi.spyOn(systemStore, 'startRetrying').mockImplementation(() => {})

    const startResult = await appStore.startBackendServer()
    expect(startResult).toBe('Backend server started successfully')
    expect(handler).toBeTypeOf('function')

    handler!({
      payload: {
        status: 'starting',
        message: 'Iniciando...',
      } satisfies BackendStatusPayload,
    })
    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBeNull()

    handler!({
      payload: {
        status: 'running',
        message: 'Servidor listo',
      } satisfies BackendStatusPayload,
    })
    expect(systemStore.backendConnected).toBe(true)
    expect(systemStore.backendStartupError).toBeNull()

    handler!({
      payload: {
        status: 'restarting',
        message: 'Reiniciando...',
      } satisfies BackendStatusPayload,
    })
    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBeNull()

    handler!({
      payload: {
        status: 'running',
        message: 'Servidor listo',
      } satisfies BackendStatusPayload,
    })
    expect(systemStore.backendConnected).toBe(true)
    expect(systemStore.backendStartupError).toBeNull()

    handler!({
      payload: {
        status: 'error',
        message: 'Backend detenido inesperadamente',
      } satisfies BackendStatusPayload,
    })
    expect(systemStore.backendConnected).toBe(false)
    expect(systemStore.backendStartupError).toBe('Backend detenido inesperadamente')
    expect(retrySpy).toHaveBeenCalledTimes(1)
  })

  it('invokes the Tauri command to start the backend server', async () => {
    listenMock.mockResolvedValue(() => {})
    invokeMock.mockResolvedValue('Backend server started successfully')

    const { appStore } = await loadStores()
    const result = await appStore.startBackendServer()

    expect(invokeMock).toHaveBeenCalledWith('start_backend_server')
    expect(result).toBe('Backend server started successfully')
  })

  it('maps start_backend_server failures to a user-facing startup error', async () => {
    listenMock.mockResolvedValue(() => {})
    invokeMock.mockRejectedValue(new Error('spawn failed'))

    const { appStore, systemStore } = await loadStores()
    const result = await appStore.startBackendServer()

    expect(result).toBeNull()
    expect(systemStore.backendStartupError).toBe('spawn failed')
  })
})
