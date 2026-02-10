/**
 * Composable: analysis polling state machine.
 *
 * Extracted from ProjectDetailView — manages polling interval, progress tracking,
 * incremental data loading during analysis, and cancel/complete lifecycle.
 */

import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import { useProjectsStore } from '@/stores/projects'
import { useNotifications } from '@/composables/useNotifications'
import type { Entity, Alert, Chapter } from '@/types'

interface ProgressData {
  progress: number
  phase: string
  error?: string
  metrics?: { chapters_found?: number; entities_found?: number }
}

interface AnalysisPollingOptions {
  /** Reactive project computed */
  project: ComputedRef<{ id: number; analysisStatus?: string | null; wordCount?: number; name?: string } | null>
  /** Data refs to populate incrementally during analysis */
  entities: Ref<Entity[]>
  alerts: Ref<Alert[]>
  chapters: Ref<Chapter[]>
  /** Loaders called when incremental data becomes available */
  loadEntities: (projectId: number) => Promise<void>
  loadAlerts: (projectId: number) => Promise<void>
  loadChapters: (projectId: number) => Promise<void>
}

export function useAnalysisPolling(options: AnalysisPollingOptions) {
  const { project, entities, alerts, chapters, loadEntities, loadAlerts, loadChapters } = options

  const analysisStore = useAnalysisStore()
  const projectsStore = useProjectsStore()
  const { notifyAnalysisComplete, notifyAnalysisError } = useNotifications()

  const analysisProgressData = ref<ProgressData | null>(null)
  const cancellingAnalysis = ref(false)

  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let chaptersLoadedDuringAnalysis = false
  let entitiesLoadedDuringAnalysis = false
  let alertsLoadedDuringAnalysis = false

  // ── Computed ─────────────────────────────────────────────

  const isAnalyzing = computed(() => {
    if (!project.value) return false
    const status = project.value.analysisStatus
    const activeStatuses = ['in_progress', 'analyzing']
    return status ? activeStatuses.includes(status) : false
  })

  const hasBeenAnalyzed = computed(() => {
    if (!project.value) return false
    const p = project.value as any
    return (p.chapterCount || 0) > 0 || (p.entityCount || 0) > 0
  })

  const analysisProgress = computed(() => {
    if (analysisProgressData.value) return analysisProgressData.value.progress
    if (!project.value) return 0
    return (project.value as any).analysisProgress || 0
  })

  const analysisPhase = computed(() => {
    return analysisProgressData.value?.phase || 'Analizando...'
  })

  // ── Polling ──────────────────────────────────────────────

  async function pollProgress() {
    if (!project.value) {
      stopPolling()
      return
    }

    try {
      const progressData = await analysisStore.getProgress(project.value.id)

      if (!progressData) {
        stopPolling()
        analysisProgressData.value = null
        return
      }

      analysisProgressData.value = {
        progress: progressData.progress || 0,
        phase: progressData.current_phase || 'Analizando...',
        error: progressData.error,
        metrics: progressData.metrics,
      }

      // Incremental loading: chapters
      const chaptersFound = progressData.metrics?.chapters_found
      if (chaptersFound && chaptersFound > 0 && !chaptersLoadedDuringAnalysis && chapters.value.length === 0) {
        chaptersLoadedDuringAnalysis = true
        loadChapters(project.value!.id)
      }

      // Incremental loading: entities
      const entitiesFound = progressData.metrics?.entities_found
      if (entitiesFound && entitiesFound > 0 && !entitiesLoadedDuringAnalysis && entities.value.length === 0) {
        entitiesLoadedDuringAnalysis = true
        loadEntities(project.value!.id)
      }

      // Incremental loading: alerts (after grammar phase)
      const grammarPhase = progressData.phases?.find((p: { id: string }) => p.id === 'grammar')
      if (grammarPhase?.completed && !alertsLoadedDuringAnalysis && alerts.value.length === 0) {
        alertsLoadedDuringAnalysis = true
        loadAlerts(project.value!.id)
      }

      // Idle — no active analysis
      if (progressData.status === 'idle') {
        stopPolling()
        analysisProgressData.value = null
        return
      }

      // Terminal states
      if (['completed', 'error', 'failed', 'cancelled'].includes(progressData.status)) {
        stopPolling()

        if (progressData.status === 'completed') {
          notifyAnalysisComplete(project.value?.name)
        } else {
          notifyAnalysisError(progressData.error || 'Error durante el análisis')
        }

        // Small delay to let the DB commit
        await new Promise(resolve => setTimeout(resolve, 500))

        await projectsStore.fetchProject(project.value!.id)
        await analysisStore.loadExecutedPhases(project.value!.id)
        await loadEntities(project.value!.id)
        await loadAlerts(project.value!.id)
        await loadChapters(project.value!.id)
        analysisProgressData.value = null

        // Retry if data seems stale
        if (project.value && project.value.wordCount === 0 && (progressData.metrics?.chapters_found || 0) > 0) {
          await new Promise(resolve => setTimeout(resolve, 1000))
          await projectsStore.fetchProject(project.value.id)
          await loadChapters(project.value.id)
        }
      }
    } catch (err) {
      console.error('Error polling analysis progress:', err)
      stopPolling()
    }
  }

  function startPolling() {
    if (pollingInterval) return
    chaptersLoadedDuringAnalysis = false
    entitiesLoadedDuringAnalysis = false
    alertsLoadedDuringAnalysis = false
    pollingInterval = setInterval(pollProgress, 1500)
    pollProgress()
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  }

  // ── Cancel ───────────────────────────────────────────────

  async function cancelAnalysis() {
    if (!project.value) return
    cancellingAnalysis.value = true
    try {
      const success = await analysisStore.cancelAnalysis(project.value.id)
      if (success) {
        stopPolling()
        analysisProgressData.value = null
        await projectsStore.fetchProject(project.value.id)
      }
    } finally {
      cancellingAnalysis.value = false
    }
  }

  // ── Watchers ─────────────────────────────────────────────

  watch(isAnalyzing, (analyzing) => {
    if (analyzing) startPolling()
    else stopPolling()
  }, { immediate: true })

  watch(() => project.value?.analysisStatus, (newStatus) => {
    if (newStatus === 'in_progress' || newStatus === 'analyzing' || newStatus === 'queued' || newStatus === 'queued_for_heavy') {
      if (!pollingInterval) startPolling()
    }
  })

  return {
    analysisProgressData,
    cancellingAnalysis,
    isAnalyzing,
    hasBeenAnalyzed,
    analysisProgress,
    analysisPhase,
    startPolling,
    stopPolling,
    cancelAnalysis,
  }
}
