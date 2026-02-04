"""
Tests adversariales GAN-style para el sistema de detección de estado vital.

Objetivo: Identificar casos límite donde el sistema falla en detectar
muertes o genera falsos positivos/negativos.

Categorías de tests:
1. Muertes directas (verbos explícitos)
2. Muertes causadas (alguien mata)
3. Muertes reportadas (se informa)
4. Muertes implícitas (indicios)
5. Falsos positivos (metáforas, expresiones)
6. Referencias válidas post-mortem (flashbacks, memorias)
7. Resurrección/casi-muerte
8. Género específico (fantasía, terror)
9. Referencias ambiguas
10. Marcadores temporales
11. Eufemismos de muerte
12. Muerte colectiva
13. Muerte animal vs humano
14. Personificación
15. Muerte simbólica
16. Nivel narrativo (historia dentro de historia)
17. Sueños y alucinaciones
18. Narrador no confiable
19. Múltiples muertes mismo capítulo
20. Secuencia temporal inversa

Basado en patrones narrativos comunes en literatura española.
"""

from dataclasses import dataclass, field
from typing import Optional

import pytest


@dataclass
class VitalStatusTestCase:
    """Caso de test para vital status."""

    id: str
    category: str
    text: str
    entities: list[str]  # Nombres de entidades a registrar
    expected_deaths: list[str] = field(
        default_factory=list
    )  # Nombres que deben detectarse como muertos
    not_deaths: list[str] = field(default_factory=list)  # NO deben detectarse como muertos
    expected_valid_references: list[str] = field(
        default_factory=list
    )  # Referencias post-mortem válidas
    chapter: int = 1
    difficulty: str = "medium"
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: MUERTES DIRECTAS
# =============================================================================

DIRECT_DEATH_TESTS = [
    VitalStatusTestCase(
        id="direct_01_murio",
        category="muertes_directas",
        text="Juan murió aquella noche de invierno.",
        entities=["Juan"],
        expected_deaths=["Juan"],
        difficulty="easy",
        linguistic_note="Verbo 'morir' en pasado simple",
    ),
    VitalStatusTestCase(
        id="direct_02_fallecio",
        category="muertes_directas",
        text="María falleció en el hospital tras una larga enfermedad.",
        entities=["María"],
        expected_deaths=["María"],
        difficulty="easy",
        linguistic_note="'Fallecer' - sinónimo formal",
    ),
    VitalStatusTestCase(
        id="direct_03_perecio",
        category="muertes_directas",
        text="El capitán pereció en el naufragio.",
        entities=["El capitán"],
        expected_deaths=["El capitán"],
        difficulty="medium",
        linguistic_note="'Perecer' - estilo literario",
    ),
    VitalStatusTestCase(
        id="direct_04_cayo_muerto",
        category="muertes_directas",
        text="Pedro cayó muerto al suelo tras el disparo.",
        entities=["Pedro"],
        expected_deaths=["Pedro"],
        difficulty="easy",
        linguistic_note="Expresión 'caer muerto'",
    ),
    VitalStatusTestCase(
        id="direct_05_dejo_respirar",
        category="muertes_directas",
        text="Ana dejó de respirar a las tres de la madrugada.",
        entities=["Ana"],
        expected_deaths=["Ana"],
        difficulty="medium",
        linguistic_note="Perífrasis 'dejar de respirar'",
    ),
    VitalStatusTestCase(
        id="direct_06_exhalo_aliento",
        category="muertes_directas",
        text="El anciano exhaló su último aliento rodeado de su familia.",
        entities=["El anciano"],
        expected_deaths=["El anciano"],
        difficulty="medium",
        linguistic_note="Expresión literaria 'exhalar último aliento'",
    ),
    VitalStatusTestCase(
        id="direct_07_multiple_verbs",
        category="muertes_directas",
        text="Carlos murió, falleció, dejó este mundo.",
        entities=["Carlos"],
        expected_deaths=["Carlos"],
        difficulty="easy",
        linguistic_note="Múltiples verbos, una sola muerte",
    ),
]

# =============================================================================
# CATEGORÍA 2: MUERTES CAUSADAS
# =============================================================================

CAUSED_DEATH_TESTS = [
    VitalStatusTestCase(
        id="caused_01_mato",
        category="muertes_causadas",
        text="El asesino mató a Roberto en el callejón.",
        entities=["Roberto", "El asesino"],
        expected_deaths=["Roberto"],
        not_deaths=["El asesino"],
        difficulty="easy",
        linguistic_note="Verbo 'matar' con OD",
    ),
    VitalStatusTestCase(
        id="caused_02_asesino",
        category="muertes_causadas",
        text="Alguien asesinó a la condesa durante la fiesta.",
        entities=["la condesa"],
        expected_deaths=["la condesa"],
        difficulty="easy",
        linguistic_note="Verbo 'asesinar'",
    ),
    VitalStatusTestCase(
        id="caused_03_ejecutaron",
        category="muertes_causadas",
        text="Los soldados ejecutaron al prisionero al amanecer.",
        entities=["al prisionero"],
        expected_deaths=["al prisionero"],
        difficulty="medium",
        linguistic_note="'Ejecutar' - muerte formal",
    ),
    VitalStatusTestCase(
        id="caused_04_disparo",
        category="muertes_causadas",
        text="Le dispararon a Miguel y cayó al instante.",
        entities=["Miguel"],
        expected_deaths=["Miguel"],
        difficulty="medium",
        linguistic_note="Disparo con resultado implícito",
    ),
    VitalStatusTestCase(
        id="caused_05_envenenaron",
        category="muertes_causadas",
        text="Envenenaron a la reina con arsénico en el vino.",
        entities=["la reina"],
        expected_deaths=["la reina"],
        difficulty="medium",
        linguistic_note="Envenenamiento",
    ),
    VitalStatusTestCase(
        id="caused_06_pasiva",
        category="muertes_causadas",
        text="Teresa fue asesinada por su propio hermano.",
        entities=["Teresa"],
        expected_deaths=["Teresa"],
        difficulty="easy",
        linguistic_note="Voz pasiva",
    ),
]

# =============================================================================
# CATEGORÍA 3: MUERTES REPORTADAS
# =============================================================================

REPORTED_DEATH_TESTS = [
    VitalStatusTestCase(
        id="reported_01_ha_muerto",
        category="muertes_reportadas",
        text="—Luis ha muerto —anunció el médico.",
        entities=["Luis"],
        expected_deaths=["Luis"],
        difficulty="easy",
        linguistic_note="Pretérito perfecto en diálogo",
    ),
    VitalStatusTestCase(
        id="reported_02_esta_muerto",
        category="muertes_reportadas",
        text="El detective confirmó: Pablo está muerto.",
        entities=["Pablo"],
        expected_deaths=["Pablo"],
        difficulty="easy",
        linguistic_note="Estado resultante",
    ),
    VitalStatusTestCase(
        id="reported_03_se_enteraron",
        category="muertes_reportadas",
        text="Se enteraron de que Marta había muerto en el accidente.",
        entities=["Marta"],
        expected_deaths=["Marta"],
        difficulty="medium",
        linguistic_note="Noticia de muerte",
    ),
    VitalStatusTestCase(
        id="reported_04_anunciaron",
        category="muertes_reportadas",
        text="Anunciaron el fallecimiento de don Álvaro en el periódico.",
        entities=["don Álvaro"],
        expected_deaths=["don Álvaro"],
        difficulty="medium",
        linguistic_note="Anuncio formal",
    ),
    VitalStatusTestCase(
        id="reported_05_no_sobrevivio",
        category="muertes_reportadas",
        text="El paciente no sobrevivió a la operación.",
        entities=["El paciente"],
        expected_deaths=["El paciente"],
        difficulty="medium",
        linguistic_note="'No sobrevivir'",
    ),
]

# =============================================================================
# CATEGORÍA 4: MUERTES IMPLÍCITAS
# =============================================================================

IMPLIED_DEATH_TESTS = [
    VitalStatusTestCase(
        id="implied_01_cadaver",
        category="muertes_implicitas",
        text="Encontraron el cadáver de Fernando en el río.",
        entities=["Fernando"],
        expected_deaths=["Fernando"],
        difficulty="easy",
        linguistic_note="'Cadáver' implica muerte",
    ),
    VitalStatusTestCase(
        id="implied_02_cuerpo_sin_vida",
        category="muertes_implicitas",
        text="El cuerpo sin vida de Elena yacía en el suelo.",
        entities=["Elena"],
        expected_deaths=["Elena"],
        difficulty="easy",
        linguistic_note="'Cuerpo sin vida'",
    ),
    VitalStatusTestCase(
        id="implied_03_tumba",
        category="muertes_implicitas",
        text="Visitó la tumba de su padre cada domingo.",
        entities=["su padre"],
        expected_deaths=["su padre"],
        difficulty="medium",
        linguistic_note="'Tumba' implica fallecimiento",
    ),
    VitalStatusTestCase(
        id="implied_04_nunca_regreso",
        category="muertes_implicitas",
        text="Jorge nunca regresó de la guerra.",
        entities=["Jorge"],
        expected_deaths=["Jorge"],
        difficulty="hard",
        linguistic_note="Desaparición permanente (implica muerte)",
    ),
    VitalStatusTestCase(
        id="implied_05_en_memoria",
        category="muertes_implicitas",
        text="Construyeron un monumento en memoria de los caídos.",
        entities=["los caídos"],
        expected_deaths=["los caídos"],
        difficulty="medium",
        linguistic_note="'En memoria de' sugiere fallecimiento",
    ),
]

# =============================================================================
# CATEGORÍA 5: FALSOS POSITIVOS (NO deben detectarse como muerte)
# =============================================================================

FALSE_POSITIVE_TESTS = [
    VitalStatusTestCase(
        id="fp_01_murio_verguenza",
        category="falsos_positivos",
        text="María se murió de vergüenza cuando la descubrieron.",
        entities=["María"],
        expected_deaths=[],
        not_deaths=["María"],
        difficulty="hard",
        linguistic_note="Expresión idiomática - no muerte real",
    ),
    VitalStatusTestCase(
        id="fp_02_muero_hambre",
        category="falsos_positivos",
        text="¡Me muero de hambre! —exclamó Pedro.",
        entities=["Pedro"],
        expected_deaths=[],
        not_deaths=["Pedro"],
        difficulty="hard",
        linguistic_note="Hipérbole coloquial",
    ),
    VitalStatusTestCase(
        id="fp_03_muerto_risa",
        category="falsos_positivos",
        text="Juan estaba muerto de risa con el chiste.",
        entities=["Juan"],
        expected_deaths=[],
        not_deaths=["Juan"],
        difficulty="hard",
        linguistic_note="'Muerto de risa' - expresión",
    ),
    VitalStatusTestCase(
        id="fp_04_muerto_cansancio",
        category="falsos_positivos",
        text="Llegó a casa muerto de cansancio.",
        entities=["Llegó"],  # Sin nombre explícito
        expected_deaths=[],
        difficulty="medium",
        linguistic_note="'Muerto de cansancio'",
    ),
    VitalStatusTestCase(
        id="fp_05_matar_tiempo",
        category="falsos_positivos",
        text="Para matar el tiempo, Ana leía revistas.",
        entities=["Ana"],
        expected_deaths=[],
        not_deaths=["Ana"],
        difficulty="medium",
        linguistic_note="'Matar el tiempo' - expresión",
    ),
    VitalStatusTestCase(
        id="fp_06_punto_muerto",
        category="falsos_positivos",
        text="Las negociaciones llegaron a un punto muerto.",
        entities=[],
        expected_deaths=[],
        difficulty="easy",
        linguistic_note="'Punto muerto' - metáfora",
    ),
    VitalStatusTestCase(
        id="fp_07_naturaleza_muerta",
        category="falsos_positivos",
        text="El pintor Carlos especializado en naturaleza muerta.",
        entities=["Carlos"],
        expected_deaths=[],
        not_deaths=["Carlos"],
        difficulty="medium",
        linguistic_note="'Naturaleza muerta' - género artístico",
    ),
    VitalStatusTestCase(
        id="fp_08_lengua_muerta",
        category="falsos_positivos",
        text="El latín es una lengua muerta.",
        entities=[],
        expected_deaths=[],
        difficulty="easy",
        linguistic_note="'Lengua muerta'",
    ),
    VitalStatusTestCase(
        id="fp_09_ciudad_muerta",
        category="falsos_positivos",
        text="A esa hora, Madrid era una ciudad muerta.",
        entities=["Madrid"],
        expected_deaths=[],
        not_deaths=["Madrid"],
        difficulty="medium",
        linguistic_note="'Ciudad muerta' - metáfora",
    ),
    VitalStatusTestCase(
        id="fp_10_mata_pasiones",
        category="falsos_positivos",
        text="La rutina mata las pasiones, decía siempre Rosa.",
        entities=["Rosa"],
        expected_deaths=[],
        not_deaths=["Rosa"],
        difficulty="hard",
        linguistic_note="'Matar' metafórico",
    ),
]

# =============================================================================
# CATEGORÍA 6: REFERENCIAS VÁLIDAS POST-MORTEM
# =============================================================================

VALID_REFERENCE_TESTS = [
    VitalStatusTestCase(
        id="valid_01_recordo",
        category="referencias_validas",
        text="María murió en el capítulo anterior. Ahora Pedro recordó a María con cariño.",
        entities=["María", "Pedro"],
        expected_deaths=["María"],
        expected_valid_references=["María"],
        difficulty="medium",
        linguistic_note="Recuerdo de persona fallecida",
    ),
    VitalStatusTestCase(
        id="valid_02_fantasma",
        category="referencias_validas",
        text="El fantasma de don Luis apareció en el pasillo.",
        entities=["don Luis"],
        expected_deaths=["don Luis"],  # Ya debe estar muerto para ser fantasma
        expected_valid_references=["don Luis"],
        difficulty="medium",
        linguistic_note="Aparición como fantasma",
    ),
    VitalStatusTestCase(
        id="valid_03_sono",
        category="referencias_validas",
        text="Elena soñó con su abuela fallecida.",
        entities=["Elena", "su abuela"],
        expected_deaths=["su abuela"],
        expected_valid_references=["su abuela"],
        difficulty="medium",
        linguistic_note="Aparición en sueño",
    ),
    VitalStatusTestCase(
        id="valid_04_flashback",
        category="referencias_validas",
        text="Años antes, cuando Alberto aún vivía, solían pasear juntos.",
        entities=["Alberto"],
        expected_deaths=[],  # No detectar muerte en flashback
        expected_valid_references=["Alberto"],
        difficulty="hard",
        linguistic_note="Marcador temporal de flashback",
    ),
    VitalStatusTestCase(
        id="valid_05_pensaba",
        category="referencias_validas",
        text="Carmen pensaba mucho en su difunto esposo.",
        entities=["Carmen", "su difunto esposo"],
        expected_deaths=["su difunto esposo"],
        expected_valid_references=["su difunto esposo"],
        difficulty="medium",
        linguistic_note="Pensamiento sobre fallecido",
    ),
]

# =============================================================================
# CATEGORÍA 7: RESURRECCIÓN / CASI-MUERTE
# =============================================================================

RESURRECTION_TESTS = [
    VitalStatusTestCase(
        id="resur_01_casi_muere",
        category="resurreccion",
        text="Juan casi muere en el accidente, pero sobrevivió.",
        entities=["Juan"],
        expected_deaths=[],
        not_deaths=["Juan"],
        difficulty="hard",
        linguistic_note="'Casi morir' - no muerte real",
    ),
    VitalStatusTestCase(
        id="resur_02_por_poco",
        category="resurreccion",
        text="Por poco muere María, pero los médicos la salvaron.",
        entities=["María"],
        expected_deaths=[],
        not_deaths=["María"],
        difficulty="hard",
        linguistic_note="'Por poco' - negación implícita",
    ),
    VitalStatusTestCase(
        id="resur_03_creyeron_muerto",
        category="resurreccion",
        text="Lo creyeron muerto, pero Pedro abrió los ojos.",
        entities=["Pedro"],
        expected_deaths=[],
        not_deaths=["Pedro"],
        difficulty="adversarial",
        linguistic_note="Muerte aparente desmentida",
    ),
    VitalStatusTestCase(
        id="resur_04_volvio_vida",
        category="resurreccion",
        text="El mago volvió a la vida después de tres días.",
        entities=["El mago"],
        expected_deaths=[],  # Resurrección anula la muerte
        difficulty="adversarial",
        linguistic_note="Resurrección (fantasía)",
    ),
    VitalStatusTestCase(
        id="resur_05_dado_por_muerto",
        category="resurreccion",
        text="Elena fue dada por muerta, pero apareció viva años después.",
        entities=["Elena"],
        expected_deaths=[],
        not_deaths=["Elena"],
        difficulty="adversarial",
        linguistic_note="Presunción de muerte desmentida",
    ),
]

# =============================================================================
# CATEGORÍA 8: GÉNERO ESPECÍFICO (fantasía, terror)
# =============================================================================

GENRE_SPECIFIC_TESTS = [
    VitalStatusTestCase(
        id="genre_01_vampiro",
        category="genero_especifico",
        text="El conde murió y renació como vampiro.",
        entities=["El conde"],
        expected_deaths=[],  # En fantasía, no-muerto ≠ muerto
        difficulty="adversarial",
        linguistic_note="Transformación en no-muerto",
    ),
    VitalStatusTestCase(
        id="genre_02_zombie",
        category="genero_especifico",
        text="Los zombies de los aldeanos muertos atacaron el pueblo.",
        entities=["los aldeanos"],
        expected_deaths=["los aldeanos"],  # Sí murieron, aunque sean zombies
        difficulty="hard",
        linguistic_note="Zombies = muertos reanimados",
    ),
    VitalStatusTestCase(
        id="genre_03_inmortal",
        category="genero_especifico",
        text="El elfo era inmortal y no podía morir.",
        entities=["El elfo"],
        expected_deaths=[],
        difficulty="medium",
        linguistic_note="Ser inmortal",
    ),
    VitalStatusTestCase(
        id="genre_04_reencarnacion",
        category="genero_especifico",
        text="Al morir, el monje reencarnó en un niño.",
        entities=["el monje"],
        expected_deaths=["el monje"],  # Sí murió, aunque reencarnó
        difficulty="hard",
        linguistic_note="Muerte con reencarnación",
    ),
]

# =============================================================================
# CATEGORÍA 9: REFERENCIAS AMBIGUAS
# =============================================================================

AMBIGUOUS_TESTS = [
    VitalStatusTestCase(
        id="ambig_01_desaparecio",
        category="ambiguedad",
        text="Carlos desapareció sin dejar rastro.",
        entities=["Carlos"],
        expected_deaths=[],  # Ambiguo - no confirma muerte
        difficulty="hard",
        linguistic_note="Desaparición ≠ muerte confirmada",
    ),
    VitalStatusTestCase(
        id="ambig_02_no_volvio",
        category="ambiguedad",
        text="Rosa no volvió a ser vista.",
        entities=["Rosa"],
        expected_deaths=[],  # Ambiguo
        difficulty="hard",
        linguistic_note="Desaparición no confirma muerte",
    ),
    VitalStatusTestCase(
        id="ambig_03_perdio_vida",
        category="ambiguedad",
        text="Muchos perdieron la vida en la batalla.",
        entities=["Muchos"],
        expected_deaths=["Muchos"],
        difficulty="medium",
        linguistic_note="'Perder la vida' = morir",
    ),
    VitalStatusTestCase(
        id="ambig_04_ultimo_adios",
        category="ambiguedad",
        text="Le dijeron el último adiós a Miguel.",
        entities=["Miguel"],
        expected_deaths=["Miguel"],  # Funeral implícito
        difficulty="hard",
        linguistic_note="'Último adiós' sugiere funeral",
    ),
]

# =============================================================================
# CATEGORÍA 10: MARCADORES TEMPORALES
# =============================================================================

TEMPORAL_TESTS = [
    VitalStatusTestCase(
        id="temp_01_cuando_vivia",
        category="marcadores_temporales",
        text="Cuando Juan vivía, la casa estaba llena de alegría.",
        entities=["Juan"],
        expected_deaths=["Juan"],  # Implica que ya no vive
        difficulty="hard",
        linguistic_note="'Cuando X vivía' implica que murió",
    ),
    VitalStatusTestCase(
        id="temp_02_antes_de_morir",
        category="marcadores_temporales",
        text="Antes de morir, María dejó instrucciones.",
        entities=["María"],
        expected_deaths=["María"],
        difficulty="medium",
        linguistic_note="'Antes de morir' confirma muerte",
    ),
    VitalStatusTestCase(
        id="temp_03_tras_muerte",
        category="marcadores_temporales",
        text="Tras la muerte de Pedro, vendieron la casa.",
        entities=["Pedro"],
        expected_deaths=["Pedro"],
        difficulty="easy",
        linguistic_note="'Tras la muerte de'",
    ),
    VitalStatusTestCase(
        id="temp_04_desde_fallecio",
        category="marcadores_temporales",
        text="Desde que falleció Ana, nadie tocó el piano.",
        entities=["Ana"],
        expected_deaths=["Ana"],
        difficulty="easy",
        linguistic_note="'Desde que falleció'",
    ),
]

# =============================================================================
# CATEGORÍA 11: EUFEMISMOS
# =============================================================================

EUPHEMISM_TESTS = [
    VitalStatusTestCase(
        id="euph_01_descanso_paz",
        category="eufemismos",
        text="Luis descansó en paz a los noventa años.",
        entities=["Luis"],
        expected_deaths=["Luis"],
        difficulty="medium",
        linguistic_note="'Descansar en paz'",
    ),
    VitalStatusTestCase(
        id="euph_02_mejor_vida",
        category="eufemismos",
        text="Doña Carmen pasó a mejor vida el martes.",
        entities=["Doña Carmen"],
        expected_deaths=["Doña Carmen"],
        difficulty="medium",
        linguistic_note="'Pasar a mejor vida'",
    ),
    VitalStatusTestCase(
        id="euph_03_nos_dejo",
        category="eufemismos",
        text="El abuelo nos dejó el año pasado.",
        entities=["El abuelo"],
        expected_deaths=["El abuelo"],
        difficulty="hard",
        linguistic_note="'Nos dejó' - eufemismo de muerte",
    ),
    VitalStatusTestCase(
        id="euph_04_se_fue",
        category="eufemismos",
        text="Don José se fue para siempre aquella noche.",
        entities=["Don José"],
        expected_deaths=["Don José"],
        difficulty="hard",
        linguistic_note="'Se fue para siempre'",
    ),
    VitalStatusTestCase(
        id="euph_05_entrego_alma",
        category="eufemismos",
        text="El moribundo entregó el alma al amanecer.",
        entities=["El moribundo"],
        expected_deaths=["El moribundo"],
        difficulty="medium",
        linguistic_note="'Entregar el alma'",
    ),
]

# =============================================================================
# CATEGORÍA 12: MUERTE COLECTIVA
# =============================================================================

COLLECTIVE_TESTS = [
    VitalStatusTestCase(
        id="coll_01_masacre",
        category="muerte_colectiva",
        text="En la masacre murieron todos los habitantes del pueblo.",
        entities=["los habitantes"],
        expected_deaths=["los habitantes"],
        difficulty="medium",
        linguistic_note="Muerte masiva",
    ),
    VitalStatusTestCase(
        id="coll_02_familia",
        category="muerte_colectiva",
        text="La familia García pereció en el incendio.",
        entities=["La familia García"],
        expected_deaths=["La familia García"],
        difficulty="medium",
        linguistic_note="Muerte de grupo familiar",
    ),
    VitalStatusTestCase(
        id="coll_03_soldados",
        category="muerte_colectiva",
        text="Cien soldados cayeron en la batalla.",
        entities=["soldados"],
        expected_deaths=["soldados"],
        difficulty="medium",
        linguistic_note="'Caer' en contexto militar = morir",
    ),
]

# =============================================================================
# CATEGORÍA 13: MUERTE ANIMAL VS HUMANO
# =============================================================================

ANIMAL_TESTS = [
    VitalStatusTestCase(
        id="animal_01_perro",
        category="animales",
        text="El perro de Juan murió de viejo.",
        entities=["Juan", "El perro"],
        expected_deaths=["El perro"],  # Si se trackean animales
        not_deaths=["Juan"],
        difficulty="medium",
        linguistic_note="Muerte de animal, no de humano",
    ),
    VitalStatusTestCase(
        id="animal_02_mataron_caballo",
        category="animales",
        text="Los soldados mataron al caballo del general.",
        entities=["el general", "al caballo"],
        expected_deaths=["al caballo"],
        not_deaths=["el general"],
        difficulty="medium",
        linguistic_note="Posesivo no implica muerte del poseedor",
    ),
]

# =============================================================================
# CATEGORÍA 14: PERSONIFICACIÓN
# =============================================================================

PERSONIFICATION_TESTS = [
    VitalStatusTestCase(
        id="pers_01_esperanza",
        category="personificacion",
        text="La esperanza murió en su corazón.",
        entities=[],
        expected_deaths=[],
        difficulty="hard",
        linguistic_note="Personificación de concepto abstracto",
    ),
    VitalStatusTestCase(
        id="pers_02_amor",
        category="personificacion",
        text="El amor murió entre ellos.",
        entities=[],
        expected_deaths=[],
        difficulty="hard",
        linguistic_note="Muerte de sentimiento",
    ),
]

# =============================================================================
# CATEGORÍA 15: MUERTE SIMBÓLICA
# =============================================================================

SYMBOLIC_TESTS = [
    VitalStatusTestCase(
        id="symb_01_civil",
        category="muerte_simbolica",
        text="Para su familia, Juan estaba muerto civilmente.",
        entities=["Juan"],
        expected_deaths=[],
        not_deaths=["Juan"],
        difficulty="hard",
        linguistic_note="Muerte civil/social, no física",
    ),
    VitalStatusTestCase(
        id="symb_02_profesional",
        category="muerte_simbolica",
        text="Su carrera murió con aquel escándalo.",
        entities=[],
        expected_deaths=[],
        difficulty="medium",
        linguistic_note="Muerte de carrera",
    ),
]

# =============================================================================
# CATEGORÍA 16: NIVEL NARRATIVO
# =============================================================================

NARRATIVE_LEVEL_TESTS = [
    VitalStatusTestCase(
        id="narr_01_libro",
        category="nivel_narrativo",
        text="En el libro que leía, el protagonista moría al final.",
        entities=["el protagonista"],
        expected_deaths=[],  # Es ficción dentro de ficción
        difficulty="adversarial",
        linguistic_note="Muerte en narrativa secundaria",
    ),
    VitalStatusTestCase(
        id="narr_02_pelicula",
        category="nivel_narrativo",
        text="En la película, el héroe murió salvando a todos.",
        entities=["el héroe"],
        expected_deaths=[],  # Es referencia a otra obra
        difficulty="adversarial",
        linguistic_note="Muerte en película mencionada",
    ),
    VitalStatusTestCase(
        id="narr_03_cuento",
        category="nivel_narrativo",
        text='El abuelo contó: "El dragón mató al príncipe".',
        entities=["el príncipe", "El dragón"],
        expected_deaths=[],  # Es cuento dentro de la historia
        difficulty="hard",
        linguistic_note="Muerte en cuento narrado",
    ),
]

# =============================================================================
# CATEGORÍA 17: SUEÑOS Y ALUCINACIONES
# =============================================================================

DREAM_TESTS = [
    VitalStatusTestCase(
        id="dream_01_sono",
        category="suenos",
        text="Ana soñó que su hermano moría. Despertó asustada.",
        entities=["su hermano", "Ana"],
        expected_deaths=[],
        not_deaths=["su hermano"],
        difficulty="hard",
        linguistic_note="Muerte en sueño - no real",
    ),
    VitalStatusTestCase(
        id="dream_02_alucino",
        category="suenos",
        text="Bajo los efectos de la fiebre, Pedro alucinó que lo mataban.",
        entities=["Pedro"],
        expected_deaths=[],
        not_deaths=["Pedro"],
        difficulty="hard",
        linguistic_note="Muerte en alucinación",
    ),
    VitalStatusTestCase(
        id="dream_03_imaginaba",
        category="suenos",
        text="María imaginaba que Juan moría y se aterraba.",
        entities=["Juan", "María"],
        expected_deaths=[],
        not_deaths=["Juan"],
        difficulty="hard",
        linguistic_note="Muerte imaginada",
    ),
]

# =============================================================================
# CATEGORÍA 18: NARRADOR NO CONFIABLE
# =============================================================================

UNRELIABLE_NARRATOR_TESTS = [
    VitalStatusTestCase(
        id="unrel_01_creo",
        category="narrador_no_confiable",
        text="Creo que Juan murió, pero no estoy seguro.",
        entities=["Juan"],
        expected_deaths=[],  # Incertidumbre
        difficulty="adversarial",
        linguistic_note="Narrador inseguro",
    ),
    VitalStatusTestCase(
        id="unrel_02_dicen",
        category="narrador_no_confiable",
        text="Dicen que María murió, pero hay quien la vio después.",
        entities=["María"],
        expected_deaths=[],  # Información contradictoria
        difficulty="adversarial",
        linguistic_note="Rumor no confirmado",
    ),
    VitalStatusTestCase(
        id="unrel_03_parecia",
        category="narrador_no_confiable",
        text="Parecía muerto, pero las apariencias engañan.",
        entities=[],
        expected_deaths=[],
        difficulty="hard",
        linguistic_note="Apariencia vs realidad",
    ),
]

# =============================================================================
# CATEGORÍA 19: MÚLTIPLES MUERTES MISMO CAPÍTULO
# =============================================================================

MULTIPLE_DEATHS_TESTS = [
    VitalStatusTestCase(
        id="multi_01_dos",
        category="multiples_muertes",
        text="Juan mató a Pedro y luego se suicidó.",
        entities=["Juan", "Pedro"],
        expected_deaths=["Pedro", "Juan"],
        difficulty="medium",
        linguistic_note="Dos muertes en una oración",
    ),
    VitalStatusTestCase(
        id="multi_02_tres",
        category="multiples_muertes",
        text="En el tiroteo murieron Ana, Carlos y Elena.",
        entities=["Ana", "Carlos", "Elena"],
        expected_deaths=["Ana", "Carlos", "Elena"],
        difficulty="medium",
        linguistic_note="Múltiples muertes listadas",
    ),
]

# =============================================================================
# CATEGORÍA 20: SECUENCIA TEMPORAL INVERSA
# =============================================================================

INVERSE_TEMPORAL_TESTS = [
    VitalStatusTestCase(
        id="inv_01_ya_muerto",
        category="temporal_inversa",
        text="Cuando llegaron, Pedro ya estaba muerto desde hacía horas.",
        entities=["Pedro"],
        expected_deaths=["Pedro"],
        chapter=2,
        difficulty="medium",
        linguistic_note="Muerte anterior al tiempo narrativo",
    ),
    VitalStatusTestCase(
        id="inv_02_habia_muerto",
        category="temporal_inversa",
        text="María había muerto mucho antes de que comenzara esta historia.",
        entities=["María"],
        expected_deaths=["María"],
        difficulty="hard",
        linguistic_note="Muerte previa a la narrativa",
    ),
]


# =============================================================================
# FIXTURE Y TEST RUNNER
# =============================================================================

ALL_VITAL_STATUS_TESTS = (
    DIRECT_DEATH_TESTS
    + CAUSED_DEATH_TESTS
    + REPORTED_DEATH_TESTS
    + IMPLIED_DEATH_TESTS
    + FALSE_POSITIVE_TESTS
    + VALID_REFERENCE_TESTS
    + RESURRECTION_TESTS
    + GENRE_SPECIFIC_TESTS
    + AMBIGUOUS_TESTS
    + TEMPORAL_TESTS
    + EUPHEMISM_TESTS
    + COLLECTIVE_TESTS
    + ANIMAL_TESTS
    + PERSONIFICATION_TESTS
    + SYMBOLIC_TESTS
    + NARRATIVE_LEVEL_TESTS
    + DREAM_TESTS
    + UNRELIABLE_NARRATOR_TESTS
    + MULTIPLE_DEATHS_TESTS
    + INVERSE_TEMPORAL_TESTS
)


class TestVitalStatusAdversarial:
    """Tests adversariales para el sistema de vital status."""

    @pytest.fixture
    def analyzer(self):
        """Crea instancia del analizador."""
        from narrative_assistant.analysis.vital_status import VitalStatusAnalyzer

        return VitalStatusAnalyzer(project_id=1)

    def _register_entities(self, analyzer, entities: list[str]):
        """Registra entidades en el analizador."""
        for i, name in enumerate(entities, start=1):
            # Limpiar nombre de artículos para registro
            clean_name = name.strip()
            for prefix in ["el ", "la ", "los ", "las ", "El ", "La ", "Los ", "Las "]:
                if clean_name.lower().startswith(prefix.lower()):
                    clean_name = clean_name[len(prefix) :]
                    break
            analyzer.register_entity(i, clean_name)

    def _name_in_deaths(self, deaths, name: str) -> bool:
        """Verifica si un nombre está en las muertes detectadas."""
        name_lower = name.lower()
        for death in deaths:
            if name_lower in death.entity_name.lower():
                return True
        return False

    @pytest.mark.parametrize("test_case", ALL_VITAL_STATUS_TESTS, ids=lambda tc: tc.id)
    def test_vital_status_case(self, analyzer, test_case: VitalStatusTestCase):
        """Ejecuta un caso de test de vital status."""
        # Registrar entidades
        self._register_entities(analyzer, test_case.entities)

        # Detectar muertes
        deaths = analyzer.detect_death_events(test_case.text, chapter=test_case.chapter)

        # Verificar muertes esperadas
        for expected_death in test_case.expected_deaths:
            assert self._name_in_deaths(deaths, expected_death), (
                f"[{test_case.id}] Muerte de '{expected_death}' no detectada.\n"
                f"Muertes detectadas: {[d.entity_name for d in deaths]}\n"
                f"Texto: {test_case.text}\n"
                f"Nota: {test_case.linguistic_note}"
            )

        # Verificar que NO se detecten falsos positivos
        for not_death in test_case.not_deaths:
            assert not self._name_in_deaths(deaths, not_death), (
                f"[{test_case.id}] '{not_death}' detectado como muerto incorrectamente.\n"
                f"Muertes detectadas: {[d.entity_name for d in deaths]}\n"
                f"Texto: {test_case.text}\n"
                f"Nota: {test_case.linguistic_note}"
            )


class TestVitalStatusByCategory:
    """Tests organizados por categoría."""

    @pytest.fixture
    def analyzer(self):
        from narrative_assistant.analysis.vital_status import VitalStatusAnalyzer

        return VitalStatusAnalyzer(project_id=1)

    @pytest.mark.parametrize("test_case", FALSE_POSITIVE_TESTS, ids=lambda tc: tc.id)
    def test_false_positives(self, analyzer, test_case):
        """Tests de falsos positivos (expresiones idiomáticas)."""
        self._run_test(analyzer, test_case)

    @pytest.mark.parametrize("test_case", RESURRECTION_TESTS, ids=lambda tc: tc.id)
    def test_resurrection(self, analyzer, test_case):
        """Tests de resurrección y casi-muerte."""
        self._run_test(analyzer, test_case)

    @pytest.mark.parametrize("test_case", DREAM_TESTS, ids=lambda tc: tc.id)
    def test_dreams(self, analyzer, test_case):
        """Tests de sueños y alucinaciones."""
        self._run_test(analyzer, test_case)

    def _run_test(self, analyzer, test_case: VitalStatusTestCase):
        """Ejecuta un caso de test."""
        for i, name in enumerate(test_case.entities, start=1):
            clean_name = name.strip()
            for prefix in ["el ", "la ", "los ", "las "]:
                if clean_name.lower().startswith(prefix):
                    clean_name = clean_name[len(prefix) :]
                    break
            analyzer.register_entity(i, clean_name)

        deaths = analyzer.detect_death_events(test_case.text, chapter=test_case.chapter)

        for not_death in test_case.not_deaths:
            found = any(not_death.lower() in d.entity_name.lower() for d in deaths)
            assert not found, f"[{test_case.id}] '{not_death}' no debería ser detectado"


def get_test_summary():
    """Genera resumen de los tests por categoría."""
    from collections import Counter

    categories = Counter(tc.category for tc in ALL_VITAL_STATUS_TESTS)
    difficulties = Counter(tc.difficulty for tc in ALL_VITAL_STATUS_TESTS)

    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS ADVERSARIALES DE VITAL STATUS")
    print("=" * 60)
    print(f"\nTotal de casos: {len(ALL_VITAL_STATUS_TESTS)}")
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
