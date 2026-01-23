# STEP 10.3: Coherencia Estructural

> **Fase**: 10 - Análisis Narrativo Avanzado (Post-MVP)
> **Complejidad**: XL (8-12 horas)
> **Prioridad**: P3
> **Dependencias**: STEP 10.1 (Character Relevance), STEP 10.2 (Chapter Pacing), STEP 6.1 (Timeline)

---

## Descripción

Sistema para analizar la coherencia estructural de la obra completa. Detecta capítulos que no contribuyen a la trama principal, subtramas abandonadas, arcos narrativos incompletos, y desconexiones entre partes del libro.

---

## Objetivos

1. Mapear la estructura narrativa (tramas, subtramas, arcos)
2. Detectar capítulos "desconectados" de la trama principal
3. Identificar subtramas abandonadas o sin resolución
4. Evaluar la completitud de arcos narrativos
5. Verificar conexiones causales entre eventos
6. Detectar finales inesperados / Deus ex machina
7. Identificar personajes o elementos no introducidos correctamente
8. Alertar sobre eventos absurdos o sin preparación narrativa

---

## Modelo de Datos

```python
@dataclass
class PlotThread:
    """Una línea argumental (trama o subtrama)."""
    id: str
    name: str
    thread_type: ThreadType

    # Alcance
    first_chapter: int
    last_chapter: int
    chapters_present: list[int]

    # Personajes involucrados
    main_characters: list[str]      # IDs de entidades

    # Estado
    is_resolved: bool
    resolution_chapter: Optional[int]

    # Conexiones
    connected_threads: list[str]    # IDs de tramas conectadas

    # Eventos clave
    key_events: list[PlotEvent]


class ThreadType(Enum):
    MAIN_PLOT = "main"              # Trama principal
    SUBPLOT = "subplot"             # Subtrama
    CHARACTER_ARC = "arc"           # Arco de personaje
    ROMANCE = "romance"             # Línea romántica
    MYSTERY = "mystery"             # Misterio/revelación
    CONFLICT = "conflict"           # Conflicto específico


@dataclass
class PlotEvent:
    """Evento significativo en una trama."""
    id: str
    description: str
    chapter: int
    event_type: EventType

    # Causalidad
    causes: list[str]               # IDs de eventos que causan este
    consequences: list[str]         # IDs de eventos causados

    # Personajes
    involved_entities: list[str]


class EventType(Enum):
    INTRODUCTION = "introduction"   # Introducción de elemento
    COMPLICATION = "complication"   # Complicación/conflicto
    REVELATION = "revelation"       # Revelación de información
    DECISION = "decision"           # Decisión importante
    CONSEQUENCE = "consequence"     # Consecuencia de acción previa
    CLIMAX = "climax"               # Punto álgido
    RESOLUTION = "resolution"       # Resolución
    TWIST = "twist"                 # Giro inesperado
    DEUS_EX_MACHINA = "deus_ex"     # Solución "caída del cielo"


@dataclass
class NarrativeElement:
    """Elemento narrativo que requiere introducción previa."""
    id: str
    element_type: str               # "character", "object", "ability", "location", "rule"
    name: str
    first_mention_chapter: int
    first_mention_context: str      # "active_use", "background", "foreshadowing"
    is_properly_introduced: bool
    introduction_quality: float     # 0.0 = aparece de la nada, 1.0 = bien preparado


@dataclass
class ChapterContribution:
    """Contribución de un capítulo a las tramas."""
    chapter_index: int

    # Contribuciones por trama
    contributions: dict[str, float]  # thread_id -> contribution_score

    # Métricas
    total_contribution: float
    advances_main_plot: bool
    advances_subplot: bool
    is_transitional: bool           # Solo conecta capítulos
    is_standalone: bool             # No conecta con nada

    # Problemas
    issues: list[StructuralIssue]


@dataclass
class StructuralIssue:
    """Problema estructural detectado."""
    code: str                       # Código técnico: "STRUCT_DEUS_EX_MACHINA"
    alert_type: str                 # Tipo legible: "Deus ex machina"
    description: str
    severity: str                   # "error", "warning", "info"
    affected_elements: list[str]    # Capítulos, tramas, personajes
    suggestion: str

    # Referencias precisas (opcional, cuando aplique)
    establishing_reference: Optional[TextReference] = None
    establishing_quote: Optional[str] = None
    contradicting_reference: Optional[TextReference] = None
    contradicting_quote: Optional[str] = None
```

---

## Componentes

### 1. PlotThreadDetector

```python
class PlotThreadDetector:
    """Detecta líneas argumentales."""

    def detect_threads(
        self,
        chapters: list[Chapter],
        entities: list[Entity],
        relationships: list[EntityRelationship]
    ) -> list[PlotThread]:
        """Detecta tramas principales y subtramas."""
        threads = []

        # Detectar trama principal (basada en protagonista)
        main_thread = self._detect_main_plot(chapters, entities)
        threads.append(main_thread)

        # Detectar subtramas por personaje
        for entity in entities:
            if entity.importance == EntityImportance.MAIN:
                arc = self._detect_character_arc(entity, chapters)
                if arc:
                    threads.append(arc)

        # Detectar subtramas por relación
        for rel in relationships:
            if rel.relation_type in [RelationType.LOVER, RelationType.RIVAL]:
                subplot = self._detect_relationship_subplot(rel, chapters)
                if subplot:
                    threads.append(subplot)

        return threads

    def _detect_main_plot(
        self,
        chapters: list[Chapter],
        entities: list[Entity]
    ) -> PlotThread:
        """Identifica la trama principal."""
        # El protagonista y sus objetivos definen la trama principal
        protagonist = self._find_protagonist(entities)
        ...
```

### 2. ContributionAnalyzer

```python
class ChapterContributionAnalyzer:
    """Analiza qué aporta cada capítulo."""

    def analyze_contribution(
        self,
        chapter: Chapter,
        threads: list[PlotThread],
        events: list[PlotEvent]
    ) -> ChapterContribution:
        """Calcula contribución del capítulo."""
        contributions = {}

        for thread in threads:
            score = self._calculate_thread_contribution(chapter, thread, events)
            contributions[thread.id] = score

        total = sum(contributions.values())

        return ChapterContribution(
            chapter_index=chapter.index,
            contributions=contributions,
            total_contribution=total,
            advances_main_plot=any(
                t.thread_type == ThreadType.MAIN_PLOT and contributions[t.id] > 0.3
                for t in threads
            ),
            is_standalone=total < 0.1
        )

    def _calculate_thread_contribution(
        self,
        chapter: Chapter,
        thread: PlotThread,
        events: list[PlotEvent]
    ) -> float:
        """Calcula cuánto aporta un capítulo a una trama."""
        score = 0.0

        # Eventos de la trama en este capítulo
        chapter_events = [e for e in events if e.chapter == chapter.index]
        thread_events = [e for e in chapter_events if e.id in [ke.id for ke in thread.key_events]]

        for event in thread_events:
            # Peso según tipo de evento
            weights = {
                EventType.CLIMAX: 1.0,
                EventType.REVELATION: 0.8,
                EventType.DECISION: 0.7,
                EventType.COMPLICATION: 0.6,
                EventType.CONSEQUENCE: 0.5,
                EventType.INTRODUCTION: 0.4,
                EventType.RESOLUTION: 0.9
            }
            score += weights.get(event.event_type, 0.3)

        return min(1.0, score)
```

### 3. CoherenceChecker

```python
class StructuralCoherenceChecker:
    """Verifica coherencia estructural."""

    def check_abandoned_subplots(
        self,
        threads: list[PlotThread],
        total_chapters: int
    ) -> list[StructuralIssue]:
        """Detecta subtramas abandonadas."""
        issues = []

        for thread in threads:
            if thread.thread_type != ThreadType.MAIN_PLOT:
                # Subtrama que no se resuelve
                if not thread.is_resolved:
                    issues.append(StructuralIssue(
                        code="STRUCT_ABANDONED_SUBPLOT",
                        alert_type="Subtrama abandonada",
                        description=f"Subtrama '{thread.name}' no tiene resolución",
                        severity="warning",
                        affected_elements=[thread.id],
                        suggestion="Resolver la subtrama o eliminarla"
                    ))

                # Subtrama que desaparece antes del final
                gap = total_chapters - thread.last_chapter
                if gap > 3 and not thread.is_resolved:
                    issues.append(StructuralIssue(
                        code="STRUCT_FORGOTTEN_SUBPLOT",
                        alert_type="Subtrama olvidada",
                        description=f"Subtrama '{thread.name}' desaparece en cap {thread.last_chapter}",
                        severity="warning",
                        affected_elements=[thread.id],
                        suggestion=f"Retomar la subtrama o resolverla antes"
                    ))

        return issues

    def check_disconnected_chapters(
        self,
        contributions: list[ChapterContribution]
    ) -> list[StructuralIssue]:
        """Detecta capítulos desconectados."""
        issues = []

        for contrib in contributions:
            if contrib.is_standalone:
                issues.append(StructuralIssue(
                    code="STRUCT_DISCONNECTED_CHAPTER",
                    alert_type="Capítulo desconectado",
                    description=f"Capítulo {contrib.chapter_index} no conecta con ninguna trama",
                    severity="warning",
                    affected_elements=[f"chapter_{contrib.chapter_index}"],
                    suggestion="Conectar con trama principal o considerar eliminar"
                ))

            elif not contrib.advances_main_plot and not contrib.advances_subplot:
                issues.append(StructuralIssue(
                    code="STRUCT_FILLER_CHAPTER",
                    alert_type="Capítulo de relleno",
                    description=f"Capítulo {contrib.chapter_index} no avanza ninguna trama",
                    severity="info",
                    affected_elements=[f"chapter_{contrib.chapter_index}"],
                    suggestion="Añadir progresión de trama o combinar con otro capítulo"
                ))

        return issues

    def check_causal_chain(
        self,
        events: list[PlotEvent]
    ) -> list[StructuralIssue]:
        """Verifica que los eventos tengan conexión causal."""
        issues = []

        for event in events:
            # Eventos sin causa ni contexto
            if not event.causes and event.event_type != EventType.INTRODUCTION:
                issues.append(StructuralIssue(
                    code="STRUCT_UNEXPLAINED_EVENT",
                    alert_type="Evento sin causa",
                    description=f"Evento '{event.description}' no tiene causa aparente",
                    severity="info",
                    affected_elements=[event.id],
                    suggestion="Establecer conexión causal con eventos anteriores"
                ))

            # Eventos importantes sin consecuencias
            if event.event_type in [EventType.DECISION, EventType.REVELATION]:
                if not event.consequences:
                    issues.append(StructuralIssue(
                        code="STRUCT_NO_CONSEQUENCES",
                        alert_type="Evento sin consecuencias",
                        description=f"'{event.description}' no tiene consecuencias visibles",
                        severity="warning",
                        affected_elements=[event.id],
                        suggestion="Mostrar el impacto de este evento"
                    ))

        return issues
```

### 4. ArcCompletenessChecker

```python
class ArcCompletenessChecker:
    """Verifica completitud de arcos narrativos."""

    # Estructura clásica de tres actos
    THREE_ACT_STRUCTURE = {
        "setup": (0.0, 0.25),        # Primer 25%
        "confrontation": (0.25, 0.75), # 25-75%
        "resolution": (0.75, 1.0)     # Último 25%
    }

    def check_arc_structure(
        self,
        thread: PlotThread,
        events: list[PlotEvent],
        total_chapters: int
    ) -> list[StructuralIssue]:
        """Verifica estructura del arco."""
        issues = []

        # Mapear eventos a actos
        events_by_act = self._categorize_by_act(events, total_chapters)

        # Verificar setup
        if not events_by_act["setup"]:
            issues.append(StructuralIssue(
                code="STRUCT_MISSING_SETUP",
                alert_type="Falta introducción",
                description=f"Trama '{thread.name}' no tiene introducción clara",
                severity="warning",
                affected_elements=[thread.id],
                suggestion="Establecer la situación inicial y objetivos"
            ))

        # Verificar confrontation (conflicto)
        confrontation_events = events_by_act["confrontation"]
        complications = [e for e in confrontation_events if e.event_type == EventType.COMPLICATION]
        if len(complications) < 2:
            issues.append(StructuralIssue(
                code="STRUCT_WEAK_CONFLICT",
                alert_type="Conflicto débil",
                description=f"Trama '{thread.name}' tiene poco conflicto en el desarrollo",
                severity="info",
                affected_elements=[thread.id],
                suggestion="Añadir complicaciones y obstáculos"
            ))

        # Verificar climax
        climax_events = [e for e in events if e.event_type == EventType.CLIMAX]
        if not climax_events:
            issues.append(StructuralIssue(
                code="STRUCT_MISSING_CLIMAX",
                alert_type="Sin clímax",
                description=f"Trama '{thread.name}' no tiene clímax identificable",
                severity="warning",
                affected_elements=[thread.id],
                suggestion="Definir un punto álgido para esta trama"
            ))

        # Verificar resolución
        if not events_by_act["resolution"] and thread.thread_type == ThreadType.MAIN_PLOT:
            issues.append(StructuralIssue(
                code="STRUCT_MISSING_RESOLUTION",
                alert_type="Sin resolución",
                description="La trama principal no tiene resolución",
                severity="error",
                affected_elements=[thread.id],
                suggestion="Añadir conclusión a la historia"
            ))

        return issues
```

### 5. NarrativeSetupChecker

```python
class NarrativeSetupChecker:
    """
    Verifica que los elementos narrativos estén correctamente introducidos.
    Detecta "Deus ex machina", personajes que aparecen de la nada, y
    eventos sin preparación.
    """

    def check_element_introduction(
        self,
        element: NarrativeElement,
        chapters: list[Chapter]
    ) -> list[StructuralIssue]:
        """Verifica si un elemento está bien introducido."""
        issues = []

        # Elemento que aparece en uso activo sin introducción previa
        if element.first_mention_context == "active_use" and not element.is_properly_introduced:
            issues.append(StructuralIssue(
                code="STRUCT_ELEMENT_NOT_INTRODUCED",
                alert_type="Elemento no introducido",
                description=f"'{element.name}' aparece en acción sin presentación previa",
                severity="warning",
                affected_elements=[element.id, f"chapter_{element.first_mention_chapter}"],
                suggestion="Introducir el elemento antes de su uso activo (foreshadowing, mención casual)"
            ))

        return issues

    def check_deus_ex_machina(
        self,
        resolution_events: list[PlotEvent],
        all_elements: list[NarrativeElement]
    ) -> list[StructuralIssue]:
        """Detecta soluciones que aparecen de la nada."""
        issues = []

        for event in resolution_events:
            if event.event_type in [EventType.RESOLUTION, EventType.CLIMAX]:
                # Buscar elementos usados en la resolución que no fueron introducidos
                for entity_id in event.involved_entities:
                    element = self._find_element(entity_id, all_elements)
                    if element and element.introduction_quality < 0.3:
                        issues.append(StructuralIssue(
                            code="STRUCT_DEUS_EX_MACHINA",
                            alert_type="Deus ex machina",
                            description=f"'{element.name}' resuelve la trama pero no fue preparado narrativamente",
                            severity="error",
                            affected_elements=[event.id, element.id],
                            suggestion="Introducir este elemento antes del clímax (regla de Chéjov: si aparece un arma, debe usarse)"
                        ))

        return issues

    def check_character_appearance(
        self,
        character: Entity,
        chapters: list[Chapter]
    ) -> list[StructuralIssue]:
        """Verifica que personajes importantes estén bien introducidos."""
        issues = []

        # Personaje importante que aparece tarde sin preparación
        if character.importance == EntityImportance.MAIN:
            first_chapter = self._get_first_appearance(character, chapters)
            total_chapters = len(chapters)

            # Aparece después del primer 30% del libro
            if first_chapter / total_chapters > 0.3:
                # Verificar si hubo menciones previas (foreshadowing)
                prior_mentions = self._count_prior_mentions(character, chapters, first_chapter)
                if prior_mentions == 0:
                    issues.append(StructuralIssue(
                        code="STRUCT_LATE_CHARACTER_INTRODUCTION",
                        alert_type="Personaje introducido tarde",
                        description=f"Personaje importante '{character.canonical_name}' aparece en cap {first_chapter} sin preparación",
                        severity="warning",
                        affected_elements=[character.id],
                        suggestion="Mencionar al personaje antes o reducir su importancia en la trama"
                    ))

        return issues

    def check_ability_preparation(
        self,
        character: Entity,
        ability_use_event: PlotEvent
    ) -> list[StructuralIssue]:
        """Verifica que habilidades/poderes estén establecidos antes de usarse."""
        issues = []

        # Habilidad usada para resolver problema sin establecerse antes
        ability = self._extract_ability_from_event(ability_use_event)
        if ability:
            prior_establishment = self._find_ability_establishment(character, ability)
            if not prior_establishment:
                issues.append(StructuralIssue(
                    code="STRUCT_UNESTABLISHED_ABILITY",
                    alert_type="Habilidad no establecida",
                    description=f"'{character.canonical_name}' usa '{ability}' sin que se estableciera previamente",
                    severity="warning",
                    affected_elements=[character.id, ability_use_event.id],
                    suggestion="Mostrar o mencionar esta habilidad antes de que sea crucial para la trama"
                ))

        return issues

    def check_world_rule_consistency(
        self,
        world_rules: list[NarrativeElement],
        events: list[PlotEvent]
    ) -> list[StructuralIssue]:
        """Verifica que las reglas del mundo se respeten."""
        issues = []

        for rule in world_rules:
            violations = self._find_rule_violations(rule, events)
            for violation in violations:
                issues.append(StructuralIssue(
                    code="STRUCT_WORLD_RULE_VIOLATED",
                    alert_type="Regla del mundo violada",
                    description=f"Evento contradice regla establecida: '{rule.name}'",
                    severity="warning",
                    affected_elements=[rule.id, violation.id],
                    suggestion="Justificar la excepción o corregir el evento"
                ))

        return issues
```

### 6. EventLogicChecker

```python
class EventLogicChecker:
    """
    Verifica la lógica y coherencia de eventos individuales.
    Usa IA para detectar eventos absurdos o ilógicos.
    """

    def __init__(self, inference_engine: Optional[ExpectationInferenceEngine] = None):
        self.inference_engine = inference_engine

    def check_event_logic(
        self,
        event: PlotEvent,
        context: NarrativeContext
    ) -> list[StructuralIssue]:
        """Verifica si un evento tiene sentido en su contexto."""
        issues = []

        if self.inference_engine:
            # Preguntar a IA si el evento tiene sentido
            logic_check = self.inference_engine.check_event_plausibility(
                event=event,
                context=context,
                prompt=f"""
                Dado el contexto narrativo:
                - Personajes involucrados: {context.characters}
                - Situación previa: {context.prior_situation}
                - Reglas del mundo: {context.world_rules}

                ¿El siguiente evento tiene sentido lógico?
                Evento: "{event.description}"

                Responde:
                1. ¿Es plausible? (sí/no/parcialmente)
                2. Si no es plausible, ¿por qué?
                3. ¿Qué preparación faltaría para que sea creíble?
                """
            )

            if logic_check.plausibility < 0.5:
                issues.append(StructuralIssue(
                    code="STRUCT_ILLOGICAL_EVENT",
                    alert_type="Evento ilógico o absurdo",
                    description=f"Evento '{event.description}' no tiene sentido en el contexto",
                    severity="warning" if logic_check.plausibility > 0.3 else "error",
                    affected_elements=[event.id],
                    suggestion=logic_check.missing_preparation
                ))

        return issues

    def check_character_motivation(
        self,
        character: Entity,
        action: PlotEvent,
        established_motivations: list[str]
    ) -> list[StructuralIssue]:
        """Verifica que las acciones de personajes tengan motivación."""
        issues = []

        # Acción importante sin motivación establecida
        if action.event_type in [EventType.DECISION, EventType.CLIMAX]:
            motivation_found = self._find_motivation_for_action(
                character, action, established_motivations
            )
            if not motivation_found:
                issues.append(StructuralIssue(
                    code="STRUCT_UNMOTIVATED_ACTION",
                    alert_type="Acción sin motivación",
                    description=f"'{character.canonical_name}' realiza '{action.description}' sin motivación clara",
                    severity="info",
                    affected_elements=[character.id, action.id],
                    suggestion="Establecer la motivación del personaje antes de esta acción"
                ))

        return issues
```

---

## Alertas Generadas

### Filosofía: Sistema Extensible

Las alertas son **100% extensibles**. La tabla siguiente muestra **ejemplos base**, pero:

1. **La IA puede detectar nuevos tipos de problemas** no listados aquí
2. **El sistema genera códigos y tipos dinámicamente** según el contexto
3. **No hay lista cerrada** - cualquier inconsistencia narrativa detectada genera alerta

```python
# El sistema NO está limitado a estos tipos
# La IA puede crear nuevos dinámicamente:

def generate_alert(issue_detected: str, context: NarrativeContext) -> StructuralIssue:
    """
    La IA analiza el problema y genera:
    - code: Código técnico generado (ej: "STRUCT_TIMELINE_PARADOX")
    - alert_type: Descripción legible (ej: "Paradoja temporal")
    - severity: Calculada según impacto narrativo
    """
    return inference_engine.classify_structural_issue(
        issue=issue_detected,
        context=context
    )
```

### Ejemplos Base (No Exhaustivos)

| Código | Tipo (visible al editor) | Descripción | Severidad |
|--------|--------------------------|-------------|-----------|
| `STRUCT_ABANDONED_SUBPLOT` | Subtrama abandonada | Subtrama sin resolución | Warning |
| `STRUCT_FORGOTTEN_SUBPLOT` | Subtrama olvidada | Subtrama que desaparece sin cierre | Warning |
| `STRUCT_DISCONNECTED_CHAPTER` | Capítulo desconectado | Capítulo sin conexión con tramas | Warning |
| `STRUCT_FILLER_CHAPTER` | Capítulo de relleno | Capítulo que no avanza ninguna trama | Info |
| `STRUCT_UNEXPLAINED_EVENT` | Evento sin causa | Evento importante sin explicación | Info |
| `STRUCT_NO_CONSEQUENCES` | Evento sin consecuencias | Decisión/revelación sin impacto | Warning |
| `STRUCT_MISSING_SETUP` | Falta introducción | Trama sin establecimiento inicial | Warning |
| `STRUCT_WEAK_CONFLICT` | Conflicto débil | Poco conflicto en el desarrollo | Info |
| `STRUCT_MISSING_CLIMAX` | Sin clímax | Trama sin punto álgido identificable | Warning |
| `STRUCT_MISSING_RESOLUTION` | Sin resolución | Trama principal sin conclusión | Error |
| `STRUCT_DEUS_EX_MACHINA` | Deus ex machina | Solución aparece sin preparación | Error |
| `STRUCT_ELEMENT_NOT_INTRODUCED` | Elemento no introducido | Objeto/lugar/regla usado sin presentar | Warning |
| `STRUCT_LATE_CHARACTER_INTRODUCTION` | Personaje introducido tarde | Personaje importante aparece tarde sin preparación | Warning |
| `STRUCT_UNESTABLISHED_ABILITY` | Habilidad no establecida | Personaje usa habilidad no mostrada antes | Warning |
| `STRUCT_WORLD_RULE_VIOLATED` | Regla del mundo violada | Evento contradice regla establecida | Warning |
| `STRUCT_ILLOGICAL_EVENT` | Evento ilógico o absurdo | Evento no tiene sentido en contexto | Warning/Error |
| `STRUCT_UNMOTIVATED_ACTION` | Acción sin motivación | Personaje actúa sin razón establecida | Info |
| *...IA genera más...* | *Según contexto* | *Detectado dinámicamente* | *Variable* |

### Ejemplos de Alertas Generadas por IA (No Predefinidas)

La IA puede detectar problemas no contemplados en la lista base:

```
🤖 PARADOJA TEMPORAL                                                  [Error]
   (Código generado: STRUCT_AI_TIMELINE_PARADOX)

   El personaje recuerda un evento que aún no ha ocurrido en la narrativa.

🤖 CONOCIMIENTO IMPOSIBLE                                            [Warning]
   (Código generado: STRUCT_AI_IMPOSSIBLE_KNOWLEDGE)

   María sabe que Pedro está en peligro, pero no hay forma de que
   lo supiera desde su ubicación.

🤖 TONO NARRATIVO INCONSISTENTE                                       [Info]
   (Código generado: STRUCT_AI_TONE_SHIFT)

   El capítulo 12 tiene un tono cómico que rompe con el drama
   establecido en los capítulos 10-11 sin transición.

🤖 ESCALA TEMPORAL IRREAL                                            [Warning]
   (Código generado: STRUCT_AI_UNREALISTIC_TIMING)

   El viaje de 500km se completa en una hora sin explicación
   (¿transporte especial? ¿magia?).
```

---

## Ejemplos de Alertas Precisas

**Ejemplo 1: Deus ex machina**
```
🚨 DEUS EX MACHINA                                                    [Error]

"Amuleto de protección" resuelve el clímax

📍 Página 287 (Cap. 22 "El enfrentamiento final"):
   "Juan sacó el amuleto de protección que su abuela le había dado y
    derrotó al villano instantáneamente."

❌ PROBLEMA: El amuleto NO aparece mencionado en ningún capítulo anterior.

💡 Sugerencia: Introducir el amuleto antes del clímax. Opciones:
   - Mencionarlo cuando Juan se despide de su abuela (cap 3)
   - Que Juan lo toque nerviosamente en momentos de tensión
   - Flashback breve sobre el origen del amuleto
```

**Ejemplo 2: Personaje no introducido**
```
⚠️ PERSONAJE INTRODUCIDO TARDE                                       [Warning]

"El Sabio Anciano" - personaje clave introducido en cap 18 de 24

📍 Página 245 (Cap. 18): "El Sabio Anciano les reveló el secreto para
   derrotar al dragón."

❌ PROBLEMA: Este personaje resuelve el problema principal pero aparece
   por primera vez al 75% del libro sin ninguna mención previa.

💡 Sugerencia: Si es tan importante, mencionarlo antes:
   - "La leyenda dice que un sabio conoce el secreto..." (cap 5)
   - Que otro personaje lo mencione como posible solución
```

**Ejemplo 3: Evento ilógico**
```
⚠️ EVENTO ILÓGICO O ABSURDO                                          [Warning]

Acción contradice capacidades establecidas del personaje

📍 Página 156 (Cap. 12): "Ana, que siempre había tenido miedo al agua
   y nunca aprendió a nadar, cruzó el río a nado para escapar."

📍 Contexto previo (pág. 34, cap 3): "Ana evitaba las piscinas desde
   niña. El simple sonido del agua la paralizaba de terror."

❌ PROBLEMA: La acción contradice un rasgo establecido del personaje
   sin justificación narrativa.

💡 Sugerencia: Añadir una escena donde Ana supera su miedo, o usar
   otro medio de escape coherente con su personalidad.
```

**Ejemplo 4: Habilidad no establecida**
```
⚠️ HABILIDAD NO ESTABLECIDA                                          [Warning]

"Carlos" usa habilidad de combate no mostrada antes

📍 Página 198 (Cap. 15): "Carlos derrotó a los tres atacantes con
   movimientos precisos de artes marciales."

❌ PROBLEMA: Carlos fue presentado como "un oficinista tímido que
   nunca había peleado" (pág. 12). No hay escenas de entrenamiento
   ni menciones a conocimientos de defensa personal.

💡 Sugerencia: Establecer la habilidad previamente:
   - "Carlos practicaba karate los sábados" (mención casual)
   - Escena donde menciona su pasado en el ejército
   - Flashback breve de entrenamiento
```

---

## Visualización

### Mapa de Contribución

```
              Main Plot  Romance  Mystery  Character Arc
Cap 1:        ████       ░░       ░░       ██
Cap 2:        ██         ████     ░░       ██
Cap 3:        ████       ██       ████     ░░
Cap 4:        ░░         ░░       ░░       ░░  ⚠️ Filler
Cap 5:        ██████     ██       ████     ████
Cap 6:        ████████   ██       ██████   ██   ← Climax
Cap 7:        ██████     ████     ████     ██████

Leyenda: ████ = Alta contribución, ░░ = Ninguna
```

### Diagrama de Flujo de Tramas

```
Cap 1 ──────────────────────────────────────────> Main Plot
       \
        \──────> Romance ─────────────────────────> Resolved (Cap 6)
         \
          \────────────> Mystery ─────────────────> ⚠️ Not resolved
```

---

## Criterios de Aceptación

- [ ] Detección de trama principal
- [ ] Detección de subtramas básicas
- [ ] Cálculo de contribución por capítulo
- [ ] Detección de capítulos desconectados
- [ ] Detección de subtramas abandonadas
- [ ] Verificación de estructura de tres actos
- [ ] Detección de Deus ex machina
- [ ] Verificación de introducción de personajes importantes
- [ ] Verificación de preparación de habilidades/elementos
- [ ] Detección de eventos ilógicos (con IA)
- [ ] Verificación de motivaciones de personajes
- [ ] Alertas con citas precisas y sugerencias útiles

---

## Notas de Implementación

- Este es el STEP más complejo, requiere todos los anteriores
- La detección de "eventos" es el mayor desafío técnico
- Empezar con análisis manual de eventos, automatizar después
- El usuario puede definir manualmente las tramas
- Considerar diferentes estructuras narrativas (no solo tres actos)

---

## Referencias

- [Character Relevance](./step-10.1-character-relevance.md)
- [Chapter Pacing](./step-10.2-chapter-pacing.md)
- [Timeline Analysis](../phase-6/step-6.1-temporal-markers.md)
- [Entity Relationships](../phase-9/step-9.1-entity-relationships.md)
