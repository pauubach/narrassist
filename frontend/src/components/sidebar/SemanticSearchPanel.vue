<script setup lang="ts">
import { ref, computed } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import { searchSimilarText, type SemanticMatch } from '@/services/semanticSearch'
import type { Chapter } from '@/types'

/**
 * SemanticSearchPanel - Panel de búsqueda semántica
 *
 * Permite buscar fragmentos de texto similares usando embeddings.
 * Muestra resultados ordenados por relevancia con navegación al manuscrito.
 */

interface Props {
  /** ID del proyecto */
  projectId: number
  /** Capítulos del proyecto */
  chapters: Chapter[]
  /** Query inicial (opcional) */
  initialQuery?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  /** Navegar a una posición en el texto */
  'navigate-to-position': [position: number, text: string, chapterId?: number]
}>()

// ============================================================================
// Estado
// ============================================================================

const query = ref(props.initialQuery || '')
const loading = ref(false)
const results = ref<SemanticMatch[]>([])
const searchInfo = ref<{ count: number; total_chunks: number } | null>(null)
const errorMessage = ref<string | null>(null)

// ============================================================================
// Búsqueda
// ============================================================================

async function performSearch() {
  if (!query.value.trim()) {
    errorMessage.value = 'Ingresa un texto para buscar'
    return
  }

  loading.value = true
  errorMessage.value = null
  results.value = []
  searchInfo.value = null

  try {
    const response = await searchSimilarText(props.projectId, {
      query: query.value,
      limit: 20,
      min_similarity: 0.4,
    })

    results.value = response.matches
    searchInfo.value = {
      count: response.count,
      total_chunks: response.total_chunks,
    }

    if (response.count === 0) {
      errorMessage.value = 'No se encontraron fragmentos similares. Intenta con otro texto.'
    }
  } catch (err: any) {
    console.error('Error en búsqueda semántica:', err)
    errorMessage.value = err?.message || 'Error al buscar. Intenta nuevamente.'
  } finally {
    loading.value = false
  }
}

function handleKeyPress(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    performSearch()
  }
}

function navigateToMatch(match: SemanticMatch) {
  emit('navigate-to-position', match.start_char, match.text, match.chapter_id ?? undefined)
}

// ============================================================================
// Helpers
// ============================================================================

function getSimilarityColor(score: number): 'critical' | 'high' | 'medium' | 'low' {
  if (score >= 0.8) return 'critical'
  if (score >= 0.7) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

function getSimilarityLabel(score: number): string {
  return `${(score * 100).toFixed(0)}%`
}

const hasSearched = computed(() => results.value.length > 0 || errorMessage.value !== null)
</script>

<template>
  <div class="semantic-search-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-title">
        <i class="pi pi-search"></i>
        <h3>Búsqueda Semántica</h3>
      </div>
      <p class="header-description">
        Encuentra fragmentos similares por significado
      </p>
    </div>

    <!-- Search box -->
    <div class="search-box">
      <InputText
        v-model="query"
        placeholder="Escribe el texto a buscar..."
        class="search-input"
        :disabled="loading"
        @keypress="handleKeyPress"
      />
      <Button
        label="Buscar"
        icon="pi pi-search"
        :loading="loading"
        :disabled="!query.trim()"
        @click="performSearch"
      />
    </div>

    <!-- Results info -->
    <div v-if="searchInfo && !loading" class="results-info">
      <span class="info-text">
        <strong>{{ searchInfo.count }}</strong> resultado{{ searchInfo.count !== 1 ? 's' : '' }}
        <span class="info-detail">de {{ searchInfo.total_chunks }} fragmentos</span>
      </span>
    </div>

    <!-- Error state -->
    <DsEmptyState
      v-if="errorMessage && !loading"
      icon="pi-info-circle"
      title="Sin resultados"
      :description="errorMessage"
    />

    <!-- Empty state (before search) -->
    <DsEmptyState
      v-if="!hasSearched && !loading"
      icon="pi-search"
      title="Búsqueda semántica"
      description="Ingresa un fragmento de texto para encontrar pasajes similares en el manuscrito"
    />

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" />
      <p class="loading-text">Analizando el manuscrito...</p>
    </div>

    <!-- Results list -->
    <div v-if="results.length > 0 && !loading" class="results-list">
      <div
        v-for="(match, idx) in results"
        :key="idx"
        class="result-item"
        @click="navigateToMatch(match)"
      >
        <div class="result-header">
          <DsBadge
            :severity="getSimilarityColor(match.similarity)"
            size="sm"
          >
            {{ getSimilarityLabel(match.similarity) }}
          </DsBadge>
          <span v-if="match.chapter_title" class="result-chapter">
            {{ match.chapter_title }}
          </span>
        </div>
        <div class="result-text">
          {{ match.text }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.semantic-search-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header */
.panel-header {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--surface-border);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.header-title i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.header-title h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.header-description {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Search box */
.search-box {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--surface-border);
}

.search-input {
  width: 100%;
}

/* Results info */
.results-info {
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
}

.info-text {
  font-size: 0.85rem;
  color: var(--text-color);
}

.info-detail {
  color: var(--text-color-secondary);
  margin-left: var(--ds-space-2);
}

/* Loading state */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-6);
}

.loading-text {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

/* Results list */
.results-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-2);
}

.result-item {
  padding: var(--ds-space-3);
  margin-bottom: var(--ds-space-2);
  background: var(--surface-0, white);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.15s;
}

.result-item:hover {
  background: var(--surface-50);
  border-color: var(--primary-color);
  transform: translateX(2px);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.result-chapter {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  flex: 1;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-text {
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--text-color);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Dark mode */
.dark .results-info {
  background: var(--surface-800);
}

.dark .result-item {
  background: var(--surface-900);
}

.dark .result-item:hover {
  background: var(--surface-800);
}
</style>
