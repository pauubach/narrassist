import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExportDialog from './ExportDialog.vue'

const { toastAddMock, apiMock, projectExportsMock, fileDownloadMock } = vi.hoisted(() => ({
  toastAddMock: vi.fn(),
  apiMock: {
    getRaw: vi.fn(),
  },
  projectExportsMock: {
    exportDocumentBlob: vi.fn(),
    exportCorrectedDocumentBlob: vi.fn(),
    exportEditorialWorkBlob: vi.fn(),
    exportScrivenerBlob: vi.fn(),
  },
  fileDownloadMock: {
    decodeBase64ToBlob: vi.fn(),
    downloadBlob: vi.fn(),
    downloadTextFile: vi.fn(),
  },
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAddMock }),
}))

vi.mock('@/services/apiClient', () => ({
  api: apiMock,
}))

vi.mock('@/services/projectExports', () => projectExportsMock)

vi.mock('@/utils/fileDownload', () => fileDownloadMock)

vi.mock('./ImportWorkDialog.vue', () => ({
  default: defineComponent({
    name: 'ImportWorkDialog',
    props: {
      visible: {
        type: Boolean,
        default: false,
      },
    },
    emits: ['update:visible', 'imported'],
    template: '<div v-if="visible" data-test="import-work-dialog">import work</div>',
  }),
}))

const ButtonStub = defineComponent({
  name: 'Button',
  props: ['label', 'disabled', 'loading', 'icon', 'outlined', 'size', 'text', 'rounded', 'severity'],
  emits: ['click'],
  template: '<button :disabled="disabled || loading" @click="$emit(\'click\')">{{ label || icon || "button" }}</button>',
})

const DialogStub = defineComponent({
  name: 'Dialog',
  props: ['visible', 'header'],
  emits: ['update:visible'],
  template: '<div v-if="visible" class="dialog-stub"><h2>{{ header }}</h2><slot /></div>',
})

const CardStub = defineComponent({
  name: 'Card',
  template: '<section class="card-stub"><slot name="title" /><slot name="subtitle" /><slot name="content" /></section>',
})

const CheckboxStub = defineComponent({
  name: 'Checkbox',
  props: ['modelValue', 'binary', 'inputId', 'value'],
  emits: ['update:modelValue'],
  template: '<input type="checkbox">',
})

const SliderStub = defineComponent({
  name: 'Slider',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<div class="slider-stub"></div>',
})

const TagStub = defineComponent({
  name: 'Tag',
  props: ['value'],
  template: '<span class="tag-stub">{{ value }}</span>',
})

function mountDialog() {
  return mount(ExportDialog, {
    props: {
      visible: true,
      projectId: 5,
      projectName: 'Mi Proyecto',
    },
    global: {
      stubs: {
        Button: ButtonStub,
        Dialog: DialogStub,
        Card: CardStub,
        Checkbox: CheckboxStub,
        Slider: SliderStub,
        Tag: TagStub,
      },
      directives: {
        tooltip: {
          mounted: () => {},
          updated: () => {},
          unmounted: () => {},
        },
      },
    },
  })
}

describe('ExportDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getRaw.mockReset()
    projectExportsMock.exportDocumentBlob.mockResolvedValue({
      blob: new Blob(['doc']),
      filename: 'informe.docx',
      response: new Response(),
    })
    projectExportsMock.exportEditorialWorkBlob.mockResolvedValue({
      blob: new Blob(['work']),
      filename: 'trabajo_editorial.narrassist',
      response: new Response(),
    })
  })

  it('exports the full document with the default options', async () => {
    const wrapper = mountDialog()

    await wrapper.findAll('button').find(button => button.text().includes('Exportar documento'))!.trigger('click')
    await flushPromises()

    expect(projectExportsMock.exportDocumentBlob).toHaveBeenCalledWith(5, {
      format: 'docx',
      include_characters: true,
      include_alerts: true,
      include_timeline: true,
      include_relationships: true,
      include_style_guide: true,
      only_main_characters: true,
      only_open_alerts: true,
    })
    expect(fileDownloadMock.downloadBlob).toHaveBeenCalledWith(expect.any(Blob), 'informe.docx')
    expect(toastAddMock).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      summary: 'Exportacion exitosa',
    }))
  })

  it('exports editorial work and opens the import dialog on demand', async () => {
    const wrapper = mountDialog()

    await wrapper.findAll('button').find(button => button.text().includes('Exportar trabajo (.narrassist)'))!.trigger('click')
    await flushPromises()

    expect(projectExportsMock.exportEditorialWorkBlob).toHaveBeenCalledWith(5)
    expect(fileDownloadMock.downloadBlob).toHaveBeenCalledWith(expect.any(Blob), 'trabajo_editorial.narrassist')

    await wrapper.findAll('button').find(button => button.text().includes('Importar trabajo'))!.trigger('click')
    expect(wrapper.get('[data-test="import-work-dialog"]')).toBeTruthy()
  })
})
