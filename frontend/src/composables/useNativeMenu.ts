/**
 * Composable para manejar eventos del menu nativo de Tauri
 */
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { logWarn } from '@/services/logger'

// Variable para guardar la función listen de Tauri
let tauriListen: ((event: string, handler: (event: { payload: string }) => void) => Promise<() => void>) | null = null

// Promise que resuelve cuando Tauri está listo
let tauriReadyPromise: Promise<void> | null = null

// Dynamic import for Tauri event API (to avoid errors when running in browser)
// Con timeout de 5s para evitar cuelgues indefinidos
const tauriReady = ref(false)
// Tauri 2.0 uses __TAURI_INTERNALS__ (not __TAURI__ unless withGlobalTauri=true)
const isTauriEnv = typeof window !== 'undefined' && ('__TAURI__' in window || '__TAURI_INTERNALS__' in window)
if (isTauriEnv) {
  const importWithTimeout = Promise.race([
    import('@tauri-apps/api/event').then(module => {
      tauriListen = module.listen as typeof tauriListen
      tauriReady.value = true
    }),
    new Promise<void>((_, reject) =>
      setTimeout(() => reject(new Error('Tauri event API import timeout (5s)')), 5000)
    ),
  ])
  tauriReadyPromise = importWithTimeout.catch(error => {
    logWarn('Menu', 'Failed to load Tauri event API', error)
  })
}

interface MenuEventHandlers {
  onNewProject?: () => void
  onOpenProject?: () => void
  onSaveProject?: () => void
  onOpenFile?: () => void
  onCloseProject?: () => void
  onImport?: () => void
  onExport?: () => void
  onUpdateManuscript?: () => void
  onSettings?: () => void
  onViewChange?: (view: string) => void
  onToggleInspector?: () => void
  onToggleSidebar?: () => void
  onRunAnalysis?: () => void
  onCheckUpdates?: () => void
  onTutorial?: () => void
  onKeyboardShortcuts?: () => void
  onAbout?: () => void
  onUserGuide?: () => void
  onManageData?: () => void
}

export function useNativeMenu(handlers: MenuEventHandlers = {}) {
  const router = useRouter()

  let unlisten: (() => void) | null = null

  /** Invoca handler o registra log cuando no está conectado */
  const invoke = (name: string, handler: (() => void) | undefined) => {
    if (handler) {
      handler()
    } else {
      logWarn('Menu', `No handler for '${name}' - event dropped`)
    }
  }

  const handleMenuEvent = async (eventId: string) => {
    switch (eventId) {
      // Archivo
      case 'new_project':
        if (handlers.onNewProject) {
          handlers.onNewProject()
        } else {
          router.push('/projects')
          // Esperar a que la vista se monte antes de disparar el evento
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

      case 'save_project':
        invoke('save_project', handlers.onSaveProject)
        break

      case 'open_file':
        invoke('open_file', handlers.onOpenFile)
        break

      case 'close_project':
        invoke('close_project', handlers.onCloseProject)
        break

      case 'import':
        invoke('import', handlers.onImport)
        break

      case 'export':
        invoke('export', handlers.onExport)
        break

      case 'update_manuscript':
        invoke('update_manuscript', handlers.onUpdateManuscript)
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
        invoke('view_chapters', handlers.onViewChange ? () => handlers.onViewChange!('chapters') : undefined)
        break

      case 'view_entities':
        invoke('view_entities', handlers.onViewChange ? () => handlers.onViewChange!('entities') : undefined)
        break

      case 'view_alerts':
        invoke('view_alerts', handlers.onViewChange ? () => handlers.onViewChange!('alerts') : undefined)
        break

      case 'view_relationships':
        invoke('view_relationships', handlers.onViewChange ? () => handlers.onViewChange!('relationships') : undefined)
        break

      case 'view_timeline':
        invoke('view_timeline', handlers.onViewChange ? () => handlers.onViewChange!('timeline') : undefined)
        break

      case 'view_style':
        invoke('view_style', handlers.onViewChange ? () => handlers.onViewChange!('style') : undefined)
        break

      case 'view_glossary':
        invoke('view_glossary', handlers.onViewChange ? () => handlers.onViewChange!('glossary') : undefined)
        break

      case 'view_summary':
        invoke('view_summary', handlers.onViewChange ? () => handlers.onViewChange!('summary') : undefined)
        break

      case 'toggle_inspector':
        invoke('toggle_inspector', handlers.onToggleInspector)
        break

      case 'toggle_sidebar':
        invoke('toggle_sidebar', handlers.onToggleSidebar)
        break

      case 'toggle_history':
        window.dispatchEvent(new CustomEvent('menubar:toggle-history'))
        break

      case 'toggle_theme':
        window.dispatchEvent(new CustomEvent('menubar:toggle-theme'))
        break

      case 'find':
        window.dispatchEvent(new CustomEvent('menubar:find'))
        break

      // Analisis
      case 'run_analysis':
        invoke('run_analysis', handlers.onRunAnalysis)
        break

      // Ayuda
      case 'tutorial':
        invoke('tutorial', handlers.onTutorial)
        break

      case 'keyboard_shortcuts':
        invoke('keyboard_shortcuts', handlers.onKeyboardShortcuts)
        break

      case 'about':
        invoke('about', handlers.onAbout)
        break

      case 'user_guide':
        invoke('user_guide', handlers.onUserGuide)
        break

      case 'manage_data':
        invoke('manage_data', handlers.onManageData)
        break

      case 'check_updates':
        invoke('check_updates', handlers.onCheckUpdates)
        break

      default:
        logWarn('Menu', 'Unknown event ID:', eventId)
        break
    }
  }

  onMounted(async () => {
    // Solo configurar listener si estamos en Tauri
    if (isTauriEnv && tauriReadyPromise) {
      try {
        // Esperar a que el import asíncrono termine (sin timeout artificial)
        await tauriReadyPromise

        if (tauriListen) {
          unlisten = await tauriListen('menu-event', (event) => {
            handleMenuEvent(event.payload)
          })
        } else {
          logWarn('Menu', 'Tauri listen function not available after import')
        }
      } catch (error) {
        logWarn('Menu', 'Failed to setup Tauri menu listener', error)
      }
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
