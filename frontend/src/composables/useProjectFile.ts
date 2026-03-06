/**
 * Composable para Guardar/Abrir archivos de proyecto .nra
 *
 * Usa el diálogo nativo de Tauri para seleccionar archivos y
 * llama a los endpoints del backend para exportar/importar.
 */
import { ref } from 'vue'
import { api } from '@/services/apiClient'

const saving = ref(false)
const opening = ref(false)

/** Tauri dialog API — cargado dinámicamente */
let dialogModule: {
  save: (opts: Record<string, unknown>) => Promise<string | null>
  open: (opts: Record<string, unknown>) => Promise<string | null>
} | null = null

const isTauriEnv =
  typeof window !== 'undefined' &&
  ('__TAURI__' in window || '__TAURI_INTERNALS__' in window)

/** Promise que resuelve cuando el plugin de diálogo está listo (o falla) */
const dialogReady: Promise<void> = isTauriEnv
  ? import('@tauri-apps/plugin-dialog')
      .then((mod) => {
        dialogModule = mod as unknown as typeof dialogModule
        console.log('[ProjectFile] Dialog plugin loaded')
      })
      .catch((err) => {
        console.warn('[ProjectFile] Failed to load dialog plugin:', err)
      })
  : Promise.resolve()

const NRA_FILTER = {
  name: 'Proyecto Narrative Assistant',
  extensions: ['nra'],
}

interface SaveResult {
  path: string
  size_bytes: number
}

interface OpenResult {
  project_id: number
  project_name: string | null
  warnings: string[]
}

export function useProjectFile() {
  /**
   * Guarda el proyecto actual como archivo .nra
   */
  async function saveProject(projectId: number, projectName: string): Promise<boolean> {
    if (saving.value) return false

    // Esperar a que el plugin de diálogo cargue (evita race condition)
    await dialogReady

    let filePath: string | null = null

    if (dialogModule) {
      // Tauri: diálogo nativo
      filePath = await dialogModule.save({
        title: 'Guardar proyecto',
        defaultPath: `${sanitizeFileName(projectName)}.nra`,
        filters: [NRA_FILTER],
      })
    } else {
      // Fallback: prompt del navegador (dev mode)
      filePath = window.prompt(
        'Ruta para guardar el proyecto:',
        `${sanitizeFileName(projectName)}.nra`
      )
    }

    if (!filePath) return false // Usuario canceló

    saving.value = true
    try {
      await api.post<SaveResult>(
        `/api/projects/${projectId}/save-file`,
        { file_path: filePath },
      )
      return true
    } finally {
      saving.value = false
    }
  }

  /**
   * Abre un proyecto desde un archivo .nra
   * @returns El project_id del proyecto importado, o null si se canceló/falló
   */
  async function openProjectFile(): Promise<{
    projectId: number
    projectName: string
    warnings: string[]
  } | null> {
    if (opening.value) return null

    // Esperar a que el plugin de diálogo cargue (evita race condition)
    await dialogReady

    let filePath: string | null = null

    if (dialogModule) {
      // Tauri: diálogo nativo
      filePath = (await dialogModule.open({
        title: 'Abrir proyecto',
        filters: [NRA_FILTER],
        multiple: false,
        directory: false,
      })) as string | null
    } else {
      // Fallback: prompt del navegador (dev mode)
      filePath = window.prompt('Ruta del archivo .nra a abrir:')
    }

    if (!filePath) return null // Usuario canceló

    opening.value = true
    try {
      const data = await api.post<OpenResult>(
        '/api/projects/open-file',
        { file_path: filePath },
      )

      return {
        projectId: data.project_id,
        projectName: data.project_name || 'Proyecto importado',
        warnings: data.warnings || [],
      }
    } finally {
      opening.value = false
    }
  }

  return {
    saving,
    opening,
    saveProject,
    openProjectFile,
  }
}

/** Limpia un nombre de archivo eliminando caracteres no seguros */
function sanitizeFileName(name: string): string {
  return name
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, '_')
    .substring(0, 100)
}
