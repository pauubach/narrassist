<template>
  <div class="project-detail-view">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <DsSkeleton variant="list" :rows="5" />
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
          <Button icon="pi pi-arrow-left" label="Proyectos" text rounded aria-label="Volver a proyectos" class="back-btn" @click="goBack" />
          <div class="header-info">
            <h1>{{ project.name }}</h1>
            <div class="header-meta">
              <span v-if="originalDocumentName" class="doc-name">{{ originalDocumentName }}</span>
              <DocumentTypeChip
                :project-id="project.id"
                @type-changed="onDocumentTypeChanged"
                @open-correction-settings="correctionConfigModalRef?.show()"
              />
            </div>
          </div>
        </div>
        <div class="header-actions">
          <Button
            v-tooltip.bottom="'Exportar Guía de Estilo'"
            icon="pi pi-book"
            outlined
            :loading="exportingStyleGuide"
            class="style-guide-btn"
            aria-label="Exportar Guía de Estilo"
            @click="quickExportStyleGuide"
          />
          <Button label="Exportar" icon="pi pi-download" outlined @click="showExportDialog = true" />
          <Button
            v-if="isAnalyzing"
            label="Cancelar análisis"
            icon="pi pi-times"
            severity="danger"
            outlined
            :loading="cancellingAnalysis"
            @click="handleCancelAnalysis"
          />
          <Button
            v-else
            :label="hasBeenAnalyzed ? 'Re-analizar' : 'Analizar'"
            :icon="hasBeenAnalyzed ? 'pi pi-refresh' : 'pi pi-play'"
            @click="showReanalyzeDialog = true"
          />
        </div>
      </div>

      <!-- Export Dialog -->
      <ExportDialog
        :visible="showExportDialog"
        :project-id="project.id"
        :project-name="project.name"
        @update:visible="showExportDialog = $event"
      />

      <!-- Correction Config Modal -->
      <CorrectionConfigModal
        ref="correctionConfigModalRef"
        :project-id="project.id"
        @saved="loadAlerts(project.id)"
      />

      <!-- Analyze/Reanalyze Confirmation Dialog -->
      <Dialog
        :visible="showReanalyzeDialog"
        :header="hasBeenAnalyzed ? 'Re-analizar documento' : 'Analizar documento'"
        :modal="true"
        :style="{ width: '450px' }"
        @update:visible="showReanalyzeDialog = $event"
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
        :alert-count="unresolvedAlertCount"
        :total-alert-count="alertsCount"
        :tab-statuses="tabStatuses"
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
              <div class="sidebar-tabs" role="tablist" aria-label="Panel lateral">
                <button
                  v-for="tab in workspaceStore.availableSidebarTabs"
                  :key="tab"
                  role="tab"
                  class="sidebar-tab-btn"
                  :class="{ active: sidebarTab === tab }"
                  :aria-selected="sidebarTab === tab"
                  :aria-label="getSidebarTabTitle(tab)"
                  :title="getSidebarTabTitle(tab)"
                  @click="sidebarTab = tab"
                >
                  <i :class="getSidebarTabIcon(tab)"></i>
                  <span v-if="tab === 'alerts' && alertsCount > 0" class="sidebar-badge">
                    {{ alertsCount > 99 ? '99+' : alertsCount }}
                  </span>
                  <span v-if="tab === 'history' && undoableCount > 0" class="sidebar-badge sidebar-badge--history">
                    {{ undoableCount > 99 ? '99+' : undoableCount }}
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
                  @alert-click="onAlertSelect"
                  @alert-navigate="onAlertNavigate"
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

                <!-- Panel Historial -->
                <HistoryPanel
                  v-show="sidebarTab === 'history'"
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
            ref="textTabRef"
            v-if="workspaceStore.activeTab === 'text'"
            :project-id="project.id"
            :document-title="project.name"
            :alerts="alerts"
            :chapters="chapters"
            :highlight-entity-id="highlightedEntityId"
            :scroll-to-chapter-id="scrollToChapterId"
            :scroll-to-position="workspaceStore.scrollToPosition"
            :alert-highlight-ranges="workspaceStore.alertHighlightRanges"
            @chapter-visible="onChapterVisible"
            @entity-click="onEntityClick"
            @alert-click="onAlertClickFromText"
          />

          <!-- Tab Entidades -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'entities'"
            :project-id="project.id"
            required-phase="entities"
            tab="entities"
            :description="TAB_PHASE_DESCRIPTIONS.entities"
            @analysis-completed="onAnalysisCompleted"
          >
            <EntitiesTab
              ref="entitiesTabRef"
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
            tab="relationships"
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
          <template v-else-if="workspaceStore.activeTab === 'alerts'">
            <ComparisonBanner
              :project-id="project.id"
              :analysis-completed="project.analysisStatus === 'completed'"
            />
            <AlertsTab
              ref="alertsTabRef"
              :alerts="alerts"
              :chapters="chapters"
              :loading="loading"
              :analysis-executed="project.analysisStatus === 'completed'"
              @alert-select="onAlertSelect"
              @alert-navigate="onAlertNavigate"
              @alert-resolve="onAlertResolve"
              @alert-dismiss="onAlertDismiss"
              @refresh="loadAlerts(project.id)"
              @open-correction-config="correctionConfigModalRef?.show()"
            />
          </template>

          <!-- Tab Timeline -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'timeline'"
            :project-id="project.id"
            required-phase="structure"
            tab="timeline"
            :description="TAB_PHASE_DESCRIPTIONS.timeline"
            @analysis-completed="onAnalysisCompleted"
          >
            <TimelineView
              :project-id="project.id"
              :entities="entities"
              :chapters="chapters"
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
            ref="glossaryTabRef"
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
                  v-if="selectionStore.hasSelection"
                  v-tooltip="'Cerrar'"
                  icon="pi pi-times"
                  text
                  rounded
                  size="small"
                  @click="selectionStore.clearAll()"
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
                  @navigate-to-position="(s, e, t) => onAlertNavigateToPosition(selectedAlert, s, e, t)"
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
        :has-analysis="project.analysisStatus === 'completed'"
        :analysis-error="project.analysisStatus === 'error'"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useWorkspaceStore, type WorkspaceTab } from '@/stores/workspace'
import { useSelectionStore } from '@/stores/selection'
import { useAnalysisStore, TAB_PHASE_DESCRIPTIONS } from '@/stores/analysis'
import { useMentionNavigation } from '@/composables/useMentionNavigation'
import { useProjectData } from '@/composables/useProjectData'
import { useAnalysisPolling } from '@/composables/useAnalysisPolling'
import Button from 'primevue/button'
import DsSkeleton from '@/components/ds/DsSkeleton.vue'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import ExportDialog from '@/components/ExportDialog.vue'
import StatusBar from '@/components/layout/StatusBar.vue'
import { WorkspaceTabs, TextTab, AlertsTab, EntitiesTab, RelationsTab, StyleTab, GlossaryTab, ResumenTab, PanelResizer } from '@/components/workspace'
import { AnalysisRequired } from '@/components/analysis'
import { TimelineView } from '@/components/timeline'
import { ChaptersPanel, AlertsPanel, CharactersPanel, AssistantPanel, HistoryPanel } from '@/components/sidebar'
import { ProjectSummary, EntityInspector, AlertInspector, ChapterInspector, TextSelectionInspector } from '@/components/inspector'
import ComparisonBanner from '@/components/alerts/ComparisonBanner.vue'
import DocumentTypeChip from '@/components/DocumentTypeChip.vue'
import CorrectionConfigModal from '@/components/workspace/CorrectionConfigModal.vue'
import type { SidebarTab } from '@/stores/workspace'
import type { Entity, Alert, AlertSource } from '@/types'
import { resetGlobalHighlight } from '@/composables/useHighlight'
import { api } from '@/services/apiClient'
import { useNotifications } from '@/composables/useNotifications'
import { useGlobalUndo } from '@/composables/useGlobalUndo'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const workspaceStore = useWorkspaceStore()
const selectionStore = useSelectionStore()
const analysisStore = useAnalysisStore()
const { requestPermission: requestNotificationPermission } = useNotifications()
const toast = useToast()

// Global undo (Ctrl+Z)
const { undoableCount } = useGlobalUndo(() => project.value?.id ?? null)

// ── Composables ────────────────────────────────────────────
const project = computed(() => projectsStore.currentProject)

const { entities, alerts, chapters, relationships, entitiesCount, alertsCount,
        loadEntities, loadAlerts, loadChapters, loadRelationships } = useProjectData()

const { isAnalyzing, hasBeenAnalyzed, cancellingAnalysis,
        startPolling: startAnalysisPolling, stopPolling: stopAnalysisPolling,
        cancelAnalysis: handleCancelAnalysis } = useAnalysisPolling({
  project,
  entities, alerts, chapters,
  loadEntities, loadAlerts, loadChapters,
})

// Navegación de menciones - usar projectId reactivo
const mentionNav = useMentionNavigation(() => project.value?.id ?? 0)

// ── Tab status + alert badges ─────────────────────────────
const unresolvedAlertCount = computed(() =>
  alerts.value.filter(a => a.status === 'active').length
)

const tabStatuses = computed(() => {
  const pid = project.value?.id
  if (!pid) return {}
  const tabs: WorkspaceTab[] = ['text', 'entities', 'relationships', 'alerts', 'timeline', 'style', 'glossary', 'summary']
  const result: Partial<Record<WorkspaceTab, ReturnType<typeof analysisStore.getTabStatus>>> = {}
  for (const tab of tabs) {
    result[tab] = analysisStore.getTabStatus(pid, tab)
  }
  return result
})

// ── Local UI state ─────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const showExportDialog = ref(false)
const showReanalyzeDialog = ref(false)
const correctionConfigModalRef = ref<InstanceType<typeof CorrectionConfigModal> | null>(null)
const reanalyzing = ref(false)
const exportingStyleGuide = ref(false)

// Refs to tab components (for Ctrl+F routing)
const textTabRef = ref<InstanceType<typeof TextTab> | null>(null)
const entitiesTabRef = ref<InstanceType<typeof EntitiesTab> | null>(null)
const alertsTabRef = ref<InstanceType<typeof AlertsTab> | null>(null)
const glossaryTabRef = ref<InstanceType<typeof GlossaryTab> | null>(null)

// Estado para sincronización
const activeChapterId = ref<number | null>(null)
const highlightedEntityId = ref<number | null>(null)
const scrollToChapterId = ref<number | null>(null)

// ID de entidad inicial (para navegación desde /characters/:id)
const initialEntityId = ref<number | null>(null)

// Estado del sidebar
const sidebarTab = ref<SidebarTab>('chapters')

// Helpers para sidebar tabs
const getSidebarTabIcon = (tab: SidebarTab): string => {
  const icons: Record<SidebarTab, string> = {
    chapters: 'pi pi-book',
    alerts: 'pi pi-exclamation-triangle',
    characters: 'pi pi-users',
    assistant: 'pi pi-comments',
    history: 'pi pi-history'
  }
  return icons[tab]
}

const getSidebarTabTitle = (tab: SidebarTab): string => {
  const titles: Record<SidebarTab, string> = {
    chapters: 'Capítulos',
    alerts: 'Alertas',
    characters: 'Personajes',
    assistant: 'Asistente',
    history: 'Historial'
  }
  return titles[tab]
}

// Observar selectedEntityForMentions para cargar y navegar a menciones
watch(() => workspaceStore.selectedEntityForMentions, async (entityId) => {
  if (entityId !== null && project.value) {
    await mentionNav.startNavigation(entityId)
    workspaceStore.selectedEntityForMentions = null
  }
})

// ── Computed (inspector + layout) ──────────────────────────

const originalDocumentName = computed(() => {
  if (!project.value?.documentPath) return null
  const filename = project.value.documentPath.split(/[/\\]/).pop() || project.value.documentPath
  const match = filename.match(/^[a-f0-9]{32}_(.+)$/)
  return match ? match[1] : filename
})

const selectedEntity = computed(() => {
  if (selectionStore.primary?.type !== 'entity') return null
  return entities.value.find(e => e.id === selectionStore.primary?.id) || null
})

const selectedAlert = computed(() => {
  if (selectionStore.primary?.type !== 'alert') return null
  return alerts.value.find(a => a.id === selectionStore.primary?.id) || null
})

const currentChapter = computed(() => {
  if (!activeChapterId.value) return null
  return chapters.value.find(c => c.id === activeChapterId.value) || null
})

const showChapterInspector = computed(() => {
  return workspaceStore.activeTab === 'text' &&
         currentChapter.value !== null &&
         !selectionStore.hasSelection
})

const inspectorTitle = computed(() => {
  if (selectedEntity.value) return 'Entidad'
  if (selectedAlert.value) return 'Alerta'
  if (selectionStore.textSelection) return 'Selección'
  if (showChapterInspector.value) return 'Capítulo'
  return 'Resumen'
})

const rightPanelWidth = computed(() => {
  const preferredWidth = workspaceStore.currentLayoutConfig.rightPanelWidth
  return preferredWidth ?? workspaceStore.rightPanel.width
})

// ── Event handlers ─────────────────────────────────────────

// Handle menu events for tab switching
const handleMenuTabEvent = (event: Event) => {
  const customEvent = event as CustomEvent<{ tab: string }>
  if (customEvent.detail?.tab) {
    workspaceStore.setActiveTab(customEvent.detail.tab as any)
  }
}

const handleMenuExport = () => { showExportDialog.value = true }
const handleMenuRunAnalysis = () => { showReanalyzeDialog.value = true }
const handleMenuToggleInspector = () => { workspaceStore.toggleRightPanel() }
const handleMenuToggleSidebar = () => { workspaceStore.toggleLeftPanel() }

// Ctrl+F — contextual find per active tab
const handleFind = () => {
  switch (workspaceStore.activeTab) {
    case 'text':
      textTabRef.value?.openFindBar()
      break
    case 'entities':
      entitiesTabRef.value?.focusSearch()
      break
    case 'alerts':
      alertsTabRef.value?.focusSearch()
      break
    case 'glossary':
      glossaryTabRef.value?.focusSearch()
      break
  }
}

// Keyboard shortcut handlers
const handleNextAlert = () => {
  const currentIdx = selectedAlert.value
    ? alerts.value.findIndex(a => a.id === selectedAlert.value!.id)
    : -1
  const next = alerts.value[currentIdx + 1] || alerts.value[0]
  if (next) selectionStore.selectAlert(next)
}
const handlePrevAlert = () => {
  const currentIdx = selectedAlert.value
    ? alerts.value.findIndex(a => a.id === selectedAlert.value!.id)
    : alerts.value.length
  const prev = alerts.value[currentIdx - 1] || alerts.value[alerts.value.length - 1]
  if (prev) selectionStore.selectAlert(prev)
}
const handleResolveAlert = () => {
  if (selectedAlert.value) onAlertResolve(selectedAlert.value)
}
const handleDismissAlert = () => {
  if (selectedAlert.value) onAlertDismiss(selectedAlert.value)
}
const handleEscape = () => { selectionStore.clearAll() }
const handleToggleHistory = () => {
  if (sidebarTab.value === 'history') {
    sidebarTab.value = 'chapters'
  } else {
    sidebarTab.value = 'history'
    if (!workspaceStore.leftPanel.expanded) workspaceStore.toggleLeftPanel()
  }
}
const handleSidebarSetTab = (event: Event) => {
  const tab = (event as CustomEvent).detail?.tab
  if (tab) {
    sidebarTab.value = tab
    if (!workspaceStore.leftPanel.expanded) workspaceStore.toggleLeftPanel()
  }
}
const handleUndoComplete = async () => {
  const pid = project.value?.id
  if (!pid) return
  await Promise.all([loadEntities(pid), loadAlerts(pid), loadRelationships(pid)])
}

// ── Lifecycle ──────────────────────────────────────────────

onMounted(async () => {
  const projectId = parseInt(route.params.id as string)

  if (isNaN(projectId)) {
    error.value = 'ID de proyecto inválido'
    loading.value = false
    return
  }

  // Listen for menu events (native Tauri menu + web MenuBar)
  window.addEventListener('menubar:view-tab', handleMenuTabEvent)
  window.addEventListener('menubar:export', handleMenuExport)
  window.addEventListener('menubar:run-analysis', handleMenuRunAnalysis)
  window.addEventListener('menubar:toggle-inspector', handleMenuToggleInspector)
  window.addEventListener('menubar:toggle-sidebar', handleMenuToggleSidebar)
  window.addEventListener('menubar:find', handleFind)

  // Keyboard shortcut events
  window.addEventListener('keyboard:next-alert', handleNextAlert)
  window.addEventListener('keyboard:prev-alert', handlePrevAlert)
  window.addEventListener('keyboard:resolve-alert', handleResolveAlert)
  window.addEventListener('keyboard:dismiss-alert', handleDismissAlert)
  window.addEventListener('keyboard:escape', handleEscape)
  window.addEventListener('menubar:toggle-history', handleToggleHistory)
  window.addEventListener('sidebar:set-tab', handleSidebarSetTab)
  window.addEventListener('history:undo-complete', handleUndoComplete)

  try {
    analysisStore.setActiveProjectId(projectId)
    workspaceStore.reset()

    const tabParam = route.query.tab as string
    if (tabParam && ['text', 'entities', 'relationships', 'alerts', 'timeline', 'style', 'glossary', 'summary'].includes(tabParam)) {
      workspaceStore.setActiveTab(tabParam as any)
    }

    const entityParam = route.query.entity as string
    if (entityParam) {
      initialEntityId.value = parseInt(entityParam)
    }

    await projectsStore.fetchProject(projectId)
    await analysisStore.loadExecutedPhases(projectId)
    await loadEntities(projectId)
    await loadAlerts(projectId)
    await loadChapters(projectId, project.value ?? undefined)
    await loadRelationships(projectId)

    // Check for alert query parameter (para navegación desde AlertsView)
    const alertParam = route.query.alert as string
    if (alertParam) {
      const alertId = parseInt(alertParam)
      const targetAlert = alerts.value.find(a => a.id === alertId)
      if (targetAlert && targetAlert.spanStart !== undefined) {
        const targetChapter = chapters.value.find(c => c.chapterNumber === targetAlert.chapter)
        const chapterId = targetChapter?.id ?? null
        workspaceStore.navigateToTextPosition(
          targetAlert.spanStart,
          targetAlert.excerpt || undefined,
          chapterId
        )
        selectionStore.selectAlert(targetAlert)
      }
    }

    const hasActiveAnalysis = await analysisStore.checkAnalysisStatus(projectId)
    if (hasActiveAnalysis) {
      startAnalysisPolling()
    }

    loading.value = false
  } catch (_err) {
    error.value = projectsStore.error || 'Error cargando proyecto'
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('menubar:view-tab', handleMenuTabEvent)
  window.removeEventListener('menubar:export', handleMenuExport)
  window.removeEventListener('menubar:run-analysis', handleMenuRunAnalysis)
  window.removeEventListener('menubar:toggle-inspector', handleMenuToggleInspector)
  window.removeEventListener('menubar:toggle-sidebar', handleMenuToggleSidebar)
  window.removeEventListener('menubar:find', handleFind)
  window.removeEventListener('keyboard:next-alert', handleNextAlert)
  window.removeEventListener('keyboard:prev-alert', handlePrevAlert)
  window.removeEventListener('keyboard:resolve-alert', handleResolveAlert)
  window.removeEventListener('keyboard:dismiss-alert', handleDismissAlert)
  window.removeEventListener('keyboard:escape', handleEscape)
  window.removeEventListener('menubar:toggle-history', handleToggleHistory)
  window.removeEventListener('sidebar:set-tab', handleSidebarSetTab)
  window.removeEventListener('history:undo-complete', handleUndoComplete)
  stopAnalysisPolling()
  resetGlobalHighlight()
})

// ── Navigation & handlers ──────────────────────────────────

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
 * Si hay múltiples sources (inconsistencias), resalta todas las ubicaciones.
 * Si se proporciona un source específico, navega solo a esa ubicación.
 */
const onAlertNavigate = (alert: Alert, source?: AlertSource) => {
  // Convertir chapter NUMBER a chapter ID si es necesario
  const getChapterId = (chapterNumber: number | undefined | null): number | null => {
    if (chapterNumber === undefined || chapterNumber === null) return null
    const chapter = chapters.value.find(c => c.chapterNumber === chapterNumber)
    return chapter?.id ?? null
  }

  // Si hay múltiples sources y no se especifica uno concreto, resaltar todos
  const sources = alert.extraData?.sources
  if (sources && sources.length > 1 && !source) {
    // Colores para distinguir los sources (valor1 vs valor2)
    const colors = ['#ef4444', '#3b82f6'] // rojo y azul

    const ranges = sources.map((s: AlertSource, idx: number) => ({
      startChar: s.startChar,
      endChar: s.endChar,
      text: s.excerpt,
      chapterId: getChapterId(s.chapter),
      color: colors[idx % colors.length],
      label: s.value
    }))

    workspaceStore.highlightAlertSources(alert.id, ranges)
    return
  }

  // Si hay un source específico, usar sus datos de ubicación
  const targetChapter = source?.chapter ?? alert.chapter
  const targetPosition = source?.startChar ?? alert.spanStart
  const targetExcerpt = source?.excerpt ?? alert.excerpt

  // Navegar al texto con posición precisa si está disponible
  if (targetPosition !== undefined) {
    // Obtener el ID del capítulo a partir del número
    const chapterId = getChapterId(targetChapter)

    // Limpiar highlights anteriores y usar navegación simple
    workspaceStore.clearAlertHighlights()
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

/**
 * Navega a una ocurrencia específica de una alerta (repeticiones, ecos).
 */
const onAlertNavigateToPosition = (alert: Alert | null, startChar: number, endChar: number, text?: string) => {
  if (!alert) return

  const getChapterId = (chapterNumber: number | undefined | null): number | null => {
    if (chapterNumber === undefined || chapterNumber === null) return null
    const chapter = chapters.value.find(c => c.chapterNumber === chapterNumber)
    return chapter?.id ?? null
  }

  const chapterId = getChapterId(alert.chapter)
  workspaceStore.clearAlertHighlights()
  workspaceStore.navigateToTextPosition(startChar, text, chapterId)
}

const onAlertResolve = async (alert: Alert) => {
  try {
    const projectId = project.value!.id
    await api.postRaw(`/api/projects/${projectId}/alerts/${alert.id}/resolve`)
    await loadAlerts(projectId)
    selectionStore.clearAll()
    toast.add({ severity: 'success', summary: 'Resuelta', detail: alert.title || `Alerta #${alert.id} resuelta`, life: 3000 })
  } catch (err) {
    console.error('Error resolving alert:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo resolver la alerta', life: 3000 })
  }
}

const onAlertDismiss = async (alert: Alert) => {
  try {
    const projectId = project.value!.id
    await api.postRaw(`/api/projects/${projectId}/alerts/${alert.id}/dismiss`)
    await loadAlerts(projectId)
    selectionStore.clearAll()
    toast.add({ severity: 'info', summary: 'Descartada', detail: alert.title || `Alerta #${alert.id} descartada`, life: 3000 })
  } catch (err) {
    console.error('Error dismissing alert:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo descartar la alerta', life: 3000 })
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
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${project.value.id}/style-guide?format=markdown`)

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
      throw new Error(data.error || 'No se pudo completar la operación. Si persiste, reinicia la aplicación.')
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

// Reload stale data when switching to tabs that depend on analysis
watch(() => workspaceStore.activeTab, async (newTab) => {
  if (!project.value) return
  if (newTab === 'relationships' && (!relationships.value || relationships.value.length === 0)) {
    await loadEntities(project.value.id)
    await loadRelationships(project.value.id)
  }
})

const onDocumentTypeChanged = async (_type: string, _subtype: string | null) => {
  // Recargar el proyecto para obtener el nuevo perfil de features
  if (project.value) {
    await projectsStore.fetchProject(project.value.id)
  }
}

const startReanalysis = async () => {
  if (!project.value) return
  reanalyzing.value = true
  showReanalyzeDialog.value = false

  // Request notification permission on first analysis (non-blocking)
  requestNotificationPermission()

  // Resetear contadores inmediatamente para mostrar 0 durante el análisis
  entities.value = []
  alerts.value = []

  // Activar el estado de análisis en el store para que StatusBar lo muestre
  analysisStore.setAnalyzing(project.value.id, true)

  try {
    const data = await api.postRaw<{ success: boolean; error?: string }>(`/api/projects/${project.value.id}/reanalyze`)

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
  } catch (_err) {
    error.value = 'No se pudo re-analizar el documento. Si persiste, reinicia la aplicación.'
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

/* Back button */
.back-btn :deep(.p-button-label) {
  font-weight: 500;
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

.header-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
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
  overflow: hidden;
  min-width: 0;
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
  overflow: hidden;
  min-width: 0;
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
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.inspector-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  font-weight: 600;
  font-size: 0.875rem;
}

.inspector-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
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
