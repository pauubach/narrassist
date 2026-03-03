/**
 * Composable: migración one-shot de localStorage → backend (CR-03 post-MVP).
 *
 * En versiones anteriores, los settings de análisis (enabledNLPMethods,
 * multiModelSynthesis, characterKnowledgeMode) se almacenaban solo en
 * localStorage. Ahora se persisten en el backend por proyecto.
 *
 * Este módulo detecta si hay settings legacy en localStorage que el backend
 * aún no tiene y los migra automáticamente una vez.
 */

import { safeGetItem } from '@/utils/safeStorage'
import { getProject, updateProjectSettings } from '@/services/projects'
import type { ApiNLPMethods, ApiPipelineFlags } from '@/types/api/projects'

const STORAGE_KEY = 'narrative_assistant_settings'
const NLP_CATEGORIES = ['coreference', 'ner', 'grammar', 'spelling', 'character_knowledge'] as const
const CHARACTER_KNOWLEDGE_MODES = new Set(['rules', 'llm', 'hybrid'])
const DEFAULT_NLP_METHODS: Required<ApiNLPMethods> = {
  coreference: ['embeddings', 'morpho', 'heuristics'],
  ner: ['spacy', 'gazetteer'],
  grammar: ['spacy_rules'],
  spelling: ['patterns', 'symspell', 'hunspell', 'languagetool', 'pyspellchecker'],
  character_knowledge: ['rules'],
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    .map(item => item.trim())
    .filter((v, i, a) => a.indexOf(v) === i) // deduplicate
}

interface LocalAnalysisSettings {
  enabledNLPMethods?: Record<string, unknown>
  characterKnowledgeMode?: string
  multiModelSynthesis?: boolean
}

/**
 * Construye un patch de API desde settings de localStorage.
 * Función interna, usada solo para migración.
 */
export function buildPatchFromLocalStorage(raw: string | null): {
  analysis_features: {
    schema_version: number
    pipeline_flags: ApiPipelineFlags
    nlp_methods: ApiNLPMethods
  }
} | null {
  if (!raw) return null

  let parsed: LocalAnalysisSettings
  try {
    parsed = JSON.parse(raw) as LocalAnalysisSettings
  } catch {
    return null
  }

  const enabled =
    parsed.enabledNLPMethods && typeof parsed.enabledNLPMethods === 'object'
      ? parsed.enabledNLPMethods
      : {}
  const nlpMethods: ApiNLPMethods = {}

  for (const category of NLP_CATEGORIES) {
    const hasCategory = Object.prototype.hasOwnProperty.call(enabled, category)
    if (hasCategory) {
      nlpMethods[category] = normalizeStringList(enabled[category])
    } else {
      nlpMethods[category] = [...DEFAULT_NLP_METHODS[category]]
    }
  }

  if (
    typeof parsed.characterKnowledgeMode === 'string' &&
    CHARACTER_KNOWLEDGE_MODES.has(parsed.characterKnowledgeMode)
  ) {
    nlpMethods.character_knowledge = [parsed.characterKnowledgeMode]
  }

  const pipelineFlags: ApiPipelineFlags = {
    grammar: (nlpMethods.grammar?.length ?? 0) > 0,
    spelling: (nlpMethods.spelling?.length ?? 0) > 0,
  }

  if (typeof parsed.multiModelSynthesis === 'boolean') {
    pipelineFlags.multi_model_voting = parsed.multiModelSynthesis
  }

  return {
    analysis_features: {
      schema_version: 1,
      pipeline_flags: pipelineFlags,
      nlp_methods: nlpMethods,
    },
  }
}

/**
 * Migra settings de análisis desde localStorage al backend para un proyecto.
 *
 * Solo migra si:
 * 1. El backend no tiene settings de usuario (updated_by es vacío o no existe)
 * 2. localStorage tiene settings que migrar
 *
 * Si `forceSync=true`, omite la condición (1) y sincroniza siempre el estado
 * local actual al backend antes de ejecutar análisis.
 *
 * Retorna true si se migró algo, false si no era necesario.
 */
export async function migrateLocalStorageSettingsToBackend(
  projectId: number,
  forceSync: boolean = false,
): Promise<boolean> {
  try {
    // 1. En modo normal, migrar solo una vez.
    if (!forceSync) {
      const project = await getProject(projectId)
      const backendFeatures = project.settings?.analysis_features

      if (
        backendFeatures?.updated_by &&
        backendFeatures.updated_by !== 'default' &&
        backendFeatures.updated_by !== ''
      ) {
        return false
      }
    }

    // 2. Leer localStorage
    const raw = safeGetItem(STORAGE_KEY)
    if (!raw) return false

    // 3. Construir patch
    const patch = buildPatchFromLocalStorage(raw)
    if (!patch) return false

    // 4. PATCH al backend
    await updateProjectSettings(projectId, patch)

    return true
  } catch (err) {
    console.warn('Settings migration failed (non-blocking):', err)
    return false
  }
}
