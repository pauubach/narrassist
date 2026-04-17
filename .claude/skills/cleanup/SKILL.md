---
name: cleanup
description: "Detectar y eliminar código muerto: exports sin consumidores, imports no usados, archivos huérfanos, dependencias no referenciadas, tests obsoletos. Invocar cuando el usuario diga 'hay código muerto', 'limpia los unused', 'cleanup', 'qué sobra aquí', 'hay archivos que ya no se usan', 'limpia el repo antes de la release'. Ejemplos: 'limpia imports no usados en el módulo NLP', 'encuentra archivos huérfanos en frontend/src', 'qué tests están obsoletos después del refactor'."
---

# /cleanup — Eliminar código muerto

## Regla inviolable

**Checkpoint git ANTES de borrar nada.** Si hay cambios sin commitear:

```bash
git status --short
git add -A && git commit -m "checkpoint: pre-cleanup"
```

Si el usuario prefiere no crear el checkpoint → pedirle stash o abortar. **Nunca** borrar sobre cambios no commiteados.

## Flujo

### 1. Scan (subagente Explore, haiku para pattern matching)

```
subagent_type: "Explore"
model: "haiku"
thoroughness: "medium"
prompt: "Escanear el proyecto narrassist buscando código muerto.

Buscar:
1. Exports Python sin importadores (grep 'from <módulo> import <nombre>' por todo el repo).
2. Exports TS/Vue sin importadores (grep 'import ... <nombre>').
3. Archivos .py/.vue/.ts nunca importados desde ningún otro archivo ni desde tests.
4. Imports de librerías en requirements/package.json que nadie usa en el código.
5. Funciones/métodos privados (_foo) nunca llamados dentro de su módulo.
6. Tests @xfail o @skip sin comentario de justificación.
7. Archivos en raíz que parecen basura (screenshots sueltos, *.log, *.tmp).

Output: tabla | Ruta | Tipo | Hallazgo | Evidencia (grep del uso, o 0 matches) |"
```

### 2. Clasificar (subagente code-reviewer simulado, sonnet)

```
subagent_type: "general-purpose"
model: "sonnet"
prompt: "Actúa como CODE REVIEWER clasificando hallazgos de código muerto.

Hallazgos del scan:
<pegar tabla>

Para cada entrada, clasificar:
- 🟢 SEGURO eliminar — sin consumidores, sin side effects, no es entry point.
- 🟡 VERIFICAR PRIMERO — posible uso dinámico (getattr, importlib, plugin, CLI entry point),
  endpoints FastAPI registrados por decorador, fixtures detectadas por pytest por nombre.
- 🔴 NO TOCAR — entry point (narrative-assistant CLI, routers FastAPI referenciados por path),
  parte de API pública documentada, re-export intencional.

Contexto a considerar:
- api-server/routers/*.py — los endpoints se registran via router.include_router(), la función
  puede parecer 'no llamada' pero la llama FastAPI.
- scripts/*.py — pueden ser entry points ejecutados manualmente por el usuario.
- CLAUDE.md menciona 'narrative-assistant verify', 'narrative-assistant analyze' — esos comandos
  tienen decoradores Click/Typer, pueden parecer no llamados.
- Tests con @pytest.fixture y nombre coincidente con parámetro de otro test.

Output: tabla con clasificación por cada hallazgo."
```

### 3. Presentar al usuario

```
## Hallazgos cleanup

🟢 Seguro eliminar (N items):
  - ruta:línea — motivo

🟡 Verificar primero (N items):
  - ruta:línea — motivo + qué verificar

🔴 No tocar (N items):
  - ruta:línea — por qué es load-bearing
```

### 4. Esperar confirmación

**Nunca** borrar sin OK explícito del usuario. Preguntar:
- ¿Procedo con todos los 🟢?
- ¿Verificamos los 🟡 uno a uno?

### 5. Ejecutar eliminación

Para cada ítem confirmado:
- Borrar archivo / eliminar import / eliminar función.
- Ejecutar `/check` inmediatamente después de cada batch de borrados.
- Si algo falla → revertir ese batch específico (el checkpoint del paso inicial lo permite).

### 6. Commit

Un solo commit por `/cleanup`:
```
chore: remove dead code (N files, N exports)
```

## Qué NUNCA limpiar sin confirmación nivel-2 del usuario

- Archivos en `~/.narrative_assistant/` — datos del usuario.
- Archivos `*.db`, `*.sqlite` en cualquier parte.
- Screenshots si el usuario los usa para docs (preguntar antes).
- Tests `@xfail` en `adversarial/` — son limitaciones NLP documentadas, no código muerto.
