/**
 * Store para selección de elementos
 *
 * Gestiona qué entidades, alertas o menciones están seleccionadas
 * y coordina el resaltado bidireccional.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Entity, Alert } from '@/types'

export type SelectionType = 'entity' | 'alert' | 'mention' | 'text'

export interface Selection {
  type: SelectionType
  id: number
  data?: Entity | Alert | unknown
}

export interface TextSelection {
  start: number
  end: number
  text: string
  chapter?: string
}

export const useSelectionStore = defineStore('selection', () => {
  // ============================================================================
  // Estado
  // ============================================================================

  /** Selección principal (el elemento activo en el panel derecho) */
  const primary = ref<Selection | null>(null)

  /** Selecciones secundarias (para operaciones multi-select) */
  const secondary = ref<Selection[]>([])

  /** Selección de texto en el editor */
  const textSelection = ref<TextSelection | null>(null)

  /** Elemento bajo el cursor (hover) */
  const hovered = ref<Selection | null>(null)

  /** Si está en modo multi-selección */
  const multiSelectMode = ref(false)

  // ============================================================================
  // Getters
  // ============================================================================

  /** Todas las selecciones (primaria + secundarias) */
  const all = computed(() => {
    const selections: Selection[] = []
    if (primary.value) selections.push(primary.value)
    selections.push(...secondary.value)
    return selections
  })

  /** IDs de todas las entidades seleccionadas */
  const selectedEntityIds = computed(() => {
    return all.value.filter(s => s.type === 'entity').map(s => s.id)
  })

  /** IDs de todas las alertas seleccionadas */
  const selectedAlertIds = computed(() => {
    return all.value.filter(s => s.type === 'alert').map(s => s.id)
  })

  /** Si hay alguna selección activa */
  const hasSelection = computed(() => primary.value !== null)

  /** Si hay múltiples selecciones */
  const hasMultipleSelections = computed(() => secondary.value.length > 0)

  /** Cantidad total de selecciones */
  const count = computed(() => all.value.length)

  // ============================================================================
  // Acciones
  // ============================================================================

  /**
   * Selecciona un elemento como primario
   */
  function select(type: SelectionType, id: number, data?: Entity | Alert | unknown) {
    // Si está en modo multi-select, añade a secundarios
    if (multiSelectMode.value && primary.value) {
      addToSecondary(type, id, data)
      return
    }

    // Selección normal: reemplaza la selección primaria
    primary.value = { type, id, data }
    secondary.value = []
  }

  /**
   * Selecciona una entidad
   */
  function selectEntity(entity: Entity) {
    select('entity', entity.id, entity)
  }

  /**
   * Selecciona una alerta
   */
  function selectAlert(alert: Alert) {
    select('alert', alert.id, alert)
  }

  /**
   * Añade un elemento a las selecciones secundarias
   */
  function addToSecondary(type: SelectionType, id: number, data?: Entity | Alert | unknown) {
    // No añadir duplicados
    if (isSelected(type, id)) return

    secondary.value.push({ type, id, data })
  }

  /**
   * Elimina un elemento de las selecciones secundarias
   */
  function removeFromSecondary(type: SelectionType, id: number) {
    secondary.value = secondary.value.filter(s => !(s.type === type && s.id === id))
  }

  /**
   * Alterna la selección de un elemento
   */
  function toggle(type: SelectionType, id: number, data?: Entity | Alert | unknown) {
    if (isSelected(type, id)) {
      // Si es el primario, deseleccionar
      if (primary.value?.type === type && primary.value?.id === id) {
        // Promover el primer secundario a primario
        primary.value = secondary.value.shift() || null
      } else {
        removeFromSecondary(type, id)
      }
    } else {
      if (multiSelectMode.value) {
        addToSecondary(type, id, data)
      } else {
        select(type, id, data)
      }
    }
  }

  /**
   * Verifica si un elemento está seleccionado
   */
  function isSelected(type: SelectionType, id: number): boolean {
    if (primary.value?.type === type && primary.value?.id === id) return true
    return secondary.value.some(s => s.type === type && s.id === id)
  }

  /**
   * Establece la selección de texto
   */
  function setTextSelection(selection: TextSelection | null) {
    textSelection.value = selection
  }

  /**
   * Establece el elemento bajo hover
   */
  function setHovered(type: SelectionType | null, id?: number, data?: unknown) {
    if (type === null) {
      hovered.value = null
    } else {
      hovered.value = { type, id: id!, data }
    }
  }

  /**
   * Activa/desactiva el modo multi-selección
   */
  function setMultiSelectMode(enabled: boolean) {
    multiSelectMode.value = enabled
    if (!enabled) {
      // Al desactivar, mantener solo la selección primaria
      secondary.value = []
    }
  }

  /**
   * Limpia la selección primaria
   */
  function clearPrimary() {
    primary.value = null
  }

  /**
   * Limpia todas las selecciones
   */
  function clearAll() {
    primary.value = null
    secondary.value = []
    textSelection.value = null
    hovered.value = null
    multiSelectMode.value = false
  }

  /**
   * Limpia solo las selecciones de un tipo
   */
  function clearType(type: SelectionType) {
    if (primary.value?.type === type) {
      // Promover secundario del mismo tipo si existe
      const nextOfType = secondary.value.find(s => s.type !== type)
      primary.value = nextOfType || null
    }
    secondary.value = secondary.value.filter(s => s.type !== type)
  }

  /**
   * Selecciona múltiples entidades
   */
  function selectEntities(entities: Entity[]) {
    if (entities.length === 0) {
      clearType('entity')
      return
    }

    primary.value = { type: 'entity', id: entities[0].id, data: entities[0] }
    secondary.value = entities.slice(1).map(e => ({ type: 'entity' as SelectionType, id: e.id, data: e }))
  }

  /**
   * Obtiene las entidades seleccionadas
   */
  function getSelectedEntities(): Entity[] {
    return all.value
      .filter(s => s.type === 'entity' && s.data)
      .map(s => s.data as Entity)
  }

  /**
   * Obtiene las alertas seleccionadas
   */
  function getSelectedAlerts(): Alert[] {
    return all.value
      .filter(s => s.type === 'alert' && s.data)
      .map(s => s.data as Alert)
  }

  return {
    // Estado
    primary,
    secondary,
    textSelection,
    hovered,
    multiSelectMode,

    // Getters
    all,
    selectedEntityIds,
    selectedAlertIds,
    hasSelection,
    hasMultipleSelections,
    count,

    // Acciones
    select,
    selectEntity,
    selectAlert,
    addToSecondary,
    removeFromSecondary,
    toggle,
    isSelected,
    setTextSelection,
    setHovered,
    setMultiSelectMode,
    clearPrimary,
    clearAll,
    clearType,
    selectEntities,
    getSelectedEntities,
    getSelectedAlerts
  }
})
