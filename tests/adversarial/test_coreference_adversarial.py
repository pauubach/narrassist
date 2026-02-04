"""
Tests adversariales GAN-style para el sistema de resolución de correferencias.

Objetivo: Identificar casos límite y edge cases donde el sistema falla,
para mejorar iterativamente el algoritmo.

Categorías de tests:
1. Pronombres personales (él, ella, lo, la)
2. Posesivos (su, sus, suyo)
3. Demostrativos (este, esa, aquellos)
4. Anáfora cero (pro-drop español)
5. Reflexivos (se, sí)
6. Concordancia género/número
7. Referencias ambiguas (múltiples candidatos)
8. Correferencia a distancia
9. Catáfora (referencia hacia adelante)
10. Cláusulas embebidas
11. SNs definidos ("el doctor", "la mujer")
12. Antecedentes divididos ("ellos" → múltiples entidades)
13. Anáfora ligada ("cada estudiante... su...")
14. Interferencia (entidades similares)
15. Patrones de narrador (primera persona)
16. Cambio de tópico
17. Elipsis verbal
18. Pronombres objeto
19. Coordinación
20. Comparativas

Basado en literatura lingüística:
- Ariel (1990): Accessibility Theory
- Grosz et al. (1995): Centering Theory
- Walker et al. (1998): Centering for Spanish
"""

from dataclasses import dataclass
from typing import Optional

import pytest


@dataclass
class CorefTestCase:
    """Caso de test para correferencia."""

    id: str
    category: str
    text: str
    expected_chains: list[tuple[str, list[str]]]  # [(main_mention, [coreferent_mentions])]
    anti_chains: list[tuple[str, str]] = None  # [(entity, should_NOT_include)]
    difficulty: str = "medium"  # easy, medium, hard, adversarial
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: PRONOMBRES PERSONALES (él, ella, lo, la, etc.)
# =============================================================================

PRONOUN_TESTS = [
    CorefTestCase(
        id="pron_01_simple_el",
        category="pronombres",
        text="Juan entró en la habitación. Él estaba cansado.",
        expected_chains=[("Juan", ["Él"])],
        difficulty="easy",
        linguistic_note="Pronombre sujeto simple, mismo párrafo",
    ),
    CorefTestCase(
        id="pron_02_simple_ella",
        category="pronombres",
        text="María cerró la puerta. Ella suspiró aliviada.",
        expected_chains=[("María", ["Ella"])],
        difficulty="easy",
        linguistic_note="Pronombre sujeto femenino simple",
    ),
    CorefTestCase(
        id="pron_03_object_lo",
        category="pronombres",
        text="Juan llegó a casa. María lo recibió con una sonrisa.",
        expected_chains=[("Juan", ["lo"])],
        difficulty="medium",
        linguistic_note="Pronombre objeto directo masculino",
    ),
    CorefTestCase(
        id="pron_04_object_la",
        category="pronombres",
        text="María estaba esperando. Juan la vio desde lejos.",
        expected_chains=[("María", ["la"])],
        difficulty="medium",
        linguistic_note="Pronombre objeto directo femenino",
    ),
    CorefTestCase(
        id="pron_05_indirect_le",
        category="pronombres",
        text="Pedro necesitaba ayuda. Ana le ofreció su apoyo.",
        expected_chains=[("Pedro", ["le"])],
        difficulty="medium",
        linguistic_note="Pronombre objeto indirecto (ambiguo en género)",
    ),
    CorefTestCase(
        id="pron_06_two_entities_gender",
        category="pronombres",
        text="Juan y María hablaron. Él parecía nervioso.",
        expected_chains=[("Juan", ["Él"])],
        anti_chains=[("María", "Él")],
        difficulty="medium",
        linguistic_note="Desambiguación por género",
    ),
    CorefTestCase(
        id="pron_07_two_same_gender",
        category="pronombres",
        text="Juan y Pedro discutieron. Él se fue enfadado.",
        expected_chains=[("Juan", ["Él"])],  # Centering: sujeto más prominente
        difficulty="hard",
        linguistic_note="Ambigüedad de género - resolver por prominencia (Centering)",
    ),
    CorefTestCase(
        id="pron_08_plural_ellos",
        category="pronombres",
        text="Los niños jugaban en el parque. Ellos reían sin parar.",
        expected_chains=[("Los niños", ["Ellos"])],
        difficulty="easy",
        linguistic_note="Pronombre plural simple",
    ),
    CorefTestCase(
        id="pron_09_usted_formal",
        category="pronombres",
        text="El doctor García entró. —¿Cómo se encuentra usted hoy?",
        expected_chains=[],  # "usted" es segunda persona, no correferente con el doctor
        difficulty="medium",
        linguistic_note="Usted es 2ª persona, no correferencia con entidad 3ª",
    ),
    CorefTestCase(
        id="pron_10_across_paragraph",
        category="pronombres",
        text="""María trabajaba en el hospital.

Al día siguiente, ella llegó temprano.""",
        expected_chains=[("María", ["ella"])],
        difficulty="medium",
        linguistic_note="Correferencia entre párrafos",
    ),
]

# =============================================================================
# CATEGORÍA 2: POSESIVOS (su, sus, suyo, etc.)
# =============================================================================

POSSESSIVE_TESTS = [
    CorefTestCase(
        id="poss_01_simple_su",
        category="posesivos",
        text="María entró en la habitación. Su rostro mostraba preocupación.",
        expected_chains=[("María", ["Su"])],
        difficulty="easy",
        linguistic_note="Posesivo simple, oración siguiente",
    ),
    CorefTestCase(
        id="poss_02_sus_plural",
        category="posesivos",
        text="Juan se sentó. Sus ojos azules brillaban.",
        expected_chains=[("Juan", ["Sus"])],
        difficulty="easy",
        linguistic_note="Posesivo plural (objeto poseído plural)",
    ),
    CorefTestCase(
        id="poss_03_same_sentence",
        category="posesivos",
        text="María peinaba su largo cabello negro.",
        expected_chains=[("María", ["su"])],
        difficulty="easy",
        linguistic_note="Posesivo en misma oración",
    ),
    CorefTestCase(
        id="poss_04_ambiguous_two_entities",
        category="posesivos",
        text="Juan visitó a María. Su madre estaba enferma.",
        expected_chains=[("Juan", ["Su"])],  # Centering: sujeto es más prominente
        difficulty="hard",
        linguistic_note="Ambigüedad posesiva - el poseedor es el sujeto (Centering)",
    ),
    CorefTestCase(
        id="poss_05_object_possessor",
        category="posesivos",
        text="María miró a Juan. Sus ojos marrones la observaban.",
        expected_chains=[("Juan", ["Sus", "la"])],  # "Sus ojos" de Juan, "la" es María
        difficulty="hard",
        linguistic_note="Posesivo refiere al objeto cuando describe físico del objeto",
    ),
    CorefTestCase(
        id="poss_06_ojos_verdes_bug",
        category="posesivos",
        text="""María apareció en la cafetería del barrio. Sus ojos verdes llamaron la atención.

Juan entró poco después.""",
        expected_chains=[("María", ["Sus"])],
        anti_chains=[("Juan", "Sus")],
        difficulty="adversarial",
        linguistic_note="BUG CONOCIDO: 'Sus' debe resolver a María, no a Juan",
    ),
    CorefTestCase(
        id="poss_07_nested_possession",
        category="posesivos",
        text="María vio a su hermana. Su vestido era azul.",
        expected_chains=[("su hermana", ["Su"])],  # El segundo "Su" refiere a la hermana
        difficulty="hard",
        linguistic_note="Posesión anidada - entidad más reciente",
    ),
    CorefTestCase(
        id="poss_08_tonic_possessive",
        category="posesivos",
        text="El libro era suyo. María lo había comprado ayer.",
        expected_chains=[("María", ["suyo"])],  # Catáfora: posesivo antes del nombre
        difficulty="hard",
        linguistic_note="Posesivo tónico con catáfora",
    ),
    CorefTestCase(
        id="poss_09_multiple_possessives",
        category="posesivos",
        text="Juan cuidaba de su madre. Su padre había fallecido hace años.",
        expected_chains=[("Juan", ["su", "Su"])],
        difficulty="medium",
        linguistic_note="Múltiples posesivos del mismo poseedor",
    ),
    CorefTestCase(
        id="poss_10_possessive_in_dialogue",
        category="posesivos",
        text='María dijo: "Mi hermano llegará pronto". Su voz temblaba.',
        expected_chains=[("María", ["Su"])],
        difficulty="medium",
        linguistic_note="Posesivo después de diálogo - refiere al hablante",
    ),
]

# =============================================================================
# CATEGORÍA 3: DEMOSTRATIVOS (este, esa, aquellos, etc.)
# =============================================================================

DEMONSTRATIVE_TESTS = [
    CorefTestCase(
        id="demo_01_este",
        category="demostrativos",
        text="Conocí a un hombre muy alto. Este me contó su historia.",
        expected_chains=[("un hombre muy alto", ["Este"])],
        difficulty="medium",
        linguistic_note="Demostrativo proximal",
    ),
    CorefTestCase(
        id="demo_02_esa",
        category="demostrativos",
        text="Vi a una mujer elegante. Esa llevaba un vestido rojo.",
        expected_chains=[("una mujer elegante", ["Esa"])],
        difficulty="medium",
        linguistic_note="Demostrativo medial femenino",
    ),
    CorefTestCase(
        id="demo_03_aquellos",
        category="demostrativos",
        text="Los soldados marchaban. Aquellos parecían exhaustos.",
        expected_chains=[("Los soldados", ["Aquellos"])],
        difficulty="medium",
        linguistic_note="Demostrativo distal plural",
    ),
    CorefTestCase(
        id="demo_04_contrast_este_aquel",
        category="demostrativos",
        text="Juan y Pedro entraron. Este llevaba sombrero, aquel no.",
        expected_chains=[("Pedro", ["Este"]), ("Juan", ["aquel"])],
        difficulty="adversarial",
        linguistic_note="Contraste este/aquel: este=más cercano textualmente, aquel=más lejano",
    ),
    CorefTestCase(
        id="demo_05_abstract_reference",
        category="demostrativos",
        text="María ganó el premio. Esto la hizo muy feliz.",
        expected_chains=[],  # "Esto" refiere al evento, no a María
        difficulty="medium",
        linguistic_note="'Esto' abstracto no es correferente con entidad",
    ),
]

# =============================================================================
# CATEGORÍA 4: ANÁFORA CERO (PRO-DROP)
# =============================================================================

ZERO_ANAPHORA_TESTS = [
    CorefTestCase(
        id="zero_01_simple",
        category="anafora_cero",
        text="María entró en la casa. Cerró la puerta con cuidado.",
        expected_chains=[("María", ["Ø"])],  # Sujeto implícito en "Cerró"
        difficulty="medium",
        linguistic_note="Pro-drop simple: sujeto de oración anterior",
    ),
    CorefTestCase(
        id="zero_02_chain",
        category="anafora_cero",
        text="Juan llegó tarde. Se quitó el abrigo. Encendió la luz.",
        expected_chains=[("Juan", ["Ø", "Ø"])],  # Dos sujetos implícitos
        difficulty="medium",
        linguistic_note="Cadena de sujetos elípticos",
    ),
    CorefTestCase(
        id="zero_03_switch",
        category="anafora_cero",
        text="María vio a Juan. Le saludó con la mano.",
        expected_chains=[("María", ["Ø"])],  # María es quien saluda
        difficulty="hard",
        linguistic_note="Pro-drop con cambio de foco - sujeto mantiene prominencia",
    ),
    CorefTestCase(
        id="zero_04_passive_like",
        category="anafora_cero",
        text="Se abrió la puerta. María entró rápidamente.",
        expected_chains=[],  # "Se abrió" es impersonal
        difficulty="medium",
        linguistic_note="'Se' impersonal, no correferencial",
    ),
    CorefTestCase(
        id="zero_05_infinitive",
        category="anafora_cero",
        text="María quería salir. Decidió esperar un poco más.",
        expected_chains=[("María", ["Ø"])],  # Sujeto de "Decidió"
        difficulty="medium",
        linguistic_note="Pro-drop con infinitivo coordinado",
    ),
]

# =============================================================================
# CATEGORÍA 5: REFLEXIVOS (se, sí)
# =============================================================================

REFLEXIVE_TESTS = [
    CorefTestCase(
        id="refl_01_simple_se",
        category="reflexivos",
        text="María se miró en el espejo.",
        expected_chains=[("María", ["se"])],
        difficulty="easy",
        linguistic_note="Reflexivo simple",
    ),
    CorefTestCase(
        id="refl_02_consigo",
        category="reflexivos",
        text="Juan hablaba consigo mismo.",
        expected_chains=[("Juan", ["consigo"])],
        difficulty="easy",
        linguistic_note="Reflexivo tónico",
    ),
    CorefTestCase(
        id="refl_03_reciprocal",
        category="reflexivos",
        text="Juan y María se miraron.",
        expected_chains=[("Juan y María", ["se"])],  # Recíproco
        difficulty="medium",
        linguistic_note="'Se' recíproco con sujeto coordinado",
    ),
    CorefTestCase(
        id="refl_04_impersonal_se",
        category="reflexivos",
        text="Se dice que María es muy inteligente.",
        expected_chains=[],  # "Se" impersonal, no correferencial
        difficulty="medium",
        linguistic_note="'Se' impersonal, no correferencial",
    ),
    CorefTestCase(
        id="refl_05_middle_se",
        category="reflexivos",
        text="La puerta se abrió. María entró.",
        expected_chains=[],  # "Se" de voz media
        difficulty="medium",
        linguistic_note="'Se' de voz media, no correferencial",
    ),
]

# =============================================================================
# CATEGORÍA 6: CONCORDANCIA GÉNERO/NÚMERO
# =============================================================================

AGREEMENT_TESTS = [
    CorefTestCase(
        id="agree_01_gender_mismatch",
        category="concordancia",
        text="María entró. Él estaba esperando.",
        expected_chains=[],  # "Él" no puede referir a María
        anti_chains=[("María", "Él")],
        difficulty="easy",
        linguistic_note="Discordancia de género bloquea correferencia",
    ),
    CorefTestCase(
        id="agree_02_number_mismatch",
        category="concordancia",
        text="Los niños jugaban. Ella miraba desde la ventana.",
        expected_chains=[],  # "Ella" no puede referir a "Los niños"
        anti_chains=[("Los niños", "Ella")],
        difficulty="easy",
        linguistic_note="Discordancia de número bloquea correferencia",
    ),
    CorefTestCase(
        id="agree_03_epicene_noun",
        category="concordancia",
        text="La víctima declaró. Él contó lo sucedido.",
        expected_chains=[("La víctima", ["Él"])],  # "víctima" es epiceno
        difficulty="hard",
        linguistic_note="Sustantivo epiceno: género gramatical ≠ sexo del referente",
    ),
    CorefTestCase(
        id="agree_04_collective_singular",
        category="concordancia",
        text="El grupo avanzaba. Ellos parecían cansados.",
        expected_chains=[("El grupo", ["Ellos"])],
        difficulty="hard",
        linguistic_note="Colectivo singular con pronombre plural (silepsis)",
    ),
    CorefTestCase(
        id="agree_05_hybrid_agreement",
        category="concordancia",
        text="Su Majestad el Rey entró. Él saludó a todos.",
        expected_chains=[("Su Majestad el Rey", ["Él"])],
        difficulty="medium",
        linguistic_note="Concordancia por el referente, no por 'Majestad'",
    ),
]

# =============================================================================
# CATEGORÍA 7: REFERENCIAS AMBIGUAS
# =============================================================================

AMBIGUOUS_TESTS = [
    CorefTestCase(
        id="ambig_01_two_males",
        category="ambiguedad",
        text="Pedro le dio el libro a Juan. Él lo leyó esa noche.",
        expected_chains=[("Juan", ["Él"])],  # Receptor es más prominente
        difficulty="hard",
        linguistic_note="Ambigüedad: receptor suele ser más prominente",
    ),
    CorefTestCase(
        id="ambig_02_parallelism",
        category="ambiguedad",
        text="Juan criticó a Pedro. María lo defendió.",
        expected_chains=[("Pedro", ["lo"])],  # Paralelismo: objeto→objeto
        difficulty="hard",
        linguistic_note="Paralelismo gramatical favorece objeto→objeto",
    ),
    CorefTestCase(
        id="ambig_03_topic_continuation",
        category="ambiguedad",
        text="Juan es profesor. Pedro es médico. Él trabaja en un hospital.",
        expected_chains=[("Pedro", ["Él"])],  # Tópico más reciente
        difficulty="hard",
        linguistic_note="Continuación de tópico: entidad más reciente",
    ),
    CorefTestCase(
        id="ambig_04_implicit_causality",
        category="ambiguedad",
        text="Juan asustó a Pedro. Él gritó de miedo.",
        expected_chains=[("Pedro", ["Él"])],  # Causalidad implícita del verbo
        difficulty="adversarial",
        linguistic_note="Verbo de transferencia de estado: paciente es causa del resultado",
    ),
    CorefTestCase(
        id="ambig_05_admired",
        category="ambiguedad",
        text="Juan admiraba a Pedro. Él era muy talentoso.",
        expected_chains=[("Pedro", ["Él"])],  # "admirar" implica que el objeto es notable
        difficulty="adversarial",
        linguistic_note="Causalidad implícita: objeto de 'admirar' es causa",
    ),
]

# =============================================================================
# CATEGORÍA 8: CORREFERENCIA A DISTANCIA
# =============================================================================

LONG_DISTANCE_TESTS = [
    CorefTestCase(
        id="dist_01_paragraph_gap",
        category="distancia",
        text="""María trabajaba en el hospital desde hacía diez años.

Era la mejor enfermera del departamento. Todos la respetaban.

Un día, ella decidió renunciar.""",
        expected_chains=[("María", ["ella", "la"])],
        difficulty="medium",
        linguistic_note="Correferencia a través de múltiples párrafos",
    ),
    CorefTestCase(
        id="dist_02_intervening_entity",
        category="distancia",
        text="María entró. Juan la saludó. Pedro también la vio.",
        expected_chains=[("María", ["la", "la"])],
        difficulty="medium",
        linguistic_note="Múltiples entidades intermedias, mismo referente",
    ),
    CorefTestCase(
        id="dist_03_chapter_boundary",
        category="distancia",
        text="""Capítulo 1
María se despidió de todos.

Capítulo 2
Ella nunca volvió.""",
        expected_chains=[("María", ["Ella"])],
        difficulty="hard",
        linguistic_note="Correferencia cruzando límites de capítulo",
    ),
]

# =============================================================================
# CATEGORÍA 9: CATÁFORA (referencia hacia adelante)
# =============================================================================

CATAPHORA_TESTS = [
    CorefTestCase(
        id="cata_01_simple",
        category="catafora",
        text="Cuando él llegó, Juan parecía cansado.",
        expected_chains=[("Juan", ["él"])],
        difficulty="hard",
        linguistic_note="Catáfora simple: pronombre antes del nombre",
    ),
    CorefTestCase(
        id="cata_02_possessive",
        category="catafora",
        text="Su madre lo esperaba. Juan la abrazó.",
        expected_chains=[("Juan", ["Su", "lo"])],
        difficulty="hard",
        linguistic_note="Posesivo catafórico",
    ),
    CorefTestCase(
        id="cata_03_conditional",
        category="catafora",
        text="Si ella quería, María podía quedarse.",
        expected_chains=[("María", ["ella"])],
        difficulty="hard",
        linguistic_note="Catáfora en condicional",
    ),
]

# =============================================================================
# CATEGORÍA 10: CLÁUSULAS EMBEBIDAS
# =============================================================================

EMBEDDED_TESTS = [
    CorefTestCase(
        id="embed_01_relative_clause",
        category="clausulas_embebidas",
        text="El hombre que María había visto tenía ojos azules.",
        expected_chains=[("El hombre", ["tenía"])],  # El sujeto de "tenía" es "El hombre"
        anti_chains=[("María", "tenía")],
        difficulty="hard",
        linguistic_note="Entidad en cláusula relativa NO es antecedente del verbo principal",
    ),
    CorefTestCase(
        id="embed_02_complement_clause",
        category="clausulas_embebidas",
        text="Juan pensaba que ella era inteligente. María se ruborizó.",
        expected_chains=[("María", ["ella"])],
        difficulty="hard",
        linguistic_note="Pronombre en cláusula complementante",
    ),
    CorefTestCase(
        id="embed_03_reported_speech",
        category="clausulas_embebidas",
        text="María dijo que él vendría. Juan llegó tarde.",
        expected_chains=[("Juan", ["él"])],
        difficulty="hard",
        linguistic_note="Pronombre en discurso indirecto",
    ),
]

# =============================================================================
# CATEGORÍA 11: SNs DEFINIDOS
# =============================================================================

DEFINITE_NP_TESTS = [
    CorefTestCase(
        id="defnp_01_role",
        category="sn_definidos",
        text="Juan García es cirujano. El doctor opera todos los días.",
        expected_chains=[("Juan García", ["El doctor"])],
        difficulty="medium",
        linguistic_note="SN definido con rol/profesión",
    ),
    CorefTestCase(
        id="defnp_02_relation",
        category="sn_definidos",
        text="María presentó a su madre. La mujer saludó a todos.",
        expected_chains=[("su madre", ["La mujer"])],
        difficulty="medium",
        linguistic_note="SN definido con relación",
    ),
    CorefTestCase(
        id="defnp_03_description",
        category="sn_definidos",
        text="Un hombre alto entró. El desconocido no dijo nada.",
        expected_chains=[("Un hombre alto", ["El desconocido"])],
        difficulty="medium",
        linguistic_note="SN definido descriptivo",
    ),
    CorefTestCase(
        id="defnp_04_bridging",
        category="sn_definidos",
        text="El coche se detuvo. El conductor bajó rápidamente.",
        expected_chains=[],  # Bridging, no correferencia directa
        difficulty="hard",
        linguistic_note="Bridging anaphora: inferencia, no correferencia",
    ),
]

# =============================================================================
# CATEGORÍA 12: ANTECEDENTES DIVIDIDOS
# =============================================================================

SPLIT_ANTECEDENT_TESTS = [
    CorefTestCase(
        id="split_01_conjunction",
        category="antecedentes_divididos",
        text="Juan habló con María. Ellos decidieron salir.",
        expected_chains=[("Juan", ["Ellos"]), ("María", ["Ellos"])],
        difficulty="hard",
        linguistic_note="Pronombre plural con antecedentes separados",
    ),
    CorefTestCase(
        id="split_02_discourse",
        category="antecedentes_divididos",
        text="Pedro trabaja aquí. Ana también. Ellos son compañeros.",
        expected_chains=[("Pedro", ["Ellos"]), ("Ana", ["Ellos"])],
        difficulty="hard",
        linguistic_note="Antecedentes en oraciones separadas",
    ),
]

# =============================================================================
# CATEGORÍA 13: ANÁFORA LIGADA
# =============================================================================

BOUND_ANAPHORA_TESTS = [
    CorefTestCase(
        id="bound_01_cada",
        category="anafora_ligada",
        text="Cada estudiante trajo su libro.",
        expected_chains=[],  # "su" está ligado a "cada estudiante", no es correferencia
        difficulty="adversarial",
        linguistic_note="Posesivo ligado cuantificacionalmente, no correferencial",
    ),
    CorefTestCase(
        id="bound_02_nadie",
        category="anafora_ligada",
        text="Nadie cree que él sea culpable.",
        expected_chains=[],  # "él" puede estar ligado o ser libre
        difficulty="adversarial",
        linguistic_note="Pronombre bajo cuantificador negativo",
    ),
]

# =============================================================================
# CATEGORÍA 14: INTERFERENCIA
# =============================================================================

INTERFERENCE_TESTS = [
    CorefTestCase(
        id="inter_01_similar_names",
        category="interferencia",
        text="María García y María López discutieron. Ella se fue enfadada.",
        expected_chains=[("María García", ["Ella"])],  # Primera mención = más prominente
        difficulty="adversarial",
        linguistic_note="Nombres similares: primera mención más prominente",
    ),
    CorefTestCase(
        id="inter_02_same_role",
        category="interferencia",
        text="El médico examinó al paciente. El doctor recetó medicinas.",
        expected_chains=[("El médico", ["El doctor"])],
        difficulty="hard",
        linguistic_note="Diferentes SNs, mismo referente",
    ),
    CorefTestCase(
        id="inter_03_title_name",
        category="interferencia",
        text="Don José llegó tarde. José se disculpó.",
        expected_chains=[("Don José", ["José"])],
        difficulty="medium",
        linguistic_note="Nombre con/sin título",
    ),
]

# =============================================================================
# CATEGORÍA 15: PATRONES DE NARRADOR
# =============================================================================

NARRATOR_TESTS = [
    CorefTestCase(
        id="narr_01_me_llamo",
        category="narrador",
        text="Me llamo María. Soy profesora en este instituto.",
        expected_chains=[("María", ["Me", "Soy"])],
        difficulty="medium",
        linguistic_note="Auto-identificación del narrador",
    ),
    CorefTestCase(
        id="narr_02_first_person",
        category="narrador",
        text="Yo entré en la habitación. Vi a Juan sentado.",
        expected_chains=[],  # "Yo" sin nombre explícito
        difficulty="medium",
        linguistic_note="Primera persona sin identificación",
    ),
    CorefTestCase(
        id="narr_03_switch_person",
        category="narrador",
        text="Me llamo Ana. María entró. Ella me miró.",
        expected_chains=[("María", ["Ella"]), ("Ana", ["Me", "me"])],
        difficulty="hard",
        linguistic_note="Cambio entre primera y tercera persona",
    ),
]

# =============================================================================
# CATEGORÍA 16: CAMBIO DE TÓPICO
# =============================================================================

TOPIC_SHIFT_TESTS = [
    CorefTestCase(
        id="topic_01_abrupt",
        category="cambio_topico",
        text="Juan trabaja en el banco. En otra parte de la ciudad, María preparaba la cena. Ella estaba cansada.",
        expected_chains=[("María", ["Ella"])],
        anti_chains=[("Juan", "Ella")],
        difficulty="medium",
        linguistic_note="Cambio de tópico explícito",
    ),
    CorefTestCase(
        id="topic_02_paragraph",
        category="cambio_topico",
        text="""Juan era feliz.

María, por su parte, sufría en silencio. Ella no lo demostraba.""",
        expected_chains=[("María", ["Ella"])],
        difficulty="medium",
        linguistic_note="Cambio de tópico por párrafo",
    ),
]

# =============================================================================
# CATEGORÍA 17: ELIPSIS VERBAL
# =============================================================================

ELLIPSIS_TESTS = [
    CorefTestCase(
        id="ellip_01_gapping",
        category="elipsis",
        text="Juan comió pasta y María, arroz.",
        expected_chains=[],  # No hay pronombres
        difficulty="medium",
        linguistic_note="Gapping: elipsis verbal, no correferencia",
    ),
    CorefTestCase(
        id="ellip_02_vp_ellipsis",
        category="elipsis",
        text="Juan quiere ir al cine y María también.",
        expected_chains=[],  # Elipsis de SV
        difficulty="medium",
        linguistic_note="Elipsis de SV",
    ),
]

# =============================================================================
# CATEGORÍA 18: PRONOMBRES OBJETO
# =============================================================================

OBJECT_PRONOUN_TESTS = [
    CorefTestCase(
        id="obj_01_double_object",
        category="pronombres_objeto",
        text="Juan le dio el libro a María. Ella lo leyó.",
        expected_chains=[("el libro", ["lo"]), ("María", ["Ella"])],
        difficulty="medium",
        linguistic_note="Doble objeto con pronombre posterior",
    ),
    CorefTestCase(
        id="obj_02_clitic_doubling",
        category="pronombres_objeto",
        text="A María la vi ayer. Ella estaba bien.",
        expected_chains=[("María", ["la", "Ella"])],
        difficulty="medium",
        linguistic_note="Duplicación de clítico",
    ),
    CorefTestCase(
        id="obj_03_se_le_lo",
        category="pronombres_objeto",
        text="Juan se lo dio a María.",
        expected_chains=[("María", ["se"])],  # "se" = le → a María
        difficulty="hard",
        linguistic_note="Cambio le→se ante lo/la",
    ),
]

# =============================================================================
# CATEGORÍA 19: COORDINACIÓN
# =============================================================================

COORDINATION_TESTS = [
    CorefTestCase(
        id="coord_01_np",
        category="coordinacion",
        text="Juan y María llegaron. Ellos traían regalos.",
        expected_chains=[("Juan y María", ["Ellos"])],
        difficulty="easy",
        linguistic_note="SN coordinado como antecedente",
    ),
    CorefTestCase(
        id="coord_02_mixed_gender",
        category="coordinacion",
        text="Ana y Pedro vinieron. Ellos parecían contentos.",
        expected_chains=[("Ana y Pedro", ["Ellos"])],
        difficulty="medium",
        linguistic_note="Coordinación mixta: masculino plural",
    ),
    CorefTestCase(
        id="coord_03_each",
        category="coordinacion",
        text="Juan y Pedro llevaban cada uno su maleta.",
        expected_chains=[("Juan", ["su"]), ("Pedro", ["su"])],  # Distributivo
        difficulty="adversarial",
        linguistic_note="'cada uno' distribuye el posesivo",
    ),
]

# =============================================================================
# CATEGORÍA 20: COMPARATIVAS
# =============================================================================

COMPARATIVE_TESTS = [
    CorefTestCase(
        id="comp_01_como",
        category="comparativas",
        text="María es tan alta como él. Juan mide dos metros.",
        expected_chains=[("Juan", ["él"])],
        difficulty="hard",
        linguistic_note="Pronombre en comparativa",
    ),
    CorefTestCase(
        id="comp_02_mejor_que",
        category="comparativas",
        text="Pedro trabaja mejor que ella. Ana se esfuerza mucho.",
        expected_chains=[("Ana", ["ella"])],
        difficulty="hard",
        linguistic_note="Pronombre en comparativa, catáfora",
    ),
]


# =============================================================================
# FIXTURE Y TEST RUNNER
# =============================================================================

ALL_COREF_TESTS = (
    PRONOUN_TESTS
    + POSSESSIVE_TESTS
    + DEMONSTRATIVE_TESTS
    + ZERO_ANAPHORA_TESTS
    + REFLEXIVE_TESTS
    + AGREEMENT_TESTS
    + AMBIGUOUS_TESTS
    + LONG_DISTANCE_TESTS
    + CATAPHORA_TESTS
    + EMBEDDED_TESTS
    + DEFINITE_NP_TESTS
    + SPLIT_ANTECEDENT_TESTS
    + BOUND_ANAPHORA_TESTS
    + INTERFERENCE_TESTS
    + NARRATOR_TESTS
    + TOPIC_SHIFT_TESTS
    + ELLIPSIS_TESTS
    + OBJECT_PRONOUN_TESTS
    + COORDINATION_TESTS
    + COMPARATIVE_TESTS
)


class TestCoreferenceAdversarial:
    """Tests adversariales para el sistema de correferencias."""

    @pytest.fixture
    def resolver(self):
        """Crea resolver con métodos rápidos para tests."""
        from narrative_assistant.nlp.coreference_resolver import (
            CorefConfig,
            CoreferenceVotingResolver,
            CorefMethod,
        )

        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS, CorefMethod.MORPHO],
            min_confidence=0.3,
        )
        return CoreferenceVotingResolver(config)

    def _find_chain_for_entity(self, chains, entity_name: str):
        """Encuentra la cadena que contiene una entidad."""
        entity_lower = entity_name.lower()
        for chain in chains:
            if chain.main_mention and entity_lower in chain.main_mention.lower():
                return chain
            for mention in chain.mentions:
                if entity_lower in mention.text.lower():
                    return chain
        return None

    def _check_mention_in_chain(self, chain, mention_text: str) -> bool:
        """Verifica si una mención está en una cadena."""
        if not chain:
            return False
        mention_lower = mention_text.lower()
        return any(mention_lower == m.text.lower() for m in chain.mentions)

    @pytest.mark.parametrize("test_case", ALL_COREF_TESTS, ids=lambda tc: tc.id)
    def test_coreference_case(self, resolver, test_case: CorefTestCase):
        """Ejecuta un caso de test de correferencia."""
        result = resolver.resolve_document(test_case.text)

        # Verificar cadenas esperadas
        for main_entity, expected_mentions in test_case.expected_chains:
            chain = self._find_chain_for_entity(result.chains, main_entity)

            # Verificar que cada mención esperada está en la cadena
            for mention in expected_mentions:
                if mention == "Ø":  # Sujeto implícito - skip por ahora
                    continue

                is_in_chain = self._check_mention_in_chain(chain, mention)
                assert is_in_chain, (
                    f"[{test_case.id}] '{mention}' debería estar en cadena de '{main_entity}'\n"
                    f"Cadenas encontradas: {[(c.main_mention, [m.text for m in c.mentions]) for c in result.chains]}\n"
                    f"Nota: {test_case.linguistic_note}"
                )

        # Verificar anti-cadenas (lo que NO debería ocurrir)
        if test_case.anti_chains:
            for entity, should_not_include in test_case.anti_chains:
                chain = self._find_chain_for_entity(result.chains, entity)
                is_wrongly_included = self._check_mention_in_chain(chain, should_not_include)
                assert not is_wrongly_included, (
                    f"[{test_case.id}] '{should_not_include}' NO debería estar en cadena de '{entity}'\n"
                    f"Nota: {test_case.linguistic_note}"
                )


class TestCoreferenceByCategory:
    """Tests organizados por categoría para análisis granular."""

    @pytest.fixture
    def resolver(self):
        from narrative_assistant.nlp.coreference_resolver import (
            CorefConfig,
            CoreferenceVotingResolver,
            CorefMethod,
        )

        config = CorefConfig(
            enabled_methods=[CorefMethod.HEURISTICS, CorefMethod.MORPHO],
            min_confidence=0.3,
        )
        return CoreferenceVotingResolver(config)

    @pytest.mark.parametrize("test_case", PRONOUN_TESTS, ids=lambda tc: tc.id)
    def test_pronouns(self, resolver, test_case):
        """Tests de pronombres personales."""
        self._run_test(resolver, test_case)

    @pytest.mark.parametrize("test_case", POSSESSIVE_TESTS, ids=lambda tc: tc.id)
    def test_possessives(self, resolver, test_case):
        """Tests de posesivos."""
        self._run_test(resolver, test_case)

    @pytest.mark.parametrize("test_case", DEMONSTRATIVE_TESTS, ids=lambda tc: tc.id)
    def test_demonstratives(self, resolver, test_case):
        """Tests de demostrativos."""
        self._run_test(resolver, test_case)

    @pytest.mark.parametrize("test_case", AMBIGUOUS_TESTS, ids=lambda tc: tc.id)
    def test_ambiguous(self, resolver, test_case):
        """Tests de referencias ambiguas."""
        self._run_test(resolver, test_case)

    def _run_test(self, resolver, test_case: CorefTestCase):
        """Ejecuta un caso de test."""
        result = resolver.resolve_document(test_case.text)

        for main_entity, expected_mentions in test_case.expected_chains:
            chain = None
            for c in result.chains:
                if c.main_mention and main_entity.lower() in c.main_mention.lower():
                    chain = c
                    break

            for mention in expected_mentions:
                if mention == "Ø":
                    continue
                is_in_chain = chain and any(
                    mention.lower() == m.text.lower() for m in chain.mentions
                )
                assert is_in_chain, (
                    f"[{test_case.id}] '{mention}' debería estar en cadena de '{main_entity}'"
                )


def get_test_summary():
    """Genera resumen de los tests por categoría."""
    from collections import Counter

    categories = Counter(tc.category for tc in ALL_COREF_TESTS)
    difficulties = Counter(tc.difficulty for tc in ALL_COREF_TESTS)

    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS ADVERSARIALES DE CORREFERENCIA")
    print("=" * 60)
    print(f"\nTotal de casos: {len(ALL_COREF_TESTS)}")
    print("\nPor categoría:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print("\nPor dificultad:")
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    get_test_summary()
    pytest.main([__file__, "-v", "--tb=short"])
