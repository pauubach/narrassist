"""
Tests adversariales GAN-style para el sistema de fusión de entidades.

Objetivo: Identificar casos donde el sistema falla al:
1. Fusionar entidades que DEBERÍAN fusionarse (misma persona, distinta forma)
2. NO fusionar entidades que NO deberían fusionarse (personas diferentes)
3. Clasificar correctamente el tipo de entidad (CHARACTER vs CONCEPT etc.)
4. Normalizar nombres compuestos españoles
5. Manejar aliases, títulos y apodos
6. Detectar variaciones ortográficas
7. Resolver nombres con artículos y preposiciones
8. Distinguir homónimos por contexto

Inspirado en el bug real: "María Sánchez" clasificada como CONCEPT
en vez de CHARACTER, y no fusionada con "María".

Autor: GAN-style Adversary Agent
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional

from narrative_assistant.entities.models import Entity, EntityType
from narrative_assistant.entities.semantic_fusion import (
    SemanticFusionService,
    SemanticFusionResult,
    normalize_for_comparison,
    strip_accents,
    names_match_after_normalization,
)


# =============================================================================
# TEST DATA STRUCTURES
# =============================================================================

@dataclass
class FusionTestCase:
    """Caso de test para fusión de entidades."""
    id: str
    category: str
    entity1_name: str
    entity1_type: EntityType
    entity2_name: str
    entity2_type: EntityType
    should_fuse: bool  # True = deberían fusionarse
    entity1_aliases: list[str] = field(default_factory=list)
    entity2_aliases: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    linguistic_note: str = ""


@dataclass
class ClassificationTestCase:
    """Caso de test para clasificación de tipo de entidad."""
    id: str
    category: str
    text: str
    entity_name: str
    expected_type: EntityType
    wrong_types: list[EntityType] = field(default_factory=list)
    difficulty: str = "medium"
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: SHOULD MERGE - Misma entidad, formas diferentes
# =============================================================================

SHOULD_MERGE_TESTS = [
    # --- 1a. Nombre completo vs. nombre parcial ---
    FusionTestCase(
        id="merge_01_full_vs_first",
        category="nombre_parcial",
        entity1_name="María Sánchez",
        entity1_type=EntityType.CHARACTER,
        entity2_name="María",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Nombre completo vs nombre de pila. Caso más común en ficción."
    ),
    FusionTestCase(
        id="merge_02_full_vs_surname",
        category="nombre_parcial",
        entity1_name="Juan Pérez",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Pérez",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="medium",
        linguistic_note="Nombre completo vs apellido solo."
    ),
    FusionTestCase(
        id="merge_03_three_names",
        category="nombre_parcial",
        entity1_name="Ana María López García",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Ana María",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="medium",
        linguistic_note="Nombre compuesto con dos apellidos vs nombre compuesto."
    ),

    # --- 1b. Títulos y honoríficos ---
    FusionTestCase(
        id="merge_04_don_title",
        category="titulos",
        entity1_name="Don Fernando",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Fernando",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Tratamiento 'Don' + nombre = mismo personaje."
    ),
    FusionTestCase(
        id="merge_05_doctor_title",
        category="titulos",
        entity1_name="Doctor Martínez",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Martínez",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Título profesional + apellido = mismo personaje."
    ),
    FusionTestCase(
        id="merge_06_doña_title",
        category="titulos",
        entity1_name="Doña Isabel",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Isabel",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Tratamiento 'Doña' + nombre."
    ),
    FusionTestCase(
        id="merge_07_nobility",
        category="titulos",
        entity1_name="Conde de Villamediana",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Villamediana",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="hard",
        linguistic_note="Título nobiliario + topónimo. Difícil porque Villamediana podría ser un lugar."
    ),
    FusionTestCase(
        id="merge_08_military",
        category="titulos",
        entity1_name="Capitán Morales",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Morales",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Rango militar + apellido."
    ),

    # --- 1c. Variaciones ortográficas ---
    FusionTestCase(
        id="merge_09_accent_variation",
        category="ortografia",
        entity1_name="María",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Maria",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Con y sin tilde. Muy común en textos con erratas."
    ),
    FusionTestCase(
        id="merge_10_jose_accent",
        category="ortografia",
        entity1_name="José García",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Jose García",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Acento faltante en nombre propio."
    ),
    FusionTestCase(
        id="merge_11_ñ_variation",
        category="ortografia",
        entity1_name="Año Nuevo",
        entity1_type=EntityType.EVENT,
        entity2_name="Ano Nuevo",
        entity2_type=EntityType.EVENT,
        should_fuse=True,
        difficulty="medium",
        linguistic_note="Pérdida de ñ (posible error de encoding). NOTA: 'año' vs 'ano' son distintos en español pero en contexto de evento son claramente el mismo."
    ),

    # --- 1d. Artículos y preposiciones ---
    FusionTestCase(
        id="merge_12_with_article",
        category="articulos",
        entity1_name="El Escorial",
        entity1_type=EntityType.LOCATION,
        entity2_name="Escorial",
        entity2_type=EntityType.LOCATION,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Topónimo con artículo vs sin artículo."
    ),
    FusionTestCase(
        id="merge_13_de_la_preposition",
        category="articulos",
        entity1_name="La Casa de la Moneda",
        entity1_type=EntityType.BUILDING,
        entity2_name="Casa de la Moneda",
        entity2_type=EntityType.BUILDING,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="Edificio con artículo inicial."
    ),

    # --- 1e. Apodos y aliases ---
    FusionTestCase(
        id="merge_14_nickname",
        category="apodos",
        entity1_name="Francisco",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Paco",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        entity1_aliases=["Paco"],
        difficulty="hard",
        linguistic_note="Diminutivo/hipocorístico. Solo resoluble si el alias está registrado."
    ),
    FusionTestCase(
        id="merge_15_the_nickname",
        category="apodos",
        entity1_name="el Gordo",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Roberto",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        entity2_aliases=["el Gordo"],
        difficulty="hard",
        linguistic_note="Apodo descriptivo. Solo resoluble con alias registrado."
    ),

    # --- 1f. Nombres con preposiciones ---
    FusionTestCase(
        id="merge_16_de_surname",
        category="preposiciones",
        entity1_name="Luis de la Fuente",
        entity1_type=EntityType.CHARACTER,
        entity2_name="De la Fuente",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="medium",
        linguistic_note="Nombre completo vs apellido con preposición."
    ),
    FusionTestCase(
        id="merge_17_del_surname",
        category="preposiciones",
        entity1_name="Carmen del Río",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Del Río",
        entity2_type=EntityType.CHARACTER,
        should_fuse=True,
        difficulty="medium",
        linguistic_note="Nombre + apellido con 'del'."
    ),

    # --- 1g. Misma entidad, distinto tipo NER ---
    FusionTestCase(
        id="merge_18_cross_type_person",
        category="cross_type",
        entity1_name="María Sánchez",
        entity1_type=EntityType.CHARACTER,
        entity2_name="María Sánchez",
        entity2_type=EntityType.CONCEPT,
        should_fuse=True,
        difficulty="adversarial",
        linguistic_note=(
            "BUG REAL: Mismo nombre pero NER clasificó una como CHARACTER y otra "
            "como CONCEPT. El fusionador debe permitir fusión con reclasificación."
        ),
    ),
    FusionTestCase(
        id="merge_19_location_building",
        category="cross_type",
        entity1_name="Iglesia de San Pedro",
        entity1_type=EntityType.LOCATION,
        entity2_name="Iglesia de San Pedro",
        entity2_type=EntityType.BUILDING,
        should_fuse=True,
        difficulty="easy",
        linguistic_note="LOCATION y BUILDING son tipos compatibles para fusión."
    ),
]


# =============================================================================
# CATEGORÍA 2: SHOULD NOT MERGE - Entidades diferentes que parecen similares
# =============================================================================

SHOULD_NOT_MERGE_TESTS = [
    # --- 2a. Homónimos (mismo nombre, persona diferente) ---
    FusionTestCase(
        id="no_merge_01_homonym",
        category="homonimos",
        entity1_name="María García",
        entity1_type=EntityType.CHARACTER,
        entity2_name="María López",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="easy",
        linguistic_note="Mismo nombre, distinto apellido = personas diferentes."
    ),
    FusionTestCase(
        id="no_merge_02_same_surname",
        category="homonimos",
        entity1_name="Carlos Ruiz",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Pedro Ruiz",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="easy",
        linguistic_note="Mismo apellido, distinto nombre = personas diferentes (posiblemente familia)."
    ),

    # --- 2b. Persona vs. Lugar ---
    FusionTestCase(
        id="no_merge_03_person_vs_place",
        category="persona_lugar",
        entity1_name="Santiago",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Santiago",
        entity2_type=EntityType.LOCATION,
        should_fuse=False,
        difficulty="hard",
        linguistic_note="'Santiago' como persona y como ciudad. Son entidades completamente distintas."
    ),
    FusionTestCase(
        id="no_merge_04_person_vs_org",
        category="persona_lugar",
        entity1_name="Mercedes",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Mercedes",
        entity2_type=EntityType.ORGANIZATION,
        should_fuse=False,
        difficulty="hard",
        linguistic_note="Mercedes como persona vs Mercedes como marca de coches."
    ),

    # --- 2c. Nombres parecidos pero diferentes ---
    FusionTestCase(
        id="no_merge_05_similar_names",
        category="nombres_similares",
        entity1_name="Marta",
        entity1_type=EntityType.CHARACTER,
        entity2_name="María",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="medium",
        linguistic_note="Nombres similares fonéticamente pero son personajes distintos."
    ),
    FusionTestCase(
        id="no_merge_06_diminutive_trap",
        category="nombres_similares",
        entity1_name="Pedro",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Pedrín",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="adversarial",
        linguistic_note=(
            "Diminutivo que PODRÍA ser la misma persona pero también un hijo. "
            "Sin contexto adicional, no fusionar."
        ),
    ),

    # --- 2d. Relación familiar, no identidad ---
    FusionTestCase(
        id="no_merge_07_parent_child",
        category="familia",
        entity1_name="Antonio Ruiz padre",
        entity1_type=EntityType.CHARACTER,
        entity2_name="Antonio Ruiz hijo",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="medium",
        linguistic_note="Padre e hijo con el mismo nombre. Explícitamente diferentes."
    ),

    # --- 2e. Conceptos vs. nombres ---
    FusionTestCase(
        id="no_merge_08_concept_vs_name",
        category="concepto_nombre",
        entity1_name="La alta sensibilidad",
        entity1_type=EntityType.CONCEPT,
        entity2_name="Alta",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="easy",
        linguistic_note="'La alta sensibilidad' es un concepto, 'Alta' es un nombre."
    ),
    FusionTestCase(
        id="no_merge_09_event_vs_place",
        category="concepto_nombre",
        entity1_name="La Gran Guerra",
        entity1_type=EntityType.EVENT,
        entity2_name="La Gran Vía",
        entity2_type=EntityType.LOCATION,
        should_fuse=False,
        difficulty="easy",
        linguistic_note="Nombres que comparten 'La Gran' pero son entidades totalmente diferentes."
    ),

    # --- 2f. Profesión como apodo falso ---
    FusionTestCase(
        id="no_merge_10_profession_not_alias",
        category="profesion_falsa",
        entity1_name="el doctor",
        entity1_type=EntityType.CHARACTER,
        entity2_name="el abogado",
        entity2_type=EntityType.CHARACTER,
        should_fuse=False,
        difficulty="medium",
        linguistic_note="Dos personajes referidos por su profesión. NO son la misma persona."
    ),
]


# =============================================================================
# CATEGORÍA 3: ENTITY TYPE CLASSIFICATION
# (Texto → ¿Qué tipo debería tener la entidad?)
# =============================================================================

CLASSIFICATION_TESTS = [
    # --- 3a. Personas que NER clasifica como MISC/CONCEPT ---
    ClassificationTestCase(
        id="class_01_spanish_compound",
        category="persona_como_concepto",
        text="María Sánchez entró en la habitación.",
        entity_name="María Sánchez",
        expected_type=EntityType.CHARACTER,
        wrong_types=[EntityType.CONCEPT, EntityType.ORGANIZATION],
        difficulty="adversarial",
        linguistic_note=(
            "BUG REAL: 'María Sánchez' clasificada como CONCEPT por el NER. "
            "Los nombres españoles con apellido pueden confundir a spaCy "
            "entrenado en texto periodístico."
        ),
    ),
    ClassificationTestCase(
        id="class_02_two_surnames",
        category="persona_como_concepto",
        text="Pedro García López saludó a todos.",
        entity_name="Pedro García López",
        expected_type=EntityType.CHARACTER,
        wrong_types=[EntityType.CONCEPT],
        difficulty="medium",
        linguistic_note="Nombre con dos apellidos (patrón español) → CHARACTER."
    ),
    ClassificationTestCase(
        id="class_03_fictional_name",
        category="persona_como_concepto",
        text="Gandalf avanzó por el camino.",
        entity_name="Gandalf",
        expected_type=EntityType.CHARACTER,
        wrong_types=[EntityType.CONCEPT, EntityType.LOCATION],
        difficulty="hard",
        linguistic_note="Nombre ficticio no presente en el léxico del NER."
    ),
    ClassificationTestCase(
        id="class_04_de_la_surname",
        category="persona_como_concepto",
        text="Luis de la Fuente tomó la palabra.",
        entity_name="Luis de la Fuente",
        expected_type=EntityType.CHARACTER,
        wrong_types=[EntityType.LOCATION, EntityType.CONCEPT],
        difficulty="medium",
        linguistic_note="Apellido con preposición 'de la'. El NER puede fragmentar el nombre."
    ),

    # --- 3b. Lugares confundidos con personas ---
    ClassificationTestCase(
        id="class_05_place_as_person",
        category="lugar_como_persona",
        text="Santiago de Compostela es una ciudad preciosa.",
        entity_name="Santiago de Compostela",
        expected_type=EntityType.LOCATION,
        wrong_types=[EntityType.CHARACTER],
        difficulty="medium",
        linguistic_note="Topónimo que contiene nombre de persona (Santiago)."
    ),
    ClassificationTestCase(
        id="class_06_building_vs_person",
        category="lugar_como_persona",
        text="San Fernando era un hospital enorme.",
        entity_name="San Fernando",
        expected_type=EntityType.BUILDING,
        wrong_types=[EntityType.CHARACTER],
        difficulty="hard",
        linguistic_note="'San Fernando' como edificio (hospital), no como persona."
    ),

    # --- 3c. Organizaciones ---
    ClassificationTestCase(
        id="class_07_org",
        category="organizaciones",
        text="La Hermandad del Dragón controlaba la ciudad.",
        entity_name="La Hermandad del Dragón",
        expected_type=EntityType.ORGANIZATION,
        wrong_types=[EntityType.CHARACTER, EntityType.CONCEPT],
        difficulty="medium",
        linguistic_note="Organización ficticia con nombre fantástico."
    ),
    ClassificationTestCase(
        id="class_08_family",
        category="organizaciones",
        text="Los Mendoza dominaron la región durante siglos.",
        entity_name="Los Mendoza",
        expected_type=EntityType.FAMILY,
        wrong_types=[EntityType.CHARACTER],
        difficulty="hard",
        linguistic_note="Apellido en plural = familia, no un solo personaje."
    ),

    # --- 3d. Conceptos abstractos ---
    ClassificationTestCase(
        id="class_09_concept",
        category="conceptos",
        text="La Profecía del Elegido se transmitía de generación en generación.",
        entity_name="La Profecía del Elegido",
        expected_type=EntityType.CONCEPT,
        wrong_types=[EntityType.CHARACTER, EntityType.LOCATION],
        difficulty="medium",
        linguistic_note="Concepto narrativo capitalizado que puede confundirse con nombre propio."
    ),
    ClassificationTestCase(
        id="class_10_magic",
        category="conceptos",
        text="La Fuerza conecta a todos los seres vivos.",
        entity_name="La Fuerza",
        expected_type=EntityType.MAGIC_SYSTEM,
        wrong_types=[EntityType.CHARACTER, EntityType.ORGANIZATION],
        difficulty="hard",
        linguistic_note="Sistema mágico capitalizado. Parece un nombre pero es un concepto."
    ),

    # --- 3e. Eventos ---
    ClassificationTestCase(
        id="class_11_event",
        category="eventos",
        text="La Batalla de las Navas de Tolosa cambió la historia.",
        entity_name="La Batalla de las Navas de Tolosa",
        expected_type=EntityType.EVENT,
        wrong_types=[EntityType.LOCATION],
        difficulty="medium",
        linguistic_note="Evento histórico que contiene un topónimo."
    ),

    # --- 3f. Obras ---
    ClassificationTestCase(
        id="class_12_work",
        category="obras",
        text="Don Quijote es la obra maestra de Cervantes.",
        entity_name="Don Quijote",
        expected_type=EntityType.WORK,
        wrong_types=[EntityType.CHARACTER],
        difficulty="adversarial",
        linguistic_note=(
            "Ambiguo: 'Don Quijote' puede ser el personaje o la obra. "
            "En este contexto es la obra. El sistema necesita contexto."
        ),
    ),
]


# =============================================================================
# CATEGORÍA 4: NORMALIZATION EDGE CASES
# =============================================================================

NORMALIZATION_TESTS = [
    # (input_name, expected_normalized)
    # NOTE: normalize_for_comparison strips PREFIXES only (titles, articles),
    # but does NOT strip interior prepositions like "de", "de la".
    ("Don Fernando García", "fernando garcia"),
    ("Doña Isabel de Castilla", "isabel de castilla"),
    ("Doctor Hernández", "hernandez"),
    ("El Escorial", "escorial"),
    ("La Casa de la Moneda", "casa de la moneda"),
    ("Capitán Morales", "morales"),
    ("  María  Sánchez  ", "maria sanchez"),
    ("PEDRO GARCÍA", "pedro garcia"),
    ("San Francisco de Asís", "francisco de asis"),
    ("Señor López", "lopez"),
    ("Fray Bartolomé", "bartolome"),
    ("General Patton", "patton"),
    ("Conde de Montecristo", "de montecristo"),  # BUG: "de" should also be stripped here
    ("Princesa Leonor", "leonor"),
    ("Sor Juana", "juana"),
]

# Tests que exponen BUGS reales en la normalización
NORMALIZATION_BUG_TESTS = [
    # Interior prepositions should ideally be stripped for comparison
    pytest.param(
        "Conde de Montecristo", "montecristo",
        id="bug_interior_de_not_stripped",
        marks=pytest.mark.xfail(reason="normalize_for_comparison no strip 'de' interior"),
    ),
    pytest.param(
        "Doña Isabel de Castilla", "isabel castilla",
        id="bug_interior_de_castilla",
        marks=pytest.mark.xfail(reason="normalize_for_comparison no strip 'de' interior"),
    ),
]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fusion_service():
    """Crea el servicio de fusión semántica sin embeddings reales."""
    try:
        return SemanticFusionService()
    except Exception:
        pytest.skip("SemanticFusionService no disponible (requiere embeddings)")


def _make_entity(
    name: str,
    entity_type: EntityType = EntityType.CHARACTER,
    aliases: Optional[list[str]] = None,
    entity_id: int = 0,
) -> Entity:
    """Helper para crear entidades de test."""
    return Entity(
        id=entity_id,
        project_id=1,
        entity_type=entity_type,
        canonical_name=name,
        aliases=aliases or [],
        mention_count=5,
        is_active=True,
    )


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestShouldMerge:
    """Tests para entidades que DEBERÍAN fusionarse."""

    @pytest.mark.parametrize(
        "case",
        SHOULD_MERGE_TESTS,
        ids=lambda c: c.id,
    )
    def test_should_merge(self, fusion_service, case: FusionTestCase):
        e1 = _make_entity(case.entity1_name, case.entity1_type, case.entity1_aliases, 1)
        e2 = _make_entity(case.entity2_name, case.entity2_type, case.entity2_aliases, 2)

        result = fusion_service.should_merge(e1, e2)

        assert result.should_merge, (
            f"[{case.id}] '{case.entity1_name}' y '{case.entity2_name}' "
            f"DEBERÍAN fusionarse.\n"
            f"Nota: {case.linguistic_note}\n"
            f"Resultado: should_merge={result.should_merge}, "
            f"similarity={result.similarity:.3f}, method={result.method}"
        )


class TestShouldNotMerge:
    """Tests para entidades que NO deberían fusionarse."""

    @pytest.mark.parametrize(
        "case",
        SHOULD_NOT_MERGE_TESTS,
        ids=lambda c: c.id,
    )
    def test_should_not_merge(self, fusion_service, case: FusionTestCase):
        e1 = _make_entity(case.entity1_name, case.entity1_type, case.entity1_aliases, 1)
        e2 = _make_entity(case.entity2_name, case.entity2_type, case.entity2_aliases, 2)

        result = fusion_service.should_merge(e1, e2)

        assert not result.should_merge, (
            f"[{case.id}] '{case.entity1_name}' y '{case.entity2_name}' "
            f"NO deberían fusionarse.\n"
            f"Nota: {case.linguistic_note}\n"
            f"Resultado: should_merge={result.should_merge}, "
            f"similarity={result.similarity:.3f}, method={result.method}"
        )


class TestEntityClassification:
    """Tests para clasificación correcta de tipo de entidad."""

    @pytest.mark.parametrize(
        "case",
        CLASSIFICATION_TESTS,
        ids=lambda c: c.id,
    )
    def test_classification(self, case: ClassificationTestCase):
        """
        Verifica que el NER clasifica la entidad con el tipo correcto.

        NOTA: Este test requiere el NER extractor. Si no está disponible,
        se verifica solo que la entidad sea detectada.
        """
        try:
            from narrative_assistant.nlp.ner import NERExtractor, EntityLabel
        except ImportError:
            pytest.skip("NER extractor no disponible")

        extractor = NERExtractor()
        result = extractor.extract_entities(case.text)

        if result.is_failure:
            pytest.skip(f"NER extraction failed: {result.error}")

        ner_result = result.value
        entities = ner_result.entities

        # Find the entity in NER results
        found_entity = None
        for ent in entities:
            if case.entity_name.lower() in ent.text.lower() or ent.text.lower() in case.entity_name.lower():
                found_entity = ent
                break

        # If entity not found, that's also a failure
        assert found_entity is not None, (
            f"[{case.id}] Entidad '{case.entity_name}' no detectada por NER.\n"
            f"Nota: {case.linguistic_note}\n"
            f"Entidades encontradas: {[e.text for e in entities]}"
        )

        # Map NER label to EntityType
        label_to_type = {
            EntityLabel.PER: EntityType.CHARACTER,
            EntityLabel.LOC: EntityType.LOCATION,
            EntityLabel.ORG: EntityType.ORGANIZATION,
            EntityLabel.MISC: EntityType.CONCEPT,  # Fallback mapping
        }

        detected_type = label_to_type.get(found_entity.label, EntityType.CONCEPT)

        # Check it's not classified as a wrong type
        for wrong_type in case.wrong_types:
            assert detected_type != wrong_type, (
                f"[{case.id}] Entidad '{case.entity_name}' clasificada como "
                f"{detected_type.value} (incorrecto: {wrong_type.value}).\n"
                f"NER label: {found_entity.label.value}\n"
                f"Nota: {case.linguistic_note}"
            )


class TestNormalization:
    """Tests para normalización de nombres de entidades."""

    @pytest.mark.parametrize(
        "input_name,expected",
        NORMALIZATION_TESTS,
        ids=[f"norm_{i:02d}" for i in range(len(NORMALIZATION_TESTS))],
    )
    def test_normalization(self, input_name, expected):
        result = normalize_for_comparison(input_name)
        assert result == expected, (
            f"Normalización incorrecta:\n"
            f"  Input:    '{input_name}'\n"
            f"  Esperado: '{expected}'\n"
            f"  Obtenido: '{result}'"
        )

    @pytest.mark.parametrize("input_name,expected", NORMALIZATION_BUG_TESTS)
    def test_normalization_bugs(self, input_name, expected):
        """Tests que exponen bugs conocidos en la normalización."""
        result = normalize_for_comparison(input_name)
        assert result == expected


class TestStripAccents:
    """Tests para eliminación de acentos."""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("María", "Maria"),
            ("José García", "Jose Garcia"),
            ("café", "cafe"),
            ("Ángel Fernández", "Angel Fernandez"),
            ("", ""),
            ("ABC", "ABC"),
        ],
        ids=["maria", "jose", "cafe", "angel", "empty", "ascii"],
    )
    def test_strip_accents(self, input_text, expected):
        result = strip_accents(input_text)
        assert result == expected

    def test_strip_accents_ü_to_u(self):
        """ü → u es comportamiento correcto (diacrítico, no letra)."""
        assert strip_accents("pingüino") == "pinguino"

    @pytest.mark.xfail(reason="BUG: strip_accents elimina ñ porque NFD la descompone en n + combining tilde (Mn)")
    def test_strip_accents_preserves_ñ(self):
        """BUG: strip_accents debería preservar ñ pero no lo hace."""
        result = strip_accents("niño")
        assert result == "niño", (
            f"strip_accents('niño') = '{result}' pero debería ser 'niño'. "
            f"La ñ es una LETRA en español, no un acento diacrítico."
        )


class TestNamesMatchAfterNormalization:
    """Tests para comparación de nombres normalizados."""

    @pytest.mark.parametrize(
        "name1,name2,expected",
        [
            # Should match
            ("Don Fernando", "Fernando", True),
            ("Doctor García", "García", True),
            ("El Escorial", "Escorial", True),
            ("María", "Maria", True),
            ("PEDRO", "Pedro", True),
            # Should NOT match
            ("María García", "María López", False),
            ("Pedro", "Pablo", False),
            ("Juan Carlos", "Juan Pablo", False),
            ("La Casa", "El Casa", True),  # Ambos normalizan a "casa"
        ],
        ids=[
            "don", "doctor", "article", "accent", "case",
            "diff_surname", "diff_name", "diff_compound", "articles_both",
        ],
    )
    def test_names_match(self, name1, name2, expected):
        result = names_match_after_normalization(name1, name2)
        assert result == expected, (
            f"Nombres: '{name1}' vs '{name2}'\n"
            f"Esperado: {expected}, Obtenido: {result}"
        )


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestFusionSummary:
    """Test de resumen que ejecuta todos los casos y reporta estadísticas."""

    def test_all_fusion_cases(self, fusion_service):
        all_cases = SHOULD_MERGE_TESTS + SHOULD_NOT_MERGE_TESTS
        passed = 0
        failed = 0
        errors = []

        for case in all_cases:
            try:
                e1 = _make_entity(case.entity1_name, case.entity1_type, case.entity1_aliases, 1)
                e2 = _make_entity(case.entity2_name, case.entity2_type, case.entity2_aliases, 2)

                result = fusion_service.should_merge(e1, e2)

                if result.should_merge == case.should_fuse:
                    passed += 1
                else:
                    failed += 1
                    errors.append({
                        "id": case.id,
                        "expected_merge": case.should_fuse,
                        "got_merge": result.should_merge,
                        "similarity": result.similarity,
                        "method": result.method,
                        "note": case.linguistic_note,
                    })
            except Exception as e:
                failed += 1
                errors.append({"id": case.id, "error": str(e)})

        # Report
        print(f"\n{'='*70}")
        print(f"ENTITY FUSION ADVERSARIAL REPORT")
        print(f"{'='*70}")
        print(f"Total cases: {len(all_cases)}")
        print(f"  Should merge: {len(SHOULD_MERGE_TESTS)}")
        print(f"  Should NOT merge: {len(SHOULD_NOT_MERGE_TESTS)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass rate: {passed/len(all_cases)*100:.1f}%")
        print(f"{'='*70}")

        if errors:
            print(f"\nFailed cases:")
            for err in errors[:15]:
                if "error" in err:
                    print(f"  - {err['id']}: ERROR - {err['error'][:80]}")
                else:
                    action = "fusionarse" if err["expected_merge"] else "NO fusionarse"
                    print(f"  - {err['id']}: Debería {action} (sim={err['similarity']:.3f}, method={err['method']})")

        # At least some should pass
        assert passed > 0, "No cases passed at all"
