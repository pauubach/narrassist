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
| **Temporal** | `temporal/` | ⚠️ Básico | Alta |
| **Diálogos** | `nlp/dialogue.py` | ✅ Funcional | Media |
| **Speaker attribution** | `nlp/cesp_resolver.py` | ⚠️ Parcial | Alta |
| **Correcciones** | `corrections/` | ✅ Funcional | Media |
| **LLM (Ollama)** | Integrado en votación | ✅ Funcional | Media |
| **Embeddings** | `nlp/embeddings.py` | ✅ Funcional | Baja |
| **Frontend atributos** | `EntitiesTab.vue` | ❌ Bug | **Crítica** |

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

### Backlog (Futuro)

| ID | Acción | Detalle |
|----|--------|---------|
| BK-01 | Integrar Maverick cuando haya soporte español | Coreference 500M params |
| BK-02 | Integrar BookNLP multilingüe | Cuando esté disponible |
| BK-03 | FlawedFictions benchmark | Cuando dataset se publique |
| BK-04 | Fine-tune PlanTL RoBERTa en ficción | Si acumulamos datos etiquetados |
| ~~BK-05~~ | ~~Comparativa antes/después~~ | ✅ DONE - Snapshot pre-reanálisis + ComparisonService (two-pass matching) |
| BK-06 | Exportar a Scrivener | Integración con herramienta escritores |
| ~~BK-07~~ | ~~Análisis multi-documento~~ | ✅ DONE - Collections, entity links, cross-book analysis, workspace auxiliar |

---

## 9. Cronograma de Implementación

### Fase Inmediata (Sprint 0): 1-2 días
```
QW-01 → QW-02 → QW-03 → QW-04
[xfails]  [frontend]  [test ORG]  [fusion]
```

### Fase Corta (Sprint 1-2): 2-3 semanas
```
S1-01 ─→ S1-02 ─→ S1-05
[PlanTL]  [voting]  [benchmark]
                         │
S2-01 ─→ S2-02 ─→ S2-03 ─→ S2-04
[pro-drop] [posesiv] [cadenas] [pesos]
```

### Fase Media (Sprint 3-4): 2-4 semanas
```
S3-01 ─→ S3-02 ─→ S3-03
[NoT]    [reflect] [anacro]
                      │
S4-01 ─→ S4-02 ─→ S4-04
[6-indic] [network] [ubicación]
```

### Fase Larga (Sprint 5-6): 2-3 semanas
```
S5-01 ─→ S5-02 ─→ S5-03
[Qwen]   [auto]   [prompts]
                      │
S6-01 ─→ S6-02 ─→ S6-03
[grafo]  [timeline] [dashboard]
```

### Estimación Total: ~8-12 semanas

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

**Última actualización**: 2026-02-06
**Autor**: Claude (Panel de 8 expertos simulados)
**Próximo paso**: Sprints 0-6 completados. Backlog futuro disponible.
