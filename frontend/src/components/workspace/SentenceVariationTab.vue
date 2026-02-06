<template>
  <div class="sentence-variation-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-chart-bar"></i>
          Variación de Oraciones
        </h3>
        <p class="subtitle">
          Visualiza la distribución de longitudes de oración para evaluar el ritmo del texto.
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
      <p>Analizando variación de oraciones...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para ver la variación de oraciones.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_sentences }}</div>
              <div class="stat-label">Oraciones</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.avg_length }}</div>
              <div class="stat-label">Promedio palabras</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="getVariationClass(report.global_stats.variation_coefficient)">
                {{ report.global_stats.variation_coefficient }}%
              </div>
              <div class="stat-label">Variación</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.min_length }}-{{ report.global_stats.max_length }}</div>
              <div class="stat-label">Rango</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Global Distribution -->
      <Card class="distribution-card">
        <template #title>
          <i class="pi pi-chart-pie"></i>
          Distribución Global
        </template>
        <template #content>
          <div class="distribution-bars">
            <div v-for="(count, category) in report.global_distribution" :key="category" class="dist-row">
              <span class="dist-label">{{ getCategoryLabel(String(category)) }}</span>
              <div class="dist-bar-container">
                <div
                  class="dist-bar"
                  :class="'cat-' + category"
                  :style="{ width: getBarWidth(count, report.global_stats.total_sentences) }"
                ></div>
              </div>
              <span class="dist-count">{{ count }} ({{ getPercentage(count, report.global_stats.total_sentences) }}%)</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Issues -->
      <Card v-if="report.all_issues?.length > 0" class="issues-card">
        <template #title>
          <i class="pi pi-exclamation-triangle"></i>
          Problemas Detectados
        </template>
        <template #content>
          <div class="issues-list">
            <div v-for="(issue, idx) in report.all_issues" :key="idx" class="issue-item">
              <Tag :severity="getIssueSeverity(issue.type)" :value="getIssueLabel(issue.type)" />
              <span class="issue-message">{{ issue.message }}</span>
              <span v-if="issue.chapter" class="issue-chapter">Cap. {{ issue.chapter }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Chapters -->
      <Accordion :multiple="true" :active-index="[0]" class="chapters-accordion">
        <AccordionPanel v-for="chapter in report.chapters" :key="chapter.chapter_number" :value="String(chapter.chapter_number)">
          <AccordionHeader>
            <div class="chapter-header">
              <span class="chapter-title">{{ chapter.chapter_title }}</span>
              <div class="chapter-stats">
                <span class="chapter-stat">{{ chapter.statistics.total_sentences }} oraciones</span>
                <Tag
                  :severity="getVariationSeverity(chapter.statistics.variation_coefficient)"
                  :value="`${chapter.statistics.variation_coefficient}% var`"
                />
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <!-- Sentence visualization -->
            <div class="sentence-graph">
              <div class="graph-y-axis">
                <span>40+</span>
                <span>30</span>
                <span>20</span>
                <span>10</span>
                <span>0</span>
              </div>
              <div class="graph-bars">
                <div
                  v-for="(sent, idx) in chapter.sentences"
                  :key="idx"
                  v-tooltip.top="getSentenceTooltip(sent)"
                  class="sentence-bar-wrapper"
                >
                  <div
                    class="sentence-bar"
                    :class="getSentenceClass(sent.length)"
                    :style="{ height: getSentenceHeight(sent.length) }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- Legend -->
            <div class="graph-legend">
              <span class="legend-item"><span class="dot very-short"></span> Muy corta (&lt;5)</span>
              <span class="legend-item"><span class="dot short"></span> Corta (5-9)</span>
              <span class="legend-item"><span class="dot medium"></span> Media (10-19)</span>
              <span class="legend-item"><span class="dot long"></span> Larga (20-34)</span>
              <span class="legend-item"><span class="dot very-long"></span> Muy larga (35+)</span>
            </div>

            <!-- Chapter stats -->
            <div class="chapter-detail-stats">
              <div class="detail-stat">
                <span class="detail-label">Promedio:</span>
                <span class="detail-value">{{ chapter.statistics.avg_length }} palabras</span>
              </div>
              <div class="detail-stat">
                <span class="detail-label">Mediana:</span>
                <span class="detail-value">{{ chapter.statistics.median_length }} palabras</span>
              </div>
              <div class="detail-stat">
                <span class="detail-label">Desv. estándar:</span>
                <span class="detail-value">{{ chapter.statistics.std_deviation }}</span>
              </div>
              <div class="detail-stat">
                <span class="detail-label">Rango:</span>
                <span class="detail-value">{{ chapter.statistics.min_length }} - {{ chapter.statistics.max_length }}</span>
              </div>
            </div>
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
import { ref, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/apiClient'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const report = ref<any>(null)

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Analyze
async function analyze() {
  loading.value = true
  try {
    const data = await api.getRaw<{ success: boolean; data: any; error?: string }>(
      `/api/projects/${props.projectId}/sentence-variation`
    )

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing sentence variation:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar la variación de oraciones',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getVariationClass(coefficient: number): string {
  if (coefficient < 20) return 'variation-low'
  if (coefficient < 35) return 'variation-moderate'
  if (coefficient > 60) return 'variation-high'
  return 'variation-good'
}

function getVariationSeverity(coefficient: number): string {
  if (coefficient < 20) return 'danger'
  if (coefficient < 35) return 'warn'
  if (coefficient > 60) return 'info'
  return 'success'
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    very_short: 'Muy cortas (<5)',
    short: 'Cortas (5-9)',
    medium: 'Medias (10-19)',
    long: 'Largas (20-34)',
    very_long: 'Muy largas (35+)',
  }
  return labels[category] || category
}

function getBarWidth(count: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.max(2, (count / total) * 100)}%`
}

function getPercentage(count: number, total: number): string {
  if (total === 0) return '0'
  return ((count / total) * 100).toFixed(1)
}

function getIssueSeverity(type: string): string {
  switch (type) {
    case 'monotonous': return 'warn'
    case 'too_many_long': return 'danger'
    case 'choppy': return 'warn'
    default: return 'info'
  }
}

function getIssueLabel(type: string): string {
  const labels: Record<string, string> = {
    monotonous: 'Monótono',
    too_many_long: 'Oraciones largas',
    choppy: 'Entrecortado',
  }
  return labels[type] || type
}

function getSentenceHeight(length: number): string {
  const maxHeight = 120 // px
  const maxLength = 50 // max words for scaling
  const height = Math.min(maxHeight, (length / maxLength) * maxHeight)
  return `${Math.max(4, height)}px`
}

function getSentenceClass(length: number): string {
  if (length < 5) return 'very-short'
  if (length < 10) return 'short'
  if (length < 20) return 'medium'
  if (length < 35) return 'long'
  return 'very-long'
}

function getSentenceTooltip(sent: any): string {
  let text = `${sent.length} palabras`
  if (sent.text) {
    text += `\n"${sent.text}"`
  }
  return text
}
</script>

<style scoped>
.sentence-variation-tab {
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

/* Variation colors */
.variation-low { color: #ef4444; }
.variation-moderate { color: #f97316; }
.variation-good { color: #10b981; }
.variation-high { color: #3b82f6; }

/* Distribution card */
.distribution-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.dist-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.dist-label {
  width: 140px;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.dist-bar-container {
  flex: 1;
  height: 16px;
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-sm);
  overflow: hidden;
}

.dist-bar {
  height: 100%;
  border-radius: var(--ds-radius-sm);
  transition: width 0.3s ease;
}

.dist-bar.cat-very_short { background: #818cf8; }
.dist-bar.cat-short { background: #34d399; }
.dist-bar.cat-medium { background: #60a5fa; }
.dist-bar.cat-long { background: #fbbf24; }
.dist-bar.cat-very_long { background: #f87171; }

.dist-count {
  width: 80px;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  text-align: right;
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
  gap: var(--ds-space-2);
}

.issue-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-sm);
}

.issue-message {
  flex: 1;
  font-size: var(--ds-font-size-sm);
}

.issue-chapter {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
}

/* Chapters accordion */
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

.chapter-stat {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

/* Sentence graph */
.sentence-graph {
  display: flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  margin-bottom: var(--ds-space-3);
  overflow-x: auto;
}

.graph-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  padding-right: var(--ds-space-2);
  border-right: 1px solid var(--ds-surface-border);
  height: 120px;
}

.graph-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 120px;
  flex: 1;
  min-width: 0;
}

.sentence-bar-wrapper {
  flex: 1;
  min-width: 3px;
  max-width: 8px;
  height: 100%;
  display: flex;
  align-items: flex-end;
  cursor: pointer;
}

.sentence-bar {
  width: 100%;
  border-radius: 2px 2px 0 0;
  transition: opacity 0.2s;
}

.sentence-bar-wrapper:hover .sentence-bar {
  opacity: 0.8;
}

.sentence-bar.very-short { background: #818cf8; }
.sentence-bar.short { background: #34d399; }
.sentence-bar.medium { background: #60a5fa; }
.sentence-bar.long { background: #fbbf24; }
.sentence-bar.very-long { background: #f87171; }

/* Legend */
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-4);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-3);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item .dot.very-short { background: #818cf8; }
.legend-item .dot.short { background: #34d399; }
.legend-item .dot.medium { background: #60a5fa; }
.legend-item .dot.long { background: #fbbf24; }
.legend-item .dot.very-long { background: #f87171; }

/* Chapter detail stats */
.chapter-detail-stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-4);
}

.detail-stat {
  display: flex;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
}

.detail-label {
  color: var(--ds-color-text-secondary);
}

.detail-value {
  font-weight: var(--ds-font-weight-medium);
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

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .dist-label {
    width: 100px;
  }

  .graph-legend {
    gap: var(--ds-space-2);
  }
}
</style>
