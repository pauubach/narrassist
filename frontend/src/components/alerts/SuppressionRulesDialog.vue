<script setup lang="ts">
/**
 * SuppressionRulesDialog — Gestión de reglas de supresión de alertas.
 *
 * Muestra tabla de reglas existentes con opción de eliminar,
 * y formulario para crear nuevas reglas.
 */
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { api } from '@/services/apiClient'
import { useToast } from 'primevue/usetoast'
import type { ApiResponse } from '@/types/api'
import type { SuppressionRuleType, SuppressionRule } from '@/types'

interface Props {
  visible: boolean
  projectId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'rules-changed': []
}>()

const toast = useToast()
const loading = ref(false)
const rules = ref<SuppressionRule[]>([])

// Form state
const newRuleType = ref<SuppressionRuleType>('alert_type')
const newPattern = ref('')
const newEntityName = ref('')
const newReason = ref('')
const creating = ref(false)

const RULE_TYPE_LABELS: Record<SuppressionRuleType, string> = {
  alert_type: 'Tipo de alerta',
  category: 'Categoría',
  entity: 'Entidad',
  source_module: 'Módulo',
}

const RULE_TYPE_OPTIONS = Object.entries(RULE_TYPE_LABELS).map(([value, label]) => ({
  value,
  label,
}))

const PATTERN_PLACEHOLDERS: Record<SuppressionRuleType, string> = {
  alert_type: 'Ej: spelling_*, grammar_agreement',
  category: 'Ej: ortografía, concordancia',
  entity: 'Ej: * (todas)',
  source_module: 'Ej: grammar_checker',
}

const patternPlaceholder = computed(() => PATTERN_PLACEHOLDERS[newRuleType.value])
const showEntityName = computed(() => newRuleType.value === 'entity')
const canCreate = computed(() => newPattern.value.trim().length > 0)

function transformRule(raw: Record<string, unknown>): SuppressionRule {
  return {
    id: raw.id as number,
    projectId: raw.project_id as number,
    ruleType: raw.rule_type as SuppressionRuleType,
    pattern: raw.pattern as string,
    entityName: (raw.entity_name as string) || null,
    reason: (raw.reason as string) || null,
    isActive: raw.is_active as boolean,
    createdAt: raw.created_at ? new Date(raw.created_at as string) : null,
  }
}

async function loadRules() {
  if (!props.projectId) return
  loading.value = true
  try {
    const res = await api.get<ApiResponse>(`/api/projects/${props.projectId}/suppression-rules`)
    if (res.success && Array.isArray(res.data)) {
      rules.value = (res.data as Record<string, unknown>[]).map(transformRule)
    }
  } catch (e) {
    console.error('Error loading suppression rules:', e)
  } finally {
    loading.value = false
  }
}

async function createRule() {
  if (!canCreate.value) return
  creating.value = true
  try {
    const body: Record<string, string> = {
      rule_type: newRuleType.value,
      pattern: newPattern.value.trim(),
    }
    if (showEntityName.value && newEntityName.value.trim()) {
      body.entity_name = newEntityName.value.trim()
    }
    if (newReason.value.trim()) {
      body.reason = newReason.value.trim()
    }
    const res = await api.post<ApiResponse>(`/api/projects/${props.projectId}/suppression-rules`, body)
    if (res.success) {
      toast.add({ severity: 'success', summary: 'Regla creada', life: 2000 })
      newPattern.value = ''
      newEntityName.value = ''
      newReason.value = ''
      await loadRules()
      emit('rules-changed')
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: res.error || 'No se pudo crear la regla', life: 3000 })
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error de conexión', life: 3000 })
  } finally {
    creating.value = false
  }
}

async function deleteRule(ruleId: number) {
  try {
    const res = await api.del<ApiResponse>(`/api/projects/${props.projectId}/suppression-rules/${ruleId}`)
    if (res.success) {
      toast.add({ severity: 'info', summary: 'Regla eliminada', life: 2000 })
      await loadRules()
      emit('rules-changed')
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 3000 })
  }
}

function formatDate(date: Date | null): string {
  if (!date) return '—'
  return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
}

watch(() => props.visible, (v) => {
  if (v) loadRules()
})
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    header="Reglas de supresión"
    :modal="true"
    :style="{ width: '700px' }"
    :closable="true"
  >
    <!-- Create form -->
    <div class="sr-form">
      <div class="sr-form-row">
        <Select
          v-model="newRuleType"
          :options="RULE_TYPE_OPTIONS"
          option-label="label"
          option-value="value"
          class="sr-select"
        />
        <InputText
          v-model="newPattern"
          :placeholder="patternPlaceholder"
          class="sr-input"
          @keydown.enter="createRule"
        />
      </div>
      <div v-if="showEntityName" class="sr-form-row">
        <InputText
          v-model="newEntityName"
          placeholder="Nombre de entidad (opcional)"
          class="sr-input-full"
        />
      </div>
      <div class="sr-form-row">
        <InputText
          v-model="newReason"
          placeholder="Razón (opcional)"
          class="sr-input-full"
        />
        <Button
          label="Añadir"
          icon="pi pi-plus"
          size="small"
          :disabled="!canCreate"
          :loading="creating"
          @click="createRule"
        />
      </div>
    </div>

    <!-- Rules table -->
    <DataTable
      :value="rules"
      :loading="loading"
      size="small"
      striped-rows
      class="sr-table"
    >
      <template #empty>
        <div class="sr-empty">No hay reglas de supresión configuradas</div>
      </template>
      <Column field="ruleType" header="Tipo" :style="{ width: '120px' }">
        <template #body="{ data }">
          <Tag :value="RULE_TYPE_LABELS[data.ruleType as SuppressionRuleType]" severity="secondary" />
        </template>
      </Column>
      <Column field="pattern" header="Patrón" />
      <Column field="entityName" header="Entidad" :style="{ width: '120px' }">
        <template #body="{ data }">{{ data.entityName || '—' }}</template>
      </Column>
      <Column field="reason" header="Razón">
        <template #body="{ data }">{{ data.reason || '—' }}</template>
      </Column>
      <Column field="createdAt" header="Fecha" :style="{ width: '100px' }">
        <template #body="{ data }">{{ formatDate(data.createdAt) }}</template>
      </Column>
      <Column :style="{ width: '50px' }">
        <template #body="{ data }">
          <Button
            icon="pi pi-trash"
            text
            rounded
            size="small"
            severity="danger"
            @click="deleteRule(data.id)"
          />
        </template>
      </Column>
    </DataTable>
  </Dialog>
</template>

<style scoped>
.sr-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--surface-200);
}

.sr-form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.sr-select {
  width: 180px;
  flex-shrink: 0;
}

.sr-input {
  flex: 1;
}

.sr-input-full {
  flex: 1;
}

.sr-table {
  margin-top: 0.5rem;
}

.sr-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}
</style>
