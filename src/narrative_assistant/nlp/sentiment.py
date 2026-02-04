"""
Análisis de Sentimiento y Emociones.

Detecta el sentimiento y estado emocional en textos narrativos,
tanto en diálogos de personajes como en la voz del narrador.
Permite identificar inconsistencias entre el estado emocional
declarado y el comportamiento comunicativo.

Usa pysentimiento para análisis en español (modelos BERT).
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)

# Lock para lazy loading thread-safe
_lock = threading.Lock()


class Emotion(Enum):
    """Emociones básicas detectables."""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    OTHERS = "others"  # Categoría catch-all de pysentimiento


class Sentiment(Enum):
    """Clasificación de sentimiento general."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# Mapeo de emociones declaradas en español a Emotion
EMOTION_KEYWORDS = {
    Emotion.JOY: [
        "feliz",
        "contento",
        "alegre",
        "dichoso",
        "radiante",
        "eufórico",
        "entusiasmado",
        "encantado",
        "satisfecho",
        "gozoso",
        "jubiloso",
    ],
    Emotion.SADNESS: [
        "triste",
        "deprimido",
        "melancólico",
        "abatido",
        "desolado",
        "devastado",
        "hundido",
        "afligido",
        "apenado",
        "desconsolado",
    ],
    Emotion.ANGER: [
        "furioso",
        "enfadado",
        "enojado",
        "iracundo",
        "rabioso",
        "colérico",
        "indignado",
        "irritado",
        "enfurecido",
        "airado",
        "exasperado",
    ],
    Emotion.FEAR: [
        "asustado",
        "aterrado",
        "temeroso",
        "aterrorizado",
        "espantado",
        "miedoso",
        "horrorizado",
        "alarmado",
        "inquieto",
        "ansioso",
    ],
    Emotion.SURPRISE: [
        "sorprendido",
        "asombrado",
        "estupefacto",
        "atónito",
        "pasmado",
        "perplejo",
        "desconcertado",
        "boquiabierto",
        "impactado",
    ],
    Emotion.DISGUST: ["asqueado", "disgustado", "repugnado", "nauseabundo", "hastiado"],
}

# Mapeo inverso para búsqueda rápida
KEYWORD_TO_EMOTION = {}
for emotion, keywords in EMOTION_KEYWORDS.items():
    for keyword in keywords:
        KEYWORD_TO_EMOTION[keyword] = emotion


@dataclass
class EmotionalState:
    """Estado emocional detectado en un segmento de texto."""

    text: str
    sentiment: Sentiment
    sentiment_confidence: float
    primary_emotion: Emotion
    emotion_confidence: float
    emotion_probabilities: dict[str, float] = field(default_factory=dict)
    speaker: str | None = None
    chapter_id: int | None = None
    start_char: int = 0
    end_char: int = 0


@dataclass
class DeclaredEmotionalState:
    """Estado emocional declarado explícitamente en el texto."""

    entity_name: str
    emotion: Emotion
    emotion_keyword: str  # La palabra exacta encontrada
    context: str  # Fragmento de texto donde se declara
    chapter_id: int | None = None
    position: int = 0


@dataclass
class EmotionalInconsistency:
    """Inconsistencia entre estado emocional declarado y conducta."""

    entity_name: str
    declared_state: DeclaredEmotionalState
    detected_state: EmotionalState
    inconsistency_type: str  # "emotion_dialogue_mismatch", "abrupt_change", etc.
    explanation: str
    confidence: float
    chapter_id: int | None = None
    start_char: int = 0
    end_char: int = 0


class SentimentAnalyzer:
    """
    Analizador de sentimiento y emociones para texto en español.

    Usa pysentimiento con modelos BERT entrenados en español.
    Los modelos se cargan de forma lazy y funcionan 100% offline
    después de la descarga inicial.
    """

    def __init__(self):
        self._sentiment_model = None
        self._emotion_model = None
        self._models_loaded = False
        self._load_error: str | None = None

    @property
    def is_available(self) -> bool:
        """Verifica si pysentimiento está disponible."""
        try:
            import pysentimiento

            return True
        except ImportError:
            return False

    def _load_models(self) -> bool:
        """
        Carga los modelos de pysentimiento (lazy loading).

        Returns:
            True si los modelos se cargaron correctamente.
        """
        if self._models_loaded:
            return True

        if self._load_error:
            return False

        with _lock:
            if self._models_loaded:
                return True

            try:
                from pysentimiento import create_analyzer

                logger.info("Cargando modelos de análisis de sentimiento...")

                # Modelo de sentimiento (POS/NEG/NEU)
                self._sentiment_model = create_analyzer(task="sentiment", lang="es")

                # Modelo de emociones (joy, sadness, anger, fear, surprise, disgust, others)
                self._emotion_model = create_analyzer(task="emotion", lang="es")

                self._models_loaded = True
                logger.info("Modelos de sentimiento cargados correctamente")
                return True

            except ImportError as e:
                self._load_error = f"pysentimiento no instalado: {e}"
                logger.warning(self._load_error)
                return False
            except Exception as e:
                self._load_error = f"Error cargando modelos: {e}"
                logger.error(self._load_error, exc_info=True)
                return False

    def analyze_text(
        self,
        text: str,
        speaker: str | None = None,
        chapter_id: int | None = None,
        start_char: int = 0,
        end_char: int = 0,
    ) -> Result[EmotionalState]:
        """
        Analiza el sentimiento y emociones de un texto.

        Args:
            text: Texto a analizar
            speaker: Nombre del personaje que habla (si es diálogo)
            chapter_id: ID del capítulo
            start_char: Posición inicial en el documento
            end_char: Posición final en el documento

        Returns:
            Result con EmotionalState
        """
        if not text or not text.strip():
            return Result.failure(
                NarrativeError(
                    message="Empty text for sentiment analysis",
                    severity=ErrorSeverity.RECOVERABLE,
                    user_message="Texto vacío para análisis de sentimiento",
                )
            )

        # Intentar cargar modelos
        if not self._load_models():
            # Fallback a análisis basado en reglas
            return self._analyze_with_rules(text, speaker, chapter_id, start_char, end_char)

        try:
            # Análisis con pysentimiento
            sent_result = self._sentiment_model.analyze(text)
            emotion_result = self._emotion_model.analyze(text)

            # Mapear resultados
            sentiment_map = {
                "pos": Sentiment.POSITIVE,
                "neg": Sentiment.NEGATIVE,
                "neu": Sentiment.NEUTRAL,
            }
            sentiment = sentiment_map.get(sent_result.output.lower(), Sentiment.NEUTRAL)
            sentiment_confidence = sent_result.probas.get(sent_result.output, 0.5)

            # Mapear emoción
            emotion_map = {
                "joy": Emotion.JOY,
                "sadness": Emotion.SADNESS,
                "anger": Emotion.ANGER,
                "fear": Emotion.FEAR,
                "surprise": Emotion.SURPRISE,
                "disgust": Emotion.DISGUST,
                "others": Emotion.OTHERS,
            }
            primary_emotion = emotion_map.get(emotion_result.output.lower(), Emotion.NEUTRAL)
            emotion_confidence = emotion_result.probas.get(emotion_result.output, 0.5)

            state = EmotionalState(
                text=text,
                sentiment=sentiment,
                sentiment_confidence=sentiment_confidence,
                primary_emotion=primary_emotion,
                emotion_confidence=emotion_confidence,
                emotion_probabilities=dict(emotion_result.probas),
                speaker=speaker,
                chapter_id=chapter_id,
                start_char=start_char,
                end_char=end_char or start_char + len(text),
            )

            return Result.success(state)

        except Exception as e:
            logger.error(f"Error en análisis de sentimiento: {e}", exc_info=True)
            return Result.failure(
                NarrativeError(
                    message=f"Sentiment analysis failed: {e}",
                    severity=ErrorSeverity.RECOVERABLE,
                    user_message=f"Error en análisis de sentimiento: {e}",
                )
            )

    def _analyze_with_rules(
        self,
        text: str,
        speaker: str | None,
        chapter_id: int | None,
        start_char: int,
        end_char: int,
    ) -> Result[EmotionalState]:
        """
        Análisis de sentimiento basado en reglas (fallback).

        Menos preciso que pysentimiento pero funciona sin dependencias.
        """
        text_lower = text.lower()

        # Palabras positivas/negativas básicas
        positive_words = [
            "feliz",
            "contento",
            "alegre",
            "bien",
            "encantado",
            "gracias",
            "perfecto",
            "maravilloso",
            "excelente",
            "genial",
            "fantástico",
            "amor",
            "cariño",
            "querido",
            "dulce",
            "bonito",
            "hermoso",
        ]
        negative_words = [
            "triste",
            "mal",
            "enfadado",
            "furioso",
            "odio",
            "terrible",
            "horrible",
            "espantoso",
            "miedo",
            "temor",
            "dolor",
            "sufrir",
            "morir",
            "muerte",
            "llorar",
            "lágrimas",
            "fracaso",
            "culpa",
        ]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            sentiment = Sentiment.POSITIVE
            primary_emotion = Emotion.JOY
        elif neg_count > pos_count:
            sentiment = Sentiment.NEGATIVE
            # Intentar determinar emoción negativa específica
            primary_emotion = Emotion.SADNESS
            for emotion, keywords in EMOTION_KEYWORDS.items():
                if emotion in [Emotion.ANGER, Emotion.FEAR, Emotion.SADNESS]:
                    if any(kw in text_lower for kw in keywords):
                        primary_emotion = emotion
                        break
        else:
            sentiment = Sentiment.NEUTRAL
            primary_emotion = Emotion.NEUTRAL

        # Confianza baja para análisis basado en reglas
        confidence = 0.5

        state = EmotionalState(
            text=text,
            sentiment=sentiment,
            sentiment_confidence=confidence,
            primary_emotion=primary_emotion,
            emotion_confidence=confidence,
            emotion_probabilities={},
            speaker=speaker,
            chapter_id=chapter_id,
            start_char=start_char,
            end_char=end_char or start_char + len(text),
        )

        return Result.success(state)

    def analyze_dialogue(
        self,
        dialogue_text: str,
        speaker: str,
        context_before: str = "",
        chapter_id: int | None = None,
        start_char: int = 0,
        end_char: int = 0,
    ) -> Result[EmotionalState]:
        """
        Analiza el sentimiento de un diálogo específico.

        Args:
            dialogue_text: Texto del diálogo
            speaker: Nombre del personaje que habla
            context_before: Texto previo al diálogo (para contexto)
            chapter_id: ID del capítulo
            start_char: Posición inicial
            end_char: Posición final

        Returns:
            Result con EmotionalState
        """
        return self.analyze_text(
            text=dialogue_text,
            speaker=speaker,
            chapter_id=chapter_id,
            start_char=start_char,
            end_char=end_char,
        )

    def extract_declared_emotions(
        self,
        text: str,
        entity_names: list[str],
        chapter_id: int | None = None,
    ) -> list[DeclaredEmotionalState]:
        """
        Extrae estados emocionales declarados explícitamente en el texto.

        Busca patrones como "Juan estaba furioso" o "María, triste, dijo..."

        Args:
            text: Texto a analizar
            entity_names: Lista de nombres de entidades a buscar
            chapter_id: ID del capítulo

        Returns:
            Lista de estados emocionales declarados
        """
        declared_states = []
        text_lower = text.lower()

        # Patrones de estado emocional
        patterns = [
            # "Juan estaba furioso"
            r"(\w+)\s+estaba\s+(\w+)",
            # "la furiosa María"
            r"(?:el|la)\s+(\w+)\s+(\w+)",
            # "Juan, furioso, dijo"
            r"(\w+),?\s+(\w+),?\s+(?:dijo|respondió|exclamó|gritó)",
            # "sintiéndose furioso, Juan"
            r"sintiéndose\s+(\w+),?\s+(\w+)",
        ]

        for entity_name in entity_names:
            entity_lower = entity_name.lower()

            for pattern in patterns:
                for match in re.finditer(pattern, text_lower):
                    groups = match.groups()

                    # Verificar si la entidad está en el match
                    matched_name = None
                    emotion_word = None

                    for group in groups:
                        if group == entity_lower or entity_lower in group:
                            matched_name = entity_name
                        elif group in KEYWORD_TO_EMOTION:
                            emotion_word = group

                    if matched_name and emotion_word:
                        emotion = KEYWORD_TO_EMOTION[emotion_word]

                        # Extraer contexto
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end]

                        declared_states.append(
                            DeclaredEmotionalState(
                                entity_name=matched_name,
                                emotion=emotion,
                                emotion_keyword=emotion_word,
                                context=context,
                                chapter_id=chapter_id,
                                position=match.start(),
                            )
                        )

        return declared_states

    def detect_inconsistencies(
        self,
        declared_states: list[DeclaredEmotionalState],
        dialogue_states: list[EmotionalState],
        proximity_chars: int = 500,
    ) -> list[EmotionalInconsistency]:
        """
        Detecta inconsistencias entre estados emocionales declarados y conducta.

        Args:
            declared_states: Estados emocionales declarados en el texto
            dialogue_states: Sentimientos detectados en diálogos
            proximity_chars: Máxima distancia en caracteres para considerar relación

        Returns:
            Lista de inconsistencias detectadas
        """
        inconsistencies = []

        # Mapeo de emociones a sentimientos esperados
        emotion_to_expected_sentiment = {
            Emotion.JOY: Sentiment.POSITIVE,
            Emotion.SADNESS: Sentiment.NEGATIVE,
            Emotion.ANGER: Sentiment.NEGATIVE,
            Emotion.FEAR: Sentiment.NEGATIVE,
            Emotion.SURPRISE: Sentiment.NEUTRAL,  # Puede ser positivo o negativo
            Emotion.DISGUST: Sentiment.NEGATIVE,
        }

        for declared in declared_states:
            # Buscar diálogos cercanos del mismo personaje
            for dialogue in dialogue_states:
                # Verificar mismo personaje
                if dialogue.speaker and dialogue.speaker.lower() != declared.entity_name.lower():
                    continue

                # Verificar mismo capítulo
                if declared.chapter_id and dialogue.chapter_id:
                    if declared.chapter_id != dialogue.chapter_id:
                        continue

                # Verificar proximidad
                distance = abs(dialogue.start_char - declared.position)
                if distance > proximity_chars:
                    continue

                # Verificar inconsistencia
                emotion_to_expected_sentiment.get(declared.emotion, Sentiment.NEUTRAL)

                # Inconsistencia: emoción negativa declarada pero diálogo positivo
                is_inconsistent = False
                explanation = ""

                if declared.emotion in [Emotion.ANGER, Emotion.SADNESS, Emotion.FEAR]:
                    if dialogue.sentiment == Sentiment.POSITIVE:
                        is_inconsistent = True
                        explanation = (
                            f"{declared.entity_name} está descrito como '{declared.emotion_keyword}', "
                            f"pero su diálogo tiene un tono {dialogue.sentiment.value}. "
                            f"Esto podría indicar autocontrol, ironía, o una inconsistencia."
                        )

                elif declared.emotion == Emotion.JOY:
                    if dialogue.sentiment == Sentiment.NEGATIVE:
                        is_inconsistent = True
                        explanation = (
                            f"{declared.entity_name} está descrito como '{declared.emotion_keyword}', "
                            f"pero su diálogo tiene un tono {dialogue.sentiment.value}. "
                            f"Esto podría ser sarcasmo o una inconsistencia."
                        )

                if is_inconsistent and dialogue.sentiment_confidence > 0.6:
                    # Calcular confianza de la inconsistencia
                    confidence = min(dialogue.sentiment_confidence, 0.8)

                    inconsistencies.append(
                        EmotionalInconsistency(
                            entity_name=declared.entity_name,
                            declared_state=declared,
                            detected_state=dialogue,
                            inconsistency_type="emotion_dialogue_mismatch",
                            explanation=explanation,
                            confidence=confidence,
                            chapter_id=declared.chapter_id,
                            start_char=min(declared.position, dialogue.start_char),
                            end_char=max(declared.position, dialogue.end_char),
                        )
                    )

        return inconsistencies

    def analyze_emotional_arc(
        self,
        dialogue_states: list[EmotionalState],
        entity_name: str,
    ) -> list[EmotionalInconsistency]:
        """
        Analiza el arco emocional de un personaje buscando cambios abruptos.

        Args:
            dialogue_states: Lista de estados emocionales de diálogos
            entity_name: Nombre del personaje

        Returns:
            Lista de inconsistencias por cambios abruptos
        """
        inconsistencies = []

        # Filtrar diálogos del personaje y ordenar por posición
        entity_dialogues = sorted(
            [d for d in dialogue_states if d.speaker and d.speaker.lower() == entity_name.lower()],
            key=lambda x: (x.chapter_id or 0, x.start_char),
        )

        if len(entity_dialogues) < 2:
            return inconsistencies

        # Buscar cambios emocionales abruptos
        for i in range(1, len(entity_dialogues)):
            prev = entity_dialogues[i - 1]
            curr = entity_dialogues[i]

            # Mismo capítulo y cambio de sentimiento extremo
            if prev.chapter_id == curr.chapter_id:
                # De muy positivo a muy negativo o viceversa
                if (
                    prev.sentiment == Sentiment.POSITIVE
                    and curr.sentiment == Sentiment.NEGATIVE
                    and prev.sentiment_confidence > 0.7
                    and curr.sentiment_confidence > 0.7
                ):
                    # Verificar que no haya mucha distancia
                    if curr.start_char - prev.end_char < 2000:
                        inconsistencies.append(
                            EmotionalInconsistency(
                                entity_name=entity_name,
                                declared_state=DeclaredEmotionalState(
                                    entity_name=entity_name,
                                    emotion=prev.primary_emotion,
                                    emotion_keyword=prev.sentiment.value,
                                    context=prev.text[:100],
                                    chapter_id=prev.chapter_id,
                                    position=prev.start_char,
                                ),
                                detected_state=curr,
                                inconsistency_type="abrupt_emotional_change",
                                explanation=(
                                    f"{entity_name} pasa de un estado emocional "
                                    f"{prev.sentiment.value} ({prev.primary_emotion.value}) "
                                    f"a {curr.sentiment.value} ({curr.primary_emotion.value}) "
                                    f"de forma abrupta sin transición aparente."
                                ),
                                confidence=min(
                                    prev.sentiment_confidence, curr.sentiment_confidence
                                ),
                                chapter_id=curr.chapter_id,
                                start_char=prev.start_char,
                                end_char=curr.end_char,
                            )
                        )

        return inconsistencies


# Singleton
_analyzer_instance: SentimentAnalyzer | None = None
_analyzer_lock = threading.Lock()


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Obtiene la instancia singleton del analizador de sentimiento."""
    global _analyzer_instance
    if _analyzer_instance is None:
        with _analyzer_lock:
            if _analyzer_instance is None:
                _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance
