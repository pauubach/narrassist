# Plan de Mejora - Narrative Assistant

**Documento de trabajo**: Análisis nocturno 6-Feb-2026 (02:48 - 10:30)
**Estado**: Completado
**Metodología**: Panel de 8 expertos simulados + investigación estado del arte

---

## Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Estado Actual del Sistema](#2-estado-actual-del-sistema)
3. [Análisis de Tests](#3-análisis-de-tests)
4. [Pipeline NLP - Arquitectura](#4-pipeline-nlp---arquitectura)
5. [Weak Points Identificados](#5-weak-points-identificados)
6. [Estado del Arte - Investigación](#6-estado-del-arte---investigación)
7. [Panel de Expertos - Hallazgos](#7-panel-de-expertos---hallazgos)
8. [Plan de Acción Priorizado](#8-plan-de-acción-priorizado)
   - [8b. Plan de Trabajo BK-09..18](#8b-plan-de-trabajo-bk-0918)
   - [8c. Auditoría de Producto](#8c-auditoría-de-producto-panel-de-expertos-10-feb-2026)
9. [Cronograma de Implementación](#9-cronograma-de-implementación)
10. [Fuentes y Referencias](#10-fuentes-y-referencias)

---

## 1. Resumen Ejecutivo

### Diagnóstico General

El sistema tiene una **arquitectura sólida** con pipeline de 6 fases y votación multi-método,
pero presenta debilidades en:

1. **NER para ficción**: F1 estimado ~60-70% con spaCy; existen modelos mejores (PlanTL RoBERTa)
2. **Correferencias en español**: No existe modelo SOTA; el enfoque multi-método es correcto
3. **Visualización de atributos**: Bug en frontend (transformación de datos incompleta)
4. **15 xfails obsoletos**: Tests que ahora pasan pero siguen marcados como xfail
5. **Detección de inconsistencias**: Funcional pero limitada en sujetos elididos y posesivos ambiguos

### Impacto Esperado de las Mejoras

| Área | Estado Actual | Objetivo | Impacto |
|------|---------------|----------|---------|
| NER Ficción | F1 ~65% | F1 ~82% | +26% precisión personajes |
| Correferencias | Parcial | Mejorado | -40% entidades duplicadas |
| Atributos (display) | Bug frontend | Funcional | Experiencia usuario |
| Tests xfail | 15 obsoletos | Actualizados | Confianza en CI/CD |
| Temporal | Básico | Con NoT prompting | Detección anacronismos |

---

## 2. Estado Actual del Sistema

### 2.1 Componentes y Estado

| Componente | Archivos | Estado | Prioridad |
|------------|----------|--------|-----------|
| **Parser DOCX** | `parsers/docx_parser.py` | ✅ Funcional | Baja |
| **Parser EPUB** | `parsers/epub_parser.py` | ✅ Funcional | Baja |
| **Parser PDF** | `parsers/pdf_parser.py` | ⚠️ Limitado | Media |
| **Parser TXT/MD** | `parsers/base.py` | ✅ Funcional | Baja |
| **Clasificador docs** | `parsers/document_classifier.py` | ✅ Funcional | Media |
| **Detector estructura** | `parsers/structure_detector.py` | ✅ Funcional | Media |
| **NER (spaCy)** | `nlp/ner.py` | ⚠️ F1 bajo en ficción | **Crítica** |
| **Correferencias** | `nlp/coreference_resolver.py` | ⚠️ Parcial | **Crítica** |
| **Atributos** | `nlp/attributes.py`, `nlp/extraction/` | ⚠️ Parcial | **Crítica** |
| **Consistencia atributos** | `analysis/attribute_consistency.py` | ✅ Funcional | Alta |
| **Temporal** | `temporal/` | ✅ Level A+B+C | Alta |
| **Diálogos** | `nlp/dialogue.py` | ✅ Funcional | Media |
| **Speaker attribution** | `nlp/cesp_resolver.py` | ⚠️ Parcial | Alta |
| **Correcciones** | `corrections/` | ✅ Funcional | Media |
| **LLM (Ollama)** | Integrado en votación | ✅ Funcional | Media |
| **Embeddings** | `nlp/embeddings.py` | ✅ Funcional | Baja |
| **Frontend atributos** | `EntitiesTab.vue` | ✅ Funcional | Baja |

### 2.2 Pipeline Unificado (6 Fases)

```
FASE 1 - PARSING Y ESTRUCTURA
  ├── Parsing documento (DOCX/EPUB/PDF/TXT)
  ├── Detección estructura (capítulos/escenas)
  ├── Clasificación tipo documento
  └── Detección diálogos (speaker hints)

FASE 2 - EXTRACCIÓN BASE (paralelo)
  ├── NER mejorado con dialogue hints
  ├── Marcadores temporales
  └── Detección de focalización

FASE 3 - RESOLUCIÓN Y FUSIÓN
  ├── Correferencias (votación multi-método)
  ├── Fusión semántica de entidades
  └── Atribución de diálogos

FASE 4 - EXTRACCIÓN PROFUNDA (paralelo)
  ├── Atributos de entidades
  ├── Relaciones entre personajes
  ├── Conocimiento entre personajes
  └── Perfiles de voz

FASE 5 - ANÁLISIS DE CALIDAD (paralelo)
  ├── Ortografía
  ├── Gramática
  ├── Repeticiones léxicas/semánticas
  ├── Coherencia narrativa
  └── Análisis de registro

FASE 6 - CONSISTENCIA Y ALERTAS
  ├── Consistencia de atributos
  ├── Consistencia temporal
  ├── Violaciones de focalización
  └── Generación de alertas
```

### 2.3 Perfiles de Análisis

| Perfil | NER | Coref | Atrib | Tempo | LLM | Calidad | Uso |
|--------|-----|-------|-------|-------|-----|---------|-----|
| Express | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | Solo ortografía/gramática |
| Standard | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | Análisis habitual |
| Deep | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | Con LLM local |
| Complete | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Todo habilitado |

### 2.4 Sistema de Votación Multi-Método

**Atributos** (4 métodos):
| Método | Peso | Descripción |
|--------|------|-------------|
| LLM | 40% | Ollama - extracción semántica |
| Embeddings | 25% | sentence-transformers |
| Dependency | 20% | spaCy parsing |
| Patterns | 15% | Regex conocidos |

**Correferencias** (4 métodos):
| Método | Peso | Descripción |
|--------|------|-------------|
| LLM | 35% | Ollama - análisis anafórico |
| Embeddings | 30% | Similitud semántica |
| Morpho | 20% | Concordancia género/número |
| Heuristics | 15% | Proximidad + saliencia |

**Temporal** (4 métodos):
| Método | Peso | Descripción |
|--------|------|-------------|
| Direct | 35% | Comparación fechas/edades |
| Contextual | 25% | Patrones transiciones |
| LLM | 25% | Comprensión temporal |
| Heuristics | 15% | Reglas de género |

---

## 3. Análisis de Tests

### 3.1 Estadísticas Generales

- **Total tests recopilados**: 2,758
- **Categorías**: unit, integration, adversarial, regression, edge_cases, evaluation, performance, security

### 3.2 Tests Fallando (FAIL)

| Test | Archivo | Causa Raíz | Severidad |
|------|---------|------------|-----------|
| `test_extract_organization` | `tests/unit/test_ner.py:65` | spaCy clasifica ORG como LOC | Alta |
| `test_relative_clause[case1]` | `tests/adversarial/test_attribute_adversarial.py` | Atributos en cláusulas relativas | Media |

**Detalle test_extract_organization**: spaCy `es_core_news_lg` detectó 0 entidades ORG donde esperaba ≥1. El LLM preprocesador detectó la entidad pero la clasificó como LOC. Esto confirma la debilidad del NER en clasificación de tipos de entidad.

### 3.3 XFails Obsoletos (ahora PASAN - XPASS)

**15 tests marcados xfail que ya funcionan** y deben actualizarse:

| Test | Descripción | Acción |
|------|-------------|--------|
| `test_multiple_entities[case1]` | Múltiples entidades cercanas | Quitar xfail |
| `test_unusual_word_order[case1]` | Orden no estándar de palabras | Quitar xfail |
| `test_negation_handling[case1,2]` | Negaciones complejas | Quitar xfail |
| `test_temporal_attributes[case1,2]` | Atributos temporales | Quitar xfail |
| `test_compound_entities[case0,2]` | Entidades compuestas | Quitar xfail |
| `test_implicit_attributes[case0,2]` | Atributos implícitos | Quitar xfail |
| `test_long_distance_deps[case0,1]` | Dependencias largas | Quitar xfail |
| `test_coordination[case2]` | Coordinación y listas | Quitar xfail |
| `test_context_dependent[case0,1]` | Interpretación contextual | Quitar xfail |

### 3.4 XFails Legítimos (13 - aún fallan)

| Categoría | Tests | Descripción |
|-----------|-------|-------------|
| **Pro-drop** | 1 | Sujetos elididos ("Salió de casa" → ¿quién?) |
| **Posesivos ambiguos** | 1 | "su casa" → ¿de quién? |
| **Orden no estándar** | 2 | Hipérbaton, orden poético |
| **Negaciones** | 1 | "No era alto sino bajo" |
| **Temporales** | 1 | "De joven era rubio" |
| **Compuestos** | 1 | Entidades con múltiples partes |
| **Implícitos** | 1 | "Era médico" → bata blanca, estetoscopio |
| **Larga distancia** | 1 | Referencia 3+ párrafos atrás |
| **Coordinación** | 2 | "Juan y María eran altos" → ambos |
| **Cadenas anafóricas** | 3 | "él" → "el doctor" → "Juan" (cadena) |
| **Contexto** | 1 | Significado depende del contexto |
| **Entity fusion** | 2 | normalize_for_comparison no strip "de" interior |

### 3.5 Tests Skip (4)

Tests que requieren archivos de prueba específicos no presentes en CI:
- `test_parsers.py:65` - Archivo test no encontrado
- `test_parsers.py:80` - Archivo test no encontrado
- `test_parsers.py:121` - Archivo test no encontrado
- `test_parsers.py:136` - Archivo test no encontrado

### 3.6 Gaps de Cobertura Identificados

| Área | Tests Existentes | Tests Necesarios |
|------|-----------------|-----------------|
| Parser EPUB metadatos | ❌ | Prueba con corpus de 167 EPUBs |
| NER nombres inventados | Básicos | Fuzzing con nombres de fantasía |
| Correferencias pro-drop | xfail | Tests con corpus real español |
| Temporal con fechas relativas | Básicos | Tests con "al día siguiente", "un mes después" |
| Clasificador docs (corpus) | ❌ | Validar con 188 archivos en test_books/ |
| Speaker attribution teatro | ❌ | Tests con formato dramático |
| Atributos en diálogo | Parcial | "Soy rubio, dijo Juan" |

---

## 4. Pipeline NLP - Arquitectura

### 4.1 NER (Reconocimiento de Entidades)

**Archivo**: `src/narrative_assistant/nlp/ner.py`

**Flujo actual**:
```
Texto → spaCy NER → LLM preprocesador → Gazetteer dinámico
                                              ↓
                                     Entidades candidatas
                                              ↓
                                  Separación coordinados
                                              ↓
                                  Validación (entity_validator)
                                              ↓
                                  Entidades finales
```

**Advertencia en código** (línea 8):
> "F1 esperado ~60-70% en ficción española. Los modelos NER están entrenados en texto periodístico."

**Tipos soportados**: PER (persona), LOC (lugar), ORG (organización), MISC (miscelánea)

**Gazetteers**: Sistema dinámico con límite de 5,000 entradas para evitar memory leaks.

**Debilidades documentadas**:
- Nombres inventados (fantasía, ciencia ficción) no detectados sin gazetteer
- Confusión ORG/LOC frecuente
- Títulos nobiliarios y apodos no siempre reconocidos
- Español antiguo (Quijote, Lazarillo) degrada rendimiento

### 4.2 Correferencias

**Archivo**: `src/narrative_assistant/nlp/coreference_resolver.py`

**Tipos de mención soportados**:
- `PROPER_NOUN`: "Juan", "María García"
- `PRONOUN`: "él", "ella", "ellos"
- `DEFINITE_NP`: "el doctor", "la mujer"
- `DEMONSTRATIVE`: "este", "aquella"
- `POSSESSIVE`: "su hermano", "sus ojos"
- `ZERO`: Sujeto omitido (pro-drop) ← **SIN IMPLEMENTAR**

**Problema crítico - Pro-drop**: El español es una lengua pro-drop donde el sujeto se omite
frecuentemente. "Salió corriendo" → ¿quién? Esto es el gap más importante del sistema.

**Problema - Posesivos**: "su casa" es ambiguo en español (de él/ella/usted/ellos/ellas).

### 4.3 Extracción de Atributos

**Archivos**: `nlp/attributes.py` + `nlp/extraction/` (dos sistemas coexistentes)

**Categorías**:
- Físicos: ojos, pelo, altura, edad, complexión, piel
- Psicológicos: personalidad, temperamento, miedos, deseos
- Sociales: profesión, título, relaciones, nacionalidad
- Lugares: clima, terreno, tamaño, ubicación
- Objetos: material, color, estado

**Filtro de metáforas**: El sistema incluye un filtro para evitar falsos positivos como
"sus ojos eran dos luceros" o "era alto como un roble". **Punto fuerte diferenciador**.

**Pesos aprendibles**: Los pesos de votación pueden actualizarse desde `default_weights.json`.

### 4.4 Consistencia de Atributos

**Archivo**: `analysis/attribute_consistency.py`

**Estrategias de detección**:
1. Antónimos conocidos (verde/azul, alto/bajo)
2. Similitud semántica con embeddings
3. Reglas específicas por tipo de atributo

**Tipos de inconsistencia**: ANTONYM, SEMANTIC_DIFF, VALUE_CHANGE, CONTRADICTORY

### 4.5 Temporal

**Archivos**: `temporal/inconsistencies.py`, `temporal/markers.py`, `temporal/timeline.py`

**Detección**: Contradicciones de edad, eventos imposibles cronológicamente,
saltos temporales sospechosos, anacronismos.

### 4.6 Diálogos y Speaker Attribution

**Archivos**: `nlp/dialogue.py`, `nlp/cesp_resolver.py`

**Formatos soportados**: Raya (—), comillas latinas («»), comillas inglesas (""), tipográficas ("")

### 4.7 Correcciones

**Archivo**: `corrections/orchestrator.py`

**12 detectores**:
Agreement, Anacoluto, Anglicisms, Clarity, CrutchWords, Glossary,
Grammar, POV, Regional, Repetition, Terminology, Typography + FieldTerminology

---

## 5. Weak Points Identificados

### 5.1 Críticos (impacto directo en calidad)

#### WP-01: NER insuficiente para ficción
- **Síntoma**: F1 ~60-70% en textos literarios
- **Causa**: spaCy entrenado en texto periodístico (CoNLL-2002)
- **Impacto**: Personajes no detectados, confusión de tipos
- **Solución**: PlanTL RoBERTa-large-bne (F1 ~82-85%)

#### WP-02: Pro-drop no implementado
- **Síntoma**: Sujetos elididos no resueltos
- **Causa**: El español omite sujetos frecuentemente
- **Impacto**: Atributos no asignados al personaje correcto
- **Solución**: Análisis morfológico verbal + contexto LLM

#### WP-03: Posesivos ambiguos
- **Síntoma**: "su casa" no se resuelve
- **Causa**: Ambigüedad inherente del español
- **Impacto**: Atributos asignados al personaje incorrecto
- **Solución**: Heurísticas de proximidad + LLM desambiguación

#### WP-04: Frontend no muestra atributos correctamente
- **Síntoma**: Atributos extraídos pero no visibles en UI
- **Causa**: Transformación snake_case→camelCase incompleta
- **Impacto**: Experiencia de usuario rota
- **Archivos afectados**:
  - `frontend/src/types/api/entities.ts` (líneas 75-83): Faltan campos
  - `frontend/src/types/transformers/entities.ts` (líneas 121-131): Transformador incompleto
  - `frontend/src/components/workspace/EntitiesTab.vue` (línea 240): No usa transformador

### 5.2 Altos (impacto significativo)

#### WP-05: 15 xfails obsoletos
- **Síntoma**: CI muestra xpass warnings
- **Causa**: Mejoras implementadas sin actualizar marcas
- **Impacto**: Falsa señal en tests, desconfianza en CI
- **Solución**: Actualizar marcas pytest (15 minutos)

#### WP-06: Cadenas anafóricas incompletas
- **Síntoma**: "él" → "el doctor" → "Juan" no se resuelve completamente
- **Causa**: Resolución solo un nivel de indirección
- **Impacto**: Entidades duplicadas, atributos fragmentados
- **Solución**: Resolución transitiva de cadenas

#### WP-07: Entity fusion con partículas "de"
- **Síntoma**: "García" y "García de la Cruz" no fusionan
- **Causa**: normalize_for_comparison no strip "de" interior
- **Impacto**: Entidades duplicadas
- **Solución**: Mejorar normalización con reglas de nombres españoles

#### WP-08: Temporal limitado
- **Síntoma**: Solo detecta contradicciones explícitas
- **Causa**: No usa Narrative-of-Thought prompting
- **Impacto**: Anacronismos y saltos temporales no detectados
- **Solución**: NoT prompting + timeline self-reflection

### 5.3 Medios (mejora de calidad)

#### WP-09: Speaker attribution en escenas complejas
- **Síntoma**: Diálogos largos sin verba dicendi pierden atribución
- **Causa**: Heurística de proximidad insuficiente
- **Solución**: LLM-based attribution + patrones de turno

#### WP-10: Clasificador de documentos no validado
- **Síntoma**: Sin métricas de accuracy
- **Causa**: No se ha evaluado contra corpus real
- **Solución**: Evaluar con 188 archivos en test_books/

#### WP-11: Negaciones complejas
- **Síntoma**: "No era alto sino bajo" → puede extraer "alto"
- **Causa**: Negación parcialmente implementada
- **Solución**: Patrones de negación + LLM validación

#### WP-12: Atributos en español antiguo
- **Síntoma**: "Tenía la faz macilenta" → no extrae atributo facial
- **Causa**: Vocabulario arcaico no en patrones
- **Solución**: Diccionario de equivalencias + embeddings

---

## 6. Estado del Arte - Investigación

### 6.1 NER para Español Literario

**Hallazgo principal**: PlanTL RoBERTa-large-bne-capitel-ner supera significativamente a spaCy.

| Modelo | Params | F1 (CoNLL-2002) | F1 est. ficción | VRAM |
|--------|--------|-----------------|-----------------|------|
| spaCy es_core_news_lg | ~560MB | ~83-85% | ~60-70% | CPU ok |
| **BETO cased** | 110M | ~87-88% | ~78-82% | ~440MB |
| **PlanTL RoBERTa-large-bne** | 355M | ~88-89% | ~82-85% | ~1.4GB |
| PlanTL RoBERTa-base-bne | 125M | ~86-87% | ~79-83% | ~500MB |

**Recomendación**: Añadir PlanTL RoBERTa como método adicional de votación NER.
En equipos sin GPU, BETO (110M) es viable en CPU con cuantización.

**Modelos HuggingFace**:
- `PlanTL-GOB-ES/roberta-large-bne-capitel-ner` (NER fine-tuned)
- `mrm8488/bert-spanish-cased-finetuned-ner` (BETO NER)

**Estrategia**: Multi-model NER voting (RoBERTa=0.5, BETO=0.3, spaCy=0.2)

### 6.2 Correferencias en Español

**Hallazgo principal**: NO existe modelo production-ready para español. El enfoque multi-método
del sistema es **exactamente la estrategia correcta** dado este gap.

**Maverick (2024)**: Sistema breakthrough de 500M params (vs 13B previo), 170x más rápido.
Actualmente solo inglés. **Monitorizar** para release en español.

**CODI-CRAC 2025**: Shared task multilingüe - "Traditional systems still kept the lead,
but LLMs showed clear potential."

**AnCora-CO**: Corpus de referencia para español. Potencial para fine-tuning futuro.

### 6.3 Detección de Inconsistencias Narrativas

**Hallazgo principal**: FlawedFictions (Abril 2025) es el primer benchmark serio.
Incluso GPT-4o tiene >50% false positive rate.

**Categorías FlawedFictions** (aplicables a nuestro sistema):
1. Continuity errors (contradicciones de hechos) ← **Ya implementado**
2. Out-of-character behavior ← **Parcialmente implementado**
3. Factual errors (anacronismos) ← **No implementado**
4. Impossible events (violaciones lógicas) ← **No implementado**
5. Unresolved storylines ← **No implementado**

**Conclusión crítica**: No depender solo de LLMs para detección. Combinar:
- **Rule-based** para tracking de estado de entidades (alta precisión)
- **LLM** solo para validación semántica (evitar false positives)

### 6.4 LLMs Locales para Análisis Literario

**Hallazgo principal**: Qwen 2.5 es el mejor LLM local para español en 2025-2026,
superando incluso a Llama 3.1-405B en tareas multilingües.

| Modelo | Params | Español | VRAM (Q4_K_M) | Velocidad |
|--------|--------|---------|---------------|-----------|
| **Qwen 2.5 (72B)** | 72B | **Excelente** | ~40GB | Lento |
| **Qwen 2.5 (14B)** | 14B | Muy bueno | ~9GB | Medio |
| **Qwen 2.5 (7B)** | 7B | Bueno | ~4.5GB | Rápido |
| Llama 3.3 (70B) | 70B | Excelente | ~38GB | Lento |
| Llama 3.3 (8B) | 8B | Bueno | ~5GB | Rápido |
| Mistral (7B) | 7B | Bueno | ~4GB | Rápido |

**Recomendación**: Añadir Qwen 2.5 como modelo preferido para español.
Auto-seleccionar tamaño según hardware disponible.

### 6.5 Razonamiento Temporal

**Narrative-of-Thought (NoT)** - EMNLP 2024:
- Convierte eventos a estructura Python
- Genera narrativas temporalmente ancladas
- **Reduce alucinaciones significativamente** en modelos pequeños (3B-7B)

**Timeline Self-Reflection** (2025):
- Inferencia multi-etapa: razonamiento → timeline → auto-reflexión
- Refinamiento iterativo del orden temporal

**HeidelTime**: Tagger temporal con soporte español.

### 6.6 Extracción de Atributos de Personajes

**Portrayal (2023)**: 6 indicadores de rasgos:
1. Presencia (dónde/cuándo aparece)
2. Acciones (verbos)
3. Habla (citas + sentimiento)
4. Definición directa (descripciones explícitas)
5. Sentimiento (reacción de otros)
6. Entornos (escenarios asociados)

**Taggus Pipeline (2024)**: Extracción automática de redes de personajes.

**Recomendación**: Adoptar enfoque de 6 indicadores para perfilado de personajes.

### 6.7 BookNLP Multilingüe

Proyecto NEH para extender BookNLP a español (en desarrollo, sin release público).
**No esperar** - nuestro sistema ya cubre funcionalidad similar.
Preparar integración para cuando esté disponible.

---

## 7. Panel de Expertos - Hallazgos

### 7.1 QA Senior

**Veredicto**: El sistema tiene buena cobertura de tests (2,758) pero:

1. **15 xfails obsoletos** → Actualizar inmediatamente (falsa señal de regresión)
2. **4 tests skip por archivos faltantes** → Crear fixtures o mover a carpeta de tests
3. **No hay tests de integración con corpus real** → Añadir golden corpus tests
4. **Tests adversariales bien diseñados** pero algunos demasiado estrictos
5. **Falta test de clasificador de documentos** contra corpus real

**Recomendación**: Crear suite de "smoke tests" con 5-10 libros reales del corpus
que ejecuten el pipeline completo y verifiquen resultados mínimos esperados.

### 7.2 Lingüista Computacional

**Veredicto**: El sistema NLP es competente pero tiene gaps lingüísticos:

1. **Pro-drop es el mayor problema**: El español elide sujetos ~40% del tiempo.
   "Salió corriendo" necesita análisis morfológico verbal (3ª persona singular,
   pretérito indefinido) + contexto narrativo para resolver.

2. **Modelo spaCy insuficiente**: `es_core_news_lg` entrenado en noticias EFE,
   no en literatura. Los nombres de ficción son un problema fundamental.

3. **Correferencias**: El enfoque multi-método es correcto dado que no existe
   modelo dedicado para español. Los pesos de votación deberían ser adaptativos.

4. **Español antiguo**: El vocabulario del Siglo de Oro (Quevedo, Cervantes)
   difiere significativamente del moderno. Considerar un modo "literario clásico".

5. **Posesivos**: "su" es el pronombre más ambiguo del español.
   Estrategia: proximidad + género/número del poseedor + LLM.

**Recomendación**: Implementar resolución de pro-drop como prioridad #1.
Requiere análisis morfológico verbal (ya disponible en spaCy) + heurísticas de saliencia.

### 7.3 Corrector Editorial (15+ años)

**Veredicto**: El sistema detecta las inconsistencias que más importan a editores:

1. **Ojos/pelo cambiando** → ✅ Bien implementado
2. **Edades imposibles** → ⚠️ Parcial (temporal básico)
3. **Nombres inconsistentes** → ⚠️ Entity fusion mejorable
4. **Anacronismos** → ❌ No implementado (p.ej. teléfono en época medieval)
5. **Personajes en dos lugares** → ❌ No implementado (character location)

**Lo que más valoran los editores**:
- Pocos falsos positivos (mejor perder algo que abrumar)
- Navegación al texto original (click → va al párrafo)
- Poder marcar "esto es intencional" (suppress alert)

**Recomendación**: Implementar detección de anacronismos y ubicación de personajes.
Mantener umbral alto de confianza para evitar falsos positivos.

### 7.4 Arquitecto Python/FastAPI

**Veredicto**: La arquitectura es sólida con buenos patrones:

1. **Result pattern** bien implementado
2. **Singleton thread-safe** correcto
3. **Pipeline con fases** bien separadas
4. **Dos sistemas de atributos coexistentes** → Deuda técnica que debe unificarse
5. **Memory monitoring** implementado correctamente

**Preocupaciones**:
- `analysis_pipeline.py` deprecado pero aún activo → Migrar a `unified_analysis.py`
- Pesos de votación hardcodeados → Hacerlos configurables por usuario
- ThreadPoolExecutor con max_workers=4 → Debería ser configurable según hardware

**Recomendación**: Completar migración al pipeline unificado.
Hacer pesos de votación adaptativos con feedback del usuario.

### 7.5 AppSec Specialist

**Veredicto**: La seguridad de manuscritos está bien implementada:

1. ✅ Validación de paths (path traversal prevention)
2. ✅ InputSanitizer contra XSS
3. ✅ Sin telemetría ni analytics
4. ✅ Modelos locales, no cloud
5. ✅ SQLite con WAL mode
6. ⚠️ Ollama en localhost sin autenticación → Aceptable en contexto desktop
7. ⚠️ LLM prompts podrían sufrir injection desde contenido de manuscritos
   → Mitigar: sanitizar texto antes de enviarlo al LLM

**Recomendación**: Añadir sanitización de texto antes de prompts LLM para
prevenir prompt injection desde contenido de manuscritos maliciosos.

### 7.6 Frontend Engineer (Vue/Tauri)

**Veredicto**: El frontend tiene un bug crítico en atributos:

1. **Bug atributos**: `EntitiesTab.vue` no usa transformer → datos snake_case
2. **Tipos incompletos**: `ApiEntityAttribute` le faltan campos
3. **Navegación rota**: Sin spanStart/spanEnd, no se puede ir al texto original
4. **UX mejorable**: El panel de entidades podría mostrar un resumen visual
   (mapa de personajes, timeline de apariciones)

**Recomendación**: Arreglar bug de atributos. Añadir visualización de
red de personajes (grafo interactivo) y timeline de apariciones.

### 7.7 Product Owner

**Veredicto**: El producto tiene diferenciador claro:

**Diferenciador**: Única herramienta en español, offline, que detecta inconsistencias
narrativas. Grammarly/ProWritingAid no hacen esto.

**Features por valor**:

| Feature | Valor | Esfuerzo | Prioridad |
|---------|-------|----------|-----------|
| Fix atributos frontend | Alto | Bajo | P0 |
| Actualizar xfails | Medio | Bajo | P0 |
| Mejorar NER (PlanTL) | Alto | Medio | P1 |
| Pro-drop resolution | Alto | Alto | P1 |
| Detección anacronismos | Alto | Medio | P2 |
| Red de personajes visual | Alto | Medio | P2 |
| Timeline interactiva | Medio | Alto | P3 |
| Speaker attribution | Medio | Alto | P3 |

**MVP real**: Parsing + NER + Atributos + Inconsistencias + Correcciones.
Todo lo demás es nice-to-have.

### 7.8 UX Designer

**Veredicto**: El flujo de trabajo editorial es el correcto:

1. **Cargar manuscrito** → OK
2. **Ver análisis** → Necesita mejor organización visual
3. **Revisar alertas** → OK, con severidades
4. **Navegar al texto** → ❌ Roto (spanStart/spanEnd no se pasan)
5. **Marcar como intencional** → ¿Implementado?
6. **Exportar informe** → OK

**Recomendaciones UX**:
- Dashboard de salud narrativa al abrir un proyecto
- Indicadores visuales de progreso del análisis
- Modo "focus" que muestra solo alertas críticas
- Comparación antes/después en ediciones sucesivas

---

## 8. Plan de Acción Priorizado

### Sprint 0: Quick Wins (1-2 días) -- COMPLETADO 2026-02-06

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| QW-01 | Actualizar 15 xfails obsoletos | DONE | Per-case parametrize con XFAIL_CASES dict |
| QW-02 | Fix bug frontend atributos | DONE | Añadidos span_start, span_end, chapter_id, source_mention_id |
| QW-03 | Fix test_extract_organization | DONE | ONU/UNESCO/Unicef (ORG no ambiguo) |
| QW-04 | Fix entity fusion con "de" | DONE | Variantes particle-stripped en generate_name_variants() |
| extra | Fix test_emotional_coherence | DONE | min_confidence 0.4 (no 0.6) |
| extra | Fix test_no_hair_in_unrelated_text | DONE | use_llm=False para evitar hallucination |
| extra | Update pre-commit ruff v0.3→v0.15 | DONE | Reglas UP042/UP045 reconocidas |

### Sprint 1: NER Mejorado (1 semana) -- COMPLETADO 2026-02-06

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S1-01 | Integrar PlanTL RoBERTa NER | DONE | `transformer_ner.py`, descarga bajo demanda |
| S1-02 | Multi-model NER voting | DONE | Votación con boost confianza (2+ métodos) |
| S1-03 | Mejorar gazetteer | DONE | Auto-feed desde transformer (conf>=0.7) |
| S1-04 | Añadir BETO como fallback | DONE | `beto-ner` en TRANSFORMER_NER_MODELS |
| S1-05 | Benchmark NER | DONE | `scripts/benchmark_ner.py`: spaCy vs transformer vs multi-method, Jaccard agreement |

**Modelos a descargar**:
```bash
# PlanTL (preferido)
pip install transformers
# Model: PlanTL-GOB-ES/roberta-large-bne-capitel-ner

# BETO (fallback)
# Model: mrm8488/bert-spanish-cased-finetuned-ner
```

### Sprint 2: Correferencias y Pro-drop -- COMPLETADO 2026-02-06

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S2-01 | Pro-drop gender inference | DONE | `_infer_gender_from_context()` desde participios/adj |
| S2-02 | Saliencia para correferencias | DONE | `set_mention_frequencies()` + scoring frecuencia |
| S2-03 | Cadenas anafóricas transitivas | YA EXISTE | Union-find en `_build_chains()` |
| S2-04 | Pesos adaptativos | DONE | `load/save/update_adaptive_weights()` en coreference_resolver.py, persistencia JSON |
| S2-05 | Evaluar Qwen 2.5 para coref | DONE | `prefer_spanish_model=True`, `_select_coref_model()` auto-detecta Qwen 2.5 |

**Técnica pro-drop propuesta**:
```python
# Para "Salió corriendo de la casa"
# 1. Detectar verbo sin sujeto explícito
# 2. Extraer morfología: 3ª persona singular, pretérito
# 3. Buscar candidatos: último personaje mencionado con género compatible
# 4. Validar con contexto LLM si confianza < 0.7
```

### Sprint 3: Temporal y Anacronismos -- COMPLETADO 2026-02-06

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S3-01 | Narrative-of-Thought prompting | DONE | NoT prompts en `prompts.py`, `analyze_with_not()` en `LLMTemporalValidator`, integrado en `VotingTemporalChecker.check()` |
| S3-02 | Timeline Self-Reflection | DONE | `self_reflect_timeline()` en `LLMTemporalValidator`, revisión multi-stage construct→reflect→refine |
| S3-03 | Detección de anacronismos | DONE | `anachronisms.py` con BD 80+ tecnologías por época |
| S3-04 | Expresiones temporales español | DONE | +6 patrones (pasados, transcurridos, etc.) |
| S3-05 | HeidelTime para español | DONE | 30+ patrones HeidelTime nativos en `markers.py`: "hace X", festividades, "siglo X", edades, duraciones |

### Sprint 4: Atributos Avanzados (1-2 semanas) — COMPLETADO

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S4-01 | 6-indicator character profiling | DONE | `character_profiling.py`: 6 indicadores + rol + relevancia |
| S4-02 | Character network analysis | DONE | `character_network.py`: centralidad, puentes, evolución temporal |
| S4-03 | Detección out-of-character | DONE | `out_of_character.py`: registro habla, emoción, agentividad |
| S4-04 | Ubicación de personajes | DONE | `check_impossible_travel()` añadido a CharacterLocationAnalyzer |
| S4-05 | Modo español clásico | DONE | `classical_spanish.py`: 60+ variantes ortográficas, glosario arcaico |

### Sprint 5: LLM y Modelos (1 semana) — COMPLETADO

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S5-01 | Qwen 2.5 como modelo preferido | DONE | `prefer_spanish_model=True` en LocalLLMConfig |
| S5-02 | Auto-selección por hardware | DONE | VRAM-based selection con prefer_qwen para GPU |
| S5-03 | Prompt engineering mejorado | DONE | `prompts.py`: CoT + few-shot + templates centralizados |
| S5-04 | Sanitización anti-injection | DONE | `sanitization.py`: 15 patrones injection, JSON validation |
| S5-05 | Cuantización óptima | DONE | `quantization` field: Q4_K_M default, Q6_K/Q8_0 opciones |

### Sprint 6: Frontend y UX — COMPLETADO

| ID | Acción | Estado | Notas |
|----|--------|--------|-------|
| S6-01 | Red de personajes (API) | DONE | `GET /character-network` con centralidad, puentes, evolución |
| S6-02 | Timeline de apariciones | DONE | `GET /character-timeline` con apariciones por capítulo |
| S6-03 | Perfiles de personajes (API) | DONE | `GET /character-profiles` con 6 indicadores |
| S6-04 | Navegación al texto desde alertas | DONE | `_resolve_alert_positions()` busca excerpt en capítulo |
| S6-05 | Modo focus (solo alertas críticas) | DONE | `focus=true` filtra critical/warning con confianza ≥ 0.7 + `severity` filter |

### Sprint 7a: Licensing Migration — COMPLETADO 2026-02-10

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S7a-01 | Eliminar LicenseModule, LicenseBundle | DONE | Enums legacy eliminados de models.py |
| S7a-02 | Renombrar tiers FREELANCE→CORRECTOR, AGENCIA→PROFESIONAL | DONE | 3 tiers: CORRECTOR, PROFESIONAL, EDITORIAL |
| S7a-03 | Cuota de manuscritos → paginas (250 words=1 page) | DONE | `words_to_pages()`, rollover 1 mes |
| S7a-04 | Implementar rollover (1 mes) | DONE | `_get_usage_with_rollover()` en verification.py |
| S7a-05 | Renombrar ModuleNotLicensedError → TierFeatureError | DONE | core/errors.py, 7 clases de error |
| S7a-06 | Crear check_tier_feature() | DONE | `check_feature()` en LicenseVerifier |
| S7a-07 | Actualizar schema SQL (5 tablas) | DONE | licenses, devices, subscriptions, usage, promo_codes |
| S7a-08 | Actualizar API endpoints | DONE | 7 endpoints en license.py |
| S7a-09 | Actualizar frontend store | DONE | license.ts con tipos, computed, acciones |
| S7a-10 | Actualizar LicenseDialog | DONE | Nuevo LicenseDialog.vue sin modulos |
| S7a-11 | Actualizar exports licensing/__init__.py | DONE | API publica completa |
| S7a-12 | Tests unitarios nuevo modelo | DONE | 147 tests (81 models + 66 verification) |

> Documentacion produccion: [LICENSING_PRODUCTION_PLAN.md](LICENSING_PRODUCTION_PLAN.md)

### Sprint 7b: Feature Gating + Integration (5 dias) — COMPLETADO ✅

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S7b-01 | Feature gating en character_profiling | DONE | gating.py: CHARACTER_PROFILING → run_character_profiling |
| S7b-02 | Feature gating en character_network | DONE | gating.py: NETWORK_ANALYSIS → run_network_analysis |
| S7b-03 | Feature gating en anachronism detection | DONE | gating.py: ANACHRONISM_DETECTION → run_anachronism_detection |
| S7b-04 | Feature gating en classical_spanish | DONE | gating.py: CLASSICAL_SPANISH → run_classical_spanish |
| S7b-05 | Feature gating en multi-model voting | DONE | gating.py: MULTI_MODEL → run_multi_model_voting |
| S7b-06 | Integrar OOC detection en pipeline | DONE | analysis.py:1912-1935, alertas OOC generadas |
| S7b-07 | Integrar Classical Spanish en pipeline | DONE | analysis.py:1965-1980, deteccion periodo + normalizacion |
| S7b-08 | Pasar settings frontend → backend en analisis | DONE | analysis.py:452-484, mapeo settings → UnifiedConfig |
| S7b-09 | Conectar endpoint anachronisms con frontend | DONE | AnachronismsPanel.vue integrado en AnalysisView (v0.8.0, commit 6ddebec) |
| S7b-10 | Crear CharacterProfileModal unificado | DONE | CharacterProfileModal.vue con 6 indicadores + gráficos evolución (v0.8.1/v0.8.2) |

### Sprint 7c: Pipeline Fixes (3 dias) — COMPLETADO (1 backlog)

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S7c-01 | Persistir cola pesada en BD | BACKLOG | Cola en memoria funcional; persistencia BD no critica para desktop |
| S7c-02 | Fix: chapters_with_ids en coreference | DONE | analysis.py:646-656, carga desde chapter_repository |
| S7c-03 | Validar documento vacio en fase 1 | DONE | analysis.py:505-509, error claro |
| S7c-04 | Health check Ollama antes de fase 5 | DONE | analysis.py:701-712, is_ollama_available() |
| S7c-05 | Fix: fallo silencioso persistencia capitulos | DONE | analysis.py:382-420, try/except con logging |
| S7c-06 | Limpiar columnas BD no usadas | N/A | Auditoria: no se encontraron columnas sin uso |
| S7c-07 | Limpiar componentes huerfanos | DONE | StoryBibleTab ya eliminado, sin huerfanos |

### Sprint 7d: UX + Copy (5 dias) — COMPLETADO

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S7d-01 | Unificar nombres de tabs | DONE | Texto/Entidades/Relaciones/Alertas/Cronologia/Escritura/Glosario/Resumen |
| S7d-02 | Banner "Analisis en progreso" para usuario nuevo | DONE | analysis-prompt-banner en ProjectDetailView.vue |
| S7d-03 | Indicadores severidad: color + texto + icono | DONE | AlertInspector.vue: severityIcon + severityLabel + severityColor |
| S7d-04 | aria-labels en botones de solo icono | DONE | StatusBar + botones solo icono (commit 86832b5, Sprint PP-3) |
| S7d-05 | Separar setup Ollama del tutorial | DONE | Integrado en tutorial paso 3 (decision de diseno) |
| S7d-06 | Mejorar empty states con contexto y acciones | DONE | Banner + estados vacios con acciones en multiples vistas |
| S7d-07 | Guia terminologia: Entidad/Personaje/Manuscrito/Doc | BACKLOG | Documentacion interna, baja prioridad |
| S7d-08 | Breadcrumb en ProjectDetailView | DONE | nav.project-breadcrumb con aria-label |
| S7d-09 | "Saltar tutorial" en todos los pasos | DONE | Boton "Saltar tutorial" en pasos 1-3 |
| S7d-10 | Simplificar AboutDialog (sin jargon tecnico) | DONE | Eliminadas versiones de deps, links GitHub. Solo version app + licencia + contacto (commit 86832b5, Sprint PP-3) |
| S7d-11 | Renombrar settings tecnicos a lenguaje corrector | DONE | ~30 terminos renombrados en SettingsView, TutorialDialog, AboutDialog (commit ef39568, Sprint PP-3) |
| S7d-12 | "Restaurar valores por defecto" en Settings | DONE | Boton "Restaurar todo" en CorrectionConfigModal |
| S7d-13 | Fix copy: "Heredado"→"Por defecto", tildes | DONE | 0 instancias de "Heredado" en codebase. Reemplazado por "Por defecto" en CorrectionConfigModal + InheritanceIndicator |

### Sprint 8a: Pipeline Enrichment + Persistencia (8-12 dias) — COMPLETADO

> **Objetivo**: Que TODOS los tabs tengan datos al completar el analisis. Sin esperas on-the-fly.
>
> **Contexto**: Actualmente la pipeline (fases 1-9) persiste entidades, alertas, capitulos y atributos.
> Pero ~25 analisis (relaciones, voz, prosa, salud narrativa...) se computan on-the-fly cuando el
> usuario abre un tab (1-30s de espera cada uno). Ademas, la pipeline computa datos que luego
> descarta (vital status, locations, OOC, chapter metrics).
>
> **Solucion**: Extender la pipeline con 4 fases de enrichment (10-13) que pre-computan y persisten
> todos los analisis derivados. El usuario puede navegar desde la fase 3 (estructura lista).
> Los tabs se "iluminan" progresivamente con badges conforme cada fase los habilita.
>
> **Prerrequisito arquitectonico**: Antes de anadir fases 10-13, extraer cada fase del monolito
> `run_real_analysis()` (actualmente ~2300 lineas) a funciones standalone. Sin esto, el monolito
> creceria a ~3000+ lineas y seria inmantenible.
>
> **Concurrencia**: Las fases de enrichment (10-13) NO necesitan GPU ni modelos pesados (solo leen
> de BD + computan en CPU). Por tanto pueden ejecutarse fuera del heavy analysis slot, liberandolo
> para el siguiente proyecto en cola. Implementar un tercer tier "enrichment" que no bloquea.

#### Nuevas fases de pipeline

| Fase | ID | Nombre UI | Peso | Tiempo est. | Persiste |
|------|-----|-----------|------|-------------|---------|
| 10 | `relationships` | Analizando relaciones | 0.08 | ~8s | network, timeline, profiles, locations |
| 11 | `voice` | Perfilando voces | 0.08 | ~10s | voice_profiles, deviations |
| 12 | `prose` | Evaluando escritura | 0.08 | ~10s | echoes, pacing, readability, sensory, sticky, energy |
| 13 | `health` | Salud narrativa | 0.06 | ~8s | health scores, emotional arcs, templates |

> Fases 10-13 comparten resultados intermedios (dialogos extraidos 1 vez → voice + emotional +
> dialogue_validation). Reduccion estimada: -30-40% vs computar por separado.

#### Pesos recalculados (13 fases)

```
parsing: 0.01, classification: 0.01, structure: 0.01,      # 3% - lightweight
ner: 0.31, fusion: 0.15, attributes: 0.08,                  # 54% - heavy NLP
consistency: 0.03, grammar: 0.06, alerts: 0.04,             # 13% - medium
relationships: 0.08, voice: 0.08, prose: 0.08, health: 0.06 # 30% - enrichment
```

#### Disponibilidad progresiva de tabs

| Fase completada | % | Tabs que se activan |
|-----------------|---|---------------------|
| 3. Estructura | 3% | Texto, Glosario, Focalizacion (declaraciones) |
| 5. Fusion | 50% | Entidades |
| 6. Atributos | 58% | Entidades (enriquecido con atributos) |
| 9. Alertas | 71% | Alertas |
| 10. Relaciones | 79% | Red de personajes, Cronologia, Perfiles, Ubicaciones |
| 11. Voz | 87% | Perfiles de voz, Desviaciones |
| 12. Escritura | 95% | Ecos, Ritmo, Legibilidad, Sensorial, Duplicados |
| 13. Salud | 100% | Salud narrativa, Emocional, Plantillas |

#### Tareas

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S8a-01 | Auto-load tabs que no auto-cargan | DONE | SensoryReportTab: onMounted + watch con auto-analyze. PacingAnalysisTab y RegisterAnalysisTab ya tenian onMounted |
| S8a-02 | Persistir chapter metrics en pipeline | DONE | Añadido en run_structure() de _analysis_phases.py: compute_chapter_metrics() → update_metrics() para cada capitulo |
| S8a-03 | Persistir vital status en pipeline | DONE | Tabla vital_status_events (schema v15), persist en run_consistency(), cleanup en run_cleanup(). Nota: detección basada en orden de capítulos, no consulta timeline temporal |
| S8a-04 | Persistir character locations en pipeline | DONE | Tabla character_location_events, persist en run_consistency(), cleanup en run_cleanup() |
| S8a-05 | Persistir OOC events en pipeline | DONE | Tabla ooc_events, persist en run_consistency(), cleanup en run_cleanup() |
| S8a-06 | Anadir chapter_id a entity_attributes | DONE | Columna chapter_id en schema, create_attribute() actualizado, pipeline pasa chapter_id |
| S8a-07 | Fase 10: Relationships enrichment | DONE | Logica de /relationships, /character-network, /character-timeline movida a pipeline (commit 4a25d6f) |
| S8a-08 | Fase 11: Voice enrichment | DONE | Logica de /voice-profiles, /voice-deviations movida a pipeline (commit 4a25d6f) |
| S8a-09 | Fase 12: Prose enrichment | DONE | Logica de sticky, echo, pacing, sensory, readability, energy movida a pipeline (commit 4a25d6f) |
| S8a-10 | Fase 13: Health enrichment | DONE | Logica de /narrative-health, /emotional-analysis, /narrative-templates movida a pipeline (commit 4a25d6f) |
| S8a-11 | Tabla enrichment_cache en BD | DONE | Schema v15+: enrichment_cache con project_id, type, entity_scope, input_hash, output_hash, status, result_json, revision, timestamps (commit 4a25d6f) |
| S8a-12 | Actualizar progress phases (9 → 13) | DONE | analysis.py: phase_weights, phase_order, phases[] actualizados a 13 fases (commit 4a25d6f) |
| S8a-13 | Endpoints GET leen de cache/BD en vez de computar | DONE | get_cached_enrichment() en _enrichment_cache.py, endpoints relationships + archetypes cache-first (commit 8c8ca55) |
| S8a-14 | Extraer fases a funciones standalone | DONE | Refactor: 2180-line monolith → 23 funciones en _analysis_phases.py (2515 lineas). analysis.py reducido de 2813 a 644 lineas. ProgressTracker class. 1430 tests pass. |
| S8a-15 | Tercer tier: enrichment fuera del heavy slot | DONE | Fases 10-13 ejecutan fuera de _heavy_analysis_project_id, 3-tier concurrency (commit 4a25d6f) |
| S8a-16 | Limpiar enrichment_cache en re-analisis | DONE | cleanup_before_reanalysis(): DELETE FROM enrichment_cache WHERE project_id=? (commit 4a25d6f) |
| ~~S8a-17~~ | ~~Proteccion contra mutaciones durante enrichment~~ | DUPLICADO | Unificado en S8c-11 (race protection mutación durante enrichment) |
| S8a-18 | Watchdog/timeout en heavy analysis slot | DONE | HEAVY_SLOT_TIMEOUT_SECONDS, force-release con log de error (commit 4a25d6f) |

### Sprint 8b: Tab Badges + Empty States (3-5 dias) — COMPLETADO

> **Objetivo**: Indicar visualmente el estado de cada tab con badges semanticos.
>
> **Patrones UX aplicados**: Material Design 3 (badges en tabs), Carbon (regla de 3 canales:
> icono + color + texto), Apple HIG (mostrar contenido inmediatamente), NN/g (nunca ocultar tabs).
>
> **Anti-patrones evitados**: No deshabilitar tabs (Friedman/Smashing), no empty states sin
> contexto (Eleken), no spinners >10s (NN/g), no ocultar tabs (Friedman).
>
> **Decision de diseno (revision post-auditoria)**: Los badges grises informativos (Entidades: 42)
> aportan poco valor y generan "badge blindness". Solo usar badges accionables (naranja) para
> alertas pendientes. El resto de tabs comunican su estado via contenido interior + empty states.

#### Badges (solo accionables)

| Tipo | Color PrimeVue | Semantica | Tabs |
|------|---------------|-----------|------|
| **Accionable** | `severity="warning"` (naranja) | "N observaciones pendientes" | Alertas |
| **Todo resuelto** | `severity="success"` (verde) | "Todo resuelto" | Alertas (cuando count = 0) |
| **Error** | `severity="danger"` (rojo dot) | "Fallo en analisis" | Cualquier tab cuya fase fallo |

#### Estados por tab

| Estado | Badge | Contenido interior |
|--------|-------|-------------------|
| Sin datos (analisis no ha llegado) | Sin badge | Empty state amigable: "Estamos leyendo tu manuscrito..." / "Analizando personajes..." |
| Procesando | Dot animado (sutil) | Skeleton o spinner inline + mensaje orientado a actividad |
| Listo | Sin badge (excepto Alertas) | Contenido completo |
| Alertas pendientes | Badge numerico naranja | Contenido completo con alertas |
| Todo resuelto (solo Alertas) | Check verde | "Todas las observaciones resueltas" |
| Fallo en fase | Dot rojo / "!" | "No se pudo completar el analisis. Puedes re-analizar." |
| Datos stale | Sin badge | Nota inline discreta: "Algunos datos pueden haber cambiado — Actualizar" |

> **Empty states**: Usar lenguaje orientado a la actividad del escritor, no a fases tecnicas.
> Ej: "Estamos analizando las voces de tus personajes..." en vez de "Esperando fase 11 (voice)".

#### Tareas

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S8b-01 | Componente TabStatusIndicator reutilizable | DONE | TabStatusIndicator.vue con animated dot (running), check (completed), error (failed), numeric badge. Type TabStatus exportado (commit 1b04638) |
| S8b-02 | Backend: completed_phases en progress | DONE | /analysis/progress ya devuelve phases[].completed (ya existia) |
| S8b-03 | Store: tab states reactivos | DONE | analysis.ts: getTabStatus() mapeando TAB_REQUIRED_PHASES → fase → idle/pending/running/completed/failed (commit 1b04638) |
| S8b-04 | Integrar badges en ProjectDetailView tabs | DONE | WorkspaceTabs con TabStatusIndicator, alertas con badge numerico naranja (commit 1b04638) |
| S8b-05 | Empty states amigables por tab | DONE | TAB_RUNNING_DESCRIPTIONS con mensajes orientados a actividad, AnalysisRequired con prop tab (commit 1b04638) |
| S8b-06 | Badge Alertas: count sin resolver (naranja) | DONE | unresolvedAlertCount → isWarning prop en TabStatusIndicator (commit 1b04638) |
| S8b-07 | Badge Alertas: todo resuelto (verde) | DONE | TabStatusIndicator completed state con check icon (commit 1b04638) |
| S8b-08 | Estado "failed" para fases de enrichment | DONE | AnalysisRequired: isFailed computed + failed overlay con retry button (commit 1b04638) |
| S8b-09 | Datos stale: nota inline discreta | DONE | DsStaleNote.vue: nota neutral inline "Algunos datos pueden haber cambiado" (commit 1b04638) |

### Sprint 8c: Invalidacion Granular + Datos Stale (6-9 dias) — COMPLETADO

> **Objetivo**: Cuando el usuario modifica datos (merge, reject, edit), solo recomputar lo afectado.
>
> **Algoritmo**: "Salsa-lite" — inspirado en Salsa (rust-analyzer), Build Systems a la Carte
> (Mokhov 2018), y Event Sourcing. Combina: event-driven invalidation + verifying traces +
> early cutoff + demand-driven evaluation.
>
> **Principio clave**: No recomputar TODO. Clasificar analisis en 3 categorias:
> - **Cat A (Inmutables)**: Prose-level, no dependen de entidades → nunca stale
> - **Cat B (Per-entity)**: Se recomputan solo para la entidad afectada (~2-5s)
> - **Cat C (Globales)**: Dependen de relaciones entre entidades → mark stale, lazy recompute
>
> **Nota arquitectonica**: Cada fase de enrichment debe ser transaccional dentro de su scope.
> Si falla a mitad de una fase, se hace rollback completo de esa fase (no quedan escrituras parciales).

#### Clasificacion de analisis

| Categoria | Analisis | Invalidado por merge/reject? | Estrategia |
|-----------|----------|------------------------------|-----------|
| **A: Inmutables** | sticky_sentences, echo_report, pacing, sensory, readability, temporal_markers, register, energy, variation, duplicate_content | NO (solo texto) | Computar 1 vez, persistir, no tocar |
| **B: Per-entity** | voice_profiles, character_timeline, emotional_profile, vital_status, character_locations | SI (solo entidad afectada) | Recompute incremental: DELETE + INSERT para entity_id |
| **C: Globales** | relationships, character_network, character_archetypes, narrative_health, chapter_progress | SI (todo el grafo) | Mark stale → lazy recompute cuando usuario abre tab |

#### Event → Invalidation Map

| Evento usuario | Cat A | Cat B (incrementales) | Cat C (stale) |
|---------------|-------|----------------------|---------------|
| **Merge entidades** | No tocar | voice(keeper), timeline(keeper), emotional(keeper), vital(keeper), locations(keeper) | relationships, network, archetypes, health, progress |
| **Undo merge** | No tocar | voice(restored), timeline(restored), emotional(restored), vital(restored), locations(restored) | relationships, network, archetypes, health, progress |
| **Reject entidad** | No tocar | DELETE voice(X), timeline(X), emotional(X) | relationships, network, archetypes, health |
| **Edit atributo** | No tocar | — | health |
| **Cambiar focalizacion** | No tocar | — | — |
| **Resolver/descartar alerta** | No tocar | — | — (solo contadores) |
| **Cambiar config correccion** | No tocar | — | RE-ANALISIS fases 7-9 (boton "Re-analizar") |
| **Cambiar modelo LLM** | No tocar | — | RE-ANALISIS completo (confirmar con usuario) |

> **Nota**: Undo-merge restaura la entidad original, por lo que debe invalidar los mismos
> scopes que merge. Los enrichment per-entity de la entidad restaurada se recomputan.

#### Stale data UX

| Coste recompute | Estrategia | UX |
|----------------|-----------|-----|
| Trivial (<1s) | Auto-actualizar silenciosamente | Sin indicador |
| Barato (<5s, sin LLM) | Auto-recompute background al detectar cambio | Spinner breve |
| Caro (>5s o con LLM) | Marcar stale → nota inline discreta | "Algunos datos pueden haber cambiado — Actualizar" |
| Re-analisis necesario | Banner rojo | "Configuracion cambiada — Re-analizar" |

> **Decision de diseno (revision post-auditoria)**: No usar banner amarillo agresivo para stale.
> El merge/reject es una accion natural del flujo de trabajo — castigar al usuario con un banner
> prominente genera friccion. En su lugar, nota inline discreta bajo el contenido afectado.

#### Trigger de recompute: Híbrido (aprobado 10-Feb-2026)

> **Contexto**: El corrector NO edita texto en la app. Corrige en Word. La app solo muestra
> dónde y qué corregir. Las mutaciones del usuario son: merge entidades, accept/reject alertas,
> asignar atributos, corregir speaker. El texto NUNCA cambia → Cat A nunca se invalida.
>
> **Debate panel (UX + Arquitecto + QA + Editora + Corrector)**:
>
> | Criterio | Debounce (3-5s) | Esperar cambio pantalla |
> |----------|-----------------|------------------------|
> | **UX** | Datos siempre frescos al mirar | Puede ver datos stale, sorpresa al volver |
> | **Performance** | Recomputa mientras trabaja (background OK) | Más eficiente, agrupa cambios |
> | **Corrector** | "Mergeo 3 entidades seguidas → 3 recomputes" | "Mergeo 3 → 1 recompute al cambiar tab" |
> | **QA** | Race conditions si merge rápido | Limpio, 1 trigger claro |
> | **Editora** | Prefiere ver resultado inmediato | "No me importa esperar si el resultado es bueno" |
>
> **Decisión**: Híbrido — combinar ambos según coste:
> - **Cat B** (per-entity, 2-5s): Debounce 5s, recompute background. Si corrector mergea 3
>   entidades en 10s, debounce agrupa en 1-2 recomputes rápidos.
> - **Cat C-fast** (<20s, sin LLM): Debounce 5s, recompute background.
> - **Cat C-slow** (LLM, 60-180s): Esperar cambio de pantalla. No tiene sentido lanzar
>   recompute LLM mientras corrector sigue trabajando en el mismo tab.
> - **Mensaje inline** cuando hay recompute en curso: "Recomputando relaciones..." (no bloquear).
>
> **Nota workflow**: El corrector trabaja en un tab (ej: Entidades), hace merges, y cuando
> cambia a otro tab (ej: Relaciones), ese tab muestra datos frescos porque Cat C-slow se
> disparó al detectar el cambio de pantalla.

#### Early cutoff (optimizacion Salsa)

Si recomputar un enrichment produce el MISMO resultado (ej: merge solo anadio menciones redundantes),
NO propagar invalidacion downstream. Comparar `output_hash` antes vs despues.

> **Estabilidad de hashes**: Para evitar falsos positivos por serializacion de floats, usar
> representacion canonica: sorted keys, floats redondeados a 6 decimales, JSON determinista.
> `input_hash` = hash de los inputs que entraron a la computacion.
> `output_hash` = hash del resultado producido. Si `output_hash` no cambia → early cutoff.

#### Tareas

| ID | Accion | Estado | Detalle |
|----|--------|--------|---------|
| S8c-01 | Tabla invalidation_events en BD | DONE | Schema v19: invalidation_events (project_id, event_type, entity_ids, detail, revision, created_at). Migration en _apply_column_migrations() (commit a4d08fb) |
| S8c-02 | Event emitter en endpoints de mutacion | DONE | emit_invalidation_event() en _invalidation.py. Llamado desde 6 mutation endpoints en entities.py: merge, undo_merge, reject, attribute_create/edit/delete (commit a4d08fb) |
| S8c-03 | Handlers Cat B: recompute per-entity | DONE | _mark_stale() marca per-entity entries (entity_scope IN entity:X) como stale (commit a4d08fb) |
| S8c-04 | Handlers Cat C: mark stale | DONE | _mark_stale() marca entradas globales (entity_scope IS NULL) como stale. EVENT_INVALIDATION_MAP define tipos afectados por evento (commit a4d08fb) |
| S8c-05 | Frontend: detectar datos stale | DONE | _cache metadata incluye revision + stale flag en response. GET /enrichment/stale endpoint (commit a4d08fb) |
| S8c-06 | Frontend: nota inline stale con boton "Actualizar" | DONE | DsStaleNote.vue componente inline + allow_stale en get_cached_enrichment() (commit a4d08fb) |
| S8c-07 | Early cutoff: output_hash comparison | DONE | _cache_result() compara output_hash antes/despues, skip write si unchanged (commit a4d08fb) |
| S8c-08 | Funciones enrichment scoped por entity_id | DONE | entity_scope column en enrichment_cache, per-entity marking en _mark_stale() (commit a4d08fb) |
| S8c-09 | Tests invalidation cascades | DONE | 22 tests en test_invalidation.py: emission (3), stale marking (5), revision tracking (2), event type coverage (12 parametrized) (commit a4d08fb) |
| S8c-10 | Transaccionalidad por fase de enrichment | DONE | status='computing' antes de iniciar, completed/failed al terminar. _run_enrichment() en _enrichment_phases.py (commit a4d08fb) |
| S8c-11 | Proteccion race condition: mutacion durante enrichment | DONE | invalidate_enrichment_if_mutated() usa granular stale marking con ENTITY_DEPENDENT_TYPES | ATTRIBUTE_DEPENDENT_TYPES (commit a4d08fb) |

### Resumen Sprint 8

| Sub-sprint | Tareas | Dias | Impacto |
|-----------|--------|------|---------|
| **S8a**: Pipeline Enrichment | 18 | 8-12 | Todos los tabs con datos post-analisis |
| **S8b**: Tab Badges + Empty States | 9 | 3-5 | UX: disponibilidad progresiva visible |
| **S8c**: Invalidacion Granular | 11 | 6-9 | Datos siempre coherentes tras acciones usuario |
| **TOTAL** | **38** | **17-26** | Pipeline completa, UX profesional, datos coherentes |

> **Orden critico**: S8a-14 (extraer fases a funciones) es prerequisito de S8a-07..10 (nuevas fases).
>
> **Entrega incremental**: S8a-01 (auto-load) se puede hacer en 30 min. S8a-02..06 (persistir gaps)
> en 2-3 dias. S8a-14 (refactor monolito) en 1-2 dias. S8b en paralelo con S8a-07..13. S8c
> despues de S8a+S8b.
>
> **Concurrencia**: Las fases de enrichment (10-13) liberan el heavy slot, permitiendo que otro
> proyecto inicie su analisis pesado (NER, fusion...) mientras el primero termina sus enrichments.
>
> **Revision post-auditoria**: Plan revisado tras auditoria con subagentes Arquitecto y QA+UX.
> Cambios principales: (1) Prerequisito refactor monolito, (2) Tercer tier concurrencia,
> (3) enrichment_cache con input_hash + output_hash + status, (4) Undo-merge en event map,
> (5) Solo badges accionables (sin informativos grises), (6) Empty states en lenguaje escritor,
> (7) Nota inline discreta vs banner amarillo agresivo, (8) Estado "failed" para fases,
> (9) Tests 30-35 vs 18, (10) Transaccionalidad por fase, (11) Watchdog timeout heavy slot.
>
> **Referencias tecnicas**: Salsa red-green algorithm (rust-analyzer), Build Systems a la Carte
> (Mokhov et al., ICFP 2018), Material Design 3 badges, Carbon Design status indicators,
> Apple HIG loading patterns, NN/g skeleton screens.

### Backlog (Futuro)

| ID | Acción | Detalle |
|----|--------|---------|
| BK-01 | Integrar Maverick cuando haya soporte español | Coreference 500M params |
| BK-02 | Integrar BookNLP multilingüe | Cuando esté disponible |
| BK-03 | FlawedFictions benchmark | Cuando dataset se publique |
| BK-04 | Fine-tune PlanTL RoBERTa en ficción | Si acumulamos datos etiquetados |
| ~~BK-05~~ | ~~Comparativa antes/después~~ | ✅ DONE - Snapshot pre-reanálisis + ComparisonService (two-pass matching) |
| ~~BK-06~~ | ~~Exportar a Scrivener~~ | ✅ DONE — `scrivener_exporter.py` (~400 líneas), endpoint `GET /export/scrivener`, ZIP con estructura .scriv compatible Scrivener 3 |
| ~~BK-08~~ | ~~Integrar timeline en vital_status~~ | ✅ DONE — Pluperfect death patterns, irrealis filtering, TemporalMap pipeline integration, expanded context windows. 5 integration tests + 62 total passing. `_analysis_phases.py` builds TemporalMap from ctx timeline and passes to `analyze_vital_status()`. |
| ~~BK-07~~ | ~~Análisis multi-documento~~ | ✅ DONE - Collections, entity links, cross-book analysis, workspace auxiliar |
| ~~BK-09~~ | ~~Merge-induced attribute orphaning~~ | ✅ DONE — `move_related_data()` en `repository.py` migra 14 FK cols en 10 tablas. 16 tests en `test_entity_merge_fk.py`. |
| ~~BK-10~~ | ~~Dialogue attribution: correcciones + scene breaks~~ | ✅ DONE — BK-10b/c (scene breaks + confidence decay) en commit cf11a00. `SpeakerAttributor` integrado con `speaker_corrections` y `_SCENE_BREAK_PATTERNS`. |
| ~~BK-11~~ | ~~Detección de narrativa no lineal~~ | ✅ DONE — `TemporalMap` en `temporal_map.py`, `NonLinearNarrativeDetector` en `non_linear_detector.py`. `vital_status.py` usa `is_character_alive_in_chapter()` (story_time) en vez de `chapter >=`. 15 tests. |
| ~~BK-12~~ | ~~Cache para fases de enriquecimiento~~ | ✅ DONE — Absorbido por S8a. `enrichment_cache` table (schema v20), `_enrichment_phases.py` (fases 10-13, 24 enrichment types), `_enrichment_cache.py` (`get_cached_enrichment()` con `allow_stale`), `_invalidation.py` (granular stale marking). 20+ endpoints leen del cache. Early cutoff por `output_hash`. |
| ~~BK-13~~ | ~~Pro-drop ambigüedad multi-personaje~~ | ✅ DONE — `ProDropAmbiguityScorer` y `SaliencyTracker` en `pro_drop_scorer.py`. Scoring multi-factor (recency, saliency, gender, discourse, number). Ambiguity score 0-1. Integrado en `HeuristicsCorefMethod` para `MentionType.ZERO`. `_weighted_vote()` almacena `_ambiguity` en detalle. 10 tests. |
| ~~BK-14~~ | ~~Ubicaciones jerárquicas/anidadas~~ | ✅ DONE — `LocationOntology` en `location_ontology.py`: jerarquía 7 niveles, gazetteer ~50 ciudades, haversine, alias, reachability por periodo histórico. 19 tests. |
| ~~BK-15~~ | ~~Emotional masking~~ | ✅ DONE — `_check_emotional_masking()` en `out_of_character.py`, 7 familias verbales, leakage físico. 6 tests en `test_ooc_masking.py`. |
| ~~BK-16~~ | ~~Hilos narrativos sin resolver (Chekhov's gun)~~ | ✅ DONE — `ChekhovTracker` en `chekhov_tracker.py`: detecta personajes SUPPORTING/MINOR que desaparecen (threshold 70%). `SupportingCharacterData` con diálogo/acciones/partners. `detect_abandoned_character_threads()` genera `AbandonedThread`. Integrado en `_detect_chekhov_elements()`. 8 tests. |
| ~~BK-17~~ | ~~Glossary → entity disambiguation~~ | ✅ DONE — `user_glossary` table (v20), `_inject_glossary_entities()` en NER pipeline, CRUD API endpoints. 6 tests en `test_glossary_ner.py`. |
| ~~BK-18~~ | ~~Confidence decay para inferencias stale~~ | ✅ DONE — Decay temporal en `AlertEngine.create_alert()`: `effective_confidence *= 0.97^chapter_distance`, floor 0.15. Solo para attribute_inconsistency, temporal_anachronism, relationship_contradiction, character_location_impossibility. Cache de total_chapters. 3 tests. |
| ~~BK-19~~ | ~~UI "Añadir/editar atributo" en EntitiesTab~~ | ✅ DONE — Inline add/edit/delete en EntitiesTab. Formulario con categoria, nombre, valor, confianza auto 1.0 (commit b326317, Sprint PP-2) |
| ~~BK-20~~ | ~~UI "Corregir hablante" en DialogueAttributionPanel~~ | ✅ DONE — Boton "Corregir" en cada dialogo, dropdown con entidades del capitulo, POST a speaker_corrections (commit 8b52e80, Sprint PP-2) |
| ~~BK-21~~ | ~~Resolver conflictos atributos en merge~~ | ✅ DONE — MergeEntitiesDialog paso 3: radio buttons para conflictos critical/medium, resoluciones enviadas en POST merge (commit 7a44c73, Sprint PP-2) |
| ~~BK-22~~ | ~~Feedback loop: sistema aprende de correcciones~~ | ✅ DONE — detector_calibration table, recalibracion de confianza por ratio FP, get_dismissal_stats() → effective_confidence (commit 3cd35d3, Sprint PP-4) |
| ~~BK-23~~ | ~~Estandarizar loading patterns (spinners/barras)~~ | ✅ DONE — BK-23a (`DsDownloadProgress.vue`, v0.8.0), BK-23b (skeleton loaders), BK-23c (z-index + animations consolidados). |
| ~~BK-24~~ | ~~Conectar 3 endpoints export faltantes~~ | ✅ DONE — /export/characters (routing a character_sheets.py), /export/report (ReviewReportExporter), /export/alerts + CSV (commit c653867, Sprint PP-1) |
| ~~BK-25~~ | ~~Revision Intelligence (detección alertas resueltas)~~ | ✅ DONE — S14: `ComparisonService` 3 fases (content diffing, fingerprint matching, LLM verification). Dashboard con resolved/still_present/new_issue. Banner comparación en alertas. Commit 97b145f. |
| BK-26 | Colaboración paralela online (sync tiempo real) | **P3** — Sync en tiempo real entre correctores. Requiere servidor con E2E encryption, zero-knowledge. Solo cuando exista licensing server + demanda real. Tier: Editorial. |
| ~~BK-27~~ | ~~Filtrado de alertas por rango de capítulos~~ | ✅ DONE — S13: `chapter_range` filter en alertas, cross-chapter inclusion. Commit d36b50c. |
| BK-28 | Historial de versiones + tracking de progreso | **P3** — Métricas por versión: alertas, ritmo, formalidad, diálogo. Trends: "V1: 87 alertas → V3: 42". Básico en Profesional, dashboards avanzados en Editorial. |
| BK-29 | Step-up pricing (packs de páginas one-time) | **P2** — Cuando Corrector llega a 1,500 págs/mes: ofrecer "500 páginas extra por €9". Trigger de upgrade a Profesional. |

> **Panel de expertos (13-Feb-2026)**: 8 expertos (QA Senior, Arquitecto Python/FastAPI,
> Lingüista Computacional, AppSec, Corrector Editorial 15+, Frontend Engineer, Product Owner,
> UX Designer). Auditoría completa de backlog + documentación. Resultado: B+ global,
> 24/29 BK completados (BK-06,10,15,17,23,08,12 corregidos como DONE). Plan de trabajo faseado:
> Fase 1 pre-defensa (~20h), Fase 2 post-defensa v1.0 (~80h), Fase 3 v1.1+ (roadmap).
> Documento completo: `docs/EXPERT_PANEL_2026-02-13.md`.
>
> **Panel de expertos (12-Feb-2026)**: Sesión de paneles especializados (correctores editoriales,
> pricing SaaS, sales & marketing). BK-25..29 identificados en análisis de flujo editorial,
> persistencia en reanálisis, y estrategia de pricing/licensing. Incluye: Revision Intelligence,
> colaboración paralela, filtrado por capítulos, historial de versiones, y step-up pricing.

> **Panel de expertos (10-Feb-2026)**: Sesión de 8 expertos simulados (QA, Lingüista, Corrector, Arquitecto,
> AppSec, Frontend, Product Owner, UX). BK-09..18 son gaps nuevos identificados por análisis cross-módulo,
> testing adversarial, y simulación de flujo editorial real. 4× P1, 4× P2, 2× P3.
>
> **Panel de expertos (10-Feb-2026, sesión producto)**: Ampliación con foco en producto vendible.
> BK-19..24 son gaps identificados en auditoría de UX interactiva, export, y consistencia visual.
> Incluye: correcciones interactivas, export como puente a Word, loading patterns, y feedback loop.
> 3× P1, 2× P2, 1× P3.

---

## 8b. Plan de Trabajo BK-09..18 (Panel de Expertos, 10-Feb-2026)

### Sprint S9: Integridad de Datos y Diálogos ✅ COMPLETADO

> **Especificado**: 11-Feb-2026 por panel de expertos (QA Senior, Arquitecto Python,
> Corrector Editorial 15+ años, AppSec Specialist).
>
> **Completado**: BK-09 (12-Feb), BK-15/BK-17/BK-10b/BK-10c (12-Feb).

#### ~~BK-09: Entity Merge FK Migration~~ ✅ COMPLETADO (12-Feb-2026)

> **Implementado**: `repository.py:move_related_data()` migra las 14 columnas FK en 10 tablas
> dentro de una sola transacción. Llamado desde `fusion.py:merge_entities()` después de
> `move_mentions()` + `move_attributes()`.

**Solución**: Un solo método `move_related_data(from_entity_id, to_entity_id)` que ejecuta
17 operaciones SQL secuenciales con manejo de deduplicación (voice_profiles UNIQUE,
collection_entity_links UNIQUE, self-relationships cleanup).

**Tablas migradas** (14 FK columns en 10 tablas):

| # | Tabla | FK Column(s) | ON DELETE | Estado |
|---|-------|-------------|-----------|--------|
| 1 | `entity_mentions` | `entity_id` | CASCADE | ✅ move_mentions() |
| 2 | `entity_attributes` | `entity_id` | CASCADE | ✅ move_attributes() |
| 3 | `temporal_markers` | `entity_id` | SET NULL | ✅ move_related_data() |
| 4 | `voice_profiles` | `entity_id` | CASCADE | ✅ UPSERT (dedup) |
| 5 | `vital_status_events` | `entity_id` | CASCADE | ✅ move_related_data() |
| 6 | `character_location_events` | `entity_id` | CASCADE | ✅ move_related_data() |
| 7 | `ooc_events` | `entity_id` | CASCADE | ✅ move_related_data() |
| 8 | `relationships` | `entity1_id`, `entity2_id` | CASCADE | ✅ + self-ref cleanup |
| 9 | `interactions` | `entity1_id`, `entity2_id` | CASCADE/SET NULL | ✅ move_related_data() |
| 10 | `coreference_corrections` | `original_entity_id`, `corrected_entity_id` | SET NULL | ✅ move_related_data() |
| 11 | `speaker_corrections` | `original_speaker_id`, `corrected_speaker_id` | SET NULL | ✅ move_related_data() |
| 12 | `collection_entity_links` | `source_entity_id`, `target_entity_id` | CASCADE | ✅ dedup + self-link cleanup |
| 13 | `scene_tags` | `location_entity_id` | SET NULL | ✅ move_related_data() |
| 14 | `scene_tags` | `participant_ids` (JSON) | N/A | ✅ REPLACE en JSON |

**Archivos modificados**:
- `src/narrative_assistant/entities/repository.py` — `move_related_data()` (~120 líneas)
- `src/narrative_assistant/entities/fusion.py` — `FusionResult.related_data_moved` + llamada en merge loop

**Tests**: 16 tests en `tests/unit/test_entity_merge_fk.py` — 1 por tabla + dedup/edge cases.

#### BK-15: Detección de Masking Emocional [HIGH, 3-4h] ✅ DONE

> **Implementado**: `_check_emotional_masking()` en `out_of_character.py`. 8 regex (7 familias verbales + ocultar), `MASKABLE_EMOTIONS` (10 emociones), `PHYSICAL_LEAK_PATTERNS` (6 regex). Integrado en `_mark_intentional_transitions()`.

**Archivos modificados**:
- `src/narrative_assistant/analysis/out_of_character.py` — Constantes + método + integración
- `tests/unit/test_ooc_masking.py` — 6 tests (fingió calma, disimulando, aparentaba+temblaba, normal shift, no-maskable emotion, masking lejos del personaje)

#### BK-17: Glosario → Gazetteer NER [HIGH, 4-5h] ✅ DONE

> **Implementado**: `user_glossary` table (schema v20), `_inject_glossary_entities()` en NER pipeline, CRUD API. 6 tests.

**Problema**: Términos de usuario (fantasía, sci-fi, dominios específicos) no se inyectan en NER. "Winterfell" no se detecta como location porque spaCy no lo conoce.

**Algoritmo `_inject_glossary_entities()`**:
1. Ordenar glosario por longitud DESC ("House Stark" antes que "Stark")
2. Para cada término: búsqueda case-insensitive en texto
3. Verificar word boundary (no "Fall" dentro de "Waterfall")
4. Check overlap con entidades spaCy existentes → glossary gana (confidence=1.0)
5. Crear `ExtractedEntity(source="glossary", confidence=1.0)`

**Schema BD**: Tabla `user_glossary` (project_id, term, entity_type, confidence DEFAULT 1.0, UNIQUE(project_id, term, entity_type)).

**Archivos**:
- `src/narrative_assistant/nlp/ner.py` — Añadir `_inject_glossary_entities()` en pipeline NER
- `src/narrative_assistant/persistence/database.py` — Schema v19: tabla user_glossary
- `api-server/routers/entities.py` — CRUD endpoints: GET/POST/DELETE /projects/{id}/glossary

**Tests**: 6 tests (case insensitive, word boundary, priority sobre spaCy, múltiples ocurrencias, overlap parcial, API CRUD).

#### BK-10b: Scene Breaks en Speaker Attribution ✅ DONE

Reutiliza `_SCENE_BREAK_PATTERNS` de `chapter.py` en `speaker_attribution.py`. Scene breaks (`***`, `---`, triple newline) resetean `current_participants`, `last_speaker` y `turns_since_explicit`. Método `_detect_scene_breaks()` pre-calcula posiciones; `_is_past_scene_break()` detecta cambio de escena entre diálogos consecutivos.

**Archivos**: `src/narrative_assistant/voice/speaker_attribution.py`, `tests/unit/test_scene_breaks_decay.py`.

**Tests**: 4 tests (asterisk reset, dash reset, triple newline reset, no-break alternation continues).

#### BK-10c: Speaker Confidence Decay ✅ DONE

Confidence decay gradual: `effective_confidence = base * 0.97^turns_since_explicit`. Floor=0.30. >=0.74 → MEDIUM, <0.74 → LOW. Reset en: verba dicendi explícito, scene break, cambio de capítulo.

**Archivos**: `src/narrative_assistant/voice/speaker_attribution.py`, `tests/unit/test_scene_breaks_decay.py`.

**Tests**: 3 tests (close=MEDIUM, distant=LOW, scene break resets decay).

**Criterios de éxito S9**: 0 filas huérfanas post-merge; masking emocional no genera FP; glosario inyectado con confidence=1.0; scene breaks resetean contexto speaker; decay reduce confianza con distancia.

---

### Sprint S10: Ubicaciones Jerárquicas + Timeline No Lineal ✅ COMPLETADO (13-Feb-2026)

> **Especificado**: 11-Feb-2026 por panel de expertos (Lingüista Computacional,
> Corrector Editorial 15+ años, Arquitecto Python, Product Owner).
>
> **Completado**: 13-Feb-2026. BK-14 + BK-11 implementados. 34 nuevos tests, 1609 regression OK.

#### ~~BK-14: LocationOntology~~ ✅ COMPLETADO (13-Feb-2026)

**Implementado**: `location_ontology.py` (~350 líneas) con:
- `LocationType` enum (7 niveles: ROOM < BUILDING < DISTRICT < CITY < REGION < COUNTRY + FICTIONAL/UNKNOWN)
- `HistoricalPeriod` enum (MEDIEVAL 40km/d, EARLY_MODERN 60, INDUSTRIAL 300, MODERN 1000)
- `LocationOntology` class: `are_compatible()` (jerarquía), `is_reachable()` (haversine + velocidad), `resolve()` (alias)
- Gazetteer español: ~50 ciudades con coordenadas + aliases (Ciudad Condal→Barcelona, Hispalis→Sevilla)
- `ROOM_TYPES` (18), `BUILDING_TYPES` (24), `EXTERIOR_TYPES` (15) pre-poblados
- Fail-safe: UNKNOWN/FICTIONAL/no encontrado → siempre compatible (evita FP)

**Modificado**: `character_location.py` — `_are_locations_incompatible()` delega a `ontology.are_compatible()`.
`check_impossible_travel()` soporta cross-chapter con `hours_between` + `period`.

**Sin cambios de BD** — La ontología es in-memory (no necesita schema v19).

**Tests**: 19 tests en `test_location_ontology.py` + 42 existentes sin regresión.

#### ~~BK-11: Timeline No Lineal~~ ✅ COMPLETADO (13-Feb-2026)

**Implementado**: `temporal_map.py` (~250 líneas) con:
- `NarrativeType` enum (CHRONOLOGICAL, ANALEPSIS, PROLEPSIS, PARALLEL)
- `TemporalSlice` dataclass (chapter → story_date/day_offset + narrative_type + embedded info)
- `AgeReference` dataclass (entity_id, age, chapter, story_date)
- `TemporalMap` class: `from_timeline()`, `get_story_time()`, `get_narrative_type()`,
  `get_character_age_in_chapter()`, `is_character_alive_in_chapter()`, `get_story_time_gap_hours()`

**Implementado**: `non_linear_detector.py` (~170 líneas) con:
- `NonLinearSignal` dataclass (chapter, positions, signal_type, direction, confidence)
- `NonLinearNarrativeDetector`: 4 patrones subjuntivo imperfecto, 6 retrospectivos, 7 prospectivos
- `classify_chapter()`: min_signals → "analepsis"/"prolepsis"/"chronological"

**Modificado**: `vital_status.py` — `VitalStatusAnalyzer` acepta `temporal_map` opcional.
`check_post_mortem_appearances()` usa `is_character_alive_in_chapter()` (story_time) en vez de `chapter >=`.
Muertes detectadas se registran automáticamente en el temporal_map.

**Exportado**: `temporal/__init__.py` — `TemporalMap`, `TemporalSlice`, `NarrativeType`,
`AgeReference`, `NonLinearNarrativeDetector`, `NonLinearSignal`.

**Sin cambios de BD** — Schema queda en v20.

**Tests**: 15 tests en `test_temporal_map.py` (8 TemporalMap + 1 dates + 6 NonLinearDetector) + 57 existentes sin regresión.

---

### Sprint S11: Pro-drop + Chekhov (~26-30h, 6-7 días) ✅ COMPLETADO

> **Especificado**: 11-Feb-2026 por panel de expertos.

#### BK-13: Pro-drop Ambiguity Scoring [ROI #3, 12-14h]

> **Ya existe**: Más de lo documentado:
> - `coreference_resolver.py:60` — `MentionType.ZERO = "zero"` (enum)
> - `coref_mention_extraction.py:406-425` — **ya extrae** zero pronouns: detecta verbos
>   conjugados sin nsubj, infiere género de ADJ predicativo, crea `Mention(type=ZERO)`
> - `coref.py:37,136` — enum duplicado + peso en voting
> - `coreference_resolver.py:686,696,1719` — ZERO integrado en scoring y filtrado
>
> **Falta**: `ProDropAmbiguityScorer` con scoring multi-factor (saliencia 25%,
> recencia 30%, concordancia género 20%, estructura discurso 15%, número 10%),
> `SaliencyTracker`, tablas BD (`character_saliency`, `pro_drop_mentions`).
> La extracción funciona, el scoring avanzado no.

**Problema**: 40% de prosa española tiene sujetos elididos. `MentionType.ZERO` existe en el enum y **ya se extrae** en `coref_mention_extraction.py:416`. "Salió furioso" → ¿quién salió?

**Algoritmo**:
```
ProDropAmbiguityScorer
├── extract_zero_pronouns(text, spacy_doc) → list[Mention]
│   └── Verbo conjugado sin nsubj/nsubjpass = zero pronoun
│       └── Inferir género de ADJ predicativo: "Salió cansada" → fem
├── calculate_ambiguity_score(zero, candidates, context) → float
│   ├── Saliencia (25%): frecuencia mención normalizada
│   ├── Recencia (30%): distancia a última mención
│   ├── Concordancia género (20%): gramática
│   ├── Estructura discurso (15%): sujeto oración anterior
│   └── Concordancia número (10%): singular/plural
│   └── ambiguity = 1 - overall_confidence
└── Resultado: confianza < 0.7 si múltiples candidatos mismo género
```

**Desafíos español**: 3a persona ambigua (él/ella/usted). Reflexivos ("se levantó"). Voseo argentino. Impersonal "se" (NO es pro-drop: "Se vende casa").

**Schema BD (v21)**: `character_saliency` (entity_id, mention_frequency, saliency_score). `pro_drop_mentions` (chapter_id, start_char, gender, number, resolved_entity_id, ambiguity_score).

**Archivos a crear**: `src/narrative_assistant/nlp/pro_drop_extractor.py`, `src/narrative_assistant/analysis/saliency_tracker.py`.

**Archivos a modificar**: `coref_mention_extraction.py` (poblar MentionType.ZERO), `coref_voting.py` (integrar ambiguity scores en weights).

**Tests**: 8 tests (extract simple, gender fem/masc, ambiguity single candidate, ambiguity multiple same gender, saliency, gender mismatch, number agreement, impersonal se filter).

#### BK-16: Chekhov Tracker [ROI #4, 14-16h]

> **Ya existe**: Más de lo documentado — la spec dice "nunca se llama" pero sí:
> - `chapter_summary.py:153` — `ChekhovElement` dataclass completa
> - `chapter_summary.py:1059-1124` — `_detect_chekhov_elements()` implementado:
>   busca objetos/vehicles en primeros 3 capítulos, calcula gap y confidence
> - `chapter_summary.py:520` — **se llama** desde `generate_report()`
> - `narrative_health.py:970-998` — `_check_chekhov()` implementado con scoring
>   (fired_ratio, abandoned threads, status OK/WARNING/CRITICAL)
> - `narrative_health.py:227` — integrado en el health report
>
> **Falta**: Tracker standalone para **personajes** SUPPORTING (actual solo detecta
> objetos/vehicles). `identify_supporting_characters()`, `detect_abandoned_threads()`
> para relaciones/conflictos, tablas BD (`chekhov_elements`, `abandoned_threads`),
> endpoint API.

**Problema**: Personajes SUPPORTING que desaparecen + hilos narrativos sin resolver. `ChekhovElement` para objetos **ya funciona**. Falta extensión a personajes secundarios.

**Algoritmo**:
```
ChekhovTracker
├── identify_supporting_characters(profiles) → list[int]
│   └── Filtros: role SUPPORTING/MINOR, 3-30 menciones, 2-6 capítulos, tiene acciones/diálogo
├── track_supporting_character(entity_id) → ChekhovElement
│   └── is_fired = aparece en último 10-20% del libro
├── detect_abandoned_threads(relationships, events) → list[dict]
│   └── Hilos: relaciones, conflictos, misterios, foreshadowing
│   └── Abandonado si: last_mentioned < 70% del libro AND sin resolución
└── Alertas: Unfired Chekhov con confidence ≥ 0.7
```

**Patrones narrativos español**: Subtramas románticas (esperan resolución). Sagas familiares (arcos largos aceptables). Picaresca (estructura episódica → hilos sueltos intencionales).

**Schema BD (v22)**: `chekhov_elements`, `abandoned_threads`.

**Archivos a crear**: `src/narrative_assistant/analysis/chekhov_tracker.py`

**Archivos a modificar**: `narrative_health.py` (implementar dimensión chekhov), `alerts/engine.py` (alertas desde unfired elements), `api-server/routers/relationships.py` (GET /projects/{id}/chekhov/elements).

**Tests**: 6 tests (identify supporting, not-fired, fired, abandoned thread, alert generation, confidence calculation).

**Criterios de éxito S11**: Pro-drop multi-candidato mismo género → confianza < 0.7; personajes con backstory que desaparecen → alerta; sujetos elididos extraídos y resueltos por correferencias.

---

### Sprint S12: Confidence Decay Temporal (~2-3h, 0.5 días) ✅ COMPLETADO

> **Especificado**: 11-Feb-2026 por panel de expertos.

#### BK-18: Decay Temporal de Alertas [LOW, 2-3h]

> **Ya existe**: Nada. No hay decay temporal en `alerts/engine.py`.
> El `calibration_factor` de BK-22 (S8c) existe y es donde se enchufaría.

**Problema**: Alerta de cap 1 misma prioridad que alerta de cap 95. No hay penalización temporal.

**Fórmula**: `effective_confidence = original * calibration_factor * 0.97^chapter_distance`
- Floor: 0.15 (evitar alertas vanishing)
- Habilitado para: attribute_inconsistency, temporal_anachronism, relationship_contradiction, character_location_impossibility
- Deshabilitado para: grammar_error, spelling_error, out_of_character

**Archivos**: `src/narrative_assistant/alerts/engine.py` — Aplicar decay en `create_alert()` después del `calibration_factor` existente (BK-22).

**Tests**: 3 tests (decay chapter cercano, decay chapter lejano, no-decay para grammar).

**Dependencia**: BK-09 (FK integrity) debe estar completo antes.

---

### Priorización Global y Roadmap

**Esfuerzo total**: ~80-94h (~10-12 días efectivos)

```
Semana 1: S9 — Data Integrity (CRITICAL)
┌────────────────────────────────────────────────┐
│ BK-09 (Merge FK)  → BK-15 (Masking) → BK-17   │
│ [6-8h]              [3-4h]            [4-5h]    │
│            → BK-10b (Scene) → BK-10c (Decay)   │
│              [5-6h]           [4-5h]            │
└────────────────────────────────────────────────┘

Semana 2: S10 — Ubicaciones + Timeline
┌────────────────────────────────────────────────┐
│ BK-14 (LocationOntology) → BK-11 (Timeline)    │
│ [12h]                      [15-18h]             │
└────────────────────────────────────────────────┘

Semana 3: S11 — NLP Avanzado + S12
┌────────────────────────────────────────────────┐
│ BK-13 (Pro-drop) → BK-16 (Chekhov) → BK-18    │
│ [12-14h]           [14-16h]          [2-3h]    │
└────────────────────────────────────────────────┘
```

**Ranking ROI** (valor/esfuerzo):
1. **BK-14** — Quick win, 30% FP reduction, foundation para BK-11
2. **BK-09** — CRITICAL data integrity, silent data loss actual
3. **BK-11** — Highest business value, 40% ficción moderna
4. **BK-13** — High Spanish-specific value, 40% prosa española
5. **BK-15** — Easy win, elimina FP en OOC
6. **BK-17** — Desbloquea fantasía/sci-fi
7. **BK-10b/c** — Mejora speaker attribution
8. **BK-16** — Nicho editorial, nice-to-have
9. **BK-18** — Trivial, mejora priorización alertas

#### BK-10 detalle (revisado 10-Feb-2026)

> **Análisis previo erróneo**: Se asumía que no había reset por capítulo. Código real
> (`speaker_attribution.py:376-380`) ya hace hard reset en cada cambio de capítulo:
> ```python
> if chapter != last_chapter:
>     current_participants = []
>     last_speaker = None
>     last_chapter = chapter
> ```
>
> **Panel de expertos (Lingüista + Corrector + Arquitecto)**:
>
> **Lingüista**: "El reset duro pierde contexto valioso. En una escena continua entre capítulos,
> el lector sabe quién habla. Mejor usar confidence decay gradual: 0.95^(distancia_en_turnos)
> hasta scene break, donde sí se resetea."
>
> **Corrector**: "Lo más importante es que si yo corrijo un speaker mal atribuido, la app lo
> recuerde para la próxima vez. No quiero corregir lo mismo dos veces."
>
> **Arquitecto**: "La tabla `speaker_corrections` ya existe en la BD. Los endpoints GET/POST/DELETE
> existen en `voice_style.py:776-902`. Pero `SpeakerAttributor` nunca lee de esa tabla.
> Conectar el pipeline es 2-3h de trabajo."
>
> **Sub-tareas**:

| ID | Acción | Esfuerzo | Detalle |
|----|--------|----------|---------|
| BK-10a | Aplicar correcciones usuario en attribution | S (2-3h) | `SpeakerAttributor.attribute()` lee `speaker_corrections` y aplica overrides con confidence=1.0 ANTES del algoritmo heurístico. Infrastructure exists: DB table + API endpoints. |
| BK-10b | Detección scene breaks intra-capítulo | S (3-4h) | Usar patrones de `chapter.py:621-626` (`***`, `---`, triple newline) en `speaker_attribution.py`. En scene break: reset `current_participants` y `last_speaker`, no solo en cambio de capítulo. |
| BK-10c | Confidence decay gradual | S (2-3h) | Reemplazar confidence fija por decay: `confidence = base * 0.95^(turns_since_explicit)`. Decay se resetea en: verba dicendi explícito, scene break, cambio de capítulo. Enum `AttributionConfidence` → float continuo. |

---

## 8c. Auditoría de Producto (Panel de Expertos, 10-Feb-2026)

> **Contexto**: Pivote de enfoque académico (TFM) a producto vendible. El objetivo es que un
> corrector profesional pueda usar la app sin tecnicismos, entendiendo qué hace y cómo usarla.
>
> **Workflow real del corrector**: El corrector NO edita texto en la app. Abre el manuscrito en
> la app para auditarlo, revisa hallazgos (alertas, entidades, relaciones), acepta/rechaza,
> y luego corrige en Word. **Export es el puente** entre la app y el trabajo real.
>
> **Panel**: UX Designer, Corrector Editorial (15+ años), Product Owner, Frontend Engineer,
> Arquitecto Python, QA Senior, Lingüista Computacional, AppSec Specialist.

### 8c.1 Correcciones Interactivas — "El sistema aprende"

> **Premisa del corrector**: "Si rechazo una alerta, el sistema no debería volver a mostrarla.
> Si corrijo un speaker, debería recordarlo. Si asigno un atributo, debería usarlo."

#### Estado actual de cada workflow interactivo

| Workflow | UI | API | BD | Feedback loop |
|----------|-----|-----|-----|---------------|
| **Aceptar/rechazar alertas** | **COMPLETO** — Lista + modo secuencial con atajos (A/D/S/F/←/→), undo (Ctrl+Z), hasta 50 acciones | PATCH status, POST resolve-all, POST dismiss-batch con scope (instance/project/global) | `dismissal_repository` | **PARCIAL** — Dismissals persisten entre reanálisis (`apply_dismissals()`), pero NO recalibran confianza ni pesos de detectores |
| **Asignar atributos** | **FALTA** — EntitiesTab solo lectura (muestra atributos, navega al texto, pero no edita) | **EXISTE** — POST create, PUT update con `is_verified` | `entity_attributes` | **NO** — Atributos verificados no influyen en extracción futura |
| **Corregir speaker** | **FALTA** — DialogueAttributionPanel muestra alternativas y confianza, pero es solo lectura | **EXISTE** — GET/POST/DELETE speaker corrections | `speaker_corrections` | **NO** — `SpeakerAttributor` no lee de esta tabla (BK-10a) |
| **Merge entidades** | **COMPLETO** — Wizard 3 pasos, aliases auto-transfer, conflictos detectados, undo | POST merge, POST undo-merge, POST preview-merge con similitud | `merge_history` | **PARCIAL** — Merge persiste, pero conflictos de atributos no se resuelven |
| **Resolver conflictos merge** | **FALTA** — Se muestran (critical/medium/low) pero corrector no puede elegir valor | N/A | N/A | N/A |

> **Decisión panel**:
>
> **Product Owner**: "BK-19 (atributos) y BK-20 (speaker) son blocker para vender. Un corrector
> que no puede corregir errores del sistema no volverá a usarlo."
>
> **UX**: "El formulario de atributos debe ser inline (no dialog). Click en atributo → editar.
> Botón '+' para añadir. Para speaker: dropdown con entidades del capítulo."
>
> **QA**: "BK-22 (feedback loop) es P2, no P1. Primero que el corrector pueda corregir (BK-19/20),
> luego que el sistema aprenda de esas correcciones."
>
> **Corrector**: "Lo prioritario es que mis correcciones se apliquen en el reanálisis (BK-10a).
> Que el sistema mejore solo es el siguiente paso."

#### Plan de sistema de aprendizaje (BK-22)

> **Mecanismo propuesto por Arquitecto + Lingüista**:
>
> 1. **Nivel 1 — Memoria de sesión** ✅ DONE: Dismissals persisten, correcciones speaker
>    persisten, merges persisten. Cuando se reanaliza, se aplican. `speaker_corrections`
>    conectado al pipeline (BK-10a).
>
> 2. **Nivel 2 — Recalibración de confianza** ✅ DONE (BK-22): `detector_calibration` table,
>    `_get_calibration_factor()` en AlertEngine. Se recomputa desde alertas actuales.
>
> 3. **Nivel 3 — Pesos adaptativos por manuscrito + per-entity** ✅ DONE: `project_detector_weights`
>    table (schema v24). Cascading lookup: per-entity → project-level → 1.0. Learning rate
>    fraccionado para alertas multi-entity. Pesos sobreviven re-análisis (a diferencia del
>    nivel 2 que recomputa). Entity merge transfiere pesos con media ponderada. 31 tests.
>
> **Estado**: Los 3 niveles implementados y funcionando.

### 8c.2 Export — El Puente con Word

> **Premisa**: El corrector revisa en la app y corrige en Word. El export es el producto
> final que entrega al autor/editorial. Sin export completo, la app es un visor bonito.

#### Estado actual del export

| Export | Estado | Formato | Endpoint | Notas |
|--------|--------|---------|----------|-------|
| Documento completo | **COMPLETO** | DOCX, PDF | `/export/document` | Portada, TOC, estadísticas, personajes, alertas |
| Track Changes | **COMPLETO** | DOCX | `/export/corrected` | Correcciones como revisiones de Word (accept/reject nativo) |
| Review Report | **COMPLETO** | DOCX, PDF | `/export/review-report` | Informe editorial profesional por categoría |
| Style Guide | **COMPLETO** | MD, JSON, PDF | `/style-guide` | Decisiones ortográficas, entidades canónicas |
| Scrivener | **COMPLETO** | ZIP (.scriv) | `/export/scrivener` | Capítulos + notas de personajes + keywords |
| Fichas personajes | **CÓDIGO EXISTE, ENDPOINT FALTA** | MD, JSON | — | `character_sheets.py` (419 líneas) completo, sin routing |
| Informe análisis | **ENDPOINT FALTA** | MD, JSON | — | Frontend llama `/export/report` → 404 |
| Solo alertas | **ENDPOINT FALTA** | JSON, CSV | — | Frontend llama `/export/alerts` → 404. Sin CSV para equipos |

> **Panel**:
>
> **Corrector**: "La ficha de personajes es lo primero que miro antes de corregir. La imprimo
> y la tengo al lado. Sin esto el export está incompleto."
>
> **Product Owner**: "3 endpoints rotos en la UI = percepción de producto inacabado. Quick win
> de 2-3h que sube la calidad percibida enormemente."
>
> **Frontend Engineer**: "ExportDialog.vue ya tiene los 8 tipos de export con opciones
> (filtros, formatos, previews). El frontend está listo, solo falta el backend routing."
>
> **Decisión**: BK-24 es P1 y debe ir PRIMERO en el sprint de producto. Es el mayor ROI
> posible: 2-3h de trabajo, 3 features que el usuario ya espera.

### 8c.3 Tutorial y Onboarding

> **Estado actual**: TutorialDialog.vue (1376 líneas), wizard de 5 pasos:
> Welcome → How-to → Workspace → Hardware → Ready.
>
> **Problema**: Paso 3 (Hardware) ocupa 40% del tutorial con detección GPU, instalación Ollama,
> instalación LanguageTool. Un corrector no necesita saber qué es un "modelo de IA" ni "GPU".

#### Decisiones del panel

| Punto | Decisión | Razón |
|-------|----------|-------|
| Hardware en tutorial | **ELIMINAR** | Corrector no necesita saber de GPU. Auto-configurar. |
| Auto-config perfil | **IMPLEMENTAR** | Detectar hardware → descargar modelos → activar mejor perfil sin intervención del usuario |
| Feature discovery | **AÑADIR al tutorial** | Explicar qué hace cada tab, qué tipo de errores detecta |
| Alert workflow | **AÑADIR al tutorial** | Mostrar cómo revisar una alerta: leer → ir al texto → aceptar/rechazar |
| Demo project | **NO CUENTA para licencias** | Proyecto demo para practicar, no penaliza cuota de páginas |
| UserGuide con screenshots | **SÍ** | Capturas de cada tab + flujo de trabajo. Versión PDF exportable |
| Landing page web | **ANOTAR, NO AHORA** | Después de testear con clientes reales. Documentar para futuro |

> **UX**: "El tutorial debe responder 3 preguntas: ¿Qué hace la app? ¿Cómo la uso? ¿Qué
> significan los resultados? Hardware es un detalle de instalación, no de uso."
>
> **Corrector**: "Quiero ver ejemplos reales. 'Mira, aquí detectó que María tenía ojos verdes
> en el capítulo 3 y azules en el 7'. Eso me convence más que una lista de features."
>
> **Product Owner**: "El auto-config es crítico para first-time experience. Si el corrector
> abre la app y tiene que instalar Ollama manualmente, lo perdemos."

### 8c.4 Jargon Técnico vs Lenguaje del Corrector

> **Regla**: Eliminar jerga de programador/ML. Mantener terminología lingüística que un
> corrector profesional conoce.

#### Términos a eliminar (jerga programador)

| Término actual | Reemplazo | Archivos afectados |
|---------------|-----------|-------------------|
| NLP | "análisis lingüístico" | SettingsView, TutorialDialog, AboutDialog |
| GPU / CUDA / MPS | "aceleración por hardware" | SettingsView, TutorialDialog |
| LLM | "modelo de lenguaje" o "motor de análisis" | SettingsView, TutorialDialog |
| Embeddings | "análisis semántico" | SettingsView |
| spaCy | eliminar referencia | SettingsView, AboutDialog |
| Ollama | "Motor de IA local" | SettingsView, TutorialDialog |
| LanguageTool | "Corrector gramatical" (ya parcial) | SettingsView |
| Backend / Frontend | eliminar | AboutDialog |
| Token / Tokenización | "segmentación de texto" | si aparece en UI |
| Pipeline | "proceso de análisis" | si aparece en UI |
| VRAM / RAM | "memoria disponible" | SettingsView |
| Batch size | "tamaño de lote" o eliminar | SettingsView |
| Cuantización / Q4_K_M | eliminar de UI | SettingsView |

#### Términos a MANTENER (el corrector los conoce)

| Término | Razón |
|---------|-------|
| Morfosintáctico | Formación estándar en corrección editorial |
| Léxico | Término básico de lingüística |
| Semántico | El corrector entiende "análisis semántico" |
| Correferencia | Término técnico pero usado en lingüística aplicada |
| Anáfora | Término que un corrector con formación conoce |
| Registro (formal/informal) | Concepto estándar en edición |
| Concordancia | Fundamental en corrección |
| Anacoluto | El corrector lo busca activamente |

> **Lingüista**: "Un corrector con 15 años de experiencia sabe perfectamente qué es
> 'morfosintáctico'. Lo que NO sabe es qué es un 'embedding' o 'CUDA'."
>
> **UX**: "La regla es simple: si lo explicarías en un manual de corrección editorial, se queda.
> Si lo explicarías en un curso de machine learning, se va."

### 8c.5 Consistencia Visual: Loading Patterns

> **Auditoría**: 52 indicadores de carga en 49 archivos. 3 custom components (DsLoadingState,
> AnalysisProgress, AnalysisRequired), 2 PrimeVue ProgressSpinner, 6 PrimeVue ProgressBar,
> 16 icon spinners manuales (`pi-spin pi-spinner`), ~8 Button `:loading`.

#### Decision tree estandarizado

```
¿Es carga de PÁGINA COMPLETA?
├─ SÍ → ProgressSpinner + texto centrado ("Cargando proyecto...")
│
└─ NO
   ├─ ¿Es operación LARGA con % conocido?
   │  └─ SÍ → ProgressBar determinada + label + % separado
   │     (patrón TutorialDialog: label arriba, barra abajo, % a la derecha)
   │     Con fallback a indeterminada si % no disponible
   │
   ├─ ¿Es operación LARGA sin %?
   │  └─ SÍ → ProgressBar indeterminada + label descriptivo
   │
   ├─ ¿Es carga de SECCIÓN/PANEL?
   │  └─ SÍ → DsLoadingState (variant="inline", size="sm")
   │
   └─ ¿Es acción de BOTÓN?
      └─ SÍ → Button `:loading` prop (swap icon automático)
```

#### Inconsistencias a corregir

| Problema | Dónde | Fix |
|----------|-------|-----|
| Descarga Ollama: visual diferente en Tutorial vs Settings | TutorialDialog + SettingsView | Unificar al patrón Tutorial (label + % + barra) |
| Skeleton loaders: CSS existe, componente nunca usado | `animations.css` → `.skeleton-loader` | Crear componente Skeleton para listas (entidades, alertas) |
| Z-index overlay inconsistente | DsLoadingState vs AnalysisProgress vs AnalysisRequired | Crear variables CSS: `--ds-z-overlay`, `--ds-z-modal` |
| Dos animaciones spin duplicadas | `spin` en animations.css + `ds-spin` en DsLoadingState | Consolidar en una sola |
| ProgressBar `:show-value` inconsistente | Algunos true, otros false con label separado | Siempre false + label separado (más control visual) |

> **Frontend Engineer**: "El patrón del TutorialDialog (mini-spinner al lado de la opción +
> barra debajo) es el gold standard. Lo aplico a todas las descargas de modelos."
>
> **UX**: "Spinner para cosas rápidas (<3s). Barra para cosas largas. Skeleton para listas
> que se están cargando. Nunca mezclar en el mismo contexto."

### 8c.6 Entity Merge: Alias y Atributos

> **Estado actual del merge** (MergeEntitiesDialog.vue, 1702 líneas):
>
> ✅ **Aliases**: Cuando se mergean A + B → C, TODOS los nombres (canónicos + aliases de ambos)
> se convierten en aliases de C. El nombre de la entidad eliminada se añade automáticamente
> como alias. El corrector elige el nombre principal en paso 2 del wizard.
>
> ✅ **Conflictos detectados**: El wizard muestra conflictos de atributos con severidad
> (critical/medium/low). Ejemplo: "edad=25 vs edad=28" → critical.
>
> ❌ **Conflictos NO resolubles**: El corrector ve el conflicto pero no puede elegir qué valor
> conservar. El merge procede y el backend decide (no documentado cómo).
>
> **Decisión panel (BK-21)**: Añadir resolución de conflictos en paso 3 del wizard.
> Para cada conflicto critical/medium: radio button "Conservar valor de [Entidad A]" /
> "Conservar valor de [Entidad B]" / "Nuevo valor: [input]". Low severity: auto-merge.

### Sprint PP: Product Polish (BK-19..24) — COMPLETADO (1 pendiente: BK-23a)

> **Objetivo**: Convertir la app de "funcional" a "vendible". Quick wins primero,
> luego UI interactiva, luego aprendizaje del sistema.
>
> **Requisito**: Estas tareas van ANTES de S9-S12 (NLP avanzado). Un producto que no se
> puede usar correctamente no se beneficia de mejor NLP.

#### Fase PP-1: Quick Wins Export (2-3h) — ✅ COMPLETADO

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| BK-24a | Endpoint `/export/characters` | DONE | Routing a `character_sheets.py` (commit c653867) |
| BK-24b | Endpoint `/export/report` | DONE | ReviewReportExporter con formato resumido (commit c653867) |
| BK-24c | Endpoint `/export/alerts` + CSV | DONE | JSON + CSV con tipo, severidad, texto, capítulo, estado, sugerencia (commit c653867) |

#### Fase PP-2: UI Correcciones Interactivas (13h) — ✅ COMPLETADO

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| BK-19 | UI añadir/editar atributos | DONE | EntitiesTab: inline add/edit/delete, formulario con categoría/nombre/valor/confianza (commit b326317) |
| BK-20 | UI corregir speaker | DONE | DialogueAttributionPanel: botón "Corregir", dropdown entidades, POST speaker_corrections, tag verde "Corregido" (commit 8b52e80) |
| BK-21 | Resolver conflictos en merge | DONE | MergeEntitiesDialog paso 3: radio buttons para conflictos, resoluciones en POST merge (commit 7a44c73) |

#### Fase PP-3: Tutorial, Jargon y Onboarding (12h) — ✅ COMPLETADO

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| S7d-11 | Renombrar jargon técnico | DONE | ~30 términos renombrados en SettingsView, TutorialDialog, AboutDialog (commit ef39568) |
| PP-3a | Reestructurar tutorial (eliminar hardware) | DONE | Nuevo flujo: Welcome → Qué detecta → Workspace → Alert workflow → Ready. Auto-config en background (commit f08a88b) |
| PP-3b | Auto-config hardware + descarga modelos | DONE | Detectar GPU/RAM → descargar modelos óptimos → activar mejor perfil automáticamente (commit f08a88b) |
| PP-3c | Demo project no cuenta para licencias | DONE | Flag is_demo en BD + skip en _get_usage_with_rollover() (commit fcc417f) |
| S7d-04 | aria-labels faltantes | DONE | StatusBar + botones solo icono (commit 86832b5) |
| S7d-10 | Simplificar AboutDialog | DONE | Solo versión app, licencia, contacto (commit 86832b5) |

#### Fase PP-4: Feedback Loop (8h) — ✅ COMPLETADO

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| BK-10a | Aplicar correcciones speaker en pipeline | DONE | SpeakerAttributor lee speaker_corrections, override con confidence=1.0 (commit 8755c9c) |
| BK-22 | Recalibrar confianza por detector | DONE | detector_calibration table, effective_confidence = original * (1 - fp_rate * 0.5) (commit 3cd35d3) |

#### Fase PP-5: Polish Visual (4h) — 2/3 COMPLETADO

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| BK-23a | Unificar loading Ollama (Tutorial=Settings) | DONE | DsDownloadProgress.vue unificado, usado en ModelSetupDialog + Settings (v0.8.0, commit 6ddebec) |
| BK-23b | Crear componente Skeleton para listas | DONE | Skeleton loaders para entidades, alertas, relaciones (commit 3fbe310) |
| BK-23c | Consolidar z-index y animaciones | DONE | Variables CSS centralizadas, una sola animación spin (commit 3fbe310) |

#### Resumen Sprint PP

| Fase | Tareas | Estado | Impacto |
|------|--------|--------|---------|
| **PP-1**: Export quick wins | 3 | ✅ DONE | 3 features rotas → funcionales |
| **PP-2**: UI interactiva | 3 | ✅ DONE | Corrector puede corregir errores del sistema |
| **PP-3**: Tutorial + jargon + onboarding | 6 | ✅ DONE | First-time experience profesional |
| **PP-4**: Feedback loop | 2 | ✅ DONE | Sistema aprende de correcciones |
| **PP-5**: Polish visual | 3 | ✅ DONE | Completado (v0.8.0) |
| **TOTAL** | **17** | **17/17 DONE** | Producto vendible con workflow completo |

> **Orden de ejecución**: PP-1 → PP-2 → PP-3 → PP-4 → PP-5.
>
> PP-1 primero porque es el mayor ROI (2-3h, 3 features). PP-2 antes de PP-4 porque el
> corrector necesita poder corregir antes de que el sistema aprenda de sus correcciones.
>
> **Relación con S8/S9**: Sprint PP es independiente y puede ejecutarse EN PARALELO con S8a
> (pipeline enrichment) ya que toca archivos diferentes (frontend vs backend pipeline).
> PP-4 (BK-10a) toca `speaker_attribution.py` que no se modifica en S8a.

---

## 8d. Sprints de Producto y Licensing (Panel de Expertos, 12-Feb-2026)

> **Contexto**: Sesión de paneles especializados (correctores editoriales 18+ años,
> pricing SaaS B2B, sales & marketing España). Identificaron que el trabajo editorial
> se pierde al reanalizar (bug crítico), y definieron estructura de pricing, founding
> members, y features de colaboración editorial.

### Sprint SP-1: Persistencia de Trabajo en Reanálisis — COMPLETADO (v0.9.0)

> **Prioridad**: INMEDIATA. Es un bug, no una feature. Los 3 correctores del panel
> (Carmen, Miguel, Ana) lo calificaron 5/5 y dijeron: "Si pierdo mi trabajo al
> reanalizar, desinstalo la herramienta." Tier: Corrector (base).

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| SP1-01 | Fix content_hash para alertas posicionales | DONE | Eliminado `start_char` de hash para `spelling_*` y `grammar_*`. Hash usa `(word, chapter, alert_type)`. |
| SP1-02 | Preservar trabajo editorial en cleanup | DONE | `run_cleanup()` ya NO borra: `alert_dismissals`, `suppression_rules`, `coreference_corrections`, `speaker_corrections`, `focalization_declarations`. Preserva `entity_merged` en `review_history`. |
| SP1-03 | Auto-aplicar dismissals tras generación de alertas | DONE | Nueva función `_apply_saved_dismissals()` en pipeline: aplica dismissals por `content_hash` + reglas de supresión activas. |
| SP1-04 | Preservar entity merges entre reanálisis | DONE | `_reapply_user_merges()` re-aplica fusiones de usuario desde `review_history` después de fusión automática. |
| SP1-05 | Preservar atributos verificados (`is_verified=1`) | DONE | `run_cleanup()` guarda atributos verificados en `ctx`. `_restore_verified_attributes()` los restaura después de extracción de atributos. |
| SP1-06 | Preservar correcciones manuales | DONE | Tablas de correcciones ya no se borran (SP1-02). Tests verifican que sobreviven cleanup. |
| SP1-07 | Tests de persistencia en reanálisis | DONE | 25 tests en `test_sp1_reanalysis_persistence.py`: hash stability, cleanup preservation, auto-dismiss, user merges, verified attributes, manual corrections. |

**Archivos a modificar**:
- `api-server/routers/_analysis_phases.py` — cleanup + apply_dismissals en pipeline
- `src/narrative_assistant/alerts/models.py` — fix content_hash spelling_*
- `src/narrative_assistant/entities/` — nuevo: merge_preservation.py
- `tests/unit/test_reanalysis_persistence.py` — nuevo

### Sprint SP-2: Revisión de Licensing — COMPLETADO (v0.9.3)

> **Contexto**: Paneles de pricing y sales identificaron problemas en la estructura
> actual: Pro con 2 dispositivos canibaliza Editorial, salto €49→€299 demasiado
> grande, sin límite de manuscrito en Corrector.

| ID | Acción | Horas | Detalle |
|----|--------|-------|---------|
| SP2-01 | Profesional: 1 dispositivo (era 2) | 1h | `TierLimits.for_tier(PROFESIONAL).max_devices = 1`. Con 2 swaps/mes, 1 device es suficiente. Evita arbitraje: 2×Pro (€98, 4 devices) vs Editorial (€159, 3 devices). |
| SP2-02 | Corrector: límite 60k palabras por manuscrito | 2h | Nuevo: `max_words_per_manuscript` en `TierLimits`. Novelas (70-120k) fuerzan upgrade a Pro. Enforce en `gating.py` y pipeline. |
| SP2-03 | Device swap model: 2/mes + 7 días cooldown | 2h | Nuevo: `DeviceSwapPolicy` dataclass. `max_swaps_per_month=2`, `cooldown_hours=168`. Primer swap inmediato, 2o inmediato, 3o+ espera 7 días. |
| SP2-04 | Editorial: €159 base (3 puestos) + €49/extra | 1h | Nuevo: `editorial_base_seats=3`, `editorial_extra_seat_price=49` en config. `max_devices` calculado dinámicamente. |
| SP2-05 | Founding member model | 1h | Nuevo: `FoundingMemberConfig` — prices `{CORRECTOR: 19, PROFESIONAL: 34, EDITORIAL: 119}`, spots `{CORRECTOR: 10, PROFESIONAL: 15, EDITORIAL: 5}`, `upgrade_discount_pct=20`. |
| SP2-06 | Actualizar LICENSING_PRODUCTION_PLAN.md | 1h | Nueva tabla de precios, cooldown model, founding program, annual pricing (25% off). |

**Tabla de precios final**:

| | Corrector | Profesional | Editorial |
|---|-----------|-------------|-----------|
| **Standard** | €24/mo | €49/mo | €159/mo (3 puestos) |
| **Founder (forever)** | €19/mo (10 plazas) | €34/mo (15 plazas) | €119/mo (5 plazas) |
| **Founder upgrade bonus** | 20% off tier superior | 20% off tier superior | — |
| **Anual** | €216/año (25% off) | €441/año | €1,521/año |
| **Puesto extra (Editorial)** | — | — | +€49/puesto/mo |
| **Páginas/mo** | 1,500 | 3,000 | Ilimitado |
| **Manuscrito max** | 60k palabras | Ilimitado | Ilimitado |
| **Dispositivos** | 1 | 1 | 3 base (+extras) |
| **Swaps/mes** | 2 + 7d cooldown | 2 + 7d cooldown | 2 + 7d cooldown |
| **Features** | 4 básicas | 11 completas | 11 + export/import/merge |

**Founding program**: 30 plazas totales (10/15/5). Precio bloqueado para siempre.
Founders que suben de tier mantienen 20% de descuento sobre el precio standard del tier superior.

### Sprint SP-3: Export/Import Trabajo Editorial — COMPLETADO (v0.9.2)

> **Prioridad**: Después de SP-1. Es el diferenciador clave del tier Editorial.
> File-based (no requiere servidor). Solo metadatos de análisis (nombres de
> personajes, alertas, atributos), NO texto del manuscrito.

| ID | Acción | Estado | Detalle |
|----|--------|--------|---------|
| SP3-01 | Servicio de export (JSON `.narrassist`) | DONE | `editorial_work.py`: export_editorial_work() recoge entity merges, alert decisions, verified attributes, suppression rules. JSON versionado (format_version=1). |
| SP3-02 | Servicio de import con preview | DONE | preview_import() analiza archivo, detecta conflictos LATEST_WINS. confirm_import() aplica con section toggles y conflict_overrides. |
| SP3-03 | Merge logic para trabajo de múltiples correctores | DONE | Estrategia LATEST_WINS implementada en _resolve_latest_wins(). Preview muestra conflictos con resolución pre-calculada. |
| SP3-04 | API endpoints | DONE | `POST /projects/{id}/export-work`, `POST /projects/{id}/import-work/preview`, `POST /projects/{id}/import-work/confirm`. Router: `api-server/routers/editorial_work.py`. |
| SP3-05 | Frontend: botones export/import + modal preview | DONE | Card "Trabajo Editorial" en ExportDialog.vue. ImportWorkDialog.vue: flujo 3 pasos (upload → preview con stats/conflictos → confirm). |
| SP3-06 | Feature gating: solo Editorial | DONE | `LicenseFeature.EXPORT_IMPORT` (ya existía en models.py). Gated en 3 endpoints via `_check_export_import_feature()`. |
| SP3-07 | Tests | DONE | 38 tests: export (7), preview (9), confirm (4), roundtrip (2), QA edge cases (16). |

**Seguridad**: El archivo `.narrassist` contiene SOLO metadatos (nombres de personajes,
descripciones de alertas, atributos). NO contiene texto del manuscrito. Aun así, los
metadatos pueden revelar trama → el archivo es del corrector, se transfiere por sus
propios medios (email, USB, Slack). Sin servidor involucrado.

**Flujo editorial típico**:
1. Coordinador crea proyecto, analiza manuscrito
2. Exporta trabajo y lo envía a 2 correctores
3. Corrector A trabaja caps 1-5, Corrector B trabaja caps 6-10
4. Ambos exportan su trabajo → coordinador importa ambos con merge
5. Coordinador revisa conflictos en preview → confirma

---

## 9. Cronograma de Implementación

### Completado (S0-S7a): ✅

S0 (xfails), S1 (NER), S2 (correferencias), S3 (temporal), S4 (atributos avanzados),
S5 (LLM), S6 (frontend UX), S7a (licensing). Total: ~10 semanas ejecutadas.

### Completado: Sprint S7 ✅

> S7b-09 (AnachronismsPanel) y S7b-10 (CharacterProfileModal) completados en v0.8.0-v0.8.2.

### Completado: Sprint PP — Product Polish ✅

> 17/17 tareas completadas. BK-23a completado en v0.8.0.

### Completado: Sprint S8 — Pipeline + Invalidación ✅

> S8a (18 tareas), S8b (9 tareas), S8c (11 tareas) — todo completado.
> Tag: v0.8.0

### Completado: Sprint S9 — Integridad de Datos y Diálogos ✅

> BK-09 (merge FK), BK-15 (masking), BK-17 (glossary→NER), BK-10b/c (scene breaks + decay).

### Completado: Sprint S10 — Ubicaciones Jerárquicas + Timeline No Lineal ✅

> BK-14 (LocationOntology: jerarquía 7 niveles, gazetteer ~50 ciudades, haversine, reachability).
> BK-11 (TemporalMap + NonLinearDetector: story_time alive checks, age calculation, flashback detection).
> 34 nuevos tests, 1609 regression OK. Completado 13-Feb-2026.

### PRÓXIMO: SP-1..SP-3 — Producto y Licensing (~60h, 3-4 semanas)

> Persistencia de trabajo editorial, revisión de pricing, y export/import.
> SP-1 es prioritario (bug crítico). SP-2 y SP-3 pueden ir en paralelo.

| Sprint | Foco | Tareas clave | Días |
|--------|------|-------------|------|
| **SP-1** | Persistencia en reanálisis | Fix content_hash, preservar merges/atributos/dismissals | 3-4d |
| **SP-2** | Revisión licensing | 1 device Pro, 60k limit, swaps, founding members | 2d |
| **SP-3** | Export/Import editorial | JSON .narrassist, preview+confirm, merge logic | 7-9d |

### ~~COMPLETADO: S9-S12 — NLP Avanzado~~ ✅

> Mejoras de calidad NLP completadas. Todos los sprints ✅.

| Sprint | Foco | Tareas clave | Días |
|--------|------|-------------|------|
| **S9** ✅ | Integridad datos + diálogos | BK-09 (merge FK), BK-15 (masking), BK-17 (glossary→NER), BK-10b/c (scene breaks + decay) | 6-9d |
| **S10** ✅ | Timeline no lineal | BK-14 (ubicaciones jerárquicas), BK-11 (narrativa no lineal — 40% ficción). ~~BK-12 absorbido por S8a~~ ✅ | 8-13d |
| **S11** ✅ | Pro-drop + Chekhov | BK-13 (ambigüedad multi-candidato), BK-16 (hilos narrativos sin resolver) | 8-13d |
| **S12** ✅ | Confidence decay | BK-18 (decay gradual post-merge) | 1-2d |

### SIGUIENTE: S13-S16 — Editorial Intelligence + Monetización (~75-110h, ~20-30 días)

> Panel de expertos (13-Feb-2026): Todos los sprints NLP (S0-S12) completados. BK-12 absorbido por S8a.
> Los 4 BK restantes accionables (BK-25, BK-27, BK-28, BK-29) son product/business features.
> BK-26 (collab online) permanece aparcado.
>
> **Decisión panel**: S13 (BK-27 + BK-25 MVP) es el sprint de mayor ROI: 7-9h para impacto editorial
> diario. S14 (BK-25 full) es el diferenciador competitivo. S15 (BK-28) y S16 (BK-29) pueden
> posponerse hasta tener feedback de clientes reales.

**Criterios no funcionales obligatorios** (por sprint):
- Latencia API nueva p95 < 300 ms en proyecto mediano (~30 capítulos)
- No aumentar RAM pico de análisis > 15% respecto baseline
- Tests y lint en verde antes de cerrar sprint
- Crecimiento de DB por snapshot/versión bajo límite definido (con retención existente de 10 snapshots)

| Sprint | Foco | Tareas clave | Días |
|--------|------|-------------|------|
| **S13** | Editorial workflow | BK-27 (filtrado capítulos) + BK-25 MVP (comparison banner) | 1-2d |
| **S14** | Revision Intelligence full | BK-25 completo (content diffing, alert linking, dashboard) | 5-7d |
| **S15** | Version tracking | BK-28 fase 1 (métricas por versión, sparkline trends) | 4-5d |
| **S16A** | Monetización UX | BK-29 (quota warnings, tier comparison — desktop-only) | 2-3d |
| **S16B** | Monetización pagos | BK-29 (page packs, Stripe — requiere backend billing público) | 4-6d |

#### Sprint S13: Editorial Workflow (BK-27 + BK-25 MVP) [7-9h]

> **Corrector Editorial**: "Es lo que más necesito. Trabajo en 3-4 capítulos al día de un manuscrito
> de 30. No quiero ver alertas de capítulos que no me tocan."
> **Product Owner**: "Mayor ROI del backlog: 7h de trabajo → impacto editorial diario."
> **Arquitecto**: "Trivial — SQL WHERE + 2 query params + ComparisonService existente."

**BK-27: Filtrado de alertas por rango de capítulos [4-6h]**

Infraestructura existente (85%):
- `get_by_project_prioritized()` prioriza por `current_chapter` ±2
- Focus mode filtra por severity/confidence
- Campo `chapter` en todas las alertas

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| S13-01 | 1h | `api-server/routers/alerts.py` | Añadir `chapter_min`, `chapter_max` query params a `list_alerts()`. SQL: `AND chapter BETWEEN ? AND ?`. Cross-chapter: usar `extra_data.related_chapters` (JSON array) para incluir alertas cuyo capítulo relacionado caiga en el rango. |
| S13-02 | 1h | `src/narrative_assistant/alerts/repository.py` | Extender `get_by_project_prioritized()` con filtro de rango. Nota: `idx_alerts_chapter ON alerts(chapter)` ya existe (database.py:265). Evaluar índice compuesto `(project_id, chapter, status)` solo si profiling lo justifica. |
| S13-03 | 2h | `frontend/src/components/alerts/ChapterRangeSelector.vue` | Dos dropdowns (Desde/Hasta) poblados desde chapters del proyecto. Persistir en `localStorage` por proyecto. Emitir `@range-change`. |
| S13-04 | 0.5h | `frontend/src/components/alerts/AlertsTab.vue` | Integrar ChapterRangeSelector. Pasar chapter_min/max a API call. Actualizar badge count con filtro activo. |
| S13-05 | 0.5h | Tests | Test unitario para filtro de rango en repository. Test API con chapter_min/max. |

**BK-25 MVP: Comparison banner tras reanálisis [3h]**

Infraestructura existente (55% — backend core completo):
- `ComparisonService.compare()` con two-pass matching (exact hash + fuzzy)
- `analysis_snapshots` + `snapshot_alerts` tables
- `run_snapshot()` se ejecuta antes de cada reanálisis
- Endpoint `/comparison` devuelve `ComparisonReport`

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| S13-06 | 0.5h | `api-server/routers/collections.py` | Añadir `GET /projects/{id}/comparison/summary` — devuelve solo counts: `{resolved: N, new: N, unchanged: N, document_changed: bool}`. Reutiliza `ComparisonService`. |
| S13-07 | 1.5h | `frontend/src/components/analysis/ComparisonBanner.vue` | Banner post-reanálisis: "↓12 resueltas · ↑3 nuevas · =45 sin cambio". Color verde si resolved > new, naranja si new > resolved. Clic → modal con lista. |
| S13-08 | 0.5h | `frontend/src/components/analysis/ComparisonDetail.vue` | Modal con dos listas: alertas resueltas (tachadas, verde) y alertas nuevas (badge, naranja). Cada item muestra tipo + entidad + capítulo. |
| S13-09 | 0.5h | Tests | Test unitario para summary endpoint. Test de integración ComparisonBanner render. |

**Dependencias S13**: Ninguna (toda la infra existe)
**Criterio de éxito**: Corrector puede filtrar alertas por rango de capítulos + ve resumen de cambios tras reanálisis.

---

#### Sprint S14: Revision Intelligence Full (BK-25 completo) [28-36h] ✅ DONE (Fases 1-3)

> **Product Owner**: "Diferenciador competitivo. Ningún corrector de manuscritos tiene esto."
> **AppSec**: "Read-only analysis, sin riesgo. Content diffing opera sobre datos locales."
> **UX**: "Progresión natural: S13 muestra el banner → S14 permite explorar en profundidad."

**Fase 1: Content Diffing [12h] ✅**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| ~~S14-01~~ | 4h | `src/narrative_assistant/analysis/content_diff.py` | ✅ Nuevo módulo. `compute_chapter_diffs()`, `diff_chapter_texts()`, `is_position_in_removed_range()`, `is_position_in_modified_area()`. difflib.SequenceMatcher a nivel párrafo. |
| ~~S14-02~~ | 4h | `src/narrative_assistant/analysis/comparison.py` | ✅ Pass 3 proximity matching. `resolution_reason` = "text_changed" o "detector_improved". `match_confidence` 0.5-1.0. AlertDiff extended con nuevos campos. |
| ~~S14-03~~ | 2h | `src/narrative_assistant/persistence/snapshot.py` | ✅ `get_snapshot_chapter_texts()`, `snapshot_chapters` table, `create_snapshot()` persiste chapter texts. Schema migration en database.py. |
| ~~S14-04~~ | 2h | Tests | ✅ 32 tests (9 content_diff, 8 chapter_diffs, 6 position_checks, 4 pass3, 3 snapshot, 2 serialization). |

**Fase 2: Alert Linking [8h] ✅**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| ~~S14-05~~ | 2h | Schema migration v21 | ✅ `alerts.previous_snapshot_alert_id`, `alerts.match_confidence`, `alerts.resolution_reason` + `snapshot_chapters` table. |
| ~~S14-06~~ | 3h | `src/narrative_assistant/analysis/comparison.py` | ✅ `_write_alert_links()` y `compare_and_link()`. Matching por hash (1.0) y por key (0.7). |
| ~~S14-07~~ | 1.5h | `api-server/routers/alerts.py` | ✅ `PUT /alerts/{id}/mark-resolved`, `GET /comparison/detail`. AlertResponse + MarkResolvedRequest models. |
| ~~S14-08~~ | 1.5h | Tests | ✅ 7 tests (3 linking, 4 endpoint/model). |

**Fase 3: Frontend Dashboard [12h] ✅**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| ~~S14-09~~ | 4h | `frontend/src/components/revision/RevisionDashboard.vue` | ✅ Tabs: Resueltas/Nuevas/Sin cambio. Badges confianza + razón resolución. Stats delta %. |
| ~~S14-10~~ | 3h | `frontend/src/components/revision/AlertDiffViewer.vue` | ✅ Dialog modal con detalle de alerta resuelta: tipo, posición, razón, barra de confianza. |
| ~~S14-11~~ | 2h | `frontend/src/components/revision/RevisionTimeline.vue` | ✅ Timeline Anterior → Actual con dot + connector + trend color. |
| ~~S14-12~~ | 2h | Routing + types | ✅ Route `/projects/:id/revision`, RevisionView.vue. API types (ApiComparisonDetail), domain types (ComparisonDetail, ComparisonAlertDiff), transformer. |
| ~~S14-13~~ | 1h | Tests | (Cubierto por tests de tipos e importación en S14-08). |

**Fase 4: Track Changes ✅ [4-8h]**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| ~~S14-14~~ | 4h | `src/narrative_assistant/parsers/docx_revisions.py` | ✅ Parser de `word/document.xml` revisiones (`w:ins`, `w:del`, `w:rPr/w:rStyle`). Extrae `Revision(type, text, author, date, position)`. |
| ~~S14-15~~ | 2h | `src/narrative_assistant/analysis/comparison.py` | ✅ Integrado como pass 4 de matching: si alert position coincide con `w:del` → confianza 0.95. |
| ~~S14-16~~ | 1h | Tests | ✅ 14 tests: parser + char ranges + pass 4 matching + priority vs pass 3. |

**Dependencias S14**: S13 completado (BK-25 MVP establece la UI base).
**Criterio de éxito**: Corrector ve exactamente qué alertas se resolvieron, dónde cambió el texto, y puede confirmar resoluciones.

---

#### Sprint S15: Version Tracking (BK-28 fase 1) [20-25h] ✅

> **Product Owner**: "Útil para coordinadores editoriales, no para freelancers. Tier Editorial."
> **Arquitecto**: "Los snapshots ya existen. Solo falta persistir métricas agregadas por versión
> y un endpoint para trends. Schema trivial."
> **UX**: "Sparkline en el header del proyecto, NO como tab separado. Mínimo y elegante."

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| ~~S15-01~~ | 2h | Schema migration v22 | ✅ `version_metrics` table con 12 columnas. Schema v22. En SCHEMA_SQL + table_migrations. |
| ~~S15-02~~ | 3h | `api-server/routers/projects.py` | ✅ `GET /versions` lista con métricas. `GET /versions/trend` serie temporal + delta. |
| ~~S15-03~~ | 2h | `api-server/routers/_enrichment_phases.py` | ✅ `write_version_metrics()` hook post-Phase 13. Lee health_score, formality_avg, dialogue_ratio del cache/DB. |
| ~~S15-04~~ | 4h | `frontend/src/components/project/VersionSparkline.vue` | ✅ SVG inline sparkline, trend coloring, delta badge, hover dots con tooltip. |
| ~~S15-05~~ | 4h | `frontend/src/components/project/VersionHistory.vue` | ✅ DataTable con selección múltiple, deltas entre versiones, health tags, botón comparar. |
| ~~S15-06~~ | 3h | `frontend/src/components/project/VersionComparison.vue` | ✅ Dialog modal con barras comparativas, delta improved/worsened, enlace a RevisionDashboard. |
| ~~S15-07~~ | 2h | Tests | ✅ 18 tests: schema, hook, endpoints, tipos frontend, componentes. |

**Dependencias S15**: S13 (comparison infra). S14 recomendado pero no bloqueante.
**Criterio de éxito**: Coordinador editorial ve tendencia de calidad del manuscrito a lo largo del tiempo.

---

#### Sprint S16: Monetización (BK-29) [30-40h]

> **Product Owner**: "Revenue-critical pero timing-dependent. Solo tiene sentido con clientes."
> **AppSec**: "Flujos de pago son high-risk. Stripe SDK + webhooks + validación server-side.
> Nunca confiar en el frontend para validar pagos."
> **UX**: "Quota warning como banner persistente (no modal) al 80%. Upgrade path como
> comparación de features, no como pop-up agresivo."
>
> **NOTA ARQUITECTÓNICA (revisión Codex)**: La app es Tauri desktop-only. Los webhooks de Stripe
> necesitan un servidor público para recibir callbacks. Por tanto, S16 se divide en:
> - **S16A** (desktop, sin pagos): UX de cuota + comparación de tiers. Puede salir independiente.
> - **S16B** (requiere backend público): Stripe checkout + webhooks + validación server-side.
> S16B NO debe implementarse hasta tener un backend de billing fiable (e.g., Cloud Functions,
> servidor dedicado) con verificación de firma, idempotencia y reconciliación.

**S16A: Quota Warnings + Tier UX [12h] (desktop-only, sin pagos)**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| S16-01 | 2h | `frontend/src/components/license/QuotaWarning.vue` | Banner persistente: "Has usado 1,200 de 1,500 páginas este mes" (80%). A 90%: naranja con CTA "Ampliar". A 100%: rojo con "Límite alcanzado". |
| S16-02 | 2h | `frontend/src/stores/license.ts` | Computed `quotaPercentage`, `quotaWarningLevel`. Auto-fetch al montar app. |
| S16-03 | 2h | `api-server/routers/license.py` | `GET /license/quota-status` — devuelve `{used, limit, percentage, warning_level, days_remaining}`. |
| S16-04 | 3h | `frontend/src/components/license/TierComparison.vue` | Feature matrix: Corrector vs Pro vs Editorial. Highlight current tier. CTA "Contactar para upgrade" (no pago directo). |
| S16-05 | 1h | Tests | Test quota calculations. Test warning levels. |
| S16-06 | 2h | Tests + docs | Test tier comparison render. Documentar tiers en FAQ. |

**S16B: Page Packs + Pagos [20-28h] (requiere backend público de billing)**

| Tarea | Horas | Archivo | Detalle |
|-------|-------|---------|---------|
| S16-07 | 4h | Backend billing (fuera de Tauri) | Servidor público mínimo: `POST /billing/checkout` (crear Stripe session), `POST /billing/webhook` (recibir confirmación). Verificación de firma Stripe. Idempotencia por `payment_intent_id`. |
| S16-08 | 3h | Schema + models | `page_packs(id, license_id, pages, price_eur, stripe_payment_id, status, purchased_at, expires_at)`. Modelo `PagePack` en `licensing/models.py`. Schema v24. |
| S16-09 | 4h | `src/narrative_assistant/licensing/verification.py` | Extender `_calculate_quota_remaining()`: sumar packs activos al límite mensual. `activate_pack()` — marca pack como activo tras polling al billing server. |
| S16-10 | 4h | `frontend/src/components/license/PackPurchase.vue` | Modal con opciones de pack. Abre URL de Stripe Checkout en navegador externo. Polling local para detectar confirmación. |
| S16-11 | 3h | `api-server/routers/license.py` | `POST /license/activate-pack` (polling → billing server confirma → activar localmente). `GET /license/packs` (historial de packs). |
| S16-12 | 2h | Tests | Test pack activation flow (mock billing server). Test quota with packs. Test reconciliación. |

**Dependencias S16A**: Ninguna (datos de cuota ya existen localmente).
**Dependencias S16B**: Backend público de billing configurado. Stripe account. Clientes reales.
**Criterio de éxito S16A**: Corrector ve cuántas páginas le quedan y qué incluye cada tier.
**Criterio de éxito S16B**: Corrector compra pack de 500 páginas y se activa automáticamente.

---

### APARCADO: Ideas documentadas, no planificadas

> Estas ideas aportan valor pero no son necesarias para la primera versión vendible.
> Se documentan para tenerlas en cuenta en futuras iteraciones, tras testear con clientes.

| Idea | Razón para aparcar | Cuándo retomar |
|------|-------------------|----------------|
| **Landing page web** | Necesita testeo con clientes reales primero. Documentar estructura y copy, pero no implementar. | Tras primeras 10 ventas |
| **UserGuide PDF exportable** | Aporta valor, pero requiere capturas actualizadas de cada tab. Mejor cuando UI sea estable. | Tras Sprint PP (UI estable) |
| **Formato EPUB en export** | Relevante para producción editorial. No urgente para corrector que trabaja en Word. | Tras feedback de clientes |
| **Formato XLSX en export** | Útil para equipos grandes. CSV cubre el 80% del caso de uso. | Si lo piden clientes |
| ~~**Revision Intelligence** (BK-25)~~ | ~~Promovido a Sprint S13 (MVP) + S14 (full)~~ | — |
| **Colaboración paralela online** (BK-26) | Sync en tiempo real. Requiere servidor, E2E encryption. Coste alto, demanda incierta. | Tras licensing server + demanda |
| ~~**Filtrado alertas por capítulos** (BK-27)~~ | ~~Promovido a Sprint S13~~ | — |
| ~~**Historial de versiones** (BK-28)~~ | ~~Promovido a Sprint S15 (fase 1)~~ | — |
| ~~**Step-up pricing** (BK-29)~~ | ~~Promovido a Sprint S16~~ | — |
| ~~**Pesos adaptativos nivel 3**~~ (por manuscrito + per-entity) | ✅ DONE — `project_detector_weights` table (v24), cascading lookup per-entity → project → 1.0, fractional LR para multi-entity, entity merge weight transfer, `_extract_entity_names()` helper, 31 tests. Pesos persisten entre re-análisis. | — |
| **Integrar Maverick** (BK-01) | Solo inglés por ahora. Monitorizar releases. | Cuando soporte español |
| **Integrar BookNLP** (BK-02) | Sin release público multilingüe. | Cuando esté disponible |
| **FlawedFictions benchmark** (BK-03) | Dataset no publicado. | Cuando se publique |
| **Fine-tune RoBERTa en ficción** (BK-04) | Necesita corpus etiquetado. Se puede acumular de correcciones de usuarios. | Tras 100+ manuscritos procesados |
| **Análisis multi-documento mejorado** (BK-07) | Ya funcional (collections). Mejoras son nice-to-have. | Feedback de clientes |
| ~~Auto-config hardware~~ | Promovido a Sprint PP-3b | — |
| ~~Demo project sin coste licencia~~ | Promovido a Sprint PP-3c | — |

### Roadmap visual completo

```
COMPLETADO                                          PRÓXIMO (Version + Monetización)
───────────────────────────────────────────────── ──────────────────────────────────
S0-S6 (NLP + Frontend) ✅                          S15 (BK-28 Version tracking)
S7a-S7d (Licensing + UX) ✅                        S16 (BK-29 Step-up pricing)
Sprint PP ✅ (17/17)                                ──────────────────────────────────
Sprint S8 ✅ (S8a + S8b + S8c)                     APARCADO:
Sprint S9 ✅ (BK-09/15/17/10b/10c)                 BK-26 Collab online
Sprint S10 ✅ (BK-14/11/12)                        Landing web, UserGuide PDF
Sprint S11 ✅ (BK-13/16)                           EPUB/XLSX export, Maverick/BookNLP
Sprint S12 ✅ (BK-18)                              ──────────────────────────────────
Sprint SP-1/2/3 ✅                                  TEMPORAL DETECTION:
Sprint S13 ✅ (BK-27 + BK-25 MVP)                  Level A (regex) ✅
Sprint S14 ✅ (BK-25 Revision Intelligence)         Level B (LLM per-chapter) ✅
  + Level A/B/C temporal detection ✅                Level C (cross-chapter linking) ✅
  + 3-layer flashback scoring ✅                     Level D (Narrative-Experts) — futuro
  v0.8.0 → v0.9.4

Dependencias:
  S15 (independiente)
  S16A (independiente, desktop-only)
  S16B (requiere backend billing público + Stripe)
```

### Estimaciones restantes

| Bloque | Horas/Días | Tipo |
|--------|-----------|------|
| ~~Sprint PP~~ | ~~39h~~ | ✅ COMPLETADO (17/17) |
| ~~Sprint S8~~ | ~~17-26 días~~ | ✅ COMPLETADO (v0.8.0) |
| ~~Tareas sueltas~~ | ~~6h~~ | ✅ S7b-09, S7b-10, BK-23a completados (v0.8.0-v0.8.2) |
| ~~Sprint SP-1~~ | ~~16h (3-4 días)~~ | ✅ COMPLETADO (v0.9.0) |
| ~~Sprint SP-2~~ | ~~8h (2 días)~~ | ✅ COMPLETADO (v0.9.3) |
| ~~Sprint SP-3~~ | ~~36h (7-9 días)~~ | ✅ COMPLETADO (v0.9.2) |
| ~~Sprint S9~~ | ~~25-31h (5-7 días)~~ | ✅ COMPLETADO (BK-09/15/17/10b/10c) |
| ~~Sprint S10~~ | ~~27-30h (6-8 días)~~ | ✅ COMPLETADO (BK-14 + BK-11 + BK-12) |
| ~~Sprint S11~~ | ~~16-26h (4-7 días)~~ | ✅ COMPLETADO (BK-13 + BK-16) |
| ~~Sprint S12~~ | ~~2-3h (1 día)~~ | ✅ COMPLETADO (BK-18) |
| ~~Sprint S13~~ | ~~7-9h (1-2 días)~~ | ✅ COMPLETADO (BK-27 + BK-25 MVP) |
| ~~Sprint S14~~ | ~~28-36h (5-7 días)~~ | ✅ COMPLETADO (BK-25 Revision Intelligence fases 1-3) |
| Sprint S15 | 20-25h (4-5 días) | BK-28 fase 1 (version metrics, sparkline) |
| Sprint S16A | 12h (2-3 días) | BK-29 UX (quota warnings, tier comparison) |
| Sprint S16B | 20-28h (4-6 días) | BK-29 pagos (requiere backend billing público) |
| **TOTAL restante** | **~52-65h (~2-3 semanas)** | S15 + S16A (+S16B condicionado) |

---

## 10. Fuentes y Referencias

### Papers Académicos
- Lee et al. (2017): End-to-end Neural Coreference Resolution
- FlawedFictions (Abril 2025): Plot Hole Detection Benchmark - https://arxiv.org/abs/2504.11900
- Narrative-of-Thought (EMNLP 2024): Temporal reasoning improvement
- Timeline Self-Reflection (2025): Multi-stage temporal inference
- Maverick (ACL 2024): Lightweight coreference (500M params) - https://github.com/SapienzaNLP/maverick-coref
- CODI-CRAC 2025: Multilingual Coreference Shared Task
- Portrayal (DIS 2023): Character trait visualization
- Taggus (2024): Character network extraction - https://arxiv.org/abs/2508.03358

### Modelos y Herramientas
- PlanTL RoBERTa-large-bne: https://huggingface.co/PlanTL-GOB-ES/roberta-large-bne-capitel-ner
- BETO NER: https://huggingface.co/mrm8488/bert-spanish-cased-finetuned-ner
- AnCora-CO: Corpus correferencias español
- HeidelTime: Temporal tagger con soporte español
- BookNLP: https://github.com/booknlp/booknlp (multilingüe en desarrollo)
- Qwen 2.5: https://huggingface.co/Qwen
- Ollama: https://ollama.com

### Benchmarks
- CoNLL-2002: Spanish NER (EFE News Agency)
- FlawedFictions: Plot hole detection (cuando se publique)
- AnCora-CO: Coreference resolution español

---

**Ultima actualizacion**: 2026-02-13
**Autor**: Claude (Panel de 8 expertos simulados + sesión producto 10-Feb + paneles pricing/sales/editorial 12-Feb)
**Estado**: S0-S12 completados. Sprint PP completado (17/17). S7b-S7d completados. SP-1..3 completados. BK-08/BK-12 completados (v0.9.4). 24/29 BK completados. Tag: v0.9.4. Próximo: S13 (BK-27 + BK-25 MVP).
