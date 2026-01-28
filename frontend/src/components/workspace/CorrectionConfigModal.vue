<template>
  <div class="correction-config-wrapper">
    <Dialog
      v-model:visible="visible"
      modal
      :header="'Configuración de corrección'"
      :style="{ width: '750px' }"
      :breakpoints="{ '960px': '90vw' }"
      :draggable="false"
      :closable="!hasUnsavedChanges"
      @hide="onHide"
    >
      <template #header>
        <div class="modal-header">
          <div class="header-left">
            <span class="header-title">{{ modalTitle }}</span>
            <Tag v-if="!loading && hasCustomizations" severity="warn" size="small" class="header-tag">
              <i class="pi pi-pencil"></i> Personalizado
            </Tag>
            <Tag v-else-if="!loading && !editingDefaults" severity="secondary" size="small" class="header-tag">
              <i class="pi pi-link"></i> Heredado
            </Tag>
            <i
              v-if="!loading && !editingDefaults"
              v-tooltip.bottom="{
                value: 'Los parámetros se heredan del tipo/subtipo. El icono 🔗 indica valor heredado, el botón ↩ permite restaurar valores personalizados.',
                showDelay: 200
              }"
              class="pi pi-info-circle inheritance-help-icon"
            />
          </div>
          <Button
            v-if="hasUnsavedChanges"
            v-tooltip="'Cerrar'"
            icon="pi pi-times"
            text
            rounded
            severity="secondary"
            @click="confirmClose"
          />
        </div>
      </template>

      <div class="correction-config-modal">
        <!-- Loading state -->
        <div v-if="loading" class="config-loading">
          <i class="pi pi-spin pi-spinner" style="font-size: 2rem"></i>
          <p>Cargando configuración...</p>
        </div>

        <template v-else>
          <!-- Defaults mode warning -->
          <Message v-if="editingDefaults" severity="info" :closable="false" class="defaults-warning">
            <i class="pi pi-info-circle"></i>
            Estos cambios se aplicarán a <strong>proyectos nuevos</strong> de este tipo.
            Los proyectos existentes no se verán afectados.
          </Message>

          <!-- Main Tabs: Parameters / Editorial Rules -->
          <Tabs :value="mainTabIndex" @update:value="mainTabIndex = String($event)">
            <TabList>
              <Tab value="0">Parámetros</Tab>
              <Tab value="1">Reglas Editoriales</Tab>
            </TabList>
            <TabPanels>
              <!-- Parameters Tab -->
              <TabPanel value="0">
                <Tabs :value="paramTabIndex" @update:value="paramTabIndex = String($event)" class="nested-tabs">
                  <TabList>
                    <Tab value="0">Diálogos</Tab>
                    <Tab value="1">Repeticiones</Tab>
                    <Tab value="2">Oraciones</Tab>
                    <Tab value="3">Estilo</Tab>
                    <Tab value="4">Estructura</Tab>
                    <Tab value="5">Legibilidad</Tab>
                  </TabList>
                  <TabPanels>
                    <!-- Dialog Tab -->
                    <TabPanel value="0">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Análisis de diálogos</label>
                        <small>Detectar y analizar marcadores de diálogo</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.dialog.enabled"
                          @change="markModified('dialog', 'enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('dialog', 'enabled')"
                          @reset="resetParam('dialog', 'enabled')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.dialog.enabled" class="param-row">
                      <div class="param-info">
                        <label>Marcadores de diálogo</label>
                        <small>Caracteres reconocidos como inicio/fin de diálogo</small>
                      </div>
                      <div class="param-control wide">
                        <InputText
                          v-model="dialogMarkersText"
                          placeholder="—, «, », comillas, etc."
                          @change="markModified('dialog', 'dialog_markers')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('dialog', 'dialog_markers')"
                          @reset="resetParam('dialog', 'dialog_markers')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.dialog.enabled" class="param-row">
                      <div class="param-info">
                        <label>Marcador preferido</label>
                        <small>Tipo de marcador estándar para este documento</small>
                      </div>
                      <div class="param-control wide">
                        <Select
                          v-model="localConfig.dialog.preferred_marker"
                          :options="preferredMarkerOptions"
                          optionLabel="label"
                          optionValue="value"
                          optionGroupLabel="label"
                          optionGroupChildren="items"
                          placeholder="Sin preferencia"
                          showClear
                          @change="markModified('dialog', 'preferred_marker')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('dialog', 'preferred_marker')"
                          @reset="resetParam('dialog', 'preferred_marker')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.dialog.enabled && localConfig.dialog.preferred_marker" class="param-row">
                      <div class="param-info">
                        <label>Alertar marcadores inconsistentes</label>
                        <small>Detectar cuando se use un marcador diferente al preferido</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.dialog.flag_inconsistent_markers"
                          @change="markModified('dialog', 'flag_inconsistent_markers')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('dialog', 'flag_inconsistent_markers')"
                          @reset="resetParam('dialog', 'flag_inconsistent_markers')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.dialog.enabled" class="param-row">
                      <div class="param-info">
                        <label>Analizar variación de verbos dicendi</label>
                        <small>Detectar repetición de "dijo", "exclamó", etc.</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.dialog.analyze_dialog_tags"
                          @change="markModified('dialog', 'analyze_dialog_tags')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('dialog', 'analyze_dialog_tags')"
                          @reset="resetParam('dialog', 'analyze_dialog_tags')"
                        />
                      </div>
                    </div>
                  </div>
                </TabPanel>

                    <!-- Repetition Tab -->
                    <TabPanel value="1">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Detección de repeticiones</label>
                        <small>Analizar palabras repetidas en el texto</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.repetition.enabled"
                          @change="markModified('repetition', 'enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('repetition', 'enabled')"
                          @reset="resetParam('repetition', 'enabled')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.repetition.enabled" class="param-row">
                      <div class="param-info">
                        <label>Tolerancia a repeticiones</label>
                        <small>Cuántas ocurrencias antes de alertar</small>
                      </div>
                      <div class="param-control">
                        <Select
                          v-model="localConfig.repetition.tolerance"
                          :options="toleranceOptions"
                          option-label="label"
                          option-value="value"
                          @change="markModified('repetition', 'tolerance')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('repetition', 'tolerance')"
                          @reset="resetParam('repetition', 'tolerance')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.repetition.enabled" class="param-row">
                      <div class="param-info">
                        <label>Ventana de proximidad</label>
                        <small>Distancia en caracteres para considerar repetición</small>
                      </div>
                      <div class="param-control">
                        <InputNumber
                          v-model="localConfig.repetition.proximity_window_chars"
                          :min="50"
                          :max="500"
                          :step="10"
                          suffix=" chars"
                          @input="markModified('repetition', 'proximity_window_chars')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('repetition', 'proximity_window_chars')"
                          @reset="resetParam('repetition', 'proximity_window_chars')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.repetition.enabled" class="param-row">
                      <div class="param-info">
                        <label>Alertar si FALTAN repeticiones</label>
                        <small>Para contenido infantil que requiere repetición deliberada</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.repetition.flag_lack_of_repetition"
                          @change="markModified('repetition', 'flag_lack_of_repetition')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('repetition', 'flag_lack_of_repetition')"
                          @reset="resetParam('repetition', 'flag_lack_of_repetition')"
                        />
                      </div>
                    </div>
                  </div>
                </TabPanel>

                <!-- Sentence Tab -->
                <TabPanel value="2">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Análisis de oraciones</label>
                        <small>Analizar longitud y complejidad de oraciones</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.sentence.enabled"
                          @change="markModified('sentence', 'enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('sentence', 'enabled')"
                          @reset="resetParam('sentence', 'enabled')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.sentence.enabled" class="param-row">
                      <div class="param-info">
                        <label>Longitud máxima (palabras)</label>
                        <small>Alerta si una oración supera este límite</small>
                      </div>
                      <div class="param-control">
                        <InputNumber
                          v-model="localConfig.sentence.max_length_words"
                          :min="5"
                          :max="100"
                          placeholder="Sin límite"
                          show-buttons
                          @input="markModified('sentence', 'max_length_words')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('sentence', 'max_length_words')"
                          @reset="resetParam('sentence', 'max_length_words')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.sentence.enabled" class="param-row">
                      <div class="param-info">
                        <label>Tolerancia a voz pasiva (%)</label>
                        <small>Porcentaje máximo de oraciones en voz pasiva</small>
                      </div>
                      <div class="param-control">
                        <InputNumber
                          v-model="localConfig.sentence.passive_voice_tolerance_pct"
                          :min="0"
                          :max="100"
                          suffix="%"
                          @input="markModified('sentence', 'passive_voice_tolerance_pct')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('sentence', 'passive_voice_tolerance_pct')"
                          @reset="resetParam('sentence', 'passive_voice_tolerance_pct')"
                        />
                      </div>
                    </div>
                  </div>
                </TabPanel>

                <!-- Style Tab -->
                <TabPanel value="3">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Análisis de estilo</label>
                        <small>Detectar patrones estilísticos problemáticos</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.style.enabled"
                          @change="markModified('style', 'enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('style', 'enabled')"
                          @reset="resetParam('style', 'enabled')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.style.enabled" class="param-row">
                      <div class="param-info">
                        <label>Variación de inicios de oración</label>
                        <small>Detectar oraciones que empiezan igual</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.style.analyze_sentence_starts"
                          @change="markModified('style', 'analyze_sentence_starts')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('style', 'analyze_sentence_starts')"
                          @reset="resetParam('style', 'analyze_sentence_starts')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.style.enabled" class="param-row">
                      <div class="param-info">
                        <label>Oraciones pegajosas</label>
                        <small>Detectar oraciones con demasiadas palabras comunes</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.style.analyze_sticky_sentences"
                          @change="markModified('style', 'analyze_sticky_sentences')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('style', 'analyze_sticky_sentences')"
                          @reset="resetParam('style', 'analyze_sticky_sentences')"
                        />
                      </div>
                    </div>
                  </div>
                </TabPanel>

                <!-- Structure Tab -->
                <TabPanel value="4">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Análisis de timeline</label>
                        <small>Detectar inconsistencias temporales</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.structure.timeline_enabled"
                          @change="markModified('structure', 'timeline_enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('structure', 'timeline_enabled')"
                          @reset="resetParam('structure', 'timeline_enabled')"
                        />
                      </div>
                    </div>

                    <div class="param-row">
                      <div class="param-info">
                        <label>Relaciones entre personajes</label>
                        <small>Rastrear y validar relaciones</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.structure.relationships_enabled"
                          @change="markModified('structure', 'relationships_enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('structure', 'relationships_enabled')"
                          @reset="resetParam('structure', 'relationships_enabled')"
                        />
                      </div>
                    </div>

                    <div class="param-row">
                      <div class="param-info">
                        <label>Consistencia de comportamiento</label>
                        <small>Detectar cambios bruscos en personajes</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.structure.behavior_consistency_enabled"
                          @change="markModified('structure', 'behavior_consistency_enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('structure', 'behavior_consistency_enabled')"
                          @reset="resetParam('structure', 'behavior_consistency_enabled')"
                        />
                      </div>
                    </div>

                    <div class="param-row">
                      <div class="param-info">
                        <label>Seguimiento de ubicaciones</label>
                        <small>Rastrear dónde están los personajes</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.structure.location_tracking_enabled"
                          @change="markModified('structure', 'location_tracking_enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('structure', 'location_tracking_enabled')"
                          @reset="resetParam('structure', 'location_tracking_enabled')"
                        />
                      </div>
                    </div>
                  </div>
                </TabPanel>

                <!-- Readability Tab -->
                <TabPanel value="5">
                  <div class="config-section">
                    <div class="param-row">
                      <div class="param-info">
                        <label>Análisis de legibilidad</label>
                        <small>Evaluar adecuación para edad objetivo</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.readability.enabled"
                          @change="markModified('readability', 'enabled')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('readability', 'enabled')"
                          @reset="resetParam('readability', 'enabled')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.readability.enabled" class="param-row">
                      <div class="param-info">
                        <label>Edad objetivo (mínima)</label>
                        <small>Edad mínima del lector objetivo</small>
                      </div>
                      <div class="param-control">
                        <InputNumber
                          v-model="localConfig.readability.target_age_min"
                          :min="0"
                          :max="18"
                          suffix=" años"
                          @input="markModified('readability', 'target_age_min')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('readability', 'target_age_min')"
                          @reset="resetParam('readability', 'target_age_min')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.readability.enabled" class="param-row">
                      <div class="param-info">
                        <label>Edad objetivo (máxima)</label>
                        <small>Edad máxima del lector objetivo</small>
                      </div>
                      <div class="param-control">
                        <InputNumber
                          v-model="localConfig.readability.target_age_max"
                          :min="0"
                          :max="99"
                          suffix=" años"
                          @input="markModified('readability', 'target_age_max')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('readability', 'target_age_max')"
                          @reset="resetParam('readability', 'target_age_max')"
                        />
                      </div>
                    </div>

                    <div v-if="localConfig.readability.enabled" class="param-row">
                      <div class="param-info">
                        <label>Analizar vocabulario por edad</label>
                        <small>Verificar que las palabras sean apropiadas</small>
                      </div>
                      <div class="param-control">
                        <ToggleSwitch
                          v-model="localConfig.readability.analyze_vocabulary_age"
                          @change="markModified('readability', 'analyze_vocabulary_age')"
                        />
                        <InheritanceIndicator
                          :is-custom="isCustom('readability', 'analyze_vocabulary_age')"
                          @reset="resetParam('readability', 'analyze_vocabulary_age')"
                        />
                      </div>
                    </div>
                  </div>
                    </TabPanel>
                  </TabPanels>
                </Tabs>
              </TabPanel>

              <!-- Editorial Rules Tab -->
              <TabPanel value="1">
              <div class="rules-section">
                <div class="rules-description">
                  <i class="pi pi-info-circle"></i>
                  <span>
                    Las reglas se aplican durante el análisis para detectar inconsistencias.
                    Pueden heredarse del tipo/subtipo y personalizarse a nivel de documento.
                  </span>
                </div>

                <!-- Rules list -->
                <div class="rules-list">
                  <div
                    v-for="(rule, index) in localRules"
                    :key="rule.id"
                    class="rule-item"
                    :class="{ disabled: !rule.enabled, inherited: rule.source !== 'custom' }"
                  >
                    <div class="rule-toggle">
                      <ToggleSwitch
                        v-model="rule.enabled"
                        @change="markRuleModified(rule)"
                      />
                    </div>
                    <div class="rule-content">
                      <Textarea
                        v-model="rule.text"
                        :disabled="!rule.enabled"
                        auto-resize
                        rows="2"
                        placeholder="Escriba la regla editorial..."
                        @input="markRuleModified(rule)"
                      />
                    </div>
                    <div class="rule-meta">
                      <Tag
                        v-if="rule.source === 'type'"
                        severity="info"
                        size="small"
                      >
                        <i class="pi pi-folder"></i> Tipo
                      </Tag>
                      <Tag
                        v-else-if="rule.source === 'subtype'"
                        severity="success"
                        size="small"
                      >
                        <i class="pi pi-file"></i> Subtipo
                      </Tag>
                      <Tag
                        v-else
                        severity="warn"
                        size="small"
                      >
                        <i class="pi pi-pencil"></i> Propia
                      </Tag>
                      <Button
                        v-if="rule.source === 'custom'"
                        v-tooltip="'Eliminar regla'"
                        icon="pi pi-trash"
                        text
                        rounded
                        severity="danger"
                        size="small"
                        @click="removeRule(index)"
                      />
                      <Button
                        v-else-if="rule.overridden"
                        v-tooltip="'Restaurar original'"
                        icon="pi pi-refresh"
                        text
                        rounded
                        severity="secondary"
                        size="small"
                        @click="resetRule(rule)"
                      />
                    </div>
                  </div>

                  <!-- Empty state -->
                  <div v-if="localRules.length === 0" class="rules-empty">
                    <i class="pi pi-list"></i>
                    <span>No hay reglas definidas</span>
                  </div>
                </div>

                <!-- Add rule button -->
                <div class="rules-actions">
                  <Button
                    label="Añadir regla"
                    icon="pi pi-plus"
                    text
                    @click="addRule"
                  />
                </div>
              </div>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </template>
      </div>

      <template #footer>
        <div class="modal-footer">
          <Button
            v-if="hasCustomizations"
            label="Restaurar todo"
            icon="pi pi-refresh"
            text
            severity="secondary"
            @click="resetAll"
          />
          <div class="footer-actions">
            <Button
              label="Cancelar"
              text
              @click="confirmClose"
            />
            <Button
              label="Guardar"
              icon="pi pi-check"
              :loading="saving"
              :disabled="!hasUnsavedChanges"
              @click="saveConfig"
            />
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Unsaved changes confirmation dialog -->
    <Dialog
      v-model:visible="showUnsavedDialog"
      modal
      header="Cambios sin guardar"
      :style="{ width: '400px' }"
    >
      <div class="unsaved-dialog-content">
        <i class="pi pi-exclamation-triangle"></i>
        <p>Hay cambios que no se han guardado. ¿Qué desea hacer?</p>
      </div>
      <template #footer>
        <Button
          label="Descartar"
          severity="secondary"
          text
          @click="discardAndClose"
        />
        <Button
          label="Guardar"
          icon="pi pi-check"
          :loading="saving"
          @click="saveAndClose"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import Dialog from 'primevue/dialog'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import InheritanceIndicator from './InheritanceIndicator.vue'
import { apiUrl } from '../../config/api'

interface EditorialRule {
  id: string
  text: string
  enabled: boolean
  source: 'type' | 'subtype' | 'custom'
  source_name: string | null
  overridden: boolean
}

interface CorrectionConfig {
  type_code: string
  type_name: string
  subtype_code: string | null
  subtype_name: string | null
  dialog: {
    enabled: boolean
    dialog_markers: string[]
    preferred_marker: string | null
    flag_inconsistent_markers: boolean
    analyze_dialog_tags: boolean
    dialog_tag_variation_min: number
    flag_consecutive_same_tag: boolean
  }
  repetition: {
    enabled: boolean
    tolerance: string
    proximity_window_chars: number
    min_word_length: number
    ignore_words: string[]
    flag_lack_of_repetition: boolean
  }
  sentence: {
    enabled: boolean
    max_length_words: number | null
    recommended_length_words: number | null
    analyze_complexity: boolean
    passive_voice_tolerance_pct: number
    adverb_ly_tolerance_pct: number
  }
  style: {
    enabled: boolean
    analyze_sentence_starts: boolean
    analyze_sticky_sentences: boolean
    sticky_threshold_pct: number
    analyze_register: boolean
    analyze_emotions: boolean
  }
  structure: {
    timeline_enabled: boolean
    relationships_enabled: boolean
    behavior_consistency_enabled: boolean
    scenes_enabled: boolean
    location_tracking_enabled: boolean
    vital_status_enabled: boolean
  }
  readability: {
    enabled: boolean
    target_age_min: number | null
    target_age_max: number | null
    analyze_vocabulary_age: boolean
    max_vocabulary_size: number | null
  }
  editorial_rules: {
    rules: EditorialRule[]
  }
  inheritance: Record<string, { source: string; source_name: string | null }>
}

const props = defineProps<{
  projectId: number
  // Props para modo edición de defaults
  editingDefaults?: boolean
  defaultsTypeCode?: string | null
  defaultsSubtypeCode?: string | null
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const toast = useToast()
const visible = ref(false)
const loading = ref(false)
const saving = ref(false)
const config = ref<CorrectionConfig | null>(null)
const defaultLocalConfig: CorrectionConfig = {
  type_code: '',
  type_name: '',
  subtype_code: null,
  subtype_name: null,
  dialog: { enabled: false, dialog_markers: [], preferred_marker: null, flag_inconsistent_markers: false, analyze_dialog_tags: false, dialog_tag_variation_min: 3, flag_consecutive_same_tag: false },
  repetition: { enabled: false, tolerance: 'medium', proximity_window_chars: 200, min_word_length: 4, ignore_words: [], flag_lack_of_repetition: false },
  sentence: { enabled: false, max_length_words: null, recommended_length_words: null, analyze_complexity: false, passive_voice_tolerance_pct: 20, adverb_ly_tolerance_pct: 10 },
  style: { enabled: false, analyze_sentence_starts: false, analyze_sticky_sentences: false, sticky_threshold_pct: 40, analyze_register: false, analyze_emotions: false },
  structure: { timeline_enabled: false, relationships_enabled: false, behavior_consistency_enabled: false, scenes_enabled: false, location_tracking_enabled: false, vital_status_enabled: false },
  readability: { enabled: false, target_age_min: null, target_age_max: null, analyze_vocabulary_age: false, max_vocabulary_size: null },
  editorial_rules: { rules: [] },
  inheritance: {},
}
const localConfig = ref<CorrectionConfig>(JSON.parse(JSON.stringify(defaultLocalConfig)))
const localRules = ref<EditorialRule[]>([])
const originalRules = ref<EditorialRule[]>([])
const modifiedParams = ref<Set<string>>(new Set())
const modifiedRules = ref<Set<string>>(new Set())
const showUnsavedDialog = ref(false)
const mainTabIndex = ref('0')
const paramTabIndex = ref('0')

const toleranceOptions = [
  { value: 'very_high', label: 'Muy alta (5+ ocurrencias)' },
  { value: 'high', label: 'Alta (4+ ocurrencias)' },
  { value: 'medium', label: 'Media (3+ ocurrencias)' },
  { value: 'low', label: 'Baja (2+ ocurrencias)' },
]

// Opciones de marcadores de diálogo agrupadas por tipo
const preferredMarkerOptions = [
  {
    label: 'Guiones y rayas',
    items: [
      { value: 'raya', label: 'Raya española (—)' },
      { value: 'guion_largo', label: 'Guión largo (–)' },
      { value: 'guion', label: 'Guión simple (-)' }
    ]
  },
  {
    label: 'Comillas',
    items: [
      { value: 'comillas_angulares', label: 'Comillas angulares/latinas («»)' },
      { value: 'comillas_inglesas', label: 'Comillas inglesas ("")' },
      { value: 'comillas_simples', label: "Comillas simples ('')" }
    ]
  }
]

// Dialog markers as editable text
const dialogMarkersText = computed({
  get: () => localConfig.value.dialog?.dialog_markers?.join(', ') || '',
  set: (val: string) => {
    localConfig.value.dialog.dialog_markers = val.split(',').map(s => s.trim()).filter(Boolean)
  }
})

const hasCustomizations = computed(() => modifiedParams.value.size > 0 || modifiedRules.value.size > 0)
const hasUnsavedChanges = computed(() => hasCustomizations.value)

const modalTitle = computed(() => {
  if (props.editingDefaults) {
    const typeName = config.value?.type_name || props.defaultsTypeCode
    const subtypeName = config.value?.subtype_name
    if (subtypeName) {
      return `Editar defaults: ${typeName} / ${subtypeName}`
    }
    return `Editar defaults: ${typeName}`
  }
  return 'Configuración de corrección'
})

const isCustom = (category: string, param: string): boolean => {
  return modifiedParams.value.has(`${category}.${param}`)
}

const markModified = (category: string, param: string) => {
  modifiedParams.value.add(`${category}.${param}`)
}

const markRuleModified = (rule: EditorialRule) => {
  modifiedRules.value.add(rule.id)
  if (rule.source !== 'custom') {
    rule.overridden = true
  }
}

const resetParam = (category: string, param: string) => {
  const key = `${category}.${param}`
  modifiedParams.value.delete(key)

  // Restore original value from config
  if (config.value) {
    const cat = category as keyof CorrectionConfig
    const p = param as string
    if (localConfig.value[cat] && config.value[cat]) {
      (localConfig.value[cat] as Record<string, unknown>)[p] =
        (config.value[cat] as Record<string, unknown>)[p]
    }
  }
}

const resetRule = (rule: EditorialRule) => {
  // Find original rule
  const original = originalRules.value.find(r => r.id === rule.id)
  if (original) {
    rule.text = original.text
    rule.enabled = original.enabled
    rule.overridden = false
    modifiedRules.value.delete(rule.id)
  }
}

const addRule = () => {
  const newRule: EditorialRule = {
    id: `custom_${Date.now()}`,
    text: '',
    enabled: true,
    source: 'custom',
    source_name: null,
    overridden: false,
  }
  localRules.value.push(newRule)
  modifiedRules.value.add(newRule.id)
}

const removeRule = (index: number) => {
  const rule = localRules.value[index]
  if (rule) {
    modifiedRules.value.delete(rule.id)
    localRules.value.splice(index, 1)
    // Mark as modified if we removed a custom rule
    modifiedRules.value.add('_removed_' + rule.id)
  }
}

const resetAll = () => {
  if (config.value) {
    localConfig.value = JSON.parse(JSON.stringify(config.value))
    localRules.value = JSON.parse(JSON.stringify(originalRules.value))
    modifiedParams.value.clear()
    modifiedRules.value.clear()
  }
}

const loadConfig = async () => {
  loading.value = true

  try {
    let url: string
    if (props.editingDefaults && props.defaultsTypeCode) {
      // Modo edición de defaults
      url = `/api/correction-config/defaults/${props.defaultsTypeCode}`
      if (props.defaultsSubtypeCode) {
        url += `?subtype_code=${props.defaultsSubtypeCode}`
      }
    } else {
      // Modo edición de proyecto
      url = `/api/projects/${props.projectId}/correction-config`
    }

    const response = await fetch(apiUrl(url))
    const data = await response.json()

    if (data.success) {
      // En modo defaults, usar effective_config
      const configData = props.editingDefaults ? data.data.effective_config : data.data

      // Asegurar que los nombres están disponibles (desde el root o effective_config)
      if (props.editingDefaults) {
        configData.type_name = configData.type_name || data.data.type_name
        configData.subtype_name = configData.subtype_name || data.data.subtype_name
      }

      config.value = configData
      localConfig.value = JSON.parse(JSON.stringify(configData))

      // Load rules
      const rules = configData.editorial_rules?.rules || []
      localRules.value = JSON.parse(JSON.stringify(rules))
      originalRules.value = JSON.parse(JSON.stringify(rules))

      // Check which params are already customized
      modifiedParams.value.clear()
      modifiedRules.value.clear()

      if (props.editingDefaults && data.data.override) {
        // En modo defaults, marcar los params del override existente
        const existingOverrides = data.data.override.overrides || {}
        for (const [category, params] of Object.entries(existingOverrides)) {
          if (typeof params === 'object' && params !== null) {
            for (const param of Object.keys(params as Record<string, unknown>)) {
              modifiedParams.value.add(`${category}.${param}`)
            }
          }
        }
      } else if (configData.inheritance) {
        for (const [key, info] of Object.entries(configData.inheritance)) {
          if ((info as { source: string }).source === 'custom') {
            modifiedParams.value.add(key)
          }
        }
      }
    }
  } catch (err) {
    console.error('Error loading correction config:', err)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo cargar la configuración',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    // Build customizations object with only modified params
    const customizations: Record<string, Record<string, unknown>> = {}

    for (const key of modifiedParams.value) {
      const [category, param] = key.split('.')
      if (!customizations[category]) {
        customizations[category] = {}
      }
      const cat = category as keyof CorrectionConfig
      customizations[category][param] = (localConfig.value[cat] as Record<string, unknown>)[param]
    }

    // Add rules if modified
    if (modifiedRules.value.size > 0) {
      customizations['editorial_rules'] = {
        rules: localRules.value.filter(r => r.text.trim() !== '')
      }
    }

    let url: string
    let body: unknown

    if (props.editingDefaults && props.defaultsTypeCode) {
      // Modo edición de defaults
      url = `/api/correction-config/defaults/${props.defaultsTypeCode}`
      if (props.defaultsSubtypeCode) {
        url += `?subtype_code=${props.defaultsSubtypeCode}`
      }
      body = { overrides: customizations }
    } else {
      // Modo edición de proyecto
      url = `/api/projects/${props.projectId}/correction-config`
      body = { customizations }
    }

    const response = await fetch(apiUrl(url), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    const data = await response.json()
    if (data.success) {
      const detail = props.editingDefaults
        ? 'Defaults actualizados correctamente'
        : 'Configuración de corrección actualizada'
      toast.add({
        severity: 'success',
        summary: 'Guardado',
        detail,
        life: 2000
      })
      emit('saved')
      modifiedParams.value.clear()
      modifiedRules.value.clear()
      visible.value = false
      return true
    } else {
      throw new Error(data.error || 'Error guardando')
    }
  } catch (err) {
    console.error('Error saving correction config:', err)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo guardar la configuración',
      life: 3000
    })
    return false
  } finally {
    saving.value = false
  }
}

const confirmClose = () => {
  if (hasUnsavedChanges.value) {
    showUnsavedDialog.value = true
  } else {
    visible.value = false
  }
}

const discardAndClose = () => {
  showUnsavedDialog.value = false
  modifiedParams.value.clear()
  modifiedRules.value.clear()
  visible.value = false
}

const saveAndClose = async () => {
  const saved = await saveConfig()
  if (saved) {
    showUnsavedDialog.value = false
  }
}

const show = async () => {
  visible.value = true
  mainTabIndex.value = '0'
  paramTabIndex.value = '0'
  // Wait for Vue to update props before loading config
  // Use double nextTick to ensure reactivity is fully processed
  await nextTick()
  await nextTick()
  loadConfig()
}

const onHide = () => {
  // Only clear if no unsaved changes (already handled by confirmClose)
  if (!hasUnsavedChanges.value) {
    modifiedParams.value.clear()
    modifiedRules.value.clear()
  }
}

// Expose show method
defineExpose({ show })

// Watch for props changes when modal is visible
watch(
  () => [props.projectId, props.defaultsTypeCode, props.defaultsSubtypeCode],
  () => {
    if (visible.value) {
      loadConfig()
    }
  }
)
</script>

<style scoped>
.correction-config-modal {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 0.5rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex: 1;
  min-width: 0;
}

.header-title {
  font-weight: 600;
}

.header-tag :deep(.p-tag) {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
}

.inheritance-help-icon {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  cursor: help;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.inheritance-help-icon:hover {
  opacity: 1;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
}

.param-info {
  flex: 1;
  min-width: 0;
}

.param-info label {
  display: block;
  font-weight: 500;
  font-size: 0.875rem;
  margin-bottom: 0.125rem;
}

.param-info small {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.param-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.param-control.wide {
  flex: 1;
  max-width: 300px;
}

.param-control.wide :deep(.p-inputtext) {
  width: 100%;
}

/* Rules section */
.rules-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rules-description {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.rules-description i {
  color: var(--primary-color);
  margin-top: 0.125rem;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 350px;
  overflow-y: auto;
}

.rule-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--orange-500);
}

.rule-item.inherited {
  border-left-color: var(--blue-500);
}

.rule-item.inherited.subtype {
  border-left-color: var(--green-500);
}

.rule-item.disabled {
  opacity: 0.6;
}

.rule-toggle {
  padding-top: 0.5rem;
}

.rule-content {
  flex: 1;
  min-width: 0;
}

.rule-content :deep(.p-textarea) {
  width: 100%;
  font-size: 0.875rem;
}

.rule-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.rule-meta :deep(.p-tag) {
  font-size: 0.6875rem;
}

.rules-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.rules-empty i {
  font-size: 2rem;
  opacity: 0.5;
}

.rules-actions {
  display: flex;
  justify-content: flex-start;
}

/* Modal footer */
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.footer-actions {
  display: flex;
  gap: 0.5rem;
}

/* Unsaved dialog */
.unsaved-dialog-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.unsaved-dialog-content i {
  font-size: 2rem;
  color: var(--orange-500);
}

.unsaved-dialog-content p {
  margin: 0;
  padding-top: 0.5rem;
}

/* Nested tabs */
.nested-tabs :deep(.p-tabview-nav) {
  background: transparent;
}

.nested-tabs :deep(.p-tabview-panels) {
  padding: 1rem 0;
}

/* Tab panel content */
:deep(.p-tabview-panels) {
  padding: 1rem 0;
}

/* Dark mode */
:deep(.dark) .param-row,
:deep(.dark) .rules-description,
:deep(.dark) .rule-item {
  background: var(--surface-card);
}
</style>
