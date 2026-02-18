# HTTP API Endpoints

Base URL: `http://localhost:8000/api`

> **Nota**: Este documento cubre ~70 endpoints principales. El sistema tiene 170+ endpoints en total incluyendo variantes y endpoints auxiliares.

## Respuestas

Todas las respuestas siguen el formato `ApiResponse`:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "message": "Operación exitosa"
}
```

---

## Sistema

### `GET /health`

Verifica que el servidor está funcionando.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "backend_loaded": true,
  "timestamp": "2024-01-15T12:00:00"
}
```

### `GET /info`

Información detallada del sistema.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `version` | `string` | Versión del backend |
| `gpu.device` | `string` | Dispositivo (cuda/mps/cpu) |
| `gpu.available` | `boolean` | GPU disponible |
| `gpu.spacy_gpu` | `boolean` | spaCy usa GPU |
| `gpu.embeddings_gpu` | `boolean` | Embeddings usa GPU |
| `models.spacy_model` | `string` | Modelo spaCy |
| `models.embeddings_model` | `string` | Modelo embeddings |
| `paths.data_dir` | `string` | Directorio datos |
| `paths.cache_dir` | `string` | Directorio caché |

---

## Proyectos

### `GET /projects`

Lista todos los proyectos.

**Response data:** `Project[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `name` | `string` |
| `description` | `string?` |
| `document_format` | `string` |
| `created_at` | `string` (ISO) |
| `last_modified` | `string` (ISO) |
| `last_opened` | `string?` (ISO) |
| `analysis_status` | `string` |
| `analysis_progress` | `number` (0-100) |
| `word_count` | `number` |
| `chapter_count` | `number` |
| `open_alerts_count` | `number` |
| `highest_alert_severity` | `string?` |

### `GET /projects/{project_id}`

Obtiene un proyecto por ID.

**Path params:**
- `project_id`: ID del proyecto

**Response data:** `Project`

### `POST /projects`

Crea un nuevo proyecto.

**Body (multipart/form-data):**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | `string` | Sí | Nombre del proyecto |
| `description` | `string` | No | Descripción |
| `file_path` | `string` | No* | Ruta al archivo local |
| `file` | `File` | No* | Archivo subido |

*Requiere `file_path` O `file`.

**Response data:** `Project`

### `DELETE /projects/{project_id}`

Elimina un proyecto.

**Path params:**
- `project_id`: ID del proyecto

### `POST /projects/{project_id}/reanalyze`

Re-analiza un proyecto existente.

**Path params:**
- `project_id`: ID del proyecto

**Response data:** `Project` (actualizado)

---

## Análisis

### `POST /projects/{project_id}/analyze`

Inicia análisis asíncrono de un proyecto.

**Path params:**
- `project_id`: ID del proyecto

**Body (multipart/form-data):**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `file` | `File` | No | Archivo (usa `document_path` del proyecto si no se proporciona) |

**Response data:**
```json
{
  "project_id": 1,
  "status": "running"
}
```

### `GET /projects/{project_id}/analysis/progress`

Obtiene progreso del análisis.

**Path params:**
- `project_id`: ID del proyecto

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `project_id` | `number` | ID del proyecto |
| `status` | `string` | "pending" \| "running" \| "completed" \| "error" |
| `progress` | `number` | 0-100 |
| `current_phase` | `string` | Fase actual |
| `current_action` | `string?` | Acción actual |
| `phases` | `Phase[]` | Lista de fases |
| `metrics` | `object` | Métricas extraídas |
| `estimated_seconds_remaining` | `number?` | Tiempo restante |
| `error` | `string?` | Error si falló |

**Phase:**
```json
{
  "id": "ner",
  "name": "Reconocimiento de entidades",
  "completed": true,
  "current": false,
  "duration": 5.2
}
```

---

## Entidades

### `GET /projects/{project_id}/entities`

Lista entidades de un proyecto.

**Path params:**
- `project_id`: ID del proyecto

**Response data:** `Entity[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `project_id` | `number` |
| `entity_type` | `string` |
| `canonical_name` | `string` |
| `aliases` | `string[]` |
| `importance` | `string` |

### `POST /projects/{project_id}/entities/merge`

Fusiona múltiples entidades.

**Path params:**
- `project_id`: ID del proyecto

**Body (JSON):**
```json
{
  "primary_entity_id": 1,
  "entity_ids": [2, 3, 4]
}
```

**Response data:**
```json
{
  "primary_entity_id": 1,
  "merged_count": 3
}
```

---

## Alertas

### `GET /projects/{project_id}/alerts`

Lista alertas de un proyecto.

**Path params:**
- `project_id`: ID del proyecto

**Query params:**
- `status` (opcional): Filtrar por estado (open, resolved, dismissed)

**Response data:** `Alert[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `project_id` | `number` |
| `category` | `string` |
| `severity` | `string` |
| `alert_type` | `string` |
| `title` | `string` |
| `description` | `string` |
| `explanation` | `string` |
| `suggestion` | `string?` |
| `chapter` | `number?` |
| `status` | `string` |
| `created_at` | `string` |

### `POST /projects/{project_id}/alerts/{alert_id}/resolve`

Marca alerta como resuelta.

### `POST /projects/{project_id}/alerts/{alert_id}/dismiss`

Descarta una alerta.

### `POST /projects/{project_id}/alerts/{alert_id}/reopen`

Reabre una alerta.

### `POST /projects/{project_id}/alerts/resolve-all`

Resuelve todas las alertas abiertas.

---

## Capítulos

### `GET /projects/{project_id}/chapters`

Lista capítulos de un proyecto.

**Path params:**
- `project_id`: ID del proyecto

**Response data:** `Chapter[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `project_id` | `number` |
| `title` | `string` |
| `content` | `string` |
| `chapter_number` | `number` |
| `word_count` | `number` |
| `position_start` | `number` |
| `position_end` | `number` |
| `structure_type` | `string?` |
| `created_at` | `string?` |
| `updated_at` | `string?` |

---

## Relaciones

### `GET /projects/{project_id}/relationships`

Obtiene análisis de relaciones entre personajes.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `project_id` | `number` | ID del proyecto |
| `entity_count` | `number` | Total entidades |
| `relations` | `Relation[]` | Relaciones inferidas |
| `clusters` | `Cluster[]` | Clusters de personajes |
| `dendrogram_data` | `object?` | Datos dendrograma |
| `mentions` | `Mention[]` | Menciones dirigidas |
| `opinions` | `Opinion[]` | Opiniones detectadas |
| `intentions` | `Intention[]` | Intenciones detectadas |
| `asymmetries` | `Asymmetry[]` | Asimetrías de conocimiento |

### `GET /projects/{project_id}/relationships/asymmetry/{entity_a_id}/{entity_b_id}`

Obtiene reporte de asimetría entre dos personajes.

---

## Servicios LLM

### `GET /api/services/llm/status`

Verifica disponibilidad de Ollama.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `available` | `boolean` | LLM disponible |
| `backend` | `string` | "ollama" \| "transformers" \| "none" |
| `model` | `string?` | Modelo configurado |
| `available_methods` | `string[]` | Métodos disponibles |
| `ollama_models` | `string[]` | Modelos Ollama instalados |
| `message` | `string` | Mensaje descriptivo |

### `GET /api/services/llm/config`

Obtiene configuración de LLM.

**Response data:**
| Campo | Tipo |
|-------|------|
| `backend` | `string` |
| `model` | `string` |
| `enabled_methods` | `string[]` |
| `min_confidence` | `number` |
| `consensus_threshold` | `number` |

### `POST /api/services/llm/config`

Actualiza configuración de LLM.

**Body (JSON):**
```json
{
  "model": "qwen2.5",
  "enabled_methods": ["llm", "embeddings", "rule_based"],
  "min_confidence": 0.6,
  "consensus_threshold": 0.5
}
```

---

## Expectativas de Comportamiento

### `POST /projects/{project_id}/characters/{character_id}/analyze-behavior`

Analiza comportamiento de un personaje con LLM.

**Response data:** `CharacterProfile`

### `POST /projects/{project_id}/characters/{character_id}/detect-violations`

Detecta violaciones de expectativas.

**Query params:**
- `chapter_number` (opcional): Capítulo específico

**Response data:**
| Campo | Tipo |
|-------|------|
| `character_id` | `number` |
| `character_name` | `string` |
| `violations_count` | `number` |
| `violations` | `Violation[]` |

### `GET /projects/{project_id}/characters/{character_id}/expectations`

Obtiene expectativas de un personaje.

**Response data:**
| Campo | Tipo |
|-------|------|
| `character_id` | `number` |
| `character_name` | `string` |
| `expectations` | `Expectation[]` |
| `personality_traits` | `string[]` |
| `values` | `string[]` |
| `goals` | `string[]` |

---

## Colecciones Cross-Book

### `POST /collections`

Crea una nueva colección (saga/serie).

**Body (JSON):**
```json
{
  "name": "Trilogía del Baztán",
  "description": "Novelas de Dolores Redondo",
  "project_ids": [1, 2, 3]
}
```

**Response data:** `Collection`

### `GET /collections`

Lista todas las colecciones.

**Response data:** `Collection[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `name` | `string` |
| `description` | `string?` |
| `project_count` | `number` |
| `created_at` | `string` |

### `GET /collections/{collection_id}`

Obtiene una colección por ID.

**Response data:** `Collection` (con lista de proyectos)

### `PUT /collections/{collection_id}`

Actualiza una colección.

**Body (JSON):**
```json
{
  "name": "Nuevo nombre",
  "description": "Nueva descripción"
}
```

### `DELETE /collections/{collection_id}`

Elimina una colección (NO elimina los proyectos).

### `POST /collections/{collection_id}/projects/{project_id}`

Añade un proyecto a la colección.

### `DELETE /collections/{collection_id}/projects/{project_id}`

Elimina un proyecto de la colección.

---

## Entity Links (Cross-Book)

### `GET /collections/{collection_id}/entity-links`

Lista vínculos de entidades entre libros.

**Response data:** `EntityLink[]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID del vínculo |
| `collection_id` | `number` | ID de la colección |
| `entity1_id` | `number` | ID entidad en libro 1 |
| `entity1_name` | `string` | Nombre en libro 1 |
| `entity1_project_id` | `number` | Proyecto del libro 1 |
| `entity2_id` | `number` | ID entidad en libro 2 |
| `entity2_name` | `string` | Nombre en libro 2 |
| `entity2_project_id` | `number` | Proyecto del libro 2 |
| `confidence` | `number` | 0.0-1.0 |
| `link_type` | `string` | "same_character", "same_location", etc. |

### `POST /collections/{collection_id}/entity-links`

Crea un vínculo manual entre entidades de diferentes libros.

**Body (JSON):**
```json
{
  "entity1_id": 10,
  "entity2_id": 45,
  "link_type": "same_character",
  "confidence": 1.0
}
```

### `GET /collections/{collection_id}/entity-link-suggestions`

Obtiene sugerencias automáticas de vínculos (fuzzy matching + embeddings).

**Response data:** `EntityLinkSuggestion[]`

| Campo | Tipo |
|-------|------|
| `entity1` | `Entity` |
| `entity2` | `Entity` |
| `similarity_score` | `number` |
| `reason` | `string` |

### `DELETE /collections/{collection_id}/entity-links/{link_id}`

Elimina un vínculo de entidad.

---

## Análisis Cross-Book

### `GET /collections/{collection_id}/cross-book-analysis`

Analiza inconsistencias entre libros de una colección.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `collection_id` | `number` | ID de la colección |
| `project_count` | `number` | Número de libros |
| `entity_links_count` | `number` | Vínculos de entidades |
| `inconsistencies` | `Inconsistency[]` | Inconsistencias detectadas |
| `severity_summary` | `object` | Resumen por severidad |

**Inconsistency:**
```json
{
  "type": "attribute_mismatch",
  "severity": "high",
  "entity_link_id": 5,
  "entity_name": "Amaia Salazar",
  "attribute": "eye_color",
  "value_in_book1": "marrón",
  "value_in_book2": "verde",
  "project1_id": 1,
  "project2_id": 2,
  "evidence": [
    {
      "text": "sus ojos marrones...",
      "chapter": 3,
      "project_id": 1
    }
  ]
}
```

### `GET /projects/{project_id}/comparison`

Compara versiones de un proyecto (detect changes entre análisis).

**Response data:**
| Campo | Tipo |
|-------|------|
| `project_id` | `number` |
| `current_version_id` | `number` |
| `previous_version_id` | `number?` |
| `changes` | `Change[]` |
| `metrics_diff` | `object` |

### `GET /projects/{project_id}/comparison/summary`

Resumen de cambios entre versiones.

---

## Eventos Narrativos

### `GET /api/projects/{project_id}/chapters/{chapter_number}/events`

Lista eventos detectados en un capítulo.

**Path params:**
- `project_id`: ID del proyecto
- `chapter_number`: Número de capítulo

**Response data:** `Event[]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `event_type` | `string` | Tipo de evento (ENCOUNTER, DEATH, etc.) |
| `tier` | `number` | 1 (estructural), 2 (transicional), 3 (micro) |
| `description` | `string` | Descripción del evento |
| `confidence` | `number` | 0.0-1.0 |
| `participants` | `string[]` | Entidades involucradas |
| `location` | `string?` | Ubicación |
| `temporal_marker` | `string?` | Marcador temporal |
| `emotional_valence` | `number` | -1.0 (negativo) a 1.0 (positivo) |

**Tipos de eventos (48 tipos, 3 tiers)**:

**Tier 1 (Estructurales - 18 tipos)**:
- `ENCOUNTER` — Primer encuentro entre personajes
- `SEPARATION` — Separación significativa
- `DEATH` — Muerte de personaje
- `BIRTH` — Nacimiento
- `MARRIAGE` — Matrimonio
- `CONFLICT_START` — Inicio de conflicto
- `CONFLICT_END` — Resolución de conflicto
- `TRAVEL` — Viaje significativo
- `DECISION` — Decisión importante
- `REVELATION` — Revelación clave
- `BETRAYAL` — Traición
- `ALLIANCE` — Alianza formada
- `ACQUISITION` — Adquisición de objeto importante
- `LOSS` — Pérdida significativa
- `TRANSFORMATION` — Cambio profundo
- `PROPHECY` — Profecía pronunciada
- `RITUAL` — Ritual o ceremonia
- `ASCENSION` — Ascenso a poder/posición

**Tier 2 (Transicionales - 15 tipos)** y **Tier 3 (Micro - 13 tipos)**: ver [event_types.py](../../src/narrative_assistant/analysis/event_types.py)

### `GET /api/projects/{project_id}/events/stats`

Estadísticas de eventos del proyecto.

**Response data:**
| Campo | Tipo |
|-------|------|
| `project_id` | `number` |
| `total_events` | `number` |
| `events_by_tier` | `{1: number, 2: number, 3: number}` |
| `events_by_type` | `{EVENT_TYPE: number}` |
| `timeline_coverage` | `number` | % capítulos con eventos |
| `average_events_per_chapter` | `number` |

### `GET /api/projects/{project_id}/events/export`

Exporta eventos a CSV.

**Query params:**
- `format`: "csv" | "json" (default: csv)

**Response:** Archivo CSV con todos los eventos

---

## Voz y Estilo (Voice & Style)

### `GET /api/projects/{project_id}/voice-profiles`

Obtiene perfiles de voz de personajes (cómo habla cada uno).

**Response data:** `VoiceProfile[]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `character_id` | `number` | ID de la entidad |
| `character_name` | `string` | Nombre del personaje |
| `metrics` | `object` | Métricas de habla |

**Voice Metrics:**
```json
{
  "formality_score": 0.75,  // 0-1 (informal → formal)
  "avg_sentence_length": 18.5,
  "vocab_complexity": 0.62,  // TTR: type-token ratio
  "filler_words_rate": 0.03,  // muletillas por palabra
  "exclamations_rate": 0.02,
  "questions_rate": 0.05,
  "common_fillers": ["bueno", "pues", "entonces"],
  "speech_patterns": ["uso frecuente de subjuntivo", "tendencia a metáforas"],
  "sample_count": 45  // número de diálogos analizados
}
```

### `GET /api/projects/{project_id}/voice-profiles/compare`

Compara perfiles de voz de dos personajes.

**Query params:**
- `character1_id`: ID primer personaje
- `character2_id`: ID segundo personaje

**Response data:**
| Campo | Tipo |
|-------|------|
| `character1` | `VoiceProfile` |
| `character2` | `VoiceProfile` |
| `similarity_score` | `number` | 0-1 |
| `differences` | `string[]` | Diferencias notables |

### `GET /api/projects/{project_id}/voice-deviations`

Detecta desviaciones de voz (personaje hablando fuera de carácter).

**Query params:**
- `character_id` (opcional): Solo analizar un personaje
- `threshold` (opcional): Umbral de desviación (default: 0.3)

**Response data:** `VoiceDeviation[]`

| Campo | Tipo |
|-------|------|
| `character_id` | `number` |
| `character_name` | `string` |
| `chapter` | `number` |
| `quote_text` | `string` |
| `deviation_score` | `number` | 0-1 |
| `reasons` | `string[]` | Por qué se desvía |
| `suggestion` | `string?` |

### `GET /api/projects/{project_id}/register-analysis`

Análisis de registro lingüístico (formal/informal, técnico/coloquial).

**Response data:**
| Campo | Tipo |
|-------|------|
| `project_id` | `number` |
| `overall_register` | `string` | "formal", "neutral", "informal" |
| `register_consistency` | `number` | 0-1 |
| `shifts` | `RegisterShift[]` | Cambios de registro |

**RegisterShift:**
```json
{
  "chapter": 5,
  "from_register": "formal",
  "to_register": "informal",
  "severity": "medium",
  "example": "De repente pasó de 'estimado señor' a 'tío, qué pasa'"
}
```

### `GET /api/projects/{project_id}/register-analysis/genre-comparison`

Compara registro del manuscrito con géneros literarios típicos.

**Response data:**
| Campo | Tipo |
|-------|------|
| `detected_genre` | `string` | Género más probable |
| `genre_scores` | `object` | `{genre: score}` |
| `recommendations` | `string[]` |

---

## Corrección de Hablantes

### `GET /api/projects/{project_id}/speaker-corrections`

Lista correcciones manuales de atribución de diálogo.

**Response data:** `SpeakerCorrection[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `project_id` | `number` |
| `chapter` | `number` |
| `quote_text` | `string` |
| `detected_speaker_id` | `number?` |
| `corrected_speaker_id` | `number` |
| `created_at` | `string` |

### `POST /api/projects/{project_id}/speaker-corrections`

Crea una corrección de hablante.

**Body (JSON):**
```json
{
  "chapter": 3,
  "quote_text": "No puedo creerlo",
  "detected_speaker_id": 5,
  "corrected_speaker_id": 7
}
```

### `DELETE /api/projects/{project_id}/speaker-corrections/{correction_id}`

Elimina una corrección de hablante.

---

## Focalización (Point of View)

### `GET /api/projects/{project_id}/focalization`

Obtiene declaraciones de punto de vista (POV).

**Response data:** `FocalizationDeclaration[]`

| Campo | Tipo |
|-------|------|
| `id` | `number` |
| `project_id` | `number` |
| `chapter_start` | `number` |
| `chapter_end` | `number?` |
| `pov_character_id` | `number?` |
| `pov_type` | `string` | "first_person", "third_limited", "omniscient" |
| `notes` | `string?` |

### `POST /api/projects/{project_id}/focalization`

Declara el POV de un capítulo o rango de capítulos.

**Body (JSON):**
```json
{
  "chapter_start": 1,
  "chapter_end": 5,
  "pov_character_id": 3,
  "pov_type": "third_limited",
  "notes": "Narración desde perspectiva de María"
}
```

### `PUT /api/projects/{project_id}/focalization/{declaration_id}`

Actualiza una declaración de POV.

### `DELETE /api/projects/{project_id}/focalization/{declaration_id}`

Elimina una declaración de POV.

### `GET /api/projects/{project_id}/focalization/violations`

Detecta violaciones de POV declarado.

**Response data:** `POVViolation[]`

| Campo | Tipo |
|-------|------|
| `chapter` | `number` |
| `declaration_id` | `number` |
| `declared_pov` | `string` |
| `violation_type` | `string` |
| `text_excerpt` | `string` |
| `explanation` | `string` |
| `severity` | `string` |

**Violation Types:**
- `omniscient_in_limited` — Conocimiento imposible en third_limited
- `wrong_pov_character` — Narración desde personaje incorrecto
- `first_to_third_shift` — Cambio first → third person
- `head_hopping` — Salto entre mentes en mismo capítulo

---

## Errores Comunes

### Error: No pasar el archivo correctamente

**Incorrecto (JavaScript):**
```javascript
fetch('/api/projects', {
  method: 'POST',
  body: JSON.stringify({ name: 'Test', file: fileObject })  // Error!
})
```

**Correcto:**
```javascript
const formData = new FormData()
formData.append('name', 'Test')
formData.append('file', fileObject)

fetch('/api/projects', {
  method: 'POST',
  body: formData  // Sin Content-Type, el navegador lo añade
})
```

### Error: No verificar success en respuesta

**Incorrecto:**
```javascript
const response = await fetch('/api/projects/1')
const data = await response.json()
console.log(data.data.name)  // Puede fallar si success=false
```

**Correcto:**
```javascript
const response = await fetch('/api/projects/1')
const data = await response.json()
if (data.success) {
  console.log(data.data.name)
} else {
  console.error(data.error)
}
```

### Error: Endpoints incorrectos

| Incorrecto | Correcto |
|------------|----------|
| `/api/project/1` | `/api/projects/1` |
| `/api/projects/1/entity` | `/api/projects/1/entities` |
| `/api/projects/1/alert` | `/api/projects/1/alerts` |
| `/api/analysis/1/progress` | `/api/projects/1/analysis/progress` |
