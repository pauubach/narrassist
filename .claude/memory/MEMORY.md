# TFM - Narrative Assistant Memory

## Project Overview
- **Stack**: Python 3.12.3, FastAPI, Vue 3, SQLite, spaCy, Ollama
- **Purpose**: Manuscript consistency checker for writers/editors (Spanish focus)
- **Repo**: github.com/pauubach/narrassist

## Architecture Patterns
- **Result pattern**: `from narrative_assistant.core.result import Result`
- **API**: FastAPI routers in `api-server/routers/`, deps in `api-server/deps.py`
- **Frontend types**: API types → transformers → domain types (snake_case → camelCase)
- **Alert positions**: `start_char`/`end_char` → `spanStart`/`spanEnd` via transformer

## Sprint History (IMPROVEMENT_PLAN.md)
- **S0**: xfail cleanup (15 tests)
- **S1**: PlanTL RoBERTa NER, multi-model voting, gazetteer auto-feed
- **S2**: Pro-drop gender inference, saliency scoring
- **S3**: Anachronism detection, temporal patterns
- **S4**: Character profiling (6 indicators), network analysis, OOC, classical Spanish
- **S5**: Qwen 2.5 preference, prompt engineering (CoT), anti-injection sanitization
- **S6**: API endpoints (network, timeline, profiles), focus mode, alert navigation fix
- **S15**: Grammar fixes (artículos 'a' tónica, concordancia contextual), alert ordering by severity
- **Tag**: v0.6.0

## Key Files
- [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) - Full sprint plan
- [alerts.py](api-server/routers/alerts.py) - Alert CRUD + focus mode + position resolution
- [relationships.py](api-server/routers/relationships.py) - Network, timeline, profiles, knowledge
- [character_profiling.py](src/narrative_assistant/analysis/character_profiling.py) - 6-indicator profiles
- [classical_spanish.py](src/narrative_assistant/nlp/classical_spanish.py) - Siglo de Oro normalizer
- [prompts.py](src/narrative_assistant/llm/prompts.py) - Centralized prompt templates
- [sanitization.py](src/narrative_assistant/llm/sanitization.py) - Anti-injection protection
- [spanish_rules.py](src/narrative_assistant/nlp/grammar/spanish_rules.py) - Grammar rules (S15: 'a' tónica, 24 sustantivos)
- [agreement.py](src/narrative_assistant/corrections/detectors/agreement.py) - Agreement detector (S15: contextual concord)

## Test Memory Management
- **Default**: `pytest` runs light tests (~3 min), excludes @heavy
- **Heavy tests**: `pytest -m ""` or `python scripts/run_heavy_tests.py`
- **spaCy cache**: `load_spacy_model()` has global cache (won't reload ~500MB)
- **Session fixtures**: `shared_spacy_nlp`, `shared_attribute_extractor` in conftest.py
- **Auto-marking**: adversarial/, evaluation/, integration/, regression/, performance/ → @heavy
- **Hanging tests**: `test_llamacpp_manager.py` has 3 tests that hang (start_server) → @heavy
- **96 xfails**: All in adversarial/ tests, NLP limitations (pro-drop, voseo, ironía)

## Release Checklist
1. `python scripts/sync_version.py X.Y.Z` — syncs all 7 version files
2. Commit: `git commit -m "chore: bump version to X.Y.Z"`
3. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: ..."`
4. Push: `git push && git push origin vX.Y.Z`
- **IMPORTANT**: Step 1 MUST happen before the tag, otherwise .exe/.dmg keep old version name

## User Preferences
- **Version NUNCA debe llegar a v1.x.x** salvo que el usuario lo diga explícitamente
- **Subir minor (0.X.0)**: Pedir confirmación al usuario justificando por qué. Solo patch (0.x.Y) sin preguntar
- **"Borra todo"**: Limpiar SIN preguntar. Borrar los 4 directorios:
  - `~/.narrative_assistant/` (modelos NLP, DB, config ~1.9 GB)
  - `%LOCALAPPDATA%/Narrative Assistant/` (datos app Tauri ~1.2 GB)
  - `~/.ollama/` (modelos LLM ~1.5 GB)
  - `~/.cache/huggingface/` (cache HF ~458 MB)
- **git commits**: Use `--no-verify` (pre-commit hooks can overload modest hardware)

## Enrichment Cache Schema Versioning
- **Purpose**: Force recomputation of cached enrichment results when code logic changes
- **Dict**: `ENRICHMENT_SCHEMA_VERSIONS` in `_enrichment_cache.py` — 27 enrichment types, each with an int version
- **How to use**: Bump the version number for a specific enrichment type when its computation logic or output format changes
- **DB column**: `schema_version INTEGER NOT NULL DEFAULT 0` in `enrichment_cache` table
- **3 layers of protection**:
  1. `get_cached_enrichment()` rejects entries where `cached_version < required_version` → GET endpoints return None → compute on-the-fly
  2. `_build_default_input_payload()` includes `schema_version` in input_hash → `_run_enrichment()` detects hash mismatch → recomputes
  3. **Fast-path** (`analysis.py`): `get_stale_enrichment_phases()` checks which enrichment phases have outdated entries → runs ONLY those phases selectively instead of skipping all
- **Phase mapping**: `ENRICHMENT_TO_PHASE` dict maps enrichment types → phase names (relationships/voice/prose/health)
- **Key files**: `_enrichment_cache.py` (versions, mapping, stale check), `_enrichment_phases.py` (cache write), `analysis.py` (fast-path), `database.py` (schema migration)
- **Tests**: `test_invalidation.py::TestSchemaVersionInvalidation` (7 tests)

## Gotchas
- `FORMAL_MARKERS` lives in `voice.profiles`, not in `character_profiling` - use lazy import
- Classical Spanish regex: must include conjugated forms (dexaría, passaría) not just infinitives
- Medieval detection: "fijo"/"fermoso" need explicit markers, not just golden age patterns
- `entity.entity_type` is an enum - use `.value` for string comparison
- **NEVER run `pytest tests/` sin -m filter** en equipos modestos → segfault por RAM
- `test_llamacpp_manager.py` últimos 3 tests cuelgan sin timeout (start_server)
- **Alert ordering** (S15): `get_by_project_prioritized()` → severity > confidence > position (NOT position first)
- **'a' tónica** (S15): FEMININE_WITH_EL has 24 sustantivos (agua, ama, ala, alma, arma, hacha, etc.)
- **Concordancia contextual** (S15): `_is_subject_modifier()` elimina falsos positivos "mandíbula...furioso"
- **Entity validation**: DISCOURSE_MARKERS in `entity_validator.py` (~35 temporal/discourse markers)
- **Discourse markers** are NOT entities: "acto seguido", "poco después", "de repente", "mientras tanto", etc.
- **Fast-path** (`analysis.py:670+`): When document fingerprint unchanged, skips NLP phases but NOW checks enrichment schema versions. If you bump a schema version, fast-path re-runs only the affected enrichment phase(s)
- **`_generate_global_summary()`** initializes its own LLM client because `self.ollama_client` returns None in BASIC mode (property guard at line ~567)
- **LLM client en chapter_summary.py**: Usar `get_llm_client()` de `llm.client`, NO `OllamaClient` (no existe). Método: `client.complete(prompt, model_name, temperature)` NO `.generate()`
- **enrichment_cache NULL scope**: SQLite `UNIQUE` con NULL no funciona (`NULL != NULL`). Fix: `idx_enrichment_unique_scope` con COALESCE. Sin esto, `INSERT OR REPLACE` crea duplicados
