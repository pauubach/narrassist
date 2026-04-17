---
name: test
description: "Generar o actualizar tests para un archivo/módulo específico, respetando helpers, fixtures (shared_spacy_nlp, shared_attribute_extractor) y convenciones del proyecto (@heavy, pytest, vitest). Invocar cuando el usuario diga 'escribe tests para X', 'falta cobertura en Y', 'añade un test que cubra Z', 'necesito test de regresión para este bug', 'escribe el spec de este componente Vue'. Ejemplos: 'escribe tests para el EPUB parser', 'añade spec vitest para AlertsDashboard', 'test de regresión para el fallo en correferencias'."
---

# /test — Generar o actualizar tests

## Argumentos

- `<archivo-o-módulo>` — target a testear. Ej: `src/narrative_assistant/nlp/orthography/voting_checker.py`.

## Flujo

### 1. Identificar stack

- Archivo `.py` → pytest, suite en `tests/`.
- Archivo `.vue` / `.ts` → vitest, suite en `frontend/src/**/*.test.ts`.

### 2. Leer contexto compartido

**Backend (Python):**
- `tests/conftest.py` — fixtures de sesión (`shared_spacy_nlp`, `shared_attribute_extractor`).
- `pytest.ini` / `pyproject.toml` — markers disponibles (`heavy`, `integration`, `regression`, etc.).
- Tests hermanos en el mismo directorio — patrón de naming y estructura.

**Frontend:**
- `frontend/vitest.config.ts` — configuración.
- Tests hermanos — patrón de mount, mocks, imports de PrimeVue.

### 3. Leer el archivo a testear

- Identificar funciones/clases públicas.
- Identificar ramas (if/else, excepciones, early returns).
- Identificar dependencias externas que requieren mock (DB, Ollama, HTTP).

### 4. Leer el test existente si hay

- Si ya existe `test_<archivo>.py` o `<archivo>.test.ts`:
  - Determinar qué está cubierto y qué falta.
  - No duplicar casos.
  - Respetar el estilo de los tests existentes.

### 5. Generar los tests

Delegar a un subagente para la generación:

```
subagent_type: "general-purpose"
model: "sonnet"
prompt: "Actúa como TEST WRITER para narrassist.

Archivo a testear: <ruta>
Contexto (conftest.py, tests hermanos, archivo fuente): <pegar>
Tests existentes: <pegar o 'ninguno'>

Generar tests que:
- Cubran happy path + edge cases + error cases.
- Usen fixtures de sesión cuando aplique (shared_spacy_nlp, etc.) para no
  recargar modelos ~500MB.
- Marquen @heavy los tests que tarden >5s o requieran Ollama/HTTP/modelo grande.
- Usen type hints y docstrings en español.
- Sigan el estilo de los tests hermanos.

Reglas:
- NO usar # type: ignore ni # noqa para silenciar mypy/ruff.
- NO escribir tests que envíen datos a internet.
- Si el módulo hace I/O de red real (Ollama, HF), mockearlo con pytest fixtures
  o con vi.mock en vitest.

Output: archivo de test completo, listo para pegar."
```

### 6. Ejecutar el test SOLO

**Backend:**
```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest tests/<path>/test_<archivo>.py -x -v
```

**Frontend:**
```bash
cd /Users/PABLO/repos/narrassist/frontend && npx vitest run <archivo>.test.ts
```

### 7. Iterar si falla

- Si el test falla por bug en el test → corregir inline.
- Si el test falla porque expone un bug real en el código → **parar**, informar al usuario: el test funcionó, hay un bug real en `<archivo>` que debe decidir si arreglar ahora o abrir ticket.

### 8. Verificar cobertura

```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest tests/<path>/ --cov=src/narrative_assistant/<path>
```

Mostrar % de cobertura antes/después.

## Reglas

- **Nunca** añadir tests que requieran internet.
- **Nunca** marcar un test como `@pytest.mark.skip` sin justificación explícita en docstring.
- **Nunca** usar `@xfail` nuevo sin documentar la limitación NLP que lo justifica (ver `tests/adversarial/`).
- Modelos NLP pesados → usar fixtures de sesión, no instancias por test.
