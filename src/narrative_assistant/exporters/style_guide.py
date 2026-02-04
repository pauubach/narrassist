"""
Generador de Guía de Estilo Automática.

Analiza el manuscrito y genera una guía de estilo con:
- Decisiones de grafía (José/Jose, María/Maria)
- Lista de entidades canónicas (nombres, lugares, organizaciones)
- Términos específicos y neologismos
- Convenciones de mayúsculas y acentuación
- Análisis de diálogos (raya, comillas angulares, comillas inglesas)
- Análisis de puntuación (punto y coma, puntos suspensivos)
- Análisis de números (cifras vs palabras)
- Estadísticas generales del texto

Útil para:
- Mantener consistencia durante la edición
- Onboarding de nuevos correctores
- Referencia rápida del mundo narrativo
"""

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..entities.models import Entity, EntityType
from ..entities.repository import get_entity_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Enums para estilos detectados
# =============================================================================


class DialogueStyle(Enum):
    """Estilo de diálogos detectado."""

    RAYA = "raya"  # —Hola —dijo
    GUILLEMETS = "guillemets"  # «Hola»
    QUOTES = "quotes"  # "Hola"
    MIXED = "mixed"


class NumberStyle(Enum):
    """Estilo de números detectado."""

    WORDS_UNDER_10 = "words_under_10"
    WORDS_UNDER_100 = "words_under_100"
    ALWAYS_DIGITS = "always_digits"
    MIXED = "mixed"


@dataclass
class SpellingDecision:
    """Decisión de grafía para una entidad o término."""

    canonical_form: str  # Forma canónica elegida
    variants: list[str]  # Variantes encontradas
    frequency: dict[str, int]  # Frecuencia de cada variante
    recommendation: str  # "canonical" o "variant_allowed"
    notes: str = ""  # Notas adicionales


@dataclass
class EntityListing:
    """Listado de una entidad en la guía."""

    type: str  # "CHARACTER", "LOCATION", "ORGANIZATION"
    canonical_name: str
    aliases: list[str]
    importance: str
    first_mention_chapter: int | None = None
    description: str = ""  # Descripción breve (opcional)


@dataclass
class StylePattern:
    """Patrón de estilo detectado en el texto."""

    name: str
    description: str
    frequency: int
    examples: list[str]
    recommendation: str


@dataclass
class TextStatistics:
    """Estadísticas generales del texto."""

    total_words: int
    total_sentences: int
    avg_sentence_length: float
    vocabulary_richness: float  # Type-Token Ratio


@dataclass
class StyleAnalysis:
    """Análisis estilístico del texto."""

    # Diálogos
    dialogue_style: str  # DialogueStyle.value
    dialogue_patterns: list[StylePattern]

    # Puntuación
    punctuation_patterns: list[StylePattern]
    uses_oxford_comma: bool
    semicolon_frequency: str  # 'high', 'medium', 'low', 'none'

    # Números
    number_style: str  # NumberStyle.value
    number_examples: dict[str, list[str]]

    # Mayúsculas
    capitalization_rules: list[StylePattern]

    # Extranjerismos
    foreign_word_style: str  # 'italic', 'quotes', 'none'
    foreign_examples: list[str]

    # Registro general
    predominant_register: str
    formality_level: str  # 'high', 'medium', 'low'

    # Estadísticas
    statistics: TextStatistics

    # Inconsistencias y recomendaciones
    consistency_issues: list[str]
    recommendations: list[str]


@dataclass
class StyleGuide:
    """
    Guía de estilo completa del manuscrito.
    """

    # Metadata del proyecto
    project_name: str
    project_id: int
    generated_date: str

    # Decisiones de grafía
    spelling_decisions: list[SpellingDecision]

    # Entidades del mundo narrativo
    characters: list[EntityListing]
    locations: list[EntityListing]
    organizations: list[EntityListing]

    # Análisis estilístico (opcional - requiere texto)
    style_analysis: StyleAnalysis | None = None

    # Términos especiales (placeholder para futuro)
    special_terms: list[str] = field(default_factory=list)

    # Estadísticas
    total_entities: int = 0
    total_spelling_variants: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convierte la guía a diccionario."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convierte la guía a JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Genera guía de estilo en formato Markdown."""
        lines = []

        # Header
        lines.append(f"# Guía de Estilo - {self.project_name}")
        lines.append("")
        lines.append(f"**Generado:** {self.generated_date}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tabla de contenidos
        lines.append("## Tabla de Contenidos")
        lines.append("")
        toc_num = 1
        lines.append(f"{toc_num}. [Decisiones de Grafía](#decisiones-de-grafía)")
        toc_num += 1
        lines.append(f"{toc_num}. [Personajes](#personajes)")
        toc_num += 1
        lines.append(f"{toc_num}. [Ubicaciones](#ubicaciones)")
        toc_num += 1
        lines.append(f"{toc_num}. [Organizaciones](#organizaciones)")
        toc_num += 1
        if self.style_analysis:
            lines.append(f"{toc_num}. [Análisis Estilístico](#análisis-estilístico)")
            toc_num += 1
        if self.special_terms:
            lines.append(f"{toc_num}. [Términos Especiales](#términos-especiales)")
            toc_num += 1
        lines.append("")
        lines.append("---")
        lines.append("")

        # Decisiones de grafía
        lines.append("## Decisiones de Grafía")
        lines.append("")
        if self.spelling_decisions:
            lines.append("| Forma Canónica | Variantes Encontradas | Frecuencia | Recomendación |")
            lines.append("|----------------|----------------------|------------|---------------|")
            for decision in sorted(
                self.spelling_decisions, key=lambda d: -sum(d.frequency.values())
            ):
                variants_str = ", ".join(decision.variants) if decision.variants else "ninguna"
                freq_total = sum(decision.frequency.values())
                recommendation = (
                    "✓ Usar forma canónica"
                    if decision.recommendation == "canonical"
                    else "⚠ Variantes permitidas"
                )
                lines.append(
                    f"| **{decision.canonical_form}** | {variants_str} | {freq_total} | {recommendation} |"
                )
            lines.append("")
            if any(d.notes for d in self.spelling_decisions):
                lines.append("### Notas:")
                for decision in self.spelling_decisions:
                    if decision.notes:
                        lines.append(f"- **{decision.canonical_form}:** {decision.notes}")
                lines.append("")
        else:
            lines.append("_No se detectaron variaciones de grafía._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Personajes
        lines.append("## Personajes")
        lines.append("")
        if self.characters:
            # Agrupar por importancia (5 niveles: principal, high, medium, low, minimal)
            principal = [c for c in self.characters if c.importance in ("principal", "critical")]
            high_importance = [c for c in self.characters if c.importance == "high"]
            medium_importance = [c for c in self.characters if c.importance == "medium"]
            low_importance = [c for c in self.characters if c.importance == "low"]
            minimal_importance = [c for c in self.characters if c.importance == "minimal"]

            # Protagonistas principales (principal + high)
            protagonists = principal + high_importance
            if protagonists:
                lines.append("### Protagonistas")
                lines.append("")
                for char in sorted(protagonists, key=lambda c: c.canonical_name):
                    lines.append(f"#### {char.canonical_name}")
                    if char.aliases:
                        lines.append(f"**También:** {', '.join(char.aliases)}")
                    if char.first_mention_chapter:
                        lines.append(f"**Primera mención:** Capítulo {char.first_mention_chapter}")
                    if char.description:
                        lines.append(f"{char.description}")
                    lines.append("")

            if medium_importance:
                lines.append("### Personajes Secundarios")
                lines.append("")
                for char in sorted(medium_importance, key=lambda c: c.canonical_name):
                    lines.append(f"- **{char.canonical_name}**")
                    if char.aliases:
                        lines.append(f"  - También: {', '.join(char.aliases)}")
                lines.append("")

            # Menores (low + minimal)
            minor_chars = low_importance + minimal_importance
            if minor_chars:
                lines.append("### Personajes Menores")
                lines.append("")
                minor_names = [
                    c.canonical_name for c in sorted(minor_chars, key=lambda c: c.canonical_name)
                ]
                lines.append(", ".join(minor_names))
                lines.append("")
        else:
            lines.append("_No se detectaron personajes._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Ubicaciones
        lines.append("## Ubicaciones")
        lines.append("")
        if self.locations:
            for loc in sorted(self.locations, key=lambda l: l.canonical_name):
                lines.append(f"- **{loc.canonical_name}**")
                if loc.aliases:
                    lines.append(f"  - También: {', '.join(loc.aliases)}")
            lines.append("")
        else:
            lines.append("_No se detectaron ubicaciones._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Organizaciones
        lines.append("## Organizaciones")
        lines.append("")
        if self.organizations:
            for org in sorted(self.organizations, key=lambda o: o.canonical_name):
                lines.append(f"- **{org.canonical_name}**")
                if org.aliases:
                    lines.append(f"  - También: {', '.join(org.aliases)}")
            lines.append("")
        else:
            lines.append("_No se detectaron organizaciones._")
            lines.append("")

        # Análisis estilístico
        if self.style_analysis:
            lines.append("---")
            lines.append("")
            lines.append("## Análisis Estilístico")
            lines.append("")

            sa = self.style_analysis

            # Resumen general
            lines.append("### Resumen General")
            lines.append("")
            lines.append(f"- **Total de palabras:** {sa.statistics.total_words:,}")
            lines.append(f"- **Total de oraciones:** {sa.statistics.total_sentences:,}")
            lines.append(
                f"- **Longitud media de oración:** {sa.statistics.avg_sentence_length:.1f} palabras"
            )
            lines.append(f"- **Riqueza léxica (TTR):** {sa.statistics.vocabulary_richness:.1%}")
            lines.append("")

            # Diálogos
            lines.append("### Diálogos")
            lines.append("")
            style_labels = {
                "raya": "Raya española (—)",
                "guillemets": "Comillas angulares («»)",
                "quotes": 'Comillas inglesas ("")',
                "mixed": "Estilo mixto",
            }
            lines.append(
                f"**Estilo detectado:** {style_labels.get(sa.dialogue_style, sa.dialogue_style)}"
            )
            lines.append("")
            for pattern in sa.dialogue_patterns:
                lines.append(f"- **{pattern.name}:** {pattern.frequency} ocurrencias")
                if pattern.examples:
                    lines.append(
                        f"  - Ejemplo: _{pattern.examples[0][:50]}..._"
                        if len(pattern.examples[0]) > 50
                        else f"  - Ejemplo: _{pattern.examples[0]}_"
                    )
                lines.append(f"  - {pattern.recommendation}")
            lines.append("")

            # Puntuación
            lines.append("### Puntuación")
            lines.append("")
            lines.append(f"- **Uso de punto y coma:** {sa.semicolon_frequency}")
            lines.append(f"- **Coma de Oxford:** {'Sí' if sa.uses_oxford_comma else 'No'}")
            lines.append("")
            for pattern in sa.punctuation_patterns:
                if pattern.frequency > 0:
                    lines.append(f"- **{pattern.name}:** {pattern.frequency} ocurrencias")
            lines.append("")

            # Números
            lines.append("### Números")
            lines.append("")
            number_labels = {
                "words_under_10": "Palabras para números menores a 10",
                "words_under_100": "Palabras para números menores a 100",
                "always_digits": "Siempre en cifras",
                "mixed": "Estilo mixto",
            }
            lines.append(
                f"**Estilo detectado:** {number_labels.get(sa.number_style, sa.number_style)}"
            )
            lines.append("")
            if sa.number_examples.get("words"):
                lines.append(
                    f"- Ejemplos en palabras: {', '.join(sa.number_examples['words'][:5])}"
                )
            if sa.number_examples.get("digits"):
                lines.append(f"- Ejemplos en cifras: {', '.join(sa.number_examples['digits'][:5])}")
            lines.append("")

            # Mayúsculas
            if sa.capitalization_rules:
                lines.append("### Mayúsculas")
                lines.append("")
                for rule in sa.capitalization_rules:
                    lines.append(f"- **{rule.name}:** {rule.frequency} casos")
                    if rule.examples:
                        lines.append(f"  - Ejemplos: {', '.join(rule.examples[:3])}")
                    lines.append(f"  - {rule.recommendation}")
                lines.append("")

            # Extranjerismos
            if sa.foreign_examples:
                lines.append("### Extranjerismos")
                lines.append("")
                foreign_labels = {
                    "italic": "En cursiva",
                    "quotes": "Entre comillas",
                    "none": "Sin marcado especial",
                }
                lines.append(
                    f"**Tratamiento:** {foreign_labels.get(sa.foreign_word_style, sa.foreign_word_style)}"
                )
                lines.append("")
                lines.append(f"Ejemplos: {', '.join(sa.foreign_examples[:5])}")
                lines.append("")

            # Inconsistencias
            if sa.consistency_issues:
                lines.append("### ⚠️ Inconsistencias Detectadas")
                lines.append("")
                for issue in sa.consistency_issues:
                    lines.append(f"- {issue}")
                lines.append("")

            # Recomendaciones
            if sa.recommendations:
                lines.append("### Recomendaciones")
                lines.append("")
                for rec in sa.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        # Términos especiales
        if self.special_terms:
            lines.append("---")
            lines.append("")
            lines.append("## Términos Especiales")
            lines.append("")
            for term in sorted(self.special_terms):
                lines.append(f"- {term}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("_Guía generada automáticamente por Narrative Assistant_")
        lines.append("")
        lines.append(f"**Total de entidades:** {self.total_entities}")
        lines.append(f"**Variaciones de grafía detectadas:** {self.total_spelling_variants}")
        if self.style_analysis:
            lines.append(
                f"**Inconsistencias de estilo:** {len(self.style_analysis.consistency_issues)}"
            )

        return "\n".join(lines)


def _normalize_text(s: str) -> str:
    """Normaliza string quitando acentos."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def _detect_spelling_variants(entities: list[Entity]) -> list[SpellingDecision]:
    """
    Detecta variaciones de grafía en nombres de entidades.

    Por ejemplo:
    - María / Maria (con/sin acento)
    - José / Jose
    - Dr. Pérez / Doctor Pérez / Pérez
    """
    decisions = []

    for entity in entities:
        all_forms = [entity.canonical_name] + (entity.aliases or [])

        # Contar frecuencias (simplificado - en realidad debería contar en el texto)
        frequency = dict.fromkeys(all_forms, 1)

        # Detectar variantes
        variants = []
        for alias in entity.aliases or []:
            if _normalize_text(alias) == _normalize_text(entity.canonical_name):
                # Misma palabra, diferente acentuación
                variants.append(alias)

        if variants:
            decision = SpellingDecision(
                canonical_form=entity.canonical_name,
                variants=variants,
                frequency=frequency,
                recommendation="canonical",
                notes=f"Se encontraron {len(variants)} variante(s) de grafía. Se recomienda usar siempre la forma canónica.",
            )
            decisions.append(decision)

    return decisions


# =============================================================================
# StyleAnalyzer - Analizador de patrones estilísticos
# =============================================================================


class StyleAnalyzer:
    """Analizador de patrones de estilo en texto narrativo."""

    def __init__(self):
        """Inicializa el analizador con patrones de regex."""
        self.patterns = {
            "raya_dialogue": re.compile(r"—[^—\n]+(?:—[^—\n]*)?"),
            "guillemet_dialogue": re.compile(r"«[^»]+»"),
            "quote_dialogue": re.compile(r'"[^"]+"|"[^"]+"|"[^"]*"'),
            "semicolon": re.compile(r";"),
            "ellipsis": re.compile(r"\.{3}|…"),
            "em_dash": re.compile(r"—"),
            "numbers_digits": re.compile(r"\b\d+\b"),
            "numbers_words": re.compile(
                r"\b(uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
                r"once|doce|trece|catorce|quince|veinte|treinta|cuarenta|"
                r"cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|mil)\b",
                re.IGNORECASE,
            ),
        }

    def analyze(self, text: str) -> StyleAnalysis:
        """Analiza el texto y devuelve el análisis estilístico completo."""
        # Análisis de diálogos
        dialogue_style, dialogue_patterns = self._analyze_dialogues(text)

        # Análisis de puntuación
        punct_patterns, uses_oxford, semicolon_freq = self._analyze_punctuation(text)

        # Análisis de números
        number_style, number_examples = self._analyze_numbers(text)

        # Análisis de mayúsculas
        cap_rules = self._analyze_capitalization(text)

        # Análisis de extranjerismos
        foreign_style, foreign_examples = self._analyze_foreign_words(text)

        # Estadísticas generales
        stats = self._calculate_statistics(text)

        # Detectar inconsistencias
        issues = self._detect_inconsistencies(dialogue_style, number_style, text)

        # Generar recomendaciones
        recommendations = self._generate_recommendations(dialogue_style, number_style, issues)

        return StyleAnalysis(
            dialogue_style=dialogue_style.value,
            dialogue_patterns=dialogue_patterns,
            punctuation_patterns=punct_patterns,
            uses_oxford_comma=uses_oxford,
            semicolon_frequency=semicolon_freq,
            number_style=number_style.value,
            number_examples=number_examples,
            capitalization_rules=cap_rules,
            foreign_word_style=foreign_style,
            foreign_examples=foreign_examples,
            predominant_register="neutral",  # Simplificado
            formality_level="medium",
            statistics=stats,
            consistency_issues=issues,
            recommendations=recommendations,
        )

    def _analyze_dialogues(self, text: str) -> tuple[DialogueStyle, list[StylePattern]]:
        """Analiza el estilo de diálogos."""
        raya_matches = self.patterns["raya_dialogue"].findall(text)
        guillemet_matches = self.patterns["guillemet_dialogue"].findall(text)
        quote_matches = self.patterns["quote_dialogue"].findall(text)

        raya_count = len(raya_matches)
        guillemet_count = len(guillemet_matches)
        quote_count = len(quote_matches)
        total = raya_count + guillemet_count + quote_count

        patterns = []

        if raya_count > 0:
            patterns.append(
                StylePattern(
                    name="Raya española",
                    description="Diálogos marcados con raya (—)",
                    frequency=raya_count,
                    examples=raya_matches[:3],
                    recommendation="Estilo estándar en español",
                )
            )

        if guillemet_count > 0:
            patterns.append(
                StylePattern(
                    name="Comillas angulares",
                    description="Diálogos marcados con « »",
                    frequency=guillemet_count,
                    examples=guillemet_matches[:3],
                    recommendation="Común en ediciones académicas",
                )
            )

        if quote_count > 0:
            patterns.append(
                StylePattern(
                    name="Comillas inglesas",
                    description='Diálogos marcados con " "',
                    frequency=quote_count,
                    examples=quote_matches[:3],
                    recommendation="Más común en traducciones del inglés",
                )
            )

        # Determinar estilo predominante
        if total == 0:
            style = DialogueStyle.RAYA  # Default
        elif raya_count > total * 0.8:
            style = DialogueStyle.RAYA
        elif guillemet_count > total * 0.8:
            style = DialogueStyle.GUILLEMETS
        elif quote_count > total * 0.8:
            style = DialogueStyle.QUOTES
        else:
            style = DialogueStyle.MIXED

        return style, patterns

    def _analyze_punctuation(self, text: str) -> tuple[list[StylePattern], bool, str]:
        """Analiza patrones de puntuación."""
        patterns = []

        # Punto y coma
        semicolons = len(self.patterns["semicolon"].findall(text))
        sentences = len(re.findall(r"[.!?]+", text))

        if sentences > 0:
            ratio = semicolons / sentences
            if ratio > 0.1:
                freq = "alto"
            elif ratio > 0.02:
                freq = "medio"
            elif semicolons > 0:
                freq = "bajo"
            else:
                freq = "ninguno"
        else:
            freq = "ninguno"

        patterns.append(
            StylePattern(
                name="Punto y coma",
                description="Uso de ; en el texto",
                frequency=semicolons,
                examples=[],
                recommendation="Uso moderado recomendado para narrativa",
            )
        )

        # Puntos suspensivos
        ellipsis_matches = self.patterns["ellipsis"].findall(text)
        patterns.append(
            StylePattern(
                name="Puntos suspensivos",
                description="Uso de ... o …",
                frequency=len(ellipsis_matches),
                examples=ellipsis_matches[:3],
                recommendation="Usar con moderación para énfasis",
            )
        )

        # Oxford comma (simplificado - buscar ", y" vs "y")
        oxford_pattern = re.compile(r"\w+,\s+\w+,\s+y\s+\w+")
        oxford_matches = oxford_pattern.findall(text)
        uses_oxford = len(oxford_matches) > 0

        return patterns, uses_oxford, freq

    def _analyze_numbers(self, text: str) -> tuple[NumberStyle, dict[str, list[str]]]:
        """Analiza el estilo de números."""
        digit_matches = self.patterns["numbers_digits"].findall(text)
        word_matches = self.patterns["numbers_words"].findall(text)

        examples = {"digits": digit_matches[:5], "words": word_matches[:5]}

        # Analizar números pequeños (1-10)
        small_digits = [d for d in digit_matches if d.isdigit() and int(d) <= 10]
        small_words_list = [
            "uno",
            "dos",
            "tres",
            "cuatro",
            "cinco",
            "seis",
            "siete",
            "ocho",
            "nueve",
            "diez",
        ]
        small_words = [w for w in word_matches if w.lower() in small_words_list]

        if len(small_digits) > len(small_words) * 2:
            style = NumberStyle.ALWAYS_DIGITS
        elif len(small_words) > len(small_digits) * 2:
            style = NumberStyle.WORDS_UNDER_10
        else:
            style = NumberStyle.MIXED

        return style, examples

    def _analyze_capitalization(self, text: str) -> list[StylePattern]:
        """Analiza reglas de mayúsculas."""
        patterns = []

        # Títulos (el Rey, el Presidente, la Reina)
        title_pattern = re.compile(r"\b(el|la|los|las)\s+([A-Z][a-záéíóúñü]+)\b")
        titles = title_pattern.findall(text)

        if titles:
            examples = [f"{t[0]} {t[1]}" for t in titles[:3]]
            patterns.append(
                StylePattern(
                    name="Títulos con mayúscula",
                    description="Cargos/títulos en mayúscula después de artículo",
                    frequency=len(titles),
                    examples=examples,
                    recommendation="RAE recomienda minúscula para cargos genéricos",
                )
            )

        return patterns

    def _analyze_foreign_words(self, text: str) -> tuple[str, list[str]]:
        """Detecta tratamiento de extranjerismos."""
        # Palabras en cursiva (Markdown)
        italic_pattern = re.compile(r"\*([a-zA-Z]+)\*|_([a-zA-Z]+)_")
        italics = italic_pattern.findall(text)

        # Palabras entre comillas que podrían ser extranjerismos
        quoted = re.compile(r'"([a-zA-Z]+)"').findall(text)

        examples = []

        if italics:
            style = "italic"
            examples = [i[0] or i[1] for i in italics[:5]]
        elif quoted:
            style = "quotes"
            examples = quoted[:5]
        else:
            style = "none"

        return style, examples

    def _calculate_statistics(self, text: str) -> TextStatistics:
        """Calcula estadísticas generales."""
        words = re.findall(r"\b\w+\b", text)
        sentences = re.split(r"[.!?]+", text)
        sentences = [s for s in sentences if s.strip()]

        word_count = len(words)
        sentence_count = len(sentences)
        avg_sentence = word_count / sentence_count if sentence_count else 0

        # Type-Token Ratio
        unique_words = {w.lower() for w in words}
        ttr = len(unique_words) / word_count if word_count else 0

        return TextStatistics(
            total_words=word_count,
            total_sentences=sentence_count,
            avg_sentence_length=round(avg_sentence, 1),
            vocabulary_richness=round(ttr, 3),
        )

    def _detect_inconsistencies(
        self, dialogue_style: DialogueStyle, number_style: NumberStyle, text: str
    ) -> list[str]:
        """Detecta inconsistencias de estilo."""
        issues = []

        if dialogue_style == DialogueStyle.MIXED:
            issues.append(
                "Se detectan múltiples estilos de diálogo (raya, comillas). Considere unificar."
            )

        if number_style == NumberStyle.MIXED:
            issues.append(
                "Uso inconsistente de números en cifras vs palabras. "
                "Considere establecer una regla clara."
            )

        return issues

    def _generate_recommendations(
        self, dialogue_style: DialogueStyle, number_style: NumberStyle, issues: list[str]
    ) -> list[str]:
        """Genera recomendaciones de estilo."""
        recommendations = []

        if dialogue_style == DialogueStyle.RAYA:
            recommendations.append("✓ Uso correcto de raya española para diálogos")

        if number_style == NumberStyle.WORDS_UNDER_10:
            recommendations.append("✓ Números pequeños escritos en palabras (convención literaria)")

        for issue in issues:
            recommendations.append(f"⚠️ {issue}")

        return recommendations


def generate_style_guide(
    project_id: int,
    project_name: str,
    text: str | None = None,
) -> Result[StyleGuide]:
    """
    Genera una guía de estilo completa para un proyecto.

    Args:
        project_id: ID del proyecto
        project_name: Nombre del proyecto
        text: Texto completo del manuscrito (opcional, para análisis estilístico)

    Returns:
        Result con StyleGuide completa
    """
    try:
        from datetime import datetime

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id)

        if not entities:
            logger.warning(f"No entities found for project {project_id}")

        # Separar por tipo
        characters = [e for e in entities if e.entity_type == EntityType.CHARACTER]
        locations = [e for e in entities if e.entity_type == EntityType.LOCATION]
        organizations = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]

        # Detectar decisiones de grafía
        spelling_decisions = _detect_spelling_variants(entities)

        # Crear listados
        character_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in characters
        ]

        location_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in locations
        ]

        organization_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in organizations
        ]

        # Análisis estilístico (si se proporciona texto)
        style_analysis = None
        if text and len(text.strip()) > 100:  # Solo si hay texto suficiente
            try:
                analyzer = StyleAnalyzer()
                style_analysis = analyzer.analyze(text)
                logger.info(f"Style analysis completed for project {project_id}")
            except Exception as e:
                logger.warning(f"Style analysis failed (non-critical): {e}")

        # Crear guía
        style_guide = StyleGuide(
            project_name=project_name,
            project_id=project_id,
            generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            spelling_decisions=spelling_decisions,
            characters=character_listings,
            locations=location_listings,
            organizations=organization_listings,
            style_analysis=style_analysis,
            total_entities=len(entities),
            total_spelling_variants=len(spelling_decisions),
        )

        logger.info(f"Generated style guide for project {project_id}")
        return Result.success(style_guide)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to generate style guide: {str(e)}",
            severity=ErrorSeverity.FATAL,
            user_message=f"Error generando guía de estilo: {str(e)}",
        )
        logger.error(f"Error generating style guide: {e}", exc_info=True)
        return Result.failure(error)


def export_style_guide(
    style_guide: StyleGuide,
    output_path: Path,
    format: str = "both",  # "json", "markdown", "both"
) -> Result[list[Path]]:
    """
    Exporta la guía de estilo a archivo.

    Args:
        style_guide: Guía de estilo generada
        output_path: Path base (sin extensión)
        format: Formato de exportación

    Returns:
        Result con lista de archivos creados
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        exported_files = []

        if format in ("json", "both"):
            json_path = output_path.with_suffix(".json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(style_guide.to_json())
            exported_files.append(json_path)
            logger.info(f"Exported style guide JSON: {json_path}")

        if format in ("markdown", "both"):
            md_path = output_path.with_suffix(".md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(style_guide.to_markdown())
            exported_files.append(md_path)
            logger.info(f"Exported style guide Markdown: {md_path}")

        return Result.success(exported_files)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to export style guide: {str(e)}",
            severity=ErrorSeverity.FATAL,
            user_message=f"Error exportando guía de estilo: {str(e)}",
        )
        logger.error(f"Error exporting style guide: {e}", exc_info=True)
        return Result.failure(error)
