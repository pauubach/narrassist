/**
 * useChat - Composable for LLM chat functionality
 *
 * Provides chat with LLM using the project document as context.
 * Supports cancellation (AbortController), message queue, and retry on connection errors.
 */

import { ref, watch, onMounted } from 'vue'
import { api, backendDown } from '@/services/apiClient'
import type { ChatMessage, ChatResponse } from '@/types'



export function useChat(projectId: number) {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const pendingQueue = ref<string[]>([])

  let abortController: AbortController | null = null

  // Load history from localStorage on mount
  onMounted(() => {
    loadHistory()
  })

  // Persist history changes (debounced to avoid serializing on every keystroke)
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    messages,
    () => {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(saveHistory, 500)
    },
    { deep: true }
  )

  function generateId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  function loadHistory(): void {
    try {
      const key = `chat_history_${projectId}`
      const saved = localStorage.getItem(key)
      if (saved) {
        const parsed = JSON.parse(saved)
        messages.value = parsed.map((m: ChatMessage) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }))
      }
    } catch (e) {
      console.warn('Error loading chat history:', e)
    }
  }

  function saveHistory(): void {
    try {
      const key = `chat_history_${projectId}`
      // Keep last 50 messages
      const toSave = messages.value.slice(-50)
      localStorage.setItem(key, JSON.stringify(toSave))
    } catch (e) {
      console.warn('Error saving chat history:', e)
    }
  }

  async function sendMessage(content: string): Promise<void> {
    // If already loading, queue the message
    if (isLoading.value) {
      pendingQueue.value.push(content)
      return
    }

    error.value = null

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'complete'
    }
    messages.value.push(userMessage)

    // Prepare request with history (last 10 messages for context)
    const history = messages.value
      .filter((m) => m.status === 'complete')
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }))

    abortController = new AbortController()
    isLoading.value = true

    try {
      // 300s timeout - CPU inference on low-end hardware can be very slow,
      // especially when analysis is running and chat has to wait for LLM scheduler.
      // retries: 3 → retry up to 3 times on connection error (backoff: 2s, 4s, 8s)
      const data = await api.postRaw<any>(
        `/api/projects/${projectId}/chat`,
        {
          message: content,
          history: history.slice(0, -1) // Exclude current message
        },
        { timeout: 300000, signal: abortController.signal, retries: 3 }
      )

      if (data.success && data.data) {
        const chatResponse = data.data as ChatResponse
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: chatResponse.response,
          timestamp: new Date(),
          status: 'complete',
          contextUsed: chatResponse.contextUsed
        }
        messages.value.push(assistantMessage)
      } else {
        error.value = data.error || 'Error al obtener respuesta'
        messages.value.push({
          id: generateId(),
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          status: 'error',
          error: data.error || 'La IA no generó respuesta'
        })
      }
    } catch (e) {
      // Manual cancellation → don't show error bubble, but finally still runs.
      // - skipCurrent: queue intact → finally processes next
      // - stopAll: queue already emptied → finally does nothing
      if (e instanceof Error && e.name === 'AbortError') {
        return
      }

      let errorMsg = 'El asistente no respondió. Si hay un análisis en curso, espera a que termine.'

      if (e instanceof Error) {
        if (e.message.includes('fetch') || e.message.includes('network')) {
          errorMsg = 'La IA no está disponible. Revisa Ajustes → Análisis.'
        } else if (e.message.includes('no respond')) {
          errorMsg = 'La IA tardó demasiado. Si hay un análisis en curso, espera a que termine.'
        } else {
          errorMsg = e.message
        }
      }

      error.value = errorMsg
      messages.value.push({
        id: generateId(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        status: 'error',
        error: errorMsg
      })
    } finally {
      abortController = null
      isLoading.value = false

      // Process queue — but only if backend is responding
      if (pendingQueue.value.length > 0 && !backendDown.value) {
        const next = pendingQueue.value.shift()!
        await sendMessage(next)
      }
    }
  }

  function cancelMessage(): void {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  function skipCurrent(): void {
    // Cancel current request but keep queue intact → finally processes next
    cancelMessage()
  }

  function stopAll(): void {
    // Cancel current + empty queue → full stop
    pendingQueue.value = []
    cancelMessage()
  }

  function removeQueued(index: number): void {
    pendingQueue.value.splice(index, 1)
  }

  function editQueued(index: number): string {
    return pendingQueue.value.splice(index, 1)[0]
  }

  function clearHistory(): void {
    messages.value = []
    pendingQueue.value = []
    localStorage.removeItem(`chat_history_${projectId}`)
    error.value = null
  }

  return {
    messages,
    isLoading,
    error,
    pendingQueue,
    sendMessage,
    cancelMessage,
    skipCurrent,
    stopAll,
    removeQueued,
    editQueued,
    clearHistory
  }
}
