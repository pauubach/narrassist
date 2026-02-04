# Narrative Assistant - Documentación

**Última actualización**: 2026-02-04
**Estado**: MVP completo, v0.3.37

---

## Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[PROJECT_STATUS.md](PROJECT_STATUS.md)** | Estado actual del proyecto, inventario de módulos |
| **[ROADMAP.md](ROADMAP.md)** | Trabajo pendiente y objetivos futuros |
| **[CHANGELOG.md](CHANGELOG.md)** | Historial de cambios por versión |
| **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** | Plan de implementación detallado por fases |
| **[CLAUDE.md](../CLAUDE.md)** | Instrucciones para Claude Code |
| **[EXPERT_REVIEW_FINDINGS.md](../EXPERT_REVIEW_FINDINGS.md)** | Hallazgos de revisión multi-experto y soluciones priorizadas |

---

## Estructura de la Documentación

```
docs/
├── PROJECT_STATUS.md          # ★ Estado actual del proyecto
├── ROADMAP.md                 # ★ Trabajo futuro
├── CHANGELOG.md               # ★ Historial de versiones
├── IMPLEMENTATION_PLAN.md     # ★ Plan de implementación por fases
├── README.md                  # Este archivo
│
├── 00-overview/               # Visión general del proyecto
│   ├── goals-and-scope.md     # Objetivos y alcance
│   ├── mvp-definition.md      # Definición del MVP
│   └── corrections-and-risks.md  # Limitaciones NLP conocidas
│
├── 01-theory/                 # Heurísticas narrativas (fundamentos teóricos)
│   ├── heuristics-h1-world.md    # H1: Coherencia del mundo
│   ├── heuristics-h2-characters.md  # H2: Personajes
│   ├── heuristics-h3-structure.md   # H3: Estructura
│   ├── heuristics-h4-voice.md       # H4: Voz y estilo
│   ├── heuristics-h5-focalization.md # H5: Focalización
│   └── heuristics-h6-information.md  # H6: Información
│
├── 02-architecture/           # Arquitectura técnica
│   ├── database-schema.md     # Schema SQLite
│   ├── document-processing.md # Pipeline de procesamiento
│   ├── SECURITY.md            # Seguridad y aislamiento
│   ├── LICENSING.md           # Sistema de licencias
│   └── ...                    # Otros docs de arquitectura
│
├── 04-references/             # Referencias
│   └── glossary.md            # Glosario de términos
│
├── api-reference/             # Documentación de API
│   ├── http-endpoints.md      # Endpoints FastAPI
│   ├── backend-*.md           # Módulos backend
│   └── frontend-stores.md     # Stores de Vue/Pinia
│
├── BUILD_AND_DEPLOY.md        # Instrucciones de build
├── COREFERENCE_RESOLUTION.md  # Sistema de correferencias
│
├── research/                  # Investigación y análisis
│   ├── ROADMAP_STATUS.md      # Estado detallado del roadmap
│   ├── AUDIT_DECISIONS_AND_ROADMAP.md  # Decisiones de auditoría
│   ├── XFAIL_RESEARCH_ROADMAP.md  # Roadmap de I+D
│   └── COMPETITIVE_ANALYSIS_2025.md  # Análisis competitivo
│
├── ux/                        # Documentos de UX
│   └── *.md                   # Revisiones UX y deliberaciones
│
└── _archive/                  # Documentos históricos (no mantener)
    ├── planning/              # Planes de implementación archivados
    ├── steps/                 # Especificaciones originales
    └── obsolete/              # Docs supersedidos
```

---

## Flujo de Lectura Recomendado

### Para nuevos desarrolladores
1. [00-overview/goals-and-scope.md](00-overview/goals-and-scope.md) - Entender el proyecto
2. [00-overview/corrections-and-risks.md](00-overview/corrections-and-risks.md) - Limitaciones NLP
3. [02-architecture/README.md](02-architecture/README.md) - Arquitectura
4. [PROJECT_STATUS.md](PROJECT_STATUS.md) - Estado actual

### Para implementar features
1. [ROADMAP.md](ROADMAP.md) - Ver qué falta por hacer
2. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Plan detallado por fases
3. [02-architecture/database-schema.md](02-architecture/database-schema.md) - Schema BD
4. [api-reference/](api-reference/) - APIs disponibles

### Para entender el NLP
1. [COREFERENCE_RESOLUTION.md](COREFERENCE_RESOLUTION.md) - Sistema de correferencias
2. [01-theory/](01-theory/) - Heurísticas narrativas
3. [api-reference/backend-nlp.md](api-reference/backend-nlp.md) - APIs NLP

---

## Estadísticas del Proyecto (v0.3.37)

- **Backend**: 177 archivos Python, ~80,000+ LoC
- **Frontend**: 83 componentes Vue, 13 stores Pinia, ~60,000+ LoC
- **API**: 170 endpoints FastAPI
- **Tests**: 966+ passing
- **Detectores**: 14 detectores editoriales
- **Total**: ~140,000+ LoC

---

## Archivo

Los documentos en `_archive/` son históricos y no se mantienen activamente:
- `planning/` - Planes de implementación anteriores (UI_IMPLEMENTATION_PLAN, ROADMAP_V2)
- `steps/` - Especificaciones originales de implementación
- `research/` - Documentos de investigación
- `obsolete/` - Documentos supersedidos

---

## Enlaces Rápidos

- [Estado del Proyecto](PROJECT_STATUS.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)
- [Plan de Implementación](IMPLEMENTATION_PLAN.md)
- [Instrucciones para Claude](../CLAUDE.md)
- [Endpoints HTTP](api-reference/http-endpoints.md)
- [Schema de BD](02-architecture/database-schema.md)
