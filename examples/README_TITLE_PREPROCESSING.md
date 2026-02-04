# Ejemplos: Preprocesamiento de Títulos para spaCy

Esta carpeta contiene ejemplos y demostraciones del sistema de preprocesamiento de títulos para spaCy.

## Archivos

### `title_preprocessing_demo.py`

Demo interactivo que muestra los 5 casos de uso principales:

1. **Detección Simple** - Clasificar líneas como título/contenido
2. **Preprocesamiento** - Separar títulos del contenido
3. **Análisis con spaCy** - Procesar texto consciente de títulos
4. **Extracción de Entidades** - Agrupar entidades por capítulo
5. **Métricas de Impacto** - Comparar parsing antes/después

#### Ejecución

```bash
# Desde la raíz del proyecto
python examples/title_preprocessing_demo.py

# Verás salida formateada mostrando cada demo
```

#### Salida Esperada

```
================================================================================
DEMO 1: Detección Simple de Títulos
================================================================================

[TÍTULO] 1: El Despertar
[CONTENIDO] María Sánchez se despertó temprano.
[TÍTULO] CAPÍTULO 3: El Encuentro
[CONTENIDO] La luz del amanecer se filtraba por las ventanas.
...
```

## Uso Rápido

### Caso 1: ¿Es esto un título?

```python
from narrative_assistant.nlp.title_preprocessor import is_title

if is_title("1: El Despertar"):
    print("Es un título")
else:
    print("Es contenido")
```

### Caso 2: Separar títulos del contenido

```python
from narrative_assistant.nlp.title_preprocessor import TitlePreprocessor

text = """1: El Despertar

María se despertó temprano.

2: Continúa

El día avanzaba."""

preprocessor = TitlePreprocessor()
processed = preprocessor.process(text)

# Acceder a títulos
for title in processed.get_titles():
    print(f"[TÍTULO] {title.text}")

# Acceder a contenido
for content in processed.get_content():
    print(f"[CONTENIDO] {content.text}")
```

### Caso 3: Analizar con spaCy (Recomendado)

```python
from narrative_assistant.nlp.spacy_gpu import load_spacy_model
from narrative_assistant.nlp.spacy_title_integration import analyze_with_title_handling

nlp = load_spacy_model()
result = analyze_with_title_handling(nlp, text)

# Procesar cada capítulo
for title_doc, content_docs in result.grouped_by_title:
    print(f"\nCapítulo: {title_doc.text if title_doc else 'Sin título'}")

    for doc in content_docs:
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ == "ROOT":
                print(f"  Verbo: {token.text}")
```

### Caso 4: Extraer entidades por capítulo

```python
from narrative_assistant.nlp.spacy_title_integration import extract_entities_by_title

entities = extract_entities_by_title(nlp, text)

for chapter, ents_by_label in entities.items():
    print(f"{chapter}:")
    for label, entity_list in ents_by_label.items():
        print(f"  {label}: {', '.join(entity_list)}")
```

## Documentación Completa

Para comprensión detallada, consulta:

- **[TITLE_PREPROCESSING.md](../docs/TITLE_PREPROCESSING.md)** - Documentación técnica completa
- **[TITLE_PREPROCESSING_BEST_PRACTICES.md](../docs/TITLE_PREPROCESSING_BEST_PRACTICES.md)** - Mejores prácticas
- **[TITLE_PARSING_SOLUTIONS.md](../docs/TITLE_PARSING_SOLUTIONS.md)** - Respuestas a preguntas técnicas

## Módulos Disponibles

### `narrative_assistant.nlp.title_preprocessor`

```python
# Clases principales
from narrative_assistant.nlp.title_preprocessor import (
    TitleDetector,          # Detecta si una línea es un título
    TitlePreprocessor,      # Preprocesa documentos completos
    ProcessedDocument,      # Resultado del preprocesamiento
    ProcessedParagraph,     # Párrafo procesado
)

# Funciones de conveniencia
from narrative_assistant.nlp.title_preprocessor import (
    is_title,                      # ¿Es un título?
    preprocess_text_for_spacy,     # Eliminar títulos
    split_by_titles,               # Dividir en títulos/contenido
)
```

### `narrative_assistant.nlp.spacy_title_integration`

```python
# Análisis con título
from narrative_assistant.nlp.spacy_title_integration import (
    analyze_with_title_handling,         # Análisis agrupado por capítulo
    extract_entities_by_title,           # Entidades por capítulo
    extract_dependencies_by_title,       # Dependencias por capítulo
    analyze_paragraphs_separately,       # Análisis lazy
    get_parsing_quality_metrics,         # Métricas de calidad
    debug_parsing,                       # Debug detallado
)
```

## Patrones Detectados

El sistema detecta automáticamente:

### Capítulos
```
1: El Despertar
CAPÍTULO 1: El Comienzo
Cap. 1: Título
Chapter 1: The Awakening
I. Título (números romanos)
```

### Secciones
```
2.1 Subsección
2.1: Descripción
Sección 2: Contenido
```

### Separadores de Escena
```
* * *
---
___
###
~~~
====
```

### Heurísticas
- Párrafos cortos (< 15 palabras)
- Sin verbo conjugado
- Estructuras de título (dos puntos, guiones)

## Performance

- **Detección**: ~0.1ms por párrafo
- **Preprocesamiento**: ~10ms por documento (típico)
- **Overhead spaCy**: < 5%
- **Memoria**: Bajo (sin duplicación de texto)

## Casos de Uso

1. **Análisis de Consistencia de Personajes** por capítulo
2. **Detección de Inconsistencias de Atributos** agrupadas
3. **Extracción de Entidades** organizadas por estructura
4. **Análisis de Sentimiento** por capítulo
5. **Verificación de Coherencia** local

## Troubleshooting

### El modelo spaCy no carga

```bash
# Descargar el modelo manualmente
python scripts/download_models.py

# O forzar descarga
python -c "from narrative_assistant.nlp.spacy_gpu import load_spacy_model; load_spacy_model()"
```

### Falsos positivos (contenido detectado como título)

Ajustar el threshold de confianza:

```python
from narrative_assistant.nlp.title_preprocessor import TitleDetector

detector = TitleDetector(max_title_length=100)  # Más restrictivo
is_title, _, confidence = detector.detect(text)

# Solo considerar como título si confianza > 0.7
if confidence < 0.7:
    is_title = False
```

### Falsos negativos (títulos no detectados)

Aumentar el threshold de confianza:

```python
detector = TitleDetector(max_title_length=250)  # Más permisivo
# Esto detecta más títulos, pero también más falsos positivos
```

## API Rápida

### `TitlePreprocessor`

```python
preprocessor = TitlePreprocessor(max_title_length=200)

# Procesar documento
processed = preprocessor.process(text)

# Métodos útiles
processed.get_titles()              # Lista de títulos
processed.get_content()             # Lista de contenido
processed.get_content_text()        # Texto de contenido (sin títulos)
processed.title_count               # Número de títulos
processed.content_count             # Número de párrafos de contenido

# Iterar
for para in preprocessor.process_with_context(text):
    print(f"Título: {para.is_title}, Confianza: {para.confidence}")
```

### `analyze_with_title_handling(nlp, text)`

```python
result = analyze_with_title_handling(nlp, text)

# Atributos
result.docs                # Todos los docs de spaCy
result.title_count         # Número de títulos
result.content_count       # Número de párrafos de contenido
result.grouped_by_title    # [(title_doc, [content_docs]), ...]

# Iteración
for title_doc, content_docs in result.grouped_by_title:
    chapter = title_doc.text if title_doc else "Sin título"
    for doc in content_docs:
        # Procesar doc de spaCy
```

## Ejemplos Avanzados

### Análisis de Consistencia por Capítulo

```python
from narrative_assistant.nlp.spacy_title_integration import analyze_with_title_handling

result = analyze_with_title_handling(nlp, text)

# Extraer personajes por capítulo
personajes_por_capitulo = {}

for title_doc, content_docs in result.grouped_by_title:
    chapter = title_doc.text if title_doc else "Sin título"
    personajes = set()

    for doc in content_docs:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                personajes.add(ent.text)

    personajes_por_capitulo[chapter] = personajes

# Verificar consistencia
personajes_totales = set()
for pers in personajes_por_capitulo.values():
    personajes_totales.update(pers)

for chapter, pers in personajes_por_capitulo.items():
    print(f"{chapter}:")
    print(f"  Nuevos personajes: {pers - personajes_totales}")
```

### Procesamiento de Documentos Grandes

```python
from narrative_assistant.nlp.spacy_title_integration import analyze_paragraphs_separately

# Para novelas largas, procesar sin mantener todo en memoria
for para, doc in analyze_paragraphs_separately(nlp, huge_novel_text):
    if not para.is_title:
        # Procesar y descartar
        extract_features(doc)
        save_to_database(para, doc)
        # doc se libera aquí
```

## Reportar Problemas

Si encuentras issues:

1. Verifica que el modelo spaCy está cargado: `load_spacy_model()`
2. Usa `debug_parsing()` para ver el análisis detallado
3. Consulta `get_parsing_quality_metrics()` para comparar parsing
4. Abre un issue con ejemplo reproducible

## Roadmap

- [ ] Machine learning para detección de títulos
- [ ] Soporte para múltiples idiomas
- [ ] Custom patterns en constructor
- [ ] Caché distribuido para batch processing
- [ ] Integración con más pipelines NLP

## Referencias

- [spaCy Documentation](https://spacy.io)
- [Dependency Parsing](https://spacy.io/usage/linguistic-features#dependency-parse)
- [Named Entity Recognition](https://spacy.io/usage/linguistic-features#named-entities)
