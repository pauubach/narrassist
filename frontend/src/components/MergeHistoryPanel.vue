<template>
  <div class="merge-history-panel">
    <div class="panel-header">
      <h3>
        <i class="pi pi-history"></i>
        Historial de Fusiones
      </h3>
      <Button
        v-tooltip.left="'Actualizar'"
        icon="pi pi-refresh"
        text
        rounded
        size="small"
        :loading="loading"
        @click="loadHistory"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading && !history.length" class="loading-state">
      <i class="pi pi-spin pi-spinner"></i>
      <span>Cargando historial...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && !history.length" class="empty-state">
      <i class="pi pi-link-slash"></i>
      <p>No hay fusiones registradas</p>
    </div>

    <!-- History list -->
    <div v-else class="history-list">
      <div
        v-for="entry in history"
        :key="entry.id"
        class="history-entry"
        :class="{ 'undone': entry.undoneAt }"
      >
        <div class="entry-header">
          <div class="entry-icon">
            <i :class="entry.undoneAt ? 'pi pi-undo' : 'pi pi-link'"></i>
          </div>
          <div class="entry-info">
            <span class="entry-result">
              {{ entry.resultEntityName }}
            </span>
            <span class="entry-sources">
              <i class="pi pi-arrow-left"></i>
              {{ entry.sourceEntityNames.join(' + ') }}
            </span>
          </div>
          <Tag
            v-if="entry.undoneAt"
            severity="secondary"
            value="Deshecha"
            class="status-tag"
          />
        </div>

        <div class="entry-meta">
          <span class="entry-date">
            <i class="pi pi-calendar"></i>
            {{ formatDate(entry.mergedAt) }}
          </span>
          <span v-if="entry.note" class="entry-note">
            <i class="pi pi-comment"></i>
            {{ entry.note }}
          </span>
        </div>

        <!-- Undone badge -->
        <div v-if="entry.undoneAt" class="entry-undone-info">
          <span>
            <i class="pi pi-check-circle"></i>
            Deshecha el {{ formatDate(entry.undoneAt) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { MergeHistoryEntry } from '@/types'
import { transformMergeHistory } from '@/types/transformers'
import { api } from '@/services/apiClient'

const props = defineProps<{
  projectId: number
}>()

// Read-only panel — undo is handled via unified HistoryPanel (Ctrl+Z / sidebar)

const loading = ref(false)
const history = ref<MergeHistoryEntry[]>([])

const loadHistory = async () => {
  loading.value = true
  try {
    const data = await api.getRaw<any>(`/api/projects/${props.projectId}/entities/merge-history`)

    if (data.success && data.data.merges) {
      history.value = transformMergeHistory(data.data.merges)
    }
  } catch (error) {
    console.error('Error loading merge history:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (date: Date): string => {
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Load on mount and when projectId changes
onMounted(loadHistory)
watch(() => props.projectId, loadHistory)

// Expose refresh method
defineExpose({ refresh: loadHistory })
</script>

<style scoped>
.merge-history-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-section);
  border-radius: 8px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--surface-border);
}

.panel-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.panel-header h3 i {
  color: var(--primary-color);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.empty-state i {
  font-size: 2rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 0.875rem;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-entry {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  transition: all 0.2s;
}

.history-entry:hover {
  border-color: var(--primary-200);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.history-entry.undone {
  opacity: 0.7;
  background: var(--surface-ground);
}

.entry-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.entry-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 50%;
  flex-shrink: 0;
}

.entry-icon i {
  font-size: 0.875rem;
  color: var(--primary-color);
}

.history-entry.undone .entry-icon {
  background: var(--surface-200);
}

.history-entry.undone .entry-icon i {
  color: var(--text-color-secondary);
}

.entry-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.entry-result {
  font-weight: 600;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-sources {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.entry-sources i {
  font-size: 0.625rem;
}

.status-tag {
  flex-shrink: 0;
}

.entry-meta {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-left: calc(32px + 0.75rem);
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entry-meta i {
  margin-right: 0.375rem;
  font-size: 0.6875rem;
}

.entry-undone-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.75rem;
  color: var(--green-600);
}

.entry-undone-info i {
  font-size: 0.875rem;
}

/* Scrollbar */
.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: var(--surface-ground);
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}
</style>
