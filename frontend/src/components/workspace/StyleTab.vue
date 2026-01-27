<script setup lang="ts">
/**
 * StyleTab - Pestana de Estilo Editorial
 *
 * Permite al corrector definir reglas editoriales personalizadas
 * en texto libre que se aplican durante el analisis.
 *
 * Incluye configuracion de detectores de correcciones.
 *
 * Las reglas son por proyecto y tienen persistencia.
 */

import { ref, computed, onMounted, watch } from 'vue'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import Card from 'primevue/card'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { useToast } from 'primevue/usetoast'
import { useWorkspaceStore } from '@/stores/workspace'
import { useFeatureProfile } from '@/composables/useFeatureProfile'
import CorrectionConfigPanel from './CorrectionConfigPanel.vue'
import RegisterAnalysisTab from './RegisterAnalysisTab.vue'
import FocalizationTab from './FocalizationTab.vue'
import SceneTaggingTab from './SceneTaggingTab.vue'
import StickySentencesTab from './StickySentencesTab.vue'
import EchoReportTab from './EchoReportTab.vue'
import SentenceVariationTab from './SentenceVariationTab.vue'
import PacingAnalysisTab from './PacingAnalysisTab.vue'
import EmotionalAnalysisTab from './EmotionalAnalysisTab.vue'
import AgeReadabilityTab from './AgeReadabilityTab.vue'
import VitalStatusTab from './VitalStatusTab.vue'
import CharacterLocationTab from './CharacterLocationTab.vue'
import ChapterProgressTab from './ChapterProgressTab.vue'

const props = defineProps<{
  projectId: number
  /** Estado del análisis del proyecto */
  analysisStatus?: string
}>()

const workspaceStore = useWorkspaceStore()

// Feature profile based on document type
const { isFeatureAvailable } = useFeatureProfile(computed(() => props.projectId))

// Active tab index
const activeTab = ref(0)

// Watch for external navigation requests (e.g., from alerts panel)
watch(() => workspaceStore.styleTabSubtab, (newSubtab) => {
  if (newSubtab !== null) {
    activeTab.value = newSubtab
    workspaceStore.clearStyleTabSubtab()
  }
}, { immediate: true })

const toast = useToast()

// Estado
const rulesText = ref('')
const rulesEnabled = ref(true)
const loading = ref(false)
const saving = ref(false)
const hasChanges = ref(false)
const lastSaved = ref<string | null>(null)

// Feature availability (based on document type)
const hasScenes = ref(false)

// Cargar reglas y features disponibles al montar
onMounted(() => {
  loadRules()
  loadFeatureAvailability()
})

async function loadFeatureAvailability() {
  try {
    // Check if project has scenes
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/scenes/stats`
    )
    const data = await response.json()
    if (data.success) {
      hasScenes.value = data.data.has_scenes || false
    }
  } catch (error) {
    console.error('Error loading feature availability:', error)
  }
}

// Detectar cambios
watch(rulesText, () => {
  hasChanges.value = true
})

watch(rulesEnabled, () => {
  hasChanges.value = true
})

// Recargar si cambia el proyecto
watch(() => props.projectId, () => {
  loadRules()
  loadFeatureAvailability()
})

async function loadRules() {
  loading.value = true
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/editorial-rules`
    )
    const data = await response.json()

    if (data.success) {
      rulesText.value = data.data.rules_text || ''
      rulesEnabled.value = data.data.enabled ?? true
      lastSaved.value = data.data.updated_at
      hasChanges.value = false
    }
  } catch (error) {
    console.error('Error loading editorial rules:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron cargar las reglas editoriales',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

async function saveRules() {
  saving.value = true
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/editorial-rules`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rules_text: rulesText.value,
          enabled: rulesEnabled.value
        })
      }
    )
    const data = await response.json()

    if (data.success) {
      hasChanges.value = false
      lastSaved.value = new Date().toISOString()
      toast.add({
        severity: 'success',
        summary: 'Guardado',
        detail: 'Reglas editoriales guardadas correctamente',
        life: 3000
      })
    } else {
      throw new Error(data.error)
    }
  } catch (error) {
    console.error('Error saving editorial rules:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron guardar las reglas editoriales',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Nunca'
  const date = new Date(dateStr)
  return date.toLocaleString('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Ejemplos de reglas para ayudar al usuario
const exampleRules = `# Reglas de estilo editorial

## Sustantivos únicos en singular
- "nuestros corazones" -> "nuestro corazón" (cada persona tiene uno)
- "sus mentes" -> "su mente"
- "nuestras vidas" -> "nuestra vida"

## Números
- Edades con cifras: "tenía veinte años" -> "tenía 20 años"
- Duraciones con letra: "durante 5 años" -> "durante cinco años"

## Preferencias léxicas
- "por contra" -> "por el contrario"
- "quizás" -> "quizá"
- "sistema inmunológico" -> "sistema inmunitario"
- "alimenticio" -> "alimentario"

## Ortografía (RAE 2010)
- Demostrativos sin tilde: "este", "ese", "aquel"
- "solo" sin tilde (adverbio)
- "aun así" (sin tilde cuando significa "incluso así")
- "periodo" sin tilde (forma preferida RAE)
- "cardiaco" sin tilde (ambas formas válidas)

## Puntuación
- Sin coma antes de interrogación: "Entonces, ¿qué hacemos?"
- Rayas largas en incisos: "—dijo ella—" (no guiones cortos)

## Partitivos con artículo
- "el resto de soldados" -> "el resto de los soldados"
- "la mayoría de personas" -> "la mayoría de las personas"

## Evitar exceso de
- Adverbios en -mente consecutivos
- Posesivos innecesarios ("su mano" vs "la mano")`

function insertExample() {
  if (rulesText.value) {
    rulesText.value = rulesText.value + '\n\n' + exampleRules
  } else {
    rulesText.value = exampleRules
  }
  hasChanges.value = true
}
</script>

<template>
  <div class="style-tab">
    <div class="style-header">
      <div class="header-info">
        <h2>
          <i class="pi pi-pencil"></i>
          Estilo y Correcciones
        </h2>
        <p class="subtitle">
          Configura las normas de estilo y los detectores de correcciones.
        </p>
      </div>
    </div>

    <TabView :activeIndex="activeTab" @update:activeIndex="activeTab = $event" class="style-tabview">
      <!-- Tab 1: Configuracion de Correcciones -->
      <TabPanel value="0">
        <template #header>
          <i class="pi pi-sliders-h"></i>
          <span>Detectores</span>
        </template>

        <div class="tab-content corrections-tab">
          <CorrectionConfigPanel :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 2: Registro Narrativo -->
      <TabPanel value="1">
        <template #header>
          <i class="pi pi-sliders-v"></i>
          <span>Registro narrativo</span>
        </template>

        <div class="tab-content">
          <RegisterAnalysisTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 3: Reglas Editoriales -->
      <TabPanel value="2">
        <template #header>
          <i class="pi pi-file-edit"></i>
          <span>Reglas editoriales</span>
        </template>

        <div class="tab-content">
          <div class="rules-header">
            <div class="toggle-container">
              <label>Reglas activas</label>
              <ToggleSwitch v-model="rulesEnabled" />
            </div>
            <Button
              label="Guardar"
              icon="pi pi-save"
              :loading="saving"
              :disabled="!hasChanges"
              @click="saveRules"
            />
          </div>

          <!-- Mensaje informativo sobre cuando se aplican las reglas -->
          <Message
            v-if="analysisStatus !== 'completed'"
            severity="info"
            :closable="false"
            class="rules-info-message"
          >
            <i class="pi pi-info-circle"></i>
            Las reglas que definas se aplicarán durante el próximo análisis del documento.
          </Message>

          <div class="style-content">
            <!-- Panel izquierdo: Editor de reglas -->
            <div class="rules-editor">
              <Card>
                <template #title>
                  <div class="card-title">
                    <span>Reglas del proyecto</span>
                    <Button
                      label="Insertar ejemplo"
                      icon="pi pi-plus"
                      text
                      size="small"
                      @click="insertExample"
                    />
                  </div>
                </template>
                <template #content>
                  <Textarea
                    v-model="rulesText"
                    :disabled="loading"
                    placeholder="Escribe aquí las reglas editoriales para este manuscrito...

Ejemplos:
- 'quizás' -> 'quizá'
- Edades con números, duraciones con letra
- Demostrativos sin tilde
- Sistema inmunitario (no inmunológico)"
                    :autoResize="false"
                    rows="20"
                    class="rules-textarea"
                  />
                  <div class="editor-footer">
                    <span class="last-saved" v-if="lastSaved">
                      <i class="pi pi-clock"></i>
                      Guardado: {{ formatDate(lastSaved) }}
                    </span>
                    <span class="unsaved-indicator" v-if="hasChanges">
                      <i class="pi pi-circle-fill"></i>
                      Sin guardar
                    </span>
                  </div>
                </template>
              </Card>
            </div>

            <!-- Panel derecho: Ayuda e informacion -->
            <div class="rules-help">
              <Card class="help-card">
                <template #title>
                  <i class="pi pi-info-circle"></i>
                  Cómo escribir reglas
                </template>
                <template #content>
                  <div class="help-content">
                    <p>
                      Escribe las reglas en texto libre. El sistema las interpretará
                      y las aplicará durante el análisis del manuscrito.
                    </p>

                    <h4>Formato recomendado</h4>
                    <ul>
                      <li>Usa <code>-></code> para sustituciones: <code>"quizás" -> "quizá"</code></li>
                      <li>Agrupa reglas por categoría con <code>##</code></li>
                      <li>Añade explicaciones para recordar el motivo</li>
                    </ul>

                    <h4>Tipos de reglas soportadas</h4>
                    <ul>
                      <li><strong>Sustituciones:</strong> palabra A -> palabra B</li>
                      <li><strong>Preferencias:</strong> preferir X sobre Y</li>
                      <li><strong>Patrones:</strong> edades con números</li>
                      <li><strong>Prohibiciones:</strong> evitar X</li>
                    </ul>

                    <Message severity="info" :closable="false" class="help-message">
                      <p>
                        Las reglas son <strong>por proyecto</strong>.
                        Cada manuscrito puede tener sus propias normas editoriales.
                      </p>
                    </Message>
                  </div>
                </template>
              </Card>

              <Card class="predefined-card">
                <template #title>
                  <i class="pi pi-list"></i>
                  Reglas predefinidas activas
                </template>
                <template #content>
                  <p class="predefined-intro">
                    El sistema incluye reglas básicas que siempre están activas:
                  </p>
                  <ul class="predefined-list">
                    <li>Órganos únicos en singular (corazón, cerebro, mente)</li>
                    <li>Demostrativos sin tilde (RAE 2010)</li>
                    <li>"Solo" sin tilde</li>
                    <li>Partitivos con artículo</li>
                    <li>Rayas en incisos (no guiones)</li>
                    <li>Dobles espacios</li>
                  </ul>
                  <p class="predefined-note">
                    Tus reglas personalizadas se suman a estas.
                  </p>
                </template>
              </Card>
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Tab 4: Focalización -->
      <TabPanel value="3">
        <template #header>
          <i class="pi pi-eye"></i>
          <span>Focalización</span>
        </template>

        <div class="tab-content">
          <FocalizationTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 5: Escenas (condicional - solo si hay escenas y feature disponible) -->
      <TabPanel v-if="hasScenes && isFeatureAvailable('scenes')" value="4">
        <template #header>
          <i class="pi pi-images"></i>
          <span>Escenas</span>
        </template>

        <div class="tab-content">
          <SceneTaggingTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 6: Sticky Sentences -->
      <TabPanel v-if="isFeatureAvailable('sticky_sentences')" value="5">
        <template #header>
          <i class="pi pi-align-left"></i>
          <span>Oraciones pesadas</span>
        </template>

        <div class="tab-content">
          <StickySentencesTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 7: Echo/Repetitions -->
      <TabPanel v-if="isFeatureAvailable('echo_repetitions')" value="6">
        <template #header>
          <i class="pi pi-replay"></i>
          <span>Repeticiones</span>
        </template>

        <div class="tab-content">
          <EchoReportTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 8: Sentence Variation -->
      <TabPanel v-if="isFeatureAvailable('sentence_variation')" value="7">
        <template #header>
          <i class="pi pi-chart-bar"></i>
          <span>Variación</span>
        </template>

        <div class="tab-content">
          <SentenceVariationTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 9: Pacing Analysis -->
      <TabPanel v-if="isFeatureAvailable('pacing')" value="8">
        <template #header>
          <i class="pi pi-forward"></i>
          <span>Ritmo</span>
        </template>

        <div class="tab-content">
          <PacingAnalysisTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 10: Emotional Analysis -->
      <TabPanel v-if="isFeatureAvailable('emotional_analysis')" value="9">
        <template #header>
          <i class="pi pi-heart"></i>
          <span>Emociones</span>
        </template>

        <div class="tab-content">
          <EmotionalAnalysisTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 11: Age Readability (only for children's books) -->
      <TabPanel v-if="isFeatureAvailable('age_readability')" value="10">
        <template #header>
          <i class="pi pi-users"></i>
          <span>Edad lectora</span>
        </template>

        <div class="tab-content">
          <AgeReadabilityTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 12: Vital Status (character deaths and resurrections) -->
      <TabPanel v-if="isFeatureAvailable('vital_status')" value="11">
        <template #header>
          <i class="pi pi-heart-fill"></i>
          <span>Estado vital</span>
        </template>

        <div class="tab-content">
          <VitalStatusTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 13: Character Location (tracking character movements) -->
      <TabPanel v-if="isFeatureAvailable('character_location')" value="12">
        <template #header>
          <i class="pi pi-map-marker"></i>
          <span>Ubicaciones</span>
        </template>

        <div class="tab-content">
          <CharacterLocationTab :project-id="projectId" />
        </div>
      </TabPanel>

      <!-- Tab 14: Chapter Progress Summary (narrative progress tracking) -->
      <TabPanel v-if="isFeatureAvailable('chapter_progress')" value="13">
        <template #header>
          <i class="pi pi-chart-line"></i>
          <span>Avance narrativo</span>
        </template>

        <div class="tab-content">
          <ChapterProgressTab :project-id="projectId" />
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

<style scoped>
.style-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--ds-space-4);
  gap: var(--ds-space-3);
  overflow: hidden;
}

.style-header {
  flex-shrink: 0;
}

.header-info h2 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0;
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-semibold);
}

.header-info .subtitle {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.style-tabview {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.style-tabview :deep(.p-tabview-panels) {
  flex: 1;
  overflow: auto;
  padding: 0;
}

.style-tabview :deep(.p-tabview-panel) {
  height: 100%;
}

/* Tab styles are now handled by global primevue-overrides.css */

.tab-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3) 0;
  height: 100%;
}

.rules-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
}

.rules-info-message {
  margin: 0;
}

.rules-info-message i {
  margin-right: var(--ds-space-2);
}

.toggle-container {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.toggle-container label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.corrections-tab {
  overflow: auto;
  padding-right: var(--ds-space-2);
}

.style-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--ds-space-4);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.rules-editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.rules-editor :deep(.p-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rules-editor :deep(.p-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rules-editor :deep(.p-card-content) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rules-textarea {
  width: 100%;
  flex: 1;
  font-family: var(--ds-font-family-mono);
  font-size: var(--ds-font-size-sm);
  line-height: 1.6;
  resize: none;
}

.rules-textarea::placeholder {
  color: var(--ds-color-text-tertiary);
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.last-saved {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.unsaved-indicator {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  color: var(--p-yellow-500);
}

.unsaved-indicator i {
  font-size: 8px;
}

.rules-help {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
  overflow: auto;
}

.help-card :deep(.p-card-title),
.predefined-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.help-content p {
  margin: 0 0 var(--ds-space-3);
  color: var(--ds-color-text-secondary);
}

.help-content h4 {
  margin: var(--ds-space-3) 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
}

.help-content ul {
  margin: 0;
  padding-left: var(--ds-space-4);
}

.help-content li {
  margin-bottom: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.help-content code {
  background: var(--ds-surface-hover);
  padding: 2px 6px;
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-xs);
}

.help-message {
  margin-top: var(--ds-space-3);
}

.help-message p {
  margin: 0;
}

.predefined-intro {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.predefined-list {
  margin: 0;
  padding-left: var(--ds-space-4);
}

.predefined-list li {
  margin-bottom: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.predefined-note {
  margin: var(--ds-space-3) 0 0;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  font-style: italic;
}

/* Responsive */
@media (max-width: 1024px) {
  .style-content {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .rules-help {
    flex-direction: row;
  }

  .rules-help > * {
    flex: 1;
  }
}

@media (max-width: 768px) {
  .rules-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--ds-space-2);
  }

  .rules-help {
    flex-direction: column;
  }

  .style-tabview :deep(.p-tabview-nav-link) {
    padding: 0.75rem;
    font-size: var(--ds-font-size-sm);
  }
}
</style>
