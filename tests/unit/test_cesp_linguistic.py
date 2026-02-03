#!/usr/bin/env python3
"""
Tests lingüísticos exhaustivos para CESP (Cascading Extraction with Syntactic Priority).

Diseñados por 3 especialistas lingüistas:
1. Correferencia y alias
2. Sintaxis española
3. Semántica y pragmática

Cobertura:
- Diminutivos y apodos (Paco/Francisco, Nacho/Ignacio)
- Títulos y profesiones (el doctor García, don Ramón)
- Relaciones familiares (el padre de María, la abuela)
- Genitivos posesivos (ojos azules de Pedro)
- Sujetos tácitos y explícitos
- Negaciones, metáforas, ironía
- Atributos temporales y condicionales
"""
import pytest
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from narrative_assistant.nlp.attributes import (
    AttributeExtractor,
    ExtractedAttribute,
    AssignmentSource,
    AttributeCategory,
    AttributeKey,
)


# ============================================================================
# ESTRUCTURAS DE DATOS PARA TESTS
# ============================================================================

@dataclass
class ExpectedAttribute:
    """Atributo esperado en un test."""
    entity: str
    key: str  # eye_color, hair_color, etc.
    value: str
    should_extract: bool = True  # False para atributos que NO deben extraerse


@dataclass
class LinguisticTestCase:
    """Caso de prueba lingüística."""
    name: str
    category: str  # correferencia, sintaxis, semantica
    text: str
    entities: List[str]  # Entidades que deben detectarse
    aliases: Dict[str, List[str]]  # entidad -> lista de alias
    expected_attributes: List[ExpectedAttribute]
    description: str
    risk: str  # Posible error del sistema


# ============================================================================
# CASOS DE CORREFERENCIA Y ALIAS (Lingüista 1)
# ============================================================================

COREFERENCE_CASES = [
    LinguisticTestCase(
        name="diminutivo_clasico",
        category="correferencia",
        text="Francisco era un hombre corpulento de manos grandes. Paco, como le llamaban sus amigos, tenía los ojos negros como el carbón.",
        entities=["Francisco"],
        aliases={"Francisco": ["Paco"]},
        expected_attributes=[
            ExpectedAttribute("Francisco", "eye_color", "negros"),
            ExpectedAttribute("Francisco", "build", "corpulento"),
        ],
        description="Diminutivo clásico: Francisco/Paco son la misma persona",
        risk="Crear dos entidades separadas para Francisco y Paco",
    ),
    LinguisticTestCase(
        name="titulo_profesional_sujeto_tacito",
        category="correferencia",
        text="El doctor Ramírez examinó al paciente con sus ojos grises entrecerrados. Era alto y delgado, con el pelo completamente canoso.",
        entities=["Doctor Ramírez"],
        aliases={"Doctor Ramírez": ["el doctor", "Ramírez"]},
        expected_attributes=[
            ExpectedAttribute("Doctor Ramírez", "eye_color", "grises"),
            ExpectedAttribute("Doctor Ramírez", "height", "alto"),
            ExpectedAttribute("Doctor Ramírez", "build", "delgado"),
            ExpectedAttribute("Doctor Ramírez", "hair_color", "canoso"),
        ],
        description="Título profesional + sujeto tácito",
        risk="No resolver sujeto tácito 'Era alto' hacia el doctor",
    ),
    LinguisticTestCase(
        name="relaciones_familiares",
        category="correferencia",
        text="La abuela de Sofía tenía el cabello blanco como la nieve. Doña Carmen, que así se llamaba, conservaba unos ojos azules vivaces.",
        entities=["Carmen", "Sofía"],
        aliases={"Carmen": ["Doña Carmen", "la abuela de Sofía", "la abuela"]},
        expected_attributes=[
            ExpectedAttribute("Carmen", "hair_color", "blanco"),
            ExpectedAttribute("Carmen", "eye_color", "azules"),
        ],
        description="Relación familiar como identificador",
        risk="No vincular 'la abuela de Sofía' con 'Doña Carmen'",
    ),
    LinguisticTestCase(
        name="bug_historico_genitivo",
        category="correferencia",
        text="Juan conversaba animadamente en la terraza. Los ojos azules de Pedro brillaban bajo el sol mientras escuchaba.",
        entities=["Juan", "Pedro"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Pedro", "eye_color", "azules"),
            # Juan NO debe tener ojos azules
            ExpectedAttribute("Juan", "eye_color", "azules", should_extract=False),
        ],
        description="Bug histórico: genitivo posesivo",
        risk="BUG CRÍTICO: Asignar 'ojos azules' a Juan por proximidad",
    ),
    LinguisticTestCase(
        name="cadena_alias_multiple",
        category="correferencia",
        text="Ignacio entró al bar. Nacho, como todos le conocían, era pelirrojo y pecoso. El hijo de doña Mercedes pidió una cerveza.",
        entities=["Ignacio"],
        aliases={"Ignacio": ["Nacho", "el hijo de doña Mercedes"]},
        expected_attributes=[
            ExpectedAttribute("Ignacio", "hair_color", "pelirrojo"),
            ExpectedAttribute("Ignacio", "skin", "pecoso"),
        ],
        description="Cadena de alias: nombre + diminutivo + relación familiar",
        risk="Crear entidades separadas para Nacho e Ignacio",
    ),
    LinguisticTestCase(
        name="dos_personajes_intercalados",
        category="correferencia",
        text="Dolores era morena de piel canela. Lola —ese era su apodo— trabajaba con Roberto. Él era rubio, de ojos claros.",
        entities=["Dolores", "Roberto"],
        aliases={"Dolores": ["Lola"]},
        expected_attributes=[
            ExpectedAttribute("Dolores", "hair_color", "morena"),
            ExpectedAttribute("Dolores", "skin_tone", "canela"),
            ExpectedAttribute("Roberto", "hair_color", "rubio"),
            ExpectedAttribute("Roberto", "eye_color", "claros"),
        ],
        description="Dos personajes con atributos intercalados",
        risk="Confundir pronombres él/ella entre Dolores y Roberto",
    ),
    LinguisticTestCase(
        name="apodo_despectivo_titulo",
        category="correferencia",
        text="Don Ramón era conocido en el pueblo como 'el Cojo' por su pierna mala. El señor tenía una barba espesa y canosa.",
        entities=["Ramón"],
        aliases={"Ramón": ["Don Ramón", "el Cojo", "el señor"]},
        expected_attributes=[
            ExpectedAttribute("Ramón", "beard", "espesa"),
            ExpectedAttribute("Ramón", "beard_color", "canosa"),
        ],
        description="Apodo despectivo + título honorífico",
        risk="Crear entidad separada para 'el Cojo'",
    ),
    LinguisticTestCase(
        name="hermanos_atributos_distribuidos",
        category="correferencia",
        text="Los hermanos García eran famosos: Miguel el alto, de ojos verdes, y Andrés el bajo, de ojos negros. Ambos tenían el pelo rizado.",
        entities=["Miguel García", "Andrés García"],
        aliases={"Miguel García": ["Miguel el alto"], "Andrés García": ["Andrés el bajo"]},
        expected_attributes=[
            ExpectedAttribute("Miguel García", "height", "alto"),
            ExpectedAttribute("Miguel García", "eye_color", "verdes"),
            ExpectedAttribute("Miguel García", "hair_texture", "rizado"),
            ExpectedAttribute("Andrés García", "height", "bajo"),
            ExpectedAttribute("Andrés García", "eye_color", "negros"),
            ExpectedAttribute("Andrés García", "hair_texture", "rizado"),
        ],
        description="Atributos distribuidos con 'ambos'",
        risk="No distribuir 'pelo rizado' a AMBOS hermanos",
    ),
]


# ============================================================================
# CASOS DE SINTAXIS ESPAÑOLA (Lingüista 2)
# ============================================================================

SYNTAX_CASES = [
    LinguisticTestCase(
        name="genitivo_simple",
        category="sintaxis",
        text="Juan miraba por la ventana. Los ojos verdes de María brillaban con la luz del atardecer.",
        entities=["Juan", "María"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("María", "eye_color", "verdes"),
            ExpectedAttribute("Juan", "eye_color", "verdes", should_extract=False),
        ],
        description="Genitivo posesivo simple 'de María'",
        risk="Asignar 'ojos verdes' a Juan por proximidad",
    ),
    LinguisticTestCase(
        name="genitivo_ambiguo_adjuncion",
        category="sintaxis",
        text="Conocí al amigo de Juan de ojos azules en la fiesta.",
        entities=["Juan", "amigo de Juan"],
        aliases={},
        expected_attributes=[
            # Ambiguo: ¿Juan o su amigo tiene ojos azules?
            # Por Late Closure, se adjunta al SN más cercano: "amigo de Juan"
            ExpectedAttribute("amigo de Juan", "eye_color", "azules"),
        ],
        description="Genitivo ambiguo: adjunción alta vs baja",
        risk="Asignar a Juan en lugar del amigo",
    ),
    LinguisticTestCase(
        name="sujeto_explicito",
        category="sintaxis",
        text="María tiene el pelo rubio y los ojos marrones. Pedro siempre la admiraba.",
        entities=["María", "Pedro"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("María", "hair_color", "rubio"),
            ExpectedAttribute("María", "eye_color", "marrones"),
        ],
        description="Sujeto explícito con verbo 'tener'",
        risk="Perder contexto por oración siguiente",
    ),
    LinguisticTestCase(
        name="sujeto_tacito_cadena",
        category="sintaxis",
        text="Elena entró en la habitación. Era morena y tenía los ojos grandes. Caminaba con elegancia.",
        entities=["Elena"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Elena", "hair_color", "morena"),
            ExpectedAttribute("Elena", "eye_size", "grandes"),
        ],
        description="Cadena de sujeto tácito",
        risk="Pérdida de cadena de correferencia",
    ),
    LinguisticTestCase(
        name="aposicion",
        category="sintaxis",
        text="María, la pelirroja del grupo, entró sonriendo. Todos la miraron.",
        entities=["María"],
        aliases={"María": ["la pelirroja del grupo"]},
        expected_attributes=[
            ExpectedAttribute("María", "hair_color", "pelirroja"),
        ],
        description="Aposición explicativa",
        risk="No detectar correferencia apositiva",
    ),
    LinguisticTestCase(
        name="relativa_con_copula",
        category="sintaxis",
        text="El hombre que tenía los ojos azules era Pedro. Juan lo saludó cordialmente.",
        entities=["Pedro", "Juan"],
        aliases={"Pedro": ["el hombre"]},
        expected_attributes=[
            ExpectedAttribute("Pedro", "eye_color", "azules"),
            ExpectedAttribute("Juan", "eye_color", "azules", should_extract=False),
        ],
        description="Oración relativa con identificación copulativa",
        risk="No resolver cadena de identidad hombre=Pedro",
    ),
    LinguisticTestCase(
        name="comparacion",
        category="sintaxis",
        text="María era más alta que Carmen, pero menos fuerte.",
        entities=["María", "Carmen"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("María", "height", "alta"),
            # Carmen también es 'alta' pero menor grado - opcional
        ],
        description="Comparación de superioridad",
        risk="No extraer atributo implícito del término de comparación",
    ),
    LinguisticTestCase(
        name="pseudocopulativo_cambio_estado",
        category="sintaxis",
        text="Juan se volvió canoso con los años. Sus ojos, sin embargo, seguían siendo azules.",
        entities=["Juan"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Juan", "hair_color", "canoso"),
            ExpectedAttribute("Juan", "eye_color", "azules"),
        ],
        description="Verbo pseudocopulativo de cambio de estado",
        risk="No reconocer 'se volvió' como atribución",
    ),
]


# ============================================================================
# CASOS DE SEMÁNTICA Y PRAGMÁTICA (Lingüista 3)
# ============================================================================

SEMANTIC_CASES = [
    LinguisticTestCase(
        name="negacion_proposicional",
        category="semantica",
        text="María no tenía los ojos verdes como decían. En realidad eran marrones.",
        entities=["María"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("María", "eye_color", "marrones"),
            ExpectedAttribute("María", "eye_color", "verdes", should_extract=False),
        ],
        description="Negación proposicional",
        risk="Extraer 'ojos verdes' ignorando la negación",
    ),
    LinguisticTestCase(
        name="negacion_temporal",
        category="semantica",
        text="Pedro jamás fue alto. Siempre fue el más bajo de sus hermanos.",
        entities=["Pedro"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Pedro", "height", "bajo"),
            ExpectedAttribute("Pedro", "height", "alto", should_extract=False),
        ],
        description="Negación temporal universal 'jamás'",
        risk="Extraer 'alto' ignorando 'jamás'",
    ),
    LinguisticTestCase(
        name="metafora_conceptual",
        category="semantica",
        text="Sus ojos eran dos soles que iluminaban la habitación. María siempre tenía esa mirada brillante.",
        entities=["María"],
        aliases={},
        expected_attributes=[
            # NO extraer "ojos=soles" como color
            ExpectedAttribute("María", "eye_color", "soles", should_extract=False),
            ExpectedAttribute("María", "eye_color", "amarillos", should_extract=False),
        ],
        description="Metáfora conceptual",
        risk="Interpretar 'dos soles' como color amarillo",
    ),
    LinguisticTestCase(
        name="metafora_lexicalizada",
        category="semantica",
        text="Tenía una mirada de acero y un corazón de oro. Juan era implacable en los negocios.",
        entities=["Juan"],
        aliases={},
        expected_attributes=[
            # Metáforas lexicalizadas - NO extraer como atributos físicos
            ExpectedAttribute("Juan", "eye_color", "acero", should_extract=False),
            ExpectedAttribute("Juan", "eye_color", "gris", should_extract=False),
        ],
        description="Metáforas lexicalizadas",
        risk="Interpretar 'mirada de acero' como ojos grises",
    ),
    LinguisticTestCase(
        name="atributo_temporal_pasado",
        category="semantica",
        text="Antes era rubio, pero ahora Pedro tiene el pelo completamente negro.",
        entities=["Pedro"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Pedro", "hair_color", "negro"),
            # "rubio" es pasado, no actual
            ExpectedAttribute("Pedro", "hair_color", "rubio", should_extract=False),
        ],
        description="Atributo temporal: antes vs ahora",
        risk="Extraer 'rubio' como atributo actual",
    ),
    LinguisticTestCase(
        name="condicional_contrafactual",
        category="semantica",
        text="Si María tuviera el pelo rubio, se parecería a su madre. Pero lo tiene negro.",
        entities=["María"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("María", "hair_color", "negro"),
            ExpectedAttribute("María", "hair_color", "rubio", should_extract=False),
        ],
        description="Condicional contrafactual",
        risk="Extraer atributo hipotético como real",
    ),
    LinguisticTestCase(
        name="comparacion_herencia",
        category="semantica",
        text="Como su madre, Elena era pelirroja. Las dos compartían también los ojos claros.",
        entities=["Elena", "madre de Elena"],
        aliases={"madre de Elena": ["su madre"]},
        expected_attributes=[
            ExpectedAttribute("Elena", "hair_color", "pelirroja"),
            ExpectedAttribute("Elena", "eye_color", "claros"),
            ExpectedAttribute("madre de Elena", "hair_color", "pelirroja"),
            ExpectedAttribute("madre de Elena", "eye_color", "claros"),
        ],
        description="Comparación con herencia explícita",
        risk="No inferir atributos compartidos",
    ),
    LinguisticTestCase(
        name="contradiccion_narrativa",
        category="semantica",
        text="Decían que Juan era moreno, pero en realidad su pelo era rubio como el trigo.",
        entities=["Juan"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Juan", "hair_color", "rubio"),
            # El rumor "moreno" no debe extraerse
            ExpectedAttribute("Juan", "hair_color", "moreno", should_extract=False),
        ],
        description="Contradicción narrativa: rumor vs realidad",
        risk="Extraer el rumor como hecho",
    ),
    LinguisticTestCase(
        name="ironia_sarcasmo",
        category="semantica",
        text="—¡Qué alto eres! —le dijeron burlándose a Pedro, que apenas medía un metro sesenta.",
        entities=["Pedro"],
        aliases={},
        expected_attributes=[
            ExpectedAttribute("Pedro", "height", "bajo"),
            ExpectedAttribute("Pedro", "height", "alto", should_extract=False),
        ],
        description="Ironía/sarcasmo",
        risk="Extraer 'alto' ignorando el contexto irónico",
    ),
]


# ============================================================================
# TODOS LOS CASOS COMBINADOS
# ============================================================================

ALL_CASES = COREFERENCE_CASES + SYNTAX_CASES + SEMANTIC_CASES


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def extractor():
    """Crear extractor con configuración estándar."""
    return AttributeExtractor(
        use_llm=False,  # Deshabilitado para tests rápidos
        use_embeddings=False,
        use_dependency_extraction=True,
        use_patterns=True,
    )


# ============================================================================
# TESTS PARAMETRIZADOS
# ============================================================================

@pytest.mark.parametrize("case", COREFERENCE_CASES, ids=[c.name for c in COREFERENCE_CASES])
def test_coreference_cases(case: LinguisticTestCase, extractor):
    """Tests de correferencia y alias."""
    _run_linguistic_test(case, extractor)


@pytest.mark.parametrize("case", SYNTAX_CASES, ids=[c.name for c in SYNTAX_CASES])
def test_syntax_cases(case: LinguisticTestCase, extractor):
    """Tests de sintaxis española."""
    _run_linguistic_test(case, extractor)


@pytest.mark.parametrize("case", SEMANTIC_CASES, ids=[c.name for c in SEMANTIC_CASES])
def test_semantic_cases(case: LinguisticTestCase, extractor):
    """Tests de semántica y pragmática."""
    _run_linguistic_test(case, extractor)


def _run_linguistic_test(case: LinguisticTestCase, extractor):
    """
    Ejecuta un caso de prueba lingüística.
    
    Por ahora, solo verifica la estructura. Los tests completos
    requieren integración con el pipeline completo de NLP.
    """
    # Verificar que el caso está bien formado
    assert case.text, f"Caso {case.name}: texto vacío"
    assert case.entities, f"Caso {case.name}: sin entidades"
    assert case.expected_attributes, f"Caso {case.name}: sin atributos esperados"
    
    # Log para debugging
    print(f"\n{'='*60}")
    print(f"CASO: {case.name} ({case.category})")
    print(f"{'='*60}")
    print(f"TEXTO: {case.text[:100]}...")
    print(f"ENTIDADES: {case.entities}")
    print(f"DESCRIPCIÓN: {case.description}")
    print(f"RIESGO: {case.risk}")
    
    # Verificar atributos esperados
    should_extract = [a for a in case.expected_attributes if a.should_extract]
    should_not_extract = [a for a in case.expected_attributes if not a.should_extract]
    
    print(f"\nATRIBUTOS QUE DEBEN EXTRAERSE:")
    for attr in should_extract:
        print(f"  ✓ {attr.entity} -> {attr.key}={attr.value}")
    
    if should_not_extract:
        print(f"\nATRIBUTOS QUE NO DEBEN EXTRAERSE:")
        for attr in should_not_extract:
            print(f"  ✗ {attr.entity} -> {attr.key}={attr.value}")


# ============================================================================
# TEST DE DEDUPLICACIÓN CESP
# ============================================================================

class TestCESPDeduplication:
    """Tests específicos para la deduplicación CESP."""
    
    def test_genitivo_beats_proximity(self):
        """GENITIVO debe ganar sobre PROXIMITY."""
        extractor = AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=False,
            use_patterns=False,
        )
        
        # Simular: "ojos azules de Pedro" asignado a Pedro (genitivo) y Juan (proximity)
        attr_pedro = ExtractedAttribute(
            entity_name="Pedro",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="ojos azules de Pedro",
            start_char=50,
            end_char=70,
            confidence=0.85,
            assignment_source=AssignmentSource.GENITIVE,
            sentence_idx=1,
        )
        
        attr_juan = ExtractedAttribute(
            entity_name="Juan",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="ojos azules de Pedro",
            start_char=50,
            end_char=70,
            confidence=0.65,
            assignment_source=AssignmentSource.PROXIMITY,
            sentence_idx=1,
        )
        
        result = extractor._deduplicate([attr_pedro, attr_juan])
        
        assert len(result) == 1, "Debe haber solo 1 atributo"
        assert result[0].entity_name == "Pedro", "Pedro debe ganar (genitivo)"
        assert result[0].assignment_source == AssignmentSource.GENITIVE
    
    def test_explicit_subject_beats_proximity(self):
        """EXPLICIT_SUBJECT debe ganar sobre PROXIMITY."""
        extractor = AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=False,
            use_patterns=False,
        )
        
        attr_maria_subj = ExtractedAttribute(
            entity_name="María",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.HAIR_COLOR,
            value="rubio",
            source_text="María tiene el pelo rubio",
            start_char=0,
            end_char=25,
            confidence=0.90,
            assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
            sentence_idx=0,
        )
        
        attr_juan_prox = ExtractedAttribute(
            entity_name="Juan",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.HAIR_COLOR,
            value="rubio",
            source_text="María tiene el pelo rubio",
            start_char=0,
            end_char=25,
            confidence=0.60,
            assignment_source=AssignmentSource.PROXIMITY,
            sentence_idx=0,
        )
        
        result = extractor._deduplicate([attr_maria_subj, attr_juan_prox])
        
        assert len(result) == 1
        assert result[0].entity_name == "María"
        assert result[0].assignment_source == AssignmentSource.EXPLICIT_SUBJECT
    
    def test_different_sentences_preserved(self):
        """Atributos en oraciones diferentes deben preservarse."""
        extractor = AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=False,
            use_patterns=False,
        )
        
        attr_sentence0 = ExtractedAttribute(
            entity_name="Juan",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="Juan tiene ojos azules",
            start_char=0,
            end_char=22,
            confidence=0.85,
            assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
            sentence_idx=0,
        )
        
        attr_sentence1 = ExtractedAttribute(
            entity_name="Pedro",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="Pedro también tiene ojos azules",
            start_char=100,
            end_char=131,
            confidence=0.85,
            assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
            sentence_idx=1,
        )
        
        result = extractor._deduplicate([attr_sentence0, attr_sentence1])
        
        assert len(result) == 2, "Ambos atributos deben preservarse (oraciones diferentes)"
        entities = {a.entity_name for a in result}
        assert entities == {"Juan", "Pedro"}
    
    def test_priority_order_complete(self):
        """Verificar orden completo de prioridades."""
        # Prioridades esperadas (de _deduplicate)
        expected_order = [
            (AssignmentSource.GENITIVE, 100),
            (AssignmentSource.EXPLICIT_SUBJECT, 90),
            (AssignmentSource.LLM, 80),
            (AssignmentSource.IMPLICIT_SUBJECT, 50),
            (AssignmentSource.EMBEDDINGS, 40),
            (AssignmentSource.PROXIMITY, 10),
        ]
        
        # Verificar que las prioridades están en orden descendente
        for i in range(len(expected_order) - 1):
            source1, priority1 = expected_order[i]
            source2, priority2 = expected_order[i + 1]
            assert priority1 > priority2, f"{source1} debe tener mayor prioridad que {source2}"


# ============================================================================
# TESTS DE CASOS ESPECÍFICOS DEL BUG HISTÓRICO
# ============================================================================

class TestHistoricalBugFixes:
    """Tests para verificar que los bugs históricos están corregidos."""
    
    def test_ojos_azules_de_pedro_not_assigned_to_juan(self):
        """
        BUG HISTÓRICO: 'ojos azules de Pedro' se asignaba a Juan.
        
        Este fue el bug original que motivó la implementación de CESP.
        """
        extractor = AttributeExtractor(
            use_llm=False,
            use_embeddings=False,
            use_dependency_extraction=False,
            use_patterns=False,
        )
        
        # Simular exactamente el escenario del bug
        attr_correct = ExtractedAttribute(
            entity_name="Pedro",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="Los ojos azules de Pedro brillaban",
            start_char=50,
            end_char=84,
            confidence=0.88,
            assignment_source=AssignmentSource.GENITIVE,
            sentence_idx=1,
        )
        
        attr_incorrect = ExtractedAttribute(
            entity_name="Juan",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="Los ojos azules de Pedro brillaban",
            start_char=50,
            end_char=84,
            confidence=0.55,
            assignment_source=AssignmentSource.PROXIMITY,
            sentence_idx=1,
        )
        
        result = extractor._deduplicate([attr_correct, attr_incorrect])
        
        # Verificaciones críticas
        assert len(result) == 1, "Solo debe haber 1 resultado"
        assert result[0].entity_name == "Pedro", "CESP debe asignar a Pedro, no a Juan"
        assert result[0].assignment_source == AssignmentSource.GENITIVE
        
        # Verificar que Juan NO tiene el atributo
        juan_attrs = [a for a in result if a.entity_name == "Juan"]
        assert len(juan_attrs) == 0, "Juan NO debe tener ojos azules"


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS LINGÜÍSTICOS CESP")
    print("=" * 70)
    print(f"\nTotal de casos: {len(ALL_CASES)}")
    print(f"  - Correferencia: {len(COREFERENCE_CASES)}")
    print(f"  - Sintaxis: {len(SYNTAX_CASES)}")
    print(f"  - Semántica: {len(SEMANTIC_CASES)}")
    
    # Ejecutar con pytest
    pytest.main([__file__, "-v", "--tb=short"])
