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
| **Conocimiento imposible** | Personaje sabe algo que no debería saber |
| **Cambios de POV** | Narrador en primera persona que de repente sabe pensamientos ajenos |

### Problemas de Estilo

| Detector | Qué Encuentra |
|----------|---------------|
| **Tipografía** | Guiones incorrectos, comillas mal cerradas, espaciado |
| **Repeticiones** | Palabras repetidas, inicios de frase similares, cacofonías |
| **Muletillas** | Sobreuso de palabras ("realmente", "básicamente") |
| **Gramática** | Leísmo, dequeísmo, concordancia género/número |
| **Extranjerismos** | Anglicismos y galicismos con alternativas en español |
| **Variantes RAE** | Grafías no preferidas (sicología → psicología) |

### Análisis de Personajes

- **Fichas automáticas**: Atributos físicos, psicológicos, relaciones
- **Grafo de relaciones**: Visualización de conexiones entre personajes
- **Perfil de voz**: Cómo habla cada personaje (formalidad, muletillas, longitud)
- **Arco emocional**: Evolución emocional a lo largo del manuscrito

---

## Cómo Funciona

### 1. Sube tu manuscrito
Formatos soportados: **DOCX**, TXT, Markdown, PDF, EPUB

### 2. Análisis automático
El sistema procesa el texto detectando:
- Entidades (personajes, lugares, objetos)
- Atributos y relaciones
- Línea temporal
- Problemas de estilo

### 3. Revisa las alertas
Cada alerta incluye:
- Descripción del problema
- Ubicación exacta en el texto
- Sugerencia de corrección
- Nivel de confianza

### 4. Exporta el resultado
- Informe de revisión (PDF/DOCX)
- Fichas de personaje
- Documento con Track Changes

---

## Privacidad Total

- **100% Offline**: Todo el procesamiento ocurre en tu ordenador
- **Sin telemetría**: No recopilamos datos de uso
- **Sin conexión**: Después de la instalación inicial, no necesita internet
- **IA Local**: Los modelos de lenguaje corren localmente (Ollama)

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
- **Windows**: `Narrative-Assistant-Setup.exe` (~40-50 MB)
- **macOS**: `Narrative-Assistant.dmg` (~60-70 MB)
- **Linux**: `narrative-assistant_x.x.x_amd64.deb` (próximamente)

**✅ No necesitas tener Python instalado** - la aplicación incluye todo lo necesario.

La primera ejecución descargará automáticamente los modelos de NLP (~900 MB). Después funciona 100% offline.

### Desarrolladores

```bash
git clone <url-repo> tfm && cd tfm
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/download_models.py
```

Ver [docs/BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) para construcción e [docs/PYTHON_EMBED.md](docs/PYTHON_EMBED.md) para la estrategia de empaquetado multi-plataforma.

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) | **Estrategia de empaquetado multi-plataforma** (Windows, macOS, Linux) |
| [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Estado actual del proyecto |
| [BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) | Construcción de instaladores |
| [ROADMAP.md](docs/ROADMAP.md) | Funcionalidades futuras |
| [CHANGELOG.md](docs/CHANGELOG.md) | Historial de versiones |

---

## Tecnología

- **Empaquetado**: Python embebido 3.12.7 para distribución sin dependencias externas
- **NLP**: spaCy, sentence-transformers
- **LLM Local**: Ollama (llama3.2, qwen2.5, mistral)
- **Frontend**: Vue 3, PrimeVue, Tauri 2.0
- **Backend**: Python 3.12, FastAPI, uvicorn

---

*Versión 0.3.0 - 2026-01-26*
