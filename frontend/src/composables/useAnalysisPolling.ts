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

interface AnalysisPollingOptions {
  /** Reactive project computed */
  project: ComputedRef<{ id: number; wordCount?: number; name?: string } | null>
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
  const { project, entities, alerts: _alerts, chapters, loadEntities, loadAlerts, loadChapters } = options

  const analysisStore = useAnalysisStore()
  const projectsStore = useProjectsStore()
  const { notifyAnalysisComplete, notifyAnalysisError } = useNotifications()

  const cancellingAnalysis = ref(false)

  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let chaptersLoadedDuringAnalysis = false
  let entitiesLoadedDuringAnalysis = false
  let alertsPartialLoaded = false
  let alertsFullLoaded = false

  // ── Computed ─────────────────────────────────────────────

  // Fuente única de verdad: el store (setAnalyzing / checkAnalysisStatus)
  const isAnalyzing = computed(() => {
    if (!project.value) return false
    return analysisStore.isProjectAnalyzing(project.value.id)
  })

  const hasBeenAnalyzed = computed(() => {
    if (!project.value) return false
    const p = project.value as any
    return (p.chapterCount || 0) > 0 || (p.entityCount || 0) > 0
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
        return
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

      // Incremental loading: alerts (two-stage via metrics)
      // Stage 1: grammar phase complete → some alerts available
      const grammarPhase = progressData.phases?.find((p: { id: string }) => p.id === 'grammar')
      if (grammarPhase?.completed && !alertsPartialLoaded) {
        alertsPartialLoaded = true
        loadAlerts(project.value!.id)
      }

      // Stage 2: all alerts phase complete → all alerts available
      const alertsPhase = progressData.phases?.find((p: { id: string }) => p.id === 'alerts')
      if (alertsPhase?.completed && !alertsFullLoaded) {
        alertsFullLoaded = true
        loadAlerts(project.value!.id)
      }

      // Ajustar rate de polling según progreso (adaptive polling)
      adjustPollingRate()

      // Idle — no active analysis
      if (progressData.status === 'idle') {
        stopPolling()
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
        // Marcar como no-analizando DESPUÉS de fetchProject para que
        // project.analysisStatus y analysisStore.isAnalyzing cambien juntos
        analysisStore.setAnalyzing(project.value!.id, false)
        await analysisStore.loadExecutedPhases(project.value!.id)
        await loadEntities(project.value!.id)
        await loadAlerts(project.value!.id)
        await loadChapters(project.value!.id)

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

  // Polling adaptativo (performance optimization #7)
  // Intervalo ajustado según progreso: lento al inicio, rápido al final
  function getAdaptiveInterval(progress: number): number {
    if (progress < 0.3) return 3000  // Inicio lento (3s)
    if (progress < 0.6) return 1500  // Medio normal (1.5s)
    if (progress < 0.9) return 1000  // Avanzado rápido (1s)
    return 500  // Final muy rápido (500ms)
  }

  let currentInterval = 1500

  function startPolling() {
    if (pollingInterval) return
    chaptersLoadedDuringAnalysis = false
    entitiesLoadedDuringAnalysis = false
    alertsPartialLoaded = false
    alertsFullLoaded = false
    currentInterval = 1500
    pollingInterval = setInterval(pollProgress, currentInterval)
    pollProgress()
  }

  function adjustPollingRate() {
    if (!pollingInterval || !project.value) return

    const currentProgress = analysisStore.currentAnalysis?.progress ?? 0
    const progress = currentProgress / 100
    const newInterval = getAdaptiveInterval(progress)

    if (newInterval !== currentInterval) {
      currentInterval = newInterval
      clearInterval(pollingInterval)
      pollingInterval = setInterval(pollProgress, currentInterval)
    }
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

  return {
    cancellingAnalysis,
    isAnalyzing,
    hasBeenAnalyzed,
    startPolling,
    stopPolling,
    cancelAnalysis,
  }
}
