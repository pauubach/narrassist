<script setup lang="ts">
/**
 * StyleTab - Pestana de Escritura y Análisis
 *
 * Contiene todos los análisis de escritura organizados en categorías:
 * - Narrativa: registro, focalización, escenas, ritmo, emociones, progreso
 * - Estilo: densidad, ecos, variación, legibilidad
 * - Consistencia: estado vital, ubicaciones
 *
 * Los sub-tabs se adaptan al tipo de documento.
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { useFeatureProfile } from '@/composables/useFeatureProfile'
import RegisterAnalysisTab from './RegisterAnalysisTab.vue'
import FocalizationTab from './FocalizationTab.vue'
import SceneTaggingTab from './SceneTaggingTab.vue'
import StickySentencesTab from './StickySentencesTab.vue'
import EchoReportTab from './EchoReportTab.vue'
import SentenceVariationTab from './SentenceVariationTab.vue'
import PacingAnalysisTab from './PacingAnalysisTab.vue'
import EmotionalAnalysisTab from './EmotionalAnalysisTab.vue'
import AgeReadabilityTab from './AgeReadabilityTab.vue'
import VitalStatusTab from './VitalStatusTab.vue'
import CharacterLocationTab from './CharacterLocationTab.vue'
import ChapterProgressTab from './ChapterProgressTab.vue'

type CategoryId = 'narrative' | 'style' | 'consistency'

interface SubTab {
  id: string
  label: string
  icon: string
  component: string
  featureKey?: string
  category: CategoryId
}

interface Category {
  id: CategoryId
  label: string
  icon: string
}

const props = defineProps<{
  projectId: number
  analysisStatus?: string
}>()

const workspaceStore = useWorkspaceStore()
const { isFeatureAvailable } = useFeatureProfile(computed(() => props.projectId))

const activeTabId = ref('register')
const activeCategoryId = ref<CategoryId>('narrative')

// Feature availability
const hasScenes = ref(false)

// Categories
const categories: Category[] = [
  { id: 'narrative', label: 'Narrativa', icon: 'pi pi-book' },
  { id: 'style', label: 'Estilo', icon: 'pi pi-pencil' },
  { id: 'consistency', label: 'Consistencia', icon: 'pi pi-check-circle' },
]

// All possible sub-tabs with category assignments
const allSubTabs: SubTab[] = [
  // Narrativa
  { id: 'register', label: 'Registro', icon: 'pi pi-sliders-v', component: 'RegisterAnalysisTab', category: 'narrative' },
  { id: 'focalization', label: 'Focalización', icon: 'pi pi-eye', component: 'FocalizationTab', category: 'narrative' },
  { id: 'scenes', label: 'Escenas', icon: 'pi pi-images', component: 'SceneTaggingTab', featureKey: 'scenes', category: 'narrative' },
  { id: 'pacing', label: 'Ritmo', icon: 'pi pi-forward', component: 'PacingAnalysisTab', featureKey: 'pacing', category: 'narrative' },
  { id: 'emotions', label: 'Emociones', icon: 'pi pi-heart', component: 'EmotionalAnalysisTab', featureKey: 'emotional_analysis', category: 'narrative' },
  { id: 'progress', label: 'Progreso', icon: 'pi pi-chart-line', component: 'ChapterProgressTab', featureKey: 'chapter_progress', category: 'narrative' },
  // Estilo
  { id: 'sticky', label: 'Densidad', icon: 'pi pi-align-left', component: 'StickySentencesTab', featureKey: 'sticky_sentences', category: 'style' },
  { id: 'echo', label: 'Ecos', icon: 'pi pi-replay', component: 'EchoReportTab', featureKey: 'echo_repetitions', category: 'style' },
  { id: 'variation', label: 'Variación', icon: 'pi pi-chart-bar', component: 'SentenceVariationTab', featureKey: 'sentence_variation', category: 'style' },
  { id: 'readability', label: 'Legibilidad', icon: 'pi pi-users', component: 'AgeReadabilityTab', featureKey: 'age_readability', category: 'style' },
  // Consistencia
  { id: 'vital', label: 'Estado vital', icon: 'pi pi-heart-fill', component: 'VitalStatusTab', featureKey: 'vital_status', category: 'consistency' },
  { id: 'locations', label: 'Ubicaciones', icon: 'pi pi-map-marker', component: 'CharacterLocationTab', featureKey: 'character_location', category: 'consistency' },
]

// Filtered sub-tabs based on feature availability
const visibleSubTabs = computed(() => {
  return allSubTabs.filter(tab => {
    if (!tab.featureKey) return true
    if (tab.id === 'scenes') return hasScenes.value && isFeatureAvailable(tab.featureKey)
    return isFeatureAvailable(tab.featureKey)
  })
})

// Sub-tabs for the active category
const categorySubTabs = computed(() => {
  return visibleSubTabs.value.filter(tab => tab.category === activeCategoryId.value)
})

// Categories that have at least one visible tab
const visibleCategories = computed(() => {
  return categories.filter(cat =>
    visibleSubTabs.value.some(tab => tab.category === cat.id)
  )
})

// Count of visible tabs per category (for badge)
function categoryTabCount(catId: CategoryId): number {
  return visibleSubTabs.value.filter(tab => tab.category === catId).length
}

// Watch for external navigation requests
watch(() => workspaceStore.styleTabSubtab, (newSubtab) => {
  if (newSubtab !== null) {
    const tab = visibleSubTabs.value[newSubtab]
    if (tab) {
      activeCategoryId.value = tab.category
      activeTabId.value = tab.id
    }
    workspaceStore.clearStyleTabSubtab()
  }
}, { immediate: true })

function selectCategory(catId: CategoryId) {
  activeCategoryId.value = catId
  // Auto-select first tab in category if current tab isn't in it
  const tabsInCat = visibleSubTabs.value.filter(t => t.category === catId)
  if (tabsInCat.length > 0 && !tabsInCat.some(t => t.id === activeTabId.value)) {
    activeTabId.value = tabsInCat[0].id
  }
}

function selectSubTab(tabId: string) {
  activeTabId.value = tabId
}

onMounted(() => {
  loadFeatureAvailability()
})

watch(() => props.projectId, () => {
  loadFeatureAvailability()
})

async function loadFeatureAvailability() {
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/scenes/stats`
    )
    const data = await response.json()
    if (data.success) {
      hasScenes.value = data.data.has_scenes || false
    }
  } catch (error) {
    console.error('Error loading feature availability:', error)
  }
}
</script>

<template>
  <div class="style-tab">
    <!-- Row 1: Category bar -->
    <div class="category-bar" role="tablist" aria-label="Categorías de análisis">
      <button
        v-for="cat in visibleCategories"
        :key="cat.id"
        type="button"
        role="tab"
        class="category-tab"
        :class="{ 'category-tab--active': activeCategoryId === cat.id }"
        :aria-selected="activeCategoryId === cat.id"
        @click="selectCategory(cat.id)"
      >
        <i :class="cat.icon" class="category-tab__icon" />
        <span class="category-tab__label">{{ cat.label }}</span>
        <span class="category-tab__count">{{ categoryTabCount(cat.id) }}</span>
      </button>
    </div>

    <!-- Row 2: Sub-tabs within category -->
    <div class="subtabs-bar" role="tablist" aria-label="Análisis de escritura">
      <div class="subtabs-scroll">
        <button
          v-for="tab in categorySubTabs"
          :key="tab.id"
          type="button"
          role="tab"
          class="subtab"
          :class="{ 'subtab--active': activeTabId === tab.id }"
          :aria-selected="activeTabId === tab.id"
          @click="selectSubTab(tab.id)"
        >
          <i :class="tab.icon" class="subtab__icon" />
          <span class="subtab__label">{{ tab.label }}</span>
        </button>
      </div>
    </div>

    <!-- Tab content -->
    <div class="subtab-content">
      <RegisterAnalysisTab v-if="activeTabId === 'register'" :project-id="projectId" />
      <FocalizationTab v-if="activeTabId === 'focalization'" :project-id="projectId" />
      <SceneTaggingTab v-if="activeTabId === 'scenes'" :project-id="projectId" />
      <StickySentencesTab v-if="activeTabId === 'sticky'" :project-id="projectId" />
      <EchoReportTab v-if="activeTabId === 'echo'" :project-id="projectId" />
      <SentenceVariationTab v-if="activeTabId === 'variation'" :project-id="projectId" />
      <PacingAnalysisTab v-if="activeTabId === 'pacing'" :project-id="projectId" />
      <EmotionalAnalysisTab v-if="activeTabId === 'emotions'" :project-id="projectId" />
      <AgeReadabilityTab v-if="activeTabId === 'readability'" :project-id="projectId" />
      <VitalStatusTab v-if="activeTabId === 'vital'" :project-id="projectId" />
      <CharacterLocationTab v-if="activeTabId === 'locations'" :project-id="projectId" />
      <ChapterProgressTab v-if="activeTabId === 'progress'" :project-id="projectId" />
    </div>
  </div>
</template>

<style scoped>
.style-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Row 1: Category bar */
.category-bar {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: var(--ds-space-1, 0.25rem);
  padding: 0 var(--ds-space-3, 0.75rem);
  height: 36px;
  background-color: var(--ds-surface-ground, var(--surface-ground));
  border-bottom: 1px solid var(--ds-surface-border, var(--surface-border));
}

.category-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-1-5, 0.375rem);
  padding: 0 var(--ds-space-4, 1rem);
  white-space: nowrap;
  border: none;
  background: transparent;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: var(--ds-font-size-sm, 0.8125rem);
  font-weight: var(--ds-font-weight-semibold, 600);
  cursor: pointer;
  position: relative;
  transition: color 0.15s ease, background-color 0.15s ease;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.category-tab:hover {
  color: var(--ds-color-text, var(--text-color));
  background-color: var(--ds-surface-hover, var(--surface-hover));
}

.category-tab:focus-visible {
  outline: 2px solid var(--ds-color-primary, var(--primary-color));
  outline-offset: -2px;
  border-radius: var(--ds-radius-sm, 4px);
}

.category-tab--active {
  color: var(--ds-color-primary, var(--primary-color));
}

.category-tab--active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--ds-space-2, 0.5rem);
  right: var(--ds-space-2, 0.5rem);
  height: 2.5px;
  background-color: var(--ds-color-primary, var(--primary-color));
  border-radius: 2px 2px 0 0;
}

.category-tab__icon {
  font-size: 0.8125rem;
}

.category-tab__label {
  white-space: nowrap;
}

.category-tab__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background-color: var(--ds-surface-border, var(--surface-border));
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1;
}

.category-tab--active .category-tab__count {
  background-color: var(--ds-color-primary, var(--primary-color));
  color: var(--ds-color-primary-contrast, white);
}

/* Row 2: Sub-tabs bar */
.subtabs-bar {
  flex-shrink: 0;
  background-color: var(--ds-surface-card);
  border-bottom: 1px solid var(--ds-surface-border, var(--surface-border));
  overflow: hidden;
}

.subtabs-scroll {
  display: flex;
  align-items: stretch;
  gap: var(--ds-space-1, 0.25rem);
  padding: 0 var(--ds-space-3, 0.75rem);
  height: 36px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--ds-color-text-tertiary, #ccc) transparent;
}

.subtabs-scroll::-webkit-scrollbar {
  height: 3px;
}

.subtabs-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.subtabs-scroll::-webkit-scrollbar-thumb {
  background: var(--ds-color-text-tertiary, #ccc);
  border-radius: 3px;
}

.subtab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-1-5, 0.375rem);
  padding: 0 var(--ds-space-3, 0.75rem);
  white-space: nowrap;
  border: none;
  background: transparent;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: var(--ds-font-size-sm, 0.8125rem);
  font-weight: var(--ds-font-weight-medium, 500);
  cursor: pointer;
  position: relative;
  transition: color 0.15s ease, background-color 0.15s ease;
  flex-shrink: 0;
}

.subtab:hover {
  color: var(--ds-color-text, var(--text-color));
  background-color: var(--ds-surface-hover, var(--surface-hover));
}

.subtab:focus-visible {
  outline: 2px solid var(--ds-color-primary, var(--primary-color));
  outline-offset: -2px;
  border-radius: var(--ds-radius-sm, 4px);
}

.subtab--active {
  color: var(--ds-color-primary, var(--primary-color));
}

.subtab--active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--ds-space-2, 0.5rem);
  right: var(--ds-space-2, 0.5rem);
  height: 2px;
  background-color: var(--ds-color-primary, var(--primary-color));
  border-radius: 1px 1px 0 0;
}

.subtab__icon {
  font-size: 0.875rem;
}

.subtab__label {
  white-space: nowrap;
}

/* Tab content area */
.subtab-content {
  flex: 1;
  overflow: auto;
  padding: var(--ds-space-4, 1rem);
}

/* Responsive: collapse to icons only */
@media (max-width: 768px) {
  .category-tab {
    padding: 0 var(--ds-space-2, 0.5rem);
  }

  .category-tab__label {
    display: none;
  }

  .subtab {
    padding: 0 var(--ds-space-2, 0.5rem);
  }

  .subtab__label {
    display: none;
  }

  .subtab__icon,
  .category-tab__icon {
    font-size: 1.125rem;
  }
}
</style>
