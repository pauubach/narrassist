---
name: refactor
description: "Renombrado o extracción de entidades con propagación completa: busca TODOS los consumidores antes de mover/renombrar, actualiza imports, tests y docs en el mismo paso. Invocar cuando el usuario diga 'renombra X a Y', 'extrae esta función a un módulo', 'mueve la clase X al módulo Y', 'separa esto en dos archivos'."
---

# /refactor — Renombrado y extracción con propagación completa

## Regla crítica

**Nunca renombrar sin encontrar primero TODOS los consumidores.** Un rename parcial rompe el proyecto silenciosamente (especialmente en Python donde los imports son strings).

## Argumentos

- `rename <viejo> <nuevo>` — renombrar función/clase/módulo
- `extract <función> to <módulo>` — extraer a nuevo módulo
- `move <archivo> to <destino>` — mover archivo con actualización de imports
- `split <archivo>` — dividir módulo grande en partes cohesivas

## Flujo

### Paso 1 — Checkpoint git PRIMERO

```bash
git status --short
```

Si hay cambios no commiteados → **parar**. Pedir que el usuario commitee o stashee antes. El refactor debe empezar desde un estado limpio para que el diff sea legible.

### Paso 2 — Encontrar TODOS los consumidores

```bash
# Para renombrar una clase/función Python
grep -rn "<nombre_viejo>" /Users/PABLO/repos/narrassist/src/ /Users/PABLO/repos/narrassist/api-server/ /Users/PABLO/repos/narrassist/tests/ --include="*.py"

# Para renombrar un componente Vue
grep -rn "<NombreViejo>" /Users/PABLO/repos/narrassist/frontend/src/ --include="*.{vue,ts}"

# Para renombrar un módulo (import)
grep -rn "from.*<módulo_viejo>" /Users/PABLO/repos/narrassist/src/ --include="*.py"
grep -rn "import.*<módulo_viejo>" /Users/PABLO/repos/narrassist/src/ --include="*.py"
```

Usar subagente Explore si el scope es ambiguo:

```
subagent_type: "Explore"
model: "haiku"
prompt: "Busca TODOS los usos de '<nombre_viejo>' en el proyecto narrassist.
Incluir: imports, llamadas, herencia, type hints, strings de registro (routes FastAPI,
decoradores, pytest marks), referencias en docs/ y CLAUDE.md.
Output: lista completa de archivo:línea:contexto para cada ocurrencia."
```

### Paso 3 — Presentar scope al usuario

```
## Scope del refactor: rename '<viejo>' → '<nuevo>'

Archivos afectados (N):
- src/narrative_assistant/nlp/ner.py:45 — definición
- src/narrative_assistant/nlp/ner.py:89 — uso interno
- api-server/routers/analysis.py:12 — import
- tests/nlp/test_ner.py:8 — import en test
- docs/02-architecture/NLP.md:23 — referencia en docs

Archivos que requieren atención especial:
- ⚠️ CLAUDE.md:156 — mencionado en documentación de usuario

¿Procedo con el rename completo?
```

Esperar OK del usuario antes de tocar nada.

### Paso 4 — Ejecutar el rename

Orden de ejecución:

1. **Definición** — renombrar en el archivo fuente.
2. **Imports en otros módulos** — actualizar cada import.
3. **Tests** — actualizar imports y referencias en tests.
4. **Docs** — actualizar referencias en `docs/` y `CLAUDE.md`.
5. **Strings mágicos** — si el nombre aparece en strings (rutas FastAPI, keys de config), actualizar con cuidado (pueden no ser renombrables automáticamente).

Para archivos (move/split):
```bash
git mv <origen> <destino>  # preserva historia git
```

### Paso 5 — Verificar con /check

```bash
# Backend
cd /Users/PABLO/repos/narrassist && .venv/bin/ruff check src/ api-server/ tests/
cd /Users/PABLO/repos/narrassist && .venv/bin/mypy src/
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest -x

# Frontend (si aplica)
cd /Users/PABLO/repos/narrassist/frontend && npx vue-tsc --noEmit
cd /Users/PABLO/repos/narrassist/frontend && npx vitest run
```

Si algo falla → diagnosticar el import roto y corregir antes de continuar.

### Paso 6 — Commit del refactor

Un solo commit con todos los cambios del rename:
```
refactor: rename <viejo> → <nuevo> (N archivos)
```

## Anti-patrones

- **NO** usar search-replace ciego sin revisar contexto: `foo` puede ser parte de `foo_bar` o `foobar`.
- **NO** asumir que `mypy` encontrará todo — los strings en FastAPI routes no son chequeados por mypy.
- **NO** renombrar y cambiar funcionalidad en el mismo commit — un refactor puro no cambia comportamiento.
- **NO** olvidar actualizar docs — los docs obsoletos son una deuda que cuesta caro.
