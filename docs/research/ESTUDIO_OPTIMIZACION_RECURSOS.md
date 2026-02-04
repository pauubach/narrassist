# Estudio: Optimizacion de Recursos para Aplicaciones NLP

**Fecha**: 4 de febrero de 2026
**Objetivo**: Documentar mejores practicas de optimizacion de recursos para aplicaciones NLP que deben ejecutarse en configuraciones de hardware diversas
**Estado**: Estudio completado - Implementacion parcial en ResourceManager

---

## Resumen Ejecutivo

Este estudio analiza las mejores practicas para la gestion adaptativa de recursos en aplicaciones NLP de escritorio, con enfasis especial en escenarios donde los usuarios tienen hardware muy variado: desde laptops con 4GB de RAM hasta workstations con 32GB+ y GPUs dedicadas.

### Conclusiones Principales

| Aspecto | Recomendacion |
|---------|---------------|
| **Deteccion de hardware** | psutil para CPU/RAM, PyTorch para GPU |
| **Clasificacion de sistemas** | 3 tiers: LOW, MEDIUM, HIGH |
| **Batch sizes** | Adaptativos segun VRAM y RAM disponible |
| **Tareas pesadas** | Semaforo con limite de concurrencia |
| **Fallback GPU->CPU** | Automatico con reduccion de batch |
| **Monitorizacion** | Por fases con umbrales de warning |

---

## 1. Gestion Adaptativa de Recursos

### 1.1 Deteccion de Capacidades del Sistema

La deteccion precisa de las capacidades del sistema es el primer paso para una gestion efectiva de recursos.

#### CPU Detection

```python
import os
import platform

# Cores logicos (threads)
cpu_cores_logical = os.cpu_count() or 1

# Cores fisicos (mas preciso con psutil)
try:
    import psutil
    cpu_cores_physical = psutil.cpu_count(logical=False) or 1
except ImportError:
    # Fallback: asumir hyperthreading
    cpu_cores_physical = max(1, cpu_cores_logical // 2)

# Carga actual
cpu_percent = psutil.cpu_percent(interval=0.1)
```

**Mejores Practicas**:
- Siempre tener fallbacks cuando las bibliotecas no estan disponibles
- Usar cores fisicos para calcular workers (evita oversubscription con HT)
- Monitorear carga antes de lanzar tareas pesadas

#### RAM Detection

```python
# Con psutil (recomendado)
import psutil
mem = psutil.virtual_memory()
ram_total_mb = mem.total // (1024 * 1024)
ram_available_mb = mem.available // (1024 * 1024)
ram_percent_used = mem.percent

# Fallback Linux (sin psutil)
def estimate_ram_linux():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024  # MB
    except:
        pass
    return 4096  # Default conservador
```

**Mejores Practicas**:
- Usar `available` en lugar de `free` (incluye cache liberable)
- Dejar margen de seguridad (15-20% de RAM para sistema)
- Monitorear periodicamente durante operaciones largas

#### GPU/VRAM Detection

```python
import torch

def detect_gpu():
    """Detecta GPU y VRAM disponible."""
    if torch.cuda.is_available():
        device = torch.cuda.current_device()
        name = torch.cuda.get_device_name(device)
        props = torch.cuda.get_device_properties(device)
        vram_total_mb = props.total_memory // (1024 * 1024)

        # VRAM libre actual
        free_mem = torch.cuda.mem_get_info()[0]
        vram_available_mb = free_mem // (1024 * 1024)

        return {
            "available": True,
            "name": name,
            "vram_total_mb": vram_total_mb,
            "vram_available_mb": vram_available_mb,
            "is_low_vram": vram_total_mb < 6144  # <6GB
        }

    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon - memoria unificada
        return {
            "available": True,
            "name": "Apple Silicon (MPS)",
            "vram_total_mb": None,  # Compartida
            "vram_available_mb": None,
            "is_low_vram": False  # MPS maneja dinamicamente
        }

    return {"available": False}
```

**Mejores Practicas**:
- Considerar VRAM < 6GB como "low VRAM"
- MPS (Apple Silicon) usa memoria unificada, diferente modelo
- Verificar VRAM libre, no solo total (otros procesos pueden usarla)

### 1.2 Clasificacion por Tiers

```python
class ResourceTier(Enum):
    LOW = "low"       # <4 cores, <8GB RAM, no GPU
    MEDIUM = "medium" # 4-8 cores, 8-16GB RAM, GPU opcional
    HIGH = "high"     # >8 cores, >16GB RAM, GPU >6GB VRAM

def classify_system(caps):
    """Clasifica el sistema segun capacidades."""
    # HIGH: workstation con GPU potente
    if (caps.cpu_cores_physical >= 8 and
        caps.ram_total_mb >= 16384 and
        caps.gpu_available and not caps.gpu_is_low_vram):
        return ResourceTier.HIGH

    # MEDIUM: laptop/desktop decente
    if caps.cpu_cores_physical >= 4 and caps.ram_total_mb >= 8192:
        return ResourceTier.MEDIUM

    # LOW: hardware limitado
    return ResourceTier.LOW
```

### 1.3 Adaptacion de Parametros

#### Batch Sizes Adaptativos

```python
@dataclass
class ResourceRecommendation:
    """Recomendaciones basadas en tier."""
    max_workers: int = 2
    batch_size_embeddings: int = 16
    batch_size_nlp: int = 100
    use_gpu_for_embeddings: bool = False
    use_gpu_for_spacy: bool = False
    max_concurrent_heavy_tasks: int = 1
    document_chunk_size: int = 50000

def generate_recommendation(caps):
    rec = ResourceRecommendation()

    # Workers: min(cores-1, RAM/2GB)
    cores_based = max(1, caps.cpu_cores_physical - 1)
    ram_based = max(1, caps.ram_available_mb // 2048)
    rec.max_workers = min(cores_based, ram_based, 8)

    # Batch sizes segun GPU
    if caps.gpu_available and not caps.gpu_is_low_vram:
        rec.batch_size_embeddings = 64
        rec.use_gpu_for_embeddings = True
    elif caps.gpu_available:
        # Low VRAM: CPU para embeddings, GPU para spaCy
        rec.batch_size_embeddings = 32
        rec.use_gpu_for_spacy = True
    else:
        rec.batch_size_embeddings = 16

    # Chunking basado en RAM
    if caps.ram_available_mb < 4096:
        rec.document_chunk_size = 30000
    elif caps.ram_available_mb < 8192:
        rec.document_chunk_size = 50000
    else:
        rec.document_chunk_size = 100000

    return rec
```

#### Ajuste Dinamico de Batch Size segun VRAM

```python
def get_safe_batch_size(default, device_info):
    """Ajusta batch size segun VRAM disponible."""
    if device_info.device_type == DeviceType.CPU:
        return default

    if device_info.memory_gb:
        if device_info.memory_gb < 4:
            return max(4, default // 8)   # VRAM muy limitada
        elif device_info.memory_gb < 6:
            return max(8, default // 4)   # VRAM baja
        elif device_info.memory_gb < 8:
            return max(16, default // 2)  # VRAM media

    return default
```

### 1.4 Cuando Deshabilitar vs Degradar

| Escenario | Estrategia |
|-----------|------------|
| GPU OOM | Fallback a CPU con batch reducido |
| RAM > 85% | Reducir workers, deshabilitar features opcionales |
| CPU > 80% | Esperar antes de lanzar nuevas tareas |
| VRAM < 4GB | Forzar CPU para embeddings |
| Sin psutil | Usar defaults conservadores |

**Principio**: Degradar gracefully antes de fallar. Solo deshabilitar features cuando no hay alternativa viable.

---

## 2. Gestion de Memoria para Aplicaciones NLP

### 2.1 Matrices de Embeddings

Las matrices de embeddings son el principal consumidor de memoria en aplicaciones NLP.

#### Estimacion de Memoria

```python
def estimate_embedding_memory(n_vectors, dim=384, dtype='float32'):
    """Estima memoria para matriz de embeddings."""
    bytes_per_float = {'float32': 4, 'float16': 2, 'int8': 1}
    bytes_needed = n_vectors * dim * bytes_per_float[dtype]
    return bytes_needed / (1024 ** 3)  # GB

# Ejemplo: 100K oraciones con embeddings de 384 dimensiones
# = 100,000 * 384 * 4 bytes = ~147 MB
```

#### Estrategias de Reduccion de Memoria

1. **Precision reducida (float16)**
```python
embeddings = model.encode(texts, convert_to_numpy=True)
embeddings_fp16 = embeddings.astype(np.float16)  # 50% menos memoria
```

2. **Procesamiento por chunks**
```python
def encode_in_chunks(model, texts, chunk_size=1000):
    """Procesa embeddings en chunks para evitar OOM."""
    all_embeddings = []
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        emb = model.encode(chunk)
        all_embeddings.append(emb)

        # Liberar memoria entre chunks si es necesario
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return np.vstack(all_embeddings)
```

3. **Memory mapping para indices grandes**
```python
# FAISS con memory mapping
index = faiss.read_index("index.faiss", faiss.IO_FLAG_MMAP)
# El indice se lee bajo demanda del disco
```

### 2.2 Estrategias FAISS para Diferentes Restricciones

#### FAISS Index Selection

| Memoria Disponible | Index Recomendado | Precision | Velocidad |
|-------------------|-------------------|-----------|-----------|
| < 2GB | IndexIVFPQ (quantizado) | Media | Alta |
| 2-8GB | IndexIVFFlat | Alta | Media |
| > 8GB | IndexFlatIP (exacto) | Perfecta | Media-Baja |
| Cualquier + GPU | GpuIndexIVFFlat | Alta | Muy Alta |

#### Implementacion Adaptativa

```python
def create_faiss_index(embeddings, memory_budget_gb=4):
    """Crea indice FAISS adaptado a memoria disponible."""
    n_vectors, dim = embeddings.shape
    faiss.normalize_L2(embeddings)  # Para similitud coseno

    # Estimar memoria del indice exacto
    exact_memory_gb = (n_vectors * dim * 4) / (1024**3)

    if exact_memory_gb < memory_budget_gb * 0.5:
        # Suficiente memoria: indice exacto
        index = faiss.IndexFlatIP(dim)
    else:
        # Memoria limitada: indice IVF
        nlist = min(100, n_vectors // 100)
        nlist = max(nlist, 1)
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(
            quantizer, dim, nlist,
            faiss.METRIC_INNER_PRODUCT
        )
        index.train(embeddings)

    index.add(embeddings)
    return index
```

### 2.3 Patrones de Carga de Modelos

#### Lazy Loading

```python
class LazyEmbeddingsModel:
    """Carga el modelo solo cuando se necesita."""

    def __init__(self, model_name):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts, **kwargs):
        return self.model.encode(texts, **kwargs)
```

#### Singleton Thread-Safe con Double-Checked Locking

```python
import threading

_lock = threading.Lock()
_instance = None

def get_model():
    """Obtiene modelo singleton (thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:  # Double-check
                _instance = load_model()
    return _instance
```

#### Descarga de Memoria Agresiva

```python
import gc
import torch

def clear_gpu_memory():
    """Libera memoria GPU agresivamente."""
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
```

### 2.4 Quantizacion de Modelos

```python
# Quantizacion dinamica (CPU)
import torch
model_quantized = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},
    dtype=torch.qint8
)

# Resultado: ~75% menos memoria, ~2x mas rapido en CPU
```

---

## 3. Scheduling de Tareas Concurrentes

### 3.1 Prevencion de Picos de Memoria

El problema principal al ejecutar multiples tareas NLP es la acumulacion de memoria.

#### Semaforo para Tareas Pesadas

```python
class HeavyTaskSemaphore:
    """
    Semaforo para controlar tareas pesadas concurrentes.
    Evita que multiples analisis consuman toda la memoria.
    """

    HEAVY_TASKS = {
        "semantic_redundancy",
        "embeddings_full",
        "coreference_resolution",
        "llm_analysis",
        "spacy_full_pipeline",
    }

    def __init__(self, max_concurrent=1):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_tasks = []
        self._lock = threading.Lock()

    def acquire(self, task_name, timeout=None):
        """Intenta adquirir slot para tarea pesada."""
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active_tasks.append(task_name)
        return acquired

    def release(self, task_name):
        """Libera slot despues de completar tarea."""
        with self._lock:
            if task_name in self._active_tasks:
                self._active_tasks.remove(task_name)
        self._semaphore.release()

    def run_heavy_task(self, task_name, func, *args, timeout=30, **kwargs):
        """Ejecuta tarea pesada con control de recursos."""
        if task_name not in self.HEAVY_TASKS:
            return func(*args, **kwargs)

        if not self.acquire(task_name, timeout=timeout):
            raise TimeoutError(
                f"No se pudieron adquirir recursos para '{task_name}'. "
                f"Tareas activas: {self._active_tasks}"
            )
        try:
            return func(*args, **kwargs)
        finally:
            self.release(task_name)
```

### 3.2 Prioridades de Tareas

```python
class TaskPriority(Enum):
    """Prioridades para scheduling."""
    CRITICAL = 1   # NER, parsing basico (rapido, necesario)
    HIGH = 2       # Correferencias, embeddings
    NORMAL = 3     # Analisis de calidad
    LOW = 4        # Redundancia semantica, exportaciones

# Uso con cola de prioridad
import heapq

class PriorityTaskQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    def push(self, priority, task):
        heapq.heappush(self._queue, (priority.value, self._counter, task))
        self._counter += 1

    def pop(self):
        _, _, task = heapq.heappop(self._queue)
        return task
```

### 3.3 Backpressure y Rate Limiting

```python
class AdaptiveRateLimiter:
    """Ajusta tasa de tareas segun presion del sistema."""

    def __init__(self, base_delay=0.1, max_delay=5.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay

    def wait(self):
        """Espera adaptativa basada en recursos."""
        import psutil

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        # Incrementar delay si hay presion
        if cpu > 80 or mem > 85:
            self.current_delay = min(self.current_delay * 2, self.max_delay)
        else:
            self.current_delay = max(self.current_delay * 0.9, self.base_delay)

        time.sleep(self.current_delay)

    def is_system_under_pressure(self):
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return cpu > 80 or mem.percent > 85
```

---

## 4. Optimizacion de Recursos GPU

### 4.1 Deteccion de Escenarios Low VRAM

```python
MIN_SAFE_VRAM_GB = 6.0

def is_low_vram(device_info):
    """Detecta si la GPU tiene VRAM limitada."""
    if device_info.device_type == DeviceType.CPU:
        return False
    if device_info.memory_gb is None:
        return True  # Asumir low si no podemos detectar
    return device_info.memory_gb < MIN_SAFE_VRAM_GB

def get_gpu_memory_usage():
    """Obtiene uso actual de VRAM."""
    if torch.cuda.is_available():
        device = torch.cuda.current_device()
        used = torch.cuda.memory_allocated(device) / (1024**3)
        total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
        return (used, total)
    return None

def is_gpu_memory_low(threshold=0.85):
    """Verifica si VRAM esta cerca del limite."""
    usage = get_gpu_memory_usage()
    if usage is None:
        return False
    used, total = usage
    return (used / total) > threshold
```

### 4.2 Fallback Automatico GPU -> CPU

```python
def encode_with_fallback(model, texts, batch_size=64):
    """Encoding con fallback automatico a CPU si hay OOM."""
    try:
        return model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
        )
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            logger.warning("GPU OOM - fallback a CPU")

            # Limpiar memoria GPU
            torch.cuda.empty_cache()
            gc.collect()

            # Reintentar en CPU con batch reducido
            return model.encode(
                texts,
                batch_size=max(4, batch_size // 4),
                convert_to_numpy=True,
                device="cpu",
            )
        raise
```

### 4.3 Estrategia de Particion de Carga GPU/CPU

En sistemas con VRAM limitada (< 6GB), donde Ollama y otros procesos compiten por GPU:

```python
class HybridComputeStrategy:
    """Distribuye carga entre GPU y CPU segun disponibilidad."""

    def __init__(self, device_info):
        self.has_gpu = device_info.gpu_available
        self.is_low_vram = device_info.is_low_vram

    def get_strategy(self):
        if not self.has_gpu:
            return {"spacy": "cpu", "embeddings": "cpu", "llm": "cpu"}

        if self.is_low_vram:
            # GPU para una cosa, CPU para el resto
            # Ollama tiene prioridad en GPU
            return {
                "spacy": "cpu",       # spaCy en CPU
                "embeddings": "cpu",  # Embeddings en CPU
                "llm": "gpu",         # Ollama en GPU
            }

        # GPU suficiente para todo
        return {"spacy": "gpu", "embeddings": "gpu", "llm": "gpu"}
```

### 4.4 Mixed Precision y Optimizaciones

```python
# Activar mixed precision para PyTorch
with torch.cuda.amp.autocast():
    embeddings = model.encode(texts)

# Gradient checkpointing (reduce memoria, aumenta tiempo)
model.gradient_checkpointing_enable()

# TF32 en Ampere GPUs (mas rapido sin perdida significativa)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

---

## 5. Monitorizacion y Benchmarking

### 5.1 Metricas Clave

| Metrica | Descripcion | Umbral Warning |
|---------|-------------|----------------|
| RSS Memory | Memoria residente del proceso | > 2GB |
| Peak Memory | Pico de memoria durante operacion | > 80% RAM |
| GPU VRAM Used | VRAM utilizada | > 85% |
| Phase Delta | Incremento de memoria por fase | > 500MB |
| Processing Time | Tiempo por fase | Variable |

### 5.2 Monitor de Memoria por Fases

```python
@dataclass
class MemorySnapshot:
    """Snapshot de memoria en un punto."""
    phase_name: str
    timestamp: datetime
    memory_mb: float
    delta_mb: float = 0.0
    label: str = ""  # "start" o "end"

class MemoryMonitor:
    """Monitor de memoria para pipeline."""

    def __init__(self, warning_threshold_mb=2048):
        self.warning_threshold = warning_threshold_mb
        self.snapshots = []
        self.peak_mb = 0.0
        self.warnings = 0

    @contextmanager
    def track_phase(self, phase_name):
        """Context manager para medir memoria de una fase."""
        start = self._snapshot(phase_name, "start")
        try:
            yield
        finally:
            end = self._snapshot(phase_name, "end")
            if start and end:
                delta = end.memory_mb - start.memory_mb
                logger.debug(
                    f"Phase '{phase_name}': "
                    f"{start.memory_mb:.0f} -> {end.memory_mb:.0f} MB "
                    f"(delta: {delta:+.1f} MB)"
                )

    def _snapshot(self, phase, label):
        mem = get_process_memory_mb()
        if mem < 0:
            return None

        snap = MemorySnapshot(
            phase_name=phase,
            timestamp=datetime.now(),
            memory_mb=mem,
            label=label,
        )

        # Actualizar peak
        if mem > self.peak_mb:
            self.peak_mb = mem

        # Warning si excede umbral
        if mem > self.warning_threshold:
            self.warnings += 1
            logger.warning(
                f"Memory {mem:.0f} MB > {self.warning_threshold} MB "
                f"(phase: {phase})"
            )

        self.snapshots.append(snap)
        return snap
```

### 5.3 Profiling de Memoria

```python
# Con memory_profiler (linea por linea)
from memory_profiler import profile

@profile
def process_document(doc):
    # ... codigo ...
    pass

# Con tracemalloc (snapshots)
import tracemalloc

tracemalloc.start()
# ... codigo ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

### 5.4 Escenarios de Test Recomendados

#### Tier LOW (4GB RAM, 2 cores, sin GPU)

```python
test_scenarios_low = [
    {"name": "small_doc", "chars": 10_000, "expected_time": "<5s"},
    {"name": "medium_doc", "chars": 50_000, "expected_time": "<30s"},
    {"name": "large_doc", "chars": 200_000, "expected_time": "<2min"},
]
```

#### Tier MEDIUM (8GB RAM, 4 cores, GPU 4GB)

```python
test_scenarios_medium = [
    {"name": "small_doc", "chars": 10_000, "expected_time": "<2s"},
    {"name": "medium_doc", "chars": 50_000, "expected_time": "<15s"},
    {"name": "large_doc", "chars": 500_000, "expected_time": "<1min"},
    {"name": "semantic_redundancy", "sentences": 5000, "expected_time": "<30s"},
]
```

#### Tier HIGH (16GB+ RAM, 8+ cores, GPU 8GB+)

```python
test_scenarios_high = [
    {"name": "small_doc", "chars": 10_000, "expected_time": "<1s"},
    {"name": "medium_doc", "chars": 50_000, "expected_time": "<5s"},
    {"name": "large_doc", "chars": 1_000_000, "expected_time": "<30s"},
    {"name": "semantic_redundancy", "sentences": 20000, "expected_time": "<1min"},
    {"name": "concurrent_analysis", "docs": 3, "expected_time": "<2min"},
]
```

### 5.5 Benchmark Suite Automatizada

```python
class ResourceBenchmark:
    """Suite de benchmarks para validar rendimiento."""

    def __init__(self, resource_manager):
        self.rm = resource_manager
        self.results = []

    def run_all(self):
        """Ejecuta todos los benchmarks."""
        tier = self.rm.capabilities.tier

        # Seleccionar escenarios segun tier
        scenarios = self._get_scenarios_for_tier(tier)

        for scenario in scenarios:
            result = self._run_scenario(scenario)
            self.results.append(result)

        return self.results

    def _run_scenario(self, scenario):
        """Ejecuta un escenario y mide recursos."""
        import time

        monitor = MemoryMonitor()
        start_time = time.time()

        with monitor.track_phase(scenario["name"]):
            # Ejecutar operacion
            self._execute(scenario)

        elapsed = time.time() - start_time

        return {
            "name": scenario["name"],
            "elapsed_seconds": elapsed,
            "peak_memory_mb": monitor.peak_mb,
            "passed": elapsed < scenario.get("max_time", float("inf")),
        }
```

---

## 6. Implementacion en Narrative Assistant

### 6.1 Componentes Implementados

| Componente | Archivo | Estado |
|------------|---------|--------|
| ResourceManager | `core/resource_manager.py` | Implementado |
| HeavyTaskSemaphore | `core/resource_manager.py` | Implementado |
| MemoryMonitor | `core/memory_monitor.py` | Implementado |
| DeviceDetector | `core/device.py` | Implementado |
| GPU Memory Utils | `core/device.py` | Implementado |
| Embeddings Fallback | `nlp/embeddings.py` | Implementado |
| FAISS Integration | `analysis/semantic_redundancy.py` | Implementado |

### 6.2 Uso del ResourceManager

```python
from narrative_assistant.core import get_resource_manager

# Obtener recomendaciones
rm = get_resource_manager()
rec = rm.recommendation

# Configurar batch size
model = EmbeddingsModel(batch_size=rec.batch_size_embeddings)

# Ejecutar tarea pesada con control
result = rm.run_heavy_task(
    "semantic_redundancy",
    detector.detect,
    chapters,
    timeout=30
)

# Verificar estado
status = rm.get_status()
print(f"Tier: {status['capabilities']['tier']}")
print(f"Workers disponibles: {status['current_state']['available_workers']}")
```

### 6.3 Integracion con Pipeline

```python
from narrative_assistant.core.memory_monitor import MemoryMonitor

def analyze_document(doc_path):
    rm = get_resource_manager()
    monitor = MemoryMonitor(warning_threshold_mb=2048)

    with monitor.track_phase("parsing"):
        doc = parse_document(doc_path)

    with monitor.track_phase("ner"):
        entities = extract_entities(
            doc.text,
            batch_size=rm.recommendation.batch_size_nlp
        )

    with monitor.track_phase("embeddings"):
        if rm.recommendation.enable_semantic_redundancy:
            rm.run_heavy_task(
                "embeddings_full",
                generate_embeddings,
                doc.sentences
            )

    # Reporte final
    report = monitor.get_report()
    logger.info(report.summary())
```

---

## 7. Recomendaciones Futuras


### 7.1 Mejoras de Corto Plazo

1. **Streaming de resultados**: Procesar y devolver resultados incrementalmente
2. **Cache de embeddings**: Persistir embeddings entre sesiones
3. **Prefetch inteligente**: Cargar modelos anticipadamente basado en patrones de uso

### 7.2 Mejoras de Medio Plazo

1. **Quantizacion automatica**: Detectar cuando usar modelos quantizados
2. **Offloading a disco**: Para indices FAISS muy grandes
3. **Pool de modelos**: Mantener multiples modelos en memoria segun uso

### 7.3 Investigacion

1. **ONNX Runtime**: Evaluar para inferencia mas eficiente
2. **Model pruning**: Reducir tamano de modelos sin perdida significativa
3. **Distilacion**: Usar modelos mas pequenos entrenados con knowledge distillation

---

## Referencias

### Bibliotecas y Documentacion

- [PyTorch Memory Management](https://pytorch.org/docs/stable/notes/cuda.html#memory-management)
- [FAISS Wiki](https://github.com/facebookresearch/faiss/wiki)
- [sentence-transformers](https://www.sbert.net/docs/package_reference/SentenceTransformer.html)
- [psutil Documentation](https://psutil.readthedocs.io/)

### Papers y Estudios

- "Efficient Transformers: A Survey" (Tay et al., 2020)
- "Billion-scale similarity search with GPUs" (Johnson et al., 2017) - FAISS
- "Product Quantization for Nearest Neighbor Search" (Jegou et al., 2011)

### Recursos Adicionales

- [Memory-efficient PyTorch](https://huggingface.co/docs/transformers/perf_train_gpu_one)
- [NVIDIA Mixed Precision Training](https://developer.nvidia.com/automatic-mixed-precision)
- [Ollama Resource Management](https://github.com/ollama/ollama/blob/main/docs/faq.md)

---

*Documento generado como parte del TFM - Narrative Assistant*
*Ultima actualizacion: 4 de febrero de 2026*
