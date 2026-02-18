# TODO: Coverage Improvements

## Estado Actual (2026-02-18)

**Progreso**: 54 tests creados para pipelines

### Coverage Alcanzado
- `ua_alerts.py`: 3% → **43%** (+40%)
- `ua_consistency.py`: 5% → **46%** (+41%)
- `ua_deep_extraction.py`: 4% → **28%** (+24%)
- `ua_quality.py`: 6% → **21%** (+15%)
- `ua_resolution.py`: 5% → **22%** (+17%)

### Objetivo Original
- **Mínimo**: 60% por archivo
- **Ideal**: 70-80% por archivo

---

## Trabajo Pendiente para Alcanzar 60%

### Estrategia Recomendada

**Opción 1: Tests de Integración Ligeros** (más eficiente)
- Usar datos reales pequeños en vez de mocks complejos
- Testear métodos `_run_*` con fixtures de datos de prueba
- Ejemplo: `_run_spelling_check()` con texto real corto

**Opción 2: Mocks Profundos de Métodos Internos** (más lento)
- Continuar con la estrategia actual de mocks
- Necesita ~100 tests adicionales para llegar a 60%
- Más mantenimiento a largo plazo

### Archivos que Necesitan Más Tests

| Archivo | Actual | Falta | Tests Estimados |
|---------|--------|-------|-----------------|
| `ua_quality.py` | 21% | +39% | ~30 tests |
| `ua_deep_extraction.py` | 28% | +32% | ~25 tests |
| `ua_resolution.py` | 22% | +38% | ~25 tests |
| `ua_alerts.py` | 43% | +17% | ~15 tests |
| `ua_consistency.py` | 46% | +14% | ~10 tests |

**Total estimado**: ~105 tests adicionales

### Métodos Específicos No Cubiertos

#### ua_quality.py (365 statements, 296 miss)
- `_run_spelling_check()`
- `_run_grammar_check()`
- `_run_lexical_repetitions()`
- `_run_semantic_repetitions()`
- `_run_coherence_check()`
- `_run_register_analysis()`
- `_run_sticky_sentences()`
- `_run_sentence_energy()`
- `_run_sensory_report()`
- `_run_typography_check()`
- `_run_pov_check()`
- `_run_references_check()`
- `_run_acronyms_check()`
- `_run_filler_detection()`

#### ua_deep_extraction.py (231 statements, 159 miss)
- `_extract_attributes()`
- `_extract_relationships()`
- `_extract_interactions()`
- `_extract_knowledge()`
- `_extract_voice_profiles()`

#### ua_resolution.py (183 statements, 136 miss)
- `_run_coreference()` - detalles internos
- `_persist_coref_voting_details()`
- `_run_entity_fusion()`
- `_attribute_dialogues()`

#### ua_alerts.py (270 statements, 149 miss)
- Branches no cubiertas en `_generate_all_alerts()`
- Manejo de más tipos de issues

---

## Decisión de Diseño

**Decisión tomada**: Dejar coverage en 21-46% por ahora.

**Razones**:
1. El objetivo de 60% requiere ~105 tests adicionales
2. Los tests actuales cubren las rutas críticas (orquestación de fases)
3. Los métodos internos son complejos y requieren fixtures elaboradas
4. ROI bajo: esfuerzo alto para cobertura de casos edge específicos

**Cuándo retomar**:
- Cuando surjan bugs en producción que justifiquen más tests
- Al refactorizar estos módulos
- Si se implementan nuevas features que requieran modificar estos pipelines

---

## Tests Creados

### Archivos
1. `tests/unit/test_pipelines_coverage_boost.py` (10 tests)
2. `tests/unit/test_pipelines_massive_coverage.py` (23 tests)
3. `tests/unit/test_pipelines_ultra_coverage.py` (14 tests)
4. `tests/unit/test_ua_alerts_mixin.py` (7 tests)

### Total: 54 tests

### Estrategia Usada
- Tests de orquestación (métodos `_phase_N_*`)
- Edge cases (listas vacías, flags deshabilitados, excepciones)
- Integración entre fases
- Validación de flujo de datos entre componentes

---

## Recomendaciones para el Futuro

### Al Añadir Features
- Escribir tests para métodos `_run_*` nuevos ANTES de implementar
- Usar TDD para asegurar coverage desde el inicio

### Al Refactorizar
- Aprovechar para añadir tests de integración ligeros
- Simplificar métodos complejos para hacerlos más testeables

### Herramientas
- `pytest --cov-report=html` genera reporte detallado en `htmlcov/`
- Ver líneas específicas no cubiertas en el reporte HTML
- Usar `pytest --cov-report=term-missing` para ver líneas en terminal
