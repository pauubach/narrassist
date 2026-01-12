# Glosario

[← Volver a Referencias](./README.md) | [← Índice principal](../../README.md)

---

## Términos Narratológicos

### Focalización

Término de Gérard Genette que describe la perspectiva desde la cual se narra. Determina qué información está disponible para el lector.

| Tipo | Descripción | Acceso a pensamientos |
|------|-------------|----------------------|
| **Cero** | Narrador omnisciente | Todos los personajes |
| **Interna** | Desde un personaje focal | Solo el personaje focal |
| **Externa** | Observador externo | Ninguno |

### Distancia Narrativa

Grado de separación entre el narrador y lo narrado. Incluye:
- **Discurso directo**: Diálogo textual ("—Voy a salir")
- **Discurso indirecto**: Reporte de habla (Dijo que iba a salir)
- **Estilo indirecto libre**: Mezcla narrador/personaje

### Tiempo Narrativo

Relación entre el tiempo de la historia y el tiempo del discurso:
- **Analepsis**: Flashback, salto al pasado
- **Prolepsis**: Flash-forward, anticipación
- **Elipsis**: Omisión de tiempo
- **Sumario**: Compresión temporal

### Voz Narrativa

Instancia que cuenta la historia. Caracterizada por:
- Nivel (intra/extradiegético)
- Persona gramatical
- Fiabilidad/no fiabilidad

### Chekhov's Gun

Principio dramático: todo elemento introducido debe tener función narrativa. Si aparece un rifle en el primer acto, debe dispararse en el tercero.

### Setup/Payoff

Técnica de plantar elementos que tendrán resolución posterior. El setup prepara; el payoff resuelve.

---

## Términos Técnicos (NLP)

### NER (Named Entity Recognition)

Tarea de NLP que identifica entidades nombradas en el texto:
- **PER**: Personas
- **LOC**: Lugares
- **ORG**: Organizaciones
- **MISC**: Otros

### Correferencia

Resolución de qué menciones se refieren a la misma entidad:
- "María" = "ella" = "la doctora" = "su madre"

### Pro-drop

Fenómeno lingüístico del español donde el sujeto se omite:
- "Llegó tarde" (¿quién llegó?)
- Afecta ~40-50% de los sujetos en español literario

### Embeddings

Representaciones vectoriales de texto que capturan significado semántico. Permiten calcular similitud entre frases.

### TTR (Type-Token Ratio)

Medida de riqueza léxica: tipos únicos / tokens totales. Ejemplo: "el gato y el perro" → 4/5 = 0.8

### MATTR (Moving-Average Type-Token Ratio)

TTR calculado sobre ventanas móviles para evitar sesgos de longitud.

### F1 Score

Medida de precisión de modelos: media armónica de precisión y recall.
- **Precisión**: Verdaderos positivos / predicciones positivas
- **Recall**: Verdaderos positivos / positivos reales

---

## Términos del Sistema

### Entidad

Elemento identificable y rastreable en el texto:
- Personajes
- Lugares
- Objetos significativos
- Organizaciones

### Atributo

Característica asociada a una entidad:
- **Físicos**: color de ojos, altura, edad
- **Psicológicos**: temperamento, miedos
- **Sociales**: profesión, estado civil
- **Background**: lugar de nacimiento, educación

### Alerta

Señal de posible inconsistencia detectada por el sistema:
- **Rojo (🔴)**: Confianza >90%
- **Naranja (🟠)**: Confianza 70-90%
- **Amarillo (🟡)**: Confianza 50-70%
- **Verde (🟢)**: Confianza 30-50%
- **Azul (🔵)**: Confianza <30% (informativo)

### Text Reference

Vinculación de cualquier dato extraído a su posición exacta en el texto original (capítulo, página, línea).

### Fusión de Entidades

Operación de unir varias menciones que se refieren a la misma entidad:
- "Roberto" + "el doctor" + "Martínez" → Roberto Martínez

### Perfil de Voz

Conjunto de características estilísticas de un personaje:
- Longitud media de oraciones
- Riqueza de vocabulario
- Nivel de formalidad
- Muletillas frecuentes

### Hoja de Estilo

Documento generado que resume las convenciones del manuscrito:
- Nombres y grafías
- Perfiles de personajes
- Lugares y sus características
- Cronología de eventos

### Gazetteer

Lista de términos conocidos para mejorar la detección de entidades:
- Nombres propios del manuscrito
- Lugares específicos
- Títulos y apodos

---

## Acrónimos

| Acrónimo | Significado |
|----------|-------------|
| NER | Named Entity Recognition |
| NLP | Natural Language Processing |
| LLM | Large Language Model |
| TTR | Type-Token Ratio |
| MATTR | Moving-Average Type-Token Ratio |
| F1 | F1 Score (medida de precisión) |
| POS | Part-of-Speech (etiquetado gramatical) |
| POV | Point of View (punto de vista) |
| CLI | Command Line Interface |
| GUI | Graphical User Interface |
| MVP | Minimum Viable Product |
| BD | Base de Datos |

---

## Niveles de Confianza

El sistema usa niveles de confianza para comunicar la certeza de sus detecciones:

| Nivel | Rango | Color | Interpretación |
|-------|-------|-------|----------------|
| Crítico | 90-100% | 🔴 | Muy probable que sea error real |
| Alto | 70-89% | 🟠 | Probablemente requiere atención |
| Medio | 50-69% | 🟡 | Posible problema, revisar |
| Bajo | 30-49% | 🟢 | Señal débil, puede ser intencional |
| Info | 0-29% | 🔵 | Informativo, no necesariamente error |

Los umbrales son configurables por el usuario y por tipo de alerta.

---

## Volver

[← Referencias](./README.md)
