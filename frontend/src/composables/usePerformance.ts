/**
 * usePerformance - Utilidades de optimización de rendimiento
 *
 * Proporciona funciones reutilizables para:
 * - Debounce de funciones (evitar ejecuciones excesivas)
 * - Throttle de funciones (limitar frecuencia de ejecución)
 * - Refs con debounce reactivo
 */

import { ref, watch, type Ref, onUnmounted } from 'vue'

/**
 * Crea una versión debounced de una función
 * La función solo se ejecuta después de que pase el tiempo especificado
 * sin nuevas llamadas
 *
 * @param fn Función a debounce
 * @param delay Tiempo de espera en ms (default: 300ms)
 * @returns Función debounced
 */
export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number = 300
): T & { cancel: () => void } {
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const debouncedFn = ((...args: any[]) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      fn(...args)
      timeoutId = null
    }, delay)
  }) as T & { cancel: () => void }

  // Método para cancelar el debounce pendiente
  debouncedFn.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return debouncedFn
}

/**
 * Crea una versión throttled de una función
 * La función se ejecuta como máximo una vez cada `limit` ms
 *
 * @param fn Función a throttle
 * @param limit Intervalo mínimo entre ejecuciones en ms (default: 100ms)
 * @returns Función throttled
 */
export function throttle<T extends (...args: any[]) => void>(
  fn: T,
  limit: number = 100
): T {
  let lastRun = 0
  let lastArgs: any[] | null = null
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  return ((...args: any[]) => {
    const now = Date.now()

    if (now - lastRun >= limit) {
      // Ejecutar inmediatamente si ha pasado suficiente tiempo
      fn(...args)
      lastRun = now
    } else {
      // Guardar args para ejecutar al final del throttle
      lastArgs = args
      if (!timeoutId) {
        timeoutId = setTimeout(() => {
          if (lastArgs) {
            fn(...lastArgs)
            lastRun = Date.now()
            lastArgs = null
          }
          timeoutId = null
        }, limit - (now - lastRun))
      }
    }
  }) as T
}

/**
 * Composable para crear un ref con valor debounced
 * Útil para campos de búsqueda que no deben filtrar en cada tecla
 *
 * @param initialValue Valor inicial
 * @param delay Tiempo de debounce en ms (default: 300ms)
 * @returns { value, debouncedValue } - value es inmediato, debouncedValue es debounced
 */
export function useDebouncedRef<T>(initialValue: T, delay: number = 300) {
  const value = ref(initialValue) as Ref<T>
  const debouncedValue = ref(initialValue) as Ref<T>

  const updateDebounced = debounce((newValue: T) => {
    debouncedValue.value = newValue
  }, delay)

  watch(value, (newValue) => {
    updateDebounced(newValue)
  })

  // Cancelar debounce pendiente al desmontar
  onUnmounted(() => {
    updateDebounced.cancel()
  })

  return {
    value,
    debouncedValue
  }
}

/**
 * Composable para detectar si el usuario está scrolleando
 * Útil para diferir actualizaciones durante scroll
 *
 * @param delay Tiempo después del último scroll para considerar que terminó (default: 150ms)
 * @returns { isScrolling: Ref<boolean> }
 */
export function useScrollDetection(delay: number = 150) {
  const isScrolling = ref(false)
  let scrollTimeout: ReturnType<typeof setTimeout> | null = null

  const handleScroll = () => {
    isScrolling.value = true

    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }

    scrollTimeout = setTimeout(() => {
      isScrolling.value = false
    }, delay)
  }

  // Limpiar al desmontar
  onUnmounted(() => {
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }
    window.removeEventListener('scroll', handleScroll, true)
  })

  // Añadir listener global de scroll (capture para detectar en cualquier elemento)
  if (typeof window !== 'undefined') {
    window.addEventListener('scroll', handleScroll, true)
  }

  return {
    isScrolling
  }
}
