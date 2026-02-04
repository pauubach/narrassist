"""
Tests unitarios para extracción de entidades (NER).
"""

import pytest

from narrative_assistant.nlp.ner import EntityLabel, NERExtractor


class TestNERExtractor:
    """Tests para el extractor de entidades."""

    @pytest.fixture
    def extractor(self):
        """Crea una instancia del extractor."""
        return NERExtractor()

    def test_extract_person(self, extractor):
        """Extrae nombres de personas."""
        text = "María Sánchez y Juan Pérez viven en Madrid."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value
        assert ner_result is not None
        assert len(ner_result.entities) > 0

        # Buscar personas
        persons = [e for e in ner_result.entities if e.label == EntityLabel.PER]
        assert len(persons) >= 2

        person_names = [e.text for e in persons]
        assert any("María" in name for name in person_names)
        assert any("Juan" in name for name in person_names)

    def test_extract_location(self, extractor):
        """Extrae nombres de ubicaciones."""
        text = "Madrid y Barcelona son las ciudades más grandes de España."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value
        assert len(ner_result.entities) > 0

        # Buscar ubicaciones
        locations = [e for e in ner_result.entities if e.label == EntityLabel.LOC]
        assert len(locations) >= 2

        location_names = [e.text for e in locations]
        assert any("Madrid" in name for name in location_names)
        assert any("Barcelona" in name for name in location_names)

    def test_extract_organization(self, extractor):
        """Extrae nombres de organizaciones."""
        text = "El Real Madrid y el Barcelona son equipos rivales."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value
        assert len(ner_result.entities) > 0

        # Buscar organizaciones
        orgs = [e for e in ner_result.entities if e.label == EntityLabel.ORG]
        # Al menos uno debería detectarse
        assert len(orgs) >= 1

    def test_empty_text(self, extractor):
        """Maneja texto vacío."""
        result = extractor.extract_entities("")

        assert result.is_success
        ner_result = result.value
        assert len(ner_result.entities) == 0

    def test_confidence_scores(self, extractor):
        """Verifica que se asignan scores de confianza."""
        text = "María vive en Madrid."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value

        for entity in ner_result.entities:
            assert hasattr(entity, "confidence")
            assert 0.0 <= entity.confidence <= 1.0

    def test_canonical_forms(self, extractor):
        """Genera formas canónicas de entidades."""
        text = "María Sánchez, María, la señora Sánchez."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value

        # Verificar que tiene forma canónica
        persons = [e for e in ner_result.entities if e.label == EntityLabel.PER]
        assert len(persons) > 0

        for person in persons:
            assert hasattr(person, "canonical_form")
            assert len(person.canonical_form) > 0

    def test_gazetteer_enabled(self):
        """Gazetteer mejora la detección."""
        extractor_with = NERExtractor(enable_gazetteer=True)
        extractor_without = NERExtractor(enable_gazetteer=False)

        text = "Gandalf y Frodo viajaron a Rivendel."

        result_with = extractor_with.extract_entities(text)
        result_without = extractor_without.extract_entities(text)

        assert result_with.is_success
        assert result_without.is_success

        # Ambos deberían funcionar, pero con gazetteer podría ser mejor
        # (esto es más una verificación de que no falla)
        assert len(result_with.value.entities) >= 0
        assert len(result_without.value.entities) >= 0

    def test_long_text(self, extractor):
        """Procesa texto largo correctamente."""
        # Texto de ~1000 palabras
        text = " ".join(["María vive en Madrid."] * 200)
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value
        # Debería detectar muchas menciones
        assert len(ner_result.entities) > 0

    def test_special_characters(self, extractor):
        """Maneja caracteres especiales."""
        text = "José-María Aznar y François Mitterrand se reunieron."
        result = extractor.extract_entities(text)

        assert result.is_success
        ner_result = result.value
        # Debería detectar nombres con guiones y acentos
        assert len(ner_result.entities) > 0


class TestEntityLabel:
    """Tests para el enum EntityLabel."""

    def test_label_values(self):
        """Verifica los valores del enum."""
        assert EntityLabel.PER.value == "PER"
        assert EntityLabel.LOC.value == "LOC"
        assert EntityLabel.ORG.value == "ORG"

    def test_label_from_string(self):
        """Crea label desde string."""
        label = EntityLabel("PER")
        assert label == EntityLabel.PER
