<template>
  <Dialog
    :visible="visible"
    modal
    :style="{ width: '900px', maxHeight: '85vh' }"
    :dismissable-mask="true"
    :draggable="false"
    class="documentation-dialog"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #header>
      <div class="doc-header">
        <i class="pi pi-book"></i>
        <span>Manual de Usuario</span>
      </div>
    </template>

    <div class="doc-content">
      <!-- Sidebar navigation -->
      <nav class="doc-nav">
        <ul>
          <li
            v-for="chapter in chapters"
            :key="chapter.key"
            :class="{ active: activeChapter === chapter.key }"
            @click="selectChapter(chapter.key)"
          >
            <i :class="chapter.icon"></i>
            <span>{{ chapter.title }}</span>
          </li>
        </ul>
      </nav>

      <!-- Markdown content -->
      <div ref="docBody" class="doc-body">
        <div class="markdown-content" v-html="renderedHtml"></div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import Dialog from 'primevue/dialog'
import { marked } from 'marked'

// Raw markdown imports via @docs alias (vite.config.ts)
import ch01 from '@docs/user-manual/01-introduction.md?raw'
import ch02 from '@docs/user-manual/02-first-analysis.md?raw'
import ch03 from '@docs/user-manual/03-entities.md?raw'
import ch04 from '@docs/user-manual/04-alerts.md?raw'
import ch05 from '@docs/user-manual/05-timeline-events.md?raw'
import ch06 from '@docs/user-manual/06-collections-sagas.md?raw'
import ch07 from '@docs/user-manual/07-settings.md?raw'
import ch08 from '@docs/user-manual/08-use-cases.md?raw'

defineProps<{
  visible: boolean
}>()

defineEmits<{
  'update:visible': [value: boolean]
}>()

interface Chapter {
  key: string
  title: string
  icon: string
  content: string
}

const chapters: Chapter[] = [
  { key: '01', title: 'Introducción', icon: 'pi pi-home', content: ch01 },
  { key: '02', title: 'Primer Análisis', icon: 'pi pi-play', content: ch02 },
  { key: '03', title: 'Entidades', icon: 'pi pi-tags', content: ch03 },
  { key: '04', title: 'Alertas', icon: 'pi pi-exclamation-triangle', content: ch04 },
  { key: '05', title: 'Timeline y Eventos', icon: 'pi pi-clock', content: ch05 },
  { key: '06', title: 'Colecciones', icon: 'pi pi-folder', content: ch06 },
  { key: '07', title: 'Configuración', icon: 'pi pi-cog', content: ch07 },
  { key: '08', title: 'Casos de Uso', icon: 'pi pi-bookmark', content: ch08 },
]

const activeChapter = ref('01')
const docBody = ref<HTMLElement | null>(null)

// Configure marked renderer to handle internal links
const renderer = new marked.Renderer()
renderer.link = ({ href, text }: { href: string; text: string }) => {
  // Convert internal .md links to chapter navigation
  const mdMatch = href.match(/(\d{2})-[\w-]+\.md/)
  if (mdMatch) {
    return `<a href="#" data-chapter="${mdMatch[1]}" class="doc-internal-link">${text}</a>`
  }
  // External links open in new tab
  if (href.startsWith('http')) {
    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${text}</a>`
  }
  // Other relative links (README, FAQ, etc.) - show as plain text
  return `<span class="doc-link-disabled" title="${href}">${text}</span>`
}

marked.setOptions({ renderer, breaks: false, gfm: true })

const renderedHtml = computed(() => {
  const chapter = chapters.find(c => c.key === activeChapter.value)
  if (!chapter) return ''
  return marked.parse(chapter.content) as string
})

function selectChapter(key: string) {
  activeChapter.value = key
  nextTick(() => {
    docBody.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

// Handle clicks on internal links
function handleContentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const link = target.closest('a.doc-internal-link') as HTMLAnchorElement | null
  if (link) {
    e.preventDefault()
    const chapterKey = link.dataset.chapter
    if (chapterKey) selectChapter(chapterKey)
  }
}

// Attach click listener when body ref is available
watch(docBody, (el) => {
  if (el) {
    el.addEventListener('click', handleContentClick)
  }
}, { immediate: true })
</script>

<style scoped>
.doc-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.doc-header i {
  font-size: 1.5rem;
  color: var(--p-primary-color);
}

.doc-content {
  display: flex;
  gap: 1.5rem;
  height: 65vh;
  min-height: 400px;
}

/* ── Sidebar nav ── */
.doc-nav {
  flex-shrink: 0;
  width: 180px;
  border-right: 1px solid var(--p-surface-border);
  padding-right: 1rem;
  overflow-y: auto;
}

.doc-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.doc-nav li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  transition: all 0.2s ease;
  white-space: nowrap;
}

.doc-nav li:hover {
  background: var(--surface-hover);
  color: var(--text-color);
}

.doc-nav li.active {
  background: var(--primary-color);
  color: white;
}

.doc-nav li i {
  font-size: 0.875rem;
  width: 1.25rem;
  flex-shrink: 0;
}

/* ── Body ── */
.doc-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 1rem;
  min-width: 0;
}

/* ── Markdown content styling ── */
.markdown-content :deep(h1) {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--primary-color);
  color: var(--text-color);
}

.markdown-content :deep(h2) {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 1.75rem 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--surface-border);
  color: var(--text-color);
}

.markdown-content :deep(h3) {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 1.25rem 0 0.5rem;
  color: var(--text-color);
}

.markdown-content :deep(h4) {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 1rem 0 0.35rem;
  color: var(--text-color);
}

.markdown-content :deep(p) {
  line-height: 1.65;
  color: var(--text-color-secondary);
  margin-bottom: 0.75rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.5rem 0 1rem;
  padding-left: 1.5rem;
}

.markdown-content :deep(li) {
  line-height: 1.65;
  color: var(--text-color-secondary);
  margin-bottom: 0.25rem;
}

.markdown-content :deep(strong) {
  color: var(--text-color);
  font-weight: 600;
}

.markdown-content :deep(a) {
  color: var(--primary-color);
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(.doc-link-disabled) {
  color: var(--text-color-secondary);
  font-style: italic;
}

.markdown-content :deep(code) {
  background: var(--surface-100);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85em;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--primary-color);
}

.markdown-content :deep(pre) {
  background: var(--surface-100);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 1rem;
  overflow-x: auto;
  margin: 0.75rem 0 1rem;
  font-size: 0.85rem;
  line-height: 1.5;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-color);
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0 1rem;
  font-size: 0.875rem;
}

.markdown-content :deep(th) {
  text-align: left;
  padding: 0.6rem 0.75rem;
  background: var(--surface-100);
  border: 1px solid var(--surface-border);
  font-weight: 600;
  color: var(--text-color);
}

.markdown-content :deep(td) {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--surface-border);
  color: var(--text-color-secondary);
}

.markdown-content :deep(tr:hover td) {
  background: var(--surface-hover);
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--primary-color);
  margin: 1rem 0;
  padding: 0.5rem 1rem;
  background: var(--surface-50);
  border-radius: 0 var(--border-radius) var(--border-radius) 0;
}

.markdown-content :deep(blockquote p) {
  margin-bottom: 0.25rem;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--surface-border);
  margin: 1.5rem 0;
}

/* ── Dark mode ── */
:global(.dark) .markdown-content :deep(code) {
  background: var(--surface-700);
}

:global(.dark) .markdown-content :deep(pre) {
  background: var(--surface-800);
  border-color: var(--surface-600);
}

:global(.dark) .markdown-content :deep(th) {
  background: var(--surface-700);
}

:global(.dark) .markdown-content :deep(blockquote) {
  background: var(--surface-800);
}
</style>
