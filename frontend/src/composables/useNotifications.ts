/**
 * useNotifications - Composable para notificaciones del sistema y sonidos.
 *
 * Proporciona:
 * - Notificaciones del sistema (browser notifications)
 * - Sonidos para eventos
 * - Respeta las preferencias del usuario en Settings
 */

import { ref } from 'vue'

// Sonidos reales (.wav) importados como assets de Vite
import SUCCESS_SOUND from '@/assets/sounds/success.wav'
import ERROR_SOUND from '@/assets/sounds/error.wav'
import WARNING_SOUND from '@/assets/sounds/warning.wav'
import INFO_SOUND from '@/assets/sounds/info.wav'

export type NotificationSeverity = 'success' | 'error' | 'info' | 'warning'

export interface NotificationOptions {
  title: string
  body: string
  severity?: NotificationSeverity
  playSound?: boolean
  icon?: string
}

// Estado de permisos
const permissionGranted = ref(false)
const permissionDenied = ref(false)

// Cache de audio para evitar recrearlos
const audioCache: Record<string, HTMLAudioElement> = {}

/**
 * Obtiene las preferencias del usuario desde localStorage
 */
function getUserPreferences() {
  try {
    const settings = localStorage.getItem('narrative_assistant_settings')
    if (settings) {
      const parsed = JSON.parse(settings)
      return {
        notifyAnalysisComplete: parsed.notifyAnalysisComplete ?? true,
        soundEnabled: parsed.soundEnabled ?? true,
      }
    }
  } catch (e) {
    console.warn('Error reading user preferences:', e)
  }
  return {
    notifyAnalysisComplete: true,
    soundEnabled: true,
  }
}

/**
 * Reproduce un sonido
 */
function playSound(severity: NotificationSeverity = 'success'): void {
  const prefs = getUserPreferences()
  if (!prefs.soundEnabled) return

  const soundMap: Record<NotificationSeverity, string> = {
    success: SUCCESS_SOUND,
    error: ERROR_SOUND,
    warning: WARNING_SOUND,
    info: INFO_SOUND,
  }

  const soundData = soundMap[severity]

  try {
    // Usar cache si existe
    if (!audioCache[severity]) {
      audioCache[severity] = new Audio(soundData)
      audioCache[severity].volume = 0.5
    }

    // Reiniciar y reproducir
    const audio = audioCache[severity]
    audio.currentTime = 0
    audio.play().catch(() => {
      // Ignorar errores de autoplay bloqueado
    })
  } catch (e) {
    console.warn('Error playing sound:', e)
  }
}

/**
 * Solicita permisos de notificación
 */
async function requestPermission(): Promise<boolean> {
  if (!('Notification' in window)) {
    console.warn('Browser does not support notifications')
    return false
  }

  if (Notification.permission === 'granted') {
    permissionGranted.value = true
    return true
  }

  if (Notification.permission === 'denied') {
    permissionDenied.value = true
    return false
  }

  try {
    const permission = await Notification.requestPermission()
    permissionGranted.value = permission === 'granted'
    permissionDenied.value = permission === 'denied'
    return permissionGranted.value
  } catch (e) {
    console.warn('Error requesting notification permission:', e)
    return false
  }
}

/**
 * Muestra una notificación del sistema.
 *
 * Si la ventana tiene el foco, solo reproduce el sonido.
 * Si la ventana NO tiene el foco, muestra notificación nativa del OS + sonido.
 */
async function showNotification(options: NotificationOptions): Promise<void> {
  const prefs = getUserPreferences()

  // Reproducir sonido si está habilitado
  if (options.playSound !== false && prefs.soundEnabled) {
    playSound(options.severity || 'info')
  }

  // Si las notificaciones están deshabilitadas, solo reproducir sonido
  if (!prefs.notifyAnalysisComplete) {
    return
  }

  // Solo mostrar notificación nativa si la ventana NO tiene el foco
  // (si tiene el foco, el usuario ya ve los toasts in-app)
  if (document.hasFocus()) {
    return
  }

  // Verificar soporte
  if (!('Notification' in window)) {
    return
  }

  // Solicitar permiso si es necesario
  if (Notification.permission === 'default') {
    await requestPermission()
  }

  if (Notification.permission !== 'granted') {
    return
  }

  // Crear notificación nativa del OS
  try {
    const notification = new Notification(options.title, {
      body: options.body,
      icon: options.icon || '/favicon.ico',
      tag: 'narrative-assistant',
      requireInteraction: false,
      silent: true, // El sonido lo manejamos nosotros
    })

    // Cerrar automáticamente después de 5 segundos
    setTimeout(() => {
      notification.close()
    }, 5000)

    // Al hacer clic, enfocar la ventana
    notification.onclick = () => {
      window.focus()
      notification.close()
    }
  } catch (e) {
    console.warn('Error showing notification:', e)
  }
}

/**
 * Notificación de análisis completado
 */
function notifyAnalysisComplete(projectName?: string): void {
  showNotification({
    title: 'Análisis completado',
    body: projectName
      ? `El análisis de "${projectName}" ha finalizado.`
      : 'El análisis del documento ha finalizado.',
    severity: 'success',
    playSound: true,
  })
}

/**
 * Notificación de error en análisis
 */
function notifyAnalysisError(errorMessage?: string): void {
  showNotification({
    title: 'Error en el análisis',
    body: errorMessage || 'Ha ocurrido un error durante el análisis.',
    severity: 'error',
    playSound: true,
  })
}

export function useNotifications() {
  // Inicializar estado de permisos
  if ('Notification' in window) {
    permissionGranted.value = Notification.permission === 'granted'
    permissionDenied.value = Notification.permission === 'denied'
  }

  return {
    // Estado
    permissionGranted,
    permissionDenied,

    // Métodos
    requestPermission,
    showNotification,
    playSound,
    notifyAnalysisComplete,
    notifyAnalysisError,

    // Utilidades
    getUserPreferences,
  }
}
