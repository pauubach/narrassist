# Plan Activo (Sprints + Backlog + Ideas)

Ultima actualizacion: 2026-02-13

## Objetivo de este documento

Mantener en un solo lugar lo que necesitas tener a mano:
- sprints activos y siguientes,
- cosas a tener en cuenta,
- backlog vivo,
- ideas futuras.

Todo lo cerrado/historico se mueve a `docs/_archive/`.

## Estado rapido

- S13: cerrado (filtrado por capitulos + comparison summary MVP).
- S14: cerrado en gran parte (Revision Intelligence y track changes).
- S15: en curso (version tracking).
- S16A: pendiente (UX de cuota y tiers, sin pagos).
- S16B: pendiente y condicionado (pagos con backend publico de billing).

## Sprints operativos

## S15 - Version Tracking (actual)

Objetivo:
- Persistir metricas por version de analisis.
- Exponer tendencias por API.
- Mostrar historial y sparkline en frontend.

Entregables minimos:
- Tabla `version_metrics`.
- Endpoints `GET /projects/{id}/versions` y `GET /projects/{id}/versions/trend`.
- Componentes UI de historial/comparacion.
- Tests unitarios e integracion del flujo.

## S16A - Monetizacion UX (sin pagos)

Objetivo:
- Alertas de cuota (80/90/100%).
- Comparativa de tiers.

Entregables minimos:
- Banner de cuota persistente.
- Logica en store de licencia.
- Endpoint de estado de cuota.

## S16B - Monetizacion pagos (condicionado)

Condicion de entrada:
- Backend publico de billing listo (webhooks, firma, idempotencia, reconciliacion).

Objetivo:
- Activar compra de packs y upgrades de forma segura.

## Cosas a tener en cuenta (obligatorio)

1. Contrato API de comparacion:
- `comparison/summary` debe alinearse con las claves reales de `ComparisonReport`.

2. Migraciones y versionado:
- Evitar mezclar cambios de columnas con numeracion ambigua.
- Definir secuencia de migraciones y mantenerla estable.

3. Rendimiento/memoria:
- Controlar crecimiento de snapshots (retencion, tamaño de textos, consultas).
- Medir latencia de endpoints nuevos con datos reales.

4. Temporal complejo:
- Mantener consistencia para viajes temporales, instancias temporales y casos extremos.
- Referencias vivas:
  - `docs/TEMPORAL_INSTANCE_SEMANTIC_LIMITS.md`
  - `docs/TIMELINE_EXTREME_CASES_2026-02-13.md`

5. Multi-plataforma:
- Todo flujo nuevo debe validarse en Windows y macOS.

## Backlog vivo (corto plazo)

- Cerrar desajustes de contrato S13/S14.
- Completar cobertura de tests de contrato API (no solo tests de existencia).
- Cerrar S15 end-to-end (backend + frontend + tests).
- Ejecutar S16A.
- Preparar prerequisitos de infraestructura para S16B.
- Hardening tecnico de auditoria (serie F): F-004, F-005, F-007, F-008, F-009, F-010, F-011, F-013, F-015, F-016, F-019, F-020, F-022.

## Cobertura de auditorias archivadas (trazabilidad)

Regla operativa:
- Ningun hallazgo archivado queda huerfano: cada ID esta en `DONE`, `BACKLOG` o `SCOPE_DECISION`.

Serie BK (producto/roadmap):
- BK-01..BK-24: completados historicamente (detalle en `docs/IMPROVEMENT_PLAN.md`).
- BK-25: completado (S13 + S14).
- BK-26: backlog medio/largo plazo (colaboracion online).
- BK-27: completado (S13).
- BK-28: Sprint S15 (estado actual en ejecucion).
- BK-29: Sprint S16A/S16B (pendiente/condicionado).

Serie F (auditoria tecnica 2026-02):
- `DONE`: F-001, F-002, F-003, F-006, F-012, F-018.
- `BACKLOG`: F-004, F-005, F-007, F-008, F-009, F-010, F-011, F-013, F-015, F-016, F-019, F-020, F-022.
- `SCOPE_DECISION`: F-014, F-017, F-021.
- Fuente de estado: `docs/_archive/audits/AUDIT_RESPONSE_INDEX_2026-02-12.md`.
- Si cambia el alcance (release comercial, requisitos tribunal/cliente), mover `SCOPE_DECISION` a backlog activo.

## Ideas futuras (medio/largo plazo)

- Colaboracion online (BK-26).
- Exportaciones avanzadas (EPUB/XLSX) segun demanda real.
- Mejoras de benchmark y calibracion narrativa.
- Integraciones externas (cuando aporten ROI real).

## Documentacion historica (archivada)

Auditorias y consolidaciones cerradas:
- `docs/_archive/audits/EXPERT_PANEL_2026-02-13.md`
- `docs/_archive/audits/MEDIATION_CONSOLIDATED_2026-02-13.md`
- `docs/_archive/audits/ARCHITECTURE_AUDIT_2026-02.md`
- `docs/_archive/audits/ENTITY_TIMELINE_ATTRIBUTES_AUDIT_2026-02-13.md`

Plan transicional archivado:
- `docs/_archive/planning/IMPROVEMENT_PLAN_EXECUTION_READY_2026-02-13.md`

Contexto completo historico:
- `docs/IMPROVEMENT_PLAN.md`
