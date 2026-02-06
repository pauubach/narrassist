<template>
  <div class="emotional-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-heart"></i>
          Coherencia Emocional
        </h3>
        <p class="subtitle">
          Detecta incoherencias entre emociones declaradas y comportamientos de personajes.
        </p>
        <!-- Estado del análisis -->
        <p v-if="lastAnalysis" class="analysis-status success">
          <i class="pi pi-check-circle"></i>
          Último análisis: {{ lastAnalysis.toLocaleTimeString() }}
        </p>
        <p v-else-if="analysisError" class="analysis-status error">
          <i class="pi pi-exclamation-triangle"></i>
          Error: {{ analysisError }}
        </p>
        <p v-else class="analysis-status pending">
          <i class="pi pi-info-circle"></i>
          No analizado
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
      <p>Analizando coherencia emocional...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar incoherencias emocionales.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Stats Summary -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.stats.total_incoherences }}</div>
              <div class="stat-label">Incoherencias</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.stats.characters_affected }}</div>
              <div class="stat-label">Personajes afectados</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.stats.chapters_affected }}</div>
              <div class="stat-label">Capítulos afectados</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ formatPercent(report.stats.avg_confidence) }}</div>
              <div class="stat-label">Confianza media</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- No Incoherences Message -->
      <Message v-if="report.incoherences.length === 0" severity="success" :closable="false" class="success-message">
        <i class="pi pi-check-circle"></i>
        No se detectaron incoherencias emocionales en el manuscrito.
      </Message>

      <!-- Incoherences by Character -->
      <template v-else>
        <!-- Filter -->
        <div class="filter-section">
          <span class="filter-label">Filtrar por tipo:</span>
          <SelectButton
            v-model="typeFilter"
            :options="typeOptions"
            option-label="label"
            option-value="value"
          />
        </div>

        <!-- Accordion by Character -->
        <Accordion :multiple="true" :active-index="[0]" class="characters-accordion">
          <AccordionPanel v-for="group in filteredGroups" :key="group.character" :value="group.character">
            <AccordionHeader>
              <div class="character-header">
                <span class="character-name">
                  <i class="pi pi-user"></i>
                  {{ group.character }}
                </span>
                <Tag
                  :severity="group.incoherences.length > 3 ? 'danger' : 'warn'"
                  :value="`${group.incoherences.length} incoherencia${group.incoherences.length !== 1 ? 's' : ''}`"
                />
              </div>
            </AccordionHeader>
            <AccordionContent>
              <div class="incoherences-list">
                <div
                  v-for="(inc, idx) in group.incoherences"
                  :key="idx"
                  class="incoherence-item"
                  :class="`type-${inc.incoherence_type}`"
                >
                  <div class="inc-header">
                    <Tag :severity="getTypeSeverity(inc.incoherence_type)" :value="getTypeLabel(inc.incoherence_type)" />
                    <span class="inc-confidence">{{ formatPercent(inc.confidence) }} confianza</span>
                    <span v-if="inc.chapter_id" class="inc-chapter">
                      Cap. {{ inc.chapter_id }}
                    </span>
                  </div>

                  <p class="inc-explanation">{{ inc.explanation }}</p>

                  <div v-if="inc.declared_emotion || inc.actual_behavior" class="inc-details">
                    <div v-if="inc.declared_emotion" class="detail-row">
                      <span class="detail-label">Declarado:</span>
                      <Tag severity="info" size="small">{{ inc.declared_emotion }}</Tag>
                    </div>
                    <div v-if="inc.actual_behavior" class="detail-row">
                      <span class="detail-label">Comportamiento:</span>
                      <span class="detail-value">{{ inc.actual_behavior }}</span>
                    </div>
                  </div>

                  <div v-if="inc.behavior_text || inc.declared_text" class="inc-excerpt">
                    <div v-if="inc.declared_text" class="excerpt-block">
                      <small class="excerpt-label">Texto declarado:</small>
                      <small class="excerpt-text">"{{ truncate(inc.declared_text, 100) }}"</small>
                    </div>
                    <div v-if="inc.behavior_text" class="excerpt-block">
                      <small class="excerpt-label">Comportamiento:</small>
                      <small class="excerpt-text">"{{ truncate(inc.behavior_text, 100) }}"</small>
                    </div>
                  </div>

                  <div v-if="inc.suggestion" class="inc-suggestion">
                    <i class="pi pi-lightbulb"></i>
                    <small>{{ inc.suggestion }}</small>
                  </div>
                </div>
              </div>
            </AccordionContent>
          </AccordionPanel>
        </Accordion>
      </template>

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
import SelectButton from 'primevue/selectbutton'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/apiClient'

interface Incoherence {
  entity_name: string
  incoherence_type: string
  declared_emotion: string
  actual_behavior: string
  declared_text: string
  behavior_text: string
  confidence: number
  explanation: string
  suggestion?: string
  chapter_id?: number
  start_char: number
  end_char: number
}

interface CharacterGroup {
  character: string
  incoherences: Incoherence[]
}

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const report = ref<any>(null)
const typeFilter = ref('all')
const lastAnalysis = ref<Date | null>(null)
const analysisError = ref<string | null>(null)

const typeOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Diálogo', value: 'emotion_dialogue' },
  { label: 'Acción', value: 'emotion_action' },
  { label: 'Cambio brusco', value: 'temporal_jump' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Group incoherences by character
const groupedByCharacter = computed((): CharacterGroup[] => {
  if (!report.value?.incoherences) return []

  const groups: Record<string, Incoherence[]> = {}

  for (const inc of report.value.incoherences) {
    const name = inc.entity_name || 'Desconocido'
    if (!groups[name]) groups[name] = []
    groups[name].push(inc)
  }

  return Object.entries(groups)
    .map(([character, incoherences]) => ({ character, incoherences }))
    .sort((a, b) => b.incoherences.length - a.incoherences.length)
})

// Filtered groups by type
const filteredGroups = computed((): CharacterGroup[] => {
  if (typeFilter.value === 'all') return groupedByCharacter.value

  return groupedByCharacter.value
    .map(group => ({
      character: group.character,
      incoherences: group.incoherences.filter(inc => inc.incoherence_type === typeFilter.value)
    }))
    .filter(group => group.incoherences.length > 0)
})

// Analyze
async function analyze() {
  loading.value = true
  analysisError.value = null
  try {
    const data = await api.getRaw<{ success: boolean; data: any; error?: string }>(
      `/api/projects/${props.projectId}/emotional-analysis`
    )

    if (data.success) {
      const incoherences = data.data.incoherences || []

      // Calculate stats
      const charactersSet = new Set(incoherences.map((i: any) => i.entity_name))
      const chaptersSet = new Set(incoherences.filter((i: any) => i.chapter_id).map((i: any) => i.chapter_id))
      const avgConf = incoherences.length > 0
        ? incoherences.reduce((sum: number, i: any) => sum + (i.confidence || 0), 0) / incoherences.length
        : 0

      report.value = {
        incoherences,
        stats: {
          total_incoherences: incoherences.length,
          characters_affected: charactersSet.size,
          chapters_affected: chaptersSet.size,
          avg_confidence: avgConf,
        },
        recommendations: [
          "Las incoherencias emocionales pueden indicar errores de continuidad.",
          "Revisa los cambios bruscos de emoción sin justificación narrativa.",
          "Los diálogos deben reflejar el estado emocional declarado del personaje.",
        ],
      }
      lastAnalysis.value = new Date()
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing emotional coherence:', error)
    analysisError.value = error instanceof Error ? error.message : 'Error desconocido'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar la coherencia emocional',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function formatPercent(value: number): string {
  if (!value && value !== 0) return '0%'
  return `${Math.round(value * 100)}%`
}

function truncate(text: string, maxLen: number): string {
  if (!text) return ''
  if (text.length <= maxLen) return text
  return text.substring(0, maxLen) + '...'
}

function getTypeSeverity(type: string): string {
  switch (type) {
    case 'emotion_dialogue': return 'warn'
    case 'emotion_action': return 'info'
    case 'temporal_jump': return 'danger'
    case 'narrator_bias': return 'secondary'
    default: return 'secondary'
  }
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'emotion_dialogue': 'Diálogo vs Emoción',
    'emotion_action': 'Acción vs Emoción',
    'temporal_jump': 'Cambio brusco',
    'narrator_bias': 'Sesgo del narrador',
  }
  return labels[type] || type
}
</script>

<style scoped>
.emotional-tab {
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

.header-left .analysis-status {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
}

.header-left .analysis-status.success {
  color: var(--green-500);
}

.header-left .analysis-status.error {
  color: var(--red-500);
}

.header-left .analysis-status.pending {
  color: var(--text-color-secondary);
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

/* Success message */
.success-message {
  margin: 0;
}

.success-message i {
  margin-right: var(--ds-space-2);
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

/* Characters accordion */
.characters-accordion {
  flex: 1;
}

.character-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: var(--ds-space-3);
}

.character-name {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-weight: var(--ds-font-weight-semibold);
}

/* Incoherences list */
.incoherences-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.incoherence-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--p-orange-400);
}

.incoherence-item.type-emotion_dialogue {
  border-left-color: var(--p-yellow-500);
}

.incoherence-item.type-emotion_action {
  border-left-color: var(--p-blue-500);
}

.incoherence-item.type-temporal_jump {
  border-left-color: var(--p-red-500);
}

.inc-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-2);
}

.inc-confidence {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.inc-chapter {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-left: auto;
}

.inc-explanation {
  margin: 0 0 var(--ds-space-2);
  font-weight: var(--ds-font-weight-medium);
}

.inc-details {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
  margin-bottom: var(--ds-space-2);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
}

.detail-label {
  color: var(--ds-color-text-secondary);
}

.detail-value {
  color: var(--ds-color-text-primary);
}

.inc-excerpt {
  padding: var(--ds-space-2);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-sm);
  margin-bottom: var(--ds-space-2);
}

.excerpt-block {
  margin-bottom: var(--ds-space-1);
}

.excerpt-block:last-child {
  margin-bottom: 0;
}

.excerpt-label {
  color: var(--ds-color-text-tertiary);
  display: block;
}

.excerpt-text {
  color: var(--ds-color-text-secondary);
  font-style: italic;
}

.inc-suggestion {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--p-green-50);
  border-radius: var(--ds-radius-sm);
  color: var(--p-green-700);
}

.inc-suggestion i {
  color: var(--p-green-500);
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

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
