<template>
  <div id="app" class="app-container">
    <!-- Skip link para accesibilidad - permite saltar navegación -->
    <a href="#main-content" class="skip-link">
      Saltar al contenido principal
    </a>
    <MenuBar v-if="hasMenuBar" />
    <main
      id="main-content"
      :class="['app-content', { 'app-content--with-menubar': hasMenuBar }]"
      role="main"
      aria-label="Contenido principal"
    >
      <Toast position="top-right" aria-live="polite" />
      <div v-if="isBackendDown" class="backend-down-banner" role="alert">
        <i class="pi pi-exclamation-triangle"></i>
        <div class="backend-down-banner__text">
          <span class="backend-down-banner__title">Sin conexión con el servidor</span>
          <span v-if="numRecoveryAttempts < 6" class="backend-down-banner__hint">
            Reintentando automáticamente...
          </span>
          <span v-else class="backend-down-banner__hint">
            No se pudo restablecer la conexión. Cierra la aplicación y vuelve a abrirla.
          </span>
        </div>
      </div>
      <RouterView />
    </main>
    <KeyboardShortcutsDialog
      :visible="showShortcutsHelp"
      @update:visible="showShortcutsHelp = $event"
    />
    <AboutDialog
      :visible="showAbout"
      @update:visible="showAbout = $event"
    />
    <TutorialDialog
      :visible="showTutorial"
      @update:visible="onTutorialVisibilityChange"
      @complete="onTutorialComplete"
    />
    <UserGuideDialog
      :visible="showUserGuide"
      @update:visible="showUserGuide = $event"
    />
    <DataManagementDialog
      :visible="showManageData"
      @update:visible="showManageData = $event"
    />
    <ModelSetupDialog />
  </div>
</template>

<script setup lang="ts">
import { RouterView, useRouter, useRoute } from 'vue-router'
import { onMounted, onBeforeUnmount, onErrorCaptured, ref, watch, computed } from 'vue'
import Toast from 'primevue/toast'
import { backendDown, recoveryAttempts } from '@/services/apiClient'
import { useAppStore } from '@/stores/app'
import { useThemeStore } from '@/stores/theme'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useNativeMenu } from './composables/useNativeMenu'
import { useWorkspaceStore } from '@/stores/workspace'
import KeyboardShortcutsDialog from '@/components/KeyboardShortcutsDialog.vue'
import AboutDialog from '@/components/AboutDialog.vue'
import TutorialDialog from '@/components/TutorialDialog.vue'
import UserGuideDialog from '@/components/UserGuideDialog.vue'
import MenuBar from '@/components/MenuBar.vue'
import DataManagementDialog from '@/components/DataManagementDialog.vue'
import ModelSetupDialog from '@/components/ModelSetupDialog.vue'
import { useSystemStore } from '@/stores/system'
const router = useRouter()
const route = useRoute()
const appStore = useAppStore()
const systemStore = useSystemStore()
const themeStore = useThemeStore()
const workspaceStore = useWorkspaceStore()
const isBackendDown = backendDown
const numRecoveryAttempts = recoveryAttempts

// ── Global error boundary ───────────────────────────────────
onErrorCaptured((err, instance, info) => {
  console.error(`[ErrorBoundary] ${info}:`, err, instance?.$options?.name || instance?.$options?.__name)
  // Don't swallow the error — let Vue's default handler log it too
  return true
})

const showShortcutsHelp = ref(false)
const showAbout = ref(false)
const showTutorial = ref(false)
const showUserGuide = ref(false)
const showManageData = ref(false)

// Detect Tauri environment - check immediately and also on mount
// __TAURI__ is injected by Tauri's webview, check multiple ways
const isTauri = ref(
  typeof window !== 'undefined' && (
    '__TAURI__' in window ||
    '__TAURI_INTERNALS__' in window ||
    window.navigator.userAgent.includes('Tauri')
  )
)

// Hide web MenuBar when running in Tauri desktop app (which has native menu)
const hasMenuBar = computed(() => !isTauri.value)

// Activar atajos de teclado globales
useKeyboardShortcuts()

// Activar manejo de menú nativo de Tauri
useNativeMenu({
  onNewProject: () => {
    console.log('[Menu] New project requested')
    router.push('/projects')
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('menubar:new-project'))
    }, 200)
  },
  onOpenProject: () => {
    console.log('[Menu] Open project requested')
    router.push('/projects')
  },
  onSettings: () => { router.push('/settings') },
  onCloseProject: () => {
    console.log('[Menu] Close project requested')
    router.push('/projects')
  },
  onImport: () => {
    console.log('[Menu] Import requested — navigating to projects')
    router.push('/projects')
  },
  onExport: () => {
    console.log('[Menu] Export requested')
    window.dispatchEvent(new CustomEvent('menubar:export'))
  },
  onViewChange: (view: string) => {
    const tabMap: Record<string, string> = {
      chapters: 'text',
      entities: 'entities',
      alerts: 'alerts',
      relationships: 'relationships',
      timeline: 'timeline',
    }
    const tab = tabMap[view] || view
    workspaceStore.setActiveTab(tab as any)
  },
  onRunAnalysis: () => {
    console.log('[Menu] Run analysis requested')
    window.dispatchEvent(new CustomEvent('menubar:run-analysis'))
  },
  onToggleInspector: () => {
    console.log('[Menu] Toggle inspector')
    window.dispatchEvent(new CustomEvent('menubar:toggle-inspector'))
  },
  onToggleSidebar: () => {
    console.log('[Menu] Toggle sidebar')
    window.dispatchEvent(new CustomEvent('menubar:toggle-sidebar'))
  },
  onTutorial: () => { showTutorial.value = true },
  onKeyboardShortcuts: () => { showShortcutsHelp.value = true },
  onAbout: () => { showAbout.value = true },
  onUserGuide: () => { showUserGuide.value = true },
  onManageData: () => { showManageData.value = true },
})

// Verificar si se debe mostrar el tutorial al inicio
const checkTutorialStatus = () => {
  // Si el usuario marcó "no mostrar más", no mostrar
  const tutorialCompleted = localStorage.getItem('narrative_assistant_tutorial_completed')
  console.log('[Tutorial] tutorialCompleted:', tutorialCompleted)
  if (tutorialCompleted === 'true') {
    console.log('[Tutorial] No mostrar: usuario marcó "no mostrar más"')
    return false
  }

  // Si ya se mostró en esta sesión, no mostrar
  const shownThisSession = sessionStorage.getItem('narrative_assistant_tutorial_shown')
  console.log('[Tutorial] shownThisSession:', shownThisSession)
  if (shownThisSession === 'true') {
    console.log('[Tutorial] No mostrar: ya se mostró en esta sesión')
    return false
  }

  console.log('[Tutorial] Mostrando tutorial')
  return true
}

const onTutorialComplete = () => {
  console.log('[Tutorial] onTutorialComplete llamado')
  // Marcar como mostrado en esta sesión
  sessionStorage.setItem('narrative_assistant_tutorial_shown', 'true')
}

// También marcar como mostrado cuando se cierra el tutorial (de cualquier forma)
const onTutorialVisibilityChange = (visible: boolean) => {
  console.log('[Tutorial] onTutorialVisibilityChange:', visible)
  showTutorial.value = visible
  // Si se cierra el diálogo, marcar como mostrado en esta sesión
  if (!visible) {
    sessionStorage.setItem('narrative_assistant_tutorial_shown', 'true')
  }
}

// Función para mostrar el tutorial desde el menú
const openTutorial = () => {
  showTutorial.value = true
}

// Event listener references para cleanup
const onShowHelp = () => { showShortcutsHelp.value = true }
const onToggleTheme = () => { themeStore.toggleMode() }
const onMenuAbout = () => { showAbout.value = true }
const onMenuTutorial = () => { openTutorial() }
const onMenuUserGuide = () => { showUserGuide.value = true }
const onMenuManageData = () => { showManageData.value = true }
const onF1 = (e: KeyboardEvent) => {
  if (e.key === 'F1') {
    e.preventDefault()
    showUserGuide.value = true
  }
}

onMounted(() => {
  // Re-check Tauri in case it wasn't ready at component creation
  if (typeof window !== 'undefined') {
    isTauri.value = '__TAURI__' in window || '__TAURI_INTERNALS__' in window
  }

  const version = systemStore.backendVersion || 'loading...'
  console.log(`Narrative Assistant UI - v${version}`)
  console.log('Vue 3.5 + PrimeVue 4')
  console.log(`Tema: ${appStore.theme} | Modo oscuro: ${appStore.isDark}`)
  console.log(`Entorno Tauri: ${isTauri.value}`)
  console.log(`Ruta actual: ${route.fullPath}`)

  // Esperar a que los modelos estén listos antes de mostrar el tutorial
  const tryShowTutorial = () => {
    const shouldShowTutorial = checkTutorialStatus()
    console.log('[Tutorial] shouldShowTutorial:', shouldShowTutorial)
    console.log('[Tutorial] modelsReady:', systemStore.modelsReady)

    if (shouldShowTutorial && systemStore.modelsReady) {
      setTimeout(() => {
        console.log('[Tutorial] Activando showTutorial.value = true')
        showTutorial.value = true
      }, 1000)
    } else if (shouldShowTutorial && !systemStore.modelsReady) {
      console.log('[Tutorial] Esperando a que los modelos estén listos...')
      const unwatch = watch(() => systemStore.modelsReady, (ready: boolean) => {
        if (ready) {
          console.log('[Tutorial] Modelos listos! Mostrando tutorial')
          setTimeout(() => {
            showTutorial.value = true
          }, 1000)
          unwatch()
        }
      })
    }
  }

  tryShowTutorial()

  // Registrar event listeners (web MenuBar y atajos globales)
  window.addEventListener('keyboard:show-help', onShowHelp)
  window.addEventListener('keyboard:toggle-theme', onToggleTheme)
  window.addEventListener('menubar:about', onMenuAbout)
  window.addEventListener('menubar:tutorial', onMenuTutorial)
  window.addEventListener('menubar:user-guide', onMenuUserGuide)
  window.addEventListener('menubar:manage-data', onMenuManageData)
  window.addEventListener('keydown', onF1)
})

onBeforeUnmount(() => {
  window.removeEventListener('keyboard:show-help', onShowHelp)
  window.removeEventListener('keyboard:toggle-theme', onToggleTheme)
  window.removeEventListener('menubar:about', onMenuAbout)
  window.removeEventListener('menubar:tutorial', onMenuTutorial)
  window.removeEventListener('menubar:user-guide', onMenuUserGuide)
  window.removeEventListener('menubar:manage-data', onMenuManageData)
  window.removeEventListener('keydown', onF1)
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: var(--p-surface-ground);
  color: var(--p-text-color);
}

.app-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: var(--p-surface-ground);
}

.app-content--with-menubar {
  margin-top: 32px;
}

.backend-down-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  background-color: var(--p-red-50);
  color: var(--p-red-700);
  border-bottom: 2px solid var(--p-red-200);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.backend-down-banner > i {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.backend-down-banner__text {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.1rem;
}

.backend-down-banner__title {
  font-weight: 600;
}

.backend-down-banner__hint {
  font-size: 0.8rem;
  opacity: 0.85;
}

:global(.dark) .backend-down-banner {
  background-color: var(--p-red-900);
  color: var(--p-red-100);
  border-color: var(--p-red-700);
}

</style>
