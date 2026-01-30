<template>
  <div class="analysis-error-state">
    <i class="pi pi-exclamation-triangle"></i>
    <p class="error-message">{{ message }}</p>
    <Button
      v-if="onRetry"
      label="Reintentar"
      icon="pi pi-refresh"
      severity="secondary"
      @click="onRetry"
    />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'

defineProps<{
  message: string
  onRetry?: () => void
}>()
</script>

<style scoped>
.analysis-error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--ds-color-text-secondary);
}

.analysis-error-state i {
  font-size: 2rem;
  color: var(--p-red-400);
}

.error-message {
  text-align: center;
  max-width: 400px;
  margin: 0;
}
</style>
