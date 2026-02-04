<template>
  <div class="focalization-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-eye"></i>
          Focalización Narrativa
        </h3>
        <p class="subtitle">
          Declara el punto de vista de cada capítulo y detecta violaciones.
          <span class="info-tooltip" v-tooltip.right="'La focalización es declarativa: tú defines qué tipo de narrador usa cada capítulo (omnisciente, primera persona, etc.) y el sistema detecta violaciones a esa declaración, como cuando un narrador limitado conoce pensamientos de otros personajes.'">
            <i class="pi pi-info-circle"></i>
          </span>
        </p>
      </div>
      <div class="header-controls">
        <Button
          label="Detectar violaciones"
          icon="pi pi-search"
          :loading="detectingViolations"
          :disabled="declarations.length === 0"
          @click="detectViolations"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando declaraciones...</p>
    </div>

    <!-- Content -->
    <div v-else class="content-container">
      <!-- Stats Summary -->
      <div v-if="declarations.length > 0 || violations.length > 0" class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ declarations.length }}</div>
              <div class="stat-label">Declaraciones</div>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="violations.length > 0 ? 'text-danger' : 'text-success'">
                {{ violations.length }}
              </div>
              <div class="stat-label">Violaciones</div>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ chaptersWithDeclaration }}/{{ totalChapters }}</div>
              <div class="stat-label">Capítulos declarados</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Chapters List -->
      <Card class="chapters-card">
        <template #title>
          <div class="card-title-row">
            <span><i class="pi pi-list"></i> Capítulos</span>
            <Button
              v-if="undeclaredChapters.length > 0"
              label="Sugerir faltantes"
              icon="pi pi-lightbulb"
              text
              size="small"
              :loading="suggesting"
              @click="suggestAllUndeclared"
            />
          </div>
        </template>
        <template #content>
          <div class="chapters-list">
            <div
              v-for="chapter in chaptersWithStatus"
              :key="chapter.number"
              class="chapter-row"
              :class="{ 'has-violations': chapter.violationsCount > 0 }"
            >
              <div class="chapter-info">
                <span class="chapter-number">Cap. {{ chapter.number }}</span>
                <span class="chapter-title">{{ chapter.title }}</span>
              </div>

              <div v-if="chapter.declaration" class="chapter-declaration">
                <Tag :severity="getFocalizationSeverity(chapter.declaration.focalization_type)">
                  {{ getFocalizationLabel(chapter.declaration.focalization_type) }}
                </Tag>
                <span v-if="chapter.declaration.focalizer_ids?.length" class="focalizers">
                  {{ getFocalizerNames(chapter.declaration.focalizer_ids) }}
                </span>
                <Tag v-if="chapter.violationsCount > 0" severity="danger" size="small">
                  {{ chapter.violationsCount }} violaciones
                </Tag>
              </div>
              <div v-else class="chapter-declaration">
                <Tag severity="secondary">Sin declarar</Tag>
              </div>

              <div class="chapter-actions">
                <Button
                  v-if="!chapter.declaration"
                  v-tooltip.top="'Sugerir'"
                  icon="pi pi-lightbulb"
                  text
                  rounded
                  size="small"
                  :loading="suggestingChapter === chapter.number"
                  @click="suggestFocalization(chapter.number)"
                />
                <Button
                  v-tooltip.top="chapter.declaration ? 'Editar' : 'Declarar'"
                  :icon="chapter.declaration ? 'pi pi-pencil' : 'pi pi-plus'"
                  text
                  rounded
                  size="small"
                  @click="openDeclarationDialog(chapter)"
                />
                <Button
                  v-if="chapter.declaration"
                  v-tooltip.top="'Eliminar'"
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  @click="deleteDeclaration(chapter.declaration.id)"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Violations Section -->
      <Card v-if="violations.length > 0" class="violations-card">
        <template #title>
          <i class="pi pi-exclamation-triangle"></i>
          Violaciones Detectadas ({{ violations.length }})
        </template>
        <template #content>
          <Accordion :multiple="true" class="violations-accordion">
            <AccordionPanel v-for="(group, chapterNum) in violationsByChapter" :key="chapterNum" :value="String(chapterNum)">
              <AccordionHeader>
                <div class="violation-chapter-header">
                  <span>Capítulo {{ chapterNum }}</span>
                  <Tag severity="danger" size="small">{{ group.length }}</Tag>
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="violations-list">
                  <div v-for="(v, idx) in group" :key="idx" class="violation-item" :class="'severity-' + v.severity">
                    <div class="violation-header">
                      <Tag :severity="getViolationSeverity(v.severity)">{{ getViolationTypeLabel(v.violation_type) }}</Tag>
                      <span v-if="v.entity_name" class="violation-entity">{{ v.entity_name }}</span>
                    </div>
                    <p class="violation-explanation">{{ v.explanation }}</p>
                    <div v-if="v.text_excerpt" class="violation-excerpt">
                      <small>"{{ v.text_excerpt }}"</small>
                    </div>
                    <div v-if="v.suggestion" class="violation-suggestion">
                      <i class="pi pi-lightbulb"></i>
                      <small>{{ v.suggestion }}</small>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
        </template>
      </Card>

      <!-- No Violations Message -->
      <Message v-else-if="declarations.length > 0 && hasDetectedViolations" severity="success" :closable="false">
        <i class="pi pi-check-circle"></i>
        No se detectaron violaciones de focalización.
      </Message>
    </div>

    <!-- Declaration Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingDeclaration ? 'Editar Focalización' : 'Declarar Focalización'"
      modal
      :style="{ width: '500px' }"
    >
      <div class="dialog-content">
        <div class="field">
          <label>Capítulo</label>
          <InputNumber v-model="dialogData.chapter" :disabled="!!editingDeclaration" :min="1" fluid />
        </div>

        <div class="field">
          <label>Tipo de Focalización</label>
          <Select
            v-model="dialogData.focalization_type"
            :options="focalizationTypes"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar tipo"
            fluid
          />
        </div>

        <div v-if="needsFocalizers" class="field">
          <label>Focalizador(es)</label>
          <MultiSelect
            v-model="dialogData.focalizer_ids"
            :options="characters"
            option-label="name"
            option-value="id"
            placeholder="Seleccionar personajes"
            :max-selected-labels="3"
            fluid
          />
        </div>

        <div class="field">
          <label>Notas (opcional)</label>
          <Textarea v-model="dialogData.notes" rows="3" fluid />
        </div>

        <!-- Suggestion Preview -->
        <div v-if="currentSuggestion" class="suggestion-preview">
          <h5><i class="pi pi-lightbulb"></i> Sugerencia del sistema</h5>
          <p>
            Tipo: <Tag :severity="getFocalizationSeverity(currentSuggestion.suggested_type)">
              {{ getFocalizationLabel(currentSuggestion.suggested_type) }}
            </Tag>
            ({{ Math.round(currentSuggestion.confidence * 100) }}% confianza)
          </p>
          <ul v-if="currentSuggestion.evidence?.length">
            <li v-for="(ev, i) in currentSuggestion.evidence" :key="i">{{ ev }}</li>
          </ul>
          <Button
            label="Aplicar sugerencia"
            icon="pi pi-check"
            size="small"
            @click="applySuggestion"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="closeDialog" />
        <Button
          :label="editingDeclaration ? 'Guardar' : 'Crear'"
          icon="pi pi-check"
          :loading="saving"
          @click="saveDeclaration"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Textarea from 'primevue/textarea'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { apiUrl } from '@/config/api'

interface Declaration {
  id: number
  project_id: number
  chapter: number
  scene?: number
  focalization_type: string
  focalizer_ids: number[]
  notes: string
  is_validated: boolean
  violations_count: number
}

interface Violation {
  violation_type: string
  severity: string
  chapter: number
  position: number
  text_excerpt: string
  entity_name?: string
  explanation: string
  suggestion?: string
}

interface Character {
  id: number
  name: string
}

interface Chapter {
  number: number
  title: string
}

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const declarations = ref<Declaration[]>([])
const violations = ref<Violation[]>([])
const chapters = ref<Chapter[]>([])
const characters = ref<Character[]>([])
const hasDetectedViolations = ref(false)
const detectingViolations = ref(false)
const suggesting = ref(false)
const suggestingChapter = ref<number | null>(null)
const saving = ref(false)

// Dialog
const showDialog = ref(false)
const editingDeclaration = ref<Declaration | null>(null)
const currentSuggestion = ref<any>(null)
const dialogData = ref({
  chapter: 1,
  focalization_type: 'zero',
  focalizer_ids: [] as number[],
  notes: '',
})

// Options
const focalizationTypes = [
  { value: 'zero', label: 'Omnisciente (Zero)' },
  { value: 'internal_fixed', label: 'Interna Fija (1 personaje)' },
  { value: 'internal_variable', label: 'Interna Variable (cambia por escena)' },
  { value: 'internal_multiple', label: 'Interna Múltiple (varios simultáneos)' },
  { value: 'external', label: 'Externa (solo observable)' },
]

// Computed
const totalChapters = computed(() => chapters.value.length)
const chaptersWithDeclaration = computed(() =>
  declarations.value.filter(d => chapters.value.some(c => c.number === d.chapter)).length
)
const undeclaredChapters = computed(() =>
  chapters.value.filter(c => !declarations.value.some(d => d.chapter === c.number))
)

const chaptersWithStatus = computed(() => {
  return chapters.value.map(ch => {
    const declaration = declarations.value.find(d => d.chapter === ch.number)
    const chapterViolations = violations.value.filter(v => v.chapter === ch.number)
    return {
      ...ch,
      declaration,
      violationsCount: chapterViolations.length,
    }
  })
})

const violationsByChapter = computed(() => {
  const grouped: Record<number, Violation[]> = {}
  for (const v of violations.value) {
    if (!grouped[v.chapter]) grouped[v.chapter] = []
    grouped[v.chapter].push(v)
  }
  return grouped
})

const needsFocalizers = computed(() => {
  const type = dialogData.value.focalization_type
  return type === 'internal_fixed' || type === 'internal_variable' || type === 'internal_multiple'
})

// Lifecycle
onMounted(() => {
  loadData()
})

watch(() => props.projectId, () => {
  loadData()
})

// Methods
async function loadData() {
  loading.value = true
  try {
    await Promise.all([
      loadDeclarations(),
      loadChapters(),
      loadCharacters(),
    ])
  } finally {
    loading.value = false
  }
}

async function loadDeclarations() {
  try {
    const res = await fetch(apiUrl(`/api/projects/${props.projectId}/focalization`))
    const data = await res.json()
    if (data.success) {
      declarations.value = data.data.declarations || []
    }
  } catch (e) {
    console.error('Error loading focalizations:', e)
  }
}

async function loadChapters() {
  try {
    const res = await fetch(apiUrl(`/api/projects/${props.projectId}/chapters`))
    const data = await res.json()
    if (data.success) {
      chapters.value = (data.data || []).map((c: any) => ({
        number: c.chapter_number,
        title: c.title || `Capítulo ${c.chapter_number}`,
      }))
    }
  } catch (e) {
    console.error('Error loading chapters:', e)
  }
}

async function loadCharacters() {
  try {
    const res = await fetch(apiUrl(`/api/projects/${props.projectId}/entities`))
    const data = await res.json()
    if (data.success) {
      characters.value = (data.data || [])
        .filter((e: any) => e.entity_type === 'PER')
        .map((e: any) => ({ id: e.id, name: e.canonical_name || e.name }))
    }
  } catch (e) {
    console.error('Error loading characters:', e)
  }
}

async function detectViolations() {
  detectingViolations.value = true
  try {
    const res = await fetch(apiUrl(`/api/projects/${props.projectId}/focalization/violations`))
    const data = await res.json()
    if (data.success) {
      violations.value = data.data.violations || []
      hasDetectedViolations.value = true
      toast.add({
        severity: violations.value.length > 0 ? 'warn' : 'success',
        summary: violations.value.length > 0 ? 'Violaciones detectadas' : 'Sin violaciones',
        detail: `Se encontraron ${violations.value.length} violaciones de focalización`,
        life: 3000,
      })
    }
  } catch (e) {
    console.error('Error detecting violations:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron detectar violaciones', life: 3000 })
  } finally {
    detectingViolations.value = false
  }
}

async function suggestFocalization(chapterNum: number) {
  suggestingChapter.value = chapterNum
  try {
    const res = await fetch(
      apiUrl(`/api/projects/${props.projectId}/chapters/${chapterNum}/focalization/suggest`)
    )
    const data = await res.json()
    if (data.success) {
      currentSuggestion.value = data.data
      const chapter = chapters.value.find(c => c.number === chapterNum)
      openDeclarationDialog({ number: chapterNum, title: chapter?.title || '', declaration: null })
    }
  } catch (e) {
    console.error('Error suggesting focalization:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo obtener sugerencia', life: 3000 })
  } finally {
    suggestingChapter.value = null
  }
}

async function suggestAllUndeclared() {
  suggesting.value = true
  for (const ch of undeclaredChapters.value.slice(0, 5)) {
    await suggestFocalization(ch.number)
    break // Solo abrir el primero
  }
  suggesting.value = false
}

function openDeclarationDialog(chapter: any) {
  editingDeclaration.value = chapter.declaration || null
  dialogData.value = {
    chapter: chapter.number,
    focalization_type: chapter.declaration?.focalization_type || 'zero',
    focalizer_ids: chapter.declaration?.focalizer_ids || [],
    notes: chapter.declaration?.notes || '',
  }
  if (!chapter.declaration) {
    currentSuggestion.value = null
  }
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
  editingDeclaration.value = null
  currentSuggestion.value = null
}

function applySuggestion() {
  if (currentSuggestion.value) {
    dialogData.value.focalization_type = currentSuggestion.value.suggested_type
    dialogData.value.focalizer_ids = currentSuggestion.value.suggested_focalizers?.map((f: any) => f.id) || []
  }
}

async function saveDeclaration() {
  saving.value = true
  try {
    const url = editingDeclaration.value
      ? apiUrl(`/api/projects/${props.projectId}/focalization/${editingDeclaration.value.id}`)
      : apiUrl(`/api/projects/${props.projectId}/focalization`)

    const res = await fetch(url, {
      method: editingDeclaration.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dialogData.value),
    })
    const data = await res.json()

    if (data.success) {
      toast.add({ severity: 'success', summary: 'Guardado', detail: 'Focalización guardada', life: 3000 })
      closeDialog()
      await loadDeclarations()
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: data.error, life: 3000 })
    }
  } catch (e) {
    console.error('Error saving declaration:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar', life: 3000 })
  } finally {
    saving.value = false
  }
}

async function deleteDeclaration(id: number) {
  try {
    const res = await fetch(apiUrl(`/api/projects/${props.projectId}/focalization/${id}`), {
      method: 'DELETE',
    })
    const data = await res.json()
    if (data.success) {
      toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Declaración eliminada', life: 3000 })
      await loadDeclarations()
    }
  } catch (e) {
    console.error('Error deleting declaration:', e)
  }
}

// Helpers
function getFocalizationLabel(type: string): string {
  const labels: Record<string, string> = {
    zero: 'Omnisciente',
    internal_fixed: 'Interna Fija',
    internal_variable: 'Interna Variable',
    internal_multiple: 'Interna Múltiple',
    external: 'Externa',
  }
  return labels[type] || type
}

function getFocalizationSeverity(type: string): string {
  const severities: Record<string, string> = {
    zero: 'info',
    internal_fixed: 'success',
    internal_variable: 'warn',
    internal_multiple: 'secondary',
    external: 'contrast',
  }
  return severities[type] || 'secondary'
}

function getFocalizerNames(ids: number[]): string {
  return ids
    .map(id => characters.value.find(c => c.id === id)?.name || `#${id}`)
    .join(', ')
}

function getViolationTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    forbidden_mind_access: 'Acceso mental prohibido',
    thought_in_external: 'Pensamiento en externa',
    inconsistent_perception: 'Percepción inconsistente',
    unmarked_focalizer_change: 'Cambio sin marca',
    omniscient_leak: 'Filtración omnisciente',
  }
  return labels[type] || type
}

function getViolationSeverity(severity: string): string {
  return severity === 'high' ? 'danger' : severity === 'medium' ? 'warn' : 'secondary'
}
</script>

<style scoped>
.focalization-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-3);
  height: 100%;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
}

.header-left h3 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0;
  font-size: var(--ds-font-size-lg);
}

.header-left .subtitle {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-tooltip {
  display: inline-flex;
  align-items: center;
  color: var(--primary-color);
  cursor: help;
}

.info-tooltip i {
  font-size: 0.9rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-8);
  color: var(--ds-color-text-secondary);
}

/* Stats */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--ds-space-3);
}

.stat-card :deep(.p-card-body) {
  padding: var(--ds-space-3);
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
}

.stat-value.text-danger { color: #ef4444; }
.stat-value.text-success { color: #22c55e; }

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-top: var(--ds-space-1);
}

/* Chapters Card */
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.chapters-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.chapter-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid transparent;
}

.chapter-row.has-violations {
  border-left-color: #ef4444;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  min-width: 200px;
}

.chapter-number {
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-secondary);
}

.chapter-title {
  color: var(--ds-color-text-primary);
}

.chapter-declaration {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.focalizers {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.chapter-actions {
  display: flex;
  gap: var(--ds-space-1);
}

/* Violations */
.violations-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: #ef4444;
}

.violation-chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.violations-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.violation-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-surface-border);
}

.violation-item.severity-high {
  border-left-color: #ef4444;
}

.violation-item.severity-medium {
  border-left-color: #f97316;
}

.violation-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.violation-entity {
  font-weight: var(--ds-font-weight-medium);
}

.violation-explanation {
  margin: 0 0 var(--ds-space-2);
}

.violation-excerpt {
  padding: var(--ds-space-2);
  background: var(--ds-surface-card);
  border-radius: var(--ds-radius-sm);
  font-style: italic;
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-2);
}

.violation-suggestion {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--p-green-50);
  border-radius: var(--ds-radius-sm);
  color: var(--p-green-700);
}

/* Dialog */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.field label {
  font-weight: var(--ds-font-weight-medium);
  font-size: var(--ds-font-size-sm);
}

.suggestion-preview {
  padding: var(--ds-space-3);
  background: var(--p-blue-50);
  border-radius: var(--ds-radius-md);
}

.suggestion-preview h5 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0 0 var(--ds-space-2);
  color: var(--p-blue-700);
}

.suggestion-preview ul {
  margin: var(--ds-space-2) 0;
  padding-left: var(--ds-space-4);
  font-size: var(--ds-font-size-sm);
}
</style>
