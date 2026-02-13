# Estado Actual del Proyecto

Fecha de verificación: 2026-02-14
Fuente de verdad operativa: `docs/PLAN_ACTIVE.md`

## Resumen ejecutivo

El proyecto está en un estado funcional alto. Todos los sprints NLP (S0-S12), editorial (S13-S14),
version tracking (S15), y monetización UX (S16A) están completados. Quedan pendientes S16B (pagos
con Stripe, bloqueado por infraestructura externa) y las ideas aparcadas.

## Estado verificado por sprint

| Sprint | Estado real | Evidencia |
|---|---|---|
| S0-S12 (NLP + Licensing) | **Completado** | 1231+ tests pasando, tags v0.1.0-v0.9.4 |
| S13 (BK-27 + BK-25 MVP) | **Completado** | `api-server/routers/alerts.py`, `ChapterRangeSelector.vue`, `ComparisonBanner.vue` |
| S14 (Revision Intelligence) | **Completado** | `content_diff.py`, `comparison.py`, `snapshot.py`, `RevisionDashboard.vue`, `docx_revisions.py` |
| S15 (Version tracking) | **Completado** | `version_metrics` table (v24), `api-server/routers/versions.py`, `VersionHistory.vue`, sparkline trends |
| S16A (Monetización UX) | **Completado** | `QuotaWarningBanner.vue`, `TierComparisonDialog.vue`, `GET /api/license/quota-status`, 20 tests |
| S16B (Monetización pagos) | **No implementado** | Bloqueado: requiere backend público de billing + Stripe account |

## Hallazgos técnicos recientes

1. Schema en v24 con `project_detector_weights` (pesos adaptativos nivel 3) y `version_metrics`.
2. `is_founding_member` se lee de `license.extra_data["founding_member"]` y se devuelve en `/api/license/status`.
3. Quota warning banner aparece al 80/90/100% de uso, con días restantes del periodo.
4. Tier comparison muestra precios founder vs. estándar según `is_founding_member`.

## Estado de riesgo (hoy)

- Riesgo funcional: **bajo** (tests pasan, endpoints verificados).
- Riesgo de evolución: **bajo** (schema versionado en v24, migraciones disciplinadas).
- Riesgo de documentación: **bajo** (IMPROVEMENT_PLAN y PROJECT_STATUS sincronizados).

## Próximos pasos

1. **S16B**: Solo cuando haya backend público de billing (Cloud Functions o servidor dedicado) + cuenta Stripe.
2. **Ideas aparcadas**: Landing web, colaboración online (BK-26), EPUB/XLSX export — tras feedback de clientes reales.
3. **Release**: El producto está listo para v1.0 desde perspectiva funcional desktop-only.

## Historial

El estado largo y legacy anterior se movió a:
- `docs/_archive/obsolete/PROJECT_STATUS_LEGACY_2026-02-13.md`

El plan transicional usado para esta limpieza se archivó en:
- `docs/_archive/planning/IMPROVEMENT_PLAN_EXECUTION_READY_2026-02-13.md`
