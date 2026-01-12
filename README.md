# Asistente de Corrección Narrativa - Especificación Técnica

---

## Instalación

### Primera vez (requiere internet)

```bash
# 1. Clonar y entrar al proyecto
git clone <url-repo> tfm
cd tfm

# 2. Crear entorno virtual
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Descargar modelos NLP (~1 GB)
python scripts/download_models.py

# 5. Verificar
narrative-assistant verify
```

### En otra máquina (sin internet)

Copiar la carpeta `tfm/` completa (incluyendo `models/`).

```bash
cd tfm
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
narrative-assistant verify
```

### Uso básico

```bash
narrative-assistant verify           # Verificar entorno
narrative-assistant info             # Info del sistema
narrative-assistant analyze doc.docx # Analizar documento
```

---

## Inicio Rápido para Claude Code

### Si es tu primera vez:
1. Lee el [Resumen Ejecutivo](./docs/00-overview/README.md)
2. Revisa las [Correcciones Críticas](./docs/00-overview/corrections-and-risks.md) - **MUY IMPORTANTE**
3. Comienza con [STEP 0.1: Configuración del Entorno](./docs/steps/phase-0/step-0.1-environment.md)

### Si ya tienes contexto:
- [Índice de STEPs](./docs/steps/README.md) - Lista completa de 27 STEPs
- [Buscar STEP por fase](#índice-de-steps)

---

## Características Clave del Sistema

### 🔄 Análisis Progresivo
**Trabaja desde el primer momento.** No esperes a que termine todo el análisis:
- Los hallazgos se muestran en cuanto se detectan
- Barra de estado muestra progreso y fase actual
- Cada fase desbloquea funcionalidad inmediatamente

### 📝 Historial Completo
**Trazabilidad de todas las decisiones:**
- Estados de alertas: nueva → revisada → resuelta/ignorada
- Historial de versiones del manuscrito
- Las decisiones se mantienen al reimportar

### ⚡ Análisis Incremental
**Solo analiza los cambios:**
- Al reimportar un documento modificado, solo se procesan las diferencias
- Las alertas ignoradas NO se vuelven a mostrar
- Opción de forzar análisis completo si es necesario

Ver [Análisis Progresivo](./docs/02-architecture/progressive-analysis.md) y [Sistema de Historial](./docs/02-architecture/history-system.md).

---

## Índice de Documentación

### Contexto y Alcance
| Documento | Descripción | Cuándo Consultarlo |
|-----------|-------------|-------------------|
| [Resumen Ejecutivo](./docs/00-overview/README.md) | Visión general del proyecto | Al iniciar |
| [Objetivos y Alcance](./docs/00-overview/goals-and-scope.md) | Usuario objetivo, tolerancia a errores | Definir prioridades |
| [Definición MVP](./docs/00-overview/mvp-definition.md) | 12 capacidades del MVP | Priorización |
| [Correcciones y Riesgos](./docs/00-overview/corrections-and-risks.md) | Expectativas realistas NER/Coref | **Antes de cada STEP NLP** |

### Teoría Narratológica
| Documento | Contenido |
|-----------|-----------|
| [Índice de Heurísticas](./docs/01-theory/README.md) | Resumen de las 6 familias |
| [H1: Mundo](./docs/01-theory/heuristics-h1-world.md) | Entidades, espacio, tiempo |
| [H2: Personajes](./docs/01-theory/heuristics-h2-characters.md) | Atributos, conocimiento, voz |
| [H3: Estructura](./docs/01-theory/heuristics-h3-structure.md) | Escenas, arcos, setup/payoff |
| [H4: Voz](./docs/01-theory/heuristics-h4-voice.md) | Estilo, registro, repeticiones |
| [H5: Focalización](./docs/01-theory/heuristics-h5-focalization.md) | Tipos, detección, limitaciones |
| [H6: Información](./docs/01-theory/heuristics-h6-information.md) | Matriz de conocimiento, revelaciones |

### Arquitectura
| Documento | Contenido |
|-----------|-----------|
| [Arquitectura Alto Nivel](./docs/02-architecture/README.md) | Diagrama de capas, flujo |
| [Modelo de Datos](./docs/02-architecture/data-model.md) | Entidades, atributos, alertas |
| [Schema BD](./docs/02-architecture/database-schema.md) | SQLite completo |
| [Puntos de Extensión](./docs/02-architecture/extension-points.md) | Plugins, nuevas heurísticas |
| **[Análisis Progresivo](./docs/02-architecture/progressive-analysis.md)** | **UX tiempo real, eventos** |
| **[Sistema de Historial](./docs/02-architecture/history-system.md)** | **Estados, versiones, incremental** |

### Roadmap
| Documento | Contenido |
|-----------|-----------|
| [Hoja de Ruta](./docs/03-roadmap/README.md) | Visión general de fases |
| [Fase 0: Setup](./docs/03-roadmap/phase-0-setup.md) | Configuración inicial |
| [Fase 1: MVP](./docs/03-roadmap/phase-1-mvp.md) | Detalles del MVP ampliado |
| [Fases 2-7](./docs/03-roadmap/phases-2-7-post-mvp.md) | Post-MVP |
| [Hitos de Validación](./docs/03-roadmap/validation-milestones.md) | Criterios entre fases |

### Referencias
| Documento | Contenido |
|-----------|-----------|
| [Índice Referencias](./docs/04-references/README.md) | Bibliografía académica |
| [Glosario](./docs/04-references/glossary.md) | Términos técnicos y narratológicos |

---

## Índice de STEPs

### Prioridad de Implementación

```
P0 (CRÍTICO):      STEP 0.1-0.3, 1.1-1.4, 2.1-2.4, 7.1    (~50-70h)
P1 (ALTO VALOR):   STEP 3.1, 7.2, 7.3, 7.4                 (~18-28h)
P2 (VALOR MEDIO):  STEP 3.2-3.3, 4.1-4.3, 5.1-5.4        (~42-60h)
P3 (EXPERIMENTAL): STEP 6.1-6.2                           (~10-14h)
```

### Lista Completa de STEPs

| STEP | Nombre | Fase | Complejidad | Prerequisitos |
|------|--------|------|-------------|---------------|
| [0.1](./docs/steps/phase-0/step-0.1-environment.md) | Configuración Entorno | 0 | S | Ninguno |
| [0.2](./docs/steps/phase-0/step-0.2-project-structure.md) | Estructura Proyecto | 0 | S | 0.1 |
| [0.3](./docs/steps/phase-0/step-0.3-database-schema.md) | Schema BD | 0 | M | 0.2 |
| [1.1](./docs/steps/phase-1/step-1.1-docx-parser.md) | Parser DOCX | 1 | M | 0.3 |
| [1.2](./docs/steps/phase-1/step-1.2-structure-detector.md) | Detector Estructura | 1 | M | 1.1 |
| [1.3](./docs/steps/phase-1/step-1.3-ner-pipeline.md) | Pipeline NER | 1 | M | 0.1, 1.2 |
| [1.4](./docs/steps/phase-1/step-1.4-dialogue-detector.md) | Detector Diálogo | 1 | S | 1.1 |
| [2.1](./docs/steps/phase-2/step-2.1-coreference.md) | Correferencia Básica | 2 | L | 1.3 |
| [2.2](./docs/steps/phase-2/step-2.2-entity-fusion.md) | **Fusión Manual (CRÍTICO)** | 2 | M | 2.1, 0.3 |
| [2.3](./docs/steps/phase-2/step-2.3-attribute-extraction.md) | Extractor Atributos | 2 | L | 2.1 |
| [2.4](./docs/steps/phase-2/step-2.4-attribute-consistency.md) | Inconsistencias Atributos | 2 | L | 2.3 |
| [3.1](./docs/steps/phase-3/step-3.1-name-variants.md) | Variantes Grafía | 3 | M | 2.2 |
| [3.2](./docs/steps/phase-3/step-3.2-lexical-repetitions.md) | Repeticiones Léxicas | 3 | M | 1.1 |
| [3.3](./docs/steps/phase-3/step-3.3-semantic-repetitions.md) | Repeticiones Semánticas | 3 | L | 3.2 |
| [4.1](./docs/steps/phase-4/step-4.1-temporal-markers.md) | Marcadores Temporales | 4 | L | 1.3 |
| [4.2](./docs/steps/phase-4/step-4.2-timeline-builder.md) | Constructor Timeline | 4 | XL | 4.1 |
| [4.3](./docs/steps/phase-4/step-4.3-temporal-inconsistencies.md) | Inconsistencias Temporales | 4 | L | 4.2, 2.4 |
| [5.1](./docs/steps/phase-5/step-5.1-voice-profiles.md) | Perfiles Voz | 5 | L | 1.4 |
| [5.2](./docs/steps/phase-5/step-5.2-voice-deviations.md) | Desviaciones Voz | 5 | M | 5.1 |
| [5.3](./docs/steps/phase-5/step-5.3-register-changes.md) | Cambios Registro | 5 | M | 5.1 |
| [5.4](./docs/steps/phase-5/step-5.4-speaker-attribution.md) | Atribución Hablante | 5 | XL | 1.4, 2.2 |
| [6.1](./docs/steps/phase-6/step-6.1-focalization-declaration.md) | Declaración Focalización | 6 | M | 1.2 |
| [6.2](./docs/steps/phase-6/step-6.2-focalization-violations.md) | Verificación Focalización | 6 | L | 6.1 |
| [7.1](./docs/steps/phase-7/step-7.1-alert-engine.md) | Motor Alertas | 7 | L | 2.4 |
| [7.2](./docs/steps/phase-7/step-7.2-character-sheets.md) | Fichas Personaje | 7 | M | 2.3, 5.1 |
| [7.3](./docs/steps/phase-7/step-7.3-style-guide.md) | Guía Estilo | 7 | M | 5.1 |
| [7.4](./docs/steps/phase-7/step-7.4-cli.md) | CLI Principal | 7 | M | Todos |

### Diagrama de Dependencias

Ver [diagrama completo](./docs/steps/README.md#diagrama-de-dependencias)

---

## Modos de Análisis

| Modo | Comando | Descripción |
|------|---------|-------------|
| **Incremental** (default) | `analyze file.docx` | Solo cambios, respeta decisiones |
| **Completo respetando** | `analyze file.docx --mode full-keep` | Todo, pero mantiene ignoradas |
| **Completo desde cero** | `analyze file.docx --mode full-reset` | Todo nuevo, regenera ignoradas |

---

## Estimación Total

| Prioridad | Horas | Descripción |
|-----------|-------|-------------|
| P0 | 50-70h | Núcleo obligatorio (incluye motor alertas) |
| P1 | 18-28h | Alto valor, recomendado |
| P2 | 42-60h | Post-validación |
| P3 | 10-14h | Experimental (focalización) |
| **Total** | **120-172h** | ~3-4 semanas a tiempo completo |

