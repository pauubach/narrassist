"""
Detector de repeticiones léxicas.

Detecta palabras repetidas dentro de una distancia configurable,
señalándolas al corrector para que decida si son intencionales
o deben variarse.
"""

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import RepetitionConfig
from ..types import CorrectionCategory, RepetitionIssueType


class RepetitionDetector(BaseDetector):
    """
    Detecta repeticiones léxicas en el texto.

    Usa lematización (si hay spaCy disponible) o comparación directa
    para encontrar palabras repetidas en proximidad.
    """

    # Palabras funcionales a ignorar (artículos, preposiciones, etc.)
    IGNORE_WORDS = {
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
        "mas",
        "aunque",
        "porque",
        "pues",
        "que",
        "si",
        "como",
        "cuando",
        "donde",
        # Pronombres
        "yo",
        "tú",
        "él",
        "ella",
        "ello",
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
        "estos",
        "estas",
        "ese",
        "esa",
        "esos",
        "esas",
        "aquel",
        "aquella",
        "aquellos",
        "aquellas",
        "esto",
        "eso",
        "aquello",
        # Verbos auxiliares
        "ser",
        "estar",
        "haber",
        "tener",
        "ir",
        "hacer",
        "poder",
        "deber",
        "querer",
        "saber",
        "decir",
        "ver",
        "dar",
        "venir",
        # Adverbios comunes
        "no",
        "sí",
        "ya",
        "muy",
        "más",
        "menos",
        "bien",
        "mal",
        "también",
        "tampoco",
        "además",
        "ahora",
        "antes",
        "después",
        "aquí",
        "ahí",
        "allí",
        "así",
        "siempre",
        "nunca",
        "todavía",
        # Otros
        "todo",
        "nada",
        "algo",
        "alguien",
        "nadie",
        "cada",
        "otro",
        "mismo",
        "tan",
        "tanto",
        "mucho",
        "poco",
        "bastante",
    }

    # Palabras que pueden repetirse intencionalmente
    INTENTIONAL_REPETITION_WORDS = {
        "sí",
        "no",
        "muy",
        "más",
        "nunca",
        "jamás",
        "siempre",
    }

    def __init__(self, config: RepetitionConfig | None = None):
        self.config = config or RepetitionConfig()
        self._spacy_doc = None

        # Mapear sensibilidad a distancia real
        self._distance_map = {
            "low": self.config.min_distance * 2,
            "medium": self.config.min_distance,
            "high": self.config.min_distance // 2,
        }

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.REPETITION

    @property
    def requires_spacy(self) -> bool:
        return True  # Opcional pero recomendado para lematización

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
    ) -> list[CorrectionIssue]:
        """
        Detecta repeticiones en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy preprocesado (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        self._spacy_doc = spacy_doc
        issues: list[CorrectionIssue] = []

        # Detectar repeticiones léxicas cercanas
        issues.extend(self._detect_lexical_repetitions(text, chapter_index))

        # Detectar oraciones que empiezan igual
        issues.extend(self._detect_sentence_starts(text, chapter_index))

        return issues

    def _detect_lexical_repetitions(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta palabras repetidas en proximidad."""
        issues = []
        distance = self._distance_map.get(self.config.sensitivity, self.config.min_distance)

        # Obtener tokens con posiciones
        if self._spacy_doc is not None:
            tokens = self._get_tokens_from_spacy()
        else:
            tokens = self._get_tokens_simple(text)

        # Filtrar tokens de contenido
        content_tokens = [
            t
            for t in tokens
            if len(t["text"]) >= self.config.min_word_length
            and t["lemma"].lower() not in self.IGNORE_WORDS
            and t["pos"] in ("NOUN", "VERB", "ADJ", "ADV", None)  # None = sin spaCy
        ]

        # Buscar repeticiones
        reported_pairs = set()  # Evitar reportar el mismo par dos veces

        for i, token in enumerate(content_tokens):
            lemma = token["lemma"].lower()

            # Buscar repeticiones en ventana posterior
            for j in range(i + 1, len(content_tokens)):
                other = content_tokens[j]

                # Fuera de la ventana de distancia
                word_distance = j - i
                if word_distance > distance:
                    break

                # ¿Es la misma palabra/lema?
                if other["lemma"].lower() == lemma:
                    # Verificar si es repetición intencional
                    if self._is_intentional(token, other, text):
                        continue

                    # Crear clave única para este par
                    pair_key = (token["start"], other["start"])
                    if pair_key in reported_pairs:
                        continue
                    reported_pairs.add(pair_key)

                    # Reportar — posición solo del primer token (no del span entre ambos)
                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=RepetitionIssueType.LEXICAL_CLOSE.value,
                            start_char=token["start"],
                            end_char=token["end"],
                            text=token["text"],
                            explanation=(
                                f"'{token['text']}' aparece repetida a {word_distance} "
                                f"palabras de distancia"
                            ),
                            suggestion=None,  # El corrector decide la variación
                            confidence=self._calculate_confidence(word_distance, distance),
                            context=self._extract_context(text, token["start"], token["end"]),
                            chapter_index=chapter_index,
                            rule_id="REP_LEXICAL",
                            extra_data={
                                "word": token["text"],
                                "lemma": lemma,
                                "distance": word_distance,
                                "first_pos": token["start"],
                                "second_pos": other["start"],
                            },
                        )
                    )

        return issues

    def _detect_sentence_starts(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta oraciones consecutivas que empiezan igual."""
        issues = []

        # Dividir en oraciones
        sentences = re.split(r"[.!?]+\s+", text)

        for i in range(len(sentences) - 1):
            sent1 = sentences[i].strip()
            sent2 = sentences[i + 1].strip()

            if not sent1 or not sent2:
                continue

            # Obtener primeras palabras (hasta 3)
            words1 = sent1.split()[:3]
            words2 = sent2.split()[:3]

            if len(words1) < 2 or len(words2) < 2:
                continue

            # Comparar inicio
            common_start = []
            for w1, w2 in zip(words1, words2, strict=False):
                if w1.lower() == w2.lower():
                    common_start.append(w1)
                else:
                    break

            # Si comparten 2+ palabras al inicio
            if len(common_start) >= 2:
                # Encontrar posición en texto original
                start_pos = text.find(sent2)
                if start_pos == -1:
                    continue

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=RepetitionIssueType.SENTENCE_START.value,
                        start_char=start_pos,
                        end_char=start_pos + len(" ".join(common_start)),
                        text=" ".join(common_start),
                        explanation=(
                            f"Oraciones consecutivas empiezan igual: '{' '.join(common_start)}...'"
                        ),
                        suggestion=None,
                        confidence=0.7,
                        context=f"...{sent1[-50:]}. {sent2[:50]}...",
                        chapter_index=chapter_index,
                        rule_id="REP_SENT_START",
                        extra_data={
                            "common_words": common_start,
                        },
                    )
                )

        return issues

    def _get_tokens_from_spacy(self) -> list[dict]:
        """Obtiene tokens del documento spaCy."""
        return [
            {
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "start": token.idx,
                "end": token.idx + len(token.text),
            }
            for token in self._spacy_doc
            if token.is_alpha  # Solo palabras
        ]

    def _get_tokens_simple(self, text: str) -> list[dict]:
        """Tokenización simple sin spaCy."""
        tokens = []
        for match in re.finditer(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b", text):
            word = match.group()
            tokens.append(
                {
                    "text": word,
                    "lemma": word,  # Sin lematización real
                    "pos": None,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
        return tokens

    def _is_intentional(self, token1: dict, token2: dict, text: str) -> bool:
        """Determina si una repetición parece intencional."""
        word = token1["text"].lower()

        # Palabras que se repiten intencionalmente
        if word in self.INTENTIONAL_REPETITION_WORDS:
            return True

        # Repetición inmediata tipo "muy muy" o "sí, sí"
        between = text[token1["end"] : token2["start"]]
        if len(between.strip()) <= 2:  # Solo espacios o coma
            return True

        # En diálogo (podría ser intencional para énfasis)
        if self.config.ignore_dialogue:
            context = text[max(0, token1["start"] - 5) : token1["start"]]
            if "—" in context or "–" in context or "-" in context:
                return True

        return False

    def _calculate_confidence(self, actual_distance: int, max_distance: int) -> float:
        """Calcula confianza basada en la distancia."""
        # Más cerca = más confianza
        ratio = actual_distance / max_distance
        if ratio < 0.3:
            return 0.9
        elif ratio < 0.5:
            return 0.8
        elif ratio < 0.7:
            return 0.7
        else:
            return 0.6
