# Auditoria extrema de recursos, instalacion, primera ejecucion, pipeline y reanalisis granular

Fecha: 2026-03-02  
Repositorio: `d:\repos\tfm`  
Tipo: auditoria tecnica exhaustiva (sin implementar cambios)

## 1) Alcance exacto auditado

Se audito de extremo a extremo:

- Instalacion y post-instalacion (Python, modelos NLP, Ollama, Java/LanguageTool).
- Primera ejecucion y auto-configuracion inicial.
- Ejecuciones posteriores (reanalyze, cancel, fast-path, incremental).
- Deteccion de capacidades de maquina y activacion/desactivacion de metodos.
- Descarga, inicializacion, readiness y fallbacks.
- Pipeline completa (fases 1-13, progreso, errores, degradaciones).
- Configuracion de metodos en frontend y consumo real en backend.
- Votacion multi-metodo y su integracion real en el flujo productivo.
- Reanalisis incremental fino por impacto de personaje/relaciones/acciones.
- Ramas con fallos silenciosos y comunicacion al usuario no tecnico.

## 2) Evidencia y validacion ejecutada

Pruebas ejecutadas en esta sesion:

- `pytest -q tests/unit/test_invalidation.py tests/unit/test_version_diff_and_planner.py tests/integration/test_incremental_planner_modes.py`
- Resultado: `36 passed, 1 deselected`

Verificaciones de cobertura (busqueda en tests):

- Sin cobertura especifica encontrada para:
  - `run_ollama_healthcheck` y bug de `tracker.update_action`.
  - `/api/system/resources`.
  - `autoConfigOnStartup`.
  - Flujo `needs_restart` frontend/backend.
  - Integracion real de `enabledNLPMethods` -> pipeline backend.

## 3) Resumen ejecutivo (veredicto)

Estado general: **base funcional buena**, pero **no cumple todavia** el nivel objetivo para:

- activacion fiable de metodos segun capacidades reales,
- comunicacion continua sin silencios en todos los caminos,
- reanalisis granular por personaje-relaciones-acciones.

Diagnostico corto:

1. Hay mecanismos incrementales, pero mayoritariamente por fase y firmas globales.
2. La configuracion de metodos en UI no esta conectada de forma verificable al motor de analisis.
3. Persisten ramas silenciosas y flujos best-effort que pueden ocultar fallos al usuario.
4. Existen bugs puntuales de alto impacto en rutas criticas.

## 4) Hallazgos priorizados

## 4.1 Criticos

### CR-01 - Bug real en healthcheck de Ollama durante analisis

Evidencia:

- `api-server/routers/_analysis_phases.py:653` define `set_action`.
- `api-server/routers/_analysis_phases.py:1556` llama `tracker.update_action(...)` (metodo no existente).
- `api-server/routers/_analysis_phases.py:1571-1573` captura excepcion y fuerza `analysis_config.use_llm = False`.

Impacto:

- En auto-config activa (`_ollama_init_started`), puede degradar a analisis sin LLM por error interno evitable.
- El usuario recibe resultado de menor calidad sin causa explicita de negocio.

---

### CR-02 - Endpoint `/api/system/resources` usa atributos privados incorrectos

Evidencia:

- `api-server/routers/system.py:1342-1343` usa `rm._running_tasks` y `rm._heavy_task_semaphore.available`.
- `src/narrative_assistant/core/resource_manager.py:170-179` expone `active_tasks` y `available_slots`.
- `src/narrative_assistant/core/resource_manager.py:413-418` expone `heavy_task_semaphore` publica.

Impacto:

- Riesgo real de `500` o telemetria invalida en endpoint clave de recursos.

---

### CR-03 - Configuracion de metodos en frontend no llega de forma consistente a backend

Evidencia:

- Frontend guarda metodos en localStorage:
  - `frontend/src/composables/useSettingsPersistence.ts:48,133-135`
  - `frontend/src/composables/useNLPMethods.ts:93-108`
- Inicio de analisis solo envia `file` y `mode`:
  - `frontend/src/stores/analysis.ts:311-320`
- Backend espera `project.settings.analysis_features`:
  - `api-server/routers/_analysis_phases.py:1103-1123`
- `frontend/src` no usa `analysis_features` (sin coincidencias).
- `api-server/routers/projects.py:445` indica settings reservadas para futuro.

Impacto:

- El usuario puede activar/desactivar metodos en UI sin garantia de efecto real en pipeline.
- Riesgo directo contra el requisito principal de control por capacidades de maquina.

---

### CR-04 - Reanalisis tras cancelar no reutiliza aunque no haya cambios

Evidencia:

- Fast-path exige estado previo `completed`:
  - `api-server/routers/analysis.py:648-653`
- Cancelacion deja estado `cancelled`:
  - `api-server/routers/_analysis_phases.py:5228`

Impacto:

- Flujo "paro -> relanzo" desperdicia tiempo/recursos aunque fingerprint no haya cambiado.

---

### CR-05 - Reanalisis incremental no es granular por personaje-relaciones-acciones

Evidencia:

- Planner actual solo controla Tier3 por 4 nodos:
  - `api-server/routers/_incremental_planner.py:11-13,23-28`
- Heuristica principal por ratio de capitulo:
  - `api-server/routers/_incremental_planner.py:63-76,145-147`
- `VersionDiffRepository.compute_chapter_diff` compara capitulo completo por igualdad de texto:
  - `src/narrative_assistant/persistence/version_diff.py:140-149`
- Enrichment usa `entity_scope IS NULL` en fast-skip:
  - `api-server/routers/_enrichment_phases.py:359-360,374-375`
- Firma de menciones es global (todas las entidades):
  - `api-server/routers/_enrichment_phases.py:196-223`

Impacto:

- Un cambio puntual en personaje A no se propaga como subgrafo fino (A + vecinos + acciones afectadas).
- Predomina recomputacion global o por fase, no por impacto semantico local.

---

### CR-06 - Doble orquestacion de descarga LLM en primera ejecucion puede generar falsos fallos

Evidencia:

- `autoConfigOnStartup` dispara `POST /api/ollama/pull/{model}`:
  - `frontend/src/stores/system.ts:589-596`
- `ModelSetupDialog` vuelve a disparar descargas despues de `autoConfigOnStartup`:
  - `frontend/src/components/ModelSetupDialog.vue:231-253`
- Backend solo permite una descarga a la vez:
  - `src/narrative_assistant/llm/ollama_manager.py:521-523`
  - `api-server/routers/services.py:372-376` retorna error "Ya hay una descarga en curso".
- En frontend, ese error cuenta como fallo de modelo:
  - `frontend/src/composables/useOllamaManagement.ts:243-249`

Impacto:

- Puede marcar instalacion parcial/fallida aunque la descarga ya este ocurriendo en background.
- Riesgo de UX confusa justo en primera experiencia.

## 4.2 Altos

### HI-01 - Timeouts de descarga fragiles y manejo incompleto del timeout global

Evidencia:

- `api-server/routers/system.py:630` usa `as_completed(..., timeout=600)`.
- `api-server/routers/system.py:633` usa `future.result(timeout=300)` dentro de futures ya finalizados.
- No hay manejo especifico del `TimeoutError` del iterador global `as_completed`.

Impacto:

- En redes lentas/modelos grandes puede cortar el flujo de forma abrupta.

---

### HI-02 - Auto-config de startup con catches silenciosos en rutas criticas

Evidencia:

- `frontend/src/stores/system.ts:578-580,596-598,603-605,609-611`

Impacto:

- Fallos de start/pull/readiness pueden no escalar a mensajes utiles.

---

### HI-03 - `llmDownloadingModels` no se usa en UI y ademas se limpia al final

Evidencia:

- Se setea en `frontend/src/stores/system.ts:592`.
- Comentario indica no limpiarlo aun (`:600`), pero `finally` lo limpia siempre (`:606`).
- Referencias encontradas solo en el mismo store (`:143,592,600,606,684`).

Impacto:

- Se pierde trazabilidad visual de descargas LLM automÃ¡ticas.
- Puede dar sensacion de "se paro" cuando aun hay trabajo en backend.

---

### HI-04 - `needs_restart` backend no consumido por frontend

Evidencia:

- Backend lo calcula y devuelve:
  - `api-server/routers/system.py:343-347,362`
- Tipo frontend no lo contempla:
  - `frontend/src/stores/system.ts:38-55`
- No hay usos en `frontend/src` (sin coincidencias).

Impacto:

- En runtime embebido/frozen, el usuario no recibe instruccion clara de reinicio cuando aplica.

---

### HI-05 - Capabilities mezcla "soportable por hardware" con "servicio actualmente corriendo"

Evidencia:

- `api-server/routers/system.py:903,947,973,1037,1055,1063` usa `ollama_available`.
- `api-server/routers/system.py:837-859` si instalado pero no iniciado, se reporta no disponible.

Impacto:

- Metodos pueden aparecer como no disponibles aunque el equipo los soporte y solo falte arranque.

---

### HI-06 - Inconsistencia entre recomendacion de modelos y requisitos reales

Evidencia:

- Capabilities recomienda `qwen3` en CPU:
  - `api-server/routers/system.py:1078`
- Metadata del modelo:
  - `src/narrative_assistant/llm/ollama_manager.py:126-132` (`min_ram_gb=12.0`)
- Config nivel RAPIDA:
  - `src/narrative_assistant/llm/config.py:241` core=`qwen3`
  - `src/narrative_assistant/llm/config.py:255` fallback ligeros
  - `src/narrative_assistant/llm/config.py:463` RAPIDA marcada siempre disponible.

Impacto:

- Mensajes/recomendaciones pueden empujar a intentos no viables en equipos limitados.

---

### HI-07 - Votacion multi-metodo no esta integrada de forma uniforme en pipeline principal

Evidencia:

- Coreferencia si usa votacion:
  - `api-server/routers/_analysis_phases.py:2568-2575`
- Temporal en pipeline usa `TemporalConsistencyChecker` (no `VotingTemporalChecker`):
  - `api-server/routers/_analysis_phases.py:3200-3203,3278-3279`
- Enrichment de relaciones usa red/timeline/perfiles, no `VotingRelationshipDetector`:
  - `api-server/routers/_enrichment_phases.py:554-628`
- `VotingRelationshipDetector` existe pero no se observa integrado en routers/pipeline principal.

Impacto:

- El principio "algunos metodos votan en conjunto" esta aplicado parcialmente, no end-to-end.

---

### HI-08 - Configuracion de votacion en pipeline esta hardcodeada y desconectada de settings de usuario

Evidencia:

- Coref fija metodos y umbrales:
  - `api-server/routers/_analysis_phases.py:2568-2575`
- UI ofrece controles `inferenceMinConfidence`/`inferenceMinConsensus`:
  - `frontend/src/composables/useSettingsPersistence.ts:31-32,57-58`
- No se observa paso de esos valores al analisis de proyecto (`startAnalysis` envia solo file+mode).

Impacto:

- El usuario puede creer que ajusta consenso/confianza, pero la pipeline usa defaults fijos.

---

### HI-09 - Invalidacion/selectividad de enrichment sigue siendo global en rutas clave

Evidencia:

- `run_cleanup` marca stale todo el cache del proyecto:
  - `api-server/routers/_analysis_phases.py:1018-1024`
- Mutacion de entidades marca tipos completos, sin sub-alcance por relacion:
  - `api-server/routers/_enrichment_phases.py:290-304`
- Fallback legacy borra todo:
  - `api-server/routers/_enrichment_phases.py:307-313`

Impacto:

- Penaliza tiempo y recursos; contradice objetivo de recomputar solo lo necesario.

---

### HI-10 - Fallos silenciosos/semisilenciosos en estado y diagnostico

Evidencia:

- `_mark_failed` en enrichment traga excepcion:
  - `api-server/routers/_enrichment_phases.py:117-118`
- Status LanguageTool en exception devuelve `success=True` con `not_installed`:
  - `api-server/routers/services.py:528-537`

Impacto:

- Puede ocultar fallos reales y complicar soporte.

---

### HI-11 - Endpoint de instalacion de dependencias sin guard idempotente de concurrencia

Evidencia:

- `install_dependencies` inicia thread siempre:
  - `api-server/routers/system.py:430-530`
- No hay rechazo temprano si `INSTALLING_DEPENDENCIES` ya esta activo.

Impacto:

- Riesgo de instalaciones solapadas y estados intermedios inconsistentes.

---

### HI-12 - Arranque sidecar puede reportar exito aunque backend no haya quedado sano

Evidencia:

- Si health no responde tras 15s, solo loguea y retorna `Ok(...)`:
  - `src-tauri/src/main.rs:109-114`
- Setup emite evento `"running"` tras ese retorno:
  - `src-tauri/src/main.rs:314-323`
- Frontend marca conectado en `running`:
  - `frontend/src/stores/app.ts:89-91`

Impacto:

- Riesgo de estado "aparentemente listo" cuando backend aun no responde.

## 4.3 Medios

### ME-01 - Endpoint stale-first en varias vistas puede mostrar datos obsoletos sin seÃ±al fuerte

Evidencia:

- `api-server/routers/relationships.py:32`
- `api-server/routers/prose.py:157`
- `api-server/routers/voice_style.py:67`

Impacto:

- El usuario puede reanalizar y seguir viendo lectura antigua hasta refresh/recompute.

---

### ME-02 - Divergencia de scripts espejo (`scripts/` vs `src-tauri/resources/`)

Evidencia:

- `scripts/download_models.py:108-113,170-179` incluye transformer NER.
- `src-tauri/resources/download_models.py:108-112` no lo incluye.

Impacto:

- Distinto comportamiento segun flujo dev vs empaquetado.

---

### ME-03 - Mensaje final de post-install puede ser demasiado optimista con fallos no fatales

Evidencia:

- Continua tras fallos Ollama/LLM:
  - `scripts/post_install.py:470-478`
- Cierra con "Instalacion completada correctamente":
  - `scripts/post_install.py:480`

Impacto:

- Puede generar falsa expectativa de disponibilidad completa.

---

### ME-04 - Progreso de dependencias Python sigue siendo poco granular en UX

Evidencia:

- UI usa estado binario durante install deps:
  - `frontend/src/components/ModelSetupDialog.vue:498-502`
- Existe script verbose (`src-tauri/resources/install_deps_verbose.py`) no integrado en flujo principal.

Impacto:

- En instalaciones largas persiste riesgo de percepcion de bloqueo.

---

### ME-05 - Evento `backend-status: restarting` no se traduce en estado UX explicito

Evidencia:

- Backend emite `restarting`:
  - `src-tauri/src/main.rs:201-206`
- Frontend solo maneja `running` y `error`:
  - `frontend/src/stores/app.ts:89-96`

Impacto:

- Falta feedback intermedio cuando watchdog reinicia backend.

## 5) Reanalisis granular (personaje -> relacionados -> acciones): estado real vs objetivo

Objetivo solicitado:

- "Si cambia un personaje, revisar solo personajes relacionados, acciones y efectos derivados."

Estado real:

1. **Nivel capitulo**: existe optimizacion parcial en NER por cache de capitulos.
   - `api-server/routers/_analysis_phases.py:1697-1740`
2. **Nivel fase**: planner incremental decide solo `relationships/voice/prose/health`.
   - `api-server/routers/_incremental_planner.py:11-13,82-127`
3. **Nivel entidad-relacion-accion**: no existe grafo de impacto operativo en planner.
4. **Firmas de enrichment**: globales por proyecto, no por subgrafo local.
   - `api-server/routers/_enrichment_phases.py:196-223,359-375`

Conclusion tecnica:

- Hay incrementalidad, pero no la granularidad que pides.
- El motor no determina todavia "vecindad de impacto" de personaje y acciones derivadas.

## 6) Deliberacion tecnica (2-3 vueltas de decision)

### Opcion A: mantener fase-level (actual)

- Ventaja: simple, robusta.
- Problema: sobrerrecalculo frecuente, no cumple objetivo fino.

### Opcion B: chapter-level extendido

- Ventaja: mejor que A, reutiliza mejor NER.
- Problema: sigue recalculando entidades no relacionadas dentro del capitulo; insuficiente para "solo relacionados".

### Opcion C: entity-impact graph (recomendada)

- Nodo base: entidad, relacion, accion/evento, capitulo, artefacto de salida.
- Aristas: dependencia de calculo y consumo.
- Regla: cambio en nodo X -> cierre transitivo minimo -> recompute selectivo.
- Fallback: si incertidumbre alta, escalar a chapter-level o phase-level.

Veredicto de debate:

- Para tu requisito explicito, solo C cumple de forma estructural.
- A y B pueden quedar como fallback de seguridad.

## 7) Evaluacion de instalacion/primera/siguientes ejecuciones

### Instalacion y post-instalacion

Puntos fuertes:

- Flujo principal funcional con comprobaciones y mensajes base.
- LanguageTool tiene fases de progreso claras:
  - `src/narrative_assistant/nlp/grammar/languagetool_manager.py:520-591`

Gaps:

- Dependencias Python sin progreso real por paquete.
- Riesgo de concurrencia en `/api/dependencies/install`.
- Mensajeria final de exito puede ocultar parcialidad.

### Primera ejecucion

Puntos fuertes:

- `ModelSetupDialog` muestra fases visibles (`starting/checking/installing-deps/downloading/downloading-llm`):
  - `frontend/src/components/ModelSetupDialog.vue:172-216,479-530`

Gaps:

- Doble orquestacion de pulls LLM.
- `llmDownloadingModels` sin reflejo real en UI.
- Catches silenciosos de auto-config.

### Ejecuciones posteriores

Puntos fuertes:

- Fast-path por fingerprint cuando `completed`:
  - `api-server/routers/analysis.py:648-685`

Gaps:

- Tras `cancelled`, no hay reutilizacion de artefactos aunque no cambie el documento.

## 8) Fallos silenciosos y comunicacion al usuario

Situaciones detectadas:

- Capturas silenciosas en auto-config y pulls.
- Endpoints que devuelven `success=True` ante error interno (caso LT status).
- Falta de mensaje de estado intermedio en algunos reinicios/reintentos.

Riesgo UX:

- Usuario no tecnico puede interpretar "se quedo parado" o "todo bien" cuando no lo esta.

Criterio objetivo recomendado:

- Ninguna operacion >10s sin actualizar estado visible.
- Ningun fallo de dependencia/modelo sin mensaje de negocio y accion sugerida.
- Estados diferenciados: `ocupado`, `reintentando`, `degradado`, `listo parcial`, `error accionable`.

## 9) Matriz de pruebas extremas recomendada (sin implementar)

## 9.1 Instalacion y bootstrap

1. Python ausente.
2. Python presente, pip roto.
3. Python correcto, `numpy` falla por wheel corrupto.
4. Espacio en disco insuficiente durante `pip install`.
5. Permisos de escritura denegados en directorio de modelos.
6. DNS intermitente durante descarga spaCy.
7. Red lenta extrema (>10 min por modelo).
8. Corte de red a mitad de descarga.
9. Reintento tras corte con cache parcial existente.
10. Lanzar `/api/dependencies/install` dos veces en paralelo.
11. Lanzar `/api/models/download` dos veces rapido.
12. Inicio app con backend tardando >15s en health.
13. Backend reinicio watchdog con frontend abierto.
14. App cerrada durante instalacion en curso.
15. Reapertura tras cierre abrupto con estado incompleto.

## 9.2 Ollama y LLM

1. Ollama no instalado.
2. Ollama instalado no arrancable.
3. Ollama arrancado sin modelos.
4. Pull modelo core con RAM insuficiente.
5. Pull simultaneo de dos modelos (debe serializar).
6. Pull fallido + fallback a modelo alternativo.
7. Readiness con fallback presente pero core ausente.
8. Cambio de quality level con modelos parciales instalados.
9. GPU bloqueada por compute capability baja.
10. CPU-only con presupuesto justo.

## 9.3 Java/LanguageTool

1. Java sistema ausente, install local correcto.
2. Java sistema presente, LT zip corrupto.
3. LT instalado no arrancable por puerto ocupado.
4. LT status endpoint con excepcion interna.
5. Reintentos de instalacion LT cuando ya hay instalacion en curso.

## 9.4 Pipeline y cancelacion

1. Cancelar en NER chapter cache loop.
2. Cancelar durante fusion coref.
3. Cancelar durante enriquecimientos paralelos.
4. Cancelar durante llamada LLM lenta.
5. Reanalizar inmediatamente tras cancelar.
6. Reanalizar sin cambios tras cancel.
7. Documento sin cambios con estado `completed` (fast-path).
8. Documento sin cambios con estado `cancelled`.
9. Documento con cambio minimo en una entidad secundaria.
10. Documento con cambios en estructura de capitulos.

## 9.5 Reanalisis granular por entidad-relacion-accion

1. Cambia alias de personaje A, sin cambio semantico.
2. Cambia atributo critico de A (edad/estado) y validar solo vecinos impactados.
3. Fusion manual A+B y medir alcance exacto recomputado.
4. Reject de entidad duplicada sin tocar texto.
5. Cambio en accion de A en capitulo N, sin impacto en otros capitulos.
6. Cambio de dialogo de A, validar solo perfiles de voz afectados.
7. Cambio de relacion A-C, validar recalculo de red local y metricas derivadas.
8. Cambio de personaje sin conexiones, validar no recalculo global.
9. Cambio simultaneo en dos subgrafos desconectados.
10. Cambio en personaje de alta centralidad (debe ampliar alcance por grafo).

## 9.6 UX y observabilidad

1. Cada tarea larga reporta mensaje cada <=10s.
2. Mensajes no tecnicos en todas las fases de descarga/instalacion.
3. Mensaje explicito en estado degradado (fallback activo).
4. Mensaje accionable en cada error final.
5. Indicador visible durante reintentos automaticos.
6. Diferenciar "ocupado" vs "bloqueado".

## 10) KPIs de aceptacion recomendados

1. Tiempo medio de reanalisis tras cambio local < 35% de full run.
2. Reanalisis tras cancel sin cambios reutiliza >= 80% artefactos.
3. Cero errores silenciosos en rutas criticas (instalacion/startup/analysis).
4. Cero fases largas sin heartbeat > 10s.
5. Exactitud de alcance: cambios de entidad aislada no fuerzan recompute global.

## 11) Priorizacion de correccion sugerida

P0 (inmediato):

1. CR-01, CR-02, CR-03.
2. CR-06.
3. HI-04.

P1 (corto plazo):

1. CR-04, CR-05.
2. HI-01, HI-02, HI-05, HI-06.
3. HI-07, HI-08.

P2 (medio plazo):

1. HI-09, HI-10, HI-11, HI-12.
2. ME-01..ME-05.
3. Matriz completa de pruebas extremas automatizadas.

## 12) Conclusion final

La plataforma tiene piezas potentes (cache incremental por capitulo, planner Tier3, fallbacks, dialogo de setup), pero para el objetivo que pediste falta cerrar tres brechas estructurales:

1. **Control real de metodos**: hoy la UI no gobierna de forma fiable la ejecucion backend.
2. **Granularidad de reanalisis**: hoy es mayormente por fase/capitulo global, no por subgrafo de impacto personaje-relaciones-acciones.
3. **Robustez UX operativa**: todavia hay ramas silenciosas y estados ambiguos en instalacion/startup/descarga.

Sin implementar cambios, el estado actual se considera **funcional pero no optimo** para tu criterio de "maxima eficiencia por impacto local + cero sensacion de bloqueo".

## 13) Soluciones y sugerencias por hallazgo (accionables)

Nota: esta seccion propone como resolver cada punto sin implementar aun cambios de codigo.

### 13.1 Criticos

- `CR-01`: Reemplazar `tracker.update_action(...)` por `tracker.set_action(...)` en healthcheck; no desactivar LLM por error interno de tracking, solo por fallo real de disponibilidad; agregar test unitario del flujo `_ollama_init_started` y asercion de no degradacion silenciosa.
- `CR-02`: Sustituir uso de atributos privados en `/api/system/resources` por API publica (`active_tasks`, `heavy_task_semaphore.available_slots`); agregar test de contrato del endpoint con `ResourceManager` real y mockeado.
- `CR-03`: Unificar ruta de configuracion de metodos: guardar en `project.settings.analysis_features` y leerla en backend en cada analisis; bloquear en UI opciones no soportadas por capacidades; agregar test e2e "toggle en UI -> efecto real en pipeline".
- `CR-04`: Permitir fast-path tambien para estado previo `cancelled` si fingerprint/artefactos son validos; separar "estado final" de "elegibilidad de reuse"; test de regresion: cancelar, relanzar sin cambios, verificar reutilizacion.
- `CR-05`: Implementar invalidacion por subgrafo de impacto (entidad-relacion-accion) con cierre transitivo acotado y fallback a chapter/phase-level; persistir "impact set" por corrida; medir precision de alcance (no recomputar no relacionados) en tests dirigidos.
- `CR-06`: Definir un unico orquestador de descargas LLM en primera ejecucion (o `autoConfigOnStartup` o `ModelSetupDialog`, no ambos); si hay descarga en curso, UI debe enlazarse al progreso existente en vez de marcar error; test concurrente de doble trigger.
- `CR-07`: Integrar `timeline` en el modelo oficial de fases (order+weights+UI) o declararla subfase formal de otra etapa; eliminar indices duplicados y garantizar progreso monotono.
- `CR-08`: En analisis parcial, diferenciar `accepted` (inicio) de `completed` (fin real); mantener polling hasta estado terminal backend y emitir `analysis-completed` solo al finalizar.

### 13.2 Altos

- `HI-01`: Reestructurar timeouts de descarga con deadline global + timeout por modelo y manejo explicito de `TimeoutError`; exponer estado `reintentando` y causa legible para usuario.
- `HI-02`: Eliminar catches vacios en startup, registrar error estructurado y mapearlo a mensaje de negocio + accion sugerida (reintentar, cerrar apps pesadas, contactar soporte).
- `HI-03`: Conectar `llmDownloadingModels` a componentes visibles y no limpiarlo hasta recibir confirmacion de fin/cancelacion real desde backend; incluir heartbeat cada <=10s.
- `HI-04`: Incluir `needs_restart` en tipo frontend y UX explicita: banner modal "reinicio necesario para aplicar cambios"; bloquear estados ambiguos.
- `HI-05`: Separar claramente capacidades en tres ejes: `hardware_supported`, `installed`, `running`; tomar decisiones de UI/pipeline sobre ese triplete y no sobre un booleano unico.
- `HI-06`: Unificar politica de recomendacion con requisitos reales de RAM/VRAM por modelo; si no cumple umbral, no recomendarlo y mostrar alternativa realista automaticamente.
- `HI-07`: Estandarizar framework de votacion para modulos que declaren multi-metodo (temporal, relaciones, etc.) con interfaz comun, pesos, quorum y trazabilidad.
- `HI-08`: Parametrizar umbrales de consenso/confianza desde settings de proyecto (no hardcode), con validaciones de rango y auditoria de valores usados por corrida.
- `HI-09`: Reemplazar invalidacion global en enrichment por invalidacion selectiva por entidad/relacion/capitulo; conservar fallback global como ultimo recurso con motivo registrado.
- `HI-10`: Prohibir rutas "success=true" ante excepcion interna; distinguir `ok`, `degraded`, `error`; anexar `error_code` estable para soporte.
- `HI-11`: Agregar guard idempotente y lock de concurrencia en `/api/dependencies/install`; si ya hay instalacion activa, devolver estado actual en vez de iniciar otra.
- `HI-12`: En Tauri, no emitir `running` hasta healthcheck correcto; introducir estado intermedio `starting`/`restarting` y timeout accionable.
- `HI-13`: Forzar que toda escritura de progreso fuera de `tracker._write` pase `_run_id`; auditar y bloquear en CI cualquier `_update_storage` sin `_run_id` en rutas concurrentes.
- `HI-14`: AÃ±adir `run_id` al orchestrator parcial y chequeo stale en cancel/restart; al completar parcial, persistir tambien `analysis_progress` en proyecto.
- `HI-15`: Corregir clasificacion de estados en `ProjectsView` (`analyzing`, `queued`, `cancelled`, `idle`) y evitar mapear `idle` a `completed`.
- `HI-16`: Revisar logica del watchdog heavy slot para marcar error del proceso realmente stale (con run_id/claim_ts), no por heuristica de status ambigua.
- `HI-17`: Si timeline falla, exponer estado degradado visible en UI (no solo log), con opcion de reintento aislado.
- `HI-18`: Incluir `timeline` en mapping parcial frontend-backend y dependencias asociadas; test e2e de analisis parcial de cronologia.
- `HI-19`: AÃ±adir estado de "deteccion incompleta" en capabilities y reintento de deteccion antes de desactivar metodos por timeout.
- `HI-20`: Unificar contrato de timeline en frontend (gates/dependencias/tab requerida/progreso backend); si la timeline no esta lista, la tab debe pedir su analisis especifico y no conformarse con `structure`.
- `HI-21`: Insertar `tracker.check_cancelled()` dentro del loop de `run_timeline` y en checkpoints de persistencia para corte rapido en cancel/reanalisis.
- `HI-22`: Evitar doble orquestacion en startup (`autoConfigOnStartup`), con lock idempotente y fuente unica de estado para descargas/configuracion inicial.
- `HI-23`: Reemplazar heuristicas de `analysis-status` por registro real de fases ejecutadas (run ledger/versionado) para evitar falsos positivos de tabs/fases.

### 13.3 Medios

- `ME-01`: Mantener stale-first solo con marca visual fuerte de "datos no actualizados" y autorefresco al completar pipeline; opcion manual "forzar refresco".
- `ME-02`: Consolidar scripts espejo en unica fuente compartida (o generar uno desde otro en build) y agregar test de paridad funcional.
- `ME-03`: Cambiar mensaje final post-install a resultado estratificado: `completo`, `parcial`, `fallido`; listar claramente que falta y como resolverlo.
- `ME-04`: Integrar instalador verbose en flujo principal para mostrar progreso por paquete/fase en UI no tecnica; actualizar estado cada pocos segundos.
- `ME-05`: Consumir evento `backend-status: restarting` en frontend y mostrar estado temporal con reintento automatico visible.
- `ME-06`: Alinear tipos API de `analysis_status` con backend real (incluyendo `queued`/`cancelled`) y eliminar defaults optimistas a `completed`.
- `ME-07`: Hacer instalacion pip no interactiva y con timeout por paquete + timeout global; en timeout, devolver error accionable.
- `ME-08`: Detener polling de modelos/dependencias en rutas de error terminal y limpiar timers de forma explicita.
- `ME-09`: Sustituir mensajes tecnicos por lenguaje editorial en setup/progreso (sin exponer nombres de librerias o siglas tecnicas).
- `ME-10`: Incluir `timeline` en `BACKEND_PHASE_TO_FRONTEND` para que el progreso en vivo marque correctamente esa fase durante ejecuciones activas.
- `ME-11`: Unificar llamadas de `SettingsView` en `apiClient` (en vez de `fetch` directo) para heredar reintentos, manejo de errores y trazabilidad consistente.

### 13.4 Recomendaciones transversales (para todos los hallazgos)

- Definir catalogo de errores estable (`error_code`, `message_user`, `message_support`, `suggested_action`) y usarlo en backend+frontend.
- Incorporar "contract tests" entre frontend/backend para configuracion, estado de capacidades y semantica de progreso.
- Exigir un heartbeat de progreso cada <=10s en toda tarea larga (instalacion, descarga, analisis, reintentos).
- AÃ±adir telemetria minima operativa: tiempo por fase, motivo de fallback, porcentaje de reutilizacion incremental, tasa de errores recuperables.
- Crear runbook de soporte para usuario no tecnico con mensajes modelo y pasos concretos por incidente.

## 14) Hallazgos adicionales (segunda pasada exhaustiva)

### 14.1 Criticos nuevos

### CR-07 - Fase `timeline` mal integrada en tracker de progreso (riesgo de progreso corrupto y UX confusa)

Evidencia:

- `PHASE_ORDER` no incluye `timeline`: `api-server/routers/analysis.py:16-30`.
- `run_timeline` inicia/cierra fase `timeline` con indice `5`: `api-server/routers/_analysis_phases.py:3212,3341`.
- `run_attributes` tambien usa indice `5`: `api-server/routers/_analysis_phases.py:3369`.
- Si una fase no existe en `phase_order`, el tracker devuelve rango `(0,100)`: `api-server/routers/_analysis_phases.py:530-541`.

Impacto:

- El progreso puede saltar, retroceder o representar mal el estado real.
- La timeline queda "mezclada" con atributos en la UI de fases.
- Se degrada la confianza del usuario ("parece bloqueado / incoherente").

---

### CR-08 - Analisis parcial en frontend se marca como "terminado" inmediatamente tras iniciar

Evidencia:

- El endpoint parcial arranca thread y retorna enseguida: `api-server/routers/analysis.py:1189-1204`.
- Frontend `runPartialAnalysis` limpia estado de ejecucion en `finally` justo despues del POST: `frontend/src/stores/analysis.ts:528-543`.
- `AnalysisRequired` emite `analysis-completed` al recibir ese `true` (inicio, no fin real): `frontend/src/components/analysis/AnalysisRequired.vue:101-108`.

Impacto:

- La UI puede recargar datos antes de que la ejecucion parcial haya acabado.
- Riesgo de mostrar resultados stale como si fueran definitivos.
- Rompe expectativa de flujo fiable para optimizar por fases.

## 14.2 Altos nuevos

### HI-13 - Guard de `run_id` existe pero casi nunca se usa en `_update_storage` (riesgo de escrituras stale)

Evidencia:

- `_update_storage` soporta `_run_id` para ignorar ejecuciones reemplazadas: `api-server/routers/_analysis_phases.py:443-464`.
- La inmensa mayoria de llamadas no pasan `_run_id` (ej.: `:1677,3235,3387,3474,3715,4421...`); solo se observa una con `_run_id`: `:2273`.

Impacto:

- Tras cancelar y relanzar, el hilo viejo puede seguir escribiendo `current_action/progress` en el nuevo run.
- Mensajes y progreso pueden cruzarse entre ejecuciones.

---

### HI-14 - Analisis parcial sin `run_id` en `ProgressTracker` (sin deteccion de ejecucion reemplazada)

Evidencia:

- `ProgressTracker` parcial se crea sin `run_id`: `api-server/routers/_partial_analysis.py:577-583`.
- La deteccion de stale depende de `run_id`: `api-server/routers/_analysis_phases.py:775-783`.

Impacto:

- Cancel/reanalyze parcial puede dejar escrituras y estados cruzados sin corte limpio por `run_id`.

---

### HI-15 - Flujo de `ProjectsView` interpreta estados de progreso de forma incorrecta

Evidencia:

- La deteccion de proyectos en curso SI incluye `analysisStatus === 'analyzing'` junto a `queued` e `in_progress`: `frontend/src/views/ProjectsView.vue:449-451`.
- Si `/analysis/progress` devuelve `idle`, se marca como `completed` al 100%: `frontend/src/views/ProjectsView.vue:471-473`.
- Estados distintos de `completed/idle/queued` se fuerzan a `analyzing`: `frontend/src/views/ProjectsView.vue:474-478`.

Impacto:

- Puede mostrarse "completado" cuando en realidad se cancelÃ³ o no hay run activo.
- Riesgo de no iniciar polling en algunos casos de `analyzing` real (especialmente con progreso 0).

---

### HI-16 - Watchdog del heavy slot con condicion dudosa al marcar error del proceso stale

Evidencia:

- Tras timeout de heavy slot, solo marca error si estado NO es `running/queued_for_heavy`: `api-server/routers/_analysis_phases.py:1498-1503`.

Impacto:

- El caso mas peligroso (run stale aun en `running`) puede no quedar marcado como error.
- Diagnostico y recuperacion quedan inconsistentes.

---

### HI-17 - `run_timeline` falla en modo no-critico y sin seÃ±al clara al usuario

Evidencia:

- En fallo de timeline, se registra warning y se continua: `api-server/routers/_analysis_phases.py:3343-3346`.
- No se emite estado degradado explicitamente hacia UX (solo logs tecnicos).

Impacto:

- El usuario puede creer que "todo se analizo" cuando una parte relevante (cronologia) fallo.

---

### HI-18 - Mapeo de analisis parcial no contempla fase `timeline`

Evidencia:

- `FRONTEND_TO_BACKEND` no define `timeline`: `api-server/routers/_partial_analysis.py:40-63`.
- El endpoint parcial rechaza fases desconocidas: `api-server/routers/analysis.py:1115-1117`.

Impacto:

- No se puede pedir de forma coherente un parcial orientado a cronologia.
- Se rompe la promesa de granularidad funcional por fase/tarea.

---

### HI-19 - Deteccion de hardware/servicios con fallback silencioso puede infra-activar capacidades

Evidencia:

- Timeout de deteccion hardware cae a fallback CPU con `except/pass`: `api-server/routers/system.py:783-793`.
- Deteccion de Ollama usa timeout corto (3s) y clasifica no disponible en errores/timeout: `api-server/routers/system.py:844,857-862`.

Impacto:

- Equipos capaces pueden aparecer como limitados por timeout puntual.
- Configuracion por capacidad puede quedar suboptima.

## 14.3 Medios nuevos

### ME-06 - Tipo API de `analysis_status` desalineado con estados reales del backend

Evidencia:

- Tipo API no contempla `queued`/`cancelled`: `frontend/src/types/api/projects.ts:10`.
- Transformer usa fallback a `completed` si el campo falta: `frontend/src/types/transformers/projects.ts:64`.

Impacto:

- Riesgo de tipado engaÃ±oso y de defaults optimistas en estados no contemplados.

---

### ME-07 - Instalacion de dependencias Python sin timeout/no-input (posible cuelgue indefinido)

Evidencia:

- `subprocess.run` de pip sin `timeout`: `api-server/routers/system.py:488-495`.
- No se observa bandera no-interactiva explicita (`--no-input`).

Impacto:

- Instalaciones pueden quedar colgadas sin feedback claro de bloqueo.

---

### ME-08 - Polling de modelos/dependencias puede quedar activo tras error

Evidencia:

- `pollModelsStatus()` solo se detiene en `all_required_installed`: `frontend/src/stores/system.ts:324-331`.
- En error de dependencias en dialogo se cambia fase a error, pero no se llama `stopPolling()`: `frontend/src/components/ModelSetupDialog.vue:347-363`.

Impacto:

- TrÃ¡fico de polling innecesario y estado de fondo confuso.

---

### ME-09 - Mensajeria de instalacion/progreso aun expone jerga tecnica para usuario no tecnico

Evidencia:

- UI muestra texto tecnico explicito: `frontend/src/components/ModelSetupDialog.vue:499` ("numpy, spaCy, transformers"), `:617` ("Python 3.10+").
- Durante analisis se publican acciones tecnicas (`GPU`, `LLM`): `api-server/routers/_analysis_phases.py:3387-3389`.

Impacto:

- Contradice el requisito de comunicacion no tecnica para corrector editorial/linguista.

## 14.4 Cobertura de tests (gaps adicionales)

- No se observa cobertura especifica para:
  - coherencia de progreso de `timeline` dentro de `PHASE_ORDER`.
  - comportamiento real end-to-end de `runPartialAnalysis` frontend (inicio vs finalizacion real).
  - contaminacion de estado cross-run por `_update_storage` sin `_run_id`.
  - clasificacion de estados en `ProjectsView` (`idle/cancelled/analyzing`).

## 14.5 Altos nuevos (tercera pasada)

### HI-20 - Contrato de `timeline` inconsistente entre gating frontend, mapping y backend

Evidencia:

- En el tab timeline se exige `required-phase="structure"` en vez de `timeline`: `frontend/src/views/ProjectDetailView.vue:317-323`.
- El store declara que timeline depende de `timeline` (no de `structure`) para gate parcial/completo: `frontend/src/stores/analysis.ts:140,90`.
- El mapping de progreso backend->frontend no incluye `timeline`: `frontend/src/stores/analysis.ts:184-198`.
- El endpoint parcial tampoco contempla `timeline` como fase frontend valida: `api-server/routers/_partial_analysis.py:40-63`.

Impacto:

- La UI puede mostrar timeline como "lista" sin haber ejecutado su fase real.
- Se rompe la trazabilidad de progreso y la promesa de analisis parcial coherente para timeline.

---

### HI-21 - `run_timeline` no chequea cancelacion durante el loop largo

Evidencia:

- Loop por capitulos sin `tracker.check_cancelled()` en `run_timeline`: `api-server/routers/_analysis_phases.py:3233-3252`.
- Otras fases largas si usan `check_cancelled` de forma explicita (ej. NER): `api-server/routers/_analysis_phases.py:1747`.

Impacto:

- Cancelaciones pueden tardar mucho en aplicarse si la timeline esta procesando documentos largos.
- Mayor ventana para escrituras stale y sensacion de bloqueo.

---

### HI-22 - Doble disparo de auto-configuracion en startup (riesgo de carrera y ruido UX)

Evidencia:

- `ModelSetupDialog` llama `autoConfigOnStartup()` en rama de "modelos listos": `frontend/src/components/ModelSetupDialog.vue:196`.
- Tambien vuelve a llamarlo en `startLLMDownloadIfNeeded()`: `frontend/src/components/ModelSetupDialog.vue:231`.
- `autoConfigOnStartup` limpia `llmDownloadingModels` en `finally` aunque la descarga sea asincrona: `frontend/src/stores/system.ts:592-607`.

Impacto:

- Posible duplicacion de acciones de arranque/descarga.
- Mensajeria de estado puede "parpadear" o desaparecer antes de tiempo.

---

### HI-23 - `analysis-status` usa heuristicas que pueden generar falsos positivos de fases ejecutadas

Evidencia:

- `coreference` y `attributes` se marcan en base a `has_entities`, no por evidencia de ejecucion real: `api-server/routers/projects.py:501-503`.
- Varias fases avanzadas se derivan de tener capitulos/entidades (heuristico), no de run ledger: `api-server/routers/projects.py:517-528`.

Impacto:

- Tabs/fases pueden aparecer como ejecutadas aunque no se hayan corrido realmente.
- Riesgo de saltar analisis necesarios o de ocultar botones de ejecucion parcial.

## 14.6 Medios nuevos (tercera pasada)

### ME-10 - `timeline` no se traduce desde progreso backend a estado frontend en vivo

Evidencia:

- `BACKEND_PHASE_TO_FRONTEND` no contiene `timeline`: `frontend/src/stores/analysis.ts:184-198`.

Impacto:

- Durante la corrida activa, la fase timeline no se marca como ejecutada en el store aunque backend la reporte.

---

### ME-11 - `SettingsView` mezcla `fetch` directo con cliente API unificado

Evidencia:

- Llamadas directas con `fetch` para hardware/config/estimates LLM: `frontend/src/views/SettingsView.vue:1253,1267,1279,1293,1319`.

Impacto:

- Inconsistencia en reintentos, manejo de errores y trazabilidad respecto al resto de la app.

## 15) Plan de ejecucion por sprints (accionable, con DoD)

### Sprint 0 (hotfix de estabilidad, 1 semana)

Objetivo: eliminar estados falsos y corrupcion de progreso.

Alcance:

1. Corregir `CR-01` (`set_action` en healthcheck Ollama).
2. Corregir `CR-02` (`/api/system/resources` con API publica).
3. Corregir `CR-07` (integrar `timeline` de forma consistente o absorberla formalmente en fase definida, sin indices duplicados ambiguos).
4. Corregir `CR-08` (flujo parcial frontend: distinguir "iniciado" vs "completado" y mantener polling real).

DoD:

- Tests de regresion para cada bug critico.
- Progreso monotono en analisis completo (sin saltos incoherentes).
- Analisis parcial no notifica finalizacion hasta estado terminal real.

### Sprint 1 (consistencia de orquestacion y concurrencia, 1-2 semanas)

Objetivo: eliminar contaminacion entre ejecuciones y robustecer colas.

Alcance:

1. Aplicar `_run_id` de forma sistematica (HI-13) o migrar rutas a `tracker._write`.
2. AÃ±adir `run_id` al parcial (HI-14) y completar persistencia (`analysis_progress`).
3. Revisar logica watchdog heavy slot (HI-16).
4. Corregir mapping parcial de `timeline` (HI-18) y contrato de gating/progreso timeline en frontend (HI-20, ME-10).
5. AÃ±adir cancel checks en `run_timeline` para corte rapido (HI-21).
6. Sustituir heuristicas de `analysis-status` por evidencia real de fase ejecutada (HI-23).

DoD:

- Cancel + reanalize repetido no cruza mensajes/estado entre runs.
- Tests concurrentes: 2 ejecuciones consecutivas del mismo proyecto.
- Trazabilidad de `run_id` en logs y storage.

### Sprint 2 (capabilities/configuracion y primera ejecucion, 1-2 semanas)

Objetivo: decisiones de motor/modelo correctas segun maquina y estados reales.

Alcance:

1. Cerrar brecha UI->backend de metodos (`CR-03`, `HI-08`).
2. Consumir `needs_restart` y flujo restart-required (HI-04 reforzado).
3. Endurecer deteccion hardware/servicios con estados explicitos de incertidumbre (HI-19).
4. Reconciliar recomendaciones de modelo con requisitos reales (HI-06).
5. Unificar orquestacion de auto-config startup para evitar dobles disparos (HI-22).

DoD:

- Configuracion elegida en UI impacta pipeline backend verificablemente.
- En escenario "restart required", UX guia al usuario sin bucles de reinstalacion.
- Capabilities separa `supported/installed/running`.

### Sprint 3 (reanalisis granular por impacto, 2-4 semanas)

Objetivo: cumplir requisito de recalculo minimo por personaje-relaciones-acciones.

Alcance:

1. DiseÃ±ar e implementar `entity-impact graph` (CR-05).
2. Invalidation selectiva y persistencia de `impact set` por corrida (HI-09).
3. Reuse tras cancel sin cambios (CR-04).

DoD:

- Caso "cambia personaje A" recomputa solo subgrafo afectado (tests dedicados).
- KPI: tiempo de reanalisis local <35% del full run.
- KPI: reuse post-cancel sin cambios >=80%.

### Sprint 4 (UX no tecnica y observabilidad, 1-2 semanas)

Objetivo: cero sensacion de bloqueo y cero fallos silenciosos accionables.

Alcance:

1. Sustituir jerga tecnica en progreso/descargas por mensajes de negocio (ME-09).
2. Heartbeat universal <=10s en tareas largas.
3. Eliminar respuestas ambiguas `success=true` en error real (HI-10).
4. Corregir polling/resolucion de estados en vistas de proyectos (HI-15, ME-08).
5. Unificar `SettingsView` con cliente API comun para errores/reintentos consistentes (ME-11).

DoD:

- Ninguna tarea larga sin actualizacion visible >10s.
- En error, siempre mensaje accionable + opcion de reintento/soporte.
- Estado visual coherente en `ProjectsView`, `StatusBar`, `ModelSetupDialog`.

## 16) Riesgos de implementacion y mitigaciones

- Riesgo: introducir regresiones en pipeline por cambios de fase/progreso.
  - Mitigacion: tests de contrato de progreso + snapshots de `analysis_progress_storage`.
- Riesgo: mayor complejidad en invalidador granular.
  - Mitigacion: rollout con fallback chapter-level/phase-level.
- Riesgo: sobrecoste de observabilidad.
  - Mitigacion: telemetria minima enfocada a KPIs y errores operativos.

## 17) Backlog ejecutable (tickets con solucion, DoD y pruebas)

### 17.1 Tickets priorizados

| Ticket | Prioridad | Hallazgos cubiertos | Solucion propuesta | DoD (Definition of Done) | Pruebas minimas |
|---|---|---|---|---|---|
| T-001 | P0 | CR-01 | Corregir `tracker.update_action` -> `tracker.set_action` en healthcheck Ollama y no degradar LLM por fallo de tracking. | No hay excepcion en healthcheck y `use_llm` depende solo de disponibilidad real. | Unit de `run_ollama_healthcheck` con `_ollama_init_started=True`. |
| T-002 | P0 | CR-07, HI-20, ME-10 | Unificar contrato de fase `timeline` (order/weights/backend/frontend mapping/gating). | Progreso monotono y timeline visible como fase real en UI y store. | E2E de analisis completo y parcial con timeline en progreso. |
| T-003 | P0 | CR-08 | Cambiar semantica parcial a `accepted` vs `completed`; mantener polling hasta estado terminal real. | `analysis-completed` solo se emite al finalizar backend. | E2E de parcial largo y validacion de evento tardio. |
| T-004 | P0 | HI-13, HI-14 | Propagar `run_id` a todas las escrituras concurrentes y al parcial. | No hay contaminacion entre runs tras cancel+reanalyze. | Test concurrente 2 runs seguidos mismo proyecto. |
| T-005 | P0 | HI-23 | Reemplazar heuristicas de `/analysis-status` por ledger real de fases ejecutadas. | Fases ejecutadas reflejan ejecucion real, no inferencias por conteo. | Contract test backend->frontend `analysis-status`. |
| T-006 | P0 | HI-15, ME-06 | Corregir mapeo de estados (`idle`, `cancelled`, `queued`, `analyzing`) en ProjectsView y tipos API. | Sin falsos "completed" por `idle`; sin defaults optimistas. | Unit/UI test de estados limite (`idle`, `cancelled`). |
| T-007 | P0 | CR-03, HI-08 | Persistir settings de analisis en `project.settings.analysis_features` y aplicarlos en pipeline. | Toggle en UI cambia ejecucion backend de forma verificable. | E2E "toggle -> run -> fases/metodos ejecutados". |
| T-008 | P1 | HI-21 | Insertar `check_cancelled` en loop timeline y checkpoints de persistencia. | Cancelacion efectiva en timeline <= 2-5s por checkpoint. | Test de cancel durante timeline de documento largo. |
| T-009 | P1 | HI-19, HI-06 | Endurecer deteccion de capacidades: estado `detection_uncertain`, retries y politica de recomendacion alineada a budget real. | No se infra-activa por timeout puntual. | Test con timeouts simulados y reintento exitoso. |
| T-010 | P1 | HI-22 | Hacer startup idempotente (lock/lease) para `autoConfigOnStartup`; una sola orquestacion. | No hay doble descarga/accion de startup. | Test de doble trigger simultaneo en arranque. |
| T-011 | P1 | ME-07, ME-08 | Instalacion Python no interactiva con timeout global+por paquete y stop polling robusto en error terminal. | Ninguna instalacion queda colgada sin mensaje accionable. | Test de timeout y recovery con reintento. |
| T-012 | P1 | ME-09, ME-11 | Lenguaje no tecnico en setup/progreso + unificacion de llamadas Settings a `apiClient`. | Mensajes claros para perfil editorial; errores consistentes. | RevisiÃ³n UX copy + tests de error handling. |
| T-013 | P2 | CR-05, HI-09 | Implementar impacto granular por subgrafo entidad-relacion-accion (no solo por fase). | Cambio local recomputa solo nodos afectados. | Suite de impacto local (personaje A aislado/conectado). |
| T-014 | P2 | PERF global | Concurrencia adaptativa para Tier-3 segun CPU/RAM/cola en vez de `max_workers=4` fijo. | Menor saturacion en equipos modestos sin penalizar equipos potentes. | Bench comparativo en 3 perfiles de hardware. |
| T-015 | P2 | Calidad global | Matriz de testing extremo automatizada para install/startup/pipeline/cancel/reanalyze/fallbacks. | Cobertura de regresion para rutas criticas y edge-cases. | CI con escenarios reproducibles y reportes KPI. |

### 17.2 Criterios transversales para cerrar cualquier ticket

- Debe incluir `error_code` estable, mensaje de usuario y accion recomendada.
- Debe incluir rollback claro (feature flag o fallback anterior).
- Debe registrar metricas: latencia, tasa de fallback, tasa de reintento y tasa de error.

## 18) Triage de falsos positivos (tercera validacion)

| Hipotesis previa | Estado tras revalidacion | Evidencia | Accion |
|---|---|---|---|
| "ProjectsView no contempla `analyzing`" | DESCARTADO (falso positivo) | `frontend/src/views/ProjectsView.vue:449-451` si contempla `analyzing`. | Cerrar hipotesis, mantener vigilancia de regresion. |
| "ProjectsView marca final correctamente siempre" | CONFIRMADO PROBLEMA | `idle -> completed` y fallback a `analyzing`: `frontend/src/views/ProjectsView.vue:471-478`. | Corregir mapping de estados (T-006). |
| "Timeline esta totalmente integrada en progreso oficial" | CONFIRMADO PROBLEMA | `PHASE_ORDER` sin timeline y uso de indices duplicados: `api-server/routers/analysis.py:16-30`, `api-server/routers/_analysis_phases.py:3212,3341,3369`. | Unificar contrato timeline (T-002). |
| "Parcial termina cuando backend termina" | CONFIRMADO PROBLEMA | `runPartialAnalysis` limpia estado en `finally`: `frontend/src/stores/analysis.ts:536-543`; emite completion inmediato: `AnalysisRequired.vue:101-108`. | Separar `accepted` vs `completed` (T-003). |
| "Guard stale por run_id cubre toda la pipeline" | CONFIRMADO PROBLEMA | `_update_storage` soporta `_run_id`, pero mayoria de llamadas no lo pasan: `api-server/routers/_analysis_phases.py:443-464` y llamadas sin `_run_id`. | Forzar `run_id` sistemico (T-004). |
| "Parcial tiene proteccion stale equivalente al full run" | CONFIRMADO PROBLEMA | Tracker parcial sin `run_id`: `api-server/routers/_partial_analysis.py:577-583`. | AÃ±adir `run_id` al parcial (T-004). |
| "Config UI de metodos gobierna backend de forma real" | CONFIRMADO PROBLEMA | UI guarda en `localStorage`: `useSettingsPersistence.ts`; backend espera `project.settings.analysis_features`: `_analysis_phases.py:1098-1123`. | Persistencia real por proyecto (T-007). |
| "Timeline parcial es pedible desde frontend" | CONFIRMADO PROBLEMA | No existe mapping timeline en parcial: `_partial_analysis.py:40-63`; fase desconocida se rechaza: `analysis.py:1115-1117`. | Corregir mapping + UX (T-002). |
| "Cancelacion corta rapido siempre" | CONFIRMADO PROBLEMA | `run_timeline` no chequea cancelacion en loop: `_analysis_phases.py:3233-3252`. | AÃ±adir checkpoints de cancel (T-008). |
| "Startup de autoconfig es una sola orquestacion" | CONFIRMADO PROBLEMA | Doble llamada `autoConfigOnStartup`: `ModelSetupDialog.vue:196,231`. | Idempotencia startup (T-010). |
| "Tipos frontend cubren todos los estados reales backend" | CONFIRMADO PROBLEMA | `ApiAnalysisStatus` sin `queued/cancelled`: `frontend/src/types/api/projects.ts:10`. | Alinear tipos + mappers (T-006). |
| "No hay fallos silenciosos en rutas criticas" | CONFIRMADO PROBLEMA | Multiples `except: pass` en routers/store (evidencia por busqueda). | Catalogo de errores + observabilidad minima (T-011/T-015). |

## 19) Criterios de optimizacion de flujo y carga de maquina (sin sobrecarga)

### 19.1 Politica de ejecucion recomendada

- Concurrencia adaptativa: calcular workers de Tier-3 por perfil (`CPU fisicos`, `RAM libre`, cola activa), evitando `max_workers` fijo.
- Presupuesto dinamico: limitar fases LLM si memoria efectiva cae bajo umbral y activar fallback inmediato.
- Backpressure: una cola pesada global + cola ligera separada, con fairness por proyecto para evitar starvation.
- Cancelacion cooperativa: checkpoints obligatorios cada bloque de trabajo largo y antes de persistir.

### 19.2 Politica de degradacion/fallback

- Estado explicito por capacidad: `supported`, `installed`, `running`, `degraded`, `detection_uncertain`.
- Si falla un metodo: intentar alternativa del mismo nivel funcional (no bajar directamente a modo minimo).
- Si no hay alternativa: avisar al usuario en lenguaje no tecnico + accion concreta (`reintentar`, `cerrar apps pesadas`, `contactar soporte`).

### 19.3 KPIs de rendimiento y estabilidad (objetivo operativo)

- Uso de CPU sostenido en fases no criticas dentro de limites configurables (evitar saturacion continua al 100%).
- Tasa de cancelacion efectiva < 5s en 95p para tareas largas.
- Reanalisis incremental local < 35% de full run en casos de cambios acotados.
- Tasa de falsos "completed" en UI: 0%.
- Ningun tramo de >10s sin heartbeat visible en setup/analisis.

### 19.4 Stress tests extremos obligatorios

- Documento grande + baja RAM + cola de 2 proyectos.
- Cancelar/reanudar en loops largos (NER, timeline, enrichments).
- Timeout de deteccion hardware + recuperacion posterior.
- Falla de Ollama/Java/Python durante startup y durante corrida.
- Doble trigger de instalacion/descarga desde dos puntos UI.

## 20) Configuracion simple, accesible y comprensible para correctores no tecnicos

### 20.1 Principios UX obligatorios

- Lenguaje editorial, no tecnico: evitar nombres de librerias, siglas y detalles de driver.
- Progresive disclosure: vista basica por defecto y "Opciones avanzadas" colapsadas.
- Presets claros: `Rapida`, `Equilibrada`, `Maxima precision`, con descripcion de impacto en tiempo.
- Estados claros: `Listo`, `Preparando`, `Descargando`, `Instalando`, `Analizando`, `Parcial`, `Error`.

### 20.2 Arquitectura de configuracion recomendada

- Config global de app: solo preferencias de interfaz.
- Config por proyecto: metodos de analisis y sensibilidad (persistidos en backend).
- Bloqueo guiado: si un metodo no es compatible, mostrarlo desactivado con explicacion breve y alternativa.
- Boton unico "Aplicar recomendada para mi equipo" con previsualizacion de cambios.

### 20.3 Accesibilidad y comprension (criterios auditables)

- Cumplir WCAG AA en contraste, foco visible, teclado y mensajes de estado (`aria-live`).
- Cada ajuste debe incluir: que hace, impacto de tiempo, impacto de precision, recomendacion.
- Mensajes de error en 3 capas: que paso, que puede hacer ahora, cuando contactar soporte.
- Prohibido dejar estados ambiguos (`success=true` con error real o spinner infinito sin contexto).

### 20.4 Copys de referencia (no tecnicos)

- En vez de "Instalando numpy/spacy/transformers": "Preparando componentes de analisis del texto".
- En vez de "GPU no compatible (Compute Capability...)": "Tu equipo usara modo estandar para mantener estabilidad".
- En vez de "Timeout Ollama": "El motor avanzado no respondio a tiempo. Seguimos en modo basico y puedes reintentar desde Configuracion".

## 21) Meta-validacion del documento (2026-03-03, revision 6)

### 21.1 Estado de hallazgos criticos en codigo actual

- `CR-01`: CERRADO en workspace actual. Healthcheck usa `tracker.set_action(...)` en `api-server/routers/_analysis_phases.py:1645`.
- `CR-02`: CERRADO en workspace actual. `/api/system/resources` usa API publica de `ResourceManager` en `api-server/routers/system.py:1342-1343`.
- `CR-03`: CERRADO a nivel MVP funcional (ya no abierto):
  - Refuerzo final de "backend como unica fuente de verdad" para settings de analisis:
    - `loadSettings()` ignora claves legacy de analisis en `localStorage` (`enabledNLPMethods`, `multiModelSynthesis`, `characterKnowledgeMode`) para evitar arrastre de estado local en CR-03.
    - Correccion de clonacion de defaults (evita compartir arrays/objetos anidados entre instancias y tests).
    - Archivo: `frontend/src/composables/useSettingsPersistence.ts`.
  - Cierre de carrera `SettingsView -> Reanalizar`:
    - `useSettingsPersistence` registra sync pendientes por proyecto y expone `waitForPendingAnalysisSettingsSync(projectId)`.
    - `ProjectDetailView.startReanalysis()` espera ese sync pendiente antes de llamar a `/api/projects/{id}/reanalyze`.
    - Evita iniciar reanalisis con settings viejos si el usuario sale de Configuracion y relanza de inmediato.
    - Archivos: `frontend/src/composables/useSettingsPersistence.ts`, `frontend/src/views/ProjectDetailView.vue`.
  - Settings de analisis pasan a backend como fuente de verdad en ejecucion; se elimina dependencia de migracion/sync desde `localStorage` en el flujo de analisis/reanalisis: `frontend/src/stores/analysis.ts`, `frontend/src/views/ProjectDetailView.vue`.
  - `SettingsView` carga settings de analisis desde backend para el proyecto activo y sincroniza cambios al backend de forma reactiva: `frontend/src/views/SettingsView.vue`, `frontend/src/composables/useSettingsPersistence.ts`.
  - Persistencia local conserva solo ajustes UI/globales; excluye `enabledNLPMethods`, `multiModelSynthesis`, `characterKnowledgeMode`: `frontend/src/composables/useSettingsPersistence.ts`.
  - Backend consume `analysis_features` y `nlp_methods` en runtime: `api-server/routers/_analysis_phases.py:1148,1213,1719,2704,4482`.
  - Validacion estricta runtime contra capabilities antes de ejecutar (bloqueo de metodos inviables): `api-server/routers/_analysis_phases.py` (`_filter_nlp_methods_by_runtime_capabilities`).
  - Consumo fino de ortografia con seleccion exacta de votantes (`patterns/symspell/hunspell/pyspellchecker/languagetool/beto/llm_arbitrator`) y fusion de issues al flujo de correcciones: `api-server/routers/_analysis_phases.py`.
  - `nlp_methods.character_knowledge` ya controla modo real `rules|llm|hybrid` con fallback seguro si `use_llm=false`: `api-server/routers/_enrichment_phases.py`.
  - Gating efectivo para flags de pipeline (incluyendo `name_variants`, `multi_model_voting`, `spelling`): `api-server/routers/_analysis_phases.py:1153-1161,2723,2925,4213,4238,4262,4495,4564` y `api-server/routers/analysis.py:908`.
  - Tests de soporte: `tests/unit/test_cr03_runtime_settings.py` + `frontend/src/stores/__tests__/analysis.spec.ts` + `frontend/src/composables/__tests__/useSettingsMigration.spec.ts` + `frontend/src/composables/__tests__/useSettingsPersistence.spec.ts`.
- `CR-07`: CERRADO. `timeline` integrada en `PHASE_ORDER` y tracker dinamico por clave.
- `CR-08`: CERRADO. Analisis parcial distingue `accepted` (POST ok) de `completed` (fin real):
  - `runPartialAnalysis()` ya no limpia estado en `finally`; solo limpia en error de POST.
  - `AnalysisRequired.vue` emite `analysis-completed` via `watch(isExecuted)` (estado real), no al retorno del POST.
  - `setAnalyzing(false)` limpia `runningPhases` al detectar fin via polling.
  - Archivos: `frontend/src/stores/analysis.ts`, `frontend/src/components/analysis/AnalysisRequired.vue`.

### 21.2 Estado de hallazgos timeline/progreso

- `HI-18`: CERRADO. Mapping parcial incluye `timeline`.
- `ME-10`: CERRADO. Mapping backend->frontend incluye `timeline`.
- `HI-20`: CERRADO. Gating UI por fase real `timeline`.
- `HI-21`: CERRADO. Loop de timeline con `check_cancelled`.
- `CR-07a`: CERRADO. Full analysis gatea timeline por `run_temporal`: `api-server/routers/analysis.py:897`.

### 21.3 Estado de hallazgos run_id / concurrencia

- `HI-13`: CERRADO. Todas las escrituras de progreso migradas a `tracker.update_storage()` con `run_id` automatico (36 callsites).
  - Wrapper seguro: `tracker.update_storage()` pasa `self.run_id` a `_update_storage()`.
  - Tests: `tests/unit/test_run_id_guard.py` (7 tests).
- `HI-14`: CERRADO. Analisis parcial genera `run_id = uuid4().hex[:12]`, propagado via `ctx["run_id"]` al tracker.
  - `api-server/routers/analysis.py`: genera run_id en storage + ctx.
  - `api-server/routers/_partial_analysis.py`: tracker recibe run_id.

### 21.4 Estado de hallazgos analysis-status / estados UI

- `HI-23`: CERRADO. `get_analysis_status()` usa run ledger (tablas `analysis_runs`/`analysis_phases`) como fuente primaria, con fallback heuristico para proyectos legacy.
  - Run ledger se persiste en `run_completion()` y en parcial completion via `AnalysisRepository`.
  - Archivos: `api-server/routers/_analysis_phases.py`, `api-server/routers/_partial_analysis.py`, `api-server/routers/projects.py`.
- `HI-15`: CERRADO. Polling de `ProjectsView` corregido:
  - `idle` ya no se mapea a `completed`; trigger refetch para obtener estado real de DB.
  - `failed`/`error`/`cancelled` se manejan explicitamente.
  - `queued_for_heavy` mapeado a `queued`.
  - Archivo: `frontend/src/views/ProjectsView.vue`.
- `ME-06`: CERRADO. Tipos API alineados:
  - `ApiAnalysisStatus` incluye `queued` y `cancelled`.
  - Transformer default cambiado de `'completed'` a `'pending'` cuando `analysis_status` es falsy.
  - Archivos: `frontend/src/types/api/projects.ts`, `frontend/src/types/transformers/projects.ts`.

### 21.5 Matriz actualizada de CR-03

Estado por bloques:

- Persistencia/validacion API: `OK`
- Sync UI->backend en flujo de analisis: `OK`
- Aplicacion de `pipeline_flags` en runtime: `OK`
- Consumo runtime de `nlp_methods` (base): `OK`
- Tests contract/runtime/store: `OK`

Resultado:

- Gap original de CR-03 ("settings no gobiernan ejecucion"): **CERRADO**.

### 21.6 Pendientes reales (no bloqueantes)

- P1:
  - E2E pipeline completo `PATCH settings -> run -> verificacion de artefactos/fases`.
- P2:
  - `CR-05`: incrementalidad fina por subgrafo entidad-relacion-accion.

### 21.7 Estado de pruebas (revalidado)

- Backend:
  - `pytest tests/unit/test_cr03_runtime_settings.py tests/api/test_project_settings.py tests/unit/test_run_id_guard.py -q`
  - Resultado: `26 passed`
- Frontend:
  - `vue-tsc --noEmit`: OK
  - `vitest run src/types/__tests__/transformers.spec.ts src/stores/__tests__/analysis.spec.ts src/stores/__tests__/projects.spec.ts`
  - Resultado: `115 passed` (42 + 52 + 21)

### 21.8 Tickets P0 completados (sprint 2026-03-03)

| Ticket | Hallazgo | Commit | Resumen |
|--------|----------|--------|---------|
| T-003 | CR-08 | `a1fe7c8` | Parcial espera fin real via polling, no POST accepted |
| T-004 | HI-13/HI-14 | `edd2217` | run_id propagado a 36 callsites + parcial |
| T-005 | HI-23 | `c4c0a15` | analysis-status basado en run ledger real |
| T-006 | HI-15/ME-06 | `d6c6b4b` | Tipos API completos + polling ProjectsView corregido |

### 21.9 Tickets P1 completados (sprint 2026-03-04)

| Ticket | Hallazgo | Commit | Resumen |
|--------|----------|--------|---------|
| T-008 | HI-21 | (ya resuelto) | `check_cancelled` ya presente en loop de run_timeline |
| T-009 | HI-19/HI-06 | `775dd31` | Retry Ollama, detection_status/warnings, CPU → llama3.2 |
| T-010 | HI-22 | `51dd3ac` | autoConfigOnStartup idempotente + fix llmDownloadingModels |
| T-011 | ME-07/ME-08 | `e891e72` | pip timeout 5min + stopPolling en error terminal |
| T-012 | ME-09/ME-11 | `e8b8d7c` | Mensajeria no tecnica + fetch → apiClient en SettingsView |

### 21.10 Re-priorizacion recomendada desde este estado

- P0 inmediato:
  - **Sin pendientes criticos abiertos.** Todos los P0 (T-003..T-006) y P1 priorizados (T-008..T-012) cerrados.
- P1 restante:
  - E2E de pipeline completo.
- P2:
  - CR-05 arquitectonico (incrementalidad fina).

### 21.11 Recomendacion de uso de documentos

- Documento base: version para stakeholders y seguimiento ejecutivo.
- Documento extremo: referencia tecnica de implementacion, QA y tracking por sprints, incluyendo estado historico + meta-validacion viva.

### 21.12 Actualizacion de cierre (2026-03-05)

- `HI-12`: CERRADO con hardening adicional en sidecar startup:
  - Arranque en dos fases (`liveness` y `readiness`) sin falso `running`.
  - Limpieza de `child` stale al iniciar (si el proceso previo ya termino).
  - Estado `warming` explicito y watchdog activo en `Ok`.
  - Archivo: `src-tauri/src/main.rs`.

- `HI-17`: CERRADO de forma completa en UX:
  - Se mantiene banner de fase degradada para `timeline`.
  - Se agrega accion de reintento aislado desde la propia vista (`runPartialAnalysis(['timeline'])`), sin forzar reanalisis completo.
  - Archivo: `frontend/src/views/ProjectDetailView.vue`.

- `CR-05`: MEJORA aplicada (no cierre total del objetivo arquitectonico):
  - Se persiste contexto del planner incremental por corrida (`impacted_nodes`, `changed_chapter_numbers`, `incremental_reason`) en `analysis_progress.stats`.
  - Se serializa el bloque `planner` en `analysis_runs.config_json` para trazabilidad de decisiones por run.
  - Archivo: `api-server/routers/_analysis_phases.py`.
  - Estado: **parcialmente cerrado** respecto al objetivo original de subgrafo entidad-relacion-accion completo.

- `HI-16`: CERRADO con hardening adicional del watchdog heavy-slot:
  - Si detecta run stale real, marca error en memoria y sincroniza tambien `project.analysis_status=error` en BD.
  - No pisa estados terminales (`completed`, `error`, `cancelled`) y evita falsos positivos cuando el run stale ya fue reemplazado (match por `run_id` y `claim_ts`).
  - Archivo: `api-server/routers/_analysis_phases.py`.
  - Tests: `tests/unit/test_hi16_heavy_slot_watchdog.py`.

- `CR-07` (robustez): mejora de mantenibilidad en orquestador principal:
  - Se elimina dependencia de indices hardcodeados en skips de fases y skips incrementales (`start_phase/end_phase` por `phase_key`).
  - Reduce riesgo de desalineacion futura al insertar/reordenar fases.
  - Archivo: `api-server/routers/analysis.py`.
