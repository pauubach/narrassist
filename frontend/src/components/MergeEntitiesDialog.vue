<template>
  <Dialog
    :visible="visible"
    modal
    header="Fusionar Entidades"
    :style="{ width: '700px' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="merge-dialog">
      <!-- Explicación -->
      <Message severity="info" :closable="false">
        <p>
          Fusiona múltiples entidades en una sola. Todas las apariciones, aliases y atributos
          serán transferidos a la entidad principal seleccionada.
        </p>
      </Message>

      <!-- Paso 1: Selección de entidades -->
      <div v-if="step === 1" class="step-content">
        <h3>Paso 1: Selecciona las entidades a fusionar</h3>

        <!-- Búsqueda de entidades -->
        <DsInput
          v-model="searchQuery"
          placeholder="Buscar entidades..."
          icon="pi pi-search"
          clearable
          class="w-full"
        />

        <!-- Lista de entidades disponibles -->
        <div class="entities-selection">
          <div
            v-for="entity in filteredAvailableEntities"
            :key="entity.id"
            class="entity-item"
            :class="{ 'selected': isSelected(entity.id) }"
            @click="toggleEntity(entity)"
          >
            <Checkbox :model-value="isSelected(entity.id)" :binary="true" />
            <div class="entity-icon-wrapper">
              <i :class="getEntityIcon(entity.type)"></i>
            </div>
            <div class="entity-info">
              <span class="entity-name">{{ entity.name }}</span>
              <span class="entity-type">{{ getTypeLabel(entity.type) }}</span>
            </div>
            <div class="entity-stats">
              <span class="stat">{{ entity.mentionCount || 0 }} apariciones</span>
            </div>
          </div>

          <div v-if="filteredAvailableEntities.length === 0" class="empty-state">
            <p>No se encontraron entidades</p>
          </div>
        </div>

        <!-- Entidades seleccionadas -->
        <div v-if="selectedEntities.length > 0" class="selected-summary">
          <strong>{{ selectedEntities.length }} entidades seleccionadas</strong>
          <div class="selected-chips">
            <Chip
              v-for="entity in selectedEntities"
              :key="entity.id"
              :label="entity.name"
              removable
              @remove="removeEntity(entity.id)"
            />
          </div>
        </div>
      </div>

      <!-- Paso 2: Seleccionar nombre principal -->
      <div v-if="step === 2" class="step-content">
        <h3>Paso 2: Selecciona el nombre principal</h3>
        <p class="step-description">
          Este será el nombre canónico de la entidad resultante. Los demás nombres se añadirán como aliases.
        </p>

        <div class="entities-selection">
          <div
            v-for="name in allAvailableNames"
            :key="name.value"
            class="entity-item entity-clickable"
            :class="{ 'primary': selectedPrimaryName === name.value }"
            @click="selectedPrimaryName = name.value"
          >
            <RadioButton
              v-model="selectedPrimaryName"
              :value="name.value"
              name="primaryName"
            />
            <div class="entity-icon-wrapper">
              <i :class="getEntityIcon(name.entityType)"></i>
            </div>
            <div class="entity-info">
              <span class="entity-name">{{ name.value }}</span>
              <div class="entity-details">
                <span class="detail-item source-tag" :class="name.isCanonical ? 'canonical' : 'alias'">
                  {{ name.isCanonical ? 'Nombre principal' : 'Alias' }}
                </span>
                <span class="detail-item">
                  <i class="pi pi-user"></i>
                  de: {{ name.sourceEntityName }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Paso 3: Confirmación -->
      <div v-if="step === 3" class="step-content">
        <h3>Paso 3: Revisa y confirma</h3>

        <!-- Loading state -->
        <div v-if="loadingPreview || loadingSimilarity" class="preview-loading">
          <i class="pi pi-spin pi-spinner" style="font-size: 2rem"></i>
          <p>Analizando entidades y detectando conflictos...</p>
        </div>

        <div v-else class="merge-preview">
          <!-- Entidad resultante -->
          <div class="result-entity">
            <h4>Entidad resultante:</h4>
            <div class="entity-card primary-card">
              <div class="entity-icon-wrapper large">
                <i :class="getEntityIcon(resultEntityType)"></i>
              </div>
              <div class="entity-info">
                <span class="entity-name large">{{ selectedPrimaryName }}</span>
                <Tag :severity="getTypeSeverity(resultEntityType)">
                  {{ getTypeLabel(resultEntityType) }}
                </Tag>
              </div>
            </div>
            <!-- Aliases que se añadirán -->
            <div v-if="resultAliases.length > 0" class="result-aliases">
              <strong>Aliases:</strong>
              <div class="aliases-list">
                <span v-for="alias in resultAliases" :key="alias" class="alias-chip">
                  {{ alias }}
                </span>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Entidades a absorber -->
          <div class="merge-entities">
            <h4>Se fusionaran estas entidades:</h4>
            <div class="entities-to-merge">
              <div
                v-for="entity in entitiesToMerge"
                :key="entity.id"
                class="entity-card secondary-card"
              >
                <i class="pi pi-arrow-right merge-arrow"></i>
                <span class="entity-name">{{ entity.name }}</span>
                <span class="entity-stats">
                  {{ entity.mentionCount || 0 }} apariciones
                </span>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Análisis de similitud mejorado -->
          <div class="similarity-analysis">
            <h4>
              <i class="pi pi-chart-bar"></i>
              Análisis de similitud
            </h4>

            <div v-if="similarityData" class="similarity-content">
              <!-- Recomendación general con razón -->
              <div class="similarity-recommendation">
                <Tag :severity="getRecommendationSeverity(similarityData.recommendation)">
                  {{ getRecommendationText(similarityData.recommendation) }}
                </Tag>
                <span class="avg-similarity">
                  Similitud promedio:
                  <strong :style="{ color: getSimilarityColor(similarityData.average_similarity) }">
                    {{ (similarityData.average_similarity * 100).toFixed(0) }}%
                  </strong>
                </span>
              </div>

              <!-- Razón de la recomendación -->
              <div v-if="previewData?.recommendation_reason" class="recommendation-reason">
                <i class="pi pi-info-circle"></i>
                {{ previewData.recommendation_reason }}
              </div>

              <!-- Detalle por pares con métricas desglosadas -->
              <div v-if="similarityData.pairs.length > 0" class="similarity-pairs">
                <div
                  v-for="pair in similarityData.pairs"
                  :key="`${pair.entity1_id}-${pair.entity2_id}`"
                  class="similarity-pair"
                >
                  <div class="pair-header">
                    <div class="pair-names">
                      <span class="pair-name">{{ pair.entity1_name }}</span>
                      <i class="pi pi-arrows-h"></i>
                      <span class="pair-name">{{ pair.entity2_name }}</span>
                    </div>
                    <Tag
                      v-if="pair.recommendation || (pair.similarity !== undefined && pair.similarity >= 0.5)"
                      :severity="pair.recommendation === 'merge' || (pair.similarity !== undefined && pair.similarity >= 0.6) ? 'success' : pair.recommendation === 'review' || (pair.similarity !== undefined && pair.similarity >= 0.4) ? 'warning' : 'danger'"
                      class="pair-tag"
                    >
                      {{ pair.recommendation === 'merge' || (pair.similarity !== undefined && pair.similarity >= 0.6) ? 'Compatible' : pair.recommendation === 'review' || (pair.similarity !== undefined && pair.similarity >= 0.4) ? 'Revisar' : 'Diferente' }}
                    </Tag>
                  </div>

                  <!-- Score combinado principal -->
                  <div class="pair-score-main">
                    <div class="score-label-row">
                      <span>Score combinado</span>
                      <span class="score-value-main" :style="{ color: getSimilarityColor(pair.similarity || pair.combined_score || 0) }">
                        {{ ((pair.similarity || pair.combined_score || 0) * 100).toFixed(0) }}%
                      </span>
                    </div>
                    <ProgressBar
                      :value="(pair.similarity || pair.combined_score || 0) * 100"
                      :show-value="false"
                      :style="{ height: '8px' }"
                      :class="getProgressBarClass(pair.similarity || pair.combined_score || 0)"
                    />
                  </div>

                  <!-- Desglose de métricas (si está disponible) -->
                  <div v-if="pair.name_similarity" class="pair-score-details">
                    <div class="score-detail">
                      <span class="detail-label">Nombre (Levenshtein)</span>
                      <div class="detail-bar-container">
                        <div
                          class="detail-bar"
                          :style="{ width: `${pair.name_similarity.levenshtein * 100}%` }"
                        ></div>
                        <span class="detail-value">{{ (pair.name_similarity.levenshtein * 100).toFixed(0) }}%</span>
                      </div>
                    </div>
                    <div class="score-detail">
                      <span class="detail-label">Nombre (Jaro-Winkler)</span>
                      <div class="detail-bar-container">
                        <div
                          class="detail-bar"
                          :style="{ width: `${pair.name_similarity.jaro_winkler * 100}%` }"
                        ></div>
                        <span class="detail-value">{{ (pair.name_similarity.jaro_winkler * 100).toFixed(0) }}%</span>
                      </div>
                    </div>
                    <div v-if="pair.semantic_similarity > 0" class="score-detail">
                      <span class="detail-label">Semantica (Embeddings)</span>
                      <div class="detail-bar-container">
                        <div
                          class="detail-bar semantic"
                          :style="{ width: `${pair.semantic_similarity * 100}%` }"
                        ></div>
                        <span class="detail-value">{{ (pair.semantic_similarity * 100).toFixed(0) }}%</span>
                      </div>
                    </div>
                  </div>

                  <small v-if="pair.reason || pair.semantic_reason" class="pair-reason">
                    {{ pair.semantic_reason || pair.reason }}
                  </small>
                </div>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Conflictos de atributos -->
          <div v-if="previewData && previewData.conflicts.length > 0" class="conflicts-section">
            <h4>
              <i class="pi pi-exclamation-triangle" style="color: var(--orange-500)"></i>
              Conflictos de atributos ({{ previewData.conflict_count }})
            </h4>

            <!-- Warning si hay conflictos críticos -->
            <Message v-if="previewData.has_critical_conflicts" severity="error" :closable="false" class="conflict-warning">
              <strong>Atencion:</strong> Se detectaron conflictos criticos en atributos de identidad o fisicos.
              Revisa cuidadosamente antes de fusionar.
            </Message>

            <div class="conflicts-list">
              <div
                v-for="(conflict, index) in previewData.conflicts"
                :key="index"
                class="conflict-item"
                :class="{ 'critical': conflict.severity === 'high' }"
              >
                <div class="conflict-header">
                  <Tag :severity="getConflictSeverityColor(conflict.severity)" class="conflict-severity">
                    {{ getConflictSeverityLabel(conflict.severity) }}
                  </Tag>
                  <span class="conflict-category">{{ getConflictCategoryLabel(conflict.category) }}</span>
                  <span class="conflict-attr-name">{{ conflict.attribute_name }}</span>
                </div>
                <div class="conflict-values">
                  <div
                    v-for="(cv, cvIndex) in conflict.conflicting_values"
                    :key="cvIndex"
                    class="conflict-value-item"
                  >
                    <span class="cv-value">"{{ cv.value }}"</span>
                    <span class="cv-source">
                      <i class="pi pi-user"></i>
                      {{ cv.entity_name }}
                    </span>
                    <span v-if="cv.confidence < 1" class="cv-confidence">
                      ({{ (cv.confidence * 100).toFixed(0) }}% conf.)
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <Divider v-if="previewData && previewData.conflicts.length > 0" />

          <!-- Resumen de cambios -->
          <div class="merge-summary">
            <h4>Resumen de cambios:</h4>
            <div class="summary-items">
              <div class="summary-item">
                <i class="pi pi-hashtag"></i>
                <span>Total de apariciones: <strong>{{ previewData?.merged_preview?.total_mentions || totalMentions }}</strong></span>
              </div>
              <div class="summary-item">
                <i class="pi pi-tag"></i>
                <span>Aliases a combinar: <strong>{{ totalAliases }}</strong></span>
              </div>
              <div class="summary-item">
                <i class="pi pi-trash"></i>
                <span>Entidades a eliminar: <strong>{{ selectedEntities.length - 1 }}</strong></span>
              </div>
              <div v-if="previewData && previewData.conflict_count > 0" class="summary-item warning">
                <i class="pi pi-exclamation-triangle"></i>
                <span>Conflictos detectados: <strong>{{ previewData.conflict_count }}</strong></span>
              </div>
            </div>
          </div>

          <!-- Advertencia -->
          <Message severity="info" :closable="false">
            <strong>Nota:</strong> Las entidades fusionadas se desactivaran pero podras deshacer
            esta fusion desde el historial de fusiones o desde la ficha de la entidad resultante.
          </Message>
        </div>
      </div>

      <!-- Indicador de progreso -->
      <div class="steps-indicator">
        <div
          v-for="i in 3"
          :key="i"
          class="step-dot"
          :class="{ 'active': step === i, 'completed': step > i }"
        >
          {{ i }}
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <Button
            v-if="step > 1"
            label="Anterior"
            icon="pi pi-arrow-left"
            text
            @click="previousStep"
          />
        </div>
        <div class="footer-right">
          <Button
            label="Cancelar"
            icon="pi pi-times"
            text
            @click="cancel"
          />
          <Button
            v-if="step < 3"
            label="Siguiente"
            icon="pi pi-arrow-right"
            icon-pos="right"
            :disabled="!canProceed"
            @click="nextStep"
          />
          <Button
            v-else
            label="Fusionar"
            icon="pi pi-check"
            severity="danger"
            :loading="merging"
            @click="confirmMerge"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import DsInput from '@/components/ds/DsInput.vue'
import Checkbox from 'primevue/checkbox'
import RadioButton from 'primevue/radiobutton'
import Chip from 'primevue/chip'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Divider from 'primevue/divider'
import ProgressBar from 'primevue/progressbar'
import type { Entity } from '@/types'
import { apiUrl } from '@/config/api'

// Interfaces para similitud por nombre
interface NameSimilarity {
  levenshtein: number
  jaro_winkler: number
  containment: number
  combined: number
}

// Interface mejorada para pares de similitud
interface SimilarityPair {
  entity1_id: number
  entity1_name: string
  entity2_id: number
  entity2_name: string
  name_similarity: NameSimilarity
  semantic_similarity: number
  semantic_reason: string
  combined_score: number
  recommendation: 'merge' | 'review' | 'keep_separate'
  // Compatibilidad con formato anterior
  similarity?: number
  should_merge?: boolean
  reason?: string
  method?: string
}

// Interface para conflictos de atributos
interface AttributeConflict {
  category: string
  attribute_name: string
  conflicting_values: {
    value: string
    entity_name: string
    entity_id: number
    confidence: number
  }[]
  severity: 'high' | 'medium' | 'low'
}

// Interface para preview de fusión
interface MergedPreview {
  suggested_canonical_name: string
  suggested_aliases: string[]
  suggested_type: string
  total_mentions: number
  entities_to_merge: number
  all_names: string[]
}

// Interface para datos de similitud (formato antiguo para compatibilidad)
interface SimilarityData {
  pairs: SimilarityPair[]
  average_similarity: number
  entity_count: number
  recommendation: 'merge' | 'review' | 'keep_separate'
}

// Interface para respuesta del preview-merge
interface PreviewMergeData {
  similarity: {
    pairs: SimilarityPair[]
    average_score: number
  }
  merged_preview: MergedPreview
  conflicts: AttributeConflict[]
  conflict_count: number
  has_critical_conflicts: boolean
  recommendation: 'merge' | 'review' | 'keep_separate'
  recommendation_reason: string
  entity_count: number
}

const props = defineProps<{
  visible: boolean
  projectId: number
  availableEntities: Entity[]
  preselectedEntities?: Entity[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'merge': [primaryId: number, entityIds: number[]]
  'cancel': []
}>()

// Interfaz para nombres disponibles
interface AvailableName {
  value: string
  entityId: number
  entityType: string
  sourceEntityName: string
  isCanonical: boolean
}

// Estado
const step = ref(1)
const searchQuery = ref('')
const selectedEntityIds = ref<Set<number>>(new Set())
const selectedPrimaryName = ref<string | null>(null)
const merging = ref(false)
const loadingSimilarity = ref(false)
const similarityData = ref<SimilarityData | null>(null)
const previewData = ref<PreviewMergeData | null>(null)
const loadingPreview = ref(false)

// Inicializar con entidades preseleccionadas
watch(() => props.preselectedEntities, (entities) => {
  if (entities && entities.length > 0) {
    selectedEntityIds.value = new Set(entities.map(e => e.id))
  }
}, { immediate: true })

// Computed
const filteredAvailableEntities = computed(() => {
  let filtered = props.availableEntities

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(e =>
      e.name.toLowerCase().includes(query) ||
      e.aliases?.some((a: string) => a.toLowerCase().includes(query))
    )
  }

  return filtered
})

const selectedEntities = computed(() => {
  return props.availableEntities.filter(e => selectedEntityIds.value.has(e.id))
})

// Todos los nombres disponibles (canónicos + aliases de todas las entidades seleccionadas)
const allAvailableNames = computed((): AvailableName[] => {
  const names: AvailableName[] = []

  selectedEntities.value.forEach(entity => {
    // Añadir nombre canónico
    names.push({
      value: entity.name,
      entityId: entity.id,
      entityType: entity.type,
      sourceEntityName: entity.name,
      isCanonical: true
    })

    // Añadir aliases
    if (entity.aliases) {
      entity.aliases.forEach((alias: string) => {
        names.push({
          value: alias,
          entityId: entity.id,
          entityType: entity.type,
          sourceEntityName: entity.name,
          isCanonical: false
        })
      })
    }
  })

  // Ordenar: nombres canónicos primero, luego por longitud (más largos primero)
  return names.sort((a, b) => {
    if (a.isCanonical !== b.isCanonical) return a.isCanonical ? -1 : 1
    return b.value.length - a.value.length
  })
})

// Entidad principal basada en el nombre seleccionado
const primaryEntity = computed(() => {
  if (!selectedPrimaryName.value) return null
  const nameObj = allAvailableNames.value.find(n => n.value === selectedPrimaryName.value)
  if (!nameObj) return null
  return selectedEntities.value.find(e => e.id === nameObj.entityId) || null
})

// Tipo de entidad para el resultado (basado en la entidad con más menciones)
const resultEntityType = computed(() => {
  if (selectedEntities.value.length === 0) return ''
  const sorted = [...selectedEntities.value].sort(
    (a, b) => (b.mentionCount || 0) - (a.mentionCount || 0)
  )
  return sorted[0]?.type || ''
})

// Aliases resultantes (todos los nombres excepto el principal)
const resultAliases = computed(() => {
  if (!selectedPrimaryName.value) return []
  return allAvailableNames.value
    .map(n => n.value)
    .filter(name => name !== selectedPrimaryName.value)
})

const entitiesToMerge = computed(() => {
  return selectedEntities.value
})

const totalMentions = computed(() => {
  return selectedEntities.value.reduce((sum, e) => sum + (e.mentionCount || 0), 0)
})

const totalAliases = computed(() => {
  return allAvailableNames.value.length - 1 // Todos menos el principal
})

const canProceed = computed(() => {
  if (step.value === 1) {
    return selectedEntities.value.length >= 2
  }
  if (step.value === 2) {
    return selectedPrimaryName.value !== null
  }
  return true
})

// Funciones
const isSelected = (id: number): boolean => {
  return selectedEntityIds.value.has(id)
}

const toggleEntity = (entity: Entity) => {
  if (selectedEntityIds.value.has(entity.id)) {
    selectedEntityIds.value.delete(entity.id)
  } else {
    selectedEntityIds.value.add(entity.id)
  }
}

const removeEntity = (id: number) => {
  selectedEntityIds.value.delete(id)
}

const loadSimilarity = async () => {
  if (selectedEntityIds.value.size < 2) return

  loadingSimilarity.value = true
  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/similarity`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_ids: Array.from(selectedEntityIds.value) })
    })
    const result = await response.json()
    if (result.success) {
      similarityData.value = result.data
    }
  } catch (error) {
    console.error('Error loading similarity:', error)
  } finally {
    loadingSimilarity.value = false
  }
}

// Cargar preview de fusión completo (con conflictos y preview del resultado)
const loadPreviewMerge = async () => {
  if (selectedEntityIds.value.size < 2) return

  loadingPreview.value = true
  try {
    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/entities/preview-merge`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_ids: Array.from(selectedEntityIds.value) })
    })
    const result = await response.json()
    if (result.success) {
      previewData.value = result.data

      // También actualizar similarityData para compatibilidad con UI existente
      if (result.data.similarity) {
        similarityData.value = {
          pairs: result.data.similarity.pairs.map((p: SimilarityPair) => ({
            ...p,
            // Adaptar al formato esperado por la UI existente
            similarity: p.combined_score || p.similarity || 0,
            should_merge: (p.combined_score || p.similarity || 0) >= 0.5,
            reason: p.semantic_reason || p.reason || '',
            method: 'combined'
          })),
          average_similarity: result.data.similarity.average_score,
          entity_count: result.data.entity_count,
          recommendation: result.data.recommendation
        }
      }
    }
  } catch (error) {
    console.error('Error loading preview merge:', error)
    // Fallback a endpoint de similitud simple
    await loadSimilarity()
  } finally {
    loadingPreview.value = false
  }
}

const getSimilarityColor = (similarity: number): string => {
  if (similarity >= 0.7) return 'var(--green-500)'
  if (similarity >= 0.5) return 'var(--yellow-500)'
  if (similarity >= 0.3) return 'var(--orange-500)'
  return 'var(--red-500)'
}

const getRecommendationText = (recommendation: string): string => {
  const texts: Record<string, string> = {
    'merge': 'Recomendado fusionar',
    'review': 'Revisar antes de fusionar',
    'keep_separate': 'Mantener separadas'
  }
  return texts[recommendation] || recommendation
}

const getRecommendationSeverity = (recommendation: string): string => {
  const severities: Record<string, string> = {
    'merge': 'success',
    'review': 'warning',
    'keep_separate': 'danger'
  }
  return severities[recommendation] || 'secondary'
}

// Helpers para conflictos de atributos
const getConflictSeverityLabel = (severity: string): string => {
  const labels: Record<string, string> = {
    'high': 'Critico',
    'medium': 'Medio',
    'low': 'Bajo'
  }
  return labels[severity] || severity
}

const getConflictSeverityColor = (severity: string): string => {
  const severities: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'secondary'
  }
  return severities[severity] || 'secondary'
}

const getConflictCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    'physical': 'Fisico',
    'identity': 'Identidad',
    'personality': 'Personalidad',
    'relationship': 'Relacion',
    'background': 'Trasfondo',
    'ability': 'Habilidad',
    'possession': 'Posesion'
  }
  return labels[category] || category
}

// Helper para clase de ProgressBar según el score
const getProgressBarClass = (score: number): string => {
  if (score >= 0.7) return 'progress-high'
  if (score >= 0.5) return 'progress-medium'
  if (score >= 0.3) return 'progress-low'
  return 'progress-very-low'
}

const nextStep = async () => {
  if (!canProceed.value) return

  step.value++

  // Al pasar al paso 2, preseleccionar el mejor nombre (nombre propio > descripción)
  if (step.value === 2 && !selectedPrimaryName.value) {
    // Función para puntuar qué tan "buen nombre propio" es un nombre
    const scoreProperName = (name: string): number => {
      let score = 0
      const words = name.split(' ')

      // Nombres cortos (1-3 palabras) son preferibles
      if (words.length <= 3) score += 20
      if (words.length === 1 || words.length === 2) score += 10

      // Empieza con mayúscula (nombre propio)
      if (name[0] === name[0].toUpperCase() && name[0] !== name[0].toLowerCase()) {
        score += 30
      }

      // Penalizar si empieza con artículo (el, la, un, una) - probablemente descripción
      const firstWord = words[0]?.toLowerCase()
      if (['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'].includes(firstWord)) {
        score -= 50
      }

      // Penalizar si contiene adjetivos descriptivos comunes
      const descriptiveWords = ['morena', 'moreno', 'rubia', 'rubio', 'alta', 'alto', 'vieja', 'viejo', 'joven', 'vestido', 'rojo', 'azul', 'verde']
      if (descriptiveWords.some(w => name.toLowerCase().includes(w))) {
        score -= 30
      }

      // Bonificar si tiene estructura de nombre + apellido
      if (words.length === 2 && words.every(w => w[0] === w[0].toUpperCase())) {
        score += 40
      }

      return score
    }

    // Ordenar nombres canónicos por puntuación
    const canonicalNames = allAvailableNames.value.filter(n => n.isCanonical)
    const bestName = canonicalNames.sort((a, b) => scoreProperName(b.value) - scoreProperName(a.value))[0]
    if (bestName) {
      selectedPrimaryName.value = bestName.value
    }
  }

  // Al pasar al paso 3, cargar preview completo de fusión
  if (step.value === 3) {
    loadPreviewMerge()
  }
}

const previousStep = () => {
  step.value--
}

const confirmMerge = async () => {
  if (!selectedPrimaryName.value || !primaryEntity.value) return

  merging.value = true

  try {
    // Emitir evento con la entidad principal, las IDs a fusionar y el nombre seleccionado
    const primaryId = primaryEntity.value.id
    const idsToMerge = Array.from(selectedEntityIds.value).filter(
      id => id !== primaryId
    )

    // Emitir con información adicional del nombre y aliases
    emit('merge', primaryId, idsToMerge)

    // TODO: El backend debería recibir también:
    // - selectedPrimaryName.value como nuevo canonical_name
    // - resultAliases.value como nuevos aliases
  } finally {
    merging.value = false
  }
}

const cancel = () => {
  emit('cancel')
  emit('update:visible', false)
  resetDialog()
}

const resetDialog = () => {
  step.value = 1
  searchQuery.value = ''
  selectedEntityIds.value = new Set()
  selectedPrimaryName.value = null
  similarityData.value = null
  previewData.value = null
}

// Helpers
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

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'CHARACTER': 'Personaje',
    'LOCATION': 'Lugar',
    'ORGANIZATION': 'Organización',
    'OBJECT': 'Objeto',
    'EVENT': 'Evento'
  }
  return labels[type] || type
}

const getTypeSeverity = (type: string): string => {
  const severities: Record<string, string> = {
    'CHARACTER': 'success',
    'LOCATION': 'danger',
    'ORGANIZATION': 'info',
    'OBJECT': 'warning',
    'EVENT': 'secondary'
  }
  return severities[type] || 'secondary'
}

// Watch para resetear al cerrar
watch(() => props.visible, (isVisible) => {
  if (!isVisible) {
    resetDialog()
  }
})
</script>

<style scoped>
.merge-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 400px;
}

.step-content h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-color);
}

.step-description {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.search-wrapper {
  width: 100%;
}

.entities-selection {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.5rem;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border: 1px solid transparent;
  transition: all 0.2s;
  cursor: pointer;
}

.entity-item:hover {
  background: var(--surface-50);
  border-color: var(--surface-200);
}

.entity-item.selected {
  background: var(--primary-50);
  border-color: var(--primary-200);
}

.entity-item.entity-clickable:hover {
  transform: translateX(4px);
}

.entity-item.primary {
  background: var(--primary-100);
  border-color: var(--primary-color);
}

.entity-icon-wrapper {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 50%;
  flex-shrink: 0;
}

.entity-icon-wrapper.large {
  width: 48px;
  height: 48px;
}

.entity-icon-wrapper i {
  font-size: 1.125rem;
  color: var(--primary-color);
}

.entity-icon-wrapper.large i {
  font-size: 1.5rem;
}

.entity-info {
  flex: 1;
  min-width: 0;
}

.entity-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
  display: block;
}

.entity-name.large {
  font-size: 1.125rem;
}

.entity-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entity-details {
  display: flex;
  gap: 1rem;
  margin-top: 0.25rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entity-stats {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.selected-summary {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.selected-summary strong {
  color: var(--text-color);
}

.selected-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* Paso 3 - Preview */
.merge-preview {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.merge-preview h4 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.entity-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid;
}

.entity-card.primary-card {
  background: var(--primary-50);
  border-color: var(--primary-color);
}

.entity-card.secondary-card {
  background: var(--surface-50);
  border-color: var(--surface-200);
  margin-bottom: 0.5rem;
}

.merge-arrow {
  color: var(--primary-color);
  font-size: 1rem;
}

.merge-summary {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
}

.summary-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9375rem;
}

.summary-item i {
  color: var(--primary-color);
}

.summary-item strong {
  color: var(--text-color);
  font-weight: 600;
}

/* Indicador de pasos */
.steps-indicator {
  display: flex;
  justify-content: center;
  gap: 1rem;
  padding-top: 0.5rem;
}

.step-dot {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--surface-200);
  color: var(--text-color-secondary);
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.3s;
}

.step-dot.active {
  background: var(--primary-color);
  color: white;
  transform: scale(1.1);
}

.step-dot.completed {
  background: var(--green-500);
  color: white;
}

/* Footer */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.footer-left,
.footer-right {
  display: flex;
  gap: 0.5rem;
}

.w-full {
  width: 100%;
}

/* Scrollbar */
.entities-selection::-webkit-scrollbar {
  width: 6px;
}

.entities-selection::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.entities-selection::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

/* Source tags para nombres */
.source-tag {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.source-tag.canonical {
  background: var(--green-100);
  color: var(--green-700);
}

.source-tag.alias {
  background: var(--surface-200);
  color: var(--text-color-secondary);
}

/* Result aliases */
.result-aliases {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.result-aliases strong {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.aliases-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.alias-chip {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  background: var(--p-surface-0, white);
  border: 1px solid var(--p-surface-300, #cbd5e1);
  border-radius: 12px;
  font-size: 0.8125rem;
  color: var(--p-text-color);
}

/* Análisis de similitud */
.similarity-analysis {
  background: var(--surface-50);
  border-radius: 8px;
  padding: 1rem;
}

.similarity-analysis h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: var(--text-color);
}

.similarity-analysis h4 i {
  color: var(--primary-color);
}

.similarity-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--text-color-secondary);
}

.similarity-recommendation {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--surface-200);
}

.avg-similarity {
  font-size: 0.9375rem;
  color: var(--text-color-secondary);
}

.avg-similarity strong {
  font-size: 1.125rem;
}

.similarity-pairs {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.similarity-pair {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: var(--p-surface-0, white);
  border-radius: 6px;
  border: 1px solid var(--p-surface-200, #e2e8f0);
}

.pair-names {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.pair-names i {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.pair-name {
  font-weight: 500;
  color: var(--text-color);
}

.pair-score {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
  height: 20px;
  background: var(--surface-100);
  border-radius: 4px;
  overflow: hidden;
}

.score-bar {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  transition: width 0.3s ease;
  opacity: 0.3;
}

.score-value {
  position: relative;
  z-index: 1;
  padding-left: 0.5rem;
  font-weight: 600;
  font-size: 0.8125rem;
}

.score-label {
  position: relative;
  z-index: 1;
  margin-left: auto;
  padding-right: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.pair-reason {
  color: var(--text-color-secondary);
  font-style: italic;
}

/* Dark mode */
.dark .similarity-pair {
  background: var(--surface-700);
  border-color: var(--surface-600);
}

.dark .pair-score {
  background: var(--surface-600);
}

/* Preview loading state */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--text-color-secondary);
}

/* Enhanced similarity pair styles */
.pair-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.pair-tag {
  font-size: 0.7rem;
}

.pair-score-main {
  margin-bottom: 0.75rem;
}

.score-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  font-size: 0.8125rem;
}

.score-value-main {
  font-weight: 700;
  font-size: 1rem;
}

/* Progress bar colors */
.progress-high :deep(.p-progressbar-value) {
  background: var(--green-500) !important;
}

.progress-medium :deep(.p-progressbar-value) {
  background: var(--yellow-500) !important;
}

.progress-low :deep(.p-progressbar-value) {
  background: var(--orange-500) !important;
}

.progress-very-low :deep(.p-progressbar-value) {
  background: var(--red-500) !important;
}

/* Score details breakdown */
.pair-score-details {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 4px;
  margin-top: 0.5rem;
}

.score-detail {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-label {
  flex: 0 0 140px;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.detail-bar-container {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 12px;
  background: var(--surface-200);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.detail-bar {
  height: 100%;
  background: var(--primary-color);
  opacity: 0.7;
  transition: width 0.3s ease;
}

.detail-bar.semantic {
  background: var(--purple-500);
}

.detail-value {
  flex: 0 0 35px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-align: right;
}

/* Recommendation reason */
.recommendation-reason {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-100);
  border-radius: 4px;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
}

.recommendation-reason i {
  color: var(--primary-color);
}

/* Conflicts section */
.conflicts-section {
  background: var(--surface-50);
  border-radius: 8px;
  padding: 1rem;
}

.conflicts-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: var(--text-color);
}

.conflict-warning {
  margin-bottom: 1rem;
}

.conflicts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.conflict-item {
  background: var(--p-surface-0, white);
  border: 1px solid var(--p-surface-200, #e2e8f0);
  border-radius: 6px;
  padding: 0.75rem;
}

.conflict-item.critical {
  border-color: var(--red-300);
  background: var(--red-50);
}

.conflict-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.conflict-severity {
  font-size: 0.6875rem;
}

.conflict-category {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.conflict-attr-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.conflict-values {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-left: 0.5rem;
  border-left: 2px solid var(--surface-200);
}

.conflict-value-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.cv-value {
  font-weight: 500;
  color: var(--text-color);
}

.cv-source {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.cv-source i {
  font-size: 0.6875rem;
}

.cv-confidence {
  color: var(--text-color-secondary);
  font-size: 0.6875rem;
  font-style: italic;
}

/* Summary item warning */
.summary-item.warning {
  color: var(--orange-600);
}

.summary-item.warning i {
  color: var(--orange-500);
}

/* Dark mode additions */
.dark .pair-score-details {
  background: var(--surface-600);
}

.dark .detail-bar-container {
  background: var(--surface-500);
}

.dark .conflict-item {
  background: var(--surface-700);
  border-color: var(--surface-600);
}

.dark .conflict-item.critical {
  background: rgba(239, 68, 68, 0.15);
  border-color: var(--red-700);
}

.dark .conflict-values {
  border-left-color: var(--surface-500);
}
</style>
