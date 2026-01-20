<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import Dialog from 'primevue/dialog'

const systemStore = useSystemStore()

const visible = ref(false)
const checkPhase = ref<'checking' | 'ready' | 'error'>('checking')

// Check models on mount - they should already be installed with the app
onMounted(async () => {
  checkPhase.value = 'checking'
  await systemStore.checkModelsStatus()

  if (systemStore.modelsReady) {
    // Models are bundled with the app, all good
    checkPhase.value = 'ready'
  } else {
    // This shouldn't happen in production - models should be bundled
    visible.value = true
    checkPhase.value = 'error'
  }
})

// Watch for model status changes
watch(() => systemStore.modelsReady, (ready) => {
  if (ready && visible.value) {
    checkPhase.value = 'ready'
    setTimeout(() => {
      visible.value = false
    }, 1500)
  }
})

const missingModels = computed(() => {
  if (!systemStore.modelsStatus?.nlp_models) return []

  return Object.entries(systemStore.modelsStatus.nlp_models)
    .filter(([_, info]) => !info.installed)
    .map(([name, info]) => ({
      name,
      displayName: info.display_name,
      sizeMb: info.size_mb
    }))
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :closable="false"
    :modal="true"
    :draggable="false"
    header="Configuracion"
    class="model-setup-dialog"
    :style="{ width: '450px' }"
  >
    <div class="dialog-content">
      <!-- Checking state -->
      <template v-if="checkPhase === 'checking'">
        <div class="checking-state">
          <i class="pi pi-spin pi-spinner checking-spinner"></i>
          <p>Verificando configuracion...</p>
        </div>
      </template>

      <!-- Ready state -->
      <template v-else-if="checkPhase === 'ready'">
        <div class="ready-state">
          <i class="pi pi-check-circle ready-icon"></i>
          <h3>Listo</h3>
          <p>Narrative Assistant esta preparado.</p>
        </div>
      </template>

      <!-- Error state - models missing (shouldn't happen in production) -->
      <template v-else-if="checkPhase === 'error'">
        <div class="error-state">
          <i class="pi pi-exclamation-triangle error-icon"></i>
          <h3>Modelos no encontrados</h3>
          <p class="error-message">
            Los modelos de NLP no estan instalados correctamente.
          </p>

          <div v-if="missingModels.length > 0" class="missing-list">
            <p>Modelos faltantes:</p>
            <ul>
              <li v-for="model in missingModels" :key="model.name">
                {{ model.displayName }}
              </li>
            </ul>
          </div>

          <p class="error-hint">
            Por favor, reinstala la aplicacion o contacta con soporte.
          </p>
        </div>
      </template>
    </div>
  </Dialog>
</template>

<style scoped>
.dialog-content {
  padding: 0.5rem 0;
}

.checking-state {
  text-align: center;
  padding: 2rem;
}

.checking-spinner {
  font-size: 2rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.ready-state {
  text-align: center;
  padding: 2rem 1rem;
}

.ready-icon {
  font-size: 4rem;
  color: var(--p-green-500);
  margin-bottom: 1rem;
}

.ready-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-green-700);
}

.ready-state p {
  margin: 0;
  color: var(--p-text-muted-color);
}

.error-state {
  text-align: center;
  padding: 1.5rem;
}

.error-icon {
  font-size: 3rem;
  color: var(--p-red-500);
  margin-bottom: 1rem;
}

.error-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-red-700);
}

.error-message {
  color: var(--p-text-muted-color);
  margin-bottom: 1rem;
}

.missing-list {
  background: var(--p-surface-100);
  border-radius: 6px;
  padding: 1rem;
  margin: 1rem 0;
  text-align: left;
}

.missing-list p {
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.missing-list ul {
  margin: 0;
  padding-left: 1.5rem;
}

.missing-list li {
  margin: 0.25rem 0;
  color: var(--p-text-muted-color);
}

.error-hint {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  margin: 0;
}

/* Dark mode */
.dark .ready-state h3 {
  color: var(--p-green-400);
}

.dark .error-state h3 {
  color: var(--p-red-400);
}

.dark .missing-list {
  background: var(--p-surface-800);
}
</style>
