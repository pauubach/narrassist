<script setup lang="ts">
/**
 * NarrativeHealthTab - Chequeo de salud narrativa
 *
 * Evalúa 12 dimensiones narrativas esenciales: protagonista, conflicto,
 * objetivo, apuestas, clímax, resolución, arco emocional, ritmo,
 * coherencia, estructura, equilibrio de personajes y tramas cerradas.
 */

import { ref, onMounted, computed, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import { api } from '@/services/apiClient'
import AnalysisErrorState from '@/components/shared/AnalysisErrorState.vue'

const props = defineProps<{
  projectId: number
}>()

interface DimensionScore {
  dimension: string
  name: string
  icon: string
  score: number
  status: 'ok' | 'warning' | 'critical' | 'n_a'
  explanation: string
  suggestion: string
  evidence: string
}

interface HealthReport {
  overall_score: number
  overall_status: 'ok' | 'warning' | 'critical' | 'n_a'
  dimensions: DimensionScore[]
  strengths: string[]
  critical_gaps: string[]
  recommendations: string[]
  total_chapters: number
}

const loading = ref(false)
const report = ref<HealthReport | null>(null)
const errorMsg = ref<string | null>(null)

onMounted(() => {
  analyze()
})

watch(() => props.projectId, () => {
  report.value = null
  errorMsg.value = null
  analyze()
})

async function analyze() {
  loading.value = true
  errorMsg.value = null
  try {
    const data = await api.getRaw<{ success: boolean; data: HealthReport; error?: string }>(
      `/api/projects/${props.projectId}/narrative-health`
    )
    if (data.success) {
      report.value = data.data
    } else {
      errorMsg.value = data.error || 'Error al evaluar la salud narrativa'
    }
  } catch (error) {
    console.error('Error checking narrative health:', error)
    errorMsg.value = error instanceof Error ? error.message : 'No se pudo evaluar la salud narrativa. Si persiste, reinicia la aplicación.'
  } finally {
    loading.value = false
  }
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ok: '#22c55e',
    warning: '#eab308',
    critical: '#ef4444',
    n_a: '#999',
  }
  return colors[status] || '#999'
}

function getStatusSeverity(status: string): 'success' | 'warn' | 'danger' | 'secondary' {
  const map: Record<string, 'success' | 'warn' | 'danger' | 'secondary'> = {
    ok: 'success',
    warning: 'warn',
    critical: 'danger',
    n_a: 'secondary',
  }
  return map[status] || 'secondary'
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: 'OK',
    warning: 'Aviso',
    critical: 'Crítico',
    n_a: 'N/A',
  }
  return labels[status] || status
}

function getScoreClass(score: number): string {
  if (score >= 65) return 'score-ok'
  if (score >= 35) return 'score-warning'
  return 'score-critical'
}

const okCount = computed(() =>
  report.value?.dimensions.filter(d => d.status === 'ok').length || 0
)
const warningCount = computed(() =>
  report.value?.dimensions.filter(d => d.status === 'warning').length || 0
)
const criticalCount = computed(() =>
  report.value?.dimensions.filter(d => d.status === 'critical').length || 0
)
</script>

<template>
  <div class="narrative-health-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-heart-fill"></i>
          Salud Narrativa
        </h3>
        <p class="subtitle">
          ¿Tiene el manuscrito los elementos narrativos esenciales?
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

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Evaluando salud narrativa...</p>
    </div>

    <!-- Error -->
    <AnalysisErrorState v-else-if="errorMsg" :message="errorMsg" :on-retry="analyze" />

    <!-- Empty -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-heart"></i>
      <p>Haz clic en "Analizar" para evaluar la salud narrativa del manuscrito.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Overall score -->
      <Card class="overall-card">
        <template #content>
          <div class="overall-content">
            <div class="overall-gauge">
              <div class="gauge-circle" :class="getScoreClass(report.overall_score)">
                <span class="gauge-value">{{ Math.round(report.overall_score) }}</span>
                <span class="gauge-label">/100</span>
              </div>
            </div>
            <div class="overall-info">
              <Tag
                :value="getStatusLabel(report.overall_status)"
                :severity="getStatusSeverity(report.overall_status)"
                class="overall-tag"
              />
              <div class="overall-counts">
                <span class="count-ok"><i class="pi pi-check-circle"></i> {{ okCount }} OK</span>
                <span class="count-warning"><i class="pi pi-exclamation-triangle"></i> {{ warningCount }} avisos</span>
                <span class="count-critical"><i class="pi pi-times-circle"></i> {{ criticalCount }} críticos</span>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Dimensions grid -->
      <div class="dimensions-grid">
        <div
          v-for="dim in report.dimensions"
          :key="dim.dimension"
          class="dimension-card"
          :class="'dim-' + dim.status"
        >
          <div class="dim-header">
            <i :class="'pi ' + dim.icon" :style="{ color: getStatusColor(dim.status) }" />
            <span class="dim-name">{{ dim.name }}</span>
            <span class="dim-score" :class="getScoreClass(dim.score)">{{ Math.round(dim.score) }}</span>
          </div>
          <p class="dim-explanation">{{ dim.explanation }}</p>
          <p v-if="dim.evidence" class="dim-evidence">{{ dim.evidence }}</p>
          <p v-if="dim.suggestion" class="dim-suggestion">
            <i class="pi pi-lightbulb"></i>
            {{ dim.suggestion }}
          </p>
        </div>
      </div>

      <!-- Critical gaps -->
      <Card v-if="report.critical_gaps.length" class="gaps-card">
        <template #title>
          <i class="pi pi-exclamation-circle"></i>
          Gaps críticos
        </template>
        <template #content>
          <ul class="gaps-list">
            <li v-for="(gap, i) in report.critical_gaps" :key="i">{{ gap }}</li>
          </ul>
        </template>
      </Card>

      <!-- Strengths -->
      <Card v-if="report.strengths.length" class="strengths-card">
        <template #title>
          <i class="pi pi-star"></i>
          Fortalezas
        </template>
        <template #content>
          <ul class="strengths-list">
            <li v-for="(s, i) in report.strengths" :key="i">{{ s }}</li>
          </ul>
        </template>
      </Card>

      <!-- Recommendations -->
      <Card v-if="report.recommendations.length" class="recommendations-card">
        <template #title>
          <i class="pi pi-lightbulb"></i>
          Recomendaciones
        </template>
        <template #content>
          <ul class="recommendations-list">
            <li v-for="(rec, i) in report.recommendations" :key="i">{{ rec }}</li>
          </ul>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.narrative-health-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4, 1rem);
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4, 1rem);
  flex-wrap: wrap;
}

.header-left h3 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin: 0 0 var(--ds-space-1, 0.25rem);
  font-size: 1.125rem;
}

.subtitle {
  margin: 0;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8, 2rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  gap: var(--ds-space-3, 0.75rem);
}

.empty-state i { font-size: 2rem; opacity: 0.5; }

/* Overall card */
.overall-card :deep(.p-card-body) {
  padding: var(--ds-space-4, 1rem);
}

.overall-content {
  display: flex;
  align-items: center;
  gap: var(--ds-space-5, 1.25rem);
}

.gauge-circle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 4px solid currentColor;
  flex-shrink: 0;
}

.gauge-value {
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1;
}

.gauge-label {
  font-size: 0.6875rem;
  opacity: 0.7;
}

.overall-info {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
}

.overall-tag {
  align-self: flex-start;
}

.overall-counts {
  display: flex;
  gap: var(--ds-space-3, 0.75rem);
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.count-ok { color: #22c55e; }
.count-warning { color: #eab308; }
.count-critical { color: #ef4444; }

.overall-counts i {
  margin-right: 2px;
}

/* Dimensions grid */
.dimensions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--ds-space-3, 0.75rem);
}

.dimension-card {
  padding: var(--ds-space-3, 0.75rem);
  border-radius: var(--ds-radius-md, 8px);
  background: var(--ds-surface-card, var(--surface-card));
  border: 1px solid var(--ds-surface-border, var(--surface-border));
  border-left: 3px solid var(--ds-surface-border);
}

.dim-ok { border-left-color: #22c55e; }
.dim-warning { border-left-color: #eab308; }
.dim-critical { border-left-color: #ef4444; }
.dim-n_a { border-left-color: #999; }

.dim-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin-bottom: var(--ds-space-2, 0.5rem);
}

.dim-header i {
  font-size: 1rem;
}

.dim-name {
  font-weight: 600;
  font-size: 0.875rem;
  flex: 1;
}

.dim-score {
  font-weight: 800;
  font-size: 1rem;
}

.dim-explanation {
  margin: 0 0 var(--ds-space-1, 0.25rem);
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.dim-evidence {
  margin: 0 0 var(--ds-space-1, 0.25rem);
  font-size: 0.75rem;
  color: var(--ds-color-text-tertiary, #999);
  font-style: italic;
}

.dim-suggestion {
  margin: 0;
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-1, 0.25rem);
}

.dim-suggestion i {
  color: #eab308;
  margin-top: 1px;
  flex-shrink: 0;
}

/* Score colors */
.score-ok { color: #22c55e; }
.score-warning { color: #eab308; }
.score-critical { color: #ef4444; }

/* Cards */
.gaps-card :deep(.p-card-title),
.strengths-card :deep(.p-card-title),
.recommendations-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
}

.gaps-list,
.strengths-list,
.recommendations-list {
  margin: 0;
  padding-left: var(--ds-space-5, 1.25rem);
}

.gaps-list li,
.strengths-list li,
.recommendations-list li {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.6;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.gaps-list li { color: #ef4444; }
.strengths-list li { color: #22c55e; }

@media (max-width: 768px) {
  .dimensions-grid {
    grid-template-columns: 1fr;
  }

  .overall-content {
    flex-direction: column;
    text-align: center;
  }
}
</style>
