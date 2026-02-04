# Panel de Expertos: Arquitectura Combinada para Atribución de Atributos Físicos

**Fecha**: 3 de febrero de 2026  
**Objetivo**: Diseñar una arquitectura que combine extractores con votación ponderada inteligente

---

## 🎯 DIAGNÓSTICO DEL PROBLEMA ACTUAL

Analizando el código existente en [aggregator.py](src/narrative_assistant/nlp/extraction/aggregator.py) y [attributes.py](src/narrative_assistant/nlp/attributes.py):

### Problemas Identificados:
1. **Votación por valor, no por validez**: El sistema agrupa por `(entidad, tipo, valor)` y vota quién tiene razón, pero no valida si la asignación entidad→atributo es correcta
2. **Ejecución paralela sin cascada**: Todos los extractores corren simultáneamente, sin posibilidad de que uno corrija a otro
3. **Falsos positivos de proximidad**: PatternExtractor puede asignar "ojos azules" a la entidad incorrecta por cercanía textual
4. **LLM como validador poco usado**: Solo se activa por complejidad, no para resolver conflictos

---

## 👥 PANEL DE EXPERTOS

### 1. Dra. Elena Martínez (Lingüista Computacional)

> **Visión**: El problema fundamental es que estamos tratando la extracción de atributos como un problema de NER cuando es un problema de **resolución de correferencia**. 
>
> **Propuesta**: Arquitectura en 3 fases:
> 1. **Fase de Detección**: Identificar todos los atributos en el texto (sin asignar)
> 2. **Fase de Asignación**: Determinar a qué entidad pertenece cada atributo
> 3. **Fase de Validación**: Verificar coherencia semántica
>
> **Métrica clave**: La evidencia sintáctica (quien es sujeto del verbo) debe ser **suficiente y necesaria**, no meramente contributiva.

---

### 2. Prof. Carlos Ruiz (Arquitecto de Sistemas)

> **Visión**: El código actual tiene buena modularidad pero mala orquestación. La clave es una **arquitectura de capas con cortocircuito**.
>
> **Propuesta**: Pipeline con Early Exit:
> ```
> Capa 1 (Rápida) → Si confianza ≥ 0.85, DONE
>                 → Si 0.60-0.85, agregar a "dudosos"
>                 → Si < 0.60, descartar
> Capa 2 (Semántica) → Solo procesa "dudosos"
> Capa 3 (LLM) → Solo conflictos irresolubles
> ```
>
> **Ventaja**: 80% de casos se resuelven en Capa 1, reduciendo costo computacional.

---

### 3. Dra. Ana López (Especialista en Parsing Sintáctico)

> **Visión**: DependencyExtractor es subutilizado. El análisis de dependencias de spaCy nos da **certeza estructural** que debería tener veto sobre otros métodos.
>
> **Propuesta**: Prioridad sintáctica absoluta:
> - Si dependency encuentra sujeto explícito → confianza 0.95, no rebatible
> - Si hay ambigüedad de sujeto → permitir votación
> - Regex/Embeddings solo como **detectores**, no como **asignadores**
>
> **Regla de oro**: "Quien puede nsubj/dobj a la entidad, gana"

---

### 4. Ing. Miguel Torres (Optimización de Rendimiento)

> **Visión**: El problema no es la arquitectura, es el **costo de coordinación**. Con 4 extractores en paralelo, estamos haciendo 4x el trabajo para casos que Regex resuelve en 1ms.
>
> **Propuesta**: Extracción progresiva con cache:
> 1. Regex primero (siempre, 1-5ms)
> 2. Dependency solo si Regex no encuentra o baja confianza (50-100ms)
> 3. Embeddings solo para validación de atributos "raros" (100-200ms)
> 4. LLM solo para conflictos o textos muy complejos (500-5000ms)
>
> **Benchmark objetivo**: <100ms para 90% de los casos

---

### 5. Dra. Sofía Vega (ML/LLM)

> **Visión**: El LLM no debe ser el último recurso sino el **árbitro inteligente**. Pero invocarlo para todo es costoso e innecesario.
>
> **Propuesta**: LLM como juez bajo demanda:
> - Detectar conflictos ANTES de resolver
> - Solo enviar al LLM: "¿A quién pertenecen 'ojos azules': María o Juan?"
> - Prompt específico, no extracción completa
>
> **Clave**: El LLM resuelve la **ambigüedad**, no hace el trabajo de extracción.

---

## 🔥 DEBATE CRÍTICO

### Punto de Conflicto 1: ¿Regex debería asignar entidades?

**Dra. López**: "Regex no tiene información estructural. No sabe quién es el sujeto."

**Prof. Ruiz**: "Pero para 'María tenía los ojos azules', el regex funciona perfecto."

**Dra. Martínez**: "El problema es 'Los ojos azules de María brillaban'. Regex encuentra 'ojos azules' pero no puede determinar si es descriptivo o metafórico."

**CONSENSO**: Regex **detecta** atributos pero no **asigna**. La asignación requiere evidencia sintáctica.

---

### Punto de Conflicto 2: ¿Cuándo invocar LLM?

**Ing. Torres**: "LLM es 100x más lento. No podemos usarlo para todo."

**Dra. Vega**: "Pero es el único que entiende 'Heredó los ojos de su madre, verdes como esmeraldas'."

**Dra. López**: "Dependency puede manejar eso si detectamos 'heredó' → 'ojos' → 'madre'."

**CONSENSO**: LLM solo para:
1. Conflictos entre extractores (valores diferentes para misma entidad)
2. Textos con complejidad > 0.7
3. Cuando no hay evidencia sintáctica clara

---

### Punto de Conflicto 3: ¿Cómo manejar sujeto tácito?

**Ejemplo**: "María entró en la habitación. Era alta y tenía el pelo largo."

**Dra. Martínez**: "Esto requiere tracking de antecedente por oración."

**Dra. López**: "DependencyExtractor ya lo hace parcialmente con `sentence_subjects`."

**CONSENSO**: Mejorar tracking de sujeto, pero marcando confianza reducida (0.75 vs 0.90).

---

## 🏆 ARQUITECTURA FINAL CONSENSUADA

### Nombre: **Cascading Extraction with Syntactic Priority (CESP)**

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                         TEXTO ENTRADA                            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1: DETECCIÓN RÁPIDA (Paralelo)                            │
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ RegexDetector│  │DependencyExtract.│  │EmbeddingsDetect.│   │
│  │(solo detecta)│  │(detecta+asigna)  │  │(solo detecta)   │   │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬─────────┘   │
│         │                   │                     │             │
│         ▼                   ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              POOL DE CANDIDATOS                          │  │
│  │  {(atributo, valor, posición, método, conf), ...}       │  │
│  └─────────────────────────┬────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2: ASIGNACIÓN CON PRIORIDAD SINTÁCTICA                   │
│                                                                  │
│  Para cada candidato:                                           │
│  1. ¿Dependency tiene asignación?                               │
│     → SÍ con sujeto explícito: confianza = 0.92, ACEPTAR       │
│     → SÍ con sujeto tácito: confianza = 0.78, MARCAR DUDOSO   │
│     → NO: buscar por proximidad + reglas                       │
│                                                                  │
│  2. Agrupar por (entidad_candidata, atributo_tipo)             │
│  3. Detectar conflictos (misma entidad, valores diferentes)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 3: RESOLUCIÓN DE CONFLICTOS                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Clasificar candidatos:                                   │   │
│  │ • CONFIRMADOS: dependency explícito, sin conflicto       │   │
│  │ • DUDOSOS: dependency tácito O solo regex/embeddings     │   │
│  │ • CONFLICTO: múltiples valores para misma entidad+tipo   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  CONFIRMADOS → Salida directa                                   │
│  DUDOSOS → Votación ponderada (sin LLM)                         │
│  CONFLICTO → Si LLM disponible: consulta específica            │
│            → Si no: método de mayor precisión gana              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 4: DEDUPLICACIÓN INTELIGENTE                              │
│                                                                  │
│  • Agrupar por (entidad, tipo_atributo)                         │
│  • Priorizar: dependency > regex > embeddings                   │
│  • Conservar source_text del más preciso                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 PSEUDOCÓDIGO DETALLADO

### Estructuras de Datos

```python
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Literal


class AssignmentConfidence(Enum):
    """Niveles de confianza en la asignación entidad→atributo."""
    SYNTACTIC_EXPLICIT = auto()   # nsubj directo, 0.92
    SYNTACTIC_TACIT = auto()      # sujeto heredado, 0.78
    PROXIMITY_STRONG = auto()     # <10 tokens, misma oración, 0.70
    PROXIMITY_WEAK = auto()       # misma oración pero lejos, 0.55
    SEMANTIC_MATCH = auto()       # embeddings coincide, 0.65
    LLM_VERIFIED = auto()         # LLM confirmó, 0.95


@dataclass
class AttributeCandidate:
    """Candidato a atributo antes de asignación final."""
    # Qué se detectó
    attribute_type: str           # "eye_color", "height", etc.
    value: str                    # "azules", "alto"
    source_text: str              # Oración original
    char_start: int
    char_end: int
    
    # Quién lo detectó
    detection_method: str         # "regex", "dependency", "embeddings"
    detection_confidence: float   # Confianza del detector (0.0-1.0)
    
    # Asignación (puede ser None si solo detectado)
    assigned_entity: Optional[str] = None
    assignment_type: Optional[AssignmentConfidence] = None
    assignment_evidence: Optional[str] = None  # "nsubj→tener→ojos"
    
    # Metadatos
    is_negated: bool = False
    is_metaphor: bool = False
    chapter: Optional[int] = None


@dataclass
class AttributeConflict:
    """Conflicto entre candidatos."""
    entity: str
    attribute_type: str
    candidates: list[AttributeCandidate]
    conflict_type: Literal["value_mismatch", "entity_ambiguous", "negation"]


@dataclass  
class ResolvedAttribute:
    """Atributo final resuelto."""
    entity_name: str
    attribute_type: str
    value: str
    final_confidence: float
    resolution_method: str        # "syntactic", "voting", "llm"
    sources: list[str]            # Métodos que contribuyeron
    source_text: str
    chapter: Optional[int] = None
    is_negated: bool = False
```

### Clase Principal: CascadingExtractor

```python
class CascadingExtractor:
    """
    Extractor con arquitectura CESP (Cascading Extraction with Syntactic Priority).
    
    Combina múltiples extractores con prioridad sintáctica y LLM como árbitro.
    """
    
    # Configuración de confianza
    CONFIG = {
        # Umbrales de confianza por tipo de asignación
        "confidence": {
            "syntactic_explicit": 0.92,
            "syntactic_tacit": 0.78,
            "proximity_strong": 0.70,
            "proximity_weak": 0.55,
            "semantic_match": 0.65,
            "llm_verified": 0.95,
        },
        # Umbrales de decisión
        "thresholds": {
            "accept_without_voting": 0.85,  # Si conf >= esto, aceptar directo
            "discard_candidate": 0.40,      # Si conf < esto, descartar
            "require_llm_for_conflict": 0.75,  # Diferencia mínima para no usar LLM
        },
        # Pesos para votación (cuando no hay sintaxis clara)
        "voting_weights": {
            "dependency": 0.40,
            "regex": 0.25,
            "embeddings": 0.20,
            "llm": 0.45,  # Si LLM participa, tiene peso alto
        },
        # Precisión esperada por método (para resolver conflictos sin LLM)
        "method_precision": {
            "dependency": 0.88,
            "regex": 0.92,
            "embeddings": 0.68,
            "llm": 0.90,
        },
        # Límites de rendimiento
        "performance": {
            "max_candidates_for_llm": 10,    # No enviar más de N conflictos
            "llm_timeout_seconds": 30,
            "complexity_threshold_llm": 0.70,
        }
    }
    
    def __init__(
        self,
        use_llm: bool = True,
        llm_client: Optional[Any] = None,
    ):
        self.use_llm = use_llm
        self.llm_client = llm_client
        
        # Inicializar extractores individuales
        self._dependency_extractor = None
        self._regex_patterns = None
        self._embeddings_model = None
        self._nlp = None
    
    def extract(
        self,
        text: str,
        entity_names: list[str],
        entity_mentions: Optional[list[tuple[str, int, int]]] = None,
        chapter: Optional[int] = None,
    ) -> list[ResolvedAttribute]:
        """
        Extrae atributos usando arquitectura CESP.
        
        Args:
            text: Texto a analizar
            entity_names: Nombres de entidades conocidas
            entity_mentions: [(nombre, start, end), ...] posiciones
            chapter: Número de capítulo
            
        Returns:
            Lista de atributos resueltos con asignación a entidades
        """
        if not text or not entity_names:
            return []
        
        # Pre-procesar
        doc = self._get_spacy_doc(text)
        entity_set = {name.lower() for name in entity_names}
        
        # FASE 1: Detección
        candidates = self._phase1_detect(doc, entity_set, entity_mentions, chapter)
        
        if not candidates:
            return []
        
        # FASE 2: Asignación con prioridad sintáctica
        assigned = self._phase2_assign(candidates, doc, entity_set)
        
        # FASE 3: Resolver conflictos
        resolved = self._phase3_resolve(assigned, text, entity_names)
        
        # FASE 4: Deduplicar
        final = self._phase4_deduplicate(resolved)
        
        return final
    
    # =========================================================================
    # FASE 1: DETECCIÓN
    # =========================================================================
    
    def _phase1_detect(
        self,
        doc,
        entity_set: set[str],
        entity_mentions: Optional[list],
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Fase 1: Detectar todos los atributos posibles.
        
        Ejecuta extractores en paralelo pero SIN asignar entidades
        (excepto DependencyExtractor que sí puede asignar).
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        candidates = []
        
        # Dependency hace detección Y asignación
        dep_candidates = self._detect_with_dependency(doc, entity_set, chapter)
        candidates.extend(dep_candidates)
        
        # Regex y Embeddings solo detectan (asignación en Fase 2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(
                    self._detect_with_regex, doc.text, chapter
                ): "regex",
                executor.submit(
                    self._detect_with_embeddings, doc, chapter
                ): "embeddings",
            }
            
            for future in as_completed(futures):
                method = futures[future]
                try:
                    method_candidates = future.result()
                    candidates.extend(method_candidates)
                except Exception as e:
                    logger.warning(f"Detector {method} falló: {e}")
        
        return candidates
    
    def _detect_with_dependency(
        self,
        doc,
        entity_set: set[str],
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Detecta Y asigna usando análisis de dependencias.
        
        Este es el único método que puede asignar con alta confianza.
        """
        candidates = []
        
        # Tracking de sujeto por oración (para sujeto tácito)
        sentence_subjects = self._build_sentence_subject_map(doc, entity_set)
        
        for sent in doc.sents:
            for token in sent:
                # Patrón 1: Verbo copulativo (ser/estar + adjetivo)
                if token.lemma_ in {"ser", "estar"} and token.pos_ in {"AUX", "VERB"}:
                    attrs = self._extract_copulative_pattern(
                        token, sent, entity_set, sentence_subjects, chapter
                    )
                    candidates.extend(attrs)
                
                # Patrón 2: Verbo posesivo (tener + sustantivo + adjetivo)
                if token.lemma_ in {"tener", "llevar", "lucir"}:
                    attrs = self._extract_possessive_pattern(
                        token, sent, entity_set, sentence_subjects, chapter
                    )
                    candidates.extend(attrs)
                
                # Patrón 3: Preposicional (con ojos azules)
                if token.text.lower() == "con" and token.dep_ == "case":
                    attrs = self._extract_prepositional_pattern(
                        token, sent, entity_set, sentence_subjects, chapter
                    )
                    candidates.extend(attrs)
        
        return candidates
    
    def _extract_copulative_pattern(
        self,
        verb_token,
        sent,
        entity_set: set[str],
        sentence_subjects: dict,
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Extrae de estructuras copulativas: "María era alta"
        
        Retorna candidatos con asignación si encuentra sujeto.
        """
        candidates = []
        
        # Buscar sujeto del verbo
        subject_token = None
        for child in verb_token.children:
            if child.dep_ in {"nsubj", "nsubj:pass"}:
                subject_token = child
                break
        
        # Determinar entidad y tipo de asignación
        if subject_token:
            entity_name = self._resolve_entity(subject_token, entity_set)
            if entity_name:
                assignment_type = AssignmentConfidence.SYNTACTIC_EXPLICIT
            else:
                # Sujeto encontrado pero no es entidad conocida
                return candidates
        else:
            # Sujeto tácito: usar último sujeto de contexto
            entity_name = sentence_subjects.get(sent.start)
            if entity_name:
                assignment_type = AssignmentConfidence.SYNTACTIC_TACIT
            else:
                # No hay sujeto ni contexto
                return candidates
        
        # Buscar atributo predicativo
        for child in verb_token.children:
            if child.dep_ in {"acomp", "attr", "xcomp"} or \
               (child.dep_ == "ROOT" and child.pos_ == "ADJ"):
                
                attr_value = child.text.lower()
                attr_type = self._classify_attribute(attr_value, child)
                
                if attr_type:
                    conf = self.CONFIG["confidence"][
                        "syntactic_explicit" if assignment_type == AssignmentConfidence.SYNTACTIC_EXPLICIT 
                        else "syntactic_tacit"
                    ]
                    
                    candidates.append(AttributeCandidate(
                        attribute_type=attr_type,
                        value=attr_value,
                        source_text=sent.text,
                        char_start=child.idx,
                        char_end=child.idx + len(child.text),
                        detection_method="dependency",
                        detection_confidence=conf,
                        assigned_entity=entity_name,
                        assignment_type=assignment_type,
                        assignment_evidence=f"nsubj→{verb_token.lemma_}→{child.dep_}",
                        chapter=chapter,
                    ))
        
        return candidates
    
    def _extract_possessive_pattern(
        self,
        verb_token,
        sent,
        entity_set: set[str],
        sentence_subjects: dict,
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Extrae de estructuras posesivas: "María tenía los ojos azules"
        """
        candidates = []
        
        # Buscar sujeto
        subject_token = None
        for child in verb_token.children:
            if child.dep_ in {"nsubj", "nsubj:pass"}:
                subject_token = child
                break
        
        if subject_token:
            entity_name = self._resolve_entity(subject_token, entity_set)
            if not entity_name:
                return candidates
            assignment_type = AssignmentConfidence.SYNTACTIC_EXPLICIT
        else:
            entity_name = sentence_subjects.get(sent.start)
            if not entity_name:
                return candidates
            assignment_type = AssignmentConfidence.SYNTACTIC_TACIT
        
        # Buscar objeto directo (los ojos)
        for child in verb_token.children:
            if child.dep_ in {"dobj", "obj"}:
                body_part = child.text.lower()
                
                # Buscar modificadores del objeto (azules)
                for modifier in child.children:
                    if modifier.pos_ == "ADJ":
                        attr_type = self._classify_body_part_attribute(
                            body_part, modifier.text.lower()
                        )
                        
                        if attr_type:
                            conf = self.CONFIG["confidence"][
                                "syntactic_explicit" if assignment_type == AssignmentConfidence.SYNTACTIC_EXPLICIT 
                                else "syntactic_tacit"
                            ]
                            
                            candidates.append(AttributeCandidate(
                                attribute_type=attr_type,
                                value=modifier.text.lower(),
                                source_text=sent.text,
                                char_start=modifier.idx,
                                char_end=modifier.idx + len(modifier.text),
                                detection_method="dependency",
                                detection_confidence=conf,
                                assigned_entity=entity_name,
                                assignment_type=assignment_type,
                                assignment_evidence=f"nsubj→{verb_token.lemma_}→obj({body_part})→amod",
                                chapter=chapter,
                            ))
        
        return candidates
    
    def _detect_with_regex(
        self,
        text: str,
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Detecta atributos con regex. NO asigna entidad.
        
        Genera candidatos con assigned_entity=None para que
        Fase 2 los asigne por proximidad.
        """
        candidates = []
        
        # Patrones de alta precisión (ejemplos)
        patterns = [
            # (pattern, attr_type, value_group, confidence)
            (r"ojos\s+(\w+)", "eye_color", 1, 0.85),
            (r"pelo\s+(\w+)", "hair_color", 1, 0.80),
            (r"cabello\s+(\w+)", "hair_color", 1, 0.80),
            (r"era\s+(alt[oa]|baj[oa])", "height", 1, 0.88),
            (r"(?:muy\s+)?(delgad[oa]|gordo|fornid[oa])", "build", 1, 0.82),
        ]
        
        for pattern, attr_type, group, conf in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(group).lower()
                
                # Verificar que no sea metáfora
                context_start = max(0, match.start() - 30)
                context = text[context_start:match.end() + 20]
                if self._is_metaphor(context):
                    continue
                
                candidates.append(AttributeCandidate(
                    attribute_type=attr_type,
                    value=value,
                    source_text=text[match.start():match.end()],
                    char_start=match.start(),
                    char_end=match.end(),
                    detection_method="regex",
                    detection_confidence=conf,
                    # NO asigna entidad - se hace en Fase 2
                    assigned_entity=None,
                    assignment_type=None,
                    chapter=chapter,
                ))
        
        return candidates
    
    def _detect_with_embeddings(
        self,
        doc,
        chapter: Optional[int],
    ) -> list[AttributeCandidate]:
        """
        Detecta atributos usando embeddings semánticos.
        
        Útil para detectar atributos expresados de forma no convencional.
        NO asigna entidad.
        """
        candidates = []
        
        if not self._embeddings_model:
            return candidates
        
        # Prototipos de atributos para comparar
        prototypes = {
            "eye_color": ["ojos azules", "ojos verdes", "ojos marrones", "ojos negros"],
            "hair_color": ["pelo rubio", "cabello negro", "pelo castaño"],
            "height": ["persona alta", "persona baja", "de gran estatura"],
            "build": ["complexión delgada", "físico robusto", "cuerpo atlético"],
        }
        
        # Analizar cada oración
        for sent in doc.sents:
            sent_embedding = self._embeddings_model.encode(sent.text)
            
            for attr_type, proto_list in prototypes.items():
                proto_embeddings = self._embeddings_model.encode(proto_list)
                similarities = cosine_similarity([sent_embedding], proto_embeddings)[0]
                
                max_sim = max(similarities)
                if max_sim > 0.75:  # Umbral de similitud
                    # Extraer el valor probable
                    best_proto = proto_list[similarities.argmax()]
                    value = self._extract_value_from_prototype(sent.text, best_proto)
                    
                    if value:
                        candidates.append(AttributeCandidate(
                            attribute_type=attr_type,
                            value=value,
                            source_text=sent.text,
                            char_start=sent.start_char,
                            char_end=sent.end_char,
                            detection_method="embeddings",
                            detection_confidence=0.65 + (max_sim - 0.75) * 0.5,
                            assigned_entity=None,  # No asigna
                            assignment_type=None,
                            chapter=chapter,
                        ))
        
        return candidates
    
    # =========================================================================
    # FASE 2: ASIGNACIÓN
    # =========================================================================
    
    def _phase2_assign(
        self,
        candidates: list[AttributeCandidate],
        doc,
        entity_set: set[str],
    ) -> list[AttributeCandidate]:
        """
        Fase 2: Asignar entidades a candidatos sin asignación.
        
        Para candidatos de Dependency: ya tienen asignación → skip
        Para candidatos de Regex/Embeddings: asignar por proximidad
        """
        assigned = []
        
        # Construir índice de menciones de entidades en el texto
        entity_positions = self._build_entity_position_index(doc, entity_set)
        
        for candidate in candidates:
            if candidate.assigned_entity:
                # Ya tiene asignación (de Dependency)
                assigned.append(candidate)
                continue
            
            # Necesita asignación por proximidad
            nearest = self._find_nearest_entity(
                candidate.char_start,
                candidate.char_end,
                entity_positions,
                doc,
            )
            
            if nearest:
                entity_name, distance, same_sentence = nearest
                
                # Determinar tipo de asignación por proximidad
                if same_sentence and distance < 50:  # <50 caracteres
                    assignment_type = AssignmentConfidence.PROXIMITY_STRONG
                    conf = self.CONFIG["confidence"]["proximity_strong"]
                elif same_sentence:
                    assignment_type = AssignmentConfidence.PROXIMITY_WEAK
                    conf = self.CONFIG["confidence"]["proximity_weak"]
                else:
                    # Diferente oración: muy baja confianza
                    conf = 0.45
                    assignment_type = AssignmentConfidence.PROXIMITY_WEAK
                
                candidate.assigned_entity = entity_name
                candidate.assignment_type = assignment_type
                candidate.detection_confidence = min(
                    candidate.detection_confidence,
                    conf
                )
                candidate.assignment_evidence = f"proximity:{distance}chars"
            
            assigned.append(candidate)
        
        # Filtrar candidatos sin asignación
        return [c for c in assigned if c.assigned_entity]
    
    def _find_nearest_entity(
        self,
        attr_start: int,
        attr_end: int,
        entity_positions: list[tuple[str, int, int]],
        doc,
    ) -> Optional[tuple[str, int, bool]]:
        """
        Encuentra la entidad más cercana al atributo.
        
        Returns:
            (entity_name, distance, same_sentence) o None
        """
        if not entity_positions:
            return None
        
        attr_mid = (attr_start + attr_end) // 2
        
        # Encontrar la oración del atributo
        attr_sent = None
        for sent in doc.sents:
            if sent.start_char <= attr_start < sent.end_char:
                attr_sent = sent
                break
        
        best = None
        best_distance = float('inf')
        
        for entity_name, ent_start, ent_end in entity_positions:
            # Distancia al centro del atributo
            if ent_end < attr_start:
                distance = attr_start - ent_end
            elif ent_start > attr_end:
                distance = ent_start - attr_end
            else:
                distance = 0  # Se solapan
            
            # ¿Misma oración?
            same_sentence = False
            if attr_sent:
                same_sentence = (
                    attr_sent.start_char <= ent_start < attr_sent.end_char
                )
            
            # Priorizar misma oración, luego distancia
            priority = (not same_sentence, distance)
            current_best = (best[2] if best else True, best_distance)
            
            if priority < current_best:
                best = (entity_name, distance, same_sentence)
                best_distance = distance
        
        return best
    
    # =========================================================================
    # FASE 3: RESOLUCIÓN DE CONFLICTOS
    # =========================================================================
    
    def _phase3_resolve(
        self,
        candidates: list[AttributeCandidate],
        text: str,
        entity_names: list[str],
    ) -> list[ResolvedAttribute]:
        """
        Fase 3: Resolver conflictos entre candidatos.
        
        Estrategia:
        1. Agrupar por (entidad, tipo_atributo)
        2. Clasificar: confirmados, dudosos, conflictos
        3. Resolver cada categoría apropiadamente
        """
        # Agrupar por (entidad, tipo)
        groups: dict[tuple[str, str], list[AttributeCandidate]] = defaultdict(list)
        for c in candidates:
            key = (c.assigned_entity.lower(), c.attribute_type)
            groups[key].append(c)
        
        resolved = []
        conflicts_for_llm = []
        
        for (entity, attr_type), group in groups.items():
            # Clasificar el grupo
            classification = self._classify_group(group)
            
            if classification == "confirmed":
                # Un solo valor, con evidencia sintáctica fuerte
                resolved.append(self._resolve_confirmed(group, entity, attr_type))
            
            elif classification == "unanimous":
                # Múltiples métodos, mismo valor
                resolved.append(self._resolve_unanimous(group, entity, attr_type))
            
            elif classification == "majority":
                # Mayoría concuerda, sin conflicto real
                resolved.append(self._resolve_majority(group, entity, attr_type))
            
            elif classification == "conflict":
                # Valores diferentes → necesita resolución
                if self.use_llm and self.llm_client:
                    conflicts_for_llm.append(
                        AttributeConflict(
                            entity=entity,
                            attribute_type=attr_type,
                            candidates=group,
                            conflict_type="value_mismatch",
                        )
                    )
                else:
                    # Sin LLM: resolver por precisión del método
                    resolved.append(
                        self._resolve_by_precision(group, entity, attr_type)
                    )
        
        # Resolver conflictos con LLM si hay
        if conflicts_for_llm:
            llm_resolved = self._resolve_with_llm(conflicts_for_llm, text, entity_names)
            resolved.extend(llm_resolved)
        
        return resolved
    
    def _classify_group(
        self,
        group: list[AttributeCandidate],
    ) -> str:
        """
        Clasifica un grupo de candidatos.
        
        Returns:
            "confirmed": Evidencia sintáctica clara, sin conflicto
            "unanimous": Múltiples fuentes, mismo valor
            "majority": Mayoría concuerda
            "conflict": Valores diferentes, requiere resolución
        """
        if len(group) == 1:
            c = group[0]
            if c.assignment_type in {
                AssignmentConfidence.SYNTACTIC_EXPLICIT,
                AssignmentConfidence.LLM_VERIFIED,
            }:
                return "confirmed"
            return "majority"  # Un solo candidato sin conflicto
        
        # Múltiples candidatos: verificar valores
        values = {c.value.lower().strip() for c in group}
        
        if len(values) == 1:
            # Todos coinciden en el valor
            has_syntactic = any(
                c.assignment_type == AssignmentConfidence.SYNTACTIC_EXPLICIT
                for c in group
            )
            return "confirmed" if has_syntactic else "unanimous"
        
        # Valores diferentes
        # Contar votos por valor
        value_counts = defaultdict(int)
        for c in group:
            value_counts[c.value.lower().strip()] += 1
        
        max_count = max(value_counts.values())
        if max_count > len(group) / 2:
            return "majority"
        
        return "conflict"
    
    def _resolve_confirmed(
        self,
        group: list[AttributeCandidate],
        entity: str,
        attr_type: str,
    ) -> ResolvedAttribute:
        """Resuelve grupo confirmado (sintaxis clara)."""
        # Elegir el de mayor confianza
        best = max(group, key=lambda c: c.detection_confidence)
        
        return ResolvedAttribute(
            entity_name=best.assigned_entity,
            attribute_type=attr_type,
            value=best.value,
            final_confidence=best.detection_confidence,
            resolution_method="syntactic",
            sources=[c.detection_method for c in group],
            source_text=best.source_text,
            chapter=best.chapter,
            is_negated=best.is_negated,
        )
    
    def _resolve_unanimous(
        self,
        group: list[AttributeCandidate],
        entity: str,
        attr_type: str,
    ) -> ResolvedAttribute:
        """Resuelve grupo unánime (todos coinciden)."""
        # Calcular confianza combinada con boost
        weights = self.CONFIG["voting_weights"]
        total_weight = 0
        weighted_conf = 0
        
        for c in group:
            w = weights.get(c.detection_method, 0.2)
            weighted_conf += c.detection_confidence * w
            total_weight += w
        
        base_conf = weighted_conf / total_weight if total_weight > 0 else 0.5
        
        # Boost por unanimidad (+10%)
        final_conf = min(0.98, base_conf * 1.10)
        
        best = max(group, key=lambda c: c.detection_confidence)
        
        return ResolvedAttribute(
            entity_name=best.assigned_entity,
            attribute_type=attr_type,
            value=best.value,
            final_confidence=final_conf,
            resolution_method="voting_unanimous",
            sources=list({c.detection_method for c in group}),
            source_text=best.source_text,
            chapter=best.chapter,
            is_negated=best.is_negated,
        )
    
    def _resolve_majority(
        self,
        group: list[AttributeCandidate],
        entity: str,
        attr_type: str,
    ) -> ResolvedAttribute:
        """Resuelve grupo por mayoría."""
        # Contar votos ponderados por valor
        value_scores: dict[str, float] = defaultdict(float)
        value_candidates: dict[str, list[AttributeCandidate]] = defaultdict(list)
        weights = self.CONFIG["voting_weights"]
        
        for c in group:
            v = c.value.lower().strip()
            w = weights.get(c.detection_method, 0.2)
            value_scores[v] += c.detection_confidence * w
            value_candidates[v].append(c)
        
        # Elegir valor ganador
        winner_value = max(value_scores.keys(), key=lambda v: value_scores[v])
        winner_candidates = value_candidates[winner_value]
        
        # Calcular confianza
        total_score = sum(value_scores.values())
        winner_score = value_scores[winner_value]
        
        # Confianza = proporción del score ganador, con penalización por conflicto
        raw_conf = winner_score / total_score if total_score > 0 else 0.5
        final_conf = raw_conf * 0.9  # -10% por no ser unánime
        
        best = max(winner_candidates, key=lambda c: c.detection_confidence)
        
        return ResolvedAttribute(
            entity_name=best.assigned_entity,
            attribute_type=attr_type,
            value=winner_value,
            final_confidence=final_conf,
            resolution_method="voting_majority",
            sources=list({c.detection_method for c in winner_candidates}),
            source_text=best.source_text,
            chapter=best.chapter,
            is_negated=best.is_negated,
        )
    
    def _resolve_by_precision(
        self,
        group: list[AttributeCandidate],
        entity: str,
        attr_type: str,
    ) -> ResolvedAttribute:
        """
        Resuelve conflicto sin LLM usando precisión del método.
        
        El método con mayor precisión histórica gana.
        """
        precisions = self.CONFIG["method_precision"]
        
        # Elegir candidato del método más preciso
        best = max(
            group,
            key=lambda c: (
                precisions.get(c.detection_method, 0.5),
                c.detection_confidence,
            )
        )
        
        # Penalizar por ser decisión sin consenso
        final_conf = best.detection_confidence * 0.85
        
        return ResolvedAttribute(
            entity_name=best.assigned_entity,
            attribute_type=attr_type,
            value=best.value,
            final_confidence=final_conf,
            resolution_method="precision_fallback",
            sources=[best.detection_method],
            source_text=best.source_text,
            chapter=best.chapter,
            is_negated=best.is_negated,
        )
    
    def _resolve_with_llm(
        self,
        conflicts: list[AttributeConflict],
        text: str,
        entity_names: list[str],
    ) -> list[ResolvedAttribute]:
        """
        Usa LLM para resolver conflictos específicos.
        
        Prompt optimizado: solo pregunta sobre el conflicto, no extrae.
        """
        if not conflicts or not self.llm_client:
            return []
        
        resolved = []
        
        # Limitar cantidad de conflictos
        max_conflicts = self.CONFIG["performance"]["max_candidates_for_llm"]
        if len(conflicts) > max_conflicts:
            # Priorizar por diferencia de confianza (más difíciles primero)
            conflicts = sorted(
                conflicts,
                key=lambda c: max(x.detection_confidence for x in c.candidates) -
                             min(x.detection_confidence for x in c.candidates)
            )[:max_conflicts]
        
        # Construir prompt
        prompt = self._build_conflict_resolution_prompt(conflicts, text)
        
        try:
            response = self.llm_client.complete(
                prompt,
                system="Eres un experto en análisis de texto narrativo en español. "
                       "Responde SOLO con JSON válido.",
                temperature=0.0,
                timeout=self.CONFIG["performance"]["llm_timeout_seconds"],
            )
            
            decisions = self._parse_llm_conflict_response(response)
            
            for conflict in conflicts:
                key = (conflict.entity, conflict.attribute_type)
                decision = decisions.get(key)
                
                if decision:
                    # LLM eligió un valor
                    matching = [
                        c for c in conflict.candidates
                        if c.value.lower().strip() == decision["value"].lower()
                    ]
                    
                    if matching:
                        best = matching[0]
                        resolved.append(ResolvedAttribute(
                            entity_name=conflict.entity,
                            attribute_type=conflict.attribute_type,
                            value=decision["value"],
                            final_confidence=self.CONFIG["confidence"]["llm_verified"],
                            resolution_method="llm_arbitration",
                            sources=["llm"] + [c.detection_method for c in matching],
                            source_text=best.source_text,
                            chapter=best.chapter,
                            is_negated=best.is_negated,
                        ))
                    else:
                        # LLM propuso valor nuevo (raro)
                        resolved.append(ResolvedAttribute(
                            entity_name=conflict.entity,
                            attribute_type=conflict.attribute_type,
                            value=decision["value"],
                            final_confidence=0.88,
                            resolution_method="llm_arbitration",
                            sources=["llm"],
                            source_text=conflict.candidates[0].source_text,
                            chapter=conflict.candidates[0].chapter,
                        ))
                else:
                    # LLM no resolvió → fallback a precisión
                    resolved.append(
                        self._resolve_by_precision(
                            conflict.candidates,
                            conflict.entity,
                            conflict.attribute_type,
                        )
                    )
        
        except Exception as e:
            logger.warning(f"LLM conflict resolution failed: {e}")
            # Fallback: resolver todos por precisión
            for conflict in conflicts:
                resolved.append(
                    self._resolve_by_precision(
                        conflict.candidates,
                        conflict.entity,
                        conflict.attribute_type,
                    )
                )
        
        return resolved
    
    def _build_conflict_resolution_prompt(
        self,
        conflicts: list[AttributeConflict],
        text: str,
    ) -> str:
        """
        Construye prompt específico para resolver conflictos.
        
        El prompt NO pide extracción, solo decisión sobre conflictos.
        """
        # Limitar texto a sección relevante
        max_text = 2000
        text_sample = text[:max_text] if len(text) > max_text else text
        
        conflict_descriptions = []
        for i, c in enumerate(conflicts, 1):
            values = [cand.value for cand in c.candidates]
            conflict_descriptions.append(
                f"{i}. Entidad: {c.entity}\n"
                f"   Atributo: {c.attribute_type}\n"
                f"   Valores posibles: {values}\n"
                f"   Evidencias:\n" +
                "\n".join(f"   - '{cand.source_text}' ({cand.detection_method})"
                         for cand in c.candidates)
            )
        
        prompt = f"""TEXTO:
{text_sample}

CONFLICTOS A RESOLVER:
{chr(10).join(conflict_descriptions)}

Para cada conflicto, determina qué valor es correcto basándote en el contexto.

Responde con JSON:
{{
  "decisions": [
    {{"entity": "nombre", "attribute": "tipo", "value": "valor_correcto", "reason": "breve"}}
  ]
}}
"""
        return prompt
    
    def _parse_llm_conflict_response(
        self,
        response: str,
    ) -> dict[tuple[str, str], dict]:
        """Parsea respuesta del LLM sobre conflictos."""
        import json
        
        try:
            # Limpiar respuesta
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            decisions = {}
            for d in data.get("decisions", []):
                key = (d["entity"].lower(), d["attribute"])
                decisions[key] = {
                    "value": d["value"],
                    "reason": d.get("reason", ""),
                }
            
            return decisions
        
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return {}
    
    # =========================================================================
    # FASE 4: DEDUPLICACIÓN
    # =========================================================================
    
    def _phase4_deduplicate(
        self,
        attributes: list[ResolvedAttribute],
    ) -> list[ResolvedAttribute]:
        """
        Fase 4: Eliminar duplicados.
        
        Prioridad:
        1. Mayor confianza
        2. Método sintáctico sobre otros
        3. Mayor cantidad de fuentes
        """
        # Agrupar por (entidad, tipo)
        groups: dict[tuple[str, str], list[ResolvedAttribute]] = defaultdict(list)
        for attr in attributes:
            key = (attr.entity_name.lower(), attr.attribute_type)
            groups[key].append(attr)
        
        final = []
        for key, group in groups.items():
            if len(group) == 1:
                final.append(group[0])
            else:
                # Elegir el mejor
                best = max(
                    group,
                    key=lambda a: (
                        a.resolution_method in {"syntactic", "llm_arbitration"},
                        a.final_confidence,
                        len(a.sources),
                    )
                )
                final.append(best)
        
        return final
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _build_sentence_subject_map(
        self,
        doc,
        entity_set: set[str],
    ) -> dict[int, Optional[str]]:
        """
        Construye mapa de sujeto por oración para tracking de sujeto tácito.
        
        Returns:
            {sent_start_char: entity_name_or_None}
        """
        sentence_subjects = {}
        last_subject = None
        
        for sent in doc.sents:
            subject = None
            
            # Buscar sujeto explícito en la oración
            for token in sent:
                if token.dep_ in {"nsubj", "nsubj:pass"}:
                    # ¿Es una entidad conocida?
                    entity = self._resolve_entity(token, entity_set)
                    if entity:
                        subject = entity
                        break
            
            if subject:
                last_subject = subject
            
            sentence_subjects[sent.start_char] = last_subject
        
        return sentence_subjects
    
    def _resolve_entity(
        self,
        token,
        entity_set: set[str],
    ) -> Optional[str]:
        """
        Resuelve un token a una entidad conocida.
        
        Maneja:
        - Nombres directos: "María" → "María"
        - Nombres compuestos: "Juan Carlos" → "Juan Carlos"
        - Pronombres: "él" → None (requiere resolución de correferencia)
        """
        # Intentar con el token solo
        if token.text.lower() in entity_set:
            return token.text
        
        # Intentar con token + siguiente (nombre compuesto)
        if token.nbor(1) and token.nbor(1).pos_ == "PROPN":
            compound = f"{token.text} {token.nbor(1).text}"
            if compound.lower() in entity_set:
                return compound
        
        # Buscar en entidades del doc
        for ent in token.doc.ents:
            if ent.start <= token.i < ent.end:
                if ent.text.lower() in entity_set:
                    return ent.text
        
        return None
    
    def _classify_attribute(
        self,
        value: str,
        token,
    ) -> Optional[str]:
        """Clasifica un adjetivo en tipo de atributo."""
        value_lower = value.lower()
        
        # Altura
        if value_lower in {"alto", "alta", "bajo", "baja"}:
            return "height"
        
        # Complexión
        if value_lower in {"delgado", "delgada", "gordo", "gorda", "fornido", 
                           "fornida", "esbelto", "esbelta", "robusto", "robusta"}:
            return "build"
        
        # Edad
        if value_lower in {"joven", "viejo", "vieja", "anciano", "anciana", 
                           "mayor", "adulto", "adulta"}:
            return "age"
        
        # Colores (pueden ser ojos/pelo, contexto determina)
        if value_lower in {"rubio", "rubia", "moreno", "morena", "castaño", 
                           "castaña", "canoso", "canosa"}:
            return "hair_color"
        
        return None
    
    def _classify_body_part_attribute(
        self,
        body_part: str,
        modifier: str,
    ) -> Optional[str]:
        """Clasifica atributo basado en parte del cuerpo + modificador."""
        body_lower = body_part.lower()
        mod_lower = modifier.lower()
        
        # Ojos
        if body_lower in {"ojos", "ojo", "mirada", "iris"}:
            if mod_lower in {"azul", "azules", "verde", "verdes", "marrón", 
                            "marrones", "negro", "negros", "gris", "grises",
                            "castaño", "castaños", "miel", "avellana"}:
                return "eye_color"
        
        # Pelo/Cabello
        if body_lower in {"pelo", "cabello", "melena", "cabellera"}:
            if mod_lower in {"rubio", "negro", "castaño", "canoso", "gris",
                            "pelirrojo", "moreno", "oscuro", "claro"}:
                return "hair_color"
            if mod_lower in {"largo", "corto", "rizado", "liso", "ondulado",
                            "fino", "grueso", "espeso"}:
                return "hair_type"
        
        return None
    
    def _is_metaphor(self, context: str) -> bool:
        """Detecta si el contexto indica una metáfora."""
        metaphor_indicators = [
            r'\bcomo\s+(?:un|una|el|la)\b',
            r'\bparec[ií]a\b',
            r'\bsemejante\s+a\b',
            r'\bbrillar\b',
            r'\breflejar\b',
            r'\bprofund[oa]s\b',  # "ojos profundos" = metáfora
        ]
        
        for pattern in metaphor_indicators:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        return False
    
    def _build_entity_position_index(
        self,
        doc,
        entity_set: set[str],
    ) -> list[tuple[str, int, int]]:
        """
        Construye índice de posiciones de entidades en el texto.
        
        Returns:
            [(entity_name, start_char, end_char), ...]
        """
        positions = []
        
        # Desde NER de spaCy
        for ent in doc.ents:
            if ent.label_ in {"PER", "PERSON"} and ent.text.lower() in entity_set:
                positions.append((ent.text, ent.start_char, ent.end_char))
        
        # Búsqueda directa de nombres
        for entity in entity_set:
            for match in re.finditer(
                rf'\b{re.escape(entity)}\b',
                doc.text,
                re.IGNORECASE
            ):
                # Evitar duplicados con NER
                is_dup = any(
                    abs(p[1] - match.start()) < 5
                    for p in positions
                )
                if not is_dup:
                    positions.append((entity, match.start(), match.end()))
        
        return sorted(positions, key=lambda x: x[1])
    
    def _get_spacy_doc(self, text: str):
        """Obtiene documento spaCy (con lazy loading)."""
        if self._nlp is None:
            from narrative_assistant.nlp.spacy_gpu import load_spacy_model
            self._nlp = load_spacy_model()
        return self._nlp(text)
```

---

## 📊 PARÁMETROS Y UMBRALES

### Tabla de Confianzas

| Tipo de Asignación | Confianza Base | Descripción |
|---|---|---|
| `syntactic_explicit` | 0.92 | Sujeto explícito en dependencias |
| `llm_verified` | 0.95 | LLM confirmó asignación |
| `syntactic_tacit` | 0.78 | Sujeto inferido por contexto |
| `proximity_strong` | 0.70 | Misma oración, <50 caracteres |
| `semantic_match` | 0.65 | Embeddings coincide |
| `proximity_weak` | 0.55 | Misma oración, lejos |

### Tabla de Pesos para Votación

| Método | Peso | Precisión Esperada |
|---|---|---|
| LLM | 0.45 | 0.90 |
| Dependency | 0.40 | 0.88 |
| Regex | 0.25 | 0.92 |
| Embeddings | 0.20 | 0.68 |

### Umbrales de Decisión

| Umbral | Valor | Uso |
|---|---|---|
| `accept_without_voting` | 0.85 | Aceptar candidato sin más verificación |
| `discard_candidate` | 0.40 | Descartar candidato por baja confianza |
| `require_llm_for_conflict` | 0.75 | Diferencia mínima entre candidatos para evitar LLM |
| `complexity_threshold_llm` | 0.70 | Complejidad de texto para activar LLM |

---

## 🎯 CASOS DE PRUEBA ESPERADOS

```python
# Caso 1: Asignación clara por sintaxis
text = "María tenía los ojos azules."
# → María.eye_color = "azules" (conf=0.92, method=syntactic)

# Caso 2: Sujeto tácito
text = "María entró en la sala. Era alta y delgada."
# → María.height = "alta" (conf=0.78, method=syntactic_tacit)
# → María.build = "delgada" (conf=0.78, method=syntactic_tacit)

# Caso 3: Conflicto de proximidad
text = "Juan miró a María. Los ojos azules brillaban."
# Sin dependency: María.eye_color = "azules" (por proximidad)
# Con dependency: ??? (no hay sujeto claro)
# → LLM resuelve o se marca como "dudoso"

# Caso 4: Múltiples métodos coinciden
text = "La mujer rubia llamada Ana sonrió."
# Regex detecta: "rubia" (sin entidad)
# Dependency asigna: Ana.hair_color = "rubia"
# → Ana.hair_color = "rubia" (conf=0.95, unanimous)

# Caso 5: Metáfora filtrada
text = "Sus ojos eran como pozos de tristeza."
# → No se extrae (detectada como metáfora)
```

---

## 🔧 INTEGRACIÓN CON CÓDIGO EXISTENTE

La arquitectura CESP está diseñada para integrarse con el código existente:

1. **Reemplaza `_vote_attributes`** en [attributes.py](src/narrative_assistant/nlp/attributes.py) con la lógica de fases
2. **Extiende `ResultAggregator`** en [aggregator.py](src/narrative_assistant/nlp/extraction/aggregator.py) con prioridad sintáctica
3. **Modifica `DependencyExtractor`** para retornar tipo de asignación
4. **Mantiene compatibilidad** con `AttributeExtractionPipeline`

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear clase `CascadingExtractor` basada en pseudocódigo
- [ ] Modificar `DependencyExtractor` para retornar `AssignmentConfidence`
- [ ] Añadir `AttributeCandidate` y `ResolvedAttribute` a base.py
- [ ] Implementar tracking de sujeto mejorado
- [ ] Crear prompt específico para conflictos LLM
- [ ] Añadir tests para cada caso de prueba
- [ ] Benchmark de rendimiento vs arquitectura actual
- [ ] Documentar migración para usuarios existentes

---

**Firmado por el Panel de Expertos**

- Dra. Elena Martínez (Lingüística)
- Prof. Carlos Ruiz (Arquitectura)
- Dra. Ana López (Parsing)
- Ing. Miguel Torres (Rendimiento)
- Dra. Sofía Vega (ML/LLM)
