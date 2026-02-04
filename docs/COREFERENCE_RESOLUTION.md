# Resolución de Correferencias - Narrative Assistant

> **Estado**: Implementado (2026-01-12)
> **Versión**: 2.0 - Sistema de votación multi-método

---

## Resumen

El sistema de resolución de correferencias identifica cuándo diferentes menciones en el texto se refieren a la misma entidad. Por ejemplo:

- "María Sánchez" y "ella" → misma persona
- "Juan Pérez" y "él" → misma persona
- "el detective" y "él" → misma persona

---

## Arquitectura

### Sistema de Votación Multi-Método

El sistema combina **4 métodos independientes** y usa **votación ponderada** para determinar las correferencias:

```
┌─────────────────────────────────────────────────────────────┐
│                    Texto de entrada                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Extracción de Menciones (spaCy)                 │
│   - Entidades nombradas (PER, LOC, ORG)                      │
│   - Pronombres (él, ella, ellos, etc.)                       │
│   - Demostrativos (este, ese, aquel)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Resolución por Métodos Paralelos                │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │  Embeddings  │ │     LLM      │ │   Morfología │         │
│  │   (30%)      │ │    (35%)     │ │    (20%)     │         │
│  │              │ │   (Ollama)   │ │   (spaCy)    │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
│                                                              │
│  ┌──────────────┐                                           │
│  │ Heurísticas  │                                           │
│  │   (15%)      │                                           │
│  │  narrativas  │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Votación Ponderada                         │
│   - Combina scores de todos los métodos                      │
│   - Umbral mínimo de confianza: 0.5                         │
│   - Consenso mínimo: 60%                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Cadenas de Correferencia                       │
│   - Agrupación por Union-Find                               │
│   - Selección de mención principal                          │
│   - Vinculación con entidades NER                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Métodos de Resolución

### 1. Embeddings Semánticos (30%)

**Modelo**: `paraphrase-multilingual-MiniLM-L12-v2` (500MB, local)

**Funcionamiento**:
- Calcula similitud semántica entre el contexto de la mención y los candidatos
- Boost por concordancia de género/número detectada
- Útil para resolver referencias semánticamente relacionadas

**Ejemplo**:
```
"El detective revisó las pruebas. Él encontró una pista."
                                   ↑
Similitud("detective" contexto) vs "Él" contexto → 0.78
```

### 2. LLM Local (35%)

**Modelos**: Ollama (llama3.2, mistral, qwen2.5)

**Funcionamiento**:
- Envía prompt estructurado al LLM con contexto y candidatos
- El LLM analiza semánticamente quién es el referente
- Especialmente útil para casos ambiguos que requieren razonamiento

**Prompt ejemplo**:
```
Analiza la siguiente correferencia en español.

CONTEXTO:
"María entró en la habitación. Ella llevaba un vestido azul."

MENCIÓN A RESOLVER: "Ella"

CANDIDATOS:
1. "María" (posición: 0)

¿A cuál candidato se refiere "Ella"?
```

**Ventajas**:
- Comprensión profunda del contexto narrativo
- Manejo de casos complejos (ironía, metáforas)
- Multilingüe por diseño

**Limitaciones**:
- Requiere Ollama instalado y corriendo
- Mayor latencia (~1-2s por consulta)
- Fallback graceful si no disponible

### 3. Análisis Morfosintáctico (20%)

**Modelo**: spaCy `es_core_news_lg`

**Funcionamiento**:
- Concordancia de género (masculino/femenino)
- Concordancia de número (singular/plural)
- Análisis de dependencias sintácticas
- Bonificación por tipo de mención

**Reglas de scoring**:
```python
# Género coincide: +0.4
# Número coincide: +0.3
# Nombre propio como candidato: +0.2
# Misma oración: +0.1
# Distancia > 5 oraciones: -0.1
```

### 4. Heurísticas Narrativas (15%)

**Funcionamiento**:
- Reglas basadas en patrones típicos de la narrativa española
- Proximidad textual (candidatos más cercanos preferidos)
- Patrones pronombre→nombre propio

**Reglas principales**:
```python
# Distancia < 100 chars: +0.4
# Distancia 100-300 chars: +0.3
# Distancia 300-1000 chars: +0.1
# "él/ella" → nombre propio: +0.2
# Posesivo → nombre: +0.15
# Mismo capítulo: +0.1
```

---

## Configuración

### Parámetros Principales

```python
from narrative_assistant.nlp.coreference_resolver import CorefConfig, CorefMethod

config = CorefConfig(
    # Métodos habilitados
    enabled_methods=[
        CorefMethod.EMBEDDINGS,
        CorefMethod.LLM,
        CorefMethod.MORPHO,
        CorefMethod.HEURISTICS,
    ],

    # Pesos de votación (deben sumar ~1.0)
    method_weights={
        CorefMethod.EMBEDDINGS: 0.30,
        CorefMethod.LLM: 0.35,
        CorefMethod.MORPHO: 0.20,
        CorefMethod.HEURISTICS: 0.15,
    },

    # Umbrales
    min_confidence=0.5,        # Confianza mínima para aceptar
    consensus_threshold=0.6,   # % mínimo de métodos que deben acordar

    # Restricciones
    max_antecedent_distance=5,     # Máx oraciones hacia atrás
    use_chapter_boundaries=True,   # No cruzar límites de capítulo

    # LLM
    ollama_model="llama3.2",
    ollama_timeout=30,
)
```

### Uso Básico

```python
from narrative_assistant.nlp.coreference_resolver import resolve_coreferences_voting

text = """
María Sánchez entró en la habitación. Ella llevaba un vestido azul.
Juan Pérez la saludó. Él era su vecino desde hace años.
"""

result = resolve_coreferences_voting(text)

print(f"Cadenas encontradas: {result.total_chains}")
for chain in result.chains:
    print(f"  {chain.main_mention}: {[m.text for m in chain.mentions]}")
```

**Salida**:
```
Cadenas encontradas: 2
  María Sánchez: ['María Sánchez', 'Ella', 'la']
  Juan Pérez: ['Juan Pérez', 'Él']
```

---

## Procesamiento por Capítulos

El sistema respeta los límites de capítulo para evitar correferencias incorrectas:

```python
chapters = [
    {"start_char": 0, "end_char": 500, "title": "Capítulo 1"},
    {"start_char": 501, "end_char": 1000, "title": "Capítulo 2"},
]

result = resolve_coreferences_voting(text, chapters=chapters)
```

**Comportamiento**:
- Un pronombre en el Capítulo 2 NO puede referir a una entidad del Capítulo 1
- Esto evita falsos positivos en narrativas con múltiples personajes

---

## Integración en el Pipeline

El sistema de correferencias se ejecuta en la **Fase 3.5** del análisis:

```
Fase 1: Carga de documento
Fase 2: Detección de estructura (capítulos)
Fase 3: NER (Named Entity Recognition)
Fase 3.5: Fusión de entidades + Correferencias  ← AQUÍ
Fase 4: Extracción de atributos
Fase 5: Análisis de consistencia
Fase 6: Generación de alertas
```

**Acciones en Fase 3.5**:
1. **Fusión semántica**: "María" + "María Sánchez" → una entidad
2. **Correferencias**: "Él" → "Juan Pérez" (incrementa menciones)

---

## Pronombres Soportados

### Pronombres Personales
| Pronombre | Género | Número |
|-----------|--------|--------|
| él | Masculino | Singular |
| ella | Femenino | Singular |
| ellos | Masculino | Plural |
| ellas | Femenino | Plural |

### Pronombres Objeto
| Pronombre | Género | Número |
|-----------|--------|--------|
| lo | Masculino | Singular |
| la | Femenino | Singular |
| los | Masculino | Plural |
| las | Femenino | Plural |
| le | Neutral | Singular |
| les | Neutral | Plural |

### Demostrativos
| Pronombre | Género | Número |
|-----------|--------|--------|
| este/esta | M/F | Singular |
| estos/estas | M/F | Plural |
| ese/esa | M/F | Singular |
| esos/esas | M/F | Plural |
| aquel/aquella | M/F | Singular |
| aquellos/aquellas | M/F | Plural |

---

## Comparación con Versión Anterior

| Aspecto | Versión 1.0 (coreferee) | Versión 2.0 (votación) |
|---------|------------------------|------------------------|
| Dependencia | coreferee (incompatible spaCy 3.7+) | Sin dependencias externas |
| Métodos | 1 (coreferee + heurísticas) | 4 (embeddings, LLM, morfología, heurísticas) |
| Español | Limitado | Completo (spaCy es_core_news_lg) |
| LLM | No | Sí (Ollama local) |
| Capítulos | No | Sí |
| Votación | No | Sí (ponderada) |
| Fallbacks | Parcial | Completo (cada método independiente) |

---

## Rendimiento

### Benchmarks (texto ~500 palabras)

| Configuración | Tiempo | Precisión estimada |
|---------------|--------|-------------------|
| Solo heurísticas | ~50ms | 60% |
| Morfología + heurísticas | ~200ms | 70% |
| + Embeddings | ~500ms | 80% |
| + LLM (Ollama) | ~3s | 85-90% |

### Recomendaciones

- **Textos cortos (<1000 palabras)**: Usar todos los métodos
- **Textos largos (>10000 palabras)**: Desactivar LLM, usar embeddings
- **Análisis rápido**: Solo morfología + heurísticas

---

## Limitaciones Conocidas

1. **Pro-drop español**: Sujetos omitidos no se detectan (ej: "Entró en la habitación" sin sujeto explícito)

2. **Referencias anafóricas complejas**:
   - "María le dijo a Juan que él debía ir" (ambiguo)
   - Requiere análisis semántico profundo

3. **Diálogos**: Pronombres en diálogo directo pueden ser ambiguos

4. **Metáforas/ironía**: "El sol de mi vida" refiriéndose a una persona

---

## Troubleshooting

### LLM no disponible
```
WARNING: No se pudo conectar LLM: ...
```
**Solución**: Iniciar Ollama (`ollama serve`) o desactivar método LLM en config.

### GPU con poca VRAM o crash de CUDA
```
error="llama runner process has terminated: exit status 2"
```
**Solución**: Usar el script `scripts/start_ollama_cpu.bat` para forzar modo CPU:
```batch
scripts\start_ollama_cpu.bat
```
Este script:
- Desactiva CUDA completamente
- Inicia Ollama minimizado en segundo plano
- Espera a que el servidor esté listo

### Embeddings lentos
```python
# Reducir peso de embeddings o desactivar
config = CorefConfig(
    enabled_methods=[CorefMethod.MORPHO, CorefMethod.HEURISTICS],
)
```

### Demasiados falsos positivos
```python
# Aumentar umbral de confianza
config = CorefConfig(min_confidence=0.7)
```

---

## Referencias

- Lee et al. (2017): "End-to-end Neural Coreference Resolution"
- AnCora-CO: Corpus español anotado para correferencias
- XLM-RoBERTa: Embeddings multilingües
- spaCy `es_core_news_lg`: Modelo español

---

## Archivos Relacionados

- `src/narrative_assistant/nlp/coreference_resolver.py` - Implementación principal
- `src/narrative_assistant/nlp/coref.py` - Versión legacy (deprecated)
- `src/narrative_assistant/entities/semantic_fusion.py` - Fusión de entidades
- `api-server/main.py` (líneas 1309-1422) - Integración en pipeline
