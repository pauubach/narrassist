<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisProgress, AnalysisPhase } from '@/composables/useAnalysisStream'
import DsCard from '@/components/ds/DsCard.vue'

/**
 * AnalysisProgress - Overlay de progreso de análisis.
 *
 * Muestra el progreso del análisis con fases, barra de progreso
 * y tiempo estimado restante.
 */

const props = defineProps<{
  /** Datos de progreso del análisis */
  progress: AnalysisProgress | null
  /** Si mostrar como overlay modal */
  overlay?: boolean
  /** Si mostrar botón de cancelar */
  showCancel?: boolean
}>()

const emit = defineEmits<{
  cancel: []
}>()

const isRunning = computed(() => props.progress?.status === 'running')
const isComplete = computed(() => props.progress?.status === 'completed')
const isFailed = computed(() => props.progress?.status === 'failed')

const progressPercent = computed(() => props.progress?.progress ?? 0)

const phaseCounter = computed(() => {
  if (!props.progress?.phases.length) return null
  const completed = props.progress.phases.filter(p => p.completed).length
  const current = props.progress.phases.some(p => p.current) ? 1 : 0
  const active = completed + current
  return { active, total: props.progress.phases.length }
})

const statusIcon = computed(() => {
  if (isComplete.value) return 'pi pi-check-circle'
  if (isFailed.value) return 'pi pi-times-circle'
  return 'pi pi-spin pi-spinner'
})

const statusClass = computed(() => {
  if (isComplete.value) return 'analysis-progress--complete'
  if (isFailed.value) return 'analysis-progress--failed'
  return 'analysis-progress--running'
})

function formatTime(seconds?: number): string {
  if (!seconds) return ''
  if (seconds < 60) return `~${Math.round(seconds)}s restantes`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `~${minutes}m ${secs}s restantes`
}

function getPhaseIcon(phase: AnalysisPhase): string {
  if (phase.completed) return 'pi pi-check'
  if (phase.current) return 'pi pi-spin pi-spinner'
  return 'pi pi-circle'
}

function getPhaseClass(phase: AnalysisPhase): string {
  if (phase.completed) return 'phase--completed'
  if (phase.current) return 'phase--current'
  return 'phase--pending'
}
</script>

<template>
  <div
    v-if="progress"
    class="analysis-progress"
    :class="[statusClass, { 'analysis-progress--overlay': overlay }]"
  >
    <DsCard :variant="overlay ? 'elevated' : 'flat'" padding="lg">
      <!-- Header -->
      <div class="analysis-progress__header">
        <i :class="statusIcon" class="analysis-progress__status-icon" />
        <div class="analysis-progress__title">
          <h3>{{ progress.phase || 'Analizando documento...' }}</h3>
          <p v-if="progress.action">{{ progress.action }}</p>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="analysis-progress__bar-container">
        <div class="analysis-progress__bar">
          <div
            class="analysis-progress__bar-fill"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
        <div class="analysis-progress__bar-info">
          <span class="analysis-progress__percent">{{ progressPercent }}%</span>
          <span v-if="isRunning && phaseCounter" class="analysis-progress__phase-counter">
            Fase {{ phaseCounter.active }} de {{ phaseCounter.total }}
          </span>
          <span v-if="isRunning && progress.estimatedSecondsRemaining" class="analysis-progress__time">
            {{ formatTime(progress.estimatedSecondsRemaining) }}
          </span>
        </div>
      </div>

      <!-- Phases -->
      <div v-if="progress.phases.length > 0" class="analysis-progress__phases">
        <div
          v-for="phase in progress.phases"
          :key="phase.id"
          class="analysis-progress__phase"
          :class="getPhaseClass(phase)"
        >
          <i :class="getPhaseIcon(phase)" />
          <span>{{ phase.name }}</span>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="isFailed && progress.error" class="analysis-progress__error">
        <i class="pi pi-exclamation-triangle" />
        <p>{{ progress.error }}</p>
      </div>

      <!-- Stats on complete -->
      <div v-if="isComplete && progress.stats" class="analysis-progress__stats">
        <div v-if="progress.stats.entities" class="analysis-progress__stat">
          <span class="stat-value">{{ progress.stats.entities }}</span>
          <span class="stat-label">Entidades</span>
        </div>
        <div v-if="progress.stats.alerts" class="analysis-progress__stat">
          <span class="stat-value">{{ progress.stats.alerts }}</span>
          <span class="stat-label">Alertas</span>
        </div>
        <div v-if="progress.stats.chapters" class="analysis-progress__stat">
          <span class="stat-value">{{ progress.stats.chapters }}</span>
          <span class="stat-label">Capítulos</span>
        </div>
        <div v-if="progress.stats.corrections" class="analysis-progress__stat">
          <span class="stat-value stat-value--corrections">{{ progress.stats.corrections }}</span>
          <span class="stat-label">Sugerencias</span>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="showCancel && isRunning" class="analysis-progress__actions">
        <button
          type="button"
          class="analysis-progress__cancel-btn"
          @click="emit('cancel')"
        >
          <i class="pi pi-times" />
          Cancelar
        </button>
      </div>
    </DsCard>
  </div>
</template>

<style scoped>
.analysis-progress {
  width: 100%;
  max-width: 500px;
}

.analysis-progress--overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: var(--ds-z-modal);
}

.analysis-progress--overlay::before {
  content: '';
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: -1;
}

/* Header */
.analysis-progress__header {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
  margin-bottom: var(--ds-space-4);
}

.analysis-progress__status-icon {
  font-size: 1.5rem;
  color: var(--ds-color-primary);
}

.analysis-progress--complete .analysis-progress__status-icon {
  color: var(--ds-color-success);
}

.analysis-progress--failed .analysis-progress__status-icon {
  color: var(--ds-color-danger);
}

.analysis-progress__title {
  flex: 1;
}

.analysis-progress__title h3 {
  margin: 0;
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.analysis-progress__title p {
  margin: var(--ds-space-1) 0 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Progress bar */
.analysis-progress__bar-container {
  margin-bottom: var(--ds-space-4);
}

.analysis-progress__bar {
  height: 8px;
  background-color: var(--ds-surface-border);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.analysis-progress__bar-fill {
  height: 100%;
  background-color: var(--ds-color-primary);
  border-radius: var(--ds-radius-full);
  transition: width 0.3s ease;
}

.analysis-progress--complete .analysis-progress__bar-fill {
  background-color: var(--ds-color-success);
}

.analysis-progress--failed .analysis-progress__bar-fill {
  background-color: var(--ds-color-danger);
}

.analysis-progress__bar-info {
  display: flex;
  justify-content: space-between;
  margin-top: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
}

.analysis-progress__percent {
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.analysis-progress__phase-counter {
  color: var(--ds-color-text-secondary);
}

.analysis-progress__time {
  color: var(--ds-color-text-muted);
}

/* Phases */
.analysis-progress__phases {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background-color: var(--ds-surface-ground);
  border-radius: var(--ds-radius-md);
}

.analysis-progress__phase {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
}

.analysis-progress__phase i {
  width: 16px;
  text-align: center;
}

.phase--completed {
  color: var(--ds-color-success);
}

.phase--current {
  color: var(--ds-color-primary);
  font-weight: var(--ds-font-weight-medium);
}

.phase--pending {
  color: var(--ds-color-text-muted);
}

/* Error */
.analysis-progress__error {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  margin-top: var(--ds-space-4);
  background-color: color-mix(in srgb, var(--ds-color-danger) 10%, transparent);
  border-radius: var(--ds-radius-md);
  color: var(--ds-color-danger);
}

.analysis-progress__error p {
  margin: 0;
  font-size: var(--ds-font-size-sm);
}

/* Stats */
.analysis-progress__stats {
  display: flex;
  justify-content: center;
  gap: var(--ds-space-8);
  margin-top: var(--ds-space-4);
  padding-top: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}

.analysis-progress__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.analysis-progress__stat .stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-success);
}

.analysis-progress__stat .stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

.analysis-progress__stat .stat-value--corrections {
  color: var(--ds-color-warning, var(--yellow-500));
}

/* Actions */
.analysis-progress__actions {
  display: flex;
  justify-content: center;
  margin-top: var(--ds-space-4);
}

.analysis-progress__cancel-btn {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-4);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  background: transparent;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.analysis-progress__cancel-btn:hover {
  background-color: var(--ds-surface-hover);
  color: var(--ds-color-danger);
  border-color: var(--ds-color-danger);
}
</style>
