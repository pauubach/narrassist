# Índice de Heurísticas Narrativas

[← Volver al índice principal](../README.md)

---

## Visión General

Este módulo documenta las **6 familias de heurísticas** que el sistema utiliza para detectar inconsistencias narrativas. Cada familia agrupa reglas relacionadas que operan sobre aspectos específicos del texto.

---

## Las 6 Familias

| # | Familia | Descripción | Viabilidad |
|---|---------|-------------|------------|
| H1 | [Mundo](./heuristics-h1-world.md) | Entidades, espacio, tiempo, reglas | MEDIA-ALTA |
| H2 | [Personajes](./heuristics-h2-characters.md) | Atributos, conocimiento, voz | MEDIA |
| H3 | [Estructura](./heuristics-h3-structure.md) | Escenas, arcos, setup/payoff | BAJA |
| H4 | [Voz](./heuristics-h4-voice.md) | Estilo, registro, repeticiones | MUY ALTA |
| H5 | [Focalización](./heuristics-h5-focalization.md) | POV, acceso a información | BAJA |
| H6 | [Información](./heuristics-h6-information.md) | Matriz de conocimiento, revelaciones | MEDIA |

---

## Viabilidad por Familia

### MUY ALTA (Implementable con NLP estándar)

- **H4: Voz y estilo** - Métricas estadísticas puras: longitud de oraciones, riqueza léxica, repeticiones

### MEDIA-ALTA (Implementable con limitaciones)

- **H1: Mundo** - NER funciona para entidades nombradas; atributos explícitos detectables

### MEDIA (Requiere validación manual significativa)

- **H2: Personajes** - Psicología es inherentemente ambigua
- **H6: Información** - Requiere modelar conocimiento de personajes

### BAJA (Requiere LLM o declaración manual)

- **H3: Estructura** - Setup/payoff requiere comprensión semántica
- **H5: Focalización** - Pro-drop hace imposible detectar sujeto en ~50% de casos

---

## Estructura de cada Heurística

Cada heurística se documenta con:

```
HEURÍSTICA: H1.1 — Consistencia de entidades

DESCRIPCIÓN: [Qué verifica]
SEÑAL: [débil/media/alta]
CONTEXTO: [Cuándo aplicar]
EXCEPCIONES: [Cuándo NO aplicar]
FALSOS POSITIVOS: [Cómo puede fallar]
IMPLEMENTACIÓN: [Cómo se implementa técnicamente]
```

---

## Principios Fundamentales

### 1. Las heurísticas son señales, no reglas

Una heurística activada NO significa necesariamente un error. Indica algo que el corrector debe verificar.

### 2. El contexto modula la aplicación

- El género afecta qué heurísticas aplican
- La focalización afecta qué información es "válida"
- El estilo del autor puede justificar "violaciones"

### 3. Lo que NO es error

- Narrador no fiable contradiciéndose
- Cambio de perspectiva a personaje con información diferente
- Violación de reglas que es el punto de la trama
- Subversión consciente de expectativas genéricas

### 4. La intención autoral es inaccesible

El sistema solo trabaja con el texto. No puede determinar "qué quiso decir el autor". Por eso:
- Señala, no corrige
- El corrector decide si es error o intención

---

## Niveles de Confianza

| Nivel | Color | Significado |
|-------|-------|-------------|
| 🔴 CRÍTICA | Rojo | Contradicción objetiva verificable |
| 🟠 ALTA | Naranja | Inconsistencia probable |
| 🟡 MEDIA | Amarillo | Posible problema a revisar |
| 🔵 INFO | Azul | Información para el corrector |

**Configurable**: El usuario puede ajustar los umbrales por tipo de alerta.

---

## Siguiente Paso

Comienza revisando [H1: Coherencia del Mundo](./heuristics-h1-world.md), que contiene las heurísticas más implementables.
