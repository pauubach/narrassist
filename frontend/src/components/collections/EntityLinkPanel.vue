<template>
  <div class="entity-link-panel">
    <TabView>
      <!-- Suggestions tab -->
      <TabPanel header="Sugerencias">
        <div class="suggestions-header">
          <div class="threshold-control">
            <label>Umbral de similitud: {{ (threshold * 100).toFixed(0) }}%</label>
            <Slider v-model="threshold" :min="0.5" :max="1.0" :step="0.05" class="threshold-slider" />
          </div>
          <Button
            label="Buscar Sugerencias"
            icon="pi pi-search"
            size="small"
            :loading="loadingSuggestions"
            @click="loadSuggestions"
          />
        </div>

        <div v-if="loadingSuggestions" class="loading-state">
          <ProgressSpinner style="width: 2rem; height: 2rem" />
          <span>Analizando entidades...</span>
        </div>

        <div v-else-if="!collectionsStore.linkSuggestions.length" class="empty-state">
          <i class="pi pi-link empty-icon"></i>
          <p>No hay sugerencias</p>
          <p class="hint">Añade al menos 2 libros con entidades analizadas y pulsa "Buscar Sugerencias"</p>
        </div>

        <DataTable
          v-else
          :value="collectionsStore.linkSuggestions"
          striped-rows
          row-hover
          class="suggestions-table"
        >
          <Column header="Entidad A" style="min-width: 180px">
            <template #body="{ data }">
              <div class="entity-cell">
                <span class="entity-name">{{ data.sourceEntityName }}</span>
                <span class="entity-project">{{ data.sourceProjectName }}</span>
              </div>
            </template>
          </Column>
          <Column header="" style="width: 50px; text-align: center">
            <template #body>
              <i class="pi pi-arrows-h" style="color: var(--text-color-secondary)"></i>
            </template>
          </Column>
          <Column header="Entidad B" style="min-width: 180px">
            <template #body="{ data }">
              <div class="entity-cell">
                <span class="entity-name">{{ data.targetEntityName }}</span>
                <span class="entity-project">{{ data.targetProjectName }}</span>
              </div>
            </template>
          </Column>
          <Column header="Similitud" style="width: 100px; text-align: center">
            <template #body="{ data }">
              <Tag
                :value="`${(data.similarity * 100).toFixed(0)}%`"
                :severity="data.similarity >= 0.9 ? 'success' : data.similarity >= 0.7 ? 'warn' : 'info'"
              />
            </template>
          </Column>
          <Column header="Tipo" field="matchType" style="width: 80px" />
          <Column header="Acciones" style="width: 120px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-check"
                  text
                  rounded
                  severity="success"
                  size="small"
                  v-tooltip="'Aceptar enlace'"
                  @click="acceptSuggestion(data)"
                />
                <Button
                  icon="pi pi-times"
                  text
                  rounded
                  severity="danger"
                  size="small"
                  v-tooltip="'Descartar'"
                  @click="dismissSuggestion(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Confirmed links tab -->
      <TabPanel header="Confirmados">
        <div v-if="!collectionsStore.entityLinks.length" class="empty-state">
          <i class="pi pi-check-circle empty-icon"></i>
          <p>No hay enlaces confirmados</p>
          <p class="hint">Acepta sugerencias o crea enlaces manuales</p>
        </div>

        <DataTable
          v-else
          :value="collectionsStore.entityLinks"
          striped-rows
          row-hover
          class="links-table"
        >
          <Column header="Entidad A" style="min-width: 180px">
            <template #body="{ data }">
              <div class="entity-cell">
                <span class="entity-name">{{ data.sourceEntityName }}</span>
                <span class="entity-project">{{ data.sourceProjectName }}</span>
              </div>
            </template>
          </Column>
          <Column header="" style="width: 50px; text-align: center">
            <template #body>
              <i class="pi pi-link" style="color: var(--primary-color)"></i>
            </template>
          </Column>
          <Column header="Entidad B" style="min-width: 180px">
            <template #body="{ data }">
              <div class="entity-cell">
                <span class="entity-name">{{ data.targetEntityName }}</span>
                <span class="entity-project">{{ data.targetProjectName }}</span>
              </div>
            </template>
          </Column>
          <Column header="Similitud" style="width: 100px; text-align: center">
            <template #body="{ data }">
              <Tag :value="`${(data.similarity * 100).toFixed(0)}%`" severity="info" />
            </template>
          </Column>
          <Column header="Tipo" field="matchType" style="width: 80px" />
          <Column header="" style="width: 60px">
            <template #body="{ data }">
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                size="small"
                v-tooltip="'Eliminar enlace'"
                @click="deleteLink(data.id)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Manual linking tab -->
      <TabPanel header="Enlace Manual">
        <div class="manual-link-form">
          <div class="link-side">
            <h4>Libro A</h4>
            <Select
              v-model="manualLink.sourceProjectId"
              :options="projects"
              option-label="name"
              option-value="id"
              placeholder="Seleccionar libro..."
              class="w-full"
              @change="loadProjectEntities('source', manualLink.sourceProjectId)"
            />
            <Select
              v-model="manualLink.sourceEntityId"
              :options="sourceEntities"
              option-label="name"
              option-value="id"
              placeholder="Seleccionar entidad..."
              class="w-full"
              :disabled="!manualLink.sourceProjectId"
            />
          </div>

          <div class="link-arrow">
            <i class="pi pi-arrows-h"></i>
          </div>

          <div class="link-side">
            <h4>Libro B</h4>
            <Select
              v-model="manualLink.targetProjectId"
              :options="projects.filter(p => p.id !== manualLink.sourceProjectId)"
              option-label="name"
              option-value="id"
              placeholder="Seleccionar libro..."
              class="w-full"
              @change="loadProjectEntities('target', manualLink.targetProjectId)"
            />
            <Select
              v-model="manualLink.targetEntityId"
              :options="targetEntities"
              option-label="name"
              option-value="id"
              placeholder="Seleccionar entidad..."
              class="w-full"
              :disabled="!manualLink.targetProjectId"
            />
          </div>
        </div>

        <div class="manual-link-actions">
          <Button
            label="Crear Enlace"
            icon="pi pi-link"
            :disabled="!canCreateManualLink"
            @click="createManualLink"
          />
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Slider from 'primevue/slider'
import Select from 'primevue/select'
import ProgressSpinner from 'primevue/progressspinner'
import { useCollectionsStore } from '@/stores/collections'
import { api } from '@/services/apiClient'
import type { CollectionProject, LinkSuggestion } from '@/types'

const props = defineProps<{
  collectionId: number
  projects: CollectionProject[]
}>()

const toast = useToast()
const collectionsStore = useCollectionsStore()

const threshold = ref(0.7)
const loadingSuggestions = ref(false)
const dismissedSuggestions = ref(new Set<string>())
const sourceEntities = ref<Array<{ id: number; name: string }>>([])
const targetEntities = ref<Array<{ id: number; name: string }>>([])

const manualLink = ref({
  sourceProjectId: null as number | null,
  sourceEntityId: null as number | null,
  targetProjectId: null as number | null,
  targetEntityId: null as number | null,
})

const canCreateManualLink = computed(() =>
  manualLink.value.sourceProjectId &&
  manualLink.value.sourceEntityId &&
  manualLink.value.targetProjectId &&
  manualLink.value.targetEntityId,
)

async function loadSuggestions() {
  loadingSuggestions.value = true
  try {
    await collectionsStore.fetchLinkSuggestions(props.collectionId, threshold.value)
  } finally {
    loadingSuggestions.value = false
  }
}

async function acceptSuggestion(suggestion: LinkSuggestion) {
  try {
    await collectionsStore.createEntityLink(props.collectionId, {
      source_entity_id: suggestion.sourceEntityId,
      target_entity_id: suggestion.targetEntityId,
      source_project_id: suggestion.sourceProjectId,
      target_project_id: suggestion.targetProjectId,
      similarity: suggestion.similarity,
      match_type: suggestion.matchType,
    })
    // Remove from suggestions list
    const key = `${suggestion.sourceEntityId}-${suggestion.targetEntityId}`
    dismissedSuggestions.value.add(key)
    toast.add({ severity: 'success', summary: 'Enlace creado', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo crear el enlace', life: 5000 })
  }
}

function dismissSuggestion(suggestion: LinkSuggestion) {
  const key = `${suggestion.sourceEntityId}-${suggestion.targetEntityId}`
  dismissedSuggestions.value.add(key)
}

async function deleteLink(linkId: number) {
  if (!confirm('¿Eliminar este enlace entre entidades?')) return
  try {
    await collectionsStore.deleteEntityLink(props.collectionId, linkId)
    toast.add({ severity: 'success', summary: 'Enlace eliminado', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 5000 })
  }
}

async function loadProjectEntities(side: 'source' | 'target', projectId: number | null) {
  if (!projectId) return
  try {
    const data = await api.getRaw<{ success: boolean; data: Array<{ id: number; name: string }> }>(
      `/api/projects/${projectId}/entities`,
    )
    const entities = data.data || data as any
    const list = Array.isArray(entities) ? entities : []
    if (side === 'source') {
      sourceEntities.value = list
    } else {
      targetEntities.value = list
    }
  } catch (err) {
    console.error('Failed to load entities:', err)
  }
}

async function createManualLink() {
  if (!canCreateManualLink.value) return
  try {
    await collectionsStore.createEntityLink(props.collectionId, {
      source_entity_id: manualLink.value.sourceEntityId!,
      target_entity_id: manualLink.value.targetEntityId!,
      source_project_id: manualLink.value.sourceProjectId!,
      target_project_id: manualLink.value.targetProjectId!,
      similarity: 1.0,
      match_type: 'manual',
    })
    manualLink.value = { sourceProjectId: null, sourceEntityId: null, targetProjectId: null, targetEntityId: null }
    sourceEntities.value = []
    targetEntities.value = []
    toast.add({ severity: 'success', summary: 'Enlace creado', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo crear el enlace', life: 5000 })
  }
}

onMounted(async () => {
  await collectionsStore.fetchEntityLinks(props.collectionId)
})
</script>

<style scoped>
.suggestions-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 1rem;
  gap: 1rem;
}

.threshold-control {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  flex: 1;
  max-width: 300px;
}

.threshold-control label {
  font-size: 0.8125rem;
  font-weight: 600;
}

.threshold-slider {
  width: 100%;
}

.entity-cell {
  display: flex;
  flex-direction: column;
}

.entity-name {
  font-weight: 600;
}

.entity-project {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.empty-state {
  text-align: center;
  padding: 2.5rem 2rem;
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--text-color-secondary);
  opacity: 0.3;
}

.empty-state p {
  margin: 0.5rem 0 0;
  color: var(--text-color-secondary);
}

.hint {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.manual-link-form {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  padding: 1rem 0;
}

.link-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.link-side h4 {
  margin: 0;
  font-size: 0.875rem;
}

.link-arrow {
  display: flex;
  align-items: center;
  padding-top: 2rem;
  font-size: 1.25rem;
  color: var(--text-color-secondary);
}

.manual-link-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}
</style>
