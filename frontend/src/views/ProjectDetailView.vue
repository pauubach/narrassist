<template>
  <div class="project-detail-view">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando proyecto...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <Message severity="error">{{ error }}</Message>
      <Button label="Volver a Proyectos" icon="pi pi-arrow-left" @click="goBack" />
    </div>

    <!-- Main content -->
    <div v-else-if="project" class="project-layout">
      <!-- Header -->
      <div class="project-header">
        <div class="header-left">
          <Button icon="pi pi-arrow-left" text rounded @click="goBack" />
          <div class="header-info">
            <h1>{{ project.name }}</h1>
            <p v-if="project.description" class="project-description">{{ project.description }}</p>
          </div>
        </div>
        <div class="header-actions">
          <Button label="Exportar" icon="pi pi-download" outlined @click="showExportDialog = true" />
          <Button label="Re-analizar" icon="pi pi-refresh" @click="showReanalyzeDialog = true" />
        </div>
      </div>

      <!-- Export Dialog -->
      <ExportDialog
        :visible="showExportDialog"
        @update:visible="showExportDialog = $event"
        :project-id="project.id"
        :project-name="project.name"
      />

      <!-- Reanalyze Confirmation Dialog -->
      <Dialog
        :visible="showReanalyzeDialog"
        @update:visible="showReanalyzeDialog = $event"
        header="Re-analizar documento"
        :modal="true"
        :style="{ width: '450px' }"
      >
        <div class="reanalyze-content">
          <p class="reanalyze-info">
            <i class="pi pi-info-circle"></i>
            Se volverá a analizar el documento original. Si el archivo ha sido modificado, los cambios se detectarán automáticamente.
          </p>
        </div>

        <template #footer>
          <Button
            label="Cancelar"
            icon="pi pi-times"
            text
            @click="showReanalyzeDialog = false"
          />
          <Button
            label="Re-analizar"
            icon="pi pi-refresh"
            :loading="reanalyzing"
            @click="startReanalysis"
          />
        </template>
      </Dialog>

      <!-- Stats Overview -->
      <div class="stats-overview">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-file stat-icon"></i>
              <div class="stat-details">
                <span class="stat-value">{{ project.word_count.toLocaleString() }}</span>
                <span class="stat-label">Palabras</span>
              </div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-book stat-icon"></i>
              <div class="stat-details">
                <span class="stat-value">{{ project.chapter_count }}</span>
                <span class="stat-label">Capítulos</span>
              </div>
            </div>
          </template>
        </Card>

        <Card class="stat-card stat-card-clickable" @click="goToEntities">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-users stat-icon"></i>
              <div class="stat-details">
                <span class="stat-value">{{ entitiesCount }}</span>
                <span class="stat-label">Entidades</span>
              </div>
              <i class="pi pi-arrow-right stat-arrow"></i>
            </div>
          </template>
        </Card>

        <Card class="stat-card stat-card-clickable" @click="goToAlerts">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-exclamation-triangle stat-icon"></i>
              <div class="stat-details">
                <span class="stat-value">{{ alertsCount }}</span>
                <span class="stat-label">Alertas</span>
              </div>
              <i class="pi pi-arrow-right stat-arrow"></i>
            </div>
          </template>
        </Card>
      </div>

      <!-- Main Dashboard -->
      <div class="dashboard-content">
        <!-- Left Panel: Chapter Tree -->
        <div class="left-panel">
          <ChapterTree
            :chapters="chapters"
            :loading="loading"
            :active-chapter-id="activeChapterId"
            @chapter-select="onChapterSelect"
            @refresh="loadChapters(project.id)"
          />
        </div>

        <!-- Center Panel: Document Viewer -->
        <div class="center-panel">
          <DocumentViewer
            :project-id="project.id"
            :document-title="project.name"
            :highlight-entity-id="highlightedEntityId"
            :scroll-to-chapter-id="scrollToChapterId"
            @chapter-visible="onChapterVisible"
            @entity-click="onEntityClick"
          />
        </div>

        <!-- Right Panel: Alerts/Details -->
        <div class="right-panel">
          <TabView value="0">
            <TabPanel value="0">
              <template #header>
                <span class="tab-header">
                  <i class="pi pi-exclamation-triangle"></i>
                  Alertas ({{ alertsCount }})
                </span>
              </template>
              <div class="alerts-list">
                <div
                  v-for="alert in alerts"
                  :key="alert.id"
                  class="alert-item"
                  :class="`alert-${alert.severity}`"
                >
                  <div class="alert-header">
                    <Tag :severity="getSeverityColor(alert.severity)">
                      {{ alert.severity.toUpperCase() }}
                    </Tag>
                    <span class="alert-title">{{ alert.title }}</span>
                  </div>
                  <p class="alert-description">{{ alert.description }}</p>
                  <div class="alert-footer">
                    <small v-if="alert.chapter">Cap. {{ alert.chapter }}</small>
                    <Button label="Ver" size="small" text />
                  </div>
                </div>
                <div v-if="alerts.length === 0" class="empty-message">
                  No hay alertas
                </div>
              </div>
            </TabPanel>

            <TabPanel value="1">
              <template #header>
                <span class="tab-header">
                  <i class="pi pi-chart-bar"></i>
                  Resumen
                </span>
              </template>
              <div class="summary-content">
                <div class="summary-section">
                  <h4>Análisis Completo</h4>
                  <ProgressBar :value="project.analysis_progress" :showValue="true" />
                  <p class="summary-note">
                    Última modificación: {{ formatDate(project.last_modified) }}
                  </p>
                </div>

                <Divider />

                <div class="summary-section">
                  <h4>Distribución de Alertas</h4>
                  <div class="alert-distribution">
                    <div class="distribution-item">
                      <div class="item-label">
                        <i class="pi pi-exclamation-circle alert-icon-critical"></i>
                        <span>Críticas</span>
                      </div>
                      <span class="item-value">{{ criticalAlertsCount }}</span>
                    </div>
                    <div class="distribution-item">
                      <div class="item-label">
                        <i class="pi pi-exclamation-triangle alert-icon-warning"></i>
                        <span>Advertencias</span>
                      </div>
                      <span class="item-value">{{ warningAlertsCount }}</span>
                    </div>
                    <div class="distribution-item">
                      <div class="item-label">
                        <i class="pi pi-info-circle alert-icon-info"></i>
                        <span>Info</span>
                      </div>
                      <span class="item-value">{{ infoAlertsCount }}</span>
                    </div>
                  </div>
                </div>

                <Divider v-if="entitiesWithCount.length > 0" />

                <div v-if="entitiesWithCount.length > 0" class="summary-section">
                  <h4>Entidades por Tipo</h4>
                  <div class="entity-distribution">
                    <div v-for="entityType in entitiesWithCount" :key="entityType.type" class="distribution-item">
                      <div class="item-label">
                        <i :class="entityType.icon" class="entity-icon"></i>
                        <span>{{ entityType.label }}</span>
                      </div>
                      <span class="item-value">{{ entityType.count }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </TabPanel>

            <TabPanel value="2">
              <template #header>
                <span class="tab-header">
                  <i class="pi pi-share-alt"></i>
                  Relaciones
                </span>
              </template>
              <div class="relationships-panel">
                <RelationshipGraph
                  v-if="project"
                  :project-id="project.id"
                  @entity-select="onRelationEntitySelect"
                />
              </div>
            </TabPanel>
          </TabView>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import Message from 'primevue/message'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import Dialog from 'primevue/dialog'
import ChapterTree from '@/components/ChapterTree.vue'
import DocumentViewer from '@/components/DocumentViewer.vue'
import ExportDialog from '@/components/ExportDialog.vue'
import RelationshipGraph from '@/components/RelationshipGraph.vue'
import type { Entity, Alert } from '@/types'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

const loading = ref(true)
const error = ref('')
const showExportDialog = ref(false)
const showReanalyzeDialog = ref(false)
const reanalyzing = ref(false)
const entities = ref<Entity[]>([])
const alerts = ref<Alert[]>([])
const chapters = ref<Array<{ id: number; title: string; chapter_number: number; word_count: number; position_start: number; position_end: number; project_id: number }>>([])

// Estado para sincronización
const activeChapterId = ref<number | null>(null)
const highlightedEntityId = ref<number | null>(null)
const scrollToChapterId = ref<number | null>(null)

const project = computed(() => projectsStore.currentProject)

// Computed stats
const entitiesCount = computed(() => entities.value.length)
const alertsCount = computed(() => alerts.value.length)
const criticalAlertsCount = computed(() => alerts.value.filter(a => a.severity === 'critical').length)
const warningAlertsCount = computed(() => alerts.value.filter(a => a.severity === 'warning').length)
const infoAlertsCount = computed(() => alerts.value.filter(a => a.severity === 'info').length)

// Definición de todos los tipos de entidades con sus iconos
const entityTypesList = [
  // Seres vivos
  { type: 'CHARACTER', label: 'Personajes', icon: 'pi pi-user' },
  { type: 'ANIMAL', label: 'Animales', icon: 'pi pi-heart' },
  { type: 'CREATURE', label: 'Criaturas', icon: 'pi pi-moon' },
  // Lugares
  { type: 'LOCATION', label: 'Lugares', icon: 'pi pi-map-marker' },
  { type: 'BUILDING', label: 'Edificios', icon: 'pi pi-home' },
  { type: 'REGION', label: 'Regiones', icon: 'pi pi-globe' },
  // Objetos
  { type: 'OBJECT', label: 'Objetos', icon: 'pi pi-box' },
  { type: 'VEHICLE', label: 'Vehículos', icon: 'pi pi-car' },
  // Grupos
  { type: 'ORGANIZATION', label: 'Organizaciones', icon: 'pi pi-building' },
  { type: 'FACTION', label: 'Facciones', icon: 'pi pi-flag' },
  { type: 'FAMILY', label: 'Familias', icon: 'pi pi-users' },
  // Temporales
  { type: 'EVENT', label: 'Eventos', icon: 'pi pi-calendar' },
  { type: 'TIME_PERIOD', label: 'Períodos', icon: 'pi pi-clock' },
  // Conceptuales
  { type: 'CONCEPT', label: 'Conceptos', icon: 'pi pi-lightbulb' },
  { type: 'RELIGION', label: 'Religiones', icon: 'pi pi-star' },
  { type: 'MAGIC_SYSTEM', label: 'Sistemas mágicos', icon: 'pi pi-sparkles' },
  // Culturales
  { type: 'WORK', label: 'Obras', icon: 'pi pi-book' },
  { type: 'TITLE', label: 'Títulos', icon: 'pi pi-crown' },
  { type: 'LANGUAGE', label: 'Idiomas', icon: 'pi pi-comment' }
]

// Función para obtener el conteo de entidades por tipo
const getEntityCount = (type: string) => {
  return entities.value.filter(e => e.entity_type === type).length
}

// Computed: solo mostrar tipos de entidades que tienen count > 0
const entitiesWithCount = computed(() => {
  return entityTypesList
    .map(entityType => ({
      ...entityType,
      count: getEntityCount(entityType.type)
    }))
    .filter(entityType => entityType.count > 0)
})

onMounted(async () => {
  const projectId = parseInt(route.params.id as string)

  if (isNaN(projectId)) {
    error.value = 'ID de proyecto inválido'
    loading.value = false
    return
  }

  try {
    await projectsStore.fetchProject(projectId)

    // Cargar entidades y alertas (stub por ahora)
    await loadEntities(projectId)
    await loadAlerts(projectId)
    await loadChapters(projectId)

    loading.value = false
  } catch (err) {
    error.value = projectsStore.error || 'Error cargando proyecto'
    loading.value = false
  }
})

const loadEntities = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/entities`)
    const data = await response.json()
    if (data.success) {
      entities.value = data.data || []
    }
  } catch (err) {
    console.error('Error loading entities:', err)
  }
}

const loadAlerts = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/alerts?status=open`)
    const data = await response.json()
    if (data.success) {
      alerts.value = data.data || []
    }
  } catch (err) {
    console.error('Error loading alerts:', err)
  }
}

const loadChapters = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/chapters`)
    const data = await response.json()
    if (data.success) {
      chapters.value = data.data || []
    }
  } catch (err) {
    console.error('Error loading chapters:', err)
    // Fallback a stub si el endpoint no está disponible
    if (project.value) {
      chapters.value = Array.from({ length: project.value.chapter_count }, (_, i) => ({
        id: i + 1,
        project_id: projectId,
        title: `Capítulo ${i + 1}`,
        chapter_number: i + 1,
        word_count: Math.floor(project.value!.word_count / project.value!.chapter_count),
        position_start: 0,
        position_end: 0
      }))
    }
  }
}

const goBack = () => {
  router.push({ name: 'projects' })
}

const goToEntities = () => {
  const projectId = route.params.id
  router.push({ name: 'entities', params: { id: projectId } })
}

const goToAlerts = () => {
  const projectId = route.params.id
  router.push({ name: 'alerts', params: { id: projectId } })
}

// Sincronización entre chapter tree y document viewer
const onChapterSelect = (chapterId: number) => {
  scrollToChapterId.value = chapterId
  activeChapterId.value = chapterId
  // Reset después de scroll
  setTimeout(() => {
    scrollToChapterId.value = null
  }, 500)
}

const onChapterVisible = (chapterId: number) => {
  activeChapterId.value = chapterId
}

// Sincronización de entidades
const onEntityClick = (entityId: number) => {
  highlightedEntityId.value = entityId
  // También actualizar el panel de alertas si hay alertas relacionadas
  console.log('Entity clicked:', entityId)
}

// Selección desde el grafo de relaciones
const onRelationEntitySelect = (entityId: number) => {
  highlightedEntityId.value = entityId
  // Navegar a la entidad en la lista de entidades
  const entity = entities.value.find(e => e.id === entityId)
  if (entity) {
    console.log('Relation entity selected:', entity.canonical_name)
  }
}

const getEntityIcon = (type: string) => {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building'
  }
  return icons[type] || 'pi pi-tag'
}

const getSeverityColor = (severity: string) => {
  const colors: Record<string, string> = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info',
    'hint': 'secondary'
  }
  return colors[severity] || 'secondary'
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Re-analyze functions
const startReanalysis = async () => {
  if (!project.value) return

  reanalyzing.value = true
  showReanalyzeDialog.value = false

  try {
    const response = await fetch(`/api/projects/${project.value.id}/reanalyze`, {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      // Recargar datos del proyecto
      await projectsStore.fetchProject(project.value.id)
      await loadEntities(project.value.id)
      await loadAlerts(project.value.id)
      await loadChapters(project.value.id)
    } else {
      console.error('Error en re-análisis:', data.error)
      error.value = data.error || 'Error al re-analizar el documento'
    }
  } catch (err) {
    console.error('Error en re-análisis:', err)
    error.value = 'Error de conexión al re-analizar'
  } finally {
    reanalyzing.value = false
  }
}
</script>

<style scoped>
.project-detail-view {
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
  overflow: hidden;
}

/* Loading & Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
}

/* Layout */
.project-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0; /* Crítico para que flex children no desborden */
}

/* Header */
.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: var(--surface-card);
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

.project-description {
  margin: 0.25rem 0 0 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

/* Stats Overview */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  padding: 1.5rem 2rem;
  background: var(--surface-section);
  flex-shrink: 0; /* No permitir que se encoja */
}

.stat-card {
  border: none;
}

.stat-card-clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card-clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem;
  position: relative;
}

.stat-arrow {
  margin-left: auto;
  color: var(--primary-color);
  opacity: 0;
  transition: opacity 0.2s;
}

.stat-card-clickable:hover .stat-arrow {
  opacity: 1;
}

.stat-icon {
  font-size: 2rem;
  color: var(--primary-color);
  opacity: 0.8;
}

.stat-details {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

/* Dashboard Content */
.dashboard-content {
  flex: 1;
  display: grid;
  grid-template-columns: 250px 1fr 350px;
  grid-template-rows: 1fr;
  gap: 1rem;
  padding: 1rem 2rem;
  overflow: hidden;
  min-height: 0; /* Importante para que flex + grid funcionen correctamente */
}

/* Panels */
.left-panel,
.center-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  min-height: 0; /* Permite que el contenido se encoja */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

/* Left and center panels now use dedicated components (ChapterTree, DocumentViewer) */

/* Alerts List */
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  max-height: 600px;
  overflow-y: auto;
}

.alert-item {
  padding: 1rem 1.25rem;
  border-radius: 6px;
  border-left: 4px solid;
  background: var(--surface-50);
}

.alert-item.alert-critical {
  border-left-color: var(--red-500);
}

.alert-item.alert-warning {
  border-left-color: var(--yellow-500);
}

.alert-item.alert-info {
  border-left-color: var(--blue-500);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.alert-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.alert-description {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0.5rem 0;
  line-height: 1.4;
}

.alert-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.alert-footer small {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

/* Summary */
.summary-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  max-height: calc(100vh - 250px);
  overflow-y: auto;
}

.summary-section {
  padding: 0;
}

.summary-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.summary-note {
  margin: 0.5rem 0 0 0;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.alert-distribution,
.entity-distribution {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.distribution-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-radius: 4px;
}

.distribution-item .item-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.distribution-item .item-value {
  font-weight: 700;
  font-size: 1.125rem;
  color: var(--text-color);
}

/* Iconos de alertas con colores */
.alert-icon-critical {
  color: #ef4444;
  font-size: 1.25rem;
}

.alert-icon-warning {
  color: #f59e0b;
  font-size: 1.25rem;
}

.alert-icon-info {
  color: #3b82f6;
  font-size: 1.25rem;
}

/* Iconos de entidades */
.entity-icon {
  color: var(--primary-color);
  font-size: 1.125rem;
}

/* Empty States */
.empty-message {
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Tab Headers */
.tab-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Reanalyze Dialog */
.reanalyze-content {
  padding: 0.5rem 0;
}

.reanalyze-info {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--blue-50);
  border-radius: 6px;
  border-left: 4px solid var(--blue-500);
  margin: 0;
  color: var(--blue-900);
  font-size: 0.9rem;
  line-height: 1.5;
}

.reanalyze-info i {
  color: var(--blue-600);
  font-size: 1.25rem;
  margin-top: 0.1rem;
}

/* Relationships Panel */
.relationships-panel {
  height: calc(100vh - 320px);
  min-height: 400px;
  display: flex;
  flex-direction: column;
}
</style>
