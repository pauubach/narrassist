/**
 * Tests para StatusBar - lógica de progreso y estados de análisis
 *
 * Testea las funciones puras y la lógica de cálculo de progreso
 * sin montar el componente (evita dependencias de PrimeVue, Tauri, etc.)
 */


// ── Phase Progress Logic ─────────────────────────────────────
// Replica la lógica de calculatePhaseProgress y steps del StatusBar
// para testar sin montar el componente.

interface PhaseDefinition {
  id: string
  name: string
  range: [number, number]
}

const allPhases: PhaseDefinition[] = [
  { id: 'parsing', name: 'Lectura del documento', range: [0, 1] },
  { id: 'classification', name: 'Clasificando documento', range: [1, 2] },
  { id: 'structure', name: 'Identificando capítulos', range: [2, 3] },
  { id: 'ner', name: 'Buscando personajes y lugares', range: [3, 34] },
  { id: 'fusion', name: 'Unificando entidades', range: [34, 49] },
  { id: 'attributes', name: 'Analizando características', range: [49, 57] },
  { id: 'consistency', name: 'Verificando coherencia', range: [57, 60] },
  { id: 'grammar', name: 'Revisando gramática y ortografía', range: [60, 66] },
  { id: 'alerts', name: 'Preparando observaciones', range: [66, 70] },
  { id: 'relationships', name: 'Analizando relaciones', range: [70, 78] },
  { id: 'voice', name: 'Perfilando voces', range: [78, 86] },
  { id: 'prose', name: 'Evaluando escritura', range: [86, 94] },
  { id: 'health', name: 'Salud narrativa', range: [94, 100] },
]

function calculatePhaseProgress(phaseId: string, totalProgress: number): number {
  const phase = allPhases.find(p => p.id === phaseId)
  if (!phase) return 0
  const [start, end] = phase.range
  if (totalProgress < start) return 0
  if (totalProgress >= end) return 100
  return Math.round(((totalProgress - start) / (end - start)) * 100)
}

function calculateSteps(currentProgress: number) {
  return allPhases.map(phase => {
    const [start, end] = phase.range
    let status: 'completed' | 'in_progress' | 'pending'
    let phaseProgress = 0

    if (currentProgress >= end) {
      status = 'completed'
      phaseProgress = 100
    } else if (currentProgress >= start) {
      status = 'in_progress'
      phaseProgress = Math.round(((currentProgress - start) / (end - start)) * 100)
    } else {
      status = 'pending'
      phaseProgress = 0
    }

    return { id: phase.id, name: phase.name, status, progress: phaseProgress }
  })
}

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const stepLabels: Record<string, string> = {
  'parsing': 'Lectura del documento',
  'classification': 'Clasificando documento',
  'structure': 'Identificando capítulos',
  'ner': 'Buscando personajes y lugares',
  'fusion': 'Unificando entidades',
  'attributes': 'Analizando características',
  'consistency': 'Verificando coherencia',
  'grammar': 'Revisando gramática',
  'alerts': 'Preparando observaciones',
  'relationships': 'Analizando relaciones',
  'voice': 'Perfilando voces',
  'prose': 'Evaluando escritura',
  'health': 'Salud narrativa',
  'complete': 'Análisis completado',
}

// ── Tests ────────────────────────────────────────────────────

describe('StatusBar: calculatePhaseProgress', () => {
  it('should return 0 for progress before phase start', () => {
    expect(calculatePhaseProgress('ner', 2)).toBe(0) // ner starts at 3
  })

  it('should return 100 for progress at or after phase end', () => {
    expect(calculatePhaseProgress('ner', 34)).toBe(100)
    expect(calculatePhaseProgress('ner', 50)).toBe(100)
  })

  it('should calculate mid-phase progress correctly', () => {
    // NER: range [3, 34], span = 31
    // At progress 18.5: (18.5 - 3) / 31 = 0.5 = 50%
    expect(calculatePhaseProgress('ner', 18.5)).toBe(50)
  })

  it('should return 0 for unknown phase', () => {
    expect(calculatePhaseProgress('nonexistent', 50)).toBe(0)
  })

  it('should handle parsing phase (0-1 range)', () => {
    expect(calculatePhaseProgress('parsing', 0)).toBe(0)
    expect(calculatePhaseProgress('parsing', 0.5)).toBe(50)
    expect(calculatePhaseProgress('parsing', 1)).toBe(100)
  })

  it('should handle health phase (94-100 range)', () => {
    expect(calculatePhaseProgress('health', 93)).toBe(0)
    expect(calculatePhaseProgress('health', 97)).toBe(50)
    expect(calculatePhaseProgress('health', 100)).toBe(100)
  })
})

describe('StatusBar: calculateSteps', () => {
  it('should mark all phases as pending at 0%', () => {
    const steps = calculateSteps(0)
    // parsing starts at 0, so it's in_progress at 0%
    expect(steps[0].status).toBe('in_progress')
    expect(steps[1].status).toBe('pending')
    expect(steps[12].status).toBe('pending')
  })

  it('should mark all phases as completed at 100%', () => {
    const steps = calculateSteps(100)
    for (const step of steps) {
      expect(step.status).toBe('completed')
      expect(step.progress).toBe(100)
    }
  })

  it('should have exactly one in_progress phase for mid-progress', () => {
    const steps = calculateSteps(50)
    const inProgress = steps.filter(s => s.status === 'in_progress')
    expect(inProgress).toHaveLength(1)
    expect(inProgress[0].id).toBe('attributes') // range [49, 57]
  })

  it('should mark phases before current as completed', () => {
    const steps = calculateSteps(50)
    const completed = steps.filter(s => s.status === 'completed')
    // All phases with end <= 50 should be completed
    expect(completed.map(s => s.id)).toContain('parsing')
    expect(completed.map(s => s.id)).toContain('ner')
    expect(completed.map(s => s.id)).toContain('fusion')
  })

  it('should mark phases after current as pending', () => {
    const steps = calculateSteps(50)
    const pending = steps.filter(s => s.status === 'pending')
    expect(pending.map(s => s.id)).toContain('grammar')
    expect(pending.map(s => s.id)).toContain('health')
  })

  it('should return 13 phases total', () => {
    const steps = calculateSteps(0)
    expect(steps).toHaveLength(13)
  })

  it('should have contiguous ranges (no gaps)', () => {
    for (let i = 1; i < allPhases.length; i++) {
      expect(allPhases[i].range[0]).toBe(allPhases[i - 1].range[1])
    }
  })

  it('should cover 0 to 100 range', () => {
    expect(allPhases[0].range[0]).toBe(0)
    expect(allPhases[allPhases.length - 1].range[1]).toBe(100)
  })
})

describe('StatusBar: formatNumber', () => {
  it('should format small numbers as-is', () => {
    expect(formatNumber(0)).toBe('0')
    expect(formatNumber(42)).toBe('42')
    expect(formatNumber(999)).toBe('999')
  })

  it('should format thousands with k suffix', () => {
    expect(formatNumber(1000)).toBe('1.0k')
    expect(formatNumber(1500)).toBe('1.5k')
    expect(formatNumber(50000)).toBe('50.0k')
    expect(formatNumber(123456)).toBe('123.5k')
  })
})

describe('StatusBar: stepLabels', () => {
  it('should have labels for all phases', () => {
    for (const phase of allPhases) {
      expect(stepLabels[phase.id]).toBeDefined()
      expect(stepLabels[phase.id].length).toBeGreaterThan(0)
    }
  })

  it('should have a "complete" label', () => {
    expect(stepLabels['complete']).toBe('Análisis completado')
  })

  it('should map known steps to Spanish labels', () => {
    expect(stepLabels['ner']).toBe('Buscando personajes y lugares')
    expect(stepLabels['grammar']).toBe('Revisando gramática')
    expect(stepLabels['health']).toBe('Salud narrativa')
  })
})

describe('StatusBar: analysisStatus logic', () => {
  // Pure function version of the computed
  function getAnalysisStatus(opts: {
    isAnalyzing: boolean
    status?: string
    error?: string | null
    analysisError?: boolean
    hasAnalysis?: boolean
  }) {
    if (opts.isAnalyzing) return null

    if (opts.status === 'queued_for_heavy') {
      return { icon: 'pi-clock', text: 'Estructura lista — en cola para análisis profundo', class: 'status-queued-heavy' }
    }
    if (opts.status === 'queued') {
      return { icon: 'pi-clock', text: 'En cola — esperando análisis anterior', class: 'status-queued' }
    }
    if (opts.error || opts.analysisError) {
      const detail = opts.error ? `Error en análisis: ${opts.error}` : 'Error en análisis'
      return { icon: 'pi-times-circle', text: detail, class: 'status-error' }
    }
    if (opts.hasAnalysis) {
      return { icon: 'pi-check-circle', text: 'Análisis completado', class: 'status-completed' }
    }
    return { icon: 'pi-circle', text: 'Sin analizar', class: 'status-pending' }
  }

  it('should return null when analyzing', () => {
    expect(getAnalysisStatus({ isAnalyzing: true })).toBeNull()
  })

  it('should show queued_for_heavy status', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, status: 'queued_for_heavy' })
    expect(result?.class).toBe('status-queued-heavy')
    expect(result?.text).toContain('en cola para análisis profundo')
  })

  it('should show queued status', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, status: 'queued' })
    expect(result?.class).toBe('status-queued')
    expect(result?.text).toContain('En cola')
  })

  it('should show error from store', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, error: 'OOM error' })
    expect(result?.class).toBe('status-error')
    expect(result?.text).toContain('OOM error')
  })

  it('should show generic error from prop', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, analysisError: true })
    expect(result?.class).toBe('status-error')
    expect(result?.text).toBe('Error en análisis')
  })

  it('should show completed when has analysis', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, hasAnalysis: true })
    expect(result?.class).toBe('status-completed')
    expect(result?.text).toBe('Análisis completado')
  })

  it('should show pending when nothing', () => {
    const result = getAnalysisStatus({ isAnalyzing: false })
    expect(result?.class).toBe('status-pending')
    expect(result?.text).toBe('Sin analizar')
  })

  it('should prioritize queued over completed', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, status: 'queued', hasAnalysis: true })
    expect(result?.class).toBe('status-queued')
  })

  it('should prioritize error over completed', () => {
    const result = getAnalysisStatus({ isAnalyzing: false, error: 'fail', hasAnalysis: true })
    expect(result?.class).toBe('status-error')
  })
})
