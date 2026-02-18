<template>
  <div class="collections-view">
    <div class="header">
      <div class="header-left">
        <h1>Colecciones</h1>
        <span v-if="collectionsStore.hasCollections" class="collection-count">
          {{ collectionsStore.collectionCount }} {{ collectionsStore.collectionCount === 1 ? 'colección' : 'colecciones' }}
        </span>
      </div>
      <div class="header-right">
        <DsInput
          v-model="searchQuery"
          placeholder="Buscar colecciones..."
          icon="pi pi-search"
          clearable
          class="search-input"
        />
        <span class="header-divider"></span>
        <Button
          label="Nueva Colección"
          icon="pi pi-plus"
          severity="success"
          @click="showCreateDialog = true"
        />
      </div>
    </div>

    <div class="content">
      <!-- Loading -->
      <div v-if="collectionsStore.loading" class="collections-grid">
        <DsSkeleton v-for="i in 3" :key="i" variant="project-card" />
      </div>

      <!-- Error -->
      <Message v-else-if="collectionsStore.error" severity="error" :closable="false" class="error-message">
        <p>{{ collectionsStore.error }}</p>
        <Button label="Reintentar" icon="pi pi-refresh" text @click="loadCollections" />
      </Message>

      <!-- Empty state -->
      <div v-else-if="!collectionsStore.hasCollections" class="empty-state">
        <i class="pi pi-folder-open empty-icon"></i>
        <h2>No hay colecciones</h2>
        <p>Crea una colección para agrupar los libros de una saga o serie y detectar inconsistencias entre ellos</p>
        <Button
          label="Crear Primera Colección"
          icon="pi pi-plus"
          size="large"
          @click="showCreateDialog = true"
        />
      </div>

      <!-- Collection list -->
      <div v-else class="collections-grid">
        <Card
          v-for="collection in filteredCollections"
          :key="collection.id"
          class="collection-card"
          @click="openCollection(collection.id)"
        >
          <template #header>
            <div class="card-header">
              <div class="format-badge">
                <i class="pi pi-folder"></i>
                Saga
              </div>
              <div class="card-actions">
                <Button
                  icon="pi pi-ellipsis-v"
                  text
                  rounded
                  @click.stop="showContextMenu($event, collection)"
                />
              </div>
            </div>
          </template>

          <template #title>
            {{ collection.name }}
          </template>

          <template #subtitle>
            <div class="collection-meta">
              <span><i class="pi pi-calendar"></i> {{ formatDate(collection.createdAt) }}</span>
            </div>
          </template>

          <template #content>
            <div class="collection-stats">
              <div class="stat">
                <span class="stat-value">{{ collection.projectCount }}</span>
                <span class="stat-label">{{ collection.projectCount === 1 ? 'libro' : 'libros' }}</span>
              </div>
            </div>
            <p v-if="collection.description" class="collection-description">
              {{ collection.description }}
            </p>
          </template>

          <template #footer>
            <div class="card-footer">
              <Button label="Abrir" icon="pi pi-arrow-right" text @click.stop="openCollection(collection.id)" />
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <CollectionDialog
      v-model:visible="showCreateDialog"
      :collection="editingCollection"
      @save="handleSave"
      @hide="editingCollection = null"
    />

    <!-- Context Menu -->
    <ContextMenu ref="contextMenuRef" :model="contextMenuItems" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import ContextMenu from 'primevue/contextmenu'
import DsInput from '@/components/ds/DsInput.vue'
import DsSkeleton from '@/components/ds/DsSkeleton.vue'
import CollectionDialog from '@/components/collections/CollectionDialog.vue'
import { useCollectionsStore } from '@/stores/collections'
import type { Collection } from '@/types'

const router = useRouter()
const toast = useToast()
const collectionsStore = useCollectionsStore()

const searchQuery = ref('')
const showCreateDialog = ref(false)
const editingCollection = ref<Collection | null>(null)
const contextMenuRef = ref()
const selectedCollection = ref<Collection | null>(null)

const filteredCollections = computed(() => {
  if (!searchQuery.value) return collectionsStore.collections
  const q = searchQuery.value.toLowerCase()
  return collectionsStore.collections.filter(
    c => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q),
  )
})

const contextMenuItems = computed(() => [
  {
    label: 'Editar',
    icon: 'pi pi-pencil',
    command: () => {
      if (selectedCollection.value) {
        editingCollection.value = selectedCollection.value
        showCreateDialog.value = true
      }
    },
  },
  {
    label: 'Eliminar',
    icon: 'pi pi-trash',
    class: 'p-menuitem-danger',
    command: () => handleDelete(),
  },
])

function showContextMenu(event: Event, collection: Collection) {
  selectedCollection.value = collection
  contextMenuRef.value?.show(event)
}

function openCollection(id: number) {
  router.push({ name: 'collection-detail', params: { id } })
}

async function handleSave(name: string, description: string) {
  try {
    if (editingCollection.value) {
      await collectionsStore.updateCollection(editingCollection.value.id, { name, description })
      toast.add({ severity: 'success', summary: 'Actualizada', detail: 'Colección actualizada', life: 3000 })
    } else {
      await collectionsStore.createCollection(name, description)
      toast.add({ severity: 'success', summary: 'Creada', detail: 'Colección creada', life: 3000 })
    }
    showCreateDialog.value = false
    editingCollection.value = null
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar la colección', life: 5000 })
  }
}

async function handleDelete() {
  if (!selectedCollection.value) return
  if (!confirm(`¿Eliminar la colección "${selectedCollection.value.name}"? Los proyectos no se borrarán.`)) return

  try {
    await collectionsStore.deleteCollection(selectedCollection.value.id)
    toast.add({ severity: 'success', summary: 'Eliminada', detail: 'Colección eliminada', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la colección', life: 5000 })
  }
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function loadCollections() {
  await collectionsStore.fetchCollections()
}

onMounted(loadCollections)
</script>

<style scoped>
.collections-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.header-left h1 {
  margin: 0;
  font-size: 1.75rem;
}

.collection-count {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-divider {
  width: 1px;
  height: 1.5rem;
  background: var(--surface-border);
}

.search-input {
  width: 240px;
}

.collections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.collection-card {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.collection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem 0;
}

.format-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.card-actions {
  display: flex;
  gap: 0.25rem;
}

.collection-meta {
  display: flex;
  gap: 1rem;
  color: var(--text-color-secondary);
  font-size: 0.8125rem;
}

.collection-meta i {
  font-size: 0.75rem;
  margin-right: 0.25rem;
}

.collection-stats {
  display: flex;
  gap: 1.5rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.collection-description {
  margin-top: 0.75rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  font-size: 4rem;
  color: var(--text-color-secondary);
  opacity: 0.3;
}

.empty-state h2 {
  margin: 1rem 0 0.5rem;
  color: var(--text-color);
}

.empty-state p {
  color: var(--text-color-secondary);
  margin-bottom: 1.5rem;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.error-message {
  margin-top: 1rem;
}
</style>
