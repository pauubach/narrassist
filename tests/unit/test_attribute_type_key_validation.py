"""Tests ligeros para validación cruzada tipo↔key de atributos (B4).

No requiere spaCy ni modelos pesados — solo instancia AttributeExtractor
con lazy loading (no carga modelos hasta que se llama extract()).
"""

import pytest

from narrative_assistant.nlp.attributes import AttributeExtractor


class TestTypeKeyCompatibility:
    """Tests para validación cruzada tipo↔key (B4)."""

    @pytest.fixture
    def extractor(self):
        return AttributeExtractor(filter_metaphors=False)

    def test_person_key_rejected_for_location(self, extractor):
        """eye_color es incompatible con LOC."""
        assert not extractor._is_key_compatible_with_type("eye_color", "LOC")
        assert not extractor._is_key_compatible_with_type("hair_color", "LOC")
        assert not extractor._is_key_compatible_with_type("personality", "LOCATION")

    def test_person_key_rejected_for_object(self, extractor):
        """build es incompatible con OBJECT."""
        assert not extractor._is_key_compatible_with_type("build", "OBJECT")
        assert not extractor._is_key_compatible_with_type("fear", "OBJECT")

    def test_location_key_rejected_for_person(self, extractor):
        """climate es incompatible con PER."""
        assert not extractor._is_key_compatible_with_type("climate", "PER")
        assert not extractor._is_key_compatible_with_type("terrain", "CHARACTER")

    def test_compatible_combinations_pass(self, extractor):
        """Combinaciones válidas pasan."""
        assert extractor._is_key_compatible_with_type("climate", "LOC")
        assert extractor._is_key_compatible_with_type("eye_color", "PER")
        assert extractor._is_key_compatible_with_type("material", "OBJECT")
        assert extractor._is_key_compatible_with_type("profession", "CHARACTER")

    def test_shared_keys_pass_for_all_types(self, extractor):
        """Keys compartidas (size, color, condition) son válidas para todo tipo."""
        for entity_type in ("PER", "LOC", "OBJECT"):
            assert extractor._is_key_compatible_with_type("size", entity_type)
            assert extractor._is_key_compatible_with_type("color", entity_type)
            assert extractor._is_key_compatible_with_type("other", entity_type)
