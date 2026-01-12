<template>
  <div class="settings-view">
    <div class="settings-header">
      <Button
        icon="pi pi-arrow-left"
        text
        @click="goBack"
        label="Volver"
      />
      <h1>Configuración</h1>
    </div>

    <div class="settings-layout">
      <!-- Sidebar Navigation -->
      <nav class="settings-sidebar">
        <ul class="nav-menu">
          <li>
            <a href="#apariencia" @click.prevent="scrollToSection('apariencia')" :class="{ active: activeSection === 'apariencia' }">
              <i class="pi pi-palette"></i>
              <span>Apariencia</span>
            </a>
          </li>
          <li>
            <a href="#analisis" @click.prevent="scrollToSection('analisis')" :class="{ active: activeSection === 'analisis' }">
              <i class="pi pi-cog"></i>
              <span>Análisis</span>
            </a>
          </li>
          <li>
            <a href="#ia-local" @click.prevent="scrollToSection('ia-local')" :class="{ active: activeSection === 'ia-local' }">
              <i class="pi pi-microchip-ai"></i>
              <span>IA Local</span>
            </a>
          </li>
          <li>
            <a href="#notificaciones" @click.prevent="scrollToSection('notificaciones')" :class="{ active: activeSection === 'notificaciones' }">
              <i class="pi pi-bell"></i>
              <span>Notificaciones</span>
            </a>
          </li>
          <li>
            <a href="#privacidad" @click.prevent="scrollToSection('privacidad')" :class="{ active: activeSection === 'privacidad' }">
              <i class="pi pi-shield"></i>
              <span>Privacidad</span>
            </a>
          </li>
          <li>
            <a href="#mantenimiento" @click.prevent="scrollToSection('mantenimiento')" :class="{ active: activeSection === 'mantenimiento' }">
              <i class="pi pi-wrench"></i>
              <span>Mantenimiento</span>
            </a>
          </li>
          <li>
            <a href="#acerca-de" @click.prevent="scrollToSection('acerca-de')" :class="{ active: activeSection === 'acerca-de' }">
              <i class="pi pi-info-circle"></i>
              <span>Acerca de</span>
            </a>
          </li>
        </ul>
      </nav>

      <!-- Content Area -->
      <div class="settings-content" ref="contentArea" @scroll="handleScroll">
      <!-- Apariencia -->
      <Card id="apariencia">
        <template #title>
          <div class="section-title">
            <i class="pi pi-palette"></i>
            <span>Apariencia</span>
          </div>
        </template>
        <template #content>
          <!-- Modo claro/oscuro/auto -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Modo de apariencia</label>
              <p class="setting-description">Elige entre modo claro, oscuro o automático según el sistema</p>
            </div>
            <div class="setting-control">
              <SelectButton
                :modelValue="themeStore.config.mode"
                @update:modelValue="(val) => themeStore.setMode(val)"
                :options="modeOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <!-- Estilo visual (preset) -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Estilo visual</label>
              <p class="setting-description">Selecciona el estilo base de la interfaz</p>
            </div>
            <div class="setting-control">
              <Dropdown
                :modelValue="themeStore.config.preset"
                @update:modelValue="onPresetChange"
                :options="presetOptions"
                optionLabel="label"
                optionValue="value"
              >
                <template #option="slotProps">
                  <div class="preset-option">
                    <span class="preset-name">{{ slotProps.option.label }}</span>
                    <span class="preset-desc">{{ slotProps.option.description }}</span>
                  </div>
                </template>
              </Dropdown>
            </div>
          </div>

          <!-- Color primario -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Color primario</label>
              <p class="setting-description">Color de acento para botones, enlaces y elementos destacados</p>
            </div>
            <div class="setting-control wide">
              <div class="color-palette">
                <button
                  v-for="color in PRIMARY_COLORS"
                  :key="color.name"
                  class="color-swatch"
                  :class="{ active: themeStore.config.primaryColor === color.value }"
                  :style="{ backgroundColor: color.value }"
                  :title="color.label"
                  @click="themeStore.setPrimaryColor(color.value)"
                >
                  <i v-if="themeStore.config.primaryColor === color.value" class="pi pi-check"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- Tamaño de fuente -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Tamaño de fuente</label>
              <p class="setting-description">Tamaño base del texto en toda la aplicación</p>
            </div>
            <div class="setting-control">
              <SelectButton
                :modelValue="themeStore.config.fontSize"
                @update:modelValue="(val) => themeStore.setFontSize(val)"
                :options="fontSizeOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <!-- Interlineado -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Interlineado</label>
              <p class="setting-description">Espaciado entre líneas del texto</p>
            </div>
            <div class="setting-control">
              <Dropdown
                :modelValue="themeStore.config.lineHeight"
                @update:modelValue="onLineHeightChange"
                :options="lineHeightOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <!-- Radio de bordes -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Bordes redondeados</label>
              <p class="setting-description">Nivel de redondeo en botones y tarjetas</p>
            </div>
            <div class="setting-control">
              <SelectButton
                :modelValue="themeStore.config.radius"
                @update:modelValue="(val) => themeStore.setRadius(val)"
                :options="radiusOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <!-- Densidad de UI -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Densidad de la interfaz</label>
              <p class="setting-description">Espaciado entre elementos de la interfaz</p>
            </div>
            <div class="setting-control">
              <SelectButton
                :modelValue="themeStore.config.compactness"
                @update:modelValue="(val) => themeStore.setCompactness(val)"
                :options="compactnessOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
          </div>

          <!-- Reducir animaciones -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Reducir animaciones</label>
              <p class="setting-description">Minimiza las animaciones y transiciones para mejorar la accesibilidad</p>
            </div>
            <div class="setting-control">
              <InputSwitch
                :modelValue="themeStore.config.reducedMotion"
                @update:modelValue="onReducedMotionChange"
              />
            </div>
          </div>

          <!-- Botón de restablecer apariencia -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Restablecer apariencia</label>
              <p class="setting-description">Volver a los valores por defecto de apariencia</p>
            </div>
            <div class="setting-control">
              <Button
                label="Restablecer"
                icon="pi pi-refresh"
                severity="secondary"
                outlined
                size="small"
                @click="themeStore.resetToDefaults()"
              />
            </div>
          </div>
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
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Confianza mínima para alertas</label>
              <p class="setting-description">
                Solo mostrar alertas con confianza superior a este valor ({{ settings.minConfidence }}%)
              </p>
            </div>
            <div class="setting-control">
              <Slider
                v-model="settings.minConfidence"
                :min="0"
                :max="100"
                :step="5"
                @change="onSliderChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Análisis automático</label>
              <p class="setting-description">Iniciar análisis automáticamente al crear proyecto</p>
            </div>
            <div class="setting-control">
              <InputSwitch
                v-model="settings.autoAnalysis"
                @change="onSettingChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Mostrar resultados parciales</label>
              <p class="setting-description">Mostrar resultados disponibles mientras el análisis continúa</p>
            </div>
            <div class="setting-control">
              <InputSwitch
                v-model="settings.showPartialResults"
                @change="onSettingChange"
              />
            </div>
          </div>
        </template>
      </Card>

      <!-- LLM / Inferencia -->
      <Card id="ia-local">
        <template #title>
          <div class="section-title">
            <i class="pi pi-microchip-ai"></i>
            <span>Análisis con IA Local</span>
          </div>
        </template>
        <template #content>
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Modelos LLM adicionales</label>
              <p class="setting-description">
                Selecciona modelos LLM para análisis avanzado.
                Los métodos básicos (reglas y embeddings) siempre están activos.
              </p>
            </div>
            <div class="setting-control wide">
              <MultiSelect
                v-model="settings.enabledInferenceMethods"
                :options="inferenceMethodOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Seleccionar modelos LLM"
                display="chip"
                :showToggleAll="false"
                @change="onSettingChange"
              >
                <template #option="slotProps">
                  <div class="method-option">
                    <div class="method-info">
                      <span class="method-name">{{ slotProps.option.label }}</span>
                      <span class="method-desc">{{ slotProps.option.description }}</span>
                    </div>
                    <div class="method-badges">
                      <Badge
                        :value="getSpeedLabel(slotProps.option.speed)"
                        :severity="getSpeedSeverity(slotProps.option.speed)"
                        class="speed-badge"
                      />
                    </div>
                  </div>
                </template>
              </MultiSelect>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Priorizar velocidad</label>
              <p class="setting-description">
                Usar configuración optimizada para respuestas rápidas
              </p>
            </div>
            <div class="setting-control">
              <InputSwitch
                v-model="settings.prioritizeSpeed"
                @change="onSettingChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Confianza mínima de inferencia</label>
              <p class="setting-description">
                Solo mostrar expectativas con confianza superior a {{ settings.inferenceMinConfidence }}%
              </p>
            </div>
            <div class="setting-control">
              <Slider
                v-model="settings.inferenceMinConfidence"
                :min="20"
                :max="90"
                :step="5"
                @change="onSliderChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Consenso mínimo para violaciones</label>
              <p class="setting-description">
                Porcentaje de métodos que deben coincidir ({{ settings.inferenceMinConsensus }}%)
              </p>
            </div>
            <div class="setting-control">
              <Slider
                v-model="settings.inferenceMinConsensus"
                :min="30"
                :max="100"
                :step="10"
                @change="onSliderChange"
              />
            </div>
          </div>

        </template>
      </Card>

      <!-- Notificaciones -->
      <Card id="notificaciones">
        <template #title>
          <div class="section-title">
            <i class="pi pi-bell"></i>
            <span>Notificaciones</span>
          </div>
        </template>
        <template #content>
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Notificaciones de análisis</label>
              <p class="setting-description">Notificar cuando el análisis se complete</p>
            </div>
            <div class="setting-control">
              <InputSwitch
                v-model="settings.notifyAnalysisComplete"
                @change="onSettingChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-label">Sonidos</label>
              <p class="setting-description">Reproducir sonidos para eventos importantes</p>
            </div>
            <div class="setting-control">
              <InputSwitch
                v-model="settings.soundEnabled"
                @change="onSettingChange"
              />
            </div>
          </div>
        </template>
      </Card>

      <!-- Privacidad y Datos -->
      <Card id="privacidad">
        <template #title>
          <div class="section-title">
            <i class="pi pi-shield"></i>
            <span>Privacidad y Datos</span>
          </div>
        </template>
        <template #content>
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
                @click="changeDataLocation"
              />
            </div>
          </div>

          <Message severity="info" :closable="false" class="info-message">
            <span class="message-content">
              <strong>Modo 100% offline:</strong> Tus manuscritos nunca salen de tu máquina.
              Esta aplicación no envía datos a internet excepto para verificación de licencia.
            </span>
          </Message>
        </template>
      </Card>

      <!-- Acciones -->
      <Card id="mantenimiento">
        <template #title>
          <div class="section-title">
            <i class="pi pi-wrench"></i>
            <span>Mantenimiento</span>
          </div>
        </template>
        <template #content>
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
                @click="confirmReset"
              />
            </div>
          </div>
        </template>
      </Card>

      <!-- Acerca de -->
      <Card id="acerca-de">
        <template #title>
          <div class="section-title">
            <i class="pi pi-info-circle"></i>
            <span>Acerca de</span>
          </div>
        </template>
        <template #content>
          <div class="about-info">
            <h3>Narrative Assistant</h3>
            <p class="version">Versión 0.2.0</p>
            <p class="description">
              Herramienta de asistencia a correctores literarios profesionales para detectar
              inconsistencias en manuscritos de ficción.
            </p>
            <div class="about-links">
              <Button
                label="Documentación"
                icon="pi pi-book"
                link
                @click="openDocumentation"
              />
              <Button
                label="Reportar problema"
                icon="pi pi-github"
                link
                @click="openIssues"
              />
            </div>
          </div>
        </template>
      </Card>
      </div>
    </div>

    <!-- Confirm Reset Dialog -->
    <Dialog
      :visible="showResetDialog"
      @update:visible="showResetDialog = $event"
      modal
      header="Confirmar restablecimiento"
      :style="{ width: '450px' }"
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import Card from 'primevue/card'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import Dropdown from 'primevue/dropdown'
import Slider from 'primevue/slider'
import InputSwitch from 'primevue/inputswitch'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import MultiSelect from 'primevue/multiselect'
import Badge from 'primevue/badge'
import { useToast } from 'primevue/usetoast'
import {
  useThemeStore,
  PRIMARY_COLORS,
  FONT_SIZES,
  LINE_HEIGHTS,
  UI_RADIUS,
  UI_COMPACTNESS,
  type ThemePreset,
  type FontSize,
  type LineHeight,
  type UIRadius,
  type UICompactness
} from '@/stores/theme'

const router = useRouter()
const toast = useToast()
const themeStore = useThemeStore()

// Opciones de apariencia usando el store de tema
const modeOptions = [
  { label: 'Claro', value: 'light' },
  { label: 'Oscuro', value: 'dark' },
  { label: 'Auto', value: 'auto' }
]

const presetOptions = [
  { label: 'Aura', value: 'aura', description: 'Moderno y minimalista' },
  { label: 'Lara', value: 'lara', description: 'Inspirado en Bootstrap' },
  { label: 'Material', value: 'material', description: 'Google Material Design' },
  { label: 'Nora', value: 'nora', description: 'Empresarial y profesional' }
]

const fontSizeOptions = Object.entries(FONT_SIZES).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const lineHeightOptions = Object.entries(LINE_HEIGHTS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const radiusOptions = Object.entries(UI_RADIUS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

const compactnessOptions = Object.entries(UI_COMPACTNESS).map(([key, val]) => ({
  label: (val as { label: string }).label,
  value: key
}))

// Métodos de inferencia LLM disponibles (solo los avanzados, los básicos siempre están activos)
const inferenceMethodOptions = [
  {
    value: 'llama3.2',
    label: 'Llama 3.2 (3B)',
    description: 'Rápido, buena calidad general',
    speed: 'fast',
    quality: 'good'
  },
  {
    value: 'mistral',
    label: 'Mistral (7B)',
    description: 'Mayor calidad, más lento',
    speed: 'medium',
    quality: 'high'
  },
  {
    value: 'gemma2',
    label: 'Gemma 2 (9B)',
    description: 'Alta calidad, requiere más recursos',
    speed: 'slow',
    quality: 'very_high'
  },
  {
    value: 'qwen2.5',
    label: 'Qwen 2.5 (7B)',
    description: 'Excelente para español',
    speed: 'medium',
    quality: 'high'
  }
]

interface Settings {
  theme: 'light' | 'dark' | 'auto'
  fontSize: 'small' | 'medium' | 'large'
  lineHeight: string
  minConfidence: number
  autoAnalysis: boolean
  showPartialResults: boolean
  notifyAnalysisComplete: boolean
  soundEnabled: boolean
  // LLM/Inferencia
  enabledInferenceMethods: string[]
  inferenceMinConfidence: number
  inferenceMinConsensus: number
  prioritizeSpeed: boolean
}

const settings = ref<Settings>({
  theme: 'auto',
  fontSize: 'medium',
  lineHeight: '1.6',
  minConfidence: 70,
  autoAnalysis: true,
  showPartialResults: true,
  notifyAnalysisComplete: true,
  soundEnabled: true,
  // LLM/Inferencia defaults (solo modelos LLM, los básicos siempre están activos)
  enabledInferenceMethods: ['llama3.2'],
  inferenceMinConfidence: 50,
  inferenceMinConsensus: 60,
  prioritizeSpeed: true
})

const dataLocation = ref('~/.narrative_assistant')
const showResetDialog = ref(false)

// Debounce timer para sliders
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Navigation
const activeSection = ref('apariencia')
const contentArea = ref<HTMLElement | null>(null)

onMounted(() => {
  loadSettings()
})

onUnmounted(() => {
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer)
  }
})

const loadSettings = () => {
  const savedSettings = localStorage.getItem('narrative_assistant_settings')
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings)
      // Migrar configuración antigua si no tiene campos LLM
      // Filtrar métodos de inferencia para quitar los básicos (rule_based, embeddings)
      // que ahora siempre están activos y no deben aparecer en el selector
      const validMethodValues = inferenceMethodOptions.map(m => m.value)
      const filteredMethods = (parsed.enabledInferenceMethods || ['llama3.2'])
        .filter((m: string) => validMethodValues.includes(m))

      settings.value = {
        ...settings.value,
        ...parsed,
        enabledInferenceMethods: filteredMethods.length > 0 ? filteredMethods : ['llama3.2'],
        inferenceMinConfidence: parsed.inferenceMinConfidence ?? 50,
        inferenceMinConsensus: parsed.inferenceMinConsensus ?? 60,
        prioritizeSpeed: parsed.prioritizeSpeed ?? true
      }
    } catch (error) {
      console.error('Error loading settings:', error)
    }
  }
}

const saveSettings = () => {
  localStorage.setItem('narrative_assistant_settings', JSON.stringify(settings.value))
  // Emitir evento para que otros componentes puedan actualizar
  window.dispatchEvent(new CustomEvent('settings-changed', { detail: settings.value }))
  toast.add({
    severity: 'success',
    summary: 'Configuración guardada',
    detail: 'Los cambios se han guardado correctamente',
    life: 3000
  })
}

const onThemeChange = () => {
  themeStore.setMode(settings.value.theme)
  saveSettings()
}

// Handlers para controles de apariencia del themeStore
const onPresetChange = (val: ThemePreset) => {
  themeStore.setPreset(val)
}

const onLineHeightChange = (val: LineHeight) => {
  themeStore.setLineHeight(val)
}

const onReducedMotionChange = (val: boolean) => {
  themeStore.setReducedMotion(val)
}

const onSettingChange = () => {
  saveSettings()
}

// Debounced save para sliders - muestra toast solo al final
const onSliderChange = () => {
  // Guardar en localStorage inmediatamente (sin toast)
  localStorage.setItem('narrative_assistant_settings', JSON.stringify(settings.value))
  // Emitir evento para actualización en tiempo real
  window.dispatchEvent(new CustomEvent('settings-changed', { detail: settings.value }))

  // Debounce el toast
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer)
  }
  saveDebounceTimer = setTimeout(() => {
    toast.add({
      severity: 'success',
      summary: 'Configuración guardada',
      detail: 'Los cambios se han guardado correctamente',
      life: 3000
    })
  }, 500)
}

// Helpers para mostrar velocidad de métodos
const getSpeedLabel = (speed: string): string => {
  const labels: Record<string, string> = {
    instant: 'Instantáneo',
    fast: 'Rápido',
    medium: 'Medio',
    slow: 'Lento'
  }
  return labels[speed] || speed
}

const getSpeedSeverity = (speed: string): string => {
  const severities: Record<string, string> = {
    instant: 'success',
    fast: 'success',
    medium: 'warning',
    slow: 'danger'
  }
  return severities[speed] || 'info'
}

const changeDataLocation = () => {
  toast.add({
    severity: 'info',
    summary: 'Función en desarrollo',
    detail: 'Esta funcionalidad estará disponible próximamente',
    life: 3000
  })
}

const clearCache = async () => {
  try {
    const response = await fetch('http://localhost:8008/api/maintenance/clear-cache', {
      method: 'POST'
    })

    if (!response.ok) {
      throw new Error('Error al limpiar caché')
    }

    toast.add({
      severity: 'success',
      summary: 'Caché limpiado',
      detail: 'Los archivos temporales se han eliminado',
      life: 3000
    })
  } catch (error) {
    console.error('Error clearing cache:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo limpiar el caché',
      life: 3000
    })
  }
}

const confirmReset = () => {
  showResetDialog.value = true
}

const resetSettings = () => {
  settings.value = {
    theme: 'auto',
    fontSize: 'medium',
    lineHeight: '1.6',
    minConfidence: 70,
    autoAnalysis: true,
    showPartialResults: true,
    notifyAnalysisComplete: true,
    soundEnabled: true,
    enabledInferenceMethods: ['llama3.2'],
    inferenceMinConfidence: 50,
    inferenceMinConsensus: 60,
    prioritizeSpeed: true
  }
  saveSettings()
  themeStore.resetToDefaults()
  showResetDialog.value = false

  toast.add({
    severity: 'success',
    summary: 'Configuración restablecida',
    detail: 'Se ha restaurado la configuración por defecto',
    life: 3000
  })
}

const openDocumentation = () => {
  // En producción, esto abriría la documentación externa
  toast.add({
    severity: 'info',
    summary: 'Documentación',
    detail: 'Abriendo documentación...',
    life: 3000
  })
}

const openIssues = () => {
  // En producción, esto abriría el repositorio de issues
  toast.add({
    severity: 'info',
    summary: 'GitHub',
    detail: 'Abriendo página de issues...',
    life: 3000
  })
}

const goBack = () => {
  router.go(-1)
}

const scrollToSection = (sectionId: string) => {
  const element = document.getElementById(sectionId)
  if (element && contentArea.value) {
    // Calcular la posición del elemento relativa al contenedor de scroll
    const containerRect = contentArea.value.getBoundingClientRect()
    const elementRect = element.getBoundingClientRect()

    // Posición actual de scroll + diferencia entre elemento y contenedor
    const scrollTop = contentArea.value.scrollTop
    const elementRelativeTop = elementRect.top - containerRect.top + scrollTop

    // Offset para dejar espacio visual arriba (16px de margen)
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

  const sections = ['apariencia', 'analisis', 'ia-local', 'notificaciones', 'privacidad', 'mantenimiento', 'acerca-de']
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
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  flex-shrink: 0;
}

/* Dark mode para header */
:global(.dark) .settings-header {
  background: var(--p-surface-900);
  border-bottom-color: var(--p-surface-700);
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
  background: var(--p-surface-0);
  border-right: 1px solid var(--p-surface-200);
  overflow-y: auto;
  padding: 1.5rem 0;
}

/* Dark mode para sidebar */
:global(.dark) .settings-sidebar {
  background: var(--p-surface-900);
  border-right-color: var(--p-surface-700);
}

.nav-menu {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-menu li {
  margin: 0;
}

.nav-menu a {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  color: var(--p-text-color);
  text-decoration: none;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
  cursor: pointer;
  user-select: none;
}

.nav-menu a:hover {
  background: var(--p-surface-100);
  color: var(--p-primary-color);
}

.nav-menu a.active {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  color: var(--p-primary-color);
  border-left-color: var(--p-primary-color);
  font-weight: 600;
}

/* Dark mode para navegación */
:global(.dark) .nav-menu a:hover {
  background: var(--p-surface-800);
}

:global(.dark) .nav-menu a.active {
  background: color-mix(in srgb, var(--p-primary-color) 20%, transparent);
}

.nav-menu a i {
  font-size: 1.1rem;
  width: 1.5rem;
  text-align: center;
}

.nav-menu a span {
  font-size: 0.95rem;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  scroll-behavior: smooth;
}

.settings-content > :deep(*) {
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.settings-content > :deep(.p-card) {
  margin-bottom: 1.5rem;
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

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 0;
  border-bottom: 1px solid var(--p-surface-200);
}

:global(.dark) .setting-item {
  border-bottom-color: var(--p-surface-700);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  flex: 1;
  padding-right: 2rem;
}

.setting-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

.setting-description {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.setting-description code {
  background: var(--p-surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
}

:global(.dark) .setting-description code {
  background: var(--p-surface-800);
}

.setting-control {
  min-width: 200px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

/* Sliders necesitan ancho completo */
.setting-control :deep(.p-slider) {
  width: 100%;
}

.about-info {
  text-align: center;
}

.about-info h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-primary-color);
}

.about-info .version {
  margin: 0 0 1rem 0;
  color: var(--p-text-muted-color);
  font-weight: 500;
}

.about-info .description {
  margin: 0 0 1.5rem 0;
  color: var(--p-text-muted-color);
  line-height: 1.6;
}

.about-links {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

/* LLM / Inferencia section */
.setting-control.wide {
  min-width: 350px;
}

.method-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  gap: 1rem;
}

.method-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.method-name {
  font-weight: 500;
}

.method-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.method-badges {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.speed-badge {
  font-size: 0.7rem;
}

/* MultiSelect styling - estilos específicos del componente */
/* Los estilos globales del panel están en primevue-overrides.css */
.setting-control.wide :deep(.p-multiselect) {
  width: 100%;
}

/* Badges de velocidad - alineación vertical */
.method-badges :deep(.p-tag) {
  padding: 0.2rem 0.5rem;
  line-height: 1;
}

/* Message styling */
.info-message {
  margin-top: 1rem;
}

.info-message :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
  gap: 0.75rem;
}

.info-message .message-content {
  line-height: 1.5;
}

.info-message .message-content code {
  padding: 0.125rem 0.375rem;
  margin: 0 0.125rem;
  background: var(--p-surface-200);
  border-radius: 0.25rem;
  font-size: 0.85em;
}

:global(.dark) .info-message .message-content code {
  background: var(--p-surface-700);
}

.info-message .message-content a {
  color: var(--p-primary-color);
  text-decoration: underline;
}

/* ============================================================================
   Apariencia - Paleta de colores y presets
   ============================================================================ */

.color-palette {
  display: grid;
  grid-template-columns: repeat(6, 32px);
  gap: 0.5rem;
  justify-content: flex-end;
}

.color-swatch {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  padding: 0;
  outline: none;
}

.color-swatch:hover {
  transform: scale(1.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.color-swatch.active {
  border-color: var(--p-text-color);
  transform: scale(1.1);
  box-shadow: 0 0 0 2px var(--p-surface-0), 0 0 0 4px var(--p-text-color);
}

.color-swatch i {
  color: white;
  font-size: 0.75rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Preset options en dropdown */
.preset-option {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.preset-name {
  font-weight: 500;
}

.preset-desc {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Dark mode ajustes para color swatches */
.dark .color-swatch.active {
  box-shadow: 0 0 0 2px var(--p-surface-900), 0 0 0 4px var(--p-text-color);
}
</style>
