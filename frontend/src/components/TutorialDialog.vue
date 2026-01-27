<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :closable="true"
    :draggable="false"
    :blockScroll="true"
    class="tutorial-dialog"
    :showHeader="currentStep > 0"
    :header="stepTitles[currentStep]"
    :style="{ width: dialogWidth }"
  >
    <!-- Paso 0: Bienvenida -->
    <div v-if="currentStep === 0" class="welcome-step">
      <div class="welcome-hero">
        <i class="pi pi-book welcome-icon"></i>
        <h1>Bienvenido a Narrative Assistant</h1>
        <p class="welcome-subtitle">
          Tu asistente de corrección para detectar inconsistencias en cualquier tipo de manuscrito
        </p>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <i class="pi pi-microchip-ai"></i>
          <h3>IA Local</h3>
          <p>Análisis inteligente que corre 100% en tu ordenador</p>
        </div>
        <div class="feature-card">
          <i class="pi pi-users"></i>
          <h3>Entidades</h3>
          <p>Detecta personajes, lugares, objetos y conceptos clave</p>
        </div>
        <div class="feature-card">
          <i class="pi pi-exclamation-triangle"></i>
          <h3>Alertas</h3>
          <p>Identifica inconsistencias, errores y problemas de coherencia</p>
        </div>
        <div class="feature-card highlight-privacy">
          <i class="pi pi-shield"></i>
          <h3>Privacidad Total</h3>
          <p>Tu manuscrito <strong>nunca</strong> se sube a internet</p>
        </div>
      </div>
    </div>

    <!-- Paso 1: Cómo funciona -->
    <div v-else-if="currentStep === 1" class="howto-step">
      <div class="howto-content">
        <h2>Cómo usar Narrative Assistant</h2>
        <p class="howto-intro">En solo 3 pasos tendrás tu manuscrito analizado:</p>

        <div class="workflow-steps">
          <div class="workflow-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4><i class="pi pi-folder-plus"></i> Crear proyecto</h4>
              <p>
                Ve a <strong>Proyectos</strong> y haz clic en <strong>"Nuevo proyecto"</strong>.
                Sube tu manuscrito en formato DOCX, TXT, MD, PDF o EPUB.
              </p>
            </div>
          </div>

          <div class="workflow-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4><i class="pi pi-spin pi-cog"></i> Analizar</h4>
              <p>
                El análisis comienza automáticamente. Mientras procesa, puedes navegar
                el texto. Las entidades y alertas aparecerán progresivamente.
              </p>
            </div>
          </div>

          <div class="workflow-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4><i class="pi pi-search"></i> Revisar alertas</h4>
              <p>
                Explora las <strong>Alertas</strong> detectadas. Haz clic en cualquiera
                para ver el contexto en el texto y decidir si corregir.
              </p>
            </div>
          </div>
        </div>

        <div class="tip-box">
          <i class="pi pi-lightbulb"></i>
          <div>
            <strong>Consejo:</strong> Usa <kbd>Ctrl</kbd>+<kbd>K</kbd> para abrir
            la paleta de comandos y navegar rápidamente.
          </div>
        </div>
      </div>
    </div>

    <!-- Paso 2: Navegación del workspace -->
    <div v-else-if="currentStep === 2" class="workspace-step">
      <div class="workspace-content">
        <h2>Navegando el workspace</h2>

        <div class="workspace-diagram">
          <div class="workspace-panel left-panel">
            <div class="panel-header">
              <i class="pi pi-list"></i> Capítulos
            </div>
            <div class="panel-desc">
              Navega entre capítulos y secciones de tu manuscrito
            </div>
          </div>

          <div class="workspace-panel center-panel">
            <div class="panel-header">
              <i class="pi pi-file-edit"></i> Contenido
            </div>
            <div class="panel-tabs">
              <span class="tab active">Texto</span>
              <span class="tab">Entidades</span>
              <span class="tab">Relaciones</span>
              <span class="tab">Alertas</span>
              <span class="tab">Timeline</span>
              <span class="tab">Estilo</span>
              <span class="tab">Glosario</span>
              <span class="tab">Resumen</span>
            </div>
            <div class="panel-desc">
              Pestañas adaptadas al tipo de documento para explorar tu manuscrito
            </div>
          </div>

          <div class="workspace-panel right-panel">
            <div class="panel-header">
              <i class="pi pi-info-circle"></i> Inspector
            </div>
            <div class="panel-desc">
              Detalles del elemento seleccionado (entidad, alerta, sección)
            </div>
          </div>
        </div>

        <div class="interaction-hints">
          <div class="hint">
            <i class="pi pi-mouse"></i>
            <span><strong>Clic</strong> en una entidad para verla en el inspector</span>
          </div>
          <div class="hint">
            <i class="pi pi-arrows-alt"></i>
            <span><strong>Arrastra</strong> los bordes para redimensionar paneles</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Paso 3: Hardware detectado -->
    <div v-else-if="currentStep === 3" class="hardware-step">
      <div class="hardware-detection">
        <div v-if="loadingCapabilities" class="loading-state">
          <ProgressSpinner />
          <p>Detectando hardware...</p>
        </div>

        <div v-else-if="systemCapabilities" class="hardware-result">
          <div class="hardware-icon-container" :class="{ 'has-gpu': systemCapabilities.hardware.has_gpu }">
            <i :class="systemCapabilities.hardware.has_gpu ? 'pi pi-bolt' : 'pi pi-desktop'"></i>
          </div>

          <h2>{{ systemCapabilities.hardware.has_gpu ? 'GPU Detectada' : 'Modo CPU' }}</h2>

          <div v-if="systemCapabilities.hardware.gpu" class="gpu-info">
            <Tag :value="systemCapabilities.hardware.gpu.name" severity="success" />
            <p v-if="systemCapabilities.hardware.gpu.memory_gb" class="gpu-memory">
              {{ systemCapabilities.hardware.gpu.memory_gb.toFixed(1) }} GB de memoria
            </p>
          </div>

          <div v-else class="cpu-info">
            <Tag :value="systemCapabilities.hardware.cpu.name" severity="info" />
          </div>

          <Message
            :severity="systemCapabilities.hardware.has_gpu ? 'success' : 'info'"
            :closable="false"
            class="hardware-message"
          >
            <span v-if="systemCapabilities.hardware.has_gpu">
              Tu sistema tiene aceleración por GPU. Los análisis serán más rápidos.
            </span>
            <span v-else>
              El análisis funcionará correctamente en CPU.
            </span>
          </Message>

          <!-- Ollama status -->
          <div v-if="systemCapabilities.ollama" class="ollama-status">
            <h4>Modelos LLM (Ollama)</h4>
            <div v-if="systemCapabilities.ollama.available" class="ollama-available">
              <Tag value="Disponible" severity="success" />
              <p v-if="systemCapabilities.ollama.models.length > 0">
                {{ systemCapabilities.ollama.models.length }} modelo(s) instalado(s)
              </p>
              <p v-else class="no-models-hint">
                Instala modelos con: <code>ollama pull llama3.2</code>
              </p>
            </div>
            <div v-else class="ollama-unavailable">
              <Tag value="No disponible" severity="warning" />
              <p>Instala Ollama para análisis avanzado con IA</p>
            </div>
          </div>
        </div>

        <div v-else class="error-state">
          <i class="pi pi-exclamation-circle"></i>
          <p>No se pudo detectar el hardware. El análisis funcionará en modo básico.</p>
        </div>
      </div>
    </div>

    <!-- Paso 4: Configuración aplicada -->
    <div v-else-if="currentStep === 4" class="config-step">
      <div class="config-summary">
        <div class="config-icon">
          <i class="pi pi-check-circle"></i>
        </div>

        <h2>Todo listo</h2>

        <div class="enabled-methods">
          <h4>Métodos de análisis habilitados:</h4>
          <div class="methods-list">
            <Tag
              v-for="method in enabledMethodsList"
              :key="method"
              :value="method"
              class="method-tag"
            />
          </div>
        </div>

        <Message severity="info" :closable="false" class="config-message">
          <div class="config-tips">
            <p>
              <i class="pi pi-cog"></i>
              Personaliza los métodos en <strong>Configuración > Métodos NLP</strong>
            </p>
            <p>
              <i class="pi pi-question-circle"></i>
              Accede a este tutorial en <strong>Ayuda > Tutorial de Bienvenida</strong>
            </p>
          </div>
        </Message>
      </div>
    </div>

    <!-- Footer con navegación -->
    <template #footer>
      <div class="tutorial-footer">
        <div class="dont-show-again" v-if="currentStep === 0">
          <Checkbox v-model="dontShowAgain" inputId="dontShowAgain" binary />
          <label for="dontShowAgain">No mostrar de nuevo</label>
        </div>
        <div v-else class="step-indicator">
          <span v-for="n in totalSteps" :key="n" class="step-dot" :class="{ active: n - 1 === currentStep }"></span>
        </div>

        <div class="nav-buttons">
          <Button
            v-if="currentStep > 0"
            label="Anterior"
            severity="secondary"
            text
            @click="prevStep"
          />
          <Button
            v-if="currentStep < totalSteps - 1"
            :label="currentStep === 0 ? 'Comenzar' : 'Siguiente'"
            @click="nextStep"
          />
          <Button
            v-else
            label="Empezar a usar"
            icon="pi pi-arrow-right"
            iconPos="right"
            @click="finish"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Checkbox from 'primevue/checkbox'
import ProgressSpinner from 'primevue/progressspinner'

interface NLPMethod {
  name: string
  description: string
  weight?: number
  available: boolean
  default_enabled: boolean
  requires_gpu: boolean
  recommended_gpu: boolean
}

interface SystemCapabilities {
  hardware: {
    gpu: { type: string; name: string; memory_gb: number | null; device_id: number } | null
    gpu_type: string
    has_gpu: boolean
    has_high_vram: boolean
    has_cupy: boolean
    cpu: { name: string }
  }
  ollama: {
    available: boolean
    models: Array<{ name: string; size: number; modified: string }>
    recommended_models: string[]
  }
  nlp_methods: {
    coreference: Record<string, NLPMethod>
    ner: Record<string, NLPMethod>
    grammar: Record<string, NLPMethod>
  }
  recommended_config: {
    device_preference: string
    spacy_gpu_enabled: boolean
    embeddings_gpu_enabled: boolean
    batch_size: number
  }
}

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'complete'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// Estado del wizard
const currentStep = ref(0)
const totalSteps = 5
const dontShowAgain = ref(false)

// Estado de capacidades
const systemCapabilities = ref<SystemCapabilities | null>(null)
const loadingCapabilities = ref(false)

// Títulos de pasos
const stepTitles = ['', 'Cómo funciona', 'El Workspace', 'Tu Sistema', 'Listo']

// Ancho del diálogo según paso
const dialogWidth = computed(() => {
  if (currentStep.value === 0) return '650px'
  if (currentStep.value === 2) return '700px' // Workspace diagram needs more space
  return '550px'
})

// Lista de métodos habilitados para mostrar
const enabledMethodsList = computed(() => {
  if (!systemCapabilities.value) return []

  const methods: string[] = []
  const nlp = systemCapabilities.value.nlp_methods

  for (const [, method] of Object.entries(nlp.coreference)) {
    if (method.available && method.default_enabled) {
      methods.push(method.name)
    }
  }
  for (const [, method] of Object.entries(nlp.ner)) {
    if (method.available && method.default_enabled) {
      methods.push(method.name)
    }
  }
  for (const [, method] of Object.entries(nlp.grammar)) {
    if (method.available && method.default_enabled) {
      methods.push(method.name)
    }
  }

  return methods
})

// Cargar capacidades cuando se abre el diálogo
watch(() => props.visible, async (newValue) => {
  if (newValue) {
    currentStep.value = 0
    await loadCapabilities()
  }
})

onMounted(async () => {
  if (props.visible) {
    await loadCapabilities()
  }
})

const loadCapabilities = async () => {
  loadingCapabilities.value = true
  try {
    const response = await fetch('http://localhost:8008/api/system/capabilities')
    if (response.ok) {
      const result = await response.json()
      if (result.success && result.data) {
        systemCapabilities.value = result.data
      }
    }
  } catch (error) {
    console.error('Error loading system capabilities:', error)
  } finally {
    loadingCapabilities.value = false
  }
}

const nextStep = async () => {
  if (currentStep.value === 0 && !systemCapabilities.value) {
    await loadCapabilities()
  }

  if (currentStep.value === 3) {
    // Aplicar configuración recomendada al pasar del paso de hardware
    applyRecommendedConfig()
  }

  currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const applyRecommendedConfig = () => {
  if (!systemCapabilities.value) return

  const methods = systemCapabilities.value.nlp_methods
  const enabledMethods = {
    coreference: [] as string[],
    ner: [] as string[],
    grammar: [] as string[]
  }

  for (const [key, method] of Object.entries(methods.coreference)) {
    if (method.available && method.default_enabled) {
      enabledMethods.coreference.push(key)
    }
  }
  for (const [key, method] of Object.entries(methods.ner)) {
    if (method.available && method.default_enabled) {
      enabledMethods.ner.push(key)
    }
  }
  for (const [key, method] of Object.entries(methods.grammar)) {
    if (method.available && method.default_enabled) {
      enabledMethods.grammar.push(key)
    }
  }

  // Guardar en localStorage
  const existingSettings = localStorage.getItem('narrative_assistant_settings')
  let settings = {}
  if (existingSettings) {
    try {
      settings = JSON.parse(existingSettings)
    } catch {
      // Ignorar errores de parsing
    }
  }

  const updatedSettings = {
    ...settings,
    enabledNLPMethods: enabledMethods
  }

  localStorage.setItem('narrative_assistant_settings', JSON.stringify(updatedSettings))
  window.dispatchEvent(new CustomEvent('settings-changed', { detail: updatedSettings }))
}

const finish = () => {
  // Guardar preferencia de no mostrar más
  if (dontShowAgain.value) {
    localStorage.setItem('narrative_assistant_tutorial_completed', 'true')
  }

  // Marcar como completado para esta sesión
  localStorage.setItem('narrative_assistant_tutorial_shown_session', 'true')

  emit('complete')
  isVisible.value = false
}
</script>

<style scoped>
.tutorial-dialog {
  max-width: 95vw;
}

/* Paso de bienvenida */
.welcome-step {
  text-align: center;
  padding: 1rem;
}

.welcome-hero {
  margin-bottom: 2rem;
}

.welcome-icon {
  font-size: 4rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.welcome-hero h1 {
  font-size: 1.75rem;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.welcome-subtitle {
  color: var(--p-text-muted-color);
  font-size: 1rem;
  margin: 0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.feature-card {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  padding: 1.25rem 1rem;
  text-align: center;
}

:global(.dark) .feature-card {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

.feature-card.highlight-privacy {
  background: var(--p-surface-50);
  border: 2px solid var(--green-400);
}

.feature-card.highlight-privacy i {
  color: var(--green-500);
}

:global(.dark) .feature-card.highlight-privacy {
  background: var(--p-surface-800);
  border-color: var(--green-500);
}

:global(.dark) .feature-card.highlight-privacy i {
  color: var(--green-400);
}

.feature-card i {
  font-size: 1.5rem;
  color: var(--p-primary-color);
  margin-bottom: 0.5rem;
}

.feature-card h3 {
  font-size: 1rem;
  margin: 0 0 0.25rem 0;
  font-weight: 600;
}

.feature-card p {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  margin: 0;
  line-height: 1.4;
}

/* Paso de cómo funciona */
.howto-step {
  padding: 1rem;
}

.howto-content h2 {
  text-align: center;
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
}

.howto-intro {
  text-align: center;
  color: var(--p-text-muted-color);
  margin: 0 0 1.5rem 0;
}

.workflow-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.workflow-step {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-content h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.step-content h4 i {
  color: var(--p-primary-color);
}

.step-content p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}

.tip-box {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  border-radius: var(--p-border-radius);
  border-left: 3px solid var(--p-primary-color);
}

.tip-box i {
  color: var(--p-primary-color);
  font-size: 1.25rem;
  flex-shrink: 0;
}

.tip-box kbd {
  display: inline-block;
  padding: 0.125rem 0.375rem;
  font-size: 0.8rem;
  font-family: monospace;
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  box-shadow: 0 1px 0 var(--p-surface-300);
}

:global(.dark) .tip-box kbd {
  background: var(--p-surface-700);
  border-color: var(--p-surface-600);
  box-shadow: 0 1px 0 var(--p-surface-600);
}

/* Paso del workspace */
.workspace-step {
  padding: 1rem;
}

.workspace-content h2 {
  text-align: center;
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
}

.workspace-diagram {
  display: grid;
  grid-template-columns: 120px 1fr 120px;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.workspace-panel {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius);
  padding: 0.75rem;
  min-height: 120px;
}

:global(.dark) .workspace-panel {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  color: var(--p-primary-color);
}

.panel-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.panel-tabs .tab {
  font-size: 0.7rem;
  padding: 0.125rem 0.375rem;
  background: var(--p-surface-100);
  border-radius: 3px;
  color: var(--p-text-muted-color);
}

:global(.dark) .panel-tabs .tab {
  background: var(--p-surface-700);
}

.panel-tabs .tab.active {
  background: var(--p-primary-color);
  color: white;
}

.panel-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  line-height: 1.3;
}

.center-panel {
  border-color: var(--p-primary-color);
  border-width: 2px;
}

.interaction-hints {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
}

.hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.hint i {
  color: var(--p-primary-color);
}

/* Paso de hardware */
.hardware-step {
  padding: 1rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.hardware-result {
  text-align: center;
}

.hardware-icon-container {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  background: var(--p-surface-100);
}

:global(.dark) .hardware-icon-container {
  background: var(--p-surface-700);
}

.hardware-icon-container.has-gpu {
  background: color-mix(in srgb, var(--p-green-500) 15%, transparent);
}

.hardware-icon-container i {
  font-size: 2.5rem;
  color: var(--p-text-muted-color);
}

.hardware-icon-container.has-gpu i {
  color: var(--p-green-500);
}

.hardware-result h2 {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
}

.gpu-info,
.cpu-info {
  margin-bottom: 1rem;
}

.gpu-memory {
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.hardware-message {
  margin: 1rem 0;
}

.ollama-status {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--p-surface-200);
  text-align: left;
}

:global(.dark) .ollama-status {
  border-top-color: var(--p-surface-700);
}

.ollama-status h4 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.ollama-available,
.ollama-unavailable {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ollama-status p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.no-models-hint code {
  background: var(--p-surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: var(--p-border-radius);
  font-size: 0.85rem;
}

:global(.dark) .no-models-hint code {
  background: var(--p-surface-700);
}

.error-state {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
}

.error-state i {
  font-size: 3rem;
  color: var(--p-yellow-500);
  margin-bottom: 1rem;
}

/* Paso de configuración */
.config-step {
  padding: 1rem;
}

.config-summary {
  text-align: center;
}

.config-icon {
  margin-bottom: 1rem;
}

.config-icon i {
  font-size: 4rem;
  color: var(--p-green-500);
}

.config-summary h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
}

.enabled-methods h4 {
  font-size: 1rem;
  margin: 0 0 0.75rem 0;
  font-weight: 600;
  text-align: left;
}

.methods-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.method-tag {
  font-size: 0.8rem;
  background: var(--p-surface-100) !important;
  color: var(--p-text-color) !important;
  border: 1px solid var(--p-surface-300) !important;
}

:global(.dark) .method-tag {
  background: var(--p-surface-700) !important;
  color: var(--p-text-color) !important;
  border-color: var(--p-surface-500) !important;
}

.config-message {
  text-align: left;
}

.config-tips {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-tips p {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.config-tips i {
  color: var(--p-primary-color);
  width: 1rem;
}

/* Footer */
.tutorial-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dont-show-again {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.step-indicator {
  display: flex;
  gap: 0.5rem;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--p-surface-300);
  transition: background 0.2s ease;
}

:global(.dark) .step-dot {
  background: var(--p-surface-600);
}

.step-dot.active {
  background: var(--p-primary-color);
}

.nav-buttons {
  display: flex;
  gap: 0.5rem;
}

/* Responsive */
@media (max-width: 600px) {
  .features-grid {
    grid-template-columns: 1fr;
  }

  .workspace-diagram {
    grid-template-columns: 1fr;
  }

  .interaction-hints {
    flex-direction: column;
    align-items: center;
  }
}
</style>
