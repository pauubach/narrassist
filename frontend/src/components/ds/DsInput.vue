<script setup lang="ts">
import { ref, computed } from 'vue'

/**
 * DsInput - Input con iconos, validación y estados.
 *
 * Uso:
 *   <DsInput v-model="search" placeholder="Buscar..." icon="pi pi-search" />
 *   <DsInput v-model="email" type="email" :error="emailError" />
 */

export interface Props {
  /** Valor del input (v-model) */
  modelValue?: string
  /** Tipo de input */
  type?: 'text' | 'email' | 'password' | 'number' | 'search' | 'url'
  /** Placeholder */
  placeholder?: string
  /** Icono izquierdo (clase PrimeIcons) */
  icon?: string
  /** Icono derecho (clase PrimeIcons) */
  iconRight?: string
  /** Mensaje de error */
  error?: string
  /** Mensaje de ayuda */
  help?: string
  /** Si está deshabilitado */
  disabled?: boolean
  /** Si es de solo lectura */
  readonly?: boolean
  /** Tamaño */
  size?: 'sm' | 'md' | 'lg'
  /** Si permite limpiar con botón X */
  clearable?: boolean
  /** Label del input */
  label?: string
  /** Si el campo es requerido */
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  type: 'text',
  size: 'md',
  clearable: false,
  disabled: false,
  readonly: false,
  required: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'focus': [event: FocusEvent]
  'blur': [event: FocusEvent]
  'clear': []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const isFocused = ref(false)

const inputId = computed(() => `ds-input-${Math.random().toString(36).substr(2, 9)}`)

const wrapperClasses = computed(() => {
  const base = ['ds-input-wrapper', `ds-input-wrapper--${props.size}`]

  if (isFocused.value) base.push('ds-input-wrapper--focused')
  if (props.error) base.push('ds-input-wrapper--error')
  if (props.disabled) base.push('ds-input-wrapper--disabled')
  if (props.icon) base.push('ds-input-wrapper--has-icon-left')
  if (props.iconRight || props.clearable) base.push('ds-input-wrapper--has-icon-right')

  return base
})

const showClearButton = computed(() => {
  return props.clearable && props.modelValue && !props.disabled && !props.readonly
})

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

function handleFocus(event: FocusEvent) {
  isFocused.value = true
  emit('focus', event)
}

function handleBlur(event: FocusEvent) {
  isFocused.value = false
  emit('blur', event)
}

function handleClear() {
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}

function focus() {
  inputRef.value?.focus()
}

function blur() {
  inputRef.value?.blur()
}

defineExpose({ focus, blur })
</script>

<template>
  <div class="ds-input">
    <label
      v-if="label"
      :for="inputId"
      class="ds-input__label"
    >
      {{ label }}
      <span v-if="required" class="ds-input__required">*</span>
    </label>

    <div :class="wrapperClasses">
      <i v-if="icon" :class="['ds-input__icon-left', icon]" />

      <input
        :id="inputId"
        ref="inputRef"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        class="ds-input__field"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />

      <button
        v-if="showClearButton"
        type="button"
        class="ds-input__clear"
        aria-label="Limpiar"
        @click="handleClear"
      >
        <i class="pi pi-times" />
      </button>

      <i v-else-if="iconRight" :class="['ds-input__icon-right', iconRight]" />
    </div>

    <p v-if="error" class="ds-input__error">
      <i class="pi pi-exclamation-circle" />
      {{ error }}
    </p>
    <p v-else-if="help" class="ds-input__help">{{ help }}</p>
  </div>
</template>

<style scoped>
.ds-input {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.ds-input__label {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
}

.ds-input__required {
  color: var(--ds-color-danger);
  margin-left: var(--ds-space-0-5);
}

.ds-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background-color: var(--ds-surface-ground);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  transition: var(--ds-transition-fast);
}

/* Sizes */
.ds-input-wrapper--sm {
  height: 32px;
}

.ds-input-wrapper--md {
  height: 40px;
}

.ds-input-wrapper--lg {
  height: 48px;
}

.ds-input-wrapper--sm .ds-input__field {
  font-size: var(--ds-font-size-sm);
  padding: 0 var(--ds-space-3);
}

.ds-input-wrapper--md .ds-input__field {
  font-size: var(--ds-font-size-base);
  padding: 0 var(--ds-space-4);
}

.ds-input-wrapper--lg .ds-input__field {
  font-size: var(--ds-font-size-lg);
  padding: 0 var(--ds-space-5);
}

/* With icons */
.ds-input-wrapper--has-icon-left .ds-input__field {
  padding-left: var(--ds-space-10);
}

.ds-input-wrapper--has-icon-right .ds-input__field {
  padding-right: var(--ds-space-10);
}

/* States */
.ds-input-wrapper--focused {
  border-color: var(--ds-color-primary);
  box-shadow: 0 0 0 3px var(--ds-color-primary-light);
}

.ds-input-wrapper--error {
  border-color: var(--ds-color-danger);
}

.ds-input-wrapper--error.ds-input-wrapper--focused {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ds-color-danger) 20%, transparent);
}

.ds-input-wrapper--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--ds-surface-hover);
}

/* Field */
.ds-input__field {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--ds-color-text);
  outline: none;
}

.ds-input__field::placeholder {
  color: var(--ds-color-text-muted);
}

.ds-input__field:disabled {
  cursor: not-allowed;
}

/* Icons */
.ds-input__icon-left,
.ds-input__icon-right {
  position: absolute;
  color: var(--ds-color-text-muted);
}

.ds-input__icon-left {
  left: var(--ds-space-3);
}

.ds-input__icon-right {
  right: var(--ds-space-3);
}

/* Clear button */
.ds-input__clear {
  position: absolute;
  right: var(--ds-space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: var(--ds-surface-hover);
  border: none;
  border-radius: var(--ds-radius-full);
  cursor: pointer;
  opacity: 0.7;
  transition: var(--ds-transition-fast);
}

.ds-input__clear:hover {
  opacity: 1;
  background: var(--ds-surface-border);
}

.ds-input__clear i {
  font-size: 10px;
  color: var(--ds-color-text-secondary);
}

/* Messages */
.ds-input__error {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-danger);
}

.ds-input__error i {
  font-size: 12px;
}

.ds-input__help {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-muted);
}
</style>
