/**
 * useChat - Composable for LLM chat functionality
 *
 * Provides chat with LLM using the project document as context.
 */

import { ref, watch, onMounted } from 'vue'
import type { ChatMessage, ChatRequest, ChatResponse } from '@/types'

const API_BASE = 'http://localhost:8008'

export function useChat(projectId: number) {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Load history from localStorage on mount
  onMounted(() => {
    loadHistory()
  })

  // Persist history changes
  watch(
    messages,
    () => {
      saveHistory()
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
      const response = await fetch(`${API_BASE}/api/projects/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          history: history.slice(0, -1) // Exclude current message
        } as ChatRequest)
      })

      const data = await response.json()

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
      const errorMsg = e instanceof Error ? e.message : 'Error de conexión'
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
