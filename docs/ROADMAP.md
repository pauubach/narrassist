# Roadmap - Narrative Assistant

> **Última actualización**: 2026-01-29
> **Versión actual**: 0.3.20
> **Estado actual**: Ver [PROJECT_STATUS.md](PROJECT_STATUS.md)
> **Historial de cambios**: Ver [CHANGELOG.md](CHANGELOG.md)

---

## Resumen

Este documento define las funcionalidades **pendientes de implementar**. Para el estado actual del proyecto, consultar [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## Trabajo Pendiente por Prioridad

### P1 - Alta Prioridad

#### Backend sin UI Completa

| Feature | Backend | Completitud | Estado |
|---------|---------|-------------|--------|
| ~~Knowledge Tracking~~ | `character_knowledge.py` | 85% | ✅ Extracción rules + LLM funcional (v0.3.19) |
| ~~Voice Profiles~~ | `voice/profiles.py` | 85% | ✅ API expone 18 métricas (v0.3.19) |
| ~~Register Analysis~~ | `voice/register.py` | 90% | ✅ Per-chapter (v0.3.14) + alertas (v0.3.17) |
| ~~Speaker Attribution~~ | `voice/speaker_attribution.py` | 85% | ✅ Bug fix (v0.3.13) |
| ~~Coreference Voting~~ | `coreference_resolver.py` | 95% | ✅ Razonamiento en API (v0.3.14) |
| ~~Pacing Analysis~~ | `analysis/pacing.py` | 90% | ✅ Curva de tensión (v0.3.13) |

**Esfuerzo restante**: Mejoras menores (benchmarks Knowledge, comparación Voice Profiles)

#### Funcionalidades Nuevas

| Funcionalidad | Descripción | Complejidad | Origen |
|---------------|-------------|-------------|--------|
| Expansión gazetteer | +45,000 nombres propios | Media | Stilus |
| Resumen por capítulo | LLM local (Ollama) | Media | MeaningCloud |
| Inconsistencias factuales | LLM detecta contradicciones | Alta | Roadmap v1 |

### P2 - Prioridad Media

| Funcionalidad | Descripción | Complejidad | Origen |
|---------------|-------------|-------------|--------|
| Conjugador verbal | Consultar conjugaciones integrado | Media | Stilus |
| Diccionario inverso | Buscar por terminación (rimas) | Media | Stilus |
| Explicaciones didácticas | Bibliografía RAE/Martínez de Sousa | Media | Stilus |
| Clasificación IPTC | Taxonomía temática estándar | Media | MeaningCloud |
| Clustering de temas | Identificar temas dominantes | Media | MeaningCloud |
| Ontología expandida | 200+ clases de entidades | Alta | MeaningCloud |

### P3 - Prioridad Baja

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| Generador morfosintáctico | Variantes de palabra | Alta |
| Lematizador en UI | Herramienta para lematizar | Fácil |
| Modo batch | Correcciones automáticas | Alta |
| Diccionarios de dominio | Ontologías especializadas | Alta |

---

## Infraestructura Pendiente

| Tarea | Descripción | Coste/Tiempo |
|-------|-------------|--------------|
| Code signing Windows | Certificado EV | ~$300/año |
| Code signing macOS | Apple Developer | $99/año |
| ~~CI/CD Pipeline~~ | ~~GitHub Actions~~ | ✅ Completado (v0.3.0) |
| i18n | Inglés + Catalán | 8-10 días |
| Landing page | Sitio web producto | 5-6 días |
| Auto-updater | Tauri updater plugin | 3-4 días |

---

## Métricas Objetivo

| Métrica | Actual (v0.3.20) | Objetivo v0.4.0 | Objetivo v1.0.0 |
|---------|-------------------|-----------------|-----------------|
| Detectores | 14 | 18 | 25 |
| Gazetteer | ~5,000 | 50,000 | 100,000 |
| Endpoints API | 170 | 180+ | 200+ |
| Componentes Vue | 89 | 95+ | 110+ |
| Tests | 966+ | 1,200+ | 2,000+ |
| Idiomas UI | 1 (ES) | 1 (ES) | 3 (ES, EN, CA) |
| Completitud módulos | 85-95% | 95% | 100% |

---

## Referencias

- [Stilus - Corrector profesional](https://www.mystilus.com/en)
- [MeaningCloud NLP](https://www.meaningcloud.com/)
- [Documentación RAE](https://www.rae.es/)
- [spaCy español](https://spacy.io/models/es)

---

*Documento actualizado: 2026-01-29*
