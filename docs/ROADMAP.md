# Roadmap Operativo

Fecha: 2026-02-13  
Basado en: `docs/IMPROVEMENT_PLAN_EXECUTION_READY_2026-02-13.md`

## Prioridad actual

1. **Cerrar deuda S13/S14 ya implementada**
- Corregir `comparison/summary` para contrato real de `ComparisonReport`.
- Consolidar tests de contrato API (no solo existencia de endpoints).
- Documentar correctamente qué parte de S14 está en producción y qué parte es parcial.

2. **Ordenar migraciones antes de S15**
- Formalizar numeración y changelog de schema.
- Evitar mezclar “migraciones por columnas” con “versionado de release” sin control.

3. **S15 (Version tracking)**
- Solo arrancar tras cerrar 1 y 2.
- Entregables: `version_metrics`, endpoints `/versions`, `/versions/trend`, UI sparkline/historial.

4. **S16 (Monetización) en dos bloques**
- S16A: UX de cuotas y upgrade en cliente.
- S16B: pagos (Stripe/webhook) únicamente con backend público de billing.

## Estado por bloque

| Bloque | Estado |
|---|---|
| S13 | Implementado con ajustes pendientes |
| S14 | Implementado en gran parte, requiere cierre de contrato/calidad |
| S15 | Pendiente |
| S16A | Pendiente |
| S16B | Pendiente (dependiente de infraestructura externa) |

## Criterios de entrada a cada sprint

- API contract tests en verde.
- Lint y test suite relevantes en verde.
- Cambios de schema con versionado explícito y reversible.
- Actualización documental mínima: `PROJECT_STATUS.md`, `README.md`, `CHANGELOG.md`.

## Historial

La versión larga/legacy del roadmap se movió a:
- `docs/_archive/obsolete/ROADMAP_LEGACY_2026-02-13.md`
