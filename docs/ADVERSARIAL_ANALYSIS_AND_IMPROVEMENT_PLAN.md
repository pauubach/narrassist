# Adversarial Analysis Report & Improvement Plan

**Fecha**: 2025-01 | **Version**: 0.3.34 | **Tests**: 818 adversariales

## 1. Resumen Ejecutivo

Se ha ejecutado una suite completa de **818 tests adversariales** GAN-style que cubren 11 modulos del sistema NLP. Los tests estan disenados para exponer debilidades algoritmicas reales.

### Resultados Globales por Modulo

| Modulo | Tests | Passed | Failed | Skipped/Err | Pass Rate | Gravedad |
|--------|-------|--------|--------|-------------|-----------|----------|
| Cross-entity attributes (NUEVO) | 29 | 10 | 19 | 0 | **34.5%** | CRITICA |
| Entity fusion (NUEVO) | 76 | 53 | 20 | 3 xfail | **71.6%** | ALTA |
| Pipeline E2E (NUEVO) | 52 | 32 | 20 | 0 | **61.5%** | CRITICA |
| Attribute extraction | 60 | ~15 | ~45 | 0 | **~25%** | CRITICA |
| NER recognition | 75 | ~40 | ~35 | 0 | **~53%** | ALTA |
| Speaker attribution | 62 | 43 | 19 | 0 | **69.4%** | MEDIA |
| Knowledge temporal | 19 | 17 | 2 | 0 | **89.5%** | BAJA |
| Vital status | ~60 | ~50 | ~10 | 0 | **~83%** | BAJA |
| Emotional coherence | ~40 | ~30 | ~10 | 0 | **~75%** | MEDIA |
| Character location | ~60 | ~35 | ~25 | 57 err | **~58%** | ALTA |
| Document classification | 76 | 26 | 0 | 50 skip | **100%** (parcial) | N/A |
| Analysis modules | 26 | 26 | 0 | 0 | **100%** | OK |

**Pass rate global estimado: ~60%** (sin contar skips/not-implemented)

---

## 2. Analisis Detallado por Modulo

### 2.1 CRITICO: Attribute Extraction (25% pass rate)

**Archivo**: `test_attribute_adversarial.py` + `test_cross_entity_attribute_adversarial.py`

#### Problemas encontrados:

1. **Proximity bias en `_find_nearest_entity()`** (19/29 cross-entity tests fallan)
   - El algoritmo asigna atributos a la entidad mas cercana en caracteres
   - No resuelve pronombres (ella, el) para redirigir al sujeto correcto
   - Cuando LLM y embeddings fallan, TODOS los atributos van al ultimo personaje mencionado
   - **Bug real**: Maria Sanchez -> atributos asignados a Juan Perez

2. **Sin resolucion de pronombres**
   - "Ella tenia ojos verdes" no se vincula a la entidad femenina anterior
   - "El era alto" no se vincula al sujeto masculino anterior
   - Sujetos elipticos en espanol (pro-drop) no se resuelven

3. **Dialogos no soportados**
   - Atributos mencionados en dialogo no se asignan al personaje descrito
   - Autodescripcion ("Soy alto") no se detecta
   - Descripcion por terceros ("la de ojos verdes") no se vincula

4. **Negacion no detectada**
   - "No era alto" se detecta como "alto"
   - "A pesar de no tener ojos azules" asigna "azules"

5. **Comparaciones no manejadas**
   - "Mas alto que Beatriz" no separa atributos por entidad
   - "A diferencia de Ricardo (moreno), Estela era rubia" no se resuelve

#### Metricas clave:
- Precision de asignacion entity-attribute: **~35%** en escenas multi-personaje
- Deteccion de atributos basicos (un personaje): **~70%**
- Resolucion de pronombres para atributos: **~5%**
- Atributos en dialogos: **~0%**

---

### 2.2 ALTA: Entity Fusion (71.6% pass rate)

**Archivo**: `test_entity_fusion_adversarial.py`

#### Problemas encontrados:

1. **`_are_different_proper_names()` demasiado agresivo** (9 fallos)
   - Bloquea fusion de "Maria" con "Maria" cuando los acentos difieren
   - "Jose Garcia" vs "Jose Garcia" (sin tilde) -> rechazado
   - "Luis de la Fuente" vs "De la Fuente" -> rechazado
   - Se ejecuta ANTES de normalizar nombres

2. **Tipos incompatibles bloquean fusion del mismo nombre** (1 fallo critico)
   - "Maria Sanchez" (CHARACTER) + "Maria Sanchez" (CONCEPT) -> rechazado
   - BUG REAL: NER clasifica mal el tipo, y el fusionador no permite corregir

3. **Aliases registrados no se consultan a tiempo** (2 fallos)
   - "Francisco" con alias "Paco" -> no se fusiona porque name_filter bloquea antes
   - "el Gordo" con alias en Roberto -> embeddings dan 0.64, debajo del umbral 0.82

4. **`strip_accents()` elimina la ñ** (bug confirmado)
   - NFD descompone ñ = n + combining tilde, que se filtra como Mn
   - Afecta comparacion de nombres con ñ (Nuñez, Muñoz, etc.)

5. **Normalizacion no strip preposiciones interiores**
   - "Conde de Montecristo" -> "de montecristo" (deberia ser "montecristo")

#### Metricas clave:
- Fusion por normalizacion (Don X / Doctor X): **100%**
- Fusion por variacion ortografica: **60%** (falla con acentos)
- Fusion cross-type (mismo nombre, distinto NER label): **0%**
- Prevencion de fusion incorrecta: **100%** (excelente)

---

### 2.3 ALTA: NER Recognition (~53% pass rate)

**Archivo**: `test_ner_adversarial.py`

#### Problemas encontrados:

1. **Nombres ficticios no detectados**
   - spaCy es_core_news_lg esta entrenado en periodismo, no ficcion
   - Nombres inventados (Eldric, Kael, Zara-7) pasan desapercibidos
   - F1 esperado ~60-70% ya documentado en el codigo

2. **Nombres compuestos con preposicion fragmentados**
   - "Luis de la Fuente" -> no detectado como entidad unica
   - "Juan de la Cruz" -> fragmentado

3. **Entidades en textos cortos**
   - Textos de 1-2 oraciones no dan suficiente contexto al NER
   - Mismo nombre en texto largo se detecta mejor

4. **Clasificacion incorrecta (MISC en vez de PER)**
   - Algunos nombres espanoles clasificados como MISC
   - BUG REAL: "Maria Sanchez" aparecio como CONCEPT en produccion

---

### 2.4 MEDIA: Speaker Attribution (69.4% pass rate)

**Archivo**: `test_speaker_attribution_adversarial.py`

#### Problemas encontrados:

1. **Verbos de habla no normalizados** (19 fallos)
   - "grito Juan" -> no se detecta (patron verbo-nombre)
   - "murmuro Pedro" -> fallo
   - "Maria dijo:" (nombre-verbo) -> fallo
   - "anadio" no reconocido como verbo de habla

2. **Dialogos interrumpidos no soportados**
   - "—Ven aqui —dijo Juan levantandose— ahora mismo."
   - Dialogos anidados con comillas dentro de rayas

---

### 2.5 ALTA: Character Location (~58% pass rate)

**Archivo**: `test_character_location_adversarial.py`

#### Problemas encontrados:

1. **57 errores de infraestructura** (modulo no totalmente implementado)
2. **Clausulas subordinadas de llegada** no detectadas
   - "Al entrar Juan en la sala..." -> no se detecta
3. **Secuencias de ubicacion** no rastreadas correctamente

---

### 2.6 BAJA: Knowledge Temporal (89.5% pass rate)

**Archivo**: `test_knowledge_temporal_adversarial.py`

Modulo con mejor rendimiento. Solo 2 fallos:
- Anachronismo en dialogo escuchado por tercero
- Conocimiento implicito (actuar sobre info no aprendida)

---

## 3. Bugs Reales Confirmados

### Bug 1: Attribute Cross-Assignment (CRITICO)
- **Sintoma**: Todos los atributos de Maria asignados a Juan
- **Causa raiz**: `_find_nearest_entity()` usa proximidad de caracteres sin resolver pronombres
- **Cuando ocurre**: LLM y embeddings fallan -> solo pattern extraction funciona -> proximity fallback
- **Impacto**: Todos los atributos de un parrafo van al ultimo personaje mencionado

### Bug 2: Entity Type Misclassification (ALTO)
- **Sintoma**: "Maria Sanchez" clasificada como CONCEPT
- **Causa raiz**: spaCy es_core_news_lg clasifica como MISC -> mapea a CONCEPT
- **Agravante**: El fusionador rechaza fusion de CHARACTER + CONCEPT del mismo nombre

### Bug 3: strip_accents elimina ñ (MEDIO)
- **Sintoma**: Normalizacion de "niño" -> "nino" en vez de preservar ñ
- **Causa raiz**: NFD descompone ñ en n + combining tilde (Mn), que se filtra
- **Fix**: Recomponer NFC antes de filtrar, o excluir ñ especificamente

### Bug 4: Accent-insensitive fusion blocked (MEDIO)
- **Sintoma**: "Jose Garcia" vs "Jose Garcia" no se fusionan
- **Causa raiz**: `_are_different_proper_names()` compara sin normalizar acentos
- **Fix**: Aplicar `normalize_for_comparison()` antes de la comparacion de nombres propios

---

## 4. Plan de Mejora

### Sprint E1: Fixes Criticos (Atributos)

**Objetivo**: Subir pass rate de attribute extraction de 25% a 60%

| Tarea | Impacto | Complejidad |
|-------|---------|-------------|
| E1.1: Integrar resolucion de pronombres en `_find_nearest_entity()` | Alto | Media |
| E1.2: Detectar genero del pronombre (ella/el/su) y filtrar candidatos | Alto | Baja |
| E1.3: Respetar limites de oracion/parrafo para proximity window | Alto | Baja |
| E1.4: Detectar negacion ("no era", "no tenia") antes de asignar | Medio | Baja |
| E1.5: Manejar atributos en dialogos (vincular al sujeto del verbo de habla) | Medio | Alta |
| E1.6: Implementar resolucion de comparaciones ("mas alto que X") | Bajo | Alta |

**Detalle E1.1**: Modificar `_find_nearest_entity()` para:
```
1. Buscar pronombre sujeto en contexto inmediato (ella/el/este/esta)
2. Si hay pronombre gendered -> filtrar candidatos por genero
3. Si hay cambio de parrafo -> resetear sujeto
4. Si hay sujeto eliptico -> usar sujeto del verbo anterior
```

**Detalle E1.4**: Anadir deteccion de negacion:
```python
NEGATION_PATTERNS = [
    r'\bno\s+(?:era|tenia|fue|habia)\b',
    r'\bsin\s+',
    r'\ba\s+pesar\s+de\s+no\b',
    r'\bnunca\s+(?:fue|tuvo|habia)\b',
]
```

### Sprint E2: Fixes de Fusion

**Objetivo**: Subir pass rate de entity fusion de 71% a 90%

| Tarea | Impacto | Complejidad |
|-------|---------|-------------|
| E2.1: Normalizar acentos ANTES de `_are_different_proper_names()` | Alto | Baja |
| E2.2: Permitir fusion cross-type para mismo nombre exacto | Alto | Baja |
| E2.3: Consultar aliases ANTES del name_filter | Medio | Baja |
| E2.4: Fix `strip_accents()` para preservar ñ (recomponer NFC) | Medio | Baja |
| E2.5: Strip preposiciones interiores en normalizacion | Bajo | Media |

**Detalle E2.1** (fix rapido):
```python
def _are_different_proper_names(self, e1, e2):
    # Normalizar antes de comparar
    n1 = normalize_for_comparison(e1.canonical_name)
    n2 = normalize_for_comparison(e2.canonical_name)
    if n1 == n2:
        return False  # Mismo nombre normalizado -> NO son diferentes
    # ... resto de la logica
```

**Detalle E2.2** (fix rapido):
```python
def _are_compatible_types(self, e1, e2):
    # Si el nombre es EXACTAMENTE igual, siempre permitir fusion
    if e1.canonical_name.lower() == e2.canonical_name.lower():
        return True
    # ... resto de la logica
```

**Detalle E2.4** (fix strip_accents):
```python
def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize('NFD', text)
    # Preservar ñ: la tilde combinante de ñ es U+0303 (COMBINING TILDE)
    # Solo filtrar cuando NO precede a 'n' o 'N'
    result = []
    for i, c in enumerate(normalized):
        if unicodedata.category(c) == 'Mn':
            # Preservar combining tilde despues de n/N (= ñ/Ñ)
            if c == '\u0303' and i > 0 and normalized[i-1].lower() == 'n':
                result.append(c)
                continue
            continue  # Skip other diacritics
        result.append(c)
    return unicodedata.normalize('NFC', ''.join(result))
```

### Sprint E3: Mejoras NER

**Objetivo**: Subir pass rate NER de 53% a 70%

| Tarea | Impacto | Complejidad |
|-------|---------|-------------|
| E3.1: Expandir gazetteer con nombres ficticios del proyecto actual | Alto | Baja |
| E3.2: Post-procesado NER: reclasificar MISC con heuristicas (nombre+apellido -> PER) | Alto | Media |
| E3.3: Mejorar deteccion de nombres compuestos con preposiciones | Medio | Media |
| E3.4: Usar contexto (verbos de accion, posesivos) para inferir entidades no detectadas | Medio | Alta |

**Detalle E3.2**:
```python
def post_process_ner(entities):
    for ent in entities:
        if ent.label == EntityLabel.MISC:
            # Heuristica: si tiene estructura de nombre propio espanol
            if looks_like_spanish_person_name(ent.text):
                ent.label = EntityLabel.PER
                ent.confidence *= 0.9  # Slight penalty
```

### Sprint E4: Speaker Attribution

**Objetivo**: Subir pass rate de 69% a 85%

| Tarea | Impacto | Complejidad |
|-------|---------|-------------|
| E4.1: Expandir lista de verbos de habla (grito, murmuro, exclamo, etc.) | Alto | Baja |
| E4.2: Soportar patron nombre-verbo ("Maria dijo:") | Alto | Baja |
| E4.3: Soportar dialogos interrumpidos por accion | Medio | Media |
| E4.4: Normalizar verbos de habla conjugados | Medio | Baja |

### Sprint E5: Character Location

**Objetivo**: Resolver errores de infraestructura y subir pass rate de 58% a 75%

| Tarea | Impacto | Complejidad |
|-------|---------|-------------|
| E5.1: Fix errores de infraestructura (57 errors en tests) | Critico | Media |
| E5.2: Detectar llegadas en clausulas subordinadas | Medio | Media |
| E5.3: Rastrear secuencias de ubicacion multi-capitulo | Medio | Alta |

---

## 5. Prioridades de Implementacion

### Prioridad 1 (Impacto inmediato, baja complejidad)
1. **E2.1**: Normalizar acentos en fusion (~30 min)
2. **E2.2**: Permitir fusion cross-type mismo nombre (~30 min)
3. **E2.3**: Consultar aliases antes de name_filter (~30 min)
4. **E2.4**: Fix strip_accents para ñ (~30 min)
5. **E1.2**: Filtrar candidatos por genero del pronombre (~1-2h)
6. **E1.3**: Respetar limites de parrafo en proximity (~1h)
7. **E4.1**: Expandir verbos de habla (~30 min)

### Prioridad 2 (Impacto alto, complejidad media)
8. **E1.1**: Integrar resolucion de pronombres en atributos (~3-4h)
9. **E1.4**: Detectar negacion (~1-2h)
10. **E3.2**: Post-procesado NER MISC->PER (~2h)
11. **E4.2**: Patron nombre-verbo en speaker attribution (~1h)
12. **E5.1**: Fix infraestructura character location (~2h)

### Prioridad 3 (Mejoras a largo plazo)
13. **E1.5**: Atributos en dialogos (~4-6h)
14. **E3.3**: Nombres compuestos con preposiciones (~3h)
15. **E3.4**: Inferencia de entidades por contexto (~6h)
16. **E5.3**: Secuencias de ubicacion multi-capitulo (~4h)

---

## 6. Metricas Objetivo

| Modulo | Actual | Objetivo Sprint E | Objetivo Final |
|--------|--------|-------------------|----------------|
| Attribute extraction | 25-35% | 60% | 80% |
| Entity fusion | 71% | 90% | 95% |
| NER recognition | 53% | 70% | 80% |
| Speaker attribution | 69% | 85% | 90% |
| Character location | 58% | 75% | 85% |
| Knowledge temporal | 89% | 95% | 95% |
| Pipeline E2E | 61% | 75% | 85% |

### Como medir progreso
```bash
# Ejecutar suite completa
pytest tests/adversarial/ -q --tb=no

# Ejecutar modulo especifico
pytest tests/adversarial/test_cross_entity_attribute_adversarial.py -q --tb=no

# Generar reporte detallado
pytest tests/adversarial/ -v --tb=short > adversarial_report.txt
```

---

## 7. Apendice: Estructura de Tests

```
tests/adversarial/
├── __init__.py
├── test_attribute_adversarial.py          # 60 cases (existente)
├── test_ner_adversarial.py                # 75 cases (existente)
├── test_coreference_adversarial.py        # ~80 cases (existente)
├── test_vital_status_adversarial.py       # ~60 cases (existente)
├── test_emotional_coherence_adversarial.py # ~40 cases (existente)
├── test_character_location_adversarial.py  # ~60 cases (existente)
├── test_speaker_attribution_adversarial.py # 62 cases (existente)
├── test_document_classification_adversarial.py # 76 cases (existente)
├── test_knowledge_temporal_adversarial.py  # 19 cases (existente)
├── test_analysis_adversarial.py           # 26 cases (existente)
├── test_cross_entity_attribute_adversarial.py  # 29 cases (NUEVO)
├── test_entity_fusion_adversarial.py      # 76 cases (NUEVO)
└── test_pipeline_e2e_adversarial.py       # 52 cases (NUEVO)
```

**Total: 818+ tests adversariales** (157 nuevos en iteracion anterior, + E2E pipeline completo)

---

## 8. Analisis E2E del Pipeline Completo (UnifiedAnalysisPipeline)

**Fecha**: 2026-01-30 | **Metodo**: 3 manuscritos realistas con inconsistencias plantadas

Se ejecuto el pipeline completo (`UnifiedAnalysisPipeline`) sobre 3 manuscritos de prueba:
- **Ficcion**: 4 capitulos, 6 inconsistencias plantadas (cabello, edad, piso, pierna, chaqueta)
- **No ficcion**: 3 capitulos, 1 inconsistencia temporal (fecha Cortes 1521 vs 1519)
- **Policiaco**: 3 capitulos, 3 inconsistencias plantadas (edad, hijos, ciudad)

### 8.1 Resultados por Manuscrito

| Manuscrito | Entidades | Atributos | Dialogos | Capitulos | Alertas | Errores Pipeline |
|-----------|-----------|-----------|----------|-----------|---------|-----------------|
| Ficcion   | 29        | 11        | 31       | 4         | 148     | 3 errores API   |
| No ficcion| 28        | 1         | 0        | 3         | 67      | 3 errores API   |
| Policiaco | 27        | 9         | 29       | 3         | 130     | 3 errores API   |

### 8.2 Desglose de Alertas (Ficcion, 148 total)

| Categoria | Count | Observacion |
|-----------|-------|-------------|
| orthography/spelling_typo | 58 | **MAYORIA FALSE POSITIVES** (`\n\n` = saltos de parrafo) |
| orthography/spelling_case | 43 | Falsos positivos en nombres propios y dialogos |
| style/coherence_break | 23 | Muchos son transiciones normales entre escenas |
| repetition/word_echo | 16 | Nombres de personajes contados como repeticiones |
| style/sticky_sentence | 8 | Logica invertida: 0% glue words marcado como "pegajoso" |
| **consistency/** | **0** | **NINGUNA inconsistencia detectada de 6 plantadas** |

### 8.3 BUGS CRITICOS del Pipeline

#### Bug P1: Entity Fusion API Rota
```
EntityFusionService.merge_entities() got an unexpected keyword argument 'session_id'
```
- **Impacto**: Las entidades NUNCA se fusionan. "Maria", "Maria Garcia", "Garcia", "profesora Garcia" son 4 entidades separadas
- **Causa**: Cambio de API en merge_entities() sin actualizar la llamada en el pipeline
- **Gravedad**: CRITICA (rompe toda la cadena de analisis posterior)

#### Bug P2: Attribute Persistence Rota
```
'ExtractedAttribute' object has no attribute 'attribute_type'
```
- **Impacto**: Los atributos extraidos no se guardan en la base de datos
- **Causa**: Modelo `ExtractedAttribute` no tiene campo `attribute_type` pero el persistence layer lo espera
- **Gravedad**: ALTA (atributos no se persisten para comparacion entre capitulos)

#### Bug P3: Emotional Coherence API Rota
```
EmotionalCoherenceChecker.analyze_chapter() got an unexpected keyword argument 'entities'
```
- **Impacto**: Analisis emocional completamente inoperativo
- **Causa**: Cambio de API sin actualizar llamada
- **Gravedad**: MEDIA

#### Bug P4: Spelling Checker Marca Parrafos como Errores
- **Sintoma**: Cada `\n\n` (salto de parrafo) genera alerta CRITICA: "Error ortografico: '\n\n'"
- **Impacto**: ~60% de alertas de ortografia son falsos positivos
- **Causa**: El checker no filtra whitespace/newlines antes de verificar
- **Gravedad**: ALTA (inunda la UI con ruido)

#### Bug P5: Dialogue Speaker Attribution = 0%
- **Sintoma**: 0 de 60 dialogos tienen speaker atribuido, incluso con marcadores explicitos ("dijo Maria", "pregunto Pedro")
- **Causa**: Sin coreference activo, no hay fallback a patrones basicos de verbo de habla
- **Gravedad**: ALTA

#### Bug P6: Attribute Proximity Bias Confirmado en Pipeline Real
- **Ejemplos reales encontrados**:
  - `hair_color=negro` asignado a entidad "alta" (la palabra previa), no a "Maria Garcia"
  - `hair_color=rubio` asignado a "Dos semanas" (expresion temporal), no a "Maria"
  - `eye_color=azules` asignado a "Primero envenenada" (concepto basura), no a "Elena"
  - `color=rojo` asignado a "vestido", no al personaje victima
  - `distinctive_feature=noche` y `distinctive_feature=enemigos` asignados a "Torres" (palabras aleatorias)
- **Gravedad**: CRITICA (los atributos extraidos son mayoritariamente basura)

### 8.4 Deteccion de Inconsistencias Plantadas

| Inconsistencia | Detectada? | Motivo del fallo |
|---------------|-----------|-----------------|
| Cabello Maria: negro -> rubio | NO | "rubio" asignado a "Dos semanas", no a Maria |
| Edad Maria: 32 -> 35 | NO | Edad no extraida como atributo (no hay patron regex) |
| Piso despacho: 2o -> 5o | NO | Ubicaciones de personajes no rastreadas |
| Pierna Pedro: izq -> der | NO | Lateralidad no extraida como atributo |
| Chaqueta Pedro: marron -> negra | NO | Color de ropa no asignado correctamente |
| Edad Pedro: 25 -> 28 | NO | Edad no comparada temporalmente |
| Cortes: 1521 vs 1519 | NO | Analisis temporal desactivado (experimental) |
| Edad Isabel: 40 -> 35 -> 38 | NO | Edad no extraida correctamente |
| Hijos Isabel: 1 -> 2 | NO | No hay patron para numero de hijos |
| Ciudad ex-marido: Bcn -> Valencia | NO | No hay tracking de ubicacion de personajes |

**Tasa de deteccion de inconsistencias: 0/10 = 0%**

### 8.5 Lo Que Funciona Bien

1. **Deteccion de capitulos**: 100% (4/4, 3/3, 3/3) con titulos correctos
2. **Deteccion de dialogos**: Buena (31, 0, 29 dialogos detectados con marcador —)
3. **Entidades principales**: Maria, Pedro, Torres, Elena, Isabel detectados
4. **Ubicaciones**: Salamanca, Madrid, Barcelona, Valencia detectados
5. **Profesiones**: "profesora", "doctora", "abogada", "doctor" correctamente asignados
6. **Repeticiones lexicas**: Funcional (detecta ecos de palabras repetidas)
7. **Coherencia narrativa**: Funcional (detecta saltos de tema y cambios de POV)

### 8.6 Lo Que No Funciona

1. **0% de inconsistencias detectadas** (critico - es la funcion principal del sistema)
2. **~70% de alertas son ruido** (spelling FP, character name echoes, inverted sticky logic)
3. **Fusion de entidades rota** (bug de API)
4. **Atributos asignados a entidades incorrectas** (proximity bias)
5. **Ningun dialogo con speaker** (0% atribucion)
6. **Entidades duplicadas** sin fusionar (Maria x4, Torres x2, Isabel x3)
7. **Clasificacion de tipo incorrecta** ("Carmen" como CONCEPT, "Petroglobal" como CHARACTER)

### 8.7 Plan de Accion Inmediato (Pre-Sprint E1)

Estos son fixes de infraestructura que deben resolverse ANTES de los sprints de mejora:

| # | Fix | Gravedad | Complejidad |
|---|-----|----------|-------------|
| P0.1 | Fix API mismatch en `merge_entities()` (quitar `session_id`) | CRITICA | Baja |
| P0.2 | Fix persistence de atributos (`attribute_type` missing) | ALTA | Baja |
| P0.3 | Fix API mismatch en `EmotionalCoherenceChecker` | MEDIA | Baja |
| P0.4 | Filtrar `\n\n` y whitespace en spelling checker | ALTA | Baja |
| P0.5 | Excluir nombres de entidades del detector de repeticiones | MEDIA | Baja |
| P0.6 | Fix logica invertida en sticky sentences (0% != sticky) | MEDIA | Baja |
| P0.7 | Implementar fallback de speaker attribution por patron de verbo | ALTA | Media |

**Impacto esperado tras P0**: Reducir alertas de ruido de ~70% a <10%, habilitar fusion de entidades, permitir persistencia de atributos

---

## 9. Evaluacion por Metodo (Precision / Recall / F1)

**Fecha**: 2026-01-30 | Archivo: `tests/adversarial/test_method_evaluation.py`

### 9.1 NER (Named Entity Recognition)

| Metodo | Precision | Recall | F1 | Notas |
|--------|-----------|--------|-----|-------|
| spaCy base (es_core_news_lg) | 1.00 | **1.00** | **1.00** | Excelente en textos con contexto. Incluso detecta Eldric/Kael |
| NERExtractor (post-procesado) | 0.00 | 0.00 | 0.00 | **BUG**: API rota, devuelve resultados incompatibles |

**Conclusion NER**: spaCy base funciona muy bien. El post-procesado del NERExtractor rompe los resultados. Petroglobal se clasifica como PER en vez de ORG (label accuracy < text recall).

### 9.2 Entity Fusion

| Metodo | Precision | Recall | F1 | Notas |
|--------|-----------|--------|-----|-------|
| Normalizacion (titulos/prefijos) | **1.00** | **0.90** | **0.95** | Solo falla en diminutivos (Paco/Francisco) |
| String similarity (SequenceMatcher 0.7) | 1.00 | 0.30 | 0.46 | Demasiado conservador, solo exactos |
| Semantic (embeddings) | 0.00 | 0.00 | 0.00 | **BUG**: should_merge() rechaza todos los casos |
| Combined(any) | 1.00 | 0.90 | 0.95 | Igual que normalizacion (domina el voto) |
| Combined(majority) | 1.00 | 0.30 | 0.46 | Igual que string_sim (semantic siempre NO) |

**Conclusion Fusion**: La normalizacion es el metodo dominante y funciona bien (F1=0.95). La fusion semantica esta rota (BUG en should_merge). String similarity es demasiado estricta. Falta soporte para diminutivos y nicknames.

### 9.3 Attribute Extraction

| Metodo | Recall | Precision | Notas |
|--------|--------|-----------|-------|
| Patterns (regex) | ~55% | ~67% | Detecta color, altura. Bug: proximity bias (hair -> "alta") |
| Dependency (spaCy) | 0% | N/A | **BUG**: devuelve 0 atributos siempre |
| Embeddings | N/A | N/A | Requiere modelo cargado |
| LLM (Ollama) | N/A | N/A | Ollama caido durante tests |
| Combined (votacion) | **45%** | **82%** | 9/20 correctos, 1 entidad incorrecta |

**Detalle por caso de atributos combinados**:
- Caso 1 (Maria, descriptiva): 3/3 OK + 1 wrong entity (hair -> "alta")
- Caso 2 (Pedro, adjetivo): 1/3 OK (solo ojos, no rubio ni carpintero)
- Caso 3 (Ana, titulo): 1/2 OK (profesion si, pelo no)
- Caso 4 (Carlos/Lucia, 2 personajes): 1/4 OK (solo Carlos alto)
- Caso 5 (Martinez, titulo+desc): 2/3 OK (profesion + delgado, no canoso)
- Caso 6 (Elena, negacion): 0/2 OK (negacion no detectada, atributo a "no")
- Caso 7 (Rosa, dialogo): 0/1 OK (autodescripcion en dialogo no detectada)
- Caso 8 (Juan/Pablo, comparacion): 1/2 OK (Pablo si, Juan no)

**Problemas clave encontrados**:
1. `_extract_by_dependency()` devuelve 0 resultados siempre (BUG)
2. Proximity bias asigna al token anterior, no a la entidad correcta
3. Negacion "no era alta" genera atributo positivo (BUG)
4. Atributos en dialogo no detectados (0%)
5. Escenas multi-personaje pierden atributos del segundo personaje
6. "rubio" en "joven rubio" no se extrae (patron no reconocido)

### 9.4 Resumen Comparativo

```
                    Precision  Recall   F1      Estado
NER (spaCy base)      1.00      1.00   1.00    EXCELENTE
Fusion (normalizacion) 1.00     0.90   0.95    MUY BUENO
Fusion (semantica)     0.00     0.00   0.00    ROTO
Atributos (combinado)  0.82     0.45   0.58    DEFICIENTE
Atributos (dependencia) N/A     0.00   0.00    ROTO
Speaker attribution    N/A      0.00   0.00    ROTO sin coref
Consistencia           N/A      0.00   0.00    NO FUNCIONA
```

### 9.5 Recomendaciones por Metodo

1. **NER**: No tocar spaCy base. Arreglar NERExtractor wrapper.
2. **Fusion**: Arreglar should_merge() API. Normalizacion funciona excelente.
3. **Atributos**: Arreglar dependency extractor (prioridad 1). Corregir proximity bias. Implementar deteccion de negacion.
4. **Speaker**: Implementar fallback de patrones basicos sin coreference.
5. **Consistencia**: Depende de que atributos se extraigan correctamente primero.

### 9.6 Votacion vs Metodo Individual

En TODOS los sistemas evaluados, **un unico metodo domina**:
- NER: spaCy base solo > spaCy + post-procesado
- Fusion: Normalizacion sola = Combined(any) >> Combined(majority)
- Atributos: Patterns solo > Combined (porque dependency/embeddings/LLM fallan)

**Conclusion**: La votacion multi-metodo NO mejora resultados actualmente porque:
1. Los metodos secundarios estan rotos (dependency=0, semantic=0, LLM caido)
2. Cuando un metodo falla, arrastra el voto combinado
3. Se recomienda **arreglar cada metodo individualmente** antes de optimizar la votacion
