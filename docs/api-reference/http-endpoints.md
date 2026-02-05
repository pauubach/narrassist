# HTTP API Endpoints

Base URL: `http://localhost:8008/api`

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

## LLM / Expectativas

### `GET /api/llm/status`

Verifica disponibilidad de todos los backends LLM.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `available` | `boolean` | Algún LLM disponible |
| `backend` | `string` | "llamacpp" \| "ollama" \| "transformers" \| "none" |
| `model` | `string?` | Modelo activo |
| `available_methods` | `string[]` | Métodos disponibles |
| `ollama_models` | `string[]` | Modelos Ollama |
| `llamacpp_models` | `string[]` | Modelos llama.cpp |
| `backends` | `object` | Estado de cada backend |
| `message` | `string` | Mensaje descriptivo |

### `GET /api/llamacpp/status`

Estado detallado de llama.cpp.

**Response data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | `string` | "not_installed" \| "installed" \| "running" \| "error" |
| `is_installed` | `boolean` | Binario instalado |
| `is_running` | `boolean` | Servidor activo |
| `host` | `string` | URL del servidor |
| `port` | `number` | Puerto |
| `downloaded_models` | `string[]` | Modelos descargados |
| `available_models` | `LlamaCppModel[]` | Modelos disponibles para descargar |

### `POST /api/llamacpp/install`

Instala el binario llama-server (~50MB).

### `POST /api/llamacpp/download/{model_name}`

Descarga un modelo GGUF.

**Path params:**
- `model_name`: "llama-3.2-3b" | "qwen2.5-7b" | "mistral-7b"

### `POST /api/llamacpp/start`

Inicia el servidor llama.cpp.

### `POST /api/llamacpp/stop`

Detiene el servidor llama.cpp.

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
