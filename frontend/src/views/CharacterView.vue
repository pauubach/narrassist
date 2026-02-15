<template>
  <div class="character-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button
          v-tooltip.right="'Volver'"
          icon="pi pi-arrow-left"
          text
          rounded
          @click="goBack"
        />
        <div class="header-info">
          <h1>{{ entityTypeTitle }}</h1>
          <p v-if="project">{{ project.name }}</p>
        </div>
      </div>
      <div class="header-actions">
        <Button
          label="Exportar ficha"
          icon="pi pi-download"
          outlined
          @click="exportSheet"
        />
      </div>
    </div>

    <!-- Contenido principal -->
    <div class="view-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <ProgressSpinner />
        <p>Cargando ficha de personaje...</p>
      </div>

      <!-- Error state -->
      <Message v-else-if="error" severity="error" :closable="false">
        {{ error }}
      </Message>

      <!-- Character Sheet -->
      <CharacterSheet
        v-else-if="character"
        :character="character"
        :project-id="projectId"
        :attributes="attributes"
        :relationships="relationships"
        :timeline="timeline"
        :editable="true"
        @edit="onEditCharacter"
        @add-attribute="onAddAttribute"
        @delete-attribute="onDeleteAttribute"
        @add-relationship="onAddRelationship"
        @delete-relationship="onDeleteRelationship"
        @undo-merge="onUndoMerge"
      />
    </div>

    <!-- Diálogo: Editar personaje -->
    <Dialog
      v-model:visible="showEditDialog"
      modal
      header="Editar Personaje"
      :style="{ width: '500px' }"
    >
      <div v-if="editingCharacter" class="edit-dialog">
        <div class="field">
          <label>Nombre canónico *</label>
          <InputText
            v-model="editingCharacter.name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Importancia</label>
          <SelectButton
            v-model="editingCharacter.importance"
            :options="importanceOptions"
            option-label="label"
            option-value="value"
          />
        </div>

        <div class="field">
          <label>Nombres alternativos</label>
          <InputChips
            v-model="editingCharacter.aliases"
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
          @click="saveCharacter"
        />
      </template>
    </Dialog>

    <!-- Diálogo: Añadir atributo -->
    <Dialog
      v-model:visible="showAddAttributeDialog"
      modal
      header="Añadir Atributo"
      :style="{ width: '500px' }"
    >
      <div class="edit-dialog">
        <div class="field">
          <label>Categoría</label>
          <Select
            v-model="newAttribute.category"
            :options="attributeCategories"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Nombre del atributo *</label>
          <InputText
            v-model="newAttribute.name"
            placeholder="Ej: Color de ojos, Altura..."
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Valor *</label>
          <InputText
            v-model="newAttribute.value"
            placeholder="Ej: Azules, 1.75m..."
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Capítulo de primera aparición</label>
          <InputNumber
            v-model="newAttribute.firstMentionChapter"
            placeholder="Número de capítulo"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="showAddAttributeDialog = false"
        />
        <Button
          label="Añadir"
          icon="pi pi-check"
          @click="saveAttribute"
        />
      </template>
    </Dialog>

    <!-- Diálogo: Añadir relación -->
    <Dialog
      v-model:visible="showAddRelationshipDialog"
      modal
      header="Añadir Relación"
      :style="{ width: '500px' }"
    >
      <div class="edit-dialog">
        <div class="field">
          <label>Personaje relacionado *</label>
          <Select
            v-model="newRelationship.relatedEntityId"
            :options="availableCharacters"
            option-label="name"
            option-value="id"
            placeholder="Seleccionar personaje"
            class="w-full"
            filter
          />
        </div>

        <div class="field">
          <label>Tipo de relación *</label>
          <Select
            v-model="newRelationship.relationshipType"
            :options="relationshipTypes"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar tipo"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Descripción (opcional)</label>
          <Textarea
            v-model="newRelationship.description"
            rows="3"
            placeholder="Describe la relación..."
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="showAddRelationshipDialog = false"
        />
        <Button
          label="Añadir"
          icon="pi pi-check"
          @click="saveRelationship"
        />
      </template>
    </Dialog>

    <!-- Diálogo: Deshacer fusión -->
    <UndoMergeDialog
      :visible="showUndoMergeDialog"
      :project-id="projectId"
      :entity="character"
      @update:visible="showUndoMergeDialog = $event"
      @undo-complete="onUndoMergeComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import InputChips from 'primevue/inputchips'
import Textarea from 'primevue/textarea'
import CharacterSheet from '@/components/CharacterSheet.vue'
import UndoMergeDialog from '@/components/UndoMergeDialog.vue'
import type { Entity, CharacterAttribute, CharacterRelationship } from '@/types'
import { transformEntity, transformEntities } from '@/types/transformers'
import { api } from '@/services/apiClient'
import { getAttributeCategoriesForEntityType } from '@/config/attributes'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const toast = useToast()

// Estado
const loading = ref(true)
const error = ref('')
const character = ref<Entity | null>(null)
const attributes = ref<CharacterAttribute[]>([])
const relationships = ref<CharacterRelationship[]>([])
const timeline = ref<any[]>([])
const availableCharacters = ref<Entity[]>([])

// Diálogos
const showEditDialog = ref(false)
const showAddAttributeDialog = ref(false)
const showAddRelationshipDialog = ref(false)
const showUndoMergeDialog = ref(false)
const editingCharacter = ref<Entity | null>(null)
const newAttribute = ref<CharacterAttribute>({
  entityId: 0,
  category: 'physical',
  name: '',
  value: ''
})
const newRelationship = ref<Partial<CharacterRelationship>>({
  relationshipType: '',
  description: ''
})

const project = computed(() => projectsStore.currentProject)
const projectId = computed(() => parseInt(route.params.projectId as string))
const characterId = computed(() => parseInt(route.params.id as string))

// Dynamic title based on entity type
const entityTypeTitle = computed(() => {
  if (!character.value) return 'Ficha de Entidad'
  const typeLabels: Record<string, string> = {
    character: 'Ficha de Personaje',
    location: 'Ficha de Lugar',
    object: 'Ficha de Objeto',
    organization: 'Ficha de Organización',
    event: 'Ficha de Evento',
    concept: 'Ficha de Concepto'
  }
  return typeLabels[character.value.type] || 'Ficha de Entidad'
})

// Opciones - Domain EntityImportance values
const importanceOptions = [
  { label: 'Menor', value: 'minor' },
  { label: 'Secundario', value: 'secondary' },
  { label: 'Principal', value: 'main' }
]

const attributeCategories = computed(() =>
  getAttributeCategoriesForEntityType(character.value?.type || 'character')
)

const relationshipTypes = [
  { label: 'Familiar', value: 'family' },
  { label: 'Amistad', value: 'friend' },
  { label: 'Enemigo', value: 'enemy' },
  { label: 'Romántica', value: 'romantic' },
  { label: 'Profesional', value: 'professional' }
]

watch(
  attributeCategories,
  (categories) => {
    if (categories.length === 0) return
    // Justificación: al cambiar tipo de entidad, forzamos una categoría válida.
    // Evita enviar categorías incompatibles al backend (ej. "physical" en location).
    if (!categories.some(c => c.value === newAttribute.value.category)) {
      newAttribute.value.category = categories[0].value
    }
  },
  { immediate: true }
)

// Funciones
const loadCharacter = async () => {
  loading.value = true
  error.value = ''

  try {
    // Cargar personaje
    const charData = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${projectId.value}/entities/${characterId.value}`)

    if (charData.success) {
      // Transform API response to domain type
      character.value = transformEntity(charData.data)

      // Cargar atributos
      const attrsData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes`)
      if (attrsData.success) {
        attributes.value = attrsData.data || []
      }

      // Cargar relaciones
      const relsData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId.value}/entities/${characterId.value}/relationships`)
      if (relsData.success) {
        relationships.value = relsData.data || []
      }

      // Cargar personajes disponibles (para relaciones)
      const entitiesData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId.value}/entities`)
      if (entitiesData.success) {
        // Transform and filter for characters
        const allEntities = transformEntities(entitiesData.data || [])
        availableCharacters.value = allEntities.filter(
          (e: Entity) => e.type === 'character' && e.id !== characterId.value
        )
      }

      // Cargar timeline del personaje
      const timelineData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId.value}/entities/${characterId.value}/timeline`)
      if (timelineData.success) {
        timeline.value = timelineData.data || []
      }
    } else {
      error.value = 'Personaje no encontrado'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  // Use browser history to go back to where user came from
  if (window.history.length > 1) {
    router.back()
  } else {
    // Fallback to project detail if no history
    router.push({ name: 'project', params: { id: projectId.value } })
  }
}

const onEditCharacter = (char: Entity) => {
  editingCharacter.value = { ...char }
  showEditDialog.value = true
}

const saveCharacter = async () => {
  if (!editingCharacter.value) {
    showEditDialog.value = false
    return
  }

  try {
    const data = await api.putRaw<{ success: boolean; data?: any; message?: string; error?: string }>(`/api/projects/${projectId.value}/entities/${characterId.value}`, {
      name: editingCharacter.value.name,
      importance: editingCharacter.value.importance,
      aliases: editingCharacter.value.aliases,
    })

    if (data.success) {
      showEditDialog.value = false
      // Actualizar personaje local
      if (character.value) {
        character.value = { ...editingCharacter.value }
      }
      console.log('Character updated successfully:', data.message)
    } else {
      console.error('Failed to update character:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al guardar: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error updating character:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar el personaje', life: 5000 })
  }
}

const onAddAttribute = (category: string) => {
  const available = attributeCategories.value.map(c => c.value)
  const safeCategory = available.includes(category)
    ? category
    : (available[0] || 'physical')
  newAttribute.value = {
    entityId: characterId.value,
    category: safeCategory,
    name: '',
    value: ''
  }
  showAddAttributeDialog.value = true
}

const saveAttribute = async () => {
  if (!newAttribute.value.name || !newAttribute.value.value) {
    toast.add({ severity: 'warn', summary: 'Campos requeridos', detail: 'Por favor completa el nombre y valor del atributo', life: 4000 })
    return
  }

  try {
    const data = await api.postRaw<{ success: boolean; data?: any; message?: string; error?: string }>(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes`, {
      category: newAttribute.value.category,
      name: newAttribute.value.name,
      value: newAttribute.value.value,
    })

    if (data.success) {
      showAddAttributeDialog.value = false
      // Añadir el nuevo atributo a la lista local
      attributes.value.push({
        id: data.data.id,
        entityId: characterId.value,
        category: newAttribute.value.category,
        name: newAttribute.value.name,
        value: newAttribute.value.value,
      })
      console.log('Attribute created successfully:', data.message)
    } else {
      console.error('Failed to create attribute:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al crear atributo: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error creating attribute:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo crear el atributo', life: 5000 })
  }
}

const onDeleteAttribute = async (attributeId: number | undefined) => {
  if (!attributeId) return

  // Pedir confirmación
  if (!confirm('¿Seguro que deseas eliminar este atributo?')) {
    return
  }

  try {
    const data = await api.del<{ success: boolean; error?: string }>(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes/${attributeId}`)

    if (data.success) {
      // Eliminar de la lista local
      attributes.value = attributes.value.filter(a => a.id !== attributeId)
      toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Atributo eliminado correctamente', life: 3000 })
    } else {
      console.error('Failed to delete attribute:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al eliminar: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error deleting attribute:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar el atributo', life: 5000 })
  }
}

const onAddRelationship = () => {
  newRelationship.value = {
    entityId: characterId.value,
    relationshipType: '',
    description: ''
  }
  showAddRelationshipDialog.value = true
}

const saveRelationship = async () => {
  if (!newRelationship.value.relationshipType) {
    toast.add({ severity: 'warn', summary: 'Campo requerido', detail: 'Por favor selecciona un tipo de relación', life: 4000 })
    return
  }

  try {
    const data = await api.postRaw<{ success: boolean; error?: string }>(`/api/projects/${projectId.value}/relationships`, {
      source_entity_id: characterId.value,
      target_entity_id: newRelationship.value.entityId,
      relation_type: newRelationship.value.relationshipType,
      description: newRelationship.value.description || '',
      bidirectional: true,
    })

    if (data.success) {
      showAddRelationshipDialog.value = false
      // Recargar relaciones
      await loadCharacter()
      toast.add({ severity: 'success', summary: 'Relación creada', detail: 'La relación se ha añadido correctamente', life: 3000 })
    } else {
      console.error('Failed to create relationship:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al crear relación: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error creating relationship:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo crear la relación', life: 5000 })
  }
}

const onDeleteRelationship = async (relationshipId: number | string | undefined) => {
  if (!relationshipId) return

  if (!confirm('¿Eliminar esta relación?')) return

  try {
    const data = await api.del<{ success: boolean; error?: string }>(`/api/projects/${projectId.value}/relationships/${relationshipId}`)

    if (data.success) {
      // Recargar relaciones
      await loadCharacter()
      toast.add({ severity: 'success', summary: 'Eliminada', detail: 'Relación eliminada correctamente', life: 3000 })
    } else {
      console.error('Failed to delete relationship:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al eliminar relación: ${data.error}`, life: 5000 })
    }
  } catch (err) {
    console.error('Error deleting relationship:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la relación', life: 5000 })
  }
}

const onUndoMerge = () => {
  showUndoMergeDialog.value = true
}

const onUndoMergeComplete = async () => {
  // Notificar al HistoryPanel y resto de la app
  window.dispatchEvent(new CustomEvent('history:undo-complete', {
    detail: { projectId: projectId.value },
  }))
  // Navegar de vuelta al proyecto ya que esta entidad ya no existe
  router.push({
    name: 'project',
    params: { id: projectId.value }
  })
}

const exportSheet = async () => {
  if (!character.value) return

  try {
    // Crear contenido del export
    const content = {
      name: character.value.name,
      type: character.value.type,
      importance: character.value.importance,
      aliases: character.value.aliases,
      attributes: attributes.value,
      relationships: relationships.value,
      exportedAt: new Date().toISOString(),
    }

    // Descargar como JSON
    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ficha_${character.value.name.replace(/\s+/g, '_')}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Error exporting sheet:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar la ficha', life: 5000 })
  }
}

// Lifecycle
onMounted(async () => {
  await projectsStore.fetchProject(projectId.value)
  await loadCharacter()
})
</script>

<style scoped>
.character-view {
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
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.view-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
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
</style>
