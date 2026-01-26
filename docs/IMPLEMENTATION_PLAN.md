# Plan de Implementación - Narrative Assistant v0.3.0+

> **Fecha**: 2026-01-26
> **Basado en**: Síntesis de 4 expertos (Arquitecto, PM, Tech Writer, Product Manager)
> **Estrategia**: "Corrector-First, Editor-Later"

---

## Resumen Ejecutivo

Este documento unifica las recomendaciones de múltiples expertos para la implementación de funcionalidades pendientes. Prioriza features para correctores profesionales antes de features para editores literarios.

### Principios Guía

1. **Estabilizar antes de expandir** - Completar módulos existentes antes de crear nuevos
2. **Backend + UI siempre juntos** - No crear backend sin UI ni viceversa
3. **Configuración adaptativa** - Todos los procesos multi-método configurables en Settings
4. **Integrar, no fragmentar** - Extender tabs existentes, no crear nuevos

---

## Fase 0: Estabilización de Fundamentos

> **Objetivo**: Completar módulos backend parcialmente implementados antes de crear UIs
> **Actualizado**: 2026-01-26

### 0.1 Completar Character Knowledge (3-4 días) 🚨 CRÍTICO

**Estado actual**: 85% - Funcional pero sin método estructurado `_extract_knowledge_facts()`

El módulo tiene implementado:
- ✅ `DirectedMention`, `KnowledgeFact`, `Opinion`, `Intention` (dataclasses)
- ✅ `analyze_dialogue()` - Detecta menciones en diálogos con sentimiento
- ✅ `analyze_narration()` - Patrones regex para pensamiento/conocimiento/opiniones
- ✅ `analyze_intentions()` - Detecta intenciones de personajes
- ✅ `get_asymmetry_report()` - Reporte comparativo entre personajes
- ⚠️ Falta: Método estructurado para extraer `KnowledgeFact` con modos (RULES/LLM/HYBRID)

**Implementar**:
```python
class KnowledgeExtractionMode(Enum):
    RULES = "rules"      # Patrones + spaCy dependency (rápido, ~70% precisión)
    LLM = "llm"          # Ollama (lento, ~90% precisión)
    HYBRID = "hybrid"    # Rules + LLM fallback (default si GPU)

def _extract_knowledge_facts(self, text, characters, mode=None):
    if mode is None:
        mode = self._auto_select_mode()  # GPU → HYBRID, CPU → RULES
    ...
```

**Archivo**: `src/narrative_assistant/analysis/character_knowledge.py`

### 0.2 Voice Profiles ✅ COMPLETADO

**Estado**: 100% - Backend completo + endpoint API creado

- ✅ `VoiceMetrics` - 12 métricas cuantitativas
- ✅ `VoiceProfile` - Perfil completo con `to_dict()`
- ✅ `VoiceProfileBuilder` - Construcción de perfiles
- ✅ `characteristic_words` - TF-IDF implementado
- ✅ `top_fillers` - Lista de muletillas con frecuencia
- ✅ `speech_patterns` - Patrones de inicio/fin/expresiones
- ✅ **Endpoint**: `GET /api/projects/{id}/voice-profiles`

**Archivo**: `src/narrative_assistant/voice/profiles.py`

### 0.3 Register Analysis ✅ COMPLETADO

**Estado**: 100% - Backend completo + endpoint API creado

- ✅ `RegisterType` enum (5 tipos de registro)
- ✅ `RegisterAnalyzer` - Analiza segmentos individuales
- ✅ `RegisterChangeDetector` - Detecta cambios con severidad
- ✅ `get_summary()` - Estadísticas agregadas
- ✅ `get_register_distribution()` - Distribución por tipo
- ✅ **Endpoint**: `GET /api/projects/{id}/register-analysis`

**Archivo**: `src/narrative_assistant/voice/register.py`

### 0.4 Speaker Attribution ✅ COMPLETADO

**Estado**: 100% - Backend completo + endpoint API creado

- ✅ `SpeakerAttributor` - 5 métodos de atribución
- ✅ Detección explícita, alternancia, perfil de voz, proximidad
- ✅ `get_attribution_stats()` - Estadísticas de atribución
- ✅ **Endpoint**: `GET /api/projects/{id}/chapters/{num}/dialogue-attributions`

**Archivo**: `src/narrative_assistant/voice/speaker_attribution.py`

### 0.5 Endpoints API - Estado

| Endpoint | Estado | Notas |
|----------|--------|-------|
| `/api/projects/{id}/voice-profiles` | ✅ | Perfiles de voz completos |
| `/api/projects/{id}/register-analysis` | ✅ | Análisis de registro con cambios |
| `/api/projects/{id}/chapters/{num}/dialogue-attributions` | ✅ | Atribución de diálogos |
| `/api/projects/{id}/characters/{charId}/knowledge` | ✅ | Conocimiento del personaje (RULES/LLM/HYBRID) |
| `/api/projects/{id}/entities/{entityId}/coreference` | ⚠️ Pendiente | Votación correferencia |
| `/api/projects/{id}/focalization` | ⚠️ Pendiente | Estado focalización |
| `/api/projects/{id}/focalization/declare` | ⚠️ Pendiente | Declarar POV |
| `/api/projects/{id}/interactions` | ⚠️ Pendiente | Patrones interacción |

### 0.6 Integración Frontend ✅ COMPLETADO

> **Actualizado**: 2026-01-26

#### Componentes Creados

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| **VoiceProfile.vue** | CharacterSheet | ✅ Integrado |
| **CharacterKnowledgeAnalysis.vue** | CharacterSheet | ✅ Integrado |
| **RegisterAnalysisTab.vue** | StyleTab | ✅ Integrado |
| **DialogueAttributionView.vue** | TextTab | ⚠️ Pendiente |

#### Store Creado

✅ `frontend/src/stores/voiceAndStyle.ts`:
- `fetchVoiceProfiles(projectId)` ✅
- `fetchRegisterAnalysis(projectId, minSeverity)` ✅
- `fetchDialogueAttributions(projectId, chapterNum)` ✅
- `fetchCharacterKnowledge(projectId, characterId, mode)` ✅

#### Tipos Creados

✅ `frontend/src/types/domain/voice.ts`:
- VoiceProfile, VoiceMetrics
- RegisterAnalysis, RegisterChange, RegisterSummary
- DialogueAttribution, DialogueAttributionStats
- KnowledgeFact, KnowledgeType

#### Integraciones Realizadas

1. ✅ **CharacterSheet.vue** → secciones VoiceProfile y CharacterKnowledge
2. ✅ **StyleTab.vue** → TabPanel "Registro Narrativo"

---

## Fase 0.5: Configuración Multi-Método (4-5 días)

> **Objetivo**: Exponer todos los procesos multi-método en Settings UI

### 0.5.1 Exponer Spelling/Ortografía (2 días)

**Backend ya tiene**: 6 voters + LLM arbitrador
**Falta**: Endpoint `/api/system/capabilities` + sección en Settings

```python
"spelling": {
    "patterns": {"name": "Patrones", "weight": 0.25, "default_enabled": True},
    "languagetool": {"name": "LanguageTool", "weight": 0.20, "default_enabled": True},
    "symspell": {"name": "SymSpell", "weight": 0.18, "default_enabled": True},
    "hunspell": {"name": "Hunspell", "weight": 0.15, "default_enabled": True},
    "pyspellchecker": {"name": "PySpellChecker", "weight": 0.12, "default_enabled": True},
    "beto": {"name": "BETO ML", "weight": 0.10, "requires_gpu": True, "default_enabled": "auto"},
    "llm_arbitrator": {"name": "LLM Arbitrador", "requires_gpu": True, "default_enabled": "auto"}
}
```

### 0.5.2 Exponer Attribute Extraction (1.5 días)

**Backend ya tiene**: 3 capas (regex, dependency, LLM)
**Falta**: Exponer en Settings

### 0.5.3 Exponer Character Knowledge (0.5 días)

**Implementar selector de modo**: RULES / LLM / HYBRID

### 0.5.4 Hardware-Adaptive Defaults (1 día)

**Frontend debe usar** `recommended_config` del backend en vez de hardcoded defaults.

---

## Fase 1: Componentes Compartidos (2-3 días)

> **Objetivo**: Crear componentes reutilizables antes de features específicas

### 1.1 ConfidenceBadge.vue

```typescript
interface Props {
  value: number          // 0-1
  variant: 'badge' | 'bar' | 'dot'
  size?: 'sm' | 'md' | 'lg'
}
```

Colores: verde (>0.7), amarillo (0.5-0.7), rojo (<0.5)

### 1.2 ChapterTimeline.vue

Adaptar de `components/timeline/VisTimeline.vue` existente.

### 1.3 MethodVotingBar.vue

```typescript
interface Props {
  methods: Array<{ name: string, score: number, agreed: boolean }>
  compact?: boolean
}
```

---

## Fase 2: Quick Wins - UI para Backend Existente (5-6 días)

> **Objetivo**: Crear UIs para módulos backend ya completos

### 2.1 Voice Profiles en BehaviorExpectations.vue (2-3 días)

**Extender** sección "Speech Patterns" con:
- Métricas cuantitativas (longitud, TTR, formalidad, muletillas)
- Palabras características (chips)
- Botón "Comparar con otro personaje"

### 2.2 Coreference Voting en EntityInspector.vue (2 días)

**Añadir** sección "Fusión Automática":
- "3/4 métodos coinciden" + ConfidenceBadge
- [Ver detalles] → Abre modal con votación detallada

### 2.3 Coreference en MergeEntitiesDialog.vue (1 día)

**Añadir** en Step 3: Recomendación del sistema con razones

---

## Fase 3: Extender Tabs Existentes (19-23 días)

> **Objetivo**: Añadir nuevas funcionalidades a tabs existentes

### 3.1 Register Analysis en StyleTab.vue (3-4 días)

**Nuevo TabPanel** "Registro Narrativo":
- Distribución por tipo (formal, neutral, coloquial)
- Lista de cambios con severidad
- Timeline por capítulo

### 3.2 Focalization en StyleTab.vue (3 días)

**Nuevo TabPanel** "Focalización":
- Matriz capítulo × tipo POV × focalizador × violaciones
- Modal de declaración

### 3.3 Interactions en RelationsTab.vue (5-6 días)

**TabView** con dos vistas:
- "Relaciones" (grafo existente)
- "Interacciones" (timeline + heatmap)

### 3.4 Knowledge en CharacterSheet.vue (5-6 días)

**Refactorizar** CharacterSheet con TabView:
- Tab "Overview" (datos estáticos)
- Tab "Analysis" (lazy loaded: BehaviorExpectations, Emotional, Knowledge)

### 3.5 Speaker Attribution en DocumentViewer.vue (3-4 días)

**Toggle** en toolbar para highlighting de diálogos:
- Color según confianza (verde/amarillo/rojo)
- Tooltip con hablante atribuido

---

## Fase 4: Features Editoriales (21-26 días)

> **Objetivo**: Features avanzadas para editores profesionales

### 4.1 Pacing Analysis (4-5 días)

Panel de ritmo narrativo con:
- Métricas por capítulo
- Curva de tensión
- Alertas de capítulos "muertos"

### 4.2 Character Arcs (5-6 días)

Vista de arco del personaje:
- Estado emocional inicial → final
- Punto de inflexión
- Clasificación (Flat/Dynamic/Tragic)

### 4.3 Chronology Checker (5-6 días)

Panel de verificación temporal:
- Timeline del manuscrito
- Alertas de anacronismos

### 4.4 Subplot Tracker (4-5 días)

Panel de subtramas:
- Lista con estado (inicio/desarrollo/clímax/cierre)
- Alertas de subtramas abandonadas

### 4.5 Editorial Report Generator (3-4 días)

Extender ExportDialog con formato "Informe Editorial":
- Resumen ejecutivo
- Fortalezas y problemas
- Recomendaciones

---

## Fase 5: Features Roadmap (37-47 días)

> **Objetivo**: Funcionalidades inspiradas en Stilus/MeaningCloud

| Feature | Días | Descripción |
|---------|------|-------------|
| Gazetteer Expansion | 5-6 | +45,000 nombres propios |
| Verb Conjugator | 3-4 | Consultar conjugaciones |
| Reverse Dictionary | 3-4 | Buscar por terminación |
| IPTC Classification | 4-5 | Clasificación temática |
| Theme Clustering | 4-5 | Temas dominantes |
| Chapter Summaries (LLM) | 4-5 | Resúmenes automáticos |
| Factual Inconsistencies | 8-10 | Detectar contradicciones |
| Expanded Ontology | 6-8 | 200+ clases de entidades |

---

## Fase 6: Deuda Técnica (30-38 días)

| Área | Días |
|------|------|
| Tests unitarios backend | 8-10 |
| Tests integración API | 4-5 |
| Tests frontend | 5-6 |
| Documentación API (OpenAPI) | 3-4 |
| Logging estructurado | 2-3 |
| Performance profiling | 3-4 |
| Refactoring deuda | 5-6 |

---

## Fase 7: Infraestructura (24-31 días)

| Tarea | Días | Coste |
|-------|------|-------|
| Code signing Windows | 2-3 | ~$300/año |
| Code signing macOS | 2-3 | $99/año |
| CI/CD Pipeline | 4-5 | Gratis |
| i18n (EN, CA) | 8-10 | - |
| Landing Page | 5-6 | ~$20/año |
| Auto-updater | 3-4 | - |

---

## Resumen de Tiempos

| Fase | Días | Acumulado | Prioridad | Estado |
|------|------|-----------|-----------|--------|
| 0: Estabilización | 3-4 | 3-4 | 🎯 Crítica | ✅ 100% |
| 0.5: Multi-Método | 4-5 | 7-9 | 🎯 Crítica | Pendiente |
| 1: Shared Components | 2-3 | 9-12 | 🎯 Crítica | Pendiente |
| 2: Quick Wins | 5-6 | 14-18 | 🎯 Crítica | Pendiente |
| 3: Extender Tabs | 19-23 | 33-41 | ✅ Alta | 🔄 En progreso |
| 4: Editoriales | 21-26 | 54-67 | ✅ Alta | Pendiente |
| 5: Roadmap | 37-47 | 91-114 | ⚠️ Media | Pendiente |
| 6: Deuda Técnica | 30-38 | 121-152 | ⚠️ Media | Pendiente |
| 7: Infraestructura | 24-31 | 145-183 | ⚠️ Media | Pendiente |

**Progreso Fase 0**: Voice Profiles ✅, Register Analysis ✅, Speaker Attribution ✅, Character Knowledge ✅
**Progreso Fase 0.6**: Store ✅, VoiceProfile.vue ✅, CharacterKnowledgeAnalysis.vue ✅, RegisterAnalysisTab.vue ✅

**MVP mejorado (Fases 0-3)**: ~33-41 días (~1.5-2 meses)
**Producto completo (Fases 0-7)**: ~145-183 días (~6-9 meses)

---

## Criterios de Éxito por Fase

### Fases 0-2 (MVP Backend-UI)

- [x] Character Knowledge extrae hechos correctamente (RULES/LLM/HYBRID)
- [x] Usuario puede ver métricas de voz completas (`/api/projects/{id}/voice-profiles`)
- [ ] Usuario puede ver por qué se fusionaron entidades
- [ ] Todos los métodos NLP configurables en Settings

### Fase 3 (Tabs Extendidas)

- [x] Usuario puede analizar registro narrativo (`/api/projects/{id}/register-analysis`)
- [ ] Usuario puede declarar y verificar focalización
- [ ] Usuario puede ver patrones de interacción
- [x] Usuario puede ver qué sabe cada personaje (CharacterKnowledgeAnalysis.vue)
- [ ] Usuario puede ver quién habla cada diálogo (DialogueAttributionView pendiente)

### Fases 4-5 (Features Avanzadas)

- [ ] Editor puede analizar pacing del manuscrito
- [ ] Editor puede ver arcos de personaje
- [ ] Editor puede detectar anacronismos
- [ ] Gazetteer expandido a 50K+ entidades

---

*Documento creado: 2026-01-26*
*Basado en síntesis de: Arquitecto, PM, Tech Writer, Product Manager*
