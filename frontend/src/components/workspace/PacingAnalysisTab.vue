<template>
  <div class="pacing-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-forward"></i>
          Ritmo Narrativo
        </h3>
        <p class="subtitle">
          Analiza el equilibrio entre capítulos, diálogo y narración.
        </p>
        <!-- Estado del análisis -->
        <p v-if="lastAnalysis" class="analysis-status success">
          <i class="pi pi-check-circle"></i>
          Último análisis: {{ lastAnalysis.toLocaleTimeString() }}
        </p>
        <p v-else-if="analysisError" class="analysis-status error">
          <i class="pi pi-exclamation-triangle"></i>
          Error: {{ analysisError }}
        </p>
        <p v-else class="analysis-status pending">
          <i class="pi pi-info-circle"></i>
          No analizado
        </p>
      </div>
      <div class="header-controls">
        <Button
          label="Analizar"
          icon="pi pi-refresh"
          :loading="loading"
          @click="analyze"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Analizando ritmo narrativo...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para evaluar el ritmo narrativo.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Summary Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.summary.total_chapters }}</div>
              <div class="stat-label">Capítulos</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ formatNumber(report.summary.avg_chapter_words) }}</div>
              <div class="stat-label">Palabras / Cap.</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ formatPercent(report.summary.avg_dialogue_ratio) }}</div>
              <div class="stat-label">Diálogo</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="getIssuesClass(report.summary.issues_count)">
                {{ report.summary.issues_count }}
              </div>
              <div class="stat-label">Observaciones</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Chapter Overview Chart -->
      <Card class="chart-card">
        <template #title>
          <i class="pi pi-chart-bar"></i>
          Distribución de Capítulos
        </template>
        <template #content>
          <div class="chapter-bars">
            <div
              v-for="chapter in report.chapter_metrics"
              :key="chapter.segment_id"
              class="chapter-bar-container"
              @click="selectChapter(chapter)"
            >
              <div class="chapter-bar-info">
                <span class="chapter-num">{{ chapter.segment_id }}</span>
                <span class="chapter-words">{{ formatNumber(chapter.word_count) }}</span>
              </div>
              <div class="chapter-bar-wrapper">
                <div
                  class="chapter-bar"
                  :class="getChapterBarClass(chapter)"
                  :style="{ width: getBarWidth(chapter.word_count) + '%' }"
                >
                  <div
                    class="dialogue-bar"
                    :style="{ width: (chapter.dialogue_ratio * 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          <div class="legend">
            <span class="legend-item">
              <span class="legend-color narration"></span> Narración
            </span>
            <span class="legend-item">
              <span class="legend-color dialogue"></span> Diálogo
            </span>
          </div>
        </template>
      </Card>

      <!-- Issues Section -->
      <Card v-if="report.issues.length > 0" class="issues-card">
        <template #title>
          <i class="pi pi-exclamation-triangle"></i>
          Observaciones ({{ report.issues.length }})
        </template>
        <template #content>
          <!-- Severity Filter -->
          <div class="filter-section">
            <span class="filter-label">Filtrar:</span>
            <SelectButton
              v-model="severityFilter"
              :options="severityOptions"
              option-label="label"
              option-value="value"
            />
          </div>

          <div class="issues-list">
            <div
              v-for="(issue, idx) in filteredIssues"
              :key="idx"
              class="issue-item"
              :class="'severity-' + issue.severity"
            >
              <div class="issue-header">
                <Tag :severity="getSeverityColor(issue.severity)" :value="getSeverityLabel(issue.severity)" />
                <Tag severity="secondary" :value="getIssueTypeLabel(issue.issue_type)" />
                <span v-if="issue.title" class="issue-chapter">
                  {{ issue.title }}
                </span>
              </div>
              <p class="issue-description">{{ issue.description }}</p>
              <p v-if="issue.explanation" class="issue-explanation">{{ issue.explanation }}</p>
              <p v-if="issue.suggestion" class="issue-suggestion">
                <i class="pi pi-lightbulb"></i> {{ issue.suggestion }}
              </p>
            </div>
          </div>
        </template>
      </Card>

      <!-- No Issues Message -->
      <Message v-else severity="success" :closable="false" class="no-issues-message">
        <i class="pi pi-check-circle"></i>
        El ritmo narrativo del manuscrito es equilibrado. No se detectaron problemas.
      </Message>

      <!-- Recommendations -->
      <Card v-if="report.recommendations?.length > 0" class="recommendations-card">
        <template #title>
          <i class="pi pi-lightbulb"></i>
          Recomendaciones
        </template>
        <template #content>
          <ul class="recommendations-list">
            <li v-for="(rec, idx) in report.recommendations" :key="idx">{{ rec }}</li>
          </ul>
        </template>
      </Card>

      <!-- Genre Comparison -->
      <Card v-if="genreComparison" class="genre-card">
        <template #title>
          <i class="pi pi-chart-line"></i>
          Comparación con {{ genreComparison.genre.genre_label }}
        </template>
        <template #content>
          <!-- Percentile gauges -->
          <div v-if="genreComparison.percentiles" class="percentile-grid">
            <div
              v-for="(pct, metric) in genreComparison.percentiles"
              :key="metric"
              class="percentile-item"
            >
              <span class="percentile-label">{{ getMetricLabel(String(metric)) }}</span>
              <div class="percentile-bar-bg">
                <div class="percentile-bar-fill" :style="{ width: pct + '%' }" :class="getPercentileClass(pct)"></div>
                <div class="percentile-marker" :style="{ left: pct + '%' }">
                  <span class="percentile-value">P{{ pct }}</span>
                </div>
              </div>
              <div class="percentile-range">
                <span>P0</span>
                <span>P50</span>
                <span>P100</span>
              </div>
            </div>
          </div>

          <!-- Deviations -->
          <div v-if="genreComparison.deviations?.length > 0" class="genre-deviations">
            <div v-for="(dev, idx) in genreComparison.deviations" :key="idx" class="deviation-item">
              <Tag :severity="dev.status === 'below' ? 'warning' : dev.status === 'above' ? 'danger' : 'info'" :value="dev.status === 'below' ? 'Bajo' : dev.status === 'above' ? 'Alto' : 'Diferente'" />
              <span class="deviation-msg">{{ dev.message }}</span>
            </div>
          </div>
          <Message v-else severity="success" :closable="false">
            Todas las métricas están dentro del rango esperado para este género.
          </Message>

          <!-- Suggestions -->
          <div v-if="genreComparison.suggestions?.length > 0" class="genre-suggestions">
            <div v-for="(sug, idx) in genreComparison.suggestions" :key="idx" class="suggestion-item">
              <Tag :severity="sug.priority === 'high' ? 'danger' : sug.priority === 'medium' ? 'warning' : 'info'" :value="sug.priority" />
              <span>{{ sug.suggestion }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Genre Comparison Button (when not loaded yet) -->
      <div v-else-if="report && !genreLoading" class="genre-compare-prompt">
        <Button
          label="Comparar con género"
          icon="pi pi-chart-line"
          outlined
          @click="loadGenreComparison"
        />
      </div>
      <div v-else-if="genreLoading" class="loading-state" style="padding: 1rem;">
        <ProgressSpinner style="width: 30px; height: 30px;" />
        <span>Comparando con género...</span>
      </div>

      <!-- Selected Chapter Detail -->
      <Card v-if="selectedChapter" class="detail-card">
        <template #title>
          <div class="detail-header">
            <span>
              <i class="pi pi-file"></i>
              {{ selectedChapter.title || `Capítulo ${selectedChapter.segment_id}` }}
            </span>
            <Button icon="pi pi-times" text rounded aria-label="Cerrar detalle" @click="selectedChapter = null" />
          </div>
        </template>
        <template #content>
          <div class="detail-metrics">
            <div class="metric">
              <span class="metric-label">Palabras</span>
              <span class="metric-value">{{ formatNumber(selectedChapter.word_count) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Oraciones</span>
              <span class="metric-value">{{ selectedChapter.sentence_count }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Párrafos</span>
              <span class="metric-value">{{ selectedChapter.paragraph_count }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Diálogo</span>
              <span class="metric-value">{{ formatPercent(selectedChapter.dialogue_ratio) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Líneas de diálogo</span>
              <span class="metric-value">{{ selectedChapter.dialogue_lines }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Long. media oración</span>
              <span class="metric-value">{{ selectedChapter.avg_sentence_length?.toFixed(1) }} palabras</span>
            </div>
            <div class="metric">
              <span class="metric-label">Densidad léxica</span>
              <span class="metric-value">{{ formatPercent(selectedChapter.lexical_density) }}</span>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/apiClient'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const report = ref<any>(null)
const severityFilter = ref('all')
const selectedChapter = ref<any>(null)
const maxWords = ref(0)
const genreComparison = ref<any>(null)
const genreLoading = ref(false)
const lastAnalysis = ref<Date | null>(null)
const analysisError = ref<string | null>(null)

const severityOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Problemas', value: 'issue' },
  { label: 'Avisos', value: 'warning' },
  { label: 'Sugerencias', value: 'suggestion' },
  { label: 'Info', value: 'info' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Filtered issues
const filteredIssues = computed(() => {
  if (!report.value?.issues) return []
  if (severityFilter.value === 'all') return report.value.issues
  return report.value.issues.filter((i: any) => i.severity === severityFilter.value)
})

// Analyze
async function analyze() {
  loading.value = true
  selectedChapter.value = null
  analysisError.value = null
  try {
    const data = await api.getRaw<any>(`/api/projects/${props.projectId}/pacing-analysis`)

    if (data.success) {
      report.value = data.data
      lastAnalysis.value = new Date()
      // Calculate max words for bar scaling
      if (report.value.chapter_metrics?.length > 0) {
        maxWords.value = Math.max(...report.value.chapter_metrics.map((c: any) => c.word_count))
      }
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing pacing:', error)
    analysisError.value = error instanceof Error ? error.message : 'Error desconocido'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar el ritmo narrativo',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Genre comparison
async function loadGenreComparison() {
  genreLoading.value = true
  try {
    // Fetch document type to get genre code
    const typeData = await api.getRaw<any>(`/api/projects/${props.projectId}/document-type`)
    const genreCode = typeData.success ? (typeData.data?.document_type || 'FIC') : 'FIC'

    const data = await api.getRaw<any>(`/api/projects/${props.projectId}/pacing-analysis/genre-comparison?genre_code=${genreCode}`)
    if (data.success) {
      genreComparison.value = data.data.comparison
    }
  } catch (error) {
    console.error('Error loading genre comparison:', error)
  } finally {
    genreLoading.value = false
  }
}

const metricLabels: Record<string, string> = {
  avg_chapter_words: 'Palabras / capítulo',
  dialogue_ratio: 'Ratio de diálogo',
  avg_sentence_length: 'Long. oración',
  avg_tension: 'Tensión media',
}

function getMetricLabel(metric: string): string {
  return metricLabels[metric] || metric
}

function getPercentileClass(pct: number): string {
  if (pct < 10 || pct > 90) return 'pct-extreme'
  if (pct < 25 || pct > 75) return 'pct-moderate'
  return 'pct-normal'
}

// Helper functions
function formatNumber(num: number): string {
  if (!num && num !== 0) return '0'
  return Math.round(num).toLocaleString('es-ES')
}

function formatPercent(ratio: number): string {
  if (!ratio && ratio !== 0) return '0%'
  return `${Math.round(ratio * 100)}%`
}

function getBarWidth(words: number): number {
  if (!maxWords.value || !words) return 0
  return (words / maxWords.value) * 100
}

function getChapterBarClass(chapter: any): string {
  const avg = report.value?.summary?.avg_chapter_words || 0
  if (!avg) return ''

  const ratio = chapter.word_count / avg
  if (ratio > 2) return 'too-long'
  if (ratio < 0.5) return 'too-short'
  return ''
}

function getIssuesClass(count: number): string {
  if (count === 0) return 'severity-success'
  if (count <= 3) return 'severity-info'
  if (count <= 6) return 'severity-warning'
  return 'severity-danger'
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'issue': return 'danger'
    case 'warning': return 'warn'
    case 'suggestion': return 'info'
    case 'info': return 'secondary'
    default: return 'secondary'
  }
}

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case 'issue': return 'Problema'
    case 'warning': return 'Aviso'
    case 'suggestion': return 'Sugerencia'
    case 'info': return 'Info'
    default: return severity
  }
}

function getIssueTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'chapter_too_short': 'Cap. corto',
    'chapter_too_long': 'Cap. largo',
    'unbalanced_chapters': 'Desequilibrio',
    'too_much_dialogue': 'Mucho diálogo',
    'too_little_dialogue': 'Poco diálogo',
    'dense_text_block': 'Bloque denso',
    'sparse_text_block': 'Bloque disperso',
    'rhythm_shift': 'Cambio ritmo',
    'scene_too_short': 'Escena corta',
    'scene_too_long': 'Escena larga',
  }
  return labels[type] || type
}

function selectChapter(chapter: any) {
  selectedChapter.value = selectedChapter.value?.segment_id === chapter.segment_id ? null : chapter
}
</script>

<style scoped>
.pacing-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-3);
  height: 100%;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
}

.header-left h3 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0;
  font-size: var(--ds-font-size-lg);
}

.header-left .subtitle {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.header-left .analysis-status {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
}

.header-left .analysis-status.success {
  color: var(--green-500);
}

.header-left .analysis-status.error {
  color: var(--red-500);
}

.header-left .analysis-status.pending {
  color: var(--text-color-secondary);
}

/* Loading & Empty states */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-8);
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 2rem;
}

/* Stats cards */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--ds-space-3);
}

.stat-card :deep(.p-card-body) {
  padding: var(--ds-space-3);
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-top: var(--ds-space-1);
}

/* Severity colors */
.severity-success { color: #22c55e; }
.severity-info { color: #3b82f6; }
.severity-warning { color: #f97316; }
.severity-danger { color: #ef4444; }

/* Chart card */
.chart-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.chapter-bars {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.chapter-bar-container {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  cursor: pointer;
  padding: var(--ds-space-1);
  border-radius: var(--ds-radius-sm);
  transition: background-color 0.15s;
}

.chapter-bar-container:hover {
  background: var(--ds-surface-hover);
}

.chapter-bar-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 60px;
}

.chapter-num {
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-sm);
}

.chapter-words {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.chapter-bar-wrapper {
  flex: 1;
  height: 20px;
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-sm);
  overflow: hidden;
}

.chapter-bar {
  height: 100%;
  background: var(--p-primary-300);
  border-radius: var(--ds-radius-sm);
  position: relative;
  transition: width 0.3s ease;
}

.chapter-bar.too-long {
  background: var(--p-orange-300);
}

.chapter-bar.too-short {
  background: var(--p-yellow-300);
}

.dialogue-bar {
  position: absolute;
  right: 0;
  top: 0;
  height: 100%;
  background: var(--p-blue-400);
  opacity: 0.8;
}

.legend {
  display: flex;
  justify-content: center;
  gap: var(--ds-space-4);
  margin-top: var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.narration {
  background: var(--p-primary-300);
}

.legend-color.dialogue {
  background: var(--p-blue-400);
}

/* Filter section */
.filter-section {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  margin-bottom: var(--ds-space-3);
}

.filter-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Issues card */
.issues-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.issue-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-surface-border);
}

.issue-item.severity-issue {
  border-left-color: #ef4444;
}

.issue-item.severity-warning {
  border-left-color: #f97316;
}

.issue-item.severity-suggestion {
  border-left-color: #3b82f6;
}

.issue-item.severity-info {
  border-left-color: #6b7280;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-2);
}

.issue-chapter {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  margin-left: auto;
}

.issue-description {
  margin: 0 0 var(--ds-space-2);
  font-weight: var(--ds-font-weight-medium);
}

.issue-explanation {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.issue-suggestion {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--p-primary-400);
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-1);
}

.issue-suggestion i {
  margin-top: 2px;
}

/* No issues message */
.no-issues-message {
  margin: 0;
}

.no-issues-message i {
  margin-right: var(--ds-space-2);
}

/* Recommendations card */
.recommendations-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.recommendations-list {
  margin: 0;
  padding-left: var(--ds-space-4);
}

.recommendations-list li {
  margin-bottom: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Detail card */
.detail-card {
  border: 1px solid var(--p-primary-300);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-header span {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.detail-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--ds-space-3);
}

.metric {
  display: flex;
  flex-direction: column;
  padding: var(--ds-space-2);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-sm);
}

.metric-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.metric-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
}

/* Responsive */
@media (max-width: 768px) {
  .tab-header {
    flex-direction: column;
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Genre comparison */
.genre-card {
  border-left: 3px solid var(--primary-color);
}

.genre-compare-prompt {
  display: flex;
  justify-content: center;
  padding: 0.5rem 0;
}

.percentile-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-bottom: 1rem;
}

.percentile-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.percentile-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.percentile-bar-bg {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: var(--surface-200);
}

.percentile-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.percentile-bar-fill.pct-normal { background: var(--green-400); }
.percentile-bar-fill.pct-moderate { background: var(--orange-400); }
.percentile-bar-fill.pct-extreme { background: var(--red-400); }

.percentile-marker {
  position: absolute;
  top: -18px;
  transform: translateX(-50%);
}

.percentile-value {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-color);
}

.percentile-range {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: var(--text-color-secondary);
}

.genre-deviations {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.deviation-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.deviation-msg {
  color: var(--text-color-secondary);
}

.genre-suggestions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .percentile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
