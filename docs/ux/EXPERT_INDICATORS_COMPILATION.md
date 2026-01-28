# Compilación de Indicadores por Expertos

**Fecha**: 2026-01-28
**Fuente**: Consulta con expertos NLP, Editorial, Lingüística

---

## Resumen Ejecutivo

Se consultaron 4 expertos especializados que proporcionaron:
- **50+ patrones regex** nuevos para mejorar detección
- **Pesos sugeridos** para cada categoría
- **Estrategias de discriminación** entre tipos similares
- **Corpus de prueba** con URLs de libros de dominio público

---

## 1. FICTION (Narrativa) - Mejoras

### Nuevos indicadores propuestos

```python
FICTION_INDICATORS_ENHANCED = {
    # POV markers (acceso a mente de personajes)
    "pov_markers": [
        r'\b(pensó|sintió|supo|comprendió|recordó)\s+que\b',
        r'\bsin\s+saber(lo)?\s+(que|cómo)\b',
        r'\b(se\s+preguntó|se\s+dijo\s+a\s+sí\s+mism[oa])\b',
    ],

    # Descripciones sensoriales inmersivas
    "sensory_immersion": [
        r'\b(olía|olió)\s+a\s+\w+',
        r'\bel\s+(olor|aroma|perfume|hedor)\s+(de|a)\b',
        r'\b(sintió|notó)\s+(el\s+)?(frío|calor|roce|tacto)\b',
        r'\b(la\s+luz|las?\s+sombras?|la\s+penumbra)\s+(de|del|se)\b',
    ],

    # Verbos de movimiento narrativo
    "movement_verbs": [
        r'\b(se\s+abalanzó|se\s+precipitó|irrumpió|huyó)\b',
        r'\b(se\s+encogió\s+de\s+hombros|frunció\s+el\s+ceño|alzó\s+una\s+ceja)\b',
        r'\b(se\s+le\s+heló\s+la\s+sangre|el\s+corazón\s+le\s+latía)\b',
    ],

    # Verbos dicendi expresivos
    "dialogue_verbs": [
        r'(susurró|gruñó|balbuceó|espetó|bramó|gimió)',
        r'(dijo|preguntó),?\s+(mientras|sin|con)\s+\w+',
    ],
}
```

### Pesos sugeridos
| Categoría | Peso | Justificación |
|-----------|------|---------------|
| pov_markers | 2.5 | Alta discriminación (solo ficción accede a mente de otros) |
| sensory_immersion | 1.5 | Construcción de mundo ficcional |
| movement_verbs | 1.5 | Convenciones del género |
| dialogue_verbs | 2.0 | Verbos dicendi expresivos |

---

## 2. MEMOIR (Memorias) - Mejoras

### Nuevos indicadores propuestos

```python
MEMOIR_INDICATORS_ENHANCED = {
    # Marcadores temporales autobiográficos
    "temporal_autobiography": [
        r'\bcuando\s+(cumplí|tenía)\s+\d+\s*años\b',
        r'\ben\s+(mi|nuestra)\s+(infancia|juventud|adolescencia)\b',
        r'\ba\s+los\s+\d+\s*años\b',
        r'\ben\s+(los|la)\s+(años?\s+)?\d{2,4}\b',
    ],

    # Referencias a personas reales
    "real_people_references": [
        r'\bmi\s+(abuel[oa]|tí[oa]|prim[oa]|herman[oa])\b',
        r'\bel\s+tío\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',
        r'\b(don|doña)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',
    ],

    # Metacognición del autor (CLAVE - exclusivo de memoir)
    "author_metacognition": [
        r'\b(ahora\s+(sé|entiendo)|mirando\s+atrás)\b',
        r'\b(no\s+recuerdo\s+(bien|exactamente)|creo\s+que\s+era)\b',
        r'\b(según\s+me\s+(contaron|dijeron))\b',
    ],

    # Verbos de memoria
    "memory_verbs": [
        r'\b(recuerdo|recordaba|rememoro|evoco|añoro)\b',
        r'\b(me\s+viene\s+a\s+la\s+memoria)\b',
    ],
}
```

### Discriminador clave MEMOIR vs FICTION
> La **duda memorística** ("no recuerdo bien", "creo que era") es EXCLUSIVA de memoir. La ficción presenta hechos como ciertos.

---

## 3. BIOGRAPHY (Biografías) - NUEVO

```python
BIOGRAPHY_INDICATORS = {
    # Nacimiento y origen en tercera persona
    "birth_origin": [
        r'\b(nació|nacía)\s+(en|el)\b',
        r'\bvino\s+al\s+mundo\b',
        r'\b(era|fue)\s+(hijo|hija)\s+de\b',
    ],

    # Fuentes y testimonios (CLAVE)
    "sources_testimony": [
        r'\bsegún\s+(testimonios?|fuentes|relatos)\b',
        r'\b(testigos|contemporáneos)\s+(afirman|relatan)\b',
        r'\bsegún\s+(su\s+)?(biógrafo|historiador)\b',
    ],

    # Muerte y legado
    "death_legacy": [
        r'\b(falleció|murió)\s+(en|el|a\s+los)\b',
        r'\bsus\s+últimos\s+(días|años|momentos)\b',
    ],
}
```

### Peso sugerido: sources_testimony = 3.0 (muy discriminativo)

---

## 4. CELEBRITY (Famosos/Influencers) - NUEVO

```python
CELEBRITY_INDICATORS = {
    # Vocabulario de redes sociales
    "social_media_audience": [
        r'\bmis?\s+(seguidores?|followers?|suscriptores?)\b',
        r'\bmi\s+(comunidad|audiencia|público)\b',
        r'\b(Instagram|TikTok|YouTube|Twitter)\b',
    ],

    # Marca personal
    "personal_brand": [
        r'\bmi\s+(marca|proyecto|negocio|emprendimiento)\b',
        r'\b(monetizar|facturar|generar\s+ingresos)\b',
    ],

    # Relación parasocial
    "parasocial_relationship": [
        r'\bustedes\s+(saben|conocen|me\s+conocen)\b',
        r'\b(gracias\s+a\s+ustedes?|sin\s+ustedes?)\b',
    ],
}
```

### Peso sugerido: social_media_audience = 3.0 (exclusivo del género)

---

## 5. DIVULGATION (Divulgación) - NUEVO

```python
DIVULGATION_INDICATORS = {
    # Referencias a estudios
    "study_references": [
        r'(?:un\s+)?(?:estudio|investigación)\s+(?:demuestra|revela|sugiere)',
    ],

    # Científicos como agentes
    "scientist_agents": [
        r'(?:los\s+)?(?:científicos|investigadores)\s+(?:descubrieron|encontraron)',
    ],

    # Datos curiosos
    "curiosity_markers": [
        r'(?:curioso|sorprendente|fascinante)\s+es\s+que',
        r'¿sabías\s+que',
    ],

    # Comparaciones didácticas
    "didactic_comparisons": [
        r'es\s+como\s+si|imagina\s+que|piensa\s+en',
    ],
}
```

---

## 6. PRACTICAL (Libros prácticos) - NUEVO

```python
PRACTICAL_INDICATORS = {
    # Ingredientes con medidas (peso 3.0)
    "ingredients_measures": [
        r'^\s*[-•·]\s*\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cucharada|taza)s?\b',
    ],

    # Pasos numerados
    "numbered_steps": [
        r'^(?:Paso\s+)?\d+[.):]\s+(?:[A-ZÁÉÍÓÚÑ])',
    ],

    # Tiempos de preparación
    "preparation_times": [
        r'tiempo\s+(?:de\s+)?(?:preparación|cocción)\s*[:\-]?\s*\d+\s*(?:min|h)',
    ],

    # Verbos imperativos
    "imperative_verbs": [
        r'^(?:Mezcl[ae]|Bate|Añad[ae]|Hornea|Cocina|Corta|Pela)\b',
    ],
}
```

---

## 7. CHILDREN (Infantil/Juvenil) - NUEVO

```python
CHILDREN_INDICATORS = {
    # Onomatopeyas
    "onomatopoeia": [
        r'\b(?:¡?(?:Pum|Zas|Plop|Crac|Bum|Miau|Guau)!?)\b',
    ],

    # Fórmulas narrativas clásicas (peso 2.8)
    "classic_formulas": [
        r'(?:Había una vez|Érase una vez|colorín colorado)',
    ],

    # Preguntas al lector
    "reader_questions": [
        r'¿(?:Sabes|Puedes|Quieres|Adivina)\s+(?:qué|quién|cómo)',
    ],

    # Repeticiones intencionales
    "intentional_repetitions": [
        r'\b(\w{3,})\s+\1\s+\1\b',  # Repetición triple
    ],
}
```

### Detección de grupo de edad
| Grupo | avg_sentence_length | unique_words |
|-------|---------------------|--------------|
| 0-3 | < 8 | < 200 |
| 3-5 | < 12 | < 500 |
| 5-8 | < 15 | < 1000 |
| 8-12 | < 20 | < 2000 |
| 12+ | >= 15 | sin límite |

---

## 8. DRAMA (Teatro/Guiones) - NUEVO

```python
DRAMA_INDICATORS = {
    # Personaje: diálogo (peso 3.0)
    "character_dialogue": [
        r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,25})\s*[:\.\-—]\s*[A-Za-z]',
    ],

    # Acotaciones escénicas
    "stage_directions": [
        r'\((?:Se\s+levanta|Entra|Sale|Pausa|Silencio)[^)]*\)',
    ],

    # Estructura de actos/escenas (peso 3.0)
    "act_scene_structure": [
        r'^(?:ACTO|ESCENA|CUADRO|JORNADA)\s+(?:[IVXLC]+|\d+)',
    ],

    # Sluglines de cine (peso 3.0)
    "sluglines": [
        r'^(?:INT\.|EXT\.)\s+[A-ZÁÉÍÓÚÑ\s]+\s*[-–—]\s*(?:DÍA|NOCHE)',
    ],

    # Transiciones
    "transitions": [
        r'^(?:FADE\s+(?:IN|OUT)|CORTE\s+A|FUNDIDO)',
    ],
}
```

---

## 9. GRAPHIC (Novela gráfica/Cómic) - NUEVO

```python
GRAPHIC_INDICATORS = {
    # Onomatopeyas mayúsculas (peso 2.5)
    "onomatopoeia_caps": [
        r'\b(?:BOOM|CRASH|BANG|ZAP|POW|KABOOM|WHAM)!?\b',
    ],

    # Acotaciones visuales
    "visual_directions": [
        r'\[(?:viñeta|plano|panel|splash)[^\]]*\]',
    ],

    # Diálogos muy cortos
    "short_dialogues": [
        r'(?:^|\n)\s*[-—]\s*[^.\n]{1,30}[.!?]*\s*(?:\n|$)',
    ],

    # Puntuación enfática
    "emphatic_punctuation": [
        r'[!?]{2,}|[A-ZÁÉÍÓÚÑ]{3,}[!?]+',
    ],
}
```

---

## 10. Corpus de Prueba (Dominio Público)

| Tipo | Título | Fuente | URL |
|------|--------|--------|-----|
| FICTION | Don Quijote | Gutenberg | gutenberg.org/ebooks/2000 |
| FICTION | La Regenta | Wikisource | es.wikisource.org |
| MEMOIR | Recuerdos de mi vida | Archive.org | Ramón y Cajal |
| BIOGRAPHY | Cristóbal Colón | Gutenberg | gutenberg.org/files/61831 |
| ESSAY | Meditaciones del Quijote | Gutenberg | gutenberg.org/files/57448 |
| ESSAY | España invertebrada | Gutenberg | gutenberg.org/files/57982 |
| DIVULGATION | Reglas y consejos | CVC | cvc.cervantes.es/ciencia/cajal |
| PRACTICAL | El Practicón | Archive.org | archive.org (Angel Muro, 1894) |
| CHILDREN | Cuentos de Calleja | Archive.org | Saturnino Calleja |
| DRAMA | Fuenteovejuna | RAE | rae.es (PDF oficial) |
| DRAMA | La vida es sueño | Wikisource | Calderón |

---

## Siguientes pasos

1. [ ] Implementar indicadores en `document_classifier.py`
2. [ ] Crear tests adversariales con corpus
3. [ ] Validar discriminación entre tipos similares
4. [ ] Ajustar pesos según resultados
