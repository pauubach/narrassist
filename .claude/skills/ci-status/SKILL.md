---
name: ci-status
description: "Consulta el estado de CI/CD en GitHub para la rama actual o un PR concreto usando el MCP de GitHub. Invocar cuando el usuario diga 'cómo va CI', '¿están verdes los checks?', 'revisa el pipeline', '¿qué falló en CI?', 'status del PR #N'."
---

# /ci-status — Estado de CI/CD en GitHub

## Cuándo usar

- Antes de mergear o pushear para saber si CI ya está verde.
- Tras un push reciente, para confirmar que los workflows pasaron.
- Al investigar un fallo en CI: ver qué job falló exactamente.
- Para dar contexto de un PR antes de `/review-pr`.

## Argumentos

- (sin args) — rama actual
- `#N` o `--pr N` — PR concreto
- `--branch <name>` — rama específica
- `--watch` — mostrar estado final en lugar de snapshot (repoll hasta resolución)

## Flujo

### Paso 1 — Identificar scope

```bash
git rev-parse --abbrev-ref HEAD   # rama actual
git log --oneline -1              # último commit SHA
```

Si se pasa `#N`, usar el PR directamente. Si no, buscar el PR abierto de la rama:

```
mcp__github__list_pull_requests(state: "open", head: "<rama>")
```

### Paso 2 — Estado del PR (si existe)

```
mcp__github__get_pull_request_status(pullNumber: N)
```

Extraer:
- `state` (open/closed/merged)
- `mergeable`
- `checks` — lista de check runs con `conclusion` (success/failure/pending)

### Paso 3 — Checks de la rama (si no hay PR)

```
mcp__github__list_commits(sha: "<rama>", perPage: 1)
```

Obtener SHA del último commit → consultar check runs vía la API.

### Paso 4 — Formatear resultado

```
## CI Status — <rama> (<SHA corto>)

| Workflow | Job | Estado | Duración |
|----------|-----|--------|----------|
| ci.yml   | backend-tests | ✅ success | 2m 14s |
| ci.yml   | frontend-tests | ✅ success | 1m 38s |
| build-release.yml | build | ⏳ in_progress | — |

Veredicto: ⚠️ PENDIENTE — build-release en curso.
```

Iconos: ✅ success · ❌ failure · ⏳ pending · ⊘ skipped · 🔁 queued

### Paso 5 — Si hay fallos (❌)

Buscar el log del job fallido para extraer el error relevante:

```
mcp__github__get_pull_request_files(...)  # para identificar scope
```

Mostrar las últimas 20 líneas del log relevante y proponer si el fallo es arreglable localmente (`/check`, `/debug`).

## Output mínimo

Una tabla de checks + veredicto en una línea. No hacer resúmenes largos si todo está verde.
