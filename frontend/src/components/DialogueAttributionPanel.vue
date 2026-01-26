<template>
  <div class="dialogue-attribution-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-left">
        <i class="pi pi-comments"></i>
        <h3>Atribución de Diálogos</h3>
      </div>
      <div class="header-actions">
        <Dropdown
          v-model="selectedChapter"
          :options="chapterOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Capítulo"
          class="chapter-selector"
          size="small"
          @change="loadAttributions"
        />
        <Button
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          :loading="loading"
          @click="loadAttributions"
          v-tooltip.bottom="'Actualizar'"
        />
      </div>
    </div>

    <!-- Stats Summary -->
    <div v-if="stats" class="stats-bar">
      <div class="stat-item">
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">Total</span>
      </div>
      <div class="stat-item success">
        <span class="stat-value">{{ stats.highConfidence }}</span>
        <span class="stat-label">Alta confianza</span>
      </div>
      <div class="stat-item warning">
        <span class="stat-value">{{ stats.mediumConfidence }}</span>
        <span class="stat-label">Media</span>
      </div>
      <div class="stat-item danger">
        <span class="stat-value">{{ stats.lowConfidence + stats.unknown }}</span>
        <span class="stat-label">Baja/Sin</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <p>Cargando atribuciones...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <Button label="Reintentar" size="small" @click="loadAttributions" />
    </div>

    <!-- Attributions List -->
    <div v-else-if="attributions.length > 0" class="attributions-list">
      <div
        v-for="(attr, idx) in attributions"
        :key="idx"
        class="attribution-item"
        :class="getConfidenceClass(attr.confidence)"
        @click="$emit('select-dialogue', attr)"
      >
        <div class="dialogue-header">
          <div class="speaker-info">
            <i class="pi pi-user"></i>
            <span class="speaker-name">{{ attr.speakerName || 'Desconocido' }}</span>
          </div>
          <div class="attribution-meta">
            <Tag :severity="getConfidenceSeverity(attr.confidence)" size="small">
              {{ getConfidenceLabel(attr.confidence) }}
            </Tag>
            <Tag severity="secondary" size="small">
              {{ getMethodLabel(attr.method) }}
            </Tag>
          </div>
        </div>

        <div class="dialogue-text">
          <i class="pi pi-quote-left quote-icon"></i>
          <p>{{ truncateText(attr.text, 150) }}</p>
        </div>

        <!-- Alternatives if low confidence -->
        <div v-if="attr.alternatives && attr.alternatives.length > 0 && attr.confidence !== 'high'" class="alternatives">
          <span class="alternatives-label">Alternativas:</span>
          <div class="alternatives-list">
            <Chip
              v-for="(alt, altIdx) in attr.alternatives.slice(0, 3)"
              :key="altIdx"
              :label="`${alt.name} (${(alt.score * 100).toFixed(0)}%)`"
            />
          </div>
        </div>

        <!-- Speech verb if detected -->
        <div v-if="attr.speechVerb" class="speech-verb">
          <small>Verbo: <em>{{ attr.speechVerb }}</em></small>
        </div>
      </div>
    </div>

    <!-- No Attributions -->
    <div v-else-if="selectedChapter !== null" class="empty-state">
      <i class="pi pi-comments empty-icon"></i>
      <p>No se encontraron diálogos en este capítulo</p>
    </div>

    <!-- No Chapter Selected -->
    <div v-else class="empty-state">
      <i class="pi pi-book empty-icon"></i>
      <p>Selecciona un capítulo para ver las atribuciones de diálogos</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import type { DialogueAttribution, DialogueAttributionStats } from '@/types'

const props = defineProps<{
  projectId: number
  chapters: Array<{ id: number; number: number; title: string }>
  initialChapter?: number
}>()

const emit = defineEmits<{
  'select-dialogue': [attribution: DialogueAttribution]
}>()

const store = useVoiceAndStyleStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const selectedChapter = ref<number | null>(props.initialChapter ?? null)

// Chapter options for dropdown
const chapterOptions = computed(() => {
  return props.chapters.map(ch => ({
    label: ch.title || `Capítulo ${ch.number}`,
    value: ch.number
  }))
})

// Get attributions from store
const attributionData = computed(() => {
  if (selectedChapter.value === null) return null
  return store.getDialogueAttributions(props.projectId, selectedChapter.value)
})

const attributions = computed<DialogueAttribution[]>(() => {
  return attributionData.value?.attributions || []
})

const stats = computed<DialogueAttributionStats | null>(() => {
  return attributionData.value?.stats || null
})

// Load attributions for selected chapter
const loadAttributions = async () => {
  if (selectedChapter.value === null) return

  loading.value = true
  error.value = null

  try {
    const success = await store.fetchDialogueAttributions(
      props.projectId,
      selectedChapter.value
    )
    if (!success) {
      error.value = store.error || 'Error al cargar atribuciones'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
  }
}

// Helpers
const getConfidenceClass = (confidence: string): string => {
  return `confidence-${confidence}`
}

const getConfidenceSeverity = (confidence: string): string => {
  const severities: Record<string, string> = {
    high: 'success',
    medium: 'warning',
    low: 'danger',
    unknown: 'secondary'
  }
  return severities[confidence] || 'secondary'
}

const getConfidenceLabel = (confidence: string): string => {
  const labels: Record<string, string> = {
    high: 'Alta',
    medium: 'Media',
    low: 'Baja',
    unknown: 'Desconocida'
  }
  return labels[confidence] || confidence
}

const getMethodLabel = (method: string): string => {
  const labels: Record<string, string> = {
    explicit_verb: 'Verbo explícito',
    alternation: 'Alternancia',
    voice_profile: 'Perfil de voz',
    proximity: 'Proximidad',
    none: 'Sin método'
  }
  return labels[method] || method
}

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Auto-load if initial chapter provided
onMounted(() => {
  if (selectedChapter.value !== null) {
    loadAttributions()
  }
})

// Watch for chapter selection changes
watch(selectedChapter, (newChapter) => {
  if (newChapter !== null) {
    const key = `${props.projectId}-${newChapter}`
    if (!store.dialogueAttributions[key]) {
      loadAttributions()
    }
  }
})
</script>

<style scoped>
.dialogue-attribution-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-card);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
  flex-wrap: wrap;
  gap: 0.75rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-left h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.header-left i {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chapter-selector {
  width: 180px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--surface-ground);
  border-bottom: 1px solid var(--surface-border);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  padding: 0.5rem;
  background: var(--surface-card);
  border-radius: 6px;
}

.stat-item .stat-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-item .stat-label {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.stat-item.success .stat-value {
  color: var(--green-500);
}

.stat-item.warning .stat-value {
  color: var(--orange-500);
}

.stat-item.danger .stat-value {
  color: var(--red-500);
}

/* Loading and Error States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  flex: 1;
  color: var(--text-color-secondary);
}

.error-state {
  color: var(--red-500);
}

.error-state i,
.empty-icon {
  font-size: 2.5rem;
  opacity: 0.4;
  margin-bottom: 1rem;
}

/* Attributions List */
.attributions-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.attribution-item {
  padding: 1rem;
  background: var(--surface-ground);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.attribution-item:hover {
  background: var(--surface-hover);
  transform: translateX(2px);
}

.attribution-item.confidence-high {
  border-color: var(--green-500);
}

.attribution-item.confidence-medium {
  border-color: var(--orange-500);
}

.attribution-item.confidence-low {
  border-color: var(--red-500);
}

.attribution-item.confidence-unknown {
  border-color: var(--gray-400);
}

.dialogue-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.speaker-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.speaker-info i {
  color: var(--primary-color);
  font-size: 0.875rem;
}

.speaker-name {
  font-weight: 600;
  color: var(--text-color);
}

.attribution-meta {
  display: flex;
  gap: 0.375rem;
}

.dialogue-text {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-card);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.quote-icon {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  flex-shrink: 0;
  margin-top: 0.25rem;
}

.dialogue-text p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-color);
  font-style: italic;
}

.alternatives {
  margin-top: 0.5rem;
}

.alternatives-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  display: block;
  margin-bottom: 0.375rem;
}

.alternatives-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.alternatives-list :deep(.p-chip) {
  font-size: 0.7rem;
}

.speech-verb {
  margin-top: 0.5rem;
  color: var(--text-color-secondary);
}

.speech-verb em {
  color: var(--primary-color);
}
</style>
