<script setup lang="ts">
/**
 * GlossaryTab - Gestión del glosario del proyecto
 *
 * Permite al usuario definir términos propios del manuscrito con:
 * - Definiciones para humanos y LLM
 * - Variantes del término (aliases)
 * - Categorización (personaje, lugar, objeto, concepto, técnico)
 * - Flags para términos inventados, técnicos, etc.
 * - Exportación para publicación
 */

import { ref, computed, onMounted, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DsInput from '@/components/ds/DsInput.vue'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import Chips from 'primevue/chips'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import { apiUrl } from '@/config/api'

interface GlossaryEntry {
  id: number
  project_id: number
  term: string
  definition: string
  variants: string[]
  category: string
  subcategory?: string
  context_notes: string
  related_terms: string[]
  usage_example: string
  is_technical: boolean
  is_invented: boolean
  is_proper_noun: boolean
  include_in_publication_glossary: boolean
  usage_count: number
  first_chapter?: number
  created_at?: string
  updated_at?: string
}

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()
const confirm = useConfirm()

// Interfaces adicionales
interface GlossarySuggestion {
  term: string
  reason: string
  category_hint: string
  confidence: number
  frequency: number
  first_chapter?: number
  contexts: string[]
  is_likely_invented: boolean
  is_likely_technical: boolean
  is_likely_proper_noun: boolean
}

// Estado
const entries = ref<GlossaryEntry[]>([])
const loading = ref(false)
const searchQuery = ref('')
const selectedCategory = ref<string | null>(null)
const showEditDialog = ref(false)
const editingEntry = ref<Partial<GlossaryEntry> | null>(null)
const saving = ref(false)

// Estado de sugerencias
const suggestions = ref<GlossarySuggestion[]>([])
const loadingSuggestions = ref(false)
const showSuggestions = ref(false)
const acceptingSuggestion = ref<string | null>(null)

// Opciones de categoría
const categoryOptions = [
  { label: 'Todas', value: null },
  { label: 'General', value: 'general' },
  { label: 'Personaje', value: 'personaje' },
  { label: 'Lugar', value: 'lugar' },
  { label: 'Objeto', value: 'objeto' },
  { label: 'Concepto', value: 'concepto' },
  { label: 'Técnico', value: 'técnico' },
]

const categoryLabels: Record<string, string> = {
  general: 'General',
  personaje: 'Personaje',
  lugar: 'Lugar',
  objeto: 'Objeto',
  concepto: 'Concepto',
  'técnico': 'Técnico',
}

// Entradas filtradas
const filteredEntries = computed(() => {
  let result = entries.value

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(e =>
      e.term.toLowerCase().includes(query) ||
      e.definition.toLowerCase().includes(query) ||
      e.variants.some(v => v.toLowerCase().includes(query))
    )
  }

  // Filtrar por categoría
  if (selectedCategory.value) {
    result = result.filter(e => e.category === selectedCategory.value)
  }

  return result
})

// Estadísticas
const stats = computed(() => {
  const byCategory: Record<string, number> = {}
  let technical = 0
  let invented = 0
  let forPublication = 0

  for (const entry of entries.value) {
    const cat = entry.category || 'general'
    byCategory[cat] = (byCategory[cat] || 0) + 1
    if (entry.is_technical) technical++
    if (entry.is_invented) invented++
    if (entry.include_in_publication_glossary) forPublication++
  }

  return {
    total: entries.value.length,
    byCategory,
    technical,
    invented,
    forPublication,
  }
})

// Cargar entradas al montar
onMounted(() => {
  loadEntries()
})

// Recargar si cambia el proyecto
watch(() => props.projectId, () => {
  loadEntries()
})

async function loadEntries() {
  loading.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/glossary`)
    )
    const data = await response.json()

    if (data.success) {
      entries.value = data.data.entries
    }
  } catch (error) {
    console.error('Error loading glossary:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo cargar el glosario',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function openNewEntryDialog() {
  editingEntry.value = {
    term: '',
    definition: '',
    variants: [],
    category: 'general',
    context_notes: '',
    related_terms: [],
    usage_example: '',
    is_technical: false,
    is_invented: false,
    is_proper_noun: false,
    include_in_publication_glossary: false,
  }
  showEditDialog.value = true
}

function openEditDialog(entry: GlossaryEntry) {
  editingEntry.value = { ...entry }
  showEditDialog.value = true
}

async function saveEntry() {
  if (!editingEntry.value) return
  if (!editingEntry.value.term?.trim() || !editingEntry.value.definition?.trim()) {
    toast.add({
      severity: 'warn',
      summary: 'Datos incompletos',
      detail: 'El término y la definición son obligatorios',
      life: 3000
    })
    return
  }

  saving.value = true
  try {
    const isNew = !editingEntry.value.id
    const url = isNew
      ? apiUrl(`/api/projects/${props.projectId}/glossary`)
      : apiUrl(`/api/projects/${props.projectId}/glossary/${editingEntry.value.id}`)

    const response = await fetch(url, {
      method: isNew ? 'POST' : 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editingEntry.value)
    })
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: isNew ? 'Creado' : 'Actualizado',
        detail: data.message || `Término "${editingEntry.value.term}" guardado`,
        life: 3000
      })
      showEditDialog.value = false
      editingEntry.value = null
      await loadEntries()
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudo guardar el término',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(entry: GlossaryEntry) {
  confirm.require({
    message: `¿Eliminar "${entry.term}" del glosario?`,
    header: 'Confirmar eliminación',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Eliminar',
    rejectLabel: 'Cancelar',
    accept: () => deleteEntry(entry),
  })
}

async function deleteEntry(entry: GlossaryEntry) {
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/glossary/${entry.id}`),
      { method: 'DELETE' }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Eliminado',
        detail: `Término "${entry.term}" eliminado del glosario`,
        life: 3000
      })
      await loadEntries()
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudo eliminar el término',
      life: 3000
    })
  }
}

function getCategoryTagSeverity(category: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' | undefined {
  const map: Record<string, 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast'> = {
    personaje: 'info',
    lugar: 'success',
    objeto: 'warn',
    concepto: 'secondary',
    'técnico': 'danger',
    general: 'contrast',
  }
  return map[category] || 'secondary'
}

async function exportForPublication() {
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/glossary/export/publication`)
    )
    const data = await response.json()

    if (data.success && data.data.content) {
      // Copiar al portapapeles
      await navigator.clipboard.writeText(data.data.content)
      toast.add({
        severity: 'success',
        summary: 'Exportado',
        detail: 'Glosario copiado al portapapeles (formato Markdown)',
        life: 3000
      })
    } else if (data.success && !data.data.content) {
      toast.add({
        severity: 'info',
        summary: 'Sin contenido',
        detail: 'No hay términos marcados para publicación',
        life: 3000
      })
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar el glosario',
      life: 3000
    })
  }
}

async function loadSuggestions() {
  loadingSuggestions.value = true
  showSuggestions.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/glossary/suggestions?max_suggestions=30`)
    )
    const data = await response.json()

    if (data.success) {
      suggestions.value = data.data.suggestions
      if (suggestions.value.length === 0) {
        toast.add({
          severity: 'info',
          summary: 'Sin sugerencias',
          detail: 'No se encontraron términos candidatos para el glosario',
          life: 3000
        })
      }
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    console.error('Error loading suggestions:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudieron cargar las sugerencias',
      life: 3000
    })
  } finally {
    loadingSuggestions.value = false
  }
}

async function acceptSuggestion(suggestion: GlossarySuggestion) {
  acceptingSuggestion.value = suggestion.term
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/glossary/suggestions/accept`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term: suggestion.term,
          definition: '',
          category: suggestion.category_hint,
          is_technical: suggestion.is_likely_technical,
          is_invented: suggestion.is_likely_invented,
          is_proper_noun: suggestion.is_likely_proper_noun,
        })
      }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Añadido',
        detail: `"${suggestion.term}" añadido al glosario`,
        life: 3000
      })
      // Eliminar de sugerencias
      suggestions.value = suggestions.value.filter(s => s.term !== suggestion.term)
      // Recargar glosario
      await loadEntries()
      // Abrir editor para completar definición
      const newEntry = entries.value.find(e => e.term === suggestion.term)
      if (newEntry) {
        openEditDialog(newEntry)
      }
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudo añadir el término',
      life: 3000
    })
  } finally {
    acceptingSuggestion.value = null
  }
}

function dismissSuggestion(suggestion: GlossarySuggestion) {
  suggestions.value = suggestions.value.filter(s => s.term !== suggestion.term)
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'var(--ds-color-success)'
  if (confidence >= 0.6) return 'var(--ds-color-info)'
  return 'var(--ds-color-warning)'
}
</script>

<template>
  <div class="glossary-tab">
    <ConfirmDialog />

    <!-- Header con estadísticas y acciones -->
    <div class="glossary-tab__header">
      <div class="glossary-tab__stats">
        <span class="glossary-tab__stat">
          <i class="pi pi-book" />
          {{ stats.total }} términos
        </span>
        <span v-if="stats.invented > 0" class="glossary-tab__stat glossary-tab__stat--invented">
          <i class="pi pi-star" />
          {{ stats.invented }} inventados
        </span>
        <span v-if="stats.technical > 0" class="glossary-tab__stat glossary-tab__stat--technical">
          <i class="pi pi-cog" />
          {{ stats.technical }} técnicos
        </span>
        <span v-if="stats.forPublication > 0" class="glossary-tab__stat glossary-tab__stat--publication">
          <i class="pi pi-file-export" />
          {{ stats.forPublication }} para publicación
        </span>
      </div>

      <div class="glossary-tab__actions">
        <Button
          label="Sugerir términos"
          icon="pi pi-sparkles"
          severity="help"
          size="small"
          :loading="loadingSuggestions"
          @click="loadSuggestions"
          title="Extraer automáticamente términos candidatos del manuscrito"
        />
        <Button
          v-if="stats.forPublication > 0"
          label="Exportar"
          icon="pi pi-download"
          severity="secondary"
          size="small"
          @click="exportForPublication"
        />
        <Button
          label="Nuevo término"
          icon="pi pi-plus"
          size="small"
          @click="openNewEntryDialog"
        />
      </div>
    </div>

    <!-- Filtros -->
    <div class="glossary-tab__filters">
      <DsInput
        v-model="searchQuery"
        placeholder="Buscar término..."
        icon="pi pi-search"
        clearable
        class="glossary-tab__search"
      />

      <Select
        v-model="selectedCategory"
        :options="categoryOptions"
        option-label="label"
        option-value="value"
        placeholder="Categoría"
        class="glossary-tab__category-filter"
      />
    </div>

    <!-- Panel de sugerencias -->
    <div v-if="showSuggestions && suggestions.length > 0" class="glossary-tab__suggestions">
      <div class="glossary-tab__suggestions-header">
        <div class="glossary-tab__suggestions-title">
          <i class="pi pi-sparkles" />
          <span>Sugerencias automáticas</span>
          <Tag :value="`${suggestions.length}`" severity="info" />
        </div>
        <Button
          icon="pi pi-times"
          severity="secondary"
          text
          rounded
          size="small"
          @click="showSuggestions = false; suggestions = []"
          title="Cerrar sugerencias"
        />
      </div>
      <div class="glossary-tab__suggestions-list">
        <div
          v-for="suggestion in suggestions"
          :key="suggestion.term"
          class="glossary-tab__suggestion-card"
        >
          <div class="glossary-tab__suggestion-main">
            <span class="glossary-tab__suggestion-term">{{ suggestion.term }}</span>
            <div class="glossary-tab__suggestion-meta">
              <Tag
                :value="categoryLabels[suggestion.category_hint] || suggestion.category_hint"
                :severity="getCategoryTagSeverity(suggestion.category_hint)"
                class="glossary-tab__suggestion-category"
              />
              <span class="glossary-tab__suggestion-freq">{{ suggestion.frequency }}×</span>
              <span
                class="glossary-tab__suggestion-confidence"
                :style="{ color: getConfidenceColor(suggestion.confidence) }"
                :title="`Confianza: ${Math.round(suggestion.confidence * 100)}%`"
              >
                {{ Math.round(suggestion.confidence * 100) }}%
              </span>
            </div>
          </div>
          <div class="glossary-tab__suggestion-reason">
            {{ suggestion.reason }}
          </div>
          <div v-if="suggestion.contexts.length > 0" class="glossary-tab__suggestion-context">
            <i class="pi pi-quote-left" />
            <span>{{ suggestion.contexts[0] }}</span>
          </div>
          <div class="glossary-tab__suggestion-actions">
            <Button
              icon="pi pi-check"
              label="Añadir"
              size="small"
              :loading="acceptingSuggestion === suggestion.term"
              @click="acceptSuggestion(suggestion)"
            />
            <Button
              icon="pi pi-times"
              severity="secondary"
              text
              size="small"
              title="Ignorar"
              @click="dismissSuggestion(suggestion)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Lista de términos -->
    <div class="glossary-tab__content">
      <DsEmptyState
        v-if="!loading && entries.length === 0"
        icon="pi pi-book"
        title="Glosario vacío"
        description="Añade términos propios de tu manuscrito: personajes, lugares inventados, términos técnicos, etc."
      >
        <template #action>
          <Button
            label="Añadir primer término"
            icon="pi pi-plus"
            @click="openNewEntryDialog"
          />
        </template>
      </DsEmptyState>

      <DsEmptyState
        v-else-if="!loading && filteredEntries.length === 0"
        icon="pi pi-search"
        title="Sin resultados"
        description="No hay términos que coincidan con los filtros."
      />

      <DataTable
        v-else
        :value="filteredEntries"
        :loading="loading"
        data-key="id"
        striped-rows
        scrollable
        scroll-height="calc(100vh - 300px)"
        class="glossary-tab__table"
      >
        <Column field="term" header="Término" sortable style="min-width: 150px">
          <template #body="{ data }">
            <div class="glossary-tab__term-cell">
              <span class="glossary-tab__term-name">{{ data.term }}</span>
              <div v-if="data.variants.length > 0" class="glossary-tab__variants">
                <Tag
                  v-for="v in data.variants.slice(0, 3)"
                  :key="v"
                  :value="v"
                  severity="secondary"
                  class="glossary-tab__variant-tag"
                />
                <span v-if="data.variants.length > 3" class="glossary-tab__more-variants">
                  +{{ data.variants.length - 3 }}
                </span>
              </div>
            </div>
          </template>
        </Column>

        <Column field="definition" header="Definición" style="min-width: 300px">
          <template #body="{ data }">
            <span class="glossary-tab__definition">{{ data.definition }}</span>
          </template>
        </Column>

        <Column field="category" header="Categoría" sortable style="width: 120px">
          <template #body="{ data }">
            <Tag
              :value="categoryLabels[data.category] || data.category"
              :severity="getCategoryTagSeverity(data.category)"
            />
          </template>
        </Column>

        <Column header="Flags" style="width: 100px">
          <template #body="{ data }">
            <div class="glossary-tab__flags">
              <i
                v-if="data.is_invented"
                class="pi pi-star"
                title="Inventado"
                style="color: var(--ds-color-warning)"
              />
              <i
                v-if="data.is_technical"
                class="pi pi-cog"
                title="Técnico"
                style="color: var(--ds-color-info)"
              />
              <i
                v-if="data.is_proper_noun"
                class="pi pi-user"
                title="Nombre propio"
                style="color: var(--ds-color-secondary)"
              />
              <i
                v-if="data.include_in_publication_glossary"
                class="pi pi-file-export"
                title="Para publicación"
                style="color: var(--ds-color-success)"
              />
            </div>
          </template>
        </Column>

        <Column field="usage_count" header="Usos" sortable style="width: 80px">
          <template #body="{ data }">
            <span class="glossary-tab__usage-count">{{ data.usage_count || 0 }}</span>
          </template>
        </Column>

        <Column header="Acciones" style="width: 100px">
          <template #body="{ data }">
            <div class="glossary-tab__row-actions">
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text
                rounded
                size="small"
                title="Editar"
                @click="openEditDialog(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                size="small"
                title="Eliminar"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Diálogo de edición -->
    <Dialog
      v-model:visible="showEditDialog"
      :header="editingEntry?.id ? 'Editar término' : 'Nuevo término'"
      modal
      :style="{ width: '600px' }"
      :closable="!saving"
      :close-on-escape="!saving"
    >
      <div v-if="editingEntry" class="glossary-dialog">
        <!-- Término -->
        <div class="glossary-dialog__field">
          <label for="term">Término *</label>
          <InputText
            id="term"
            v-model="editingEntry.term"
            placeholder="Nombre del término"
            class="w-full"
          />
        </div>

        <!-- Definición -->
        <div class="glossary-dialog__field">
          <label for="definition">Definición *</label>
          <Textarea
            id="definition"
            v-model="editingEntry.definition"
            placeholder="Definición clara del término"
            rows="3"
            class="w-full"
          />
          <small class="text-muted">Esta definición se usará como contexto para el chat con el LLM.</small>
        </div>

        <!-- Variantes -->
        <div class="glossary-dialog__field">
          <label for="variants">Variantes / Aliases</label>
          <Chips
            id="variants"
            v-model="editingEntry.variants"
            placeholder="Añadir variante y Enter"
            class="w-full"
          />
          <small class="text-muted">Otras formas en que aparece este término en el texto.</small>
        </div>

        <!-- Categoría -->
        <div class="glossary-dialog__field">
          <label for="category">Categoría</label>
          <Select
            id="category"
            v-model="editingEntry.category"
            :options="categoryOptions.filter(o => o.value)"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar categoría"
            class="w-full"
          />
        </div>

        <!-- Notas de contexto -->
        <div class="glossary-dialog__field">
          <label for="context_notes">Notas de contexto</label>
          <Textarea
            id="context_notes"
            v-model="editingEntry.context_notes"
            placeholder="Notas adicionales para el LLM (ej: solo aparece en capítulos 3-5)"
            rows="2"
            class="w-full"
          />
        </div>

        <!-- Ejemplo de uso -->
        <div class="glossary-dialog__field">
          <label for="usage_example">Ejemplo de uso</label>
          <InputText
            id="usage_example"
            v-model="editingEntry.usage_example"
            placeholder="Frase de ejemplo"
            class="w-full"
          />
        </div>

        <!-- Flags -->
        <div class="glossary-dialog__flags">
          <div class="glossary-dialog__flag">
            <Checkbox
              id="is_invented"
              v-model="editingEntry.is_invented"
              :binary="true"
            />
            <label for="is_invented">Término inventado</label>
          </div>
          <div class="glossary-dialog__flag">
            <Checkbox
              id="is_technical"
              v-model="editingEntry.is_technical"
              :binary="true"
            />
            <label for="is_technical">Término técnico</label>
          </div>
          <div class="glossary-dialog__flag">
            <Checkbox
              id="is_proper_noun"
              v-model="editingEntry.is_proper_noun"
              :binary="true"
            />
            <label for="is_proper_noun">Nombre propio</label>
          </div>
          <div class="glossary-dialog__flag">
            <Checkbox
              id="include_in_publication_glossary"
              v-model="editingEntry.include_in_publication_glossary"
              :binary="true"
            />
            <label for="include_in_publication_glossary">Incluir en glosario de publicación</label>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          text
          :disabled="saving"
          @click="showEditDialog = false"
        />
        <Button
          :label="editingEntry?.id ? 'Guardar cambios' : 'Crear término'"
          icon="pi pi-check"
          :loading="saving"
          @click="saveEntry"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.glossary-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--ds-space-4);
  gap: var(--ds-space-4);
}

.glossary-tab__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.glossary-tab__stats {
  display: flex;
  gap: var(--ds-space-4);
}

.glossary-tab__stat {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.glossary-tab__stat i {
  font-size: 1rem;
}

.glossary-tab__stat--invented i {
  color: var(--ds-color-warning);
}

.glossary-tab__stat--technical i {
  color: var(--ds-color-info);
}

.glossary-tab__stat--publication i {
  color: var(--ds-color-success);
}

.glossary-tab__actions {
  display: flex;
  gap: var(--ds-space-2);
}

.glossary-tab__filters {
  display: flex;
  gap: var(--ds-space-3);
}

.glossary-tab__search {
  width: 250px;
}

.glossary-tab__category-filter {
  width: 150px;
}

.glossary-tab__content {
  flex: 1;
  overflow: hidden;
}

.glossary-tab__table {
  height: 100%;
}

.glossary-tab__term-cell {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.glossary-tab__term-name {
  font-weight: var(--ds-font-weight-semibold);
}

.glossary-tab__variants {
  display: flex;
  gap: var(--ds-space-1);
  flex-wrap: wrap;
}

.glossary-tab__variant-tag {
  font-size: var(--ds-font-size-xs);
}

.glossary-tab__more-variants {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
}

.glossary-tab__definition {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.glossary-tab__flags {
  display: flex;
  gap: var(--ds-space-2);
}

.glossary-tab__usage-count {
  color: var(--ds-color-text-secondary);
}

.glossary-tab__row-actions {
  display: flex;
  gap: var(--ds-space-1);
}

/* Dialog styles */
.glossary-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.glossary-dialog__field {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.glossary-dialog__field label {
  font-weight: var(--ds-font-weight-medium);
}

.glossary-dialog__field small {
  color: var(--ds-color-text-tertiary);
}

.glossary-dialog__flags {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ds-space-3);
}

.glossary-dialog__flag {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.text-muted {
  color: var(--ds-color-text-tertiary);
}

.w-full {
  width: 100%;
}

/* Suggestions panel styles */
.glossary-tab__suggestions {
  background: var(--ds-color-surface-secondary);
  border: 1px solid var(--ds-color-border);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-3);
  max-height: 300px;
  display: flex;
  flex-direction: column;
}

.glossary-tab__suggestions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ds-space-3);
}

.glossary-tab__suggestions-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-primary);
}

.glossary-tab__suggestions-title i {
  color: var(--ds-color-help);
}

.glossary-tab__suggestions-list {
  display: flex;
  gap: var(--ds-space-2);
  overflow-x: auto;
  padding-bottom: var(--ds-space-2);
}

.glossary-tab__suggestion-card {
  flex: 0 0 auto;
  width: 280px;
  background: var(--ds-color-surface-primary);
  border: 1px solid var(--ds-color-border);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.glossary-tab__suggestion-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.glossary-tab__suggestion-term {
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-md);
}

.glossary-tab__suggestion-meta {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.glossary-tab__suggestion-freq {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
}

.glossary-tab__suggestion-confidence {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
}

.glossary-tab__suggestion-reason {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.glossary-tab__suggestion-context {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  font-style: italic;
  display: flex;
  gap: var(--ds-space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.glossary-tab__suggestion-context i {
  flex-shrink: 0;
  opacity: 0.5;
}

.glossary-tab__suggestion-actions {
  display: flex;
  gap: var(--ds-space-2);
  margin-top: auto;
}
</style>
