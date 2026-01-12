<template>
  <div class="alerts-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          @click="goBack"
          v-tooltip.right="'Volver al proyecto'"
        />
        <div class="header-info">
          <h1>Alertas</h1>
          <p v-if="project">{{ project.name }}</p>
        </div>
      </div>
      <div class="header-actions">
        <Button
          label="Exportar"
          icon="pi pi-download"
          outlined
          @click="exportAlerts"
        />
        <Button
          label="Resolver todas"
          icon="pi pi-check-circle"
          @click="resolveAll"
          :disabled="openAlertsCount === 0"
        />
      </div>
    </div>

    <!-- Stats bar -->
    <div class="stats-bar">
      <div class="stat-item critical">
        <i class="pi pi-exclamation-circle"></i>
        <span class="stat-value">{{ criticalCount }}</span>
        <span class="stat-label">Críticas</span>
      </div>
      <div class="stat-item warning">
        <i class="pi pi-exclamation-triangle"></i>
        <span class="stat-value">{{ warningCount }}</span>
        <span class="stat-label">Advertencias</span>
      </div>
      <div class="stat-item info">
        <i class="pi pi-info-circle"></i>
        <span class="stat-value">{{ infoCount }}</span>
        <span class="stat-label">Informativas</span>
      </div>
      <div class="stat-item">
        <i class="pi pi-check"></i>
        <span class="stat-value">{{ resolvedCount }}</span>
        <span class="stat-label">Resueltas</span>
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="view-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <ProgressSpinner />
        <p>Cargando alertas...</p>
      </div>

      <!-- Error state -->
      <Message v-else-if="error" severity="error" :closable="false">
        {{ error }}
      </Message>

      <!-- Alert List -->
      <AlertList
        v-else
        :alerts="alerts"
        :loading="loading"
        :show-title="false"
        :show-filters="true"
        :show-actions="true"
        :show-pagination="true"
        :selected-alert-id="selectedAlertId"
        @select="onAlertSelect"
        @view-context="onViewContext"
        @resolve="onResolveAlert"
        @dismiss="onDismissAlert"
        @refresh="loadAlerts"
      />
    </div>

    <!-- Sidebar con detalles de alerta -->
    <Sidebar
      v-model:visible="showAlertDetails"
      position="right"
      :style="{ width: '600px' }"
      :modal="false"
    >
      <template #header>
        <div class="sidebar-header">
          <h3>Detalles de Alerta</h3>
        </div>
      </template>

      <div v-if="selectedAlert" class="alert-details">
        <!-- Severidad y categoría -->
        <div class="detail-section">
          <div class="alert-detail-header">
            <Tag :severity="getSeverityColor(selectedAlert.severity)" class="large-tag">
              <i :class="getSeverityIcon(selectedAlert.severity)"></i>
              {{ selectedAlert.severity.toUpperCase() }}
            </Tag>
            <Tag severity="secondary" class="large-tag">
              {{ getCategoryLabel(selectedAlert.category) }}
            </Tag>
          </div>
        </div>

        <Divider />

        <!-- Título y descripción -->
        <div class="detail-section">
          <h2 class="alert-detail-title">{{ selectedAlert.title }}</h2>
          <p class="alert-detail-description">{{ selectedAlert.description }}</p>
        </div>

        <Divider />

        <!-- Explicación -->
        <div v-if="selectedAlert.explanation" class="detail-section">
          <h4>Explicación</h4>
          <p class="explanation-text">{{ selectedAlert.explanation }}</p>
        </div>

        <!-- Sugerencia -->
        <div v-if="selectedAlert.suggestion" class="detail-section">
          <h4>Sugerencia</h4>
          <Panel class="suggestion-panel">
            <template #header>
              <i class="pi pi-lightbulb"></i>
              <span>Cómo resolverlo</span>
            </template>
            <p>{{ selectedAlert.suggestion }}</p>
          </Panel>
        </div>

        <Divider />

        <!-- Ubicación -->
        <div class="detail-section">
          <h4>Ubicación</h4>
          <div class="location-info">
            <div v-if="selectedAlert.chapter" class="location-item">
              <i class="pi pi-book"></i>
              <span>Capítulo {{ selectedAlert.chapter }}</span>
            </div>
            <div v-if="selectedAlert.position_start" class="location-item">
              <i class="pi pi-map-marker"></i>
              <span>Posición {{ selectedAlert.position_start }}</span>
            </div>
          </div>
          <Button
            label="Ver en contexto"
            icon="pi pi-search"
            outlined
            class="w-full mt-2"
            @click="onViewContext(selectedAlert)"
          />
        </div>

        <Divider />

        <!-- Entidades relacionadas -->
        <div v-if="selectedAlert.entities && selectedAlert.entities.length > 0" class="detail-section">
          <h4>Entidades relacionadas</h4>
          <div class="entities-grid">
            <Chip
              v-for="entity in selectedAlert.entities"
              :key="entity.id"
              :label="entity.canonical_name"
              icon="pi pi-user"
            />
          </div>
        </div>

        <Divider />

        <!-- Metadata -->
        <div class="detail-section">
          <h4>Información</h4>
          <div class="metadata-grid">
            <div class="metadata-item">
              <span class="metadata-label">Estado</span>
              <Tag :severity="getStatusSeverity(selectedAlert.status)">
                {{ getStatusLabel(selectedAlert.status) }}
              </Tag>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Tipo</span>
              <span class="metadata-value">{{ selectedAlert.alert_type }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Creada</span>
              <span class="metadata-value">{{ formatDate(selectedAlert.created_at) }}</span>
            </div>
            <div v-if="selectedAlert.resolved_at" class="metadata-item">
              <span class="metadata-label">Resuelta</span>
              <span class="metadata-value">{{ formatDate(selectedAlert.resolved_at) }}</span>
            </div>
          </div>
        </div>

        <Divider />

        <!-- Acciones -->
        <div class="detail-section">
          <h4>Acciones</h4>
          <div class="detail-actions">
            <Button
              v-if="selectedAlert.status === 'open'"
              label="Marcar como resuelta"
              icon="pi pi-check"
              severity="success"
              @click="onResolveAlert(selectedAlert)"
              class="w-full"
            />
            <Button
              v-if="selectedAlert.status === 'open'"
              label="Descartar alerta"
              icon="pi pi-times"
              severity="secondary"
              outlined
              @click="onDismissAlert(selectedAlert)"
              class="w-full"
            />
            <Button
              v-if="selectedAlert.status !== 'open'"
              label="Reabrir alerta"
              icon="pi pi-replay"
              outlined
              @click="onReopenAlert(selectedAlert)"
              class="w-full"
            />
          </div>
        </div>
      </div>
    </Sidebar>

    <!-- Diálogo de confirmación: Resolver todas -->
    <Dialog
      v-model:visible="showResolveAllDialog"
      modal
      header="Resolver todas las alertas"
      :style="{ width: '500px' }"
    >
      <p>
        ¿Estás seguro de que quieres marcar todas las alertas abiertas como resueltas?
      </p>
      <Message severity="warn" :closable="false">
        Esta acción afectará a {{ openAlertsCount }} alertas abiertas.
      </Message>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="showResolveAllDialog = false"
        />
        <Button
          label="Resolver todas"
          icon="pi pi-check"
          severity="success"
          @click="confirmResolveAll"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Sidebar from 'primevue/sidebar'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Panel from 'primevue/panel'
import Divider from 'primevue/divider'
import AlertList from '@/components/AlertList.vue'
import type { Alert } from '@/types'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

// Estado
const loading = ref(true)
const error = ref('')
const alerts = ref<Alert[]>([])
const selectedAlertId = ref<number | null>(null)
const selectedAlert = ref<Alert | null>(null)
const showAlertDetails = ref(false)
const showResolveAllDialog = ref(false)

const project = computed(() => projectsStore.currentProject)
const projectId = computed(() => parseInt(route.params.id as string))

// Computed stats
const criticalCount = computed(() =>
  alerts.value.filter(a => a.severity === 'critical' && a.status === 'open').length
)

const warningCount = computed(() =>
  alerts.value.filter(a => a.severity === 'warning' && a.status === 'open').length
)

const infoCount = computed(() =>
  alerts.value.filter(a => a.severity === 'info' && a.status === 'open').length
)

const resolvedCount = computed(() =>
  alerts.value.filter(a => a.status === 'resolved').length
)

const openAlertsCount = computed(() =>
  alerts.value.filter(a => a.status === 'open').length
)

// Funciones
const loadAlerts = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`/api/projects/${projectId.value}/alerts`)
    const data = await response.json()

    if (data.success) {
      alerts.value = data.data || []
    } else {
      error.value = 'Error cargando alertas'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push({ name: 'project', params: { id: projectId.value } })
}

const onAlertSelect = (alert: Alert) => {
  selectedAlertId.value = alert.id
  selectedAlert.value = alert
  showAlertDetails.value = true
}

const onViewContext = (alert: Alert) => {
  // Navegar al documento con la alerta resaltada
  router.push({
    name: 'project',
    params: { id: projectId.value },
    query: {
      alert: alert.id,
      chapter: alert.chapter
    }
  })
}

const onResolveAlert = async (alert: Alert) => {
  try {
    const response = await fetch(`/api/projects/${projectId.value}/alerts/${alert.id}/resolve`, {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      await loadAlerts()
      showAlertDetails.value = false
    }
  } catch (err) {
    console.error('Error resolving alert:', err)
  }
}

const onDismissAlert = async (alert: Alert) => {
  try {
    const response = await fetch(`/api/projects/${projectId.value}/alerts/${alert.id}/dismiss`, {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      await loadAlerts()
      showAlertDetails.value = false
    }
  } catch (err) {
    console.error('Error dismissing alert:', err)
  }
}

const onReopenAlert = async (alert: Alert) => {
  try {
    const response = await fetch(`/api/projects/${projectId.value}/alerts/${alert.id}/reopen`, {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      await loadAlerts()
    }
  } catch (err) {
    console.error('Error reopening alert:', err)
  }
}

const resolveAll = () => {
  showResolveAllDialog.value = true
}

const confirmResolveAll = async () => {
  try {
    const response = await fetch(`/api/projects/${projectId.value}/alerts/resolve-all`, {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      showResolveAllDialog.value = false
      await loadAlerts()
    }
  } catch (err) {
    console.error('Error resolving all alerts:', err)
  }
}

const exportAlerts = () => {
  // TODO: Implementar exportación
  console.log('Export alerts')
}

// Helpers
const getSeverityColor = (severity: string): string => {
  const colors: Record<string, string> = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info',
    'hint': 'secondary'
  }
  return colors[severity] || 'secondary'
}

const getSeverityIcon = (severity: string): string => {
  const icons: Record<string, string> = {
    'critical': 'pi pi-exclamation-circle',
    'warning': 'pi pi-exclamation-triangle',
    'info': 'pi pi-info-circle',
    'hint': 'pi pi-lightbulb'
  }
  return icons[severity] || 'pi pi-info-circle'
}

const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    'consistency': 'Consistencia',
    'continuity': 'Continuidad',
    'characterization': 'Caracterización',
    'chronology': 'Cronología',
    'style': 'Estilo'
  }
  return labels[category] || category
}

const getStatusSeverity = (status: string): string => {
  const severities: Record<string, string> = {
    'open': 'warning',
    'resolved': 'success',
    'dismissed': 'secondary'
  }
  return severities[status] || 'secondary'
}

const getStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    'open': 'Abierta',
    'resolved': 'Resuelta',
    'dismissed': 'Descartada'
  }
  return labels[status] || status
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Lifecycle
onMounted(async () => {
  await projectsStore.fetchProject(projectId.value)
  await loadAlerts()
})
</script>

<style scoped>
.alerts-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: white;
  border-bottom: 1px solid var(--surface-border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-info h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-color);
}

.header-info p {
  margin: 0.25rem 0 0 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.stats-bar {
  display: flex;
  gap: 2rem;
  padding: 1rem 2rem;
  background: white;
  border-bottom: 1px solid var(--surface-border);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.stat-item i {
  font-size: 1.5rem;
  color: var(--text-color-secondary);
}

.stat-item.critical i {
  color: var(--red-500);
}

.stat-item.warning i {
  color: var(--yellow-600);
}

.stat-item.info i {
  color: var(--blue-500);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.view-content {
  flex: 1;
  overflow: hidden;
  padding: 1rem 2rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
}

/* Sidebar de detalles */
.sidebar-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.alert-details {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-section h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.alert-detail-header {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.large-tag {
  font-size: 0.875rem;
  padding: 0.5rem 0.75rem;
}

.large-tag i {
  margin-right: 0.5rem;
}

.alert-detail-title {
  margin: 0 0 0.75rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.alert-detail-description {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--text-color-secondary);
  line-height: 1.6;
}

.explanation-text {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--text-color);
  line-height: 1.6;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 3px solid var(--blue-500);
}

.suggestion-panel {
  background: var(--yellow-50);
  border: 1px solid var(--yellow-200);
}

.suggestion-panel :deep(.p-panel-header) {
  background: var(--yellow-100);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.location-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.location-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9375rem;
  color: var(--text-color);
}

.location-item i {
  color: var(--primary-color);
}

.entities-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.metadata-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.metadata-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.metadata-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  font-weight: 600;
}

.metadata-value {
  font-size: 0.9375rem;
  color: var(--text-color);
}

.detail-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.w-full {
  width: 100%;
}

.mt-2 {
  margin-top: 0.5rem;
}
</style>
