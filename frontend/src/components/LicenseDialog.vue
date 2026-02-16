<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :closable="canClose"
    :draggable="false"
    :block-scroll="true"
    class="license-dialog"
    :header="dialogTitle"
    :style="{ width: '500px' }"
  >
    <!-- Estado: Sin licencia -->
    <div v-if="currentView === 'activate'" class="license-activate">
      <div class="license-icon">
        <i class="pi pi-lock"></i>
      </div>

      <p class="license-message">
        Introduce tu clave de licencia para activar Narrative Assistant.
      </p>

      <div class="license-form">
        <InputText
          v-model="licenseKey"
          placeholder="XXXX-XXXX-XXXX-XXXX"
          class="license-input"
          :disabled="licenseStore.loading"
          @keyup.enter="handleActivate"
        />

        <Message v-if="licenseStore.error" severity="error" :closable="false" class="error-message">
          {{ licenseStore.error }}
        </Message>

        <Button
          label="Activar licencia"
          icon="pi pi-check"
          :loading="licenseStore.loading"
          :disabled="!licenseKey.trim()"
          class="activate-button"
          @click="handleActivate"
        />
      </div>

      <Divider />

      <div class="license-footer-links">
        <a href="https://narrativeassistant.com/pricing" target="_blank" rel="noopener">
          <i class="pi pi-external-link"></i> Ver planes y precios
        </a>
        <a href="https://narrativeassistant.com/trial" target="_blank" rel="noopener">
          <i class="pi pi-gift"></i> Solicitar prueba gratuita
        </a>
      </div>
    </div>

    <!-- Estado: Licencia activa -->
    <div v-else-if="currentView === 'status'" class="license-status">
      <div class="status-header" :class="statusClass">
        <i :class="statusIcon"></i>
        <div class="status-text">
          <h3>{{ licenseStore.tierDisplayName }}</h3>
          <p>{{ statusMessage }}</p>
        </div>
      </div>

      <!-- Features -->
      <div class="license-features">
        <h4>Funcionalidades incluidas</h4>
        <div class="features-grid">
          <Tag
            v-for="feature in licenseStore.features"
            :key="feature"
            :value="featureNames[feature] || feature"
            severity="success"
          />
          <Tag
            v-for="feature in missingFeatures"
            :key="feature"
            :value="featureNames[feature] || feature"
            severity="secondary"
            class="feature-missing"
          />
        </div>
      </div>

      <!-- Cuotas -->
      <div class="license-quotas">
        <div class="quota-item">
          <span class="quota-label">Páginas este mes</span>
          <span class="quota-value">
            <template v-if="licenseStore.licenseInfo?.unlimited">
              Ilimitadas
            </template>
            <template v-else>
              {{ licenseStore.licenseInfo?.pages_used }} / {{ licenseStore.licenseInfo?.pages_max }}
            </template>
          </span>
        </div>

        <div class="quota-item">
          <span class="quota-label">Dispositivos</span>
          <span class="quota-value">
            {{ licenseStore.licenseInfo?.devices_used }} / {{ licenseStore.licenseInfo?.devices_max }}
          </span>
        </div>
      </div>

      <!-- Advertencia offline -->
      <Message v-if="licenseStore.isOffline" severity="warn" :closable="false" class="offline-warning">
        <div class="offline-content">
          <strong>Modo offline</strong>
          <p>
            Quedan {{ licenseStore.offlineDaysRemaining }} días para verificar tu licencia.
            Conéctate a internet para renovar.
          </p>
        </div>
      </Message>

      <!-- Trial -->
      <Message v-if="licenseStore.isTrial" severity="info" :closable="false">
        <div class="trial-content">
          <strong>Periodo de prueba</strong>
          <p>Tienes acceso completo durante 14 días.</p>
          <Button
            label="Comprar licencia"
            size="small"
            severity="info"
            @click="openPricing"
          />
        </div>
      </Message>

      <!-- Botones -->
      <div class="status-actions">
        <Button
          label="Gestionar dispositivos"
          icon="pi pi-desktop"
          text
          @click="currentView = 'devices'"
        />
        <Button
          label="Ver uso"
          icon="pi pi-chart-bar"
          text
          @click="showUsage"
        />
      </div>
    </div>

    <!-- Vista: Dispositivos -->
    <div v-else-if="currentView === 'devices'" class="license-devices">
      <Button
        icon="pi pi-arrow-left"
        text
        size="small"
        label="Volver"
        class="back-button"
        @click="currentView = 'status'"
      />

      <h4>Dispositivos registrados</h4>

      <div class="devices-list">
        <div
          v-for="device in licenseStore.devices"
          :key="device.fingerprint"
          class="device-item"
          :class="{ 'device-current': device.is_current }"
        >
          <div class="device-info">
            <i class="pi pi-desktop"></i>
            <div class="device-details">
              <span class="device-name">{{ device.name }}</span>
              <span class="device-status">
                <Tag
                  :value="device.is_current ? 'Este dispositivo' : device.status"
                  :severity="device.status === 'active' ? 'success' : 'secondary'"
                  size="small"
                />
              </span>
            </div>
          </div>

          <Button
            v-if="!device.is_current && device.status === 'active'"
            icon="pi pi-times"
            text
            severity="danger"
            size="small"
            @click="handleDeactivateDevice(device.fingerprint)"
          />
        </div>
      </div>

      <p v-if="licenseStore.devicesRemaining > 0" class="devices-hint">
        Puedes registrar {{ licenseStore.devicesRemaining }} dispositivo(s) más.
      </p>
      <p v-else class="devices-hint devices-full">
        Has alcanzado el límite de dispositivos. Desactiva uno para usar otro.
      </p>
    </div>

    <!-- Vista: Uso -->
    <div v-else-if="currentView === 'usage'" class="license-usage">
      <Button
        icon="pi pi-arrow-left"
        text
        size="small"
        label="Volver"
        class="back-button"
        @click="currentView = 'status'"
      />

      <h4>Uso del Periodo Actual</h4>

      <div v-if="licenseStore.usage" class="usage-details">
        <div class="usage-chart">
          <div class="usage-bar-container">
            <div
              class="usage-bar"
              :style="{ width: usagePercentage + '%' }"
              :class="{ 'usage-warning': usagePercentage > 80, 'usage-full': usagePercentage >= 100 }"
            ></div>
          </div>
          <div class="usage-labels">
            <span class="usage-used">{{ licenseStore.usage.pages_used }} páginas usadas</span>
            <span class="usage-limit">
              <template v-if="licenseStore.usage.unlimited">Ilimitado</template>
              <template v-else>{{ licenseStore.usage.pages_max }} límite</template>
            </span>
          </div>
        </div>

        <div v-if="!licenseStore.usage.unlimited" class="usage-remaining">
          <template v-if="licenseStore.usage.pages_remaining > 0">
            <i class="pi pi-check-circle success-icon"></i>
            <span>Te quedan <strong>{{ licenseStore.usage.pages_remaining }}</strong> páginas este periodo</span>
          </template>
          <template v-else>
            <i class="pi pi-exclamation-circle warning-icon"></i>
            <span>Has agotado tu cuota de páginas para este periodo</span>
          </template>
        </div>

        <div v-else class="usage-remaining">
          <i class="pi pi-infinity success-icon"></i>
          <span>Páginas ilimitadas con tu plan</span>
        </div>

        <div class="usage-note">
          <small>Nota: El reanálisis de un documento ya procesado no consume cuota adicional.</small>
        </div>
      </div>

      <div v-else class="usage-empty">
        <i class="pi pi-info-circle"></i>
        <p>No hay datos de uso disponibles</p>
      </div>
    </div>

    <!-- Footer -->
    <template v-if="currentView === 'status'" #footer>
      <div class="dialog-footer">
        <Button label="Cerrar" @click="close" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

import { useLicenseStore, type LicenseFeature } from '../stores/license'

interface Props {
  visible: boolean
  forceActivation?: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'activated'): void
}

const props = withDefaults(defineProps<Props>(), {
  forceActivation: false,
})
const emit = defineEmits<Emits>()

const licenseStore = useLicenseStore()

// Estado local
const licenseKey = ref('')
const currentView = ref<'activate' | 'status' | 'devices' | 'usage'>('activate')

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const canClose = computed(() => {
  return !props.forceActivation || licenseStore.isLicensed
})

const dialogTitle = computed(() => {
  switch (currentView.value) {
    case 'activate':
      return 'Activar Licencia'
    case 'devices':
      return 'Gestionar Dispositivos'
    case 'usage':
      return 'Uso del Periodo'
    default:
      return 'Tu Licencia'
  }
})

// Nombres de features para mostrar
const featureNames: Record<LicenseFeature, string> = {
  attribute_consistency: 'Consistencia de atributos',
  grammar_spelling: 'Gramática y ortografía',
  ner_coreference: 'Entidades y correferencias',
  name_variants: 'Variantes de nombres',
  character_profiling: 'Perfiles de personajes',
  network_analysis: 'Análisis de relaciones',
  anachronism_detection: 'Detección de anacronismos',
  ooc_detection: 'Detección fuera de carácter',
  classical_spanish: 'Español clásico',
  multi_model: 'Multi-modelo (votación)',
  full_reports: 'Informes completos',
}

const allFeatures: LicenseFeature[] = [
  'attribute_consistency',
  'grammar_spelling',
  'ner_coreference',
  'name_variants',
  'character_profiling',
  'network_analysis',
  'anachronism_detection',
  'ooc_detection',
  'classical_spanish',
  'multi_model',
  'full_reports',
]

const missingFeatures = computed(() => {
  return allFeatures.filter((f) => !licenseStore.features.includes(f))
})

const statusClass = computed(() => {
  if (!licenseStore.licenseInfo) return 'status-none'
  if (licenseStore.isOffline) return 'status-offline'
  if (licenseStore.isLicensed) return 'status-active'
  return 'status-expired'
})

const statusIcon = computed(() => {
  if (!licenseStore.licenseInfo) return 'pi pi-lock'
  if (licenseStore.isOffline) return 'pi pi-cloud-upload'
  if (licenseStore.isLicensed) return 'pi pi-check-circle'
  return 'pi pi-times-circle'
})

const statusMessage = computed(() => {
  if (!licenseStore.licenseInfo) return 'Sin licencia'
  if (licenseStore.isTrial) return 'Periodo de prueba'
  if (licenseStore.isOffline) return 'Modo offline'
  if (licenseStore.isLicensed) return 'Licencia activa'
  return 'Licencia expirada'
})

const usagePercentage = computed(() => {
  if (!licenseStore.usage || licenseStore.usage.unlimited) return 0
  if (licenseStore.usage.pages_max === 0) return 0
  return Math.min(100, (licenseStore.usage.pages_used / licenseStore.usage.pages_max) * 100)
})

// Determinar vista inicial
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      licenseStore.fetchLicenseStatus()
      if (licenseStore.isLicensed && !props.forceActivation) {
        currentView.value = 'status'
      } else {
        currentView.value = 'activate'
      }
    }
  },
  { immediate: true }
)

watch(
  () => licenseStore.isLicensed,
  (isLicensed) => {
    if (isLicensed && currentView.value === 'activate') {
      currentView.value = 'status'
    }
  }
)

async function handleActivate() {
  const key = licenseKey.value.trim()
  if (!key) return

  const success = await licenseStore.activateLicense(key)
  if (success) {
    emit('activated')
    currentView.value = 'status'
  }
}

async function handleDeactivateDevice(fingerprint: string) {
  await licenseStore.deactivateDevice(fingerprint)
}

async function showUsage() {
  await licenseStore.fetchUsage()
  currentView.value = 'usage'
}

function openPricing() {
  window.open('https://narrativeassistant.com/pricing', '_blank')
}

function close() {
  isVisible.value = false
}

onMounted(() => {
  if (props.visible && currentView.value === 'devices') {
    licenseStore.fetchDevices()
  }
})
</script>

<style scoped>
.license-dialog {
  max-width: 95vw;
}

/* Activar licencia */
.license-activate {
  text-align: center;
  padding: 1rem 0;
}

.license-icon {
  font-size: 3rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.license-message {
  color: var(--p-text-muted-color);
  margin-bottom: 1.5rem;
}

.license-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 320px;
  margin: 0 auto;
}

.license-input {
  text-align: center;
  font-family: monospace;
  font-size: 1.1rem;
  letter-spacing: 0.1em;
}

.activate-button {
  width: 100%;
}

.error-message {
  margin: 0;
}

.license-footer-links {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  font-size: 0.9rem;
}

.license-footer-links a {
  color: var(--p-primary-color);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.license-footer-links a:hover {
  text-decoration: underline;
}

/* Estado de licencia */
.license-status {
  padding: 0.5rem 0;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: var(--p-border-radius);
  margin-bottom: 1.5rem;
}

.status-header i {
  font-size: 2rem;
}

.status-header.status-active {
  background: color-mix(in srgb, var(--p-green-500) 15%, transparent);
}

.status-header.status-active i {
  color: var(--p-green-500);
}

.status-header.status-offline {
  background: color-mix(in srgb, var(--p-yellow-500) 15%, transparent);
}

.status-header.status-offline i {
  color: var(--p-yellow-500);
}

.status-header.status-expired {
  background: color-mix(in srgb, var(--p-red-500) 15%, transparent);
}

.status-header.status-expired i {
  color: var(--p-red-500);
}

.status-text h3 {
  margin: 0;
  font-size: 1.25rem;
}

.status-text p {
  margin: 0.25rem 0 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

/* Features */
.license-features {
  margin-bottom: 1.5rem;
}

.license-features h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
}

.features-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.feature-missing {
  opacity: 0.5;
  text-decoration: line-through;
}

/* Cuotas */
.license-quotas {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
  margin-bottom: 1rem;
}

:global(.dark) .license-quotas {
  background: var(--p-surface-800);
}

.quota-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quota-label {
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}

.quota-value {
  font-weight: 600;
}

/* Advertencias */
.offline-warning,
.trial-content {
  margin-bottom: 1rem;
}

.offline-content p,
.trial-content p {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
}

.trial-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

/* Acciones */
.status-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1rem;
}

/* Dispositivos */
.license-devices {
  padding: 0.5rem 0;
}

.back-button {
  margin-bottom: 1rem;
}

.license-devices h4 {
  margin: 0 0 1rem 0;
}

.devices-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.device-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) .device-item {
  background: var(--p-surface-800);
}

.device-item.device-current {
  border: 1px solid var(--p-primary-color);
}

.device-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.device-info i {
  font-size: 1.25rem;
  color: var(--p-text-muted-color);
}

.device-details {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-weight: 500;
}

.device-status {
  margin-top: 0.25rem;
}

.devices-hint {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  text-align: center;
}

.devices-hint.devices-full {
  color: var(--p-yellow-500);
}

/* Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

/* Vista de Uso */
.license-usage {
  padding: 0.5rem 0;
}

.license-usage h4 {
  margin: 0 0 1rem 0;
}

.usage-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.usage-chart {
  background: var(--p-surface-50);
  padding: 1rem;
  border-radius: var(--p-border-radius);
}

:global(.dark) .usage-chart {
  background: var(--p-surface-800);
}

.usage-bar-container {
  height: 12px;
  background: var(--p-surface-200);
  border-radius: var(--app-radius);
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.usage-bar {
  height: 100%;
  background: var(--p-green-500);
  border-radius: var(--app-radius);
  transition: width 0.3s ease;
}

.usage-bar.usage-warning {
  background: var(--p-yellow-500);
}

.usage-bar.usage-full {
  background: var(--p-red-500);
}

.usage-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.usage-remaining {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

:global(.dark) .usage-remaining {
  background: var(--p-surface-800);
}

.success-icon {
  color: var(--p-green-500);
  font-size: 1.25rem;
}

.warning-icon {
  color: var(--p-yellow-500);
  font-size: 1.25rem;
}

.usage-note {
  padding: 0.5rem;
  background: color-mix(in srgb, var(--p-blue-500) 10%, transparent);
  border-radius: var(--p-border-radius);
  text-align: center;
}

.usage-note small {
  color: var(--p-text-muted-color);
}

.usage-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
  gap: 0.5rem;
}

.usage-empty i {
  font-size: 2rem;
  opacity: 0.5;
}
</style>
