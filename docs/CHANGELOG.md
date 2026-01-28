# Changelog - Narrative Assistant

Todas las versiones notables del proyecto están documentadas aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

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

*Documento generado: 2026-01-26*
