# Narrative Assistant

**Asistente de corrección para manuscritos** que detecta inconsistencias narrativas de forma automática y 100% privada.

> Tu manuscrito **nunca** sale de tu ordenador.

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

### 1. Sube tu manuscrito
Formatos soportados: **DOCX** (prioritario), TXT, Markdown, PDF, EPUB

### 2. Análisis automático
El sistema procesa el texto en múltiples fases:
- Entidades (personajes, lugares, objetos) con NER multi-modelo (spaCy + PlanTL RoBERTa)
- Correferencias con votación multi-método (embeddings, LLM, morfosintáctico, heurísticas)
- Atributos, relaciones y línea temporal
- Problemas de estilo y tipografía
- Perfiles de personaje y detección de comportamiento fuera de carácter

### 3. Revisa las alertas
Cada alerta incluye:
- Descripción del problema
- Ubicación exacta en el texto (con navegación al párrafo)
- Sugerencia de corrección
- Nivel de confianza (ajustado por pesos adaptativos)
- Modo foco: filtra alertas por capítulo o rango de capítulos

### 4. Itera
- Reanaliza después de corregir y compara versiones
- Las alertas corregidas se resuelven automáticamente
- El sistema aprende de tus decisiones (descartar = falso positivo, resolver = útil)

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
| GPU | No necesaria | NVIDIA con 4+ GB VRAM |
| Sistema | Windows 10, macOS 11, Ubuntu 20.04 | |

---

## Instalación

### Usuarios Finales

Descargar el instalador desde [Releases](../../releases):
- **Windows**: `Narrative-Assistant-Setup.exe`
- **macOS**: `Narrative-Assistant.dmg`

**No necesitas tener Python instalado** — la aplicación incluye Python embebido 3.12 con todas las dependencias.

La primera ejecución descargará automáticamente los modelos de NLP (~1 GB). Después funciona 100% offline.

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
| [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Estado actual del proyecto |
| [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) | Plan de sprints (S0-S16) |
| [BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) | Construcción de instaladores |
| [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) | Estrategia de empaquetado multi-plataforma |
| [COREFERENCE_RESOLUTION.md](docs/COREFERENCE_RESOLUTION.md) | Sistema de correferencias multi-método |
| [CHANGELOG.md](docs/CHANGELOG.md) | Historial de versiones |
| [LICENSING_PRODUCTION_PLAN.md](docs/LICENSING_PRODUCTION_PLAN.md) | Plan de monetización y licencias |

---

## Tests

```bash
# Tests unitarios (~1950 tests, ~3 min)
pytest tests/unit -v -m "not heavy"

# Tests pesados (requieren modelos NLP + Ollama)
pytest -m ""

# Lint
ruff check src/ tests/ api-server/

# Type-check frontend
cd frontend && npx vue-tsc --noEmit
```

---

*Versión 0.9.5 — 2026-02-14*
