<template>
  <div class="project-detail-view">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando proyecto...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <Message severity="error">{{ error }}</Message>
      <Button label="Volver a Proyectos" icon="pi pi-arrow-left" @click="goBack" />
    </div>

    <!-- Main content -->
    <div v-else-if="project" class="project-layout">
      <!-- Header -->
      <div class="project-header">
        <div class="header-left">
          <Button icon="pi pi-arrow-left" text rounded @click="goBack" />
          <div class="header-info">
            <h1>{{ project.name }}</h1>
            <span class="doc-name" v-if="originalDocumentName">{{ originalDocumentName }}</span>
          </div>
          <DocumentTypeChip
            :project-id="project.id"
            @type-changed="onDocumentTypeChanged"
          />
        </div>
        <div class="header-actions">
          <Button
            icon="pi pi-book"
            outlined
            @click="quickExportStyleGuide"
            :loading="exportingStyleGuide"
            v-tooltip.bottom="'Exportar Guía de Estilo'"
            class="style-guide-btn"
          />
          <Button label="Exportar" icon="pi pi-download" outlined @click="showExportDialog = true" />
          <Button
            :label="isAnalyzing ? 'Analizando...' : (hasBeenAnalyzed ? 'Re-analizar' : 'Analizar')"
            :icon="isAnalyzing ? 'pi pi-spin pi-spinner' : (hasBeenAnalyzed ? 'pi pi-refresh' : 'pi pi-play')"
            :disabled="isAnalyzing"
            @click="showReanalyzeDialog = true"
          />
        </div>
      </div>

      <!-- Export Dialog -->
      <ExportDialog
        :visible="showExportDialog"
        @update:visible="showExportDialog = $event"
        :project-id="project.id"
        :project-name="project.name"
      />

      <!-- Analyze/Reanalyze Confirmation Dialog -->
      <Dialog
        :visible="showReanalyzeDialog"
        @update:visible="showReanalyzeDialog = $event"
        :header="hasBeenAnalyzed ? 'Re-analizar documento' : 'Analizar documento'"
        :modal="true"
        :style="{ width: '450px' }"
      >
        <p class="reanalyze-info">
          <i class="pi pi-info-circle"></i>
          {{ hasBeenAnalyzed ? 'Se volverá a analizar el documento original.' : 'Se analizará el documento para detectar inconsistencias.' }}
        </p>
        <template #footer>
          <Button label="Cancelar" icon="pi pi-times" text @click="showReanalyzeDialog = false" />
          <Button
            :label="hasBeenAnalyzed ? 'Re-analizar' : 'Analizar'"
            :icon="hasBeenAnalyzed ? 'pi pi-refresh' : 'pi pi-play'"
            :loading="reanalyzing"
            :disabled="isAnalyzing"
            @click="startReanalysis"
          />
        </template>
      </Dialog>

      <!-- WORKSPACE TABS - Encima de todo el layout -->
      <!-- Las pestañas se adaptan según el tipo de documento detectado -->
      <WorkspaceTabs
        :entity-count="entitiesCount"
        :alert-count="alertsCount"
        :document-type="project.documentType"
        :recommended-analysis="project.recommendedAnalysis"
      />

      <!-- WORKSPACE CONTENT - Layout contextual según tab activo -->
      <div class="workspace-content">
        <!-- Panel izquierdo (solo si el tab lo requiere) -->
        <Transition name="panel-slide">
          <div
            v-if="workspaceStore.shouldShowLeftPanel"
            class="left-panel"
            :style="{ width: workspaceStore.leftPanel.width + 'px' }"
          >
            <div class="sidebar-container">
              <!-- Tabs icónicos del sidebar -->
              <div class="sidebar-tabs">
                <button
                  v-for="tab in workspaceStore.availableSidebarTabs"
                  :key="tab"
                  class="sidebar-tab-btn"
                  :class="{ active: sidebarTab === tab }"
                  @click="sidebarTab = tab"
                  :title="getSidebarTabTitle(tab)"
                >
                  <i :class="getSidebarTabIcon(tab)"></i>
                  <span v-if="tab === 'alerts' && alertsCount > 0" class="sidebar-badge">
                    {{ alertsCount > 99 ? '99+' : alertsCount }}
                  </span>
                </button>
              </div>

              <!-- Contenido del sidebar -->
              <div class="sidebar-content">
                <!-- Panel Capítulos -->
                <ChaptersPanel
                  v-show="sidebarTab === 'chapters'"
                  :chapters="chapters"
                  :loading="loading"
                  :active-chapter-id="activeChapterId"
                  @chapter-select="onChapterSelect"
                  @section-select="onSectionSelect"
                  @refresh="loadChapters(project.id)"
                />

                <!-- Panel Alertas rápidas -->
                <AlertsPanel
                  v-show="sidebarTab === 'alerts'"
                  :alerts="alerts"
                  @navigate="navigateToAlerts"
                  @filter-severity="handleFilterSeverity"
                />

                <!-- Panel Personajes -->
                <CharactersPanel
                  v-show="sidebarTab === 'characters'"
                  :entities="entities"
                  :max-items="10"
                  @select="onEntitySelect"
                  @view-details="onEntityEdit"
                />

                <!-- Panel Asistente LLM -->
                <AssistantPanel
                  v-show="sidebarTab === 'assistant'"
                  :project-id="project.id"
                />
              </div>
            </div>

            <!-- Resizer izquierdo -->
            <PanelResizer
              position="right"
              :min-size="200"
              :max-size="400"
              @resize="workspaceStore.adjustLeftPanelWidth($event)"
            />
          </div>
        </Transition>

        <!-- Panel central (siempre visible) -->
        <div class="center-panel">
          <!-- Tab Texto -->
          <TextTab
            v-if="workspaceStore.activeTab === 'text'"
            :project-id="project.id"
            :document-title="project.name"
            :alerts="alerts"
            :chapters="chapters"
            :highlight-entity-id="highlightedEntityId"
            :scroll-to-chapter-id="scrollToChapterId"
            :scroll-to-position="workspaceStore.scrollToPosition"
            @chapter-visible="onChapterVisible"
            @entity-click="onEntityClick"
            @alert-click="onAlertClickFromText"
          />

          <!-- Tab Entidades -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'entities'"
            :project-id="project.id"
            required-phase="entities"
            :description="TAB_PHASE_DESCRIPTIONS.entities"
            @analysis-completed="onAnalysisCompleted"
          >
            <EntitiesTab
              :entities="entities"
              :project-id="project.id"
              :loading="loading"
              :initial-entity-id="initialEntityId"
              :chapter-count="chapters.length"
              @entity-select="onEntitySelect"
              @refresh="loadEntities(project.id)"
            />
          </AnalysisRequired>

          <!-- Tab Relaciones -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'relationships'"
            :project-id="project.id"
            required-phase="coreference"
            :description="TAB_PHASE_DESCRIPTIONS.relationships"
            @analysis-completed="onAnalysisCompleted"
          >
            <RelationsTab
              :project-id="project.id"
              :entities="entities"
              :relationships="relationships"
              @entity-select="onEntitySelect"
              @refresh="loadRelationships(project.id)"
            />
          </AnalysisRequired>

          <!-- Tab Alertas -->
          <AlertsTab
            v-else-if="workspaceStore.activeTab === 'alerts'"
            :alerts="alerts"
            :chapters="chapters"
            :loading="loading"
            :analysis-executed="project.analysisStatus === 'completed'"
            @alert-select="onAlertSelect"
            @alert-navigate="onAlertNavigate"
            @alert-resolve="onAlertResolve"
            @alert-dismiss="onAlertDismiss"
            @refresh="loadAlerts(project.id)"
            @open-correction-config="workspaceStore.openCorrectionConfig()"
          />

          <!-- Tab Timeline -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'timeline'"
            :project-id="project.id"
            required-phase="structure"
            :description="TAB_PHASE_DESCRIPTIONS.timeline"
            @analysis-completed="onAnalysisCompleted"
          >
            <TimelineView
              :project-id="project.id"
              :entities="entities"
            />
          </AnalysisRequired>

          <!-- Tab Estilo (siempre disponible, las reglas se aplican durante análisis) -->
          <StyleTab
            v-else-if="workspaceStore.activeTab === 'style'"
            :project-id="project.id"
            :analysis-status="project.analysisStatus"
          />

          <!-- Tab Glosario (siempre disponible) -->
          <GlossaryTab
            v-else-if="workspaceStore.activeTab === 'glossary'"
            :project-id="project.id"
          />

          <!-- Tab Resumen -->
          <ResumenTab
            v-else-if="workspaceStore.activeTab === 'summary'"
            :project="project"
            :entities="entities"
            :alerts="alerts"
            :chapters="chapters"
            @export="showExportDialog = true"
            @export-style-guide="handleExportStyleGuide"
            @export-corrected="handleExportCorrected"
            @re-analyze="showReanalyzeDialog = true"
          />
        </div>

        <!-- Panel derecho / Inspector (solo si el tab lo requiere) -->
        <Transition name="panel-slide">
          <div
            v-if="workspaceStore.shouldShowRightPanel"
            class="right-panel"
            :style="{ width: rightPanelWidth + 'px' }"
          >
            <!-- Resizer derecho -->
            <PanelResizer
              position="left"
              :min-size="250"
              :max-size="500"
              @resize="workspaceStore.adjustRightPanelWidth($event)"
            />

            <div class="inspector-container">
              <div class="inspector-header">
                <span class="inspector-title">{{ inspectorTitle }}</span>
                <Button
                  icon="pi pi-times"
                  text
                  rounded
                  size="small"
                  @click="selectionStore.clearAll()"
                  v-if="selectionStore.hasSelection"
                  v-tooltip="'Cerrar'"
                />
              </div>

              <div class="inspector-content">
                <!-- Entidad seleccionada (prioridad más alta) -->
                <EntityInspector
                  v-if="selectedEntity"
                  :entity="selectedEntity"
                  :project-id="project.id"
                  :alerts="alerts"
                  :chapter-count="chapters.length"
                  @view-details="onEntityEdit(selectedEntity)"
                  @go-to-mentions="handleGoToMentions(selectedEntity)"
                  @close="selectionStore.clearAll()"
                />

                <!-- Alerta seleccionada -->
                <AlertInspector
                  v-else-if="selectedAlert"
                  :alert="selectedAlert"
                  :chapters="chapters"
                  @navigate="onAlertNavigate(selectedAlert, $event)"
                  @resolve="onAlertResolve(selectedAlert)"
                  @dismiss="onAlertDismiss(selectedAlert)"
                  @close="selectionStore.clearAll()"
                />

                <!-- Texto seleccionado -->
                <TextSelectionInspector
                  v-else-if="selectionStore.textSelection"
                  :selection="selectionStore.textSelection"
                  :entities="entities"
                  @close="selectionStore.setTextSelection(null)"
                  @select-entity="onEntityClick"
                  @search-similar="onSearchSimilarText"
                />

                <!-- Capítulo visible en tab texto (contextual) -->
                <ChapterInspector
                  v-else-if="showChapterInspector && currentChapter"
                  :chapter="currentChapter"
                  :project-id="project.id"
                  :entities="entities"
                  :alerts="alerts"
                  @back-to-document="onBackToDocumentSummary"
                  @go-to-start="onGoToChapterStart"
                  @view-alerts="onViewChapterAlerts"
                  @select-entity="onEntityClick"
                />

                <!-- Sin selección ni capítulo visible: resumen del proyecto -->
                <ProjectSummary
                  v-else
                  :word-count="project.wordCount"
                  :chapter-count="project.chapterCount"
                  :entity-count="entitiesCount"
                  :alert-count="alertsCount"
                  @stat-click="handleStatClick"
                />
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Status Bar -->
      <StatusBar
        :word-count="project.wordCount"
        :chapter-count="project.chapterCount"
        :entity-count="entitiesCount"
        :alert-count="alertsCount"
        :has-analysis="(project.wordCount || 0) > 0 || entities.length > 0"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useWorkspaceStore } from '@/stores/workspace'
import { useSelectionStore } from '@/stores/selection'
import { useAnalysisStore, TAB_REQUIRED_PHASES, TAB_PHASE_DESCRIPTIONS, type WorkspaceTab as AnalysisWorkspaceTab } from '@/stores/analysis'
import { useMentionNavigation } from '@/composables/useMentionNavigation'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import ExportDialog from '@/components/ExportDialog.vue'
import StatusBar from '@/components/layout/StatusBar.vue'
import { WorkspaceTabs, TextTab, AlertsTab, EntitiesTab, RelationsTab, StyleTab, GlossaryTab, ResumenTab, PanelResizer } from '@/components/workspace'
import { AnalysisRequired } from '@/components/analysis'
import { TimelineView } from '@/components/timeline'
import { ChaptersPanel, AlertsPanel, CharactersPanel, AssistantPanel } from '@/components/sidebar'
import { ProjectSummary, EntityInspector, AlertInspector, ChapterInspector, TextSelectionInspector } from '@/components/inspector'
import DocumentTypeChip from '@/components/DocumentTypeChip.vue'
import type { SidebarTab } from '@/stores/workspace'
import type { Entity, Alert, Chapter, AlertSource } from '@/types'
import { transformEntities, transformAlerts, transformChapters } from '@/types/transformers'
import { useAlertUtils } from '@/composables/useAlertUtils'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const workspaceStore = useWorkspaceStore()
const selectionStore = useSelectionStore()
const analysisStore = useAnalysisStore()

// Navegación de menciones - usar projectId reactivo
const mentionNav = useMentionNavigation(() => project.value?.id ?? 0)

const loading = ref(true)
const error = ref('')
const showExportDialog = ref(false)
const showReanalyzeDialog = ref(false)
const reanalyzing = ref(false)
const exportingStyleGuide = ref(false)
const entities = ref<Entity[]>([])
const alerts = ref<Alert[]>([])
const chapters = ref<Chapter[]>([])
const relationships = ref<any>(null)

// Estado para sincronización
const activeChapterId = ref<number | null>(null)
const highlightedEntityId = ref<number | null>(null)
const scrollToChapterId = ref<number | null>(null)

// ID de entidad inicial (para navegación desde /characters/:id)
const initialEntityId = ref<number | null>(null)

// Estado del sidebar - se resetea al cambiar de tab principal
const sidebarTab = ref<SidebarTab>('chapters')

// Helpers para sidebar tabs
const getSidebarTabIcon = (tab: SidebarTab): string => {
  const icons: Record<SidebarTab, string> = {
    chapters: 'pi pi-book',
    alerts: 'pi pi-exclamation-triangle',
    characters: 'pi pi-users',
    assistant: 'pi pi-comments'
  }
  return icons[tab]
}

const getSidebarTabTitle = (tab: SidebarTab): string => {
  const titles: Record<SidebarTab, string> = {
    chapters: 'Capítulos',
    alerts: 'Alertas',
    characters: 'Personajes',
    assistant: 'Asistente'
  }
  return titles[tab]
}

const project = computed(() => projectsStore.currentProject)

// Estado del análisis con polling
const analysisProgressData = ref<{ progress: number; phase: string; error?: string; metrics?: { chapters_found?: number; entities_found?: number } } | null>(null)
let analysisPollingInterval: ReturnType<typeof setInterval> | null = null
// Track what was already loaded during this analysis session
let chaptersLoadedDuringAnalysis = false
let entitiesLoadedDuringAnalysis = false
let alertsLoadedDuringAnalysis = false

const isAnalyzing = computed(() => {
  if (!project.value) return false
  const status = project.value.analysisStatus
  // Solo estados activos de análisis deshabilitan el botón
  // Si el status es null, undefined, 'completed', 'error', etc. - permitir re-analizar
  const activeStatuses = ['pending', 'in_progress', 'analyzing']
  return status ? activeStatuses.includes(status) : false
})

/** Indica si el proyecto ya fue analizado alguna vez (tiene capítulos o entidades) */
const hasBeenAnalyzed = computed(() => {
  if (!project.value) return false
  return (project.value.chapterCount || 0) > 0 || (project.value.entityCount || 0) > 0
})

const analysisProgress = computed(() => {
  // Usar datos de polling si están disponibles
  if (analysisProgressData.value) {
    return analysisProgressData.value.progress
  }
  if (!project.value) return 0
  return Math.round((project.value.analysisProgress || 0) * 100)
})

const analysisPhase = computed(() => {
  return analysisProgressData.value?.phase || 'Analizando...'
})

// Polling del progreso de análisis
async function pollAnalysisProgress() {
  if (!project.value) {
    console.log('[Polling] No project, stopping polling')
    stopAnalysisPolling()
    return
  }

  try {
    console.log('[Polling] Fetching progress for project', project.value.id)
    // Usar el store para obtener el progreso (actualiza estado global)
    const progressData = await analysisStore.getProgress(project.value.id)
    console.log('[Polling] Progress data:', progressData)

    // Si no hay datos de progreso, significa que no hay análisis activo
    // Detener el polling para evitar llamadas innecesarias
    if (!progressData) {
      console.log('[Polling] No progress data returned, stopping polling')
      stopAnalysisPolling()
      analysisProgressData.value = null
      return
    }

    analysisProgressData.value = {
      progress: progressData.progress || 0,
      phase: progressData.current_phase || 'Analizando...',
      error: progressData.error,
      metrics: progressData.metrics
    }

    // Si hay capítulos disponibles y aún no los cargamos, cargarlos ahora
    const chaptersFound = progressData.metrics?.chapters_found
    if (chaptersFound && chaptersFound > 0 && !chaptersLoadedDuringAnalysis && chapters.value.length === 0) {
      console.log('[Polling] Chapters found in analysis, loading chapters:', chaptersFound)
      chaptersLoadedDuringAnalysis = true
      loadChapters(project.value!.id)
    }

    // Si hay entidades disponibles y aún no las cargamos, cargarlas ahora
    const entitiesFound = progressData.metrics?.entities_found
    if (entitiesFound && entitiesFound > 0 && !entitiesLoadedDuringAnalysis && entities.value.length === 0) {
      console.log('[Polling] Entities found in analysis, loading entities:', entitiesFound)
      entitiesLoadedDuringAnalysis = true
      loadEntities(project.value!.id)
    }

    // Cargar alertas cuando la fase grammar esté completada (las alertas se van generando)
    const grammarPhase = progressData.phases?.find((p: { id: string }) => p.id === 'grammar')
    if (grammarPhase?.completed && !alertsLoadedDuringAnalysis && alerts.value.length === 0) {
      console.log('[Polling] Grammar phase completed, loading alerts')
      alertsLoadedDuringAnalysis = true
      loadAlerts(project.value!.id)
    }

    // Si idle (no hay análisis activo), detener polling silenciosamente
    if (progressData.status === 'idle') {
      console.log('[Polling] No active analysis (idle), stopping polling')
      stopAnalysisPolling()
      analysisProgressData.value = null
      return
    }

    // Si completado o error, detener polling y recargar datos
    if (progressData.status === 'completed' || progressData.status === 'error' || progressData.status === 'failed') {
      console.log('[Polling] Analysis finished with status:', progressData.status)
      stopAnalysisPolling()

      // Pequeño delay para asegurar que la BD se haya actualizado completamente
      // (el análisis corre en background thread y puede haber una condición de carrera)
      await new Promise(resolve => setTimeout(resolve, 500))

      // Recargar proyecto y datos
      await projectsStore.fetchProject(project.value!.id)
      // Recargar fases ejecutadas para actualizar tabs
      await analysisStore.loadExecutedPhases(project.value!.id)
      await loadEntities(project.value!.id)
      await loadAlerts(project.value!.id)
      await loadChapters(project.value!.id)
      analysisProgressData.value = null

      // Verificar que los datos se cargaron correctamente
      // Si wordCount sigue siendo 0 pero hay capítulos, reintentar
      if (project.value && project.value.wordCount === 0 && (progressData.metrics?.chapters_found || 0) > 0) {
        console.log('[Polling] Data seems stale, retrying fetch after delay...')
        await new Promise(resolve => setTimeout(resolve, 1000))
        await projectsStore.fetchProject(project.value.id)
        await loadChapters(project.value.id)
      }
    }
  } catch (err) {
    console.error('Error polling analysis progress:', err)
    // Si hay error de red o el endpoint no responde, detener polling
    // para evitar spam de errores
    console.log('[Polling] Stopping polling due to error')
    stopAnalysisPolling()
  }
}

function startAnalysisPolling() {
  if (analysisPollingInterval) return
  // Reset the flags when starting a new polling session
  chaptersLoadedDuringAnalysis = false
  entitiesLoadedDuringAnalysis = false
  alertsLoadedDuringAnalysis = false
  analysisPollingInterval = setInterval(pollAnalysisProgress, 1500)
  // Hacer primera llamada inmediatamente
  pollAnalysisProgress()
}

function stopAnalysisPolling() {
  if (analysisPollingInterval) {
    clearInterval(analysisPollingInterval)
    analysisPollingInterval = null
  }
}

// Iniciar/detener polling cuando cambia el estado de análisis
watch(isAnalyzing, (analyzing, oldAnalyzing) => {
  console.log('[Analysis] isAnalyzing changed:', oldAnalyzing, '->', analyzing)
  if (analyzing) {
    startAnalysisPolling()
  } else {
    stopAnalysisPolling()
  }
}, { immediate: true })

// También observar cambios en el proyecto para detectar análisis
watch(() => project.value?.analysisStatus, (newStatus, oldStatus) => {
  console.log('[Analysis] project.analysisStatus changed:', oldStatus, '->', newStatus)
  if (newStatus === 'pending' || newStatus === 'in_progress' || newStatus === 'analyzing') {
    if (!analysisPollingInterval) {
      console.log('[Analysis] Starting polling from status change')
      startAnalysisPolling()
    }
  }
})

// Observar selectedEntityForMentions para cargar y navegar a menciones
watch(() => workspaceStore.selectedEntityForMentions, async (entityId) => {
  if (entityId !== null && project.value) {
    // Cargar menciones de la entidad y navegar a la primera
    await mentionNav.startNavigation(entityId)
    // Limpiar el valor para permitir re-seleccionar la misma entidad
    workspaceStore.selectedEntityForMentions = null
  }
})

// Computed: nombre original del documento (sin prefijo hash)
const originalDocumentName = computed(() => {
  if (!project.value?.documentPath) return null
  const filename = project.value.documentPath.split('/').pop() || project.value.documentPath
  const match = filename.match(/^[a-f0-9]{32}_(.+)$/)
  return match ? match[1] : filename
})

// Stats
const entitiesCount = computed(() => entities.value.length)
const alertsCount = computed(() => alerts.value.length)

// Alertas agrupadas por severidad para sidebar
const alertsBySeverity = computed(() => {
  const counts: Record<string, number> = {}
  for (const alert of alerts.value) {
    if (alert.status === 'active') {
      counts[alert.severity] = (counts[alert.severity] || 0) + 1
    }
  }
  return counts
})

// Top personajes para sidebar
const topCharacters = computed(() => {
  return entities.value
    .filter(e => e.type === 'character')
    .sort((a, b) => (b.mentionCount || 0) - (a.mentionCount || 0))
    .slice(0, 10)
})

// Entidad seleccionada para inspector
const selectedEntity = computed(() => {
  if (selectionStore.primary?.type !== 'entity') return null
  return entities.value.find(e => e.id === selectionStore.primary?.id) || null
})

// Alerta seleccionada para inspector
const selectedAlert = computed(() => {
  if (selectionStore.primary?.type !== 'alert') return null
  return alerts.value.find(a => a.id === selectionStore.primary?.id) || null
})

// Capítulo actual para el inspector contextual
const currentChapter = computed(() => {
  if (!activeChapterId.value) return null
  return chapters.value.find(c => c.id === activeChapterId.value) || null
})

// Determinar si mostrar ChapterInspector contextualmente
// Se muestra cuando: estamos en tab texto, hay un capítulo visible, y no hay selección explícita
const showChapterInspector = computed(() => {
  return workspaceStore.activeTab === 'text' &&
         currentChapter.value !== null &&
         !selectionStore.hasSelection
})

// Título del inspector
const inspectorTitle = computed(() => {
  if (selectedEntity.value) return 'Entidad'
  if (selectedAlert.value) return 'Alerta'
  if (selectionStore.textSelection) return 'Selección'
  if (showChapterInspector.value) return 'Capítulo'
  return 'Resumen'
})

// Ancho del panel derecho (usa el preferido del tab si existe)
const rightPanelWidth = computed(() => {
  const preferredWidth = workspaceStore.currentLayoutConfig.rightPanelWidth
  return preferredWidth ?? workspaceStore.rightPanel.width
})

// Usar composable centralizado para alertas
const { getSeverityConfig } = useAlertUtils()

// Helper para label de severidad
const getSeverityLabel = (severity: string) => {
  return getSeverityConfig(severity as any).label
}

// Helper para label de tipo de entidad
const getEntityTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    character: 'Personaje',
    location: 'Lugar',
    object: 'Objeto',
    organization: 'Organización',
    event: 'Evento',
    concept: 'Concepto',
    other: 'Otro'
  }
  return labels[type] || type
}

const getEntityIcon = (type: string) => {
  const icons: Record<string, string> = {
    character: 'pi pi-user',
    location: 'pi pi-map-marker',
    organization: 'pi pi-building',
    object: 'pi pi-box',
    event: 'pi pi-calendar',
    concept: 'pi pi-lightbulb',
    other: 'pi pi-tag'
  }
  return icons[type] || 'pi pi-tag'
}

// Handle menu events for tab switching
const handleMenuTabEvent = (event: Event) => {
  const customEvent = event as CustomEvent<{ tab: string }>
  if (customEvent.detail?.tab) {
    workspaceStore.setActiveTab(customEvent.detail.tab as any)
  }
}

onMounted(async () => {
  const projectId = parseInt(route.params.id as string)

  if (isNaN(projectId)) {
    error.value = 'ID de proyecto inválido'
    loading.value = false
    return
  }

  // Listen for menu tab change events
  window.addEventListener('menubar:view-tab', handleMenuTabEvent)

  try {
    // Resetear workspace al entrar
    workspaceStore.reset()

    // Check for tab query parameter
    const tabParam = route.query.tab as string
    if (tabParam && ['text', 'entities', 'relations', 'alerts', 'style', 'resumen'].includes(tabParam)) {
      workspaceStore.setActiveTab(tabParam as any)
    }

    // Check for entity query parameter (para navegación desde /characters/:id)
    const entityParam = route.query.entity as string
    if (entityParam) {
      initialEntityId.value = parseInt(entityParam)
    }

    await projectsStore.fetchProject(projectId)
    // Cargar fases ejecutadas para mostrar tabs condicionalmente
    await analysisStore.loadExecutedPhases(projectId)
    await loadEntities(projectId)
    await loadAlerts(projectId)
    await loadChapters(projectId)
    await loadRelationships(projectId)

    // Check for alert query parameter (para navegación desde AlertsView)
    const alertParam = route.query.alert as string
    if (alertParam) {
      const alertId = parseInt(alertParam)
      const targetAlert = alerts.value.find(a => a.id === alertId)
      if (targetAlert && targetAlert.spanStart !== undefined) {
        // Convertir chapter number a chapter ID
        const targetChapter = chapters.value.find(c => c.chapterNumber === targetAlert.chapter)
        const chapterId = targetChapter?.id ?? null

        // Navegar a la posición de la alerta en el texto
        workspaceStore.navigateToTextPosition(
          targetAlert.spanStart,
          targetAlert.excerpt || undefined,
          chapterId
        )
        // Seleccionar la alerta en el inspector
        selectionStore.selectAlert(targetAlert)
      }
    }

    // Verificar si hay un análisis en curso (por si se refrescó la página)
    const hasActiveAnalysis = await analysisStore.checkAnalysisStatus(projectId)
    if (hasActiveAnalysis) {
      startAnalysisPolling()
    }

    loading.value = false
  } catch (err) {
    error.value = projectsStore.error || 'Error cargando proyecto'
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('menubar:view-tab', handleMenuTabEvent)
  stopAnalysisPolling()
})

const loadEntities = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/entities`)
    const data = await response.json()
    if (data.success) {
      entities.value = transformEntities(data.data || [])
    }
  } catch (err) {
    console.error('Error loading entities:', err)
  }
}

const loadAlerts = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/alerts?status=open`)
    const data = await response.json()
    if (data.success) {
      alerts.value = transformAlerts(data.data || [])
    }
  } catch (err) {
    console.error('Error loading alerts:', err)
  }
}

const loadChapters = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/chapters`)
    const data = await response.json()
    if (data.success) {
      chapters.value = transformChapters(data.data || [])
    }
  } catch (err) {
    console.error('Error loading chapters:', err)
    // Fallback
    if (project.value) {
      chapters.value = Array.from({ length: project.value.chapterCount }, (_, i) => ({
        id: i + 1,
        projectId: projectId,
        title: `Capítulo ${i + 1}`,
        content: '',
        chapterNumber: i + 1,
        wordCount: Math.floor(project.value!.wordCount / project.value!.chapterCount),
        positionStart: 0,
        positionEnd: 0
      }))
    }
  }
}

const loadRelationships = async (projectId: number) => {
  try {
    const response = await fetch(`/api/projects/${projectId}/relationships`)
    const data = await response.json()
    if (data.success) {
      relationships.value = data.data
    }
  } catch (err) {
    console.error('Error loading relationships:', err)
  }
}

const goBack = () => {
  router.push({ name: 'projects' })
}

// Navegación y sincronización
const onChapterSelect = (chapterId: number) => {
  scrollToChapterId.value = chapterId
  activeChapterId.value = chapterId
  workspaceStore.setActiveTab('text')
  setTimeout(() => { scrollToChapterId.value = null }, 500)
}

const onSectionSelect = (chapterId: number, _sectionId: number, startChar: number) => {
  activeChapterId.value = chapterId
  // Usar la función del store para navegar a la posición
  workspaceStore.navigateToTextPosition(startChar)
}

// Debounce para cambios de capítulo visible (evita actualizaciones rápidas durante scroll)
let chapterVisibleTimeout: ReturnType<typeof setTimeout> | null = null
const onChapterVisible = (chapterId: number) => {
  // Clear pending timeout
  if (chapterVisibleTimeout) {
    clearTimeout(chapterVisibleTimeout)
  }
  // Debounce 400ms para evitar cambios rápidos durante scroll
  chapterVisibleTimeout = setTimeout(() => {
    activeChapterId.value = chapterId
    workspaceStore.setCurrentChapter(chapterId)
  }, 400)
}

const onEntityClick = (entityId: number) => {
  highlightedEntityId.value = entityId
  const entity = entities.value.find(e => e.id === entityId)
  if (entity) {
    selectionStore.selectEntity(entity)
  }
}

const onEntitySelect = (entity: Entity) => {
  highlightedEntityId.value = entity.id
  selectionStore.selectEntity(entity)
}

const onEntityEdit = (entity: Entity) => {
  // Navegar a la pestaña de entidades con esta entidad seleccionada
  initialEntityId.value = entity.id
  workspaceStore.setActiveTab('entities')
}

const onAlertSelect = (alert: Alert) => {
  selectionStore.selectAlert(alert)
}

const onAlertClickFromText = (alert: Alert) => {
  selectionStore.selectAlert(alert)
}

/**
 * Navega al texto de una alerta.
 * Si se proporciona un source (para inconsistencias), navega a la ubicación de ese source
 * en lugar de la ubicación principal de la alerta.
 */
const onAlertNavigate = (alert: Alert, source?: AlertSource) => {
  // Convertir chapter NUMBER a chapter ID si es necesario
  const getChapterId = (chapterNumber: number | undefined | null): number | null => {
    if (chapterNumber === undefined || chapterNumber === null) return null
    const chapter = chapters.value.find(c => c.chapterNumber === chapterNumber)
    return chapter?.id ?? null
  }

  // Si hay un source específico, usar sus datos de ubicación
  const targetChapter = source?.chapter ?? alert.chapter
  const targetPosition = source?.startChar ?? alert.spanStart
  const targetExcerpt = source?.excerpt ?? alert.excerpt

  // Navegar al texto con posición precisa si está disponible
  if (targetPosition !== undefined) {
    // Obtener el ID del capítulo a partir del número
    const chapterId = getChapterId(targetChapter)

    // Usar navigateToTextPosition para scroll preciso con resaltado
    workspaceStore.navigateToTextPosition(
      targetPosition,
      targetExcerpt || undefined,
      chapterId
    )
  } else if (targetChapter !== undefined && targetChapter !== null) {
    // Fallback: solo navegar al capítulo si no hay posición exacta
    const chapter = chapters.value.find(c => c.chapterNumber === targetChapter)
    if (chapter) {
      scrollToChapterId.value = chapter.id
      activeChapterId.value = chapter.id
      workspaceStore.setActiveTab('text')
      setTimeout(() => { scrollToChapterId.value = null }, 500)
    }
  }
}

const onAlertResolve = async (alert: Alert) => {
  try {
    const projectId = project.value!.id
    const response = await fetch(`/api/projects/${projectId}/alerts/${alert.id}/resolve`, { method: 'POST' })
    if (response.ok) {
      await loadAlerts(projectId)
      selectionStore.clearAll()
    }
  } catch (err) {
    console.error('Error resolving alert:', err)
  }
}

const onAlertDismiss = async (alert: Alert) => {
  try {
    const projectId = project.value!.id
    const response = await fetch(`/api/projects/${projectId}/alerts/${alert.id}/dismiss`, { method: 'POST' })
    if (response.ok) {
      await loadAlerts(projectId)
      selectionStore.clearAll()
    }
  } catch (err) {
    console.error('Error dismissing alert:', err)
  }
}

const navigateToAlerts = () => {
  workspaceStore.setActiveTab('alerts')
}

const handleFilterSeverity = (severity: string) => {
  workspaceStore.setAlertSeverityFilter(severity)
  workspaceStore.setActiveTab('alerts')
}

const handleStatClick = (stat: 'words' | 'chapters' | 'entities' | 'alerts') => {
  switch (stat) {
    case 'entities':
      workspaceStore.setActiveTab('entities')
      break
    case 'alerts':
      workspaceStore.setActiveTab('alerts')
      break
    case 'chapters':
      // Mantener en text tab y mostrar capítulos en sidebar
      workspaceStore.setActiveTab('text')
      sidebarTab.value = 'chapters'
      break
    default:
      // words - ir al texto
      workspaceStore.setActiveTab('text')
  }
}

const handleGoToMentions = (entity: Entity) => {
  workspaceStore.navigateToEntityMentions(entity.id)
  highlightedEntityId.value = entity.id
}

// ChapterInspector handlers
const onBackToDocumentSummary = () => {
  // Clear the active chapter to show document summary
  activeChapterId.value = null
  workspaceStore.setCurrentChapter(null)
}

const onGoToChapterStart = () => {
  // Scroll to the start of the current chapter
  if (currentChapter.value) {
    scrollToChapterId.value = currentChapter.value.id
    setTimeout(() => { scrollToChapterId.value = null }, 500)
  }
}

const onViewChapterAlerts = () => {
  // Navigate to alerts tab - could filter by chapter if needed
  if (currentChapter.value) {
    workspaceStore.setActiveTab('alerts')
    // The alerts tab will show all alerts, user can filter as needed
  }
}

// TextSelectionInspector handlers
const onSearchSimilarText = (text: string) => {
  // Por ahora solo limpiamos la selección y mostramos un mensaje en consola
  // En el futuro podría abrir el asistente LLM con el texto seleccionado
  console.log('Search similar text:', text.substring(0, 50) + '...')
  selectionStore.setTextSelection(null)
  // Podría activar el sidebar del asistente con el texto como contexto
  sidebarTab.value = 'assistant'
}

const handleExportStyleGuide = () => {
  showExportDialog.value = true
}

const handleExportCorrected = async () => {
  if (!project.value) return

  try {
    // Descargar documento con correcciones como Track Changes
    const url = `/api/projects/${project.value.id}/export/corrected?min_confidence=0.5&as_track_changes=true`

    const response = await fetch(url)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || 'Error al exportar documento corregido')
    }

    // Obtener el blob del documento
    const blob = await response.blob()

    // Obtener nombre del archivo del header o usar default
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = 'documento_corregido.docx'
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/)
      if (match) filename = match[1]
    }

    // Descargar
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)

  } catch (err) {
    console.error('Error exporting corrected document:', err)
    alert(err instanceof Error ? err.message : 'Error al exportar documento corregido')
  }
}

const quickExportStyleGuide = async () => {
  if (!project.value) return

  exportingStyleGuide.value = true

  try {
    // Exportar directamente en formato Markdown (el más común para correctores)
    const response = await fetch(`/api/projects/${project.value.id}/style-guide?format=markdown`)

    if (!response.ok) {
      throw new Error('Error al exportar guía de estilo')
    }

    const data = await response.json()

    if (data.success) {
      const content = data.data.content
      const filename = `guia_estilo_${project.value.name}_${Date.now()}.md`

      // Descargar archivo
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (err) {
    console.error('Error exporting style guide:', err)
    error.value = 'No se pudo exportar la guía de estilo'
  } finally {
    exportingStyleGuide.value = false
  }
}

/**
 * Handler cuando un análisis parcial se completa (desde AnalysisRequired).
 * Recarga los datos relevantes para la tab actual.
 */
const onAnalysisCompleted = async () => {
  if (!project.value) return

  // Recargar fases ejecutadas
  await analysisStore.loadExecutedPhases(project.value.id)

  // Recargar datos según el tab activo
  const activeTab = workspaceStore.activeTab
  if (activeTab === 'entities') {
    await loadEntities(project.value.id)
  } else if (activeTab === 'relationships') {
    await loadEntities(project.value.id)
    await loadRelationships(project.value.id)
  } else if (activeTab === 'alerts') {
    await loadAlerts(project.value.id)
  }
  // Timeline y Style cargan sus propios datos
}

const onDocumentTypeChanged = async (type: string, subtype: string | null) => {
  // Recargar el proyecto para obtener el nuevo perfil de features
  if (project.value) {
    await projectsStore.fetchProject(project.value.id)
  }
}

const startReanalysis = async () => {
  if (!project.value) return
  reanalyzing.value = true
  showReanalyzeDialog.value = false

  // Resetear contadores inmediatamente para mostrar 0 durante el análisis
  entities.value = []
  alerts.value = []

  // Activar el estado de análisis en el store para que StatusBar lo muestre
  analysisStore.setAnalyzing(project.value.id, true)

  try {
    const response = await fetch(`/api/projects/${project.value.id}/reanalyze`, { method: 'POST' })
    const data = await response.json()

    if (data.success) {
      // El proyecto ahora está en estado "analyzing", iniciar polling
      await projectsStore.fetchProject(project.value.id)
      // No cargar entidades/alertas aquí - se cargarán cuando termine el análisis
    } else {
      error.value = data.error || 'Error al re-analizar'
      // En caso de error, recargar los datos originales
      analysisStore.setAnalyzing(project.value.id, false)
      await loadEntities(project.value.id)
      await loadAlerts(project.value.id)
    }
  } catch (err) {
    error.value = 'Error de conexión'
    // En caso de error, recargar los datos originales
    if (project.value) {
      analysisStore.setAnalyzing(project.value.id, false)
      await loadEntities(project.value.id)
      await loadAlerts(project.value.id)
    }
  } finally {
    reanalyzing.value = false
  }
}
</script>

<style scoped>
.project-detail-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
  overflow: hidden;
}

/* Loading & Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
}

/* Layout */
.project-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* Header */
.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-left > :deep(.document-type-chip) {
  align-self: flex-end;
  margin-left: 0.5rem;
}

.header-info h1 {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-color);
}

.doc-name {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.style-guide-btn {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.style-guide-btn:hover {
  background: var(--primary-100);
}

/* Sidebar */
.sidebar-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.sidebar-tabs {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
  flex-shrink: 0;
}

.sidebar-tab-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-color-secondary);
  transition: all 0.15s;
}

.sidebar-tab-btn:hover {
  background: var(--surface-hover);
  color: var(--text-color);
}

.sidebar-tab-btn.active {
  background: var(--primary-100);
  color: var(--primary-color);
}

.sidebar-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  font-size: 0.625rem;
  font-weight: 600;
  background: var(--red-500);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
}

.sidebar-panel {
  height: 100%;
  overflow-y: auto;
}

.mini-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
  border-bottom: 1px solid var(--surface-border);
}

.mini-count {
  background: var(--surface-200);
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.severity-list {
  padding: 0.5rem;
}

.severity-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.severity-row:hover {
  background: var(--surface-hover);
}

.severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-critical { background: var(--red-500); }
.dot-high { background: var(--orange-500); }
.dot-medium { background: var(--yellow-500); }
.dot-low { background: var(--blue-500); }
.dot-info { background: var(--gray-400); }

.severity-label {
  flex: 1;
  font-size: 0.8125rem;
}

.severity-count {
  font-weight: 600;
  font-size: 0.8125rem;
}

.characters-list {
  padding: 0.5rem;
}

.character-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.character-item:hover {
  background: var(--surface-hover);
}

.character-item.active {
  background: var(--primary-100);
}

.character-item i {
  color: var(--text-color-secondary);
}

.char-name {
  flex: 1;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.char-mentions {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

/* Workspace content - layout de 3 paneles */
.workspace-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.left-panel {
  display: flex;
  flex-shrink: 0;
  background: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  position: relative;
  box-sizing: border-box;
}

.center-panel {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.right-panel {
  display: flex;
  flex-shrink: 0;
  background: var(--surface-card);
  border-left: 1px solid var(--surface-border);
  position: relative;
}

/* Animación de paneles */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.25s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.right-panel.panel-slide-enter-from,
.right-panel.panel-slide-leave-to {
  transform: translateX(20px);
}

/* Inspector */
.inspector-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.inspector-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  font-weight: 600;
  font-size: 0.875rem;
}

.inspector-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.inspector-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-stat {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.summary-stat i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.summary-stat .stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.summary-stat .stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  display: block;
}

.inspector-entity,
.inspector-alert {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.entity-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.entity-header i {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.entity-header h3 {
  margin: 0;
  font-size: 1.125rem;
}

.entity-type-label {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.entity-aliases {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.entity-aliases .label {
  font-weight: 500;
}

.entity-mentions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.alert-severity {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  width: fit-content;
}

.severity-critical { background: var(--red-100); color: var(--red-700); }
.severity-high { background: var(--orange-100); color: var(--orange-700); }
.severity-medium { background: var(--yellow-100); color: var(--yellow-700); }
.severity-low { background: var(--blue-100); color: var(--blue-700); }
.severity-info { background: var(--gray-100); color: var(--gray-700); }

.inspector-alert h3 {
  margin: 0;
  font-size: 1rem;
}

.inspector-alert p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  line-height: 1.5;
}

.alert-location {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.alert-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

/* Reanalyze dialog */
.reanalyze-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--blue-50);
  border-radius: 6px;
  border-left: 4px solid var(--blue-500);
  color: var(--blue-900);
  font-size: 0.9rem;
  margin: 0;
}

.reanalyze-info i {
  font-size: 1.25rem;
}

/* Dark mode */
.dark .sidebar-tab-btn.active {
  background: var(--primary-900);
}

.dark .character-item.active {
  background: var(--primary-900);
}

.dark .summary-stat {
  background: var(--surface-700);
}

.dark .reanalyze-info {
  background: var(--blue-900);
  color: var(--blue-100);
}
</style>
