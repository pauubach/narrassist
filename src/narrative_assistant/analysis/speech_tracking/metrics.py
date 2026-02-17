"""
SpeechMetrics - Cálculo de métricas de habla por ventana.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Métricas rastreadas en el sistema
TRACKED_METRICS = [
    "filler_rate",  # Muletillas por 100 palabras
    "formality_score",  # Score de formalidad (0-1)
    "avg_sentence_length",  # Longitud promedio de oración
    "lexical_diversity",  # Type-Token Ratio
    "exclamation_rate",  # Exclamaciones por 100 oraciones
    "question_rate",  # Preguntas por 100 oraciones
]


class SpeechMetrics:
    """
    Calculador de métricas de habla para ventanas temporales.

    Integra con detectores existentes del sistema:
    - FillerDetector: filler_rate
    - VoiceAnalyzer: formality_score
    - spaCy: avg_sentence_length
    - Regex: exclamation_rate, question_rate
    - Básico: lexical_diversity (TTR)
    """

    @staticmethod
    def calculate(
        dialogues: list[str], spacy_nlp=None, use_cache: bool = True
    ) -> dict[str, float]:
        """
        Calcula todas las métricas para una lista de diálogos.

        Args:
            dialogues: Lista de diálogos del personaje
            spacy_nlp: Modelo spaCy (opcional, para ASL)
            use_cache: Si True, usa cache en memoria (default: True)

        Returns:
            Dict con todas las métricas calculadas
        """
        if not dialogues:
            return {metric: 0.0 for metric in TRACKED_METRICS}

        combined_text = " ".join(dialogues)

        # Intentar recuperar del cache
        if use_cache:
            from .cache import get_metrics_cache

            cache = get_metrics_cache()
            cached_metrics = cache.get(combined_text)

            if cached_metrics is not None:
                return cached_metrics

        metrics = {
            "filler_rate": SpeechMetrics._calculate_filler_rate(combined_text),
            "formality_score": SpeechMetrics._calculate_formality(combined_text),
            "avg_sentence_length": SpeechMetrics._calculate_avg_sentence_length(
                combined_text, spacy_nlp
            ),
            "lexical_diversity": SpeechMetrics._calculate_lexical_diversity(
                combined_text
            ),
            "exclamation_rate": SpeechMetrics._calculate_exclamation_rate(
                combined_text
            ),
            "question_rate": SpeechMetrics._calculate_question_rate(combined_text),
        }

        logger.debug(f"Calculated metrics: {metrics}")

        # Guardar en cache
        if use_cache:
            cache.set(combined_text, metrics)

        return metrics

    @staticmethod
    def _calculate_filler_rate(text: str) -> float:
        """
        Calcula tasa de muletillas por 100 palabras.

        Integra con FillerDetector existente.

        Returns:
            Muletillas por 100 palabras (0.0 - 100.0)
        """
        try:
            from ...nlp.style.filler_detector import get_filler_detector

            detector = get_filler_detector()
            result = detector.detect(text, chapter_id=None)

            if result.is_failure:
                logger.debug(f"FillerDetector failed: {result.error}")
                return 0.0

            report = result.value
            word_count = len(text.split())

            if word_count == 0:
                return 0.0

            # Total de muletillas encontradas
            total_fillers = sum(f.count for f in report.fillers)

            # Normalizar a 100 palabras
            filler_rate = (total_fillers / word_count) * 100

            return round(filler_rate, 2)

        except ImportError:
            logger.warning("FillerDetector not available")
            return 0.0
        except Exception as e:
            logger.warning(f"Error calculating filler_rate: {e}")
            return 0.0

    @staticmethod
    def _calculate_formality(text: str) -> float:
        """
        Calcula score de formalidad (0 = coloquial, 1 = formal).

        Integra con VoiceAnalyzer existente.

        Returns:
            Score de formalidad (0.0 - 1.0)
        """
        try:
            from ...analysis.voice import VoiceAnalyzer

            analyzer = VoiceAnalyzer()
            register_result = analyzer.analyze_register(text)

            # Mapear registro a score
            register_scores = {
                "colloquial": 0.1,
                "neutral": 0.5,
                "formal": 0.8,
                "formal_literary": 0.9,
                "technical": 0.85,
                "poetic": 0.75,
                "vulgar": 0.0,
            }

            # Si register_result es un dict
            if isinstance(register_result, dict):
                register = register_result.get("dominant_register", "neutral")
            else:
                register = str(register_result)

            score = register_scores.get(register, 0.5)
            return round(score, 2)

        except ImportError:
            logger.warning("VoiceAnalyzer not available")
            return 0.5  # Default neutral
        except Exception as e:
            logger.warning(f"Error calculating formality: {e}")
            return 0.5

    @staticmethod
    def _calculate_avg_sentence_length(
        text: str, spacy_nlp=None
    ) -> float:
        """
        Calcula longitud promedio de oración en palabras.

        Usa spaCy si está disponible, sino regex básico.

        Returns:
            Promedio de palabras por oración
        """
        if spacy_nlp:
            try:
                doc = spacy_nlp(text)
                sentences = list(doc.sents)

                if not sentences:
                    return 0.0

                total_words = sum(len(sent) for sent in sentences)
                return round(total_words / len(sentences), 2)

            except Exception as e:
                logger.warning(f"spaCy sentence analysis failed: {e}")
                # Fallback a regex

        # Fallback: Regex básico para oraciones
        import re

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        total_words = sum(len(s.split()) for s in sentences)
        return round(total_words / len(sentences), 2)

    @staticmethod
    def _calculate_lexical_diversity(text: str) -> float:
        """
        Calcula Type-Token Ratio (TTR).

        TTR = unique_words / total_words

        Returns:
            TTR (0.0 - 1.0)
        """
        words = text.lower().split()

        if not words:
            return 0.0

        unique_words = set(words)
        ttr = len(unique_words) / len(words)

        return round(ttr, 3)

    @staticmethod
    def _calculate_exclamation_rate(text: str) -> float:
        """
        Calcula tasa de exclamaciones por 100 oraciones.

        Detecta:
        - ¡...! (español)
        - !...! (inglés)

        Returns:
            Exclamaciones por 100 oraciones (0.0 - 100.0)
        """
        # Contar exclamaciones
        exclamation_pattern = r"¡[^!]+!|![^!]+"
        exclamations = re.findall(exclamation_pattern, text)

        # Contar oraciones totales
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        exclamation_rate = (len(exclamations) / len(sentences)) * 100

        return round(exclamation_rate, 2)

    @staticmethod
    def _calculate_question_rate(text: str) -> float:
        """
        Calcula tasa de preguntas por 100 oraciones.

        Detecta:
        - ¿...? (español)
        - ?...? (inglés)

        Returns:
            Preguntas por 100 oraciones (0.0 - 100.0)
        """
        # Contar preguntas
        question_pattern = r"¿[^?]+\?|\?[^?]+"
        questions = re.findall(question_pattern, text)

        # Contar oraciones totales
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        question_rate = (len(questions) / len(sentences)) * 100

        return round(question_rate, 2)
