# Auditoria integral de recursos, instalacion, inicializacion, pipeline y reanalisis incremental

Fecha: 2026-03-02  
Repositorio: `d:\repos\tfm`  
Tipo: auditoria tecnica exhaustiva (sin implementar cambios)

## 1. Alcance y objetivo

Se audito extremo a extremo:

- Instalacion y post-instalacion.
- Primera ejecucion y ejecuciones posteriores.
- Deteccion de capacidades de maquina y activacion de metodos/modelos.
- Descarga, inicializacion y arranque de Python/Ollama/Java/LanguageTool/modelos.
- Pipeline de analisis y manejo de progreso en tareas largas.
- Fallbacks y manejo de errores (incluyendo fallos silenciosos).
- Reanalisis incremental, incluyendo el requisito adicional de granularidad fina por entidad-relacion-accion.

Se evaluo:

- Correccion funcional.
- Robustez en escenarios de fallo.
- Coherencia entre recomendacion de hardware y comportamiento real.
- UX de progreso para evitar sensacion de bloqueo.
- Cobertura de pruebas y huecos de testing.

## 2. Evidencia y validacion ejecutada

Pruebas ejecutadas:

- `pytest -q tests/unit/test_invalidation.py tests/unit/test_version_diff_and_planner.py tests/integration/test_incremental_planner_modes.py`
- Resultado: `36 passed, 1 deselected`.

Busquedas de cobertura:

- No aparecen tests para rutas/areas clave de esta auditoria:
  - `run_ollama_healthcheck` / bug de `update_action`.
  - `/api/system/resources`.
  - `autoConfigOnStartup`.
  - Consumo real backend de `enabledNLPMethods`.
  - Flujos de `needs_restart` en frontend.

## 3. Resumen ejecutivo

Estado general: base funcional buena, pero con gaps importantes para tu objetivo de robustez y optimizacion fina.

Puntos fuertes:

- Hay base de invalidacion y planner incremental.
- Hay UX de progreso en primera configuracion y analisis.
- Hay fallbacks relevantes (CPU fallback en Ollama, degradacion sin LLM, LanguageTool opcional).

Riesgos principales detectados:

1. Bug funcional en healthcheck de Ollama durante analisis (llamada a metodo inexistente).
2. Endpoint de recursos con acceso a atributos no validos.
3. Configuracion de metodos en UI no conectada de forma clara a ejecucion backend.
4. Incrementalidad todavia gruesa: por fase/tipo global, no por grafo de impacto entidad-relacion-accion.
5. Varios tramos best-effort con catches silenciosos que ocultan fallos al usuario.

## 4. Hallazgos (priorizados)

## 4.1 Criticos

### CR-01 - Bug real en analisis: `run_ollama_healthcheck` llama a un metodo inexistente

Evidencia:

- `api-server/routers/_analysis_phases.py:653` define `set_action`.
- `api-server/routers/_analysis_phases.py:1556` llama `tracker.update_action(...)` (no existe).
- `api-server/routers/_analysis_phases.py:1571-1573` captura la excepcion y desactiva `use_llm`.

Impacto:

- Cuando `_ollama_init_started` es `True`, puede caer en excepcion y degradar a analisis sin LLM aunque el sistema pudiera usarlo.
- Resultado funcional potencialmente inferior sin aviso claro de causa.

Recomendacion:

- Corregir llamada al metodo correcto y cubrir con test de regresion para ese branch concreto.

---

### CR-02 - Endpoint `/api/system/resources` potencialmente roto por atributos privados incorrectos

Evidencia:

- `api-server/routers/system.py:1342-1343` usa `rm._running_tasks` y `rm._heavy_task_semaphore.available`.
- `src/narrative_assistant/core/resource_manager.py:170-179` expone `active_tasks` y `available_slots`.
- `src/narrative_assistant/core/resource_manager.py:413-418` expone `heavy_task_semaphore` via propiedad publica.

Impacto:

- Riesgo de error 500 al consultar recursos.
- Telemetria operativa inconsistente o inutilizable.

Recomendacion:

- Usar API publica del `ResourceManager` y agregar test de endpoint.

---

### CR-03 - Configuracion de metodos NLP en Settings no esta claramente conectada al motor de analisis backend

Evidencia:

- Persistencia local:
  - `frontend/src/composables/useSettingsPersistence.ts:48` (`localStorage`).
  - `frontend/src/composables/useSettingsPersistence.ts:133-135` guarda local y emite evento local.
  - `frontend/src/composables/useNLPMethods.ts:93-108` toggles solo en estado local.
- Inicio de analisis:
  - `frontend/src/stores/analysis.ts:311-320` envia solo `file` y `mode`.
- Backend espera otra estructura:
  - `api-server/routers/_analysis_phases.py:1103-1123` lee `project.settings.analysis_features`.
- No hay rastro en frontend de `analysis_features` (busqueda sin coincidencias).

Impacto:

- El usuario puede creer que activa/desactiva metodos soportados, pero el backend puede no obedecer esa configuracion.
- Riesgo directo contra tu requerimiento principal.

Recomendacion:

- Unificar contrato frontend-backend de configuracion de metodos y hacerlo verificable.

---

### CR-04 - Reanalisis tras cancelar no reutiliza artefactos aunque no haya cambios

Evidencia:

- Fast-path requiere estado previo `completed`:
  - `api-server/routers/analysis.py:652`.
- Cancelacion mueve a estados no reutilizables:
  - `api-server/routers/analysis.py:1336` (`pending`).
  - `api-server/routers/analysis.py:1362` (`cancelled` en progreso).

Impacto:

- Si paras y relanzas, se pierde oportunidad de optimizacion.
- Contradice el requisito de ahorrar tiempo/recursos en reanalisis.

Recomendacion:

- Definir politica de reutilizacion segura para estados cancelados (por fase y por huella).

---

### CR-05 - Incrementalidad fina por entidad-relacion-accion incompleta

Evidencia:

- Planner actual de impacto:
  - `api-server/routers/_incremental_planner.py:15-28` grafo simple de 4 nodos Tier 3.
  - `api-server/routers/_incremental_planner.py:56-76` heuristicas por `chapter_diff` + flags.
- Enrichment ejecuta caches mayormente globales:
  - `api-server/routers/_enrichment_phases.py:557-628` llamadas `_run_enrichment` sin `entity_scope`.
  - `api-server/routers/_enrichment_cache.py:131` y `:228` prioriza `entity_scope IS NULL`.
- Servido de stale global:
  - endpoints con `allow_stale=True` (relaciones/prosa/voz), por ejemplo:
    - `api-server/routers/relationships.py:32`
    - `api-server/routers/prose.py:157`
    - `api-server/routers/voice_style.py:67`

Impacto:

- Existe base incremental, pero no propagacion fina tipo:
  - "cambio en personaje X -> recalcular solo vecinos y acciones afectadas".
- Se recalcula/expone demasiado global para tu objetivo.

Recomendacion:

- Introducir planner de impacto con grafo de dependencias entidad-relacion-capitulo-accion y recomputacion por alcance.

## 4.2 Altos

### HI-01 - Timeouts y manejo de timeout de descarga fragiles

Evidencia:

- `api-server/routers/system.py:630` usa `as_completed(..., timeout=600)`.
- `api-server/routers/system.py:633` usa `future.result(timeout=300)`.
- El timeout del iterador `as_completed` puede propagarse fuera del `try` interno.

Impacto:

- En redes lentas/modelos grandes, fallos prematuros o thread abortado sin cierre limpio.

Recomendacion:

- Diseñar timeouts por etapa + recuperacion uniforme (incluido timeout global del iterador).

---

### HI-02 - Auto-config de arranque con silencios amplios (frontend)

Evidencia:

- `frontend/src/stores/system.ts:578-580`
- `frontend/src/stores/system.ts:596-598`
- `frontend/src/stores/system.ts:603-605`
- `frontend/src/stores/system.ts:609-611`

Impacto:

- Fallos de start/pull/readiness pueden pasar desapercibidos.
- El usuario no entiende por que no esta "listo".

Recomendacion:

- Elevar errores relevantes a mensajes de estado de negocio (no tecnicos), con accion sugerida.

---

### HI-03 - Inconsistencias de requisitos/recomendaciones de modelos por hardware

Evidencia:

- `api-server/routers/system.py:1078` recomienda `qwen3` en CPU.
- `src/narrative_assistant/llm/ollama_manager.py:126-133` `qwen3` con `min_ram_gb=12.0`.
- `src/narrative_assistant/llm/config.py:241` RAPIDA usa `qwen3` core.
- `src/narrative_assistant/llm/config.py:463` RAPIDA aparece "siempre disponible".

Impacto:

- Recomendaciones pueden no ser ejecutables en maquinas justas.
- Riesgo de intentos de descarga no optimos y degradacion de UX.

Recomendacion:

- Unificar matriz de capacidad/recomendacion/descarga en una sola fuente de verdad.

---

### HI-04 - Readiness y auto-descarga pueden intentar cores no viables para ese equipo

Evidencia:

- Readiness marca missing de modelos core:
  - `api-server/routers/_llm_helpers.py:148-156`.
- Auto-config intenta descargar `missing_models`:
  - `frontend/src/stores/system.ts:591-596`.
- Pull bloquea por RAM minima:
  - `api-server/routers/services.py:348-357`.
- Errores de ese pull en auto-config se ignoran:
  - `frontend/src/stores/system.ts:596-598`.

Impacto:

- Bucle de "faltan modelos core" aunque haya fallback usable.
- Sensacion de setup incompleto permanente en algunos equipos.

Recomendacion:

- Readiness debe reflejar "ready con fallback suficiente" de forma coherente y accionable.

---

### HI-05 - Mutacion global de `KNOWN_MODELS` en runtime

Evidencia:

- `src/narrative_assistant/core/model_manager.py:1183` asigna `KNOWN_MODELS[...] = attempt_info`.

Impacto:

- Estado global mutable, potencialmente no determinista entre sesiones/hilos/pruebas.

Recomendacion:

- Evitar mutacion global; persistir seleccion efectiva en metadatos locales por instalacion.

---

### HI-06 - Verificacion hash no bloqueante para wheel

Evidencia:

- `src/narrative_assistant/core/model_manager.py:1389-1391` explicita que no bloquea.
- `src/narrative_assistant/core/model_manager.py:1414-1422` warning y continua.

Impacto:

- Se puede continuar con artefacto inesperado/corrupto sin fail hard.

Recomendacion:

- Definir politica por entorno: fail hard en produccion, warning solo en modo desarrollo.

---

### HI-07 - Se sirven resultados stale en varios endpoints de enrichment

Evidencia:

- `api-server/routers/relationships.py:32` (`allow_stale=True`).
- `api-server/routers/prose.py:157` (`allow_stale=True`).
- `api-server/routers/voice_style.py:67` (`allow_stale=True`).

Impacto:

- El usuario puede ver analisis obsoleto tras cambios.

Recomendacion:

- Etiquetado visible de stale + invalidacion/recompute dirigida.

---

### HI-08 - `run_cleanup` invalida todo el cache de enrichment del proyecto

Evidencia:

- `api-server/routers/_analysis_phases.py:1018-1024`.

Impacto:

- Recalculo mas amplio del necesario.
- Penaliza tu objetivo de ahorro de recursos.

Recomendacion:

- Sustituir por invalidacion selectiva basada en diff e impacto.

---

### HI-09 - Fallos al marcar enrichment `failed` pueden quedar silenciosos

Evidencia:

- `api-server/routers/_enrichment_phases.py:117-118` (`except Exception: pass`).

Impacto:

- Puede perderse señal de error real y dejar estado ambiguo.

Recomendacion:

- Registrar al menos warning estructurado y bandera de degradacion.

---

### HI-10 - Instalacion de dependencias sin guard de concurrencia

Evidencia:

- `api-server/routers/system.py:452` inicia tarea siempre.
- Se setea `INSTALLING_DEPENDENCIES=True` pero no se rechaza una segunda peticion concurrente.

Impacto:

- Riesgo de ejecuciones de `pip` solapadas y estados inconsistentes.

Recomendacion:

- Bloqueo idempotente del endpoint + respuesta "ya en curso".

---

### HI-11 - Señal `needs_restart` del backend no se consume en frontend

Evidencia:

- Backend la calcula/devuelve:
  - `api-server/routers/system.py:344-347`
  - `api-server/routers/system.py:362`
- No hay usos de `needs_restart` en `frontend/src` (busqueda sin coincidencias).

Impacto:

- El usuario recibe error generico en vez de instruccion clara de reinicio.

Recomendacion:

- Manejo explicito de `needs_restart` en flujo de setup.

---

### HI-12 - Capabilities mezclan "soportable" con "actualmente arrancado"

Evidencia:

- `api-server/routers/system.py:903`, `:947`, `:973`, `:1037` usan `ollama_available` (running actual) para `available/default_enabled`.
- `api-server/routers/system.py:837-859` si instalado pero no arrancado, se reporta no disponible.

Impacto:

- UI puede deshabilitar metodos que el hardware soporta pero servicio no arranco aun.

Recomendacion:

- Separar banderas: `supported_by_hardware`, `installed`, `running`, `ready`.

---

### HI-13 - Divergencia de scripts espejo (`scripts/` vs `src-tauri/resources/`)

Evidencia:

- `scripts/download_models.py:108-113` contempla `download_transformer_ner`.
- `src-tauri/resources/download_models.py:108-112` no contempla `transformer_ner`.
- `scripts/download_models.py:170-179` descarga transformer NER; el de resources no.

Impacto:

- Comportamiento distinto segun flujo de empaquetado/ejecucion.

Recomendacion:

- Unificar fuente unica o validacion CI de paridad entre scripts espejo.

## 4.3 Medios

### ME-01 - Mensajeria de instalacion mezcla mensajes de exito con fallos no fatales

Evidencia:

- `scripts/post_install.py:470-478` continua tras fallar Ollama/LLM.
- `scripts/post_install.py:480` reporta "Instalacion completada correctamente."

Impacto:

- Puede inducir falsa sensacion de sistema totalmente listo.

Recomendacion:

- Mensaje final diferenciado: completo / parcial / fallido con pasos sugeridos.

---

### ME-02 - Progreso de dependencias Python poco granular pese a existir script verbose

Evidencia:

- Setup usa `install_dependencies` con polling binario (`installing`) via `/api/models/status`.
- Existe `src-tauri/resources/install_deps_verbose.py` con salida estructurada `PROGRESS|...` pero sin integracion observada.

Impacto:

- En instalaciones largas, UX con barra indeterminada y menor confianza.

Recomendacion:

- Integrar progreso por paquete/descarga en flujo real de instalacion.

---

### ME-03 - `LanguageTool` status en error devuelve `success=True` con fallback "not_installed"

Evidencia:

- `api-server/routers/services.py:528-537`.

Impacto:

- Fallos reales de estado pueden enmascararse como no instalado.

Recomendacion:

- Mantener `success=False` con error de negocio distinguible.

---

### ME-04 - Progreso intra-fase de analisis desigual (riesgo de sensacion de bloqueo)

Evidencia:

- Updates de progreso parciales localizados:
  - `api-server/routers/_analysis_phases.py:1756`
  - `api-server/routers/_analysis_phases.py:3469`
- Varias fases largas solo cambian al inicio/fin.

Impacto:

- En documentos grandes, puede parecer que se queda "parado".

Recomendacion:

- Subfases y heartbeats por chunk en NER/fusion/consistency/grammar/enrichment.

---

### ME-05 - `analysis_features` parece via no operativa en estado actual

Evidencia:

- Backend lo lee:
  - `api-server/routers/_analysis_phases.py:1103-1123`.
- En proyecto se marca settings como "reserved for future":
  - `api-server/routers/projects.py:445`.
- No se encontro emision clara desde frontend de `analysis_features`.

Impacto:

- Configurabilidad declarada pero no plenamente operacional.

Recomendacion:

- Definir contrato oficial de configuracion por proyecto y persistencia efectiva.

## 5. Reanalisis incremental: estado real vs requisito solicitado

Requisito pedido:

- Si cambia un personaje, recalcular solo lo afectado (personajes relacionados, acciones derivadas, etc.).

Estado actual:

- Hay incremental por fases Tier 3 (relationships/voice/prose/health).
- Hay invalidacion por eventos de entidad/atributo.
- Pero la ejecucion principal de enriquecimientos sigue mayormente global.

Conclusion:

- Base incremental existente: si.
- Incremental fino por grafo de impacto entidad-relacion-accion: todavia no.

## 6. UX de progreso y comunicacion al usuario no tecnico

Fortalezas:

- `ModelSetupDialog.vue` separa fases (`starting/checking/installing-deps/downloading/downloading-llm`).
- Mensajes generalmente orientados a usuario final.
- Polling adaptativo en analisis (`useAnalysisPolling.ts`).

Gaps:

- En varios puntos hay catches silenciosos (auto-config, polling, pulls).
- Algunos textos siguen tecnicos (`numpy`, `spaCy`, `transformers`, `Ollama`) en setup.
- Falta mensaje uniforme de "sistema ocupado" en todos los caminos de recuperacion/error.

## 7. Cobertura de fallback y anti-silent-failure

Lo positivo:

- Fallback CPU en errores VRAM de Ollama (`llm/client.py`).
- Degradacion a modo sin LLM si no esta disponible.
- LanguageTool puede iniciarse automaticamente si ya instalado.

Lo pendiente:

- Reducir silencios (`except: pass` / catches vacios) en rutas criticas de instalacion/arranque.
- Exponer al usuario causas y accion sugerida de forma no tecnica.

## 8. Casos de test extremos recomendados (no implementados)

### 8.1 Instalacion y primer arranque

- Red lenta extrema (modelo > timeout global).
- DNS intermitente / mirrors alternos.
- Python presente pero `pip` roto.
- Ollama instalado no arrancable.
- Java ausente + descarga LT fallida en mirror principal.
- Reinicio requerido en modo frozen.

### 8.2 Ejecucion y pipeline

- Cancelar en cada fase (incluyendo llamadas LLM largas).
- Reanalizar inmediatamente tras cancelar.
- Documento igual, fingerprint igual, estado previo no completed.
- Cambios minimos por entidad con muchas relaciones.
- Cambios solo de atributos vs solo de menciones vs merge/reject.

### 8.3 Configuracion

- Metodo marcado localmente como habilitado pero no soportado en backend.
- Nivel de calidad LLM incompatible con RAM efectiva.
- Fallback disponible pero core ausente.

### 8.4 Observabilidad y UX

- Verificar que siempre hay feedback visible cada N segundos en tareas largas.
- Verificar que no hay ramas sin mensaje al usuario en fallo.

## 9. Priorizacion sugerida (orden de correccion)

1. CR-01, CR-02, CR-03.
2. CR-04, CR-05.
3. HI-01, HI-02, HI-03, HI-04.
4. Resto de hallazgos altos.
5. Medios y deuda de testing.

## 10. Veredicto final

La aplicacion tiene una base solida para deteccion de capacidades, fallback y progreso, pero hoy no cumple al nivel optimo tu objetivo de:

- activacion fiable de metodos segun maquina,
- comunicacion continua sin silencios,
- y reanalisis incremental fino por impacto real de entidad-relacion-accion.

La mayor brecha no es de ausencia total de arquitectura incremental, sino de granularidad efectiva y de cierre de ramas silenciosas en setup/arranque/reintentos.

