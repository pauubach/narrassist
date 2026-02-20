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
import { api } from '@/services/apiClient'
import { getChapterEvents, type ChapterEventsResponse } from '@/services/events'
import EventsExportDialog from '@/components/events/EventsExportDialog.vue'
import EventStatsCard from '@/components/events/EventStatsCard.vue'

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
  /** Navegar a un evento en el texto */
  (e: 'navigate-to-event', startChar: number, endChar: number): void
  /** Navegar a un capítulo por número */
  (e: 'navigate-to-chapter', chapterNumber: number): void
}>()

// Chapter summary data
const summaryLoading = ref(false)
const summaryError = ref<string | null>(null)
const chapterSummary = ref<ChapterSummaryData | null>(null)

// Cache for chapter summaries
const summaryCache = ref<Map<number, ChapterSummaryData>>(new Map())

// Events data
const eventsLoading = ref(false)
const eventsError = ref<string | null>(null)
const chapterEvents = ref<ChapterEventsResponse | null>(null)
const eventsCache = ref<Map<number, ChapterEventsResponse>>(new Map())

// Export/Stats UI state
const showExportDialog = ref(false)
const showStats = ref(false)

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
    const data = await api.getRaw<any>(
      `/api/projects/${props.projectId}/chapter-progress?mode=basic`
    )

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

// Load chapter events
async function loadChapterEvents() {
  if (!props.chapter) return

  // Check cache first
  const cached = eventsCache.value.get(props.chapter.chapterNumber)
  if (cached) {
    chapterEvents.value = cached
    return
  }

  eventsLoading.value = true
  eventsError.value = null

  try {
    const data = await getChapterEvents(props.projectId, props.chapter.chapterNumber)
    chapterEvents.value = data
    eventsCache.value.set(props.chapter.chapterNumber, data)
  } catch (err) {
    console.error('Error loading chapter events:', err)
    eventsError.value = 'Error al cargar eventos'
  } finally {
    eventsLoading.value = false
  }
}

// Watch for chapter changes
watch(
  () => props.chapter?.id,
  () => {
    if (props.chapter) {
      loadChapterSummary()
      loadChapterEvents()
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

/** Eventos detectados (combinando todos los tiers) */
const keyEvents = computed(() => {
  if (!chapterEvents.value) return []

  // Combinar eventos de todos los tiers
  const allEvents = [
    ...(chapterEvents.value.tier1_events || []),
    ...(chapterEvents.value.tier2_events || []),
    ...(chapterEvents.value.tier3_events || []),
  ]

  // Mapear a formato esperado por el template + incluir posiciones para navegación
  return allEvents.map(e => ({
    event_type: e.event_type,
    description: e.description,
    characters_involved: [], // TODO: Extraer de entity_ids si es necesario
    start_char: e.start_char,
    end_char: e.end_char,
    confidence: e.confidence,
  }))
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

function getEventTypeLabel(eventType: string): string {
  const labels: Record<string, string> = {
    first_appearance: 'Primera aparición',
    return: 'Regreso',
    death: 'Muerte',
    conflict: 'Conflicto',
    revelation: 'Revelación',
    decision: 'Decisión',
    transformation: 'Transformación',
  }
  return labels[eventType] || eventType
}

/** Navegar a un evento en el texto */
function navigateToEvent(event: any) {
  if (event.start_char !== undefined && event.end_char !== undefined) {
    emit('navigate-to-event', event.start_char, event.end_char)
  }
}

// ============================================================================
// Event Type Filter
// ============================================================================

const selectedEventTypes = ref<Set<string>>(new Set())

/** Tipos de eventos disponibles (dinámicamente detectados) */
const availableEventTypes = computed(() => {
  const types = new Set<string>()
  keyEvents.value.forEach(e => types.add(e.event_type))
  return Array.from(types).sort()
})

/** Eventos filtrados por tipo seleccionado */
const filteredKeyEvents = computed(() => {
  if (selectedEventTypes.value.size === 0) {
    return keyEvents.value // Sin filtro, mostrar todos
  }
  return keyEvents.value.filter(e => selectedEventTypes.value.has(e.event_type))
})

/** Toggle de tipo de evento en el filtro */
function toggleEventType(eventType: string) {
  if (selectedEventTypes.value.has(eventType)) {
    selectedEventTypes.value.delete(eventType)
  } else {
    selectedEventTypes.value.add(eventType)
  }
  // Force reactivity
  selectedEventTypes.value = new Set(selectedEventTypes.value)
}

/** Limpiar todos los filtros */
function clearEventFilters() {
  selectedEventTypes.value.clear()
  selectedEventTypes.value = new Set()
}

/** Navegar a un capítulo específico por número */
function navigateToChapter(chapterNumber: number) {
  emit('navigate-to-chapter', chapterNumber)
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

      <!-- Event actions -->
      <div class="header-actions">
        <Button
          v-tooltip.bottom="'Exportar eventos'"
          icon="pi pi-download"
          text
          rounded
          size="small"
          @click="showExportDialog = true"
        />
        <Button
          v-tooltip.bottom="'Estadísticas de eventos'"
          icon="pi pi-chart-bar"
          text
          rounded
          size="small"
          @click="showStats = !showStats"
        />
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
        <ProgressSpinner class="summary-spinner" />
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
              <span>Eventos ({{ filteredKeyEvents.length }}{{ selectedEventTypes.size > 0 ? ` / ${keyEvents.length}` : '' }})</span>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <!-- Filtro de tipos de eventos -->
            <div v-if="availableEventTypes.length > 1" class="event-filter">
              <div class="filter-header">
                <span class="filter-label">Filtrar por tipo:</span>
                <button
                  v-if="selectedEventTypes.size > 0"
                  type="button"
                  class="clear-filter-btn"
                  @click="clearEventFilters"
                >
                  <i class="pi pi-times"></i>
                  Limpiar
                </button>
              </div>
              <div class="event-type-chips">
                <button
                  v-for="type in availableEventTypes"
                  :key="type"
                  type="button"
                  class="event-type-chip"
                  :class="{ 'chip-active': selectedEventTypes.has(type) }"
                  @click="toggleEventType(type)"
                >
                  <i :class="`pi ${getEventIcon(type)}`"></i>
                  <span>{{ getEventTypeLabel(type) }}</span>
                </button>
              </div>
            </div>

            <div class="events-list">
              <div
                v-for="(event, idx) in filteredKeyEvents"
                :key="idx"
                class="event-item"
                @click="navigateToEvent(event)"
              >
                <i :class="`pi ${getEventIcon(event.event_type)}`"></i>
                <span>{{ event.description }}</span>
              </div>
            </div>

            <!-- Mensaje si no hay eventos tras filtrar -->
            <div v-if="filteredKeyEvents.length === 0 && selectedEventTypes.size > 0" class="no-events-filtered">
              <i class="pi pi-filter-slash"></i>
              <span>No hay eventos del tipo seleccionado</span>
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

    <!-- Export dialog -->
    <EventsExportDialog v-model:visible="showExportDialog" :project-id="projectId" />

    <!-- Stats card -->
    <EventStatsCard
      :visible="showStats"
      :project-id="projectId"
      @close="showStats = false"
      @navigate-to-chapter="navigateToChapter"
    />
  </div>
</template>

<style scoped>
.chapter-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.inspector-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
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
  font-size: var(--ds-font-sm);
  font-weight: 500;
  flex: 1;
}

.chapter-badge i {
  font-size: var(--ds-font-sm);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  flex-shrink: 0;
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
  font-size: var(--ds-font-lg);
  font-weight: 600;
  color: var(--text-color);
  line-height: 1.4;
  flex: 1;
}

.summary-spinner {
  width: var(--ds-space-6);
  height: var(--ds-space-6);
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
  font-size: var(--ds-font-sm);
}

.summary-section {
  background: var(--surface-50);
  padding: var(--ds-space-3);
  border-radius: var(--border-radius);
  border-left: calc(var(--ds-border-2) + var(--ds-border-1)) solid var(--primary-color);
}

.summary-text {
  margin: 0;
  font-size: var(--ds-font-sm);
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
  font-size: var(--ds-font-sm);
  color: var(--text-color-secondary);
}

.stat-chip i {
  font-size: var(--ds-font-xs);
}

.chapter-accordion {
  margin-top: var(--ds-space-2);
}

.chapter-accordion :deep(.p-accordionpanel) {
  border: var(--ds-border-1) solid var(--surface-border);
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
  font-size: var(--ds-font-sm);
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
  transition: background-color var(--ds-duration-normal) var(--ds-ease-in-out);
}

.character-item:hover {
  background: var(--surface-100);
}

.character-item.is-new {
  border-left: calc(var(--ds-border-2) + var(--ds-border-1)) solid var(--green-500);
}

.character-item.is-return {
  border-left: calc(var(--ds-border-2) + var(--ds-border-1)) solid var(--blue-500);
}

.char-name {
  font-weight: 500;
  font-size: var(--ds-font-sm);
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
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
}

/* Event Filter */
.event-filter {
  margin-bottom: var(--ds-space-3);
  padding: var(--ds-space-2);
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ds-space-2);
}

.filter-label {
  font-size: var(--ds-font-xs);
  font-weight: 500;
  color: var(--text-color-secondary);
}

.clear-filter-btn {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  background: transparent;
  border: var(--ds-border-1) solid var(--surface-border);
  border-radius: var(--border-radius);
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
  cursor: pointer;
  transition: var(--ds-transition-base);
}

.clear-filter-btn:hover {
  background: var(--surface-100);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.clear-filter-btn i {
  font-size: calc(var(--ds-font-xs) * 0.933);
}

.event-type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
}

.event-type-chip {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1-5) var(--ds-space-3);
  background: var(--surface-0, white);
  border: var(--ds-border-1) solid var(--surface-border);
  border-radius: var(--border-radius-xl);
  font-size: var(--ds-font-xs);
  color: var(--text-color);
  cursor: pointer;
  transition: var(--ds-transition-base);
}

.event-type-chip:hover {
  background: var(--surface-100);
  border-color: var(--primary-color);
}

.event-type-chip.chip-active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.event-type-chip i {
  font-size: var(--ds-font-xs);
}

.dark .event-type-chip {
  background: var(--surface-700);
}

.dark .event-type-chip:hover {
  background: var(--surface-600);
}

.dark .event-filter {
  background: var(--surface-800);
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
  font-size: var(--ds-font-sm);
  padding: var(--ds-space-2);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background var(--ds-duration-fast) var(--ds-ease-in-out);
}

.event-item:hover {
  background: var(--surface-50);
}

.event-item i {
  color: var(--text-color-secondary);
  margin-top: var(--ds-space-0-5);
  flex-shrink: 0;
}

.no-events-filtered {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  color: var(--text-color-secondary);
  font-size: var(--ds-font-sm);
  text-align: center;
  justify-content: center;
}

.no-events-filtered i {
  font-size: var(--ds-font-base);
  opacity: 0.5;
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
  font-size: var(--ds-font-sm);
}

.alert-count .count {
  font-weight: 600;
}

.alert-count .label {
  font-size: var(--ds-font-xs);
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
  font-size: var(--ds-font-sm);
}

.no-alerts-badge i {
  font-size: var(--ds-font-base);
}

.locations-section {
  margin-top: var(--ds-space-2);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-xs);
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
  border-top: var(--ds-border-1) solid var(--surface-border);
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
