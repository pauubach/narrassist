# STEP 8.1: Análisis de Sentimiento

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (8-10 horas) |
| **Prioridad** | P2 (Post-MVP) |
| **Prerequisitos** | STEP 1.4 (Diálogos), STEP 2.1 (Correferencia) |

---

## Descripción

Detectar el sentimiento y estado emocional en textos narrativos, tanto en diálogos de personajes como en la voz del narrador. Esto permite identificar inconsistencias entre el estado emocional declarado y el comportamiento comunicativo.

---

## Motivación

En narrativa, es importante la coherencia emocional-conductual:

- **Personaje enfadado que habla amablemente** → Indica autocontrol, ironía o inconsistencia
- **Personaje triste pero charlatán** → Puede ser nerviosismo o inconsistencia
- **Narrador con tono que no coincide con los hechos** → Voz narrativa inconsistente

---

## Inputs

- Texto de diálogos (STEP 1.4)
- Texto narrativo (párrafos de descripción)
- Atributos emocionales de personajes (STEP 2.3)
- Menciones resueltas (STEP 2.1)

---

## Outputs

- `src/narrative_assistant/nlp/sentiment.py`
- Clasificación de sentimiento por segmento (positivo/negativo/neutro)
- Detección de emociones específicas (alegría, tristeza, enfado, miedo, sorpresa)
- Alertas de inconsistencia emocional-conductual

---

## Modelo Propuesto

### Opción 1: pysentimiento (Recomendado para español)

```python
# Instalación: pip install pysentimiento
from pysentimiento import create_analyzer

# Modelo pre-entrenado en español
sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
emotion_analyzer = create_analyzer(task="emotion", lang="es")

# Análisis
result = sentiment_analyzer.analyze("Estoy muy contento de verte")
# Output: {'output': 'POS', 'probas': {'POS': 0.98, 'NEG': 0.01, 'NEU': 0.01}}

emotions = emotion_analyzer.analyze("Me da mucha rabia esto")
# Output: {'output': 'anger', 'probas': {'anger': 0.85, 'joy': 0.02, ...}}
```

**Ventajas:**
- Modelos BERT entrenados específicamente en español
- Funciona 100% offline después de descarga inicial
- Tareas: sentiment, emotion, hate_speech, irony

### Opción 2: Transformers con modelo local

```python
from transformers import pipeline

# Cargar modelo español de Hugging Face
classifier = pipeline(
    "text-classification",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    device=0  # GPU
)
```

---

## Arquitectura Propuesta

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Emotion(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"

class Sentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

@dataclass
class EmotionalState:
    """Estado emocional detectado en un segmento de texto."""
    text: str
    sentiment: Sentiment
    sentiment_confidence: float
    primary_emotion: Emotion
    emotion_confidence: float
    speaker: Optional[str]  # Personaje que habla (si es diálogo)
    chapter_id: Optional[int]
    start_char: int
    end_char: int

@dataclass
class EmotionalInconsistency:
    """Inconsistencia entre estado emocional declarado y conducta."""
    entity_name: str
    declared_state: str  # "estaba furioso"
    detected_sentiment: Sentiment
    detected_emotion: Emotion
    speech_text: str  # Lo que dijo
    explanation: str
    confidence: float
```

---

## Patrones de Inconsistencia a Detectar

### 1. Estado declarado vs. diálogo

```
Texto: Juan estaba furioso. —Claro, no hay problema —dijo con calma.
Inconsistencia: Estado=furioso, Diálogo=positivo/neutro
```

### 2. Emoción vs. longitud de discurso

```
Texto: María estaba devastada por la muerte de su padre.
       —Bueno, ya sabes cómo son estas cosas. Mi padre siempre decía que...
       [continúa hablando 500 palabras]
Inconsistencia: Tristeza profunda + discurso extenso
```

### 3. Evolución emocional abrupta

```
Cap 1: Juan estaba hundido en la depresión más profunda.
Cap 2 (mismo día): Juan reía a carcajadas con sus amigos.
Inconsistencia: Cambio emocional extremo sin justificación temporal
```

---

## Implementación Básica

```python
class SentimentAnalyzer:
    def __init__(self):
        self._sentiment_model = None
        self._emotion_model = None

    def _load_models(self):
        """Carga modelos (lazy loading)."""
        from pysentimiento import create_analyzer
        self._sentiment_model = create_analyzer(task="sentiment", lang="es")
        self._emotion_model = create_analyzer(task="emotion", lang="es")

    def analyze_dialogue(
        self,
        dialogue_text: str,
        speaker: str,
        context_before: str,
    ) -> EmotionalState:
        """Analiza el sentimiento de un diálogo."""
        if not self._sentiment_model:
            self._load_models()

        sent_result = self._sentiment_model.analyze(dialogue_text)
        emotion_result = self._emotion_model.analyze(dialogue_text)

        return EmotionalState(
            text=dialogue_text,
            sentiment=Sentiment(sent_result['output'].lower()),
            sentiment_confidence=sent_result['probas'][sent_result['output']],
            primary_emotion=Emotion(emotion_result['output']),
            emotion_confidence=emotion_result['probas'][emotion_result['output']],
            speaker=speaker,
            # ...
        )

    def detect_inconsistencies(
        self,
        declared_emotions: list[ExtractedAttribute],
        dialogue_sentiments: list[EmotionalState],
    ) -> list[EmotionalInconsistency]:
        """Detecta inconsistencias entre estado declarado y conducta."""
        # Cruzar emociones declaradas con diálogos cercanos
        # del mismo personaje
        pass
```

---

## Consideraciones

### Offline
- pysentimiento descarga modelos una vez (~500MB)
- Después funciona 100% offline
- Añadir a `scripts/download_models.py`

### Rendimiento
- Procesar por chunks de diálogos
- Cache de resultados por hash de texto
- GPU acelera significativamente

### Limitaciones conocidas
- Ironía/sarcasmo son difíciles de detectar
- Contexto cultural puede afectar interpretación
- Diálogos muy cortos tienen menor precisión

---

## Criterio de DONE

```python
from narrative_assistant.nlp.sentiment import SentimentAnalyzer, Emotion

analyzer = SentimentAnalyzer()

# Test básico
result = analyzer.analyze_dialogue(
    "¡Estoy muy feliz de verte!",
    speaker="Juan",
    context_before=""
)
assert result.sentiment.value == "positive"
assert result.primary_emotion in [Emotion.JOY, Emotion.SURPRISE]

# Test de inconsistencia
# ... (cuando se implemente detect_inconsistencies)

print("✅ Análisis de sentimiento funcionando")
```

---

## Siguiente

[STEP 8.2: Coherencia Emocional](./step-8.2-emotional-coherence.md)
