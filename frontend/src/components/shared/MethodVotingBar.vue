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

    <!-- Barras usando DsBarChart -->
    <DsBarChart
      :items="barItems"
      :size="compact ? 'compact' : 'normal'"
      :label-width="compact ? 80 : 120"
      :show-count="false"
    />

    <!-- Compact summary -->
    <div v-if="compact" class="compact-summary">
      <span>{{ agreedCount }}/{{ methods.length }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ConfidenceBadge from './ConfidenceBadge.vue'
import DsBarChart, { type BarChartItem } from '@/components/ds/DsBarChart.vue'

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

// Transform to BarChartItem format
const barItems = computed((): BarChartItem[] => {
  return sortedMethods.value.map(method => {
    const label = getMethodLabel(method.name)
    const displayLabel = method.agreed
      ? `✓ ${label}`
      : label

    return {
      label: displayLabel,
      value: method.score,
      max: 1, // Scores are 0-1
      color: method.agreed ? 'var(--green-500)' : 'var(--surface-400)',
      tooltip: `${label}: ${formatScore(method.score)}${method.agreed ? ' (consenso)' : ''}`
    }
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

.compact-summary {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}
</style>
