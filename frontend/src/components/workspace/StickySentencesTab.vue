<template>
  <div class="sticky-sentences-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-exclamation-triangle"></i>
          Oraciones Pesadas
        </h3>
        <p class="subtitle">
          Detecta oraciones con exceso de palabras funcionales que dificultan la lectura.
        </p>
      </div>
      <div class="header-controls">
        <div class="threshold-control">
          <label>Umbral:</label>
          <Slider v-model="threshold" :min="30" :max="60" :step="5" class="threshold-slider" />
          <span class="threshold-value">{{ threshold }}%</span>
        </div>
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
      <p>Analizando oraciones pesadas...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar oraciones pesadas.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="getScoreClass(report.global_stats.avg_glue_percentage)">
                {{ report.global_stats.avg_glue_percentage }}%
              </div>
              <div class="stat-label">Promedio Glue Words</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_sticky_sentences }}</div>
              <div class="stat-label">Oraciones Pesadas</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_sentences }}</div>
              <div class="stat-label">Total Oraciones</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value severity-high">
                {{ report.global_stats.by_severity?.critical || 0 }}
              </div>
              <div class="stat-label">Críticas</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Severity Filter -->
      <div class="filter-section">
        <span class="filter-label">Mostrar:</span>
        <SelectButton v-model="severityFilter" :options="severityOptions" optionLabel="label" optionValue="value" />
      </div>

      <!-- Chapters Accordion -->
      <Accordion :multiple="true" :activeIndex="[0]" class="chapters-accordion">
        <AccordionPanel v-for="chapter in filteredChapters" :key="chapter.chapter_number" :value="String(chapter.chapter_number)">
          <AccordionHeader>
            <div class="chapter-header">
              <span class="chapter-title">
                {{ chapter.chapter_title }}
              </span>
              <div class="chapter-stats">
                <Tag
                  v-if="chapter.sticky_count > 0"
                  :severity="getChapterSeverity(chapter)"
                  :value="`${chapter.sticky_count} pesadas`"
                />
                <span class="chapter-avg" :class="getScoreClass(chapter.avg_glue_percentage)">
                  {{ chapter.avg_glue_percentage }}% promedio
                </span>
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <!-- Chapter distribution -->
            <div class="chapter-distribution">
              <div class="dist-bar">
                <div
                  class="dist-segment clean"
                  :style="{ width: getDistributionWidth(chapter, 'clean') }"
                  v-tooltip.top="'Limpias: ' + chapter.distribution.clean"
                ></div>
                <div
                  class="dist-segment borderline"
                  :style="{ width: getDistributionWidth(chapter, 'borderline') }"
                  v-tooltip.top="'Límite: ' + chapter.distribution.borderline"
                ></div>
                <div
                  class="dist-segment sticky"
                  :style="{ width: getDistributionWidth(chapter, 'sticky') }"
                  v-tooltip.top="'Pesadas: ' + chapter.distribution.sticky"
                ></div>
              </div>
              <div class="dist-legend">
                <span class="legend-item"><span class="dot clean"></span> Limpias</span>
                <span class="legend-item"><span class="dot borderline"></span> Límite (40-45%)</span>
                <span class="legend-item"><span class="dot sticky"></span> Pesadas (>45%)</span>
              </div>
            </div>

            <!-- Sticky sentences list -->
            <div v-if="chapter.sticky_sentences.length > 0" class="sticky-list">
              <div
                v-for="(sentence, idx) in getFilteredSentences(chapter)"
                :key="idx"
                class="sticky-item"
                :class="'severity-' + sentence.severity"
              >
                <div class="sticky-header">
                  <Tag :severity="getSeverityColor(sentence.severity)" :value="sentence.glue_percentage_display" />
                  <span class="sticky-stats">
                    {{ sentence.glue_words }}/{{ sentence.total_words }} glue words
                  </span>
                </div>
                <p class="sticky-text">{{ sentence.text }}</p>
                <div class="sticky-glue-words">
                  <span class="glue-label">Palabras pegamento:</span>
                  <span
                    v-for="(word, wIdx) in sentence.glue_word_list"
                    :key="wIdx"
                    class="glue-word"
                  >{{ word }}</span>
                </div>
                <p class="sticky-recommendation">
                  <i class="pi pi-lightbulb"></i>
                  {{ sentence.recommendation }}
                </p>
              </div>
            </div>

            <Message v-else severity="success" :closable="false">
              Este capítulo no tiene oraciones pesadas.
            </Message>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Slider from 'primevue/slider'
import SelectButton from 'primevue/selectbutton'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const threshold = ref(40)
const report = ref<any>(null)
const severityFilter = ref('all')

const severityOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Críticas', value: 'critical' },
  { label: 'Altas', value: 'high' },
  { label: 'Medias', value: 'medium' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Filtered chapters (only those with sticky sentences based on filter)
const filteredChapters = computed(() => {
  if (!report.value?.chapters) return []

  return report.value.chapters.filter((ch: any) => {
    if (severityFilter.value === 'all') return ch.sticky_count > 0
    return ch.by_severity?.[severityFilter.value] > 0
  })
})

// Get filtered sentences for a chapter
function getFilteredSentences(chapter: any) {
  if (severityFilter.value === 'all') return chapter.sticky_sentences
  return chapter.sticky_sentences.filter((s: any) => s.severity === severityFilter.value)
}

// Analyze
async function analyze() {
  loading.value = true
  try {
    const thresholdDecimal = threshold.value / 100
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/sticky-sentences?threshold=${thresholdDecimal}`
    )
    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing sticky sentences:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron analizar las oraciones pesadas',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getScoreClass(percentage: number): string {
  if (percentage >= 50) return 'severity-critical'
  if (percentage >= 45) return 'severity-high'
  if (percentage >= 40) return 'severity-medium'
  return 'severity-low'
}

function getChapterSeverity(chapter: any): string {
  if (chapter.by_severity?.critical > 0) return 'danger'
  if (chapter.by_severity?.high > 0) return 'warn'
  if (chapter.by_severity?.medium > 0) return 'info'
  return 'secondary'
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'danger'
    case 'high': return 'warn'
    case 'medium': return 'info'
    default: return 'secondary'
  }
}

function getDistributionWidth(chapter: any, type: string): string {
  const total = chapter.distribution.clean + chapter.distribution.borderline + chapter.distribution.sticky
  if (total === 0) return '0%'
  return `${(chapter.distribution[type] / total) * 100}%`
}
</script>

<style scoped>
.sticky-sentences-tab {
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

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.threshold-control label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.threshold-slider {
  width: 100px;
}

.threshold-value {
  font-weight: var(--ds-font-weight-medium);
  min-width: 40px;
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
.severity-critical { color: #ef4444; }
.severity-high { color: #f97316; }
.severity-medium { color: #eab308; }
.severity-low { color: #6b7280; }

/* Filter section */
.filter-section {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.filter-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Chapters accordion */
.chapters-accordion {
  flex: 1;
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: var(--ds-space-3);
}

.chapter-title {
  font-weight: var(--ds-font-weight-medium);
}

.chapter-stats {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.chapter-avg {
  font-size: var(--ds-font-size-sm);
}

/* Distribution bar */
.chapter-distribution {
  margin-bottom: var(--ds-space-4);
}

.dist-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--ds-surface-hover);
}

.dist-segment {
  transition: width 0.3s ease;
}

.dist-segment.clean {
  background: #10b981;
}

.dist-segment.borderline {
  background: #eab308;
}

.dist-segment.sticky {
  background: #ef4444;
}

.dist-legend {
  display: flex;
  gap: var(--ds-space-4);
  margin-top: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-item .dot.clean { background: #10b981; }
.legend-item .dot.borderline { background: #eab308; }
.legend-item .dot.sticky { background: #ef4444; }

/* Sticky sentences list */
.sticky-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.sticky-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-surface-border);
}

.sticky-item.severity-critical {
  border-left-color: #ef4444;
}

.sticky-item.severity-high {
  border-left-color: #f97316;
}

.sticky-item.severity-medium {
  border-left-color: #eab308;
}

.sticky-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.sticky-stats {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.sticky-text {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  line-height: 1.6;
}

.sticky-glue-words {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ds-space-1);
  margin-bottom: var(--ds-space-2);
}

.glue-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.glue-word {
  display: inline-block;
  padding: 2px 6px;
  background: var(--ds-color-primary-soft);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-primary);
}

.sticky-recommendation {
  margin: 0;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  font-style: italic;
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-1);
}

.sticky-recommendation i {
  color: var(--p-yellow-500);
  margin-top: 2px;
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

/* Responsive */
@media (max-width: 768px) {
  .tab-header {
    flex-direction: column;
  }

  .header-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
