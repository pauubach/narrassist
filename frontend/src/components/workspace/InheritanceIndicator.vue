<template>
  <div class="inheritance-indicator" :class="{ custom: isCustom }">
    <i
      v-if="!isCustom"
      v-tooltip.top="'Valor por defecto del tipo/subtipo'"
      class="pi pi-link"
    />
    <Button
      v-else
      v-tooltip.top="'Restaurar valor por defecto'"
      icon="pi pi-undo"
      text
      rounded
      size="small"
      severity="secondary"
      @click="$emit('reset')"
    />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'

defineProps<{
  isCustom: boolean
}>()

defineEmits<{
  (e: 'reset'): void
}>()
</script>

<style scoped>
.inheritance-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.inheritance-indicator i {
  font-size: 0.875rem;
  color: var(--primary-color);
  opacity: 0.6;
}

.inheritance-indicator.custom i {
  color: var(--orange-500);
}

.inheritance-indicator :deep(.p-button) {
  width: 28px;
  height: 28px;
}

.inheritance-indicator :deep(.p-button .pi) {
  font-size: 0.75rem;
}
</style>
