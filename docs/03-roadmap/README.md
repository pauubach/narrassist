# Roadmap de Implementación

[← Volver al índice principal](../../README.md)

---

## Visión General

El desarrollo sigue un enfoque incremental con validación entre fases. El MVP incluye 12 capacidades distribuidas en las fases 0-2, con mejoras progresivas en fases posteriores.

---

## Estrategia de Priorización

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRIORIDAD DE IMPLEMENTACIÓN                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  P0 (CRÍTICO - Sin esto no hay producto):                                   │
│  ├── STEP 0.1-0.3: Entorno + BD                                            │
│  ├── STEP 1.1-1.4: Parser + NER + Diálogos                                 │
│  ├── STEP 2.1-2.4: Coref + Fusión + Atributos                              │
│  └── STEP 7.1: Motor de Alertas (centraliza todos los hallazgos)          │
│                                                                              │
│  P1 (ALTO VALOR - Diferenciales claros):                                    │
│  ├── STEP 3.1: Variantes de grafía (error común, fácil de corregir)       │
│  ├── STEP 7.3: Hoja de estilo (valor inmediato para correctores)          │
│  └── STEP 7.4: CLI (permite usar sin UI)                                   │
│                                                                              │
│  P2 (VALOR MEDIO - Añadir tras validación):                                │
│  ├── STEP 3.2-3.3: Repeticiones                                            │
│  ├── STEP 5.1-5.4: Voz y registro                                          │
│  └── STEP 4.1-4.3: Timeline                                                │
│                                                                              │
│  P3 (EXPERIMENTAL - Alta tasa de error esperada):                          │
│  ├── STEP 6.1-6.2: Focalización (>50% error por pro-drop)                 │
│  └── [FUTURO] Tauri UI (evaluar solo si CLI valida demanda)               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Estimación de Horas por Prioridad

| Prioridad | Horas estimadas | Tipo |
|-----------|-----------------|------|
| P0 | ~43-64h | OBLIGATORIO |
| P1 | ~14-22h | Recomendado para MVP |
| P2 | ~42-60h | Post-validación |
| P3 | ~36-50h | Opcional/experimental |
| **Total** | **135-196h** | — |

---

## Fases de Desarrollo

| Fase | Nombre | Contenido principal |
|------|--------|---------------------|
| [Fase 0](./phase-0-setup.md) | Fundamentos | Entorno, proyecto, BD |
| [Fase 1](./phase-1-mvp.md) | MVP Core | Parser, NER, diálogos, alertas básicas |
| [Fases 2-7](./phases-2-7-post-mvp.md) | Post-MVP | Correferencia mejorada, voz, focalización, género |

---

## Flujo de Dependencias entre Fases

```
FASE 0: Fundamentos
    │
    ▼
FASE 1: MVP ──────────────────────────────────────────────────────►
    │
    ├── Entidades + validación ──► Fase 2: Correferencia mejorada
    │                                      Sugerencias de atributos
    │
    ├── Marcadores temporales ───► Fase 2: Timeline asistido
    │                              Fase 4: Timeline automático (si viable)
    │
    ├── Estadísticas diálogo ────► Fase 2: Alertas de voz
    │                              Fase 3: Perfiles completos
    │
    ├── Métricas complejidad ────► Fase 2: Alertas de registro
    │                              Fase 3: Estilo indirecto libre
    │
    ├── Repeticiones verbatim ───► Fase 2: Paráfrasis semántica
    │
    └── Hoja de estilo ──────────► (se enriquece en cada fase)

Fase 2 + Fase 3 ──► Fase 4: Coherencia temporal/causal (alto riesgo)

Fase 4 + recursos léxicos ──► Fase 5: Estructura + anacronismos

Fase 5 + corpus por género ──► Fase 6: Calibración por género

Fase 6 + investigación ──► Fase 7: Temas (condicional)
```

---

## Hitos de Validación

Ver [Validación entre Fases](./validation-milestones.md) para los criterios específicos.

| Transición | Criterio principal |
|------------|-------------------|
| MVP → Fase 2 | Correctores confirman utilidad; NER >80% |
| Fase 2 → Fase 3 | Embeddings funcionan; alertas voz <30% FP |
| Fase 3 → Fase 4 | Focalización validada; LLM local viable |
| Fase 4 → Fase 5 | Timeline preciso; base léxica disponible |
| Fase 5 → Fase 6 | Corpus de géneros; clasificador entrenado |
| Fase 6 → Fase 7 | Investigación favorable; interés de usuarios |

---

## Documentos de esta Sección

| Documento | Descripción |
|-----------|-------------|
| [Fase 0: Setup](./phase-0-setup.md) | Configuración inicial |
| [Fase 1: MVP](./phase-1-mvp.md) | Capacidades del MVP |
| [Fases 2-7: Post-MVP](./phases-2-7-post-mvp.md) | Desarrollo posterior |
| [Validación](./validation-milestones.md) | Criterios entre fases |

---

## Siguiente Paso

Ver [Fase 0: Setup](./phase-0-setup.md) para comenzar la implementación.
