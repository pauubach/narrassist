<template>
  <div class="relationship-graph">
    <!-- Toolbar -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h3>Grafo de Relaciones</h3>
        <Tag v-if="stats.totalNodes > 0" severity="info">
          {{ stats.totalNodes }} entidades
        </Tag>
        <Tag v-if="stats.visibleEdges !== stats.totalEdges" severity="warn">
          {{ stats.visibleEdges }}/{{ stats.totalEdges }} relaciones
        </Tag>
        <Tag v-else-if="stats.totalEdges > 0" severity="secondary">
          {{ stats.totalEdges }} relaciones
        </Tag>
        <Tag v-if="graphStore.hasActiveFilters" severity="contrast" class="filter-badge">
          <i class="pi pi-filter"></i>
          {{ graphStore.activeFilterCount }} filtro(s)
        </Tag>
      </div>
      <div class="toolbar-right">
        <Button
          v-tooltip.bottom="'Alejar'"
          icon="pi pi-search-minus"
          text
          rounded
          @click="zoomOut"
        />
        <Button
          v-tooltip.bottom="'Acercar'"
          icon="pi pi-search-plus"
          text
          rounded
          @click="zoomIn"
        />
        <Button
          v-tooltip.bottom="'Restablecer vista'"
          icon="pi pi-refresh"
          text
          rounded
          @click="resetView"
        />
        <Select
          v-model="graphStore.layoutType"
          :options="layoutOptions"
          option-label="label"
          option-value="value"
          placeholder="Layout"
          class="layout-dropdown"
          @change="updateLayout"
        />
        <Button
          v-tooltip.bottom="'Filtros'"
          icon="pi pi-filter"
          text
          rounded
          :severity="graphStore.hasActiveFilters ? 'warn' : undefined"
          @click="showFilters = !showFilters"
        />
        <Button
          v-tooltip.bottom="'Configuracion'"
          icon="pi pi-cog"
          text
          rounded
          @click="showSettings = !showSettings"
        />
      </div>
    </div>

    <!-- Filter Panel -->
    <div v-if="showFilters" class="filter-panel">
      <div class="filter-header">
        <h4>Filtros de relaciones</h4>
        <Button
          v-if="graphStore.hasActiveFilters"
          label="Limpiar filtros"
          icon="pi pi-times"
          text
          size="small"
          @click="graphStore.resetFilters()"
        />
      </div>
      <div class="filter-grid">
        <!-- Filtro por tipo de relacion -->
        <div class="filter-group">
          <label>Tipo de relacion</label>
          <MultiSelect
            v-model="graphStore.filters.relationshipTypes"
            :options="graphStore.relationshipTypeOptions"
            option-label="label"
            option-value="value"
            placeholder="Todos los tipos"
            :max-selected-labels="2"
            display="chip"
            class="filter-select"
          >
            <template #option="{ option }">
              <div class="filter-option">
                <span class="filter-color-dot" :style="{ background: option.color }"></span>
                <i :class="option.icon" class="filter-option-icon"></i>
                <span>{{ option.label }}</span>
              </div>
            </template>
          </MultiSelect>
        </div>

        <!-- Filtro por fuerza -->
        <div class="filter-group">
          <label>Fuerza de la relacion</label>
          <MultiSelect
            v-model="graphStore.filters.strengthLevels"
            :options="graphStore.strengthOptions"
            option-label="label"
            option-value="value"
            placeholder="Todas las fuerzas"
            :max-selected-labels="2"
            display="chip"
            class="filter-select"
          >
            <template #option="{ option }">
              <div class="filter-option">
                <span
                  class="filter-strength-line"
                  :style="{ background: option.color, height: getStrengthLineHeight(option.value) }"
                ></span>
                <span>{{ option.label }}</span>
              </div>
            </template>
          </MultiSelect>
        </div>

        <!-- Filtro por valencia -->
        <div class="filter-group">
          <label>Valencia</label>
          <MultiSelect
            v-model="graphStore.filters.valences"
            :options="graphStore.valenceOptions"
            option-label="label"
            option-value="value"
            placeholder="Todas las valencias"
            :max-selected-labels="3"
            display="chip"
            class="filter-select"
          >
            <template #option="{ option }">
              <div class="filter-option">
                <span
                  class="filter-valence-line"
                  :class="`valence-${option.value.toLowerCase()}`"
                  :style="{ background: option.color }"
                ></span>
                <span>{{ option.label }}</span>
              </div>
            </template>
          </MultiSelect>
        </div>

        <!-- Solo relaciones confirmadas -->
        <div class="filter-group filter-checkbox-group">
          <div class="checkbox-item">
            <Checkbox
              v-model="graphStore.filters.showOnlyConfirmed"
              :binary="true"
              input-id="showOnlyConfirmed"
            />
            <label for="showOnlyConfirmed">Solo relaciones confirmadas</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Settings Panel (configuracion avanzada) -->
    <div v-if="showSettings" class="settings-panel">
      <div class="setting-group">
        <label>Intensidad minima</label>
        <div class="slider-with-value">
          <Slider v-model="graphStore.filters.minStrength" :min="0" :max="1" :step="0.05" class="strength-slider" />
          <span class="slider-value">{{ (graphStore.filters.minStrength * 100).toFixed(0) }}%</span>
        </div>
      </div>
      <div class="setting-group">
        <label>Mostrar clusters</label>
        <ToggleSwitch v-model="graphStore.filters.showClusters" />
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
      <!-- Fila 1: Propiedades de las líneas (Valencia y Fuerza) -->
      <div class="legend-row">
        <div class="legend-section">
          <span class="legend-title">Valencia:</span>
          <div class="legend-item">
            <span class="legend-line legend-line-solid positive"></span>
            <span>Positiva</span>
          </div>
          <div class="legend-item">
            <span class="legend-line legend-line-dashed neutral"></span>
            <span>Neutral</span>
          </div>
          <div class="legend-item">
            <span class="legend-line legend-line-dotted negative"></span>
            <span>Negativa</span>
          </div>
        </div>

        <div class="legend-divider"></div>

        <div class="legend-section">
          <span class="legend-title">Fuerza:</span>
          <div class="legend-item">
            <span class="legend-line-strength strength-weak"></span>
            <span>Débil</span>
          </div>
          <div class="legend-item">
            <span class="legend-line-strength strength-moderate"></span>
            <span>Moderada</span>
          </div>
          <div class="legend-item">
            <span class="legend-line-strength strength-strong"></span>
            <span>Fuerte</span>
          </div>
          <div class="legend-item">
            <span class="legend-line-strength strength-very-strong"></span>
            <span>Muy fuerte</span>
          </div>
        </div>
      </div>

      <!-- Fila 2: Tipos de entidades (nodos) -->
      <div v-if="visibleEntityTypes.length > 0" class="legend-row">
        <div class="legend-section legend-section-entities">
          <span class="legend-title">Entidades:</span>
          <div class="legend-types-grid">
            <div
              v-for="entityType in visibleEntityTypes"
              :key="entityType.type"
              class="legend-item"
            >
              <span class="legend-dot" :style="{ background: entityType.color }"></span>
              <span>{{ entityType.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Fila 3: Tipos de relación (solo si hay tipos diferentes) -->
      <div v-if="visibleRelationshipTypes.length > 0" class="legend-row">
        <div class="legend-section legend-section-types">
          <span class="legend-title">Tipo de relación:</span>
          <div class="legend-types-grid">
            <div
              v-for="typeOption in visibleRelationshipTypes"
              :key="typeOption.value"
              class="legend-item"
            >
              <span class="legend-dot" :style="{ background: typeOption.color }"></span>
              <span>{{ typeOption.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Fila 4: Clusters (si están habilitados) -->
      <div v-if="graphStore.filters.showClusters && clusters.length > 0" class="legend-row">
        <div class="legend-section legend-section-clusters">
          <span class="legend-title">Clusters:</span>
          <div class="legend-types-grid">
            <div
              v-for="cluster in clusters.slice(0, 5)"
              :key="cluster.id"
              v-tooltip.top="'Clic para renombrar'"
              class="legend-item legend-item-clickable"
              @click="openClusterRenameDialog(cluster)"
            >
              <span class="legend-dot" :style="{ background: cluster.color }"></span>
              <span>{{ cluster.label || `Grupo ${cluster.id}` }}</span>
              <i class="pi pi-pencil legend-edit-icon"></i>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cluster Rename Dialog -->
    <Dialog
      :visible="showClusterRenameDialog"
      :header="`Renombrar cluster: ${editingCluster?.label || ''}`"
      :modal="true"
      :closable="true"
      :style="{ width: '400px' }"
      @update:visible="showClusterRenameDialog = $event"
    >
      <div class="cluster-rename-form">
        <div class="form-field">
          <label for="clusterName">Nombre personalizado</label>
          <InputText
            id="clusterName"
            v-model="newClusterName"
            placeholder="Ej: Familia Pérez, Grupo del trabajo..."
            class="w-full"
            @keyup.enter="saveClusterName"
          />
          <small class="form-hint">
            Nombre original: {{ editingCluster?.name || 'N/A' }}
          </small>
        </div>

        <div v-if="editingCluster" class="cluster-info">
          <h5>Información del cluster</h5>
          <ul>
            <li><strong>Miembros:</strong> {{ editingCluster.entity_names?.join(', ') || 'N/A' }}</li>
            <li><strong>Personaje central:</strong> {{ editingCluster.centroid_entity_name || 'N/A' }}</li>
            <li><strong>Cohesión:</strong> {{ Math.round((editingCluster.cohesion_score || 0) * 100) }}%</li>
          </ul>
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="showClusterRenameDialog = false" />
        <Button label="Restaurar nombre" severity="secondary" @click="resetClusterName" />
        <Button label="Guardar" @click="saveClusterName" />
      </template>
    </Dialog>

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
          <h5>Apariciones recientes</h5>
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
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Slider from 'primevue/slider'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressSpinner from 'primevue/progressspinner'
import Divider from 'primevue/divider'
import MultiSelect from 'primevue/multiselect'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { apiUrl } from '@/config/api'
import {
  useRelationshipGraphStore,
  type RelationshipValence,
  type RelationshipType
} from '@/stores/relationshipGraph'

// Store para persistir filtros
const graphStore = useRelationshipGraphStore()

interface RelationshipData {
  relations: Array<{
    // Backend puede enviar entity1_id/entity2_id o source_id/target_id
    source_id?: number
    target_id?: number
    entity1_id?: number
    entity2_id?: number
    // Strength puede ser string (nombre) o number
    strength: string | number
    valence: string
    // Backend envía confidence en lugar de evidence_count
    evidence_count?: number
    confidence?: number
    cooccurrence_score?: number
    relation_type?: string
    confirmed?: boolean
  }>
  clusters: Array<{
    id: number
    name: string
    display_name: string
    custom_name?: string | null
    entity_ids: number[]
    entity_names: string[]
    centroid_entity_id?: number | null
    centroid_entity_name?: string | null
    cohesion_score: number
    detection_method: string
    chapters_active: number[]
    member_count: number
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
    mentionCount?: number
  }>
}

const props = defineProps<{
  projectId: number
  data?: RelationshipData | null
}>()

const emit = defineEmits<{
  entitySelect: [entityId: number]
  relationSelect: [sourceId: number, targetId: number]
  clusterRename: [clusterId: number, customName: string | null]
}>()

// Refs
const graphContainer = ref<HTMLElement | null>(null)
const network = ref<Network | null>(null)
const loading = ref(false)
const showSettings = ref(false)
const showFilters = ref(false)
const selectedEntity = ref<{ id: number; label: string; type: string } | null>(null)

// Cluster rename dialog
const showClusterRenameDialog = ref(false)
const editingCluster = ref<typeof clusters.value[0] | null>(null)
const newClusterName = ref('')

// Nombres personalizados de clusters (almacenados localmente)
const customClusterNames = ref<Map<number, string>>(new Map())

// Data
const relationshipData = ref<RelationshipData | null>(null)

// Posiciones de nodos para mantener layout estable al filtrar
const nodePositions = ref<Map<number, { x: number; y: number }>>(new Map())

// =============================================================================
// Funciones para Convex Hull de Clusters
// =============================================================================

/**
 * Calcula el convex hull (casco convexo) de un conjunto de puntos.
 * Usa el algoritmo de Graham Scan para encontrar el polígono más pequeño
 * que envuelve todos los puntos.
 */
function computeConvexHull(points: Array<{ x: number; y: number }>): Array<{ x: number; y: number }> {
  if (points.length < 3) return points

  // Encontrar el punto más abajo (y menor y, en caso de empate menor x)
  let start = points[0]
  for (const p of points) {
    if (p.y < start.y || (p.y === start.y && p.x < start.x)) {
      start = p
    }
  }

  // Ordenar puntos por ángulo polar respecto al punto de inicio
  const sorted = points
    .filter(p => p !== start)
    .sort((a, b) => {
      const angleA = Math.atan2(a.y - start.y, a.x - start.x)
      const angleB = Math.atan2(b.y - start.y, b.x - start.x)
      return angleA - angleB
    })

  // Construir el hull
  const hull = [start]
  for (const p of sorted) {
    while (hull.length > 1) {
      const top = hull[hull.length - 1]
      const nextToTop = hull[hull.length - 2]
      const cross = (top.x - nextToTop.x) * (p.y - nextToTop.y) - (top.y - nextToTop.y) * (p.x - nextToTop.x)
      if (cross <= 0) {
        hull.pop()
      } else {
        break
      }
    }
    hull.push(p)
  }

  return hull
}

/**
 * Genera puntos alrededor del perímetro de un nodo (círculo).
 * Esto permite que el convex hull tenga en cuenta el área completa del nodo,
 * no solo su centro.
 */
function generateNodePerimeterPoints(
  center: { x: number; y: number },
  radius: number,
  numPoints: number = 8
): Array<{ x: number; y: number }> {
  const points: Array<{ x: number; y: number }> = []
  for (let i = 0; i < numPoints; i++) {
    const angle = (2 * Math.PI * i) / numPoints
    points.push({
      x: center.x + radius * Math.cos(angle),
      y: center.y + radius * Math.sin(angle)
    })
  }
  return points
}

/**
 * Expande el hull añadiendo un margen uniforme.
 */
function expandHull(
  hull: Array<{ x: number; y: number }>,
  padding: number
): Array<{ x: number; y: number }> {
  if (hull.length < 3) return hull

  // Calcular el centroide
  const centroid = hull.reduce(
    (acc, p) => ({ x: acc.x + p.x / hull.length, y: acc.y + p.y / hull.length }),
    { x: 0, y: 0 }
  )

  // Expandir cada punto alejándolo del centroide
  return hull.map(p => {
    const dx = p.x - centroid.x
    const dy = p.y - centroid.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist === 0) return p
    const scale = (dist + padding) / dist
    return {
      x: centroid.x + dx * scale,
      y: centroid.y + dy * scale
    }
  })
}

/**
 * Genera puntos intermedios usando interpolación Catmull-Rom para curvas más suaves.
 * Esto crea una forma orgánica sin angulosidades.
 */
function catmullRomSpline(
  points: Array<{ x: number; y: number }>,
  _tension: number = 0.5,
  segments: number = 20
): Array<{ x: number; y: number }> {
  if (points.length < 3) return points

  const result: Array<{ x: number; y: number }> = []
  const n = points.length

  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n]
    const p1 = points[i]
    const p2 = points[(i + 1) % n]
    const p3 = points[(i + 2) % n]

    for (let t = 0; t < segments; t++) {
      const s = t / segments
      const s2 = s * s
      const s3 = s2 * s

      const x =
        0.5 *
        ((2 * p1.x) +
          (-p0.x + p2.x) * s +
          (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * s2 +
          (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * s3)

      const y =
        0.5 *
        ((2 * p1.y) +
          (-p0.y + p2.y) * s +
          (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * s2 +
          (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * s3)

      result.push({ x, y })
    }
  }

  return result
}

/**
 * Suaviza un hull usando el algoritmo de Chaikin para crear curvas suaves.
 * Este algoritmo "corta las esquinas" iterativamente para crear una curva más orgánica.
 */
function chaikinSmooth(
  hull: Array<{ x: number; y: number }>,
  iterations: number = 3
): Array<{ x: number; y: number }> {
  let result = [...hull]

  for (let iter = 0; iter < iterations; iter++) {
    const newResult: Array<{ x: number; y: number }> = []
    const n = result.length

    for (let i = 0; i < n; i++) {
      const p0 = result[i]
      const p1 = result[(i + 1) % n]

      // Punto a 1/4 del segmento
      newResult.push({
        x: 0.75 * p0.x + 0.25 * p1.x,
        y: 0.75 * p0.y + 0.25 * p1.y
      })

      // Punto a 3/4 del segmento
      newResult.push({
        x: 0.25 * p0.x + 0.75 * p1.x,
        y: 0.25 * p0.y + 0.75 * p1.y
      })
    }

    result = newResult
  }

  return result
}

/**
 * Dibuja el fondo de un cluster en el canvas.
 * Crea una forma suave y orgánica usando splines Catmull-Rom que envuelve los nodos del cluster.
 */
function drawClusterBackground(
  ctx: CanvasRenderingContext2D,
  hull: Array<{ x: number; y: number }>,
  fillColor: string,
  borderColor: string,
  label: string
) {
  if (hull.length < 3) return

  ctx.save()

  // Suavizar el hull usando el algoritmo de Chaikin (corta esquinas)
  const smoothedHull = chaikinSmooth(hull, 4)

  // Aplicar Catmull-Rom splines para curvas aún más suaves
  const smoothPoints = catmullRomSpline(smoothedHull, 0.5, 10)

  // Dibujar la forma suave
  ctx.beginPath()
  if (smoothPoints.length > 0) {
    ctx.moveTo(smoothPoints[0].x, smoothPoints[0].y)
    for (let i = 1; i < smoothPoints.length; i++) {
      ctx.lineTo(smoothPoints[i].x, smoothPoints[i].y)
    }
  }
  ctx.closePath()

  // Relleno semitransparente
  ctx.fillStyle = fillColor
  ctx.fill()

  // Borde sutil
  ctx.strokeStyle = borderColor
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])
  ctx.stroke()

  // Etiqueta del cluster en la parte superior
  const topPoint = hull.reduce((min, p) => (p.y < min.y ? p : min), hull[0])
  ctx.setLineDash([])
  ctx.font = 'bold 12px Inter, system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.fillStyle = borderColor
  ctx.fillText(label, topPoint.x, topPoint.y - 15)

  ctx.restore()
}

// =============================================================================
// Funciones de normalizacion para mapear valores del backend a tipos del store

/**
 * Normaliza los datos de una relación del backend al formato del frontend.
 * El backend puede enviar entity1_id/entity2_id o source_id/target_id,
 * y strength puede ser string ("STRONG") o number (0.75).
 */
interface NormalizedRelation {
  source_id: number
  target_id: number
  strength: number
  valence: string
  evidence_count: number
  relation_type?: string
  confirmed?: boolean
}

const normalizeRelation = (rel: RelationshipData['relations'][0]): NormalizedRelation => {
  // Normalizar IDs
  const source_id = rel.source_id ?? rel.entity1_id ?? 0
  const target_id = rel.target_id ?? rel.entity2_id ?? 0

  // Normalizar strength (puede ser string o number)
  let strengthNum: number
  if (typeof rel.strength === 'number') {
    strengthNum = rel.strength
  } else if (rel.strength) {
    // Convertir nombre de strength a valor numérico
    const strengthMapping: Record<string, number> = {
      'WEAK': 0.25,
      'MODERATE': 0.5,
      'STRONG': 0.75,
      'VERY_STRONG': 0.95
    }
    strengthNum = strengthMapping[rel.strength.toUpperCase()] ?? 0.5
  } else {
    // Default si no hay strength
    strengthNum = 0.5
  }

  // Usar cooccurrence_score o confidence como strength adicional si no hay valor
  if (strengthNum === 0.5 && rel.cooccurrence_score) {
    strengthNum = Math.min(1, rel.cooccurrence_score)
  }

  // Normalizar evidence_count
  const evidence_count = rel.evidence_count ?? Math.round((rel.confidence ?? 0.5) * 10)

  return {
    source_id,
    target_id,
    strength: strengthNum,
    valence: rel.valence?.toLowerCase() ?? 'neutral',
    evidence_count,
    relation_type: rel.relation_type,
    confirmed: rel.confirmed
  }
}

const normalizeValence = (valence: string): RelationshipValence => {
  const mapping: Record<string, RelationshipValence> = {
    'positive': 'POSITIVE',
    'very_positive': 'POSITIVE',
    'negative': 'NEGATIVE',
    'very_negative': 'NEGATIVE',
    'neutral': 'NEUTRAL'
  }
  return mapping[valence.toLowerCase()] || 'NEUTRAL'
}

const normalizeRelationshipType = (type?: string): RelationshipType | null => {
  if (!type) return null

  const mapping: Record<string, RelationshipType> = {
    'family': 'FAMILY',
    'familiar': 'FAMILY',
    'romantic': 'ROMANTIC',
    'romantico': 'ROMANTIC',
    'friend': 'FRIENDSHIP',
    'friendship': 'FRIENDSHIP',
    'amistad': 'FRIENDSHIP',
    'professional': 'PROFESSIONAL',
    'profesional': 'PROFESSIONAL',
    'rival': 'RIVALRY',
    'rivalry': 'RIVALRY',
    'rivalidad': 'RIVALRY',
    'ally': 'ALLY',
    'aliado': 'ALLY',
    'mentor': 'MENTOR',
    'enemy': 'ENEMY',
    'enemigo': 'ENEMY',
    'neutral': 'NEUTRAL'
  }
  return mapping[type.toLowerCase()] || null
}

// Helper para altura de linea en filtro de fuerza
const getStrengthLineHeight = (strength: string): string => {
  const heights: Record<string, string> = {
    'WEAK': '2px',
    'MODERATE': '3px',
    'STRONG': '4px',
    'VERY_STRONG': '6px'
  }
  return heights[strength] || '2px'
}
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

// Paleta de colores para clusters (distinguibles y semitransparentes)
const CLUSTER_COLORS = [
  { fill: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6' },   // Blue
  { fill: 'rgba(16, 185, 129, 0.15)', border: '#10b981' },   // Emerald
  { fill: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b' },   // Amber
  { fill: 'rgba(139, 92, 246, 0.15)', border: '#8b5cf6' },   // Violet
  { fill: 'rgba(236, 72, 153, 0.15)', border: '#ec4899' },   // Pink
  { fill: 'rgba(6, 182, 212, 0.15)', border: '#06b6d4' },    // Cyan
  { fill: 'rgba(132, 204, 22, 0.15)', border: '#84cc16' },   // Lime
  { fill: 'rgba(249, 115, 22, 0.15)', border: '#f97316' },   // Orange
]

const clusters = computed(() => {
  const data = props.data || relationshipData.value
  if (!data?.clusters) return []

  return data.clusters.map((c, idx) => {
    const colorPair = CLUSTER_COLORS[idx % CLUSTER_COLORS.length]
    // Prioridad: nombre personalizado local > custom_name del backend (solo si es corto)
    const localCustomName = customClusterNames.value.get(c.id)

    // SIEMPRE generar nombre basado en el personaje principal del cluster
    // Esto evita mostrar listas largas como "María Sánchez, Juan Pérez y Madrid"
    let generatedLabel = `Grupo ${c.id}`
    if (c.entity_ids?.length > 0 && data.entities) {
      // Encontrar la entidad principal del cluster:
      // 1. Usar centroid_entity_name si existe
      // 2. Si no, buscar la entidad con más menciones
      if (c.centroid_entity_name) {
        // Extraer solo el primer nombre si hay apellido
        const firstName = c.centroid_entity_name.split(' ')[0]
        generatedLabel = `Entorno de ${firstName}`
      } else {
        const clusterEntities = data.entities.filter(e => c.entity_ids.includes(e.id))
        if (clusterEntities.length > 0) {
          // Encontrar entidad con más menciones
          const mainEntity = clusterEntities.reduce((prev, curr) =>
            (curr.mentionCount || 0) > (prev.mentionCount || 0) ? curr : prev
          )
          // Extraer solo el primer nombre para mantenerlo breve
          const firstName = mainEntity.name.split(' ')[0]
          generatedLabel = `Entorno de ${firstName}`
        }
      }
    }

    // Usar nombre personalizado si existe, sino siempre usar el generado
    // Ignorar display_name y name del backend ya que suelen ser listas largas
    const displayLabel = localCustomName || (c.custom_name && c.custom_name.length < 25 ? c.custom_name : null) || generatedLabel

    return {
      ...c,
      label: displayLabel,
      color: colorPair.border,
      fillColor: colorPair.fill,
      borderColor: colorPair.border
    }
  })
})

const stats = computed(() => {
  const data = props.data || relationshipData.value
  const totalEdges = data?.relations?.length || 0

  // Contar relaciones visibles aplicando filtros
  let visibleEdges = totalEdges
  if (data?.relations) {
    // Normalizar relaciones primero
    const normalized = data.relations.map(normalizeRelation)
    visibleEdges = normalized.filter(rel => {
      const storeFilters = graphStore.filters
      if (rel.strength < storeFilters.minStrength) return false
      if (storeFilters.valences.length > 0) {
        const relValence = normalizeValence(rel.valence)
        if (!storeFilters.valences.includes(relValence)) return false
      }
      if (storeFilters.relationshipTypes.length > 0) {
        const relType = normalizeRelationshipType(rel.relation_type)
        if (relType && !storeFilters.relationshipTypes.includes(relType)) return false
      }
      if (storeFilters.strengthLevels.length > 0) {
        const strengthLevel = graphStore.strengthValueToLevel(rel.strength)
        if (!storeFilters.strengthLevels.includes(strengthLevel)) return false
      }
      if (storeFilters.showOnlyConfirmed && !rel.confirmed) return false
      return true
    }).length
  }

  return {
    totalNodes: data?.entities?.length || 0,
    totalEdges,
    visibleEdges
  }
})

// Tipos de relacion visibles en la leyenda (los que estan en uso o seleccionados)
const visibleRelationshipTypes = computed(() => {
  const data = props.data || relationshipData.value
  if (!data?.relations) return graphStore.relationshipTypeOptions.slice(0, 5)

  // Obtener tipos unicos de las relaciones actuales
  const typesInUse = new Set<string>()
  data.relations.forEach(rel => {
    if (rel.relation_type) {
      const normalized = normalizeRelationshipType(rel.relation_type)
      if (normalized) typesInUse.add(normalized)
    }
  })

  // Filtrar opciones para mostrar solo las que estan en uso
  if (typesInUse.size > 0) {
    return graphStore.relationshipTypeOptions.filter(opt => typesInUse.has(opt.value))
  }

  // Si no hay tipos, mostrar los primeros 5
  return graphStore.relationshipTypeOptions.slice(0, 5)
})

// Tipos de entidades visibles en la leyenda (los que están en uso)
const visibleEntityTypes = computed(() => {
  const data = props.data || relationshipData.value
  if (!data?.entities) return []

  // Obtener tipos únicos de las entidades actuales
  const typesInUse = new Map<string, { type: string; label: string; color: string }>()
  data.entities.forEach(entity => {
    const normalizedType = entity.type?.toUpperCase() || 'OTHER'
    if (!typesInUse.has(normalizedType)) {
      typesInUse.set(normalizedType, {
        type: normalizedType,
        label: getEntityTypeLabel(normalizedType),
        color: getEntityColor(normalizedType)
      })
    }
  })

  return Array.from(typesInUse.values())
})

const selectedEntityRelations = computed(() => {
  if (!selectedEntity.value) return []
  const data = props.data || relationshipData.value
  if (!data?.relations) return []

  const entityId = selectedEntity.value.id
  // Normalizar las relaciones primero
  const normalizedRels = data.relations.map(normalizeRelation)

  return normalizedRels
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
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/relationships`))
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

  // Verificar que entities existe
  if (!data.entities || !Array.isArray(data.entities)) {
    console.warn('RelationshipGraph: data.entities is missing or not an array')
    return
  }

  // Debug: mostrar datos recibidos
  console.log('RelationshipGraph: Initializing with data:', {
    entitiesCount: data.entities?.length || 0,
    relationsCount: data.relations?.length || 0,
    relations: data.relations?.slice(0, 3) // Primeras 3 para debug
  })

  // Crear set de IDs de entidades válidos para validar edges
  const validEntityIds = new Set(data.entities.map(e => e.id))

  // Normalizar todas las relaciones al formato del frontend
  const normalizedRelations = (data.relations || []).map(normalizeRelation)

  console.log('RelationshipGraph: Normalized relations:', {
    count: normalizedRelations.length,
    sample: normalizedRelations.slice(0, 3)
  })

  // PRIMERO: Filtrar relaciones antes de crear nodos
  // Esto permite mostrar solo los nodos que tienen relaciones visibles
  const filteredRelations = normalizedRelations.filter(rel => {
    const storeFilters = graphStore.filters

    // Validar que tanto source como target existen en las entidades
    if (!validEntityIds.has(rel.source_id) || !validEntityIds.has(rel.target_id)) {
      console.warn('RelationshipGraph: Skipping edge with invalid entity ID:', rel)
      return false
    }

    // Filtrar por intensidad minima
    if (rel.strength < storeFilters.minStrength) return false

    // Filtrar por valencia
    if (storeFilters.valences.length > 0) {
      const relValence = normalizeValence(rel.valence)
      if (!storeFilters.valences.includes(relValence)) return false
    }

    // Filtrar por tipo de relacion
    if (storeFilters.relationshipTypes.length > 0) {
      const relType = normalizeRelationshipType(rel.relation_type)
      if (relType && !storeFilters.relationshipTypes.includes(relType)) return false
    }

    // Filtrar por fuerza
    if (storeFilters.strengthLevels.length > 0) {
      const strengthLevel = graphStore.strengthValueToLevel(rel.strength)
      if (!storeFilters.strengthLevels.includes(strengthLevel)) return false
    }

    // Filtrar solo relaciones confirmadas
    if (storeFilters.showOnlyConfirmed && !rel.confirmed) return false

    return true
  })

  console.log('RelationshipGraph: After filtering:', {
    filteredRelationsCount: filteredRelations.length,
    filters: graphStore.filters
  })

  // SEGUNDO: Mostrar TODAS las entidades siempre
  // Los filtros de relaciones solo afectan a las relaciones visibles, no a los nodos
  // Esto permite ver el grafo completo aunque algunas relaciones estén filtradas
  const visibleEntities = data.entities

  // TERCERO: Crear nodos solo para entidades visibles
  const maxMentions = Math.max(...visibleEntities.map(e => e.mentionCount || 1), 1)

  // Función para generar tooltip enriquecido
  const buildNodeTooltip = (entity: typeof data.entities[0], cluster: typeof clusters.value[0] | undefined): string => {
    const lines: string[] = [
      `📌 ${entity.name}`,
      `Tipo: ${getEntityTypeLabel(entity.type)}`,
      `Apariciones: ${entity.mentionCount || 1}`
    ]

    if (cluster) {
      lines.push('')  // Línea vacía para separar
      lines.push(`📊 Cluster: ${cluster.label}`)
      if (cluster.centroid_entity_name && cluster.centroid_entity_id === entity.id) {
        lines.push('⭐ Personaje central del grupo')
      }
      lines.push(`Miembros: ${cluster.member_count}`)
      lines.push(`Cohesión: ${Math.round((cluster.cohesion_score || 0) * 100)}%`)
      if (cluster.chapters_active && cluster.chapters_active.length > 0) {
        lines.push(`Capítulos: ${cluster.chapters_active.join(', ')}`)
      }
    }

    return lines.join('\n')
  }

  const nodes = new DataSet<Node>(
    visibleEntities.map(entity => {
      const cluster = clusters.value.find(c => c.entity_ids?.includes(entity.id))
      // Usar color del tipo de entidad (no del cluster) para mantener consistencia con badges
      const nodeColor = getEntityColor(entity.type)
      const mentions = entity.mentionCount || 1
      // Tamaño proporcional a menciones (min 15, max 45)
      const nodeSize = 15 + (mentions / maxMentions) * 30

      return {
        id: entity.id,
        label: entity.name,
        title: buildNodeTooltip(entity, cluster),
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
          size: Math.max(12, nodeSize * 0.4)
        },
        size: nodeSize,
        shape: getNodeShape(entity.type),
        group: cluster?.id?.toString()
      }
    }) as Node[]
  )

  // CUARTO: Crear edges
  const edgeData = filteredRelations.map((rel, idx) => {
    const color = getEdgeColor(rel.valence, rel.relation_type)
    const valenceLabel = getValenceLabel(rel.valence)
    const edgeWidth = Math.max(2, graphStore.getEdgeWidthForStrength(rel.strength))

    return {
      id: `edge-${idx}`,
      from: rel.source_id,
      to: rel.target_id,
      // Solo mostrar etiqueta si tiene valencia conocida y no vacía
      label: valenceLabel || undefined,
      title: `Intensidad: ${(rel.strength * 100).toFixed(0)}%${valenceLabel ? `\nValencia: ${valenceLabel}` : ''}${rel.evidence_count ? `\nEvidencias: ${rel.evidence_count}` : ''}${rel.relation_type ? `\nTipo: ${rel.relation_type}` : ''}`,
      color: {
        color: color,
        highlight: color,
        hover: color
      },
      width: edgeWidth,
      dashes: graphStore.getEdgeDashForValence(rel.valence),
      smooth: {
        enabled: true,
        type: 'continuous' as const,
        roundness: 0.5
      }
    }
  })

  console.log('RelationshipGraph: Creating edges:', {
    edgeCount: edgeData.length,
    sampleEdges: edgeData.slice(0, 3)
  })

  const edges = new DataSet<Edge>(edgeData as Edge[])

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
      shadow: true,
      width: 2,
      color: {
        color: '#6b7280',
        highlight: '#3b82f6',
        hover: '#3b82f6'
      },
      selectionWidth: 2,
      hoverWidth: 1.5
    },
    physics: getPhysicsOptions(),
    interaction: {
      hover: true,
      tooltipDelay: 200,
      navigationButtons: false,
      keyboard: true,
      zoomView: true,
      dragView: true,
      hideEdgesOnDrag: false,
      hideEdgesOnZoom: false
    },
    layout: getLayoutOptions()
  }

  // Destroy existing network
  if (network.value) {
    network.value.destroy()
  }

  console.log('RelationshipGraph: Creating network with:', {
    nodesCount: nodes.length,
    edgesCount: edges.length,
    nodeIds: nodes.getIds().slice(0, 5),
    edgeIds: edges.getIds().slice(0, 5)
  })

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

  // Dibujar fondos de clusters si está habilitado
  if (graphStore.filters.showClusters && clusters.value.length > 0 && visibleEntities.length > 0) {
    network.value.on('beforeDrawing', (ctx: CanvasRenderingContext2D) => {
      // Obtener posiciones actuales de todos los nodos
      const positions = network.value?.getPositions()
      if (!positions) return

      // Dibujar cada cluster
      for (const cluster of clusters.value) {
        if (!cluster.entity_ids || cluster.entity_ids.length < 2) continue

        // Generar puntos del perímetro de cada nodo del cluster
        // Esto asegura que el hull envuelva el ÁREA de los nodos, no solo sus centros
        const allPerimeterPoints: Array<{ x: number; y: number }> = []

        for (const entityId of cluster.entity_ids) {
          const pos = positions[entityId]
          if (pos) {
            // Calcular tamaño del nodo para este entityId
            const entity = data.entities.find(e => e.id === entityId)
            const mentions = entity?.mentionCount || 1
            // Usar maxMentions de todas las entidades para consistencia
            const allMaxMentions = Math.max(...data.entities.map(e => e.mentionCount || 1), 1)
            const nodeSize = 15 + (mentions / allMaxMentions) * 30

            // Generar puntos alrededor del perímetro del nodo
            // Añadir un pequeño margen (10px) para que la curva no toque el nodo
            const perimeterPoints = generateNodePerimeterPoints(
              { x: pos.x, y: pos.y },
              nodeSize + 15,  // radio del nodo + margen
              8  // 8 puntos por nodo
            )
            allPerimeterPoints.push(...perimeterPoints)
          }
        }

        if (allPerimeterPoints.length < 3) continue

        // Calcular el convex hull usando todos los puntos del perímetro
        const hull = computeConvexHull(allPerimeterPoints)

        // Expandir más para dar espacio visual y curvas más suaves
        const expandedHull = expandHull(hull, 35)

        // Dibujar el fondo del cluster
        drawClusterBackground(
          ctx,
          expandedHull,
          cluster.fillColor,
          cluster.borderColor,
          cluster.label
        )
      }
    })
  }
}

const getPhysicsOptions = () => {
  if (graphStore.layoutType === 'hierarchical') {
    return { enabled: false }
  }

  return {
    enabled: true,
    solver: graphStore.layoutType === 'forceAtlas2Based' ? 'forceAtlas2Based' : 'barnesHut',
    forceAtlas2Based: {
      gravitationalConstant: -100,
      centralGravity: 0.005,
      springLength: 250,
      springConstant: 0.05,
      damping: 0.4,
      avoidOverlap: 1
    },
    barnesHut: {
      gravitationalConstant: -3000,
      centralGravity: 0.1,
      springLength: 200,
      springConstant: 0.04,
      damping: 0.09,
      avoidOverlap: 1
    },
    stabilization: {
      enabled: true,
      iterations: 300,
      updateInterval: 25
    }
  }
}

const getLayoutOptions = () => {
  if (graphStore.layoutType === 'hierarchical') {
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

  if (graphStore.layoutType === 'circular') {
    return {
      improvedLayout: true
    }
  }

  return {
    improvedLayout: true,
    randomSeed: 42
  }
}

/**
 * Obtiene el color de entidad desde las variables CSS del design system.
 * Los colores coinciden con los badges de tipo de entidad para mantener consistencia.
 */
const getEntityColor = (type: string): string => {
  // Mapeo de tipos de entidad a variables CSS del design system
  const typeToVar: Record<string, string> = {
    'CHARACTER': '--ds-entity-character',
    'character': '--ds-entity-character',
    'LOCATION': '--ds-entity-location',
    'location': '--ds-entity-location',
    'ORGANIZATION': '--ds-entity-organization',
    'organization': '--ds-entity-organization',
    'OBJECT': '--ds-entity-object',
    'object': '--ds-entity-object',
    'EVENT': '--ds-entity-event',
    'event': '--ds-entity-event',
    'ANIMAL': '--ds-entity-animal',
    'animal': '--ds-entity-animal',
    'CREATURE': '--ds-entity-creature',
    'creature': '--ds-entity-creature',
    'BUILDING': '--ds-entity-building',
    'building': '--ds-entity-building',
    'REGION': '--ds-entity-region',
    'region': '--ds-entity-region',
    'VEHICLE': '--ds-entity-vehicle',
    'vehicle': '--ds-entity-vehicle',
    'FACTION': '--ds-entity-faction',
    'faction': '--ds-entity-faction',
    'FAMILY': '--ds-entity-family',
    'family': '--ds-entity-family',
    'TIME_PERIOD': '--ds-entity-time-period',
    'time_period': '--ds-entity-time-period',
    'CONCEPT': '--ds-entity-concept',
    'concept': '--ds-entity-concept',
    'RELIGION': '--ds-entity-religion',
    'religion': '--ds-entity-religion',
    'MAGIC_SYSTEM': '--ds-entity-magic-system',
    'magic_system': '--ds-entity-magic-system',
    'WORK': '--ds-entity-work',
    'work': '--ds-entity-work',
    'TITLE': '--ds-entity-title',
    'title': '--ds-entity-title',
    'LANGUAGE': '--ds-entity-language',
    'language': '--ds-entity-language',
    'OTHER': '--ds-entity-other',
    'other': '--ds-entity-other'
  }

  const cssVar = typeToVar[type]
  if (cssVar) {
    // Obtener el valor computed de la variable CSS
    const computedColor = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim()
    if (computedColor) return computedColor
  }

  // Fallback si no hay variable CSS
  return getComputedStyle(document.documentElement).getPropertyValue('--ds-entity-other').trim() || '#616161'
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

/**
 * Obtiene la etiqueta traducida para un tipo de entidad.
 */
const getEntityTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'CHARACTER': 'Personaje',
    'character': 'Personaje',
    'LOCATION': 'Lugar',
    'location': 'Lugar',
    'ORGANIZATION': 'Organización',
    'organization': 'Organización',
    'OBJECT': 'Objeto',
    'object': 'Objeto',
    'EVENT': 'Evento',
    'event': 'Evento',
    'ANIMAL': 'Animal',
    'animal': 'Animal',
    'CREATURE': 'Criatura',
    'creature': 'Criatura',
    'BUILDING': 'Edificio',
    'building': 'Edificio',
    'REGION': 'Región',
    'region': 'Región',
    'VEHICLE': 'Vehículo',
    'vehicle': 'Vehículo',
    'FACTION': 'Facción',
    'faction': 'Facción',
    'FAMILY': 'Familia',
    'family': 'Familia',
    'TIME_PERIOD': 'Período',
    'time_period': 'Período',
    'CONCEPT': 'Concepto',
    'concept': 'Concepto',
    'OTHER': 'Otro',
    'other': 'Otro'
  }
  return labels[type] || type
}

const getEdgeColor = (valence: string, relationType?: string): string => {
  // Si hay tipo de relacion, usar color del tipo
  if (relationType) {
    const normalizedType = normalizeRelationshipType(relationType)
    if (normalizedType) {
      return graphStore.getRelationshipTypeColor(normalizedType)
    }
  }

  // Fallback a colores por valencia
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
    'very_negative': 'Muy negativa',
    'unknown': ''  // No mostrar etiqueta para valencia desconocida
  }
  return labels[valence.toLowerCase()] || ''
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

// =============================================================================
// Cluster Rename Functions
// =============================================================================

/**
 * Abre el diálogo para renombrar un cluster.
 */
const openClusterRenameDialog = (cluster: typeof clusters.value[0]) => {
  editingCluster.value = cluster
  // Usar el nombre personalizado si existe, sino el nombre actual
  newClusterName.value = customClusterNames.value.get(cluster.id) || cluster.custom_name || ''
  showClusterRenameDialog.value = true
}

/**
 * Guarda el nombre personalizado del cluster.
 */
const saveClusterName = async () => {
  if (!editingCluster.value) return

  const clusterId = editingCluster.value.id
  const name = newClusterName.value.trim()

  if (name) {
    customClusterNames.value.set(clusterId, name)
  } else {
    customClusterNames.value.delete(clusterId)
  }

  // Emitir evento para que el padre pueda persistir el cambio si es necesario
  emit('clusterRename', clusterId, name || null)

  showClusterRenameDialog.value = false
  editingCluster.value = null
  newClusterName.value = ''

  // Reinicializar el grafo para reflejar el nuevo nombre
  nextTick(() => initializeGraph())
}

/**
 * Restaura el nombre original del cluster (elimina el custom_name).
 */
const resetClusterName = () => {
  if (!editingCluster.value) return

  customClusterNames.value.delete(editingCluster.value.id)
  newClusterName.value = ''

  emit('clusterRename', editingCluster.value.id, null)

  showClusterRenameDialog.value = false
  editingCluster.value = null

  nextTick(() => initializeGraph())
}

// Guardar posiciones de nodos para mantener layout estable al filtrar
const saveNodePositions = () => {
  if (!network.value) return

  const positions = network.value.getPositions()
  nodePositions.value.clear()

  for (const [nodeId, pos] of Object.entries(positions)) {
    nodePositions.value.set(Number(nodeId), pos as { x: number; y: number })
  }
}

// Watchers - Optimizados para evitar recálculos innecesarios
// Solo reaccionar a cambios significativos, no deep watch completo
watch(
  () => [props.data?.entities?.length, props.data?.relations?.length],
  ([newEntLen, newRelLen], [oldEntLen, oldRelLen]) => {
    // Solo reinicializar si cambió el número de entidades o relaciones
    if (props.data && (newEntLen !== oldEntLen || newRelLen !== oldRelLen)) {
      relationshipData.value = props.data
      nextTick(() => initializeGraph())
    }
  }
)

// Para filtros, usar JSON.stringify para comparación superficial
let lastFiltersJson = ''
watch(
  () => graphStore.filters,
  (newFilters) => {
    const filtersJson = JSON.stringify(newFilters)
    if (filtersJson !== lastFiltersJson) {
      lastFiltersJson = filtersJson
      // Guardar posiciones actuales antes de reinicializar
      saveNodePositions()
      nextTick(() => initializeGraph())
    }
  },
  { deep: true }
)

watch(() => graphStore.layoutType, () => {
  nextTick(() => initializeGraph())
})

// Lifecycle
onMounted(async () => {
  await loadRelationships()
  nextTick(() => initializeGraph())
})

onUnmounted(() => {
  // Limpiar network y liberar memoria de DataSets
  if (network.value) {
    // Remover event listeners primero
    network.value.off('selectNode')
    network.value.off('deselectNode')
    network.value.off('selectEdge')
    network.value.off('beforeDrawing')
    // Destruir la red
    network.value.destroy()
    network.value = null
  }
  // Limpiar caches y posiciones guardadas
  nodePositions.value.clear()
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

.type-filter {
  width: 200px;
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

/* Filter Panel */
.filter-panel {
  padding: 1rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-200);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.filter-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-color);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-color-secondary);
}

.filter-select {
  width: 100%;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.filter-option-icon {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.filter-strength-line {
  width: 20px;
  border-radius: 2px;
  flex-shrink: 0;
}

.filter-valence-line {
  width: 20px;
  height: 3px;
  border-radius: 2px;
  flex-shrink: 0;
}

.filter-valence-line.valence-positive {
  background: #10b981;
}

.filter-valence-line.valence-negative {
  background: #ef4444;
  border-style: dotted;
}

.filter-valence-line.valence-neutral {
  background: #6b7280;
  border-style: dashed;
}

.filter-checkbox-group {
  justify-content: center;
}

.filter-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.filter-badge i {
  font-size: 0.75rem;
}

/* Slider con valor */
.slider-with-value {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.strength-slider {
  flex: 1;
  min-width: 100px;
}

.slider-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color);
  min-width: 40px;
  text-align: right;
}

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
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-top: 1px solid var(--surface-200);
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
}

.legend-divider {
  width: 1px;
  height: 20px;
  background: var(--surface-300);
  flex-shrink: 0;
}

.legend-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
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

/* Estilos de linea por valencia */
.legend-line-solid {
  border-style: solid;
}

.legend-line-dashed {
  background: transparent !important;
  border-bottom: 3px dashed;
}

.legend-line-dashed.neutral {
  border-color: #6b7280;
}

.legend-line-dotted {
  background: transparent !important;
  border-bottom: 3px dotted;
}

.legend-line-dotted.negative {
  border-color: #ef4444;
}

/* Estilos de linea por fuerza */
.legend-line-strength {
  width: 24px;
  background: #6b7280;
  border-radius: 2px;
}

.strength-weak {
  height: 1px;
}

.strength-moderate {
  height: 2px;
}

.strength-strong {
  height: 3px;
}

.strength-very-strong {
  height: 5px;
}

/* Seccion de tipos en leyenda */
.legend-section-types,
.legend-section-entities {
  flex-wrap: wrap;
}

.legend-types-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

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

/* =============================================================================
   Cluster Legend Styles
   ============================================================================= */

.legend-section-clusters {
  flex-wrap: wrap;
}

.legend-section-clusters .legend-types-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.legend-item-clickable {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: var(--ds-radius-default, 4px);
  transition: background-color var(--ds-duration-fast, 150ms) ease;
  position: relative;
}

.legend-item-clickable:hover {
  background-color: var(--surface-100);
}

.legend-item-clickable:hover .legend-edit-icon {
  opacity: 1;
}

.legend-edit-icon {
  font-size: 0.625rem;
  color: var(--text-color-secondary);
  opacity: 0;
  transition: opacity var(--ds-duration-fast, 150ms) ease;
  margin-left: 0.25rem;
}

/* =============================================================================
   Cluster Rename Dialog Styles
   ============================================================================= */

.cluster-rename-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color);
}

.form-hint {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.cluster-info {
  background: var(--surface-50);
  border-radius: var(--ds-radius-md, 6px);
  padding: 1rem;
}

.cluster-info h5 {
  margin: 0 0 0.75rem 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.cluster-info ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cluster-info li {
  font-size: 0.875rem;
  color: var(--text-color);
}

.cluster-info li strong {
  color: var(--text-color-secondary);
  font-weight: 500;
}
</style>
