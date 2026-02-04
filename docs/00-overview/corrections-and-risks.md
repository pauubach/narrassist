# Correcciones Técnicas Críticas y Riesgos

[← Volver a Overview](./README.md) | [← Índice principal](../../README.md)

---

## IMPORTANTE: LEER ANTES DE IMPLEMENTAR

Este documento contiene las **correcciones críticas** identificadas por 7 subagentes OPUS especializados. Las expectativas originales del documento eran demasiado optimistas. Este documento refleja la **realidad** de las capacidades NLP actuales.

---

## Correcciones Técnicas Críticas

### 1. NER (Reconocimiento de Entidades)

| Aspecto | Valor INCORRECTO | Valor CORRECTO |
|---------|------------------|----------------|
| Modelo | `es_dep_news_trf` | **`es_core_news_lg`** |
| F1 en ficción | 75-80% | **60-70%** |

**Razón**: El modelo `es_dep_news_trf` **NO tiene NER integrado**. Solo tiene parsing de dependencias.

**Solución**:
- Usar `es_core_news_lg` para NER
- Implementar gazetteers dinámicos para nombres inventados/creativos
- La validación manual es **obligatoria**, no opcional

```python
# CORRECTO
import spacy
nlp = spacy.load("es_core_news_lg")  # Este SÍ tiene NER

# INCORRECTO - NO USAR
# nlp = spacy.load("es_dep_news_trf")  # Este NO tiene NER
```

---

### 2. Correferencia

| Aspecto | Valor INCORRECTO | Valor CORRECTO |
|---------|------------------|----------------|
| F1 esperado | 65% | **45-55%** |
| Sujetos detectables | ~80% | **~50-60%** |

**Razón**: El **pro-drop** en español hace que ~40-50% de los sujetos sean invisibles.

**Ejemplo de pro-drop**:
```
"Llegó tarde. Pensó que nadie lo notaría."
         ↑          ↑
    (él/ella)   (él/ella) - sujetos omitidos
```

**Solución**:
- STEP 2.2 (Fusión Manual) es **OBLIGATORIO**, no opcional
- Sin fusión manual, el sistema NO es usable
- Esperar ~50% de errores en correferencia automática

---

### 3. Focalización

| Aspecto | Valor INCORRECTO | Valor CORRECTO |
|---------|------------------|----------------|
| Viabilidad | MEDIA-BAJA | **BAJA** |
| Tasa de error | ~30% | **>50%** |

**Razón**: El pro-drop hace imposible detectar automáticamente quién piensa/siente en la mayoría de casos.

**Ejemplo**:
```
"Pensó que era un idiota."
   ↑
¿Quién pensó? Sin sujeto explícito, no se puede determinar.
```

**Solución**:
- Solo verificar focalización con sujetos **EXPLÍCITOS**
- Para sujetos implícitos: confianza MUY BAJA o ignorar
- Declaración manual de focalización por capítulo (STEP 6.1)

---

### 4. Memoria RAM

| Aspecto | Riesgo |
|---------|--------|
| Requisito declarado | 16GB RAM |
| Riesgo real | Puede no ser suficiente con spaCy + embeddings + LLM |

**Solución**:
- Benchmark obligatorio en STEP 0.1 con documento de 100k palabras
- Si falla, considerar:
  - Procesamiento por capítulos (no todo el documento en memoria)
  - Modelos más pequeños
  - Descartar LLM local

---

## Tabla de Riesgos

| Riesgo | Prob. | Impacto | STEP | Mitigación |
|--------|-------|---------|------|------------|
| Correferencia <50% F1 | ALTA | ALTO | 2.1 | Fusión manual OBLIGATORIA |
| Memoria >16GB | MEDIA | ALTO | 0.1 | Benchmark obligatorio |
| Atribución diálogo <60% | MEDIA | MEDIO | 5.4 | Confianza explícita |
| Focalización inservible | ALTA | BAJO | 6.2 | Solo sujetos explícitos |
| Parser DOCX falla | MEDIA | MEDIO | 1.1 | Fixtures variados |
| Embeddings lentos | MEDIA | MEDIO | 3.3 | Batch + cache |
| Timeline con ciclos | BAJA | ALTO | 4.3 | Validación de grafo |
| Perfiles voz insuficientes | ALTA | MEDIO | 5.1 | Mínimo 500 palabras |
| Comunicación Tauri-Python | MEDIA | ALTO | Futuro | Prototipar IPC primero (post-MVP) |

---

## Resumen de Revisión por Subagentes

Esta especificación fue revisada por 7 subagentes OPUS:

| Subagente | Hallazgo Principal |
|-----------|-------------------|
| **Lingüista Computacional** | NER/Coref sobrestimados; pro-drop subestimado |
| **Arquitecto Software** | Faltaba schema BD completo; comunicación Tauri-Python |
| **Product Manager** | MVP demasiado grande; falta validación de demanda |
| **Narratólogo** | Focalización sobresimplificada |
| **Editor Profesional** | Hoja de estilo progresiva es crítica |
| **UX Designer** | Faltan wireframes; 15+ estados UI indefinidos |
| **OPUS Integrador** | Documento mezclaba spec con justificación |

---

## Implicaciones para la Implementación

### Lo que FUNCIONA bien
- Parser de DOCX
- Detección de estructura (capítulos/escenas)
- Detección de diálogo (patrones regex)
- Repeticiones léxicas
- Métricas estilométricas

### Lo que funciona con LIMITACIONES
- NER (~60-70% en ficción - necesita gazetteers)
- Correferencia (~45-55% - necesita fusión manual)
- Repeticiones semánticas (embeddings son buenos)
- Perfiles de voz (necesita suficiente texto)

### Lo que tiene ALTA tasa de error
- Focalización automática (>50% error)
- Atribución de hablante sin acotación (~40% error)
- Detección de sujetos implícitos (pro-drop)

---

## Prioridad de Implementación Ajustada

Dado estos riesgos, la prioridad recomendada es:

```
P0 (OBLIGATORIO):
├── STEP 0.1-0.3: Entorno + BD
├── STEP 1.1-1.4: Parser + NER + Diálogos
└── STEP 2.1-2.4: Coref + Fusión + Atributos

P1 (ALTO VALOR, bajo riesgo):
├── STEP 3.1: Variantes de grafía
├── STEP 7.3: Hoja de estilo
└── STEP 7.4: CLI

P2 (POST-VALIDACIÓN):
├── STEP 3.2-3.3: Repeticiones
├── STEP 4.1-4.3: Timeline
└── STEP 5.1-5.4: Voz y registro

P3 (EXPERIMENTAL - alta tasa de error):
├── STEP 6.1-6.2: Focalización
└── [FUTURO] Tauri UI (no STEP definido - evaluar tras validar CLI)
```

---

## Siguiente Paso

Con esta información en mente, comienza con [STEP 0.1: Configuración del Entorno](../../steps/phase-0/step-0.1-environment.md).

El benchmark de memoria en STEP 0.1 validará si el hardware es suficiente antes de invertir más tiempo.
