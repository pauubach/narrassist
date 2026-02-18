# Atributos Ambiguos - Guía Técnica

## Introducción

El sistema de **Atributos Ambiguos** permite detectar y resolver casos donde la propiedad de un atributo físico o descriptivo no puede determinarse automáticamente debido a la estructura sintáctica del texto.

En lugar de realizar una asignación incorrecta por proximidad, el sistema genera una **alerta interactiva** que pregunta al usuario a qué entidad pertenece el atributo.

---

## Problema que resuelve

### Ejemplo real

```
Texto: "Cuando Juan conoció a María tenía los ojos azules."
```

**Ambigüedad**: ¿Quién tenía los ojos azules? ¿Juan o María?

**Comportamiento anterior** (antes de este feature):
- El sistema asignaba el atributo por proximidad → `María.eye_color = azules` (INCORRECTO)
- Resultado: Inconsistencias silenciosas en la base de datos de personajes

**Comportamiento actual** (con este feature):
- El sistema detecta la ambigüedad sintáctica
- NO asigna el atributo automáticamente
- Genera alerta interactiva pidiendo al usuario que seleccione el propietario correcto
- Resultado: Datos precisos, sin falsas atribuciones

---

## Patrones de Ambigüedad Detectados

El sistema detecta 3 patrones sintácticos sistemáticos que generan ambigüedad:

### 1. Subordinada temporal con "cuando X verbo a Y"

```python
# Patrón: cuando X verbo a Y, tenía/tenían atributo
"Cuando Juan conoció a María tenía los ojos azules."
"Cuando Pedro vio a Elena tenía el cabello largo."
```

**Causa de ambigüedad**: El sujeto de "tenía" puede ser X o Y.

### 2. Posesivo "sus" + clítico neutro "le"

```python
# Patrón: X verbo a Y. Sus atributo le verbo
"María saludó a Juan. Sus ojos azules le llamaron la atención."
```

**Causa de ambigüedad**: "Sus" es ambiguo (¿de María o de Juan?), y "le" no marca género.

### 3. Subordinada completiva con "le dijo que tenía"

```python
# Patrón: X le dijo a Y que tenía atributo
"Juan le dijo a María que tenía el pelo sucio."
```

**Causa de ambigüedad**: "tenía" puede referirse a X (Juan) o Y (María).

---

## Arquitectura del Sistema

### Flujo end-to-end

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Texto en manuscrito                                          │
│    "Cuando Juan conoció a María tenía los ojos azules."         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. AttributeExtractor extrae atributos                          │
│    - Detecta "ojos azules" en posición 38-49                    │
│    - Llama a ScopeResolver para asignar entity                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ScopeResolver._is_ambiguous_context()                        │
│    - Analiza sintaxis: detecta patrón "cuando X conoció a Y"    │
│    - Encuentra 2 candidatos: ["Juan", "María"]                  │
│    - Retorna AmbiguousResult (NO None, NO asignación errónea)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. AttributeExtractor NO asigna el atributo                     │
│    - Crea AmbiguousAttribute con:                               │
│      * attribute_key = "eye_color"                              │
│      * attribute_value = "azules"                               │
│      * candidates = ["Juan", "María"]                           │
│      * source_text = "Cuando Juan conoció a María tenía..."     │
│    - Agrega a AttributeExtractionResult.ambiguous_attributes    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. AnalysisPipeline.STEP 8a                                     │
│    - _create_alerts_from_ambiguous_attributes()                 │
│    - Resuelve entity_name -> entity_id para cada candidato      │
│    - Llama a AlertEngine.create_from_ambiguous_attribute()      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. AlertEngine crea alerta con extra_data                       │
│    {                                                             │
│      "attribute_key": "eye_color",                              │
│      "attribute_value": "azules",                               │
│      "candidates": [                                             │
│        {"entity_name": "Juan", "entity_id": 5},                 │
│        {"entity_name": "María", "entity_id": 8}                 │
│      ],                                                          │
│      "source_text": "Cuando Juan conoció a María tenía..."      │
│    }                                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Frontend muestra alerta interactiva                          │
│    - Título: "¿Quién tiene color de ojos azules?"              │
│    - Contexto: "Cuando Juan conoció a María tenía los ojos..." │
│    - Botones: [Juan] [María] [No asignar]                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Usuario selecciona: Juan                                     │
│    POST /api/projects/123/alerts/456/resolve-attribute          │
│    { "entity_id": 5 }                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. API asigna atributo con alta confianza                       │
│    entity_repository.create_attribute(                          │
│      entity_id=5,  # Juan                                       │
│      attribute_key="eye_color",                                 │
│      attribute_value="azules",                                  │
│      confidence=0.9  # Alta: confirmado por usuario             │
│    )                                                             │
│    alert.status = RESOLVED                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Componentes Clave

### Backend

#### 1. `scope_resolver.py` - Detección de Ambigüedad

```python
@dataclass
class AmbiguousResult:
    """Retornado cuando atribución es genuinamente ambigua."""
    candidates: list[str]  # Nombres de entidades candidatas
    position: int          # Posición del atributo en el texto
    context_text: str      # Oración ambigua completa
```

**Función principal**: `_is_ambiguous_context(position, entity_mentions) -> tuple[list[str], str] | None`

Detecta los 3 patrones de ambigüedad mediante análisis sintáctico con spaCy.

#### 2. `attributes.py` - Recolección de Atributos Ambiguos

```python
@dataclass
class AmbiguousAttribute:
    """Atributo cuya propiedad es ambigua."""
    attribute_key: str       # "eye_color", "hair_color", etc.
    attribute_value: str     # "azules", "rizado", etc.
    candidates: list[str]    # Nombres de entidades candidatas
    source_text: str         # Oración ambigua
    start_char: int
    end_char: int
    chapter_id: int | None
```

Agregado a `AttributeExtractionResult.ambiguous_attributes`.

#### 3. `analysis_pipeline.py` - Creación de Alertas

`_create_alerts_from_ambiguous_attributes(project_id, ambiguous_attrs)`:
- Resuelve `entity_name` → `entity_id` desde `entity_repository`
- Llama a `AlertEngine.create_from_ambiguous_attribute()`

#### 4. `alerts/engine.py` - Factory Method

`create_from_ambiguous_attribute()`:
- Crea alerta tipo `"ambiguous_attribute"`
- Categoría: `CONSISTENCY`, Severidad: `WARNING`
- `extra_data` contiene `candidates` con `entity_id` para resolución

#### 5. `api-server/routers/alerts.py` - Endpoint de Resolución

```python
@router.post("/api/projects/{project_id}/alerts/{alert_id}/resolve-attribute")
def resolve_ambiguous_attribute(
    project_id: int,
    alert_id: int,
    body: ResolveAmbiguousAttributeRequest  # { entity_id: int | None }
):
    # Si entity_id = None → "No asignar"
    # Si entity_id = 5 → Crear atributo con confidence=0.9
    # Marcar alerta como RESOLVED
```

### Frontend

#### 1. `types/domain/alerts.ts` - Tipos TypeScript

```typescript
export interface AlertExtraData {
  attributeValue?: string
  candidates?: Array<{ entityName: string; entityId: number }>
  sourceText?: string
  // ...
}
```

#### 2. `AlertModal.vue` y `AlertInspector.vue` - UI Interactiva

```vue
<div v-if="isAmbiguousAttribute && alert.status === 'active'" class="ambiguous-actions">
  <!-- Contexto ambiguo -->
  <div v-if="alert.extraData?.sourceText" class="ambiguous-context">
    <i class="pi pi-info-circle"></i>
    <span class="context-text">{{ alert.extraData.sourceText }}</span>
  </div>

  <!-- Pregunta -->
  <p class="ambiguous-label">¿Quién tiene este atributo?</p>

  <!-- Botones de candidatos -->
  <div class="candidate-buttons">
    <Button
      v-for="candidate in ambiguousCandidates"
      :key="candidate.entityId"
      :label="candidate.entityName"
      severity="info"
      outlined
      @click="resolveWithCandidate(candidate.entityId)"
    />
    <Button
      label="No asignar"
      severity="secondary"
      text
      @click="resolveAsUnassigned"
    />
  </div>
</div>
```

#### 3. `ProjectDetailView.vue` - Handler de Resolución

```typescript
const onResolveAmbiguousAttribute = async (alert: Alert, entityId: number | null) => {
  await api.postRaw(
    `/api/projects/${projectId}/alerts/${alert.id}/resolve-attribute`,
    { entity_id: entityId }
  )
  await loadAlerts(projectId)
  toast.add({ severity: 'success', summary: 'Resuelto', detail: message })
}
```

---

## Mensajes de Alerta

### Título
```
¿Quién tiene color de ojos azules?
```

### Descripción
```
No se puede determinar automáticamente a quién pertenece este atributo.
Candidatos: Juan, María.
```

### Explicación
```
El contexto «Cuando Juan conoció a María tenía los ojos azules» no permite
determinar con certeza el propietario del atributo. Por favor, seleccione
la entidad correcta.
```

### Sugerencia
```
Seleccione quién tiene color de ojos azules, o marque como 'No asignar'
si ningún candidato es correcto
```

---

## Content Hash

Las alertas de atributos ambiguos tienen un `content_hash` determinista que permite:
- **Deduplicación**: Evitar alertas duplicadas en re-análisis
- **Persistencia**: La misma ambigüedad genera el mismo hash entre ejecuciones

```python
# En alerts/models.py::compute_content_hash()
elif self.alert_type == "ambiguous_attribute":
    ed = self.extra_data
    candidates = ed.get("candidates", [])
    candidate_names = sorted([c.get("entity_name", "") for c in candidates])
    parts.extend([
        ed.get("attribute_key", ""),
        ed.get("attribute_value", ""),
        str(candidate_names),  # Ordenados para determinismo
    ])
```

**Hash = `sha256(project_id | alert_type | attribute_key | attribute_value | sorted(candidates))[:16]`**

---

## Testing

### Tests Unitarios

**`test_scope_adversarial_r2.py::TestAmbiguityDetection`** (5 tests):
- `test_cuando_conocio_a_tenia_cabello`: Patrón "cuando X conoció a Y tenía"
- `test_cuando_vio_a_tenia_ojos`: Variante con "vio"
- `test_sus_ojos_le_llamaron_la_atencion`: Patrón "sus + le"
- `test_le_dijo_que_tenia_pelo`: Patrón "le dijo que tenía"
- `test_cuando_se_conocieron_tenia`: Ambigüedad con verbo recíproco

Todos verifican:
```python
assert isinstance(result, AmbiguousResult)
assert set(result.candidates) == {"Juan", "María"}
assert "atributo" in result.context_text.lower()
```

### Tests de Integración

**`test_ambiguous_attribute_flow.py`**:
- `test_scope_resolver_returns_ambiguous_result`: ScopeResolver detecta ambigüedad
- `test_ambiguous_result_propagates_through_attribute_extraction`: Propagación sin asignación incorrecta
- `test_alert_creation_from_ambiguous_attribute`: Estructura de alerta correcta

---

## Casos de Uso

### 1. Manuscrito con diálogo ambiguo

```
Juan le dijo a Pedro que tenía el pelo sucio.
```

**Sistema**:
- Detecta ambigüedad: ¿quién tiene el pelo sucio? (Juan o Pedro)
- Genera alerta interactiva
- Usuario selecciona: Pedro
- Resultado: `Pedro.hair_state = "sucio"` con `confidence=0.9`

### 2. Descripción con pronombre posesivo

```
María saludó a Ana. Sus ojos verdes brillaban bajo la luz.
```

**Sistema**:
- Detecta ambigüedad: "sus" puede referirse a María o Ana
- Genera alerta interactiva
- Usuario selecciona: María
- Resultado: `María.eye_color = "verdes"` con `confidence=0.9`

### 3. Usuario marca "No asignar"

```
Cuando el detective interrogó al sospechoso tenía los ojos inyectados en sangre.
```

**Sistema**:
- Detecta ambigüedad: detective vs sospechoso
- Usuario selecciona: **No asignar** (porque ambos podrían tenerlo)
- Resultado: Alerta marcada como `RESOLVED`, NO se crea atributo
- `alert.resolution_note = "Usuario eligió no asignar el atributo"`

---

## Limitaciones y Trabajo Futuro

### Limitaciones Actuales

1. **Solo 3 patrones sintácticos**: No cubre TODOS los casos de ambigüedad (ej: elipsis, anáfora cero)
2. **Dependencia de NER**: Si spaCy no detecta una entidad, no se incluye como candidato
3. **Contexto de una oración**: No considera contexto discursivo más amplio

### Trabajo Futuro

1. **Análisis semántico con LLM**: Usar Ollama para desambiguar casos complejos
2. **Memoria contextual**: Recordar atributos previamente asignados para inferencia
3. **Sugerencia por defecto**: Basada en género gramatical o saliencia de entidad
4. **Batch resolution**: Permitir resolver múltiples atributos ambiguos a la vez

---

## Referencias

- [scope_resolver.py](../src/narrative_assistant/nlp/scope_resolver.py) - Detección de ambigüedad
- [attributes.py](../src/narrative_assistant/nlp/attributes.py) - Recolección de atributos ambiguos
- [analysis_pipeline.py](../src/narrative_assistant/pipelines/analysis_pipeline.py) - STEP 8a
- [alerts/engine.py](../src/narrative_assistant/alerts/engine.py) - `create_from_ambiguous_attribute()`
- [alerts/models.py](../src/narrative_assistant/alerts/models.py) - `content_hash` para `ambiguous_attribute`
- [api-server/routers/alerts.py](../api-server/routers/alerts.py) - Endpoint `/resolve-attribute`
- [AlertModal.vue](../frontend/src/components/modals/AlertModal.vue) - UI de resolución
- [test_scope_adversarial_r2.py](../tests/unit/test_scope_adversarial_r2.py) - Tests de ambigüedad

---

## Mejoras Post-Implementación

Después del Sprint S20 (implementación inicial), se añadieron 3 mejoras para optimizar la experiencia de usuario:

### 1. Sugerencia Contextual Basada en Atributos Existentes

**Problema**: El usuario debe revisar todos los candidatos sin contexto previo.

**Solución**: Si un candidato ya tiene el mismo atributo asignado (ej: `Juan.eye_color = "azules"`), se marca como sugerido.

**Implementación**:
- En `create_from_ambiguous_attribute()` ([alerts/engine.py](../src/narrative_assistant/alerts/engine.py)):
  - Consulta `entity_repository.get_attributes_by_entity()` para cada candidato
  - Compara `attribute_key` y `attribute_value` (normalizado)
  - Marca candidato con `suggested: true` si coincide
  - Agrega `suggested_entity_id` a `extra_data`
- Frontend ordena candidatos sugeridos primero
- UI muestra "(Recomendado)" con severidad `success`

**Beneficio**: Reduce carga cognitiva, especialmente cuando un personaje ya tiene el atributo definido.

**Test**: `test_ambiguous_enhancements.py::TestContextualSuggestion`

---

### 2. Batch Resolution de Alertas Ambiguas

**Problema**: Resolver alertas una por una es tedioso en manuscritos con muchas ambigüedades.

**Solución**: Endpoint `POST /api/projects/{id}/alerts/batch-resolve-attributes` permite resolver múltiples alertas en una sola petición.

**Implementación**:
- Nuevos modelos Pydantic en [api-server/deps.py](../api-server/deps.py):
  ```python
  class AmbiguousAttributeResolution(BaseModel):
      alert_id: int
      entity_id: int | None  # None = "No asignar"

  class BatchResolveAmbiguousAttributesRequest(BaseModel):
      resolutions: list[AmbiguousAttributeResolution] = Field(..., min_length=1)
  ```
- Endpoint en [api-server/routers/alerts.py](../api-server/routers/alerts.py):
  - Itera sobre `resolutions`
  - Valida cada alerta (ownership, tipo, candidatos)
  - Crea atributos con `confidence=0.9`
  - Marca alertas como `RESOLVED`
  - Retorna estadísticas: `{resolved: N, skipped: M, errors: [...]}`

**Beneficio**: Permite workflows futuros como "Resolver todas las seleccionadas" o "Resolver todas con sugerencia automática".

**Test**: `test_ambiguous_enhancements.py::TestBatchResolution`

---

### 3. Desambiguación Semántica con LLM (Ollama)

**Problema**: Los 3 patrones sintácticos no cubren TODOS los casos de ambigüedad. Algunos casos requieren análisis semántico.

**Solución**: Usar Ollama (si disponible) para desambiguar casos complejos antes de generar alerta.

**Implementación**:
- Nuevo método `_llm_semantic_disambiguation()` en [scope_resolver.py](../src/narrative_assistant/nlp/scope_resolver.py):
  1. Verifica disponibilidad de Ollama con `get_llm_client().is_available()`
  2. Extrae contexto de 300 caracteres antes/después
  3. Identifica texto del atributo (span de 2-5 tokens)
  4. Limita a 2-3 candidatos más probables por proximidad
  5. Envía prompt a LLM: *"¿A quién se refiere 'ojos azules'? Candidatos: Juan, María"*
  6. Procesa respuesta: si LLM responde con nombre de candidato → `(entity_name, 0.65)`
  7. Si LLM responde "AMBIGUO" o no hay match → `None`
- Integrado en `find_nearest_entity_by_scope()` en 2 puntos:
  - **Después de paragraph scope**: Si `confidence < 0.6`, intenta LLM antes de fallar
  - **Antes de fallback final**: Si no hay candidatos claros, intenta LLM como último recurso
- **Graceful degradation**: Si Ollama no disponible, retorna `None` sin crashear

**Configuración**:
- Requiere Ollama corriendo (`ollama serve`)
- Modelo recomendado: `llama3.2` (3B, funciona en CPU)
- Para hardware limitado: usar `scripts/start_ollama_cpu.bat` (fuerza CPU)

**Beneficio**: Mejora precisión en casos donde sintaxis no es suficiente, pero NO genera alertas si LLM no está disponible (respeta limitaciones de hardware).

**Test**: `test_ambiguous_enhancements.py::TestLLMSemanticDisambiguation`

---

## ROI de las Mejoras

| Mejora | Complejidad | Impacto | ROI |
|--------|-------------|---------|-----|
| Sugerencia contextual | Baja (1 consulta DB) | Alto (reduce decisiones) | ⭐⭐⭐⭐⭐ |
| Batch resolution | Media (nuevo endpoint) | Medio (workflow futuro) | ⭐⭐⭐⭐ |
| LLM semántico | Alta (integración LLM) | Medio (casos edge) | ⭐⭐⭐ |

---

**Última actualización**: 2026-02-18
**Versión**: 0.6.1 (post-implementación de atributos ambiguos + 3 mejoras)
