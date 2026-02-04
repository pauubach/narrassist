# Roadmap - Narrative Assistant

> **Última actualización**: 2026-02-04
> **Versión actual**: 0.3.37
> **Estado actual**: Ver [PROJECT_STATUS.md](PROJECT_STATUS.md)
> **Historial de cambios**: Ver [CHANGELOG.md](CHANGELOG.md)

---

## Resumen

Este documento define las funcionalidades **pendientes de implementar**. El proyecto está funcionalmente completo para la funcionalidad core de correctores — solo queda infraestructura y mejoras de calidad.

**Documentación detallada de estado**:
- [research/ROADMAP_STATUS.md](research/ROADMAP_STATUS.md) - Estado detallado con auditorías
- [research/AUDIT_DECISIONS_AND_ROADMAP.md](research/AUDIT_DECISIONS_AND_ROADMAP.md) - Decisiones de auditoría y sprints de calidad
- [../EXPERT_REVIEW_FINDINGS.md](../EXPERT_REVIEW_FINDINGS.md) - Hallazgos de revisión multi-experto

---

## Estado Actual: Features Completas

Todas las features core están implementadas:

| Área | Estado |
|------|--------|
| **Backend NLP** | ✅ 177 archivos Python, 9 fases completas |
| **Frontend** | ✅ 83 componentes Vue, 6 vistas, 13 stores |
| **API** | ✅ 170 endpoints FastAPI |
| **Features Correctores** | ✅ 4 sprints (A-D) completados |
| **Tests** | ✅ 966+ tests passing |

---

## Trabajo Pendiente

### Sprints de Calidad (Post-Auditoría)

> Detalle: [AUDIT_DECISIONS_AND_ROADMAP.md](research/AUDIT_DECISIONS_AND_ROADMAP.md)

| Sprint | Objetivo | Items | Días |
|--------|----------|-------|------|
| **E: Hotfix Crítico** | Crashes + XSS | 5 | <1 |
| **F: Calidad Frontend** | Error handling, apiUrl, watch | 6 | 1-2 |
| **G: Lingüística Española** | Pasiva refleja, estar, haber | 8 | 2-3 |
| **H: Calibración Narrativa** | Tono diagnóstico, templates | 10 | 2-3 |
| **I: Tests + Calibración** | Cobertura + umbrales | 15 | 3-4 |
| **TOTAL** | | **44** | **~10 días** |

### Infraestructura Pendiente

| Tarea | Descripción | Coste/Tiempo |
|-------|-------------|--------------|
| Code signing Windows | Certificado EV | ~$300/año |
| Code signing macOS | Apple Developer | $99/año |
| ~~CI/CD Pipeline~~ | ~~GitHub Actions~~ | ✅ Completado (v0.3.0) |
| i18n | Inglés + Catalán | 8-10 días |
| Landing page | Sitio web producto | 5-6 días |
| Auto-updater | Tauri updater plugin | 3-4 días |

### Features Futuras (P2-P3)

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| Expansión gazetteer | +45,000 nombres propios | Media |
| Resumen por capítulo | LLM local (Ollama) | Media |
| Inconsistencias factuales | LLM detecta contradicciones | Alta |
| Conjugador verbal | Consultar conjugaciones | Media |
| Diccionario inverso | Buscar por terminación | Media |
| Clasificación IPTC | Taxonomía temática | Media |

---

## Métricas Objetivo

| Métrica | Actual (v0.3.37) | Objetivo v1.0.0 |
|---------|------------------|-----------------|
| Detectores | 14 | 25 |
| Gazetteer | ~5,000 | 100,000 |
| Endpoints API | 170 | 200+ |
| Componentes Vue | 83 | 110+ |
| Tests | 966+ | 2,000+ |
| Idiomas UI | 1 (ES) | 3 (ES, EN, CA) |

---

## Referencias

- [Stilus - Corrector profesional](https://www.mystilus.com/en)
- [MeaningCloud NLP](https://www.meaningcloud.com/)
- [Documentación RAE](https://www.rae.es/)
- [spaCy español](https://spacy.io/models/es)

---

*Documento actualizado: 2026-02-04*
