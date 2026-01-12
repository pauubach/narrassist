<template>
  <div class="home-view">
    <!-- Top Actions Bar -->
    <div class="top-actions">
      <Button
        :icon="appStore.isDark ? 'pi pi-sun' : 'pi pi-moon'"
        @click="appStore.toggleTheme"
        text
        rounded
        v-tooltip.bottom="'Cambiar tema'"
      />
      <Button
        icon="pi pi-cog"
        @click="goToSettings"
        text
        rounded
        v-tooltip.bottom="'Configuración'"
      />
    </div>

    <div class="welcome-container">
      <div class="welcome-header">
        <h1>Narrative Assistant</h1>
        <p class="subtitle">Herramienta de corrección narrativa para editores profesionales</p>
      </div>

      <div class="status-card">
        <h2><i class="pi pi-check-circle"></i> Estado del Sistema</h2>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">Backend Python:</span>
            <span class="status-value" :class="{ 'status-ok': backendStatus }">
              {{ backendStatus ? 'Conectado' : 'Desconectado' }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">Base de datos:</span>
            <span class="status-value status-ok">SQLite Ready</span>
          </div>
          <div class="status-item">
            <span class="status-label">Modelos NLP:</span>
            <span class="status-value status-ok">Offline (Local)</span>
          </div>
        </div>
      </div>

      <div class="actions">
        <Button label="Ver Proyectos" icon="pi pi-folder" @click="goToProjects" size="large" />
        <Button label="Nuevo Proyecto" icon="pi pi-plus" severity="secondary" size="large" outlined />
      </div>

      <div class="info-box">
        <p><strong>Fase 0:</strong> Setup Base completado</p>
        <p><strong>Siguiente:</strong> Implementar FastAPI server</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import Button from 'primevue/button'

const router = useRouter()
const appStore = useAppStore()

const backendStatus = computed(() => appStore.backendConnected)

onMounted(async () => {
  await appStore.checkBackendHealth()
})

const goToProjects = () => {
  router.push('/projects')
}

const goToSettings = () => {
  router.push('/settings')
}
</script>

<style scoped>
.home-view {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  background: var(--surface-ground);
}

.top-actions {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
  z-index: 10;
}

.welcome-container {
  max-width: 600px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 12px;
  padding: 3rem;
  box-shadow: var(--shadow-lg);
}

.welcome-header {
  text-align: center;
  margin-bottom: 2rem;
}

.welcome-header h1 {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.1rem;
  color: var(--text-color-secondary);
}

.status-card {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.status-card h2 {
  font-size: 1.25rem;
  margin-bottom: 1rem;
  color: var(--text-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  font-weight: 500;
  color: #475569;
}

.status-value {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  background: #fee2e2;
  color: #dc2626;
}

.status-value.status-ok {
  background: #d1fae5;
  color: #059669;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-box {
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.info-box p {
  margin: 0.25rem 0;
  color: #1e40af;
}

.info-box strong {
  color: #1e3a8a;
}
</style>
