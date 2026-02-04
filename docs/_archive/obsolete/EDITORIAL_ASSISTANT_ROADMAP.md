# Roadmap: Narrative Assistant como Asistente Editorial Completo

## Resumen Ejecutivo

Este documento consolida el análisis de 4 perspectivas especializadas (lingüista, experto IA/NLP, arquitecto de software, experto UX) para transformar Narrative Assistant de un "detector de inconsistencias narrativas" a un **asistente editorial completo**.

---

## 1. Clasificación de Correcciones por Dificultad

### Matriz de Viabilidad vs Impacto

```
                    IMPACTO ALTO
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    │  PRIORIDAD ALTA    │   PRIORIDAD MÁXIMA │
    │  (Invertir)        │   (Hacer YA)       │
    │                    │                    │
    │  • Claridad/Estilo │   • Tipografía     │
    │  • Puntuación      │   • Repeticiones   │
    │  • Vocab. Regional │   • Concordancia   │
    │                    │   • Terminología   │
DIFÍCIL ─────────────────┼───────────────────── FÁCIL
    │                    │                    │
    │  PRIORIDAD BAJA    │   QUICK WINS       │
    │  (Evaluar)         │   (Implementar)    │
    │                    │                    │
    │  • Inconsistencias │   • (ya cubierto)  │
    │    factuales       │                    │
    │    complejas       │                    │
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
                    IMPACTO BAJO
```

---

## 2. Clasificación Detallada por Tipo de Corrección

### NIVEL 1: Trivial (1-2 días)

| Tipo | Técnica | Precisión | Recursos | Dependencias |
|------|---------|-----------|----------|--------------|
| **Tipografía (guiones)** | Regex | 95% | CPU mínimo | Ninguna |
| **Tipografía (comillas)** | Regex | 90% | CPU mínimo | Ninguna |
| **Puntos suspensivos** | Regex | 98% | CPU mínimo | Ninguna |
| **Espaciado tipográfico** | Regex | 85% | CPU mínimo | Ninguna |

**Código ejemplo - Guiones:**
```python
# Detectar guion corto donde debería ser raya
dialogue_pattern = r'^(\s*)([-–])(\s)'  # Inicio de línea con guion
# Sugerencia: reemplazar por '—'
```

---

### NIVEL 2: Fácil (3-5 días)

| Tipo | Técnica | Precisión | Recursos | Dependencias |
|------|---------|-----------|----------|--------------|
| **Repeticiones léxicas** | spaCy + ventana deslizante | 75% | CPU | spaCy (ya instalado) |
| **Concordancia género/número** | spaCy morfología | 80% | CPU | spaCy (ya instalado) |
| **Números inconsistentes** | Regex + reglas | 85% | CPU mínimo | Ninguna |
| **Mayúsculas inconsistentes** | Regex + diccionario | 80% | CPU mínimo | Diccionario de nombres |

**Código ejemplo - Repeticiones:**
```python
def detect_repetitions(doc, window=50, min_length=4):
    IGNORE = {"ser", "estar", "haber", "tener", "hacer", "decir", ...}
    issues = []
    content_tokens = [(i, t) for i, t in enumerate(doc)
                      if t.pos_ in ("NOUN", "VERB", "ADJ")
                      and len(t.text) >= min_length
                      and t.lemma_.lower() not in IGNORE]

    for i, (idx, token) in enumerate(content_tokens):
        for j in range(i+1, len(content_tokens)):
            other_idx, other = content_tokens[j]
            if other_idx - idx > window:
                break
            if other.lemma_.lower() == token.lemma_.lower():
                issues.append({"word": token.text, "positions": [idx, other_idx]})
    return issues
```

---

### NIVEL 3: Moderado (1-2 semanas)

| Tipo | Técnica | Precisión | Recursos | Dependencias |
|------|---------|-----------|----------|--------------|
| **Terminología inconsistente** | Embeddings + clustering | 70% | GPU recomendada | sentence-transformers (ya instalado) |
| **Vocabulario regional** | Diccionarios + lookup | 80% | CPU mínimo | **Diccionarios a compilar** |
| **Dequeísmo/Queísmo** | spaCy + reglas | 75% | CPU | Reglas gramaticales |
| **Leísmo/Laísmo** | spaCy + reglas | 70% | CPU | Diccionario de verbos |

**Dependencias a crear:**
```
~/.narrative_assistant/dictionaries/
├── regional/
│   ├── es_ES.json      # ~500 términos peninsulares
│   ├── es_MX.json      # ~500 términos mexicanos
│   └── catalanismos.json
├── grammar/
│   └── verbos_transitivos.json  # Para leísmo/laísmo
└── terminology/
    └── glosario_proyecto.json   # Por proyecto
```

---

### NIVEL 4: Difícil (2-4 semanas)

| Tipo | Técnica | Precisión | Recursos | Dependencias |
|------|---------|-----------|----------|--------------|
| **Puntuación completa** | Reglas + spaCy + LLM | 65% | CPU/GPU | Corpus de reglas RAE |
| **Claridad/Estilo** | Heurísticas sintácticas | 50% | CPU | Calibración por género |
| **Oraciones largas** | spaCy árbol sintáctico | 70% | CPU | Umbrales configurables |

**Desafíos:**
- Muchas excepciones estilísticas
- Depende del género literario
- Alto riesgo de falsos positivos

---

### NIVEL 5: Muy Difícil (1-3 meses)

| Tipo | Técnica | Precisión | Recursos | Dependencias |
|------|---------|-----------|----------|--------------|
| **Inconsistencias factuales** | NLI + LLM | 50% | GPU obligatoria | Modelo NLI fine-tuned |
| **Contradicciones semánticas** | Embeddings + LLM | 45% | GPU obligatoria | Integración compleja |

**Por qué es difícil:**
- Requiere comprensión semántica profunda
- Contexto puede cambiar significado
- Necesita razonamiento sobre conocimiento implícito
- Alto coste computacional

---

## 3. Plan de Implementación por Fases

### FASE 1: Quick Wins (Semana 1-2)
**Objetivo:** Valor visible inmediato con mínimo esfuerzo

| Tarea | Días | Prioridad |
|-------|------|-----------|
| Detector de tipografía (guiones, comillas, espaciado) | 2 | P0 |
| Detector de repeticiones léxicas | 3 | P0 |
| Detector de concordancia básica | 3 | P0 |
| UI: Nueva categoría "Formato" en AlertsTab | 2 | P0 |

**Entregable:** 3 nuevos tipos de corrección funcionando

---

### FASE 2: Core Value (Semana 3-6)
**Objetivo:** Funcionalidades diferenciadoras

| Tarea | Días | Prioridad |
|-------|------|-----------|
| Detector de terminología inconsistente | 5 | P1 |
| Sistema de diccionarios regionales | 5 | P1 |
| Compilar diccionario es_ES (500 términos) | 3 | P1 |
| API endpoints para configuración | 3 | P1 |
| UI: Panel de configuración de detección | 4 | P1 |
| UI: Modo corrección secuencial | 5 | P2 |

**Entregable:** Terminología + Vocabulario regional funcionando

---

### FASE 3: Profesional (Semana 7-12)
**Objetivo:** Herramienta completa para correctores

| Tarea | Días | Prioridad |
|-------|------|-----------|
| Detector de puntuación (reglas básicas) | 7 | P2 |
| Detector de claridad (oraciones largas) | 5 | P2 |
| Detector leísmo/laísmo/dequeísmo | 7 | P2 |
| Sistema de plugins para detectores | 5 | P3 |
| Exportación mejorada (Word con Track Changes) | 5 | P2 |
| Mapa de densidad de errores | 3 | P3 |

**Entregable:** Suite completa de corrección editorial

---

### FASE 4: Avanzado (Futuro)
**Objetivo:** Diferenciación con IA avanzada

| Tarea | Semanas | Prioridad |
|-------|---------|-----------|
| Inconsistencias factuales con LLM | 4-6 | P4 |
| Fine-tuning modelo NLI español | 4-8 | P4 |
| Sugerencias de estilo con LLM | 2-4 | P4 |

---

## 4. Arquitectura Propuesta

### Nuevos Módulos

```
src/narrative_assistant/
    corrections/                    # NUEVO PAQUETE
        __init__.py
        config.py                   # CorrectionConfig dataclass
        types.py                    # Enums de tipos de issues
        base.py                     # BaseDetector ABC
        orchestrator.py             # Ejecuta detectores en paralelo

        detectors/
            typography.py           # Guiones, comillas, espaciado
            repetition.py           # Repeticiones léxicas
            agreement.py            # Concordancia género/número
            terminology.py          # Terminología inconsistente
            regional.py             # Vocabulario regional
            punctuation.py          # Puntuación
            clarity.py              # Claridad/estilo

        dictionaries/
            regional/
                es_ES.json
                es_MX.json
```

### Modelo de Datos

```python
@dataclass
class CorrectionIssue:
    """Issue de corrección detectado."""
    category: str           # "typography", "repetition", etc.
    issue_type: str         # Tipo específico
    start_char: int
    end_char: int
    text: str               # Texto problemático
    suggestion: Optional[str]
    explanation: str
    confidence: float
    rule_id: Optional[str]
```

### Integración con Sistema Existente

Las correcciones se convierten en `Alert` y se almacenan en `AlertRepository`:

```python
# En orchestrator.py
def corrections_to_alerts(issues: list[CorrectionIssue]) -> list[Alert]:
    return [
        Alert(
            category=AlertCategory(issue.category),
            severity=compute_severity(issue),
            message=issue.explanation,
            suggestion=issue.suggestion,
            # ...
        )
        for issue in issues
    ]
```

---

## 5. UX: Cambios en la Interfaz

### 5.1 Macro-Categorías de Alertas

```
┌─────────────────────────────────────────────────────────────┐
│  [Narrativa]    [Lenguaje]    [Formato]                     │
│                  (activo)                                    │
├─────────────────────────────────────────────────────────────┤
│  ○ Gramática          ○ Estilo/Claridad                     │
│  ● Repeticiones       ○ Vocabulario regional                │
│  ○ Terminología       ○ Puntuación                          │
└─────────────────────────────────────────────────────────────┘
```

**Narrativa:** Atributos, Timeline, Relaciones, Ubicación, Comportamiento
**Lenguaje:** Gramática, Estilo, Repeticiones, Terminología, Regional
**Formato:** Tipografía, Puntuación, Estructura

### 5.2 Modo Corrección Secuencial

```
┌─ Panel Alerta ──────────┬─ Documento ────────────────────────┐
│                         │                                     │
│  Repetición detectada   │  ...el libro era un libro muy     │
│  ────────────────────   │  interesante. El libro trataba... │
│                         │       ^^^^         ^^^^            │
│  "libro" aparece 3      │                                     │
│  veces en 20 palabras   │                                     │
│                         │                                     │
│  Sugerencias:           │                                     │
│  • obra                 │                                     │
│  • volumen              │                                     │
│  • texto                │                                     │
│                         │                                     │
│  [Ignorar] [Siguiente]  │                                     │
│                         │                                     │
│  ─────────────────────  │                                     │
│  Alerta 12 de 47        │                                     │
└─────────────────────────┴─────────────────────────────────────┘
```

### 5.3 Configuración de Detección

```
┌─ Configuración de Detección ────────────────────────────────┐
│                                                              │
│  Perfil: [Novela literaria ▼]                               │
│                                                              │
│  ┌─ LENGUAJE ──────────────────────────────────────────┐    │
│  │  [✓] Repeticiones     Sensibilidad: [====|---] 70%  │    │
│  │  [✓] Vocabulario      Variante: [España ▼]          │    │
│  │  [ ] Puntuación       (muchos falsos positivos)     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─ FORMATO ───────────────────────────────────────────┐    │
│  │  [✓] Tipografía       Comillas: [Angulares ▼]       │    │
│  │                       Diálogos: [Raya (—) ▼]        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [Guardar] [Restaurar defaults]                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Estimación de Esfuerzo Total

| Fase | Duración | Funcionalidades |
|------|----------|-----------------|
| Fase 1 | 2 semanas | Tipografía, Repeticiones, Concordancia |
| Fase 2 | 4 semanas | Terminología, Vocabulario regional, Config UI |
| Fase 3 | 6 semanas | Puntuación, Claridad, Leísmo, Plugins, Export |
| Fase 4 | 8+ semanas | Inconsistencias factuales con LLM |

**Total mínimo viable (Fases 1-2):** 6 semanas
**Total completo (Fases 1-3):** 12 semanas
**Con IA avanzada (Fases 1-4):** 20+ semanas

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Falsos positivos en puntuación | Alta | Medio | Configuración de sensibilidad, botón "Ignorar tipo" |
| Diccionarios regionales incompletos | Media | Alto | Empezar con 100 términos, ampliar con uso |
| Rendimiento en documentos largos | Media | Alto | Procesamiento por chunks, cache |
| LLM lento para inconsistencias | Alta | Medio | Solo activar con GPU, hacer opcional |

---

## 8. Métricas de Éxito

| Métrica | Objetivo Fase 1 | Objetivo Fase 3 |
|---------|-----------------|-----------------|
| Tipos de corrección | 3 nuevos | 8 nuevos |
| Precisión tipografía | >90% | >95% |
| Precisión repeticiones | >70% | >80% |
| Tiempo análisis 100 págs | <30s | <60s |
| Falsos positivos/página | <5 | <3 |

---

## 9. Conclusión

Narrative Assistant puede evolucionar de un detector de inconsistencias narrativas a un **asistente editorial completo** siguiendo este roadmap incremental:

1. **Fase 1 (2 semanas):** Implementar tipografía, repeticiones y concordancia. Alto impacto, bajo esfuerzo.

2. **Fase 2 (4 semanas):** Añadir terminología inconsistente y vocabulario regional. Diferenciación real.

3. **Fase 3 (6 semanas):** Completar con puntuación y claridad. Herramienta profesional.

4. **Fase 4 (futuro):** Inconsistencias factuales con LLM. Innovación.

La clave es **no intentar todo a la vez**. Empezar con los quick wins (tipografía, repeticiones) genera valor inmediato y permite iterar basándose en feedback real de correctores profesionales.

---

## Apéndice: Código de Referencia

Ver los análisis completos de cada agente en:
- Lingüista: Priorización por valor editorial
- Experto NLP: Viabilidad técnica detallada
- Arquitecto: Diseño de módulos y APIs
- Experto UX: Diseño de interfaz

*Documento generado por análisis multi-agente - Enero 2026*

---

## 10. Estado de Implementación (Actualizado Enero 2026)

### Detectores Implementados ✅

| Detector | Estado | Ubicación |
|----------|--------|-----------|
| **Tipografía** | ✅ Completo | `detectors/typography.py` |
| **Repeticiones léxicas** | ✅ Completo | `detectors/repetition.py` |
| **Concordancia** | ✅ Completo | `detectors/agreement.py` |
| **Terminología inconsistente** | ✅ Completo | `detectors/terminology.py` |
| **Vocabulario regional** | ✅ Completo | `detectors/regional.py` |
| **Terminología de campo** | ✅ Completo | `detectors/field_terminology.py` |
| **Claridad/Estilo** | ✅ Completo | `detectors/clarity.py` |
| **Gramática (leísmo, dequeísmo)** | ✅ Completo | `detectors/grammar.py` |
| **Anglicismos** | ✅ Completo | `detectors/anglicisms.py` |
| **Muletillas del autor** | ✅ Completo | `detectors/crutch_words.py` |

### Funcionalidades de UI ✅

| Funcionalidad | Estado | Ubicación |
|---------------|--------|-----------|
| Modo corrección secuencial | ✅ Completo | `SequentialCorrectionMode.vue` |
| Panel de configuración | ✅ Completo | `CorrectionConfigPanel.vue` |
| Mapa de densidad de errores | ✅ Completo | `ResumenTab.vue` (sección Diagnóstico) |
| Tendencia de errores | ✅ Completo | `ResumenTab.vue` |

### Exportación ✅

| Funcionalidad | Estado | Ubicación |
|---------------|--------|-----------|
| Informe DOCX/PDF | ✅ Completo | `exporters/document_exporter.py` |
| Guía de estilo | ✅ Completo | `exporters/style_guide.py` |
| **Word con Track Changes** | ✅ Completo | `exporters/corrected_document_exporter.py` |

### Glosario ✅

| Funcionalidad | Estado | Ubicación |
|---------------|--------|-----------|
| **Modelo de datos** | ✅ Completo | `persistence/glossary.py` |
| **Detector de glosario** | ✅ Completo | `detectors/glossary.py` |
| **API CRUD** | ✅ Completo | `api-server/main.py` |
| **UI de gestión** | ✅ Completo | `GlossaryTab.vue` |
| **Contexto para LLM** | ✅ Completo | `generate_llm_context()` |
| **Export publicación** | ✅ Completo | `export_for_publication()` |

### Pendiente 🔜

| Funcionalidad | Prioridad | Notas |
|---------------|-----------|-------|
| Detector de anacolutos | P3 | Requiere LLM |
| Detector de cambios de POV | P3 | Análisis narrativo avanzado |
| Templates de glosario por género | P3 | Ciencia ficción, histórica, etc. |
| Inconsistencias factuales con LLM | P4 | Fase 4 del roadmap |

---

## 11. Arquitectura Final

```
src/narrative_assistant/corrections/
├── __init__.py
├── base.py                  # BaseDetector ABC, CorrectionIssue
├── config.py                # Configuración de todos los detectores
├── orchestrator.py          # Ejecuta detectores en paralelo
├── types.py                 # Enums de categorías y tipos
│
├── detectors/
│   ├── __init__.py
│   ├── typography.py        # Guiones, comillas, espaciado
│   ├── repetition.py        # Repeticiones léxicas
│   ├── agreement.py         # Concordancia género/número
│   ├── terminology.py       # Terminología inconsistente
│   ├── regional.py          # Vocabulario regional
│   ├── field_terminology.py # Terminología de campo
│   ├── clarity.py           # Claridad/estilo
│   ├── grammar.py           # Leísmo, dequeísmo, etc.
│   ├── anglicisms.py        # Anglicismos innecesarios
│   ├── crutch_words.py      # Muletillas del autor
│   └── glossary.py          # Términos del glosario del proyecto
│
└── dictionaries/            # Diccionarios de datos
    └── regional/
        ├── es_ES.json
        └── es_MX.json

src/narrative_assistant/exporters/
├── document_exporter.py           # Informe completo DOCX/PDF
├── corrected_document_exporter.py # Word con Track Changes
├── character_sheets.py            # Fichas de personajes
└── style_guide.py                 # Guía de estilo
```

---

## 12. Decisiones de Diseño

### Sin Sistema de Plugins

Tras análisis con 4 agentes especializados, se decidió **NO implementar** un sistema de plugins:

1. **Razón principal**: El mercado es pequeño, los usuarios no son técnicos
2. **Alternativa**: Feature flags configurables por proyecto
3. **Beneficio**: Menor complejidad, testing centralizado, UX más simple

### Modelo de Tiers (futuro)

Para monetización, se recomienda modelo de tiers sin plugins:

- **Tier Básico**: Tipografía, repeticiones, concordancia, anglicismos
- **Tier Profesional**: Gramática avanzada, muletillas, claridad, export Word
- **Tier Enterprise**: Análisis LLM, inconsistencias factuales

### Densidad en ResumenTab

Se integró el mapa de densidad en el tab "Resumen" existente (opción híbrida), evitando crear un nuevo tab "Diagnóstico" que fragmentaría la UI.

*Última actualización: Enero 2026*
