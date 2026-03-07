# Narrative Assistant - Documentación

Ultima actualizacion: 2026-03-07 | Version: 0.11.12

## Documentos canónicos (mantener actualizados)

| Documento | Uso |
|---|---|
| `PLAN_ACTIVE.md` | Sprints activos, backlog vivo, ideas y criterios operativos |
| `PROJECT_STATUS.md` | Estado real verificado de implementación |
| `ROADMAP.md` | Prioridades operativas próximas |
| `IMPROVEMENT_PLAN.md` | Historial completo de planificación y contexto |
| `CHANGELOG.md` | Historial de cambios por versión |
| `AUDIT_INDEX.md` | Índice de auditorías activas y archivadas |
| `COREFERENCE_RESOLUTION.md` | Sistema de correferencias multi-método |
| `LICENSING_PRODUCTION_PLAN.md` | Plan de monetización y licencias |
| `BUILD_AND_DEPLOY.md` | Construcción de instaladores |
| `PYTHON_EMBED.md` | Estrategia de empaquetado multi-plataforma |

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
- `audits/`: auditorías activas e históricas mantenidas en el árbol principal.

## Política de mantenimiento documental

- Todo documento operativo nuevo debe estar enlazado desde este `README.md`.
- No referenciar rutas `docs/_archive/...` mientras ese directorio no exista en el repositorio.
- Evitar duplicar “estado actual” en varios `.md`: usar `PROJECT_STATUS.md` como fuente única.
- Evitar duplicar “siguiente trabajo” en varios `.md`: usar `ROADMAP.md` como fuente única.

## Cambios de curación aplicados

- Las referencias previas a `docs/_archive/...` ya no son válidas en el árbol actual.
- Para auditorías activas e históricas usar `docs/audits/`.
- Para contexto de planificación acumulado usar `docs/IMPROVEMENT_PLAN.md`.
