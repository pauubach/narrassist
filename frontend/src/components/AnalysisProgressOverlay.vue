<template>
  <Dialog
    :visible="visible"
    modal
    :closable="true"
    :dismissableMask="true"
    :style="{ width: '600px' }"
    :draggable="false"
    header="Analizando manuscrito..."
    @hide="onHide"
  >
    <template #header>
      <div class="progress-header">
        <i class="pi pi-spin pi-spinner header-icon"></i>
        <h3>Analizando manuscrito...</h3>
      </div>
    </template>

    <div class="progress-content">
      <!-- Barra de progreso general -->
      <div class="overall-progress">
        <ProgressBar
          :value="overallProgress"
          :showValue="true"
        >
          <template #default>
            {{ Math.round(overallProgress) }}%
          </template>
        </ProgressBar>
      </div>

      <!-- Fase actual -->
      <div class="current-phase">
        <div class="phase-info">
          <strong>{{ currentPhaseMessage }}</strong>
          <span v-if="currentAction" class="phase-action">{{ currentAction }}</span>
        </div>
      </div>

      <!-- Métricas parciales -->
      <div v-if="hasMetrics" class="metrics-grid">
        <div v-if="metrics.chapters_found" class="metric-card">
          <i class="pi pi-book metric-icon"></i>
          <div class="metric-content">
            <span class="metric-value">{{ metrics.chapters_found }}</span>
            <span class="metric-label">Capítulos</span>
          </div>
        </div>

        <div v-if="metrics.entities_found" class="metric-card">
          <i class="pi pi-users metric-icon"></i>
          <div class="metric-content">
            <span class="metric-value">{{ metrics.entities_found }}</span>
            <span class="metric-label">Entidades</span>
          </div>
        </div>

        <div v-if="metrics.word_count" class="metric-card">
          <i class="pi pi-file metric-icon"></i>
          <div class="metric-content">
            <span class="metric-value">{{ metrics.word_count.toLocaleString() }}</span>
            <span class="metric-label">Palabras</span>
          </div>
        </div>

        <div v-if="metrics.alerts_generated" class="metric-card">
          <i class="pi pi-exclamation-triangle metric-icon"></i>
          <div class="metric-content">
            <span class="metric-value">{{ metrics.alerts_generated }}</span>
            <span class="metric-label">Alertas</span>
          </div>
        </div>
      </div>

      <!-- Fases completadas -->
      <div class="phases-list">
        <div
          v-for="phase in phases"
          :key="phase.id"
          class="phase-item"
          :class="{
            'phase-completed': phase.completed,
            'phase-current': phase.current,
            'phase-pending': !phase.completed && !phase.current
          }"
        >
          <i
            class="phase-icon"
            :class="{
              'pi pi-check-circle': phase.completed,
              'pi pi-spin pi-spinner': phase.current,
              'pi pi-circle': !phase.completed && !phase.current
            }"
          ></i>
          <span class="phase-name">{{ phase.name }}</span>
          <span v-if="phase.duration" class="phase-duration">{{ phase.duration }}s</span>
        </div>
      </div>

      <!-- Tiempo estimado -->
      <div v-if="estimatedTimeRemaining" class="estimated-time">
        <i class="pi pi-clock"></i>
        <span>Tiempo estimado restante: {{ estimatedTimeRemaining }}</span>
      </div>
    </div>

    <template #footer>
      <div class="progress-footer">
        <small class="footer-note">
          El análisis puede tardar varios minutos dependiendo del tamaño del manuscrito.
          <br />
          Puedes cerrar este diálogo y el análisis continuará en segundo plano.
        </small>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'

interface AnalysisPhase {
  id: string
  name: string
  completed: boolean
  current: boolean
  duration?: number
}

interface AnalysisMetrics {
  chapters_found?: number
  entities_found?: number
  word_count?: number
  alerts_generated?: number
}

const props = defineProps<{
  visible: boolean
  projectId?: number
}>()

const emit = defineEmits<{
  complete: [projectId: number]
  error: [error: string]
  close: []
}>()

// Manejador para cuando se cierra el diálogo manualmente
const onHide = () => {
  // El análisis continúa en segundo plano, solo ocultamos el overlay
  emit('close')
}

// Estado del progreso
const overallProgress = ref(0)
const currentPhaseMessage = ref('Iniciando análisis...')
const currentAction = ref('')
const metrics = ref<AnalysisMetrics>({})
const estimatedTimeRemaining = ref('')

const phases = ref<AnalysisPhase[]>([
  { id: 'parsing', name: 'Extracción de texto', completed: false, current: false },
  { id: 'structure', name: 'Detección de estructura', completed: false, current: false },
  { id: 'ner', name: 'Reconocimiento de entidades', completed: false, current: false },
  { id: 'attributes', name: 'Extracción de atributos', completed: false, current: false },
  { id: 'consistency', name: 'Análisis de consistencia', completed: false, current: false },
  { id: 'alerts', name: 'Generación de alertas', completed: false, current: false }
])

const hasMetrics = computed(() => Object.keys(metrics.value).length > 0)

// Polling interval
let pollingInterval: number | null = null

// Función para obtener el progreso del backend
const fetchProgress = async () => {
  if (!props.projectId) return

  try {
    const response = await fetch(`/api/projects/${props.projectId}/analysis/progress`)

    if (!response.ok) {
      throw new Error('Error obteniendo progreso')
    }

    const data = await response.json()

    if (data.success) {
      updateProgress(data.data)

      // Si el análisis está completo
      if (data.data.progress >= 100 || data.data.status === 'completed') {
        stopPolling()
        emit('complete', props.projectId)
      }

      // Si hay error (backend usa 'error', no 'failed')
      if (data.data.status === 'error' || data.data.status === 'failed') {
        stopPolling()
        emit('error', data.data.error || 'Error durante el análisis')
      }
    }
  } catch (error) {
    console.error('Error fetching progress:', error)
    // No detenemos el polling, reintentaremos en el próximo ciclo
  }
}

// Actualizar estado del progreso
const updateProgress = (data: any) => {
  overallProgress.value = data.progress || 0
  currentPhaseMessage.value = data.current_phase || 'Procesando...'
  currentAction.value = data.current_action || ''

  // Actualizar métricas
  if (data.metrics) {
    metrics.value = data.metrics
  }

  // Actualizar fases
  if (data.phases) {
    phases.value.forEach((phase) => {
      const phaseData = data.phases.find((p: any) => p.id === phase.id)
      if (phaseData) {
        phase.completed = phaseData.completed
        phase.current = phaseData.current
        phase.duration = phaseData.duration
      }
    })
  }

  // Calcular tiempo estimado
  if (data.estimated_seconds_remaining) {
    const minutes = Math.floor(data.estimated_seconds_remaining / 60)
    const seconds = data.estimated_seconds_remaining % 60
    if (minutes > 0) {
      estimatedTimeRemaining.value = `${minutes}m ${seconds}s`
    } else {
      estimatedTimeRemaining.value = `${seconds}s`
    }
  }
}

// Iniciar polling
const startPolling = () => {
  if (pollingInterval) return

  // Primera consulta inmediata
  fetchProgress()

  // Polling cada 1 segundo
  pollingInterval = window.setInterval(() => {
    fetchProgress()
  }, 1000)
}

// Detener polling
const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// Watchers
watch(() => props.visible, (isVisible) => {
  if (isVisible && props.projectId) {
    startPolling()
  } else {
    stopPolling()
  }
})

// Lifecycle
onMounted(() => {
  if (props.visible && props.projectId) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.progress-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.progress-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.progress-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.overall-progress {
  margin-bottom: 0.5rem;
}

.current-phase {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

.phase-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.phase-info strong {
  font-size: 1rem;
  color: var(--text-primary);
}

.phase-action {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.metric-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.metric-content {
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.phases-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

.phase-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.phase-completed {
  background: rgba(34, 197, 94, 0.1);
}

.phase-current {
  background: rgba(59, 130, 246, 0.1);
  font-weight: 500;
}

.phase-pending {
  opacity: 0.6;
}

.phase-icon {
  font-size: 1.1rem;
}

.phase-completed .phase-icon {
  color: #22c55e;
}

.phase-current .phase-icon {
  color: #3b82f6;
}

.phase-pending .phase-icon {
  color: var(--text-secondary);
}

.phase-name {
  flex: 1;
}

.phase-duration {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.estimated-time {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.estimated-time i {
  font-size: 1rem;
}

.progress-footer {
  display: flex;
  justify-content: center;
  width: 100%;
}

.footer-note {
  color: var(--text-secondary);
  font-size: 0.8rem;
  text-align: center;
}
</style>
