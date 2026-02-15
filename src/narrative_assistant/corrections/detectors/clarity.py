"""
Detector de problemas de claridad.

Detecta:
- Oraciones excesivamente largas
- Oraciones con demasiadas subordinadas
- Párrafos sin pausas (comas, puntos y coma)
"""

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import ClarityConfig
from ..types import CorrectionCategory


class ClarityIssueType:
    """Tipos de problemas de claridad."""

    SENTENCE_TOO_LONG = "sentence_too_long"
    SENTENCE_LONG_WARNING = "sentence_long_warning"
    TOO_MANY_SUBORDINATES = "too_many_subordinates"
    PARAGRAPH_NO_PAUSES = "paragraph_no_pauses"
    RUN_ON_SENTENCE = "run_on_sentence"
    PARAGRAPH_TOO_SHORT = "paragraph_too_short"
    PARAGRAPH_TOO_LONG = "paragraph_too_long"


class ClarityDetector(BaseDetector):
    """
    Detecta problemas de claridad y legibilidad.

    Analiza la estructura de oraciones y párrafos para identificar
    textos que podrían ser difíciles de leer o entender.
    """

    # Patrones para detectar fin de oración
    SENTENCE_END = re.compile(r'[.!?]+(?:\s|$|"|\)|»|\')')

    # Patrón para detectar subordinadas
    SUBORDINATE_PATTERN = re.compile(
        r"\b(que|quien|cual|cuyo|donde|cuando|como|aunque|mientras|porque)\b", re.IGNORECASE
    )

    # Patrón para pausas internas
    PAUSE_PATTERN = re.compile(r"[,;:]")

    def __init__(self, config: ClarityConfig | None = None):
        self.config = config or ClarityConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.CLARITY

    @property
    def requires_spacy(self) -> bool:
        return False

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta problemas de claridad en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Detectar oraciones largas
        issues.extend(self._check_sentence_length(text, chapter_index))

        # Detectar subordinadas excesivas
        issues.extend(self._check_subordination(text, chapter_index))

        # Detectar párrafos sin pausas
        issues.extend(self._check_paragraph_pauses(text, chapter_index))

        # Detectar párrafos demasiado cortos o largos
        if self.config.detect_paragraph_length:
            issues.extend(self._check_paragraph_length(text, chapter_index))

        return issues

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """
        Divide el texto en oraciones, retornando (oración, start, end).

        Returns:
            Lista de tuplas (texto_oración, posición_inicio, posición_fin)
        """
        sentences = []
        current_start = 0

        for match in self.SENTENCE_END.finditer(text):
            end = match.end()
            sentence_text = text[current_start:end].strip()

            if sentence_text:
                sentences.append((sentence_text, current_start, end))

            current_start = end

        # Última oración si no termina en punto
        if current_start < len(text):
            remaining = text[current_start:].strip()
            if remaining and len(remaining) > 10:  # Ignorar fragmentos muy cortos
                sentences.append((remaining, current_start, len(text)))

        return sentences

    def _count_words(self, text: str) -> int:
        """Cuenta palabras en un texto."""
        return len(re.findall(r"\b\w+\b", text))

    def _check_sentence_length(self, text: str, chapter_index: int | None) -> list[CorrectionIssue]:
        """Verifica la longitud de las oraciones."""
        issues = []
        sentences = self._split_sentences(text)

        for sentence_text, start, end in sentences:
            word_count = self._count_words(sentence_text)
            char_count = len(sentence_text)

            # Oración demasiado larga (error)
            if (
                word_count > self.config.max_sentence_words
                or char_count > self.config.max_sentence_chars
            ):
                # Calcular confianza basada en cuánto excede el límite
                excess_ratio = max(
                    word_count / self.config.max_sentence_words,
                    char_count / self.config.max_sentence_chars,
                )
                confidence = min(0.95, self.config.base_confidence + (excess_ratio - 1) * 0.1)

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.SENTENCE_TOO_LONG,
                        start_char=start,
                        end_char=end,
                        text=sentence_text[:100] + "..."
                        if len(sentence_text) > 100
                        else sentence_text,
                        explanation=(
                            f"Oración muy larga: {word_count} palabras, "
                            f"{char_count} caracteres. Considere dividirla en oraciones "
                            f"más cortas para mejorar la legibilidad."
                        ),
                        suggestion="Divida la oración en oraciones más cortas usando punto seguido.",
                        confidence=confidence,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_SENTENCE_LONG",
                        extra_data={
                            "word_count": word_count,
                            "char_count": char_count,
                            "max_words": self.config.max_sentence_words,
                        },
                    )
                )

            # Oración larga (advertencia)
            elif word_count > self.config.warning_sentence_words:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.SENTENCE_LONG_WARNING,
                        start_char=start,
                        end_char=end,
                        text=sentence_text[:100] + "..."
                        if len(sentence_text) > 100
                        else sentence_text,
                        explanation=(
                            f"Oración larga: {word_count} palabras. "
                            f"Considere si podría simplificarse."
                        ),
                        suggestion=None,  # Solo advertencia
                        confidence=0.7,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_SENTENCE_WARNING",
                        extra_data={
                            "word_count": word_count,
                            "char_count": char_count,
                        },
                    )
                )

        return issues

    def _check_subordination(self, text: str, chapter_index: int | None) -> list[CorrectionIssue]:
        """Verifica subordinadas encadenadas."""
        issues = []
        sentences = self._split_sentences(text)

        for sentence_text, start, end in sentences:
            # Contar marcadores de subordinación
            subordinates = self.SUBORDINATE_PATTERN.findall(sentence_text)
            count = len(subordinates)

            if count > self.config.max_subordinates:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.TOO_MANY_SUBORDINATES,
                        start_char=start,
                        end_char=end,
                        text=sentence_text[:100] + "..."
                        if len(sentence_text) > 100
                        else sentence_text,
                        explanation=(
                            f"Demasiadas subordinadas encadenadas: {count} conectores "
                            f"({', '.join({s.lower() for s in subordinates})}). "
                            f"Esto puede dificultar la lectura."
                        ),
                        suggestion="Divida la oración en oraciones independientes más simples.",
                        confidence=min(0.9, 0.7 + (count - self.config.max_subordinates) * 0.1),
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_SUBORDINATION",
                        extra_data={
                            "subordinate_count": count,
                            "subordinates": list({s.lower() for s in subordinates}),
                        },
                    )
                )

        return issues

    def _check_paragraph_pauses(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Verifica que los párrafos tengan suficientes pausas."""
        issues = []

        # Dividir en párrafos
        paragraphs = re.split(r"\n\s*\n", text)
        current_pos = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                current_pos += 2  # Líneas vacías
                continue

            # Solo analizar párrafos sustanciales
            word_count = self._count_words(paragraph)
            if word_count < 50:  # Ignorar párrafos cortos
                current_pos += len(paragraph) + 2
                continue

            # Contar pausas (comas, punto y coma)
            pause_count = len(self.PAUSE_PATTERN.findall(paragraph))

            # Calcular pausas por 100 palabras
            pauses_per_100 = (pause_count / word_count) * 100

            if pauses_per_100 < self.config.min_pauses_per_100_words:
                start = text.find(paragraph, current_pos)
                end = start + len(paragraph)

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.PARAGRAPH_NO_PAUSES,
                        start_char=start,
                        end_char=end,
                        text=paragraph[:150] + "..." if len(paragraph) > 150 else paragraph,
                        explanation=(
                            f"Párrafo con pocas pausas: {pause_count} comas/punto y coma "
                            f"en {word_count} palabras. Puede resultar denso de leer."
                        ),
                        suggestion="Considere añadir pausas (comas) o dividir en oraciones más cortas.",
                        confidence=0.75,
                        context=self._extract_context(text, start, min(end, start + 200)),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_NO_PAUSES",
                        extra_data={
                            "word_count": word_count,
                            "pause_count": pause_count,
                            "pauses_per_100": round(pauses_per_100, 2),
                        },
                    )
                )

            current_pos += len(paragraph) + 2

        return issues

    def _check_paragraph_length(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Verifica que los párrafos no sean demasiado cortos ni largos."""
        issues = []

        paragraphs = re.split(r"\n\s*\n", text)
        current_pos = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                current_pos += 2
                continue

            # Ignorar párrafos que parecen headings (líneas cortas solas)
            if len(paragraph) < 80 and "\n" not in paragraph:
                word_count = self._count_words(paragraph)
                if word_count < 10:
                    current_pos += len(paragraph) + 2
                    continue

            # Contar frases en el párrafo
            sentences = self._split_sentences(paragraph)
            sentence_count = len(sentences)

            if sentence_count == 0:
                current_pos += len(paragraph) + 2
                continue

            start = text.find(paragraph, current_pos)
            if start == -1:
                current_pos += len(paragraph) + 2
                continue
            end = start + len(paragraph)

            # Párrafo demasiado corto
            if sentence_count < self.config.min_paragraph_sentences:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.PARAGRAPH_TOO_SHORT,
                        start_char=start,
                        end_char=end,
                        text=paragraph[:150] + "..." if len(paragraph) > 150 else paragraph,
                        explanation=(
                            f"Párrafo con solo {sentence_count} oración(es). "
                            f"Considere fusionarlo con el párrafo anterior o siguiente."
                        ),
                        suggestion="Fusione este párrafo con el adyacente o amplíe su contenido.",
                        confidence=0.75,
                        context=self._extract_context(text, start, min(end, start + 200)),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_PARAGRAPH_SHORT",
                        extra_data={"sentence_count": sentence_count},
                    )
                )

            # Párrafo demasiado largo
            elif sentence_count > self.config.max_paragraph_sentences:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ClarityIssueType.PARAGRAPH_TOO_LONG,
                        start_char=start,
                        end_char=end,
                        text=paragraph[:150] + "..." if len(paragraph) > 150 else paragraph,
                        explanation=(
                            f"Párrafo con {sentence_count} oraciones. "
                            f"Los párrafos de más de {self.config.max_paragraph_sentences} "
                            f"oraciones pueden dificultar la lectura."
                        ),
                        suggestion="Divida este párrafo en bloques temáticos más pequeños.",
                        confidence=min(
                            0.92,
                            0.78 + (sentence_count - self.config.max_paragraph_sentences) * 0.03,
                        ),
                        context=self._extract_context(text, start, min(end, start + 200)),
                        chapter_index=chapter_index,
                        rule_id="CLARITY_PARAGRAPH_LONG",
                        extra_data={"sentence_count": sentence_count},
                    )
                )

            current_pos = end + 2

        return issues
