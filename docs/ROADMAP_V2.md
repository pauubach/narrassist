# Roadmap v2.0 - Narrative Assistant

> **Última actualización**: 2026-01-23
> **Versión actual**: 1.1.0

---

## Resumen del Estado Actual

### Completado ✅

| Área | Estado |
|------|--------|
| **Backend Core** | 103 archivos Python, ~49,000 LoC |
| **Frontend** | 53 componentes Vue, ~30,000 LoC |
| **API Server** | 39 endpoints FastAPI |
| **Detectores Editoriales** | 10 detectores implementados |
| **Exportación** | DOCX, PDF, JSON, Track Changes |
| **Sistema de Licencias** | Implementado |
| **Tauri Desktop** | Empaquetado listo |

### Detectores Actuales

1. ✅ Tipografía (guiones, comillas, espaciado)
2. ✅ Repeticiones léxicas
3. ✅ Concordancia género/número
4. ✅ Terminología inconsistente
5. ✅ Vocabulario regional (es_ES, es_MX)
6. ✅ Terminología de campo
7. ✅ Claridad/Estilo (oraciones largas)
8. ✅ Gramática (leísmo, dequeísmo)
9. ✅ Anglicismos
10. ✅ Muletillas del autor
11. ✅ Detector de legibilidad (Flesch-Szigriszt)
12. ✅ Detector de fillers/muletillas

---

## Ideas Inspiradas en Stilus

> Fuentes: [Stilus](https://www.mystilus.com/en), [La Linterna del Traductor](https://lalinternadeltraductor.org/n7/stilus.html)

### P1 - Alta Prioridad

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Expansión de gazetteer** | Ampliar de ~5,000 a 50,000+ nombres propios (personas, lugares, organizaciones) | Media |
| **Acceso a diccionarios RAE** | Integrar API del DLE para consultas de definiciones | Media |
| **Variantes ortográficas RAE** | Detectar cuando se usa variante no preferida (ej: "sicología" vs "psicología") | Fácil |
| **Informe de revisión detallado** | Generar informe PDF/DOCX con estadísticas de errores por categoría | Fácil |
| **Secuencias de puntuación inválidas** | Detectar ",." o "!?" mal usados | Fácil |

### P2 - Prioridad Media

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Conjugador verbal integrado** | Herramienta para consultar conjugaciones sin salir de la app | Media |
| **Diccionario inverso** | Buscar palabras por terminación (útil para rimas, cacofonías) | Media |
| **Pares de signos** | Verificar apertura/cierre de comillas, paréntesis, corchetes | Fácil |
| **Explicaciones didácticas** | Añadir bibliografía RAE/Martínez de Sousa a cada corrección | Media |
| **Detección de galicismos** | Expandir detector de extranjerismos a francés, italiano | Media |

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

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Análisis de sentimiento por capítulo** | Gráfico de arco emocional del libro | Media |
| **Ontología expandida (200+ clases)** | Clasificar entidades en subcategorías más precisas | Alta |
| **Detección de fechas y cantidades** | Extraer y normalizar fechas, números, monedas | Media |

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
| **Knowledge Tracking** | `character_knowledge.py` | Panel "Qué sabe cada personaje" |
| **Voice Profiles** | `voice/profiles.py` | Vista de perfiles de voz |
| **Register Analysis** | `voice/register.py` | Indicador de registro lingüístico |
| **Speaker Attribution** | `voice/speaker_attribution.py` | Atribución visual en diálogos |
| **Emotional Coherence** | `emotional_coherence.py` | Arco emocional visual |
| **Interaction Patterns** | `interactions/` | Panel de patrones de interacción |

### P2 - Detectores Adicionales

| Detector | Descripción | Complejidad |
|----------|-------------|-------------|
| **Anacolutos** | Oraciones con construcción sintáctica rota | Alta (LLM) |
| **Cambios de POV** | Detectar cambios involuntarios de punto de vista | Alta (LLM) |
| **Inconsistencias factuales** | Contradicciones en hechos narrados | Muy Alta (LLM) |

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

| # | Tarea | Tiempo | Origen |
|---|-------|--------|--------|
| 1 | Secuencias de puntuación inválidas | 1d | Stilus |
| 2 | Pares de signos (comillas, paréntesis) | 1d | Stilus |
| 3 | Variantes ortográficas RAE | 2d | Stilus |
| 4 | Informe de revisión detallado | 2d | Stilus |
| 5 | UI para Knowledge Tracking | 3d | Pendiente |

### Fase 2: Valor Diferencial (4 semanas)

| # | Tarea | Tiempo | Origen |
|---|-------|--------|--------|
| 6 | Resumen automático por capítulo | 5d | MeaningCloud |
| 7 | Arco emocional visual | 5d | MeaningCloud |
| 8 | Expansión gazetteer (+45,000 nombres) | 5d | Stilus |
| 9 | Integración API DLE (RAE) | 3d | Stilus |
| 10 | UI para Voice Profiles | 3d | Pendiente |

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

| Métrica | Actual | Objetivo Fase 2 | Objetivo Fase 4 |
|---------|--------|-----------------|-----------------|
| Tipos de corrección | 12 | 18 | 25 |
| Entidades en gazetteer | ~5,000 | 50,000 | 100,000 |
| Precisión gramática | ~80% | 85% | 90% |
| Tiempo análisis 100 págs | ~30s | ~25s | ~20s |
| Categorías de alerta | 13 | 16 | 20 |

---

## Decisiones Técnicas

### Integración RAE
- Usar API oficial del DLE si está disponible
- Alternativa: scraping con cache local (respetando términos de uso)
- Cache de consultas para modo offline

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

*Documento generado: 2026-01-23*
