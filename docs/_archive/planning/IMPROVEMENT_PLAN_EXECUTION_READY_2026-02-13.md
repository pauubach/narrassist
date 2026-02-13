# Plan de Mejora (Execution-Ready)

Fecha: 2026-02-13
Base: `docs/IMPROVEMENT_PLAN.md` + contraste con código actual

## 1) Objetivo

Convertir el plan actual en una versión **ejecutable** (sin ambigüedades), manteniendo el foco en S13-S16 pero corrigiendo incoherencias de roadmap, contratos API/datos y migraciones.

## 2) Evidencia técnica verificada (estado real del código)

- Schema actual en código: `SCHEMA_VERSION = 20` en `src/narrative_assistant/persistence/database.py:26`.
- Índice existente: `idx_alerts_chapter ON alerts(chapter)` en `src/narrative_assistant/persistence/database.py:265`.
- Endpoint de comparación actual: `GET /projects/{project_id}/comparison` en `api-server/routers/collections.py:63` (no existe `comparison/summary`).
- Alertas API actuales: `list_alerts()` expone `status`, `current_chapter`, `severity`, `focus` en `api-server/routers/alerts.py:60`.
- Priorización actual de alertas por capítulo: `get_by_project_prioritized()` en `src/narrative_assistant/alerts/repository.py:165`.
- El modelo `Alert` tiene `chapter` y `extra_data`, pero no `related_chapter`:
  - `src/narrative_assistant/alerts/models.py:86`
  - `src/narrative_assistant/alerts/models.py:107`
- Snapshot pre-reanálisis sí existe y se limpia por retención:
  - `create_snapshot()` en `src/narrative_assistant/persistence/snapshot.py:74`
  - `cleanup_old_snapshots()` en `src/narrative_assistant/persistence/snapshot.py:270`
  - uso en pipeline: `api-server/routers/_analysis_phases.py:363`
- Licensing actual: existen `status/usage/check-feature`, no endpoints de compra/webhook:
  - `api-server/routers/license.py:22`
  - `api-server/routers/license.py:257`
  - `api-server/routers/license.py:343`

## 3) Incoherencias del plan actual (y por qué son críticas)

1. Doble bloque de “SIGUIENTE”:
- `docs/IMPROVEMENT_PLAN.md:1890` (S9-S12) y `docs/IMPROVEMENT_PLAN.md:1902` (S13-S16).
- Problema: rompe priorización operativa y secuencia de ejecución.

2. Estimaciones “restantes” incluyen trabajo ya marcado como completado:
- SP-1 aún figura en restantes (`docs/IMPROVEMENT_PLAN.md:2124`) pero estado dice SP-1..3 completados (`docs/IMPROVEMENT_PLAN.md:2168`).
- S11-S12 también figuran como restantes (`docs/IMPROVEMENT_PLAN.md:2133`, `docs/IMPROVEMENT_PLAN.md:2134`) aunque el estado global los marca completos (`docs/IMPROVEMENT_PLAN.md:2168`).
- Problema: planificación y reporting de avance no confiables.

3. Colisión de versionado de schema:
- Ya hay referencias previas a v21/v22 (`docs/IMPROVEMENT_PLAN.md:1312`, `docs/IMPROVEMENT_PLAN.md:1353`).
- Se vuelve a proponer v21/v22 para nuevas tablas/campos (`docs/IMPROVEMENT_PLAN.md:1980`, `docs/IMPROVEMENT_PLAN.md:2017`).
- Problema: riesgo alto de migraciones incoherentes entre entornos.

4. Supuesto de datos no existente (`related_chapter`):
- Plan lo usa en S13 (`docs/IMPROVEMENT_PLAN.md:1935`), pero no existe en modelo persistido.
- Problema: la query propuesta no puede implementarse tal cual.

5. Índice propuesto como “nuevo” ya existe:
- Plan propone `idx_alerts_chapter` (`docs/IMPROVEMENT_PLAN.md:1936`), pero ya está en schema (`src/narrative_assistant/persistence/database.py:265`).
- Problema: trabajo duplicado, falsa sensación de optimización.

6. Monetización local-first subestimada:
- Plan asume Stripe checkout + webhook directo (`docs/IMPROVEMENT_PLAN.md:2053`).
- Problema: webhooks no deben depender de app desktop local; requieren backend público fiable.

## 4) Plan corregido (secuencia ejecutable)

## 4.1 Roadmap único activo

- **Activo ahora**: S13
- **Secuencia oficial**: S13 -> S14 -> S15
- **S16**: condicionado a backend de billing público (no bloquear core editorial)

Por qué:
- El mayor ROI inmediato es editorial (filtrado + comparación tras reanálisis).
- Monetización sin backend robusto introduce deuda operativa y riesgo de soporte.

## 4.2 Versionado de schema corregido

Nuevo convenio:
- v21: campos de linking en `alerts` para comparación avanzada.
- v22: `snapshot_chapters` (texto por snapshot para diff).
- v23: `version_metrics`.
- v24: `page_packs` y soporte monetización (solo con backend de billing listo).

Por qué:
- Evita colisiones con numeración ya usada documentalmente.
- Permite auditoría y rollback por bloques funcionales.

## 4.3 S13 (1-2 días) - Editorial workflow

Scope cerrado:
1. Filtro por rango de capítulos en alertas (API + repo + UI).
2. Summary de comparación post-reanálisis (backend + banner UI).

Ajustes de diseño:
- Para “cross-chapter”, usar `extra_data.related_chapters: list[int]` en vez de `related_chapter` directo.
- No recrear `idx_alerts_chapter`; añadir índice compuesto solo si profiling lo justifica:
  - candidato: `(project_id, chapter, status)`.

Por qué:
- `extra_data` ya existe y evita migración inmediata de bajo valor.
- El índice actual cubre parte del caso; el compuesto solo aporta si la query real lo necesita.

Definition of Done S13:
- API acepta `chapter_min` y `chapter_max`.
- UI filtra y persiste rango por proyecto.
- Endpoint `comparison/summary` operativo.
- Tests unitarios e integración de los nuevos contratos.

## 4.4 S14 (5-7 días) - Revision Intelligence full

Scope cerrado:
1. Diff de contenido por capítulo.
2. Linking de alertas antes/después.
3. Dashboard de revisión.

Guardas de rendimiento/memoria:
- `snapshot_chapters` con retención existente (10 snapshots).
- Guardar `content_hash` siempre y `content_text` comprimido.
- Límite configurable por capítulo para evitar crecimiento explosivo.

Por qué:
- Sin texto previo no hay diff útil para explicación editorial.
- Compresión + retención mitigan crecimiento de BD y degradación.

Definition of Done S14:
- `resolution_reason` y `match_confidence` expuestos en API.
- Dashboard muestra nuevas/resueltas/sin cambio con trazabilidad.
- Pruebas de edge cases: capítulo añadido, eliminado, reordenado, cambio masivo.

## 4.5 S15 (4-5 días) - Version tracking

Scope cerrado:
1. Persistir `version_metrics` por corrida completada.
2. Endpoints `versions` y `versions/trend`.
3. Sparkline + historial en frontend.

Por qué:
- Ya existe infraestructura de snapshot y enrichment; falta materializar métricas agregadas.
- El valor para coordinación editorial es alto y el riesgo técnico es bajo-medio.

Definition of Done S15:
- Una corrida completada genera registro de versión.
- Tendencia disponible y usable en UI.
- Tests de migración + API + render.

## 4.6 S16 (6-8 días, condicionado) - Monetización

Partición obligatoria:
- S16A (desktop, sin pagos): warnings de cuota + UX de upgrade.
- S16B (pagos): Stripe/webhooks solo a través de backend público de billing.

Por qué:
- En desktop local no se debe confiar en callbacks/webhooks ni validación en cliente.
- Separar UX de pagos permite avanzar sin comprometer seguridad/operación.

Definition of Done S16:
- S16A puede salir solo.
- S16B requiere backend público, verificación de firma, idempotencia y reconciliación.

## 5) Matriz de decisiones (cambio + por qué + riesgo mitigado)

| Cambio | Por qué | Riesgo mitigado |
|---|---|---|
| Un solo bloque “siguiente” (S13 activo) | Evitar prioridades contradictorias | Bloqueos de planificación |
| Limpiar estimaciones restantes (quitar SP-1..3 y S11-S12) | Coherencia de reporting y capacidad | Forecast irreal |
| Renumerar migraciones a v21-v24 | El código base está en v20 y hay referencias v21/v22 previas | Migraciones conflictivas |
| `related_chapter` via `extra_data.related_chapters` en S13 | Existe hoy sin migración adicional | Rotura de contrato de datos |
| Índices por profiling, no por intuición | Ya existe `idx_alerts_chapter` | Optimización falsa |
| `snapshot_chapters` comprimido + retención + límites | Necesario para diff explicable sin inflar BD | OOM/crecimiento de DB |
| S16 dividido en A/B | Desktop local-first no soporta bien webhooks directos | Fraude/errores de cobro/soporte |

## 6) Criterios no funcionales obligatorios por sprint

- Latencia API nueva p95 < 300 ms en proyecto mediano.
- No aumentar RAM pico de análisis > 15% respecto baseline.
- Crecimiento de DB por snapshot bajo límite definido (con compresión + retención).
- Tests y lint en verde antes de cerrar sprint.

Por qué:
- El roadmap es editorial, pero el producto es desktop y sensible a rendimiento.
- Sin estos gates, se puede “cumplir funcionalmente” degradando la experiencia.

## 7) Checklist inmediato (orden recomendado)

1. Corregir en `docs/IMPROVEMENT_PLAN.md` las secciones de “SIGUIENTE” y “estimaciones restantes”.
2. Congelar convenio de migraciones v21-v24.
3. Ejecutar S13 completo con tests (API + repo + frontend + summary endpoint).
4. Medir impacto real de índices antes de crear nuevos compuestos.
5. Diseñar S14 con políticas explícitas de retención/compresión de snapshot.
6. Tratar S16 como dos entregables (A sin pagos, B con backend billing).

## 8) Veredicto

La actualización va en buena dirección estratégica (más valor editorial y monetización real), pero para ser ejecutable sin sobresaltos requiere:
- alineación con el estado real del código,
- versionado de schema disciplinado,
- contratos de datos explícitos,
- y separación de monetización UX vs infraestructura de pagos.

Sin esos ajustes, el principal riesgo no es “que falle una feature”, sino **degradar confiabilidad operativa** y acumular deuda de migraciones/API.
