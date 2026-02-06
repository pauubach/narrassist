<script setup lang="ts">
/**
 * SentenceEnergyTab - Análisis de energía de oraciones
 *
 * Muestra métricas de energía: voz activa/pasiva, fuerza de verbos,
 * estructura, y nominalizaciones. Destaca oraciones de baja energía.
 */

import { ref, onMounted, computed, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Message from 'primevue/message'
import { api } from '@/services/apiClient'
import AnalysisErrorState from '@/components/shared/AnalysisErrorState.vue'

const props = defineProps<{
  projectId: number
}>()

interface EnergyIssue {
  type: string
  detail: string
  suggestion: string
  penalty: number
}

interface LowEnergySentence {
  text: string
  energy_score: number
  energy_level: string
  voice_score: number
  verb_strength: number
  structure_score: number
  issues: EnergyIssue[]
  is_passive: boolean
  has_weak_verb: boolean
  has_nominalization: boolean
  word_count: number
}

interface ChapterEnergy {
  chapter_number: number
  chapter_title: string
  total_sentences: number
  avg_energy: number
  avg_voice_score: number
  avg_verb_strength: number
  avg_structure_score: number
  by_level: Record<string, number>
  issues: {
    passive_count: number
    weak_verb_count: number
    nominalization_count: number
  }
  low_energy_sentences: LowEnergySentence[]
  low_energy_count: number
  recommendations: string[]
}

interface EnergyReport {
  global_stats: {
    total_sentences: number
    analyzed_sentences: number
    avg_energy: number
    low_energy_count: number
    passive_count: number
    weak_verb_count: number
    nominalization_count: number
    by_level: Record<string, number>
  }
  chapters: ChapterEnergy[]
  recommendations: string[]
  threshold_used: number
}

const loading = ref(false)
const report = ref<EnergyReport | null>(null)
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
    const data = await api.getRaw<{ success: boolean; data: EnergyReport; error?: string }>(
      `/api/projects/${props.projectId}/sentence-energy`
    )
    if (data.success) {
      report.value = data.data
    } else {
      errorMsg.value = data.error || 'Error al analizar energía de oraciones'
    }
  } catch (error) {
    console.error('Error analyzing sentence energy:', error)
    errorMsg.value = error instanceof Error ? error.message : 'Error de conexión'
  } finally {
    loading.value = false
  }
}

function getEnergyClass(score: number): string {
  if (score >= 80) return 'energy-very-high'
  if (score >= 60) return 'energy-high'
  if (score >= 40) return 'energy-medium'
  if (score >= 20) return 'energy-low'
  return 'energy-very-low'
}

function getEnergySeverity(score: number): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  if (score >= 70) return 'success'
  if (score >= 50) return 'info'
  if (score >= 35) return 'warn'
  return 'danger'
}

function getEnergyLabel(level: string): string {
  const labels: Record<string, string> = {
    very_high: 'Muy alta',
    high: 'Alta',
    medium: 'Media',
    low: 'Baja',
    very_low: 'Muy baja',
  }
  return labels[level] || level
}

function getLevelColor(level: string): string {
  const colors: Record<string, string> = {
    very_high: '#22c55e',
    high: '#84cc16',
    medium: '#eab308',
    low: '#f97316',
    very_low: '#ef4444',
  }
  return colors[level] || '#999'
}

function getIssueTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    passive_voice: 'Voz pasiva',
    weak_verb: 'Verbo débil',
    nominalization: 'Nominalización',
    excessive_length: 'Longitud excesiva',
  }
  return labels[type] || type
}

function getIssueTypeSeverity(type: string): 'warn' | 'danger' | 'info' | 'secondary' {
  const map: Record<string, 'warn' | 'danger' | 'info' | 'secondary'> = {
    passive_voice: 'danger',
    weak_verb: 'warn',
    nominalization: 'info',
    excessive_length: 'secondary',
  }
  return map[type] || 'info'
}

const totalLowEnergy = computed(() => {
  if (!report.value) return 0
  return report.value.global_stats.low_energy_count
})

const levelOrder = ['very_high', 'high', 'medium', 'low', 'very_low']

const sortedLevels = computed(() => {
  if (!report.value) return []
  const by = report.value.global_stats.by_level
  return levelOrder
    .filter(l => (by[l] || 0) > 0)
    .map(l => ({
      level: l,
      count: by[l] || 0,
      label: getEnergyLabel(l),
      color: getLevelColor(l),
    }))
})

const totalAnalyzed = computed(() => {
  if (!report.value) return 0
  return report.value.global_stats.analyzed_sentences
})
</script>

<template>
  <div class="sentence-energy-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-bolt"></i>
          Energía de Oraciones
        </h3>
        <p class="subtitle">
          Evalúa el dinamismo del texto: voz activa/pasiva, fuerza de verbos y estructura.
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

    <!-- Calibration banner -->
    <Message severity="info" :closable="true" class="calibration-banner">
      Las métricas de energía están calibradas para prosa narrativa en español.
      Estilos deliberadamente contemplativos o líricos pueden mostrar puntuaciones más bajas sin que esto indique un problema.
    </Message>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Analizando energía de oraciones...</p>
    </div>

    <!-- Error -->
    <AnalysisErrorState v-else-if="errorMsg" :message="errorMsg" :on-retry="analyze" />

    <!-- Empty -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-bolt"></i>
      <p>Haz clic en "Analizar" para evaluar la energía de las oraciones.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats Row -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="getEnergyClass(report.global_stats.avg_energy)">
                {{ report.global_stats.avg_energy }}
              </div>
              <div class="stat-label">Energía media</div>
              <div class="stat-sublabel">/100</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value energy-low">{{ totalLowEnergy }}</div>
              <div class="stat-label">Baja energía</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.passive_count }}</div>
              <div class="stat-label">Voz pasiva</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.weak_verb_count }}</div>
              <div class="stat-label">Verbos débiles</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.nominalization_count }}</div>
              <div class="stat-label">Nominalizaciones</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Energy Distribution -->
      <Card v-if="sortedLevels.length" class="distribution-card">
        <template #title>
          <i class="pi pi-chart-bar"></i>
          Distribución de energía
        </template>
        <template #content>
          <div class="energy-distribution">
            <div
              v-for="item in sortedLevels"
              :key="item.level"
              class="distribution-row"
            >
              <span class="dist-label">{{ item.label }}</span>
              <div class="dist-bar-container">
                <div
                  class="dist-bar"
                  :style="{
                    width: totalAnalyzed > 0
                      ? (item.count / totalAnalyzed * 100) + '%'
                      : '0%',
                    backgroundColor: item.color,
                  }"
                />
              </div>
              <span class="dist-count">{{ item.count }}</span>
              <span class="dist-pct">
                {{ totalAnalyzed > 0 ? Math.round(item.count / totalAnalyzed * 100) : 0 }}%
              </span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Global Recommendations -->
      <Card v-if="report.recommendations.length" class="recommendations-card">
        <template #title>
          <i class="pi pi-lightbulb"></i>
          Recomendaciones
        </template>
        <template #content>
          <ul class="recommendations-list">
            <li v-for="(rec, i) in report.recommendations" :key="i">
              {{ rec }}
            </li>
          </ul>
        </template>
      </Card>

      <!-- Chapters -->
      <Accordion v-if="report.chapters.length > 1" :multiple="true">
        <AccordionPanel
          v-for="ch in report.chapters"
          :key="ch.chapter_number"
          :value="String(ch.chapter_number)"
        >
          <AccordionHeader>
            <div class="chapter-header">
              <span class="chapter-title">{{ ch.chapter_title }}</span>
              <div class="chapter-badges">
                <Tag
                  :value="'Energía: ' + ch.avg_energy"
                  :severity="getEnergySeverity(ch.avg_energy)"
                />
                <Tag
                  v-if="ch.low_energy_count > 0"
                  :value="ch.low_energy_count + ' baja energía'"
                  severity="warn"
                />
                <Tag
                  v-if="ch.issues.passive_count > 0"
                  :value="ch.issues.passive_count + ' pasivas'"
                  severity="danger"
                />
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="chapter-detail">
              <!-- Chapter sub-scores -->
              <div class="chapter-subscores">
                <div class="subscore">
                  <span class="subscore-label">Voz</span>
                  <span class="subscore-value" :class="getEnergyClass(ch.avg_voice_score)">
                    {{ ch.avg_voice_score }}
                  </span>
                </div>
                <div class="subscore">
                  <span class="subscore-label">Verbos</span>
                  <span class="subscore-value" :class="getEnergyClass(ch.avg_verb_strength)">
                    {{ ch.avg_verb_strength }}
                  </span>
                </div>
                <div class="subscore">
                  <span class="subscore-label">Estructura</span>
                  <span class="subscore-value" :class="getEnergyClass(ch.avg_structure_score)">
                    {{ ch.avg_structure_score }}
                  </span>
                </div>
              </div>

              <!-- Chapter recommendations -->
              <ul v-if="ch.recommendations.length" class="recommendations-list chapter-recs">
                <li v-for="(rec, i) in ch.recommendations" :key="i">{{ rec }}</li>
              </ul>

              <!-- Low energy sentences -->
              <div v-if="ch.low_energy_sentences.length" class="low-energy-list">
                <h4>Oraciones de baja energía</h4>
                <div
                  v-for="(sent, idx) in ch.low_energy_sentences"
                  :key="idx"
                  class="low-energy-item"
                >
                  <div class="sent-header">
                    <Tag
                      :value="getEnergyLabel(sent.energy_level)"
                      :severity="getEnergySeverity(sent.energy_score)"
                      class="energy-tag"
                    />
                    <span class="sent-score">{{ sent.energy_score }}/100</span>
                    <div class="sent-flags">
                      <Tag v-if="sent.is_passive" value="Pasiva" severity="danger" />
                      <Tag v-if="sent.has_weak_verb" value="V. débil" severity="warn" />
                      <Tag v-if="sent.has_nominalization" value="Nomin." severity="info" />
                    </div>
                  </div>
                  <p class="sent-text">"{{ sent.text }}"</p>
                  <div v-if="sent.issues.length" class="sent-issues">
                    <div
                      v-for="(issue, ii) in sent.issues"
                      :key="ii"
                      class="issue-item"
                    >
                      <Tag
                        :value="getIssueTypeLabel(issue.type)"
                        :severity="getIssueTypeSeverity(issue.type)"
                        class="issue-tag"
                      />
                      <span class="issue-suggestion">{{ issue.suggestion }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <p v-else class="no-issues">
                <i class="pi pi-check-circle"></i>
                Sin oraciones de baja energía en este capítulo.
              </p>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

      <!-- Single chapter (no accordion) -->
      <div v-else-if="report.chapters.length === 1" class="single-chapter">
        <div
          v-for="(sent, idx) in report.chapters[0].low_energy_sentences"
          :key="idx"
          class="low-energy-item"
        >
          <div class="sent-header">
            <Tag
              :value="getEnergyLabel(sent.energy_level)"
              :severity="getEnergySeverity(sent.energy_score)"
              class="energy-tag"
            />
            <span class="sent-score">{{ sent.energy_score }}/100</span>
            <div class="sent-flags">
              <Tag v-if="sent.is_passive" value="Pasiva" severity="danger" />
              <Tag v-if="sent.has_weak_verb" value="V. débil" severity="warn" />
              <Tag v-if="sent.has_nominalization" value="Nomin." severity="info" />
            </div>
          </div>
          <p class="sent-text">"{{ sent.text }}"</p>
          <div v-if="sent.issues.length" class="sent-issues">
            <div
              v-for="(issue, ii) in sent.issues"
              :key="ii"
              class="issue-item"
            >
              <Tag
                :value="getIssueTypeLabel(issue.type)"
                :severity="getIssueTypeSeverity(issue.type)"
                class="issue-tag"
              />
              <span class="issue-suggestion">{{ issue.suggestion }}</span>
            </div>
          </div>
        </div>

        <!-- Single chapter recommendations -->
        <ul v-if="report.chapters[0].recommendations.length" class="recommendations-list">
          <li v-for="(rec, i) in report.chapters[0].recommendations" :key="i">{{ rec }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sentence-energy-tab {
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

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3, 0.75rem);
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

.empty-state i {
  font-size: 2rem;
  opacity: 0.5;
}

/* Stats cards */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: var(--ds-space-3, 0.75rem);
}

.stat-card :deep(.p-card-body) {
  padding: var(--ds-space-3, 0.75rem);
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  margin-top: var(--ds-space-1, 0.25rem);
}

.stat-sublabel {
  font-size: 0.75rem;
  color: var(--ds-color-text-tertiary, #999);
}

/* Energy colors */
.energy-very-high { color: #22c55e; }
.energy-high { color: #84cc16; }
.energy-medium { color: #eab308; }
.energy-low { color: #f97316; }
.energy-very-low { color: #ef4444; }

/* Distribution */
.distribution-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
}

.energy-distribution {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
}

.distribution-row {
  display: grid;
  grid-template-columns: 80px 1fr 40px 40px;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
}

.dist-label {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  font-weight: 500;
}

.dist-bar-container {
  height: 16px;
  background: var(--ds-surface-ground, var(--surface-ground));
  border-radius: 8px;
  overflow: hidden;
}

.dist-bar {
  height: 100%;
  border-radius: 8px;
  min-width: 2px;
  transition: width 0.3s ease;
}

.dist-count {
  text-align: right;
  font-weight: 600;
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.dist-pct {
  text-align: right;
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

/* Recommendations */
.recommendations-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
}

.recommendations-list {
  margin: 0;
  padding-left: var(--ds-space-5, 1.25rem);
  list-style-type: disc;
}

.recommendations-list li {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.6;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.chapter-recs {
  margin-bottom: var(--ds-space-3, 0.75rem);
}

/* Chapter accordion */
.chapter-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3, 0.75rem);
  width: 100%;
  flex-wrap: wrap;
}

.chapter-title {
  font-weight: 600;
}

.chapter-badges {
  display: flex;
  gap: var(--ds-space-1, 0.25rem);
  flex-wrap: wrap;
}

.chapter-detail {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3, 0.75rem);
}

.chapter-subscores {
  display: flex;
  gap: var(--ds-space-4, 1rem);
  flex-wrap: wrap;
}

.subscore {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-1, 0.25rem);
}

.subscore-label {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.subscore-value {
  font-size: 1.25rem;
  font-weight: 700;
}

/* Low energy list */
.low-energy-list h4 {
  margin: 0 0 var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
  font-weight: 600;
}

.low-energy-item {
  padding: var(--ds-space-3, 0.75rem);
  background: var(--ds-surface-ground, var(--surface-ground));
  border-radius: var(--ds-radius-md, 8px);
  border-left: 3px solid var(--ds-color-warn, #f97316);
  margin-bottom: var(--ds-space-2, 0.5rem);
}

.sent-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin-bottom: var(--ds-space-2, 0.5rem);
  flex-wrap: wrap;
}

.sent-score {
  font-weight: 600;
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.sent-flags {
  display: flex;
  gap: var(--ds-space-1, 0.25rem);
}

.sent-text {
  margin: 0 0 var(--ds-space-2, 0.5rem);
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.6;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-style: italic;
}

.sent-issues {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1, 0.25rem);
}

.issue-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
}

.issue-tag {
  flex-shrink: 0;
}

.issue-suggestion {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.no-issues {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  color: var(--ds-color-success, #22c55e);
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.no-issues i {
  font-size: 1.125rem;
}
</style>
