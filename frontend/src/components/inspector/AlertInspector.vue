<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import type { Alert, AlertSource } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'

/**
 * AlertInspector - Panel de detalles de alerta para el inspector.
 *
 * Muestra información detallada de una alerta seleccionada:
 * - Severidad y categoría
 * - Título y descripción
 * - Ubicación en el texto (con título de capítulo si disponible)
 * - Sugerencia de corrección
 * - Acciones (resolver, descartar, ir al texto)
 * - Múltiples botones de navegación para alertas de inconsistencia
 * - Navegación de ocurrencias para alertas de repetición (prev/next)
 */

interface ChapterInfo {
  id: number
  chapterNumber: number
  title: string
}

/** Ocurrencia de una palabra repetida */
interface AlertOccurrence {
  start_char: number
  end_char: number
  context?: string
}

const props = defineProps<{
  /** Alerta a mostrar */
  alert: Alert
  /** Capítulos disponibles para mostrar títulos */
  chapters?: ChapterInfo[]
}>()

const emit = defineEmits<{
  /** Ir al texto donde está la alerta, opcionalmente a una fuente específica */
  (e: 'navigate', source?: AlertSource): void
  /** Navegar a una ocurrencia específica por posición */
  (e: 'navigateToPosition', startChar: number, endChar: number, text?: string): void
  /** Marcar como resuelta */
  (e: 'resolve'): void
  /** Descartar alerta */
  (e: 'dismiss'): void
  /** Cerrar el inspector */
  (e: 'close'): void
}>()

const { getSeverityLabel, getSeverityColor, getSeverityIcon, getCategoryConfig } = useAlertUtils()

const severityLabel = computed(() => getSeverityLabel(props.alert.severity))
const severityColor = computed(() => getSeverityColor(props.alert.severity))
const severityIcon = computed(() => getSeverityIcon(props.alert.severity))
const categoryConfig = computed(() => getCategoryConfig(props.alert.category))
const categoryLabel = computed(() => categoryConfig.value.label)

const confidencePercent = computed(() => Math.round(props.alert.confidence * 100))

/**
 * Obtiene el título del capítulo por número.
 */
function getChapterTitle(chapterNumber: number): string {
  const chapter = props.chapters?.find(c => c.chapterNumber === chapterNumber)
  if (chapter?.title && chapter.title.trim()) {
    return chapter.title
  }
  return `Capítulo ${chapterNumber}`
}

/**
 * Etiqueta del capítulo con título si está disponible.
 */
const chapterLabel = computed(() => {
  if (!props.alert.chapter) return null
  return getChapterTitle(props.alert.chapter)
})

/**
 * Verifica si la alerta tiene múltiples fuentes (inconsistencia).
 */
const hasMultipleSources = computed(() => {
  const sources = props.alert.extraData?.sources
  return Array.isArray(sources) && sources.length > 1
})

/**
 * Fuentes de la alerta para navegación múltiple.
 */
const alertSources = computed(() => {
  return props.alert.extraData?.sources ?? []
})

/**
 * Genera etiqueta para un valor de fuente.
 */
function getSourceLabel(source: AlertSource): string {
  return `"${source.value}"`
}

/**
 * Genera ubicación de una fuente.
 */
function getSourceLocation(source: AlertSource): string {
  const parts: string[] = []
  if (source.chapter) {
    parts.push(getChapterTitle(source.chapter))
  }
  return parts.join(', ') || ''
}

// =========================================================================
// Occurrence navigation (for word echo / repetition alerts)
// =========================================================================

const occurrenceIndex = ref(0)

/** Ocurrencias de la alerta (repeticiones, ecos, etc.) */
const occurrences = computed<AlertOccurrence[]>(() => {
  const raw = props.alert.extraData?.occurrences
  if (!Array.isArray(raw)) return []
  return raw.filter((o: any) => typeof o.start_char === 'number' && typeof o.end_char === 'number')
})

const hasOccurrences = computed(() => occurrences.value.length > 1)
const canGoPrev = computed(() => occurrenceIndex.value > 0)
const canGoNext = computed(() => occurrenceIndex.value < occurrences.value.length - 1)
const occurrenceLabel = computed(() =>
  `${occurrenceIndex.value + 1} / ${occurrences.value.length}`
)

/** Palabra de la alerta (para el highlight) */
const alertWord = computed(() => {
  return (props.alert.extraData?.word as string) ?? props.alert.excerpt ?? ''
})

// Reset index when alert changes
watch(() => props.alert.id, () => {
  occurrenceIndex.value = 0
})

function navigateToOccurrence(index: number) {
  const occ = occurrences.value[index]
  if (!occ) return
  occurrenceIndex.value = index
  emit('navigateToPosition', occ.start_char, occ.end_char, alertWord.value)
}

function goToPrevOccurrence() {
  if (!canGoPrev.value) return
  navigateToOccurrence(occurrenceIndex.value - 1)
}

function goToNextOccurrence() {
  if (!canGoNext.value) return
  navigateToOccurrence(occurrenceIndex.value + 1)
}
</script>

<template>
  <div class="alert-inspector">
    <!-- Header con severidad -->
    <div class="inspector-header" :style="{ borderLeftColor: severityColor }">
      <div class="severity-badge" :style="{ backgroundColor: severityColor + '20', color: severityColor }">
        <i :class="severityIcon"></i>
        <span>{{ severityLabel }}</span>
      </div>
      <span class="category-label">{{ categoryLabel }}</span>
    </div>

    <!-- Tarjeta de categoría: ¿Por qué se genera esta alerta? -->
    <div class="category-info-card">
      <i :class="categoryConfig.icon" class="category-info-icon"></i>
      <span class="category-info-text">{{ categoryConfig.description }}</span>
    </div>

    <!-- Contenido -->
    <div class="inspector-body">
      <!-- Título -->
      <div class="alert-title-section">
        <h3 class="alert-title">{{ alert.title }}</h3>
      </div>

      <!-- Descripción -->
      <div v-if="alert.description" class="info-section">
        <div class="section-label">Descripción</div>
        <p class="description">{{ alert.description }}</p>
      </div>

      <!-- Explicación -->
      <div v-if="alert.explanation" class="info-section">
        <div class="section-label">Explicación</div>
        <p class="explanation">{{ alert.explanation }}</p>
      </div>

      <!-- Sugerencia -->
      <div v-if="alert.suggestion" class="info-section suggestion-section">
        <div class="section-label">
          <i class="pi pi-lightbulb"></i>
          Sugerencia
        </div>
        <p class="suggestion">{{ alert.suggestion }}</p>
      </div>

      <!-- Contexto del texto (excerpt) -->
      <div v-if="alert.excerpt" class="info-section excerpt-section">
        <div class="section-label">
          <i class="pi pi-file-edit"></i>
          Contexto en el texto
        </div>
        <div class="excerpt-box">
          <p class="excerpt-text">"{{ alert.excerpt }}"</p>
        </div>
      </div>

      <!-- Ubicación -->
      <div v-if="alert.chapter" class="info-section">
        <div class="section-label">Ubicación</div>
        <div class="location-info">
          <i class="pi pi-map-marker"></i>
          <span>{{ chapterLabel }}</span>
        </div>
      </div>

      <!-- Confianza -->
      <div class="info-section">
        <div class="section-label">Confianza del análisis</div>
        <div class="confidence-bar">
          <div
            class="confidence-fill"
            :style="{ width: confidencePercent + '%', backgroundColor: severityColor }"
          ></div>
          <span class="confidence-value">{{ confidencePercent }}%</span>
        </div>
      </div>

      <!-- Estado -->
      <div class="info-section">
        <div class="section-label">Estado</div>
        <div class="status-badge" :class="`status-${alert.status}`">
          {{ alert.status === 'active' ? 'Pendiente' : alert.status === 'resolved' ? 'Resuelta' : 'Descartada' }}
        </div>
      </div>
    </div>

    <!-- Acciones -->
    <div class="inspector-actions">
      <!-- Múltiples botones de navegación para alertas de inconsistencia -->
      <div v-if="hasMultipleSources" class="multi-source-nav">
        <span class="nav-label">Ver en documento:</span>
        <div class="source-buttons">
          <Button
            v-for="(source, index) in alertSources"
            :key="index"
            v-tooltip.top="getSourceLocation(source)"
            :label="getSourceLabel(source)"
            icon="pi pi-arrow-right"
            size="small"
            outlined
            class="source-btn"
            @click="emit('navigate', source)"
          />
        </div>
      </div>
      <!-- Navegación de ocurrencias (repeticiones, ecos) -->
      <div v-else-if="hasOccurrences" class="occurrence-nav">
        <div class="occurrence-nav-row">
          <Button
            icon="pi pi-chevron-left"
            text
            rounded
            size="small"
            :disabled="!canGoPrev"
            @click="goToPrevOccurrence"
          />
          <span class="occurrence-label">{{ occurrenceLabel }}</span>
          <Button
            icon="pi pi-chevron-right"
            text
            rounded
            size="small"
            :disabled="!canGoNext"
            @click="goToNextOccurrence"
          />
        </div>
        <Button
          label="Ir al texto"
          icon="pi pi-arrow-right"
          size="small"
          @click="navigateToOccurrence(occurrenceIndex)"
        />
      </div>
      <!-- Botón único para alertas sin múltiples fuentes ni ocurrencias -->
      <Button
        v-else
        label="Ir al texto"
        icon="pi pi-arrow-right"
        size="small"
        @click="emit('navigate')"
      />
      <div class="action-row">
        <Button
          label="Resolver"
          icon="pi pi-check"
          size="small"
          severity="success"
          outlined
          :disabled="alert.status !== 'active'"
          @click="emit('resolve')"
        />
        <Button
          label="Descartar"
          icon="pi pi-times"
          size="small"
          severity="secondary"
          text
          :disabled="alert.status !== 'active'"
          @click="emit('dismiss')"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.alert-inspector {
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
  justify-content: space-between;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-surface-border);
  border-left: 4px solid;
}

.severity-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-1) var(--ds-space-3);
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
}

.severity-badge i {
  font-size: 0.875rem;
}

.category-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.category-info-card {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-4);
  background: var(--ds-surface-ground);
  border-bottom: 1px solid var(--ds-surface-border);
}

.category-info-icon {
  font-size: 0.875rem;
  color: var(--ds-color-text-secondary);
}

.category-info-text {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  font-style: italic;
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.alert-title-section {
  padding-bottom: var(--ds-space-2);
  border-bottom: 1px solid var(--ds-surface-border);
}

.alert-title {
  margin: 0;
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  line-height: 1.4;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-label i {
  font-size: 0.875rem;
}

.description,
.explanation {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.6;
}

.suggestion-section {
  background: var(--ds-color-info-soft);
  padding: var(--ds-space-3);
  border-radius: var(--ds-radius-md);
  margin: 0 calc(-1 * var(--ds-space-4));
  padding-left: var(--ds-space-4);
  padding-right: var(--ds-space-4);
}

.suggestion-section .section-label {
  color: var(--ds-color-info);
}

.suggestion-section .section-label i {
  color: var(--ds-color-info);
}

.suggestion {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.6;
  font-style: italic;
}

.location-info {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.location-info i {
  color: var(--ds-color-text-secondary);
}

/* Excerpt section */
.excerpt-section {
  background: var(--ds-surface-ground);
  padding: var(--ds-space-3);
  border-radius: var(--ds-radius-md);
  margin: 0 calc(-1 * var(--ds-space-4));
  padding-left: var(--ds-space-4);
  padding-right: var(--ds-space-4);
}

.excerpt-box {
  background: var(--ds-surface-card);
  border: 1px solid var(--ds-surface-border);
  border-left: 3px solid var(--ds-color-primary);
  border-radius: var(--ds-radius-sm);
  padding: var(--ds-space-3);
}

.excerpt-text {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.6;
  font-style: italic;
}

.confidence-bar {
  position: relative;
  height: 8px;
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: var(--ds-radius-full);
  transition: width var(--ds-transition-base);
}

.confidence-value {
  position: absolute;
  right: 0;
  top: -20px;
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--ds-space-1) var(--ds-space-3);
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  width: fit-content;
}

.status-active {
  background: var(--ds-color-warning-soft);
  color: var(--ds-color-warning);
}

.status-resolved {
  background: var(--ds-color-success-soft);
  color: var(--ds-color-success);
}

.status-dismissed {
  background: var(--ds-surface-hover);
  color: var(--ds-color-text-secondary);
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}

.action-row {
  display: flex;
  gap: var(--ds-space-2);
}

.action-row > * {
  flex: 1;
}

/* Multi-source navigation for inconsistency alerts */
.multi-source-nav {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.nav-label {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}

.source-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.source-btn {
  flex: 1;
  min-width: 80px;
}

.source-btn :deep(.p-button-label) {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Occurrence navigation (word echo / repetition alerts) */
.occurrence-nav {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  align-items: center;
}

.occurrence-nav-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.occurrence-label {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  min-width: 3rem;
  text-align: center;
}
</style>
