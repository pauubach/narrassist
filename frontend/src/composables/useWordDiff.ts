import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { diffWords } from 'diff'

export interface DiffSegment {
  value: string
  type: 'unchanged' | 'removed' | 'added'
}

/**
 * Composable que calcula diff a nivel de palabra entre dos textos.
 * Usa jsdiff (diffWords) para generar segmentos con tipo unchanged/removed/added.
 *
 * isDiffMeaningful indica si hay suficiente solapamiento entre original y propuesta
 * para que el diff tenga sentido visual. Si es false, la sugerencia es probablemente
 * una instrucción editorial (ej. "Fusione este párrafo...") y no un texto corregido.
 */
export function useWordDiff(
  original: MaybeRefOrGetter<string>,
  proposed: MaybeRefOrGetter<string>
) {
  const segments = computed<DiffSegment[]>(() => {
    const orig = toValue(original)
    const prop = toValue(proposed)
    if (!orig || !prop) return []

    return diffWords(orig, prop).map(part => ({
      value: part.value,
      type: part.added ? 'added' : part.removed ? 'removed' : 'unchanged'
    }))
  })

  const hasChanges = computed(() =>
    segments.value.some(s => s.type !== 'unchanged')
  )

  /** Ratio de texto sin cambios respecto al total. Si <20%, el diff no aporta. */
  const isDiffMeaningful = computed(() => {
    const segs = segments.value
    if (segs.length === 0) return false
    const unchangedLen = segs
      .filter(s => s.type === 'unchanged')
      .reduce((acc, s) => acc + s.value.length, 0)
    const totalLen = segs.reduce((acc, s) => acc + s.value.length, 0)
    return totalLen > 0 && (unchangedLen / totalLen) >= 0.2
  })

  return { segments, hasChanges, isDiffMeaningful }
}
