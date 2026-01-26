# Plan de Implementación UI - Features Backend sin Frontend

> **Fecha**: 2026-01-26
> **Versión objetivo**: 0.3.0
> **Principio**: Integrar en tabs existentes, NO crear nuevos tabs
> **Estado**: ✅ VALIDADO por 5 expertos (UX, FE, Arquitecto, Corrector, Editor)

---

## Resumen Ejecutivo

7 módulos backend tienen análisis completo pero **no tienen UI visible**. Este documento define cómo integrarlos en la UI existente sin fragmentar la experiencia.

### ⚠️ Hallazgos de Validación (2026-01-26)

**Tiempo real estimado**: **33 días** (vs 24 días original) debido a:
- 3 componentes compartidos NO existen (ChapterTimeline, ConfidenceBadge, MethodVotingBar)
- 8 endpoints API NO existen
- RelationsTab requiere refactorización arquitectónica
- Backend de votación correferencias NO implementado

**Prioridades por rol**:
| Feature | Corrector | Editor |
|---------|-----------|--------|
| Speaker Attribution | 🎯 CRÍTICA | ❌ No relevante |
| Voice Profiles | 🎯 Muy útil | 🎯 CRÍTICO |
| Knowledge Tracking | 🎯 Muy útil | 🎯 CRÍTICO |
| Register Analysis | 🎯 Muy útil | ✅ Útil |
| Focalization | 🤷 Solo editores | 🎯 Solo multi-POV |
| Interaction Patterns | ✅ Útil | ✅ Útil |
| Coreference Voting | ✅ Útil | 🤷 Ocasional |

### Estrategia: Extender Tabs Existentes

| Feature | Tab Existente | Tipo de Integración | Validación |
|---------|---------------|---------------------|------------|
| Voice Profiles | `entities` | Sección en BehaviorExpectations | ✅ UX/FE/Arq |
| Knowledge Tracking | `entities` | **Versión compacta** en CharacterSheet + modal | ⚠️ UX sugiere simplificar |
| Coreference Voting | `entities` | Panel en EntityInspector + badges en lista | ⚠️ Añadir descubribilidad |
| Interaction Patterns | `relationships` | TabView (no toggle) en RelationsTab | ⚠️ FE: usar TabView |
| Register Analysis | `style` | Nuevo TabPanel en StyleTab | ✅ UX/Corrector |
| Focalization | `style` | Nuevo TabPanel en StyleTab | ⚠️ Considerar tab "Estructura" |
| Speaker Attribution | `text` | **Highlighting** (no overlays) | ⚠️ FE: simplificar |

---

## ⚠️ Trabajo Backend Requerido (ANTES de UI)

> **Crítico**: Completar backend ANTES de implementar UI

### Endpoints API Faltantes

| Endpoint | Estado | Acción |
|----------|--------|--------|
| `/api/projects/{id}/interactions` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/characters/{charId}/voice-profile` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/entities/{entityId}/coreference` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/register-analysis` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/focalization` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/focalization/declare` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/characters/{charId}/knowledge` | ❌ NO EXISTE | Implementar |
| `/api/projects/{id}/chapters/{num}/dialogue-attributions` | ❌ NO EXISTE | Implementar |

### Lógica Backend Faltante

| Módulo | Estado | Acción |
|--------|--------|--------|
| `nlp/coreference_resolver.py` | ✅ YA TIENE votación multi-método | Solo crear endpoint API |
| `voice/register.py` | ✅ YA TIENE `RegisterChangeDetector.detect_changes()` | Solo crear endpoint API |

> ✅ **Corrección (verificado 2026-01-26)**: Ambos módulos ya tienen la lógica implementada.
> Solo falta exponer los endpoints API.

**Tiempo estimado backend**: 3-4 días (solo endpoints, no lógica)

---

## 🔍 Análisis de Completitud de Módulos Existentes

> **Verificado**: 2026-01-26 mediante exploración exhaustiva del código

### Resumen de Estado

| Módulo | Completitud | Prioridad Mejora | Esfuerzo |
|--------|-------------|------------------|----------|
| **Coreference** | 85% | Media | 2-3 días |
| **Register** | 75% | Media | 2-3 días |
| **Voice Profiles** | 70% | Alta | 3-4 días |
| **Speaker Attribution** | 80% | Media | 2-3 días |
| **Pacing** | 80% | Baja | 2-3 días |
| **Character Knowledge** | 60% | 🎯 **CRÍTICA** | 5-7 días |

**Esfuerzo total para 100%**: 16-23 días adicionales

### Detalle por Módulo

#### 1. Coreference Resolution (85% completo)

**✅ Ya implementado:**
- Votación multi-método con 4 métodos (LLM 35%, embeddings 30%, morpho 20%, heuristics 15%)
- `resolve_coreferences_voting()` funcional
- Cadenas de correferencia y menciones no resueltas

**❌ Falta para 100%:**
- Exponer resultados de votación individual por método en API
- Razonamiento textual de cada método (actualmente solo scores)
- Persistencia de decisiones del usuario (confirmar/rechazar fusión)

**Acción**: Crear endpoint `/api/projects/{id}/entities/{entityId}/coreference` que exponga `method_scores` y `method_reasoning`

#### 2. Register Analysis (75% completo)

**✅ Ya implementado:**
- `RegisterChangeDetector` con `detect_changes()`
- Análisis de registro por fragmento
- Clasificación: formal, neutral, coloquial, poético, técnico

**❌ Falta para 100%:**
- Análisis por capítulo (actualmente solo por fragmento suelto)
- Estadísticas agregadas (distribución de registros en manuscrito)
- Severidad de cambios (alta/media/baja)
- Timeline visual de evolución

**Acción**: Añadir `analyze_register_by_chapter()` que devuelva distribución + cambios con severidad

#### 3. Voice Profiles (70% completo)

**✅ Ya implementado:**
- `VoiceMetrics` dataclass con 17 métricas (avg_sentence_length, ttr, formality_index, etc.)
- `VoiceAnalyzer.analyze_voice()` calcula todas las métricas
- `VoiceProfiler` para comparación entre personajes

**❌ Falta para 100%:**
- API endpoint no devuelve todas las métricas calculadas
- `characteristic_words` y `top_fillers` no se retornan
- Comparación directa entre 2 personajes en un endpoint
- Patrones de puntuación (exclamaciones, interrogaciones)

**Acción**: Extender endpoint `/api/projects/{id}/characters/{charId}/voice-profile` para devolver todas las métricas de `VoiceMetrics`

#### 4. Speaker Attribution (80% completo)

**✅ Ya implementado:**
- 5 métodos de atribución (verb, proximity, context, name, coreference)
- 4 niveles de confianza (high, medium, low, unknown)
- `DialogueAttributor.attribute_dialogues()`

**❌ Falta para 100%:**
- Voice matching débil (no usa `VoiceAnalyzer` para comparar estilo de diálogo con perfil)
- No hay feedback loop: correcciones del usuario no mejoran futuras atribuciones
- API endpoint faltante para obtener atribuciones por capítulo

**Acción**:
- Crear endpoint `/api/projects/{id}/chapters/{num}/dialogue-attributions`
- Integrar `VoiceAnalyzer` en el método de atribución

#### 5. Pacing Analysis (80% completo)

**✅ Ya implementado:**
- `PacingAnalyzer` con 10 tipos de problemas
- 11 métricas por capítulo (word_count, dialogue_ratio, action_ratio, etc.)
- Detección de capítulos "muertos" sin conflicto

**❌ Falta para 100%:**
- Curva de tensión narrativa (tension_curve) no implementada
- Comparación con benchmarks de género
- Sugerencias de corrección específicas

**Acción**: Añadir `calculate_tension_curve()` basado en densidad de eventos + emociones + conflictos

#### 6. Character Knowledge (60% completo) 🚨 CRÍTICO

**✅ Ya implementado:**
- `CharacterKnowledgeTracker` estructura básica
- Detección de asimetrías entre personajes
- `track_knowledge_flow()` funcional

**❌ Falta para 100% (CRÍTICO):**
- `_extract_knowledge_facts()` devuelve lista vacía - **CORE NO IMPLEMENTADO**
- No extrae hechos de texto narrativo
- No distingue opiniones vs hechos
- No detecta cuándo un personaje aprende algo nuevo

**Acción PRIORITARIA**:
1. Implementar `_extract_knowledge_facts()` con LLM o reglas
2. Añadir `opinion` vs `fact` a `KnowledgeFact`
3. Crear `track_knowledge_acquisition()` para momentos de aprendizaje

### Impacto en Fases

| Fase Original | Ajuste Necesario |
|---------------|------------------|
| Fase 0 | +2 días para mejorar endpoints existentes |
| Fase 1 (Voice Profiles) | +1 día para devolver todas las métricas |
| Fase 2.4 (Knowledge) | +5-7 días para implementar core de extracción |

**Nuevo total Fase 0-2**: 38-48 días (vs 33-39 días original)

### Recomendación de Priorización

1. **🎯 INMEDIATO**: Character Knowledge core (bloqueante para UI)
2. **Alta**: Voice Profiles métricas completas
3. **Media**: Register por capítulo, Coreference razonamiento
4. **Baja**: Pacing tension curve, Speaker Attribution voice matching

---

## Fase 1: Quick Wins (Extender Componentes Existentes)

### 1.1 Voice Profiles → Extender BehaviorExpectations.vue

**Ubicación**: `frontend/src/components/BehaviorExpectations.vue`

**Estado actual**: ⚠️ Tiene `speech_patterns: string[]` básico - debe EXPANDIRSE con métricas

**Cambios**:
```
BehaviorExpectations.vue
├── Personality Analysis ✓ (existente)
├── Behavior Expectations ✓ (existente)
├── Speech Patterns ✓ (existente, EXPANDIR)
│   └── AÑADIR:
│       ├── Métricas cuantitativas
│       │   ├── Longitud promedio intervención
│       │   ├── Riqueza léxica (TTR)
│       │   ├── Índice de formalidad (0-100%)
│       │   └── Ratio de muletillas
│       ├── Palabras características (chips)
│       ├── Patrones de puntuación (!, ?, ...)
│       └── Botón "Comparar con otro personaje"
└── Violations ✓ (existente)
```

**API necesaria**:
```
GET /api/projects/{id}/characters/{charId}/voice-profile
Response: {
  metrics: { avg_length, ttr, formality, filler_ratio },
  characteristic_words: [["palabra", score], ...],
  punctuation: { exclamation: 0.4, question: 0.6 },
  top_fillers: [["bueno", 12], ["pues", 8]]
}
```

**Esfuerzo**: 1-2 días

---

### 1.2 Coreference Voting → Extender EntityInspector.vue

**Ubicación**: `frontend/src/components/inspector/EntityInspector.vue`

**Estado actual**: Muestra header, aliases, stats, menciones

> ⚠️ **Validación UX**: Añadir descubribilidad proactiva con badges en EntityList

**Cambios en EntityList** (descubribilidad):
```
EntityList.vue (sidebar)
└── Cada entidad con posible fusión:
    └── Badge "Posible duplicado" (si confianza > 70%)
```

**Cambios en EntityInspector** (versión compacta):
```
EntityInspector.vue (añadir después de stats, línea ~137)
└── AÑADIR sección "Fusión Automática" (COMPACTA):
    ├── "3/4 métodos coinciden" + ConfidenceBadge
    └── [Ver detalles] → Abre CoreferenceDetailsModal
```

**CoreferenceDetailsModal.vue** (contenido completo):
```
CoreferenceDetailsModal.vue
├── Confianza general: 75%
├── Barras de votación por método:
│   ├── LLM: 85% ████████░
│   ├── Embeddings: 78% ███████░░
│   ├── Morfológico: 65% ██████░░░
│   └── Heurísticas: 35% ███░░░░░░
├── Razonamiento de cada método (colapsable)
└── [Fusionar] [Rechazar fusión]
```

**Componentes nuevos**:
```
frontend/src/components/
├── shared/
│   └── ConfidenceBadge.vue          # Reutilizable
└── coreference/
    ├── CoreferenceVotingCard.vue    # Card compacta
    └── CoreferenceDetailsModal.vue  # Modal detallado
```

**API necesaria**:
```
GET /api/projects/{id}/entities/{entityId}/coreference
Response: {
  chain_id, confidence, methods_agreed: ["llm", "embeddings", "morpho"],
  method_scores: { llm: 0.85, embeddings: 0.78, morpho: 0.65, heuristics: 0.35 },
  method_reasoning: { llm: "Pronombre en siguiente oración...", ... }
}
```

**Esfuerzo**: 2-3 días

---

### 1.3 Coreference en MergeEntitiesDialog.vue

**Ubicación**: `frontend/src/components/MergeEntitiesDialog.vue` (Step 3)

**Estado actual**: Step 3 muestra preview de fusión

**Cambios** (después de línea 275):
```
Step 3: Confirmación
├── Preview actual ✓
└── AÑADIR sección "Recomendación del Sistema":
    ├── CoreferenceVotingCard (mode="detailed")
    ├── Si sistema recomienda: "✓ El sistema también sugiere fusionar"
    └── Si sistema NO recomienda: "⚠ El sistema sugiere NO fusionar"
        └── Mostrar razones
```

**Esfuerzo**: 1 día

---

## Fase 2: Extender Tabs de Workspace

### 2.1 Register Analysis → Añadir TabPanel en StyleTab.vue

**Ubicación**: `frontend/src/components/workspace/StyleTab.vue`

**Estado actual**:
- TabPanel "Detectores"
- TabPanel "Reglas editoriales"

**Cambios**:
```
StyleTab.vue
├── TabPanel "Detectores" ✓
├── TabPanel "Reglas editoriales" ✓
└── TabPanel "Registro Narrativo"  ← AÑADIR
    ├── RegisterAnalysisPanel.vue
    │   ├── Estadísticas generales
    │   │   ├── Distribución: Formal 35%, Neutral 45%, Coloquial 8%...
    │   │   └── Registro dominante
    │   ├── Lista de cambios detectados
    │   │   ├── [ALTA] Cap 3: Formal → Coloquial
    │   │   ├── [MEDIA] Cap 7: Neutral → Poético
    │   │   └── Click → navega a DocumentViewer
    │   └── Timeline por capítulo (reutiliza ChapterTimeline)
```

**Componentes nuevos**:
```
frontend/src/components/analysis/
└── RegisterAnalysisPanel.vue
```

**API necesaria**:
```
GET /api/projects/{id}/register-analysis
Response: {
  distribution: { formal: 0.35, neutral: 0.45, colloquial: 0.08, ... },
  dominant: "neutral",
  changes: [
    { chapter: 3, position: 1245, from: "formal", to: "colloquial", severity: "high" }
  ]
}
```

**Esfuerzo**: 2-3 días

---

### 2.2 Focalization → Añadir TabPanel en StyleTab.vue

**Ubicación**: `frontend/src/components/workspace/StyleTab.vue`

**Cambios**:
```
StyleTab.vue
├── TabPanel "Detectores" ✓
├── TabPanel "Reglas editoriales" ✓
├── TabPanel "Registro Narrativo" (fase 2.1)
└── TabPanel "Focalización"  ← AÑADIR
    ├── FocalizationPanel.vue
    │   ├── Matriz de capítulos
    │   │   ├── Cap | Tipo POV | Focalizador | Violaciones
    │   │   ├── 1   | Int.Fixed| Alice       | ✓ 0
    │   │   ├── 2   | Int.Fixed| Alice       | ⚠ 2
    │   │   └── 3   | Externo  | —           | ❌ 5
    │   ├── Modal de declaración (click en fila)
    │   │   ├── Selector de tipo POV
    │   │   ├── Selector de focalizador(es)
    │   │   └── Sugerencia automática del sistema
    │   └── Lista de violaciones con navegación
```

**Componentes nuevos**:
```
frontend/src/components/analysis/
├── FocalizationPanel.vue
└── FocalizationDeclarator.vue  # Modal
```

**API necesaria**:
```
GET /api/projects/{id}/focalization
Response: {
  chapters: [
    { chapter: 1, declared_type: "internal_fixed", focalizers: ["Alice"], violations: [] },
    { chapter: 2, declared_type: "internal_fixed", focalizers: ["Alice"], violations: [...] }
  ]
}

POST /api/projects/{id}/focalization/declare
Body: { chapter: 3, type: "external", focalizers: [] }
```

**Esfuerzo**: 3-4 días

---

### 2.3 Interaction Patterns → Extender RelationsTab.vue

**Ubicación**: `frontend/src/components/workspace/RelationsTab.vue`

**Estado actual**: Muestra RelationshipGraph.vue (grafo de relaciones)

**Cambios**:
```
RelationsTab.vue
├── Vista actual: Grafo de relaciones ✓
└── AÑADIR toggle de vista:
    ├── [Relaciones] [Interacciones]  ← Selector
    │
    ├── Vista "Relaciones" (existente)
    │   └── RelationshipGraph.vue ✓
    │
    └── Vista "Interacciones" (NUEVA)
        └── InteractionsView.vue
            ├── Selector de vista: [Timeline] [Heatmap]
            ├── Timeline de interacciones
            │   ├── Por par de personajes
            │   ├── Marcadores de tono (colores)
            │   └── Click → ver texto
            ├── Heatmap de frecuencia
            │   ├── Matriz personaje x personaje
            │   ├── Color = tono promedio
            │   └── Tamaño = frecuencia
            └── Panel de detalles (al seleccionar par)
```

**Componentes nuevos**:
```
frontend/src/components/analysis/
├── InteractionsView.vue
├── InteractionTimeline.vue
└── InteractionHeatmap.vue
```

**API** (ya existe parcialmente):
```
GET /api/projects/{id}/interactions
```

**Esfuerzo**: 4-5 días

---

### 2.4 Knowledge Tracking → Refactorizar CharacterSheet.vue con Tabs

**Ubicación**: `frontend/src/components/CharacterSheet.vue`

**Estado actual**: BehaviorExpectations + EmotionalAnalysis (todo inline, ~700 LOC)

> ✅ **Decisión de Debate de Expertos (3-1)**:
> - Refactorizar CharacterSheet con TabView
> - Lazy load de análisis avanzados
> - Knowledge aparece en 2 contextos (exploración + alertas)

**Refactorización de CharacterSheet**:
```
CharacterSheet.vue (orchestrator, ~200 LOC)
└── TabView lazy
    ├── TabPanel "Overview" → Datos estáticos
    │   ├── CharacterOverview.vue
    │   │   ├── Header, avatar, aliases
    │   │   ├── Stats básicos
    │   │   └── Atributos por tipo
    │   └── CharacterRelations.vue (relaciones + timeline)
    │
    └── TabPanel "Advanced Analysis" → LAZY LOADED
        └── CharacterAnalysis.vue (container)
            ├── BehaviorExpectations ✓ (mover aquí)
            ├── EmotionalAnalysis ✓ (mover aquí)
            └── KnowledgeNetwork ← NUEVO
                ├── Tabs internas:
                │   ├── "Lo que sabe" - Lista con opiniones/hechos
                │   ├── "Quién lo conoce" - Inverso
                │   └── "Asimetrías" - Alertas temporales
                └── Visualización: Grafo D3 (colapsable)
```

**Contexto 2: Resolución de Alertas** (Right Panel):
```
AlertsTab → Click en "Knowledge Inconsistency"
└── Right Panel muestra:
    └── KnowledgeInconsistencyAlert.vue
        ├── Descripción del problema
        ├── Capítulo y posición afectada
        ├── <KnowledgeNetwork mode="alert" :highlight-chapter="3" />
        └── Sugerencias de corrección
```

**Componentes nuevos**:
```
frontend/src/components/
├── character/
│   ├── CharacterOverview.vue     # Datos estáticos extraídos
│   ├── CharacterRelations.vue    # Relaciones extraídas
│   └── CharacterAnalysis.vue     # Container lazy-loaded
│
├── analysis/
│   └── KnowledgeNetwork.vue      # Componente reutilizable
│       └── Props: { mode: 'full'|'alert', highlightChapter?: number }
│
└── alerts/
    └── KnowledgeInconsistencyAlert.vue  # Embebe KnowledgeNetwork
```

**Performance budget**:
- CharacterSheet initial load: < 200ms
- Analysis tab lazy load: < 500ms
- Knowledge graph render: < 300ms

**Bundle splitting** (vite.config.js):
```javascript
manualChunks: {
  'character-basic': ['CharacterSheet', 'CharacterOverview'],
  'character-analysis': ['BehaviorExpectations', 'EmotionalAnalysis'],
  'knowledge-graph': ['KnowledgeNetwork', 'd3']
}
```

**Componentes nuevos**:
```
frontend/src/components/analysis/
├── KnowledgeNetwork.vue       # Container
├── KnowledgeOutgoing.vue      # Lo que sabe
├── KnowledgeIncoming.vue      # Quién lo conoce
└── KnowledgeAsymmetries.vue   # Alertas
```

**API necesaria**:
```
GET /api/projects/{id}/characters/{charId}/knowledge
Response: {
  outgoing: [{ target: "María", opinion: "positive", mentions: 23, facts: [...] }],
  incoming: [...],
  asymmetries: [{ other: "María", score: 0.82, explanation: "..." }]
}
```

**Esfuerzo**: 5-6 días (incluye refactorización de CharacterSheet)

---

### 2.5 Speaker Attribution → Highlighting en DocumentViewer.vue

**Ubicación**: `frontend/src/components/DocumentViewer.vue`

**Estado actual**: Entity highlighting, grammar annotations

> ⚠️ **Validación FE**: Usar highlighting simple (no overlays invasivos)
> ⚠️ **Validación Editor**: Feature más útil para correctores que para editores

**Cambios** (enfoque simplificado):
```
DocumentViewer.vue
├── Toolbar existente
│   └── AÑADIR toggle: [👤 Hablantes]
│
├── Contenido del documento
│   └── Cuando toggle activo, diálogos con highlighting:
│       <span class="dialogue dialogue--high" data-speaker="Juan">
│         —¿Qué hacemos ahora? —preguntó.
│       </span>
│
│       <span class="dialogue dialogue--unknown">
│         —Espera.
│       </span>
│
│   └── Tooltip al hover: "Hablante: Juan García (85% confianza)"
│   └── Color de fondo según confianza:
│       ├── Verde: alta (>70%)
│       ├── Amarillo: media (40-70%)
│       └── Rojo: baja/desconocido (<40%)
│
└── Fetch dialogue attributions por capítulo (lazy loading)
```

**Componentes nuevos**:
```
frontend/src/components/
├── document/
│   └── DialogueTooltip.vue  # Tooltip con info de hablante
└── sidebar/
    └── DialoguesPanel.vue   # Lista completa de diálogos
```

**DialoguesPanel.vue** (panel lateral):
```
DialoguesPanel.vue
├── Filtros: [Todos] [Sin atribuir] [Baja confianza]
├── Lista de diálogos:
│   ├── "—¿Qué hacemos?" → Juan García 🟢
│   ├── "—Espera." → ??? 🔴 [Atribuir a ▼]
│   └── Click → navega a posición en texto
└── Estadística: "45/50 diálogos atribuidos (90%)"
```

**API necesaria**:
```
GET /api/projects/{id}/chapters/{num}/dialogue-attributions
Response: {
  dialogues: [
    { id, text, start, end, speaker_id, speaker_name, confidence: "high"|"medium"|"low"|"unknown" }
  ]
}

PATCH /api/projects/{id}/dialogue-attributions/{id}
Body: { speaker_id: 42 }  # Usuario corrige atribución
```

**Esfuerzo**: 3-4 días (simplificado)

---

## Componentes Compartidos

Crear en `frontend/src/components/shared/`:

### ConfidenceBadge.vue
```typescript
interface Props {
  value: number          // 0-1
  variant: 'badge' | 'bar' | 'dot'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}
```
Colores: verde (>0.7), amarillo (0.5-0.7), rojo (<0.5)

### ChapterTimeline.vue
```typescript
interface Props {
  chapters: Chapter[]
  highlights: Array<{ chapter: number, color: string, intensity: number }>
  selectedChapter?: number
}
```
Reutilizado por: Register, Focalization, Interactions, Emotional

### MethodVotingBar.vue
```typescript
interface Props {
  methods: Array<{ name: string, score: number, agreed: boolean, reasoning?: string }>
  compact?: boolean
}
```
Reutilizado por: Coreference, BehaviorExpectations (ya tiene algo similar)

---

## Orden de Implementación (REVISADO)

### Fase 0: Prerequisitos (Backend + Componentes Compartidos)

| Tarea | Días | Notas |
|-------|------|-------|
| Implementar 8 endpoints API faltantes | 3-4 | Ver sección "Trabajo Backend Requerido" |
| ~~Implementar votación multi-método coreference~~ | ~~2~~ | ✅ YA EXISTE en `coreference_resolver.py` |
| ~~Añadir `detect_register_changes()`~~ | ~~1~~ | ✅ YA EXISTE en `voice/register.py` |
| Crear ConfidenceBadge.vue | 0.5 | Componente compartido |
| Adaptar VisTimeline.vue → ChapterTimeline.vue | 1 | Reutilizar `components/timeline/VisTimeline.vue` existente |
| Crear MethodVotingBar.vue | 1 | Componente compartido |

**Subtotal Fase 0**: 5.5-6.5 días (reducido de 9-10 días)

### Fase 1: Quick Wins

| Feature | Días | Dependencias |
|---------|------|--------------|
| **1.1** Voice Profiles en BehaviorExpectations | 2-3 | API voice-profile |
| **1.2** Coreference en EntityInspector + badges | 2 | ConfidenceBadge, MethodVotingBar |
| **1.3** Coreference en MergeDialog | 1 | 1.2 |

**Subtotal Fase 1**: 5-6 días

### Fase 2: Extender Tabs

| Feature | Días | Dependencias |
|---------|------|--------------|
| **2.1** Register Analysis en StyleTab | 3-4 | ChapterTimeline, API register |
| **2.2** Focalization en StyleTab | 3 | ChapterTimeline |
| **2.3** Interactions (TabView) en RelationsTab | 5-6 | API interactions, refactor tab |
| **2.4** Knowledge + Refactor CharacterSheet | 5-6 | Refactorización completa |
| **2.5** Speaker Attribution (highlighting) en DocumentViewer | 3-4 | API dialogue-attributions |

**Subtotal Fase 2**: 19-23 días

---

### Fase 3: Features Editoriales (Identificadas por Experto Editorial)

> Prioridad alta para editores profesionales

| Feature | Días | Backend | UI |
|---------|------|---------|-----|
| **3.1** Pacing Analysis | 4-5 | `analysis/pacing.py` (CREAR) | PacingPanel en StyleTab |
| **3.2** Character Arcs | 5-6 | Extender `emotional_coherence.py` | CharacterArcView en CharacterSheet |
| **3.3** Chronology Checker | 5-6 | `temporal/chronology_checker.py` (CREAR) | ChronologyPanel en TimelineTab |
| **3.4** Subplot Tracker | 4-5 | `analysis/subplots.py` (CREAR) | SubplotPanel en ResumenTab |
| **3.5** Editorial Report Generator | 3-4 | Extender `review_report_exporter.py` | ExportDialog mejorado |

**Subtotal Fase 3**: 21-26 días

#### 3.1 Pacing Analysis
```
PacingPanel.vue (StyleTab → nuevo TabPanel "Ritmo")
├── Métricas por capítulo:
│   ├── Longitud (palabras, páginas)
│   ├── Ratio diálogo/narración/acción
│   ├── Densidad de eventos
│   └── Comparación con media del manuscrito
├── Curva de tensión narrativa (gráfico)
├── Alertas: capítulos "muertos" sin conflicto
└── Click → navega al capítulo
```

**API**: `GET /api/projects/{id}/pacing-analysis`

#### 3.2 Character Arcs
```
CharacterArcView.vue (CharacterSheet → Analysis tab)
├── Estado emocional inicial vs final
├── Timeline de cambios significativos
├── Punto de inflexión detectado
├── Clasificación: Flat/Dynamic/Tragic
└── Comparación con otros personajes
```

**API**: Extender `/api/projects/{id}/characters/{charId}/emotional-profile`

#### 3.3 Chronology Checker
```
ChronologyPanel.vue (TimelineTab → nuevo panel)
├── Línea temporal del manuscrito
├── Alertas de anacronismos:
│   ├── "Cap 5: 'ayer martes' pero Cap 3 era lunes"
│   ├── "Pedro murió en cap 8, aparece vivo cap 12"
│   └── Severidad: Alta/Media/Baja
├── Eventos referidos sin setup
└── Timeline visual interactivo
```

**API**: `GET /api/projects/{id}/chronology-analysis`

#### 3.4 Subplot Tracker
```
SubplotPanel.vue (ResumenTab → nueva sección)
├── Lista de subtramas detectadas:
│   ├── Romance Alice-Bob (caps 2-15, CERRADA)
│   ├── Misterio del collar (caps 3-?, ABIERTA ⚠️)
│   └── Conflicto familiar (caps 1-20, CERRADA)
├── Estado: Inicio/Desarrollo/Clímax/Cierre
├── Alertas: subtramas abandonadas
└── Grafo de dependencias entre tramas
```

**API**: `GET /api/projects/{id}/subplots`

#### 3.5 Editorial Report Generator
```
Extender ExportDialog.vue:
├── Nuevo formato: "Informe Editorial"
├── Secciones configurables:
│   ├── Resumen ejecutivo
│   ├── Fortalezas detectadas
│   ├── Problemas críticos (plot holes, inconsistencias)
│   ├── Análisis de personajes
│   ├── Problemas de ritmo
│   └── Recomendaciones de desarrollo
└── Exportar PDF/DOCX (3-5 páginas)
```

**API**: `GET /api/projects/{id}/export/editorial-report`

---

### Fase 4: Backend sin UI Pendiente

| Feature | Días | Backend Existente | UI |
|---------|------|-------------------|-----|
| **4.1** Style Guide Export | 2-3 | `exporters/style_guide.py` ✅ | Completar stub en ExportDialog |
| **4.2** Grammar/Spelling Highlight | 3-4 | `nlp/orthography/`, `nlp/grammar/` ✅ | Highlighting en DocumentViewer |
| **4.3** Gazetteer Management | 3-4 | `nlp/ner.py` ✅ | GazetteerPanel en Settings |
| **4.4** Undo Merge | 2-3 | `persistence/history.py` ✅ | Botón en EntityInspector + historial |

**Subtotal Fase 4**: 10-14 días

#### 4.1 Style Guide Export
```
ExportDialog.vue:
└── Formato "Guía de Estilo":
    ├── Glosario de términos del proyecto
    ├── Convenciones tipográficas usadas
    ├── Nombres propios y variantes
    └── Reglas editoriales aplicadas
```

#### 4.2 Grammar/Spelling Highlight
```
DocumentViewer.vue:
├── Toolbar: [🔤 Ortografía] toggle
├── Errores subrayados en texto:
│   ├── Rojo ondulado: ortografía
│   ├── Azul ondulado: gramática
│   └── Verde ondulado: estilo
├── Tooltip al hover: explicación + sugerencia
└── Click derecho: Ignorar / Añadir al diccionario
```

**API**: Extender `/api/projects/{id}/chapters/{num}/annotations`

#### 4.3 Gazetteer Management
```
GazetteerPanel.vue (Settings → nueva sección)
├── Lista de entidades en gazetteer:
│   ├── Buscar / Filtrar por tipo
│   ├── Añadir entidad manualmente
│   ├── Editar variantes/aliases
│   └── Eliminar entrada
├── Importar/Exportar JSON
└── Estadísticas: X personajes, Y lugares, Z organizaciones
```

**API**:
- `GET /api/gazetteer`
- `POST /api/gazetteer`
- `PUT /api/gazetteer/{id}`
- `DELETE /api/gazetteer/{id}`

#### 4.4 Undo Merge
```
EntityInspector.vue:
├── Si entidad fue fusionada:
│   └── Botón "Deshacer fusión" → Confirmar → Restaura entidades originales

MergeHistoryPanel.vue (sidebar opcional):
├── Lista de fusiones recientes
├── Timestamp, entidades involucradas
└── [Deshacer] por cada fusión
```

**API**:
- `GET /api/projects/{id}/merge-history`
- `POST /api/projects/{id}/entities/{id}/undo-merge`

---

### Fase 5: Roadmap Features (Stilus/MeaningCloud)

| Feature | Días | Complejidad | Origen |
|---------|------|-------------|--------|
| **5.1** Gazetteer Expansion (+45K nombres) | 5-6 | Media | Stilus |
| **5.2** Verb Conjugator | 3-4 | Media | Stilus |
| **5.3** Reverse Dictionary (rimas) | 3-4 | Media | Stilus |
| **5.4** IPTC Topic Classification | 4-5 | Media | MeaningCloud |
| **5.5** Theme Clustering | 4-5 | Media | MeaningCloud |
| **5.6** Chapter Summaries (LLM) | 4-5 | Media | MeaningCloud |
| **5.7** Factual Inconsistencies (LLM) | 8-10 | Alta | Roadmap v1 |
| **5.8** Expanded Ontology (200+ classes) | 6-8 | Alta | MeaningCloud |

**Subtotal Fase 5**: 37-47 días

#### 5.1 Gazetteer Expansion
```
Scripts:
├── scripts/expand_gazetteer.py
│   ├── Fuentes: Wikipedia ES, Wikidata, INE
│   ├── Categorías: personas, lugares, organizaciones
│   └── Formato: JSON con variantes
└── Actualización anual automática

UI: Indicador en GazetteerPanel: "50,000 entidades"
```

#### 5.2 Verb Conjugator
```
ConjugatorPanel.vue (Tools → nuevo panel)
├── Input: verbo infinitivo
├── Output: tabla de conjugación completa
│   ├── Indicativo, Subjuntivo, Imperativo
│   ├── Todos los tiempos
│   └── Formas no personales
├── Destacar irregularidades
└── Botón "Copiar" por tiempo
```

**Backend**: `tools/conjugator.py` (usar mlconjug3 o similar)

#### 5.3 Reverse Dictionary
```
ReverseDictionaryPanel.vue (Tools → nuevo panel)
├── Buscar por terminación: *ción, *mente
├── Buscar por patrón: ?a?o (4 letras, a en 2ª, o en 4ª)
├── Resultados con definiciones
└── Útil para: rimas, cacofonías, juegos de palabras
```

**Backend**: `dictionaries/reverse_search.py`

#### 5.4-5.5 IPTC Classification + Theme Clustering
```
ThemeAnalysisPanel.vue (ResumenTab → nueva sección)
├── Clasificación IPTC del manuscrito:
│   ├── "Ficción > Novela negra > Thriller psicológico"
│   └── Confianza: 85%
├── Temas principales (clustering):
│   ├── Tema 1: "Venganza" (caps 1, 3, 7, 12) - 35%
│   ├── Tema 2: "Familia" (caps 2, 5, 8) - 28%
│   └── Tema 3: "Redención" (caps 9, 14, 15) - 22%
└── Visualización: word cloud o grafo
```

**Backend**:
- `analysis/topic_classification.py` (IPTC taxonomy)
- `analysis/theme_clustering.py` (LDA/BERTopic)

#### 5.6 Chapter Summaries (LLM)
```
ChapterInspector.vue (extender):
├── Sección "Resumen automático":
│   ├── Sinopsis generada por LLM (2-3 frases)
│   ├── Personajes principales del capítulo
│   ├── Eventos clave
│   └── Tono emocional
├── Botón "Regenerar" si no satisface
└── Cache de resúmenes generados
```

**Backend**: `llm/chapter_summarizer.py` (usar Ollama local)

#### 5.7 Factual Inconsistencies (LLM)
```
FactualInconsistenciesPanel.vue (AlertsTab → nuevo tipo de alerta)
├── Detectar contradicciones factuales:
│   ├── "Cap 3: María tiene 25 años / Cap 8: María cumple 30"
│   ├── "Cap 2: La casa es azul / Cap 6: La casa roja"
│   └── Severidad + confianza
├── LLM analiza pares de afirmaciones
├── Usuario confirma/descarta
└── Aprende de correcciones
```

**Backend**: `analysis/factual_consistency.py` (LLM-based)

#### 5.8 Expanded Ontology
```
Extender NER con subcategorías:
├── PERSON → Writer, Politician, Artist, Athlete, ...
├── LOCATION → City, Country, Building, Natural, ...
├── ORGANIZATION → Company, Government, NGO, ...
└── 200+ clases totales

UI: EntityInspector muestra subcategoría refinada
```

**Backend**: `nlp/ner_expanded.py` + modelo fine-tuned

---

### Fase 6: Deuda Técnica

| Área | Días | Descripción |
|------|------|-------------|
| **6.1** Tests unitarios backend | 8-10 | Cobertura >80% para módulos críticos |
| **6.2** Tests integración API | 4-5 | Tests E2E de endpoints |
| **6.3** Tests frontend | 5-6 | Vitest + Vue Test Utils |
| **6.4** Documentación API | 3-4 | OpenAPI/Swagger completo |
| **6.5** Logging estructurado | 2-3 | Structured logging, error tracking |
| **6.6** Performance profiling | 3-4 | Identificar bottlenecks, optimizar |
| **6.7** Refactoring deuda | 5-6 | Code smells, duplicación, complejidad |

**Subtotal Fase 6**: 30-38 días

#### 6.1-6.3 Tests
```
tests/
├── unit/
│   ├── test_entities.py
│   ├── test_nlp.py
│   ├── test_analysis.py
│   └── ...
├── integration/
│   ├── test_api_endpoints.py
│   └── test_pipeline.py
└── frontend/
    ├── components/
    └── stores/

Herramientas:
- Backend: pytest, pytest-cov, pytest-asyncio
- Frontend: Vitest, @vue/test-utils, MSW (mocks)
```

#### 6.4 Documentación API
```
Completar docstrings + FastAPI autodocs:
├── Todos los endpoints documentados
├── Schemas de request/response
├── Ejemplos de uso
└── Exportar OpenAPI spec

Herramientas: FastAPI autodocs, Redoc
```

#### 6.5 Logging Estructurado
```
Implementar:
├── structlog para Python
├── Niveles consistentes (DEBUG, INFO, WARNING, ERROR)
├── Contexto automático (user, project, request_id)
├── Rotación de logs
└── Error tracking (Sentry opcional, self-hosted)
```

#### 6.6 Performance Profiling
```
Áreas a optimizar:
├── Análisis NLP de documentos grandes (>100 páginas)
├── Carga inicial de CharacterSheet
├── Renderizado de grafos D3
├── Queries SQL lentas
└── Bundle size frontend

Herramientas: py-spy, cProfile, Lighthouse, webpack-bundle-analyzer
```

---

### Fase 7: Infraestructura

| Tarea | Días | Coste | Notas |
|-------|------|-------|-------|
| **7.1** Code signing Windows | 2-3 | ~$300/año | Certificado EV recomendado |
| **7.2** Code signing macOS | 2-3 | $99/año | Apple Developer Program |
| **7.3** CI/CD Pipeline | 4-5 | Gratis | GitHub Actions |
| **7.4** i18n (EN, CA) | 8-10 | - | vue-i18n + traducciones |
| **7.5** Landing Page | 5-6 | ~$20/año | Dominio + hosting estático |
| **7.6** Auto-updater | 3-4 | - | Tauri updater plugin |

**Subtotal Fase 7**: 24-31 días

#### 7.3 CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
jobs:
  test-backend:
    - pytest --cov
  test-frontend:
    - npm run test
  build:
    - Build Tauri (Windows, macOS, Linux)
  release:
    - Create GitHub Release
    - Upload artifacts
```

#### 7.4 i18n
```
Estructura:
├── frontend/src/locales/
│   ├── es.json (actual)
│   ├── en.json (traducir)
│   └── ca.json (traducir)
├── vue-i18n configurado
└── Backend: mensajes de error traducibles
```

---

### Resumen de Tiempo COMPLETO

| Fase | Días | Acumulado | Prioridad |
|------|------|-----------|-----------|
| Fase 0 (Backend + Shared) | 5.5-6.5 | 5.5-6.5 | 🎯 Crítica |
| **Mejoras módulos existentes** | **12-16** | **17.5-22.5** | 🎯 Crítica |
| Fase 1 (Quick Wins) | 5-6 | 22.5-28.5 | 🎯 Crítica |
| Fase 2 (Tabs existentes) | 19-23 | 41.5-51.5 | 🎯 Crítica |
| Fase 3 (Features Editoriales) | 21-26 | 62.5-77.5 | ✅ Alta |
| Fase 4 (Backend sin UI) | 10-14 | 72.5-91.5 | ✅ Alta |
| Fase 5 (Roadmap Stilus/MC) | 37-47 | 109.5-138.5 | ⚠️ Media |
| Fase 6 (Deuda Técnica) | 30-38 | 139.5-176.5 | ✅ Alta |
| Fase 7 (Infraestructura) | 24-31 | 163.5-207.5 | ⚠️ Media |

**Total estimado**: **164-208 días** (~33-42 semanas, ~8-10 meses)

> ⚠️ **Incluye 12-16 días de mejoras a módulos existentes** (ver sección "Análisis de Completitud")
> - Character Knowledge core: 5-7 días (CRÍTICO)
> - Voice Profiles completo: 3-4 días
> - Register por capítulo: 2-3 días
> - Speaker Attribution voice matching: 2-3 días

> **Nota**: Fases 6 y 7 pueden ejecutarse en paralelo con otras fases.
> **Recomendación**: Priorizar Fases 0-4 para MVP completo (~64-79 días, ~3-4 meses)

---

## Estructura de Archivos Final (Completa)

```
frontend/src/components/
├── shared/                        # CREAR (Fase 0)
│   ├── ConfidenceBadge.vue
│   ├── ChapterTimeline.vue
│   └── MethodVotingBar.vue
│
├── analysis/                      # CREAR (Fases 1-3)
│   ├── RegisterAnalysisPanel.vue
│   ├── FocalizationPanel.vue
│   ├── FocalizationDeclarator.vue
│   ├── InteractionsView.vue
│   ├── InteractionTimeline.vue
│   ├── InteractionHeatmap.vue
│   ├── KnowledgeNetwork.vue
│   ├── KnowledgeOutgoing.vue
│   ├── KnowledgeIncoming.vue
│   ├── KnowledgeAsymmetries.vue
│   ├── PacingPanel.vue            # Fase 3
│   ├── CharacterArcView.vue       # Fase 3
│   ├── ChronologyPanel.vue        # Fase 3
│   ├── SubplotPanel.vue           # Fase 3
│   ├── ThemeAnalysisPanel.vue     # Fase 5
│   └── FactualInconsistenciesPanel.vue  # Fase 5
│
├── coreference/                   # CREAR (Fase 1)
│   ├── CoreferenceVotingCard.vue
│   └── CoreferenceDetailsModal.vue
│
├── character/                     # CREAR (Fase 2)
│   ├── CharacterOverview.vue
│   ├── CharacterRelations.vue
│   └── CharacterAnalysis.vue
│
├── document/
│   ├── DialogueTooltip.vue        # Fase 2
│   └── GrammarHighlight.vue       # Fase 4
│
├── sidebar/
│   ├── DialoguesPanel.vue         # Fase 2
│   └── MergeHistoryPanel.vue      # Fase 4
│
├── tools/                         # CREAR (Fase 5)
│   ├── ConjugatorPanel.vue
│   └── ReverseDictionaryPanel.vue
│
├── settings/                      # CREAR (Fase 4)
│   └── GazetteerPanel.vue
│
├── alerts/                        # CREAR (Fase 2)
│   └── KnowledgeInconsistencyAlert.vue
│
├── inspector/
│   └── EntityInspector.vue        # MODIFICAR
│
├── workspace/
│   ├── StyleTab.vue               # MODIFICAR (3 TabPanels: Detectores, Reglas, Registro, Ritmo)
│   ├── RelationsTab.vue           # MODIFICAR (TabView: Relaciones, Interacciones)
│   ├── TimelineTab.vue            # MODIFICAR (añadir ChronologyPanel)
│   └── ResumenTab.vue             # MODIFICAR (añadir SubplotPanel, ThemeAnalysis)
│
├── BehaviorExpectations.vue       # MODIFICAR (expandir Voice)
├── CharacterSheet.vue             # REFACTORIZAR (TabView + lazy loading)
├── DocumentViewer.vue             # MODIFICAR (dialogue + grammar highlight)
├── MergeEntitiesDialog.vue        # MODIFICAR (coreference step)
├── ExportDialog.vue               # MODIFICAR (editorial report, style guide)
└── ChapterInspector.vue           # MODIFICAR (LLM summary)
```

### Backend (módulos nuevos)

```
src/narrative_assistant/
├── analysis/
│   ├── pacing.py                  # Fase 3 - Análisis de ritmo
│   ├── subplots.py                # Fase 3 - Tracking de subtramas
│   ├── topic_classification.py   # Fase 5 - IPTC
│   ├── theme_clustering.py       # Fase 5 - Clustering de temas
│   └── factual_consistency.py    # Fase 5 - LLM-based
│
├── temporal/
│   └── chronology_checker.py     # Fase 3 - Anacronismos
│
├── tools/
│   └── conjugator.py             # Fase 5 - Conjugador verbal
│
├── dictionaries/
│   └── reverse_search.py         # Fase 5 - Búsqueda inversa
│
├── llm/
│   └── chapter_summarizer.py     # Fase 5 - Resúmenes LLM
│
└── nlp/
    └── ner_expanded.py           # Fase 5 - Ontología 200+ clases
```

---

## APIs Backend Necesarias (Completas)

### Fase 0-2: Endpoints Core

| Endpoint | Método | Propósito | Fase |
|----------|--------|-----------|------|
| `/api/projects/{id}/characters/{charId}/voice-profile` | GET | Métricas de voz | 0 |
| `/api/projects/{id}/entities/{entityId}/coreference` | GET | Votación correferencia | 0 |
| `/api/projects/{id}/register-analysis` | GET | Análisis de registro | 0 |
| `/api/projects/{id}/focalization` | GET | Estado focalización | 0 |
| `/api/projects/{id}/focalization/declare` | POST | Declarar POV | 0 |
| `/api/projects/{id}/characters/{charId}/knowledge` | GET | Red de conocimiento | 0 |
| `/api/projects/{id}/chapters/{num}/dialogue-attributions` | GET | Atribución diálogos | 0 |
| `/api/projects/{id}/dialogue-attributions/{id}` | PATCH | Corregir atribución | 0 |
| `/api/projects/{id}/interactions` | GET | Patrones interacción | 0 |

### Fase 3: Endpoints Editoriales

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/projects/{id}/pacing-analysis` | GET | Análisis de ritmo |
| `/api/projects/{id}/characters/{charId}/arc` | GET | Arco del personaje |
| `/api/projects/{id}/chronology-analysis` | GET | Análisis cronológico |
| `/api/projects/{id}/subplots` | GET | Lista de subtramas |
| `/api/projects/{id}/export/editorial-report` | GET | Informe editorial |

### Fase 4: Endpoints Backend sin UI

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/projects/{id}/export/style-guide` | GET | Guía de estilo |
| `/api/gazetteer` | GET, POST | Listar/Añadir entidades |
| `/api/gazetteer/{id}` | PUT, DELETE | Editar/Eliminar entidad |
| `/api/projects/{id}/merge-history` | GET | Historial de fusiones |
| `/api/projects/{id}/entities/{id}/undo-merge` | POST | Deshacer fusión |

### Fase 5: Endpoints Roadmap

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/tools/conjugate/{verb}` | GET | Conjugar verbo |
| `/api/dictionary/reverse-search` | GET | Búsqueda por terminación |
| `/api/projects/{id}/topic-classification` | GET | Clasificación IPTC |
| `/api/projects/{id}/themes` | GET | Temas principales |
| `/api/projects/{id}/chapters/{num}/summary` | GET | Resumen LLM |
| `/api/projects/{id}/chapters/{num}/summary` | POST | Regenerar resumen |
| `/api/projects/{id}/factual-inconsistencies` | GET | Inconsistencias factuales |

### Endpoints existentes a reutilizar:
- `/api/projects/{id}/interactions` ✅
- `/api/projects/{id}/characters/{charId}/emotional-profile` ✅
- `/api/projects/{id}/export/review-report` ✅
- `/api/dictionary/lookup/{word}` ✅
- `/api/dictionary/synonyms/{word}` ✅

**Total endpoints nuevos**: ~25-30

---

## Criterios de Éxito

### Fase 0-2 (MVP Backend UI)
- [ ] Usuario puede ver métricas de voz en BehaviorExpectations
- [ ] Usuario puede ver por qué se fusionaron entidades
- [ ] Usuario puede analizar registro narrativo sin salir de StyleTab
- [ ] Usuario puede declarar y verificar focalización
- [ ] Usuario puede ver patrones de interacción en RelationsTab
- [ ] Usuario puede ver qué sabe cada personaje
- [ ] Usuario puede ver quién habla cada diálogo en el texto

### Fase 3 (Features Editoriales)
- [ ] Editor puede analizar pacing/ritmo del manuscrito
- [ ] Editor puede ver arcos de personaje con evolución
- [ ] Editor puede detectar anacronismos temporales
- [ ] Editor puede rastrear subtramas y su estado
- [ ] Editor puede generar informe editorial automático

### Fase 4 (Backend sin UI)
- [ ] Usuario puede exportar guía de estilo
- [ ] Usuario ve errores ortográficos/gramaticales subrayados en texto
- [ ] Usuario puede gestionar gazetteer manualmente
- [ ] Usuario puede deshacer fusiones de entidades

### Fase 5 (Roadmap)
- [ ] Gazetteer expandido a 50K+ entidades
- [ ] Usuario puede consultar conjugaciones verbales
- [ ] Usuario puede buscar palabras por terminación
- [ ] Manuscrito clasificado por taxonomía IPTC
- [ ] Temas principales identificados automáticamente
- [ ] Capítulos tienen resumen automático (LLM)
- [ ] Inconsistencias factuales detectadas (LLM)
- [ ] Entidades clasificadas en 200+ subcategorías

### Fase 6 (Deuda Técnica)
- [ ] Cobertura de tests >80%
- [ ] API documentada con OpenAPI
- [ ] Logging estructurado implementado
- [ ] Performance optimizada (<30s para 100 páginas)

### Fase 7 (Infraestructura)
- [ ] Instaladores firmados (Windows + macOS)
- [ ] CI/CD funcionando en GitHub Actions
- [ ] UI disponible en ES, EN, CA
- [ ] Landing page publicada
- [ ] Auto-updater funcionando

---

## Métricas Objetivo Final

| Métrica | Actual (v0.2.9) | Post-Fase 4 | Post-Fase 7 |
|---------|-----------------|-------------|-------------|
| Detectores | 14 | 18 | 25 |
| Endpoints API | 48+ | 65+ | 85+ |
| Componentes Vue | 54 | 75+ | 95+ |
| Gazetteer | ~5,000 | ~5,000 | 50,000+ |
| Test coverage | ~10% | 50% | 80%+ |
| Idiomas UI | 1 (ES) | 1 (ES) | 3 (ES, EN, CA) |
| Tiempo análisis 100pp | ~30s | ~25s | ~20s |

---

*Documento creado: 2026-01-26*
*Actualizado: 2026-01-26 (plan completo con todas las features)*
