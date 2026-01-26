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
| `nlp/coreference_resolver.py` | ⚠️ Sin votación multi-método | Implementar voting system |
| `voice/register.py` | ⚠️ Clasifica pero NO detecta cambios | Añadir `detect_register_changes()` |

**Tiempo estimado backend**: 5-7 días adicionales

---

## Fase 1: Quick Wins (Extender Componentes Existentes)

### 1.1 Voice Profiles → Extender BehaviorExpectations.vue

**Ubicación**: `frontend/src/components/BehaviorExpectations.vue`

**Estado actual**: ⚠️ NO tiene sección "Speech Patterns" - debe crearse completa

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

### 2.4 Knowledge Tracking → Añadir en CharacterSheet.vue

**Ubicación**: `frontend/src/components/CharacterSheet.vue`

**Estado actual**: BehaviorExpectations + EmotionalAnalysis

> ⚠️ **Validación UX**: CharacterSheet ya es largo. Implementar **versión compacta**.

**Cambios** (después de EmotionalAnalysis, línea ~240):
```
CharacterSheet.vue
├── ... secciones existentes ...
├── BehaviorExpectations ✓
├── EmotionalAnalysis ✓
└── KnowledgeSummary  ← AÑADIR (VERSIÓN COMPACTA)
    ├── Resumen: "Sabe sobre 5 personajes | 3 lo conocen | 2 asimetrías"
    ├── Badge de alertas si hay asimetrías críticas
    └── [Ver red completa] → Abre KnowledgeNetworkModal
```

**Modal KnowledgeNetworkModal.vue** (contenido completo):
```
KnowledgeNetworkModal.vue
├── Header: "Red de Conocimiento de {personaje}"
├── Tabs:
│   ├── "Lo que sabe" - Lista de otros personajes
│   │   ├── María: Opinión positiva, 23 menciones
│   │   │   ├── Sabe que es su hermana
│   │   │   ├── Sabe su secreto
│   │   │   └── Intención: protegerla
│   │   └── Pedro: Opinión negativa, 8 menciones
│   │
│   ├── "Quién lo conoce" - Inverso
│   │
│   └── "Asimetrías" - Alertas
│       └── ⚠ María sabe más sobre Juan que viceversa
│
└── Visualización opcional: Grafo D3 (colapsable)
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

**Esfuerzo**: 3-4 días

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

## Orden de Implementación

| Fase | Feature | Días | Dependencias |
|------|---------|------|--------------|
| **1.1** | Voice Profiles (expandir BehaviorExpectations) | 2 | Ninguna |
| **1.2** | Coreference en EntityInspector | 2 | shared/ConfidenceBadge |
| **1.3** | Coreference en MergeDialog | 1 | 1.2 |
| **2.1** | Register Analysis en StyleTab | 3 | shared/ChapterTimeline |
| **2.2** | Focalization en StyleTab | 3 | shared/ChapterTimeline |
| **2.3** | Interactions en RelationsTab | 4 | shared/ChapterTimeline |
| **2.4** | Knowledge en CharacterSheet | 4 | Ninguna |
| **2.5** | Speaker Attribution en DocumentViewer | 5 | Ninguna |

**Total estimado**: 24 días (~5 semanas)

---

## Estructura de Archivos Final

```
frontend/src/components/
├── shared/                        # CREAR
│   ├── ConfidenceBadge.vue
│   ├── ChapterTimeline.vue
│   └── MethodVotingBar.vue
│
├── analysis/                      # CREAR
│   ├── RegisterAnalysisPanel.vue
│   ├── FocalizationPanel.vue
│   ├── FocalizationDeclarator.vue
│   ├── InteractionsView.vue
│   ├── InteractionTimeline.vue
│   ├── InteractionHeatmap.vue
│   ├── KnowledgeNetwork.vue
│   ├── KnowledgeOutgoing.vue
│   ├── KnowledgeIncoming.vue
│   └── KnowledgeAsymmetries.vue
│
├── coreference/                   # CREAR
│   ├── CoreferenceVotingCard.vue
│   └── CoreferenceDetailsModal.vue
│
├── document/
│   └── DialogueOverlay.vue        # CREAR
│
├── sidebar/
│   └── DialoguesPanel.vue         # CREAR
│
├── inspector/
│   └── EntityInspector.vue        # MODIFICAR
│
├── workspace/
│   ├── StyleTab.vue               # MODIFICAR (2 TabPanels)
│   └── RelationsTab.vue           # MODIFICAR (toggle vista)
│
├── BehaviorExpectations.vue       # MODIFICAR (expandir Voice)
├── CharacterSheet.vue             # MODIFICAR (añadir Knowledge)
├── DocumentViewer.vue             # MODIFICAR (dialogue overlay)
└── MergeEntitiesDialog.vue        # MODIFICAR (coreference step)
```

---

## APIs Backend Necesarias

### Nuevos endpoints:

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/projects/{id}/characters/{charId}/voice-profile` | GET | Métricas de voz |
| `/api/projects/{id}/entities/{entityId}/coreference` | GET | Votación correferencia |
| `/api/projects/{id}/register-analysis` | GET | Análisis de registro |
| `/api/projects/{id}/focalization` | GET | Estado focalización |
| `/api/projects/{id}/focalization/declare` | POST | Declarar POV |
| `/api/projects/{id}/characters/{charId}/knowledge` | GET | Red de conocimiento |
| `/api/projects/{id}/chapters/{num}/dialogue-attributions` | GET | Atribución diálogos |
| `/api/projects/{id}/dialogue-attributions/{id}` | PATCH | Corregir atribución |

### Endpoints existentes a usar:
- `/api/projects/{id}/interactions` (ya existe)
- `/api/projects/{id}/characters/{charId}/emotional-profile` (ya existe)

---

## Criterios de Éxito

- [ ] Usuario puede ver métricas de voz en BehaviorExpectations
- [ ] Usuario puede ver por qué se fusionaron entidades
- [ ] Usuario puede analizar registro narrativo sin salir de StyleTab
- [ ] Usuario puede declarar y verificar focalización
- [ ] Usuario puede ver patrones de interacción en RelationsTab
- [ ] Usuario puede ver qué sabe cada personaje
- [ ] Usuario puede ver quién habla cada diálogo en el texto

---

*Documento creado: 2026-01-26*
