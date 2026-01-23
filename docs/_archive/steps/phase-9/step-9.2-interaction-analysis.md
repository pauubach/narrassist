# STEP 9.2: Análisis de Interacciones

> **Fase**: 9 - Grafo de Relaciones (Post-MVP)
> **Complejidad**: M (4-6 horas)
> **Prioridad**: P2
> **Dependencias**: STEP 9.1 (Entity Relationships)

---

## Descripción

Análisis de cómo interactúan las entidades cuando coinciden en escena. Detecta patrones de comportamiento, coherencia en las reacciones, y genera alertas cuando un personaje actúa de forma inconsistente con su relación establecida.

---

## Objetivos

1. Detectar interacciones entre entidades en el texto
2. Clasificar tipo de interacción (diálogo, acción, pensamiento)
3. Evaluar coherencia entre interacción y relación establecida
4. Generar alertas por comportamientos inconsistentes

---

## Modelo de Datos

```python
class InteractionType(Enum):
    """Tipos de interacción entre entidades."""
    DIALOGUE = "dialogue"           # Conversación directa
    ACTION_TOWARDS = "action"       # Acción de uno hacia otro
    THOUGHT_ABOUT = "thought"       # Pensamiento sobre otro
    OBSERVATION = "observation"     # Observación de uno sobre otro
    PHYSICAL_CONTACT = "physical"   # Contacto físico
    GIFT_EXCHANGE = "gift"          # Intercambio de objetos


class InteractionTone(Enum):
    """Tono de la interacción."""
    HOSTILE = "hostile"
    COLD = "cold"
    NEUTRAL = "neutral"
    WARM = "warm"
    AFFECTIONATE = "affectionate"


@dataclass
class EntityInteraction:
    """Una interacción específica entre entidades."""
    id: str
    project_id: int

    # Participantes
    initiator_id: str           # Quien inicia la interacción
    receiver_id: str            # Quien la recibe

    # Clasificación
    interaction_type: InteractionType
    tone: InteractionTone

    # Ubicación
    chapter: int
    scene_index: Optional[int]
    text_excerpt: str           # Fragmento de texto
    start_char: int
    end_char: int

    # Análisis
    sentiment_score: float = 0.0  # -1 a 1
    intensity: float = 0.5        # 0 a 1

    # Coherencia
    expected_tone: Optional[InteractionTone] = None  # Basado en relación
    is_coherent: bool = True
    coherence_note: str = ""


@dataclass
class InteractionPattern:
    """Patrón de interacción entre dos entidades."""
    entity1_id: str
    entity2_id: str

    # Estadísticas
    total_interactions: int
    interactions_by_type: dict[InteractionType, int]
    average_tone: InteractionTone
    tone_variance: float        # Qué tan variable es el tono

    # Evolución
    tone_trend: str             # "improving", "deteriorating", "stable"
    first_interaction_chapter: int
    last_interaction_chapter: int
```

---

## Componentes

### 1. InteractionDetector

```python
class InteractionDetector:
    """Detecta interacciones en el texto."""

    def detect_dialogue_interaction(
        self,
        dialogue: str,
        speaker: Entity,
        context_entities: list[Entity]
    ) -> list[EntityInteraction]:
        """Detecta a quién se dirige un diálogo."""
        ...

    def detect_action_interaction(
        self,
        sentence: str,
        subject: Entity,
        context_entities: list[Entity]
    ) -> Optional[EntityInteraction]:
        """Detecta acciones de una entidad hacia otra."""
        # Patrones: "X golpeó a Y", "X abrazó a Y", "X miró a Y"
        ...

    def classify_tone(self, text: str) -> InteractionTone:
        """Clasifica el tono de una interacción."""
        # Usa lexicones de sentimiento y patrones
        ...
```

### 2. CoherenceChecker

```python
class InteractionCoherenceChecker:
    """Verifica coherencia entre interacciones y relaciones."""

    # Expectativas por tipo de relación
    EXPECTED_TONES = {
        RelationType.FRIEND: [InteractionTone.WARM, InteractionTone.AFFECTIONATE],
        RelationType.ENEMY: [InteractionTone.HOSTILE, InteractionTone.COLD],
        RelationType.LOVER: [InteractionTone.AFFECTIONATE, InteractionTone.WARM],
        RelationType.RIVAL: [InteractionTone.COLD, InteractionTone.HOSTILE],
        RelationType.PARENT: [InteractionTone.WARM, InteractionTone.NEUTRAL],
    }

    def check_coherence(
        self,
        interaction: EntityInteraction,
        relationship: EntityRelationship
    ) -> tuple[bool, str]:
        """
        Verifica si la interacción es coherente con la relación.

        Returns:
            (is_coherent, explanation)
        """
        expected = self.EXPECTED_TONES.get(relationship.relation_type, [])
        if interaction.tone in expected:
            return True, ""

        # Permitir variaciones si hay justificación narrativa
        if self._has_narrative_justification(interaction, relationship):
            return True, "Justified deviation"

        return False, f"Expected {expected}, got {interaction.tone}"

    def _has_narrative_justification(self, interaction, relationship) -> bool:
        """Busca si hay un cambio de relación que justifique el tono."""
        ...
```

### 3. PatternAnalyzer

```python
class InteractionPatternAnalyzer:
    """Analiza patrones de interacción."""

    def analyze_pair(
        self,
        entity1_id: str,
        entity2_id: str,
        interactions: list[EntityInteraction]
    ) -> InteractionPattern:
        """Genera análisis de patrón para un par de entidades."""
        ...

    def detect_anomalies(
        self,
        pattern: InteractionPattern,
        new_interaction: EntityInteraction
    ) -> Optional[Alert]:
        """Detecta si una nueva interacción rompe el patrón establecido."""
        ...

    def generate_interaction_report(
        self,
        project_id: int
    ) -> dict[tuple[str, str], InteractionPattern]:
        """Genera reporte de todos los patrones de interacción."""
        ...
```

---

## Alertas Generadas

| Código | Descripción | Severidad |
|--------|-------------|-----------|
| `INT_TONE_MISMATCH` | Tono no corresponde con relación | Warning |
| `INT_SUDDEN_CHANGE` | Cambio brusco de tono sin justificación | Warning |
| `INT_MISSING_REACTION` | Personaje no reacciona a interacción importante | Info |
| `INT_ONE_SIDED` | Interacciones siempre iniciadas por el mismo | Info |
| `INT_ENEMY_FRIENDLY` | Enemigos interactúan amistosamente | Warning |
| `INT_FRIEND_HOSTILE` | Amigos interactúan hostilmente | Warning |

---

## Ejemplo de Detección

### Entrada
```
Relación establecida: Pedro y María son ENEMY (desde cap 2)

Capítulo 5:
"Pedro se acercó a María con una sonrisa.
—Me alegro de verte —dijo, abrazándola con cariño."
```

### Análisis
```python
interaction = EntityInteraction(
    initiator_id="pedro_001",
    receiver_id="maria_001",
    interaction_type=InteractionType.DIALOGUE,
    tone=InteractionTone.AFFECTIONATE,  # Detectado por "sonrisa", "alegro", "cariño"
    chapter=5,
    text_excerpt="Pedro se acercó a María...",
    is_coherent=False,
    coherence_note="ENEMY relationship expects HOSTILE/COLD tone"
)

alert = Alert(
    code="INT_ENEMY_FRIENDLY",
    message="Pedro (enemigo de María) interactúa afectuosamente en cap 5",
    suggestion="Verificar si hay reconciliación entre caps 2-5"
)
```

---

## Integración con Sentimiento (STEP 8.1)

Cuando el análisis de sentimiento esté disponible:

```python
def classify_tone_with_sentiment(self, text: str) -> InteractionTone:
    """Usa análisis de sentimiento para clasificar tono."""
    sentiment = self.sentiment_analyzer.analyze(text)

    if sentiment.score < -0.5:
        return InteractionTone.HOSTILE
    elif sentiment.score < -0.2:
        return InteractionTone.COLD
    elif sentiment.score < 0.2:
        return InteractionTone.NEUTRAL
    elif sentiment.score < 0.5:
        return InteractionTone.WARM
    else:
        return InteractionTone.AFFECTIONATE
```

---

## Criterios de Aceptación

- [ ] Detector identifica interacciones en diálogos con >70% precisión
- [ ] Clasificación de tono funciona para casos claros
- [ ] Checker detecta inconsistencias tono-relación
- [ ] Alertas incluyen contexto suficiente para revisión
- [ ] Sistema permite marcar interacciones como "intencionalmente inconsistentes"

---

## Notas de Implementación

- Empezar con detección de diálogos (más estructurado)
- La clasificación de tono inicial puede ser basada en reglas/lexicones
- Cuando STEP 8.1 esté listo, migrar a análisis de sentimiento
- Las acciones físicas requieren extracción de verbos + objetos

---

## Referencias

- [Entity Relationships](./step-9.1-entity-relationships.md)
- [Sentiment Analysis](../phase-8/step-8.1-sentiment-analysis.md)
- [Dialogue Detection](../phase-5/step-5.1-ner-pipeline.md)
