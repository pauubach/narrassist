<template>
  <div class="project-detail-view">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-content">
        <i class="pi pi-spin pi-spinner loading-icon"></i>
        <h2>Cargando proyecto...</h2>
        <p class="loading-hint">
          Esto puede tardar unos segundos para proyectos grandes
        </p>
        <DsSkeleton variant="list" :rows="3" />
      </div>
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
          <input
            ref="replaceDocumentInputRef"
            type="file"
            accept=".doc,.docx,.txt,.md,.pdf,.epub"
            style="display: none"
            @change="onReplaceDocumentSelected"
          >
          <Button
            v-tooltip.bottom="'Exportar Guía de Estilo'"
            icon="pi pi-book"
            outlined
            :loading="exportingStyleGuide"
            class="style-guide-btn"
            aria-label="Exportar Guía de Estilo"
            @click="quickExportStyleGuide"
          />
          <Button data-testid="open-export-dialog" label="Exportar" icon="pi pi-download" outlined @click="openExportDialog" />
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
        @saved="loadAlerts(project.id, true)"
      />

      <!-- Analyze/Reanalyze Confirmation Dialog -->
      <Dialog
        :visible="showReanalyzeDialog"
        :header="hasBeenAnalyzed ? 'Re-analizar documento' : 'Analizar documento'"
        :modal="true"
        :style="{ width: 'var(--ds-size-dialog-md)' }"
        @update:visible="showReanalyzeDialog = $event"
      >
        <p class="reanalyze-info">
          <i class="pi pi-info-circle"></i>
          {{ hasBeenAnalyzed ? 'Se volverá a analizar el documento original.' : 'Se analizará el documento para detectar inconsistencias.' }}
        </p>
        <div class="analysis-mode-selector">
          <label class="analysis-mode-label">Modo de análisis</label>
          <select v-model="selectedAnalysisMode" class="analysis-mode-select">
            <option v-for="opt in analysisModeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }} — {{ opt.description }}
            </option>
          </select>
        </div>
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

                <!-- Panel Alertas (muestra alertas filtradas por el dashboard cuando está activo) -->
                <AlertsPanel
                  v-show="sidebarTab === 'alerts'"
                  :alerts="workspaceStore.activeTab === 'alerts' && dashboardFilteredAlerts !== null ? dashboardFilteredAlerts : alerts"
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
                  :selection-chapter-number="currentChapter?.chapterNumber ?? null"
                  @navigate-to-reference="onChatReferenceNavigate"
                />

                <!-- Panel Búsqueda Semántica -->
                <SemanticSearchPanel
                  v-show="sidebarTab === 'search'"
                  :project-id="project.id"
                  :chapters="chapters"
                  :initial-query="searchQuery"
                  @navigate-to-position="onSearchResultNavigate"
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
          <!-- ME-01: Stale data banner -->
          <div v-if="isActiveTabDataStale" class="stale-data-banner">
            <i class="pi pi-info-circle"></i>
            <span>Los datos mostrados podrían no reflejar el último análisis.</span>
          </div>

          <!-- Tab Texto -->
          <TextTab
            v-if="workspaceStore.activeTab === 'text'"
            ref="textTabRef"
            :project-id="project.id"
            :document-title="project.name"
            :alerts="activeAlerts"
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
              :loading="loadingEntities"
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
              :loading="loadingRelations"
              @entity-select="onEntitySelect"
              @refresh="loadRelationships(project.id)"
            />
          </AnalysisRequired>

          <!-- Tab Alertas (Dashboard en centro, lista en sidebar, detalle en panel dcho) -->
          <template v-else-if="workspaceStore.activeTab === 'alerts'">
            <ComparisonBanner
              :project-id="project.id"
              :analysis-completed="project.analysisStatus === 'completed'"
            />
            <AlertsDashboard
              ref="alertsDashboardRef"
              :alerts="alerts"
              :chapters="chapters"
              :entities="entities"
              :loading="loadingAlerts"
              :analysis-executed="project.analysisStatus === 'completed'"
              @alert-select="onAlertSelect"
              @alert-navigate="onAlertNavigate"
              @alert-resolve="onAlertResolve"
              @alert-dismiss="onAlertDismiss"
              @refresh="loadAlerts(project.id)"
              @resolve-all="onResolveAll"
              @batch-resolve-ambiguous="onBatchResolveAmbiguous"
              @open-correction-config="correctionConfigModalRef?.show()"
              @filter-change="onDashboardFilterChange"
            />
          </template>

          <!-- Tab Timeline -->
          <AnalysisRequired
            v-else-if="workspaceStore.activeTab === 'timeline'"
            :project-id="project.id"
            required-phase="timeline"
            tab="timeline"
            :description="TAB_PHASE_DESCRIPTIONS.timeline"
            @analysis-completed="onAnalysisCompleted"
          >
            <!-- HI-17: degraded timeline warning -->
            <div v-if="analysisStore.isTabDegraded(project.id, 'timeline')" class="degraded-banner">
              <i class="pi pi-exclamation-triangle"></i>
              <span class="degraded-banner__text">
                La línea temporal se generó con datos parciales. Puedes relanzar solo esta parte para completar los resultados.
              </span>
              <Button
                label="Reintentar cronología"
                icon="pi pi-refresh"
                size="small"
                severity="warning"
                text
                class="degraded-banner__action"
                :disabled="isAnalyzing || retryingTimeline"
                :loading="retryingTimeline"
                @click="retryTimelinePhase"
              />
            </div>
            <TimelineView
              :project-id="project.id"
              :entities="entities"
              :chapters="chapters"
              @navigate-to-chapter="onNavigateToChapter"
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
            ref="glossaryTabRef"
            :project-id="project.id"
          />

          <!-- Tab Resumen -->
          <ResumenTab
            v-else-if="workspaceStore.activeTab === 'summary'"
            :project="project"
            :entities="entities"
            :alerts="alerts"
            :chapters="chapters"
            @export="openExportDialog()"
            @export-style-guide="handleExportStyleGuide"
            @export-corrected="handleExportCorrected"
            @re-analyze="showReanalyzeDialog = true"
            @navigate-to-character="handleNavigateToCharacter"
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
              <div v-if="showInspectorHeader" class="inspector-header">
                <span v-if="inspectorHeaderTitle" class="inspector-title">{{ inspectorHeaderTitle }}</span>
                <Button
                  v-if="(selectionStore.hasSelection || selectionStore.textSelection) && isContextualInspector && !selectedEntity"
                  v-tooltip="'Cerrar'"
                  icon="pi pi-times"
                  text
                  rounded
                  size="small"
                  @click="selectionStore.clearAll()"
                />
              </div>

              <div
                v-if="workspaceStore.activeTab === 'text'"
                class="inspector-tabs"
                :class="{ 'with-contextual': hasContextualContent }"
              >
                <Button
                  size="small"
                  :text="rightInspectorTab !== 'summary'"
                  :outlined="rightInspectorTab === 'summary'"
                  @click="switchRightInspectorTab('summary')"
                >
                  Resumen
                </Button>
                <Button
                  size="small"
                  :text="rightInspectorTab !== 'chapters'"
                  :outlined="rightInspectorTab === 'chapters'"
                  @click="switchRightInspectorTab('chapters')"
                >
                  Capítulo
                </Button>
                <Button
                  size="small"
                  :text="rightInspectorTab !== 'dialogue'"
                  :outlined="rightInspectorTab === 'dialogue'"
                  @click="switchRightInspectorTab('dialogue')"
                >
                  Diálogos
                </Button>
                <Button
                  v-if="hasContextualContent"
                  size="small"
                  :text="rightInspectorTab !== 'contextual'"
                  :outlined="rightInspectorTab === 'contextual'"
                  @click="switchRightInspectorTab('contextual')"
                >
                  {{ contextualTabLabel }}
                </Button>
              </div>

              <div
                class="inspector-content"
                :class="{
                  'inspector-content--dialogue': workspaceStore.activeTab === 'text' && rightInspectorTab === 'dialogue'
                }"
              >
                <template v-if="workspaceStore.activeTab === 'text' && rightInspectorTab === 'summary'">
                  <ProjectSummary
                    :alerts="alerts"
                    :global-summary="globalSummary"
                    @navigate-to-alert="onAlertClick"
                    @view-alerts="handleViewAlerts"
                    @filter-alerts="handleFilterAlerts"
                    @alert-action="handleAlertAction"
                  />
                </template>

                <template v-else-if="workspaceStore.activeTab === 'text' && rightInspectorTab === 'chapters'">
                  <ChapterInspector
                    v-if="currentChapter"
                    :chapter="currentChapter"
                    :project-id="project.id"
                    :entities="entities"
                    :alerts="alerts"
                    :summaries="chapterSummaries"
                    @back-to-document="onBackToDocumentSummary"
                    @go-to-start="onGoToChapterStart"
                    @view-alerts="onViewChapterAlerts"
                    @select-entity="onEntityClick"
                    @navigate-to-event="onNavigateToEvent"
                    @navigate-to-chapter="onNavigateToChapter"
                  />
                  <ProjectSummary
                    v-else
                    :word-count="project.wordCount"
                    :chapter-count="project.chapterCount"
                    :entity-count="entitiesCount"
                    :alert-count="alertsCount"
                    :alerts="alerts"
                    :global-summary="globalSummary"
                    @stat-click="handleStatClick"
                  />
                </template>

                <template v-else-if="workspaceStore.activeTab === 'text' && rightInspectorTab === 'dialogue'">
                  <DialogueAttributionPanel
                    :project-id="project.id"
                    :chapters="dialogueChapters"
                    :entities="entities"
                    :initial-chapter="currentChapter?.chapterNumber"
                    @select-dialogue="onInspectorDialogueSelected"
                  />
                </template>

                <template v-else>
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

                  <AlertInspector
                    v-else-if="selectedAlert"
                    :alert="selectedAlert"
                    :chapters="chapters"
                    @navigate="selectedAlert && onAlertNavigate(selectedAlert, $event)"
                    @navigate-to-position="(s, e, t) => selectedAlert && onAlertNavigateToPosition(selectedAlert, s, e, t)"
                    @resolve="selectedAlert && onAlertResolve(selectedAlert)"
                    @dismiss="selectedAlert && onAlertDismiss(selectedAlert)"
                    @resolve-ambiguous-attribute="(entityId) => selectedAlert && onResolveAmbiguousAttribute(selectedAlert, entityId)"
                    @close="selectionStore.clearAll()"
                  />

                  <TextSelectionInspector
                    v-else-if="selectionStore.textSelection"
                    :selection="selectionStore.textSelection"
                    :entities="entities"
                    @close="selectionStore.setTextSelection(null)"
                    @select-entity="onEntityClick"
                    @search-similar="onSearchSimilarText"
                    @ask-ai="onAskAiAboutSelection"
                  />

                  <ChapterInspector
                    v-else-if="showChapterInspector && currentChapter"
                    :chapter="currentChapter"
                    :project-id="project.id"
                    :entities="entities"
                    :alerts="alerts"
                    :summaries="chapterSummaries"
                    @back-to-document="onBackToDocumentSummary"
                    @go-to-start="onGoToChapterStart"
                    @view-alerts="onViewChapterAlerts"
                    @select-entity="onEntityClick"
                    @navigate-to-event="onNavigateToEvent"
                    @navigate-to-chapter="onNavigateToChapter"
                  />

                  <ProjectSummary
                    v-else
                    :word-count="project.wordCount"
                    :chapter-count="project.chapterCount"
                    :entity-count="entitiesCount"
                    :alert-count="alertsCount"
                    :alerts="alerts"
                    :global-summary="globalSummary"
                    @stat-click="handleStatClick"
                  />
                </template>
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
        :total-alert-count="alerts.length"
        :resolved-count="alerts.filter(a => a.status === 'resolved').length"
        :dismissed-count="alerts.filter(a => a.status === 'dismissed').length"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, defineAsyncComponent } from 'vue'
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
import { WorkspaceTabs, TextTab, PanelResizer } from '@/components/workspace'
import { AnalysisRequired } from '@/components/analysis'
import DialogueAttributionPanel from '@/components/DialogueAttributionPanel.vue'
import { ChaptersPanel, AlertsPanel, CharactersPanel } from '@/components/sidebar'
import { ProjectSummary, EntityInspector } from '@/components/inspector'

// Idle-prefetch: tabs y paneles que no se ven al inicio se cargan en background
// tras el primer render. defineAsyncComponent es transparente para el template.
const AlertsDashboard = defineAsyncComponent(() => import('@/components/workspace/AlertsDashboard.vue'))
const EntitiesTab = defineAsyncComponent(() => import('@/components/workspace/EntitiesTab.vue'))
const RelationsTab = defineAsyncComponent(() => import('@/components/workspace/RelationsTab.vue'))
const StyleTab = defineAsyncComponent(() => import('@/components/workspace/StyleTab.vue'))
const GlossaryTab = defineAsyncComponent(() => import('@/components/workspace/GlossaryTab.vue'))
const ResumenTab = defineAsyncComponent(() => import('@/components/workspace/ResumenTab.vue'))
const TimelineView = defineAsyncComponent(() => import('@/components/timeline/TimelineView.vue'))
const AlertInspector = defineAsyncComponent(() => import('@/components/inspector/AlertInspector.vue'))
const ChapterInspector = defineAsyncComponent(() => import('@/components/inspector/ChapterInspector.vue'))
const TextSelectionInspector = defineAsyncComponent(() => import('@/components/inspector/TextSelectionInspector.vue'))
const AssistantPanel = defineAsyncComponent(() => import('@/components/sidebar/AssistantPanel.vue'))
const HistoryPanel = defineAsyncComponent(() => import('@/components/sidebar/HistoryPanel.vue'))
const SemanticSearchPanel = defineAsyncComponent(() => import('@/components/sidebar/SemanticSearchPanel.vue'))
import ComparisonBanner from '@/components/alerts/ComparisonBanner.vue'
import DocumentTypeChip from '@/components/DocumentTypeChip.vue'
import CorrectionConfigModal from '@/components/workspace/CorrectionConfigModal.vue'
import type { SidebarTab } from '@/stores/workspace'
import type { Entity, Alert, AlertSource, ChatReference, DialogueAttribution } from '@/types'
import { resetGlobalHighlight } from '@/composables/useHighlight'
import { useNotifications } from '@/composables/useNotifications'
import { useGlobalUndo } from '@/composables/useGlobalUndo'
import { updateProjectStats } from '@/composables/useGlobalStats'
import { waitForPendingAnalysisSettingsSync } from '@/composables/useSettingsPersistence'
import { useProjectDetailAnalysis } from '@/views/project-detail/useProjectDetailAnalysis'
import { useProjectDetailExports } from '@/views/project-detail/useProjectDetailExports'
import { useProjectDetailAlerts } from '@/views/project-detail/useProjectDetailAlerts'
import { useProjectDetailLifecycle } from '@/views/project-detail/useProjectDetailLifecycle'
import { useProjectDetailNavigation } from '@/views/project-detail/useProjectDetailNavigation'
import { initializeProjectDetail, parsePositiveInt } from '@/views/project-detail/projectDetailBootstrap'
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

const { entities, alerts, chapters, relationships, chapterSummaries, globalSummary, entitiesCount, alertsCount,
        loadingEntities, loadingAlerts, loadingRelationships,
        loadEntities, loadAlerts, loadChapters, loadRelationships, loadChapterSummaries } = useProjectData()

// Wrapper para loadChapters que coincide con la firma esperada por useAnalysisPolling
const loadChaptersWrapper = async (projectId: number, forceReload = false) => {
  await loadChapters(projectId, project.value ?? undefined, forceReload)
}

const { isAnalyzing, hasBeenAnalyzed, cancellingAnalysis,
        startPolling: startAnalysisPolling, stopPolling: stopAnalysisPolling,
        cancelAnalysis: handleCancelAnalysis } = useAnalysisPolling({
  project,
  entities, alerts, chapters,
  loadEntities, loadAlerts, loadChapters: loadChaptersWrapper,
})

// ME-01: Stale data signal for the active tab
const isActiveTabDataStale = computed(() => {
  if (!project.value) return false
  const tab = workspaceStore.activeTab
  if (tab === 'text') return false // Text tab always shows live document
  return analysisStore.isTabDataStale(project.value.id, tab)
})

// Navegación de menciones - usar projectId reactivo
const mentionNav = useMentionNavigation(() => project.value?.id ?? 0)

// ── Tab status + alert badges ─────────────────────────────
const unresolvedAlertCount = computed(() =>
  alerts.value.filter(a => a.status === 'active').length
)

// Batch tab statuses (performance optimization #9)
const tabStatuses = computed(() => {
  const pid = project.value?.id
  if (!pid) return {}
  const tabs: WorkspaceTab[] = ['text', 'entities', 'relationships', 'alerts', 'timeline', 'style', 'glossary', 'summary']
  return analysisStore.getBatchTabStatuses(pid, tabs)
})

// Loading combinado para RelationsTab (necesita entities + relationships)
const loadingRelations = computed(() => loadingEntities.value || loadingRelationships.value)

// ── Local UI state ─────────────────────────────────────────
const loading = ref(true) // Loading inicial del proyecto
const error = ref('')
const {
  showExportDialog,
  exportingStyleGuide,
  openExportDialog,
  handleExportCorrected,
  quickExportStyleGuide,
} = useProjectDetailExports({
  project,
  setError: (message: string) => {
    error.value = message
  },
  addToast: toast.add,
})
const {
  onAlertResolve,
  onAlertDismiss,
  onResolveAmbiguousAttribute,
  onResolveAll,
  onBatchResolveAmbiguous,
  handleAlertAction,
} = useProjectDetailAlerts({
  projectId: computed(() => project.value?.id ?? null),
  loadAlerts,
  clearSelection: () => {
    selectionStore.clearAll()
  },
  addToast: toast.add,
})
const replaceDocumentInputRef = ref<HTMLInputElement | null>(null)
const showReanalyzeDialog = ref(false)
const correctionConfigModalRef = ref<InstanceType<typeof CorrectionConfigModal> | null>(null)
const selectedAnalysisMode = ref('auto')
const analysisModeOptions = [
  { label: 'Auto', value: 'auto', description: 'Ajusta según tamaño del documento' },
  { label: 'Express', value: 'express', description: 'Solo gramática y ortografía' },
  { label: 'Ligero', value: 'light', description: 'Personajes + gramática (sin análisis profundo)' },
  { label: 'Estándar', value: 'standard', description: 'Análisis completo' },
  { label: 'Profundo', value: 'deep', description: 'Todo incluido (requiere más recursos)' },
]

// Estados de carga individuales vienen de useProjectData()
// loadingEntities, loadingAlerts, loadingRelationships

// Refs to tab components (for Ctrl+F routing)
const textTabRef = ref<InstanceType<typeof TextTab> | null>(null)
const entitiesTabRef = ref<InstanceType<typeof EntitiesTab> | null>(null)
const alertsDashboardRef = ref<InstanceType<typeof AlertsDashboard> | null>(null)
const glossaryTabRef = ref<InstanceType<typeof GlossaryTab> | null>(null)

// Alertas filtradas por el dashboard (se pasan al sidebar)
// null = no hay filtro activo; [] = filtro activo sin resultados
const dashboardFilteredAlerts = ref<Alert[] | null>(null)

function onDashboardFilterChange(filtered: Alert[]) {
  dashboardFilteredAlerts.value = filtered
}

type RightInspectorTab = 'summary' | 'chapters' | 'dialogue' | 'contextual'
const rightInspectorTab = ref<RightInspectorTab>('summary')

// Estado para sincronización
const activeChapterId = ref<number | null>(null)
const highlightedEntityId = ref<number | null>(null)
const scrollToChapterId = ref<number | null>(null)

// ID de entidad inicial (para navegación desde /characters/:id)
const initialEntityId = ref<number | null>(null)

// Estado del sidebar
const sidebarTab = ref<SidebarTab>('chapters')
const searchQuery = ref<string>('')

// Helpers para sidebar tabs
const getSidebarTabIcon = (tab: SidebarTab): string => {
  const icons: Record<SidebarTab, string> = {
    chapters: 'pi pi-book',
    alerts: 'pi pi-exclamation-triangle',
    characters: 'pi pi-users',
    search: 'pi pi-search',
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
    search: 'Búsqueda',
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

watch(
  [
    () => selectionStore.primary?.type ?? null,
    () => selectionStore.textSelection,
    () => workspaceStore.activeTab,
  ],
  ([primaryType, textSelection, activeTab]) => {
    if (activeTab !== 'text') return
    const hasContextual = Boolean(primaryType || textSelection)
    if (hasContextual) {
      rightInspectorTab.value = 'contextual'
    } else if (rightInspectorTab.value === 'contextual') {
      rightInspectorTab.value = 'summary'
    }
  }
)

// ── Computed (inspector + layout) ──────────────────────────

const originalDocumentName = computed(() => {
  if (!project.value?.documentPath) return null
  const filename = project.value.documentPath.split(/[/\\]/).pop() || project.value.documentPath
  const match = filename.match(/^[a-f0-9]{32}_(.+)$/)
  return match ? match[1] : filename
})

// Map index para lookups O(1) (performance optimization)
const entitiesById = computed(() =>
  new Map(entities.value.map(e => [e.id, e]))
)

const alertsById = computed(() =>
  new Map(alerts.value.map(a => [a.id, a]))
)

// Alertas activas para mostrar en el documento (sin resueltas/descartadas)
const activeAlerts = computed(() =>
  alerts.value.filter(a => a.status === 'active')
)

const chaptersById = computed(() =>
  new Map(chapters.value.map(c => [c.id, c]))
)

const ensureInspectorChapterSelection = () => {
  if (chapters.value.length === 0) return

  const hasValidActiveChapter =
    activeChapterId.value !== null && chaptersById.value.has(activeChapterId.value)

  if (hasValidActiveChapter) return

  const firstChapter = chapters.value[0]
  if (!firstChapter) return

  activeChapterId.value = firstChapter.id
  workspaceStore.setCurrentChapter(firstChapter.id)
}

const switchRightInspectorTab = (tab: RightInspectorTab) => {
  rightInspectorTab.value = tab
  if (tab === 'chapters' && workspaceStore.activeTab === 'text') {
    ensureInspectorChapterSelection()
  }
}

const selectedEntity = computed(() => {
  if (selectionStore.primary?.type !== 'entity') return null
  return entitiesById.value.get(selectionStore.primary.id) || null
})

const selectedAlert = computed(() => {
  if (selectionStore.primary?.type !== 'alert') return null
  return alertsById.value.get(selectionStore.primary.id) || null
})

const currentChapter = computed(() => {
  if (!activeChapterId.value) return null
  return chaptersById.value.get(activeChapterId.value) || null
})

const {
  goBack,
  onChapterSelect,
  onSectionSelect,
  onChapterVisible,
  onEntityClick,
  onEntitySelect,
  onEntityEdit,
  onAlertSelect,
  onAlertClickFromText,
  onAlertNavigate,
  onAlertNavigateToPosition,
  navigateToAlerts,
  handleFilterSeverity,
  handleStatClick,
  handleViewAlerts,
  handleFilterAlerts,
  onAlertClick,
  handleGoToMentions,
  onBackToDocumentSummary,
  onGoToChapterStart,
  onViewChapterAlerts,
  onNavigateToChapter,
  onNavigateToEvent,
  onInspectorDialogueSelected,
  onSearchSimilarText,
  onSearchResultNavigate,
  onAskAiAboutSelection,
  onChatReferenceNavigate,
  handleNavigateToCharacter,
} = useProjectDetailNavigation({
  router,
  chapters,
  entities,
  rightInspectorTab,
  activeChapterId,
  highlightedEntityId,
  scrollToChapterId,
  initialEntityId,
  sidebarTab,
  searchQuery,
  currentChapter,
  workspaceStore,
  selectionStore,
  scrollToDialogue: (attribution) => {
    textTabRef.value?.scrollToDialogue(attribution)
  },
})

watch(
  [() => rightInspectorTab.value, () => workspaceStore.activeTab, () => chapters.value.length],
  ([inspectorTab, activeTab]) => {
    if (activeTab !== 'text' || inspectorTab !== 'chapters') return
    ensureInspectorChapterSelection()
  },
  { immediate: true }
)

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

const entityTypeLabels: Record<Entity['type'], string> = {
  character: 'Personaje',
  location: 'Lugar',
  object: 'Objeto',
  organization: 'Organización',
  event: 'Evento',
  concept: 'Concepto',
  other: 'Entidad',
}

const dialogueChapters = computed(() =>
  chapters.value.map(ch => ({
    id: ch.id,
    number: ch.chapterNumber,
    title: ch.title,
  }))
)

const hasContextualContent = computed(() => {
  if (workspaceStore.activeTab !== 'text') return false
  return selectionStore.hasSelection || Boolean(selectionStore.textSelection)
})

const isContextualInspector = computed(() => {
  if (workspaceStore.activeTab !== 'text') return true
  return rightInspectorTab.value === 'contextual'
})

const contextualTabLabel = computed(() => {
  if (selectedEntity.value) {
    return entityTypeLabels[selectedEntity.value.type] || 'Entidad'
  }
  if (selectedAlert.value) return 'Alerta'
  if (selectionStore.textSelection) return 'Selección'
  return 'Contextual'
})

const inspectorHeaderTitle = computed(() => {
  if (workspaceStore.activeTab !== 'text') {
    return inspectorTitle.value
  }
  if (rightInspectorTab.value === 'contextual') {
    return ''
  }
  return ''
})

const showInspectorHeader = computed(() => {
  if (workspaceStore.activeTab !== 'text') return true
  return isContextualInspector.value && hasContextualContent.value
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

const handleMenuExport = () => { openExportDialog() }
const handleMenuUpdateManuscript = () => { openUpdateDocumentDialog() }
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
      alertsDashboardRef.value?.focusSearch()
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
  if (parsePositiveInt(route.params.id as string | undefined) === null) {
    error.value = 'ID de proyecto invalido'
    loading.value = false
    return
  }

  // Listen for menu events (native Tauri menu + web MenuBar)
  window.addEventListener('menubar:view-tab', handleMenuTabEvent)
  window.addEventListener('menubar:export', handleMenuExport)
  window.addEventListener('menubar:update-manuscript', handleMenuUpdateManuscript)
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

  await initializeProjectDetail({
    projectIdParam: route.params.id as string | undefined,
    query: {
      tab: route.query.tab as string | undefined,
      entity: route.query.entity as string | undefined,
      alert: route.query.alert as string | undefined,
      scrollPos: route.query.scrollPos as string | undefined,
      scrollChapter: route.query.scrollChapter as string | undefined,
    },
    getProject: () => project.value,
    getAlerts: () => alerts.value,
    getChapters: () => chapters.value,
    setError: (message) => {
      error.value = message
    },
    setLoading: (isLoading) => {
      loading.value = isLoading
    },
    setInitialEntityId: (entityId) => {
      initialEntityId.value = entityId
    },
    projectsStore,
    analysisStore,
    workspaceStore,
    selectionStore,
    loadChapters,
    loadEntities,
    loadAlerts,
    loadRelationships,
    loadChapterSummaries,
    startAnalysisPolling,
  })
})

onUnmounted(() => {
  window.removeEventListener('menubar:view-tab', handleMenuTabEvent)
  window.removeEventListener('menubar:export', handleMenuExport)
  window.removeEventListener('menubar:update-manuscript', handleMenuUpdateManuscript)
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

const handleExportStyleGuide = () => {
  openExportDialog()
}

const {
  reanalyzing,
  retryingTimeline,
  retryTimelinePhase,
  startReanalysis,
  openUpdateDocumentDialog,
  onReplaceDocumentSelected,
} = useProjectDetailAnalysis({
  project,
  showReanalyzeDialog,
  selectedAnalysisMode,
  entities,
  alerts,
  isAnalyzing,
  replaceDocumentInputRef,
  analysisStore,
  projectsStore,
  stopAnalysisPolling,
  loadEntities,
  loadAlerts,
  loadChapters,
  waitForPendingAnalysisSettingsSync,
  requestNotificationPermission,
  setError: (message) => {
    error.value = message
  },
  addToast: toast.add,
})

const { onAnalysisCompleted } = useProjectDetailLifecycle({
  project,
  workspaceStore,
  analysisStore,
  rightInspectorTab,
  sidebarTab,
  alerts,
  isAnalyzing,
  loadEntities,
  loadRelationships,
  loadAlerts,
  loadChapters,
  loadChapterSummaries,
  updateProjectStats,
})

const onDocumentTypeChanged = async (_type: string, _subtype: string | null) => {
  // Recargar el proyecto para obtener el nuevo perfil de features
  if (project.value) {
    await projectsStore.fetchProject(project.value.id)
  }
}

</script>

<style scoped>
/* HI-17: Degraded phase banner */
.degraded-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  margin-bottom: 0.75rem;
  background: var(--p-orange-50);
  color: var(--p-orange-700);
  border-radius: var(--app-radius);
  font-size: 0.85rem;
}

.degraded-banner i {
  color: var(--p-orange-500);
}

.degraded-banner__text {
  flex: 1;
}

.degraded-banner__action {
  flex-shrink: 0;
}

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
  gap: var(--ds-space-4);
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-3);
  max-width: 600px;
  text-align: center;
}

.loading-icon {
  font-size: 3rem;
  color: var(--primary-color);
  margin-bottom: var(--ds-space-2);
}

.loading-content h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-color);
}

.loading-hint {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-color-secondary);
  margin-bottom: var(--ds-space-3);
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
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--surface-card);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.header-left > :deep(.document-type-chip) {
  align-self: flex-end;
  margin-left: var(--ds-space-2);
}

.header-info h1 {
  font-size: var(--ds-font-lg);
  font-weight: 600;
  margin: 0;
  color: var(--text-color);
}

.header-meta {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-1);
}

.doc-name {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
}

.header-actions {
  display: flex;
  gap: var(--ds-space-2);
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
  gap: var(--ds-space-1);
  padding: var(--ds-space-2);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
  flex-shrink: 0;
}

.sidebar-tab-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--ds-space-10);
  height: var(--ds-space-10);
  border: none;
  background: transparent;
  border-radius: var(--app-radius);
  cursor: pointer;
  color: var(--text-color-secondary);
  transition: var(--ds-transition-fast);
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
  top: var(--ds-space-0-5);
  right: var(--ds-space-0-5);
  min-width: var(--ds-space-4);
  height: var(--ds-space-4);
  font-size: calc(var(--ds-font-xs) * 0.833);
  font-weight: 600;
  background: var(--ds-color-danger, #ef4444);
  color: white;
  border-radius: var(--app-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--ds-space-1);
}

.sidebar-badge--warning {
  background: var(--orange-500);
}

.sidebar-badge--history {
  background: var(--blue-500);
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
  padding: var(--ds-space-3) var(--ds-space-4);
  font-weight: 600;
  font-size: var(--ds-font-sm);
  color: var(--text-color);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
}

.mini-count {
  background: var(--surface-200);
  padding: var(--ds-space-0-5) var(--ds-space-2);
  border-radius: var(--app-radius-lg);
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
}

.severity-list {
  padding: var(--ds-space-2);
}

.severity-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: background var(--ds-duration-fast) var(--ds-ease-in-out);
}

.severity-row:hover {
  background: var(--surface-hover);
}

.severity-dot {
  width: var(--ds-space-2);
  height: var(--ds-space-2);
  border-radius: 50%;
}

.dot-critical { background: var(--ds-color-danger, #ef4444); }
.dot-high { background: var(--orange-500); }
.dot-medium { background: var(--yellow-500); }
.dot-low { background: var(--blue-500); }
.dot-info { background: var(--gray-400); }

.severity-label {
  flex: 1;
  font-size: var(--ds-font-xs);
}

.severity-count {
  font-weight: 600;
  font-size: var(--ds-font-xs);
}

.characters-list {
  padding: var(--ds-space-2);
}

.character-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: background var(--ds-duration-fast) var(--ds-ease-in-out);
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
  font-size: var(--ds-font-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.char-mentions {
  font-size: var(--ds-font-xs);
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
  border-right: var(--ds-border-1) solid var(--surface-border);
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

/* ME-01: Stale data banner */
.stale-data-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  background: var(--yellow-50);
  color: var(--yellow-900);
  font-size: 0.8rem;
  border-bottom: 1px solid var(--yellow-200);
}

.stale-data-banner .pi {
  font-size: 0.85rem;
  color: var(--yellow-600);
}

.right-panel {
  display: flex;
  flex-shrink: 0;
  background: var(--surface-card);
  border-left: var(--ds-border-1) solid var(--surface-border);
  position: relative;
  overflow: hidden;
  min-width: 0;
}

/* Animación de paneles */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all var(--ds-duration-normal) var(--ds-ease-in-out);
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(calc(-1 * var(--ds-space-5)));
}

.right-panel.panel-slide-enter-from,
.right-panel.panel-slide-leave-to {
  transform: translateX(var(--ds-space-5));
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
  padding: var(--ds-space-3) var(--ds-space-4);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
  font-weight: 600;
  font-size: var(--ds-font-sm);
}

.inspector-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--ds-space-1-5);
  padding: var(--ds-space-2);
  border-bottom: var(--ds-border-1) solid var(--surface-border);
}

.inspector-tabs.with-contextual {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.inspector-tabs :deep(.p-button) {
  width: 100%;
  white-space: nowrap;
  font-size: var(--ds-font-xs);
  min-width: 0;
  overflow: hidden;
}

.inspector-tabs :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
}

.inspector-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--ds-space-4);
  scrollbar-gutter: stable;
}

.inspector-content.inspector-content--dialogue {
  padding: 0;
  overflow: hidden;
}

.inspector-summary {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.summary-stat {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  background: var(--surface-50);
  border-radius: var(--app-radius);
}

.summary-stat i {
  font-size: var(--ds-font-xl);
  color: var(--primary-color);
}

.summary-stat .stat-value {
  font-size: var(--ds-font-xl);
  font-weight: 700;
  color: var(--text-color);
}

.summary-stat .stat-label {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
  display: block;
}

.inspector-entity,
.inspector-alert {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.entity-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.entity-header i {
  font-size: var(--ds-font-2xl);
  color: var(--primary-color);
}

.entity-header h3 {
  margin: 0;
  font-size: var(--ds-font-lg);
}

.entity-type-label {
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.entity-aliases {
  font-size: var(--ds-font-sm);
  color: var(--text-color-secondary);
}

.entity-aliases .label {
  font-weight: 500;
}

.entity-mentions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-sm);
  color: var(--text-color-secondary);
}

.alert-severity {
  display: inline-block;
  padding: var(--ds-space-1) var(--ds-space-3);
  border-radius: var(--app-radius);
  font-size: var(--ds-font-xs);
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
  font-size: var(--ds-font-base);
}

.inspector-alert p {
  margin: 0;
  font-size: var(--ds-font-sm);
  color: var(--text-color-secondary);
  line-height: var(--ds-leading-normal);
}

.alert-location {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-xs);
  color: var(--text-color-secondary);
}

.alert-actions {
  display: flex;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-2);
}

/* Reanalyze dialog */
.reanalyze-info {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  background: var(--blue-50);
  border-radius: var(--app-radius);
  border-left: var(--ds-border-4) solid var(--blue-500);
  color: var(--blue-900);
  font-size: var(--ds-font-sm);
  margin: 0;
}

.reanalyze-info i {
  font-size: var(--ds-font-xl);
}

.analysis-mode-selector {
  margin-top: var(--ds-space-4);
}

.analysis-mode-label {
  display: block;
  font-size: var(--ds-font-sm);
  font-weight: 600;
  margin-bottom: var(--ds-space-2);
  color: var(--text-color);
}

.analysis-mode-select {
  width: 100%;
  padding: var(--ds-space-2) var(--ds-space-3);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-ground);
  color: var(--text-color);
  font-size: var(--ds-font-sm);
  cursor: pointer;
}

.analysis-mode-select:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: -1px;
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
