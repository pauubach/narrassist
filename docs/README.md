# Narrative Assistant - Documentación

Ultima actualizacion: 2026-02-13 | Version: 0.9.4

## Documentos canónicos (mantener actualizados)

| Documento | Uso |
|---|---|
| `PLAN_ACTIVE.md` | Sprints activos, backlog vivo, ideas y criterios operativos |
| `PROJECT_STATUS.md` | Estado real verificado de implementación |
| `ROADMAP.md` | Prioridades operativas próximas |
| `IMPROVEMENT_PLAN.md` | Historial completo de planificación y contexto |
| `CHANGELOG.md` | Historial de cambios por versión |
| `AUDIT_INDEX.md` | Índice de auditorías activas y archivadas |

## Para arrancar rápido

1. `00-overview/goals-and-scope.md`
2. `02-architecture/database-schema.md`
3. `PLAN_ACTIVE.md`
4. `PROJECT_STATUS.md`
5. `ROADMAP.md`

## Estructura recomendada de uso

- `00-overview/`, `01-theory/`, `02-architecture/`, `04-references/`: base conceptual y técnica.
- `api-reference/`: contratos y referencia de API.
- `research/`, `ux/`, `testing/`: soporte y estudios especializados.
- `_archive/`: histórico, no canónico para decisiones actuales.

## Política de mantenimiento documental

- Todo documento operativo nuevo debe estar enlazado desde este `README.md`.
- Si un documento queda obsoleto, se mueve a `docs/_archive/obsolete/`.
- Evitar duplicar “estado actual” en varios `.md`: usar `PROJECT_STATUS.md` como fuente única.
- Evitar duplicar “siguiente trabajo” en varios `.md`: usar `ROADMAP.md` como fuente única.

## Cambios de curación aplicados

- `PROJECT_STATUS.md` legacy movido a `docs/_archive/obsolete/PROJECT_STATUS_LEGACY_2026-02-13.md`.
- `ROADMAP.md` legacy movido a `docs/_archive/obsolete/ROADMAP_LEGACY_2026-02-13.md`.
- Auditorías cerradas movidas a `docs/_archive/audits/`.
- Plan transicional movido a `docs/_archive/planning/IMPROVEMENT_PLAN_EXECUTION_READY_2026-02-13.md`.
