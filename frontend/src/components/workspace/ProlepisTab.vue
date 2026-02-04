<template>
  <div class="prolepsis-tab">
    <!-- Header con controles -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-clock"></i>
          Estructura Narrativa
        </h3>
        <p class="subtitle">
          Detecta prolepsis (anticipaciones) y analepsis (flashbacks) en el manuscrito.
        </p>
      </div>
      <div class="header-controls">
        <div class="confidence-control">
          <label>Confianza min:</label>
          <InputNumber
            v-model="minConfidence"
            :min="0.3"
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
      <p>Analizando estructura narrativa...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para detectar anomalias narrativas.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Global Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.total_anomalies }}</div>
              <div class="stat-label">Anomalias</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value severity-prolepsis">
                {{ report.global_stats.prolepsis_count }}
              </div>
              <div class="stat-label">Prolepsis</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value severity-analepsis">
                {{ report.global_stats.analepsis_count }}
              </div>
              <div class="stat-label">Analepsis</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.global_stats.chapters_analyzed }}</div>
              <div class="stat-label">Capitulos</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- No anomalies message -->
      <Message v-if="report.global_stats.total_anomalies === 0" severity="success" :closable="false">
        No se encontraron anomalias narrativas en el manuscrito.
      </Message>

      <!-- Prolepsis List -->
      <div v-if="report.prolepsis.length > 0" class="anomalies-section">
        <h4>
          <i class="pi pi-forward"></i>
          Prolepsis detectadas
        </h4>
        <div class="anomalies-list">
          <Card
            v-for="(p, idx) in report.prolepsis"
            :key="'prolepsis-' + idx"
            class="anomaly-card"
            :class="'severity-border-' + p.severity"
          >
            <template #header>
              <div class="anomaly-header">
                <div class="anomaly-tags">
                  <Tag :severity="getSeverityColor(p.severity)" :value="getSeverityLabel(p.severity)" />
                  <span class="confidence-badge">
                    {{ Math.round(p.confidence * 100) }}% confianza
                  </span>
                </div>
                <div class="anomaly-chapter">
                  Cap. {{ p.location.chapter }}
                  <span v-if="p.resolved_event_chapter" class="resolved-ref">
                    <i class="pi pi-arrow-right"></i>
                    Cap. {{ p.resolved_event_chapter }}
                  </span>
                </div>
              </div>
            </template>

            <template #content>
              <div class="anomaly-content">
                <!-- Description -->
                <div class="anomaly-description">
                  {{ p.description }}
                </div>

                <!-- Text quote -->
                <div class="text-quote">
                  <i class="pi pi-comment"></i>
                  <blockquote>{{ p.location.text }}</blockquote>
                </div>

                <!-- Evidence -->
                <div v-if="p.evidence && p.evidence.length > 0" class="evidence-list">
                  <span class="evidence-label">Evidencia:</span>
                  <ul>
                    <li v-for="(ev, evIdx) in p.evidence" :key="evIdx">{{ ev }}</li>
                  </ul>
                </div>

                <!-- Resolved event -->
                <div v-if="p.resolved_event_text" class="resolved-event">
                  <span class="resolved-label">
                    <i class="pi pi-check-circle"></i>
                    Evento encontrado en cap. {{ p.resolved_event_chapter }}:
                  </span>
                  <blockquote>{{ p.resolved_event_text }}</blockquote>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>

      <!-- Analepsis List (if any) -->
      <div v-if="report.analepsis.length > 0" class="anomalies-section">
        <h4>
          <i class="pi pi-replay"></i>
          Analepsis detectadas
        </h4>
        <div class="anomalies-list">
          <Card
            v-for="(a, idx) in report.analepsis"
            :key="'analepsis-' + idx"
            class="anomaly-card"
          >
            <template #content>
              <div class="anomaly-content">
                <div class="anomaly-description">{{ a.description }}</div>
                <div class="text-quote">
                  <blockquote>{{ a.location.text }}</blockquote>
                </div>
              </div>
            </template>
          </Card>
        </div>
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
import { ref, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import InputNumber from 'primevue/inputnumber'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { apiUrl } from '@/config/api'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const minConfidence = ref(0.7)
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
    const params = new URLSearchParams({
      min_confidence: minConfidence.value.toString(),
    })
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/narrative-structure?${params}`)
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing narrative structure:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar la estructura narrativa',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'high': return 'danger'
    case 'medium': return 'warn'
    case 'low': return 'secondary'
    default: return 'info'
  }
}

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case 'high': return 'Alta'
    case 'medium': return 'Media'
    case 'low': return 'Baja'
    default: return severity
  }
}
</script>

<style scoped>
.prolepsis-tab {
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

.confidence-control {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.confidence-control label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.confidence-control :deep(.p-inputnumber) {
  width: 80px;
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
.severity-prolepsis { color: #7c3aed; }  /* violet-600 */
.severity-analepsis { color: #0891b2; }  /* cyan-600 */

/* Anomalies section */
.anomalies-section {
  margin-top: var(--ds-space-4);
}

.anomalies-section h4 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0 0 var(--ds-space-3);
  font-size: var(--ds-font-size-base);
  color: var(--ds-color-text);
}

.anomalies-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.anomaly-card {
  border-left: 4px solid var(--ds-surface-border);
}

.anomaly-card.severity-border-high {
  border-left-color: #b91c1c;
}

.anomaly-card.severity-border-medium {
  border-left-color: #c2410c;
}

.anomaly-card.severity-border-low {
  border-left-color: #6b7280;
}

.anomaly-card :deep(.p-card-header) {
  padding: var(--ds-space-3);
  padding-bottom: 0;
}

.anomaly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.anomaly-tags {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.confidence-badge {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.anomaly-chapter {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.resolved-ref {
  color: var(--ds-color-success);
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.anomaly-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.anomaly-description {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.text-quote {
  display: flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
}

.text-quote i {
  color: var(--ds-color-text-tertiary);
  flex-shrink: 0;
}

.text-quote blockquote {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  font-style: italic;
  color: var(--ds-color-text-secondary);
  line-height: 1.6;
}

.evidence-list {
  font-size: var(--ds-font-size-sm);
}

.evidence-label {
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}

.evidence-list ul {
  margin: var(--ds-space-1) 0 0;
  padding-left: var(--ds-space-4);
}

.evidence-list li {
  color: var(--ds-color-text-secondary);
}

.resolved-event {
  padding: var(--ds-space-3);
  background: rgba(34, 197, 94, 0.1);
  border-radius: var(--ds-radius-md);
}

.resolved-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-success);
  margin-bottom: var(--ds-space-2);
}

.resolved-event blockquote {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  font-style: italic;
  color: var(--ds-color-text-secondary);
}

/* Recommendations card */
.recommendations-card {
  margin-top: var(--ds-space-4);
}

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
