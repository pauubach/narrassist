<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import { useAppStore } from '@/stores/app'
import { useSystemStore } from '@/stores/system'
import ProgressBar from 'primevue/progressbar'
import Button from 'primevue/button'

/**
 * StatusBar - Barra de estado inferior con progreso de análisis
 *
 * Muestra información del proyecto actual y progreso de análisis en tiempo real.
 * El análisis es NO BLOQUEANTE - el usuario puede trabajar mientras se analiza.
 */

interface Props {
  /** Número de palabras del documento */
  wordCount?: number
  /** Número de capítulos */
  chapterCount?: number
  /** Número de entidades detectadas */
  entityCount?: number
  /** Número de alertas activas */
  alertCount?: number
  /** Si hay un análisis completado */
  hasAnalysis?: boolean
  /** Si el análisis terminó con error */
  analysisError?: boolean
  /** Timestamp del último análisis */
  lastAnalysisTime?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  wordCount: 0,
  chapterCount: 0,
  entityCount: 0,
  alertCount: 0,
  hasAnalysis: false,
  analysisError: false,
  lastAnalysisTime: null
})

const analysisStore = useAnalysisStore()
const appStore = useAppStore()
const systemStore = useSystemStore()

// Versión de la aplicación (desde el backend, con fallback entre stores)
// systemStore se inicializa via waitForBackend() en ModelSetupDialog al arrancar
// appStore se inicializa via checkBackendHealth() en HomeView
const appVersion = computed(() =>
  appStore.backendVersion
  || (systemStore.backendVersion !== 'unknown' ? systemStore.backendVersion : null)
  || 'sin conexión'
)

// Si aún no tenemos versión, lanzar health check
onMounted(async () => {
  if (!appStore.backendVersion) {
    await appStore.checkBackendHealth()
  }
})

// Estado local para expandir/colapsar detalles
const showDetails = ref(false)

// Definición de todas las fases del análisis con sus rangos de progreso
interface PhaseDefinition {
  id: string
  name: string
  range: [number, number]
}

// Rangos ajustados según tiempos reales de procesamiento:
// - Loading/chapters: muy rápido (~5%)
// - NER: proceso pesado con spaCy (~25% del tiempo)
// - Correferencias: más lento, usa LLM/embeddings (~35% del tiempo)
// - Atributos: moderado (~15%)
// - Inconsistencias: moderado (~15%)
// - Clustering: rápido (~5%)
const allPhases: PhaseDefinition[] = [
  { id: 'loading', name: 'Cargando documento', range: [0, 3] },
  { id: 'chapters', name: 'Detectando capítulos', range: [3, 5] },
  { id: 'ner', name: 'Extrayendo entidades (NLP)', range: [5, 30] },
  { id: 'coreference', name: 'Resolviendo correferencias', range: [30, 65] },
  { id: 'attributes', name: 'Analizando atributos', range: [65, 80] },
  { id: 'inconsistencies', name: 'Detectando inconsistencias', range: [80, 95] },
  { id: 'clustering', name: 'Agrupando relaciones', range: [95, 100] },
]

// Computed - usando propiedades reales del store
const isAnalyzing = computed(() => analysisStore.isAnalyzing)
const progress = computed(() => analysisStore.currentAnalysis?.progress ?? 0)
const currentStep = computed(() => analysisStore.currentAnalysis?.current_phase ?? '')
const currentAction = computed(() => analysisStore.currentAnalysis?.current_action ?? '')

// Si hay análisis completado pero no hay currentAnalysis (recargó la página después del análisis)
const isCompletedWithoutDetails = computed(() => {
  return props.hasAnalysis && !analysisStore.currentAnalysis && !analysisStore.isAnalyzing
})

// Calcular el estado de cada fase basado en el progreso actual
const steps = computed(() => {
  const currentProgress = progress.value
  const backendPhases = analysisStore.currentAnalysis?.phases ?? []

  // Si hay fases del backend, usarlas
  if (backendPhases.length > 0) {
    return backendPhases.map(phase => ({
      id: phase.id,
      name: phase.name,
      status: phase.completed ? 'completed' : phase.current ? 'in_progress' : 'pending',
      duration: phase.duration,
      progress: phase.current ? calculatePhaseProgress(phase.id, currentProgress) : (phase.completed ? 100 : 0)
    }))
  }

  // Si es un análisis completado sin detalles (recargó la página), mostrar todas las fases como completadas
  if (isCompletedWithoutDetails.value) {
    return allPhases.map(phase => ({
      id: phase.id,
      name: phase.name,
      status: 'completed' as const,
      progress: 100,
      duration: undefined as number | undefined
    }))
  }

  // Si no hay fases del backend, calcular basado en el progreso
  return allPhases.map(phase => {
    const [start, end] = phase.range
    let status: 'completed' | 'in_progress' | 'pending'
    let phaseProgress = 0

    if (currentProgress >= end) {
      status = 'completed'
      phaseProgress = 100
    } else if (currentProgress >= start) {
      status = 'in_progress'
      phaseProgress = Math.round(((currentProgress - start) / (end - start)) * 100)
    } else {
      status = 'pending'
      phaseProgress = 0
    }

    return {
      id: phase.id,
      name: phase.name,
      status,
      progress: phaseProgress,
      duration: undefined as number | undefined
    }
  })
})

// Calcular progreso dentro de una fase específica
function calculatePhaseProgress(phaseId: string, totalProgress: number): number {
  const phase = allPhases.find(p => p.id === phaseId)
  if (!phase) return 0
  const [start, end] = phase.range
  if (totalProgress < start) return 0
  if (totalProgress >= end) return 100
  return Math.round(((totalProgress - start) / (end - start)) * 100)
}

// Mapeo de pasos a textos legibles (para compatibilidad)
const stepLabels: Record<string, string> = {
  'loading': 'Cargando documento',
  'chapters': 'Detectando capítulos',
  'ner': 'Extrayendo entidades',
  'coreference': 'Resolviendo correferencias',
  'attributes': 'Analizando atributos',
  'inconsistencies': 'Detectando inconsistencias',
  'clustering': 'Agrupando relaciones',
  'complete': 'Análisis completado'
}

const currentStepLabel = computed(() => {
  return stepLabels[currentStep.value] || currentStep.value || 'Procesando...'
})

// Estado del análisis cuando no está analizando
const analysisStatus = computed(() => {
  if (isAnalyzing.value) return null

  // Si hay error (del store o del prop)
  if (analysisStore.error || props.analysisError) {
    const detail = analysisStore.error
      ? `Error en análisis: ${analysisStore.error}`
      : 'Error en análisis'
    return { icon: 'pi-times-circle', text: detail, class: 'status-error' }
  }

  // Si hay análisis completado
  if (props.hasAnalysis) {
    return { icon: 'pi-check-circle', text: 'Análisis completado', class: 'status-completed' }
  }

  // Sin análisis
  return { icon: 'pi-circle', text: 'Sin analizar', class: 'status-pending' }
})

// Si hay un análisis completado con información para mostrar
const hasCompletedAnalysis = computed(() => {
  return props.hasAnalysis || analysisStore.currentAnalysis?.status === 'completed'
})

// Formato de números
function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

function toggleDetails() {
  showDetails.value = !showDetails.value
}
</script>

<template>
  <div class="status-bar">
    <!-- Sección izquierda: Estadísticas del documento -->
    <div class="status-section status-stats">
      <span v-if="wordCount > 0" class="stat-item">
        <i class="pi pi-file-edit"></i>
        {{ formatNumber(wordCount) }} palabras
      </span>
      <span v-if="chapterCount > 0" class="stat-item">
        <i class="pi pi-book"></i>
        {{ chapterCount }} capítulos
      </span>
      <span v-if="entityCount > 0" class="stat-item">
        <i class="pi pi-th-large"></i>
        {{ entityCount }} entidades
      </span>
      <span v-if="alertCount > 0" class="stat-item stat-alerts">
        <i class="pi pi-exclamation-triangle"></i>
        {{ alertCount }} alertas
      </span>
    </div>

    <!-- Sección central: Estado/Progreso de análisis -->
    <!-- Estado cuando NO está analizando -->
    <div v-if="!isAnalyzing && analysisStatus" class="status-section status-analysis-state" :class="analysisStatus.class" @click="toggleDetails">
      <i :class="['pi', analysisStatus.icon]"></i>
      <span>{{ analysisStatus.text }}</span>
      <Button
        v-if="hasCompletedAnalysis"
        :icon="showDetails ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"
        text
        rounded
        size="small"
        class="expand-btn"
        @click.stop="toggleDetails"
      />
    </div>

    <!-- Progreso cuando SÍ está analizando -->
    <div v-if="isAnalyzing" class="status-section status-progress" @click="toggleDetails">
      <span class="progress-step">{{ currentStepLabel }}</span>
      <ProgressBar
        :value="progress"
        :show-value="false"
        class="progress-bar"
      />
      <span class="progress-percent">{{ progress }}%</span>
      <Button
        :icon="showDetails ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"
        text
        rounded
        size="small"
        class="expand-btn"
        @click.stop="toggleDetails"
      />
    </div>

    <!-- Sección derecha: Versión/info -->
    <div class="status-section status-info">
      <span class="version">Narrative Assistant v{{ appVersion }}</span>
    </div>

    <!-- Panel de detalles expandido -->
    <Transition name="slide-up">
      <div v-if="showDetails && (isAnalyzing || hasCompletedAnalysis)" class="details-panel">
        <div class="details-header">
          <h4>{{ isAnalyzing ? 'Progreso del Análisis' : 'Resumen del Análisis' }}</h4>
          <Button
            icon="pi pi-times"
            text
            rounded
            size="small"
            @click="showDetails = false"
          />
        </div>

        <!-- Acción actual con indicador de actividad -->
        <div v-if="currentAction" class="current-action">
          <span class="activity-indicator"></span>
          <span class="action-text">{{ currentAction }}</span>
        </div>

        <div class="details-steps">
          <div
            v-for="step in steps"
            :key="step.id"
            class="step-item"
            :class="{
              'step-completed': step.status === 'completed',
              'step-active': step.status === 'in_progress',
              'step-pending': step.status === 'pending'
            }"
          >
            <span class="step-icon">
              <i v-if="step.status === 'completed'" class="pi pi-check-circle"></i>
              <i v-else-if="step.status === 'in_progress'" class="pi pi-spin pi-spinner"></i>
              <i v-else class="pi pi-circle"></i>
            </span>
            <div class="step-content">
              <div class="step-header">
                <span class="step-name">{{ step.name }}</span>
                <span v-if="step.status === 'in_progress'" class="step-percent">{{ step.progress }}%</span>
                <span v-if="step.duration" class="step-duration">{{ step.duration }}s</span>
              </div>
              <!-- Mini barra de progreso para la fase activa -->
              <div v-if="step.status === 'in_progress'" class="step-progress-bar">
                <div class="step-progress-fill" :style="{ width: `${step.progress}%` }"></div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="isAnalyzing" class="details-note">
          <span class="activity-dot"></span>
          El análisis continúa en segundo plano. Puedes seguir trabajando.
        </p>
        <p v-else class="details-note details-note-completed">
          <i class="pi pi-check-circle"></i>
          Análisis completado correctamente.
        </p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.status-bar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  padding: 0.25rem 1rem;
  background: var(--surface-100);
  border-top: 1px solid var(--surface-border);
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  user-select: none;
  /* overflow: hidden removed - was clipping the details panel */
}

.status-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.stat-item i {
  font-size: 0.75rem;
  opacity: 0.7;
}

.stat-alerts {
  color: var(--orange-500);
}

/* Analysis state (when not analyzing) */
.status-analysis-state {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: filter 0.2s;
}

.status-analysis-state:hover {
  filter: brightness(0.95);
}

.status-analysis-state i {
  font-size: 0.75rem;
}

.status-completed {
  color: var(--green-600);
  background: var(--green-50);
}

.status-completed i {
  color: var(--green-500);
}

.status-error {
  color: var(--red-600);
  background: var(--red-50);
}

.status-error i {
  color: var(--red-500);
}

.status-pending {
  color: var(--text-color-secondary);
  opacity: 0.7;
}

/* Progress section */
.status-progress {
  flex: 0 1 auto;
  min-width: 250px;
  max-width: 400px;
  cursor: pointer;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-progress:hover {
  background: var(--surface-200);
}

.progress-step {
  font-size: 0.6875rem;
  color: var(--primary-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
  flex-shrink: 1;
  min-width: 0;
}

.progress-bar {
  flex: 1;
  min-width: 60px;
  max-width: 120px;
  height: 4px;
}

.progress-percent {
  font-size: 0.6875rem;
  font-weight: 600;
  flex-shrink: 0;
  min-width: 28px;
  text-align: right;
}

.progress-bar :deep(.p-progressbar-value) {
  background: var(--primary-color);
}

.expand-btn {
  width: 1.25rem;
  height: 1.25rem;
  margin-left: 0.5rem;
}

/* Info section */
.status-info {
  font-size: 0.75rem;
  opacity: 0.7;
}

/* Details panel */
.details-panel {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 380px;
  background-color: var(--p-surface-ground, var(--surface-ground, #ffffff));
  border: 1px solid var(--p-surface-border, var(--surface-border, #e2e8f0));
  border-radius: 8px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.12);
  padding: 1rem;
  margin-bottom: 0.5rem;
  z-index: 1000;
  color: var(--p-text-color, var(--text-color, #1e293b));
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.details-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-color);
}

.details-steps {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.8125rem;
}

.step-icon {
  width: 1.25rem;
  text-align: center;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.step-name {
  flex: 1;
}

.step-percent {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-primary-color, #2563eb);
}

.step-duration {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.step-progress-bar {
  height: 4px;
  margin-top: 0.35rem;
  background: var(--p-surface-300, #e2e8f0);
  border-radius: 2px;
  overflow: hidden;
}

.step-progress-fill {
  height: 100%;
  background: var(--p-primary-500, #3b82f6);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Current action indicator */
.current-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--p-primary-50, rgba(59, 130, 246, 0.1));
  border: 1px solid var(--p-primary-200, rgba(59, 130, 246, 0.3));
  border-radius: 6px;
  font-size: 0.8125rem;
  color: var(--p-primary-700, #1d4ed8);
}

.activity-indicator {
  width: 8px;
  height: 8px;
  background: var(--primary-500);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.activity-dot {
  width: 8px;
  height: 8px;
  background: var(--p-green-500, #16a34a);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

.action-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-completed {
  color: var(--p-green-600, #16a34a);
}

.step-completed .step-icon i {
  color: var(--p-green-500, #22c55e);
}

.step-active {
  background: var(--p-primary-50, rgba(59, 130, 246, 0.08));
  color: var(--p-primary-700, #1d4ed8);
  border-left: 3px solid var(--p-primary-500, #3b82f6);
  border-radius: 6px;
  padding-left: calc(0.5rem + 3px);
}

.step-active .step-icon i {
  color: var(--p-primary-500, #3b82f6);
}

.step-active .step-name {
  font-weight: 600;
  color: var(--p-primary-700, #1d4ed8);
}

.step-pending {
  color: var(--p-text-muted-color, #64748b);
  opacity: 0.7;
}

.step-pending .step-icon i {
  color: var(--p-text-muted-color, #9ca3af);
}

.details-note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 1rem 0 0 0;
  padding: 0.75rem;
  background-color: var(--p-green-50, rgba(34, 197, 94, 0.08));
  border: 1px solid var(--p-green-300, #86efac);
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-green-700, #15803d);
}

/* Transitions */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

/* Dark mode */
.dark .status-bar {
  background: var(--surface-800);
}

.dark .status-progress:hover {
  background: var(--surface-700);
}

.dark .details-panel {
  background-color: var(--p-surface-800, #1e293b);
  border-color: var(--p-surface-600, #475569);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.4);
  color: var(--p-text-color, #e4e4e7);
}

/* Dark mode: Asegurar texto legible en details-panel */
.dark .details-header h4 {
  color: var(--p-surface-100, #f1f5f9);
}

.dark .step-item {
  color: var(--p-surface-200, #e2e8f0);
}

.dark .step-name {
  color: var(--p-surface-200, #e2e8f0);
}

.dark .step-duration {
  color: var(--p-surface-400, #94a3b8);
}

.dark .step-completed {
  color: var(--green-400, #4ade80);
}

.dark .step-completed .step-icon i {
  color: var(--green-400, #4ade80);
}

.dark .step-pending {
  color: var(--p-surface-500, #64748b);
  opacity: 0.8;
}

.dark .step-pending .step-icon i {
  color: var(--p-surface-500, #64748b);
}

.dark .current-action {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(96, 165, 250, 0.4);
  color: var(--primary-300, #93c5fd);
}

.dark .step-progress-bar {
  background: var(--p-surface-600, #475569);
}

.dark .step-percent {
  color: var(--primary-300, #93c5fd);
}

.dark .step-active {
  background: rgba(59, 130, 246, 0.15);
  color: var(--primary-300, #93c5fd);
}

.dark .step-active .step-icon i {
  color: var(--primary-400, #60a5fa);
}

.dark .step-active .step-name {
  color: var(--primary-200, #bfdbfe);
}

.dark .details-note {
  background: rgba(34, 197, 94, 0.12);
  border-color: var(--green-700, #15803d);
  color: var(--green-300, #86efac);
}

.details-note-completed {
  background: var(--p-green-100, #dcfce7);
  border-color: var(--p-green-500, #22c55e);
}

.details-note-completed i {
  color: var(--p-green-600, #16a34a);
}

/* Dark mode adjustments */
.dark .details-note-completed {
  background: rgba(34, 197, 94, 0.2);
  border-color: var(--p-green-500, #22c55e);
  color: var(--p-green-300, #86efac);
}

.dark .status-completed {
  background: rgba(34, 197, 94, 0.15);
}

.dark .status-error {
  background: rgba(239, 68, 68, 0.15);
}

/* ============================================================
   SCRIVENER/WARM THEME ADJUSTMENTS
   El tema Scrivener tiene fondo sepia que requiere ajustes
   ============================================================ */

/* Detectar tema cálido por el color de fondo del panel */
.details-panel {
  /* Usar colores con buen contraste universal */
  color: var(--p-text-color, #1e293b);
}

.details-header h4 {
  color: var(--p-text-color, #1e293b);
}

.step-item {
  color: var(--p-text-color, #374151);
}

/* Activity dot - verde sólido visible en cualquier fondo */
.activity-dot {
  width: 8px;
  height: 8px;
  background: var(--p-green-500, #22c55e);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.3);
}

/* Note info - los estilos principales ya tienen buen contraste */

/* Mejorar visibilidad de iconos pending */
.step-pending .step-icon i {
  font-size: 0.875rem;
}
</style>
