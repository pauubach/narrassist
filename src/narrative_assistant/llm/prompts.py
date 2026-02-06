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

    # Rellenar template
    try:
        filled = template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Variable faltante en template: {e}")
        filled = template

    parts.append(filled)

    return "\n".join(parts)


# Registro de temperaturas recomendadas por tarea
RECOMMENDED_TEMPERATURES = {
    "character_analysis": 0.3,
    "violation_detection": 0.2,
    "alert_review": 0.1,
    "coreference": 0.2,
}
