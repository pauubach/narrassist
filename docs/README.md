# Narrative Assistant - Documentación

**Última actualización**: 2026-01-23
**Estado**: MVP completo (Fases 0-14)

---

## Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[PROJECT_STATUS.md](PROJECT_STATUS.md)** | Estado actual del proyecto, inventario de módulos, métricas |
| **[steps/README.md](steps/README.md)** | Índice de todas las fases de implementación (0-14) |
| **[CLAUDE.md](../CLAUDE.md)** | Instrucciones para Claude Code |

---

## Estructura de la Documentación

```
docs/
├── PROJECT_STATUS.md          # ★ Estado actual del proyecto
├── README.md                  # Este archivo
│
├── 00-overview/               # Visión general del proyecto
│   ├── README.md              # Propuesta de valor, trazabilidad
│   ├── goals-and-scope.md     # Objetivos y alcance
│   ├── mvp-definition.md      # Definición del MVP
│   └── corrections-and-risks.md  # Limitaciones NLP conocidas
│
├── 01-theory/                 # Heurísticas narrativas
│   ├── README.md              # Índice de heurísticas
│   ├── heuristics-h1-world.md    # H1: Coherencia del mundo
│   ├── heuristics-h2-characters.md  # H2: Personajes
│   ├── heuristics-h3-structure.md   # H3: Estructura
│   ├── heuristics-h4-voice.md       # H4: Voz y estilo
│   ├── heuristics-h5-focalization.md # H5: Focalización
│   └── heuristics-h6-information.md  # H6: Información
│
├── 02-architecture/           # Arquitectura técnica
│   ├── README.md              # Diagrama de capas, stack
│   ├── data-model.md          # Modelo de datos
│   ├── database-schema.md     # Schema SQLite
│   ├── enums-reference.md     # Valores de enums
│   ├── document-processing.md # Pipeline de procesamiento
│   ├── progressive-analysis.md # Análisis en tiempo real
│   ├── history-system.md      # Sistema de historial
│   ├── position-synchronization.md # Sincronización de posiciones
│   ├── extension-points.md    # Puntos de extensión
│   ├── SETUP.md               # Instalación
│   └── SECURITY.md            # Seguridad y aislamiento
│
├── 04-references/             # Referencias
│   ├── README.md              # Bibliografía
│   └── glossary.md            # Glosario de términos
│
├── 05-ui-design/              # Diseño de UI
│   ├── README.md              # Resumen del diseño
│   ├── UI_DESIGN_PROPOSAL.md  # Propuesta completa
│   ├── UI_UX_CORRECTIONS.md   # Correcciones UX
│   └── BACKEND_GAPS_ANALYSIS.md # Análisis de gaps
│
├── api-reference/             # Documentación de API
│   ├── README.md              # Índice
│   ├── http-endpoints.md      # Endpoints FastAPI
│   ├── backend-core.md        # Módulos core
│   ├── backend-entities.md    # Módulos de entidades
│   ├── backend-nlp.md         # Módulos NLP
│   ├── backend-persistence.md # Persistencia
│   ├── backend-alerts.md      # Sistema de alertas
│   └── frontend-stores.md     # Stores de Vue/Pinia
│
├── steps/                     # Especificaciones de implementación
│   ├── README.md              # ★ Índice de fases (0-14)
│   ├── phase-0/               # Fase 0: Fundamentos
│   ├── phase-1/               # Fase 1: Infraestructura
│   ├── phase-2/               # Fase 2: Entidades y Atributos
│   ├── phase-3/               # Fase 3: Grafías y Repeticiones
│   ├── phase-4/               # Fase 4: Temporalidad
│   ├── phase-5/               # Fase 5: Voz y Registro
│   ├── phase-6/               # Fase 6: Focalización
│   ├── phase-7/               # Fase 7: Integración y Exportación
│   ├── phase-8/               # Fase 8: Análisis Emocional
│   ├── phase-9/               # Fase 9: Grafo de Relaciones
│   └── phase-10/              # Fase 10: Análisis Narrativo Avanzado (futuro)
│
├── research/                  # Investigación
│   └── ESTADO_DEL_ARTE_UI_UX_2025.md
│
└── [Documentos adicionales]
    ├── API_REFERENCE.md       # Referencia rápida de APIs
    ├── BUILD_AND_DEPLOY.md    # Instrucciones de build
    ├── COREFERENCE_RESOLUTION.md  # Sistema de correferencias
    ├── TESTING_STRATEGY.md    # Estrategia de tests
    └── spanish-dialogue-pattern-review.md  # Análisis de patrones de diálogo
```

---

## Flujo de Lectura Recomendado

### Para nuevos desarrolladores
1. [00-overview/README.md](00-overview/README.md) - Entender el proyecto
2. [00-overview/corrections-and-risks.md](00-overview/corrections-and-risks.md) - Limitaciones NLP
3. [02-architecture/README.md](02-architecture/README.md) - Arquitectura
4. [PROJECT_STATUS.md](PROJECT_STATUS.md) - Estado actual

### Para implementar features
1. [steps/README.md](steps/README.md) - Ver estado de implementación
2. [02-architecture/enums-reference.md](02-architecture/enums-reference.md) - Valores de enums
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

## Enlaces Rápidos

- [Estado del Proyecto](PROJECT_STATUS.md)
- [Instrucciones para Claude](../CLAUDE.md)
- [Endpoints HTTP](api-reference/http-endpoints.md)
- [Schema de BD](02-architecture/database-schema.md)
