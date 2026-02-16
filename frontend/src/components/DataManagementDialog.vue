<script setup lang="ts">
/**
 * DataManagementDialog - Gestión de datos almacenados en disco.
 *
 * Muestra las categorías de datos con su tamaño y permite eliminar
 * las que son propiedad de la app. Los directorios compartidos
 * (Ollama, HuggingFace) solo se muestran como información.
 *
 * Funciona tanto en macOS (donde no hay uninstaller) como en Windows
 * (complementa el uninstaller NSIS con gestión desde dentro de la app).
 */
import { ref, computed, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'

interface DataCategory {
  id: string
  label: string
  description: string
  path: string
  size_bytes: number
  is_shared: boolean
  is_destructive: boolean
  exists: boolean
}

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const toast = useToast()
const categories = ref<DataCategory[]>([])
const loading = ref(false)
const deleting = ref<string | null>(null)
const confirmingDelete = ref<string | null>(null)

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const totalOwnSize = computed(() =>
  categories.value
    .filter(c => !c.is_shared && c.exists)
    .reduce((sum, c) => sum + c.size_bytes, 0)
)

const totalSharedSize = computed(() =>
  categories.value
    .filter(c => c.is_shared && c.exists)
    .reduce((sum, c) => sum + c.size_bytes, 0)
)

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

async function loadCategories() {
  loading.value = true
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    categories.value = await invoke<DataCategory[]>('get_data_categories')
  } catch (err) {
    console.error('Error loading data categories:', err)
    // Fallback: mostrar mensaje si Tauri no está disponible (dev mode)
    toast.add({
      severity: 'warn',
      summary: 'Modo desarrollo',
      detail: 'La gestión de datos solo funciona en la aplicación instalada.',
      life: 5000
    })
  } finally {
    loading.value = false
  }
}

function requestDelete(categoryId: string) {
  confirmingDelete.value = categoryId
}

function cancelDelete() {
  confirmingDelete.value = null
}

async function confirmDelete(categoryId: string) {
  confirmingDelete.value = null
  deleting.value = categoryId

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const message = await invoke<string>('delete_data_category', { id: categoryId })

    toast.add({
      severity: 'success',
      summary: 'Eliminado',
      detail: message,
      life: 3000
    })

    // Recargar categorías para actualizar tamaños
    await loadCategories()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err instanceof Error ? err.message : String(err),
      life: 5000
    })
  } finally {
    deleting.value = null
  }
}

onMounted(() => {
  if (props.visible) {
    loadCategories()
  }
})

// Recargar cuando se abre el diálogo
function onShow() {
  loadCategories()
}
</script>

<template>
  <Dialog
    v-model:visible="dialogVisible"
    modal
    header="Gestionar datos"
    :style="{ width: '550px' }"
    @show="onShow"
  >
    <div v-if="loading" class="loading-container">
      <ProgressSpinner style="width: 40px; height: 40px" />
      <span>Calculando uso de disco...</span>
    </div>

    <div v-else class="data-categories">
      <!-- Datos propios -->
      <div class="section-header">
        <h4>Datos de Narrative Assistant</h4>
        <span class="section-size">{{ formatSize(totalOwnSize) }}</span>
      </div>

      <div
        v-for="cat in categories.filter(c => !c.is_shared)"
        :key="cat.id"
        class="category-item"
        :class="{ 'category-destructive': cat.is_destructive, 'category-empty': !cat.exists }"
      >
        <div class="category-info">
          <div class="category-header">
            <span class="category-label">{{ cat.label }}</span>
            <span class="category-size">{{ formatSize(cat.size_bytes) }}</span>
          </div>
          <p class="category-description">{{ cat.description }}</p>
          <code class="category-path">{{ cat.path }}</code>
        </div>

        <div class="category-actions">
          <!-- Confirming state -->
          <div v-if="confirmingDelete === cat.id" class="confirm-actions">
            <Button
              label="Confirmar"
              icon="pi pi-check"
              severity="danger"
              size="small"
              @click="confirmDelete(cat.id)"
            />
            <Button
              label="Cancelar"
              icon="pi pi-times"
              text
              size="small"
              @click="cancelDelete"
            />
          </div>
          <!-- Normal state -->
          <Button
            v-else-if="cat.exists"
            :label="deleting === cat.id ? 'Eliminando...' : 'Eliminar'"
            :icon="deleting === cat.id ? 'pi pi-spin pi-spinner' : 'pi pi-trash'"
            :severity="cat.is_destructive ? 'danger' : 'secondary'"
            size="small"
            :disabled="deleting !== null"
            outlined
            @click="requestDelete(cat.id)"
          />
          <span v-else class="empty-label">No encontrado</span>
        </div>
      </div>

      <!-- Advertencia para datos destructivos -->
      <Message v-if="categories.some(c => c.is_destructive && c.exists)" severity="warn" :closable="false" class="mt-3">
        Los elementos marcados en rojo contienen datos de trabajo que no se pueden recuperar.
      </Message>

      <!-- Datos compartidos -->
      <div v-if="categories.some(c => c.is_shared && c.exists)" class="shared-section">
        <div class="section-header">
          <h4>Datos compartidos con otras aplicaciones</h4>
          <span class="section-size">{{ formatSize(totalSharedSize) }}</span>
        </div>

        <div
          v-for="cat in categories.filter(c => c.is_shared && c.exists)"
          :key="cat.id"
          class="category-item category-shared"
        >
          <div class="category-info">
            <div class="category-header">
              <span class="category-label">{{ cat.label }}</span>
              <span class="category-size">{{ formatSize(cat.size_bytes) }}</span>
            </div>
            <p class="category-description">{{ cat.description }}</p>
            <code class="category-path">{{ cat.path }}</code>
          </div>
        </div>

        <Message severity="info" :closable="false" class="mt-2">
          Estos directorios son utilizados por otras aplicaciones y no se eliminan automaticamente.
          Si no los utiliza, puede eliminarlos manualmente.
        </Message>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <span class="footer-hint">
          En macOS, después de limpiar, arrastre la aplicación a la Papelera.
        </span>
        <Button label="Cerrar" icon="pi pi-times" text @click="dialogVisible = false" />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.data-categories {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.section-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-color);
}

.section-size {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--app-radius);
  background: var(--surface-card);
}

.category-item.category-empty {
  opacity: 0.5;
}

.category-item.category-destructive {
  border-color: var(--red-200);
}

.category-item.category-shared {
  border-color: var(--blue-200);
  background: color-mix(in srgb, var(--blue-50) 30%, var(--surface-card));
}

.category-info {
  flex: 1;
  min-width: 0;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.25rem;
}

.category-label {
  font-weight: 600;
  font-size: 0.875rem;
}

.category-size {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  background: var(--surface-100);
  padding: 0.125rem 0.5rem;
  border-radius: var(--app-radius);
}

.category-description {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.category-path {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--text-color-secondary);
  opacity: 0.7;
  word-break: break-all;
}

.category-actions {
  flex-shrink: 0;
}

.confirm-actions {
  display: flex;
  gap: 0.25rem;
}

.empty-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.shared-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.footer-hint {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

/* Dark mode */
.dark .category-item.category-shared {
  background: color-mix(in srgb, var(--blue-900) 20%, var(--surface-card));
}

.dark .category-item.category-destructive {
  border-color: var(--red-800);
}
</style>
