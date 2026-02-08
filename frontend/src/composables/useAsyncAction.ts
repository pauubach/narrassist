/**
 * Composable DRY para acciones async con loading/error.
 *
 * Elimina el boilerplate repetido en 40+ workspace tabs:
 *   loading.value = true
 *   error.value = null
 *   try { ... }
 *   catch (err) { error.value = err.message; console.error(...) }
 *   finally { loading.value = false }
 *
 * @example
 *   const { loading, error, run } = useAsyncAction()
 *
 *   async function analyze() {
 *     await run(async () => {
 *       report.value = await api.getChecked<Report>(url)
 *     }, 'Error al analizar')
 *   }
 *
 * @example Con toast:
 *   await run(
 *     async () => { ... },
 *     'Error al guardar',
 *     { toast, toastDetail: 'No se pudo guardar la configuración' }
 *   )
 */

import { ref, type Ref } from 'vue'

interface RunOptions {
  toast?: { add: (opts: { severity: string; summary: string; detail: string; life: number }) => void }
  toastDetail?: string
}

export function useAsyncAction(
  externalLoading?: Ref<boolean>,
  externalError?: Ref<string | null>,
) {
  const loading = externalLoading ?? ref(false)
  const error = externalError ?? ref<string | null>(null)

  async function run<T>(
    action: () => Promise<T>,
    fallbackMessage = 'Error desconocido',
    options?: RunOptions,
  ): Promise<T | undefined> {
    loading.value = true
    error.value = null

    try {
      const result = await action()
      return result
    } catch (err) {
      const msg = err instanceof Error ? err.message : fallbackMessage
      error.value = msg
      console.error(`[AsyncAction] ${fallbackMessage}:`, err)

      if (options?.toast) {
        options.toast.add({
          severity: 'error',
          summary: 'Error',
          detail: options.toastDetail || msg,
          life: 3000,
        })
      }

      return undefined
    } finally {
      loading.value = false
    }
  }

  return { loading, error, run }
}
