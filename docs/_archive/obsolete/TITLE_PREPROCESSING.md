# Preprocesamiento de Títulos para spaCy

## Problema

Los títulos de capítulos causan errores de análisis sintáctico (dependency parsing) cuando se procesan directamente con spaCy. El parser confunde la estructura, especialmente cuando un título está directamente antes de la primera oración.

### Ejemplo del Problema

```
Input: "1: El Despertar\n\nMaría Sánchez se despertó temprano."

Parse INCORRECTO (con título):
1                    NUM      ROOT          ❌ MAL
El                   DET      det      -> Despertar
Despertar            PROPN    nsubj    -> despertó  ❌ ¡Debería ser nmod!
María                PROPN    iobj     -> Despertar ❌ ¡Debería ser nsubj!
despertó             VERB     acl      -> 1          ❌ ¡Debería ser ROOT!

Parse CORRECTO (sin título):
María                PROPN    nsubj    -> despertó  ✅ Correcto
despertó             VERB     ROOT               ✅ Correcto
```

### Causa

El parser de spaCy intenta conectar todas las palabras en un solo árbol de dependencias. Cuando hay una estructura irregular como "1: El Despertar" seguida de una oración normal, el parser:

1. Asigna "1" (NUM) como ROOT (intenta ser la palabra principal)
2. Intenta conectar "María" y "despertó" a "Despertar"
3. Genera análisis sintáctico incorrecto

## Solución

Separar los títulos del contenido narrativo ANTES de procesar con spaCy:

1. **Detectar** líneas que son títulos (patrones, heurísticas)
2. **Separar** títulos del contenido
3. **Procesar** cada párrafo de contenido independientemente
4. **Agrupar** resultados manteniendo la asociación título-contenido

## Arquitectura

### Módulo: `title_preprocessor.py`

**Propósito**: Detectar y separar títulos del contenido narrativo.

**Clases principales**:

#### `TitleDetector`
Detecta si una línea es un título usando múltiples heurísticas:

```python
class TitleDetector:
    def detect(self, text: str) -> tuple[bool, Optional[TitleType], float]:
        """
        Retorna: (is_title, title_type, confidence)

        Heurísticas:
        1. Patrones explícitos (máxima confianza)
           - "1: El Despertar", "Capítulo 1", "CHAPTER 5"
           - "2.1 Subsección", "Sección 2"
           - "* * *", "---", "###" (separadores)

        2. Longitud < 50 palabras
        3. Ausencia de verbo conjugado
        4. No termina en puntuación de fin de oración
        5. Empieza en mayúscula
        6. Contiene estructuras típicas de título
        """
```

#### `TitlePreprocessor`
Orquesta la detección y preprocesamiento:

```python
class TitlePreprocessor:
    def process(self, text: str) -> ProcessedDocument:
        """
        - Divide el texto en párrafos
        - Detecta títulos en cada párrafo
        - Retorna documento con clasificación
        """

    def separate_content_for_spacy(self, text: str) -> list[str]:
        """Retorna solo párrafos de contenido, listos para spaCy"""

    def process_with_context(self, text: str) -> Iterator[ProcessedParagraph]:
        """Permite iterar sobre párrafos con contexto"""
```

### Módulo: `spacy_title_integration.py`

**Propósito**: Integrar el preprocesador con pipelines de spaCy.

**Funciones principales**:

```python
def analyze_with_title_handling(nlp, text: str) -> TitleAwareAnalysisResult:
    """
    Analiza un texto con manejo especial de títulos.

    Retorna resultado agrupado:
    [
        (título_doc, [contenido_doc1, contenido_doc2, ...]),
        (título_doc2, [contenido_doc3, ...]),
        ...
    ]
    """

def extract_entities_by_title(nlp, text: str) -> dict:
    """
    Extrae entidades (PERSON, LOC, ORG) agrupadas por capítulo.

    Retorna:
    {
        "Capítulo 1: El Despertar": {
            "PERSON": ["María", "Juan"],
            "LOC": ["Madrid", "París"],
        },
        ...
    }
    """

def analyze_paragraphs_separately(nlp, text: str) -> Iterator:
    """
    Analiza párrafos uno a uno (lazy evaluation).
    Útil para documentos muy grandes.
    """
```

## Patrones Detectados

### 1. Capítulos Numerados

```
"1: El Despertar"
"1 - El Despertar"
"1. El Despertar"
"CAPÍTULO 1: El Despertar"
"Cap. 1: El Despertar"
"Chapter 1: The Awakening"
"I. El Despertar" (romanos)
```

### 2. Secciones

```
"2.1 Subsección"
"2.1: Título de subsección"
"Sección 2: Descripción"
```

### 3. Separadores de Escena

```
"* * *"
"***"
"---"
"___"
"###"
"~~~"
"===="
```

### 4. Heurísticas

- Longitud corta (típicamente < 15 palabras)
- Ausencia de verbo conjugado
- No termina en `.`, `!` o `?`
- Contiene `:`, `-` o `—`

## Uso

### Caso 1: Detección Simple

```python
from narrative_assistant.nlp.title_preprocessor import is_title

line = "1: El Despertar"
if is_title(line):
    print("Es un título")
```

### Caso 2: Preprocesamiento Básico

```python
from narrative_assistant.nlp.title_preprocessor import TitlePreprocessor

preprocessor = TitlePreprocessor()
processed = preprocessor.process(text)

for para in processed.paragraphs:
    if para.is_title:
        print(f"[TÍTULO] {para.text}")
    else:
        print(f"[CONTENIDO] {para.text}")
```

### Caso 3: Análisis con spaCy (Recomendado)

```python
from narrative_assistant.nlp.spacy_gpu import load_spacy_model
from narrative_assistant.nlp.spacy_title_integration import analyze_with_title_handling

nlp = load_spacy_model()
result = analyze_with_title_handling(nlp, text)

for title_doc, content_docs in result.grouped_by_title:
    print(f"Capítulo: {title_doc.text if title_doc else 'Sin título'}")

    for doc in content_docs:
        for token in doc:
            if token.pos_ == "VERB":
                print(f"  Verbo: {token.text} ({token.dep_})")
```

### Caso 4: Extracción de Entidades por Capítulo

```python
from narrative_assistant.nlp.spacy_title_integration import extract_entities_by_title

entities = extract_entities_by_title(nlp, text)

for title, ents_by_label in entities.items():
    print(f"Capítulo: {title}")
    for label, entity_list in ents_by_label.items():
        print(f"  {label}: {', '.join(entity_list)}")
```

### Caso 5: Análisis Lazy (Para Documentos Grandes)

```python
from narrative_assistant.nlp.spacy_title_integration import analyze_paragraphs_separately

for para, doc in analyze_paragraphs_separately(nlp, text):
    if not para.is_title:
        print(f"Párrafo {para.paragraph_index}:")
        for ent in doc.ents:
            print(f"  - {ent.text} ({ent.label_})")
```

## Rendimiento

### Impacto en Parsing

Con un texto problema típico:

```
Input: "1: El Despertar\n\nMaría se despertó..."

Sin preprocesamiento:
- ROOT incorrectamente asignado a "1" (NUM)
- Relaciones sintácticas incorrectas
- Entidades mal extraídas

Con preprocesamiento:
- Cada párrafo analizado independientemente
- ROOT correctamente asignado a "despertó" (VERB)
- Entidades correctamente extraídas
```

### Velocidad

- **Detección de títulos**: ~1ms por párrafo (regex)
- **Análisis spaCy**: Sin cambio significativo (mismo número de tokens)
- **Overhead total**: < 5% del tiempo de análisis

### Memoria

- **Bajo overhead**: Solo mantiene objetos `ProcessedParagraph`
- **No hay duplicación**: El texto se procesa una sola vez
- **Lazy evaluation**: Permite procesar documentos muy grandes

## Configuración

### Variables de Entorno

```bash
# Máximo de caracteres para considerar una línea como título
NA_MAX_TITLE_LENGTH=200

# Deshabilitar detección automática de títulos
NA_DISABLE_TITLE_PREPROCESSING=false
```

### Parámetros de Constructor

```python
# Detector
TitleDetector(max_title_length=200)

# Preprocessor
TitlePreprocessor(max_title_length=200)

# Análisis
analyze_with_title_handling(
    nlp,
    text,
    # keep_titles=False,  # Filtrar títulos en análisis
)
```

## Debugging

### Ver análisis detallado

```python
from narrative_assistant.nlp.spacy_title_integration import debug_parsing

output = debug_parsing(nlp, text)
print(output)
```

Muestra:
- Párrafos detectados (título vs contenido)
- Análisis token-por-token de cada párrafo
- Entidades encontradas
- Comparación antes/después del preprocesamiento

### Obtener métricas

```python
from narrative_assistant.nlp.spacy_title_integration import get_parsing_quality_metrics

metrics = get_parsing_quality_metrics(nlp, text)

print(f"Entidades con títulos: {metrics['with_titles']['entity_count']}")
print(f"Entidades sin títulos: {metrics['without_titles']['entity_count']}")
print(f"Diferencia: {metrics['with_titles']['entity_count'] - metrics['without_titles']['entity_count']}")
```

## Limitaciones y Edge Cases

### 1. Párrafos Cortos sin Estructura Numérica

```
"El Comienzo"  # Podría detectarse como título (sin número)
```

**Solución**: Usar `confidence` threshold. Si < 0.7, tratar como contenido.

### 2. Titulares en Contenido

```
"EL PERIÓDICO ANUNCIA NUEVO DESCUBRIMIENTO"
"LLAMADA URGENTE PARA TODOS LOS CIUDADANOS"
```

**Solución**: Contexto es clave. Estos se detectan mejor con `structure_detector.py` que usa estilos de Word.

### 3. Diálogos en Mayúscula

```
"¿DÓNDE ESTÁS?"  # Puede parecer un título
```

**Solución**: La heurística de verbo conjugado lo captura (pregunta contiene verbo).

### 4. Metadatos en DOCX

Los títulos pueden estar marcados con estilos Word (Heading 1, etc.), que `structure_detector.py` ya detecta.

**Recomendación**: Usar `structure_detector.py` primero para DOCX, luego `title_preprocessor.py` como fallback.

## Integración con Pipeline Actual

El preprocesador se integra en estos puntos:

### 1. Análisis de Atributos

```python
# En: nlp/attributes.py
from narrative_assistant.nlp.title_preprocessor import TitlePreprocessor

preprocessor = TitlePreprocessor()
processed = preprocessor.process(text)

for para in processed.get_content():  # Solo contenido
    # Analizar atributos
```

### 2. Extracción de Entidades

```python
# En: nlp/ner.py
from narrative_assistant.nlp.spacy_title_integration import extract_entities_by_title

entities = extract_entities_by_title(nlp, text)
# Agrupar por capítulo automáticamente
```

### 3. Análisis de Correferencias

```python
# En: nlp/coreference_resolver.py
from narrative_assistant.nlp.spacy_title_integration import analyze_paragraphs_separately

for para, doc in analyze_paragraphs_separately(nlp, text):
    # Resolver correferencias por párrafo
```

## Pruebas

Ver `frontend/e2e/title-preprocessing.spec.ts` para tests end-to-end.

## Referencias

- spaCy Dependency Parsing: https://spacy.io/usage/linguistic-features#dependency-parse
- Spanish Grammar: Verbs, Tenses, Conjugation
- Document Structure Detection (relacionado): `docs/STRUCTURE_DETECTION.md`
