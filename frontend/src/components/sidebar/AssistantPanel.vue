<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChat } from '@/composables/useChat'
import type { ChatSelectionContext } from '@/composables/useChat'
import { useAnalysisStore } from '@/stores/analysis'
import { useSelectionStore } from '@/stores/selection'
import { useSystemStore } from '@/stores/system'
import type { ChatReference } from '@/types'
import ChatMessageContent from './ChatMessageContent.vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

/**
 * AssistantPanel - Chat con LLM para el sidebar.
 *
 * Permite hacer preguntas sobre el documento usando Ollama.
 * Si hay un análisis en curso, el backend prioriza el chat
 * entre iteraciones LLM (LLMScheduler), así que no se bloquea.
 *
 * Features:
 * - Text selection context: sends selected text as context to the LLM
 * - Navigable references: [REF:N] in responses become clickable badges
 * - Arrow up/down: navigate previous user messages (terminal-style)
 * - Escape: cancel current request + empty queue
 * - Message queue: send while waiting, shown as editable list
 * - Stop button: cancel + clear queue
 * - Auto-scroll on page reload
 * - Retry on connection errors (2 retries with backoff)
 */

const props = defineProps<{
  /** ID del proyecto actual */
  projectId: number
  /** Número de capítulo correspondiente a la selección (1-indexed) */
  selectionChapterNumber?: number | null
}>()

const emit = defineEmits<{
  /** Navegar a una referencia en el documento */
  (e: 'navigate-to-reference', ref: ChatReference): void
}>()

const {
  messages, isLoading, error, pendingQueue,
  sendMessage, skipCurrent, stopAll, removeQueued, editQueued, clearHistory
} = useChat(props.projectId)

const analysisStore = useAnalysisStore()
const selectionStore = useSelectionStore()
const systemStore = useSystemStore()
const isProjectAnalyzing = computed(() => analysisStore.isProjectAnalyzing(props.projectId))

const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

// Input history (terminal-style navigation)
const inputHistory = ref<string[]>([])
const historyIndex = ref(-1)
const savedInput = ref('')

// Text selection context
const activeSelection = computed(() => selectionStore.textSelection)
const activeSelectionPreview = computed(() => {
  const sel = selectionStore.textSelection
  if (!sel) return ''
  return sel.text.length > 50 ? sel.text.substring(0, 50) + '...' : sel.text
})

// --- Ollama status: adaptive polling (up: 15s, down: 5s) ---
const ollamaAvailable = computed(() => systemStore.systemCapabilities?.ollama?.available ?? false)
const ollamaHasModels = computed(() => (systemStore.systemCapabilities?.ollama?.models?.length ?? 0) > 0)
const ollamaReady = computed(() => ollamaAvailable.value && ollamaHasModels.value)

let ollamaTimer: ReturnType<typeof setInterval> | null = null

function startOllamaPolling() {
  stopOllamaPolling()
  const interval = ollamaReady.value ? 15000 : 5000
  ollamaTimer = setInterval(async () => {
    await systemStore.refreshCapabilities()
    // Adapt interval if state changed
    const newInterval = ollamaReady.value ? 15000 : 5000
    if (ollamaTimer && newInterval !== interval) {
      startOllamaPolling()
    }
  }, interval)
}

function stopOllamaPolling() {
  if (ollamaTimer) { clearInterval(ollamaTimer); ollamaTimer = null }
}

// --- Dynamic suggested questions based on entities ---
const suggestedQuestions = ref<string[]>([])

async function loadSuggestedQuestions() {
  try {
    const data = await (await import('@/services/apiClient')).api
      .getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${props.projectId}/entities`)
    if (!data.success || !data.data?.length) return
    const names = data.data
      .filter((e: any) => e.entity_type === 'PERSON' || e.entity_type === 'CHARACTER')
      .slice(0, 10)
      .map((e: any) => e.canonical_name as string)
    if (names.length === 0) return

    const questions: string[] = []
    if (names.length >= 2) {
      questions.push(`¿Qué relación tienen ${names[0]} y ${names[1]}?`)
    }
    if (names.length >= 1) {
      questions.push(`¿Hay inconsistencias con ${names[0]}?`)
    }
    if (names.length >= 3) {
      questions.push(`¿En qué capítulos aparece ${names[2]}?`)
    }
    suggestedQuestions.value = questions
  } catch { /* silent — fallback to static hints */ }
}

function useSuggestedQuestion(q: string) {
  inputText.value = q
}

// Rebuild input history from saved messages + auto-scroll on mount
onMounted(() => {
  nextTick(() => {
    inputHistory.value = messages.value
      .filter(m => m.role === 'user' && m.status === 'complete')
      .map(m => m.content)
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
  // Start Ollama polling + load entity suggestions
  systemStore.refreshCapabilities().then(() => startOllamaPolling())
  loadSuggestedQuestions()
})

onUnmounted(() => {
  stopOllamaPolling()
})

// Auto-scroll on new messages (watch length, not deep — avoid recalc on every property mutation)
watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
)

function handleSend() {
  if (!inputText.value.trim()) return
  const message = inputText.value.trim()
  inputText.value = ''
  inputHistory.value.push(message)
  historyIndex.value = -1

  // Build selection context if text is selected
  let selection: ChatSelectionContext | undefined
  const sel = selectionStore.textSelection
  if (sel?.text) {
    selection = {
      text: sel.text,
      chapter: props.selectionChapterNumber ?? undefined,
      start: sel.start,
      end: sel.end,
    }
  }

  sendMessage(message, selection)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    navigateHistory('up')
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    navigateHistory('down')
  } else if (e.key === 'Escape') {
    if (isLoading.value || pendingQueue.value.length > 0) {
      stopAll()
    }
  }
}

function navigateHistory(direction: 'up' | 'down') {
  if (inputHistory.value.length === 0) return

  if (historyIndex.value === -1) {
    if (direction === 'down') return
    savedInput.value = inputText.value
    historyIndex.value = inputHistory.value.length
  }

  const newIndex = direction === 'up'
    ? historyIndex.value - 1
    : historyIndex.value + 1

  if (newIndex < 0) return

  if (newIndex >= inputHistory.value.length) {
    historyIndex.value = -1
    inputText.value = savedInput.value
    return
  }

  historyIndex.value = newIndex
  inputText.value = inputHistory.value[newIndex]
}

function handleEditQueued(index: number) {
  inputText.value = editQueued(index)
}

function handleReferenceClick(ref: ChatReference) {
  emit('navigate-to-reference', ref)
}

function clearSelectionContext() {
  selectionStore.setTextSelection(null)
}
</script>

<template>
  <div class="assistant-panel">
    <div class="panel-header">
      <span class="panel-title">
        <i class="pi pi-comments"></i>
        Asistente
      </span>
      <div class="header-actions">
        <span
          v-tooltip.left="ollamaReady ? 'IA lista' : ollamaAvailable ? 'Sin modelos LLM' : 'Ollama no disponible'"
          class="ollama-status-dot"
          :class="ollamaReady ? 'status-ok' : 'status-down'"
        />
        <Button
          v-tooltip.left="'Limpiar historial'"
          icon="pi pi-trash"
          text
          rounded
          size="small"
          :disabled="messages.length === 0"
          class="clear-btn"
          @click="clearHistory"
        />
      </div>
    </div>

    <!-- Ollama warning banner -->
    <div v-if="!ollamaReady" class="ollama-warning">
      <i class="pi pi-exclamation-triangle"></i>
      <span v-if="!ollamaAvailable">Ollama no está arrancado. Inícialo desde Configuración.</span>
      <span v-else>No hay modelos LLM. Descarga uno desde Configuración.</span>
    </div>

    <!-- Messages area -->
    <div ref="messagesContainer" class="messages-container">
      <!-- Empty state -->
      <div v-if="messages.length === 0 && !isLoading" class="empty-state">
        <i class="pi pi-comments"></i>
        <p>Pregunta sobre tu manuscrito</p>
        <!-- Dynamic suggested questions (if entities available) -->
        <template v-if="suggestedQuestions.length > 0">
          <button
            v-for="(q, i) in suggestedQuestions"
            :key="i"
            class="suggested-question"
            @click="useSuggestedQuestion(q)"
          >
            {{ q }}
          </button>
        </template>
        <template v-else>
          <span class="hint">Ej: "¿De qué color tiene los ojos María?"</span>
        </template>
        <span class="hint">Selecciona texto para dar contexto a la IA</span>
      </div>

      <!-- Messages -->
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="[`message-${msg.role}`, msg.status === 'error' ? 'message-error' : '']"
      >
        <div v-if="msg.status !== 'error'" class="message-content">
          <!-- Assistant messages: use ChatMessageContent for reference support -->
          <template v-if="msg.role === 'assistant'">
            <ChatMessageContent
              :content="msg.content"
              :references="msg.references"
              :context-used="msg.contextUsed"
              @navigate-reference="handleReferenceClick"
            />
            <span
              v-if="msg.multiModel && msg.modelsUsed"
              class="synthesis-badge"
              v-tooltip.top="'Respuesta combinada de: ' + msg.modelsUsed.join(', ')"
            >
              <i class="pi pi-sparkles"></i>
              Síntesis &middot; {{ msg.modelsUsed.length }} modelos
            </span>
          </template>
          <template v-else>
            {{ msg.content }}
          </template>
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
        <span class="loading-text">{{ isProjectAnalyzing ? 'Esperando turno...' : 'Pensando...' }}</span>
        <Button
          v-if="pendingQueue.length > 0"
          v-tooltip.top="'Saltar esta y seguir con la cola'"
          icon="pi pi-forward"
          text
          rounded
          size="small"
          class="skip-btn"
          @click="skipCurrent"
        />
        <Button
          v-else
          v-tooltip.top="'Cancelar (Esc)'"
          icon="pi pi-times"
          text
          rounded
          size="small"
          class="skip-btn"
          @click="stopAll"
        />
      </div>
    </div>

    <!-- Queue panel -->
    <div v-if="pendingQueue.length > 0" class="queue-panel">
      <div class="queue-header">
        <span class="queue-title">En cola ({{ pendingQueue.length }})</span>
      </div>
      <div v-for="(q, idx) in pendingQueue" :key="idx" class="queue-item">
        <span class="queue-text">{{ q.content }}</span>
        <div class="queue-actions">
          <Button
            v-tooltip.top="'Editar'"
            icon="pi pi-pencil"
            text
            rounded
            size="small"
            @click="handleEditQueued(idx)"
          />
          <Button
            v-tooltip.top="'Eliminar'"
            icon="pi pi-trash"
            text
            rounded
            size="small"
            severity="danger"
            @click="removeQueued(idx)"
          />
        </div>
      </div>
    </div>

    <!-- Selection context bar -->
    <div v-if="activeSelection" class="selection-context-bar">
      <i class="pi pi-text-select"></i>
      <span class="selection-preview" :title="activeSelection.text" v-tooltip.top="'Texto seleccionado como contexto para tu pregunta'">
        "{{ activeSelectionPreview }}"
      </span>
      <Button
        v-tooltip.top="'Quitar contexto'"
        icon="pi pi-times"
        text
        rounded
        size="small"
        class="selection-clear-btn"
        @click="clearSelectionContext"
      />
    </div>

    <!-- Input area -->
    <div class="input-area">
      <InputText
        v-model="inputText"
        :placeholder="activeSelection ? 'Pregunta sobre la selección...' : 'Escribe tu pregunta...'"
        class="chat-input"
        @keydown="handleKeydown"
      />
      <!-- Stop button: visible during loading or when queue has items -->
      <Button
        v-if="isLoading || pendingQueue.length > 0"
        v-tooltip.top="'Detener (Esc)'"
        icon="pi pi-stop"
        severity="danger"
        text
        rounded
        class="stop-btn"
        @click="stopAll"
      />
      <!-- Send button: visible when idle and no queue -->
      <Button
        v-else
        icon="pi pi-send"
        :disabled="!inputText.trim()"
        class="send-btn"
        @click="handleSend"
      />
    </div>

    <!-- Global error banner — only show if no error message bubble is visible -->
    <div v-if="error && messages.length > 0 && messages[messages.length - 1]?.status !== 'error'" class="error-banner">
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

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.ollama-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ollama-status-dot.status-ok {
  background: var(--ds-color-success, #22c55e);
  box-shadow: 0 0 4px var(--ds-color-success, #22c55e);
}

.ollama-status-dot.status-down {
  background: var(--ds-color-warning, #f59e0b);
  box-shadow: 0 0 4px var(--ds-color-warning, #f59e0b);
}

.ollama-warning {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-color-warning-subtle, rgba(245, 158, 11, 0.1));
  border-bottom: 1px solid var(--ds-color-warning, #f59e0b);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-warning, #f59e0b);
  flex-shrink: 0;
}

.ollama-warning i {
  flex-shrink: 0;
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

.suggested-question {
  display: block;
  width: 100%;
  padding: var(--ds-space-2) var(--ds-space-3);
  margin: 2px 0;
  background: var(--ds-surface-hover);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text);
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
  font-family: inherit;
}

.suggested-question:hover {
  background: var(--ds-color-primary-soft, rgba(59, 130, 246, 0.08));
  border-color: var(--ds-color-primary-subtle, rgba(59, 130, 246, 0.3));
  color: var(--ds-color-primary);
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
  align-items: flex-start;
  gap: var(--ds-space-2);
  color: var(--ds-color-danger);
  font-size: var(--ds-font-size-xs);
  overflow-wrap: break-word;
  word-break: break-word;
}

.message-error-content i {
  flex-shrink: 0;
  margin-top: 2px;
}

.synthesis-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding: 2px 8px;
  font-size: 0.7rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  border-radius: 12px;
}

.synthesis-badge i {
  font-size: 0.65rem;
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

.skip-btn {
  margin-left: auto;
  width: 1.5rem;
  height: 1.5rem;
  color: var(--ds-color-text-muted) !important;
}

/* Queue panel */
.queue-panel {
  border-top: 1px solid var(--ds-surface-border);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-surface-ground);
  max-height: 120px;
  overflow-y: auto;
  flex-shrink: 0;
}

.queue-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--ds-space-1);
}

.queue-title {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
  font-weight: var(--ds-font-weight-semibold);
}

.queue-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-1) 0;
  gap: var(--ds-space-2);
  border-bottom: 1px solid var(--ds-surface-border);
}

.queue-item:last-child {
  border-bottom: none;
}

.queue-text {
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

/* Selection context bar */
.selection-context-bar {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-color-primary-soft, rgba(59, 130, 246, 0.08));
  border-top: 1px solid var(--ds-color-primary-subtle, rgba(59, 130, 246, 0.2));
  flex-shrink: 0;
}

.selection-context-bar i.pi-text-select {
  color: var(--ds-color-primary);
  font-size: 0.8rem;
  flex-shrink: 0;
}

.selection-preview {
  flex: 1;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selection-clear-btn {
  width: 1.5rem;
  height: 1.5rem;
  flex-shrink: 0;
  color: var(--ds-color-text-muted) !important;
}

/* Input area */
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

.stop-btn {
  flex-shrink: 0;
}

.error-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-color-danger-subtle);
  border-top: 1px solid var(--ds-color-danger);
  color: var(--ds-color-danger);
  font-size: var(--ds-font-size-xs);
  overflow-wrap: break-word;
  word-break: break-word;
  flex-shrink: 0;
}
</style>
