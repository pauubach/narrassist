<template>
  <div class="settings-view">
    <div class="settings-header">
      <Button
        icon="pi pi-arrow-left"
        text
        label="Volver"
        @click="goBack"
      />
      <h1>Configuración</h1>
    </div>

    <div class="settings-layout">
      <!-- Sidebar Navigation -->
      <nav class="settings-sidebar">
        <ul class="nav-menu">
          <li>
            <a href="#apariencia" :class="{ active: activeSection === 'apariencia' }" @click.prevent="scrollToSection('apariencia')">
              <i class="pi pi-palette"></i>
              <span>Apariencia</span>
            </a>
          </li>
          <li>
            <a href="#analisis" :class="{ active: activeSection === 'analisis' }" @click.prevent="scrollToSection('analisis')">
              <i class="pi pi-cog"></i>
              <span>Análisis</span>
            </a>
          </li>
          <li>
            <a href="#analizador-ia" :class="{ active: activeSection === 'analizador-ia' }" @click.prevent="scrollToSection('analizador-ia')">
              <i class="pi pi-microchip-ai"></i>
              <span>Analizador Semántico</span>
            </a>
          </li>
          <li>
            <a href="#metodos-nlp" :class="{ active: activeSection === 'metodos-nlp' }" @click.prevent="scrollToSection('metodos-nlp')">
              <i class="pi pi-sliders-h"></i>
              <span>Métodos de Detección</span>
            </a>
          </li>
          <li>
            <a href="#correcciones" :class="{ active: activeSection === 'correcciones' }" @click.prevent="scrollToSection('correcciones')">
              <i class="pi pi-pencil"></i>
              <span>Correcciones</span>
            </a>
          </li>
          <li>
            <a href="#datos-mantenimiento" :class="{ active: activeSection === 'datos-mantenimiento' }" @click.prevent="scrollToSection('datos-mantenimiento')">
              <i class="pi pi-database"></i>
              <span>Datos y Mantenimiento</span>
            </a>
          </li>
          <li>
            <a href="#licencia" :class="{ active: activeSection === 'licencia' }" @click.prevent="scrollToSection('licencia')">
              <i class="pi pi-key"></i>
              <span>Licencia</span>
            </a>
          </li>
        </ul>
      </nav>

      <!-- Content Area -->
      <div ref="contentArea" class="settings-content" @scroll="handleScroll">
        <!-- Apariencia -->
        <Card id="apariencia">
          <template #title>
            <div class="section-title">
              <i class="pi pi-palette"></i>
              <span>Apariencia</span>
            </div>
          </template>
          <template #content>
            <AppearanceSection />
          </template>
        </Card>

        <!-- Análisis -->
        <Card id="analisis">
          <template #title>
            <div class="section-title">
              <i class="pi pi-cog"></i>
              <span>Análisis</span>
            </div>
          </template>
          <template #content>
            <AnalysisSection />
          </template>
        </Card>

        <!-- Analizador Semántico (IA) -->
        <Card id="analizador-ia">
          <template #title>
            <div class="section-title">
              <i class="pi pi-microchip-ai"></i>
              <span>Analizador Semántico</span>
              <Tag v-if="loadingCapabilities" value="Cargando..." severity="info" />
            </div>
          </template>
          <template #content>
            <SemanticAnalyzerSection
              :quality-levels="qualityLevels"
              :quality-level-downloading="qualityLevelDownloading"
              :loading-capabilities="loadingCapabilities"
              @select-quality-level="selectQualityLevel"
              @llm-sensitivity-change="onLlmSensitivityChange"
            />
          </template>
        </Card>

        <!-- Métodos de Detección -->
        <Card id="metodos-nlp">
          <template #title>
            <div class="section-title">
              <i class="pi pi-sliders-h"></i>
              <span>Métodos de Detección</span>
            </div>
          </template>
          <template #content>
            <DetectionMethodsSection
              :lt-action-config="ltActionConfig"
              :lt-status-message="ltStatusMessage"
              :lt-installing="ltInstalling"
              :lt-starting="ltStarting"
              :lt-install-progress="ltInstallProgress"
              :lt-state="ltState"
            />
          </template>
        </Card>

        <!-- Correcciones -->
        <Card id="correcciones">
          <template #title>
            <div class="section-title">
              <i class="pi pi-pencil"></i>
              <span>Correcciones Editoriales</span>
            </div>
          </template>
          <template #content>
            <CorrectionsSection ref="correctionsSection" />
          </template>
        </Card>

        <!-- Datos y Mantenimiento -->
        <Card id="datos-mantenimiento">
          <template #title>
            <div class="section-title">
              <i class="pi pi-database"></i>
              <span>Datos y Mantenimiento</span>
            </div>
          </template>
          <template #content>
            <DataMaintenanceSection
              ref="dataMaintenanceSection"
              :data-location="dataLocation"
              @change-data-location="changeDataLocation"
              @confirm-reset="confirmReset"
            />
          </template>
        </Card>

        <!-- Licencia -->
        <Card id="licencia">
          <template #title>
            <div class="section-title">
              <i class="pi pi-key"></i>
              <span>Licencia</span>
            </div>
          </template>
          <template #content>
            <LicenseSection @show-license-dialog="showLicenseDialog = true" />
          </template>
        </Card>
      </div>
    </div>

    <!-- Confirm Reset Dialog -->
    <Dialog
      :visible="showResetDialog"
      modal
      header="Confirmar restablecimiento"
      :style="{ width: '450px' }"
      @update:visible="showResetDialog = $event"
    >
      <p>
        ¿Estás seguro de que deseas restablecer toda la configuración a los valores por defecto?
        Esta acción no se puede deshacer.
      </p>
      <template #footer>
        <Button label="Cancelar" severity="secondary" @click="showResetDialog = false" />
        <Button label="Restablecer" severity="danger" @click="resetSettings" />
      </template>
    </Dialog>

    <!-- Change Data Location Dialog -->
    <Dialog
      :visible="showDataLocationDialog"
      modal
      header="Cambiar ubicación de datos"
      :style="{ width: '550px' }"
      @update:visible="showDataLocationDialog = $event"
    >
      <div class="data-location-dialog">
        <p class="dialog-description">
          Selecciona una nueva carpeta donde se guardarán los proyectos y datos de la aplicación.
        </p>

        <div class="location-input">
          <label class="input-label">Nueva ubicación</label>
          <InputText
            v-model="newDataLocation"
            placeholder="Ej: C:\Users\Usuario\Documents\NarrativeAssistant"
            class="location-field"
          />
        </div>

        <div class="migrate-option">
          <ToggleSwitch
            v-model="migrateData"
            inputId="settings-migrate-data"
            aria-label="Migrar datos existentes"
          />
          <div class="migrate-info">
            <label>Migrar datos existentes</label>
            <span class="migrate-description">
              Copia los proyectos y configuración actual a la nueva ubicación
            </span>
          </div>
        </div>

        <Message severity="info" :closable="false" class="location-info-message">
          <span>Necesitarás reiniciar la aplicación después de cambiar la ubicación.</span>
        </Message>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          :disabled="changingLocation"
          @click="showDataLocationDialog = false"
        />
        <Button
          label="Cambiar ubicación"
          icon="pi pi-check"
          :loading="changingLocation"
          @click="confirmChangeDataLocation"
        />
      </template>
    </Dialog>

    <LicenseDialog :visible="showLicenseDialog" @update:visible="showLicenseDialog = $event" @activated="onLicenseActivated" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, provide, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/apiClient'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { useSystemStore, type LTState } from '@/stores/system'
import { useLicenseStore } from '@/stores/license'
import { useProjectsStore } from '@/stores/projects'
import LicenseDialog from '@/components/LicenseDialog.vue'

// Section components
import AppearanceSection from '@/components/settings/AppearanceSection.vue'
import AnalysisSection from '@/components/settings/AnalysisSection.vue'
import SemanticAnalyzerSection from '@/components/settings/SemanticAnalyzerSection.vue'
import DetectionMethodsSection from '@/components/settings/DetectionMethodsSection.vue'
import CorrectionsSection from '@/components/settings/CorrectionsSection.vue'
import DataMaintenanceSection from '@/components/settings/DataMaintenanceSection.vue'
import LicenseSection from '@/components/settings/LicenseSection.vue'

// Composables
import { useSettingsPersistence } from '@/composables/useSettingsPersistence'
import { useSensitivityPresets } from '@/composables/useSensitivityPresets'
import { useOllamaManagement } from '@/composables/useOllamaManagement'
import { useNLPMethods } from '@/composables/useNLPMethods'
import { safeGetItem } from '@/utils/safeStorage'

// Injection keys
import { settingsKey, sensitivityKey, ollamaKey, nlpMethodsKey } from '@/components/settings/settingsInjection'

const router = useRouter()
const toast = useToast()
const systemStore = useSystemStore()
const licenseStore = useLicenseStore()
const projectsStore = useProjectsStore()
const showLicenseDialog = ref(false)

function onLicenseActivated() {
  toast.add({ severity: 'success', summary: 'Licencia activada', detail: `Plan ${licenseStore.tierDisplayName} activado`, life: 3000 })
}

// ── Composable wiring ──────────────────────────────────────

const {
  settings, loadSettings, saveSettings, onSettingChange, onSliderChange,
  applyDefaultsFromCapabilities, resetSettings: doResetSettings,
  loadAnalysisSettingsFromBackend, syncAnalysisSettingsToBackend, cleanup: cleanupPersistence,
} = useSettingsPersistence()

const sensitivityContext = useSensitivityPresets(settings, saveSettings, onSliderChange)

const ollamaContext = useOllamaManagement()

const nlpMethodsContext = useNLPMethods(settings, saveSettings, applyDefaultsFromCapabilities)

// ── Provide composable state to child sections ──────────────

provide(settingsKey, { settings, onSettingChange, saveSettings })
provide(sensitivityKey, sensitivityContext)
provide(ollamaKey, ollamaContext)
provide(nlpMethodsKey, nlpMethodsContext)

// ── Quality Level system ────────────────────────────────────

const qualityLevelDownloading = ref(false)

const qualityLevels = ref([
  {
    value: 'rapida',
    label: 'Rápida',
    description: 'Análisis rápido con un motor',
    icon: 'pi pi-bolt',
    available: true,
    recommended: false,
    reason: null as string | null,
    estimate: null as string | null,
  },
  {
    value: 'completa',
    label: 'Completa',
    description: 'Verificación cruzada con 2 motores',
    icon: 'pi pi-check-circle',
    available: true,
    recommended: false,
    reason: null as string | null,
    estimate: null as string | null,
  },
  {
    value: 'experta',
    label: 'Experta',
    description: 'Máxima precisión con 3 motores votando',
    icon: 'pi pi-star',
    available: true,
    recommended: false,
    reason: null as string | null,
    estimate: null as string | null,
  },
])

async function loadQualityLevels() {
  try {
    const hwData = await api.get<{ levels: Array<{ value: string; available: boolean; recommended: boolean; reason: string }> }>('/api/services/llm/hardware')
    if (hwData?.levels) {
      for (const apiLevel of hwData.levels) {
        const local = qualityLevels.value.find(l => l.value === apiLevel.value)
        if (local) {
          local.available = apiLevel.available
          local.recommended = apiLevel.recommended
          local.reason = apiLevel.reason
        }
      }
    }

    const estData = await api.get<{ estimates: Record<string, { description: string }> }>('/api/services/llm/estimates?word_count=50000')
    if (estData?.estimates) {
      for (const [level, est] of Object.entries(estData.estimates) as [string, { description: string }][]) {
        const local = qualityLevels.value.find(l => l.value === level)
        if (local && est?.description) {
          local.estimate = est.description
        }
      }
    }

    const cfgData = await api.get<{ qualityLevel: string; sensitivity: number }>('/api/services/llm/config')
    if (cfgData) {
      settings.value.qualityLevel = cfgData.qualityLevel || 'rapida'
      settings.value.llmSensitivity = cfgData.sensitivity ?? 5
    }
  } catch {}
}

async function selectQualityLevel(level: string) {
  settings.value.qualityLevel = level
  try {
    const data = await api.put<{ modelsToDownload?: string[] }>('/api/services/llm/config', {
      qualityLevel: level,
      sensitivity: settings.value.llmSensitivity ?? 5,
    })

    if (data?.modelsToDownload?.length) {
      qualityLevelDownloading.value = true
      for (const modelName of data.modelsToDownload) {
        await ollamaContext.installModel(modelName)
      }
      qualityLevelDownloading.value = false
    }

    onSettingChange()
  } catch (e) {
    console.error('Error setting quality level:', e)
  }
}

function onLlmSensitivityChange() {
  api.put('/api/services/llm/config', {
    qualityLevel: settings.value.qualityLevel || 'rapida',
    sensitivity: settings.value.llmSensitivity ?? 5,
  }).catch(() => {})
  onSettingChange()
}

// ── System capabilities (proxied from store) ───────────────

const systemCapabilities = computed(() => systemStore.systemCapabilities)
const loadingCapabilities = computed(() => systemStore.capabilitiesLoading)

// ── LanguageTool state ─────────────────────────────────────

const ltInstalling = computed(() => systemStore.ltInstalling)
const ltStarting = computed(() => systemStore.ltStarting)
const ltInstallProgress = computed(() => systemStore.ltInstallProgress)
const ltState = computed<LTState>(() => systemStore.ltState)

const ltActionConfig = computed(() => {
  const configs: Record<LTState, { label: string; icon: string; severity: string; action: () => void }> = {
    not_installed: {
      label: 'Instalar',
      icon: 'pi pi-download',
      severity: 'warning',
      action: installLanguageTool
    },
    installing: {
      label: 'Instalando...',
      icon: 'pi pi-spin pi-spinner',
      severity: 'info',
      action: () => {}
    },
    installed_not_running: {
      label: 'Iniciar',
      icon: 'pi pi-play',
      severity: 'warning',
      action: startLanguageTool
    },
    running: {
      label: 'Activo',
      icon: 'pi pi-check',
      severity: 'success',
      action: () => {}
    }
  }
  return configs[ltState.value]
})

const ltStatusMessage = computed(() => {
  if (ltState.value === 'installing' && ltInstallProgress.value) {
    return ltInstallProgress.value.detail || ltInstallProgress.value.phase_label
  }
  const messages: Record<LTState, string> = {
    not_installed: 'Instala el corrector avanzado para +2000 reglas de gramática y ortografía (~300MB)',
    installing: 'Iniciando descarga...',
    installed_not_running: 'Corrector avanzado instalado pero no activo',
    running: 'Corrector avanzado activo'
  }
  return messages[ltState.value]
})

const installLanguageTool = async () => {
  toast.add({ severity: 'info', summary: 'Instalando corrector avanzado', detail: 'Descargando componentes necesarios...', life: 5000 })
  const success = await systemStore.installLanguageTool()
  if (success) {
    await loadSystemCapabilities()
    const lt = systemCapabilities.value?.languagetool
    if (lt?.running) {
      toast.add({ severity: 'success', summary: 'Corrector avanzado instalado', detail: 'Corrector avanzado disponible', life: 3000 })
    } else if (lt?.installed) {
      toast.add({ severity: 'success', summary: 'Corrector avanzado instalado', detail: 'Puedes iniciarlo desde aquí', life: 3000 })
    }
  } else {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo instalar el corrector avanzado', life: 5000 })
  }
}

const startLanguageTool = async () => {
  const success = await systemStore.startLanguageTool()
  if (success) {
    await loadSystemCapabilities()
    toast.add({ severity: 'success', summary: 'Corrector avanzado iniciado', detail: 'Corrector avanzado disponible', life: 3000 })
  } else {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo iniciar el corrector avanzado', life: 5000 })
  }
}

// ── Data location state ────────────────────────────────────

const dataLocation = ref('~/.narrative_assistant')
const showResetDialog = ref(false)
const showDataLocationDialog = ref(false)
const newDataLocation = ref('')
const migrateData = ref(true)
const changingLocation = ref(false)

// ── Child component refs ───────────────────────────────────

const correctionsSection = ref()
const dataMaintenanceSection = ref()

// ── Navigation ─────────────────────────────────────────────

const activeSection = ref('apariencia')
const contentArea = ref<HTMLElement | null>(null)
const activeProjectId = computed(() => projectsStore.currentProject?.id ?? null)
const loadingProjectAnalysisSettings = ref(false)
let analysisSyncTimer: ReturnType<typeof setTimeout> | null = null
let capabilitiesWarningShown = false

async function loadProjectAnalysisSettings(projectId: number): Promise<void> {
  loadingProjectAnalysisSettings.value = true
  try {
    await loadAnalysisSettingsFromBackend(projectId)
  } finally {
    loadingProjectAnalysisSettings.value = false
  }
}

function queueAnalysisSettingsSync(): void {
  const projectId = activeProjectId.value
  if (!projectId || loadingProjectAnalysisSettings.value) return

  if (analysisSyncTimer) {
    clearTimeout(analysisSyncTimer)
  }
  analysisSyncTimer = setTimeout(async () => {
    await syncAnalysisSettingsToBackend(projectId)
  }, 400)
}

const analysisSettingsSignature = computed(() =>
  JSON.stringify({
    projectId: activeProjectId.value,
    coreference: settings.value.enabledNLPMethods.coreference,
    ner: settings.value.enabledNLPMethods.ner,
    grammar: settings.value.enabledNLPMethods.grammar,
    spelling: settings.value.enabledNLPMethods.spelling,
    characterKnowledge: settings.value.enabledNLPMethods.character_knowledge,
    characterKnowledgeMode: settings.value.characterKnowledgeMode,
    multiModelSynthesis: settings.value.multiModelSynthesis,
  })
)

watch(
  analysisSettingsSignature,
  (_newValue, oldValue) => {
    if (!oldValue) return
    queueAnalysisSettingsSync()
  },
  { flush: 'post' }
)

watch(
  activeProjectId,
  async (projectId, previousProjectId) => {
    if (!projectId || projectId === previousProjectId) return
    await loadProjectAnalysisSettings(projectId)
  }
)

onMounted(async () => {
  loadSettings()
  if (activeProjectId.value) {
    await loadProjectAnalysisSettings(activeProjectId.value)
  }
  await loadSystemCapabilities()
  await loadCurrentDataLocation()
  correctionsSection.value?.loadCorrectionPresets()
  await loadQualityLevels()
  dataMaintenanceSection.value?.loadUserRejections()
})

onUnmounted(() => {
  if (analysisSyncTimer) {
    clearTimeout(analysisSyncTimer)
    analysisSyncTimer = null
    const projectId = activeProjectId.value
    if (projectId) {
      syncAnalysisSettingsToBackend(projectId).catch(() => undefined)
    }
  }
  cleanupPersistence()
  ollamaContext.cleanup()
  systemStore.stopLTPolling()
})

const loadSystemCapabilities = async (): Promise<boolean> => {
  const capabilities = await systemStore.loadCapabilities(true)
  if (capabilities) {
    if (
      !capabilitiesWarningShown &&
      capabilities.detection_status === 'uncertain' &&
      Array.isArray(capabilities.detection_warnings) &&
      capabilities.detection_warnings.length > 0
    ) {
      capabilitiesWarningShown = true
      toast.add({
        severity: 'warn',
        summary: 'Preparación en curso',
        detail: 'El sistema sigue verificando algunos componentes. Puedes continuar y reintentar más tarde si alguna función no aparece.',
        life: 6000,
      })
    }

    const savedSettings = safeGetItem('narrative_assistant_settings')
    if (!savedSettings) {
      applyDefaultsFromCapabilities(capabilities)
    }
    return true
  }
  console.error('Error loading system capabilities')
  return false
}

const changeDataLocation = () => {
  loadCurrentDataLocation()
  showDataLocationDialog.value = true
}

const loadCurrentDataLocation = async () => {
  try {
    const result = await api.getRaw<{ success: boolean; data?: any }>('/api/maintenance/data-location')
    if (result.success && result.data) {
      dataLocation.value = result.data.path
      newDataLocation.value = result.data.path
    }
  } catch (error) {
    console.error('Error loading data location:', error)
  }
}

const confirmChangeDataLocation = async () => {
  if (!newDataLocation.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Ruta vacía', detail: 'Introduce una ruta válida', life: 3000 })
    return
  }

  changingLocation.value = true

  try {
    const result = await api.postRaw<{ success: boolean; data?: any; error?: string }>('/api/maintenance/data-location', {
      new_path: newDataLocation.value,
      migrate_data: migrateData.value
    })

    if (result.success) {
      dataLocation.value = newDataLocation.value
      showDataLocationDialog.value = false

      toast.add({
        severity: 'success',
        summary: 'Ubicación actualizada',
        detail: result.data?.restart_required
          ? 'Reinicia la aplicación para aplicar los cambios'
          : 'La ubicación de datos ha sido actualizada',
        life: 5000
      })

      if (result.data?.migrated_items?.length > 0) {
        toast.add({
          severity: 'info',
          summary: 'Datos migrados',
          detail: `Se han migrado: ${result.data.migrated_items.join(', ')}`,
          life: 5000
        })
      }
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: result.error || 'No se pudo cambiar la ubicación', life: 5000 })
    }
  } catch (error) {
    console.error('Error changing data location:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo cambiar la ubicación de datos. Comprueba que la carpeta existe y tiene permisos de escritura.',
      life: 3000
    })
  } finally {
    changingLocation.value = false
  }
}

const confirmReset = () => {
  showResetDialog.value = true
}

const resetSettings = () => {
  doResetSettings(systemCapabilities.value)
  showResetDialog.value = false
}

const goBack = () => {
  router.go(-1)
}

const scrollToSection = (sectionId: string) => {
  const element = document.getElementById(sectionId)
  if (element && contentArea.value) {
    const containerRect = contentArea.value.getBoundingClientRect()
    const elementRect = element.getBoundingClientRect()
    const scrollTop = contentArea.value.scrollTop
    const elementRelativeTop = elementRect.top - containerRect.top + scrollTop
    const offset = 16

    contentArea.value.scrollTo({
      top: elementRelativeTop - offset,
      behavior: 'smooth'
    })
    activeSection.value = sectionId
  }
}

const handleScroll = () => {
  if (!contentArea.value) return

  const sections = ['apariencia', 'analisis', 'analizador-ia', 'metodos-nlp', 'correcciones', 'datos-mantenimiento', 'licencia']
  const scrollPosition = contentArea.value.scrollTop + 100

  for (const sectionId of sections) {
    const element = document.getElementById(sectionId)
    if (element) {
      const offsetTop = element.offsetTop
      const offsetBottom = offsetTop + element.offsetHeight

      if (scrollPosition >= offsetTop && scrollPosition < offsetBottom) {
        activeSection.value = sectionId
        break
      }
    }
  }
}
</script>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  --settings-nav-hover-color: var(--p-primary-800, var(--primary-color, #2563eb));
  --settings-nav-active-color: var(--p-primary-800, var(--primary-color, #2563eb));
  --settings-nav-hover-bg: color-mix(in srgb, var(--p-primary-color, var(--primary-color, #3B82F6)) 10%, var(--surface-card));
  --settings-nav-active-bg: color-mix(in srgb, var(--p-primary-color, var(--primary-color, #3B82F6)) 16%, var(--surface-card));
}

:global(.dark) .settings-view {
  --settings-nav-hover-color: var(--text-color, #f8fafc);
  --settings-nav-active-color: var(--text-color, #f8fafc);
  --settings-nav-hover-bg: color-mix(in srgb, var(--p-primary-color, var(--primary-color, #3B82F6)) 18%, var(--surface-card, #111827));
  --settings-nav-active-bg: color-mix(in srgb, var(--p-primary-color, var(--primary-color, #3B82F6)) 28%, var(--surface-card, #111827));
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  flex-shrink: 0;
}

:global(.dark) .settings-header {
  background: var(--surface-card);
  border-bottom-color: var(--surface-border);
}

.settings-header h1 {
  margin: 0;
  font-size: 2rem;
}

.settings-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.settings-sidebar {
  width: 250px;
  flex-shrink: 0;
  background: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  overflow-y: auto;
  padding: 1.5rem 0;
}

:global(.dark) .settings-sidebar {
  background: var(--surface-card);
  border-right-color: var(--surface-border);
}

.nav-menu {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-menu li {
  margin: 0;
}

.nav-menu a,
.nav-menu a:link,
.nav-menu a:visited,
.nav-menu a:hover,
.nav-menu a:active {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  color: var(--text-color);
  text-decoration: none !important;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  border-left: 3px solid transparent;
  cursor: pointer;
  user-select: none;
}

.nav-menu a:hover {
  background: var(--settings-nav-hover-bg);
  color: var(--settings-nav-hover-color) !important;
}

.nav-menu a.active {
  background: var(--settings-nav-active-bg);
  color: var(--settings-nav-active-color) !important;
  border-left-color: var(--p-primary-color, var(--primary-color, #3B82F6));
  font-weight: 600;
}

:global(.dark) .nav-menu a:hover {
  background: var(--settings-nav-hover-bg);
  color: var(--settings-nav-hover-color) !important;
}

:global(.dark) .nav-menu a.active {
  background: var(--settings-nav-active-bg);
  color: var(--settings-nav-active-color) !important;
}

:global(html.dark) .settings-view .nav-menu a:hover,
:global(html.dark) .settings-view .nav-menu a:hover span,
:global(html.dark) .settings-view .nav-menu a:hover i {
  color: var(--settings-nav-hover-color) !important;
}

:global(html.dark) .settings-view .nav-menu a.active,
:global(html.dark) .settings-view .nav-menu a.active span,
:global(html.dark) .settings-view .nav-menu a.active i {
  color: var(--settings-nav-active-color) !important;
}

.nav-menu a i {
  font-size: 1.1rem;
  width: 1.5rem;
  text-align: center;
  color: inherit;
  text-decoration: none !important;
}

.nav-menu a span {
  font-size: 0.95rem;
  color: inherit;
  text-decoration: none !important;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
  scroll-behavior: smooth;
  background: var(--surface-ground);
}

.settings-content > :deep(.p-card) {
  max-width: 1100px;
  margin-bottom: 1.5rem;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  color: var(--text-color);
}

.settings-content > :deep(.p-card .p-card-body),
.settings-content > :deep(.p-card .p-card-content),
.settings-content > :deep(.p-card .p-card-title),
.settings-content > :deep(.p-card .p-card-subtitle) {
  background: transparent;
  color: inherit;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
}

.section-title i {
  color: var(--p-primary-color);
}

/* ── Shared styles used by child section components ──────── */

:deep(.setting-item) {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 0;
  border-bottom: 1px solid var(--surface-border);
}

:global(.dark) :deep(.setting-item) {
  border-bottom-color: var(--surface-border);
}

:deep(.setting-item:last-child) {
  border-bottom: none;
}

:deep(.setting-item.column) {
  flex-direction: column;
  gap: 1rem;
}

:deep(.setting-item.column .setting-info) {
  padding-right: 0;
  max-width: 100%;
}

:deep(.setting-item.column .setting-control),
:deep(.setting-item.column .system-patterns-list),
:deep(.setting-item.column .correction-config-summary),
:deep(.setting-item.column .user-rejections-list) {
  width: 100%;
}

:deep(.setting-info) {
  flex: 1;
  padding-right: 2rem;
}

:deep(.setting-label) {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

:deep(.setting-description) {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

:deep(.setting-description code) {
  background: var(--p-surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
}

:global(.dark) :deep(.setting-description code) {
  background: var(--p-surface-800);
}

:deep(.setting-control) {
  min-width: 200px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

:deep(.setting-control :deep(.p-slider)) {
  width: 100%;
}

:deep(.setting-control.wide) {
  min-width: 350px;
}

/* ── Sensitivity section styles ─────────────────────────── */

:deep(.sensitivity-section) {
  padding: 0.5rem 0;
}

:deep(.sensitivity-header) {
  margin-bottom: 1.25rem;
}

:deep(.sensitivity-header .setting-label) {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

:deep(.sensitivity-presets-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

:deep(.preset-button) {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--p-surface-50);
  border: 2px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;
}

:deep(.preset-button:hover) {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-surface-50));
}

:deep(.preset-button.active) {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-50));
}

:deep(.preset-button > i:first-child) {
  font-size: 1.5rem;
  color: var(--p-text-muted-color);
  width: 2rem;
  text-align: center;
}

:deep(.preset-button.active > i:first-child) {
  color: var(--p-primary-color);
}

:deep(.preset-content) {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

:deep(.preset-title) {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-text-color);
}

:deep(.preset-button .preset-desc) {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

:deep(.recommended-star) {
  color: var(--ds-text-warning);
  font-size: 0.9rem;
}

:global(.dark) :deep(.preset-button) {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) :deep(.preset-button:hover) {
  background: color-mix(in srgb, var(--p-primary-color) 15%, var(--p-surface-800));
}

:global(.dark) :deep(.preset-button.active) {
  background: color-mix(in srgb, var(--p-primary-color) 20%, var(--p-surface-800));
}

:deep(.sensitivity-slider) {
  padding: 1rem 1.25rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
  margin-bottom: 1rem;
}

:global(.dark) :deep(.sensitivity-slider) {
  background: var(--p-surface-800);
}

:deep(.slider-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

:deep(.slider-label) {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--p-text-color);
}

:deep(.slider-value) {
  font-size: 0.85rem;
  color: var(--p-primary-color);
  font-weight: 600;
}

:deep(.slider-hints) {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

:deep(.advanced-panel) {
  border-top: 1px solid var(--p-surface-200);
  padding-top: 1rem;
  margin-top: 0.5rem;
}

:global(.dark) :deep(.advanced-panel) {
  border-top-color: var(--p-surface-700);
}

:deep(.advanced-toggle) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.5rem 0;
  transition: color 0.15s ease;
}

:deep(.advanced-toggle:hover) {
  color: var(--p-primary-color);
}

:deep(.advanced-toggle i) {
  font-size: 0.75rem;
}

:deep(.advanced-content) {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) :deep(.advanced-content) {
  background: var(--p-surface-800);
}

:deep(.advanced-note) {
  margin: 0 0 1rem 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

:deep(.advanced-slider) {
  margin-bottom: 1rem;
}

:deep(.advanced-slider:last-of-type) {
  margin-bottom: 1.25rem;
}

:deep(.advanced-slider-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

:deep(.advanced-slider-header label) {
  font-size: 0.85rem;
  color: var(--p-text-color);
}

:deep(.advanced-slider-header span) {
  font-size: 0.85rem;
  color: var(--p-primary-color);
  font-weight: 500;
}

:deep(.slider-help) {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

/* ── NLP / Ollama styles ────────────────────────────────── */

:deep(.nlp-category) {
  margin-bottom: 2rem;
}

:deep(.nlp-category:last-of-type) {
  margin-bottom: 1rem;
}

:deep(.category-header) {
  margin-bottom: 1rem;
}

:deep(.category-header h4) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
}

:deep(.category-header h4 i) {
  color: var(--p-primary-color);
}

:deep(.category-desc) {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

:deep(.methods-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

:deep(.method-card) {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  padding: 1rem;
  transition: all 0.15s ease;
}

:global(.dark) :deep(.method-card) {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:deep(.method-card.enabled) {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-surface-50));
}

:global(.dark) :deep(.method-card.enabled) {
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-800));
}

:deep(.method-card.disabled) {
  opacity: 0.6;
}

:deep(.method-header) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

:deep(.method-header .method-name) {
  font-weight: 600;
  font-size: 0.95rem;
  flex: 1;
  min-width: 120px;
}

:deep(.method-tag) {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  font-weight: 600;
}

:deep(.method-card .method-tag.p-tag-info) {
  background: var(--blue-100) !important;
  color: var(--blue-700) !important;
  border: 1px solid var(--blue-300) !important;
}

:deep(.method-card .method-tag.p-tag-warning) {
  background: var(--yellow-100) !important;
  color: var(--yellow-800) !important;
  border: 1px solid var(--yellow-400) !important;
}

:deep(.method-card .method-tag.p-tag-danger) {
  background: var(--red-100) !important;
  color: var(--red-700) !important;
  border: 1px solid var(--red-300) !important;
}

:global(.dark) :deep(.method-card .method-tag.p-tag-info) {
  background: var(--blue-900) !important;
  color: var(--blue-200) !important;
  border: 1px solid var(--blue-600) !important;
}

:global(.dark) :deep(.method-card .method-tag.p-tag-warning) {
  background: var(--yellow-900) !important;
  color: var(--yellow-200) !important;
  border: 1px solid var(--ds-color-warning, #d97706) !important;
}

:global(.dark) :deep(.method-card .method-tag.p-tag-danger) {
  background: var(--red-900) !important;
  color: var(--red-200) !important;
  border: 1px solid var(--red-600) !important;
}

:deep(.method-description) {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}

:deep(.method-weight) {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

/* Quality Level cards */
:deep(.quality-level-section) {
  margin-bottom: 1rem;
}

:deep(.quality-level-cards) {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

:deep(.quality-level-card) {
  border: 2px solid var(--p-surface-200);
  border-radius: 8px;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--p-surface-0);
}

:deep(.quality-level-card:hover:not(.disabled)) {
  border-color: var(--p-primary-300);
  background: var(--p-primary-50);
}

:deep(.quality-level-card.selected) {
  border-color: var(--p-primary-500);
  background: var(--p-primary-50);
}

:deep(.quality-level-card.disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

:deep(.quality-level-card.recommended:not(.selected)) {
  border-color: var(--p-green-200);
}

:deep(.quality-level-header) {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.3rem;
}

:deep(.quality-level-header i) {
  color: var(--p-primary-500);
  font-size: 1.1rem;
}

:deep(.quality-level-header strong) {
  font-size: 0.95rem;
}

:deep(.recommended-badge) {
  font-size: 0.65rem !important;
  padding: 0.1rem 0.3rem !important;
}

:deep(.quality-level-desc) {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
  margin: 0 0 0.3rem 0;
}

:deep(.quality-level-time) {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
  font-style: italic;
}

:deep(.slider-value) {
  font-weight: 600;
  font-size: 0.9rem;
  min-width: 1.5rem;
  text-align: center;
  margin-left: 0.5rem;
}

:deep(.motors-list) {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-left: 0.5rem;
}

:deep(.motor-item) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 6px;
  background: var(--p-surface-50);
}

:deep(.motor-item i) {
  font-size: 1.1rem;
  color: var(--p-primary-400);
}

:deep(.motor-item div) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.motor-item strong) {
  font-size: 0.85rem;
}

:deep(.motor-item span) {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
}

:global(.dark) :deep(.quality-level-card) {
  background: var(--p-surface-800);
  border-color: var(--p-surface-600);
}

:global(.dark) :deep(.quality-level-card.selected) {
  background: var(--p-primary-900);
  border-color: var(--p-primary-400);
}

:global(.dark) :deep(.quality-level-card:hover:not(.disabled)) {
  background: var(--p-primary-900);
  border-color: var(--p-primary-500);
}

:global(.dark) :deep(.motor-item) {
  background: var(--p-surface-700);
}

:deep(.hardware-inline-badge) {
  font-size: 0.7rem !important;
  padding: 0.15rem 0.4rem !important;
  vertical-align: middle;
  margin-left: 0.4rem;
}

:deep(.ollama-inline-badge) {
  font-size: 0.7rem !important;
  padding: 0.15rem 0.4rem !important;
  vertical-align: middle;
  margin-left: 0.25rem;
}

/* Ollama action card / ready bar */
:deep(.ollama-ready-bar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: var(--green-50);
  border: 1px solid var(--green-200);
  border-radius: var(--app-radius);
  margin-bottom: 1rem;
}

:deep(.ollama-ready-info) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--green-700);
}

:deep(.ollama-ready-info i) {
  color: var(--ds-text-success);
}

:deep(.ollama-action-card) {
  background: var(--yellow-50);
  border: 1px solid var(--yellow-200);
  border-radius: var(--app-radius);
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
}

:deep(.ollama-action-card.ollama-state-no_models) {
  background: var(--blue-50);
  border-color: var(--blue-200);
}

:deep(.ollama-action-card.ollama-state-configuring) {
  background: var(--blue-50);
  border-color: var(--blue-200);
}

:deep(.ollama-action-card.ollama-state-configuring .ollama-action-content > i) {
  color: var(--ds-text-info, #3b82f6);
}

:deep(.ollama-hint) {
  font-size: 0.7rem;
  opacity: 0.7;
  font-style: italic;
}

:deep(.ollama-action-content) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

:deep(.ollama-action-content > i) {
  font-size: 1.25rem;
  color: var(--ds-color-warning, #d97706);
  flex-shrink: 0;
}

:deep(.ollama-action-card.ollama-state-no_models .ollama-action-content > i) {
  color: var(--ds-text-info);
}

:deep(.ollama-action-text) {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

:deep(.ollama-action-text strong) {
  font-size: 0.9rem;
  color: var(--p-text-color);
}

:deep(.ollama-action-text span) {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

:deep(.ollama-progress-wrapper) {
  width: 100%;
  margin-top: 0.5rem;
}

:deep(.lt-progress-container) {
  margin-top: 0.5rem;
  width: 100%;
}

:global(.dark) :deep(.ollama-ready-bar) {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--green-800);
}

:global(.dark) :deep(.ollama-ready-info) {
  color: var(--green-400);
}

:global(.dark) :deep(.ollama-action-card) {
  background: rgba(234, 179, 8, 0.1);
  border-color: var(--yellow-800);
}

:global(.dark) :deep(.ollama-action-card.ollama-state-no_models),
:global(.dark) :deep(.ollama-action-card.ollama-state-configuring) {
  background: color-mix(in srgb, var(--p-primary-color, #3B82F6) 10%, transparent);
  border-color: var(--p-primary-800, #1e40af);
}

:global(.dark) :deep(.ollama-action-content > i) {
  color: var(--yellow-400);
}

:global(.dark) :deep(.ollama-action-card.ollama-state-no_models .ollama-action-content > i),
:global(.dark) :deep(.ollama-action-card.ollama-state-configuring .ollama-action-content > i) {
  color: var(--blue-400);
}

/* ── Corrections section styles ─────────────────────────── */

:deep(.correction-info-message) {
  font-size: 0.9rem;
  line-height: 1.5;
}

:deep(.correction-info-message p) {
  margin: 0;
}

:deep(.correction-config-summary) {
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
  padding: 1rem;
}

:global(.dark) :deep(.correction-config-summary) {
  background: var(--p-surface-800);
}

:deep(.config-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

:deep(.config-section) {
  background: var(--p-surface-0);
  border-radius: var(--p-border-radius);
  padding: 1rem;
}

:global(.dark) :deep(.config-section) {
  background: var(--p-surface-900);
}

:deep(.config-section h4) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-primary-color);
}

:deep(.config-section h4 i) {
  font-size: 1rem;
}

:deep(.config-items) {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

:deep(.config-item) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

:deep(.config-label) {
  color: var(--p-text-secondary-color);
  min-width: 80px;
}

:deep(.preset-dropdown-option) {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

:deep(.preset-dropdown-option .preset-name) {
  font-weight: 500;
}

:deep(.preset-dropdown-option .preset-description) {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
}

:deep(.text-green-500) {
  color: var(--p-green-500);
}

:deep(.text-red-500) {
  color: var(--p-red-500);
}

/* ── Knowledge mode selector ────────────────────────────── */

:deep(.knowledge-mode-selector) {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

:deep(.knowledge-mode-card) {
  flex: 1;
  min-width: 200px;
  padding: 1rem;
  border: 2px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius);
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--p-surface-ground);
}

:deep(.knowledge-mode-card:hover:not(.disabled)) {
  border-color: var(--p-primary-color);
  background: var(--p-surface-hover);
}

:deep(.knowledge-mode-card.selected) {
  border-color: var(--p-primary-color);
  background: var(--p-primary-50);
}

:deep(.knowledge-mode-card.disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

:deep(.knowledge-mode-card .mode-name) {
  font-weight: 600;
  font-size: 1rem;
}

:deep(.knowledge-mode-card .mode-description) {
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
  line-height: 1.4;
}

:deep(.knowledge-mode-card .method-tag) {
  margin-top: 0.5rem;
  width: fit-content;
}

/* ── Data maintenance styles ────────────────────────────── */

:deep(.info-message) {
  margin-top: 1rem;
}

:deep(.info-message :deep(.p-message-wrapper)) {
  padding: 0.75rem 1rem;
  gap: 0.75rem;
}

:deep(.info-message .message-content) {
  line-height: 1.5;
}

:deep(.loading-patterns) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  color: var(--p-text-secondary-color);
}

:deep(.user-rejections-list) {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 300px;
  overflow-y: auto;
}

:deep(.rejection-item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

:global(.dark) :deep(.rejection-item) {
  background: var(--p-surface-800);
}

:deep(.rejection-info) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

:deep(.rejection-name) {
  font-weight: 500;
  color: var(--p-text-color);
}

:deep(.rejection-reason) {
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
}

:deep(.empty-rejections) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  color: var(--p-text-secondary-color);
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

:global(.dark) :deep(.empty-rejections) {
  background: var(--p-surface-800);
}

:deep(.empty-rejections i) {
  font-size: 1.25rem;
  color: var(--p-green-500);
}

/* ── Data Location Dialog ───────────────────────────────── */

.data-location-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.dialog-description {
  margin: 0;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.location-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.location-field {
  width: 100%;
}

.migrate-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) .migrate-option {
  background: var(--p-surface-800);
}

.migrate-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.migrate-info label {
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}

.migrate-description {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.location-info-message {
  margin: 0;
}

.location-info-message :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
}
</style>
