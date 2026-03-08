import type { Ref } from 'vue'
import { api } from '@/services/apiClient'
import type { Alert } from '@/types'

type ToastSeverity = 'success' | 'info' | 'error'

type ToastAdd = (message: {
  severity: ToastSeverity
  summary: string
  detail?: string
  life: number
}) => void

interface UseProjectDetailAlertsOptions {
  projectId: Ref<number | null>
  loadAlerts: (projectId: number, forceReload?: boolean) => Promise<void>
  clearSelection: () => void
  addToast: ToastAdd
}

export function useProjectDetailAlerts(options: UseProjectDetailAlertsOptions) {
  const getProjectId = () => options.projectId.value

  const reloadAlerts = async (projectId: number) => {
    await options.loadAlerts(projectId)
    options.clearSelection()
  }

  const onAlertResolve = async (alert: Alert) => {
    const projectId = getProjectId()
    if (!projectId) return

    try {
      await api.postRaw(`/api/projects/${projectId}/alerts/${alert.id}/resolve`)
      await reloadAlerts(projectId)
      options.addToast({
        severity: 'success',
        summary: 'Resuelta',
        detail: alert.title || `Alerta #${alert.id} resuelta`,
        life: 3000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo resolver la alerta',
        life: 3000,
      })
    }
  }

  const onAlertDismiss = async (alert: Alert) => {
    const projectId = getProjectId()
    if (!projectId) return

    try {
      await api.postRaw(`/api/projects/${projectId}/alerts/${alert.id}/dismiss`)
      await reloadAlerts(projectId)
      options.addToast({
        severity: 'info',
        summary: 'Descartada',
        detail: alert.title || `Alerta #${alert.id} descartada`,
        life: 3000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo descartar la alerta',
        life: 3000,
      })
    }
  }

  const onResolveAmbiguousAttribute = async (alert: Alert, entityId: number | null) => {
    const projectId = getProjectId()
    if (!projectId) return

    try {
      await api.postRaw(`/api/projects/${projectId}/alerts/${alert.id}/resolve-attribute`, {
        entity_id: entityId,
      })
      await reloadAlerts(projectId)
      options.addToast({
        severity: 'success',
        summary: 'Resuelto',
        detail: entityId === null ? 'Atributo no asignado' : 'Atributo asignado correctamente',
        life: 3000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo resolver el atributo ambiguo',
        life: 3000,
      })
    }
  }

  const onResolveAll = async () => {
    const projectId = getProjectId()
    if (!projectId) return

    try {
      await api.postRaw(`/api/projects/${projectId}/alerts/resolve-all`)
      await reloadAlerts(projectId)
      options.addToast({
        severity: 'success',
        summary: 'Resueltas',
        detail: 'Todas las alertas activas han sido resueltas',
        life: 3000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudieron resolver las alertas',
        life: 3000,
      })
    }
  }

  const onBatchResolveAmbiguous = async (alertsToResolve: Alert[]) => {
    const projectId = getProjectId()
    if (!projectId) return

    try {
      const resolutions = alertsToResolve.map((alert) => ({
        alert_id: alert.id,
        entity_id: alert.extraData?.suggestedEntityId ?? null,
      }))
      await api.postRaw(`/api/projects/${projectId}/alerts/batch-resolve-attributes`, {
        resolutions,
      })
      await reloadAlerts(projectId)
      options.addToast({
        severity: 'success',
        summary: 'Resueltas',
        detail: `${alertsToResolve.length} alertas ambiguas resueltas con sugerencia`,
        life: 3000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudieron resolver las alertas',
        life: 3000,
      })
    }
  }

  const handleAlertAction = async (alert: Alert, action: 'accept' | 'reject') => {
    const projectId = getProjectId()
    if (!projectId) return

    const newStatus = action === 'accept' ? 'resolved' : 'dismissed'

    try {
      await api.patch(`/api/projects/${projectId}/alerts/${alert.id}/status`, {
        status: newStatus,
      })
      await options.loadAlerts(projectId)
      window.dispatchEvent(new CustomEvent('history:changed', {
        detail: { projectId, alertId: alert.id },
      }))
      options.addToast({
        severity: 'success',
        summary: action === 'accept' ? 'Alerta aceptada' : 'Alerta rechazada',
        life: 2000,
      })
    } catch {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: `No se pudo ${action === 'accept' ? 'aceptar' : 'rechazar'} la alerta`,
        life: 3000,
      })
    }
  }

  return {
    onAlertResolve,
    onAlertDismiss,
    onResolveAmbiguousAttribute,
    onResolveAll,
    onBatchResolveAmbiguous,
    handleAlertAction,
  }
}
