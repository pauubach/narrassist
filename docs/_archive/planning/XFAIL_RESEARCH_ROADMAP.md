# Roadmap de Investigacion y Desarrollo: 7 xfails restantes

> Estado: v0.3.37 — 30 passed, 7 xfailed, 28/28 multimethod
> Fecha: 31 Enero 2026
> Baseline: 18 xfails -> 7 xfails (11 resueltos en v0.3.36)

---

## Indice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Tabla de prioridades](#2-tabla-de-prioridades)
3. [XF5: Temporal — fechas historicas y a.C.](#3-xf5-temporal--fechas-historicas-y-ac)
4. [XF3: Spelling — newlines en LanguageTool](#4-xf3-spelling--newlines-en-languagetool)
5. [XF1+XF7: Location — ubicacion de personajes](#5-xf1xf7-location--ubicacion-de-personajes)
6. [XF6: Family — numero de hijos](#6-xf6-family--numero-de-hijos)
7. [XF2: Laterality — lateralidad de extremidades](#7-xf2-laterality--lateralidad-de-extremidades)
8. [XF4: Possessive — atribucion sintactica de atributos](#8-xf4-possessive--atribucion-sintactica-de-atributos)
9. [Lineas de investigacion avanzada](#9-lineas-de-investigacion-avanzada)
10. [Tests adversariales propuestos](#10-tests-adversariales-propuestos)
11. [Dependencias entre tareas](#11-dependencias-entre-tareas)

---

## 1. Resumen ejecutivo

Quedan 7 tests xfail en `test_full_pipeline_e2e.py` agrupados en 5 categorias:

| Cat | Tests | Problema | Tipo |
|-----|-------|----------|------|
| **Temporal** | XF5 | Regex solo captura 1900-2029 | Implementacion directa |
| **Spelling** | XF3 | LanguageTool devuelve spans con `\n` | Implementacion directa |
| **Location** | XF1, XF7 | `LOCATION` existe como tipo pero ningun extractor lo soporta | Implementacion media |
| **Family** | XF6 | No existe AttributeType para hijos/familia | Implementacion media |
| **Laterality** | XF2 | No se extrae lateralidad de extremidades | Implementacion media |
| **Possessive** | XF4 | Atributos asignados por proximidad, no por sintaxis | **Requiere investigacion** |

---

## 2. Tabla de prioridades

| Prio | XF | Fix | Dificultad | Requiere investigacion | Archivos afectados |
|------|-----|-----|------------|----------------------|-------------------|
| **1** | XF5 | Ampliar regex temporal + a.C./d.C. | Baja | Si: a.C. implicito | `temporal/markers.py`, `temporal/inconsistencies.py` |
| **2** | XF3 | Descartar words con `\n` original | Baja | No | `nlp/orthography/voting_checker.py` |
| **3** | XF1+XF7 | Location patterns en RegexExtractor | Baja-Media | No | `nlp/extraction/extractors/regex_extractor.py`, `nlp/extraction/base.py` |
| **4** | XF6 | Family/children patterns | Media | No | `nlp/extraction/base.py`, `nlp/extraction/extractors/regex_extractor.py` |
| **5** | XF2 | Laterality AttributeType + patterns | Media | No | `nlp/extraction/base.py`, `nlp/extraction/extractors/regex_extractor.py` |
| **6** | XF4 | Posesion sintactica con spaCy deps | Alta | **Si** | `nlp/extraction/extractors/regex_extractor.py`, `nlp/extraction/extractors/dependency_extractor.py` |

---

## 3. XF5: Temporal — fechas historicas y a.C.

### Problema actual

El regex en `temporal/markers.py:150-152` solo captura anos 1900-2029:
```python
(r"\ben\s+(19\d{2}|20[0-2]\d)\b", 0.85),
(r"\b(19\d{2}|20[0-2]\d)\b", 0.6),
```

El test planta "Cortes llego a Mexico en 1521" vs "en 1519" — ambos fuera de rango.

### Solucion directa (sin investigacion)

Ampliar a `\d{3,4}` con validacion:
```python
# "en 1521" — cualquier ano 3-4 digitos con contexto
(r"\ben\s+(\d{3,4})\b", 0.80),
# "el ano 2350" — futurista
(r"\bel\s+a[ñn]o\s+(\d{3,4})\b", 0.90),
# Ano suelto 3-4 digitos (menor confianza, riesgo de falsos positivos con numeros)
(r"\b(\d{4})\b", 0.45),
```

Post-filtro para descartar numeros que no son anos (e.g., "habitacion 1521", "pagina 2350"):
- Contexto: verificar que no hay palabras como "pagina", "habitacion", "piso", "numero", "articulo" en los 30 chars anteriores
- Rango plausible: 500 <= ano <= 2200 (configurable por genero)

### Investigacion necesaria: a.C. implicito

**Pregunta de investigacion**: En textos sobre imperios antiguos, civilizaciones clasicas o epocas pre-cristianas, los anos suelen aparecer sin "a.C." despues de que el contexto lo establece. Ejemplo:

> "En el 44 a.C., Julio Cesar fue asesinado. Al ano siguiente, en el 43, estallo la guerra civil."

El "43" no lleva "a.C." pero se sobreentiende del contexto. Esto afecta a:

1. **Deteccion de era implicita**: Si ya aparecio "a.C." antes, los anos siguientes sin marcador estan probablemente en la misma era
2. **Comparacion numerica invertida**: En a.C., 44 > 43 cronologicamente
3. **Siglos romanos**: "siglo V a.C." vs "siglo V" (d.C. implicito)

**Expertos que deberian investigar**:
- **Linguista computacional**: Disenar heuristica de propagacion de era temporal. Analizar corpus de textos historicos en espanol para determinar con que frecuencia se omite "a.C." y en que contextos.
- **Historiador/editor**: Definir convenciones editoriales para manuscritos historicos. ¿Es un error del escritor omitir "a.C." o es convencion aceptada?
- **Arquitecto NLP**: Evaluar si el detector temporal necesita un estado de "era activa" que persista entre marcadores.

**Patrones a.C. a implementar (directos)**:
```python
# "44 a.C." / "44 a. C." / "44 AC" / "44 antes de Cristo"
(r"\b(\d{1,4})\s*(?:a\.?\s*C\.?|a\.?\s*de\s*C\.?|antes\s+de\s+Cristo|a\.?\s*n\.?\s*e\.?|BCE)\b", 0.95),
# "siglo V a.C."
(r"\bsiglo\s+([IVXLCDM]+)\s*(?:a\.?\s*C\.?|a\.?\s*de\s*C\.?|antes\s+de\s+Cristo)\b", 0.90),
```

**Modelo de datos**: Anadir campo `era` al `TemporalMarker`:
```python
@dataclass
class TemporalMarker:
    # ... campos existentes ...
    era: Literal["CE", "BCE"] = "CE"  # CE = d.C., BCE = a.C.
```

**Comparacion temporal con era**:
```python
def normalize_year(year: int, era: str) -> int:
    """Normaliza ano a valor signed para comparacion."""
    return -year if era == "BCE" else year
```

### Pros y contras

| Aspecto | Pro | Contra |
|---------|-----|--------|
| Ampliar regex | Desbloquea toda novela historica/sci-fi | Mas falsos positivos con numeros |
| Post-filtro contextual | Reduce falsos positivos | Complejidad anadida, posibles falsos negativos |
| Soporte a.C. | Cubre generos historicos completos | Requiere investigacion para a.C. implicito |
| Estado de "era activa" | Resuelve a.C. implicito | Aumenta complejidad del temporal checker, puede propagar errores |

### Plan de implementacion

1. **Fase 1 (directa)**: Ampliar regex a `\d{3,4}`, anadir patrones a.C. explicito, campo `era`
2. **Fase 2 (investigacion)**: Analizar corpus → disenar heuristica de propagacion de era → implementar
3. **Fase 3 (tests)**: Tests adversariales con fechas a.C., mixtas, futuristas

---

## 4. XF3: Spelling — newlines en LanguageTool

### Problema actual

En `voting_checker.py:506-508`, el word se limpia con `replace('\n', ' ')`, pero si el word original cruza dos parrafos (e.g., `"ultima\n\nprimera"`), el resultado limpio es `"ultima  primera"` — pasa el filtro `if word_clean:` porque no es whitespace-only.

### Solucion

Cambiar la estrategia: si el span original contiene `\n`, descartar completamente:

```python
word = text[match.offset:match.offset + error_len]
# Si el span cruza lineas, LanguageTool está analizando entre párrafos — ignorar
if '\n' in word or '\r' in word:
    continue
```

### Pros y contras

| Pro | Contra |
|-----|--------|
| Elimina los 64 falsos positivos | Podria perder errores reales que cruzan lineas (improbable en espanol) |
| Cambio de una linea | Ninguno significativo |

### Alternativa mas robusta

Pre-procesar el texto antes de enviarlo a LanguageTool: dividir en parrafos y analizarlos individualmente. Esto evita que LanguageTool vea spans cross-paragraph.

**Evaluacion**: La alternativa es mas robusta pero requiere mas cambios. La solucion simple (descartar spans con `\n`) es suficiente para el 99% de los casos.

### Plan de implementacion

1. Aplicar `if '\n' in word: continue` en ambas ramas (python lib y server client)
2. Verificar con test que las 64 alertas desaparecen
3. No requiere investigacion

---

## 5. XF1+XF7: Location — ubicacion de personajes

### Problema actual

`AttributeType.LOCATION` existe en `base.py:36` pero ningun extractor tiene patterns para extraerlo. No hay `LOCATION_PATTERNS` en `RegexExtractor` ni mapeo de dependencias en `DependencyExtractor`.

### Tests afectados

- **XF1** (`test_detect_floor_inconsistency`): "segundo piso" (cap.1) vs "quinto piso" (cap.3) — despacho de Maria
- **XF7** (`test_location_inconsistency_detected`): Marcos vive en "Barcelona" (cap.2) vs "Valencia" (cap.3)

### Solucion: LOCATION_PATTERNS en RegexExtractor

```python
LOCATION_PATTERNS = [
    # "vivía en Barcelona" / "vive en Madrid" / "residía en Valencia"
    (r'(?P<entity>[A-ZÁÉÍÓÚÜÑ]\w+)\s+(?:vivía|vive|vivió|reside|residía|habitaba)\s+en\s+(?P<value>[A-ZÁÉÍÓÚÜÑ][\w\s]+?)(?:\s+con|\s*[,.])', 0.85),
    # "vive con el padre en Barcelona" (entidad indirecta)
    (r'(?:vive|vivía|reside|residía)\s+(?:con\s+[\w\s]+?\s+)?en\s+(?P<value>[A-ZÁÉÍÓÚÜÑ]\w+)', 0.80),
    # "despacho en el segundo/quinto piso"
    (r'(?:su\s+)?(?:despacho|oficina|casa|apartamento|habitacion)\s+en\s+(?:el\s+)?(?P<value>(?:primer|segund|tercer|cuart|quint|sext|septim|octav|noven|decim)[oa]?\s+piso)', 0.80),
    # "desde su despacho en el quinto piso"
    (r'(?:en|desde)\s+(?:su\s+)?(?:despacho|oficina)\s+en\s+(?:el\s+)?(?P<value>[\w\s]+piso)', 0.75),
]
```

### Pros y contras

| Pro | Contra |
|-----|--------|
| Desbloquea 2 xfails con un solo cambio | Patterns pueden tener falsos positivos en textos donde "vivir en X" es metaforico |
| LOCATION ya existe en el enum | Comparacion de ubicaciones requiere normalizacion (e.g., "segundo piso" vs "2o piso") |
| No requiere investigacion | Necesita integracion con el consistency checker para comparar valores de LOCATION |

### Plan de implementacion

1. Anadir `LOCATION_PATTERNS` al `RegexExtractor`
2. Anadir `AttributeType.LOCATION` a `supported_attributes`
3. Compilar patterns en `_compile_patterns()`
4. Anadir branch de extraccion en `_extract_for_entity()`
5. Verificar que el consistency checker compara atributos de tipo LOCATION

---

## 6. XF6: Family — numero de hijos

### Problema actual

No existe `AttributeType` para composicion familiar. Ningun extractor tiene patterns para "un hijo", "dos hijos", "tenia tres hijos".

### Test afectado

- **XF6** (`test_children_inconsistency_detected`): Isabel Navarro tiene "un hijo" (cap.2) vs "dos hijos" (cap.3)

### Solucion

1. Anadir `FAMILY = "family"` al `AttributeType` enum
2. Crear `FAMILY_PATTERNS`:

```python
FAMILY_PATTERNS = [
    # "tenía dos hijos" / "un hijo de diez años"
    (r'ten[ií]a\s+(?P<value>un[oa]?|dos|tres|cuatro|cinco|\d+)\s+(?:hijo|hija|hijos|hijas)', 0.90),
    # "divorciada y tenía dos hijos"
    (r'(?:divorciada?|casada?|viuda?)\s+y\s+ten[ií]a\s+(?P<value>\w+)\s+hijos?', 0.85),
    # "madre/padre de X hijos"
    (r'(?:madre|padre)\s+de\s+(?P<value>un[oa]?|dos|tres|cuatro|cinco|\d+)\s+(?:hijo|hija|hijos|hijas)', 0.90),
    # "un hijo que vive con..."
    (r'(?P<value>un|una|dos|tres)\s+(?:hijo|hija)s?\s+(?:de|que)\b', 0.80),
    # "X hijos" (suelto, menos confianza)
    (r'(?:sus?\s+)?(?P<value>\w+)\s+hijos?\s+(?:de|que|viv)', 0.70),
]
```

### Detalle importante: comparacion numerica

Los valores extraidos seran palabras ("un", "dos") que necesitan normalizarse a numeros para comparacion:

```python
WORD_TO_NUM = {
    "un": 1, "una": 1, "uno": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}
```

### Pros y contras

| Pro | Contra |
|-----|--------|
| Cubre inconsistencia comun en manuscritos | Requiere nuevo AttributeType |
| Patterns claros y poco ambiguos | Normalizacion word→number anade complejidad |
| No requiere investigacion | Solo cubre hijos, no otros datos familiares (estado civil, parentesco) |

### Plan de implementacion

1. Anadir `FAMILY = "family"` a `AttributeType`
2. Anadir `FAMILY_PATTERNS` al `RegexExtractor`
3. Anadir normalizacion numerica en el consistency checker
4. Compilar y cablear patterns

---

## 7. XF2: Laterality — lateralidad de extremidades

### Problema actual

No existe extraccion de lateralidad (izquierda/derecha) para partes del cuerpo. `BODY_PARTS_TO_ATTR` en `DependencyExtractor` solo mapea partes a color (ojos→eye_color, pelo→hair_color).

### Test afectado

- **XF2** (`test_detect_leg_inconsistency`): "pierna izquierda" (cap.1) vs "pierna derecha" (cap.3)

### Solucion

1. Anadir `LATERALITY = "laterality"` al `AttributeType` enum
2. Crear `LATERALITY_PATTERNS`:

```python
LATERALITY_PATTERNS = [
    # "pierna/brazo/ojo izquierda/derecho"
    (r'(?:su\s+)?(?P<bodypart>pierna|brazo|ojo|oreja|mano|rodilla|hombro|tobillo|codo)\s+(?P<value>izquierd[oa]|derech[oa])', 0.90),
    # "de la pierna izquierda" / "en la mano derecha"
    (r'(?:de|en)\s+(?:la|el)\s+(?P<bodypart>pierna|brazo|ojo|oreja|mano|rodilla|hombro)\s+(?P<value>izquierd[oa]|derech[oa])', 0.90),
    # "cojeaba de la pierna izquierda"
    (r'coje(?:a|aba)\s+(?:de\s+)?(?:la\s+)?(?P<bodypart>pierna)\s+(?P<value>izquierd[oa]|derech[oa])', 0.90),
    # "la pierna izquierda, la que le molestaba"
    (r'(?:su|la)\s+(?P<bodypart>pierna|brazo|mano)\s+(?P<value>izquierd[oa]|derech[oa]),?\s+(?:la|el)\s+que', 0.85),
]
```

### Detalle: body part como clave de comparacion

El atributo necesita incluir el body part para que "pierna izquierda" y "pierna derecha" se comparen correctamente (ambas son piernas, pero con lateralidad diferente). Propuesta:

```python
ExtractedAttribute(
    entity_name="Pedro",
    attribute_type=AttributeType.LATERALITY,
    value="izquierda",
    extra_data={"body_part": "pierna"},
)
```

El consistency checker debe agrupar por `(entity, attribute_type, body_part)` para detectar conflictos.

### Pros y contras

| Pro | Contra |
|-----|--------|
| Detecta inconsistencia comun (escritores cambian lateralidad) | Requiere nuevo AttributeType + body_part metadata |
| Patterns claros | El consistency checker necesita soporte para extra_data grouping |

### Plan de implementacion

1. Anadir `LATERALITY = "laterality"` a `AttributeType`
2. Anadir `LATERALITY_PATTERNS` al `RegexExtractor`
3. Pasar `body_part` via `extra_data` del `ExtractedAttribute`
4. Modificar consistency checker para agrupar por `(entity, type, extra_data.body_part)`

---

## 8. XF4: Possessive — atribucion sintactica de atributos

### Problema actual

`RegexExtractor._find_nearest_entity()` asigna atributos a la entidad mas cercana textualmente, ignorando la estructura sintactica. Esto produce errores cuando hay 2+ personajes en una oracion.

### Ejemplo del test

Cap.2: "Maria, con su cabello rubio recogido en una coleta, examinaba un documento"
- `hair_color=rubio` se asigna correctamente a Maria (proximidad funciona aqui)

Pero en otros contextos:
- "Pedro miro a Maria con sus ojos azules" → `eye_color=azules` deberia ser de Pedro (`con` = instrumental)
- "Pedro miro a Maria a sus ojos azules" → `eye_color=azules` deberia ser de Maria (`a` = direccional)

### Investigacion realizada: analisis de dependencias spaCy

Script: `scripts/analyze_possessive_deps.py`

**Resultados**:

| Patron | dep_ de body_part | Preposicion | Senal spaCy | Disambiguable |
|--------|-------------------|-------------|-------------|---------------|
| "miro ... con sus ojos" | `obl` | `con` | Instrumental → sujeto | **Si** |
| "miro ... a sus ojos" | `obl` | `a` | Direccional → objeto | **Parcial** (a es polisemico) |
| "los ojos de Maria" | `obj` | `de` (en sibling) | Genitivo posesivo | **Si** (heuristica) |
| "Pedro, de ojos azules," | `nmod` → Pedro | `de` | Link directo nmod | **Si** |

### Investigacion pendiente

**Pregunta 1: Polisemia de "a"**

> "Pedro miro **a** sus ojos azules" — aqui "a" es direccional (ojos de Maria)
> "Pedro se aferro **a** sus principios" — aqui "a" no refiere a body_parts
> "A Maria le brillaban los ojos" — topicalizacion, ojos de Maria

La preposicion "a" tiene multiples funciones en espanol:
- Complemento directo animado: "miro **a** Maria"
- Direccional: "miro **a** sus ojos"
- Dativo etico: "**a** Maria le brillaban los ojos"
- Complemento de regimen: "se aferro **a** sus principios"

**Expertos que deberian investigar**:
- **Linguista hispanista**: Clasificar las funciones de "a" que implican posesion del OD vs del sujeto. Crear catalogo de verbos de percepcion (mirar, observar, contemplar, admirar) donde "a + body_part" implica posesion del OD.
- **Especialista en spaCy**: Evaluar si la etiqueta `obl` con `a` tiene sub-clasificaciones en el modelo es_core_news_lg. Explorar si la morph info anade senal.

**Pregunta 2: Pronombre posesivo ambiguo "sus" en 3a persona**

> "Pedro hablo con Juan. **Sus** ojos brillaban."

"Sus" puede referirse a Pedro o a Juan. spaCy NO resuelve esta ambiguedad (la morph es `Person=3|Poss=Yes` sin referente). Resolver esto requiere:
- Correferencia (ya existe sistema de correferencia multi-metodo en el codebase)
- Heuristica de sujeto topico (el sujeto de la oracion anterior suele ser el antecedente)
- LLM como arbitro

**Expertos que deberian investigar**:
- **Investigador en correferencia**: Evaluar si el sistema de correferencia existente (4 metodos: embeddings 30%, LLM 35%, morpho 20%, heuristics 15%) puede resolver posesivos "su/sus" en el contexto de atribucion de atributos.
- **Arquitecto**: Disenar la integracion entre el coreference resolver y el attribute extractor. ¿Se resuelve primero la correferencia y luego se extraen atributos? ¿O se hace en paralelo con votacion?

**Pregunta 3: Mas patrones sintacticos**

Patrones adicionales que necesitan cobertura:

| Patron | Ejemplo | Dueno | Senal |
|--------|---------|-------|-------|
| Reflexivo | "Se toco su cabello rubio" | Sujeto | Pronombre reflexivo `se` |
| OI topicalizado | "A Maria le brillaban los ojos azules" | OI (Maria) | `iobj` en dep tree |
| Relativa especificativa | "Pedro, que tenia ojos azules, salio" | Antecedente (Pedro) | Clausula relativa con `acl:relcl` |
| Lista descriptiva | "Ana era alta; Pedro, bajo y de ojos verdes" | Sujeto de cada clausula | Punto y coma como separador de clausulas |
| Gerundio | "Mirandola con sus ojos tristes, Pedro callo" | Sujeto del gerundio (Pedro) | `advcl` con gerundio |
| Participio absoluto | "Cerrados los ojos, Maria escucho" | Sujeto principal (Maria) | `advcl` con participio |

**Experto recomendado**: Linguista computacional con experiencia en parsing de espanol para catalogar estos patrones y verificar que spaCy los etiqueta correctamente.

### Propuesta de implementacion (post-investigacion)

```python
class PossessiveResolver:
    """Resuelve la posesion de atributos usando dependencias spaCy."""

    INSTRUMENTAL_PREPS = {"con"}
    DIRECTIONAL_PREPS = {"a", "hacia"}
    POSSESSIVE_PREPS = {"de"}
    PERCEPTION_VERBS = {"mirar", "observar", "contemplar", "admirar", "ver", "notar"}

    def resolve_owner(self, sentence_doc, body_part_token, entities):
        """
        Determina el dueno de un atributo (body_part) en una oracion parseada.

        Orden de precedencia:
        1. nmod directo (aposicion) → head del nmod
        2. Genitivo "de" → el PROPN con case=de
        3. Instrumental "con" → nsubj del verbo
        4. Direccional "a" + verbo de percepcion → obj del verbo
        5. Reflexivo "se" → nsubj del verbo
        6. Fallback → proximidad (legacy)
        """
        ...
```

### Pros y contras

| Pro | Contra |
|-----|--------|
| Resuelve la clase mas dificil de errores de atribucion | Complejidad alta: integracion spaCy + correferencia |
| Mejora precision de TODOS los atributos, no solo body_parts | "a" polisemico requiere whitelist de verbos |
| spaCy ya da senal suficiente para 3/4 patrones | "sus" ambiguo en 3a persona requiere correferencia |
| El LLM voter puede arbitrar casos dificiles | Performance: parsear con spaCy cada oracion con atributos |

### Plan de implementacion

1. **Fase 1 (investigacion)**: Catalogar funciones de "a" con verbos de percepcion. Evaluar correferencia para "sus" ambiguo.
2. **Fase 2 (implementacion basica)**: `PossessiveResolver` con reglas para `nmod`, `con`, `de`. Sin resolver "a" ambiguo ni "sus" ambiguo.
3. **Fase 3 (integracion)**: Conectar `PossessiveResolver` al `RegexExtractor` como alternativa a `_find_nearest_entity()` cuando spaCy doc esta disponible.
4. **Fase 4 (avanzado)**: Integrar correferencia para resolver "sus" ambiguo. Anadir whitelist de verbos de percepcion para "a" direccional.

---

## 9. Lineas de investigacion avanzada

### 9.1 Atributos negados

**Estado**: No implementado. Los `NEGATION_INDICATORS` existentes DESCARTAN el atributo en vez de marcarlo como negado.

**Propuesta**: Extraer atributos negados para detectar contradicciones:
- "No era rubia" (cap.1) + "su cabello rubio" (cap.3) → **ALERTA**

**Tipos de negacion a distinguir**:

| Tipo | Ejemplo | Extraer | Representacion |
|------|---------|---------|----------------|
| Negacion directa | "No era rubia" | Si | `negated=True` |
| Negacion enfatica | "Nunca habia sido rubia" / "Jamas fue rubia" | Si | `negated=True` |
| Hipotetico/subjuntivo | "Si Maria fuera rubia..." | **No** | Ignorar (contrafactual) |
| Cambio temporal | "Dejo de ser rubia" / "Ya no era rubia" | Si | `temporal_change=True` |

**Modelo de datos**:
```python
@dataclass
class ExtractedAttribute:
    # ... campos existentes ...
    negated: bool = False
    temporal_change: bool = False
```

**Implementacion**:
- Cambiar `NEGATION_INDICATORS` de filtro a marcador
- Anadir deteccion de subjuntivo/condicional (patrones: "si + imperfecto subjuntivo", "como si + subjuntivo")
- El consistency checker compara negated+value contra value directo

**Expertos recomendados**:
- **Linguista**: Catalogar patrones de negacion, hipotetico y cambio temporal en espanol narrativo
- **QA**: Disenar tests con negaciones ambiguas ("Nadie diria que era rubia" — ¿es negacion o afirmacion encubierta?)

**Dificultad**: Media
**Dependencia**: Ninguna

---

### 9.2 Metaforas convencionales → atributos

**Estado**: El filtro de metaforas actual en `RegexExtractor.METAPHOR_INDICATORS` RECHAZA toda metafora. Pero ciertas metaforas literarias convencionales implican atributos:

| Metafora | Inferencia | Confianza |
|----------|-----------|-----------|
| "ojos como lagos/cielo/mar/zafiros" | azules | 0.70 |
| "ojos de esmeralda/jade" | verdes | 0.70 |
| "cabello como fuego/llamas/cobre" | rojo/pelirrojo | 0.70 |
| "piel de porcelana/marfil/alabastro" | palida/blanca | 0.70 |
| "cabello de ebano/azabache/noche" | negro | 0.70 |
| "ojos de miel/ambar" | marrones claros | 0.60 |
| "piel de bronce/canela/chocolate" | morena | 0.60 |

**Propuesta**: Tabla `METAPHOR_TO_ATTRIBUTE` como voter adicional. No como extractor primario, sino como complemento de baja confianza que el sistema de votacion puede confirmar o descartar.

**Distincion clave**: Metaforas convencionales (inferibles) vs creativas (no inferibles):
- Convencional: "ojos como el cielo" → azules (patron cultural estandarizado)
- Creativa: "ojos como dos abismos de soledad" → ¿oscuros? ¿tristes? (interpretacion ambigua)

**Expertos recomendados**:
- **Linguista/Narratologo**: Compilar catalogo de metaforas convencionales en narrativa hispanohablante
- **NLP**: Evaluar si el EmbeddingsExtractor puede distinguir metaforas convencionales vs creativas por similaridad semantica con los valores conocidos

**Dificultad**: Media
**Dependencia**: Ninguna (puede implementarse en paralelo)

---

### 9.3 Fechas a.C. implicitas — propagacion de era

**Estado**: No implementado. El sistema temporal no tiene concepto de "era activa".

**Problema**: En textos historicos, la era (a.C./d.C.) se establece una vez y se sobreentiende:
> "Los romanos fundaron la ciudad en el 753 a.C. Durante los siguientes siglos, el 509 vio la caida de la monarquia, y en el 264 comenzaron las guerras punicas."

Los anos 509 y 264 no llevan "a.C." pero se sobreentienden como a.C. por contexto.

**Heuristica propuesta (a investigar)**:
1. Si un parrafo/capitulo contiene un marcador explicito "a.C.", los anos sueltos que aparezcan despues (sin marcador de era) en el mismo parrafo heredan la era
2. Si TODOS los anos de un capitulo son a.C. explicitos, los anos sueltos heredan a.C.
3. Si el texto habla de civilizaciones antiguas (romanos, griegos, egipcios, mayas) y los anos son < 500, es probable a.C.
4. Si aparece una transicion "a.C." → "d.C." explicita, los anos sueltos despues son d.C.

**Riesgos**:
- Propagar era incorrectamente (un ano d.C. en medio de texto sobre epoca a.C.)
- Generos mixtos: novela que salta entre epocas con y sin a.C.
- Ficcion alternativa: "En el ano 200 del Imperio Galactico" — no es ni a.C. ni d.C.

**Expertos recomendados**:
- **Linguista computacional**: Analizar corpus de textos historicos para validar la heuristica de propagacion
- **Editor de no-ficcion historica**: ¿Es estandar omitir a.C. despues de establecerlo? ¿Que convenciones editoriales existen?

**Dificultad**: Alta
**Dependencia**: XF5 (patrones basicos de a.C.) debe implementarse primero

---

## 10. Tests adversariales propuestos

### Categoria A: Atributos (stress del extractor)

| ID | Test | Trampa | Que reta | Dificultad de implementar |
|----|------|--------|----------|--------------------------|
| A1 | `test_metaphor_conventional_inference` | "ojos como dos lagos" → detectar azules | Inferencia de metaforas convencionales | Media (tabla de metaforas) |
| A2 | `test_negated_attribute` | "No tenia el pelo rubio sino moreno" → extraer moreno, NO rubio | Manejo de negacion con alternativa | Media (patrones de negacion) |
| A3 | `test_hypothetical_not_extracted` | "Si Maria fuera rubia..." → NO extraer atributo | Filtro de subjuntivo/condicional | Media |
| A4 | `test_temporal_attribute_change` | "Antes era morena. Ahora su pelo era blanco." → extraer blanco, detectar cambio | Cambio temporal de atributo | Media |
| A5 | `test_three_entities_one_sentence` | "Ana era alta, Pedro bajo y Lucia de estatura media" → 3 atributos correctos | Disambiguation en lista | Alta (requiere XF4) |
| A6 | `test_possessive_3rd_person` | "Pedro miro a Juan. Sus ojos brillaban" → ambiguo | Coreferencia de posesivos | Alta (requiere correferencia) |

### Categoria B: Spelling (stress del corrector)

| ID | Test | Trampa | Que reta |
|----|------|--------|----------|
| B1 | `test_archaic_spanish` | "Vuestra merced sabra..." | Espanol antiguo/literario |
| B2 | `test_fantasy_proper_names` | "Xylophia camino por Zethara" | Nombres inventados fantasy/sci-fi |
| B3 | `test_code_switching` | "—It's over —dijo Maria" | Cambio de codigo intencional |
| B4 | `test_dialect_words` | "El chamaco se fue pal monte" | Variantes regionales (mexicanismos, etc.) |
| B5 | `test_onomatopoeia` | "¡Brrrum! El motor arranco. ¡Splash!" | Palabras expresivas |

### Categoria C: Temporal (stress de la linea temporal)

| ID | Test | Trampa | Que reta |
|----|------|--------|----------|
| C1 | `test_relative_time_contradiction` | "Tres dias despues" vs "al dia siguiente del evento" | Relativo vs relativo |
| C2 | `test_season_vs_description` | "hojas caian en otono" + "cerezos florecian" (mismo mes) | Estaciones vs naturaleza |
| C3 | `test_age_vs_date_contradiction` | "30 anos en 2020" + "35 anos en 2022" (solo 2 anos pasaron) | Edad vs fecha cruzada |
| C4 | `test_bce_date_ordering` | "En el 44 a.C. murio" + "en el 45 a.C. ya gobernaba" | Orden inverso a.C. |
| C5 | `test_bce_implicit_era` | "En el 753 a.C. se fundo Roma. En el 509 cayo la monarquia" | a.C. implicito |

### Categoria D: Entidades (stress de fusion + NER)

| ID | Test | Trampa | Que reta |
|----|------|--------|----------|
| D1 | `test_same_name_different_person` | "Juan Garcia padre" y "Juan Garcia hijo" | Homonimos — NO fusionar |
| D2 | `test_alias_chain` | "El Profesor" → "Walter White" → "Heisenberg" | Cadena de aliases |
| D3 | `test_gender_no_fusion` | "Francisco" y "Francisca" | Genero distinto — NO fusionar |
| D4 | `test_title_plus_name` | "Dr. Perez", "el doctor Perez", "Perez" | Titulo + nombre — fusionar |

### Categoria E: Consistencia global (stress del pipeline)

| ID | Test | Trampa | Que reta |
|----|------|--------|----------|
| E1 | `test_dead_character_speaks` | Pedro muere cap.3, habla cap.5 | Continuidad vital |
| E2 | `test_object_continuity` | "Perdio la espada" → "Blandio su espada" | Objeto perdido reaparece |
| E3 | `test_relationship_contradiction` | "Ana, hermana de Pedro" vs "Ana, su prima" | Parentesco inconsistente |
| E4 | `test_unreliable_narrator` | Narrador: "ojos azules", personaje: "mis ojos marrones" | Perspectiva conflictiva |

---

## 11. Dependencias entre tareas

```
XF5 (temporal regex) ──────┐
                           ├──→ C4/C5 (tests a.C.)
9.3 (a.C. implicito) ─────┘        ↑
                              requiere investigacion

XF3 (newline filter) → directo, sin dependencias

XF1+XF7 (location) → directo, sin dependencias

XF6 (family) → directo, sin dependencias

XF2 (laterality) → directo, sin dependencias
                    (pero consistency checker necesita soporte extra_data)

XF4 (possessive) ─────────┐
                           ├──→ A5/A6 (tests multi-entity)
9.1 (negated attrs) ──────┤        ↑
                           │  requiere investigacion
9.2 (metaphor table) ─────┘
```

**Orden recomendado de implementacion**:

```
Fase 1 (sin investigacion, 3 items):
  XF5 regex temporal → XF3 newline → XF1+XF7 location

Fase 2 (sin investigacion, 2 items):
  XF6 family → XF2 laterality

Fase 3 (investigacion en paralelo):
  [Investigar] Polisemia de "a", coreferencia de "sus"
  [Investigar] Negacion vs subjuntivo vs cambio temporal
  [Investigar] Metaforas convencionales vs creativas
  [Investigar] Propagacion de era a.C. implicita

Fase 4 (implementacion post-investigacion):
  XF4 possessive → negated attrs → metaphor table → a.C. implicito

Fase 5 (tests adversariales):
  Implementar tests A1-E4 a medida que se completan las fases anteriores
```

---

> **Nota**: Este documento es una hoja de ruta. Las secciones marcadas como "requiere investigacion" deben completarse antes de implementar. Actualizar este documento cuando la investigacion este terminada con los resultados y la decision de implementacion.
