import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Project } from '@/types'
import type { ApiProject } from '@/types/api'
import { transformProject, transformProjects } from '@/types/transformers'
import { api } from '@/services/apiClient'
import { ensureBackendReady } from '@/composables/useBackendReady'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const projectCount = computed(() => projects.value.length)
  const hasProjects = computed(() => projectCount.value > 0)
  const recentProjects = computed(() =>
    [...projects.value]
      .sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime())
      .slice(0, 5)
  )

  async function fetchProjects() {
    loading.value = true
    error.value = null

    try {
      await ensureBackendReady()
      const data = await api.get<ApiProject[]>('/api/projects')
      projects.value = transformProjects(data)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to fetch projects:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    error.value = null

    try {
      await ensureBackendReady()
      const data = await api.get<ApiProject>(`/api/projects/${id}`)
      const transformed = transformProject(data)
      currentProject.value = transformed

      const index = projects.value.findIndex(p => p.id === id)
      if (index !== -1) {
        projects.value[index] = transformed
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to fetch project:', err)
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string, description?: string, file?: File) {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('name', name)
      if (description) formData.append('description', description)
      if (file) formData.append('file', file)

      const data = await api.postForm<ApiProject>('/api/projects', formData)
      const transformed = transformProject(data)
      projects.value.push(transformed)
      currentProject.value = transformed
      return transformed
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to create project:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /** Actualiza solo progreso y estado de análisis sin recargar toda la lista */
  function updateProjectProgress(projectId: number, progress: number, status: string) {
    const idx = projects.value.findIndex(p => p.id === projectId)
    if (idx !== -1) {
      projects.value[idx] = {
        ...projects.value[idx],
        analysisProgress: progress,
        analysisStatus: status as Project['analysisStatus'],
      }
    }
  }

  function clearCurrentProject() {
    currentProject.value = null
  }

  return {
    projects,
    currentProject,
    loading,
    error,
    projectCount,
    hasProjects,
    recentProjects,
    fetchProjects,
    fetchProject,
    createProject,
    updateProjectProgress,
    clearCurrentProject
  }
})
