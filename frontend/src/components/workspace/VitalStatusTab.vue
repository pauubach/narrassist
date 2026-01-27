<template>
  <div class="vital-status-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-heart"></i>
          Estado Vital de Personajes
        </h3>
        <p class="subtitle">
          Detecta muertes de personajes y verifica que no reaparezcan como vivos posteriormente.
        </p>
      </div>
      <div class="header-controls">
        <Button
          label="Analizar"
          icon="pi pi-refresh"
          :loading="loading"
          @click="analyze"
        />
        <Button
          v-if="report && report.inconsistencies_count > 0"
          label="Generar alertas"
          icon="pi pi-bell"
          severity="warning"
          :loading="generatingAlerts"
          @click="generateAlerts"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Analizando estado vital de personajes...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar muertes y reapariciones de personajes.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Stats Summary -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.death_events.length }}</div>
              <div class="stat-label">Muertes detectadas</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.post_mortem_appearances.length }}</div>
              <div class="stat-label">Apariciones post-mortem</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value text-danger">{{ report.inconsistencies_count }}</div>
              <div class="stat-label">Inconsistencias</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value text-success">{{ validAppearances }}</div>
              <div class="stat-label">Referencias válidas</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- No Deaths Message -->
      <Message v-if="report.death_events.length === 0" severity="info" :closable="false" class="info-message">
        <i class="pi pi-info-circle"></i>
        No se detectaron muertes de personajes en el manuscrito.
      </Message>

      <!-- Death Events -->
      <Card v-if="report.death_events.length > 0" class="deaths-card">
        <template #title>
          <i class="pi pi-times-circle"></i>
          Muertes Detectadas ({{ report.death_events.length }})
        </template>
        <template #content>
          <div class="events-list">
            <div
              v-for="(event, idx) in report.death_events"
              :key="idx"
              class="event-item death-event"
            >
              <div class="event-header">
                <Tag severity="danger">
                  <i class="pi pi-user"></i>
                  {{ event.entity_name }}
                </Tag>
                <Tag severity="secondary" size="small">Cap. {{ event.chapter }}</Tag>
                <Tag :severity="getDeathTypeSeverity(event.death_type)" size="small">
                  {{ getDeathTypeLabel(event.death_type) }}
                </Tag>
                <span class="confidence">{{ (event.confidence * 100).toFixed(0) }}% confianza</span>
              </div>
              <div class="event-excerpt">
                "{{ truncate(event.excerpt, 150) }}"
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Inconsistencies (Post-mortem errors) -->
      <Card v-if="inconsistencies.length > 0" class="inconsistencies-card">
        <template #title>
          <i class="pi pi-exclamation-triangle"></i>
          Inconsistencias ({{ inconsistencies.length }})
        </template>
        <template #content>
          <Message severity="warn" :closable="false" class="warning-message">
            Estos personajes aparecen actuando/hablando después de su muerte sin ser flashbacks o recuerdos.
          </Message>
          <div class="events-list">
            <div
              v-for="(app, idx) in inconsistencies"
              :key="idx"
              class="event-item inconsistency-event"
            >
              <div class="event-header">
                <Tag severity="danger">
                  <i class="pi pi-user"></i>
                  {{ app.entity_name }}
                </Tag>
                <div class="chapter-flow">
                  <Tag severity="secondary" size="small">Muere: Cap. {{ app.death_chapter }}</Tag>
                  <i class="pi pi-arrow-right"></i>
                  <Tag severity="warning" size="small">Aparece: Cap. {{ app.appearance_chapter }}</Tag>
                </div>
                <Tag :severity="getAppearanceTypeSeverity(app.appearance_type)" size="small">
                  {{ getAppearanceTypeLabel(app.appearance_type) }}
                </Tag>
              </div>
              <div class="event-excerpt">
                "{{ truncate(app.appearance_excerpt, 150) }}"
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Valid Post-mortem References -->
      <Card v-if="validReferences.length > 0" class="valid-refs-card">
        <template #title>
          <i class="pi pi-check-circle"></i>
          Referencias Válidas ({{ validReferences.length }})
        </template>
        <template #subtitle>
          Flashbacks, recuerdos o menciones que no son inconsistencias
        </template>
        <template #content>
          <Accordion :multiple="true" class="refs-accordion">
            <AccordionPanel v-for="(app, idx) in validReferences" :key="idx" :value="String(idx)">
              <AccordionHeader>
                <div class="ref-header">
                  <Tag severity="success" size="small">
                    <i class="pi pi-user"></i>
                    {{ app.entity_name }}
                  </Tag>
                  <span class="chapter-info">Cap. {{ app.appearance_chapter }}</span>
                  <Tag severity="secondary" size="small">{{ getAppearanceTypeLabel(app.appearance_type) }}</Tag>
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="ref-detail">
                  <p class="ref-excerpt">"{{ app.appearance_excerpt }}"</p>
                  <small class="ref-meta">
                    Personaje fallecido en capítulo {{ app.death_chapter }}
                  </small>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
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
import Message from 'primevue/message'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'

interface DeathEvent {
  entity_id: number
  entity_name: string
  chapter: number
  start_char: number
  end_char: number
  excerpt: string
  death_type: string  // "direct", "narrated", "reported", "implied"
  confidence: number
}

interface PostMortemAppearance {
  entity_id: number
  entity_name: string
  death_chapter: number
  appearance_chapter: number
  appearance_start_char: number
  appearance_end_char: number
  appearance_excerpt: string
  appearance_type: string  // "dialogue", "action", "narration"
  is_valid: boolean
  confidence: number
}

interface VitalStatusReport {
  project_id: number
  death_events: DeathEvent[]
  post_mortem_appearances: PostMortemAppearance[]
  inconsistencies_count: number
  entities_status: Record<number, string>
}

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const generatingAlerts = ref(false)
const report = ref<VitalStatusReport | null>(null)

// Computed
const inconsistencies = computed(() => {
  if (!report.value) return []
  return report.value.post_mortem_appearances.filter(a => !a.is_valid)
})

const validReferences = computed(() => {
  if (!report.value) return []
  return report.value.post_mortem_appearances.filter(a => a.is_valid)
})

const validAppearances = computed(() => {
  return validReferences.value.length
})

// Analyze
async function analyze() {
  loading.value = true
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/vital-status`
    )
    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error: any) {
    console.error('Error analyzing vital status:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudo analizar el estado vital',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Generate alerts
async function generateAlerts() {
  generatingAlerts.value = true
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/vital-status/generate-alerts`,
      { method: 'POST' }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Alertas generadas',
        detail: `Se crearon ${data.data.alerts_created} alertas`,
        life: 3000
      })
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    console.error('Error generating alerts:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudieron generar las alertas',
      life: 3000
    })
  } finally {
    generatingAlerts.value = false
  }
}

// Helper functions
function truncate(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function getDeathTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    direct: 'Muerte directa',
    narrated: 'Narrado',
    reported: 'Reportado',
    implied: 'Implícito',
    caused: 'Asesinato',
  }
  return labels[type] || type
}

function getDeathTypeSeverity(type: string): string {
  const severities: Record<string, string> = {
    direct: 'danger',
    narrated: 'info',
    reported: 'secondary',
    implied: 'warning',
    caused: 'danger',
  }
  return severities[type] || 'secondary'
}

function getAppearanceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    dialogue: 'Diálogo',
    action: 'Acción',
    narration: 'Narración',
    mention: 'Mención',
  }
  return labels[type] || type
}

function getAppearanceTypeSeverity(type: string): string {
  const severities: Record<string, string> = {
    dialogue: 'danger',
    action: 'danger',
    narration: 'warning',
    mention: 'secondary',
  }
  return severities[type] || 'secondary'
}

// Lifecycle
onMounted(() => {
  analyze()
})

watch(() => props.projectId, () => {
  analyze()
})
</script>

<style scoped>
.vital-status-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-4);
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

.header-controls {
  display: flex;
  gap: var(--ds-space-2);
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

.text-danger { color: var(--p-red-500); }
.text-success { color: var(--p-green-500); }

/* Cards */
.deaths-card :deep(.p-card-title),
.inconsistencies-card :deep(.p-card-title),
.valid-refs-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.deaths-card :deep(.p-card-title) i { color: var(--p-red-500); }
.inconsistencies-card :deep(.p-card-title) i { color: var(--p-yellow-600); }
.valid-refs-card :deep(.p-card-title) i { color: var(--p-green-500); }

.valid-refs-card :deep(.p-card-subtitle) {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Events list */
.events-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.event-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-secondary);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid;
}

.death-event {
  border-left-color: var(--p-red-500);
}

.inconsistency-event {
  border-left-color: var(--p-yellow-500);
}

.event-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-2);
}

.chapter-flow {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.chapter-flow i {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary);
}

.confidence {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-left: auto;
}

.event-excerpt {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  font-style: italic;
  line-height: 1.5;
}

/* Valid references accordion */
.refs-accordion {
  margin-top: var(--ds-space-3);
}

.ref-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  width: 100%;
}

.chapter-info {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.ref-detail {
  padding: var(--ds-space-2);
}

.ref-excerpt {
  font-size: var(--ds-font-size-sm);
  font-style: italic;
  color: var(--ds-color-text-secondary);
  margin: 0 0 var(--ds-space-2);
}

.ref-meta {
  color: var(--ds-color-text-tertiary);
}

/* Messages */
.info-message,
.warning-message {
  margin-bottom: var(--ds-space-3);
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

  .event-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .confidence {
    margin-left: 0;
  }
}
</style>
