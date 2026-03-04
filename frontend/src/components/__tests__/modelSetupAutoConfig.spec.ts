import { createEnsureAutoConfig } from '../modelSetupAutoConfig'

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('createEnsureAutoConfig', () => {
  it('ejecuta solo una vez tras éxito en llamadas secuenciales', async () => {
    const task = vi.fn().mockResolvedValue(undefined)
    const ensure = createEnsureAutoConfig(task)

    await ensure()
    await ensure()
    await ensure()

    expect(task).toHaveBeenCalledTimes(1)
  })

  it('deduplica llamadas concurrentes', async () => {
    const gate = deferred<void>()
    const task = vi.fn().mockReturnValue(gate.promise)
    const ensure = createEnsureAutoConfig(task)

    const p1 = ensure()
    const p2 = ensure()
    const p3 = ensure()

    expect(task).toHaveBeenCalledTimes(1)

    gate.resolve()
    await Promise.all([p1, p2, p3])

    expect(task).toHaveBeenCalledTimes(1)
  })

  it('permite reintento después de error', async () => {
    const task = vi
      .fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(undefined)
    const ensure = createEnsureAutoConfig(task)

    await expect(ensure()).resolves.toBeUndefined()
    await expect(ensure()).resolves.toBeUndefined()

    expect(task).toHaveBeenCalledTimes(2)
  })

  it('no propaga errores al caller (best-effort)', async () => {
    const task = vi.fn().mockRejectedValue(new Error('fail'))
    const ensure = createEnsureAutoConfig(task)

    await expect(ensure()).resolves.toBeUndefined()
  })
})

