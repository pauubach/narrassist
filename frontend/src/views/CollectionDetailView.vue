<template>
  <div class="collection-detail-view">
    <!-- Loading -->
    <div v-if="collectionsStore.loading && !collectionsStore.currentCollection" class="loading-state">
      <ProgressSpinner />
    </div>

    <!-- Error -->
    <Message v-else-if="collectionsStore.error" severity="error" :closable="false">
      <p>{{ collectionsStore.error }}</p>
      <Button label="Volver" icon="pi pi-arrow-left" text @click="router.push('/collections')" />
    </Message>

    <!-- Content -->
    <template v-else-if="collection">
      <!-- Header -->
      <div class="detail-header">
        <div class="header-left">
          <Button
            icon="pi pi-arrow-left"
            text
            rounded
            v-tooltip="'Volver a colecciones'"
            @click="router.push('/collections')"
          />
          <div class="header-info">
            <h1>{{ collection.name }}</h1>
            <p v-if="collection.description" class="description">{{ collection.description }}</p>
            <div class="header-meta">
              <Tag :value="`${collection.projects.length} libros`" severity="info" />
              <Tag :value="`${collection.entityLinkCount} enlaces`" severity="secondary" />
            </div>
          </div>
        </div>
        <div class="header-actions">
          <Button icon="pi pi-pencil" text rounded v-tooltip="'Editar'" @click="showEditDialog = true" />
          <Button icon="pi pi-trash" text rounded severity="danger" v-tooltip="'Eliminar'" @click="handleDelete" />
        </div>
      </div>

      <!-- Tabs -->
      <TabView class="detail-tabs">
        <TabPanel header="Libros">
          <CollectionBookList
            :collection="collection"
            @add-project="handleAddProject"
            @remove-project="handleRemoveProject"
          />
        </TabPanel>

        <TabPanel header="Entity Links">
          <EntityLinkPanel
            :collection-id="collection.id"
            :projects="collection.projects"
          />
        </TabPanel>

        <TabPanel header="Análisis Cross-Book">
          <CrossBookReport :collection-id="collection.id" />
        </TabPanel>
      </TabView>

      <!-- Edit Dialog -->
      <CollectionDialog
        v-model:visible="showEditDialog"
        :collection="collection"
        @save="handleSave"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import ProgressSpinner from 'primevue/progressspinner'
import CollectionDialog from '@/components/collections/CollectionDialog.vue'
import CollectionBookList from '@/components/collections/CollectionBookList.vue'
import EntityLinkPanel from '@/components/collections/EntityLinkPanel.vue'
import CrossBookReport from '@/components/collections/CrossBookReport.vue'
import { useCollectionsStore } from '@/stores/collections'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const collectionsStore = useCollectionsStore()

const showEditDialog = ref(false)

const collectionId = computed(() => Number(route.params.id))
const collection = computed(() => collectionsStore.currentCollection)

async function handleSave(name: string, description: string) {
  try {
    await collectionsStore.updateCollection(collectionId.value, { name, description })
    showEditDialog.value = false
    toast.add({ severity: 'success', summary: 'Actualizada', detail: 'Colección actualizada', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar', life: 5000 })
  }
}

async function handleDelete() {
  if (!collection.value) return
  if (!confirm(`¿Eliminar la colección "${collection.value.name}"? Los proyectos no se borrarán.`)) return

  try {
    await collectionsStore.deleteCollection(collectionId.value)
    toast.add({ severity: 'success', summary: 'Eliminada', detail: 'Colección eliminada', life: 3000 })
    router.push('/collections')
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 5000 })
  }
}

async function handleAddProject(projectId: number) {
  try {
    await collectionsStore.addProject(collectionId.value, projectId)
    toast.add({ severity: 'success', summary: 'Añadido', detail: 'Libro añadido a la colección', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo añadir el libro', life: 5000 })
  }
}

async function handleRemoveProject(projectId: number) {
  try {
    await collectionsStore.removeProject(collectionId.value, projectId)
    toast.add({ severity: 'success', summary: 'Quitado', detail: 'Libro quitado de la colección', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo quitar el libro', life: 5000 })
  }
}

onMounted(async () => {
  await collectionsStore.fetchCollection(collectionId.value)
})

onUnmounted(() => {
  collectionsStore.clearCurrentCollection()
})
</script>

<style scoped>
.collection-detail-view {
  padding: 1.5rem 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 4rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.header-info h1 {
  margin: 0 0 0.25rem;
  font-size: 1.5rem;
}

.description {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin: 0 0 0.5rem;
}

.header-meta {
  display: flex;
  gap: 0.5rem;
}

.header-actions {
  display: flex;
  gap: 0.25rem;
}

.detail-tabs {
  margin-top: 1rem;
}
</style>
