<template>
  <div class="dialogue-attribution-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-left">
        <i class="pi pi-comments"></i>
        <h3>Atribución de Diálogos</h3>
      </div>
      <div class="header-actions">
        <Select
          v-model="selectedChapter"
          :options="chapterOptions"
          option-label="label"
          option-value="value"
          placeholder="Todos los capítulos"
          class="chapter-selector"
          size="small"
          show-clear
          @change="loadAttributions"
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
      <ProgressSpinner class="loading-spinner" />
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
        @click="$emit('select-dialogue', { ...attr, chapterNumber: selectedChapter ?? attr.chapterNumber })"
      >
        <div class="dialogue-header">
          <div class="speaker-info">
            <i class="pi pi-user"></i>
            <span v-if="isDialogueCorrected(attr)" class="speaker-name speaker-corrected">
              {{ getCorrectedSpeaker(attr) }}
              <Tag severity="success" size="small" class="corrected-tag">Corregido</Tag>
            </span>
            <span v-else class="speaker-name">{{ attr.speakerName || 'Desconocido' }}</span>
          </div>
          <div class="attribution-meta">
            <Tag v-if="selectedChapter === null && attr.chapterNumber" severity="info" size="small">
              Cap. {{ attr.chapterNumber }}
            </Tag>
            <Tag :severity="getConfidenceSeverity(attr.confidence)" size="small">
              {{ getConfidenceLabel(attr.confidence) }}
            </Tag>
            <Tag severity="secondary" size="small">
              {{ getMethodLabel(attr.method) }}
            </Tag>
            <Button
              v-if="correctingIndex !== idx"
              v-tooltip="'Corregir hablante'"
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              class="correct-btn"
              @click.stop="startCorrection(idx, attr)"
            />
          </div>
        </div>

        <!-- Inline speaker correction -->
        <div v-if="correctingIndex === idx" class="correction-form" @click.stop>
          <label class="correction-label">Hablante correcto:</label>
          <Select
            v-model="correctedSpeakerId"
            :options="speakerOptions"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar hablante"
            class="correction-select"
            size="small"
            :disabled="savingCorrection"
            @change="onCorrectionSelectionChange(attr)"
          />
          <span v-if="speakerOptions.length === 0" class="no-entities-message">No hay personajes disponibles</span>
          <span class="auto-save-hint">Se guarda al seleccionar</span>
        </div>

        <div class="dialogue-text">
          <i class="pi pi-quote-left quote-icon"></i>
          <p>{{ truncateText(attr.text, 150) }}</p>
        </div>

        <!-- Alternatives if low confidence -->
        <div v-if="attr.alternatives && attr.alternatives.length > 0 && attr.confidence !== 'high' && correctingIndex !== idx" class="alternatives">
          <span class="alternatives-label">Alternativas:</span>
          <div class="alternatives-list">
            <Chip
              v-for="(alt, altIdx) in attr.alternatives.slice(0, 3)"
              :key="altIdx"
              :label="`${alt.name} (${(alt.score * 100).toFixed(0)}%)`"
              class="alt-chip"
              @click.stop="startCorrectionWithAlt(idx, attr, alt.id)"
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
    <div v-else class="empty-state">
      <i class="pi pi-comments empty-icon"></i>
      <p v-if="selectedChapter !== null">No se encontraron diálogos en este capítulo</p>
      <p v-else>No se encontraron diálogos en el proyecto</p>
      <small v-if="selectedChapter === null">Haz clic en "Actualizar" para cargar todos los capítulos</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Select from 'primevue/select'
import ProgressSpinner from 'primevue/progressspinner'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/apiClient'
import type { DialogueAttribution, DialogueAttributionStats } from '@/types'

interface SpeakerEntity {
  id: number
  name?: string
  canonical_name?: string
  canonicalName?: string
  type?: string
  entity_type?: string
  entityType?: string
}

const props = defineProps<{
  projectId: number
  chapters: Array<{ id: number; number: number; title: string }>
  entities?: SpeakerEntity[]
  initialChapter?: number
}>()

defineEmits<{
  'select-dialogue': [attribution: DialogueAttribution]
}>()

const toast = useToast()

const store = useVoiceAndStyleStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const selectedChapter = ref<number | null>(props.initialChapter ?? null)

// Speaker correction state
const correctingIndex = ref<number | null>(null)
const correctedSpeakerId = ref<number | null>(null)
const savingCorrection = ref(false)
const correctedDialogues = ref<Map<string, { speakerName: string; speakerId: number | null }>>(new Map())

// Entity options for speaker correction dropdown
const speakerOptions = computed(() => {
  // Ensure entities is always an array, never undefined
  if (!props.entities || !Array.isArray(props.entities)) {
    return []
  }

  const characters = props.entities.filter(e => {
    const t = String(e.type || e.entity_type || e.entityType || '').toLowerCase()
    return t === 'character' || t === 'animal' || t === 'creature' || t === 'per' || t === 'person'
  })
  const options: Array<{ label: string; value: number | null }> = characters.map(e => ({
    label: e.name || e.canonical_name || e.canonicalName || `Entidad ${e.id}`,
    value: e.id
  }))

  // Only add "Desconocido" option if there are characters
  if (options.length > 0) {
    options.push({ label: 'Desconocido', value: null })
  }

  return options
})

watch(speakerOptions, (options) => {
  if (!options.some(opt => opt.value === correctedSpeakerId.value)) {
    correctedSpeakerId.value = null
  }
})

// Chapter options for dropdown
const chapterOptions = computed(() => {
  return props.chapters.map(ch => ({
    label: ch.title || `Capítulo ${ch.number}`,
    value: ch.number
  }))
})

// Get attributions from store
const attributionData = computed(() => {
  if (selectedChapter.value === null) {
    // Return combined attributions from all chapters
    const allAttributions: DialogueAttribution[] = []
    const statsCombined = {
      total: 0,
      attributed: 0,
      highConfidence: 0,
      mediumConfidence: 0,
      lowConfidence: 0,
      unknown: 0,
      byMethod: {} as Record<string, number>
    }

    props.chapters.forEach(ch => {
      const data = store.getDialogueAttributions(props.projectId, ch.number)
      if (data) {
        // Add chapter number to each attribution for context
        const withChapter = data.attributions.map(attr => ({
          ...attr,
          chapterNumber: ch.number
        }))
        allAttributions.push(...withChapter)

        // Combine stats
        if (data.stats) {
          statsCombined.total += data.stats.total
          statsCombined.attributed += data.stats.attributed
          statsCombined.highConfidence += data.stats.highConfidence
          statsCombined.mediumConfidence += data.stats.mediumConfidence
          statsCombined.lowConfidence += data.stats.lowConfidence
          statsCombined.unknown += data.stats.unknown

          // Merge byMethod counts
          Object.entries(data.stats.byMethod).forEach(([method, count]) => {
            statsCombined.byMethod[method] = (statsCombined.byMethod[method] || 0) + (count as number)
          })
        }
      }
    })

    return allAttributions.length > 0 ? {
      attributions: allAttributions,
      stats: statsCombined
    } : null
  }

  return store.getDialogueAttributions(props.projectId, selectedChapter.value)
})

const attributions = computed<DialogueAttribution[]>(() => {
  return attributionData.value?.attributions || []
})

const stats = computed<DialogueAttributionStats | null>(() => {
  return attributionData.value?.stats || null
})

// Load attributions for selected chapter (or all chapters)
const loadAttributions = async () => {
  loading.value = true
  error.value = null

  try {
    if (selectedChapter.value === null) {
      // Load all chapters
      const promises = props.chapters.map(ch =>
        store.fetchDialogueAttributions(props.projectId, ch.number)
      )
      const results = await Promise.all(promises)
      if (results.some(success => !success)) {
        error.value = store.error || 'Error al cargar algunas atribuciones'
      }
    } else {
      // Load single chapter
      const success = await store.fetchDialogueAttributions(
        props.projectId,
        selectedChapter.value
      )
      if (!success) {
        error.value = store.error || 'Error al cargar atribuciones'
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
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

// Speaker correction methods
function startCorrection(idx: number, attr: DialogueAttribution) {
  // Defensive check: don't start correction if no speaker options available
  if (speakerOptions.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'No hay personajes',
      detail: 'No se encontraron personajes en el proyecto para asignar como hablantes',
      life: 3000
    })
    return
  }

  correctingIndex.value = idx
  // Seleccionar hablante actual o fallback a "Desconocido".
  correctedSpeakerId.value = speakerOptions.value.some(o => o.value === attr.speakerId)
    ? (attr.speakerId ?? null)
    : null
}

function startCorrectionWithAlt(idx: number, attr: DialogueAttribution, altId: number) {
  startCorrection(idx, attr)
  if (correctingIndex.value !== null) {
    if (speakerOptions.value.some(o => o.value === altId)) {
      correctedSpeakerId.value = altId
    }
  }
}

async function onCorrectionSelectionChange(attr: DialogueAttribution & { chapterNumber?: number }) {
  if (correctingIndex.value === null || savingCorrection.value) {
    return
  }
  await saveCorrection(attr)
}

function getDialogueKey(attr: DialogueAttribution & { chapterNumber?: number }): string {
  const chapterNum = selectedChapter.value ?? attr.chapterNumber ?? 'unknown'
  return `${chapterNum}-${attr.startChar}-${attr.endChar}`
}

function isDialogueCorrected(attr: DialogueAttribution): boolean {
  return correctedDialogues.value.has(getDialogueKey(attr))
}

function getCorrectedSpeaker(attr: DialogueAttribution): string {
  const correction = correctedDialogues.value.get(getDialogueKey(attr))
  return correction?.speakerName || attr.speakerName || 'Desconocido'
}

async function saveCorrection(attr: DialogueAttribution & { chapterNumber?: number }) {
  // Get chapter number from either selected chapter or from the attribution itself
  const chapterNum = selectedChapter.value ?? attr.chapterNumber
  if (chapterNum === null || chapterNum === undefined) return

  const selectedSpeakerId = correctedSpeakerId.value ?? null

  savingCorrection.value = true
  try {
    const data = await api.postRaw<any>(`/api/projects/${props.projectId}/speaker-corrections`, {
      chapter_number: chapterNum,
      dialogue_start_char: attr.startChar,
      dialogue_end_char: attr.endChar,
      dialogue_text: attr.text,
      original_speaker_id: attr.speakerId,
      corrected_speaker_id: selectedSpeakerId,
    })

    if (data.success) {
      const selectedOption = speakerOptions.value.find(o => o.value === selectedSpeakerId) || null
      // Track locally which dialogues have been corrected
      correctedDialogues.value.set(getDialogueKey(attr), {
        speakerName: selectedOption?.label || 'Desconocido',
        speakerId: selectedSpeakerId,
      })
      toast.add({ severity: 'success', summary: 'Corregido', detail: 'Hablante corregido correctamente', life: 2000 })
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: data.error || 'No se pudo guardar', life: 4000 })
    }
  } catch (err) {
    console.error('Error saving speaker correction:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al guardar la corrección', life: 4000 })
  } finally {
    savingCorrection.value = false
    correctingIndex.value = null
    correctedSpeakerId.value = null
  }
}

// Auto-load on mount
onMounted(() => {
  // Load all chapters by default (selectedChapter starts as null)
  loadAttributions()
})

// Watch for chapter selection changes
watch(selectedChapter, () => {
  loadAttributions()
})
</script>

<style scoped>
.dialogue-attribution-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  background: var(--surface-card);
  overflow: hidden;
}

.dialogue-attribution-panel,
.dialogue-attribution-panel * {
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ds-space-4);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
  flex-wrap: wrap;
  gap: var(--ds-space-3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.header-left h3 {
  margin: 0;
  font-size: var(--ds-font-base);
  font-weight: 600;
}

.header-left i {
  color: var(--primary-color);
  font-size: var(--ds-font-xl);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  min-width: 0;
}

.chapter-selector {
  width: min(calc(var(--ds-space-10) * 4.5), 100%);
  max-width: 100%;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--surface-ground);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
  min-width: 0;
  overflow: hidden;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  padding: var(--ds-space-2);
  background: var(--surface-card);
  border-radius: var(--app-radius);
  min-width: 0;
}

.stat-item .stat-value {
  font-size: var(--ds-font-lg);
  font-weight: 700;
  color: var(--text-color);
}

.stat-item .stat-label {
  font-size: calc(var(--ds-font-xs) * 0.933);
  color: var(--text-color-secondary);
  text-align: center;
  line-height: var(--ds-leading-tight);
  overflow-wrap: anywhere;
}

.stat-item.success .stat-value {
  color: var(--ds-text-success);
}

.stat-item.warning .stat-value {
  color: var(--orange-500);
}

.stat-item.danger .stat-value {
  color: var(--ds-text-danger);
}

/* Loading and Error States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-12);
  flex: 1;
  color: var(--text-color-secondary);
}

.loading-spinner {
  width: calc(var(--ds-space-6) + var(--ds-space-1-5));
  height: calc(var(--ds-space-6) + var(--ds-space-1-5));
}

.error-state {
  color: var(--ds-text-danger);
}

.error-state i,
.empty-icon {
  font-size: var(--ds-font-2xl);
  opacity: 0.4;
  margin-bottom: var(--ds-space-4);
}

/* Attributions List */
.attributions-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  scrollbar-gutter: stable;
  padding: var(--ds-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.attribution-item {
  padding: var(--ds-space-4);
  background: var(--surface-ground);
  border-radius: var(--app-radius);
  border-left: var(--ds-border-4) solid var(--primary-color);
  cursor: pointer;
  transition: background var(--ds-duration-normal) var(--ds-ease-in-out),
    transform var(--ds-duration-fast) var(--ds-ease-in-out);
  min-width: 0;
  overflow: hidden;
}

.attribution-item:hover {
  background: var(--surface-hover);
  transform: translateX(var(--ds-space-0-5));
}

.attribution-item.confidence-high {
  border-color: var(--ds-text-success);
}

.attribution-item.confidence-medium {
  border-color: var(--orange-500);
}

.attribution-item.confidence-low {
  border-color: var(--ds-text-danger);
}

.attribution-item.confidence-unknown {
  border-color: var(--gray-400);
}

.dialogue-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--ds-space-3);
  flex-wrap: wrap;
  gap: var(--ds-space-2);
  min-width: 0;
}

.speaker-info {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  min-width: 0;
  flex: 1 1 auto;
}

.speaker-info i {
  color: var(--primary-color);
  font-size: var(--ds-font-sm);
}

.speaker-name {
  font-weight: 600;
  color: var(--text-color);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attribution-meta {
  display: flex;
  gap: var(--ds-space-1-5);
  align-items: center;
  min-width: 0;
  max-width: 100%;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.attribution-meta :deep(.p-tag) {
  padding: var(--ds-space-1) var(--ds-space-2);
  font-size: var(--ds-font-xs);
}

.dialogue-text {
  display: flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--surface-card);
  border-radius: var(--app-radius);
  margin-bottom: var(--ds-space-2);
  min-width: 0;
}

.quote-icon {
  color: var(--text-color-secondary);
  font-size: var(--ds-font-xs);
  flex-shrink: 0;
  margin-top: var(--ds-space-1);
}

.dialogue-text p {
  margin: 0;
  font-size: var(--ds-font-sm);
  line-height: 1.5;
  color: var(--text-color);
  font-style: italic;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.alternatives {
  margin-top: var(--ds-space-2);
}

.alternatives-label {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
  display: block;
  margin-bottom: var(--ds-space-1-5);
}

.alternatives-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1-5);
  min-width: 0;
}

.alternatives-list :deep(.p-chip) {
  font-size: calc(var(--ds-font-xs) * 0.933);
  max-width: 100%;
}

.alternatives-list :deep(.p-chip-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.speech-verb {
  margin-top: var(--ds-space-2);
  color: var(--text-color-secondary);
}

.speech-verb em {
  color: var(--primary-color);
}

/* Speaker correction */
.correct-btn {
  opacity: 0;
  transition: opacity var(--ds-duration-fast);
  width: var(--ds-space-6) !important;
  height: var(--ds-space-6) !important;
  padding: 0 !important;
}

.attribution-item:hover .correct-btn {
  opacity: 1;
}

.speaker-corrected {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  min-width: 0;
  flex-wrap: wrap;
}

.corrected-tag {
  font-size: calc(var(--ds-font-xs) * 0.867);
}

.correction-form {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  margin-bottom: var(--ds-space-2);
  background: var(--primary-50);
  border: var(--ds-border-1) solid var(--primary-200);
  border-radius: var(--app-radius);
  flex-wrap: wrap;
}

.correction-label {
  font-size: var(--ds-font-xs);
  font-weight: 500;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

.correction-select {
  flex: 1;
  min-width: calc(var(--ds-space-10) * 3.75);
}

.auto-save-hint {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
}

.alt-chip {
  cursor: pointer;
}

.alt-chip:hover {
  background: var(--primary-100);
}

.no-entities-message {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
  font-style: italic;
}
</style>
