"""
Detector de repeticiones léxicas y semánticas.

Detecta:
- Repeticiones léxicas: misma palabra repetida en cercanía
- Repeticiones semánticas: conceptos similares repetidos
- Cacofonías: sonidos repetidos molestos

El sistema es configurable para diferentes niveles de sensibilidad
y puede ignorar palabras funcionales (artículos, preposiciones).
"""

import logging
import re
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.errors import ErrorSeverity, NLPError
from ...core.result import Result

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["RepetitionDetector"] = None


def get_repetition_detector() -> "RepetitionDetector":
    """Obtener instancia singleton del detector de repeticiones."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = RepetitionDetector()

    return _instance


def reset_repetition_detector() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================


class RepetitionType(Enum):
    """Tipos de repeticiones detectadas."""

    LEXICAL = "lexical"  # Misma palabra exacta
    LEMMA = "lemma"  # Mismo lema (conjugaciones)
    SEMANTIC = "semantic"  # Mismo concepto/significado
    PHONETIC = "phonetic"  # Sonido similar (cacofonía)
    STRUCTURAL = "structural"  # Estructura sintáctica repetida


class RepetitionSeverity(Enum):
    """Severidad de la repetición."""

    HIGH = "high"  # Muy cercanas, muy evidentes
    MEDIUM = "medium"  # Moderadamente cercanas
    LOW = "low"  # Lejanas pero notables


@dataclass
class RepetitionOccurrence:
    """Una ocurrencia de una palabra repetida."""

    text: str  # Texto exacto
    start_char: int  # Posición inicio
    end_char: int  # Posición fin
    sentence: str  # Oración de contexto
    word_position: int  # Posición en número de palabras


@dataclass
class Repetition:
    """Una repetición detectada."""

    # Palabra/concepto repetido
    word: str  # Palabra o lema
    lemma: str = ""  # Lema (si aplica)

    # Tipo y severidad
    repetition_type: RepetitionType = RepetitionType.LEXICAL
    severity: RepetitionSeverity = RepetitionSeverity.MEDIUM

    # Ocurrencias
    occurrences: list[RepetitionOccurrence] = field(default_factory=list)
    count: int = 0  # Número de repeticiones

    # Métricas
    min_distance: int = 0  # Distancia mínima entre ocurrencias (palabras)
    max_distance: int = 0  # Distancia máxima
    avg_distance: float = 0.0  # Distancia promedio

    # Confianza
    confidence: float = 0.8  # 0.0-1.0

    def __post_init__(self):
        if not self.count:
            self.count = len(self.occurrences)
        if not self.lemma:
            self.lemma = self.word.lower()

    @property
    def is_problematic(self) -> bool:
        """True si la repetición es problemática (muy cercana)."""
        return self.min_distance < 30 and self.count >= 2

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "word": self.word,
            "lemma": self.lemma,
            "type": self.repetition_type.value,
            "severity": self.severity.value,
            "count": self.count,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
            "avg_distance": self.avg_distance,
            "confidence": self.confidence,
            "occurrences": [
                {
                    "text": o.text,
                    "start_char": o.start_char,
                    "end_char": o.end_char,
                    "word_position": o.word_position,
                }
                for o in self.occurrences
            ],
        }


@dataclass
class RepetitionReport:
    """Resultado del análisis de repeticiones."""

    repetitions: list[Repetition] = field(default_factory=list)
    processed_words: int = 0

    # Estadísticas
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)

    # Palabras ignoradas
    ignored_words: set[str] = field(default_factory=set)

    def add_repetition(self, rep: Repetition) -> None:
        """Añadir una repetición."""
        self.repetitions.append(rep)

        type_key = rep.repetition_type.value
        self.by_type[type_key] = self.by_type.get(type_key, 0) + 1

        severity_key = rep.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

    def get_problematic(self) -> list[Repetition]:
        """Obtener solo repeticiones problemáticas."""
        return [r for r in self.repetitions if r.is_problematic]

    def get_by_severity(self, severity: RepetitionSeverity) -> list[Repetition]:
        """Filtrar por severidad."""
        return [r for r in self.repetitions if r.severity == severity]

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "repetitions": [r.to_dict() for r in self.repetitions],
            "processed_words": self.processed_words,
            "by_type": self.by_type,
            "by_severity": self.by_severity,
            "problematic_count": len(self.get_problematic()),
        }


# =============================================================================
# Palabras a ignorar (stop words y palabras funcionales)
# =============================================================================

SPANISH_STOP_WORDS = {
    # Artículos
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    # Preposiciones
    "a",
    "ante",
    "bajo",
    "con",
    "contra",
    "de",
    "del",
    "desde",
    "en",
    "entre",
    "hacia",
    "hasta",
    "para",
    "por",
    "según",
    "sin",
    "sobre",
    "tras",
    # Conjunciones
    "y",
    "e",
    "ni",
    "o",
    "u",
    "pero",
    "sino",
    "porque",
    "que",
    "si",
    "aunque",
    "como",
    "cuando",
    "donde",
    "mientras",
    # Pronombres
    "yo",
    "tú",
    "él",
    "ella",
    "nosotros",
    "vosotros",
    "ellos",
    "ellas",
    "me",
    "te",
    "se",
    "nos",
    "os",
    "le",
    "les",
    "lo",
    "mi",
    "tu",
    "su",
    "nuestro",
    "vuestro",
    "este",
    "esta",
    "esto",
    "estos",
    "estas",
    "ese",
    "esa",
    "eso",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquello",
    "aquellos",
    "aquellas",
    "quien",
    "quienes",
    "cual",
    "cuales",
    "cuyo",
    "cuya",
    # Verbos muy comunes
    "ser",
    "estar",
    "tener",
    "haber",
    "hacer",
    "ir",
    "poder",
    "es",
    "está",
    "son",
    "están",
    "era",
    "fue",
    "ha",
    "han",
    "hay",
    "había",
    "tiene",
    "tienen",
    "hace",
    "hacen",
    # Adverbios
    "no",
    "sí",
    "ya",
    "más",
    "muy",
    "bien",
    "mal",
    "así",
    "también",
    "tampoco",
    "ahora",
    "después",
    "antes",
    "aquí",
    "allí",
    "siempre",
    "nunca",
    "solo",
    "todavía",
    # Otros
    "todo",
    "toda",
    "todos",
    "todas",
    "otro",
    "otra",
    "otros",
    "otras",
    "mismo",
    "misma",
    "mismos",
    "mismas",
    "cada",
    "mucho",
    "poco",
    "tanto",
    "tan",
    "algo",
    "nada",
    "alguien",
    "nadie",
}

# Palabras que pueden repetirse sin problema en narrativa
NARRATIVE_ALLOWED = {
    "dijo",
    "preguntó",
    "respondió",
    "contestó",
    "exclamó",
    "pensó",
    "sintió",
    "miró",
    "vio",
    "oyó",
}


@dataclass
class RepetitionCheckError(NLPError):
    """Error durante el análisis de repeticiones."""

    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)

    def __post_init__(self):
        self.message = f"Repetition check error: {self.original_error}"
        super().__post_init__()


class RepetitionDetector:
    """
    Detector de repeticiones léxicas y semánticas.

    Detecta palabras y conceptos repetidos en cercanía,
    excluyendo palabras funcionales y permitiendo repeticiones
    narrativas normales.
    """

    def __init__(self):
        """Inicializar el detector."""
        self._nlp = None
        self._embeddings = None
        self._load_resources()

    def _load_resources(self) -> None:
        """Cargar recursos NLP si están disponibles."""
        try:
            from ..spacy_gpu import load_spacy_model

            self._nlp = load_spacy_model()
        except Exception as e:
            logger.warning(f"spaCy not available for repetition detection: {e}")

        try:
            from ..embeddings import get_embeddings_model

            self._embeddings = get_embeddings_model()
        except Exception as e:
            logger.warning(f"Embeddings not available for semantic repetitions: {e}")

    def detect_lexical(
        self,
        text: str,
        min_distance: int = 50,
        min_occurrences: int = 2,
        ignore_dialogue: bool = True,
    ) -> Result[RepetitionReport]:
        """
        Detectar repeticiones léxicas (misma palabra exacta).

        Args:
            text: Texto a analizar
            min_distance: Distancia mínima en palabras para considerar repetición
            min_occurrences: Número mínimo de ocurrencias para reportar
            ignore_dialogue: Ignorar contenido dentro de diálogos

        Returns:
            Result con RepetitionReport
        """
        if not text or not text.strip():
            return Result.success(RepetitionReport())

        report = RepetitionReport()
        errors: list[NLPError] = []

        try:
            # Preprocesar texto
            processed_text = text
            if ignore_dialogue:
                processed_text = self._remove_dialogues(text)

            # Tokenizar y rastrear posiciones
            word_positions = self._tokenize_with_positions(processed_text)
            report.processed_words = len(word_positions)

            # Agrupar por palabra (lowercase)
            word_occurrences: dict[str, list[tuple[str, int, int, int]]] = defaultdict(list)
            for word, start, end, word_idx in word_positions:
                word_lower = word.lower()

                # Ignorar stop words y palabras permitidas
                if word_lower in SPANISH_STOP_WORDS:
                    report.ignored_words.add(word_lower)
                    continue
                if word_lower in NARRATIVE_ALLOWED:
                    continue
                if len(word) < 3:
                    continue

                word_occurrences[word_lower].append((word, start, end, word_idx))

            # Detectar repeticiones
            for word_lower, occurrences in word_occurrences.items():
                if len(occurrences) < min_occurrences:
                    continue

                # Calcular distancias entre ocurrencias consecutivas
                distances = []
                for i in range(1, len(occurrences)):
                    dist = occurrences[i][3] - occurrences[i - 1][3]
                    distances.append(dist)

                if not distances:
                    continue

                min_dist = min(distances)
                max_dist = max(distances)
                avg_dist = sum(distances) / len(distances)

                # Solo reportar si alguna distancia es menor al umbral
                if min_dist > min_distance:
                    continue

                # Determinar severidad
                if min_dist < 10:
                    severity = RepetitionSeverity.HIGH
                elif min_dist < 30:
                    severity = RepetitionSeverity.MEDIUM
                else:
                    severity = RepetitionSeverity.LOW

                # Crear ocurrencias
                occ_list = [
                    RepetitionOccurrence(
                        text=occ[0],
                        start_char=occ[1],
                        end_char=occ[2],
                        sentence=self._extract_sentence(text, occ[1]),
                        word_position=occ[3],
                    )
                    for occ in occurrences
                ]

                rep = Repetition(
                    word=word_lower,
                    repetition_type=RepetitionType.LEXICAL,
                    severity=severity,
                    occurrences=occ_list,
                    count=len(occurrences),
                    min_distance=min_dist,
                    max_distance=max_dist,
                    avg_distance=avg_dist,
                    confidence=0.9 if min_dist < 20 else 0.7,
                )
                report.add_repetition(rep)

        except Exception as e:
            logger.error(f"Error in lexical repetition detection: {e}")
            errors.append(RepetitionCheckError(original_error=str(e)))

        if errors:
            return Result.partial(report, errors)
        return Result.success(report)

    def detect_lemma(
        self,
        text: str,
        min_distance: int = 50,
        min_occurrences: int = 2,
    ) -> Result[RepetitionReport]:
        """
        Detectar repeticiones por lema (conjugaciones del mismo verbo, etc.).

        Requiere spaCy para lematización.
        """
        if not self._nlp:
            return Result.success(RepetitionReport())

        report = RepetitionReport()

        try:
            doc = self._nlp(text)

            # Agrupar por lema
            lemma_occurrences: dict[str, list[tuple]] = defaultdict(list)
            word_idx = 0

            for token in doc:
                if token.is_space or token.is_punct:
                    continue

                lemma = token.lemma_.lower()
                word = token.text

                # Ignorar stop words
                if lemma in SPANISH_STOP_WORDS or token.is_stop:
                    continue
                if len(lemma) < 3:
                    continue

                lemma_occurrences[lemma].append(
                    (word, token.idx, token.idx + len(word), word_idx, lemma)
                )
                word_idx += 1

            report.processed_words = word_idx

            # Detectar repeticiones
            for lemma, occurrences in lemma_occurrences.items():
                if len(occurrences) < min_occurrences:
                    continue

                # Verificar que hay variación de formas (no solo repetición exacta)
                unique_forms = {occ[0].lower() for occ in occurrences}
                if len(unique_forms) == 1:
                    # Es repetición léxica, no de lema
                    continue

                distances = []
                for i in range(1, len(occurrences)):
                    dist = occurrences[i][3] - occurrences[i - 1][3]
                    distances.append(dist)

                if not distances:
                    continue

                min_dist = min(distances)
                if min_dist > min_distance:
                    continue

                severity = RepetitionSeverity.MEDIUM if min_dist < 30 else RepetitionSeverity.LOW

                occ_list = [
                    RepetitionOccurrence(
                        text=occ[0],
                        start_char=occ[1],
                        end_char=occ[2],
                        sentence=self._extract_sentence(text, occ[1]),
                        word_position=occ[3],
                    )
                    for occ in occurrences
                ]

                rep = Repetition(
                    word=lemma,
                    lemma=lemma,
                    repetition_type=RepetitionType.LEMMA,
                    severity=severity,
                    occurrences=occ_list,
                    count=len(occurrences),
                    min_distance=min_dist,
                    max_distance=max(distances),
                    avg_distance=sum(distances) / len(distances),
                    confidence=0.7,
                )
                report.add_repetition(rep)

        except Exception as e:
            logger.error(f"Error in lemma repetition detection: {e}")

        return Result.success(report)

    def detect_semantic(
        self,
        text: str,
        min_distance: int = 100,
        similarity_threshold: float = 0.85,
    ) -> Result[RepetitionReport]:
        """
        Detectar repeticiones semánticas (conceptos similares).

        Usa embeddings para detectar palabras con significado similar
        que se repiten en cercanía.
        """
        if not self._embeddings:
            return Result.success(RepetitionReport())

        report = RepetitionReport()

        try:
            # Extraer palabras de contenido (sustantivos, verbos, adjetivos)
            content_words = self._extract_content_words(text)

            if len(content_words) < 2:
                return Result.success(report)

            # Obtener embeddings
            word_texts = [w[0] for w in content_words]
            embeddings = self._embeddings.encode(word_texts)

            # Comparar pares de palabras cercanas
            semantic_groups: dict[str, list] = defaultdict(list)

            for i, (word1, _start1, _end1, pos1) in enumerate(content_words):
                for j, (word2, start2, end2, pos2) in enumerate(content_words):
                    if i >= j:
                        continue

                    # Solo comparar si están suficientemente cerca
                    distance = abs(pos2 - pos1)
                    if distance > min_distance:
                        continue

                    # Calcular similitud
                    sim = self._cosine_similarity(embeddings[i], embeddings[j])

                    if sim >= similarity_threshold and word1.lower() != word2.lower():
                        # Agrupar por el primer término encontrado
                        key = word1.lower()
                        semantic_groups[key].append(
                            {
                                "word": word2,
                                "similarity": sim,
                                "position": pos2,
                                "start": start2,
                                "end": end2,
                            }
                        )

            # Crear repeticiones semánticas
            for base_word, related in semantic_groups.items():
                if len(related) < 1:
                    continue

                # Encontrar la ocurrencia original
                orig = next((w for w in content_words if w[0].lower() == base_word), None)
                if not orig:
                    continue

                occ_list = [
                    RepetitionOccurrence(
                        text=orig[0],
                        start_char=orig[1],
                        end_char=orig[2],
                        sentence=self._extract_sentence(text, orig[1]),
                        word_position=orig[3],
                    )
                ]

                for rel in related:
                    occ_list.append(
                        RepetitionOccurrence(
                            text=rel["word"],
                            start_char=rel["start"],
                            end_char=rel["end"],
                            sentence=self._extract_sentence(text, rel["start"]),
                            word_position=rel["position"],
                        )
                    )

                rep = Repetition(
                    word=base_word,
                    repetition_type=RepetitionType.SEMANTIC,
                    severity=RepetitionSeverity.LOW,
                    occurrences=occ_list,
                    count=len(occ_list),
                    confidence=0.6,
                )
                report.add_repetition(rep)

        except Exception as e:
            logger.error(f"Error in semantic repetition detection: {e}")

        return Result.success(report)

    def detect_all(
        self,
        text: str,
        min_distance: int = 50,
    ) -> Result[RepetitionReport]:
        """
        Detectar todos los tipos de repeticiones.

        Combina:
        - Repeticiones léxicas
        - Repeticiones por lema
        - Repeticiones semánticas (si embeddings disponibles)
        """
        combined = RepetitionReport()

        # Léxicas
        lexical = self.detect_lexical(text, min_distance)
        if lexical.is_success:
            for rep in lexical.value.repetitions:
                combined.add_repetition(rep)
            combined.processed_words = lexical.value.processed_words

        # Por lema
        lemma = self.detect_lemma(text, min_distance)
        if lemma.is_success:
            for rep in lemma.value.repetitions:
                combined.add_repetition(rep)

        # Semánticas (menos estrictas)
        semantic = self.detect_semantic(text, min_distance * 2)
        if semantic.is_success:
            for rep in semantic.value.repetitions:
                combined.add_repetition(rep)

        return Result.success(combined)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _tokenize_with_positions(self, text: str) -> list[tuple[str, int, int, int]]:
        """Tokenizar texto preservando posiciones."""
        tokens = []
        word_pattern = re.compile(r"\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)\b")
        word_idx = 0

        for match in word_pattern.finditer(text):
            word = match.group(1)
            tokens.append((word, match.start(), match.end(), word_idx))
            word_idx += 1

        return tokens

    def _remove_dialogues(self, text: str) -> str:
        """Eliminar contenido de diálogos del texto."""
        # Remover texto entre comillas y guiones de diálogo
        text = re.sub(r"«[^»]*»", "", text)
        text = re.sub(r'"[^"]*"', "", text)
        text = re.sub(r"—[^—\n]*(?:—|\n)", "", text)
        return text

    def _extract_sentence(self, text: str, position: int) -> str:
        """Extraer oración que contiene la posición."""
        start = position
        while start > 0 and text[start - 1] not in ".!?\n":
            start -= 1

        end = position
        while end < len(text) and text[end] not in ".!?\n":
            end += 1

        sentence = text[start : end + 1].strip()
        if len(sentence) > 150:
            word_pos = position - start
            context_start = max(0, word_pos - 60)
            context_end = min(len(sentence), word_pos + 60)
            sentence = "..." + sentence[context_start:context_end] + "..."

        return sentence

    def _extract_content_words(self, text: str) -> list[tuple[str, int, int, int]]:
        """Extraer palabras de contenido (sustantivos, verbos, adjetivos)."""
        content_words = []

        if self._nlp:
            doc = self._nlp(text)
            word_idx = 0
            for token in doc:
                if token.is_space or token.is_punct:
                    continue
                if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV"]:
                    if not token.is_stop and len(token.text) >= 3:
                        content_words.append(
                            (token.text, token.idx, token.idx + len(token.text), word_idx)
                        )
                word_idx += 1
        else:
            # Fallback: usar todas las palabras largas
            for word, start, end, idx in self._tokenize_with_positions(text):
                if len(word) >= 4 and word.lower() not in SPANISH_STOP_WORDS:
                    content_words.append((word, start, end, idx))

        return content_words

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calcular similitud coseno entre dos vectores."""
        import numpy as np

        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))
