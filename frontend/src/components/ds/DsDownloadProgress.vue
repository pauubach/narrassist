<script setup lang="ts">
/**
 * DsDownloadProgress - Barra de progreso unificada para descargas.
 *
 * Patron gold standard: label + porcentaje + barra determinada/indeterminada.
 * Usado tanto en ModelSetupDialog (startup) como en SettingsView (descarga manual).
 */
import ProgressBar from 'primevue/progressbar'

defineProps<{
  /** Texto descriptivo de la descarga */
  label: string
  /** Porcentaje de progreso (0-100). Si null/undefined, muestra barra indeterminada */
  percentage?: number | null
  /** Info adicional de descarga (ej: "234 MB / 500 MB") */
  bytesInfo?: string
  /** Velocidad de descarga (ej: "12.3 MB/s") */
  speed?: string
  /** Texto de detalle adicional bajo la barra */
  detail?: string
}>()
</script>

<template>
  <div class="ds-download-progress">
    <div class="ds-download-progress__info">
      <span class="ds-download-progress__label">{{ label }}</span>
      <span v-if="percentage != null" class="ds-download-progress__percent">
        {{ Math.round(percentage) }}%
      </span>
    </div>

    <ProgressBar
      v-if="percentage != null"
      :value="percentage"
      :show-value="false"
      class="ds-download-progress__bar"
    />
    <ProgressBar
      v-else
      mode="indeterminate"
      class="ds-download-progress__bar"
    />

    <div v-if="bytesInfo || speed" class="ds-download-progress__stats">
      <span v-if="bytesInfo" class="ds-download-progress__bytes">{{ bytesInfo }}</span>
      <span v-if="speed" class="ds-download-progress__speed">{{ speed }}</span>
    </div>

    <div v-if="detail" class="ds-download-progress__detail">
      {{ detail }}
    </div>
  </div>
</template>

<style scoped>
.ds-download-progress {
  width: 100%;
}

.ds-download-progress__info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.ds-download-progress__label {
  font-size: 0.85rem;
  color: var(--p-text-color);
  font-weight: 500;
}

.ds-download-progress__percent {
  font-size: 0.85rem;
  color: var(--p-primary-color);
  font-weight: 600;
}

.ds-download-progress__bar {
  height: 8px;
  border-radius: 4px;
}

.ds-download-progress__bar :deep(.p-progressbar-value) {
  background: var(--p-primary-color);
  border-radius: 4px;
}

.ds-download-progress__stats {
  display: flex;
  justify-content: space-between;
  margin-top: 0.35rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.ds-download-progress__bytes {
  font-family: monospace;
}

.ds-download-progress__speed {
  color: var(--p-primary-color);
  font-weight: 500;
}

.ds-download-progress__detail {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
</style>
