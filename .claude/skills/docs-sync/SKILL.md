---
name: docs-sync
description: "Detecta divergencias entre la documentación en docs/ y el código actual (firmas de funciones renombradas, módulos movidos, configuración obsoleta). Invocar cuando el usuario diga 'actualiza los docs', 'hay docs desactualizados', 'sincroniza documentación', 'los docs están desfasados'."
---

# /docs-sync — Sincronización de documentación con el código

## Cuándo usar

- Tras un refactor grande que movió o renombró módulos.
- Después de `/audit` si se detectó doc drift.
- Como paso final antes de una release.
- Cuando el usuario menciona que los docs están desfasados.

## Argumentos

- (sin args) — auditoría completa de docs/
- `<doc>` — archivo o carpeta específica, p.ej. `docs/02-architecture/SECURITY.md`
- `--fix` — aplicar fixes automáticos donde sean triviales (renombrados, rutas de archivos)
- `--report-only` — solo listar divergencias, no proponer cambios

## Flujo

### Paso 1 — Inventario de docs

```bash
find /Users/PABLO/repos/narrassist/docs -name "*.md" | sort
```

Identificar docs de arquitectura, guías de módulos, y docs de API.

### Paso 2 — Análisis de drift (subagente Explore sonnet)

```
subagent_type: "Explore"
model: "sonnet"
prompt: "Analiza el drift entre la documentación y el código actual en este proyecto.

Para cada archivo .md en docs/, identifica:
1. Rutas de archivos mencionadas que ya no existen (archivos movidos o renombrados).
2. Nombres de funciones/clases/módulos mencionados que ya no existen en el código.
3. Comandos CLI mencionados que ya no funcionan (verificar en pyproject.toml [project.scripts]).
4. Configuraciones de variables de entorno obsoletas (comparar con CLAUDE.md y core/config.py).
5. Diagramas de arquitectura que no reflejan la estructura actual de src/.

Para cada divergencia encontrada:
- Citar la línea exacta del doc que está mal.
- Citar la evidencia en el código de que está desactualizado.
- Clasificar: 🔴 Misleading (puede causar errores) / 🟡 Stale (información vieja) / 🟢 Minor (typo, estilo).

Output: tabla | Doc | Línea | Texto actual | Realidad | Severidad | Fix sugerido |"
```

### Paso 3 — Revisión de CLAUDE.md específicamente

CLAUDE.md es el doc más crítico (Claude lo lee siempre). Verificar:

```bash
# ¿Los scripts mencionados existen?
ls /Users/PABLO/repos/narrassist/scripts/

# ¿Las variables de entorno documentadas están en config.py?
grep -n "NA_" /Users/PABLO/repos/narrassist/src/narrative_assistant/core/config.py | head -20
```

### Paso 4 — Cambios en API backend

```bash
# Buscar endpoints actuales vs documentados
grep -rn "@router\." /Users/PABLO/repos/narrassist/api-server/routers/ | grep "def " | head -30
```

Comparar con cualquier doc de API en `docs/`.

### Paso 5 — Output

```
## Docs Sync Report — <fecha>

### 🔴 Misleading (corrección urgente)
| Doc | Línea | Problema | Fix |
|-----|-------|---------|-----|
| docs/02-architecture/SECURITY.md:45 | Menciona `src/sanitization.py` | Movido a `src/narrative_assistant/parsers/sanitization.py` | Actualizar ruta |

### 🟡 Stale (desactualizado)
| Doc | Línea | Problema | Fix |
|-----|-------|---------|-----|

### 🟢 Minor
...

### Docs en buen estado ✅
- CLAUDE.md — variables de entorno correctas
- docs/01-getting-started/ — setup steps verificados

### Acciones propuestas
```

### Paso 6 — Aplicar fixes (solo con `--fix`)

Para fixes triviales (renombrar rutas de archivos, actualizar nombres de funciones):
- Editar directamente.
- Para cambios de significado o reestructuración → proponer al usuario, no aplicar automáticamente.

Después de aplicar: `/check` para verificar que no se rompió nada.
