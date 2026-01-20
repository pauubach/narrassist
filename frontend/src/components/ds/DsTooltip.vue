<script setup lang="ts">
import { ref, nextTick, onBeforeUnmount } from 'vue'

/**
 * DsTooltip - Tooltip con posicionamiento inteligente.
 *
 * Uso:
 *   <DsTooltip content="Información adicional">
 *     <Button icon="pi pi-info-circle" />
 *   </DsTooltip>
 *
 *   <DsTooltip position="bottom">
 *     <template #content>
 *       <strong>Título</strong>
 *       <p>Descripción detallada</p>
 *     </template>
 *     <span>Hover me</span>
 *   </DsTooltip>
 */

export interface Props {
  /** Contenido del tooltip (texto simple) */
  content?: string
  /** Posición preferida */
  position?: 'top' | 'bottom' | 'left' | 'right'
  /** Delay antes de mostrar (ms) */
  showDelay?: number
  /** Delay antes de ocultar (ms) */
  hideDelay?: number
  /** Si está deshabilitado */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  position: 'top',
  showDelay: 200,
  hideDelay: 0,
  disabled: false
})

const isVisible = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const tooltipRef = ref<HTMLElement | null>(null)

let showTimeout: ReturnType<typeof setTimeout> | null = null
let hideTimeout: ReturnType<typeof setTimeout> | null = null

const tooltipStyle = ref<Record<string, string>>({})

function calculatePosition() {
  if (!triggerRef.value || !tooltipRef.value) return

  const trigger = triggerRef.value.getBoundingClientRect()
  const tooltip = tooltipRef.value.getBoundingClientRect()
  const spacing = 8

  let top = 0
  let left = 0

  switch (props.position) {
    case 'top':
      top = trigger.top - tooltip.height - spacing
      left = trigger.left + (trigger.width - tooltip.width) / 2
      break
    case 'bottom':
      top = trigger.bottom + spacing
      left = trigger.left + (trigger.width - tooltip.width) / 2
      break
    case 'left':
      top = trigger.top + (trigger.height - tooltip.height) / 2
      left = trigger.left - tooltip.width - spacing
      break
    case 'right':
      top = trigger.top + (trigger.height - tooltip.height) / 2
      left = trigger.right + spacing
      break
  }

  // Clamp to viewport
  const padding = 8
  top = Math.max(padding, Math.min(top, window.innerHeight - tooltip.height - padding))
  left = Math.max(padding, Math.min(left, window.innerWidth - tooltip.width - padding))

  tooltipStyle.value = {
    top: `${top}px`,
    left: `${left}px`
  }
}

function show() {
  if (props.disabled) return

  if (hideTimeout) {
    clearTimeout(hideTimeout)
    hideTimeout = null
  }

  showTimeout = setTimeout(() => {
    isVisible.value = true
    nextTick(calculatePosition)
  }, props.showDelay)
}

function hide() {
  if (showTimeout) {
    clearTimeout(showTimeout)
    showTimeout = null
  }

  hideTimeout = setTimeout(() => {
    isVisible.value = false
  }, props.hideDelay)
}

onBeforeUnmount(() => {
  if (showTimeout) clearTimeout(showTimeout)
  if (hideTimeout) clearTimeout(hideTimeout)
})
</script>

<template>
  <div class="ds-tooltip-wrapper">
    <div
      ref="triggerRef"
      class="ds-tooltip-trigger"
      @mouseenter="show"
      @mouseleave="hide"
      @focus="show"
      @blur="hide"
    >
      <slot />
    </div>

    <Teleport to="body">
      <Transition name="ds-tooltip">
        <div
          v-if="isVisible"
          ref="tooltipRef"
          class="ds-tooltip"
          :class="`ds-tooltip--${position}`"
          :style="tooltipStyle"
          role="tooltip"
        >
          <slot name="content">
            {{ content }}
          </slot>
          <div class="ds-tooltip__arrow" />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.ds-tooltip-wrapper {
  display: inline-block;
}

.ds-tooltip-trigger {
  display: inline-block;
}

.ds-tooltip {
  position: fixed;
  z-index: var(--ds-z-tooltip);
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-size-sm);
  /* WCAG: Fondo oscuro fijo con texto claro - garantiza 12:1 ratio */
  color: #f8fafc !important; /* gray-50 */
  background-color: #1e293b !important; /* gray-800 - fondo oscuro fijo */
  border-radius: var(--ds-radius-md);
  box-shadow: var(--ds-shadow-lg);
  max-width: 300px;
  word-wrap: break-word;
}

/* Arrow */
.ds-tooltip__arrow {
  position: absolute;
  width: 8px;
  height: 8px;
  background-color: #1e293b !important; /* mismo que tooltip */
  transform: rotate(45deg);
}

.ds-tooltip--top .ds-tooltip__arrow {
  bottom: -4px;
  left: 50%;
  margin-left: -4px;
}

.ds-tooltip--bottom .ds-tooltip__arrow {
  top: -4px;
  left: 50%;
  margin-left: -4px;
}

.ds-tooltip--left .ds-tooltip__arrow {
  right: -4px;
  top: 50%;
  margin-top: -4px;
}

.ds-tooltip--right .ds-tooltip__arrow {
  left: -4px;
  top: 50%;
  margin-top: -4px;
}

/* Transitions */
.ds-tooltip-enter-active,
.ds-tooltip-leave-active {
  transition: opacity var(--ds-transition-fast), transform var(--ds-transition-fast);
}

.ds-tooltip-enter-from,
.ds-tooltip-leave-to {
  opacity: 0;
}

.ds-tooltip--top.ds-tooltip-enter-from,
.ds-tooltip--top.ds-tooltip-leave-to {
  transform: translateY(4px);
}

.ds-tooltip--bottom.ds-tooltip-enter-from,
.ds-tooltip--bottom.ds-tooltip-leave-to {
  transform: translateY(-4px);
}

.ds-tooltip--left.ds-tooltip-enter-from,
.ds-tooltip--left.ds-tooltip-leave-to {
  transform: translateX(4px);
}

.ds-tooltip--right.ds-tooltip-enter-from,
.ds-tooltip--right.ds-tooltip-leave-to {
  transform: translateX(-4px);
}
</style>
