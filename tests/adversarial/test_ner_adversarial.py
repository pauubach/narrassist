"""
Tests adversariales GAN-style para el sistema de reconocimiento de entidades (NER).

Objetivo: Identificar casos límite donde el NER falla para mejorar
iterativamente el algoritmo.

Categorías de tests:
1. Nombres compuestos y apellidos
2. Apodos y diminutivos
3. Títulos y tratamientos
4. Nombres en diálogos
5. Nombres con artículos
6. Nombres extranjeros
7. Entidades ambiguas (persona/lugar/org)
8. Metáforas y personificación
9. Referencias históricas/ficticias
10. Nombres incompletos
11. Coordinación de nombres
12. Nombres en aposición
13. Pronombres como falsos positivos
14. Profesiones vs nombres
15. Lugares vs personas
16. Organizaciones vs personas
17. Nombres en mayúsculas
18. Nombres con preposiciones
19. Alias y "conocido como"
20. Entidades en listas

Basado en errores comunes de NER en español:
- Confusión con palabras comunes capitalizadas
- Nombres compuestos mal segmentados
- Falsos positivos con títulos
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NERTestCase:
    """Caso de test para NER."""
    id: str
    category: str
    text: str
    expected_persons: list[str] = field(default_factory=list)
    expected_locations: list[str] = field(default_factory=list)
    expected_organizations: list[str] = field(default_factory=list)
    not_persons: list[str] = field(default_factory=list)  # Falsos positivos a evitar
    not_locations: list[str] = field(default_factory=list)
    not_organizations: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: NOMBRES COMPUESTOS Y APELLIDOS
# =============================================================================

COMPOUND_NAME_TESTS = [
    NERTestCase(
        id="comp_01_two_surnames",
        category="nombres_compuestos",
        text="María García López llegó temprano.",
        expected_persons=["María García López"],
        difficulty="easy",
        linguistic_note="Nombre + dos apellidos (patrón español)"
    ),
    NERTestCase(
        id="comp_02_de_surname",
        category="nombres_compuestos",
        text="Juan de la Cruz era poeta.",
        expected_persons=["Juan de la Cruz"],
        difficulty="medium",
        linguistic_note="Apellido con 'de la'"
    ),
    NERTestCase(
        id="comp_03_del_surname",
        category="nombres_compuestos",
        text="Pedro del Valle habló primero.",
        expected_persons=["Pedro del Valle"],
        difficulty="medium",
        linguistic_note="Apellido con 'del'"
    ),
    NERTestCase(
        id="comp_04_compound_first_name",
        category="nombres_compuestos",
        text="María José y Juan Carlos llegaron juntos.",
        expected_persons=["María José", "Juan Carlos"],
        difficulty="medium",
        linguistic_note="Nombres compuestos (dos nombres de pila)"
    ),
    NERTestCase(
        id="comp_05_y_in_surname",
        category="nombres_compuestos",
        text="José Ortega y Gasset escribió mucho.",
        expected_persons=["José Ortega y Gasset"],
        difficulty="hard",
        linguistic_note="Apellido con 'y' (aristocrático)"
    ),
    NERTestCase(
        id="comp_06_particle_surnames",
        category="nombres_compuestos",
        text="Antonio de los Ríos y María van der Berg conversaban.",
        expected_persons=["Antonio de los Ríos", "María van der Berg"],
        difficulty="hard",
        linguistic_note="Partículas nobiliarias múltiples"
    ),
    NERTestCase(
        id="comp_07_hyphenated",
        category="nombres_compuestos",
        text="Ana Martín-Pérez presentó el proyecto.",
        expected_persons=["Ana Martín-Pérez"],
        difficulty="medium",
        linguistic_note="Apellido con guión"
    ),
]

# =============================================================================
# CATEGORÍA 2: APODOS Y DIMINUTIVOS
# =============================================================================

NICKNAME_TESTS = [
    NERTestCase(
        id="nick_01_quotes",
        category="apodos",
        text='Juan "el Rápido" García ganó la carrera.',
        expected_persons=["Juan García", "el Rápido"],  # O combinado
        difficulty="hard",
        linguistic_note="Apodo entre comillas"
    ),
    NERTestCase(
        id="nick_02_diminutive",
        category="apodos",
        text="Juanito era el menor de los hermanos. Juan creció rápido.",
        expected_persons=["Juanito", "Juan"],
        difficulty="medium",
        linguistic_note="Diminutivo como variante del nombre"
    ),
    NERTestCase(
        id="nick_03_alias",
        category="apodos",
        text="Pedro, conocido como Perico, trabajaba en el campo.",
        expected_persons=["Pedro", "Perico"],
        difficulty="medium",
        linguistic_note="Alias con 'conocido como'"
    ),
    NERTestCase(
        id="nick_04_el_la",
        category="apodos",
        text="La Paca y el Manolo llegaron tarde.",
        expected_persons=["La Paca", "el Manolo"],
        difficulty="hard",
        linguistic_note="Nombres con artículo (coloquial)"
    ),
    NERTestCase(
        id="nick_05_augmentative",
        category="apodos",
        text="Pedrote era el más alto del grupo.",
        expected_persons=["Pedrote"],
        difficulty="medium",
        linguistic_note="Aumentativo como nombre"
    ),
]

# =============================================================================
# CATEGORÍA 3: TÍTULOS Y TRATAMIENTOS
# =============================================================================

TITLE_TESTS = [
    NERTestCase(
        id="title_01_don",
        category="titulos",
        text="Don Quijote cabalgaba por La Mancha.",
        expected_persons=["Don Quijote"],
        expected_locations=["La Mancha"],
        difficulty="easy",
        linguistic_note="Título 'Don' + nombre"
    ),
    NERTestCase(
        id="title_02_doctor",
        category="titulos",
        text="El doctor García y la doctora López operaron juntos.",
        expected_persons=["García", "López"],  # Sin el título
        not_persons=["doctor", "doctora"],
        difficulty="medium",
        linguistic_note="Título profesional no es parte del nombre"
    ),
    NERTestCase(
        id="title_03_senor",
        category="titulos",
        text="El señor Martínez y la señora Ruiz firmaron el contrato.",
        expected_persons=["Martínez", "Ruiz"],
        not_persons=["señor", "señora"],
        difficulty="medium",
        linguistic_note="Tratamiento de cortesía"
    ),
    NERTestCase(
        id="title_04_padre",
        category="titulos",
        text="El padre Antonio bendijo la ceremonia.",
        expected_persons=["Antonio"],  # o "padre Antonio"
        difficulty="medium",
        linguistic_note="Título religioso"
    ),
    NERTestCase(
        id="title_05_rey",
        category="titulos",
        text="El rey Felipe VI inauguró el edificio.",
        expected_persons=["Felipe VI"],
        not_persons=["rey"],
        difficulty="medium",
        linguistic_note="Título nobiliario con numeral"
    ),
    NERTestCase(
        id="title_06_multiple",
        category="titulos",
        text="Su Excelencia el embajador don José García presentó credenciales.",
        expected_persons=["José García"],
        not_persons=["Excelencia", "embajador"],
        difficulty="hard",
        linguistic_note="Múltiples títulos antes del nombre"
    ),
    NERTestCase(
        id="title_07_general",
        category="titulos",
        text="El general Franco y el coronel Tejero conspiraron.",
        expected_persons=["Franco", "Tejero"],
        not_persons=["general", "coronel"],
        difficulty="medium",
        linguistic_note="Rangos militares"
    ),
]

# =============================================================================
# CATEGORÍA 4: NOMBRES EN DIÁLOGOS
# =============================================================================

DIALOGUE_TESTS = [
    NERTestCase(
        id="dial_01_vocative",
        category="dialogos",
        text='—María, ven aquí —dijo Juan.',
        expected_persons=["María", "Juan"],
        difficulty="easy",
        linguistic_note="Vocativo en diálogo"
    ),
    NERTestCase(
        id="dial_02_reported",
        category="dialogos",
        text='"Mi amigo Pedro vendrá", dijo María.',
        expected_persons=["Pedro", "María"],
        difficulty="medium",
        linguistic_note="Nombre mencionado en diálogo"
    ),
    NERTestCase(
        id="dial_03_nested",
        category="dialogos",
        text='Juan dijo: "Ana me contó que Luis llegó".',
        expected_persons=["Juan", "Ana", "Luis"],
        difficulty="medium",
        linguistic_note="Múltiples niveles de cita"
    ),
    NERTestCase(
        id="dial_04_interrupted",
        category="dialogos",
        text='—Pedro —comenzó María— no deberías...',
        expected_persons=["Pedro", "María"],
        difficulty="medium",
        linguistic_note="Diálogo interrumpido por inciso"
    ),
    NERTestCase(
        id="dial_05_greeting",
        category="dialogos",
        text='"¡Hola, Pepe!" saludó Rosa.',
        expected_persons=["Pepe", "Rosa"],
        difficulty="easy",
        linguistic_note="Saludo con vocativo"
    ),
]

# =============================================================================
# CATEGORÍA 5: NOMBRES CON ARTÍCULOS
# =============================================================================

ARTICLE_TESTS = [
    NERTestCase(
        id="art_01_location_article",
        category="articulos",
        text="Viajó a La Habana y luego a El Cairo.",
        expected_locations=["La Habana", "El Cairo"],
        not_persons=["La Habana", "El Cairo"],
        difficulty="medium",
        linguistic_note="Topónimos con artículo incorporado"
    ),
    NERTestCase(
        id="art_02_org_article",
        category="articulos",
        text="Trabaja en El País y colabora con La Vanguardia.",
        expected_organizations=["El País", "La Vanguardia"],
        not_persons=["El País", "La Vanguardia"],
        difficulty="medium",
        linguistic_note="Organizaciones con artículo"
    ),
    NERTestCase(
        id="art_03_el_not_article",
        category="articulos",
        text="El Greco pintó muchos cuadros.",
        expected_persons=["El Greco"],
        difficulty="medium",
        linguistic_note="Apodo artístico con artículo"
    ),
    NERTestCase(
        id="art_04_la_person",
        category="articulos",
        text="La Pasionaria dio un discurso memorable.",
        expected_persons=["La Pasionaria"],
        difficulty="hard",
        linguistic_note="Apodo político con artículo"
    ),
]

# =============================================================================
# CATEGORÍA 6: NOMBRES EXTRANJEROS
# =============================================================================

FOREIGN_TESTS = [
    NERTestCase(
        id="for_01_english",
        category="extranjeros",
        text="William Shakespeare y John Smith eran ingleses.",
        expected_persons=["William Shakespeare", "John Smith"],
        difficulty="easy",
        linguistic_note="Nombres ingleses"
    ),
    NERTestCase(
        id="for_02_german",
        category="extranjeros",
        text="Johann Wolfgang von Goethe escribió Fausto.",
        expected_persons=["Johann Wolfgang von Goethe"],
        difficulty="hard",
        linguistic_note="Nombre alemán con 'von'"
    ),
    NERTestCase(
        id="for_03_arabic",
        category="extranjeros",
        text="Ibn Battuta viajó por el mundo conocido.",
        expected_persons=["Ibn Battuta"],
        difficulty="hard",
        linguistic_note="Nombre árabe con 'Ibn'"
    ),
    NERTestCase(
        id="for_04_asian",
        category="extranjeros",
        text="Mao Zedong y Deng Xiaoping gobernaron China.",
        expected_persons=["Mao Zedong", "Deng Xiaoping"],
        expected_locations=["China"],
        difficulty="medium",
        linguistic_note="Nombres chinos (apellido primero)"
    ),
    NERTestCase(
        id="for_05_russian",
        category="extranjeros",
        text="Fiódor Dostoyevski y León Tolstói son clásicos.",
        expected_persons=["Fiódor Dostoyevski", "León Tolstói"],
        difficulty="medium",
        linguistic_note="Nombres rusos hispanizados"
    ),
    NERTestCase(
        id="for_06_portuguese",
        category="extranjeros",
        text="Fernando Pessoa y José Saramago son portugueses.",
        expected_persons=["Fernando Pessoa", "José Saramago"],
        difficulty="easy",
        linguistic_note="Nombres portugueses"
    ),
]

# =============================================================================
# CATEGORÍA 7: ENTIDADES AMBIGUAS
# =============================================================================

AMBIGUOUS_TESTS = [
    NERTestCase(
        id="ambig_01_washington",
        category="ambiguedad",
        text="Washington cruzó el río. Washington es la capital.",
        expected_persons=["Washington"],  # Primera mención
        expected_locations=["Washington"],  # Segunda mención
        difficulty="adversarial",
        linguistic_note="Mismo nombre, diferente tipo según contexto"
    ),
    NERTestCase(
        id="ambig_02_barcelona",
        category="ambiguedad",
        text="El Barcelona ganó el partido. Barcelona es una ciudad hermosa.",
        expected_organizations=["Barcelona"],  # equipo
        expected_locations=["Barcelona"],  # ciudad
        difficulty="adversarial",
        linguistic_note="Barcelona como equipo vs ciudad"
    ),
    NERTestCase(
        id="ambig_03_amazon",
        category="ambiguedad",
        text="El Amazonas fluye por la selva. Amazon vende de todo.",
        expected_locations=["Amazonas"],
        expected_organizations=["Amazon"],
        difficulty="medium",
        linguistic_note="Río vs empresa"
    ),
    NERTestCase(
        id="ambig_04_victoria",
        category="ambiguedad",
        text="Victoria celebró su victoria. La reina Victoria reinó mucho tiempo.",
        expected_persons=["Victoria", "Victoria"],
        not_persons=["victoria"],  # minúscula = sustantivo común
        difficulty="hard",
        linguistic_note="Nombre propio vs sustantivo común"
    ),
    NERTestCase(
        id="ambig_05_rosa",
        category="ambiguedad",
        text="Rosa plantó una rosa en el jardín.",
        expected_persons=["Rosa"],
        not_persons=["rosa"],  # minúscula
        difficulty="medium",
        linguistic_note="Nombre propio vs sustantivo común"
    ),
]

# =============================================================================
# CATEGORÍA 8: METÁFORAS Y PERSONIFICACIÓN
# =============================================================================

METAPHOR_TESTS = [
    NERTestCase(
        id="meta_01_death",
        category="metaforas",
        text="La Muerte vino a buscarlo.",
        not_persons=["La Muerte"],  # Personificación, no persona real
        difficulty="hard",
        linguistic_note="Personificación de concepto abstracto"
    ),
    NERTestCase(
        id="meta_02_nature",
        category="metaforas",
        text="La Naturaleza es sabia. El Tiempo no perdona.",
        not_persons=["La Naturaleza", "El Tiempo"],
        difficulty="hard",
        linguistic_note="Conceptos personificados"
    ),
    NERTestCase(
        id="meta_03_country",
        category="metaforas",
        text="España lloró la derrota.",
        expected_locations=["España"],
        not_persons=["España"],
        difficulty="medium",
        linguistic_note="País como agente (metonimia)"
    ),
    NERTestCase(
        id="meta_04_ship",
        category="metaforas",
        text="El Titanic navegaba orgulloso.",
        not_persons=["El Titanic"],  # Es un barco
        difficulty="medium",
        linguistic_note="Nombre de vehículo, no persona"
    ),
]

# =============================================================================
# CATEGORÍA 9: REFERENCIAS HISTÓRICAS/FICTICIAS
# =============================================================================

HISTORICAL_TESTS = [
    NERTestCase(
        id="hist_01_fictional",
        category="historicos",
        text="Sherlock Holmes investigó el caso. Watson lo ayudó.",
        expected_persons=["Sherlock Holmes", "Watson"],
        difficulty="easy",
        linguistic_note="Personajes ficticios famosos"
    ),
    NERTestCase(
        id="hist_02_mythological",
        category="historicos",
        text="Zeus lanzó un rayo. Atenea observaba.",
        expected_persons=["Zeus", "Atenea"],  # O no, según criterio
        difficulty="hard",
        linguistic_note="Dioses mitológicos"
    ),
    NERTestCase(
        id="hist_03_biblical",
        category="historicos",
        text="Moisés guió al pueblo. Abraham era su antepasado.",
        expected_persons=["Moisés", "Abraham"],
        difficulty="medium",
        linguistic_note="Personajes bíblicos"
    ),
    NERTestCase(
        id="hist_04_legendary",
        category="historicos",
        text="El Cid conquistó Valencia. Doña Jimena lo esperaba.",
        expected_persons=["El Cid", "Doña Jimena"],
        expected_locations=["Valencia"],
        difficulty="medium",
        linguistic_note="Personajes histórico-legendarios"
    ),
]

# =============================================================================
# CATEGORÍA 10: NOMBRES INCOMPLETOS
# =============================================================================

INCOMPLETE_TESTS = [
    NERTestCase(
        id="inc_01_first_only",
        category="incompletos",
        text="María entró. Luego llegó Juan.",
        expected_persons=["María", "Juan"],
        difficulty="easy",
        linguistic_note="Solo nombre de pila"
    ),
    NERTestCase(
        id="inc_02_surname_only",
        category="incompletos",
        text="García habló primero. Martínez respondió.",
        expected_persons=["García", "Martínez"],
        difficulty="medium",
        linguistic_note="Solo apellido (contexto formal)"
    ),
    NERTestCase(
        id="inc_03_initial",
        category="incompletos",
        text="J. García y M. López firmaron.",
        expected_persons=["J. García", "M. López"],
        difficulty="medium",
        linguistic_note="Inicial + apellido"
    ),
    NERTestCase(
        id="inc_04_abbreviated",
        category="incompletos",
        text="Fdo. García autorizó el documento.",
        expected_persons=["García"],  # "Fdo." es abreviatura de "Firmado"
        not_persons=["Fdo."],
        difficulty="hard",
        linguistic_note="Abreviatura de fórmula, no nombre"
    ),
]

# =============================================================================
# CATEGORÍA 11: COORDINACIÓN DE NOMBRES
# =============================================================================

COORDINATION_TESTS = [
    NERTestCase(
        id="coord_01_simple",
        category="coordinacion",
        text="Juan, María y Pedro llegaron.",
        expected_persons=["Juan", "María", "Pedro"],
        difficulty="easy",
        linguistic_note="Lista simple de nombres"
    ),
    NERTestCase(
        id="coord_02_with_surnames",
        category="coordinacion",
        text="Juan García, María López y Pedro Ruiz asistieron.",
        expected_persons=["Juan García", "María López", "Pedro Ruiz"],
        difficulty="medium",
        linguistic_note="Lista con nombre y apellido"
    ),
    NERTestCase(
        id="coord_03_shared_surname",
        category="coordinacion",
        text="Juan y María García son hermanos.",
        expected_persons=["Juan García", "María García"],  # O detectar compartido
        difficulty="hard",
        linguistic_note="Apellido compartido (elipsis)"
    ),
    NERTestCase(
        id="coord_04_family",
        category="coordinacion",
        text="Los García y los López se reunieron.",
        expected_persons=[],  # Familias, no individuos
        difficulty="hard",
        linguistic_note="Apellidos pluralizados = familias"
    ),
]

# =============================================================================
# CATEGORÍA 12: NOMBRES EN APOSICIÓN
# =============================================================================

APPOSITION_TESTS = [
    NERTestCase(
        id="apos_01_simple",
        category="aposicion",
        text="Mi amigo Pedro llegó tarde.",
        expected_persons=["Pedro"],
        not_persons=["amigo"],
        difficulty="easy",
        linguistic_note="Aposición con sustantivo común"
    ),
    NERTestCase(
        id="apos_02_profession",
        category="aposicion",
        text="El escritor García Márquez ganó el Nobel.",
        expected_persons=["García Márquez"],
        not_persons=["escritor"],
        difficulty="medium",
        linguistic_note="Profesión en aposición"
    ),
    NERTestCase(
        id="apos_03_relation",
        category="aposicion",
        text="Su hermana María la ayudó.",
        expected_persons=["María"],
        not_persons=["hermana"],
        difficulty="easy",
        linguistic_note="Relación familiar en aposición"
    ),
    NERTestCase(
        id="apos_04_epithet",
        category="aposicion",
        text="Alfonso X, el Sabio, promovió la cultura.",
        expected_persons=["Alfonso X"],
        difficulty="hard",
        linguistic_note="Epíteto en aposición"
    ),
]

# =============================================================================
# CATEGORÍA 13: PRONOMBRES COMO FALSOS POSITIVOS
# =============================================================================

FALSE_POSITIVE_TESTS = [
    NERTestCase(
        id="fp_01_el_pronoun",
        category="falsos_positivos",
        text="El entró en la casa.",
        expected_persons=[],  # "El" aquí es error tipográfico de "Él"
        not_persons=["El"],
        difficulty="medium",
        linguistic_note="Artículo/pronombre mal escrito"
    ),
    NERTestCase(
        id="fp_02_common_noun",
        category="falsos_positivos",
        text="El Amor es ciego. La Verdad duele.",
        not_persons=["El Amor", "La Verdad"],  # Conceptos abstractos
        difficulty="hard",
        linguistic_note="Sustantivos abstractos mayúscula"
    ),
    NERTestCase(
        id="fp_03_sentence_start",
        category="falsos_positivos",
        text="Alto y fuerte, el hombre avanzó.",
        not_persons=["Alto"],
        difficulty="easy",
        linguistic_note="Mayúscula inicial no indica nombre"
    ),
    NERTestCase(
        id="fp_04_quote_start",
        category="falsos_positivos",
        text='"Bueno, ya veremos", dijo.',
        not_persons=["Bueno"],
        difficulty="easy",
        linguistic_note="Palabra inicial de cita"
    ),
]

# =============================================================================
# CATEGORÍA 14: PROFESIONES VS NOMBRES
# =============================================================================

PROFESSION_TESTS = [
    NERTestCase(
        id="prof_01_capitalized",
        category="profesiones",
        text="El Presidente habló. El Ministro escuchó.",
        not_persons=["Presidente", "Ministro"],  # Cargo, no nombre
        difficulty="medium",
        linguistic_note="Cargo institucional, no nombre"
    ),
    NERTestCase(
        id="prof_02_with_name",
        category="profesiones",
        text="El presidente Sánchez y la ministra López acordaron.",
        expected_persons=["Sánchez", "López"],
        not_persons=["presidente", "ministra"],
        difficulty="medium",
        linguistic_note="Cargo + nombre"
    ),
    NERTestCase(
        id="prof_03_teacher",
        category="profesiones",
        text="El profesor explicó la lección. La profesora García añadió detalles.",
        expected_persons=["García"],
        not_persons=["profesor", "profesora"],
        difficulty="medium",
        linguistic_note="Profesión sin/con nombre"
    ),
]

# =============================================================================
# CATEGORÍA 15: LUGARES VS PERSONAS
# =============================================================================

PLACE_PERSON_TESTS = [
    NERTestCase(
        id="plp_01_street",
        category="lugar_persona",
        text="Vive en la calle Cervantes. Cervantes escribió el Quijote.",
        expected_persons=["Cervantes"],  # Segunda mención
        expected_locations=["calle Cervantes"],  # Primera mención
        difficulty="hard",
        linguistic_note="Nombre en topónimo vs persona"
    ),
    NERTestCase(
        id="plp_02_building",
        category="lugar_persona",
        text="El hospital Gregorio Marañón está en Madrid.",
        expected_persons=[],  # No hay persona, solo nombre de hospital
        expected_locations=["hospital Gregorio Marañón", "Madrid"],
        difficulty="hard",
        linguistic_note="Nombre propio en nombre de edificio"
    ),
    NERTestCase(
        id="plp_03_airport",
        category="lugar_persona",
        text="Aterrizó en el aeropuerto Adolfo Suárez.",
        expected_persons=[],
        expected_locations=["aeropuerto Adolfo Suárez"],
        difficulty="hard",
        linguistic_note="Nombre honorífico en infraestructura"
    ),
]

# =============================================================================
# CATEGORÍA 16: ORGANIZACIONES VS PERSONAS
# =============================================================================

ORG_PERSON_TESTS = [
    NERTestCase(
        id="org_01_foundation",
        category="org_persona",
        text="La Fundación Rockefeller otorgó la beca.",
        expected_organizations=["Fundación Rockefeller"],
        not_persons=["Rockefeller"],  # Aquí es parte del nombre de org
        difficulty="medium",
        linguistic_note="Apellido en nombre de fundación"
    ),
    NERTestCase(
        id="org_02_company",
        category="org_persona",
        text="La empresa Ford fabrica coches. Ford revolucionó la industria.",
        expected_organizations=["Ford"],
        expected_persons=["Ford"],  # Segunda mención = persona histórica
        difficulty="adversarial",
        linguistic_note="Contexto diferencia empresa de persona"
    ),
    NERTestCase(
        id="org_03_university",
        category="org_persona",
        text="Estudió en la Universidad Complutense de Madrid.",
        expected_organizations=["Universidad Complutense de Madrid"],
        expected_locations=["Madrid"],
        not_persons=["Complutense"],
        difficulty="medium",
        linguistic_note="Universidad con nombre propio"
    ),
]

# =============================================================================
# CATEGORÍA 17: NOMBRES EN MAYÚSCULAS
# =============================================================================

CAPITALIZATION_TESTS = [
    NERTestCase(
        id="cap_01_all_caps",
        category="mayusculas",
        text="JUAN GARCÍA firmó el documento.",
        expected_persons=["JUAN GARCÍA"],
        difficulty="medium",
        linguistic_note="Nombre en mayúsculas (documentos legales)"
    ),
    NERTestCase(
        id="cap_02_title_case",
        category="mayusculas",
        text="La Señora De La Casa salió.",
        not_persons=["La Señora De La Casa"],  # No es nombre propio
        difficulty="medium",
        linguistic_note="Title Case no indica nombre propio"
    ),
    NERTestCase(
        id="cap_03_lowercase_name",
        category="mayusculas",
        text="El poeta e.e. cummings no usaba mayúsculas.",
        expected_persons=["e.e. cummings"],
        difficulty="adversarial",
        linguistic_note="Nombre en minúsculas (estilo del autor)"
    ),
]

# =============================================================================
# CATEGORÍA 18: NOMBRES CON PREPOSICIONES
# =============================================================================

PREPOSITION_TESTS = [
    NERTestCase(
        id="prep_01_de",
        category="preposiciones",
        text="Leonardo da Vinci pintó la Mona Lisa.",
        expected_persons=["Leonardo da Vinci"],
        difficulty="medium",
        linguistic_note="Nombre italiano con 'da'"
    ),
    NERTestCase(
        id="prep_02_di",
        category="preposiciones",
        text="Giuseppe di Stefano era tenor.",
        expected_persons=["Giuseppe di Stefano"],
        difficulty="medium",
        linguistic_note="Nombre italiano con 'di'"
    ),
    NERTestCase(
        id="prep_03_af",
        category="preposiciones",
        text="Alfred Nobel y Ingmar af Trolle se reunieron.",
        expected_persons=["Alfred Nobel", "Ingmar af Trolle"],
        difficulty="hard",
        linguistic_note="Nombre escandinavo con 'af'"
    ),
    NERTestCase(
        id="prep_04_mac",
        category="preposiciones",
        text="Ronald McDonald y Ian MacLeod son escoceses.",
        expected_persons=["Ronald McDonald", "Ian MacLeod"],
        difficulty="medium",
        linguistic_note="Prefijos escoceses/irlandeses"
    ),
]

# =============================================================================
# CATEGORÍA 19: ALIAS Y "CONOCIDO COMO"
# =============================================================================

ALIAS_TESTS = [
    NERTestCase(
        id="alias_01_aka",
        category="alias",
        text="Pablo Ruiz Picasso, conocido como Picasso, revolucionó el arte.",
        expected_persons=["Pablo Ruiz Picasso", "Picasso"],
        difficulty="medium",
        linguistic_note="Nombre completo y nombre artístico"
    ),
    NERTestCase(
        id="alias_02_llamado",
        category="alias",
        text="El hombre llamado Pedro huyó.",
        expected_persons=["Pedro"],
        not_persons=["hombre"],
        difficulty="easy",
        linguistic_note="Identificación con 'llamado'"
    ),
    NERTestCase(
        id="alias_03_apodado",
        category="alias",
        text="Juan, apodado el Loco, asustaba a todos.",
        expected_persons=["Juan"],
        difficulty="medium",
        linguistic_note="Apodo con 'apodado'"
    ),
    NERTestCase(
        id="alias_04_stage_name",
        category="alias",
        text="Norma Jeane Mortenson, mejor conocida como Marilyn Monroe, era actriz.",
        expected_persons=["Norma Jeane Mortenson", "Marilyn Monroe"],
        difficulty="hard",
        linguistic_note="Nombre real y artístico"
    ),
]

# =============================================================================
# CATEGORÍA 20: ENTIDADES EN LISTAS
# =============================================================================

LIST_TESTS = [
    NERTestCase(
        id="list_01_simple",
        category="listas",
        text="Asistieron: Juan García, María López, Pedro Ruiz.",
        expected_persons=["Juan García", "María López", "Pedro Ruiz"],
        difficulty="medium",
        linguistic_note="Lista formal con dos puntos"
    ),
    NERTestCase(
        id="list_02_numbered",
        category="listas",
        text="1. Juan García\n2. María López\n3. Pedro Ruiz",
        expected_persons=["Juan García", "María López", "Pedro Ruiz"],
        difficulty="medium",
        linguistic_note="Lista numerada"
    ),
    NERTestCase(
        id="list_03_mixed",
        category="listas",
        text="Participantes: Dr. García (Madrid), Dra. López (Barcelona), Prof. Ruiz (Valencia).",
        expected_persons=["García", "López", "Ruiz"],
        expected_locations=["Madrid", "Barcelona", "Valencia"],
        difficulty="hard",
        linguistic_note="Lista con títulos y ubicaciones"
    ),
]


# =============================================================================
# FIXTURE Y TEST RUNNER
# =============================================================================

ALL_NER_TESTS = (
    COMPOUND_NAME_TESTS +
    NICKNAME_TESTS +
    TITLE_TESTS +
    DIALOGUE_TESTS +
    ARTICLE_TESTS +
    FOREIGN_TESTS +
    AMBIGUOUS_TESTS +
    METAPHOR_TESTS +
    HISTORICAL_TESTS +
    INCOMPLETE_TESTS +
    COORDINATION_TESTS +
    APPOSITION_TESTS +
    FALSE_POSITIVE_TESTS +
    PROFESSION_TESTS +
    PLACE_PERSON_TESTS +
    ORG_PERSON_TESTS +
    CAPITALIZATION_TESTS +
    PREPOSITION_TESTS +
    ALIAS_TESTS +
    LIST_TESTS
)


class TestNERAdversarial:
    """Tests adversariales para el sistema NER."""

    @pytest.fixture
    def extractor(self):
        """Crea instancia del extractor NER."""
        from narrative_assistant.nlp.ner import NERExtractor
        return NERExtractor()

    def _get_persons(self, ner_result) -> list[str]:
        """Extrae nombres de personas del resultado."""
        from narrative_assistant.nlp.ner import EntityLabel
        return [e.text for e in ner_result.entities if e.label == EntityLabel.PER]

    def _get_locations(self, ner_result) -> list[str]:
        """Extrae ubicaciones del resultado."""
        from narrative_assistant.nlp.ner import EntityLabel
        return [e.text for e in ner_result.entities if e.label == EntityLabel.LOC]

    def _get_organizations(self, ner_result) -> list[str]:
        """Extrae organizaciones del resultado."""
        from narrative_assistant.nlp.ner import EntityLabel
        return [e.text for e in ner_result.entities if e.label == EntityLabel.ORG]

    def _entity_found(self, entities: list[str], expected: str) -> bool:
        """Verifica si una entidad esperada fue encontrada."""
        expected_lower = expected.lower()
        for entity in entities:
            if expected_lower in entity.lower() or entity.lower() in expected_lower:
                return True
        return False

    @pytest.mark.parametrize("test_case", ALL_NER_TESTS, ids=lambda tc: tc.id)
    def test_ner_case(self, extractor, test_case: NERTestCase):
        """Ejecuta un caso de test NER."""
        result = extractor.extract_entities(test_case.text)
        assert result.is_success, f"Extracción falló: {result.error}"

        ner_result = result.value
        persons = self._get_persons(ner_result)
        locations = self._get_locations(ner_result)
        organizations = self._get_organizations(ner_result)

        # Verificar personas esperadas
        for expected_person in test_case.expected_persons:
            assert self._entity_found(persons, expected_person), (
                f"[{test_case.id}] Persona '{expected_person}' no encontrada.\n"
                f"Personas detectadas: {persons}\n"
                f"Nota: {test_case.linguistic_note}"
            )

        # Verificar ubicaciones esperadas
        for expected_loc in test_case.expected_locations:
            assert self._entity_found(locations, expected_loc), (
                f"[{test_case.id}] Ubicación '{expected_loc}' no encontrada.\n"
                f"Ubicaciones detectadas: {locations}\n"
                f"Nota: {test_case.linguistic_note}"
            )

        # Verificar organizaciones esperadas
        for expected_org in test_case.expected_organizations:
            assert self._entity_found(organizations, expected_org), (
                f"[{test_case.id}] Organización '{expected_org}' no encontrada.\n"
                f"Organizaciones detectadas: {organizations}\n"
                f"Nota: {test_case.linguistic_note}"
            )

        # Verificar falsos positivos (lo que NO debería ser persona)
        for not_person in test_case.not_persons:
            is_wrongly_detected = any(
                not_person.lower() == p.lower() for p in persons
            )
            assert not is_wrongly_detected, (
                f"[{test_case.id}] '{not_person}' NO debería ser detectado como persona.\n"
                f"Personas detectadas: {persons}\n"
                f"Nota: {test_case.linguistic_note}"
            )


class TestNERByCategory:
    """Tests organizados por categoría."""

    @pytest.fixture
    def extractor(self):
        from narrative_assistant.nlp.ner import NERExtractor
        return NERExtractor()

    @pytest.mark.parametrize("test_case", COMPOUND_NAME_TESTS, ids=lambda tc: tc.id)
    def test_compound_names(self, extractor, test_case):
        """Tests de nombres compuestos."""
        self._run_test(extractor, test_case)

    @pytest.mark.parametrize("test_case", TITLE_TESTS, ids=lambda tc: tc.id)
    def test_titles(self, extractor, test_case):
        """Tests de títulos y tratamientos."""
        self._run_test(extractor, test_case)

    @pytest.mark.parametrize("test_case", AMBIGUOUS_TESTS, ids=lambda tc: tc.id)
    def test_ambiguous(self, extractor, test_case):
        """Tests de entidades ambiguas."""
        self._run_test(extractor, test_case)

    @pytest.mark.parametrize("test_case", FALSE_POSITIVE_TESTS, ids=lambda tc: tc.id)
    def test_false_positives(self, extractor, test_case):
        """Tests de falsos positivos."""
        self._run_test(extractor, test_case)

    def _run_test(self, extractor, test_case: NERTestCase):
        """Ejecuta un caso de test."""
        from narrative_assistant.nlp.ner import EntityLabel

        result = extractor.extract_entities(test_case.text)
        assert result.is_success

        ner_result = result.value
        persons = [e.text for e in ner_result.entities if e.label == EntityLabel.PER]

        for expected in test_case.expected_persons:
            found = any(expected.lower() in p.lower() or p.lower() in expected.lower()
                       for p in persons)
            assert found, f"[{test_case.id}] '{expected}' no encontrado en {persons}"


def get_test_summary():
    """Genera resumen de los tests por categoría."""
    from collections import Counter

    categories = Counter(tc.category for tc in ALL_NER_TESTS)
    difficulties = Counter(tc.difficulty for tc in ALL_NER_TESTS)

    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS ADVERSARIALES DE NER")
    print("=" * 60)
    print(f"\nTotal de casos: {len(ALL_NER_TESTS)}")
    print(f"\nPor categoría:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print(f"\nPor dificultad:")
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    get_test_summary()
    pytest.main([__file__, "-v", "--tb=short"])
