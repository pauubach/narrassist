# Plan de Detección de Errores Estructurales

> **Fecha**: 4 Febrero 2026
> **Contexto**: Auditoría de capacidades de detección y plan de mejoras
> **Metodología**: 8 expertos (3 paneles) + análisis de cobertura de tests

---

## Resumen Ejecutivo

Tras analizar el documento de test `test_document_rich.txt` y consultar con el panel completo de 8 expertos, se identificaron:

- **9 tipos de errores** en el documento de test
- **6 detectados** por el sistema actual
- **3 no detectados** (prolepsis, duplicados a nivel frase, diálogos huérfanos)
- **38 archivos de test** existentes (~90% cobertura)
- **5 gaps críticos** en tests para MVP

---

## 1. Documento de Test Enriquecido

**Archivo**: `test_books/test_document_rich.txt`

### Errores Incluidos

| # | Tipo de Error | Ubicación | Descripción | Detectado? |
|---|---------------|-----------|-------------|------------|
| 1 | **Ortográficos** | Cap 1,2,3,4,5 | "tenia", "noto", "despues", "amava", "Habrió", "Traia", "habia", "sostubo", "dejo" | ✅ AlertsTab |
| 2 | **Atributo inconsistente** | Cap 1→2 | Ojos de Carmen: grises → verdes → azules | ✅ AlertsTab |
| 3 | **Personaje post-mortem** | Cap 4→5 | Carmen muere en cap 4, aparece en cap 5 | ✅ VitalStatusTab |
| 4 | **Párrafos fragmentados** | Cap 3 | "Pedro llegó. / Azotó la puerta. / Su cara estaba roja." | ⚠️ Parcial |
| 5 | **Oración muy larga** | Cap 1 | 80+ palabras sobre la alfombra persa | ✅ StyleTab |
| 6 | **Prolepsis fuera de lugar** | Cap 2 | Mención de ceremonia (ocurre en cap 5) | ❌ No detecta |
| 7 | **Contenido duplicado** | Cap 1 ↔ 5 | "La casa olía a humedad y memorias..." | ⚠️ Solo palabras |
| 8 | **Diálogos sin atribución** | Cap 4 | "—Tienes razón. / —¿Crees que...?" | ⚠️ Solo atribución |
| 9 | **Punto y seguido incorrecto** | Cap 1 | Mezcla tema casa + recuerdos Pedro | ❌ No detecta |

### Correcciones Realizadas Hoy

| Fix | Archivo | Descripción |
|-----|---------|-------------|
| FIN como capítulo | `txt_parser.py` | Añadida lista `NOT_HEADING_WORDS` para excluir "FIN", "THE END", etc. |
| Título como capítulo | `structure_detector.py` | Mejorada heurística: priorizar headings con patrón "Capítulo N" |
| Ritmo error | `prose.py:736` | `analyzer.analyze(chapter_text)` → `[{number, title, content}]` |
| Salud Narrativa | `narrative_health.py` | Umbral adaptativo para documentos pequeños |
| Arquetipos | `relationships.py` | Conversión `entity_type` enum → string |
| Accesibilidad WCAG | `StickySentencesTab.vue` | Colores severity con ratio ≥4.5:1 |

---

## 2. Mapeo: Errores → Detección → UI

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE DETECCIÓN DE ERRORES                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ORTOGRAFÍA                                                             │
│  ├─ Módulo: orthography.VotingSpellingChecker                          │
│  ├─ Métodos: pyspellchecker + hunspell + LanguageTool + LLM            │
│  ├─ Categoría: GRAMMAR                                                  │
│  ├─ UI: AlertsTab                                                       │
│  └─ Test: test_orthography.py ✅                                        │
│                                                                         │
│  ATRIBUTOS INCONSISTENTES                                               │
│  ├─ Módulo: analysis.AttributeConsistencyChecker                       │
│  ├─ Métodos: Lematización + antónimos + embeddings                     │
│  ├─ Categoría: CONSISTENCY                                              │
│  ├─ UI: AlertsTab, EntitiesTab                                         │
│  └─ Test: test_consistency.py, test_attributes.py ✅                   │
│                                                                         │
│  PERSONAJE POST-MORTEM                                                  │
│  ├─ Módulo: analysis.VitalStatusAnalyzer                               │
│  ├─ Métodos: Patrones muerte + acciones post-mortem                    │
│  ├─ Categoría: CONSISTENCY                                              │
│  ├─ UI: VitalStatusTab                                                 │
│  └─ Test: test_vital_status.py ✅                                       │
│                                                                         │
│  ORACIONES LARGAS / READABILITY                                         │
│  ├─ Módulo: nlp.style.ReadabilityAnalyzer + EditorialRules             │
│  ├─ Métodos: Flesch-Szigriszt + conteo palabras                        │
│  ├─ Categoría: STYLE                                                    │
│  ├─ UI: StyleTab, AgeReadabilityTab                                    │
│  └─ Test: test_readability.py ✅                                        │
│                                                                         │
│  REPETICIONES                                                           │
│  ├─ Módulo: nlp.style.RepetitionDetector                               │
│  ├─ Métodos: N-gramas + similitud semántica                            │
│  ├─ Categoría: STYLE                                                    │
│  ├─ UI: EchoReportTab                                                  │
│  └─ Test: test_style.py ⚠️ (parcial, no cubre frases)                  │
│                                                                         │
│  PROLEPSIS/ANALEPSIS                                                    │
│  ├─ Módulo: analysis.NarrativeTemplateAnalyzer                         │
│  ├─ Métodos: Marcadores temporales + embeddings                        │
│  ├─ Categoría: NARRATIVE                                                │
│  ├─ UI: NarrativeTemplatesTab                                          │
│  └─ Test: test_narrative_templates.py ⚠️ (prolepsis marcado xfail)     │
│                                                                         │
│  DIÁLOGOS HUÉRFANOS                                                     │
│  ├─ Módulo: voice.SpeakerAttributor                                    │
│  ├─ Métodos: Extracción diálogo + resolución hablante                  │
│  ├─ Categoría: CLARITY                                                  │
│  ├─ UI: AlertsTab                                                       │
│  └─ Test: test_speaker_attribution.py ⚠️ (no valida contexto)          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Revisión del Panel de 8 Expertos

### Panel A: Lingüística + Editorial

| Experto | Assessment | Gap Crítico | Recomendación |
|---------|-----------|-------------|---------------|
| **Dra. Carmen Vidal** (NLP) | ⚠️ Warning | Prolepsis/analepsis incompleto | Crear `test_temporal_narrative_ordering.py` |
| **Miguel Á. Durán** (Editorial) | 🔴 Crítico | Duplicados, diálogos huérfanos, anachronismos | 5 nuevos módulos de test |
| **Prof. Elena Sánchez** (Narratóloga) | ⚠️ Warning | Función narrativa no validada | Tests de flashback con propósito |

### Panel B: Backend + Seguridad

| Experto | Assessment | Gap Crítico | Recomendación |
|---------|-----------|-------------|---------------|
| **Javier Ruiz** (Arquitecto) | ✅ OK | Tests de carga/performance | `tests/performance/` |
| **Ana Torres** (AppSec) | ✅ OK | SQL injection, integridad modelos | `tests/security/` |
| **David Chen** (QA) | ⚠️ Warning | Edge cases (encodings, extremos) | `tests/edge_cases/` |

### Panel C: Frontend + Producto

| Experto | Assessment | Gap Crítico | Recomendación |
|---------|-----------|-------------|---------------|
| **Tomás García** (UX) | ⚠️ Warning | Presentación alertas no validada | Tests de calidad UX |
| **Laura Martín** (PO) | 🔴 Crítico | **Prioridades desalineadas con MVP** | Rebalancear tests |

### Hallazgo Principal (Product Owner)

```
PRIORIDADES ACTUALES (por # tests)     PRIORIDADES USUARIO (por solicitud)
────────────────────────────────────   ────────────────────────────────────
1. Relaciones personajes               1. REPETICIONES (más solicitado)
2. Análisis temporal                   2. Flashbacks/prolepsis
3. Reconocimiento entidades            3. Contenido duplicado
4. Consistencia voz                    4. Diálogos huérfanos
```

---

## 4. Tests Faltantes para MVP

### Críticos (Semana 1-2)

| Test | Módulo | Prioridad | Esfuerzo |
|------|--------|-----------|----------|
| `test_repetition_analysis.py` | Detección de repeticiones semánticas | CRÍTICA | 40h |
| `test_duplicate_content.py` | Frases/párrafos duplicados | CRÍTICA | 30h |
| `test_orphaned_dialogue.py` | Diálogos sin contexto | ALTA | 25h |
| `test_narrative_structure.py` | Prolepsis/analepsis funcional | ALTA | 35h |

### Importantes (Semana 3-4)

| Test | Módulo | Prioridad | Esfuerzo |
|------|--------|-----------|----------|
| `test_sql_injection.py` | Seguridad SQL | ALTA | 20h |
| `test_file_security.py` | Validación archivos | ALTA | 25h |
| `test_edge_cases.py` | Extremos y encodings | MEDIA | 30h |

### Post-MVP (Semana 5+)

| Test | Módulo | Prioridad | Esfuerzo |
|------|--------|-----------|----------|
| `test_large_manuscript.py` | Performance 100K palabras | MEDIA | 35h |
| `test_concurrent_analysis.py` | Análisis paralelo | MEDIA | 25h |
| `test_alert_display_quality.py` | UX de alertas | MEDIA | 20h |

---

## 5. Plan de Implementación por Fases

### Fase 1: Repeticiones y Duplicados (Crítico - 2 semanas)

**Objetivo**: Detectar contenido repetido a nivel frase/párrafo

```python
# Nuevo módulo: src/narrative_assistant/analysis/duplicate_detector.py

class DuplicateContentDetector:
    """Detecta contenido duplicado a nivel frase y párrafo."""

    def detect_duplicate_sentences(
        self,
        text: str,
        threshold: float = 0.95  # Jaccard similarity
    ) -> list[DuplicateMatch]:
        """Detecta frases duplicadas exactas o casi-exactas."""

    def detect_duplicate_paragraphs(
        self,
        paragraphs: list[str],
        threshold: float = 0.85  # Semantic similarity
    ) -> list[DuplicateMatch]:
        """Detecta párrafos duplicados semánticamente."""
```

**Archivos a crear**:
- `src/narrative_assistant/analysis/duplicate_detector.py`
- `tests/unit/test_duplicate_content.py`
- `tests/integration/test_duplicate_workflow.py`

**Endpoint**:
- `POST /api/projects/{id}/duplicate-content`

### Fase 2: Estructura Narrativa (Alta - 2 semanas)

**Objetivo**: Detectar prolepsis/analepsis con función narrativa

```python
# Mejora: src/narrative_assistant/analysis/narrative_templates.py

class NarrativeStructureValidator:
    """Valida estructura narrativa incluyendo flashbacks."""

    def detect_prolepsis(
        self,
        events: list[TimelineEvent],
        chapters: list[Chapter]
    ) -> list[NarrativeAnomaly]:
        """Detecta prolepsis: eventos mencionados antes de ocurrir."""

    def validate_flashback_function(
        self,
        flashback: Flashback,
        context: NarrativeContext
    ) -> FlashbackAssessment:
        """Evalúa si el flashback tiene función narrativa válida."""
```

**Archivos a crear/modificar**:
- Mejorar `src/narrative_assistant/analysis/narrative_templates.py`
- `tests/unit/test_narrative_structure.py`

### Fase 3: Diálogos y Seguridad (Alta - 2 semanas)

**Objetivo**: Validar contexto de diálogos + seguridad básica

```python
# Nuevo módulo: src/narrative_assistant/nlp/dialogue_validator.py

class DialogueContextValidator:
    """Valida que los diálogos tengan contexto adecuado."""

    def detect_orphaned_dialogue(
        self,
        dialogue: Dialogue,
        surrounding_text: str
    ) -> list[DialogueIssue]:
        """Detecta diálogos sin configuración de escena."""
```

**Archivos a crear**:
- `src/narrative_assistant/nlp/dialogue_validator.py`
- `tests/unit/test_orphaned_dialogue.py`
- `tests/security/test_sql_injection.py`
- `tests/security/test_file_security.py`

### Fase 4: Edge Cases y Performance (Media - 2 semanas)

**Objetivo**: Robustez para casos extremos

**Archivos a crear**:
- `tests/edge_cases/test_document_extremes.py`
- `tests/edge_cases/test_encoding_variants.py`
- `tests/performance/test_large_manuscript.py`

---

## 6. Criterios de Aceptación

### Para cada nuevo detector:

- [ ] Unit test con ≥5 casos positivos y ≥3 negativos
- [ ] Integration test end-to-end
- [ ] Adversarial test con edge cases
- [ ] Endpoint API funcional
- [ ] Panel UI muestra resultados
- [ ] Documentación actualizada

### Para MVP:

- [ ] Todos los errores del `test_document_rich.txt` detectados
- [ ] Cero falsos positivos en errores obvios
- [ ] Tiempo de análisis < 30s para 50K palabras
- [ ] Tests pasan en CI/CD

---

## 7. Métricas de Éxito

| Métrica | Actual | Objetivo MVP | Objetivo v1.1 |
|---------|--------|--------------|---------------|
| Errores detectados en test_document_rich | 6/9 (67%) | 9/9 (100%) | 9/9 + warnings |
| Cobertura de tests | ~90% | 95% | 98% |
| Falsos positivos en corpus golden | N/A | < 5% | < 2% |
| Tiempo análisis 50K palabras | N/A | < 30s | < 15s |

---

## 8. Dependencias y Riesgos

### Dependencias:

1. **spaCy es_core_news_lg** - Ya instalado
2. **sentence-transformers** - Ya instalado
3. **Ollama** - Para análisis semántico profundo (opcional)

### Riesgos:

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Falsos positivos en duplicados | Media | Alto | Threshold configurable |
| Performance con docs grandes | Media | Medio | Procesamiento por chunks |
| Prolepsis mal interpretadas | Alta | Medio | Validación con LLM |

---

## 9. Cronograma Propuesto

```
Semana 1-2:  Fase 1 (Repeticiones/Duplicados) ████████████████████
Semana 3-4:  Fase 2 (Estructura Narrativa)    ████████████████████
Semana 5-6:  Fase 3 (Diálogos + Seguridad)    ████████████████████
Semana 7-8:  Fase 4 (Edge Cases + Perf)       ████████████████████
Semana 9:    QA final + Documentación         ██████████
```

**Esfuerzo total estimado**: ~355 horas / 9 semanas

---

*Documento generado: 4 Febrero 2026*
*Basado en: 8 expertos (3 paneles) + análisis de cobertura*

---

## 10. Estado de Implementación

> **Actualizado**: 4 Febrero 2026

### ✅ Fase 1-2: Duplicados + Prolepsis (COMPLETADA)

| Componente | Estado | Tests |
|------------|--------|-------|
| `duplicate_detector.py` | ✅ Implementado | 16 tests |
| `narrative_structure.py` | ✅ Implementado | 12 tests |
| Endpoint `/duplicate-content` | ✅ Funcional | - |
| Endpoint `/narrative-structure` | ✅ Funcional | - |
| UI: DuplicateContentTab | ✅ Creado | - |
| UI: ProlepisTab | ✅ Creado | - |

### ✅ Fase 3: Diálogos + Seguridad (COMPLETADA)

| Componente | Estado | Tests |
|------------|--------|-------|
| `dialogue_validator.py` | ✅ Implementado | 13 tests |
| Endpoint `/dialogue-validation` | ✅ Funcional | - |
| Tests SQL injection | ✅ Creados | 2 tests |
| Tests path traversal | ✅ Creados | 5 tests |
| Tests inputs malformados | ✅ Creados | 4 tests |
| Tests límites tamaño | ✅ Creados | 2 tests |
| Tests seguridad detectores | ✅ Creados | 5 tests |

### ✅ Fase 4: Edge Cases + Performance (COMPLETADA)

| Componente | Estado | Tests |
|------------|--------|-------|
| `test_document_extremes.py` | ✅ Creado | 25 tests |
| `test_encoding_variants.py` | ✅ Creado | 22 tests |
| `test_large_manuscript.py` | ✅ Creado | 9 tests |

### Resumen de Tests Nuevos

| Categoría | Archivo | Tests |
|-----------|---------|-------|
| Duplicados | `test_duplicate_detector.py` | 16 |
| Estructura | `test_narrative_structure.py` | 12 |
| Diálogos | `test_dialogue_validator.py` | 13 |
| Seguridad | `test_input_validation.py` | 18 |
| Edge Cases | `test_document_extremes.py` | 25 |
| Encodings | `test_encoding_variants.py` | 22 |
| Performance | `test_large_manuscript.py` | 9 |
| **TOTAL** | - | **115 tests** |

### 📋 Pendiente para Fases Futuras

1. **Redundancia Semántica** (documentado en PENDING_ISSUES.md):
   - Duplicados semánticos (mismo contenido, palabras diferentes)
   - Acciones repetidas de personajes
   - Insistencia temática excesiva

2. **UI de Validación de Diálogos**: ✅ INTEGRADO
   - ~~Crear DialogueValidationTab.vue~~
   - Decisión: Integrado en AlertsTab como categoría DIALOGUE
   - AlertEngine.create_from_dialogue_issue() añadido
   - Endpoint actualizado con create_alerts=True

3. **Issues Resueltos**:
   - ✅ #5: Relaciones sin datos - Corregido matching chapter_id y contexto relativo
   - ✅ #8: Timeline flashback incorrecto - Añadida validación de evidencia retrospectiva

4. **Issues en Backlog**:
   - #22: Glosario extracción automática (feature request, prioridad baja)
