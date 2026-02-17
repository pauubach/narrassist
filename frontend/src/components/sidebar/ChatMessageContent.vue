<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import type { ChatReference } from '@/types'
import { renderAssistantMarkdown } from '@/utils/renderAssistantMarkdown'

/**
 * ChatMessageContent - Renderiza mensajes del asistente con referencias navegables.
 *
 * Estrategia de rendering (2 pasos):
 * 1. Renderiza TODO el markdown de una sola vez (preserva estructura de listas/párrafos)
 * 2. Post-procesa el HTML sanitizado para reemplazar [REF:N] por botones clicables
 * 3. Usa event delegation para capturar clicks en los botones inyectados
 */

const props = defineProps<{
  /** Contenido markdown del mensaje */
  content: string
  /** Referencias navegables asociadas al mensaje */
  references?: ChatReference[]
  /** Capítulos usados como contexto RAG (para feedback cuando no hay refs inline) */
  contextUsed?: string[]
}>()

const emit = defineEmits<{
  /** Navegar a una referencia en el documento */
  (e: 'navigate-reference', ref: ChatReference): void
}>()

/** Mapa rápido de ref_id → ChatReference */
const refMap = computed(() => {
  const map = new Map<number, ChatReference>()
  if (props.references) {
    for (const ref of props.references) {
      map.set(ref.id, ref)
    }
  }
  return map
})

/** IDs de referencias válidas presentes en el texto */
const activeRefIds = computed<number[]>(() => {
  const content = props.content || ''
  const ids: number[] = []
  const seen = new Set<number>()
  const refPattern = /\[REF:(\d+)\]/g
  let match: RegExpExecArray | null
  while ((match = refPattern.exec(content)) !== null) {
    const id = parseInt(match[1], 10)
    if (refMap.value.has(id) && !seen.has(id)) {
      ids.push(id)
      seen.add(id)
    }
  }
  return ids
})

/** Si hay referencias válidas en el mensaje */
const hasReferences = computed(() => activeRefIds.value.length > 0)

/** Referencias que realmente aparecen en el texto (para el footer) */
const activeRefs = computed(() =>
  activeRefIds.value
    .map(id => refMap.value.get(id))
    .filter((r): r is ChatReference => !!r)
)

/** Feedback de contexto: se muestra cuando hay contexto RAG pero no refs inline */
const contextFeedback = computed(() => {
  if (hasReferences.value || !props.contextUsed?.length) return ''
  const n = props.contextUsed.length
  const unique = new Set(props.contextUsed)
  return `Basado en ${n} fragmento${n > 1 ? 's' : ''} de ${unique.size} cap\u00edtulo${unique.size > 1 ? 's' : ''}`
})

/**
 * HTML renderizado: renderiza markdown completo, luego reemplaza [REF:N]
 * por botones inline. El reemplazo ocurre DESPUÉS de DOMPurify, lo cual
 * es seguro porque el HTML del botón es generado por nosotros, no por el LLM.
 */
const renderedHtml = computed(() => {
  const content = props.content || ''
  if (!content) return ''

  // Paso 1: Renderizar todo el markdown (incluyendo [REF:N] como texto)
  let html = renderAssistantMarkdown(content)

  // Paso 2: Post-procesar — reemplazar [REF:N] por botones HTML
  html = html.replace(
    /\[REF:(\d+)\]/g,
    (_match, idStr) => {
      const id = parseInt(idStr, 10)
      const ref = refMap.value.get(id)
      if (ref) {
        const title = escapeAttr(ref.chapterTitle)
        const excerpt = escapeAttr(
          ref.excerpt.length > 80 ? ref.excerpt.substring(0, 80) + '...' : ref.excerpt
        )
        const tooltip = `${title}: &quot;${excerpt}&quot;`
        return `<button type="button" class="ref-badge" data-ref-id="${id}" title="${tooltip}">`
          + `<i class="pi pi-map-marker"></i>`
          + `<span>${title}</span>`
          + `<i class="pi pi-arrow-right ref-arrow"></i>`
          + `</button>`
      }
      return _match
    }
  )

  return html
})

/** Escapa atributos HTML */
function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** Event delegation: captura clicks en .ref-badge dentro del contenido renderizado */
function handleContentClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  console.log('[ChatMessageContent] Click detected on:', target.tagName, target.className)

  const badge = target.closest('.ref-badge') as HTMLElement | null
  if (!badge) {
    console.log('[ChatMessageContent] Not a ref-badge click')
    return
  }

  const refId = parseInt(badge.dataset.refId || '', 10)
  console.log('[ChatMessageContent] Ref badge clicked, id:', refId)

  const ref = refMap.value.get(refId)
  if (ref) {
    console.log('[ChatMessageContent] Emitting navigate-reference for:', ref)
    emit('navigate-reference', ref)
  } else {
    console.warn('[ChatMessageContent] No reference found for id:', refId)
  }
}

function handleRefClick(ref: ChatReference) {
  emit('navigate-reference', ref)
}

function getRefTooltip(ref: ChatReference): string {
  const excerpt = ref.excerpt.length > 80
    ? ref.excerpt.substring(0, 80) + '...'
    : ref.excerpt
  return `${ref.chapterTitle}: "${excerpt}"`
}
</script>

<template>
  <div class="chat-message-content" @click="handleContentClick">
    <!-- Contenido markdown + ref badges inyectados via post-procesado -->
    <div class="text-segment" v-html="renderedHtml" />

    <!-- Feedback de contexto RAG (cuando no hay refs inline) -->
    <div v-if="contextFeedback" class="context-feedback">
      <i class="pi pi-search"></i>
      {{ contextFeedback }}
    </div>

    <!-- Lista de referencias al final (solo las que aparecen en el texto) -->
    <div v-if="hasReferences" class="references-footer">
      <div class="references-label">
        <i class="pi pi-bookmark"></i>
        Referencias
      </div>
      <div class="references-list">
        <Button
          v-for="ref in activeRefs"
          :key="ref.id"
          v-tooltip.top="getRefTooltip(ref)"
          :label="`[${ref.id}] ${ref.chapterTitle}`"
          icon="pi pi-arrow-right"
          size="small"
          text
          class="ref-nav-btn"
          @click="handleRefClick(ref)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-message-content {
  display: contents;
}

.text-segment :deep(p) {
  margin: 0 0 0.35rem 0;
}

.text-segment :deep(p:last-child) {
  margin-bottom: 0;
}

.text-segment :deep(ul),
.text-segment :deep(ol) {
  margin: 0.35rem 0;
  padding-left: 1.25rem;
}

.text-segment :deep(li) {
  margin: 0.15rem 0;
}

.text-segment :deep(code) {
  font-family: var(--ds-font-family-mono, ui-monospace, SFMono-Regular, Consolas, monospace);
  font-size: 0.85em;
  background: var(--ds-surface-ground);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-sm);
  padding: 0.05rem 0.25rem;
}

.text-segment :deep(blockquote) {
  margin: 0.4rem 0;
  padding-left: 0.6rem;
  border-left: 3px solid var(--ds-color-primary);
  color: var(--ds-color-text-secondary);
}

.text-segment :deep(a) {
  color: var(--ds-color-primary);
  text-decoration: underline;
}

/* Reference badge inline (inyectado via post-procesado HTML) */
.text-segment :deep(.ref-badge) {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  margin: 0 2px;
  background: var(--ds-color-primary-soft, rgba(59, 130, 246, 0.12));
  border: 1px solid var(--ds-color-primary-subtle, rgba(59, 130, 246, 0.3));
  border-radius: var(--ds-radius-sm);
  color: var(--ds-color-primary);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  vertical-align: middle;
  line-height: 1.4;
  font-family: inherit;
}

.text-segment :deep(.ref-badge:hover) {
  background: var(--ds-color-primary-subtle, rgba(59, 130, 246, 0.2));
  border-color: var(--ds-color-primary);
}

.text-segment :deep(.ref-badge i) {
  font-size: 0.65rem;
}

.text-segment :deep(.ref-arrow) {
  font-size: 0.6rem !important;
  opacity: 0.7;
}

/* Context feedback (when no inline refs) */
.context-feedback {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 0.4rem;
  font-size: 0.7rem;
  color: var(--ds-color-text-muted);
  opacity: 0.7;
}

.context-feedback i {
  font-size: 0.65rem;
}

/* References footer */
.references-footer {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--ds-surface-border);
}

.references-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--ds-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.references-label i {
  font-size: 0.7rem;
}

.references-list {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.ref-nav-btn {
  font-size: 0.75rem !important;
  padding: 2px 6px !important;
}

.ref-nav-btn :deep(.p-button-label) {
  font-size: 0.75rem;
}
</style>
