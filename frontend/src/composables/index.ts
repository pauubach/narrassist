/**
 * Composables del sistema
 *
 * Funciones reactivas reutilizables para lógica de negocio.
 */

export { useEntityUtils } from './useEntityUtils'
export type { EntityTypeConfig, EntityImportanceConfig } from './useEntityUtils'

export { useAlertUtils } from './useAlertUtils'
export type { SeverityConfig, CategoryConfig, StatusConfig } from './useAlertUtils'

export {
  useHighlight,
  useGlobalHighlight,
  resetGlobalHighlight,
  HIGHLIGHT_FLASH_CLASS
} from './useHighlight'
export type { HighlightSpan, HighlightOptions, FlashState } from './useHighlight'

export { useAnalysisStream } from './useAnalysisStream'
export type { AnalysisProgress, AnalysisPhase, UseAnalysisStreamOptions } from './useAnalysisStream'

export { useNavigation } from './useNavigation'
export type { NavigationTarget, TooltipData, HighlightState } from './useNavigation'

export {
  debounce,
  throttle,
  useDebouncedRef,
  useScrollDetection
} from './usePerformance'

export { useNativeMenu } from './useNativeMenu'

export { useNotifications } from './useNotifications'
export type { NotificationSeverity, NotificationOptions } from './useNotifications'

export { useMentionNavigation } from './useMentionNavigation'
export type { Mention, MentionNavigationState } from './useMentionNavigation'

export { useDocumentTypeConfig } from './useDocumentTypeConfig'
export type { DocumentTypeUIConfig } from './useDocumentTypeConfig'

export { useAttributeLabels, getAttributeLabel } from './useAttributeLabels'
