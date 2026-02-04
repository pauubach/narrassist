<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Atajos de Teclado"
    :style="{ width: '700px' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="shortcuts-content">
      <p class="shortcuts-note">
        <i class="pi pi-info-circle"></i>
        Usa <kbd>F1</kbd> o <kbd>Ctrl/Cmd</kbd> + <kbd>/</kbd> para mostrar esta ayuda en cualquier momento
      </p>

      <div class="shortcuts-container">
        <div
          v-for="category in KEYBOARD_SHORTCUTS"
          :key="category.category"
          class="shortcuts-category"
        >
          <h3>{{ category.category }}</h3>
          <div class="shortcuts-list">
            <div
              v-for="(shortcut, index) in category.shortcuts"
              :key="index"
              class="shortcut-item"
            >
              <div class="shortcut-keys">
                <kbd v-for="(key, i) in shortcut.keys" :key="i" class="key">
                  {{ key }}
                </kbd>
              </div>
              <span class="shortcut-description">{{ shortcut.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { KEYBOARD_SHORTCUTS } from '@/composables/useKeyboardShortcuts'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const visible = ref(props.visible)

watch(
  () => props.visible,
  (newValue) => {
    visible.value = newValue
  }
)

watch(visible, (newValue) => {
  emit('update:visible', newValue)
})
</script>

<style scoped>
.shortcuts-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.shortcuts-note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.shortcuts-note i {
  color: var(--primary-color);
}

.shortcuts-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-height: 55vh;
  overflow-y: auto;
}

.shortcuts-category {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.shortcuts-category h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--primary-color);
  border-bottom: 2px solid var(--surface-border);
  padding-bottom: 0.5rem;
}

.shortcuts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.shortcut-item:hover {
  background-color: var(--surface-hover);
}

.shortcut-keys {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  min-width: 200px;
}

.key {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: var(--surface-100);
  border: 1px solid var(--surface-border);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  min-width: 40px;
  text-align: center;
}

.dark .key {
  background: var(--surface-200);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.shortcut-description {
  flex: 1;
  color: var(--text-color-secondary);
  font-size: 0.95rem;
}

/* Scrollbar personalizado */
.shortcuts-container::-webkit-scrollbar {
  width: 8px;
}

.shortcuts-container::-webkit-scrollbar-track {
  background: var(--surface-ground);
  border-radius: 4px;
}

.shortcuts-container::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 4px;
}

.shortcuts-container::-webkit-scrollbar-thumb:hover {
  background: var(--text-color-secondary);
}
</style>
