<script setup lang="ts">
/**
 * NarrativeTemplatesTab - Diagnóstico de plantillas narrativas
 *
 * Evalúa si el manuscrito sigue patrones conocidos (Tres Actos, Viaje del Héroe,
 * Save the Cat, Kishotenketsu, Cinco Actos). Herramienta diagnóstica, no prescriptiva.
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
import { api } from '@/services/apiClient'
import AnalysisErrorState from '@/components/shared/AnalysisErrorState.vue'

const props = defineProps<{
  projectId: number
}>()

interface Beat {
  beat_id: string
  name: string
  description: string
  expected_position: number
  status: 'detected' | 'possible' | 'missing' | 'n_a'
  detected_chapter: number | null
  detected_position: number
  confidence: number
  evidence: string
}

interface TemplateMatch {
  template_type: string
  template_name: string
  template_description: string
  fit_score: number
  beats: Beat[]
  detected_count: number
  possible_count: number
  missing_count: number
  total_beats: number
  gaps: string[]
  strengths: string[]
  suggestions: string[]
}

interface TemplateReport {
  best_match: TemplateMatch | null
  matches: TemplateMatch[]
  total_chapters: number
  manuscript_summary: string
}

const loading = ref(false)
const report = ref<TemplateReport | null>(null)
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
    const data = await api.getRaw<{ success: boolean; data: TemplateReport; error?: string }>(
      `/api/projects/${props.projectId}/narrative-templates`
    )
    if (data.success) {
      report.value = data.data
    } else {
      errorMsg.value = data.error || 'Error al analizar plantillas narrativas'
    }
  } catch (error) {
    console.error('Error analyzing narrative templates:', error)
    errorMsg.value = error instanceof Error ? error.message : 'No se pudo analizar las plantillas narrativas.'
  } finally {
    loading.value = false
  }
}

function _getFitClass(score: number): string {
  if (score >= 60) return 'fit-high'
  if (score >= 35) return 'fit-medium'
  return 'fit-low'
}

function getFitSeverity(score: number): 'success' | 'warn' | 'danger' | 'info' {
  if (score >= 60) return 'success'
  if (score >= 35) return 'warn'
  return 'danger'
}

function getBeatStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    detected: 'pi pi-check-circle',
    possible: 'pi pi-question-circle',
    missing: 'pi pi-times-circle',
    n_a: 'pi pi-minus-circle',
  }
  return icons[status] || 'pi pi-circle'
}

function getBeatStatusColor(status: string): string {
  const colors: Record<string, string> = {
    detected: '#22c55e',
    possible: '#eab308',
    missing: '#ef4444',
    n_a: '#999',
  }
  return colors[status] || '#999'
}

function getBeatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    detected: 'Detectado',
    possible: 'Posible',
    missing: 'No encontrado',
    n_a: 'N/A',
  }
  return labels[status] || status
}

const sortedMatches = computed(() => {
  if (!report.value) return []
  return [...report.value.matches].sort((a, b) => b.fit_score - a.fit_score)
})
</script>

<template>
  <div class="narrative-templates-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-sitemap"></i>
          Plantillas Narrativas
        </h3>
        <p class="subtitle">
          Diagnóstico de estructura: ¿qué patrón narrativo sigue el manuscrito?
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
      <p>Analizando estructura narrativa...</p>
    </div>

    <!-- Error -->
    <AnalysisErrorState v-else-if="errorMsg" :message="errorMsg" :on-retry="analyze" />

    <!-- Empty -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-sitemap"></i>
      <p>Haz clic en "Analizar" para evaluar la estructura narrativa.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Summary -->
      <Card class="summary-card">
        <template #content>
          <p class="manuscript-summary">{{ report.manuscript_summary }}</p>
        </template>
      </Card>

      <!-- Template matches -->
      <Accordion :multiple="true" :value="sortedMatches.length ? [sortedMatches[0].template_type] : []">
        <AccordionPanel
          v-for="match in sortedMatches"
          :key="match.template_type"
          :value="match.template_type"
        >
          <AccordionHeader>
            <div class="template-header">
              <span class="template-name">{{ match.template_name }}</span>
              <div class="template-badges">
                <Tag
                  :value="match.fit_score + '%'"
                  :severity="getFitSeverity(match.fit_score)"
                />
                <span class="beat-counts">
                  <span class="beat-detected">{{ match.detected_count }}</span>/
                  <span class="beat-total">{{ match.total_beats }}</span>
                </span>
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="template-detail">
              <p class="template-desc">{{ match.template_description }}</p>

              <!-- Beat timeline -->
              <div class="beat-timeline">
                <div class="timeline-bar">
                  <div
                    v-for="beat in match.beats"
                    :key="beat.beat_id"
                    class="timeline-marker"
                    :style="{ left: (beat.expected_position * 100) + '%' }"
                    :title="beat.name + ' (' + getBeatStatusLabel(beat.status) + ')'"
                  >
                    <div
                      class="marker-dot"
                      :style="{ backgroundColor: getBeatStatusColor(beat.status) }"
                    />
                  </div>
                </div>
                <div class="timeline-labels">
                  <span>Inicio</span>
                  <span>25%</span>
                  <span>50%</span>
                  <span>75%</span>
                  <span>Final</span>
                </div>
              </div>

              <!-- Beats list -->
              <div class="beats-list">
                <div
                  v-for="beat in match.beats"
                  :key="beat.beat_id"
                  class="beat-item"
                  :class="'beat-' + beat.status"
                >
                  <i :class="getBeatStatusIcon(beat.status)" :style="{ color: getBeatStatusColor(beat.status) }" />
                  <div class="beat-info">
                    <span class="beat-name">{{ beat.name }}</span>
                    <span class="beat-desc">{{ beat.description }}</span>
                    <span v-if="beat.evidence" class="beat-evidence">{{ beat.evidence }}</span>
                  </div>
                  <div class="beat-meta">
                    <span v-if="beat.detected_chapter" class="beat-chapter">
                      Cap. {{ beat.detected_chapter }}
                    </span>
                    <span class="beat-position">
                      {{ Math.round(beat.expected_position * 100) }}%
                    </span>
                  </div>
                </div>
              </div>

              <!-- Strengths -->
              <div v-if="match.strengths.length" class="template-section">
                <h4><i class="pi pi-check"></i> Puntos fuertes</h4>
                <ul>
                  <li v-for="(s, i) in match.strengths" :key="i">{{ s }}</li>
                </ul>
              </div>

              <!-- Gaps -->
              <div v-if="match.gaps.length" class="template-section">
                <h4><i class="pi pi-exclamation-triangle"></i> Huecos</h4>
                <ul>
                  <li v-for="(g, i) in match.gaps" :key="i">{{ g }}</li>
                </ul>
              </div>

              <!-- Suggestions -->
              <div v-if="match.suggestions.length" class="template-section">
                <h4><i class="pi pi-lightbulb"></i> Sugerencias</h4>
                <ul>
                  <li v-for="(s, i) in match.suggestions" :key="i">{{ s }}</li>
                </ul>
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>
    </div>
  </div>
</template>

<style scoped>
.narrative-templates-tab {
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

.manuscript-summary {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--ds-color-text, var(--text-color));
}

/* Template header */
.template-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3, 0.75rem);
  width: 100%;
}

.template-name { font-weight: 600; }

.template-badges {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin-left: auto;
}

.beat-counts {
  font-size: 0.8125rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.beat-detected { font-weight: 700; color: var(--ds-color-text, var(--text-color)); }
.beat-total { font-weight: 400; }

.template-desc {
  margin: 0 0 var(--ds-space-3, 0.75rem);
  font-size: var(--ds-font-size-sm, 0.8125rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-style: italic;
}

/* Beat timeline */
.beat-timeline {
  margin-bottom: var(--ds-space-4, 1rem);
}

.timeline-bar {
  position: relative;
  height: 24px;
  background: var(--ds-surface-ground, var(--surface-ground));
  border-radius: 12px;
  margin-bottom: var(--ds-space-1, 0.25rem);
}

.timeline-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
}

.marker-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--ds-surface-card, white);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.timeline-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
  color: var(--ds-color-text-tertiary, #999);
}

/* Beats list */
.beats-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1, 0.25rem);
  margin-bottom: var(--ds-space-3, 0.75rem);
}

.beat-item {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  gap: var(--ds-space-2, 0.5rem);
  align-items: start;
  padding: var(--ds-space-2, 0.5rem);
  border-radius: var(--ds-radius-sm, 4px);
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.beat-item:hover {
  background: var(--ds-surface-hover, var(--surface-hover));
}

.beat-item i { margin-top: 2px; }

.beat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.beat-name { font-weight: 600; }

.beat-desc {
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: 0.75rem;
}

.beat-evidence {
  color: var(--ds-color-text-tertiary, #999);
  font-size: 0.75rem;
  font-style: italic;
}

.beat-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  white-space: nowrap;
}

.beat-chapter {
  font-weight: 600;
  font-size: 0.75rem;
}

.beat-position {
  color: var(--ds-color-text-tertiary, #999);
  font-size: 0.6875rem;
}

/* Sections */
.template-section {
  margin-top: var(--ds-space-3, 0.75rem);
}

.template-section h4 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin: 0 0 var(--ds-space-2, 0.5rem);
  font-size: 0.875rem;
}

.template-section ul {
  margin: 0;
  padding-left: var(--ds-space-5, 1.25rem);
}

.template-section li {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.6;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

/* Fit colors */
.fit-high { color: #22c55e; }
.fit-medium { color: #eab308; }
.fit-low { color: #ef4444; }
</style>
