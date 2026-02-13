# Auditoría Técnica Exhaustiva

Fecha de auditoría: 2026-02-13  
Documento: ampliación profunda de `docs/CODE_FINDINGS_2026-02-12.md`  
Ámbito revisado: frontend Vue/Pinia, backend FastAPI, orquestación de análisis, Tauri/Rust, CI/CD, tests, seguridad, memoria/rendimiento y documentación operativa.

## 1) Resumen ejecutivo

Estado general: el proyecto tiene base técnica sólida y ambición alta, pero hoy existen riesgos críticos de consistencia funcional y operativa que impiden afirmar "no habrá problemas" en producción sin una fase de hardening.

Conclusión ejecutiva:
- El riesgo más serio no es un bug aislado; es la desalineación entre contratos (frontend/backend), orquestación de análisis y gates de calidad.
- Hay problemas concretos con impacto directo para cliente/editorial (glosario, cancelación/estado de análisis, análisis parcial).
- Hay riesgo real de degradación de rendimiento en equipos con recursos limitados si se encadenan análisis concurrentes.

## 2) Método y límites de esta auditoría

Se revisó estáticamente el código y configuración de todo el repo con evidencia por archivo/línea.  
No se modificó implementación.  
No se ejecutó una batería completa end-to-end en entorno real Windows/macOS durante esta pasada.

Cobertura estructural observada:
- Routers backend con endpoints declarados: 233 (suma de `rg -c @router ...`).
- Módulos de integración backend: 6 (`tests/integration/*.py`).
- Tests e2e frontend presentes, pero no integrados en CI estándar de PR.

## 3) Hallazgos críticos

### F-001 [CRÍTICO] Colisión de rutas de glosario entre routers

Evidencia:
- `api-server/routers/entities.py:2563` GET `/api/projects/{project_id}/glossary`
- `api-server/routers/entities.py:2594` POST `/api/projects/{project_id}/glossary`
- `api-server/routers/entities.py:2647` DELETE `/api/projects/{project_id}/glossary/{entry_id}`
- `api-server/routers/content.py:13` GET `/api/projects/{project_id}/glossary`
- `api-server/routers/content.py:63` POST `/api/projects/{project_id}/glossary`
- `api-server/routers/content.py:198` DELETE `/api/projects/{project_id}/glossary/{entry_id}`
- Orden de registro:
  - `api-server/main.py:531` `app.include_router(entities.router)`
  - `api-server/main.py:552` `app.include_router(content.router)`

Impacto funcional:
- Riesgo de que el frontend reciba payloads incompatibles según qué router resuelva la ruta.
- `GlossaryTab` espera shape de `content.py`:
  - `frontend/src/components/workspace/GlossaryTab.vue:171` usa `data.data.entries`.
- `entities.py` devuelve lista plana (sin `entries`) y esquema distinto.

Riesgo cliente/editorial:
- Pérdida/ocultación de campos de glosario (definición, variantes, flags), comportamiento errático al crear/editar.

Optimización recomendada:
- Unificar definitivamente el dominio glosario en un solo router.
- Si se mantiene compatibilidad legacy, usar rutas versionadas o alias explícitos, nunca la misma ruta/método en dos routers.
- Añadir tests de contrato para `/glossary` y CRUD completo.

### F-002 [CRÍTICO] “Análisis parcial” expuesto en frontend sin contrato backend equivalente

Evidencia:
- Front:
  - `frontend/src/stores/analysis.ts:431` `runPartialAnalysis(...)`
  - `frontend/src/stores/analysis.ts:458` POST `/api/projects/${projectId}/analyze` con `{ phases, force }`
  - `frontend/src/components/analysis/AnalysisRequired.vue:104` invoca `runPartialAnalysis`
- Back:
  - `api-server/routers/analysis.py:212` endpoint `/analyze`
  - `api-server/routers/analysis.py:213` firma `file: Optional[UploadFile] = File(None)` (sin `phases/force`)
  - No endpoint dedicado de análisis parcial.

Impacto funcional:
- La UI promete ejecutar solo fases dependientes, pero el backend no refleja ese contrato.
- Riesgo de ejecución completa cuando el usuario cree que es parcial.

Riesgo UX/PO:
- Fricción y pérdida de confianza: el producto “dice una cosa” y hace otra.

Optimización recomendada:
- Definir contrato explícito para análisis parcial (endpoint, schema, validaciones y respuesta de progreso por fase).
- O retirar temporalmente la opción de UI hasta cerrar backend y tests.

### F-003 [CRÍTICO] Máquina de estados de cancelación/errores inconsistente

Evidencia:
- Cancelación en progreso:
  - `api-server/routers/analysis.py:666` set `status = "cancelled"`
- Chequeo de cancelación lanza excepción genérica:
  - `api-server/routers/_analysis_phases.py:170`
  - `api-server/routers/_analysis_phases.py:177` `raise Exception("Análisis cancelado por el usuario")`
- Captura global de excepciones en flujo principal:
  - `api-server/routers/analysis.py:466` `except Exception as e:`
  - `api-server/routers/analysis.py:467` `handle_analysis_error(ctx, e)`
- Error handler fuerza estado `error`:
  - `api-server/routers/_analysis_phases.py:2887` `status = "error"`

Impacto funcional:
- Una cancelación puede terminar reportándose como error.
- Estado final poco fiable para UI, soporte y métricas.

Optimización recomendada:
- Introducir excepción tipada `AnalysisCancelled` y tratarla fuera del flujo de error.
- Definir tabla de transiciones de estado (state machine) y validarla en tests.

### F-004 [CRÍTICO] Riesgo de saturación de memoria/CPU por concurrencia Tier 1 no limitada

Evidencia:
- Se crea un hilo por análisis:
  - `api-server/routers/analysis.py:513` `threading.Thread(..., daemon=True)`
- Diseño explícito:
  - `api-server/routers/analysis.py:282-283` Tier 1 corre para todos los proyectos, solo Tier 2 es exclusivo.
- Gate de cola pesada ocurre después de parse/classificación/estructura:
  - `api-server/routers/analysis.py:415-422`

Impacto rendimiento:
- En ráfagas de análisis, múltiples documentos grandes pueden parsearse en paralelo.
- Riesgo de degradación severa (equipo lento, ventiladores, bloqueo percibido).

Riesgo cross-platform:
- En Mac y Windows de gama media/baja el impacto puede ser visible rápidamente.

Optimización recomendada:
- Límite global de concurrencia para Tier 1 (semaforización + backpressure).
- Cola central de jobs con política FIFO/prioridades y límite de encolado.
- Exponer métricas de cola/concurrencia para diagnóstico.

### F-005 [CRÍTICO] Cola pesada guarda contexto completo en memoria (incluye texto completo)

Evidencia:
- Encolado guarda `tier1_context` completo y `tracker`:
  - `api-server/routers/_analysis_phases.py:680-683`
- El contexto incluye objetos pesados:
  - `api-server/routers/_analysis_phases.py:487` `ctx["raw_document"]`
  - `api-server/routers/_analysis_phases.py:488` `ctx["full_text"]`
  - `api-server/routers/_analysis_phases.py:638` `ctx["chapters_data"]`

Riesgo:
- Con varios proyectos en cola, la RAM crece por acumulación de contenido completo.
- Riesgo de colgado/desaceleración del equipo en escenarios de uso intensivo.

Optimización recomendada:
- Encolar solo referencias ligeras (project_id, rutas temporales, metadata mínima).
- Persistir snapshots intermedios en DB/disco y reconstruir contexto al reanudar.
- Límite de longitud de cola + rechazo controlado con mensaje UX.

## 4) Hallazgos altos

### F-006 [ALTA] Contrato de estados FE/BE desalineado y fallback peligroso en transformador

Evidencia:
- Backend usa estados reales:
  - `api-server/routers/analysis.py:429` `analysis_status = "queued"`
  - `api-server/routers/analysis.py:286` `analysis_status = "analyzing"`
  - `api-server/routers/_analysis_phases.py:2859` `"completed"`
  - `api-server/routers/_analysis_phases.py:2906` `"error"`
- Front API types dicen “exact match” pero no incluyen `queued`:
  - `frontend/src/types/api/projects.ts:4`
  - `frontend/src/types/api/projects.ts:10`
- Transformador fuerza default a `completed` si falta estado:
  - `frontend/src/types/transformers/projects.ts:58`

Impacto:
- Estados desconocidos pueden enmascararse como “completado”.
- Riesgo de decisiones UX incorrectas (tabs habilitadas cuando no procede).

Optimización recomendada:
- Enum de estados único compartido por contrato (OpenAPI + generación de tipos).
- Fallback a `unknown`, nunca a `completed`.

### F-007 [ALTA] Ruta SSE de progreso con cierre terminal incompleto y timeout incongruente

Evidencia:
- SSE cierra en `completed` o `failed`:
  - `api-server/routers/analysis.py:763`
  - `api-server/routers/analysis.py:773`
- Estados reales incluyen `error/cancelled`:
  - `api-server/routers/analysis.py:666`
  - `api-server/routers/_analysis_phases.py:2887`
- Timeout SSE 10 minutos:
  - `api-server/routers/analysis.py:719`
- Timeout del slot pesado 30 minutos:
  - `api-server/deps.py:79`

Impacto:
- Riesgo de stream colgado hasta timeout o de error falso en análisis largos.

Optimización recomendada:
- Cierre explícito del stream en `error`, `cancelled`, `queued_for_heavy`.
- Alinear timeout SSE con SLA real del análisis.

### F-008 [ALTA] Estados globales de orquestación parcialmente muertos/incompletos

Evidencia:
- Variables globales declaradas:
  - `api-server/deps.py:64` `_active_analysis_project_id`
  - `api-server/deps.py:68` `_analysis_queue`
- Uso real de `_analysis_queue` solo en cancelación:
  - `api-server/routers/analysis.py:628`
  - `api-server/routers/analysis.py:632`
- No hay alta en esa cola en flujo principal.

Impacto:
- Diseño confuso y difícil de mantener.
- Riesgo de bugs sutiles al asumir colas que en la práctica no gobiernan el flujo.

Optimización recomendada:
- Eliminar estado legacy no usado o completar implementación.
- Documentar state machine real en código + tests de transición.

### F-009 [ALTA] Guard de concurrencia insuficiente permite reentradas en estado `queued`

Evidencia:
- Guard actual:
  - `api-server/routers/analysis.py:240` solo bloquea si `analysis_status == "analyzing"`.
- Estado `queued` se marca durante flujo:
  - `api-server/routers/analysis.py:429`.

Impacto:
- Se pueden lanzar nuevos análisis sobre proyecto ya encolado.
- Riesgo de duplicación de trabajo y consumo extra de memoria.

Optimización recomendada:
- Guard en estados no terminales: `analyzing`, `queued`, `queued_for_heavy`, `running`.

### F-010 [ALTA] CI de PR no garantiza calidad frontend ni integración real

Evidencia:
- CI estándar con filtros de paths sin `frontend/**`:
  - `.github/workflows/ci.yml:10-23`
- Tolerancias a fallo:
  - `.github/workflows/ci.yml:80` `mypy ... || true`
  - `.github/workflows/ci.yml:109` integración `|| true`
  - `.github/workflows/ci.yml:142` performance `|| true`
- Summary depende solo de `unit-tests` y `lint`:
  - `.github/workflows/ci.yml:155`
- Tests frontend están en workflow de release/tag:
  - `.github/workflows/build-release.yml:92`
  - `.github/workflows/build-release.yml:230`

Impacto QA:
- Riesgo alto de regresiones frontend y de integración backend no detectadas en PR.

Optimización recomendada:
- Añadir workflow PR para frontend (`type-check`, `vitest`, smoke e2e).
- Quitar `|| true` en jobs críticos o separarlos como no bloqueantes explícitos.

### F-011 [ALTA] Cobertura de tests crítica incompleta en rutas sensibles

Evidencia:
- Sin tests para SSE:
  - búsqueda sin resultados de `analysis/stream` en `tests/`.
- Sin tests backend para glosario:
  - búsqueda sin resultados de `/glossary` en `tests/`.
- Sin tests frontend para componentes críticos:
  - no tests para `GlossaryTab` ni `AnalysisRequired` (sin resultados por nombre).
  - `useAnalysisStream` sin spec dedicado; solo existe el archivo fuente.

Impacto:
- Bugs contractuales pueden llegar a producción sin detección temprana.

Optimización recomendada:
- Test matrix mínima obligatoria:
  - contrato API glosario,
  - cancelación/estado terminal análisis,
  - análisis parcial,
  - sincronización estados FE/BE.

### F-012 [ALTA] Suite de performance desfasada respecto a API actual

Evidencia:
- Firma actual del detector:
  - `src/narrative_assistant/analysis/semantic_redundancy.py:216-220` (`detect(chapters, max_duplicates=...)`)
- Tests llaman parámetros no soportados:
  - `tests/performance/test_semantic_redundancy_performance.py:163` (`mode=...`)
  - `tests/performance/test_semantic_redundancy_performance.py:457` (`threshold=...`)
- Test referencia atributo interno no garantizado:
  - `tests/performance/test_semantic_redundancy_performance.py:579` `_faiss_available`

Impacto:
- Métricas de performance no fiables como señal de release.

Optimización recomendada:
- Actualizar tests al contrato actual o restaurar API anterior de forma explícita.
- Añadir test de firma pública para evitar drift silencioso.

## 5) Hallazgos medios

### F-013 [MEDIA] `useAnalysisStream` está desacoplado del flujo activo y sin cobertura

Evidencia:
- Definido en `frontend/src/composables/useAnalysisStream.ts`.
- No hay uso real más allá de export:
  - `frontend/src/composables/index.ts:21-22`
  - sin llamadas a `useAnalysisStream(...)` fuera del propio archivo.

Impacto:
- Código muerto con alto riesgo de quedar obsoleto.
- Mantener dos caminos (polling vs SSE) incrementa complejidad.

Optimización recomendada:
- Elegir un único camino productivo y eliminar/reintegrar el otro con tests.

### F-014 [MEDIA] Inconsistencias de estado de cancelación en frontend store

Evidencia:
- `frontend/src/stores/analysis.ts:268` tras cancelar, estado local pasa a `idle`.
- Test lo valida:
  - `frontend/src/stores/__tests__/analysis.spec.ts:626`

Impacto:
- Se pierde semántica de “cancelado” para trazabilidad UX/soporte.

Optimización recomendada:
- Mantener `cancelled` como estado explícito y normalizar transición posterior a `idle`.

### F-015 [MEDIA] Validación “safe” de rutas permisiva sin `allowed_dir`

Evidencia:
- `src/narrative_assistant/parsers/sanitization.py:346` `validate_file_path_safe`
- `src/narrative_assistant/parsers/sanitization.py:402` check estricto solo si `allowed_dir is not None`
- `src/narrative_assistant/parsers/sanitization.py:431-440` rama de validación básica sin perímetro.

Impacto:
- Reduce defensa en profundidad si un caller omite `allowed_dir`.

Optimización recomendada:
- Hacer `allowed_dir` obligatorio en flujo de producción.

### F-016 [MEDIA] Permisos de ruta “estricta” amplios (incluye home completo)

Evidencia:
- `src/narrative_assistant/parsers/sanitization.py:268-273` incluye `Path.home()` y temp dir.

Impacto:
- Superficie de acceso mayor de la necesaria.

Optimización recomendada:
- Reducir a directorios de trabajo/app data y rutas explícitas configuradas.

### F-017 [MEDIA] Logging excesivo en hot path de base de datos

Evidencia:
- `src/narrative_assistant/persistence/database.py:1503` log `info` en cada `get_database`.
- `src/narrative_assistant/persistence/database.py:1514` log `info` en reutilización.

Impacto:
- Ruido operativo y posible impacto en rendimiento I/O/logs.

Optimización recomendada:
- Bajar a `debug` o muestreo.

### F-018 [MEDIA] Drift documental/versionado visible para cliente

Evidencia:
- Canon real:
  - `VERSION:1` `0.9.3`
  - `pyproject.toml:3` `0.9.3`
  - `frontend/package.json:3` `0.9.3`
  - `src-tauri/Cargo.toml:3` `0.9.3`
- Documentación desactualizada:
  - `README.md:142` `0.3.0`
  - `docs/README.md:4` `0.7.17`
  - `docs/PROJECT_STATUS.md:4` `0.7.17`

Impacto:
- Mensaje de producto inconsistente para cliente, soporte y QA.

Optimización recomendada:
- Pipeline de sincronización automática de versión + lint de docs.

### F-019 [MEDIA] Requisito de Python inconsistente entre app y backend deps

Evidencia:
- `pyproject.toml:10` `requires-python = ">=3.11"`
- `api-server/deps.py:33` `MIN_PYTHON_VERSION = (3, 10)`

Impacto:
- Mensajes de instalación/confianza contradictorios.

Optimización recomendada:
- Unificar versión mínima y su mensaje en todas las capas.

## 6) Hallazgos de hardening Tauri / cross-platform

### F-020 [ALTA] Firma y hardening incompletos en configuración de bundle

Evidencia:
- `src-tauri/tauri.conf.json:30` `certificateThumbprint: null`
- `src-tauri/tauri.conf.json:32` `timestampUrl: ""`
- `src-tauri/tauri.conf.json:39` `signingIdentity: "-"`
- `src-tauri/tauri.conf.json:73` CSP con `style-src 'unsafe-inline'`
- `src-tauri/tauri.conf.dev.json:54` `shell.open = true` (dev)

Impacto:
- Riesgo de fricción de confianza (SmartScreen/Gatekeeper) y postura de seguridad débil.

Optimización recomendada:
- Completar cadena de firma release (Windows/macOS) y endurecer CSP en producción.

### F-021 [MEDIA] Acoplamiento fuerte a Python 3.12 en runtime macOS

Evidencia:
- `src-tauri/src/main.rs:394`
- `src-tauri/src/main.rs:438`
- `src-tauri/src/main.rs:462`
- `src-tauri/src/main.rs:488`
- `src-tauri/src/main.rs:496`

Impacto:
- Menor flexibilidad de empaquetado/migración.

Optimización recomendada:
- Resolver versión dinámicamente desde bundle o metadata de build.

### F-022 [MEDIA] Divergencia de toolchain en workflows de release

Evidencia:
- `build-release.yml` usa Python 3.12:
  - `.github/workflows/build-release.yml:22`
  - `.github/workflows/build-release.yml:129`
- `release.yml` usa Python 3.11:
  - `.github/workflows/release.yml:29`
  - `.github/workflows/release.yml:97`

Impacto:
- Riesgo de comportamiento distinto entre pipelines de release.

Optimización recomendada:
- Unificar versión y validar compatibilidad en una única matriz controlada.

## 7) Memoria, rendimiento y estabilidad del equipo del usuario

Riesgos observados:
- Análisis concurrentes Tier 1 sin límite explícito (`api-server/routers/analysis.py:282-283`, `api-server/routers/analysis.py:513`).
- Contextos completos de documentos en cola pesada (`api-server/routers/_analysis_phases.py:680-683`, `api-server/routers/_analysis_phases.py:487-488`).
- Monitor de presión de memoria robusto existe, pero en pipeline no usado por router activo:
  - `src/narrative_assistant/pipelines/unified_analysis.py:755`
  - `src/narrative_assistant/pipelines/unified_analysis.py:761`
  - sin uso directo en `api-server/routers/analysis.py`.

Fortalezas existentes:
- Gestión de recursos avanzada ya implementada:
  - `src/narrative_assistant/core/resource_manager.py:431`
  - `src/narrative_assistant/core/resource_manager.py:479`
- Front `DocumentViewer` con lazy loading + LRU:
  - `frontend/src/components/DocumentViewer.vue:254-277`
  - `frontend/src/components/DocumentViewer.vue:434-455`

Recomendación de optimización:
- Reutilizar el `ResourceManager` en el flujo real de API.
- Añadir límites de concurrencia por proceso y por proyecto.
- Medir p95/p99 de RAM y CPU durante análisis de documentos grandes antes de release.

## 8) Perspectiva funcional (cliente/editorial)

Riesgos visibles para usuario final:
- Glosario potencialmente inconsistente por colisión de endpoints (crear/editar/listar).
- Acción de “análisis parcial” no garantizada, con posible ejecución completa.
- Cancelación que puede acabar reportándose como error.
- Estados de análisis que no reflejan fielmente el backend en todas las capas tipadas.

Qué significa para el negocio:
- Menor confianza en resultados.
- Mayor coste de soporte (tickets “comportamiento raro” difícil de reproducir).
- Riesgo reputacional si se promete precisión/estabilidad sin hardening previo.

## 9) Plan de optimización priorizado

### P0 (inmediato, antes de siguiente release)
- Unificar rutas de glosario (eliminar colisión `entities.py` vs `content.py`).
- Cerrar contrato de análisis parcial (o retirar feature temporalmente).
- Arreglar máquina de estados de cancelación con excepción tipada.
- Añadir límite de concurrencia Tier 1 y límite de cola pesada.
- Endurecer CI de PR (frontend + integración básica obligatoria).

### P1 (sprint siguiente)
- Unificar enum de estados FE/BE y regenerar tipos desde OpenAPI.
- Añadir tests de contrato para endpoints críticos (glossary, analysis progress/cancel).
- Reducir estado global en memoria y formalizar state machine.
- Resolver drift de versión/docs.

### P2 (2-3 sprints)
- Integrar ResourceManager en el flujo activo de API.
- Revisar estrategia de persistencia de jobs (durabilidad y recuperación).
- Hardening final de Tauri signing/CSP con checklist release.

## 10) Señales positivas (importantes)

- Arquitectura con separación de dominios amplia (routers y módulos de análisis especializados).
- Existencia de watchdog backend en Tauri:
  - `src-tauri/src/main.rs:143`
- Sanitización HTML con DOMPurify:
  - `frontend/src/utils/sanitizeHtml.ts:32`
- Estrategias de UX rendimiento en visor de documento (lazy + LRU):
  - `frontend/src/components/DocumentViewer.vue:254`

## 11) Cierre

La base es potente y ya contiene muchas piezas maduras, pero el sistema necesita cerrar brechas de contrato, estado y QA para ofrecer fiabilidad de nivel editorial-profesional en Windows y Mac sin sorpresas operativas.
