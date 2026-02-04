# Mapa de Integración con Sistema de Alertas

> Documento que mapea qué features del sistema generan alertas y cuáles son solo informativas.

---

## Resumen

| Feature | Genera Alertas | Categoría de Alerta | Método en AlertEngine |
|---------|----------------|---------------------|----------------------|
| **Attribute Consistency** | ✅ Sí | `CONSISTENCY` | `create_from_attribute_inconsistency()` |
| **Timeline** | ✅ Sí | `TIMELINE_ISSUE` | `create_from_temporal_inconsistency()` |
| **Focalization** | ✅ Sí | `FOCALIZATION` | `create_from_focalization_violation()` |
| **Voice Profiles** | ✅ Sí | `VOICE_DEVIATION` | `create_from_voice_deviation()` |
| **Register Analysis** | ✅ Sí | `STYLE` | `create_from_register_change()` |
| **Emotional Analysis** | ✅ Sí | `EMOTIONAL` | `create_from_emotional_incoherence()` |
| **Echo/Repetitions** | ✅ Sí | `REPETITION` | `create_from_correction_issue()` |
| **Spelling** | ✅ Sí | `ORTHOGRAPHY` | `create_from_spelling_issue()` |
| **Grammar** | ✅ Sí | `GRAMMAR` | `create_from_grammar_issue()` |
| **Typography/Punctuation** | ✅ Sí | `TYPOGRAPHY`/`PUNCTUATION` | `create_from_correction_issue()` |
| **Speaker Attribution** | ✅ Sí | `STYLE` | `create_from_speaker_attribution()` |
| **Deceased Reappearance** | ✅ Sí | `CONSISTENCY` | `create_from_deceased_reappearance()` |
| Sticky Sentences | ❌ No | - | Solo métrica informativa |
| Sentence Variation | ❌ No | - | Solo métrica informativa |
| Pacing Analysis | ❌ No | - | Solo métrica informativa |
| Age Readability | ❌ No | - | Solo métrica informativa |
| Scenes/Tagging | ❌ No | - | Solo organizativo |
| Relationships Graph | ❌ No | - | Solo visualización |
| Glossary/Terminology | ❌ No | - | Solo referencia |

---

## Categorías de Alertas Disponibles

```python
class AlertCategory(Enum):
    CONSISTENCY = "consistency"        # Inconsistencias de atributos
    STYLE = "style"                    # Estilo narrativo
    BEHAVIORAL = "behavioral"          # Comportamiento de personajes
    FOCALIZATION = "focalization"      # Violaciones de focalización
    STRUCTURE = "structure"            # Problemas estructurales
    WORLD = "world"                    # Inconsistencias del mundo
    ENTITY = "entity"                  # Problemas con entidades
    ORTHOGRAPHY = "orthography"        # Errores ortográficos
    GRAMMAR = "grammar"                # Errores gramaticales
    TIMELINE_ISSUE = "timeline"        # Inconsistencias temporales
    CHARACTER_CONSISTENCY = "character_consistency"  # Personajes
    VOICE_DEVIATION = "voice_deviation"  # Desviaciones de voz
    EMOTIONAL = "emotional"            # Incoherencias emocionales
    TYPOGRAPHY = "typography"          # Tipografía
    PUNCTUATION = "punctuation"        # Puntuación
    REPETITION = "repetition"          # Repeticiones
    AGREEMENT = "agreement"            # Concordancia
    OTHER = "other"
```

---

## Features Sin Alertas (Solo Métricas)

Estas features proporcionan información y métricas pero **NO detectan errores**, por lo que no generan alertas:

### 1. Sticky Sentences (Oraciones Pesadas)
- **Qué hace**: Mide el % de palabras funcionales (glue words) por oración
- **Por qué no alerta**: Es una métrica de estilo, no un error. Un alto % puede ser intencional
- **Posible mejora futura**: Alertar si > 60% de oraciones son "pegajosas" (muy alto)

### 2. Sentence Variation (Variación de Oraciones)
- **Qué hace**: Analiza distribución de longitudes de oraciones
- **Por qué no alerta**: Variación baja puede ser estilo del autor
- **Posible mejora futura**: Alertar si desviación estándar < 3 (muy monótono)

### 3. Pacing Analysis (Ritmo Narrativo)
- **Qué hace**: Analiza ratio diálogo/narración/descripción
- **Por qué no alerta**: El ritmo es decisión del autor
- **Posible mejora futura**: Alertar si hay 10+ páginas consecutivas sin diálogo

### 4. Age Readability (Legibilidad por Edad)
- **Qué hace**: Estima grupo de edad objetivo para literatura infantil
- **Por qué no alerta**: Es orientativo, el autor decide
- **Posible mejora futura**: Ver [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md)

---

## Features Sin Duplicar

Verificación de que no hay features duplicadas:

| Feature Backend | Tab/Componente UI | Endpoint API | Único |
|----------------|-------------------|--------------|-------|
| `sticky_sentences.py` | `StickySentencesTab.vue` | `/api/projects/{id}/sticky-sentences` | ✅ |
| `repetition_detector.py` | `EchoReportTab.vue` | `/api/projects/{id}/echo-report` | ✅ |
| `readability.py` (variación) | `SentenceVariationTab.vue` | `/api/projects/{id}/sentence-variation` | ✅ |
| `readability.py` (edad) | `AgeReadabilityTab.vue` | `/api/projects/{id}/age-readability` | ✅ |
| `pacing.py` | `PacingAnalysisTab.vue` | `/api/projects/{id}/pacing-analysis` | ✅ |
| `emotional_coherence.py` | `EmotionalAnalysisTab.vue` | `/api/projects/{id}/emotional-analysis` | ✅ |
| `focalization/` | `FocalizationTab.vue` | `/api/projects/{id}/focalization` | ✅ |
| `scenes/` | `SceneTaggingTab.vue` | `/api/projects/{id}/scenes` | ✅ |
| `register_analyzer.py` | `RegisterAnalysisTab.vue` | `/api/projects/{id}/register-analysis` | ✅ |
| `voice_profiles.py` | (dentro de CharacterView) | `/api/projects/{id}/voice-profiles` | ✅ |
| `vital_status.py` | API endpoint | `/api/projects/{id}/vital-status` | ✅ |

**Nota**: `readability.py` contiene tanto variación de oraciones como legibilidad por edad, pero son funciones distintas con endpoints separados.

---

## Resumen de Gaps

### Lo que SÍ está conectado a alertas:
- ✅ Consistencia de atributos
- ✅ Timeline/temporalidad
- ✅ Focalización
- ✅ Voz de personajes
- ✅ Registro narrativo
- ✅ Coherencia emocional
- ✅ Repeticiones léxicas (eco)
- ✅ Ortografía y gramática
- ✅ Tipografía y puntuación
- ✅ Atribución de hablantes
- ✅ Reaparición de personaje fallecido

### Lo que NO genera alertas (por diseño):
- ℹ️ Sticky sentences (métrica)
- ℹ️ Variación de oraciones (métrica)
- ℹ️ Ritmo narrativo (métrica)
- ℹ️ Legibilidad por edad (métrica)
- ℹ️ Grafo de relaciones (visualización)
- ℹ️ Escenas (organización)
- ℹ️ Glosario (referencia)

### Lo que podría generar alertas en el futuro:
- 📋 Age Readability: "Texto demasiado complejo para edad objetivo"
- 📋 Sticky Sentences: "Más del 60% de oraciones son pesadas"
- 📋 Pacing: "Sección muy larga sin diálogo"
- 📋 Character Location: "Personaje en dos lugares simultáneos" (parcial)

---

*Documento creado: 26 Enero 2026*
