<script setup lang="ts">
/**
 * SequentialCorrectionMode - Modo de corrección secuencial (vista túnel)
 *
 * Permite revisar alertas una por una de forma enfocada:
 * - Navegación con teclado (←/→, A/D/S/F)
 * - Contexto del texto con highlighting
 * - Undo multinivel (Ctrl+Z)
 * - Barra de progreso visual
 *
 * Atajos de teclado:
 * - ← / P: Anterior
 * - → / N: Siguiente
 * - A / Enter: Aceptar (resolver)
 * - D: Descartar
 * - S: Saltar
 * - F: Marcar para revisar
 * - Ctrl+Z: Deshacer
 * - Escape: Salir
 */

import { computed } from 'vue'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
// import Divider from 'primevue/divider'  // Reserved
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import type { Alert, AlertSource } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'

interface ChapterInfo {
  id: number
  chapterNumber: number
  title: string
}

const props = defineProps<{
  currentAlert: Alert | null
  progress: {
    current: number
    total: number
    pending: number
    percentage: number
  }
  hasNext: boolean
  hasPrevious: boolean
  canUndo: boolean
  updating: boolean
  recentActions: Array<{
    alertId: number
    action: string
    timestamp: Date
  }>
  showResolved: boolean
  /** Capítulos disponibles para mostrar títulos */
  chapters?: ChapterInfo[]
}>()

const emit = defineEmits<{
  (e: 'next'): void
  (e: 'previous'): void
  (e: 'resolve'): void
  (e: 'dismiss'): void
  (e: 'skip'): void
  (e: 'flag'): void
  (e: 'undo'): void
  (e: 'exit'): void
  (e: 'update:showResolved', value: boolean): void
  /** Navega al texto, opcionalmente a una fuente específica para inconsistencias */
  (e: 'navigate-to-text', source?: AlertSource): void
}>()

const { getSeverityConfig, getCategoryLabel } = useAlertUtils()

// Computed
const severityConfig = computed(() =>
  props.currentAlert ? getSeverityConfig(props.currentAlert.severity) : null
)

const categoryLabel = computed(() =>
  props.currentAlert ? getCategoryLabel(props.currentAlert.category) : ''
)

/**
 * Obtiene el título del capítulo por número.
 * Retorna el título si está disponible, o "Cap. X" como fallback.
 */
function getChapterTitle(chapterNumber: number): string {
  const chapter = props.chapters?.find(c => c.chapterNumber === chapterNumber)
  if (chapter?.title && chapter.title.trim()) {
    // Si el título es significativo (no vacío ni genérico), mostrarlo
    return chapter.title
  }
  // Fallback: mostrar "Cap. X"
  return `Cap. ${chapterNumber}`
}

const chapterLabel = computed(() => {
  if (props.currentAlert?.chapter === undefined) {
    return 'Sin capítulo'
  }
  return getChapterTitle(props.currentAlert.chapter)
})

const isResolved = computed(() =>
  props.currentAlert?.status === 'resolved'
)

const isDismissed = computed(() =>
  props.currentAlert?.status === 'dismissed'
)

/**
 * Verifica si la alerta tiene múltiples fuentes (es una inconsistencia).
 * Si tiene sources[], muestra múltiples botones de navegación.
 */
const hasMultipleSources = computed(() => {
  const sources = props.currentAlert?.extraData?.sources
  return Array.isArray(sources) && sources.length > 1
})

/**
 * Obtiene las fuentes de la alerta para navegación múltiple.
 */
const alertSources = computed(() => {
  return props.currentAlert?.extraData?.sources ?? []
})

/**
 * Genera una etiqueta corta para el valor de una fuente.
 */
function getSourceLabel(source: AlertSource): string {
  return `"${source.value}"`
}

/**
 * Genera una descripción de ubicación para una fuente.
 * Muestra el título del capítulo si está disponible.
 */
function getSourceLocation(source: AlertSource): string {
  const parts: string[] = []
  if (source.chapter) {
    parts.push(getChapterTitle(source.chapter))
  }
  if (source.page) {
    parts.push(`pág. ${source.page}`)
  }
  return parts.join(', ') || 'Sin ubicación'
}

const contextLines = computed(() => {
  if (!props.currentAlert?.excerpt) return { before: '', highlight: '', after: '' }

  const excerpt = props.currentAlert.excerpt
  // Try to find the highlighted portion based on the title/description
  // For now, return the whole excerpt as context
  return {
    before: '',
    highlight: excerpt,
    after: '',
  }
})

// Keyboard shortcuts display
const shortcuts = [
  { key: '←/P', action: 'Anterior' },
  { key: '→/N', action: 'Siguiente' },
  { key: 'A/Enter', action: 'Aceptar' },
  { key: 'D', action: 'Descartar' },
  { key: 'S', action: 'Saltar' },
  { key: 'F', action: 'Marcar' },
  { key: 'Ctrl+Z', action: 'Deshacer' },
  { key: 'Esc', action: 'Salir' },
]

function formatActionTime(date: Date): string {
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return 'hace unos segundos'
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
  return date.toLocaleTimeString()
}

function getActionLabel(action: string): string {
  switch (action) {
    case 'resolve': return 'Aceptada'
    case 'dismiss': return 'Descartada'
    case 'skip': return 'Saltada'
    case 'flag': return 'Marcada'
    default: return action
  }
}

function getActionSeverity(action: string): 'success' | 'warn' | 'info' | 'secondary' {
  switch (action) {
    case 'resolve': return 'success'
    case 'dismiss': return 'warn'
    case 'flag': return 'info'
    default: return 'secondary'
  }
}
</script>

<template>
  <div class="sequential-mode">
    <!-- Header -->
    <header class="sequential-header">
      <div class="header-left">
        <h2 class="mode-title">Modo Corrección Secuencial</h2>
      </div>

      <div class="header-center">
        <div class="progress-info">
          <span class="progress-numbers">
            {{ progress.current }} de {{ progress.total }}
          </span>
          <span v-if="progress.pending !== progress.total" class="progress-pending">
            ({{ progress.pending }} pendientes)
          </span>
        </div>
        <ProgressBar
          :value="progress.percentage"
          :show-value="false"
          class="progress-bar"
          aria-label="Progreso de revisión"
        />
      </div>

      <div class="header-right">
        <div class="toggle-resolved">
          <label for="show-resolved">Mostrar resueltas</label>
          <ToggleSwitch
            id="show-resolved"
            :model-value="showResolved"
            @update:model-value="emit('update:showResolved', $event)"
          />
        </div>
        <Button
          v-tooltip.bottom="'Salir (Esc)'"
          icon="pi pi-times"
          text
          rounded
          severity="secondary"
          aria-label="Salir del modo secuencial"
          class="close-button"
          @click="emit('exit')"
        />
      </div>
    </header>

    <!-- Main Content -->
    <main v-if="currentAlert" class="sequential-content">
      <!-- Alert Card -->
      <section class="alert-section" aria-label="Detalle de la alerta">
        <!-- Status Banner for resolved/dismissed -->
        <Message
          v-if="isResolved"
          severity="success"
          :closable="false"
          class="status-banner"
        >
          Esta alerta ya ha sido resuelta
        </Message>
        <Message
          v-else-if="isDismissed"
          severity="warn"
          :closable="false"
          class="status-banner"
        >
          Esta alerta ha sido descartada
        </Message>

        <!-- Alert Header -->
        <div class="alert-header">
          <div class="alert-category">
            <Tag
              :severity="severityConfig?.primeSeverity || 'info'"
              class="severity-tag"
            >
              {{ severityConfig?.label || currentAlert.severity }}
            </Tag>
            <span class="category-label">{{ categoryLabel }}</span>
          </div>
          <div class="alert-location">
            <i class="pi pi-bookmark"></i>
            {{ chapterLabel }}
            <span v-if="currentAlert.spanStart !== undefined" class="position">
              · pos. {{ currentAlert.spanStart }}-{{ currentAlert.spanEnd }}
            </span>
          </div>
        </div>

        <!-- Alert Title & Description -->
        <div class="alert-body">
          <h3 class="alert-title">{{ currentAlert.title }}</h3>
          <p class="alert-description">{{ currentAlert.description }}</p>

          <!-- Explanation if available -->
          <div v-if="currentAlert.explanation" class="alert-explanation">
            <i class="pi pi-info-circle"></i>
            <span>{{ currentAlert.explanation }}</span>
          </div>
        </div>

        <!-- Text Context -->
        <div class="text-context" aria-label="Contexto del texto">
          <div class="context-header">
            <span class="context-label">TEXTO</span>
            <!-- Múltiples botones si hay sources (inconsistencias) -->
            <div v-if="hasMultipleSources" class="multi-source-nav">
              <span class="nav-hint">Ver en documento:</span>
              <Button
                v-for="(source, index) in alertSources"
                :key="index"
                v-tooltip.bottom="getSourceLocation(source)"
                icon="pi pi-external-link"
                :label="getSourceLabel(source)"
                text
                size="small"
                class="source-nav-btn"
                @click="emit('navigate-to-text', source)"
              />
            </div>
            <!-- Botón único si no hay múltiples sources -->
            <Button
              v-else
              icon="pi pi-external-link"
              label="Ver en documento"
              text
              size="small"
              @click="emit('navigate-to-text')"
            />
          </div>
          <div class="context-body">
            <p class="excerpt">
              <span v-if="contextLines.before" class="context-before">{{ contextLines.before }}</span>
              <mark class="highlight">{{ contextLines.highlight }}</mark>
              <span v-if="contextLines.after" class="context-after">{{ contextLines.after }}</span>
            </p>
          </div>
        </div>

        <!-- Suggestion if available -->
        <div v-if="currentAlert.suggestion" class="alert-suggestion">
          <div class="suggestion-header">
            <i class="pi pi-lightbulb"></i>
            <span>Sugerencia</span>
          </div>
          <p class="suggestion-text">{{ currentAlert.suggestion }}</p>
        </div>
      </section>

      <!-- Action Buttons -->
      <section class="action-section" aria-label="Acciones">
        <div class="primary-actions">
          <Button
            v-tooltip.bottom="'Aceptar corrección (A)'"
            label="Aceptar"
            icon="pi pi-check"
            severity="success"
            :disabled="updating || isResolved"
            :loading="updating"
            class="action-btn"
            @click="emit('resolve')"
          >
            <template #default>
              <span class="btn-content">
                <i class="pi pi-check"></i>
                <span>Aceptar</span>
                <kbd>A</kbd>
              </span>
            </template>
          </Button>

          <Button
            v-tooltip.bottom="'Descartar alerta (D)'"
            label="Descartar"
            icon="pi pi-times"
            severity="warn"
            :disabled="updating || isDismissed"
            class="action-btn"
            @click="emit('dismiss')"
          >
            <template #default>
              <span class="btn-content">
                <i class="pi pi-times"></i>
                <span>Descartar</span>
                <kbd>D</kbd>
              </span>
            </template>
          </Button>

          <Button
            v-tooltip.bottom="'Saltar sin acción (S)'"
            label="Saltar"
            icon="pi pi-forward"
            severity="secondary"
            outlined
            :disabled="updating"
            class="action-btn"
            @click="emit('skip')"
          >
            <template #default>
              <span class="btn-content">
                <i class="pi pi-forward"></i>
                <span>Saltar</span>
                <kbd>S</kbd>
              </span>
            </template>
          </Button>

          <Button
            v-tooltip.bottom="'Marcar para revisar después (F)'"
            label="Marcar"
            icon="pi pi-flag"
            severity="info"
            outlined
            :disabled="updating"
            class="action-btn"
            @click="emit('flag')"
          >
            <template #default>
              <span class="btn-content">
                <i class="pi pi-flag"></i>
                <span>Marcar</span>
                <kbd>F</kbd>
              </span>
            </template>
          </Button>
        </div>

        <!-- Navigation -->
        <div class="navigation-actions">
          <Button
            v-tooltip.bottom="'Anterior (←)'"
            icon="pi pi-chevron-left"
            label="Anterior"
            severity="secondary"
            text
            :disabled="!hasPrevious"
            @click="emit('previous')"
          />
          <Button
            v-tooltip.bottom="'Siguiente (→)'"
            icon="pi pi-chevron-right"
            icon-pos="right"
            label="Siguiente"
            severity="secondary"
            text
            :disabled="!hasNext"
            @click="emit('next')"
          />
        </div>

        <!-- Undo -->
        <div v-if="canUndo" class="undo-action">
          <Button
            v-tooltip.bottom="'Deshacer última acción (Ctrl+Z)'"
            icon="pi pi-replay"
            label="Deshacer"
            severity="secondary"
            text
            size="small"
            @click="emit('undo')"
          />
        </div>
      </section>

      <!-- Recent Actions -->
      <section v-if="recentActions.length > 0" class="history-section" aria-label="Acciones recientes">
        <div class="history-header">
          <span>Acciones recientes</span>
        </div>
        <div class="history-list">
          <div
            v-for="action in recentActions.slice(0, 5)"
            :key="action.alertId + action.timestamp.getTime()"
            class="history-item"
          >
            <Tag
              :severity="getActionSeverity(action.action)"
              size="small"
            >
              {{ getActionLabel(action.action) }}
            </Tag>
            <span class="history-time">{{ formatActionTime(action.timestamp) }}</span>
          </div>
        </div>
      </section>
    </main>

    <!-- Empty State -->
    <main v-else class="sequential-empty">
      <div class="empty-content">
        <i class="pi pi-check-circle empty-icon"></i>
        <h3>No hay más alertas</h3>
        <p>Has revisado todas las alertas con los filtros actuales.</p>
        <Button
          label="Volver a la lista"
          icon="pi pi-arrow-left"
          @click="emit('exit')"
        />
      </div>
    </main>

    <!-- Footer with Shortcuts -->
    <footer class="sequential-footer">
      <div class="shortcuts-list">
        <span
          v-for="shortcut in shortcuts"
          :key="shortcut.key"
          class="shortcut-item"
        >
          <kbd>{{ shortcut.key }}</kbd>
          <span>{{ shortcut.action }}</span>
        </span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.sequential-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--p-surface-0);
  border-radius: 12px;
  overflow: hidden;
}

/* Header */
.sequential-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.mode-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  max-width: 400px;
  margin: 0 2rem;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.progress-numbers {
  font-weight: 600;
  color: var(--p-text-color);
}

.progress-pending {
  color: var(--p-text-secondary-color);
}

.progress-bar {
  width: 100%;
  height: 6px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.close-button {
  margin-left: 0.5rem;
}

.toggle-resolved {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--p-text-secondary-color);
}

/* Main Content */
.sequential-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

/* Alert Section */
.alert-section {
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  overflow: hidden;
}

.status-banner {
  margin: 0;
  border-radius: 0;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: var(--p-surface-50);
  border-bottom: 1px solid var(--p-surface-200);
}

.alert-category {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.category-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--p-text-color);
}

.alert-location {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--p-text-secondary-color);
}

.alert-location .position {
  opacity: 0.7;
}

.alert-body {
  padding: 1.25rem;
}

.alert-title {
  margin: 0 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.alert-description {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--p-text-secondary-color);
  line-height: 1.5;
}

.alert-explanation {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--p-blue-50);
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--p-blue-700);
}

.alert-explanation i {
  margin-top: 2px;
}

/* Text Context */
.text-context {
  border-top: 1px solid var(--p-surface-200);
}

.context-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: var(--p-surface-50);
}

.context-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--p-text-secondary-color);
}

/* Multi-source navigation for inconsistency alerts */
.multi-source-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.nav-hint {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
}

.source-nav-btn {
  font-weight: 500;
}

.source-nav-btn :deep(.p-button-label) {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-body {
  padding: 1.25rem;
}

.excerpt {
  margin: 0;
  font-family: 'Georgia', serif;
  font-size: 1rem;
  line-height: 1.7;
  color: var(--p-text-color);
}

.excerpt .highlight {
  background: rgba(251, 191, 36, 0.3);
  padding: 2px 4px;
  border-radius: 2px;
}

.context-before,
.context-after {
  color: var(--p-text-secondary-color);
}

/* Suggestion */
.alert-suggestion {
  border-top: 1px solid var(--p-surface-200);
  padding: 1rem 1.25rem;
  background: var(--p-green-50);
}

.suggestion-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-green-700);
  margin-bottom: 0.5rem;
}

.suggestion-text {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--p-green-800);
}

/* Action Section */
.action-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.primary-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}

.action-btn {
  min-width: 120px;
}

.action-btn .btn-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn kbd {
  font-size: 0.6875rem;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
  font-family: monospace;
  margin-left: 0.25rem;
}

.navigation-actions {
  display: flex;
  gap: 1rem;
}

.undo-action {
  margin-top: 0.5rem;
}

/* History Section */
.history-section {
  background: var(--p-surface-50);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.history-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-secondary-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.history-time {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
}

/* Empty State */
.sequential-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
  padding: 2rem;
}

.empty-icon {
  font-size: 4rem;
  color: var(--p-green-500);
  margin-bottom: 1rem;
}

.empty-content h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  color: var(--p-text-color);
}

.empty-content p {
  margin: 0 0 1.5rem;
  color: var(--p-text-secondary-color);
}

/* Footer */
.sequential-footer {
  padding: 0.5rem 1.5rem;
  border-top: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
}

.shortcuts-list {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
}

.shortcut-item kbd {
  padding: 2px 6px;
  background: var(--p-surface-200);
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.6875rem;
}

/* Dark Mode */
:global(.dark) .sequential-mode {
  background: var(--p-surface-900);
}

:global(.dark) .sequential-header {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .mode-title {
  color: var(--p-text-color);
}

:global(.dark) .alert-section {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .alert-header {
  background: var(--p-surface-700);
  border-color: var(--p-surface-600);
}

:global(.dark) .context-header {
  background: var(--p-surface-700);
}

:global(.dark) .alert-explanation {
  background: var(--p-blue-900);
  color: var(--p-blue-200);
}

:global(.dark) .alert-suggestion {
  background: var(--p-green-900);
}

:global(.dark) .suggestion-header {
  color: var(--p-green-300);
}

:global(.dark) .suggestion-text {
  color: var(--p-green-200);
}

:global(.dark) .history-section {
  background: var(--p-surface-800);
}

:global(.dark) .sequential-footer {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .shortcut-item kbd {
  background: var(--p-surface-700);
}

:global(.dark) .action-btn kbd {
  background: rgba(255, 255, 255, 0.1);
}
</style>
