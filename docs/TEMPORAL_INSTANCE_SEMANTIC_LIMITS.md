# Temporal Instance Detection: Niveles y Limites Semanticos

> Documento tecnico sobre las capacidades actuales de deteccion de instancias
> temporales y las mejoras posibles organizadas por nivel de complejidad.

## Contexto

El sistema de instancias temporales permite distinguir a un mismo personaje
en distintos momentos de su vida (Ana a los 10 vs Ana a los 40). Esto es
fundamental para detectar inconsistencias en narrativas no lineales con
flashbacks, prolepsis y saltos temporales.

**Formato de instance ID**: `{entity_id}@{qualifier}:{value}`

| Tipo | Ejemplo | Descripcion |
|------|---------|-------------|
| `@age:N` | `1@age:40` | Edad explicita en anios |
| `@phase:X` | `1@phase:child` | Fase vital (ninio, joven, adulto...) |
| `@offset_years:±N` | `1@offset_years:-5` | Offset relativo ("hace 5 anios") |
| `@year:YYYY` | `1@year:1985` | Anio absoluto |

---

## Nivel A — Regex + Heuristicas (Implementado)

### Capacidades actuales

**Patrones de edad explicita** (`markers.py`):
- "cuando tenia 40 anios" → `@age:40`
- "a los 40 anios" → `@age:40`
- "con 40 anios" → `@age:40`
- "cumplio 40 anios" → `@age:40`
- "recien cumplidos los 40" → `@age:40`

**Fases vitales** (AGE_PHASE_ALIASES):
- ninio/nina, pequenio/pequenia → `@phase:child`
- adolescente → `@phase:teen`
- joven → `@phase:young`
- adulto/adulta → `@phase:adult`
- mayor, viejo/vieja → `@phase:elder`

**Deteccion de adyacencia** (linea 974):
- "la pequenia Ana" → mira si hay mencion de entidad adyacente → `1@phase:child`
- "el joven Pedro" → `2@phase:young`

**Offsets relativos**:
- "hace 5 anios" → `@offset_years:-5`
- "3 anios atras" → `@offset_years:-3`
- "dentro de 2 anios" → `@offset_years:+2`
- "5 anios despues" → `@offset_years:+5`

**Anios absolutos**:
- "en 1985" → `@year:1985`
- "primavera de 1990" → `@year:1990`

### Limites del Nivel A

| Limite | Ejemplo que falla | Causa |
|--------|------------------|-------|
| Edad implicita | "ya era un hombre maduro" | No hay numero, no hay alias exacto |
| Contexto narrativo | "tras la guerra, envejecio" | Requiere inferencia temporal |
| Pro-drop | "Tenia 40 anios" (sin sujeto) | Necesita resolucion de correferencia |
| Epocas vagas | "en la belle epoque" | No mapea a rango de anios |
| Edad relativa | "10 anios mayor que Pedro" | Requiere razonamiento sobre otra entidad |
| Ironia/metafora | "tenia mil anios encima" | Falso positivo (mil no es edad real) |

### Cobertura estimada

- **Novelas contemporaneas con flashbacks**: ~65-75% de instancias temporales
- **Narrativa historica con epocas vagas**: ~30-40%
- **Narrativa experimental (flujo de conciencia)**: ~15-25%

---

## Nivel B — LLM Per-Chapter Prompts (Propuesto)

### Objetivo

Usar el LLM local (Ollama) para extraer instancias temporales que escapan
al regex, procesando capitulo por capitulo.

### Diseno propuesto

```
Entrada: texto del capitulo + lista de entidades conocidas
Prompt: "Extrae la edad, fase vital o epoca de cada personaje mencionado"
Salida: JSON con instancias detectadas
```

**Prompt template** (ejemplo):

```
Dado el siguiente fragmento narrativo y la lista de personajes,
identifica la edad, fase vital o epoca temporal de cada personaje
mencionado. Solo incluye informacion EXPLICITA o claramente implicita
en el texto.

Personajes: {entity_names}

Texto:
---
{chapter_text}
---

Responde en JSON:
[
  {
    "entity": "nombre",
    "type": "age|phase|year|offset",
    "value": "40|child|1985|+5",
    "evidence": "cita textual",
    "confidence": 0.0-1.0
  }
]
```

### Ventajas sobre Nivel A

| Mejora | Ejemplo | Nivel A | Nivel B |
|--------|---------|---------|---------|
| Edad implicita | "era un hombre maduro" | Miss | `@phase:adult` (0.7) |
| Contexto narrativo | "Desde la jubilacion..." | Miss | `@phase:elder` (0.8) |
| Epocas | "durante la Transicion" | Miss | `@year:1978` (0.6) |
| Relaciones edad | "su hermana menor" | Miss | Inferencia relativa |

### Limites del Nivel B

- **Alucinaciones**: El LLM puede inventar edades no mencionadas
- **Costo computacional**: 1-3 segundos por capitulo con qwen2.5 7B
- **Inconsistencia inter-chapter**: Cada capitulo se procesa aislado
- **Dependencia de modelo**: Calidad varia entre llama3.2, mistral, qwen2.5

### Mitigaciones

1. **Umbral de confianza minimo** (0.6): Descartar detecciones inciertas
2. **Evidencia obligatoria**: Solo aceptar si incluye cita textual verificable
3. **Votacion multi-modelo**: Confirmar con >= 2 modelos (ya tenemos infraestructura)
4. **Cross-check con Nivel A**: Priorizar regex cuando ambos detectan

### Estimacion de mejora

- Cobertura: +15-25% sobre Nivel A
- Precision: ~80-90% (con mitigaciones)
- Latencia adicional: ~1-3 seg/capitulo

---

## Nivel C — Cross-Chapter Temporal Linking (Futuro)

### Objetivo

Vincular instancias temporales entre capitulos para construir una linea
temporal coherente por personaje.

### Ejemplo

```
Cap 1: "Ana tenia 10 anios cuando murio su padre"  → 1@age:10
Cap 5: "Veinte anios despues, Ana volvio al pueblo" → 1@age:30 (inferido)
Cap 3: "De nina, Ana jugaba en el rio"              → 1@phase:child (= 1@age:10?)
```

### Tecnicas

1. **Grafo temporal por entidad**: Nodos = instancias, aristas = relaciones
   temporales (offset, secuencia narrativa)
2. **Propagacion de restricciones**: Si `@age:10` + "20 anios despues" →
   `@age:30` automatico
3. **Coherencia check**: Si Cap 1 dice 10 y Cap 5 dice 25 "20 anios despues" →
   alerta de inconsistencia

### Requisitos

- Nivel B funcionando (para capturar instancias implicitas)
- Modelo de grafo temporal (nuevo modulo)
- Ventana de contexto multi-capitulo para el LLM

### Complejidad

Alta. Requiere:
- Resolver ambiguedades de correferencia cross-chapter
- Manejar narrativa no lineal (flashbacks dentro de flashbacks)
- Distinguir tiempo narrativo vs tiempo del discurso

---

## Nivel D — Narrative-Experts Decomposition (Investigacion)

### Objetivo

Descomponer el analisis temporal en sub-tareas especializadas, cada una
manejada por un agente/prompt experto.

### Arquitectura (inspirada en Narrative-Experts, ACL 2024)

```
Coordinador
  ├── Agente Temporal → extrae fechas, edades, epocas
  ├── Agente Causal   → infiere relaciones causa-efecto temporales
  ├── Agente Biografico → construye timeline por personaje
  └── Agente Validador → cross-check coherencia global
```

### Referencia academica

- **TimeChara** (Wang et al., 2024): Benchmark para deteccion de
  alucinaciones punto-en-el-tiempo en personajes. Demuestra que los LLMs
  actuales (GPT-4, Llama) cometen errores significativos al responder
  "como era X en el anio Y". Precision ~60-75% segun modelo.

- **Temporal Blind Spots in LLMs** (Fatemi et al., 2024): Los LLMs tienen
  dificultades sistematicas con razonamiento temporal, especialmente:
  - Ordenacion de eventos con pistas implicitas
  - Duracion y solapamiento de intervalos
  - Relaciones temporales transitivas (A antes de B, B antes de C → A antes de C)

- **Narrative-Experts** (Chen et al., 2024): Descomposicion de analisis
  narrativo complejo en sub-tareas especializadas con agentes LLM mejora
  precision un 15-30% vs single-prompt.

### Viabilidad

- Requiere modelos mas capaces (7B minimo, idealmente 13B+)
- Latencia alta (10-30 seg por documento completo)
- Mayor consumo de GPU/CPU
- Solo viable como analisis batch, no interactivo

---

## Hoja de Ruta Recomendada

```
Actual:  [A] Regex + heuristicas ─────────────────── Implementado (v0.6.0)
Corto:   [B] LLM per-chapter prompts ────────────── Sprint S7-S8
Medio:   [C] Cross-chapter linking ──────────────── Post-TFM
Largo:   [D] Narrative-Experts ──────────────────── Investigacion futura
```

### Prioridad: Nivel B

El Nivel B es el siguiente paso natural porque:

1. **Infraestructura existente**: Ya tenemos Ollama, votacion multi-modelo,
   y prompt engineering (Sprint S5)
2. **Impacto alto**: +15-25% cobertura con precision aceptable
3. **Riesgo bajo**: Se integra como capa adicional sobre Nivel A (no reemplaza)
4. **Precedente**: El flashback validation ya usa LLM con exito (3-layer scoring)

### Integracion con el pipeline existente

```python
# Flujo propuesto para Nivel B
def extract_temporal_instances(chapter, entities):
    # 1. Nivel A: regex (rapido, alta precision)
    regex_instances = marker_extractor.extract_with_entities(chapter, entities)

    # 2. Nivel B: LLM (lento, mayor cobertura)
    llm_instances = llm_temporal_extractor.extract(chapter, entities)

    # 3. Merge: regex tiene prioridad; LLM solo anade nuevas detecciones
    merged = merge_instances(regex_instances, llm_instances,
                            min_confidence=0.6)

    return merged
```

---

## Metricas de Evaluacion

Para medir el progreso entre niveles, se proponen estas metricas:

| Metrica | Descripcion | Target Nivel B |
|---------|-------------|----------------|
| **Recall** | % de instancias reales detectadas | >= 80% |
| **Precision** | % de detecciones correctas | >= 85% |
| **F1** | Media armonica | >= 0.82 |
| **Latencia** | Tiempo adicional por capitulo | < 3 seg |
| **Falsos positivos** | Instancias inventadas | < 5% |

### Corpus de evaluacion

Para validar, se necesita un corpus anotado con:
- 5-10 fragmentos narrativos con flashbacks
- Instancias temporales gold-standard anotadas manualmente
- Mezcla de edades explicitas, implicitas y contextuales

---

*Documento creado: 2026-02-13*
*Ultima actualizacion: 2026-02-13*
*Relacionado: [ENTITY_TIMELINE_ATTRIBUTES_AUDIT_2026-02-13.md](ENTITY_TIMELINE_ATTRIBUTES_AUDIT_2026-02-13.md)*
