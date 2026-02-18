# 1. Introducción

## ¿Qué es Narrative Assistant?

**Narrative Assistant** es una herramienta de asistencia profesional para escritores, editores y correctores que ayuda a detectar **inconsistencias narrativas** en manuscritos de cualquier género: novelas, memorias, ensayos, libros técnicos, manuales, etc.

A diferencia de correctores ortográficos tradicionales, Narrative Assistant se enfoca en la **coherencia interna** del manuscrito:

- ✅ **Personajes**: Atributos contradictorios (edad, apariencia, profesión)
- ✅ **Timeline**: Secuencias temporales imposibles, edades incoherentes
- ✅ **Eventos**: Contradicciones de causa-efecto
- ✅ **Diálogos**: Atribución de hablantes, registro inconsistente
- ✅ **Relaciones**: Vínculos entre personajes mal definidos
- ✅ **Geografía**: Ubicaciones contradictorias
- ✅ **Calidad**: Repeticiones, muletillas, claridad

---

## Características Principales

### 1. Análisis NLP Avanzado (100% Local)

- **spaCy** para español (es_core_news_lg)
- **Embeddings semánticos** para similitud de texto
- **Multi-model NER** con votación (4 métodos)
- **Ollama** para análisis LLM local (llama3.2, qwen2.5, mistral)

**Privacidad garantizada**: Todos los modelos corren en tu máquina. Tus manuscritos **nunca salen de tu ordenador**.

### 2. Detección de Inconsistencias

| Categoría | Ejemplos |
|-----------|----------|
| **Personajes** | "María tiene 25 años" → "María cumplió 30 años" (en 1 mes de historia) |
| **Timeline** | "Nació en 1990" → "En 2010 tenía 25 años" (debería tener 20) |
| **Diálogos** | Hablante incorrecto, cambio de registro (formal → coloquial) |
| **Relaciones** | "Su hermano Juan" → "Su primo Juan" |
| **Eventos** | "Murió en capítulo 5" → "Aparece vivo en capítulo 10" |

### 3. Gestión de Colecciones (Sagas)

Analiza **múltiples libros** de una saga y detecta inconsistencias entre ellos:

- Personaje aparece en Libro 1 con ojos azules, en Libro 3 con ojos verdes
- Evento clave descrito de forma diferente en cada tomo
- Relaciones entre personajes que cambian sin justificación

### 4. Formatos Soportados

| Formato | Prioridad | Notas |
|---------|-----------|-------|
| **DOCX** | ⭐⭐⭐ | Word (recomendado) |
| **TXT** | ⭐⭐⭐ | Texto plano |
| **MD** | ⭐⭐⭐ | Markdown |
| **PDF** | ⭐⭐ | Solo texto, no OCR |
| **EPUB** | ⭐⭐ | E-books |

---

## Para Quién es Esta Herramienta

### ✅ Ideal para:

- **Escritores de ficción**: Novelas, cuentos, series de libros
- **Editores profesionales**: Revisión editorial de manuscritos
- **Correctores**: Fase previa a corrección de estilo
- **Autores de no-ficción**: Memorias, biografías, ensayos
- **Escritores técnicos**: Libros técnicos, manuales, documentación

### ⚠️ No recomendado para:

- Corrección ortográfica básica (usa Word/Antidote para eso)
- Gramática avanzada (Narrative Assistant complementa, no sustituye)
- Textos muy cortos (< 5.000 palabras)
- Idiomas distintos al español (solo soporta español por ahora)

---

## Requisitos del Sistema

### Mínimos

- **SO**: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+)
- **RAM**: 8 GB (16 GB recomendado para LLM)
- **Disco**: 5 GB libres (modelos NLP + LLM)
- **Conexión**: Solo primera vez (descarga de modelos)

### Recomendados

- **RAM**: 16 GB+ (para análisis LLM)
- **GPU**: NVIDIA CUDA o Apple Silicon (acelera procesamiento)
- **SSD**: Mejora tiempos de carga

---

## Filosofía: Asistencia, No Automatización

> **Narrative Assistant NO reescribe tu texto ni toma decisiones por ti.**

Esta herramienta:
- ✅ **Detecta** posibles inconsistencias
- ✅ **Señala** patrones sospechosos
- ✅ **Sugiere** qué revisar

**TÚ decides**:
- ❓ ¿Es realmente una inconsistencia o intencional?
- ❓ ¿Cómo quieres resolverla?
- ❓ ¿Qué alertas son relevantes para tu manuscrito?

**Ejemplo**: Si un personaje cambia de nombre (María → Mari → Maruja), el sistema lo detecta. **Tú decides** si es un error o evolución narrativa intencional.

---

## Próximos Pasos

1. **Instalación**: [README.md principal](../../README.md)
2. **Primer Análisis**: [Capítulo 2](02-first-analysis.md)
3. **Gestión de Entidades**: [Capítulo 3](03-entities.md)

---

**Nota**: Este manual está en desarrollo continuo. Si encuentras algo poco claro, [abre un issue](https://github.com/pauubach/narrassist/issues).
