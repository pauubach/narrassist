# Narrative Assistant - Documentación

**Última actualización**: 2026-01-23
**Estado**: MVP completo, v1.0.1

---

## Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[PROJECT_STATUS.md](PROJECT_STATUS.md)** | Estado actual del proyecto, inventario de módulos |
| **[ROADMAP_V2.md](ROADMAP_V2.md)** | Plan de futuras funcionalidades |
| **[CLAUDE.md](../CLAUDE.md)** | Instrucciones para Claude Code |

---

## Estructura de la Documentación

```
docs/
├── PROJECT_STATUS.md          # ★ Estado actual del proyecto
├── ROADMAP_V2.md              # ★ Plan de futuro
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
└── _archive/                  # Documentos históricos (no mantener)
    ├── steps/                 # Especificaciones de implementación originales
    ├── research/              # Investigación
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
1. [ROADMAP_V2.md](ROADMAP_V2.md) - Ver qué falta por hacer
2. [02-architecture/database-schema.md](02-architecture/database-schema.md) - Schema BD
3. [api-reference/](api-reference/) - APIs disponibles

### Para entender el NLP
1. [COREFERENCE_RESOLUTION.md](COREFERENCE_RESOLUTION.md) - Sistema de correferencias
2. [01-theory/](01-theory/) - Heurísticas narrativas
3. [api-reference/backend-nlp.md](api-reference/backend-nlp.md) - APIs NLP

---

## Estadísticas del Proyecto

- **Backend**: 103 archivos Python, ~49,000 LoC
- **Frontend**: 53 componentes Vue, 7 stores Pinia, ~30,000 LoC
- **API**: 39 endpoints FastAPI
- **Tests**: 612+ passing
- **Total**: ~79,000 LoC

---

## Archivo

Los documentos en `_archive/` son históricos y no se mantienen activamente:
- `steps/` - Especificaciones originales de implementación (el código es ahora la fuente de verdad)
- `research/` - Documentos de investigación
- `obsolete/` - Documentos supersedidos por versiones más recientes

---

## Enlaces Rápidos

- [Estado del Proyecto](PROJECT_STATUS.md)
- [Roadmap](ROADMAP_V2.md)
- [Instrucciones para Claude](../CLAUDE.md)
- [Endpoints HTTP](api-reference/http-endpoints.md)
- [Schema de BD](02-architecture/database-schema.md)
