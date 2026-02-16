<template>
  <div class="register-analysis">
    <!-- Header -->
    <div class="analysis-header">
      <div class="header-left">
        <h3>Análisis de Registro Narrativo</h3>
        <Tag v-if="summary" severity="info" size="small">
          {{ totalSegments }} segmentos analizados
        </Tag>
      </div>
      <div class="header-actions">
        <Select
          v-model="selectedSeverity"
          :options="severityOptions"
          option-label="label"
          option-value="value"
          placeholder="Severidad mínima"
          class="severity-selector"
          size="small"
        />
        <Button
          label="Analizar"
          icon="pi pi-play"
          :loading="loading"
          size="small"
          @click="loadAnalysis"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 40px; height: 40px" />
      <p>Analizando registro narrativo...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <Button label="Reintentar" size="small" @click="loadAnalysis" />
    </div>

    <!-- Content -->
    <div v-else-if="analysis" class="analysis-content">
      <!-- Summary Cards -->
      <div v-if="summary" class="summary-section">
        <div class="summary-cards">
          <Card class="summary-card">
            <template #content>
              <div class="stat-content">
                <i class="pi pi-chart-pie stat-icon"></i>
                <div class="stat-info">
                  <span class="stat-value">{{ summary.dominantRegister || 'N/A' }}</span>
                  <span class="stat-label">Registro dominante</span>
                </div>
              </div>
            </template>
          </Card>
          <Card class="summary-card">
            <template #content>
              <div class="stat-content">
                <i class="pi pi-sync stat-icon warning"></i>
                <div class="stat-info">
                  <span class="stat-value">{{ changes.length }}</span>
                  <span class="stat-label">Cambios de registro</span>
                </div>
              </div>
            </template>
          </Card>
          <Card class="summary-card">
            <template #content>
              <div class="stat-content">
                <i class="pi pi-percentage stat-icon success"></i>
                <div class="stat-info">
                  <span class="stat-value">{{ formatPercent(summary.consistency || 0) }}</span>
                  <span class="stat-label">Consistencia</span>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>

      <!-- Chapter Timeline Overview -->
      <div v-if="timelineChapters.length > 0" class="timeline-section">
        <h4><i class="pi pi-map"></i> Vista por Capítulos</h4>
        <ChapterTimeline
          :chapters="timelineChapters"
          :highlights="timelineHighlights"
          :selected-chapter="selectedChapter"
          :show-legend="true"
          :legend="timelineLegend"
          @select="onChapterSelect"
        />
      </div>

      <!-- Register Distribution -->
      <div class="distribution-section">
        <div class="distribution-header-row">
          <h4><i class="pi pi-chart-bar"></i> Distribución de Registros</h4>
          <SelectButton 
            v-model="chartType" 
            :options="chartTypeOptions" 
            option-value="value"
            :allow-empty="false"
            class="chart-type-toggle"
          >
            <template #option="slotProps">
              <i :class="slotProps.option.icon"></i>
            </template>
          </SelectButton>
        </div>
        
        <!-- Bars view -->
        <div v-if="chartType === 'bars'" class="distribution-bars">
          <div
            v-for="(value, register) in registerDistribution"
            :key="register"
            class="distribution-item"
          >
            <div class="distribution-header">
              <span class="register-name">{{ getRegisterLabel(String(register)) }}</span>
              <span class="register-percent">{{ formatPercent(value) }}</span>
            </div>
            <ProgressBar
              :value="value * 100"
              :show-value="false"
              :class="getRegisterClass(String(register))"
            />
          </div>
        </div>
        
        <!-- Pie chart view -->
        <div v-else class="distribution-pie">
          <Chart 
            type="pie" 
            :data="pieChartData" 
            :options="pieChartOptions"
            class="pie-chart"
          />
        </div>
      </div>

      <!-- Register Changes -->
      <div class="changes-section">
        <h4>
          <i class="pi pi-exclamation-triangle"></i>
          Cambios de Registro ({{ changes.length }})
        </h4>
        <p class="changes-description">
          Los cambios abruptos de registro pueden indicar inconsistencias en el tono narrativo.
          <span class="tooltip-text">
            <i class="pi pi-info-circle"></i>
            <strong>Nota:</strong> Es normal que el registro cambie entre narración y diálogo.
            Los personajes suelen hablar en registro coloquial mientras que la narración
            mantiene un tono neutro o literario. Revisa solo cambios inesperados dentro
            del mismo tipo de texto.
          </span>
        </p>

        <div v-if="changes.length > 0" class="changes-list">
          <div
            v-for="(change, idx) in changes"
            :key="idx"
            class="change-item"
            :class="`severity-${change.severity}`"
          >
            <div class="change-header">
              <Tag :severity="getSeveritySeverity(change.severity)" size="small">
                {{ getSeverityLabel(change.severity) }}
              </Tag>
              <span v-if="change.chapter" class="change-chapter">
                Capítulo {{ change.chapter }}
              </span>
            </div>
            <div class="change-flow">
              <Tag :severity="getRegisterSeverity(change.fromRegister)">
                {{ getRegisterLabel(change.fromRegister) }}
              </Tag>
              <i class="pi pi-arrow-right"></i>
              <Tag :severity="getRegisterSeverity(change.toRegister)">
                {{ getRegisterLabel(change.toRegister) }}
              </Tag>
            </div>
            <p class="change-explanation">{{ change.explanation }}</p>
            <div class="change-actions">
              <small class="change-location-text">
                <i class="pi pi-map-marker"></i>
                Capítulo {{ change.chapter }}
              </small>
              <Button
                v-if="change.chapter"
                icon="pi pi-arrow-right"
                label="Ir al texto"
                size="small"
                text
                severity="info"
                @click="navigateToChange(change)"
              />
            </div>
          </div>
        </div>
        <Message v-else severity="success" :closable="false" class="no-changes-message">
          <i class="pi pi-check-circle"></i>
          No se detectaron cambios abruptos de registro con la severidad seleccionada.
        </Message>
      </div>

      <!-- Per-Chapter Overview Grid -->
      <div v-if="perChapter.length > 0" class="chapter-overview-section">
        <h4><i class="pi pi-th-large"></i> Registro por Capítulo</h4>
        <div class="chapter-overview-grid">
          <div
            v-for="ch in perChapter"
            :key="ch.chapter_number"
            class="chapter-overview-card"
            :class="{
              'low-consistency': ch.consistency_pct < 60,
              'has-changes': ch.change_count > 0,
            }"
            @click="onChapterSelect(ch.chapter_number)"
          >
            <div class="overview-header">
              <span class="overview-chapter-num">{{ ch.chapter_number }}</span>
              <Tag
                :severity="getRegisterSeverity(ch.dominant_register)"
                size="small"
              >
                {{ getRegisterLabel(ch.dominant_register) }}
              </Tag>
            </div>
            <div class="overview-stats">
              <span class="overview-consistency" :class="getConsistencyClass(ch.consistency_pct)">
                {{ ch.consistency_pct }}%
              </span>
              <span class="overview-segments">{{ ch.segment_count }} seg.</span>
            </div>
            <div v-if="ch.change_count > 0" class="overview-changes">
              <i class="pi pi-exclamation-triangle"></i>
              {{ ch.change_count }} cambio{{ ch.change_count !== 1 ? 's' : '' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Analysis by Chapter -->
      <div v-if="analysesByChapter.length > 0" class="chapters-section">
        <h4><i class="pi pi-book"></i> Detalle por Capítulo</h4>
        <Accordion :multiple="true">
          <AccordionPanel
            v-for="chapter in analysesByChapter"
            :key="chapter.chapterNum"
            :value="`chapter-${chapter.chapterNum}`"
          >
            <AccordionHeader>
              <div class="chapter-header">
                <span>Capítulo {{ chapter.chapterNum }}</span>
                <div class="chapter-tags">
                  <Tag severity="info" size="small">{{ chapter.segments.length }} segmentos</Tag>
                  <Tag
                    :severity="getRegisterSeverity(chapter.dominantRegister)"
                    size="small"
                  >
                    {{ getRegisterLabel(chapter.dominantRegister) }}
                  </Tag>
                  <Tag
                    v-if="getChapterConsistency(chapter.chapterNum) !== null"
                    :severity="(getChapterConsistency(chapter.chapterNum) ?? 100) < 60 ? 'warning' : 'success'"
                    size="small"
                  >
                    {{ getChapterConsistency(chapter.chapterNum) }}%
                  </Tag>
                </div>
              </div>
            </AccordionHeader>
            <AccordionContent>
              <div class="chapter-content">
                <div class="segment-list">
                  <div
                    v-for="segment in chapter.segments.slice(0, 20)"
                    :key="segment.segmentIndex"
                    class="segment-item"
                  >
                    <div class="segment-info">
                      <span class="segment-index">#{{ segment.segmentIndex }}</span>
                      <Tag
                        :severity="getRegisterSeverity(segment.primaryRegister)"
                        size="small"
                      >
                        {{ getRegisterLabel(segment.primaryRegister) }}
                      </Tag>
                      <Tag
                        v-if="segment.isDialogue"
                        severity="secondary"
                        size="small"
                      >
                        Diálogo
                      </Tag>
                    </div>
                    <div class="segment-confidence">
                      {{ formatPercent(segment.confidence) }} confianza
                    </div>
                  </div>
                  <p v-if="chapter.segments.length > 20" class="more-segments">
                    ... y {{ chapter.segments.length - 20 }} segmentos más
                  </p>
                </div>
              </div>
            </AccordionContent>
          </AccordionPanel>
        </Accordion>
      </div>
    </div>

    <!-- No Analysis Yet -->
    <div v-else class="no-analysis">
      <i class="pi pi-sliders-v empty-icon"></i>
      <p>Haz clic en "Analizar" para detectar los registros narrativos del manuscrito.</p>
      <small>El análisis identificará segmentos formales, neutros, coloquiales y detectará cambios abruptos.</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Card from 'primevue/card'
import Select from 'primevue/select'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Chart from 'primevue/chart'
import SelectButton from 'primevue/selectbutton'
import { ChapterTimeline } from '@/components/shared'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import { useWorkspaceStore } from '@/stores/workspace'
import type { RegisterAnalysis, RegisterChange, RegisterSummary } from '@/types'

const props = defineProps<{
  projectId: number
}>()

const store = useVoiceAndStyleStore()
const workspaceStore = useWorkspaceStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const selectedSeverity = ref('medium')
const chartType = ref<'bars' | 'pie'>('bars')

const chartTypeOptions = [
  { icon: 'pi pi-chart-bar', value: 'bars' },
  { icon: 'pi pi-chart-pie', value: 'pie' }
]

const severityOptions = [
  { label: 'Baja+', value: 'low' },
  { label: 'Media+', value: 'medium' },
  { label: 'Alta+', value: 'high' },
  { label: 'Crítica', value: 'critical' }
]

// Get analysis from store
const analysis = computed(() => {
  return store.getRegisterAnalysis(props.projectId)
})

const analyses = computed<RegisterAnalysis[]>(() => {
  return analysis.value?.analyses || []
})

const changes = computed<RegisterChange[]>(() => {
  return analysis.value?.changes || []
})

const summary = computed<RegisterSummary | null>(() => {
  return analysis.value?.summary || null
})

const totalSegments = computed(() => analyses.value.length)

// Per-chapter summaries from backend
const perChapter = computed(() => {
  return analysis.value?.perChapter || []
})

// Get consistency for a specific chapter
function getChapterConsistency(chapterNum: number): number | null {
  const ch = perChapter.value.find(c => c.chapter_number === chapterNum)
  return ch ? ch.consistency_pct : null
}

function getConsistencyClass(pct: number): string {
  if (pct >= 80) return 'consistency-high'
  if (pct >= 60) return 'consistency-medium'
  return 'consistency-low'
}

// Calculate register distribution (prefer summary from API, fallback to analyses)
const registerDistribution = computed(() => {
  // Prefer distribution_pct (percentages) from API, then raw counts
  const distPct = (summary.value as any)?.distribution_pct
  if (distPct && Object.keys(distPct).length > 0) {
    const distribution: Record<string, number> = {}
    for (const [reg, pct] of Object.entries(distPct)) {
      distribution[reg] = (pct as number) / 100
    }
    return distribution
  }
  // Raw counts: convert to fractions
  const distRaw = summary.value?.distribution
  if (distRaw && Object.keys(distRaw).length > 0) {
    const vals = Object.values(distRaw) as number[]
    const total = vals.reduce((s, v) => s + v, 0) || 1
    const distribution: Record<string, number> = {}
    for (const [reg, count] of Object.entries(distRaw) as [string, number][]) {
      distribution[reg] = count / total
    }
    return distribution
  }

  // Fallback: compute from individual analyses
  if (analyses.value.length === 0) return {}

  const counts: Record<string, number> = {}
  for (const a of analyses.value) {
    counts[a.primaryRegister] = (counts[a.primaryRegister] || 0) + 1
  }

  const total = analyses.value.length
  const distribution: Record<string, number> = {}
  for (const [reg, count] of Object.entries(counts)) {
    distribution[reg] = count / total
  }

  return distribution
})

// Pie chart data for register distribution
const pieChartData = computed(() => {
  const dist = registerDistribution.value
  const labels = Object.keys(dist).map(r => getRegisterLabel(r))
  const data = Object.values(dist).map(v => Math.round(v * 100))
  const colors = Object.keys(dist).map(r => getRegisterColor(r))
  
  return {
    labels,
    datasets: [{
      data,
      backgroundColor: colors,
      hoverBackgroundColor: colors.map(c => c + 'CC')
    }]
  }
})

const pieChartOptions = {
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        usePointStyle: true,
        padding: 15
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx: { label: string; raw: number }) => `${ctx.label}: ${ctx.raw}%`
      }
    }
  },
  responsive: true,
  maintainAspectRatio: false
}

// Get color for register type
function getRegisterColor(register: string): string {
  const colors: Record<string, string> = {
    formal: '#6366f1',         // Indigo
    formal_literary: '#6366f1', // Indigo (same as formal)
    neutral: '#8b5cf6',        // Violet
    colloquial: '#f59e0b',     // Amber
    literary: '#10b981',       // Emerald
    technical: '#3b82f6',      // Blue
    poetic: '#ec4899',         // Pink
  }
  return colors[register.toLowerCase()] || '#64748b'
}

// Build chapters for timeline
const timelineChapters = computed(() => {
  return analysesByChapter.value.map(ch => ({
    id: ch.chapterNum,
    number: ch.chapterNum,
    title: `Capítulo ${ch.chapterNum}`
  }))
})

// Build highlights based on register changes per chapter
const timelineHighlights = computed(() => {
  const changesByChapter: Record<number, { count: number; maxSeverity: string }> = {}

  for (const change of changes.value) {
    if (change.chapter) {
      if (!changesByChapter[change.chapter]) {
        changesByChapter[change.chapter] = { count: 0, maxSeverity: 'low' }
      }
      changesByChapter[change.chapter].count++
      // Track highest severity
      const severityOrder = ['low', 'medium', 'high', 'critical']
      const current = severityOrder.indexOf(changesByChapter[change.chapter].maxSeverity)
      const incoming = severityOrder.indexOf(change.severity)
      if (incoming > current) {
        changesByChapter[change.chapter].maxSeverity = change.severity
      }
    }
  }

  const highlights = []
  for (const [chapter, data] of Object.entries(changesByChapter)) {
    const severityColors: Record<string, string> = {
      critical: '#ef4444',  // red
      high: '#f97316',      // orange
      medium: '#eab308',    // yellow
      low: '#6b7280'        // gray
    }
    highlights.push({
      chapter: parseInt(chapter),
      color: severityColors[data.maxSeverity] || '#6b7280',
      intensity: Math.min(1, 0.3 + data.count * 0.2),
      label: `${data.count} cambio${data.count !== 1 ? 's' : ''} (${getSeverityLabel(data.maxSeverity)})`
    })
  }

  return highlights
})

const timelineLegend = [
  { label: 'Crítico', color: '#ef4444' },
  { label: 'Alto', color: '#f97316' },
  { label: 'Medio', color: '#eab308' },
  { label: 'Bajo', color: '#6b7280' }
]

// Selected chapter for navigation
const selectedChapter = ref<number | undefined>(undefined)

const onChapterSelect = (chapterNumber: number) => {
  selectedChapter.value = chapterNumber
  // Scroll to chapter section in accordion (if visible)
  const accordionEl = document.querySelector(`[data-p-index="${chapterNumber - 1}"]`)
  if (accordionEl) {
    accordionEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// Group analyses by chapter
const analysesByChapter = computed(() => {
  if (analyses.value.length === 0) return []

  const byChapter: Record<number, RegisterAnalysis[]> = {}
  for (const a of analyses.value) {
    if (!byChapter[a.chapter]) byChapter[a.chapter] = []
    byChapter[a.chapter].push(a)
  }

  return Object.entries(byChapter).map(([chapterNum, segments]) => {
    // Find dominant register for chapter
    const counts: Record<string, number> = {}
    for (const seg of segments) {
      counts[seg.primaryRegister] = (counts[seg.primaryRegister] || 0) + 1
    }
    const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'neutral'

    return {
      chapterNum: parseInt(chapterNum),
      segments,
      dominantRegister: dominant
    }
  }).sort((a, b) => a.chapterNum - b.chapterNum)
})

// Navigate to a register change in the text
function navigateToChange(change: RegisterChange) {
  const searchText = change.contextAfter?.trim().split(/\s+/).slice(0, 6).join(' ') || undefined
  workspaceStore.navigateToTextPosition(change.position, searchText)
}

// Load analysis
const loadAnalysis = async () => {
  loading.value = true
  error.value = null

  try {
    const success = await store.fetchRegisterAnalysis(props.projectId, selectedSeverity.value)
    if (!success) {
      error.value = store.error || 'Error al cargar el análisis de registro'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
  } finally {
    loading.value = false
  }
}

// Helpers
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`
}

const getRegisterLabel = (register: string): string => {
  const labels: Record<string, string> = {
    formal: 'Formal',
    formal_literary: 'Formal / Literario',
    neutral: 'Neutro',
    colloquial: 'Coloquial',
    technical: 'Técnico',
    literary: 'Literario',
    poetic: 'Poético',
  }
  return labels[register] || register
}

const getRegisterSeverity = (register: string): string => {
  const severities: Record<string, string> = {
    formal: 'info',
    formal_literary: 'info',
    neutral: 'secondary',
    colloquial: 'warning',
    technical: 'contrast',
    literary: 'success',
    poetic: 'help',
  }
  return severities[register] || 'secondary'
}

const getRegisterClass = (register: string): string => {
  return `register-${register}`
}

const getSeveritySeverity = (severity: string): string => {
  const severities: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'secondary'
  }
  return severities[severity] || 'secondary'
}

const getSeverityLabel = (severity: string): string => {
  const labels: Record<string, string> = {
    critical: 'Crítico',
    high: 'Alto',
    medium: 'Medio',
    low: 'Bajo'
  }
  return labels[severity] || severity
}

// Auto-load on mount
onMounted(() => {
  if (props.projectId && !analysis.value) {
    loadAnalysis()
  }
})

// Watch for project changes
watch(() => props.projectId, (newId) => {
  if (newId && !store.registerAnalyses[newId]) {
    loadAnalysis()
  }
})
</script>

<style scoped>
.register-analysis {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-left h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.severity-selector {
  width: 130px;
}

/* Loading and Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.error-state {
  color: var(--red-500);
}

.error-state i {
  font-size: 2.5rem;
}

.no-analysis {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.4;
  margin-bottom: 1rem;
}

.no-analysis small {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

/* Content */
.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Summary Section */
.summary-section {
  margin-bottom: 0.5rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.summary-card {
  background: var(--surface-card);
}

.summary-card :deep(.p-card-body) {
  padding: 1rem;
}

.summary-card :deep(.p-card-content) {
  padding: 0;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.stat-icon.warning {
  color: var(--orange-500);
}

.stat-icon.success {
  color: var(--green-500);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

/* Distribution Section */
.distribution-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.distribution-header-row h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.chart-type-toggle {
  scale: 0.85;
}

.chart-type-toggle :deep(.p-button) {
  padding: 0.5rem 0.75rem;
}

.distribution-pie {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 250px;
}

.pie-chart {
  width: 100%;
  max-width: 400px;
  height: 250px;
}

.distribution-section h4,
.changes-section h4,
.chapters-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.distribution-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.distribution-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.register-name {
  font-weight: 500;
  color: var(--text-color);
}

.register-percent {
  color: var(--text-color-secondary);
}

/* Progress bar colors - PrimeVue 4 compatible */
/* The p-progressbar component uses p-progressbar-value internally */
.register-formal :deep(.p-progressbar-value),
.register-formal:deep(.p-progressbar-value),
.register-formal_literary :deep(.p-progressbar-value),
.register-formal_literary:deep(.p-progressbar-value) {
  background: #6366f1 !important; /* Indigo - Formal */
}

.register-neutral :deep(.p-progressbar-value),
.register-neutral:deep(.p-progressbar-value) {
  background: #8b5cf6 !important; /* Violet - Neutro (más visible que gris) */
}

.register-colloquial :deep(.p-progressbar-value),
.register-colloquial:deep(.p-progressbar-value) {
  background: #f59e0b !important; /* Amber - Coloquial */
}

.register-technical :deep(.p-progressbar-value),
.register-technical:deep(.p-progressbar-value) {
  background: #3b82f6 !important; /* Blue - Técnico */
}

.register-literary :deep(.p-progressbar-value),
.register-literary:deep(.p-progressbar-value) {
  background: #10b981 !important; /* Emerald - Literario */
}

.register-poetic :deep(.p-progressbar-value),
.register-poetic:deep(.p-progressbar-value) {
  background: #ec4899 !important; /* Pink - Poético */
}

/* Ensure progress bar has visible background track */
.distribution-item :deep(.p-progressbar) {
  background: var(--surface-200, #e5e7eb);
  height: 8px;
  border-radius: var(--app-radius);
}

.distribution-item :deep(.p-progressbar-value) {
  border-radius: var(--app-radius);
}

/* Changes Section */
.changes-description {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.changes-description .tooltip-text {
  display: block;
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: var(--app-radius);
  border-left: 3px solid var(--primary-color);
  font-size: 0.8rem;
  line-height: 1.5;
}

.changes-description .tooltip-text i {
  margin-right: 0.25rem;
  color: var(--primary-color);
}

.changes-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.change-item {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: var(--app-radius);
  border-left: 4px solid var(--primary-color);
}

.change-item.severity-critical {
  border-color: var(--red-500);
  background: var(--red-50);
}

.change-item.severity-high {
  border-color: var(--orange-500);
  background: var(--orange-50);
}

.change-item.severity-medium {
  border-color: var(--yellow-500);
}

.change-item.severity-low {
  border-color: var(--gray-400);
}

.change-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.change-chapter {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.change-flow {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.change-flow i {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.change-explanation {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-color);
}

.change-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.change-location-text {
  color: var(--text-color-secondary);
}

.change-location-text i {
  font-size: 0.75rem;
  margin-right: 0.25rem;
}

.no-changes-message {
  margin: 0;
}

.no-changes-message i {
  margin-right: 0.5rem;
}

/* Chapter Overview Grid */
.chapter-overview-section {
  margin-top: 0.5rem;
}

.chapter-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
}

.chapter-overview-card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.625rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-200);
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.chapter-overview-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-color: var(--primary-color);
}

.chapter-overview-card.low-consistency {
  border-color: var(--orange-300);
}

.chapter-overview-card.has-changes {
  border-left: 3px solid var(--orange-500);
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.375rem;
}

.overview-chapter-num {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--text-color);
}

.overview-stats {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.overview-consistency {
  font-size: 1rem;
  font-weight: 700;
}

.overview-consistency.consistency-high {
  color: var(--green-600);
}

.overview-consistency.consistency-medium {
  color: var(--yellow-600);
}

.overview-consistency.consistency-low {
  color: var(--red-500);
}

.overview-segments {
  font-size: 0.6875rem;
  color: var(--text-color-secondary);
}

.overview-changes {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.6875rem;
  color: var(--orange-600);
}

.overview-changes i {
  font-size: 0.625rem;
}

/* Chapters Section */
.chapters-section {
  margin-top: 0.5rem;
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 1rem;
}

.chapter-tags {
  display: flex;
  gap: 0.5rem;
}

.chapter-content {
  padding: 0.5rem 0;
}

.segment-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.segment-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-radius: var(--app-radius);
}

.segment-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.segment-index {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.segment-confidence {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.more-segments {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

/* Timeline Section */
.timeline-section {
  padding: 1rem;
  background: var(--surface-card);
  border-radius: var(--app-radius);
  border: 1px solid var(--surface-200);
}

.timeline-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}
</style>
