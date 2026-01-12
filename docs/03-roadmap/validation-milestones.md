# Validación entre Fases

[← Volver a Roadmap](./README.md) | [← Índice principal](../../README.md)

---

## Principio de Validación

> **No avanzar a la siguiente fase sin validar la anterior con usuarios reales.**

Cada transición requiere evidencia concreta de que las capacidades anteriores funcionan y aportan valor.

---

## Hitos de Validación

### MVP → Fase 2

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Utilidad confirmada | Encuesta a correctores | >70% considera útil |
| Precisión NER | F1 en corpus de prueba | >80% |
| Uso de fusión manual | % de entidades fusionadas | Datos de uso disponibles |
| Alertas útiles | % de alertas aceptadas | >40% |

**Preguntas a validar**:
- ¿Los correctores usan el sistema en su flujo de trabajo?
- ¿Las alertas detectan errores reales?
- ¿El tiempo de análisis es aceptable?

---

### Fase 2 → Fase 3

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Embeddings funcionales | Tiempo de procesamiento | <5min para 100k palabras |
| Hardware compatible | Funciona en 16GB RAM | Sin swapping excesivo |
| Alertas de voz | Falsos positivos | <30% |
| Mejora correferencia | F1 vs MVP | +10 puntos |

**Preguntas a validar**:
- ¿Los perfiles de voz son distinguibles?
- ¿Las alertas de voz detectan inconsistencias reales?
- ¿El sistema escala a novelas largas?

---

### Fase 3 → Fase 4

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Detección focalización | Precisión validada | >60% |
| LLM local viable | Inferencia en 16GB | <10s por consulta |
| Perfiles de voz | Utilidad confirmada | >50% de correctores los usan |

**Preguntas a validar**:
- ¿La detección de focalización es útil?
- ¿El LLM local aporta valor vs. heurísticas?
- ¿Vale la pena el coste computacional?

---

### Fase 4 → Fase 5

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Timeline automático | Precisión de ordenación | >75% |
| Modelo de conocimiento | Alertas de "saber imposible" | >50% verdaderos positivos |
| Base léxica disponible | Cobertura temporal | 1800-2020 |

**Preguntas a validar**:
- ¿El timeline automático reduce trabajo del corrector?
- ¿Las alertas de conocimiento son útiles?
- ¿Hay recursos léxicos disponibles para anacronismos?

---

### Fase 5 → Fase 6

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Corpus de géneros | Textos etiquetados | >100 por género principal |
| Clasificador de género | Precisión | >80% |
| Setup/Payoff | Utilidad validada | Feedback positivo |

**Preguntas a validar**:
- ¿La calibración por género mejora la experiencia?
- ¿Los correctores quieren detección automática de género?
- ¿El análisis setup/payoff es viable?

---

### Fase 6 → Fase 7

| Criterio | Medida | Umbral |
|----------|--------|--------|
| Investigación favorable | Papers publicados | Viabilidad demostrada |
| Interés de usuarios | Encuesta | >60% quiere esta funcionalidad |
| Enfoque no prescriptivo | Diseño validado | Aprobado por narratólogos |

**Preguntas a validar**:
- ¿Es técnicamente viable detectar temas sin imponer interpretación?
- ¿Los correctores quieren análisis temático?
- ¿Cómo evitar sesgo ideológico?

---

## Proceso de Validación

### 1. Recopilación de Datos

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FUENTES DE DATOS PARA VALIDACIÓN                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CUANTITATIVAS:                                                          │
│  • Logs de uso (con consentimiento)                                      │
│  • Métricas de precisión/recall                                          │
│  • Tiempos de procesamiento                                              │
│  • % de alertas aceptadas/descartadas                                    │
│                                                                          │
│  CUALITATIVAS:                                                           │
│  • Entrevistas con correctores                                           │
│  • Encuestas de satisfacción                                             │
│  • Feedback en issues/tickets                                            │
│  • Observación de uso real                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Análisis

- Comparar métricas con umbrales definidos
- Identificar patrones en el feedback cualitativo
- Documentar limitaciones encontradas
- Priorizar mejoras para siguiente fase

### 3. Decisión

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MATRIZ DE DECISIÓN                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TODOS los criterios cumplidos:                                          │
│  └── ✅ Avanzar a siguiente fase                                        │
│                                                                          │
│  MAYORÍA de criterios cumplidos (>70%):                                  │
│  └── ⚠️ Avanzar con plan de mejora paralelo                            │
│                                                                          │
│  MINORÍA de criterios cumplidos (<70%):                                  │
│  └── ❌ Iterar en fase actual antes de avanzar                          │
│                                                                          │
│  CRITERIO CRÍTICO no cumplido:                                          │
│  └── 🛑 Reevaluar viabilidad de la fase siguiente                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Documentación de Validación

Cada transición debe documentar:

1. **Fecha de validación**
2. **Métricas obtenidas** vs umbrales
3. **Feedback cualitativo** resumido
4. **Decisión tomada** y justificación
5. **Acciones pendientes** para siguiente fase

### Plantilla

```markdown
# Validación: MVP → Fase 2

**Fecha**: YYYY-MM-DD

## Métricas

| Criterio | Umbral | Obtenido | Estado |
|----------|--------|----------|--------|
| Utilidad | >70% | 78% | ✅ |
| NER F1 | >80% | 82% | ✅ |
| Alertas útiles | >40% | 45% | ✅ |

## Feedback Cualitativo

- [Resumen de entrevistas]
- [Patrones identificados]
- [Limitaciones reportadas]

## Decisión

✅ Avanzar a Fase 2

## Acciones para Fase 2

1. [Mejora específica 1]
2. [Mejora específica 2]
```

---

## Volver

[← Roadmap](./README.md)
