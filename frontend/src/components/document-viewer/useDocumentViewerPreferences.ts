import { computed, ref, watch, type Ref } from 'vue'

interface UseDocumentViewerPreferencesOptions {
  showSpellingErrors: Ref<boolean>
  showGrammarErrors: Ref<boolean>
}

export function useDocumentViewerPreferences(options: UseDocumentViewerPreferencesOptions) {
  const fontSize = ref<'small' | 'medium' | 'large'>('medium')
  const lineHeight = ref('1.6')

  const fontSizeMap: Record<string, string> = {
    small: '0.9rem',
    medium: '1rem',
    large: '1.15rem',
  }

  const loadAppearanceSettings = () => {
    const savedSettings = localStorage.getItem('narrative_assistant_settings')
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings)
        fontSize.value = parsed.fontSize || 'medium'
        lineHeight.value = parsed.lineHeight || '1.6'
      } catch {
        // Mantener defaults si el almacenamiento local est?? corrupto.
      }
    }

    const errorPrefs = localStorage.getItem('narrative_assistant_error_prefs')
    if (errorPrefs) {
      try {
        const parsed = JSON.parse(errorPrefs)
        options.showSpellingErrors.value = parsed.showSpellingErrors ?? true
        options.showGrammarErrors.value = parsed.showGrammarErrors ?? true
      } catch {
        // Mantener defaults si las preferencias est??n corruptas.
      }
    }
  }

  const saveErrorPreferences = () => {
    localStorage.setItem('narrative_assistant_error_prefs', JSON.stringify({
      showSpellingErrors: options.showSpellingErrors.value,
      showGrammarErrors: options.showGrammarErrors.value,
    }))
  }

  watch([options.showSpellingErrors, options.showGrammarErrors], saveErrorPreferences)

  const contentStyle = computed(() => ({
    fontSize: fontSizeMap[fontSize.value] || '1rem',
    lineHeight: lineHeight.value,
  }))

  return {
    fontSize,
    lineHeight,
    contentStyle,
    loadAppearanceSettings,
  }
}
