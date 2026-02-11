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
          Asistente de corrección con IA para escritores, editores y correctores profesionales.
          Detecta inconsistencias en cualquier tipo de manuscrito.
        </p>
        <p class="privacy-badge">
          <i class="pi pi-shield"></i>
          <span>IA 100% local · Tu manuscrito nunca se sube a internet</span>
        </p>
      </div>

      <div class="system-status">
        <h3>Estado</h3>

        <div class="status-item">
          <span class="status-label">Herramienta de análisis:</span>
          <Tag
            :severity="backendStatus.connected ? 'success' : 'danger'"
          >
            {{ backendStatus.connected ? 'Listo' : 'No disponible' }}
          </Tag>
        </div>

        <div class="status-item">
          <span class="status-label">Base de datos:</span>
          <Tag
            :severity="backendStatus.connected ? 'success' : 'warn'"
          >
            {{ backendStatus.database }}
          </Tag>
        </div>

        <div class="status-item">
          <span class="status-label">Modelos de IA:</span>
          <Tag
            :severity="backendStatus.connected ? 'success' : 'warn'"
          >
            {{ backendStatus.models }}
          </Tag>
        </div>
      </div>

      <div class="copyright">
        <p>&copy; 2026 Narrative Assistant</p>
        <p class="license">Todos los derechos reservados</p>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
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

// Versión desde el backend
const version = computed(() => systemStore.backendVersion || 'sin conexión')

const backendStatus = computed(() => ({
  connected: systemStore.backendConnected,
  database: systemStore.backendConnected ? 'Operativa' : 'No disponible',
  models: systemStore.backendConnected ? 'Cargados' : 'No disponible'
}))

// Refrescar estado al abrir el diálogo
watch(() => props.visible, (newValue) => {
  if (newValue) {
    systemStore.checkBackendStatus()
  }
}, { immediate: true })
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

.privacy-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: var(--green-50);
  border: 1px solid var(--green-200);
  border-radius: 20px;
  font-size: 0.8125rem;
  color: var(--green-700);
}

:global(.dark) .privacy-badge {
  background: var(--green-900);
  border-color: var(--green-700);
  color: var(--green-300);
}

.privacy-badge i {
  color: var(--green-500);
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

.license {
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
