---
name: coverage
description: "Mapa de cobertura de tests para el proyecto dual-stack (backend Python + frontend Vue). Clasifica módulos por riesgo (🔴/🟡/🟢) y prioriza qué escribir primero. Invocar cuando el usuario diga 'qué cobertura tenemos', 'qué falta testear', 'coverage del módulo X', 'tabla de cobertura'."
---

# /coverage — Mapa de cobertura y gaps de tests

## Cuándo usar

- Tras añadir una feature para ver si quedaron gaps.
- Antes de `/audit` para precargar la foto de cobertura.
- Cuando el usuario quiere priorizar qué tests escribir a continuación.
- Como parte del checklist pre-release.

## Argumentos

- (sin args) — cobertura global del proyecto
- `<módulo>` — scope reducido, p.ej. `parsers`, `nlp/coreference_resolver`, `frontend/components/workspace`
- `--run` — ejecutar los runners de cobertura (lento, ~2 min); sin `--run` solo analiza qué tests existen
- `--threshold N` — marcar como 🔴 cualquier módulo con cobertura < N% (default: 60)

## Flujo

### Paso 1 — Mapa estático (siempre, sin `--run`)

Subagente Explore haiku para mapear relaciones fuente ↔ test:

```
subagent_type: "Explore"
model: "haiku"
prompt: "Para este proyecto dual-stack (Python backend en src/narrative_assistant/ y
api-server/, frontend Vue en frontend/src/), construye una tabla de cobertura estática:

1. Lista todos los archivos fuente Python relevantes (excluir __init__.py triviales).
2. Para cada uno, busca si existe un archivo de test en tests/ que lo cubre
   (convención: test_<modulo>.py o tests/<carpeta>/test_<archivo>.py).
3. Haz lo mismo para los componentes Vue en frontend/src/: busca *.spec.ts correspondiente.
4. Output: tabla | Archivo fuente | Test existe (✅/❌) | Ruta del test |

No ejecutes comandos, solo analiza la estructura de archivos."
```

### Paso 2 — Ejecutar runners (solo con `--run`)

En paralelo:

```bash
# Backend
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest --cov=src/narrative_assistant --cov=api-server --cov-report=json --cov-report=term-missing -q -m "" 2>&1 | tail -40

# Frontend
cd /Users/PABLO/repos/narrassist/frontend && npx vitest run --coverage --reporter=json 2>&1 | tail -40
```

Parsear porcentajes por módulo del output JSON/term.

### Paso 3 — Clasificación por riesgo

Para cada módulo sin cobertura suficiente:

| Riesgo | Criterio |
|--------|----------|
| 🔴 ALTO | Módulo toca manuscritos/parsers/seguridad + cobertura < threshold |
| 🟡 MEDIO | Módulo de lógica de negocio + cobertura < threshold |
| 🟢 OK | Cobertura ≥ threshold o módulo es glue code sin lógica |

Criterios adicionales de riesgo alto (siempre 🔴 independiente del %):
- `parsers/` — validan paths y manipulan archivos del usuario
- `nlp/coreference_resolver.py` — núcleo del análisis
- `persistence/database.py` — SQLite WAL
- `exporters/` — escriben archivos al disco del usuario
- `llm/client.py` — única capa que habla con Ollama (posible fuga de datos)

### Paso 4 — Output

```
## Coverage Map — <scope> — <fecha>

### Backend
| Módulo | Test | Cobertura | Riesgo |
|--------|------|-----------|--------|
| parsers/docx_parser.py | ✅ test_docx_parser.py | 78% | 🟡 |
| nlp/coreference_resolver.py | ✅ test_coreference_resolver.py | 42% | 🔴 |
| llm/client.py | ❌ — | 0% | 🔴 |
...

### Frontend
| Componente | Spec | Riesgo |
|------------|------|--------|
| workspace/AlertsDashboard.vue | ✅ | 🟢 |
| components/ExportDialog.vue | ✅ | 🟡 |
| views/WorkspaceView.vue | ❌ | 🔴 |
...

### Top-5 gaps prioritarios
1. 🔴 llm/client.py — 0% cobertura, toca Ollama directamente
2. 🔴 nlp/coreference_resolver.py — 42%, lógica crítica sin edge cases
...

Próximo paso sugerido: `/test llm/client.py` para empezar por el gap de mayor riesgo.
```

**No escribir los tests aquí** — para eso el usuario invoca `/test <módulo>`.
