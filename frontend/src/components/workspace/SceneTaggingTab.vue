<template>
  <div class="scene-tagging-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-images"></i>
          Escenas
        </h3>
        <p class="subtitle">
          Etiqueta las escenas por tipo, tono y participantes.
        </p>
      </div>
      <div class="header-controls">
        <div class="view-toggle">
          <Button
            v-tooltip.top="'Vista lista'"
            icon="pi pi-list"
            :text="viewMode !== 'list'"
            :outlined="viewMode === 'list'"
            size="small"
            severity="secondary"
            @click="viewMode = 'list'"
          />
          <Button
            v-tooltip.top="'Vista tarjetas'"
            icon="pi pi-th-large"
            :text="viewMode !== 'cards'"
            :outlined="viewMode === 'cards'"
            size="small"
            severity="secondary"
            @click="viewMode = 'cards'"
          />
        </div>
        <Select
          v-model="filterType"
          :options="sceneTypeOptions"
          option-label="label"
          option-value="value"
          placeholder="Filtrar por tipo"
          show-clear
          class="filter-dropdown"
        />
        <Select
          v-model="filterTone"
          :options="toneOptions"
          option-label="label"
          option-value="value"
          placeholder="Filtrar por tono"
          show-clear
          class="filter-dropdown"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando escenas...</p>
    </div>

    <!-- No scenes message -->
    <div v-else-if="!hasScenes" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Este proyecto no tiene estructura de escenas detectada.</p>
      <small>Las escenas se detectan automáticamente en manuscritos narrativos mediante separadores como * * *, ---, etc.</small>
    </div>

    <!-- Content -->
    <div v-else class="content-container">
      <!-- Stats Summary -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_scenes }}</div>
              <div class="stat-label">Escenas</div>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ stats.chapters_with_scenes }}</div>
              <div class="stat-label">Capítulos con escenas</div>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value text-success">{{ stats.tagged_scenes }}</div>
              <div class="stat-label">Etiquetadas</div>
            </div>
          </template>
        </Card>
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="stats.untagged_scenes > 0 ? 'text-warning' : ''">
                {{ stats.untagged_scenes }}
              </div>
              <div class="stat-label">Sin etiquetar</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Cards View -->
      <SceneCardsView
        v-if="viewMode === 'cards'"
        :scenes="filteredScenes"
        :project-id="projectId"
        @tag-scene="(id) => openTagDialog(scenes.find(s => s.id === id))"
        @select-scene="(id) => openTagDialog(scenes.find(s => s.id === id))"
      />

      <!-- List View: Scenes by Chapter -->
      <Accordion v-if="viewMode === 'list'" :multiple="true" class="scenes-accordion">
        <AccordionPanel v-for="(chapterScenes, chapterNum) in scenesByChapter" :key="chapterNum" :value="String(chapterNum)">
          <AccordionHeader>
            <div class="chapter-header">
              <span class="chapter-title">
                <i class="pi pi-book"></i>
                Capítulo {{ chapterNum }}
                <span v-if="chapterScenes[0]?.chapter_title" class="chapter-subtitle">
                  - {{ chapterScenes[0].chapter_title }}
                </span>
              </span>
              <Tag severity="secondary" size="small">{{ chapterScenes.length }} escenas</Tag>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="scenes-list">
              <div
                v-for="scene in chapterScenes"
                :key="scene.id"
                class="scene-row"
                :class="{ 'is-tagged': scene.tags?.scene_type || scene.tags?.tone }"
              >
                <div class="scene-info">
                  <div class="scene-number">
                    <i class="pi pi-bookmark"></i>
                    Escena {{ scene.scene_number }}
                  </div>
                  <div class="scene-excerpt">{{ scene.excerpt }}</div>
                  <div class="scene-meta">
                    <span class="word-count">
                      <i class="pi pi-align-left"></i>
                      {{ scene.word_count }} palabras
                    </span>
                  </div>
                </div>

                <div class="scene-tags">
                  <!-- Predefined Tags -->
                  <Tag
                    v-if="scene.tags?.scene_type"
                    :severity="getTypeTagSeverity(scene.tags.scene_type)"
                  >
                    {{ getTypeLabel(scene.tags.scene_type) }}
                  </Tag>
                  <Tag
                    v-if="scene.tags?.tone"
                    :severity="getToneTagSeverity(scene.tags.tone)"
                  >
                    {{ getToneLabel(scene.tags.tone) }}
                  </Tag>
                  <Tag
                    v-if="scene.tags?.location_name"
                    severity="info"
                  >
                    <i class="pi pi-map-marker"></i>
                    {{ scene.tags.location_name }}
                  </Tag>

                  <!-- Custom Tags -->
                  <Tag
                    v-for="ct in scene.custom_tags"
                    :key="ct.name"
                    :style="ct.color ? { backgroundColor: ct.color } : {}"
                    class="custom-tag"
                  >
                    {{ ct.name }}
                    <i
                      class="pi pi-times remove-tag"
                      @click.stop="removeCustomTag(scene.id, ct.name)"
                    ></i>
                  </Tag>
                </div>

                <div class="scene-actions">
                  <Button
                    v-tooltip.top="'Etiquetar'"
                    icon="pi pi-tag"
                    text
                    rounded
                    size="small"
                    @click="openTagDialog(scene)"
                  />
                  <Button
                    v-tooltip.top="'Añadir etiqueta personalizada'"
                    icon="pi pi-plus"
                    text
                    rounded
                    size="small"
                    @click="openCustomTagDialog(scene)"
                  />
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

      <!-- Custom Tags Used -->
      <Card v-if="stats.custom_tags_used?.length > 0" class="custom-tags-card">
        <template #title>
          <i class="pi pi-tags"></i>
          Etiquetas personalizadas usadas
        </template>
        <template #content>
          <div class="custom-tags-list">
            <Tag
              v-for="tag in stats.custom_tags_used"
              :key="tag"
              severity="secondary"
              class="clickable-tag"
              @click="filterByCustomTag(tag)"
            >
              {{ tag }}
            </Tag>
          </div>
        </template>
      </Card>
    </div>

    <!-- Tag Dialog -->
    <Dialog
      v-model:visible="showTagDialog"
      :header="tagDialogTitle"
      modal
      :style="{ width: '500px' }"
      :closable="true"
    >
      <div class="tag-form">
        <div class="form-field">
          <label>Tipo de escena</label>
          <Select
            v-model="tagForm.scene_type"
            :options="sceneTypeOptions"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar tipo"
            show-clear
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Tono emocional</label>
          <Select
            v-model="tagForm.tone"
            :options="toneOptions"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar tono"
            show-clear
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Ubicación</label>
          <Select
            v-model="tagForm.location_entity_id"
            :options="locationEntities"
            option-label="name"
            option-value="id"
            placeholder="Seleccionar ubicación"
            show-clear
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Participantes</label>
          <MultiSelect
            v-model="tagForm.participant_ids"
            :options="characterEntities"
            option-label="name"
            option-value="id"
            placeholder="Seleccionar personajes"
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Resumen</label>
          <Textarea
            v-model="tagForm.summary"
            placeholder="Breve resumen de la escena..."
            rows="2"
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Notas</label>
          <Textarea
            v-model="tagForm.notes"
            placeholder="Notas adicionales..."
            rows="2"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="showTagDialog = false" />
        <Button label="Guardar" icon="pi pi-check" :loading="saving" @click="saveSceneTags" />
      </template>
    </Dialog>

    <!-- Custom Tag Dialog -->
    <Dialog
      v-model:visible="showCustomTagDialog"
      header="Añadir etiqueta personalizada"
      modal
      :style="{ width: '400px' }"
    >
      <div class="custom-tag-form">
        <div class="form-field">
          <label>Nombre de la etiqueta</label>
          <AutoComplete
            v-model="customTagForm.name"
            :suggestions="tagSuggestions"
            placeholder="Ej: importante, revisar, clave..."
            class="w-full"
            @complete="searchTags"
          />
        </div>
        <div class="form-field">
          <label>Color (opcional)</label>
          <ColorPicker v-model="customTagForm.color" />
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="showCustomTagDialog = false" />
        <Button
          label="Añadir"
          icon="pi pi-plus"
          :loading="saving"
          :disabled="!customTagForm.name?.trim()"
          @click="saveCustomTag"
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
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Textarea from 'primevue/textarea'
import AutoComplete from 'primevue/autocomplete'
import ColorPicker from 'primevue/colorpicker'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import SceneCardsView from './SceneCardsView.vue'
import { apiUrl } from '@/config/api'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// View mode
const viewMode = ref<'list' | 'cards'>('list')

// State
const loading = ref(true)
const saving = ref(false)
const hasScenes = ref(false)
const scenes = ref<any[]>([])
const stats = ref({
  total_scenes: 0,
  chapters_with_scenes: 0,
  tagged_scenes: 0,
  untagged_scenes: 0,
  scenes_by_type: {},
  scenes_by_tone: {},
  custom_tags_used: [],
})

// Filters
const filterType = ref<string | null>(null)
const filterTone = ref<string | null>(null)

// Entities for dropdowns
const characterEntities = ref<any[]>([])
const locationEntities = ref<any[]>([])

// Tag Dialog
const showTagDialog = ref(false)
const selectedScene = ref<any>(null)
const tagForm = ref({
  scene_type: null as string | null,
  tone: null as string | null,
  location_entity_id: null as number | null,
  participant_ids: [] as number[],
  summary: '',
  notes: '',
})

// Custom Tag Dialog
const showCustomTagDialog = ref(false)
const customTagForm = ref({
  name: '',
  color: '',
})
const tagSuggestions = ref<string[]>([])

// Options
const sceneTypeOptions = [
  { label: 'Acción', value: 'action' },
  { label: 'Diálogo', value: 'dialogue' },
  { label: 'Exposición', value: 'exposition' },
  { label: 'Introspección', value: 'introspection' },
  { label: 'Flashback', value: 'flashback' },
  { label: 'Sueño', value: 'dream' },
  { label: 'Transición', value: 'transition' },
  { label: 'Mixto', value: 'mixed' },
]

const toneOptions = [
  { label: 'Tenso', value: 'tense' },
  { label: 'Calmo', value: 'calm' },
  { label: 'Alegre', value: 'happy' },
  { label: 'Triste', value: 'sad' },
  { label: 'Romántico', value: 'romantic' },
  { label: 'Misterioso', value: 'mysterious' },
  { label: 'Ominoso', value: 'ominous' },
  { label: 'Esperanzador', value: 'hopeful' },
  { label: 'Nostálgico', value: 'nostalgic' },
  { label: 'Neutro', value: 'neutral' },
]

// Computed
const scenesByChapter = computed(() => {
  const filtered = filteredScenes.value
  const grouped: Record<number, any[]> = {}

  for (const scene of filtered) {
    const chapterNum = scene.chapter_number || 0
    if (!grouped[chapterNum]) {
      grouped[chapterNum] = []
    }
    grouped[chapterNum].push(scene)
  }

  return grouped
})

const filteredScenes = computed(() => {
  let result = scenes.value

  if (filterType.value) {
    result = result.filter(s => s.tags?.scene_type === filterType.value)
  }

  if (filterTone.value) {
    result = result.filter(s => s.tags?.tone === filterTone.value)
  }

  return result
})

const tagDialogTitle = computed(() => {
  if (!selectedScene.value) return 'Etiquetar escena'
  return `Etiquetar escena ${selectedScene.value.scene_number} - Cap. ${selectedScene.value.chapter_number}`
})

// Methods
async function loadScenes() {
  loading.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/scenes`)
    )
    const data = await response.json()

    if (data.success) {
      hasScenes.value = data.data.has_scenes
      scenes.value = data.data.scenes || []
      stats.value = data.data.stats || stats.value
    }
  } catch (error) {
    console.error('Error loading scenes:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron cargar las escenas',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

async function loadEntities() {
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/entities`)
    )
    const data = await response.json()

    if (data.success) {
      const entities = data.data.entities || []
      characterEntities.value = entities.filter((e: any) => e.entity_type === 'PER')
      locationEntities.value = entities.filter((e: any) => e.entity_type === 'LOC')
    }
  } catch (error) {
    console.error('Error loading entities:', error)
  }
}

function openTagDialog(scene: any) {
  selectedScene.value = scene
  tagForm.value = {
    scene_type: scene.tags?.scene_type || null,
    tone: scene.tags?.tone || null,
    location_entity_id: scene.tags?.location_entity_id || null,
    participant_ids: scene.tags?.participant_ids || [],
    summary: scene.tags?.summary || '',
    notes: scene.tags?.notes || '',
  }
  showTagDialog.value = true
}

async function saveSceneTags() {
  if (!selectedScene.value) return

  saving.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/scenes/${selectedScene.value.id}/tags`),
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tagForm.value),
      }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Guardado',
        detail: 'Etiquetas guardadas correctamente',
        life: 3000,
      })
      showTagDialog.value = false
      await loadScenes()
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    console.error('Error saving tags:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudieron guardar las etiquetas',
      life: 3000,
    })
  } finally {
    saving.value = false
  }
}

function openCustomTagDialog(scene: any) {
  selectedScene.value = scene
  customTagForm.value = { name: '', color: '' }
  showCustomTagDialog.value = true
}

async function saveCustomTag() {
  if (!selectedScene.value || !customTagForm.value.name?.trim()) return

  saving.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/scenes/${selectedScene.value.id}/custom-tags`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tag_name: customTagForm.value.name.trim(),
          tag_color: customTagForm.value.color ? `#${customTagForm.value.color}` : null,
        }),
      }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Añadida',
        detail: `Etiqueta "${customTagForm.value.name}" añadida`,
        life: 3000,
      })
      showCustomTagDialog.value = false
      await loadScenes()
    } else {
      throw new Error(data.error)
    }
  } catch (error: any) {
    console.error('Error adding custom tag:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudo añadir la etiqueta',
      life: 3000,
    })
  } finally {
    saving.value = false
  }
}

async function removeCustomTag(sceneId: number, tagName: string) {
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/scenes/${sceneId}/custom-tags/${encodeURIComponent(tagName)}`),
      { method: 'DELETE' }
    )
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Eliminada',
        detail: `Etiqueta "${tagName}" eliminada`,
        life: 2000,
      })
      await loadScenes()
    }
  } catch (error) {
    console.error('Error removing tag:', error)
  }
}

function searchTags(event: any) {
  const query = event.query.toLowerCase()
  tagSuggestions.value = (stats.value.custom_tags_used || []).filter((tag: string) =>
    tag.toLowerCase().includes(query)
  )
}

function filterByCustomTag(tag: string) {
  // Simple implementation: filter scenes that have this custom tag
  toast.add({
    severity: 'info',
    summary: 'Filtro',
    detail: `Filtrando por etiqueta: ${tag}`,
    life: 2000,
  })
  // Could implement more advanced filtering here
}

// Helper functions
function getTypeLabel(type: string): string {
  const option = sceneTypeOptions.find(o => o.value === type)
  return option?.label || type
}

function getToneLabel(tone: string): string {
  const option = toneOptions.find(o => o.value === tone)
  return option?.label || tone
}

function getTypeTagSeverity(type: string): string {
  const severities: Record<string, string> = {
    action: 'danger',
    dialogue: 'info',
    exposition: 'secondary',
    introspection: 'warning',
    flashback: 'contrast',
    dream: 'success',
    transition: 'secondary',
    mixed: 'secondary',
  }
  return severities[type] || 'secondary'
}

function getToneTagSeverity(tone: string): string {
  const severities: Record<string, string> = {
    tense: 'danger',
    calm: 'success',
    happy: 'success',
    sad: 'info',
    romantic: 'warning',
    mysterious: 'contrast',
    ominous: 'danger',
    hopeful: 'success',
    nostalgic: 'info',
    neutral: 'secondary',
  }
  return severities[tone] || 'secondary'
}

// Lifecycle
onMounted(() => {
  loadScenes()
  loadEntities()
})

watch(() => props.projectId, () => {
  loadScenes()
  loadEntities()
})
</script>

<style scoped>
.scene-tagging-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-4);
  height: 100%;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4);
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
}

.header-controls {
  display: flex;
  gap: var(--ds-space-2);
}

.view-toggle {
  display: flex;
  gap: 2px;
  border: 1px solid var(--ds-surface-border, var(--surface-border));
  border-radius: var(--ds-radius-md, 6px);
  padding: 2px;
}

.filter-dropdown {
  width: 180px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8);
  text-align: center;
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: var(--ds-space-4);
  opacity: 0.5;
}

.empty-state small {
  margin-top: var(--ds-space-2);
  opacity: 0.7;
}

.stats-cards {
  display: flex;
  gap: var(--ds-space-3);
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 120px;
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
}

/* WCAG AA: usar colores -700 para 4.5:1 sobre fondos claros */
.text-success { color: var(--ds-text-success, #15803d); }
.text-warning { color: var(--ds-text-warning, #a16207); }
.text-danger { color: var(--ds-text-danger, #b91c1c); }

.scenes-accordion {
  margin-top: var(--ds-space-4);
}

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--ds-space-3);
}

.chapter-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.chapter-subtitle {
  color: var(--ds-color-text-secondary);
  font-weight: normal;
}

.scenes-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.scene-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  background: var(--ds-surface-secondary);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid transparent;
}

.scene-row.is-tagged {
  border-left-color: var(--p-green-500);
}

.scene-info {
  flex: 1;
  min-width: 0;
}

.scene-number {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-sm);
}

.scene-excerpt {
  margin-top: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}

.scene-meta {
  margin-top: var(--ds-space-1);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
}

.scene-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
  align-items: center;
}

.custom-tag {
  position: relative;
}

.custom-tag .remove-tag {
  margin-left: var(--ds-space-1);
  cursor: pointer;
  opacity: 0.7;
  font-size: 10px;
}

.custom-tag .remove-tag:hover {
  opacity: 1;
}

.scene-actions {
  display: flex;
  gap: var(--ds-space-1);
}

.custom-tags-card {
  margin-top: var(--ds-space-4);
}

.custom-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.clickable-tag {
  cursor: pointer;
}

.clickable-tag:hover {
  opacity: 0.8;
}

.tag-form,
.custom-tag-form {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.form-field label {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
}

.w-full {
  width: 100%;
}

@media (max-width: 768px) {
  .tab-header {
    flex-direction: column;
  }

  .header-controls {
    width: 100%;
  }

  .filter-dropdown {
    flex: 1;
  }

  .scene-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .scene-tags {
    margin-top: var(--ds-space-2);
  }

  .scene-actions {
    margin-top: var(--ds-space-2);
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
