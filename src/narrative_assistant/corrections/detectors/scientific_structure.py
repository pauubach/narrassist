"""
Detector de estructura de documento científico/académico.

Detecta:
- Secciones obligatorias ausentes según perfil (scientific/essay/technical)
- Secciones en orden incorrecto
- Ausencia de abstract/resumen

Nombre: ScientificStructureDetector (no StructureDetector, para evitar
conflicto con parsers/structure_detector.py que detecta capítulos/escenas).
"""

from __future__ import annotations

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import StructureConfig
from ..types import CorrectionCategory, StructureIssueType

# ============================================================================
# Patrones de detección de secciones
# ============================================================================

# Detectar secciones por header markdown o por línea sola en mayúsculas/título
SECTION_PATTERNS: dict[str, re.Pattern] = {
    "abstract": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:resumen|abstract|sumario)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "introduction": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:introducción|introduction)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "state_of_art": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:estado\s+del\s+arte|antecedentes|"
        r"marco\s+teórico|related\s+work|trabajos?\s+relacionados?|"
        r"revisión\s+(?:de\s+)?(?:la\s+)?literatura)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "methodology": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:metodología|método|methodology|"
        r"methods|diseño\s+experimental|materiales?\s+y\s+métodos?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "results": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:resultados|results|"
        r"experimentación|análisis(?:\s+de\s+resultados)?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "discussion": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:discusión|discussion)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "conclusions": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:conclusiones|conclusions?|"
        r"conclusiones?\s+y\s+(?:trabajos?\s+)?futuros?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "references": re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+\.?\s*)?(?:referencias|bibliografía|"
        r"bibliography|references|fuentes)\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Detección heurística: líneas solas en MAYÚSCULAS que podrían ser headers
HEADING_HEURISTIC = re.compile(
    r"^\s*(?:\d+\.?\s+)?([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,})\s*$", re.MULTILINE
)

# Secciones requeridas por perfil + orden esperado
REQUIRED_SECTIONS: dict[str, list[str]] = {
    "scientific": ["introduction", "methodology", "results", "conclusions", "references"],
    "essay": ["introduction", "conclusions", "references"],
    "technical": ["introduction", "references"],
}

# Orden canónico de secciones para verificar secuencia
SECTION_ORDER = [
    "abstract",
    "introduction",
    "state_of_art",
    "methodology",
    "results",
    "discussion",
    "conclusions",
    "references",
]


class ScientificStructureDetector(BaseDetector):
    """Detecta problemas de estructura en documentos científicos/académicos."""

    def __init__(self, config: StructureConfig | None = None):
        self.config = config or StructureConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.STRUCTURE

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Detectar secciones presentes
        found_sections = self._find_sections(text)

        # 1. Verificar secciones obligatorias
        required = REQUIRED_SECTIONS.get(self.config.profile, [])
        for section in required:
            if section not in found_sections:
                label = self._section_label(section)
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=StructureIssueType.MISSING_SECTION.value,
                        start_char=0,
                        end_char=min(len(text), 50),
                        text=f"(sección ausente: {label})",
                        explanation=(
                            f"El documento no tiene sección de '{label}'. "
                            f"Para un documento de tipo '{self.config.profile}', "
                            f"esta sección es esperada."
                        ),
                        suggestion=f"Añada una sección '{label}' al documento.",
                        confidence=0.80,
                        context="",
                        chapter_index=chapter_index,
                        rule_id="STRUCT_MISSING_SECTION",
                        extra_data={
                            "missing_section": section,
                            "profile": self.config.profile,
                        },
                    )
                )

        # 2. Verificar abstract para perfil scientific
        if self.config.profile == "scientific" and "abstract" not in found_sections:
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StructureIssueType.MISSING_ABSTRACT.value,
                    start_char=0,
                    end_char=min(len(text), 50),
                    text="(sin resumen/abstract)",
                    explanation=(
                        "No se encontró sección de Resumen/Abstract. "
                        "Los artículos científicos generalmente incluyen un resumen inicial."
                    ),
                    suggestion="Añada un Resumen o Abstract al inicio del documento.",
                    confidence=0.75,
                    context="",
                    chapter_index=chapter_index,
                    rule_id="STRUCT_MISSING_ABSTRACT",
                    extra_data={"profile": self.config.profile},
                )
            )

        # 3. Verificar orden de secciones
        if len(found_sections) >= 2:
            order_issues = self._check_order(found_sections, text, chapter_index)
            issues.extend(order_issues)

        return issues

    def _find_sections(self, text: str) -> dict[str, int]:
        """Detecta qué secciones están presentes y en qué posición."""
        found: dict[str, int] = {}

        # Buscar por patrones de sección
        for section_name, pattern in SECTION_PATTERNS.items():
            m = pattern.search(text)
            if m:
                found[section_name] = m.start()

        # Buscar por heurística de líneas en mayúsculas
        for m in HEADING_HEURISTIC.finditer(text):
            heading_text = m.group(1).strip().lower()
            for section_name, pattern in SECTION_PATTERNS.items():
                if section_name not in found:
                    # Verificar si el heading en mayúsculas coincide
                    if pattern.search(heading_text) or pattern.search(m.group(0)):
                        found[section_name] = m.start()

        return found

    def _check_order(
        self,
        found: dict[str, int],
        text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """Verifica que las secciones estén en el orden canónico."""
        issues = []

        # Filtrar solo secciones que están en el orden canónico
        present_ordered = [
            (s, pos)
            for s in SECTION_ORDER
            if (pos := found.get(s)) is not None
        ]

        # Verificar que las posiciones estén en orden creciente
        for i in range(len(present_ordered) - 1):
            section_a, pos_a = present_ordered[i]
            section_b, pos_b = present_ordered[i + 1]

            if pos_a > pos_b:
                label_a = self._section_label(section_a)
                label_b = self._section_label(section_b)
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=StructureIssueType.WRONG_ORDER.value,
                        start_char=pos_b,
                        end_char=min(pos_b + 80, len(text)),
                        text=f"'{label_b}' antes de '{label_a}'",
                        explanation=(
                            f"La sección '{label_b}' aparece antes de '{label_a}'. "
                            f"El orden esperado es: {label_a} → {label_b}."
                        ),
                        suggestion=f"Reordene: '{label_a}' debería preceder a '{label_b}'.",
                        confidence=0.70,
                        context=self._extract_context(text, pos_b, min(pos_b + 80, len(text))),
                        chapter_index=chapter_index,
                        rule_id="STRUCT_WRONG_ORDER",
                        extra_data={
                            "section_before": section_a,
                            "section_after": section_b,
                        },
                    )
                )

        return issues

    @staticmethod
    def _section_label(section: str) -> str:
        """Nombre legible de una sección."""
        return {
            "abstract": "Resumen/Abstract",
            "introduction": "Introducción",
            "state_of_art": "Estado del Arte",
            "methodology": "Metodología",
            "results": "Resultados",
            "discussion": "Discusión",
            "conclusions": "Conclusiones",
            "references": "Referencias",
        }.get(section, section.replace("_", " ").title())
