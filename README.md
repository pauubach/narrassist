# Narrative Assistant

[![Versión](https://img.shields.io/badge/versión-0.11.12-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Tauri](https://img.shields.io/badge/Tauri-2.0-24C8DB.svg)](https://tauri.app/)
[![Licencia](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)
[![Offline](https://img.shields.io/badge/offline-100%25-orange.svg)](#privacidad-total)

**Asistente de corrección para manuscritos** que detecta inconsistencias narrativas de forma automática y 100% privada.

> Tu manuscrito **nunca** sale de tu ordenador.

📖 [Manual de Usuario](docs_site/user-manual/introduction.md) · 📝 [Historial de Cambios](CHANGELOG.md) · 🏗️ [Documentación Técnica](docs/)

---

## Para Quién Es

- **Correctores profesionales** que revisan novelas, memorias, ensayos
- **Editores literarios** que evalúan coherencia narrativa
- **Escritores** que quieren detectar errores antes de enviar a editorial

---

## Qué Detecta

### Inconsistencias Narrativas

| Problema | Ejemplo |
|----------|---------|
| **Atributos contradictorios** | "María tiene ojos azules" (cap. 2) vs "sus ojos verdes" (cap. 8) |
| **Errores temporales** | "Ayer martes" cuando el capítulo anterior era lunes |
| **Anacronismos** | Teléfono móvil en una novela ambientada en 1950 |
| **Conocimiento imposible** | Personaje sabe algo que no debería saber |
| **Cambios de POV** | Narrador en primera persona que de repente sabe pensamientos ajenos |
| **Comportamiento fuera de personaje** | Personaje tímido que de repente habla en público sin justificación |

### Problemas de Estilo

| Detector | Qué Encuentra |
|----------|---------------|
| **Tipografía** | Guiones incorrectos, comillas mal cerradas, espaciado |
| **Repeticiones** | Palabras repetidas, inicios de frase similares, cacofonías |
| **Muletillas** | Sobreuso de palabras ("realmente", "básicamente") |
| **Gramática** | Leísmo, dequeísmo, concordancia género/número |
| **Extranjerismos** | Anglicismos y galicismos con alternativas en español |
| **Variantes RAE** | Grafías no preferidas (sicología → psicología) |
| **Español clásico** | Normalización de formas del Siglo de Oro (fermoso → hermoso) |

### Análisis de Personajes

- **Fichas automáticas**: Atributos físicos, psicológicos, relaciones — 6 indicadores de perfil
- **Grafo de relaciones**: Visualización interactiva de conexiones entre personajes (vis-network)
- **Perfil de voz**: Cómo habla cada personaje (formalidad, muletillas, longitud)
- **Arco emocional**: Evolución emocional a lo largo del manuscrito
- **Línea temporal visual**: Vista de lista o interactiva con eventos y relaciones causales

### Sistema de Revisión Inteligente

- **Comparación entre versiones**: Detecta qué cambió entre revisiones del manuscrito
- **Resolución automática de alertas**: Identifica alertas que el autor ya corrigió
- **Track changes (.docx)**: Aprovecha marcas de revisión de Word para vincular correcciones
- **Historial de versiones**: Métricas de progreso con minigráficos de tendencia
- **Pesos adaptativos**: El sistema aprende de tus valoraciones (descartar/resolver) y ajusta la sensibilidad por tipo de alerta, proyecto y entidad

---

## Cómo Funciona

### 1. Carga tu manuscrito
Formatos soportados: **DOCX** (prioritario), TXT, Markdown, PDF, EPUB

Puedes ajustar el análisis con **presets por género**:
- Novela de ficción
- Divulgación / Técnico
- Memorias / Autobiografía
- Serie / Saga
- Policíaca / Misterio
- Corrección editorial

### 2. Análisis automático
El sistema ejecuta **14 fases de análisis**:

1. **Parsing** — lectura del documento y preparación del texto
2. **Clasificación** — tipología del documento y contexto editorial
3. **Estructura** — capítulos, bloques y organización narrativa
4. **NER** — personajes, lugares, objetos y otras entidades (multi-método)
5. **Fusión** — deduplicación y consolidación de entidades
6. **Timeline** — marcadores temporales, eventos y cronología
7. **Atributos** — rasgos físicos, psicológicos y metadata narrativa
8. **Consistencia** — contradicciones, continuidad y conocimiento imposible
9. **Gramática** — gramática, ortografía y redacción
10. **Alertas** — consolidación y priorización de hallazgos
11. **Relaciones** — vínculos familiares, románticos, profesionales y de conflicto
12. **Voz** — perfilado de habla, registro y diferenciación de personajes
13. **Prosa** — estilo, ritmo, repeticiones y calidad textual
14. **Health** — métricas globales y chequeos de salud narrativa

> 💡 Ver detalles en [Manual: Primer Análisis](docs_site/user-manual/first-analysis.md)

### 3. Revisa las alertas
Cada alerta incluye:
- 📝 **Descripción** del problema
- 📍 **Ubicación exacta** (navegación directa al párrafo)
- 💡 **Sugerencia** de corrección
- 🎯 **Confianza** ajustada por pesos adaptativos
- 🔍 **Modo foco** por capítulo o sección

**Filtrado avanzado**:
- Por severidad (crítico, alto, medio, bajo)
- Por categoría (inconsistencias, estilo, gramática)
- Por tipo específico (atributos, temporal, POV...)
- Búsqueda por texto

### 4. Itera y mejora
- ✏️ **Corrige** en tu editor de texto favorito
- 🔄 **Reanaliza** para comparar versiones
- ✅ **Resolución automática** de alertas corregidas
- 📈 **Métricas de progreso** entre revisiones

---

## Privacidad Total

- **100% Offline**: Todo el procesamiento ocurre en tu ordenador
- **Sin telemetría**: No recopilamos datos de uso
- **Sin conexión**: Después de la instalación inicial, no necesita internet
- **IA Local**: Los modelos de lenguaje corren localmente (Ollama)
- **Manuscritos aislados**: Los archivos nunca se envían a internet

---

## Requisitos

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| RAM | 8 GB | 16 GB |
| Disco | 3 GB | 6 GB (con modelos LLM) |
| GPU | No necesaria | NVIDIA con 4+ GB VRAM / Apple Silicon |
| Sistema | Windows 10, macOS 11, Ubuntu 20.04 | |

### Capacidades según Hardware

La profundidad del análisis se adapta automáticamente a los recursos disponibles.
No todos los ordenadores pueden ejecutar todas las funciones a la misma velocidad.

| Capacidad | PC Básico | PC Medio | PC Alto |
|-----------|-----------|----------|---------|
| | 8 GB RAM, sin GPU | 16 GB RAM, GPU integrada | 16+ GB, GPU dedicada |
| Gramática y ortografía | Si | Si | Si |
| Detección de personajes (NER) | Si (lento en >50k palabras) | Si | Si |
| Deduplicación de entidades | Limitado (>50k se omite) | Si | Si |
| Análisis LLM (Ollama) | No recomendado | Si (CPU, lento) | Si (GPU, rápido) |
| Relaciones y perfiles | No | Si | Si |
| Manuscritos <30k palabras | Análisis completo (~3 min) | Completo (~1 min) | Completo (<30s) |
| Manuscritos 50-100k palabras | Modo Ligero (~5 min) | Completo (~5 min) | Completo (~2 min) |
| Manuscritos >100k palabras | Modo Express (~2 min) | Modo Ligero (~8 min) | Completo (~5 min) |

**Modos de análisis** (seleccionable al re-analizar):

| Modo | Qué incluye | Ideal para |
|------|-------------|------------|
| **Express** | Gramática y ortografía | Revisión rápida, cualquier PC |
| **Ligero** | Express + detección de personajes + consistencia | Manuscritos grandes, PCs modestos |
| **Estándar** | Ligero + deduplicación + análisis LLM | Uso habitual (<50k palabras) |
| **Profundo** | Estándar + relaciones + conocimiento | Análisis exhaustivo con buenos recursos |
| **Auto** | Se ajusta según tamaño del documento | Recomendado (por defecto) |

> En modo **Auto**, la aplicación selecciona automáticamente el modo más adecuado
> según el tamaño del documento: >50k palabras usa Ligero, >100k usa Express.

---

## Primeros Pasos

1. **Instala** la aplicación (ver sección siguiente)
2. **Configura** un preset según tu tipo de manuscrito
3. **Carga** tu documento (DOCX, TXT, MD, PDF, EPUB)
4. **Analiza** — el primer análisis tarda 2-5 minutos según el tamaño
5. **Revisa** alertas y fichas de personajes
6. **Corrige** en tu editor favorito (Word, Scrivener, etc.)
7. **Reanaliza** para ver el progreso

> 📖 **Guía completa**: [Manual de Usuario](docs_site/user-manual/introduction.md) con ejemplos paso a paso

---

## Instalación Rápida

### Usuarios Finales

1. **Descarga** el instalador desde [Releases](../../releases):
   - **Windows**: `Narrative-Assistant-Setup.exe`
   - **macOS**: `Narrative-Assistant.dmg`

2. **Instala** y ejecuta — no necesitas tener Python instalado

3. **Primera ejecución**: descarga automática de modelos NLP (~1 GB)

4. **¡Listo!** Funciona 100% offline después de la instalación

> 💡 **Ayuda rápida**: Dentro de la aplicación, pulsa el botón "📖 Manual" para acceder a la guía completa con ejemplos paso a paso.

### Desarrolladores

```bash
git clone https://github.com/pauubach/narrassist.git tfm && cd tfm
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -r api-server/requirements.txt
python scripts/download_models.py
python scripts/setup_ollama.py
```

Ver [BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) para construcción y [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) para la estrategia de empaquetado multi-plataforma.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Frontend** | Vue 3, PrimeVue, vis-network, vis-timeline, Chart.js |
| **Desktop** | Tauri 2.0 (Rust) |
| **Backend** | Python 3.11+, FastAPI, uvicorn, SQLite (WAL) |
| **NLP** | spaCy (es_core_news_lg), PlanTL RoBERTa NER, sentence-transformers |
| **LLM Local** | Ollama (qwen2.5, llama3.2, mistral) con votación multi-modelo |
| **Empaquetado** | Python embebido 3.12.7, NSIS (Windows), DMG (macOS) |

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| 📖 [Manual de Usuario](docs_site/user-manual/introduction.md) | Guía completa en 8 capítulos (también disponible dentro de la app) |
| 📝 [CHANGELOG.md](CHANGELOG.md) | Historial de cambios de v0.1.0 a v0.11.12 |
| 🏗️ [Docs Técnicas](docs/) | Arquitectura, API reference, ADRs, build process |
| 🚀 [BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) | Guía para construcción y despliegue |
| 🐍 [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) | Estrategia de empaquetado multi-plataforma |
| 🔧 [CLAUDE.md](CLAUDE.md) | Instrucciones para desarrollo con Claude Code |

---

## Desarrollo

### Tests

```bash
# Tests ligeros
pytest -v

# Tests pesados (requieren modelos NLP + Ollama)
pytest -m ""
# o
python scripts/run_heavy_tests.py

# Cobertura
pytest --cov=src --cov-report=html
```

### Linting y Type Checking

```bash
# Backend Python
ruff check src/ tests/ api-server/
mypy src/

# Frontend TypeScript
cd frontend && npx vue-tsc --noEmit

# Formateo
black src/ tests/ api-server/
isort src/ tests/ api-server/
```

### Ejecutar en Desarrollo

```bash
# Terminal 1: API server
cd api-server
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend dev server
cd frontend
npm run dev

# Terminal 3 (opcional): Ollama para LLM
ollama serve
```

---

---

## Características Principales

### 🎯 Sagas y Series (Cross-Book Analysis)

- **Colecciones multi-libro**: Agrupa novelas de una saga para análisis conjunto
- **Entity linking**: Vincula personajes, lugares y objetos entre libros
- **Detección de inconsistencias cross-book**: Encuentra contradicciones entre libros (atributos, eventos)

### 🧠 Sistema de Aprendizaje Adaptativo

- **Pesos adaptativos**: El sistema aprende de tus decisiones (descartar/resolver)
- **Ajuste automático**: Sensibilidad por tipo de alerta, proyecto y entidad
- **Track changes**: Aprovecha marcas de revisión de Word para vincular correcciones

### 📊 Visualizaciones Interactivas

- **Grafo de relaciones**: Red de personajes con vis-network
- **Línea temporal**: Vista interactiva con vis-timeline
- **Arco emocional**: Evolución emocional de personajes por capítulo
- **Métricas de progreso**: Minigráficos de tendencias entre revisiones

### 🌐 Multi-Modelo y Multi-Método

- **NER**: Votación entre spaCy + PlanTL RoBERTa + LLM + heurísticas
- **Correferencias**: Votación entre embeddings + LLM + morfosintáctico + heurísticas
- **LLM local**: Ollama con qwen2.5, llama3.2, mistral (100% offline)

---

## Versión y Licencia

**Versión actual**: [0.11.12](CHANGELOG.md) — 2026-03-07

**Licencia**: MIT — ver [LICENSE](LICENSE)

**Repositorio**: [github.com/pauubach/narrassist](https://github.com/pauubach/narrassist)
