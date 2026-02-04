<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import type { Chapter, Entity, Alert } from '@/types'

/**
 * ChapterInspector - Panel de detalles de capítulo para el inspector.
 *
 * Muestra información del capítulo actualmente visible:
 * - Botón para volver al resumen del documento
 * - Título y número
 * - Resumen automático del capítulo (si disponible)
 * - Personajes presentes con conteo de menciones
 * - Alertas del capítulo agrupadas por severidad
 */

interface CharacterPresence {
  entity_id: number
  name: string
  mention_count: number
  is_first_appearance: boolean
  is_return: boolean
  chapters_absent: number
}

interface ChapterSummaryData {
  chapter_number: number
  chapter_title: string | null
  word_count: number
  characters_present: CharacterPresence[]
  new_characters: string[]
  returning_characters: string[]
  key_events: Array<{
    event_type: string
    description: string
    characters_involved: string[]
  }>
  llm_events: Array<{
    event_type: string
    description: string
    characters_involved: string[]
  }>
  total_interactions: number
  conflict_interactions: number
  positive_interactions: number
  dominant_tone: string
  locations_mentioned: string[]
  auto_summary: string
  llm_summary: string | null
}

const props = defineProps<{
  /** Capítulo a mostrar */
  chapter: Chapter
  /** ID del proyecto */
  projectId: number
  /** Entidades del proyecto (para mostrar personajes del capítulo) */
  entities?: Entity[]
  /** Alertas del proyecto (para filtrar las del capítulo) */
  alerts?: Alert[]
}>()

const emit = defineEmits<{
  /** Volver al resumen del documento */
  (e: 'back-to-document'): void
  /** Ir al inicio del capítulo */
  (e: 'go-to-start'): void
  /** Ver alertas del capítulo */
  (e: 'view-alerts'): void
  /** Seleccionar un personaje */
  (e: 'select-entity', entityId: number): void
}>()

// Chapter summary data
const summaryLoading = ref(false)
const summaryError = ref<string | null>(null)
const chapterSummary = ref<ChapterSummaryData | null>(null)

// Cache for chapter summaries
const summaryCache = ref<Map<number, ChapterSummaryData>>(new Map())

// Load chapter summary when chapter changes
async function loadChapterSummary() {
  if (!props.chapter) return

  // Check cache first
  const cached = summaryCache.value.get(props.chapter.chapterNumber)
  if (cached) {
    chapterSummary.value = cached
    return
  }

  summaryLoading.value = true
  summaryError.value = null

  try {
    const response = await fetch(
      `/api/projects/${props.projectId}/chapter-progress?mode=basic`
    )
    const data = await response.json()

    if (data.success && data.data.chapters) {
      // Cache all chapters
      for (const ch of data.data.chapters) {
        summaryCache.value.set(ch.chapter_number, ch)
      }
      // Get the summary for this chapter
      chapterSummary.value = summaryCache.value.get(props.chapter.chapterNumber) || null
    }
  } catch (err) {
    console.error('Error loading chapter summary:', err)
    summaryError.value = 'Error al cargar el resumen'
  } finally {
    summaryLoading.value = false
  }
}

// Watch for chapter changes
watch(
  () => props.chapter?.id,
  () => {
    if (props.chapter) {
      loadChapterSummary()
    }
  },
  { immediate: true }
)

/** Alertas de este capítulo */
const chapterAlerts = computed(() => {
  if (!props.alerts) return []
  return props.alerts.filter(a => a.chapter === props.chapter.chapterNumber)
})

/** Contar alertas por severidad */
const alertCounts = computed(() => {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const alert of chapterAlerts.value) {
    if (alert.severity in counts) {
      counts[alert.severity as keyof typeof counts]++
    }
  }
  return counts
})

const hasAlerts = computed(() => chapterAlerts.value.length > 0)

/** Resumen a mostrar (preferir LLM si está disponible) */
const displaySummary = computed(() => {
  if (!chapterSummary.value) return null
  return chapterSummary.value.llm_summary || chapterSummary.value.auto_summary
})

/** Personajes ordenados por menciones */
const topCharacters = computed(() => {
  if (!chapterSummary.value?.characters_present) return []
  return [...chapterSummary.value.characters_present]
    .sort((a, b) => b.mention_count - a.mention_count)
    .slice(0, 8)
})

/** Eventos clave combinados */
const keyEvents = computed(() => {
  if (!chapterSummary.value) return []
  const events = [
    ...(chapterSummary.value.key_events || []),
    ...(chapterSummary.value.llm_events || []),
  ]
  // Dedup by description
  const seen = new Set<string>()
  return events.filter(e => {
    const key = e.description.toLowerCase().substring(0, 30)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).slice(0, 5)
})

function getToneSeverity(tone: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  switch (tone) {
    case 'positive': return 'success'
    case 'tense': return 'warn'
    case 'negative': return 'danger'
    default: return 'secondary'
  }
}

function getToneLabel(tone: string): string {
  const labels: Record<string, string> = {
    positive: 'Positivo',
    tense: 'Tenso',
    negative: 'Negativo',
    neutral: 'Neutro',
  }
  return labels[tone] || tone
}

function getEventIcon(eventType: string): string {
  const icons: Record<string, string> = {
    first_appearance: 'pi-user-plus',
    return: 'pi-replay',
    death: 'pi-heart',
    conflict: 'pi-bolt',
    revelation: 'pi-eye',
    decision: 'pi-check-circle',
    transformation: 'pi-sync',
  }
  return icons[eventType] || 'pi-circle'
}
</script>

<template>
  <div class="chapter-inspector">
    <!-- Header with back button -->
    <div class="inspector-header">
      <Button
        v-tooltip.bottom="'Volver al documento'"
        icon="pi pi-arrow-left"
        text
        rounded
        size="small"
        class="back-button"
        @click="emit('back-to-document')"
      />
      <div class="chapter-badge">
        <i class="pi pi-book"></i>
        <span>Capítulo {{ chapter.chapterNumber }}</span>
      </div>
    </div>

    <!-- Contenido -->
    <div class="inspector-body">
      <!-- Título -->
      <div class="chapter-title-section">
        <h3 class="chapter-title">{{ chapter.title || `Capítulo ${chapter.chapterNumber}` }}</h3>
        <Tag
          v-if="chapterSummary?.dominant_tone && chapterSummary.dominant_tone !== 'neutral'"
          :severity="getToneSeverity(chapterSummary.dominant_tone)"
          :value="getToneLabel(chapterSummary.dominant_tone)"
          class="tone-tag"
        />
      </div>

      <!-- Loading state -->
      <div v-if="summaryLoading" class="loading-section">
        <ProgressSpinner style="width: 24px; height: 24px" />
        <span>Cargando resumen...</span>
      </div>

      <!-- Summary section -->
      <div v-else-if="displaySummary" class="summary-section">
        <p class="summary-text">{{ displaySummary }}</p>
      </div>

      <!-- Estadísticas compactas -->
      <div class="stats-row">
        <div class="stat-chip">
          <i class="pi pi-align-left"></i>
          <span>{{ (chapter.wordCount || 0).toLocaleString() }}</span>
        </div>
        <div v-if="chapterSummary?.total_interactions" class="stat-chip">
          <i class="pi pi-comments"></i>
          <span>{{ chapterSummary.total_interactions }}</span>
        </div>
        <div v-if="chapterSummary?.locations_mentioned?.length" class="stat-chip">
          <i class="pi pi-map-marker"></i>
          <span>{{ chapterSummary.locations_mentioned.length }}</span>
        </div>
      </div>

      <!-- Accordion sections -->
      <Accordion :multiple="true" class="chapter-accordion">
        <!-- Personajes -->
        <AccordionPanel v-if="topCharacters.length > 0" value="characters">
          <AccordionHeader>
            <div class="accordion-header">
              <i class="pi pi-users"></i>
              <span>Personajes ({{ topCharacters.length }})</span>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="characters-list">
              <div
                v-for="char in topCharacters"
                :key="char.entity_id"
                class="character-item"
                :class="{
                  'is-new': char.is_first_appearance,
                  'is-return': char.is_return,
                }"
                @click="emit('select-entity', char.entity_id)"
              >
                <span class="char-name">{{ char.name }}</span>
                <div class="char-badges">
                  <Tag
                    v-if="char.is_first_appearance"
                    severity="success"
                    value="Nuevo"
                    size="small"
                  />
                  <Tag
                    v-if="char.is_return"
                    severity="info"
                    value="Regresa"
                    size="small"
                  />
                  <span class="mention-count">{{ char.mention_count }}</span>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>

        <!-- Eventos clave -->
        <AccordionPanel v-if="keyEvents.length > 0" value="events">
          <AccordionHeader>
            <div class="accordion-header">
              <i class="pi pi-bolt"></i>
              <span>Eventos ({{ keyEvents.length }})</span>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="events-list">
              <div v-for="(event, idx) in keyEvents" :key="idx" class="event-item">
                <i :class="`pi ${getEventIcon(event.event_type)}`"></i>
                <span>{{ event.description }}</span>
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>

        <!-- Alertas -->
        <AccordionPanel v-if="hasAlerts" value="alerts">
          <AccordionHeader>
            <div class="accordion-header">
              <i class="pi pi-exclamation-triangle"></i>
              <span>Alertas ({{ chapterAlerts.length }})</span>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="alerts-summary">
              <div v-if="alertCounts.critical > 0" class="alert-count alert-critical">
                <span class="count">{{ alertCounts.critical }}</span>
                <span class="label">críticas</span>
              </div>
              <div v-if="alertCounts.high > 0" class="alert-count alert-high">
                <span class="count">{{ alertCounts.high }}</span>
                <span class="label">altas</span>
              </div>
              <div v-if="alertCounts.medium > 0" class="alert-count alert-medium">
                <span class="count">{{ alertCounts.medium }}</span>
                <span class="label">medias</span>
              </div>
              <div v-if="alertCounts.low > 0" class="alert-count alert-low">
                <span class="count">{{ alertCounts.low }}</span>
                <span class="label">bajas</span>
              </div>
            </div>
            <Button
              label="Ver todas"
              icon="pi pi-list"
              size="small"
              text
              class="view-alerts-btn"
              @click="emit('view-alerts')"
            />
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

      <!-- Sin alertas badge -->
      <div v-if="!hasAlerts && !summaryLoading" class="no-alerts-badge">
        <i class="pi pi-check-circle"></i>
        <span>Sin alertas</span>
      </div>

      <!-- Ubicaciones -->
      <div v-if="chapterSummary?.locations_mentioned?.length" class="locations-section">
        <div class="section-label">
          <i class="pi pi-map-marker"></i>
          <span>Ubicaciones</span>
        </div>
        <div class="locations-list">
          <Tag
            v-for="loc in chapterSummary.locations_mentioned.slice(0, 5)"
            :key="loc"
            :value="loc"
            severity="secondary"
          />
        </div>
      </div>
    </div>

    <!-- Acciones -->
    <div class="inspector-actions">
      <Button
        label="Ir al inicio"
        icon="pi pi-arrow-up"
        size="small"
        outlined
        @click="emit('go-to-start')"
      />
    </div>
  </div>
</template>

<style scoped>
.chapter-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.inspector-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  border-bottom: 1px solid var(--surface-border);
}

.back-button {
  flex-shrink: 0;
}

.chapter-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-1) var(--ds-space-3);
  background: var(--primary-100);
  color: var(--primary-700);
  border-radius: var(--border-radius-xl);
  font-size: 0.875rem;
  font-weight: 500;
}

.chapter-badge i {
  font-size: 0.875rem;
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.chapter-title-section {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ds-space-2);
}

.chapter-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
  line-height: 1.4;
  flex: 1;
}

.tone-tag {
  flex-shrink: 0;
}

.loading-section {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.summary-section {
  background: var(--surface-50);
  padding: var(--ds-space-3);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--primary-color);
}

.summary-text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-color);
}

.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  background: var(--surface-100);
  border-radius: var(--border-radius);
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.stat-chip i {
  font-size: 0.8rem;
}

.chapter-accordion {
  margin-top: var(--ds-space-2);
}

.chapter-accordion :deep(.p-accordionpanel) {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  margin-bottom: var(--ds-space-2);
}

.chapter-accordion :deep(.p-accordionheader) {
  padding: var(--ds-space-2) var(--ds-space-3);
}

.chapter-accordion :deep(.p-accordioncontent-content) {
  padding: var(--ds-space-3);
}

.accordion-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: 0.9rem;
  font-weight: 500;
}

.accordion-header i {
  color: var(--text-color-secondary);
}

.characters-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.character-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-2);
  background: var(--surface-50);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background-color 0.2s;
}

.character-item:hover {
  background: var(--surface-100);
}

.character-item.is-new {
  border-left: 3px solid var(--green-500);
}

.character-item.is-return {
  border-left: 3px solid var(--blue-500);
}

.char-name {
  font-weight: 500;
  font-size: 0.9rem;
}

.char-badges {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.mention-count {
  background: var(--surface-200);
  padding: 0 var(--ds-space-2);
  border-radius: var(--border-radius-xl);
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  font-size: 0.9rem;
}

.event-item i {
  color: var(--text-color-secondary);
  margin-top: 2px;
}

.alerts-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.alert-count {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--border-radius);
  font-size: 0.85rem;
}

.alert-count .count {
  font-weight: 600;
}

.alert-count .label {
  font-size: 0.8rem;
}

.alert-critical {
  background: var(--red-100);
  color: var(--red-700);
}

.alert-high {
  background: var(--orange-100);
  color: var(--orange-700);
}

.alert-medium {
  background: var(--yellow-100);
  color: var(--yellow-700);
}

.alert-low {
  background: var(--blue-100);
  color: var(--blue-700);
}

.view-alerts-btn {
  width: 100%;
}

.no-alerts-badge {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--green-100);
  border-radius: var(--border-radius);
  color: var(--green-700);
  font-size: 0.9rem;
}

.no-alerts-badge i {
  font-size: 1rem;
}

.locations-section {
  margin-top: var(--ds-space-2);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--ds-space-2);
}

.locations-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  border-top: 1px solid var(--surface-border);
}

/* Dark mode */
.dark .chapter-badge {
  background: var(--primary-900);
  color: var(--primary-200);
}

.dark .summary-section {
  background: var(--surface-800);
}

.dark .stat-chip {
  background: var(--surface-700);
}

.dark .character-item {
  background: var(--surface-800);
}

.dark .character-item:hover {
  background: var(--surface-700);
}

.dark .no-alerts-badge {
  background: var(--green-900);
  color: var(--green-200);
}

.dark .alert-critical {
  background: var(--red-900);
  color: var(--red-200);
}

.dark .alert-high {
  background: var(--orange-900);
  color: var(--orange-200);
}

.dark .alert-medium {
  background: var(--yellow-900);
  color: var(--yellow-200);
}

.dark .alert-low {
  background: var(--blue-900);
  color: var(--blue-200);
}
</style>
