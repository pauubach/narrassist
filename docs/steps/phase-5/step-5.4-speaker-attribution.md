# STEP 5.4: Atribución de Hablante en Diálogos

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | XL (8-12 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 1.4, STEP 5.1 |

---

## Descripción

Determinar **quién dice qué** en los diálogos. Este es uno de los problemas más difíciles del NLP narrativo porque:

1. Muchos diálogos no tienen verbo de habla explícito
2. El patrón de alternancia puede romperse
3. Hay diálogos intercalados con narración

---

## Inputs

- Diálogos detectados (STEP 1.4)
- Entidades con posiciones
- Perfiles de voz (STEP 5.1)

---

## Outputs

- `src/narrative_assistant/voice/speaker_attribution.py`
- Hablante asignado a cada intervención
- Confianza de la atribución
- Alertas cuando hay ambigüedad

---

## Algoritmo

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ALGORITMO DE ATRIBUCIÓN DE HABLANTE                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. DETECCIÓN EXPLÍCITA (alta confianza)                                │
│     └── "—Hola —dijo Juan"  → Juan                                      │
│     └── "Juan respondió: —Hola" → Juan                                  │
│                                                                          │
│  2. ALTERNANCIA (media confianza)                                       │
│     └── Si A habla, luego B, luego probablemente A                      │
│     └── Requiere detectar participantes de la escena                    │
│                                                                          │
│  3. PERFIL DE VOZ (baja confianza)                                      │
│     └── Comparar estilo con perfiles conocidos                          │
│     └── Solo si 1 y 2 no funcionan                                      │
│                                                                          │
│  4. VALIDACIÓN MANUAL                                                   │
│     └── Marcar intervenciones con baja confianza                        │
│     └── Permitir corrección del usuario                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Patrones de Verbo de Habla

```python
# Verbos de habla en español
SPEECH_VERBS = {
    # Neutros
    'decir', 'dijo', 'dice', 'dije', 'dijeron', 'dirá',
    'hablar', 'habló', 'habla',
    'responder', 'respondió', 'responde',
    'contestar', 'contestó', 'contesta',
    'añadir', 'añadió', 'añade',
    'agregar', 'agregó', 'agrega',
    'continuar', 'continuó', 'continúa',

    # Emocionales
    'gritar', 'gritó', 'grita',
    'susurrar', 'susurró', 'susurra',
    'murmurar', 'murmuró', 'murmura',
    'exclamar', 'exclamó', 'exclama',
    'gemir', 'gimió', 'gime',
    'sollozar', 'sollozó', 'solloza',

    # Interrogativos
    'preguntar', 'preguntó', 'pregunta',
    'inquirir', 'inquirió', 'inquiere',
    'interrogar', 'interrogó', 'interroga',

    # Otros
    'comentar', 'comentó', 'comenta',
    'explicar', 'explicó', 'explica',
    'admitir', 'admitió', 'admite',
    'confesar', 'confesó', 'confiesa',
    'insistir', 'insistió', 'insiste',
    'ordenar', 'ordenó', 'ordena',
    'sugerir', 'sugirió', 'sugiere',
}
```

---

## Implementación

```python
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

class AttributionConfidence(Enum):
    HIGH = "high"      # Verbo de habla explícito
    MEDIUM = "medium"  # Alternancia clara
    LOW = "low"        # Inferido por contexto/perfil
    UNKNOWN = "unknown"

@dataclass
class DialogueAttribution:
    dialogue_id: int
    text: str
    start_char: int
    end_char: int
    chapter: int

    # Atribución
    speaker_id: Optional[int] = None
    speaker_name: Optional[str] = None
    confidence: AttributionConfidence = AttributionConfidence.UNKNOWN

    # Evidencia
    attribution_method: str = ""
    speech_verb: Optional[str] = None
    context_snippet: str = ""

@dataclass
class SceneParticipants:
    chapter: int
    scene_start: int
    scene_end: int
    participants: List[int]  # entity_ids

class SpeakerAttributor:
    def __init__(
        self,
        entities: List['Entity'],
        voice_profiles: Optional[Dict[int, 'VoiceProfile']] = None
    ):
        self.entities = {e.id: e for e in entities}
        self.entity_names = {e.canonical_name.lower(): e.id for e in entities}
        # Añadir aliases
        for e in entities:
            for alias in getattr(e, 'aliases', []):
                self.entity_names[alias.lower()] = e.id

        self.voice_profiles = voice_profiles or {}

    def attribute_dialogues(
        self,
        dialogues: List['Dialogue'],
        entity_mentions: List[Tuple[int, int, int]]  # (entity_id, start, end)
    ) -> List[DialogueAttribution]:
        """Atribuye hablante a cada diálogo."""
        attributions = []

        # Ordenar diálogos por posición
        sorted_dialogues = sorted(dialogues, key=lambda d: d.start_char)

        # Contexto de escena actual
        current_participants: List[int] = []
        last_speaker: Optional[int] = None

        for i, dialogue in enumerate(sorted_dialogues):
            attr = DialogueAttribution(
                dialogue_id=i,
                text=dialogue.text,
                start_char=dialogue.start_char,
                end_char=dialogue.end_char,
                chapter=dialogue.chapter
            )

            # 1. Intentar detección explícita
            explicit = self._detect_explicit_speaker(dialogue, entity_mentions)
            if explicit:
                attr.speaker_id = explicit[0]
                attr.speaker_name = self.entities[explicit[0]].canonical_name
                attr.confidence = AttributionConfidence.HIGH
                attr.attribution_method = "explicit_verb"
                attr.speech_verb = explicit[1]
                last_speaker = explicit[0]
                attributions.append(attr)
                continue

            # 2. Actualizar participantes de escena
            scene_entities = self._get_nearby_entities(
                dialogue.start_char, entity_mentions, window=500
            )
            if scene_entities:
                current_participants = scene_entities

            # 3. Intentar alternancia
            if last_speaker and len(current_participants) == 2:
                other_speaker = [p for p in current_participants if p != last_speaker]
                if other_speaker:
                    attr.speaker_id = other_speaker[0]
                    attr.speaker_name = self.entities[other_speaker[0]].canonical_name
                    attr.confidence = AttributionConfidence.MEDIUM
                    attr.attribution_method = "alternation"
                    last_speaker = other_speaker[0]
                    attributions.append(attr)
                    continue

            # 4. Intentar perfil de voz
            if self.voice_profiles and current_participants:
                best_match = self._match_voice_profile(dialogue.text, current_participants)
                if best_match:
                    attr.speaker_id = best_match
                    attr.speaker_name = self.entities[best_match].canonical_name
                    attr.confidence = AttributionConfidence.LOW
                    attr.attribution_method = "voice_profile"
                    last_speaker = best_match
                    attributions.append(attr)
                    continue

            # 5. Sin atribución clara
            attr.confidence = AttributionConfidence.UNKNOWN
            attr.attribution_method = "none"
            attributions.append(attr)

        return attributions

    def _detect_explicit_speaker(
        self,
        dialogue: 'Dialogue',
        entity_mentions: List[Tuple[int, int, int]]
    ) -> Optional[Tuple[int, str]]:
        """Detecta hablante explícito por verbo de habla."""
        # Buscar en contexto después del diálogo
        context_after = dialogue.context_after if hasattr(dialogue, 'context_after') else ""

        # Patrón: "—Texto —verbo Nombre" o "—Texto. \nNombre verbo"
        patterns = [
            # "—dijo Juan"
            r'—\s*(' + '|'.join(SPEECH_VERBS) + r')\s+(\w+)',
            # "Juan dijo:"
            r'(\w+)\s+(' + '|'.join(SPEECH_VERBS) + r')\s*:?\s*$',
        ]

        for pattern in patterns:
            match = re.search(pattern, context_after, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Determinar cuál grupo es el nombre
                for group in groups:
                    name_lower = group.lower()
                    if name_lower in self.entity_names:
                        entity_id = self.entity_names[name_lower]
                        verb = [g for g in groups if g.lower() in SPEECH_VERBS][0]
                        return (entity_id, verb)

        # Buscar mención de entidad cerca
        for entity_id, start, end in entity_mentions:
            # Si la mención está justo antes o después del diálogo
            if (dialogue.start_char - 100 <= start <= dialogue.start_char or
                dialogue.end_char <= start <= dialogue.end_char + 100):
                # Verificar si hay verbo de habla cerca
                context = context_after[:100] if context_after else ""
                for verb in SPEECH_VERBS:
                    if verb in context.lower():
                        return (entity_id, verb)

        return None

    def _get_nearby_entities(
        self,
        position: int,
        entity_mentions: List[Tuple[int, int, int]],
        window: int = 500
    ) -> List[int]:
        """Obtiene entidades mencionadas cerca de una posición."""
        nearby = set()
        for entity_id, start, end in entity_mentions:
            if abs(start - position) <= window:
                nearby.add(entity_id)
        return list(nearby)

    def _match_voice_profile(
        self,
        text: str,
        candidates: List[int]
    ) -> Optional[int]:
        """Intenta matching por perfil de voz."""
        if not candidates or not self.voice_profiles:
            return None

        best_match = None
        best_score = 0.0

        # Calcular características del texto
        text_lower = text.lower()
        uses_usted = 'usted' in text_lower
        uses_tu = 'tú' in text_lower
        word_count = len(text.split())

        for entity_id in candidates:
            if entity_id not in self.voice_profiles:
                continue

            profile = self.voice_profiles[entity_id]
            score = 0.0

            # Matching de formalidad
            if uses_usted and profile.uses_usted:
                score += 0.3
            if uses_tu and profile.uses_tu:
                score += 0.3

            # Matching de longitud (si está cerca del promedio)
            if profile.avg_intervention_length > 0:
                length_diff = abs(word_count - profile.avg_intervention_length)
                if length_diff < profile.avg_intervention_length * 0.5:
                    score += 0.2

            # Matching de muletillas
            for filler in profile.filler_words:
                if filler in text_lower:
                    score += 0.2
                    break

            if score > best_score:
                best_score = score
                best_match = entity_id

        return best_match if best_score >= 0.3 else None

    def get_attribution_stats(
        self,
        attributions: List[DialogueAttribution]
    ) -> Dict[str, any]:
        """Genera estadísticas de atribución."""
        total = len(attributions)
        by_confidence = {
            'high': sum(1 for a in attributions if a.confidence == AttributionConfidence.HIGH),
            'medium': sum(1 for a in attributions if a.confidence == AttributionConfidence.MEDIUM),
            'low': sum(1 for a in attributions if a.confidence == AttributionConfidence.LOW),
            'unknown': sum(1 for a in attributions if a.confidence == AttributionConfidence.UNKNOWN),
        }

        by_method = {}
        for a in attributions:
            by_method[a.attribution_method] = by_method.get(a.attribution_method, 0) + 1

        return {
            'total_dialogues': total,
            'by_confidence': by_confidence,
            'by_method': by_method,
            'attribution_rate': (total - by_confidence['unknown']) / total if total > 0 else 0
        }

# Constante para verbos de habla
SPEECH_VERBS = {
    'decir', 'dijo', 'dice', 'dije', 'dijeron',
    'hablar', 'habló', 'habla',
    'responder', 'respondió', 'responde',
    'contestar', 'contestó', 'contesta',
    'añadir', 'añadió', 'añade',
    'gritar', 'gritó', 'grita',
    'susurrar', 'susurró', 'susurra',
    'murmurar', 'murmuró', 'murmura',
    'exclamar', 'exclamó', 'exclama',
    'preguntar', 'preguntó', 'pregunta',
    'comentar', 'comentó', 'comenta',
}
```

---

## Criterio de DONE

```python
from narrative_assistant.voice import SpeakerAttributor, AttributionConfidence

class MockEntity:
    def __init__(self, id, name, aliases=None):
        self.id = id
        self.canonical_name = name
        self.aliases = aliases or []

class MockDialogue:
    def __init__(self, text, start, end, chapter, context_after=""):
        self.text = text
        self.start_char = start
        self.end_char = end
        self.chapter = chapter
        self.context_after = context_after

entities = [
    MockEntity(1, "Juan", ["Juanito"]),
    MockEntity(2, "María"),
]

attributor = SpeakerAttributor(entities)

dialogues = [
    MockDialogue("¡Hola!", 100, 110, 1, " —dijo Juan con una sonrisa."),
    MockDialogue("¿Cómo estás?", 200, 220, 1, ""),  # Sin atribución explícita
    MockDialogue("Muy bien, gracias.", 300, 330, 1, " —respondió María."),
]

entity_mentions = [
    (1, 115, 119),  # "Juan" después del primer diálogo
    (2, 335, 340),  # "María" después del tercer diálogo
]

attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

# Verificar
assert attributions[0].speaker_name == "Juan"
assert attributions[0].confidence == AttributionConfidence.HIGH

assert attributions[2].speaker_name == "María"
assert attributions[2].confidence == AttributionConfidence.HIGH

# El segundo puede ser por alternancia
# (depende de la implementación)

stats = attributor.get_attribution_stats(attributions)
print(f"✅ Atribuidos {len(attributions)} diálogos")
print(f"   Tasa de atribución: {stats['attribution_rate']:.1%}")
print(f"   Alta confianza: {stats['by_confidence']['high']}")
print(f"   Media confianza: {stats['by_confidence']['medium']}")
print(f"   Sin atribuir: {stats['by_confidence']['unknown']}")
```

---

## Siguiente

[STEP 6.1: Declaración de Focalización](../phase-6/step-6.1-focalization-declaration.md)
