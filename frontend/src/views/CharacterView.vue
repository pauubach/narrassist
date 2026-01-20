<template>
  <div class="character-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          @click="goBack"
          v-tooltip.right="'Volver'"
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
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="field">
          <label>Nombres alternativos</label>
          <Chips
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
          <Dropdown
            v-model="newAttribute.category"
            :options="attributeCategories"
            optionLabel="label"
            optionValue="value"
            class="w-full"
            disabled
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
          <Dropdown
            v-model="newRelationship.relatedEntityId"
            :options="availableCharacters"
            optionLabel="name"
            optionValue="id"
            placeholder="Seleccionar personaje"
            class="w-full"
            filter
          />
        </div>

        <div class="field">
          <label>Tipo de relación *</label>
          <Dropdown
            v-model="newRelationship.relationshipType"
            :options="relationshipTypes"
            optionLabel="label"
            optionValue="value"
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import SelectButton from 'primevue/selectbutton'
import Chips from 'primevue/chips'
import Textarea from 'primevue/textarea'
import CharacterSheet from '@/components/CharacterSheet.vue'
import UndoMergeDialog from '@/components/UndoMergeDialog.vue'
import type { Entity, CharacterAttribute, CharacterRelationship } from '@/types'
import { transformEntity, transformEntities } from '@/types/transformers'

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

const attributeCategories = [
  { label: 'Físico', value: 'physical' },
  { label: 'Psicológico', value: 'psychological' }
]

const relationshipTypes = [
  { label: 'Familiar', value: 'family' },
  { label: 'Amistad', value: 'friend' },
  { label: 'Enemigo', value: 'enemy' },
  { label: 'Romántica', value: 'romantic' },
  { label: 'Profesional', value: 'professional' }
]

// Funciones
const loadCharacter = async () => {
  loading.value = true
  error.value = ''

  try {
    // Cargar personaje
    const charResponse = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}`)
    const charData = await charResponse.json()

    if (charData.success) {
      // Transform API response to domain type
      character.value = transformEntity(charData.data)

      // Cargar atributos
      const attrsResponse = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes`)
      const attrsData = await attrsResponse.json()
      if (attrsData.success) {
        attributes.value = attrsData.data || []
      }

      // Cargar relaciones
      const relsResponse = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}/relationships`)
      const relsData = await relsResponse.json()
      if (relsData.success) {
        relationships.value = relsData.data || []
      }

      // Cargar personajes disponibles (para relaciones)
      const entitiesResponse = await fetch(`/api/projects/${projectId.value}/entities`)
      const entitiesData = await entitiesResponse.json()
      if (entitiesData.success) {
        // Transform and filter for characters
        const allEntities = transformEntities(entitiesData.data || [])
        availableCharacters.value = allEntities.filter(
          (e: Entity) => e.type === 'character' && e.id !== characterId.value
        )
      }

      // Cargar timeline del personaje
      const timelineResponse = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}/timeline`)
      const timelineData = await timelineResponse.json()
      if (timelineData.success) {
        timeline.value = timelineData.data || []
      }
    } else {
      error.value = 'Personaje no encontrado'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
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
    const response = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: editingCharacter.value.name,
        importance: editingCharacter.value.importance,
        aliases: editingCharacter.value.aliases,
      }),
    })

    const data = await response.json()

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
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo guardar el personaje', life: 5000 })
  }
}

const onAddAttribute = (category: string) => {
  newAttribute.value = {
    entityId: characterId.value,
    category: category,
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
    const response = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        category: newAttribute.value.category,
        name: newAttribute.value.name,
        value: newAttribute.value.value,
      }),
    })

    const data = await response.json()

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
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo crear el atributo', life: 5000 })
  }
}

const onDeleteAttribute = async (attributeId: number | undefined) => {
  if (!attributeId) return

  // Pedir confirmación
  if (!confirm('¿Seguro que deseas eliminar este atributo?')) {
    return
  }

  try {
    const response = await fetch(`/api/projects/${projectId.value}/entities/${characterId.value}/attributes/${attributeId}`, {
      method: 'DELETE',
    })

    const data = await response.json()

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
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo eliminar el atributo', life: 5000 })
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
    const response = await fetch(`/api/projects/${projectId.value}/relationships`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source_entity_id: characterId.value,
        target_entity_id: newRelationship.value.entityId,
        relation_type: newRelationship.value.relationshipType,
        description: newRelationship.value.description || '',
        bidirectional: true,
      }),
    })

    const data = await response.json()

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
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo crear la relación', life: 5000 })
  }
}

const onDeleteRelationship = async (relationshipId: number | string | undefined) => {
  if (!relationshipId) return

  if (!confirm('¿Eliminar esta relación?')) return

  try {
    const response = await fetch(`/api/projects/${projectId.value}/relationships/${relationshipId}`, {
      method: 'DELETE',
    })

    const data = await response.json()

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
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo eliminar la relación', life: 5000 })
  }
}

const onUndoMerge = () => {
  showUndoMergeDialog.value = true
}

const onUndoMergeComplete = async () => {
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
