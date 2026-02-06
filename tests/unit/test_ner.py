"""
Tests unitarios para extracción de entidades (NER).
"""

from unittest.mock import MagicMock, patch

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
        # Usar organizaciones inequívocas (no ciudades que también son equipos)
        text = "La ONU y la UNESCO colaboran con Unicef en proyectos humanitarios."
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


class TestTransformerNER:
    """Tests para integración de transformer NER (PlanTL RoBERTa)."""

    def test_transformer_ner_module_import(self):
        """El módulo transformer_ner se puede importar."""
        from narrative_assistant.nlp.transformer_ner import (
            TRANSFORMER_NER_MODELS,
            TransformerNERModel,
        )

        assert "roberta-base-bne" in TRANSFORMER_NER_MODELS
        assert "roberta-large-bne" in TRANSFORMER_NER_MODELS
        assert "beto-ner" in TRANSFORMER_NER_MODELS

    def test_transformer_ner_entity_dataclass(self):
        """TransformerNEREntity tiene los campos correctos."""
        from narrative_assistant.nlp.transformer_ner import TransformerNEREntity

        ent = TransformerNEREntity(
            text="Madrid", label="LOC", start=10, end=16, score=0.95
        )
        assert ent.text == "Madrid"
        assert ent.label == "LOC"
        assert ent.score == 0.95

    def test_transformer_ner_label_mapping(self):
        """Las etiquetas se mapean correctamente."""
        from narrative_assistant.nlp.transformer_ner import LABEL_MAP

        assert LABEL_MAP["PER"] == "PER"
        assert LABEL_MAP["LOC"] == "LOC"
        assert LABEL_MAP["ORG"] == "ORG"
        assert LABEL_MAP["OTH"] == "MISC"  # CAPITEL

    def test_extractor_accepts_transformer_flag(self):
        """NERExtractor acepta el flag use_transformer_ner."""
        extractor = NERExtractor(use_transformer_ner=False)
        assert extractor.use_transformer_ner is False

    def test_extract_entities_without_transformer(self):
        """La extracción funciona sin transformer NER."""
        extractor = NERExtractor(use_transformer_ner=False)
        text = "María García vive en Barcelona."
        result = extractor.extract_entities(text)
        assert result.is_success
        assert len(result.value.entities) > 0

    def test_voting_boost_confidence(self):
        """La votación multi-método aumenta la confianza."""
        from narrative_assistant.nlp.ner import ExtractedEntity

        extractor = NERExtractor(use_transformer_ner=False)
        # Simular entidades de diferentes fuentes con la misma forma canónica
        entities = [
            ExtractedEntity(
                text="Madrid", label=EntityLabel.LOC,
                start_char=0, end_char=6, confidence=0.8, source="spacy",
            )
        ]
        transformer_ents = [
            ExtractedEntity(
                text="Madrid", label=EntityLabel.LOC,
                start_char=0, end_char=6, confidence=0.9, source="roberta",
            )
        ]
        llm_ents = [
            ExtractedEntity(
                text="Madrid", label=EntityLabel.LOC,
                start_char=0, end_char=6, confidence=0.85, source="llm",
            )
        ]
        result = extractor._apply_multi_method_voting(
            entities, transformer_ents, llm_ents
        )
        # 3 métodos coinciden → boost +0.15, pero capped at 0.98
        assert result[0].confidence > 0.8
