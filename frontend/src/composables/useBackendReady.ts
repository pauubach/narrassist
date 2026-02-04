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
    if (systemStore.backendReady) { resolve(); return }

    const unwatch = watch(() => systemStore.backendReady, (ready) => {
      if (ready) {
        unwatch()
        resolve()
      }
    })

    setTimeout(() => {
      unwatch()
      if (!systemStore.backendReady) {
        reject(new Error('Backend no disponible después de 65s de espera'))
      } else {
        resolve()
      }
    }, BACKEND_TIMEOUT_MS)
  })
}
