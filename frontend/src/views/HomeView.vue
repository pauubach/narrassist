<template>
  <ErrorBoundary>
    <div class="home-view">
    <!-- Top Actions Bar -->
    <div class="top-actions">
      <Button
        v-tooltip.bottom="'Cambiar tema'"
        :icon="appStore.isDark ? 'pi pi-sun' : 'pi pi-moon'"
        text
        rounded
        @click="appStore.toggleTheme"
      />
      <Button
        v-tooltip.bottom="'Configuración'"
        icon="pi pi-cog"
        text
        rounded
        @click="goToSettings"
      />
    </div>

    <div class="welcome-container">
      <div class="welcome-header">
        <h1>Narrative Assistant</h1>
        <p class="subtitle">Asistente de corrección con IA para escritores, editores y correctores profesionales</p>
        <p class="privacy-note">
          <i class="pi pi-shield"></i>
          <span>IA 100% local · Tu manuscrito nunca se sube a internet</span>
        </p>
      </div>

      <div class="status-card">
        <h2><i class="pi pi-check-circle"></i> Estado del Sistema</h2>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">Motor interno:</span>
            <span
              class="status-value"
              :class="{ 'status-ok': backendStatus || systemStore.backendStarting, 'status-error': showBackendDisconnected }"
            >
              {{ systemStore.backendStarting ? 'Iniciando...' : (backendStatus ? 'Activo' : 'Inactivo') }}
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

        <!-- Error message and retry when backend disconnected -->
        <div v-if="showBackendDisconnected" class="backend-error-container">
          <p class="backend-error-message">
            <i class="pi pi-exclamation-triangle"></i>
            {{ backendError || 'El motor de análisis no responde. Reintentando...' }}
          </p>
          <Button
            label="Reintentar"
            icon="pi pi-refresh"
            severity="warning"
            size="small"
            :loading="isRetrying"
            @click="retryConnection"
          />
        </div>
      </div>

      <!-- Métricas globales (solo si hay datos cacheados) -->
      <div v-if="globalMetrics.manuscripts > 0" class="global-stats">
        <h2><i class="pi pi-chart-bar"></i> Tu actividad</h2>
        <div class="stats-grid">
          <div class="stat-card stat-manuscripts">
            <div class="stat-icon-bg">
              <i class="pi pi-book"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ globalMetrics.manuscripts }}</span>
              <span class="stat-label">Manuscritos analizados</span>
            </div>
          </div>

          <div class="stat-card stat-reviewed">
            <div class="stat-icon-bg">
              <i class="pi pi-check-square"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ globalMetrics.reviewed }}</span>
              <span class="stat-label">Alertas revisadas</span>
            </div>
          </div>

          <div class="stat-card stat-time">
            <div class="stat-icon-bg">
              <i class="pi pi-clock"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ globalMetrics.timeSavedFormatted }}</span>
              <span class="stat-label">Tiempo estimado ahorrado</span>
            </div>
          </div>

          <div class="stat-card stat-rate">
            <div class="stat-icon-bg">
              <i class="pi pi-percentage"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ globalMetrics.reviewRate }}%</span>
              <span class="stat-label">Tasa de revisión</span>
            </div>
          </div>
        </div>
      </div>

      <div class="actions">
        <Button label="Ver Proyectos" icon="pi pi-folder" size="large" @click="goToProjects" />
        <Button label="Nuevo Proyecto" icon="pi pi-plus" severity="secondary" size="large" outlined @click="goToProjects" />
      </div>
    </div>
    </div>
  </ErrorBoundary>
</template>

<script setup lang="ts">
import ErrorBoundary from '../components/ErrorBoundary.vue'

import { onMounted, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useSystemStore } from '@/stores/system'
import { useGlobalStats } from '@/composables/useGlobalStats'
import Button from 'primevue/button'

const router = useRouter()
const appStore = useAppStore()
const systemStore = useSystemStore()
const { globalMetrics } = useGlobalStats()

const backendStatus = computed(() => systemStore.backendConnected)
const backendError = computed(() => systemStore.backendStartupError)
const showBackendDisconnected = computed(() => !systemStore.backendStarting && !backendStatus.value)
const isRetrying = ref(false)

const retryConnection = async () => {
  isRetrying.value = true
  await systemStore.checkBackendStatus()
  if (!backendStatus.value) {
    systemStore.startRetrying()
  }
  isRetrying.value = false
}

onMounted(async () => {
  await systemStore.checkBackendStatus()
  if (!backendStatus.value) {
    systemStore.startRetrying()
  }
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
  z-index: var(--ds-z-fixed);
}

.welcome-container {
  max-width: 600px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--app-radius-lg);
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

.privacy-note {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: var(--green-50);
  border: 1px solid var(--green-200);
  border-radius: var(--app-radius-lg);
  font-size: 0.875rem;
  color: var(--green-700);
}

:global(.dark) .privacy-note {
  background: var(--green-900);
  border-color: var(--green-700);
  color: var(--green-300);
}

.privacy-note i {
  color: var(--ds-text-success);
}

.status-card {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: var(--app-radius);
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
  color: var(--text-color-secondary);
}

.status-value {
  padding: 0.25rem 0.75rem;
  border-radius: var(--app-radius);
  font-size: 0.875rem;
  font-weight: 600;
  background: var(--red-50);
  color: var(--red-600);
}

.status-value.status-ok {
  background: var(--green-50);
  color: var(--green-600);
}

.status-value.status-error {
  background: var(--red-50);
  color: var(--red-600);
}

.backend-error-container {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--yellow-50);
  border: 1px solid var(--yellow-500);
  border-radius: var(--app-radius);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.backend-error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--yellow-900);
  font-size: 0.9rem;
  margin: 0;
}

:global(.dark) .backend-error-container {
  background: var(--yellow-900);
  border-color: var(--yellow-700);
}

:global(.dark) .backend-error-message {
  color: var(--yellow-300);
}

.actions {
  display: flex;
  gap: 1rem;
}

/* Global Stats */
.global-stats {
  margin-bottom: 2rem;
}

.global-stats h2 {
  font-size: 1.25rem;
  margin-bottom: 1rem;
  color: var(--text-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--app-radius);
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon-bg {
  width: 36px;
  height: 36px;
  border-radius: var(--app-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1rem;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Card color variants */
.stat-manuscripts .stat-icon-bg {
  background: var(--blue-50);
  color: var(--blue-500);
}

.stat-reviewed .stat-icon-bg {
  background: var(--green-50);
  color: var(--ds-text-success);
}

.stat-time .stat-icon-bg {
  background: var(--purple-50);
  color: var(--purple-500);
}

.stat-rate .stat-icon-bg {
  background: var(--orange-50);
  color: var(--orange-500);
}

/* Dark mode */
:global(.dark) .stat-card {
  border-color: var(--surface-600);
}

:global(.dark) .stat-manuscripts .stat-icon-bg {
  background: var(--blue-900);
}

:global(.dark) .stat-reviewed .stat-icon-bg {
  background: var(--green-900);
}

:global(.dark) .stat-time .stat-icon-bg {
  background: var(--purple-900);
}

:global(.dark) .stat-rate .stat-icon-bg {
  background: var(--orange-900);
}
</style>
