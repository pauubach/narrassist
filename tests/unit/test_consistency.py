"""
Tests unitarios para análisis de consistencia de atributos.
"""

import pytest

from narrative_assistant.analysis.attribute_consistency import (
    AttributeConsistencyChecker,
    AttributeInconsistency,
    InconsistencyType,
)
from narrative_assistant.nlp.attributes import (
    AttributeCategory,
    AttributeKey,
    ExtractedAttribute,
)


class TestAttributeConsistencyChecker:
    """Tests para el verificador de consistencia de atributos."""

    @pytest.fixture
    def checker(self):
        """Crea una instancia del checker."""
        return AttributeConsistencyChecker()

    def test_detect_eye_color_inconsistency(self, checker):
        """Detecta inconsistencia en color de ojos."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="azules",
                source_text="Sus ojos azules brillaban",
                start_char=0,
                end_char=25,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="verdes",
                source_text="Sus ojos verdes miraban",
                start_char=500,
                end_char=523,
                confidence=0.9,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(
            attributes,
        )

        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) > 0

        # Buscar inconsistencia de color de ojos
        eye_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.EYE_COLOR]
        assert len(eye_incon) > 0
        assert eye_incon[0].entity_name == "María"

    def test_no_inconsistency_same_value(self, checker):
        """No detecta inconsistencia cuando los valores son iguales."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="azules",
                source_text="ojos azules",
                start_char=0,
                end_char=11,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="azules",
                source_text="sus ojos azules",
                start_char=500,
                end_char=515,
                confidence=0.9,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(
            attributes,
        )

        assert result.is_success
        inconsistencies = result.value
        # No debería haber inconsistencias
        eye_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.EYE_COLOR]
        assert len(eye_incon) == 0

    def test_empty_attributes(self, checker):
        """Maneja lista vacía de atributos."""
        result = checker.check_consistency(
            [],
        )

        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) == 0

    def test_single_attribute(self, checker):
        """Maneja un solo atributo (no puede haber inconsistencia)."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="azules",
                source_text="ojos azules",
                start_char=0,
                end_char=11,
                confidence=0.9,
                chapter_id=1,
            ),
        ]

        result = checker.check_consistency(
            attributes,
        )

        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) == 0

    def test_checker_initialization(self, checker):
        """Verifica que el checker se inicializa correctamente."""
        assert checker is not None
        assert hasattr(checker, "check_consistency")

    def test_inconsistency_type(self, checker):
        """Verifica que se asigna un tipo de inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HEIGHT,
                value="alto",
                source_text="era alto",
                start_char=0,
                end_char=8,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HEIGHT,
                value="bajo",
                source_text="era bajo",
                start_char=400,
                end_char=408,
                confidence=0.8,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(
            attributes,
        )

        assert result.is_success
        inconsistencies = result.value
        if len(inconsistencies) > 0:
            assert hasattr(inconsistencies[0], "inconsistency_type")
            assert isinstance(inconsistencies[0].inconsistency_type, InconsistencyType)


class TestAttributeInconsistency:
    """Tests para el modelo de inconsistencia."""

    def test_inconsistency_creation(self):
        """Crea una inconsistencia correctamente."""
        attr1 = ExtractedAttribute(
            entity_name="María",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="azules",
            source_text="ojos azules",
            start_char=0,
            end_char=11,
            confidence=0.9,
            chapter_id=1,
        )
        attr2 = ExtractedAttribute(
            entity_name="María",
            category=AttributeCategory.PHYSICAL,
            key=AttributeKey.EYE_COLOR,
            value="verdes",
            source_text="ojos verdes",
            start_char=500,
            end_char=511,
            confidence=0.9,
            chapter_id=2,
        )

        inconsistency = AttributeInconsistency(
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR,
            value1="azules",
            value1_chapter=1,
            value1_excerpt="ojos azules",
            value2="verdes",
            value2_chapter=2,
            value2_excerpt="ojos verdes",
            inconsistency_type=InconsistencyType.ANTONYM,
            confidence=0.95,
            explanation="Color de ojos inconsistente: azules vs verdes",
        )

        assert inconsistency.entity_name == "María"
        assert inconsistency.entity_id == 1
        assert inconsistency.attribute_key == AttributeKey.EYE_COLOR
        assert inconsistency.inconsistency_type == InconsistencyType.ANTONYM
        assert inconsistency.value1 == "azules"
        assert inconsistency.value2 == "verdes"

    def test_inconsistency_to_dict(self):
        """Verifica serialización a diccionario."""
        inconsistency = AttributeInconsistency(
            entity_name="María",
            entity_id=1,
            attribute_key=AttributeKey.EYE_COLOR,
            value1="azules",
            value1_chapter=1,
            value1_excerpt="ojos azules",
            value2="verdes",
            value2_chapter=2,
            value2_excerpt="ojos verdes",
            inconsistency_type=InconsistencyType.ANTONYM,
            confidence=0.95,
            explanation="Color de ojos inconsistente",
        )

        d = inconsistency.to_dict()
        assert d["entity_name"] == "María"
        assert d["attribute_key"] == "eye_color"
        assert d["inconsistency_type"] == "antonym"


class TestHairConsistency:
    """Tests para inconsistencias de pelo (color y tipo)."""

    @pytest.fixture
    def checker(self):
        """Crea una instancia del checker."""
        return AttributeConsistencyChecker(use_embeddings=False)

    def test_detect_hair_color_inconsistency(self, checker):
        """Detecta inconsistencia en color de pelo."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="negro",
                source_text="cabello largo y negro",
                start_char=0,
                end_char=21,
                confidence=0.85,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="rubio",
                source_text="cabello corto y rubio",
                start_char=500,
                end_char=521,
                confidence=0.85,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        hair_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.HAIR_COLOR]
        assert len(hair_incon) > 0
        assert hair_incon[0].entity_name == "María"
        assert hair_incon[0].value1 == "negro"
        assert hair_incon[0].value2 == "rubio"

    def test_detect_hair_type_inconsistency(self, checker):
        """Detecta inconsistencia en tipo de pelo (largo/corto)."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_TYPE,
                value="largo",
                source_text="cabello largo",
                start_char=0,
                end_char=13,
                confidence=0.85,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_TYPE,
                value="corto",
                source_text="cabello corto",
                start_char=500,
                end_char=513,
                confidence=0.85,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        type_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.HAIR_TYPE]
        assert len(type_incon) > 0
        assert type_incon[0].value1 == "largo"
        assert type_incon[0].value2 == "corto"

    def test_no_inconsistency_hair_synonyms(self, checker):
        """No detecta inconsistencia para sinónimos de pelo (negro/oscuro)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="negro",
                source_text="pelo negro",
                start_char=0,
                end_char=10,
                confidence=0.85,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="oscuro",
                source_text="pelo oscuro",
                start_char=500,
                end_char=511,
                confidence=0.85,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        # negro y oscuro son sinónimos, no debería haber inconsistencia de alta confianza
        hair_incon = [
            i
            for i in inconsistencies
            if i.attribute_key == AttributeKey.HAIR_COLOR and i.confidence >= 0.5
        ]
        assert len(hair_incon) == 0

    def test_multiple_hair_changes_across_chapters(self, checker):
        """Detecta múltiples cambios de pelo a través de capítulos."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="negro",
                source_text="cabello negro",
                start_char=0,
                end_char=13,
                confidence=0.85,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="rubio",
                source_text="cabello rubio",
                start_char=500,
                end_char=513,
                confidence=0.85,
                chapter_id=2,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HAIR_COLOR,
                value="negro",
                source_text="cabello negro de nuevo",
                start_char=1000,
                end_char=1022,
                confidence=0.85,
                chapter_id=3,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        hair_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.HAIR_COLOR]
        # Debería detectar al menos 2 inconsistencias (negro→rubio, rubio→negro)
        assert len(hair_incon) >= 2


class TestBuildConsistency:
    """Tests para inconsistencias de complexión física."""

    @pytest.fixture
    def checker(self):
        return AttributeConsistencyChecker(use_embeddings=False)

    def test_detect_height_inconsistency(self, checker):
        """Detecta inconsistencia en altura (alto/bajo)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HEIGHT,
                value="bajo",
                source_text="era un hombre bajo",
                start_char=0,
                end_char=18,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.HEIGHT,
                value="alto",
                source_text="era muy alto",
                start_char=500,
                end_char=512,
                confidence=0.8,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        height_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.HEIGHT]
        assert len(height_incon) > 0
        # alto/bajo son antónimos, alta confianza
        assert height_incon[0].confidence >= 0.9

    def test_detect_build_inconsistency(self, checker):
        """Detecta inconsistencia en complexión (fornido/delgado)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.BUILD,
                value="fornido",
                source_text="hombre fornido",
                start_char=0,
                end_char=14,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.BUILD,
                value="delgado",
                source_text="hombre delgado",
                start_char=500,
                end_char=514,
                confidence=0.8,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        build_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.BUILD]
        assert len(build_incon) > 0


class TestGenericInconsistencyDetection:
    """Tests para demostrar que el sistema es genérico y funciona con cualquier atributo."""

    @pytest.fixture
    def checker(self):
        # Usar embeddings=False para tests rápidos
        return AttributeConsistencyChecker(use_embeddings=False, min_confidence=0.3)

    def test_generic_attribute_different_values(self, checker):
        """Detecta diferencias genéricas en cualquier atributo."""
        # Usando AttributeKey.OTHER para atributos no predefinidos
        attributes = [
            ExtractedAttribute(
                entity_name="Excalibur",
                category=AttributeCategory.MATERIAL,
                key=AttributeKey.MATERIAL,
                value="oro",
                source_text="espada de oro",
                start_char=0,
                end_char=13,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Excalibur",
                category=AttributeCategory.MATERIAL,
                key=AttributeKey.MATERIAL,
                value="acero",
                source_text="espada de acero",
                start_char=500,
                end_char=515,
                confidence=0.9,
                chapter_id=5,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        # El sistema debería detectar la diferencia aunque no esté en diccionarios
        material_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.MATERIAL]
        assert len(material_incon) > 0

    def test_different_entities_no_cross_inconsistency(self, checker):
        """No detecta inconsistencia entre diferentes entidades."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="azules",
                source_text="ojos azules de María",
                start_char=0,
                end_char=20,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",  # Diferente entidad
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.EYE_COLOR,
                value="verdes",
                source_text="ojos verdes de Juan",
                start_char=500,
                end_char=519,
                confidence=0.9,
                chapter_id=1,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        # No debería haber inconsistencia porque son entidades diferentes
        assert len(inconsistencies) == 0

    def test_detect_facial_hair_inconsistency(self, checker):
        """Detecta inconsistencia en vello facial (barba espesa vs barba rala)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="espesa",
                source_text="con barba espesa",
                start_char=0,
                end_char=16,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="rala",
                source_text="barba rala",
                start_char=500,
                end_char=510,
                confidence=0.8,
                chapter_id=3,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        facial_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.FACIAL_HAIR]
        assert len(facial_incon) > 0
        assert facial_incon[0].entity_name == "Juan"

    def test_no_facial_hair_inconsistency_for_synonyms(self, checker):
        """No detecta inconsistencia cuando son sinónimos (espesa/poblada)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="espesa",
                source_text="barba espesa",
                start_char=0,
                end_char=12,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="poblada",
                source_text="barba poblada",
                start_char=500,
                end_char=513,
                confidence=0.8,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        facial_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.FACIAL_HAIR]
        assert len(facial_incon) == 0

    def test_facial_hair_color_inconsistency(self, checker):
        """Detecta inconsistencia en color de barba (negra vs canosa)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="negra",
                source_text="barba negra",
                start_char=0,
                end_char=11,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="canosa",
                source_text="barba canosa",
                start_char=500,
                end_char=512,
                confidence=0.8,
                chapter_id=2,
            ),
        ]

        result = checker.check_consistency(attributes)

        assert result.is_success
        inconsistencies = result.value
        facial_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.FACIAL_HAIR]
        assert len(facial_incon) > 0

    def test_different_dimensions_no_inconsistency(self, checker):
        """'espesa' (densidad) vs 'canas' (color) → dimensiones distintas, sin inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="espesa",
                source_text="barba espesa",
                start_char=0,
                end_char=12,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.FACIAL_HAIR,
                value="canas",
                source_text="barba con canas",
                start_char=500,
                end_char=515,
                confidence=0.8,
                chapter_id=3,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        facial_incon = [i for i in inconsistencies if i.attribute_key == AttributeKey.FACIAL_HAIR]
        assert len(facial_incon) == 0


class TestDistinctiveFeatureConsistency:
    """Tests para consistencia de rasgos distintivos con sub-matching por región corporal."""

    @pytest.fixture
    def checker(self):
        return AttributeConsistencyChecker(use_embeddings=False)

    def test_nariz_inconsistency_detected(self, checker):
        """'nariz aguileña' vs 'nariz chata' → inconsistencia (misma región)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="nariz aguileña",
                source_text="su nariz aguileña",
                start_char=0,
                end_char=17,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="nariz chata",
                source_text="con nariz chata",
                start_char=500,
                end_char=515,
                confidence=0.8,
                chapter_id=5,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) > 0
        assert inconsistencies[0].entity_name.lower() == "pedro"

    def test_different_regions_no_inconsistency(self, checker):
        """'nariz aguileña' vs 'cicatriz en mejilla' → NO inconsistencia (regiones distintas)."""
        attributes = [
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="nariz aguileña",
                source_text="su nariz aguileña",
                start_char=0,
                end_char=17,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="cicatriz en la mejilla",
                source_text="una cicatriz en la mejilla",
                start_char=500,
                end_char=526,
                confidence=0.8,
                chapter_id=2,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) == 0

    def test_labios_inconsistency_detected(self, checker):
        """'labios gruesos' vs 'labios finos' → inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="Ana",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="labios gruesos",
                source_text="sus labios gruesos",
                start_char=0,
                end_char=18,
                confidence=0.8,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Ana",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.DISTINCTIVE_FEATURE,
                value="labios finos",
                source_text="con labios finos",
                start_char=800,
                end_char=816,
                confidence=0.8,
                chapter_id=8,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) > 0


class TestAgeConsistency:
    """Tests para consistencia de edad real y edad aparente."""

    @pytest.fixture
    def checker(self):
        return AttributeConsistencyChecker()

    def test_real_age_inconsistency(self, checker):
        """Edad real 25 vs 50 → inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.AGE,
                value="25",
                source_text="tenía 25 años",
                start_char=0,
                end_char=14,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.AGE,
                value="50",
                source_text="tenía 50 años",
                start_char=500,
                end_char=514,
                confidence=0.9,
                chapter_id=5,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) > 0
        assert any(i.confidence >= 0.7 for i in inconsistencies)

    def test_real_vs_apparent_no_cross_comparison(self, checker):
        """AGE=25 y APPARENT_AGE=30 → NO deben compararse entre sí."""
        attributes = [
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.AGE,
                value="25",
                source_text="tenía 25 años",
                start_char=0,
                end_char=14,
                confidence=0.9,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Juan",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.APPARENT_AGE,
                value="30",
                source_text="aparentaba unos 30 años",
                start_char=500,
                end_char=523,
                confidence=0.8,
                chapter_id=3,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        # No debería haber inconsistencia al cruzar age vs apparent_age
        assert len(inconsistencies) == 0

    def test_apparent_age_inconsistency_descriptive(self, checker):
        """'joven' vs 'anciano' en APPARENT_AGE → inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.APPARENT_AGE,
                value="joven",
                source_text="era joven",
                start_char=0,
                end_char=9,
                confidence=0.7,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="María",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.APPARENT_AGE,
                value="anciano",
                source_text="parecía anciana",
                start_char=800,
                end_char=815,
                confidence=0.7,
                chapter_id=8,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) > 0
        assert any(i.confidence >= 0.7 for i in inconsistencies)

    def test_compatible_descriptors_no_inconsistency(self, checker):
        """'joven' y 'veinteañero' son compatibles → sin inconsistencia."""
        attributes = [
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.APPARENT_AGE,
                value="joven",
                source_text="era joven",
                start_char=0,
                end_char=9,
                confidence=0.7,
                chapter_id=1,
            ),
            ExtractedAttribute(
                entity_name="Pedro",
                category=AttributeCategory.PHYSICAL,
                key=AttributeKey.APPARENT_AGE,
                value="veinteañero",
                source_text="un veinteañero",
                start_char=300,
                end_char=314,
                confidence=0.7,
                chapter_id=3,
            ),
        ]
        result = checker.check_consistency(attributes)
        assert result.is_success
        inconsistencies = result.value
        assert len(inconsistencies) == 0
