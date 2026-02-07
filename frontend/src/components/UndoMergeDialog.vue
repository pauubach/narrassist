<template>
  <Dialog
    :visible="visible"
    modal
    header="Deshacer Fusión"
    :style="{ width: '500px' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="undo-merge-dialog">
      <!-- Advertencia -->
      <Message severity="warn" :closable="false">
        <p>
          Esta acción restaurará las entidades que fueron fusionadas.
          Las apariciones y atributos serán redistribuidos a sus entidades originales.
        </p>
      </Message>

      <!-- Info de la entidad fusionada -->
      <div v-if="entity" class="entity-info-section">
        <h4>Entidad actual</h4>
        <div class="entity-card">
          <div class="entity-icon-wrapper">
            <i :class="getEntityIcon(entity.type)"></i>
          </div>
          <div class="entity-details">
            <span class="entity-name">{{ entity.name }}</span>
            <span class="entity-stats">{{ entity.mentionCount }} apariciones</span>
          </div>
        </div>
      </div>

      <!-- Entidades a restaurar -->
      <div v-if="mergeHistory" class="restore-section">
        <h4>Se restaurarán las siguientes entidades:</h4>
        <div class="entities-to-restore">
          <div
            v-for="(name, index) in mergeHistory.sourceEntityNames"
            :key="index"
            class="restore-entity-item"
          >
            <i class="pi pi-replay restore-icon"></i>
            <span class="restore-name">{{ name }}</span>
          </div>
        </div>

        <div class="merge-info">
          <span class="merge-date">
            <i class="pi pi-calendar"></i>
            Fusionado el {{ formatDate(mergeHistory.mergedAt) }}
          </span>
          <span v-if="mergeHistory.note" class="merge-note">
            <i class="pi pi-comment"></i>
            {{ mergeHistory.note }}
          </span>
        </div>
      </div>

      <!-- Loading state si no tenemos historial -->
      <div v-else-if="loading" class="loading-state">
        <i class="pi pi-spin pi-spinner"></i>
        <span>Cargando información de fusión...</span>
      </div>

      <!-- Sin historial -->
      <div v-else class="no-history">
        <Message severity="error" :closable="false">
          No se encontró información de fusión para esta entidad.
        </Message>
      </div>
    </div>

    <template #footer>
      <Button
        label="Cancelar"
        icon="pi pi-times"
        text
        @click="$emit('update:visible', false)"
      />
      <Button
        label="Deshacer Fusión"
        icon="pi pi-replay"
        severity="warning"
        :loading="undoing"
        :disabled="!mergeHistory"
        @click="confirmUndo"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import type { Entity, MergeHistoryEntry } from '@/types'
import { transformMergeHistoryEntry } from '@/types/transformers'
import { api } from '@/services/apiClient'

const toast = useToast()

const props = defineProps<{
  visible: boolean
  projectId: number
  entity: Entity | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'undo-complete': [restoredEntityIds: number[]]
}>()

const loading = ref(false)
const undoing = ref(false)
const mergeHistory = ref<MergeHistoryEntry | null>(null)

// Cargar historial cuando el dialog se abre
watch(() => props.visible, async (isVisible) => {
  if (isVisible && props.entity) {
    await loadMergeHistory()
  } else {
    mergeHistory.value = null
  }
})

const loadMergeHistory = async () => {
  if (!props.entity || props.entity.mergedFromIds.length === 0) {
    return
  }

  loading.value = true
  try {
    // Obtener el historial de fusiones del proyecto
    const data = await api.getRaw<any>(`/api/projects/${props.projectId}/entities/merge-history`)

    if (data.success && data.data.merges) {
      // Buscar la fusión más reciente que creó esta entidad
      const relevantMerge = data.data.merges.find(
        (m: any) => m.target_id === props.entity?.id && !m.undone_at
      )

      if (relevantMerge) {
        mergeHistory.value = transformMergeHistoryEntry(relevantMerge)
      }
    }
  } catch (error) {
    console.error('Error loading merge history:', error)
  } finally {
    loading.value = false
  }
}

const confirmUndo = async () => {
  if (!mergeHistory.value) return

  undoing.value = true
  try {
    const data = await api.postRaw<any>(
      `/api/projects/${props.projectId}/entities/undo-merge/${mergeHistory.value.id}`
    )

    if (data.success) {
      emit('undo-complete', data.data.restored_entity_ids || [])
      emit('update:visible', false)
      toast.add({ severity: 'success', summary: 'Fusión deshecha', detail: 'Las entidades originales han sido restauradas', life: 3000 })
    } else {
      console.error('Error undoing merge:', data.error)
      toast.add({ severity: 'error', summary: 'Error', detail: `Error al deshacer fusión: ${data.error}`, life: 5000 })
    }
  } catch (error) {
    console.error('Error undoing merge:', error)
    toast.add({ severity: 'error', summary: 'Error de conexión', detail: 'No se pudo deshacer la fusión', life: 5000 })
  } finally {
    undoing.value = false
  }
}

const formatDate = (date: Date): string => {
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'character': 'pi pi-user',
    'location': 'pi pi-map-marker',
    'organization': 'pi pi-building',
    'object': 'pi pi-box',
    'event': 'pi pi-calendar',
    'concept': 'pi pi-lightbulb',
    'other': 'pi pi-tag'
  }
  return icons[type] || 'pi pi-tag'
}
</script>

<style scoped>
.undo-merge-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.entity-info-section h4,
.restore-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.entity-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
}

.entity-icon-wrapper {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 50%;
  flex-shrink: 0;
}

.entity-icon-wrapper i {
  font-size: 1.125rem;
  color: var(--primary-color);
}

.entity-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.entity-name {
  font-weight: 600;
  color: var(--text-color);
}

.entity-stats {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.entities-to-restore {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.restore-entity-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.restore-icon {
  color: var(--green-600);
}

.restore-name {
  font-weight: 500;
  color: var(--text-color);
}

.merge-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.merge-info i {
  margin-right: 0.5rem;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.no-history {
  padding: 1rem 0;
}
</style>
