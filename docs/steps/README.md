# STEPs de Implementación

[← Volver al índice principal](../../README.md)

---

## Visión General

Los STEPs son unidades ejecutables de implementación diseñadas para Claude Code. Cada STEP tiene prerequisitos claros, inputs/outputs definidos, y criterios de DONE verificables.

---

## Índice de STEPs por Fase

### Fase 0: Fundamentos

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [0.1](./phase-0/step-0.1-environment.md) | Configuración del Entorno | S | P0 |
| [0.2](./phase-0/step-0.2-project-structure.md) | Estructura del Proyecto | S | P0 |
| [0.3](./phase-0/step-0.3-database-schema.md) | Schema de Base de Datos | M | P0 |

### Fase 1: Infraestructura Base

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [1.1](./phase-1/step-1.1-docx-parser.md) | Parser DOCX | M | P0 |
| [1.2](./phase-1/step-1.2-structure-detector.md) | Detector de Estructura | M | P0 |
| [1.3](./phase-1/step-1.3-ner-pipeline.md) | Pipeline NER | M | P0 |
| [1.4](./phase-1/step-1.4-dialogue-detector.md) | Detector de Diálogos | S | P0 |

### Fase 2: Entidades y Atributos

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [2.1](./phase-2/step-2.1-coreference.md) | Correferencia Básica | L | P0 |
| [2.2](./phase-2/step-2.2-entity-fusion.md) | Fusión de Entidades | M | P0 |
| [2.3](./phase-2/step-2.3-attribute-extraction.md) | Extracción de Atributos | L | P0 |
| [2.4](./phase-2/step-2.4-attribute-consistency.md) | Consistencia de Atributos | L | P0 |

### Fase 3: Grafías y Repeticiones

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [3.1](./phase-3/step-3.1-name-variants.md) | Variantes de Grafía | M | P1 |
| [3.2](./phase-3/step-3.2-lexical-repetitions.md) | Repeticiones Léxicas | M | P2 |
| [3.3](./phase-3/step-3.3-semantic-repetitions.md) | Repeticiones Semánticas | M | P2 |

### Fase 4: Temporalidad

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [4.1](./phase-4/step-4.1-temporal-markers.md) | Marcadores Temporales | M | P2 |
| [4.2](./phase-4/step-4.2-timeline-builder.md) | Constructor de Timeline | L | P2 |
| [4.3](./phase-4/step-4.3-temporal-inconsistencies.md) | Inconsistencias Temporales | L | P2 |

### Fase 5: Voz y Registro

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [5.1](./phase-5/step-5.1-voice-profiles.md) | Perfiles de Voz | M | P2 |
| [5.2](./phase-5/step-5.2-voice-deviations.md) | Desviaciones de Voz | M | P2 |
| [5.3](./phase-5/step-5.3-register-changes.md) | Cambios de Registro | M | P2 |
| [5.4](./phase-5/step-5.4-speaker-attribution.md) | Atribución de Hablante | XL | P2 |

### Fase 6: Focalización

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [6.1](./phase-6/step-6.1-focalization-declaration.md) | Declaración de Focalización | M | P3 |
| [6.2](./phase-6/step-6.2-focalization-violations.md) | Violaciones de Focalización | L | P3 |

### Fase 7: Integración y Exportación

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [7.1](./phase-7/step-7.1-alert-engine.md) | Motor de Alertas | L | P0 |
| [7.2](./phase-7/step-7.2-character-sheets.md) | Fichas de Personaje | M | P1 |
| [7.3](./phase-7/step-7.3-style-guide.md) | Hoja de Estilo | M | P1 |
| [7.4](./phase-7/step-7.4-cli.md) | CLI de Análisis | M | P1 |

### Fase 8: Análisis Emocional (Post-MVP)

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [8.1](./phase-8/step-8.1-sentiment-analysis.md) | Análisis de Sentimiento | L | P2 |
| [8.2](./phase-8/step-8.2-emotional-coherence.md) | Coherencia Emocional | L | P2 |

> **Nota**: La Fase 8 está planificada para después del MVP. Incluye detección de inconsistencias entre el estado emocional declarado de un personaje y su comportamiento comunicativo (diálogos, acciones).

### Fase 9: Grafo de Relaciones (Post-MVP)

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [9.1](./phase-9/step-9.1-entity-relationships.md) | Relaciones entre Entidades | L | P2 |
| [9.2](./phase-9/step-9.2-interaction-analysis.md) | Análisis de Interacciones | M | P2 |

> **Nota**: La Fase 9 modela relaciones entre personajes (amistad, enemistad, familia, etc.), detecta cómo evolucionan, y verifica coherencia en las interacciones. Por ejemplo: si A y B son enemigos, alerta si interactúan amistosamente sin justificación.

### Fase 10: Análisis Narrativo Avanzado (Post-MVP)

| STEP | Nombre | Complejidad | Prioridad |
|------|--------|-------------|-----------|
| [10.1](./phase-10/step-10.1-character-relevance.md) | Relevancia de Personajes | L | P3 |
| [10.2](./phase-10/step-10.2-chapter-pacing.md) | Ritmo y Pacing | L | P3 |
| [10.3](./phase-10/step-10.3-structural-coherence.md) | Coherencia Estructural | XL | P3 |

> **Nota**: La Fase 10 es análisis narrativo de alto nivel:
> - **10.1**: Detecta personajes que no aportan, son "planos" o redundantes
> - **10.2**: Analiza ritmo de capítulos, detecta problemas de pacing
> - **10.3**: Verifica conexiones entre capítulos, subtramas abandonadas, arcos incompletos

---

## Complejidad

| Símbolo | Horas estimadas |
|---------|-----------------|
| S | 2-4 horas |
| M | 4-6 horas |
| L | 6-8 horas |
| XL | 8-12 horas |

---

## Prioridad

| Nivel | Descripción |
|-------|-------------|
| P0 | Crítico - Sin esto no hay producto |
| P1 | Alto valor - Diferenciales claros |
| P2 | Valor medio - Añadir tras validación |
| P3 | Experimental - Alta tasa de error |

---

## Estructura de un STEP

Cada documento de STEP sigue esta estructura:

```
# STEP X.Y: Nombre

## Metadata
- Complejidad: S/M/L
- Prioridad: P0/P1/P2/P3
- Prerequisitos: STEPs anteriores requeridos

## Descripción
Qué hace este STEP y por qué es necesario.

## Inputs
Qué necesita para ejecutarse.

## Outputs
Qué produce (archivos, APIs, tablas).

## Implementación
Código guía o algoritmo detallado.

## Criterio de DONE
Test verificable que confirma completitud.

## Advertencias
Limitaciones conocidas y expectativas realistas.
```

---

## Patrones Comunes

<!-- Patrones compartidos: se documentarán durante la implementación -->

---

## Volver

[← Índice principal](../../README.md)
