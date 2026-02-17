import { ref, type ComponentPublicInstance, type Ref } from 'vue'

/**
 * Composable para navegación por teclado en listas (roving tabindex).
 *
 * Patrón ARIA estándar: solo el item enfocado tiene tabindex=0,
 * el resto tabindex=-1. Flechas ↑/↓ mueven el foco, Home/End saltan
 * al principio/final.
 *
 * Uso:
 * ```vue
 * <div @keydown="onKeydown">
 *   <button
 *     v-for="(item, i) in items"
 *     :ref="el => setItemRef(el, i)"
 *     :tabindex="getTabindex(i)"
 *     @focus="focusedIndex = i"
 *     @click="onSelect(item)"
 *   />
 * </div>
 * ```
 */
export function useListKeyboardNav(opts?: {
  /** Si true, ↓ desde el último item vuelve al primero */
  wrap?: boolean
  /** Orientación: 'vertical' usa ↑/↓, 'horizontal' usa ←/→, 'both' ambos */
  orientation?: 'vertical' | 'horizontal' | 'both'
}) {
  const wrap = opts?.wrap ?? true
  const orientation = opts?.orientation ?? 'vertical'

  const focusedIndex = ref(-1) as Ref<number>
  const itemRefs: (HTMLElement | null)[] = []

  function setItemRef(el: Element | ComponentPublicInstance | null, index: number) {
    // Vue template refs pueden ser Element o ComponentPublicInstance
    // Extraemos el $el si es un componente, sino usamos el elemento directamente
    if (el && '$el' in el) {
      itemRefs[index] = el.$el as HTMLElement | null
    } else {
      itemRefs[index] = el as HTMLElement | null
    }
  }

  function getTabindex(index: number): number {
    // Si nada está enfocado, el primer item es tabbable
    if (focusedIndex.value === -1 && index === 0) return 0
    return focusedIndex.value === index ? 0 : -1
  }

  function focusItem(index: number) {
    const el = itemRefs[index]
    if (el) {
      focusedIndex.value = index
      el.focus()
    }
  }

  function onKeydown(event: KeyboardEvent) {
    const count = itemRefs.filter(el => el !== null).length
    if (count === 0) return

    const isUp = orientation !== 'horizontal' && event.key === 'ArrowUp'
    const isDown = orientation !== 'horizontal' && event.key === 'ArrowDown'
    const isLeft = orientation !== 'vertical' && event.key === 'ArrowLeft'
    const isRight = orientation !== 'vertical' && event.key === 'ArrowRight'
    const isPrev = isUp || isLeft
    const isNext = isDown || isRight

    if (isPrev) {
      event.preventDefault()
      if (focusedIndex.value <= 0) {
        focusItem(wrap ? count - 1 : 0)
      } else {
        focusItem(focusedIndex.value - 1)
      }
    } else if (isNext) {
      event.preventDefault()
      if (focusedIndex.value >= count - 1) {
        focusItem(wrap ? 0 : count - 1)
      } else {
        focusItem(focusedIndex.value + 1)
      }
    } else if (event.key === 'Home') {
      event.preventDefault()
      focusItem(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      focusItem(count - 1)
    }
  }

  /** Limpiar refs cuando la lista cambia */
  function resetRefs() {
    itemRefs.length = 0
    focusedIndex.value = -1
  }

  return {
    focusedIndex,
    setItemRef,
    getTabindex,
    onKeydown,
    focusItem,
    resetRefs,
  }
}
