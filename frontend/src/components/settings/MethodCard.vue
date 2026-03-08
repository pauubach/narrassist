<template>
  <div
    class="method-card"
    :class="{ disabled: !method.available, enabled: enabled }"
  >
    <div class="method-header">
      <ToggleSwitch
        :inputId="`method-${category}-${methodKey}`"
        :model-value="enabled"
        :aria-label="method.name"
        :disabled="!method.available"
        @update:model-value="$emit('toggle', $event)"
      />
      <label class="method-name" :for="`method-${category}-${methodKey}`">{{ method.name }}</label>
      <Tag v-if="method.recommended_gpu && !method.requires_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
      <Tag v-if="method.recommended_gpu && !method.requires_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
      <Tag
        v-if="method.requires_gpu"
        v-tooltip.top="gpuTooltip"
        :value="systemCapabilities?.hardware.gpu_blocked ? 'Hardware no compatible' : 'Requiere aceleración'"
        severity="warning"
        class="method-tag"
      />
      <Tag v-if="!method.available && method.requires_ollama" value="Requiere iniciar el analizador" severity="warning" class="method-tag" />
      <Tag v-else-if="!method.available && method.hardware_supported === false" value="No compatible con este equipo" severity="danger" class="method-tag" />
      <Tag v-else-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
    </div>
    <p class="method-description">{{ method.description }}</p>
    <div v-if="showWeight && method.weight" class="method-weight">
      Peso en votación: {{ (method.weight * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'

defineProps<{
  category: string
  methodKey: string
  method: Record<string, any>
  enabled: boolean
  systemCapabilities: Record<string, any> | null
  gpuTooltip: string
  showWeight?: boolean
}>()

defineEmits<{
  toggle: [value: boolean]
}>()
</script>
