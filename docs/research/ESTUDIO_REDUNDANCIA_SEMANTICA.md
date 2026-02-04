# Estudio: Detección de Redundancia Semántica

**Fecha**: 4 de febrero de 2026
**Objetivo**: Analizar las mejores prácticas para implementar detección de redundancia semántica de forma eficiente
**Estado**: Estudio completado - Pendiente de implementación

---

## 1. Resumen Ejecutivo

La detección de redundancia semántica busca identificar contenido que se repite conceptualmente aunque esté escrito con palabras diferentes. Este estudio analiza las opciones de implementación, trade-offs de rendimiento, y estrategias de optimización para reducir la complejidad computacional de O(n²) a complejidades sublineales.

### Conclusiones Principales

| Aspecto | Recomendación |
|---------|---------------|
| **Algoritmo base** | FAISS + Sentence Transformers |
| **Complejidad optimizada** | O(n log n) con índices ANN |
| **Umbral recomendado** | 0.80-0.85 (configurable) |
| **Chunking** | Nivel oración con agrupación semántica |
| **Modo default** | Deshabilitado (opt-in por usuario) |
| **Requisitos mínimos** | 4GB RAM, GPU opcional pero recomendada |

---

## 2. Análisis del Problema

### 2.1 Casos de Uso

1. **Reescritura involuntaria**: El autor escribió algo que ya estaba escrito antes pero con otras palabras
2. **Acciones repetidas**: Un personaje hace algo que ya había hecho antes (mismo evento, distinta narración)
3. **Insistencia temática excesiva**: Se repite el mismo tema demasiadas veces

### 2.2 Complejidad Naive

```
Comparar todas las oraciones entre sí:
- n oraciones → n(n-1)/2 comparaciones
- Documento de 10,000 oraciones → ~50 millones de comparaciones
- Tiempo estimado (CPU): 30-60 minutos
- Tiempo estimado (GPU): 2-5 minutos
```

### 2.3 Objetivo de Optimización

Reducir la complejidad de **O(n²)** a **O(n log n)** o mejor, manteniendo alta precisión.

---

## 3. Estrategias de Optimización

### 3.1 Approximate Nearest Neighbors (ANN)

En lugar de comparar todos los vectores uno a uno, los algoritmos ANN organizan los vectores en estructuras de datos que permiten búsquedas eficientes.

#### Comparativa de Algoritmos ANN

| Algoritmo | Complejidad Búsqueda | Memoria | Precisión | Mejor Para |
|-----------|---------------------|---------|-----------|------------|
| **FAISS IVF** | O(√n) | Media | Alta | Datasets medianos (100K-10M) |
| **FAISS HNSW** | O(log n) | Alta | Muy alta | Alta precisión requerida |
| **LSH (MinHash)** | O(1) amortizado | Baja | Media | Datasets muy grandes (>10M) |
| **ScaNN** | O(log n) | Media | Alta | Balance velocidad/precisión |

**Recomendación para Narrative Assistant**: FAISS con índice IVF (Inverted File) para balance óptimo.

### 3.2 Locality Sensitive Hashing (LSH)

LSH agrupa elementos similares en los mismos "buckets" con alta probabilidad, reduciendo drásticamente el espacio de búsqueda.

```python
# Pseudocódigo conceptual
class LSHIndex:
    def __init__(self, num_bands=20, rows_per_band=5):
        self.bands = num_bands
        self.rows = rows_per_band
        self.buckets = [defaultdict(list) for _ in range(num_bands)]

    def add(self, doc_id, minhash_signature):
        for band_idx in range(self.bands):
            start = band_idx * self.rows
            band_hash = hash(tuple(minhash_signature[start:start+self.rows]))
            self.buckets[band_idx][band_hash].append(doc_id)

    def query(self, minhash_signature):
        candidates = set()
        for band_idx in range(self.bands):
            start = band_idx * self.rows
            band_hash = hash(tuple(minhash_signature[start:start+self.rows]))
            candidates.update(self.buckets[band_idx][band_hash])
        return candidates
```

**Ventajas**:
- Muy eficiente en memoria (~11 GB para millones de documentos vs ~200 GB con MinHash tradicional)
- Escalable a datasets de billones de tokens
- Procesamiento incremental posible

**Desventajas**:
- Menor precisión que embeddings semánticos puros
- Requiere tuning de parámetros (bands, rows)

### 3.3 Enfoque Híbrido (Recomendado)

Combinar LSH para filtrado inicial + embeddings para verificación:

```
1. Fase 1 (Filtrado): LSH para identificar candidatos (~O(n))
2. Fase 2 (Verificación): Cosine similarity solo entre candidatos (~O(k²) donde k << n)
```

**Benchmarks de referencia**:
- SemHash: 1.8M textos en ~83 segundos (CPU)
- LSHBloom: 12× más rápido que MinHashLSH tradicional
- FAISS GPU: 75× más rápido que CPU (Tesla T4)

---

## 4. Estrategias de Chunking

### 4.1 Comparativa de Niveles

| Nivel | Pros | Contras | Uso Recomendado |
|-------|------|---------|-----------------|
| **Oración** | Alta granularidad, detecta duplicados exactos | Muchos chunks, más comparaciones | Detección de repeticiones textuales |
| **Párrafo** | Contexto más rico, menos chunks | Puede perder duplicados parciales | Detección de ideas repetidas |
| **Semántico** | Agrupa por significado | Computacionalmente costoso | Máxima calidad, menor volumen |

### 4.2 Chunking Semántico Adaptativo

```python
# Pseudocódigo para chunking semántico
def semantic_chunk(sentences, threshold=0.75):
    embeddings = model.encode(sentences)
    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = cosine_similarity(embeddings[i-1], embeddings[i])

        if similarity < threshold:  # Cambio de tema detectado
            chunks.append(current_chunk)
            current_chunk = []

        current_chunk.append(sentences[i])

    chunks.append(current_chunk)
    return chunks
```

**Recomendación**: Usar chunking a nivel de oración con post-agrupación semántica opcional.

---

## 5. Umbrales de Similitud

### 5.1 Rangos Recomendados

| Umbral | Comportamiento | Uso |
|--------|----------------|-----|
| **0.95+** | Solo casi-idénticos | Detección de copias exactas |
| **0.85-0.95** | Alta similitud | Balance recomendado |
| **0.75-0.85** | Similitud moderada | Detección agresiva |
| **<0.75** | Similitud baja | Muchos falsos positivos |

### 5.2 Calibración por Dominio

No existe un umbral universal. Se recomienda:

1. **Fase de calibración**: Muestra de 50-100 pares evaluados manualmente
2. **Métricas objetivo**: Maximizar F1-score en el conjunto de validación
3. **Umbrales diferenciados**: Diferentes umbrales para diferentes tipos de redundancia

```python
# Ejemplo de calibración automática
def find_optimal_threshold(pairs, labels, model):
    embeddings = model.encode([p[0] for p in pairs] + [p[1] for p in pairs])
    similarities = [cosine_similarity(e1, e2) for e1, e2 in ...]

    best_f1, best_threshold = 0, 0.8
    for threshold in np.arange(0.5, 0.99, 0.01):
        predictions = [1 if sim >= threshold else 0 for sim in similarities]
        f1 = f1_score(labels, predictions)
        if f1 > best_f1:
            best_f1, best_threshold = f1, threshold

    return best_threshold, best_f1
```

---

## 6. Arquitectura Propuesta

### 6.1 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DETECCIÓN DE REDUNDANCIA SEMÁNTICA               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Documento   │───▶│   Chunking   │───▶│  Embeddings  │          │
│  │   (texto)    │    │  (oraciones) │    │ (vectores)   │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                 │                   │
│                                                 ▼                   │
│                             ┌─────────────────────────────────┐     │
│                             │      FAISS Index (IVF)          │     │
│                             │   - Clustering automático       │     │
│                             │   - Búsqueda O(√n)              │     │
│                             └─────────────────────────────────┘     │
│                                                 │                   │
│                                                 ▼                   │
│                      ┌──────────────────────────────────────┐      │
│                      │     Candidatos (k vecinos cercanos)   │      │
│                      └──────────────────────────────────────┘      │
│                                                 │                   │
│                                                 ▼                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Filtrado   │◀───│   Cosine     │◀───│  Verificación│          │
│  │  (umbral)    │    │  Similarity  │    │   (pares)    │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              Reporte de Redundancias                      │      │
│  │  - Pares de oraciones/párrafos similares                  │      │
│  │  - Capítulos y posiciones                                 │      │
│  │  - Score de similitud                                     │      │
│  │  - Clasificación (textual / temática / acción)            │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Componentes

```python
# Estructura propuesta de clases

@dataclass
class SemanticDuplicate:
    """Par de textos semánticamente similares."""
    text1: str
    text2: str
    chapter1: int
    chapter2: int
    position1: int
    position2: int
    similarity: float
    duplicate_type: str  # "textual", "thematic", "action"

@dataclass
class RedundancyReport:
    """Reporte de redundancias detectadas."""
    duplicates: list[SemanticDuplicate]
    sentences_analyzed: int
    clusters_found: int
    processing_time_seconds: float

class SemanticRedundancyDetector:
    """Detector de redundancia semántica optimizado."""

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.85,
        index_type: str = "IVF",  # IVF, HNSW, Flat
        use_gpu: bool = True,
        min_sentence_length: int = 10,
    ):
        ...

    def build_index(self, sentences: list[str]) -> None:
        """Construye índice FAISS de embeddings."""
        ...

    def find_duplicates(
        self,
        chapters: list[dict],
        k_neighbors: int = 10,
    ) -> Result[RedundancyReport]:
        """Detecta duplicados semánticos en capítulos."""
        ...

    def detect_thematic_overemphasis(
        self,
        chapters: list[dict],
        theme_threshold: float = 0.7,
    ) -> list[ThematicCluster]:
        """Detecta temas repetidos excesivamente."""
        ...
```

---

## 7. Configuración de Usuario

### 7.1 Opciones Recomendadas

```typescript
// Settings del usuario
interface SemanticRedundancySettings {
  // Habilitación
  enabled: boolean;              // Default: false (opt-in)

  // Precisión vs Velocidad
  mode: "fast" | "balanced" | "thorough";  // Default: balanced

  // Umbrales
  similarityThreshold: number;   // Default: 0.85, Range: [0.70, 0.95]
  minSentenceLength: number;     // Default: 20 caracteres

  // Tipos de detección
  detectTextualDuplicates: boolean;    // Default: true
  detectThematicOveremphasis: boolean; // Default: true
  detectRepeatedActions: boolean;      // Default: false (más lento)

  // Rendimiento
  useGpu: boolean;               // Default: auto-detect
  maxSentencesPerAnalysis: number;  // Default: 10000
}
```

### 7.2 Modos de Operación

| Modo | Algoritmo | Tiempo (10K oraciones) | Precisión |
|------|-----------|------------------------|-----------|
| **Fast** | LSH + top-100 candidatos | ~5 seg | 85% |
| **Balanced** | FAISS IVF + top-500 | ~30 seg | 95% |
| **Thorough** | FAISS Flat (exhaustivo) | ~5 min | 99% |

---

## 8. Requisitos de Recursos

### 8.1 Memoria

| Componente | Memoria Estimada |
|------------|-----------------|
| Embeddings (10K oraciones × 384 dim) | ~15 MB |
| Índice FAISS IVF | ~20 MB |
| Modelo sentence-transformers | ~500 MB |
| **Total mínimo** | **~600 MB** |
| **Recomendado** | **2-4 GB** |

### 8.2 Tiempo de Procesamiento

| Documento | CPU (i7) | GPU (RTX 3060) |
|-----------|----------|----------------|
| 1,000 oraciones | 5 seg | <1 seg |
| 10,000 oraciones | 45 seg | 3 seg |
| 50,000 oraciones | 4 min | 15 seg |
| 100,000 oraciones | 15 min | 1 min |

### 8.3 Recomendación de Hardware

- **Mínimo**: CPU 4 cores, 4 GB RAM
- **Recomendado**: GPU con 4+ GB VRAM, 8 GB RAM
- **Óptimo**: GPU con 8+ GB VRAM, 16 GB RAM

---

## 9. Estrategia Incremental

Para documentos que se editan frecuentemente, mantener un índice persistente:

```python
class IncrementalRedundancyIndex:
    """Índice persistente para detección incremental."""

    def __init__(self, project_id: int):
        self.index_path = f"~/.narrative_assistant/indexes/{project_id}_semantic.faiss"
        self.metadata_path = f"~/.narrative_assistant/indexes/{project_id}_metadata.json"

    def add_sentences(self, new_sentences: list[str], chapter: int) -> list[SemanticDuplicate]:
        """
        Añade nuevas oraciones y detecta duplicados contra el índice existente.
        Solo compara nuevas vs existentes (no n² completo).
        """
        # 1. Generar embeddings de nuevas oraciones
        new_embeddings = self.model.encode(new_sentences)

        # 2. Buscar vecinos cercanos en índice existente
        distances, indices = self.index.search(new_embeddings, k=10)

        # 3. Filtrar por umbral
        duplicates = []
        for i, (dists, idxs) in enumerate(zip(distances, indices)):
            for dist, idx in zip(dists, idxs):
                if dist < self.threshold:
                    duplicates.append(...)

        # 4. Añadir nuevas oraciones al índice
        self.index.add(new_embeddings)

        return duplicates

    def rebuild_full(self, chapters: list[dict]) -> None:
        """Reconstruye índice completo (ejecutar ocasionalmente)."""
        ...
```

**Ventaja**: Análisis de nuevos capítulos en O(m × log n) donde m = oraciones nuevas, n = total.

---

## 10. Mitigación de Falsos Positivos

### 10.1 Estrategias

1. **Filtro de frases comunes**: Excluir frases muy frecuentes en español
   ```python
   COMMON_PHRASES = {
       "dijo que", "se levantó", "miró a", "pensó en",
       "al día siguiente", "en ese momento", ...
   }
   ```

2. **Filtro de diálogo**: Los diálogos cortos no deberían marcarse como duplicados
   ```python
   def is_dialogue(text: str) -> bool:
       return text.startswith("—") or text.startswith('"')
   ```

3. **Contexto de capítulo**: Duplicados en el mismo capítulo tienen diferente peso
   ```python
   if chapter1 == chapter2:
       score *= 0.8  # Menos relevante si es mismo capítulo
   ```

4. **Verificación semántica secundaria**: Usar LLM local para verificar casos borderline
   ```python
   if 0.80 <= similarity <= 0.90:
       # Verificar con Ollama
       is_truly_duplicate = verify_with_llm(text1, text2)
   ```

### 10.2 Categorización de Duplicados

| Categoría | Descripción | Umbral Sugerido |
|-----------|-------------|-----------------|
| **Exacto** | Mismo texto o muy similar | >0.95 |
| **Paráfrasis** | Misma idea, diferentes palabras | 0.85-0.95 |
| **Temático** | Mismo tema general | 0.75-0.85 |
| **Relacionado** | Conceptos relacionados | <0.75 (ignorar) |

---

## 11. Integración con Sistema Existente

### 11.1 Integración con AlertEngine

```python
# En AlertEngine
def create_from_semantic_duplicate(
    self,
    project_id: int,
    duplicate: SemanticDuplicate,
) -> Result[Alert]:
    """Crea alerta desde duplicado semántico."""
    return self.create_alert(
        project_id=project_id,
        category=AlertCategory.STRUCTURE,  # O nueva categoría REDUNDANCY
        severity=self._map_similarity_to_severity(duplicate.similarity),
        alert_type=f"semantic_{duplicate.duplicate_type}",
        title=self._get_duplicate_title(duplicate),
        description=f"Contenido similar encontrado en capítulos {duplicate.chapter1} y {duplicate.chapter2}",
        suggestion="Considerar eliminar o reformular uno de los pasajes",
        ...
    )
```

### 11.2 API Endpoints

```python
@router.get("/api/projects/{project_id}/semantic-redundancy")
async def detect_semantic_redundancy(
    project_id: str,
    mode: str = Query("balanced", enum=["fast", "balanced", "thorough"]),
    threshold: float = Query(0.85, ge=0.70, le=0.95),
    max_results: int = Query(50, ge=10, le=200),
    create_alerts: bool = Query(False),
) -> ApiResponse:
    """Detecta redundancia semántica en el proyecto."""
    ...

@router.get("/api/projects/{project_id}/semantic-redundancy/preview")
async def preview_redundancy_detection(
    project_id: str,
    chapter_number: int,
) -> ApiResponse:
    """Preview rápido para un capítulo específico."""
    ...
```

### 11.3 UI Propuesta

```
┌─────────────────────────────────────────────────────────────────┐
│  Redundancia Semántica                              [Analizar]  │
├─────────────────────────────────────────────────────────────────┤
│  ⚙️ Configuración                                               │
│  ├─ Modo: [Balanced ▼]                                         │
│  ├─ Umbral: [0.85 ────●────]                                   │
│  └─ Tipos: [✓] Textual  [✓] Temática  [ ] Acciones             │
├─────────────────────────────────────────────────────────────────┤
│  📊 Resultados (12 encontrados)                                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 92% similitud - Capítulos 3 y 7                         │   │
│  │ ────────────────────────────────────────────────────── │   │
│  │ Cap 3: "María observó el paisaje con melancolía,       │   │
│  │        recordando los días felices de su juventud."    │   │
│  │ Cap 7: "Con tristeza, María contempló el horizonte,    │   │
│  │        añorando los tiempos de su juventud feliz."     │   │
│  │ [Ir a Cap 3] [Ir a Cap 7] [Ignorar]                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Plan de Implementación Sugerido

### Fase 1: Core (1-2 semanas)
- [ ] `SemanticRedundancyDetector` con FAISS
- [ ] Tests unitarios
- [ ] Integración con embeddings existentes

### Fase 2: Optimización (1 semana)
- [ ] Índice incremental
- [ ] Filtros de falsos positivos
- [ ] Calibración de umbrales

### Fase 3: Integración (1 semana)
- [ ] Endpoint API
- [ ] Integración con AlertEngine
- [ ] Configuración en Settings

### Fase 4: UI (1 semana)
- [ ] Tab o panel en workspace
- [ ] Visualización de resultados
- [ ] Navegación a pasajes

---

## 13. Fuentes y Referencias

### Artículos y Documentación

- [Billion-scale semantic similarity search with FAISS+SBERT](https://towardsdatascience.com/billion-scale-semantic-similarity-search-with-faiss-sbert-c845614962e2/)
- [Master Semantic Search at Scale](https://towardsdatascience.com/master-semantic-search-at-scale-index-millions-of-documents-with-lightning-fast-inference-times-fa395e4efd88/)
- [Semantic search with FAISS - Hugging Face](https://huggingface.co/learn/llm-course/en/chapter5/6)
- [SemDeDup: Data-efficient learning through semantic deduplication](https://arxiv.org/abs/2303.09540)
- [Large-scale Near-deduplication Behind BigCode](https://huggingface.co/blog/dedup)

### Herramientas y Librerías

- [FAISS - Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://sbert.net/)
- [SemHash - Fast Multimodal Semantic Deduplication](https://github.com/MinishLab/semhash)
- [Datasketch - Probabilistic Data Structures](https://github.com/ekzhu/datasketch)
- [NVIDIA NeMo Curator - Semantic Deduplication](https://docs.nvidia.com/nemo-framework/user-guide/24.09/datacuration/semdedup.html)

### Chunking y Optimización

- [Chunking Strategies for LLM Applications - Pinecone](https://www.pinecone.io/learn/chunking-strategies/)
- [Semantic Chunking for RAG](https://medium.com/the-ai-forum/semantic-chunking-for-rag-f4733025d5f5)
- [How to split text based on semantic similarity - LangChain](https://python.langchain.com/docs/how_to/semantic-chunker/)

### Umbrales y Calibración

- [How do you tune similarity thresholds to reduce false positives?](https://milvus.io/ai-quick-reference/how-do-you-tune-similarity-thresholds-to-reduce-false-positives)
- [Sentence Transformers Evaluation](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html)

### LSH y Algoritmos ANN

- [Locality-sensitive hashing - Wikipedia](https://en.wikipedia.org/wiki/Locality-sensitive_hashing)
- [Near-duplicate Detection with LSH and Datasketch](https://yorko.github.io/2023/practical-near-dup-detection/)
- [MinHash LSH in Milvus](https://milvus.io/blog/minhash-lsh-in-milvus-the-secret-weapon-for-fighting-duplicates-in-llm-training-data.md)

---

## 14. Conclusiones

### Viabilidad: ✅ Alta

La detección de redundancia semántica es técnicamente viable con las herramientas actuales. Las optimizaciones con FAISS + ANN reducen la complejidad de O(n²) a O(n log n), haciéndolo práctico para documentos de hasta ~100K oraciones.

### Recomendaciones Clave

1. **Implementar como opt-in**: Deshabilitado por defecto debido al costo computacional
2. **Usar enfoque híbrido**: FAISS IVF para balance velocidad/precisión
3. **Ofrecer modos**: Fast/Balanced/Thorough para diferentes necesidades
4. **Calibrar umbrales**: 0.85 como default, configurable por usuario
5. **Filtrar falsos positivos**: Excluir diálogos cortos y frases comunes
6. **Índice incremental**: Para análisis eficiente de cambios

### Siguiente Paso

Cuando se decida implementar, comenzar por la Fase 1 (Core) con un prototipo simple que use FAISS Flat para validar el concepto antes de optimizar.
