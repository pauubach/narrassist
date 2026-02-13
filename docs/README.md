# Narrative Assistant - Documentacion

**Ultima actualizacion**: 2026-02-13
**Version**: 0.9.4

---

## Documentacion Principal

| Documento | Descripcion |
|-----------|-------------|
| **[PROJECT_STATUS.md](PROJECT_STATUS.md)** | Estado actual del proyecto, inventario de modulos |
| **[IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)** | Plan de mejora por sprints (S0-S6+) |
| **[ROADMAP.md](ROADMAP.md)** | Trabajo pendiente y objetivos futuros |
| **[CHANGELOG.md](CHANGELOG.md)** | Historial de cambios por version |
| **[CLAUDE.md](../CLAUDE.md)** | Instrucciones para Claude Code |

---

## Estructura de la Documentacion

```
docs/
├── PROJECT_STATUS.md              # Estado actual del proyecto
├── IMPROVEMENT_PLAN.md            # Plan de mejora por sprints (S0-S6+)
├── ROADMAP.md                     # Trabajo futuro
├── CHANGELOG.md                   # Historial de versiones
├── README.md                      # Este archivo
│
├── 00-overview/                   # Vision general del proyecto
│   ├── goals-and-scope.md         # Objetivos y alcance
│   ├── mvp-definition.md          # Definicion del MVP
│   └── corrections-and-risks.md   # Limitaciones NLP conocidas
│
├── 01-theory/                     # Heuristicas narrativas (fundamentos teoricos)
│   ├── heuristics-h1-world.md     # H1: Coherencia del mundo
│   ├── heuristics-h2-characters.md  # H2: Personajes
│   ├── heuristics-h3-structure.md   # H3: Estructura
│   ├── heuristics-h4-voice.md       # H4: Voz y estilo
│   ├── heuristics-h5-focalization.md # H5: Focalizacion
│   └── heuristics-h6-information.md  # H6: Informacion
│
├── 02-architecture/               # Arquitectura tecnica
│   ├── database-schema.md         # Schema SQLite
│   ├── document-processing.md     # Pipeline de procesamiento
│   ├── SECURITY.md                # Seguridad y aislamiento
│   ├── data-model.md              # Modelo de datos
│   ├── enums-reference.md         # Referencia de enums
│   ├── extension-points.md        # Puntos de extension
│   ├── history-system.md          # Sistema de historial
│   ├── position-synchronization.md # Sincronizacion de posiciones
│   └── progressive-analysis.md    # Analisis progresivo
│
├── 04-references/                 # Referencias
│   └── glossary.md                # Glosario de terminos
│
├── api-reference/                 # Documentacion de API
│   ├── backend-alerts.md          # Modulo de alertas
│   ├── backend-core.md            # Modulo core
│   ├── backend-entities.md        # Modulo de entidades
│   ├── backend-nlp.md             # Modulo NLP
│   ├── backend-persistence.md     # Modulo de persistencia
│   └── frontend-stores.md         # Stores de Vue/Pinia
│
├── research/                      # Investigacion y analisis (referencia futura)
│   ├── COMPETITIVE_ANALYSIS_2025.md      # Analisis competitivo
│   ├── FEATURE_ANALYSIS_CORRECTORS.md    # Features correctores vs escritores
│   ├── DOCUMENT_TYPE_FEATURES.md         # Matriz tipos documento-features
│   ├── AGE_READABILITY_IMPROVEMENTS.md   # Mejoras legibilidad infantil
│   ├── ALERTS_INTEGRATION_MAP.md         # Mapa integracion alertas
│   ├── UI_REDESIGN_PROPOSAL.md           # Propuesta rediseno UI
│   ├── PLAN_DETECCION_ERRORES_ESTRUCTURALES.md  # Errores estructurales
│   ├── ESTUDIO_REDUNDANCIA_SEMANTICA.md  # Redundancia semantica
│   └── ESTUDIO_OPTIMIZACION_RECURSOS.md  # Optimizacion recursos
│
├── ux/                            # Documentos de UX
│   ├── UX_REVIEW_SETTINGS.md                      # Review: Settings
│   ├── UX_REVIEW_DOCUMENT_TYPE_SELECTOR.md         # Review: Selector tipo doc
│   ├── DELIBERATION_SESSION_DOCUMENT_CLASSIFICATION.md  # Clasificacion
│   └── EXPERT_INDICATORS_COMPILATION.md            # Indicadores expertos
│
├── testing/                       # Testing y QA
│   └── MACOS_TESTING_CHECKLIST.md # Checklist macOS
│
├── BUILD_AND_DEPLOY.md            # Instrucciones de build
├── PYTHON_EMBED.md                # Python embebido (Tauri)
├── COREFERENCE_RESOLUTION.md      # Sistema de correferencias
├── LICENSING_PRODUCTION_PLAN.md   # Plan produccion licencias
├── AUDIT_INDEX.md                 # Índice de documentos de auditoría
├── ARCHITECTURE_AUDIT_2026-02.md  # Auditoria arquitectonica
├── WCAG_COLOR_AUDIT.md            # Auditoria accesibilidad
├── OPTIMIZATION_STATUS.md         # Estado optimizaciones
│
└── _archive/                      # Documentos historicos (no mantener)
    ├── audits/                    # Auditorias y reviews de versiones antiguas
    ├── planning/                  # Planes de implementacion archivados
    ├── steps/                     # Especificaciones originales (phases 0-10)
    ├── research/                  # Investigacion historica
    ├── obsolete/                  # Docs supersedidos
    └── 05-ui-design/              # Diseno UI historico
```

---

## Flujo de Lectura Recomendado

### Para nuevos desarrolladores
1. [00-overview/goals-and-scope.md](00-overview/goals-and-scope.md) - Entender el proyecto
2. [00-overview/corrections-and-risks.md](00-overview/corrections-and-risks.md) - Limitaciones NLP
3. [02-architecture/database-schema.md](02-architecture/database-schema.md) - Schema BD
4. [PROJECT_STATUS.md](PROJECT_STATUS.md) - Estado actual

### Para implementar features
1. [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) - Sprints y features planificadas
2. [ROADMAP.md](ROADMAP.md) - Vision general de trabajo pendiente
3. [02-architecture/database-schema.md](02-architecture/database-schema.md) - Schema BD
4. [api-reference/](api-reference/) - APIs disponibles

### Para entender el NLP
1. [COREFERENCE_RESOLUTION.md](COREFERENCE_RESOLUTION.md) - Sistema de correferencias
2. [01-theory/](01-theory/) - Heuristicas narrativas
3. [api-reference/backend-nlp.md](api-reference/backend-nlp.md) - APIs NLP

---

## Archivo

Los documentos en `_archive/` son historicos y no se mantienen activamente:

- `audits/` - Auditorias y reviews de versiones antiguas (v0.3.34, v0.4.30, etc.)
- `planning/` - Planes de implementacion anteriores (IMPLEMENTATION_PLAN, ROADMAP_V2, etc.)
- `steps/` - Especificaciones originales de implementacion (phases 0-10)
- `research/` - Documentos de investigacion historica
- `obsolete/` - Docs supersedidos
- `05-ui-design/` - Propuestas de diseno UI historicas
