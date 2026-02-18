/**
 * useAppToast - Wrapper unificado para notificaciones toast
 *
 * Proporciona una API simplificada y consistente sobre PrimeVue Toast.
 * Sustituye llamadas directas a `toast.add()` en toda la app.
 *
 * @example
 * // Métodos semánticos (operaciones CRUD)
 * toast.created('Nueva entidad añadida')
 * toast.saved('Cambios guardados correctamente')
 * toast.updated('Entidad actualizada')
 * toast.deleted('Alerta eliminada')
 *
 * // Operaciones de archivo
 * toast.exported('Alertas exportadas como CSV')
 * toast.imported('Trabajo editorial importado')
 *
 * // Genéricos (fallback)
 * toast.success('Operación completada')
 * toast.error('No se pudo conectar con el servidor')
 */

import { useToast } from 'primevue/usetoast'
import type { ToastMessageOptions } from 'primevue/toast'

export interface AppToastOptions {
  /** Duración en ms (default: varía según severity) */
  life?: number
  /** Permite cerrar manualmente (default: true) */
  closable?: boolean
  /** Grupo de toast (default: undefined) */
  group?: string
}

export function useAppToast() {
  const toast = useToast()

  // ==========================================
  // OPERACIONES CRUD (5 métodos)
  // ==========================================

  /**
   * Notificación de creación (entidades, reglas, enlaces, proyectos)
   * @example toast.created('Nueva entidad añadida al proyecto')
   */
  function created(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Creado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de guardado
   * Usar para: guardar cambios, exportar, aplicar configuración
   * @example toast.saved('Cambios guardados correctamente')
   * @example toast.saved('Alertas exportadas como CSV')
   * @example toast.saved('Configuración aplicada')
   */
  function saved(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Guardado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de actualización (modificación de existente)
   * @example toast.updated('Entidad actualizada correctamente')
   */
  function updated(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Actualizado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de eliminación
   * @example toast.deleted('Alerta eliminada permanentemente')
   */
  function deleted(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'info',
      summary: 'Eliminado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de restauración
   * Usar para: undo, recuperar, importar
   * @example toast.restored('Entidad restaurada desde papelera')
   * @example toast.restored('Trabajo editorial importado correctamente')
   */
  function restored(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Restaurado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  // ==========================================
  // OPERACIONES ESPECIALES (2 métodos)
  // ==========================================

  /**
   * Notificación de fusión de entidades
   * @example toast.merged('2 entidades fusionadas en "Personaje Principal"')
   */
  function merged(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Fusionado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de separación (deshacer fusión)
   * @example toast.separated('Fusión deshecha, entidades restauradas')
   */
  function separated(message: string, options?: AppToastOptions) {
    toast.add({
      severity: 'success',
      summary: 'Separado',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  // ==========================================
  // GENÉRICOS (5 métodos)
  // ==========================================

  /**
   * Notificación de éxito genérica
   * @example toast.success('Operación completada correctamente')
   */
  function success(message: string, options?: AppToastOptions & { summary?: string }) {
    toast.add({
      severity: 'success',
      summary: options?.summary ?? 'Éxito',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de error
   * @example toast.error('No se pudo conectar con el servidor')
   */
  function error(message: string, options?: AppToastOptions & { summary?: string }) {
    toast.add({
      severity: 'error',
      summary: options?.summary ?? 'Error',
      detail: message,
      life: options?.life ?? 5000, // Errores duran más
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de advertencia
   * @example toast.warn('El archivo es muy grande, puede tardar')
   */
  function warn(message: string, options?: AppToastOptions & { summary?: string }) {
    toast.add({
      severity: 'warn',
      summary: options?.summary ?? 'Advertencia',
      detail: message,
      life: options?.life ?? 4000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación informativa
   * @example toast.info('Se requiere reiniciar para aplicar cambios')
   */
  function info(message: string, options?: AppToastOptions & { summary?: string }) {
    toast.add({
      severity: 'info',
      summary: options?.summary ?? 'Información',
      detail: message,
      life: options?.life ?? 3000,
      closable: options?.closable ?? true,
      group: options?.group,
    } as ToastMessageOptions)
  }

  /**
   * Notificación de operación en progreso
   * Retorna objeto para actualizar/cerrar dinámicamente
   * @example
   * const loader = toast.loading('Analizando documento...')
   * loader.update('Procesando capítulo 5 de 45...')
   * loader.done('Análisis completado')
   */
  function loading(message: string, options?: AppToastOptions) {
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
    // CRUD (5)
    created,
    saved,
    updated,
    deleted,
    restored,
    // Especiales (2)
    merged,
    separated,
    // Genéricos (5)
    success,
    error,
    warn,
    info,
    loading,
    clear,
  }
}
