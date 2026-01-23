# STEP 10.1: Relevancia de Personajes

> **Fase**: 10 - Análisis Narrativo Avanzado (Post-MVP)
> **Complejidad**: L (6-8 horas)
> **Prioridad**: P3
> **Dependencias**: STEP 4.1 (Entity Repository), STEP 9.1 (Relationships)

---

## Descripción

Sistema para evaluar la relevancia narrativa de cada personaje. Detecta personajes que no aportan a la trama, aquellos que aparecen mucho pero no influyen, y personajes "planos" o "insulsos" que podrían necesitar desarrollo.

---

## Objetivos

1. Calcular métricas de relevancia para cada personaje
2. Detectar personajes sin contribución narrativa
3. Identificar personajes "planos" (sin arco ni desarrollo)
4. Generar sugerencias de mejora o eliminación

---

## Métricas de Relevancia

### 1. Presencia Cuantitativa

```python
@dataclass
class PresenceMetrics:
    """Métricas de presencia del personaje."""
    total_mentions: int              # Menciones totales
    chapters_present: int            # Capítulos donde aparece
    scenes_present: int              # Escenas donde aparece
    dialogue_count: int              # Líneas de diálogo
    action_count: int                # Acciones realizadas

    # Distribución
    first_appearance: int            # Primer capítulo
    last_appearance: int             # Último capítulo
    presence_gaps: list[tuple[int, int]]  # Huecos sin aparecer

    # Comparativas
    mention_rank: int                # Posición en ranking de menciones
    mention_percentile: float        # Percentil (0-100)
```

### 2. Influencia Narrativa

```python
@dataclass
class InfluenceMetrics:
    """Métricas de influencia en la trama."""

    # Conexiones
    unique_interactions: int         # Con cuántos personajes interactúa
    relationship_count: int          # Relaciones establecidas
    central_to_relationships: int    # Relaciones donde es central

    # Impacto
    plot_events_involved: int        # Eventos de trama donde participa
    decisions_made: int              # Decisiones que toma
    consequences_caused: int         # Consecuencias de sus acciones

    # Posición en red
    network_centrality: float        # Centralidad en grafo de personajes
    bridge_score: float              # Conecta grupos separados
```

### 3. Desarrollo del Personaje

```python
@dataclass
class DevelopmentMetrics:
    """Métricas de desarrollo/arco del personaje."""

    # Atributos
    attributes_defined: int          # Atributos físicos/psicológicos
    attributes_changed: int          # Atributos que cambian

    # Arco narrativo
    has_goal: bool                   # Tiene objetivo identificable
    has_conflict: bool               # Enfrenta conflicto
    has_change: bool                 # Cambia durante la historia
    arc_completeness: float          # 0-1, qué tan completo es su arco

    # Profundidad
    internal_monologue_count: int    # Pensamientos mostrados
    backstory_mentions: int          # Referencias a su pasado
    motivation_clarity: float        # Claridad de motivaciones (0-1)
```

---

## Modelo de Evaluación

```python
@dataclass
class CharacterRelevanceScore:
    """Puntuación de relevancia de un personaje."""
    entity_id: str
    entity_name: str

    # Métricas individuales
    presence: PresenceMetrics
    influence: InfluenceMetrics
    development: DevelopmentMetrics

    # Scores calculados (0-100)
    presence_score: float
    influence_score: float
    development_score: float
    overall_score: float

    # Clasificación
    character_type: CharacterType    # PROTAGONIST, SUPPORTING, MINOR, EXTRA
    relevance_verdict: RelevanceVerdict

    # Problemas detectados
    issues: list[CharacterIssue]
    suggestions: list[str]


class CharacterType(Enum):
    PROTAGONIST = "protagonist"      # Personaje principal
    ANTAGONIST = "antagonist"        # Antagonista principal
    SUPPORTING = "supporting"        # Personaje secundario importante
    MINOR = "minor"                  # Personaje menor con función
    EXTRA = "extra"                  # Aparición sin función clara


class RelevanceVerdict(Enum):
    ESSENTIAL = "essential"          # Esencial para la trama
    IMPORTANT = "important"          # Importante, bien desarrollado
    ADEQUATE = "adequate"            # Cumple su función
    UNDERDEVELOPED = "underdeveloped"  # Necesita más desarrollo
    REDUNDANT = "redundant"          # Podría eliminarse/fusionarse
    PROBLEMATIC = "problematic"      # Inconsistente o confuso


@dataclass
class CharacterIssue:
    """Problema detectado en un personaje."""
    code: str
    description: str
    severity: str                    # "info", "warning", "error"
    chapter_refs: list[int]          # Capítulos relevantes
```

---

## Componentes

### 1. RelevanceCalculator

```python
class CharacterRelevanceCalculator:
    """Calcula relevancia de personajes."""

    def calculate_presence_score(self, entity: Entity, mentions: list[EntityMention]) -> float:
        """
        Score basado en presencia.
        Considera: frecuencia, distribución, protagonismo en escenas.
        """
        ...

    def calculate_influence_score(
        self,
        entity: Entity,
        relationships: list[EntityRelationship],
        interactions: list[EntityInteraction]
    ) -> float:
        """
        Score basado en influencia.
        Considera: conexiones, centralidad, impacto en otros.
        """
        ...

    def calculate_development_score(
        self,
        entity: Entity,
        attributes: list[EntityAttribute],
        arc_events: list[ArcEvent]
    ) -> float:
        """
        Score basado en desarrollo.
        Considera: profundidad, cambio, arco narrativo.
        """
        ...

    def classify_character(self, scores: CharacterRelevanceScore) -> CharacterType:
        """Clasifica el tipo de personaje según sus scores."""
        if scores.overall_score > 80:
            return CharacterType.PROTAGONIST
        elif scores.overall_score > 60:
            return CharacterType.SUPPORTING
        elif scores.overall_score > 30:
            return CharacterType.MINOR
        else:
            return CharacterType.EXTRA
```

### 2. IssueDetector

```python
class CharacterIssueDetector:
    """Detecta problemas en personajes."""

    ISSUES = {
        "CHAR_NO_PURPOSE": "Personaje sin propósito claro en la trama",
        "CHAR_FLAT": "Personaje plano, sin desarrollo ni cambio",
        "CHAR_INCONSISTENT": "Comportamiento inconsistente sin justificación",
        "CHAR_OVERCROWDED": "Demasiados personajes similares",
        "CHAR_ABANDONED": "Personaje introducido y luego olvidado",
        "CHAR_UNDERUSED": "Alta presencia pero baja influencia",
        "CHAR_DEUS_EX": "Aparece solo para resolver problemas",
        "CHAR_NO_AGENCY": "Nunca toma decisiones propias",
        "CHAR_REDUNDANT": "Función duplicada con otro personaje",
    }

    def detect_flat_character(self, score: CharacterRelevanceScore) -> Optional[CharacterIssue]:
        """Detecta personaje sin desarrollo."""
        if score.development.has_change == False and score.presence_score > 50:
            return CharacterIssue(
                code="CHAR_FLAT",
                description=f"{score.entity_name} aparece frecuentemente pero no muestra desarrollo",
                severity="warning",
                chapter_refs=[]
            )
        return None

    def detect_abandoned_character(self, score: CharacterRelevanceScore) -> Optional[CharacterIssue]:
        """Detecta personaje olvidado."""
        gaps = score.presence.presence_gaps
        if gaps and max(g[1] - g[0] for g in gaps) > 5:  # Gap > 5 capítulos
            return CharacterIssue(
                code="CHAR_ABANDONED",
                description=f"{score.entity_name} desaparece por largos periodos",
                severity="info",
                chapter_refs=[g[0] for g in gaps]
            )
        return None

    def detect_redundant_characters(
        self,
        scores: list[CharacterRelevanceScore]
    ) -> list[CharacterIssue]:
        """Detecta personajes con funciones duplicadas."""
        ...
```

### 3. SuggestionGenerator

```python
class CharacterSuggestionGenerator:
    """Genera sugerencias para mejorar personajes."""

    def generate_suggestions(self, score: CharacterRelevanceScore) -> list[str]:
        suggestions = []

        if score.relevance_verdict == RelevanceVerdict.UNDERDEVELOPED:
            suggestions.append(
                f"Considerar añadir más escenas de desarrollo para {score.entity_name}"
            )

        if score.relevance_verdict == RelevanceVerdict.REDUNDANT:
            suggestions.append(
                f"Evaluar si {score.entity_name} puede fusionarse con otro personaje"
            )

        if "CHAR_NO_AGENCY" in [i.code for i in score.issues]:
            suggestions.append(
                f"Dar a {score.entity_name} oportunidad de tomar decisiones propias"
            )

        return suggestions
```

---

## Alertas Generadas

| Código | Descripción | Severidad |
|--------|-------------|-----------|
| `CHAR_NO_PURPOSE` | Personaje sin propósito narrativo | Warning |
| `CHAR_FLAT` | Personaje sin desarrollo | Info |
| `CHAR_ABANDONED` | Personaje introducido y olvidado | Warning |
| `CHAR_UNDERUSED` | Alta presencia, baja influencia | Info |
| `CHAR_REDUNDANT` | Función duplicada | Info |
| `CHAR_OVERCROWDED` | Demasiados personajes menores | Info |

---

## Ejemplo de Análisis

### Entrada
```
Personaje: "Don Ramiro"
- Menciones: 45 (15% del total)
- Capítulos: aparece en 3 de 20
- Diálogos: 8 líneas
- Relaciones: ninguna establecida
- Atributos: "viejo", "canoso" (solo físicos)
- Acciones: ninguna que afecte la trama
```

### Resultado
```python
score = CharacterRelevanceScore(
    entity_name="Don Ramiro",
    presence_score=35.0,      # Presente pero disperso
    influence_score=5.0,      # Sin influencia
    development_score=10.0,   # Sin desarrollo
    overall_score=16.7,
    character_type=CharacterType.EXTRA,
    relevance_verdict=RelevanceVerdict.REDUNDANT,
    issues=[
        CharacterIssue(
            code="CHAR_NO_PURPOSE",
            description="Don Ramiro no tiene función clara en la trama",
            severity="warning"
        ),
        CharacterIssue(
            code="CHAR_FLAT",
            description="Solo tiene atributos físicos, sin profundidad",
            severity="info"
        )
    ],
    suggestions=[
        "Considerar eliminar a Don Ramiro o darle un rol específico",
        "Si es necesario para ambientación, reducir menciones",
        "Alternativa: fusionar con otro personaje secundario"
    ]
)
```

---

## Criterios de Aceptación

- [ ] Cálculo de métricas de presencia funcional
- [ ] Cálculo de métricas de influencia (requiere grafo de relaciones)
- [ ] Detección de personajes planos/insulsos
- [ ] Detección de personajes abandonados
- [ ] Generación de sugerencias útiles
- [ ] Reporte de relevancia exportable

---

## Notas de Implementación

- Las métricas de desarrollo son las más difíciles de calcular automáticamente
- Empezar con presencia + influencia, añadir desarrollo después
- El usuario debe poder marcar personajes como "intencionalmente menores"
- Considerar el género: en novelas corales, muchos personajes es normal

---

## Referencias

- [Entity Repository](../phase-4/step-4.1-entity-repository.md)
- [Entity Relationships](../phase-9/step-9.1-entity-relationships.md)
- [Interaction Analysis](../phase-9/step-9.2-interaction-analysis.md)
