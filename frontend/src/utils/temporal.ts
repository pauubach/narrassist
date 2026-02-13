/**
 * Formatea un temporal_instance_id a texto legible para UI.
 *
 * Formatos soportados:
 *   "1@age:40"           → "@40 años"
 *   "1@year:1985"        → "@1985"
 *   "1@phase:young"      → "@joven"
 *   "1@offset_years:+5"  → "@+5 años"
 *   "1@offset_years:-3"  → "@-3 años"
 *   otro                 → raw instanceId
 */

const PHASE_LABELS: Record<string, string> = {
  child: 'niño/a',
  teen: 'adolescente',
  young: 'joven',
  adult: 'adulto/a',
  elder: 'mayor',
  future_self: 'yo futuro',
  past_self: 'yo pasado',
}

export function formatTemporalInstance(instanceId: string): string {
  const ageMatch = instanceId.match(/@age:(\d{1,3})$/)
  if (ageMatch) return `@${ageMatch[1]} años`

  const yearMatch = instanceId.match(/@year:(\d{4})$/)
  if (yearMatch) return `@${yearMatch[1]}`

  const phaseMatch = instanceId.match(/@phase:(\w+)$/)
  if (phaseMatch) return `@${PHASE_LABELS[phaseMatch[1]] || phaseMatch[1]}`

  const offsetMatch = instanceId.match(/@offset_years:([+-]?\d{1,3})$/)
  if (offsetMatch) return `@${offsetMatch[1]} años`

  return instanceId
}
