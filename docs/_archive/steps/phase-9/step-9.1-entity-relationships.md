# STEP 9.1: Relaciones entre Entidades

> **Fase**: 9 - Grafo de Relaciones (Post-MVP)
> **Complejidad**: L (6-8 horas)
> **Prioridad**: P2
> **Dependencias**: STEP 4.1 (Entity Repository), STEP 5.1 (NER Pipeline)

---

## Descripción

Sistema para detectar, almacenar y analizar relaciones entre **cualquier tipo de entidad narrativa** (no solo personas). Permite modelar:
- Relaciones interpersonales (amistad, enemistad, familia)
- Relaciones persona-lugar (vive en, teme, frecuenta)
- Relaciones persona-objeto (posee, desea, teme)
- Relaciones objeto-lugar (está en, pertenece a)
- Relaciones con organizaciones (miembro de, perseguido por)

También detecta **reacciones esperadas** y alerta cuando un personaje actúa de forma inconsistente con la relación establecida.

---

## Objetivos

1. Definir tipos de relaciones para **todas las combinaciones de entidades**
2. Detectar relaciones a partir de co-ocurrencias y contexto
3. Almacenar relaciones con metadatos (inicio, fin, intensidad, valencia emocional)
4. Definir **reacciones esperadas** según tipo de relación
5. Generar alertas por inconsistencias relacionales y reacciones anómalas

---

## Combinaciones de Entidades

| Source | Target | Ejemplos de relación |
|--------|--------|----------------------|
| PERSON | PERSON | amigo, enemigo, padre, rival, amante |
| PERSON | PLACE | vive_en, trabaja_en, teme, ama, evita, nació_en |
| PERSON | OBJECT | posee, desea, teme, usa, creó, destruyó |
| PERSON | ORGANIZATION | miembro_de, fundador_de, enemigo_de, trabaja_para |
| OBJECT | PLACE | está_en, pertenece_a, fue_creado_en |
| OBJECT | PERSON | pertenece_a, fue_regalo_de, está_maldito_por |
| ORGANIZATION | PERSON | emplea_a, persigue_a, protege_a |
| ORGANIZATION | PLACE | tiene_sede_en, controla, opera_en |
| PLACE | PLACE | cerca_de, parte_de, conectado_con |

---

## Filosofía: Extracción Automática + Enriquecimiento IA

El sistema es **100% automático**. El usuario (editor/revisor) **NO crea nada**, solo:
- Revisa lo que el sistema detecta
- Confirma o rechaza sugerencias
- Marca falsos positivos para mejorar el sistema

### Flujo Automático

```
1. EXTRACCIÓN (NLP + Patrones)
   Sistema lee el texto → detecta relaciones explícitas
   "María, madre de Juan" → RelationType: PARENT

2. INFERENCIA (IA)
   Sistema pregunta a LLM: "¿Qué implica esta relación?"
   → Expectativas de comportamiento inferidas automáticamente

3. VERIFICACIÓN (Reglas)
   Sistema escanea el texto buscando inconsistencias
   → Genera alertas automáticas

4. REVISIÓN (Humano)
   Editor revisa alertas → confirma/rechaza
   → Feedback mejora futuras inferencias
```

### Extracción Automática de Relaciones

El sistema detecta relaciones de múltiples fuentes:

| Fuente | Ejemplo | Relación extraída |
|--------|---------|-------------------|
| Patrón explícito | "María, madre de Juan" | María → Juan [PARENT] |
| Verbo + objeto | "Pedro odiaba el cementerio" | Pedro → cementerio [FEARS/HATES] |
| Diálogo | "—Te quiero —susurró Ana a Luis" | Ana → Luis [LOVES] |
| Descripción | "La espada maldita de Dorian" | espada → Dorian [BELONGS_TO + CURSED] |
| Co-ocurrencia + contexto | Pedro y cementerio siempre en escenas de tensión | Pedro → cementerio [NEGATIVE_ASSOCIATION] |
| Inferencia IA | Contexto sugiere miedo | Sistema confirma: Pedro FEARS cementerio |

### Enriquecimiento con IA

Una vez detectada una relación, el sistema consulta a IA para inferir expectativas:

```
Contexto conocido sobre Pedro:
- Tiene fobia a los lugares oscuros desde niño
- Es supersticioso
- Evita hablar de la muerte

Contexto conocido sobre el cementerio:
- Lugar donde murió su padre
- Descrito como "lúgubre y abandonado"

Relación detectada: Pedro → cementerio [negativa/miedo]

Pregunta al modelo:
"Dado lo que sabemos de Pedro y el cementerio, ¿qué comportamientos
serían ESPERABLES cuando Pedro se encuentra con/cerca del cementerio?
¿Qué comportamientos serían INESPERADOS o CONTRADICTORIOS?"
```

### Estado del Arte (2024-2025)

La inferencia de expectativas se basa en avances recientes en:

1. **ATOMIC 2020** ([Hwang et al., AAAI 2021](https://cdn.aaai.org/ojs/16792/16792-13-20286-1-2-20210518.pdf)): Knowledge graph con 1.33M tuplas de conocimiento inferencial sobre entidades y eventos. Define 23 tipos de relaciones de sentido común:
   - `xIntent`: intención de PersonX
   - `xReact`: reacción emocional de PersonX
   - `oEffect`: efecto en otros
   - `xWant`: qué querrá hacer PersonX después

2. **COMET** ([Bosselut et al.](https://github.com/allenai/comet-atomic-2020/)): Modelo generativo entrenado en ATOMIC que infiere conocimiento de sentido común para eventos no vistos.

3. **Narrative Coherence con LLMs** ([MLD-EA, 2024](https://arxiv.org/html/2412.02897v1)): Verificación de coherencia narrativa introduciendo emociones y acciones.

4. **Character Intentionality** ([Wang et al., 2024](https://arxiv.org/html/2506.10161v1)): STORYVERSE traduce puntos de trama en acciones de personajes respetando intencionalidad.

### Ventajas del Enfoque con IA

| Enfoque Manual | Enfoque con IA |
|----------------|----------------|
| Usuario define todo | Sistema sugiere, usuario confirma/rechaza |
| Costoso en tiempo | Automático con validación humana |
| Puede olvidar casos | Infiere basándose en todo el contexto |
| Reglas rígidas | Inferencia contextual flexible |

---

## Modelo de Datos

```python
@dataclass
class RelationshipType:
    """
    Tipo de relación EXTRAÍDO AUTOMÁTICAMENTE del texto.
    El sistema detecta y clasifica; el usuario solo revisa.
    """
    id: str                         # UUID
    project_id: int
    name: str                       # "fears", "loves", "owns", "cursed_by", etc.
    description: str                # Descripción generada automáticamente

    # Clasificación (inferida automáticamente)
    source_entity_types: list[str]  # ["PERSON"], ["OBJECT"], etc.
    target_entity_types: list[str]  # ["PLACE"], ["PERSON"], etc.

    # Valencia emocional (detectada del léxico)
    default_valence: str            # "positive", "negative", "neutral", "fear", "desire"
    is_bidirectional: bool          # Inferido del contexto
    inverse_type_id: Optional[str]  # Auto-generado si aplica

    # Expectativas (INFERIDAS POR IA, no definidas por usuario)
    expected_behaviors: list[str]   # Generados por LLM
    forbidden_behaviors: list[str]  # Generados por LLM
    expected_consequences: list[str] # Generados por LLM
    inference_reasoning: str        # Explicación del LLM

    # Metadatos
    created_at: datetime
    extraction_source: str          # "pattern", "dependency", "cooccurrence", "llm_inference"
    confidence: float               # 0.0 - 1.0
    user_confirmed: bool            # True si el editor lo validó
    user_rejected: bool             # True si el editor lo rechazó


@dataclass
class EntityRelationship:
    """Relación entre dos entidades."""
    id: str
    project_id: int
    source_entity_id: str       # Entidad origen
    target_entity_id: str       # Entidad destino
    relation_type: RelationType

    # Metadatos
    bidirectional: bool = True  # ¿La relación es mutua?
    intensity: float = 0.5      # 0.0 (débil) a 1.0 (fuerte)
    sentiment: float = 0.0      # -1.0 (negativo) a 1.0 (positivo)

    # Temporalidad
    first_mention_chapter: Optional[int] = None
    last_mention_chapter: Optional[int] = None
    is_active: bool = True      # ¿Sigue vigente al final?

    # Evidencia
    evidence_mentions: list[str] = field(default_factory=list)
    confidence: float = 0.5     # Confianza en la detección

    # Auditoría
    created_at: datetime = field(default_factory=datetime.now)
    user_confirmed: bool = False  # Confirmada manualmente


@dataclass
class RelationshipChange:
    """Cambio en una relación a lo largo de la narrativa."""
    relationship_id: str
    chapter: int
    old_type: Optional[RelationType]
    new_type: RelationType
    trigger_text: str           # Texto que evidencia el cambio
    notes: str = ""
```

---

## Componentes

### 1. RelationshipRepository

```python
class RelationshipRepository:
    """Persistencia de relaciones."""

    def create_relationship(self, rel: EntityRelationship) -> str: ...
    def get_relationships_for_entity(self, entity_id: str) -> list[EntityRelationship]: ...
    def get_relationship_between(self, entity1_id: str, entity2_id: str) -> Optional[EntityRelationship]: ...
    def update_relationship(self, rel: EntityRelationship) -> bool: ...
    def get_relationship_graph(self, project_id: int) -> dict[str, list[EntityRelationship]]: ...
```

### 2. RelationshipDetector

```python
class RelationshipDetector:
    """Detecta relaciones a partir del texto."""

    # Patrones para detección
    FAMILY_PATTERNS = [
        r"(?P<source>\w+),?\s+(padre|madre|hijo|hija|hermano|hermana)\s+de\s+(?P<target>\w+)",
        r"(?P<source>\w+)\s+y\s+su\s+(padre|madre|hijo|hermano)",
    ]

    SOCIAL_PATTERNS = [
        r"(?P<source>\w+),?\s+(amigo|enemigo|rival)\s+de\s+(?P<target>\w+)",
        r"(?P<source>\w+)\s+odiaba\s+a\s+(?P<target>\w+)",
        r"(?P<source>\w+)\s+y\s+(?P<target>\w+)\s+eran\s+(amigos|enemigos)",
    ]

    def detect_from_text(self, text: str, entities: list[Entity]) -> list[EntityRelationship]: ...
    def detect_from_cooccurrence(self, mentions: list[EntityMention]) -> list[EntityRelationship]: ...
    def infer_from_dialogue(self, dialogue: str, speaker: Entity, listener: Entity) -> Optional[RelationType]: ...
```

### 3. ExpectationInferenceEngine

```python
class ExpectationInferenceEngine:
    """
    Motor de inferencia de expectativas usando IA.

    Puede usar:
    - LLM local (Ollama, llama.cpp) para offline
    - API externa (OpenAI, Anthropic) si el usuario lo permite
    - COMET/ATOMIC como fallback sin conexión
    """

    def infer_expectations(
        self,
        source_entity: Entity,
        target_entity: Entity,
        relationship_type: RelationshipType,
        context: EntityContext
    ) -> InferredExpectations:
        """
        Infiere comportamientos esperados/prohibidos y consecuencias.

        Args:
            source_entity: Entidad origen (ej: Pedro)
            target_entity: Entidad destino (ej: cementerio)
            relationship_type: Tipo de relación (ej: "teme")
            context: Contexto conocido de ambas entidades

        Returns:
            InferredExpectations con:
            - expected_behaviors: ["evita", "palidece", "tiembla"]
            - forbidden_behaviors: ["entra tranquilamente"]
            - expected_consequences: []
            - confidence: 0.85
            - reasoning: "Explicación del modelo"
        """
        prompt = self._build_prompt(source_entity, target_entity, relationship_type, context)

        if self.use_local_llm:
            response = self._query_local_llm(prompt)
        elif self.use_comet:
            response = self._query_comet(source_entity, target_entity, relationship_type)
        else:
            response = self._query_api(prompt)

        return self._parse_response(response)

    def _build_prompt(self, source, target, rel_type, context) -> str:
        """Construye prompt para inferencia."""
        return f"""
Contexto conocido sobre {source.canonical_name}:
{self._format_entity_context(source, context)}

Contexto conocido sobre {target.canonical_name}:
{self._format_entity_context(target, context)}

Relación: {source.canonical_name} [{rel_type.name}] {target.canonical_name}

Basándote en el contexto narrativo, responde:
1. ¿Qué comportamientos serían ESPERABLES de {source.canonical_name}
   cuando se encuentra con/cerca de {target.canonical_name}?
2. ¿Qué comportamientos serían CONTRADICTORIOS con esta relación?
3. ¿Debería haber consecuencias específicas de esta interacción?

Responde en JSON:
{{
  "expected_behaviors": ["...", "..."],
  "forbidden_behaviors": ["...", "..."],
  "expected_consequences": ["...", "..."],
  "reasoning": "..."
}}
"""


@dataclass
class InferredExpectations:
    """Expectativas inferidas por IA."""
    expected_behaviors: list[str]
    forbidden_behaviors: list[str]
    expected_consequences: list[str]
    confidence: float
    reasoning: str
    inference_source: str  # "local_llm", "api", "comet", "user_defined"


@dataclass
class EntityContext:
    """Contexto conocido de una entidad para inferencia."""
    entity_id: str
    attributes: list[EntityAttribute]
    relationships: list[EntityRelationship]
    mentions_summary: str  # Resumen de menciones relevantes
    personality_traits: list[str]  # Inferidos de atributos
    backstory_facts: list[str]  # Hechos del pasado conocidos
```

### 4. RelationshipAnalyzer

```python
class RelationshipAnalyzer:
    """Analiza coherencia y evolución de relaciones."""

    def __init__(self, inference_engine: Optional[ExpectationInferenceEngine] = None):
        self.inference_engine = inference_engine

    def check_consistency(
        self,
        relationship: EntityRelationship,
        scene_text: str
    ) -> list[Alert]:
        """
        Detecta inconsistencias entre relación y comportamiento en escena.

        Si no hay expectativas definidas y hay inference_engine disponible,
        las infiere automáticamente.
        """
        expectations = relationship.type.get_expectations()

        # Si no hay expectativas definidas, inferir con IA
        if not expectations and self.inference_engine:
            expectations = self.inference_engine.infer_expectations(
                relationship.source_entity,
                relationship.target_entity,
                relationship.type,
                self._build_context(relationship)
            )
            # Guardar para no re-inferir
            relationship.type.set_inferred_expectations(expectations)

        return self._check_against_expectations(scene_text, expectations)

    def track_evolution(self, relationship: EntityRelationship) -> list[RelationshipChange]:
        """Rastrea cómo evoluciona una relación."""
        ...

    def generate_relationship_map(self, project_id: int) -> RelationshipGraph:
        """Genera grafo de relaciones para visualización."""
        ...
```

---

## Sistema de Verificación Automática

Todo es automático. El sistema extrae, infiere, verifica y alerta. El editor solo revisa.

### Pipeline Completo

```
TEXTO NARRATIVO
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. EXTRACCIÓN DE RELACIONES                                 │
│    - Patrones lingüísticos: "X, madre de Y"                 │
│    - Análisis de dependencias: "X odiaba Y"                 │
│    - Detección de posesivos: "la espada de X"               │
│    - Co-ocurrencias significativas                          │
└─────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CLASIFICACIÓN AUTOMÁTICA                                 │
│    - Tipo de relación (familiar, emocional, posesión...)    │
│    - Valencia (positiva, negativa, neutral, miedo...)       │
│    - Intensidad (basada en léxico usado)                    │
└─────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. INFERENCIA DE EXPECTATIVAS (IA)                          │
│    Prompt: "Dado que Pedro teme el cementerio porque        │
│    su padre murió allí, ¿qué comportamientos esperarías?"   │
│                                                             │
│    → expected: ["evita", "palidece", "tiembla"]             │
│    → forbidden: ["entra tranquilo", "silba"]                │
│    → consequences: []                                        │
└─────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ESCANEO Y VERIFICACIÓN                                   │
│    Para cada escena donde co-ocurren las entidades:         │
│    - ¿Hay comportamiento prohibido? → ALERTA                │
│    - ¿Falta comportamiento esperado? → ALERTA               │
│    - ¿Falta consecuencia esperada? → ALERTA                 │
└─────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. REVISIÓN HUMANA                                          │
│    Editor ve alertas → Confirma / Rechaza / Ignora          │
│    Feedback se usa para mejorar futuras inferencias         │
└─────────────────────────────────────────────────────────────┘
```

### Ejemplos de Extracción Automática

**Texto**: *"Pedro nunca se acercaba al viejo cementerio. Desde que su padre murió allí, el simple pensamiento del lugar le provocaba escalofríos."*

**Extracción automática**:
```python
# Detectado por patrones y análisis semántico
EntityRelationship(
    source="Pedro",
    target="cementerio",
    relation_type="FEARS",           # Inferido de "escalofríos", "nunca se acercaba"
    valence="negative",
    intensity=0.8,                   # Alta por "nunca", "escalofríos"
    evidence=["nunca se acercaba", "le provocaba escalofríos"],
    backstory="su padre murió allí"  # Contexto extraído
)
```

**Inferencia IA automática**:
```python
# Sistema pregunta a LLM con el contexto
InferredExpectations(
    expected_behaviors=["evita el lugar", "rodea", "palidece si se menciona"],
    forbidden_behaviors=["entra voluntariamente", "pasea tranquilo", "duerme allí"],
    expected_consequences=[],
    reasoning="El trauma por la muerte del padre genera aversión fuerte al lugar"
)
```

**Verificación automática**:
```
Cap 15: "Pedro cruzó el cementerio silbando una melodía alegre."

→ ALERTA AUTOMÁTICA:
  Código: COHERENCE_FORBIDDEN_BEHAVIOR
  Mensaje: "Pedro realiza comportamiento prohibido respecto a 'cementerio'"
  Detalles:
    - Relación: Pedro FEARS cementerio (establecida cap 3)
    - Comportamiento detectado: "cruzó silbando" (positivo/relajado)
    - Comportamiento esperado: evitación, tensión
  Sugerencia: "Verificar si hay escena de superación del trauma entre caps 3-15"
```

### Detección de Anomalías Automática

| Relación extraída | Comportamiento detectado | Anomalía | Alerta |
|-------------------|--------------------------|----------|--------|
| Pedro FEARS cementerio | "entró silbando" | Comportamiento contradice miedo | `COHERENCE_FORBIDDEN` |
| Ana ENEMY Luis | "lo abrazó con cariño" | Interacción positiva entre enemigos | `COHERENCE_VALENCE_MISMATCH` |
| Espada CURSED | Juan la usa, nada malo pasa | Falta consecuencia de maldición | `COHERENCE_MISSING_CONSEQUENCE` |
| Gato "da mala suerte" | Protagonista lo acaricia sin efecto | Superstición ignorada | `COHERENCE_WORLD_RULE_VIOLATED` |

---

## Alertas Generadas

### Filosofía: Sistema 100% Extensible

Las alertas son **completamente dinámicas**. No existe una lista cerrada de tipos:

1. **La IA detecta cualquier inconsistencia** en relaciones y comportamientos
2. **Genera códigos y descripciones sobre la marcha** según el problema encontrado
3. **Aprende de feedback** del editor para mejorar futuras detecciones

```python
class DynamicAlertGenerator:
    """
    Genera alertas dinámicamente según lo que detecte la IA.
    NO está limitado a tipos predefinidos.
    """

    def generate_alert(
        self,
        issue: str,
        entities: list[Entity],
        context: NarrativeContext
    ) -> CoherenceAlert:
        """
        La IA analiza el problema y genera:
        - code: Código único (ej: "REL_AI_BETRAYAL_UNMOTIVATED")
        - alert_type: Descripción legible (ej: "Traición sin motivación")
        - severity: Calculada según impacto narrativo
        - suggestion: Generada contextualmente
        """
        return self.inference_engine.classify_coherence_issue(
            issue=issue,
            entities=entities,
            context=context
        )
```

### Ejemplos Base (No Exhaustivos)

#### Alertas de Relación

| Código | Tipo (visible al editor) | Descripción | Severidad |
|--------|--------------------------|-------------|-----------|
| `REL_CONTRADICTORY` | Relación contradictoria | Relación contradice otra existente | Warning |
| `REL_UNEXPLAINED_CHANGE` | Cambio de relación sin justificar | Cambio de relación sin justificación textual | Info |
| `REL_CIRCULAR` | Relación circular imposible | Relación crea ciclo imposible (A padre de B padre de A) | Error |
| `REL_WITH_INACTIVE` | Interacción con entidad inactiva | Interacción con entidad marcada como inactiva/muerta | Warning |
| *...IA genera más...* | *Según contexto* | *Detectado dinámicamente* | *Variable* |

#### Alertas de Coherencia

| Código | Tipo (visible al editor) | Descripción | Severidad |
|--------|--------------------------|-------------|-----------|
| `COHERENCE_FORBIDDEN_BEHAVIOR` | Comportamiento contradictorio | Comportamiento en lista de prohibidos | Warning |
| `COHERENCE_MISSING_EXPECTED` | Reacción esperada ausente | Falta comportamiento esperado en encuentro | Info |
| `COHERENCE_MISSING_CONSEQUENCE` | Consecuencia no cumplida | Consecuencia esperada no ocurre | Info |
| `COHERENCE_VALENCE_MISMATCH` | Tono emocional inconsistente | Tono de interacción contradice valencia definida | Info |
| *...IA genera más...* | *Según contexto* | *Detectado dinámicamente* | *Variable* |

### Ejemplos de Alertas Generadas por IA (No Predefinidas)

La IA puede detectar problemas no contemplados en los ejemplos base:

```
🤖 LEALTAD INCONSISTENTE                                              [Warning]
   (Código generado: REL_AI_LOYALTY_INCONSISTENT)

   Juan jura lealtad eterna a María (pág. 45) pero la traiciona
   sin conflicto interno visible (pág. 120).

🤖 CONOCIMIENTO RELACIONAL IMPOSIBLE                                  [Warning]
   (Código generado: REL_AI_IMPOSSIBLE_KNOWLEDGE)

   Ana sabe que Pedro y Luis son hermanos, pero nunca estuvo presente
   cuando se reveló esta información.

🤖 REACCIÓN EMOCIONAL AUSENTE                                         [Info]
   (Código generado: REL_AI_MISSING_EMOTIONAL_REACTION)

   Carlos se entera de la muerte de su mejor amigo pero no muestra
   ninguna reacción emocional en las siguientes 3 escenas.

🤖 PROXIMIDAD FÍSICA IMPOSIBLE                                        [Error]
   (Código generado: REL_AI_IMPOSSIBLE_PROXIMITY)

   María y Pedro interactúan en Madrid (cap 15) cuando Pedro
   estaba establecido en Barcelona desde el cap 12 sin viaje mencionado.

🤖 OLVIDO DE INFORMACIÓN IMPORTANTE                                   [Warning]
   (Código generado: REL_AI_FORGOTTEN_INFORMATION)

   El protagonista "descubre" que el villano es su tío (pág. 200)
   aunque ya se lo habían dicho en la pág. 50.
```

### Formato de Alerta (Preciso y Contextual)

Las alertas siempre muestran **citas exactas** con ubicaciones precisas, e incluyen un **tipo de alerta** legible para el editor:

```python
@dataclass
class CoherenceAlert:
    """Alerta de inconsistencia con referencias precisas."""
    code: str                        # Código técnico: "COHERENCE_FORBIDDEN_BEHAVIOR"
    alert_type: str                  # Tipo legible: "Comportamiento contradictorio"
    severity: str                    # "error", "warning", "info"

    # Entidades involucradas
    source_entity: str
    target_entity: str
    relationship_type: str

    # REFERENCIA 1: Donde se establece la relación/expectativa
    establishing_reference: TextReference
    establishing_quote: str          # Cita exacta del texto

    # REFERENCIA 2: Donde se contradice
    contradicting_reference: TextReference
    contradicting_quote: str         # Cita exacta del texto

    # Explicación
    explanation: str
    suggestion: str


# ALERT_TYPES es un diccionario DINÁMICO
# Comienza con ejemplos base pero la IA añade nuevos tipos continuamente

class DynamicAlertTypes:
    """
    Registro dinámico de tipos de alerta.
    La IA registra nuevos tipos cuando detecta problemas no catalogados.
    """

    # Ejemplos base (punto de partida, NO lista cerrada)
    _base_types = {
        "COHERENCE_FORBIDDEN_BEHAVIOR": "Comportamiento contradictorio",
        "COHERENCE_MISSING_EXPECTED": "Reacción esperada ausente",
        "COHERENCE_MISSING_CONSEQUENCE": "Consecuencia no cumplida",
        "COHERENCE_VALENCE_MISMATCH": "Tono emocional inconsistente",
        "REL_CONTRADICTORY": "Relación contradictoria",
        "REL_UNEXPLAINED_CHANGE": "Cambio de relación sin justificar",
        "REL_CIRCULAR": "Relación circular imposible",
        "REL_WITH_INACTIVE": "Interacción con entidad inactiva",
    }

    # Tipos generados dinámicamente por IA (se persisten en BD)
    _ai_generated_types: dict[str, str] = {}

    def register_new_type(self, code: str, description: str) -> None:
        """La IA registra un nuevo tipo de alerta detectado."""
        self._ai_generated_types[code] = description

    def get_type(self, code: str) -> str:
        """Obtiene descripción legible para un código."""
        return (
            self._base_types.get(code) or
            self._ai_generated_types.get(code) or
            code  # Si no existe, usa el código como descripción
        )


@dataclass
class TextReference:
    """Referencia precisa a ubicación en el texto."""
    chapter: int
    chapter_title: Optional[str]
    page: Optional[int]              # Si está disponible
    paragraph: int
    sentence: int
    char_start: int
    char_end: int


# Ejemplo de alerta generada:
Alert(
    code="COHERENCE_FORBIDDEN_BEHAVIOR",
    alert_type="Comportamiento contradictorio",  # Tipo legible para el editor
    severity="warning",
    source_entity="Pedro",
    target_entity="cementerio",
    relationship_type="FEARS",

    establishing_reference=TextReference(
        chapter=3,
        chapter_title="Los recuerdos",
        page=47,
        paragraph=12,
        sentence=2,
        char_start=15234,
        char_end=15412
    ),
    establishing_quote="Pedro nunca se acercaba al viejo cementerio. Desde que su padre murió allí, el simple pensamiento del lugar le provocaba escalofríos.",

    contradicting_reference=TextReference(
        chapter=15,
        chapter_title="El regreso",
        page=203,
        paragraph=5,
        sentence=1,
        char_start=89234,
        char_end=89298
    ),
    contradicting_quote="Pedro cruzó el cementerio silbando una melodía alegre.",

    explanation="En la página 47 (cap. 3) se establece que Pedro teme el cementerio debido al trauma por la muerte de su padre. Sin embargo, en la página 203 (cap. 15) Pedro cruza el cementerio 'silbando una melodía alegre', lo cual contradice el miedo establecido.",

    suggestion="Verificar si existe una escena de superación del trauma entre los capítulos 3 y 15 que justifique este cambio de comportamiento."
)
```

### Visualización para el Editor

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ⚠️  COMPORTAMIENTO CONTRADICTORIO                               [Warning]     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Pedro → cementerio [FEARS]                                                  ║
║                                                                              ║
║  📍 ESTABLECIDO en página 47 (Cap. 3 "Los recuerdos", párrafo 12):          ║
║  ┌────────────────────────────────────────────────────────────────────────┐  ║
║  │ "Pedro nunca se acercaba al viejo cementerio. Desde que su padre      │  ║
║  │  murió allí, el simple pensamiento del lugar le provocaba             │  ║
║  │  escalofríos."                                                        │  ║
║  └────────────────────────────────────────────────────────────────────────┘  ║
║                                                                              ║
║  ❌ CONTRADICE en página 203 (Cap. 15 "El regreso", párrafo 5):             ║
║  ┌────────────────────────────────────────────────────────────────────────┐  ║
║  │ "Pedro cruzó el cementerio silbando una melodía alegre."              │  ║
║  └────────────────────────────────────────────────────────────────────────┘  ║
║                                                                              ║
║  💡 Sugerencia: Verificar si existe una escena de superación del trauma     ║
║     entre los capítulos 3 y 15.                                             ║
║                                                                              ║
║  [✓ Confirmar problema]  [✗ Ignorar]  [📝 Añadir nota]  [🔗 Ver contexto]   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Más Ejemplos de Alertas Precisas

**Ejemplo 1: Enemigos que se abrazan**
```
⚠️ TONO EMOCIONAL INCONSISTENTE                                    [Warning]

Ana → Luis [ENEMY]

📍 Página 23 (Cap. 2): "Ana odiaba a Luis con toda su alma. Jamás
   le perdonaría lo que le hizo a su familia."

❌ Página 156 (Cap. 12): "Ana abrazó a Luis con cariño, como si nada
   hubiera pasado entre ellos."

💡 Sugerencia: Buscar escena de reconciliación entre caps 2-12.
```

**Ejemplo 2: Objeto maldito sin consecuencias**
```
⚠️ CONSECUENCIA NO CUMPLIDA                                        [Warning]

Espada de Morvan → Juan [CURSED_BY]

📍 Página 89 (Cap. 7): "La espada de Morvan estaba maldita. Todo aquel
   que la empuñara sufriría terribles pesadillas."

❌ Página 234 (Cap. 18): "Juan usó la espada de Morvan durante toda la
   batalla." [No se mencionan pesadillas en caps 18-20]

💡 Sugerencia: Añadir consecuencias de la maldición o justificar
   por qué Juan es inmune.
```

**Ejemplo 3: Superstición ignorada**
```
⚠️ CONSECUENCIA NO CUMPLIDA                                        [Info]

Gato negro → Pueblo [BRINGS_BAD_LUCK]

📍 Página 12 (Cap. 1): "En el pueblo todos sabían que cruzarse con un
   gato negro traía desgracia. Nadie se atrevía a acercarse a ellos."

❌ Página 178 (Cap. 14): "María acarició al gato negro que dormía en
   el porche." [No hay consecuencia negativa posterior]

💡 Sugerencia: El mundo narrativo establece esta superstición como
   "real". Considerar añadir consecuencia o mostrar que María no
   es supersticiosa.
```

---

## Schema de Base de Datos

```sql
-- Tipos de relación definidos por el usuario (genérico)
CREATE TABLE relationship_types (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,                    -- "enemigo", "teme", "maldito_por"
    description TEXT,
    source_entity_types TEXT NOT NULL,     -- JSON: ["PERSON"] o ["*"]
    target_entity_types TEXT NOT NULL,     -- JSON: ["PLACE", "OBJECT"]
    default_valence TEXT DEFAULT 'neutral', -- positive/negative/neutral/fear/desire
    is_bidirectional INTEGER DEFAULT 0,
    inverse_type_id TEXT,                  -- FK a otro relationship_type
    expected_behaviors TEXT,               -- JSON: ["evita", "huye"]
    forbidden_behaviors TEXT,              -- JSON: ["abraza", "ayuda"]
    expected_consequences TEXT,            -- JSON: ["sufre daño"]
    is_system_suggested INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (inverse_type_id) REFERENCES relationship_types(id),
    UNIQUE(project_id, name)
);

-- Instancias de relaciones entre entidades específicas
CREATE TABLE entity_relationships (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    relationship_type_id TEXT NOT NULL,    -- FK al tipo definido por usuario
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,

    -- Metadatos de la instancia
    intensity REAL DEFAULT 0.5,            -- 0.0 a 1.0
    notes TEXT,                            -- Notas del usuario

    -- Temporalidad
    first_mention_chapter INTEGER,
    last_mention_chapter INTEGER,
    is_active INTEGER DEFAULT 1,           -- ¿Sigue vigente?

    -- Confianza
    confidence REAL DEFAULT 0.5,
    user_confirmed INTEGER DEFAULT 0,

    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (relationship_type_id) REFERENCES relationship_types(id),
    FOREIGN KEY (source_entity_id) REFERENCES entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES entities(id),
    UNIQUE(project_id, relationship_type_id, source_entity_id, target_entity_id)
);

-- Evidencia textual de cada relación
CREATE TABLE relationship_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id TEXT NOT NULL,
    mention_id TEXT,                       -- Opcional: mención específica
    context_text TEXT NOT NULL,            -- Texto que evidencia la relación
    chapter INTEGER,
    behavior_type TEXT,                    -- "expected", "forbidden", "consequence", "other"
    created_at TEXT NOT NULL,
    FOREIGN KEY (relationship_id) REFERENCES entity_relationships(id),
    FOREIGN KEY (mention_id) REFERENCES entity_mentions(id)
);

-- Cambios/evolución de relaciones
CREATE TABLE relationship_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    change_type TEXT NOT NULL,             -- "created", "intensified", "weakened", "ended", "transformed"
    old_type_id TEXT,                      -- Si cambió de tipo
    new_type_id TEXT,
    trigger_text TEXT,                     -- Texto que provocó el cambio
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (relationship_id) REFERENCES entity_relationships(id),
    FOREIGN KEY (old_type_id) REFERENCES relationship_types(id),
    FOREIGN KEY (new_type_id) REFERENCES relationship_types(id)
);
```

---

## Casos de Uso

### Ejemplo 1: Detección de relación familiar
```
Texto: "María, la madre de Juan, entró en la habitación."

Resultado:
- source: María
- target: Juan
- relation_type: PARENT
- bidirectional: False (Juan es CHILD de María)
```

### Ejemplo 2: Evolución de relación
```
Cap 1: "Pedro y Luis eran los mejores amigos desde la infancia."
Cap 5: "Pedro nunca perdonaría la traición de Luis."

Evolución detectada:
- Cap 1: FRIEND (intensity: 0.9)
- Cap 5: ENEMY (intensity: 0.7)
- Alerta: REL_UNEXPLAINED_CHANGE (si no hay escena de traición entre caps 1-5)
```

---

## Criterios de Aceptación

- [ ] Modelo de relaciones soporta todos los tipos definidos
- [ ] Detector identifica relaciones explícitas con >80% precisión
- [ ] Sistema almacena evidencia textual de cada relación
- [ ] Alertas detectan contradicciones básicas
- [ ] Exportación de grafo de relaciones funcional

---

## Notas de Implementación

- Las relaciones inferidas por co-ocurrencia tienen `confidence` bajo (0.3)
- El usuario puede confirmar/rechazar relaciones detectadas
- Las relaciones familiares son más fáciles de detectar que las emocionales
- Considerar integración con STEP 8.1 (sentimiento) para inferir tipo de relación

---

## Referencias

- [Entity Models](../../../src/narrative_assistant/entities/models.py)
- [Co-occurrence Analysis](../phase-5/step-5.2-cooccurrence.md)
- [Alert Engine](../phase-7/step-7.1-alert-engine.md)
