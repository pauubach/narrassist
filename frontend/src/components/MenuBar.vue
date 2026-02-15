<template>
  <nav class="menubar" role="menubar" aria-label="Menú principal">
    <div class="menubar-items">
      <button
        v-for="(menu, index) in menus"
        :id="`menu-trigger-${index}`"
        :key="menu.label"
        class="menubar-item"
        role="menuitem"
        :aria-haspopup="true"
        :aria-expanded="activeMenu === menu.label"
        :aria-controls="`menu-dropdown-${index}`"
        @click="toggleMenu(menu.label, index)"
        @mouseenter="hoveredMenu = menu.label"
        @keydown="handleMenuKeydown($event, menu.label, index)"
      >
        {{ menu.label }}
      </button>
    </div>

    <!-- Dropdown Menus -->
    <Transition name="dropdown">
      <div
        v-if="activeMenu"
        :id="`menu-dropdown-${activeMenuIndex}`"
        class="menu-dropdown"
        role="menu"
        :aria-labelledby="`menu-trigger-${activeMenuIndex}`"
        :style="{ left: menuPosition + 'px' }"
        @mouseleave="closeMenu"
        @keydown="handleDropdownKeydown"
      >
        <template v-for="(item, itemIndex) in activeMenuItems" :key="item.label">
          <div
            v-if="item.divider"
            class="menu-item divider"
            role="separator"
          ></div>
          <button
            v-else
            :ref="el => setItemRef(el, itemIndex)"
            class="menu-item"
            :class="{ disabled: item.disabled }"
            role="menuitem"
            :aria-disabled="item.disabled"
            :tabindex="focusedItemIndex === itemIndex ? 0 : -1"
            @click="!item.disabled && handleMenuAction(item)"
          >
            <i v-if="item.icon" :class="'pi pi-' + item.icon" class="menu-icon" aria-hidden="true"></i>
            <span class="menu-label">{{ item.label }}</span>
            <span v-if="item.shortcut" class="menu-shortcut" aria-label="Atajo de teclado">{{ item.shortcut }}</span>
          </button>
        </template>
      </div>
    </Transition>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const activeMenu = ref<string | null>(null)
const activeMenuIndex = ref<number>(0)
const hoveredMenu = ref<string | null>(null)
const menuPosition = ref(0)
const focusedItemIndex = ref<number>(0)
const itemRefs = ref<(HTMLElement | null)[]>([])

// Función para guardar referencias a los items del menú
const setItemRef = (el: Element | ComponentPublicInstance | null, index: number) => {
  if (el) {
    itemRefs.value[index] = el as HTMLElement
  }
}

// Importar tipo para refs
import type { ComponentPublicInstance } from 'vue'

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
    { label: 'Proyectos', action: 'viewProjects', icon: 'folder' }
  ]

  // Agregar pestañas del proyecto si estamos en un proyecto (Ctrl+1..8)
  if (isInProject.value) {
    viewItems.push(
      { label: 'Texto', action: 'viewText', icon: 'file-edit', shortcut: 'Ctrl+1' },
      { label: 'Entidades', action: 'viewEntities', icon: 'users', shortcut: 'Ctrl+2' },
      { label: 'Relaciones', action: 'viewRelations', icon: 'share-alt', shortcut: 'Ctrl+3' },
      { label: 'Revisión', action: 'viewAlerts', icon: 'exclamation-triangle', shortcut: 'Ctrl+4' },
      { label: 'Cronología', action: 'viewTimeline', icon: 'clock', shortcut: 'Ctrl+5' },
      { label: 'Escritura', action: 'viewStyle', icon: 'pencil', shortcut: 'Ctrl+6' },
      { label: 'Glosario', action: 'viewGlossary', icon: 'book', shortcut: 'Ctrl+7' },
      { label: 'Resumen', action: 'viewSummary', icon: 'chart-bar', shortcut: 'Ctrl+8' },
      { divider: true, label: '' },
      { label: 'Sidebar', action: 'toggleSidebar', icon: 'th-large', shortcut: 'Ctrl+B' },
      { label: 'Inspector', action: 'toggleInspector', icon: 'sliders-h', shortcut: 'Ctrl+Shift+I' },
      { label: 'Historial', action: 'toggleHistory', icon: 'history', shortcut: 'Ctrl+Shift+H' },
      { divider: true, label: '' },
      { label: 'Cambiar tema', action: 'toggleTheme', icon: 'palette', shortcut: 'Ctrl+Shift+D' }
    )
  }

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
        { label: 'Buscar', action: 'find', icon: 'search', shortcut: 'Ctrl+F' },
      ]
    },
    {
      label: 'Ver',
      items: viewItems
    },
    {
      label: 'Análisis',
      items: [
        { label: 'Ejecutar análisis', action: 'runAnalysis', icon: 'play', disabled: !isInProject.value },
      ]
    },
    {
      label: 'Ayuda',
      items: [
        { label: 'Tutorial de Bienvenida', action: 'tutorial', icon: 'compass' },
        { label: 'Atajos de Teclado', action: 'shortcuts', icon: 'hashtag', shortcut: 'F1' },
        { label: 'Documentación', action: 'docs', icon: 'book' },
        { divider: true, label: '' },
        { label: 'Gestionar datos...', action: 'manageData', icon: 'database' },
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

const toggleMenu = (label: string, index: number) => {
  if (activeMenu.value === label) {
    activeMenu.value = null
  } else {
    activeMenu.value = label
    activeMenuIndex.value = index
    focusedItemIndex.value = 0
    itemRefs.value = []
    // Calcular posición del dropdown
    const menubarItem = document.querySelector(`.menubar-item:nth-child(${index + 1})`)
    if (menubarItem) {
      menuPosition.value = (menubarItem as HTMLElement).offsetLeft
    }
    // Enfocar primer item después del render
    nextTick(() => {
      const firstItem = itemRefs.value.find(el => el !== null)
      firstItem?.focus()
    })
  }
}

const closeMenu = () => {
  activeMenu.value = null
  focusedItemIndex.value = 0
}

// Navegación por teclado en el menubar
const handleMenuKeydown = (event: KeyboardEvent, label: string, index: number) => {
  switch (event.key) {
    case 'Enter':
    case ' ':
    case 'ArrowDown':
      event.preventDefault()
      toggleMenu(label, index)
      break
    case 'ArrowRight':
      event.preventDefault()
      if (index < menus.value.length - 1) {
        const nextButton = document.getElementById(`menu-trigger-${index + 1}`)
        nextButton?.focus()
      }
      break
    case 'ArrowLeft':
      event.preventDefault()
      if (index > 0) {
        const prevButton = document.getElementById(`menu-trigger-${index - 1}`)
        prevButton?.focus()
      }
      break
  }
}

// Navegación por teclado en el dropdown
const handleDropdownKeydown = (event: KeyboardEvent) => {
  const items = activeMenuItems.value.filter(item => !item.divider)
  const currentIndex = focusedItemIndex.value

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      if (currentIndex < items.length - 1) {
        focusedItemIndex.value = currentIndex + 1
        nextTick(() => {
          itemRefs.value[focusedItemIndex.value]?.focus()
        })
      }
      break
    case 'ArrowUp':
      event.preventDefault()
      if (currentIndex > 0) {
        focusedItemIndex.value = currentIndex - 1
        nextTick(() => {
          itemRefs.value[focusedItemIndex.value]?.focus()
        })
      }
      break
    case 'Escape': {
      event.preventDefault()
      closeMenu()
      // Devolver foco al trigger del menú
      const trigger = document.getElementById(`menu-trigger-${activeMenuIndex.value}`)
      trigger?.focus()
      break
    }
    case 'Tab':
      closeMenu()
      break
    case 'Home':
      event.preventDefault()
      focusedItemIndex.value = 0
      nextTick(() => {
        itemRefs.value[0]?.focus()
      })
      break
    case 'End':
      event.preventDefault()
      focusedItemIndex.value = items.length - 1
      nextTick(() => {
        itemRefs.value[focusedItemIndex.value]?.focus()
      })
      break
  }
}

const handleMenuAction = (item: MenuItem) => {
  if (!item.action || item.divider) return

  closeMenu()

  switch (item.action) {
    case 'newProject':
      // Emit event to open new project dialog in ProjectsView
      router.push('/projects')
      nextTick(() => {
        window.dispatchEvent(new CustomEvent('menubar:new-project'))
      })
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
    case 'viewText':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'text' } }))
      }
      break
    case 'viewEntities':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'entities' } }))
      }
      break
    case 'viewRelations':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'relationships' } }))
      }
      break
    case 'viewAlerts':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'alerts' } }))
      }
      break
    case 'viewTimeline':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'timeline' } }))
      }
      break
    case 'viewStyle':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'style' } }))
      }
      break
    case 'viewGlossary':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'glossary' } }))
      }
      break
    case 'viewSummary':
      if (route.params.id) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'summary' } }))
      }
      break
    case 'toggleSidebar':
      window.dispatchEvent(new CustomEvent('menubar:toggle-sidebar'))
      break
    case 'toggleInspector':
      window.dispatchEvent(new CustomEvent('menubar:toggle-inspector'))
      break
    case 'toggleHistory':
      window.dispatchEvent(new CustomEvent('menubar:toggle-history'))
      break
    case 'toggleTheme':
      window.dispatchEvent(new CustomEvent('menubar:toggle-theme'))
      break
    case 'shortcuts':
      window.dispatchEvent(new CustomEvent('keyboard:show-help'))
      break
    case 'tutorial':
      window.dispatchEvent(new CustomEvent('menubar:tutorial'))
      break
    case 'about':
      window.dispatchEvent(new CustomEvent('menubar:about'))
      break
    case 'docs':
      // Abrir guía de usuario integrada
      window.dispatchEvent(new CustomEvent('menubar:user-guide'))
      break
    case 'manageData':
      window.dispatchEvent(new CustomEvent('menubar:manage-data'))
      break
    case 'runAnalysis':
      window.dispatchEvent(new CustomEvent('menubar:run-analysis'))
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
  z-index: var(--ds-z-dropdown);
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
  background: transparent;
  border: none;
  font-family: inherit;
  transition: background-color 0.1s ease;
}

.menubar-item:hover {
  background: var(--p-surface-100);
}

.menubar-item:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
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
  z-index: var(--ds-z-sticky);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  cursor: pointer;
  color: var(--p-text-color);
  background: transparent;
  border: none;
  width: 100%;
  text-align: left;
  font-family: inherit;
  transition: background-color 0.1s ease;
  min-height: 36px;
}

.menu-item:hover:not(.disabled):not(.divider) {
  background: var(--p-surface-100);
}

.menu-item:focus-visible {
  outline: none;
  background: var(--p-primary-100);
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

.dark .menu-item:focus-visible {
  background: var(--p-primary-900);
}

.dark .menu-item.divider {
  border-top-color: var(--p-surface-700);
}
</style>
