# Temporal Instance Detection: Niveles y Limites Semanticos

> Documento tecnico sobre las capacidades de deteccion de instancias
> temporales, organizadas por nivel de complejidad.
>
> **Estado**: Nivel A y B implementados (v0.7.0)

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

### Patrones de edad explicita

| Patron | Ejemplo | Confianza |
|--------|---------|-----------|
| `cuando tenia X anios` | "cuando tenia 40 anios" | 0.90 |
| `a los X anios` | "a los 40 anios" | 0.85 |
| `con X anios` | "con 40 anios" | 0.85 |
| `X anios cumplidos` | "40 anios cumplidos" | 0.90 |
| `tenia X anios` | "tenia 40 anios" | 0.85 |
| `cumplio X anios` | "cumplio 40 anios" | 0.90 |
| `rondaba los X` | "rondaba los 40" | 0.75 |
| `pasados los X` | "pasados los 60" | 0.75 |
| `cerca de los X anios` | "cerca de los 30 anios" | 0.70 |
| `apenas X anios` | "apenas 15 anios" | 0.80 |

### Fases vitales (39 alias)

| Fase | Alias |
|------|-------|
| `child` | ninio/nina, pequenio/pequenia, bebe, criatura, chiquillo/a, crio/cria, infancia, niniez |
| `teen` | adolescente, muchacho/a, chaval/a, chico/a, adolescencia, pubertad |
| `young` | joven, mozo/moza, juventud |
| `adult` | adulto/a, maduro/a, madurez |
| `elder` | mayor, viejo/a, anciano/a, abuelo/a, vejez, senectud |

### Deteccion de adyacencia al nombre

Todos los alias se detectan como fase cuando preceden al nombre de un personaje:
- "el anciano Pedro" → `2@phase:elder`
- "la muchacha Ana" → `1@phase:teen`
- "el bebe Juan" → `3@phase:child`

### Inferencia por evento vital (15 eventos)

| Evento | Fase inferida | Confianza |
|--------|---------------|-----------|
| guarderia, escuela primaria | child | 0.85 |
| colegio | child | 0.70 |
| instituto, bachillerato | teen | 0.80-0.85 |
| universidad, facultad | young | 0.80 |
| servicio militar, mili | young | 0.80 |
| boda | adult | 0.60 |
| jubilacion, retiro | elder | 0.70-0.85 |
| residencia de ancianos, geriatrico | elder | 0.90 |

Ejemplo: "Ana recordaba sus anios de universidad" → `1@phase:young` (0.80)

### Guardia contra edades metaforicas

Edades > 130 se descartan automaticamente como metaforas/hiperboles:
- "tenia mil anios encima" → descartado (1000 > 130)
- "cien anios de soledad" → descartado (solo si > 130; 100 si pasa)

### Limites del Nivel A

| Limite | Ejemplo que falla | Causa |
|--------|------------------|-------|
| Edad implicita sin pattern | "ya era un hombre hecho y derecho" | No hay alias exacto |
| Contexto narrativo complejo | "tras la guerra, envejecio" | Requiere inferencia |
| Pro-drop | "Tenia 40 anios" (sin sujeto) | Necesita correferencia |
| Epocas vagas | "en la belle epoque" | No mapea a rango de anios |
| Edad relativa | "10 anios mayor que Pedro" | Requiere razonamiento |

### Cobertura estimada

- **Novelas contemporaneas con flashbacks**: ~70-80%
- **Narrativa historica con epocas vagas**: ~35-45%
- **Narrativa experimental**: ~20-30%

---

## Nivel B — LLM Per-Chapter Extraction (Implementado)

### Arquitectura

```
Capitulo + Lista de personajes
       |
       v
  [Prompt CoT + few-shot]
       |
       v
  [Ollama (qwen2.5/llama3.2/mistral)]
       |
       v
  [JSON parse + validacion]
       |
       v
  [Merge con Nivel A (regex prioridad)]
       |
       v
  Instancias temporales finales
```

### Modulo: `temporal/llm_extraction.py`

**Funcion principal**: `extract_temporal_instances_llm(chapter_text, entity_names)`

**Validaciones aplicadas a cada deteccion LLM**:
1. Tipo valido (age, phase, year, offset)
2. Confianza >= 0.6 (umbral por defecto)
3. Entidad conocida (nombre existe en la lista)
4. Valor en rango razonable (age: 0-130, year: 0-2100, offset: ±200)
5. Evidencia textual verificable (la cita debe existir en el texto original)
6. Si la evidencia no se encuentra, confianza * 0.6 (penalizacion)

### Prompt template

- **System**: Analista narrativo experto en cronologia de personajes
- **Few-shot**: 2 ejemplos (jubilacion → elder, rondaba los cuarenta + guerra 1936)
- **Temperatura**: 0.2 (conservador)
- **Max tokens**: 500
- **Texto truncado**: Maximo 3000 caracteres por capitulo

### Integracion con el pipeline

El pipeline `_run_temporal_analysis` ejecuta ambos niveles secuencialmente:

```python
# 1. Nivel A: regex (rapido, alta precision)
chapter_markers = marker_extractor.extract_with_entities(...)

# 2. Nivel B: LLM (complementa, no reemplaza)
llm_instances = extract_temporal_instances_llm(chapter.content, entity_names)
llm_instances = resolve_entity_ids(llm_instances, entity_name_to_id)
new_instances = merge_with_regex_instances(regex_ids, llm_instances)
```

**Merge**: Regex siempre tiene prioridad. LLM solo anade instancias nuevas
(que no coincidan con ningun `temporal_instance_id` ya detectado por regex).

### Graceful degradation

Si Ollama no esta disponible o el LLM falla:
- `is_llm_available()` retorna `False` → skip silencioso
- Excepciones capturadas con logger.debug → no rompe el pipeline
- El Nivel A sigue funcionando normalmente

### Limites del Nivel B

- **Alucinaciones**: Mitigadas con validacion de evidencia textual
- **Costo**: ~1-3 seg/capitulo con qwen2.5 7B en CPU
- **Sin cross-chapter**: Cada capitulo se procesa aislado
- **Variabilidad inter-modelo**: Calidad depende del modelo Ollama disponible

### Cobertura estimada (A + B combinados)

- **Novelas contemporaneas con flashbacks**: ~85-90%
- **Narrativa historica con epocas vagas**: ~50-60%
- **Narrativa experimental**: ~35-45%

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

### Tecnicas propuestas

1. **Grafo temporal por entidad**: Nodos = instancias, aristas = relaciones
2. **Propagacion de restricciones**: `@age:10` + "20 anios despues" → `@age:30`
3. **Coherencia check**: Cap 1 dice 10, Cap 5 dice 25 "20 anios despues" → alerta

### Complejidad

Alta. Requiere resolver ambiguedades de correferencia cross-chapter,
manejar narrativa no lineal, y distinguir tiempo narrativo vs discurso.

---

## Nivel D — Narrative-Experts Decomposition (Investigacion)

### Arquitectura propuesta (inspirada en ACL 2024)

```
Coordinador
  ├── Agente Temporal → extrae fechas, edades, epocas
  ├── Agente Causal   → infiere relaciones causa-efecto temporales
  ├── Agente Biografico → construye timeline por personaje
  └── Agente Validador → cross-check coherencia global
```

### Referencias academicas

- **TimeChara** (Wang et al., 2024): Benchmark para deteccion de
  alucinaciones punto-en-el-tiempo. Precision LLM: ~60-75%.

- **Temporal Blind Spots in LLMs** (Fatemi et al., 2024): Dificultades
  sistematicas con razonamiento temporal (ordenacion, duracion, transitividad).

- **Narrative-Experts** (Chen et al., 2024): Descomposicion en sub-tareas
  mejora precision 15-30% vs single-prompt.

### Viabilidad

Requiere modelos 13B+, latencia 10-30 seg/doc, solo viable como batch.

---

## Hoja de Ruta

```
v0.6.0   [A] Regex basico ─────────────────── Completado
v0.7.0   [A] Regex hardened + [B] LLM ────── Completado (actual)
Futuro   [C] Cross-chapter linking ─────────── Post-TFM
Futuro   [D] Narrative-Experts ─────────────── Investigacion
```

---

## Ficheros clave

| Fichero | Descripcion |
|---------|-------------|
| `temporal/markers.py` | Nivel A: regex, AGE_PHASE_ALIASES, LIFE_EVENT_PHASE_MAP |
| `temporal/llm_extraction.py` | Nivel B: LLM extraction, validation, merge |
| `temporal/entity_mentions.py` | Utilidad compartida: carga menciones por capitulo |
| `temporal/timeline.py` | Timeline builder, flashback validation (LLM Layer 3) |
| `llm/prompts.py` | TEMPORAL_EXTRACTION_SYSTEM/TEMPLATE/EXAMPLES |
| `pipelines/analysis_pipeline.py` | Integracion A+B en `_run_temporal_analysis` |

## Tests

| Fichero | Tests | Cobertura |
|---------|-------|-----------|
| `test_temporal.py` | 42 | Nivel A basico + edge cases |
| `test_temporal_level_ab.py` | 47 | Nivel A hardening + Nivel B |
| `test_temporal_entity_mentions_integration.py` | 4 | Shared utility |

---

*Creado: 2026-02-13*
*Actualizado: 2026-02-13 — Nivel A hardened + Nivel B implementado*
