<template>
  <div class="sensory-report-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-palette"></i>
          Reporte Sensorial
        </h3>
        <p class="subtitle">
          Analiza la presencia de los 5 sentidos en tu narrativa.
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
      <p>Analizando densidad sensorial...</p>
    </div>

    <!-- Error -->
    <AnalysisErrorState v-else-if="errorMsg" :message="errorMsg" :on-retry="analyze" />

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar detalles sensoriales.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card v-for="sense in senseOrder" :key="sense" class="stat-card sense-card">
          <template #content>
            <div class="stat-content" :class="'sense-' + sense">
              <i :class="senseIcons[sense]"></i>
              <span class="stat-value">{{ report.by_sense[sense] || 0 }}</span>
              <span class="stat-label">{{ senseNames[sense] || sense }}</span>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <span class="stat-value">{{ report.total_details }}</span>
              <span class="stat-label">Total detalles</span>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <span class="stat-value">{{ report.overall_density?.toFixed(1) }}</span>
              <span class="stat-label">Densidad / 1000 pal.</span>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <Tag
                :severity="densitySeverity(report.overall_density_level)"
                :value="densityLabel(report.overall_density_level)"
              />
              <span class="stat-label">Nivel global</span>
            </div>
          </template>
        </Card>
      </div>

      <!-- Balance -->
      <Card v-if="report.balance_score !== undefined" class="balance-card">
        <template #title>Equilibrio sensorial</template>
        <template #content>
          <div class="balance-bar-container">
            <div
              v-for="sense in senseOrder"
              :key="sense"
              v-tooltip.top="senseNames[sense] + ': ' + (report.sense_percentages?.[sense] || 0).toFixed(1) + '%'"
              class="balance-segment"
              :class="'sense-bg-' + sense"
              :style="{ width: (report.sense_percentages?.[sense] || 0) + '%' }"
            />
          </div>
          <div class="balance-legend">
            <span v-for="sense in senseOrder" :key="sense" class="legend-item">
              <span class="legend-dot" :class="'sense-bg-' + sense" />
              {{ senseNames[sense] }} ({{ (report.sense_percentages?.[sense] || 0).toFixed(0) }}%)
            </span>
          </div>
          <div class="balance-info">
            <span>Puntuación de equilibrio: <strong>{{ (report.balance_score * 100).toFixed(0) }}%</strong></span>
            <span v-if="report.dominant_sense"> | Dominante: <Tag :value="senseNames[report.dominant_sense]" severity="info" /></span>
            <span v-if="report.weakest_sense"> | Más débil: <Tag :value="senseNames[report.weakest_sense]" severity="warn" /></span>
          </div>
        </template>
      </Card>

      <!-- Sugerencias de enriquecimiento -->
      <Card v-if="report.suggestions?.length" class="suggestions-card">
        <template #title>
          <i class="pi pi-lightbulb"></i>
          Sugerencias de enriquecimiento ({{ report.suggestions.length }})
        </template>
        <template #content>
          <div class="suggestions-list">
            <div
              v-for="(sug, idx) in report.suggestions"
              :key="idx"
              class="suggestion-item"
            >
              <Tag
                :severity="sug.priority === 'high' ? 'danger' : sug.priority === 'medium' ? 'warning' : 'info'"
                :value="sug.priority === 'high' ? 'Alta' : sug.priority === 'medium' ? 'Media' : 'Baja'"
              />
              <span class="suggestion-text">{{ sug.message }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Por capítulo -->
      <Card v-if="report.chapter_stats?.length" class="chapters-card">
        <template #title>Densidad por capítulo</template>
        <template #content>
          <Accordion>
            <AccordionPanel
              v-for="ch in report.chapter_stats"
              :key="ch.chapter"
              :value="'ch-' + ch.chapter"
            >
              <AccordionHeader>
                <div class="chapter-header-row">
                  <span class="chapter-label">Capítulo {{ ch.chapter }}</span>
                  <Tag
                    :severity="densitySeverity(ch.density_level)"
                    :value="densityLabel(ch.density_level)"
                    class="chapter-density-tag"
                  />
                  <span class="chapter-count">{{ ch.details_count }} detalles</span>
                  <span v-if="ch.missing_senses?.length" class="missing-hint">
                    <i class="pi pi-exclamation-triangle" />
                    {{ ch.missing_senses.length }} sentidos ausentes
                  </span>
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="chapter-sense-grid">
                  <div v-for="sense in senseOrder" :key="sense" class="sense-row">
                    <span class="sense-name" :class="'sense-text-' + sense">
                      <i :class="senseIcons[sense]" /> {{ senseNames[sense] }}
                    </span>
                    <span class="sense-count">{{ ch.by_sense?.[sense] || 0 }}</span>
                    <Tag
                      v-if="ch.missing_senses?.includes(sense)"
                      value="Ausente"
                      severity="warn"
                      class="sense-absent-tag"
                    />
                  </div>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
        </template>
      </Card>

      <!-- Detalles detectados -->
      <Card v-if="report.details?.length" class="details-card">
        <template #title>
          Detalles detectados ({{ filteredDetails.length }})
        </template>
        <template #subtitle>
          <div class="filter-row">
            <Button
              v-for="sense in senseOrder"
              :key="sense"
              :label="senseNames[sense]"
              :class="{ 'active-filter': filterSense === sense }"
              :outlined="filterSense !== sense"
              size="small"
              @click="filterSense = filterSense === sense ? null : sense"
            />
            <Button
              v-if="filterSense"
              label="Todos"
              text
              size="small"
              @click="filterSense = null"
            />
          </div>
        </template>
        <template #content>
          <div class="details-list">
            <div
              v-for="(detail, idx) in paginatedDetails"
              :key="idx"
              class="detail-item"
              :class="'sense-border-' + detail.sense"
            >
              <div class="detail-header">
                <Tag
                  :value="senseNames[detail.sense] || detail.sense"
                  :severity="senseSeverity(detail.sense)"
                  class="detail-sense-tag"
                />
                <span v-if="detail.chapter" class="detail-chapter">Cap. {{ detail.chapter }}</span>
                <span class="detail-confidence">{{ (detail.confidence * 100).toFixed(0) }}%</span>
              </div>
              <div class="detail-context">
                <span class="context-text">...{{ detail.context }}...</span>
              </div>
              <div class="detail-keyword">
                Palabra clave: <strong>{{ detail.keyword }}</strong>
              </div>
            </div>
            <div v-if="filteredDetails.length > pageSize" class="pagination-row">
              <Button
                label="Anterior"
                icon="pi pi-chevron-left"
                text
                size="small"
                :disabled="page === 0"
                @click="page--"
              />
              <span>{{ page + 1 }} / {{ totalPages }}</span>
              <Button
                label="Siguiente"
                icon="pi pi-chevron-right"
                icon-pos="right"
                text
                size="small"
                :disabled="page >= totalPages - 1"
                @click="page++"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
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

const loading = ref(false)
const report = ref<any>(null)
const errorMsg = ref<string | null>(null)
const filterSense = ref<string | null>(null)
const page = ref(0)
const pageSize = 20

const senseOrder = ['sight', 'hearing', 'touch', 'smell', 'taste']

const senseNames: Record<string, string> = {
  sight: 'Vista',
  hearing: 'Oído',
  touch: 'Tacto',
  smell: 'Olfato',
  taste: 'Gusto',
}

const senseIcons: Record<string, string> = {
  sight: 'pi pi-eye',
  hearing: 'pi pi-volume-up',
  touch: 'pi pi-hand',
  smell: 'pi pi-cloud',
  taste: 'pi pi-star',
}

function densitySeverity(level: string): string {
  switch (level) {
    case 'rich': return 'success'
    case 'adequate': return 'info'
    case 'sparse': return 'warn'
    case 'absent': return 'danger'
    default: return 'secondary'
  }
}

function densityLabel(level: string): string {
  switch (level) {
    case 'rich': return 'Rico'
    case 'adequate': return 'Adecuado'
    case 'sparse': return 'Escaso'
    case 'absent': return 'Ausente'
    default: return level
  }
}

function senseSeverity(sense: string): string {
  switch (sense) {
    case 'sight': return 'info'
    case 'hearing': return 'success'
    case 'touch': return 'warn'
    case 'smell': return 'danger'
    case 'taste': return 'contrast'
    default: return 'secondary'
  }
}

const filteredDetails = computed(() => {
  if (!report.value?.details) return []
  if (!filterSense.value) return report.value.details
  return report.value.details.filter((d: any) => d.sense === filterSense.value)
})

const totalPages = computed(() => Math.ceil(filteredDetails.value.length / pageSize))

const paginatedDetails = computed(() => {
  const start = page.value * pageSize
  return filteredDetails.value.slice(start, start + pageSize)
})

// Auto-load on mount
onMounted(() => {
  if (props.projectId) {
    analyze()
  }
})

watch(() => props.projectId, () => {
  report.value = null
  errorMsg.value = null
  if (props.projectId) {
    analyze()
  }
})

async function analyze() {
  loading.value = true
  errorMsg.value = null
  try {
    const json = await api.getRaw<{ success: boolean; data: any; error?: string }>(
      `/api/projects/${props.projectId}/sensory-report`
    )
    if (json.success) {
      report.value = json.data
      // Use backend sense names if provided
      if (json.data.sense_names) {
        Object.assign(senseNames, json.data.sense_names)
      }
    } else {
      errorMsg.value = json.error || 'Error al analizar reporte sensorial'
    }
  } catch (e) {
    console.error('Sensory report error:', e)
    errorMsg.value = e instanceof Error ? e.message : 'No se pudo generar el informe sensorial. Si persiste, reinicia la aplicación.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.sensory-report-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tab-header h3 { margin: 0; display: flex; align-items: center; gap: 0.5rem; }
.tab-header .subtitle { margin: 0.25rem 0 0; color: var(--text-color-secondary); font-size: 0.85rem; }

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem;
  color: var(--text-color-secondary);
}
.empty-state i { font-size: 2rem; }

.stats-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.stat-card { flex: 1 1 100px; min-width: 100px; }
.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  text-align: center;
}
.stat-value { font-size: 1.5rem; font-weight: 700; }
.stat-label { font-size: 0.75rem; color: var(--text-color-secondary); }

/* Sense colors */
.sense-sight, .sense-text-sight { color: #3b82f6; }
.sense-hearing, .sense-text-hearing { color: #22c55e; }
.sense-touch, .sense-text-touch { color: #f59e0b; }
.sense-smell, .sense-text-smell { color: #a855f7; }
.sense-taste, .sense-text-taste { color: #ef4444; }

.sense-bg-sight { background-color: #3b82f6; }
.sense-bg-hearing { background-color: #22c55e; }
.sense-bg-touch { background-color: #f59e0b; }
.sense-bg-smell { background-color: #a855f7; }
.sense-bg-taste { background-color: #ef4444; }

.sense-border-sight { border-left: 3px solid #3b82f6; }
.sense-border-hearing { border-left: 3px solid #22c55e; }
.sense-border-touch { border-left: 3px solid #f59e0b; }
.sense-border-smell { border-left: 3px solid #a855f7; }
.sense-border-taste { border-left: 3px solid #ef4444; }

/* Balance bar */
.balance-bar-container {
  display: flex;
  height: 24px;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 0.75rem;
}
.balance-segment { transition: width 0.3s ease; min-width: 2px; }
.balance-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
}
.legend-item { display: flex; align-items: center; gap: 0.25rem; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.balance-info { font-size: 0.85rem; color: var(--text-color-secondary); }

/* Chapters */
.chapter-header-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}
.chapter-label { font-weight: 600; }
.chapter-count { font-size: 0.85rem; color: var(--text-color-secondary); }
.missing-hint { font-size: 0.8rem; color: var(--orange-500); }
.chapter-sense-grid { display: flex; flex-direction: column; gap: 0.4rem; }
.sense-row { display: flex; align-items: center; gap: 0.5rem; }
.sense-name { width: 80px; font-size: 0.85rem; }
.sense-count { font-weight: 600; min-width: 30px; }

/* Details */
.filter-row { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.5rem; }
.active-filter { font-weight: 700; }
.details-list { display: flex; flex-direction: column; gap: 0.5rem; }
.detail-item {
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  background: var(--surface-ground);
}
.detail-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}
.detail-chapter { font-size: 0.8rem; color: var(--text-color-secondary); }
.detail-confidence { font-size: 0.75rem; color: var(--text-color-secondary); margin-left: auto; }
.detail-context { font-size: 0.85rem; font-style: italic; color: var(--text-color-secondary); }
.detail-keyword { font-size: 0.8rem; margin-top: 0.25rem; }
.pagination-row { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 0.5rem; }

/* Suggestions */
.suggestions-card { border-left: 3px solid var(--orange-400); }
.suggestions-list { display: flex; flex-direction: column; gap: 0.75rem; }
.suggestion-item { display: flex; align-items: flex-start; gap: 0.5rem; }
.suggestion-text { font-size: 0.85rem; color: var(--text-color-secondary); line-height: 1.4; }
</style>
