<template>
  <div class="error-boundary-wrapper">
    <slot v-if="!hasError" />
    <div v-else class="error-boundary">
      <div class="error-boundary__content">
        <i class="pi pi-exclamation-triangle error-boundary__icon"></i>
        <h2 class="error-boundary__title">Algo salió mal</h2>
        <p class="error-boundary__message">
          {{ errorMessage }}
        </p>
        <div class="error-boundary__actions">
          <Button
            label="Reintentar"
            icon="pi pi-refresh"
            @click="retry"
            severity="secondary"
          />
          <Button
            label="Volver al inicio"
            icon="pi pi-home"
            @click="goHome"
            outlined
          />
        </div>
        <details v-if="errorDetails" class="error-boundary__details">
          <summary>Detalles técnicos</summary>
          <pre>{{ errorDetails }}</pre>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

const router = useRouter()

const hasError = ref(false)
const errorMessage = ref('')
const errorDetails = ref('')

onErrorCaptured((err, instance, info) => {
  hasError.value = true

  // Mensaje user-friendly según tipo de error
  if (err.message?.includes('Failed to fetch')) {
    errorMessage.value = 'No se pudo conectar con el servidor. Verifica tu conexión.'
  } else if (err.message?.includes('Network')) {
    errorMessage.value = 'Error de red. Intenta nuevamente.'
  } else if (err.message?.includes('timeout')) {
    errorMessage.value = 'La operación tardó demasiado. Intenta nuevamente.'
  } else {
    errorMessage.value = 'Ocurrió un error inesperado. Por favor, intenta nuevamente.'
  }

  // Detalles técnicos (solo en desarrollo o para reportes)
  errorDetails.value = `Error: ${err.message}\nStack: ${err.stack}\nInfo: ${info}`

  // Log en consola
  console.error('[ErrorBoundary]', {
    error: err,
    component: instance,
    info,
  })

  // Detener propagación del error
  return false
})

function retry() {
  hasError.value = false
  errorMessage.value = ''
  errorDetails.value = ''
}

function goHome() {
  hasError.value = false
  errorMessage.value = ''
  errorDetails.value = ''
  router.push('/')
}
</script>

<style scoped>
.error-boundary-wrapper {
  display: contents;
}

.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: var(--ds-spacing-6);
}

.error-boundary__content {
  max-width: 600px;
  text-align: center;
}

.error-boundary__icon {
  font-size: 4rem;
  color: var(--red-500);
  margin-bottom: var(--ds-spacing-4);
}

.error-boundary__title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--ds-text-primary);
  margin-bottom: var(--ds-spacing-3);
}

.error-boundary__message {
  font-size: 1rem;
  color: var(--ds-text-secondary);
  margin-bottom: var(--ds-spacing-6);
  line-height: 1.6;
}

.error-boundary__actions {
  display: flex;
  gap: var(--ds-spacing-3);
  justify-content: center;
  margin-bottom: var(--ds-spacing-6);
}

.error-boundary__details {
  text-align: left;
  margin-top: var(--ds-spacing-4);
  padding: var(--ds-spacing-4);
  background: var(--surface-100);
  border: 1px solid var(--surface-200);
  border-radius: 6px;
}

.error-boundary__details summary {
  cursor: pointer;
  font-weight: 500;
  color: var(--ds-text-secondary);
  user-select: none;
}

.error-boundary__details summary:hover {
  color: var(--ds-text-primary);
}

.error-boundary__details pre {
  margin-top: var(--ds-spacing-3);
  padding: var(--ds-spacing-3);
  background: var(--surface-0);
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.875rem;
  color: var(--ds-text-primary);
  font-family: 'Courier New', monospace;
}
</style>
