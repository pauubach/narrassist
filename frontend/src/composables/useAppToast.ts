/**
 * useAppToast - Wrapper unificado para notificaciones toast
 *
 * Proporciona una API simplificada y consistente sobre PrimeVue Toast.
 * Sustituye llamadas directas a `toast.add()` en toda la app.
 */

import { useToast } from 'primevue/usetoast'
import type { ToastMessageOptions } from 'primevue/toast'

export interface AppToastOptions {
  /** Duración en ms (default: 3000) */
  life?: number
  /** Permite cerrar manualmente (default: true) */
  closable?: boolean
  /** Grupo de toast (default: undefined) */
  group?: string
}

export function useAppToast() {
  const toast = useToast()

  /**
   * Notificación de éxito
   */
  function success(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Éxito',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de error
   */
  function error(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
      life: options?.life ?? 5000, // Errores duran más
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de advertencia
   */
  function warn(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'warn',
      summary: 'Advertencia',
      detail: message,
      life: options?.life ?? 4000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación informativa
   */
  function info(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'info',
      summary: 'Información',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de operación en progreso
   * Retorna función para actualizar/cerrar
   */
  function loading(message: string, options?: AppToastOptions) {
    const id = Date.now().toString()

    toast.add({
      severity: 'info',
      summary: 'Procesando',
      detail: message,
      life: options?.life ?? 0, // No se cierra automáticamente
      closable: options?.closable ?? false,
      group: options?.group ?? 'loading',
    } as ToastMessageOptions)

    return {
      /** Actualizar mensaje */
      update: (newMessage: string) => {
        toast.removeGroup('loading')
        toast.add({
          severity: 'info',
          summary: 'Procesando',
          detail: newMessage,
          life: 0,
          closable: false,
          group: 'loading',
        } as ToastMessageOptions)
      },
      /** Cerrar con éxito */
      done: (successMessage?: string) => {
        toast.removeGroup('loading')
        if (successMessage) {
          success(successMessage)
        }
      },
      /** Cerrar con error */
      fail: (errorMessage?: string) => {
        toast.removeGroup('loading')
        if (errorMessage) {
          error(errorMessage)
        }
      },
    }
  }

  /**
   * Limpiar todos los toasts
   */
  function clear() {
    toast.removeAllGroups()
  }

  return {
    success,
    error,
    warn,
    info,
    loading,
    clear,
  }
}
