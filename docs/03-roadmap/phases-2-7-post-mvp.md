# Fases 2-7: Desarrollo Post-MVP

[← Volver a Roadmap](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Las fases posteriores al MVP añaden capacidades incrementalmente, siempre validando con usuarios reales antes de avanzar.

---

## Fase 2: Mejora de Correferencia

**Duración estimada**: 3-6 meses
**Dependencia**: MVP validado por correctores

### Estrategia de Mejora Progresiva

```
┌─────────────────────────────────────────────────────────────────────────┐
│              ESTRATEGIA DE CORREFERENCIA: MEJORA PROGRESIVA              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MVP (Fase 1): CORREFERENCIA BÁSICA                                     │
│  ├── Coreferee + heurísticas de género/número                           │
│  ├── F1 esperado: ~55% (suficiente con validación humana)               │
│  ├── FUSIÓN MANUAL de entidades por el corrector                        │
│  └── El corrector corrige; el sistema aprende                           │
│                                                                          │
│  Fase 2A: MEJORAS INCREMENTALES (3-4 meses)                             │
│  ├── Heurísticas mejoradas basadas en patrones de corrección            │
│  ├── LLM local para casos ambiguos (Llama 3.1 8B)                       │
│  └── F1 objetivo: ~72% (+17 puntos)                                     │
│                                                                          │
│  Fase 2B: FINE-TUNING LIGERO (4-6 meses adicionales)                    │
│  ├── Recopilar correcciones de usuarios (con consentimiento)            │
│  ├── Fine-tune de modelo existente (wl-coref o similar)                 │
│  └── F1 objetivo: ~78% (+6 puntos adicionales)                          │
│                                                                          │
│  Fase 2C: MODELO ESPECIALIZADO (9-12 meses, OPCIONAL)                   │
│  ├── Solo si hay demanda y recursos                                      │
│  ├── Corpus literario: AnCora + anotaciones propias (~2M tokens)        │
│  └── F1 objetivo: ≥85%                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Otras capacidades de Fase 2

- Modelo espacial simple (lugares y contención)
- Mejoras en timeline basadas en feedback
- Detección mejorada de diálogo
- Alertas de voz básicas

### Hardware

| Tarea | Requisitos |
|-------|------------|
| MVP e inferencia | 16GB RAM, sin GPU |
| Fine-tuning (2B) | GPU (Colab Pro) |
| Entrenamiento completo (2C) | GPU dedicada |

---

## Fase 3: Análisis de Voz y Perspectiva

**Duración estimada**: 4-6 meses
**Dependencia**: Fase 2 completada

### Heurísticas incorporadas

- H4.1 avanzado: Detección de estilo indirecto libre
- H5.1 completo: Detección de focalización automática
- H5.2: Cambios focales no marcados

### Capacidades nuevas

- Perfiles de voz con alertas calibradas
- Detección de hibridación de voces
- Sugerencias sobre marcado de cambios focales

### Dependencias técnicas

- Modelos de clasificación de estilo
- Fine-tuning en corpus literario español (si disponible)

### Riesgo

**MEDIO-ALTO**: Esta fase requiere validación empírica. Puede reducirse si los resultados no son satisfactorios.

---

## Fase 4: Coherencia Temporal y Causal

**Duración estimada**: 6-9 meses
**Dependencia**: Fases 2-3 completadas

### Heurísticas incorporadas

- H1.4 completo: Ordenación temporal automática
- H2.2: Consistencia de conocimiento de personajes

### Capacidades nuevas

- Timeline automático con alto nivel de confianza
- Detección de analepsis y prolepsis
- Modelo de propagación de información entre personajes
- Alertas de "personaje sabe lo que no debería saber"

### Dependencias técnicas

- Razonamiento temporal
- Modelo de eventos y causalidad
- Posiblemente LLM más potente

### Riesgo

**ALTO**: Esta fase puede no ser viable con tecnología local en 2024-2025.

---

## Fase 5: Análisis Estructural y Anacronismos

**Duración estimada**: 6-9 meses
**Dependencia**: Fase 4 + recursos léxicos

### Heurísticas incorporadas

- H3.1: Setup/Payoff (experimental)
- H4.2: Anacronismos (requiere base de datos léxica)
- H3.3: Balance de escenas

### Capacidades nuevas

- Detección de elementos plantados (muy conservador)
- Base de datos de datación léxica para español
- Clasificación de tipo de escena
- Visualización de estructura narrativa

### Dependencias técnicas

- Base de datos léxica histórica (construir o licenciar)
- Clasificador de escenas
- Investigación sobre setup/payoff

### Estado

**Parcialmente condicional** a disponibilidad de recursos léxicos.

---

## Fase 6: Género y Calibración Avanzada

**Duración estimada**: 4-6 meses
**Dependencia**: Fase 5 + corpus por género

### Capacidades nuevas

- Detección automática de género (con corrección manual)
- Perfiles de género que modulan todas las heurísticas
- Calibración automática basada en el texto analizado

### Dependencias

- Corpus de entrenamiento por género
- Ontología de géneros narrativos
- Validación con correctores profesionales

---

## Fase 7: Temas y Coherencia Profunda

**Duración estimada**: Investigación abierta
**Dependencia**: Fase 6 + investigación académica favorable

### Capacidades (si la investigación lo permite)

- Detección de temas emergentes
- Análisis de coherencia temática
- Sugerencias sobre desarrollo temático

### Estado

**CONDICIONAL**. El riesgo de imponer interpretaciones es muy alto. Solo se implementará si:

1. La investigación muestra viabilidad técnica
2. Los correctores validan que es útil
3. Se puede hacer de forma no prescriptiva

---

## Resumen de Fases

| Fase | Riesgo | Dependencia crítica |
|------|--------|---------------------|
| 2 | Bajo | Feedback de correctores |
| 3 | Medio | Validación empírica |
| 4 | Alto | LLM potente local |
| 5 | Medio | Base léxica histórica |
| 6 | Bajo | Corpus por género |
| 7 | Muy alto | Investigación académica |

---

## Siguiente Paso

Ver [Validación entre Fases](./validation-milestones.md) para los criterios de transición.
