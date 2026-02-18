"""
Tests para validación automática de entidades (entity_validation.py).

Verifica que el EntityValidator filtra correctamente falsos positivos
como marcadores temporales ("acto seguido") y expresiones discursivas.
"""

import pytest

from narrative_assistant.nlp.entity_validator import (
    DISCOURSE_MARKERS,
    EntityValidator,
    ValidationResult,
)
from narrative_assistant.nlp.spacy_gpu import load_spacy_model


@pytest.fixture(scope="module")
def nlp():
    """Fixture de spaCy compartido para todos los tests."""
    return load_spacy_model()


@pytest.fixture
def validator(nlp):
    """Fixture del validador."""
    return EntityValidator(nlp)


class TestDiscourseMarkers:
    """Tests para filtrado de marcadores discursivos."""

    def test_acto_seguido_rejected(self, validator):
        """'acto seguido' debe rechazarse como marcador temporal."""
        result = validator.validate_entity("acto seguido")
        assert not result.is_valid
        assert "discursivo" in result.reason.lower() or "temporal" in result.reason.lower()

    def test_poco_despues_rejected(self, validator):
        """'poco después' debe rechazarse como marcador temporal."""
        result = validator.validate_entity("poco después")
        assert not result.is_valid
        assert "discursivo" in result.reason.lower() or "temporal" in result.reason.lower()

    def test_de_repente_rejected(self, validator):
        """'de repente' debe rechazarse como marcador temporal."""
        result = validator.validate_entity("de repente")
        assert not result.is_valid

    def test_all_discourse_markers_rejected(self, validator):
        """Todos los marcadores en DISCOURSE_MARKERS deben rechazarse."""
        for marker in DISCOURSE_MARKERS:
            result = validator.validate_entity(marker)
            assert not result.is_valid, f"Marcador '{marker}' no fue rechazado"


class TestPOSPatterns:
    """Tests para validación de patrones POS."""

    def test_invalid_pos_adv_adv_rejected(self, validator, nlp):
        """Patrón ADV+ADV inválido debe rechazarse."""
        doc = nlp("Y acto seguido se marchó.")
        result = validator.validate_entity("acto seguido", doc=doc)
        # Puede rechazarse por marcador discursivo O por patrón POS
        assert not result.is_valid

    def test_valid_proper_noun_accepted(self, validator, nlp):
        """Nombres propios válidos deben aceptarse por POS."""
        doc = nlp("María García es la protagonista.")
        result = validator.validate_entity("María García", doc=doc)
        # Sin menciones, valida por POS
        assert result.is_valid


class TestSyntacticRoles:
    """Tests para análisis de roles sintácticos."""

    def test_entity_with_subject_role_accepted(self, validator):
        """Entidad con rol de sujeto debe aceptarse."""
        mentions = [
            {
                "text": "María",
                "validationReasoning": "Aparece como sujeto (nsubj) de 'caminaba'",
                "confidence": 0.9,
            }
        ]
        result = validator.validate_entity("María", mentions=mentions)
        assert result.is_valid
        assert result.stats is not None
        assert result.stats.subject_count == 1

    def test_entity_with_object_role_accepted(self, validator):
        """Entidad con rol de objeto debe aceptarse."""
        mentions = [
            {
                "text": "Juan",
                "validationReasoning": "Aparece como objeto directo (dobj)",
                "confidence": 0.9,
            }
        ]
        result = validator.validate_entity("Juan", mentions=mentions)
        assert result.is_valid
        assert result.stats is not None
        assert result.stats.object_count == 1

    def test_entity_only_possessive_rejected(self, validator):
        """Entidad solo en contexto posesivo debe rechazarse."""
        mentions = [
            {
                "text": "Isabel",
                "validationReasoning": "Contexto posesivo (poss): 'el amante de Isabel'",
                "confidence": 0.6,
            },
            {
                "text": "Isabel",
                "validationReasoning": "Contexto posesivo (poss): 'la casa de Isabel'",
                "confidence": 0.6,
            },
        ]
        result = validator.validate_entity("Isabel", mentions=mentions)
        assert not result.is_valid
        assert "sin roles sintácticos activos" in result.reason.lower()
        assert result.stats is not None
        assert result.stats.possessive_count == 2
        assert result.stats.subject_count == 0
        assert result.stats.object_count == 0

    def test_entity_mixed_roles_accepted(self, validator):
        """Entidad con roles mixtos (sujeto + posesivo) debe aceptarse."""
        mentions = [
            {
                "text": "Ana",
                "validationReasoning": "Aparece como sujeto (nsubj)",
                "confidence": 0.9,
            },
            {
                "text": "Ana",
                "validationReasoning": "Contexto posesivo (poss): 'el libro de Ana'",
                "confidence": 0.6,
            },
        ]
        result = validator.validate_entity("Ana", mentions=mentions)
        assert result.is_valid
        assert result.stats is not None
        assert result.stats.subject_count == 1
        assert result.stats.possessive_count == 1


class TestEndToEnd:
    """Tests de integración end-to-end."""

    def test_realistic_false_positive_filtered(self, validator, nlp):
        """Test realista: marcador temporal en contexto."""
        doc = nlp("María llegó y acto seguido se marchó.")

        # Simular menciones que podría generar mention_finder
        mentions_maria = [
            {
                "text": "María",
                "validationReasoning": "Aparece como sujeto (nsubj) de 'llegó'",
                "confidence": 0.9,
            }
        ]

        mentions_acto_seguido = [
            {
                "text": "acto seguido",
                "validationReasoning": "Aparece como adverbio (advmod)",
                "confidence": 0.5,
            }
        ]

        result_maria = validator.validate_entity("María", mentions=mentions_maria, doc=doc)
        result_acto = validator.validate_entity("acto seguido", mentions=mentions_acto_seguido, doc=doc)

        assert result_maria.is_valid, "María debería ser válida"
        assert not result_acto.is_valid, "acto seguido debería ser inválida"

    def test_no_mentions_no_doc_accepts_by_default(self, validator):
        """Sin menciones ni doc, debería aceptar por defecto (validación incompleta)."""
        result = validator.validate_entity("Nombre Desconocido")
        assert result.is_valid
        assert "incompleta" in result.reason.lower()
        assert result.confidence < 1.0
