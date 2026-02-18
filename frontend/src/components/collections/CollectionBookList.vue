<template>
  <div class="book-list">
    <div class="book-list-header">
      <h3>Libros en la colección</h3>
      <Button
        label="Añadir Libro"
        icon="pi pi-plus"
        size="small"
        @click="showAddProject = true"
      />
    </div>

    <!-- Empty state -->
    <div v-if="!collection.projects.length" class="empty-state">
      <i class="pi pi-book empty-icon"></i>
      <p>No hay libros en esta colección</p>
      <p class="hint">Añade proyectos existentes para empezar el análisis cross-book</p>
    </div>

    <!-- Book list -->
    <div v-else class="books">
      <div v-for="(project, index) in collection.projects" :key="project.id" class="book-item">
        <div class="book-order">
          <span class="order-number">{{ index + 1 }}</span>
          <div class="order-buttons">
            <Button
              icon="pi pi-chevron-up"
              text
              rounded
              size="small"
              :disabled="index === 0"
              v-tooltip="'Subir'"
              @click="moveProject(project.id, index - 1)"
            />
            <Button
              icon="pi pi-chevron-down"
              text
              rounded
              size="small"
              :disabled="index === collection.projects.length - 1"
              v-tooltip="'Bajar'"
              @click="moveProject(project.id, index + 1)"
            />
          </div>
        </div>

        <div class="book-info">
          <div class="book-name">
            <i :class="getFormatIcon(project.documentFormat)" class="format-icon"></i>
            <span>{{ project.name }}</span>
          </div>
          <div class="book-meta">
            <span>{{ project.wordCount.toLocaleString() }} palabras</span>
            <span>{{ project.entityCount }} entidades</span>
          </div>
        </div>

        <Button
          icon="pi pi-times"
          text
          rounded
          severity="danger"
          size="small"
          v-tooltip="'Quitar de la colección'"
          @click="confirmRemove(project)"
        />
      </div>
    </div>

    <!-- Add Project Dialog -->
    <Dialog
      v-model:visible="showAddProject"
      header="Añadir Libro"
      :modal="true"
      :style="{ width: '400px' }"
    >
      <div v-if="availableProjects.length === 0" class="no-projects">
        <p>No hay proyectos disponibles para añadir.</p>
        <p class="hint">Todos los proyectos ya están en esta colección, o no hay proyectos creados.</p>
      </div>
      <div v-else class="add-project-list">
        <div
          v-for="project in availableProjects"
          :key="project.id"
          class="add-project-item"
          @click="handleAdd(project.id)"
        >
          <div class="project-info">
            <span class="project-name">{{ project.name }}</span>
            <span class="project-meta">{{ project.wordCount.toLocaleString() }} palabras</span>
          </div>
          <Button icon="pi pi-plus" text rounded size="small" />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useProjectsStore } from '@/stores/projects'
import { useCollectionsStore } from '@/stores/collections'
import type { CollectionDetail, CollectionProject } from '@/types'

const props = defineProps<{
  collection: CollectionDetail
}>()

const emit = defineEmits<{
  'add-project': [projectId: number]
  'remove-project': [projectId: number]
}>()

const projectsStore = useProjectsStore()
const collectionsStore = useCollectionsStore()
const showAddProject = ref(false)

const collectionProjectIds = computed(() =>
  new Set(props.collection.projects.map(p => p.id)),
)

const availableProjects = computed(() =>
  projectsStore.projects.filter(p => !collectionProjectIds.value.has(p.id)),
)

function getFormatIcon(format: string): string {
  const icons: Record<string, string> = {
    docx: 'pi pi-file-word',
    txt: 'pi pi-file',
    md: 'pi pi-file',
    pdf: 'pi pi-file-pdf',
    epub: 'pi pi-book',
  }
  return icons[format?.toLowerCase()] || 'pi pi-file'
}

function handleAdd(projectId: number) {
  emit('add-project', projectId)
  showAddProject.value = false
}

function confirmRemove(project: CollectionProject) {
  if (!confirm(`¿Quitar "${project.name}" de la colección?`)) return
  emit('remove-project', project.id)
}

async function moveProject(projectId: number, newOrder: number) {
  try {
    await collectionsStore.removeProject(props.collection.id, projectId)
    await collectionsStore.addProject(props.collection.id, projectId, newOrder)
  } catch (err) {
    console.error('Failed to reorder project:', err)
  }
}

onMounted(async () => {
  if (!projectsStore.hasProjects) {
    await projectsStore.fetchProjects()
  }
})
</script>

<style scoped>
.book-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.book-list-header h3 {
  margin: 0;
  font-size: 1rem;
}

.books {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.book-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  transition: background 0.15s;
}

.book-item:hover {
  background: var(--surface-hover);
}

.book-order {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-width: 80px;
}

.order-number {
  font-weight: 700;
  font-size: 1.125rem;
  color: var(--primary-color);
  width: 1.5rem;
  text-align: center;
}

.order-buttons {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.format-icon {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.book-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
}

.empty-icon {
  font-size: 3rem;
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

.add-project-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 400px;
  overflow-y: auto;
}

.add-project-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background 0.15s;
}

.add-project-item:hover {
  background: var(--surface-hover);
}

.project-name {
  font-weight: 600;
}

.project-meta {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.no-projects {
  text-align: center;
  padding: 1.5rem;
  color: var(--text-color-secondary);
}
</style>
