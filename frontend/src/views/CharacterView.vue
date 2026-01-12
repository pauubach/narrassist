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
          v-tooltip.right="'Volver a entidades'"
        />
        <div class="header-info">
          <h1>Ficha de Personaje</h1>
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
        :attributes="attributes"
        :relationships="relationships"
        :timeline="timeline"
        :editable="true"
        @edit="onEditCharacter"
        @add-attribute="onAddAttribute"
        @delete-attribute="onDeleteAttribute"
        @add-relationship="onAddRelationship"
        @delete-relationship="onDeleteRelationship"
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
            v-model="editingCharacter.canonical_name"
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
            v-model="newAttribute.attribute_category"
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
            v-model="newAttribute.attribute_name"
            placeholder="Ej: Color de ojos, Altura..."
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Valor *</label>
          <InputText
            v-model="newAttribute.attribute_value"
            placeholder="Ej: Azules, 1.75m..."
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Capítulo de primera mención</label>
          <InputNumber
            v-model="newAttribute.first_mention_chapter"
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
            v-model="newRelationship.related_entity_id"
            :options="availableCharacters"
            optionLabel="canonical_name"
            optionValue="id"
            placeholder="Seleccionar personaje"
            class="w-full"
            filter
          />
        </div>

        <div class="field">
          <label>Tipo de relación *</label>
          <Dropdown
            v-model="newRelationship.relationship_type"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
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
import type { Entity, CharacterAttribute, CharacterRelationship } from '@/types'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

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
const editingCharacter = ref<Entity | null>(null)
const newAttribute = ref<CharacterAttribute>({
  entity_id: 0,
  attribute_category: 'physical',
  attribute_name: '',
  attribute_value: ''
})
const newRelationship = ref<Partial<CharacterRelationship>>({
  relationship_type: '',
  description: ''
})

const project = computed(() => projectsStore.currentProject)
const projectId = computed(() => parseInt(route.params.projectId as string))
const characterId = computed(() => parseInt(route.params.id as string))

// Opciones
const importanceOptions = [
  { label: 'Baja', value: 'low' },
  { label: 'Media', value: 'medium' },
  { label: 'Alta', value: 'high' }
]

const attributeCategories = [
  { label: 'Físico', value: 'physical' },
  { label: 'Psicológico', value: 'psychological' }
]

const relationshipTypes = [
  { label: 'Familiar', value: 'family' },
  { label: 'Amistad', value: 'friend' },
  { label: 'Enemigo', value: 'enemy' },
  { label: 'Romántico', value: 'romantic' },
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
      character.value = charData.data

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
        availableCharacters.value = entitiesData.data.filter(
          (e: Entity) => e.entity_type === 'CHARACTER' && e.id !== characterId.value
        )
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
  router.push({ name: 'entities', params: { id: projectId.value } })
}

const onEditCharacter = (char: Entity) => {
  editingCharacter.value = { ...char }
  showEditDialog.value = true
}

const saveCharacter = async () => {
  // TODO: Implementar guardado de personaje
  console.log('Save character:', editingCharacter.value)
  showEditDialog.value = false
}

const onAddAttribute = (category: string) => {
  newAttribute.value = {
    entity_id: characterId.value,
    attribute_category: category,
    attribute_name: '',
    attribute_value: ''
  }
  showAddAttributeDialog.value = true
}

const saveAttribute = async () => {
  // TODO: Implementar guardado de atributo
  console.log('Save attribute:', newAttribute.value)
  showAddAttributeDialog.value = false
}

const onDeleteAttribute = async (attributeId: number | undefined) => {
  if (!attributeId) return
  // TODO: Implementar eliminación de atributo
  console.log('Delete attribute:', attributeId)
}

const onAddRelationship = () => {
  newRelationship.value = {
    entity_id: characterId.value,
    relationship_type: '',
    description: ''
  }
  showAddRelationshipDialog.value = true
}

const saveRelationship = async () => {
  // TODO: Implementar guardado de relación
  console.log('Save relationship:', newRelationship.value)
  showAddRelationshipDialog.value = false
}

const onDeleteRelationship = async (relationshipId: number | undefined) => {
  if (!relationshipId) return
  // TODO: Implementar eliminación de relación
  console.log('Delete relationship:', relationshipId)
}

const exportSheet = () => {
  // TODO: Implementar exportación
  console.log('Export sheet')
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
