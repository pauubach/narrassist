<template>
  <div :class="['method-voting-bar', { compact }]">
    <!-- Header with summary -->
    <div v-if="!compact" class="voting-header">
      <span class="voting-summary">
        <strong>{{ agreedCount }}/{{ methods.length }}</strong> métodos coinciden
      </span>
      <ConfidenceBadge
        :value="consensusScore"
        variant="badge"
        size="sm"
        :show-icon="false"
      />
    </div>

    <!-- Methods list -->
    <div class="methods-list">
      <div
        v-for="method in sortedMethods"
        :key="method.name"
        :class="['method-item', { agreed: method.agreed, compact }]"
      >
        <div class="method-info">
          <span class="method-name">{{ getMethodLabel(method.name) }}</span>
          <span v-if="!compact" class="method-score">{{ formatScore(method.score) }}</span>
        </div>
        <div class="method-bar">
          <div
            class="method-fill"
            :style="{ width: `${method.score * 100}%` }"
            :class="{ agreed: method.agreed }"
          ></div>
        </div>
        <i
          v-if="method.agreed"
          v-tooltip.top="'Coincide con el consenso'"
          class="pi pi-check agreed-icon"
        ></i>
      </div>
    </div>

    <!-- Compact summary -->
    <div v-if="compact" class="compact-summary">
      <span>{{ agreedCount }}/{{ methods.length }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ConfidenceBadge from './ConfidenceBadge.vue'

interface MethodVote {
  name: string
  score: number
  agreed: boolean
}

interface Props {
  methods: MethodVote[]
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
})

// Method name labels
const METHOD_LABELS: Record<string, string> = {
  // Coreference methods
  embeddings: 'Embeddings',
  llm: 'LLM',
  morpho: 'Morfosintáctico',
  heuristics: 'Heurísticas',
  transformer: 'Transformer',
  // Spelling methods
  patterns: 'Patrones',
  languagetool: 'LanguageTool',
  symspell: 'SymSpell',
  hunspell: 'Hunspell',
  pyspellchecker: 'PySpellChecker',
  beto: 'BETO ML',
  llm_arbitrator: 'LLM Arbitrador',
  // LLM models
  'llama3.2': 'Llama 3.2',
  mistral: 'Mistral',
  'qwen2.5': 'Qwen 2.5',
  gemma2: 'Gemma 2',
  // Generic
  rule_based: 'Reglas',
  manual: 'Manual'
}

const getMethodLabel = (name: string): string => {
  return METHOD_LABELS[name] || name
}

const formatScore = (score: number): string => {
  return `${Math.round(score * 100)}%`
}

// Computed: count of methods that agreed
const agreedCount = computed(() => {
  return props.methods.filter(m => m.agreed).length
})

// Computed: overall consensus score (average of agreed methods)
const consensusScore = computed(() => {
  const agreed = props.methods.filter(m => m.agreed)
  if (agreed.length === 0) return 0
  return agreed.reduce((sum, m) => sum + m.score, 0) / agreed.length
})

// Sort methods: agreed first, then by score
const sortedMethods = computed(() => {
  return [...props.methods].sort((a, b) => {
    if (a.agreed !== b.agreed) return b.agreed ? 1 : -1
    return b.score - a.score
  })
})
</script>

<style scoped>
.method-voting-bar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.method-voting-bar.compact {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.voting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.voting-summary {
  font-size: 0.875rem;
  color: var(--text-color);
}

.voting-summary strong {
  color: var(--primary-color);
}

.methods-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.compact .methods-list {
  flex-direction: row;
  gap: 0.25rem;
  flex: 1;
}

.method-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 3px solid var(--surface-300);
  transition: border-color 0.2s;
}

.method-item.agreed {
  border-left-color: var(--app-success-hover, var(--p-green-600, #16a34a)); /* WCAG AA */
  background: var(--app-success-bg, var(--p-green-50, #f0fdf4));
}

.method-item.compact {
  padding: 0.25rem 0.5rem;
  border-left-width: 2px;
}

.method-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 0;
}

.compact .method-info {
  display: none;
}

.method-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.method-score {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  flex-shrink: 0;
}

.method-bar {
  width: 80px;
  height: 6px;
  background: var(--surface-200);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.compact .method-bar {
  width: 40px;
  height: 4px;
}

.method-fill {
  height: 100%;
  background: var(--surface-400);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.method-fill.agreed {
  background: var(--app-success-hover, var(--p-green-600, #16a34a)); /* WCAG AA */
}

.agreed-icon {
  color: var(--app-success-hover, var(--p-green-600, #16a34a)); /* WCAG AA: 4.5:1 */
  font-size: 0.875rem;
  flex-shrink: 0;
}

.compact .agreed-icon {
  font-size: 0.75rem;
}

.compact-summary {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}
</style>
