# Plan de Desarrollo: Análisis Narrativo Avanzado

## Estado Actual del Sistema

### Pipeline Unificado - Fases

```
FASE 1: PARSING
├── Parsing documento
├── Detección estructura (capítulos)
├── Clasificación documento (ficción/ensayo/técnico)
└── Detección diálogos

FASE 2: EXTRACCIÓN BASE
├── NER mejorado con dialogue hints
└── Marcadores temporales

FASE 3: RESOLUCIÓN
├── Correferencias (votación multi-método)
├── Fusión semántica de entidades
└── Atribución de diálogos (speaker_attribution)

FASE 4: EXTRACCIÓN PROFUNDA
├── Atributos de entidades
├── Relaciones entre personajes
├── Interacciones
├── Matriz de conocimiento
└── Perfiles de voz

FASE 5: CALIDAD
├── Ortografía
├── Gramática
├── Repeticiones léxicas/semánticas
├── Coherencia narrativa
├── Cambios de registro
└── Ritmo/Pacing

FASE 6: CONSISTENCIA
├── Consistencia de atributos
├── Consistencia temporal
├── Violaciones de focalización
├── Desviaciones de voz
├── Coherencia emocional
└── Análisis de sentimiento (arcos)
```

---

## 1. Frontend: Tabs Condicionales ⚠️ PARCIALMENTE IMPLEMENTADO

### Implementado

1. **Store actualizado** (`frontend/src/stores/analysis.ts`):
   - `ExecutedPhases` - Interface con todas las fases de análisis
   - `ANALYSIS_DEPENDENCIES` - Mapa de dependencias entre fases
   - `PHASE_LABELS` - Nombres legibles para UI
   - Métodos: `loadExecutedPhases()`, `isPhaseExecuted()`, `getMissingDependencies()`, `canRunPhase()`, `runPartialAnalysis()`

2. **Componente creado** (`frontend/src/components/analysis/AnalysisRequired.vue`):
   - Muestra overlay cuando el análisis no se ha ejecutado
   - Lista dependencias faltantes
   - Botón para ejecutar análisis (con dependencias)
   - Loading state durante ejecución

### Pendiente

- Integrar `AnalysisRequired` en las tabs del workspace
- Añadir endpoint `/api/projects/{id}/analysis-status` en backend
- Añadir endpoint para análisis parcial
- Modificar `ProjectDetailView.vue` para usar el componente

### Diseño Original

#### 1.1 Modelo de datos del análisis
```typescript
interface AnalysisStatus {
  // Flags de ejecución
  executed: {
    structure: boolean;
    entities: boolean;
    attributes: boolean;
    relationships: boolean;
    interactions: boolean;
    spelling: boolean;
    grammar: boolean;
    coherence: boolean;
    register: boolean;
    pacing: boolean;
    emotional: boolean;
    sentiment: boolean;
    temporal: boolean;
    focalization: boolean;
  };

  // Dependencias entre análisis
  dependencies: {
    attributes: ['entities'];
    relationships: ['entities', 'coreference'];
    interactions: ['entities'];
    emotional: ['entities', 'dialogues'];
    voice_deviations: ['voice_profiles'];
    temporal_consistency: ['temporal_markers'];
  };
}
```

#### 1.2 Componente Tab Condicional
```vue
<!-- AnalysisTab.vue -->
<template>
  <div class="analysis-tab" :class="{ 'not-executed': !isExecuted }">
    <div v-if="!isExecuted" class="not-executed-overlay">
      <div class="message">
        <i class="pi pi-info-circle" />
        <span>Este análisis no se ha ejecutado</span>
      </div>

      <div v-if="missingDependencies.length > 0" class="dependencies">
        <p>Requiere ejecutar primero:</p>
        <ul>
          <li v-for="dep in missingDependencies" :key="dep">
            {{ getAnalysisLabel(dep) }}
          </li>
        </ul>
      </div>

      <Button
        :label="runButtonLabel"
        icon="pi pi-play"
        @click="runAnalysis"
        :loading="isRunning"
      />
    </div>

    <slot v-else />
  </div>
</template>
```

#### 1.3 Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `frontend/src/stores/analysis.ts` | Añadir `executedAnalyses` al estado |
| `frontend/src/views/ProjectDetailView.vue` | Tabs condicionales |
| `frontend/src/components/AnalysisTab.vue` | **Nuevo** - Wrapper con lógica |
| `api-server/main.py` | Endpoint para ejecutar análisis parcial |

---

## 2. Backend: Unificación de Extractores de Atributos

### Estado Actual

Existen **3 sistemas** de extracción de atributos:

| Sistema | Ubicación | Técnica | Estado |
|---------|-----------|---------|--------|
| `AttributeExtractionPipeline` | `nlp/extraction/` | Híbrido (spaCy + LLM + voting) | **Principal, conectado** |
| `AIAttributeExtractor` | `nlp/ai_attribute_extractor.py` | Solo LLM | **Desconectado** |
| `AttributeExtractor` (legacy) | `nlp/attributes.py` | Solo spaCy patterns | **Parcialmente usado** |

### Análisis Comparativo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE (Principal)                  │
├─────────────────────────────────────────────────────────────────────┤
│ Pros:                                                               │
│ ✓ Votación multi-método (dependencias, patrones, LLM)               │
│ ✓ Confianza calibrada por consenso                                  │
│ ✓ Fallback automático si LLM no disponible                          │
│ ✓ Bien integrado en unified_analysis                                │
│                                                                     │
│ Contras:                                                            │
│ ✗ No usa todas las capacidades del AIAttributeExtractor             │
│ ✗ Patrones regex limitados para español complejo                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    AI ATTRIBUTE EXTRACTOR                           │
├─────────────────────────────────────────────────────────────────────┤
│ Pros:                                                               │
│ ✓ Prompts más elaborados para LLM                                   │
│ ✓ Extracción de atributos implícitos (inferencia)                   │
│ ✓ Mejor manejo de contexto largo                                    │
│                                                                     │
│ Contras:                                                            │
│ ✗ Depende 100% de LLM (sin fallback)                                │
│ ✗ Más lento                                                         │
│ ✗ No integrado en pipeline                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    LEGACY ATTRIBUTE EXTRACTOR                       │
├─────────────────────────────────────────────────────────────────────┤
│ Pros:                                                               │
│ ✓ Muy rápido (solo regex)                                           │
│ ✓ Sin dependencias externas                                         │
│                                                                     │
│ Contras:                                                            │
│ ✗ Patrones limitados                                                │
│ ✗ Alta tasa de falsos positivos/negativos                           │
│ ✗ No detecta atributos implícitos                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Decisión: Fusionar en ExtractionPipeline ✅ COMPLETADO

**Acción realizada**:

1. ✅ **Análisis de los 3 sistemas**:
   - `AttributeExtractionPipeline` (nlp/extraction/) - Sistema principal con votación
   - `AIAttributeExtractor` (nlp/ai_attribute_extractor.py) - Duplicado de DependencyExtractor
   - `AttributeExtractor` (nlp/attributes.py) - Sistema legacy pero funcional

2. ✅ **Resultado del análisis**:
   - El `DependencyExtractor` ya tiene todas las funcionalidades del `AIAttributeExtractor`
   - El `LLMExtractor` ya tiene prompts elaborados similares
   - No hay funcionalidad única que migrar

3. ✅ **Acciones tomadas**:
   - `ai_attribute_extractor.py`: Añadido deprecation warning con guía de migración
   - `attributes.py`: Añadida nota de unificación (se mantiene porque está en uso)
   - `nlp/__init__.py`: Expone ambos sistemas, recomienda el nuevo
   - `nlp/extraction/__init__.py`: Exporta `get_extraction_pipeline`, `reset_extraction_pipeline`

4. **Recomendación para nuevos desarrollos**:
   ```python
   # RECOMENDADO:
   from narrative_assistant.nlp.extraction import AttributeExtractionPipeline
   pipeline = AttributeExtractionPipeline()
   attributes = pipeline.extract(text, entity_names)

   # LEGACY (sigue funcionando):
   from narrative_assistant.nlp import get_attribute_extractor
   extractor = get_attribute_extractor()
   result = extractor.extract_attributes(text, entity_mentions)
   ```

### Cambios Específicos

```python
# nlp/extraction/extractors/llm_extractor.py

# ANTES: Prompt simple
prompt = f"Extrae atributos físicos de: {text}"

# DESPUÉS: Prompt elaborado (de AIAttributeExtractor)
prompt = f"""Analiza el siguiente texto y extrae atributos del personaje {entity_name}.

CATEGORÍAS:
- Físicos: altura, peso, color de pelo, ojos, rasgos distintivos
- Personalidad: rasgos de carácter, comportamientos habituales
- Relaciones: vínculos familiares, profesionales, románticos
- Historia: edad, profesión, origen, eventos pasados

REGLAS:
1. Solo extrae información EXPLÍCITA o FUERTEMENTE IMPLÍCITA
2. Indica confianza: alta (explícito), media (implícito claro), baja (inferido)
3. Cita el fragmento que justifica cada atributo

TEXTO:
{text}

PERSONAJE: {entity_name}
"""
```

---

## 3. Revisión de Módulos Desconectados

### Panel de Expertos

**Lingüista Computacional** (LC), **Corrector Profesional** (CP), **Experto NLP/IA** (NLP)

### Módulo: `relationships.detector` vs `relationship_clustering`

| Aspecto | relationships.detector | relationship_clustering |
|---------|----------------------|------------------------|
| Técnica | Patrones + dependencias | Co-ocurrencia + clustering |
| Output | Relaciones tipadas | Clusters + grafo |
| Conectado | No | Sí |

**LC**: El detector tiene tipos de relación más precisos (FAMILIA, AMOR, ENEMIGO). El clustering es más estadístico.

**CP**: Para corrección necesito saber "Juan es hermano de María", no solo "están relacionados".

**NLP**: Podemos usar votación: si ambos detectan una relación, más confianza.

**Decisión**: Integrar `relationships.detector` como método adicional en la votación de relaciones.

### Módulo: `relationships.repository`

**LC**: Necesario para persistir relaciones entre sesiones.

**CP**: Sí, quiero ver relaciones detectadas antes sin re-analizar.

**NLP**: Esquema simple: `(entity1_id, entity2_id, relation_type, confidence, chapter_id)`.

**Decisión**: Implementar persistencia. Ver sección 4.

### Módulo: `nlp.training_data`

**LC**: Sistema experimental de aprendizaje de pesos. Interesante pero no prioritario.

**CP**: No lo necesito para corrección.

**NLP**: Útil para ajustar pesos de votación según corpus del usuario. Fase 2.

**Decisión**: Mantener pero no conectar ahora. Documentar para futuro.

### Módulo: `nlp.coref.py` (obsoleto)

**Todos**: Eliminar. Reemplazado por `coreference_resolver.py`.

**Decisión**: Eliminar archivo.

---

## 4. Persistencia de Resultados de Análisis ✅ IMPLEMENTADO

### Cambios Realizados

1. **Base de datos** (`persistence/database.py`):
   - Schema actualizado a versión 6
   - Nuevas tablas: `analysis_runs`, `analysis_phases`, `relationships`, `interactions`, `register_changes`, `pacing_metrics`, `emotional_arcs`, `voice_profiles`

2. **Nuevo repositorio** (`persistence/analysis.py`):
   - `AnalysisRepository` con métodos para guardar/leer todos los tipos de resultados
   - Clases: `AnalysisRun`, `AnalysisPhase`, `Relationship`, `Interaction`, `RegisterChange`, `PacingMetrics`
   - Enums: `AnalysisStatus`, `RelationType`, `InteractionType`, `Tone`
   - Métodos batch para inserción eficiente
   - Singleton `get_analysis_repository()`

3. **Exportado en** `persistence/__init__.py`

### Ejemplo de uso

```python
from narrative_assistant.persistence import (
    get_analysis_repository,
    Relationship, Interaction, RegisterChange, PacingMetrics
)

repo = get_analysis_repository()

# Crear run de análisis
run_id = repo.create_run(project_id, config_json, quality_profile="deep")

# Guardar fases ejecutadas
repo.save_phase(run_id, "ner", executed=True, result_count=50)

# Guardar relaciones
repo.save_relationships_batch([
    Relationship(project_id=1, entity1_id=1, entity2_id=2, relation_type="FAMILY")
])

# Consultar estado
executed = repo.get_executed_phases(project_id)  # {"ner": True, ...}
```

### Esquema de Base de Datos (Referencia)

```sql
-- Tabla principal de análisis
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    config_json TEXT,  -- UnifiedConfig serializado
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,  -- 'running', 'completed', 'failed'
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Qué análisis se ejecutaron en cada run
CREATE TABLE analysis_phases (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    phase_name TEXT NOT NULL,  -- 'ner', 'attributes', 'spelling', etc.
    executed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_count INTEGER,  -- Número de items encontrados
    error_message TEXT,
    FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
);

-- Relaciones detectadas (nuevo)
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    entity1_id INTEGER NOT NULL,
    entity2_id INTEGER NOT NULL,
    relation_type TEXT,  -- 'FAMILY', 'ROMANTIC', 'PROFESSIONAL', etc.
    subtype TEXT,  -- 'hermano', 'esposo', 'jefe', etc.
    confidence REAL,
    chapter_id INTEGER,
    source_text TEXT,
    detection_method TEXT,  -- 'pattern', 'clustering', 'llm'
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (entity1_id) REFERENCES entities(id),
    FOREIGN KEY (entity2_id) REFERENCES entities(id)
);

-- Interacciones (nuevo)
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    entity1_id INTEGER NOT NULL,
    entity2_id INTEGER NOT NULL,
    interaction_type TEXT,  -- 'DIALOGUE', 'PHYSICAL', 'THOUGHT'
    tone TEXT,  -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    chapter_id INTEGER,
    position INTEGER,
    text_excerpt TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Marcadores temporales (nuevo)
CREATE TABLE temporal_markers (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    marker_type TEXT,  -- 'ABSOLUTE', 'RELATIVE', 'DURATION'
    text TEXT,
    normalized_value TEXT,  -- ISO date o duración normalizada
    chapter_id INTEGER,
    position INTEGER,
    confidence REAL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Cambios de registro (nuevo)
CREATE TABLE register_changes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_register TEXT,
    to_register TEXT,
    chapter_id INTEGER,
    position INTEGER,
    severity TEXT,
    explanation TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Métricas de pacing (nuevo)
CREATE TABLE pacing_metrics (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    word_count INTEGER,
    dialogue_ratio REAL,
    avg_sentence_length REAL,
    lexical_density REAL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

---

## 5. Módulos Potenciales a Implementar

### Prioridad Alta (Útiles para corrección)

#### 5.1 Detector de Muletillas
```
Ubicación: src/narrative_assistant/nlp/style/filler_detector.py
Dependencias: NER (para asociar a personajes)
Output: Lista de muletillas por personaje con frecuencia

Ejemplo:
- "Juan": {"bueno": 15, "o sea": 8, "¿sabes?": 12}
- "María": {"la verdad": 5, "tipo": 3}

Alertas:
- Muletilla excesiva (>10 usos)
- Muletilla inconsistente (personaje la usa solo en un capítulo)
- Muletilla del autor (todos los personajes la usan igual)
```

#### 5.2 Análisis de Legibilidad
```
Ubicación: src/narrative_assistant/nlp/style/readability.py
Métricas:
- Índice Flesch-Szigriszt (adaptado español)
- Índice Fernández-Huerta
- INFLESZ (Legibilidad)
- Promedio sílabas por palabra
- Promedio palabras por oración

Output por capítulo:
{
  "chapter": 1,
  "flesch_szigriszt": 65.2,  // 0-100, mayor = más fácil
  "classification": "Normal",  // Muy fácil, Fácil, Normal, Difícil, Muy difícil
  "complex_sentences": [...]  // Oraciones > 40 palabras
}
```

#### 5.3 Detector de Anacolutos
```
Ubicación: src/narrative_assistant/nlp/grammar/anacoluthon.py
Técnica: Análisis de dependencias + patrones

Ejemplos detectables:
- "El perro, que estaba en el jardín, los niños lo vieron" (cambio de sujeto)
- "María pensaba que si llegaba tarde..." (frase incompleta)
```

### Prioridad Media (Análisis narrativo)

#### 5.4 Análisis de Tensión Narrativa
```
Ubicación: src/narrative_assistant/analysis/tension.py
Inputs:
- Sentimiento por segmento
- Verbos de acción detectados
- Longitud de oraciones
- Presencia de diálogo

Output:
{
  "chapter": 1,
  "tension_curve": [0.2, 0.3, 0.5, 0.8, 0.9, 0.4],  // Por segmento
  "peak_position": 0.7,  // 70% del capítulo
  "avg_tension": 0.52,
  "classification": "climax_late"  // early, mid, late, flat
}
```

#### 5.5 Detector de Chekhov's Guns
```
Ubicación: src/narrative_assistant/analysis/foreshadowing.py
Técnica:
1. Detectar menciones únicas de objetos/conceptos
2. Rastrear si reaparecen después
3. Alertar sobre "guns" que no se disparan

Output:
{
  "item": "la pistola del abuelo",
  "first_mention": {"chapter": 2, "position": 1500},
  "subsequent_mentions": [...],
  "resolved": false,  // ¿Se usa/resuelve?
  "alert": "Objeto mencionado una vez y nunca más usado"
}
```

### Prioridad Baja (Futuro)

#### 5.6 Visualización de Red de Conocimiento
```
No es módulo de backend, es feature de frontend.
Usar datos de character_knowledge para grafo interactivo.
```

---

## 6. Plan de Implementación

### Fase 1: Infraestructura ✅ COMPLETADA
- [x] Crear documento de planificación
- [x] Unificar extractores de atributos (deprecado ai_attribute_extractor.py)
- [x] Añadir persistencia de relaciones/interacciones/pacing (`persistence/analysis.py`)
- [x] Actualizar schema de BD a versión 6
- [x] Frontend: Store con tracking de fases ejecutadas
- [x] Frontend: Componente `AnalysisRequired` para tabs condicionales

### Fase 2: Módulos de Estilo (SIGUIENTE)
- [ ] Detector de muletillas (`nlp/style/filler_detector.py`)
- [ ] Análisis de legibilidad (`nlp/style/readability.py`)
- [ ] Detector de anacolutos (`nlp/grammar/anacoluthon.py`)

### Fase 3: Módulos Narrativos
- [ ] Análisis de tensión (`analysis/tension.py`)
- [ ] Detector de Chekhov's guns (`analysis/foreshadowing.py`)

### Fase 4: Visualización
- [ ] Red de conocimiento (frontend)
- [ ] Curva de tensión (frontend)

---

## 7. API Endpoints Necesarios

```python
# Ejecutar análisis parcial
POST /api/projects/{id}/analyze
Body: {
  "phases": ["attributes", "relationships"],
  "force": false
}

# Estado de análisis
GET /api/projects/{id}/analysis-status
Response: {
  "executed": {"entities": true, "attributes": false, ...},
  "last_run": "2024-01-15T10:30:00Z",
  "can_run": {"attributes": true, "relationships": false},
  "missing_dependencies": {"relationships": ["entities"]}
}

# Obtener resultados de fase específica
GET /api/projects/{id}/analysis/{phase}
Response: {
  "phase": "relationships",
  "executed": true,
  "executed_at": "...",
  "results": [...]
}
```

---

## Notas

- **No implementar**: Auto-corrección, generación de contenido, traducción
- **Principio**: El sistema sugiere, el humano decide
- **Prioridad**: Herramientas útiles para correctores profesionales
