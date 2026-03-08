import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { apiPostMock, dialogSaveMock, dialogOpenMock } = vi.hoisted(() => ({
  apiPostMock: vi.fn(),
  dialogSaveMock: vi.fn(),
  dialogOpenMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    post: apiPostMock,
  },
}))

vi.mock('@tauri-apps/plugin-dialog', () => ({
  save: dialogSaveMock,
  open: dialogOpenMock,
}))

describe('useProjectFile', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    delete (window as Window & { __TAURI__?: unknown }).__TAURI__
  })

  afterEach(() => {
    delete (window as Window & { __TAURI__?: unknown }).__TAURI__
  })

  async function loadComposableInTauri() {
    Object.defineProperty(window, '__TAURI__', {
      value: {},
      configurable: true,
    })
    const { useProjectFile } = await import('./useProjectFile')
    return useProjectFile()
  }

  it('saveProject sanitizes the default filename and posts the selected path', async () => {
    dialogSaveMock.mockResolvedValueOnce('D:/Exports/proyecto.nra')
    apiPostMock.mockResolvedValueOnce({ path: 'D:/Exports/proyecto.nra', size_bytes: 1024 })

    const { saveProject, saving } = await loadComposableInTauri()
    const result = await saveProject(7, 'Mi:Proyecto/Con*Caracteres?')

    expect(result).toBe(true)
    expect(dialogSaveMock).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Guardar proyecto',
      defaultPath: 'Mi_Proyecto_Con_Caracteres_.nra',
    }))
    expect(apiPostMock).toHaveBeenCalledWith('/api/projects/7/save-file', {
      file_path: 'D:/Exports/proyecto.nra',
    })
    expect(saving.value).toBe(false)
  })

  it('saveProject returns false when the user cancels the dialog', async () => {
    dialogSaveMock.mockResolvedValueOnce(null)

    const { saveProject } = await loadComposableInTauri()
    const result = await saveProject(7, 'Proyecto')

    expect(result).toBe(false)
    expect(apiPostMock).not.toHaveBeenCalled()
  })

  it('openProjectFile normalizes imported project data and warnings', async () => {
    dialogOpenMock.mockResolvedValueOnce('D:/Imports/proyecto.nra')
    apiPostMock.mockResolvedValueOnce({
      project_id: 15,
      project_name: null,
      warnings: ['Algunas relaciones no se pudieron importar'],
    })

    const { openProjectFile, opening } = await loadComposableInTauri()
    const result = await openProjectFile()

    expect(dialogOpenMock).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Abrir proyecto',
      multiple: false,
      directory: false,
    }))
    expect(apiPostMock).toHaveBeenCalledWith('/api/projects/open-file', {
      file_path: 'D:/Imports/proyecto.nra',
    })
    expect(result).toEqual({
      projectId: 15,
      projectName: 'Proyecto importado',
      warnings: ['Algunas relaciones no se pudieron importar'],
    })
    expect(opening.value).toBe(false)
  })

  it('throws a desktop-only error outside Tauri', async () => {
    const { useProjectFile } = await import('./useProjectFile')
    const { saveProject, openProjectFile } = useProjectFile()

    await expect(saveProject(7, 'Proyecto')).rejects.toThrow(
      'Guardar proyectos como archivo solo esta disponible en la app de escritorio.',
    )
    await expect(openProjectFile()).rejects.toThrow(
      'Abrir proyectos desde archivo solo esta disponible en la app de escritorio.',
    )
  })
})
