/**
 * useChat - Composable for LLM chat functionality
 *
 * Provides chat with LLM using the project document as context.
 */

import { ref, watch, onMounted } from 'vue'
import { api } from '@/services/apiClient'
import type { ChatMessage, ChatResponse } from '@/types'



export function useChat(projectId: number) {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

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

    isLoading.value = true

    try {
      // 120s timeout for LLM response - CPU inference can be slow
      const data = await api.postRaw<any>(
        `/api/projects/${projectId}/chat`,
        {
          message: content,
          history: history.slice(0, -1) // Exclude current message
        },
        { timeout: 120000 }
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
        // Add error message
        messages.value.push({
          id: generateId(),
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          status: 'error',
          error: data.error || 'Error desconocido'
        })
      }
    } catch (e) {
      let errorMsg = 'Error de conexión'

      if (e instanceof Error) {
        if (e.name === 'AbortError') {
          errorMsg = 'La respuesta tardó demasiado. Verifica que Ollama esté corriendo.'
        } else if (e.message.includes('fetch')) {
          errorMsg = 'No se pudo conectar con el servidor. Verifica la conexión.'
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
      isLoading.value = false
    }
  }

  function clearHistory(): void {
    messages.value = []
    localStorage.removeItem(`chat_history_${projectId}`)
    error.value = null
  }

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearHistory
  }
}
