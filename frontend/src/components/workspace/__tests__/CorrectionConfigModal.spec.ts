/**
 * Tests para CorrectionConfigModal - lógica pura de configuración de corrección
 *
 * Testea las funciones puras y lógica de negocio:
 * - Mapeo de caracteres de diálogo (guiones, comillas)
 * - Presets de marcadores (español tradicional, anglosajón, etc.)
 * - Tracking de modificaciones (isCustom, markModified, resetParam)
 * - Gestión de reglas editoriales (add, remove, reset)
 * - Cálculo de hasUnsavedChanges
 * - Modal title con tipo/subtipo
 */


// ── Pure functions extracted from CorrectionConfigModal ─────

function getDashChar(dashType: string): string {
  switch (dashType) {
    case 'em_dash': return '—'
    case 'en_dash': return '–'
    case 'hyphen': return '-'
    default: return ''
  }
}

function getQuoteChars(quoteType: string): [string, string] {
  switch (quoteType) {
    case 'angular': return ['«', '»']
    case 'double': return ['"', '"']
    case 'single': return ["'", "'"]
    default: return ['', '']
  }
}

// Presets
const MARKER_PRESETS: Record<string, Record<string, string | boolean>> = {
  spanish_traditional: {
    spoken_dialogue_dash: 'em_dash',
    spoken_dialogue_quote: 'none',
    thoughts_quote: 'angular',
    thoughts_use_italics: true,
    nested_dialogue_quote: 'double',
    textual_quote: 'angular',
  },
  anglo_saxon: {
    spoken_dialogue_dash: 'none',
    spoken_dialogue_quote: 'double',
    thoughts_quote: 'single',
    thoughts_use_italics: true,
    nested_dialogue_quote: 'single',
    textual_quote: 'double',
  },
  spanish_quotes: {
    spoken_dialogue_dash: 'none',
    spoken_dialogue_quote: 'angular',
    thoughts_quote: 'double',
    thoughts_use_italics: true,
    nested_dialogue_quote: 'single',
    textual_quote: 'angular',
  },
}

// Modification tracking
function isCustom(modifiedParams: Set<string>, category: string, param: string): boolean {
  return modifiedParams.has(`${category}.${param}`)
}

function markModified(modifiedParams: Set<string>, category: string, param: string): Set<string> {
  const next = new Set(modifiedParams)
  next.add(`${category}.${param}`)
  return next
}

function resetParam(modifiedParams: Set<string>, category: string, param: string): Set<string> {
  const next = new Set(modifiedParams)
  next.delete(`${category}.${param}`)
  return next
}

function hasCustomizations(modifiedParams: Set<string>, modifiedRules: Set<string>): boolean {
  return modifiedParams.size > 0 || modifiedRules.size > 0
}

// Modal title
function getModalTitle(
  editingDefaults: boolean,
  typeName: string | undefined,
  subtypeName: string | undefined,
  defaultsTypeCode: string | undefined,
): string {
  if (editingDefaults) {
    const name = typeName || defaultsTypeCode
    if (subtypeName) {
      return `Editar defaults: ${name} / ${subtypeName}`
    }
    return `Editar defaults: ${name}`
  }
  return 'Configuración de corrección'
}

// Rule management
interface EditorialRule {
  id: string
  text: string
  enabled: boolean
  source: string
  source_name: string | null
  overridden: boolean
}

function addRule(rules: EditorialRule[], modifiedRules: Set<string>, timestamp: number): {
  rules: EditorialRule[]
  modifiedRules: Set<string>
} {
  const newRule: EditorialRule = {
    id: `custom_${timestamp}`,
    text: '',
    enabled: true,
    source: 'custom',
    source_name: null,
    overridden: false,
  }
  return {
    rules: [...rules, newRule],
    modifiedRules: new Set([...modifiedRules, newRule.id]),
  }
}

function removeRule(rules: EditorialRule[], modifiedRules: Set<string>, index: number): {
  rules: EditorialRule[]
  modifiedRules: Set<string>
} {
  const rule = rules[index]
  if (!rule) return { rules, modifiedRules }

  const newModified = new Set(modifiedRules)
  newModified.delete(rule.id)
  newModified.add('_removed_' + rule.id)

  const newRules = [...rules]
  newRules.splice(index, 1)

  return { rules: newRules, modifiedRules: newModified }
}

function markRuleModified(rule: EditorialRule, modifiedRules: Set<string>): Set<string> {
  const next = new Set(modifiedRules)
  next.add(rule.id)
  if (rule.source !== 'custom') {
    rule.overridden = true
  }
  return next
}

// Apply preset to dialog config
function applyPreset(presetName: string): Record<string, string | boolean> | null {
  return MARKER_PRESETS[presetName] || null
}

// ── Tests ───────────────────────────────────────────────────

describe('CorrectionConfigModal: getDashChar', () => {
  it('should return em dash for em_dash', () => {
    expect(getDashChar('em_dash')).toBe('—')
  })

  it('should return en dash for en_dash', () => {
    expect(getDashChar('en_dash')).toBe('–')
  })

  it('should return hyphen for hyphen', () => {
    expect(getDashChar('hyphen')).toBe('-')
  })

  it('should return empty for unknown type', () => {
    expect(getDashChar('none')).toBe('')
    expect(getDashChar('unknown')).toBe('')
  })
})

describe('CorrectionConfigModal: getQuoteChars', () => {
  it('should return angular quotes «»', () => {
    expect(getQuoteChars('angular')).toEqual(['«', '»'])
  })

  it('should return double quotes ""', () => {
    expect(getQuoteChars('double')).toEqual(['"', '"'])
  })

  it('should return single quotes \'\'', () => {
    expect(getQuoteChars('single')).toEqual(["'", "'"])
  })

  it('should return empty for unknown type', () => {
    expect(getQuoteChars('none')).toEqual(['', ''])
    expect(getQuoteChars('unknown')).toEqual(['', ''])
  })
})

describe('CorrectionConfigModal: MARKER_PRESETS', () => {
  it('should have 3 presets', () => {
    expect(Object.keys(MARKER_PRESETS)).toHaveLength(3)
  })

  it('spanish_traditional: uses em_dash and angular quotes', () => {
    const preset = MARKER_PRESETS['spanish_traditional']
    expect(preset.spoken_dialogue_dash).toBe('em_dash')
    expect(preset.spoken_dialogue_quote).toBe('none')
    expect(preset.thoughts_quote).toBe('angular')
    expect(preset.nested_dialogue_quote).toBe('double')
    expect(preset.textual_quote).toBe('angular')
    expect(preset.thoughts_use_italics).toBe(true)
  })

  it('anglo_saxon: uses no dash and double quotes', () => {
    const preset = MARKER_PRESETS['anglo_saxon']
    expect(preset.spoken_dialogue_dash).toBe('none')
    expect(preset.spoken_dialogue_quote).toBe('double')
    expect(preset.thoughts_quote).toBe('single')
    expect(preset.nested_dialogue_quote).toBe('single')
    expect(preset.textual_quote).toBe('double')
  })

  it('spanish_quotes: uses no dash and angular quotes', () => {
    const preset = MARKER_PRESETS['spanish_quotes']
    expect(preset.spoken_dialogue_dash).toBe('none')
    expect(preset.spoken_dialogue_quote).toBe('angular')
    expect(preset.thoughts_quote).toBe('double')
    expect(preset.nested_dialogue_quote).toBe('single')
    expect(preset.textual_quote).toBe('angular')
  })

  it('all presets should have same set of keys', () => {
    const expectedKeys = ['spoken_dialogue_dash', 'spoken_dialogue_quote', 'thoughts_quote', 'thoughts_use_italics', 'nested_dialogue_quote', 'textual_quote']
    for (const [name, preset] of Object.entries(MARKER_PRESETS)) {
      for (const key of expectedKeys) {
        expect(preset[key], `${name}.${key}`).toBeDefined()
      }
    }
  })

  it('all presets should use italics for thoughts', () => {
    for (const preset of Object.values(MARKER_PRESETS)) {
      expect(preset.thoughts_use_italics).toBe(true)
    }
  })
})

describe('CorrectionConfigModal: applyPreset', () => {
  it('should return preset config for known presets', () => {
    expect(applyPreset('spanish_traditional')).toBeTruthy()
    expect(applyPreset('anglo_saxon')).toBeTruthy()
    expect(applyPreset('spanish_quotes')).toBeTruthy()
  })

  it('should return null for unknown preset', () => {
    expect(applyPreset('unknown')).toBeNull()
    expect(applyPreset('detect')).toBeNull()
  })
})

describe('CorrectionConfigModal: modification tracking', () => {
  it('should detect custom parameter', () => {
    const params = new Set(['dialog.enabled'])
    expect(isCustom(params, 'dialog', 'enabled')).toBe(true)
    expect(isCustom(params, 'dialog', 'other')).toBe(false)
  })

  it('should add parameter to modified set', () => {
    const params = markModified(new Set(), 'dialog', 'enabled')
    expect(params.has('dialog.enabled')).toBe(true)
  })

  it('should accumulate multiple modifications', () => {
    let params = new Set<string>()
    params = markModified(params, 'dialog', 'enabled')
    params = markModified(params, 'repetition', 'tolerance')
    params = markModified(params, 'sentence', 'max_length_words')
    expect(params.size).toBe(3)
  })

  it('should remove parameter on reset', () => {
    let params = new Set(['dialog.enabled', 'dialog.preset'])
    params = resetParam(params, 'dialog', 'enabled')
    expect(params.has('dialog.enabled')).toBe(false)
    expect(params.has('dialog.preset')).toBe(true)
  })

  it('should handle resetting non-existent parameter', () => {
    const params = resetParam(new Set(['dialog.enabled']), 'dialog', 'nonexistent')
    expect(params.size).toBe(1) // Unchanged
  })
})

describe('CorrectionConfigModal: hasCustomizations', () => {
  it('should be false with no modifications', () => {
    expect(hasCustomizations(new Set(), new Set())).toBe(false)
  })

  it('should be true with modified params', () => {
    expect(hasCustomizations(new Set(['dialog.enabled']), new Set())).toBe(true)
  })

  it('should be true with modified rules', () => {
    expect(hasCustomizations(new Set(), new Set(['rule_1']))).toBe(true)
  })

  it('should be true with both modified', () => {
    expect(hasCustomizations(new Set(['dialog.enabled']), new Set(['rule_1']))).toBe(true)
  })
})

describe('CorrectionConfigModal: modalTitle', () => {
  it('should return default title when not editing defaults', () => {
    expect(getModalTitle(false, undefined, undefined, undefined)).toBe('Configuración de corrección')
  })

  it('should show type name when editing defaults', () => {
    expect(getModalTitle(true, 'Novela', undefined, undefined)).toBe('Editar defaults: Novela')
  })

  it('should show type + subtype when both available', () => {
    expect(getModalTitle(true, 'Novela', 'Histórica', undefined)).toBe('Editar defaults: Novela / Histórica')
  })

  it('should fall back to defaultsTypeCode if no typeName', () => {
    expect(getModalTitle(true, undefined, undefined, 'novel')).toBe('Editar defaults: novel')
  })

  it('should use typeName over defaultsTypeCode', () => {
    expect(getModalTitle(true, 'Novela', undefined, 'novel')).toBe('Editar defaults: Novela')
  })
})

describe('CorrectionConfigModal: rule management', () => {
  const existingRules: EditorialRule[] = [
    { id: 'rule_1', text: 'No usar gerundios', enabled: true, source: 'type', source_name: 'Novela', overridden: false },
    { id: 'rule_2', text: 'Evitar adverbios en -mente', enabled: true, source: 'type', source_name: 'Novela', overridden: false },
  ]

  it('should add a new custom rule', () => {
    const result = addRule(existingRules, new Set(), 1234567890)
    expect(result.rules).toHaveLength(3)
    expect(result.rules[2].id).toBe('custom_1234567890')
    expect(result.rules[2].source).toBe('custom')
    expect(result.rules[2].enabled).toBe(true)
    expect(result.rules[2].text).toBe('')
    expect(result.modifiedRules.has('custom_1234567890')).toBe(true)
  })

  it('should remove rule by index', () => {
    const result = removeRule(existingRules, new Set(), 0)
    expect(result.rules).toHaveLength(1)
    expect(result.rules[0].id).toBe('rule_2')
    expect(result.modifiedRules.has('_removed_rule_1')).toBe(true)
  })

  it('should handle removing non-existent index', () => {
    const result = removeRule(existingRules, new Set(), 99)
    expect(result.rules).toHaveLength(2) // Unchanged
  })

  it('should mark type-sourced rule as overridden', () => {
    const rule: EditorialRule = { ...existingRules[0] }
    const modified = markRuleModified(rule, new Set())
    expect(modified.has('rule_1')).toBe(true)
    expect(rule.overridden).toBe(true)
  })

  it('should not mark custom rule as overridden', () => {
    const rule: EditorialRule = {
      id: 'custom_1', text: 'My rule', enabled: true, source: 'custom', source_name: null, overridden: false,
    }
    const modified = markRuleModified(rule, new Set())
    expect(modified.has('custom_1')).toBe(true)
    expect(rule.overridden).toBe(false) // custom rules are never "overridden"
  })

  it('should not mutate original rules array on add', () => {
    const original = [...existingRules]
    addRule(existingRules, new Set(), 1234567890)
    expect(existingRules).toEqual(original)
  })

  it('should not mutate original rules array on remove', () => {
    const original = [...existingRules]
    removeRule(existingRules, new Set(), 0)
    expect(existingRules).toEqual(original)
  })
})

describe('CorrectionConfigModal: preset application workflow', () => {
  it('should apply spanish_traditional and mark all fields', () => {
    let params = new Set<string>()
    const preset = applyPreset('spanish_traditional')!

    // Simulate onPresetChange: mark preset + all individual fields
    params = markModified(params, 'dialog', 'preset')
    params = markModified(params, 'dialog', 'detection_mode')
    params = markModified(params, 'dialog', 'spoken_dialogue_dash')
    params = markModified(params, 'dialog', 'spoken_dialogue_quote')
    params = markModified(params, 'dialog', 'thoughts_quote')
    params = markModified(params, 'dialog', 'thoughts_use_italics')
    params = markModified(params, 'dialog', 'nested_dialogue_quote')
    params = markModified(params, 'dialog', 'textual_quote')

    // 8 params marked
    expect(params.size).toBe(8)
    expect(hasCustomizations(params, new Set())).toBe(true)

    // Verify preset values
    expect(preset.spoken_dialogue_dash).toBe('em_dash')
    expect(getDashChar(preset.spoken_dialogue_dash as string)).toBe('—')
  })

  it('should generate correct preview for spanish_traditional', () => {
    const preset = MARKER_PRESETS['spanish_traditional']
    const dash = getDashChar(preset.spoken_dialogue_dash as string)
    const nested = getQuoteChars(preset.nested_dialogue_quote as string)
    const thoughts = getQuoteChars(preset.thoughts_quote as string)

    expect(dash).toBe('—')
    expect(nested).toEqual(['"', '"'])
    expect(thoughts).toEqual(['«', '»'])
  })

  it('should generate correct preview for anglo_saxon', () => {
    const preset = MARKER_PRESETS['anglo_saxon']
    const spoken = getQuoteChars(preset.spoken_dialogue_quote as string)
    const nested = getQuoteChars(preset.nested_dialogue_quote as string)
    const thoughts = getQuoteChars(preset.thoughts_quote as string)

    expect(spoken).toEqual(['"', '"'])
    expect(nested).toEqual(["'", "'"])
    expect(thoughts).toEqual(["'", "'"])
  })
})
