<script setup lang="ts">
import { ref } from 'vue'

/**
 * PanelResizer - Control de redimensionado para paneles.
 *
 * Emite eventos de resize con el delta de movimiento.
 */

defineProps<{
  /** Posición del resizer */
  position: 'left' | 'right'
  /** Posición actual como porcentaje (0-100) para accesibilidad */
  currentPercent?: number
}>()

const emit = defineEmits<{
  resize: [delta: number]
}>()

const isDragging = ref(false)
const startX = ref(0)

function handleMouseDown(event: MouseEvent) {
  isDragging.value = true
  startX.value = event.clientX

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function handleMouseMove(event: MouseEvent) {
  if (!isDragging.value) return

  const delta = event.clientX - startX.value
  startX.value = event.clientX
  emit('resize', delta)
}

function handleMouseUp() {
  isDragging.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// Keyboard support
function handleKeyDown(event: KeyboardEvent) {
  const step = event.shiftKey ? 50 : 10

  switch (event.key) {
    case 'ArrowLeft':
      emit('resize', -step)
      event.preventDefault()
      break
    case 'ArrowRight':
      emit('resize', step)
      event.preventDefault()
      break
  }
}
</script>

<template>
  <div
    class="panel-resizer"
    :class="[
      `panel-resizer--${position}`,
      { 'panel-resizer--dragging': isDragging }
    ]"
    role="separator"
    aria-orientation="vertical"
    :aria-label="`Redimensionar panel ${position === 'left' ? 'izquierdo' : 'derecho'}`"
    :aria-valuenow="currentPercent ?? 50"
    aria-valuemin="0"
    aria-valuemax="100"
    tabindex="0"
    @mousedown="handleMouseDown"
    @keydown="handleKeyDown"
  >
    <div class="panel-resizer__handle" />
  </div>
</template>

<style scoped>
.panel-resizer {
  position: relative;
  width: 8px;
  cursor: col-resize;
  flex-shrink: 0;
  z-index: 10;
}

.panel-resizer::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  background-color: var(--ds-surface-border, var(--surface-border, rgba(0, 0, 0, 0.1)));
  transform: translateX(-50%);
  transition: background-color var(--ds-transition-fast, 0.15s), width var(--ds-transition-fast, 0.15s);
}

.panel-resizer:hover::before,
.panel-resizer--dragging::before {
  width: 3px;
  background-color: var(--ds-color-primary);
}

.panel-resizer:focus-visible {
  outline: none;
}

.panel-resizer:focus-visible::before {
  width: 3px;
  background-color: var(--ds-color-primary);
}

.panel-resizer__handle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 40px;
  background-color: var(--ds-surface-border, var(--surface-border, rgba(0, 0, 0, 0.1)));
  border-radius: var(--ds-radius-full, 9999px);
  opacity: 0;
  transition: opacity var(--ds-transition-fast, 0.15s);
}

.panel-resizer:hover .panel-resizer__handle,
.panel-resizer--dragging .panel-resizer__handle {
  opacity: 1;
  background-color: var(--ds-color-primary);
}

/* Área de agarre más grande */
.panel-resizer::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
}
</style>
