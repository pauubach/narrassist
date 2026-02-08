<template>
  <div class="duplicate-content-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-copy"></i>
          Contenido Duplicado
        </h3>
        <p class="subtitle">
          Detecta frases y párrafos repetidos o muy similares (posibles copy/paste).
        </p>
      </div>
      <div class="header-controls">
        <div class="threshold-control">
          <label>Umbral frases:</label>
          <InputNumber
            v-model="sentenceThreshold"
            :min="0.5"
            :max="1"
            :step="0.05"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
          />
        </div>
        <div class="threshold-control">
          <label>Umbral párrafos:</label>
          <InputNumber
            v-model="paragraphThreshold"
            :min="0.5"
            :max="1"
            :step="0.05"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
          />
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
      <p>Analizando contenido duplicado...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar contenido duplicado.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_duplicates }}</div>
              <div class="stat-label">Duplicados</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="{ 'severity-critical': (report.global_stats.by_severity?.critical || 0) > 0 }">
                {{ report.global_stats.by_severity?.critical || 0 }}
              </div>
              <div class="stat-label">Exactos</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="{ 'severity-high': (report.global_stats.by_severity?.high || 0) > 0 }">
                {{ report.global_stats.by_severity?.high || 0 }}
              </div>
              <div class="stat-label">Muy similares</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.sentences_analyzed }}</div>
              <div class="stat-label">Frases analizadas</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- No duplicates message -->
      <Message v-if="report.global_stats.total_duplicates === 0" severity="success" :closable="false">
        No se encontraron duplicados en el manuscrito.
      </Message>

      <!-- Type Filter -->
      <div v-if="report.global_stats.total_duplicates > 0" class="filter-section">
        <span class="filter-label">Mostrar:</span>
        <SelectButton v-model="typeFilter" :options="typeOptions" option-label="label" option-value="value" />
      </div>

      <!-- Duplicates List -->
      <div v-if="filteredDuplicates.length > 0" class="duplicates-list">
        <Card
          v-for="(dup, idx) in filteredDuplicates"
          :key="idx"
          class="duplicate-card"
          :class="'severity-border-' + dup.severity"
        >
          <template #header>
            <div class="duplicate-header">
              <div class="dup-tags">
                <Tag :severity="getSeverityColor(dup.severity)" :value="getSeverityLabel(dup.severity)" />
                <Tag severity="secondary" :value="getTypeLabel(dup.duplicate_type)" />
                <span class="similarity-badge">
                  {{ Math.round(dup.similarity * 100) }}% similar
                </span>
              </div>
              <div class="dup-chapters">
                <span v-if="dup.location1.chapter !== dup.location2.chapter">
                  Cap. {{ dup.location1.chapter }} ↔ Cap. {{ dup.location2.chapter }}
                </span>
                <span v-else>
                  Cap. {{ dup.location1.chapter }}
                </span>
              </div>
            </div>
          </template>

          <template #content>
            <div class="duplicate-content">
              <!-- Location 1 -->
              <div class="location-box">
                <div class="location-label">
                  <i class="pi pi-bookmark"></i>
                  Ubicación 1
                  <span class="char-position">(pos. {{ dup.location1.start_char }})</span>
                </div>
                <div class="location-text">{{ dup.location1.text }}</div>
              </div>

              <!-- Arrow -->
              <div class="arrow-separator">
                <i class="pi pi-arrows-v"></i>
              </div>

              <!-- Location 2 -->
              <div class="location-box">
                <div class="location-label">
                  <i class="pi pi-bookmark"></i>
                  Ubicación 2
                  <span class="char-position">(pos. {{ dup.location2.start_char }})</span>
                </div>
                <div class="location-text">{{ dup.location2.text }}</div>
              </div>
            </div>
          </template>
        </Card>
      </div>

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
const sentenceThreshold = ref(0.90)
const paragraphThreshold = ref(0.85)
const report = ref<any>(null)
const typeFilter = ref('all')

const typeOptions = [
  { label: 'Todos', value: 'all' },
  { label: 'Frases', value: 'sentence' },
  { label: 'Párrafos', value: 'paragraph' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Filtered duplicates
const filteredDuplicates = computed(() => {
  if (!report.value?.duplicates) return []

  if (typeFilter.value === 'all') return report.value.duplicates

  return report.value.duplicates.filter((d: any) => {
    if (typeFilter.value === 'sentence') {
      return d.duplicate_type.includes('sentence')
    }
    if (typeFilter.value === 'paragraph') {
      return d.duplicate_type.includes('paragraph')
    }
    return true
  })
})

// Analyze
async function analyze() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      sentence_threshold: sentenceThreshold.value.toString(),
      paragraph_threshold: paragraphThreshold.value.toString(),
      min_sentence_length: '30',
    })
    const data = await api.getRaw<{ success: boolean; data: any; error?: string }>(
      `/api/projects/${props.projectId}/duplicate-content?${params}`
    )

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing duplicate content:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar el contenido duplicado',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'danger'
    case 'high': return 'warn'
    case 'medium': return 'secondary'
    default: return 'info'
  }
}

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case 'critical': return 'Exacto'
    case 'high': return 'Muy similar'
    case 'medium': return 'Similar'
    default: return severity
  }
}

function getTypeLabel(type: string): string {
  switch (type) {
    case 'exact_sentence': return 'Frase exacta'
    case 'near_sentence': return 'Frase similar'
    case 'exact_paragraph': return 'Párrafo exacto'
    case 'near_paragraph': return 'Párrafo similar'
    case 'semantic_paragraph': return 'Semánticamente similar'
    default: return type
  }
}
</script>

<style scoped>
.duplicate-content-tab {
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
  gap: var(--ds-space-3);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  white-space: nowrap;
}

.threshold-control label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.threshold-control :deep(.p-inputnumber) {
  width: 70px;
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

/* Severity colors - WCAG compliant */
.severity-critical { color: #b91c1c; }  /* red-700 */
.severity-high { color: #c2410c; }      /* orange-700 */
.severity-medium { color: #a16207; }    /* yellow-700 */

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

/* Duplicates list */
.duplicates-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.duplicate-card {
  border-left: 4px solid var(--ds-surface-border);
}

.duplicate-card.severity-border-critical {
  border-left-color: #b91c1c;
}

.duplicate-card.severity-border-high {
  border-left-color: #c2410c;
}

.duplicate-card.severity-border-medium {
  border-left-color: #a16207;
}

.duplicate-card :deep(.p-card-header) {
  padding: var(--ds-space-3);
  padding-bottom: 0;
}

.duplicate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.dup-tags {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.similarity-badge {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  font-weight: var(--ds-font-weight-medium);
}

.dup-chapters {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.duplicate-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.location-box {
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-3);
}

.location-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-2);
}

.char-position {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
}

.location-text {
  font-size: var(--ds-font-size-sm);
  line-height: 1.6;
  color: var(--ds-color-text);
}

.arrow-separator {
  display: flex;
  justify-content: center;
  padding: var(--ds-space-1) 0;
  color: var(--ds-color-text-tertiary);
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
