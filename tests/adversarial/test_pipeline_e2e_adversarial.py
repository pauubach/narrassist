"""
Tests adversariales end-to-end para el pipeline completo NER → Atributos → Fusión.

A diferencia de los tests unitarios adversariales (que testean un módulo aislado),
estos tests ejecutan el pipeline COMPLETO como lo haría un usuario real:
1. Texto → NER (detectar entidades)
2. Entidades → Atributos (extraer atributos)
3. Entidades → Fusión (deduplicar entidades)
4. Verificar resultado final integrado

Estos tests replican escenarios REALES encontrados en producción donde
errores en una etapa se propagan a las siguientes.

Inspirado en el bug real donde:
- NER clasificó "María Sánchez" como MISC (→ CONCEPT)
- Attribute extractor asignó atributos de María a Juan por proximidad
- Fusión no unificó "María Sánchez" con "María" por tipo incompatible

Autor: GAN-style Adversary Agent
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# TEST DATA STRUCTURES
# =============================================================================

@dataclass
class PipelineTestCase:
    """Caso de test end-to-end para el pipeline completo."""
    id: str
    category: str
    text: str
    # Expected entities after NER + fusion
    expected_entities: dict[str, str]  # {canonical_name: expected_type}
    # Expected attributes per entity
    expected_attributes: dict[str, dict[str, str]]  # {entity_name: {key: value}}
    # Entities that should be fused into one
    expected_fusions: list[list[str]]  # [[name1, name2], ...] - groups that should merge
    # Entities that should NOT exist as separate
    forbidden_entities: list[str] = field(default_factory=list)
    # Attributes that should NOT be assigned to these entities
    forbidden_attributes: dict[str, list[str]] = field(default_factory=dict)
    difficulty: str = "medium"
    description: str = ""


# =============================================================================
# PIPELINE TEST CASES
# =============================================================================

PIPELINE_CASES = [
    # -------------------------------------------------------------------------
    # 1. REAL BUG REPLICAS - Casos extraídos de errores en producción
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_real_01_maria_juan",
        category="bug_real",
        text=(
            "María Sánchez caminaba por el parque central. Tenía el pelo "
            "castaño y los ojos marrones. Era alta y delgada, de unos "
            "treinta y cinco años.\n\n"
            "Juan Pérez la saludó desde un banco cercano. Era bajo y "
            "robusto, con el pelo canoso y barba descuidada."
        ),
        expected_entities={
            "María Sánchez": "character",
            "Juan Pérez": "character",
        },
        expected_attributes={
            "María Sánchez": {
                "hair_color": "castaño",
                "eye_color": "marrones",
                "height": "alta",
                "age": "treinta y cinco",
            },
            "Juan Pérez": {
                "height": "bajo",
                "hair_color": "canoso",
            },
        },
        expected_fusions=[],
        forbidden_attributes={
            "Juan Pérez": ["eye_color"],  # Bug: Juan recibía ojos marrones de María
        },
        difficulty="adversarial",
        description=(
            "REPLICA BUG REAL: María clasificada como CONCEPT, todos sus "
            "atributos asignados a Juan por proximidad."
        ),
    ),

    PipelineTestCase(
        id="e2e_real_02_maria_fusion",
        category="bug_real",
        text=(
            "María entró en la sala. Llevaba un vestido azul que resaltaba "
            "sus ojos verdes.\n\n"
            "—Buenos días, María Sánchez —dijo el director.\n\n"
            "María Sánchez se sentó en la primera fila. Su pelo negro "
            "contrastaba con su piel clara."
        ),
        expected_entities={
            "María Sánchez": "character",
        },
        expected_attributes={
            "María Sánchez": {
                "eye_color": "verdes",
                "hair_color": "negro",
            },
        },
        expected_fusions=[
            ["María", "María Sánchez"],  # Should merge into one entity
        ],
        forbidden_entities=["María"],  # After fusion, only María Sánchez should exist
        difficulty="adversarial",
        description=(
            "REPLICA BUG REAL: 'María' y 'María Sánchez' deberían fusionarse. "
            "Atributos de ambas menciones van a la entidad fusionada."
        ),
    ),

    PipelineTestCase(
        id="e2e_real_03_no_alerts",
        category="bug_real",
        text=(
            "En el capítulo uno, Pedro tenía los ojos azules y el pelo rubio.\n\n"
            "En el capítulo tres, Pedro miraba con sus ojos verdes por la ventana. "
            "Su cabello oscuro le caía sobre la frente."
        ),
        expected_entities={
            "Pedro": "character",
        },
        expected_attributes={
            "Pedro": {
                "eye_color": "azules",  # First mention wins (inconsistency detected)
            },
        },
        expected_fusions=[],
        difficulty="hard",
        description=(
            "Inconsistencia de atributos: ojos azules→verdes, pelo rubio→oscuro. "
            "El pipeline debe detectar estos conflictos como alertas."
        ),
    ),

    # -------------------------------------------------------------------------
    # 2. MULTI-CHARACTER SCENES - Escenas con múltiples personajes
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_multi_01_three_chars",
        category="multi_personaje",
        text=(
            "Alberto era el más alto de los tres hermanos, con ojos azules "
            "heredados de su padre. Mónica, la mediana, tenía el pelo rizado "
            "y castaño. El pequeño, Sergio, apenas tenía quince años y ya "
            "era más fuerte que Alberto."
        ),
        expected_entities={
            "Alberto": "character",
            "Mónica": "character",
            "Sergio": "character",
        },
        expected_attributes={
            "Alberto": {"height": "alto", "eye_color": "azules"},
            "Mónica": {"hair_color": "castaño"},
            "Sergio": {"age": "quince"},
        },
        expected_fusions=[],
        forbidden_attributes={
            "Mónica": ["eye_color", "height"],
            "Sergio": ["eye_color"],
        },
        difficulty="hard",
        description="Tres personajes con descripciones entrelazadas."
    ),

    PipelineTestCase(
        id="e2e_multi_02_dialogue_scene",
        category="multi_personaje",
        text=(
            "—¿Quién eres? —preguntó Elena, apartándose el pelo rubio de la cara.\n"
            "—Me llamo Diego —respondió el hombre moreno—. Soy el nuevo vecino.\n"
            "—Bienvenido —dijo Elena con sus grandes ojos pardos—. Yo soy Elena García."
        ),
        expected_entities={
            "Elena": "character",
            "Diego": "character",
        },
        expected_attributes={
            "Elena": {"hair_color": "rubio", "eye_color": "pardos"},
            "Diego": {"hair_color": "moreno"},
        },
        expected_fusions=[
            ["Elena", "Elena García"],
        ],
        forbidden_attributes={
            "Diego": ["eye_color", "hair_color_rubio"],
            "Elena": ["hair_color_moreno"],
        },
        difficulty="hard",
        description="Diálogo con descripciones intercaladas y fusión nombre/apellido."
    ),

    # -------------------------------------------------------------------------
    # 3. TITLE + NAME FUSION - Personaje referido de múltiples formas
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_title_01_doctor",
        category="titulos",
        text=(
            "El doctor Hernández examinó al paciente. Hernández era un hombre "
            "de unos sesenta años, calvo y con gafas gruesas. El doctor le "
            "pidió que respirara hondo."
        ),
        expected_entities={
            "Hernández": "character",
        },
        expected_attributes={
            "Hernández": {"age": "sesenta", "hair_color": "calvo"},
        },
        expected_fusions=[
            ["doctor Hernández", "Hernández"],
        ],
        difficulty="medium",
        description="Personaje referido con y sin título profesional."
    ),

    PipelineTestCase(
        id="e2e_title_02_don",
        category="titulos",
        text=(
            "Don Álvaro entró en el casino. Era un hombre alto y elegante, "
            "de pelo entrecano. Álvaro saludó a los presentes con un gesto. "
            "Don Álvaro de Mendoza, como le gustaba que le llamaran, tomó asiento."
        ),
        expected_entities={
            "Álvaro de Mendoza": "character",
        },
        expected_attributes={
            "Álvaro de Mendoza": {"height": "alto", "hair_color": "entrecano"},
        },
        expected_fusions=[
            ["Don Álvaro", "Álvaro", "Don Álvaro de Mendoza", "Álvaro de Mendoza"],
        ],
        difficulty="adversarial",
        description=(
            "Personaje con 4 variantes: Don Álvaro, Álvaro, Don Álvaro de Mendoza, "
            "Álvaro de Mendoza. Todas deberían fusionarse."
        ),
    ),

    PipelineTestCase(
        id="e2e_title_03_military",
        category="titulos",
        text=(
            "El capitán Morales revisó a sus hombres. Morales era joven para "
            "su rango, apenas treinta años, pero tenía una mirada dura y pelo "
            "cortado al rape."
        ),
        expected_entities={
            "Morales": "character",
        },
        expected_attributes={
            "Morales": {"age": "treinta"},
        },
        expected_fusions=[
            ["capitán Morales", "Morales"],
        ],
        difficulty="medium",
        description="Rango militar + apellido debe fusionarse con apellido solo."
    ),

    # -------------------------------------------------------------------------
    # 4. FICTIONAL NAMES - Nombres inventados difíciles para NER
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_fiction_01_fantasy",
        category="ficcion",
        text=(
            "Eldric el Sabio contempló la torre. Tenía la barba blanca y larga, "
            "y unos ojos que brillaban como estrellas. Su bastón emitía una luz "
            "tenue. Kael, su aprendiz, era joven y pelirrojo."
        ),
        expected_entities={
            "Eldric": "character",
            "Kael": "character",
        },
        expected_attributes={
            "Eldric": {"hair_color": "blanca"},
            "Kael": {"age": "joven", "hair_color": "pelirrojo"},
        },
        expected_fusions=[
            ["Eldric", "Eldric el Sabio"],
        ],
        forbidden_attributes={
            "Kael": ["hair_color_blanca"],
        },
        difficulty="hard",
        description="Nombres de fantasía que spaCy no reconocerá como PER."
    ),

    PipelineTestCase(
        id="e2e_fiction_02_scifi",
        category="ficcion",
        text=(
            "La comandante Zara-7 tenía piel azul y ojos plateados, como "
            "todos los de su especie. Su segundo al mando, el teniente Kron, "
            "era humano: alto, de pelo negro y ojos oscuros."
        ),
        expected_entities={
            "Zara-7": "character",
            "Kron": "character",
        },
        expected_attributes={
            "Zara-7": {"skin": "azul", "eye_color": "plateados"},
            "Kron": {"height": "alto", "hair_color": "negro", "eye_color": "oscuros"},
        },
        expected_fusions=[],
        forbidden_attributes={
            "Kron": ["skin"],
            "Zara-7": ["height"],
        },
        difficulty="adversarial",
        description="Nombres de ciencia ficción con guión y números."
    ),

    # -------------------------------------------------------------------------
    # 5. NON-FICTION ENTITIES - Entidades en textos de no ficción
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_nonfic_01_cookbook",
        category="no_ficcion",
        text=(
            "El paté es un plato francés elaborado con hígado de pato. "
            "La bechamel es una salsa blanca espesa. El roux, su base, "
            "se prepara con mantequilla y harina."
        ),
        expected_entities={
            "paté": "concept",
            "bechamel": "concept",
        },
        expected_attributes={},
        expected_fusions=[],
        difficulty="medium",
        description=(
            "Texto de cocina: entidades son conceptos/ingredientes, "
            "no personajes. El NER no debe clasificarlas como PER."
        ),
    ),

    PipelineTestCase(
        id="e2e_nonfic_02_self_help",
        category="no_ficcion",
        text=(
            "La resiliencia es la capacidad de adaptarse. Viktor Frankl, "
            "psiquiatra austríaco, demostró que encontrar sentido al "
            "sufrimiento fortalece la resiliencia."
        ),
        expected_entities={
            "Viktor Frankl": "character",
            "resiliencia": "concept",
        },
        expected_attributes={},
        expected_fusions=[],
        forbidden_entities=[],
        difficulty="medium",
        description="Mezcla de personaje real y concepto abstracto."
    ),

    # -------------------------------------------------------------------------
    # 6. COMPLEX NARRATIVES - Narrativas con dificultades combinadas
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_complex_01_family",
        category="narrativa_compleja",
        text=(
            "Los García vivían en una casa grande. El padre, Don Antonio García, "
            "era un hombre corpulento de bigote espeso. Su esposa, Doña Carmen, "
            "tenía el pelo blanco y unos ojos negros vivaces. El hijo mayor, "
            "Antonio —al que todos llamaban Toño— había heredado los ojos de "
            "su madre. La pequeña Lucía García, de apenas diez años, tenía "
            "el pelo rubio como el trigo."
        ),
        expected_entities={
            "Antonio García": "character",
            "Carmen": "character",
            "Lucía García": "character",
        },
        expected_attributes={
            "Antonio García": {"build": "corpulento"},
            "Carmen": {"hair_color": "blanco", "eye_color": "negros"},
            "Lucía García": {"age": "diez", "hair_color": "rubio"},
        },
        expected_fusions=[
            ["Don Antonio García", "Antonio García"],
            ["Doña Carmen", "Carmen"],
            ["Lucía García"],
        ],
        forbidden_attributes={
            "Antonio García": ["hair_color_blanco", "eye_color"],
            "Lucía García": ["eye_color", "build"],
        },
        difficulty="adversarial",
        description=(
            "Escena familiar con honoríficos, herencia de rasgos, apodos, "
            "y múltiples personajes con el mismo apellido."
        ),
    ),

    PipelineTestCase(
        id="e2e_complex_02_flashback",
        category="narrativa_compleja",
        text=(
            "Recordaba a su abuela Pilar como una mujer menuda de pelo blanco. "
            "Ahora, treinta años después, Sara se miraba al espejo. Tenía los "
            "mismos ojos negros de la abuela, pero su pelo era castaño oscuro. "
            "A sus cuarenta años, Sara García se parecía cada vez más a ella."
        ),
        expected_entities={
            "Pilar": "character",
            "Sara García": "character",
        },
        expected_attributes={
            "Pilar": {"build": "menuda", "hair_color": "blanco"},
            "Sara García": {
                "eye_color": "negros",
                "hair_color": "castaño oscuro",
                "age": "cuarenta",
            },
        },
        expected_fusions=[
            ["Sara", "Sara García"],
        ],
        forbidden_attributes={
            "Sara García": ["build", "hair_color_blanco"],
            "Pilar": ["hair_color_castaño"],
        },
        difficulty="adversarial",
        description=(
            "Flashback con comparación entre abuela y nieta. Atributos de "
            "la abuela no deben contaminar a la nieta y viceversa."
        ),
    ),

    PipelineTestCase(
        id="e2e_complex_03_crowd",
        category="narrativa_compleja",
        text=(
            "La reunión empezó a las diez. El director, Rafael Mora, un hombre "
            "de pelo gris y gafas redondas, tomó la palabra. A su derecha, "
            "la subdirectora Isabel Vega, morena y de mirada intensa, tomaba "
            "notas. Más allá, el jefe de ventas, un tal Paco Gutiérrez, gordito "
            "y sonriente, hacía cálculos en su libreta. Y en la última fila, "
            "Marta Díaz, la becaria, alta y tímida, apenas se atrevía a hablar."
        ),
        expected_entities={
            "Rafael Mora": "character",
            "Isabel Vega": "character",
            "Paco Gutiérrez": "character",
            "Marta Díaz": "character",
        },
        expected_attributes={
            "Rafael Mora": {"hair_color": "gris"},
            "Isabel Vega": {"hair_color": "morena"},
            "Paco Gutiérrez": {"build": "gordito"},
            "Marta Díaz": {"height": "alta"},
        },
        expected_fusions=[],
        forbidden_attributes={
            "Rafael Mora": ["height", "build"],
            "Isabel Vega": ["hair_color_gris", "build"],
            "Paco Gutiérrez": ["hair_color", "height"],
            "Marta Díaz": ["hair_color", "build"],
        },
        difficulty="adversarial",
        description=(
            "Cuatro personajes con descripciones apositivas intercaladas. "
            "Cada atributo debe ir al personaje correcto."
        ),
    ),

    # -------------------------------------------------------------------------
    # 7. EDGE CASES - Casos extremos
    # -------------------------------------------------------------------------
    PipelineTestCase(
        id="e2e_edge_01_no_entities",
        category="edge_case",
        text="El sol brillaba sobre los campos de trigo. El viento soplaba suavemente.",
        expected_entities={},
        expected_attributes={},
        expected_fusions=[],
        difficulty="easy",
        description="Texto sin entidades nombradas. El pipeline no debe crashear."
    ),

    PipelineTestCase(
        id="e2e_edge_02_entity_no_attrs",
        category="edge_case",
        text="María entró en la sala y salió corriendo.",
        expected_entities={
            "María": "character",
        },
        expected_attributes={},
        expected_fusions=[],
        difficulty="easy",
        description="Entidad sin atributos descriptivos."
    ),

    PipelineTestCase(
        id="e2e_edge_03_long_description",
        category="edge_case",
        text=(
            "Clara tenía los ojos de un verde intenso que recordaban a los "
            "prados de Irlanda en primavera, cuando la lluvia reciente hacía "
            "brillar la hierba bajo un sol tímido que apenas asomaba entre "
            "las nubes grises del norte. Su pelo, negro como el azabache, "
            "le caía en ondas espesas hasta más allá de los hombros, y su "
            "piel, clara como la porcelana, contrastaba con las ojeras "
            "violáceas que delataban muchas noches de insomnio."
        ),
        expected_entities={
            "Clara": "character",
        },
        expected_attributes={
            "Clara": {
                "eye_color": "verde",
                "hair_color": "negro",
            },
        },
        expected_fusions=[],
        difficulty="hard",
        description=(
            "Descripción muy larga con metáforas. El extractor debe "
            "encontrar los atributos reales entre la prosa literaria."
        ),
    ),

    PipelineTestCase(
        id="e2e_edge_04_same_name_different_people",
        category="edge_case",
        text=(
            "Juan el panadero tenía las manos grandes y ásperas. "
            "Juan el herrero, en cambio, era delgado pero fuerte. "
            "Ambos Juanes se conocían desde niños."
        ),
        expected_entities={
            "Juan el panadero": "character",
            "Juan el herrero": "character",
        },
        expected_attributes={},
        expected_fusions=[],
        forbidden_entities=[],
        difficulty="adversarial",
        description=(
            "Dos personajes con el mismo nombre diferenciados por profesión. "
            "NO deben fusionarse."
        ),
    ),

    PipelineTestCase(
        id="e2e_edge_05_narrator",
        category="edge_case",
        text=(
            "Me llamo Marcos y tengo treinta años. Soy alto y moreno, "
            "con una cicatriz en la ceja izquierda. Mi mejor amigo, Pablo, "
            "es rubio y bajito."
        ),
        expected_entities={
            "Marcos": "character",
            "Pablo": "character",
        },
        expected_attributes={
            "Marcos": {"age": "treinta", "height": "alto", "hair_color": "moreno"},
            "Pablo": {"hair_color": "rubio", "height": "bajito"},
        },
        expected_fusions=[],
        forbidden_attributes={
            "Pablo": ["age"],
            "Marcos": ["hair_color_rubio"],
        },
        difficulty="hard",
        description="Narración en primera persona con autodescripción."
    ),
]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def ner_extractor():
    """Crea un NERExtractor."""
    try:
        from narrative_assistant.nlp.ner import NERExtractor
        return NERExtractor()
    except Exception:
        pytest.skip("NERExtractor no disponible (requiere spaCy)")


@pytest.fixture
def attr_extractor():
    """Crea un AttributeExtractor sin LLM/embeddings."""
    from narrative_assistant.nlp.attributes import AttributeExtractor
    return AttributeExtractor(
        filter_metaphors=True,
        min_confidence=0.5,
        use_llm=False,
        use_embeddings=False,
        use_dependency_extraction=True,
        use_patterns=True,
    )


@pytest.fixture
def fusion_service():
    """Crea el servicio de fusión semántica."""
    try:
        from narrative_assistant.entities.semantic_fusion import SemanticFusionService
        return SemanticFusionService()
    except Exception:
        pytest.skip("SemanticFusionService no disponible")


def run_ner(ner_extractor, text: str) -> list[tuple[str, str, int, int]]:
    """Ejecuta NER y retorna lista de (name, label, start, end)."""
    result = ner_extractor.extract_entities(text)
    if result.is_failure:
        return []

    entities = []
    for ent in result.value.entities:
        entities.append((ent.text, ent.label.value, ent.start_char, ent.end_char))
    return entities


def run_attributes(attr_extractor, text: str, entity_mentions: list) -> dict[str, dict]:
    """Ejecuta extracción de atributos y retorna por entidad."""
    ner_mentions = [(name, start, end, label) for name, label, start, end in entity_mentions]

    result = attr_extractor.extract_attributes(text, entity_mentions=ner_mentions)
    if result.is_failure:
        return {}

    by_entity = {}
    for attr in result.value.attributes:
        entity = attr.entity_name
        if entity not in by_entity:
            by_entity[entity] = {}
        by_entity[entity][attr.key.value] = attr.value

    return by_entity


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestPipelineNER:
    """Tests end-to-end enfocados en la etapa NER."""

    @pytest.mark.parametrize(
        "case",
        [c for c in PIPELINE_CASES if c.expected_entities],
        ids=lambda c: c.id,
    )
    def test_entities_detected(self, ner_extractor, case: PipelineTestCase):
        """Verifica que las entidades esperadas se detecten."""
        ner_entities = run_ner(ner_extractor, case.text)
        detected_names = [name for name, _, _, _ in ner_entities]

        for expected_name in case.expected_entities:
            found = any(
                expected_name.lower() in name.lower() or name.lower() in expected_name.lower()
                for name in detected_names
            )
            assert found, (
                f"[{case.id}] Entidad '{expected_name}' no detectada por NER.\n"
                f"Descripción: {case.description}\n"
                f"Detectadas: {detected_names}"
            )


class TestPipelineAttributes:
    """Tests end-to-end enfocados en la etapa de atributos."""

    @pytest.mark.parametrize(
        "case",
        [c for c in PIPELINE_CASES if c.expected_attributes],
        ids=lambda c: c.id,
    )
    def test_attributes_assigned(self, ner_extractor, attr_extractor, case: PipelineTestCase):
        """Verifica que los atributos se asignen a la entidad correcta."""
        # Stage 1: NER
        ner_entities = run_ner(ner_extractor, case.text)

        if not ner_entities:
            pytest.skip(f"NER no detectó entidades en: {case.text[:50]}...")

        # Stage 2: Attributes
        attributes = run_attributes(attr_extractor, case.text, ner_entities)

        # Check expected attributes
        for entity_name, expected_attrs in case.expected_attributes.items():
            # Find entity in results (flexible matching)
            matching_entity = None
            for result_entity in attributes:
                if (entity_name.lower() in result_entity.lower() or
                        result_entity.lower() in entity_name.lower()):
                    matching_entity = result_entity
                    break

            assert matching_entity is not None, (
                f"[{case.id}] Entidad '{entity_name}' sin atributos.\n"
                f"Descripción: {case.description}\n"
                f"Entidades con atributos: {list(attributes.keys())}"
            )

            for key, value in expected_attrs.items():
                actual_value = attributes[matching_entity].get(key)
                assert actual_value is not None, (
                    f"[{case.id}] Atributo '{key}' no encontrado para '{entity_name}'.\n"
                    f"Descripción: {case.description}\n"
                    f"Atributos de {matching_entity}: {attributes[matching_entity]}"
                )

    @pytest.mark.parametrize(
        "case",
        [c for c in PIPELINE_CASES if c.forbidden_attributes],
        ids=lambda c: c.id,
    )
    def test_forbidden_attributes(self, ner_extractor, attr_extractor, case: PipelineTestCase):
        """Verifica que los atributos NO se asignen a entidades incorrectas."""
        # Stage 1: NER
        ner_entities = run_ner(ner_extractor, case.text)
        if not ner_entities:
            pytest.skip("NER no detectó entidades")

        # Stage 2: Attributes
        attributes = run_attributes(attr_extractor, case.text, ner_entities)

        # Check forbidden attributes
        for entity_name, forbidden_keys in case.forbidden_attributes.items():
            matching_entity = None
            for result_entity in attributes:
                if (entity_name.lower() in result_entity.lower() or
                        result_entity.lower() in entity_name.lower()):
                    matching_entity = result_entity
                    break

            if matching_entity is None:
                continue  # Entity not in results → no forbidden violation

            for key in forbidden_keys:
                assert key not in attributes[matching_entity], (
                    f"[{case.id}] Atributo PROHIBIDO '{key}' asignado a '{entity_name}'.\n"
                    f"Valor: {attributes[matching_entity].get(key)}\n"
                    f"Descripción: {case.description}\n"
                    f"Todos los atributos: {attributes}"
                )


class TestPipelineFusion:
    """Tests end-to-end enfocados en la etapa de fusión."""

    @pytest.mark.parametrize(
        "case",
        [c for c in PIPELINE_CASES if c.expected_fusions],
        ids=lambda c: c.id,
    )
    def test_entity_fusion(self, ner_extractor, fusion_service, case: PipelineTestCase):
        """Verifica que las entidades que deberían fusionarse lo hagan."""
        from narrative_assistant.entities.models import Entity, EntityType
        from narrative_assistant.nlp.ner import EntityLabel

        # Stage 1: NER
        ner_entities = run_ner(ner_extractor, case.text)

        if not ner_entities:
            pytest.skip("NER no detectó entidades")

        # Map NER labels to EntityType
        label_map = {
            "PER": EntityType.CHARACTER,
            "LOC": EntityType.LOCATION,
            "ORG": EntityType.ORGANIZATION,
            "MISC": EntityType.CONCEPT,
        }

        # Create Entity objects from NER results
        entities = []
        for i, (name, label, start, end) in enumerate(ner_entities):
            etype = label_map.get(label, EntityType.CONCEPT)
            entities.append(Entity(
                id=i + 1,
                project_id=1,
                entity_type=etype,
                canonical_name=name,
                mention_count=1,
                is_active=True,
            ))

        # Stage 2: Check fusion decisions
        for fusion_group in case.expected_fusions:
            # Find entities from this fusion group in NER results
            group_entities = []
            for group_name in fusion_group:
                for ent in entities:
                    if (group_name.lower() in ent.canonical_name.lower() or
                            ent.canonical_name.lower() in group_name.lower()):
                        group_entities.append(ent)
                        break

            if len(group_entities) < 2:
                # Not all entities in the group were detected by NER
                continue

            # Check pairwise that they should merge
            for i in range(len(group_entities)):
                for j in range(i + 1, len(group_entities)):
                    result = fusion_service.should_merge(group_entities[i], group_entities[j])
                    assert result.should_merge, (
                        f"[{case.id}] '{group_entities[i].canonical_name}' y "
                        f"'{group_entities[j].canonical_name}' deberían fusionarse.\n"
                        f"Resultado: should_merge={result.should_merge}, "
                        f"similarity={result.similarity:.3f}, method={result.method}\n"
                        f"Descripción: {case.description}"
                    )


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestPipelineSummary:
    """Test de resumen que ejecuta el pipeline completo."""

    def test_full_pipeline_summary(self, ner_extractor, attr_extractor):
        """Ejecuta todos los casos y genera informe completo."""
        ner_passed = 0
        ner_failed = 0
        attr_passed = 0
        attr_failed = 0
        forbidden_violations = 0
        total_cases = len([c for c in PIPELINE_CASES if c.expected_entities])

        for case in PIPELINE_CASES:
            try:
                # NER stage
                ner_entities = run_ner(ner_extractor, case.text)
                detected_names = [name for name, _, _, _ in ner_entities]

                all_found = True
                for expected_name in case.expected_entities:
                    found = any(
                        expected_name.lower() in name.lower() or name.lower() in expected_name.lower()
                        for name in detected_names
                    )
                    if not found:
                        all_found = False

                if all_found and case.expected_entities:
                    ner_passed += 1
                elif case.expected_entities:
                    ner_failed += 1

                # Attribute stage
                if ner_entities and case.expected_attributes:
                    attributes = run_attributes(attr_extractor, case.text, ner_entities)

                    all_attrs_correct = True
                    for entity_name, expected_attrs in case.expected_attributes.items():
                        matching = None
                        for re_name in attributes:
                            if entity_name.lower() in re_name.lower() or re_name.lower() in entity_name.lower():
                                matching = re_name
                                break
                        if not matching:
                            all_attrs_correct = False
                            continue
                        for key, value in expected_attrs.items():
                            if key not in attributes[matching]:
                                all_attrs_correct = False

                    if all_attrs_correct:
                        attr_passed += 1
                    else:
                        attr_failed += 1

                    # Check forbidden
                    for entity_name, forbidden_keys in case.forbidden_attributes.items():
                        matching = None
                        for re_name in attributes:
                            if entity_name.lower() in re_name.lower() or re_name.lower() in entity_name.lower():
                                matching = re_name
                                break
                        if matching:
                            for key in forbidden_keys:
                                if key in attributes[matching]:
                                    forbidden_violations += 1

            except Exception as e:
                ner_failed += 1

        # Report
        print(f"\n{'='*70}")
        print(f"END-TO-END PIPELINE ADVERSARIAL REPORT")
        print(f"{'='*70}")
        print(f"\nNER Stage:")
        print(f"  Passed: {ner_passed}/{total_cases}")
        print(f"  Failed: {ner_failed}/{total_cases}")
        if total_cases > 0:
            print(f"  Rate: {ner_passed/max(1,total_cases)*100:.1f}%")
        print(f"\nAttribute Stage:")
        print(f"  Passed: {attr_passed}")
        print(f"  Failed: {attr_failed}")
        print(f"  Forbidden violations: {forbidden_violations}")
        print(f"{'='*70}")
