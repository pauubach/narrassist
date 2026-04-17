---
name: ship
description: "Pre-push completo + push + crear PR a master en un solo flujo. Invocar cuando el usuario diga 'haz ship', 'sube y abre PR', 'crea el PR', 'publícalo', 'manda esto a GitHub', 'abre un PR con lo de hoy'. Requiere confirmación explícita en cada paso destructivo. Ejemplos: 'ship el feature de exportación EPUB', 'crea PR con todos los commits de esta semana', 'sube y abre PR a master'."
---

# /ship — Pre-push + push + PR

## Flujo

### Paso 1 — Pre-push

Ejecutar `/pre-push` completo (ver `.claude/skills/pre-push/SKILL.md`). Si el veredicto es ❌ → parar. Si es ⚠️ → preguntar al usuario si procede con reservas.

### Paso 2 — Verificar rama

```bash
git rev-parse --abbrev-ref HEAD
```

- Si estamos en `master` → **parar**. El PR desde `master` hacia `master` no tiene sentido. Pedir al usuario que cree una feature branch primero.
- Si la rama tiene upstream tracking → `git push`.
- Si no → `git push -u origin <rama>`.

### Paso 3 — Push (con confirmación)

```
Voy a ejecutar: git push -u origin <rama>
Esto hará visible los N commits en el remoto.
¿Procedo?
```

Esperar OK → ejecutar.

### Paso 4 — Construir descripción del PR

Analizar **todos** los commits del PR (no solo el último):

```bash
git log --oneline master..HEAD
git diff master..HEAD --stat
```

Construir:
- **Título**: < 70 chars, resumen accionable, prefijo convencional (`feat:` / `fix:` / etc.).
- **Body**:
  - `## Summary` — 1-3 bullets con el "qué" y el "por qué".
  - `## Test plan` — checklist markdown con pasos para validar la feature.
  - **No** añadir "🤖 Generated with Claude Code" ni co-authorship.

### Paso 5 — Crear PR (con confirmación)

```
Título propuesto: <título>

Body:
<body>

Base: master
Head: <rama>

¿Procedo con: gh pr create --base master?
```

Esperar OK → ejecutar:

```bash
gh pr create --base master --title "<título>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

### Paso 6 — Devolver URL del PR

Al terminar, mostrar la URL para que el usuario pueda abrirla.

## Reglas

- PRs SIEMPRE hacia `master` (trunk-based, no hay `develop`).
- **Nunca** `git push --force` a una rama compartida sin instrucción explícita. Si se necesita reescritura de historia, usar `--force-with-lease` y confirmar.
- Si el usuario pide `hotfix`: mismo flujo, con prefijo `fix:` en el título y etiqueta de urgencia en el body.
