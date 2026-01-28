<script setup lang="ts">
/**
 * StyleTab - Pestana de Escritura y Análisis
 *
 * Contiene todos los análisis de escritura: registro narrativo,
 * focalización, oraciones, repeticiones, ritmo, emociones, etc.
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

interface SubTab {
  id: string
  label: string
  icon: string
  component: string
  featureKey?: string
}

const props = defineProps<{
  projectId: number
  analysisStatus?: string
}>()

const workspaceStore = useWorkspaceStore()
const { isFeatureAvailable } = useFeatureProfile(computed(() => props.projectId))

const activeTabId = ref('register')

// Feature availability
const hasScenes = ref(false)

// All possible sub-tabs
const allSubTabs: SubTab[] = [
  { id: 'register', label: 'Registro', icon: 'pi pi-sliders-v', component: 'RegisterAnalysisTab' },
  { id: 'focalization', label: 'Focalización', icon: 'pi pi-eye', component: 'FocalizationTab' },
  { id: 'scenes', label: 'Escenas', icon: 'pi pi-images', component: 'SceneTaggingTab', featureKey: 'scenes' },
  { id: 'sticky', label: 'Densidad', icon: 'pi pi-align-left', component: 'StickySentencesTab', featureKey: 'sticky_sentences' },
  { id: 'echo', label: 'Ecos', icon: 'pi pi-replay', component: 'EchoReportTab', featureKey: 'echo_repetitions' },
  { id: 'variation', label: 'Variación', icon: 'pi pi-chart-bar', component: 'SentenceVariationTab', featureKey: 'sentence_variation' },
  { id: 'pacing', label: 'Ritmo', icon: 'pi pi-forward', component: 'PacingAnalysisTab', featureKey: 'pacing' },
  { id: 'emotions', label: 'Emociones', icon: 'pi pi-heart', component: 'EmotionalAnalysisTab', featureKey: 'emotional_analysis' },
  { id: 'readability', label: 'Legibilidad', icon: 'pi pi-users', component: 'AgeReadabilityTab', featureKey: 'age_readability' },
  { id: 'vital', label: 'Estado vital', icon: 'pi pi-heart-fill', component: 'VitalStatusTab', featureKey: 'vital_status' },
  { id: 'locations', label: 'Ubicaciones', icon: 'pi pi-map-marker', component: 'CharacterLocationTab', featureKey: 'character_location' },
  { id: 'progress', label: 'Progreso', icon: 'pi pi-chart-line', component: 'ChapterProgressTab', featureKey: 'chapter_progress' },
]

// Filtered sub-tabs based on feature availability
const visibleSubTabs = computed(() => {
  return allSubTabs.filter(tab => {
    if (!tab.featureKey) return true
    if (tab.id === 'scenes') return hasScenes.value && isFeatureAvailable(tab.featureKey)
    return isFeatureAvailable(tab.featureKey)
  })
})

// Watch for external navigation requests
watch(() => workspaceStore.styleTabSubtab, (newSubtab) => {
  if (newSubtab !== null) {
    const tab = visibleSubTabs.value[newSubtab]
    if (tab) {
      activeTabId.value = tab.id
    }
    workspaceStore.clearStyleTabSubtab()
  }
}, { immediate: true })

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
    <!-- Sub-tabs bar (same style as workspace tabs) -->
    <div class="subtabs-bar" role="tablist" aria-label="Análisis de escritura">
      <div class="subtabs-scroll">
        <button
          v-for="tab in visibleSubTabs"
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

/* Sub-tabs bar: same visual style as workspace-tabs */
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
  height: 40px;
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

/* Responsive: hide labels when too narrow */
@media (max-width: 768px) {
  .subtab {
    padding: 0 var(--ds-space-2, 0.5rem);
  }

  .subtab__label {
    display: none;
  }

  .subtab__icon {
    font-size: 1.125rem;
  }
}
</style>
