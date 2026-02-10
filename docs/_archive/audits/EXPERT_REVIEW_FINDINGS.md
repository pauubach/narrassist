# Revisión Multi-Experto — Narrative Assistant Pipeline

**Fecha**: 2026-02-02
**Paneles**: NLP+Lingüista+Corrector, AI+Arquitecto+BE, UX+FE+Editor, PO+QA
**Estado**: 4/4 completados

---

## Resumen Ejecutivo

4 paneles de expertos (11 roles) revisaron exhaustivamente el codebase. Hallaron **85+ issues** que convergen en **4 problemas sistémicos**:

| Problema sistémico | Afecta a | Paneles que lo detectaron |
|---|---|---|
| Listas hardcodeadas donde debería haber análisis morfológico | NER, atributos, metáforas, pro-drop, subjuntivo | NLP, Arquitecto, PO |
| Errores silenciosos entre fases | Pipeline completa, datos corruptos sin aviso | Arquitecto, QA, UX |
| No hay feedback loop | No aprende de correcciones ni dismissals | NLP, UX, PO |
| Proximidad textual en vez de scope gramatical | Atributos, correferencias, coherencia emocional | NLP, Arquitecto, Editor |

### Métricas clave (PO+QA)

| Métrica | Valor | Objetivo |
|---|---|---|
| Codebase | 152 módulos, 106K líneas | — |
| Tests | 2.346 tests, 63 archivos | — |
| Cobertura por imports | ~45% de módulos | >90% |
| Código sin tests | 35-40% (~400 KB) | <10% |
| MVP features funcionando bien | 3-4 de 12 | 12/12 |
| Recall de inconsistencias | 13% | 80% |
| Performance (2-6 KB) | 100-130s | <30s |
| Bugs críticos bloqueantes | 5 | 0 |
| Production readiness | 4.1/10 | 8/10 |

---

# Panel 1: NLP + Lingüista + Corrector

**27 issues** (3 críticos, 9 mayores, 10 moderados, 5 menores)

---

## NLP-C1 [CRÍTICO]: `mention_count` nunca se incrementa

**Ubicación**: `src/narrative_assistant/entities/repository.py:249`

**Código del problema**: El método existe pero nadie lo llama:

```python
# repository.py:249 — método existente, huérfano
def increment_mention_count(self, entity_id: int, delta: int = 1) -> None:
    """Incrementar el contador de menciones."""
    self.db.execute(
        "UPDATE entities SET mention_count = mention_count + ? WHERE id = ?",
        (delta, entity_id),
    )
```

Grep en todo el codebase: **cero llamadas** en código de producción.

**Impacto**:
- `mention_count` siempre es 0 para todas las entidades
- Imposible distinguir protagonistas de figurantes
- Ranking de entidades por importancia roto
- `ORDER BY mention_count DESC` devuelve orden arbitrario

**Fix genérico**: Cada vez que NER detecta una mención y se vincula a una entidad almacenada, llamar a `increment_mention_count(entity_id)`. Añadir tests que verifiquen incremento.

---

## NLP-C2 [CRÍTICO]: Ventana de 400 chars para resolver atributos

**Ubicación**: `src/narrative_assistant/nlp/attributes.py:2556-2728`

**Código del problema**:

```python
# attributes.py:2556 — extrae ventana de contexto (400 chars ATRÁS)
context_start = max(0, position - 400)
context = text[context_start:position]

# attributes.py:2567 — rechaza candidatos fuera de la ventana
if distance < 400:  # Ventana amplia
    candidates.append((name, start, end, distance, entity_type))

# attributes.py:2728 — ajuste de género TAMBIÉN requiere <400
if best_candidate[1] < 400:
    logger.debug(...)
    return best_candidate[0]
```

**Por qué 400 chars no es lingüísticamente correcto**:
- 400 chars ≈ 50-65 palabras
- Oración media en español literario: 150-200 palabras
- Prosa profesional/literaria: frecuentemente 250+ palabras
- 400 chars no corresponde a ninguna unidad lingüística (ni oración, ni cláusula, ni párrafo)

**Ejemplo de fallo**:

```
"Juan García era un ejecutivo exitoso de mediana edad. Su pelo,
que antaño había sido completamente negro, ahora mostraba algunas
canas. La vida en la metrópoli lo había envejecido, aunque su
carácter seguía siendo jovial. Sus compañeros de trabajo siempre
lo recordaban por su sentido del humor, que nunca le abandonaba
incluso en los momentos más difíciles. María, su esposa, solía
bromear diciendo que era imposible hacerlo enojar. Pero lo que
pocos sabían era que guardaba un dolor muy profundo en su pecho,
una herida que nunca había sanado. Y sus ojos verdes, tan
expresivos normalmente, a veces reflejaban una tristeza inexplicable."

Posición de "sus ojos verdes": ~char 520
Posición de "Juan García": char 0
Distancia: >400 chars → _find_nearest_entity() PODRÍA resolverlo a María (más cercana)
```

**Otros fallos**: No detecta límites de párrafo (`\n\n`), ignora cláusulas subordinadas ("María, quien había estado esperando, sus ojos brillaban" → "sus ojos" podría resolverse a María en vez de a Juan del clause principal), no respeta aposiciones ("Juan, mi amigo Carlos, tenía ojos azules" → podría asignar a Carlos en vez de a Juan).

**Fix genérico**: Reemplazar distancia en chars por scope basado en `doc.sents` de spaCy (oración actual + 2-3 oraciones previas). Usar `token.dep_` para identificar sujeto gramatical. Respetar límites de párrafo. Máximo 1000-1500 chars como safety limit.

---

## NLP-C3 [CRÍTICO]: Listas de verbos incompletas en NER

**Ubicación**: `src/narrative_assistant/nlp/ner.py:1191-1535`

**Escala del problema**:

```python
# ner.py:1191-1230 — VERBS_AT_SENTENCE_START
VERBS_AT_SENTENCE_START = {
    "fue", "saludo", "saludó", "vio", "leyó", "llegó",
    "escucho", "escuchó", "dijo", "correo", "corrió",
    # ... ~40 formas
}

# ner.py:1407-1420 — verb_indicators
verb_indicators = {
    "hace", "hizo", "hacen", "hacían",
    "toma", "tomó", "tomaban",
    # ... ~15 formas
}

# ner.py:1466-1535 — VERB_ENDINGS (pattern-based)
VERB_ENDINGS = ('aba', 'aban', 'aria', 'arian', 'aré', ...)
# ... ~30-40 terminaciones
```

- Total cubierto: **~200 formas**
- Español tiene: **20.000+ formas verbales** inflectadas
- Cobertura: **<1%**

**Conjugaciones que faltan completamente**:
- Subjuntivo: "fuera", "fuese", "llegues", "tuviera", "hayas"
- Gerundios: "sabiendo", "haciendo", "siendo", "teniendo"
- Participios como adjetivos: "cansado", "roto", "escrito", "pintado"
- Imperativos: "vuelve", "venid", "esperad", "escuchad"
- Condicional compuesto: "habría podido", "habría sido"
- Verbos comunes enteros: "decir", "ir", "estar", "ser", "mirar", "pensar", "sentir"

**Ejemplo de falso positivo**:

```
Texto: "María corrió rápidamente. Sabiendo que la perseguían,
no se atrevía a mirar atrás. Roto de cansancio, cada paso le
costaba más. Llegaba a la puerta cuando oyó gritos."

Verbos que DEBERÍAN filtrarse pero NO están en las listas:
- "Sabiendo" (gerundio) → extraído como entidad
- "Roto" (participio) → extraído como entidad
- "Llegaba" (imperfecto) → extraído como entidad
- "oyó" (pretérito) → extraído como entidad
```

**Fix genérico**: Reemplazar listas hardcodeadas con POS tagging de spaCy:

```python
for token in doc:
    if token.pos_ in ("VERB", "AUX") or token.tag_.startswith("V"):
        continue  # Es verbo, no es entidad
```

Esto resuelve de golpe el 100% de formas verbales reconocidas por spaCy, en vez del <1% actual.

---

## NLP-M1 [MAYOR]: MISC→PER demasiado agresivo

**Ubicación**: `src/narrative_assistant/nlp/ner.py:985-1076`

```python
# ner.py:1038-1067 — CUALQUIER MISC que coincida con apellido → PER
COMMON_SURNAMES_AS_PER = {
    "ozores", "garcía", "martínez", "lópez", "fernández", ...
}

if text_lower in COMMON_SURNAMES_AS_PER:
    entity.label = EntityLabel.PER  # RECLASIFICAR
```

**Falsos positivos**:
- "la García" (taberna/bar) → CHARACTER
- "los Martínez" (barrio) → CHARACTER
- "calle Fernández" → CHARACTER
- "El López" (tienda) → CHARACTER

**Fix genérico**: Verificar contexto antes de reclasificar — tokens precedentes (artículo + sustantivo locativo como "calle", "barrio", "zona"), preposición "en" (ubicación), función semántica del sintagma.

---

## NLP-M2 [MAYOR]: Detección de metáforas simplista

**Ubicación**: `src/narrative_assistant/nlp/attributes.py:953-962`

```python
METAPHOR_INDICATORS = [
    r"\bcomo\b",           # "como" = like
    r"\bparec[íi]a\b",     # "parecía" = seemed
    r"\bcual\b",           # "cual" = such/which
    r"\bsemejante\s+a\b",  # "semejante a" = similar to
]
```

**Problema**: `como` tiene 6+ usos en español:
1. **Comparación** (metáfora): "Sus ojos eran como diamantes" ✓
2. **Manera**: "Como lo hizo" — NO es metáfora
3. **Temporal**: "Como llegó, vimos la verdad" — NO es metáfora
4. **Condicional**: "Como no vuelvas, te castigo" — NO es metáfora
5. **Aproximación**: "Tenía como veinte años" — NO es metáfora
6. **Causal**: "Como estaba cansado, se sentó" — NO es metáfora

**El sistema trata los 6 como metáfora** → sobrefiltra atributos válidos (20-30% false negatives).

**Además NO detecta metáforas sin marcador**:
- "Era un muro de hielo" (frialdad emocional)
- "Tenía fuego en los ojos" (intensidad)
- "Su corazón era de piedra"

**Comportamiento actual**: Si detecta metáfora → **filtra completamente** el atributo:

```python
if is_metaphor and self.filter_metaphors:
    continue  # SKIP THE ATTRIBUTE ENTIRELY
```

**Fix genérico**: Desambiguar `como` con POS tags (`token.dep_` == `mark` + `head.pos_` == `VERB` → temporal/condicional, no metáfora). Reducir confianza en vez de filtrar (`confidence *= 0.6`). Usar distancia semántica para detectar metáforas implícitas.

---

## NLP-M3 [MAYOR]: Pro-drop incompleto

**Ubicación**: `src/narrative_assistant/nlp/coreference_resolver.py:57`

```python
ZERO = "zero"  # Sujeto omitido (pro-drop)
```

`MentionType.ZERO` está definido pero la resolución real es mínima. En español el sujeto se omite constantemente:

```
"Entré en la habitación. Vi una carta. Leí rápidamente.
Guardé en el bolsillo. Salí corriendo."

→ Todos los predicados: [Yo] Entré, [Yo] Vi, [Yo] Leí, [Yo] Guardé, [Yo] Salí
→ 5 menciones pro-drop del narrador en primera persona
→ Sistema actual: probablemente trata cada verbo como desconectado
```

**Fix genérico**: Implementar resolución desde morfología verbal:

```python
def detect_pro_drop_subject(token):
    person = token.morph.get("Person")  # [1, 2, 3]
    number = token.morph.get("Number")  # [Sing, Plur]
    if person and number:
        return create_zero_pronoun(person, number, token)
```

---

## NLP-M4 [MAYOR]: No distingue discurso directo/indirecto/libre

**Ubicación**: `src/narrative_assistant/nlp/dialogue.py`

El sistema detecta formato de diálogo (rayas, comillas) pero no clasifica tipo de speech:

| Tipo | Ejemplo | Confianza emocional |
|---|---|---|
| Directo | María dijo: "Iré mañana." | Alta — voz real del personaje |
| Indirecto | María dijo que iría mañana. | Baja — filtrado por narrador |
| Libre indirecto | ¿Iría mañana? | Media — voz ambigua |
| Narrativizado | María prometió volver. | Muy baja — acción, no habla |

**Impacto**: Coherencia emocional analiza speech reportado como si fuera diálogo directo → falsos positivos con narrador neutral.

**Fix genérico**: Clasificar tipo de speech (marcas de cita → directo, verbo + "que" → indirecto, pregunta sin atribución → libre, verbo de comunicación sin cita → narrativizado). Ajustar peso de análisis emocional por tipo.

---

## NLP-M5 [MAYOR]: No detecta narrador no fiable

**Ubicación**: Sistema completo (no hay módulo)

```
Narrador: "No estaba nervioso."
Descripción: Sudaba, tartamudeaba, temblaba.
→ Pipeline marca: INCONSISTENCIA ✗
→ Realidad: Técnica narrativa deliberada ✓
```

Inconsistencias intencionales (narrador poco fiable, ironía dramática, autoengaño del personaje) se marcan como errores del manuscrito.

**Manuscritos afectados**: Lolita, Fight Club, cualquier primera persona con autoengaño.

**Fix genérico**: Detectar marcadores de incertidumbre ("creo que", "quizá", "no recuerdo exactamente"), distancia temporal, limitaciones cognitivas. Flag como "posible técnica narrativa" en vez de error.

---

## NLP-M6 [MAYOR]: Coherencia emocional rígida

**Ubicación**: `src/narrative_assistant/analysis/emotional_coherence.py:75-250`

```python
# Mapeo hardcodeado — emoción → sentimiento esperado
EMOTION_SENTIMENT_MAP = {
    "furioso": {"negative"},     # SOLO negativo
    "feliz": {"positive"},       # SOLO positivo
    "triste": {"negative", "neutral"},
}
```

**Problemas**:
1. No detecta rabia fría: "Escúchame bien. No te vuelvo a hablar de esto." → tono controlado pero personaje furioso = coherente en literatura
2. No detecta enmascaramiento: personaje finge felicidad frente al jefe
3. Solo marcadores explícitos de ironía ("dijo con ironía"), no implícitos
4. Ventana de proximidad 500 chars demasiado pequeña
5. Speaker matching exacto (case-sensitive)
6. No considera distancia temporal (furioso → calmado 2 horas después = natural)

**Fix genérico**: Expandir patrones (usar LLM para análisis contextual), ampliar ventana a 1500 chars, matching fuzzy de speakers, considerar distancia temporal entre declaración y diálogo.

---

## NLP-M7 [MAYOR]: Fusión de acentos incompleta

**Ubicación**: `src/narrative_assistant/entities/fusion.py:552-588`

`_name_similarity()` normaliza acentos, pero el path principal de `canonical_name` no:

```python
# Entity creation — NO normaliza acentos
canonical_name = name.lower()  # "maría" ≠ "maria"
```

Resultado: "María" y "Maria" (error OCR común) → dos entidades separadas. Afecta ~30% de nombres españoles.

**Fix genérico**: Normalizar acentos al crear canonical_name con `unicodedata.normalize('NFKD')` + strip combining chars. Añadir variante sin acento como alias automáticamente.

---

## NLP Moderados (resumen detallado)

### NLP-m1: Voseo no soportado
- `voice/profiles.py:34` reconoce "vos" como informal pero no valida conjugaciones voseo
- "vos hablás" podría flaggearse como error gramatical (debería ser válido en español rioplatense)
- Fix: Implementar paradigma de conjugación voseo; añadir modo regional a grammar checker

### NLP-m2: Leísmo/laísmo muy básico
- `spanish_rules.py:443-609` trata todo como error sin distinguir variantes regionales
- "Le vi a Juan" es leísmo aceptado en España
- Fix: Base de datos sociolingüística con gradación (estándar/regional/dialectal/error)

### NLP-m3: Atribución de diálogo ambigua en multi-speaker
- `dialogue.py:59-62` extrae speaker_hint pero no maneja múltiples turnos en un párrafo
- "—¿Cómo estás? —Bien, ¿y tú? —También bien," dijo María. → ¿quién dice qué?
- Fix: Tracking de turnos de diálogo; action beats como indicadores de cambio de speaker

### NLP-m4: Filtro condicional incompleto
- `attributes.py:1076` — CONDITIONAL_INDICATORS no incluye: "si fuese" (arcaico), "aunque fuere" (futuro subj.), "supongamos que", "a menos que"
- Fix: Expandir lista; usar detección de modo subjuntivo de spaCy

### NLP-m5: Indicadores temporales pasados limitados
- `attributes.py:991-1002` — faltan: "antes era", "otrora", "solía", "en aquel entonces", "tiempo atrás", "antaño", "acostumbraba a"
- "Antes era un excelente violinista" → "violinista" extraído como atributo PRESENTE
- Fix: Expandir TEMPORAL_PAST_INDICATORS; detectar imperfecto como indicador de estado pasado

### NLP-m6: No valida concordancia morfológica en atributos
- "El personaje era altas y rubios" → no se detecta mismatch género/número
- Fix: Verificar concordancia adjetivo-sustantivo en extracción de atributos

### NLP-m7: Elipsis y fragmentos no detectados
- "—¿Ojos azules? —Sí. Ojos verdes." → fragmentos sin sujeto
- Fix: Detectar fragmentos (<3 palabras, sin verbo principal); marcar atributos con confianza reducida

### NLP-m8: "se" impersonal no manejado
- "Se encontró el cadáver. Sus heridas..." → "sus" se refiere a quién?
- Fix: Detectar construcción impersonal con "se"; manejar resolución pronominal diferente

### NLP-m9: Detección de modo subjuntivo ausente
- "No creo que sea alto" → "alto" extraído como atributo real (debería ser hipotético)
- "Si fuera rico..." → "rico" extraído como real
- Fix: Detectar modo subjuntivo desde `token.morph`; marcar atributos en subjuntivo como hipotéticos

### NLP-m10: Clíticos enclíticos incompletos
- `ner.py:1503-1514` — ENCLITIC_SUFFIXES tiene "me", "te", "le", etc. pero falta "sela", "selo", combinaciones con gerundio ("dándosela")
- Fix: Expandir combinaciones; detectar accent shifts en gerundio+clítico

---

# Panel 2: AI + Arquitecto + BE

**17 issues** (4 críticos, 4 altos, 5 medios, 4 bajos)

---

## ARCH-C1 [CRÍTICO]: Fases fallan silenciosamente

**Ubicación**: `src/narrative_assistant/pipelines/unified_analysis.py` — flujo completo de fases

**Flujo actual**:
```python
def analyze(...) -> Result[UnifiedReport]:
    context = AnalysisContext()  # Todo en memoria

    # Phase 1: Parse → resultados solo en memoria
    # Phase 2: NER → resultados solo en memoria
    # Phase 3: Coreference → FALLA → context.entities = []
    # Phase 4: Attributes → recibe entities vacío → 0 atributos
    # Phase 5: Quality → recibe atributos vacíos → 0 issues
    # Phase 6: Consistency → recibe vacío → "No inconsistencies found"

    return Result.success(report)  # ← "Éxito" con datos corruptos
```

**Impacto**: El usuario recibe "Análisis completo: 0 problemas encontrados" cuando en realidad la pipeline crasheó internamente. Datos corruptos propagados como verdad.

**Fix genérico**: Precondiciones verificables por fase:

```python
class Phase(ABC):
    @abstractmethod
    def validate_preconditions(self, context: AnalysisContext) -> Result[None]:
        """Verificar que los datos necesarios existen."""
        pass

class NERPhase(Phase):
    def validate_preconditions(self, context):
        if not context.full_text:
            return Result.failure(NarrativeError("Texto del documento vacío"))
        return Result.success(None)

class AttributePhase(Phase):
    def validate_preconditions(self, context):
        if not context.entities:
            return Result.failure(NarrativeError("No hay entidades — NER falló"))
        return Result.success(None)
```

Checkpointing a DB tras cada fase. Error handling granular. Informe parcial si una fase falla.

---

## ARCH-C2 [CRÍTICO]: Acumulación de memoria sin límite

**Ubicación**: Pipeline completa

4 extractores × N capítulos generan listas en memoria sin límite. Para novela larga:

```
4 extractores × 500 capítulos → potencial 180K atributos en memoria
Coherencia emocional: O(n²) comparando párrafos
Consistency check: all-pairs comparison
```

**Extrapolación**:
| Documento | Tamaño | Tiempo estimado | Memoria |
|---|---|---|---|
| 2-6 KB | Evaluación | 100-130s | Aceptable |
| 50 KB | Cuento | ~33 min | Alta |
| 100 KB | Novela corta | ~67 min | Muy alta |
| 500 KB | Novela | ~5.5 horas | OOM probable |

**Fix genérico**: Streaming/chunked processing; flush a DB tras cada capítulo; lazy loading; `BoundedList` con max_size:

```python
class BoundedList(list):
    def __init__(self, max_size=10000):
        self.max_size = max_size
    def append(self, item):
        if len(self) >= self.max_size:
            logger.warning(f"List full (max {self.max_size})")
            return
        super().append(item)
```

---

## ARCH-C3 [CRÍTICO]: Exception handler genérico

**Ubicación**: `unified_analysis.py` — wrapper principal

Un solo `except Exception` envuelve las 6 fases. Si Phase 3 falla:

```
"Unexpected error"
→ Sin indicar QUÉ fase falló
→ Sin indicar QUÉ datos se perdieron
→ Sin indicar QUÉ acción tomar
```

**Fix genérico**: Try/except por fase con errores tipados; log de fase+contexto+stack trace; recovery parcial que devuelve lo que sí funcionó.

---

## ARCH-C4 [CRÍTICO]: Race condition en entity_map

**Ubicación**: `unified_analysis.py` — Phase 3-4 con ThreadPoolExecutor

```python
# Phase 4: 4 extractores en paralelo
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(RegexExtractor(...).extract, context): "regex",
        executor.submit(DependencyExtractor(...).extract, context): "dependency",
        executor.submit(EmbeddingsExtractor(...).extract, context): "embeddings",
        executor.submit(LLMExtractor(...).extract, context): "llm",
    }
```

Todos acceden a `context.entity_map` sin locks. Comportamiento no determinista → atributos asignados a entidad equivocada a veces sí, a veces no.

**Fix genérico**: Inmutabilizar output de cada fase antes de pasar a la siguiente (`frozenset`, `MappingProxyType`). O usar locks en shared state.

---

## ARCH-H1 [ALTO]: `_extract_attributes()` retorna `None`

No propaga errores; caller asume éxito. Fases posteriores trabajan con datos vacíos sin saberlo.

**Fix genérico**: Usar Result pattern consistentemente:
```python
def _extract_attributes(self, context) -> Result[list[ExtractedAttribute]]:
    # ... en vez de retornar None
```

---

## ARCH-H2 [ALTO]: Dos sistemas de tipos de atributos

`AttributeCategory` (viejo) y `AttributeType` (nuevo) coexisten. Queries a DB no encuentran atributos si usan el enum equivocado.

**Fix genérico**: Unificar a un solo sistema; migración de datos existentes.

---

## ARCH-H3 [ALTO]: Coherencia emocional nunca se ejecuta

`run_emotional=True` en config pero `_extract_emotional()` no se invoca en ninguna fase. Feature completa → dead code.

**Fix genérico**: Wiring correcto en pipeline; test de integración que verifique que config flags activan fases.

---

## ARCH-H4 [ALTO]: Campos de capítulo inconsistentes

```python
ch["number"]                    # A veces
ch.get("number", 1)            # Otras veces
ch.get("end_char", float("inf"))  # Otras veces
```

No hay modelo de datos de capítulo. Menciones asignadas a capítulo incorrecto.

**Fix genérico**: Crear dataclass `Chapter` con campos tipados:
```python
@dataclass
class Chapter:
    number: int
    title: str
    start_char: int
    end_char: int
```

---

## ARCH-m1 [MEDIO]: Carga de modelo spaCy repetida en extractores paralelos

**Ubicación**: `src/narrative_assistant/nlp/extraction/pipeline.py:109-114`

```python
class BaseExtractor:
    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = load_spacy_model()  # ← Cada extractor carga el suyo
        return self._nlp
```

4 extractores en paralelo → 4 copias del modelo (4 × 500 MB = 2 GB).

**Fix**: Singleton compartido con double-checked locking.

---

## ARCH-m2: No hay checkpointing entre fases

Si Phase 5 falla tras 30 minutos de análisis, se pierde todo el trabajo de Phase 1-4.

**Fix**: Guardar checkpoint a DB tras cada fase completada; implementar resume-on-crash.

---

## ARCH-m3: Magic numbers sin documentar

400 chars (ventana atributos), 0.4 (threshold validación NER), 500 chars (ventana emocional) — todos hardcodeados sin nombre ni config.

**Fix**: Extraer a constantes nombradas en config.

---

## ARCH-m4: API server sin rate limiting

Sin límites de tamaño de request ni rate limiting. Upload de archivo de 10 GB → servidor se congela.

---

## ARCH-m5: SQLite WAL sin vacuum automático

DB crece indefinidamente sin cleanup.

---

## ARCH-b1 [BAJO]: No hay validación de nombres de entidad

Entidades se crean sin validar que `canonical_name` no sea vacío, None, o demasiado largo.

---

## ARCH-b2 [BAJO]: FK constraints inconsistentes en SQLite

`PRAGMA foreign_keys = ON` solo en algunos code paths.

---

## ARCH-b3 [BAJO]: Tabla `attribute_evidences` nunca se llena

Schema existe pero nada la popula. Evidencias textuales de atributos no se guardan.

---

## ARCH-b4 [BAJO]: Config no se auto-valida

`run_attributes=True` + `run_ner=False` = atributos sin entidades. No hay validación de coherencia de config.

---

# Panel 3: UX + FE + Editor

**20 issues**, organizados por impacto editorial

---

## UX-C1 [CRÍTICO]: No hay edición inline desde alertas

Editor debe context-switch constantemente entre lista de alertas y texto del manuscrito. En herramientas estándar (Word, Scrivener), el corrector trabaja directamente sobre el texto.

**Impacto**: ~25 minutos extra por manuscrito.

**Fix genérico**: Click en alerta → scroll al texto con highlight. Botón "Ver en contexto":

```typescript
function navigateToLocation() {
  emit('navigate-to-location', {
    chapter: alert.chapter,
    startChar: alert.spanStart,
    endChar: alert.spanEnd,
    excerpt: alert.excerpt
  })
}
```

---

## UX-C2 [CRÍTICO]: No hay comparación lado a lado

Inconsistencia "ojos verdes cap 2 vs azules cap 5" → editor debe navegar manualmente entre ambos capítulos para verificar.

**Impacto**: 30-60 segundos por cada inconsistencia para verificar.

**Fix genérico**: Vista split con ambas referencias side by side. Componente `AttributeComparisonTable`:

```typescript
// Agrupar por valor — mostrar cada variante con sus menciones
const groupedByValue = computed(() => {
  const groups = new Map<string, AlertSource[]>()
  sources.value.forEach(source => {
    const key = source.value
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(source)
  })
  return groups
})
```

Tabla con: Valor | Menciones | Capítulos | Confianza | Contexto (con botón "Ver").

---

## UX-C3 [CRÍTICO]: Confidence threshold no configurable en UI

No hay slider ni filtro para nivel de confianza. Imposible reducir ruido de falsos positivos.

**Fix genérico**: Añadir a workspace store:

```typescript
const alertConfidenceThreshold = ref(0.3)
function setAlertConfidenceThreshold(value: number) {
  alertConfidenceThreshold.value = value
  localStorage.setItem('alertConfidenceThreshold', String(value))
}
```

Slider en panel de alertas.

---

## UX-C4 [CRÍTICO]: No hay "scroll to text" desde alertas

Alerta muestra posición pero no navega. 30-60s por alerta buscando manualmente.

**Fix genérico**: Botón "Ver en contexto" que navega y resalta.

---

## UX-FP1 [ALTO]: No aprende de dismissals

Descartar alerta → re-análisis → misma alerta generada otra vez → loop infinito.

**Fix genérico**: Persistir dismissals en DB; excluir de futuros análisis; opción de "suprimir regla":

```python
class FeedbackTracker:
    def record_dismissal(self, alert_type: str, confidence: float):
        metrics = self.metrics[alert_type]
        metrics.dismissed += 1
        metrics.total_generated += 1
        fp_rate = metrics.false_positive_rate
        if fp_rate > 0.5:
            logger.warning(f"'{alert_type}' tiene {fp_rate:.0%} false positives")
```

---

## UX-FP2 [ALTO]: No hay whitelisting/suppression rules

No puedes decir "ignora variantes María/Maria para entidad #3".

**Fix genérico**: Reglas de supresión por entidad, por tipo de alerta, por capítulo.

---

## UX-FP3 [ALTO]: No hay métricas de precisión

No se trackean aceptaciones vs dismissals. No sabes qué detectores tienen 90% accuracy vs 20%.

**Fix genérico**: Dashboard con acceptance rate por tipo de detector.

---

## UX Estado y Responsividad

### UX-m1: Filtros de alertas se resetean al navegar
State no persiste al cambiar de tab/vista.

### UX-m2: Diálogos con `width: '450px'` hardcodeado
Overflow en pantallas pequeñas/móvil.

### UX-m3: No hay breakpoints responsive
Componentes de alertas no se adaptan.

---

## UX Features Ausentes para Editor Profesional

| ID | Feature | Descripción |
|---|---|---|
| UX-f1 | Heatmap por capítulo | Estadísticas de alertas por capítulo — visualizar dónde se concentran los problemas |
| UX-f2 | Operaciones batch | Resolver/descartar múltiples alertas de una vez |
| UX-f3 | Modo review secuencial | Navegar alertas con keyboard shortcuts (←→ anterior/siguiente, Enter resolver, Esc descartar) |
| UX-f4 | Vista timeline | Timeline integrado con alertas temporales |
| UX-f5 | Presets por género | Ficción/no-ficción/técnico → umbrales y detectores diferentes |
| UX-f6 | Export a Word | Alertas como comentarios de Word para compartir con autores |

---

## Evaluación general del panel UX+FE+Editor

| Aspecto | Score |
|---|---|
| Arquitectura frontend | ⭐⭐⭐⭐ (Vue 3 + Pinia + TypeScript + PrimeVue) |
| Tipo safety | ⭐⭐⭐⭐ (API types separados de domain types con transformers) |
| Experiencia de usuario | ⭐⭐ (funcional pero no profesional) |
| Preparación para editor profesional | ⭐⭐ (falta feedback loop, navegación, batch) |
| Responsividad | ⭐ (roto en móvil) |
| Testing frontend | ⭐⭐ (stores testeados, componentes no) |
| Accesibilidad | ⭐⭐⭐⭐ (ARIA labels, semántico — buena base) |

---

# Panel 4: PO + QA

**Hallazgos detallados del Product Owner y QA Lead**

---

## QA: Cobertura de tests

### Infraestructura de tests

```
tests/
├── unit/          (35 archivos, ~12K líneas, ~600 tests)
├── adversarial/   (22 archivos, ~18K líneas, ~1.200 tests)
├── integration/   (5 archivos, ~3K líneas, ~200 tests)
├── evaluation/    (2 archivos)
└── regression/    (1 archivo)
Total: 2.346 tests en 63 archivos
```

### Tests con buena cobertura

| Archivo | Tests | Calidad |
|---|---|---|
| `test_chapter_summary.py` (26 KB) | 80+ | Exhaustivo |
| `test_character_location.py` (29 KB) | 100+ | Exhaustivo |
| `test_attributes.py` (19 KB) | 65+ | Shallow |
| `test_relationships.py` (24 KB) | 85+ | Bueno |
| `test_consistency.py` (19 KB) | 70+ | Bueno |
| `test_readability.py` (22 KB) | 80+ | Bueno |
| `test_pacing.py` (23 KB) | 90+ | Bueno |
| `test_vital_status.py` (28 KB) | 60+ | Bueno |

### Tests con cobertura débil (smoke tests)

| Archivo | Tests | Problema |
|---|---|---|
| `test_ner.py` (5.3 KB) | **13** | NER apenas testeado — módulo crítico |
| `test_coreference.py` (7.3 KB) | **7** | Correferencia voting system apenas testeado |
| `test_parsers.py` (5.6 KB) | **8** | Solo TXT/DOCX, no EPUB/PDF |
| `test_orthography.py` (8.9 KB) | ~25 | Mínimo para spelling/grammar |

### Módulos sin tests (0 cobertura)

| Módulo | Tamaño | Riesgo |
|---|---|---|
| `character_knowledge.py` | 55 KB | 🔴 MUY ALTO — lógica compleja, no probada |
| `semantic_fusion.py` | — | 🔴 Fusión semántica de entidades |
| `character_sheets.py` | 60 KB | 🔴 Exportador no validado |
| `scrivener_exporter.py` | 33 KB | 🔴 Probablemente genera XML inválido |
| `pdf_parser.py` | 25 KB | 🔴 Declarado soportado pero sin test |
| `epub_parser.py` | 20 KB | 🔴 Declarado soportado pero sin test |
| `register.py` | ~400 líneas | 🔴 Análisis de registro |
| `story_bible.py` | 13 KB | 🟠 |

### Edge cases no cubiertos

**Documentos extremos**:
- ❌ Archivo vacío (0 bytes)
- ❌ Solo whitespace
- ❌ Una sola palabra/oración
- ❌ Solo diálogo (sin narración)
- ❌ Solo narración (sin diálogo)
- ❌ Novela 500+ páginas (500 KB+)
- ❌ Documento con miles de personajes
- ❌ Capítulo único >100 KB

**Idioma**:
- ❌ Español + inglés mezclado (muy común en LatAm)
- ❌ Español medieval/arcaico
- ❌ Dialectos múltiples mezclados
- ❌ Poesía (saltos de línea no estándar)
- ❌ Narrativa experimental (fragmentada, no lineal)
- ❌ Documentos con HTML/XML embebido

**Personajes**:
- ❌ Mismo nombre para distintos personajes (homonimia)
- ❌ Nombres de una letra (X, Z, A)
- ❌ Nombres fantásticos nunca en datos de entrenamiento
- ❌ Nombres con partículas ("María de los Ángeles")

**Diálogo**:
- ❌ Diálogo anidado (diálogo dentro de diálogo)
- ❌ Estilos de cita mezclados (— con «»)
- ❌ Múltiples hablantes en un párrafo
- ❌ Diálogo que cruza párrafos
- ❌ Monólogo interior vs diálogo hablado

**Temporal**:
- ❌ Narrativa no lineal (flashbacks intercalados)
- ❌ Marcadores temporales vagos ("pronto", "tiempo después")
- ❌ Formatos de fecha conflictivos
- ❌ Tiempo circular (final = inicio)

**Formatos**:
- ❌ DOCX con tablas embebidas
- ❌ DOCX con headers/footers
- ❌ DOCX con notas al pie
- ❌ DOCX con tracked changes
- ❌ PDF con texto en imagen (OCR)
- ❌ PDF con columnas múltiples
- ❌ EPUB2 vs EPUB3

### Tests de integración — lo que falta

```
❌ Documento grande (100+ KB) end-to-end
❌ Validación de consistencia multi-capítulo
❌ Exportación que preserve estructura de input
❌ Recovery de errores (NER falla a mitad)
❌ Análisis concurrente (thread-safe state)
❌ Análisis incremental (documento actualizado)
❌ Cache invalidation (documento cambiado)
❌ Pipeline con todas las features on vs off
```

### Riesgo de regresión por módulo

| Módulo | Riesgo | Tests | Razón |
|---|---|---|---|
| Coreference resolver (2000+ líneas) | 🔴 MUY ALTO | 7 tests | Voting system complejo, sin tests sistemáticos |
| NER (500+ líneas) | 🔴 MUY ALTO | 13 tests | Crea entidades basura, sin validación post-NER |
| Attributes (800+ líneas) | 🟠 ALTO | 65 tests (shallow) | 47% recall, misatribución conocida |
| Spelling checker (300+ líneas) | 🟠 ALTO | ~25 tests | Falsos positivos de regex |
| Temporal (400+ líneas) | 🟠 ALTO | ~30 tests | Deshabilitado por defecto, 0% accuracy |

---

## PO: Feature Completeness — MVP vs Realidad

### Definición de MVP (12 capabilities) vs Estado Actual

| # | Capability | Implementado | Calidad | ¿Funciona? |
|---|---|---|---|---|
| 1 | Parser DOCX | ✅ | Buena | ✅ SÍ |
| 2 | Detección de estructura | ✅ | Regular | ⚠️ PARCIAL (83% precision) |
| 3 | Pipeline NER | ✅ | Pobre | ❌ NO (entidades falsas) |
| 4 | Detección de diálogo | ✅ | Buena | ✅ SÍ |
| 5 | Correferencia básica | ✅ | Rota | ❌ NO (bug de parámetros) |
| 6 | Fusión manual de entidades | ✅ | Buena | ✅ SÍ |
| 7 | Extracción de atributos | ✅ | Pobre | ❌ NO (47% recall) |
| 8 | Inconsistencias de atributos | ✅ | Pobre | ❌ NO (13% recall) |
| 9 | Motor de alertas | ✅ | Regular | ⚠️ PARCIAL |
| 10 | Variantes grafía | ⚠️ Parcial | Pobre | ❌ NO (sin merge acentos) |
| 11 | Export guía de estilo | ✅ | Desconocida | ❌ SIN TESTAR |
| 12 | CLI | ✅ | Buena | ✅ SÍ |

**Resultado: 9/12 implementadas, 3-4/12 funcionando bien = 25% del MVP funcional**

### Soporte de formatos de documento

| Formato | README dice | Testeado | Estado real |
|---|---|---|---|
| DOCX | Prioritario | ✅ Sí | ✅ Producción |
| TXT | Soportado | ✅ Sí | ✅ Producción |
| MD | Soportado | ⚠️ Mínimo | ⚠️ Funciona como TXT |
| PDF | Soportado | ❌ No | ❌ Probablemente roto |
| EPUB | Soportado | ❌ No | ❌ Probablemente roto |

**README anuncia 5 formatos, solo 2-3 realmente testeados.**

### Cobertura de géneros

**Testeados** (archivos `unseen_test_*.txt`):
✅ Ciencia ficción, novela histórica, thriller, romance, fantasía, terror, aventuras, drama familiar

**No testeados**:
❌ Poesía, escritura técnica, memorias/autobiografía, guiones, literatura infantil, narrativa experimental, novela epistolar, múltiples POV, narrador no fiable

### Performance

| Documento | Tamaño | Tiempo actual | Aceptable |
|---|---|---|---|
| 2-6 KB | Evaluación | 100-130s | ❌ Lento |
| 50 KB | Cuento | ~33 min | ❌ Inaceptable |
| 100 KB | Novela corta | ~67 min | ❌ Inaceptable |
| 500 KB | Novela | ~5.5 horas | ❌ Imposible |

**Objetivo**: <30 segundos para 50 KB.

### Offline-first — Verificación

| Componente | Offline | Nota |
|---|---|---|
| Modelos NLP | ✅ tras descarga | Primera vez requiere internet |
| Ollama/LLM | ✅ localhost | Primera vez requiere download |
| Pipeline de análisis | ✅ 100% | Sin conexiones externas |
| Verificación licencias | ❌ | Requiere online |
| Telemetría | ✅ No hay | Ninguna |

**Promesa mayormente mantenida** salvo verificación de licencias.

### Análisis competitivo

| Feature | ProWritingAid | Grammarly | Scrivener | **Este sistema** |
|---|---|---|---|---|
| Grammar/style | Excelente | Avanzado | — | Regular |
| Consistencia personajes | No | No | Manual | **Automático (roto)** |
| Privacidad | Cloud | Cloud | Offline | **Offline** |
| Español nativo | Limitado | Básico | Sí | **Nativo** |
| Precio | $99-199/año | $12-30/mes | $99 único | Desconocido |

**USP**: Detección automática de inconsistencias + offline + español nativo. Pero USP principal no funciona (13% recall).

---

## PO: Criterios de aceptación — Evaluación

| Criterio | Objetivo | Actual | ¿Cumple? |
|---|---|---|---|
| Parser sin perder texto | 100% párrafos | 100% | ✅ |
| Detección capítulos >95% | 95% | 83% | ❌ |
| NER F1 ~60-70% ficción | 60-70% | Desconocido (sospecha <50%) | ❌ |
| Inconsistencias atributos >80% recall | 80% | 13% | ❌ (-67pp) |
| Inconsistencias temporales funcional | Funcional | 0% (deshabilitado) | ❌ |
| 100% offline post-setup | Offline | Mayormente | ⚠️ |
| Corrección manual NER/coref | Funcional | Funcional | ✅ |
| Export informe DOCX/PDF | Funcional | Sin testar | ❌ |

**Solo 2 de 8 criterios cumplidos.**

---

## QA/PO: Estado de producción

### Madurez del producto

| Dimensión | Score | Estado |
|---|---|---|
| Calidad de código | 6/10 | ⚠️ Módulos grandes sin tests |
| Cobertura de tests | 5/10 | ⚠️ 2.346 tests pero muchos son smoke |
| Documentación | 7/10 | ✅ CLAUDE.md excelente, docs usuario faltan |
| Performance | 2/10 | 🔴 100+ seg para 2-6 KB |
| Accuracy | 3/10 | 🔴 13% recall en feature core |
| Feature completeness | 6/10 | ⚠️ 9/12 MVP, solo 3-4 funcionando |
| Error handling | 5/10 | ⚠️ Fallos silenciosos, cascada |
| Offline guarantee | 7/10 | ✅ Funciona offline post-setup |
| Escalabilidad | 2/10 | 🔴 No escala más allá de docs pequeños |
| Seguridad/Privacidad | 7/10 | ✅ Sin telemetría, local |
| **TOTAL** | **5.0/10** | **❌ NO PRODUCTION READY** |

### Escenarios de release

| Escenario | Timeline | Riesgo | Resultado |
|---|---|---|---|
| Release as-is | Ahora | MUY ALTO | Usuarios frustrados, daño reputacional |
| Fix bugs críticos → Beta | 2-4 semanas | ALTO | Funciona para docs pequeños, lento pero usable |
| Fix + Test + Optimize → 1.0 | 6-12 meses | MEDIO | Production-ready, cumple MVP |

---

# Convergencia Cross-Panel (4 de 4)

Los 4 paneles convergen en los mismos problemas sistémicos:

## 1. Listas hardcodeadas vs análisis morfológico

| Panel | Manifestación |
|---|---|
| **NLP** | Verbos, metáforas, pro-drop, subjuntivo — todo usa listas estáticas de <1% cobertura |
| **Arquitecto** | Magic numbers (400 chars, 0.4 threshold, 500 char window) sin parametrizar |
| **UX** | Confidence no configurable; presets de género no existen |
| **QA** | Listas incompletas causan falsos positivos que no se capturan en tests |
| **Solución genérica** | Migrar a features de spaCy (`pos_`, `morph`, `dep_`); externalizar umbrales a config editable |

## 2. Errores silenciosos entre fases

| Panel | Manifestación |
|---|---|
| **NLP** | NER produce entidades basura → pipeline las propaga como verdad |
| **Arquitecto** | Fases fallan → datos corruptos, `except Exception` global → "Unexpected error" |
| **UX** | Usuario no sabe qué falló ni por qué; ve "0 problemas" cuando la pipeline crasheó |
| **QA** | 5 bugs críticos bloqueantes; tests no validan precondiciones entre fases |
| **Solución genérica** | Precondiciones verificables por fase; Result pattern en todo; feedback visual; checkpoints |

## 3. No hay feedback loop

| Panel | Manifestación |
|---|---|
| **NLP** | No aprende de correcciones del usuario; no mejora con uso |
| **Arquitecto** | No guarda checkpoints; no hay métricas de rendimiento por fase |
| **UX** | Dismissals no persisten; mismos falsos positivos en cada re-análisis |
| **PO** | No hay métricas de precisión por detector; no se sabe qué funciona bien |
| **Solución genérica** | Persistir decisiones; excluir supresiones; métricas por detector; dashboard de accuracy |

## 4. Proximidad textual en vez de scope gramatical

| Panel | Manifestación |
|---|---|
| **NLP** | Atributos por chars (400), no por oración; no respeta cláusulas subordinadas ni aposiciones |
| **Arquitecto** | entity_map race condition por compartir estado mutable entre threads |
| **UX** | No hay "go to text" para que el editor verifique el contexto real |
| **Editor** | Misatribuciones frustran al editor profesional — pierde confianza en la herramienta |
| **Solución genérica** | Scope basado en `doc.sents` + dep parsing; inmutabilizar outputs; navegación a texto |

---

# Debate Inter-Expertos y Lista Final de Soluciones

## Desacuerdos clave del debate

### ¿Primero corregir o primero infraestructura?

**Arquitecto**: "Hay que arreglar la propagación de errores silenciosos primero. Cada otro fix se invalida si Phase N+1 consume datos vacíos silenciosamente."

**Product Owner**: "La accuracy está al 13% vs objetivo 80%. Los usuarios no les importa el error handling si la herramienta no encuentra nada."

**QA Lead**: "Sin validación de fases, no podemos ni medir si los fixes de NER funcionan. Arreglaremos NER, veremos '0 issues' en tests de integración, y perderemos días descubriendo que la pipeline se tragó los resultados."

**Consenso**: Validación de fases primero (rápido, desbloquea medición), luego NER/atributos.

### ¿Expandir listas o cambiar mecanismo?

**NLP Engineer**: "Las listas de verbos cubren ~200 formas de 20.000+. Hay que usar `token.pos_ == 'VERB'` de spaCy."

**Lingüista**: "De acuerdo, pero spaCy tiene debilidades con voseo y subjuntivo. POS como mecanismo principal, pero un pequeño override set para errores conocidos de spaCy."

**AI/ML Engineer**: "Esto es un patrón que se repite: MISC→PER, metáforas, pro-drop — todos sufren lo mismo. Crear una capa centralizada de análisis morfológico."

**Arquitecto**: "Elegante pero arriesgado. Fix NER primero, probar el patrón, luego propagar."

**Consenso**: Reemplazar listas con spaCy en NER primero, crear módulo `morpho_utils.py`, propagar después.

### ¿Qué tan lejos ir con scope gramatical?

**Lingüista**: "La ventana de 400 chars es fundamentalmente incorrecta. Necesitamos detección de límites de oración como mínimo, idealmente parsing de cláusulas."

**NLP Engineer**: "Límites de oración fácil — spaCy nos da `doc.sents`. Cláusulas mucho más difícil — el dependency parser de spaCy para español no es fiable para segmentación de cláusulas."

**BE**: "Me preocupa performance. Ya tardamos 100-130s."

**AI/ML**: "Sentence-scoped limita el espacio de búsqueda. Podría ser más rápido."

**Consenso**: Reemplazar char-window con sentence/paragraph scope. NO intentar clause-level parsing.

### ¿El feedback loop ahora o después?

**PO**: "Persistencia de dismissals es importante para retención, pero no arregla accuracy. P2."

**Editor**: "Mis correctores pierden 30% de su tiempo re-descartando alertas ya revisadas. Es un blocker de workflow, no un nice-to-have."

**QA**: "El feedback loop nos da datos. Si los usuarios descartan 80% de alertas de metáforas, sabemos que ese detector necesita trabajo."

**Consenso**: Persistencia de dismissals a P1. Tuning de thresholds basado en feedback a P2.

---

## Lista Final de Soluciones (Priorizada)

### S-1 [P0]: Validación de Fases y Propagación de Errores

**Issues que resuelve**: Fases fallan silenciosamente (ARCH-C1), exception handler genérico (ARCH-C3), race condition entity_map (ARCH-C4), mention_count nunca incrementado (NLP-C1), coherencia emocional nunca ejecutada (ARCH-H3)

**Consenso**: 11/11 expertos de acuerdo. Es la base para todo lo demás.

**Qué cambia**:
- `unified_analysis.py`: Reemplazar el `try/except Exception` global con validación por fase. Cada fase retorna `Result[T]` y valida que su output no esté vacío antes de pasar a la siguiente
- `core/errors.py`: Añadir `PhaseError` con `phase_name`, `input_summary`, `output_summary`
- Assertions entre fases: si NER retorna 0 entidades para documento con >100 palabras → WARNING
- Fix `mention_count`: trazar por qué nunca se incrementa (probablemente fallo silencioso)
- Fix coherencia emocional: config la activa pero pipeline no la llama → añadir invocación
- `threading.Lock` en entity_map para ThreadPoolExecutor (5 líneas)

**Por qué genérico**: No arregla ninguna detección específica. Arregla la infraestructura que permite observar, medir y validar todos los demás fixes.

**Dependencias**: Ninguna. Es la fundación.

**Riesgo si se omite**: Cada fix posterior es inverificable. Mejoras en NER podrían funcionar pero producir "0 issues" porque una fase posterior falló silenciosamente.

---

### S-2 [P0]: Reemplazar Listas Hardcodeadas con Análisis Morfológico de spaCy

**Issues que resuelve**: NER listas de verbos (NLP-C3), MISC→PER agresivo (NLP-M1), metáforas "como" (NLP-M2), pro-drop (NLP-M3), subjuntivo no detectado (NLP-m9), acentos no normalizados (NLP-M7), ~60-70% de falsos negativos de NER

**Consenso**: 10/11. Arquitecto prefiere NER primero y luego propagar (vs todo de golpe).

**Qué cambia**:
- **Crear `nlp/morpho_utils.py`**: Módulo centralizado con `is_verb(token)`, `is_proper_noun(token)`, `get_gender(token)`, `get_number(token)`, `get_verb_mood(token)`, `normalize_name(text)`. Fuente única de verdad para queries morfológicas.
- **`nlp/ner.py`**: Reemplazar `_is_verb_form()` + listas con `morpho_utils.is_verb()`. Reemplazar MISC→PER con check de contexto: solo reclasificar si tiene capitalización de nombre propio Y aparece como sujeto/objeto de verbo "de persona" (hablar, caminar, sentir) determinado por dep parsing.
- **`nlp/ner.py`**: Normalización de acentos en `canonical_name` vía `morpho_utils.normalize_name()`.
- **`nlp/attributes.py`**: Reemplazar lógica de "como = metáfora" con dep parsing: `como` como `mark` (conjunción subordinante) o `advmod` (manera) NO es comparación. Reducir de flag binario a score de confianza (0.0-1.0).
- **Pro-drop**: Detectar verbos conjugados sin `nsubj` explícito en el parse → flag como pronombre cero → resolver usando persona/número contra contexto de entidades.

**Por qué genérico**: Reemplaza una categoría entera de conocimiento lingüístico hardcodeado con modelos entrenados de spaCy. Cualquier verbo en cualquier conjugación se maneja. Cualquier nuevo patrón de metáfora se maneja por dep parsing. Escala a todos los módulos actuales y futuros.

**Dependencias**: S-1 (necesita validación de fases para verificar mejoras).

**Riesgo si se omite**: NER sigue al ~13% recall. La herramienta no detecta nombres de personajes que siguen verbos no incluidos en las 200 formas. Metáforas falso-positivas continúan. Pro-drop (extremadamente común en español) sigue sin resolver.

---

### S-3 [P0]: Resolución de Scope Gramatical (Reemplazar Ventanas de Chars)

**Issues que resuelve**: Ventana 400 chars atributos (NLP-C2), ventana 500 chars emocional (NLP-M6), speaker matching exacto, cross-attribution entre entidades, dos enums de atributos (ARCH-H2)

**Consenso**: 11/11. Puede hacerse en paralelo con S-2.

**Qué cambia**:
- **Crear `nlp/scope_resolver.py`**: Utilidad con:
  - `sentence_scope(doc, token) -> Span`: oración que contiene el token
  - `paragraph_scope(doc, token) -> Span`: tokens entre `\n\n` más cercanos
  - `chapter_scope(chapters, token_idx) -> Chapter`
  - `find_subject_in_scope(doc, token) -> Optional[Span]`: dado un predicado, busca sujeto gramatical por dep tree
- **`nlp/attributes.py`**: Reemplazar TODA vinculación entity-atributo basada en proximidad con `scope_resolver.find_subject_in_scope()`. Consolidar los dos enums de atributos en uno solo.
- **Coherencia emocional**: Reemplazar ventana 500 chars con paragraph scope. Speaker matching con `morpho_utils.normalize_name()` (de S-2).

**Por qué genérico**: `ScopeResolver` es un componente reutilizable. Cualquier módulo que necesite "encontrar la entidad relevante para este elemento lingüístico" lo usa en vez de inventar su propia ventana de chars.

**Dependencias**: S-1. Se beneficia de S-2 pero puede desarrollarse en paralelo.

**Riesgo si se omite**: Cross-contaminación de atributos continúa. "Juan era alto. Pedro era bajo." dentro de 400 chars → ambas alturas asignadas a ambos. Usuarios pierden confianza.

---

### S-4 [P1]: Persistencia de Dismissals y Framework de Supresión

**Issues que resuelve**: Dismissals no persisten (UX-FP1), no hay whitelisting (UX-FP2), no hay batch (UX-f2), no hay métricas de precisión (UX-FP3)

**Consenso**: 10/11. PO inicialmente P2, cambió a P1 tras argumento del Editor.

**Qué cambia**:
- **`persistence/database.py`**: Tabla `dismissals` con `alert_hash`, `scope` (instancia/documento/proyecto/global), `reason`
- **`persistence/dismissal_repository.py`**: CRUD + `is_dismissed()`, `dismiss_batch()`, `get_dismissal_stats()`
- **`unified_analysis.py`**: Post-procesamiento que filtra alertas contra tabla de dismissals
- **API server**: Endpoints REST para dismiss, undismiss, batch dismiss, stats
- **Frontend**: Botón dismiss por alerta, checkbox batch, toggle "mostrar descartadas"
- **Tabla `suppression_rules`**: Patrones definidos por usuario (ej: "nunca flaggear 'como' en títulos de capítulo")

**Por qué genérico**: Framework funciona para TODOS los tipos de alerta. No arregla ningún detector — hace todos usables. Stats de dismissal informan qué detectores mejorar.

**Dependencias**: S-1.

**Riesgo si se omite**: Correctores pierden 30%+ del tiempo re-descartando. Sin datos de qué detectores generan más falsos positivos.

---

### S-5 [P1]: Memory Bounds y Procesamiento por Capítulos

**Issues que resuelve**: Memoria sin límite (ARCH-C2), performance (parcialmente), OOM en manuscritos largos

**Consenso**: 11/11.

**Qué cambia**:
- **`unified_analysis.py`**: Procesamiento capítulo por capítulo con paso de merge, en vez de documento completo en memoria
- **`nlp/chunking.py`**: Auditar y asegurar que se usa realmente
- **Monitorización de memoria**: Log de peak memory por fase
- **spaCy batching**: Usar `nlp.pipe()` con `batch_size` de config
- **`entities/fusion.py`**: Asegurar que fusión cross-chapter funciona

**Dependencias**: S-1, parcialmente S-3.

**Riesgo si se omite**: Herramienta no puede procesar manuscritos reales (novela 300 pags → OOM o 30+ min).

---

### S-6 [P1]: Formalización del Modelo de Datos de Capítulo

**Issues que resuelve**: Chapter es dict sin tipo (ARCH-H4), no hay campo para tipo de speech (NLP-M4), campos inconsistentes

**Qué cambia**:
- Crear dataclasses `Chapter`, `Segment`, `SpeechInstance` con campos tipados
- Migrar de `dict` a dataclass en todos los módulos
- Añadir `speech_type: Optional[SpeechType]` (DIRECT, INDIRECT, FREE_INDIRECT, NARRATION)

**Dependencias**: Coordinar con S-5.

---

### S-7 [P1]: Infraestructura de Tests para Medir Accuracy NLP

**Issues que resuelve**: 35-40% código sin tests, NER 13 tests, correferencia 7 tests, 13% recall sin forma de medir

**Qué cambia**:
- Tests unitarios para `morpho_utils.py` (S-2) y `scope_resolver.py` (S-3)
- **Harness de accuracy**: 5-10 pasajes anotados en español (500-1000 palabras cada uno) con gold standard para entidades, atributos, metáforas, speech, inconsistencias
- Harness reporta precision/recall/F1 por detector
- CI falla si recall baja de threshold (inicialmente 30%, subiendo)
- Tests para parsers PDF/EPUB — si no funcionan, marcar como no soportados

**Dependencias**: S-1. Se beneficia de S-2/S-3.

---

### S-8 [P2]: Navegación y Comparación en UI

**Issues que resuelve**: No hay scroll-to-text (UX-C4), no hay side-by-side (UX-C2), confidence no configurable (UX-C3)

**Qué cambia**:
- Backend: asegurar que todas las alertas incluyen `start_offset`, `end_offset`
- Frontend: click en alerta → scroll + highlight en document viewer
- Vista side-by-side para inconsistencias ("ojos verdes cap 2" vs "ojos azules cap 5")
- Slider de confidence threshold en settings

**Dependencias**: S-1, S-4, S-2.

---

### S-9 [P3]: Detección de Narrador No Fiable y Narrativa Avanzada

**Issues que resuelve**: No detecta narrador no fiable (NLP-M5), no distingue discurso libre indirecto (NLP-M4 parcial)

**Qué cambia**:
- Detección de tipo de speech con dep parsing + marcadores de cita
- Narrador no fiable vía LLM (Ollama) — tarea fundamentalmente semántica
- Marcadores de incertidumbre, distancia temporal, limitaciones cognitivas

**Dependencias**: S-2, S-3, S-5, S-6.

---

## Enfoques RECHAZADOS

| Enfoque | Por qué rechazado |
|---|---|
| **Expandir listas de verbos** | Overfit por definición. 20.000+ formas, cualquier verbo nuevo requiere cambio de código. spaCy los maneja todos con 0 mantenimiento. |
| **Regex para desambiguar "como"** | Overfit clásico. Necesitarías 20+ patrones. Un check de dependencia (`token.dep_`) maneja todos los casos. |
| **Aumentar ventana de chars (400→800)** | Empeora el problema. Mayor ventana = MÁS cross-attribution. La proximidad en chars no es proxy de relación gramatical. |
| **Analyzer morfológico custom (sin spaCy)** | Esfuerzo masivo, beneficio marginal. spaCy tiene 97% accuracy POS para español. |
| **Usar LLM para todo** | Performance 100-1000x más lento que spaCy. Output no determinista. LLM reservado para tareas semánticas (P3). |
| **Plugin architecture antes de arreglar detectores** | Abstracción prematura. Primero hacer que funcionen, luego abstraer. |
| **PostgreSQL en vez de SQLite** | Totalmente innecesario. La herramienta corre local. SQLite con WAL es perfecto. |
| **Clause-level parsing** | Dep parser de spaCy para español no es fiable para cláusulas. Sentence scope es suficiente y confiable para 90%+ de los casos. |

---

## Roadmap de Implementación

| Fase | Soluciones | Gate de calidad |
|---|---|---|
| **P0** | S-1 (Validación Pipeline), S-2 (Análisis Morfológico), S-3 (Scope Gramatical) | Recall > 40%, sin fallos silenciosos |
| **P1** | S-4 (Dismissals), S-5 (Memory), S-6 (Chapter Model), S-7 (Test Harness) | Manuscrito completo procesable, dismissals funcionando, recall medible |
| **P2** | S-8 (UX Navegación) | Workflow de usuario completo |
| **P3** | S-9 (Narrativa Avanzada) | Tipos de speech detectados, integración LLM |

**Métrica clave**: Recall debería pasar de 13% a >50% tras P0, y >70% tras P1 con el test harness proporcionando medición continua. El objetivo de 80% es alcanzable en P2 con tuning informado por datos de dismissals de S-4.

---

# Próximos Pasos

1. ✅ Revisión multi-experto completada (4/4 paneles)
2. ✅ Debate inter-expertos completado
3. ✅ Lista final de 9 soluciones genéricas priorizadas
4. ⏳ Implementación por prioridad (P0 → P1 → P2 → P3)
