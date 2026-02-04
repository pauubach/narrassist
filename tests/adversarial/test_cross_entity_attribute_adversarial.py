"""
Tests adversariales GAN-style para asignación cruzada de atributos entre entidades.

Objetivo: Detectar casos donde _find_nearest_entity() asigna atributos
al personaje EQUIVOCADO debido a:
1. Sesgo de proximidad (400-char window)
2. Detección de género incorrecta
3. Múltiples personajes en el mismo párrafo
4. Sujetos elípticos (pro-drop español)
5. Diálogos con atributos del interlocutor
6. Atributos en cláusulas subordinadas
7. Atributos negados mal asignados
8. Comparaciones entre personajes
9. Enumeraciones y listas de personajes
10. Cambio de foco narrativo

Inspirado en errores reales: Juan recibe atributos de María Sánchez
porque _find_nearest_entity() selecciona por proximidad y gender detection
siempre selecciona el masculino cuando LLM y embeddings fallan.

Autor: GAN-style Adversary Agent
"""

import re
from typing import Optional

import pytest

from narrative_assistant.nlp.attributes import (
    AttributeExtractor,
    AttributeKey,
    ExtractedAttribute,
)

# =============================================================================
# ADVERSARIAL TEST CASES - CROSS-ENTITY ATTRIBUTE ASSIGNMENT
# =============================================================================

CROSS_ENTITY_CASES = [
    # -------------------------------------------------------------------------
    # 1. PROXIMITY BIAS - Entidad más cercana NO es la dueña del atributo
    # -------------------------------------------------------------------------
    {
        "id": "prox_01_adjacent_entities",
        "text": "Juan se acercó a María. Ella tenía los ojos verdes.",
        "expected": {"María": {"eye_color": "verdes"}},
        "forbidden": {"Juan": ["eye_color"]},
        "reason": (
            "Juan es la entidad más cercana por caracteres, pero 'Ella' refiere "
            "a María. El pronombre femenino debe resolver correctamente."
        ),
    },
    {
        "id": "prox_02_reverse_order",
        "text": "María miró a Juan. Él era alto y de pelo negro.",
        "expected": {"Juan": {"height": "alto", "hair_color": "negro"}},
        "forbidden": {"María": ["height", "hair_color"]},
        "reason": (
            "María aparece primero pero 'Él' refiere a Juan. El sesgo de "
            "proximidad podría asignar 'alto' a María si no se resuelve 'Él'."
        ),
    },
    {
        "id": "prox_03_interleaved_descriptions",
        "text": (
            "Pedro era rubio y fuerte. Ana, su compañera, tenía el pelo castaño "
            "y ojos marrones. Pedro también tenía una cicatriz en la mejilla."
        ),
        "expected": {
            "Pedro": {"hair_color": "rubio"},
            "Ana": {"hair_color": "castaño", "eye_color": "marrones"},
        },
        "forbidden": {"Pedro": ["eye_color"], "Ana": ["hair_color_rubio"]},
        "reason": (
            "Descripciones intercaladas de dos personajes. El extractor debe "
            "separar correctamente qué atributo pertenece a quién."
        ),
    },
    {
        "id": "prox_04_far_subject",
        "text": (
            "Carlos entró en la habitación donde estaba Elena hablando con "
            "el portero del edificio. Tenía los ojos azules y el pelo canoso."
        ),
        "expected": {"Carlos": {"eye_color": "azules", "hair_color": "canoso"}},
        "forbidden": {"Elena": ["eye_color", "hair_color"]},
        "reason": (
            "Carlos es el sujeto de la oración anterior pero Elena y 'el portero' "
            "están más cerca. El sujeto elíptico 'Tenía' refiere a Carlos "
            "como sujeto principal del párrafo."
        ),
    },
    {
        "id": "prox_05_two_females",
        "text": (
            "Lucía y Carmen compartían habitación. Lucía era alta y delgada, "
            "con ojos claros. Carmen, en cambio, era baja y robusta."
        ),
        "expected": {
            "Lucía": {"height": "alta", "eye_color": "claros"},
            "Carmen": {"height": "baja"},
        },
        "forbidden": {"Carmen": ["eye_color"]},
        "reason": (
            "Dos personajes femeninos dificultan la resolución por género. "
            "El extractor debe usar posición y sintaxis, no solo género."
        ),
    },
    # -------------------------------------------------------------------------
    # 2. GENDER MISMATCH - Género del pronombre no concuerda con asignación
    # -------------------------------------------------------------------------
    {
        "id": "gender_01_ella_not_he",
        "text": "Juan habló con María. Ella era pelirroja y tenía pecas.",
        "expected": {"María": {"hair_color": "pelirroja"}},
        "forbidden": {"Juan": ["hair_color"]},
        "reason": (
            "'Ella' es inequívocamente femenino. No debe asignarse a Juan, "
            "aunque Juan esté más cerca posicionalmente."
        ),
    },
    {
        "id": "gender_02_possessive_su",
        "text": (
            "María Sánchez se peinaba frente al espejo. Su cabello negro "
            "brillaba bajo la luz. Juan la observaba desde la puerta."
        ),
        "expected": {"María Sánchez": {"hair_color": "negro"}},
        "forbidden": {"Juan": ["hair_color"]},
        "reason": (
            "Replica el bug real: 'Su cabello negro' pertenece a María Sánchez "
            "(sujeto de 'se peinaba'), no a Juan que aparece después."
        ),
    },
    {
        "id": "gender_03_ambiguous_su",
        "text": ("Pedro y Marta cenaron juntos. Su pelo rubio le caía sobre los hombros."),
        "expected": {"Marta": {"hair_color": "rubio"}},
        "forbidden": {"Pedro": ["hair_color"]},
        "reason": (
            "'Su pelo rubio le caía sobre los hombros' - el verbo 'caía sobre "
            "los hombros' sugiere pelo largo (estereotípicamente femenino), "
            "pero el extractor debería resolver por contexto pragmático."
        ),
    },
    {
        "id": "gender_04_compound_name_female",
        "text": "María del Carmen García tenía los ojos negros como la noche.",
        "expected": {"María del Carmen García": {"eye_color": "negros"}},
        "forbidden": {},
        "reason": (
            "Nombre compuesto femenino con preposición. El extractor podría "
            "fragmentar el nombre y no asignar el atributo correctamente."
        ),
    },
    {
        "id": "gender_05_mixed_group",
        "text": (
            "Roberto, Clara y Miguel entraron al salón. Ella tenía el pelo "
            "rizado y los ojos miel. Él, el más joven, era pelirrojo."
        ),
        "expected": {
            "Clara": {"hair_color": "rizado", "eye_color": "miel"},
            "Miguel": {"hair_color": "pelirrojo"},
        },
        "forbidden": {
            "Roberto": ["hair_color", "eye_color"],
        },
        "reason": (
            "Grupo mixto de tres. 'Ella' → Clara (única mujer). "
            "'Él, el más joven' → Miguel (último masculino mencionado). "
            "Roberto no recibe atributos."
        ),
    },
    # -------------------------------------------------------------------------
    # 3. DIALOGUE ATTRIBUTION - Atributos dichos EN diálogo vs DEL hablante
    # -------------------------------------------------------------------------
    {
        "id": "dialog_01_description_by_other",
        "text": (
            "—¿Has visto a Laura? —preguntó Miguel.\n"
            "—Sí, la de ojos verdes y pelo largo —respondió Carlos."
        ),
        "expected": {"Laura": {"eye_color": "verdes"}},
        "forbidden": {"Carlos": ["eye_color"], "Miguel": ["eye_color"]},
        "reason": (
            "Carlos DESCRIBE a Laura. Los ojos verdes son de Laura, "
            "no de Carlos (hablante) ni de Miguel (interlocutor)."
        ),
    },
    {
        "id": "dialog_02_self_description",
        "text": ("—Soy alto y moreno —dijo Rafael—. Siempre me lo dicen."),
        "expected": {"Rafael": {"height": "alto", "hair_color": "moreno"}},
        "forbidden": {},
        "reason": (
            "Autodescripción en diálogo. Los atributos pertenecen al hablante "
            "(Rafael), no a una tercera persona mencionada."
        ),
    },
    {
        "id": "dialog_03_description_in_reply",
        "text": (
            "—¿Cómo es tu hermana? —preguntó Elena.\n"
            "—Tiene los ojos azules y es bajita —dijo Pablo."
        ),
        "expected": {},  # La hermana no tiene nombre, no asignar a Elena ni Pablo
        "forbidden": {"Elena": ["eye_color", "height"], "Pablo": ["eye_color", "height"]},
        "reason": (
            "Pablo describe a su hermana (sin nombre). Los atributos NO "
            "pertenecen ni a Elena ni a Pablo."
        ),
    },
    {
        "id": "dialog_04_indirect_description",
        "text": (
            "Marcos le dijo a Sofía que tenía unos ojos preciosos. "
            "Sofía se sonrojó; sus ojos eran de color miel."
        ),
        "expected": {"Sofía": {"eye_color": "miel"}},
        "forbidden": {"Marcos": ["eye_color"]},
        "reason": (
            "Marcos habla sobre los ojos de Sofía. 'sus ojos eran de color miel' "
            "refiere a Sofía explícitamente."
        ),
    },
    # -------------------------------------------------------------------------
    # 4. SUBORDINATE CLAUSES - Atributos en cláusulas subordinadas
    # -------------------------------------------------------------------------
    {
        "id": "subord_01_while_clause",
        "text": ("Mientras Ana leía, Pedro se miraba al espejo. Era rubio y de ojos claros."),
        "expected": {"Pedro": {"hair_color": "rubio", "eye_color": "claros"}},
        "forbidden": {"Ana": ["hair_color", "eye_color"]},
        "reason": (
            "Cláusula temporal 'Mientras Ana leía' es subordinada. "
            "El sujeto principal es Pedro, que es quien 'se miraba al espejo'."
        ),
    },
    {
        "id": "subord_02_because_clause",
        "text": ("Porque Laura se lo pidió, Manuel se cortó el pelo. Antes era castaño y largo."),
        "expected": {"Manuel": {"hair_color": "castaño"}},
        "forbidden": {"Laura": ["hair_color"]},
        "reason": (
            "La cláusula causal 'Porque Laura se lo pidió' es subordinada. "
            "El pelo castaño y largo era de Manuel (sujeto de 'se cortó el pelo')."
        ),
    },
    {
        "id": "subord_03_conditional",
        "text": (
            "Si Elena no hubiera sido tan alta, Jorge no la habría notado. "
            "Medía casi un metro ochenta."
        ),
        "expected": {"Elena": {"height": "alta"}},
        "forbidden": {"Jorge": ["height"]},
        "reason": (
            "Condicional con sujeto en cláusula if. 'Medía casi un metro ochenta' "
            "refiere a Elena (la 'alta'), no a Jorge."
        ),
    },
    # -------------------------------------------------------------------------
    # 5. NEGATED ATTRIBUTES - Atributos negados confundidos con afirmativos
    # -------------------------------------------------------------------------
    {
        "id": "neg_01_not_tall",
        "text": "David no era alto. Isabel sí lo era.",
        "expected": {"Isabel": {"height": "alto"}},
        "forbidden": {},
        "reason": (
            "'David no era alto' niega el atributo para David. "
            "'Isabel sí lo era' afirma el atributo. El extractor debe distinguir "
            "negación (no) de afirmación (sí)."
        ),
    },
    {
        "id": "neg_02_despite",
        "text": "A pesar de no tener los ojos azules como su padre, Sara era hermosa.",
        "expected": {},
        "forbidden": {"Sara": ["eye_color"]},
        "reason": (
            "'no tener los ojos azules' niega explícitamente el atributo para Sara. "
            "El extractor no debe asignar eye_color=azules a Sara."
        ),
    },
    {
        "id": "neg_03_contrast_negation",
        "text": ("Rosa no tenía el pelo negro como Eva; el suyo era cobrizo."),
        "expected": {
            "Eva": {"hair_color": "negro"},
            "Rosa": {"hair_color": "cobrizo"},
        },
        "forbidden": {},
        "reason": (
            "Contraste con negación. 'pelo negro' → Eva. "
            "'cobrizo' → Rosa. El extractor debe separar ambos."
        ),
    },
    # -------------------------------------------------------------------------
    # 6. COMPARISONS - Comparaciones entre personajes confunden asignación
    # -------------------------------------------------------------------------
    {
        "id": "comp_01_taller_than",
        "text": "Andrés era más alto que Beatriz, quien apenas llegaba al metro sesenta.",
        "expected": {
            "Andrés": {"height": "alto"},
            "Beatriz": {"height": "metro sesenta"},
        },
        "forbidden": {},
        "reason": (
            "Comparación directa. 'más alto' → Andrés. "
            "'metro sesenta' → Beatriz. El extractor puede confundir "
            "a quién pertenece cada atributo en una comparación."
        ),
    },
    {
        "id": "comp_02_like_father",
        "text": "Tomás tenía los ojos de su madre: grandes, verdes y expresivos.",
        "expected": {"Tomás": {"eye_color": "verdes"}},
        "forbidden": {},
        "reason": (
            "'los ojos de su madre' establece herencia pero el poseedor "
            "actual es Tomás. La madre no tiene nombre, así que los atributos "
            "deben ir a Tomás."
        ),
    },
    {
        "id": "comp_03_unlike",
        "text": (
            "A diferencia de su hermano Ricardo, que era moreno, Estela era rubia y de tez clara."
        ),
        "expected": {
            "Ricardo": {"hair_color": "moreno"},
            "Estela": {"hair_color": "rubia"},
        },
        "forbidden": {},
        "reason": (
            "Contraste explícito: 'moreno' → Ricardo, 'rubia' → Estela. "
            "La frase 'A diferencia de' señala oposición."
        ),
    },
    {
        "id": "comp_04_same_as",
        "text": "Gloria tenía el mismo tono de pelo que Nuria: castaño oscuro.",
        "expected": {
            "Gloria": {"hair_color": "castaño oscuro"},
            "Nuria": {"hair_color": "castaño oscuro"},
        },
        "forbidden": {},
        "reason": (
            "Comparación de igualdad. 'castaño oscuro' aplica a AMBAS entidades. "
            "El extractor podría asignar solo a una."
        ),
    },
    # -------------------------------------------------------------------------
    # 7. ENUMERATIONS - Listas de personajes con atributos intercalados
    # -------------------------------------------------------------------------
    {
        "id": "enum_01_list_with_attrs",
        "text": (
            "En la foto aparecían: Luis, de ojos azules; Teresa, pelirroja; "
            "y Marcos, el más alto de los tres."
        ),
        "expected": {
            "Luis": {"eye_color": "azules"},
            "Teresa": {"hair_color": "pelirroja"},
            "Marcos": {"height": "alto"},
        },
        "forbidden": {},
        "reason": (
            "Enumeración con atributos individuales separados por punto y coma. "
            "Cada atributo pertenece al personaje inmediatamente anterior."
        ),
    },
    {
        "id": "enum_02_first_last",
        "text": (
            "Diana, Raúl, Silvia y Óscar se sentaron en fila. "
            "La primera era la más joven; el último, el más viejo."
        ),
        "expected": {
            "Diana": {"age": "joven"},
            "Óscar": {"age": "viejo"},
        },
        "forbidden": {"Raúl": ["age"], "Silvia": ["age"]},
        "reason": (
            "Referencia posicional: 'La primera' → Diana, 'el último' → Óscar. "
            "El extractor debe resolver referencias ordinales."
        ),
    },
    # -------------------------------------------------------------------------
    # 8. NARRATIVE FOCUS SHIFT - Cambio de foco narrativo
    # -------------------------------------------------------------------------
    {
        "id": "focus_01_paragraph_break",
        "text": (
            "Javier caminaba por la calle pensando en sus problemas. Era delgado "
            "y pálido, con ojeras marcadas.\n\n"
            "Alicia lo esperaba en el café. Tenía los ojos brillantes y el pelo "
            "recogido en una trenza."
        ),
        "expected": {
            "Javier": {"build": "delgado"},
            "Alicia": {"eye_color": "brillantes"},
        },
        "forbidden": {"Javier": ["eye_color"], "Alicia": ["build"]},
        "reason": (
            "Cambio de párrafo = cambio de foco. El primer párrafo describe "
            "a Javier, el segundo a Alicia. El sujeto elíptico 'Era' en el "
            "primer párrafo refiere a Javier; 'Tenía' en el segundo a Alicia."
        ),
    },
    {
        "id": "focus_02_scene_change",
        "text": (
            "Mario salió de casa. Alto y desgarbado, caminaba sin prisa. "
            "En la oficina, Claudia revisaba papeles. Era rubia y siempre "
            "vestía de negro."
        ),
        "expected": {
            "Mario": {"height": "alto"},
            "Claudia": {"hair_color": "rubia"},
        },
        "forbidden": {"Mario": ["hair_color"], "Claudia": ["height"]},
        "reason": (
            "Cambio de escena: 'En la oficina' inicia nuevo contexto. "
            "Cada personaje recibe sus propios atributos."
        ),
    },
    {
        "id": "focus_03_flashback",
        "text": (
            "Fernando recordaba a su abuela. Ella tenía los ojos grises y la "
            "piel arrugada. Fernando, en cambio, había heredado los ojos oscuros "
            "de su madre."
        ),
        "expected": {
            "Fernando": {"eye_color": "oscuros"},
        },
        "forbidden": {"Fernando": ["eye_color_grises"]},
        "reason": (
            "'Ella tenía los ojos grises' → abuela (sin nombre). "
            "'Fernando había heredado los ojos oscuros' → Fernando. "
            "El extractor no debe asignar 'grises' a Fernando."
        ),
    },
    # -------------------------------------------------------------------------
    # 9. REAL BUG REPRODUCTION - Replicas del error encontrado en producción
    # -------------------------------------------------------------------------
    {
        "id": "real_bug_01_maria_juan",
        "text": (
            "María Sánchez caminaba por el parque. Tenía el pelo castaño y "
            "los ojos marrones. Juan Pérez la saludó desde el banco."
        ),
        "expected": {
            "María Sánchez": {"hair_color": "castaño", "eye_color": "marrones"},
        },
        "forbidden": {"Juan Pérez": ["hair_color", "eye_color"]},
        "reason": (
            "REPLICA DEL BUG REAL: En producción, _find_nearest_entity() "
            "asignaba 'castaño' y 'marrones' a Juan porque el gender detection "
            "priorizaba masculinos. María es el sujeto correcto."
        ),
    },
    {
        "id": "real_bug_02_all_to_nearest",
        "text": (
            "María era alta y delgada, con ojos verdes y pelo rubio. Juan era bajo y robusto."
        ),
        "expected": {
            "María": {"height": "alta", "eye_color": "verdes", "hair_color": "rubio"},
            "Juan": {"height": "bajo"},
        },
        "forbidden": {"Juan": ["eye_color", "hair_color"]},
        "reason": (
            "REPLICA DEL BUG REAL: Cuando LLM y embeddings fallan, solo "
            "pattern-based extraction funciona. Todos los atributos del párrafo "
            "iban a Juan por proximidad."
        ),
    },
    {
        "id": "real_bug_03_compound_name_split",
        "text": (
            "María Sánchez tenía los ojos azules. Su hijo pequeño, Juan, había heredado esos ojos."
        ),
        "expected": {"María Sánchez": {"eye_color": "azules"}},
        "forbidden": {},
        "reason": (
            "REPLICA DEL BUG REAL: El nombre compuesto 'María Sánchez' podría "
            "fragmentarse como 'María' y 'Sánchez' por separado, causando "
            "que el atributo no se asigne correctamente."
        ),
    },
    {
        "id": "real_bug_04_multiple_attrs_same_entity",
        "text": (
            "La detective Clara Vidal era una mujer de unos cuarenta años, "
            "alta, de pelo negro azabache y ojos grises penetrantes. "
            "Su compañero, el agente Tomás Ruiz, era joven y nervioso."
        ),
        "expected": {
            "Clara Vidal": {
                "age": "cuarenta",
                "height": "alta",
                "hair_color": "negro azabache",
                "eye_color": "grises",
            },
            "Tomás Ruiz": {"age": "joven"},
        },
        "forbidden": {"Tomás Ruiz": ["height", "hair_color", "eye_color"]},
        "reason": (
            "Descripción extensa de un personaje seguida de breve descripción "
            "de otro. Todos los atributos de Clara podrían ir a Tomás por "
            "proximidad."
        ),
    },
    # -------------------------------------------------------------------------
    # 10. POSSESSIVE CHAINS - Cadenas posesivas complejas
    # -------------------------------------------------------------------------
    {
        "id": "poss_01_de_chain",
        "text": ("Los ojos de Isabel eran del mismo color que los de su madre: azul profundo."),
        "expected": {"Isabel": {"eye_color": "azul profundo"}},
        "forbidden": {},
        "reason": (
            "Cadena posesiva 'Los ojos de Isabel'. La preposición 'de' indica "
            "pertenencia. 'su madre' es otro referente sin nombre."
        ),
    },
    {
        "id": "poss_02_nested_possessive",
        "text": "El pelo de la hermana de Santiago era negro como el carbón.",
        "expected": {},  # La hermana no tiene nombre
        "forbidden": {"Santiago": ["hair_color"]},
        "reason": (
            "Posesivo anidado: 'El pelo de la hermana de Santiago'. El pelo "
            "NO es de Santiago, sino de su hermana (sin nombre)."
        ),
    },
    {
        "id": "poss_03_reflexive",
        "text": "Valentina se miró las manos. Sus dedos eran largos y pálidos.",
        "expected": {"Valentina": {}},
        "forbidden": {},
        "reason": (
            "Reflexivo + posesivo. 'Sus dedos' refiere a Valentina. "
            "Los dedos no son un atributo estándar pero la resolución del "
            "posesivo debe funcionar correctamente."
        ),
    },
    # -------------------------------------------------------------------------
    # 11. INDIRECT REFERENCES - Referencias indirectas a entidades
    # -------------------------------------------------------------------------
    {
        "id": "indirect_01_the_woman",
        "text": ("La mujer de ojos verdes se llamaba Sara. Juan no podía dejar de mirarla."),
        "expected": {"Sara": {"eye_color": "verdes"}},
        "forbidden": {"Juan": ["eye_color"]},
        "reason": (
            "'La mujer de ojos verdes' es una referencia indirecta a Sara. "
            "El extractor debe vincular 'La mujer' → Sara → ojos verdes."
        ),
    },
    {
        "id": "indirect_02_occupation",
        "text": ("El médico era calvo y usaba gafas. Se llamaba doctor Hernández."),
        "expected": {"Hernández": {"hair_color": "calvo"}},
        "forbidden": {},
        "reason": (
            "'El médico' y 'doctor Hernández' son la misma entidad. "
            "El atributo 'calvo' debe asignarse a Hernández."
        ),
    },
    # -------------------------------------------------------------------------
    # 12. TEMPORAL DESCRIPTIONS - Atributos que cambian con el tiempo
    # -------------------------------------------------------------------------
    {
        "id": "temp_01_before_after",
        "text": (
            "Antes de la guerra, Hugo tenía el pelo negro. Ahora, diez años "
            "después, era completamente canoso."
        ),
        "expected": {"Hugo": {"hair_color": "canoso"}},
        "forbidden": {},
        "reason": (
            "Atributo temporal: el pelo de Hugo cambió de negro a canoso. "
            "El extractor debe priorizar el estado más reciente ('ahora')."
        ),
    },
    {
        "id": "temp_02_young_vs_old",
        "text": (
            "De joven, Pilar era rubia. Con los años se le oscureció el pelo hasta quedar castaño."
        ),
        "expected": {"Pilar": {"hair_color": "castaño"}},
        "forbidden": {},
        "reason": (
            "Cambio temporal de atributo. 'De joven' marca un estado anterior. "
            "El extractor debe tomar el valor actual (castaño)."
        ),
    },
    # -------------------------------------------------------------------------
    # 13. COMPLEX MULTI-ENTITY SCENES - Escenas con muchos personajes
    # -------------------------------------------------------------------------
    {
        "id": "multi_01_three_characters",
        "text": (
            "Alberto, Mónica y Sergio se reunieron en el café. Alberto era "
            "el más alto, con barba espesa. Mónica, de pelo corto y ojos "
            "verdes, pidió un café. Sergio, el más joven, tenía pecas."
        ),
        "expected": {
            "Alberto": {"height": "alto"},
            "Mónica": {"eye_color": "verdes"},
            "Sergio": {"age": "joven"},
        },
        "forbidden": {
            "Alberto": ["eye_color"],
            "Sergio": ["eye_color", "height"],
        },
        "reason": (
            "Tres personajes con descripciones intercaladas. Cada aposición "
            "descriptiva pertenece a su entidad inmediatamente anterior."
        ),
    },
    {
        "id": "multi_02_family_scene",
        "text": (
            "La familia García estaba completa: el padre, Ernesto, alto y "
            "canoso; la madre, Dolores, menuda y morena; y el hijo, Paco, "
            "un adolescente pecoso de ojos claros."
        ),
        "expected": {
            "Ernesto": {"height": "alto", "hair_color": "canoso"},
            "Dolores": {"build": "menuda", "hair_color": "morena"},
            "Paco": {"eye_color": "claros"},
        },
        "forbidden": {},
        "reason": (
            "Enumeración familiar con descripciones entre punto y coma. "
            "Cada miembro tiene sus propios atributos."
        ),
    },
    {
        "id": "multi_03_witness_lineup",
        "text": (
            "El testigo los describió: el primero era alto y rubio; el segundo, "
            "bajo y moreno; el tercero, de complexión media y calvo. Solo el "
            "primero coincidía con la descripción de Ramón."
        ),
        "expected": {"Ramón": {"height": "alto", "hair_color": "rubio"}},
        "forbidden": {},
        "reason": (
            "Descripciones anónimas que luego se vinculan a un nombre. "
            "'el primero coincidía con Ramón' → Ramón es alto y rubio."
        ),
    },
    # -------------------------------------------------------------------------
    # 14. APPEARANCE IN NARRATION vs. REALITY
    # -------------------------------------------------------------------------
    {
        "id": "appear_01_seemed",
        "text": "Pablo parecía más joven de lo que era. En realidad tenía cuarenta años.",
        "expected": {"Pablo": {"age": "cuarenta"}},
        "forbidden": {},
        "reason": (
            "'parecía más joven' es apariencia, 'tenía cuarenta años' es el "
            "dato real. El extractor debe preferir datos factuales."
        ),
    },
    {
        "id": "appear_02_disguise",
        "text": ("Isabel se disfrazó con una peluca rubia, pero en realidad era morena."),
        "expected": {"Isabel": {"hair_color": "morena"}},
        "forbidden": {},
        "reason": (
            "'peluca rubia' es un disfraz, no el atributo real. "
            "'en realidad era morena' es el dato verdadero."
        ),
    },
    # -------------------------------------------------------------------------
    # 15. REPORTED SPEECH - Estilo indirecto
    # -------------------------------------------------------------------------
    {
        "id": "reported_01_said_that",
        "text": (
            "Marcos dijo que Sonia tenía los ojos más bonitos del mundo. Eran de color avellana."
        ),
        "expected": {"Sonia": {"eye_color": "avellana"}},
        "forbidden": {"Marcos": ["eye_color"]},
        "reason": (
            "Estilo indirecto: Marcos habla SOBRE Sonia. Los ojos avellana "
            "son de Sonia, no de Marcos."
        ),
    },
    {
        "id": "reported_02_remembered",
        "text": (
            "Felipe recordaba que Inés era pelirroja cuando se conocieron. "
            "Él, en cambio, siempre había sido moreno."
        ),
        "expected": {
            "Inés": {"hair_color": "pelirroja"},
            "Felipe": {"hair_color": "moreno"},
        },
        "forbidden": {},
        "reason": (
            "Recuerdo de atributo ajeno + contraste con propio. "
            "'Inés era pelirroja' (estilo indirecto) y 'Él...moreno' (contraste)."
        ),
    },
]


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture
def extractor():
    """Crea una instancia del extractor de atributos sin LLM/embeddings."""
    return AttributeExtractor(
        filter_metaphors=True,
        min_confidence=0.5,
        use_llm=False,
        use_embeddings=False,
        use_dependency_extraction=True,
        use_patterns=True,
    )


def extract_and_organize(extractor: AttributeExtractor, text: str) -> dict:
    """
    Extrae atributos y los organiza por entidad para comparación.

    Returns:
        Dict de entidad -> {key: value, ...}
    """

    name_pattern = r"\b([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+(?:de(?:l|\s+la|\s+los|\s+las)?\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)*)\b"
    entity_mentions = []

    common_words = {
        "El",
        "La",
        "Los",
        "Las",
        "Un",
        "Una",
        "Unos",
        "Unas",
        "De",
        "En",
        "Con",
        "Por",
        "Para",
        "Sin",
        "Sobre",
        "Tras",
        "Antes",
        "Despues",
        "Según",
        "Durante",
        "Mediante",
        "Era",
        "Tenia",
        "Fue",
        "Habia",
        "Dijo",
        "Pensó",
        "Verdes",
        "Azules",
        "Negros",
        "Rubio",
        "Moreno",
        "Canoso",
        "Alto",
        "Bajo",
        "Delgado",
        "Gordo",
        "Pero",
        "Sino",
        "Aunque",
        "Ella",
        "Sí",
        "Ahora",
        "Solo",
        "Mientras",
        "Porque",
        "Cuando",
        "Donde",
        "Tiene",
        "Tenía",
        "Eran",
        "Soy",
        "Siempre",
        "También",
        "Como",
        "Medía",
        "Sus",
    }

    for match in re.finditer(name_pattern, text):
        name = match.group(1)
        words = name.split()
        if words[0] not in common_words and len(name) > 2:
            entity_mentions.append((name, match.start(), match.end(), "PER"))

    extraction_result = extractor.extract_attributes(text, entity_mentions=entity_mentions)

    if extraction_result.is_failure:
        return {}

    result = extraction_result.value

    by_entity = {}
    for attr in result.attributes:
        entity = attr.entity_name
        if entity not in by_entity:
            by_entity[entity] = {}
        by_entity[entity][attr.key.value] = attr.value

    return by_entity


# =============================================================================
# TEST CLASSES - Individual categories
# =============================================================================


class TestProximityBias:
    """Tests para sesgo de proximidad en asignación de atributos."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("prox_")],
        ids=lambda c: c["id"],
    )
    def test_proximity_bias(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] Entidad '{entity}' no encontrada.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )
            for key, value in expected_attrs.items():
                assert result[entity].get(key) == value, (
                    f"[{case['id']}] Atributo '{key}' de '{entity}' incorrecto.\n"
                    f"Esperado: {value}, Obtenido: {result[entity].get(key)}\n"
                    f"Razón: {case['reason']}"
                )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] Atributo '{key}' NO debería estar en '{entity}'.\n"
                        f"Valor asignado: {result[entity].get(key)}\n"
                        f"Razón: {case['reason']}"
                    )


class TestGenderMismatch:
    """Tests para errores de género en resolución de entidades."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("gender_")],
        ids=lambda c: c["id"],
    )
    def test_gender_mismatch(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] Entidad '{entity}' no encontrada.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] Atributo '{key}' asignado incorrectamente a '{entity}'.\n"
                        f"Razón: {case['reason']}"
                    )


class TestDialogueAttribution:
    """Tests para atributos en diálogos."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("dialog_")],
        ids=lambda c: c["id"],
    )
    def test_dialogue_attribution(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] Entidad '{entity}' no encontrada en diálogo.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] Atributo '{key}' no debería asignarse a '{entity}' (hablante/oyente).\n"
                        f"Razón: {case['reason']}"
                    )


class TestSubordinateClauses:
    """Tests para cláusulas subordinadas."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("subord_")],
        ids=lambda c: c["id"],
    )
    def test_subordinate_clauses(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] Sujeto '{entity}' no resuelto en cláusula subordinada.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] Atributo '{key}' asignado al sujeto subordinado '{entity}'.\n"
                        f"Razón: {case['reason']}"
                    )


class TestNegatedAttributes:
    """Tests para atributos negados."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("neg_")],
        ids=lambda c: c["id"],
    )
    def test_negated_attributes(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            if expected_attrs:
                assert entity in result, (
                    f"[{case['id']}] Entidad '{entity}' no encontrada.\n"
                    f"Razón: {case['reason']}\n"
                    f"Resultado: {result}"
                )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] Atributo negado '{key}' asignado a '{entity}'.\n"
                        f"Razón: {case['reason']}"
                    )


class TestComparisons:
    """Tests para comparaciones entre personajes."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("comp_")],
        ids=lambda c: c["id"],
    )
    def test_comparisons(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] Entidad '{entity}' no encontrada en comparación.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )


class TestRealBugReproductions:
    """Tests que replican bugs reales encontrados en producción."""

    @pytest.mark.parametrize(
        "case",
        [c for c in CROSS_ENTITY_CASES if c["id"].startswith("real_bug_")],
        ids=lambda c: c["id"],
    )
    def test_real_bug_reproduction(self, extractor, case):
        result = extract_and_organize(extractor, case["text"])

        for entity, expected_attrs in case["expected"].items():
            assert entity in result, (
                f"[{case['id']}] BUG REAL: Entidad '{entity}' no encontrada.\n"
                f"Razón: {case['reason']}\n"
                f"Resultado: {result}"
            )
            for key, value in expected_attrs.items():
                assert result[entity].get(key) == value, (
                    f"[{case['id']}] BUG REAL: Atributo '{key}' de '{entity}' incorrecto.\n"
                    f"Esperado: {value}, Obtenido: {result[entity].get(key)}\n"
                    f"Razón: {case['reason']}"
                )

        for entity, forbidden_keys in case.get("forbidden", {}).items():
            if entity in result:
                for key in forbidden_keys:
                    assert key not in result[entity], (
                        f"[{case['id']}] BUG REAL: Atributo '{key}' asignado incorrectamente a '{entity}'.\n"
                        f"Razón: {case['reason']}"
                    )


# =============================================================================
# SUMMARY TEST - Estadísticas globales
# =============================================================================


class TestCrossEntitySummary:
    """Test de resumen que ejecuta todos los casos y reporta estadísticas."""

    def test_all_cross_entity_cases(self, extractor):
        """Ejecuta todos los casos y genera un informe."""
        passed = 0
        failed = 0
        forbidden_violations = 0
        errors = []

        for case in CROSS_ENTITY_CASES:
            try:
                result = extract_and_organize(extractor, case["text"])
                case_passed = True

                # Check expected
                for entity, expected_attrs in case["expected"].items():
                    if entity not in result:
                        case_passed = False
                        break
                    for key, value in expected_attrs.items():
                        if value is not None and result[entity].get(key) != value:
                            case_passed = False
                            break

                # Check forbidden
                for entity, forbidden_keys in case.get("forbidden", {}).items():
                    if entity in result:
                        for key in forbidden_keys:
                            if key in result[entity]:
                                forbidden_violations += 1
                                case_passed = False

                if case_passed:
                    passed += 1
                else:
                    failed += 1
                    errors.append(
                        {
                            "id": case["id"],
                            "reason": case["reason"],
                            "expected": case["expected"],
                            "forbidden": case.get("forbidden", {}),
                            "got": result,
                        }
                    )

            except Exception as e:
                failed += 1
                errors.append({"id": case["id"], "error": str(e)})

        # Report
        print(f"\n{'=' * 70}")
        print("CROSS-ENTITY ATTRIBUTE ASSIGNMENT ADVERSARIAL REPORT")
        print(f"{'=' * 70}")
        print(f"Total cases: {len(CROSS_ENTITY_CASES)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Forbidden violations: {forbidden_violations}")
        print(f"Pass rate: {passed / len(CROSS_ENTITY_CASES) * 100:.1f}%")
        print(f"{'=' * 70}")

        if errors:
            print("\nFailed cases (first 15):")
            for err in errors[:15]:
                print(f"  - {err['id']}: {err.get('reason', err.get('error', 'Unknown'))[:100]}")

        # These tests are designed to expose weaknesses
        # If >60% pass, the algorithm is performing well
        assert failed > 0, (
            f"All {len(CROSS_ENTITY_CASES)} cases passed - "
            f"tests may be too easy or algorithm is excellent."
        )
