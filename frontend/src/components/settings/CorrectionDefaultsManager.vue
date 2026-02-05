<template>
  <div class="correction-defaults-manager">
    <!-- Header -->
    <div class="manager-header">
      <div class="header-info">
        <h4>Personalizar defaults por tipo</h4>
        <p class="header-description">
          Modifica los valores predeterminados para tipos y subtipos de documento.
          Estos cambios se aplicarán a proyectos nuevos.
        </p>
      </div>
      <div class="header-actions">
        <Button
          v-if="totalOverrides > 0"
          label="Restaurar todo"
          icon="pi pi-refresh"
          severity="danger"
          text
          size="small"
          @click="confirmResetAll"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <span>Cargando configuración...</span>
    </div>

    <!-- Error -->
    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- Types List -->
    <div v-else class="types-list">
      <Accordion multiple>
        <AccordionPanel
          v-for="typeEntry in typesWithStatus"
          :key="typeEntry.code"
          :value="typeEntry.code"
        >
          <AccordionHeader>
            <div class="type-header">
              <div class="type-info">
                <i :class="typeEntry.icon" :style="{ color: typeEntry.color }"></i>
                <span class="type-name">{{ typeEntry.name }}</span>
                <Badge
                  v-if="typeEntry.hasOverrides"
                  value="Modificado"
                  severity="warn"
                  class="modified-badge"
                />
              </div>
              <div class="type-actions" @click.stop>
                <Button
                  v-tooltip.top="'Editar defaults del tipo'"
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  @click="editType(typeEntry.code)"
                />
                <Button
                  v-if="typeEntry.hasTypeOverride"
                  v-tooltip.top="'Restaurar tipo'"
                  icon="pi pi-undo"
                  text
                  rounded
                  size="small"
                  severity="secondary"
                  @click="resetType(typeEntry.code)"
                />
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="subtypes-list">
              <div
                v-for="subtype in typeEntry.subtypes"
                :key="subtype.code"
                class="subtype-row"
              >
                <div class="subtype-info">
                  <span class="subtype-name">{{ subtype.name }}</span>
                  <Tag
                    v-if="subtype.hasOverride"
                    value="Modificado"
                    severity="warn"
                    size="small"
                  />
                </div>
                <div class="subtype-actions">
                  <Button
                    v-tooltip.top="'Editar defaults'"
                    icon="pi pi-pencil"
                    text
                    rounded
                    size="small"
                    @click="editSubtype(typeEntry.code, subtype.code)"
                  />
                  <Button
                    v-if="subtype.hasOverride"
                    v-tooltip.top="'Restaurar'"
                    icon="pi pi-undo"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    @click="resetSubtype(typeEntry.code, subtype.code)"
                  />
                </div>
              </div>
              <div v-if="typeEntry.subtypes.length === 0" class="no-subtypes">
                Este tipo no tiene subtipos definidos
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>
    </div>

    <!-- Edit Modal -->
    <CorrectionConfigModal
      ref="configModal"
      :project-id="0"
      :editing-defaults="true"
      :defaults-type-code="editingTypeCode"
      :defaults-subtype-code="editingSubtypeCode"
      @saved="onDefaultsSaved"
    />

    <!-- Confirm Reset All Dialog -->
    <Dialog
      v-model:visible="showResetAllDialog"
      modal
      header="Restaurar todos los defaults"
      :style="{ width: '450px' }"
    >
      <p>
        ¿Estás seguro de que deseas restaurar TODOS los defaults a sus valores originales?
      </p>
      <p class="reset-warning">
        <i class="pi pi-exclamation-triangle"></i>
        Se eliminarán {{ totalOverrides }} personalizaciones.
      </p>
      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          @click="showResetAllDialog = false"
        />
        <Button
          label="Restaurar todo"
          severity="danger"
          icon="pi pi-refresh"
          :loading="resetting"
          @click="resetAll"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import CorrectionConfigModal from '../workspace/CorrectionConfigModal.vue'
import { apiUrl } from '@/config/api'

interface SubtypeInfo {
  code: string
  name: string
  hasOverride: boolean
}

interface TypeWithStatus {
  code: string
  name: string
  description: string
  icon: string
  color: string
  hasOverrides: boolean
  hasTypeOverride: boolean
  subtypes: SubtypeInfo[]
}

const toast = useToast()

// State
const loading = ref(true)
const error = ref<string | null>(null)
const types = ref<TypeWithStatus[]>([])
const overridesStatus = ref<Record<string, { has_type_override: boolean; subtype_overrides: string[] }>>({})
const showResetAllDialog = ref(false)
const resetting = ref(false)

// Edit state
const configModal = ref<InstanceType<typeof CorrectionConfigModal> | null>(null)
const editingTypeCode = ref<string | null>(null)
const editingSubtypeCode = ref<string | null>(null)

// Computed
const totalOverrides = computed(() => {
  return Object.values(overridesStatus.value).reduce(
    (sum, status) => sum + (status.has_type_override ? 1 : 0) + status.subtype_overrides.length,
    0
  )
})

const typesWithStatus = computed((): TypeWithStatus[] => {
  return types.value.map(type => {
    const status = overridesStatus.value[type.code] || { has_type_override: false, subtype_overrides: [] }
    return {
      ...type,
      hasTypeOverride: status.has_type_override,
      hasOverrides: status.has_type_override || status.subtype_overrides.length > 0,
      subtypes: (type.subtypes || []).map(sub => ({
        ...sub,
        hasOverride: status.subtype_overrides.includes(sub.code)
      }))
    }
  })
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // Load types with subtypes
    const typesRes = await fetch(apiUrl('/api/correction-config/types'))
    const typesData = await typesRes.json()
    if (typesData.success && Array.isArray(typesData.data)) {
      types.value = typesData.data.map((t: any) => {
        // Normalize icon: backend returns "pi-book", we need "pi pi-book"
        let icon = t.icon || 'pi-file'
        if (!icon.startsWith('pi ')) {
          icon = `pi ${icon}`
        }
        return {
          code: t.code,
          name: t.name,
          description: t.description,
          icon,
          color: t.color || '#6366f1',
          subtypes: t.subtypes || []
        }
      })
    }

    // Load overrides status
    const statusRes = await fetch(apiUrl('/api/correction-config/defaults/status'))
    const statusData = await statusRes.json()
    if (statusData.success && statusData.data?.status) {
      overridesStatus.value = statusData.data.status
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error cargando configuración'
  } finally {
    loading.value = false
  }
}

const editType = (typeCode: string) => {
  editingTypeCode.value = typeCode
  editingSubtypeCode.value = null
  configModal.value?.show()
}

const editSubtype = (typeCode: string, subtypeCode: string) => {
  editingTypeCode.value = typeCode
  editingSubtypeCode.value = subtypeCode
  configModal.value?.show()
}

const resetType = async (typeCode: string) => {
  try {
    const response = await fetch(apiUrl(`/api/correction-config/defaults/${typeCode}`), {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Defaults restaurados',
        detail: `Configuración del tipo restaurada`,
        life: 3000
      })
      await loadData()
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo restaurar la configuración',
      life: 5000
    })
  }
}

const resetSubtype = async (typeCode: string, subtypeCode: string) => {
  try {
    const response = await fetch(apiUrl(`/api/correction-config/defaults/${typeCode}?subtype_code=${subtypeCode}`), {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Defaults restaurados',
        detail: `Configuración del subtipo restaurada`,
        life: 3000
      })
      await loadData()
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo restaurar la configuración',
      life: 5000
    })
  }
}

const confirmResetAll = () => {
  showResetAllDialog.value = true
}

const resetAll = async () => {
  resetting.value = true
  try {
    const response = await fetch(apiUrl('/api/correction-config/defaults'), {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Todo restaurado',
        detail: data.data.message,
        life: 3000
      })
      showResetAllDialog.value = false
      await loadData()
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo restaurar la configuración',
      life: 5000
    })
  } finally {
    resetting.value = false
  }
}

const onDefaultsSaved = () => {
  loadData()
}

// Lifecycle
onMounted(() => {
  loadData()
})

// Expose for parent
defineExpose({
  refresh: loadData
})
</script>

<style scoped>
.correction-defaults-manager {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.header-info h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.header-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  justify-content: center;
  color: var(--text-color-secondary);
}

.types-list {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  overflow: hidden;
}

.type-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 0.5rem;
}

.type-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.type-info i {
  font-size: 1.25rem;
}

.type-name {
  font-weight: 600;
}

.modified-badge {
  font-size: 0.7rem;
}

.type-actions {
  display: flex;
  gap: 0.25rem;
}

.subtypes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

.subtype-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: var(--surface-ground);
  border-radius: 6px;
  margin: 0 0.5rem;
}

.subtype-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.subtype-name {
  font-size: 0.9rem;
}

.subtype-actions {
  display: flex;
  gap: 0.25rem;
}

.no-subtypes {
  padding: 1rem;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-style: italic;
}

.reset-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--red-500);
  font-weight: 500;
}

.reset-warning i {
  font-size: 1rem;
}
</style>
