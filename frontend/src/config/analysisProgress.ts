export interface PhaseDefinition {
  id: string
  name: string
  range: [number, number]
}

// Fallback progress ranges aligned with backend PHASE_WEIGHTS.
// Order must match backend PHASE_ORDER exactly.
export const STATUSBAR_PHASES: PhaseDefinition[] = [
  { id: 'parsing', name: 'Lectura del documento', range: [0, 1] },
  { id: 'classification', name: 'Clasificando documento', range: [1, 2] },
  { id: 'structure', name: 'Identificando capítulos', range: [2, 3] },
  { id: 'ner', name: 'Buscando personajes y lugares', range: [3, 24] },
  { id: 'fusion', name: 'Unificando entidades', range: [24, 49] },
  { id: 'timeline', name: 'Construyendo línea temporal', range: [49, 53] },
  { id: 'attributes', name: 'Analizando características', range: [53, 60] },
  { id: 'consistency', name: 'Verificando coherencia', range: [60, 63] },
  { id: 'grammar', name: 'Revisando gramática', range: [63, 69] },
  { id: 'alerts', name: 'Preparando observaciones', range: [69, 72] },
  { id: 'relationships', name: 'Analizando relaciones', range: [72, 80] },
  { id: 'voice', name: 'Perfilando voces', range: [80, 87] },
  { id: 'prose', name: 'Evaluando escritura', range: [87, 94] },
  { id: 'health', name: 'Salud narrativa', range: [94, 100] },
]

export const STATUSBAR_STEP_LABELS: Record<string, string> = {
  parsing: 'Lectura del documento',
  classification: 'Clasificando documento',
  structure: 'Identificando capítulos',
  ner: 'Buscando personajes y lugares',
  fusion: 'Unificando entidades',
  timeline: 'Construyendo línea temporal',
  attributes: 'Analizando características',
  consistency: 'Verificando coherencia',
  grammar: 'Revisando gramática',
  alerts: 'Preparando observaciones',
  relationships: 'Analizando relaciones',
  voice: 'Perfilando voces',
  prose: 'Evaluando escritura',
  health: 'Salud narrativa',
  complete: 'Análisis completado',
}

export function calculateStatusBarPhaseProgress(phaseId: string, totalProgress: number): number {
  const phase = STATUSBAR_PHASES.find(p => p.id === phaseId)
  if (!phase) return 0
  const [start, end] = phase.range
  if (totalProgress < start) return 0
  if (totalProgress >= end) return 100
  return Math.round(((totalProgress - start) / (end - start)) * 100)
}
