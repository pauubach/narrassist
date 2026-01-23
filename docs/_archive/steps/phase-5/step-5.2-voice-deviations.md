# STEP 5.2: Detector de Desviaciones de Voz

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

Detectar cuando un personaje "habla diferente" a su patrón establecido. Esto puede indicar:
- Error de escritura (el autor olvidó cómo habla el personaje)
- Desarrollo intencional del personaje
- Influencia de otro personaje o situación

---

## Inputs

- Perfiles de voz por personaje (STEP 5.1)
- Nueva intervención a evaluar
- Umbral de desviación configurable

---

## Outputs

- `src/narrative_assistant/voice/deviations.py`
- Alertas de desviaciones significativas
- Métricas específicas que desvían
- Contexto para revisión

---

## Tipos de Desviaciones

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `formality_shift` | Cambio en nivel de formalidad | Personaje informal dice "usted" |
| `length_anomaly` | Intervención muy larga/corta | Personaje lacónico habla mucho |
| `vocabulary_shift` | Uso de vocabulario atípico | Personaje culto usa jerga |
| `filler_anomaly` | Muletilla nueva o ausente | Nueva muletilla aparece |
| `punctuation_shift` | Cambio en estilo de puntuación | Sin exclamaciones cuando siempre las usa |

---

## Implementación

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum
import re
from collections import Counter

class DeviationType(Enum):
    FORMALITY_SHIFT = "formality_shift"
    LENGTH_ANOMALY = "length_anomaly"
    VOCABULARY_SHIFT = "vocabulary_shift"
    FILLER_ANOMALY = "filler_anomaly"
    PUNCTUATION_SHIFT = "punctuation_shift"

@dataclass
class VoiceDeviation:
    deviation_type: DeviationType
    entity_id: int
    entity_name: str
    intervention_text: str
    chapter: int
    position: int

    # Detalles de la desviación
    expected_value: str
    found_value: str
    deviation_score: float  # 0-1, mayor = más desviación

    explanation: str
    suggestion: Optional[str] = None

@dataclass
class DeviationConfig:
    # Umbrales de desviación
    formality_threshold: float = 0.3  # Diferencia mínima para alertar
    length_std_threshold: float = 2.0  # Desviaciones estándar
    min_interventions_for_profile: int = 5  # Mínimo para considerar perfil estable

class VoiceDeviationDetector:
    def __init__(
        self,
        profiles: Dict[int, 'VoiceProfile'],
        config: Optional[DeviationConfig] = None
    ):
        self.profiles = profiles
        self.config = config or DeviationConfig()

        # Calcular estadísticas adicionales por perfil
        self._precompute_stats()

    def _precompute_stats(self) -> None:
        """Precalcula estadísticas para detección."""
        self.length_stats: Dict[int, tuple] = {}  # entity_id -> (mean, std)

        for entity_id, profile in self.profiles.items():
            if profile.total_interventions > 0:
                mean_len = profile.avg_intervention_length
                # Estimación de std basada en características típicas
                # En implementación completa, se calcularía de los datos originales
                estimated_std = mean_len * 0.5  # Heurística
                self.length_stats[entity_id] = (mean_len, estimated_std)

    def check_intervention(
        self,
        entity_id: int,
        text: str,
        chapter: int,
        position: int
    ) -> List[VoiceDeviation]:
        """Verifica una intervención contra el perfil del personaje."""
        deviations = []

        profile = self.profiles.get(entity_id)
        if not profile:
            return []

        # Solo alertar si tenemos suficientes datos
        if profile.total_interventions < self.config.min_interventions_for_profile:
            return []

        entity_name = profile.entity_name

        # 1. Verificar formalidad
        formality_dev = self._check_formality(profile, text, entity_name, chapter, position)
        if formality_dev:
            deviations.append(formality_dev)

        # 2. Verificar longitud
        length_dev = self._check_length(profile, text, entity_name, chapter, position)
        if length_dev:
            deviations.append(length_dev)

        # 3. Verificar muletillas
        filler_dev = self._check_fillers(profile, text, entity_name, chapter, position)
        if filler_dev:
            deviations.append(filler_dev)

        # 4. Verificar puntuación
        punct_dev = self._check_punctuation(profile, text, entity_name, chapter, position)
        if punct_dev:
            deviations.append(punct_dev)

        return deviations

    def _check_formality(
        self,
        profile: 'VoiceProfile',
        text: str,
        entity_name: str,
        chapter: int,
        position: int
    ) -> Optional[VoiceDeviation]:
        """Detecta cambios en nivel de formalidad."""
        text_lower = text.lower()

        # Calcular formalidad de esta intervención
        formal_markers = sum(1 for w in ['usted', 'señor', 'señora', 'disculpe']
                            if w in text_lower)
        informal_markers = sum(1 for w in ['tú', 'tío', 'tía', 'mola', 'flipar']
                              if w in text_lower)

        total = formal_markers + informal_markers
        if total == 0:
            return None

        current_formality = formal_markers / total

        # Comparar con perfil
        diff = abs(current_formality - profile.formality_score)

        if diff >= self.config.formality_threshold:
            direction = "más formal" if current_formality > profile.formality_score else "más informal"

            return VoiceDeviation(
                deviation_type=DeviationType.FORMALITY_SHIFT,
                entity_id=profile.entity_id,
                entity_name=entity_name,
                intervention_text=text,
                chapter=chapter,
                position=position,
                expected_value=f"Formalidad: {profile.formality_score:.0%}",
                found_value=f"Formalidad: {current_formality:.0%}",
                deviation_score=diff,
                explanation=f"{entity_name} habla {direction} de lo habitual",
                suggestion="Verificar si es intencional o error de caracterización"
            )

        return None

    def _check_length(
        self,
        profile: 'VoiceProfile',
        text: str,
        entity_name: str,
        chapter: int,
        position: int
    ) -> Optional[VoiceDeviation]:
        """Detecta longitudes de intervención anómalas."""
        word_count = len(text.split())

        if profile.entity_id not in self.length_stats:
            return None

        mean_len, std_len = self.length_stats[profile.entity_id]
        if std_len == 0:
            return None

        z_score = abs(word_count - mean_len) / std_len

        if z_score >= self.config.length_std_threshold:
            direction = "más larga" if word_count > mean_len else "más corta"

            return VoiceDeviation(
                deviation_type=DeviationType.LENGTH_ANOMALY,
                entity_id=profile.entity_id,
                entity_name=entity_name,
                intervention_text=text,
                chapter=chapter,
                position=position,
                expected_value=f"~{mean_len:.0f} palabras",
                found_value=f"{word_count} palabras",
                deviation_score=min(z_score / 4, 1.0),  # Normalizar
                explanation=f"Intervención {direction} de lo habitual para {entity_name}",
                suggestion="Verificar si la longitud es apropiada para este momento"
            )

        return None

    def _check_fillers(
        self,
        profile: 'VoiceProfile',
        text: str,
        entity_name: str,
        chapter: int,
        position: int
    ) -> Optional[VoiceDeviation]:
        """Detecta uso anómalo de muletillas."""
        text_lower = text.lower()

        # Muletillas conocidas del personaje
        expected_fillers = set(profile.filler_words.keys())

        # Muletillas en esta intervención
        found_fillers: Set[str] = set()
        filler_patterns = [
            r'\b(bueno|pues|vamos|mira|oye|eh|ah)\b',
            r'\b(o sea|es decir|en plan|¿sabes\?)\b',
        ]
        for pattern in filler_patterns:
            for match in re.finditer(pattern, text_lower):
                found_fillers.add(match.group(0))

        # Detectar muletillas nuevas
        new_fillers = found_fillers - expected_fillers

        if new_fillers and expected_fillers:
            return VoiceDeviation(
                deviation_type=DeviationType.FILLER_ANOMALY,
                entity_id=profile.entity_id,
                entity_name=entity_name,
                intervention_text=text,
                chapter=chapter,
                position=position,
                expected_value=f"Muletillas: {', '.join(list(expected_fillers)[:3])}",
                found_value=f"Nueva muletilla: {', '.join(new_fillers)}",
                deviation_score=0.6,
                explanation=f"{entity_name} usa muletilla(s) que no son habituales en él/ella",
                suggestion="Verificar consistencia del habla del personaje"
            )

        return None

    def _check_punctuation(
        self,
        profile: 'VoiceProfile',
        text: str,
        entity_name: str,
        chapter: int,
        position: int
    ) -> Optional[VoiceDeviation]:
        """Detecta cambios en patrones de puntuación."""
        exclamations = text.count('!')
        questions = text.count('?')

        # Si el personaje usa muchas exclamaciones pero esta no tiene ninguna
        if profile.avg_exclamations_per_intervention > 1.0 and exclamations == 0:
            return VoiceDeviation(
                deviation_type=DeviationType.PUNCTUATION_SHIFT,
                entity_id=profile.entity_id,
                entity_name=entity_name,
                intervention_text=text,
                chapter=chapter,
                position=position,
                expected_value=f"~{profile.avg_exclamations_per_intervention:.1f} exclamaciones",
                found_value="0 exclamaciones",
                deviation_score=0.5,
                explanation=f"{entity_name} habitualmente usa exclamaciones pero aquí no",
                suggestion="Verificar si la falta de exclamaciones es intencional"
            )

        # Si el personaje no usa exclamaciones pero esta tiene muchas
        if profile.avg_exclamations_per_intervention < 0.2 and exclamations > 2:
            return VoiceDeviation(
                deviation_type=DeviationType.PUNCTUATION_SHIFT,
                entity_id=profile.entity_id,
                entity_name=entity_name,
                intervention_text=text,
                chapter=chapter,
                position=position,
                expected_value=f"~{profile.avg_exclamations_per_intervention:.1f} exclamaciones",
                found_value=f"{exclamations} exclamaciones",
                deviation_score=0.6,
                explanation=f"{entity_name} no suele usar exclamaciones pero aquí usa {exclamations}",
                suggestion="Verificar si el énfasis es apropiado para el personaje"
            )

        return None

    def check_all_interventions(
        self,
        interventions: List['DialogueIntervention']
    ) -> List[VoiceDeviation]:
        """Verifica todas las intervenciones y devuelve desviaciones."""
        all_deviations = []

        for intervention in interventions:
            deviations = self.check_intervention(
                entity_id=intervention.entity_id,
                text=intervention.text,
                chapter=intervention.chapter,
                position=intervention.position
            )
            all_deviations.extend(deviations)

        # Ordenar por score de desviación
        return sorted(all_deviations, key=lambda d: -d.deviation_score)
```

---

## Criterio de DONE

```python
from narrative_assistant.voice import (
    VoiceProfileBuilder,
    VoiceDeviationDetector,
    DialogueIntervention,
    DeviationType
)

# Construir perfiles
builder = VoiceProfileBuilder()
training_interventions = [
    # Personaje formal (5+ intervenciones para perfil estable)
    DialogueIntervention(1, "Buenos días, señor.", 1, 100),
    DialogueIntervention(1, "¿Podría usted ayudarme?", 1, 200),
    DialogueIntervention(1, "Muchas gracias por su amabilidad.", 1, 300),
    DialogueIntervention(1, "Disculpe las molestias, señora.", 1, 400),
    DialogueIntervention(1, "Le agradezco su paciencia.", 1, 500),
]

profiles = builder.build_profiles(training_interventions)

# Detector
detector = VoiceDeviationDetector(profiles)

# Intervención que desvía (personaje formal hablando informal)
deviations = detector.check_intervention(
    entity_id=1,
    text="¡Eh, tío! ¡Qué pasa! Mola mucho esto, ¿no?",
    chapter=3,
    position=1000
)

# Debe detectar desviación de formalidad
assert len(deviations) >= 1
assert any(d.deviation_type == DeviationType.FORMALITY_SHIFT for d in deviations)

print(f"✅ Detectadas {len(deviations)} desviaciones")
for dev in deviations:
    print(f"  [{dev.deviation_type.value}] {dev.explanation}")
    print(f"    Esperado: {dev.expected_value}")
    print(f"    Encontrado: {dev.found_value}")
```

---

## Siguiente

[STEP 5.3: Cambios de Registro](./step-5.3-register-changes.md)
