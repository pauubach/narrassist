# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

---

## [Unreleased]

### Añadido
- Manual de usuario completo (8 capítulos) con MkDocs Material
- Build automático del manual integrado en `npm run build`
- Composable `useAppToast` con 12 métodos semánticos en español natural
- ErrorBoundary component para manejo robusto de errores en UI
- Documentación de build process (DOCUMENTATION_BUILD.md)

### Cambiado
- Migrado toast notifications de `toast.add()` a API semántica (`saved()`, `updated()`, etc.)

---

## [0.10.15] - 2026-02-15

### Añadido
- **Sistema de caché comprehensivo** para NER, correferencias y atributos
  - Reduce tiempo de re-análisis de 3-5 min a <1 segundo
  - Caché basado en document_fingerprint (SHA-256 + n-gram Jaccard)
  - Invalidación inteligente solo cuando cambia el documento
- Detección automática de análisis bloqueados (`stuck_analysis`) con auto-limpieza
- Endpoint `/force-clear` para desbloquear análisis manualmente
- Marcadores claros de inicio/fin en logs de análisis para timing

### Corregido
- Proyectos bloqueados en estado `in_progress` tras reinicio del servidor
- Aserciones de tests en CI (ruff, mypy, TypeScript)
- Spinner de progreso centrado en UI
- Validación de `document_fingerprint` no vacío en metrics

---

## [0.10.14] - 2026-02-12

### Añadido
- **Character Speech Consistency Tracking** completo
  - Caché persistente de métricas de habla en DB
  - Análisis de patrones de habla por personaje
  - Detección de cambios de registro inconsistentes
- Sistema de eventos narrativos (Tier 1: 14 de 18 eventos)
  - ENCOUNTER, DEATH, BIRTH, TRAVEL, DECISION, REVELATION
  - Taxonomía de eventos con 3 niveles
- Navegación de eventos desde ChapterInspector al texto
- Integración de event continuity tracking en InconsistenciesPanel
- 58 pares de confusión semántica (homófonos españoles)

### Corregido
- **CRITICAL**: Comparación de EntityType enum vs string en speech tracking
- Z-index del panel de progreso
- Posiciones de citas `[REF:1]` en contexto expandido del chat

---

## [0.10.11] - 2026-02-08

### Añadido
- **FillerDetector** integrado con documentación de invariantes
- Badges diferenciados para tipos de muletillas/repeticiones en UI
- Inyección de selección como `[REF:1]` en chat con formato ultra-explícito

### Corregido
- Priorización de contexto de selección en chat
- Layout de botones en interfaz de chat

---

## [0.10.9] - 2026-02-06

### Añadido
- **Cross-Book Collections** (frontend completo)
  - Creación de colecciones multi-libro
  - Vinculación de entidades entre libros
  - Análisis de inconsistencias cross-book
- WordNet OMW 1.4 para sinónimos con auto-descarga
- Composables extraídos: `useAlertUtils`, `useEntityUtils`, `useAlertFiltering`, `useAlertExport`
- Numeración jerárquica de capítulos en sidebar y visor de texto

### Corregido
- Validación de entidades por proyecto (entity project validation)
- Filtro de sidebar y z-index normalizado
- Fugas de errores en manejo de excepciones
- Paths de endpoints LLM (`/llm/*` → `/api/services/llm/*`)
- Sección de entidades rechazadas en Settings
- Mensajes de diálogo y glossary 422

### Cambiado
- Redesign de Alerts tab a layout de 3 paneles
- Refactorización de frontend: integración de composables en AlertsDashboard y EntitiesTab
- Corrección de tipos duplicados en frontend

---

## [0.6.0] - 2026-01-30

### Añadido
- **Sprint S15**: Fixes de gramática española
  - Regla de artículos 'a' tónica (24 sustantivos femeninos)
  - Concordancia contextual mejorada (`_is_subject_modifier()`)
- **Sprint S6**: Endpoints de API para análisis avanzado
  - `/api/relationships/network` - Análisis de red de personajes
  - `/api/relationships/timeline` - Línea temporal
  - `/api/relationships/profiles` - Perfiles de personajes (6 indicadores)
  - `/api/relationships/knowledge` - Grafo de conocimiento
- Modo focus en alertas con navegación mejorada
- Ordenamiento de alertas por severidad > confianza > posición

### Cambiado
- Alertas priorizadas por severidad en vez de solo posición
- Transformadores de API: `start_char`/`end_char` → `spanStart`/`spanEnd`

---

## [0.5.0] - 2026-01-25

### Añadido
- **Sprint S5**: Prompting avanzado con LLM
  - Preferencia por Qwen 2.5 para español
  - Chain-of-Thought (CoT) en prompts
  - Sanitización anti-injection en inputs
- **Sprint S4**: Perfilado de personajes
  - 6 indicadores de caracterización
  - Análisis de red de relaciones
  - Detección de personajes Out-Of-Character (OOC)
  - Soporte para español clásico (Siglo de Oro)

---

## [0.4.0] - 2026-01-20

### Añadido
- **Sprint S3**: Detección de anacronismos
  - Patrones temporales
  - Validación de fechas históricas
  - Detección de tecnología fuera de época
- **Sprint S2**: Inferencia de género con pro-drop
  - Scoring de saliencia para menciones
  - Mejora en resolución de correferencias

---

## [0.3.0] - 2026-01-15

### Añadido
- **Sprint S1**: NER Multi-Modelo
  - PlanTL RoBERTa NER integrado
  - Votación entre 4 métodos (spaCy, RoBERTa, LLM, heurísticas)
  - Auto-alimentación de gazetteer desde entidades detectadas
- Ollama local para análisis LLM (llama3.2, mistral, qwen2.5)

---

## [0.2.0] - 2026-01-10

### Añadido
- **Sprint S0**: Limpieza de tests
  - 15 xfail obsoletos actualizados a tests normales
  - Cobertura de tests mejorada
- Pipeline de 6 fases de análisis
- Sistema de correferencias multi-método (4 métodos con votación)
- Detección de inconsistencias de atributos
- Frontend Vue 3 + Tauri con PrimeVue

---

## [0.1.0] - 2025-12-20

### Añadido
- Versión inicial del proyecto
- Parser de DOCX, TXT, MD, PDF, EPUB
- Análisis NLP con spaCy (es_core_news_lg)
- Extracción básica de entidades
- Detección de inconsistencias temporales
- API REST con FastAPI
- Base de datos SQLite con WAL mode
- Sistema de gestión de proyectos

---

## Tipos de Cambios

- **Añadido**: Nuevas funcionalidades
- **Cambiado**: Cambios en funcionalidades existentes
- **Deprecado**: Funcionalidades que serán eliminadas
- **Eliminado**: Funcionalidades eliminadas
- **Corregido**: Correcciones de bugs
- **Seguridad**: Correcciones de seguridad

[Unreleased]: https://github.com/pauubach/narrassist/compare/v0.10.15...HEAD
[0.10.15]: https://github.com/pauubach/narrassist/compare/v0.10.14...v0.10.15
[0.10.14]: https://github.com/pauubach/narrassist/compare/v0.10.11...v0.10.14
[0.10.11]: https://github.com/pauubach/narrassist/compare/v0.10.9...v0.10.11
[0.10.9]: https://github.com/pauubach/narrassist/compare/v0.6.0...v0.10.9
[0.6.0]: https://github.com/pauubach/narrassist/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/pauubach/narrassist/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/pauubach/narrassist/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pauubach/narrassist/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pauubach/narrassist/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pauubach/narrassist/releases/tag/v0.1.0
