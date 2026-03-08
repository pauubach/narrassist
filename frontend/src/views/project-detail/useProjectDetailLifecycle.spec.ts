import { defineComponent, nextTick, reactive, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useProjectDetailLifecycle } from './useProjectDetailLifecycle'

const flushPromises = async () => {
  await Promise.resolve()
  await nextTick()
}

describe('useProjectDetailLifecycle', () => {
  const addEventListenerSpy = vi.spyOn(window, 'addEventListener')
  const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function mountHarness() {
    const project = ref({ id: 7, name: 'Proyecto', wordCount: 1200, chapterCount: 8 })
    const workspaceStore = reactive({
      activeTab: 'summary',
      scrollToPosition: null as number | null,
    })
    const analysisStore = {
      loadExecutedPhases: vi.fn().mockResolvedValue(undefined),
      clearTabStale: vi.fn(),
    }
    const rightInspectorTab = ref<'summary' | 'chapters' | 'dialogue' | 'contextual'>('dialogue')
    const sidebarTab = ref('chapters')
    const alerts = ref([{ id: 1 } as any])
    const isAnalyzing = ref(false)
    const loadEntities = vi.fn().mockResolvedValue(undefined)
    const loadRelationships = vi.fn().mockResolvedValue(undefined)
    const loadAlerts = vi.fn().mockResolvedValue(undefined)
    const loadChapters = vi.fn().mockResolvedValue(undefined)
    const loadChapterSummaries = vi.fn().mockResolvedValue(undefined)
    const updateProjectStats = vi.fn()
    const prefetchPanels = vi.fn()

    const Harness = defineComponent({
      setup(_, { expose }) {
        const lifecycle = useProjectDetailLifecycle({
          project,
          workspaceStore: workspaceStore as any,
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
          prefetchPanels,
        })

        expose({
          project,
          workspaceStore,
          rightInspectorTab,
          sidebarTab,
          alerts,
          isAnalyzing,
          analysisStore,
          loadEntities,
          loadRelationships,
          loadAlerts,
          loadChapters,
          loadChapterSummaries,
          updateProjectStats,
          prefetchPanels,
          ...lifecycle,
        })

        return () => null
      },
    })

    const wrapper = mount(Harness)
    return {
      wrapper,
      project,
      workspaceStore,
      rightInspectorTab,
      sidebarTab,
      alerts,
      isAnalyzing,
      analysisStore,
      loadEntities,
      loadRelationships,
      loadAlerts,
      loadChapters,
      loadChapterSummaries,
      updateProjectStats,
      prefetchPanels,
      onAnalysisCompleted: (wrapper.vm as any).onAnalysisCompleted as () => Promise<void>,
    }
  }

  it('recarga relaciones y limpia stale al entrar en relationships', async () => {
    const vm = mountHarness()

    vm.workspaceStore.activeTab = 'relationships' as any
    await flushPromises()

    expect(vm.loadEntities).toHaveBeenCalledWith(7)
    expect(vm.loadRelationships).toHaveBeenCalledWith(7)
    expect(vm.analysisStore.clearTabStale).toHaveBeenCalledWith(7, 'relationships')
    expect(vm.rightInspectorTab.value).toBe('summary')
  })

  it('recarga alertas cuando cambia la configuracion global', async () => {
    const vm = mountHarness()

    window.dispatchEvent(new Event('settings-changed'))
    await flushPromises()

    expect(vm.loadAlerts).toHaveBeenCalledWith(7, true)
    expect(addEventListenerSpy).toHaveBeenCalledWith('settings-changed', expect.any(Function))
  })

  it('recalcula resumenes cuando termina un analisis', async () => {
    const vm = mountHarness()

    vm.isAnalyzing.value = true
    await nextTick()
    vm.isAnalyzing.value = false
    await flushPromises()

    expect(vm.loadChapterSummaries).toHaveBeenCalledWith(7, true)
  })

  it('actualiza stats con debounce cuando cambia el numero de alertas', async () => {
    const vm = mountHarness()

    vm.alerts.value = [{ id: 1 } as any, { id: 2 } as any]
    await nextTick()
    vi.advanceTimersByTime(500)
    await flushPromises()

    expect(vm.updateProjectStats).toHaveBeenCalledWith(7, 'Proyecto', vm.alerts.value)
  })

  it('prefetches panels on mount and removes listeners on unmount', async () => {
    const wrapper = mount(
      defineComponent({
        setup(_, { expose }) {
          const project = ref({ id: 7, name: 'Proyecto', wordCount: 1200, chapterCount: 8 })
          const workspaceStore = reactive({ activeTab: 'summary', scrollToPosition: null as number | null })
          const prefetchPanels = vi.fn()

          useProjectDetailLifecycle({
            project,
            workspaceStore: workspaceStore as any,
            analysisStore: {
              loadExecutedPhases: vi.fn().mockResolvedValue(undefined),
              clearTabStale: vi.fn(),
            },
            rightInspectorTab: ref<'summary' | 'chapters' | 'dialogue' | 'contextual'>('summary'),
            sidebarTab: ref('chapters'),
            alerts: ref([]),
            isAnalyzing: ref(false),
            loadEntities: vi.fn().mockResolvedValue(undefined),
            loadRelationships: vi.fn().mockResolvedValue(undefined),
            loadAlerts: vi.fn().mockResolvedValue(undefined),
            loadChapters: vi.fn().mockResolvedValue(undefined),
            loadChapterSummaries: vi.fn().mockResolvedValue(undefined),
            updateProjectStats: vi.fn(),
            prefetchPanels,
          })

          expose({ prefetchPanels })
          return () => null
        },
      }),
    )

    vi.runAllTimers()
    await flushPromises()

    expect((wrapper.vm as any).prefetchPanels).toHaveBeenCalled()

    wrapper.unmount()
    expect(removeEventListenerSpy).toHaveBeenCalledWith('settings-changed', expect.any(Function))
  })

  it('recarga fases y datos relevantes al completar analisis parcial', async () => {
    const vm = mountHarness()
    vm.workspaceStore.activeTab = 'alerts' as any

    await vm.onAnalysisCompleted()

    expect(vm.analysisStore.loadExecutedPhases).toHaveBeenCalledWith(7)
    expect(vm.loadAlerts).toHaveBeenCalledWith(7)
    expect(vm.analysisStore.clearTabStale).toHaveBeenCalledWith(7, 'alerts')
  })
})
