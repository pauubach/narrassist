"""
Detector de referencias y citas bibliográficas.

Detecta:
- Texto sin citas cuando se espera contenido referenciado
- Citas huérfanas (referenciadas pero no en bibliografía)
- Referencias no citadas (en bibliografía pero nunca referenciadas)
- Formato de citas mixto (numérico + autor-año)
- Ausencia de sección bibliográfica
"""

from __future__ import annotations

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import ReferencesConfig
from ..types import CorrectionCategory, ReferencesIssueType

# ============================================================================
# Patrones de citas en texto
# ============================================================================

# [1], [1-3], [1, 2, 5]
NUMERIC_CITE = re.compile(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]")

# (García, 2024), (García & López, 2024), (García et al., 2024)
AUTHOR_YEAR = re.compile(
    r"\("
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:et\s+al\.?|[yY&]\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?)"
    r",?\s*(\d{4}[a-z]?)"
    r"\)"
)

# García (2024), García et al. (2024)
AUTHOR_INLINE = re.compile(
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:et\s+al\.?|[yY&]\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?)"
    r"\s+\((\d{4}[a-z]?)\)"
)

# ============================================================================
# Patrones de sección bibliográfica
# ============================================================================

BIBLIOGRAPHY_HEADER = re.compile(
    r"^(?:#{1,3}\s*)?(?:referencias|bibliografía|bibliography|references|"
    r"fuentes|works?\s+cited|fuentes\s+consultadas|obras\s+citadas)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class ReferencesDetector(BaseDetector):
    """Detecta problemas con referencias y citas bibliográficas."""

    def __init__(self, config: ReferencesConfig | None = None):
        self.config = config or ReferencesConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.REFERENCES

    @staticmethod
    def _expand_numeric_citation(cite_body: str) -> set[str]:
        """Expande [1-3, 5] -> {"1", "2", "3", "5"}."""
        numbers: set[str] = set()

        for part in re.split(r"\s*,\s*", cite_body.strip()):
            if not part:
                continue

            range_match = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", part)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                lo, hi = sorted((start, end))

                # Guardar extremos si el rango es patológico.
                if hi - lo > 1000:
                    numbers.add(str(start))
                    numbers.add(str(end))
                else:
                    for value in range(lo, hi + 1):
                        numbers.add(str(value))
                continue

            numbers.update(re.findall(r"\d+", part))

        return numbers

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Recopilar citas encontradas
        numeric_cites = list(NUMERIC_CITE.finditer(text))
        author_year_cites = list(AUTHOR_YEAR.finditer(text))
        author_inline_cites = list(AUTHOR_INLINE.finditer(text))

        all_author_cites = author_year_cites + author_inline_cites
        has_numeric = len(numeric_cites) > 0
        has_author = len(all_author_cites) > 0

        # Detectar sección bibliográfica
        bib_match = BIBLIOGRAPHY_HEADER.search(text)
        has_bibliography = bib_match is not None

        # 1. Sin citas en absoluto
        if not has_numeric and not has_author:
            if self.config.min_citations_expected > 0:
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=ReferencesIssueType.NO_CITATIONS.value,
                        start_char=0,
                        end_char=min(len(text), 100),
                        text=text[:100] + "..." if len(text) > 100 else text,
                        explanation=(
                            "No se encontraron citas bibliográficas en el texto. "
                            "Los textos científicos/académicos requieren citas a fuentes."
                        ),
                        suggestion="Añada citas bibliográficas a las afirmaciones que lo requieran.",
                        confidence=0.88,
                        context="",
                        chapter_index=chapter_index,
                        rule_id="REF_NO_CITATIONS",
                    )
                )
            return issues

        # 2. Formato mixto
        if has_numeric and has_author and self.config.detect_mixed_format:
            # Tomar la primera ocurrencia del formato minoritario
            if len(numeric_cites) <= len(all_author_cites):
                minority = numeric_cites[0]
            else:
                minority = all_author_cites[0]

            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=ReferencesIssueType.MIXED_FORMAT.value,
                    start_char=minority.start(),
                    end_char=minority.end(),
                    text=minority.group(),
                    explanation=(
                        f"Formato de citas mixto: se encontraron {len(numeric_cites)} citas "
                        f"numéricas y {len(all_author_cites)} citas autor-año. "
                        "Use un solo formato de forma consistente."
                    ),
                    suggestion="Unifique todas las citas al mismo formato (numérico o autor-año).",
                    confidence=0.90,
                    context=self._extract_context(text, minority.start(), minority.end()),
                    chapter_index=chapter_index,
                    rule_id="REF_MIXED_FORMAT",
                    extra_data={
                        "numeric_count": len(numeric_cites),
                        "author_year_count": len(all_author_cites),
                    },
                )
            )

        # 3. Sin sección bibliográfica
        if not has_bibliography and self.config.detect_no_bibliography:
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=ReferencesIssueType.NO_BIBLIOGRAPHY.value,
                    start_char=max(0, len(text) - 100),
                    end_char=len(text),
                    text="(fin del documento)",
                    explanation=(
                        "El texto contiene citas pero no tiene sección de bibliografía/referencias. "
                        "Toda cita debe tener su referencia completa al final del documento."
                    ),
                    suggestion=(
                        "Añada una sección 'Referencias' o 'Bibliografía' al final del documento."
                    ),
                    confidence=0.92,
                    context="",
                    chapter_index=chapter_index,
                    rule_id="REF_NO_BIBLIOGRAPHY",
                )
            )

        # 4. Citas huérfanas (numéricas sin entrada en bibliografía)
        if has_bibliography and has_numeric and self.config.detect_orphan_citations:
            assert bib_match is not None  # guarded by has_bibliography
            bib_start = bib_match.start()
            bib_text = text[bib_start:]

            for cite_match in numeric_cites:
                # Solo citas antes de la bibliografía
                if cite_match.start() >= bib_start:
                    continue

                # Extraer números individuales de la cita
                cite_nums = self._expand_numeric_citation(cite_match.group(1))
                for num in cite_nums:
                    # Buscar si el número aparece en la sección bibliográfica
                    bib_pattern = re.compile(
                        rf"(?:^|\n)\s*\[?{re.escape(num)}\]?[\.\)\s]", re.MULTILINE
                    )
                    if not bib_pattern.search(bib_text):
                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=ReferencesIssueType.ORPHAN_CITATION.value,
                                start_char=cite_match.start(),
                                end_char=cite_match.end(),
                                text=cite_match.group(),
                                explanation=(
                                    f"La cita [{num}] no se encontró en la sección de bibliografía."
                                ),
                                suggestion=f"Añada la referencia [{num}] a la bibliografía.",
                                confidence=0.85,
                                context=self._extract_context(
                                    text, cite_match.start(), cite_match.end()
                                ),
                                chapter_index=chapter_index,
                                rule_id="REF_ORPHAN_CITATION",
                                extra_data={"citation_number": num},
                            )
                        )

        # 5. Referencias no citadas (entradas en bibliografía sin cita en texto)
        if has_bibliography and has_numeric and self.config.detect_unused_references:
            assert bib_match is not None  # guarded by has_bibliography
            bib_start = bib_match.start()
            bib_text = text[bib_start:]

            # Extraer números de entradas bibliográficas: [1], [2], etc.
            bib_entries = re.findall(r"(?:^|\n)\s*\[(\d+)\]", bib_text)
            # Extraer todos los números citados en el cuerpo
            cited_nums: set[str] = set()
            for cm in numeric_cites:
                if cm.start() < bib_start:
                    cited_nums.update(self._expand_numeric_citation(cm.group(1)))

            for entry_num in bib_entries:
                if entry_num not in cited_nums:
                    entry_pattern = re.compile(
                        rf"(?:^|\n)\s*\[{re.escape(entry_num)}\]",
                        re.MULTILINE,
                    )
                    entry_match = entry_pattern.search(bib_text)
                    if entry_match:
                        abs_pos = bib_start + entry_match.start()
                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=ReferencesIssueType.UNUSED_REFERENCE.value,
                                start_char=abs_pos,
                                end_char=abs_pos + len(entry_match.group()),
                                text=f"[{entry_num}]",
                                explanation=(
                                    f"La referencia [{entry_num}] de la bibliografía "
                                    f"no se cita en el cuerpo del texto."
                                ),
                                suggestion=(
                                    f"Cite la referencia [{entry_num}] en el texto "
                                    f"o elimínela de la bibliografía."
                                ),
                                confidence=0.80,
                                context=self._extract_context(
                                    text, abs_pos, abs_pos + 80
                                ),
                                chapter_index=chapter_index,
                                rule_id="REF_UNUSED_REFERENCE",
                                extra_data={"reference_number": entry_num},
                            )
                        )

        return issues
