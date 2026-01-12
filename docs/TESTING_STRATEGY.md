# Estrategia de Testing - Narrative Assistant

> **CRÍTICO**: Código actual tiene 0% test coverage. Este documento define la estrategia de testing para alcanzar MVP production-ready.

---

## Estado Actual (2026-01-09)

### ❌ Problemas Identificados en Code Review

**Revisión por 3 agentes (1 Opus + 2 Sonnet):**
- Score de calidad: 9.5/10
- **Único problema crítico**: 0% test coverage
- Tests no implementados a pesar de tener pytest configurado

### ✅ Infraestructura Existente

```toml
# pyproject.toml - YA configurado
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.10",
    "factory-boy>=3.2",
    "syrupy>=4.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
markers = [
    "slow: marks tests as slow (NLP integration)",
]
```

**Estado**: Dependencias instaladas, configuración lista, pero `tests/` vacío.

---

## Prioridades de Testing (MVP)

### 🔴 P0: Tests Críticos (BLOQUEANTES para producción)

#### 1. Alert System Tests (4-5 horas)

**tests/test_alerts/test_repository.py**
```python
# Tests de persistencia
- test_create_alert_success()
- test_create_alert_with_invalid_data()
- test_get_alert_by_id()
- test_get_alert_not_found()
- test_get_alerts_by_project()
- test_update_alert_status()
- test_delete_alert()
- test_count_by_status()
```

**tests/test_alerts/test_engine.py**
```python
# Tests de lógica de negocio
- test_create_alert_calculates_severity()
- test_create_alerts_batch()
- test_filter_alerts_by_severity()
- test_filter_alerts_by_category()
- test_prioritize_alerts()
- test_get_summary_statistics()
- test_create_from_attribute_inconsistency()
- test_thread_safe_singleton()
```

**tests/test_alerts/test_models.py**
```python
# Tests de modelos
- test_alert_serialization()
- test_alert_filter_matches()
- test_alert_is_open()
- test_alert_is_closed()
```

**Estimación**: 3 horas

#### 2. Integration Tests (1-2 horas)

**tests/test_integration/test_alert_pipeline.py**
```python
# Tests end-to-end
- test_attribute_inconsistency_to_alert()
  # AttributeInconsistency → AlertEngine → DB → retrieval

- test_entity_id_resolution()
  # entity_name → EntityRepository.get_by_name() → entity_id

- test_alert_lifecycle()
  # NEW → OPEN → ACKNOWLEDGED → RESOLVED

- test_database_foreign_keys()
  # project_id references projects(id) ON DELETE CASCADE
```

**Estimación**: 1.5 horas

#### 3. Core System Tests (1-2 horas)

**tests/test_core/test_result.py**
```python
- test_result_success()
- test_result_failure()
- test_result_partial()
- test_result_error_property()  # Nuevo
- test_result_unwrap()
- test_result_merge()
```

**tests/test_persistence/test_database.py**
```python
- test_database_initialization()
- test_database_schema_created()
- test_database_indices_exist()
- test_transaction_commit()
- test_transaction_rollback()
- test_in_memory_database()
```

**Estimación**: 1.5 horas

---

### 🟡 P1: Tests Completos por Módulo (MVP Completo)

#### 4. Parsers Tests (2-3 horas)

**tests/test_parsers/test_docx_parser.py**
```python
- test_parse_docx_valid_file()
- test_parse_docx_with_chapters()
- test_parse_docx_with_styles()
- test_parse_docx_invalid_file()
- test_parse_docx_corrupted_file()
- test_parse_docx_file_too_large()
```

**tests/test_parsers/test_txt_parser.py**
```python
- test_parse_txt_utf8()
- test_parse_txt_latin1()
- test_parse_txt_with_encoding_detection()
- test_parse_markdown()
```

**tests/test_parsers/test_structure_detector.py**
```python
- test_detect_chapters_numbered()
- test_detect_chapters_roman_numerals()
- test_detect_scenes()
- test_detect_nested_structure()
```

**tests/test_parsers/test_sanitization.py**
```python
- test_validate_file_path_traversal_attack()
- test_validate_file_size_limit()
- test_validate_file_extension()
- test_sanitize_filename()
```

#### 5. NLP Core Tests (3-4 horas, @pytest.mark.slow)

**tests/test_nlp/test_ner.py**
```python
- test_extract_persons()
- test_extract_locations()
- test_extract_organizations()
- test_gazetteer_dynamic_update()
- test_entity_disambiguation()
- test_coreference_resolution()
```

**tests/test_nlp/test_attributes.py**
```python
- test_extract_physical_attributes()
- test_extract_personality_attributes()
- test_extract_possession_attributes()
- test_extract_relationships()
- test_negation_detection()
- test_metaphor_detection()
- test_context_extraction()
```

**tests/test_nlp/test_dialogue.py**
```python
- test_parse_dialogue_guillemets()
- test_parse_dialogue_em_dash()
- test_parse_dialogue_quotes()
- test_extract_speaker()
```

**tests/test_nlp/test_coref.py**
```python
- test_resolve_pronouns()
- test_gender_agreement()
- test_pro_drop_inference()
```

**tests/test_nlp/test_embeddings.py**
```python
- test_load_model_offline()
- test_encode_text()
- test_similarity_calculation()
- test_batch_processing()
- test_fallback_cpu_on_oom()
```

**tests/test_nlp/test_spacy_gpu.py**
```python
- test_detect_cuda()
- test_detect_mps()
- test_fallback_cpu()
- test_load_model_local()
```

#### 6. Entities Tests (2-3 horas)

**tests/test_entities/test_models.py**
```python
- test_entity_creation()
- test_entity_types()
- test_mention_creation()
- test_entity_merge()
```

**tests/test_entities/test_repository.py**
```python
- test_create_entity()
- test_get_entity_by_id()
- test_search_entities_by_name()
- test_search_entities_fuzzy()
- test_update_entity()
- test_delete_entity()
- test_get_entities_by_type()
- test_transaction_rollback()
```

**tests/test_entities/test_fusion.py**
```python
- test_calculate_similarity()
- test_merge_entities()
- test_merge_mentions()
- test_fuzzy_matching()
```

#### 7. Analysis Tests (1-2 horas)

**tests/test_analysis/test_attribute_consistency.py**
```python
- test_detect_direct_contradiction()
- test_detect_antonym()
- test_detect_semantic_difference()
- test_detect_value_change()
- test_synonym_filtering()
- test_confidence_calculation()
- test_entity_id_present()  # Nuevo campo
- test_group_by_entity()
```

#### 8. Persistence Tests (2-3 horas)

**tests/test_persistence/test_project.py**
```python
- test_create_project()
- test_get_project()
- test_update_project()
- test_delete_project_cascade()
- test_list_projects()
```

**tests/test_persistence/test_session.py**
```python
- test_create_session()
- test_get_active_sessions()
- test_close_session()
```

**tests/test_persistence/test_history.py**
```python
- test_record_action()
- test_get_history()
- test_undo_action()
```

**tests/test_persistence/test_document_fingerprint.py**
```python
- test_calculate_sha256()
- test_calculate_jaccard()
- test_detect_changes()
```

---

### 🔵 P2: Tests End-to-End Completos (Post-MVP)

#### 9. E2E Pipeline Completo (3-4 horas)

**tests/test_e2e/test_full_pipeline.py**
```python
- test_docx_to_alerts_full_pipeline()
  # DOCX file → parse → NER → attributes → inconsistencies → alerts → DB
  # Verifica todo el flujo con documento real

- test_txt_to_alerts_full_pipeline()
  # TXT file → parse → ... → alerts

- test_pipeline_with_multiple_chapters()
  # Documento multi-capítulo con entidades recurrentes

- test_pipeline_with_entity_fusion()
  # "Ana" y "Anna" se fusionan correctamente

- test_pipeline_performance()
  # Documento de 50k palabras procesa en < 60 segundos
```

**tests/test_e2e/test_cli_e2e.py**
```python
- test_cli_analyze_command()
  # narrative-assistant analyze documento.docx

- test_cli_verify_command()
  # narrative-assistant verify

- test_cli_info_command()
  # narrative-assistant info

- test_cli_project_list()
  # narrative-assistant project list

- test_cli_alert_list()
  # narrative-assistant alert list --project=1
```

**tests/test_e2e/test_exporters.py**
```python
- test_export_character_sheets()
  # Genera fichas de personaje completas

- test_export_style_guide()
  # Genera hoja de estilo con decisiones

- test_export_alerts_json()
  # Exporta alertas a JSON

- test_export_alerts_markdown()
  # Exporta alertas a Markdown
```

**tests/test_e2e/test_session_workflow.py**
```python
- test_create_project_and_session()
  # Workflow: crear proyecto → iniciar sesión → analizar → revisar alertas

- test_resolve_alert_workflow()
  # NEW → OPEN → ACKNOWLEDGED → RESOLVED

- test_dismiss_false_positive()
  # Usuario descarta falso positivo

- test_entity_merge_workflow()
  # Usuario fusiona entidades duplicadas manualmente
```

**tests/test_e2e/test_edge_cases.py**
```python
- test_very_large_document()
  # 200k+ palabras, chunking automático

- test_document_with_no_entities()
  # Texto sin personajes identificables

- test_document_with_minimal_dialogue()
  # Novela sin diálogos

- test_multilingual_text()
  # Texto con palabras en otros idiomas (inglés, francés)

- test_corrupted_document_recovery()
  # Documento parcialmente corrupto
```

---

## Estructura de Directorio de Tests (Completa)

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartidos (DB, projects, entities)
├── fixtures/                # Archivos de test (sample.docx, sample.txt)
│   ├── sample_manuscript.docx
│   ├── sample_manuscript.txt
│   └── corrupted_file.docx
│
├── test_core/               # ✅ P0 (1.5h)
│   ├── __init__.py
│   ├── test_result.py       # Result pattern + .error property
│   ├── test_errors.py
│   └── test_config.py
│
├── test_parsers/            # ✅ P1 (2-3h)
│   ├── __init__.py
│   ├── test_docx_parser.py
│   ├── test_txt_parser.py
│   ├── test_structure_detector.py
│   └── test_sanitization.py
│
├── test_persistence/        # ✅ P1 (2-3h)
│   ├── __init__.py
│   ├── test_database.py     # Schema, índices, transactions
│   ├── test_project.py
│   ├── test_session.py
│   ├── test_history.py
│   └── test_document_fingerprint.py
│
├── test_entities/           # ✅ P1 (2-3h)
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   └── test_fusion.py
│
├── test_nlp/                # ✅ P1 (3-4h, @slow)
│   ├── __init__.py
│   ├── test_ner.py
│   ├── test_attributes.py
│   ├── test_dialogue.py
│   ├── test_coref.py
│   ├── test_embeddings.py
│   ├── test_spacy_gpu.py
│   └── test_chunking.py
│
├── test_analysis/           # ✅ P1 (1-2h)
│   ├── __init__.py
│   └── test_attribute_consistency.py
│
├── test_alerts/             # 🔴 P0 CRÍTICO (3h)
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   └── test_engine.py
│
├── test_integration/        # 🔴 P0 CRÍTICO (1.5h)
│   ├── __init__.py
│   └── test_alert_pipeline.py
│
└── test_e2e/                # ✅ P2 (3-4h)
    ├── __init__.py
    ├── test_full_pipeline.py
    ├── test_cli_e2e.py
    ├── test_exporters.py
    ├── test_session_workflow.py
    └── test_edge_cases.py
```

**Total archivos**: ~40 archivos de test
**Total tests estimados**: ~300-400 tests individuales

---

## Fixtures Comunes (conftest.py)

```python
import pytest
from narrative_assistant.persistence.database import get_database
from narrative_assistant.entities.repository import get_entity_repository
from narrative_assistant.alerts.repository import get_alert_repository

@pytest.fixture
def db():
    """Base de datos en memoria para tests."""
    db = get_database(":memory:")
    db.initialize_schema()
    yield db
    # Cleanup handled by in-memory

@pytest.fixture
def project_id(db):
    """Crea un proyecto de prueba."""
    with db.transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (name, document_fingerprint, document_format) "
            "VALUES (?, ?, ?)",
            ("Test Project", "test_fp_123", "docx")
        )
    return cursor.lastrowid

@pytest.fixture
def entity_repo(db):
    """Repositorio de entidades."""
    return get_entity_repository()

@pytest.fixture
def alert_repo(db):
    """Repositorio de alertas."""
    return get_alert_repository()
```

---

## Comandos de Testing

```bash
# Ejecutar todos los tests
pytest

# Tests con coverage
pytest --cov=src/narrative_assistant --cov-report=html

# Solo tests rápidos (sin @slow)
pytest -m "not slow"

# Solo tests de alerts
pytest tests/test_alerts/

# Verbose con traceback completo
pytest -vv --tb=long

# Ejecutar test específico
pytest tests/test_alerts/test_engine.py::test_create_alert_success
```

---

## Cobertura Objetivo

| Módulo | Objetivo MVP | Objetivo v1.0 |
|--------|--------------|---------------|
| `alerts/` | **90%** | 95% |
| `core/` | **80%** | 90% |
| `persistence/` | **75%** | 85% |
| `analysis/` | 60% | 80% |
| `nlp/` | 40% (slow) | 70% |
| **Global** | **70%** | 85% |

---

## Criterios de Aceptación MVP

✅ Tests deben pasar para considerar STEP 7.5 completado:

1. **Alert System**: 100% tests P0 pasando
2. **Integration**: Pipeline completo funciona end-to-end
3. **Core**: Result pattern y Database tests pasando
4. **Coverage**: Al menos 70% global
5. **CI Ready**: Tests ejecutables en CI/CD (GitHub Actions)

---

## Roadmap de Implementación Completo

### 🔴 FASE 1: Tests Críticos MVP (P0) - 6 horas
**Objetivo**: Alcanzar 70% coverage, código seguro para producción

#### Sesión 1: Alert Tests (3 horas)
- [ ] Crear estructura `tests/test_alerts/`
- [ ] Implementar `test_models.py` (Alert, AlertFilter)
- [ ] Implementar `test_repository.py` (CRUD, indices nuevos)
- [ ] Implementar `test_engine.py` (filtering, prioritization, batch)

#### Sesión 2: Integration Tests (1.5 horas)
- [ ] Crear `tests/test_integration/`
- [ ] Test end-to-end AttributeInconsistency → Alert
- [ ] Test entity_id resolution (entity_name → entity_id)
- [ ] Test alert lifecycle (NEW → RESOLVED)
- [ ] Test database foreign keys y cascade deletes

#### Sesión 3: Core Tests (1.5 horas)
- [ ] Tests de Result pattern (incluyendo .error property)
- [ ] Tests de Database (schema, índices, transactions)
- [ ] Fixtures en `conftest.py`
- [ ] Tests de errores y excepciones

#### Sesión 4: Verificación P0 (30 min)
- [ ] Ejecutar `pytest --cov` y verificar 70%+ coverage
- [ ] Todos los tests P0 pasan
- [ ] Documentar en PROJECT_STATUS.md
- [ ] Commit: "feat: add critical unit tests (70% coverage)"

**Total FASE 1**: 6 horas

---

### 🟡 FASE 2: Tests Completos por Módulo (P1) - 15-18 horas
**Objetivo**: Alcanzar 85% coverage, todos los módulos testeados

#### Sesión 5: Parsers Tests (2-3 horas)
- [ ] `test_docx_parser.py` (parsing, validación, errores)
- [ ] `test_txt_parser.py` (encodings, markdown)
- [ ] `test_structure_detector.py` (chapters, scenes)
- [ ] `test_sanitization.py` (security, path traversal)

#### Sesión 6: Entities Tests (2-3 horas)
- [ ] `test_models.py` (Entity, Mention, Merge)
- [ ] `test_repository.py` (CRUD, search, fuzzy matching)
- [ ] `test_fusion.py` (similarity, merge logic)

#### Sesión 7: Persistence Tests (2-3 horas)
- [ ] `test_database.py` (schema validation, indices check)
- [ ] `test_project.py` (CRUD, cascade deletes)
- [ ] `test_session.py` (lifecycle)
- [ ] `test_history.py` (undo/redo)
- [ ] `test_document_fingerprint.py` (SHA-256, Jaccard)

#### Sesión 8: Analysis Tests (1-2 horas)
- [ ] `test_attribute_consistency.py` (contradictions, synonyms, entity_id)

#### Sesión 9: NLP Tests - Parte 1 (2 horas)
- [ ] `test_ner.py` (entity extraction, gazetteer)
- [ ] `test_dialogue.py` (4 formatos, speaker extraction)
- [ ] `test_coref.py` (pronoun resolution, heuristics)

#### Sesión 10: NLP Tests - Parte 2 (2 horas)
- [ ] `test_attributes.py` (physical, personality, possessions)
- [ ] `test_embeddings.py` (offline models, similarity)
- [ ] `test_spacy_gpu.py` (CUDA/MPS detection)
- [ ] `test_chunking.py` (large documents)

#### Sesión 11: Verificación P1 (1 hora)
- [ ] Ejecutar `pytest --cov` y verificar 85%+ coverage
- [ ] Ejecutar `pytest -m slow` para NLP tests
- [ ] Documentar en PROJECT_STATUS.md
- [ ] Commit: "feat: comprehensive test suite (85% coverage)"

**Total FASE 2**: 15-18 horas

---

### 🔵 FASE 3: Tests E2E y Edge Cases (P2) - 4-5 horas
**Objetivo**: Validar workflows completos y casos extremos

#### Sesión 12: E2E Pipeline (2 horas)
- [ ] `test_full_pipeline.py` (DOCX→Alerts end-to-end)
- [ ] `test_cli_e2e.py` (comandos CLI)
- [ ] Performance tests (50k+ palabras)

#### Sesión 13: Workflows y Exporters (1.5 horas)
- [ ] `test_session_workflow.py` (crear proyecto, resolver alertas)
- [ ] `test_exporters.py` (character sheets, style guide)

#### Sesión 14: Edge Cases (1 hora)
- [ ] `test_edge_cases.py` (documentos grandes, corruptos, sin entidades)
- [ ] Multilingual tests
- [ ] Recovery tests

#### Sesión 15: Verificación Final (30 min)
- [ ] Todos los tests E2E pasan
- [ ] Coverage final: 90%+
- [ ] CI/CD pipeline configurado (GitHub Actions)
- [ ] Documentar en PROJECT_STATUS.md
- [ ] Commit: "feat: complete E2E test suite (90% coverage)"

**Total FASE 3**: 4-5 horas

---

## Resumen de Estimaciones

| Fase | Prioridad | Cobertura Objetivo | Tiempo | Tests Aprox. |
|------|-----------|-------------------|--------|--------------|
| FASE 1: Crítico | P0 | 70% | 6h | ~80 tests |
| FASE 2: Completo | P1 | 85% | 15-18h | ~250 tests |
| FASE 3: E2E | P2 | 90%+ | 4-5h | ~70 tests |
| **TOTAL** | | **90%+** | **25-29h** | **~400 tests** |

**Bloqueantes**:
- FASE 1 (P0) es **BLOQUEANTE** para producción
- FASE 2 (P1) recomendada para MVP estable
- FASE 3 (P2) opcional pero altamente recomendada

---

## Notas Importantes

### Thread Safety
- Usar pytest-xdist para tests paralelos cuando sea seguro
- Singletons ya implementan double-checked locking
- Cada test debe usar DB en memoria independiente

### Tests Lentos (NLP)
- Marcar con `@pytest.mark.slow`
- Cargan modelos spaCy/embeddings (~2-3 segundos)
- Ejecutar solo cuando se modifique NLP code

### Mocking
- NO mockear base de datos (usar :memory:)
- SÍ mockear filesystem para parsers
- SÍ mockear modelos NLP en tests rápidos

### Datos de Test
- Usar textos cortos (<100 palabras)
- Entidades ficticias ("TestEntity", "PersonaPrueba")
- Evitar datos reales de manuscritos

---

## Referencias

- pytest docs: https://docs.pytest.org/
- pytest-cov: https://pytest-cov.readthedocs.io/
- factory-boy: https://factoryboy.readthedocs.io/
- Configuración actual: `pyproject.toml` líneas 73-82

---

## Para otra instancia de Claude Code

**Si necesitas implementar tests:**

1. Leer este documento completo
2. Revisar `pyproject.toml` para configuración pytest
3. Empezar por tests de alerts (P0)
4. Usar fixtures de `conftest.py`
5. Objetivo mínimo: 70% coverage global

**Comando para verificar progreso:**
```bash
pytest --cov=src/narrative_assistant --cov-report=term-missing
```
