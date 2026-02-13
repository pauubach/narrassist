# Estado Actual del Proyecto

Fecha de verificación: 2026-02-13  
Fuente de verdad para plan: `docs/IMPROVEMENT_PLAN_EXECUTION_READY_2026-02-13.md`

## Resumen ejecutivo

El proyecto está en un estado funcional alto, con avances reales en S13 y S14.  
No obstante, hay desalineaciones entre implementación, pruebas y documentación que conviene cerrar antes de continuar con S15/S16.

## Estado verificado por sprint

| Sprint | Estado real | Evidencia |
|---|---|---|
| S13 (BK-27 + BK-25 MVP) | **Mayormente implementado** | `api-server/routers/alerts.py`, `src/narrative_assistant/alerts/repository.py`, `api-server/routers/collections.py`, `frontend/src/components/alerts/ChapterRangeSelector.vue`, `frontend/src/components/alerts/ComparisonBanner.vue` |
| S14 (Revision Intelligence) | **Implementado en gran parte** | `src/narrative_assistant/analysis/content_diff.py`, `src/narrative_assistant/analysis/comparison.py`, `src/narrative_assistant/persistence/snapshot.py`, `frontend/src/components/revision/RevisionDashboard.vue`, `frontend/src/views/RevisionView.vue` |
| S15 (Version tracking) | **No implementado** | Sin `version_metrics` en `src/` ni endpoints `/versions` |
| S16 (Monetización) | **No implementado** | Sin `/api/license/quota-status`, `purchase-pack`, `webhook`, `upgrade` |

## Hallazgos técnicos relevantes

1. El endpoint `comparison/summary` existe, pero usa claves incompatibles con `ComparisonReport.to_dict()`:
- Endpoint: `api-server/routers/collections.py`
- Report serializa en `alerts.new/resolved/unchanged` y `document_fingerprint_changed`: `src/narrative_assistant/analysis/comparison.py`
- Riesgo: el banner puede mostrar contadores incorrectos.

2. Hay migraciones etiquetadas como “v21” en código, pero `SCHEMA_VERSION` sigue en 20:
- `src/narrative_assistant/persistence/database.py:26`
- Riesgo: trazabilidad de migraciones confusa en entornos reales.

3. Las pruebas específicas S13/S14 existen y pasan, pero son más de existencia/lógica local que de contrato API extremo:
- Ejecutado: `pytest -q tests/unit/test_s13_chapter_filter_comparison.py tests/unit/test_s14_content_diff.py`
- Resultado: 49 passed.

## Estado de riesgo (hoy)

- Riesgo funcional: **medio** (por inconsistencia de serialización en `comparison/summary`).
- Riesgo de evolución: **medio-alto** (versionado de schema no disciplinado).
- Riesgo de documentación: **alto** (había duplicidad y enlaces rotos; limpieza aplicada en esta iteración).

## Próximos pasos recomendados

1. Corregir contrato de `comparison/summary` para leer `alerts.resolved/new/unchanged` y `document_fingerprint_changed`.
2. Definir y congelar estrategia explícita de versionado de schema (v21+).
3. Iniciar S15 solo después de cerrar 1 y 2.
4. Mantener S16 desacoplado en dos fases: UX local y billing backend público.

## Historial

El estado largo y legacy anterior se movió a:
- `docs/_archive/obsolete/PROJECT_STATUS_LEGACY_2026-02-13.md`
