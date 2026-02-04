# STEP 5.1: Perfiles de Voz por Personaje

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P2 (Post-validación) |
| **Prerequisitos** | STEP 1.4 |

---

## Descripción

Construir perfiles estilísticos de voz para cada personaje basándose en sus diálogos. Esto permite detectar cuando un personaje "habla diferente" a su patrón establecido.

Métricas a extraer:
- Longitud media de intervención
- Riqueza léxica (Type-Token Ratio)
- Uso de muletillas características
- Nivel de formalidad (tú/usted, vocabulario)
- Patrones sintácticos frecuentes

---

## Inputs

- Diálogos detectados (STEP 1.4)
- Atribuciones de hablante
- Texto completo para contexto

---

## Outputs

- `src/narrative_assistant/voice/profiles.py`
- Perfil de voz por personaje
- Métricas calculadas
- Base para comparación

---

## Modelo de Datos

```python
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import Counter

@dataclass
class VoiceProfile:
    entity_id: int
    entity_name: str

    # Métricas básicas
    total_interventions: int = 0
    total_words: int = 0
    avg_intervention_length: float = 0.0  # Palabras por intervención

    # Riqueza léxica
    vocabulary_size: int = 0  # Tipos únicos
    type_token_ratio: float = 0.0  # TTR = tipos / tokens

    # Formalidad
    formality_score: float = 0.5  # 0 = muy informal, 1 = muy formal
    uses_usted: bool = False
    uses_tu: bool = False

    # Muletillas y patrones
    filler_words: Dict[str, int] = field(default_factory=dict)  # Palabra -> frecuencia
    characteristic_phrases: List[str] = field(default_factory=list)
    frequent_sentence_starters: Dict[str, int] = field(default_factory=dict)

    # Puntuación y estilo
    avg_exclamations_per_intervention: float = 0.0
    avg_questions_per_intervention: float = 0.0
    uses_ellipsis: bool = False

    # Vocabulario característico
    distinctive_words: List[str] = field(default_factory=list)  # Palabras más usadas vs. otros personajes

    # Embeddings para comparación
    style_embedding: Optional[List[float]] = None

@dataclass
class DialogueIntervention:
    entity_id: int
    text: str
    chapter: int
    position: int
```

---

## Implementación

```python
import re
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
import numpy as np

# Palabras funcionales (stopwords) para excluir de análisis léxico
STOPWORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'al', 'a', 'en',
    'con', 'por', 'para', 'y', 'e', 'o', 'u', 'que', 'se', 'su', 'sus',
    'lo', 'le', 'les', 'me', 'te', 'nos', 'es', 'son', 'era', 'fue',
    'no', 'sí', 'ya', 'muy', 'más', 'pero', 'sin', 'como', 'si',
}

# Muletillas comunes en español
FILLER_PATTERNS = [
    r'\b(bueno|pues|vamos|mira|oye|eh|ah|uf|ay|hombre|mujer|tío|tía)\b',
    r'\b(o sea|es decir|en plan|¿sabes\?|¿no\?|¿vale\?|¿entiendes\?)\b',
    r'\b(tipo|como que|básicamente|literalmente|totalmente)\b',
]

# Indicadores de formalidad
FORMAL_INDICATORS = {
    'usted', 'ustedes', 'señor', 'señora', 'don', 'doña',
    'disculpe', 'perdone', 'permítame', 'le ruego',
}

INFORMAL_INDICATORS = {
    'tú', 'vosotros', 'tío', 'tía', 'colega', 'chaval',
    'mola', 'flipar', 'currar', '

', 'mogollón',
}

class VoiceProfileBuilder:
    def __init__(self):
        self.profiles: Dict[int, VoiceProfile] = {}
        self.all_words: Counter = Counter()  # Para calcular palabras distintivas

    def build_profiles(
        self,
        interventions: List[DialogueIntervention]
    ) -> Dict[int, VoiceProfile]:
        """Construye perfiles de voz para todos los personajes."""
        # Agrupar intervenciones por personaje
        by_entity: Dict[int, List[DialogueIntervention]] = defaultdict(list)
        for intervention in interventions:
            by_entity[intervention.entity_id].append(intervention)

        # Construir perfil para cada personaje
        for entity_id, entity_interventions in by_entity.items():
            profile = self._build_single_profile(entity_id, entity_interventions)
            self.profiles[entity_id] = profile

        # Calcular palabras distintivas (comparando entre personajes)
        self._calculate_distinctive_words()

        return self.profiles

    def _build_single_profile(
        self,
        entity_id: int,
        interventions: List[DialogueIntervention]
    ) -> VoiceProfile:
        """Construye perfil para un solo personaje."""
        profile = VoiceProfile(
            entity_id=entity_id,
            entity_name=f"Entity {entity_id}",  # Se actualiza externamente
            total_interventions=len(interventions)
        )

        all_text = " ".join(i.text for i in interventions)
        words = self._tokenize(all_text)
        profile.total_words = len(words)

        if not words:
            return profile

        # Longitud media
        profile.avg_intervention_length = profile.total_words / profile.total_interventions

        # Riqueza léxica
        word_counter = Counter(w.lower() for w in words if w.lower() not in STOPWORDS)
        profile.vocabulary_size = len(word_counter)
        profile.type_token_ratio = profile.vocabulary_size / len(words) if words else 0

        # Actualizar contador global
        self.all_words.update(word_counter)

        # Formalidad
        profile.formality_score = self._calculate_formality(all_text, words)
        profile.uses_usted = bool(re.search(r'\busted\b', all_text, re.IGNORECASE))
        profile.uses_tu = bool(re.search(r'\btú\b', all_text, re.IGNORECASE))

        # Muletillas
        profile.filler_words = self._extract_fillers(all_text)

        # Patrones de puntuación
        exclamations = sum(i.text.count('!') for i in interventions)
        questions = sum(i.text.count('?') for i in interventions)
        profile.avg_exclamations_per_intervention = exclamations / len(interventions)
        profile.avg_questions_per_intervention = questions / len(interventions)
        profile.uses_ellipsis = '...' in all_text or '…' in all_text

        # Inicios de frase frecuentes
        profile.frequent_sentence_starters = self._extract_starters(interventions)

        return profile

    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto en palabras."""
        return re.findall(r'\b\w+\b', text)

    def _calculate_formality(self, text: str, words: List[str]) -> float:
        """Calcula score de formalidad (0-1)."""
        text_lower = text.lower()
        words_set = set(w.lower() for w in words)

        formal_count = sum(1 for w in FORMAL_INDICATORS if w in words_set or w in text_lower)
        informal_count = sum(1 for w in INFORMAL_INDICATORS if w in words_set or w in text_lower)

        total = formal_count + informal_count
        if total == 0:
            return 0.5  # Neutral

        return formal_count / total

    def _extract_fillers(self, text: str) -> Dict[str, int]:
        """Extrae muletillas y su frecuencia."""
        fillers = Counter()
        for pattern in FILLER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                fillers[match.group(0).lower()] += 1
        return dict(fillers)

    def _extract_starters(
        self,
        interventions: List[DialogueIntervention]
    ) -> Dict[str, int]:
        """Extrae inicios de frase frecuentes."""
        starters = Counter()
        for intervention in interventions:
            # Primera palabra de cada oración
            sentences = re.split(r'[.!?]+', intervention.text)
            for sentence in sentences:
                words = sentence.strip().split()
                if words:
                    starter = words[0].lower()
                    if len(starter) > 2:  # Ignorar muy cortas
                        starters[starter] += 1

        # Devolver top 5
        return dict(starters.most_common(5))

    def _calculate_distinctive_words(self) -> None:
        """Calcula palabras distintivas por personaje."""
        total_words = sum(self.all_words.values())
        if total_words == 0:
            return

        for entity_id, profile in self.profiles.items():
            # Palabras del personaje
            interventions_text = ""  # Se necesitaría guardar
            # Por simplicidad, usar las palabras más frecuentes del perfil
            # En implementación completa, calcular TF-IDF

            # Placeholder: usar palabras con alta frecuencia relativa
            profile.distinctive_words = list(profile.filler_words.keys())[:5]

    def compare_profiles(
        self,
        profile1: VoiceProfile,
        profile2: VoiceProfile
    ) -> float:
        """Compara dos perfiles, devuelve similitud (0-1)."""
        scores = []

        # Comparar longitud media
        if profile1.avg_intervention_length and profile2.avg_intervention_length:
            len_diff = abs(profile1.avg_intervention_length - profile2.avg_intervention_length)
            len_score = 1 / (1 + len_diff / 10)  # Normalizar
            scores.append(len_score)

        # Comparar TTR
        ttr_diff = abs(profile1.type_token_ratio - profile2.type_token_ratio)
        scores.append(1 - ttr_diff)

        # Comparar formalidad
        form_diff = abs(profile1.formality_score - profile2.formality_score)
        scores.append(1 - form_diff)

        # Comparar muletillas compartidas
        fillers1 = set(profile1.filler_words.keys())
        fillers2 = set(profile2.filler_words.keys())
        if fillers1 or fillers2:
            jaccard = len(fillers1 & fillers2) / len(fillers1 | fillers2)
            scores.append(jaccard)

        return sum(scores) / len(scores) if scores else 0.5

    def generate_report(self, entity_id: int) -> str:
        """Genera reporte legible del perfil de voz."""
        profile = self.profiles.get(entity_id)
        if not profile:
            return f"No se encontró perfil para entidad {entity_id}"

        lines = [
            f"# Perfil de Voz: {profile.entity_name}",
            "",
            f"**Intervenciones:** {profile.total_interventions}",
            f"**Palabras totales:** {profile.total_words}",
            f"**Longitud media:** {profile.avg_intervention_length:.1f} palabras/intervención",
            "",
            "## Riqueza Léxica",
            f"- Vocabulario único: {profile.vocabulary_size} palabras",
            f"- Type-Token Ratio: {profile.type_token_ratio:.3f}",
            "",
            "## Estilo",
            f"- Formalidad: {profile.formality_score:.1%}",
            f"- Usa 'usted': {'Sí' if profile.uses_usted else 'No'}",
            f"- Usa 'tú': {'Sí' if profile.uses_tu else 'No'}",
            f"- Exclamaciones/intervención: {profile.avg_exclamations_per_intervention:.2f}",
            f"- Preguntas/intervención: {profile.avg_questions_per_intervention:.2f}",
            "",
        ]

        if profile.filler_words:
            lines.append("## Muletillas")
            for word, count in sorted(profile.filler_words.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"- '{word}': {count} veces")
            lines.append("")

        if profile.frequent_sentence_starters:
            lines.append("## Inicios frecuentes")
            for starter, count in profile.frequent_sentence_starters.items():
                lines.append(f"- '{starter}': {count} veces")

        return "\n".join(lines)
```

---

## Criterio de DONE

```python
from narrative_assistant.voice import VoiceProfileBuilder, DialogueIntervention

builder = VoiceProfileBuilder()

# Simular intervenciones de dos personajes diferentes
interventions = [
    # Personaje 1: formal, educado
    DialogueIntervention(1, "Buenos días, señor. ¿Podría usted indicarme dónde se encuentra la biblioteca?", 1, 100),
    DialogueIntervention(1, "Muchas gracias por su amabilidad. Disculpe las molestias.", 1, 200),

    # Personaje 2: informal, coloquial
    DialogueIntervention(2, "¡Eh, tío! ¿Qué pasa? Mola, ¿no?", 1, 300),
    DialogueIntervention(2, "Pues mira, o sea, es que flipas con esto...", 1, 400),
    DialogueIntervention(2, "¡Venga, vamos!", 1, 500),
]

profiles = builder.build_profiles(interventions)

# Verificar diferencias
profile1 = profiles[1]
profile2 = profiles[2]

# El personaje 1 debe ser más formal
assert profile1.formality_score > profile2.formality_score
assert profile1.uses_usted == True
assert profile2.uses_tu == True or 'tío' in profile2.filler_words

# El personaje 2 debe tener más muletillas
assert len(profile2.filler_words) >= len(profile1.filler_words)

# Comparar perfiles
similarity = builder.compare_profiles(profile1, profile2)
assert similarity < 0.7  # Deben ser diferentes

print(f"✅ Perfiles construidos para {len(profiles)} personajes")
print(f"   Similitud entre perfiles: {similarity:.1%}")
print(builder.generate_report(1))
```

---

## Siguiente

[STEP 5.2: Desviaciones de Voz](./step-5.2-voice-deviations.md)
