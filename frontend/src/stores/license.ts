/**
 * Store para gestion de licencias
 */
import { defineStore } from 'pinia'
import { api } from '@/services/apiClient'
import { ref, computed } from 'vue'

// Tipos de licencia
export type LicenseTier = 'freelance' | 'agencia' | 'editorial'
export type LicenseModule = 'CORE' | 'NARRATIVA' | 'VOZ_ESTILO' | 'AVANZADO'
export type LicenseStatus = 'no_license' | 'active' | 'expired' | 'grace_period' | 'suspended'

export interface LicenseInfo {
  status: LicenseStatus
  tier: LicenseTier | null
  modules: LicenseModule[]
  devices_used: number
  devices_max: number
  manuscripts_used: number
  manuscripts_max: number
  expires_at: string | null
  is_trial: boolean
  offline_days_remaining: number | null
}

export interface DeviceInfo {
  fingerprint: string
  name: string
  status: 'active' | 'inactive' | 'pending'
  last_seen: string | null
  is_current: boolean
}

export interface UsageInfo {
  period_start: string
  period_end: string
  manuscripts_used: number
  manuscripts_limit: number
  manuscripts_remaining: number
  unlimited: boolean
}



export const useLicenseStore = defineStore('license', () => {
  // Estado
  const loading = ref(false)
  const error = ref<string | null>(null)
  const licenseInfo = ref<LicenseInfo | null>(null)
  const devices = ref<DeviceInfo[]>([])
  const usage = ref<UsageInfo | null>(null)

  // Computados
  const isLicensed = computed(() => {
    return licenseInfo.value?.status === 'active' || licenseInfo.value?.status === 'grace_period'
  })

  const isTrial = computed(() => licenseInfo.value?.is_trial ?? false)

  const isOffline = computed(() => {
    return licenseInfo.value?.status === 'grace_period'
  })

  const offlineDaysRemaining = computed(() => {
    return licenseInfo.value?.offline_days_remaining ?? null
  })

  const tier = computed(() => licenseInfo.value?.tier ?? null)

  const tierDisplayName = computed(() => {
    const names: Record<LicenseTier, string> = {
      freelance: 'Freelance',
      agencia: 'Agencia',
      editorial: 'Editorial',
    }
    return tier.value ? names[tier.value] : 'Sin licencia'
  })

  const modules = computed(() => licenseInfo.value?.modules ?? [])

  const hasModule = (module: LicenseModule) => {
    return modules.value.includes(module)
  }

  const manuscriptsRemaining = computed(() => {
    if (!licenseInfo.value) return 0
    if (licenseInfo.value.manuscripts_max === -1) return -1 // Ilimitado
    return Math.max(0, licenseInfo.value.manuscripts_max - licenseInfo.value.manuscripts_used)
  })

  const devicesRemaining = computed(() => {
    if (!licenseInfo.value) return 0
    return Math.max(0, licenseInfo.value.devices_max - licenseInfo.value.devices_used)
  })

  // Acciones
  async function fetchLicenseStatus() {
    loading.value = true
    error.value = null

    try {
      licenseInfo.value = await api.get<LicenseInfo>('/api/license/status')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'No se pudo conectar con el servidor'
      console.error('Error fetching license status:', e)
    } finally {
      loading.value = false
    }
  }

  async function activateLicense(licenseKey: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.post('/api/license/activate', { license_key: licenseKey })
      await fetchLicenseStatus()
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error activando licencia'
      console.error('Error activating license:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  async function verifyLicense(): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const data = await api.post<{ valid: boolean; message?: string }>('/api/license/verify')
      if (data.valid) {
        await fetchLicenseStatus()
        return true
      }
      error.value = data.message || 'Verificación fallida'
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Verificación fallida'
      console.error('Error verifying license:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchDevices() {
    try {
      const data = await api.get<{ devices: DeviceInfo[] }>('/api/license/devices')
      devices.value = data.devices || []
    } catch (e) {
      console.error('Error fetching devices:', e)
    }
  }

  async function deactivateDevice(fingerprint: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.post('/api/license/devices/deactivate', { device_fingerprint: fingerprint })
      await fetchDevices()
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error desactivando dispositivo'
      console.error('Error deactivating device:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUsage() {
    try {
      usage.value = await api.get<UsageInfo>('/api/license/usage')
    } catch (e) {
      console.error('Error fetching usage:', e)
    }
  }

  async function checkModuleAccess(moduleName: LicenseModule): Promise<boolean> {
    try {
      const data = await api.get<{ has_access: boolean }>(`/api/license/check-module/${moduleName}`)
      return data.has_access === true
    } catch (e) {
      console.error('Error checking module access:', e)
      return false
    }
  }

  async function recordManuscriptUsage(projectId: number): Promise<boolean> {
    try {
      const data = await api.post<{ allowed: boolean }>('/api/license/record-manuscript', { project_id: projectId })
      if (data.allowed) {
        await fetchLicenseStatus()
        return true
      }
      error.value = 'Cuota de manuscritos excedida'
      return false
    } catch (e) {
      console.error('Error recording manuscript usage:', e)
      return true // Permitir en modo desarrollo si no hay conexion
    }
  }

  // Inicializacion
  fetchLicenseStatus()

  return {
    // Estado
    loading,
    error,
    licenseInfo,
    devices,
    usage,

    // Computados
    isLicensed,
    isTrial,
    isOffline,
    offlineDaysRemaining,
    tier,
    tierDisplayName,
    modules,
    manuscriptsRemaining,
    devicesRemaining,

    // Acciones
    fetchLicenseStatus,
    activateLicense,
    verifyLicense,
    fetchDevices,
    deactivateDevice,
    fetchUsage,
    checkModuleAccess,
    recordManuscriptUsage,
    hasModule,
  }
})
