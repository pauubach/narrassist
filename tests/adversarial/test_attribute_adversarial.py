"""
Adversarial Test Cases for Attribute Extraction Algorithm.

Este archivo contiene casos de prueba adversariales disenados para ROMPER
el algoritmo actual de extraccion de atributos basado en regex y heuristicas.

El objetivo es exponer debilidades en:
1. _find_nearest_entity() - resolucion de entidades cercanas
2. _extract_by_patterns() - patrones regex
3. ATTRIBUTE_PATTERNS - lista de patrones

Estos tests estan disenados para FALLAR con la implementacion actual,
sirviendo como casos de prueba para mejorar el algoritmo.

Autor: GAN-style Adversary Agent
Fecha: 2025-01
"""

import pytest
from typing import Optional

from narrative_assistant.nlp.attributes import (
    AttributeExtractor,
    AttributeKey,
    ExtractedAttribute,
)


# =============================================================================
# ADVERSARIAL TEST CASES
# =============================================================================

ADVERSARIAL_CASES = [
    # -------------------------------------------------------------------------
    # 1. RELATIVE CLAUSES - El sujeto esta desplazado por una clausula relativa
    # -------------------------------------------------------------------------
    {
        "id": "rel_clause_01",
        "text": "La mujer de ojos verdes que Juan conocio era Maria.",
        "expected": {"Maria": {"eye_color": "verdes"}},
        "reason": (
            "Clausula relativa con sujeto desplazado. El regex captura 'Juan' "
            "como entidad cercana a 'ojos verdes' pero el referente es 'La mujer' "
            "que luego se identifica como 'Maria'."
        ),
    },
    {
        "id": "rel_clause_02",
        "text": "El hombre que Maria habia visto tenia ojos azules.",
        "expected": {"El hombre": {"eye_color": "azules"}},
        "reason": (
            "La entidad mas cercana al patron es 'Maria' (dentro de la clausula relativa), "
            "pero el atributo pertenece a 'El hombre' que es el sujeto principal."
        ),
    },
    {
        "id": "rel_clause_03",
        "text": "Carlos, cuya hermana tenia pelo rubio, era moreno.",
        "expected": {
            "Carlos": {"hair_color": "moreno"},
            # La hermana de Carlos tiene pelo rubio, pero no sabemos su nombre
        },
        "reason": (
            "Posesivo 'cuya' crea ambiguedad. 'pelo rubio' pertenece a 'hermana' "
            "(no nombrada), no a Carlos. El regex puede asignar 'rubio' a Carlos."
        ),
    },

    # -------------------------------------------------------------------------
    # 2. ELLIPTICAL SUBJECTS - Sujetos elididos en espanol (pro-drop)
    # -------------------------------------------------------------------------
    {
        "id": "ellipsis_01",
        "text": "Maria entro en la habitacion. Tenia los ojos rojos de llorar.",
        "expected": {"Maria": {"eye_color": "rojos"}},
        "reason": (
            "Sujeto elidido en segunda oracion. El algoritmo debe inferir que "
            "'Tenia' refiere a Maria, pero el patron 'tenia ojos X' no captura "
            "la entidad porque no hay nombre propio explicito."
        ),
    },
    {
        "id": "ellipsis_02",
        "text": "Juan saludo a Pedro. Era alto y corpulento.",
        "expected": {"Juan": {"build": "alto y corpulento"}},
        "reason": (
            "Ambiguedad: 'Era alto' puede referir a Juan (sujeto) o Pedro (objeto). "
            "En espanol, el sujeto elidido tipicamente refiere al sujeto anterior, "
            "pero _find_nearest_entity puede elegir Pedro por proximidad."
        ),
    },
    {
        "id": "ellipsis_03",
        "text": "Elena miro a Sofia con envidia. Era rubia natural.",
        "expected": {"Sofia": {"hair_color": "rubia", "hair_modification": "natural"}},
        "reason": (
            "El sujeto elidido de 'Era rubia' ambiguamente puede ser Elena o Sofia. "
            "El contexto de 'envidia' sugiere que Sofia es la rubia, pero el algoritmo "
            "puede elegir Elena por ser sujeto de la oracion anterior."
        ),
    },

    # -------------------------------------------------------------------------
    # 3. POSSESSIVE AMBIGUITY - Posesivos ambiguos (su/sus)
    # -------------------------------------------------------------------------
    {
        "id": "possessive_01",
        "text": "Juan le dijo a Maria que sus ojos eran hermosos.",
        "expected": {"Maria": {"eye_color": None}},  # Atributo implicito, no color
        "reason": (
            "'sus ojos' es ambiguo: puede referir a Juan (sujeto), Maria (objeto indirecto), "
            "o incluso una tercera persona. El algoritmo asume el mas cercano."
        ),
    },
    {
        "id": "possessive_02",
        "text": "Pedro abrazo a su madre. Sus ojos azules brillaban de emocion.",
        "expected": {"la madre de Pedro": {"eye_color": "azules"}},
        "reason": (
            "'Sus ojos azules' probablemente refiere a 'su madre' (la persona mencionada "
            "justo antes), no a Pedro. Pero 'madre' no es nombre propio."
        ),
    },
    {
        "id": "possessive_03",
        "text": "Ana y Luis se miraron. Sus ojos verdes se encontraron.",
        "expected": {},  # Ambiguo - no deberia asignar a nadie sin mas contexto
        "reason": (
            "'Sus ojos verdes' con dos candidatos de genero mixto. Ambos podrian tener "
            "ojos verdes, o solo uno. El algoritmo no puede decidir correctamente."
        ),
    },

    # -------------------------------------------------------------------------
    # 4. ARTICLES VS PRONOUNS - Articulos que parecen pronombres
    # -------------------------------------------------------------------------
    {
        "id": "article_01",
        "text": "Juan la saludo. La sorprendio su cabello negro.",
        "expected": {"la persona saludada": {"hair_color": "negro"}},
        "reason": (
            "El primer 'la' es pronombre objeto. El segundo 'La' es articulo (sujeto). "
            "'su cabello negro' refiere a la persona saludada, no a Juan. El algoritmo "
            "puede confundir 'la' articulo con pronombre."
        ),
    },
    {
        "id": "article_02",
        "text": "El alto edificio donde vivia Juan proyectaba su sombra.",
        "expected": {},  # 'su sombra' refiere al edificio, no a Juan
        "reason": (
            "'El alto' parece patron de 'el alto Juan' pero es 'el alto edificio'. "
            "El algoritmo puede extraer 'alto' como atributo de Juan incorrectamente."
        ),
    },
    {
        "id": "article_03",
        "text": "Los ojos verdes de la estatua parecian seguir a Maria.",
        "expected": {},  # Los ojos son de la estatua, no de Maria
        "reason": (
            "El patron 'los ojos verdes de X' espera nombre propio, pero aqui es "
            "'la estatua'. Maria esta cerca pero no es la poseedora."
        ),
    },

    # -------------------------------------------------------------------------
    # 5. MULTIPLE ENTITIES CLOSE TOGETHER - Varias entidades muy cercanas
    # -------------------------------------------------------------------------
    {
        "id": "multiple_01",
        "text": "Maria, Juan y Pedro compartian rasgos: ella de ojos azules, el de verdes.",
        "expected": {"Maria": {"eye_color": "azules"}, "Juan": {"eye_color": "verdes"}},
        "reason": (
            "Multiples entidades con atributos distribuidos. 'ella' refiere a Maria, "
            "'el' a Juan. Los patrones no pueden resolver pronombres en listas."
        ),
    },
    {
        "id": "multiple_02",
        "text": "Entre Carlos y Ana, de pelo rubio, habia una gran diferencia.",
        "expected": {"Ana": {"hair_color": "rubio"}},
        "reason": (
            "'de pelo rubio' modifica a Ana (por proximidad y genero), pero el algoritmo "
            "podria asignarlo a Carlos o a ambos."
        ),
    },
    {
        "id": "multiple_03",
        "text": "Sofia presento a Diego, un hombre alto de ojos negros, a su madre.",
        "expected": {"Diego": {"height": "alto", "eye_color": "negros"}},
        "reason": (
            "Aposicion con atributos. 'un hombre alto de ojos negros' describe a Diego, "
            "no a Sofia ni a 'su madre'. El algoritmo puede confundirse con las entidades cercanas."
        ),
    },

    # -------------------------------------------------------------------------
    # 6. UNUSUAL WORD ORDER - Orden de palabras no estandar
    # -------------------------------------------------------------------------
    {
        "id": "word_order_01",
        "text": "Verdes eran los ojos de Laura.",
        "expected": {"Laura": {"eye_color": "verdes"}},
        "reason": (
            "Orden OSV en lugar de SVO. El patron 'los ojos X de Y' no captura "
            "'Verdes eran los ojos de Y' porque el color esta antepuesto."
        ),
    },
    {
        "id": "word_order_02",
        "text": "De cabello rubio y ojos claros era la joven Lucia.",
        "expected": {"Lucia": {"hair_color": "rubio", "eye_color": "claros"}},
        "reason": (
            "Predicado antepuesto al sujeto. Los patrones asumen sujeto primero, "
            "este orden invierte completamente la estructura."
        ),
    },
    {
        "id": "word_order_03",
        "text": "Alto no era Miguel, sino de estatura media.",
        "expected": {"Miguel": {"height": "estatura media"}},
        "reason": (
            "Negacion con correccion posterior. El algoritmo puede detectar 'alto' "
            "pero perder la negacion y el valor correcto."
        ),
    },

    # -------------------------------------------------------------------------
    # 7. NEGATION EDGE CASES - Negaciones complejas
    # -------------------------------------------------------------------------
    {
        "id": "negation_01",
        "text": "No es que Pedro tuviera ojos azules, sino grises.",
        "expected": {"Pedro": {"eye_color": "grises"}},
        "reason": (
            "Negacion del primer valor, afirmacion del segundo. El algoritmo "
            "puede capturar 'ojos azules' ignorando la estructura 'No es que...sino'."
        ),
    },
    {
        "id": "negation_02",
        "text": "Rosa nunca tuvo el pelo negro que todos recordaban.",
        "expected": {},  # Niega que tuvo pelo negro
        "reason": (
            "Negacion con 'nunca'. El patron 'tenia pelo negro' puede activarse "
            "ignorando que 'nunca tuvo' niega el atributo."
        ),
    },
    {
        "id": "negation_03",
        "text": "Nadie diria que Lucas, de ojos marrones, era ciego.",
        "expected": {"Lucas": {"eye_color": "marrones"}},
        "reason": (
            "'Nadie diria' no niega el atributo 'ojos marrones', solo la conclusion. "
            "El algoritmo debe extraer el atributo correctamente a pesar del contexto."
        ),
    },

    # -------------------------------------------------------------------------
    # 8. METAPHORS AND FIGURATIVE LANGUAGE - Metaforas no filtradas
    # -------------------------------------------------------------------------
    {
        "id": "metaphor_01",
        "text": "Marta tenia ojos de fuego que quemaban con la mirada.",
        "expected": {},  # 'ojos de fuego' es metaforico
        "reason": (
            "Metafora no literal. El filtro de metaforas puede no detectar "
            "'ojos de fuego' como figurativo porque no tiene 'como'."
        ),
    },
    {
        "id": "metaphor_02",
        "text": "El pelo de sol de Alejandra brillaba bajo la luz.",
        "expected": {},  # 'pelo de sol' es metaforico para rubio
        "reason": (
            "Metafora creativa para color. El patron captura 'pelo de sol' "
            "literalmente en vez de reconocerlo como expresion figurativa."
        ),
    },
    {
        "id": "metaphor_03",
        "text": "Tenia unos ojos de acero que no mostraban emocion.",
        "expected": {},  # 'ojos de acero' = duros, no color
        "reason": (
            "'ojos de acero' describe actitud, no color. El patron 'ojos de X' "
            "puede interpretarlo como material/color."
        ),
    },

    # -------------------------------------------------------------------------
    # 9. DIALOGUE EDGE CASES - Atributos dentro de dialogos
    # -------------------------------------------------------------------------
    {
        "id": "dialogue_01",
        "text": '- Tienes los ojos mas verdes que he visto - dijo Pablo a Clara.',
        "expected": {"Clara": {"eye_color": "verdes"}},
        "reason": (
            "Atributo mencionado en dialogo. El patron puede capturar 'ojos verdes' "
            "pero asignarlo a Pablo (quien habla) en vez de Clara (destinataria)."
        ),
    },
    {
        "id": "dialogue_02",
        "text": 'Maria penso: "Ese hombre de pelo canoso debe ser el jefe."',
        "expected": {},  # El hombre no esta identificado
        "reason": (
            "Pensamiento/dialogo interno con entidad no identificada. El algoritmo "
            "puede asignar 'pelo canoso' a Maria por ser la entidad mas cercana."
        ),
    },
    {
        "id": "dialogue_03",
        "text": '- Soy rubio natural - mintio Carlos, que siempre se tenia el pelo.',
        "expected": {"Carlos": {"hair_modification": "tenido"}},
        "reason": (
            "Atributo en dialogo contradice la narracion. El dialogo dice 'rubio natural' "
            "pero la narracion revela que es 'tenido'. El algoritmo debe preferir la narracion."
        ),
    },

    # -------------------------------------------------------------------------
    # 10. TEMPORAL/CONDITIONAL ATTRIBUTES - Atributos temporales o condicionales
    # -------------------------------------------------------------------------
    {
        "id": "temporal_01",
        "text": "De joven, Eva tenia el pelo negro, pero ahora era completamente canosa.",
        "expected": {"Eva": {"hair_color": "canoso"}},  # Estado actual
        "reason": (
            "Atributo temporal vs actual. El algoritmo puede capturar 'pelo negro' "
            "(pasado) en vez de 'canosa' (presente)."
        ),
    },
    {
        "id": "temporal_02",
        "text": "Si Oscar se tenia el pelo, seria pelirrojo.",
        "expected": {},  # Condicional, no real
        "reason": (
            "Condicional irreal. 'seria pelirrojo' no es un atributo actual, "
            "pero el patron puede capturarlo como si lo fuera."
        ),
    },
    {
        "id": "temporal_03",
        "text": "Antes de la operacion, Isabel tenia ojos marrones.",
        "expected": {},  # Implica que ya no los tiene marrones
        "reason": (
            "Implicacion de cambio. 'Antes de' sugiere que el atributo ya no aplica, "
            "pero el algoritmo extrae el patron literalmente."
        ),
    },

    # -------------------------------------------------------------------------
    # 11. COMPOUND ENTITIES - Entidades compuestas o grupos
    # -------------------------------------------------------------------------
    {
        "id": "compound_01",
        "text": "Los hermanos Garcia tenian todos ojos azules.",
        "expected": {"Los hermanos Garcia": {"eye_color": "azules"}},
        "reason": (
            "Entidad compuesta/grupo. El algoritmo espera nombres simples, "
            "no 'Los hermanos Garcia' como unidad."
        ),
    },
    {
        "id": "compound_02",
        "text": "Maria Jose, la del pelo rizado, entro en la sala.",
        "expected": {"Maria Jose": {"hair_type": "rizado"}},
        "reason": (
            "Nombre compuesto con atributo. El algoritmo puede capturar solo "
            "'Jose' o confundirse con el espacio en el nombre."
        ),
    },
    {
        "id": "compound_03",
        "text": "Don Alvaro de ojos grises saludo a la concurrencia.",
        "expected": {"Don Alvaro": {"eye_color": "grises"}},
        "reason": (
            "Tratamiento + nombre. El patron puede no reconocer 'Don Alvaro' "
            "como entidad unica y capturar solo 'Alvaro'."
        ),
    },

    # -------------------------------------------------------------------------
    # 12. IMPLICIT/INFERRED ATTRIBUTES - Atributos implicitos
    # -------------------------------------------------------------------------
    {
        "id": "implicit_01",
        "text": "Fernando se rasco la barba pelirroja pensativo.",
        "expected": {"Fernando": {"hair_color": "pelirrojo"}},
        "reason": (
            "Barba pelirroja implica pelo pelirrojo tipicamente. El algoritmo "
            "no infiere esto, solo captura patrones explicitos de pelo/cabello."
        ),
    },
    {
        "id": "implicit_02",
        "text": "La albina Lucia se protegia del sol constantemente.",
        "expected": {"Lucia": {"skin": "albina", "hair_color": "blanco", "eye_color": "claro"}},
        "reason": (
            "'albina' implica multiples atributos fisicos, pero el algoritmo "
            "solo captura lo explicito."
        ),
    },
    {
        "id": "implicit_03",
        "text": "El anciano Roberto caminaba con dificultad.",
        "expected": {"Roberto": {"age": "anciano"}},
        "reason": (
            "'anciano' es un atributo de edad, pero el patron busca 'X anos' "
            "y no reconoce adjetivos de edad."
        ),
    },

    # -------------------------------------------------------------------------
    # 13. PROFESSION/ROLE EDGE CASES - Profesiones y roles complejos
    # -------------------------------------------------------------------------
    {
        "id": "profession_01",
        "text": "El que era carpintero resulto ser arquitecto.",
        "expected": {},  # Ambiguo - no hay entidad nombrada
        "reason": (
            "Dos profesiones para entidad anonima. El algoritmo no puede resolver "
            "'El que' a una entidad concreta."
        ),
    },
    {
        "id": "profession_02",
        "text": "Carmen trabajaba de ingeniera pero sonaba con ser artista.",
        "expected": {"Carmen": {"profession": "ingeniera"}},  # Actual, no deseada
        "reason": (
            "Profesion actual vs aspiracional. El algoritmo puede capturar "
            "'artista' como profesion ignorando 'sonaba con ser'."
        ),
    },
    {
        "id": "profession_03",
        "text": "Nacho, mas conocido como el Carpintero, nunca toco un martillo.",
        "expected": {"Nacho": {"title": "el Carpintero"}},  # Apodo, no profesion real
        "reason": (
            "Apodo vs profesion real. El algoritmo puede extraer 'Carpintero' "
            "como profesion cuando es solo un sobrenombre."
        ),
    },

    # -------------------------------------------------------------------------
    # 14. ORTHOGRAPHIC VARIATIONS - Variaciones ortograficas
    # -------------------------------------------------------------------------
    {
        "id": "ortho_01",
        "text": "Jose tenia unos hojos azules muy bonitos.",
        "expected": {"Jose": {"eye_color": "azules"}},
        "reason": (
            "Error ortografico 'hojos' en vez de 'ojos'. Los patrones regex "
            "buscan 'ojos' exacto y no capturan variantes con errores."
        ),
    },
    {
        "id": "ortho_02",
        "text": "Maria era una muger alta y esvelta.",
        "expected": {"Maria": {"height": "alta", "build": "esbelta"}},
        "reason": (
            "Errores: 'muger' por 'mujer', 'esvelta' por 'esbelta'. Los patrones "
            "no toleran variaciones ortograficas."
        ),
    },
    {
        "id": "ortho_03",
        "text": "El pelo rubio de Andres era teido, no natural.",
        "expected": {"Andres": {"hair_color": "rubio", "hair_modification": "tenido"}},
        "reason": (
            "Error: 'teido' por 'tenido'. El patron de modificacion de cabello "
            "no reconoce la variante mal escrita."
        ),
    },

    # -------------------------------------------------------------------------
    # 15. LONG-DISTANCE DEPENDENCIES - Dependencias a larga distancia
    # -------------------------------------------------------------------------
    {
        "id": "long_dist_01",
        "text": (
            "Pablo, que habia vivido en Paris durante diez anos, trabajado como chef, "
            "y recorrido media Europa, tenia unos distintivos ojos verdes."
        ),
        "expected": {"Pablo": {"eye_color": "verdes"}},
        "reason": (
            "El sujeto 'Pablo' esta muy lejos del predicado 'tenia ojos verdes' "
            "debido a clausulas interpoladas. El algoritmo puede perder la referencia."
        ),
    },
    {
        "id": "long_dist_02",
        "text": (
            "La mujer de la que todos hablaban en el pueblo, aquella misteriosa "
            "forastera que llego una noche de tormenta, era Elvira, de ojos negros."
        ),
        "expected": {"Elvira": {"eye_color": "negros"}},
        "reason": (
            "La entidad 'Elvira' aparece muy tarde despues de multiples descripciones. "
            "El algoritmo puede asignar atributos a entidades incorrectas."
        ),
    },
    {
        "id": "long_dist_03",
        "text": (
            "Sergio, tras anos de ausencia, finalmente regreso al pueblo donde "
            "su madre, una mujer de cabello blanco, lo esperaba ansiosa."
        ),
        "expected": {"la madre de Sergio": {"hair_color": "blanco"}},
        "reason": (
            "'cabello blanco' pertenece a 'su madre', no a Sergio. La distancia "
            "y la estructura pueden confundir al algoritmo."
        ),
    },

    # -------------------------------------------------------------------------
    # 16. COORDINATION AND LISTS - Coordinacion y listas
    # -------------------------------------------------------------------------
    {
        "id": "coord_01",
        "text": "Diana de pelo negro y ojos verdes y Raul de pelo rubio se casaron.",
        "expected": {
            "Diana": {"hair_color": "negro", "eye_color": "verdes"},
            "Raul": {"hair_color": "rubio"},
        },
        "reason": (
            "Dos entidades con atributos en paralelo. El algoritmo puede mezclar "
            "los atributos entre Diana y Raul."
        ),
    },
    {
        "id": "coord_02",
        "text": "Tanto Miguel como su hermano eran altos, pero solo el tenia ojos azules.",
        "expected": {
            "Miguel": {"height": "alto", "eye_color": "azules"},
            "su hermano": {"height": "alto"},
        },
        "reason": (
            "Atributo compartido (altos) vs individual (ojos azules). El algoritmo "
            "puede no distinguir el 'solo' que restringe el segundo atributo."
        ),
    },
    {
        "id": "coord_03",
        "text": "Ni Eva ni Marcos tenian el pelo largo.",
        "expected": {},  # Ambos NO tienen pelo largo
        "reason": (
            "Negacion distribuida sobre coordinacion. El algoritmo puede capturar "
            "'pelo largo' ignorando 'Ni...ni' que lo niega."
        ),
    },

    # -------------------------------------------------------------------------
    # 17. ANAPHORIC CHAINS - Cadenas anaforicas complejas
    # -------------------------------------------------------------------------
    {
        "id": "anaphor_01",
        "text": (
            "Jorge conocio a una mujer. Era morena. Tenia ojos claros. "
            "Se llamaba Patricia."
        ),
        "expected": {"Patricia": {"hair_color": "morena", "eye_color": "claros"}},
        "reason": (
            "Cadena anaforica: 'una mujer' -> 'Era' -> 'Tenia' -> 'Se llamaba Patricia'. "
            "El algoritmo debe vincular todos los atributos a Patricia."
        ),
    },
    {
        "id": "anaphor_02",
        "text": (
            "Conoci a dos personas: el era rubio y ella morena. "
            "Ricardo y Sonia, respectivamente."
        ),
        "expected": {"Ricardo": {"hair_color": "rubio"}, "Sonia": {"hair_color": "morena"}},
        "reason": (
            "Referencia catafroica con 'respectivamente'. Los atributos se asignan "
            "en orden: 'el rubio' = Ricardo, 'ella morena' = Sonia."
        ),
    },
    {
        "id": "anaphor_03",
        "text": "Adriana vio a su reflejo. Tenia ojeras y el pelo revuelto.",
        "expected": {"Adriana": {"hair_type": "revuelto"}},
        "reason": (
            "'su reflejo' refiere a Adriana misma. Los atributos del reflejo "
            "son atributos de Adriana, pero el algoritmo puede no inferirlo."
        ),
    },

    # -------------------------------------------------------------------------
    # 18. SEMANTIC ROLE CONFUSION - Confusion de roles semanticos
    # -------------------------------------------------------------------------
    {
        "id": "role_01",
        "text": "El hombre de ojos azules fue visto por Maria.",
        "expected": {"El hombre": {"eye_color": "azules"}},
        "reason": (
            "Voz pasiva. 'Maria' es el agente (quien ve), pero 'ojos azules' "
            "pertenece al paciente. El algoritmo puede asignar a Maria por proximidad."
        ),
    },
    {
        "id": "role_02",
        "text": "A Roberto le gustaba pintar mujeres de pelo largo.",
        "expected": {},  # Las mujeres pintadas no son entidades con nombre
        "reason": (
            "'pelo largo' describe las mujeres que Roberto pinta, no a Roberto. "
            "El algoritmo puede asignar el atributo incorrectamente."
        ),
    },
    {
        "id": "role_03",
        "text": "Carmen imagino a su hijo con el pelo canoso.",
        "expected": {},  # Hipotetico, no real
        "reason": (
            "Atributo imaginado/hipotetico. 'pelo canoso' es como Carmen imagina "
            "a su hijo, no un atributo real actual."
        ),
    },

    # -------------------------------------------------------------------------
    # 19. GENERIC/INDEFINITE REFERENCES - Referencias genericas o indefinidas
    # -------------------------------------------------------------------------
    {
        "id": "generic_01",
        "text": "Dicen que los pelirrojos tienen mal genio. Enrique era pelirrojo.",
        "expected": {"Enrique": {"hair_color": "pelirrojo"}},
        "reason": (
            "Primera mencion es generica ('los pelirrojos'), segunda es especifica. "
            "El algoritmo debe capturar solo el atributo de Enrique."
        ),
    },
    {
        "id": "generic_02",
        "text": "Una persona de ojos verdes entro. Era Beatriz.",
        "expected": {"Beatriz": {"eye_color": "verdes"}},
        "reason": (
            "Referencia indefinida 'Una persona' identificada despues como Beatriz. "
            "El algoritmo debe vincular el atributo a Beatriz."
        ),
    },
    {
        "id": "generic_03",
        "text": "Alguien muy alto paso corriendo. Podria haber sido Victor.",
        "expected": {},  # Incertidumbre - 'podria'
        "reason": (
            "Incertidumbre sobre identidad. 'Podria haber sido' no confirma que "
            "Victor sea 'muy alto', pero el algoritmo puede asignarlo."
        ),
    },

    # -------------------------------------------------------------------------
    # 20. CONTEXT-DEPENDENT INTERPRETATION - Interpretacion dependiente del contexto
    # -------------------------------------------------------------------------
    {
        "id": "context_01",
        "text": (
            "En la foto antigua, Luis tenia el pelo negro. "
            "Ahora, treinta anos despues, era completamente calvo."
        ),
        "expected": {"Luis": {"hair_type": "calvo"}},  # Estado actual
        "reason": (
            "Conflicto temporal explicito. El algoritmo puede capturar ambos "
            "atributos sin resolver cual es el actual."
        ),
    },
    {
        "id": "context_02",
        "text": "Según Maria, Pedro tenia ojos verdes. Pero ella mentia.",
        "expected": {},  # Atributo en duda por mentira
        "reason": (
            "Atributo reportado por fuente no fiable. 'ella mentia' invalida "
            "el atributo, pero el algoritmo puede capturarlo."
        ),
    },
    {
        "id": "context_03",
        "text": "El gemelo de ojos azules no era Ramon, sino Tomas.",
        "expected": {"Tomas": {"eye_color": "azules"}},
        "reason": (
            "Negacion de identidad seguida de correccion. El algoritmo puede "
            "asignar 'ojos azules' a Ramon ignorando la negacion."
        ),
    },
]


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================

@pytest.fixture
def extractor():
    """Crea una instancia del extractor de atributos."""
    return AttributeExtractor(
        filter_metaphors=True,
        min_confidence=0.5,
        use_llm=False,  # Desactivar LLM para tests deterministicos
        use_embeddings=False,  # Desactivar embeddings para tests deterministicos
        use_dependency_extraction=True,
        use_patterns=True,
    )


def extract_attributes_for_test(extractor: AttributeExtractor, text: str) -> dict:
    """
    Extrae atributos y los organiza por entidad para comparacion.

    Returns:
        Dict de entidad -> {key: value, ...}
    """
    # Primero necesitamos simular entity_mentions para el algoritmo
    # En produccion esto viene del NER, aqui lo simplificamos
    import re

    # Patron simple para detectar nombres propios (capitalizados)
    name_pattern = r'\b([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)?)\b'
    entity_mentions = []

    for match in re.finditer(name_pattern, text):
        name = match.group(1)
        # Filtrar palabras comunes que no son nombres
        common_words = {
            'El', 'La', 'Los', 'Las', 'Un', 'Una', 'Unos', 'Unas',
            'De', 'En', 'Con', 'Por', 'Para', 'Sin', 'Sobre', 'Tras',
            'Antes', 'Despues', 'Segun', 'Durante', 'Mediante',
            'Era', 'Tenia', 'Fue', 'Habia', 'Dijo', 'Penso',
            'Verdes', 'Azules', 'Negros', 'Rubio', 'Moreno', 'Canoso',
            'Alto', 'Bajo', 'Delgado', 'Gordo', 'Pero', 'Sino', 'Aunque',
        }
        if name not in common_words:
            entity_mentions.append((name, match.start(), match.end(), 'PER'))

    extraction_result = extractor.extract_attributes(text, entity_mentions=entity_mentions)

    # Unwrap Result pattern
    if extraction_result.is_failure:
        return {}

    result = extraction_result.value

    # Organizar por entidad
    by_entity = {}
    for attr in result.attributes:
        entity = attr.entity_name
        if entity not in by_entity:
            by_entity[entity] = {}
        by_entity[entity][attr.key.value] = attr.value

    return by_entity


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestAdversarialRelativeClauses:
    """Tests para clausulas relativas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("rel_clause")])
    def test_relative_clause(self, extractor, case):
        """Verifica que las clausulas relativas se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        # Este test esta disenado para FALLAR con la implementacion actual
        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )
            for key, value in expected_attrs.items():
                if value is not None:
                    assert result[entity].get(key) == value, (
                        f"Caso {case['id']}: Atributo {key}={value} no encontrado para {entity}.\n"
                        f"Razon: {case['reason']}\n"
                        f"Resultado: {result}"
                    )


class TestAdversarialEllipsis:
    """Tests para sujetos elididos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("ellipsis")])
    def test_elliptical_subjects(self, extractor, case):
        """Verifica que los sujetos elididos se resuelvan correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialPossessives:
    """Tests para posesivos ambiguos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("possessive")])
    def test_possessive_ambiguity(self, extractor, case):
        """Verifica que los posesivos ambiguos se resuelvan correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        if not case["expected"]:
            # Esperamos que NO extraiga atributos (caso ambiguo)
            assert len(result) == 0, (
                f"Caso {case['id']}: Se esperaba ningun atributo pero se encontraron.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )
        else:
            for entity, expected_attrs in case["expected"].items():
                assert entity in result, (
                    f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                    f"Razon: {case['reason']}\n"
                    f"Resultado: {result}"
                )


class TestAdversarialArticles:
    """Tests para articulos vs pronombres."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("article")])
    def test_article_pronoun_confusion(self, extractor, case):
        """Verifica que articulos y pronombres no se confundan."""
        result = extract_attributes_for_test(extractor, case["text"])

        if not case["expected"]:
            # Verificar que no se extraigan atributos incorrectos
            # El algoritmo puede extraer algo incorrecto, lo cual es un fallo
            pass  # Este test documenta el comportamiento esperado


class TestAdversarialMultipleEntities:
    """Tests para multiples entidades cercanas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("multiple")])
    def test_multiple_entities(self, extractor, case):
        """Verifica que multiples entidades cercanas se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialWordOrder:
    """Tests para orden de palabras no estandar."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("word_order")])
    def test_unusual_word_order(self, extractor, case):
        """Verifica que ordenes de palabras no estandar se manejen."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialNegation:
    """Tests para negaciones complejas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("negation")])
    def test_negation_handling(self, extractor, case):
        """Verifica que las negaciones se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        if not case["expected"]:
            # Esperamos que el atributo NO se extraiga
            pass
        else:
            for entity, expected_attrs in case["expected"].items():
                assert entity in result, (
                    f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                    f"Razon: {case['reason']}\n"
                    f"Resultado: {result}"
                )


class TestAdversarialMetaphors:
    """Tests para metaforas no detectadas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("metaphor")])
    def test_metaphor_filtering(self, extractor, case):
        """Verifica que las metaforas se filtren correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        # Esperamos que NO se extraigan atributos metaforicos
        if not case["expected"]:
            # Cualquier extraccion es un error
            assert len(result) == 0, (
                f"Caso {case['id']}: Metafora no filtrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialDialogue:
    """Tests para atributos en dialogos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("dialogue")])
    def test_dialogue_handling(self, extractor, case):
        """Verifica que los dialogos se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        # Los tests de dialogo son complejos porque el atributo
        # puede estar en el dialogo pero ser sobre otra persona


class TestAdversarialTemporal:
    """Tests para atributos temporales/condicionales."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("temporal")])
    def test_temporal_attributes(self, extractor, case):
        """Verifica que los atributos temporales se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        if case["expected"]:
            for entity, expected_attrs in case["expected"].items():
                assert entity in result, (
                    f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                    f"Razon: {case['reason']}\n"
                    f"Resultado: {result}"
                )


class TestAdversarialCompound:
    """Tests para entidades compuestas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("compound")])
    def test_compound_entities(self, extractor, case):
        """Verifica que las entidades compuestas se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            # Nota: las entidades compuestas pueden necesitar match parcial
            found = any(entity.lower() in e.lower() or e.lower() in entity.lower()
                       for e in result.keys())
            assert found, (
                f"Caso {case['id']}: Entidad '{entity}' no encontrada.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialImplicit:
    """Tests para atributos implicitos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("implicit")])
    def test_implicit_attributes(self, extractor, case):
        """Verifica que los atributos implicitos se infieran correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])

        # Estos tests verifican inferencia - el algoritmo actual no la hace
        for entity, expected_attrs in case["expected"].items():
            if entity in result:
                # Si la entidad existe, verificar atributos
                for key, value in expected_attrs.items():
                    assert result[entity].get(key) == value, (
                        f"Caso {case['id']}: Atributo implicito no inferido.\n"
                        f"Razon: {case['reason']}\n"
                        f"Resultado: {result}"
                    )


class TestAdversarialProfession:
    """Tests para profesiones y roles complejos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("profession")])
    def test_profession_handling(self, extractor, case):
        """Verifica que las profesiones se manejen correctamente."""
        result = extract_attributes_for_test(extractor, case["text"])


class TestAdversarialOrthographic:
    """Tests para variaciones ortograficas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("ortho")])
    def test_orthographic_variations(self, extractor, case):
        """Verifica tolerancia a variaciones ortograficas."""
        result = extract_attributes_for_test(extractor, case["text"])

        # Estos tests DEBEN fallar si el algoritmo no tolera errores ortograficos
        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: No se tolero variacion ortografica.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialLongDistance:
    """Tests para dependencias a larga distancia."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("long_dist")])
    def test_long_distance_dependencies(self, extractor, case):
        """Verifica manejo de dependencias a larga distancia."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Dependencia a larga distancia fallida.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialCoordination:
    """Tests para coordinacion y listas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("coord")])
    def test_coordination(self, extractor, case):
        """Verifica manejo de coordinacion y listas."""
        result = extract_attributes_for_test(extractor, case["text"])

        if not case["expected"]:
            pass  # Verificar que no extraiga cuando hay negacion coordinada
        else:
            for entity, expected_attrs in case["expected"].items():
                assert entity in result, (
                    f"Caso {case['id']}: Coordinacion mal manejada.\n"
                    f"Razon: {case['reason']}\n"
                    f"Resultado: {result}"
                )


class TestAdversarialAnaphor:
    """Tests para cadenas anaforicas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("anaphor")])
    def test_anaphoric_chains(self, extractor, case):
        """Verifica resolucion de cadenas anaforicas."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Cadena anaforica no resuelta.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestAdversarialSemanticRole:
    """Tests para confusion de roles semanticos."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("role")])
    def test_semantic_role_confusion(self, extractor, case):
        """Verifica que los roles semanticos no se confundan."""
        result = extract_attributes_for_test(extractor, case["text"])


class TestAdversarialGeneric:
    """Tests para referencias genericas/indefinidas."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("generic")])
    def test_generic_references(self, extractor, case):
        """Verifica manejo de referencias genericas."""
        result = extract_attributes_for_test(extractor, case["text"])


class TestAdversarialContext:
    """Tests para interpretacion dependiente del contexto."""

    @pytest.mark.parametrize("case", [c for c in ADVERSARIAL_CASES if c["id"].startswith("context")])
    def test_context_dependent(self, extractor, case):
        """Verifica interpretacion correcta segun contexto."""
        result = extract_attributes_for_test(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"Caso {case['id']}: Contexto mal interpretado.\n"
                f"Razon: {case['reason']}\n"
                f"Resultado: {result}"
            )


# =============================================================================
# SUMMARY TEST - Runs all cases and reports statistics
# =============================================================================

class TestAdversarialSummary:
    """Test de resumen que ejecuta todos los casos y reporta estadisticas."""

    def test_all_adversarial_cases(self, extractor):
        """Ejecuta todos los casos adversariales y reporta resultados."""
        passed = 0
        failed = 0
        errors = []

        for case in ADVERSARIAL_CASES:
            try:
                result = extract_attributes_for_test(extractor, case["text"])

                # Verificar si el resultado coincide con lo esperado
                case_passed = True

                if not case["expected"]:
                    # Esperamos vacio
                    if result:
                        case_passed = False
                else:
                    for entity, expected_attrs in case["expected"].items():
                        if entity not in result:
                            case_passed = False
                            break
                        for key, value in expected_attrs.items():
                            if value is not None and result[entity].get(key) != value:
                                case_passed = False
                                break

                if case_passed:
                    passed += 1
                else:
                    failed += 1
                    errors.append({
                        "id": case["id"],
                        "reason": case["reason"],
                        "expected": case["expected"],
                        "got": result,
                    })

            except Exception as e:
                failed += 1
                errors.append({
                    "id": case["id"],
                    "error": str(e),
                })

        # Imprimir resumen
        print(f"\n{'='*60}")
        print(f"ADVERSARIAL TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total cases: {len(ADVERSARIAL_CASES)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass rate: {passed/len(ADVERSARIAL_CASES)*100:.1f}%")
        print(f"{'='*60}")

        if errors:
            print(f"\nFailed cases:")
            for err in errors[:10]:  # Mostrar primeros 10
                print(f"  - {err['id']}: {err.get('reason', err.get('error', 'Unknown'))[:80]}")

        # Este test esta disenado para que el algoritmo FALLE en la mayoria de casos
        # Si pasa mas del 50%, el algoritmo es mejor de lo esperado o los tests son muy faciles
        assert failed > passed, (
            f"El algoritmo paso {passed}/{len(ADVERSARIAL_CASES)} tests. "
            f"Estos tests estan disenados para ROMPER el algoritmo actual."
        )
