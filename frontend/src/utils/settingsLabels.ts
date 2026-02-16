/**
 * Pure label/severity mapper functions for SettingsView.
 *
 * Extracted from SettingsView.vue to reduce component size.
 * All functions are stateless — they map value → display string.
 */

export function getFieldLabel(field: string | undefined): string {
  const labels: Record<string, string> = {
    general: 'General',
    literary: 'Literario',
    journalistic: 'Periodistico',
    academic: 'Academico',
    technical: 'Tecnico',
    legal: 'Juridico',
    medical: 'Medico',
    business: 'Empresarial',
    selfhelp: 'Autoayuda',
    culinary: 'Gastronomia',
  }
  return labels[field || 'general'] || field || 'General'
}

export function getRegisterLabel(register: string | undefined): string {
  const labels: Record<string, string> = {
    formal: 'Formal',
    formal_literary: 'Formal / Literario',
    neutral: 'Neutro',
    colloquial: 'Coloquial',
    vulgar: 'Vulgar',
    technical: 'Técnico',
    literary: 'Literario',
    poetic: 'Poético',
  }
  return labels[register || 'neutral'] || register || 'Neutro'
}

export function getAudienceLabel(audience: string | undefined): string {
  const labels: Record<string, string> = {
    general: 'Publico general',
    children: 'Infantil/Juvenil',
    adult: 'Adultos',
    specialist: 'Especialistas',
    mixed: 'Mixta',
  }
  return labels[audience || 'general'] || audience || 'General'
}

export function getDashLabel(dash: string | undefined): string {
  const labels: Record<string, string> = {
    em: 'Raya (--)',
    en: 'Semiraya (-)',
    hyphen: 'Guion (-)',
  }
  return labels[dash || 'em'] || dash || 'Raya'
}

export function getQuoteLabel(quote: string | undefined): string {
  const labels: Record<string, string> = {
    angular: 'Angulares \u00AB\u00BB',
    curly: 'Inglesas tipogr\u00E1ficas \u201C\u201D',
    straight: 'Rectas ""',
  }
  return labels[quote || 'angular'] || quote || 'Angulares'
}

export function getSensitivityLabel(sensitivity: string | undefined): string {
  const labels: Record<string, string> = {
    low: 'Baja',
    medium: 'Media',
    high: 'Alta',
  }
  return labels[sensitivity || 'medium'] || sensitivity || 'Media'
}

export type PrimeSeverity = 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast'

export function getSensitivitySeverity(sensitivity: string | undefined): PrimeSeverity {
  const severities: Record<string, PrimeSeverity> = {
    low: 'success',
    medium: 'info',
    high: 'warn',
  }
  return severities[sensitivity || 'medium'] || 'info'
}

export function getRegionLabel(region: string | undefined): string {
  const labels: Record<string, string> = {
    es_ES: 'Espana',
    es_MX: 'Mexico',
    es_AR: 'Argentina',
    es_CO: 'Colombia',
    es_CL: 'Chile',
    es_PE: 'Peru',
  }
  return labels[region || 'es_ES'] || region || 'Espana'
}

export function getSpeedLabel(speed: string): string {
  const labels: Record<string, string> = {
    instant: 'Instant\u00E1neo',
    fast: 'R\u00E1pido',
    medium: 'Media',
    slow: 'Lenta',
  }
  return labels[speed] || speed
}

export function getSpeedSeverity(speed: string): PrimeSeverity {
  const severities: Record<string, PrimeSeverity> = {
    instant: 'success',
    fast: 'success',
    medium: 'warn',
    slow: 'danger',
  }
  return severities[speed] || 'info'
}
