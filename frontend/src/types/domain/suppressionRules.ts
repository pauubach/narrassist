export type SuppressionRuleType = 'alert_type' | 'category' | 'entity' | 'source_module'

export interface SuppressionRule {
  id: number
  projectId: number
  ruleType: SuppressionRuleType
  pattern: string
  entityName: string | null
  reason: string | null
  isActive: boolean
  createdAt: Date | null
}
