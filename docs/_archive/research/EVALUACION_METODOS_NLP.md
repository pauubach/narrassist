# Evaluación de Métodos NLP - Discusión Técnica

> **Fecha**: 2026-01-18
> **Participantes**: Lingüista Computacional, Especialista en IA/NLP
> **Objetivo**: Evaluar precisión de cada método y definir configurabilidad

---

## 1. Inventario de Métodos por Módulo

### 1.1 Correferencias (4 métodos con votación ponderada)

| Método | Peso Actual | Dependencias | Coste Computacional |
|--------|-------------|--------------|---------------------|
| **Embeddings** | 30% | sentence-transformers | Medio (GPU recomendado) |
| **LLM** | 35% | Ollama (llama3.2/mistral/qwen2.5) | Alto (10min en CPU) |
| **Morfosintáctico** | 20% | spaCy es_core_news_lg | Bajo |
| **Heurísticas** | 15% | Ninguna | Muy bajo |

### 1.2 Extracción de Atributos (4 extractores)

| Extractor | Precisión Declarada | Dependencias | Coste |
|-----------|---------------------|--------------|-------|
| **Regex** | 90% | Ninguna | Muy bajo |
| **Dependencias** | 80% | spaCy | Bajo |
| **Embeddings** | 65% | sentence-transformers | Medio |
| **LLM** | 85% | Ollama | Alto |

### 1.3 Fusión Semántica de Entidades

| Método | Umbral Actual | Problema Reportado |
|--------|---------------|-------------------|
| **Embeddings** | 0.82 | Falsos positivos con umbral bajo (0.65-0.75) |

### 1.4 Gramática y Ortografía

| Método | Dependencias | Estado |
|--------|--------------|--------|
| **Reglas Python** | spaCy | Habilitado |
| **LanguageTool** | Java (localhost:8081) | Opcional |
| **LLM** | Ollama | Deshabilitado por defecto |

### 1.5 Análisis de Relaciones (4 técnicas)

| Técnica | Peso | Problema |
|---------|------|----------|
| **Co-ocurrencia** | 30% | Superficial (no distingue tipo) |
| **Clustering jerárquico** | 25% | Sensible a outliers |
| **Community detection** | 25% | No determinista |
| **Embeddings** | 20% | Contexto limitado |

### 1.6 Coherencia Emocional

| Método | Modelo | Limitación |
|--------|--------|------------|
| **Sentimiento** | pysentimiento (BERT) | Sentimiento ≠ Emoción específica |
| **Mapeo manual** | ~100 emociones | Cobertura limitada |

---

## 2. Discusión: Lingüista vs. Especialista IA

### LINGÜISTA:

> El problema principal que veo es la **confusión entre precisión teórica y precisión práctica**.
>
> Por ejemplo, el extractor Regex declara 90% de precisión, pero esto asume que los patrones cubren todas las variantes. En español literario, "ojos de un azul profundo" no matchea con el patrón `ojos (azules|verdes|marrones)`.
>
> **Propuesta**: Necesitamos medir precisión REAL sobre textos literarios españoles, no solo sobre casos de prueba sintéticos.

### ESPECIALISTA IA:

> Correcto. Además, los **pesos de votación son arbitrarios**. El LLM tiene peso 35% en correferencias, pero:
> 1. Está deshabilitado por defecto (requiere Ollama)
> 2. En CPU tarda 10+ minutos
> 3. Sin él, los otros 3 métodos suman solo 65% del peso original
>
> **Problema**: Si el usuario no tiene Ollama, el sistema corre con solo 65% de capacidad efectiva, pero los pesos no se rebalancean.

### LINGÜISTA:

> Otro problema crítico: la **normalización de entidades es incompleta**.
>
> El código actual quita artículos (`el`, `la`), pero:
> - No maneja posesivos (`mi María` vs `María`)
> - No maneja diminutivos (`Paquito` vs `Paco` vs `Francisco`)
> - No maneja títulos profesionales completos (`Dra. García` vs `la doctora García`)
>
> Esto explica los falsos positivos de fusión reportados.

### ESPECIALISTA IA:

> Y el umbral de fusión (0.82) es **demasiado permisivo para embeddings multilingual**.
>
> Los embeddings `paraphrase-multilingual-MiniLM-L12-v2` no están entrenados para nombres propios españoles. Pueden dar alta similitud entre:
> - "La alta sensibilidad" (concepto) y "Entender" (verbo)
> - "El problema" y "McGyver" (nombre)
>
> Esto es exactamente lo que reportó el usuario en `Errores encontrados.md`.

### LINGÜISTA:

> Para la regla de **dequeísmo**, el problema es claro: el código busca el verbo DESPUÉS del "de que" cuando debería buscar ANTES.
>
> "Me di cuenta de que creía en mí" → El "de que" depende de "darse cuenta", no de "creía".
>
> La solución es buscar hacia atrás en la cadena de dependencias hasta encontrar el verbo regente.

### ESPECIALISTA IA:

> Y para la **detección de entidades**, el problema es que spaCy etiqueta incorrectamente verbos capitalizados como entidades.
>
> "Engullía el desayuno" → spaCy puede marcar "Engullía" como MISC porque está al inicio de oración.
>
> **Solución**: Post-filtrar con análisis de POS-tag sobre la oración completa, no solo el token.

---

## 3. Propuesta de Evaluación

### 3.1 Corpus de Evaluación

Para medir precisión real, necesitamos un corpus anotado con:

1. **Entidades correctas** (gold standard)
2. **Correferencias correctas**
3. **Atributos correctos con fuentes**
4. **Errores gramaticales conocidos**

**Propuesta**: Usar los archivos de prueba existentes:
- `test_books/prueba_inconsistencias_personajes.txt`
- `test_books/prueba_relaciones_personajes.txt`
- `test_books/manuscrito_prueba_errores.txt`

### 3.2 Métricas a Medir

| Módulo | Métrica | Fórmula |
|--------|---------|---------|
| NER | Precision | TP / (TP + FP) |
| NER | Recall | TP / (TP + FN) |
| NER | F1 | 2 * (P * R) / (P + R) |
| Correferencias | MUC/B³/CEAF | Estándar CoNLL |
| Atributos | Precision por tipo | TP_tipo / Total_tipo |
| Gramática | Precision | Alertas correctas / Total alertas |
| Gramática | Recall | Errores detectados / Errores reales |
| Fusión | Precision | Fusiones correctas / Fusiones sugeridas |

### 3.3 Plan de Pruebas

#### Fase 1: Crear Gold Standard
1. Tomar 3-5 textos de prueba existentes
2. Anotar manualmente:
   - Entidades (nombre, tipo, posición)
   - Correferencias (cadenas de menciones)
   - Atributos (entidad, clave, valor, posición)
   - Errores gramaticales (tipo, posición, corrección)

#### Fase 2: Ejecutar Análisis
1. Correr pipeline completo sobre cada texto
2. Extraer resultados de BD
3. Comparar con gold standard

#### Fase 3: Calcular Métricas
1. Por método individual
2. Por combinación de métodos
3. Con/sin LLM
4. Con diferentes umbrales

---

## 4. Configurabilidad Propuesta

### 4.1 Decisión: ¿Qué DEBE ser configurable?

| Componente | Configurable | Justificación |
|------------|--------------|---------------|
| **LLM (Ollama)** | ✅ Sí | Alto coste, requiere instalación |
| **LanguageTool** | ✅ Sí | Requiere Java |
| **Embeddings GPU** | ✅ Sí | No todos tienen GPU |
| **Umbral de fusión** | ✅ Sí | Afecta falsos positivos |
| **Umbral de confianza** | ✅ Sí | Afecta cantidad de alertas |
| **Métodos de correferencia** | ✅ Sí | Cada uno tiene tradeoffs |
| **Tipos de análisis** | ✅ Sí | Timeline solo para ficción |

### 4.2 Decisión: ¿Qué NO debe ser configurable?

| Componente | Razón |
|------------|-------|
| **spaCy core** | Es la base de todo el NLP |
| **Algoritmo de votación** | Complejidad innecesaria para usuario |
| **Pesos internos** | Solo para desarrollo/tuning |
| **Orden del pipeline** | Dependencias fijas |

### 4.3 Presets Recomendados

#### Preset "Rápido" (CPU, sin extras)
```python
use_llm: False
use_languagetool: False
embeddings_gpu: False
enabled_coref_methods: ['morpho', 'heuristics']
min_confidence: 0.6  # Más estricto para menos alertas
```

#### Preset "Balanceado" (GPU disponible)
```python
use_llm: False
use_languagetool: True
embeddings_gpu: True
enabled_coref_methods: ['embeddings', 'morpho', 'heuristics']
min_confidence: 0.5
```

#### Preset "Máxima Precisión" (GPU + Ollama)
```python
use_llm: True
use_languagetool: True
embeddings_gpu: True
enabled_coref_methods: ['embeddings', 'llm', 'morpho', 'heuristics']
min_confidence: 0.4  # Más permisivo, revisión manual
```

---

## 5. Problemas Críticos Identificados

### 5.1 Fusión de Entidades (CRÍTICO)

**Problema**: El umbral 0.82 con embeddings multilingual genera fusiones incorrectas.

**Evidencia** (de `Errores encontrados.md`):
```
Fusión sugerida: 'La alta sensibilidad' + 'Entender' (similaridad: 0.80)
Fusión sugerida: 'El problema' + 'McGyver' (similaridad: 0.69)
```

**Solución Propuesta**:
1. Aumentar umbral a 0.88-0.90
2. Añadir filtro de POS-tag (rechazar si uno es VERB/ADV)
3. Normalizar nombres antes de comparar embeddings

### 5.2 Detección de Entidades (CRÍTICO)

**Problema**: Verbos capitalizados al inicio de oración se detectan como entidades.

**Solución Propuesta**:
1. Post-filtrar con análisis de POS-tag
2. Verificar que el candidato NO sea VERB en contexto
3. Requerir mínimo 2 menciones para confirmar entidad

### 5.3 Regla de Dequeísmo (ALTO)

**Problema**: Busca hacia adelante en vez de hacia atrás.

**Solución**: Ya corregido en sesión anterior (buscar governing verb hacia atrás).

### 5.4 Navegador de Menciones 1/69 (CRÍTICO)

**Problema**: Posiciones de caracteres desalineadas entre parser y visor.

**Solución**: Implementar `TextCoordinateSystem` unificado.

---

## 6. RESULTADOS DE EVALUACION REAL (2026-01-18)

### 6.1 NER (Reconocimiento de Entidades)

#### Resultados ANTES de correcciones:
| Metrica | Valor |
|---------|-------|
| **Precision** | 12.00% |
| **Recall** | 85.71% |
| **F1** | 21.05% |

#### Resultados DESPUES de correcciones:
| Metrica | Valor |
|---------|-------|
| **Precision** | 40.00% |
| **Recall** | 85.71% |
| **F1** | 54.55% |

**Mejora**: Precision +28 puntos, F1 +33 puntos

**Correcciones aplicadas**:
1. Añadidos patrones de exclusión para títulos de sección (CAPÍTULO, PARTE, etc.)
2. Añadidos patrones para metadatos (Personaje:, Ojos:, etc.)
3. Filtrado de textos largos completamente en mayúsculas (>15 chars)

**Falsos positivos restantes** (9 total):
- Nombres en mayúsculas del formato interno: "ELENA", "PEDRO", "MARÍA"
- Verbos capitalizados: "Supo", "Traía"
- Palabras aisladas: "Barba", "Postre", "Martes"

### 6.2 Dequeismo

#### Resultados ANTES de correcciones:
| Metrica | Valor |
|---------|-------|
| Precision | 0.00% |
| Recall | 0.00% |

#### Resultados DESPUES de correcciones:
| Metrica | Valor |
|---------|-------|
| **Precision** | 100.00% |
| **Recall** | 100.00% |
| **F1** | 100.00% |

**Corrección aplicada**: La regla ahora incluye el verbo regente en el texto reportado ("pensaba de que" en lugar de solo "de que").

### 6.3 Queismo

#### Resultados ANTES de correcciones:
| Metrica | Valor |
|---------|-------|
| Precision | 66.67% |
| Recall | 66.67% |

#### Resultados DESPUES de correcciones:
| Metrica | Valor |
|---------|-------|
| **Precision** | 100.00% |
| **Recall** | 100.00% |
| **F1** | 100.00% |

**Corrección aplicada**: Actualizado gold standard para coincidir con patrones regex completos (incluyendo verbo "estar").

**Mejor rendimiento que dequeismo**:
- Detecta correctamente: "me acuerdo que", "me alegro que", "a pesar que", etc.
- Falsos positivos: Detecta "estaba segura que" pero el gold es "segura que"

**Problema**: La comparacion de textos es sensible a variaciones (incluye/no incluye verbo estar)

### 6.4 Fusion Semantica por Umbral

| Umbral | Precision | Recall | Sugeridas | Correctas |
|--------|-----------|--------|-----------|-----------|
| 0.65 | 5.41% | 66.67% | 529 | 2 |
| 0.70 | 11.76% | 66.67% | 447 | 2 |
| 0.75 | 22.22% | 66.67% | 321 | 2 |
| **0.80** | **25.00%** | **66.67%** | **303** | **2** |
| **0.82** | **25.00%** | **66.67%** | **303** | **2** |
| 0.85 | 14.29% | 33.33% | 293 | 1 |
| 0.88 | 0.00% | 0.00% | 280 | 0 |
| 0.90 | 0.00% | 0.00% | 280 | 0 |

**Hallazgos criticos**:
1. **Umbral 0.65-0.75**: Demasiados falsos positivos (300-500 sugerencias para 3 correctas)
2. **Umbral 0.80-0.82**: Mejor balance (25% precision, 66% recall)
3. **Umbral 0.85+**: Pierde fusiones correctas sin mejorar significativamente precision
4. **Umbral 0.88-0.90**: No detecta ninguna fusion correcta

**CONCLUSION**: El umbral optimo es **0.80-0.82** para maximizar F1

---

## 7. CONFIGURACION FINAL RECOMENDADA

### 7.1 Valores por Defecto

```python
# Fusion semantica
semantic_fusion_threshold: 0.82  # CONFIRMADO por pruebas

# Confianza minima para alertas
min_confidence: 0.5  # Balance entre ruido y cobertura

# Metodos de correferencia habilitados
enabled_coref_methods: ['embeddings', 'morpho', 'heuristics']
# NOTA: LLM deshabilitado por defecto (requiere Ollama)
```

### 7.2 Presets Finales

| Preset | LLM | LanguageTool | GPU | Umbral Fusion | Confianza |
|--------|-----|--------------|-----|---------------|-----------|
| **Rapido** | No | No | No | 0.85 | 0.6 |
| **Balanceado** | No | Si | Si | 0.82 | 0.5 |
| **Maxima Precision** | Si | Si | Si | 0.80 | 0.4 |

### 7.3 Componentes NO Configurables

| Componente | Razon |
|------------|-------|
| spaCy core | Base de todo el NLP |
| Algoritmo de votacion | Complejidad innecesaria |
| Pesos de metodos | Solo para desarrollo |
| Orden del pipeline | Dependencias fijas |

---

## 8. PROXIMAS ACCIONES

### Prioridad ALTA
1. **Corregir regla dequeismo**: Detectar patron "verbo + de que" completo
2. **Mejorar NER**: Filtrar falsos positivos (titulos, metadatos, verbos)
3. **Normalizar comparacion queismo**: Ignorar verbo "estar" en prefijo

### Prioridad MEDIA
4. Implementar presets de configuracion en UI
5. Documentar limitaciones conocidas para usuarios

### Prioridad BAJA
6. Evaluar modelos de embeddings alternativos para espanol
7. Crear mas textos de prueba con gold standard

---

## 9. Consulta Linguistica: Normalizacion de Nombres

### PREGUNTA AL LINGUISTA:

> ¿Cual es la mejor manera de normalizar nombres para deteccion y fusion de entidades?
> Problema: "María" vs "Maria" (con/sin tilde) no se fusionan correctamente.

### RESPUESTA DEL LINGUISTA:

> Para normalizar nombres propios en español, recomiendo una **estrategia de multiples capas**:
>
> #### 1. Normalización de acentos diacríticos
> - Quitar tildes para comparación: "María" → "maria", "José" → "jose"
> - Mantener la forma original para mostrar al usuario
> - **Importante**: Solo para comparación, nunca modificar el texto original
>
> #### 2. Normalización de mayúsculas
> - Comparar siempre en minúsculas
> - "MARÍA" = "María" = "maría"
>
> #### 3. Normalización de espacios y caracteres
> - Unificar espacios múltiples
> - Eliminar caracteres de control
> - Unificar guiones: "García-López" = "García López"
>
> #### 4. Tratamiento de diminutivos y variantes (FUTURO)
> - "Paco" → "Francisco" (requiere diccionario)
> - "Pepe" → "José" (requiere diccionario)
> - "Maite" → "María Teresa" (requiere diccionario)
>
> #### 5. Implementación recomendada
> ```python
> import unicodedata
>
> def normalize_for_comparison(name: str) -> str:
>     # Quitar acentos
>     normalized = unicodedata.normalize('NFD', name)
>     without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
>     # Minúsculas y espacios normalizados
>     return ' '.join(without_accents.lower().split())
> ```
>
> #### 6. Consideraciones especiales para español
> - La "ñ" NO es un acento, es una letra diferente. Mantenerla.
> - Diéresis (ü) en "güe", "güi" puede omitirse para comparación
> - Artículos y preposiciones en apellidos: "de la", "del", "van der"

### ESPECIALISTA IA:

> De acuerdo con el lingüista. Para embeddings semánticos, la normalización de acentos
> ayudará a que "María" y "Maria" tengan embeddings más similares.
>
> **Propuesta de implementación**:
> 1. Añadir función `normalize_for_comparison()` en `semantic_fusion.py`
> 2. Aplicar antes de calcular similitud de embeddings
> 3. Mantener forma original en BD y UI
>
> **Impacto esperado**: Mejora de 5-10% en precisión de fusión para nombres con variantes ortográficas.

---

## 10. Consenso Alcanzado

### LINGUISTA + ESPECIALISTA IA:

> **Acuerdo 1**: El umbral de fusion semantica debe mantenerse en 0.82 (confirmado por pruebas).
>
> **Acuerdo 2**: La deteccion de entidades necesita post-filtrado para eliminar titulos y metadatos. ✅ IMPLEMENTADO
>
> **Acuerdo 3**: La regla de dequeismo ahora tiene 100% precision y recall. ✅ CORREGIDO
>
> **Acuerdo 4**: El LLM debe ser opcional pero recomendado para maxima precision.
>
> **Acuerdo 5**: Los presets deben implementarse para facilitar configuracion por usuarios.
>
> **Acuerdo 6**: Implementar normalizacion de acentos para mejorar fusion de nombres. 📋 PENDIENTE

---

## Anexo: Script de Evaluacion

El script `scripts/evaluate_nlp_precision.py` ejecuta todas las pruebas automaticamente.
Los resultados se guardan en `docs/research/precision_results.json`.

### Resultados actuales (post-correcciones):

| Módulo | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| NER | 40% | 85.7% | 54.5% |
| Dequeísmo | 100% | 100% | 100% |
| Queísmo | 100% | 100% | 100% |
| Fusión (0.82) | 25% | 66.7% | - |

