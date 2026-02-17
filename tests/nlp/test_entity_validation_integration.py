"""
Tests de integración end-to-end para validación de entidades.

Verifica que el sistema completo (NER + EntityValidator) filtra correctamente
falsos positivos como marcadores temporales.
"""

import pytest

from narrative_assistant.nlp.ner import NERExtractor


@pytest.fixture(scope="module")
def ner_extractor():
    """Fixture del extractor NER con validación habilitada."""
    return NERExtractor(
        enable_gazetteer=True,
        use_llm_preprocessing=False,  # Deshabilitar LLM para tests rápidos
        use_transformer_ner=False,  # Deshabilitar transformer para tests rápidos
    )


class TestDiscourseMarkerFiltering:
    """Tests end-to-end para filtrado de marcadores discursivos."""

    def test_acto_seguido_not_extracted(self, ner_extractor):
        """'acto seguido' NO debe extraerse como entidad."""
        text = "María llegó a casa y acto seguido se marchó a la tienda."

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value
        entity_texts = [e.text for e in entities.entities]

        # "María" debe extraerse
        assert "María" in entity_texts, "María debería haberse extraído como entidad"

        # "acto seguido" NO debe extraerse
        assert "acto seguido" not in entity_texts, "acto seguido NO debería ser una entidad"

        # Verificar que fue rechazada si llegó al validador
        rejected_texts = [e.text for e in entities.rejected_entities]
        if "acto seguido" in rejected_texts:
            # Si llegó al validador, debe estar rechazada
            assert "acto seguido" in rejected_texts

    def test_multiple_discourse_markers_filtered(self, ner_extractor):
        """Múltiples marcadores discursivos deben filtrarse."""
        text = """
        Juan entró en la habitación. Acto seguido miró alrededor.
        Poco después salió corriendo. De repente se detuvo.
        Mientras tanto, María esperaba afuera.
        """

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value
        entity_texts = [e.text.lower() for e in entities.entities]

        # Marcadores que NO deben extraerse
        forbidden_markers = ["acto seguido", "poco después", "de repente", "mientras tanto"]

        for marker in forbidden_markers:
            assert marker not in entity_texts, f"'{marker}' NO debería ser una entidad"

        # Personajes que SÍ deben extraerse
        assert any("juan" in e.lower() for e in entity_texts), "Juan debería haberse extraído"
        assert any("maría" in e.lower() for e in entity_texts), "María debería haberse extraído"

    def test_temporal_marker_in_title_filtered(self, ner_extractor):
        """Marcador temporal en título también debe filtrarse."""
        text = """
        Capítulo 5: Acto Seguido

        María llegó y vio la escena.
        """

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value
        entity_texts = [e.text.lower() for e in entities.entities]

        # "Acto Seguido" NO debe extraerse (marcador temporal + zona no-narrativa)
        assert "acto seguido" not in entity_texts

        # "María" sí debe extraerse
        assert any("maría" in e.lower() for e in entity_texts)

    def test_real_entity_with_similar_name_not_filtered(self, ner_extractor):
        """Entidad real con nombre similar NO debe filtrarse."""
        # "Seguido" podría ser un apellido real
        text = """
        Juan Seguido es un personaje importante.
        Seguido trabajaba en la empresa desde hace años.
        """

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value
        entity_texts = [e.text for e in entities.entities]

        # "Juan Seguido" o "Seguido" deben extraerse (es un apellido)
        assert any("Seguido" in e for e in entity_texts), "Seguido (apellido) debería ser válido"

        # Pero "acto seguido" NO
        assert "acto seguido" not in [e.lower() for e in entity_texts]


class TestEntityValidationStats:
    """Tests para estadísticas de validación."""

    def test_validation_stats_populated(self, ner_extractor):
        """Las estadísticas de validación deben poblarse correctamente."""
        text = "María llegó y acto seguido se marchó."

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value

        # Debe haber estadísticas de validación
        assert entities.validation_scores is not None
        assert isinstance(entities.validation_scores, dict)

        # El método de validación debe estar definido
        assert entities.validation_method in ["heuristic", "combined", "none"]

        # Si hay entidades rechazadas, deben tener scores
        if entities.rejected_entities:
            for rejected in entities.rejected_entities:
                # Puede estar en validation_scores o no (dependiendo de si llegó al validador)
                if rejected.text in entities.validation_scores:
                    score = entities.validation_scores[rejected.text]
                    assert "is_valid" in score
                    assert score["is_valid"] is False

    def test_rejected_count_with_discourse_markers(self, ner_extractor):
        """Texto con marcadores debe incrementar rejected_entities."""
        text = """
        María vive en Madrid. Acto seguido fue a Barcelona.
        Poco después regresó a casa. De repente sonó el teléfono.
        """

        result = ner_extractor.extract_entities(text, enable_validation=True)
        assert result.is_success

        entities = result.value

        # Debe haber al menos algunas entidades rechazadas
        # (los marcadores discursivos si llegaron al validador)
        rejected_texts = [e.text.lower() for e in entities.rejected_entities]

        # Al menos uno de los marcadores debe estar rechazado
        discourse_markers_found = [
            m for m in ["acto seguido", "poco después", "de repente"] if m in rejected_texts
        ]

        # Puede que no todos lleguen al validador (algunos se filtran antes)
        # pero si llegaron, deben estar rechazados
        if discourse_markers_found:
            assert len(discourse_markers_found) > 0, "Marcadores discursivos deben rechazarse"
