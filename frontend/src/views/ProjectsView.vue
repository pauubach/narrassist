<template>
  <div class="projects-view">
    <div class="header">
      <div class="header-left">
        <h1>Proyectos</h1>
      </div>
      <div class="header-right">
        <DsInput
          v-model="searchQuery"
          placeholder="Buscar proyectos..."
          icon="pi pi-search"
          clearable
          class="search-input"
        />
        <Select
          v-model="sortBy"
          :options="sortOptions"
          option-label="label"
          option-value="value"
          placeholder="Ordenar por"
          class="sort-dropdown"
          append-to="self"
        />
        <Button
          label="Nuevo Proyecto"
          icon="pi pi-plus"
          severity="success"
          @click="showCreateDialog = true"
        />
      </div>
    </div>

    <div class="content">
      <!-- Estado: Cargando -->
      <div v-if="projectsStore.loading" class="loading-state">
        <ProgressSpinner />
        <p>Cargando proyectos...</p>
      </div>

      <!-- Estado: Error -->
      <Message v-else-if="projectsStore.error" severity="error" :closable="false" class="error-message">
        <p>{{ projectsStore.error }}</p>
        <Button
          label="Reintentar"
          icon="pi pi-refresh"
          text
          @click="loadProjects"
        />
      </Message>

      <!-- Estado: Sin proyectos -->
      <div v-else-if="!projectsStore.hasProjects" class="empty-state">
        <i class="pi pi-folder-open empty-icon"></i>
        <h2>No hay proyectos</h2>
        <p>Crea tu primer proyecto para comenzar a analizar un manuscrito</p>
        <Button
          label="Crear Primer Proyecto"
          icon="pi pi-plus"
          size="large"
          @click="showCreateDialog = true"
        />
      </div>

      <!-- Estado: Lista de proyectos -->
      <div v-else class="projects-list">
        <!-- Grid de proyectos -->
        <div class="projects-grid">
          <Card
            v-for="project in filteredProjects"
            :key="project.id"
            class="project-card"
            @click="openProject(project.id)"
          >
            <template #header>
              <div class="card-header">
                <div class="format-badge">
                  <i :class="getFormatIcon(project.documentFormat)"></i>
                  {{ project.documentFormat }}
                </div>
                <div class="card-actions">
                  <Badge
                    v-if="project.openAlertsCount && project.openAlertsCount > 0"
                    :value="project.openAlertsCount"
                    :severity="getAlertSeverity(project.highestAlertSeverity)"
                    class="alert-badge"
                  />
                  <Button
                    icon="pi pi-ellipsis-v"
                    text
                    rounded
                    @click.stop="showProjectMenu($event, project)"
                  />
                </div>
              </div>
            </template>

            <template #title>
              {{ project.name }}
            </template>

            <template #subtitle>
              <div class="project-meta">
                <span><i class="pi pi-calendar"></i> {{ formatDate(project.lastModified) }}</span>
              </div>
            </template>

            <template #content>
              <div class="project-stats">
                <div class="stat">
                  <span class="stat-value">{{ project.wordCount.toLocaleString() }}</span>
                  <span class="stat-label">palabras</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ project.chapterCount }}</span>
                  <span class="stat-label">capítulos</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ project.analysisProgress ?? 0 }}%</span>
                  <span class="stat-label">analizado</span>
                </div>
              </div>

              <ProgressBar
                v-if="(project.analysisProgress ?? 0) < 100"
                :value="project.analysisProgress ?? 0"
                :show-value="false"
                class="mt-3"
              />
            </template>

            <template #footer>
              <div class="card-footer">
                <Button
                  label="Abrir"
                  icon="pi pi-arrow-right"
                  text
                  @click.stop="openProject(project.id)"
                />
              </div>
            </template>
          </Card>
        </div>
      </div>
    </div>

    <!-- Diálogo: Crear proyecto -->
    <Dialog
      v-model:visible="showCreateDialog"
      modal
      header="Nuevo Proyecto"
      :style="{ width: '500px' }"
    >
      <div class="create-dialog">
        <div class="field">
          <label for="project-name">Nombre del proyecto *</label>
          <InputText
            id="project-name"
            v-model="newProject.name"
            placeholder="Ej: Mi Novela - Borrador 1"
            class="w-full"
            :class="{ 'p-invalid': !newProject.name && showValidation }"
          />
          <small v-if="!newProject.name && showValidation" class="p-error">
            El nombre es obligatorio
          </small>
        </div>

        <div class="field">
          <label for="project-description">Descripción (opcional)</label>
          <Textarea
            id="project-description"
            v-model="newProject.description"
            rows="3"
            placeholder="Breve descripción del manuscrito..."
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Documento *</label>
          <FileUpload
            mode="basic"
            accept=".docx,.doc,.txt,.md,.pdf,.epub"
            :max-file-size="50000000"
            :auto="false"
            choose-label="Seleccionar archivo"
            :class="{ 'p-invalid': !newProject.file && showValidation }"
            @select="onFileSelect"
          />
          <small class="p-text-secondary">
            Formatos soportados: DOCX, DOC, TXT, MD, PDF, EPUB (máx. 50 MB)
          </small>
          <small v-if="!newProject.file && showValidation" class="p-error block">
            Debes seleccionar un archivo
          </small>
          <div v-if="newProject.file" class="selected-file">
            <i class="pi pi-file"></i>
            <span>{{ newProject.file.name }}</span>
            <Button icon="pi pi-times" text rounded @click="newProject.file = null" />
          </div>
        </div>

        <div class="field">
          <label for="project-rules">Normas y preferencias (opcional)</label>
          <Textarea
            id="project-rules"
            v-model="newProject.rules"
            rows="4"
            placeholder="Ej: Usar coma antes de 'pero'. Evitar gerundios al inicio de frase. Los diálogos usan raya (—). Verificar concordancia de tiempos verbales..."
            class="w-full"
          />
          <small class="p-text-secondary">
            Normas editoriales, preferencias de estilo o criterios específicos para este manuscrito
          </small>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="closeCreateDialog"
        />
        <Button
          label="Crear y Analizar"
          icon="pi pi-check"
          :loading="creatingProject"
          @click="createProject"
        />
      </template>
    </Dialog>

    <!-- Menu contextual de proyecto -->
    <Menu ref="projectMenu" :model="projectMenuItems" :popup="true" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useAnalysisStore } from '@/stores/analysis'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import DsInput from '@/components/ds/DsInput.vue'
import FileUpload from 'primevue/fileupload'
import Select from 'primevue/select'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Menu from 'primevue/menu'
import Badge from 'primevue/badge'
import { useToast } from 'primevue/usetoast'
import type { Project } from '@/types'
import { apiUrl } from '@/config/api'

const router = useRouter()
const toast = useToast()
const projectsStore = useProjectsStore()
const analysisStore = useAnalysisStore()

// Estado de la vista
const showCreateDialog = ref(false)
const showValidation = ref(false)
const creatingProject = ref(false)
const searchQuery = ref('')
const sortBy = ref('lastModified')
const projectMenu = ref()
const selectedProject = ref<Project | null>(null)

// Opciones de ordenamiento - using domain camelCase properties
const sortOptions = [
  { label: 'Última modificación', value: 'lastModified' },
  { label: 'Nombre', value: 'name' },
  { label: 'Fecha de creación', value: 'createdAt' },
  { label: 'Progreso', value: 'analysisProgress' }
]

// Formulario de nuevo proyecto
const newProject = ref({
  name: '',
  description: '',
  file: null as File | null,
  rules: ''
})

// Items del menú contextual
const projectMenuItems = computed(() => [
  {
    label: 'Abrir',
    icon: 'pi pi-folder-open',
    command: () => selectedProject.value && openProject(selectedProject.value.id)
  },
  {
    label: 'Re-analizar',
    icon: 'pi pi-refresh',
    command: () => console.log('Re-analyze')
  },
  { separator: true },
  {
    label: 'Exportar',
    icon: 'pi pi-download',
    command: () => console.log('Export')
  },
  { separator: true },
  {
    label: 'Eliminar',
    icon: 'pi pi-trash',
    command: () => selectedProject.value && deleteProject(selectedProject.value.id),
    class: 'text-red-500'
  }
])

// Proyectos filtrados y ordenados
const filteredProjects = computed(() => {
  let filtered = projectsStore.projects

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.description?.toLowerCase().includes(query)
    )
  }

  // Ordenar - using domain property names (camelCase)
  return [...filtered].sort((a, b) => {
    switch (sortBy.value) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'createdAt':
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      case 'analysisProgress':
        return b.analysisProgress - a.analysisProgress
      case 'lastModified':
      default:
        return new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime()
    }
  })
})

// Funciones
const loadProjects = async () => {
  await projectsStore.fetchProjects()
}

const openProject = (projectId: number) => {
  router.push({ name: 'project', params: { id: projectId } })
}

const onFileSelect = (event: any) => {
  newProject.value.file = event.files[0]
  showValidation.value = false
}

const createProject = async () => {
  showValidation.value = true

  if (!newProject.value.name || !newProject.value.file) {
    return
  }

  creatingProject.value = true
  const fileToAnalyze = newProject.value.file

  try {
    const project = await projectsStore.createProject(
      newProject.value.name,
      newProject.value.description,
      newProject.value.file,
      newProject.value.rules
    )

    if (project) {
      // Cerrar diálogo inmediatamente
      closeCreateDialog()

      // Navegar al proyecto INMEDIATAMENTE (análisis no bloqueante)
      // El documento será visible desde el primer momento
      // El análisis correrá en background con progreso en StatusBar
      router.push({ name: 'project', params: { id: project.id } })

      // Iniciar análisis en background (no bloquea la navegación)
      if (fileToAnalyze) {
        analysisStore.startAnalysis(project.id, fileToAnalyze).catch((error) => {
          console.error('Error starting analysis:', error)
          toast.add({
            severity: 'error',
            summary: 'Error al iniciar análisis',
            detail: 'El análisis no pudo iniciarse. Puedes intentar re-analizar desde el proyecto.',
            life: 5000
          })
        })
      }
    } else {
      closeCreateDialog()
    }
  } catch (error) {
    console.error('Error creating project:', error)
    toast.add({
      severity: 'error',
      summary: 'Error al crear proyecto',
      detail: error instanceof Error ? error.message : 'Error desconocido',
      life: 5000
    })
    closeCreateDialog()
  } finally {
    creatingProject.value = false
  }
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  showValidation.value = false
  newProject.value = {
    name: '',
    description: '',
    file: null,
    rules: ''
  }
}

const showProjectMenu = (event: Event, project: Project) => {
  selectedProject.value = project
  projectMenu.value.toggle(event)
}

const deleteProject = async (projectId: number) => {
  if (!selectedProject.value) return

  // Mostrar confirmación
  const confirmed = confirm(
    `¿Estás seguro de que deseas eliminar el proyecto "${selectedProject.value.name}"?\n\nEsta acción no se puede deshacer.`
  )

  if (!confirmed) return

  try {
    // Llamar al endpoint DELETE
    const response = await fetch(apiUrl(`/api/projects/${projectId}`), {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('Error al eliminar el proyecto')
    }

    // Recargar la lista de proyectos
    await projectsStore.fetchProjects()
  } catch (error) {
    console.error('Error deleting project:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al eliminar el proyecto. Por favor, inténtalo de nuevo.', life: 5000 })
  }
}

const getFormatIcon = (format: string) => {
  const icons: Record<string, string> = {
    'DOCX': 'pi pi-file-word',
    'TXT': 'pi pi-file',
    'MD': 'pi pi-file-edit'
  }
  return icons[format] || 'pi pi-file'
}

const formatDate = (date: Date | string) => {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - dateObj.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Hoy'
  if (diffDays === 1) return 'Ayer'
  if (diffDays < 7) return `Hace ${diffDays} días`

  return dateObj.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })
}

const getAlertSeverity = (severity?: string | null) => {
  if (!severity) return undefined

  // Domain AlertSeverity: critical, high, medium, low, info
  const severityMap: Record<string, 'danger' | 'warning' | 'info' | 'secondary'> = {
    'critical': 'danger',
    'high': 'warning',
    'medium': 'info',
    'low': 'secondary',
    'info': 'info'
  }

  return severityMap[severity] || 'secondary'
}

// Handle menu event for new project
const handleNewProjectEvent = () => {
  showCreateDialog.value = true
}

// Lifecycle
onMounted(async () => {
  window.addEventListener('menubar:new-project', handleNewProjectEvent)
  await loadProjects()
})

onUnmounted(() => {
  window.removeEventListener('menubar:new-project', handleNewProjectEvent)
})
</script>

<style scoped>
.projects-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  flex-shrink: 0;
}

.header-left h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-color);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 300px;
  padding-right: 2.5rem;
  height: 2.5rem; /* Match button and dropdown height */
}

/* Ensure all header controls have consistent height */
.header-right .p-button {
  height: 2.5rem;
}

.header-right .p-dropdown,
.header-right .p-select {
  height: 2.5rem;
}

.search-wrapper .pi-search {
  position: absolute;
  right: 1rem;
  color: var(--text-color-secondary);
}

.sort-dropdown {
  min-width: 200px;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

/* Estados vacíos */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.loading-state p {
  margin-top: 1rem;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 4rem;
  color: var(--text-color-secondary);
  opacity: 0.5;
  margin-bottom: 1rem;
}

.empty-state h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.empty-state p {
  color: var(--text-color-secondary);
  margin-bottom: 2rem;
}

/* Estado de error */
.error-message {
  margin: 0;
}

.error-message :deep(.p-message-wrapper) {
  padding: 1rem 1.25rem;
}

.error-message p {
  margin: 0 0 0.5rem 0;
  line-height: 1.5;
}

.error-message .p-button {
  margin-top: 0;
}

/* Grid de proyectos - usa auto-fit para llenar todo el ancho disponible */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 1.5rem;
}

/* Responsive: 1 columna en móviles */
@media (max-width: 768px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }
}

.project-card {
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
  height: 100%;
  border: 1px solid var(--surface-border);
}

.project-card:hover {
  background-color: var(--surface-hover);
  border-color: var(--primary-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
}

.format-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  background: var(--surface-0);
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.alert-badge {
  font-size: 0.75rem;
  min-width: 1.5rem;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.project-meta i {
  font-size: 0.75rem;
}

.project-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin: 1rem 0;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  margin-top: 0.25rem;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

/* Diálogo de creación */
.create-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  color: var(--text-color);
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 4px;
  margin-top: 0.5rem;
}

.selected-file i {
  color: var(--primary-color);
}

.selected-file span {
  flex: 1;
  font-size: 0.875rem;
}

/* Utilidades */
.w-full {
  width: 100%;
}

.mt-3 {
  margin-top: 1rem;
}

.block {
  display: block;
}

.text-red-500 {
  color: #ef4444;
}
</style>
