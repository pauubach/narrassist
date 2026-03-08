<template>
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Ubicación de datos</label>
      <p class="setting-description">
        Los proyectos se guardan en: <code>{{ dataLocation }}</code>
      </p>
    </div>
    <div class="setting-control">
      <Button
        label="Cambiar ubicación"
        icon="pi pi-folder-open"
        outlined
        @click="$emit('changeDataLocation')"
      />
    </div>
  </div>

  <Message severity="info" :closable="false" class="info-message">
    <span class="message-content">
      <strong>Modo 100% offline:</strong> Tus manuscritos nunca salen de tu máquina.
      Esta aplicación no envía datos a internet excepto para verificación de licencia.
    </span>
  </Message>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Modelos de analisis del texto</label>
      <p class="setting-description">Verificar y preparar los recursos de analisis necesarios</p>
    </div>
    <div class="setting-control">
      <Button
        :label="nlpDownloading ? 'Descargando...' : 'Verificar modelos'"
        icon="pi pi-download"
        severity="secondary"
        outlined
        :loading="nlpDownloading"
        @click="redownloadNLPModels"
      />
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Limpiar caché</label>
      <p class="setting-description">Eliminar archivos temporales y caché de modelos</p>
    </div>
    <div class="setting-control">
      <Button
        label="Limpiar caché"
        icon="pi pi-trash"
        severity="secondary"
        outlined
        @click="clearCache"
      />
    </div>
  </div>

  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Restablecer configuración</label>
      <p class="setting-description">Volver a la configuración por defecto</p>
    </div>
    <div class="setting-control">
      <Button
        label="Restablecer"
        icon="pi pi-refresh"
        severity="danger"
        outlined
        @click="$emit('confirmReset')"
      />
    </div>
  </div>

  <Divider />

  <div class="setting-item column">
    <div class="setting-info">
      <label class="setting-label">Entidades rechazadas (global)</label>
      <p class="setting-description">
        Textos marcados como "no es una entidad" en todos tus proyectos.
        Al restaurar, volverán a detectarse en futuros análisis.
      </p>
    </div>

    <div v-if="loadingRejections" class="loading-patterns">
      <i class="pi pi-spin pi-spinner"></i>
      <span>Cargando...</span>
    </div>

    <div v-else-if="userRejections.length === 0" class="empty-rejections">
      <i class="pi pi-check-circle"></i>
      <span>No hay entidades rechazadas globalmente</span>
    </div>

    <div v-else class="user-rejections-list">
      <div
        v-for="rejection in userRejections"
        :key="rejection.id"
        class="rejection-item"
      >
        <div class="rejection-info">
          <span class="rejection-name">{{ rejection.entityName }}</span>
          <Tag
            v-if="rejection.entityType"
            :value="rejection.entityType"
            severity="secondary"
            class="rejection-type"
          />
          <span v-if="rejection.reason" class="rejection-reason">
            — {{ rejection.reason }}
          </span>
        </div>
        <Button
          v-tooltip.left="'Restaurar: volver a detectar esta entidad'"
          :aria-label="`Restaurar entidad rechazada ${rejection.entityName}`"
          icon="pi pi-undo"
          severity="secondary"
          text
          rounded
          size="small"
          @click="removeRejection(rejection)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import { api } from '@/services/apiClient'
import { useToast } from 'primevue/usetoast'
import { useSystemStore } from '@/stores/system'
import { logError } from '@/services/logger'

defineProps<{
  dataLocation: string
}>()

defineEmits<{
  changeDataLocation: []
  confirmReset: []
}>()

const toast = useToast()
const systemStore = useSystemStore()

// NLP model download
const nlpDownloading = ref(false)

async function redownloadNLPModels() {
  nlpDownloading.value = true
  try {
    const ok = await systemStore.downloadModels(['spacy', 'embeddings', 'transformer_ner'])
    if (ok) {
      toast.add({ severity: 'success', summary: 'Recursos verificados', detail: 'Los recursos de analisis estan disponibles.', life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: 'No se pudo completar', detail: systemStore.modelsError || 'No se pudieron preparar los recursos. El sistema puede seguir ocupado; espera unos segundos y reintenta.', life: 6000 })
    }
  } finally {
    nlpDownloading.value = false
  }
}

// Cache
async function clearCache() {
  try {
    await api.postRaw('/api/maintenance/clear-cache')
    toast.add({ severity: 'success', summary: 'Caché limpiado', detail: 'Los archivos temporales se han eliminado', life: 3000 })
  } catch (error) {
    logError('DataMaintenanceSection', 'Error clearing cache:', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo limpiar el caché', life: 3000 })
  }
}

// User rejections
interface UserRejection {
  id: number
  entityName: string
  entityType: string | null
  reason: string | null
  rejectedAt: string
}

const userRejections = ref<UserRejection[]>([])
const loadingRejections = ref(false)

async function loadUserRejections() {
  loadingRejections.value = true
  try {
    const data = await api.getRaw<{ success: boolean; data?: UserRejection[] }>('/api/entity-filters/user-rejections')
    if (data.success && data.data) {
      userRejections.value = data.data
    }
  } catch {} finally {
    loadingRejections.value = false
  }
}

async function removeRejection(rejection: UserRejection) {
  try {
    const data = await api.del<{ success: boolean }>(`/api/entity-filters/user-rejections/${rejection.id}`)
    if (data.success) {
      userRejections.value = userRejections.value.filter(r => r.id !== rejection.id)
      toast.add({
        severity: 'success',
        summary: 'Entidad restaurada',
        detail: `"${rejection.entityName}" volverá a detectarse en futuros análisis`,
        life: 3000,
      })
    }
  } catch (e) {
    logError('DataMaintenanceSection', 'Error removing rejection:', e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo restaurar la entidad',
      life: 3000,
    })
  }
}

defineExpose({ loadUserRejections })
</script>
