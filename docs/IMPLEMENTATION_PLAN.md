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

## Fase 0: Estabilización de Fundamentos (10-14 días)

> **Objetivo**: Completar módulos backend parcialmente implementados antes de crear UIs

### 0.1 Completar Character Knowledge (5-7 días) 🚨 CRÍTICO

**Estado actual**: 60% - Core `_extract_knowledge_facts()` está vacío

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

### 0.2 Completar Voice Profiles (2-3 días)

**Estado actual**: 70% - API no devuelve todas las métricas

**Implementar**:
- Extender API para devolver `characteristic_words`, `top_fillers`, `punctuation_patterns`
- Añadir endpoint de comparación: `GET /api/projects/{id}/characters/compare/{char1}/{char2}`

**Archivo**: `src/narrative_assistant/voice/profiles.py`

### 0.3 Completar Register Analysis (1-2 días)

**Estado actual**: 75% - Solo analiza fragmentos sueltos

**Implementar**:
- `analyze_register_by_chapter()` con distribución + severidad de cambios
- Estadísticas agregadas (% formal, neutral, coloquial por manuscrito)

**Archivo**: `src/narrative_assistant/voice/register.py`

### 0.4 Crear Endpoints API Faltantes (2-3 días)

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/projects/{id}/characters/{charId}/voice-profile` | GET | Perfil de voz completo |
| `/api/projects/{id}/entities/{entityId}/coreference` | GET | Votación correferencia |
| `/api/projects/{id}/register-analysis` | GET | Análisis de registro |
| `/api/projects/{id}/focalization` | GET | Estado focalización |
| `/api/projects/{id}/focalization/declare` | POST | Declarar POV |
| `/api/projects/{id}/characters/{charId}/knowledge` | GET | Red de conocimiento |
| `/api/projects/{id}/chapters/{num}/dialogue-attributions` | GET | Atribución diálogos |
| `/api/projects/{id}/interactions` | GET | Patrones interacción |

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

| Fase | Días | Acumulado | Prioridad |
|------|------|-----------|-----------|
| 0: Estabilización | 10-14 | 10-14 | 🎯 Crítica |
| 0.5: Multi-Método | 4-5 | 14-19 | 🎯 Crítica |
| 1: Shared Components | 2-3 | 16-22 | 🎯 Crítica |
| 2: Quick Wins | 5-6 | 21-28 | 🎯 Crítica |
| 3: Extender Tabs | 19-23 | 40-51 | ✅ Alta |
| 4: Editoriales | 21-26 | 61-77 | ✅ Alta |
| 5: Roadmap | 37-47 | 98-124 | ⚠️ Media |
| 6: Deuda Técnica | 30-38 | 128-162 | ⚠️ Media |
| 7: Infraestructura | 24-31 | 152-193 | ⚠️ Media |

**MVP mejorado (Fases 0-3)**: ~40-51 días (~2-2.5 meses)
**Producto completo (Fases 0-7)**: ~152-193 días (~7-10 meses)

---

## Criterios de Éxito por Fase

### Fases 0-2 (MVP Backend-UI)

- [ ] Character Knowledge extrae hechos correctamente
- [ ] Usuario puede ver métricas de voz completas
- [ ] Usuario puede ver por qué se fusionaron entidades
- [ ] Todos los métodos NLP configurables en Settings

### Fase 3 (Tabs Extendidas)

- [ ] Usuario puede analizar registro narrativo
- [ ] Usuario puede declarar y verificar focalización
- [ ] Usuario puede ver patrones de interacción
- [ ] Usuario puede ver qué sabe cada personaje
- [ ] Usuario puede ver quién habla cada diálogo

### Fases 4-5 (Features Avanzadas)

- [ ] Editor puede analizar pacing del manuscrito
- [ ] Editor puede ver arcos de personaje
- [ ] Editor puede detectar anacronismos
- [ ] Gazetteer expandido a 50K+ entidades

---

*Documento creado: 2026-01-26*
*Basado en síntesis de: Arquitecto, PM, Tech Writer, Product Manager*
