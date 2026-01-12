import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Project, ApiResponse } from '@/types'

export const useProjectsStore = defineStore('projects', () => {
  // Estado
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const projectCount = computed(() => projects.value.length)
  const hasProjects = computed(() => projectCount.value > 0)
  const recentProjects = computed(() =>
    [...projects.value]
      .sort((a, b) => new Date(b.last_modified).getTime() - new Date(a.last_modified).getTime())
      .slice(0, 5)
  )

  // Actions
  async function fetchProjects() {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/projects')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<Project[]> = await response.json()
      if (data.success && data.data) {
        projects.value = data.data
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
      const response = await fetch(`/api/projects/${id}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<Project> = await response.json()
      if (data.success && data.data) {
        currentProject.value = data.data

        // Actualizar en la lista si existe
        const index = projects.value.findIndex(p => p.id === id)
        if (index !== -1) {
          projects.value[index] = data.data
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

  async function createProject(name: string, description?: string, file?: File) {
    // NO usamos loading.value aquí para evitar que la UI muestre "Cargando proyectos..."
    // El componente que llama usa su propio estado (creatingProject)
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

      const response = await fetch('/api/projects', {
        method: 'POST',
        body: formData
        // No establecer Content-Type, el navegador lo hará automáticamente con boundary
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ApiResponse<Project> = await response.json()
      if (data.success && data.data) {
        projects.value.push(data.data)
        currentProject.value = data.data
        return data.data
      } else {
        throw new Error(data.error || 'Error desconocido al crear proyecto')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Failed to create project:', err)
      throw err
    }
    // No hay finally con loading.value = false porque no lo pusimos a true
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
