# Temporal Instance Detection: Niveles y Limites Semanticos

> Documento tecnico sobre las capacidades de deteccion de instancias
> temporales, organizadas por nivel de complejidad.
>
> **Estado**: Nivel A, B y C implementados (v0.8.0)

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

## Nivel C — Cross-Chapter Temporal Linking (Implementado)

### Objetivo

Vincular instancias temporales entre capitulos para construir una linea
temporal coherente por personaje.

### Ejemplo

```
Cap 1: "Ana tenia 10 anios cuando murio su padre"  → 1@age:10
Cap 5: "Veinte anios despues, Ana volvio al pueblo" → 1@age:30 (inferido)
Cap 3: "De nina, Ana jugaba en el rio"              → 1@phase:child (= 1@age:10?)
```

### Modulo: `temporal/cross_chapter.py`

**Funcion principal**: `build_entity_timelines(markers, entities, timeline)`

**Algoritmo en 5 fases**:

1. **Collect**: Agrupa instancias por entity_id, marca capitulos analepsis
2. **Sort**: Ordena en story-time (year → age → phase_rank → chapter)
3. **Link + Detect**: Conecta pares en story-order (progresion, co-ocurrencia, fase-edad)
   - Fase 3b: Compara discourse order (capitulo) vs story order para regresiones
4. **Infer**: Calcula anio de nacimiento desde pares (year, age); infiere edades desde offsets
5. **Discourse**: Detecta regressions en orden de capitulos sin flashback

### Rangos fase-edad (fuzzy, con ±3 tolerancia)

| Fase | Rango base | Con tolerancia |
|------|-----------|----------------|
| child | 0-14 | -3 a 17 |
| teen | 11-21 | 8 a 24 |
| young | 17-40 | 14 a 43 |
| adult | 30-70 | 27 a 73 |
| elder | 55-130 | 52 a 133 |

### Nuevas inconsistencias detectadas

| Tipo | Severidad | Descripcion |
|------|-----------|-------------|
| `cross_chapter_age_regression` | CRITICAL | Edad retrocede entre capitulos sin flashback |
| `phase_age_incompatible` | MEDIUM | Fase vital incompatible con edad explicita |
| `birth_year_contradiction` | HIGH | Combinaciones (anio, edad) dan nacimientos distintos |

### Integracion con pipeline

En `_run_temporal_analysis`, Level C se ejecuta despues del timeline building:
- Infiere marcadores adicionales (offsets → edades)
- Pasa `character_ages=None` al checker base para evitar duplicados (C-2)
- Agrega sus inconsistencias propias al resultado

### Flashback awareness (C-1)

Recibe el Timeline construido y marca capitulos como analepsis. Regresiones
en capitulos marcados como flashback se suprimen automaticamente.

### Cobertura estimada (A + B + C combinados)

- **Novelas contemporaneas con flashbacks**: ~90-95%
- **Narrativa historica con epocas vagas**: ~55-65%
- **Narrativa experimental**: ~40-50%

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
v0.7.0   [A] Regex hardened + [B] LLM ────── Completado
v0.8.0   [C] Cross-chapter linking ─────────── Completado (actual)
Futuro   [D] Narrative-Experts ─────────────── Investigacion
```

---

## Ficheros clave

| Fichero | Descripcion |
|---------|-------------|
| `temporal/markers.py` | Nivel A: regex, AGE_PHASE_ALIASES, LIFE_EVENT_PHASE_MAP |
| `temporal/llm_extraction.py` | Nivel B: LLM extraction, validation, merge |
| `temporal/cross_chapter.py` | Nivel C: cross-chapter linking, birth year, regression |
| `temporal/inconsistencies.py` | Checker + 3 nuevos tipos Level C |
| `temporal/entity_mentions.py` | Utilidad compartida: carga menciones por capitulo |
| `temporal/timeline.py` | Timeline builder, flashback validation (LLM Layer 3) |
| `llm/prompts.py` | TEMPORAL_EXTRACTION_SYSTEM/TEMPLATE/EXAMPLES |
| `pipelines/analysis_pipeline.py` | Integracion A+B+C en `_run_temporal_analysis` |

## Tests

| Fichero | Tests | Cobertura |
|---------|-------|-----------|
| `test_temporal.py` | 42 | Nivel A basico + edge cases |
| `test_temporal_level_ab.py` | 47 | Nivel A hardening + Nivel B |
| `test_cross_chapter.py` | 32 | Nivel C: linking, regression, inference |
| `test_temporal_entity_mentions_integration.py` | 4 | Shared utility |

---

*Creado: 2026-02-13*
*Actualizado: 2026-02-13 — Nivel C cross-chapter linking implementado*
