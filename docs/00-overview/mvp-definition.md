# Definición del MVP

[← Volver a Overview](./README.md) | [← Índice principal](../../README.md)

> **Contexto**: Este documento define el MVP original. Todas las capacidades P0 y P1 están
> implementadas (v0.9.4). El sistema actual va más allá del MVP con detección temporal
> multinivel, perfilado de personajes, análisis de voz y ortografía.
> Ver [PROJECT_STATUS.md](../PROJECT_STATUS.md) para el estado actual.

---

## Las 12 Capacidades del MVP

El MVP ampliado incluye estas capacidades ordenadas por prioridad de implementación:

### P0 - Crítico (Núcleo obligatorio)

| # | Capacidad | STEPs | Descripción |
|---|-----------|-------|-------------|
| 1 | **Parser DOCX** | 1.1 | Extracción de texto preservando estructura de párrafos |
| 2 | **Detección de estructura** | 1.2 | Identificación de capítulos, escenas, separadores |
| 3 | **Pipeline NER** | 1.3 | Extracción de personajes (PER) y lugares (LOC) |
| 4 | **Detector de diálogos** | 1.4 | Identificación de parlamentos y acotaciones |
| 5 | **Correferencia básica** | 2.1 | Resolución de pronombres → nombres propios |
| 6 | **Fusión manual** | 2.2 | Unificación de entidades duplicadas por el usuario |
| 7 | **Extractor de atributos** | 2.3 | Características físicas/psicológicas de personajes |
| 8 | **Inconsistencias de atributos** | 2.4 | Detección de contradicciones en fichas |
| 9 | **Motor de alertas** | 7.1 | Centralización y gestión de todas las alertas |

### P1 - Alto valor (Recomendado)

| # | Capacidad | STEPs | Descripción |
|---|-----------|-------|-------------|
| 10 | **Variantes de grafía** | 3.1 | Detección de nombres escritos de formas diferentes |
| 11 | **Hoja de estilo** | 7.3 | Exportación de decisiones editoriales |
| 12 | **CLI** | 7.4 | Interfaz de línea de comandos funcional |

---

## Detalle por Capacidad

### 1. Parser DOCX

**Input**: Archivo `.docx`
**Output**: Estructura de párrafos con metadatos

```python
@dataclass
class Paragraph:
    id: int
    text: str
    style: str  # 'Heading 1', 'Normal', etc.
    chapter_id: Optional[int]
    page_estimate: int
```

**Criterio de éxito**: 100% de párrafos extraídos sin pérdida de texto.

---

### 2. Detección de Estructura

**Input**: Lista de párrafos
**Output**: Jerarquía de capítulos y escenas

**Patrones detectados**:
- Estilos de Word (Heading 1, 2, 3)
- Patrones textuales ("Capítulo X", "PARTE", números romanos)
- Separadores de escena ("***", "---", líneas en blanco)

**Criterio de éxito**: >95% de capítulos detectados correctamente.

---

### 3. Pipeline NER

**Input**: Texto segmentado
**Output**: Entidades etiquetadas (PER, LOC)

**Modelo**: `es_core_news_lg` (spaCy)

**Limitaciones conocidas**:
- F1 esperado en ficción: ~60-70%
- Nombres inventados requieren gazetteers dinámicos
- Validación manual obligatoria

---

### 4. Detector de Diálogos

**Input**: Texto
**Output**: Segmentos de diálogo con tipo

**Patrones**:
```
—Diálogo con raya
«Diálogo con comillas latinas»
"Diálogo con comillas inglesas"
```

**Criterio de éxito**: >98% de diálogos detectados.

---

### 5. Correferencia Básica

**Input**: Documento con entidades NER
**Output**: Clusters de menciones coreferentes

**Modelo**: Coreferee para spaCy

**Limitaciones conocidas**:
- F1 esperado: ~45-55%
- Pro-drop hace ~40-50% de sujetos invisibles
- Fusión manual (2.2) es OBLIGATORIA

---

### 6. Fusión Manual

**Input**: Sugerencias de duplicados
**Output**: Entidades unificadas

**Operaciones**:
- Fusionar: Unir 2+ entidades
- Dividir: Separar entidad fusionada por error
- Reasignar: Mover mención específica
- Alias: Añadir nombre alternativo

**Criterio de éxito**: El usuario puede corregir todos los errores de NER/coref.

---

### 7. Extractor de Atributos

**Input**: Menciones de personajes en contexto
**Output**: Atributos con fuentes

**Tipos de atributos**:
- Físicos: edad, color de ojos, altura
- Psicológicos: personalidad, miedos
- Roles: profesión, relaciones
- Hechos: conocimientos, habilidades

---

### 8. Inconsistencias de Atributos

**Input**: Fichas de personajes
**Output**: Alertas de contradicción

**Ejemplo**:
```
⚠️ INCONSISTENCIA: "Ojos"
- Cap.2, pág.56: "ojos verdes"
- Cap.3, pág.78: "ojos azules"
```

---

### 9. Motor de Alertas

**Input**: Alertas de todos los módulos (inconsistencias, variantes, etc.)
**Output**: Sistema unificado de gestión de alertas

**Funcionalidades**:
- Centralización de todas las alertas del sistema
- Estados: new → reviewed → pending → resolved/dismissed
- Historial completo de transiciones
- Filtrado por severidad, tipo, capítulo
- Persistencia de decisiones entre sesiones

---

### 10. Variantes de Grafía

**Input**: Lista de entidades
**Output**: Grupos de posibles duplicados

**Algoritmos**:
- Levenshtein distance
- Soundex/Metaphone para español
- Embeddings de caracteres

---

### 11. Hoja de Estilo

**Input**: Proyecto completo
**Output**: Documento exportable

**Contenido**:
- Decisiones de grafía
- Lista de personajes canónicos
- Convenciones tipográficas
- Notas del corrector

---

### 12. CLI

**Input**: Comandos de terminal
**Output**: Análisis y reportes

**Comandos principales**:
```bash
narrative-assistant analyze documento.docx
narrative-assistant export --format json proyecto.db
narrative-assistant report --type inconsistencies proyecto.db
```

---

## Criterios de Aceptación del MVP

El MVP está **completo** cuando:

1. ✅ Se puede cargar un DOCX y extraer estructura
2. ✅ Se detectan personajes y lugares con NER
3. ✅ Se resuelven correferencias (con validación manual)
4. ✅ Se pueden fusionar entidades manualmente
5. ✅ Se extraen atributos de personajes
6. ✅ Se detectan inconsistencias de atributos
7. ✅ Motor de alertas centraliza y gestiona hallazgos
8. ✅ Se detectan variantes de grafía
9. ✅ Se puede exportar hoja de estilo
10. ✅ Existe CLI funcional
11. ✅ Todo funciona 100% offline

---

## Lo que NO incluye el MVP

| Capacidad | Razón de exclusión |
|-----------|-------------------|
| Timeline automático | Requiere ordenación causal compleja |
| Focalización automática | No existe tecnología madura |
| UI gráfica | No esencial para validación |
| Soporte multilingüe | Complejidad innecesaria en MVP |
| LLM integrado | Requisitos de hardware excesivos |

---

## Siguiente Paso

Ver [Correcciones y Riesgos](./corrections-and-risks.md) para entender las limitaciones técnicas reales antes de implementar.
