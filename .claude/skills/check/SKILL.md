---
name: check
description: "Validación rápida mientras se trabaja: lint + types + tests afectados, en ambos stacks (Python backend y Vue/TS frontend). Invocar cuando el usuario diga 'chequea', 'pasa lint/tests', '¿está verde?', 'run checks', 'verifica antes de commitear', '¿pasa ruff?', '¿vitest verde?' o antes de /commit. Ejemplos: 'chequea el parser nuevo', '¿están verdes los tests del frontend?', 'run checks en ambos stacks antes de commitear'."
---

# /check — Validación rápida

## Cuándo se invoca

- "chequea esto" / "¿pasa lint?" / "¿tests verdes?" / "run checks"
- Automáticamente como primer paso de `/commit` y `/pre-push`

## Flujo

### 1. Detectar scope del cambio

```bash
git diff --name-only HEAD
git diff --cached --name-only
```

Clasificar archivos:
- `src/**/*.py`, `api-server/**/*.py`, `tests/**/*.py` → backend
- `frontend/src/**/*.{vue,ts}` → frontend
- Ambos → ejecutar ambas suites

### 2. Backend (si hay cambios Python)

Ejecutar en orden, **parar en el primer fallo**:

```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/ruff check src/ tests/ api-server/
cd /Users/PABLO/repos/narrassist && .venv/bin/mypy src/
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest -x
```

- `pytest -x` por defecto excluye el marcador `heavy` (ver `pytest.ini`).
- Para tests completos (raro, bajo demanda): `.venv/bin/pytest -m ""`.

### 3. Frontend (si hay cambios Vue/TS)

```bash
cd /Users/PABLO/repos/narrassist/frontend && npx eslint .
cd /Users/PABLO/repos/narrassist/frontend && npx vue-tsc --noEmit
cd /Users/PABLO/repos/narrassist/frontend && npx vitest run
```

### 4. Output

Tabla:

| Check | Resultado |
|---|---|
| ruff (backend) | ✅ / ❌ |
| mypy (backend) | ✅ / ❌ |
| pytest (backend) | ✅ / ❌ |
| eslint (frontend) | ✅ / ❌ |
| vue-tsc (frontend) | ✅ / ❌ |
| vitest (frontend) | ✅ / ❌ |

### 5. Próximos pasos

- Todo verde → sugerir `/commit`.
- Falla tests → mostrar los 2-3 fallos más relevantes (no log completo) + hipótesis.
- Falla lint/types → mostrar los errores + sugerir fix inline.
- Faltan tests para el cambio → sugerir `/test <archivo>` antes de `/commit`.

## Reglas

- **NO** usar `# type: ignore`, `# noqa`, `eslint-disable`, `@ts-ignore` para silenciar errores — arreglar el problema.
- **NO** ejecutar `pytest tests/` sin `-m` o `-x` (segfault por RAM en hardware modesto, ver auto-memoria).
- Si el test de Ollama requiere `start_server` → avisar que ese test está marcado `@heavy` y lo saltamos.
