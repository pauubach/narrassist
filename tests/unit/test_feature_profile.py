"""
Tests para el módulo de perfiles de features por tipo de documento.
"""

import pytest

from narrative_assistant.feature_profile.models import (
    DOCUMENT_SUBTYPES,
    DOCUMENT_TYPES,
    PROFILE_CREATORS,
    DocumentType,
    FeatureAvailability,
    FeatureProfile,
    create_feature_profile,
)

# =============================================================================
# Tests de Enums
# =============================================================================


class TestDocumentType:
    """Tests para DocumentType enum."""

    def test_all_document_types_defined(self):
        """Verifica que todos los tipos de documento están definidos."""
        expected_types = [
            "FICTION",
            "MEMOIR",
            "BIOGRAPHY",
            "CELEBRITY",
            "DIVULGATION",
            "ESSAY",
            "SELF_HELP",
            "TECHNICAL",
            "PRACTICAL",
            "GRAPHIC",
            "CHILDREN",
            "DRAMA",
        ]
        for type_name in expected_types:
            assert hasattr(DocumentType, type_name)

    def test_document_type_values(self):
        """Verifica valores de los tipos."""
        assert DocumentType.FICTION.value == "FIC"
        assert DocumentType.MEMOIR.value == "MEM"
        assert DocumentType.BIOGRAPHY.value == "BIO"
        assert DocumentType.CELEBRITY.value == "CEL"
        assert DocumentType.DIVULGATION.value == "DIV"
        assert DocumentType.ESSAY.value == "ENS"
        assert DocumentType.SELF_HELP.value == "AUT"
        assert DocumentType.TECHNICAL.value == "TEC"
        assert DocumentType.PRACTICAL.value == "PRA"
        assert DocumentType.GRAPHIC.value == "GRA"
        assert DocumentType.CHILDREN.value == "INF"
        assert DocumentType.DRAMA.value == "DRA"

    def test_document_type_count(self):
        """Verifica número de tipos de documento."""
        assert len(DocumentType) == 12


class TestFeatureAvailability:
    """Tests para FeatureAvailability enum."""

    def test_all_availabilities_defined(self):
        """Verifica que todos los niveles están definidos."""
        expected = ["ENABLED", "OPTIONAL", "DISABLED"]
        for avail in expected:
            assert hasattr(FeatureAvailability, avail)

    def test_availability_values(self):
        """Verifica valores de disponibilidad."""
        assert FeatureAvailability.ENABLED.value == "enabled"
        assert FeatureAvailability.OPTIONAL.value == "optional"
        assert FeatureAvailability.DISABLED.value == "disabled"


# =============================================================================
# Tests de Constantes
# =============================================================================


class TestDocumentTypesInfo:
    """Tests para información de tipos de documento."""

    def test_all_types_have_info(self):
        """Verifica que todos los tipos tienen información."""
        for doc_type in DocumentType:
            assert doc_type in DOCUMENT_TYPES
            info = DOCUMENT_TYPES[doc_type]
            assert "name" in info
            assert "description" in info
            assert "icon" in info
            assert "color" in info

    def test_info_fields_not_empty(self):
        """Verifica que los campos de información no están vacíos."""
        for doc_type, info in DOCUMENT_TYPES.items():
            assert info["name"], f"Name vacío para {doc_type}"
            assert info["description"], f"Description vacío para {doc_type}"
            assert info["icon"].startswith("pi-"), f"Icon inválido para {doc_type}"
            assert info["color"].startswith("#"), f"Color inválido para {doc_type}"

    def test_fiction_info(self):
        """Verifica información de ficción."""
        info = DOCUMENT_TYPES[DocumentType.FICTION]
        assert info["name"] == "Ficción narrativa"
        assert info["icon"] == "pi-book"
        assert "novela" in info["description"].lower()


class TestDocumentSubtypes:
    """Tests para subtipos de documento."""

    def test_all_types_have_subtypes(self):
        """Verifica que todos los tipos tienen subtipos."""
        for doc_type in DocumentType:
            assert doc_type in DOCUMENT_SUBTYPES
            subtypes = DOCUMENT_SUBTYPES[doc_type]
            assert isinstance(subtypes, list)
            assert len(subtypes) > 0

    def test_subtype_structure(self):
        """Verifica estructura de subtipos."""
        for doc_type, subtypes in DOCUMENT_SUBTYPES.items():
            for subtype in subtypes:
                assert "code" in subtype
                assert "name" in subtype
                # El código debería empezar con el código del tipo padre
                type_prefix = doc_type.value
                assert subtype["code"].startswith(type_prefix), (
                    f"Subtipo {subtype['code']} no empieza con {type_prefix}"
                )

    def test_fiction_subtypes(self):
        """Verifica subtipos de ficción."""
        subtypes = DOCUMENT_SUBTYPES[DocumentType.FICTION]
        codes = [s["code"] for s in subtypes]
        assert "FIC_LIT" in codes
        assert "FIC_GEN" in codes
        assert "FIC_HIS" in codes
        assert "FIC_COR" in codes
        assert "FIC_MIC" in codes

    def test_children_subtypes_age_ranges(self):
        """Verifica subtipos infantiles por edades."""
        subtypes = DOCUMENT_SUBTYPES[DocumentType.CHILDREN]
        codes = [s["code"] for s in subtypes]
        # Debe cubrir todas las edades
        assert "INF_CAR" in codes  # 0-3 años
        assert "INF_ALB" in codes  # 3-5 años
        assert "INF_PRI" in codes  # 5-8 años
        assert "INF_CAP" in codes  # 6-10 años
        assert "INF_MID" in codes  # 8-12 años
        assert "INF_YA" in codes  # 12+ años


# =============================================================================
# Tests de FeatureProfile
# =============================================================================


class TestFeatureProfile:
    """Tests para FeatureProfile dataclass."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        profile = FeatureProfile(document_type=DocumentType.FICTION)
        assert profile.document_type == DocumentType.FICTION
        assert profile.document_subtype is None
        # Por defecto, la mayoría están enabled
        assert profile.characters == FeatureAvailability.ENABLED
        assert profile.relationships == FeatureAvailability.ENABLED
        assert profile.timeline == FeatureAvailability.ENABLED
        assert profile.pacing == FeatureAvailability.ENABLED
        # Age readability está disabled por defecto
        assert profile.age_readability == FeatureAvailability.DISABLED

    def test_custom_values(self):
        """Verifica valores personalizados."""
        profile = FeatureProfile(
            document_type=DocumentType.ESSAY,
            characters=FeatureAvailability.DISABLED,
            timeline=FeatureAvailability.OPTIONAL,
        )
        assert profile.characters == FeatureAvailability.DISABLED
        assert profile.timeline == FeatureAvailability.OPTIONAL

    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        profile = FeatureProfile(
            document_type=DocumentType.FICTION,
            document_subtype="FIC_LIT",
        )
        d = profile.to_dict()

        assert d["document_type"] == "FIC"
        assert d["document_subtype"] == "FIC_LIT"
        assert "type_info" in d
        assert "features" in d
        assert d["features"]["characters"] == "enabled"

    def test_is_enabled(self):
        """Verifica método is_enabled."""
        profile = FeatureProfile(
            document_type=DocumentType.FICTION,
            characters=FeatureAvailability.ENABLED,
            timeline=FeatureAvailability.OPTIONAL,
            scenes=FeatureAvailability.DISABLED,
        )
        assert profile.is_enabled("characters") is True
        assert profile.is_enabled("timeline") is False  # Optional != Enabled
        assert profile.is_enabled("scenes") is False
        assert profile.is_enabled("nonexistent") is False

    def test_is_available(self):
        """Verifica método is_available."""
        profile = FeatureProfile(
            document_type=DocumentType.FICTION,
            characters=FeatureAvailability.ENABLED,
            timeline=FeatureAvailability.OPTIONAL,
            scenes=FeatureAvailability.DISABLED,
        )
        assert profile.is_available("characters") is True
        assert profile.is_available("timeline") is True  # Optional = disponible
        assert profile.is_available("scenes") is False
        assert profile.is_available("nonexistent") is False


# =============================================================================
# Tests de Profile Creators
# =============================================================================


class TestProfileCreators:
    """Tests para funciones de creación de perfiles."""

    def test_all_types_have_creators(self):
        """Verifica que todos los tipos tienen creador."""
        for doc_type in DocumentType:
            assert doc_type in PROFILE_CREATORS
            creator = PROFILE_CREATORS[doc_type]
            assert callable(creator)

    def test_fiction_profile(self):
        """Verifica perfil de ficción (todas las features)."""
        profile = create_feature_profile(DocumentType.FICTION)
        assert profile.document_type == DocumentType.FICTION
        # Ficción tiene todas las features de estructura narrativa
        assert profile.characters == FeatureAvailability.ENABLED
        assert profile.relationships == FeatureAvailability.ENABLED
        assert profile.timeline == FeatureAvailability.ENABLED
        assert profile.scenes == FeatureAvailability.ENABLED
        assert profile.pov_focalization == FeatureAvailability.ENABLED

    def test_essay_profile(self):
        """Verifica perfil de ensayo (features narrativas desactivadas)."""
        profile = create_feature_profile(DocumentType.ESSAY)
        assert profile.document_type == DocumentType.ESSAY
        # Ensayo no tiene personajes ni timeline
        assert profile.characters == FeatureAvailability.DISABLED
        assert profile.relationships == FeatureAvailability.DISABLED
        assert profile.timeline == FeatureAvailability.DISABLED
        assert profile.scenes == FeatureAvailability.DISABLED
        # Pero tiene features de estilo
        assert profile.sticky_sentences == FeatureAvailability.ENABLED

    def test_technical_profile(self):
        """Verifica perfil de manual técnico."""
        profile = create_feature_profile(DocumentType.TECHNICAL)
        assert profile.document_type == DocumentType.TECHNICAL
        # Muy pocas features narrativas
        assert profile.characters == FeatureAvailability.DISABLED
        assert profile.pacing == FeatureAvailability.DISABLED
        assert profile.emotional_analysis == FeatureAvailability.DISABLED
        # Pero terminología y glosario son importantes
        assert profile.terminology == FeatureAvailability.ENABLED
        assert profile.glossary == FeatureAvailability.ENABLED

    def test_children_profile(self):
        """Verifica perfil de literatura infantil."""
        profile = create_feature_profile(DocumentType.CHILDREN)
        assert profile.document_type == DocumentType.CHILDREN
        # Tiene age_readability activo (único tipo)
        assert profile.age_readability == FeatureAvailability.ENABLED
        # Las demás features de narrativa disponibles
        assert profile.characters == FeatureAvailability.ENABLED

    def test_drama_profile(self):
        """Verifica perfil de teatro/guion."""
        profile = create_feature_profile(DocumentType.DRAMA)
        assert profile.document_type == DocumentType.DRAMA
        # Sin focalización (no aplica a teatro)
        assert profile.pov_focalization == FeatureAvailability.DISABLED
        # Escenas son importantes
        assert profile.scenes == FeatureAvailability.ENABLED

    def test_memoir_profile(self):
        """Verifica perfil de memorias."""
        profile = create_feature_profile(DocumentType.MEMOIR)
        assert profile.document_type == DocumentType.MEMOIR
        # Escenas y voice_profiles opcionales
        assert profile.scenes == FeatureAvailability.OPTIONAL
        assert profile.voice_profiles == FeatureAvailability.OPTIONAL

    def test_biography_profile(self):
        """Verifica perfil de biografía."""
        profile = create_feature_profile(DocumentType.BIOGRAPHY)
        assert profile.document_type == DocumentType.BIOGRAPHY
        # Sin diálogos ficticios
        assert profile.voice_profiles == FeatureAvailability.DISABLED

    def test_graphic_profile(self):
        """Verifica perfil de novela gráfica."""
        profile = create_feature_profile(DocumentType.GRAPHIC)
        assert profile.document_type == DocumentType.GRAPHIC
        # Poco texto, algunas features limitadas
        assert profile.sentence_variation == FeatureAvailability.DISABLED


# =============================================================================
# Tests de create_feature_profile
# =============================================================================


class TestCreateFeatureProfile:
    """Tests para función create_feature_profile."""

    def test_basic_creation(self):
        """Verifica creación básica."""
        profile = create_feature_profile(DocumentType.FICTION)
        assert profile.document_type == DocumentType.FICTION
        assert profile.document_subtype is None

    def test_creation_with_subtype(self):
        """Verifica creación con subtipo."""
        profile = create_feature_profile(DocumentType.FICTION, "FIC_HIS")
        assert profile.document_type == DocumentType.FICTION
        assert profile.document_subtype == "FIC_HIS"

    def test_invalid_subtype_ignored(self):
        """Verifica que subtipo inválido es ignorado (no lanza error)."""
        # La función no valida subtipos, solo los asigna
        profile = create_feature_profile(DocumentType.FICTION, "INVALID")
        assert profile.document_subtype == "INVALID"


# =============================================================================
# Tests de Subtype Adjustments
# =============================================================================


class TestSubtypeAdjustments:
    """Tests para ajustes por subtipo."""

    def test_children_cartone_adjustments(self):
        """Verifica ajustes para cartoné (0-3 años)."""
        profile = create_feature_profile(DocumentType.CHILDREN, "INF_CAR")
        # Muy poco texto
        assert profile.sticky_sentences == FeatureAvailability.DISABLED
        assert profile.sentence_variation == FeatureAvailability.DISABLED
        assert profile.scenes == FeatureAvailability.DISABLED
        assert profile.pacing == FeatureAvailability.DISABLED

    def test_children_album_adjustments(self):
        """Verifica ajustes para álbum ilustrado (3-5 años)."""
        profile = create_feature_profile(DocumentType.CHILDREN, "INF_ALB")
        # Similar a cartoné
        assert profile.sticky_sentences == FeatureAvailability.DISABLED
        assert profile.timeline == FeatureAvailability.DISABLED

    def test_children_middle_grade_adjustments(self):
        """Verifica ajustes para middle grade (8-12 años)."""
        profile = create_feature_profile(DocumentType.CHILDREN, "INF_MID")
        # Casi como adulto
        assert profile.scenes == FeatureAvailability.ENABLED
        assert profile.timeline == FeatureAvailability.ENABLED

    def test_children_young_adult_adjustments(self):
        """Verifica ajustes para young adult (12+ años)."""
        profile = create_feature_profile(DocumentType.CHILDREN, "INF_YA")
        # Como adulto
        assert profile.scenes == FeatureAvailability.ENABLED
        assert profile.timeline == FeatureAvailability.ENABLED

    def test_fiction_historical_adjustments(self):
        """Verifica ajustes para novela histórica."""
        profile = create_feature_profile(DocumentType.FICTION, "FIC_HIS")
        # Terminología de época importante
        assert profile.terminology == FeatureAvailability.ENABLED
        assert profile.glossary == FeatureAvailability.ENABLED

    def test_fiction_microrrelato_adjustments(self):
        """Verifica ajustes para microrrelatos."""
        profile = create_feature_profile(DocumentType.FICTION, "FIC_MIC")
        # Texto muy corto
        assert profile.scenes == FeatureAvailability.DISABLED
        assert profile.timeline == FeatureAvailability.OPTIONAL
        assert profile.pacing == FeatureAvailability.OPTIONAL

    def test_graphic_manga_adjustments(self):
        """Verifica ajustes para manga."""
        profile = create_feature_profile(DocumentType.GRAPHIC, "GRA_MAN")
        # Manga tiene más texto que cómic occidental
        assert profile.sentence_variation == FeatureAvailability.OPTIONAL


# =============================================================================
# Tests de Integración
# =============================================================================


class TestFeatureProfileIntegration:
    """Tests de integración para perfiles de features."""

    def test_all_profiles_serializable(self):
        """Verifica que todos los perfiles son serializables."""
        for doc_type in DocumentType:
            profile = create_feature_profile(doc_type)
            d = profile.to_dict()
            assert isinstance(d, dict)
            assert "document_type" in d
            assert "features" in d

    def test_profile_features_complete(self):
        """Verifica que todos los perfiles tienen todas las features."""
        expected_features = [
            "characters",
            "relationships",
            "timeline",
            "scenes",
            "pov_focalization",
            "pacing",
            "register_analysis",
            "voice_profiles",
            "sticky_sentences",
            "echo_repetitions",
            "sentence_variation",
            "emotional_analysis",
            "age_readability",
            "attribute_consistency",
            "world_consistency",
            "glossary",
            "terminology",
            "editorial_rules",
        ]
        for doc_type in DocumentType:
            profile = create_feature_profile(doc_type)
            features = profile.to_dict()["features"]
            for feat in expected_features:
                assert feat in features, f"Feature {feat} missing in {doc_type}"

    def test_only_children_has_age_readability(self):
        """Verifica que solo infantil tiene age_readability activo por defecto."""
        for doc_type in DocumentType:
            profile = create_feature_profile(doc_type)
            if doc_type == DocumentType.CHILDREN:
                assert profile.age_readability == FeatureAvailability.ENABLED
            else:
                assert profile.age_readability == FeatureAvailability.DISABLED

    def test_narrative_types_have_characters(self):
        """Verifica que tipos narrativos tienen personajes."""
        narrative_types = [
            DocumentType.FICTION,
            DocumentType.MEMOIR,
            DocumentType.BIOGRAPHY,
            DocumentType.CHILDREN,
            DocumentType.DRAMA,
            DocumentType.GRAPHIC,
        ]
        for doc_type in narrative_types:
            profile = create_feature_profile(doc_type)
            assert profile.is_available("characters"), f"{doc_type} should have characters"

    def test_non_narrative_types_no_characters(self):
        """Verifica que tipos no narrativos no tienen personajes."""
        non_narrative = [
            DocumentType.ESSAY,
            DocumentType.SELF_HELP,
            DocumentType.TECHNICAL,
            DocumentType.PRACTICAL,
        ]
        for doc_type in non_narrative:
            profile = create_feature_profile(doc_type)
            assert not profile.is_enabled("characters"), (
                f"{doc_type} should not have characters enabled"
            )


class TestFeatureProfileEdgeCases:
    """Tests de casos límite."""

    def test_profile_with_all_disabled(self):
        """Verifica perfil con todo deshabilitado."""
        profile = FeatureProfile(
            document_type=DocumentType.ESSAY,
            characters=FeatureAvailability.DISABLED,
            relationships=FeatureAvailability.DISABLED,
            timeline=FeatureAvailability.DISABLED,
            scenes=FeatureAvailability.DISABLED,
            pov_focalization=FeatureAvailability.DISABLED,
            pacing=FeatureAvailability.DISABLED,
        )
        # Verificar que is_enabled y is_available funcionan
        assert not profile.is_enabled("characters")
        assert not profile.is_available("characters")

    def test_profile_with_all_optional(self):
        """Verifica perfil con todo opcional."""
        profile = FeatureProfile(
            document_type=DocumentType.GRAPHIC,
            characters=FeatureAvailability.OPTIONAL,
            scenes=FeatureAvailability.OPTIONAL,
        )
        # Optional no es enabled pero sí available
        assert not profile.is_enabled("characters")
        assert profile.is_available("characters")

    def test_subtype_code_validation_format(self):
        """Verifica formato de códigos de subtipo."""
        for doc_type, subtypes in DOCUMENT_SUBTYPES.items():
            for subtype in subtypes:
                code = subtype["code"]
                # Código debe tener formato: TYPE_XXX (3 letras + _ + 2-3 letras)
                parts = code.split("_")
                assert len(parts) == 2, f"Código inválido: {code}"
                assert len(parts[0]) == 3, f"Prefijo inválido: {code}"
                assert 2 <= len(parts[1]) <= 3, f"Sufijo inválido: {code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
