import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'
import { useDocumentTypeConfig } from '../useDocumentTypeConfig'
import type { DocumentType, RecommendedAnalysis } from '@/types/domain/projects'

describe('useDocumentTypeConfig', () => {
  describe('config por tipo de documento', () => {
    it('devuelve configuración de ficción por defecto', () => {
      const documentType = ref<DocumentType>('fiction')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Ficción')
      expect(config.value.tabs.timeline).toBe(true)
      expect(config.value.tabs.relations).toBe(true)
      expect(config.value.tabLabels.entities).toBe('Entidades')
    })

    it('oculta timeline y relaciones para autoayuda', () => {
      const documentType = ref<DocumentType>('self_help')
      const { config, isTabVisible } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Autoayuda')
      expect(config.value.tabs.timeline).toBe(false)
      expect(config.value.tabs.relations).toBe(false)
      expect(isTabVisible('timeline')).toBe(false)
      expect(isTabVisible('relations')).toBe(false)
      expect(config.value.tabLabels.entities).toBe('Conceptos')
    })

    it('configura correctamente ensayo', () => {
      const documentType = ref<DocumentType>('essay')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Ensayo')
      expect(config.value.tabs.timeline).toBe(false)
      expect(config.value.tabs.relations).toBe(false)
      expect(config.value.analysis.conceptTracking).toBe(true)
    })

    it('configura correctamente memorias', () => {
      const documentType = ref<DocumentType>('memoir')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Memorias')
      expect(config.value.tabs.timeline).toBe(true)
      expect(config.value.tabs.relations).toBe(true)
      expect(config.value.tabLabels.entities).toBe('Personas')
      expect(config.value.tabLabels.timeline).toBe('Cronología')
    })

    it('configura correctamente técnico', () => {
      const documentType = ref<DocumentType>('technical')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Técnico')
      expect(config.value.tabs.style).toBe(false)
      expect(config.value.tabLabels.entities).toBe('Términos')
    })

    it('configura correctamente recetario', () => {
      const documentType = ref<DocumentType>('cookbook')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Recetario')
      expect(config.value.tabLabels.text).toBe('Recetas')
      expect(config.value.tabLabels.entities).toBe('Ingredientes')
    })

    it('devuelve configuración completa para unknown', () => {
      const documentType = ref<DocumentType>('unknown')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Documento')
      expect(config.value.tabs.timeline).toBe(true)
      expect(config.value.tabs.relations).toBe(true)
      expect(config.value.tabs.style).toBe(true)
    })
  })

  describe('visibleTabs', () => {
    it('devuelve solo tabs visibles para ficción', () => {
      const documentType = ref<DocumentType>('fiction')
      const { visibleTabs } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(visibleTabs.value).toContain('text')
      expect(visibleTabs.value).toContain('entities')
      expect(visibleTabs.value).toContain('relations')
      expect(visibleTabs.value).toContain('timeline')
      expect(visibleTabs.value).toContain('alerts')
      expect(visibleTabs.value).toContain('style')
    })

    it('devuelve solo tabs visibles para autoayuda', () => {
      const documentType = ref<DocumentType>('self_help')
      const { visibleTabs } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(visibleTabs.value).toContain('text')
      expect(visibleTabs.value).toContain('entities')
      expect(visibleTabs.value).not.toContain('relations')
      expect(visibleTabs.value).not.toContain('timeline')
      expect(visibleTabs.value).toContain('alerts')
      expect(visibleTabs.value).toContain('style')
    })
  })

  describe('getTabLabel', () => {
    it('devuelve labels personalizados según tipo', () => {
      const documentType = ref<DocumentType>('cookbook')
      const { getTabLabel } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(getTabLabel('text')).toBe('Recetas')
      expect(getTabLabel('entities')).toBe('Ingredientes')
    })

    it('devuelve el key si no hay label definido', () => {
      const documentType = ref<DocumentType>('fiction')
      const { getTabLabel } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(getTabLabel('unknown_tab')).toBe('unknown_tab')
    })
  })

  describe('isAnalysisEnabled', () => {
    it('devuelve true para análisis habilitados en ficción', () => {
      const documentType = ref<DocumentType>('fiction')
      const { isAnalysisEnabled } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(isAnalysisEnabled('temporal')).toBe(true)
      expect(isAnalysisEnabled('relationships')).toBe(true)
      expect(isAnalysisEnabled('behaviorConsistency')).toBe(true)
    })

    it('devuelve false para análisis deshabilitados en autoayuda', () => {
      const documentType = ref<DocumentType>('self_help')
      const { isAnalysisEnabled } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(isAnalysisEnabled('temporal')).toBe(false)
      expect(isAnalysisEnabled('relationships')).toBe(false)
      expect(isAnalysisEnabled('conceptTracking')).toBe(true)
    })
  })

  describe('override con recommendedAnalysis', () => {
    it('sobrescribe configuración con recommendedAnalysis del backend', () => {
      const documentType = ref<DocumentType>('fiction')
      const recommendedAnalysis = ref<RecommendedAnalysis>({
        entity_detection: {
          focus: 'characters',
          detect_implicit: true,
          min_mentions_for_entity: 2
        },
        semantic_fusion: {
          threshold: 0.85,
          allow_cross_type: false
        },
        analysis: {
          temporal_analysis: false, // Override: desactivar timeline
          relationship_detection: false, // Override: desactivar relaciones
          behavior_consistency: true,
          dialog_analysis: true
        },
        alerts: {}
      })

      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value),
        computed(() => recommendedAnalysis.value)
      )

      // Los overrides del backend deben aplicarse
      expect(config.value.tabs.timeline).toBe(false)
      expect(config.value.tabs.relations).toBe(false)
      expect(config.value.analysis.temporal).toBe(false)
      expect(config.value.analysis.relationships).toBe(false)
    })
  })

  describe('reactividad', () => {
    it('actualiza config cuando cambia el tipo de documento', () => {
      const documentType = ref<DocumentType>('fiction')
      const { config } = useDocumentTypeConfig(
        computed(() => documentType.value)
      )

      expect(config.value.typeLabel).toBe('Ficción')
      expect(config.value.tabs.timeline).toBe(true)

      // Cambiar tipo
      documentType.value = 'self_help'

      expect(config.value.typeLabel).toBe('Autoayuda')
      expect(config.value.tabs.timeline).toBe(false)
    })
  })
})
