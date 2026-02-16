import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { diffWords } from 'diff'

export interface DiffSegment {
  value: string
  type: 'unchanged' | 'removed' | 'added'
}

/**
 * Composable que calcula diff a nivel de palabra entre dos textos.
 * Usa jsdiff (diffWords) para generar segmentos con tipo unchanged/removed/added.
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

  return { segments, hasChanges }
}
