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

**Total: 818 tests adversariales** (157 nuevos en esta iteracion)
