<template>
  <div class="echo-report-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-sync"></i>
          Echo Report
        </h3>
        <p class="subtitle">
          Detecta repeticiones de palabras en proximidad que afectan la fluidez del texto.
        </p>
      </div>
      <div class="header-controls">
        <div class="distance-control">
          <label>Distancia:</label>
          <InputNumber v-model="minDistance" :min="10" :max="200" :step="10" suffix=" palabras" />
        </div>
        <div class="semantic-control">
          <Checkbox v-model="includeSemantic" binary inputId="semantic" />
          <label for="semantic">Semánticas</label>
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
      <p>Analizando repeticiones...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar repeticiones.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_repetitions }}</div>
              <div class="stat-label">Repeticiones</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value severity-high">
                {{ report.global_stats.by_severity?.high || 0 }}
              </div>
              <div class="stat-label">Muy cercanas</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value severity-medium">
                {{ report.global_stats.by_severity?.medium || 0 }}
              </div>
              <div class="stat-label">Cercanas</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_words }}</div>
              <div class="stat-label">Palabras analizadas</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Top repeated words -->
      <Card v-if="report.global_stats.top_repeated_words?.length > 0" class="top-words-card">
        <template #title>
          <i class="pi pi-chart-bar"></i>
          Palabras más repetidas
        </template>
        <template #content>
          <div class="top-words-list">
            <Tag
              v-for="item in report.global_stats.top_repeated_words.slice(0, 15)"
              :key="item.word"
              :value="`${item.word} (${item.count})`"
              severity="secondary"
              class="word-tag"
            />
          </div>
        </template>
      </Card>

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
                  v-if="chapter.repetition_count > 0"
                  :severity="getChapterSeverity(chapter)"
                  :value="`${chapter.repetition_count} repeticiones`"
                />
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <!-- Repetitions list -->
            <div v-if="getFilteredRepetitions(chapter).length > 0" class="repetitions-list">
              <div
                v-for="(rep, idx) in getFilteredRepetitions(chapter)"
                :key="idx"
                class="repetition-item"
                :class="'severity-' + rep.severity"
              >
                <div class="rep-header">
                  <span class="rep-word">{{ rep.word }}</span>
                  <Tag :severity="getSeverityColor(rep.severity)" :value="`${rep.count}x`" />
                  <Tag severity="secondary" :value="getTypeLabel(rep.type)" />
                  <span class="rep-distance">
                    Min: {{ rep.min_distance }} palabras
                  </span>
                </div>

                <!-- Occurrences -->
                <div class="occurrences">
                  <div
                    v-for="(occ, occIdx) in rep.occurrences.slice(0, 5)"
                    :key="occIdx"
                    class="occurrence"
                  >
                    <span class="occ-position">#{{ Number(occIdx) + 1 }}</span>
                    <span class="occ-text" v-html="highlightWord(occ.sentence || occ.text, rep.word)"></span>
                  </div>
                  <span v-if="rep.occurrences.length > 5" class="more-occurrences">
                    +{{ rep.occurrences.length - 5 }} más...
                  </span>
                </div>
              </div>
            </div>

            <Message v-else severity="success" :closable="false">
              Este capítulo no tiene repeticiones problemáticas.
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
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
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
const minDistance = ref(50)
const includeSemantic = ref(false)
const report = ref<any>(null)
const severityFilter = ref('all')

const severityOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Muy cercanas', value: 'high' },
  { label: 'Cercanas', value: 'medium' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Filtered chapters
const filteredChapters = computed(() => {
  if (!report.value?.chapters) return []

  return report.value.chapters.filter((ch: any) => {
    if (severityFilter.value === 'all') return ch.repetition_count > 0
    return ch.by_severity?.[severityFilter.value] > 0
  })
})

// Get filtered repetitions for a chapter
function getFilteredRepetitions(chapter: any) {
  if (severityFilter.value === 'all') return chapter.repetitions
  return chapter.repetitions.filter((r: any) => r.severity === severityFilter.value)
}

// Analyze
async function analyze() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      min_distance: minDistance.value.toString(),
      include_semantic: includeSemantic.value.toString(),
    })
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/echo-report?${params}`
    )
    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing echo report:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron analizar las repeticiones',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getChapterSeverity(chapter: any): string {
  if (chapter.by_severity?.high > 0) return 'danger'
  if (chapter.by_severity?.medium > 0) return 'warn'
  return 'secondary'
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'high': return 'danger'
    case 'medium': return 'warn'
    default: return 'secondary'
  }
}

function getTypeLabel(type: string): string {
  switch (type) {
    case 'lexical': return 'Exacta'
    case 'lemma': return 'Lema'
    case 'semantic': return 'Semántica'
    default: return type
  }
}

function highlightWord(text: string, word: string): string {
  if (!text || !word) return text
  const regex = new RegExp(`(${word})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}
</script>

<style scoped>
.echo-report-tab {
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
  flex-wrap: wrap;
}

.distance-control,
.semantic-control {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.distance-control label,
.semantic-control label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
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
.severity-high { color: #ef4444; }
.severity-medium { color: #f97316; }
.severity-low { color: #6b7280; }

/* Top words card */
.top-words-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.top-words-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.word-tag {
  font-family: var(--ds-font-family-mono);
}

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

/* Repetitions list */
.repetitions-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.repetition-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-surface-border);
}

.repetition-item.severity-high {
  border-left-color: #ef4444;
}

.repetition-item.severity-medium {
  border-left-color: #f97316;
}

.rep-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-2);
}

.rep-word {
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-lg);
  font-family: var(--ds-font-family-mono);
}

.rep-distance {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-left: auto;
}

/* Occurrences */
.occurrences {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.occurrence {
  display: flex;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  line-height: 1.5;
}

.occ-position {
  color: var(--ds-color-text-tertiary);
  font-size: var(--ds-font-size-xs);
  min-width: 24px;
}

.occ-text {
  color: var(--ds-color-text-secondary);
}

.occ-text :deep(mark) {
  background: var(--p-yellow-200);
  color: var(--p-yellow-900);
  padding: 0 2px;
  border-radius: 2px;
}

.more-occurrences {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  font-style: italic;
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
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
