/**
 * Chat Types for LLM Assistant
 */

/** Role in conversation */
export type ChatRole = 'user' | 'assistant'

/** Status of a message */
export type MessageStatus = 'pending' | 'complete' | 'error'

/** A navigable reference in an AI response (maps to [REF:N] in text) */
export interface ChatReference {
  /** Reference number (matches [REF:N] in response text) */
  id: number
  /** Chapter number (1-indexed) */
  chapter: number
  /** Chapter title */
  chapterTitle: string
  /** Global start character position */
  startChar: number
  /** Global end character position */
  endChar: number
  /** Excerpt text from the manuscript */
  excerpt: string
}

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
  /** Navigable references for this message */
  references?: ChatReference[]
  /** Whether the response was synthesized from multiple models */
  multiModel?: boolean
  /** Models that contributed to this response */
  modelsUsed?: string[]
}

/** Request to chat endpoint */
export interface ChatRequest {
  message: string
  history?: Array<{
    role: ChatRole
    content: string
  }>
  context?: {
    enabledInferenceMethods?: string[]
    prioritizeSpeed?: boolean
    multiModelSynthesis?: boolean
  }
  /** Selected text from the document viewer */
  selectedText?: string
  /** Chapter number of the selected text (1-indexed) */
  selectedTextChapter?: number
  /** Start character position of the selection */
  selectedTextStart?: number
  /** End character position of the selection */
  selectedTextEnd?: number
}

/** Response from chat endpoint */
export interface ChatResponse {
  response: string
  contextUsed?: string[]
  model?: string
  candidateModels?: string[]
  /** Navigable references in the response */
  references?: ChatReference[]
  /** Whether the response was synthesized from multiple models */
  multiModel?: boolean
  /** Models that contributed to this response */
  modelsUsed?: string[]
}
