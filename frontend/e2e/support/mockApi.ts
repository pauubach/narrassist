import type { Page, Route } from '@playwright/test'

type ApiAlertSeverity = 'critical' | 'warning' | 'info' | 'hint'
type ApiAlertStatus = 'new' | 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'dismissed' | 'auto_resolved'

interface ApiProject {
  id: number
  name: string
  description: string | null
  document_path: string | null
  document_format: string
  created_at: string
  last_modified: string
  last_opened: string
  analysis_status: 'pending' | 'in_progress' | 'analyzing' | 'queued' | 'completed' | 'error' | 'failed'
  analysis_progress: number
  word_count: number
  chapter_count: number
  entity_count: number
  open_alerts_count: number
  highest_alert_severity: ApiAlertSeverity | null
  document_type: 'fiction' | 'essay' | 'self_help' | 'technical' | 'memoir' | 'cookbook' | 'academic' | 'unknown'
  recommended_analysis: {
    entity_detection: {
      focus: string
      detect_implicit: boolean
      min_mentions_for_entity: number
    }
    semantic_fusion: {
      threshold: number
      allow_cross_type: boolean
    }
    analysis: Record<string, boolean>
    alerts: Record<string, boolean>
  }
}

interface ApiEntity {
  id: number
  project_id: number
  entity_type: string
  canonical_name: string
  aliases: string[]
  importance: string
  description: string | null
  first_appearance_char: number | null
  first_mention_chapter: number | null
  mention_count: number
  is_active: boolean
  merged_from_ids: number[]
  relevance_score: number
  created_at: string
  updated_at: string
}

interface ApiAlert {
  id: number
  project_id: number
  category: string
  severity: ApiAlertSeverity
  alert_type: string
  title: string
  description: string
  explanation: string
  suggestion: string | null
  chapter: number | null
  start_char: number | null
  end_char: number | null
  excerpt: string | null
  status: ApiAlertStatus
  entity_ids: number[]
  confidence: number
  created_at: string
  resolved_at: string | null
  extra_data?: Record<string, unknown>
}

interface ApiChapter {
  id: number
  project_id: number
  title: string
  content: string
  chapter_number: number
  word_count: number
  position_start: number
  position_end: number
  structure_type: string | null
  created_at: string
  updated_at: string
}

interface AnalysisProgressPayload {
  project_id: number
  status: 'pending' | 'running' | 'queued' | 'queued_for_heavy' | 'completed' | 'failed' | 'error' | 'idle' | 'cancelled'
  progress: number
  current_phase: string
  phases: Array<{ id: string; name: string; completed: boolean; current: boolean }>
  metrics?: { chapters_found?: number; entities_found?: number; word_count?: number; alerts_generated?: number }
  error?: string
}

interface LicenseStatusPayload {
  status: 'no_license' | 'active' | 'expired' | 'grace_period' | 'suspended'
  tier: 'corrector' | 'profesional' | 'editorial' | null
  features: string[]
  devices_used: number
  devices_max: number
  pages_used: number
  pages_max: number
  pages_remaining: number | null
  unlimited: boolean
  expires_at: string | null
  is_trial: boolean
  offline_days_remaining: number | null
}

export interface MockApiState {
  projects: ApiProject[]
  entitiesByProject: Record<number, ApiEntity[]>
  alertsByProject: Record<number, ApiAlert[]>
  chaptersByProject: Record<number, ApiChapter[]>
  relationshipsByProject: Record<number, any>
  attributesByEntity: Record<number, Array<{
    id: number
    entity_id: number
    category: string
    name: string
    value: string
    chapter: string | null
    confidence: number
    span_start: number | null
    span_end: number | null
    chapter_id: number | null
    source_mention_id: number | null
  }>>
  progressByProject: Record<number, AnalysisProgressPayload>
  executedPhasesByProject: Record<number, Record<string, boolean>>
  failProjectsRemaining: number
  lastProjectId: number
}

export interface MockApiOptions {
  projectCount?: number
  failProjectsOnce?: boolean
  chatFailureTrigger?: string
  forceChatFailure?: boolean
  executedPhasesOverride?: Record<number, Record<string, boolean>>
}

const nowIso = () => new Date().toISOString()

const daysAgoIso = (days: number) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

const wrap = <T>(data: T) => ({ success: true, data })

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

function parseJsonBody<T>(route: Route): T | null {
  try {
    return route.request().postDataJSON() as T
  } catch {
    return null
  }
}

function countOpenAlerts(alerts: ApiAlert[]): number {
  const openStatuses: ApiAlertStatus[] = ['new', 'open', 'acknowledged', 'in_progress']
  return alerts.filter(a => openStatuses.includes(a.status)).length
}

function maxSeverity(alerts: ApiAlert[]): ApiAlertSeverity | null {
  const openStatuses: ApiAlertStatus[] = ['new', 'open', 'acknowledged', 'in_progress']
  const open = alerts.filter(a => openStatuses.includes(a.status))
  if (open.length === 0) return null

  const rank: Record<ApiAlertSeverity, number> = {
    critical: 4,
    warning: 3,
    info: 2,
    hint: 1,
  }

  return open.reduce((max, current) => (rank[current.severity] > rank[max] ? current.severity : max), open[0].severity)
}

function updateProjectAlertCounters(state: MockApiState, projectId: number) {
  const project = state.projects.find(p => p.id === projectId)
  if (!project) return
  const alerts = state.alertsByProject[projectId] || []
  project.open_alerts_count = countOpenAlerts(alerts)
  project.highest_alert_severity = maxSeverity(alerts)
}

function defaultExecutedPhases(): Record<string, boolean> {
  return {
    parsing: true,
    structure: true,
    entities: true,
    coreference: true,
    attributes: true,
    relationships: true,
    interactions: false,
    spelling: true,
    grammar: true,
    register: true,
    pacing: true,
    coherence: true,
    alerts: true,
    temporal: true,
    emotional: false,
    sentiment: false,
    focalization: false,
    voice_profiles: true,
  }
}

function buildProject(id: number, name: string, overrides: Partial<ApiProject> = {}): ApiProject {
  return {
    id,
    name,
    description: `Descripción de ${name}`,
    document_path: `C:/mock/${id}.txt`,
    document_format: 'TXT',
    created_at: daysAgoIso(20 + id),
    last_modified: daysAgoIso(id),
    last_opened: nowIso(),
    analysis_status: 'completed',
    analysis_progress: 100,
    word_count: 9000 + id * 500,
    chapter_count: 3,
    entity_count: 3,
    open_alerts_count: 0,
    highest_alert_severity: null,
    document_type: 'fiction',
    recommended_analysis: {
      entity_detection: {
        focus: 'characters_and_locations',
        detect_implicit: true,
        min_mentions_for_entity: 2,
      },
      semantic_fusion: {
        threshold: 0.85,
        allow_cross_type: false,
      },
      analysis: {
        temporal_analysis: true,
        relationship_detection: true,
        behavior_consistency: true,
        dialog_analysis: true,
        concept_tracking: true,
      },
      alerts: {
        consistency: true,
        grammar: true,
        style: true,
      },
    },
    ...overrides,
  }
}

function createMockState(options: MockApiOptions = {}): MockApiState {
  const projects: ApiProject[] = [
    buildProject(1, 'Proyecto E2E Principal', {
      word_count: 12480,
      chapter_count: 3,
      entity_count: 3,
      analysis_status: 'completed',
      analysis_progress: 100,
    }),
    buildProject(2, 'Proyecto E2E Secundario', {
      word_count: 6400,
      chapter_count: 2,
      entity_count: 2,
      analysis_status: 'completed',
      analysis_progress: 100,
    }),
  ]

  const desiredCount = Math.max(2, options.projectCount ?? 2)
  for (let id = 3; id <= desiredCount; id++) {
    projects.push(buildProject(id, `Proyecto Carga ${id.toString().padStart(3, '0')}`))
  }

  const chaptersByProject: MockApiState['chaptersByProject'] = {
    1: [
      {
        id: 101,
        project_id: 1,
        title: 'Capítulo 1',
        content: 'Juan Pérez llegó a Madrid al amanecer. Ana lo esperaba en la estación.',
        chapter_number: 1,
        word_count: 4200,
        position_start: 0,
        position_end: 4200,
        structure_type: 'chapter',
        created_at: daysAgoIso(20),
        updated_at: daysAgoIso(1),
      },
      {
        id: 102,
        project_id: 1,
        title: 'Capítulo 2',
        content: 'Ana dudó sobre la edad de Juan en su informe, creando una inconsistencia.',
        chapter_number: 2,
        word_count: 3950,
        position_start: 4201,
        position_end: 8151,
        structure_type: 'chapter',
        created_at: daysAgoIso(19),
        updated_at: daysAgoIso(1),
      },
      {
        id: 103,
        project_id: 1,
        title: 'Capítulo 3',
        content: 'El equipo revisó las alertas y dejó el manuscrito listo para la edición.',
        chapter_number: 3,
        word_count: 4330,
        position_start: 8152,
        position_end: 12480,
        structure_type: 'chapter',
        created_at: daysAgoIso(18),
        updated_at: nowIso(),
      },
    ],
    2: [
      {
        id: 201,
        project_id: 2,
        title: 'Capítulo 1',
        content: 'Texto base del proyecto secundario.',
        chapter_number: 1,
        word_count: 3200,
        position_start: 0,
        position_end: 3200,
        structure_type: 'chapter',
        created_at: daysAgoIso(15),
        updated_at: daysAgoIso(2),
      },
      {
        id: 202,
        project_id: 2,
        title: 'Capítulo 2',
        content: 'Segundo capítulo con menos densidad de entidades.',
        chapter_number: 2,
        word_count: 3200,
        position_start: 3201,
        position_end: 6400,
        structure_type: 'chapter',
        created_at: daysAgoIso(14),
        updated_at: daysAgoIso(2),
      },
    ],
  }

  for (let id = 3; id <= desiredCount; id++) {
    chaptersByProject[id] = [
      {
        id: id * 100 + 1,
        project_id: id,
        title: 'Capítulo 1',
        content: `Contenido simulado del proyecto ${id}.`,
        chapter_number: 1,
        word_count: 2500,
        position_start: 0,
        position_end: 2500,
        structure_type: 'chapter',
        created_at: daysAgoIso(8),
        updated_at: daysAgoIso(1),
      },
    ]
  }

  const entitiesByProject: MockApiState['entitiesByProject'] = {
    1: [
      {
        id: 11,
        project_id: 1,
        entity_type: 'character',
        canonical_name: 'Juan Pérez',
        aliases: ['Juan'],
        importance: 'principal',
        description: 'Protagonista de la historia',
        first_appearance_char: 15,
        first_mention_chapter: 1,
        mention_count: 17,
        is_active: true,
        merged_from_ids: [],
        relevance_score: 0.98,
        created_at: daysAgoIso(20),
        updated_at: nowIso(),
      },
      {
        id: 12,
        project_id: 1,
        entity_type: 'character',
        canonical_name: 'Ana Robles',
        aliases: ['Ana'],
        importance: 'high',
        description: 'Co-protagonista',
        first_appearance_char: 47,
        first_mention_chapter: 1,
        mention_count: 13,
        is_active: true,
        merged_from_ids: [],
        relevance_score: 0.91,
        created_at: daysAgoIso(20),
        updated_at: nowIso(),
      },
      {
        id: 13,
        project_id: 1,
        entity_type: 'location',
        canonical_name: 'Madrid',
        aliases: ['la capital'],
        importance: 'medium',
        description: 'Localización principal',
        first_appearance_char: 28,
        first_mention_chapter: 1,
        mention_count: 7,
        is_active: true,
        merged_from_ids: [],
        relevance_score: 0.68,
        created_at: daysAgoIso(20),
        updated_at: nowIso(),
      },
    ],
    2: [
      {
        id: 21,
        project_id: 2,
        entity_type: 'character',
        canonical_name: 'Lucía',
        aliases: [],
        importance: 'principal',
        description: null,
        first_appearance_char: 10,
        first_mention_chapter: 1,
        mention_count: 8,
        is_active: true,
        merged_from_ids: [],
        relevance_score: 0.87,
        created_at: daysAgoIso(15),
        updated_at: daysAgoIso(1),
      },
    ],
  }

  for (let id = 3; id <= desiredCount; id++) {
    entitiesByProject[id] = []
  }

  const alertsByProject: MockApiState['alertsByProject'] = {
    1: [
      {
        id: 1011,
        project_id: 1,
        category: 'consistency',
        severity: 'warning',
        alert_type: 'attribute_inconsistency',
        title: 'Edad inconsistente de Juan',
        description: 'Juan aparece con 31 y 34 años en capítulos distintos.',
        explanation: 'Se detectaron dos valores de edad incompatibles.',
        suggestion: 'Unifica la edad de Juan en todo el manuscrito.',
        chapter: 2,
        start_char: 230,
        end_char: 265,
        excerpt: 'Juan tenía 34 años cuando...',
        status: 'open',
        entity_ids: [11],
        confidence: 0.93,
        created_at: daysAgoIso(2),
        resolved_at: null,
        extra_data: {
          entity_name: 'Juan Pérez',
          attribute_key: 'edad',
          value1: '31',
          value2: '34',
          sources: [
            {
              chapter: 1,
              start_char: 180,
              end_char: 196,
              excerpt: 'Juan, de 31 años...',
              value: '31',
            },
            {
              chapter: 2,
              start_char: 230,
              end_char: 248,
              excerpt: 'Juan tenía 34 años...',
              value: '34',
            },
          ],
        },
      },
      {
        id: 1012,
        project_id: 1,
        category: 'grammar',
        severity: 'info',
        alert_type: 'grammar_issue',
        title: 'Concordancia verbal mejorable',
        description: 'Se detectó una forma verbal ambigua en capítulo 3.',
        explanation: 'Posible problema de concordancia sujeto-verbo.',
        suggestion: 'Revisa la frase para mejorar claridad.',
        chapter: 3,
        start_char: 80,
        end_char: 102,
        excerpt: 'el equipo revisó y dejó',
        status: 'open',
        entity_ids: [],
        confidence: 0.81,
        created_at: daysAgoIso(1),
        resolved_at: null,
      },
    ],
    2: [],
  }

  for (let id = 3; id <= desiredCount; id++) {
    alertsByProject[id] = []
  }

  const relationshipsByProject: MockApiState['relationshipsByProject'] = {
    1: {
      entities: [
        { id: 11, name: 'Juan Pérez', type: 'CHARACTER', importance: 'critical', mentionCount: 17 },
        { id: 12, name: 'Ana Robles', type: 'CHARACTER', importance: 'high', mentionCount: 13 },
        { id: 13, name: 'Madrid', type: 'LOCATION', importance: 'medium', mentionCount: 7 },
      ],
      relations: [
        {
          source_id: 11,
          target_id: 12,
          strength: 0.8,
          valence: 'positive',
          confidence: 0.89,
          relation_type: 'friendship',
          confirmed: true,
        },
        {
          source_id: 11,
          target_id: 13,
          strength: 0.55,
          valence: 'neutral',
          confidence: 0.72,
          relation_type: 'located_in',
          confirmed: true,
        },
      ],
      mentions: [
        {
          id: 1,
          source_id: 11,
          target_id: 12,
          context: 'Juan y Ana prepararon la revisión.',
          mention_type: 'cooccurrence',
        },
      ],
      clusters: [],
    },
    2: { entities: [], relations: [], mentions: [], clusters: [] },
  }

  for (let id = 3; id <= desiredCount; id++) {
    relationshipsByProject[id] = { entities: [], relations: [], mentions: [], clusters: [] }
  }

  const attributesByEntity: MockApiState['attributesByEntity'] = {
    11: [
      {
        id: 5001,
        entity_id: 11,
        category: 'physical',
        name: 'edad',
        value: '31',
        chapter: '1',
        confidence: 0.92,
        span_start: 180,
        span_end: 196,
        chapter_id: 101,
        source_mention_id: null,
      },
    ],
    12: [],
    13: [],
    21: [],
  }

  const progressByProject: MockApiState['progressByProject'] = {}
  for (const project of projects) {
    progressByProject[project.id] = {
      project_id: project.id,
      status: 'idle',
      progress: 100,
      current_phase: 'Completado',
      phases: [
        { id: 'parsing', name: 'Análisis inicial', completed: true, current: false },
        { id: 'ner', name: 'Extracción de entidades', completed: true, current: false },
        { id: 'alerts', name: 'Generación de alertas', completed: true, current: false },
      ],
      metrics: {
        chapters_found: project.chapter_count,
        entities_found: project.entity_count,
        word_count: project.word_count,
        alerts_generated: countOpenAlerts(alertsByProject[project.id] || []),
      },
    }
  }

  const executedPhasesByProject: MockApiState['executedPhasesByProject'] = {}
  for (const project of projects) {
    executedPhasesByProject[project.id] = defaultExecutedPhases()
  }

  if (options.executedPhasesOverride) {
    for (const [projectId, phaseMap] of Object.entries(options.executedPhasesOverride)) {
      const id = Number(projectId)
      executedPhasesByProject[id] = {
        ...executedPhasesByProject[id],
        ...phaseMap,
      }
    }
  }

  const state: MockApiState = {
    projects,
    entitiesByProject,
    alertsByProject,
    chaptersByProject,
    relationshipsByProject,
    attributesByEntity,
    progressByProject,
    executedPhasesByProject,
    failProjectsRemaining: options.failProjectsOnce ? 1 : 0,
    lastProjectId: projects[projects.length - 1].id,
  }

  for (const project of state.projects) {
    updateProjectAlertCounters(state, project.id)
  }

  return state
}

function mockModelsStatus(ollama: { installed: boolean; models: string[] }) {
  return {
    nlp_models: {
      spacy: { type: 'spacy', installed: true, display_name: 'SpaCy', size_mb: 540 },
      embeddings: { type: 'embeddings', installed: true, display_name: 'Embeddings', size_mb: 470 },
      transformer_ner: { type: 'transformer_ner', installed: true, display_name: 'NER', size_mb: 500 },
    },
    ollama: {
      installed: ollama.installed,
      models: ollama.models,
    },
    all_required_installed: true,
    backend_loaded: true,
    dependencies_needed: false,
    all_installed: true,
    installing: false,
    python_available: true,
    python_version: '3.11.6',
    python_path: 'C:/Python311/python.exe',
    python_error: null,
  }
}

function mockCapabilities(ollama: { installed: boolean; available: boolean; models: string[] }) {
  return {
    hardware: {
      gpu: null,
      gpu_type: 'cpu',
      has_gpu: false,
      has_high_vram: false,
      has_cupy: false,
      gpu_blocked: null,
      cpu: { name: 'Mock CPU' },
    },
    ollama: {
      installed: ollama.installed,
      available: ollama.available,
      models: ollama.models.map(name => ({ name, size: 2_100_000_000, modified: nowIso() })),
      recommended_models: ['llama3.2'],
    },
    languagetool: {
      installed: false,
      running: false,
      installing: false,
      java_available: true,
    },
    nlp_methods: {
      coreference: {
        neural: {
          name: 'Coreference neural',
          description: 'Mock coreference model',
          available: true,
          default_enabled: true,
          requires_gpu: false,
          recommended_gpu: false,
        },
      },
      ner: {
        spacy: {
          name: 'spaCy NER',
          description: 'Mock NER model',
          available: true,
          default_enabled: true,
          requires_gpu: false,
          recommended_gpu: false,
        },
      },
      grammar: {
        languagetool: {
          name: 'LanguageTool',
          description: 'Mock grammar checker',
          available: true,
          default_enabled: true,
          requires_gpu: false,
          recommended_gpu: false,
        },
      },
      spelling: {},
      character_knowledge: {},
    },
    recommended_config: {
      device_preference: 'cpu',
      spacy_gpu_enabled: false,
      embeddings_gpu_enabled: false,
      batch_size: 16,
    },
  }
}

function mockLicenseStatus(): LicenseStatusPayload {
  return {
    status: 'active',
    tier: 'profesional',
    features: [],
    devices_used: 1,
    devices_max: 2,
    pages_used: 20,
    pages_max: 1000,
    pages_remaining: 980,
    unlimited: false,
    expires_at: null,
    is_trial: false,
    offline_days_remaining: null,
  }
}

export async function setupMockApi(page: Page, options: MockApiOptions = {}): Promise<MockApiState> {
  const state = createMockState(options)
  let ollamaInstalled = false
  let ollamaRunning = false
  let ollamaModels: string[] = []
  let ollamaIsDownloading = false
  let ollamaDownloadProgress: { percentage: number; status: string; error?: string } | null = null

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method().toUpperCase()

    if (path === '/api/logs/frontend') {
      await route.fulfill({ status: 204, body: '' })
      return
    }

    if (path === '/api/health' && method === 'GET') {
      await fulfillJson(route, { status: 'ok', version: 'e2e-mock' })
      return
    }

    if (path === '/api/license/status' && method === 'GET') {
      await fulfillJson(route, wrap(mockLicenseStatus()))
      return
    }

    if (path === '/api/license/quota-status' && method === 'GET') {
      await fulfillJson(route, wrap({
        pages_used: 20,
        pages_max: 1000,
        pages_remaining: 980,
        percentage: 2,
        warning_level: 'none',
        days_remaining_in_period: 25,
        unlimited: false,
      }))
      return
    }

    if (path.startsWith('/api/license/check-feature/') && method === 'GET') {
      await fulfillJson(route, wrap({ has_access: true }))
      return
    }

    if (path === '/api/models/status' && method === 'GET') {
      await fulfillJson(route, wrap(mockModelsStatus({
        installed: ollamaInstalled,
        models: [...ollamaModels],
      })))
      return
    }

    if (path === '/api/system/capabilities' && method === 'GET') {
      await fulfillJson(route, wrap(mockCapabilities({
        installed: ollamaInstalled,
        available: ollamaRunning,
        models: [...ollamaModels],
      })))
      return
    }

    if (path === '/api/models/download/progress' && method === 'GET') {
      await fulfillJson(route, wrap({
        active_downloads: {},
        has_active: false,
        model_sizes: {
          spacy: 540 * 1024 * 1024,
          embeddings: 470 * 1024 * 1024,
          transformer_ner: 500 * 1024 * 1024,
          total: 1510 * 1024 * 1024,
        },
      }))
      return
    }

    if (path === '/api/projects' && method === 'GET') {
      if (state.failProjectsRemaining > 0) {
        state.failProjectsRemaining -= 1
        await fulfillJson(route, { detail: 'Fallo simulado al listar proyectos' }, 500)
        return
      }
      await fulfillJson(route, wrap(state.projects))
      return
    }

    if (path === '/api/projects' && method === 'POST') {
      const newId = ++state.lastProjectId
      const project = buildProject(newId, `Proyecto ${newId}`, {
        analysis_status: 'pending',
        analysis_progress: 0,
        chapter_count: 1,
        entity_count: 0,
        word_count: 1500,
      })
      state.projects.push(project)
      state.entitiesByProject[newId] = []
      state.alertsByProject[newId] = []
      state.chaptersByProject[newId] = [
        {
          id: newId * 100 + 1,
          project_id: newId,
          title: 'Capítulo 1',
          content: 'Contenido inicial del proyecto recién creado.',
          chapter_number: 1,
          word_count: 1500,
          position_start: 0,
          position_end: 1500,
          structure_type: 'chapter',
          created_at: nowIso(),
          updated_at: nowIso(),
        },
      ]
      state.relationshipsByProject[newId] = { entities: [], relations: [], mentions: [], clusters: [] }
      state.progressByProject[newId] = {
        project_id: newId,
        status: 'queued',
        progress: 0,
        current_phase: 'En cola',
        phases: [],
      }
      state.executedPhasesByProject[newId] = {
        parsing: false,
        structure: false,
        entities: false,
        coreference: false,
        attributes: false,
        relationships: false,
        interactions: false,
        spelling: false,
        grammar: false,
        register: false,
        pacing: false,
        coherence: false,
        alerts: false,
        temporal: false,
        emotional: false,
        sentiment: false,
        focalization: false,
        voice_profiles: false,
      }
      updateProjectAlertCounters(state, newId)
      await fulfillJson(route, wrap(project))
      return
    }

    const projectPathMatch = path.match(/^\/api\/projects\/(\d+)$/)
    if (projectPathMatch) {
      const projectId = Number(projectPathMatch[1])

      if (method === 'GET') {
        const project = state.projects.find(p => p.id === projectId)
        if (!project) {
          await fulfillJson(route, { detail: 'Project not found' }, 404)
          return
        }
        updateProjectAlertCounters(state, projectId)
        await fulfillJson(route, wrap(project))
        return
      }

      if (method === 'DELETE') {
        state.projects = state.projects.filter(p => p.id !== projectId)
        delete state.entitiesByProject[projectId]
        delete state.alertsByProject[projectId]
        delete state.chaptersByProject[projectId]
        delete state.relationshipsByProject[projectId]
        delete state.progressByProject[projectId]
        delete state.executedPhasesByProject[projectId]
        await fulfillJson(route, { success: true })
        return
      }
    }

    const entitiesMatch = path.match(/^\/api\/projects\/(\d+)\/entities$/)
    if (entitiesMatch && method === 'GET') {
      const projectId = Number(entitiesMatch[1])
      await fulfillJson(route, { success: true, data: state.entitiesByProject[projectId] || [] })
      return
    }

    const entityAttrsMatch = path.match(/^\/api\/projects\/(\d+)\/entities\/(\d+)\/attributes$/)
    if (entityAttrsMatch && method === 'GET') {
      const entityId = Number(entityAttrsMatch[2])
      await fulfillJson(route, { success: true, data: state.attributesByEntity[entityId] || [] })
      return
    }

    const storyBibleMatch = path.match(/^\/api\/projects\/(\d+)\/story-bible\/(\d+)$/)
    if (storyBibleMatch && method === 'GET') {
      await fulfillJson(route, {
        success: true,
        data: {
          relationships: [],
          vital_status: null,
        },
      })
      return
    }

    const alertsMatch = path.match(/^\/api\/projects\/(\d+)\/alerts$/)
    if (alertsMatch && method === 'GET') {
      const projectId = Number(alertsMatch[1])
      const status = url.searchParams.get('status')
      let alerts = state.alertsByProject[projectId] || []
      if (status === 'open') {
        alerts = alerts.filter(a => ['new', 'open', 'acknowledged', 'in_progress'].includes(a.status))
      }
      await fulfillJson(route, { success: true, data: alerts })
      return
    }

    const alertActionMatch = path.match(/^\/api\/projects\/(\d+)\/alerts\/(\d+)\/(resolve|dismiss)$/)
    if (alertActionMatch && method === 'POST') {
      const projectId = Number(alertActionMatch[1])
      const alertId = Number(alertActionMatch[2])
      const action = alertActionMatch[3]
      const alerts = state.alertsByProject[projectId] || []
      const alert = alerts.find(a => a.id === alertId)
      if (alert) {
        alert.status = action === 'resolve' ? 'resolved' : 'dismissed'
        alert.resolved_at = nowIso()
        updateProjectAlertCounters(state, projectId)
      }
      await fulfillJson(route, { success: true })
      return
    }

    const chaptersMatch = path.match(/^\/api\/projects\/(\d+)\/chapters$/)
    if (chaptersMatch && method === 'GET') {
      const projectId = Number(chaptersMatch[1])
      await fulfillJson(route, { success: true, data: state.chaptersByProject[projectId] || [] })
      return
    }

    const chapterAnnotationsMatch = path.match(/^\/api\/projects\/(\d+)\/chapters\/(\d+)\/annotations$/)
    if (chapterAnnotationsMatch && method === 'GET') {
      await fulfillJson(route, { success: true, data: { annotations: [] } })
      return
    }

    const chapterDialoguesMatch = path.match(/^\/api\/projects\/(\d+)\/chapters\/(\d+)\/dialogue-attributions$/)
    if (chapterDialoguesMatch && method === 'GET') {
      await fulfillJson(route, { success: true, data: { attributions: [] } })
      return
    }

    const relationshipsMatch = path.match(/^\/api\/projects\/(\d+)\/relationships$/)
    if (relationshipsMatch && method === 'GET') {
      const projectId = Number(relationshipsMatch[1])
      await fulfillJson(route, { success: true, data: state.relationshipsByProject[projectId] || { entities: [], relations: [], mentions: [], clusters: [] } })
      return
    }

    const analysisStatusMatch = path.match(/^\/api\/projects\/(\d+)\/analysis-status$/)
    if (analysisStatusMatch && method === 'GET') {
      const projectId = Number(analysisStatusMatch[1])
      await fulfillJson(route, wrap({ executed: state.executedPhasesByProject[projectId] || {} }))
      return
    }

    const analysisProgressMatch = path.match(/^\/api\/projects\/(\d+)\/analysis\/progress$/)
    if (analysisProgressMatch && method === 'GET') {
      const projectId = Number(analysisProgressMatch[1])
      await fulfillJson(route, wrap(state.progressByProject[projectId] || {
        project_id: projectId,
        status: 'idle',
        progress: 0,
        current_phase: 'Sin actividad',
        phases: [],
      }))
      return
    }

    const analyzeMatch = path.match(/^\/api\/projects\/(\d+)\/analyze$/)
    if (analyzeMatch && method === 'POST') {
      const projectId = Number(analyzeMatch[1])
      const progress = state.progressByProject[projectId]
      if (progress) {
        progress.status = 'queued'
        progress.progress = 0
        progress.current_phase = 'En cola'
      }
      const project = state.projects.find(p => p.id === projectId)
      if (project) {
        project.analysis_status = 'queued'
        project.analysis_progress = 0
      }
      await fulfillJson(route, wrap({ project_id: projectId, status: 'queued' }))
      return
    }

    const analyzePartialMatch = path.match(/^\/api\/projects\/(\d+)\/analyze\/partial$/)
    if (analyzePartialMatch && method === 'POST') {
      const projectId = Number(analyzePartialMatch[1])
      const body = parseJsonBody<{ phases?: string[] }>(route)
      const phases = body?.phases || []
      if (!state.executedPhasesByProject[projectId]) {
        state.executedPhasesByProject[projectId] = {}
      }
      for (const phase of phases) {
        state.executedPhasesByProject[projectId][phase] = true
      }
      if (phases.includes('coreference')) {
        state.executedPhasesByProject[projectId].relationships = true
      }
      await fulfillJson(route, wrap({ started: true }))
      return
    }

    const reanalyzeMatch = path.match(/^\/api\/projects\/(\d+)\/reanalyze$/)
    if (reanalyzeMatch && method === 'POST') {
      const projectId = Number(reanalyzeMatch[1])
      const project = state.projects.find(p => p.id === projectId)
      if (project) {
        project.analysis_status = 'analyzing'
        project.analysis_progress = 15
      }
      state.progressByProject[projectId] = {
        project_id: projectId,
        status: 'running',
        progress: 15,
        current_phase: 'Reanalizando',
        phases: [
          { id: 'parsing', name: 'Análisis inicial', completed: true, current: false },
          { id: 'ner', name: 'Extracción de entidades', completed: false, current: true },
        ],
      }
      await fulfillJson(route, { success: true })
      return
    }

    const cancelAnalysisMatch = path.match(/^\/api\/projects\/(\d+)\/analysis\/cancel$/)
    if (cancelAnalysisMatch && method === 'POST') {
      const projectId = Number(cancelAnalysisMatch[1])
      state.progressByProject[projectId] = {
        project_id: projectId,
        status: 'cancelled',
        progress: 0,
        current_phase: 'Cancelado',
        phases: [],
      }
      const project = state.projects.find(p => p.id === projectId)
      if (project) {
        project.analysis_status = 'completed'
        project.analysis_progress = 100
      }
      await fulfillJson(route, { success: true })
      return
    }

    const chatMatch = path.match(/^\/api\/projects\/(\d+)\/chat$/)
    if (chatMatch && method === 'POST') {
      const body = parseJsonBody<{ message?: string }>(route)
      const message = body?.message ?? ''
      const shouldFail = options.forceChatFailure || (options.chatFailureTrigger ? message.includes(options.chatFailureTrigger) : false)
      if (shouldFail) {
        await fulfillJson(route, { success: false, error: 'El LLM no generó una respuesta' })
      } else {
        await fulfillJson(route, {
          success: true,
          data: {
            response: `Respuesta simulada para: "${message.slice(0, 60)}"`,
            contextUsed: ['Capítulo 1', 'Capítulo 2'],
            model: 'mock-llm',
          },
        })
      }
      return
    }

    const styleGuideMatch = path.match(/^\/api\/projects\/(\d+)\/style-guide$/)
    if (styleGuideMatch && method === 'GET') {
      await fulfillJson(route, {
        success: true,
        data: {
          content: '# Guia de estilo mock\n\n- Consistencia de nombres\n- Tono narrativo estable\n',
        },
      })
      return
    }

    if (path === '/api/ollama/status' && method === 'GET') {
      await fulfillJson(route, {
        success: true,
        data: {
          running: ollamaRunning,
          installed: ollamaInstalled,
          models: [...ollamaModels],
          downloaded_models: [...ollamaModels],
          is_downloading: ollamaIsDownloading,
          download_progress: ollamaDownloadProgress,
        },
      })
      return
    }

    if (path === '/api/ollama/start' && method === 'POST') {
      if (!ollamaInstalled) {
        await fulfillJson(route, {
          success: false,
          error: 'Ollama no está instalado',
          data: { action_required: 'install' },
        })
        return
      }

      ollamaRunning = true
      await fulfillJson(route, { success: true })
      return
    }

    if (path === '/api/ollama/install' && method === 'POST') {
      ollamaInstalled = true
      await fulfillJson(route, { success: true })
      return
    }

    if (path.startsWith('/api/ollama/pull/') && method === 'POST') {
      const modelName = decodeURIComponent(path.split('/').pop() || '').split(':')[0]
      if (!modelName) {
        await fulfillJson(route, { success: false, error: 'Modelo inválido' })
        return
      }

      ollamaInstalled = true
      ollamaRunning = true
      ollamaIsDownloading = true
      ollamaDownloadProgress = { percentage: 40, status: 'downloading' }

      if (!ollamaModels.includes(modelName)) {
        ollamaModels.push(modelName)
      }

      ollamaIsDownloading = false
      ollamaDownloadProgress = { percentage: 100, status: 'complete' }
      await fulfillJson(route, { success: true })
      return
    }

    if (path.startsWith('/api/ollama/model/') && method === 'DELETE') {
      const modelName = decodeURIComponent(path.split('/').pop() || '').split(':')[0]
      if (!ollamaModels.includes(modelName)) {
        await fulfillJson(route, { success: false, error: `El modelo '${modelName}' no está instalado` })
        return
      }

      if (ollamaModels.length <= 1) {
        await fulfillJson(route, { success: false, error: 'Debe quedar al menos 1 modelo instalado' })
        return
      }

      ollamaModels = ollamaModels.filter(model => model !== modelName)
      await fulfillJson(route, {
        success: true,
        data: {
          message: `Modelo '${modelName}' eliminado`,
          remaining_models: [...ollamaModels],
        },
      })
      return
    }

    if (path === '/api/dependencies/install' && method === 'POST') {
      await fulfillJson(route, wrap({ started: true }))
      return
    }

    if (path === '/api/models/download' && method === 'POST') {
      await fulfillJson(route, wrap({ started: true }))
      return
    }

    await fulfillJson(route, { success: true, data: {} })
  })

  return state
}
