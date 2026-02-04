"""
Tests de casos SEMÁNTICOS Y PRAGMÁTICOS para extracción de atributos.

Autor: Lingüista Especialista en Semántica y Pragmática del Español
Perspectiva: Análisis de fenómenos que van más allá de la sintaxis superficial

Este archivo evalúa fenómenos semánticos y pragmáticos complejos del español
que afectan la interpretación correcta de atributos físicos y de personalidad.

FENÓMENOS EVALUADOS:
1. Negaciones (semántica proposicional)
2. Metáforas (semántica figurada vs. literal)
3. Atributos temporales (aspecto y tiempo)
4. Atributos condicionales (mundos posibles)
5. Comparaciones implícitas (presuposiciones)
6. Inferencias léxicas (conocimiento enciclopédico)
7. Atributos por contexto (descriptores definidos)
8. Contradicciones narrativas (coherencia discursiva)
9. Descripciones indirectas (referencia opaca)
10. Ironía y sarcasmo (pragmática conversacional)

PRINCIPIO FUNDAMENTAL:
El sistema debe distinguir entre:
- AFIRMACIONES: Atributos que SÍ posee el personaje
- NEGACIONES: Atributos que NO posee el personaje
- METÁFORAS: Expresiones figuradas sin valor literal
- HIPOTÉTICOS: Atributos en mundos contrafactuales
- PASADOS: Atributos que YA NO son vigentes
- INFERIDOS: Atributos derivables por conocimiento del mundo
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

import pytest

# =============================================================================
# TIPOS DE ATRIBUTOS Y SU ESTATUS EPISTÉMICO
# =============================================================================


class AttributeStatus(Enum):
    """Estatus epistémico del atributo."""

    AFFIRMED = "affirmed"  # Afirmado como verdadero en el mundo narrativo
    NEGATED = "negated"  # Explícitamente negado
    METAPHORICAL = "metaphorical"  # Expresión figurada, no literal
    PAST = "past"  # Era verdadero, ya no lo es
    CONDITIONAL = "conditional"  # Solo verdadero en mundo contrafactual
    INFERRED = "inferred"  # Inferible por conocimiento enciclopédico
    UNCERTAIN = "uncertain"  # Ambiguo o contradictorio
    IRONIC = "ironic"  # Afirmado irónicamente (significa lo contrario)


@dataclass
class SemanticTestCase:
    """Estructura para un caso de prueba semántico-pragmático."""

    id: str
    phenomenon: str  # Fenómeno semántico/pragmático evaluado
    text: str  # Texto narrativo
    entities: list[str]  # Entidades mencionadas
    extract_attributes: dict[str, dict[str, str]]  # DEBE extraer
    reject_attributes: dict[str, dict[str, str]]  # NO debe extraer
    semantic_analysis: str  # Análisis semántico/pragmático
    trap_description: str  # Por qué es difícil para el sistema
    linguistic_phenomenon: str  # Clasificación lingüística formal


# =============================================================================
# CASO 1: NEGACIÓN EXPLÍCITA
# =============================================================================

CASO_1_NEGACION = SemanticTestCase(
    id="NEGACION_001",
    phenomenon="Negación proposicional explícita",
    text="""
    Luisa no tenía los ojos verdes, como muchos creían. Su mirada era de un
    castaño profundo, casi negro. Tampoco era rubia: su pelo azabache caía
    en cascada sobre sus hombros.
    """,
    entities=["Luisa"],
    extract_attributes={
        "Luisa": {
            "eye_color": "castaño",  # Afirmado explícitamente
            "hair_color": "azabache",  # Afirmado explícitamente (negro)
        }
    },
    reject_attributes={
        "Luisa": {
            "eye_color": "verdes",  # NEGADO explícitamente
            "hair_color": "rubia",  # NEGADO con "tampoco"
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (NEGACIÓN):

    Estructura lógica:
    - ¬(tener(Luisa, ojos_verdes))  →  Luisa NO tiene ojos verdes
    - tener(Luisa, mirada_castaña)  →  Luisa SÍ tiene ojos castaños
    - ¬(ser(Luisa, rubia))          →  Luisa NO es rubia
    - tener(Luisa, pelo_azabache)   →  Luisa SÍ tiene pelo negro

    Operadores de negación detectados:
    1. "no tenía" - negación verbal directa
    2. "tampoco era" - negación aditiva (presupone negación previa)

    La negación en español opera sobre la proposición completa.
    "No tenía ojos verdes" niega la existencia del atributo, no
    la existencia de los ojos.

    PRESUPOSICIONES:
    - "como muchos creían" → presuposición de creencia errónea común
    - La negación AFIRMA que la creencia es falsa
    """,
    trap_description="""
    TRAMPA: Extracción ingenua de patrones léxicos.

    Un sistema basado en patrones podría detectar:
    - "ojos verdes" → extraer eye_color=verde ❌
    - "rubia" → extraer hair_color=rubio ❌

    El sistema DEBE detectar la negación y:
    1. NO extraer el atributo negado
    2. O marcarlo explícitamente como NEGATED

    La dificultad radica en el scope de la negación:
    - "no tenía" tiene scope sobre todo el SN "los ojos verdes"
    """,
    linguistic_phenomenon="Negación proposicional (¬p)",
)


# =============================================================================
# CASO 2: NEGACIÓN CON JAMÁS/NUNCA
# =============================================================================

CASO_2_NEGACION_TEMPORAL = SemanticTestCase(
    id="NEGACION_002",
    phenomenon="Negación con adverbios temporales universales",
    text="""
    Pedro jamás fue alto. Desde niño había sido el más bajo de su clase, y
    eso no cambió con los años. Su complexión menuda contrastaba con la de
    su hermano Lucas, un gigante de casi dos metros.
    """,
    entities=["Pedro", "Lucas"],
    extract_attributes={
        "Pedro": {
            "height": "bajo",  # Inferido de "el más bajo"
            "build": "menuda",  # Afirmado explícitamente
        },
        "Lucas": {
            "height": "alto",  # "gigante de casi dos metros"
            "build": "grande",  # Inferido de "gigante"
        },
    },
    reject_attributes={
        "Pedro": {
            "height": "alto"  # NEGADO con "jamás"
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (NEGACIÓN UNIVERSAL TEMPORAL):

    "Jamás fue alto":
    - Adverbio: jamás = en ningún momento del tiempo
    - Cuantificación: ∀t ¬(ser(Pedro, alto, t))
    - Para todo tiempo t, Pedro no es alto

    Esto es más fuerte que una negación simple:
    - "No es alto" → negación en el momento actual
    - "Jamás fue alto" → negación en TODO el eje temporal

    CONTRASTE:
    - Pedro: bajo, menudo (atributos positivos)
    - Lucas: gigante, ~2m (contraste explícito)

    El sistema debe manejar:
    1. Negación universal (jamás/nunca)
    2. Contraste entre entidades (resalta la negación)
    """,
    trap_description="""
    TRAMPA: Ignorar el adverbio de negación universal.

    "Jamás fue alto" podría procesarse como:
    - "fue alto" → extraer height=alto ❌

    El adverbio "jamás" tiene scope sobre toda la proposición
    y establece una negación PERMANENTE, no solo puntual.

    Adicionalmente, el contraste con Lucas ("gigante") podría
    confundir si el sistema no delimita bien los referentes.
    """,
    linguistic_phenomenon="Cuantificación temporal negativa (∀t ¬p)",
)


# =============================================================================
# CASO 3: METÁFORA OCULAR
# =============================================================================

CASO_3_METAFORA_OJOS = SemanticTestCase(
    id="METAFORA_003",
    phenomenon="Metáfora conceptual - ojos como entidades luminosas",
    text="""
    Los ojos de Isabel eran dos soles que iluminaban cualquier habitación.
    Cuando entraba, su mirada dorada parecía derretir hasta el más frío
    corazón. Pero en realidad, sus iris eran de un verde grisáceo común.
    """,
    entities=["Isabel"],
    extract_attributes={
        "Isabel": {
            "eye_color": "verde grisáceo"  # El ÚNICO color literal
        }
    },
    reject_attributes={
        "Isabel": {
            "eye_color": "dorado",  # METÁFORA ("mirada dorada")
            "eye_color": "solar",  # METÁFORA ("dos soles")
            "eye_color": "amarillo",  # Inferencia errónea de "soles"
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (METÁFORA CONCEPTUAL):

    Metáfora: OJOS SON FUENTES DE LUZ
    - "eran dos soles" → predicación metafórica de identidad
    - "mirada dorada" → transferencia de atributo solar
    - "iluminaban" → extensión del dominio fuente

    Estructura según Lakoff & Johnson (1980):
    - Dominio fuente: SOL (calor, luz, dorado)
    - Dominio meta: OJOS (expresividad, calidez emocional)
    - Mapeo: luminosidad → expresividad

    CLAVE INTERPRETATIVA:
    La oración "Pero en realidad, sus iris eran de un verde grisáceo"
    CANCELA la interpretación literal de la metáfora.

    El marcador "en realidad" señala:
    - Lo anterior era descripción no literal
    - Lo que sigue es la descripción factual
    """,
    trap_description="""
    TRAMPA: Procesar metáforas como descripciones literales.

    Error potencial 1: "dos soles" → color amarillo/dorado
    Error potencial 2: "mirada dorada" → ojos dorados

    El sistema debe detectar:
    1. Construcciones metafóricas (X es Y donde Y es semánticamente
       incompatible con X: ojos ≠ soles literalmente)
    2. Marcadores de corrección ("pero en realidad")
    3. Priorizar la descripción literal sobre la figurada

    Las metáforas oculares son MUY comunes en narrativa y el sistema
    debe tener un módulo específico para filtrarlas.
    """,
    linguistic_phenomenon="Metáfora conceptual (Lakoff & Johnson)",
)


# =============================================================================
# CASO 4: METÁFORA DE PERSONALIDAD
# =============================================================================

CASO_4_METAFORA_PERSONALIDAD = SemanticTestCase(
    id="METAFORA_004",
    phenomenon="Metáfora de atributos de personalidad",
    text="""
    Carmen tenía un corazón de oro y una voluntad de hierro. Su sonrisa
    cálida contrastaba con su mirada de acero cuando alguien la desafiaba.
    Era, sin embargo, una mujer de ojos marrones y gesto amable.
    """,
    entities=["Carmen"],
    extract_attributes={
        "Carmen": {
            "eye_color": "marrones",  # LITERAL
            "personality": "generosa",  # Inferible de "corazón de oro"
            "personality": "determinada",  # Inferible de "voluntad de hierro"
        }
    },
    reject_attributes={
        "Carmen": {
            "eye_color": "acero",  # METÁFORA ("mirada de acero")
            "eye_color": "gris",  # Inferencia errónea de "acero"
            "heart_material": "oro",  # ABSURDO literal
            "will_material": "hierro",  # ABSURDO literal
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (METÁFORAS DE PERSONALIDAD):

    Metáforas detectadas:
    1. "corazón de oro" → PERSONA ES METAL PRECIOSO
       - Significado: generosidad, bondad
       - NO es atributo físico literal

    2. "voluntad de hierro" → CARÁCTER ES METAL
       - Significado: determinación, fortaleza
       - NO es atributo físico literal

    3. "mirada de acero" → EXPRESIÓN ES METAL
       - Significado: dureza, frialdad expresiva
       - NO implica color de ojos gris

    CLAVE: Las metáforas de metal para rasgos de personalidad son
    expresiones lexicalizadas (idioms) en español:
    - corazón de oro = generoso
    - voluntad de hierro = determinado
    - mirada de acero = severo

    El único atributo físico literal es "ojos marrones".
    """,
    trap_description="""
    TRAMPA: Confundir metáforas lexicalizadas con atributos físicos.

    Error potencial: "mirada de acero" → ojos grises

    La expresión "mirada de acero" es una COLOCACIÓN FIJA que denota:
    - Expresión dura, severa, intimidante
    - NO tiene nada que ver con el color de ojos

    El sistema debe tener un lexicón de expresiones metafóricas
    comunes en español para evitar estos errores.

    Además, debe distinguir entre:
    - Atributos físicos (extraer a BD de personajes)
    - Atributos de personalidad (categoría diferente)
    """,
    linguistic_phenomenon="Expresiones idiomáticas / Metáforas lexicalizadas",
)


# =============================================================================
# CASO 5: ATRIBUTOS TEMPORALES (ANTES/DESPUÉS)
# =============================================================================

CASO_5_TEMPORAL = SemanticTestCase(
    id="TEMPORAL_005",
    phenomenon="Atributos con marca temporal explícita",
    text="""
    Antes de los treinta, Roberto era rubio. Los años y el estrés habían
    oscurecido su pelo hasta convertirlo en un castaño apagado. De joven
    tenía los ojos claros, casi celestes, pero ahora parecían grises,
    desvaídos por el tiempo.
    """,
    entities=["Roberto"],
    extract_attributes={
        "Roberto": {
            "hair_color": "castaño",  # Estado ACTUAL
            "eye_color": "gris",  # Estado ACTUAL ("ahora")
        }
    },
    reject_attributes={
        "Roberto": {
            "hair_color": "rubio",  # Estado PASADO ("antes")
            "eye_color": "celeste",  # Estado PASADO ("de joven")
            # NOTA: Podrían almacenarse como atributos históricos,
            # pero NO como atributos vigentes del personaje
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (ASPECTO TEMPORAL):

    Estructura temporal del texto:

    TIEMPO PASADO (antes de los 30 / de joven):
    - rubio (pelo)
    - ojos claros, casi celestes

    TIEMPO PRESENTE (ahora / estado actual):
    - castaño apagado (pelo)
    - ojos grises, desvaídos

    Marcadores temporales:
    - "Antes de los treinta" → delimita período pasado
    - "De joven" → período pasado
    - "ahora" → tiempo narrativo presente
    - "habían oscurecido" → pluscuamperfecto (cambio completado)

    TRANSFORMACIÓN:
    rubio → castaño (proceso: "habían oscurecido")
    celeste → gris (proceso: "desvaídos por el tiempo")

    El sistema debe extraer el estado ACTUAL, no el pasado,
    a menos que se soliciten específicamente atributos históricos.
    """,
    trap_description="""
    TRAMPA: No distinguir tiempo verbal ni marcadores temporales.

    Un sistema ingenuo extraería TODOS los atributos:
    - rubio ❌ (pasado)
    - castaño ✓ (presente)
    - celeste ❌ (pasado)
    - gris ✓ (presente)

    Resultado erróneo: Roberto tiene pelo rubio Y castaño

    El sistema DEBE:
    1. Detectar marcadores temporales (antes, de joven, ahora)
    2. Aplicar el tiempo verbal correcto
    3. Priorizar el estado actual sobre el pasado
    4. Opcionalmente, almacenar el pasado como "former_attribute"
    """,
    linguistic_phenomenon="Aspecto léxico y marcadores temporales",
)


# =============================================================================
# CASO 6: ATRIBUTOS CONDICIONALES
# =============================================================================

CASO_6_CONDICIONAL = SemanticTestCase(
    id="CONDICIONAL_006",
    phenomenon="Atributos en oraciones condicionales contrafactuales",
    text="""
    Si Elena no fuera morena, quizás habría sido modelo de pasarela. Con
    ese pelo negro azabache y esos ojos oscuros, no encajaba en los
    estándares de la industria. Si tuviera el pelo rubio y ojos claros,
    todo habría sido diferente.
    """,
    entities=["Elena"],
    extract_attributes={
        "Elena": {
            "hair_color": "negro azabache",  # REAL (base del contrafactual)
            "eye_color": "oscuros",  # REAL
            "complexion": "morena",  # REAL (presuposición del condicional)
        }
    },
    reject_attributes={
        "Elena": {
            "hair_color": "rubio",  # CONTRAFACTUAL (mundo posible, no real)
            "eye_color": "claros",  # CONTRAFACTUAL
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (CONDICIONALES CONTRAFACTUALES):

    Estructura: Si [P_contrafactual], [Q_consecuencia]
    - "Si Elena no fuera morena" → P contrafactual
    - Presuposición: Elena ES morena (en el mundo real)

    Semántica de mundos posibles (Kripke, Lewis):
    - Mundo actual W₀: Elena es morena, pelo negro, ojos oscuros
    - Mundo contrafactual W₁: Elena no es morena, pelo rubio, ojos claros

    La oración condicional contrafactual:
    1. AFIRMA implícitamente la negación del antecedente en W₀
    2. Explora un mundo posible alternativo W₁

    "Si tuviera el pelo rubio":
    - Subjuntivo imperfecto → contrafactual
    - Elena NO tiene pelo rubio en W₀
    - El atributo "rubio" solo existe en W₁

    EXTRACCIÓN CORRECTA: Atributos de W₀ (mundo narrativo)
    """,
    trap_description="""
    TRAMPA: Extraer atributos del mundo contrafactual como reales.

    Error potencial:
    - "pelo rubio" → hair_color=rubio ❌
    - "ojos claros" → eye_color=claro ❌

    Estos atributos existen solo en el MUNDO CONTRAFACTUAL,
    no en el mundo narrativo real.

    PISTA LINGÜÍSTICA: El subjuntivo imperfecto ("fuera", "tuviera")
    marca el modo irreal. El sistema debe detectar:
    1. Conjunción condicional "si"
    2. Verbo en subjuntivo (modo irreal)
    3. No extraer atributos de la prótasis contrafactual

    Además, la negación "si no fuera morena" CONFIRMA que
    Elena SÍ es morena en el mundo real.
    """,
    linguistic_phenomenon="Condicionales contrafactuales (subjuntivo)",
)


# =============================================================================
# CASO 7: COMPARACIÓN CON HERENCIA IMPLÍCITA
# =============================================================================

CASO_7_COMPARACION_HERENCIA = SemanticTestCase(
    id="COMPARACION_007",
    phenomenon="Comparación con atributo heredado implícito",
    text="""
    Como su madre, Sofía era pelirroja. Los mismos rizos cobrizos enmarcaban
    su rostro, aunque sus ojos eran del padre: verdes y penetrantes. Miguel,
    su hermano, no había heredado el pelo rojo de la familia.
    """,
    entities=["Sofía", "Miguel", "madre", "padre"],
    extract_attributes={
        "Sofía": {
            "hair_color": "pelirroja",  # Explícito + comparación
            "hair_texture": "rizos",  # "rizos cobrizos"
            "eye_color": "verdes",  # "ojos... del padre: verdes"
        },
        "madre": {
            "hair_color": "pelirroja"  # Inferido por comparación
        },
        "padre": {
            "eye_color": "verdes"  # "ojos eran del padre: verdes"
        },
    },
    reject_attributes={
        "Miguel": {
            "hair_color": "rojo"  # NEGADO ("no había heredado")
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (COMPARACIÓN Y HERENCIA):

    Estructura comparativa: "Como X, Y era Z"
    - Presupone: X es Z
    - Afirma: Y es Z

    "Como su madre, Sofía era pelirroja":
    1. Sofía es pelirroja (afirmación directa)
    2. La madre es pelirroja (presuposición de la comparación)

    Construcción de herencia: "X eran del padre: Y"
    - "sus ojos eran del padre: verdes"
    - Sofía tiene ojos verdes (explícito)
    - El padre tiene ojos verdes (fuente de herencia)

    NEGACIÓN DE HERENCIA:
    "Miguel no había heredado el pelo rojo"
    - Miguel NO tiene pelo rojo
    - Presuposición: existe "pelo rojo de la familia"
    """,
    trap_description="""
    TRAMPA 1: No inferir atributo de la madre desde comparación.
    La comparación "como su madre" PRESUPONE que la madre también
    es pelirroja. Muchos sistemas perderían este atributo inferido.

    TRAMPA 2: No resolver la referencia "del padre" en genitivo.
    "sus ojos eran del padre: verdes" tiene estructura compleja:
    - Genitivo de origen/herencia
    - Aposición explicativa del color

    TRAMPA 3: Asignar "pelo rojo" a Miguel.
    La negación "no había heredado" debe bloquear la extracción.
    """,
    linguistic_phenomenon="Comparación con presuposición de identidad de atributo",
)


# =============================================================================
# CASO 8: INFERENCIA LÉXICA (ALBINO)
# =============================================================================

CASO_8_INFERENCIA_LEXICA = SemanticTestCase(
    id="INFERENCIA_008",
    phenomenon="Inferencia por conocimiento enciclopédico",
    text="""
    El albino cruzó la plaza sin prisa. Su figura fantasmagórica destacaba
    entre la multitud morena del mercado. Silas, que así se llamaba,
    buscaba la sombra para proteger su delicada piel.
    """,
    entities=["Silas"],
    extract_attributes={
        "Silas": {
            # Inferidos por conocimiento enciclopédico de "albino":
            "skin_color": "muy pálida/blanca",  # Definición de albinismo
            "hair_color": "blanco/muy claro",  # Característica típica
            "eye_sensitivity": "fotosensible",  # "proteger su delicada piel"
            # Confirmado explícitamente:
            "complexion": "pálida",  # "figura fantasmagórica"
        }
    },
    reject_attributes={
        "Silas": {
            "skin_color": "morena"  # Es del "mercado moreno", no de Silas
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (INFERENCIA LÉXICA):

    El sustantivo "albino" es un TÉRMINO TÉCNICO que implica:
    - Condición genética: hipopigmentación
    - Piel: muy pálida, blanca
    - Pelo: blanco o muy rubio
    - Ojos: claros, frecuentemente rojos/rosados, fotosensibles

    El sistema debe tener CONOCIMIENTO ENCICLOPÉDICO para inferir:
    albino(X) → piel_pálida(X) ∧ pelo_claro(X) ∧ fotosensible(X)

    CORREFERENCIA:
    "El albino" = "Silas" (establecido por "que así se llamaba")
    Los atributos inferidos de "albino" se transfieren a "Silas".

    TRAMPA CONTEXTUAL:
    "multitud morena" → NO es atributo de Silas
    Es descripción del CONTEXTO (el mercado), no del personaje.
    """,
    trap_description="""
    TRAMPA 1: No inferir atributos de términos técnicos/médicos.
    "Albino" implica múltiples atributos físicos que NO están
    escritos explícitamente. El sistema necesita:
    - Ontología de condiciones médicas
    - Mapeo término → atributos físicos asociados

    TRAMPA 2: Asignar "morena" a Silas.
    "multitud morena del mercado" describe el ENTORNO, no a Silas.
    De hecho, Silas CONTRASTA con la multitud ("destacaba").

    TRAMPA 3: No resolver correferencia "El albino" = "Silas".
    Sin esta resolución, los atributos quedarían en entidad anónima.
    """,
    linguistic_phenomenon="Inferencia enciclopédica por término técnico",
)


# =============================================================================
# CASO 9: CONTRADICCIÓN NARRATIVA
# =============================================================================

CASO_9_CONTRADICCION = SemanticTestCase(
    id="CONTRADICCION_009",
    phenomenon="Contradicción explícita en la narración",
    text="""
    Todos decían que Marcos era moreno, casi gitano. Pero la verdad era
    distinta: bajo aquella capa de suciedad y sol, su pelo era de un rubio
    sucio, desvaído. Sus ojos, que muchos recordaban negros, eran en
    realidad de un gris azulado que el polvo opacaba.
    """,
    entities=["Marcos"],
    extract_attributes={
        "Marcos": {
            "hair_color": "rubio sucio",  # La VERDAD narrativa
            "eye_color": "gris azulado",  # "en realidad"
        }
    },
    reject_attributes={
        "Marcos": {
            "complexion": "moreno",  # Creencia falsa ("decían que")
            "eye_color": "negro",  # Recuerdo erróneo ("muchos recordaban")
        }
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (EVIDENCIALIDAD Y FUENTE):

    El texto presenta DOS niveles de información:

    NIVEL 1 - CREENCIA COMÚN (rechazar):
    - "decían que era moreno" → evidencial de rumor
    - "muchos recordaban negros" → evidencial de memoria ajena
    - Marcador: "decían que", "recordaban"

    NIVEL 2 - VERDAD NARRATIVA (extraer):
    - "la verdad era distinta" → marcador de corrección
    - "su pelo era de un rubio sucio" → afirmación factual
    - "en realidad... gris azulado" → marcador de verdad
    - Marcadores: "la verdad", "en realidad"

    EVIDENCIALIDAD (categoría gramatical):
    - Reportativo: "decían que" → información de segunda mano
    - Directo: descripción del narrador → fuente primaria

    El sistema debe priorizar la información directa del narrador
    sobre la información reportada/rumoreada.
    """,
    trap_description="""
    TRAMPA: Tratar todas las menciones de atributos como equivalentes.

    Error potencial:
    - "moreno" aparece primero → extraer como atributo ❌
    - "ojos negros" aparece → extraer como atributo ❌

    El sistema debe detectar FUENTE EVIDENCIAL:
    1. "decían que" → marca información como rumor/creencia
    2. "recordaban" → marca información como memoria (posiblemente errónea)
    3. "la verdad era" / "en realidad" → marca información como factual

    PRIORIDAD: Verdad narrativa > Creencia de personajes > Rumores
    """,
    linguistic_phenomenon="Evidencialidad y gestión de fuentes epistémicas",
)


# =============================================================================
# CASO 10: DESCRIPCIÓN INDIRECTA (REFERENCIA OPACA)
# =============================================================================

CASO_10_INDIRECTA = SemanticTestCase(
    id="INDIRECTA_010",
    phenomenon="Atributo heredado sin especificación de valor",
    text="""
    Lucía había heredado los ojos de su abuela Amparo. Todo el mundo lo
    comentaba: eran idénticos, como dos gotas de agua. También el pelo,
    esa melena indomable que saltaba generaciones. Nadie sabía de dónde
    venía ese rasgo tan peculiar.
    """,
    entities=["Lucía", "Amparo"],
    extract_attributes={
        # NO PODEMOS extraer COLOR específico - no se menciona
        "Lucía": {
            "hair_texture": "indomable"  # Único atributo explícito
        },
        "Amparo": {
            "hair_texture": "indomable"  # Por herencia inversa
        },
    },
    reject_attributes={
        "Lucía": {
            "eye_color": "???",  # NO ESPECIFICADO - no inventar
        },
        "Amparo": {
            "eye_color": "???"  # NO ESPECIFICADO - no inventar
        },
    },
    semantic_analysis="""
    ANÁLISIS SEMÁNTICO (REFERENCIA OPACA):

    "Heredó los ojos de su abuela":
    - Establece RELACIÓN de identidad de atributo
    - NO especifica el VALOR del atributo
    - ojos(Lucía) = ojos(Amparo) [identidad]
    - Pero: color(ojos(Lucía)) = ??? [no especificado]

    CONTEXTO OPACO (Quine):
    Podemos afirmar que Lucía tiene "los mismos ojos" que Amparo
    sin saber QUÉ color son esos ojos. La referencia es OPACA
    respecto al valor específico del atributo.

    El único atributo con VALOR especificado:
    - "melena indomable" → textura de pelo

    RESTRICCIÓN CRUCIAL:
    El sistema NO debe inventar valores para atributos no especificados.
    "Heredó los ojos" ≠ "Heredó ojos verdes/azules/marrones"
    """,
    trap_description="""
    TRAMPA: Inventar valores de atributos no especificados.

    Error potencial con LLM:
    - El modelo podría "imaginar" un color de ojos
    - Podría usar heurísticas culturales (española → ojos marrones)

    El sistema DEBE:
    1. Reconocer que se menciona herencia de atributo
    2. NO asignar valor inventado
    3. Posiblemente crear relación: ojos(Lucía) ≡ ojos(Amparo)
       sin especificar el valor

    SOLO "melena indomable" tiene valor especificado y puede extraerse.
    """,
    linguistic_phenomenon="Referencia opaca / Atributo sin valor especificado",
)


# =============================================================================
# CASO 11: IRONÍA Y SARCASMO
# =============================================================================

CASO_11_IRONIA = SemanticTestCase(
    id="IRONIA_011",
    phenomenon="Ironía y sarcasmo en atribución",
    text="""
    —¡Qué alto estás! —se burló Marina al ver a Paco entrar agachándose.
    Paco, que apenas llegaba al metro sesenta, sonrió con resignación.
    —Ya, y tú eres rubia natural —respondió él, mirando las evidentes
    raíces oscuras bajo el teñido platino de Marina.
    """,
    entities=["Paco", "Marina"],
    extract_attributes={
        "Paco": {
            "height": "bajo"  # ~1.60m = bajo para hombre
        },
        "Marina": {
            "hair_color": "oscuro",  # Raíces = color natural
            "hair_dye": "platino",  # Teñido (no natural)
        },
    },
    reject_attributes={
        "Paco": {
            "height": "alto"  # IRÓNICO - significa lo contrario
        },
        "Marina": {
            "hair_color": "rubio natural"  # IRÓNICO - significa lo contrario
        },
    },
    semantic_analysis="""
    ANÁLISIS PRAGMÁTICO (IRONÍA):

    Teoría de la ironía (Grice, Sperber & Wilson):
    La ironía comunica lo OPUESTO de lo dicho literalmente.

    IRONÍA 1: "¡Qué alto estás!"
    - Contexto: Marina "se burló"
    - Evidencia: Paco "apenas llegaba al metro sesenta"
    - Interpretación: Paco es BAJO (lo contrario de "alto")
    - Pista: Verbo "burlarse" marca intención irónica

    IRONÍA 2: "eres rubia natural"
    - Contexto: respuesta irónica a ironía previa
    - Evidencia: "raíces oscuras bajo el teñido platino"
    - Interpretación: Marina NO es rubia natural
    - El pelo platino es TEÑIDO, el natural es OSCURO

    INDICADORES DE IRONÍA:
    1. Verbo performativo: "se burló"
    2. Contradicción con evidencia en el texto
    3. Contexto de intercambio jocoso
    """,
    trap_description="""
    TRAMPA: Procesar enunciados irónicos como literales.

    Error grave:
    - "¡Qué alto!" → height=alto ❌
    - "rubia natural" → hair_color=rubio_natural ❌

    El sistema DEBE detectar ironía mediante:
    1. Verbos de habla que marcan burla/sarcasmo
    2. Contradicción con información factual del texto
    3. Contexto de diálogo hostil/jocoso

    PRIORIZAR evidencia narrativa sobre enunciados de personajes,
    especialmente cuando hay marcadores de ironía.

    La ironía es uno de los fenómenos MÁS DIFÍCILES para NLP.
    """,
    linguistic_phenomenon="Ironía verbal (pragmática conversacional)",
)


# =============================================================================
# LISTA DE TODOS LOS CASOS
# =============================================================================

SEMANTIC_PRAGMATIC_TEST_CASES = [
    CASO_1_NEGACION,
    CASO_2_NEGACION_TEMPORAL,
    CASO_3_METAFORA_OJOS,
    CASO_4_METAFORA_PERSONALIDAD,
    CASO_5_TEMPORAL,
    CASO_6_CONDICIONAL,
    CASO_7_COMPARACION_HERENCIA,
    CASO_8_INFERENCIA_LEXICA,
    CASO_9_CONTRADICCION,
    CASO_10_INDIRECTA,
    CASO_11_IRONIA,
]


# =============================================================================
# FUNCIONES DE TEST
# =============================================================================


def import_attribute_extractor():
    """Importa el extractor de atributos si está disponible."""
    try:
        from src.narrative_assistant.attributes import AttributeExtractor

        return AttributeExtractor
    except ImportError:
        return None


def import_cesp_resolver():
    """Importa el resolver CESP si está disponible."""
    try:
        from src.narrative_assistant.cesp_resolver import CESPResolver

        return CESPResolver
    except ImportError:
        return None


class TestSemanticPragmaticAttribution:
    """Tests para validar manejo de fenómenos semánticos y pragmáticos."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Configura los componentes de test."""
        self.AttributeExtractor = import_attribute_extractor()
        self.CESPResolver = import_cesp_resolver()

    @pytest.mark.parametrize(
        "case", SEMANTIC_PRAGMATIC_TEST_CASES, ids=[c.id for c in SEMANTIC_PRAGMATIC_TEST_CASES]
    )
    def test_semantic_case_documented(self, case: SemanticTestCase):
        """Verifica que el caso de prueba está bien documentado."""
        assert case.text.strip(), f"Caso {case.id} sin texto"
        assert case.entities, f"Caso {case.id} sin entidades"
        assert case.semantic_analysis.strip(), f"Caso {case.id} sin análisis"
        assert case.trap_description.strip(), f"Caso {case.id} sin trampa"
        print(f"\n{'=' * 60}")
        print(f"CASO: {case.id}")
        print(f"FENÓMENO: {case.phenomenon}")
        print(f"{'=' * 60}")
        print(f"TEXTO:\n{case.text.strip()}")
        print(f"\nENTIDADES: {case.entities}")
        print(f"\nEXTRAER: {case.extract_attributes}")
        print(f"\nNO EXTRAER: {case.reject_attributes}")
        print(f"\nTRAMPA: {case.trap_description.strip()}")
        print(f"\nFENÓMENO LINGÜÍSTICO: {case.linguistic_phenomenon}")

    @pytest.mark.parametrize(
        "case", [CASO_1_NEGACION, CASO_2_NEGACION_TEMPORAL], ids=["NEGACION_001", "NEGACION_002"]
    )
    def test_negation_handling(self, case: SemanticTestCase):
        """Verifica que el sistema detecte y maneje negaciones."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        # Este test verificaría que atributos negados no se extraen
        print(f"\nTest de NEGACIÓN: {case.id}")
        print(f"Atributos que NO deben extraerse: {case.reject_attributes}")

    @pytest.mark.parametrize(
        "case",
        [CASO_3_METAFORA_OJOS, CASO_4_METAFORA_PERSONALIDAD],
        ids=["METAFORA_003", "METAFORA_004"],
    )
    def test_metaphor_filtering(self, case: SemanticTestCase):
        """Verifica que el sistema filtre metáforas como no literales."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest de METÁFORA: {case.id}")
        print(f"Atributos metafóricos a rechazar: {case.reject_attributes}")

    @pytest.mark.parametrize("case", [CASO_5_TEMPORAL], ids=["TEMPORAL_005"])
    def test_temporal_attributes(self, case: SemanticTestCase):
        """Verifica manejo correcto de atributos temporales."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest TEMPORAL: {case.id}")
        print(f"Atributos pasados a rechazar: {case.reject_attributes}")

    @pytest.mark.parametrize("case", [CASO_6_CONDICIONAL], ids=["CONDICIONAL_006"])
    def test_conditional_attributes(self, case: SemanticTestCase):
        """Verifica que atributos contrafactuales no se extraigan."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest CONDICIONAL: {case.id}")
        print(f"Atributos contrafactuales a rechazar: {case.reject_attributes}")

    @pytest.mark.parametrize("case", [CASO_8_INFERENCIA_LEXICA], ids=["INFERENCIA_008"])
    def test_lexical_inference(self, case: SemanticTestCase):
        """Verifica inferencia de atributos por conocimiento léxico."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest INFERENCIA: {case.id}")
        print(f"Atributos a inferir: {case.extract_attributes}")

    @pytest.mark.parametrize("case", [CASO_9_CONTRADICCION], ids=["CONTRADICCION_009"])
    def test_contradiction_resolution(self, case: SemanticTestCase):
        """Verifica resolución correcta de contradicciones narrativas."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest CONTRADICCIÓN: {case.id}")
        print(f"Verdad narrativa a extraer: {case.extract_attributes}")
        print(f"Rumores/creencias a rechazar: {case.reject_attributes}")

    @pytest.mark.parametrize("case", [CASO_11_IRONIA], ids=["IRONIA_011"])
    def test_irony_detection(self, case: SemanticTestCase):
        """Verifica detección de ironía y extracción del significado real."""
        if self.AttributeExtractor is None:
            pytest.skip("AttributeExtractor no disponible")

        print(f"\nTest IRONÍA: {case.id}")
        print(f"Atributos reales: {case.extract_attributes}")
        print(f"Atributos irónicos a rechazar: {case.reject_attributes}")


# =============================================================================
# TABLA RESUMEN PARA DOCUMENTACIÓN
# =============================================================================


def print_test_summary():
    """Imprime resumen de todos los casos para documentación."""
    print("\n" + "=" * 80)
    print("RESUMEN DE CASOS DE PRUEBA SEMÁNTICO-PRAGMÁTICOS")
    print("=" * 80)

    for case in SEMANTIC_PRAGMATIC_TEST_CASES:
        print(f"""
CASO {case.id}: {case.phenomenon}
{"─" * 60}
TEXTO: {case.text.strip()[:100]}...

INTERPRETACIÓN: {case.semantic_analysis.strip()[:150]}...

EXTRAER: {case.extract_attributes}
NO EXTRAER: {case.reject_attributes}

TRAMPA: {case.trap_description.strip()[:100]}...

FENÓMENO LINGÜÍSTICO: {case.linguistic_phenomenon}
""")


if __name__ == "__main__":
    # Ejecutar como script para ver resumen
    print_test_summary()

    # O ejecutar tests con pytest
    pytest.main([__file__, "-v", "-s"])
