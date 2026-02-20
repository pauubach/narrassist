# Plan Fase 3: Aceleración Incremental e Identidad de Manuscrito

Fecha: 2026-02-19
Estado: Propuesta técnica detallada (lista para implementación por sprints)

## 1. Objetivo

Diseñar e implementar un sistema que:

1. Acelere reanálisis posteriores sin romper coherencia entre fases dependientes.
2. Distinga de forma robusta entre:
   - la misma obra con revisiones,
   - y un manuscrito realmente distinto.
3. Mejore el seguimiento de progreso editorial por versiones (qué mejoró, qué empeoró, qué cambió).
4. Permita bloquear, en flujo local, intentos de reutilizar un proyecto con un manuscrito distinto.

## 2. Principios de diseño

1. No asumir independencia entre fases: usar invalidación por dependencias.
2. Separar dos decisiones distintas:
   - decisión de cómputo (`full run` vs `incremental`),
   - decisión de identidad/licencia (`misma obra` vs `obra distinta`).
3. Nunca usar solo “% capítulos cambiados” para identidad de obra.
4. Evitar revelar señales sensibles anti-fraude en la UI.
5. Mantener fallback seguro a `full run` si la evidencia incremental no es suficiente.

## 3. Contexto actual (resumen)

1. Ya existe fast-path para fingerprint exacto (documento idéntico).
2. Ya existe caché NER por capítulo.
3. Ya existe historial básico de versiones (`version_metrics`) y snapshots.
4. Existe comparación pre/post con diffs de alertas y entidades.

Limitaciones actuales relevantes:

1. El incremental está concentrado en NER; otras fases siguen recálculo completo.
2. Enriquecimientos no aprovechan `input_hash` para saltar cómputo antes de ejecutar.
3. El matcher de similitud documental aún es débil para fraude/licencias.
4. El detalle de “mejora por versión” sigue siendo limitado para producto.

## 4. Requisitos funcionales nuevos

## 4.1 Aceleración incremental con dependencias

1. Detectar impacto por capítulo, entidad, relación y evento.
2. Recalcular solo nodos del grafo afectados.
3. Recalcular completo cuando el impacto global supere umbrales de seguridad.

## 4.2 Identidad de manuscrito robusta

1. Clasificar cada reemplazo/subida en:
   - `same_exact`,
   - `same_revision`,
   - `different_document`,
   - `uncertain`.
2. Soportar cambios de nombre de personajes entre versiones.
3. Incluir señales textuales y narrativas (entidades, relaciones, hechos/eventos).
4. Bloquear flujo si se detecta `different_document`.

## 4.3 Mejora de versiones para usuario

1. Informar en resumen/historial:
   - alertas resueltas/nuevas/sin cambio,
   - cambios de entidades relevantes,
   - renombres detectados de personajes,
   - cambios estructurales (capítulos nuevos/eliminados/reordenados).

## 5. Modelo de dependencias (impact graph)

Nodos mínimos:

1. Texto/capítulos.
2. NER.
3. Fusión de entidades.
4. Atributos.
5. Timeline/eventos/hechos.
6. Consistencia.
7. Grammar/prose.
8. Enrichments (relaciones, voz, salud).
9. Alertas.

Reglas de invalidación (ejemplos):

1. Cambio textual local:
   - invalida NER local + grammar/prose local.
2. Cambio en NER:
   - invalida fusión y derivados (atributos, relaciones, eventos, consistencia).
3. Merge/split/rename de entidad:
   - invalida relaciones, perfiles, timeline, eventos vinculados.
4. Cambio de atributos:
   - invalida checks de consistencia y partes de voz/perfiles.

Política de seguridad:

1. Si hay incertidumbre alta de impacto transversal, usar `full run`.
2. Si cambia estructura fuerte (muchas altas/bajas/reordenación), subir agresividad de invalidación.

## 6. Identidad de manuscrito: diseño de scoring

## 6.1 Señales textuales

1. Solape global normalizado de texto.
2. Similitud media por capítulo (no solo porcentaje de capítulos tocados).
3. Distribución de cambios por capítulo (media, mediana, p95).
4. Ratio de capítulos nuevos/eliminados.
5. Señal de reordenación de capítulos.
6. Ratio de texto nuevo no presente en versión anterior.

Nota clave:
`>40%` de capítulos modificados puede implicar `full run`, pero no implica manuscrito distinto.

## 6.2 Señales narrativas

1. Solape de entidades canónicas “estables”.
2. Solape de grafo de relaciones.
3. Solape de hechos/eventos narrativos.
4. Solape de anclas semánticas (frases/escenas clave).

## 6.3 Continuidad de personaje con cambio de nombre

Problema: un personaje puede renombrarse entre versiones.

Estrategia:

1. Construir una huella de identidad por personaje basada en contexto, no en nombre:
   - vecindario de co-ocurrencias,
   - relaciones frecuentes,
   - acciones/verbos asociados,
   - patrón de presencia por capítulos,
   - estilo de diálogo/intervención.
2. Resolver matching entre personajes versión N y N+1 por optimización bipartita (score compuesto).
3. Detectar:
   - `rename` (mismo personaje, nombre cambiado),
   - `split/merge`,
   - `new/remove`.
4. Mostrar en resumen de versión:
   “Personaje renombrado: A → B (confianza alta)”.

## 6.4 Clasificador final

1. Entrada: vector de señales textuales + narrativas + continuidad de entidades.
2. Salida: clase + confianza.
3. Política:
   - `same_exact`: fast-path máximo.
   - `same_revision`: incremental/full según impacto.
   - `different_document`: bloquear en ese proyecto.
   - `uncertain`: permitir con control de riesgo y contador acumulado por licencia/proyecto.

## 7. Política UI/UX

## 7.1 Flujo de reemplazo manuscrito

1. Acción recomendada: opción secundaria en menú de proyecto:
   - “Reemplazar manuscrito…”
2. No como botón primario global (acción poco frecuente y sensible).

## 7.2 Mensajería al usuario

Si `same_revision`:

1. Confirmación simple.
2. Mostrar resultados en resumen/historial de versiones.

Si `different_document`:

1. Error directo y claro:
   - “Este archivo parece un manuscrito distinto. Crea un proyecto nuevo.”
2. CTA:
   - “Crear nuevo proyecto con este archivo”.
3. No mostrar diagnóstico detallado (ni score ni señales) para evitar enseñar cómo burlar el sistema.

Si `uncertain`:

1. Mensaje neutro de validación:
   - “Hemos detectado cambios extensos; revisaremos este reemplazo con controles adicionales.”
2. Sin detalle técnico de señales.
3. Si la licencia ya está en `review_required` (por `uncertain > 3`):
   - bloquear reemplazo y proponer nuevo proyecto.

## 7.3 Dónde mostrar la nueva información

Recomendación:

1. Resumen principal:
   - delta corto de la última versión.
2. Historial de versiones:
   - tabla completa y comparaciones.
3. Comparación detallada:
   - panel/modal avanzado para usuarios que quieran trazabilidad fina.

## 8. Cambios de datos propuestos

## 8.1 Nuevas tablas

1. `manuscript_identity_checks`
   - `project_id`, `old_fingerprint`, `new_fingerprint`,
   - señales agregadas (json),
   - `classification`, `confidence`,
   - `blocked` (bool), `created_at`.
2. `entity_version_links`
   - mapeo entidad_vN -> entidad_vN1,
   - tipo de cambio (`unchanged`, `rename`, `split`, `merge`, `new`, `removed`),
   - score/confianza.
3. `identity_risk_events`
   - eventos de riesgo por clasificación `uncertain`.
4. `identity_risk_state`
   - estado agregado por licencia (`uncertain_count_rolling_30d`, `review_required`).

## 8.2 Extensión de `version_metrics`

Agregar campos agregados:

1. `alerts_new_count`, `alerts_resolved_count`, `alerts_unchanged_count`.
2. `critical_count`, `warning_count`, `info_count`.
3. `entities_new_count`, `entities_removed_count`, `entities_renamed_count`.
4. `chapter_added_count`, `chapter_removed_count`, `chapter_reordered_count`.
5. `run_mode` (`fast_path`, `incremental`, `full`).
6. `duration_total_sec`, opcional `phase_durations_json`.

## 9. API y flujo de ejecución

## 9.1 Endpoints nuevos/revisados

1. `POST /api/projects/{id}/document/replace`
   Ejecuta precheck de identidad y aplica política.
2. `GET /api/projects/{id}/identity/last-check`
   Solo para auditoría interna/soporte.
3. `GET /api/projects/{id}/versions`
   Extender payload con nuevos deltas y cambios de entidades.

## 9.2 Integración en pipeline

1. Antes de analizar tras reemplazo:
   - correr identidad documental.
2. Si bloqueado:
   - abortar análisis.
3. Si permitido:
   - calcular impacto,
   - escoger `fast_path/incremental/full`.
4. Al finalizar:
   - persistir métricas de versión ampliadas,
   - persistir links de continuidad de entidades.

## 10. Riesgos y mitigaciones

1. Falsos positivos de “documento distinto”.
   - Mitigar con ensemble de señales y modo `uncertain`.
2. Inconsistencia por incremental incompleto.
   - Mitigar con grafo de invalidación + fallback full.
3. Coste de almacenamiento.
   - Retención configurable y agregación compacta.
4. “Gaming” del sistema.
   - No exponer detalles de scoring ni umbrales en UI.

## 11. Plan por sprints

## 11.1 Sprint A: Bloqueo y clasificación base (textual + estructura)

Objetivo:

1. Bloquear reutilización de proyecto cuando el archivo es claramente otro manuscrito.
2. Introducir el flujo formal de reemplazo de manuscrito.

Alcance técnico:

1. Backend:
   - Crear módulo `manuscript_identity_service.py` (v1) con señales:
     - similitud global normalizada,
     - similitud media por capítulo,
     - ratio de capítulos nuevos/eliminados,
     - ratio de reordenación,
     - ratio de texto nuevo neto.
   - Salida tipada:
     - `classification`,
     - `confidence`,
     - `signals` (solo interno),
     - `reasons_internal`.
2. Persistencia:
   - Migración para `manuscript_identity_checks`.
   - Campos propuestos:
     - `id`, `project_id`, `old_fingerprint`, `new_fingerprint`,
     - `classification`, `confidence`,
     - `blocked`, `signals_json`, `created_at`.
3. API:
   - `POST /api/projects/{id}/document/replace`
     - Parsea el nuevo documento.
     - Ejecuta identidad.
     - Si `different_document` y confianza alta: bloqueo.
     - Si permitido: guarda archivo y marca proyecto para reanálisis.
   - `GET /api/projects/{id}/identity/last-check` para soporte/admin.
4. UI:
   - Añadir acción "Reemplazar manuscrito..." en menú secundario de proyecto.
   - Si bloqueado:
     - Mensaje genérico,
     - CTA "Crear nuevo proyecto".
   - No mostrar señales numéricas ni detalles de score.

Reglas de decisión v1:

1. `same_exact`:
   - fingerprints idénticos.
2. `same_revision`:
   - alta similitud textual global y baja divergencia estructural.
3. `different_document`:
   - baja similitud global + alta divergencia estructural.
4. `uncertain`:
   - zona intermedia.

Nota de seguridad:

1. Umbrales y pesos en backend/config, nunca en UI.
2. Logs con detalle solo en nivel debug interno.

Plan de pruebas Sprint A:

1. Unit:
   - corpus sintético de revisiones leves, medias y manuscritos distintos.
2. Integration:
   - flujo real `replace` -> `analyze`.
3. E2E:
   - UX bloqueo y CTA de nuevo proyecto.

Definition of Done Sprint A:

1. Reemplazo de manuscrito distinto bloquea en backend.
2. Reemplazo de revisión razonable no bloquea.
3. La UI no expone datos de diagnóstico anti-fraude.

## 11.2 Sprint B: Señales narrativas y continuidad de personajes (renombres)

Objetivo:

1. Mejorar robustez de identidad con señales narrativas.
2. Detectar cambios de nombre de personaje entre versiones.

Alcance técnico:

1. Nuevas señales para identidad:
   - solape de entidades por continuidad semántica,
   - solape de relaciones,
   - solape de hechos/eventos.
2. Servicio de continuidad de entidades (`entity_continuity_service.py`):
   - Entrada:
     - entidades versión N y N+1,
     - menciones,
     - relaciones,
     - capítulos.
   - Firma por entidad:
     - contexto lexical,
     - vecinos de co-ocurrencia,
     - grados y tipos de relación,
     - patrón de presencia por capítulo.
   - Matching:
     - matriz de similitud compuesta,
     - asignación uno-a-uno con umbral de confianza,
     - clasificación de cambios: `rename`, `merge`, `split`, `new`, `removed`, `unchanged`.
3. Persistencia:
   - Migración para `entity_version_links`.
   - Campos:
     - `project_id`, `old_version_num`, `new_version_num`,
     - `old_entity_id`, `new_entity_id`,
     - `change_type`, `confidence`, `evidence_json`.
4. Versionado:
   - Extender `version_metrics` con:
     - `entities_renamed_count`,
     - `entities_new_count`,
     - `entities_removed_count`.
5. API/UI:
   - Incluir en endpoint de versiones:
     - resumen de renombres detectados de alta confianza.
   - Mostrar en historial:
     - "Nombre cambiado: X -> Y".

Reglas de negocio para renombre:

1. Solo informar renombre si:
   - continuidad alta,
   - no hay evidencia fuerte de split/merge ambiguo.
2. Si ambiguedad alta:
   - marcar como `uncertain` interno, no mostrar en UI como hecho.

Plan de pruebas Sprint B:

1. Dataset curado con:
   - renombres verdaderos,
   - personajes nuevos con rol parecido,
   - casos de merge/split.
2. Validación:
   - precision/recall por tipo de cambio.
3. Revisión manual:
   - al menos 50 casos reales para ajustar umbrales.

Definition of Done Sprint B:

1. Clasificador de identidad mejora frente a Sprint A.
2. Renombres se detectan y aparecen en resumen de versiones con confianza adecuada.
3. No hay regresiones en métricas base de análisis.

## 11.3 Sprint C: Incremental dependiente avanzado (planner de impacto)

Objetivo:

1. Reducir tiempo de reanálisis sin romper consistencia.
2. Recalcular solo lo afectado por cambios reales.

Alcance técnico:

1. `impact_planner`:
   - Entrada:
     - `DocumentDiff`,
     - cambios de entidades/relaciones/eventos,
     - invalidaciones manuales.
   - Salida:
     - `phase_plan` con fases completas/parciales/skip.
2. Grafo de dependencias explícito:
   - texto -> NER -> fusión -> atributos -> consistencia/relaciones/eventos/voz/salud -> alertas.
3. Invalidación granular:
   - usar y extender `stale` en `enrichment_cache`.
   - eliminar `DELETE enrichment_cache` en cleanup full.
4. `input_hash` real por enrichment:
   - antes de `compute_fn`, calcular hash de inputs.
   - si `input_hash` coincide y estado es `completed`, skip inmediato.
5. Reanálisis parcial por alcance:
   - capítulos afectados,
   - entidades afectadas,
   - vistas globales recalculadas solo si cambia material global.
6. Fallbacks de seguridad:
   - si plan incierto -> `full run`,
   - si mismatch de consistencia post-run -> rerun global automático.

Separación obligatoria de políticas:

1. Criterio de `full run` por costo/riesgo computacional.
2. Criterio de identidad/licencia por continuidad de manuscrito.

Umbrales de ejemplo para planner (no licencia):

1. Muchos capítulos tocados pero cambios leves por capítulo:
   - puede seguir incremental.
2. Cambios estructurales severos:
   - preferir full run.

Plan de pruebas Sprint C:

1. Regression suite:
   - comparar output de incremental vs full en el mismo input.
2. Performance suite:
   - sin cambios,
   - cambios leves distribuidos,
   - cambios focalizados,
   - cambios estructurales.
3. SLO:
   - definir tiempos objetivo por escenario.

Definition of Done Sprint C:

1. Incremental produce resultados equivalentes a full (dentro de tolerancia definida).
2. Ahorro de tiempo medible en escenarios de revisión real.
3. Fallback automático cubre casos de alto riesgo.

## 11.4 Sprint D: Producto, métricas y observabilidad

Objetivo:

1. Hacer visible el valor para el usuario.
2. Medir precisión y rendimiento en producción.

Alcance técnico:

1. Extender `version_metrics`:
   - `alerts_new_count`, `alerts_resolved_count`, `alerts_unchanged_count`,
   - severidades por tipo,
   - cambios estructurales por capítulos,
   - `run_mode`, `duration_total_sec`, `phase_durations_json`.
2. API:
   - enriquecer `/versions` y `/versions/trend`,
   - endpoint de comparativa entre dos versiones con deltas extendidos.
3. UI:
   - resumen principal con delta de última versión,
   - historial de versiones enriquecido,
   - bloque de "cambios clave" (renombres, capítulos nuevos/eliminados, alertas resueltas).
4. Observabilidad:
   - métricas técnicas:
     - hit-rate por cache,
     - tiempos por fase,
     - ratio incremental/full.
   - métricas de identidad:
     - distribución de clasificaciones,
     - tasa de bloqueos,
     - tasa de revisiones anuladas por usuario (si aplica flujo `uncertain`).

Rollout:

1. Feature flags por componente:
   - identidad v2,
   - planner incremental,
   - UI avanzada de versiones.
2. Activación progresiva:
   - canary interno,
   - grupo beta,
   - despliegue completo.

Definition of Done Sprint D:

1. Usuario ve mejoras de versión de forma clara.
2. Equipo tiene paneles de observabilidad para ajustar umbrales.
3. Sistema estable tras rollout gradual.

## 11.5 Dependencias y orden de ejecución

1. Sprint A desbloquea control de reemplazo y bloqueo local.
2. Sprint B mejora precisión de identidad y añade continuidad de personajes.
3. Sprint C optimiza tiempo de cálculo con garantías de coherencia.
4. Sprint D productiza, mide y estabiliza.

Recomendación:

1. No iniciar Sprint C sin señales mínimas de Sprint B.
2. No cerrar Sprint D sin baseline comparativa pre/post.

## 11.6 Estimación orientativa (equipo 1 backend + 1 frontend + QA parcial)

1. Sprint A: 1.5-2 semanas.
2. Sprint B: 2-3 semanas.
3. Sprint C: 3-4 semanas.
4. Sprint D: 1.5-2 semanas.

Total estimado:

1. 8-11 semanas, con iteración de umbrales incluida.

## 11.7 Backlog técnico granular por sprint

## Sprint A: tareas concretas

1. Migraciones:
   - crear tabla `manuscript_identity_checks`,
   - índices por `project_id` y `created_at`.
2. Servicio:
   - implementar `compute_identity_signals(old_text, new_text, old_chapters, new_chapters)`,
   - implementar `classify_identity(signals, config)`.
3. Router/API:
   - añadir endpoint `POST /api/projects/{id}/document/replace`,
   - inyectar validación de identidad antes de persistir el nuevo archivo.
4. Pipeline:
   - actualizar `project.document_path`, `document_fingerprint`,
   - marcar necesidad de reanálisis.
5. UX:
   - acción de menú,
   - diálogo de confirmación simple para revisión permitida,
   - error bloqueante para manuscrito distinto.
6. Test:
   - unit signals,
   - integration endpoint,
   - e2e de flujo bloqueado/permitido.

## Sprint B: tareas concretas

1. Migraciones:
   - crear `entity_version_links`,
   - ampliar `version_metrics` con contadores de cambios de entidades.
2. Servicios:
   - implementar firma de continuidad de entidad,
   - implementar matching y clasificación de `rename/split/merge`.
3. Integración:
   - ejecutar continuidad al cerrar análisis,
   - persistir links entre versión N y N+1.
4. API/UI:
   - exponer lista resumida de renombres en endpoint de versiones,
   - renderizar en `VersionHistory` y comparativa.
5. Test:
   - dataset de continuidad,
   - pruebas de regresión de identidad.

## Sprint C: tareas concretas

1. Planner:
   - implementar `impact_planner.plan(diff, invalidations, entity_changes)`.
2. Orquestación:
   - reemplazar secuencia fija por ejecución guiada por plan.
3. Enrichment:
   - usar `input_hash` antes de `compute_fn`,
   - mantener `status=stale` en vez de borrado masivo.
4. Invalidación:
   - extender reglas por tipo de cambio,
   - invalidación por entidad y por capítulo.
5. Fallback:
   - reglas explícitas para promoción a `full run`.
6. Test:
   - equivalencia incremental vs full,
   - benchmark de rendimiento por escenario.

## Sprint D: tareas concretas

1. Métricas:
   - ampliar captura por versión y por fase.
2. API:
   - extender `/versions`, `/versions/trend`, comparativa por pares.
3. UI:
   - resumen de última versión,
   - vista detallada de evolución.
4. Observabilidad:
   - panel técnico de tiempos/hit-rate,
   - panel de identidad (clasificaciones y bloqueos).
5. Release:
   - feature flags,
   - rollout gradual y monitoreo.

## 11.8 Contratos API propuestos (detalle)

## `POST /api/projects/{id}/document/replace`

Request:

1. `multipart/form-data` con `file`.
2. Opcional:
   - `force_new_project` (bool),
   - `source` (`ui`, `cli`).

Response `200` (permitido):

1. `allowed: true`
2. `classification: same_exact | same_revision | uncertain`
3. `project_updated: true`
4. `analysis_required: true`

Response `409` (bloqueado):

1. `allowed: false`
2. `classification: different_document`
3. `error_code: DIFFERENT_MANUSCRIPT`
4. `message: "Este archivo parece un manuscrito distinto. Crea un proyecto nuevo."`
5. `cta: { action: "create_project_from_file" }`

## `GET /api/projects/{id}/versions`

Nuevos campos en cada versión:

1. `alerts_new_count`
2. `alerts_resolved_count`
3. `alerts_unchanged_count`
4. `entities_renamed_count`
5. `chapter_added_count`
6. `chapter_removed_count`
7. `run_mode`
8. `duration_total_sec`
9. `top_changes` (resumen corto para UI)

## `GET /api/projects/{id}/identity/last-check`

Uso:

1. Soporte interno y debugging.
2. No consumir en UX estándar.

Payload:

1. `classification`
2. `confidence`
3. `blocked`
4. `created_at`
5. `signals` (solo si usuario interno o modo debug habilitado)

## 11.9 Feature flags recomendadas

1. `NA_IDENTITY_V1_ENABLED`:
   - habilita clasificador textual-estructural.
2. `NA_IDENTITY_V2_NARRATIVE_ENABLED`:
   - habilita señales narrativas y renombres.
3. `NA_INCREMENTAL_PLANNER_ENABLED`:
   - habilita planner dependiente.
4. `NA_ENRICHMENT_INPUT_HASH_ENABLED`:
   - habilita skip pre-cómputo por input hash.
5. `NA_VERSION_INSIGHTS_UI_ENABLED`:
   - habilita nueva UX de evolución.

## 11.10 Política `uncertain` y medidas progresivas de licencia

Objetivo:

1. No bloquear revisiones legítimas por falsos positivos.
2. Detectar patrones repetidos de riesgo sin exponer criterios de detección.

Regla propuesta:

1. Cada evaluación `uncertain` genera un `risk_event`.
2. Se calcula `uncertain_count_rolling_30d` por licencia local.
3. Si `uncertain_count_rolling_30d > 3`:
   - marcar licencia local como `identity_review_required`,
   - endurecer política para próximos reemplazos (`uncertain` pasa a bloqueo local),
   - mostrar mensaje genérico: “No se puede reutilizar este proyecto con este archivo”.
4. Cuando exista backend/licensing cloud:
   - sincronizar eventos para revisión server-side.

Identificador temporal de licencia (sin servicio cloud):

1. Prioridad:
   - `license_id` (si existe en local),
   - fallback `hardware_fingerprint`,
   - fallback `installation_uuid`.

Persistencia propuesta:

1. Tabla `identity_risk_events`:
   - `id`, `license_subject`, `project_id`,
   - `classification`, `confidence`,
   - `action_taken` (`allow`, `block`, `escalate`),
   - `created_at`.
2. Tabla `identity_risk_state`:
   - `license_subject` PK,
   - `uncertain_count_rolling_30d`,
   - `review_required` (0/1),
   - `last_event_at`,
   - `updated_at`.

Nota de seguridad:

1. No exponer en UI:
   - contador,
   - umbrales,
   - señales concretas.
2. Exponer solo resultado final y CTA segura.

## 11.11 Checklist ejecutable por tickets (nivel implementación)

Esta sección está escrita para ejecución paso a paso por una IA de menor capacidad.

Regla operativa:

1. No mezclar tickets de sprints distintos en el mismo commit.
2. Validar cada ticket con pruebas mínimas antes de continuar.
3. Si falta un archivo esperado, ejecutar búsqueda guiada (`rg`) y adaptar ruta.

### Sprint A - Tickets

Ticket A-01: Migración base de identidad

1. Archivos:
   - `src/narrative_assistant/persistence/database.py`
2. Pasos:
   - subir `SCHEMA_VERSION` en +1,
   - añadir `CREATE TABLE IF NOT EXISTS manuscript_identity_checks (...)`,
   - añadir índices por `project_id`, `classification`, `created_at`,
   - añadir migraciones equivalentes en `table_migrations`.
3. Validación:
   - inicializar BD limpia y verificar que la tabla existe,
   - ejecutar tests de persistencia.

Ticket A-02: Estado de riesgo para `uncertain`

1. Archivos:
   - `src/narrative_assistant/persistence/database.py`
2. Pasos:
   - crear tablas:
     - `identity_risk_events`,
     - `identity_risk_state`,
   - añadir índices por `license_subject` y `created_at`.
3. Validación:
   - prueba SQL de inserción y consulta rolling 30 días.

Ticket A-03: Servicio de identidad v1

1. Archivos nuevos:
   - `src/narrative_assistant/analysis/manuscript_identity_service.py`
2. Funciones mínimas:
   - `compute_identity_signals(old_text, new_text, old_chapters, new_chapters) -> dict`,
   - `classify_identity(signals, cfg) -> IdentityResult`,
   - `record_identity_check(...)`,
   - `update_uncertain_risk_state(...)`.
3. Requisitos:
   - tipado estricto,
   - logs internos sin exponer pesos/umbrales.
4. Validación:
   - tests unitarios con casos:
     - exacto,
     - revisión leve,
     - documento claramente distinto,
     - borde uncertain.

Ticket A-04: Configuración y umbrales

1. Archivos:
   - `src/narrative_assistant/core/config.py`
2. Añadir en `PersistenceConfig`:
   - `identity_uncertain_limit_30d` (default `3`),
   - umbrales v1 de clasificación (texto/estructura).
3. Validación:
   - lectura desde env vars y defaults.

Ticket A-05: Endpoint de reemplazo

1. Archivos:
   - `api-server/routers/projects.py` o router dedicado de documentos.
2. Añadir endpoint:
   - `POST /api/projects/{project_id}/document/replace`.
3. Flujo:
   - parsear archivo nuevo,
   - obtener texto/capítulos actuales del proyecto,
   - ejecutar `manuscript_identity_service`,
   - si `different_document`: `409`,
   - si `uncertain` y `review_required`: `409`,
   - si permitido: reemplazar `document_path`/fingerprint y responder `200`.
4. Validación:
   - tests integration para cada clasificación.

Ticket A-06: UI mínima de reemplazo

1. Archivos (ubicar con `rg` si cambia la estructura):
   - menú de proyecto en `frontend/src/components/project/*`,
   - cliente API `frontend/src/services/*`.
2. Pasos:
   - añadir acción “Reemplazar manuscrito…”,
   - enviar archivo al endpoint,
   - manejar `409` con mensaje genérico + CTA nuevo proyecto.
3. Validación:
   - prueba manual UX.

Ticket A-07: Pruebas y CI Sprint A

1. Crear:
   - tests unit para servicio,
   - tests integration endpoint replace.
2. Ejecutar:
   - `ruff check src/ tests/ api-server/ --output-format=github`,
   - `mypy src/narrative_assistant/core src/narrative_assistant/persistence src/narrative_assistant/parsers src/narrative_assistant/alerts --ignore-missing-imports`,
   - pytest selectivo del nuevo módulo.

### Sprint B - Tickets

Ticket B-01: Migración continuidad de entidades

1. Archivos:
   - `src/narrative_assistant/persistence/database.py`
2. Añadir:
   - `entity_version_links`,
   - columnas extra en `version_metrics` para renombres y deltas.

Ticket B-02: Servicio de continuidad

1. Archivos nuevos:
   - `src/narrative_assistant/analysis/entity_continuity_service.py`
2. Funciones:
   - `build_entity_signature(...)`,
   - `match_entities_between_versions(...)`,
   - `classify_entity_change(...)`.

Ticket B-03: Integración al cierre de análisis

1. Archivos:
   - `api-server/routers/_enrichment_phases.py`,
   - `api-server/routers/analysis.py`,
   - `api-server/routers/_partial_analysis.py`.
2. Pasos:
   - ejecutar continuidad tras escribir métricas de versión,
   - persistir links y agregar contadores en versión.

Ticket B-04: API/UI de renombres

1. Archivos:
   - `api-server/routers/projects.py`,
   - `frontend/src/components/project/VersionHistory.vue`,
   - `frontend/src/components/project/VersionComparison.vue`,
   - tipos API/domain en `frontend/src/types/*`.
2. Pasos:
   - incluir `top_entity_renames` en respuesta,
   - renderizar en historial de versiones.

Ticket B-05: Dataset y validación

1. Crear fixture de casos reales/sintéticos en `tests/fixtures/*`.
2. Añadir métricas precision/recall por tipo de cambio.

### Sprint C - Tickets

Ticket C-01: Impact planner

1. Archivos nuevos:
   - `api-server/routers/_impact_planner.py`
2. Funciones:
   - `build_impact_graph()`,
   - `compute_impacted_nodes(diff, entity_changes, invalidations)`,
   - `build_phase_plan(...)`.

Ticket C-02: Orquestador guiado por plan

1. Archivos:
   - `api-server/routers/analysis.py`,
   - `api-server/routers/_partial_analysis.py`.
2. Pasos:
   - reemplazar flujo fijo por ejecución condicional según `phase_plan`,
   - conservar fallback a `full run`.

Ticket C-03: Enrichment con `input_hash`

1. Archivos:
   - `api-server/routers/_enrichment_phases.py`.
2. Pasos:
   - calcular `input_hash` antes de `compute_fn`,
   - si coincide con cache `completed`, skip pre-cómputo,
   - persistir `input_hash` + `output_hash`.

Ticket C-04: Evitar borrado masivo de enrichment cache

1. Archivos:
   - `api-server/routers/_analysis_phases.py`,
   - `api-server/routers/_invalidation.py`.
2. Pasos:
   - eliminar `DELETE enrichment_cache` del cleanup general,
   - usar `status='stale'` por impacto.

Ticket C-05: Benchmarks y equivalencia

1. Archivos:
   - `tests/performance/*`,
   - `tests/integration/*`.
2. Casos mínimos:
   - sin cambios,
   - cambios leves en todos los capítulos,
   - cambios focalizados,
   - cambios estructurales severos.

### Sprint D - Tickets

Ticket D-01: Version metrics extendidas

1. Archivos:
   - `src/narrative_assistant/persistence/database.py`,
   - `api-server/routers/_enrichment_phases.py`.
2. Pasos:
   - añadir columnas nuevas,
   - poblarlas en `write_version_metrics`.

Ticket D-02: Endpoints de evolución

1. Archivos:
   - `api-server/routers/projects.py`,
   - opcional nuevo router `api-server/routers/versioning.py`.
2. Pasos:
   - ampliar `/versions` y `/versions/trend`,
   - agregar endpoint de comparativa detallada entre dos versiones.

Ticket D-03: UI de insights

1. Archivos:
   - `frontend/src/components/project/VersionSparkline.vue`,
   - `frontend/src/components/project/VersionHistory.vue`,
   - `frontend/src/components/project/VersionComparison.vue`.
2. Pasos:
   - mostrar deltas de alertas/entidades/estructura,
   - mostrar modo de ejecución (`fast_path`/`incremental`/`full`).

Ticket D-04: Observabilidad operativa

1. Archivos:
   - módulo de logging/telemetría backend,
   - documentación operativa (`docs/`).
2. Pasos:
   - emitir métricas técnicas y de identidad,
   - documentar playbook de análisis de incidentes.

## 11.12 Runbook de implementación secuencial (paso a paso)

Fase 0: Preparación

1. Crear rama: `feature/identity-incremental-phase3`.
2. Verificar baseline:
   - `ruff`,
   - `mypy` (módulos críticos),
   - tests unitarios relevantes.

Fase 1: Sprint A completo

1. Implementar A-01 a A-07 en orden.
2. Abrir PR con etiqueta `identity-v1`.
3. Merge solo si:
   - endpoint replace operativo,
   - bloqueo `different_document` validado.

Fase 2: Sprint B completo

1. Implementar B-01 a B-05.
2. PR con etiqueta `entity-continuity`.
3. Merge solo si:
   - renombres detectados con precisión aceptable.

Fase 3: Sprint C completo

1. Implementar C-01 a C-05.
2. PR con etiqueta `incremental-planner`.
3. Merge solo si:
   - benchmark muestra mejora,
   - equivalencia incremental/full aprobada.

Fase 4: Sprint D completo

1. Implementar D-01 a D-04.
2. PR con etiqueta `version-insights`.
3. Activar flags progresivamente en entornos.

Checklist de cierre por sprint:

1. Documentación actualizada en `docs/`.
2. Changelog técnico.
3. Métricas post-release capturadas 7 días.

## 11.13 Algoritmos de referencia (pseudo-código implementable)

### A) Evaluación de identidad en reemplazo de manuscrito

```python
def replace_document(project_id: int, file: UploadFile) -> ApiResponse:
    project = project_repo.get(project_id)
    old_text, old_chapters = load_current_project_text(project_id)
    new_text, new_chapters = parse_uploaded_file(file)

    signals = compute_identity_signals(
        old_text=old_text,
        new_text=new_text,
        old_chapters=old_chapters,
        new_chapters=new_chapters,
    )
    result = classify_identity(signals, cfg)

    license_subject = resolve_license_subject()
    risk_state = update_uncertain_risk_state(
        license_subject=license_subject,
        classification=result.classification,
        confidence=result.confidence,
    )

    blocked = False
    if result.classification == "different_document":
        blocked = True
    elif result.classification == "uncertain" and risk_state.review_required:
        blocked = True

    record_identity_check(
        project_id=project_id,
        old_fingerprint=hash_text(old_text),
        new_fingerprint=hash_text(new_text),
        classification=result.classification,
        confidence=result.confidence,
        blocked=blocked,
        signals=signals,
        license_subject=license_subject,
    )

    if blocked:
        return conflict_409_new_project_cta()

    persist_replaced_file(project_id, file, new_text)
    return ok_allowed_response(result.classification)
```

### B) Política de riesgo `uncertain > 3` en rolling 30 días

```python
def update_uncertain_risk_state(license_subject: str, classification: str, confidence: float) -> RiskState:
    now = utcnow()
    action_taken = "allow"

    if classification == "uncertain":
        insert_identity_risk_event(
            license_subject=license_subject,
            classification=classification,
            confidence=confidence,
            action_taken="allow",
            created_at=now,
        )

    count_30d = query_scalar(
        """
        SELECT COUNT(*)
        FROM identity_risk_events
        WHERE license_subject = ?
          AND classification = 'uncertain'
          AND created_at >= datetime('now', '-30 days')
        """,
        (license_subject,),
    )

    review_required = count_30d > cfg.identity_uncertain_limit_30d  # default 3

    upsert_identity_risk_state(
        license_subject=license_subject,
        uncertain_count_rolling_30d=count_30d,
        review_required=review_required,
        last_event_at=now,
    )

    if review_required:
        action_taken = "escalate"

    return RiskState(
        license_subject=license_subject,
        uncertain_count_rolling_30d=count_30d,
        review_required=review_required,
        action_taken=action_taken,
    )
```

### C) Planner incremental con fallback seguro

```python
def build_plan(diff: DocumentDiff, entity_changes: EntityChanges, invalidations: InvalidationState) -> PhasePlan:
    impacted = set()
    if diff.has_text_changes:
        impacted.add("ner")
        impacted.add("grammar")
        impacted.add("prose")

    if entity_changes.has_ner_delta:
        impacted.update(["fusion", "attributes", "consistency", "relationships", "voice", "health"])

    if invalidations.has_global_stale:
        impacted.update(["relationships", "voice", "prose", "health"])

    impacted = close_over_dependencies(impacted)

    if is_high_risk(diff, entity_changes):
        return PhasePlan(mode="full", phases=ALL_PHASES)

    return PhasePlan(mode="incremental", phases=ordered(impacted))
```

## 11.14 SQL de referencia para migraciones nuevas

```sql
CREATE TABLE IF NOT EXISTS manuscript_identity_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    old_fingerprint TEXT NOT NULL,
    new_fingerprint TEXT NOT NULL,
    classification TEXT NOT NULL, -- same_exact/same_revision/different_document/uncertain
    confidence REAL NOT NULL DEFAULT 0.0,
    blocked INTEGER NOT NULL DEFAULT 0,
    signals_json TEXT NOT NULL DEFAULT '{}',
    license_subject TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_identity_checks_project ON manuscript_identity_checks(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_identity_checks_class ON manuscript_identity_checks(classification, created_at);
CREATE INDEX IF NOT EXISTS idx_identity_checks_license ON manuscript_identity_checks(license_subject, created_at);

CREATE TABLE IF NOT EXISTS identity_risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_subject TEXT NOT NULL,
    project_id INTEGER,
    classification TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    action_taken TEXT NOT NULL DEFAULT 'allow', -- allow/block/escalate
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_identity_risk_events_license ON identity_risk_events(license_subject, created_at);

CREATE TABLE IF NOT EXISTS identity_risk_state (
    license_subject TEXT PRIMARY KEY,
    uncertain_count_rolling_30d INTEGER NOT NULL DEFAULT 0,
    review_required INTEGER NOT NULL DEFAULT 0,
    last_event_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## 11.15 Plan de commits recomendado (ejecutable)

1. Commit `A-01 A-02`:
   - solo migraciones y esquema.
2. Commit `A-03 A-04`:
   - servicio identidad + config.
3. Commit `A-05`:
   - endpoint replace + tests integration.
4. Commit `A-06`:
   - UI replace + manejo de errores.
5. Commit `A-07`:
   - hardening de tests/CI.
6. Repetir el mismo patrón en B, C, D:
   - migraciones,
   - servicio,
   - integración backend,
   - UI,
   - tests.

## 12. Criterios de aceptación

1. Reemplazo de manuscrito distinto bloqueado localmente con mensaje claro.
2. Revisión del mismo manuscrito no bloqueada aunque cambien muchos capítulos “poco” en promedio.
3. Detección de renombres de personajes visible en resumen de versión (cuando confianza >= umbral).
4. Incremental mantiene resultados consistentes con full run en corpus de validación.
5. Reducción medible de tiempo medio de reanálisis.

## 13. Decisiones UX cerradas (de esta iteración)

1. Reemplazo en menú secundario de proyecto.
2. Para documento distinto: error y CTA a nuevo proyecto.
3. Sin modal diagnóstico detallado en caso bloqueado.
4. Información de mejoras por versión en resumen + historial.

## 14. Pendientes de decisión (producto/negocio)

1. Retención histórica (número de versiones/snapshots por proyecto).
2. Nivel de detalle visible para soporte interno vs usuario final.
3. Momento exacto para activar la política endurecida de `uncertain > 3` en producción (desde día 1 o rollout gradual).
