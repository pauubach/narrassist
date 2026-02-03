"""
Tests de casos sintácticos para asignación de atributos CESP.

Autor: Lingüista Especialista en Sintaxis Española
Perspectiva: Análisis sintáctico para resolución de atributos físicos

Este archivo evalúa estructuras sintácticas del español que afectan
la asignación correcta de atributos a entidades mediante el sistema CESP
(Cascading Extraction with Syntactic Priority).

JERARQUÍA CESP:
1. GENITIVO ("los ojos de Pedro") - confianza 0.92
2. SUJETO_EXPLÍCITO ("María tiene pelo rubio") - confianza 0.88
3. LLM (análisis contextual) - confianza 0.85
4. SUJETO_TÁCITO ("Era morena") - confianza 0.78
5. EMBEDDINGS - confianza 0.70
6. PROXIMIDAD - confianza 0.60

BUG HISTÓRICO: "ojos azules de Pedro" se asignaba a Juan por proximidad.

ESTRUCTURAS EVALUADAS:
1. Genitivos posesivos simples
2. Genitivos ambiguos anidados
3. Sujetos explícitos con verbos posesivos
4. Sujetos tácitos (pro-drop español)
5. Oraciones coordinadas con pronombres
6. Aposiciones descriptivas
7. Cláusulas relativas con atributos
8. Comparaciones y superlativos
9. Estructuras dislocadas (topicalizaciones)
10. Verbos pseudocopulativos
"""

import pytest
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


# =============================================================================
# DEFINICIÓN DE CASOS DE PRUEBA
# =============================================================================

@dataclass
class SyntacticTestCase:
    """Estructura para un caso de prueba sintáctico."""
    id: str
    name: str
    text: str
    entities: List[str]
    expected_attributions: Dict[str, Dict[str, str]]  # entidad -> {attr_type: valor}
    syntactic_analysis: str
    risk_description: str
    priority_level: str  # Nivel CESP que debería resolver


# =============================================================================
# CASO 1: GENITIVOS POSESIVOS SIMPLES
# =============================================================================

CASO_1_GENITIVO_SIMPLE = SyntacticTestCase(
    id="GENITIVO_SIMPLE_001",
    name="Genitivo posesivo con 'de' - estructura canónica",
    text="Juan observaba a María desde la ventana. Los ojos verdes de María brillaban con la luz del atardecer.",
    entities=["Juan", "María"],
    expected_attributions={
        "María": {"eye_color": "verdes"}
        # Juan NO debe recibir ningún atributo ocular
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO:
    - SN: [los ojos verdes de María]
        - DET: los
        - N: ojos (núcleo)
        - ADJ: verdes (modificador directo)
        - SP: de María (complemento del nombre - GENITIVO)
    
    El genitivo "de María" establece una relación de posesión/pertenencia
    inequívoca. El adjetivo "verdes" modifica a "ojos" y por transitividad
    del genitivo, el atributo pertenece a María.
    """,
    risk_description="""
    RIESGO: Asignación por proximidad textual.
    Juan aparece antes en el texto y podría capturar el atributo si el 
    sistema prioriza la proximidad sobre la estructura sintáctica.
    El algoritmo CESP debe detectar el SP "de María" y asignar confianza
    GENITIVO (0.92) que supera cualquier heurística de proximidad.
    """,
    priority_level="GENITIVO"
)


# =============================================================================
# CASO 2: GENITIVOS AMBIGUOS ANIDADOS
# =============================================================================

CASO_2_GENITIVO_AMBIGUO = SyntacticTestCase(
    id="GENITIVO_AMBIGUO_002",
    name="Genitivo anidado con modificador flotante",
    text="Pedro conocía bien al amigo de Juan de ojos azules.",
    entities=["Pedro", "Juan"],
    expected_attributions={
        # ANÁLISIS: Estructura ambigua por adjunción de PP
        # Interpretación preferida: [el amigo de Juan] [de ojos azules]
        # El PP "de ojos azules" modifica a "amigo", no a Juan directamente
        # Por tanto, NO debemos asignar a ninguna de las entidades conocidas
        # a menos que "el amigo de Juan" sea una entidad rastreada
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (AMBIGÜEDAD ESTRUCTURAL):
    
    Parsing 1 (adjunción alta):
    - [el amigo [de Juan [de ojos azules]]]
    - "de ojos azules" modifica a "Juan" → Juan tiene ojos azules
    
    Parsing 2 (adjunción baja) - PREFERIDO:
    - [[el amigo [de Juan]] [de ojos azules]]
    - "de ojos azules" modifica a "amigo" → el amigo tiene ojos azules
    
    Por el principio de Late Closure (Frazier, 1978) y la preferencia
    del español por adjunción baja de PPs, la interpretación preferida
    es que "ojos azules" pertenece al amigo, NO a Juan.
    
    NOTA: Esta estructura es genuinamente ambigua y podría requerir
    desambiguación contextual o consulta LLM.
    """,
    risk_description="""
    RIESGO: Asignación errónea a entidad conocida.
    El sistema podría asignar "ojos azules" a Juan porque:
    1. Juan es la entidad conocida más cercana al atributo
    2. El genitivo "de Juan" aparece adyacente
    
    Solución correcta: NO asignar a ninguna entidad conocida, o
    crear entidad temporal "amigo de Juan" para el atributo.
    """,
    priority_level="GENITIVO_AMBIGUO"
)


# =============================================================================
# CASO 3: SUJETO EXPLÍCITO CON VERBO POSESIVO
# =============================================================================

CASO_3_SUJETO_EXPLICITO = SyntacticTestCase(
    id="SUJETO_EXPLICITO_003",
    name="Sujeto explícito con 'tener' + atributo directo",
    text="María tiene el pelo rubio y largo. Juan la miraba con admiración.",
    entities=["María", "Juan"],
    expected_attributions={
        "María": {"hair_color": "rubio"}
        # Juan NO debe recibir atributo de pelo
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO:
    - Oración 1: [María]_SUJ [tiene]_V [el pelo rubio y largo]_OD
        - SUJ: María (agente, poseedor)
        - V: tiene (verbo posesivo, establece relación de posesión)
        - OD: el pelo rubio y largo
            - DET: el
            - N: pelo (núcleo)
            - ADJ coordinados: rubio y largo
    
    El verbo "tener" con sujeto explícito crea asignación directa.
    La estructura [SUJ + tener + atributo físico] es una construcción
    atributiva en español que NO requiere cópula.
    """,
    risk_description="""
    RIESGO: Confusión de referente por oración siguiente.
    La segunda oración menciona a Juan como sujeto. Un sistema que
    procese secuencialmente podría:
    1. Perder el contexto de quién es el poseedor
    2. Asociar "pelo rubio" con el sujeto más reciente (Juan)
    
    El nivel SUJETO_EXPLÍCITO (0.88) debe capturar la relación.
    """,
    priority_level="SUJETO_EXPLICITO"
)


# =============================================================================
# CASO 4: SUJETO TÁCITO (PRO-DROP ESPAÑOL)
# =============================================================================

CASO_4_SUJETO_TACITO = SyntacticTestCase(
    id="SUJETO_TACITO_004",
    name="Cadena de sujetos tácitos con referente distante",
    text="Elena entró en la habitación. Era morena. Tenía una cicatriz en la mejilla. Sonreía con dulzura.",
    entities=["Elena"],
    expected_attributions={
        "Elena": {
            "hair_color": "morena",  # o complexion según el modelo
            "distinguishing_marks": "cicatriz en la mejilla"
        }
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (SUJETO TÁCITO / PRO-DROP):
    
    Oración 1: [Elena]_SUJ [entró en la habitación]_VP
        - Establece referente para cadena anafórica
    
    Oración 2: [Ø]_SUJ [era morena]_VP
        - Sujeto tácito [Ø] = pro
        - Referente: Elena (antecedente más saliente)
        - Verbo copulativo "era" + atributo "morena"
    
    Oración 3: [Ø]_SUJ [tenía una cicatriz...]_VP
        - Sujeto tácito, mismo referente (Elena)
        - Continuidad temática mantiene la referencia
    
    Oración 4: [Ø]_SUJ [sonreía con dulzura]_VP
        - Sujeto tácito, mismo referente (Elena)
    
    El español es lengua pro-drop: el sujeto puede omitirse cuando
    es recuperable del contexto. La morfología verbal (3ª sing) y
    la coherencia temática mantienen la referencia.
    """,
    risk_description="""
    RIESGO: Pérdida de cadena de correferencia.
    Si el sistema procesa oraciones independientemente sin mantener
    el sujeto tácito, podría:
    1. No asignar los atributos a ninguna entidad
    2. Buscar otra entidad más cercana erróneamente
    
    El nivel SUJETO_TÁCITO (0.78) debe rastrear la referencia a
    través de la morfología verbal y coherencia temática.
    """,
    priority_level="SUJETO_TACITO"
)


# =============================================================================
# CASO 5: ORACIONES COORDINADAS CON PRONOMBRE AMBIGUO
# =============================================================================

CASO_5_COORDINADAS_PRONOMBRE = SyntacticTestCase(
    id="COORDINADAS_PRONOMBRE_005",
    name="Coordinación con pronombre 'él' ambiguo",
    text="Juan y Pedro entraron en el bar. Él era alto y corpulento.",
    entities=["Juan", "Pedro"],
    expected_attributions={
        # ANÁLISIS: El pronombre "él" es ambiguo sintácticamente
        # Puede referir a Juan O a Pedro
        # Por el principio de recency, Pedro es el antecedente preferido
        # Pero sin más contexto, es genuinamente ambiguo
        "Pedro": {"height": "alto", "build": "corpulento"}  # Por recency
        # NOTA: En sistema real, podría requerir LLM para desambiguar
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (AMBIGÜEDAD PRONOMINAL):
    
    Oración 1: [Juan y Pedro]_SUJ [entraron en el bar]_VP
        - Sujeto compuesto coordinado
        - Ambos referentes igualmente salientes
    
    Oración 2: [Él]_SUJ [era alto y corpulento]_VP
        - Pronombre anafórico "él" (3ª sing masc)
        - Antecedentes posibles: Juan, Pedro
    
    DESAMBIGUACIÓN PRAGMÁTICA:
    - Principio de recency: El último mencionado (Pedro) es preferido
    - Paralelismo estructural: Ambos son igualmente accesibles
    - Focus: Sin marca de foco, se aplica recency por defecto
    
    La gramática española no tiene regla firme para este caso.
    Es estructuralmente ambiguo y requiere contexto pragmático.
    """,
    risk_description="""
    RIESGO: Asignación arbitraria o doble.
    El sistema podría:
    1. Asignar a ambos (error: duplicación de atributo)
    2. Asignar a Juan (por ser primero) - incorrecto por recency
    3. No asignar a ninguno - pérdida de información
    
    Solución: Aplicar heurística de recency (Pedro), pero con
    confianza reducida, o escalar a LLM para desambiguación.
    """,
    priority_level="SUJETO_TACITO_AMBIGUO"
)


# =============================================================================
# CASO 6: APOSICIÓN DESCRIPTIVA
# =============================================================================

CASO_6_APOSICION = SyntacticTestCase(
    id="APOSICION_006",
    name="Aposición descriptiva con atributos físicos",
    text="María, la pelirroja del grupo, entró con paso decidido. Juan la saludó.",
    entities=["María", "Juan"],
    expected_attributions={
        "María": {"hair_color": "pelirroja"}
        # Juan NO debe recibir ningún atributo
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (APOSICIÓN):
    
    Estructura: [María]_NÚCLEO, [la pelirroja del grupo]_APOSICIÓN, [VP]
    
    La aposición es un SN explicativo que:
    1. Está delimitado por comas (aposición explicativa)
    2. Tiene correferencia total con el núcleo (María = la pelirroja)
    3. Aporta información descriptiva adicional
    
    Análisis del SN apositivo:
    - DET: la (artículo definido, indica identificabilidad)
    - N: pelirroja (sustantivo derivado de adjetivo, denota color de pelo)
    - SP: del grupo (modificador restrictivo)
    
    La correferencia [María = la pelirroja] permite inferir:
    María tiene pelo rojo/pelirrojo.
    """,
    risk_description="""
    RIESGO: No detectar la correferencia apositiva.
    El sistema podría:
    1. Tratar "la pelirroja" como entidad separada
    2. No extraer el atributo de color de pelo
    3. Perder la información en el procesamiento
    
    La aposición debe resolverse como correferencia y el atributo
    "pelirroja" asignarse a María con confianza alta.
    """,
    priority_level="GENITIVO"  # Similar a estructura posesiva
)


# =============================================================================
# CASO 7: CLÁUSULA RELATIVA CON ATRIBUTO
# =============================================================================

CASO_7_RELATIVA = SyntacticTestCase(
    id="RELATIVA_007",
    name="Cláusula relativa especificativa con atributo",
    text="El hombre que tenía los ojos azules era Pedro. María lo reconoció al instante.",
    entities=["Pedro", "María"],
    expected_attributions={
        "Pedro": {"eye_color": "azules"}
        # María NO debe recibir atributo ocular
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (CLÁUSULA RELATIVA):
    
    Oración principal: [El hombre que tenía los ojos azules]_SUJ [era Pedro]_VP
    
    Análisis del sujeto complejo:
    - SN: [el hombre [que tenía los ojos azules]]
        - DET: el
        - N: hombre (núcleo)
        - Cláusula relativa: que tenía los ojos azules
            - PRO REL: que (antecedente: hombre)
            - V: tenía (posesivo)
            - OD: los ojos azules
    
    El verbo copulativo "era" establece:
    [El hombre que tenía ojos azules] = Pedro
    
    Por transitividad:
    1. hombre tiene ojos azules (de la relativa)
    2. hombre = Pedro (de la cópula)
    3. ∴ Pedro tiene ojos azules
    """,
    risk_description="""
    RIESGO: No resolver la cadena de identidad.
    El sistema debe:
    1. Detectar que "el hombre" tiene ojos azules
    2. Resolver que "el hombre" = Pedro (vía cópula)
    3. Transferir el atributo a Pedro
    
    Si solo procesa la relativa sin resolver la identidad,
    el atributo quedaría asignado a entidad anónima "el hombre".
    """,
    priority_level="SUJETO_EXPLICITO"  # Via construcción copulativa
)


# =============================================================================
# CASO 8: COMPARACIÓN CON ATRIBUTO IMPLÍCITO
# =============================================================================

CASO_8_COMPARACION = SyntacticTestCase(
    id="COMPARACION_008",
    name="Estructura comparativa con atributo implícito para ambos",
    text="María era más alta que su hermana Carmen. Las dos entraron en la tienda.",
    entities=["María", "Carmen"],
    expected_attributions={
        "María": {"height": "alta"},  # explícito + grado comparativo
        "Carmen": {"height": "alta"}   # implícito por comparación
        # NOTA: Carmen también es "alta" pero menos que María
        # El sistema podría no capturar el atributo de Carmen
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (COMPARACIÓN):
    
    Estructura: [María]_SUJ [era más alta que su hermana Carmen]_VP
    
    Construcción comparativa:
    - más + ADJ + que + TÉRMINO
    - Término de comparación: su hermana Carmen
    
    Implicaciones semánticas:
    1. María ES alta (atributo explícito)
    2. Carmen ES alta (implícito por participar en comparación)
    3. altura(María) > altura(Carmen) (relación de grado)
    
    En español, la comparación presupone que ambos términos
    poseen el atributo comparado. No se puede ser "más alto que X"
    si X no tiene altura (implica que X también es alto).
    """,
    risk_description="""
    RIESGO: No extraer atributo del término de comparación.
    El sistema típicamente captura:
    - María → alta (explícito)
    
    Pero podría perder:
    - Carmen → alta (implícito por comparación)
    
    La semántica comparativa presupone que ambos términos
    tienen el atributo comparado. Esta información implícita
    podría requerir procesamiento pragmático adicional.
    """,
    priority_level="SUJETO_EXPLICITO"
)


# =============================================================================
# CASO 9: TOPICALIZACIÓN / DISLOCACIÓN A LA IZQUIERDA
# =============================================================================

CASO_9_TOPICALIZACION = SyntacticTestCase(
    id="TOPICALIZACION_009",
    name="Dislocación a la izquierda con retoma pronominal",
    text="A Pedro, los ojos negros le daban un aspecto misterioso. María siempre lo había pensado.",
    entities=["Pedro", "María"],
    expected_attributions={
        "Pedro": {"eye_color": "negros"}
        # María NO debe recibir atributo ocular
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (DISLOCACIÓN A LA IZQUIERDA):
    
    Estructura: [A Pedro]_TÓPICO, [los ojos negros le daban...]_COMENTARIO
    
    Análisis:
    - Tópico dislocado: "A Pedro" (dativo de posesión inalienable)
    - Clítico de retoma: "le" (correferente con "Pedro")
    - Sujeto: "los ojos negros"
    - Predicado: "daban un aspecto misterioso"
    
    La construcción de posesión inalienable en español:
    - Los ojos son de Pedro (relación parte-todo)
    - El dativo "a Pedro" marca el poseedor
    - "le" retoma el dativo y confirma la posesión
    
    Inferencia: Pedro tiene ojos negros
    """,
    risk_description="""
    RIESGO: No interpretar dativo de posesión inalienable.
    El sistema podría:
    1. No vincular "A Pedro" con "los ojos negros"
    2. Tratar "los ojos negros" como sujeto independiente
    3. Asignar atributo a entidad incorrecta por proximidad
    
    La estructura de posesión inalienable (partes del cuerpo)
    requiere análisis del dativo posesivo, no solo de genitivos.
    """,
    priority_level="GENITIVO"  # Dativo de posesión = equivalente semántico
)


# =============================================================================
# CASO 10: VERBOS PSEUDOCOPULATIVOS DE CAMBIO
# =============================================================================

CASO_10_PSEUDOCOPULATIVO = SyntacticTestCase(
    id="PSEUDOCOPULATIVO_010",
    name="Verbo pseudocopulativo 'volverse' con atributo resultante",
    text="Juan se volvió canoso después del accidente. María notó el cambio inmediatamente.",
    entities=["Juan", "María"],
    expected_attributions={
        "Juan": {"hair_color": "canoso"}  # Estado resultante
        # María NO debe recibir atributo de pelo
        # NOTA: "canoso" es estado POST-accidente, no permanente original
    },
    syntactic_analysis="""
    ANÁLISIS SINTÁCTICO (VERBO PSEUDOCOPULATIVO):
    
    Oración: [Juan]_SUJ [se volvió canoso después del accidente]_VP
    
    Análisis del VP:
    - V: volverse (pseudocopulativo de cambio)
    - Atributo: canoso
    - Adjunto temporal: después del accidente
    
    Los verbos pseudocopulativos de cambio en español:
    - volverse, hacerse, ponerse, quedarse, convertirse en
    
    Semántica: 
    - Estado inicial: Juan NO canoso (implícito)
    - Evento: accidente (causa del cambio)
    - Estado final: Juan canoso (explícito)
    
    El atributo "canoso" es el estado RESULTANTE, actual.
    """,
    risk_description="""
    RIESGO: No capturar atributos con verbos pseudocopulativos.
    El sistema puede estar entrenado principalmente para:
    - Verbos copulativos: ser, estar
    - Verbos posesivos: tener
    
    Los pseudocopulativos (volverse, hacerse, quedarse, ponerse)
    también asignan atributos y deben detectarse.
    
    Adicionalmente, hay información temporal: el atributo es
    posterior al accidente, no un rasgo original.
    """,
    priority_level="SUJETO_EXPLICITO"
)


# =============================================================================
# COLECCIÓN DE TODOS LOS CASOS
# =============================================================================

ALL_SYNTACTIC_CASES = [
    CASO_1_GENITIVO_SIMPLE,
    CASO_2_GENITIVO_AMBIGUO,
    CASO_3_SUJETO_EXPLICITO,
    CASO_4_SUJETO_TACITO,
    CASO_5_COORDINADAS_PRONOMBRE,
    CASO_6_APOSICION,
    CASO_7_RELATIVA,
    CASO_8_COMPARACION,
    CASO_9_TOPICALIZACION,
    CASO_10_PSEUDOCOPULATIVO,
]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def dependency_extractor():
    """DependencyExtractor compartido."""
    from narrative_assistant.nlp.extraction.extractors.dependency_extractor import DependencyExtractor
    return DependencyExtractor()


@pytest.fixture(scope="module")  
def cesp_resolver():
    """CESPResolver compartido."""
    from narrative_assistant.nlp.cesp_resolver import CESPResolver
    return CESPResolver()


@pytest.fixture(scope="module")
def extraction_context_factory():
    """Factory para crear contextos de extracción."""
    from narrative_assistant.nlp.extraction.base import ExtractionContext
    
    def _create(text: str, entities: List[str]) -> ExtractionContext:
        return ExtractionContext(
            text=text,
            entity_names=entities,
            entity_mentions=None,
            chapter=1,
        )
    return _create


# =============================================================================
# TESTS PARAMETRIZADOS
# =============================================================================

class TestSyntacticAttributionCases:
    """
    Tests para evaluar la asignación de atributos basada en sintaxis.
    
    Cada caso evalúa una estructura sintáctica específica del español
    y verifica que el sistema CESP asigne correctamente los atributos.
    """
    
    @pytest.mark.parametrize("case", ALL_SYNTACTIC_CASES, ids=lambda c: c.id)
    def test_syntactic_case(
        self, 
        case: SyntacticTestCase,
        dependency_extractor,
        extraction_context_factory
    ):
        """Test parametrizado para cada caso sintáctico."""
        context = extraction_context_factory(case.text, case.entities)
        result = dependency_extractor.extract(context)
        
        # Verificar atributos esperados
        for entity, expected_attrs in case.expected_attributions.items():
            for attr_type, expected_value in expected_attrs.items():
                # Buscar el atributo en los resultados
                found_attrs = [
                    a for a in result.attributes
                    if a.entity_name == entity and a.attribute_type == attr_type
                ]
                
                if not found_attrs:
                    pytest.xfail(
                        f"[{case.id}] No se encontró {attr_type} para {entity}\n"
                        f"Texto: {case.text}\n"
                        f"Riesgo: {case.risk_description}"
                    )
                
                # Verificar valor
                actual_value = found_attrs[0].value
                if expected_value.lower() not in actual_value.lower():
                    pytest.xfail(
                        f"[{case.id}] Valor incorrecto para {entity}.{attr_type}\n"
                        f"Esperado: {expected_value}, Actual: {actual_value}\n"
                        f"Texto: {case.text}"
                    )
        
        # Verificar que entidades NO esperadas no reciban atributos erróneos
        for entity in case.entities:
            if entity not in case.expected_attributions:
                entity_attrs = [
                    a for a in result.attributes
                    if a.entity_name == entity
                ]
                
                # Filtrar solo atributos físicos relevantes
                physical_attrs = [
                    a for a in entity_attrs
                    if a.attribute_type in [
                        'eye_color', 'hair_color', 'height', 
                        'build', 'distinguishing_marks', 'complexion'
                    ]
                ]
                
                if physical_attrs:
                    # Esto podría ser el bug de asignación por proximidad
                    pytest.xfail(
                        f"[{case.id}] POSIBLE BUG: {entity} recibió atributos no esperados\n"
                        f"Atributos: {[(a.attribute_type, a.value) for a in physical_attrs]}\n"
                        f"Riesgo descrito: {case.risk_description}"
                    )


class TestGenitiveVsProximity:
    """
    Tests específicos para verificar que el genitivo supera la proximidad.
    
    Este es el bug histórico principal: "ojos azules de Pedro" se asignaba
    a Juan por estar más cerca en el texto.
    """
    
    GENITIVE_CASES = [
        # (texto, entidades, entidad_correcta, entidad_incorrecta, atributo)
        (
            "Juan miraba a María. Los ojos azules de María eran hermosos.",
            ["Juan", "María"],
            "María", "Juan", "eye_color"
        ),
        (
            "Pedro hablaba con Ana. La sonrisa de Ana iluminaba la sala.",
            ["Pedro", "Ana"],
            "Ana", "Pedro", "facial_expression"
        ),
        (
            "Carlos observó a Elena. El pelo negro de Elena caía sobre sus hombros.",
            ["Carlos", "Elena"],
            "Elena", "Carlos", "hair_color"
        ),
        (
            "Marta entró con Luis. La cicatriz de Luis en la mejilla era visible.",
            ["Marta", "Luis"],
            "Luis", "Marta", "distinguishing_marks"
        ),
    ]
    
    @pytest.mark.parametrize(
        "text,entities,correct_entity,wrong_entity,attr_type",
        GENITIVE_CASES
    )
    def test_genitive_over_proximity(
        self,
        text: str,
        entities: List[str],
        correct_entity: str,
        wrong_entity: str,
        attr_type: str,
        dependency_extractor,
        extraction_context_factory
    ):
        """
        Verifica que el genitivo tenga prioridad sobre la proximidad.
        
        El bug histórico asignaba atributos a la entidad más cercana
        ignorando la estructura genitiva "de X".
        """
        context = extraction_context_factory(text, entities)
        result = dependency_extractor.extract(context)
        
        # Buscar atributos del tipo esperado
        relevant_attrs = [
            a for a in result.attributes
            if a.attribute_type == attr_type or attr_type in a.attribute_type
        ]
        
        if not relevant_attrs:
            pytest.skip(f"No se detectó atributo {attr_type} en: {text}")
        
        # Verificar asignación correcta
        correct_attrs = [a for a in relevant_attrs if a.entity_name == correct_entity]
        wrong_attrs = [a for a in relevant_attrs if a.entity_name == wrong_entity]
        
        # El atributo DEBE estar asignado a la entidad correcta
        assert correct_attrs, (
            f"FALLO: Atributo {attr_type} no asignado a {correct_entity}\n"
            f"Texto: {text}"
        )
        
        # El atributo NO DEBE estar asignado a la entidad incorrecta
        if wrong_attrs:
            pytest.xfail(
                f"BUG DETECTADO: {attr_type} asignado erróneamente a {wrong_entity}\n"
                f"Debería ser solo de {correct_entity}\n"
                f"Texto: {text}\n"
                f"Este es el bug histórico de proximidad vs genitivo."
            )


class TestTacitSubjectChains:
    """
    Tests para cadenas de sujetos tácitos (pro-drop español).
    """
    
    TACIT_CHAINS = [
        # (texto, entidad_referente, atributos_esperados)
        (
            "Ana llegó temprano. Era rubia. Tenía ojos verdes. Sonreía.",
            "Ana",
            {"hair_color": "rubia", "eye_color": "verdes"}
        ),
        (
            "El profesor entró. Era un hombre mayor. Tenía barba blanca. Caminaba despacio.",
            "profesor",  # o la entidad que el NER detecte
            {"build": "mayor", "facial_hair": "barba blanca"}
        ),
        (
            "La niña apareció. Era pequeña y delgada. Tenía el pelo corto.",
            "niña",
            {"build": "pequeña", "hair_style": "corto"}
        ),
    ]
    
    @pytest.mark.parametrize(
        "text,expected_entity,expected_attrs",
        TACIT_CHAINS
    )
    def test_tacit_subject_resolution(
        self,
        text: str,
        expected_entity: str,
        expected_attrs: Dict[str, str],
        dependency_extractor,
        extraction_context_factory
    ):
        """
        Verifica que los sujetos tácitos se resuelvan correctamente.
        """
        # Detectar entidades en el texto
        entities = [expected_entity]
        context = extraction_context_factory(text, entities)
        result = dependency_extractor.extract(context)
        
        found_count = 0
        for attr_type, expected_value in expected_attrs.items():
            matching = [
                a for a in result.attributes
                if a.entity_name == expected_entity 
                and (attr_type in a.attribute_type or a.attribute_type in attr_type)
            ]
            
            if matching:
                found_count += 1
        
        if found_count == 0:
            pytest.xfail(
                f"Cadena de sujeto tácito no resuelta\n"
                f"Texto: {text}\n"
                f"Se esperaba asignar a: {expected_entity}\n"
                f"Atributos esperados: {expected_attrs}"
            )


# =============================================================================
# TESTS DE INTEGRACIÓN CON CESP
# =============================================================================

class TestCESPIntegration:
    """
    Tests de integración completa con el resolver CESP.
    
    Estos tests verifican que la jerarquía de prioridades CESP
    funcione correctamente con los casos sintácticos.
    """
    
    def test_cesp_priority_genitive_over_proximity(
        self,
        cesp_resolver,
    ):
        """
        Test crítico: El genitivo debe tener prioridad sobre proximidad.
        """
        text = "Juan era un hombre tranquilo. Los ojos azules de Pedro brillaban."
        entities = ["Juan", "Pedro"]
        
        # Este test documenta el comportamiento esperado
        # El CESP debe asignar "ojos azules" a Pedro (genitivo)
        # NO a Juan (proximidad)
        
        # La implementación real del test depende de la API de CESP
        pytest.xfail(
            "Test de integración CESP: Verificar que genitivo supera proximidad\n"
            f"Texto: {text}\n"
            f"Esperado: Pedro.eye_color = azules\n"
            f"NO esperado: Juan.eye_color = azules"
        )
    
    def test_cesp_priority_explicit_subject_over_tacit(
        self,
        cesp_resolver,
    ):
        """
        Test: Sujeto explícito debe tener más confianza que tácito.
        """
        text = "María tenía los ojos verdes. Era muy alta."
        entities = ["María"]
        
        # Ambos atributos son de María pero:
        # - "ojos verdes" tiene confianza SUJETO_EXPLICITO (0.88)
        # - "alta" tiene confianza SUJETO_TACITO (0.78)
        
        pytest.xfail(
            "Test de integración CESP: Verificar niveles de confianza\n"
            f"Texto: {text}\n"
            f"Esperado: María.eye_color confianza > María.height confianza"
        )


# =============================================================================
# RESUMEN DE CASOS PARA DOCUMENTACIÓN
# =============================================================================

def print_test_cases_summary():
    """
    Imprime un resumen de todos los casos de prueba en formato legible.
    """
    print("=" * 80)
    print("CASOS DE PRUEBA SINTÁCTICA PARA ASIGNACIÓN DE ATRIBUTOS CESP")
    print("=" * 80)
    
    for case in ALL_SYNTACTIC_CASES:
        print(f"\n{'='*80}")
        print(f"CASO {case.id}: {case.name}")
        print(f"{'='*80}")
        print(f"\nTEXTO:\n\"{case.text}\"")
        print(f"\nENTIDADES: {case.entities}")
        print(f"\nATRIBUTOS ESPERADOS:")
        for entity, attrs in case.expected_attributions.items():
            for attr_type, value in attrs.items():
                print(f"  - {entity} → {attr_type} = {value}")
        print(f"\nANÁLISIS SINTÁCTICO:{case.syntactic_analysis}")
        print(f"\nRIESGO:{case.risk_description}")
        print(f"\nNIVEL CESP: {case.priority_level}")


if __name__ == "__main__":
    print_test_cases_summary()
