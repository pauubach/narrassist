import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { Project, ApiResponse } from '@/types'
import type { ApiProject } from '@/types/api'
import { transformProject, transformProjects } from '@/types/transformers'
import { apiUrl } from '@/config/api'
import { useSystemStore } from '@/stores/system'

/** Espera a que el backend esté listo antes de hacer llamadas API */
async function ensureBackendReady(): Promise<void> {
  const systemStore = useSystemStore()
  if (systemStore.backendReady) return
  // Esperar a que backendReady cambie a true (max 65s, el waitForBackend ya se ejecuta en ModelSetupDialog)
  return new Promise((resolve) => {
    if (systemStore.backendReady) { resolve(); return }
    const unwatch = watch(() => systemStore.backendReady, (ready) => {
      if (ready) {
        unwatch()
        resolve()
      }
    })
    // Safety timeout: no bloquear indefinidamente
    setTimeout(() => { unwatch(); resolve() }, 65000)
  })
}

export const useProjectsStore = defineStore('projects', () => {
  // Estado - usando domain types (camelCase)
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const projectCount = computed(() => projects.value.length)
  const hasProjects = computed(() => projectCount.value > 0)
  const recentProjects = computed(() =>
    [...projects.value]
      .sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime())
      .slice(0, 5)
  )

  // Actions
  async function fetchProjects() {
    loading.value = true
    error.value = null

    try {
      // Esperar a que el backend este listo antes de hacer el fetch
      await ensureBackendReady()
      const response = await fetch(apiUrl('/api/projects'))
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<ApiProject[]> = await response.json()
      if (data.success && data.data) {
        // Transformar de API (snake_case) a Domain (camelCase)
        projects.value = transformProjects(data.data)
      } else {
        throw new Error(data.error || 'Error desconocido al cargar proyectos')
      }
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
      const response = await fetch(apiUrl(`/api/projects/${id}`))
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<ApiProject> = await response.json()
      if (data.success && data.data) {
        // Transformar de API a Domain
        const transformed = transformProject(data.data)
        currentProject.value = transformed

        // Actualizar en la lista si existe
        const index = projects.value.findIndex(p => p.id === id)
        if (index !== -1) {
          projects.value[index] = transformed
        }
      } else {
        throw new Error(data.error || 'Error desconocido al cargar proyecto')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to fetch project:', err)
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string, description?: string, file?: File, rules?: string) {
    error.value = null

    try {
      const formData = new FormData()
      formData.append('name', name)
      if (description) {
        formData.append('description', description)
      }
      if (file) {
        formData.append('file', file)
      }
      if (rules) {
        formData.append('rules', rules)
      }

      const response = await fetch(apiUrl('/api/projects'), {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<ApiProject> = await response.json()
      if (data.success && data.data) {
        // Transformar de API a Domain
        const transformed = transformProject(data.data)
        projects.value.push(transformed)
        currentProject.value = transformed
        return transformed
      } else {
        throw new Error(data.error || 'Error desconocido al crear proyecto')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to create project:', err)
      throw err
    }
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentProject() {
    currentProject.value = null
  }

  return {
    // State
    projects,
    currentProject,
    loading,
    error,
    // Getters
    projectCount,
    hasProjects,
    recentProjects,
    // Actions
    fetchProjects,
    fetchProject,
    createProject,
    clearError,
    clearCurrentProject
  }
})
