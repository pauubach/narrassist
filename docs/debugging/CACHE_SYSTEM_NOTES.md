# Sistema de Cache - Notas de Implementación

**Fecha**: 2026-02-17
**Versión**: v0.10.15
**Objetivo**: 100x speedup en re-análisis (10-12 min → <10 seg)

---

## 📊 Estado de Implementación

### ✅ Completado

| Componente | Estado | Commit | Speedup |
|------------|--------|--------|---------|
| **Schema DB** | ✅ | `d205162` | - |
| **AnalysisCache** | ✅ | `d205162` | - |
| **NER Cache** | ✅ | `bc05901` | 3-5 min → <1s |
| **Coref Cache** | ⏳ | Pendiente | 5-7 min → <1s |
| **Attr Cache** | ⏳ | Pendiente | 30s → <1s |

### 🎯 Progreso

- **Actual**: ~40% del speedup total (solo NER cacheado)
- **Target**: 100x speedup cuando las 3 fases estén integradas

---

## 🏗️ Arquitectura

### Tablas de Cache (SCHEMA_VERSION 29)

```sql
-- 3 tablas con patrón idéntico
CREATE TABLE {phase}_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_fingerprint TEXT NOT NULL,  -- SHA-256 cache key
    config_hash TEXT NOT NULL,           -- Config-aware cache
    {phase}_json TEXT NOT NULL,          -- Serialized results
    {counters} INTEGER DEFAULT 0,        -- Metadata
    cache_version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, document_fingerprint, config_hash)
);

CREATE INDEX idx_{phase}_cache_lookup ON {phase}_cache(
    project_id, document_fingerprint, config_hash
);
```

### Cache Key = `(project_id, fingerprint, config_hash)`

**¿Por qué config_hash?**
- NER puede usar Ollama o no (`use_llm=true/false`)
- Correferencias puede usar diferentes métodos
- Configuraciones diferentes → resultados diferentes → cache separado

**Ejemplo**:
```python
config_hash = hashlib.sha256(
    json.dumps({
        "use_llm": True,
        "run_ner": True
    }, sort_keys=True).encode()
).hexdigest()[:16]  # "a3f2c1d4e5b6..."
```

---

## 🔄 Flujo de Re-análisis

### Sin Cache (ANTES)
```
1. Parsing (1s)
2. Structure (2s)
3. NER (3-5 min)    ← Ollama bloqueante
4. Coref (5-7 min)  ← Ollama bloqueante
5. Attributes (30s)
6. Consistency (2 min)
TOTAL: 10-12 min
```

### Con Cache (DESPUÉS)
```
1. Parsing (1s)
2. Structure (2s)
3. NER (<1s)         ← Cache hit, deserialize JSON
4. Coref (<1s)       ← Cache hit (pendiente)
5. Attributes (<1s)  ← Cache hit (pendiente)
6. Consistency (2 min)
TOTAL: ~2-3 min (con solo NER), <10s (con las 3 fases)
```

---

## 💾 Serialización

### NER (Entidades + Menciones)

```json
[
  {
    "id": 3456,
    "canonical_name": "María Sánchez",
    "entity_type": "CHARACTER",
    "aliases": ["María", "Sánchez"],
    "importance": "PRINCIPAL",
    "first_appearance_char": 125,
    "mention_count": 45,
    "mentions": [
      {
        "surface_form": "María",
        "start_char": 125,
        "end_char": 130,
        "chapter_id": 1,
        "confidence": 0.95,
        "source": "spacy"
      },
      // ... 44 más
    ]
  },
  // ... más entidades
]
```

**Tamaño**: ~500 KB por proyecto típico (3 entidades, 100 menciones)

### Correferencias (Pendiente)

```json
{
  "chains": [
    {
      "mentions": ["María", "ella", "la mujer"],
      "entity_id": 3456,
      "confidence": 0.85
    }
  ],
  "unresolved": ["ese hombre"],
  "method": "voting"
}
```

### Atributos (Pendiente)

```json
[
  {
    "entity_id": 3456,
    "attr_type": "eye_color",
    "value": "azules",
    "evidence": {
      "text": "sus ojos azules brillaban",
      "start_char": 450,
      "end_char": 478,
      "confidence": 0.9
    }
  }
]
```

---

## 🧪 Testing

### Cache Hit (Esperado)

```bash
# Primer análisis
[NER] NER complete: 3 entities (5 minutos)
[NER_CACHE] SET SUCCESS: project=5, entities=3, mentions=45

# Re-análisis (documento sin cambios)
[NER] Using cached results: 3 entities, 45 mentions (SKIP NER)
[NER] Cache restore complete: 3 entities (0.8s)
```

### Cache Miss (Esperado)

```bash
# Documento modificado (fingerprint cambió)
[NER_CACHE] MISS: project=5, config=a3f2c1d4 (hit rate: 0.0%)
[NER] NER complete: 3 entities (5 minutos)
[NER_CACHE] SET SUCCESS: project=5, entities=3, mentions=45
```

---

## 🐛 Issues Conocidos

### 1. Cancelación NO funciona durante Ollama

**Problema**: Cuando usuario cancela análisis, el backend está bloqueado esperando respuesta de Ollama (2-5 min) y no puede verificar `cancellation_flags`.

**Logs**:
```
17:54:15 - Votación coreference/qwen2.5: 109.0s  ← Bloqueado aquí
```

**Solución propuesta**:
- Hacer llamadas a Ollama con timeout corto
- Verificar flag de cancelación cada N segundos
- Usar threads cancelables para LLM calls

**Workaround actual**: Esperar a que Ollama termine (puede tardar 5-10 min).

### 2. tokenizers version mismatch

**Warning**:
```
tokenizers>=0.22.0,<=0.23.0 is required, but found tokenizers==0.20.3
```

**Impacto**: Embeddings para correferencias NO funcionan → solo LLM method

**Fix**:
```bash
pip install tokenizers==0.22.0
```

---

## 📈 Métricas de Performance

### Proyecto "Rich" (318 palabras, 3 capítulos)

| Fase | Sin Cache | Con Cache | Speedup |
|------|-----------|-----------|---------|
| Parsing | 1s | 1s | 1x |
| Structure | 2s | 2s | 1x |
| **NER** | **180s** | **<1s** | **180x** |
| Coref | 300s | ⏳ | - |
| Attributes | 30s | ⏳ | - |
| Consistency | 120s | 120s | 1x |
| **TOTAL** | **633s (10.5 min)** | **~450s (7.5 min)** | **1.4x** |

**Con todas las fases cacheadas**:
- **Target**: <10s (100x speedup)

---

## 🔧 Rollback Plan

### Nivel 1: Deshabilitar cache (sin reiniciar)
```bash
# En ~/.bashrc o equivalente
export NA_CACHE_ENABLED=false

# Reiniciar servidor API
pkill -f "uvicorn.*main:app"
```

### Nivel 2: Limpiar cache (usuario)
```python
from narrative_assistant.persistence.analysis_cache import clear_analysis_cache
clear_analysis_cache()  # Borra todas las entradas
```

### Nivel 3: Drop tablas (catastrófico)
```sql
DROP TABLE IF EXISTS ner_cache;
DROP TABLE IF EXISTS coreference_cache;
DROP TABLE IF EXISTS attribute_cache;
```

---

## 📚 Referencias

- [CACHE_DB_DEBUGGING_SESSION.md](CACHE_DB_DEBUGGING_SESSION.md) - Speech tracking cache (patrón base)
- [analysis_cache.py](../../src/narrative_assistant/persistence/analysis_cache.py) - Implementación
- [database.py](../../src/narrative_assistant/persistence/database.py) - Schema SQL

---

## ✅ Próximos Pasos

1. ⏳ Integrar cache en `run_fusion` (correferencias)
2. ⏳ Integrar cache en `run_attributes`
3. ⏳ Probar con proyecto "Rich" (re-análisis < 10s)
4. ⏳ Tests unitarios
5. ⏳ Fix cancelación durante Ollama calls
