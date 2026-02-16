<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted, computed } from 'vue'
import Button from 'primevue/button'

/**
 * TextFindBar - Barra de búsqueda flotante para el tab de texto.
 *
 * Busca coincidencias en el contenido del documento (.chapter-text)
 * y las resalta con <mark> elements. Navegación con Enter/Shift+Enter.
 */

interface Props {
  visible: boolean
  container: HTMLElement | null
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const findInputRef = ref<HTMLInputElement | null>(null)
const query = ref('')
const currentIndex = ref(-1)
const totalMatches = ref(0)
const marks = ref<HTMLElement[]>([])

const matchLabel = computed(() => {
  if (!query.value) return ''
  if (totalMatches.value === 0) return 'Sin resultados'
  return `${currentIndex.value + 1} / ${totalMatches.value}`
})

// Focus input when visible
watch(() => props.visible, async (visible) => {
  if (visible) {
    await nextTick()
    findInputRef.value?.focus()
    findInputRef.value?.select()
  } else {
    clearHighlights()
    query.value = ''
  }
})

// Search when query changes (debounced)
let searchTimeout: ReturnType<typeof setTimeout> | null = null
watch(query, (newQuery) => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    performSearch(newQuery)
  }, 200)
})

function getSearchContainer(): HTMLElement | null {
  if (!props.container) return null
  return props.container.querySelector('.document-content') as HTMLElement
}

function clearHighlights() {
  const container = getSearchContainer()
  if (!container) return

  const existingMarks = container.querySelectorAll('mark.text-find-match')
  existingMarks.forEach(mark => {
    const parent = mark.parentNode
    if (parent) {
      while (mark.firstChild) {
        parent.insertBefore(mark.firstChild, mark)
      }
      parent.removeChild(mark)
      parent.normalize()
    }
  })

  marks.value = []
  totalMatches.value = 0
  currentIndex.value = -1
}

interface TextMatch {
  node: Text
  offset: number
  length: number
}

function performSearch(searchQuery: string) {
  clearHighlights()

  if (!searchQuery || searchQuery.length < 2) return

  const container = getSearchContainer()
  if (!container) return

  const lowerQuery = searchQuery.toLowerCase()

  // Collect all matches across all chapter-text elements
  const allMatches: TextMatch[] = []
  const chapterTexts = container.querySelectorAll('.chapter-text')

  chapterTexts.forEach(chapterText => {
    const walker = document.createTreeWalker(chapterText, NodeFilter.SHOW_TEXT)

    while (walker.nextNode()) {
      const node = walker.currentNode as Text
      const text = (node.textContent || '').toLowerCase()
      let pos = 0

      while (true) {
        const idx = text.indexOf(lowerQuery, pos)
        if (idx === -1) break
        allMatches.push({ node, offset: idx, length: searchQuery.length })
        pos = idx + 1
      }
    }
  })

  // Wrap matches from end to start to avoid offset invalidation
  const foundMarks: HTMLElement[] = new Array(allMatches.length)

  for (let i = allMatches.length - 1; i >= 0; i--) {
    const { node, offset, length } = allMatches[i]
    try {
      const range = document.createRange()
      range.setStart(node, offset)
      range.setEnd(node, offset + length)

      const mark = document.createElement('mark')
      mark.className = 'text-find-match'
      range.surroundContents(mark)
      foundMarks[i] = mark
    } catch {
      // Skip matches that cross element boundaries
    }
  }

  // Filter out undefined entries from skipped matches
  marks.value = foundMarks.filter(Boolean)
  totalMatches.value = marks.value.length

  if (marks.value.length > 0) {
    currentIndex.value = 0
    scrollToMatch(0)
  }
}

function scrollToMatch(index: number) {
  marks.value.forEach(m => m.classList.remove('text-find-current'))

  if (index >= 0 && index < marks.value.length) {
    const mark = marks.value[index]
    mark.classList.add('text-find-current')
    mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function goToNext() {
  if (totalMatches.value === 0) return
  currentIndex.value = (currentIndex.value + 1) % totalMatches.value
  scrollToMatch(currentIndex.value)
}

function goToPrevious() {
  if (totalMatches.value === 0) return
  currentIndex.value = (currentIndex.value - 1 + totalMatches.value) % totalMatches.value
  scrollToMatch(currentIndex.value)
}

function close() {
  emit('close')
}

function onFindKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    event.stopPropagation()
    if (event.shiftKey) goToPrevious()
    else goToNext()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close()
  }
}

function focusInput() {
  findInputRef.value?.focus()
  findInputRef.value?.select()
}

onUnmounted(() => {
  clearHighlights()
  if (searchTimeout) clearTimeout(searchTimeout)
})

defineExpose({ focusInput })
</script>

<template>
  <Transition name="findbar-slide">
    <div v-if="visible" class="find-bar">
      <div class="find-bar-inner">
        <i class="pi pi-search find-bar-icon" />
        <input
          ref="findInputRef"
          v-model="query"
          type="text"
          placeholder="Buscar en el texto..."
          class="find-input"
          aria-label="Buscar en el texto"
          @keydown="onFindKeydown"
        >
        <span v-if="query" class="match-count" :class="{ 'no-matches': query.length >= 2 && totalMatches === 0 }">
          {{ matchLabel }}
        </span>
        <Button
          v-tooltip.bottom="'Anterior (Shift+Enter)'"
          icon="pi pi-chevron-up"
          text
          rounded
          size="small"
          :disabled="totalMatches === 0"
          aria-label="Resultado anterior"
          @click="goToPrevious"
        />
        <Button
          v-tooltip.bottom="'Siguiente (Enter)'"
          icon="pi pi-chevron-down"
          text
          rounded
          size="small"
          :disabled="totalMatches === 0"
          aria-label="Resultado siguiente"
          @click="goToNext"
        />
        <Button
          v-tooltip.bottom="'Cerrar (Escape)'"
          icon="pi pi-times"
          text
          rounded
          size="small"
          aria-label="Cerrar búsqueda"
          @click="close"
        />
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.find-bar {
  position: absolute;
  top: 0;
  right: 1rem;
  z-index: 10;
  padding-top: 0.5rem;
}

.find-bar-inner {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--app-radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.find-bar-icon {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.find-input {
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-color);
  font-size: 0.875rem;
  width: 200px;
  padding: 0.25rem 0.375rem;
  font-family: inherit;
}

.find-input::placeholder {
  color: var(--text-color-secondary);
}

.match-count {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  padding: 0 0.25rem;
  flex-shrink: 0;
}

.match-count.no-matches {
  color: var(--red-500);
}

/* Transition */
.findbar-slide-enter-active,
.findbar-slide-leave-active {
  transition: all 0.2s ease;
}

.findbar-slide-enter-from,
.findbar-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

<style>
/* Global styles for dynamically injected mark elements */
mark.text-find-match {
  background-color: rgba(255, 213, 0, 0.4);
  border-radius: 2px;
  color: inherit;
}

mark.text-find-match.text-find-current {
  background-color: rgba(255, 150, 0, 0.6);
  outline: 2px solid var(--primary-color);
  border-radius: 2px;
}

/* Dark mode — stronger highlights for contrast on dark backgrounds */
.dark mark.text-find-match {
  background-color: rgba(255, 213, 0, 0.35);
  color: #1a1a1a;
}

.dark mark.text-find-match.text-find-current {
  background-color: rgba(255, 170, 0, 0.7);
  color: #1a1a1a;
}
</style>
