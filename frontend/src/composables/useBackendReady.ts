import { watch } from 'vue'
import { useSystemStore } from '@/stores/system'

/** Timeout (ms) para esperar al backend antes de rechazar */
const BACKEND_TIMEOUT_MS = 65_000

/**
 * Espera a que el backend esté listo antes de hacer llamadas API.
 *
 * Uso:
 *   import { ensureBackendReady } from '@/composables/useBackendReady'
 *   await ensureBackendReady()
 */
export async function ensureBackendReady(): Promise<void> {
  const systemStore = useSystemStore()
  if (systemStore.backendReady) return

  return new Promise((resolve, reject) => {
    let settled = false

    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      unwatch()
      reject(new Error('Backend no disponible después de 65s de espera'))
    }, BACKEND_TIMEOUT_MS)

    const unwatch = watch(() => systemStore.backendReady, (ready) => {
      if (ready && !settled) {
        settled = true
        clearTimeout(timer)
        unwatch()
        resolve()
      }
    }, { immediate: true })
  })
}
