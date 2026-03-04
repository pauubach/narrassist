/**
 * Crea una función "ensure" para auto-configuración de arranque.
 *
 * Garantías:
 * - Deduplica llamadas concurrentes.
 * - Una vez completada con éxito, no vuelve a ejecutar.
 * - Si falla, permite reintento en la siguiente llamada.
 */
export function createEnsureAutoConfig(
  autoConfigTask: () => Promise<void>,
): () => Promise<void> {
  let pending: Promise<void> | null = null
  let completed = false

  return async () => {
    if (completed) return

    if (!pending) {
      pending = autoConfigTask()
        .then(() => {
          completed = true
        })
        .finally(() => {
          pending = null
        })
    }

    try {
      await pending
    } catch {
      // Best-effort: los errores no deben bloquear el flujo de setup.
    }
  }
}

