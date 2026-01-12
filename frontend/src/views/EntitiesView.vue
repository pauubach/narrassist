<template>
  <div class="entities-view">
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
          <h1>Entidades</h1>
          <p v-if="project">{{ project.name }}</p>
        </div>
      </div>
      <div class="header-actions">
        <Button
          label="Exportar"
          icon="pi pi-download"
          outlined
          @click="exportEntities"
        />
        <Button
          label="Fusionar entidades"
          icon="pi pi-link"
          @click="showMergeDialog = true"
          :disabled="selectedEntities.length < 2"
        />
      </div>
    </div>

    <!-- Stats rápidas -->
    <div class="stats-bar">
      <div class="stat-item">
        <i class="pi pi-users"></i>
        <span class="stat-value">{{ entities.length }}</span>
        <span class="stat-label">Total entidades</span>
      </div>
      <div class="stat-item">
        <i class="pi pi-user"></i>
        <span class="stat-value">{{ charactersCount }}</span>
        <span class="stat-label">Personajes</span>
      </div>
      <div class="stat-item">
        <i class="pi pi-map-marker"></i>
        <span class="stat-value">{{ locationsCount }}</span>
        <span class="stat-label">Lugares</span>
      </div>
      <div class="stat-item">
        <i class="pi pi-building"></i>
        <span class="stat-value">{{ organizationsCount }}</span>
        <span class="stat-label">Organizaciones</span>
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="view-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <ProgressSpinner />
        <p>Cargando entidades...</p>
      </div>

      <!-- Error state -->
      <Message v-else-if="error" severity="error" :closable="false">
        {{ error }}
      </Message>

      <!-- Lista de entidades -->
      <EntityList
        v-else
        :entities="entities"
        :loading="loading"
        :show-title="false"
        :show-filters="true"
        :show-actions="true"
        :show-pagination="true"
        :selected-entity-id="selectedEntityId"
        @select="onEntitySelect"
        @view="onEntityView"
        @edit="onEntityEdit"
        @merge="onEntityMerge"
        @delete="onEntityDelete"
        @refresh="loadEntities"
      />
    </div>

    <!-- Sidebar con detalles de entidad seleccionada -->
    <Sidebar
      v-model:visible="showEntityDetails"
      position="right"
      :style="{ width: '400px' }"
      :modal="false"
      class="entity-sidebar"
      :pt="{
        content: { style: 'padding: 1.5rem' },
        header: { style: 'padding: 1rem 1.5rem' }
      }"
    >
      <template #header>
        <div class="sidebar-header">
          <h3>Detalles de Entidad</h3>
        </div>
      </template>

      <div v-if="selectedEntity" class="entity-details">
        <!-- Nombre y tipo -->
        <div class="detail-section">
          <div class="entity-header">
            <div class="entity-icon-large">
              <i :class="getEntityIcon(selectedEntity.entity_type)"></i>
            </div>
            <div class="entity-header-info">
              <h2>{{ selectedEntity.canonical_name }}</h2>
              <Tag :severity="getTypeSeverity(selectedEntity.entity_type)" class="type-tag">
                {{ getTypeLabel(selectedEntity.entity_type) }}
              </Tag>
            </div>
          </div>
        </div>

        <Divider />

        <!-- Aliases -->
        <div class="detail-section">
          <h4>Nombres alternativos</h4>
          <div v-if="selectedEntity.aliases && selectedEntity.aliases.length > 0" class="aliases-list">
            <span
              v-for="(alias, idx) in selectedEntity.aliases"
              :key="idx"
              class="alias-tag"
            >
              {{ alias }}
            </span>
          </div>
          <p v-else class="empty-text">No hay nombres alternativos registrados</p>
        </div>

        <Divider />

        <!-- Estadísticas -->
        <div class="detail-section">
          <h4>Estadísticas</h4>
          <div class="detail-stats">
            <div class="detail-stat">
              <span class="stat-label">Menciones totales</span>
              <span class="stat-value">{{ selectedEntity.mention_count || 0 }}</span>
            </div>
            <div class="detail-stat">
              <span class="stat-label">Primera mención</span>
              <span class="stat-value">
                {{ selectedEntity.first_mention_chapter ? `Capítulo ${selectedEntity.first_mention_chapter}` : 'N/A' }}
              </span>
            </div>
            <div class="detail-stat">
              <span class="stat-label">Importancia</span>
              <Tag :severity="getImportanceSeverity(selectedEntity.importance)" class="importance-tag">
                {{ getImportanceLabel(selectedEntity.importance) }}
              </Tag>
            </div>
          </div>
        </div>

        <Divider />

        <!-- Acciones -->
        <div class="detail-section">
          <h4>Acciones</h4>
          <div class="detail-actions">
            <Button
              label="Editar"
              icon="pi pi-pencil"
              outlined
              @click="onEntityEdit(selectedEntity)"
              class="w-full"
            />
            <Button
              label="Ver menciones"
              icon="pi pi-eye"
              outlined
              @click="viewMentions(selectedEntity)"
              class="w-full"
            />
            <Button
              label="Fusionar con otra"
              icon="pi pi-link"
              outlined
              @click="onEntityMerge(selectedEntity)"
              class="w-full"
            />
            <Button
              label="Eliminar"
              icon="pi pi-trash"
              severity="danger"
              outlined
              @click="onEntityDelete(selectedEntity)"
              class="w-full"
            />
          </div>
        </div>
      </div>
    </Sidebar>

    <!-- Diálogo de edición -->
    <Dialog
      v-model:visible="showEditDialog"
      modal
      header="Editar Entidad"
      :style="{ width: '500px' }"
    >
      <div v-if="editingEntity" class="edit-dialog">
        <div class="field">
          <label>Nombre canónico *</label>
          <InputText
            v-model="editingEntity.canonical_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Tipo de entidad</label>
          <Dropdown
            v-model="editingEntity.entity_type"
            :options="entityTypeOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Importancia</label>
          <SelectButton
            v-model="editingEntity.importance"
            :options="importanceOptions"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="field">
          <label>Nombres alternativos</label>
          <Chips
            v-model="editingEntity.aliases"
            placeholder="Añadir alias y presionar Enter"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="showEditDialog = false"
        />
        <Button
          label="Guardar"
          icon="pi pi-check"
          @click="saveEntity"
        />
      </template>
    </Dialog>

    <!-- Diálogo de fusión -->
    <MergeEntitiesDialog
      :visible="showMergeDialog"
      :project-id="projectId"
      :available-entities="entities"
      :preselected-entities="selectedEntities"
      @update:visible="showMergeDialog = $event"
      @merge="onMergeEntities"
      @cancel="showMergeDialog = false"
    />
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
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import SelectButton from 'primevue/selectbutton'
import Chips from 'primevue/chips'
import Chip from 'primevue/chip'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import EntityList from '@/components/EntityList.vue'
import MergeEntitiesDialog from '@/components/MergeEntitiesDialog.vue'
import type { Entity } from '@/types'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

// Estado
const loading = ref(true)
const error = ref('')
const entities = ref<Entity[]>([])
const selectedEntityId = ref<number | null>(null)
const selectedEntity = ref<Entity | null>(null)
const selectedEntities = ref<Entity[]>([])
const showEntityDetails = ref(false)
const showEditDialog = ref(false)
const showMergeDialog = ref(false)
const editingEntity = ref<Entity | null>(null)

const project = computed(() => projectsStore.currentProject)
const projectId = computed(() => parseInt(route.params.id as string))

// Opciones
const entityTypeOptions = [
  { label: 'Personaje', value: 'CHARACTER' },
  { label: 'Lugar', value: 'LOCATION' },
  { label: 'Organización', value: 'ORGANIZATION' },
  { label: 'Objeto', value: 'OBJECT' },
  { label: 'Evento', value: 'EVENT' }
]

const importanceOptions = [
  { label: 'Baja', value: 'low' },
  { label: 'Media', value: 'medium' },
  { label: 'Alta', value: 'high' }
]

// Computed stats
const charactersCount = computed(() =>
  entities.value.filter(e => e.entity_type === 'CHARACTER').length
)

const locationsCount = computed(() =>
  entities.value.filter(e => e.entity_type === 'LOCATION').length
)

const organizationsCount = computed(() =>
  entities.value.filter(e => e.entity_type === 'ORGANIZATION').length
)

// Funciones
const loadEntities = async () => {
  const projectId = parseInt(route.params.id as string)
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`/api/projects/${projectId}/entities`)
    const data = await response.json()

    if (data.success) {
      entities.value = data.data || []
    } else {
      error.value = 'Error cargando entidades'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  const projectId = route.params.id
  router.push({ name: 'project', params: { id: projectId } })
}

const onEntitySelect = (entity: Entity) => {
  selectedEntityId.value = entity.id
  selectedEntity.value = entity
  showEntityDetails.value = true
}

const onEntityView = (entity: Entity) => {
  // Si es un personaje, navegar a la ficha de personaje
  if (entity.entity_type === 'CHARACTER') {
    router.push({
      name: 'character',
      params: {
        projectId: projectId.value,
        id: entity.id
      }
    })
  } else {
    // Para otros tipos, mostrar sidebar
    selectedEntity.value = entity
    showEntityDetails.value = true
  }
}

const onEntityEdit = (entity: Entity) => {
  editingEntity.value = { ...entity }
  showEditDialog.value = true
}

const onEntityMerge = (entity: Entity) => {
  selectedEntities.value = [entity]
  showMergeDialog.value = true
}

const onEntityDelete = async (entity: Entity) => {
  // TODO: Implementar confirmación y eliminación
  console.log('Delete entity:', entity.id)
}

const saveEntity = async () => {
  // TODO: Implementar guardado de entidad
  console.log('Save entity:', editingEntity.value)
  showEditDialog.value = false
}

const viewMentions = (entity: Entity) => {
  // TODO: Navegar a vista de menciones o resaltar en documento
  console.log('View mentions:', entity.id)
}

const onMergeEntities = async (primaryEntityId: number, entityIdsToMerge: number[]) => {
  try {
    // TODO: Implementar endpoint de fusión
    const response = await fetch(`/api/projects/${projectId.value}/entities/merge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        primary_entity_id: primaryEntityId,
        entity_ids: entityIdsToMerge
      })
    })

    const data = await response.json()

    if (data.success) {
      showMergeDialog.value = false
      // Recargar entidades
      await loadEntities()
      console.log('Entities merged successfully')
    } else {
      console.error('Failed to merge entities:', data.error)
    }
  } catch (err) {
    console.error('Error merging entities:', err)
  }
}

const exportEntities = () => {
  // TODO: Implementar exportación
  console.log('Export entities')
}

const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building',
    'OBJECT': 'pi pi-box',
    'EVENT': 'pi pi-calendar'
  }
  return icons[type] || 'pi pi-tag'
}

const getTypeSeverity = (type: string): string => {
  const severities: Record<string, string> = {
    'CHARACTER': 'success',
    'LOCATION': 'danger',
    'ORGANIZATION': 'info',
    'OBJECT': 'warning',
    'EVENT': 'secondary'
  }
  return severities[type] || 'secondary'
}

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'CHARACTER': 'Personaje',
    'LOCATION': 'Lugar',
    'ORGANIZATION': 'Organización',
    'OBJECT': 'Objeto',
    'EVENT': 'Evento'
  }
  return labels[type] || type
}

const getImportanceSeverity = (importance: string): string => {
  const severities: Record<string, string> = {
    'critical': 'danger',
    'high': 'warning',
    'medium': 'info',
    'low': 'secondary',
    'minimal': 'contrast'
  }
  return severities[importance] || 'secondary'
}

const getImportanceLabel = (importance: string): string => {
  const labels: Record<string, string> = {
    'critical': 'Crítica',
    'high': 'Alta',
    'medium': 'Media',
    'low': 'Baja',
    'minimal': 'Mínima'
  }
  return labels[importance] || importance
}

// Lifecycle
onMounted(async () => {
  const projectId = parseInt(route.params.id as string)
  await projectsStore.fetchProject(projectId)
  await loadEntities()
})
</script>

<style scoped>
.entities-view {
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
  color: var(--primary-color);
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
:deep(.entity-sidebar .p-sidebar-content) {
  padding: 1.5rem;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.entity-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-section {
  padding: 0;
}

.detail-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.entity-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.entity-header-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-icon-large {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--green-50);
  border-radius: 12px;
  flex-shrink: 0;
}

.entity-icon-large i {
  font-size: 1.5rem;
  color: var(--green-600);
}

.entity-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

/* Tags con padding adecuado */
.type-tag {
  font-size: 0.75rem;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
}

.importance-tag {
  font-size: 0.75rem;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
}

.aliases-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.alias-tag {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.empty-text {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin: 0;
}

.detail-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--surface-50);
  border-radius: 8px;
}

.detail-stat .stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.detail-stat .stat-value {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-color);
}

.detail-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Diálogos */
.edit-dialog {
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

.w-full {
  width: 100%;
}

.mb-3 {
  margin-bottom: 1rem;
}
</style>
