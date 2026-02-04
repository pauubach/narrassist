# Estado de Optimización de Recursos - Narrative Assistant

**Fecha de revisión**: 4 de febrero de 2026
**Documento base**: [docs/research/ESTUDIO_OPTIMIZACION_RECURSOS.md](research/ESTUDIO_OPTIMIZACION_RECURSOS.md)

---

## Resumen

Este documento compara las recomendaciones del estudio de optimización con el estado actual de implementación y prioriza las mejoras pendientes.

---

## Estado de Implementación

### Implementado (✅)

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| ResourceManager | `core/resource_manager.py` | Gestión centralizada de recursos |
| SystemCapabilities | `core/resource_manager.py` | Detección de CPU, RAM, GPU |
| ResourceTier | `core/resource_manager.py` | Clasificación LOW/MEDIUM/HIGH |
| ResourceRecommendation | `core/resource_manager.py` | Parámetros adaptativos |
| HeavyTaskSemaphore | `core/resource_manager.py` | Control de tareas pesadas concurrentes |
| MemoryMonitor | `core/memory_monitor.py` | Monitoreo de memoria por fases |
| get_process_memory_mb() | `core/memory_monitor.py` | Medición RSS con fallbacks |
| GPU Detection | `core/device.py` | CUDA y MPS |
| Batch Size Adaptativo | `core/resource_manager.py` | Ajuste según VRAM/RAM |
| FAISS Integration | `analysis/semantic_redundancy.py` | Búsqueda ANN eficiente |
| Embeddings Fallback | `nlp/embeddings.py` | GPU→CPU automático |
| System Pressure Detection | `core/resource_manager.py` | CPU >80% o RAM >85% |

### Parcialmente Implementado (⚠️)

| Componente | Estado | Pendiente |
|------------|--------|-----------|
| TaskPriority | Enum definido | Falta cola de prioridad funcional |
| GPU Memory Tracking | En detección | Falta monitoreo durante operaciones |
| Chunking de Documentos | Parámetro existe | Falta integración en pipeline |

### No Implementado (❌)

| Componente | Prioridad | Descripción |
|------------|-----------|-------------|
| AdaptiveRateLimiter | MEDIA | Backpressure basado en carga del sistema |
| PriorityTaskQueue | BAJA | Scheduling con prioridades |
| Cache de Embeddings | ALTA | Persistir embeddings entre sesiones |
| Streaming de Resultados | BAJA | Devolver resultados incrementalmente |
| Model Prefetch | BAJA | Carga anticipada de modelos |
| ONNX Runtime | INVESTIGAR | Inferencia más eficiente |
| Model Quantization | BAJA | Detección automática de cuándo usar |

---

## Plan de Mejoras Prioritarias

### Prioridad Alta

#### 1. Cache de Embeddings (Persistencia)

**Problema**: Cada vez que se abre un proyecto, se regeneran todos los embeddings.

**Solución propuesta**:
```python
# En analysis/semantic_redundancy.py o nuevo archivo
class EmbeddingsCache:
    """Cache persistente de embeddings por proyecto."""

    def __init__(self, project_id: int, cache_dir: Path):
        self.cache_file = cache_dir / f"embeddings_{project_id}.npz"
        self.metadata_file = cache_dir / f"embeddings_{project_id}.json"

    def get_or_compute(self, sentences: list[str], model) -> np.ndarray:
        # Verificar hash de sentences
        # Si coincide, cargar de cache
        # Si no, computar y guardar
        pass
```

**Beneficio**: Reduce tiempo de análisis repetido de ~30s a ~1s.

**Archivos a modificar**:
- `analysis/semantic_redundancy.py`
- Nuevo: `core/embeddings_cache.py`

---

### Prioridad Media

#### 2. AdaptiveRateLimiter

**Problema**: Cuando el sistema está bajo presión, las tareas se encolan sin control.

**Solución propuesta**:
```python
class AdaptiveRateLimiter:
    """Ajusta tasa de tareas según presión del sistema."""

    def wait_if_needed(self):
        if self.is_system_under_pressure():
            self.delay = min(self.delay * 2, self.max_delay)
        else:
            self.delay = max(self.delay * 0.9, self.base_delay)
        time.sleep(self.delay)
```

**Beneficio**: Evita sobrecarga del sistema durante análisis concurrentes.

**Archivos a modificar**:
- `core/resource_manager.py`

#### 3. Chunking en Pipeline

**Problema**: El parámetro `document_chunk_size` existe pero no se usa.

**Solución propuesta**: Integrar chunking en el pipeline principal.

**Archivos a modificar**:
- `nlp/pipeline.py`
- `api-server/routers/analysis.py`

---

### Prioridad Baja (Backlog)

#### 4. PriorityTaskQueue
- Implementar cola de prioridad real con heapq
- Útil cuando hay muchos análisis en paralelo

#### 5. Streaming de Resultados
- WebSocket o SSE para reportar progreso
- Útil para documentos muy grandes

#### 6. Model Prefetch
- Cargar modelos anticipadamente al abrir proyecto
- Reduce latencia percibida

#### 7. ONNX Runtime
- Evaluar para sentence-transformers
- Potencial mejora de 2-3x en inferencia

---

## Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tiempo análisis 50K palabras | ~30s | <20s |
| Memoria pico 50K palabras | ~1.5GB | <1GB |
| Tiempo re-análisis (con cache) | ~30s | <5s |
| Concurrencia de usuarios | 1 | 3+ |

---

## Próximos Pasos

1. **Inmediato**:
   - Los tests de performance están creados
   - Ejecutar benchmarks iniciales para baseline

2. **Corto plazo** (1-2 semanas):
   - Implementar cache de embeddings
   - Integrar chunking en pipeline

3. **Medio plazo** (1 mes):
   - AdaptiveRateLimiter
   - Evaluar ONNX Runtime

---

## Comandos Útiles

```bash
# Ejecutar tests de performance
pytest tests/performance/ -v -m slow --tb=short

# Solo semantic redundancy
pytest tests/performance/test_semantic_redundancy_performance.py -v -m slow

# Ver estado de recursos
python -c "from narrative_assistant.core import get_resource_manager; print(get_resource_manager().get_status())"

# Benchmark rápido
python -c "
from tests.performance.test_semantic_redundancy_performance import generate_manuscript_with_redundancy
text, chapters = generate_manuscript_with_redundancy(10000)
print(f'Generados {len(chapters)} capítulos, {len(text)} caracteres')
"
```

---

*Documento generado como parte del TFM - Narrative Assistant*
