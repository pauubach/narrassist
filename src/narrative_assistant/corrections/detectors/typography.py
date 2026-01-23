"""
Detector de problemas tipográficos.

Detecta:
- Guiones incorrectos (diálogos, rangos, incisos)
- Comillas inconsistentes
- Puntos suspensivos mal formados
- Problemas de espaciado
"""

import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import TypographyConfig
from ..types import CorrectionCategory, TypographyIssueType


class TypographyDetector(BaseDetector):
    """
    Detecta problemas tipográficos en el texto.

    Genera sugerencias para que el corrector decida si aplicarlas.
    """

    # Caracteres de guiones/rayas
    HYPHEN = "-"  # U+002D - guion corto
    EN_DASH = "–"  # U+2013 - semiraya
    EM_DASH = "—"  # U+2014 - raya

    # Mapeo de configuración a carácter
    DASH_MAP = {
        "em": EM_DASH,
        "en": EN_DASH,
        "hyphen": HYPHEN,
    }

    def __init__(self, config: Optional[TypographyConfig] = None):
        self.config = config or TypographyConfig()
        self._compile_patterns()

    def _compile_patterns(self):
        """Compila patrones regex para detección."""
        # Patrón para detectar inicio de diálogo
        # Busca guiones al inicio de línea o después de párrafo
        self._dialogue_pattern = re.compile(
            r"(?:^|\n)\s*([—–\-])\s*[A-ZÁÉÍÓÚÜÑ¿¡]",
            re.MULTILINE,
        )

        # Patrón para rangos numéricos (1990-2000, páginas 10-20)
        self._range_pattern = re.compile(
            r"\b(\d+)\s*([—–\-])\s*(\d+)\b"
        )

        # Patrón para incisos (palabra —inciso— palabra)
        self._inciso_pattern = re.compile(
            r"\w\s+([—–\-])[^—–\-\n]+([—–\-])\s+\w"
        )

        # Patrones de comillas
        # Usando Unicode escapes para evitar problemas de encoding
        self._quote_patterns = {
            "angular": re.compile(r"[\u00AB\u00BB]"),  # « »
            "curly": re.compile(r"[\u201C\u201D]"),    # " "
            "straight": re.compile(r'"'),
        }

        # Puntos suspensivos mal formados
        # (?<!\.) asegura que no hay punto antes (evita match en "..." válido)
        # \.\.(?!\.) detecta exactamente dos puntos
        # \.{4,} detecta cuatro o más puntos
        self._ellipsis_wrong = re.compile(r"(?<!\.)\.\.(?!\.)|\.{4,}")

        # Espaciado
        self._space_before_punct = re.compile(r'\s+([.,;:!?\u00BB\"\)\]])')
        self._no_space_after_punct = re.compile(r"([.,;:!?])[A-Za-záéíóúüñÁÉÍÓÚÜÑ]")
        self._multiple_spaces = re.compile(r"  +")

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.TYPOGRAPHY

    def detect(
        self,
        text: str,
        chapter_index: Optional[int] = None,
    ) -> list[CorrectionIssue]:
        """
        Detecta problemas tipográficos en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Detectar guiones en diálogos
        issues.extend(self._check_dialogue_dashes(text, chapter_index))

        # Detectar guiones en rangos
        issues.extend(self._check_range_dashes(text, chapter_index))

        # Detectar comillas inconsistentes
        issues.extend(self._check_quotes(text, chapter_index))

        # Detectar puntos suspensivos
        if self.config.check_ellipsis:
            issues.extend(self._check_ellipsis(text, chapter_index))

        # Detectar problemas de espaciado
        if self.config.check_spacing:
            issues.extend(self._check_spacing(text, chapter_index))

        # Detectar espacios múltiples
        if self.config.check_multiple_spaces:
            issues.extend(self._check_multiple_spaces(text, chapter_index))

        return issues

    def _check_dialogue_dashes(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica guiones en diálogos."""
        issues = []
        expected_dash = self.DASH_MAP[self.config.dialogue_dash]

        for match in self._dialogue_pattern.finditer(text):
            found_dash = match.group(1)

            if found_dash != expected_dash:
                start = match.start(1)
                end = match.end(1)

                # Verificar contexto para reducir falsos positivos
                # Si es un guion corto al inicio de línea, podría ser lista con viñetas
                context_after = text[end:end+20] if end+20 < len(text) else text[end:]

                # Si parece una lista (número, letra con punto), no es diálogo
                if re.match(r'\s*[a-zA-Z0-9]\s*[.):]', context_after):
                    continue

                # Si el guion es corto pero hay raya larga en el documento,
                # probablemente es intencional (listas vs diálogos)
                if found_dash == self.HYPHEN and self.EM_DASH in text:
                    # El documento usa rayas para diálogos, este guion es otra cosa
                    continue

                issues.append(
                    CorrectionIssue(
                        # Según RAE, la raya en diálogos es signo de puntuación
                        category=CorrectionCategory.PUNCTUATION.value,
                        issue_type=TypographyIssueType.WRONG_DASH_DIALOGUE.value,
                        start_char=start,
                        end_char=end,
                        text=found_dash,
                        explanation=f"Guion de diálogo: se encontró '{found_dash}' pero "
                        f"el estilo configurado usa '{expected_dash}'",
                        suggestion=expected_dash,
                        confidence=0.85,  # Reducida por posibles falsos positivos
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="PUNCT_DASH_DIALOGUE",
                    )
                )

        return issues

    def _check_range_dashes(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica guiones en rangos numéricos."""
        issues = []
        # El estándar tipográfico usa semiraya (–) para rangos
        expected_dash = self.EN_DASH

        for match in self._range_pattern.finditer(text):
            found_dash = match.group(2)

            if found_dash != expected_dash:
                start = match.start(2)
                end = match.end(2)

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=TypographyIssueType.WRONG_DASH_RANGE.value,
                        start_char=start,
                        end_char=end,
                        text=found_dash,
                        explanation=f"Rango numérico: se recomienda usar semiraya (–) "
                        f"en lugar de '{found_dash}'",
                        suggestion=expected_dash,
                        confidence=0.85,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="TYPO_DASH_RANGE",
                    )
                )

        return issues

    def _check_quotes(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica consistencia de comillas."""
        issues = []
        preferred = self.config.quote_style

        # Contar tipos de comillas
        counts = {
            style: len(pattern.findall(text))
            for style, pattern in self._quote_patterns.items()
        }

        # Si hay mezcla de estilos
        styles_used = [s for s, c in counts.items() if c > 0]

        if len(styles_used) > 1:
            # Reportar el estilo no preferido
            for style in styles_used:
                if style != preferred and counts[style] > 0:
                    # Encontrar las primeras ocurrencias
                    pattern = self._quote_patterns[style]
                    for match in list(pattern.finditer(text))[:5]:  # Máx 5
                        start = match.start()
                        end = match.end()

                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=TypographyIssueType.MIXED_QUOTES.value,
                                start_char=start,
                                end_char=end,
                                text=match.group(),
                                explanation=f"Mezcla de estilos de comillas: "
                                f"se encontró estilo '{style}' pero el "
                                f"preferido es '{preferred}'",
                                suggestion=None,  # Depende del contexto
                                confidence=0.75,
                                context=self._extract_context(text, start, end),
                                chapter_index=chapter_index,
                                rule_id="TYPO_QUOTE_MIX",
                                extra_data={
                                    "found_style": style,
                                    "preferred_style": preferred,
                                    "counts": counts,
                                },
                            )
                        )

        return issues

    def _check_ellipsis(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica puntos suspensivos."""
        issues = []

        for match in self._ellipsis_wrong.finditer(text):
            start = match.start()
            end = match.end()
            found = match.group()

            if len(found) == 2:
                explanation = "Puntos suspensivos: deben ser exactamente tres puntos"
            else:
                explanation = "Puntos suspensivos: demasiados puntos (usar solo tres)"

            issues.append(
                CorrectionIssue(
                    # Según RAE, los puntos suspensivos son signo de puntuación
                    category=CorrectionCategory.PUNCTUATION.value,
                    issue_type=TypographyIssueType.WRONG_ELLIPSIS.value,
                    start_char=start,
                    end_char=end,
                    text=found,
                    explanation=explanation,
                    suggestion="...",
                    confidence=0.95,
                    context=self._extract_context(text, start, end),
                    chapter_index=chapter_index,
                    rule_id="PUNCT_ELLIPSIS",
                )
            )

        return issues

    def _check_spacing(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica problemas de espaciado."""
        issues = []

        # Espacio antes de puntuación
        for match in self._space_before_punct.finditer(text):
            start = match.start()
            end = match.end()

            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=TypographyIssueType.SPACING_BEFORE_PUNCT.value,
                    start_char=start,
                    end_char=end,
                    text=match.group(),
                    explanation=f"Espacio innecesario antes de '{match.group(1)}'",
                    suggestion=match.group(1),
                    confidence=0.9,
                    context=self._extract_context(text, start, end),
                    chapter_index=chapter_index,
                    rule_id="TYPO_SPACE_BEFORE",
                )
            )

        # Falta espacio después de puntuación
        # Lista ampliada de abreviaturas comunes en español
        COMMON_ABBREVIATIONS = {
            "sr.", "sra.", "srta.", "dr.", "dra.", "lic.", "ing.", "arq.",
            "prof.", "mag.", "etc.", "ej.", "p.ej.", "pág.", "págs.", "cap.",
            "vol.", "núm.", "nº.", "art.", "ed.", "fig.", "tel.", "fax.",
            "av.", "avda.", "c.", "ctra.", "pza.", "urb.", "apdo.", "dpto.",
            "http", "https", "www", "ftp", ".com", ".es", ".org", ".net",
            "a.m.", "p.m.", "a.c.", "d.c.", "s.a.", "s.l.", "s.r.l.",
        }

        for match in self._no_space_after_punct.finditer(text):
            start = match.start()
            end = match.end()

            # Obtener contexto más amplio
            context_start = max(0, start - 15)
            context_end = min(len(text), end + 15)
            context = text[context_start:context_end].lower()

            # Ignorar si parece abreviatura o URL
            if any(abbr in context for abbr in COMMON_ABBREVIATIONS):
                continue

            # Ignorar números con punto decimal (3.14)
            if match.group(1) == '.' and text[start-1:start].isdigit():
                char_after = match.group()[-1]
                if char_after.isdigit():
                    continue

            # Ignorar horas (10:30)
            if match.group(1) == ':' and text[max(0,start-2):start].isdigit():
                continue

            # Ignorar si es parte de un email o URL
            if '@' in context or '://' in context:
                continue

            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=TypographyIssueType.SPACING_AFTER_PUNCT.value,
                    start_char=start,
                    end_char=end,
                    text=match.group(),
                    explanation=f"Falta espacio después de '{match.group(1)}'",
                    suggestion=match.group(1) + " " + match.group()[1],
                    confidence=0.75,  # Reducida por posibles falsos positivos
                    context=self._extract_context(text, start, end),
                    chapter_index=chapter_index,
                    rule_id="TYPO_SPACE_AFTER",
                )
            )

        return issues

    def _check_multiple_spaces(
        self, text: str, chapter_index: Optional[int]
    ) -> list[CorrectionIssue]:
        """Verifica espacios múltiples."""
        issues = []

        for match in self._multiple_spaces.finditer(text):
            start = match.start()
            end = match.end()

            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=TypographyIssueType.MULTIPLE_SPACES.value,
                    start_char=start,
                    end_char=end,
                    text=match.group(),
                    explanation=f"Espacios múltiples ({len(match.group())} espacios)",
                    suggestion=" ",
                    confidence=0.95,
                    context=self._extract_context(text, start, end),
                    chapter_index=chapter_index,
                    rule_id="TYPO_MULTI_SPACE",
                )
            )

        return issues
