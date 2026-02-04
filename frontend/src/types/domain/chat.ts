/**
 * Chat Types for LLM Assistant
 */

/** Role in conversation */
export type ChatRole = 'user' | 'assistant'

/** Status of a message */
export type MessageStatus = 'pending' | 'complete' | 'error'

/** Single chat message */
export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  timestamp: Date
  status: MessageStatus
  /** Context chunks used for this response (for transparency) */
  contextUsed?: string[]
  /** Error message if status is 'error' */
  error?: string
}

/** Request to chat endpoint */
export interface ChatRequest {
  message: string
  history?: Array<{
    role: ChatRole
    content: string
  }>
}

/** Response from chat endpoint */
export interface ChatResponse {
  response: string
  contextUsed?: string[]
  model?: string
}
