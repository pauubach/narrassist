# H4: Voz y Estilo

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia analiza la consistencia estilística: registro, vocabulario, figuración y repeticiones.

**Viabilidad técnica**: MUY ALTA (métricas estadísticas puras, sin LLM)

---

## H4.1 — Consistencia de Registro

### Descripción
El nivel de formalidad, complejidad y tono se mantiene dentro de la misma instancia narrativa.

### Señal
**Media** - Analizable estilométricamente.

### Contexto de aplicación
Dentro de una misma voz narrativa.

### Cuándo NO aplicar
- Cambios de focalización
- Estilo indirecto libre (fusión de voces)
- Evolución intencional de la voz

### Cómo puede fallar
- **Falso positivo**: Variación natural no es inconsistencia
- **Dificultad**: Estilo indirecto libre es difícil de delimitar

### Métricas estilométricas

| Métrica | Descripción | Fórmula/Herramienta |
|---------|-------------|---------------------|
| Longitud oraciones | Palabras por oración | Promedio simple |
| Riqueza léxica | Diversidad de vocabulario | TTR, MATTR |
| Legibilidad | Facilidad de lectura | Fernández-Huerta (español) |
| Distribución POS | % adjetivos, verbos, etc. | spaCy |
| Voz pasiva | Uso de construcciones pasivas | Regex + POS |
| Ratio diálogo/narración | Proporción de texto dialogado | Detección de diálogo |

### Detección de anomalías

Una anomalía se detecta cuando una métrica está a >2σ de la media del documento:

```python
def detect_anomalies(metrics_by_chapter: Dict[int, Metrics]) -> List[Alert]:
    alerts = []
    for metric_name in ['sentence_length', 'lexical_richness', 'adjective_ratio']:
        values = [m[metric_name] for m in metrics_by_chapter.values()]
        mean = statistics.mean(values)
        std = statistics.stdev(values)

        for chapter, metrics in metrics_by_chapter.items():
            deviation = (metrics[metric_name] - mean) / std
            if abs(deviation) > 2.0:
                alerts.append(Alert(
                    type='REGISTER_CHANGE',
                    chapter=chapter,
                    metric=metric_name,
                    deviation=deviation
                ))
    return alerts
```

### Ejemplo de alerta
```
⚠️ CAMBIO BRUSCO DE REGISTRO

Capítulo 5 tiene métricas muy diferentes al resto:

│ Métrica              │ Cap.5    │ Media   │ Desviación │
├──────────────────────┼──────────┼─────────┼────────────┤
│ Long. oraciones      │ 31.2     │ 18.3    │ +3.2σ  ⚠️  │
│ Riqueza léxica       │ 0.89     │ 0.72    │ +2.8σ  ⚠️  │
│ % Adjetivos          │ 14.2%    │ 8.1%    │ +2.4σ  ⚠️  │

¿Es intencional? (ej: cambio de narrador, flashback estilizado)
[Sí, es intencional] [Revisar capítulo] [Ignorar]
```

---

## H4.2 — Adecuación del Vocabulario

### Descripción
El léxico es apropiado para el contexto histórico, social y focal.

### Señal
**Media-alta** - Anacronismos son relativamente objetivos.

### Contexto de aplicación
Siempre.

### Cuándo NO aplicar
- Anacronismo deliberado (sátira, posmodernismo)
- Narradores que usan lenguaje de su tiempo para describir otro

### Cómo puede fallar
- **Falso positivo**: Palabras antiguas que parecen modernas
- **Requiere**: Base de conocimiento histórico-lingüístico

### Implementación básica
Mantener listas de vocabulario por época:
- Palabras que NO existían antes de cierta fecha
- Palabras que eran arcaicas para cierta época

```python
anachronisms = {
    'smartphone': 2007,
    'internet': 1990,
    'televisión': 1930,
    'ordenador': 1960,
    # ...
}

def check_anachronisms(text: str, setting_year: int) -> List[Alert]:
    alerts = []
    for word, first_year in anachronisms.items():
        if word in text.lower() and setting_year < first_year:
            alerts.append(Alert(
                type='ANACHRONISM',
                word=word,
                setting_year=setting_year,
                word_first_year=first_year
            ))
    return alerts
```

---

## H4.3 — Repeticiones Léxicas

### Descripción
Detección de palabras o expresiones que se repiten excesivamente.

### Señal
**Alta** - Detectable automáticamente.

### Tipos de repetición

| Tipo | Descripción | Umbral típico |
|------|-------------|---------------|
| Repetición global | Palabra frecuente en todo el texto | >2σ vs frecuencia esperada |
| Repetición cercana | Misma palabra en párrafos adyacentes | 3+ en 500 palabras |
| Muletilla | Expresión que se repite patrón | Frecuencia anómala |

### Exclusiones
No marcar como repetición:
- Nombres de personajes
- Palabras funcionales (artículos, preposiciones)
- Términos técnicos necesarios

### Ejemplo de alerta
```
⚠️ REPETICIÓN CERCANA

"intensamente" aparece 3 veces en 2 párrafos (pág.89-90)

"...miró intensamente a María. Ella, intensamente emocionada,
respondió con una mirada intensamente cargada de..."

[→ Ir al texto] [Ignorar] [Añadir nota]
```

---

## H4.4 — Repeticiones Semánticas

### Descripción
Detección de conceptos que se expresan de formas diferentes pero cercanas.

### Señal
**Media** - Requiere embeddings para similitud semántica.

### Implementación
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def find_semantic_repetitions(sentences: List[str], threshold: float = 0.85) -> List[Alert]:
    embeddings = model.encode(sentences)
    alerts = []

    for i in range(len(sentences)):
        for j in range(i + 1, min(i + 5, len(sentences))):  # Ventana de 5 oraciones
            similarity = cosine_similarity(embeddings[i], embeddings[j])
            if similarity > threshold:
                alerts.append(Alert(
                    type='SEMANTIC_REPETITION',
                    sentence_1=sentences[i],
                    sentence_2=sentences[j],
                    similarity=similarity
                ))
    return alerts
```

---

## H4.5 — Coherencia de Figuración

### Descripción
Las metáforas y figuras son internamente consistentes y apropiadas al contexto.

### Señal
**Media** - Campos semánticos son rastreables.

### Contexto de aplicación
Pasajes con densidad figurativa.

### Cuándo NO aplicar
- Mezcla deliberada (surrealismo, humor)
- Voz de personaje que hablaría así

### Cómo puede fallar
- **Falso positivo**: Mezclas creativas tomadas como error
- **Dificultad**: Evaluar "calidad" metafórica sin ser prescriptivo

### Nota de implementación
Esta heurística es difícil de automatizar. El sistema puede:
1. Detectar **densidad figurativa** por capítulo
2. Dejar al corrector identificar mezclas problemáticas

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [3.2](../../steps/phase-3/step-3.2-lexical-repetitions.md) | Repeticiones léxicas | H4.3 |
| [3.3](../../steps/phase-3/step-3.3-semantic-repetitions.md) | Repeticiones semánticas | H4.4 |
| [5.1](../../steps/phase-5/step-5.1-voice-profiles.md) | Perfiles voz | H4.1 |
| [5.3](../../steps/phase-5/step-5.3-register-changes.md) | Cambios registro | H4.1 |
| [7.3](../../steps/phase-7/step-7.3-style-guide.md) | Hoja estilo | Todas |

---

## Siguiente

Ver [H5: Focalización](./heuristics-h5-focalization.md).
