# Auditoría Técnica: Entidades, Timeline y Atributos

Fecha: 2026-02-13
Estado revisado: `HEAD a1badba` (incluye `10c2733`)
Verificación independiente: 2026-02-13 (Claude Code, post-commit `2cbe8c6`)

## Alcance y objetivo

Este documento revisa, con foco técnico y funcional:

1. Detección de entidades y su impacto en timeline.
2. Extracción y asignación de atributos (personajes, lugares, objetos, etc.).
3. Lógica temporal para casos extremos (viajes temporales, desfases, calendarios).
4. UX/UI de timeline y edición de atributos.
5. Cobertura de tests y riesgos de regresión.
6. Robustez de rendimiento y memoria (Windows/Mac).

## Resumen ejecutivo

Fortalezas actuales:

- La base temporal ha mejorado de forma real: `day_offset`/`weekday` ya fluye backend->frontend (`src/narrative_assistant/temporal/timeline.py:1022`, `frontend/src/types/transformers/timeline.ts:31`).
- Hay protección de rendimiento para timelines grandes (limitado a 5000 eventos y aviso de truncado) (`api-server/routers/chapters.py:431`, `frontend/src/components/timeline/TimelineView.vue:147`).
- Hay cobertura unitaria sólida para `TemporalMap`, incluyendo instancias temporales (`tests/unit/test_temporal_map.py:275`).
- Existe hardening de GPU/VRAM para evitar cuelgues en hardware problemático (`src/narrative_assistant/core/device.py:12`, `src/narrative_assistant/core/device.py:411`).

Riesgos principales aún abiertos:

- `temporal_instance_id` está modelado/persistido, pero no se asigna al construir eventos de timeline.
- `vital_status` registra muertes sin instancia temporal, rompiendo casos "mismo personaje, dos edades".
- La extracción de atributos sigue sesgada a persona y deja fuera gran parte de atributos de lugares/objetos.
- Hay incoherencias entre UI de edición de atributos y taxonomía real de tipos de entidad.
- ~~Falta cobertura de tests en endpoint timeline por entidad y en semántica temporal de frontend.~~ Parcialmente cubierto con tests de `TemporalMap` e instancias temporales.

---

## Actualización post-fix (2026-02-13)

Estado de implementación tras esta ronda (sin commit):

| ID | Estado anterior | Estado actual | Evidencia de implementación |
|----|-----------------|---------------|-----------------------------|
| F1 | Pendiente | **Parcial (alto avance)** | `TemporalMarker` ahora soporta `temporal_instance_id` y se materializa en eventos (`src/narrative_assistant/temporal/markers.py`, `src/narrative_assistant/temporal/timeline.py`, `api-server/routers/chapters.py`). Cobertura: `tests/unit/test_temporal.py::test_extract_with_entities_sets_temporal_instance_id`, `tests/unit/test_temporal.py::test_temporal_instance_id_propagates_to_events_and_json`. |
| F2 | Parcial | **Corregido** | `vital_status` detecta instancia temporal explícita (edad/año), la registra en `TemporalMap` y la usa en alive-check (`src/narrative_assistant/analysis/vital_status.py`). Cobertura: `tests/unit/test_vital_status.py::test_death_registers_temporal_instance_when_age_is_explicit`. |
| F3 | Pendiente | **Parcial (avance estructural)** | Se propaga `entity_type` en pipelines (`src/narrative_assistant/pipelines/ua_deep_extraction.py`, `src/narrative_assistant/pipelines/analysis_pipeline.py`), se elimina sesgo persona cuando hay tipos explícitos (`src/narrative_assistant/nlp/attributes.py`) y se enruta por clase de entidad en embeddings. |
| F4 | Pendiente | **Corregido** | `_map_attribute_key` y `_extract_value_from_sentence` ahora soportan `climate/terrain/size/location` + material/color/condition (`src/narrative_assistant/nlp/attributes.py`). Cobertura: `tests/unit/test_attributes.py::TestAttributeExtractorNonPerson`. |
| F6 | Pendiente | **Corregido** | UI timeline ahora muestra instancia temporal (badge/tip) y permite filtrar por instancia (`frontend/src/components/timeline/TimelineEvent.vue`, `frontend/src/components/timeline/TimelineView.vue`, `frontend/src/components/timeline/VisTimeline.vue`). |
| F8 | Pendiente | **Corregido** | Config de categorías unificada y compartida (`frontend/src/config/attributes.ts`), selector habilitado en `CharacterView`, y validación backend por tipo (`frontend/src/views/CharacterView.vue`, `frontend/src/components/CharacterSheet.vue`, `api-server/deps.py`, `api-server/routers/entities.py`). Cobertura API: `tests/unit/test_entities_attribute_validation.py`. |
| F9 | Pendiente | **Corregido** | `_infer_category/_infer_key` ahora son sensibles a `entity_type`, con defaults útiles para `LOC` y `OBJECT` (`src/narrative_assistant/nlp/attr_entity_resolution.py`, llamadas en `src/narrative_assistant/nlp/attributes.py`). |

### Limitación residual principal

- F1 no está al 100% semántico: la detección de instancia temporal cubre casos explícitos (edad/año + mención asociada), pero no todos los casos implícitos narrativos complejos. La infraestructura ya quedó conectada end-to-end; el siguiente salto es NLP semántico avanzado.

### Validación ejecutada en esta ronda

- `pytest tests/unit/test_temporal.py tests/unit/test_vital_status.py tests/unit/test_entities_attribute_validation.py tests/unit/test_entities_timeline_endpoint.py -q` → **102 passed**
- `pytest tests/unit/test_attributes.py::TestAttributeExtractorNonPerson -m heavy -q` → **4 passed**
- `npm run test:run` (frontend) → **450 passed** (se mantienen warnings conocidos de `happy-dom` al final, sin fallo de salida)
- `npm run build` (frontend) → **OK**
- `python -m py_compile ...` sobre módulos modificados de Python/API/tests → **OK**

## Verificación independiente — estado por hallazgo

| ID | Hallazgo | Verificación | Estado |
|----|----------|-------------|--------|
| F1 | `temporal_instance_id` no se materializa | **CONFIRMADO** | Pendiente — requiere detección NLP |
| F2 | Muerte sin instancia temporal | **CONFIRMADO** | Parcial — `TemporalMap` ya soporta, falta `vital_status` |
| F3 | Sesgo a "persona" en atributos | **CONFIRMADO** | Pendiente — refactor atributos |
| F4 | Claves de lugar sin implementar | **CONFIRMADO** | Pendiente — refactor atributos |
| F5 | Sort comparator roto (storyDate/dayOffset) | **CONFIRMADO** | **CORREGIDO** |
| F6 | `temporalInstanceId` sin uso en UI | **CONFIRMADO** | Pendiente — depende de F1 |
| F7 | Endpoint entity timeline básico | **PARCIAL** | Bajo riesgo real |
| F8 | CharacterSheet vs CharacterView | **CONFIRMADO** | Pendiente — sprint UI |
| F9 | Defaults "physical/other" para no-persona | **PARCIAL** (default es SOCIAL, no PHYSICAL) | Pendiente — refactor atributos |

---

## Hallazgos críticos (P0/P1)

### F1. `temporal_instance_id` no se materializa en eventos

Evidencia:

- Campo existe en modelo/export: `src/narrative_assistant/temporal/timeline.py:91`, `src/narrative_assistant/temporal/timeline.py:1023`.
- Persistencia lista para guardarlo: `src/narrative_assistant/persistence/timeline.py:35`, `src/narrative_assistant/persistence/timeline.py:217`.
- Frontend lo transforma: `frontend/src/types/transformers/timeline.ts:35`.
- Pero los constructores de eventos no lo asignan: `src/narrative_assistant/temporal/timeline.py:249`, `src/narrative_assistant/temporal/timeline.py:335`, `src/narrative_assistant/temporal/timeline.py:476`, `src/narrative_assistant/temporal/timeline.py:574`.

Impacto:

- Casos de viaje temporal tipo `A@40` y `A@45` no quedan representados en timeline operativo, aunque el esquema lo soporte.
- La UI no puede diferenciar instancias temporales porque no llegan con valor útil.

Verificación: **CONFIRMADO**. Los 4 constructores de `TimelineEvent` nunca asignan `temporal_instance_id`. El campo viaja vacío por toda la stack (backend → API → transformer → frontend). La infraestructura completa está lista (modelo, persistencia, tipos, transformer), pero falta la pieza clave: que el NLP detecte y asigne instancias.

Estado: La infraestructura de transporte está completa (añadida en sprint timeline). Falta la detección NLP.

Plan de solución:

1. **Detección**: Añadir detector de instancias temporales en `temporal/markers.py` que identifique patrones como "Juan a los 40 años" / "el joven Juan" / "Juan en 1985" y genere un `temporal_instance_id` (ej: `"Juan@40"`, `"Juan@1985"`).
2. **Asignación**: En los 4 constructores de `TimelineEvent`, consultar el `TemporalMap` para obtener la instancia temporal de la entidad en ese capítulo/slice.
3. **Propagación**: El campo ya se exporta, persiste y transforma — solo hay que popularlo.
4. **Riesgo**: La detección de instancias temporales es un problema NLP difícil (requiere comprensión semántica profunda). Primera iteración puede limitarse a patrones explícitos (`@edad`, `en YYYY`) y dejar los implícitos para LLM.

### F2. Muerte por personaje sin distinguir instancia temporal

Evidencia:

- Registro de muerte sin `temporal_instance_id`: `src/narrative_assistant/analysis/vital_status.py:316`.
- `TemporalMap` sí soporta instancia temporal: `src/narrative_assistant/temporal/temporal_map.py:162`, `src/narrative_assistant/temporal/temporal_map.py:257`.

Impacto:

- Si muere `A@45`, puede marcarse como muerto el canónico y producir falsos positivos con `A@40`.
- Riesgo narrativo alto en historias con desdobles temporales.

Verificación: **CONFIRMADO**. `vital_status.py:316` llama `register_death(entity_id, chapter)` sin pasar `temporal_instance_id`. El `TemporalMap` ya soporta muerte por instancia (añadido en sprint timeline con tests en `test_temporal_map.py:TestTemporalInstances`), pero el módulo de análisis no lo usa.

Estado: `TemporalMap.register_death()` ya acepta `temporal_instance_id` opcional. `is_character_alive_in_chapter()` ya consulta por instancia con fallback a canónico. Falta que `vital_status.py` propague el dato.

Plan de solución:

1. **Corto plazo**: Modificar `vital_status.py:316` para pasar `temporal_instance_id` cuando esté disponible en el evento de muerte. Si no hay instancia, mantener comportamiento actual (muerte canónica).
2. **Medio plazo**: Depende de F1 — sin detección de instancias, no hay `temporal_instance_id` que propagar. Es un cambio de ~5 líneas una vez F1 esté resuelto.

### F3. Sesgo estructural a "persona" en extracción de atributos

Evidencia:

- Si no hay tipo de entidad, se asume persona: `src/narrative_assistant/nlp/attributes.py:544`.
- Filtros reiterados a persona: `src/narrative_assistant/nlp/attributes.py:1700`, `src/narrative_assistant/nlp/attributes.py:2367`, `src/narrative_assistant/nlp/attributes.py:2719`.
- Prompt LLM enfocado en personajes: `src/narrative_assistant/nlp/attributes.py:1707`, `src/narrative_assistant/nlp/attributes.py:1717`.
- Descripciones canónicas de embeddings centradas en físico/psicológico/social de personaje: `src/narrative_assistant/nlp/attributes.py:1812`.
- Menciones en pipeline aún en 3-tupla sin tipo: `src/narrative_assistant/pipelines/ua_deep_extraction.py:82`, `src/narrative_assistant/pipelines/analysis_pipeline.py:1453`.

Impacto:

- Lugares/objetos pueden recibir `physical/other` o quedarse sin extracción útil.
- Se limita valor editorial en worldbuilding (escenario, ambientación, objetos relevantes).

Verificación: **CONFIRMADO al 100%**. Cada línea referenciada es precisa:

- `_is_person_entity(None)` retorna `True` — toda entidad sin tipo se trata como persona.
- `_is_location_entity()` existe (línea 549) pero **nunca se llama** en todo el archivo.
- Los regex de lugar/clima/terreno existen en `ATTRIBUTE_PATTERNS` (líneas 1258-1284) pero se filtran antes de llegar a entidades no-persona por los filtros en líneas 1700/2367/2719.
- Los pipelines pasan 3-tuplas `(name, start, end)` sin tipo. La normalización en `attributes.py:527` añade `None` como tipo → `_is_person_entity(None)` → persona.

Es un sesgo profundo y multicapa: no basta con cambiar un default, hay que intervenir en 5+ puntos.

Plan de solución:

1. **Paso 1 — Propagar tipo de entidad en menciones**: Cambiar 3-tuplas `(name, start, end)` a 4-tuplas `(name, start, end, entity_type)` en `ua_deep_extraction.py:82` y `analysis_pipeline.py:1453`. Actualizar normalización en `attributes.py:527`.
2. **Paso 2 — Bifurcar extracción por tipo**: En lugar de filtrar con `_is_person_entity()`, crear ramas: persona → prompt persona actual, lugar → prompt lugar (clima, terreno, tamaño), objeto → prompt objeto (material, estado, propietario).
3. **Paso 3 — Prompts LLM por tipo**: Añadir prompts específicos en `prompts.py` para extracción de atributos de lugar y objeto.
4. **Paso 4 — Embeddings por tipo**: Extender `canonical_descriptions` (línea 1812) con descriptores geográficos y de objeto.
5. **Paso 5 — Activar `_is_location_entity()`**: Usarla en los puntos de decisión para enrutar correctamente.

### F4. Claves de lugar definidas pero no implementadas en mapeo/extracción

Evidencia:

- `AttributeKey` incluye `CLIMATE/TERRAIN/SIZE/LOCATION`: `src/narrative_assistant/nlp/attributes.py:137`.
- `_map_attribute_key` no mapea esas claves: `src/narrative_assistant/nlp/attributes.py:2181`.
- `_extract_value_from_sentence` no extrae esos tipos: `src/narrative_assistant/nlp/attributes.py:2562`.
- Helper de ubicación no se usa en el flujo: `src/narrative_assistant/nlp/attributes.py:549`.

Impacto:

- La taxonomía existe en teoría, pero no en ejecución.
- Escenarios como "el valle era húmedo", "terreno árido", "zona costera" quedan infrautilizados.

Verificación: **CONFIRMADO**. Cada referencia es exacta:

- Las 4 claves existen en el enum pero no aparecen en el `mapping` dict de `_map_attribute_key()` → caen a `AttributeKey.OTHER`.
- `_extract_value_from_sentence()` solo tiene bloques `elif` para 5 keys (hair_color, eye_color, build, personality, profession) — ninguna geográfica.
- Los regex de lugar en `ATTRIBUTE_PATTERNS` (líneas 1258-1284) SÍ existen y detectarían patrones, pero son inalcanzables por el filtro persona de F3.

Hallazgo adicional: Es código fantasma con regex funcionales que nunca se ejecutan. El esfuerzo de implementación ya está parcialmente hecho — solo falta conectarlo.

Plan de solución (ejecutar junto con F3):

1. Añadir `"climate": AttributeKey.CLIMATE`, `"terrain": AttributeKey.TERRAIN`, `"size": AttributeKey.SIZE`, `"location": AttributeKey.LOCATION` al mapping dict de `_map_attribute_key()`.
2. Añadir bloques `elif` en `_extract_value_from_sentence()` para las 4 claves con listas de valores esperados (húmedo/seco/templado/tropical para clima, montañoso/llano/costero para terreno, etc.).
3. Quitar el filtro persona que bloquea los regex de `ATTRIBUTE_PATTERNS` para entidades tipo LOC/GPE.

---

## Hallazgos altos (P1/P2)

### F5. Orden cronológico en UI puede ser inconsistente al mezclar fecha real y dayOffset

Evidencia:

- Comparator actual en lista cronológica: `frontend/src/components/timeline/TimelineView.vue:598`.
- Cuando uno tiene `storyDate` y otro `dayOffset`, el comparator devuelve `-1` en ambos sentidos por la rama de "tiene tiempo conocido": `frontend/src/components/timeline/TimelineView.vue:613`.

Impacto:

- Orden no determinista en algunos datasets mixtos.
- Riesgo UX: eventos "saltan" entre recargas o filtros.

Verificación: **CONFIRMADO**. El comparator original tenía:
```javascript
if (aHasDate || aHasOffset) return -1
if (bHasDate || bHasOffset) return 1
```
Si A tiene `storyDate` y B tiene `dayOffset`, `compare(A,B) = -1` pero `compare(B,A)` también = `-1`. Viola transitividad del sort → orden dependiente de implementación del motor JS.

Estado: **CORREGIDO**. Reemplazado por rank numérico transitivo:
```javascript
const aRank = aHasDate ? 2 : aHasOffset ? 1 : 0
const bRank = bHasDate ? 2 : bHasOffset ? 1 : 0
return bRank - aRank
```
Ahora: eventos con `storyDate` (rank 2) van primero entre sí, luego `dayOffset` (rank 1) entre sí, luego sin tiempo (rank 0). Determinista y transitivo.

### F6. `temporalInstanceId` no se muestra ni explota en UI

Evidencia:

- Solo aparece en tipos/transformer: `frontend/src/types/domain/timeline.ts:40`, `frontend/src/types/transformers/timeline.ts:35`.
- No hay uso en componentes de timeline (`TimelineView`, `TimelineEvent`, `VisTimeline`).

Impacto:

- No hay forma visual de distinguir "misma persona en dos planos temporales".

Verificación: **CONFIRMADO**. El campo viaja por types → transformer pero cero componentes lo leen.

Estado: Depende de F1. Sin detección de instancias, el campo llega como `null` siempre. No tiene sentido añadir UI para un valor que nunca se popula.

Plan de solución (activar cuando F1 esté resuelto):

1. **`TimelineEvent.vue`**: Mostrar badge `@instance` junto al nombre de entidad cuando `temporalInstanceId` no sea null.
2. **`VisTimeline.vue`**: Incluir instancia en tooltip y usar color/icono distinto por instancia.
3. **`TimelineView.vue`**: Permitir filtrar por instancia temporal en los controles.

### F7. Endpoint timeline por entidad es útil pero básico y con riesgo de duplicado

Evidencia:

- Endpoint actual agrupa menciones por capítulo y no usa semántica temporal rica: `api-server/routers/entities.py:901`.
- Mezcla `chapter_id` y `chapter_number` al combinar atributos: `api-server/routers/entities.py:1003`.

Impacto:

- Timeline "de entidad" no refleja story-time real (solo aparición por capítulo).
- Posibles atributos duplicados en casos concretos.

Verificación: **PARCIALMENTE CORRECTO**. El endpoint es básico (confirmado) y el riesgo de duplicado por mezcla `chapter_id`/`chapter_number` es real pero solo se manifiesta con datos inconsistentes entre ambos campos. En la práctica, el riesgo es bajo porque `chapter_id` y `chapter_number` suelen ser coherentes.

Plan de solución:

1. **Corto plazo**: Normalizar la clave de agrupación — usar siempre `chapter_id` como clave primaria, `chapter_number` solo para display.
2. **Medio plazo**: Enriquecer el endpoint con `story_date`/`day_offset` del `TemporalMap` para posicionar menciones en story-time real, no solo por capítulo.

### F8. Incoherencia UI: `CharacterSheet` soporta muchos tipos, diálogo de `CharacterView` no

Evidencia:

- Config amplia por tipo en `CharacterSheet`: `frontend/src/components/CharacterSheet.vue:343`.
- Modal de alta de atributo limitado a `physical/psychological` y deshabilitado: `frontend/src/views/CharacterView.vue:120`, `frontend/src/views/CharacterView.vue:320`.
- Request backend acepta categorías libres sin validación fuerte: `api-server/deps.py:460`.

Impacto:

- Mala experiencia para editor/corrector: la UI sugiere capacidad que luego no se puede operar desde todos los flujos.

Verificación: **CONFIRMADO**. La incoherencia es severa:
- `CharacterSheet.vue:343` define config para 7+ categorías por tipo (character, location, object, organization, event, concept) con categorías como geographic, atmosphere, function, history, temporal, etc.
- `CharacterView.vue:320` tiene solo `[{label: 'Físico', value: 'physical'}, {label: 'Psicológico', value: 'psychological'}]` y el `<Select>` está `disabled`.
- Backend acepta cualquier string como `category` sin enum ni validación.

Plan de solución:

1. **`CharacterView.vue`**: Hacer que `attributeCategories` sea dinámico basado en el tipo de entidad, reutilizando la misma config de `CharacterSheet.vue:343`. Habilitar el `<Select>`.
2. **`deps.py`**: Añadir validación de categoría por tipo de entidad (enum o whitelist configurable).
3. **Extraer config compartida**: Mover `ATTRIBUTE_CONFIG` a un archivo compartido (`frontend/src/config/attributes.ts`) para que tanto `CharacterSheet` como `CharacterView` usen la misma fuente de verdad.

### F9. Inferencia por dependencias aún genera defaults para no-persona

Evidencia:

- `_infer_category` default `PHYSICAL` para adjetivos: `src/narrative_assistant/nlp/attr_entity_resolution.py:612`.
- `_infer_key` default `OTHER`: `src/narrative_assistant/nlp/attr_entity_resolution.py:653`.

Impacto:

- Atributos válidos de entorno/objeto acaban en buckets poco útiles para decisiones editoriales.

Verificación: **PARCIALMENTE CORRECTO**. Correcciones:

- `_infer_category` para adjetivos sí devuelve `PHYSICAL` (línea 613) — correcto.
- Pero el default final (línea 616) es `SOCIAL`, **no** `PHYSICAL` como afirma el documento. Esto es peor para no-personas: un atributo de lugar como "húmedo" caería en `SOCIAL`.
- `_infer_key` sí devuelve `OTHER` (línea 653) — correcto.

Plan de solución (ejecutar junto con F3):

1. **`_infer_category`**: Aceptar `entity_type` como parámetro. Si es lugar → default `GEOGRAPHIC` en vez de `SOCIAL`. Si es objeto → default `PHYSICAL`. Si es persona → mantener lógica actual.
2. **`_infer_key`**: Aceptar `entity_type`. Si es lugar y categoría geográfica → default `LOCATION` en vez de `OTHER`. Si es objeto → default `CONDITION`.

---

## Casos extremos de timeline (estado actual vs esperado)

### Caso 1. Viajero de 40 años que salta +5 años

Esperado:

- Convivencia de `A@40` y `A@45`.
- Compartir identidad canónica, pero con estado temporal independiente (edad, vitalidad, relaciones situadas en story-time).

Estado actual:

- Infraestructura parcial (`temporal_instance_id`) existe en toda la stack, pero no llega al evento operativo (F1/F2/F6).
- `TemporalMap` ya soporta muerte por instancia y alive-check por instancia con fallback a canónico (tests: `test_temporal_map.py:TestTemporalInstances`).

Valoración: La plomería está completa. El cuello de botella es la detección NLP (F1).

### Caso 2. Cambio de huso horario y llegada "antes" por reloj local

Esperado:

- Diferenciar tiempo absoluto (UTC/story-axis) de tiempo civil local (zona y reloj local).

Estado actual:

- `TemporalMarker` no modela timezone/DST (`src/narrative_assistant/temporal/markers.py:49`).
- No hay rastros de soporte `timezone`/`dst` en módulos temporales revisados.

Valoración: Caso real pero de baja frecuencia en narrativa literaria. El 95% de manuscritos no necesita resolución horaria. Si se implementa, debería ser opt-in por proyecto (campo `timezone` en `TemporalMarker` con default `None` = ignorar).

### Caso 3. Día de duración no estándar (DST, vuelos, cruces de fecha)

Esperado:

- Capacidad de representar días de 23h/25h y cambios de fecha por localización.

Estado actual:

- El modelo usa `day_offset` en días enteros; no hay capa de cronometría civil/horaria.

Valoración: Mismo ámbito que Caso 2. Para un asistente de corrección narrativa, la granularidad de "día" es suficiente en el 99% de los casos. Añadir `hour_offset` como campo opcional en `TemporalSlice` cubriría el 1% restante sin romper nada.

### Caso 4. Dilatación temporal por viaje espacial

Esperado:

- Separar tiempo subjetivo del viajero vs tiempo externo del mundo.

Estado actual:

- No existe estructura explícita para dualidad `proper_time` vs `world_time`.

Valoración: Caso de ciencia ficción hard. Relevante para un nicho muy específico. La solución sería el mismo mecanismo de instancias temporales de F1 — el viajero relativista ES una instancia temporal con desfase respecto al mundo. No requiere modelado relativista real, solo la capacidad de asignar tiempos distintos a la misma entidad.

### Caso 5. Planetas con día no-24h o calendarios no gregorianos

Esperado:

- Calendario configurable por mundo narrativo.

Estado actual:

- El sistema está orientado a convención terrestre (día/semana/mes/año).

Valoración: Caso de worldbuilding fantástico. La solución más pragmática es usar `day_offset` como eje temporal abstracto (ya lo es) y permitir que el frontend muestre labels personalizados ("Sol 23" en vez de "Día 23"). No requiere cambio de modelo temporal, solo de presentación.

---

## Revisión de detección de entidades y atributos (funcional/editorial)

### Qué funciona bien

- Pipeline de atributos multi-método con consolidación y evidencias.
- Soporte de tipos de entidad amplio en dominio de entidades (`src/narrative_assistant/entities/models.py:18`).
- UI `CharacterSheet` ya intenta segmentar por tipo de entidad.

### Qué falta para corrector/editorial

1. Atributos dinámicos por contexto temporal:
- "paisaje verde" en primavera y "seco/marrón" años después necesita dimensión temporal por atributo.

2. Atributos situacionales por evento:
- "la ciudad quedó destruida tras bomba" debería adjuntarse a `evento causal` y rango temporal.

3. Atributos de entorno con jerarquía:
- lugar -> clima/terreno/estado ambiental/infraestructura, no solo `other`.

4. Atributos de objeto con ciclo de vida:
- estado, propietario por tramo temporal, daños, reparaciones, desaparición.

5. Modelo explícito de "misma entidad, múltiples instancias temporales":
- clave para coherencia narrativa en ciencia ficción/fantasía temporal.

---

## UX/UI: problemas y mejoras

Problemas:

- Timeline no comunica instancia temporal del personaje (depende de F1).
- ~~Orden cronológico puede resultar ambiguo en mezcla fecha real/dayOffset.~~ **Corregido** — comparator transitivo con rank numérico.
- Modal de atributos en `CharacterView` limita categorías y contradice la riqueza de `CharacterSheet`.

Mejoras recomendadas:

1. Mostrar badge de instancia temporal (`A@40`, `A@45`) en tarjetas y detalle de evento (pendiente F1).
2. ~~Corregir comparator cronológico.~~ **Hecho**.
3. Unificar selector de categorías con configuración por tipo de entidad (F8).
4. ~~Añadir tooltips explicando diferencia entre "orden del texto" y "orden de historia".~~ **Hecho** — badge `#N` de discourse position en `TimelineEvent.vue`.

---

## QA: cobertura actual y gaps

Cobertura sólida:

- `day_offset`/`weekday` y límites extremos: `tests/unit/test_temporal.py:214`, `tests/unit/test_temporal.py:257`.
- Instancias temporales en `TemporalMap`: `tests/unit/test_temporal_map.py:275`.
- Overflow guard en `_resolve_relative_markers`: `tests/unit/test_temporal.py` (test_extreme_offset_no_crash, test_extreme_day_offset_clamped).
- Mixed type comparison (`_date_to_offset`): `tests/unit/test_temporal_map.py:TestAliveCheckEdgeCases`.
- Muerte por instancia temporal: `tests/unit/test_temporal_map.py:TestTemporalInstances` (3 tests).

Cobertura débil o ausente:

1. Endpoint `get_entity_timeline` sin suite específica dedicada.
2. Semántica timeline en frontend mayormente validada como smoke/e2e de presencia (no de orden semántico profundo) (`frontend/e2e/timeline.spec.ts:219`).
3. Muchos adversariales en `xfail` documentan límites reales de NLP (`tests/adversarial/test_pipeline_breaking.py:186`, `tests/adversarial/test_attribute_adversarial.py:863`).
4. Sin tests para extracción de atributos de lugar/objeto (F3/F4 — no hay funcionalidad que testear aún).

---

## Rendimiento/memoria y estabilidad (Windows/Mac)

Puntos a favor:

- Protección temprana contra GPUs de riesgo (evita BSOD): `src/narrative_assistant/core/device.py:14`.
- Limpieza defensiva de memoria GPU: `src/narrative_assistant/core/device.py:411`.
- Límite de eventos + truncado en timeline: `api-server/routers/chapters.py:431`, `api-server/routers/chapters.py:605`.
- Virtualización en lista para altos volúmenes (PrimeVue VirtualScroller >100 eventos): `frontend/src/components/timeline/TimelineView.vue`.
- Overflow guard con clamp a ±365.000 días: `src/narrative_assistant/temporal/timeline.py`.

Riesgos vigentes:

- Vista horizontal (`vis-timeline`) puede degradarse con miles de eventos aunque la lista esté virtualizada.
- Falta de modelado temporal avanzado (timezone/DST/relatividad) provoca decisiones heurísticas simplificadas que pueden confundir al usuario experto.

---

## Plan de optimización propuesto (priorizado)

### Fase 1 — Timeline fix (completada parcialmente)

| Tarea | Estado | Notas |
|-------|--------|-------|
| Corregir comparator mixto storyDate/dayOffset | **HECHO** | Rank numérico transitivo |
| Badge discourse position (#N) | **HECHO** | En TimelineEvent.vue |
| Gap indicators + colored connectors | **HECHO** | Verde/azul por narrative_order |
| VisTimeline soporta dayOffset-only | **HECHO** | Synthetic dates con setFullYear |
| export_to_json incluye day_offset/weekday | **HECHO** | +temporal_instance_id |
| Overflow guard en _resolve_relative_markers | **HECHO** | MAX_DAY_OFFSET = 365.000 |
| API limit 5000 eventos + truncado | **HECHO** | Con warning en frontend |
| VirtualScroller para listas grandes | **HECHO** | Threshold: 100 eventos |
| Materializar temporal_instance_id en constructores | Pendiente | Requiere detección NLP (F1) |
| vital_status con temporal_instance_id | Pendiente | ~5 líneas, depende de F1 |

### Fase 2 — Atributos no-persona (sprint dedicado)

Objetivo: que el sistema extraiga y clasifique atributos de lugar/objeto/organización con la misma calidad que los de persona.

| # | Tarea | Esfuerzo | Dependencias |
|---|-------|----------|-------------|
| 2.1 | Propagar entity_type en menciones (3-tupla → 4-tupla) | S | Ninguna |
| 2.2 | Bifurcar extracción por tipo (persona/lugar/objeto) | M | 2.1 |
| 2.3 | Completar _map_attribute_key con CLIMATE/TERRAIN/SIZE/LOCATION | S | 2.2 |
| 2.4 | Añadir _extract_value_from_sentence para claves geográficas | M | 2.3 |
| 2.5 | Prompts LLM por tipo de entidad | M | 2.2 |
| 2.6 | Extender canonical_descriptions con descriptores geográficos | S | 2.2 |
| 2.7 | _infer_category/_infer_key sensibles a entity_type | S | 2.1 |
| 2.8 | Unificar UI categorías (CharacterView = CharacterSheet) | M | Ninguna |
| 2.9 | Validación backend de categoría por tipo de entidad | S | 2.8 |
| 2.10 | Tests unitarios de extracción lugar/objeto | M | 2.4 |

Esfuerzo estimado: S = pocas líneas, M = módulo o función completa.

### Fase 3 — Casos extremos narrativos (futuro)

| # | Tarea | Prioridad | Notas |
|---|-------|-----------|-------|
| 3.1 | Detección NLP de instancias temporales | Alta | Habilita F1/F2/F6 |
| 3.2 | Badge temporal_instance_id en UI | Media | Depende de 3.1 |
| 3.3 | Labels personalizables en timeline (worldbuilding) | Baja | Solo presentación |
| 3.4 | hour_offset opcional en TemporalSlice | Baja | Para el 1% de manuscritos |
| 3.5 | timezone/DST opt-in en TemporalMarker | Muy baja | Nicho |

---

## Conclusión

El proyecto está mejor que en iteraciones anteriores en la capa temporal básica y en protección de rendimiento. Los problemas de timeline detectados en esta auditoría (F5 sort, F6 UI, F7 endpoint) están corregidos o son de baja gravedad.

El cuello de botella real es doble:

1. **Detección NLP de instancias temporales** (F1) — es la pieza que desbloquea F2, F6, y los casos extremos 1-4. Sin ella, toda la infraestructura de `temporal_instance_id` es código muerto útil.

2. **Sesgo a persona en atributos** (F3/F4/F9) — limita el valor editorial para worldbuilding. Es un refactor multicapa pero con piezas ya existentes (regex, enum keys, helpers) que solo necesitan conectarse.

Para historias lineales con personajes como eje, el sistema es completo y funcional.
Para narrativa compleja o worldbuilding rico, la Fase 2 (atributos) y la Fase 3.1 (instancias temporales) son los siguientes pasos naturales.

## Actualización final de cierre (2026-02-13)

Esta actualización sustituye el estado previo para los puntos pendientes más críticos.

### Estado actualizado por hallazgo

| ID | Estado anterior | Estado final actualizado | Comentario |
|----|------------------|--------------------------|------------|
| F1 | Parcial | **Parcial alto (casi cerrado)** | Se cubren instancias temporales explícitas por edad numérica y fase vital léxica (`@age`, `@phase`) y ya se propagan en pipeline batch, endpoint timeline y exportador. Pendiente solo NLP semántico profundo (casos implícitos sin marcador textual). |
| F2 | Corregido | **Corregido** | Se mantiene corregido: `vital_status` registra/consulta muerte por instancia temporal cuando hay evidencia explícita. |
| F3 | Parcial | **Parcial** | Sin cambios estructurales en esta ronda respecto a lo ya implementado anteriormente. |
| F4 | Corregido | **Corregido** | Se mantiene corregido. |
| F6 | Corregido | **Corregido** | Se mantiene corregido. |
| F8 | Corregido | **Corregido** | Se mantiene corregido. |
| F9 | Corregido | **Corregido** | Se mantiene corregido. |

### Cambios técnicos añadidos en esta ronda

1. `TemporalMarker` soporta fase de edad (`age_phase`) para textos como "de joven", y genera `temporal_instance_id` estable (`<entity>@phase:<phase>`).
2. `_parse_age()` deja de asumir `groups[0]` y parsea correctamente patrones con grupos opcionales como "recién cumplidos los 41".
3. `analysis_pipeline._run_temporal_analysis()` ahora carga menciones de entidades persistidas por capítulo y usa `extract_with_entities()` cuando hay contexto, igual que el endpoint timeline.
4. `collect_export_data()` (timeline de exportación DOC/PDF) también usa menciones por capítulo + `extract_with_entities()`, evitando divergencia entre API y export.

### Evidencia de tests (esta ronda)

- `pytest tests/unit/test_temporal.py tests/unit/test_vital_status.py tests/unit/test_entities_attribute_validation.py tests/unit/test_temporal_entity_mentions_integration.py -q` -> **100 passed**
- `pytest tests/unit/test_entities_timeline_endpoint.py -q` -> **6 passed**
- `python -m py_compile` en módulos Python modificados -> **OK**
- `npm run -s lint` -> **OK**
- `npm run -s build` -> **OK**
- `npm run -s test:run` -> **450 passed** (persisten warnings conocidos de `happy-dom`, sin fallo)

### Nuevos tests añadidos

- `tests/unit/test_temporal_entity_mentions_integration.py`
  - Verifica que `analysis_pipeline` construye `temporal_instance_id` desde menciones persistidas.
  - Verifica que `collect_export_data` conserva `temporal_instance_id` en `timeline_events`.
- `tests/unit/test_temporal.py`
  - Caso "recién cumplidos los X".
  - Caso de fase implícita "de joven" con `@phase:young`.

### Conclusión de cierre

Los pendientes funcionales de timeline que quedaban abiertos en código han quedado implementados. El único resto real en "parcial" es de naturaleza NLP avanzada (inferencias semánticas implícitas sin marcador textual), no de plomería ni de integración backend/frontend/export.

## Addendum NLP implícito (2026-02-13, segunda iteración)

Se implementó una mejora adicional para reducir el "parcial" en detección de instancias temporales implícitas:

- `TemporalMarker` ahora soporta `relative_year_offset` además de `age_phase`.
- `extract_with_entities()` detecta y asigna instancia temporal en:
  - Adjetivo adyacente a mención: `joven Juan`, `viejo Juan`.
  - Desdoble explícito: `yo del futuro`, `versión pasada`.
  - Desfase relativo en años: `dentro de 5 años`, `5 años después`, `hace 3 años`.
- Los relativos en años se vinculan a la entidad cercana y generan `temporal_instance_id` estable (`@offset_years:+/-N`).
- `TimelineBuilder` ahora materializa eventos también para instancias por fase/offset aunque no exista edad numérica.

### Estado tras esta mejora

- F1 pasa de "parcial alto" a **"parcial muy alto"**: ya cubre explícitos + implícitos heurísticos frecuentes.
- Límite restante: inferencias semánticas profundas sin pista léxica local (casos de larga distancia, ironía, elipsis compleja, co-referencia difusa).

### Validación específica de esta iteración

- `tests/unit/test_temporal.py`:
  - `test_extract_with_entities_infers_phase_from_adjacent_mention`
  - `test_extract_with_entities_infers_relative_offset_instance`
  - `test_phase_instance_without_numeric_age_creates_timeline_event`
- `tests/unit/test_temporal_entity_mentions_integration.py` (pipeline/export)
- `tests/unit/test_vital_status.py`

Resultado: **101 passed** + endpoint timeline **6 passed**.
