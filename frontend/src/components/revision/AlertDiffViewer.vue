<script setup lang="ts">
/**
 * AlertDiffViewer — Vista side-by-side de alerta antes/después (S14-10).
 *
 * Muestra la alerta resuelta con contexto: título, tipo, posición,
 * razón de resolución y confianza del matching.
 */
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import type { ComparisonAlertDiff } from '@/types/domain/alerts'

const props = defineProps<{
  alert: ComparisonAlertDiff
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

function reasonLabel(reason: string | undefined): string {
  switch (reason) {
    case 'text_changed': return 'El texto fue editado en la zona de la alerta'
    case 'detector_improved': return 'El detector ya no genera esta alerta'
    case 'manual': return 'Resuelta manualmente por el usuario'
    default: return reason || 'Razón no determinada'
  }
}

function reasonIcon(reason: string | undefined): string {
  switch (reason) {
    case 'text_changed': return 'pi pi-pencil'
    case 'detector_improved': return 'pi pi-cog'
    case 'manual': return 'pi pi-user'
    default: return 'pi pi-question-circle'
  }
}

const confidencePercent = computed(() =>
  Math.round((props.alert.matchConfidence ?? 0) * 100)
)

const confidenceLabel = computed(() => {
  const pct = confidencePercent.value
  if (pct >= 90) return 'Alta'
  if (pct >= 70) return 'Media'
  return 'Baja'
})
</script>

<template>
  <Dialog
    :visible="true"
    header="Detalle de alerta resuelta"
    :modal="true"
    :style="{ width: '550px' }"
    @update:visible="emit('close')"
  >
    <div class="diff-viewer">
      <div class="diff-section">
        <h4>Alerta</h4>
        <div class="diff-field">
          <span class="field-label">Título:</span>
          <span class="field-value">{{ alert.title }}</span>
        </div>
        <div class="diff-field">
          <span class="field-label">Tipo:</span>
          <Tag :value="alert.alertType" severity="secondary" />
        </div>
        <div class="diff-field">
          <span class="field-label">Categoría:</span>
          <span class="field-value">{{ alert.category }}</span>
        </div>
        <div v-if="alert.chapter" class="diff-field">
          <span class="field-label">Capítulo:</span>
          <span class="field-value">{{ alert.chapter }}</span>
        </div>
        <div v-if="alert.spanStart != null" class="diff-field">
          <span class="field-label">Posición:</span>
          <span class="field-value">chars {{ alert.spanStart }}–{{ alert.spanEnd }}</span>
        </div>
      </div>

      <div class="diff-divider" />

      <div class="diff-section resolution-section">
        <h4>Resolución</h4>
        <div class="resolution-reason">
          <i :class="reasonIcon(alert.resolutionReason)" />
          <span>{{ reasonLabel(alert.resolutionReason) }}</span>
        </div>

        <div v-if="alert.matchConfidence" class="confidence-bar">
          <span class="confidence-label">Confianza: {{ confidenceLabel }} ({{ confidencePercent }}%)</span>
          <div class="bar-track">
            <div
              class="bar-fill"
              :style="{ width: `${confidencePercent}%` }"
              :class="{
                high: confidencePercent >= 90,
                medium: confidencePercent >= 70 && confidencePercent < 90,
                low: confidencePercent < 70,
              }"
            />
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Cerrar" text @click="emit('close')" />
    </template>
  </Dialog>
</template>

<style scoped>
.diff-viewer {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diff-section h4 {
  margin: 0 0 10px;
  font-size: 0.95rem;
  color: var(--text-color);
}

.diff-field {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.field-label {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  min-width: 80px;
}

.field-value {
  font-weight: 500;
}

.diff-divider {
  height: 1px;
  background: var(--surface-border);
}

.resolution-section {
  background: var(--surface-ground);
  padding: 12px;
  border-radius: var(--app-radius);
}

.resolution-reason {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  padding: 8px 0;
}

.resolution-reason i {
  font-size: 1.1rem;
  color: var(--primary-color);
}

.confidence-bar {
  margin-top: 10px;
}

.confidence-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.bar-track {
  height: 6px;
  background: var(--surface-200);
  border-radius: var(--app-radius-sm);
  margin-top: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--app-radius-sm);
  transition: width 0.3s ease;
}

.bar-fill.high { background: var(--green-500); }
.bar-fill.medium { background: var(--yellow-500); }
.bar-fill.low { background: var(--orange-500); }
</style>
