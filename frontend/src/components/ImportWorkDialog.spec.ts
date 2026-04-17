import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImportWorkDialog from './ImportWorkDialog.vue'

const { apiMock, toastAddMock } = vi.hoisted(() => ({
  apiMock: {
    postForm: vi.fn(),
    post: vi.fn(),
  },
  toastAddMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: apiMock,
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAddMock }),
}))

const ButtonStub = defineComponent({
  name: 'PButton',
  props: ['label', 'disabled', 'loading', 'severity', 'text', 'icon'],
  emits: ['click'],
  template: '<button :disabled="disabled || loading" @click="$emit(\'click\')">{{ label || icon || "button" }}</button>',
})

const DialogStub = defineComponent({
  name: 'PDialog',
  props: ['visible', 'header'],
  emits: ['update:visible'],
  template: '<div v-if="visible" class="dialog-stub"><h2>{{ header }}</h2><slot /><footer><slot name="footer" /></footer></div>',
})

const CheckboxStub = defineComponent({
  name: 'Checkbox',
  props: ['modelValue', 'binary', 'inputId', 'value'],
  emits: ['update:modelValue'],
  template: '<input type="checkbox">',
})

const FileUploadStub = defineComponent({
  name: 'FileUpload',
  emits: ['select'],
  setup(_props, { emit }) {
    return () => h('button', {
      'data-test': 'select-file',
      onClick: () => emit('select', {
        files: [new File(['contenido'], 'trabajo.narrassist', { type: 'application/octet-stream' })],
      }),
    }, 'Seleccionar archivo')
  },
})

const TagStub = defineComponent({
  name: 'Tag',
  props: ['value'],
  template: '<span class="tag-stub">{{ value }}</span>',
})

function mountDialog() {
  return mount(ImportWorkDialog, {
    props: {
      visible: true,
      projectId: 7,
    },
    global: {
      stubs: {
        Button: ButtonStub,
        Dialog: DialogStub,
        Checkbox: CheckboxStub,
        FileUpload: FileUploadStub,
        Tag: TagStub,
      },
    },
  })
}

describe('ImportWorkDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('previews an editorial work file and confirms the import', async () => {
    apiMock.postForm.mockResolvedValueOnce({
      project_fingerprint_match: true,
      warnings: ['Se omitira una regla ya existente'],
      entity_merges: { to_apply: 2, already_done: 1, conflicts: 0 },
      alert_decisions: { to_apply: 3, already_done: 0, conflicts: 0 },
      verified_attributes: { to_apply: 1, already_done: 0, conflicts: 0 },
      suppression_rules: { to_add: 4, already_exist: 1 },
      conflicts: [],
      total_to_apply: 10,
      total_conflicts: 0,
      import_data: { token: 'preview-data' },
    })
    apiMock.post.mockResolvedValueOnce({
      entity_merges_applied: 2,
      alert_decisions_applied: 3,
      verified_attributes_applied: 1,
      suppression_rules_added: 4,
      conflicts_resolved: 0,
    })

    const wrapper = mountDialog()

    await wrapper.get('[data-test="select-file"]').trigger('click')
    expect(wrapper.text()).toContain('trabajo.narrassist')

    await wrapper.findAll('button').find(button => button.text().includes('Analizar archivo'))!.trigger('click')
    await flushPromises()

    expect(apiMock.postForm).toHaveBeenCalledTimes(1)
    expect(apiMock.postForm.mock.calls[0][0]).toBe('/api/projects/7/import-work/preview')
    expect(apiMock.postForm.mock.calls[0][1]).toBeInstanceOf(FormData)
    expect(wrapper.text()).toContain('Resumen de importacion')
    expect(wrapper.text()).toContain('Se omitira una regla ya existente')

    await wrapper.findAll('button').find(button => button.text().includes('Aplicar cambios'))!.trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/api/projects/7/import-work/confirm', {
      import_data: { token: 'preview-data' },
      import_entity_merges: true,
      import_alert_decisions: true,
      import_verified_attributes: true,
      import_suppression_rules: true,
      conflict_overrides: null,
    })
    expect(wrapper.emitted('imported')).toBeTruthy()
    expect(wrapper.text()).toContain('Importacion completada')

    await wrapper.findAll('button').find(button => button.text().includes('Cerrar'))!.trigger('click')
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('shows a toast when preview analysis fails', async () => {
    apiMock.postForm.mockRejectedValueOnce(new Error('Archivo no valido'))

    const wrapper = mountDialog()
    await wrapper.get('[data-test="select-file"]').trigger('click')
    await wrapper.findAll('button').find(button => button.text().includes('Analizar archivo'))!.trigger('click')
    await flushPromises()

    expect(toastAddMock).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'error',
      detail: 'Archivo no valido',
    }))
    expect(wrapper.text()).not.toContain('Resumen de importacion')
  })
})
