<template>
  <div class="menubar">
    <div class="menubar-items">
      <div
        v-for="menu in menus"
        :key="menu.label"
        class="menubar-item"
        @click="toggleMenu(menu.label)"
        @mouseenter="hoveredMenu = menu.label"
      >
        {{ menu.label }}
      </div>
    </div>

    <!-- Dropdown Menus -->
    <Transition name="dropdown">
      <div
        v-if="activeMenu"
        class="menu-dropdown"
        :style="{ left: menuPosition + 'px' }"
        @mouseleave="closeMenu"
      >
        <div
          v-for="item in activeMenuItems"
          :key="item.label"
          class="menu-item"
          :class="{ disabled: item.disabled, divider: item.divider }"
          @click="!item.disabled && handleMenuAction(item)"
        >
          <i v-if="item.icon" :class="'pi pi-' + item.icon" class="menu-icon"></i>
          <span class="menu-label">{{ item.label }}</span>
          <span v-if="item.shortcut" class="menu-shortcut">{{ item.shortcut }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const route = useRoute()
const themeStore = useThemeStore()

const activeMenu = ref<string | null>(null)
const hoveredMenu = ref<string | null>(null)
const menuPosition = ref(0)

interface MenuItem {
  label: string
  action?: string
  icon?: string
  shortcut?: string
  disabled?: boolean
  divider?: boolean
}

interface Menu {
  label: string
  items: MenuItem[]
}

// Computed para detectar si estamos en un proyecto
const isInProject = computed(() => {
  return route.name === 'project' && route.params.id
})

const menus = computed<Menu[]>(() => {
  const viewItems: MenuItem[] = [
    { label: 'Proyectos', action: 'viewProjects', icon: 'folder', shortcut: 'Ctrl+P' }
  ]

  // Solo agregar Entidades y Alertas si estamos en un proyecto
  if (isInProject.value) {
    viewItems.push(
      { label: 'Entidades', action: 'viewEntities', icon: 'users', shortcut: 'Ctrl+E' },
      { label: 'Alertas', action: 'viewAlerts', icon: 'exclamation-triangle', shortcut: 'Ctrl+A' }
    )
  }

  viewItems.push(
    { divider: true, label: '' },
    { label: 'Alternar Tema', action: 'toggleTheme', icon: 'moon', shortcut: 'Ctrl+T' }
  )

  return [
    {
      label: 'Archivo',
      items: [
        { label: 'Nuevo Proyecto', action: 'newProject', icon: 'plus', shortcut: 'Ctrl+N' },
        { label: 'Abrir Proyecto', action: 'openProject', icon: 'folder-open', shortcut: 'Ctrl+O' },
        { label: 'Cerrar Proyecto', action: 'closeProject', icon: 'times', disabled: !isInProject.value },
        { divider: true, label: '' },
        { label: 'Exportar', action: 'export', icon: 'download', shortcut: 'Ctrl+E', disabled: !isInProject.value },
        { divider: true, label: '' },
        { label: 'Preferencias', action: 'settings', icon: 'cog', shortcut: 'Ctrl+,' },
        { divider: true, label: '' },
        { label: 'Salir', action: 'exit', icon: 'sign-out', shortcut: 'Ctrl+Q' },
      ]
    },
    {
      label: 'Edición',
      items: [
        { label: 'Deshacer', action: 'undo', icon: 'undo', shortcut: 'Ctrl+Z', disabled: true },
        { label: 'Rehacer', action: 'redo', icon: 'refresh', shortcut: 'Ctrl+Y', disabled: true },
        { divider: true, label: '' },
        { label: 'Buscar', action: 'find', icon: 'search', shortcut: 'Ctrl+F' },
        { label: 'Reemplazar', action: 'replace', icon: 'sync', shortcut: 'Ctrl+H' },
      ]
    },
    {
      label: 'Ver',
      items: viewItems
    },
    {
      label: 'Ayuda',
      items: [
        { label: 'Atajos de Teclado', action: 'shortcuts', icon: 'hashtag', shortcut: 'F1' },
        { label: 'Documentación', action: 'docs', icon: 'book' },
        { divider: true, label: '' },
        { label: 'Acerca de', action: 'about', icon: 'info-circle' },
      ]
    }
  ]
})

const activeMenuItems = computed(() => {
  const menu = menus.value.find(m => m.label === activeMenu.value)
  return menu ? menu.items : []
})

const toggleMenu = (label: string) => {
  if (activeMenu.value === label) {
    activeMenu.value = null
  } else {
    activeMenu.value = label
    // Calcular posición del dropdown
    const menubarItem = document.querySelector(`.menubar-item:nth-child(${menus.value.findIndex(m => m.label === label) + 1})`)
    if (menubarItem) {
      menuPosition.value = (menubarItem as HTMLElement).offsetLeft
    }
  }
}

const closeMenu = () => {
  activeMenu.value = null
}

const handleMenuAction = (item: MenuItem) => {
  if (!item.action || item.divider) return

  closeMenu()

  switch (item.action) {
    case 'newProject':
      router.push('/projects/new')
      break
    case 'openProject':
      router.push('/projects')
      break
    case 'export':
      // Trigger export dialog
      window.dispatchEvent(new CustomEvent('menubar:export'))
      break
    case 'settings':
      router.push('/settings')
      break
    case 'exit':
      // In Tauri, use window close
      break
    case 'find':
      window.dispatchEvent(new CustomEvent('menubar:find'))
      break
    case 'viewProjects':
      router.push('/projects')
      break
    case 'viewEntities':
      // Navigate to current project entities
      break
    case 'viewAlerts':
      // Navigate to current project alerts
      break
    case 'toggleTheme':
      themeStore.toggleMode()
      break
    case 'shortcuts':
      window.dispatchEvent(new CustomEvent('keyboard:show-help'))
      break
    case 'about':
      window.dispatchEvent(new CustomEvent('menubar:about'))
      break
  }
}
</script>

<style scoped>
/* PrimeVue 4 usa variables con prefijo --p- */
.menubar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 32px;
  background: var(--p-surface-0);
  border-bottom: 1px solid var(--p-surface-200);
  display: flex;
  align-items: center;
  padding: 0 0.5rem;
  z-index: 1000;
  user-select: none;
}

.menubar-items {
  display: flex;
  gap: 0.25rem;
}

.menubar-item {
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  border-radius: 4px;
  color: var(--p-text-color);
  transition: background-color 0.1s ease;
}

.menubar-item:hover {
  background: var(--p-surface-100);
}

.menu-dropdown {
  position: fixed;
  top: 32px;
  min-width: 220px;
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 0.25rem 0;
  z-index: 1001;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  cursor: pointer;
  color: var(--p-text-color);
  transition: background-color 0.1s ease;
  min-height: 36px;
}

.menu-item:hover:not(.disabled):not(.divider) {
  background: var(--p-surface-100);
}

.menu-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.menu-item.divider {
  height: 0;
  min-height: 0;
  border-top: 1px solid var(--p-surface-200);
  margin: 0.25rem 0;
  padding: 0;
  cursor: default;
  pointer-events: none;
}

.menu-icon {
  font-size: 0.875rem;
  opacity: 0.7;
  min-width: 16px;
}

.menu-label {
  flex: 1;
}

.menu-shortcut {
  font-size: 0.75rem;
  opacity: 0.6;
  font-family: monospace;
}

/* Animación del dropdown */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}

.dropdown-leave-to {
  opacity: 0;
}

/* Dark mode adjustments */
.dark .menubar {
  background: var(--p-surface-900);
  border-bottom-color: var(--p-surface-700);
}

.dark .menubar-item:hover {
  background: var(--p-surface-800);
}

.dark .menu-dropdown {
  background: var(--p-surface-900);
  border-color: var(--p-surface-700);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.dark .menu-item:hover:not(.disabled):not(.divider) {
  background: var(--p-surface-800);
}

.dark .menu-item.divider {
  border-top-color: var(--p-surface-700);
}
</style>
