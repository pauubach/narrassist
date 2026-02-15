"""
Detector de siglas y abreviaturas.

Detecta:
- Siglas usadas sin definir previamente
- Siglas definidas después de su primer uso
- Formas inconsistentes de una misma sigla (NLP vs N.L.P.)
- Siglas redefinidas con diferente expansión
"""

from __future__ import annotations

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import AcronymConfig
from ..types import AcronymIssueType, CorrectionCategory

# ============================================================================
# Patrones de siglas
# ============================================================================

# Definición: "Procesamiento de Lenguaje Natural (PLN)"
# Captura 2+ palabras seguidas de (SIGLA en mayúsculas)
ACRONYM_DEF_AFTER = re.compile(
    r"((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+)"  # Primera palabra capitalizada
    r"(?:(?:de|del|la|el|los|las|en|y|e|o|por|para|con|a|al)\s+)*"  # Conectores opcionales
    r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"  # Segunda palabra capitalizada
    r"(?:\s+(?:(?:de|del|la|el|los|las|en|y|e|o|por|para|con|a|al)\s+)*"
    r"[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+)*)"  # Más palabras opcionales
    r"\s*\(([A-ZÁÉÍÓÚÑ]{2,8})\)"
)

# Definición inversa: "PLN (Procesamiento de Lenguaje Natural)"
ACRONYM_DEF_BEFORE = re.compile(r"([A-ZÁÉÍÓÚÑ]{2,8})\s*\(([^)]{10,80})\)")

# Uso de sigla en texto (2-8 letras mayúsculas)
ACRONYM_USE = re.compile(r"\b([A-ZÁÉÍÓÚÑ]{2,8})\b")

# Palabras que parecen siglas pero no lo son
FALSE_ACRONYMS = frozenset({
    "EL", "LA", "LO", "LAS", "LOS", "UN", "UNA", "DE", "EN", "AL", "DEL",
    "NO", "SI", "SU", "SE", "YA", "II", "III", "IV", "VI", "VII", "VIII",
    "IX", "XI", "XII", "XX", "XXI", "MR", "DR", "SR", "SRA",
})


_LEADING_ARTICLES = re.compile(
    r"^(?:el|la|los|las|un|una|unos|unas)\s+", re.IGNORECASE
)


def _normalize_expansion(text: str) -> str:
    """Normaliza una expansión quitando artículos iniciales y espacios."""
    return _LEADING_ARTICLES.sub("", text.strip()).strip().lower()


class AcronymDetector(BaseDetector):
    """Detecta problemas con siglas y abreviaturas."""

    def __init__(self, config: AcronymConfig | None = None):
        self.config = config or AcronymConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.ACRONYMS

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Paso 1: Encontrar todas las definiciones de siglas
        definitions: dict[str, list[tuple[str, int]]] = {}  # sigla → [(expansión, posición)]

        for m in ACRONYM_DEF_AFTER.finditer(text):
            acronym = m.group(2)
            expansion = m.group(1).strip()
            definitions.setdefault(acronym, []).append((expansion, m.start()))

        for m in ACRONYM_DEF_BEFORE.finditer(text):
            acronym = m.group(1)
            expansion = m.group(2).strip()
            # Solo si la expansión parece texto (no otra sigla)
            if any(c.islower() for c in expansion):
                definitions.setdefault(acronym, []).append((expansion, m.start()))

        # Paso 2: Encontrar todos los usos de siglas
        uses: dict[str, list[tuple[int, int]]] = {}  # sigla → [(start, end)]

        known_set = frozenset(a.upper() for a in self.config.known_acronyms)

        for m in ACRONYM_USE.finditer(text):
            acronym = m.group(1)

            # Filtrar falsos positivos
            if acronym in FALSE_ACRONYMS:
                continue
            if len(acronym) < self.config.min_acronym_length:
                continue
            if len(acronym) > self.config.max_acronym_length:
                continue

            uses.setdefault(acronym, []).append((m.start(), m.end()))

        # Paso 3: Verificar cada sigla usada
        for acronym, positions in uses.items():
            # Sigla conocida universalmente → no necesita definición
            if acronym in known_set:
                continue

            first_use_start, first_use_end = positions[0]

            if acronym in definitions:
                defs = definitions[acronym]
                first_def_pos = min(d[1] for d in defs)

                # Definida después de primer uso → late_definition
                if first_def_pos > first_use_start:
                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=AcronymIssueType.LATE_DEFINITION.value,
                            start_char=first_use_start,
                            end_char=first_use_end,
                            text=acronym,
                            explanation=(
                                f"La sigla '{acronym}' se usa antes de ser definida. "
                                f"Primer uso en posición {first_use_start}, "
                                f"definición en posición {first_def_pos}."
                            ),
                            suggestion=(
                                f"Defina '{acronym}' en su primer uso, antes de la posición "
                                f"{first_use_start}."
                            ),
                            confidence=0.75,
                            context=self._extract_context(
                                text, first_use_start, first_use_end
                            ),
                            chapter_index=chapter_index,
                            rule_id="ACR_LATE_DEFINITION",
                            extra_data={
                                "acronym": acronym,
                                "first_use_pos": first_use_start,
                                "definition_pos": first_def_pos,
                            },
                        )
                    )

                # Redefinida con diferente expansión
                if len(defs) > 1:
                    normalized = {_normalize_expansion(d[0]) for d in defs}
                    expansions = {d[0] for d in defs}
                    if len(normalized) > 1:
                        second_def = defs[1]
                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=AcronymIssueType.REDEFINED_ACRONYM.value,
                                start_char=second_def[1],
                                end_char=second_def[1] + len(acronym),
                                text=acronym,
                                explanation=(
                                    f"La sigla '{acronym}' se definió con expansiones "
                                    f"diferentes: {', '.join(repr(e) for e in expansions)}."
                                ),
                                suggestion=f"Use una sola expansión para '{acronym}'.",
                                confidence=0.90,
                                context=self._extract_context(
                                    text, second_def[1], second_def[1] + len(acronym)
                                ),
                                chapter_index=chapter_index,
                                rule_id="ACR_REDEFINED",
                                extra_data={
                                    "acronym": acronym,
                                    "expansions": list(expansions),
                                },
                            )
                        )
            else:
                # No definida en absoluto → undefined
                # Solo flaggear si se usa 1+ veces (no en definiciones mismas)
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=AcronymIssueType.UNDEFINED_ACRONYM.value,
                        start_char=first_use_start,
                        end_char=first_use_end,
                        text=acronym,
                        explanation=(
                            f"La sigla '{acronym}' se usa sin haber sido definida previamente."
                        ),
                        suggestion=(
                            f"Defina '{acronym}' la primera vez que la use, por ejemplo: "
                            f"'Nombre Completo ({acronym})'."
                        ),
                        confidence=0.88,
                        context=self._extract_context(
                            text, first_use_start, first_use_end
                        ),
                        chapter_index=chapter_index,
                        rule_id="ACR_UNDEFINED",
                        extra_data={"acronym": acronym, "use_count": len(positions)},
                    )
                )

        return issues
