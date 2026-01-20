<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChat } from '@/composables/useChat'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

/**
 * AssistantPanel - Chat con LLM para el sidebar.
 *
 * Permite hacer preguntas sobre el documento usando Ollama.
 */

const props = defineProps<{
  /** ID del proyecto actual */
  projectId: number
}>()

const { messages, isLoading, error, sendMessage, clearHistory } = useChat(props.projectId)

const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

// Auto-scroll on new messages
watch(
  messages,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
  { deep: true }
)

async function handleSend() {
  if (!inputText.value.trim() || isLoading.value) return

  const message = inputText.value.trim()
  inputText.value = ''
  await sendMessage(message)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="assistant-panel">
    <div class="panel-header">
      <span class="panel-title">
        <i class="pi pi-comments"></i>
        Asistente
      </span>
      <Button
        icon="pi pi-trash"
        text
        rounded
        size="small"
        @click="clearHistory"
        v-tooltip.left="'Limpiar historial'"
        :disabled="messages.length === 0"
        class="clear-btn"
      />
    </div>

    <!-- Messages area -->
    <div ref="messagesContainer" class="messages-container">
      <!-- Empty state -->
      <div v-if="messages.length === 0 && !isLoading" class="empty-state">
        <i class="pi pi-comments"></i>
        <p>Pregunta sobre tu manuscrito</p>
        <span class="hint">Ej: "¿Cuántas veces aparece Ana?"</span>
      </div>

      <!-- Messages -->
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="[`message-${msg.role}`, msg.status === 'error' ? 'message-error' : '']"
      >
        <div v-if="msg.status !== 'error'" class="message-content">
          {{ msg.content }}
        </div>
        <div v-else class="message-error-content">
          <i class="pi pi-exclamation-triangle"></i>
          {{ msg.error || 'Error al obtener respuesta' }}
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="isLoading" class="message message-assistant message-loading">
        <span class="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </span>
        <span class="loading-text">Pensando...</span>
      </div>
    </div>

    <!-- Input area -->
    <div class="input-area">
      <InputText
        v-model="inputText"
        placeholder="Escribe tu pregunta..."
        @keydown="handleKeydown"
        :disabled="isLoading"
        class="chat-input"
      />
      <Button
        icon="pi pi-send"
        @click="handleSend"
        :disabled="!inputText.trim() || isLoading"
        :loading="isLoading"
        class="send-btn"
      />
    </div>

    <!-- Global error banner -->
    <div v-if="error && messages.length > 0" class="error-banner">
      <i class="pi pi-exclamation-triangle"></i>
      <span>{{ error }}</span>
    </div>
  </div>
</template>

<style scoped>
.assistant-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.panel-title i {
  color: var(--ds-color-primary);
}

.clear-btn {
  width: 2rem;
  height: 2rem;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-6);
  color: var(--ds-color-text-secondary);
  text-align: center;
  flex: 1;
}

.empty-state i {
  font-size: 2.5rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: var(--ds-font-size-sm);
}

.empty-state .hint {
  font-size: var(--ds-font-size-xs);
  font-style: italic;
  opacity: 0.7;
}

.message {
  max-width: 85%;
  padding: var(--ds-space-2) var(--ds-space-3);
  border-radius: var(--ds-radius-lg);
  font-size: var(--ds-font-size-sm);
  line-height: 1.5;
  word-wrap: break-word;
}

.message-user {
  align-self: flex-end;
  background: var(--ds-color-primary);
  color: white;
  border-bottom-right-radius: var(--ds-radius-sm);
}

.message-assistant {
  align-self: flex-start;
  background: var(--ds-surface-hover);
  color: var(--ds-color-text);
  border-bottom-left-radius: var(--ds-radius-sm);
}

.message-error {
  background: var(--ds-color-danger-subtle);
  border: 1px solid var(--ds-color-danger);
}

.message-error-content {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-color-danger);
  font-size: var(--ds-font-size-xs);
}

.message-loading {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: var(--ds-color-text-secondary);
  border-radius: 50%;
  animation: dot-pulse 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes dot-pulse {
  0%,
  80%,
  100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.loading-text {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.input-area {
  display: flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  border-top: 1px solid var(--ds-surface-border);
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  font-size: var(--ds-font-size-sm);
}

.send-btn {
  flex-shrink: 0;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-color-danger-subtle);
  border-top: 1px solid var(--ds-color-danger);
  color: var(--ds-color-danger);
  font-size: var(--ds-font-size-xs);
}
</style>
