<template>
  <div class="relationship-graph">
    <!-- Toolbar -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h3>Grafo de Relaciones</h3>
        <Tag v-if="stats.totalNodes > 0" severity="info">
          {{ stats.totalNodes }} entidades
        </Tag>
        <Tag v-if="stats.totalEdges > 0" severity="secondary">
          {{ stats.totalEdges }} relaciones
        </Tag>
      </div>
      <div class="toolbar-right">
        <Button
          icon="pi pi-search-minus"
          text
          rounded
          @click="zoomOut"
          v-tooltip.bottom="'Alejar'"
        />
        <Button
          icon="pi pi-search-plus"
          text
          rounded
          @click="zoomIn"
          v-tooltip.bottom="'Acercar'"
        />
        <Button
          icon="pi pi-refresh"
          text
          rounded
          @click="resetView"
          v-tooltip.bottom="'Restablecer vista'"
        />
        <Dropdown
          v-model="layoutType"
          :options="layoutOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Layout"
          class="layout-dropdown"
          @change="updateLayout"
        />
        <Button
          icon="pi pi-cog"
          text
          rounded
          @click="showSettings = !showSettings"
          v-tooltip.bottom="'Configuración'"
        />
      </div>
    </div>

    <!-- Settings Panel -->
    <div v-if="showSettings" class="settings-panel">
      <div class="setting-group">
        <label>Mostrar relaciones</label>
        <div class="checkbox-group">
          <div class="checkbox-item">
            <Checkbox v-model="filters.showPositive" :binary="true" inputId="showPositive" />
            <label for="showPositive" class="positive-label">Positivas</label>
          </div>
          <div class="checkbox-item">
            <Checkbox v-model="filters.showNeutral" :binary="true" inputId="showNeutral" />
            <label for="showNeutral" class="neutral-label">Neutrales</label>
          </div>
          <div class="checkbox-item">
            <Checkbox v-model="filters.showNegative" :binary="true" inputId="showNegative" />
            <label for="showNegative" class="negative-label">Negativas</label>
          </div>
        </div>
      </div>
      <div class="setting-group">
        <label>Intensidad mínima</label>
        <Slider v-model="filters.minStrength" :min="0" :max="1" :step="0.1" />
        <small>{{ (filters.minStrength * 100).toFixed(0) }}%</small>
      </div>
      <div class="setting-group">
        <label>Mostrar clusters</label>
        <InputSwitch v-model="filters.showClusters" />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="graph-loading">
      <ProgressSpinner style="width: 50px; height: 50px" />
      <p>Analizando relaciones...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasData" class="graph-empty">
      <i class="pi pi-share-alt empty-icon"></i>
      <h4>No hay datos de relaciones</h4>
      <p>Analiza el documento para detectar relaciones entre personajes</p>
    </div>

    <!-- Graph Container -->
    <div v-else ref="graphContainer" class="graph-container"></div>

    <!-- Legend -->
    <div v-if="hasData && !loading" class="graph-legend">
      <div class="legend-section">
        <span class="legend-title">Relaciones:</span>
        <div class="legend-item">
          <span class="legend-line positive"></span>
          <span>Positiva</span>
        </div>
        <div class="legend-item">
          <span class="legend-line neutral"></span>
          <span>Neutral</span>
        </div>
        <div class="legend-item">
          <span class="legend-line negative"></span>
          <span>Negativa</span>
        </div>
      </div>
      <div v-if="filters.showClusters && clusters.length > 0" class="legend-section">
        <span class="legend-title">Clusters:</span>
        <div v-for="cluster in clusters.slice(0, 5)" :key="cluster.id" class="legend-item">
          <span class="legend-dot" :style="{ background: cluster.color }"></span>
          <span>{{ cluster.label || `Grupo ${cluster.id}` }}</span>
        </div>
      </div>
    </div>

    <!-- Selected Entity Panel -->
    <div v-if="selectedEntity" class="entity-panel">
      <div class="panel-header">
        <div class="entity-title">
          <i :class="getEntityIcon(selectedEntity.type)"></i>
          <h4>{{ selectedEntity.label }}</h4>
        </div>
        <Button icon="pi pi-times" text rounded size="small" @click="selectedEntity = null" />
      </div>
      <div class="panel-content">
        <div v-if="selectedEntityRelations.length > 0" class="relations-list">
          <div
            v-for="rel in selectedEntityRelations"
            :key="rel.target"
            class="relation-item"
            :class="`relation-${rel.valence}`"
          >
            <span class="relation-target">{{ rel.targetLabel }}</span>
            <div class="relation-info">
              <Tag :severity="getValenceSeverity(rel.valence)" size="small">
                {{ getValenceLabel(rel.valence) }}
              </Tag>
              <span class="relation-strength">{{ (rel.strength * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="no-relations">
          <small>No hay relaciones directas</small>
        </div>
        <Divider v-if="selectedEntityMentions.length > 0" />
        <div v-if="selectedEntityMentions.length > 0" class="mentions-summary">
          <h5>Menciones recientes</h5>
          <div v-for="mention in selectedEntityMentions.slice(0, 5)" :key="mention.id" class="mention-item">
            <small>{{ mention.context }}</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import type { Options, Node, Edge } from 'vis-network/standalone'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Slider from 'primevue/slider'
import InputSwitch from 'primevue/inputswitch'
import ProgressSpinner from 'primevue/progressspinner'
import Divider from 'primevue/divider'

interface RelationshipData {
  relations: Array<{
    source_id: number
    target_id: number
    strength: number
    valence: string
    evidence_count: number
  }>
  clusters: Array<{
    id: number
    entity_ids: number[]
    cohesion: number
    label?: string
  }>
  mentions: Array<{
    id: number
    source_id: number
    target_id: number
    context: string
    mention_type: string
  }>
  entities: Array<{
    id: number
    name: string
    type: string
    importance: string
  }>
}

const props = defineProps<{
  projectId: number
  data?: RelationshipData | null
}>()

const emit = defineEmits<{
  entitySelect: [entityId: number]
  relationSelect: [sourceId: number, targetId: number]
}>()

// Refs
const graphContainer = ref<HTMLElement | null>(null)
const network = ref<Network | null>(null)
const loading = ref(false)
const showSettings = ref(false)
const selectedEntity = ref<{ id: number; label: string; type: string } | null>(null)

// Data
const relationshipData = ref<RelationshipData | null>(null)

// Filters
const filters = ref({
  showPositive: true,
  showNeutral: true,
  showNegative: true,
  minStrength: 0.1,
  showClusters: true
})

const layoutType = ref('forceAtlas2Based')
const layoutOptions = [
  { label: 'Force Atlas', value: 'forceAtlas2Based' },
  { label: 'Jerárquico', value: 'hierarchical' },
  { label: 'Circular', value: 'circular' },
  { label: 'Aleatorio', value: 'random' }
]

// Computed
const hasData = computed(() => {
  const data = props.data || relationshipData.value
  return data && (data.relations?.length > 0 || data.entities?.length > 0)
})

const clusters = computed(() => {
  const data = props.data || relationshipData.value
  if (!data?.clusters) return []

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
  return data.clusters.map((c, idx) => ({
    ...c,
    color: colors[idx % colors.length]
  }))
})

const stats = computed(() => {
  const data = props.data || relationshipData.value
  return {
    totalNodes: data?.entities?.length || 0,
    totalEdges: data?.relations?.length || 0
  }
})

const selectedEntityRelations = computed(() => {
  if (!selectedEntity.value) return []
  const data = props.data || relationshipData.value
  if (!data?.relations) return []

  const entityId = selectedEntity.value.id
  return data.relations
    .filter(r => r.source_id === entityId || r.target_id === entityId)
    .map(r => {
      const isSource = r.source_id === entityId
      const targetId = isSource ? r.target_id : r.source_id
      const targetEntity = data.entities?.find(e => e.id === targetId)
      return {
        target: targetId,
        targetLabel: targetEntity?.name || `Entity ${targetId}`,
        strength: r.strength,
        valence: r.valence
      }
    })
    .sort((a, b) => b.strength - a.strength)
})

const selectedEntityMentions = computed(() => {
  if (!selectedEntity.value) return []
  const data = props.data || relationshipData.value
  if (!data?.mentions) return []

  const entityId = selectedEntity.value.id
  return data.mentions
    .filter(m => m.source_id === entityId || m.target_id === entityId)
    .slice(0, 10)
})

// Methods
const loadRelationships = async () => {
  if (props.data) {
    relationshipData.value = props.data
    return
  }

  loading.value = true
  try {
    const response = await fetch(`/api/projects/${props.projectId}/relationships`)
    const result = await response.json()
    if (result.success) {
      relationshipData.value = result.data
    }
  } catch (err) {
    console.error('Error loading relationships:', err)
  } finally {
    loading.value = false
  }
}

const initializeGraph = () => {
  if (!graphContainer.value || !hasData.value) return

  const data = props.data || relationshipData.value
  if (!data) return

  // Create nodes
  const nodes = new DataSet<Node>(
    data.entities.map(entity => {
      const cluster = clusters.value.find(c => c.entity_ids?.includes(entity.id))
      const nodeColor = cluster?.color || getEntityColor(entity.type)

      return {
        id: entity.id,
        label: entity.name,
        title: `${entity.name}\nTipo: ${entity.type}\nImportancia: ${entity.importance}`,
        color: {
          background: nodeColor,
          border: nodeColor,
          highlight: {
            background: nodeColor,
            border: '#1e40af'
          }
        },
        font: {
          color: '#1f2937',
          size: getNodeSize(entity.importance)
        },
        size: getNodeSize(entity.importance),
        shape: getNodeShape(entity.type),
        group: cluster?.id?.toString()
      }
    }) as Node[]
  )

  // Create edges with filtering
  const filteredRelations = data.relations.filter(rel => {
    if (rel.strength < filters.value.minStrength) return false
    if (rel.valence === 'positive' && !filters.value.showPositive) return false
    if (rel.valence === 'neutral' && !filters.value.showNeutral) return false
    if (rel.valence === 'negative' && !filters.value.showNegative) return false
    return true
  })

  const edges = new DataSet<Edge>(
    filteredRelations.map((rel, idx) => ({
      id: idx,
      from: rel.source_id,
      to: rel.target_id,
      value: rel.strength * 10,
      title: `Intensidad: ${(rel.strength * 100).toFixed(0)}%\nEvidencias: ${rel.evidence_count}`,
      color: {
        color: getEdgeColor(rel.valence),
        highlight: getEdgeColor(rel.valence),
        opacity: 0.6 + rel.strength * 0.4
      },
      width: 1 + rel.strength * 4,
      smooth: {
        enabled: true,
        type: 'continuous',
        roundness: 0.5
      }
    })) as Edge[]
  )

  // Network options
  const options: Options = {
    nodes: {
      borderWidth: 2,
      shadow: true,
      font: {
        face: 'Inter, system-ui, sans-serif'
      }
    },
    edges: {
      smooth: {
        enabled: true,
        type: 'continuous',
        roundness: 0.5
      },
      shadow: true
    },
    physics: getPhysicsOptions(),
    interaction: {
      hover: true,
      tooltipDelay: 200,
      navigationButtons: false,
      keyboard: true,
      zoomView: true,
      dragView: true
    },
    layout: getLayoutOptions()
  }

  // Destroy existing network
  if (network.value) {
    network.value.destroy()
  }

  // Create new network
  network.value = new Network(graphContainer.value, { nodes, edges }, options)

  // Event listeners
  network.value.on('selectNode', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      const entity = data.entities.find(e => e.id === nodeId)
      if (entity) {
        selectedEntity.value = {
          id: entity.id,
          label: entity.name,
          type: entity.type
        }
        emit('entitySelect', nodeId)
      }
    }
  })

  network.value.on('deselectNode', () => {
    selectedEntity.value = null
  })

  network.value.on('selectEdge', (params) => {
    if (params.edges.length > 0) {
      const edgeIdx = params.edges[0]
      const rel = filteredRelations[edgeIdx]
      if (rel) {
        emit('relationSelect', rel.source_id, rel.target_id)
      }
    }
  })
}

const getPhysicsOptions = () => {
  if (layoutType.value === 'hierarchical') {
    return { enabled: false }
  }

  return {
    enabled: true,
    solver: layoutType.value === 'forceAtlas2Based' ? 'forceAtlas2Based' : 'barnesHut',
    forceAtlas2Based: {
      gravitationalConstant: -50,
      centralGravity: 0.01,
      springLength: 200,
      springConstant: 0.08,
      damping: 0.4
    },
    barnesHut: {
      gravitationalConstant: -2000,
      centralGravity: 0.3,
      springLength: 150,
      springConstant: 0.04,
      damping: 0.09
    },
    stabilization: {
      enabled: true,
      iterations: 200,
      updateInterval: 25
    }
  }
}

const getLayoutOptions = () => {
  if (layoutType.value === 'hierarchical') {
    return {
      hierarchical: {
        enabled: true,
        direction: 'UD',
        sortMethod: 'hubsize',
        levelSeparation: 150,
        nodeSpacing: 100
      }
    }
  }

  if (layoutType.value === 'circular') {
    return {
      improvedLayout: true
    }
  }

  return {
    improvedLayout: true,
    randomSeed: 42
  }
}

const getEntityColor = (type: string): string => {
  const colors: Record<string, string> = {
    'CHARACTER': '#3b82f6',
    'LOCATION': '#10b981',
    'ORGANIZATION': '#f59e0b',
    'OBJECT': '#8b5cf6',
    'EVENT': '#ec4899',
    'ANIMAL': '#06b6d4',
    'CREATURE': '#6366f1'
  }
  return colors[type] || '#6b7280'
}

const getNodeSize = (importance: string): number => {
  const sizes: Record<string, number> = {
    'critical': 35,
    'high': 28,
    'medium': 22,
    'low': 16,
    'minimal': 12
  }
  return sizes[importance] || 18
}

const getNodeShape = (type: string): string => {
  const shapes: Record<string, string> = {
    'CHARACTER': 'dot',
    'LOCATION': 'diamond',
    'ORGANIZATION': 'square',
    'OBJECT': 'triangle',
    'EVENT': 'star'
  }
  return shapes[type] || 'dot'
}

const getEdgeColor = (valence: string): string => {
  const colors: Record<string, string> = {
    'positive': '#10b981',
    'neutral': '#6b7280',
    'negative': '#ef4444',
    'very_positive': '#059669',
    'very_negative': '#dc2626'
  }
  return colors[valence] || '#6b7280'
}

const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building',
    'OBJECT': 'pi pi-box',
    'EVENT': 'pi pi-calendar'
  }
  return icons[type] || 'pi pi-tag'
}

const getValenceSeverity = (valence: string): string => {
  const severities: Record<string, string> = {
    'positive': 'success',
    'very_positive': 'success',
    'neutral': 'secondary',
    'negative': 'danger',
    'very_negative': 'danger'
  }
  return severities[valence] || 'secondary'
}

const getValenceLabel = (valence: string): string => {
  const labels: Record<string, string> = {
    'positive': 'Positiva',
    'very_positive': 'Muy positiva',
    'neutral': 'Neutral',
    'negative': 'Negativa',
    'very_negative': 'Muy negativa'
  }
  return labels[valence] || valence
}

// Actions
const zoomIn = () => {
  if (network.value) {
    const scale = network.value.getScale()
    network.value.moveTo({ scale: scale * 1.3 })
  }
}

const zoomOut = () => {
  if (network.value) {
    const scale = network.value.getScale()
    network.value.moveTo({ scale: scale / 1.3 })
  }
}

const resetView = () => {
  if (network.value) {
    network.value.fit({ animation: true })
  }
}

const updateLayout = () => {
  nextTick(() => {
    initializeGraph()
  })
}

// Watchers
watch(() => props.data, () => {
  if (props.data) {
    relationshipData.value = props.data
    nextTick(() => initializeGraph())
  }
}, { deep: true })

watch(filters, () => {
  nextTick(() => initializeGraph())
}, { deep: true })

// Lifecycle
onMounted(async () => {
  await loadRelationships()
  nextTick(() => initializeGraph())
})

onUnmounted(() => {
  if (network.value) {
    network.value.destroy()
    network.value = null
  }
})
</script>

<style scoped>
.relationship-graph {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-card);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-200);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toolbar-left h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.layout-dropdown {
  width: 140px;
}

.settings-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding: 1rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-200);
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.setting-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color-secondary);
}

.checkbox-group {
  display: flex;
  gap: 1rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.positive-label { color: #10b981; }
.neutral-label { color: #6b7280; }
.negative-label { color: #ef4444; }

.graph-loading,
.graph-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.4;
}

.graph-container {
  flex: 1;
  width: 100%;
  min-height: 400px;
}

.graph-legend {
  display: flex;
  gap: 2rem;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-top: 1px solid var(--surface-200);
}

.legend-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.legend-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.legend-line {
  width: 24px;
  height: 3px;
  border-radius: 2px;
}

.legend-line.positive { background: #10b981; }
.legend-line.neutral { background: #6b7280; }
.legend-line.negative { background: #ef4444; }

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.entity-panel {
  position: absolute;
  top: 60px;
  right: 1rem;
  width: 280px;
  background: var(--surface-card);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  z-index: 10;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-200);
}

.entity-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.entity-title h4 {
  margin: 0;
  font-size: 0.9375rem;
}

.entity-title i {
  color: var(--primary-color);
}

.panel-content {
  padding: 1rem;
  max-height: 350px;
  overflow-y: auto;
}

.relations-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-radius: 4px;
  border-left: 3px solid;
}

.relation-item.relation-positive { border-color: #10b981; }
.relation-item.relation-neutral { border-color: #6b7280; }
.relation-item.relation-negative { border-color: #ef4444; }

.relation-target {
  font-weight: 500;
  font-size: 0.875rem;
}

.relation-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.relation-strength {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.no-relations {
  text-align: center;
  padding: 1rem;
  color: var(--text-color-secondary);
}

.mentions-summary h5 {
  margin: 0 0 0.75rem 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.mention-item {
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.mention-item small {
  font-size: 0.8125rem;
  color: var(--text-color);
  line-height: 1.4;
}
</style>
