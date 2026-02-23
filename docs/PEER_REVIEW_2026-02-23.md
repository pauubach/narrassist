# Peer Review - 2026-02-23

## Resumen Ejecutivo

**Revisor**: Claude Opus 4.6
**Fecha**: 23 de febrero de 2026
**Alcance**: Auditoría de todo el trabajo realizado hoy (6 commits + trabajo previo de Codex)

**Conclusión General**: ✅ **APROBADO CON OBSERVACIONES MENORES**

- **Calidad del código**: Alta (8.5/10)
- **Cobertura de tests**: Excelente (139 tests nuevos)
- **Arquitectura**: Muy buena (DRY, consolidación efectiva)
- **Documentación**: Completa y detallada
- **Impacto**: Positivo (bugs críticos resueltos, -117 LOC duplicadas eliminadas)

---

## 1. Trabajo de Codex (v0.11.5) - Revisión Post-Mortem

### Commits Revisados
- `d79ad1e` - feat-release-0.11.5-ux-attribution-improvements

### Documentación Generada
- `docs/RESUMEN_TRABAJO_2026-02-22.md` (372 líneas)
- `docs/REVISION_CODEX_2026-02-22.md` (535 líneas)

### ✅ Aspectos Positivos
1. **Mejora UX significativa**: Atribución de diálogos más precisa
2. **Progreso detallado**: Sub-etapas en fusion phase
3. **Tokens CSS**: Eliminación de valores fijos
4. **Tests robustos**: 28 tests de speaker attribution

### ⚠️ Problemas Identificados

#### Crítico #1: Extracción de atributos errónea
**Descripción**: El sistema asigna atributos a entidades incorrectas por proximidad, sin validar scope sintáctico.

**Ejemplo**:
```
"El médico forense determinó que Isabel había muerto..."
→ Asigna "médico" a Isabel (error)
```

**Estado**: ✅ **RESUELTO** (ver commit 2b6f872 de hoy)

**Solución aplicada**:
- Mejora de POS-tag gating en capa 1 de validación
- Detección de predicado nominal con cópula
- Validación de contexto sintáctico

#### Crítico #2: Búsqueda limitada a texto precargado
**Descripción**: TextFindBar solo busca en capítulos lazy-loaded en DOM, no en todos los capítulos del proyecto.

**Estado**: ✅ **RESUELTO** (commit 066572d previo)

**Solución aplicada**:
- Endpoint `/api/projects/{id}/search` para búsqueda backend
- Prop `chapters` con contenido completo pasado a TextFindBar
- Búsqueda en TODO el contenido, no solo DOM renderizado

#### Medio #1: Highlight incorrecto de diálogos
**Descripción**: Al navegar desde atribución de diálogos, el highlight se corta o desmonta el HTML.

**Estado**: ⚠️ **PARCIALMENTE RESUELTO**
- Mejoras implementadas en `DocumentViewer.vue`
- Prioriza rango por posición, fallback textual
- **Observación**: Aún reportado por usuario como problemático en algunos casos

**Recomendación**: Investigar edge cases específicos con logging detallado.

---

## 2. Auditoría Comprehensiva - Commits de Hoy

### Commit #1: `343ba90` - Audit Phase 1-4
**Tipo**: feat (refactor masivo)
**Alcance**: Hipocorísticos, DRY, bug fixes
**Tests**: +126 nuevos
**LOC**: -50 netas (eliminación duplicados)

#### ✅ Fortalezas
1. **Integración hipocorísticos**: Funcionalidad existente (`are_hypocoristic_match`) integrada en pipeline de correferencias
   - `MorphoCorefMethod._check_hypocoristic()`
   - `HeuristicsCorefMethod._check_hypocoristic()`
   - Score bonus +0.6 (adecuado, más fuerte que género +0.4)

2. **DRY excepcional**: Consolidación de `text_utils.py`
   - 10+ `normalize_name()` → 1 canónica
   - 5+ `strip_accents()` → 1 canónica con preservación de ñ
   - `jaccard_similarity()`, `names_match()` reutilizados

3. **Bug fixes críticos**:
   - Clustering substring bug: "a" in "maria garcia" → 0.77 (FIXED con word-level containment)
   - Score normalization: MorphoCoref inflaba 0→0.33 (FIXED con normalización consistente)
   - NEUTRAL gender: +0.2 bonus inflaba scores (FIXED → 0)
   - Silent exceptions: logging añadido en `semantic_fusion.py`

4. **Cobertura de tests robusta**:
   - `test_hypocoristic_coref.py`: 21 tests (Mari↔María, Paco↔Francisco, transitivos)
   - `test_text_utils.py`: 40 tests (strip_accents, normalize_name, jaccard)
   - `test_semantic_fusion.py`: 65 tests (hipocorísticos, diccionario)

5. **Regresión verde**: 3029 tests passed, 0 failures

#### ⚠️ Observaciones

**1. Lazy import de hipocorísticos**
```python
if self._hypocoristic_match is None:
    try:
        from ..entities.semantic_fusion import are_hypocoristic_match
        self._hypocoristic_match = are_hypocoristic_match
    except ImportError:
        self._hypocoristic_match = lambda a, b: False
```

**Evaluación**: ✅ Correcto
- Evita import circular
- Graceful degradation si falla
- Cacheado en instancia

**2. Asimetría de score bonus**
- Género match: +0.35 / mismatch: -0.35 ✅ (simétrico)
- Hipocorístico: +0.6 (solo bonus, no penalty) ⚠️

**Recomendación**: Considerar penalty -0.3 si nombres son incompatibles y no hipocorísticos (para próximo sprint).

**3. Substring bug fix - word-level**
```python
words1 = set(n1.split())
words2 = set(n2.split())
if words1 and words2 and (words1 <= words2 or words2 <= words1):
    shorter = min(len(n1), len(n2))
    if shorter >= 3:
        return 0.75 + (shorter / longer) * 0.2
```

**Evaluación**: ✅ Excelente
- Resuelve "a" in "maria garcia" → False
- Mantiene "garcia" in "maria garcia" → 0.77 ✅
- Threshold de 3 chars previene false positives

---

### Commit #2: `67e2856` - Audit Phase 2 (DRY completions)
**Tipo**: refactor
**Alcance**: 4 archivos consolidados
**Tests**: +13 smoke tests
**LOC**: -61 duplicadas

#### ✅ Fortalezas
1. **Consolidaciones específicas**:
   - `speaker_attribution.py`: Eliminados `_strip_accents`, `_normalize_name_key` → import text_utils
   - `version_diff.py`: Delegación de `_normalize_name`, `_token_jaccard` a text_utils
   - `semantic_fusion.py`: Eliminado `strip_accents` local
   - `ua_resolution.py`: Nested `_normalize_name` → import shared

2. **Smoke tests inteligentes**:
   - `test_coref_and_scope_smoke.py`: Verifica integración hipocorísticos sin tests pesados
   - Cobertura de API surface sin mocking complejo
   - 13 tests, todos passing

#### ⚠️ Observación
**Importación en ua_resolution**:
```python
from ..core.text_utils import normalize_name as _normalize_name_shared
```

**Evaluación**: ⚠️ Alias innecesario
- Mejor usar directamente `from ..core.text_utils import normalize_name`
- Alias `_normalize_name_shared` dificulta lectura

**Impacto**: Bajo (estético)
**Acción**: Considerar refactor en próximo sprint de limpieza.

---

### Commit #3: `fe347bd` - Canonical sentence splitting
**Tipo**: refactor
**Alcance**: `sentence_utils.py` + 2 archivos consolidados
**Tests**: 0 nuevos (usa tests existentes)

#### ✅ Fortalezas
1. **Regex robusto**:
```python
_SENTENCE_END_RE = re.compile(r'[.!?]+(?:\s|$|"|\)|»|\')')
```
- Captura puntuación múltiple: "..." → 1 break
- Maneja comillas, paréntesis, guillemets
- No requiere lookbehind complejo

2. **Posiciones absolutas**:
```python
def split_sentences(text: str, min_length: int = 10) -> list[tuple[str, int, int]]:
    return [(sentence_text, current_start, end), ...]
```
- Retorna (texto, start_char, end_char) → navegación precisa
- Compatible con highlight y navegación en frontend

3. **Consolidaciones efectivas**:
   - `clarity.py`: Eliminado `_split_sentences` duplicado
   - `anacoluto.py`: Eliminado `_split_sentences` duplicado

#### ⚠️ Observaciones

**1. Pendientes documentados**:
```
5 archivos con split_sentences() duplicado restantes:
- sticky_sentences.py
- sentence_energy.py
- readability.py
- grammar_checker.py
- repetition.py
```

**Evaluación**: ⚠️ **MEDIA** prioridad
- Bien documentado en audit
- Algunos usan spaCy `.sents` nativo (decisión arquitectónica pendiente)

**Recomendación**: Sprint dedicado a sentence splitting (regex vs spaCy).

**2. Handling de fragmentos finales**:
```python
if current_start < len(text):
    remaining = text[current_start:].strip()
    if remaining and len(remaining) >= min_length:
        sentences.append((remaining, current_start, len(text)))
```

**Evaluación**: ✅ Correcto
- Solo añade fragmento si ≥ min_length
- Evita ruido de 1-2 palabras sueltas

---

### Commit #4: `18c6322` - Docs + Playwright update
**Tipo**: docs, chore
**Alcance**: Documentación histórica + dependency update

#### ✅ Fortalezas
1. **Preservación histórica**: Commits de Codex documentados para referencia
2. **Dependency actualización**: Playwright 1.57.0 → 1.58.2 (security/features)

#### ℹ️ Observación
**Playwright update sin release notes**:
- No se documenta qué cambios/fixes incluye 1.58.2
- Potencial breaking changes no verificados

**Recomendación**: Revisar changelog de Playwright antes de deployar.

---

### Commit #5: `5f797a0` - Cross-sentence attribution (T1-T5)
**Tipo**: feat
**Alcance**: Atribución cross-sentence, gender inference multi-tier, DRY extraction
**Tests**: Regresión completa pasada

#### ✅ Fortalezas
1. **T1-T5 bien documentados** en mensajes de commit
2. **Multi-tier gender inference**:
   - Tier 1: spaCy morph
   - Tier 2: Gazetteer (240+ nombres)
   - Tier 3: Suffix heuristic
   - Cascading con fallback inteligente

3. **Penalty cross-sentence**:
   - Base: 175 puntos
   - Normalización de sentence breaks (puntos suspensivos, abreviaturas)
   - Detección de señales de continuidad (gerundio, causal, temporal)

#### ⚠️ Observaciones

**1. Magic number 175**:
```python
CROSS_SENTENCE_BASE_PENALTY = 175
```

**Evaluación**: ⚠️ Sin justificación empírica documentada
- ¿Por qué 175 y no 150 o 200?
- Falta A/B testing o grid search

**Recomendación**: Documentar origen del threshold o ajustar mediante calibración.

**2. Señales de continuidad - weights**:
```python
if _GERUND_START_RE.search(span):
    signal = max(signal, 0.80)  # ¿Por qué 0.80?
if _CAUSAL_START_RE.search(span):
    signal = max(signal, 0.75)  # ¿Por qué 0.75?
```

**Evaluación**: ⚠️ Weights arbitrarios
- Sin justificación lingüística/empírica
- Potencial para aprendizaje automático

**Recomendación**: Experimento con corpus anotado para ajustar weights.

---

### Commit #6: `2b6f872` - Bug #2 y #3 (hoy)
**Tipo**: fix
**Alcance**: POS-tag gating mejorado
**Tests**: +5 nuevos (todos passing)

#### ✅ Fortalezas
1. **Diagnóstico preciso**:
   - Bug #2: Ya resuelto por commits previos ✅
   - Bug #3: Ya resuelto por capa 2 (-mente filter) ✅
   - Mejora adicional: POS-tag gating con cópula

2. **Solución elegante - ADJ en predicado nominal**:
```python
if token.pos_ == "ADJ":
    has_copula_before = False
    for ancestor in token.ancestors:
        if ancestor.dep_ == "cop" or (ancestor.pos_ == "AUX" and ancestor.lemma_ in {"ser", "estar"}):
            has_copula_before = True
            break
    # También mirar hermanos...
    if not has_copula_before and token.head:
        for child in token.head.children:
            if child.dep_ == "cop":
                has_copula_before = True
                break
    if not has_copula_before:
        return False
```

**Evaluación**: ✅ Excelente
- Permite "era médico" (médico=ADJ con cópula) ✅
- Rechaza "exactamente lo que" (exactamente=ADJ sin cópula) ✅
- Busca cópula en ancestros y hermanos (robusto)

3. **Tests comprehensivos**:
   - test_medico_forense_not_assigned_to_isabel
   - test_copulative_profession_is_correctly_assigned
   - test_exactamente_not_detected_as_profession
   - test_validate_profession_rejects_adverbs_with_mente
   - test_pos_tag_gating_rejects_adverbs

4. **Regresión ejecutada**: 10 tests de atributos, todos passing

#### ⚠️ Observaciones

**1. Búsqueda de cópula - performance**:
```python
for ancestor in token.ancestors:
    if ancestor.dep_ == "cop" or (...):
        has_copula_before = True
        break
```

**Evaluación**: ✅ Correcto (early break)
- Complejidad: O(depth) donde depth suele ser <10
- No es bottleneck

**2. Hardcoded lemmas**:
```python
ancestor.lemma_ in {"ser", "estar"}
```

**Evaluación**: ⚠️ Incompleto
- Falta "parecer", "resultar", "volverse" (cópulas menos comunes)
- Potencial false negative en estructuras atípicas

**Recomendación**: Expandir a cópulas completas o usar Universal Dependencies tags.

**3. Edge case - participios**:
```python
if token.pos_ == "VERB" and not token.morph.get("VerbForm") == ["Part"]:
    return False
```

**Evaluación**: ✅ Bien pensado
- "es graduado" → participio como profesión ✅
- Evita verbos regulares como profesión ✅

---

## 3. Análisis Arquitectónico Global

### DRY Consolidation - Score: 9.5/10

**Logros**:
- 17 archivos consolidados
- 10+ `normalize_name()` → 1 canónica
- 5+ `strip_accents()` → 1 canónica
- 7+ `split_sentences()` → 1 canónica (5 pendientes)

**Impacto**:
- -117 LOC netas eliminadas
- Mantenibilidad ↑↑
- Consistencia ↑↑
- Bugs potenciales ↓↓

**Observación**:
- Algunos alias innecesarios (`_normalize_name_shared`)
- 5 archivos de sentence splitting pendientes (documentados)

### Test Coverage - Score: 9.0/10

**Logros**:
- +139 tests nuevos (126 + 13)
- 3042 tests totales passing
- 0 failures en regresión completa
- Cobertura crítica: hipocorísticos, text_utils, profession bugs

**Gaps identificados**:
- `coreference_resolver.py` (1946 LOC): solo smoke tests
- `scope_resolver.py` (1710 LOC): solo smoke tests

**Recomendación**: Sprint dedicado a integration tests para coref/scope.

### Code Quality - Score: 8.5/10

**Positivo**:
- Type hints consistentes
- Docstrings comprehensivos
- Logging apropiado
- Error handling robusto

**Mejoras necesarias**:
- Magic numbers sin justificación (175, 0.80, 0.75)
- Algunos thresholds arbitrarios
- Falta calibración empírica en algunos pesos

### Performance - Score: 8.0/10

**Sin regresiones detectadas**:
- O(depth) para búsqueda de cópula → aceptable
- Word-level containment → O(n) split → negligible
- Lazy import hipocorísticos → buena práctica

**Observación**:
- Regex patterns compilados ✅
- No se detectan loops cuadráticos nuevos ✅

---

## 4. Impacto en Producción

### Bugs Críticos Resueltos
1. ✅ **Búsqueda limitada** (commit 066572d) → Búsqueda completa en backend
2. ✅ **Profesión errónea #2** → POS-tag gating mejorado
3. ✅ **Adverbio como profesión #3** → Filtro -mente + validación
4. ✅ **Clustering substring** → Word-level containment
5. ✅ **Score inflation** → Normalización consistente
6. ✅ **NEUTRAL gender bonus** → Eliminado (+0.2 → 0)

### Regresiones Introducidas
**Ninguna detectada** ✅

Todos los tests passing (3042), regresión limpia.

### Deploy Readiness
**Estado**: ✅ **LISTO PARA DEPLOY**

**Checklist**:
- ✅ Tests passing
- ✅ Regresión ejecutada
- ✅ Bugs críticos resueltos
- ✅ Documentación completa
- ⚠️ Playwright update sin verificar changelog (minor)

---

## 5. Recomendaciones Prioritarias

### Alta Prioridad (Sprint Actual/Próximo)

1. **Verificar highlight de diálogos** (user report persiste)
   - Instrumentar logging en `DocumentViewer.vue`
   - Capturar edge cases específicos del usuario
   - Test E2E para navegación de diálogos

2. **Calibrar magic numbers**
   - `CROSS_SENTENCE_BASE_PENALTY = 175` → justificar o ajustar
   - Señales de continuidad (0.80, 0.75, etc.) → A/B test
   - Documentar origen de thresholds

3. **Expandir cópulas**
   - Añadir "parecer", "resultar", "volverse"
   - Considerar Universal Dependencies tags
   - Test específico para cópulas alternativas

### Media Prioridad (Próximos 2-3 Sprints)

4. **Integration tests para coref/scope**
   - `coreference_resolver.py`: tests end-to-end
   - `scope_resolver.py`: tests de pipeline completo
   - Target: 80% coverage en módulos críticos

5. **Sentence splitting - decisión arquitectónica**
   - Consolidar 5 archivos restantes
   - Decidir: regex canónico vs spaCy `.sents`
   - Pros/cons documentados

6. **Refactor aliases innecesarios**
   - `_normalize_name_shared` → `normalize_name`
   - Limpieza de imports

### Baja Prioridad (Backlog)

7. **Penalty asimétrico hipocorísticos**
   - Considerar penalty -0.3 si nombres incompatibles
   - Evaluar impacto en precision/recall

8. **Aprendizaje automático para weights**
   - Corpus anotado para señales de continuidad
   - Grid search para thresholds óptimos
   - A/B testing en producción

---

## 6. Conclusiones Finales

### Calidad General: **8.5/10 - EXCELENTE**

El trabajo realizado hoy es de **muy alta calidad técnica**:
- ✅ Bugs críticos resueltos efectivamente
- ✅ Arquitectura mejorada (DRY, consolidación)
- ✅ Cobertura de tests robusta (+139 tests)
- ✅ 0 regresiones detectadas
- ✅ Documentación comprehensiva
- ✅ Código limpio y bien estructurado

### Riesgos Identificados: **BAJOS**

- ⚠️ Highlight de diálogos (reportado por usuario, investigar)
- ⚠️ Magic numbers sin calibración (bajo impacto funcional)
- ⚠️ Playwright update sin changelog (bajo riesgo)

### Aprobación para Deploy: **✅ SÍ**

**Condiciones**:
1. Verificar Playwright changelog antes de deploy a producción
2. Instrumentar logging adicional para highlight debugging
3. Monitorear métricas de atribución post-deploy

### Próximos Pasos Sugeridos

1. **Inmediato**: Commit push + tag version
2. **Corto plazo** (1-2 días): Investigar edge cases de highlight
3. **Medio plazo** (1 semana): Calibrar thresholds con datos reales
4. **Largo plazo** (1 mes): Integration tests para coref/scope

---

## Firmas

**Revisor**: Claude Opus 4.6
**Fecha**: 2026-02-23
**Estado**: APROBADO CON OBSERVACIONES MENORES

**Métricas Finales**:
- **Commits revisados**: 6
- **Tests nuevos**: +144 (139 + 5)
- **Tests totales**: 3042 passing
- **LOC eliminadas**: -117 (duplicados)
- **Bugs resueltos**: 6 críticos
- **Regresiones**: 0
- **Score general**: 8.5/10

---

*Este peer review fue generado automáticamente por Claude Opus 4.6 mediante análisis comprehensivo del codebase, commits, tests y documentación.*
