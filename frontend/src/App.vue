<template>
  <div id="app" class="app-container">
    <!-- Skip link para accesibilidad - permite saltar navegación -->
    <a href="#main-content" class="skip-link">
      Saltar al contenido principal
    </a>
    <MenuBar />
    <main id="main-content" class="app-content" role="main" aria-label="Contenido principal">
      <Toast position="top-right" aria-live="polite" />
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
    <ModelSetupDialog />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted, ref, watch } from 'vue'
import Toast from 'primevue/toast'
import { useAppStore } from '@/stores/app'
import { useThemeStore } from '@/stores/theme'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import KeyboardShortcutsDialog from '@/components/KeyboardShortcutsDialog.vue'
import AboutDialog from '@/components/AboutDialog.vue'
import TutorialDialog from '@/components/TutorialDialog.vue'
import UserGuideDialog from '@/components/UserGuideDialog.vue'
import MenuBar from '@/components/MenuBar.vue'
import ModelSetupDialog from '@/components/ModelSetupDialog.vue'
import { useSystemStore } from '@/stores/system'

const appStore = useAppStore()
const systemStore = useSystemStore()
const themeStore = useThemeStore()
const showShortcutsHelp = ref(false)
const showAbout = ref(false)
const showTutorial = ref(false)
const showUserGuide = ref(false)

// Activar atajos de teclado globales
useKeyboardShortcuts()

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

onMounted(() => {
  console.log('Narrative Assistant UI - v0.4.0')
  console.log('Vue 3.5 + PrimeVue 4')
  console.log(`Tema: ${appStore.theme} | Modo oscuro: ${appStore.isDark}`)

  // Esperar a que los modelos estén listos antes de mostrar el tutorial
  const tryShowTutorial = () => {
    const shouldShowTutorial = checkTutorialStatus()
    console.log('[Tutorial] shouldShowTutorial:', shouldShowTutorial)
    console.log('[Tutorial] modelsReady:', systemStore.modelsReady)

    if (shouldShowTutorial && systemStore.modelsReady) {
      // Solo mostrar tutorial cuando los modelos estén completamente listos
      setTimeout(() => {
        console.log('[Tutorial] Activando showTutorial.value = true')
        showTutorial.value = true
        console.log('[Tutorial] showTutorial.value =', showTutorial.value)
      }, 1000)
    } else if (shouldShowTutorial && !systemStore.modelsReady) {
      // Si los modelos no están listos, esperar hasta que lo estén
      console.log('[Tutorial] Esperando a que los modelos estén listos...')
      const unwatch = watch(() => systemStore.modelsReady, (ready: boolean) => {
        if (ready) {
          console.log('[Tutorial] Modelos listos! Mostrando tutorial')
          setTimeout(() => {
            showTutorial.value = true
          }, 1000)
          unwatch() // Dejar de observar
        }
      })
    }
  }

  // Intentar mostrar tutorial
  tryShowTutorial()

  // Listeners para eventos de teclado
  window.addEventListener('keyboard:show-help', () => {
    showShortcutsHelp.value = true
  })

  window.addEventListener('keyboard:toggle-theme', () => {
    themeStore.toggleMode()
  })

  // Listener para mostrar diálogo "Acerca de"
  window.addEventListener('menubar:about', () => {
    showAbout.value = true
  })

  // Listener para mostrar tutorial desde menú
  window.addEventListener('menubar:tutorial', () => {
    openTutorial()
  })

  // Listener para mostrar guía de usuario
  window.addEventListener('menubar:user-guide', () => {
    showUserGuide.value = true
  })

  // Listener para F1 - abrir ayuda
  window.addEventListener('keydown', (e) => {
    if (e.key === 'F1') {
      e.preventDefault()
      showUserGuide.value = true
    }
  })
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
  margin-top: 32px; /* Height of MenuBar */
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: var(--p-surface-ground);
}
</style>
