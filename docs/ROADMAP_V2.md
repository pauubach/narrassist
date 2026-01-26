# Roadmap v2.0 - Narrative Assistant

> **Última actualización**: 2026-01-26
> **Versión tauri.conf.json**: 0.2.9

---

## Resumen del Estado Actual

### Completado ✅

| Área | Estado |
|------|--------|
| **Backend Core** | 103 archivos Python, ~49,000 LoC |
| **Frontend** | 53 componentes Vue, ~30,000 LoC |
| **API Server** | 48+ endpoints FastAPI |
| **Detectores Editoriales** | 14 detectores implementados |
| **Exportación** | DOCX, PDF, JSON, Track Changes, Review Reports |
| **Diccionario Local** | Wiktionary, sinónimos, custom (v0.2.9) |
| **Arco Emocional** | UI visual completa (v0.2.9) |
| **Sistema de Licencias** | Implementado |
| **Tauri Desktop** | Empaquetado listo (sidecar + instalador) |

### Detectores Actuales (14 total)

1. ✅ **Tipografía** - guiones, comillas, espaciado, secuencias, pares
2. ✅ **Repeticiones** - léxicas, inicio de oración, cacofonías
3. ✅ **Concordancia** - género/número
4. ✅ **Terminología** - inconsistencias terminológicas
5. ✅ **Regional** - vocabulario es_ES, es_MX, es_AR
6. ✅ **Campo** - terminología especializada
7. ✅ **Claridad** - oraciones largas, subordinadas
8. ✅ **Gramática** - leísmo, dequeísmo, queísmo
9. ✅ **Extranjerismos** - anglicismos + galicismos (v0.2.8)
10. ✅ **Muletillas** - sobreuso de palabras (z-score)
11. ✅ **Glosario** - términos del proyecto
12. ✅ **Anacolutos** - rupturas sintácticas (completo)
13. ✅ **POV** - cambios de punto de vista (completo)
14. ✅ **Variantes ortográficas** - grafías RAE (v0.2.8)

### Typography - Detecciones Completas (v0.2.8)

| Detección | Estado |
|-----------|--------|
| Comillas antes/después del punto según RAE | ✅ Implementado |
| Secuencias de puntuación inválidas (`,.` `!?` `??`) | ✅ Implementado |
| Pares de signos sin cerrar (`(texto` `«texto`) | ✅ Implementado |

### Anacolutos - Detecciones Completas (v0.2.8)

| Detección | Estado |
|-----------|--------|
| Nominativus pendens | ✅ |
| Broken construction | ✅ |
| Incomplete clause | ✅ |
| Subject shift | ✅ Implementado |
| Dangling modifier | ✅ |

### POV - Detecciones Completas (v0.2.8)

| Detección | Estado |
|-----------|--------|
| Person shift | ✅ (regex mejorados) |
| Tú/usted mix | ✅ |
| Focalizer shift | ✅ Implementado |
| Inconsistent omniscience | ✅ Implementado |

---

## Ideas Inspiradas en Stilus

> Fuentes: [Stilus](https://www.mystilus.com/en), [La Linterna del Traductor](https://lalinternadeltraductor.org/n7/stilus.html)

### P1 - Alta Prioridad

| Funcionalidad | Descripción | Complejidad | Estado |
|---------------|-------------|-------------|--------|
| **Expansión de gazetteer** | Ampliar de ~5,000 a 50,000+ nombres propios (personas, lugares, organizaciones) | Media | ❌ Pendiente |
| **Diccionario local** | Definiciones offline (Wiktionary/sinónimos) + links externos RAE/Moliner | Media | ✅ v0.2.9 |
| **Variantes ortográficas RAE** | Detectar cuando se usa variante no preferida (ej: "sicología" vs "psicología") | Fácil | ✅ v0.2.8 |
| **Informe de revisión detallado** | Generar informe PDF/DOCX con estadísticas de errores por categoría | Fácil | ✅ v0.2.9 |
| **Secuencias de puntuación inválidas** | Detectar ",." o "!?" mal usados | Fácil | ✅ v0.2.8 |

### P2 - Prioridad Media

| Funcionalidad | Descripción | Complejidad | Estado |
|---------------|-------------|-------------|--------|
| **Conjugador verbal integrado** | Herramienta para consultar conjugaciones sin salir de la app | Media | ❌ Pendiente |
| **Diccionario inverso** | Buscar palabras por terminación (útil para rimas, cacofonías) | Media | ❌ Pendiente |
| **Pares de signos** | Verificar apertura/cierre de comillas, paréntesis, corchetes | Fácil | ✅ v0.2.8 |
| **Explicaciones didácticas** | Añadir bibliografía RAE/Martínez de Sousa a cada corrección | Media | ❌ Pendiente |
| **Detección de galicismos** | Expandir detector de extranjerismos a francés, italiano | Media | ✅ v0.2.8 |

### P3 - Prioridad Baja

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Generador morfosintáctico** | Generar variantes de una palabra (plural, femenino, etc.) | Alta |
| **Lematizador expuesto en UI** | Herramienta para lematizar texto seleccionado | Fácil |
| **Modo "Macro" batch** | Aplicar correcciones automáticas sin confirmación (errores seguros) | Alta |

---

## Ideas Inspiradas en MeaningCloud

> Fuente: [Sngular - NLP con MeaningCloud](https://www.sngular.com/es/insights/201/insight-nlp-al-alcance-de-todos-meaningcloud)

### P1 - Alta Prioridad

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Resumen automático por capítulo** | Generar sinopsis de cada capítulo con LLM local | Media |
| **Clasificación temática IPTC** | Categorizar el manuscrito según taxonomía estándar | Media |
| **Extracción de temas principales** | Identificar temas dominantes del texto (clustering) | Media |

### P2 - Prioridad Media

| Funcionalidad | Descripción | Complejidad | Estado |
|---------------|-------------|-------------|--------|
| **UI Arco emocional** | Gráfico de arco emocional del libro + API endpoint | Fácil | ✅ v0.2.9 |
| **Ontología expandida (200+ clases)** | Clasificar entidades en subcategorías más precisas | Alta | ❌ Pendiente |
| **Detección de fechas y cantidades** | Extraer y normalizar fechas, números, monedas | Media | ❌ Pendiente |

### P3 - Prioridad Baja

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Diccionarios de dominio** | Integrar ontologías especializadas (médica, legal, etc.) | Alta |
| **Análisis de estructura documental** | Mejor detección de partes del libro (prólogo, epílogo, etc.) | Media |

---

## Funcionalidades Pendientes del Roadmap Original

### P1 - Backend sin UI adecuada

| Feature | Módulo Backend | UI Necesaria |
|---------|----------------|--------------|
| **Knowledge Tracking** | `character_knowledge.py` ✅ | Panel "Qué sabe cada personaje" |
| **Voice Profiles** | `voice/profiles.py` ✅ | Vista de perfiles de voz |
| **Register Analysis** | `voice/register.py` ✅ | Indicador de registro lingüístico |
| **Speaker Attribution** | `voice/speaker_attribution.py` ✅ | Atribución visual en diálogos |
| **Sentiment Analysis** | `nlp/sentiment.py` ✅ | ✅ EmotionalAnalysis.vue (v0.2.9) |
| **Emotional Coherence** | `emotional_coherence.py` ✅ | ✅ Arco emocional visual (v0.2.9) |
| **Interaction Patterns** | `interactions/` ✅ | Panel de patrones de interacción |

### P2 - Detectores Adicionales

| Detector | Descripción | Estado |
|----------|-------------|--------|
| **Anacolutos** | Oraciones con construcción sintáctica rota | ✅ Completo (v0.2.8) |
| **Cambios de POV** | Detectar cambios involuntarios de punto de vista | ✅ Completo (v0.2.8) |
| **Inconsistencias factuales** | Contradicciones en hechos narrados | ❌ Pendiente (requiere LLM) |

### P3 - Infraestructura

| Tarea | Descripción |
|-------|-------------|
| Code signing Windows | Certificado ~$300/año |
| Code signing macOS | Apple Developer $99/año |
| CI/CD Pipeline | GitHub Actions |
| i18n | Internacionalización (inglés, catalán) |
| Landing page | Sitio web de producto |

---

## Plan de Implementación Propuesto

### Fase 1: Quick Wins (2 semanas)

| # | Tarea | Tiempo | Origen | Estado |
|---|-------|--------|--------|--------|
| 1 | Secuencias de puntuación inválidas | 1d | Stilus | ✅ v0.2.8 |
| 2 | Pares de signos (comillas, paréntesis) | 1d | Stilus | ✅ v0.2.8 |
| 3 | Variantes ortográficas RAE | 2d | Stilus | ✅ v0.2.8 |
| 4 | Detección de galicismos | 1d | Stilus | ✅ v0.2.8 |
| 5 | Informe de revisión detallado | 2d | Stilus | ✅ v0.2.9 |
| 6 | UI para Knowledge Tracking | 3d | Pendiente | ❌ Pendiente |

### Fase 2: Valor Diferencial (4 semanas)

| # | Tarea | Tiempo | Origen | Estado |
|---|-------|--------|--------|--------|
| 6 | Resumen automático por capítulo | 5d | MeaningCloud | ❌ Pendiente |
| 7 | Arco emocional visual | 5d | MeaningCloud | ✅ v0.2.9 |
| 8 | Expansión gazetteer (+45,000 nombres) | 5d | Stilus | ❌ Pendiente |
| 9 | Diccionario local multi-fuente | 3d | Stilus | ✅ v0.2.9 |
| 10 | UI para Voice Profiles | 3d | Pendiente | ❌ Pendiente |

### Fase 3: Profesional (6 semanas)

| # | Tarea | Tiempo | Origen |
|---|-------|--------|--------|
| 11 | Clasificación temática IPTC | 5d | MeaningCloud |
| 12 | Clustering de temas | 5d | MeaningCloud |
| 13 | Conjugador verbal integrado | 3d | Stilus |
| 14 | Diccionario inverso | 3d | Stilus |
| 15 | Explicaciones con bibliografía | 5d | Stilus |
| 16 | UI para Speaker Attribution | 4d | Pendiente |
| 17 | UI para Interaction Patterns | 4d | Pendiente |

### Fase 4: IA Avanzada (8+ semanas)

| # | Tarea | Tiempo | Origen |
|---|-------|--------|--------|
| 18 | Detector de anacolutos | 2 sem | Roadmap v1 |
| 19 | Detector de cambios de POV | 2 sem | Roadmap v1 |
| 20 | Inconsistencias factuales con LLM | 4 sem | Roadmap v1 |
| 21 | Ontología expandida (200+ clases) | 3 sem | MeaningCloud |

---

## Métricas de Éxito

| Métrica | Actual (v0.2.9) | Objetivo Fase 2 | Objetivo Fase 4 |
|---------|-----------------|-----------------|-----------------|
| Tipos de corrección | 14 | 18 | 25 |
| Entidades en gazetteer | ~5,000 | 50,000 | 100,000 |
| Precisión gramática | ~80% | 85% | 90% |
| Tiempo análisis 100 págs | ~30s | ~25s | ~20s |
| Categorías de alerta | 14 | 16 | 20 |
| Endpoints API | 48+ | 55 | 70 |
| Componentes Vue | 54+ | 60 | 75 |

---

## Decisiones Técnicas

### Integración Diccionario (100% Offline) ✅ v0.2.9
- **Decisión**: Diccionario local descargable (NO consultas online)
- **Fuentes implementadas**:
  - Wiktionary español (SQLite)
  - Diccionario de sinónimos/antónimos (SQLite)
  - Diccionario personalizado del usuario (JSON)
- **Links externos** (para consulta manual): RAE DLE, María Moliner, Oxford, WordReference
- Cache en `~/.narrative_assistant/dictionaries/`
- **API endpoints**: `/api/dictionary/lookup/{word}`, `/api/dictionary/synonyms/{word}`, etc.
- Alineado con política de privacidad: manuscritos NUNCA salen de la máquina

### Informe de Revisión Detallado ✅ v0.2.9
- **Formatos**: PDF (reportlab) y DOCX (python-docx)
- **Estadísticas incluidas**:
  - Errores por categoría (gráfico de barras)
  - Distribución por capítulo
  - Distribución por confianza
  - Top errores más frecuentes
- **Recomendaciones automáticas** según patrones detectados
- **API endpoints**: `/api/projects/{id}/export/review-report`

### Arco Emocional Visual ✅ v0.2.9
- **Backend**: `nlp/sentiment.py` + `analysis/emotional_coherence.py`
- **Frontend**: `EmotionalAnalysis.vue` con timeline visual
- **Características**:
  - Evolución emocional por capítulo
  - Estados emocionales declarados
  - Detección de incoherencias emocionales
  - Sugerencias de corrección
- **API endpoint**: `/api/projects/{id}/characters/{name}/emotional-profile`

### Resumen con LLM
- Usar Ollama local (qwen2.5 o mistral)
- Limitar a 1 capítulo por vez para evitar timeout
- Cache de resúmenes generados

### Expansión Gazetteer
- Fuentes: Wikipedia español, Wikidata, INE
- Formato: JSON con categoría y variantes
- Actualización anual

---

## Referencias

- [Stilus - Corrector profesional](https://www.mystilus.com/en)
- [MeaningCloud NLP](https://www.meaningcloud.com/)
- [Documentación RAE](https://www.rae.es/)
- [spaCy español](https://spacy.io/models/es)

---

*Documento actualizado: 2026-01-26*
