<template>
  <div id="app" class="app-container">
    <MenuBar />
    <div class="app-content">
      <Toast position="top-right" />
      <RouterView />
    </div>
    <KeyboardShortcutsDialog
      :visible="showShortcutsHelp"
      @update:visible="showShortcutsHelp = $event"
    />
    <AboutDialog
      :visible="showAbout"
      @update:visible="showAbout = $event"
    />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted, ref } from 'vue'
import Toast from 'primevue/toast'
import { useAppStore } from '@/stores/app'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import KeyboardShortcutsDialog from '@/components/KeyboardShortcutsDialog.vue'
import AboutDialog from '@/components/AboutDialog.vue'
import MenuBar from '@/components/MenuBar.vue'

const appStore = useAppStore()
const showShortcutsHelp = ref(false)
const showAbout = ref(false)

// Activar atajos de teclado globales
useKeyboardShortcuts()

onMounted(() => {
  console.log('Narrative Assistant UI - v0.4.0')
  console.log('Vue 3.5 + PrimeVue 4')
  console.log(`Tema: ${appStore.theme} | Modo oscuro: ${appStore.isDark}`)

  // Listeners para eventos de teclado
  window.addEventListener('keyboard:show-help', () => {
    showShortcutsHelp.value = true
  })

  window.addEventListener('keyboard:toggle-theme', () => {
    appStore.toggleTheme()
  })

  // Listener para mostrar diálogo "Acerca de"
  window.addEventListener('menubar:about', () => {
    showAbout.value = true
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
