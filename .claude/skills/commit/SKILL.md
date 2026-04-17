---
name: commit
description: "Preparar y ejecutar un commit local con cobertura de tests revisada, lint + tests verdes y mensaje de una sola línea. Invocar cuando el usuario diga 'commitea', 'haz el commit', 'súbelo a git' (local), 'guarda los cambios', 'crea el commit'. NUNCA commitear sin confirmación explícita del usuario. Ejemplos: 'commitea el refactor del parser', 'haz commit de los tests nuevos con mensaje feat: X', 'guarda todo lo de hoy'."
---

# /commit — Preparar y ejecutar commit

## Regla inviolable

**NUNCA** ejecutar `git commit` sin confirmación explícita del usuario en este turno. Mostrar diff + mensaje propuesto → esperar "sí" / "OK" / "procede" → entonces commitear.

## Flujo

### 1. Snapshot del estado

```bash
git status --short
git diff --cached --stat
git diff --stat
git log --oneline -5
```

### 2. Revisión de cobertura de tests (MANDATORY)

Para cada archivo modificado bajo `src/narrative_assistant/**` o `api-server/**`:
- ¿Existe test correspondiente en `tests/`?
- ¿El cambio introduce nueva lógica/rama no cubierta?
- Si falta cobertura → **PARAR** y sugerir `/test <archivo>` antes de continuar. No commitear sin tests cuando corresponde.

Para cambios en `frontend/src/**`:
- ¿Existe `*.test.ts` / `*.spec.ts` correspondiente?
- Aplicar el mismo criterio.

### 3. Lint + tests

Ejecutar `/check` (ver `.claude/skills/check/SKILL.md`). Si algo falla → parar, corregir, reintentar.

### 4. Staging

Si hay archivos sin stagear relevantes para el commit → proponer `git add <archivo>` explícito por archivo. **Nunca** `git add -A` ni `git add .` — puede incluir archivos sensibles (.env, screenshots, caches).

Excluir siempre de staging (a menos que el usuario lo pida):
- Screenshots sueltos en raíz (`*.png` en root).
- Archivos en `~/.narrative_assistant/`, caches, `.venv/`.

### 5. Mensaje de commit

- **Una sola línea**. Sin cuerpo extendido salvo que el usuario lo pida.
- **Sin** `Co-Authored-By`, sin referencias a Claude, sin emojis salvo petición.
- Prefijos convencionales según `git log` reciente: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Foco en el **por qué**, no el qué.

Ejemplo:
```
fix: preserve alert position when resolving via focus mode
```

### 6. Presentar al usuario

```
Archivos a commitear:
  M src/narrative_assistant/.../foo.py
  A tests/.../test_foo.py

Mensaje propuesto:
  feat: <mensaje>

¿Procedo con el commit?
```

### 7. Ejecutar (solo tras OK)

```bash
git add <archivos-explicitos>
git commit -m "<mensaje>"
git status  # verificar éxito
```

### 8. Si el pre-commit hook falla

**Nunca** usar `--no-verify` salvo que la auto-memoria del usuario lo mande explícitamente para hardware modesto (ver memoria: "git commits: Use --no-verify"). En este proyecto la auto-memoria lo permite — confirmar con el usuario antes de usarlo de todas formas.

**Nunca** `git commit --amend` tras un fallo de hook — el commit no ocurrió, `--amend` modificaría el commit anterior. Arreglar, re-stagear, crear commit **nuevo**.
