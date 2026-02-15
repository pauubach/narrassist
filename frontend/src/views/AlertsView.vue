<template>
  <div class="alerts-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button
          v-tooltip.right="'Volver al proyecto'"
          icon="pi pi-arrow-left"
          text
          rounded
          @click="goBack"
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
          :disabled="openAlertsCount === 0"
          @click="resolveAll"
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

    <!-- Drawer con detalles de alerta -->
    <Drawer
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
            <div v-if="selectedAlert.spanStart" class="location-item">
              <i class="pi pi-map-marker"></i>
              <span>Posición {{ selectedAlert.spanStart }}</span>
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
        <div v-if="selectedAlert.entityIds && selectedAlert.entityIds.length > 0" class="detail-section">
          <h4>Entidades relacionadas</h4>
          <div class="entities-grid">
            <Chip
              v-for="entityId in selectedAlert.entityIds"
              :key="entityId"
              :label="`Entidad #${entityId}`"
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
              <span class="metadata-label">Categoría</span>
              <span class="metadata-value">{{ getCategoryLabel(selectedAlert.category) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Creada</span>
              <span class="metadata-value">{{ formatDate(selectedAlert.createdAt) }}</span>
            </div>
            <div v-if="selectedAlert.resolvedAt" class="metadata-item">
              <span class="metadata-label">Resuelta</span>
              <span class="metadata-value">{{ formatDate(selectedAlert.resolvedAt) }}</span>
            </div>
          </div>
        </div>

        <Divider />

        <!-- Acciones -->
        <div class="detail-section">
          <h4>Acciones</h4>
          <div class="detail-actions">
            <Button
              v-if="isAlertOpenStatus(selectedAlert.status)"
              label="Marcar como resuelta"
              icon="pi pi-check"
              severity="success"
              class="w-full"
              @click="onResolveAlert(selectedAlert)"
            />
            <Button
              v-if="isAlertOpenStatus(selectedAlert.status)"
              label="Descartar alerta"
              icon="pi pi-times"
              severity="secondary"
              outlined
              class="w-full"
              @click="onDismissAlert(selectedAlert)"
            />
            <Button
              v-if="!isAlertOpenStatus(selectedAlert.status)"
              label="Reabrir alerta"
              icon="pi pi-replay"
              outlined
              class="w-full"
              @click="onReopenAlert(selectedAlert)"
            />
          </div>
        </div>
      </div>
    </Drawer>

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
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Panel from 'primevue/panel'
import Divider from 'primevue/divider'
import AlertList from '@/components/AlertList.vue'
import type { Alert } from '@/types'
import type { ApiAlert } from '@/types/api'
import { transformAlerts } from '@/types/transformers'
import { useToast } from 'primevue/usetoast'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { api } from '@/services/apiClient'

const { getSeverityConfig, getCategoryConfig, getStatusConfig } = useAlertUtils()

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const toast = useToast()

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

// Helper para verificar si una alerta está "abierta" (no resuelta/descartada)
const isAlertOpenStatus = (status: string): boolean => {
  // Domain status: active, dismissed, resolved
  return status === 'active'
}

// Computed stats
const criticalCount = computed(() =>
  alerts.value.filter(a => a.severity === 'critical' && isAlertOpenStatus(a.status)).length
)

const warningCount = computed(() =>
  alerts.value.filter(a => a.severity === 'high' && isAlertOpenStatus(a.status)).length
)

const infoCount = computed(() =>
  alerts.value.filter(a => a.severity === 'info' && isAlertOpenStatus(a.status)).length
)

const resolvedCount = computed(() =>
  alerts.value.filter(a => a.status === 'resolved').length
)

const openAlertsCount = computed(() =>
  alerts.value.filter(a => isAlertOpenStatus(a.status)).length
)

// Funciones
const loadAlerts = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await api.getRaw<{ success: boolean; data?: ApiAlert[]; error?: string }>(`/api/projects/${projectId.value}/alerts`)

    if (data.success) {
      // Transform API response to domain types
      alerts.value = transformAlerts(data.data || [])
    } else {
      error.value = 'Error cargando alertas'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo completar la operación'
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
    const data = await api.postRaw<{ success: boolean }>(`/api/projects/${projectId.value}/alerts/${alert.id}/resolve`)

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
    const data = await api.postRaw<{ success: boolean }>(`/api/projects/${projectId.value}/alerts/${alert.id}/dismiss`)

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
    const data = await api.postRaw<{ success: boolean }>(`/api/projects/${projectId.value}/alerts/${alert.id}/reopen`)

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
    const data = await api.postRaw<{ success: boolean }>(`/api/projects/${projectId.value}/alerts/resolve-all`)

    if (data.success) {
      showResolveAllDialog.value = false
      await loadAlerts()
    }
  } catch (err) {
    console.error('Error resolving all alerts:', err)
  }
}

const exportAlerts = () => {
  if (!alerts.value || alerts.value.length === 0) {
    toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'No hay alertas para exportar', life: 4000 })
    return
  }

  try {
    const content = {
      projectId: projectId.value,
      exportedAt: new Date().toISOString(),
      totalAlerts: alerts.value.length,
      bySeverity: {
        critical: alerts.value.filter(a => a.severity === 'critical').length,
        high: alerts.value.filter(a => a.severity === 'high').length,
        medium: alerts.value.filter(a => a.severity === 'medium').length,
        low: alerts.value.filter(a => a.severity === 'low').length,
        info: alerts.value.filter(a => a.severity === 'info').length,
      },
      byStatus: {
        active: alerts.value.filter(a => a.status === 'active').length,
        resolved: alerts.value.filter(a => a.status === 'resolved').length,
        dismissed: alerts.value.filter(a => a.status === 'dismissed').length,
      },
      alerts: alerts.value.map(a => ({
        id: a.id,
        title: a.title,
        description: a.description,
        severity: a.severity,
        category: a.category,
        status: a.status,
        chapter: a.chapter,
        confidence: a.confidence,
        createdAt: a.createdAt,
      })),
    }

    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alertas_proyecto_${projectId.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Error exporting alerts:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar alertas', life: 5000 })
  }
}

// Helpers
const getSeverityColor = (severity: string): string => {
  // Domain severity: critical, high, medium, low, info
  const colors: Record<string, string> = {
    'critical': 'danger',
    'high': 'warning',
    'medium': 'info',
    'low': 'secondary',
    'info': 'info'
  }
  return colors[severity] || 'secondary'
}

// Usar composable centralizado
const getSeverityIcon = (severity: string): string => {
  return getSeverityConfig(severity as any).icon
}

const getCategoryLabel = (category: string): string => {
  return getCategoryConfig(category as any).label
}

const getStatusSeverity = (status: string): string => {
  // Map to PrimeVue Tag severity values
  const primeVueMap: Record<string, string> = {
    'active': 'warning',
    'resolved': 'success',
    'dismissed': 'secondary'
  }
  return primeVueMap[status] || 'secondary'
}

const getStatusLabel = (status: string): string => {
  return getStatusConfig(status as any).label
}

const formatDate = (date: Date | string | undefined): string => {
  if (!date) return 'N/A'
  const dateObj = typeof date === 'string' ? new Date(date) : date
  return dateObj.toLocaleDateString('es-ES', {
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
  background: var(--p-surface-0, white);
  border-bottom: 1px solid var(--p-surface-border, #e2e8f0);
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
  color: var(--p-text-color);
}

.header-info p {
  margin: 0.25rem 0 0 0;
  color: var(--p-text-color-secondary, #64748b);
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
  background: var(--p-surface-0, white);
  border-bottom: 1px solid var(--p-surface-border, #e2e8f0);
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

/* Drawer de detalles */
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
