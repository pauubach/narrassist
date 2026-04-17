---
description: "Reglas para código Python del backend: pipeline NLP, API FastAPI, parsers, persistencia. Aplicar al editar archivos en src/narrative_assistant/** y api-server/**."
globs: ["src/narrative_assistant/**/*.py", "api-server/**/*.py", "tests/**/*.py"]
---

# Backend Python — Reglas del proyecto

## Result pattern

Operaciones que pueden fallar → `Result[T]`, **no excepciones sobre flujo normal**.

```python
from narrative_assistant.core.result import Result

def process(data) -> Result[OutputType]:
    if error_condition:
        return Result.failure(SomeError(...))
    return Result.success(output)
```

- Parsers: `Result[RawDocument]` tras validación previa.
- Detectores NLP: si la operación puede fallar parcialmente sin que sea bug, `Result`.
- Excepciones: solo para errores verdaderamente inesperados (programación, invariantes rotas).

## Type hints

- **Obligatorios** en funciones públicas (las que no empiezan con `_`).
- `Optional[X]` → preferir `X | None` (Python 3.11+).
- **PROHIBIDO** `# type: ignore` — arreglar el tipo real o cambiar la signatura.

## Enums

```python
# BAD — compara con string
if entity.entity_type == "PERSON":

# GOOD — compara con enum, o usa .value si es imprescindible
if entity.entity_type == EntityType.PERSON:
if entity.entity_type.value == "PERSON":
```

## Validación de archivos en parsers

**SIEMPRE** validar antes de abrir — path traversal + tamaño + extensión:

```python
def parse(self, path: Path) -> Result[RawDocument]:
    validation = self.validate_file(path)
    if validation.is_failure:
        return validation
    # ... continuar
```

## Singletons

Double-checked locking con `threading.Lock()` — nunca singleton naive.

```python
_lock = threading.Lock()
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = create_instance()
    return _instance
```

## Fixtures de sesión NLP

Modelos pesados (spaCy ~500MB, embeddings ~500MB) → usar `shared_spacy_nlp` y `shared_attribute_extractor` de `tests/conftest.py`. **Nunca** `load_spacy_model()` en un test sin fixture de sesión.

## Aislamiento de manuscritos

- **PROHIBIDO** enviar texto de manuscritos a servicios externos (no a OpenAI, no a Claude API, no a analytics).
- **PROHIBIDO** `requests.get/post` a hosts que no sean:
  - `localhost` / `127.0.0.1` (Ollama, API server).
  - `huggingface.co` (solo descarga inicial de modelos vía `ModelManager`).
  - `spacy.io` (solo descarga inicial).
- Tráfico de verificación de licencias permitido al endpoint oficial del proyecto.

## API FastAPI

- Routers en `api-server/routers/`.
- Dependencias compartidas en `api-server/deps.py`.
- Respuestas: snake_case en backend, transformer a camelCase en frontend (no cambiar este contrato sin coordinar).
- Paginación estándar: `{ items: [], total: int, page: int, size: int }`.
- Errores: `{ detail: string, code: string }`.

## Tests

- Marcador `@heavy` para tests que tarden >5s, carguen modelos grandes o requieran Ollama.
- Marcador `@pytest.mark.xfail` SOLO para limitaciones NLP documentadas (`adversarial/`).
- `pytest` por defecto excluye `heavy`; para suite completa: `pytest -m ""`.
- **NUNCA** `pytest tests/` sin `-m` o `-x` en hardware modesto — segfault por RAM.

## Logging

- Usar `logging.getLogger(__name__)` — nunca `print` en producción.
- Niveles: `DEBUG` para flujo interno, `INFO` para fases del pipeline, `WARNING` para degradaciones, `ERROR` para fallos recuperables, `CRITICAL` para fallos que abortan.

## Gotchas conocidos (de auto-memoria)

- `FORMAL_MARKERS` vive en `voice.profiles`, **no** en `character_profiling` → usar lazy import.
- `entity.entity_type` es enum → usar `.value` para comparar con string si es necesario.
- Discourse markers (`"acto seguido"`, `"poco después"`, etc.) NO son entidades — listar en `DISCOURSE_MARKERS` de `entity_validator.py`.
- Fast-path de `analysis.py:670+` revisa `ENRICHMENT_SCHEMA_VERSIONS`. Si cambias la lógica de un enrichment, **bump** la versión en `_enrichment_cache.py`.
- `get_llm_client()` está en `llm.client`. `OllamaClient` NO existe como clase pública — no lo uses.
- `enrichment_cache`: SQLite `UNIQUE` con NULL no funciona (`NULL != NULL`). Usa `idx_enrichment_unique_scope` con `COALESCE`.
