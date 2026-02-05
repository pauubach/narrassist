# Changelog - Narrative Assistant

Todas las versiones notables del proyecto están documentadas aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [0.4.43] - 2026-02-04

### Added
- **Sistema multi-backend LLM con fallback automático**
  - Cadena de prioridad: `llama.cpp → Ollama → Transformers → Reglas`
  - llama.cpp como backend principal (~150 tok/s, ~50MB)
  - Ollama como alternativa (~30 tok/s, más fácil de usar)
  - Fallback a reglas si ningún LLM disponible

- **Integración completa de llama.cpp**
  - `LlamaCppManager`: Gestor del ciclo de vida del servidor
  - Descarga automática de binarios desde GitHub releases
  - Descarga de modelos GGUF desde HuggingFace
  - API compatible con OpenAI (`/v1/chat/completions`)
  - Modelos soportados: `llama-3.2-3b` (2GB), `qwen2.5-7b` (4.4GB), `mistral-7b` (4.1GB)

- **Endpoints API para llama.cpp**
  - `GET /api/llamacpp/status` - Estado del servidor y modelos
  - `POST /api/llamacpp/install` - Instalar binario (~50MB)
  - `POST /api/llamacpp/download/{model}` - Descargar modelo GGUF
  - `POST /api/llamacpp/start` - Iniciar servidor
  - `POST /api/llamacpp/stop` - Detener servidor

- **Frontend Vue para llama.cpp**
  - UI en Settings > Métodos de Análisis
  - Estado centralizado en `system.ts` store
  - Acciones: instalar, descargar modelo, iniciar/detener
  - Selector de modelos unificado (llama.cpp + Ollama)

- **Validaciones de seguridad LLM**
  - Hosts LLM DEBEN ser localhost (protección de manuscritos)
  - Validación de path traversal en rutas de modelos
  - Logs sin datos sensibles (response.text eliminado)

### Changed
- `LocalLLMClient` ahora soporta múltiples backends con auto-detección
- `SystemCapabilities` incluye estado de llama.cpp
- Variables de entorno: `NA_LLM_BACKEND=auto|llamacpp|ollama|transformers|none`

### Security
- **Manuscritos 100% offline**: Validación localhost-only para todos los backends LLM
- Path traversal protection en model downloads
- Removed sensitive data from error logs

### Infrastructure
- **LanguageTool embebido con JRE portable**
  - Script `download_languagetool_jre.py` para descargar OpenJDK 21 + LanguageTool 6.4
  - JRE portable (~50MB) para Windows y macOS
  - LanguageTool JAR (~180MB) bundled en installer
  - Scripts de inicio automático (`start_lt_embedded.sh/bat`)
  - Workflow CI/CD actualizado para ambas plataformas
  - Validaciones de binarios en build process

---

## [0.3.22] - 2026-01-29

### Added
- **Benchmarks de registro por género literario** (12 géneros)
  - `RegisterGenreBenchmarks` dataclass con registro esperado, consistencia, distribución
  - Rangos para: registro dominante, consistencia (%), distribución por tipo, cambios bruscos
  - `GET /api/register/genre-benchmarks` para consultar benchmarks
  - `GET /api/projects/{id}/register-analysis/genre-comparison` para comparar vs género
- **Sugerencias de pacing basadas en benchmarks de género**
  - Cada desviación genera una sugerencia accionable con prioridad (high/medium/low)
  - Sugerencias para: longitud de capítulo, ratio diálogo, longitud oraciones, tensión, arco
  - Incluidas automáticamente en respuesta de `genre-comparison`
- **Invalidación de caché de perfiles de voz al re-analizar**
  - `DELETE FROM voice_profiles` al iniciar re-análisis de proyecto
  - Garantiza que los perfiles se recalculen con datos actualizados

---

## [0.3.21] - 2026-01-29

### Added
- **Benchmarks de pacing por género literario** (12 géneros)
  - `GenreBenchmarks` dataclass con rangos de referencia por tipo de documento
  - Géneros: FIC, MEM, BIO, CEL, DIV, ENS, AUT, TEC, PRA, INF, DRA, GRA
  - Rangos para: longitud de capítulo, ratio diálogo, longitud oraciones, tensión, arcos
  - `GET /api/pacing/genre-benchmarks` para consultar benchmarks
  - `GET /api/projects/{id}/pacing-analysis/genre-comparison` para comparar vs género
- **Correcciones manuales de correferencias** (persistencia en BD)
  - Tabla `coreference_corrections` con audit trail completo
  - `GET/POST/DELETE /api/projects/{id}/coreference-corrections`
  - Aplicación automática: reassign, unlink, confirm
  - Reversión al eliminar corrección
- **Correcciones manuales de atribución de hablantes**
  - Tabla `speaker_corrections` con tracking por capítulo
  - `GET/POST/DELETE /api/projects/{id}/speaker-corrections`
  - Filtrado por capítulo
- **Caché de perfiles de voz en BD**
  - Perfiles calculados se persisten en tabla `voice_profiles`
  - Parámetro `force_refresh` para recalcular
  - Reducción significativa de tiempo en consultas repetidas

### Changed
- **Schema BD**: Versión 10 → 11 (2 tablas nuevas: `coreference_corrections`, `speaker_corrections`)

---

## [0.3.20] - 2026-01-29

### Added
- **Endpoint de comparación de perfiles de voz** (`/voice-profiles/compare`)
  - Comparación side-by-side de métricas entre dos personajes con deltas
  - Índice de similitud global (normalizado 0-1)
  - Análisis de vocabulario compartido y exclusivo
- **Voice matching multi-métrica** en `speaker_attribution.py`
  - Reemplazo de matching superficial por scoring ponderado con 5 dimensiones:
    - Formalidad vía usted/tú (20%), longitud de intervención con z-score (20%),
      patrones de puntuación (15%), muletillas (20%), vocabulario TF-IDF (25%)
  - Alternativas rankeadas: `alternative_speakers` poblado con candidatos y scores

### Fixed
- **Tipo de `alternative_speakers`**: `List[Tuple[int, float]]` → `List[Tuple[int, str, float]]` (id, nombre, score)
- **Documentación PROJECT_STATUS.md**: Corregidas inconsistencias en sección P2 backend

---

## [0.3.19] - 2026-01-29

### Added
- **18 métricas de voz expuestas en API** (antes solo 10)
  - `to_dict()` en `VoiceMetrics` serializa todas las métricas
  - Frontend types y store transformers sincronizados
- **Estadísticas agregadas de registro** en endpoint project-wide
  - `consistency_pct`: porcentaje de segmentos en el registro dominante
  - `distribution_pct`: distribución porcentual por tipo de registro

### Fixed
- **Naming consistency API**: `chapter_num` → `chapter_number` en 2 path params (register, dialogue-attributions)
- **Query param renombrado**: `chapter` → `chapter_number` en temporal-markers
- **3 bare `except:` clauses** → `except Exception:` en `main.py`
- **Documentación**: Character Knowledge corregido de 60% a 85% en PROJECT_STATUS.md

---

## [0.3.18] - 2026-01-29

### Added
- **Análisis habilitados en perfil estándar**: `register_analysis`, `pacing`, `sticky_sentences`
  activados por defecto en `unified_analysis.py`
- **Filtrado por capítulo** en 5 endpoints:
  - `echo-report`, `sentence-variation`, `pacing-analysis`, `register-analysis`, `tension-curve`
  - Parámetro `chapter_number` para obtener resultados de un solo capítulo

### Changed
- **Documentación actualizada**: CHANGELOG, PROJECT_STATUS y ROADMAP sincronizados con estado real

---

## [0.3.17] - 2026-01-29

### Added
- **Sticky sentences integradas en pipeline unificado**
  - Nuevo paso en Phase 5 de `unified_analysis.py`
  - Detección de oraciones con >40% palabras funcionales (artículos, preposiciones, conjunciones)
  - Generación automática de alertas vía `create_from_sticky_sentence()`
- **Alertas de cambio de registro** conectadas al pipeline
  - `create_from_register_change()` integrado en generación de alertas
- **Alertas de eco léxico mejoradas**
  - Migración de alertas genéricas a `create_from_word_echo()` con datos estructurados

### Fixed
- **Bare except** en `docx_parser.py:411` → `except (AttributeError, TypeError):`
- **Versión hardcodeada** en `licensing/verification.py` → usa `_get_app_version()` dinámico

---

## [0.3.16] - 2026-01-29

### Fixed
- **CI build**: Re-trigger de GitHub Actions (re-tagging no lanza workflows)
- TypeScript: `per_chapter: any[]` añadido al tipo de respuesta de register analysis

---

## [0.3.15] - 2026-01-29

### Added
- **Logging diagnóstico de BD para producción**
  - Prefijos `[DB_INIT]`, `[SCHEMA]`, `[VERIFY]` en `database.py`
  - Verificación post-init con conexión sqlite3 independiente
  - WAL checkpoint forzado tras creación de esquema
  - Fallback: creación forzada de esquema si tabla `projects` no existe
- **Logging mejorado en `list_projects`**
  - Diagnóstico de existencia de archivo de BD
  - Enumeración directa de tablas vía sqlite3

### Fixed
- **TypeScript build**: Añadido `per_chapter` al tipo de respuesta en `voiceAndStyle.ts`

---

## [0.3.14] - 2026-01-29

### Added
- **Sprint de funcionalidades**:
  - **Categorías en StyleTab**: Agrupación por categoría de detectores editoriales
  - **Scene Cards**: Tarjetas de resumen por escena con personajes, ubicación y emociones
  - **Registro por capítulo**: Análisis de registro lingüístico desglosado por capítulo
  - **Razonamiento de correferencias**: Exposición de scores y razones de votación en API
- **Sensory Report**: Informe de uso sensorial (vista, oído, tacto, olfato, gusto)
- **Story Bible Export**: Exportación completa del universo narrativo
- **Scrivener Export**: Exportación compatible con formato Scrivener

### Fixed
- Logging mode en producción corregido

---

## [0.3.13] - 2026-01-29

### Added
- **Speaker Attribution**: Corrección de bug en atribución de diálogos
- **Style Alerts**: Alertas de estilo conectadas al pipeline
- **Tension Curve**: Curva de tensión narrativa implementada en pacing

### Fixed
- **Embedded Python**: Fallos de importación de módulos en builds de producción resueltos

---

## [0.3.12] - 2026-01-28

### Added
- **Atributos por capítulo**: Mostrar todos los capítulos donde aparece cada atributo de personaje

### Fixed
- **Embedded Python**: Funcionamiento en máquinas limpias sin Python del sistema instalado

---

## [0.3.11] - 2026-01-28

### Added
- **Sistema de configuración de corrección por tipo de documento**
  - Tipos: FIC, MEM, INF, TEC, AYU, COC, REF con subtipos
  - Herencia tipo → subtipo → proyecto con overrides personalizables
  - Tabla `correction_config_overrides` en BD para persistencia
- **Configuración de marcadores de diálogo per-función**
  - Enums: `DashType`, `QuoteType`, `MarkerDetectionMode`, `MarkerPreset`
  - Presets: español tradicional, anglosajón, comillas españolas, auto-detección
  - Campos por función: diálogo hablado, pensamientos, diálogo anidado, citas textuales
  - Preview visual de marcadores en modal de configuración
- **Tests E2E adversariales (Playwright)** para configuración de corrección
  - 35 tests: serialización, persistencia, adversarial (GAN), herencia, overrides, UI
  - Cobertura: XSS, SQL injection, race conditions, tipos incorrectos, valores nulos

### Changed
- **Frontend migrado a PrimeVue 4** con componentes actualizados
- **ESLint migrado a flat config** con dependencias actualizadas
- **DialogConfig.to_dict()** usa `_get_value()` helper para manejar dualidad enum/string

### Fixed
- Persistencia de configuración de marcadores (servidor devolvía formato antiguo)
- Tabla `correction_config_overrides` añadida a `ESSENTIAL_TABLES`
- Timing de inicialización de modal de configuración

---

## [0.3.1] - 2026-01-27

### Fixed
- **Mejoras significativas en extracción de atributos** (bug "ojos verdes")
  - Detección de negaciones mejorada (NEGATION_INDICATORS, CONTRASTIVE_PATTERNS)
  - Filtrado de atributos temporales/condicionales (TEMPORAL_PAST_INDICATORS, CONDITIONAL_INDICATORS)
  - Resolución de sujeto elíptico con penalización de objeto
  - Detección de cláusulas relativas (_is_inside_relative_clause)
  - Validación expandida de nombres de entidad (incluye verbos y palabras comunes)
  - Corrección de carga de menciones para usar todas las menciones de la BD

### Added
- **Tests de regresión para bug de atributos** (`tests/regression/test_ojos_verdes_bug.py`)
  - 8 tests cubriendo: posesivos, artículos vs pronombres, sujeto elíptico, negación, patrones contrastivos, temporales, cláusulas relativas
- **Framework de tests adversariales** (`tests/adversarial/test_attribute_adversarial.py`)
  - 60 casos de prueba en 20 categorías lingüísticas
  - Sistema GAN-style para mejora iterativa del algoritmo
- **Tests unitarios de correferencias** (`tests/unit/test_coreference.py`)
  - Tests para resolución de pronombres posesivos

### Changed
- **Frontend**: Mejoras en ChapterInspector y EntityInspector
  - Resúmenes automáticos de capítulo
  - Conteo de menciones de personajes
  - Eventos clave e interacciones

---

## [0.3.0] - 2026-01-26

### Added
- **Soporte multi-plataforma con Python embebido** 🎉
  - Windows: Python 3.12.7 embebido (~20MB) - ✅ Verificado funcional
  - macOS: Python 3.12.7 Framework (~30-40MB) - 🧪 Implementado, pendiente test
  - Solución permite instalación en máquinas **sin Python instalado**
- **Script de descarga multi-plataforma** (`scripts/download_python_embed.py`)
  - Descarga automática de Python por plataforma (Windows .zip, macOS .pkg)
  - Extracción de Python.framework en macOS vía pkgutil + cpio
  - Configuración automática de pip en Windows (_pth file)
- **Launcher Unix** (`src-tauri/binaries/start-backend.sh`)
  - Detección de OS (darwin/linux-gnu)
  - Resolución de Python (framework/link/system fallback)
  - Configuración de PYTHONPATH y ejecución de backend
- **Build script mejorado** (`scripts/build_app_with_python_embed.py`)
  - Detección automática de plataforma
  - Helper `get_python_embed_executable()` multi-plataforma
  - Paso adicional: verificación de pip instalado

### Changed
- **Configuración Tauri multi-plataforma** (`src-tauri/tauri.conf.json`)
  - `externalBin` sin extensión (Tauri auto-detecta .bat/.sh)
  - Recursos incluyen `start-backend.sh` explícitamente para permisos Unix
- **Backend detecta Python embebido** (`api-server/main.py`)
  - Skip Anaconda detection si `'python-embed'` en sys.executable
  - Compatible con Python.framework de macOS

### Documentation
- **PYTHON_EMBED.md**: Documentación técnica completa multi-plataforma
  - Arquitectura Windows y macOS
  - Proceso de build por plataforma
  - Launchers documentados con código completo
  - Roadmap: v0.3.0 (actual) → v0.3.1 (testing) → v0.4.0 (producción)
- **README.md**: Actualizado con info instalación multi-plataforma
- **MULTI_PLATFORM_STATUS.md**: Estado detallado por plataforma
- **MACOS_TESTING_CHECKLIST.md**: Checklist exhaustivo para validación macOS

### Technical Details
- Tamaño instalador Windows: ~40-50 MB
- Tamaño instalador macOS: ~60-70 MB
- Backend bundle: ~3.5MB (scripts Python sin PyInstaller)
- Sin conflictos numpy/PyInstaller en ninguna plataforma
- Primera ejecución descarga modelos NLP (~900MB), después 100% offline

---

## [0.2.9] - 2026-01-26

### Added
- **Informe de revisión detallado** (PDF/DOCX con estadísticas por categoría)
  - `exporters/review_report_exporter.py`: ReviewReportExporter, ReviewReportOptions, ReviewReportData
  - API: `/api/projects/{id}/export/review-report` (GET)
  - API: `/api/projects/{id}/export/review-report/preview` (GET)
- **Diccionario local multi-fuente** (100% offline)
  - `dictionaries/`: models, sources, manager
  - Fuentes: Wiktionary español, sinónimos/antónimos, diccionario custom
  - Links externos: RAE DLE, María Moliner, Oxford, WordReference
  - API: `/api/dictionary/lookup/{word}`, `/api/dictionary/synonyms/{word}`, etc.
- **UI Arco emocional completa**
  - `EmotionalAnalysis.vue`: Timeline visual, estados emocionales, incoherencias
  - API: `/api/projects/{id}/characters/{name}/emotional-profile`

---

## [0.2.8] - 2026-01-26

### Added
- **Detector de variantes ortográficas RAE** (14º detector)
  - Grupos consonánticos ps-, obs-, subs- (sicología→psicología)
  - Variantes con h (armonía/harmonía)
  - Variantes acentuales (periodo/período)
  - Extranjerismos no adaptados (ballet→balé)
- **Soporte para galicismos** en detector de extranjerismos (80+ términos franceses)
  - Gastronomía: chef, gourmet, sommelier
  - Moda: chic, boutique, prêt-à-porter
  - Arte: atelier, vernissage
  - Sociedad: savoir-faire, rendez-vous
- **Typography detector completo**
  - Secuencias de puntuación inválidas (`,.` `!?` `??`)
  - Pares de signos sin cerrar (`(texto` `«texto`)
  - Orden comilla/punto según RAE
- **Anacoluto detector completo**
  - Subject shift implementado
- **POV detector completo**
  - Focalizer shift implementado
  - Inconsistent omniscience implementado

---

## [0.2.7] - 2026-01-26

### Changed
- Limpieza de código duplicado y preparación release

---

## [0.2.6] - 2026-01-25

### Fixed
- Template vacío durante instalación de dependencias
- Ocultar ventana de consola Python en Windows

---

## [0.2.5] - 2026-01-25

### Fixed
- Template para fase 'installing-deps' en ModelSetupDialog

---

## [0.2.4] - 2026-01-25

### Added
- Detección de Python con verificación de versión (Python 3.10+)
- Endpoint `/api/system/python-status`
- UI para estado "Python no encontrado"
- Inclusión de info Python en `/api/models/status`

---

## [0.2.3] - 2026-01-25

### Fixed
- Setup sys.path antes de imports para PyInstaller

---

## [0.2.2] - 2026-01-24

### Fixed
- Cargar site-packages de usuario/Anaconda al inicio

---

## [0.2.1] - 2026-01-24

### Fixed
- Instalación de dependencias con PyInstaller

---

## [0.2.0] - 2026-01-24

### Fixed
- Verificar backend_loaded antes de descargar modelos

---

## [0.1.9] - 2026-01-24

### Added
- Lazy loading de dependencias NLP

---

## [0.1.8] - 2026-01-23

### Fixed
- NSIS hooks para cerrar procesos antes de instalar

---

## [0.1.7] - 2026-01-23

### Fixed
- Tutorial solo se muestra cuando modelos están listos

---

## [0.1.6] - 2026-01-23

### Added
- Primera versión con instalador funcional

---

## [0.1.5] - 2026-01-22

### Added
- Sistema de licencias completo (backend + API + frontend)
- Modelos bajo demanda (`core/model_manager.py`)
- Ollama bajo demanda (`llm/ollama_manager.py`)

---

## [0.1.4] - 2026-01-21

### Added
- Sidecar Python configurado (`scripts/build_sidecar.py`)
- Menú nativo Tauri (`src-tauri/src/menu.rs`)
- Iconos generados (32x32, 128x128, icns, ico)

---

## [0.1.0 - 0.1.3] - 2026-01-19

### Added
- MVP funcional completo
- Backend: 103 archivos Python, ~49,000 LoC
- Frontend: 53 componentes Vue, ~30,000 LoC
- API: 48+ endpoints FastAPI
- 14 detectores editoriales
- Sistema de correferencias con votación (4 métodos)
- Grafo de relaciones con vis-network
- Exportación JSON/Markdown
- Temas light/dark/auto

---

## Versiones Anteriores

Las versiones 0.0.x fueron desarrollo interno sin changelog formal.

---

*Documento actualizado: 2026-02-04*

> **Nota**: Para el estado actual completo del proyecto (v0.3.37+), ver [PROJECT_STATUS.md](PROJECT_STATUS.md) y [research/ROADMAP_STATUS.md](research/ROADMAP_STATUS.md).
