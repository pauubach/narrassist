import { nextTick, ref } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'
import { useDocumentViewerPreferences } from './useDocumentViewerPreferences'

describe('useDocumentViewerPreferences', () => {
  const showSpellingErrors = ref(true)
  const showGrammarErrors = ref(true)

  beforeEach(() => {
    localStorage.clear()
    showSpellingErrors.value = true
    showGrammarErrors.value = true
  })

  it('loads appearance and error preferences from localStorage', () => {
    localStorage.setItem('narrative_assistant_settings', JSON.stringify({
      fontSize: 'large',
      lineHeight: '1.8',
    }))
    localStorage.setItem('narrative_assistant_error_prefs', JSON.stringify({
      showSpellingErrors: false,
      showGrammarErrors: true,
    }))

    const prefs = useDocumentViewerPreferences({
      showSpellingErrors,
      showGrammarErrors,
    })
    prefs.loadAppearanceSettings()

    expect(prefs.contentStyle.value).toEqual({
      fontSize: '1.15rem',
      lineHeight: '1.8',
    })
    expect(showSpellingErrors.value).toBe(false)
    expect(showGrammarErrors.value).toBe(true)
  })

  it('persists error preferences when toggles change', async () => {
    useDocumentViewerPreferences({
      showSpellingErrors,
      showGrammarErrors,
    })

    showSpellingErrors.value = false
    showGrammarErrors.value = false
    await nextTick()

    expect(JSON.parse(localStorage.getItem('narrative_assistant_error_prefs') || '{}')).toEqual({
      showSpellingErrors: false,
      showGrammarErrors: false,
    })
  })

  it('keeps defaults when stored settings are invalid', () => {
    localStorage.setItem('narrative_assistant_settings', '{invalid')
    localStorage.setItem('narrative_assistant_error_prefs', '{invalid')

    const prefs = useDocumentViewerPreferences({
      showSpellingErrors,
      showGrammarErrors,
    })
    prefs.loadAppearanceSettings()

    expect(prefs.contentStyle.value).toEqual({
      fontSize: '1rem',
      lineHeight: '1.6',
    })
    expect(showSpellingErrors.value).toBe(true)
    expect(showGrammarErrors.value).toBe(true)
  })
})
