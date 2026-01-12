<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :closable="true"
    :draggable="false"
    class="about-dialog"
    header="Acerca de Narrative Assistant"
  >
    <div class="about-content">
      <div class="app-info">
        <h2>Narrative Assistant</h2>
        <p class="version">Versión {{ version }}</p>
        <p class="description">
          Herramienta de corrección narrativa para editores profesionales
        </p>
      </div>

      <div class="system-status">
        <h3>Estado del Sistema</h3>

        <div class="status-item">
          <span class="status-label">Backend Python:</span>
          <Tag
            :value="backendStatus.connected ? 'Conectado' : 'Desconectado'"
            :severity="backendStatus.connected ? 'success' : 'danger'"
          />
        </div>

        <div class="status-item">
          <span class="status-label">Base de datos:</span>
          <Tag
            :value="backendStatus.database"
            :severity="backendStatus.database === 'SQLite Ready' ? 'success' : 'warning'"
          />
        </div>

        <div class="status-item">
          <span class="status-label">Modelos NLP:</span>
          <Tag
            :value="backendStatus.models"
            :severity="backendStatus.models === 'Offline (Local)' ? 'success' : 'info'"
          />
        </div>
      </div>

      <div class="copyright">
        <p>&copy; 2026 Narrative Assistant</p>
        <p class="tech-stack">Vue 3 · FastAPI · spaCy · SQLite</p>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useSystemStore } from '@/stores/system'

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const systemStore = useSystemStore()

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const version = ref('0.1.0')

const backendStatus = computed(() => ({
  connected: systemStore.backendConnected,
  database: systemStore.backendConnected ? 'SQLite Ready' : 'No disponible',
  models: systemStore.backendConnected ? 'Offline (Local)' : 'No disponible'
}))

// Refrescar estado al abrir el diálogo
watch(() => props.visible, (newValue) => {
  if (newValue) {
    systemStore.checkBackendStatus()
  }
})
</script>

<style scoped>
.about-dialog {
  width: 500px;
  max-width: 90vw;
}

.about-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.app-info {
  text-align: center;
  padding: 1rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.app-info h2 {
  font-size: 1.75rem;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.version {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin: 0 0 1rem 0;
}

.description {
  color: var(--text-color-secondary);
  font-size: 0.9375rem;
  margin: 0;
  line-height: 1.5;
}

.system-status h3 {
  font-size: 1.125rem;
  margin: 0 0 1rem 0;
  font-weight: 600;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: var(--text-color);
}

.copyright {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.copyright p {
  margin: 0.25rem 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.tech-stack {
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
