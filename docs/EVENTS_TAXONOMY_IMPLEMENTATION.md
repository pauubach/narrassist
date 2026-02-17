# Plan de Implementación - Taxonomía Ampliada de Eventos Narrativos

**Fecha**: 2026-02-17
**Estimación**: 8-12 horas de desarrollo
**Prioridad**: Media (Tier 1: Alta, Tier 2-3: Baja)

---

## 📋 Resumen Ejecutivo

Ampliar el sistema de detección de eventos narrativos de **7 eventos básicos** a **45+ eventos** organizados en 3 tiers, con énfasis en detectar inconsistencias mediante rastreo de pares de eventos (ej: `promise` → `broken_promise`).

### Estado Actual
- 7 eventos básicos: `first_appearance`, `return`, `death`, `conflict`, `revelation`, `decision`, `transformation`
- Detección en `chapter_summary.py` mediante heurísticas simples
- No hay rastreo de continuidad entre capítulos

### Estado Objetivo
- 18 eventos Tier 1 (alta prioridad) completamente implementados
- 15 eventos Tier 2 (prioridad media) parcialmente implementados
- Rastreo de 8 pares de eventos para detectar inconsistencias
- Soporte para eventos especializados por género (thriller, fantasía, romance)

---

## 🎯 Tier 1: Eventos de Alta Prioridad (18 eventos)

### Grupo 1: Detección NLP Básica (8 eventos)

#### 1. `promise` / `broken_promise`
**Descripción**: Promesa hecha por personaje / Incumplimiento de promesa previa
**Método**: spaCy + verbos clave ("prometer", "jurar", "palabra de honor")
**Patrón**:
```python
PROMISE_VERBS = ["prometer", "jurar", "garantizar", "asegurar", "dar palabra"]
PROMISE_PATTERNS = [
    "te prometo",
    "te juro",
    "palabra de honor",
    "te doy mi palabra",
]
```

**Rastreo**: Almacenar promesas en `chapter_summary.key_events` con:
```json
{
  "event_type": "promise",
  "description": "Juan prometió volver antes del anochecer",
  "characters_involved": ["Juan"],
  "chapter": 3,
  "metadata": {
    "promise_text": "volver antes del anochecer",
    "promise_id": "uuid"
  }
}
```

Luego detectar `broken_promise` si en capítulos posteriores:
- El personaje NO cumple
- Mención explícita de incumplimiento ("olvidó su promesa", "no regresó")

**Alerta generada**: Si `broken_promise` sin `promise` previo → inconsistencia

---

#### 2. `confession` / `lie`
**Descripción**: Confesión de secreto / Mentira dicha
**Método**: NLP ("confesar", "admitir", "revelar") vs ("mentir", "engañar", "ocultar")
**Patrón**:
```python
CONFESSION_VERBS = ["confesar", "admitir", "reconocer", "revelar"]
LIE_VERBS = ["mentir", "engañar", "ocultar", "disimular", "fingir"]
```

**Rastreo**: Almacenar en metadata qué se confesó/mintió
**Alerta**: Si `confession` contradice `lie` previo → inconsistencia de coherencia

---

#### 3. `acquisition` / `loss`
**Descripción**: Obtención de objeto/habilidad / Pérdida de objeto/persona
**Método**: NLP + NER (detectar objeto PROPN/NOUN tras verbos clave)
**Patrón**:
```python
ACQUISITION_VERBS = ["conseguir", "obtener", "encontrar", "recibir", "heredar"]
LOSS_VERBS = ["perder", "robar", "desaparecer", "extraviar"]
```

**Ejemplo**:
```
"María encontró la espada ancestral" → acquisition
  - object: "espada ancestral"
  - character: "María"
```

**Rastreo**: Inventario de objetos por personaje
**Alerta**: Si usa objeto que nunca adquirió → inconsistencia

---

#### 4. `injury` / `healing`
**Descripción**: Herida/lesión de personaje / Curación de herida
**Método**: NLP + NER (anatomía) + verbos clave
**Patrón**:
```python
INJURY_VERBS = ["herir", "lastimar", "fracturar", "sangrar", "atravesar"]
HEALING_VERBS = ["curar", "sanar", "recuperarse", "cicatrizar"]
BODY_PARTS = ["brazo", "pierna", "hombro", "cabeza", "pecho", "mano"]
```

**Ejemplo**:
```
"Le atravesaron el hombro con la flecha" → injury
  - character: detectar por contexto (sujeto/objeto)
  - body_part: "hombro"
  - severity: inferir de verbos (atravesar = grave)
```

**Rastreo**: Estado de salud por personaje
**Alerta**: Si `healing` sin `injury` previo → inconsistencia

---

### Grupo 2: Detección Heurística (6 eventos)

#### 5. `flashback_start` / `flashback_end`
**Descripción**: Inicio/fin de analepsis temporal
**Método**: Regex + marcadores temporales
**Patrón**:
```python
FLASHBACK_START_PATTERNS = [
    r"recordó\b",
    r"años atrás",
    r"en aquel entonces",
    r"cuando era (niño|joven|pequeño)",
    r"\d+ años (antes|atrás)",
    r"en el pasado",
]

FLASHBACK_END_PATTERNS = [
    r"volvió (en sí|al presente|a la realidad)",
    r"el presente",
    r"ahora\b",
    r"de vuelta (en|a)",
]
```

**Rastreo**: Stack de analepsis (LIFO)
**Alerta**: Si `flashback_start` sin `flashback_end` → analepsis sin cerrar

---

#### 6. `pov_change`
**Descripción**: Cambio de punto de vista narrativo
**Método**: Análisis de pronombres (1ª vs 3ª persona) + nombres
**Patrón**:
```python
def detect_pov_change(prev_chapter_pov: str, current_chapter_text: str) -> bool:
    # Detectar pronombres predominantes
    first_person_count = count_patterns(text, [r"\byo\b", r"\bme\b", r"\bmi\b"])
    third_person_count = count_patterns(text, [r"\bél\b", r"\bella\b"])

    current_pov = "first" if first_person_count > third_person_count else "third"
    return current_pov != prev_chapter_pov
```

**Rastreo**: POV por capítulo
**Alerta**: Cambio de POV en mitad de capítulo (sin marcador de sección)

---

#### 7. `time_skip`
**Descripción**: Salto temporal explícito
**Método**: Regex de marcadores temporales
**Patrón**:
```python
TIME_SKIP_PATTERNS = [
    r"(\d+) (años|meses|días|horas) (después|más tarde)",
    r"al día siguiente",
    r"a la mañana siguiente",
    r"tres semanas (después|más tarde)",
]
```

---

#### 8-10. `dream_sequence`, `narrative_intrusion`
Similar a los anteriores, con regex específicos.

---

### Grupo 3: Detección LLM (4 eventos)

#### 11. `betrayal` / `alliance`
**Descripción**: Traición/alianza entre personajes
**Método**: LLM (Ollama: qwen2.5) con prompt especializado
**Prompt**:
```python
BETRAYAL_PROMPT = """
Analiza el siguiente fragmento narrativo y determina si ocurre una TRAICIÓN.

Fragmento:
{text}

Personajes conocidos: {characters}

Responde en JSON:
{
  "is_betrayal": true/false,
  "betrayer": "nombre del traidor",
  "betrayed": "nombre del traicionado",
  "description": "breve descripción de la traición",
  "confidence": 0.0-1.0
}
"""
```

**Rastreo**: Relaciones entre personajes (grafo dirigido)
**Alerta**: Si `betrayal` entre personajes sin relación previa → inconsistencia

---

## 📊 Arquitectura de Implementación

### 1. Módulo de Detección de Eventos

**Nuevo archivo**: `src/narrative_assistant/analysis/event_detection.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class EventType(Enum):
    # Tier 1 - High Priority
    PROMISE = "promise"
    BROKEN_PROMISE = "broken_promise"
    CONFESSION = "confession"
    LIE = "lie"
    ACQUISITION = "acquisition"
    LOSS = "loss"
    INJURY = "injury"
    HEALING = "healing"
    FLASHBACK_START = "flashback_start"
    FLASHBACK_END = "flashback_end"
    POV_CHANGE = "pov_change"
    TIME_SKIP = "time_skip"
    DREAM_SEQUENCE = "dream_sequence"
    NARRATIVE_INTRUSION = "narrative_intrusion"
    BETRAYAL = "betrayal"
    ALLIANCE = "alliance"
    EPIPHANY = "epiphany"
    SACRIFICE = "sacrifice"

    # Tier 2 - Medium Priority (implementar después)
    ESCAPE = "escape"
    CAPTURE = "capture"
    RESCUE = "rescue"
    # ... etc

@dataclass
class NarrativeEvent:
    event_type: EventType
    description: str
    chapter: int
    characters_involved: List[str]
    confidence: float
    metadata: Dict[str, Any]

class EventDetector:
    """Detector de eventos narrativos multi-método"""

    def __init__(self, nlp, llm_manager=None):
        self.nlp = nlp
        self.llm = llm_manager
        self.detectors = {
            EventType.PROMISE: self._detect_promise,
            EventType.BETRAYAL: self._detect_betrayal_llm,
            # ... registro de detectores
        }

    def detect_events(self, text: str, chapter: int, entities: List[Entity]) -> List[NarrativeEvent]:
        """Detecta todos los eventos en un fragmento de texto"""
        events = []

        # NLP-based detection (rápido)
        events.extend(self._detect_nlp_events(text, chapter, entities))

        # Heuristic detection (medio)
        events.extend(self._detect_heuristic_events(text, chapter))

        # LLM-based detection (lento, solo si está habilitado)
        if self.llm:
            events.extend(self._detect_llm_events(text, chapter, entities))

        return events

    def _detect_promise(self, text: str, chapter: int, entities: List[Entity]) -> List[NarrativeEvent]:
        """Detecta promesas usando spaCy + verbos clave"""
        doc = self.nlp(text)
        events = []

        PROMISE_VERBS = {"prometer", "jurar", "garantizar", "asegurar"}

        for sent in doc.sents:
            for token in sent:
                if token.lemma_ in PROMISE_VERBS:
                    # Extraer sujeto (quién promete)
                    subject = self._extract_subject(token)
                    # Extraer objeto (qué promete)
                    promise_content = self._extract_promise_content(token, sent)

                    if subject and promise_content:
                        events.append(NarrativeEvent(
                            event_type=EventType.PROMISE,
                            description=f"{subject} prometió {promise_content}",
                            chapter=chapter,
                            characters_involved=[subject],
                            confidence=0.85,
                            metadata={
                                "promise_text": promise_content,
                                "verb": token.lemma_,
                            }
                        ))

        return events
```

---

### 2. Sistema de Rastreo de Continuidad

**Nuevo archivo**: `src/narrative_assistant/analysis/event_tracker.py`

```python
from typing import Dict, List, Optional
from collections import defaultdict

class EventTracker:
    """Rastrea eventos a través de capítulos para detectar inconsistencias"""

    def __init__(self):
        self.promises_by_character: Dict[str, List[NarrativeEvent]] = defaultdict(list)
        self.injuries_by_character: Dict[str, List[NarrativeEvent]] = defaultdict(list)
        self.object_inventory: Dict[str, List[str]] = defaultdict(list)  # character → objects

    def track_event(self, event: NarrativeEvent):
        """Registra un evento para rastreo de continuidad"""
        if event.event_type == EventType.PROMISE:
            for char in event.characters_involved:
                self.promises_by_character[char].append(event)

        elif event.event_type == EventType.ACQUISITION:
            char = event.characters_involved[0]
            obj = event.metadata.get("object")
            if obj and obj not in self.object_inventory[char]:
                self.object_inventory[char].append(obj)

        # ... más tipos de rastreo

    def check_inconsistencies(self, event: NarrativeEvent) -> List[str]:
        """Verifica si el evento genera inconsistencias"""
        inconsistencies = []

        if event.event_type == EventType.BROKEN_PROMISE:
            char = event.characters_involved[0]
            if char not in self.promises_by_character:
                inconsistencies.append(
                    f"{char} rompió una promesa, pero no hay registro de promesa previa"
                )

        elif event.event_type == EventType.HEALING:
            char = event.characters_involved[0]
            if char not in self.injuries_by_character:
                inconsistencies.append(
                    f"{char} se curó de una herida que nunca recibió"
                )

        return inconsistencies
```

---

### 3. Integración con `chapter_summary.py`

**Modificar**: `src/narrative_assistant/analysis/chapter_summary.py`

```python
from narrative_assistant.analysis.event_detection import EventDetector, EventType
from narrative_assistant.analysis.event_tracker import EventTracker

class ChapterSummarizer:
    def __init__(self, nlp, llm_manager=None, event_tracker: Optional[EventTracker] = None):
        self.nlp = nlp
        self.llm = llm_manager
        self.event_detector = EventDetector(nlp, llm_manager)
        self.event_tracker = event_tracker or EventTracker()

    def summarize_chapter(self, chapter: Chapter, entities: List[Entity]) -> ChapterSummary:
        # ... código existente ...

        # **NUEVO**: Detectar eventos ampliados
        detected_events = self.event_detector.detect_events(
            chapter.content,
            chapter.chapter_number,
            entities
        )

        # Rastrear eventos para continuidad
        for event in detected_events:
            self.event_tracker.track_event(event)

            # Verificar inconsistencias
            inconsistencies = self.event_tracker.check_inconsistencies(event)
            if inconsistencies:
                # Generar alertas de inconsistencia
                for issue in inconsistencies:
                    self._create_inconsistency_alert(chapter, event, issue)

        # Convertir a formato legacy (key_events)
        key_events = [
            {
                "event_type": e.event_type.value,
                "description": e.description,
                "characters_involved": e.characters_involved,
                "confidence": e.confidence,
            }
            for e in detected_events
        ]

        return ChapterSummary(
            # ... campos existentes ...
            key_events=key_events,
        )
```

---

### 4. Endpoint API para Eventos

**Nuevo endpoint**: `GET /api/projects/{project_id}/events`

```python
# api-server/routers/events.py

from fastapi import APIRouter, Depends
from narrative_assistant.analysis.event_tracker import EventTracker

router = APIRouter()

@router.get("/projects/{project_id}/events")
async def get_project_events(
    project_id: int,
    event_type: Optional[str] = None,
    chapter: Optional[int] = None,
):
    """
    Retorna todos los eventos del proyecto.

    Filtros opcionales:
    - event_type: filtrar por tipo de evento
    - chapter: filtrar por capítulo
    """
    # Cargar chapter_summaries desde DB
    summaries = db.get_chapter_summaries(project_id)

    # Extraer eventos
    all_events = []
    for summary in summaries:
        for event in summary.key_events:
            if event_type and event["event_type"] != event_type:
                continue
            if chapter and event.get("chapter") != chapter:
                continue
            all_events.append(event)

    return {"events": all_events, "total": len(all_events)}


@router.get("/projects/{project_id}/events/inconsistencies")
async def get_event_inconsistencies(project_id: int):
    """
    Retorna inconsistencias detectadas en el rastreo de eventos.

    Ejemplo:
    - Promesa rota sin promesa previa
    - Curación sin herida registrada
    - Uso de objeto no adquirido
    """
    tracker = EventTracker()

    # Cargar eventos y reconstruir tracker
    summaries = db.get_chapter_summaries(project_id)
    for summary in summaries:
        for event_data in summary.key_events:
            event = NarrativeEvent.from_dict(event_data)
            tracker.track_event(event)

    # Verificar inconsistencias
    inconsistencies = []
    for summary in summaries:
        for event_data in summary.key_events:
            event = NarrativeEvent.from_dict(event_data)
            issues = tracker.check_inconsistencies(event)
            if issues:
                inconsistencies.append({
                    "event": event_data,
                    "issues": issues,
                })

    return {"inconsistencies": inconsistencies, "total": len(inconsistencies)}
```

---

## 🧪 Plan de Testing

### Tests Unitarios

**Archivo**: `tests/analysis/test_event_detection.py`

```python
import pytest
from narrative_assistant.analysis.event_detection import EventDetector, EventType

def test_detect_promise():
    detector = EventDetector(nlp)
    text = "Juan le prometió a María que volvería antes del anochecer."
    events = detector.detect_events(text, chapter=1, entities=[])

    assert len(events) == 1
    assert events[0].event_type == EventType.PROMISE
    assert "Juan" in events[0].characters_involved
    assert "volver antes del anochecer" in events[0].metadata["promise_text"]

def test_detect_broken_promise_inconsistency():
    tracker = EventTracker()

    # No hay promesa previa
    broken_event = NarrativeEvent(
        event_type=EventType.BROKEN_PROMISE,
        description="Juan nunca regresó",
        chapter=5,
        characters_involved=["Juan"],
        confidence=0.9,
        metadata={}
    )

    issues = tracker.check_inconsistencies(broken_event)
    assert len(issues) > 0
    assert "no hay registro de promesa previa" in issues[0]
```

---

## 📅 Roadmap de Implementación

### Fase 1: Fundamentos (2-3 horas)
- [ ] Crear `EventType` enum con 18 eventos Tier 1
- [ ] Implementar `EventDetector` base con registro de detectores
- [ ] Implementar `EventTracker` con rastreo de promesas
- [ ] Tests unitarios de `promise` / `broken_promise`

### Fase 2: Detectores NLP (3-4 horas)
- [ ] Implementar detectores de `confession`/`lie`
- [ ] Implementar detectores de `acquisition`/`loss`
- [ ] Implementar detectores de `injury`/`healing`
- [ ] Tests de cada detector

### Fase 3: Detectores Heurísticos (2-3 horas)
- [ ] Implementar `flashback_start`/`flashback_end`
- [ ] Implementar `pov_change`
- [ ] Implementar `time_skip`
- [ ] Tests de regex patterns

### Fase 4: Detectores LLM (2-3 horas)
- [ ] Implementar `betrayal`/`alliance` con Ollama
- [ ] Implementar `epiphany`/`sacrifice`
- [ ] Tests con mocks de LLM

### Fase 5: Integración (1-2 horas)
- [ ] Integrar `EventDetector` en `chapter_summary.py`
- [ ] Crear endpoints API (`/events`, `/events/inconsistencies`)
- [ ] Tests de integración end-to-end

### Fase 6: Frontend (1 hora)
- [ ] Ampliar tipos de eventos en `ChapterInspector.vue` (ya done ✅)
- [ ] Añadir vista de inconsistencias en UI
- [ ] Tests E2E

---

## 📊 Métricas de Éxito

### KPIs Técnicos
- ✅ 18 eventos Tier 1 implementados
- ✅ 8 pares de rastreo funcionando
- ✅ <100ms latencia por evento (NLP)
- ✅ <2s latencia por evento (LLM)
- ✅ >80% precision en detección de promesas

### KPIs de Producto
- ✅ Correctores encuentran ≥3 inconsistencias nuevas por manuscrito
- ✅ Reducción del 30% en tiempo de corrección manual
- ✅ >90% satisfacción con detección de eventos

---

## 🚧 Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Falsos positivos en promesas | Alto | Aumentar umbral de confianza a 0.85, requerir contexto |
| Performance con LLM | Medio | Hacer detección LLM opcional, cache de resultados |
| Complejidad de rastreo | Alto | Empezar con 3 pares simples, ampliar gradualmente |
| Compatibilidad con DB legacy | Medio | Mantener formato `key_events` actual, extender metadata |

---

## 📚 Referencias

- [Taxonomía completa de eventos](docs/EVENTS_TAXONOMY_FULL.md) (output del comité de expertos)
- [Propp's Morphology](https://en.wikipedia.org/wiki/Vladimir_Propp)
- [Campbell's Hero's Journey](https://en.wikipedia.org/wiki/Hero%27s_journey)
- [Save the Cat Beat Sheet](https://savethecat.com/beat-sheet)

---

**Próximos pasos**:
1. Review de este plan con el usuario
2. Aprobación de scope (Tier 1 completo vs Tier 1 parcial)
3. Setup de branch feature (`feature/event-taxonomy`)
4. Implementación Fase 1-6 secuencial
