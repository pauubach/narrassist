# Introducción

## ¿Qué es Narrative Assistant?

**Narrative Assistant** es una herramienta de asistencia profesional para escritores, editores y correctores que ayuda a detectar **inconsistencias narrativas** en manuscritos de cualquier género: novelas, memorias, ensayos, libros técnicos, manuales, etc.

A diferencia de correctores ortográficos tradicionales, Narrative Assistant se enfoca en la **coherencia interna** del manuscrito.

---

## Qué Detecta

<div class="grid cards" markdown>

-   :material-account:{ .lg } __Personajes__

    ---

    Atributos contradictorios (edad, apariencia, profesión), relaciones inconsistentes.

-   :material-clock-time-four:{ .lg } __Timeline__

    ---

    Secuencias temporales imposibles, edades incoherentes, fechas que no cuadran.

-   :material-calendar-today:{ .lg } __Eventos__

    ---

    Contradicciones de causa-efecto, eventos que se solapan.

-   :material-message-text:{ .lg } __Diálogos__

    ---

    Atribución de hablantes incorrecta, registro inconsistente.

-   :material-account-group:{ .lg } __Relaciones__

    ---

    Vínculos entre personajes mal definidos o contradictorios.

-   :material-map-marker:{ .lg } __Geografía__

    ---

    Ubicaciones contradictorias, distancias imposibles.

-   :material-text-search:{ .lg } __Calidad__

    ---

    Repeticiones, muletillas, problemas de claridad.

</div>

---

## Características Principales

### 1. Análisis NLP Avanzado (100% Local)

- **spaCy** para español (`es_core_news_lg`)
- **Embeddings semánticos** para similitud de texto
- **Multi-model NER** con votación (4 métodos)
- **Ollama** para análisis LLM local (llama3.2, qwen2.5, mistral)

!!! success "Privacidad garantizada"
    Todos los modelos corren en tu máquina. Tus manuscritos **nunca salen de tu ordenador**.

### 2. Detección de Inconsistencias

=== "Personajes"
    **Ejemplo**:

    - Cap. 3: *"María tiene 25 años"*
    - Cap. 12: *"María cumplió 30 años"*

    ⚠️ **Problema**: En la historia solo pasan 2 meses, pero María envejece 5 años.

=== "Timeline"
    **Ejemplo**:

    - *"Nació en 1990"*
    - *"En 2010 tenía 25 años"*

    ⚠️ **Problema**: Debería tener 20 años, no 25.

=== "Diálogos"
    **Ejemplo**:

    - Cap. 5: Personaje habla formalmente
    - Cap. 10: Mismo personaje usa jerga coloquial sin justificación

    ⚠️ **Problema**: Cambio de registro inconsistente.

=== "Relaciones"
    **Ejemplo**:

    - Cap. 2: *"Su hermano Juan"*
    - Cap. 15: *"Su primo Juan"*

    ⚠️ **Problema**: Parentesco contradictorio.

### 3. Gestión de Colecciones (Sagas)

Analiza **múltiples libros** de una saga y detecta inconsistencias entre ellos:

- Personaje aparece en Libro 1 con ojos azules, en Libro 3 con ojos verdes
- Evento clave descrito de forma diferente en cada tomo
- Relaciones entre personajes que cambian sin justificación

---

## Formatos Soportados

| Formato | Prioridad | Notas |
|---------|-----------|-------|
| **DOCX** | :star::star::star: | Word (recomendado) |
| **TXT** | :star::star::star: | Texto plano |
| **MD** | :star::star::star: | Markdown |
| **PDF** | :star::star: | Solo texto, no OCR |
| **EPUB** | :star::star: | E-books |

---

## Para Quién es Esta Herramienta

### ✅ Ideal para

- **Escritores de ficción**: Novelas, cuentos, series de libros
- **Editores profesionales**: Revisión editorial de manuscritos
- **Correctores**: Fase previa a corrección de estilo
- **Autores de no-ficción**: Memorias, biografías, ensayos
- **Escritores técnicos**: Libros técnicos, manuales, documentación

### ⚠️ No recomendado para

- Corrección ortográfica básica (usa Word/Antidote para eso)
- Gramática avanzada (Narrative Assistant complementa, no sustituye)
- Textos muy cortos (< 5.000 palabras)
- Idiomas distintos al español (solo soporta español por ahora)

---

## Requisitos del Sistema

### Mínimos

| Componente | Requisito |
|------------|-----------|
| **SO** | Windows 10+, macOS 11+, Linux (Ubuntu 20.04+) |
| **RAM** | 8 GB |
| **Disco** | 5 GB libres (modelos NLP + LLM) |
| **Conexión** | Solo primera vez (descarga de modelos) |

### Recomendados

| Componente | Recomendación |
|------------|---------------|
| **RAM** | 16 GB+ (para análisis LLM) |
| **GPU** | NVIDIA CUDA o Apple Silicon (acelera procesamiento) |
| **SSD** | Mejora tiempos de carga |

---

## Filosofía: Asistencia, No Automatización

!!! quote "Principio fundamental"
    **Narrative Assistant NO reescribe tu texto ni toma decisiones por ti.**

Esta herramienta:

- ✅ **Detecta** posibles inconsistencias
- ✅ **Señala** patrones sospechosos
- ✅ **Sugiere** qué revisar

**TÚ decides**:

- ❓ ¿Es realmente una inconsistencia o intencional?
- ❓ ¿Cómo quieres resolverla?
- ❓ ¿Qué alertas son relevantes para tu manuscrito?

!!! example "Ejemplo"
    Si un personaje cambia de nombre (María → Mari → Maruja), el sistema lo detecta. **Tú decides** si es un error o evolución narrativa intencional.

---

## Próximos Pasos

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg } __[Primer Análisis](first-analysis.md)__

    ---

    Aprende a crear tu primer proyecto y ejecutar el análisis.

-   :material-account-multiple:{ .lg } __[Gestión de Entidades](entities.md)__

    ---

    Cómo gestionar personajes, lugares y eventos detectados.

-   :material-alert:{ .lg } __[Trabajar con Alertas](alerts.md)__

    ---

    Interpreta y resuelve las inconsistencias detectadas.

</div>

---

!!! tip "Ayuda"
    Si encuentras algo poco claro, [abre un issue](https://github.com/pauubach/narrassist/issues).
