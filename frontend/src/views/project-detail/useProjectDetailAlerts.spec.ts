import { computed } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Alert } from '@/types'

const { postRawMock, patchMock } = vi.hoisted(() => ({
  postRawMock: vi.fn(),
  patchMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    postRaw: postRawMock,
    patch: patchMock,
  },
}))

import { useProjectDetailAlerts } from './useProjectDetailAlerts'

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: 11,
    message: 'Alerta',
    title: 'Alerta importante',
    severity: 'medium',
    category: 'consistency',
    status: 'active',
    chapter: 1,
    chapterNumber: 1,
    highlightedText: null,
    extraData: null,
    sourceType: 'manual',
    metadata: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  } as Alert
}

describe('useProjectDetailAlerts', () => {
  const loadAlerts = vi.fn().mockResolvedValue(undefined)
  const clearSelection = vi.fn()
  const addToast = vi.fn()
  const projectId = computed(() => 7)

  beforeEach(() => {
    vi.clearAllMocks()
    postRawMock.mockResolvedValue({})
    patchMock.mockResolvedValue({})
  })

  it('resolves an alert, reloads data and clears selection', async () => {
    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.onAlertResolve(makeAlert())

    expect(postRawMock).toHaveBeenCalledWith('/api/projects/7/alerts/11/resolve')
    expect(loadAlerts).toHaveBeenCalledWith(7)
    expect(clearSelection).toHaveBeenCalled()
    expect(addToast).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      summary: 'Resuelta',
    }))
  })

  it('dismisses an alert and reports failures with toast', async () => {
    postRawMock.mockRejectedValueOnce(new Error('boom'))

    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.onAlertDismiss(makeAlert())

    expect(addToast).toHaveBeenCalledWith({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo descartar la alerta',
      life: 3000,
    })
    expect(loadAlerts).not.toHaveBeenCalled()
  })

  it('resolves ambiguous attributes and handles null entity assignment', async () => {
    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.onResolveAmbiguousAttribute(makeAlert(), null)

    expect(postRawMock).toHaveBeenCalledWith('/api/projects/7/alerts/11/resolve-attribute', {
      entity_id: null,
    })
    expect(addToast).toHaveBeenCalledWith({
      severity: 'success',
      summary: 'Resuelto',
      detail: 'Atributo no asignado',
      life: 3000,
    })
  })

  it('updates alert status and notifies history listeners', async () => {
    const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent')

    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.handleAlertAction(makeAlert(), 'accept')

    expect(patchMock).toHaveBeenCalledWith('/api/projects/7/alerts/11/status', {
      status: 'resolved',
    })
    expect(dispatchEventSpy).toHaveBeenCalledWith(expect.objectContaining({
      type: 'history:changed',
    }))
    expect(addToast).toHaveBeenCalledWith({
      severity: 'success',
      summary: 'Alerta aceptada',
      life: 2000,
    })
  })

  it('resolves all active alerts and clears selection through the shared reload path', async () => {
    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.onResolveAll()

    expect(postRawMock).toHaveBeenCalledWith('/api/projects/7/alerts/resolve-all')
    expect(loadAlerts).toHaveBeenCalledWith(7)
    expect(clearSelection).toHaveBeenCalled()
    expect(addToast).toHaveBeenCalledWith({
      severity: 'success',
      summary: 'Resueltas',
      detail: 'Todas las alertas activas han sido resueltas',
      life: 3000,
    })
  })

  it('sends batch resolutions using suggested entities and reports success', async () => {
    const alertsState = useProjectDetailAlerts({
      projectId,
      loadAlerts,
      clearSelection,
      addToast,
    })

    await alertsState.onBatchResolveAmbiguous([
      makeAlert({
        id: 21,
        extraData: { suggestedEntityId: 9 } as Alert['extraData'],
      }),
      makeAlert({
        id: 22,
        extraData: undefined,
      }),
    ])

    expect(postRawMock).toHaveBeenCalledWith('/api/projects/7/alerts/batch-resolve-attributes', {
      resolutions: [
        { alert_id: 21, entity_id: 9 },
        { alert_id: 22, entity_id: null },
      ],
    })
    expect(loadAlerts).toHaveBeenCalledWith(7)
    expect(clearSelection).toHaveBeenCalled()
    expect(addToast).toHaveBeenCalledWith({
      severity: 'success',
      summary: 'Resueltas',
      detail: '2 alertas ambiguas resueltas con sugerencia',
      life: 3000,
    })
  })
})
