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
              optionLabel="label"
              optionValue="value"
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
                <span class="issue-chapter" v-if="issue.title">
                  {{ issue.title }}
                </span>
              </div>
              <p class="issue-description">{{ issue.description }}</p>
              <p class="issue-explanation" v-if="issue.explanation">{{ issue.explanation }}</p>
              <p class="issue-suggestion" v-if="issue.suggestion">
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

      <!-- Selected Chapter Detail -->
      <Card v-if="selectedChapter" class="detail-card">
        <template #title>
          <div class="detail-header">
            <span>
              <i class="pi pi-file"></i>
              {{ selectedChapter.title || `Capítulo ${selectedChapter.segment_id}` }}
            </span>
            <Button icon="pi pi-times" text rounded @click="selectedChapter = null" />
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
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/pacing-analysis`
    )
    const data = await response.json()

    if (data.success) {
      report.value = data.data
      // Calculate max words for bar scaling
      if (report.value.chapter_metrics?.length > 0) {
        maxWords.value = Math.max(...report.value.chapter_metrics.map((c: any) => c.word_count))
      }
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing pacing:', error)
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
</style>
