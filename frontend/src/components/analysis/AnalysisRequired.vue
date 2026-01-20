<script setup lang="ts">
/**
 * AnalysisRequired - Overlay para tabs que requieren análisis no ejecutado.
 *
 * Muestra un mensaje indicando que el análisis no se ha ejecutado,
 * con opción de ejecutarlo incluyendo sus dependencias si las hay.
 */
import { computed } from 'vue'
import Button from 'primevue/button'
import { useAnalysisStore, PHASE_LABELS, type ExecutedPhases } from '@/stores/analysis'

const props = defineProps<{
  /** ID del proyecto */
  projectId: number
  /** Fase requerida para mostrar el contenido */
  requiredPhase: keyof ExecutedPhases
  /** Texto descriptivo de qué se verá cuando se ejecute */
  description?: string
}>()

const emit = defineEmits<{
  /** Emitido cuando el análisis se completa exitosamente */
  (e: 'analysis-completed'): void
}>()

const analysisStore = useAnalysisStore()

// Computeds
const isExecuted = computed(() =>
  analysisStore.isPhaseExecuted(props.projectId, props.requiredPhase)
)

// Verificar si esta fase está corriendo O si hay análisis global en progreso para este proyecto
const isRunning = computed(() => {
  // Si esta fase específica está corriendo
  if (analysisStore.isPhaseRunning(props.requiredPhase)) {
    return true
  }
  // Si hay un análisis global en curso para este proyecto
  if (analysisStore.isAnalyzing && analysisStore.currentAnalysis?.project_id === props.projectId) {
    return true
  }
  return false
})

const missingDependencies = computed(() =>
  analysisStore.getMissingDependencies(props.projectId, props.requiredPhase)
)

const hasMissingDependencies = computed(() => missingDependencies.value.length > 0)

const phaseLabel = computed(() => PHASE_LABELS[props.requiredPhase])

const dependencyLabels = computed(() =>
  missingDependencies.value.map(dep => PHASE_LABELS[dep])
)

// Calcula todas las fases a ejecutar (incluyendo dependencias)
const phasesToRun = computed(() => {
  const phases: (keyof ExecutedPhases)[] = [...missingDependencies.value, props.requiredPhase]
  // Eliminar duplicados manteniendo orden
  return [...new Set(phases)]
})

const runButtonLabel = computed(() => {
  if (hasMissingDependencies.value) {
    return `Ejecutar ${phasesToRun.value.length} análisis`
  }
  return `Ejecutar ${phaseLabel.value}`
})

// Actions
async function runAnalysis() {
  const success = await analysisStore.runPartialAnalysis(
    props.projectId,
    phasesToRun.value,
    false
  )
  if (success) {
    emit('analysis-completed')
  }
}
</script>

<template>
  <div class="analysis-required" :class="{ 'is-executed': isExecuted }">
    <!-- Overlay cuando no está ejecutado -->
    <Transition name="fade">
      <div v-if="!isExecuted && !isRunning" class="not-executed-overlay">
        <div class="not-executed-content">
          <div class="icon-container">
            <i class="pi pi-chart-bar" />
          </div>

          <h3 class="title">Análisis no ejecutado</h3>

          <p class="description">
            {{ description || `El análisis de "${phaseLabel}" no se ha ejecutado aún.` }}
          </p>

          <!-- Dependencias faltantes -->
          <div v-if="hasMissingDependencies" class="dependencies">
            <p class="dependencies-label">
              <i class="pi pi-info-circle" />
              Requiere ejecutar primero:
            </p>
            <ul class="dependencies-list">
              <li v-for="dep in dependencyLabels" :key="dep">
                {{ dep }}
              </li>
            </ul>
          </div>

          <Button
            :label="runButtonLabel"
            icon="pi pi-play"
            @click="runAnalysis"
            class="run-button"
          />
        </div>
      </div>
    </Transition>

    <!-- Contenido real cuando está ejecutado -->
    <div v-if="isExecuted" class="content">
      <slot />
    </div>

    <!-- Loading overlay durante ejecución -->
    <Transition name="fade">
      <div v-if="isRunning" class="running-overlay">
        <i class="pi pi-spin pi-spinner" />
        <span>Ejecutando análisis...</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.analysis-required {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
}

.not-executed-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ds-surface-ground);
  z-index: 10;
}

.not-executed-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 400px;
  padding: var(--ds-space-6);
}

.icon-container {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ds-surface-card);
  border-radius: var(--ds-radius-full);
  margin-bottom: var(--ds-space-4);
}

.icon-container i {
  font-size: 2rem;
  color: var(--ds-color-text-secondary);
}

.title {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.description {
  margin: 0 0 var(--ds-space-4);
  color: var(--ds-color-text-secondary);
  line-height: 1.5;
}

.dependencies {
  width: 100%;
  padding: var(--ds-space-3);
  background: var(--ds-surface-card);
  border-radius: var(--ds-radius-md);
  margin-bottom: var(--ds-space-4);
  text-align: left;
}

.dependencies-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.dependencies-label i {
  color: var(--ds-color-info);
}

.dependencies-list {
  margin: 0;
  padding-left: var(--ds-space-4);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.dependencies-list li {
  margin-bottom: var(--ds-space-1);
}

.dependencies-list li:last-child {
  margin-bottom: 0;
}

.run-button {
  min-width: 180px;
}

.content {
  width: 100%;
  height: 100%;
}

.running-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  background: color-mix(in srgb, var(--ds-surface-ground, #f8fafc) 95%, transparent);
  z-index: 20;
}

/* Dark mode */
.dark .running-overlay {
  background: color-mix(in srgb, var(--ds-surface-ground, #0f172a) 95%, transparent);
}

.running-overlay i {
  font-size: 2rem;
  color: var(--ds-color-primary);
}

.running-overlay span {
  color: var(--ds-color-text-secondary);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--ds-transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
