import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSystemStore = defineStore('system', () => {
  const backendConnected = ref(false)
  const backendVersion = ref('unknown')

  async function checkBackendStatus() {
    try {
      const response = await fetch('http://localhost:8008/api/health')
      if (response.ok) {
        const data = await response.json()
        backendConnected.value = data.status === 'ok'
        backendVersion.value = data.version || 'unknown'
      } else {
        backendConnected.value = false
      }
    } catch (error) {
      backendConnected.value = false
    }
  }

  // Check backend status on store creation
  checkBackendStatus()

  return {
    backendConnected,
    backendVersion,
    checkBackendStatus
  }
})
