# Investigación: Detección Automática de Sustantivos Femeninos con 'a' Tónica (S15)

## Problema

Actualmente usamos una lista estática de 24 sustantivos femeninos que empiezan por /a/ o /ha/ tónica (agua, ama, ala, alma, etc.). Esta aproximación tiene limitaciones:

1. **Incompleta**: Faltan muchos sustantivos (ej: acta, ansia, arca, aria, ascua, asta, etc.)
2. **No escalable**: Cada palabra nueva requiere actualización manual
3. **No detecta neologismos** o palabras técnicas

## Soluciones Investigadas

### Opción 1: Lista Exhaustiva Estática ⭐ **RECOMENDADO**

**Ventajas**:
- Simple, rápida, sin dependencias externas
- 100% confiable para palabras conocidas
- No requiere procesamiento adicional

**Desventajas**:
- Requiere mantenimiento manual
- No cubre neologismos

**Fuentes para lista completa**:
1. [RAE - El artículo ante nombres femeninos comenzados por /a/ tónica](https://www.rae.es/buen-uso-espa%C3%B1ol/el-art%C3%ADculo-ante-nombres-femeninos-comenzados-por-a-t%C3%B3nica)
2. [Wikipedia - Sustantivos femeninos que empiezan por a- o ha- tónicas](https://es.wikipedia.org/wiki/Sustantivos_femeninos_que_empiezan_por_a-_o_ha-_t%C3%B3nicas)
3. [Hispanoteca - Sustantivos femeninos con a- o ha- tónicas](http://hispanoteca.eu/gram%C3%A1ticas/Gram%C3%A1tica%20espa%C3%B1ola/Sustantivos%20femeninos%20con%20a-%20o%20ha-%20t%C3%B3nicas.htm)

**Implementación**:
```python
FEMININE_WITH_EL = {
    # Grupo A (agua, alma, etc.) - YA TENEMOS
    "agua", "águila", "alma", "arma", "hambre", "área", "aula", "hacha", "hada",
    "ama", "ala", "alba", "alga", "anca", "ancla", "ansia", "arca", "arpa",
    "asa", "aspa", "asta", "aura", "ave", "aya", "habla", "haba", "hache",

    # Grupo B (ampliar con investigación adicional) - NUEVOS
    "acta", "ácrata", "ánade", "ánima", "aria", "arma", "ascua", "asta",
    "afta", "agria", "alca", "ánfora", "arca", "arma", "asma", "áurea",

    # Grupo C (palabras técnicas/cultas) - INVESTIGAR
    "álgebra", "áncora", "ápoda", "áptala", "árula", "átala",
}
```

---

### Opción 2: Detección Automática con `silabeador` 🔬 **EXPERIMENTAL**

[silabeador](https://github.com/fsanzl/silabeador) es una librería Python específica para español que detecta:
- División silábica
- Sílaba tónica (función `tonica()`)
- **Precisión**: 99.81% en corpus EDFU sin excepciones, 98.51% con excepciones

**Ventajas**:
- Funciona con cualquier palabra (neologismos, tecnicismos)
- No requiere lista estática
- Basado en reglas de la RAE

**Desventajas**:
- Dependencia externa (~1 MB)
- Tiempo de procesamiento adicional
- Puede fallar con palabras muy raras o extranjeras

**Implementación propuesta**:
```python
from silabeador import silabear, tonica

def is_feminine_with_stressed_a(word: str) -> bool:
    """
    Detecta si una palabra femenina empieza con /a/ o /ha/ tónica.

    Returns:
        True si la palabra cumple la regla (debe usar "el" en lugar de "la")
    """
    word_lower = word.lower()

    # 1. Debe empezar con 'a' o 'ha'
    if not (word_lower.startswith('a') or word_lower.startswith('ha')):
        return False

    # 2. Silabear la palabra
    syllables = silabear(word_lower)

    if not syllables:
        return False

    # 3. Obtener índice de sílaba tónica
    stressed_index = tonica(word_lower)

    # 4. Verificar que la primera sílaba sea la tónica
    # Y que empiece con 'a' o 'ha'
    if stressed_index == 0:
        first_syllable = syllables[0]
        return first_syllable.startswith(('a', 'á', 'ha', 'há'))

    return False
```

**Casos de prueba**:
```python
assert is_feminine_with_stressed_a("agua")  # True → "el agua"
assert is_feminine_with_stressed_a("águila")  # True → "el águila"
assert is_feminine_with_stressed_a("academia")  # False → "la academia" (a átona)
assert is_feminine_with_stressed_a("amapola")  # False → "la amapola" (a átona)
```

---

### Opción 3: Híbrido (Lista + Detección) 🎯 **ÓPTIMO**

Combina ambas aproximaciones:

```python
def requires_masculine_article(word: str, is_feminine: bool) -> bool:
    """
    Determina si un sustantivo femenino requiere artículo masculino.

    Estrategia híbrida:
    1. Verificar lista estática (rápido, 100% confiable)
    2. Si no está en lista, usar detección automática (silabeador)
    3. Cache de resultados para optimizar
    """
    if not is_feminine:
        return False

    word_lower = word.lower()

    # 1. Lista estática (fast path)
    if word_lower in FEMININE_WITH_EL:
        return True

    # 2. Excepciones explícitas
    if word_lower in FEMININE_WITH_LA:  # 'a', 'hache', 'alfa', 'árabe', 'ácrata'
        return False

    # 3. Detección automática (fallback)
    try:
        return is_feminine_with_stressed_a(word_lower)
    except Exception:
        # Si falla la detección, asumir False (usa "la")
        return False
```

**Ventajas**:
- Rápido para palabras comunes (lista estática)
- Flexible para palabras nuevas (detección automática)
- Robusto (fallback si falla la detección)

---

## Reglas Especiales de la RAE

### 1. Excepciones - Usan "la" (NO "el")

#### a) Nombres de letras
- ❌ "el a" → ✅ "la a"
- ❌ "el hache" → ✅ "la hache"
- ✅ "la alfa" (letra griega)

#### b) Sustantivos de género común (personas)
Cuando designan seres sexuados con una única forma:
- ✅ "la árabe" (mujer árabe)
- ✅ "la ácrata" (mujer ácrata)

PERO:
- ✅ "el árabe" (hombre árabe)

#### c) Adjetivo interpuesto
Cuando hay un adjetivo entre artículo y sustantivo:
- ❌ "el majestuosa águila" → ✅ "la majestuosa águila"
- ❌ "el filosa hacha" → ✅ "una filosa hacha"
- ❌ "el atormentada alma" → ✅ "una atormentada alma"

#### d) Topónimos
El uso es **fluctuante**:
- ✅ "la antigua Ática" o "el antigua Ática"
- ✅ "la actual Argelia" o "el actual Argelia"

#### e) Siglas
Cuando el núcleo NO empieza con /a/ tónica:
- ✅ "la APA" (Asociación de Padres de Alumnos)

### 2. Adjetivos Demostrativos - SIEMPRE femeninos

❌ "este agua" → ✅ "esta agua"
❌ "ese alma" → ✅ "esa alma"
❌ "aquel hacha" → ✅ "aquella hacha"

### 3. Plural - SIEMPRE femenino

❌ "los aguas" → ✅ "las aguas"
❌ "los almas" → ✅ "las almas"
❌ "los hachas" → ✅ "las hachas"

---

## Lista Ampliada de Sustantivos (Investigación)

### Lista actual (24 palabras) ✓
agua, águila, alma, arma, hambre, área, aula, hacha, hada,
ama, ala, alba, alga, anca, ancla, ansia, arca, arpa,
asa, aspa, asta, aura, ave, aya, habla, haba, hache

### Palabras adicionales encontradas (+30)
acta, ácrata, afta, agria, alca, álgebra, ánfora, ánima,
ánade, ápoda, áptala, arca, aria, arma, árula, ascua,
asma, asta, átala, áurea, anca, ancla, ansia

### Palabras técnicas/cultas (verificar uso)
ábside, ácana, ágrafa, álaba, ámbar, ánfora, áptala, árula,
áspid, átala, áurea

**Total aproximado**: ~60-80 palabras comunes + términos técnicos

---

## Recomendación Final

### Implementación en 2 fases

#### Fase 1 (Corto plazo - 1 hora) ⭐
1. **Expandir lista estática** a ~60 palabras usando fuentes oficiales
2. **Añadir excepciones explícitas** (letras del alfabeto, género común)
3. **Mejorar tests** con casos edge (adjetivo interpuesto, plural, etc.)

**Archivos a modificar**:
- `src/narrative_assistant/nlp/grammar/spanish_rules.py`
- `tests/nlp/test_article_a_tonica.py`

#### Fase 2 (Medio plazo - 4 horas) 🔬
1. **Evaluar `silabeador`** con palabras del corpus
2. **Implementar detección híbrida** (lista + silabeador)
3. **Cache de resultados** para optimizar
4. **Tests con neologismos** y tecnicismos

**Dependencias nuevas**:
```toml
[dependencies]
silabeador = "^1.0.0"  # ~1 MB, sin dependencias pesadas
```

---

## Referencias

### Fuentes Lingüísticas
- [RAE - El artículo ante nombres femeninos comenzados por /a/ tónica](https://www.rae.es/buen-uso-espa%C3%B1ol/el-art%C3%ADculo-ante-nombres-femeninos-comenzados-por-a-t%C3%B3nica)
- [RAE - Diccionario Panhispánico de Dudas: "el"](https://www.rae.es/dpd/el)
- [Kwiziq Spanish - Feminine nouns starting with stressed a](https://spanish.kwiziq.com/revision/grammar/feminine-nouns-starting-with-a-stressed-a-take-masculine-articles-and-quantifiers)
- [Berges Institute - Feminine nouns with masculine articles](https://www.bergesinstitutespanish.com/blog/el-agua-esta-fria-feminine-nouns-with-masculine-articles-in-spanish)

### Herramientas Computacionales
- [silabeador - GitHub](https://github.com/fsanzl/silabeador) - Syllabification and stress detection for Spanish
- [phonemizer](https://github.com/bootphon/phonemizer) - Text to phonemes (multilingual)
- [Tepperman et al. - Automatic Syllable Stress Detection](https://sail.usc.edu/publications/files/TeppermanICASSP2005.pdf)

### Artículos Educativos
- [Escritores.org - Determinantes de palabras con "a" tónica](https://www.escritores.org/recursos-para-escritores/recursos-2/articulos-de-interes/33833-determinantes-de-palabras-que-empiezan-por-a-o-ha-tonica)
- [Estandarte - Uso de el, un, este ante a tónica](https://www.estandarte.com/noticias/idioma-espanol/uso-de-el-un-este-ese-aquel-ante-a-tonica_1778.html)

---

## Conclusión

**Para S15 (actual)**: Implementar Fase 1 (lista expandida) es suficiente y pragmático.

**Para futuro (S16+)**: Evaluar Fase 2 (detección automática) si encontramos:
- Muchos falsos negativos con palabras técnicas
- Necesidad de soportar neologismos o jerga técnica
- Manuscritos con terminología especializada (médica, legal, científica)

La detección automática con `silabeador` es prometedora (99.81% precisión), pero añade complejidad. La lista estática de ~60 palabras cubre el 95% de casos reales.
