# STEP 7.3: Generador de Guía de Estilo

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P1 (Alto valor) |
| **Prerequisitos** | STEP 5.1 |

---

## Descripción

Generar automáticamente una guía de estilo basada en el análisis del manuscrito:
- Convenciones de nombres
- Estilo de diálogos (raya vs comillas)
- Convenciones tipográficas
- Registro predominante
- Patrones de puntuación

---

## Inputs

- Texto completo procesado
- Perfiles de voz
- Análisis de registro
- Patrones detectados

---

## Outputs

- `src/narrative_assistant/export/style_guide.py`
- Guía en formato Markdown
- Estadísticas de uso
- Recomendaciones de consistencia

---

## Áreas de Análisis

| Área | Qué se analiza | Output |
|------|----------------|--------|
| Diálogos | Marcadores (raya, comillas), estilo de inciso | Convención detectada |
| Puntuación | Uso de ;, :, ..., — | Patrones frecuentes |
| Mayúsculas | Títulos, cargos, épocas | Reglas inferidas |
| Números | Escritos vs cifras | Umbral detectado |
| Extranjerismos | Cursiva, comillas | Convención usada |

---

## Implementación

```python
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter
from enum import Enum

class DialogueStyle(Enum):
    RAYA = "raya"                # —Hola —dijo
    GUILLEMETS = "guillemets"    # «Hola»
    QUOTES = "quotes"            # "Hola"
    MIXED = "mixed"

class NumberStyle(Enum):
    WORDS_UNDER_10 = "words_under_10"
    WORDS_UNDER_100 = "words_under_100"
    ALWAYS_DIGITS = "always_digits"
    MIXED = "mixed"

@dataclass
class StylePattern:
    name: str
    description: str
    frequency: int
    examples: List[str]
    recommendation: str

@dataclass
class StyleGuide:
    project_id: int
    project_name: str

    # Diálogos
    dialogue_style: DialogueStyle
    dialogue_patterns: List[StylePattern]

    # Puntuación
    punctuation_patterns: List[StylePattern]
    uses_oxford_comma: bool
    semicolon_frequency: str  # 'high', 'medium', 'low', 'none'

    # Números
    number_style: NumberStyle
    number_examples: Dict[str, List[str]]

    # Mayúsculas
    capitalization_rules: List[StylePattern]

    # Extranjerismos
    foreign_word_style: str  # 'italic', 'quotes', 'none'
    foreign_examples: List[str]

    # Registro general
    predominant_register: str
    formality_level: str  # 'high', 'medium', 'low'

    # Estadísticas generales
    total_words: int
    total_sentences: int
    avg_sentence_length: float
    vocabulary_richness: float

    # Recomendaciones
    consistency_issues: List[str]
    recommendations: List[str]

class StyleGuideGenerator:
    def __init__(self):
        self.patterns = {
            'raya_dialogue': re.compile(r'—[^—]+—'),
            'guillemet_dialogue': re.compile(r'«[^»]+»'),
            'quote_dialogue': re.compile(r'"[^"]+"'),
            'semicolon': re.compile(r';'),
            'ellipsis': re.compile(r'\.{3}|…'),
            'em_dash': re.compile(r'—'),
            'numbers_digits': re.compile(r'\b\d+\b'),
            'numbers_words': re.compile(
                r'\b(uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|'
                r'once|doce|trece|catorce|quince|veinte|treinta|cuarenta|'
                r'cincuenta|cien|mil)\b',
                re.IGNORECASE
            ),
        }

    def generate(
        self,
        project_id: int,
        project_name: str,
        text: str
    ) -> StyleGuide:
        """Genera guía de estilo completa."""
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
        issues = self._detect_inconsistencies(
            dialogue_style, number_style, text
        )

        # Generar recomendaciones
        recommendations = self._generate_recommendations(
            dialogue_style, number_style, issues
        )

        return StyleGuide(
            project_id=project_id,
            project_name=project_name,
            dialogue_style=dialogue_style,
            dialogue_patterns=dialogue_patterns,
            punctuation_patterns=punct_patterns,
            uses_oxford_comma=uses_oxford,
            semicolon_frequency=semicolon_freq,
            number_style=number_style,
            number_examples=number_examples,
            capitalization_rules=cap_rules,
            foreign_word_style=foreign_style,
            foreign_examples=foreign_examples,
            predominant_register="neutral",  # Simplificado
            formality_level="medium",
            total_words=stats['words'],
            total_sentences=stats['sentences'],
            avg_sentence_length=stats['avg_sentence_length'],
            vocabulary_richness=stats['ttr'],
            consistency_issues=issues,
            recommendations=recommendations
        )

    def _analyze_dialogues(
        self,
        text: str
    ) -> Tuple[DialogueStyle, List[StylePattern]]:
        """Analiza el estilo de diálogos."""
        raya_count = len(self.patterns['raya_dialogue'].findall(text))
        guillemet_count = len(self.patterns['guillemet_dialogue'].findall(text))
        quote_count = len(self.patterns['quote_dialogue'].findall(text))

        total = raya_count + guillemet_count + quote_count

        patterns = []

        if raya_count > 0:
            patterns.append(StylePattern(
                name="Raya española",
                description="Diálogos marcados con raya (—)",
                frequency=raya_count,
                examples=self.patterns['raya_dialogue'].findall(text)[:3],
                recommendation="Estilo estándar en español"
            ))

        if guillemet_count > 0:
            patterns.append(StylePattern(
                name="Comillas angulares",
                description="Diálogos marcados con « »",
                frequency=guillemet_count,
                examples=self.patterns['guillemet_dialogue'].findall(text)[:3],
                recommendation="Común en ediciones académicas"
            ))

        if quote_count > 0:
            patterns.append(StylePattern(
                name="Comillas inglesas",
                description='Diálogos marcados con " "',
                frequency=quote_count,
                examples=self.patterns['quote_dialogue'].findall(text)[:3],
                recommendation="Más común en traducciones del inglés"
            ))

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

    def _analyze_punctuation(
        self,
        text: str
    ) -> Tuple[List[StylePattern], bool, str]:
        """Analiza patrones de puntuación."""
        patterns = []

        # Punto y coma
        semicolons = len(self.patterns['semicolon'].findall(text))
        sentences = len(re.findall(r'[.!?]+', text))

        if sentences > 0:
            ratio = semicolons / sentences
            if ratio > 0.1:
                freq = 'high'
            elif ratio > 0.02:
                freq = 'medium'
            elif semicolons > 0:
                freq = 'low'
            else:
                freq = 'none'
        else:
            freq = 'none'

        patterns.append(StylePattern(
            name="Punto y coma",
            description=f"Uso de ; en el texto",
            frequency=semicolons,
            examples=[],
            recommendation="Uso moderado recomendado para narrativa"
        ))

        # Puntos suspensivos
        ellipsis = len(self.patterns['ellipsis'].findall(text))
        patterns.append(StylePattern(
            name="Puntos suspensivos",
            description="Uso de ... o …",
            frequency=ellipsis,
            examples=self.patterns['ellipsis'].findall(text)[:3],
            recommendation="Usar con moderación para énfasis"
        ))

        # Oxford comma (simplificado)
        oxford_pattern = re.compile(r'\w+,\s+\w+,?\s+y\s+\w+')
        oxford_matches = oxford_pattern.findall(text)
        uses_oxford = any(',' in m.split(' y ')[0][-2:] for m in oxford_matches if ' y ' in m)

        return patterns, uses_oxford, freq

    def _analyze_numbers(
        self,
        text: str
    ) -> Tuple[NumberStyle, Dict[str, List[str]]]:
        """Analiza el estilo de números."""
        digit_matches = self.patterns['numbers_digits'].findall(text)
        word_matches = self.patterns['numbers_words'].findall(text)

        examples = {
            'digits': digit_matches[:5],
            'words': word_matches[:5]
        }

        # Analizar números pequeños (1-10)
        small_digits = [d for d in digit_matches if d.isdigit() and int(d) <= 10]
        small_words = [w for w in word_matches
                      if w.lower() in ['uno', 'dos', 'tres', 'cuatro', 'cinco',
                                       'seis', 'siete', 'ocho', 'nueve', 'diez']]

        if len(small_digits) > len(small_words) * 2:
            style = NumberStyle.ALWAYS_DIGITS
        elif len(small_words) > len(small_digits) * 2:
            style = NumberStyle.WORDS_UNDER_10
        else:
            style = NumberStyle.MIXED

        return style, examples

    def _analyze_capitalization(self, text: str) -> List[StylePattern]:
        """Analiza reglas de mayúsculas."""
        patterns = []

        # Títulos (el Rey, el Presidente)
        title_pattern = re.compile(r'\b(el|la|los|las)\s+([A-Z][a-záéíóúñ]+)\b')
        titles = title_pattern.findall(text)

        if titles:
            patterns.append(StylePattern(
                name="Títulos con mayúscula",
                description="Cargos/títulos en mayúscula después de artículo",
                frequency=len(titles),
                examples=[f"{t[0]} {t[1]}" for t in titles[:3]],
                recommendation="RAE recomienda minúscula para cargos genéricos"
            ))

        return patterns

    def _analyze_foreign_words(
        self,
        text: str
    ) -> Tuple[str, List[str]]:
        """Detecta tratamiento de extranjerismos."""
        # Palabras en cursiva (HTML/Markdown)
        italic_pattern = re.compile(r'\*([a-zA-Z]+)\*|_([a-zA-Z]+)_')
        italics = italic_pattern.findall(text)

        # Palabras entre comillas que podrían ser extranjerismos
        quoted = re.compile(r'"([a-zA-Z]+)"').findall(text)

        examples = []

        if italics:
            style = 'italic'
            examples = [i[0] or i[1] for i in italics[:5]]
        elif quoted:
            style = 'quotes'
            examples = quoted[:5]
        else:
            style = 'none'

        return style, examples

    def _calculate_statistics(self, text: str) -> Dict[str, Any]:
        """Calcula estadísticas generales."""
        words = re.findall(r'\b\w+\b', text)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]

        word_count = len(words)
        sentence_count = len(sentences)
        avg_sentence = word_count / sentence_count if sentence_count else 0

        # Type-Token Ratio
        unique_words = set(w.lower() for w in words)
        ttr = len(unique_words) / word_count if word_count else 0

        return {
            'words': word_count,
            'sentences': sentence_count,
            'avg_sentence_length': round(avg_sentence, 1),
            'ttr': round(ttr, 3)
        }

    def _detect_inconsistencies(
        self,
        dialogue_style: DialogueStyle,
        number_style: NumberStyle,
        text: str
    ) -> List[str]:
        """Detecta inconsistencias de estilo."""
        issues = []

        if dialogue_style == DialogueStyle.MIXED:
            issues.append(
                "Se detectan múltiples estilos de diálogo (raya, comillas). "
                "Considere unificar."
            )

        if number_style == NumberStyle.MIXED:
            issues.append(
                "Uso inconsistente de números en cifras vs palabras. "
                "Considere establecer una regla clara."
            )

        return issues

    def _generate_recommendations(
        self,
        dialogue_style: DialogueStyle,
        number_style: NumberStyle,
        issues: List[str]
    ) -> List[str]:
        """Genera recomendaciones de estilo."""
        recommendations = []

        if dialogue_style == DialogueStyle.RAYA:
            recommendations.append(
                "✓ Uso correcto de raya española para diálogos"
            )

        if number_style == NumberStyle.WORDS_UNDER_10:
            recommendations.append(
                "✓ Números pequeños escritos en palabras (convención literaria)"
            )

        for issue in issues:
            recommendations.append(f"⚠️ {issue}")

        return recommendations

    def export_to_markdown(self, guide: StyleGuide) -> str:
        """Exporta guía a Markdown."""
        lines = [
            f"# Guía de Estilo: {guide.project_name}",
            "",
            "## Resumen General",
            "",
            f"- **Total de palabras:** {guide.total_words:,}",
            f"- **Total de oraciones:** {guide.total_sentences:,}",
            f"- **Longitud media de oración:** {guide.avg_sentence_length} palabras",
            f"- **Riqueza léxica (TTR):** {guide.vocabulary_richness:.1%}",
            "",
            "## Diálogos",
            "",
            f"**Estilo detectado:** {guide.dialogue_style.value}",
            "",
        ]

        for pattern in guide.dialogue_patterns:
            lines.extend([
                f"### {pattern.name}",
                f"- Frecuencia: {pattern.frequency}",
                f"- {pattern.recommendation}",
                ""
            ])

        lines.extend([
            "## Puntuación",
            "",
            f"- **Uso de punto y coma:** {guide.semicolon_frequency}",
            f"- **Coma de Oxford:** {'Sí' if guide.uses_oxford_comma else 'No'}",
            "",
            "## Números",
            "",
            f"**Estilo detectado:** {guide.number_style.value}",
            "",
        ])

        if guide.consistency_issues:
            lines.extend([
                "## ⚠️ Inconsistencias Detectadas",
                "",
            ])
            for issue in guide.consistency_issues:
                lines.append(f"- {issue}")
            lines.append("")

        if guide.recommendations:
            lines.extend([
                "## Recomendaciones",
                "",
            ])
            for rec in guide.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)
```

---

## Criterio de DONE

```python
from narrative_assistant.export import StyleGuideGenerator, DialogueStyle

generator = StyleGuideGenerator()

text = """
—Buenos días —dijo Juan mientras entraba—. ¿Cómo estás?
—Muy bien, gracias —respondió María—. Han pasado tres años desde la última vez.

El sol brillaba con fuerza; era uno de esos días de verano que invitan a pasear.
María tenía 35 años y había vivido en Madrid durante quince de ellos.

«Qué extraño», pensó Juan. No esperaba encontrarla allí después de tanto tiempo.
"""

guide = generator.generate(
    project_id=1,
    project_name="Novela de prueba",
    text=text
)

# Verificaciones
assert guide.dialogue_style in [DialogueStyle.RAYA, DialogueStyle.MIXED]
assert guide.total_words > 50
assert guide.avg_sentence_length > 0

# Exportar
md = generator.export_to_markdown(guide)
assert "Guía de Estilo" in md
assert "Diálogos" in md

print(f"✅ Guía de estilo generada")
print(md[:800])
```

---

## Siguiente

[STEP 7.4: CLI Principal](./step-7.4-cli.md)
