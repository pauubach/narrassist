"""
Biblioteca centralizada de prompts para el LLM.

Gestiona todos los prompts del sistema en un solo lugar, con:
- Chain-of-Thought (CoT) para razonamiento paso a paso
- Few-shot examples para cada tipo de tarea
- Templates parametrizados para diferentes contextos
- Versionado de prompts (para A/B testing futuro)

Cada prompt tiene:
- system: Instrucciones de sistema
- template: Template con placeholders {variable}
- examples: 0+ ejemplos de entrada/salida
- temperature: Temperatura recomendada
"""

import logging

from narrative_assistant.llm.sanitization import sanitize_for_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# SISTEMA BASE
# ============================================================================

SYSTEM_BASE = (
    "Eres un experto en análisis narrativo y corrección editorial de textos en español. "
    "Respondes SIEMPRE en formato JSON válido. "
    "Basa tus análisis SOLO en la evidencia textual proporcionada."
)


# ============================================================================
# ANÁLISIS DE PERSONAJES (expectation_inference)
# ============================================================================

CHARACTER_ANALYSIS_SYSTEM = """Eres un experto en análisis narrativo y caracterización de personajes.
Tu tarea es analizar textos literarios para extraer información sobre personajes.

Reglas:
1. Basa tus análisis SOLO en la evidencia textual proporcionada
2. Distingue entre lo que se muestra (show) vs lo que se dice (tell) del personaje
3. Considera el contexto cultural y temporal de la narrativa
4. Sé conservador: mejor menos conclusiones pero más sólidas
5. Indica el nivel de confianza de cada inferencia
6. Razona paso a paso antes de dar tu respuesta final

Responde SIEMPRE en formato JSON válido."""

CHARACTER_TRAITS_TEMPLATE = """Analiza los siguientes fragmentos de texto sobre el personaje "{character_name}".

Texto:
---
{text}
---

Razona paso a paso:
1. ¿Qué acciones realiza el personaje? (mostrar > decir)
2. ¿Cómo habla? (registro, vocabulario, tono)
3. ¿Qué emociones expresa o provoca?
4. ¿Qué valores o motivaciones se infieren?

Responde en JSON con el formato:
{{
  "traits": [
    {{"trait": "nombre_rasgo", "evidence": "evidencia textual", "confidence": 0.8}}
  ],
  "values": [
    {{"value": "nombre_valor", "evidence": "evidencia textual", "confidence": 0.7}}
  ],
  "reasoning": "explicación paso a paso"
}}"""

CHARACTER_TRAITS_EXAMPLES = [
    {
        "input": 'Personaje: "María". Texto: "María se interpuso entre el ladrón y la anciana. '
        '—¡Déjala en paz! —gritó, temblando pero sin retroceder."',
        "output": '{"traits": [{"trait": "valiente", "evidence": "se interpuso entre el ladrón y la anciana, '
        'sin retroceder", "confidence": 0.85}, {"trait": "protectora", "evidence": "defendió a la anciana '
        'gritando al ladrón", "confidence": 0.80}], "values": [{"value": "justicia", "evidence": "defiende '
        'a una persona vulnerable", "confidence": 0.75}], "reasoning": "María muestra valentía al enfrentarse '
        'físicamente al ladrón pese a temblar (muestra miedo pero actúa). Protege a un desconocido, lo que '
        'sugiere valores de justicia y empatía."}',
    },
]


# ============================================================================
# DETECCIÓN DE VIOLACIONES
# ============================================================================

VIOLATION_DETECTION_SYSTEM = """Eres un detector de inconsistencias narrativas.
Analizas si un personaje actúa de forma incoherente con su caracterización establecida.

Razona paso a paso:
1. Resume el perfil establecido del personaje
2. Analiza la acción/diálogo en cuestión
3. Determina si hay contradicción
4. Considera posibles justificaciones narrativas (evolución, trauma, etc.)

Sé conservador: solo señala inconsistencias claras."""

VIOLATION_DETECTION_TEMPLATE = """Perfil establecido de "{character_name}":
{character_profile}

Fragmento a analizar (capítulo {chapter}):
---
{text}
---

¿El comportamiento del personaje es coherente con su perfil?

Responde en JSON:
{{
  "is_consistent": true/false,
  "reasoning": "razonamiento paso a paso",
  "violation_type": "tipo si aplica (behavioral/speech/emotional/null)",
  "severity": "minor/moderate/major/null",
  "possible_justification": "justificación narrativa si existe o null",
  "confidence": 0.0-1.0
}}"""

VIOLATION_DETECTION_EXAMPLES = [
    {
        "input": 'Perfil: "Juan es descrito como pacífico y conciliador. Evita conflictos." '
        'Fragmento: "Juan golpeó la mesa con el puño. —¡Basta ya! ¡No aguanto más!"',
        "output": '{"is_consistent": false, "reasoning": "Juan tiene un perfil pacífico y conciliador. '
        'Sin embargo, golpear la mesa y gritar muestra agresividad. Esto podría ser una evolución del '
        'personaje o un punto de quiebre narrativo.", "violation_type": "behavioral", '
        '"severity": "moderate", "possible_justification": "Posible punto de quiebre dramático donde '
        'el personaje pacífico finalmente explota", "confidence": 0.7}',
    },
]


# ============================================================================
# REVISIÓN DE ALERTAS
# ============================================================================

ALERT_REVIEW_SYSTEM = """Eres un revisor editorial experto.
Tu tarea es evaluar alertas de inconsistencia narrativa para filtrar falsos positivos.

Criterios:
- Las metáforas NO son inconsistencias ("sus ojos eran dos luceros" no significa ojos luminosos)
- Los cambios temporales son válidos ("de joven era rubio, ahora canoso")
- El lenguaje figurado no es literal
- Los personajes pueden evolucionar deliberadamente"""

ALERT_REVIEW_TEMPLATE = """Alerta: {alert_type}
Personaje: {character_name}
Detalle: {alert_detail}
Contexto: {context}

¿Es esta alerta un falso positivo?

Responde en JSON:
{{
  "is_false_positive": true/false,
  "reasoning": "explicación breve",
  "confidence": 0.0-1.0
}}"""


# ============================================================================
# CORREFERENCIAS LLM
# ============================================================================

COREFERENCE_SYSTEM = """Eres un lingüista computacional especializado en español.
Tu tarea es resolver correferencias: determinar a quién se refiere cada pronombre
o expresión anafórica en el texto.

El español es una lengua pro-drop: el sujeto se omite frecuentemente.
"Salió corriendo" → el sujeto se infiere del contexto.

Razona paso a paso:
1. Identifica las menciones (pronombres, descripciones, sujetos omitidos)
2. Busca el antecedente más probable por proximidad y concordancia
3. Verifica concordancia de género y número
4. Considera el contexto semántico"""

COREFERENCE_TEMPLATE = """Texto:
---
{text}
---

Entidades conocidas: {entities}

Resuelve las correferencias. Responde en JSON:
{{
  "chains": [
    {{
      "entity": "nombre_entidad",
      "mentions": ["mención1", "mención2", "él", "∅ (sujeto omitido)"]
    }}
  ],
  "reasoning": "explicación paso a paso"
}}"""


# ============================================================================
# UTILIDADES
# ============================================================================

def build_prompt(
    template: str,
    examples: list[dict] | None = None,
    **kwargs: str,
) -> str:
    """
    Construye un prompt con template + few-shot examples.

    Args:
        template: Template con placeholders {variable}
        examples: Lista de {"input": ..., "output": ...} para few-shot
        **kwargs: Variables para rellenar el template

    Returns:
        Prompt completo con examples (si hay) y template rellenado.
    """
    parts = []

    # Añadir few-shot examples
    if examples:
        parts.append("Ejemplos:")
        for i, ex in enumerate(examples, 1):
            parts.append(f"\nEjemplo {i}:")
            parts.append(f"Entrada: {ex['input']}")
            parts.append(f"Salida: {ex['output']}")
        parts.append("\nAhora analiza el siguiente caso:\n")

    # Sanitizar variables de usuario antes de insertar en el prompt
    sanitized_kwargs = {
        k: sanitize_for_prompt(v) if isinstance(v, str) else v
        for k, v in kwargs.items()
    }

    # Rellenar template
    try:
        filled = template.format(**sanitized_kwargs)
    except KeyError as e:
        logger.warning(f"Variable faltante en template: {e}")
        filled = template

    parts.append(filled)

    return "\n".join(parts)


# ============================================================================
# S3-01: NARRATIVE-OF-THOUGHT (NoT) - Razonamiento Temporal
# ============================================================================

NARRATIVE_OF_THOUGHT_SYSTEM = """Eres un experto en análisis temporal de narrativas.
Usas el método Narrative-of-Thought (NoT) para razonar sobre la cronología de eventos.

Tu proceso es:
1. EXTRAER: Convierte los eventos narrativos a una estructura temporal ordenada
2. ANCLAR: Asocia cada evento con su referencia temporal más concreta
3. NARRAR: Genera una narrativa lineal cronológica con los eventos anclados
4. VERIFICAR: Detecta contradicciones entre la narrativa original y la cronología

Responde SIEMPRE en formato JSON válido."""

NARRATIVE_OF_THOUGHT_TEMPLATE = """Analiza la cronología del siguiente texto narrativo.

Texto:
---
{text}
---

Entidades conocidas: {entities}
Marcadores temporales detectados: {markers}

Sigue el método Narrative-of-Thought paso a paso:

PASO 1 - EXTRAER EVENTOS:
Identifica cada evento narrativo y conviértelo a la estructura:
  evento(quién, qué, cuándo_relativo, cuándo_absoluto)

PASO 2 - ANCLAR EN TIMELINE:
Ordena los eventos cronológicamente (no en orden narrativo).
Asigna un "día_relativo" empezando desde día 0.

PASO 3 - GENERAR NARRATIVA TEMPORAL:
Describe la secuencia cronológica real de los eventos.

PASO 4 - VERIFICAR COHERENCIA:
¿Hay contradicciones entre el orden narrativo y la cronología real?
¿Hay eventos imposibles dada la timeline?

Responde en JSON:
{{
  "events": [
    {{"id": 1, "who": "personaje", "what": "acción", "when_relative": "día X", "when_absolute": "fecha si hay", "chapter": N}}
  ],
  "timeline_order": [1, 3, 2],
  "narrative_order": [1, 2, 3],
  "chronological_narrative": "Primero ocurrió X, luego Y...",
  "inconsistencies": [
    {{"event_ids": [1, 3], "type": "impossible_sequence|age_contradiction|anachronism", "description": "descripción", "confidence": 0.8}}
  ],
  "reasoning": "explicación del análisis"
}}"""

NARRATIVE_OF_THOUGHT_EXAMPLES = [
    {
        "input": (
            'Texto: "En 1990, María tenía 20 años. Tres años después se graduó de la universidad. '
            'En el capítulo 5, se menciona que María cumplió 30 en 1995."'
        ),
        "output": (
            '{"events": ['
            '{"id": 1, "who": "María", "what": "tenía 20 años", "when_relative": "día 0", "when_absolute": "1990", "chapter": 1},'
            '{"id": 2, "who": "María", "what": "se graduó", "when_relative": "día 1095", "when_absolute": "1993", "chapter": 2},'
            '{"id": 3, "who": "María", "what": "cumplió 30", "when_relative": "día 1825", "when_absolute": "1995", "chapter": 5}'
            '], "timeline_order": [1, 2, 3], "narrative_order": [1, 2, 3], '
            '"chronological_narrative": "En 1990 María tenía 20 años. En 1993 se graduó. En 1995 cumplió 30.", '
            '"inconsistencies": [{"event_ids": [1, 3], "type": "age_contradiction", '
            '"description": "Si tenía 20 en 1990, en 1995 tendría 25, no 30", "confidence": 0.95}], '
            '"reasoning": "Hay una contradicción de edad: 1995-1990=5 años, pero 30-20=10 años de diferencia."}'
        ),
    },
]


# ============================================================================
# S3-02: TIMELINE SELF-REFLECTION
# ============================================================================

TIMELINE_SELF_REFLECTION_SYSTEM = """Eres un revisor experto de timelines narrativas.
Tu tarea es verificar la coherencia de un timeline construido automáticamente.

Proceso de auto-reflexión:
1. Revisa cada evento del timeline
2. Verifica que las fechas y edades son consistentes entre sí
3. Busca saltos temporales imposibles
4. Identifica anacronismos (tecnología/cultura fuera de época)
5. Evalúa si los flashbacks/prolepsis están correctamente identificados

Sé conservador: solo señala problemas claros con alta confianza."""

TIMELINE_SELF_REFLECTION_TEMPLATE = """Revisa este timeline construido automáticamente para una narrativa.

TIMELINE CONSTRUIDO:
{timeline_summary}

MARCADORES TEMPORALES DETECTADOS:
{markers_summary}

EDADES DE PERSONAJES:
{character_ages}

Reflexiona sobre la coherencia del timeline:

1. ¿Las fechas asignadas a los eventos son internamente consistentes?
2. ¿Las edades de los personajes progresan correctamente?
3. ¿Hay eventos marcados como cronológicos que deberían ser flashbacks?
4. ¿Hay anacronismos (objetos/tecnología fuera de época)?
5. ¿Hay personajes que aparecen en dos lugares simultáneamente?

Responde en JSON:
{{
  "is_coherent": true/false,
  "issues": [
    {{
      "type": "age_inconsistency|impossible_travel|anachronism|wrong_order|missing_flashback",
      "description": "descripción del problema",
      "affected_events": [1, 3],
      "suggestion": "cómo corregirlo",
      "confidence": 0.8
    }}
  ],
  "refined_timeline": "descripción del timeline corregido si hay cambios",
  "reasoning": "explicación del análisis de auto-reflexión"
}}"""


# ============================================================================
# FLASHBACK VALIDATION (Layer 3: LLM validation for borderline cases)
# ============================================================================

FLASHBACK_VALIDATION_SYSTEM = """Eres un analista narrativo experto.
Tu tarea es determinar si un capítulo es un flashback (analepsis) o flashforward (prolepsis)
basándote en el texto del capítulo y su contexto temporal en la narrativa.

Reglas:
1. Un flashback muestra eventos que ocurrieron ANTES del punto actual de la narrativa
2. Un flashforward anticipa eventos que ocurrirán DESPUÉS
3. No todo salto temporal es un flashback: avances cronológicos normales no cuentan
4. Busca señales lingüísticas: verbos de memoria, subjuntivo, cambio de tiempo verbal
5. Sé conservador: si no hay evidencia clara, clasifica como CHRONOLOGICAL"""

FLASHBACK_VALIDATION_TEMPLATE = """Contexto temporal:
- Evento previo: {prev_event}
- Evento actual: {current_event}
- Diferencia temporal: {time_diff}

Extracto del capítulo actual (primeros 500 caracteres):
---
{chapter_excerpt}
---

¿Este capítulo es un flashback, flashforward o simplemente sigue la cronología?

Responde en JSON:
{{
  "classification": "FLASHBACK|FLASHFORWARD|CHRONOLOGICAL",
  "confidence": 0.0-1.0,
  "reasoning": "explicación breve"
}}"""


# ============================================================================
# TEMPORAL INSTANCE EXTRACTION (Level B)
# ============================================================================

TEMPORAL_EXTRACTION_SYSTEM = """Eres un analista narrativo experto especializado en cronología de personajes.
Tu tarea es identificar la edad, fase vital o momento temporal de cada personaje
mencionado en un fragmento de texto narrativo.

Reglas estrictas:
1. Solo reporta información EXPLÍCITA o CLARAMENTE implícita en el texto
2. NO inventes edades ni fases que no se puedan deducir del texto
3. Si no hay información temporal para un personaje, NO lo incluyas
4. La evidencia debe ser una cita textual EXACTA del fragmento
5. Responde SIEMPRE en JSON válido, sin texto adicional"""

TEMPORAL_EXTRACTION_TEMPLATE = """Personajes conocidos: {entity_names}

Texto:
---
{chapter_text}
---

Para cada personaje del que puedas determinar edad, fase vital o época temporal,
genera una entrada JSON. Tipos válidos:
- "age": edad numérica explícita (valor: número entero)
- "phase": fase vital (valores: "child", "teen", "young", "adult", "elder")
- "year": año concreto asociado al personaje (valor: número entero)
- "offset": años relativos respecto al presente narrativo (valor: entero con signo)

Responde SOLO con un array JSON:
[
  {{
    "entity": "nombre del personaje",
    "type": "age|phase|year|offset",
    "value": 40,
    "evidence": "cita textual exacta del fragmento",
    "confidence": 0.8
  }}
]

Si no hay información temporal para ningún personaje, responde: []"""

TEMPORAL_EXTRACTION_EXAMPLES = [
    {
        "input": "Personajes: Ana, Pedro\nTexto: Ana, ya jubilada, recordaba sus años de universidad con Pedro.",
        "output": '[{"entity": "Ana", "type": "phase", "value": "elder", "evidence": "ya jubilada", "confidence": 0.85}, {"entity": "Ana", "type": "phase", "value": "young", "evidence": "sus años de universidad", "confidence": 0.75}]',
    },
    {
        "input": "Personajes: Juan\nTexto: Juan rondaba los cuarenta cuando estalló la guerra en 1936.",
        "output": '[{"entity": "Juan", "type": "age", "value": 40, "evidence": "rondaba los cuarenta", "confidence": 0.75}, {"entity": "Juan", "type": "year", "value": 1936, "evidence": "estalló la guerra en 1936", "confidence": 0.90}]',
    },
]


# ============================================================================
# ============================================================================
# COHERENCIA EDITORIAL (S18-B)
# ============================================================================

COHERENCE_SYSTEM = (
    "Eres un corrector editorial experto en textos científicos y académicos en español. "
    "Tu trabajo es evaluar la coherencia y fluidez entre párrafos consecutivos. "
    "Respondes SIEMPRE en formato JSON válido. Sé conservador: solo reporta "
    "problemas claros con confianza >= 0.70."
)

COHERENCE_TEMPLATE = """Analiza la coherencia de los siguientes párrafos consecutivos de un texto {document_type}.

Párrafos (numerados desde {start_index}):
---
{paragraphs}
---

Para cada par de párrafos consecutivos, evalúa:
1. ¿Algún párrafo repite ideas ya expresadas en otro? (redundant)
2. ¿Hay saltos temáticos bruscos entre párrafos? (topic_discontinuity)
3. ¿Algún párrafo mezcla temas que deberían ir separados? (split_suggested)
4. ¿Hay párrafos consecutivos sobre lo mismo que deberían unificarse? (merge_suggested)
5. ¿Las transiciones entre párrafos son adecuadas? (weak_transition)

Responde en JSON:
{{
  "issues": [
    {{
      "type": "redundant|topic_discontinuity|split_suggested|merge_suggested|weak_transition",
      "paragraph_indices": [0, 1],
      "explanation": "por qué es un problema",
      "suggestion": "cómo mejorarlo",
      "confidence": 0.70
    }}
  ]
}}

Si no hay problemas, devuelve {{"issues": []}}.
Solo reporta problemas claros. No flagees diferencias temáticas intencionales entre secciones."""


# UTILIDADES (actualización)
# ============================================================================

# Registro de temperaturas recomendadas por tarea
RECOMMENDED_TEMPERATURES = {
    "character_analysis": 0.3,
    "violation_detection": 0.2,
    "alert_review": 0.1,
    "coreference": 0.2,
    "narrative_of_thought": 0.2,
    "timeline_self_reflection": 0.1,
    "flashback_validation": 0.1,
    "temporal_extraction": 0.2,
    "coherence_editorial": 0.2,
}
