# STEP 5.3: Detector de Cambios de Registro

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 5.1 |

---

## Descripción

Detectar cambios de registro narrativo (formal/informal, técnico/coloquial) que pueden indicar inconsistencias en la voz del narrador o en los diálogos.

Diferencia con STEP 5.2:
- STEP 5.2: Desviaciones de voz por **personaje individual**
- STEP 5.3: Cambios de registro en la **narración general** o entre escenas

---

## Inputs

- Texto completo segmentado por escenas/capítulos
- Perfiles de voz existentes
- Diálogos marcados (para separar narración de diálogos)

---

## Outputs

- `src/narrative_assistant/voice/register.py`
- Alertas de cambios de registro
- Clasificación de registro por sección
- Visualización de variación

---

## Tipos de Registro

| Registro | Características | Ejemplo |
|----------|-----------------|---------|
| `formal_literary` | Vocabulario culto, sintaxis elaborada | "Contempló la vastedad del horizonte" |
| `neutral` | Estándar, equilibrado | "Miró hacia el horizonte" |
| `colloquial` | Informal, cercano | "Se quedó mirando pa'l cielo" |
| `technical` | Jerga especializada | "El sistema límbico procesaba..." |
| `poetic` | Metafórico, lírico | "El cielo sangraba carmesí" |

---

## Implementación

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from collections import Counter
import numpy as np

class RegisterType(Enum):
    FORMAL_LITERARY = "formal_literary"
    NEUTRAL = "neutral"
    COLLOQUIAL = "colloquial"
    TECHNICAL = "technical"
    POETIC = "poetic"

@dataclass
class RegisterAnalysis:
    text_segment: str
    chapter: int
    position: int
    is_dialogue: bool

    primary_register: RegisterType
    register_scores: Dict[RegisterType, float]
    confidence: float

    # Indicadores encontrados
    formal_indicators: List[str]
    colloquial_indicators: List[str]
    technical_terms: List[str]
    poetic_devices: List[str]

@dataclass
class RegisterChange:
    from_register: RegisterType
    to_register: RegisterType
    chapter: int
    position: int
    context_before: str
    context_after: str
    severity: str  # 'high', 'medium', 'low'
    explanation: str

# Indicadores de registro
FORMAL_INDICATORS = {
    # Verbos formales
    'contemplar', 'observar', 'percibir', 'manifestar', 'acontecer',
    'transcurrir', 'acaecer', 'proferir', 'esgrimir', 'denotar',
    # Conectores formales
    'asimismo', 'no obstante', 'sin embargo', 'empero', 'por ende',
    'en consecuencia', 'cabe destacar', 'en virtud de',
    # Vocabulario culto
    'vastedad', 'magnánimo', 'ignominia', 'sempiterno', 'inexorable',
}

COLLOQUIAL_INDICATORS = {
    # Contracciones/elisiones
    "pa'", "pa'l", "pal", "p'a", "to'", "toa", "tos", "tas",
    # Expresiones coloquiales
    'mola', 'flipar', 'currar', '

', 'mogollón', '

',
    'rollo', '

', '

', '

',
    # Muletillas
    'tío', 'tía', 'colega', 'macho', 'chaval',
    # Intensificadores coloquiales
    '

', '

', 'total', '

',
}

TECHNICAL_PATTERNS = [
    # Médicos
    r'\b(diagnóstico|síntoma|patología|etiología|pronóstico)\b',
    # Legales
    r'\b(jurisprudencia|tipificación|prescripción|prevaricación)\b',
    # Tecnológicos
    r'\b(algoritmo|interfaz|protocolo|implementación|parámetro)\b',
    # Científicos
    r'\b(hipótesis|variable|correlación|metodología|paradigma)\b',
]

POETIC_PATTERNS = [
    # Metáforas comunes
    r'(como|cual)\s+\w+\s+(de|del)\s+\w+',  # símiles
    r'\b(susurr|murmur|danz|flot)\w+',  # verbos poéticos
    # Personificación
    r'(el|la)\s+(luna|sol|viento|noche|mar)\s+\w*(aba|ía)',
]

class RegisterAnalyzer:
    def __init__(self):
        self.formal_set = FORMAL_INDICATORS
        self.colloquial_set = COLLOQUIAL_INDICATORS

    def analyze_segment(
        self,
        text: str,
        chapter: int,
        position: int,
        is_dialogue: bool = False
    ) -> RegisterAnalysis:
        """Analiza el registro de un segmento de texto."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        # Encontrar indicadores
        formal_found = [w for w in self.formal_set if w in text_lower]
        colloquial_found = [w for w in self.colloquial_set if w in text_lower]

        technical_found = []
        for pattern in TECHNICAL_PATTERNS:
            technical_found.extend(re.findall(pattern, text_lower))

        poetic_found = []
        for pattern in POETIC_PATTERNS:
            poetic_found.extend(re.findall(pattern, text_lower))

        # Calcular scores
        scores = self._calculate_scores(
            len(words),
            len(formal_found),
            len(colloquial_found),
            len(technical_found),
            len(poetic_found)
        )

        # Determinar registro primario
        primary = max(scores.items(), key=lambda x: x[1])[0]
        confidence = scores[primary]

        return RegisterAnalysis(
            text_segment=text[:200] + "..." if len(text) > 200 else text,
            chapter=chapter,
            position=position,
            is_dialogue=is_dialogue,
            primary_register=primary,
            register_scores=scores,
            confidence=confidence,
            formal_indicators=formal_found,
            colloquial_indicators=colloquial_found,
            technical_terms=[str(t) for t in technical_found[:5]],
            poetic_devices=[str(p) for p in poetic_found[:5]]
        )

    def _calculate_scores(
        self,
        total_words: int,
        formal_count: int,
        colloquial_count: int,
        technical_count: int,
        poetic_count: int
    ) -> Dict[RegisterType, float]:
        """Calcula scores normalizados por tipo de registro."""
        if total_words == 0:
            return {r: 0.2 for r in RegisterType}

        # Normalizar por longitud del texto
        norm = max(total_words / 100, 1)

        formal_score = min(formal_count / norm, 1.0)
        colloquial_score = min(colloquial_count / norm, 1.0)
        technical_score = min(technical_count / norm, 1.0)
        poetic_score = min(poetic_count / norm, 1.0)

        # Score neutral es inverso a los otros
        other_total = formal_score + colloquial_score + technical_score + poetic_score
        neutral_score = max(0, 1 - other_total)

        scores = {
            RegisterType.FORMAL_LITERARY: formal_score,
            RegisterType.NEUTRAL: neutral_score,
            RegisterType.COLLOQUIAL: colloquial_score,
            RegisterType.TECHNICAL: technical_score,
            RegisterType.POETIC: poetic_score,
        }

        # Normalizar para que sumen 1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

class RegisterChangeDetector:
    def __init__(self, analyzer: Optional[RegisterAnalyzer] = None):
        self.analyzer = analyzer or RegisterAnalyzer()
        self.analyses: List[RegisterAnalysis] = []

    def analyze_document(
        self,
        segments: List[Tuple[str, int, int, bool]]  # (text, chapter, position, is_dialogue)
    ) -> List[RegisterAnalysis]:
        """Analiza todos los segmentos del documento."""
        self.analyses = []

        for text, chapter, position, is_dialogue in segments:
            analysis = self.analyzer.analyze_segment(
                text, chapter, position, is_dialogue
            )
            self.analyses.append(analysis)

        return self.analyses

    def detect_changes(
        self,
        min_severity: str = 'medium'
    ) -> List[RegisterChange]:
        """Detecta cambios significativos de registro."""
        changes = []

        # Filtrar solo narración (no diálogos) para comparar
        narrative_analyses = [a for a in self.analyses if not a.is_dialogue]

        for i in range(1, len(narrative_analyses)):
            prev = narrative_analyses[i - 1]
            curr = narrative_analyses[i]

            # Calcular severidad del cambio
            severity = self._calculate_severity(prev, curr)

            if self._should_report(severity, min_severity):
                changes.append(RegisterChange(
                    from_register=prev.primary_register,
                    to_register=curr.primary_register,
                    chapter=curr.chapter,
                    position=curr.position,
                    context_before=prev.text_segment,
                    context_after=curr.text_segment,
                    severity=severity,
                    explanation=self._generate_explanation(prev, curr)
                ))

        return changes

    def _calculate_severity(
        self,
        prev: RegisterAnalysis,
        curr: RegisterAnalysis
    ) -> str:
        """Calcula severidad del cambio de registro."""
        # Distancia entre registros
        register_distance = {
            (RegisterType.FORMAL_LITERARY, RegisterType.COLLOQUIAL): 'high',
            (RegisterType.COLLOQUIAL, RegisterType.FORMAL_LITERARY): 'high',
            (RegisterType.TECHNICAL, RegisterType.COLLOQUIAL): 'high',
            (RegisterType.COLLOQUIAL, RegisterType.TECHNICAL): 'high',
            (RegisterType.POETIC, RegisterType.TECHNICAL): 'medium',
            (RegisterType.TECHNICAL, RegisterType.POETIC): 'medium',
        }

        pair = (prev.primary_register, curr.primary_register)
        if pair in register_distance:
            return register_distance[pair]

        # Si cambia pero no es extremo
        if prev.primary_register != curr.primary_register:
            return 'low'

        return 'none'

    def _should_report(self, severity: str, min_severity: str) -> bool:
        """Determina si debe reportarse según severidad mínima."""
        severity_order = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
        return severity_order.get(severity, 0) >= severity_order.get(min_severity, 0)

    def _generate_explanation(
        self,
        prev: RegisterAnalysis,
        curr: RegisterAnalysis
    ) -> str:
        """Genera explicación del cambio."""
        explanations = []

        if prev.formal_indicators and curr.colloquial_indicators:
            explanations.append(
                f"Cambio de lenguaje formal ('{prev.formal_indicators[0]}') "
                f"a coloquial ('{curr.colloquial_indicators[0]}')"
            )
        elif prev.colloquial_indicators and curr.formal_indicators:
            explanations.append(
                f"Cambio de lenguaje coloquial ('{prev.colloquial_indicators[0]}') "
                f"a formal ('{curr.formal_indicators[0]}')"
            )
        else:
            explanations.append(
                f"Cambio de registro {prev.primary_register.value} "
                f"a {curr.primary_register.value}"
            )

        return "; ".join(explanations)

    def get_register_distribution(self) -> Dict[RegisterType, int]:
        """Devuelve distribución de registros en el documento."""
        distribution = Counter(a.primary_register for a in self.analyses)
        return dict(distribution)
```

---

## Criterio de DONE

```python
from narrative_assistant.voice import (
    RegisterAnalyzer,
    RegisterChangeDetector,
    RegisterType
)

analyzer = RegisterAnalyzer()
detector = RegisterChangeDetector(analyzer)

# Segmentos con diferentes registros
segments = [
    # Formal/literario
    ("Contempló la vastedad del horizonte mientras la melancolía "
     "se apoderaba de su alma. No obstante, mantuvo la compostura.", 1, 0, False),

    # Cambio a coloquial (narración)
    ("El tío se quedó ahí

 mirando pal cielo. "
     "Mola

, ¿no? Pues eso,

.", 1, 500, False),

    # Diálogo (no cuenta para cambios de narración)
    ("—¡Eh, colega! ¿Qué

 haces?", 1, 600, True),

    # Técnico
    ("El diagnóstico revelaba una patología compleja. "
     "La etiología permanecía indeterminada.", 2, 0, False),
]

analyses = detector.analyze_document(segments)
changes = detector.detect_changes(min_severity='medium')

# Verificaciones
assert len(analyses) == 4

# Debe detectar cambio formal -> coloquial
high_severity = [c for c in changes if c.severity == 'high']
assert len(high_severity) >= 1
assert high_severity[0].from_register == RegisterType.FORMAL_LITERARY
assert high_severity[0].to_register == RegisterType.COLLOQUIAL

print(f"✅ Analizados {len(analyses)} segmentos")
print(f"   Cambios detectados: {len(changes)}")
for change in changes:
    print(f"   [{change.severity}] {change.explanation}")
```

---

## Siguiente

[STEP 5.4: Atribución de Hablante](./step-5.4-speaker-attribution.md)
