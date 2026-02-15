/**
 * useGlobalUndo - Composable para deshacer acciones globalmente (Ctrl+Z).
 *
 * Conecta con el backend para deshacer la última acción registrada
 * en el historial del proyecto. Muestra un toast de feedback de 3 segundos.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { apiUrl } from '@/config/api'

export interface UndoResult {
  success: boolean
  entryId?: number
  message?: string
  conflicts?: string[]
}

export interface HistoryEntry {
  id: number
  projectId: number
  actionType: string
  targetType: string
  targetId: number | null
  note: string | null
  batchId: string | null
  isUndoable: boolean
  isUndone: boolean
  createdAt: string
  undoneAt: string | null
}

export function useGlobalUndo(projectId: () => number | null) {
  const undoing = ref(false)
  const lastUndoResult = ref<UndoResult | null>(null)
  const undoableCount = ref(0)
  const toast = useToast()

  /**
   * Deshace la última acción del proyecto (Ctrl+Z).
   */
  async function undoLast(): Promise<UndoResult> {
    const pid = projectId()
    if (!pid || undoing.value) {
      return { success: false, message: 'No hay proyecto activo' }
    }

    undoing.value = true
    try {
      const response = await fetch(apiUrl(`/api/projects/${pid}/undo`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const json = await response.json()

      if (json.success) {
        const result: UndoResult = {
          success: true,
          entryId: json.data?.entry_id,
          message: json.data?.message || json.message,
        }
        lastUndoResult.value = result

        toast.add({
          severity: 'info',
          summary: 'Acción deshecha',
          detail: result.message || 'Se ha deshecho la última acción',
          life: 3000,
        })

        // Actualizar conteo
        await fetchUndoableCount()

        // Notificar al resto de la app que se deshizo algo
        window.dispatchEvent(new CustomEvent('history:undo-complete', {
          detail: { projectId: pid, entryId: result.entryId },
        }))

        return result
      } else {
        const result: UndoResult = {
          success: false,
          message: json.error || 'No se pudo deshacer',
          conflicts: json.data?.conflicts,
        }
        lastUndoResult.value = result

        toast.add({
          severity: 'warn',
          summary: 'No se puede deshacer',
          detail: result.message,
          life: 3000,
        })

        return result
      }
    } catch (error) {
      const result: UndoResult = {
        success: false,
        message: 'Error de conexión al deshacer',
      }
      lastUndoResult.value = result

      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo conectar con el servidor',
        life: 3000,
      })

      return result
    } finally {
      undoing.value = false
    }
  }

  /**
   * Deshace una acción específica por ID.
   */
  async function undoEntry(entryId: number): Promise<UndoResult> {
    const pid = projectId()
    if (!pid) return { success: false, message: 'No hay proyecto activo' }

    undoing.value = true
    try {
      const response = await fetch(apiUrl(`/api/projects/${pid}/undo/${entryId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const json = await response.json()

      if (json.success) {
        const result: UndoResult = {
          success: true,
          entryId: json.data?.entry_id,
          message: json.data?.message || json.message,
        }

        toast.add({
          severity: 'info',
          summary: 'Acción deshecha',
          detail: result.message,
          life: 3000,
        })

        await fetchUndoableCount()
        window.dispatchEvent(new CustomEvent('history:undo-complete', {
          detail: { projectId: pid, entryId },
        }))

        return result
      } else {
        toast.add({
          severity: 'warn',
          summary: 'No se puede deshacer',
          detail: json.error || 'Acción no reversible',
          life: 3000,
        })
        return { success: false, message: json.error, conflicts: json.data?.conflicts }
      }
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo conectar con el servidor',
        life: 3000,
      })
      return { success: false, message: 'Error de conexión' }
    } finally {
      undoing.value = false
    }
  }

  /**
   * Deshace una operación compuesta (batch).
   */
  async function undoBatch(batchId: string): Promise<UndoResult> {
    const pid = projectId()
    if (!pid) return { success: false, message: 'No hay proyecto activo' }

    undoing.value = true
    try {
      const response = await fetch(apiUrl(`/api/projects/${pid}/undo-batch/${batchId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const json = await response.json()

      if (json.success) {
        toast.add({
          severity: 'info',
          summary: 'Operación deshecha',
          detail: json.data?.message || json.message,
          life: 3000,
        })

        await fetchUndoableCount()
        window.dispatchEvent(new CustomEvent('history:undo-complete', {
          detail: { projectId: pid, batchId },
        }))

        return { success: true, message: json.data?.message }
      } else {
        toast.add({
          severity: 'warn',
          summary: 'No se puede deshacer',
          detail: json.error,
          life: 3000,
        })
        return { success: false, message: json.error }
      }
    } catch {
      return { success: false, message: 'Error de conexión' }
    } finally {
      undoing.value = false
    }
  }

  /**
   * Obtiene el historial de acciones del proyecto.
   */
  async function fetchHistory(options?: {
    limit?: number
    offset?: number
    undoableOnly?: boolean
  }): Promise<HistoryEntry[]> {
    const pid = projectId()
    if (!pid) return []

    try {
      const params = new URLSearchParams()
      if (options?.limit) params.set('limit', String(options.limit))
      if (options?.offset) params.set('offset', String(options.offset))
      if (options?.undoableOnly) params.set('undoable_only', 'true')

      const url = apiUrl(`/api/projects/${pid}/history?${params}`)
      const response = await fetch(url)
      const json = await response.json()

      if (json.success && Array.isArray(json.data)) {
        return json.data.map(mapHistoryEntry)
      }
      return []
    } catch {
      return []
    }
  }

  /**
   * Obtiene el conteo de acciones pendientes de deshacer.
   */
  async function fetchUndoableCount(): Promise<number> {
    const pid = projectId()
    if (!pid) return 0

    try {
      const response = await fetch(apiUrl(`/api/projects/${pid}/history/count`))
      const json = await response.json()
      undoableCount.value = json.data?.count ?? 0
      return undoableCount.value
    } catch {
      return 0
    }
  }

  /**
   * Mapea un entry del backend al formato frontend.
   */
  function mapHistoryEntry(raw: Record<string, unknown>): HistoryEntry {
    return {
      id: raw.id as number,
      projectId: raw.project_id as number,
      actionType: raw.action_type as string,
      targetType: raw.target_type as string,
      targetId: raw.target_id as number | null,
      note: raw.note as string | null,
      batchId: raw.batch_id as string | null,
      isUndoable: raw.is_undoable as boolean,
      isUndone: raw.is_undone as boolean,
      createdAt: raw.created_at as string,
      undoneAt: raw.undone_at as string | null,
    }
  }

  // Handler para Ctrl+Z
  function handleKeydown(event: KeyboardEvent) {
    const { key, ctrlKey, metaKey, shiftKey } = event
    const modifier = ctrlKey || metaKey

    // Ignorar si el usuario está escribiendo en un input
    const target = event.target as HTMLElement
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      return
    }

    // No interceptar Ctrl+Z si el modo corrección secuencial está activo
    // (tiene su propio stack de undo local)
    if (document.querySelector('.sequential-mode')) {
      return
    }

    // Ctrl+Z: deshacer última acción
    if (modifier && !shiftKey && key === 'z') {
      event.preventDefault()
      undoLast()
    }
  }

  // Handler para evento de toggle del panel de historial (Ctrl+Shift+H)
  function handleToggleHistory() {
    window.dispatchEvent(new CustomEvent('sidebar:set-tab', { detail: { tab: 'history' } }))
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
    window.addEventListener('menubar:toggle-history', handleToggleHistory)
    // Cargar conteo inicial
    fetchUndoableCount()
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
    window.removeEventListener('menubar:toggle-history', handleToggleHistory)
  })

  return {
    undoing,
    lastUndoResult,
    undoableCount,
    undoLast,
    undoEntry,
    undoBatch,
    fetchHistory,
    fetchUndoableCount,
  }
}
