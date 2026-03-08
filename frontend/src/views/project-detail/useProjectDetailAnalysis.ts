import { ref, type Ref } from 'vue'
import { api } from '@/services/apiClient'
import type { ExecutedPhases } from '@/stores/analysis'
import type { Alert, Entity } from '@/types'
import type { Project } from '@/types/domain/projects'

type ToastSeverity = 'info' | 'warn' | 'success' | 'error'

type ToastAdd = (message: {
  severity: ToastSeverity
  summary: string
  detail?: string
  life: number
}) => void

type ProjectAnalysisTarget = Pick<Project, 'id' | 'wordCount' | 'chapterCount'>
type ChapterFallback = Pick<Project, 'wordCount' | 'chapterCount'>
type PartialAnalysisPhase = keyof ExecutedPhases

interface AnalysisStoreLike {
  error?: string | null
  runPartialAnalysis: (
    projectId: number,
    phases: PartialAnalysisPhase[],
    forceSync?: boolean,
  ) => Promise<boolean>
  setAnalyzing: (projectId: number, value: boolean) => void
}

interface ProjectsStoreLike {
  fetchProject: (projectId: number) => Promise<unknown>
}

interface UseProjectDetailAnalysisOptions {
  project: Ref<ProjectAnalysisTarget | null | undefined>
  showReanalyzeDialog: Ref<boolean>
  selectedAnalysisMode: Ref<string>
  entities: Ref<Entity[]>
  alerts: Ref<Alert[]>
  isAnalyzing: Ref<boolean>
  replaceDocumentInputRef: Ref<HTMLInputElement | null>
  analysisStore: AnalysisStoreLike
  projectsStore: ProjectsStoreLike
  stopAnalysisPolling: () => void
  loadEntities: (projectId: number, forceReload?: boolean) => Promise<void>
  loadAlerts: (projectId: number, forceReload?: boolean) => Promise<void>
  loadChapters: (projectId: number, project?: ChapterFallback, forceReload?: boolean) => Promise<void>
  waitForPendingAnalysisSettingsSync: (projectId: number) => Promise<boolean>
  requestNotificationPermission: () => void
  setError: (message: string) => void
  addToast: ToastAdd
}

export function useProjectDetailAnalysis(options: UseProjectDetailAnalysisOptions) {
  const reanalyzing = ref(false)
  const retryingTimeline = ref(false)

  const retryTimelinePhase = async () => {
    const project = options.project.value
    if (!project || retryingTimeline.value) return

    if (options.isAnalyzing.value) {
      options.addToast({
        severity: 'info',
        summary: 'Análisis en curso',
        detail: 'Espera a que termine el análisis actual para reintentar la cronología.',
        life: 3500,
      })
      return
    }

    retryingTimeline.value = true
    try {
      const settingsSyncOk = await options.waitForPendingAnalysisSettingsSync(project.id)
      if (!settingsSyncOk) {
        options.addToast({
          severity: 'warn',
          summary: 'Configuración pendiente',
          detail: 'No se pudo confirmar la última configuración. Se usará la configuración guardada disponible.',
          life: 4000,
        })
      }

      const started = await options.analysisStore.runPartialAnalysis(project.id, ['timeline'], true)
      if (started) {
        options.addToast({
          severity: 'info',
          summary: 'Cronología en actualización',
          detail: 'Estamos reconstruyendo la línea temporal con los datos más recientes.',
          life: 3500,
        })
      } else {
        options.addToast({
          severity: 'warn',
          summary: 'No se pudo iniciar',
          detail: options.analysisStore.error || 'No se pudo iniciar el reanálisis de cronología. Inténtalo de nuevo.',
          life: 4000,
        })
      }
    } catch (err) {
      const detail = err instanceof Error
        ? err.message
        : 'No se pudo reintentar la cronología. Si persiste, reinicia la aplicación.'
      options.addToast({
        severity: 'error',
        summary: 'Error al reintentar',
        detail,
        life: 4500,
      })
    } finally {
      retryingTimeline.value = false
    }
  }

  const startReanalysis = async () => {
    const project = options.project.value
    if (!project) return

    reanalyzing.value = true
    options.showReanalyzeDialog.value = false
    options.requestNotificationPermission()
    options.entities.value = []
    options.alerts.value = []
    options.stopAnalysisPolling()

    try {
      const settingsSyncOk = await options.waitForPendingAnalysisSettingsSync(project.id)
      if (!settingsSyncOk) {
        options.addToast({
          severity: 'warn',
          summary: 'Configuración pendiente',
          detail: 'No se pudo confirmar la última configuración. Se iniciará el análisis con la configuración guardada disponible.',
          life: 4000,
        })
      }

      const modeParam = options.selectedAnalysisMode.value !== 'auto'
        ? `?mode=${options.selectedAnalysisMode.value}`
        : ''
      const data = await api.postRaw<{ success: boolean; error?: string }>(
        `/api/projects/${project.id}/reanalyze${modeParam}`,
      )

      if (data.success) {
        options.analysisStore.setAnalyzing(project.id, true)
        await options.projectsStore.fetchProject(project.id)
        return
      }

      options.setError(data.error || 'Error al re-analizar')
      await options.loadEntities(project.id)
      await options.loadAlerts(project.id)
    } catch {
      options.setError('No se pudo re-analizar el documento. Si persiste, reinicia la aplicación.')
      await options.loadEntities(project.id)
      await options.loadAlerts(project.id)
    } finally {
      reanalyzing.value = false
    }
  }

  const openUpdateDocumentDialog = () => {
    options.replaceDocumentInputRef.value?.click()
  }

  const onReplaceDocumentSelected = async (event: Event) => {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    const project = options.project.value
    if (!file || !project) return

    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await api.postForm<{
        project_id: number
        classification: string
        confidence: number
        recommended_full_run: boolean
      }>(`/api/projects/${project.id}/document/replace`, formData, { timeout: 120000 })

      options.addToast({
        severity: 'success',
        summary: 'Manuscrito actualizado',
        detail: `Clasificación: ${result.classification}. Ejecuta un nuevo análisis.`,
        life: 4000,
      })
      await options.projectsStore.fetchProject(project.id)
      await options.loadChapters(project.id, project)
      options.entities.value = []
      options.alerts.value = []
    } catch (err) {
      const detail = err instanceof Error
        ? err.message
        : 'No se pudo actualizar el manuscrito. Crea un proyecto nuevo para este archivo.'
      options.addToast({
        severity: 'error',
        summary: 'Actualización bloqueada',
        detail,
        life: 5000,
      })
    } finally {
      input.value = ''
    }
  }

  return {
    reanalyzing,
    retryingTimeline,
    retryTimelinePhase,
    startReanalysis,
    openUpdateDocumentDialog,
    onReplaceDocumentSelected,
  }
}
