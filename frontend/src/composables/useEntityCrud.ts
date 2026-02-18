/**
 * useEntityCrud - Composable para operaciones CRUD de entidades
 *
 * Extrae la lógica compartida de edición, guardado, eliminación y gestión
 * de atributos desde EntitiesTab y CharacterView.
 *
 * Extraído de:
 * - frontend/src/components/workspace/EntitiesTab.vue (L263-716)
 * - frontend/src/views/CharacterView.vue (L346-619)
 */

import { ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { Entity, EntityAttribute } from '@/types'
import { api } from '@/services/apiClient'
import { getAttributeCategoriesForEntityType } from '@/config/attributes'

export interface UseEntityCrudOptions {
  /** Project ID getter */
  projectId: () => number
  /** Callback llamado después de una operación exitosa */
  onSuccess?: () => void
  /** Callback llamado después de cambios en atributos */
  onAttributeChange?: () => void
}

export interface UseEntityCrudReturn {
  // Edit entity dialog state
  editingEntity: Ref<Entity | null>
  showEditDialog: Ref<boolean>
  openEditDialog: (entity: Entity) => void
  saveEntity: () => Promise<void>

  // Delete entity
  deleteEntity: (entity: Entity) => Promise<void>

  // Attribute loading state
  loadingAttributes: Ref<boolean>
  attributes: Ref<EntityAttribute[]>
  loadAttributes: (entityId: number) => Promise<void>

  // Attribute editing (inline)
  editingAttributeId: Ref<number | null>
  editingAttributeValue: Ref<string>
  savingAttribute: Ref<boolean>
  startEditAttribute: (attr: EntityAttribute) => void
  cancelEditAttribute: () => void
  saveEditedAttribute: (attr: EntityAttribute) => Promise<void>

  // Attribute creation
  newAttribute: Ref<{ category: string; name: string; value: string }>
  showAddAttribute: Ref<boolean>
  createAttribute: (entityId: number) => Promise<void>
  getAttributeCategories: (entityType?: string) => Array<{ label: string; value: string }>

  // Attribute deletion
  deleteAttribute: (entityId: number, attributeId: number) => Promise<void>

  // Rich data loading (story-bible)
  loadingRichData: Ref<boolean>
  entityRelationships: Ref<any[]>
  entityVitalStatus: Ref<any | null>
  loadRichData: (entityId: number) => Promise<void>
}

/**
 * Composable para operaciones CRUD de entidades y atributos
 */
export function useEntityCrud(options: UseEntityCrudOptions): UseEntityCrudReturn {
  const toast = useToast()

  // Edit entity dialog state
  const editingEntity = ref<Entity | null>(null)
  const showEditDialog = ref(false)

  // Attribute state
  const loadingAttributes = ref(false)
  const attributes = ref<EntityAttribute[]>([])

  // Inline attribute editing
  const editingAttributeId = ref<number | null>(null)
  const editingAttributeValue = ref('')
  const savingAttribute = ref(false)

  // Attribute creation
  const newAttribute = ref({ category: 'physical', name: '', value: '' })
  const showAddAttribute = ref(false)

  // Rich data state
  const loadingRichData = ref(false)
  const entityRelationships = ref<any[]>([])
  const entityVitalStatus = ref<any | null>(null)

  /**
   * Abre el diálogo de edición de entidad
   */
  function openEditDialog(entity: Entity) {
    editingEntity.value = { ...entity }
    showEditDialog.value = true
  }

  /**
   * Guarda los cambios de la entidad editada
   */
  async function saveEntity() {
    if (!editingEntity.value) {
      showEditDialog.value = false
      return
    }

    try {
      const data = await api.putRaw<any>(
        `/api/projects/${options.projectId()}/entities/${editingEntity.value.id}`,
        {
          name: editingEntity.value.name,
          type: editingEntity.value.type,
          importance: editingEntity.value.importance,
          aliases: editingEntity.value.aliases,
        }
      )

      if (data.success) {
        showEditDialog.value = false
        options.onSuccess?.()
        toast.add({
          severity: 'success',
          summary: 'Guardado',
          detail: 'Entidad actualizada correctamente',
          life: 3000,
        })
      } else {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: `Error al guardar: ${data.error}`,
          life: 5000,
        })
      }
    } catch (err) {
      console.error('Error updating entity:', err)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo guardar la entidad',
        life: 5000,
      })
    }
  }

  /**
   * Elimina (oculta) una entidad del proyecto
   */
  async function deleteEntity(entity: Entity) {
    if (
      !confirm(
        `"${entity.name}" dejará de aparecer en la lista de entidades.\n\nSi vuelves a analizar el documento, podría reaparecer.`
      )
    ) {
      return
    }

    try {
      const data = await api.del<any>(`/api/projects/${options.projectId()}/entities/${entity.id}`)

      if (data.success) {
        options.onSuccess?.()
        toast.add({
          severity: 'success',
          summary: 'Oculta',
          detail: `"${entity.name}" se ha ocultado`,
          life: 3000,
        })
      } else {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: `Error al ocultar: ${data.error}`,
          life: 5000,
        })
      }
    } catch (err) {
      console.error('Error deleting entity:', err)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo ocultar la entidad',
        life: 5000,
      })
    }
  }

  /**
   * Carga los atributos de una entidad
   */
  async function loadAttributes(entityId: number) {
    loadingAttributes.value = true
    try {
      const data = await api.getRaw<any>(`/api/projects/${options.projectId()}/entities/${entityId}/attributes`)
      if (data.success) {
        attributes.value = data.data || []
      } else {
        attributes.value = []
      }
    } catch (err) {
      console.error('Error loading entity attributes:', err)
      attributes.value = []
    } finally {
      loadingAttributes.value = false
    }
  }

  /**
   * Inicia la edición inline de un atributo
   */
  function startEditAttribute(attr: EntityAttribute) {
    editingAttributeId.value = attr.id
    editingAttributeValue.value = attr.value
  }

  /**
   * Cancela la edición inline
   */
  function cancelEditAttribute() {
    editingAttributeId.value = null
    editingAttributeValue.value = ''
  }

  /**
   * Guarda el valor editado de un atributo existente
   */
  async function saveEditedAttribute(attr: EntityAttribute) {
    if (!editingAttributeValue.value.trim()) return

    savingAttribute.value = true
    try {
      const data = await api.putRaw<any>(
        `/api/projects/${options.projectId()}/entities/${attr.entityId}/attributes/${attr.id}`,
        { value: editingAttributeValue.value.trim() }
      )

      if (data.success) {
        await loadAttributes(attr.entityId)
        options.onAttributeChange?.()
        toast.add({
          severity: 'success',
          summary: 'Guardado',
          detail: 'Atributo actualizado',
          life: 2000,
        })
      } else {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: data.error || 'No se pudo actualizar',
          life: 4000,
        })
      }
    } catch (err) {
      console.error('Error updating attribute:', err)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Error al actualizar el atributo',
        life: 4000,
      })
    } finally {
      savingAttribute.value = false
      editingAttributeId.value = null
      editingAttributeValue.value = ''
    }
  }

  /**
   * Crea un nuevo atributo para la entidad
   */
  async function createAttribute(entityId: number) {
    if (!newAttribute.value.name.trim() || !newAttribute.value.value.trim()) {
      toast.add({
        severity: 'warn',
        summary: 'Campos requeridos',
        detail: 'Por favor completa el nombre y valor del atributo',
        life: 4000,
      })
      return
    }

    savingAttribute.value = true
    try {
      const data = await api.postRaw<any>(`/api/projects/${options.projectId()}/entities/${entityId}/attributes`, {
        category: newAttribute.value.category,
        name: newAttribute.value.name.trim(),
        value: newAttribute.value.value.trim(),
        confidence: 1.0,
      })

      if (data.success) {
        await loadAttributes(entityId)
        options.onAttributeChange?.()
        newAttribute.value = { category: 'physical', name: '', value: '' }
        showAddAttribute.value = false
        toast.add({
          severity: 'success',
          summary: 'Creado',
          detail: 'Atributo añadido',
          life: 2000,
        })
      } else {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: data.error || 'No se pudo crear',
          life: 4000,
        })
      }
    } catch (err) {
      console.error('Error creating attribute:', err)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Error al crear el atributo',
        life: 4000,
      })
    } finally {
      savingAttribute.value = false
    }
  }

  /**
   * Elimina un atributo de la entidad
   */
  async function deleteAttribute(entityId: number, attributeId: number) {
    if (!confirm('¿Seguro que deseas eliminar este atributo?')) {
      return
    }

    try {
      const data = await api.del<any>(
        `/api/projects/${options.projectId()}/entities/${entityId}/attributes/${attributeId}`
      )

      if (data.success) {
        await loadAttributes(entityId)
        options.onAttributeChange?.()
        toast.add({
          severity: 'success',
          summary: 'Eliminado',
          detail: 'Atributo eliminado',
          life: 2000,
        })
      } else {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: data.error || 'No se pudo eliminar',
          life: 4000,
        })
      }
    } catch (err) {
      console.error('Error deleting attribute:', err)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Error al eliminar el atributo',
        life: 4000,
      })
    }
  }

  /**
   * Obtiene las categorías de atributos para un tipo de entidad
   * Usa la configuración unificada de attributes.ts
   */
  function getAttributeCategories(entityType?: string) {
    return getAttributeCategoriesForEntityType(entityType)
  }

  /**
   * Carga datos enriquecidos de la entidad desde el story-bible API
   * (relaciones y estado vital)
   */
  async function loadRichData(entityId: number) {
    loadingRichData.value = true
    try {
      const data = await api.getRaw<any>(`/api/projects/${options.projectId()}/story-bible/${entityId}`)
      if (data.success && data.data) {
        const entry = data.data
        entityRelationships.value = entry.relationships || []
        entityVitalStatus.value = entry.vital_status || null
      } else {
        entityRelationships.value = []
        entityVitalStatus.value = null
      }
    } catch (err) {
      console.error('Error loading rich entity data:', err)
      entityRelationships.value = []
      entityVitalStatus.value = null
    } finally {
      loadingRichData.value = false
    }
  }

  return {
    // Edit entity
    editingEntity,
    showEditDialog,
    openEditDialog,
    saveEntity,

    // Delete entity
    deleteEntity,

    // Attributes loading
    loadingAttributes,
    attributes,
    loadAttributes,

    // Attribute editing
    editingAttributeId,
    editingAttributeValue,
    savingAttribute,
    startEditAttribute,
    cancelEditAttribute,
    saveEditedAttribute,

    // Attribute creation
    newAttribute,
    showAddAttribute,
    createAttribute,
    getAttributeCategories,

    // Attribute deletion
    deleteAttribute,

    // Rich data
    loadingRichData,
    entityRelationships,
    entityVitalStatus,
    loadRichData,
  }
}
