<script setup lang="ts">
/**
 * ChapterRangeSelector — filtrado de alertas por rango de capítulos (BK-27, S13-03).
 *
 * Dos dropdowns (Desde/Hasta) poblados desde la lista de capítulos del proyecto.
 * Persiste la selección en localStorage por proyecto.
 */
import { computed, onMounted, ref, watch } from 'vue'
import Select from 'primevue/select'

interface ChapterOption {
  chapterNumber: number
  title: string
}

const props = defineProps<{
  chapters: ChapterOption[]
  projectId?: number
}>()

const emit = defineEmits<{
  (e: 'range-change', range: { min: number | null; max: number | null }): void
}>()

const chapterMin = ref<number | null>(null)
const chapterMax = ref<number | null>(null)

const storageKey = computed(() =>
  props.projectId ? `na-chapter-range-${props.projectId}` : null
)

// Opciones para "Desde" — todos los capítulos + opción "Todos"
const fromOptions = computed(() => [
  { label: 'Desde...', value: null },
  ...props.chapters.map(ch => ({
    label: `Cap. ${ch.chapterNumber}`,
    value: ch.chapterNumber,
  })),
])

// Opciones para "Hasta" — solo capítulos >= chapterMin
const toOptions = computed(() => {
  const minVal = chapterMin.value
  const filtered = minVal != null
    ? props.chapters.filter(ch => ch.chapterNumber >= minVal)
    : props.chapters
  return [
    { label: 'Hasta...', value: null },
    ...filtered.map(ch => ({
      label: `Cap. ${ch.chapterNumber}`,
      value: ch.chapterNumber,
    })),
  ]
})

const hasRange = computed(() => chapterMin.value != null || chapterMax.value != null)

function clearRange() {
  chapterMin.value = null
  chapterMax.value = null
}

// Emitir cambios y persistir
watch([chapterMin, chapterMax], ([min, max]) => {
  // Ajustar max si es menor que min
  if (min != null && max != null && max < min) {
    chapterMax.value = null
    return // el watch se re-disparará
  }
  emit('range-change', { min, max })
  if (storageKey.value) {
    if (min == null && max == null) {
      localStorage.removeItem(storageKey.value)
    } else {
      localStorage.setItem(storageKey.value, JSON.stringify({ min, max }))
    }
  }
})

// Restaurar desde localStorage al montar
onMounted(() => {
  if (storageKey.value) {
    try {
      const saved = localStorage.getItem(storageKey.value)
      if (saved) {
        const { min, max } = JSON.parse(saved)
        chapterMin.value = min ?? null
        chapterMax.value = max ?? null
      }
    } catch {
      // Ignorar datos corruptos
    }
  }
})
</script>

<template>
  <div class="chapter-range-selector">
    <Select
      v-model="chapterMin"
      :options="fromOptions"
      option-label="label"
      option-value="value"
      placeholder="Desde..."
      class="range-select"
    />
    <span class="range-separator">–</span>
    <Select
      v-model="chapterMax"
      :options="toOptions"
      option-label="label"
      option-value="value"
      placeholder="Hasta..."
      class="range-select"
    />
    <button
      v-if="hasRange"
      class="range-clear"
      title="Limpiar rango"
      @click="clearRange"
    >
      <i class="pi pi-times" />
    </button>
  </div>
</template>

<style scoped>
.chapter-range-selector {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.range-select {
  min-width: 100px;
  max-width: 130px;
}

.range-separator {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.range-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-color-secondary);
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
}

.range-clear:hover {
  background: var(--surface-hover);
  color: var(--text-color);
}
</style>
