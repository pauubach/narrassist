/**
 * Composable para manejar eventos del menu nativo de Tauri
 */
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

// Variable para guardar la función listen de Tauri
let tauriListen: ((event: string, handler: (event: { payload: string }) => void) => Promise<() => void>) | null = null

// Dynamic import for Tauri event API (to avoid errors when running in browser)
const tauriReady = ref(false)
if (typeof window !== 'undefined' && '__TAURI__' in window) {
  import('@tauri-apps/api/event').then(module => {
    tauriListen = module.listen as typeof tauriListen
    tauriReady.value = true
    console.log('[Menu] Tauri event API loaded successfully')
  }).catch(error => {
    console.warn('[Menu] Failed to load Tauri event API:', error)
  })
}

interface MenuEventHandlers {
  onNewProject?: () => void
  onOpenProject?: () => void
  onCloseProject?: () => void
  onImport?: () => void
  onExport?: () => void
  onSettings?: () => void
  onViewChange?: (view: string) => void
  onToggleInspector?: () => void
  onToggleSidebar?: () => void
  onRunAnalysis?: () => void
  onPauseAnalysis?: () => void
  onTutorial?: () => void
  onKeyboardShortcuts?: () => void
  onAbout?: () => void
  onUserGuide?: () => void
}

export function useNativeMenu(handlers: MenuEventHandlers = {}) {
  const router = useRouter()

  let unlisten: (() => void) | null = null

  const handleMenuEvent = async (eventId: string) => {
    console.log('[Menu] Handling event:', eventId)

    switch (eventId) {
      // Archivo
      case 'new_project':
        if (handlers.onNewProject) {
          handlers.onNewProject()
        } else {
          // Navigate to projects and emit event to open dialog
          router.push('/projects')
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('menubar:new-project'))
          }, 100)
        }
        break

      case 'open_project':
        if (handlers.onOpenProject) {
          handlers.onOpenProject()
        } else {
          router.push('/projects')
        }
        break

      case 'close_project':
        handlers.onCloseProject?.()
        break

      case 'import':
        handlers.onImport?.()
        break

      case 'export':
        handlers.onExport?.()
        break

      case 'settings':
        if (handlers.onSettings) {
          handlers.onSettings()
        } else {
          router.push('/settings')
        }
        break

      // Ver
      case 'view_chapters':
        handlers.onViewChange?.('chapters')
        break

      case 'view_entities':
        handlers.onViewChange?.('entities')
        break

      case 'view_alerts':
        handlers.onViewChange?.('alerts')
        break

      case 'view_relationships':
        handlers.onViewChange?.('relationships')
        break

      case 'view_timeline':
        handlers.onViewChange?.('timeline')
        break

      case 'toggle_inspector':
        handlers.onToggleInspector?.()
        break

      case 'toggle_sidebar':
        handlers.onToggleSidebar?.()
        break

      // Analisis
      case 'run_analysis':
        handlers.onRunAnalysis?.()
        break

      case 'pause_analysis':
        handlers.onPauseAnalysis?.()
        break

      case 'analyze_structure':
      case 'analyze_entities':
      case 'analyze_consistency':
      case 'analyze_style':
        // Estos se manejan igual que run_analysis pero con fase especifica
        handlers.onRunAnalysis?.()
        break

      // Ayuda
      case 'tutorial':
        handlers.onTutorial?.()
        break

      case 'keyboard_shortcuts':
        handlers.onKeyboardShortcuts?.()
        break

      case 'about':
        handlers.onAbout?.()
        break

      case 'user_guide':
        handlers.onUserGuide?.()
        break

      case 'check_updates':
        // TODO: Implementar verificacion de actualizaciones
        console.log('[Menu] Check updates - not implemented yet')
        break

      default:
        console.log('[Menu] Unhandled event:', eventId)
        break
    }
  }

  onMounted(async () => {
    // Solo configurar listener si estamos en Tauri y la API está lista
    if (typeof window !== 'undefined' && '__TAURI__' in window) {
      // Esperar a que la API de Tauri esté lista (máximo 2 segundos)
      let attempts = 0
      const maxAttempts = 20

      const setupListener = async () => {
        if (tauriListen) {
          try {
            unlisten = await tauriListen('menu-event', (event) => {
              console.log('[Menu] Received menu event:', event.payload)
              handleMenuEvent(event.payload)
            })
            console.log('[Menu] Listener setup successfully')
          } catch (error) {
            console.warn('[Menu] Failed to setup Tauri menu listener:', error)
          }
        } else if (attempts < maxAttempts) {
          attempts++
          setTimeout(setupListener, 100)
        } else {
          console.warn('[Menu] Tauri event API not available after timeout')
        }
      }

      setupListener()
    }
  })

  onUnmounted(() => {
    if (unlisten) {
      unlisten()
    }
  })

  return {
    handleMenuEvent,
  }
}

export default useNativeMenu
